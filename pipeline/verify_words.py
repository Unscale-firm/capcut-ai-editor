"""
Seam verifier: prove no word got clipped by a cut.

Re-transcribes the ASSEMBLED audio (base_cut.mp4 — the actual thing that ships) with Whisper and
diffs it against the words the cut was supposed to keep (words_cut.json).
  - expected word missing / mangled at a seam                    -> CLIPPED  (FAIL)
  - unexpected word heard at a seam that sits ON speech energy    -> PARTIAL  (FAIL: sliced a word)
  - unexpected word heard at a QUIET seam, and it is the neighbouring source word -> the cut sits
    in real silence past it, so the word is audibly whole; Whisper had only mis-timed it.
    words_cut.json is repaired (word added with its heard timing) so the caption shows it.
  - unexpected word heard at a QUIET seam that Whisper never listed -> EXTRA (warning: a whole word
    the transcript missed; caption added — editor decides if it dangles; use a hard edge `t!` in
    refine_cut.py --ranges to force the cut before it)
Also checks the waveform at every seam: a cut landing on speech energy is flagged "on-speech".

Run:  venv/bin/python pipeline/verify_words.py --work work_cut            (exit 1 on FAIL)
      venv/bin/python pipeline/verify_words.py --work work_cut --audio some.mp4
"""
import os, sys, re, json, argparse, subprocess
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(__file__))
from seams import Envelope, load_pcm, seam_times, FF, SR
from sync_transcribe import NAMES_HINT
import ad_names

TOL = 0.5
FILLERS = {"um", "uh", "uhh", "umm", "erm", "hmm", "mmm", "ah", "uhm"}


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())


