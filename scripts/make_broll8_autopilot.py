"""B-roll: the system on a loop (monitor -> spot role -> reach manager), RUNNING 24/7. UNSCALE dark."""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
BG = (13, 12, 11); CARD = (20, 20, 20); BORDER = (42, 42, 42)
WHITE = (255, 255, 255); GOLD = (200, 148, 62); ORANGE = (232, 118, 45); GRAY = (150, 150, 150); MUTE = (110, 110, 110); GREEN = (90, 200, 120)
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

STEPS = ["Monitor the job boards", "Spot the new role instantly", "Reach the hiring manager"]
CXc = 175; SY = [640, 940, 1240]   # circle x, step y positions

FPS, TOTAL = 30, 180
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    im = BGIMG.copy().convert('RGBA'); d = ImageDraw.Draw(im, 'RGBA')
    # header
    ha = min(1, fr / 14); hf = dm(56, 700); af = pfi(62, 600)
    p1 = "RUNS ON "; p2 = "autopilot"
    w1 = d.textlength(p1, font=hf); w2 = d.textlength(p2, font=af)
    hx = (W - (w1 + w2)) / 2
    d.text((hx, 280), p1, font=hf, fill=tuple(int(BG[i] + (WHITE[i] - BG[i]) * ha) for i in range(3)) + (255,))
    d.text((hx + w1, 272), p2, font=af, fill=tuple(int(BG[i] + (ORANGE[i] - BG[i]) * ha) for i in range(3)) + (255,))
    # connecting line through the circles
    d.line([CXc, SY[0], CXc, SY[2]], fill=BORDER + (255,), width=4)
    active = (fr // 16) % 3 if fr > 24 else -1     # which step is lit (cycles forever)
    for i, (label, y) in enumerate(zip(STEPS, SY)):
        ap = min(1, max(0, (fr - 6 - i * 6) / 16))   # fade in staggered
        lit = (i == active)
        if lit:
            gl = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).ellipse([CXc - 70, y - 70, CXc + 70, y + 70], fill=ORANGE + (120,))
            im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(22)))
            d = ImageDraw.Draw(im, 'RGBA')
        col = ORANGE if lit else (60, 60, 64)
        d.ellipse([CXc - 46, y - 46, CXc + 46, y + 46], fill=(col if lit else CARD) + (int(255 * ap),),
                  outline=(ORANGE if lit else BORDER) + (int(255 * ap),), width=3)
        d.text((CXc, y), str(i + 1), font=dm(44, 800), fill=((15, 12, 10) if lit else GRAY) + (int(255 * ap),), anchor='mm')
        d.text((CXc + 90, y - 22), label, font=dm(42, 700), fill=(WHITE if lit else GRAY) + (int(255 * ap),))
    # RUNNING 24/7 pill (pulsing dot)
    pf = dm(42, 700); msg = 'RUNNING 24/7'; tw = d.textlength(msg, font=pf)
    px = (W - (tw + 90)) / 2; py = 1520
    d.rounded_rectangle([px - 30, py - 14, px + tw + 70, py + 60], radius=36, fill=(22, 22, 24, 255), outline=BORDER + (255,), width=2)
    pulse = 0.5 + 0.5 * math.sin(fr * 0.4)
    d.ellipse([px, py + 10, px + 28, py + 38], fill=GREEN + (int(120 + 135 * pulse),))
    d.text((px + 56, py + 6), msg, font=pf, fill=WHITE + (255,))
    im.convert('RGB').save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll8-autopilot.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
