"""Transcribe the full mic and dump segment-level transcript for ad-counting."""
import json, os, sys
from faster_whisper import WhisperModel

MIC = r"C:\Users\User\Desktop\New folder (2)\2.wav"
OUT = r"C:\Users\User\capcut-ai-editor\work\full_mic_transcript.json"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

print("loading model...", flush=True)
model = WhisperModel("base", device="cpu", compute_type="int8")
print("transcribing full mic (~59 min)...", flush=True)
segs, info = model.transcribe(MIC, language="en", vad_filter=True)
out = []
for s in segs:
    out.append({"start": round(s.start, 1), "end": round(s.end, 1), "text": s.text.strip()})
    if len(out) % 40 == 0:
        print(f"  {out[-1]['start']:.0f}s / 3521s ...", flush=True)
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(f"DONE — {len(out)} segments -> {OUT}", flush=True)
