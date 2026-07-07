"""Subtle floating bokeh/dust atmosphere over 4s footage (warm + a touch of cyan), additive."""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'
SRC0,DUR=343.0,4.0
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
GOLD=(235,195,120); CYAN=(120,225,235)

tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(SRC0),'-i',FRONT,'-t',str(DUR),'-vf',CROP,os.path.join(tmp,'f%03d.png')],capture_output=True)
frames=sorted(f for f in os.listdir(tmp) if f.startswith('f')); N=len(frames)
rng=np.random.RandomState(11)
NB=22
BX=rng.uniform(0,W,NB); BY=rng.uniform(0,H,NB); BR=rng.uniform(14,70,NB)
BSP=rng.uniform(8,30,NB); BAMP=rng.uniform(10,40,NB); BPH=rng.uniform(0,6.28,NB)
BBR=rng.uniform(0.15,0.5,NB); BCY=rng.rand(NB)<0.3
ND=40; DX=rng.uniform(0,W,ND); DY=rng.uniform(0,H,ND); DSP=rng.uniform(20,60,ND); DPH=rng.uniform(0,6.28,ND)
out=tempfile.mkdtemp()
for i,fn in enumerate(frames):
    t=i/FPS
    foot=np.asarray(Image.open(os.path.join(tmp,fn)).convert('RGB'),np.float32)
    L=Image.new('RGB',(W,H),(0,0,0)); d=ImageDraw.Draw(L)
    for k in range(NB):
        x=(BX[k]+math.sin(t*0.6+BPH[k])*BAMP[k])%W
        y=(BY[k]-BSP[k]*t)%H
        col=CYAN if BCY[k] else GOLD; r=BR[k]
        br=BBR[k]*(0.7+0.3*math.sin(t*1.5+BPH[k]))
        d.ellipse((x-r,y-r,x+r,y+r),fill=tuple(int(c*br) for c in col))
    L=L.filter(ImageFilter.GaussianBlur(16))
    d2=ImageDraw.Draw(L)
    for k in range(ND):  # sharp dust specks
        x=(DX[k]+math.sin(t+DPH[k])*20)%W; y=(DY[k]-DSP[k]*t)%H
        tw=0.4+0.6*abs(math.sin(t*4+DPH[k]))
        d2.ellipse((x-1,y-1,x+2,y+2),fill=tuple(int(c*tw) for c in GOLD))
    la=np.asarray(L,np.float32)
    final=np.clip(foot+la*0.9,0,255)
    Image.fromarray(final.astype(np.uint8)).save(os.path.join(out,f'p{i:03d}.png'))
mp4='C:/Users/User/Downloads/0616_fx_particles.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True); print('SAVED',mp4)
