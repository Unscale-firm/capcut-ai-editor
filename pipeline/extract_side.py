"""
Extract side-angle clips for angle switches, aligned to the base cut.

For each switch (comp-frame cut point + duration), maps comp frame -> base_cut time ->
mic time (via keep_ranges) -> side-camera source time (+ off_side), and extracts a clip
from the trimmed side video that STARTS exactly at that moment (plays from frame 0 at SPEED
in Remotion). Each switch must stay within a single kept segment (checked).

Run:
  venv/Scripts/python.exe pipeline/extract_side.py --work work_ad0604 \
    --switches 506:100,1153:120,1904:100,2411:140 --out C:/Users/User/my-video/public --prefix side0604
"""
import json, os, argparse, subprocess

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"  # non-Windows: use ffmpeg from PATH
SPEED, FPS = 1.1, 30

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_ad0604")
    ap.add_argument("--switches", required=True, help="comma list of cutframe:durframe")
    ap.add_argument("--out", required=True)
    ap.add_argument("--prefix", default="side0604")
    a = ap.parse_args()

    kr = json.load(open(os.path.join(a.work, "keep_ranges.json")))
    off = json.load(open(os.path.join(a.work, "offsets.json")))
    side = os.path.join(a.work, "src", "side.mp4")
    off_side = off["side"]

    # cumulative segment map in base_cut seconds
    segs, cum = [], 0.0
    for (x, y) in kr:
        L = y - x
        segs.append({"cs": cum, "ce": cum + L, "mic_a": x})
        cum += L

    def cut_to_mic(fr):
        T = fr / FPS * SPEED  # base_cut seconds
        for s in segs:
            if s["cs"] - 1e-6 <= T <= s["ce"] + 1e-6:
                return s, s["mic_a"] + (T - s["cs"])
        return None, None

    specs = []
    for tok in a.switches.split(","):
        cf, df = tok.split(":")
        specs.append((int(cf), int(df)))

    results = []
    for i, (cf, df) in enumerate(specs, 1):
        s0, mic0 = cut_to_mic(cf)
        s1, mic1 = cut_to_mic(cf + df)
        if s0 is None or s1 is None or s0 is not s1:
            print(f"!! switch {i} (f{cf}+{df}) crosses a segment boundary or is out of range -- skipping")
            continue
        src_start = mic0 + off_side
        length = df / FPS * SPEED + 0.4  # +pad; Remotion plays it at SPEED from frame 0
        out = os.path.join(a.out, f"{a.prefix}_{i}.mp4")
        print(f"switch {i}: f{cf}+{df}  mic {mic0:.2f}s -> side src {src_start:.2f}s  len {length:.2f}s -> {os.path.basename(out)}")
        # reframe: side cam is a WIDE shot -> crop+enlarge to match the front's head-and-shoulders,
        # drop the lamp (x0=0) + lift head to upper third (y0=360); hflip cancels AdComposition's scaleX(-1)
        r = subprocess.run([FF, "-y", "-ss", f"{src_start:.3f}", "-t", f"{length:.3f}", "-i", side,
                            "-vf", "crop=771:1371:0:360,hflip,scale=1080:1920",
                            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                            "-pix_fmt", "yuv420p", out], capture_output=True, text=True)
        if r.returncode:
            print("  FFMPEG ERR:", r.stderr[-400:])
        else:
            results.append((i, cf, df, os.path.basename(out)))
    print("\nSWITCHES (for the component):")
    print("[" + ", ".join(f'{{ cut: {cf}, dur: {df}, src: "{name}" }}' for (i, cf, df, name) in results) + "]")

if __name__ == "__main__":
    main()
