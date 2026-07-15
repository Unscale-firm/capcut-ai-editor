"""Sample: a zoom/motion-blur transition over an angle switch (side->front at ~22s).
The frame blurs up into the cut and blurs back out, hiding the switch in the smear."""
import json, subprocess, os, tempfile, shutil, sys
import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30
PROJ = r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608\draft_content.json'
FF = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
      r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
CUT = float(sys.argv[1]) if len(sys.argv) > 1 else 22.0
FROM_TAG = sys.argv[2] if len(sys.argv) > 2 else '4571'    # angle BEFORE the cut
TO_TAG = sys.argv[3] if len(sys.argv) > 3 else '4106'      # angle AFTER
OUT = sys.argv[4] if len(sys.argv) > 4 else 'C:/Users/User/Downloads/blur-transition.mp4'
HALF = 0.22; MAXS = 0.42; FLASH_MAX = 1.0   # full white flash, several frames
MOV = {'4106': 'C:/Users/User/Downloads/IMG_4106.MOV', '4571': 'C:/Users/User/Downloads/IMG_4571.MOV'}

d = json.load(open(PROJ, encoding='utf-8'))
vmat = {m['id']: m for m in d['materials']['videos']}
def src_time(tag, t):
    for tr in d['tracks']:
        if tr['type'] == 'video':
            for s in tr['segments']:
                if tag in vmat.get(s['material_id'], {}).get('path', ''):
                    a = s['target_timerange']['start'] / 1e6; b = a + s['target_timerange']['duration'] / 1e6
                    if a <= t < b:
                        return (s['source_timerange']['start'] + (t * 1e6 - s['target_timerange']['start'])) / 1e6
    return None
from_t = src_time(FROM_TAG, CUT - HALF)
to_t = src_time(TO_TAG, CUT)

tmp = tempfile.mkdtemp()
subprocess.run([FF, '-y', '-ss', str(from_t), '-i', MOV[FROM_TAG], '-t', str(HALF),
                '-vf', 'crop=1200:2133:480:853,scale=1080:1920,fps=30', os.path.join(tmp, 's%03d.png')], capture_output=True)
subprocess.run([FF, '-y', '-ss', str(to_t), '-i', MOV[TO_TAG], '-t', str(HALF),
                '-vf', 'crop=1200:2133:480:853,scale=1080:1920,fps=30', os.path.join(tmp, 'f%03d.png')], capture_output=True)
sides = sorted(f for f in os.listdir(tmp) if f.startswith('s'))
fronts = sorted(f for f in os.listdir(tmp) if f.startswith('f'))
seq = [('s', x) for x in sides] + [('f', x) for x in fronts]
N = len(seq); mid = (N - 1) / 2

def zoomblur(im, s, n=7):
    if s <= 0.01: return im
    acc = np.zeros_like(im, dtype=np.float32)
    base = Image.fromarray(im.astype(np.uint8))
    for k in range(n):
        sc = 1 + s * k / (n - 1)
        nh, nw = int(H * sc), int(W * sc)
        big = np.asarray(base.resize((nw, nh), Image.BILINEAR), dtype=np.float32)
        oy, ox = (nh - H) // 2, (nw - W) // 2
        acc += big[oy:oy + H, ox:ox + W]
    return acc / n

for i, (kind, fn) in enumerate(seq):
    im = np.asarray(Image.open(os.path.join(tmp, fn)).convert('RGB'), dtype=np.float32)
    s = MAXS * (1 - abs((i - mid) / mid))     # 0 at ends, peak at the cut
    out = zoomblur(im, s)
    dist = abs(i - mid)
    flash = FLASH_MAX * (1.0 if dist <= 1.6 else max(0, 1 - (dist - 1.6) / 2.2))  # ~4 pure-white frames + falloff
    if flash > 0:
        out = out * (1 - flash) + np.array([255, 252, 245], dtype=np.float32) * flash
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(os.path.join(tmp, f'p{i:03d}.png'))

subprocess.run([FF, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'p%03d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), OUT], capture_output=True)
start_place = round(CUT - HALF, 2)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', OUT, '| place at', start_place)
