import re, json
SPEED = 1.1; FPS = 30
ASS = r"C:\Users\User\capcut-ai-editor\work\captions_v2.ass"
OUT = r"C:\Users\User\my-video\src\captionsData.ts"

def t2s(t):
    h, m, s = t.split(':'); return int(h) * 3600 + int(m) * 60 + float(s)

def conv_color(h):
    h = h[-6:]                      # BBGGRR
    bb, gg, rr = h[0:2], h[2:4], h[4:6]
    return ("#" + rr + gg + bb).upper()

def parse_text(txt):
    runs = []; cur = "#FFFFFF"; buf = ""; i = 0
    while i < len(txt):
        if txt[i] == '{':
            j = txt.find('}', i)
            if j == -1:
                buf += txt[i:]; break
            tag = txt[i + 1:j]
            cm = re.search(r'\\c&H([0-9A-Fa-f]+)&', tag)
            if cm:
                if buf:
                    runs.append({"t": buf, "c": cur}); buf = ""
                cur = conv_color(cm.group(1))
            i = j + 1
        else:
            buf += txt[i]; i += 1
    if buf:
        runs.append({"t": buf, "c": cur})
    return runs

caps = []
for line in open(ASS, encoding='utf-8'):
    if not line.startswith('Dialogue:'):
        continue
    m = re.match(r'Dialogue:\s*\d+,([0-9:.]+),([0-9:.]+),[^,]*,\d+,\d+,\d+,[^,]*,(.*)', line)
    if not m:
        continue
    st = round(t2s(m.group(1)) / SPEED * FPS)
    en = round(t2s(m.group(2)) / SPEED * FPS)
    runs = parse_text(m.group(3).rstrip('\n'))
    caps.append({"from": st, "dur": max(1, en - st), "runs": runs})

ts = "// auto-generated from captions_v2.ass (times scaled to 1.1x, 30fps)\n"
ts += "export type CapRun = { t: string; c: string };\n"
ts += "export type Cap = { from: number; dur: number; runs: CapRun[] };\n"
ts += "export const CAPTIONS: Cap[] = " + json.dumps(caps, ensure_ascii=False) + ";\n"
open(OUT, 'w', encoding='utf-8').write(ts)
print("captions:", len(caps))
print("first:", caps[0])
print("last:", caps[-1])
