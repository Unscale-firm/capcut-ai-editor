"""B-roll #2 — VERSION B: editorial 'flood'. A wall of identical generic pitches piles up
(dimmed, struck through), then IGNORED cuts across. Different composition from the card."""
import os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (13, 12, 11); ORANGE = (232, 118, 45); DIM = (74, 74, 78); DIMMER = (52, 52, 55); WHITE = (255, 255, 255)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/PlayfairDisplay-Italic.ttf'.replace('PlayfairDisplay-Italic', 'Playfair-Italic')
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
base = np.zeros((H, W, 3), np.float32)
for i in range(3): base[:, :, i] = BG[i]
gl = np.clip(1 - np.sqrt((xx) ** 2 + (yy) ** 2) / 820, 0, 1) ** 2 * 0.12
gl += np.clip(1 - np.sqrt((xx - W) ** 2 + (yy) ** 2) / 820, 0, 1) ** 2 * 0.12
for i in range(3): base[:, :, i] += ORANGE[i] * gl
BGIMG = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))

PITCHES = [
    "Hi, we're a specialist recruitment firm",
    "Quick question about your hiring needs",
    "We'd love to support your team",
    "Any roles you're looking to fill?",
    "We specialise in your industry",
    "Do you have any vacancies right now?",
    "Let's set up a quick call",
    "We have great candidates ready",
    "Following up on my last message",
    "Just checking in on hiring plans",
    "We'd be a great partner for you",
    "Can we help with your recruitment?",
    "Hi, we're a specialist recruitment firm",
    "Any hiring needs at the moment?",
    "We'd love to support your team",
    "Just following up again",
]
LF = dm(34, 500)
top = 250; lh = 86

FPS, TOTAL = 30, 168
appear_per = 5     # one line every 5 frames
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    n_shown = min(len(PITCHES), fr // appear_per)
    stamp_p = max(0, min(1, (fr - (len(PITCHES) * appear_per + 8)) / 12))
    for i in range(n_shown):
        y = top + i * lh
        col = DIMMER if stamp_p > 0 else DIM
        # tiny alternating indent for organic feel
        x = 90 + (18 if i % 2 else 0)
        d.text((x, y), PITCHES[i], font=LF, fill=col)
        d.ellipse([54, y + 8, 78, y + 32], outline=col, width=3)   # bullet
        if stamp_p > 0:                                            # strike-through when ignored
            d.line([x, y + 24, x + d.textlength(PITCHES[i], font=LF), y + 24], fill=DIMMER, width=2)
    # IGNORED slab across the middle
    if stamp_p > 0:
        by = H * 0.52; bh = 220
        bar = Image.new('RGBA', (W, int(bh)), (0, 0, 0, 0)); bd = ImageDraw.Draw(bar)
        a = int(255 * stamp_p)
        bd.rectangle([0, 0, W, bh], fill=(13, 12, 11, int(235 * stamp_p)))
        bd.rectangle([0, 0, W, 5], fill=ORANGE + (a,)); bd.rectangle([0, bh - 5, W, bh], fill=ORANGE + (a,))
        im.paste(bar, (0, int(by)), bar)
        kf = dm(150, 800)
        d2 = ImageDraw.Draw(im)
        d2.text((W / 2, by + bh / 2 - 16), 'IGNORED', font=kf, fill=ORANGE, anchor='mm')
        d2.text((W / 2, by + bh / 2 + 70), 'the same pitch, every single day', font=pfi(40, 500),
                fill=(150, 120, 95), anchor='mm')
    im.save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll2b-flood.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
