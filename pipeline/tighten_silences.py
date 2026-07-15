"""
Detect silences in base_cut.mp4 (ground truth — Whisper word timings smear across pauses) and
produce a TIGHTENED set of mic-time keep ranges that caps every pause at CAP seconds. Prints the
--ranges string for refine_cut.py.

Run: venv/Scripts/python.exe pipeline/tighten_silences.py --work work_ad0604
"""
import json, os, re, subprocess, argparse

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"  # non-Windows: use ffmpeg from PATH
CAP = 0.22   # keep this much AFTER speech tapers into the pause
PAD = 0.40   # keep this much BEFORE speech resumes (protects soft word onsets from being eaten)
DMIN = 1.00  # only trim clearly-long dead-air pauses

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_ad0604")
    a = ap.parse_args()
    kr = json.load(open(os.path.join(a.work, "keep_ranges.json")))
    base = os.path.join(a.work, "base_cut.mp4")

    # cut-time -> mic-time piecewise map
    cum = 0.0; segs = []
    for (x, y) in kr:
        segs.append({"cs": cum, "ce": cum + (y - x), "a": x}); cum += (y - x)
    total_cut = cum
    def cut2mic(t):
        for s in segs:
            if s["cs"] - 1e-6 <= t <= s["ce"] + 1e-6:
                return s["a"] + (t - s["cs"])
        return None

    # detect silences on the assembled cut
    r = subprocess.run([FF, "-i", base, "-af", f"silencedetect=noise=-30dB:d={DMIN}", "-f", "null", "-"],
                       capture_output=True, text=True)
    log = r.stderr
    sils = []
    cur = None
    for m in re.finditer(r"silence_(start|end):\s*([0-9.]+)", log):
        k, v = m.group(1), float(m.group(2))
        if k == "start": cur = v
        elif k == "end" and cur is not None: sils.append((cur, v)); cur = None

    # removal intervals in MIC time: keep CAP after speech tapers, drop the rest of the pause
    removals = []
    for (cs, ce) in sils:
        if ce - cs <= CAP + PAD: continue           # too short to safely trim
        ms = cut2mic(cs + CAP); me = cut2mic(ce - PAD)
        if ms is None or me is None or me <= ms + 0.05: continue
        removals.append((ms, me))
    removals.sort()
    print(f"{len(sils)} silences, removing {len(removals)} pause-excesses; cut {total_cut:.1f}s -> ~{total_cut - sum(e-s for s,e in removals):.1f}s")

    # subtract removals from each keep range (mic time)
    new = []
    for (a0, b0) in kr:
        cuts = [(s, e) for (s, e) in removals if s < b0 and e > a0]
        pos = a0
        for (s, e) in cuts:
            s = max(s, a0); e = min(e, b0)
            if s > pos + 0.02: new.append([round(pos, 3), round(s, 3)])
            pos = max(pos, e)
        if b0 > pos + 0.02: new.append([round(pos, 3), round(b0, 3)])

    print("--ranges " + ",".join(f"{a0}:{b0}" for a0, b0 in new))

if __name__ == "__main__":
    main()
