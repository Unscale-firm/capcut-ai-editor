"""
Burn the locked caption look into the finished VSL — pure ffmpeg/libass, no Remotion.

Reuses the ad pipeline's grouping + keyword logic (gen_captions.build) so the wording, line
breaks and orange keyword choice are identical to the ad look. Only the LAYOUT differs: the ad
canvas is 1080x1920 portrait, this is 1920x1080 landscape, so the captions sit in the lower
third and the type is sized against the frame HEIGHT.

Words come in on the CUT timeline; the rendered video is sped up, so every time is divided by
--speed (gen_captions.build already does this).

Run:
  venv/Scripts/python.exe pipeline/burn_captions.py --work work_vsl \
      --video C:/Users/User/Downloads/vsl-cut.mp4 --out C:/Users/User/Downloads/vsl-captioned.mp4
"""
import os, json, argparse, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
from gen_captions import build, ORANGE
from caption_fixes import apply as fix_words

FF = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
if not os.path.exists(FF):
    FF = "ffmpeg"  # non-Windows: use ffmpeg from PATH

W, H, FPS = 1920, 1080, 30
POS_X, POS_Y = W // 2, 916       # centred, lower third — clear of his hands and the desk
BOX_W = 1500
FONT = "Montserrat ExtraBold"
FONT_SIZE = 88                   # sized against frame HEIGHT; 60 read too small in landscape
SPACING = 1
OUTLINE = 4
SHADOW = 3
FADE_FRAMES = 2


def ass_colour(hex_rgb):
    h = hex_rgb.lstrip("#")
    return f"&H00{h[4:6]}{h[2:4]}{h[0:2]}&".upper()      # ASS is &HAABBGGRR


def ts(frames, fps):
    t = max(0.0, frames / fps)
    return f"{int(t//3600)}:{int((t%3600)//60):02d}:{t%60:05.2f}"


def esc(s):
    return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def to_ass(caps, fps=FPS):
    white, outline = ass_colour("#FFFFFF"), ass_colour("#3A3A3A")   # contour: dark grey, softer than black
    margin = (W - BOX_W) // 2
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},{FONT_SIZE},{white},{white},{outline},&H8C000000&,-1,0,0,0,100,100,{SPACING},0,1,{OUTLINE},{SHADOW},5,{margin},{margin},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    fade_ms = round(FADE_FRAMES / fps * 1000)
    lines = []
    for c in caps:
        parts = []
        for w in c["words"]:
            at = round(w["rel"] / fps * 1000)
            # every word holds its final position from the start (alpha only), so the line
            # never re-centres as words arrive — it just fills in as he says them.
            parts.append(f"{{\\c{ass_colour(w['c'])}\\alpha&HFF&"
                         f"\\t({at},{at+fade_ms},\\alpha&H00&)}}{esc(w['t'])}")
        lines.append(f"Dialogue: 0,{ts(c['from'],fps)},{ts(c['from']+c['dur'],fps)},Cap,,0,0,0,,"
                     f"{{\\pos({POS_X},{POS_Y})}}" + " ".join(parts))
    return head + "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work_vsl")
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--speed", type=float, default=1.15)
    ap.add_argument("--preview", default=None, help="output seconds, e.g. 95,120")
    a = ap.parse_args()

    words = json.load(open(os.path.join(a.work, "words_cut.json"), encoding="utf-8"))
    words = fix_words(words)          # correct Whisper mishears (Amine, ex-McKinsey, expendable, ...)
    caps = build(words, a.speed, FPS)
    ass = os.path.join(a.work, "captions.ass")
    open(ass, "w", encoding="utf-8").write(to_ass(caps))
    nkey = sum(1 for c in caps for w in c["words"] if w["c"] == ORANGE)
    print(f"  {len(caps)} caption lines, {nkey} orange keywords -> {ass}")

    # libass wants a forward-slash, drive-escaped path inside the filter string
    p = ass.replace("\\", "/").replace(":", "\\:")
    cmd = [FF, "-y", "-stats"]
    if a.preview:
        s, e = [float(v) for v in a.preview.split(",")]
        cmd += ["-ss", str(s), "-t", str(e - s)]
    cmd += ["-i", a.video, "-vf", f"subtitles='{p}'",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "copy", "-movflags", "+faststart", a.out]
    if a.preview:                     # -ss before -i shifts time; re-anchor the subs to match
        s, e = [float(v) for v in a.preview.split(",")]
        cmd[cmd.index("-vf") + 1] = f"setpts=PTS+{s}/TB,subtitles='{p}',setpts=PTS-{s}/TB"

    r = subprocess.run(cmd, capture_output=True, text=True)
    print("FFMPEG ERROR:\n" + r.stderr[-2000:] if r.returncode else "wrote " + a.out)


if __name__ == "__main__":
    main()
