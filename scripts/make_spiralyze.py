"""Spiralyze LOGO ONLY, centered above his head, over live footage at 71.5-74.5s.
Color-keys white bg out; adds a soft dark glow so the blue logo reads on any background.
New filename (spiralyze2) to dodge CapCut's path cache.
"""
import json, os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W,H=1080,1920
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
LOGO='C:/Users/User/Downloads/spiralyze-logo.jpg'
FPS=30; CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'; START,DUR=71.5,3.0
def ease(t): t=max(0.0,min(1.0,t)); return t*t*(3-2*t)

# color-key white -> transparent, trim, scale
lg=Image.open(LOGO).convert('RGB'); a=np.asarray(lg).astype(np.int16)
white=(a[:,:,0]>234)&(a[:,:,1]>234)&(a[:,:,2]>234)
lg=lg.convert('RGBA'); lg.putalpha(Image.fromarray(np.where(white,0,255).astype(np.uint8)))
lg=lg.crop(lg.getbbox())
LH=300; LOGO_IMG=lg.resize((int(lg.width*LH/lg.height),LH),Image.LANCZOS)
# soft dark glow (blurred black silhouette) for legibility on any bg
sil=Image.new('RGBA',LOGO_IMG.size,(0,0,0,0)); sil.putalpha(LOGO_IMG.split()[3])
pad=60
GLOW=Image.new('RGBA',(LOGO_IMG.width+2*pad,LOGO_IMG.height+2*pad),(0,0,0,0))
GLOW.alpha_composite(sil,(pad,pad)); GLOW=GLOW.filter(ImageFilter.GaussianBlur(26))
LX=(W-LOGO_IMG.width)//2; LY=160

def logo_layer(t):
    p=ease(t/0.16); op=p
    if t>0.86: op*=ease((1-t)/0.14)
    dy=int((1-p)*-20)
    layer=Image.new('RGBA',(W,H),(0,0,0,0))
    layer.alpha_composite(GLOW,(LX-pad,LY+dy-pad)); layer.alpha_composite(GLOW,(LX-pad,LY+dy-pad))
    layer.alpha_composite(LOGO_IMG,(LX,LY+dy))
    if op<0.999:
        arr=np.asarray(layer).astype(np.float32); arr[:,:,3]*=op
        layer=Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
    return layer

# extract live front footage + overlay logo
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
out=tempfile.mkdtemp(); N=len(paths)
for i,fp in enumerate(paths):
    t=i/(N-1) if N>1 else 1.0
    im=Image.open(fp).convert('RGBA'); im.alpha_composite(logo_layer(t))
    im.convert('RGB').save(os.path.join(out,f'p{i:04d}.png'))
mp4='C:/Users/User/Downloads/0616_broll_spiralyze2.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True)
print('SAVED',mp4,'| place at',START,'-',round(START+DUR,2))
