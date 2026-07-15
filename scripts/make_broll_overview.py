"""Overview mockups for the 5 b-rolls in their INTENDED form, so the user can see
what each will look like before placing:
  1 pipeline      -> full-screen graphic
  2 one-man hub   -> graphic BEHIND Amine (rembg cutout composited on top)
  3 agency burn   -> ledger panel BESIDE Amine (right side, over his frame)
  4 10-leads stat -> lower-third stat strip overlay (Amine stays on cam)
  5 build/run/own -> full-screen 3-step flow
Saves each full-res to Downloads + a tiled overview.
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG=(13,12,11); CARD=(20,20,20); CARDHI=(26,22,18); BORDER=(44,44,44)
WHITE=(245,245,245); GOLD=(200,148,62); ORANGE=(232,118,45); GRAY=(150,150,150)
MUTE=(95,95,95); RED=(214,69,60); GREEN=(90,200,120)
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
PFI='C:/Users/User/capcut-ai-editor/brandfonts/Playfair-Italic.ttf'
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

AMINE=Image.open('C:/Users/User/capcut-ai-editor/refframes/amine_ref.png').convert('RGB')
CUT=Image.open('C:/Users/User/capcut-ai-editor/refframes/amine_cut.png').convert('RGBA')

# ---- 1 & 2 from their generators / composite ----
mock1=Image.open('C:/Users/User/capcut-ai-editor/refframes/broll1_preview.png').convert('RGB')

hub=Image.open('C:/Users/User/capcut-ai-editor/refframes/broll2_preview.png').convert('RGB').copy()
# darken hub slightly so the subject reads, then composite Amine on top
hub=Image.blend(hub, Image.new('RGB',(W,H),BG), 0.18)
mock2=hub.copy(); mock2.paste(CUT,(0,0),CUT)
d=ImageDraw.Draw(mock2)
ctext(d,W/2,1500,"You ARE the sales department",dm(44,700,30),RED)

# ---- 3: agency-burn ledger BESIDE Amine (right panel) ----
mock3=AMINE.copy()
# scrim under the panel for legibility
sc=Image.new('RGBA',(W,H),(0,0,0,0)); ds=ImageDraw.Draw(sc)
ds.rounded_rectangle((560,300,1040,1500),radius=28,fill=(10,9,8,235),outline=(60,48,34,255),width=2)
mock3=Image.alpha_composite(mock3.convert('RGBA'),sc).convert('RGB')
d=ImageDraw.Draw(mock3)
d.text((600,338),"AGENCY",font=dm(30,700,24),fill=GOLD)
d.text((600,376),"6 months in",font=dm(26,400,20),fill=MUTE)
rows=[("Month 1","-$12,000"),("Month 2","-$15,000"),("Month 3","-$10,000"),
      ("Month 4","-$15,000"),("Month 5","-$13,000"),("Month 6","-$15,000")]
ry=470
for lab,amt in rows:
    d.text((600,ry),lab,font=dm(30,500,20),fill=GRAY)
    rtext(d,1010,ry,amt,dm(30,600,20),WHITE); ry+=72
d.line((600,ry+6,1010,ry+6),fill=BORDER,width=2)
d.text((600,ry+34),"TOTAL BURNED",font=dm(28,700,20),fill=MUTE)
rtext(d,1010,ry+78,"-$100K",dm(74,800,40),RED)
d.text((600,ry+184),"Closed deals",font=dm(30,600,20),fill=GRAY)
rtext(d,1010,ry+180,"0",dm(56,800,40),RED)

# ---- 4: 10-leads lower-third stat strip overlay ----
mock4=AMINE.copy()
sc=Image.new('RGBA',(W,H),(0,0,0,0)); ds=ImageDraw.Draw(sc)
ds.rectangle((0,1360,W,1920),fill=(0,0,0,0))
# gradient-ish scrim band
band=Image.new('RGBA',(W,H),(0,0,0,0)); db=ImageDraw.Draw(band)
db.rounded_rectangle((50,1380,1030,1740),radius=30,fill=(10,9,8,225),outline=(70,56,38,255),width=2)
mock4=Image.alpha_composite(mock4.convert('RGBA'),band).convert('RGB')
d=ImageDraw.Draw(mock4)
d.text((92,1410),"RESULT  /  LIVE LAUNCH",font=dm(28,700,24),fill=GOLD)
d.text((92,1470),"10",font=dm(150,800,40),fill=WHITE)
lw=d.textlength("10",font=dm(150,800,40))
d.text((92+lw+24,1500),"LEADS",font=dm(66,800,40),fill=ORANGE)
d.text((92+lw+24,1582),"in 12 hours",font=pfi(48,500),fill=GRAY)
rtext(d,1000,1486,"from a system",dm(34,600,24),WHITE)
rtext(d,1000,1532,"they OWN",dm(34,700,24),GOLD)
rtext(d,1000,1602,"sales team asked to pause",dm(26,400,20),MUTE)

# ---- 5: BUILD -> RUN -> OWN full-screen flow ----
mock5=glow_bg(); d=ImageDraw.Draw(mock5)
d.text((70,250),"THE UNSCALE MODEL",font=dm(34,700,30),fill=GOLD)
ctext(d,W/2,320,"How it actually works",pfi(82),WHITE)
steps=[("1","BUILD IT","We build the system with you",GRAY),
       ("2","RUN IT","We run it together, live",GRAY),
       ("3","OWN IT","Yours. Forever.",ORANGE)]
sx0,sy0,sw,sh,gap=90,560,900,300,70
for i,(num,title,sub,accent) in enumerate(steps):
    y=sy0+i*(sh+gap)
    if i<2:
        d.line((sx0+90,y+sh,sx0+90,y+sh+gap),fill=(70,56,38),width=5)
    hl=(accent==ORANGE)
    d.rounded_rectangle((sx0,y,sx0+sw,y+sh),radius=26,
                        fill=CARDHI if hl else CARD,outline=(120,86,40) if hl else BORDER,width=3 if hl else 2)
    d.ellipse((sx0+34,y+sh/2-56,sx0+34+112,y+sh/2+56),fill=(34,27,20),outline=accent,width=4)
    ctext(d,sx0+34+56,y+sh/2-44,num,dm(64,800,40),accent)
    d.text((sx0+210,y+72),title,font=dm(58,800,40),fill=WHITE if not hl else ORANGE)
    d.text((sx0+210,y+158),sub,font=dm(34,400,24),fill=GRAY)

# ---- save full-res to Downloads + build overview tile ----
DL='C:/Users/User/Downloads/'
mocks=[("1_pipeline",mock1),("2_oneman",mock2),("3_agencyburn",mock3),("4_10leads",mock4),("5_buildrunown",mock5)]
for name,im in mocks:
    im.save(f'{DL}0616_broll{name}_preview.png')
# tile 5 across
tw=360; th=int(th if False else tw*H/W)
sheet=Image.new('RGB',(tw*5+6*14,th+28),(18,18,18))
for i,(name,im) in enumerate(mocks):
    t=im.resize((tw,th)); sheet.paste(t,(14+i*(tw+14),14))
sheet.save(f'{DL}0616_broll_OVERVIEW.png')
sheet.save('C:/Users/User/capcut-ai-editor/refframes/broll_overview.png')
print("saved 5 mockups + overview to Downloads")
