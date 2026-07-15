"""B-roll #3 (UNSCALE dark): a job-board live-feed UI where a NEW ROLE pops in (real-time monitoring)."""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
BG = (13, 12, 11); CARD = (20, 20, 20); CARDHI = (26, 22, 18); BORDER = (42, 42, 42)
WHITE = (255, 255, 255); GOLD = (200, 148, 62); ORANGE = (232, 118, 45); GRAY = (150, 150, 150); MUTE = (110, 110, 110)
GREEN = (90, 200, 120)
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

CX0, CW, CH, PITCH = 70, 940, 150, 174
NEW_Y = 360
EX = [
    ("Head of Marketing", "Nexa  ·  Remote", "5h"),
    ("Finance Director", "Orbit  ·  New York", "8h"),
    ("Senior Designer", "Lumen  ·  London", "1d"),
    ("Sales Lead", "Vertex  ·  Berlin", "1d"),
]
NEW = ("VP of Engineering", "Stripe  ·  Remote", "just now")

def card(im, x, y, role, sub, t, hi=False, alpha=1.0, glow=0.0):
    d = ImageDraw.Draw(im, 'RGBA')
    if glow > 0:
        gl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)
        gd.rounded_rectangle([x - 8, y - 8, x + CW + 8, y + CH + 8], radius=26, outline=ORANGE + (int(200 * glow),), width=10)
        im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(10)))
    A = int(255 * alpha)
    d.rounded_rectangle([x, y, x + CW, y + CH], radius=20, fill=(CARDHI if hi else CARD) + (A,),
                        outline=(ORANGE if hi else BORDER) + (A,), width=3 if hi else 2)
    d.rounded_rectangle([x + 28, y + 38, x + 28 + 74, y + 38 + 74], radius=16,
                        fill=(ORANGE if hi else (60, 60, 64)) + (A,))
    d.text((x + 128, y + 36), role, font=dm(40, 700), fill=WHITE + (A,))
    d.text((x + 128, y + 92), sub, font=dm(31, 400), fill=GRAY + (A,))
    if hi:
        bw = 96
        d.rounded_rectangle([x + CW - 30 - bw, y + 34, x + CW - 30, y + 34 + 44], radius=12, fill=ORANGE + (A,))
        d.text((x + CW - 30 - bw / 2, y + 56), 'NEW', font=dm(26, 800), fill=(15, 12, 10, A), anchor='mm')
        d.text((x + CW - 30, y + 96), t, font=dm(30, 700), fill=ORANGE + (A,), anchor='ra')
    else:
        d.text((x + CW - 30, y + 60), t, font=dm(30, 400), fill=MUTE + (A,), anchor='ra')

FPS, TOTAL = 30, 180
NEW_AT = 78
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    im = BGIMG.copy().convert('RGBA'); d = ImageDraw.Draw(im, 'RGBA')
    # header pill: LIVE · MONITORING JOB BOARDS, pulsing dot
    pill = "MONITORING JOB BOARDS"
    pf = dm(40, 700); tw = d.textlength(pill, font=pf)
    px = (W - (tw + 90)) / 2; py = 175
    d.rounded_rectangle([px - 30, py - 14, px + tw + 70, py + 56], radius=34, fill=(22, 22, 24, 255), outline=BORDER + (255,), width=2)
    dotpulse = 0.5 + 0.5 * math.sin(fr * 0.35)
    d.ellipse([px, py + 8, px + 26, py + 34], fill=GREEN + (int(120 + 135 * dotpulse),))
    d.text((px + 52, py + 6), pill, font=pf, fill=WHITE + (255,))
    # existing cards fade in
    ef = min(1, fr / 18)
    for i, (r, s, t) in enumerate(EX):
        card(im, CX0, NEW_Y + (i + 1) * PITCH, r, s, t, hi=False, alpha=ef)
    # NEW card pops in
    if fr >= NEW_AT:
        p = min(1, (fr - NEW_AT) / 10)
        a = p
        glow = max(0, 1 - (fr - NEW_AT) / 14) * 0.9 + 0.25 * (0.5 + 0.5 * math.sin((fr - NEW_AT) * 0.3))
        card(im, CX0, NEW_Y, *NEW, hi=True, alpha=a, glow=glow * p)
        # toast
        if fr < NEW_AT + 40:
            ta = min(1, (fr - NEW_AT) / 6) * (1 if fr < NEW_AT + 28 else max(0, (NEW_AT + 40 - fr) / 12))
            tf = dm(34, 700); msg = 'NEW ROLE DETECTED'
            mw = d.textlength(msg, font=tf)
            d.rounded_rectangle([(W - mw) / 2 - 60, 290, (W + mw) / 2 + 30, 350], radius=30, fill=ORANGE + (int(235 * ta),))
            d.ellipse([(W - mw) / 2 - 44, 308, (W - mw) / 2 - 20, 332], fill=(15, 12, 10, int(255 * ta)))
            d.text(((W - mw) / 2 + 8, 300), msg, font=tf, fill=(15, 12, 10, int(255 * ta)))
    im.convert('RGB').save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll4-jobboard.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
