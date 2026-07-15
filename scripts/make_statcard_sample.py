"""Reference-style floating stat/scorecard card over footage (cyan accent), slides in."""
import os, subprocess, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
SRC0,DUR=343.0,4.0
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
CARD=(18,22,30); BORD=(40,70,90); INK=(235,242,246); GRAY=(140,148,156); CYAN=(40,205,225); GREEN=(90,210,140)
def dm(sz,w=500,o=22):
    f=ImageFont.truetype(DMS,sz); f.set_variation_by_axes([o,w]); return f
def ease(t): t=max(0,min(1,t)); return t*t*(3-2*t)

ROWS=[("Reply rate","11.2%",CYAN),("Meetings booked","14",INK),("Closed deals","3",GREEN)]
tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(SRC0),'-i',FRONT,'-t',str(DUR),'-vf',CROP,os.path.join(tmp,'f%03d.png')],capture_output=True)
frames=sorted(f for f in os.listdir(tmp) if f.startswith('f')); N=len(frames)
out=tempfile.mkdtemp()
for i,fn in enumerate(frames):
    t=i/FPS
    base=Image.open(os.path.join(tmp,fn)).convert('RGBA')
    layer=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    p=ease((t-0.3)/0.4)
    if p>0.01:
        dy=int((1-p)*50); a=int(255*p)
        x0,y0,x1,y1=70,1150+dy,1010,1630+dy
        d.rounded_rectangle((x0,y0,x1,y1),radius=24,fill=CARD+(a,),outline=BORD+(a,),width=2)
        d.text((x0+40,y0+34),"OUTREACH SCORECARD",font=dm(30,700,24),fill=CYAN+(a,))
        d.text((x0+40,y0+78),"system they own · live",font=dm(26,400,20),fill=GRAY+(a,))
        d.line((x0+40,y0+136,x1-40,y0+136),fill=BORD+(a,),width=2)
        ry=y0+172
        for j,(lab,val,col) in enumerate(ROWS):
            rp=ease((t-0.5-j*0.18)/0.25)
            if rp>0.01:
                d.text((x0+40,ry),lab,font=dm(38,500,24),fill=GRAY+(int(255*rp),))
                vw=d.textlength(val,font=dm(46,800,30))
                d.text((x1-40-vw,ry-4),val,font=dm(46,800,30),fill=col+(int(255*rp),))
            ry+=104
    im=Image.alpha_composite(base,layer).convert('RGB')
    im.save(os.path.join(out,f'p{i:03d}.png'))
mp4='C:/Users/User/Downloads/0616_fx_statcard.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True); print('SAVED',mp4)
