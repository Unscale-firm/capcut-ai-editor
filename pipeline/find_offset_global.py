"""Global camera->mic offset: correlate the FULL amplitude envelopes with no lag window.
The per-window search fails when the camera rolled minutes before the recorder — the true
lag sits far outside any narrow max_lag. Envelopes (not raw audio) so the two very different
mics still correlate. Then re-verify the winner at several windows."""
import os, wave, argparse
import numpy as np

SR = 16000
DS = 100          # envelope sample rate (Hz)


def load(p):
    with wave.open(p, "rb") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    return a - a.mean()


def envelope(x):
    k = SR // DS
    n = (len(x) // k) * k
    e = np.sqrt((x[:n] ** 2).reshape(-1, k).mean(axis=1))
    e = np.log1p(e)               # compress — loud peaks shouldn't dominate
    return e - e.mean()


def global_offset(cam, mic):
    a, b = envelope(cam), envelope(mic)
    n = 1
    while n < len(a) + len(b):
        n *= 2
    corr = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    corr = np.concatenate((corr[-(len(b) - 1):], corr[:len(a)]))
    lags = np.arange(-(len(b) - 1), len(a))
    i = np.argmax(corr)
    conf = corr[i] / (np.abs(corr).mean() + 1e-9)
    return lags[i] / DS, conf


def verify(cam, mic, off):
    """With the offset applied, how well does each 60s window line up?"""
    out = []
    for t in (120, 400, 700, 1000, 1300, 1600):
        s_m, s_c = int(t * SR), int((t + off) * SR)
        w = 60 * SR
        if s_c < 0 or s_c + w > len(cam) or s_m + w > len(mic):
            out.append((t, None))
            continue
        a = envelope(cam[s_c:s_c + w])
        b = envelope(mic[s_m:s_m + w])
        n = 1
        while n < len(a) + len(b):
            n *= 2
        corr = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
        corr = np.concatenate((corr[-(len(b) - 1):], corr[:len(a)]))
        lags = np.arange(-(len(b) - 1), len(a))
        m = np.abs(lags) <= 5 * DS          # residual should be tiny
        peak = corr[m]
        out.append((t, lags[m][np.argmax(peak)] / DS))
    return out


ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work_vsl")
a = ap.parse_args()

mic = load(os.path.join(a.work, "audio_mic.wav"))
res = {}
for name in ("front", "side"):
    cam = load(os.path.join(a.work, f"audio_{name}.wav"))
    off, conf = global_offset(cam, mic)
    print(f"\n=== {name} ===   cam {len(cam)/SR:.0f}s   mic {len(mic)/SR:.0f}s")
    print(f"  GLOBAL offset = {off:+.2f}s   (confidence {conf:.1f})")
    print("  residual per window (should be ~0.00):")
    for t, r in verify(cam, mic, off):
        print(f"    t={t:>5}s  ->  {('%+.2f s' % r) if r is not None else 'out of range'}")
    res[name] = round(float(off), 3)

print("\noffsets:", res)
import json
json.dump(res, open(os.path.join(a.work, "offsets.json"), "w"))
print("wrote", os.path.join(a.work, "offsets.json"))
