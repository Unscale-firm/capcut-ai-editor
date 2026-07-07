"""Preview: cut the speaker out and put an IGNORED graphic BEHIND him (bg replacement)."""
import subprocess, os, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rembg import remove

W, H = 1080, 1920
BG = (13, 12, 11); ORANGE = (232, 118, 45); GOLD = (200, 148, 62); WHITE = (255, 255, 255)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FF = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
      r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
def dm(sz, w, o=14):
    f = ImageFont.truetype(DMS, sz); f.set_variation_by_axes([o, w]); return f
def pfi(sz, w=500):
    f = ImageFont.truetype(PFI, sz); f.set_variation_by_axes([w]); return f

# 1) front frame (zoomed framing) + cut out the person
tmp = tempfile.gettempdir(); fr = os.path.join(tmp, 'ff.png')
subprocess.run([FF, '-y', '-ss', '55', '-i', 'C:/Users/User/Downloads/IMG_4106.MOV',
                '-frames:v', '1', '-vf', 'crop=1200:2133:480:760,scale=1080:1920', fr], capture_output=True)
person = remove(Image.open(fr).convert('RGB'))   # RGBA, bg removed

# 2) IGNORED background graphic
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
arr = np.zeros((H, W, 3), np.float32); arr[:] = BG
for gx, gy in [(0, 0), (W, 0)]:
    g = np.clip(1 - np.sqrt((xx - gx) ** 2 + (yy - gy) ** 2) / 820, 0, 1) ** 2 * 0.16
    for i in range(3): arr[:, :, i] += ORANGE[i] * g
bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert('RGBA')
d = ImageDraw.Draw(bg)
# UN logo top
lf = dm(40, 700)
d.text((W / 2 - d.textlength('UNSCALE', font=lf) / 2, 110), 'UN', font=lf, fill=GOLD)
d.text((W / 2 - d.textlength('UNSCALE', font=lf) / 2 + d.textlength('UN', font=lf), 110), 'SCALE', font=lf, fill=WHITE)
# big IGNORED ABOVE/behind the head so the word stays readable
size = 250
while dm(size, 800).getlength('IGNORED') > W * 0.92: size -= 4
d.text((W / 2, 300), 'IGNORED', font=dm(size, 800), fill=ORANGE, anchor='mm')
# tag low-left corner (not hidden behind him)
d.text((70, 1640), 'the same pitch,', font=pfi(46, 500), fill=GOLD, anchor='lm')
d.text((70, 1700), 'every single day', font=pfi(46, 500), fill=GOLD, anchor='lm')

# 3) composite person over the graphic
out = Image.alpha_composite(bg, person).convert('RGB')
out.save('C:/Users/User/Downloads/bg-replace-preview.png')
print('saved Downloads/bg-replace-preview.png')
