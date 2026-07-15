"""
One-off: move the SECOND kept segment ("These are real businesses ... recurring revenue")
in front of the FIRST ("In the next few minutes ..."), so the VSL opens on the recurring-revenue
hook (matches the v5 script's montage-hook-first structure).

The swap lives entirely inside the first ~33s of the cut; every SIDE angle window starts at
111s+, so nothing downstream (build_vsl's SIDE list, the flashes) needs to change. This script:
  1. rewrites keep_ranges.json + words_cut.json in the reordered order (for captions + script_doc)
  2. --assemble : re-bakes base_cut.mp4 from the EXISTING base_cut (no raw source needed) by
     swapping its first two pieces. side_cut is untouched (side is never shown in the first 33s).

Run:
  venv/Scripts/python.exe pipeline/reorder_open.py --work work_vsl --assemble
"""
import os, sys, json, argparse, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from edl_cut import clamp, merge, FF

FPS = 25.0


def compute_ranges(work):
    words = json.load(open(os.path.join(work, "words.json"), encoding="utf-8"))
    off = json.load(open(os.path.join(work, "offsets.json")))
    edl = json.load(open(os.path.join(work, "edl.json")))
    ranges = merge(clamp(edl, words))
    fo = off["front"]
    snapped = []
    for x, y in ranges:
        k0, k1 = round((x + fo) * FPS), round((y + fo) * FPS)
        if k1 <= k0:
            k1 = k0 + 1
        snapped.append([round(k0 / FPS - fo, 4), round(k1 / FPS - fo, 4)])
    return words, snapped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_vsl")
    ap.add_argument("--assemble", action="store_true")
    a = ap.parse_args()

    words, ranges = compute_ranges(a.work)
    # move index 1 (the hook) to the front
    order = [1, 0] + list(range(2, len(ranges)))
    reordered = [ranges[i] for i in order]

    # rebuild words_cut on the NEW timeline (cumulative)
    words_cut, t_out = [], 0.0
    for a0, b0 in reordered:
        for w in words:
            if a0 <= (w["start"] + w["end"]) / 2 <= b0:
                ns = t_out + (w["start"] - a0)
                words_cut.append({"start": round(ns, 3),
                                  "end": round(ns + (w["end"] - w["start"]), 3),
                                  "word": w["word"]})
        t_out += (b0 - a0)

    json.dump(reordered, open(os.path.join(a.work, "keep_ranges.json"), "w"))
    json.dump(words_cut, open(os.path.join(a.work, "words_cut.json"), "w"), ensure_ascii=False)
    print(f"reordered {len(reordered)} pieces; new opening word: {words_cut[0]['word']!r}")

    if a.assemble:
        # swap the first two pieces of the EXISTING base_cut.mp4 (no raw source).
        d0 = ranges[0][1] - ranges[0][0]           # "In the next few minutes" duration
        d1 = ranges[1][1] - ranges[1][0]           # "These are real businesses" duration
        b0, b1 = round(d0, 4), round(d0 + d1, 4)
        src = os.path.join(a.work, "base_cut.mp4")
        orig = os.path.join(a.work, "base_cut_orig.mp4")
        if not os.path.exists(orig):
            os.replace(src, orig)                  # keep the original safe, once
        out = src
        fc = (
            f"[0:v]trim={b0}:{b1},setpts=PTS-STARTPTS[v0];"
            f"[0:a]atrim={b0}:{b1},asetpts=PTS-STARTPTS[a0];"
            f"[0:v]trim=0:{b0},setpts=PTS-STARTPTS[v1];"
            f"[0:a]atrim=0:{b0},asetpts=PTS-STARTPTS[a1];"
            f"[0:v]trim={b1},setpts=PTS-STARTPTS[v2];"
            f"[0:a]atrim={b1},asetpts=PTS-STARTPTS[a2];"
            f"[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]"
        )
        fcfile = os.path.join(a.work, "fc_reorder.txt")
        open(fcfile, "w").write(fc)
        print(f"swapping base_cut pieces at {b0}s / {b1}s ...")
        r = subprocess.run([FF, "-y", "-i", orig, "-filter_complex_script", fcfile,
                            "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast",
                            "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", out],
                           capture_output=True, text=True)
        print("FFMPEG ERROR:\n" + r.stderr[-1800:] if r.returncode else "wrote " + out)


if __name__ == "__main__":
    main()
