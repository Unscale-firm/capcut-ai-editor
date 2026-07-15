"""B-roll #1 (UNSCALE dark): a founder's CRM 'SALES PIPELINE' kanban that's basically empty —
only the personal network (15) sits in the first column. '15 people you know != a pipeline'.
Animated: board fades in, NEW LEADS ticks 0->15, the network card slides in with avatars,
then the red kicker pops. Outputs mp4 (+ a still with --still).
"""
import sys, os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (13, 12, 11); CARD = (20, 20, 20); CARDHI = (26, 22, 18); BORDER = (44, 44, 44)
WHITE = (245, 245, 245); GOLD = (200, 148, 62); ORANGE = (232, 118, 45)
GRAY = (150, 150, 150); MUTE = (95, 95, 95); RED = (214, 69, 60); GREEN = (90, 200, 120)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FFMPEG = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
          r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
if shutil.which('ffmpeg'): FFMPEG = 'ffmpeg'

_c = {}
def dm(sz, w, o=14):
    k = (sz, w, o)
    if k not in _c:
        f = ImageFont.truetype(DMS, sz); f.set_variation_by_axes([o, w]); _c[k] = f
    return _c[k]
def pfi(sz, w=500):
    k = ('p', sz, w)
    if k not in _c:
        f = ImageFont.truetype(PFI, sz); f.set_variation_by_axes([w]); _c[k] = f
    return _c[k]
def ease(t): t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)
def lerp(a, b, t): return tuple(int(x + (y - x) * t) for x, y in zip(a, b))

# ---- background: dark + soft orange glow top corners ----
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
arr = np.zeros((H, W, 3), np.float32); arr[:] = BG
for gx, gy in [(0, 120), (W, 120)]:
    g = np.clip(1 - np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2) / 860, 0, 1) ** 2 * 0.16
    for i in range(3): arr[:, :, i] += ORANGE[i] * g
BGIMG = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

COL_W = 470; GAP = 40; X0 = 70; Y0 = 500; COL_H = 430; ROW_GAP = 36
POS = [(X0, Y0), (X0 + COL_W + GAP, Y0),
       (X0, Y0 + COL_H + ROW_GAP), (X0 + COL_W + GAP, Y0 + COL_H + ROW_GAP)]
COLS = [("NEW LEADS", GRAY), ("CONTACTED", GRAY), ("MEETING", GRAY), ("CLOSED", GREEN)]
KICK_Y = Y0 + 2 * COL_H + ROW_GAP + 70

def ctext(d, cx, y, s, font, fill):
    w = d.textlength(s, font=font); d.text((cx - w / 2, y), s, font=font, fill=fill)

def make_base():
    """static layer: bg + header + title + 4 column shells (empty)."""
    img = BGIMG.copy(); d = ImageDraw.Draw(img)
    d.text((70, 250), "CRM", font=dm(34, 700, 30), fill=GOLD)
    d.text((148, 250), "/ SALES PIPELINE", font=dm(34, 500, 30), fill=MUTE)
    ctext(d, W / 2, 320, "Where are your deals?", pfi(86), WHITE)
    for i, ((cx, cy), (name, accent)) in enumerate(zip(POS, COLS)):
        d.rounded_rectangle((cx, cy, cx + COL_W, cy + COL_H), radius=24, fill=CARD, outline=BORDER, width=2)
        d.text((cx + 30, cy + 26), name, font=dm(28, 700, 20), fill=accent)
        d.line((cx + 28, cy + 86, cx + COL_W - 28, cy + 86), fill=(38, 38, 38), width=2)
        if i != 0:  # the three empty columns
            d.rounded_rectangle((cx + COL_W - 30 - 22 - 26, cy + 24, cx + COL_W - 30, cy + 24 + 44),
                                radius=22, fill=(30, 30, 30))
            d.text((cx + COL_W - 30 - 22 - 13, cy + 30), "0", font=dm(26, 700, 20), fill=MUTE)
            ctext(d, cx + COL_W / 2, cy + COL_H / 2 + 6, "—  empty  —", dm(28, 500, 20), MUTE)
    return img

BASE = make_base()

def render_frame(t):
    """t in [0,1] overall progress."""
    # phases
    p_fade = ease(t / 0.10)
    p_card = ease((t - 0.12) / 0.32)
    p_kick = ease((t - 0.60) / 0.18)
    if t < 0.10:
        return Image.blend(BGIMG, BASE, p_fade)
    im = BASE.copy(); d = ImageDraw.Draw(im)
    cx, cy = POS[0]
    # NEW LEADS count badge ticking 0 -> 15
    cnt = str(int(round(15 * p_card)))
    on = p_card > 0.02
    cf = dm(26, 700, 20); cw = d.textlength(cnt, font=cf)
    bx = cx + COL_W - 30 - cw - 26
    d.rounded_rectangle((bx, cy + 24, bx + cw + 26, cy + 24 + 44), radius=22,
                        fill=(36, 30, 24) if on else (30, 30, 30))
    d.text((bx + 13, cy + 30), cnt, font=cf, fill=ORANGE if on else MUTE)
    # network card slides up + fades in
    if p_card > 0.01:
        dy = int((1 - p_card) * 46)
        cardbg = lerp(CARD, CARDHI, p_card)
        ol = lerp(BORDER, (70, 56, 38), p_card)
        top = cy + 108 + dy
        d.rounded_rectangle((cx + 26, top, cx + COL_W - 26, top + 210), radius=18, fill=cardbg, outline=ol, width=2)
        tcol = lerp(CARD, WHITE, p_card)
        d.text((cx + 50, top + 26), "Friends & network", font=dm(30, 700, 20), fill=tcol)
        d.text((cx + 50, top + 72), "People you already know", font=dm(25, 400, 20), fill=lerp(CARD, GRAY, p_card))
        n_av = int(round(6 * ease((p_card - 0.3) / 0.6)))
        for i in range(n_av):
            ax = cx + 50 + i * 44
            d.ellipse((ax, top + 124, ax + 52, top + 176), fill=(48, 44, 40), outline=(80, 70, 58), width=2)
        if n_av >= 6:
            d.text((cx + 50 + 6 * 44 + 8, top + 138), "+9", font=dm(28, 600, 20), fill=GOLD)
    # red kicker pops in
    if p_kick > 0.01:
        col = lerp(BG, RED, p_kick)
        ctext(d, W / 2, KICK_Y, "15 people you know  ≠  a pipeline", dm(46, 700, 30), col)
    return im

if '--still' in sys.argv:
    render_frame(1.0).save('C:/Users/User/capcut-ai-editor/refframes/broll1_preview.png')
    print('saved still'); sys.exit()

FPS, SECONDS = 30, 6
TOTAL = FPS * SECONDS
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    render_frame(fr / (TOTAL - 1)).save(os.path.join(tmp, f'f{fr:04d}.png'))
out = 'C:/Users/User/Downloads/0616_broll1_pipeline.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
