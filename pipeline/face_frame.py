"""
Per-ad face framing: measure WHERE the face sits on each camera, then tell Remotion how to frame it.

The camera never moves during a shoot, so the face position per camera is a constant for the whole
tape. Founder complaints this answers: "face not centred after the switch", "why did you zoom that
much", both of which come from the comp using a fixed `scale(ZOOM)` about the canvas centre with no
per-ad offset.

    venv/bin/python pipeline/face_frame.py --front front.mp4 [--side side.mp4] --work work_x \
        --face-box X,Y,W,H [--side-face-box X,Y,W,H]     # face box in PIXELS on the rotated/transposed frame
        [--side-vf transpose=1]   # C0011 side tape is landscape; the installed side*.mp4 already is portrait
        [--front-vf ...]          # ffmpeg autorotates rotation-tagged sources by itself
        [--samples 9]             # only used when OpenCV is installed (auto-detect, median over samples)

Manual workflow (no OpenCV): run once WITHOUT --face-box — it extracts work_x/front_frame.png and
side_frame.png and exits 1. Read the face box off each (forehead-to-chin, ear-to-ear, pixels) and
re-run with --face-box / --side-face-box. Detection is only a convenience when cv2 happens to exist.

Writes:
  work_x/front_frame.png, side_frame.png   one mid-tape frame per camera (rotated/transposed as given)
  work_x/face.json                          all numbers + paste-ready CSS per camera
  work_x/face_check.png                     the frames with the box drawn — LOOK at it before trusting the numbers

Framing math (1080x1920 canvas, `objectFit: 'cover'`, then `transform: scale(Z)`):
  * objectPosition only moves the picture inside the cover overflow. A 9:16 source on a 9:16 canvas has
    NO overflow, so objectPosition is a no-op there (both F10 tapes are 1080x1920 after rotate/transpose).
  * What always works: scale about the EYE LINE and translate it to target —
        transformOrigin: '<fx>px <eyes_y>px'
        transform: `translate(<dx>px, <dy>px) scale(${ZOOM})`
    the eye point stays put under any scale (constant, ramp or punch), the translate parks it at
    x=540, y=40% of the canvas height. Both strings are ZOOM-independent.
  * ZOOM_MAX = 0.32 / (face height as a fraction of the canvas after cover) — face never taller than ~32%.
  * ZOOM_MIN = smallest scale that still fills the canvas after the translate (no black edge).
    ZOOM_MIN > ZOOM_MAX means the face is too far off-centre to fix without over-zooming: pick a side.
"""
import os, sys, json, argparse, subprocess
import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

FF = "ffmpeg"
CANVAS_W, CANVAS_H = 1080, 1920
EYES_TARGET = 0.40          # eyes at 40% from the top of the canvas
FACE_MAX = 0.32             # face box never taller than this fraction of the canvas
EYES_IN_BOX = 0.35          # a forehead->chin box: eyes sit ~35% down from its top
OFFCENTRE_PCT = 8.0         # |cx - 50| beyond this = OFF-CENTRE (switch_stills.py uses the same)
OVERZOOM_PCT = 35.0         # face height above this % of the frame = OVER-ZOOM


