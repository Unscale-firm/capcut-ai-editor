"""Print word-level timings for given segment indices (1-based), to find in-sentence cut points."""
import json, argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cut_heuristic import segments

ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work_vsl")
ap.add_argument("--segs", required=True, help="e.g. 1,115,142")
a = ap.parse_args()

words = json.load(open(os.path.join(a.work, "words.json"), encoding="utf-8"))
segs = segments(words)
for i in [int(x) for x in a.segs.split(",")]:
    print(f"\n=== seg {i} ===")
    for w in segs[i - 1]:
        print(f'  {w["start"]:8.2f} {w["end"]:8.2f}  {w["word"]}')
