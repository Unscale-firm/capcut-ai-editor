"""Reference-style email-screenshot lower-third over footage, with a highlighted key phrase."""
import os, subprocess, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FRONT='C:/Users/User/Downloads/Video/C9146-cut925.MP4'
DMS='C:/Users/User/capcut-ai-editor/brandfonts/DMSans.ttf'
SRC0,DUR=343.0,4.0
CROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
CARD=(247,248,250); INK=(28,30,34); GRAY=(120,124,130); CYAN=(40,205,225); HL=(120,235,242)
def dm(sz,w=400,o=20):
    f=ImageFont.truetype(DMS,sz); f.set_variation_by_axes([o,w]); return f
def ease(t): t=max(0,min(1,t)); return t*t*(3-2*t)

tmp=tempfile.mkdtemp()
subprocess.run([FF,'-y','-ss',str(SRC0),'-i',FRONT,'-t',str(DUR),'-vf',CROP,os.path.join(tmp,'f%03d.png')],capture_output=True)
frames=sorted(f for f in os.listdir(tmp) if f.startswith('f')); N=len(frames)
out=tempfile.mkdtemp()
for i,fn in enumerate(frames):
    t=i/FPS
    base=Image.open(os.path.join(tmp,fn)).convert('RGBA')
    layer=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(layer)
    p=ease((t-0.3)/0.4); hl=ease((t-1.2)/0.3)
    if p>0.01:
        dy=int((1-p)*60); a=int(255*p)
        x0,y0,x1,y1=60,1330+dy,1020,1740+dy
        d.rounded_rectangle((x0,y0,x1,y1),radius=26,fill=CARD+(a,))
        d.ellipse((x0+34,y0+34,x0+34+78,y0+34+78),fill=CYAN+(a,))
        d.text((x0+50,y0+50),"S",font=dm(44,700,30),fill=(255,255,255,a))
        d.text((x0+138,y0+44),"Sales reply",font=dm(36,700,24),fill=INK+(a,))
        d.text((x0+138,y0+92),"to you",font=dm(28,400,20),fill=GRAY+(a,))
        d.line((x0+34,y0+148,x1-34,y0+148),fill=(225,228,232,a),width=2)
        d.text((x0+50,y0+176),"Re: quick question",font=dm(36,700,24),fill=INK+(a,))
        # body with one highlighted line
        d.text((x0+50,y0+238),"Hi — honestly,",font=dm(34,400,20),fill=(70,74,80,a))
        ln="this is the best outreach I've seen."
        ly=y0+292
        if hl>0.01:
            w=d.textlength(ln,font=dm(34,600,20))
            d.rounded_rectangle((x0+46,ly-4,x0+46+int(w*hl)+12,ly+44),radius=8,fill=HL+(int(150*hl),))
        d.text((x0+50,ly),ln,font=dm(34,600,20),fill=INK+(a,))
        d.text((x0+50,y0+346),"Let's book a call this week?",font=dm(34,400,20),fill=(70,74,80,a))
    im=Image.alpha_composite(base,layer).convert('RGB')
    im.save(os.path.join(out,f'p{i:03d}.png'))
mp4='C:/Users/User/Downloads/0616_fx_email.mp4'
subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
shutil.rmtree(tmp,ignore_errors=True); shutil.rmtree(out,ignore_errors=True); print('SAVED',mp4)
