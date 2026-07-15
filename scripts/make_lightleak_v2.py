"""Light-leak TRANSITION (reference style) on 4s of 0616 footage, UNSCALE orange/gold.
Elements: diagonal light streaks + brief color flash + falling sparkle particles + bottom bloom.
"""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'
# cyan/teal palette to match the reference video
ORANGE=(34,200,222); GOLD=(120,236,242); WARM=(205,250,253)
SRC0,DUR=343.0,4.0
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
ANGLE=58

tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(SRC0),'-i',FRONT,'-t',str(DUR),'-vf',CROP,os.path.join(tmp,'f%03d.png')],capture_output=True)
frames=sorted(f for f in os.listdir(tmp) if f.startswith('f')); N=len(frames)

rng=np.random.RandomState(3)
# diagonal streaks: perpendicular offsets along the frame
NST=14; OFFS=rng.uniform(-1200,1200,NST); STBR=rng.uniform(0.4,1.0,NST); STLAG=rng.uniform(0,0.25,NST)
# particles (lower frame)
NP=70; PX=rng.uniform(0,W,NP); PY0=rng.uniform(0.5*H,1.05*H,NP); PSPD=rng.uniform(120,420,NP)
PBR=rng.uniform(0.4,1.0,NP); PPH=rng.uniform(0,6.28,NP)
def lerp(a,b,t): return tuple(int(x+(y-x)*max(0,min(1,t))) for x,y in zip(a,b))

def env(t):  # transition envelope, peak ~1.7s
    if t<1.1 or t>2.6: return 0.0
    if t<1.7: return (t-1.1)/0.6
    return max(0.0,1-(t-1.7)/0.9)

dx,dy=math.cos(math.radians(ANGLE)),math.sin(math.radians(ANGLE))
px_,py_=-dy,dx  # perpendicular
out=tempfile.mkdtemp()
for i,fn in enumerate(frames):
    t=i/FPS; e=env(t)
    foot=np.asarray(Image.open(os.path.join(tmp,fn)).convert('RGB'),np.float32)
    if e>0.01:
        L=Image.new('RGB',(W,H),(0,0,0)); d=ImageDraw.Draw(L)
        cx,cy=W/2,H/2
        # diagonal streaks across whole frame
        for k in range(NST):
            sb=STBR[k]*max(0,min(1,(e-STLAG[k])/0.5))
            if sb<=0.02: continue
            ox=cx+px_*OFFS[k]; oy=cy+py_*OFFS[k]
            x1,y1=ox-dx*1600,oy-dy*1600; x2,y2=ox+dx*1600,oy+dy*1600
            col=lerp(ORANGE,WARM,(k%5)/4)
            d.line((x1,y1,x2,y2),fill=tuple(int(c*sb) for c in col),width=3)
        core=L.copy()
        L=L.filter(ImageFilter.GaussianBlur(11))   # soft halo
        la=np.asarray(L,np.float32)+np.asarray(core.filter(ImageFilter.GaussianBlur(1)),np.float32)*0.9
        # falling sparkle particles (lower frame)
        P=Image.new('RGB',(W,H),(0,0,0)); pd=ImageDraw.Draw(P)
        for k in range(NP):
            y=PY0[k]+PSPD[k]*(t-1.1)
            if y>H+10 or y<0: continue
            tw=0.5+0.5*math.sin(t*9+PPH[k]); br=PBR[k]*e*tw
            if br<=0.05: continue
            x=PX[k]; col=lerp(GOLD,WARM,tw)
            pd.line((x,y,x,y+10),fill=tuple(int(c*br) for c in col),width=2)
            pd.ellipse((x-2,y-2,x+2,y+2),fill=tuple(int(c*br) for c in col))
        la+=np.asarray(P.filter(ImageFilter.GaussianBlur(1)),np.float32)
        # bottom bloom + brief flash
        yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
        bloom=np.clip(1-((yy-H*0.92)**2/(H*0.5)**2+(xx-cx)**2/(W*0.9)**2),0,1)*0.6*e
        flash=0.0
        if 1.55<t<1.78: flash=(1-abs(t-1.66)/0.12)*0.32
        for c in range(3):
            la[:,:,c]+=ORANGE[c]*bloom+ORANGE[c]*flash
        final=np.clip(foot+la,0,255)
    else:
        final=foot
    Image.fromarray(final.astype(np.uint8)).save(os.path.join(out,f'p{i:03d}.png'))

mp4='C:/Users/User/Downloads/0616_lightleak_cyan.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True)
print('SAVED',mp4)
