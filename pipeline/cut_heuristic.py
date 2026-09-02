"""
Stage 2 of the ad machine: the CUTTER (v2 — best-take selection).
Reads work/words.json (+ per-word confidence "p") + offsets.json. Removes silences,
slate/warmup lines, and repeated takes — keeping the BEST take of each line (most complete +
clearest delivery + least disfluent). Optionally assembles base_cut.mp4 (front cam + clean mic).

Outputs in --work: keep_ranges.json, words_cut.json, (base_cut.mp4 with --assemble)

Run:
  venv/Scripts/python.exe pipeline/cut_heuristic.py --work work_cut --front <front.mp4> --assemble
"""
import json, re, argparse, os, subprocess, sys
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from seams import snap_ranges, words_on_timeline, mic_wav_for

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"  # non-Windows: use ffmpeg from PATH
SILENCE = 0.8       # gap (s) that ends a speech segment
SIM = 0.60          # ratio above which two segments are the same line (different takes)
ISO = 2.5           # a short segment isolated by gaps this big = slate/warmup
PAD = 0.12          # only used with --no-snap (legacy: fixed pad on the Whisper timestamp)
SLATE = re.compile(
    r"^(number\s+\w+|body|cta|hook|intro|outro|take\s*\d+|fs\s*0?\d+|add\s+fs.*|"
    r"test(,?\s*test)+|super|all right|i'?ll go in|open\s+number.*|come.*|sa.*|"
    r"let'?s go into.*|that'?s? (it|good))\.?$", re.I)
FILLERS = {"um", "uh", "uhh", "umm", "erm", "hmm", "mmm", "ah", "uhm"}

def norm(t):
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()

def segments(words):
    segs, cur = [], []
    for w in words:
        if cur and w["start"] - cur[-1]["end"] > SILENCE:
            segs.append(cur); cur = []
        cur.append(w)
    if cur:
        segs.append(cur)
    return segs

def text(s):
    return " ".join(w["word"] for w in s)

def disfluency(s):
    ws = [re.sub(r"[^a-z']", "", w["word"].lower()) for w in s]
    fil = sum(1 for w in ws if w in FILLERS)
    stut = sum(1 for i in range(1, len(ws)) if ws[i] and ws[i] == ws[i - 1])
    return fil + stut

def score(s):
    nwords = len(s)
    conf = sum(w.get("p", 1.0) for w in s) / max(1, nwords)
    return nwords + 12 * conf - 3 * disfluency(s)

def similar(a, b):
    if not a or not b:
        return False
    if a in b or b in a:
        return min(len(a), len(b)) / max(len(a), len(b)) > 0.4
    return SequenceMatcher(None, a, b).ratio() > SIM

def is_slate(s, prev_gap, next_gap):
    n = norm(text(s))
    if SLATE.match(n):
        return True
    if len(s) <= 6 and prev_gap > ISO and next_gap > ISO:
        return True
    # low-confidence mumbled warmup isolated by big gaps
    conf = sum(w.get("p", 1.0) for w in s) / max(1, len(s))
    if conf < 0.55 and prev_gap > ISO and next_gap > ISO:
        return True
    return False

def select(segs):
    # 1) drop slate / isolated warmup
    content = []
    for i, s in enumerate(segs):
        pg = s[0]["start"] - segs[i - 1][-1]["end"] if i else 999
        ng = segs[i + 1][0]["start"] - s[-1]["end"] if i + 1 < len(segs) else 999
        if not is_slate(s, pg, ng):
            content.append(s)
    # 2) keep the BEST take of each repeated line
    kept = []  # dicts: seg, norm, score
    for s in content:
        n = norm(text(s)); sc = score(s)
        hit = next((k for k in kept if similar(n, k["norm"])), None)
        if hit:
            if sc > hit["score"]:
                hit.update(seg=s, norm=n, score=sc)
        else:
            kept.append({"seg": s, "norm": n, "score": sc})
    # 3) back to time order
    out = sorted((k["seg"] for k in kept), key=lambda s: s[0]["start"])
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_cut")
    ap.add_argument("--front", default=None)
    ap.add_argument("--assemble", action="store_true")
    ap.add_argument("--drop", default="", help="1-based positions in the kept list to remove, e.g. 1,4,5")
    ap.add_argument("--no-snap", action="store_true", help="legacy: pad Whisper timestamps instead of snapping cuts to silence")
    ap.add_argument("--no-verify", action="store_true", help="skip the seam verifier after --assemble")
    a = ap.parse_args()

    words = json.load(open(os.path.join(a.work, "words.json"), encoding="utf-8"))
    off = json.load(open(os.path.join(a.work, "offsets.json")))
    segs = segments(words)
    kept = select(segs)
    if a.drop:
        drop = {int(x) for x in a.drop.replace(" ", "").split(",") if x}
        kept = [s for i, s in enumerate(kept, 1) if i not in drop]
        print(f"(editor dropped positions {sorted(drop)})")

    raw = [[s[0]["start"], s[-1]["end"]] for s in kept]
    if a.no_snap:
        ranges = [[round(max(0, x - PAD), 2), round(y + PAD, 2)] for x, y in raw]
    else:
        # cut on real silence next to the words, never on the Whisper timestamp itself
        print("--- snapping cuts to silence ---")
        ranges = snap_ranges(raw, words, mic_wav_for(a.work), verbose=True)
    words_cut = words_on_timeline(ranges, words)
    t_out = sum(y - x for x, y in ranges)

    json.dump(ranges, open(os.path.join(a.work, "keep_ranges.json"), "w"))
    json.dump(words_cut, open(os.path.join(a.work, "words_cut.json"), "w"), ensure_ascii=False)
    print(f"raw {len(segs)} segs ({words[-1]['end']:.0f}s)  ->  kept {len(kept)} segs ({t_out:.0f}s)")
    print("--- kept lines, in order ---")
    for s in kept:
        print(f"  [{s[0]['start']:6.1f}] {text(s)[:72]}")

    if a.assemble:
        assert a.front
        fo = off["front"]
        # use the full-quality mic (48k) for the final audio, not the 16k transcription copy
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
