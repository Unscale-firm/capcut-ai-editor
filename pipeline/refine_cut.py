"""
Word-level refine of the cut: assemble base_cut.mp4 from an EXPLICIT list of mic-time keep
ranges (so repeated-sentence first-attempts can be excised mid-segment, which the segment-level
cut_heuristic can't do). Rewrites base_cut.mp4, words_cut.json, keep_ranges.json in --work.

Run:
  venv/Scripts/python.exe pipeline/refine_cut.py --work work_ad0604 --front work_ad0604/src/front.mp4 \
    --ranges "37.18:45.56,48.76:51.84,102.38:106.28,..." --assemble
"""
import json, os, argparse, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from seams import snap_ranges, words_on_timeline, mic_wav_for

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"  # non-Windows: use ffmpeg from PATH

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_ad0604")
    ap.add_argument("--front", required=True)
    ap.add_argument("--ranges", required=True,
                    help="comma list of micStart:micEnd (seconds). Suffix an edge with ! to make it HARD "
                         "(trusted as given, not extended to the next silence): 139.6:143.5!,146.8:159.7")
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--no-snap", action="store_true", help="use the ranges exactly as given (no silence snapping)")
    ap.add_argument("--no-verify", action="store_true", help="skip the seam verifier after --assemble")
    a = ap.parse_args()

    off = json.load(open(os.path.join(a.work, "offsets.json")))
    words = json.load(open(os.path.join(a.work, "words.json"), encoding="utf-8"))
    ranges, hard = [], []
    for tok in a.ranges.split(","):
        x, y = tok.split(":")
        hard.append((x.endswith("!"), y.endswith("!")))
        ranges.append([round(float(x.rstrip("!")), 3), round(float(y.rstrip("!")), 3)])

    if not a.no_snap:
        # the given ranges come from Whisper word times; move each edge onto real silence
        print("--- snapping cuts to silence ---")
        ranges = snap_ranges(ranges, words, mic_wav_for(a.work), verbose=True, hard=hard)
    # words_cut on the OUTPUT timeline (midpoint rule: a word belongs to the range holding its middle)
    words_cut = words_on_timeline(ranges, words)
    t_out = sum(y - x for x, y in ranges)

    json.dump(ranges, open(os.path.join(a.work, "keep_ranges.json"), "w"))
    json.dump(words_cut, open(os.path.join(a.work, "words_cut.json"), "w"), ensure_ascii=False)
    print(f"{len(ranges)} ranges -> {t_out:.2f}s cut, {len(words_cut)} words")
    for (x, y) in ranges:
        txt = " ".join(w["word"] for w in words if x <= (w["start"] + w["end"]) / 2 <= y)
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
        # NVENC (GPU) when available, else libx264
        has_nvenc = "h264_nvenc" in subprocess.run([FF, "-hide_banner", "-encoders"],
                                                   capture_output=True, text=True).stdout
        venc = ["-c:v", "h264_nvenc", "-preset", "p4", "-tune", "hq", "-rc", "vbr", "-cq", "19", "-b:v", "0"] \
            if has_nvenc else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19"]
        hwdec = ["-hwaccel", "cuda"] if has_nvenc else []
        r = subprocess.run([FF, "-y", *hwdec, "-i", a.front, "-i", mic, "-filter_complex_script", fcfile,
                            "-map", "[v]", "-map", "[a]", *venc,
                            "-c:a", "aac", "-b:a", "192k", out], capture_output=True, text=True)
        print("FFMPEG ERROR:\n" + r.stderr[-1200:] if r.returncode else "wrote " + out)
        if r.returncode == 0 and not a.no_verify:
            subprocess.run([sys.executable, os.path.join(HERE, "verify_words.py"), "--work", a.work])

if __name__ == "__main__":
    main()
