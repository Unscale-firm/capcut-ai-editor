"""Render a 3s clip across the 0:53.7 front->side switch, 6 different transition styles,
so the user can compare. Front 1.5x, side reframed 1.43x (matched). Outputs to Downloads.
"""
import os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'; SIDE='C:/Users/User/Downloads/Video/C9138-cut925.MP4'
DL='C:/Users/User/Downloads/'
N=90; CUT=45                       # 3s @30fps, switch at 1.5s
FRONT_SRC=374.24; SIDE_SRC=379.767 # tl 52.2 : front + side(=front+5.527) source times
FCROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
SCROP='crop=755:1342:303:135,scale=1080:1920,fps=30'   # reframed side (matched)

tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(FRONT_SRC),'-i',FRONT,'-t','3.0','-vf',FCROP,os.path.join(tmp,'F%03d.png')],capture_output=True)
subprocess.run([FF,'-y','-ss',str(SIDE_SRC),'-i',SIDE,'-t','3.0','-vf',SCROP,os.path.join(tmp,'S%03d.png')],capture_output=True)
F=[np.asarray(Image.open(os.path.join(tmp,f'F{i+1:03d}.png')).convert('RGB'),np.float32) for i in range(N)]
S=[np.asarray(Image.open(os.path.join(tmp,f'S{i+1:03d}.png')).convert('RGB'),np.float32) for i in range(N)]

def zoom(a,f):
    if f<=1.001: return a
    nh,nw=int(H*f),int(W*f); big=np.asarray(Image.fromarray(a.astype(np.uint8)).resize((nw,nh),Image.BILINEAR),np.float32)
    oy,ox=(nh-H)//2,(nw-W)//2; return big[oy:oy+H,ox:ox+W]
def hblur(a,amt):
    if amt<1: return a
    acc=np.zeros_like(a); k=9
    for j in range(k):
        sh=int(-amt+2*amt*j/(k-1)); acc+=np.roll(a,sh,axis=1)
    return acc/k

def render(name,fn):
    out=tempfile.mkdtemp()
    for i in range(N):
        Image.fromarray(np.clip(fn(i),0,255).astype(np.uint8)).save(os.path.join(out,f'p{i:03d}.png'))
    mp4=DL+f'0616_TRANS_{name}.mp4'
    subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
    shutil.rmtree(out,ignore_errors=True); print('saved',mp4.split('/')[-1])

# 1 clean cut
render('1_cut', lambda i: F[i] if i<CUT else S[i])
# 2 cross-dissolve (12 frames)
def dissolve(i):
    D=6
    if i<CUT-D: return F[i]
    if i>=CUT+D: return S[i]
    ea=(i-(CUT-D))/(2*D); return F[i]*(1-ea)+S[i]*ea
render('2_dissolve', dissolve)
# 3 dip to black
def dip(i):
    D=5
    if i<CUT:
        b=1.0 if i<CUT-D else (CUT-i)/D; return F[i]*b
    b=1.0 if i>=CUT+D else (i-CUT)/D; return S[i]*b
render('3_dipblack', dip)
# 4 zoom-punch (front pushes in, side settles)
def punch(i):
    if i<CUT:
        k=CUT-i; f=1.0+0.10*max(0,(4-k))/4; return zoom(F[i],f)
    k=i-CUT; f=1.0+0.13*max(0,(8-k))/8; return zoom(S[i],f)
render('4_zoompunch', punch)
# 5 directional whip-pan (horizontal motion blur ramps into/out of cut)
def whip(i):
    if i<CUT:
        k=CUT-i; amt=max(0,(5-k))/5*70; return hblur(F[i],amt)
    k=i-CUT; amt=max(0,(5-k))/5*70; return hblur(S[i],amt)
render('5_whippan', whip)
# 6 glitch (RGB split + slice at the cut, 3 frames)
def glitch(i):
    base=F[i] if i<CUT else S[i]
    d=abs(i-CUT)
    if d>2: return base
    g=base.copy(); off=10*(3-d)
    g[:,:,0]=np.roll(base[:,:,0],off,axis=1); g[:,:,2]=np.roll(base[:,:,2],-off,axis=1)
    for b in range(0,H,120):
        s=((b//120)%2*2-1)*off*2; g[b:b+120]=np.roll(g[b:b+120],s,axis=1)
    return g
render('6_glitch', glitch)

shutil.rmtree(tmp,ignore_errors=True)
print('done — 6 samples in Downloads (0616_TRANS_*.mp4)')