# ---------------------------------------------------------------- ffmpeg helpers (no cv2 needed)
def duration_of(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return float(out)


def png_size(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def grab_frame(src, t, out_png, vf=None):
    """One decoded frame at t seconds -> PNG. `-ss` before `-i`: never decodes the whole file."""
    cmd = [FF, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", src]
    if vf:
        cmd += ["-vf", vf]
    cmd += ["-frames:v", "1", out_png]
    subprocess.run(cmd, check=True)
    return png_size(out_png)


def dt_escape(s):
    """drawtext text= value: ':' and ',' end the option otherwise."""
    return s.replace("\\", "\\\\").replace(":", "\\:").replace(",", "\\,").replace("'", "")


def draw_check(frames, out_png, tile_h=720):
    """frames: list of (png, box or None, label). Box drawn with ffmpeg drawbox, tiles hstacked."""
    cmd = [FF, "-v", "error", "-y"]
    parts = []
    for i, (png, box, label) in enumerate(frames):
        cmd += ["-i", png]
        chain = []
        if box is not None:
            x, y, w, h = box
            chain.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=lime:t=6")
            chain.append(f"drawbox=x={x + w // 2 - 2}:y={y}:w=4:h={h}:color=lime:t=fill")   # vertical centre
            chain.append(f"drawbox=x={x}:y={y + int(EYES_IN_BOX * h) - 2}:w={w}:h=4:color=yellow:t=fill")  # eye line
        chain.append(f"scale=-2:{tile_h}")
        chain.append("drawbox=x=0:y=0:w=iw:h=36:color=black:t=fill")
        chain.append(f"drawtext=text='{dt_escape(label)}':x=8:y=8:fontsize=24:fontcolor={'lime' if box else 'red'}")
        parts.append(f"[{i}:v]{','.join(chain)}[t{i}]")
    fc = ";".join(parts) + ";" + "".join(f"[t{i}]" for i in range(len(frames))) + f"hstack=inputs={len(frames)}"
    if len(frames) == 1:
        fc = parts[0].replace(f"[t0]", "")
    cmd += ["-filter_complex", fc, "-frames:v", "1", out_png]
    subprocess.run(cmd, check=True)


# ---------------------------------------------------------------- detection (optional)
_CASCADES = None


def _cascades():
    global _CASCADES
    if _CASCADES is None:
        d = cv2.data.haarcascades
        _CASCADES = [
            ("frontal", cv2.CascadeClassifier(os.path.join(d, "haarcascade_frontalface_default.xml"))),
            ("frontal_alt2", cv2.CascadeClassifier(os.path.join(d, "haarcascade_frontalface_alt2.xml"))),
            ("profile", cv2.CascadeClassifier(os.path.join(d, "haarcascade_profileface.xml"))),
        ]
    return _CASCADES


def detect_largest_face(img):
    """(x, y, w, h, detector_name) of the largest face in a BGR image, or None. Needs cv2."""
    gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
    h, w = gray.shape
    min_side = max(24, int(0.06 * h))
    best = None
    for name, cas in _cascades():
        for flipped in (False, True):
            if flipped and name != "profile":
                continue
            g = cv2.flip(gray, 1) if flipped else gray
            faces = cas.detectMultiScale(g, scaleFactor=1.08, minNeighbors=6, minSize=(min_side, min_side))
            if len(faces) == 0:
                continue
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            if flipped:
                x = w - x - fw
            cand = (int(x), int(y), int(fw), int(fh), name + ("_mirror" if flipped else ""))
            if best is None or cand[2] * cand[3] > best[2] * best[3]:
                best = cand
        if best is not None and name.startswith("frontal"):
            break
    return best


# ---------------------------------------------------------------- framing math (pure numpy)
def framing(w, h, dets, samples=1):
    """dets: list of (x, y, fw, fh, name) boxes in pixels on a w x h source. Median -> canvas framing + CSS."""
    n_ok = len(dets)
    if n_ok == 0:
        return {"source_w": w, "source_h": h, "detected": 0, "samples": samples,
                "error": "no face box (pass --face-box X,Y,W,H read off the extracted frame)"}
    cx = float(np.median([(x + fw / 2) / w for x, y, fw, fh, _ in dets]))
    cy = float(np.median([(y + fh / 2) / h for x, y, fw, fh, _ in dets]))
    fhf = float(np.median([fh / h for x, y, fw, fh, _ in dets]))
    spread_x = float(np.ptp([(x + fw / 2) / w for x, y, fw, fh, _ in dets]))
    spread_y = float(np.ptp([(y + fh / 2) / h for x, y, fw, fh, _ in dets]))
    eyes_y = cy - (0.5 - EYES_IN_BOX) * fhf         # source fraction

    # objectFit: cover  -> displayed size + overflow
    s = max(CANVAS_W / w, CANVAS_H / h)
    wd, hd = w * s, h * s
    ox, oy = wd - CANVAS_W, hd - CANVAS_H

    def obj_pos(target, frac, disp, overflow):
        # source point (frac*disp) lands at target when objectPosition p%: frac*disp + (canvas-disp)*p = target
        if overflow < 1:
            return 50.0
        return float(np.clip((target - frac * disp) / -overflow * 100.0, 0, 100))

    px = obj_pos(CANVAS_W / 2, cx, wd, ox)
    py = obj_pos(EYES_TARGET * CANVAS_H, eyes_y, hd, oy)

    # where the face lands on the canvas after cover + objectPosition
    fx_c = cx * wd - ox * px / 100.0
    fy_c = cy * hd - oy * py / 100.0
    eyes_c = eyes_y * hd - oy * py / 100.0
    fh_c = fhf * hd
    face_frac_canvas = fh_c / CANVAS_H

    # residual: scale about the eye point (fx_c, eyes_c), translate it to (540, 40% H) — holds for any Z
    dx = CANVAS_W / 2 - fx_c
    dy = EYES_TARGET * CANVAS_H - eyes_c
    zoom_max = FACE_MAX / face_frac_canvas
    # smallest Z with no black edge: edges after scale about (fx_c, eyes_c) then translate (dx, dy)
    cands = [1.0]
    if fx_c > 0:               cands.append((fx_c + dx) / fx_c)
    if CANVAS_W - fx_c > 0:    cands.append((CANVAS_W - fx_c - dx) / (CANVAS_W - fx_c))
    if eyes_c > 0:             cands.append((eyes_c + dy) / eyes_c)
    if CANVAS_H - eyes_c > 0:  cands.append((CANVAS_H - eyes_c - dy) / (CANVAS_H - eyes_c))
    zoom_min = float(max(cands))

    return {
        "source_w": w, "source_h": h, "samples": samples, "detected": n_ok,
        "detectors": sorted({d[4] for d in dets}),
        "face_cx": round(cx, 4), "face_cy": round(cy, 4), "face_h": round(fhf, 4),
        "eyes_y": round(eyes_y, 4),
        "spread_x": round(spread_x, 4), "spread_y": round(spread_y, 4),
        "cover_scale": round(s, 4), "overflow_x": round(ox, 1), "overflow_y": round(oy, 1),
        "objectPosition": f"{px:.1f}% {py:.1f}%",
        "objectPosition_effective": bool(ox >= 1 or oy >= 1),
        "face_on_canvas": {"x": round(fx_c, 1), "y": round(fy_c, 1), "eyes_y": round(eyes_c, 1),
                           "h": round(fh_c, 1), "h_frac": round(face_frac_canvas, 4)},
        "transformOrigin": f"{fx_c:.0f}px {eyes_c:.0f}px",
        "translate": f"translate({dx:.0f}px, {dy:.0f}px)",
        "ZOOM_MAX": round(zoom_max, 3),
        "ZOOM_MIN": round(zoom_min, 3),
    }


# ---------------------------------------------------------------- per-camera driver
def measure(name, src, work, vf, box, samples):
    """Extract work/<name>_frame.png; box from --face-box, else cv2 median over `samples` frames."""
    dur = duration_of(src)
    frame_png = os.path.join(work, f"{name}_frame.png")
    w, h = grab_frame(src, dur / 2, frame_png, vf)
    if box is not None:
        dets = [tuple(box) + ("manual",)]
        return framing(w, h, dets, 1), frame_png, tuple(box)
    if cv2 is None:
        return framing(w, h, [], 1), frame_png, None
    lo, hi = min(5.0, dur * 0.05), dur - min(5.0, dur * 0.05)
    dets = []
    for t in np.linspace(lo, hi, samples):
        tmp = os.path.join(work, f"_{name}_sample.png")
        grab_frame(src, float(t), tmp, vf)
        d = detect_largest_face(cv2.imread(tmp))
        if d is not None:
            dets.append(d)
        os.unlink(tmp)
    r = framing(w, h, dets, samples)
    box = None
    if dets:
        box = (int(r["face_cx"] * w - np.median([d[2] for d in dets]) / 2),
               int(r["face_cy"] * h - r["face_h"] * h / 2),
               int(np.median([d[2] for d in dets])), int(r["face_h"] * h))
    return r, frame_png, box


def parse_box(s):
    if s is None:
        return None
    v = [int(float(x)) for x in s.split(",")]
    if len(v) != 4:
        raise argparse.ArgumentTypeError("--face-box wants X,Y,W,H in pixels")
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--front", required=True)
    ap.add_argument("--side")
    ap.add_argument("--work", required=True)
    ap.add_argument("--face-box", type=parse_box, help="front face box X,Y,W,H (px on the rotated frame)")
    ap.add_argument("--side-face-box", type=parse_box, help="side face box X,Y,W,H (px on the transposed frame)")
    ap.add_argument("--samples", type=int, default=9, help="cv2 only: frames sampled per camera")
    ap.add_argument("--front-vf", default=None, help="extra ffmpeg -vf for the front (autorotate is automatic)")
    ap.add_argument("--side-vf", default=None,
                    help="ffmpeg -vf for the side, e.g. transpose=1 for the raw C0011 tape, or the same "
                         "crop/hflip/scale chain extract_side.py used so the numbers match the installed clips")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)

    cams = [("front", a.front, a.front_vf, a.face_box)]
    if a.side:
        cams.append(("side", a.side, a.side_vf, a.side_face_box))

    result = {"canvas": [CANVAS_W, CANVAS_H], "eyes_target": EYES_TARGET, "face_max": FACE_MAX}
    check = []
    missing = []
    for name, src, vf, box in cams:
        r, frame_png, box_used = measure(name, src, a.work, vf, box, a.samples)
        result[name] = r
        print(f"\n== {name}  ({r['source_w']}x{r['source_h']}, frame: {frame_png})")
        if "error" in r:
            print("   " + r["error"])
            check.append((frame_png, None, f"{name}: NO BOX"))
            missing.append(name)
            continue
        src_tag = "manual box" if box is not None else f"cv2 on {r['detected']}/{r['samples']} samples"
        print(f"   face centre x={r['face_cx']*100:.1f}%  y={r['face_cy']*100:.1f}%  height={r['face_h']*100:.1f}%  ({src_tag})")
        flags = []
        if abs(r["face_cx"] * 100 - 50) > OFFCENTRE_PCT:
            flags.append("OFF-CENTRE")
        if r["face_on_canvas"]["h_frac"] * 100 > OVERZOOM_PCT:
            flags.append("OVER-ZOOM at scale(1)")
        if flags:
            print("   " + " ".join(flags))
        eff = "" if r["objectPosition_effective"] else "   (NO-OP: source has the canvas aspect, no cover overflow)"
        print(f"   objectPosition: '{r['objectPosition']}',{eff}")
        print(f"   transformOrigin: '{r['transformOrigin']}',")
        print(f"   transform: `{r['translate']} scale(${{ZOOM}})`,")
        print(f"   ZOOM_MAX = {r['ZOOM_MAX']}   ZOOM_MIN = {r['ZOOM_MIN']} (below this the translate shows a black edge)")
        if r["ZOOM_MIN"] > r["ZOOM_MAX"]:
            print("   WARNING: ZOOM_MIN > ZOOM_MAX — cannot centre this face without over-zooming; pick one")
        check.append((frame_png, box_used, f"{name}: box {box_used[0]},{box_used[1]},{box_used[2]},{box_used[3]}"))

    out_png = os.path.join(a.work, "face_check.png")
    draw_check(check, out_png)
    out_json = os.path.join(a.work, "face.json")
    with open(out_json, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nwrote {out_json}\nwrote {out_png}  <- LOOK: box on the face, yellow line through the eyes?")
    if missing:
        flag = "--face-box" if missing[0] == "front" else "--side-face-box"
        print(f"no cv2: read the face box off {a.work}/{missing[0]}_frame.png and pass {flag} X,Y,W,H")
        sys.exit(1)


if __name__ == "__main__":
    main()
