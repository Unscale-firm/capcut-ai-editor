"""
Word-level refine of the cut: assemble base_cut.mp4 from an EXPLICIT list of mic-time keep
ranges (so repeated-sentence first-attempts can be excised mid-segment, which the segment-level
cut_heuristic can't do). Rewrites base_cut.mp4, words_cut.json, keep_ranges.json in --work.

Run:
  venv/Scripts/python.exe pipeline/refine_cut.py --work work_ad0604 --front work_ad0604/src/front.mp4 \
    --ranges "37.18:45.56,48.76:51.84,102.38:106.28,..." --assemble
"""
import json, os, argparse, subprocess

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"  # non-Windows: use ffmpeg from PATH

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_ad0604")
    ap.add_argument("--front", required=True)
    ap.add_argument("--ranges", required=True, help="comma list of micStart:micEnd (seconds)")
    ap.add_argument("--assemble", action="store_true")
    a = ap.parse_args()

    off = json.load(open(os.path.join(a.work, "offsets.json")))
    words = json.load(open(os.path.join(a.work, "words.json"), encoding="utf-8"))
    ranges = []
    for tok in a.ranges.split(","):
        x, y = tok.split(":"); ranges.append([round(float(x), 3), round(float(y), 3)])

    # words_cut on the OUTPUT timeline
    words_cut, t_out = [], 0.0
    for (x, y) in ranges:
        for w in words:
            if x - 1e-6 <= w["start"] < y - 1e-6:
                ns = t_out + (w["start"] - x)
                words_cut.append({"start": round(ns, 3), "end": round(ns + (w["end"] - w["start"]), 3), "word": w["word"]})
        t_out += (y - x)

    json.dump(ranges, open(os.path.join(a.work, "keep_ranges.json"), "w"))
    json.dump(words_cut, open(os.path.join(a.work, "words_cut.json"), "w"), ensure_ascii=False)
    print(f"{len(ranges)} ranges -> {t_out:.2f}s cut, {len(words_cut)} words")
    for (x, y) in ranges:
        txt = " ".join(w["word"] for w in words if x - 1e-6 <= w["start"] < y - 1e-6)
        print(f"  [{x:7.2f}:{y:7.2f}] {txt[:70]}")

    if a.assemble:
        fo = off["front"]
        mic_hq = os.path.join(a.work, "mic_hq.wav")
        mic = mic_hq if os.path.exists(mic_hq) else os.path.join(a.work, "audio_mic.wav")
        parts = []
        for i, (x, y) in enumerate(ranges):
            parts.append(f"[0:v]trim=start={x+fo:.3f}:end={y+fo:.3f},setpts=PTS-STARTPTS[v{i}];")
            parts.append(f"[1:a]atrim=start={x:.3f}:end={y:.3f},asetpts=PTS-STARTPTS[a{i}];")
        fc = "".join(parts) + "".join(f"[v{i}][a{i}]" for i in range(len(ranges))) + f"concat=n={len(ranges)}:v=1:a=1[v][a]"
        fcfile = os.path.join(a.work, "fc.txt"); open(fcfile, "w").write(fc)
        out = os.path.join(a.work, "base_cut.mp4")
        print("assembling base_cut.mp4 ...")
        r = subprocess.run([FF, "-y", "-i", a.front, "-i", mic, "-filter_complex_script", fcfile,
                            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "19", "-c:a", "aac", "-b:a", "192k", out], capture_output=True, text=True)
        print("FFMPEG ERROR:\n" + r.stderr[-1200:] if r.returncode else "wrote " + out)

if __name__ == "__main__":
    main()
