"""B-roll: closing CTA — BOOK A DISCOVERY CALL with a pulsing button. UNSCALE dark."""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
BG = (13, 12, 11); WHITE = (255, 255, 255); GOLD = (200, 148, 62); ORANGE = (232, 118, 45); GRAY = (150, 150, 150)
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
gl = np.clip(1 - np.sqrt((xx - W * 0.5) ** 2 + (yy - H * 0.42) ** 2) / 760, 0, 1) ** 2 * 0.20
for i in range(3): arr[:, :, i] += ORANGE[i] * gl
BGIMG = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

FPS, TOTAL = 30, 138
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    im = BGIMG.copy().convert('RGBA'); d = ImageDraw.Draw(im, 'RGBA')
    # logo
    lf = dm(40, 700); lx = W / 2 - d.textlength('UNSCALE', font=lf) / 2
    d.text((lx, 150), 'UN', font=lf, fill=GOLD + (255,))
    d.text((lx + d.textlength('UN', font=lf), 150), 'SCALE', font=lf, fill=WHITE + (255,))
    # header
    ha = min(1, fr / 14)
    d.text((W / 2, 540), 'WANT THIS RUNNING FOR YOU?', font=dm(44, 700),
           fill=tuple(int(BG[i] + (GRAY[i] - BG[i]) * ha) for i in range(3)) + (255,), anchor='mm')
    # BOOK A DISCOVERY  +  serif-italic 'call'
    ba = max(0, min(1, (fr - 10) / 14))
    if ba > 0:
        d.text((W / 2, 730), 'BOOK A DISCOVERY', font=dm(60, 700),
               fill=tuple(int(BG[i] + (WHITE[i] - BG[i]) * ba) for i in range(3)) + (255,), anchor='mm')
        d.text((W / 2, 860), 'call', font=pfi(150, 600),
               fill=tuple(int(BG[i] + (ORANGE[i] - BG[i]) * ba) for i in range(3)) + (255,), anchor='mm')
    # subtle ghost-outline button (no fill, no pulse)
    if fr >= 32:
        p = min(1, (fr - 32) / 16)
        A = int(255 * p)
        bf = dm(40, 500); label = 'Book your call   →'
        tw = d.textlength(label, font=bf); bw = tw + 100; bh = 100
        bx0 = (W - bw) / 2; by0 = 1170 + int((1 - p) * 18)
        d.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=50, outline=ORANGE + (A,), width=2)
        d.text((W / 2, by0 + bh / 2), label, font=bf, fill=WHITE + (A,), anchor='mm')
        d.text((W / 2, 1400), 'the form’s in the description', font=pfi(38, 500),
               fill=GRAY + (int(190 * p),), anchor='mm')
    im.convert('RGB').save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll6-cta.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
