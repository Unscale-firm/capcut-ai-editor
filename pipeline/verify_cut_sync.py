"""Prove the finished cut is in sync: rebuild the same EDL from the CAMERA'S OWN audio
(which is glued to its own picture) and correlate it against the mic track that is actually
in base_cut.mp4. If the picture matches the sound, the residual is ~0 at every point."""
import os, json, wave, subprocess, argparse
import numpy as np

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"  # non-Windows: use ffmpeg from PATH
SR, DS = 16000, 100

ap = argparse.ArgumentParser()
ap.add_argument("--work", default="work_vsl")
a = ap.parse_args()

ranges = json.load(open(os.path.join(a.work, "keep_ranges.json")))
off = json.load(open(os.path.join(a.work, "offsets.json")))["front"]

# camera audio cut with the SAME ranges, shifted by the offset (i.e. what the picture "says")
cam_cut = os.path.join(a.work, "_camtrack.wav")
fc = "".join(f"[0:a]atrim=start={x+off:.3f}:end={y+off:.3f},asetpts=PTS-STARTPTS[a{i}];"
             for i, (x, y) in enumerate(ranges))
fc += "".join(f"[a{i}]" for i in range(len(ranges))) + f"concat=n={len(ranges)}:v=0:a=1[a]"
f = os.path.join(a.work, "_fc_v.txt"); open(f, "w").write(fc)
subprocess.run([FF, "-y", "-i", os.path.join(a.work, "audio_front.wav"),
                "-filter_complex_script", f, "-map", "[a]", "-ar", str(SR), cam_cut],
               capture_output=True)

# mic track as it exists inside the rendered video
mic_cut = os.path.join(a.work, "_mictrack.wav")
subprocess.run([FF, "-y", "-i", os.path.join(a.work, "base_cut.mp4"),
                "-vn", "-ac", "1", "-ar", str(SR), mic_cut], capture_output=True)


def load(p):
    with wave.open(p, "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    return x - x.mean()


def envelope(x):
    k = SR // DS
    n = (len(x) // k) * k
    e = np.sqrt((x[:n] ** 2).reshape(-1, k).mean(axis=1))
    return np.log1p(e) - np.log1p(e).mean()


cam, mic = load(cam_cut), load(mic_cut)
print(f"camera-audio cut {len(cam)/SR:.1f}s   mic track in video {len(mic)/SR:.1f}s\n")
print("residual A/V offset through the finished cut (0.00 = perfectly lip-synced):")
bad = 0
for t in (10, 120, 300, 500, 700, 900, 1100, 1250):
    s, w = int(t * SR), int(45 * SR)
    if s + w > min(len(cam), len(mic)):
        continue
    x, y = envelope(cam[s:s + w]), envelope(mic[s:s + w])
    n = 1
    while n < len(x) + len(y):
        n *= 2
    c = np.fft.irfft(np.fft.rfft(x, n) * np.conj(np.fft.rfft(y, n)), n)
    c = np.concatenate((c[-(len(y) - 1):], c[:len(x)]))
    lags = np.arange(-(len(y) - 1), len(x))
    m = np.abs(lags) <= 3 * DS
    r = lags[m][np.argmax(c[m])] / DS
    flag = "OK" if abs(r) <= 0.08 else "OUT OF SYNC"
    if abs(r) > 0.08:
        bad += 1
    print(f"  {t//60:02d}:{t%60:02d}   {r:+.2f}s   {flag}")
print("\nVERDICT:", "IN SYNC end to end" if not bad else f"{bad} point(s) out of sync")
