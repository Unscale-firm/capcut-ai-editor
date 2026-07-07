"""Full 0608 rebuild from clean base: junk-cut, zoom, finer angle-switching,
word-by-word captions (Montserrat ExtraBold, off-face, white/orange/RED, soft shadow)."""
import sys, shutil, copy, uuid, re, json
from pathlib import Path
sys.path.insert(0, 'src')
from smartcut.core.capcut_reader import CapCutProject

US = 1_000_000
FONT = 'C:/Users/User/AppData/Local/CapCut/Fonts/Montserrat-ExtraBold.ttf'
FONT_NAME = 'Montserrat ExtraBold'
WHITE = [1.0, 1.0, 1.0]
ORANGE = [0.9098039, 0.4627451, 0.1764706]   # #E8762D
RED = [0.882, 0.196, 0.196]                   # #E13232
SIZE = 18.0
POS_Y = -0.52        # lower third, clearly off his face
ZOOM = 1.8

KEYWORD = set("""recruiters recruitment mandates hr job boards board hiring manager managers
winning discovery call book form specialist""".split())
RED_TRIGGERS = ['problem', 'ignores', 'cold pitching', 'ton of the same', 'every single day']

def guid(): return str(uuid.uuid4()).upper()
def clean(t): return re.sub(r"[^a-z0-9]", "", t.lower())

p = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608')
cf = p / 'draft_content.json'
shutil.copy2(str(cf) + '.before-fix', cf)          # restore clean base (20 lines, junk in, full video)
proj = CapCutProject(p); C = proj._content
texts = {m['id']: m for m in C['materials']['texts']}

# 1) remove junk lines
JUNK = ['pitch the candidate', 'best recruitment firms do differently']
caps = []
for tr in C['tracks']:
    if tr['type'] == 'text':
        for s in tr['segments']:
            t = s['target_timerange']
            caps.append((t['start'], t['start'] + t['duration'], json.loads(texts[s['material_id']]['content']).get('text', '').strip()))
caps.sort(); dur = C['duration']; ranges = []
for i, (st, en, txt) in enumerate(caps):
    if any(j in txt.lower() for j in JUNK):
        ranges.append((caps[i-1][1] if i > 0 else 0, caps[i+1][0] if i+1 < len(caps) else dur))
ranges.sort(); merged = []
for a, b in ranges:
    if merged and a <= merged[-1][1]: merged[-1] = (merged[-1][0], max(merged[-1][1], b))
    else: merged.append((a, b))
proj.remove_time_ranges(merged)

# 2) zoom both angles
for tr in C['tracks']:
    if tr['type'] == 'video':
        for s in tr['segments']:
            s['clip']['scale']['x'] = ZOOM; s['clip']['scale']['y'] = ZOOM

# 3) finer angle switching: alternate front/side at each sentence boundary
vmat = {m['id']: m for m in C['materials']['videos']}
vtr = [(i, tr) for i, tr in enumerate(C['tracks']) if tr['type'] == 'video']
lab = lambda tr: 'FRONT' if '4106' in vmat.get(tr['segments'][0]['material_id'], {}).get('path', '') else 'SIDE'
top = max(vtr, key=lambda x: x[0])[1]    # rendered on top
texts2 = {m['id']: m for m in C['materials']['texts']}
bot = min(vtr, key=lambda x: x[0])[1]
top_segs = sorted(top['segments'], key=lambda s: s['target_timerange']['start'])
bot_segs = sorted(bot['segments'], key=lambda s: s['target_timerange']['start'])
def bcov(a, b):
    return any(s['target_timerange']['start'] <= a+1 and s['target_timerange']['start']+s['target_timerange']['duration'] >= b-1 for s in bot_segs)
# alternate at the REAL cut boundaries only (fewer, cleaner switches — the version the user preferred)
keep = []; nside = 0
for i, seg in enumerate(top_segs):
    a = seg['target_timerange']['start']; b = a + seg['target_timerange']['duration']
    if i % 2 == 1 and bcov(a, b): nside += 1
    else: keep.append(seg)
top['segments'] = keep
print(f'angle: {len(top_segs)} cuts, {nside} show SIDE ({lab(top)} is top)')

# slow zoom on FRONT (top) clips — reuse CapCut's native "Zoom 1" group animation
# (the one the user tried & liked; it's cached locally so it renders reliably)
ZOOM1 = {
    'id': '6759078592740594184', 'type': 'group', 'start': 0, 'duration': 0,
    'path': 'C:/Users/User/AppData/Local/CapCut/User Data/Cache/effect/6759078592740594184/cac9a365aab6a7fe878431abd85d4b5d',
    'platform': 'all', 'resource_id': '6759078592740594184', 'third_resource_id': '6759078592740594184',
    'source_platform': 1, 'name': 'Zoom 1', 'category_id': '2037708347', 'category_name': 'Trending-1',
    'panel': 'video', 'material_type': 'video', 'anim_adjust_params': None,
    'request_id': '20260608220908E713F38FB6173A61F9FF',
}
C['materials'].setdefault('material_animations', [])
for seg in top['segments']:
    anim = copy.deepcopy(ZOOM1); anim['duration'] = seg['target_timerange']['duration']
    ma_id = guid()
    C['materials']['material_animations'].append(
        {'id': ma_id, 'type': 'sticker_animation', 'animations': [anim], 'multi_language_current': 'none'})
    seg.setdefault('extra_material_refs', []).append(ma_id)
