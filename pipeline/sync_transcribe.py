"""
Stage 1 of the ad machine: SYNC (audio cross-correlation) + TRANSCRIBE (Whisper).

Takes: front video, side video, clean mic wav.
Produces (in --work dir):
  audio_front.wav, audio_side.wav, audio_mic.wav   (16k mono)
  offsets.json   {front, side}  seconds the camera audio lags the mic (mic is the master clock)
  words.json     [{start,end,word}, ...]  word-level transcript from the mic

Run:
  venv/Scripts/python.exe pipeline/sync_transcribe.py \
    --front <front.mp4> --side <side.mp4> --mic <mic.wav> --work work_cut
"""
import os, sys, json, subprocess, argparse, wave
import numpy as np

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
SR = 16000

def extract_audio(src, dst):
    if os.path.exists(dst):
        print("  cached", os.path.basename(dst)); return
    subprocess.run([FF, "-y", "-i", src, "-vn", "-ac", "1", "-ar", str(SR), "-f", "wav", dst],
                   capture_output=True)
    print("  extracted", os.path.basename(dst))

def load_wav(path):
    with wave.open(path, "rb") as w:
        n = w.getnframes()
        a = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32)
    a -= a.mean()
    return a

def find_offset(cam, mic, max_lag_s=30):
    """Lag (seconds) that cam lags mic, via FFT cross-correlation on a middle window."""
    win = SR * 90
    c0 = min(len(cam), len(mic))
    s = max(0, c0 // 2 - win // 2)
    a = cam[s:s + win]; b = mic[s:s + win]
    n = 1
    while n < len(a) + len(b):
        n *= 2
    A = np.fft.rfft(a, n); B = np.fft.rfft(b, n)
    corr = np.fft.irfft(A * np.conj(B), n)
    corr = np.concatenate((corr[-(len(b) - 1):], corr[:len(a)]))
    lags = np.arange(-(len(b) - 1), len(a))
    m = np.abs(lags) <= max_lag_s * SR
    best = lags[m][np.argmax(corr[m])]
    return best / SR

def transcribe(mic_wav, out_json):
    if os.path.exists(out_json):
        print("  cached words.json"); return json.load(open(out_json))
    from faster_whisper import WhisperModel
    print("  loading whisper (base)...")
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(mic_wav, language="en", word_timestamps=True, vad_filter=True)
    words = []
    for s in segs:
        for w in (s.words or []):
            words.append({"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word.strip(),
                          "p": round(getattr(w, "probability", 1.0), 3)})
    json.dump(words, open(out_json, "w"), ensure_ascii=False)
    print(f"  transcribed {len(words)} words")
    return words

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--front", required=True)
    ap.add_argument("--side", required=True)
    ap.add_argument("--mic", required=True)
    ap.add_argument("--work", default="work_cut")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    af = os.path.join(a.work, "audio_front.wav")
    asd = os.path.join(a.work, "audio_side.wav")
    am = os.path.join(a.work, "audio_mic.wav")

    print("[1/3] extracting audio...")
    extract_audio(a.front, af); extract_audio(a.side, asd); extract_audio(a.mic, am)
    # full-quality mic (48k mono) aligned to audio_mic — used for the FINAL cut audio (not the 16k copy)
    mhq = os.path.join(a.work, "mic_hq.wav")
    if not os.path.exists(mhq):
        subprocess.run([FF, "-y", "-i", a.mic, "-vn", "-ac", "1", "-ar", "48000",
                        "-c:a", "pcm_s24le", mhq], capture_output=True)
        print("  extracted mic_hq.wav (48k)")

    print("[2/3] syncing (cross-correlation)...")
    mic = load_wav(am)
    off = {"front": round(find_offset(load_wav(af), mic), 3),
           "side": round(find_offset(load_wav(asd), mic), 3)}
    json.dump(off, open(os.path.join(a.work, "offsets.json"), "w"))
    print("  offsets (sec cam lags mic):", off)

    print("[3/3] transcribing mic with Whisper...")
    words = transcribe(am, os.path.join(a.work, "words.json"))
    print("DONE. first words:", " ".join(w["word"] for w in words[:14]))

if __name__ == "__main__":
    main()
