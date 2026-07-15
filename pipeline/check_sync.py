"""Measure the camera->mic offset at several independent windows, to catch a bad
single-window correlation OR a clock drift between the camera and the recorder."""
import os, json, wave, argparse
import numpy as np

SR = 16000


def load(p):
    with wave.open(p, "rb") as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    return a - a.mean()


def env(x):
    """Amplitude envelope — robust to the two mics sounding totally different."""
    k = 400  # 25 ms
    e = np.sqrt(np.convolve(x * x, np.ones(k) / k, mode="same"))
    return e - e.mean()


def offset_at(cam, mic, t, win=60.0, max_lag=40.0):
    s = int(t * SR)
    w = int(win * SR)
    if s + w > len(cam) or s + w > len(mic):
        return None
    a, b = env(cam[s:s + w]), env(mic[s:s + w])
    n = 1
    while n < len(a) + len(b):
        n *= 2
    corr = np.fft.irfft(np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n)), n)
    corr = np.concatenate((corr[-(len(b) - 1):], corr[:len(a)]))
    lags = np.arange(-(len(b) - 1), len(a))
    m = np.abs(lags) <= max_lag * SR
    peak = corr[m]
    best = lags[m][np.argmax(peak)]
    # confidence: how much the peak beats the rest
    conf = peak.max() / (np.abs(peak).mean() + 1e-9)
    return best / SR, conf


ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work_vsl")
a = ap.parse_args()

mic = load(os.path.join(a.work, "audio_mic.wav"))
for cam_name in ("front", "side"):
    cam = load(os.path.join(a.work, f"audio_{cam_name}.wav"))
    print(f"\n=== {cam_name} (cam {len(cam)/SR:.0f}s, mic {len(mic)/SR:.0f}s) ===")
    for t in (60, 300, 600, 900, 1200, 1500, 1700):
        r = offset_at(cam, mic, t)
        if r:
            print(f"  t={t:>5}s   offset {r[0]:+8.3f}s   confidence {r[1]:5.1f}")
