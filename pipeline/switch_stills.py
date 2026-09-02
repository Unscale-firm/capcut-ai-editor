"""
Contact sheet of a render at the angle-switch frames, so the framing is checked by eye BEFORE surfacing.

    venv/bin/python pipeline/switch_stills.py --video render.mp4 --frames 1020,1170,1885,2050 \
        [--fps 30] [--offset 5] [--face] --out sheet.png

Grabs one still per listed frame (+offset frames, i.e. just after the switch has landed), tiles them
with the frame number burned in. ffmpeg only (drawtext + hstack/vstack), no OpenCV needed.
--face needs OpenCV: runs the face_frame.py detector on each still and prints
    frame  cx%  cy%  height%  [OFF-CENTRE if |cx-50| > 8]  [OVER-ZOOM if height > 35%]
Without cv2 it prints "cv2 not installed" and still builds the sheet.
"""
import os, sys, argparse, subprocess, tempfile

sys.path.insert(0, os.path.dirname(__file__))
from face_frame import cv2, detect_largest_face, png_size, dt_escape, OFFCENTRE_PCT, OVERZOOM_PCT

FF = "ffmpeg"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True)
    ap.add_argument("--frames", required=True, help="comma-separated switch frames (comp frame numbers)")
    ap.add_argument("--fps", type=float, default=30.0)
    ap.add_argument("--offset", type=int, default=5, help="frames AFTER each listed frame to sample")
    ap.add_argument("--face", action="store_true", help="detect the face on every still and flag framing (cv2)")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--tile-h", type=int, default=640)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    frames = [int(x) for x in a.frames.split(",") if x.strip()]
    if a.face and cv2 is None:
        print("cv2 not installed — sheet only, no face metrics")
        a.face = False

    tmpdir = tempfile.mkdtemp(prefix="stills_")
    tiles = []
    for fr in frames:
        f = fr + a.offset
        t = f / a.fps
        png = os.path.join(tmpdir, f"f{f}.png")
        subprocess.run([FF, "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", a.video, "-frames:v", "1", png], check=True)
        w, h = png_size(png)
        label = f"f{fr}+{a.offset}={f}  {t:.2f}s"
        color, box = "white", None
        if a.face:
            det = detect_largest_face(cv2.imread(png))
            if det is None:
                print(f"{fr:>6}  NO FACE")
                label += "  NO FACE"
                color = "red"
            else:
                x, y, fw, fh, _ = det
                box = (x, y, fw, fh)
                cx, cy, hp = (x + fw / 2) / w * 100, (y + fh / 2) / h * 100, fh / h * 100
                flags = []
                if abs(cx - 50) > OFFCENTRE_PCT:
                    flags.append("OFF-CENTRE")
                if hp > OVERZOOM_PCT:
                    flags.append("OVER-ZOOM")
                print(f"{fr:>6}  cx={cx:5.1f}%  cy={cy:5.1f}%  h={hp:5.1f}%  {' '.join(flags)}")
                label += f"  cx{cx:.0f} h{hp:.0f}" + (" " + " ".join(flags) if flags else "")
                color = "red" if flags else "lime"
        tiles.append((png, w, h, label, color, box))

    # one ffmpeg call: per-tile scale + label, then rows (hstack) and the sheet (vstack)
    cols = max(1, min(a.cols, len(tiles)))
    tw = int(tiles[0][1] * a.tile_h / tiles[0][2]) // 2 * 2
    cmd = [FF, "-v", "error", "-y"]
    parts = []
    for i, (png, w, h, label, color, box) in enumerate(tiles):
        cmd += ["-i", png]
        chain = []
        if box:
            x, y, fw, fh = box
            chain.append(f"drawbox=x={x}:y={y}:w={fw}:h={fh}:color=lime:t=6")
        chain.append(f"drawbox=x={w // 2 - 1}:y=0:w=2:h=ih:color=orange:t=fill")     # canvas centre line
        chain.append(f"scale={tw}:{a.tile_h}")
        chain.append("drawbox=x=0:y=0:w=iw:h=34:color=black:t=fill")
        chain.append(f"drawtext=text='{dt_escape(label)}':x=6:y=7:fontsize=22:fontcolor={color}")
        parts.append(f"[{i}:v]{','.join(chain)}[t{i}]")
    n = len(tiles)
    pad = (-n) % cols
    for j in range(pad):
        parts.append(f"color=black:s={tw}x{a.tile_h}:d=1[t{n + j}]")
    total = n + pad
    rows = []
    for r in range(total // cols):
        ins = "".join(f"[t{r * cols + c}]" for c in range(cols))
        if cols == 1:
            parts.append(f"{ins}null[r{r}]")
        else:
            parts.append(f"{ins}hstack=inputs={cols}[r{r}]")
        rows.append(f"[r{r}]")
    if len(rows) == 1:
        parts[-1] = parts[-1].replace(f"[r0]", "")
    else:
        parts.append("".join(rows) + f"vstack=inputs={len(rows)}")
    cmd += ["-filter_complex", ";".join(parts), "-frames:v", "1", a.out]
    subprocess.run(cmd, check=True)
    for png, *_ in tiles:
        os.unlink(png)
    os.rmdir(tmpdir)
    sw, sh = png_size(a.out)
    print(f"wrote {a.out}  ({sw}x{sh}, {n} stills, tile {tw}x{a.tile_h})")


if __name__ == "__main__":
    main()
