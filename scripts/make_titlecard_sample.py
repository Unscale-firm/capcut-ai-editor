"""Reference-style animated title card: dark bg, cyan text + geometric chevron icon + dot, big number.
"""
import os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
CYAN=(40,205,225); CYAN_D=(20,120,140); WHITE=(235,245,248)
DUR=4.0
def dm(sz,w=800,o=30):
    f=ImageFont.truetype(DMS,sz); f.set_variation_by_axes([o,w]); return f
def ease(t): t=max(0,min(1,t)); return t*t*(3-2*t)
def lerp(a,b,t): return tuple(int(x+(y-x)*max(0,min(1,t))) for x,y in zip(a,b))

# dark navy gradient bg
yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
g=1-((yy-H*0.35)**2/(H*0.9)**2+(xx-W/2)**2/(W*0.9)**2)
g=np.clip(g,0,1)
arr=np.zeros((H,W,3),np.float32)
top=np.array([14,30,46]); bot=np.array([5,11,20])
for c in range(3): arr[:,:,c]=bot[c]+(top[c]-bot[c])*g
BG=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))

def ls_text(d,cx,y,s,font,fill,ls):
    w=sum(d.textlength(c,font=font)+ls for c in s)-ls
    x=cx-w/2
    for c in s: d.text((x,y),c,font=font,fill=fill); x+=d.textlength(c,font=font)+ls
    return w

tmp=tempfile.mkdtemp()
for i in range(int(DUR*FPS)):
    t=i/FPS
    im=BG.copy(); d=ImageDraw.Draw(im)
    pd=ease(t/0.30)            # dot
    pt=ease((t-0.25)/0.35)     # title
    pc=ease((t-0.50)/0.40)     # chevron + number
    # dot
    if pd>0.01:
        r=int(11*pd); d.ellipse((540-r,610-r,540+r,610+r),fill=lerp((5,11,20),CYAN,pd))
    # DIFFERENCE
    if pt>0.01:
        ls_text(d,540,700,"DIFFERENCE",dm(58,700,30),lerp((5,11,20),CYAN,pt),10)
    # chevron (up arrow) + big number
    if pc>0.01:
        col=lerp((5,11,20),CYAN,pc); cy0=900
        d.line((430,cy0+120,540,cy0),fill=col,width=10,joint='curve')
        d.line((540,cy0,650,cy0+120),fill=col,width=10,joint='curve')
        d.line((540,cy0+30,540,cy0+300),fill=lerp((5,11,20),CYAN_D,pc),width=4)
        nf=dm(220,800,40); s="1"; w=d.textlength(s,font=nf)
        d.text((540-w/2,cy0+300),s,font=nf,fill=lerp((5,11,20),WHITE,pc))
    im.save(os.path.join(tmp,f'p{i:03d}.png'))
mp4='C:/Users/User/Downloads/0616_fx_titlecard.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(tmp,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); print('SAVED',mp4)
