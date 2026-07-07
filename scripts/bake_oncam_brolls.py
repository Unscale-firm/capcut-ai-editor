"""Bake the on-camera b-rolls onto Amine's LIVE front footage at their real windows:
  #2 (behind him): rembg cutout per frame, hub graphic behind, crossfade bg in/out.
  #4 (over him):   10-leads top strip composited on top.
Front (track0) footage is continuous on the timeline; we extract each overlapping segment's
source range (1.5x crop to match the edit) so he moves naturally. Outputs mp4s to Downloads.
"""
import json, os, subprocess, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from rembg import remove, new_session

W, H = 1080, 1920
BG=(13,12,11); CARD=(20,20,20); BORDER=(44,44,44); WHITE=(245,245,245)
GOLD=(200,148,62); ORANGE=(232,118,45); GRAY=(150,150,150); MUTE=(95,95,95); RED=(214,69,60)
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI='C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
FPS=30
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
_c={}
def dm(sz,w,o=14):
    k=(sz,w,o)
    if k not in _c: f=ImageFont.truetype(DMS,sz); f.set_variation_by_axes([o,w]); _c[k]=f
    return _c[k]
def pfi(sz,w=500):
    k=('p',sz,w)
    if k not in _c: f=ImageFont.truetype(PFI,sz); f.set_variation_by_axes([w]); _c[k]=f
    return _c[k]
def ease(t): t=max(0.0,min(1.0,t)); return t*t*(3-2*t)
def lerp(a,b,t): return tuple(int(x+(y-x)*max(0,min(1,t))) for x,y in zip(a,b))
def ctext(d,cx,y,s,font,fill):
    w=d.textlength(s,font=font); d.text((cx-w/2,y),s,font=font,fill=fill)
def rtext(d,rx,y,s,font,fill):
    w=d.textlength(s,font=font); d.text((rx-w,y),s,font=font,fill=fill)
def glow_bg():
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32); arr=np.zeros((H,W,3),np.float32); arr[:]=BG
    for gx,gy in [(0,120),(W,120)]:
        g=np.clip(1-np.sqrt((xx-gx)**2+(yy-gy)**2)/860,0,1)**2*0.16
        for i in range(3): arr[:,:,i]+=ORANGE[i]*g
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
GBG=glow_bg()

# ---------- timeline front-footage extraction ----------
d=json.load(open(PROJ,encoding='utf-8'))
vmat={m['id']:m for m in d['materials']['videos']}
track0=[t for t in d['tracks'] if t['type']=='video'][0]
FRONT=next(m['path'] for m in d['materials']['videos'] if 'C9146' in m['path'])
def extract_window(a_us,b_us,tmp):
    """extract continuous timeline front footage [a,b] (us) as ordered frame paths."""
    idx=0; paths=[]
    for s in track0['segments']:
        st=s['target_timerange']['start']; en=st+s['target_timerange']['duration']
        lo=max(a_us,st); hi=min(b_us,en)
        if hi<=lo: continue
        src=(s['source_timerange']['start']+(lo-st))/1e6; dur=(hi-lo)/1e6
        sub=os.path.join(tmp,f'seg{idx}_%04d.png')
        subprocess.run([FF,'-y','-ss',str(src),'-i',FRONT,'-t',str(dur),'-vf',CROP,sub],capture_output=True)
        for f in sorted(x for x in os.listdir(tmp) if x.startswith(f'seg{idx}_')): paths.append(os.path.join(tmp,f))
        idx+=1
    return paths

# ---------- #2 hub layout ----------
TASKS=["Cold emails","LinkedIn DMs","Follow-ups","Booking calls","Prospecting","Pitching"]
CHIP_YS=[470,640,810]
NODES=[(195,CHIP_YS[0]),(885,CHIP_YS[0]),(195,CHIP_YS[1]),(885,CHIP_YS[1]),(195,CHIP_YS[2]),(885,CHIP_YS[2])]
HUBX,HUBY=540,1010
def hub_base():
    img=GBG.copy(); d2=ImageDraw.Draw(img)
    d2.text((70,205),"ORG CHART",font=dm(34,700,30),fill=GOLD)
    d2.text((300,205),"/ SALES DEPARTMENT",font=dm(34,500,30),fill=MUTE)
    ctext(d2,W/2,268,"Who runs your sales?",pfi(82),WHITE)
    return img
