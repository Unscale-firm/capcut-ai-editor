"""B-roll #2 (UNSCALE dark theme): a counter floods up with identical pitches, then an
'IGNORED' stamp slams across. Non-email. Renders frames -> mp4."""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (13, 12, 11); WHITE = (255, 255, 255); GOLD = (200, 148, 62)
ORANGE = (232, 118, 45); GRAY = (154, 154, 154); MUTE = (112, 112, 112)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FFMPEG = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
          r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
_c = {}
def dm(sz, w, o=14):
    k = ('d', sz, w)
    if k not in _c:
        f = ImageFont.truetype(DMS, sz); f.set_variation_by_axes([o, w]); _c[k] = f
    return _c[k]
def pfi(sz, w=500):
    k = ('p', sz, w)
    if k not in _c:
        f = ImageFont.truetype(PFI, sz); f.set_variation_by_axes([w]); _c[k] = f
    return _c[k]

# background with glow
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
arr = np.zeros((H, W, 3), np.float32); arr[:] = BG
for gx, gy in [(0, 0), (W, 0)]:
    g = np.clip(1 - np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2) / 780, 0, 1) ** 2 * 0.16
    for i in range(3): arr[:, :, i] += ORANGE[i] * g
BGIMG = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
TARGET = 214

def logo(d):
    lf = dm(40, 700)
    un = sum(d.textlength(c, font=lf) + 6 for c in 'UN'); sc = sum(d.textlength(c, font=lf) + 6 for c in 'SCALE')
    x = (W - (un + sc)) / 2
    for c in 'UN': d.text((x, 150), c, font=lf, fill=GOLD); x += d.textlength(c, font=lf) + 6
    for c in 'SCALE': d.text((x, 150), c, font=lf, fill=WHITE); x += d.textlength(c, font=lf) + 6

# pre-build the rotated IGNORED stamp (RGBA)
def build_stamp():
    sf = dm(150, 800); pad = 50
    tw = ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength('IGNORED', font=sf)
    sw, sh = int(tw + pad * 2), 260
    st = Image.new('RGBA', (sw, sh), (0, 0, 0, 0)); sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([6, 6, sw - 6, sh - 6], radius=24, outline=ORANGE + (255,), width=10)
    sd.text((sw / 2, sh / 2), 'IGNORED', font=sf, fill=ORANGE + (255,), anchor='mm')
    return st.rotate(11, expand=True, resample=Image.BICUBIC)
STAMP = build_stamp()

FPS, TOTAL = 30, 180
C_START, C_END = 12, 95       # counter climbs
S_START = 132                 # stamp slams
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    logo(d)
    # header
    hf = dm(54, 700); af = pfi(60, 600)
    h1 = 'HR GETS THE SAME PITCH'
    d.text((W / 2, 300), h1, font=hf, fill=WHITE, anchor='mm')
    # counter
    t = max(0, min(1, (fr - C_START) / (C_END - C_START)))
    ease = 1 - (1 - t) ** 3
    val = int(TARGET * ease)
    stamped = fr >= S_START
    numcol = MUTE if stamped else GOLD
    nf = dm(300, 800)
    d.text((W / 2, 880), str(val), font=nf, fill=numcol, anchor='mm')
    lf2 = dm(52, 700)
    d.text((W / 2, 1120), 'IDENTICAL PITCHES', font=lf2, fill=(GRAY if not stamped else MUTE), anchor='mm')
    d.text((W / 2, 1210), 'every single day', font=pfi(54, 500), fill=(ORANGE if not stamped else MUTE), anchor='mm')
    # stamp slam
    if fr >= S_START:
        p = min(1, (fr - S_START) / 12)
        scale = 1.6 - 0.6 * (1 - (1 - p) ** 2)     # 1.6 -> 1.0 ease-out
        alpha = int(255 * min(1, p * 1.5))
        sw, sh = STAMP.size; nw, nh = int(sw * scale), int(sh * scale)
        s = STAMP.resize((nw, nh), Image.BICUBIC)
        if alpha < 255:
            a = s.split()[3].point(lambda v: int(v * alpha / 255)); s.putalpha(a)
        im.paste(s, (int(W / 2 - nw / 2), int(880 - nh / 2)), s)
    im.save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll2-ignored.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out, '(', TOTAL / FPS, 's )')
