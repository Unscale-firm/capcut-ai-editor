"""Recreate the reference's energy/light-burst effect on a 4s clip of 0616 footage,
in the UNSCALE palette (orange/gold) instead of cyan. Streaks radiate + glow, burst mid-clip.
"""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'
ORANGE=(232,118,45); GOLD=(200,148,62)
SRC0,DUR=343.0,4.0
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
CX,CY=540,660            # burst origin (around his head/shoulders)

# footage
tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(SRC0),'-i',FRONT,'-t',str(DUR),'-vf',CROP,os.path.join(tmp,'f%03d.png')],capture_output=True)
frames=sorted(f for f in os.listdir(tmp) if f.startswith('f'))
N=len(frames)

rng=np.random.RandomState(7)
NS=70
ANG=rng.uniform(0,360,NS)
LEN=rng.uniform(360,940,NS)
BRI=rng.uniform(0.5,1.0,NS)
PH=rng.uniform(0,6.28,NS)
def lerp(a,b,t): return tuple(int(x+(y-x)*t) for x,y in zip(a,b))

def burst(t):  # 0..1 intensity, peaks ~1.4-1.9s
    if t<0.4: return 0.0
    if t<1.4: return (t-0.4)/1.0
    if t<2.0: return 1.0
    if t<3.4: return max(0.0,1-(t-2.0)/1.4)
    return 0.0

out=tempfile.mkdtemp()
for i,fn in enumerate(frames):
    t=i/FPS
    b=burst(t)
    foot=np.asarray(Image.open(os.path.join(tmp,fn)).convert('RGB'),np.float32)
    if b>0.01:
        layer=Image.new('RGB',(W,H),(0,0,0)); d=ImageDraw.Draw(layer)
        rot=t*22
        for k in range(NS):
            a=math.radians(ANG[k]+rot)
            ln=LEN[k]*(0.55+0.45*math.sin(t*5+PH[k]))*b
            x2=CX+math.cos(a)*ln; y2=CY+math.sin(a)*ln
            col=lerp(ORANGE,GOLD,(k%7)/6)
            br=BRI[k]*b
            d.line((CX,CY,x2,y2),fill=tuple(int(c*br) for c in col),width=3)
            d.line((CX,CY,(CX+x2)/2,(CY+y2)/2),fill=tuple(min(255,int(c*br*1.6)) for c in col),width=2)
        layer=layer.filter(ImageFilter.GaussianBlur(3))
        la=np.asarray(layer,np.float32)
        # central glow
        yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
        g=np.clip(1-np.sqrt((xx-CX)**2+(yy-CY)**2)/520,0,1)**2*0.5*b
        for c in range(3): la[:,:,c]+=ORANGE[c]*g
        final=np.clip(foot+la,0,255)
    else:
        final=foot
    Image.fromarray(final.astype(np.uint8)).save(os.path.join(out,f'p{i:03d}.png'))

mp4='C:/Users/User/Downloads/0616_lightburst_sample.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True)
print('SAVED',mp4)
