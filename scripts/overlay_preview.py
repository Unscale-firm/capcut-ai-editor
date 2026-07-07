"""Preview: lay an IGNORED overlay over a real front-camera frame (speaker stays visible)."""
import subprocess, os, tempfile
from PIL import Image, ImageDraw, ImageFont
import numpy as np

W, H = 1080, 1920
ORANGE = (232, 118, 45); GOLD = (200, 148, 62); WHITE = (255, 255, 255); GRAY = (200, 200, 200)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FF = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
      r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
def dm(sz, w, o=14):
    f = ImageFont.truetype(DMS, sz); f.set_variation_by_axes([o, w]); return f
def pfi(sz, w=500):
    f = ImageFont.truetype(PFI, sz); f.set_variation_by_axes([w]); return f

# 1) grab a front-camera frame, emulate the ~1.8x zoom framing
tmp = tempfile.gettempdir(); fr = os.path.join(tmp, 'frontframe.png')
subprocess.run([FF, '-y', '-ss', '55', '-i', 'C:/Users/User/Downloads/IMG_4106.MOV',
                '-frames:v', '1', '-vf', 'crop=1200:2133:480:760,scale=1080:1920', fr], capture_output=True)
base = Image.open(fr).convert('RGB')

# 2) overlay layer (alpha)
ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
# bottom darkening gradient for readability
grad = np.zeros((H, W, 4), np.uint8)
for y in range(H):
    a = int(np.clip((y - 820) / (H - 820), 0, 1) ** 1.3 * 210)
    grad[y, :, 3] = a
ov = Image.alpha_composite(ov, Image.fromarray(grad))
d = ImageDraw.Draw(ov)
# label + keyword + tag (lower third, off the face)
d.text((W / 2, 1190), "HR'S RESPONSE TO YOUR PITCH:", font=dm(38, 600), fill=GRAY + (255,), anchor='mm')
kf = dm(150, 800)
d.text((W / 2, 1320), 'IGNORED', font=kf, fill=ORANGE + (255,), anchor='mm')
uw = int(W * 0.42)
d.rectangle([W / 2 - uw / 2, 1400, W / 2 + uw / 2, 1408], fill=ORANGE + (255,))
d.text((W / 2, 1470), 'the same pitch, every single day', font=pfi(42, 500), fill=GOLD + (255,), anchor='mm')

out = Image.alpha_composite(base.convert('RGBA'), ov).convert('RGB')
out.save('C:/Users/User/capcut-ai-editor/refframes/overlay-preview.png')
print('saved preview')
