"""Glitch / RGB-split / slice-displacement burst over 4s footage (cyan digital feel)."""
import os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'
SRC0,DUR=343.0,4.0
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'

tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(SRC0),'-i',FRONT,'-t',str(DUR),'-vf',CROP,os.path.join(tmp,'f%03d.png')],capture_output=True)
frames=sorted(f for f in os.listdir(tmp) if f.startswith('f')); N=len(frames)
out=tempfile.mkdtemp()
for i,fn in enumerate(frames):
    t=i/FPS
    a=np.asarray(Image.open(os.path.join(tmp,fn)).convert('RGB'),np.float32)
    # glitch active ~1.4-2.0s, stuttering
    g=0.0
    if 1.4<t<2.05:
        g=1-abs(t-1.7)/0.35
    rs=np.random.RandomState(i)
    if g>0.05 and rs.rand()<0.85:
        amp=int(28*g)
        out_a=a.copy()
        out_a[:,:,0]=np.roll(a[:,:,0],-amp,axis=1)      # R left
        out_a[:,:,2]=np.roll(a[:,:,2],amp,axis=1)        # B right
        # slice displacement
        nb=rs.randint(6,14)
        ys=np.sort(rs.randint(0,H,nb))
        prev=0
        for yb in list(ys)+[H]:
            sh=int(rs.uniform(-60,60)*g)
            out_a[prev:yb]=np.roll(out_a[prev:yb],sh,axis=1)
            prev=yb
        # occasional cyan tint band
        if rs.rand()<0.4:
            b0=rs.randint(0,H-200); out_a[b0:b0+rs.randint(40,160),:,1]+=40*g; out_a[b0:b0+120,:,2]+=50*g
        # scanline darkening
        out_a[::3]*=0.85
        a=out_a
    Image.fromarray(np.clip(a,0,255).astype(np.uint8)).save(os.path.join(out,f'p{i:03d}.png'))
mp4='C:/Users/User/Downloads/0616_fx_glitch.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True); print('SAVED',mp4)
