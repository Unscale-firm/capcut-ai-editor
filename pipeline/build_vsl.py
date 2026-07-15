"""
VSL finisher — pure ffmpeg, local. No Remotion, no CapCut.

Inputs: the two baked angle cuts (base_cut.mp4 = front, side_cut.mp4 = side), already frame-aligned
on ONE timeline by edl_cut.py. Produces the finished video:

  * speed-up (1.15x default) — video via setpts, audio via atempo (pitch preserved)
  * angle switches — the side angle plays during the SIDE windows, natural size, muted
  * orange flash   — the locked beat on EVERY switch: warm orange bloom (SCREEN-blended, so it
                     glows instead of fogging) + a 2-frame black dip right on the cut

The flash can't be done with chained fade filters — once `fade=out` blacks a stream it stays black,
so a pulse TRAIN is impossible that way. Instead we build a full-length FX track by concatenating
black gaps with a pre-baked bloom clip, then SCREEN it over the footage (screen against black is a
no-op, so the FX track is invisible everywhere except the cuts).

Run:
  venv/Scripts/python.exe pipeline/build_vsl.py --work work_vsl --out C:/Users/User/Downloads/vsl.mp4
"""
import os, argparse, subprocess
import numpy as np

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
W, H, FPS = 1920, 1080, 30

# --- angle-switch plan: SIDE-angle windows, in seconds of the CUT (before the speed-up) ---
SIDE = [
    (111.76, 135.93),   # Tony / Michael / Josh — "none of them are technical"
    (162.34, 185.20),   # McKinsey, Boston -> Dubai, first-class travel
    (203.16, 221.78),   # the 2am voice / the pit in the stomach
    (265.71, 292.52),   # the layoffs — Amazon, Meta, Oracle
    (306.06, 328.28),   # couldn't walk away / Ryan is born
    (359.50, 383.35),   # the Zuckerberg myth / the mistake
    (415.09, 442.81),   # VC = a deal with the devil
    (483.71, 510.43),   # get-rich-quick schemes / rock bottom
    (538.61, 572.37),   # ChatGPT is born
    (603.27, 623.79),   # the first replies pour in / Spiralized
    (655.21, 675.00),   # the art of unscaling
    (705.94, 728.45),   # time with the people I love / the mission
    (767.70, 794.32),   # the three walls
    (819.28, 847.50),   # the marketing team runs your outreach
    (868.04, 896.31),   # the credibility wall
    (904.33, 935.29),   # the SizeMick case study
    (959.68, 979.24),   # how your week actually looks
    (994.29, 1021.94),  # the math — 3 clients at 4k
    (1049.19, 1076.01), # tying my reputation to your name
    (1089.43, 1120.97), # capital / coachable
    (1148.69, 1167.26), # the guarantee, in the contract
    (1181.14, 1202.50), # the blue pill
]

BEAT = 19        # frames in one flash beat
GAP = 3          # the two blooms peak GAP frames either side of the cut...
BW = 4           # ...each with this half-width
DIP = 2          # ...and black dips right on the cut, between them


