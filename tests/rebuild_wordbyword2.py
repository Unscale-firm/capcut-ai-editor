"""Rebuild 0607 word-by-word with importance-based sizing + orange keywords + black outline."""
import json, shutil, copy, uuid, re
from pathlib import Path

PROJ = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0607')
f = PROJ / 'draft_content.json'
SRC = str(f) + '.before-wordbyword'        # the 28-caption state (has per-word timing)
shutil.copy2(str(f), str(f) + '.before-sizing2')
d = json.load(open(SRC, encoding='utf-8'))

FONT = 'C:/Users/User/AppData/Local/CapCut/Fonts/Montserrat-ExtraBold.ttf'
WHITE = [1.0, 1.0, 1.0]
ORANGE = [0.9098039, 0.4627451, 0.1764706]   # #E8762D
STROKE_RGB = [0.251, 0.251, 0.251]     # #404040 dark grey outline
STROKE_HEX = '#404040'
SIZE_UNIFORM = 18.0     # every word the same size
STROKE_W = 0.08
LEFT_X, Y = 0.0, 0.0    # centered on screen
ZOOM = 1.8
US = 1_000_000

# words that stay small (never emphasized)
STOP = set("""a an the and or but so if of to in on at for with as by is are was were be been am
i you he she it we they me him her us them my your his its our their this that these those
what which who whom there here then than too very just do does did have has had will would
can could should im id ive youre dont its theres about into out up down over under all""".split())
# ONLY the punchiest words get orange (kept very tight; easy to add/remove later)
KEYWORD = set("""ai npc mckinsey mandates placements playbook 2026""".split())

def guid():
    return str(uuid.uuid4()).upper()

def clean(tok):
    return re.sub(r"[^a-z0-9]", "", tok.lower())

text_tracks = [tr for tr in d['tracks'] if tr['type'] == 'text']
mat_by_id = {m['id']: m for m in d['materials']['texts']}
tmpl_mat = copy.deepcopy(d['materials']['texts'][0])
tmpl_seg = copy.deepcopy(text_tracks[0]['segments'][0])

# collect spoken words per caption, decide kind + size + color
words = []
for tr in text_tracks:
    for seg in tr['segments']:
        mat = mat_by_id.get(seg['material_id'])
        if not mat:
            continue
        w = mat.get('words') or {}
        toks = w.get('text') or []
        starts = w.get('start_time') or []
        seg_start = seg['target_timerange']['start']
        real = [(toks[i], starts[i]) for i in range(min(len(toks), len(starts))) if toks[i].strip()]
        if not real:
            c = json.loads(mat['content']); real = [(c.get('text', ''), 0)]
        for i, (tok, st_ms) in enumerate(real):
            cw = clean(tok)
            # all words same size; only color marks importance (orange keyword vs white)
            color = ORANGE if cw in KEYWORD else WHITE
            words.append({'start_us': seg_start + st_ms * 1000,
                          'text': tok.upper(), 'size': SIZE_UNIFORM, 'color': color})

words.sort(key=lambda x: x['start_us'])
for i in range(1, len(words)):
    if words[i]['start_us'] <= words[i-1]['start_us']:
        words[i]['start_us'] = words[i-1]['start_us'] + 1
proj_end = d['duration']
for i, wd in enumerate(words):
    nxt = words[i+1]['start_us'] if i + 1 < len(words) else proj_end
    wd['dur'] = max(1, nxt - wd['start_us'])

new_mats, new_segs = [], []
for wd in words:
    mid = guid(); txt = wd['text']
    m = copy.deepcopy(tmpl_mat); m['id'] = mid
    content = {
        'styles': [{
            'fill': {'alpha': 1.0, 'content': {'render_type': 'solid',
                     'solid': {'alpha': 1.0, 'color': wd['color'][:]}}},
            'strokes': [{'content': {'render_type': 'solid',
                        'solid': {'alpha': 1.0, 'color': STROKE_RGB[:]}}, 'width': STROKE_W}],
            'font': {'id': '', 'path': FONT},
            'range': [0, len(txt)], 'size': wd['size'],
        }],
        'text': txt,
    }
    m['content'] = json.dumps(content, ensure_ascii=False)
    m['words'] = {'text': [txt], 'start_time': [0], 'end_time': [int(wd['dur'] / 1000)]}
    m['font_path'] = FONT; m['font_name'] = 'Montserrat'; m['font_title'] = 'Montserrat ExtraBold'
    m['font_id'] = ''; m['font_resource_id'] = ''
    hexcol = '#%02X%02X%02X' % tuple(int(x*255) for x in wd['color'])
    m['text_color'] = hexcol
    m['font_size'] = wd['size']; m['text_size'] = int(wd['size'] * 3); m['letter_spacing'] = -0.04
    m['alignment'] = 1; m['line_max_width'] = 1.0; m['force_apply_line_max_width'] = False
    m['is_rich_text'] = False
    # dark grey outline (top-level fields too, belt-and-suspenders)
    m['border_color'] = STROKE_HEX; m['border_alpha'] = 1.0; m['border_width'] = STROKE_W; m['border_mode'] = 0
    new_mats.append(m)

    s = copy.deepcopy(tmpl_seg); s['id'] = guid(); s['material_id'] = mid
    s['target_timerange'] = {'start': wd['start_us'], 'duration': wd['dur']}
    s['source_timerange'] = None
    s['clip']['transform']['x'] = LEFT_X; s['clip']['transform']['y'] = Y
    s['clip']['scale']['x'] = 1.0; s['clip']['scale']['y'] = 1.0
    new_segs.append(s)

d['materials']['texts'] = new_mats
nt = copy.deepcopy(text_tracks[0]); nt['id'] = guid(); nt['segments'] = new_segs
d['tracks'] = [tr for tr in d['tracks'] if tr['type'] != 'text'] + [nt]
for tr in d['tracks']:
    if tr['type'] == 'video':
        for s in tr['segments']:
            s['clip']['scale']['x'] = ZOOM; s['clip']['scale']['y'] = ZOOM

json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
nk = sum(1 for w in words if w['color'] == ORANGE)
print(f'{len(new_segs)} words | all size {SIZE_UNIFORM} | {nk} orange keywords | black outline | zoom {ZOOM}x')
print('--- sample sentence ---')
for wd in words[7:15]:
    tag = 'ORANGE' if wd['color'] == ORANGE else 'white'
    print(f"  {round(wd['start_us']/US,2)}s  {tag:<7} {wd['text']}")
