"""Crossfade the 3 full-screen b-rolls with the underlying front camera at their edges
(dissolve in + out, ~0.4s) — the clean 0608 look, no white flash.
Outputs *_xf.mp4 (new names to dodge CapCut's cache).
"""
import json, os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
DL='C:/Users/User/Downloads/'
JOBS=[('0616_broll1_pipeline.mp4',8.0),('0616_broll3_agencyburn.mp4',43.5),('0616_broll5_buildrunown.mp4',84.0)]

d=json.load(open(PROJ,encoding='utf-8'))
track0=[t for t in d['tracks'] if t['type']=='video'][0]
FRONT=next(m['path'] for m in d['materials']['videos'] if 'C9146' in m['path'])
def extract_window(a_us,b_us,tmp):
    paths=[]; idx=0
    for s in track0['segments']:
        st=s['target_timerange']['start']; en=st+s['target_timerange']['duration']
        lo=max(a_us,st); hi=min(b_us,en)
        if hi<=lo: continue
        src=(s['source_timerange']['start']+(lo-st))/1e6; dur=(hi-lo)/1e6
        subprocess.run([FF,'-y','-ss',str(src),'-i',FRONT,'-t',str(dur),'-vf',CROP,os.path.join(tmp,f'seg{idx}_%04d.png')],capture_output=True)
        for f in sorted(x for x in os.listdir(tmp) if x.startswith(f'seg{idx}_')): paths.append(os.path.join(tmp,f))
        idx+=1
    return paths

FADE=12
for fn,start in JOBS:
    g=DL+fn
    dur=float(subprocess.run([FF.replace('ffmpeg.exe','ffprobe.exe') if FF.endswith('ffmpeg.exe') else 'ffprobe',
            '-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',g],capture_output=True,text=True).stdout)
    tmp=tempfile.mkdtemp()
    cam=extract_window(int(start*1e6),int((start+dur+0.05)*1e6),tmp)
    subprocess.run([FF,'-y','-i',g,'-vf','fps=30',os.path.join(tmp,'g%04d.png')],capture_output=True)
    graphs=sorted(f for f in os.listdir(tmp) if f.startswith('g'))
    N=min(len(cam),len(graphs)); out=tempfile.mkdtemp()
    for i in range(N):
        ca=np.asarray(Image.open(cam[i]).convert('RGB'),np.float32)
        ga=np.asarray(Image.open(os.path.join(tmp,graphs[i])).convert('RGB'),np.float32)
        ea=1.0
        if i<FADE: ea=i/FADE
        elif i>=N-FADE: ea=(N-1-i)/FADE
        Image.fromarray(np.clip(ca*(1-ea)+ga*ea,0,255).astype(np.uint8)).save(os.path.join(out,f'p{i:04d}.png'))
    mp4=DL+fn.replace('.mp4','_xf.mp4')
    subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
    shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True)
    print('saved',mp4.split('/')[-1])
print('done')
