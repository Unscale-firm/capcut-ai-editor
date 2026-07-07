"""Blur-whip (zoom motion-blur smear) over an angle switch in 0616 — NO flash.
Samples the FROM angle just before the cut and the TO angle just after, zoom-blurs into and
out of the cut so the switch is hidden in the smear. Per-angle crop matches the edit
(front = 1.5x zoom, side = full frame). Place the clip at cut-0.22.
Usage: make_blur_0616.py <cut_s> <from_tag C9146|C9138> <to_tag> <out.mp4>
"""
import json, subprocess, os, tempfile, shutil, sys
import numpy as np
from PIL import Image

W,H,FPS=1080,1920,30
PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
CUT=float(sys.argv[1]); FROM_TAG=sys.argv[2]; TO_TAG=sys.argv[3]; OUT=sys.argv[4]
HALF=0.22; MAXS=0.46   # blur strength; no flash
CROP={'C9146':'crop=720:1280:180:200,scale=1080:1920,fps=30',   # front 1.5x zoom
      'C9138':'scale=1080:1920,fps=30'}                          # side full frame

d=json.load(open(PROJ,encoding='utf-8'))
vmat={m['id']:m for m in d['materials']['videos']}
SRCFILE={'C9146':next(m['path'] for m in d['materials']['videos'] if 'C9146' in m['path']),
         'C9138':next(m['path'] for m in d['materials']['videos'] if 'C9138' in m['path'])}
def src_time(tag,t):
    for tr in d['tracks']:
        if tr['type']!='video': continue
        for s in tr['segments']:
            if tag in vmat.get(s['material_id'],{}).get('path',''):
                a=s['target_timerange']['start']/1e6; b=a+s['target_timerange']['duration']/1e6
                if a<=t<b: return (s['source_timerange']['start']+(t*1e6-s['target_timerange']['start']))/1e6
    return None
from_t=src_time(FROM_TAG,CUT-HALF); to_t=src_time(TO_TAG,CUT)
if from_t is None or to_t is None: raise SystemExit(f'cannot resolve src: from={from_t} to={to_t}')

tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(from_t),'-i',SRCFILE[FROM_TAG],'-t',str(HALF),'-vf',CROP[FROM_TAG],os.path.join(tmp,'s%03d.png')],capture_output=True)
subprocess.run([FF,'-y','-ss',str(to_t),'-i',SRCFILE[TO_TAG],'-t',str(HALF),'-vf',CROP[TO_TAG],os.path.join(tmp,'f%03d.png')],capture_output=True)
seq=[('s',x) for x in sorted(f for f in os.listdir(tmp) if f.startswith('s'))]+\
    [('f',x) for x in sorted(f for f in os.listdir(tmp) if f.startswith('f'))]
N=len(seq); mid=(N-1)/2
def zoomblur(im,s,n=8):
    if s<=0.01: return im
    acc=np.zeros_like(im,dtype=np.float32); base=Image.fromarray(im.astype(np.uint8))
    for k in range(n):
        sc=1+s*k/(n-1); nh,nw=int(H*sc),int(W*sc)
        big=np.asarray(base.resize((nw,nh),Image.BILINEAR),dtype=np.float32)
        oy,ox=(nh-H)//2,(nw-W)//2; acc+=big[oy:oy+H,ox:ox+W]
    return acc/n
for i,(kind,fn) in enumerate(seq):
    im=np.asarray(Image.open(os.path.join(tmp,fn)).convert('RGB'),dtype=np.float32)
    s=MAXS*(1-abs((i-mid)/mid))   # 0 at ends, peak at the cut
    Image.fromarray(np.clip(zoomblur(im,s),0,255).astype(np.uint8)).save(os.path.join(tmp,f'p{i:03d}.png'))
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(tmp,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),OUT],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True)
print('saved',OUT,'| place at',round(CUT-HALF,2))
