"""Reference-style bullet-list build: cyan-outlined boxes appearing one by one over footage."""
import os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
CYAN=(40,205,225); WHITE=(240,248,250)
SRC0,DUR=343.0,4.0
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
def dm(sz,w=700,o=24):
    f=ImageFont.truetype(DMS,sz); f.set_variation_by_axes([o,w]); return f
def ease(t): t=max(0,min(1,t)); return t*t*(3-2*t)

ITEMS=[("IT'S VAGUE",0.4),("IT'S LAZY",1.2),("IT JUST SCREAMS|MASS EMAIL",2.0)]
BX1=1020; BW=520; FNT=dm(46)
tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(SRC0),'-i',FRONT,'-t',str(DUR),'-vf',CROP,os.path.join(tmp,'f%03d.png')],capture_output=True)
frames=sorted(f for f in os.listdir(tmp) if f.startswith('f')); N=len(frames)
out=tempfile.mkdtemp()
for i,fn in enumerate(frames):
    t=i/FPS
    base=Image.open(os.path.join(tmp,fn)).convert('RGBA')
    layer=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    y=300
    for text,st in ITEMS:
        lines=text.split('|'); bh=86 if len(lines)==1 else 150
        p=ease((t-st)/0.22)
        if p>0.01:
            a=int(255*p); dx=int((1-p)*50)
            x0=BX1-BW+dx; x1=BX1+dx
            d.rounded_rectangle((x0,y,x1,y+bh),radius=18,fill=(8,16,24,int(205*p)),outline=CYAN+(a,),width=3)
            ty=y+(bh-(len(lines)*52))//2+4
            for ln in lines:
                w=d.textlength(ln,font=FNT); d.text((x1-30-w,ty),ln,font=FNT,fill=WHITE+(a,)); ty+=52
        y+=bh+24
    im=Image.alpha_composite(base,layer).convert('RGB')
    im.save(os.path.join(out,f'p{i:03d}.png'))
mp4='C:/Users/User/Downloads/0616_fx_bullets.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True); print('SAVED',mp4)