print(f'applied "Zoom 1" animation to {len(top["segments"])} front clips')

# 4) word-by-word captions
text_tracks = [tr for tr in C['tracks'] if tr['type'] == 'text']
tmpl_mat = copy.deepcopy(C['materials']['texts'][0])
tmpl_seg = copy.deepcopy(text_tracks[0]['segments'][0])
words = []
for tr in text_tracks:
    for seg in tr['segments']:
        mat = texts2.get(seg['material_id'])
        if not mat: continue
        sentence = json.loads(mat['content']).get('text', '').lower()
        is_red = any(t in sentence for t in RED_TRIGGERS)
        w = mat.get('words') or {}
        toks, starts_ms = w.get('text') or [], w.get('start_time') or []
        seg_start = seg['target_timerange']['start']
        for i in range(min(len(toks), len(starts_ms))):
            if toks[i].strip():
                if is_red: col = RED
                elif clean(toks[i]) in KEYWORD: col = ORANGE
                else: col = WHITE
                words.append({'t': seg_start + starts_ms[i]*1000, 'w': toks[i].upper(), 'c': col})
words.sort(key=lambda x: x['t'])
for i in range(1, len(words)):
    if words[i]['t'] <= words[i-1]['t']: words[i]['t'] = words[i-1]['t'] + 1
for i, wd in enumerate(words):
    nxt = words[i+1]['t'] if i+1 < len(words) else C['duration']
    wd['dur'] = max(1, nxt - wd['t'])

new_mats, new_segs = [], []
for wd in words:
    mid = guid(); txt = wd['w']
    m = copy.deepcopy(tmpl_mat); m['id'] = mid
    m['content'] = json.dumps({'styles': [{
        'fill': {'alpha': 1.0, 'content': {'render_type': 'solid', 'solid': {'alpha': 1.0, 'color': wd['c'][:]}}},
        'strokes': [{'content': {'render_type': 'solid', 'solid': {'alpha': 1.0, 'color': [0.251, 0.251, 0.251]}}, 'width': 0.06}],
        'font': {'id': '', 'path': FONT}, 'range': [0, len(txt)], 'size': SIZE}], 'text': txt}, ensure_ascii=False)
    m['words'] = {'text': [txt], 'start_time': [0], 'end_time': [int(wd['dur']/1000)]}
    m['font_path'] = FONT; m['font_name'] = FONT_NAME; m['font_title'] = FONT_NAME
    m['font_id'] = ''; m['font_resource_id'] = ''
    m['text_color'] = '#%02X%02X%02X' % tuple(int(x*255) for x in wd['c'])
    m['font_size'] = SIZE; m['text_size'] = int(SIZE*3); m['letter_spacing'] = -0.02
    m['alignment'] = 1; m['line_max_width'] = 1.0; m['force_apply_line_max_width'] = False
    m['is_rich_text'] = False
    # grey outline + a real, visible drop shadow
    m['border_color'] = '#404040'; m['border_alpha'] = 1.0; m['border_width'] = 0.06; m['border_mode'] = 0
    m['has_shadow'] = True; m['shadow_color'] = '#000000'; m['shadow_alpha'] = 0.8
    m['shadow_smoothing'] = 0.12; m['shadow_distance'] = 0.08; m['shadow_angle'] = -45.0
    m['shadow_point'] = {'x': 0.057, 'y': -0.057}
    new_mats.append(m)
    s = copy.deepcopy(tmpl_seg); s['id'] = guid(); s['material_id'] = mid
    s['target_timerange'] = {'start': wd['t'], 'duration': wd['dur']}; s['source_timerange'] = None
    s['clip']['transform']['x'] = 0.0; s['clip']['transform']['y'] = POS_Y
    s['clip']['scale']['x'] = 1.0; s['clip']['scale']['y'] = 1.0
    new_segs.append(s)
C['materials']['texts'] = new_mats
nt = copy.deepcopy(text_tracks[0]); nt['id'] = guid(); nt['segments'] = new_segs
C['tracks'] = [tr for tr in C['tracks'] if tr['type'] != 'text'] + [nt]
proj.save()

nred = sum(1 for w in words if w['c'] == RED); norange = sum(1 for w in words if w['c'] == ORANGE)
print(f'captions: {len(words)} words | {norange} orange | {nred} red | font={FONT_NAME} | y={POS_Y}')
print(f'final dur {round(C["duration"]/US,1)}s')
