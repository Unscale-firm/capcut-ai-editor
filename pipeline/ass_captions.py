"""
ASS caption emitter — the ffmpeg/libass equivalent of Captions.tsx.

Reproduces the locked caption look WITHOUT Remotion:
  Montserrat ExtraBold, uppercase, 62px, white with ONE orange (#E8762D) keyword,
  dark #141414 outline, centred at (540, 1380) on a 1080x1920 canvas,
  each word FADING IN at the moment it's spoken while the line keeps its final layout.

The "final layout" part matters: in Captions.tsx the words are inline-block with opacity,
so a not-yet-spoken word still occupies its space and the line never reflows. In ASS we get
the same behaviour by emitting ONE Dialogue per line holding every word, and animating each
word's alpha inline with \\alpha + \\t. (A progressive multi-Dialogue reveal would re-centre
the line on every word — visibly wrong.)

Colours in ASS are &HAABBGGRR (alpha, then BLUE, GREEN, RED — reversed from hex RGB).
"""

CANVAS_W, CANVAS_H = 1080, 1920
POS_X, POS_Y = 540, 1380      # Captions.tsx: top:1380 left:540 translate(-50%,-50%)
BOX_W = 940                   # Captions.tsx: width 940 -> margins (1080-940)/2 = 70
FONT = "Montserrat ExtraBold"
# Captions.tsx uses CSS fontSize 62. libass sizes glyphs by a different metric than CSS px, so the
# same number renders ~1.55x smaller. 96 was found by sweeping against the Remotion render (see the
# `verify` step): it is the value that matches the locked look, NOT a redesign.
FONT_SIZE = 96
SPACING = 1                   # Captions.tsx: letterSpacing 1
OUTLINE = 4                   # matched to the CSS 6px centred stroke by the same sweep
SHADOW = 3                    # CSS textShadow 0 5px 10px rgba(0,0,0,.55)
FADE_FRAMES = 2               # Captions.tsx: opacity 0->1 over 2 frames

ORANGE_HEX = "#E8762D"


def _ass_colour(hex_rgb: str) -> str:
    """#RRGGBB -> &H00BBGGRR& (ASS is BGR with a leading alpha byte)."""
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}&".upper()


def _ts(frames: int, fps: int) -> str:
    """frame number -> ASS timestamp H:MM:SS.cc (centiseconds)."""
    t = max(0.0, frames / fps)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _escape(text: str) -> str:
    """ASS treats { } as override-tag delimiters and \\ as an escape."""
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def caps_to_ass(caps, fps: int = 30) -> str:
    """caps: [{from, dur, words:[{t, c, rel}]}] (frames) -> a full .ass document."""
    white = _ass_colour("#FFFFFF")
    outline = _ass_colour("#141414")

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {CANVAS_W}
PlayResY: {CANVAS_H}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},{FONT_SIZE},{white},{white},{outline},&H8C000000&,-1,0,0,0,100,100,{SPACING},0,1,{OUTLINE},{SHADOW},5,{(CANVAS_W - BOX_W) // 2},{(CANVAS_W - BOX_W) // 2},0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    fade_ms = round(FADE_FRAMES / fps * 1000)
    lines = []
    for c in caps:
        start = _ts(c["from"], fps)
        end = _ts(c["from"] + c["dur"], fps)

        parts = []
        for w in c["words"]:
            colour = _ass_colour(w["c"])
            at = round(w["rel"] / fps * 1000)          # ms after the line starts
            # start transparent, fade to opaque over FADE_FRAMES at the moment the word is spoken.
            # \t timings are relative to this Dialogue's Start, which is exactly what `rel` is.
            parts.append(
                f"{{\\c{colour}\\alpha&HFF&\\t({at},{at + fade_ms},\\alpha&H00&)}}{_escape(w['t'])}"
            )
        text = " ".join(parts)
        lines.append(
            f"Dialogue: 0,{start},{end},Cap,,0,0,0,,{{\\pos({POS_X},{POS_Y})}}{text}"
        )

    return head + "\n".join(lines) + "\n"


def write_ass(caps, path: str, fps: int = 30) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(caps_to_ass(caps, fps))
    return path
