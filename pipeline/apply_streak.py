"""
apply_streak.py — batch-composite an orange light-streak overlay onto the edit at each cut.

Effect: at every cut timestamp, `streak.mp4` (orange streak on BLACK) is screen-blended over
`main.mp4` so the black drops out and only the warm streak shows — a ~5-frame diagonal swipe of
light that masks the cut. Output is same resolution/fps as main, H.264.

Screen-blend + timing is done by building a black "streak track" the length of main, dropping the
streak clip onto it at each cut (peak = cut frame), then `blend=all_mode=screen` with main.

Tweak the variables in CONFIG below.
"""
import subprocess, json, os

# ─────────────── CONFIG (tweak these) ───────────────
MAIN    = r"C:\Users\User\my-video\public\ad.mp4"          # edited talking-head video
STREAK  = r"C:\Users\User\capcut-ai-editor\work\streak.mp4" # orange streak overlay on black bg
OUT     = r"C:\Users\User\Downloads\unscale_ad\main_streaked.mp4"
CUTS    = [16.9, 46.8, 66.6, 107.7]   # seconds — where the streak lands (peak = cut)
OPACITY = 0.9                         # 0..1 streak strength
WIN     = 5                           # frames of streak kept around each cut
ROTATE  = 0                           # degrees to rotate the streak (0 = as-is)
# ────────────────────────────────────────────────────

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
FP = FF.replace("ffmpeg.exe", "ffprobe.exe")
if not os.path.exists(FF):
    FF, FP = "ffmpeg", "ffprobe"  # non-Windows: use PATH

def probe(path):
    out = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_read_frames:format=duration",
        "-count_frames", "-of", "json", path], capture_output=True, text=True).stdout
    d = json.loads(out); s = d["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    fps = float(num) / float(den)
    return int(s["width"]), int(s["height"]), fps, float(d["format"]["duration"]), int(s.get("nb_read_frames", 0) or 0)

def main():
    W, H, fps, dur, _ = probe(MAIN)
    _, _, _, _, sframes = probe(STREAK)
    half = WIN / 2.0 / fps                      # half-window in seconds
    peak = (sframes // 2) if sframes else 3     # assume the streak peaks at its middle
    trim0 = max(0, peak - WIN // 2)

    rot = f",rotate={ROTATE}*PI/180:c=black@0" if ROTATE else ""
    # streak: scale to frame, trim ~WIN frames around its peak, apply opacity (work in RGB throughout)
    pre = (f"[1:v]scale={W}:{H},setsar=1{rot},"
           f"trim=start_frame={trim0}:end_frame={trim0+WIN},setpts=PTS-STARTPTS,"
           f"colorchannelmixer=rr={OPACITY}:gg={OPACITY}:bb={OPACITY},format=gbrp[sc];")
    n = len(CUTS)
    split = f"[sc]split={n}" + "".join(f"[c{i}]" for i in range(n)) + ";"
    base = f"color=c=black:s={W}x{H}:r={fps:.6f}:d={dur:.3f},format=gbrp[bg];"

    chain = base
    prev = "bg"
    for i, t in enumerate(CUTS):
        start = t - half
        chain += (f"[c{i}]setpts=PTS-STARTPTS+{start:.4f}/TB[o{i}];"
                  f"[{prev}][o{i}]overlay=enable='between(t,{t-half:.4f},{t+half:.4f})'[b{i}];")
        prev = f"b{i}"
    # force both sides to RGB (gbrp) before screen blend, back to yuv420p after (avoids the magenta bug)
    blend = (f"[0:v]format=gbrp[mn];"
             f"[mn][{prev}]blend=all_mode=screen,format=yuv420p[v]")
    fc = pre + split + chain + blend

    cmd = [FF, "-y", "-i", MAIN, "-i", STREAK, "-filter_complex", fc,
           "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-r", f"{fps:.6f}", "-pix_fmt", "yuv420p", "-c:a", "copy", OUT]
    print(f"main {W}x{H} @ {fps:.2f}fps, {dur:.1f}s | streak {sframes}f | {n} cuts @ {CUTS}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    print("ERROR:\n" + r.stderr[-1600:] if r.returncode else "wrote " + OUT)

if __name__ == "__main__":
    main()
