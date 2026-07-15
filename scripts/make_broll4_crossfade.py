"""Crossfade the job-board graphic with the underlying side camera at its edges (seamless in/out)."""
import json, subprocess, os, tempfile, shutil
import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30
START_T, DUR = 32.0, 6.0
PROJ = r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608\draft_content.json'
GRAPHIC = 'C:/Users/User/Downloads/broll4-jobboard.mp4'
FF = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
      r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')

# side segment source time for the window
d = json.load(open(PROJ, encoding='utf-8'))
vmat = {m['id']: m for m in d['materials']['videos']}
sseg = None
for tr in d['tracks']:
    if tr['type'] == 'video':
        for s in tr['segments']:
            if '4571' in vmat.get(s['material_id'], {}).get('path', ''):
                t = s['target_timerange']
                if t['start'] / 1e6 <= START_T < (t['start'] + t['duration']) / 1e6:
                    sseg = s
src_t = (sseg['source_timerange']['start'] + (START_T * 1e6 - sseg['target_timerange']['start'])) / 1e6

tmp = tempfile.mkdtemp()
# side frames (match the 1.8x framing) + graphic frames
subprocess.run([FF, '-y', '-ss', str(src_t), '-i', 'C:/Users/User/Downloads/IMG_4571.MOV', '-t', str(DUR),
                '-vf', 'crop=1200:2133:480:853,scale=1080:1920,fps=30', os.path.join(tmp, 's%04d.png')], capture_output=True)
subprocess.run([FF, '-y', '-i', GRAPHIC, '-vf', 'fps=30', os.path.join(tmp, 'g%04d.png')], capture_output=True)
sides = sorted(f for f in os.listdir(tmp) if f.startswith('s'))
graphs = sorted(f for f in os.listdir(tmp) if f.startswith('g'))
N = min(len(sides), len(graphs)); FADE = 12
print('side', len(sides), 'graphic', len(graphs), 'src', round(src_t, 2))
for i in range(N):
    sa = np.asarray(Image.open(os.path.join(tmp, sides[i])).convert('RGB'), np.float32)
    ga = np.asarray(Image.open(os.path.join(tmp, graphs[i])).convert('RGB'), np.float32)
    ea = 1.0
    if i < FADE: ea = i / FADE
    elif i >= N - FADE: ea = (N - 1 - i) / FADE
    Image.fromarray(np.clip(sa * (1 - ea) + ga * ea, 0, 255).astype(np.uint8)).save(os.path.join(tmp, f'p{i:04d}.png'))

out = 'C:/Users/User/Downloads/broll4-final.mp4'
subprocess.run([FF, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'p%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out, '| place at', START_T, '-', START_T + DUR)
