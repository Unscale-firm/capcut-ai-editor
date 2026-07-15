"""Place the baked IGNORED-background b-roll over the front camera (seamless crossfade is baked in)."""
import json, shutil, copy, uuid, subprocess, sys, os
PROJ = r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608\draft_content.json'
MP4 = sys.argv[1] if len(sys.argv) > 1 else 'C:/Users/User/Downloads/broll3-ignored-bg.mp4'
START = int(float(sys.argv[2]) * 1_000_000) if len(sys.argv) > 2 else int(24.0 * 1_000_000)
NAME = 'broll-' + os.path.splitext(os.path.basename(MP4))[0]
FFPROBE = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
           r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffprobe.exe')
def guid(): return str(uuid.uuid4()).upper()
DUR = int(float(subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
          '-of', 'default=noprint_wrappers=1:nokey=1', MP4], capture_output=True, text=True).stdout) * 1_000_000)

shutil.copy2(PROJ, PROJ + '.before-' + NAME)
d = json.load(open(PROJ, encoding='utf-8')); M = d['materials']
idmap = {}
for k, v in M.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and 'id' in m: idmap[m['id']] = (k, m)
anim_ids = {m['id'] for m in M.get('material_animations', [])}

vb = copy.deepcopy(M['videos'][0]); mid = guid()
vb['id'] = mid; vb['path'] = MP4; vb['duration'] = DUR; vb['width'] = 1080; vb['height'] = 1920
vb['material_name'] = NAME
if 'crop' in vb:
    vb['crop'] = {'upper_left_x': 0.0, 'upper_left_y': 0.0, 'upper_right_x': 1.0, 'upper_right_y': 0.0,
                  'lower_left_x': 0.0, 'lower_left_y': 1.0, 'lower_right_x': 1.0, 'lower_right_y': 1.0}
M['videos'].append(vb)

vseg = next(s for tr in d['tracks'] if tr['type'] == 'video' for s in tr['segments'][:1])
seg = copy.deepcopy(vseg); seg['id'] = guid(); seg['material_id'] = mid
seg['target_timerange'] = {'start': START, 'duration': DUR}
seg['source_timerange'] = {'start': 0, 'duration': DUR}
seg['clip']['scale'] = {'x': 1.0, 'y': 1.0}; seg['clip']['transform'] = {'x': 0.0, 'y': 0.0}
seg['volume'] = 0.0; seg['common_keyframes'] = []
new_refs = []
for r in seg.get('extra_material_refs', []):
    if r in anim_ids: continue           # no animation — crossfade is baked into the video
    if r in idmap:
        lst, orig = idmap[r]; c = copy.deepcopy(orig); c['id'] = guid()
        M[lst].append(c); new_refs.append(c['id'])
seg['extra_material_refs'] = new_refs

vtrack = next(tr for tr in d['tracks'] if tr['type'] == 'video')
nt = copy.deepcopy(vtrack); nt['id'] = guid(); nt['segments'] = [seg]
d['tracks'].append(nt)
json.dump(d, open(PROJ, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'placed baked b-roll at {START/1e6}-{round((START+DUR)/1e6,2)}s, full-screen, no extra transition')