def transcribe(path, model_name):
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(model_name, device="cuda", compute_type="float16")
    except Exception as e:  # no CUDA runtime -> CPU
        print(f"  (cuda unavailable: {str(e)[:80]} -> cpu)")
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(path, language="en", word_timestamps=True, vad_filter=False,
                               condition_on_previous_text=False, initial_prompt=NAMES_HINT)
    out = []
    for s in segs:
        for w in (s.words or []):
            out.append({"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word.strip()})
    return out


def nearest_seam(t, seams):
    return min((abs(t - s) for s in seams), default=999.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--audio", default=None, help="override: file to verify (default work/base_cut.mp4)")
    ap.add_argument("--model", default="large-v3")
    ap.add_argument("--tol", type=float, default=TOL, help="seconds around a seam that count as 'at the seam'")
    a = ap.parse_args()

    audio = a.audio or os.path.join(a.work, "base_cut.mp4")
    assert os.path.exists(audio), f"nothing to verify: {audio}"
    wc_path = os.path.join(a.work, "words_cut.json")
    expected = json.load(open(wc_path, encoding="utf-8"))
    source = json.load(open(os.path.join(a.work, "words.json"), encoding="utf-8"))
    ranges = json.load(open(os.path.join(a.work, "keep_ranges.json")))
    seams = seam_times(ranges)
    # source words NOT in the cut that sit right at a range edge (Whisper may have mis-timed them)
    kept_mid = {(round((w["start"] + w["end"]) / 2, 3)) for w in source
                if any(x <= (w["start"] + w["end"]) / 2 <= y for x, y in ranges)}
    def edge_words_at(seam):
        """source words (not in the cut) hugging the two range edges that meet at this seam"""
        k = seams.index(seam)
        y, x = ranges[k][1], ranges[k + 1][0]           # tail of the piece before, head of the piece after
        out = set()
        for w in source:
            if round((w["start"] + w["end"]) / 2, 3) in kept_mid:
                continue
            if (w["start"] <= y + 0.6 and w["end"] >= y - 0.6) or (w["start"] <= x + 0.6 and w["end"] >= x - 0.6):
                out.add(norm(w["word"]))
        return out

    wav = os.path.join(a.work, "_verify_16k.wav")
    subprocess.run([FF, "-y", "-v", "error", "-i", audio, "-vn", "-ac", "1", "-ar", str(SR), wav], check=True)
    print(f"verifying {os.path.basename(audio)}: {len(seams)} seams, {len(expected)} expected words, whisper {a.model}")
    heard = transcribe(wav, a.model)
    json.dump(heard, open(os.path.join(a.work, "words_heard.json"), "w"), ensure_ascii=False)
    # same proper-noun dictionary on both sides so Amin/McKenzie/430 are not reported as mismatches
    expected = ad_names.fix(expected, tag="expected")
    heard = ad_names.fix(heard, tag="heard")

    env = Envelope(load_pcm(wav))
    exp_tok = [norm(w["word"]) for w in expected]
    hrd_tok = [norm(w["word"]) for w in heard]
    sm = SequenceMatcher(None, exp_tok, hrd_tok, autojunk=False)
    fails, notes, repaired, repaired_msgs, extras = [], [], [], [], []
    for op, i0, i1, j0, j1 in sm.get_opcodes():
        if op == "equal":
            continue
        e_words, h_words = expected[i0:i1], heard[j0:j1]
        e_txt = " ".join(w["word"] for w in e_words) or "-"
        h_txt = " ".join(w["word"] for w in h_words) or "-"
        if op == "replace" and SequenceMatcher(None, " ".join(exp_tok[i0:i1]), " ".join(hrd_tok[j0:j1])).ratio() >= 0.8:
            continue                                   # spelling / punctuation variance
        if op == "insert" and all(t in FILLERS for t in hrd_tok[j0:j1]):
            continue                                   # a breath Whisper heard as "um"
        t = e_words[0]["start"] if e_words else h_words[0]["start"]
        d = nearest_seam(t, seams)
        line = f"{t:7.2f}s  expected «{e_txt}»  heard «{h_txt}»  (seam {d:.2f}s away)"
        if d > a.tol:
            notes.append(line); continue
        if op == "insert":
            seam = min(seams, key=lambda x: abs(x - t))
            if not env.is_quiet_at(seam, 0.015):
                fails.append("PARTIAL  " + line)       # cut sits on speech and a stray word is heard
            elif all(tok in edge_words_at(seam) for tok in hrd_tok[j0:j1]):
                repaired.extend(h_words)               # whole neighbour word audibly inside the cut
                repaired_msgs.append(f"{t:7.2f}s  heard «{h_txt}» — neighbour word restored by the silence snap; caption added")
            else:
                repaired.extend(h_words)               # whole word the transcript never listed
                extras.append(f"{t:7.2f}s  heard «{h_txt}» — not in words.json; whole (seam is silent); caption added. Dangling? force the cut with a hard edge.")
            continue
        fails.append("CLIPPED  " + line)

    # seam energy: a cut point sitting on speech means we sliced into a word
    exp_sorted = sorted(expected, key=lambda w: w["start"])
    print("\n--- seams ---")
    for k, s in enumerate(seams, 1):
        before = next((w["word"] for w in reversed(exp_sorted) if w["end"] <= s + 0.05), "")
        after = next((w["word"] for w in exp_sorted if w["start"] >= s - 0.05), "")
        hot = not env.is_quiet_at(s, 0.015)
        bad = next((f.split()[0] for f in fails if abs(float(f.split()[1].rstrip("s")) - s) <= a.tol), None)
        rep = any(abs(w["start"] - s) <= a.tol for w in repaired)
        ext = any(abs(float(e.split()[0].rstrip("s")) - s) <= a.tol for e in extras)
        flag = bad or ("EXTRA-word" if ext else ("caption-repaired" if rep else ("on-speech" if hot else "ok")))
        print(f"  {k:2d} {s:7.2f}s  …{before} | {after}…  {flag}")

    if repaired:
        os.replace(wc_path, wc_path.replace(".json", ".preverify.json"))
        merged = sorted(expected + repaired, key=lambda w: w["start"])
        json.dump(merged, open(wc_path, "w"), ensure_ascii=False)
        print("\n--- captions repaired (words_cut.json updated, old copy in words_cut.preverify.json) ---")
        for m in repaired_msgs:
            print("  " + m)
    if extras:
        print("\n--- WARNING: whole words at seams that words.json never listed ---")
        for e in extras:
            print("  " + e)
    if notes:
        print("\n--- differences away from seams (transcription variance, info only) ---")
        for n in notes:
            print("  " + n)
    if fails:
        print("\n--- FAIL: word damage at seams ---")
        for f in fails:
            print("  " + f)
        print(f"\nVERDICT: FAIL ({len(fails)} seam problem(s))")
        sys.exit(1)
    print(f"\nVERDICT: PASS — all {len(seams)} seams clean, every expected word heard"
          + (f" ({len(extras)} extra-word warning(s) to eyeball)" if extras else ""))


if __name__ == "__main__":
    main()
