"""Find the time offset between a reference audio and one or more media files,
by FFT cross-correlation of their waveforms. Used to sync two camera angles to the
clean master audio.

offset > 0 means: reference_time = media_time + offset
(i.e. the media started recording `offset` seconds AFTER the reference).
"""
import subprocess, sys, wave, tempfile, os
from pathlib import Path
import numpy as np

# ffmpeg: PATH first, else the winget install location
_WINGET = Path(r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
               r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe'
               r'\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FFMPEG = 'ffmpeg' if subprocess.run(['where', 'ffmpeg'], capture_output=True).returncode == 0 else str(_WINGET)

SR = 8000        # resample everything to 8 kHz mono
DUR = 540        # only need the first ~9 min to find the offset


def extract(src, sr=SR, dur=DUR):
    tmp = Path(tempfile.gettempdir()) / (Path(src).stem + f'_{sr}.wav')
    subprocess.run([FFMPEG, '-y', '-vn', '-i', src, '-ac', '1', '-ar', str(sr),
                    '-t', str(dur), '-acodec', 'pcm_s16le', str(tmp)],
                   check=True, capture_output=True)
    w = wave.open(str(tmp), 'rb')
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)
    w.close()
    return a


def offset_seconds(ref, sig, sr=SR):
    """Lag (s) to ADD to sig's time to match ref's time, + a 0..1 confidence."""
    r = ref - ref.mean()
    s = sig - sig.mean()
    n = len(r) + len(s) - 1
    N = 1 << (n - 1).bit_length()
    corr = np.fft.irfft(np.fft.rfft(r, N) * np.conj(np.fft.rfft(s, N)), N)
    idx = int(np.argmax(corr))
    if idx > N // 2:
        idx -= N
    conf = float(corr.max() / (np.linalg.norm(r) * np.linalg.norm(s) + 1e-9))
    return idx / sr, conf


if __name__ == '__main__':
    ref_path = sys.argv[1]
    media = sys.argv[2:]
    print(f'ffmpeg: {FFMPEG}')
    print(f'reference: {Path(ref_path).name}')
    ref = extract(ref_path)
    for m in media:
        sig = extract(m)
        off, conf = offset_seconds(ref, sig)
        print(f'  {Path(m).name:22}  offset = {off:+.3f}s   confidence = {conf:.3f}')
