"""Rebuild 0607 captions as word-by-word kinetic text: appear-as-spoken + escalating size."""
import json, shutil, copy, uuid
from pathlib import Path

PROJ = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0607')
f = PROJ / 'draft_content.json'
shutil.copy2(f, str(f) + '.before-wordbyword')
d = json.load(open(f, encoding='utf-8'))

FONT = 'C:/Users/User/AppData/Local/CapCut/Fonts/Montserrat-ExtraBold.ttf'
WHITE = [1.0, 1.0, 1.0]
MIN_SIZE, MAX_SIZE = 12.0, 22.0     # first word -> last word within a sentence
LEFT_X, Y = -0.45, 0.0
US = 1_000_000

def guid():
    return str(uuid.uuid4()).upper()

# --- gather template material + segment from existing captions ---
text_tracks = [tr for tr in d['tracks'] if tr['type'] == 'text']
mat_by_id = {m['id']: m for m in d['materials']['texts']}
tmpl_mat = copy.deepcopy(d['materials']['texts'][0])
tmpl_seg = copy.deepcopy(text_tracks[0]['segments'][0])

# --- collect every spoken word with its absolute time + per-sentence size ---
words = []   # dicts: {start_us, text, size}
for tr in text_tracks:
    for seg in tr['segments']:
        mat = mat_by_id.get(seg['material_id'])
        if not mat:
            continue
        w = mat.get('words') or {}
        toks = w.get('text') or []
        starts = w.get('start_time') or []
        seg_start = seg['target_timerange']['start']
        seg_end = seg_start + seg['target_timerange']['duration']
        # real (non-space) tokens with their start times
        real = [(toks[i], starts[i]) for i in range(min(len(toks), len(starts))) if toks[i].strip()]
        if not real:
            # fallback: whole caption as one word
            c = json.loads(mat['content'])
            real = [(c.get('text', ''), 0)]
        n = len(real)
        for i, (tok, st_ms) in enumerate(real):
            size = MAX_SIZE if n == 1 else MIN_SIZE + (MAX_SIZE - MIN_SIZE) * (i / (n - 1))
            words.append({
                'start_us': seg_start + st_ms * 1000,
                'text': tok.upper(),
                'size': round(size, 2),
            })

# --- sort globally, force strictly increasing starts, set each word to last until the next ---
words.sort(key=lambda x: x['start_us'])
for i in range(1, len(words)):
    if words[i]['start_us'] <= words[i-1]['start_us']:
        words[i]['start_us'] = words[i-1]['start_us'] + 1
proj_end = d['duration']
for i, wd in enumerate(words):
    nxt = words[i+1]['start_us'] if i + 1 < len(words) else proj_end
    wd['dur'] = max(1, nxt - wd['start_us'])  # last until next word (no overlap)

# --- build fresh materials + segments ---
new_mats, new_segs = [], []
for wd in words:
    mid = guid()
    m = copy.deepcopy(tmpl_mat)
    m['id'] = mid
    txt = wd['text']
    content = {
        'styles': [{
            'fill': {'alpha': 1.0, 'content': {'render_type': 'solid',
                     'solid': {'alpha': 1.0, 'color': WHITE[:]}}},
            'font': {'id': '', 'path': FONT},
            'range': [0, len(txt)],
            'size': wd['size'],
        }],
        'text': txt,
    }
    m['content'] = json.dumps(content, ensure_ascii=False)
    m['words'] = {'text': [txt], 'start_time': [0], 'end_time': [int(wd['dur'] / 1000)]}
    m['font_path'] = FONT; m['font_name'] = 'Montserrat'; m['font_title'] = 'Montserrat ExtraBold'
    m['font_id'] = ''; m['font_resource_id'] = ''; m['text_color'] = '#FFFFFF'
    m['font_size'] = wd['size']; m['text_size'] = int(wd['size'] * 3); m['letter_spacing'] = -0.04
    m['alignment'] = 0                  # left
    m['line_max_width'] = 1.0; m['force_apply_line_max_width'] = False
    m['is_rich_text'] = False
    new_mats.append(m)

    s = copy.deepcopy(tmpl_seg)
    s['id'] = guid()
    s['material_id'] = mid
    s['target_timerange'] = {'start': wd['start_us'], 'duration': wd['dur']}
    s['source_timerange'] = None
    s['clip']['transform']['x'] = LEFT_X
    s['clip']['transform']['y'] = Y
    s['clip']['scale']['x'] = 1.0
    s['clip']['scale']['y'] = 1.0
    new_segs.append(s)

# --- swap in: one text track, fresh materials ---
d['materials']['texts'] = new_mats
new_track = copy.deepcopy(text_tracks[0])
new_track['id'] = guid()
new_track['segments'] = new_segs
d['tracks'] = [tr for tr in d['tracks'] if tr['type'] != 'text'] + [new_track]

# --- zoom video even more ---
ZOOM = 1.8
for tr in d['tracks']:
    if tr['type'] == 'video':
        for s in tr['segments']:
            s['clip']['scale']['x'] = ZOOM
            s['clip']['scale']['y'] = ZOOM

json.dump(d, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'Built {len(new_segs)} word-by-word segments (sizes {MIN_SIZE}->{MAX_SIZE} per sentence)')
print(f'Zoom: {ZOOM}x | text at left x={LEFT_X}')
# preview first sentence
print('--- first 8 words (time / size / text) ---')
for wd in words[:8]:
    print(f"  {round(wd['start_us']/US,2)}s  size {wd['size']}  {wd['text']}")
