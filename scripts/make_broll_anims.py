"""Animate b-rolls #2-#5 (in their intended form) and export mp4s to Downloads.
#1 already animated by make_broll1_pipeline.py. On-camera ones (#2 bg, #3 beside, #4 strip)
animate the graphic over a still Amine frame so you can preview the motion in context.
"""
import os, subprocess, tempfile, shutil, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG=(13,12,11); CARD=(20,20,20); CARDHI=(26,22,18); BORDER=(44,44,44)
WHITE=(245,245,245); GOLD=(200,148,62); ORANGE=(232,118,45); GRAY=(150,150,150)
MUTE=(95,95,95); RED=(214,69,60); GREEN=(90,200,120)
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI='C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
FFMPEG='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
        r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
DL='C:/Users/User/Downloads/'
_c={}
def dm(sz,w,o=14):
    k=(sz,w,o)
    if k not in _c:
        f=ImageFont.truetype(DMS,sz); f.set_variation_by_axes([o,w]); _c[k]=f
    return _c[k]
def pfi(sz,w=500):
    k=('p',sz,w)
    if k not in _c:
        f=ImageFont.truetype(PFI,sz); f.set_variation_by_axes([w]); _c[k]=f
    return _c[k]
def ease(t): t=max(0.0,min(1.0,t)); return t*t*(3-2*t)
def lerp(a,b,t): return tuple(int(x+(y-x)*max(0,min(1,t))) for x,y in zip(a,b))
def ctext(d,cx,y,s,font,fill):
    w=d.textlength(s,font=font); d.text((cx-w/2,y),s,font=font,fill=fill)
def rtext(d,rx,y,s,font,fill):
    w=d.textlength(s,font=font); d.text((rx-w,y),s,font=font,fill=fill)

def glow_bg():
    yy,xx=np.mgrid[0:H,0:W].astype(np.float32)
    arr=np.zeros((H,W,3),np.float32); arr[:]=BG
    for gx,gy in [(0,120),(W,120)]:
        g=np.clip(1-np.sqrt((xx-gx)**2+(yy-gy)**2)/860,0,1)**2*0.16
        for i in range(3): arr[:,:,i]+=ORANGE[i]*g
    return Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
GBG=glow_bg()
AMINE=Image.open('C:/Users/User/capcut-ai-editor/refframes/amine_ref.png').convert('RGB')
CUT=Image.open('C:/Users/User/capcut-ai-editor/refframes/amine_cut.png').convert('RGBA')
AMINE_DARK=Image.blend(AMINE, Image.new('RGB',(W,H),BG), 0.0)

# ===================== #2 hub behind Amine =====================
HUBX,HUBY=540,1010   # branches converge onto Amine (the hub)
TASKS=["Cold emails","LinkedIn DMs","Follow-ups","Booking calls","Prospecting","Pitching"]
CHIP_YS=[470,640,810]
NODES=[(195,CHIP_YS[0]),(885,CHIP_YS[0]),
       (195,CHIP_YS[1]),(885,CHIP_YS[1]),
       (195,CHIP_YS[2]),(885,CHIP_YS[2])]   # two columns flanking his head, all visible
def hub_base():
    img=GBG.copy(); d=ImageDraw.Draw(img)
    d.text((70,205),"ORG CHART",font=dm(34,700,30),fill=GOLD)
    d.text((300,205),"/ SALES DEPARTMENT",font=dm(34,500,30),fill=MUTE)
    ctext(d,W/2,268,"Who runs your sales?",pfi(82),WHITE)
    return img
HUB_BASE=hub_base()
def chip(d,cxy,text,p):
    cw,ch=300,86; x,y=cxy[0]-cw/2,cxy[1]-ch/2
    d.rounded_rectangle((x,y,x+cw,y+ch),radius=20,fill=lerp(BG,CARD,p),outline=lerp(BG,BORDER,p),width=2)
    d.ellipse((x+22,y+ch/2-6,x+34,y+ch/2+6),fill=lerp(BG,ORANGE,p))
    ctext(d,cxy[0]+16,cxy[1]-16,text,dm(28,600,20),lerp(BG,WHITE,p))