HUB_BASE=hub_base()
def hub_at(t):
    im=HUB_BASE.copy(); d2=ImageDraw.Draw(im)
    for i,(nx,ny) in enumerate(NODES):
        p=ease((t-0.10-i*0.06)/0.16)
        if p<=0.01: continue
        ex,ey=HUBX+(nx-HUBX)*p,HUBY+(ny-HUBY)*p
        d2.line((HUBX,HUBY,ex,ey),fill=lerp(BG,(70,60,50),p),width=4)
        cw,ch=300,86; x,y=nx-cw/2,ny-ch/2
        d2.rounded_rectangle((x,y,x+cw,y+ch),radius=20,fill=lerp(BG,CARD,p),outline=lerp(BG,BORDER,p),width=2)
        d2.ellipse((x+22,y+ch/2-6,x+34,y+ch/2+6),fill=lerp(BG,ORANGE,p))
        ctext(d2,nx+16,ny-16,TASKS[i],dm(28,600,20),lerp(BG,WHITE,p))
    pk=ease((t-0.72)/0.16)
    if pk>0.01: ctext(d2,W/2,1500,"You ARE the sales department",dm(44,700,30),lerp(BG,RED,pk))
    return np.asarray(im,dtype=np.float32)

def strip_at(t):
    """RGBA top strip for #4."""
    p=ease(t/0.12)
    im=Image.new('RGBA',(W,H),(0,0,0,0)); d2=ImageDraw.Draw(im)
    d2.rounded_rectangle((50,180,1030,556),radius=30,fill=(10,9,8,int(228*p)),outline=(70,56,38,int(255*p)),width=2)
    if p>0.4: d2.text((92,212),"RESULT  /  LIVE LAUNCH",font=dm(28,700,24),fill=GOLD)
    pn=ease((t-0.18)/0.30); num=str(int(round(10*pn))); bigf=dm(150,800,40)
    d2.text((92,274),num,font=bigf,fill=lerp(BG,WHITE,min(1,pn*3))); lw=d2.textlength(num,font=bigf)
    pl=ease((t-0.42)/0.18)
    if pl>0.01:
        d2.text((92+lw+24,304),"LEADS",font=dm(66,800,40),fill=lerp(BG,ORANGE,pl))
        d2.text((92+lw+24,386),"in 12 hours",font=pfi(48,500),fill=lerp(BG,GRAY,pl))
    pr=ease((t-0.56)/0.18)
    if pr>0.01:
        rtext(d2,1000,290,"from a system",dm(34,600,24),lerp(BG,WHITE,pr))
        rtext(d2,1000,336,"they OWN",dm(34,700,24),lerp(BG,GOLD,pr))
        rtext(d2,1000,406,"sales team asked to pause",dm(26,400,20),lerp(BG,MUTE,pr))
    return im

def bake(name,start_s,dur_s,mode):
    tmp=tempfile.mkdtemp()
    frames=extract_window(int(start_s*1e6),int((start_s+dur_s)*1e6),tmp)
    N=len(frames); FADE=10
    sess=new_session('u2net_human_seg') if mode=='bg' else None
    outdir=tempfile.mkdtemp()
    for i,fp in enumerate(frames):
        t=i/(N-1) if N>1 else 1.0
        foot=Image.open(fp).convert('RGB'); fa=np.asarray(foot,dtype=np.float32)
        if mode=='bg':
            cut=remove(foot.resize((540,960)),session=sess)
            pa=np.asarray(cut.split()[3].resize((W,H),Image.BILINEAR),dtype=np.float32)/255.0
            ea=1.0
            if i<FADE: ea=i/FADE
            elif i>=N-FADE: ea=(N-1-i)/FADE
            hub=hub_at(t)
            pa3=pa[...,None]; e=ea
            final=fa*pa3 + (fa*(1-e)+hub*e)*(1-pa3)
        else:  # overlay
            strip=strip_at(t)
            comp=Image.fromarray(fa.astype(np.uint8)).convert('RGBA'); comp.alpha_composite(strip)
            final=np.asarray(comp.convert('RGB'),dtype=np.float32)
        Image.fromarray(np.clip(final,0,255).astype(np.uint8)).save(os.path.join(outdir,f'p{i:04d}.png'))
        if i%30==0: print(f'{name}: {i}/{N}',flush=True)
    out=f'C:/Users/User/Downloads/0616_{name}_baked.mp4'
    subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(outdir,'p%04d.png'),
                    '-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),out],capture_output=True)
    shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(outdir,ignore_errors=True)
    print('SAVED',out,'| place at',start_s,'-',round(start_s+dur_s,2),flush=True)

bake('broll2_oneman',15.3,7.0,'bg')
bake('broll4_10leads',75.5,6.0,'overlay')
print('done')
