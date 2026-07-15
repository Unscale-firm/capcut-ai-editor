"""Reference-style keyword captions on 4s footage: white bold caps + CYAN keyword + hand-drawn
underline scribble, pop-in per phrase, drop shadow for legibility.
"""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
WHITE=(245,245,245); CYAN=(34,200,222); SHADOW=(0,0,0)
SRC0,DUR=343.0,4.0
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
CY_TEXT=1470
def dm(sz,w=900):
    f=ImageFont.truetype(DMS,sz); f.set_variation_by_axes([40,w]); return f
FONT=dm(86)
def ease(t): t=max(0,min(1,t)); return t*t*(3-2*t)

# phrases: (start,end, [(word, color)], underline: None|'all'|index)
PHRASES=[(0.05,1.15,[("AND",WHITE),("THIS",WHITE),("IS",WHITE)],None),
         (1.20,2.55,[("EXACTLY",CYAN),("WHY",CYAN)],'all'),
         (2.60,3.95,[("IT",WHITE),("FAILS",CYAN)],1)]

tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(SRC0),'-i',FRONT,'-t',str(DUR),'-vf',CROP,os.path.join(tmp,'f%03d.png')],capture_output=True)
frames=sorted(f for f in os.listdir(tmp) if f.startswith('f')); N=len(frames)

def scribble(d,x0,x1,y,col):
    pts=[]; n=14
    for i in range(n+1):
        x=x0+(x1-x0)*i/n; yo=math.sin(i*1.3)*4+(np.random.RandomState(i).uniform(-3,3))
        pts.append((x,y+yo))
    for w,a in [(10,90),(6,255)]:
        d.line(pts,fill=col,width=w,joint='curve')

out=tempfile.mkdtemp()
for i,fn in enumerate(frames):
    t=i/FPS
    im=Image.open(os.path.join(tmp,fn)).convert('RGB'); d=ImageDraw.Draw(im)
    for st,en,words,ul in PHRASES:
        if not (st<=t<en): continue
        p=ease((t-st)/0.12); sc=0.85+0.15*p
        fnt=dm(int(86*sc))
        sp=fnt.getlength(' ')
        widths=[fnt.getlength(w) for w,_ in words]
        total=sum(widths)+sp*(len(words)-1)
        x=(W-total)/2; key_x0=key_x1=None
        for (w,col),wd in zip(words,widths):
            d.text((x+3,CY_TEXT+3),w,font=fnt,fill=SHADOW)  # shadow
            d.text((x,CY_TEXT),w,font=fnt,fill=col)
            if col==CYAN and key_x0 is None: key_x0=x
            if col==CYAN: key_x1=x+wd
            x+=wd+sp
        if ul=='all' and key_x0 is not None:
            scribble(d,key_x0-6,key_x1+6,CY_TEXT+int(96*sc),CYAN)
        elif isinstance(ul,int):
            # underline the ul-th word
            xx=(W-total)/2
            for j,((w,col),wd) in enumerate(zip(words,widths)):
                if j==ul: scribble(d,xx-6,xx+wd+6,CY_TEXT+int(96*sc),CYAN); break
                xx+=wd+sp
    im.save(os.path.join(out,f'p{i:03d}.png'))

mp4='C:/Users/User/Downloads/0616_fx_captions.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True)
print('SAVED',mp4)
