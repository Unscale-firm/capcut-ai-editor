"""Rebuild captions as PHRASES (2-4 words) matching the reference ad GROW MORE HOOK1:
Montserrat ExtraBold ALL CAPS, white with orange key words, soft drop-shadow, centered."""
import sys, shutil, copy, uuid, re, json
from pathlib import Path
sys.path.insert(0, 'src')
from smartcut.core.capcut_reader import CapCutProject

US = 1_000_000
FONT = 'C:/Users/User/AppData/Local/CapCut/Fonts/Montserrat-ExtraBold.ttf'
WHITE = [1.0, 1.0, 1.0]
ORANGE = [0.9098039, 0.4627451, 0.1764706]   # #E8762D
SIZE = 16.0
MAXW = 4                 # max words per phrase
GAP_BREAK = int(0.55 * US)   # start a new phrase after a pause this long

# tight orange keyword set for the 0608 recruitment script
KEYWORD = set("""recruiters recruitment mandates hr job boards board hiring manager managers
winning different ignores real-time realtime discovery call book form specialist""".split())

def guid(): return str(uuid.uuid4()).upper()
def clean(t): return re.sub(r"[^a-z0-9]", "", t.lower())

p = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608')
cf = p / 'draft_content.json'
shutil.copy2(cf, str(cf) + '.before-phrases')
proj = CapCutProject(p)
C = proj._content

text_tracks = [tr for tr in C['tracks'] if tr['type'] == 'text']
mat_by_id = {m['id']: m for m in C['materials']['texts']}
tmpl_mat = copy.deepcopy(C['materials']['texts'][0])
tmpl_seg = copy.deepcopy(text_tracks[0]['segments'][0])

# --- collect words grouped by caption (sentence) ---
caption_lists = []
for tr in text_tracks:
    for seg in tr['segments']:
        mat = mat_by_id.get(seg['material_id'])
        if not mat: continue
        w = mat.get('words') or {}
        toks, starts = w.get('text') or [], w.get('start_time') or []
        seg_start = seg['target_timerange']['start']
        L = [{'t': seg_start + starts[i] * 1000, 'w': toks[i]}
             for i in range(min(len(toks), len(starts))) if toks[i].strip()]
        if L: caption_lists.append(L)
caption_lists.sort(key=lambda L: L[0]['t'])

# split each sentence into BALANCED chunks of ~3 words (no orphans, no split pairs)
phrases = []
for L in caption_lists:
    n = len(L)
    nchunks = max(1, round(n / 3))
    base, rem = divmod(n, nchunks)
    idx = 0
    for c in range(nchunks):
        sz = base + (1 if c < rem else 0)
        phrases.append(L[idx:idx + sz]); idx += sz
phrases.sort(key=lambda ph: ph[0]['t'])

# phrase timings: start at first word, last until next phrase
proj_end = C['duration']
items = []
for j, ph in enumerate(phrases):
    start = ph[0]['t']
    end = phrases[j + 1][0]['t'] if j + 1 < len(phrases) else proj_end
    items.append({'start': start, 'dur': max(1, end - start), 'words': [x['w'] for x in ph]})

# --- build phrase text materials/segments ---
new_mats, new_segs = [], []
for it in items:
    words = [w.upper() for w in it['words']]
    text = ' '.join(words)
    # per-word color ranges
    styles, pos = [], 0
    for w in words:
        col = ORANGE if clean(w) in KEYWORD else WHITE
        styles.append({
            'fill': {'alpha': 1.0, 'content': {'render_type': 'solid', 'solid': {'alpha': 1.0, 'color': col[:]}}},
            'font': {'id': '', 'path': FONT}, 'range': [pos, pos + len(w)], 'size': SIZE,
        })
        pos += len(w) + 1   # +1 for the space
    mid = guid()
    m = copy.deepcopy(tmpl_mat); m['id'] = mid
    m['content'] = json.dumps({'styles': styles, 'text': text}, ensure_ascii=False)
    m['words'] = {'text': [text], 'start_time': [0], 'end_time': [int(it['dur'] / 1000)]}
    m['font_path'] = FONT; m['font_name'] = 'Montserrat'; m['font_title'] = 'Montserrat ExtraBold'
    m['font_id'] = ''; m['font_resource_id'] = ''; m['text_color'] = '#FFFFFF'
    m['font_size'] = SIZE; m['text_size'] = int(SIZE * 3); m['letter_spacing'] = -0.02
    m['alignment'] = 1; m['line_max_width'] = 0.7; m['force_apply_line_max_width'] = True
    m['is_rich_text'] = True
    # soft drop-shadow (no hard outline)
    m['has_shadow'] = True; m['shadow_color'] = '#000000'; m['shadow_alpha'] = 0.55
    m['border_alpha'] = 0.0; m['border_color'] = ''
    new_mats.append(m)

    s = copy.deepcopy(tmpl_seg); s['id'] = guid(); s['material_id'] = mid
    s['target_timerange'] = {'start': it['start'], 'duration': it['dur']}
    s['source_timerange'] = None
    s['clip']['transform']['x'] = 0.0; s['clip']['transform']['y'] = 0.0
    s['clip']['scale']['x'] = 1.0; s['clip']['scale']['y'] = 1.0
    new_segs.append(s)

C['materials']['texts'] = new_mats
nt = copy.deepcopy(text_tracks[0]); nt['id'] = guid(); nt['segments'] = new_segs
C['tracks'] = [tr for tr in C['tracks'] if tr['type'] != 'text'] + [nt]
proj.save()

n_orange = sum(1 for it in items for w in it['words'] if clean(w) in KEYWORD)
print(f'{len(items)} phrases | {n_orange} orange words | soft shadow | centered')
print('--- first 8 phrases ---')
for it in items[:8]:
    print(f"  {it['start']/US:5.1f}s  {' '.join(w.upper() for w in it['words'])}")
