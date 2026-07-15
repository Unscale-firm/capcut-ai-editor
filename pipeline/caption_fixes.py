"""
Transcription fixes for the VSL captions. Whisper misheard several proper nouns / words; these
are corrected against the v5 script (63_VSL_v5.md) before the captions are built.

apply(words) rewrites a [{start,end,word}] list in place-order, matching each rule on the
punctuation-stripped, lower-cased token sequence. Trailing punctuation on the last matched token
is carried onto the last replacement token, and timing is split evenly when the token count changes.
"""
import re

# (find sequence -> replace sequence). Match is case/punctuation-insensitive on the find side.
CORRECTIONS = [
    (["amin"],                 ["Amine"]),            # founder's name
    (["x", "mckinsey"],        ["ex-McKinsey"]),      # "ex-McKinsey", not "X McKinsey"
    (["30", "on", "the", "30"],["30", "under", "30"]),# Forbes 30 UNDER 30
    (["expandable"],           ["expendable"]),       # "you are expendable"
    (["ryan"],                 ["Rayan"]),            # his son's name
    (["cardi", "lavine"],      ["Cara", "Delevingne"]),
    (["spiralized"],           ["Spiralyze"]),        # first client
    (["unlocked"],             ["locked"]),           # "I locked myself in"
    (["unskilled"],            ["Unscale"]),          # the company is Unscale
    (["of", "our", "scale"],   ["at", "Unscale"]),    # "a partner at Unscale"
    (["metta"],                ["Meta"]),             # the company Meta
    (["reached"],              ["rich"]),             # "you'll get rich next month"
    (["defeat"],               ["to", "feed"]),       # "a family to feed"
    # --- pending the user's confirmation (real names) ---
    # (["sizemick"],           ["Seismic"]),          # recruitment case-study company
    # (["cls"],                ["sales"]),            # "not my sales team"
]

_norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())
_TRAIL = re.compile(r"[.,!?;:]+$")


def apply(words):
    out = []
    i = 0
    while i < len(words):
        hit = None
        for find, repl in CORRECTIONS:
            n = len(find)
            if i + n <= len(words) and [_norm(words[i + j]["word"]) for j in range(n)] == find:
                hit = (find, repl, n)
                break
        if not hit:
            out.append(words[i]); i += 1; continue

        find, repl, n = hit
        span = words[i:i + n]
        repl = list(repl)
        m = _TRAIL.search(span[-1]["word"])          # carry trailing punctuation
        if m and not _TRAIL.search(repl[-1]):
            repl[-1] += m.group(0)

        s, e = span[0]["start"], span[-1]["end"]
        step = (e - s) / len(repl)
        for k, tok in enumerate(repl):
            out.append({"start": round(s + k * step, 3),
                        "end": round(s + (k + 1) * step, 3),
                        "word": tok})
        i += n
    return out
