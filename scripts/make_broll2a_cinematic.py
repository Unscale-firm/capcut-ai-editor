"""B-roll #2 — VERSION A: cinematic bold-keyword (your 'DO MORE' style). Moody dark bg,
giant orange IGNORED that blurs in, minimal text. Distinct from the email card."""
import os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
BG = (13, 12, 11); ORANGE = (232, 118, 45); GRAY = (150, 150, 150); WHITE = (255, 255, 255)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
FFMPEG = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
          r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
_c = {}
def dm(sz, w, o=14):
    k = (sz, w)
    if k not in _c:
        f = ImageFont.truetype(DMS, sz); f.set_variation_by_axes([o, w]); _c[k] = f
    return _c[k]

# moody cinematic background: gradient + warm top glow + vignette + grain
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
base = np.zeros((H, W, 3), np.float32)
for i in range(3): base[:, :, i] = BG[i]
gl = np.clip(1 - np.sqrt((xx - W * 0.5) ** 2 + (yy - H * 0.30) ** 2) / 760, 0, 1) ** 2 * 0.20
for i in range(3): base[:, :, i] += ORANGE[i] * gl
vig = np.clip(1 - np.sqrt((xx - W / 2) ** 2 + (yy - H / 2) ** 2) / 1150, 0, 1)
for i in range(3): base[:, :, i] *= 0.5 + 0.5 * vig
grain = np.random.default_rng(7).standard_normal((H, W, 1)).astype(np.float32) * 5
base = np.clip(base + grain, 0, 255).astype(np.uint8)
BGIMG = Image.fromarray(base)

KW = 'IGNORED'
size = 230
while dm(size, 800).getlength(KW) > W * 0.82: size -= 4
KF = dm(size, 800)
KY = 980

def word(scale, blur, alpha):
    wi = Image.new('RGBA', (W, 460), (0, 0, 0, 0)); wd = ImageDraw.Draw(wi)
    wd.text((W / 2, 230), KW, font=KF, fill=ORANGE + (255,), anchor='mm')
    if blur > 0.2: wi = wi.filter(ImageFilter.GaussianBlur(blur))
    if abs(scale - 1) > 0.001:
        wi = wi.resize((int(W * scale), int(460 * scale)), Image.BICUBIC)
    if alpha < 255:
        a = wi.split()[3].point(lambda v: int(v * alpha / 255)); wi.putalpha(a)
    return wi

FPS, TOTAL = 30, 168
tmp = tempfile.mkdtemp()
for fr in range(TOTAL):
    im = BGIMG.copy(); d = ImageDraw.Draw(im)
    # small grey label fades in
    la = max(0, min(1, (fr - 6) / 16))
    if la > 0:
        d.text((W / 2, 770), "HR'S RESPONSE TO YOUR PITCH:", font=dm(40, 600),
               fill=tuple(int(BG[i] + (GRAY[i] - BG[i]) * la) for i in range(3)), anchor='mm')
    # keyword: blur-scale entrance, then slow drift
    if fr <= 16:
        p = fr / 16
        blur = 24 * (1 - p); scale = 1.14 - 0.14 * (1 - (1 - p) ** 2); alpha = int(255 * min(1, p * 1.4))
    else:
        blur = 0; scale = 1.0 + 0.035 * ((fr - 16) / (TOTAL - 16)); alpha = 255
    wi = word(scale, blur, alpha)
    im.paste(wi, (int(W / 2 - wi.width / 2), int(KY - wi.height / 2)), wi)
    # underline draws in
    if fr > 18:
        up = max(0, min(1, (fr - 18) / 14)); uw = int(W * 0.46 * up)
        d.rectangle([W / 2 - uw / 2, KY + 130, W / 2 + uw / 2, KY + 138], fill=ORANGE)
    im.save(os.path.join(tmp, f'f{fr:04d}.png'))

out = 'C:/Users/User/Downloads/broll2a-cinematic.mp4'
subprocess.run([FFMPEG, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'f%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out)
