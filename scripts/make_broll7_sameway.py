"""Opening b-roll: a wall of identical recruiter pitches piles up -> COPY · PASTE · REPEAT.
Sets up 'most recruitment firms do outreach exactly the same way'. UNSCALE dark."""
import os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (13, 12, 11); ORANGE = (232, 118, 45); DIM = (74, 74, 78); DIMMER = (52, 52, 55); WHITE = (255, 255, 255); GOLD = (200, 148, 62)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FFMPEG = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
          r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
_c = {}
def dm(sz, w, o=14):
    k = (sz, w)
    if k not in _c:
        f = ImageFont.truetype(DMS, sz); f.set_variation_by_axes([o, w]); _c[k] = f
    return _c[k]
def pfi(sz, w=500):
    k = ('p', sz, w)
    if k not in _c:
        f = ImageFont.truetype(PFI, sz); f.set_variation_by_axes([w]); _c[k] = f
    return _c[k]

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
arr = np.zeros((H, W, 3), np.float32); arr[:] = BG
for gx, gy in [(0, 0), (W, 0)]:
    g = np.clip(1 - np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2) / 820, 0, 1) ** 2 * 0.12
    for i in range(3): arr[:, :, i] += ORANGE[i] * g
BGIMG = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

PITCHES = [
    "Hi, we're a specialist recruitment firm",
    "We'd love to support your team",
    "Any roles you're looking to fill?",
    "Quick question about your hiring",
    "We specialise in your industry",
    "Hi, we're a specialist recruitment firm",
    "Do you have any vacancies right now?",
    "We'd love to support your team",
    "Let's set up a quick call",
    "Following up on my last message",
    "Hi, we're a specialist recruitment firm",
    "Any hiring needs at the moment?",
    "We'd love to support your team",
    "Just checking in on hiring plans",
]
LF = dm(34, 500)
top, lh = 300, 84

FPS, TOTAL, per = 30, 150, 5
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    im = BGIMG.copy(); d = ImageDraw.Draw(im, 'RGBA')
    # header
    ha = min(1, fr / 14); hf = dm(50, 700)
    d.text((W / 2, 210), 'EVERY RECRUITER SENDS THIS', font=hf,
           fill=tuple(int(BG[i] + (WHITE[i] - BG[i]) * ha) for i in range(3)) + (255,), anchor='mm')
    n_shown = min(len(PITCHES), fr // per)
    end_p = max(0, min(1, (fr - (len(PITCHES) * per + 8)) / 12))
    for i in range(n_shown):
        y = top + i * lh; col = DIMMER if end_p > 0 else DIM
        x = 90 + (18 if i % 2 else 0)
        d.ellipse([54, y + 8, 78, y + 32], outline=col + (255,), width=3)
        d.text((x, y), PITCHES[i], font=LF, fill=col + (255,))
        if end_p > 0:
            d.line([x, y + 24, x + d.textlength(PITCHES[i], font=LF), y + 24], fill=DIMMER + (255,), width=2)
    # COPY · PASTE · REPEAT slab
    if end_p > 0:
        by, bh = H * 0.55, 200; a = int(255 * end_p)
        bar = Image.new('RGBA', (W, int(bh)), (0, 0, 0, 0)); bd = ImageDraw.Draw(bar)
        bd.rectangle([0, 0, W, bh], fill=(13, 12, 11, int(235 * end_p)))
        bd.rectangle([0, 0, W, 5], fill=ORANGE + (a,)); bd.rectangle([0, bh - 5, W, bh], fill=ORANGE + (a,))
        im.paste(bar, (0, int(by)), bar)
        d2 = ImageDraw.Draw(im, 'RGBA')
        d2.text((W / 2, by + bh / 2 - 20), 'COPY · PASTE · REPEAT', font=dm(64, 800), fill=ORANGE + (a,), anchor='mm')
        d2.text((W / 2, by + bh / 2 + 56), 'word for word, every firm', font=pfi(40, 500), fill=GOLD + (int(220 * end_p),), anchor='mm')
    im.convert('RGB').save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll7-sameway.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