def frame2(t):
    im=HUB_BASE.copy(); d=ImageDraw.Draw(im)
    for i,(nx,ny) in enumerate(NODES):
        p=ease((t-0.10-i*0.06)/0.16)
        if p<=0.01: continue
        ex,ey=HUBX+(nx-HUBX)*p,HUBY+(ny-HUBY)*p
        d.line((HUBX,HUBY,ex,ey),fill=lerp(BG,(70,60,50),p),width=4)
        chip(d,(nx,ny),TASKS[i],p)
    # composite Amine over the hub (he is the center)
    im=im.convert('RGBA'); im.alpha_composite(CUT); im=im.convert('RGB')
    d=ImageDraw.Draw(im)
    pk=ease((t-0.72)/0.16)
    if pk>0.01: ctext(d,W/2,1500,"You ARE the sales department",dm(44,700,30),lerp(BG,RED,pk))
    return im

# ===================== #3 agency money-burn FULL-SCREEN =====================
ROWS=[("Month 1","-$12,000"),("Month 2","-$15,000"),("Month 3","-$10,000"),
      ("Month 4","-$15,000"),("Month 5","-$13,000"),("Month 6","-$15,000")]
def frame3(t):
    im=GBG.copy(); d=ImageDraw.Draw(im)
    pf=ease(t/0.08)
    d.text((70,250),"THE AGENCY ROUTE",font=dm(34,700,30),fill=lerp(BG,GOLD,pf))
    ctext(d,W/2,320,"Where did the money go?",pfi(82),lerp(BG,WHITE,pf))
    x0,y0,x1,y1=80,460,1000,1230
    d.rounded_rectangle((x0,y0,x1,y1),radius=28,fill=CARD,outline=BORDER,width=2)
    if pf>0.5:
        d.text((x0+44,y0+34),"AGENCY  ·  6 MONTHS",font=dm(28,700,24),fill=MUTE)
        rtext(d,x1-44,y0+34,"5-15K / mo",dm(28,500,24),GRAY)
    d.line((x0+44,y0+92,x1-44,y0+92),fill=BORDER,width=2)
    ry=y0+130
    for i,(lab,amt) in enumerate(ROWS):
        p=ease((t-0.12-i*0.07)/0.14)
        if p>0.01:
            dx=int((1-p)*26)
            d.text((x0+44+dx,ry),lab,font=dm(34,500,24),fill=lerp(BG,GRAY,p))
            rtext(d,x1-44+dx,ry,amt,dm(34,600,24),lerp(BG,WHITE,p))
        ry+=78
    pt=ease((t-0.66)/0.20)
    if pt>0.01:
        d.line((x0+44,ry+8,x1-44,ry+8),fill=(80,60,40),width=2)
        d.text((x0+44,ry+44),"TOTAL BURNED",font=dm(32,700,24),fill=lerp(BG,MUTE,pt))
        val=int(round(100*pt))
        rtext(d,x1-44,ry+28,f"-${val}K",dm(92,800,40),lerp(BG,RED,pt))
    pc=ease((t-0.84)/0.14)
    if pc>0.01:
        ctext(d,W/2,1330,"CLOSED DEALS",dm(40,700,30),lerp(BG,GRAY,pc))
        ctext(d,W/2,1392,"0",dm(150,800,40),lerp(BG,RED,pc))
    return im

