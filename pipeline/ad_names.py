"""
Proper-noun fixes for the ADS (not the VSL — that list is caption_fixes.CORRECTIONS and carries
VSL-only word swaps like expandable->expendable that must NOT touch an ad).

Whisper mangles the founder's intro in nearly every ad. Every entry below was seen in a real
work_*/words*.json (surveyed 2026-09-02 across 84 work dirs). Sequence match is case/punctuation
insensitive (caption_fixes._norm strips everything but [a-z0-9]), so "-McKenzie" == "mckenzie".
Longer / more specific sequences must come first: apply() takes the first rule that matches.

Names locked by the founder: AMINE, McKinsey, Unscale, Forbes 30 Under 30.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caption_fixes

# bare "430" / "z430" only mean "Forbes 30" right after the McKinsey intro — a real "$430" is never touched
_FORBES_CTX = {"mckinsey", "mckenzie", "xmikin", "consultant"}
_after_mckinsey = lambda prev: bool(_FORBES_CTX & set(prev))

AD_CORRECTIONS = [
    # ---- "my name is Amine, I'm an ex-McKinsey ..." ----
    (["aminam", "and", "x", "mckinsey"],   ["Amine,", "an", "ex-McKinsey"]),   # f03 f05 s4
    (["aminam", "and", "ex", "mckinsey"],  ["Amine,", "an", "ex-McKinsey"]),   # f11 s5
    (["aminam"],                           ["Amine"]),
    (["amina"],                            ["Amine"]),                         # f14 f18 f20 f19
    (["amin"],                             ["Amine"]),                         # everywhere
    # ---- ex-McKinsey ----
    (["ex", "mckinsey", "for", "the", "30"],       ["ex-McKinsey", "Forbes", "30"]),                 # f09 f11
    (["ex", "mckinsey", "for", "up", "3030"],      ["ex-McKinsey", "Forbes", "30", "under", "30"]),  # f11 s5
    (["ex", "mckinsey", "for", "up", "30", "on", "a", "30"],
                                                   ["ex-McKinsey", "Forbes", "30", "under", "30"]),  # f10t
    (["ex", "mckinsey", "for", "absurdity", "im", "a", "30"],
                                                   ["ex-McKinsey", "Forbes", "30", "under", "30"]),  # f10
    (["xmikin", "z430", "on", "the", "30"],        ["ex-McKinsey", "Forbes", "30", "under", "30"]),  # f11 s5
    (["xmikin"],                                   ["ex-McKinsey"]),
    (["x", "mckinsey"],                            ["ex-McKinsey"]),
    (["x", "mckenzie"],                            ["ex-McKinsey"]),
    (["ex", "mckinsey"],                           ["ex-McKinsey"]),           # "ex -McKinsey" split token
    (["ex", "mckenzie"],                           ["ex-McKinsey"]),           # f20
    (["mckenzies"],                                ["McKinsey's"]),
    (["mckenzie"],                                 ["McKinsey"]),
    # ---- Forbes 30 Under 30 ----
    (["z430", "30", "the", "under", "30"],         ["Forbes", "30", "under", "30"]),  # f07
    (["z430"],                                     ["Forbes", "30"], _after_mckinsey),
    (["430", "on", "the", "30"],                   ["Forbes", "30", "under", "30"]),  # f01 f03 f05 f14 f20 ...
    (["430"],                                      ["Forbes", "30"], _after_mckinsey),  # "…consultant, 430, and I"
    (["forbes", "3030"],                           ["Forbes", "30", "under", "30"]),  # f01 f03 f05 s4
    (["3030"],                                     ["30", "under", "30"]),
    (["forbes", "on", "the", "30"],                ["Forbes", "30", "under", "30"]),
    (["forbes", "under", "30"],                    ["Forbes", "30", "under", "30"]),
    (["30", "on", "the", "30"],                    ["30", "under", "30"]),
    (["30", "under", "the", "30"],                 ["30", "under", "30"]),
    (["the", "fourth", "brand"],                   ["the", "Forbes", "brand"]),     # f01 f03 f04 f05 s4
    # ---- Unscale ----
    (["un", "scale"],                              ["Unscale"]),
    (["unskilled"],                                ["Unscale"]),                    # f06 f09 …
    (["unscaled"],                                 ["Unscale"]),                    # "Unscale partner(s)"
    (["onscale"],                                  ["Unscale"]),                    # f03 s5
    # NOTE: "unscaling" is a real word he uses ("the art of unscaling") — left alone on purpose.
]


def fix(words, tag=None, out=sys.stdout):
    """Return a corrected copy of a [{start,end,word}] list, printing one line per replacement:
         fixed: 'Amin' -> 'Amine' at 12.34s"""
    pre = f"[{tag}] " if tag else ""
    def log(found, repl, t):
        print(f"  {pre}fixed: '{found}' -> '{repl}' at {t:.2f}s", file=out)
    return caption_fixes.apply(words, rules=AD_CORRECTIONS, log=log)


if __name__ == "__main__":   # quick check:  python ad_names.py work_x/words_cut.json
    import json
    w = json.load(open(sys.argv[1], encoding="utf-8"))
    fixed = fix(w)
    print(" ".join(x["word"] for x in fixed)[:600])
