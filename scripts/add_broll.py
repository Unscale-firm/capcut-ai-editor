"""Place the email b-roll mp4 as a full-screen overlay, timed to the 'specialist firm' line,
with a soft blur-out on exit back to the speaker."""
import json, shutil, copy, uuid, subprocess
from pathlib import Path

PROJ = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608')
CF = PROJ / 'draft_content.json'
MP4 = 'C:/Users/User/Downloads/broll-cold-email.mp4'
ANCHOR = 'specialist'   # unique to "we're a SPECIALIST firm" (~18s)
PRE = 2_700_000         # start ~2.7s before it, so the email is mid-type as he says the pitch
FFPROBE = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
           r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffprobe.exe')
def guid(): return str(uuid.uuid4()).upper()

dur = int(float(subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
          '-of', 'default=noprint_wrappers=1:nokey=1', MP4], capture_output=True, text=True).stdout) * 1_000_000)

shutil.copy2(CF, str(CF) + '.before-broll')
d = json.load(open(CF, encoding='utf-8')); M = d['materials']
idmap = {}
for k, v in M.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and 'id' in m: idmap[m['id']] = (k, m)
anim_ids = {m['id'] for m in M.get('material_animations', [])}

# find anchor word time
texts = {m['id']: m for m in M['texts']}
start = None
rows = sorted([(s['target_timerange']['start'], json.loads(texts[s['material_id']]['content']).get('text', ''))
               for tr in d['tracks'] if tr['type'] == 'text' for s in tr['segments']])
for t, txt in rows:
    if ANCHOR in txt.lower():
        start = max(0, t - PRE); break
if start is None: start = int(15.5 * 1_000_000)

# b-roll video material (clone an existing video material, repoint to the mp4)
vbase = copy.deepcopy(M['videos'][0]); mid = guid()
vbase['id'] = mid; vbase['path'] = MP4; vbase['duration'] = dur
vbase['width'] = 1080; vbase['height'] = 1920; vbase['material_name'] = 'broll-cold-email'
if 'crop' in vbase:
    vbase['crop'] = {'upper_left_x': 0.0, 'upper_left_y': 0.0, 'upper_right_x': 1.0, 'upper_right_y': 0.0,
                     'lower_left_x': 0.0, 'lower_left_y': 1.0, 'lower_right_x': 1.0, 'lower_right_y': 1.0}
M['videos'].append(vbase)

# segment (clone a video segment, repoint)
vseg = next(s for tr in d['tracks'] if tr['type'] == 'video' for s in tr['segments'][:1])
seg = copy.deepcopy(vseg); seg['id'] = guid(); seg['material_id'] = mid
seg['target_timerange'] = {'start': start, 'duration': dur}
seg['source_timerange'] = {'start': 0, 'duration': dur}
seg['clip']['scale'] = {'x': 1.0, 'y': 1.0}; seg['clip']['transform'] = {'x': 0.0, 'y': 0.0}
seg['volume'] = 0.0; seg['common_keyframes'] = []

# clone companion materials, drop inherited animations, add a Blur Out exit
new_refs = []
for r in seg.get('extra_material_refs', []):
    if r in anim_ids:   # skip inherited Zoom/transition animations
        continue
    if r in idmap:
        lst, orig = idmap[r]; c = copy.deepcopy(orig); c['id'] = guid()
        M[lst].append(c); new_refs.append(c['id'])
ANIM = 400_000
blur = {'id': '7507514531212479761', 'type': 'out', 'start': max(0, dur - ANIM), 'duration': ANIM,
        'path': 'C:/Users/User/AppData/Local/CapCut/User Data/Cache/effect/7507514531212479761/78d0826a4aba60259f37acb30149b258',
        'platform': 'all', 'resource_id': '7507514531212479761', 'third_resource_id': '0', 'source_platform': 1,
        'name': 'Blur Out', 'category_id': '2037708372', 'category_name': 'Trending-2', 'panel': 'video',
        'material_type': 'video', 'anim_adjust_params': None, 'request_id': '20260608220908E713F38FB6173A61F9FF'}
ma_id = guid()
M['material_animations'].append({'id': ma_id, 'type': 'sticker_animation', 'animations': [blur], 'multi_language_current': 'none'})
new_refs.append(ma_id)
seg['extra_material_refs'] = new_refs

# new video track ON TOP (covers speaker + captions during the b-roll)
vtrack = next(tr for tr in d['tracks'] if tr['type'] == 'video')
nt = copy.deepcopy(vtrack); nt['id'] = guid(); nt['segments'] = [seg]
d['tracks'].append(nt)

json.dump(d, open(CF, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'b-roll placed at {round(start/1e6,2)}-{round((start+dur)/1e6,2)}s (anchored to "{ANCHOR}"), full-screen, blur-out exit')
