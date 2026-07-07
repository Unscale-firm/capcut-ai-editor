"""Bake the IGNORED background-replacement b-roll: cut the speaker out per frame, composite
over the IGNORED graphic, crossfade the bg in/out so it morphs seamlessly from the real wall."""
import json, subprocess, os, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rembg import remove, new_session
from PIL import ImageFilter

W, H = 1080, 1920
BG = (13, 12, 11); ORANGE = (232, 118, 45); GOLD = (200, 148, 62); WHITE = (255, 255, 255)
DMS = 'C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI = 'C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FF = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
      r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
PROJ = r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608\draft_content.json'
def dm(sz, w, o=14):
    f = ImageFont.truetype(DMS, sz); f.set_variation_by_axes([o, w]); return f
def pfi(sz, w=500):
    f = ImageFont.truetype(PFI, sz); f.set_variation_by_axes([w]); return f

START_T, DUR, FPS = 24.0, 5.8, 30

# front segment source mapping -> source time to extract
d = json.load(open(PROJ, encoding='utf-8'))
vmat = {m['id']: m for m in d['materials']['videos']}
fseg = None
for tr in d['tracks']:
    if tr['type'] == 'video':
        for s in tr['segments']:
            if '4106' in vmat.get(s['material_id'], {}).get('path', ''):
                t = s['target_timerange']
                if t['start'] / 1e6 <= START_T < (t['start'] + t['duration']) / 1e6:
                    fseg = s
if fseg is None: raise SystemExit('no front segment over the window')
src_t = (fseg['source_timerange']['start'] + (START_T * 1e6 - fseg['target_timerange']['start'])) / 1e6

tmp = tempfile.mkdtemp()
subprocess.run([FF, '-y', '-ss', str(src_t), '-i', 'C:/Users/User/Downloads/IMG_4106.MOV', '-t', str(DUR),
                '-vf', 'crop=1200:2133:480:853,scale=1080:1920,fps=30', os.path.join(tmp, 'o%04d.png')],
               capture_output=True)
frames = sorted(f for f in os.listdir(tmp) if f.startswith('o'))
print('extracted', len(frames), 'frames at source', round(src_t, 2), 's', flush=True)

# a CONTAINED IGNORED card behind the head — real wall kept everywhere else
CX0, CY0, CX1, CY1 = 150, 175, 930, 650
card = Image.new('RGBA', (W, H), (0, 0, 0, 0))
glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
ImageDraw.Draw(glow).rounded_rectangle([CX0 - 12, CY0 - 12, CX1 + 12, CY1 + 12], radius=52, fill=ORANGE + (46,))
card.alpha_composite(glow.filter(ImageFilter.GaussianBlur(34)))
cd = ImageDraw.Draw(card)
cd.rounded_rectangle([CX0, CY0, CX1, CY1], radius=42, fill=(17, 17, 19, 255), outline=(76, 60, 42, 255), width=2)
lf = dm(34, 700); lx = (CX0 + CX1) / 2 - cd.textlength('UNSCALE', font=lf) / 2
cd.text((lx, CY0 + 40), 'UN', font=lf, fill=GOLD + (255,))
cd.text((lx + cd.textlength('UN', font=lf), CY0 + 40), 'SCALE', font=lf, fill=WHITE + (255,))
sz = 200
while dm(sz, 800).getlength('IGNORED') > (CX1 - CX0) * 0.86: sz -= 4
cd.text(((CX0 + CX1) / 2, CY0 + 165), 'IGNORED', font=dm(sz, 800), fill=ORANGE + (255,), anchor='mm')
CARD_RGB = np.asarray(card.convert('RGB'), dtype=np.float32)
CARD_A = np.asarray(card.split()[3], dtype=np.float32) / 255.0     # card shape (incl. soft glow)

sess = new_session('u2net')
N = len(frames); FADE = 12
for i, fn in enumerate(frames):
    orig = Image.open(os.path.join(tmp, fn)).convert('RGB')
    oa = np.asarray(orig, dtype=np.float32)
    cut = remove(orig.resize((540, 960)), session=sess)         # cut out at half-res = faster
    pa = np.asarray(cut.split()[3].resize((W, H), Image.BILINEAR), dtype=np.float32) / 255.0  # person
    ea = 1.0
    if i < FADE: ea = i / FADE
    elif i >= N - FADE: ea = (N - 1 - i) / FADE
    rep = (CARD_A * (1.0 - pa) * ea)[..., None]                 # card only where not-person, behind head
    final = oa * (1 - rep) + CARD_RGB * rep
    Image.fromarray(np.clip(final, 0, 255).astype(np.uint8)).save(os.path.join(tmp, f'p{i:04d}.png'))
    if i % 30 == 0: print('processed', i, '/', N, flush=True)

out = 'C:/Users/User/Downloads/broll3-ignored-bg.mp4'
subprocess.run([FF, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'p%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('DONE saved', out, '| place at', START_T, '-', round(START_T + DUR, 2), 's', flush=True)
