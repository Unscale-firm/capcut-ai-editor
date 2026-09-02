"""
Seam snapping: move every cut point off the Whisper word timestamp and onto real silence.

Whisper word boundaries are ~50-150 ms rough, so a cut placed at `word.end + PAD` regularly
slices into the word (or into the first word of the take being dropped). This module reads the
mic waveform and, for each keep range:
  1. widens the range to cover the words it actually holds (midpoint rule, Whisper-safe)
  2. scans OUTWARD from the first/last word for the nearest run of real silence and cuts there,
     plus a small breathing margin
  3. never crosses into a dropped neighbour word (word-level guard), never overlaps another range

Library use:
    from seams import snap_ranges, words_on_timeline, mic_wav_for
CLI (dry run, show before/after for a work dir):
    venv/bin/python pipeline/seams.py --work work_f10t
"""
import os, json, wave, argparse, subprocess
import numpy as np

FF = "ffmpeg"
SR = 16000
HOP = 0.005          # envelope hop (s)
RUN = 0.15           # this much continuous quiet = a real gap (shorter dips are stop closures INSIDE words)
MAXPAD = 0.45        # how far past the Whisper boundary we look for silence
MINPAD = 0.03        # fallback pad when no silence exists (words butted together)
GUARD = 0.03         # never come this close to a dropped word
SLOP = 0.25          # Whisper may place a neighbour word this far off; the waveform decides inside it
START_EXTRA = 0.15   # margin kept BEFORE the first word (soft onsets are fragile)
END_EXTRA = 0.12     # margin kept AFTER the last word (quiet fricative tails: "face", "us")
THRESH_ABOVE_FLOOR = 12.0   # dB above the room floor = still speech
SMOOTH = 0.025       # envelope smoothing window (s) — kills frame-to-frame flicker at word tails


def mic_wav_for(work):
    """16k mono wav of the mic in `work` (decodes mic_hq.wav if the 16k copy is missing)."""
    p16 = os.path.join(work, "audio_mic.wav")
    if os.path.exists(p16):
        return p16
    hq = os.path.join(work, "mic_hq.wav")
    if not os.path.exists(hq):
        raise FileNotFoundError(f"no audio_mic.wav / mic_hq.wav in {work}")
    subprocess.run([FF, "-y", "-i", hq, "-ac", "1", "-ar", str(SR), p16], capture_output=True, check=True)
    return p16


