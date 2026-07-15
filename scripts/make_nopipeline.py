"""'NO PIPELINE' background behind Amine for the emphatic line at ~28s (27.7-30.0s).
Bakes over the live front footage (rembg cutout, bold struck-through wordmark behind him).
"""
import json, os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rembg import remove, new_session

W,H=1080,1920
BG=(13,12,11); ORANGE=(232,118,45); GOLD=(200,148,62); WHITE=(245,245,245); RED=(214,69,60); MUTE=(120,120,120)
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI='C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
FPS=30; CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
START,DUR=27.7,2.3
_c={}
def dm(sz,w,o=14):
    k=(sz,w,o)
    if k not in _c: f=ImageFont.truetype(DMS,sz); f.set_variation_by_axes([o,w]); _c[k]=f
    return _c[k]
def ease(t): t=max(0.0,min(1.0,t)); return t*t*(3-2*t)
def lerp(a,b,t): return tuple(int(x+(y-x)*max(0,min(1,t))) for x,y in zip(a,b))
def ctext(d,cx,y,s,font,fill):
    w=d.textlength(s,font=font); d.text((cx-w/2,y),s,font=font,fill=fill); return w
def glow_bg():
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32); arr=np.zeros((H,W,3),np.float32); arr[:]=BG
    for gx,gy in [(0,120),(W,120)]:
        g=np.clip(1-np.sqrt((xx-gx)**2+(yy-gy)**2)/860,0,1)**2*0.16
        for i in range(3): arr[:,:,i]+=ORANGE[i]*g
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
GBG=glow_bg()

def render(t):
    """big NO PIPELINE struck through, sits high so it reads around his head."""
    im=GBG.copy(); d=ImageDraw.Draw(im)
    pf=ease(t/0.10)
    ctext(d,W/2,300,"THERE IS",dm(40,700,30),lerp(BG,GOLD,pf))
    bigf=dm(118,800,40)
    wpx=ctext(d,W/2,372,"NO PIPELINE",bigf,lerp(BG,WHITE,pf))
    # red strikethrough draws across as he says it (~0.4-0.9s in)
    ps=ease((t-0.18)/0.30)
    if ps>0.01:
        x0=W/2-wpx/2-10; x1=x0+(wpx+20)*ps; y=372+62
        d.line((x0,y,x1,y),fill=RED,width=12)
    return np.asarray(im,dtype=np.float32)

# --- extract live front footage for the window ---
d=json.load(open(PROJ,encoding='utf-8'))
track0=[t for t in d['tracks'] if t['type']=='video'][0]
FRONT=next(m['path'] for m in d['materials']['videos'] if 'C9146' in m['path'])
tmp=tempfile.mkdtemp(); paths=[]; idx=0
a_us,b_us=int(START*1e6),int((START+DUR)*1e6)
for s in track0['segments']:
    st=s['target_timerange']['start']; en=st+s['target_timerange']['duration']
    lo=max(a_us,st); hi=min(b_us,en)
    if hi<=lo: continue
    src=(s['source_timerange']['start']+(lo-st))/1e6; dur=(hi-lo)/1e6
    subprocess.run([FF,'-y','-ss',str(src),'-i',FRONT,'-t',str(dur),'-vf',CROP,os.path.join(tmp,f'seg{idx}_%04d.png')],capture_output=True)
    for f in sorted(x for x in os.listdir(tmp) if x.startswith(f'seg{idx}_')): paths.append(os.path.join(tmp,f))
    idx+=1

sess=new_session('u2net_human_seg'); N=len(paths); FADE=8; out=tempfile.mkdtemp()
for i,fp in enumerate(paths):
    t=i/(N-1) if N>1 else 1.0
    foot=Image.open(fp).convert('RGB'); fa=np.asarray(foot,dtype=np.float32)
    cut=remove(foot.resize((540,960)),session=sess)
    pa=np.asarray(cut.split()[3].resize((W,H),Image.BILINEAR),dtype=np.float32)/255.0
    ea=1.0
    if i<FADE: ea=i/FADE
    elif i>=N-FADE: ea=(N-1-i)/FADE
    bg=render(t); pa3=pa[...,None]
    final=fa*pa3+(fa*(1-ea)+bg*ea)*(1-pa3)
    Image.fromarray(np.clip(final,0,255).astype(np.uint8)).save(os.path.join(out,f'p{i:04d}.png'))
    if i%30==0: print(i,'/',N,flush=True)
mp4='C:/Users/User/Downloads/0616_broll_nopipeline_baked.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True)
print('SAVED',mp4,'| place at',START,'-',round(START+DUR,2))