def bake_bloom(work):
    """One flash beat, pre-rendered: warm orange bloom on BLACK, rising to a peak and falling.
    On black so it can be SCREEN-blended — screen against black leaves the footage untouched."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = 0.30 * W, 0.48 * H              # origin sits left of centre and sweeps warm across
    r = np.sqrt(((x - cx) / (1.85 * W)) ** 2 + ((y - cy) / (1.60 * H)) ** 2)
    r = np.clip(r / 0.62, 0, 1)

    stops = [0.0, 0.26, 0.52, 0.78, 1.0]
    cols = np.array([[255, 186, 96], [255, 154, 44], [255, 116, 0],
                     [232, 96, 20], [206, 80, 16]], dtype=np.float32)    # saturated, not creamy
    inten = np.array([0.98, 0.90, 0.74, 0.52, 0.34], dtype=np.float32)   # falloff across the frame

    rgb = np.stack([np.interp(r, stops, cols[:, i]) for i in range(3)], axis=-1)
    k = (np.interp(r, stops, inten) * 0.80 + 0.16)[..., None]            # + flat base: covers edge to edge
    bloom = rgb * k                                                       # premultiplied onto black

    d = os.path.join(work, "bloom")
    os.makedirs(d, exist_ok=True)
    from PIL import Image
    c = (BEAT - 1) / 2
    bell = lambda i, k: max(0.0, 1.0 - abs(i - k) / BW)
    for i in range(BEAT):
        # TWO blooms — one either side of the cut — with the black dip landing between them.
        # A single bloom peaking on the cut would be wiped out by the dip and never be seen.
        p = max(bell(i, c - GAP), bell(i, c + GAP))
        Image.fromarray(np.clip(bloom * p, 0, 255).astype(np.uint8)).save(
            os.path.join(d, f"{i:03d}.png"))
    print(f"  baked {BEAT}-frame bloom -> {d}")
    return d


def enc(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("FFMPEG ERROR:\n" + r.stderr[-2500:])


def build_fx_track(work, cuts, total):
    """Full-length FX track: black everywhere, bloom at each cut. Concatenated, so it costs
    almost nothing to make and h264 squashes the black to nothing."""
    d = bake_bloom(work)
    beat = os.path.join(work, "beat.mp4")
    enc([FF, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(d, "%03d.png"),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
         "-r", str(FPS), beat])

    gap = os.path.join(work, "gap.mp4")            # a pool of black we slice gaps out of
    enc([FF, "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"color=c=black:s={W}x{H}:r={FPS}:d=200",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p", gap])

    beat_d = BEAT / FPS
    lines, t = [], 0.0
    for c in cuts:
        start = c - beat_d / 2                     # centre the beat on the cut
        if start - t > 0.02:
            lines.append(f"file '{os.path.abspath(gap)}'\noutpoint {start - t:.3f}")
        lines.append(f"file '{os.path.abspath(beat)}'")
        t = start + beat_d
    if total - t > 0.02:
        lines.append(f"file '{os.path.abspath(gap)}'\noutpoint {min(total - t, 199):.3f}")

    lst = os.path.join(work, "fx.txt")
    open(lst, "w").write("\n".join(lines) + "\n")
    fx = os.path.join(work, "fx.mp4")
    enc([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
         "-c", "copy", fx])
    print(f"  built FX track ({len(cuts)} blooms) -> {fx}")
    return fx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_vsl")
    ap.add_argument("--speed", type=float, default=1.15)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", default=None, help="cut-seconds window, e.g. 100,145")
    a = ap.parse_args()

    sp = a.speed
    front = os.path.join(a.work, "base_cut.mp4")
    side = os.path.join(a.work, "side_cut.mp4")
    for p in (front, side):
        assert os.path.exists(p), f"missing {p}"

    windows, t0, dur = SIDE, 0.0, None
    if a.preview:
        p0, p1 = [float(v) for v in a.preview.split(",")]
        windows = [(s, e) for s, e in SIDE if e > p0 and s < p1]
        t0, dur = p0, (p1 - p0)

    T = lambda t: (t - t0) / sp                    # cut-seconds -> output (sped-up) seconds
    total = (dur if dur else 1265.2) / sp
    side_expr = "+".join(f"between(t,{T(s):.3f},{T(e):.3f})" for s, e in windows) or "0"
    cuts = sorted([T(s) for s, e in windows] + [T(e) for s, e in windows])
    dip_expr = "+".join(f"between(t,{c-DIP/2/FPS:.3f},{c+DIP/2/FPS:.3f})" for c in cuts) or "0"

    fx = build_fx_track(a.work, cuts, total)

    fc = (
        f"[0:v]setpts=PTS/{sp},fps={FPS},scale={W}:{H},setsar=1[f];"
        f"[1:v]setpts=PTS/{sp},fps={FPS},scale={W}:{H},setsar=1[s];"
        f"[f][s]overlay=enable='{side_expr}':eof_action=pass,format=gbrp[sw];"
        f"[2:v]scale={W}:{H},setsar=1,format=gbrp[fx];"
        # screen MUST run in RGB — blending yuv planes turns the orange bloom magenta
        f"[sw][fx]blend=all_mode=screen:shortest=1,format=yuv420p[o1];"
        f"color=c=black:s={W}x{H}:r={FPS}[bk];"
        f"[o1][bk]overlay=enable='{dip_expr}':shortest=1[v];"     # 2-frame black dip on the cut
        f"[0:a]atempo={sp}[a]"
    )
    fcf = os.path.join(a.work, "fc_vsl.txt")
    open(fcf, "w").write(fc)

    cmd = [FF, "-y", "-stats"]
    if a.preview:
        p0, p1 = [float(v) for v in a.preview.split(",")]
        cmd += ["-ss", str(p0), "-t", str(p1 - p0), "-i", front,
                "-ss", str(p0), "-t", str(p1 - p0), "-i", side]
    else:
        cmd += ["-i", front, "-i", side]
    cmd += ["-i", fx, "-filter_complex_script", fcf, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", a.out]

    print(f"  speed {sp}x   {len(windows)} side windows   {len(cuts)} switches, each flashed")
    r = subprocess.run(cmd, capture_output=True, text=True)
    print("FFMPEG ERROR:\n" + r.stderr[-2500:] if r.returncode else "wrote " + a.out)


if __name__ == "__main__":
    main()