def load_pcm(path):
    """Any audio file -> float32 mono 16k."""
    if path.lower().endswith(".wav"):
        try:
            with wave.open(path, "rb") as w:
                if w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2:
                    return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        except wave.Error:
            pass
    r = subprocess.run([FF, "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.int16).astype(np.float32)


class Envelope:
    """dBFS RMS envelope at HOP resolution + a speech/quiet threshold derived from the file."""
    def __init__(self, pcm):
        k = int(SR * HOP)
        n = (len(pcm) // k) * k
        power = (pcm[:n] ** 2).reshape(-1, k).mean(axis=1)
        m = max(1, int(round(SMOOTH / HOP)))
        power = np.convolve(power, np.ones(m) / m, mode="same")
        self.db = 10 * np.log10(power / (32768.0 ** 2) + 1e-18)
        self.dur = n / SR
        live = self.db[self.db > -100]              # ignore digital silence (padding)
        floor = float(np.percentile(live, 10)) if len(live) else -70.0
        self.thresh = float(min(max(floor + THRESH_ABOVE_FLOOR, -70.0), -45.0))
        self.quiet = self.db < self.thresh
        self.run = max(1, int(round(RUN / HOP)))

    def idx(self, t):
        return int(min(max(t, 0.0), self.dur) / HOP)

    def quietest(self, t0, t1):
        """Time of the lowest-energy 15 ms in [t0, t1], or None if the window is empty."""
        i0, i1 = self.idx(t0), self.idx(t1)
        if i1 - i0 < 3:
            return None
        seg = self.db[i0:i1]
        sm = np.convolve(seg, np.ones(3) / 3, mode="same")
        j = int(np.argmin(sm))
        return (i0 + j) * HOP, float(sm[j])

    def is_quiet_at(self, t, half=0.01):
        i0, i1 = self.idx(t - half), self.idx(t + half) + 1
        return bool(self.quiet[i0:i1].all()) if i1 > i0 else True

    def first_gap_after(self, t, limit):
        """First quiet run starting in [t, limit] as (q0, q1) seconds, or None. q1 may exceed limit."""
        i, end = self.idx(t), self.idx(limit) + self.run     # the run must START inside the limit
        cnt = 0
        while i <= end and i < len(self.quiet):
            cnt = cnt + 1 if self.quiet[i] else 0
            if cnt >= self.run:
                q0 = i - self.run + 1
                j = i
                while j + 1 < len(self.quiet) and self.quiet[j + 1]:
                    j += 1
                return q0 * HOP, (j + 1) * HOP
            i += 1
        return None

    def last_gap_before(self, t, limit):
        """Last quiet run ending in [limit, t] as (q0, q1) seconds, or None. q0 may precede limit."""
        i, end = self.idx(t) - 1, self.idx(limit) - self.run  # the run must END inside the limit
        cnt = 0
        while i >= end and i >= 0:
            cnt = cnt + 1 if self.quiet[i] else 0
            if cnt >= self.run:
                q1 = i + self.run
                j = i
                while j - 1 >= 0 and self.quiet[j - 1]:
                    j -= 1
                return j * HOP, q1 * HOP
            i -= 1
        return None


def _mid(w):
    return (w["start"] + w["end"]) / 2


HARD_SLACK = 0.05    # a hard edge (`t!` in refine_cut --ranges) may move at most this much outward


def snap_ranges(ranges, words, mic_wav, verbose=False, hard=None):
    """ranges: [[a,b],...] in mic seconds (word-boundary based). Returns snapped, merged ranges.
    hard: optional list of (head_is_hard, tail_is_hard) per range — a hard edge is trusted as given
    (only widened to the word it already holds, then at most HARD_SLACK outward)."""
    env = Envelope(load_pcm(mic_wav))
    words = sorted(words, key=lambda w: w["start"])
    hard = hard or [(False, False)] * len(ranges)
    order = sorted(range(len(ranges)), key=lambda i: ranges[i])
    out = []
    for i in order:
        a, b = ranges[i]
        h_head, h_tail = hard[i]
        mine = [w for w in words if a - 0.05 <= _mid(w) <= b + 0.05]
        if mine:
            a, b = min(a, mine[0]["start"]), max(b, mine[-1]["end"])
        others = [w for w in words if w not in mine]
        prev_end = max([w["end"] for w in others if w["end"] <= a + 0.02] or [0.0])
        next_start = min([w["start"] for w in others if w["start"] >= b - 0.02] or [env.dur])

        # search bounds: how far we may look. Whisper's neighbour timestamps only BOUND the
        # search (with SLOP); the waveform decides where the actual silence is.
        lo_lim = max(0.0, a - MAXPAD, prev_end - SLOP)
        hi_lim = min(env.dur, b + MAXPAD, next_start + SLOP)
        if h_head:
            lo_lim = max(lo_lim, a - HARD_SLACK)
        if h_tail:
            hi_lim = min(hi_lim, b + HARD_SLACK)

        g = env.last_gap_before(a, lo_lim)
        if g is not None:
            q0, q1 = g                                   # quiet run just before the first word
            lo = max(q1 - START_EXTRA, q0 + GUARD, lo_lim)
        else:                                            # run-on speech: take the quietest dip
            q = env.quietest(max(lo_lim, prev_end - GUARD, a - 0.2), a)
            lo = q[0] if q and q[1] < env.thresh + 6 else max(lo_lim, prev_end + GUARD, a - MINPAD)
        g2 = env.first_gap_after(b, hi_lim)
        if g2 is not None:
            q0, q1 = g2                                  # quiet run just after the last word
            hi = min(q0 + END_EXTRA, q1 - GUARD, hi_lim)
        else:                                            # run-on speech: take the quietest dip
            q = env.quietest(b, min(hi_lim, next_start + GUARD, b + 0.2))
            hi = q[0] if q and q[1] < env.thresh + 6 else min(hi_lim, next_start - GUARD, b + MINPAD)
        lo, hi = min(lo, a), max(hi, b)          # never tighter than the words themselves
        if verbose:
            print(f"  [{a:8.2f}-{b:8.2f}] -> [{lo:8.2f}-{hi:8.2f}]  head {'gap' if g is not None else 'NO-GAP'} "
                  f"{a-lo:+.2f}s  tail {'gap' if g2 is not None else 'NO-GAP'} {hi-b:+.2f}s"
                  f"{'' if env.is_quiet_at(lo) else '  !head-on-speech'}{'' if env.is_quiet_at(hi) else '  !tail-on-speech'}")
        out.append([round(lo, 3), round(hi, 3)])
    # merge touching / overlapping
    merged = []
    for a, b in out:
        if merged and a - merged[-1][1] < 0.02:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def words_on_timeline(ranges, words):
    """words_cut.json entries: every word whose midpoint sits in a range, retimed to the cut."""
    out, t_out = [], 0.0
    for a, b in ranges:
        for w in words:
            if a <= _mid(w) <= b:
                ns = t_out + (w["start"] - a)
                out.append({"start": round(ns, 3), "end": round(ns + (w["end"] - w["start"]), 3),
                            "word": w["word"]})
        t_out += (b - a)
    return out


def seam_times(ranges):
    """Output-timeline seam positions (end of every piece but the last)."""
    t, seams = 0.0, []
    for a, b in ranges[:-1]:
        t += (b - a); seams.append(round(t, 3))
    return seams


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="dry-run: show how keep_ranges.json would snap")
    ap.add_argument("--work", required=True)
    a = ap.parse_args()
    words = json.load(open(os.path.join(a.work, "words.json"), encoding="utf-8"))
    kr = json.load(open(os.path.join(a.work, "keep_ranges.json")))
    print(f"{len(kr)} ranges, snapping against {mic_wav_for(a.work)}")
    snapped = snap_ranges(kr, words, mic_wav_for(a.work), verbose=True)
    print(f"-> {len(snapped)} ranges after merge")
