"""Animated cold-email b-roll in the UNSCALE dark theme (DM Sans + Playfair italic accent)."""
import os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (13, 12, 11)                # near-black, warm
CARD = (20, 20, 20)              # #141414
BORDER = (42, 42, 42)            # #2A2A2A
FIELD = (26, 26, 28)
WHITE = (255, 255, 255)
GOLD = (200, 148, 62)            # #C8943E
ORANGE = (232, 118, 45)          # #E8762D
GRAY = (154, 154, 154)           # #9A9A9A
MUTE = (112, 112, 112)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FFMPEG = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
          r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')

_c = {}
def dm(sz, wght, opsz=14):
    k = ('d', sz, wght)
    if k not in _c:
        f = ImageFont.truetype(DMS, sz); f.set_variation_by_axes([opsz, wght]); _c[k] = f
    return _c[k]
def pfi(sz, wght=500):
    k = ('p', sz, wght)
    if k not in _c:
        f = ImageFont.truetype(PFI, sz); f.set_variation_by_axes([wght]); _c[k] = f
    return _c[k]
def ls_text(d, xy, text, font, fill, ls):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font) + ls
    return x

# ---- background with warm corner glows ----
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
arr = np.zeros((H, W, 3), np.float32); arr[:] = BG
for gx, gy in [(0, 0), (W, 0)]:
    dist = np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2)
    g = np.clip(1 - dist / 780, 0, 1) ** 2 * 0.16
    for i in range(3):
        arr[:, :, i] += ORANGE[i] * g
bgimg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

x0, y0, x1, y1 = 60, 470, 1020, 1500
pad = 58; cx = x0 + pad
bf = dm(37, 400); maxw = (x1 - pad) - cx

body = ("Hi there,|We're a specialist recruitment firm and we'd love to support your team."
        "|Do you have any hiring needs at the moment?|Best regards,~Specialist Recruitment")
lines = []
_m = ImageDraw.Draw(Image.new('RGB', (1, 1)))
for para in body.split('|'):
    for sub in para.split('~'):
        cur = ''
        for w in sub.split(' '):
            t = (cur + ' ' + w).strip()
            if _m.textlength(t, font=bf) <= maxw: cur = t
            else: lines.append(cur); cur = w
        lines.append(cur)
    lines.append('')
total_chars = sum(len(l) for l in lines)

def make_base():
    img = bgimg.copy(); d = ImageDraw.Draw(img)
    # UNSCALE logo
    lf = dm(40, 700)
    un_w = sum(d.textlength(c, font=lf) + 6 for c in 'UN')
    sc_w = sum(d.textlength(c, font=lf) + 6 for c in 'SCALE')
    sx = (W - (un_w + sc_w)) / 2
    ex = ls_text(d, (sx, 150), 'UN', lf, GOLD, 6)
    ls_text(d, (ex, 150), 'SCALE', lf, WHITE, 6)
    # header: THE EMAIL everyone SENDS
    hf = dm(56, 700); af = pfi(66, 600)
    w1 = d.textlength('THE EMAIL ', font=hf); w2 = d.textlength('everyone', font=af); w3 = d.textlength(' SENDS', font=hf)
    hx = (W - (w1 + w2 + w3)) / 2; hy = 270
    d.text((hx, hy), 'THE EMAIL ', font=hf, fill=WHITE)
    d.text((hx + w1, hy - 6), 'everyone', font=af, fill=ORANGE)
    d.text((hx + w1 + w2, hy), ' SENDS', font=hf, fill=WHITE)
    # card
    d.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=CARD, outline=BORDER, width=2)
    d.ellipse([cx, y0 + 55, cx + 96, y0 + 151], fill=ORANGE)
    d.text((cx + 48, y0 + 103), 'SR', font=dm(42, 700), fill=(15, 12, 10), anchor='mm')
    d.text((cx + 122, y0 + 62), 'Specialist Recruitment', font=dm(38, 700), fill=WHITE)
    d.text((cx + 122, y0 + 118), 'to you', font=dm(30, 400), fill=MUTE)
    d.text((x1 - pad, y0 + 62), '9:41 AM', font=dm(30, 400), fill=MUTE, anchor='ra')
    d.line([cx, y0 + 185, x1 - pad, y0 + 185], fill=BORDER, width=2)
    d.text((cx, y0 + 222), 'Any hiring needs right now?', font=dm(43, 600), fill=WHITE)
    return img
BASE = make_base(); BODY_Y = y0 + 345

FPS, TOTAL, FADE, type_start, type_end = 30, 240, 12, 12, 195
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    if fr < FADE:
        im = Image.blend(bgimg, BASE, fr / FADE)
    else:
        im = BASE.copy(); d = ImageDraw.Draw(im)
        reveal = int(total_chars * min(1, (fr - type_start) / (type_end - type_start)))
        R = reveal; ty = BODY_Y; cur = None
        for ln in lines:
            if ln == '': ty += 28; continue
            n = min(len(ln), R)
            d.text((cx, ty), ln[:n], font=bf, fill=GRAY)
            if n < len(ln):
                cur = (cx + d.textlength(ln[:n], font=bf) + 4, ty); R = 0; ty += 56; break
            R -= len(ln); ty += 56
            if R <= 0 and reveal < total_chars:
                cur = (cx + d.textlength(ln, font=bf) + 4, ty - 56); break
        if reveal < total_chars and (fr // 8) % 2 == 0 and cur:
            d.rectangle([cur[0], cur[1] + 4, cur[0] + 4, cur[1] + 46], fill=ORANGE)
        if reveal >= total_chars:
            d.text((W / 2, y1 + 60), 'sound familiar?', font=pfi(44, 500), fill=GOLD, anchor='mm')
    im.save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll-cold-email.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
