"""General: crossfade a full-screen graphic with the underlying camera at its edges.
usage: crossfade_broll.py <graphic.mp4> <start_sec> <4106|4571> <fade_out 0|1>"""
import json, subprocess, os, tempfile, shutil, sys
import numpy as np
from PIL import Image

GRAPHIC, START_T, CAM, FADEOUT = sys.argv[1], float(sys.argv[2]), sys.argv[3], int(sys.argv[4])
W, H, FPS = 1080, 1920, 30
PROJ = r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608\draft_content.json'
SRCVID = 'C:/Users/User/Downloads/IMG_4106.MOV' if CAM == '4106' else 'C:/Users/User/Downloads/IMG_4571.MOV'
FF = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
      r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FP = FF.replace('ffmpeg.exe', 'ffprobe.exe')
DUR = float(subprocess.run([FP, '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', GRAPHIC], capture_output=True, text=True).stdout)

d = json.load(open(PROJ, encoding='utf-8'))
vmat = {m['id']: m for m in d['materials']['videos']}
seg = None
for tr in d['tracks']:
    if tr['type'] == 'video':
        for s in tr['segments']:
            if CAM in vmat.get(s['material_id'], {}).get('path', ''):
                t = s['target_timerange']
                if t['start'] / 1e6 <= START_T < (t['start'] + t['duration']) / 1e6:
                    seg = s
src_t = (seg['source_timerange']['start'] + (START_T * 1e6 - seg['target_timerange']['start'])) / 1e6

tmp = tempfile.mkdtemp()
subprocess.run([FF, '-y', '-ss', str(src_t), '-i', SRCVID, '-t', str(DUR + 0.2),
                '-vf', 'crop=1200:2133:480:853,scale=1080:1920,fps=30', os.path.join(tmp, 'c%04d.png')], capture_output=True)
subprocess.run([FF, '-y', '-i', GRAPHIC, '-vf', 'fps=30', os.path.join(tmp, 'g%04d.png')], capture_output=True)
cams = sorted(f for f in os.listdir(tmp) if f.startswith('c'))
graphs = sorted(f for f in os.listdir(tmp) if f.startswith('g'))
N = min(len(cams), len(graphs)); FADE = 12
for i in range(N):
    ca = np.asarray(Image.open(os.path.join(tmp, cams[i])).convert('RGB'), np.float32)
    ga = np.asarray(Image.open(os.path.join(tmp, graphs[i])).convert('RGB'), np.float32)
    ea = 1.0
    if i < FADE: ea = i / FADE
    elif FADEOUT and i >= N - FADE: ea = (N - 1 - i) / FADE
    Image.fromarray(np.clip(ca * (1 - ea) + ga * ea, 0, 255).astype(np.uint8)).save(os.path.join(tmp, f'p{i:04d}.png'))

out = GRAPHIC.replace('.mp4', '-final.mp4')
subprocess.run([FF, '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, 'p%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), out], capture_output=True)
shutil.rmtree(tmp, ignore_errors=True)
print('saved', out, '| place at', START_T, '-', round(START_T + DUR, 2), '| fade_out', FADEOUT)
