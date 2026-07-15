"""Dump every speech segment with index, times, gaps and full text — the editor's worksheet."""
import json, argparse, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cut_heuristic import segments, text

ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work_vsl")
a = ap.parse_args()

words = json.load(open(os.path.join(a.work, "words.json"), encoding="utf-8"))
segs = segments(words)
out = []
for i, s in enumerate(segs):
    pg = s[0]["start"] - segs[i - 1][-1]["end"] if i else 0.0
    conf = sum(w.get("p", 1.0) for w in s) / max(1, len(s))
    out.append({
        "i": i + 1,
        "start": round(s[0]["start"], 1),
        "end": round(s[-1]["end"], 1),
        "dur": round(s[-1]["end"] - s[0]["start"], 1),
        "gap_before": round(pg, 1),
        "nwords": len(s),
        "conf": round(conf, 2),
        "text": text(s),
    })
json.dump(out, open(os.path.join(a.work, "segs.json"), "w"), ensure_ascii=False, indent=1)
for o in out:
    print(f'{o["i"]:>3} [{o["start"]:>7.1f}-{o["end"]:>7.1f}] gap{o["gap_before"]:>5.1f} c{o["conf"]:.2f} :: {o["text"]}')