# ===================== #4 10-leads TOP strip =====================
def frame4(t):
    base=AMINE.convert('RGBA')
    p=ease(t/0.12)
    band=Image.new('RGBA',(W,H),(0,0,0,0)); db=ImageDraw.Draw(band)
    db.rounded_rectangle((50,180,1030,556),radius=30,fill=(10,9,8,int(228*p)),outline=(70,56,38,int(255*p)),width=2)
    im=Image.alpha_composite(base,band).convert('RGB'); d=ImageDraw.Draw(im)
    if p>0.4:
        d.text((92,212),"RESULT  /  LIVE LAUNCH",font=dm(28,700,24),fill=GOLD)
    pn=ease((t-0.18)/0.30)
    num=str(int(round(10*pn)))
    bigf=dm(150,800,40)
    d.text((92,274),num,font=bigf,fill=lerp(BG,WHITE,min(1,pn*3)))
    lw=d.textlength(num,font=bigf)
    pl=ease((t-0.42)/0.18)
    if pl>0.01:
        d.text((92+lw+24,304),"LEADS",font=dm(66,800,40),fill=lerp(BG,ORANGE,pl))
        d.text((92+lw+24,386),"in 12 hours",font=pfi(48,500),fill=lerp(BG,GRAY,pl))
    pr=ease((t-0.56)/0.18)
    if pr>0.01:
        rtext(d,1000,290,"from a system",dm(34,600,24),lerp(BG,WHITE,pr))
        rtext(d,1000,336,"they OWN",dm(34,700,24),lerp(BG,GOLD,pr))
        rtext(d,1000,406,"sales team asked to pause",dm(26,400,20),lerp(BG,MUTE,pr))
    return im

# ===================== #5 build -> run -> own =====================
STEPS=[("1","BUILD IT","We build the system with you"),
       ("2","RUN IT","We run it together, live"),
       ("3","OWN IT","Yours. Forever.")]
def frame5(t):
    im=GBG.copy(); d=ImageDraw.Draw(im)
    pf=ease(t/0.08)
    d.text((70,250),"THE UNSCALE MODEL",font=dm(34,700,30),fill=lerp(BG,GOLD,pf))
    ctext(d,W/2,320,"How it actually works",pfi(82),lerp(BG,WHITE,pf))
    sx0,sy0,sw,sh,gap=90,560,900,300,70
    for i,(num,title,sub) in enumerate(STEPS):
        p=ease((t-0.14-i*0.20)/0.22)
        if p<=0.01: continue
        y=sy0+i*(sh+gap)
        hl=(i==2)
        last=i==2
        accent=ORANGE if hl else GRAY
        if i<2:
            lp=ease((t-0.14-i*0.20-0.12)/0.12)
            d.line((sx0+90,y+sh,sx0+90,y+sh+int(gap*lp)),fill=(70,56,38),width=5)
        dy=int((1-p)*24)
        d.rounded_rectangle((sx0,y+dy,sx0+sw,y+sh+dy),radius=26,
                            fill=CARDHI if hl else CARD,outline=lerp(BG,(120,86,40) if hl else BORDER,p),width=3 if hl else 2)
        d.ellipse((sx0+34,y+dy+sh/2-56,sx0+34+112,y+dy+sh/2+56),fill=(34,27,20),outline=lerp(BG,accent,p),width=4)
        ctext(d,sx0+34+56,y+dy+sh/2-44,num,dm(64,800,40),lerp(BG,accent,p))
        d.text((sx0+210,y+dy+72),title,font=dm(58,800,40),fill=lerp(BG,ORANGE if hl else WHITE,p))
        d.text((sx0+210,y+dy+158),sub,font=dm(34,400,24),fill=lerp(BG,GRAY,p))
    return im

import sys
JOBS=[("2_oneman",frame2,7),("3_agencyburn",frame3,7),("4_10leads",frame4,6),("5_buildrunown",frame5,6)]
ONLY=sys.argv[1:]
FPS=30
for name,fn,secs in JOBS:
    if ONLY and not any(o in name for o in ONLY): continue
    tot=FPS*secs; tmp=tempfile.mkdtemp()
    for fr in range(tot): fn(fr/(tot-1)).save(os.path.join(tmp,f'f{fr:04d}.png'))
    out=f'{DL}0616_broll{name}.mp4'
    subprocess.run([FFMPEG,'-y','-framerate',str(FPS),'-i',os.path.join(tmp,'f%04d.png'),
                    '-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),out],capture_output=True)
    shutil.rmtree(tmp,ignore_errors=True); print('saved',out)
print('done')
