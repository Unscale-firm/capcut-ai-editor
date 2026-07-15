"""STEP 4 - word-by-word captions in the Unscale brand style, mapped from the camera
word-transcript (0616_camera_words.json) onto the EDITED timeline of 0616.
ALL CAPS, Montserrat ExtraBold, white + orange keywords + red on negatives, lower third.
Re-runnable (rebuilds the text track each time).
"""
import json, os, copy, uuid, re

US = 1_000_000
BASE = os.path.join(os.environ['LOCALAPPDATA'], 'CapCut', 'User Data', 'Projects', 'com.lveditor.draft')
CF = os.path.join(BASE, '0616', 'draft_content.json')
TMPL = os.path.join(BASE, '0608', 'draft_content.json')

FONT = 'C:/Users/User/AppData/Local/CapCut/Fonts/Montserrat-ExtraBold.ttf'
FONT_NAME = 'Montserrat ExtraBold'
WHITE = [1.0, 1.0, 1.0]
ORANGE = [0.9098039, 0.4627451, 0.1764706]   # #E8762D
RED = [0.882, 0.196, 0.196]
SIZE = 15.0
POS_Y = -0.50

KEYWORD = set("""pipeline leads system systems demos meetings capability playbook playbooks
diagnostic founders scale agency sdr money capital sales own""".split())
RED_WORDS = set("""not no don't doesn't can't cannot never nothing prayer improvise burned burn""".split())

def guid(): return str(uuid.uuid4()).upper()
def clean(t): return re.sub(r"[^a-z']", "", t.lower())

d = json.load(open(CF, encoding='utf-8'))
vmat = {m['id']: m for m in d['materials']['videos']}
front = next(t for t in d['tracks'] if t['type'] == 'video'
            and 'C9146' in vmat[t['segments'][0]['material_id']]['material_name'])

# source(camera) seconds -> edited seconds, via the front cut segments
segmap = []
for s in front['segments']:
    ss = s['source_timerange']['start']; dur = s['source_timerange']['duration']
    ts = s['target_timerange']['start']
    segmap.append((ss, ss + dur, ts))
def to_edited(t_us):
    for ss, se, ts in segmap:
        if ss <= t_us < se:
            return ts + (t_us - ss)
    return None

words = json.load(open('0616_camera_words.json', encoding='utf-8'))
items = []
for w in words:
    txt = w['word'].strip()
    if not txt: continue
    e_start = to_edited(int(w['start'] * US))
    if e_start is None: continue          # word fell in a cut-out region
    e_end = to_edited(int(w['end'] * US))
    dur = (e_end - e_start) if (e_end and e_end > e_start) else int((w['end'] - w['start']) * US)
    items.append({'t': e_start, 'dur': max(1, dur), 'w': txt})
items.sort(key=lambda x: x['t'])
# no overlaps; each word shows until the next starts
for i in range(len(items) - 1):
    items[i]['dur'] = max(1, items[i + 1]['t'] - items[i]['t'])

# templates from 0608
t608 = json.load(open(TMPL, encoding='utf-8'))
tmpl_mat = copy.deepcopy(t608['materials']['texts'][0])
tmpl_seg = None
for tr in t608['tracks']:
    if tr['type'] == 'text' and tr['segments']:
        tmpl_seg = copy.deepcopy(tr['segments'][0]); break

new_mats, new_segs = [], []
for it in items:
    txt = it['w'].upper()
    cl = clean(it['w'])
    col = RED if cl in RED_WORDS else (ORANGE if cl in KEYWORD else WHITE)
    mid = guid()
    m = copy.deepcopy(tmpl_mat); m['id'] = mid; m['type'] = 'text'
    m['content'] = json.dumps({'styles': [{
        'fill': {'alpha': 1.0, 'content': {'render_type': 'solid', 'solid': {'alpha': 1.0, 'color': col[:]}}},
        'strokes': [{'content': {'render_type': 'solid', 'solid': {'alpha': 1.0, 'color': [0.0, 0.0, 0.0]}}, 'width': 0.08}],
        'font': {'id': '', 'path': FONT}, 'range': [0, len(txt)], 'size': SIZE}], 'text': txt}, ensure_ascii=False)
    m['words'] = {'text': [txt], 'start_time': [0], 'end_time': [int(it['dur'] / 1000)]}
    m['font_path'] = FONT; m['font_name'] = FONT_NAME; m['font_title'] = FONT_NAME
    m['font_id'] = ''; m['font_resource_id'] = ''
    m['text_color'] = '#%02X%02X%02X' % tuple(int(x * 255) for x in col)
    m['font_size'] = SIZE; m['letter_spacing'] = -0.02; m['alignment'] = 1
    m['border_color'] = '#000000'; m['border_alpha'] = 1.0; m['border_width'] = 0.08; m['border_mode'] = 0
    m['has_shadow'] = True; m['shadow_color'] = '#000000'; m['shadow_alpha'] = 0.9
    m['shadow_smoothing'] = 0.15; m['shadow_distance'] = 0.1; m['shadow_angle'] = -45.0
    m['shadow_point'] = {'x': 0.06, 'y': -0.06}
    if 'recognize_task_id' in m: m['recognize_task_id'] = ''
    new_mats.append(m)
    s = copy.deepcopy(tmpl_seg); s['id'] = guid(); s['material_id'] = mid
    s['target_timerange'] = {'start': it['t'], 'duration': it['dur']}; s['source_timerange'] = None
    s['clip']['transform']['x'] = 0.0; s['clip']['transform']['y'] = POS_Y
    s['clip']['scale']['x'] = 1.0; s['clip']['scale']['y'] = 1.0
    s['render_index'] = 14000 + len(new_segs)
    new_segs.append(s)

d['materials']['texts'] = new_mats
d['tracks'] = [tr for tr in d['tracks'] if tr['type'] != 'text']
nt = {'attribute': 0, 'flag': 0, 'id': guid(), 'is_default_name': True, 'name': '',
      'segments': new_segs, 'type': 'text'}
d['tracks'].append(nt)
json.dump(d, open(CF, 'w', encoding='utf-8'), ensure_ascii=False)
norange = sum(1 for it in items if clean(it['w']) in KEYWORD)
nred = sum(1 for it in items if clean(it['w']) in RED_WORDS)
print(f"captions: {len(items)} words | {norange} orange | {nred} red | font={FONT_NAME}")
