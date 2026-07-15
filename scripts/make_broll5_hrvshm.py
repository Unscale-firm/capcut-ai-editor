"""B-roll: HR (gatekeeper, ignores you) vs HIRING MANAGER (decision-maker) contrast. UNSCALE dark."""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
BG = (13, 12, 11); CARD = (20, 20, 20); CARDHI = (26, 22, 18); BORDER = (42, 42, 42)
WHITE = (255, 255, 255); GOLD = (200, 148, 62); ORANGE = (232, 118, 45); GRAY = (150, 150, 150); MUTE = (105, 105, 105)
RED = (210, 78, 70)
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
    g = np.clip(1 - np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2) / 820, 0, 1) ** 2 * 0.15
    for i in range(3): arr[:, :, i] += ORANGE[i] * g
BGIMG = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def card(im, y, big, sub, kind, alpha=1.0, glow=0.0):
    x0, x1 = 90, 990; h = 300
    d = ImageDraw.Draw(im, 'RGBA'); A = int(255 * alpha)
    hi = kind == 'hm'
    if glow > 0:
        gl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle(
            [x0 - 8, y - 8, x1 + 8, y + h + 8], radius=34, outline=ORANGE + (int(210 * glow),), width=12)
        im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(12)))
    d.rounded_rectangle([x0, y, x1, y + h], radius=28, fill=(CARDHI if hi else CARD) + (A,),
                        outline=(ORANGE if hi else BORDER) + (A,), width=3 if hi else 2)
    d.text((x0 + 50, y + 56), big, font=dm(72, 800), fill=(WHITE if hi else (175, 175, 178)) + (A,))
    d.text((x0 + 50, y + 168), sub, font=dm(38, 500), fill=(GRAY if hi else MUTE) + (A,))
    # badge circle right
    cxr, cyr = x1 - 90, y + 110
    if hi:
        d.ellipse([cxr - 46, cyr - 46, cxr + 46, cyr + 46], fill=ORANGE + (A,))
        d.line([cxr - 22, cyr + 2, cxr - 6, cyr + 20], fill=(15, 12, 10, A), width=9)
        d.line([cxr - 6, cyr + 20, cxr + 24, cyr - 18], fill=(15, 12, 10, A), width=9)
    else:
        d.ellipse([cxr - 46, cyr - 46, cxr + 46, cyr + 46], outline=RED + (A,), width=6)
        d.line([cxr - 20, cyr - 20, cxr + 20, cyr + 20], fill=RED + (A,), width=8)
        d.line([cxr - 20, cyr + 20, cxr + 20, cyr - 20], fill=RED + (A,), width=8)

FPS, TOTAL = 30, 132
HM_AT = 54
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    im = BGIMG.copy().convert('RGBA'); d = ImageDraw.Draw(im, 'RGBA')
    # header
    ha = min(1, fr / 14)
    h1 = dm(50, 700); af = pfi(56, 600)
    p1 = "STOP PITCHING "; p2 = "HR"
    w1 = d.textlength(p1, font=h1); w2 = d.textlength(p2, font=h1)
    hx = (W - (w1 + w2)) / 2
    d.text((hx, 320), p1, font=h1, fill=tuple(int(BG[i] + (WHITE[i] - BG[i]) * ha) for i in range(3)) + (255,))
    d.text((hx + w1, 320), p2, font=h1, fill=tuple(int(BG[i] + (RED[i] - BG[i]) * ha) for i in range(3)) + (255,))
    # HR card (fades in, then a red X / dims handled by kind='hr')
    card(im, 500, 'HR', 'the gatekeeper — ignores you', 'hr', alpha=min(1, fr / 16))
    # connector
    if fr > 30:
        ca = min(1, (fr - 30) / 12)
        d.text((W / 2, 870), 'go straight to the', font=pfi(40, 500), fill=GOLD + (int(255 * ca),), anchor='mm')
    # Hiring Manager card pops with glow
    if fr >= HM_AT:
        p = min(1, (fr - HM_AT) / 12)
        glow = max(0, 1 - (fr - HM_AT) / 16) * 0.9 + 0.22 * (0.5 + 0.5 * math.sin((fr - HM_AT) * 0.3))
        card(im, 960, 'HIRING MANAGER', 'the decision-maker — wants to hire', 'hm', alpha=p, glow=glow * p)
    im.convert('RGB').save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll5-hrvshm.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
