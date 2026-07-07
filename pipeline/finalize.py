"""
Stage 3 of the ad machine: FINALIZE — turn the cut into the Remotion `new-ad` composition.
- copies base_cut.mp4 -> my-video/public/ad.mp4 (faststart, so the studio preview plays)
- generates captions from words_cut.json -> my-video/src/captionsData.ts
- sets AD_DUR in my-video/src/adConfig.ts  (cut_len / SPEED * fps)

Run:  venv/Scripts/python.exe pipeline/finalize.py --work work_cut
"""
import json, os, re, subprocess, argparse

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
VID = r"C:\Users\User\my-video"
HERE = os.path.dirname(__file__)
SPEED, FPS = 1.1, 30

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_cut")
    a = ap.parse_args()

    base = os.path.join(a.work, "base_cut.mp4")
    assert os.path.exists(base), "run cut_heuristic.py --assemble first"

    # 1) footage -> public/ad.mp4 (faststart)
    dst = os.path.join(VID, "public", "ad.mp4")
    bak = os.path.join(VID, "public", "ad_prev.bak.mp4")
    if os.path.exists(dst) and not os.path.exists(bak):
        os.replace(dst, bak)
    subprocess.run([FF, "-y", "-i", base, "-c", "copy", "-movflags", "+faststart", dst], capture_output=True)
    print("installed footage ->", dst)

    # 2) captions -> src/captionsData.ts
    cap_out = os.path.join(VID, "src", "captionsData.ts")
    subprocess.run(["python", os.path.join(HERE, "gen_captions.py"),
                    os.path.join(a.work, "words_cut.json"), "--speed", str(SPEED),
                    "--fps", str(FPS), "--out", cap_out], check=True)

    # 3) AD_DUR -> src/adConfig.ts
    words = json.load(open(os.path.join(a.work, "words_cut.json"), encoding="utf-8"))
    cut_len = words[-1]["end"] + 0.3
    ad_dur = round(cut_len / SPEED * FPS)
    cfg = os.path.join(VID, "src", "adConfig.ts")
    txt = open(cfg, encoding="utf-8").read()
    txt = re.sub(r"export const AD_DUR = \d+;", f"export const AD_DUR = {ad_dur};", txt)
    open(cfg, "w", encoding="utf-8").write(txt)
    print(f"AD_DUR = {ad_dur} frames ({cut_len:.1f}s cut / {SPEED}x)")
    print("DONE — open Remotion studio, composition 'new-ad'.")

if __name__ == "__main__":
    main()
