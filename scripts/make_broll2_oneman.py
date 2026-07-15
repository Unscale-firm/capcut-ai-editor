"""B-roll #2 (UNSCALE dark): hub-and-spoke — every sales task wires into ONE person (YOU/CEO).
'DMs between meetings, cold emails... the CEO becomes the entire sales department.'
Distinct layout: central avatar with task chips orbiting + connector lines. Animated reveal.
"""
import sys, os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (13, 12, 11); CARD = (20, 20, 20); BORDER = (44, 44, 44)
WHITE = (245, 245, 245); GOLD = (200, 148, 62); ORANGE = (232, 118, 45)
GRAY = (150, 150, 150); MUTE = (95, 95, 95); RED = (214, 69, 60)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FFMPEG = 'ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
          r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
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
def ctext(d, cx, y, s, font, fill):
    w = d.textlength(s, font=font); d.text((cx - w / 2, y), s, font=font, fill=fill)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
arr = np.zeros((H, W, 3), np.float32); arr[:] = BG
for gx, gy in [(0, 120), (W, 120)]:
    g = np.clip(1 - np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2) / 860, 0, 1) ** 2 * 0.16
    for i in range(3): arr[:, :, i] += ORANGE[i] * g
BGIMG = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

CX, CY, R = 540, 980, 415
TASKS = ["Cold emails", "LinkedIn DMs", "Follow-ups", "Booking calls", "Prospecting", "Pitching"]
ANG = [90, 30, 150, 210, 330, 270]
NODES = [(CX + R * math.cos(math.radians(a)), CY - R * math.sin(math.radians(a))) for a in ANG]

def make_base():
    img = BGIMG.copy(); d = ImageDraw.Draw(img)
    d.text((70, 250), "ORG CHART", font=dm(34, 700, 30), fill=GOLD)
    d.text((300, 250), "/ SALES DEPARTMENT", font=dm(34, 500, 30), fill=MUTE)
    ctext(d, W / 2, 318, "Who runs your sales?", pfi(82), WHITE)
    return img
BASE = make_base()

def chip(d, cxy, text, p):
    cw = 330; ch = 92; x, y = cxy[0] - cw / 2, cxy[1] - ch / 2
    bg = lerp(BG, CARD, p); ol = lerp(BG, BORDER, p)
    d.rounded_rectangle((x, y, x + cw, y + ch), radius=20, fill=bg, outline=ol, width=2)
    d.ellipse((x + 24, y + ch / 2 - 6, x + 36, y + ch / 2 + 6), fill=lerp(BG, ORANGE, p))
    ctext(d, cxy[0] + 18, cxy[1] - 17, text, dm(30, 600, 20), lerp(BG, WHITE, p))

def render_frame(t):
    if t < 0.10:
        return Image.blend(BGIMG, BASE, ease(t / 0.10))
    im = BASE.copy(); d = ImageDraw.Draw(im)
    # connectors + chips appear one by one
    for i, (nx, ny) in enumerate(NODES):
        p = ease((t - 0.14 - i * 0.075) / 0.18)
        if p <= 0.01: continue
        ex = CX + (nx - CX) * 1.0; ey = CY + (ny - CY) * 1.0
        lx = CX + (nx - CX) * (0.18 + 0.82 * (1 - p) * 0 + 0)  # full line drawn by p via endpoint
        endx = CX + (nx - CX) * p; endy = CY + (ny - CY) * p
        d.line((CX, CY, endx, endy), fill=lerp(BG, (70, 60, 50), p), width=4)
        chip(d, (nx, ny), TASKS[i], p)
    # center hub pulses in
    ph = ease((t - 0.10) / 0.14)
    pulse = 1 + 0.03 * math.sin(t * 22)
    rr = int(118 * ph * pulse)
    d.ellipse((CX - rr - 8, CY - rr - 8, CX + rr + 8, CY + rr + 8), outline=lerp(BG, ORANGE, ph), width=4)
    d.ellipse((CX - rr, CY - rr, CX + rr, CY + rr), fill=lerp(BG, (32, 26, 20), ph), outline=lerp(BG, GOLD, ph), width=3)
    if ph > 0.5:
        ctext(d, CX, CY - 44, "YOU", dm(54, 800, 30), WHITE)
        ctext(d, CX, CY + 18, "CEO", dm(30, 600, 20), GOLD)
    # punchline
    pk = ease((t - 0.74) / 0.16)
    if pk > 0.01:
        ctext(d, W / 2, 1500, "Sales team headcount:  1", dm(46, 700, 30), lerp(BG, RED, pk))
    return im

if '--still' in sys.argv:
    render_frame(1.0).save('C:/Users/User/capcut-ai-editor/refframes/broll2_preview.png'); print('still'); sys.exit()
FPS, SECONDS = 30, 7; TOTAL = FPS * SECONDS
tmp = tempfile.mkdtemp()
for fr in range(TOTAL): render_frame(fr / (TOTAL - 1)).save(os.path.join(tmp, f'f{fr:04d}.png'))
out = 'C:/Users/User/Downloads/0616_broll2_oneman.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True); print('saved', out)
