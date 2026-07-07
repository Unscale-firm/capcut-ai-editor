"""Generate the 'generic cold email' b-roll card (1080x1920) matching the ad's style."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
BG = (244, 221, 201)        # soft pastel (ad vibe)
NAVY = (26, 33, 48)
GREY = (140, 148, 160)
ORANGE = (232, 118, 45)     # #E8762D
WHITE = (255, 255, 255)
CARD = (255, 255, 255)

MONT = 'C:/Users/User/AppData/Local/CapCut/Fonts/Montserrat-ExtraBold.ttf'
SEG = 'C:/Windows/Fonts/segoeui.ttf'
SEGSB = 'C:/Windows/Fonts/seguisb.ttf'
def f(path, s): return ImageFont.truetype(path, s)

img = Image.new('RGB', (W, H), BG)
d = ImageDraw.Draw(img)

# --- header: "THE EMAIL EVERYONE SENDS" (EVERYONE in orange) ---
hf = f(MONT, 60)
parts = [('THE EMAIL ', NAVY), ('EVERYONE', ORANGE), (' SENDS', NAVY)]
total = sum(d.textlength(t, font=hf) for t, _ in parts)
x = (W - total) / 2; y = 300
for t, c in parts:
    d.text((x, y), t, font=hf, fill=c); x += d.textlength(t, font=hf)

# --- email card ---
x0, y0, x1, y1 = 60, 470, 1020, 1500
d.rounded_rectangle([x0, y0, x1, y1], radius=46, fill=CARD)
pad = 58
cx = x0 + pad

# avatar + sender
d.ellipse([cx, y0 + 55, cx + 96, y0 + 151], fill=ORANGE)
af = f(MONT, 44)
d.text((cx + 48, y0 + 103), 'SR', font=af, fill=WHITE, anchor='mm')
d.text((cx + 122, y0 + 62), 'Specialist Recruitment', font=f(MONT, 38), fill=NAVY)
d.text((cx + 122, y0 + 118), 'to you', font=f(SEG, 30), fill=GREY)
tf = f(SEG, 30)
d.text((x1 - pad, y0 + 62), '9:41 AM', font=tf, fill=GREY, anchor='ra')

# divider
dy = y0 + 185
d.line([cx, dy, x1 - pad, dy], fill=(232, 234, 238), width=3)

# subject
d.text((cx, dy + 35), 'Any hiring needs right now?', font=f(SEGSB, 44), fill=NAVY)

# body (wrapped)
body = ("Hi there,\n\nWe're a specialist recruitment firm and "
        "we'd love to support your team.\n\nDo you have any hiring "
        "needs at the moment?\n\nBest regards,\nSpecialist Recruitment")
bf = f(SEG, 37)
maxw = (x1 - pad) - cx
ty = dy + 130
for para in body.split('\n'):
    if not para:
        ty += 28; continue
    words = para.split(' '); line = ''
    for w in words:
        test = (line + ' ' + w).strip()
        if d.textlength(test, font=bf) <= maxw:
            line = test
        else:
            d.text((cx, ty), line, font=bf, fill=(70, 78, 92)); ty += 56; line = w
    if line:
        d.text((cx, ty), line, font=bf, fill=(70, 78, 92)); ty += 56

# footer hint
d.text((W/2, y1 + 60), 'sound familiar?', font=f(SEGSB, 40), fill=(150, 120, 95), anchor='mm')

out = 'C:/Users/User/Downloads/broll-cold-email.png'
img.save(out)
print('saved', out)
