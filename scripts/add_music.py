"""Add a background-music track to a CapCut project: low volume under the voice, fade in/out."""
import sys, json, shutil, copy, uuid, subprocess
from pathlib import Path

PROJ = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608')
CF = PROJ / 'draft_content.json'
MUSIC = 'C:/Users/User/Downloads/bg-music-corporate.mp3'
VOL = 0.13
FADE_IN, FADE_OUT = 1_000_000, 2_000_000
FFPROBE = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
           r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffprobe.exe')

def guid(): return str(uuid.uuid4()).upper()

dur_s = float(subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
              '-of', 'default=noprint_wrappers=1:nokey=1', MUSIC], capture_output=True, text=True).stdout.strip())
music_dur = int(dur_s * 1_000_000)

shutil.copy2(CF, str(CF) + '.before-music')
d = json.load(open(CF, encoding='utf-8')); M = d['materials']
seg_dur = min(music_dur, d['duration'])

idmap = {}
for k, v in M.items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and 'id' in m: idmap[m['id']] = (k, m)

# new music material (clone the existing audio material, repoint it)
mat = copy.deepcopy(M['audios'][0]); mat_id = guid()
mat['id'] = mat_id; mat['name'] = 'bg-music-corporate'; mat['path'] = MUSIC
mat['duration'] = music_dur; mat['music_id'] = str(uuid.uuid4()); mat['wave_points'] = []
M['audios'].append(mat)

# clone an existing audio segment, repoint to the music
aud_seg = next(s for tr in d['tracks'] if tr['type'] == 'audio' for s in tr['segments'][:1])
seg = copy.deepcopy(aud_seg); seg['id'] = guid(); seg['material_id'] = mat_id
seg['target_timerange'] = {'start': 0, 'duration': seg_dur}
seg['source_timerange'] = {'start': 0, 'duration': seg_dur}
seg['render_timerange'] = {'start': 0, 'duration': 0}
seg['volume'] = VOL; seg['last_nonzero_volume'] = VOL

# give the music segment its own copies of the companion materials + a fade
new_refs = []
for r in seg.get('extra_material_refs', []):
    if r in idmap:
        lst, orig = idmap[r]; c = copy.deepcopy(orig); c['id'] = guid()
        M[lst].append(c); new_refs.append(c['id'])
fade = {'id': guid(), 'type': 'audio_fade', 'fade_in_duration': FADE_IN, 'fade_out_duration': FADE_OUT}
M.setdefault('audio_fades', []).append(fade); new_refs.append(fade['id'])
seg['extra_material_refs'] = new_refs

# new audio track
base_track = next(tr for tr in d['tracks'] if tr['type'] == 'audio')
nt = copy.deepcopy(base_track); nt['id'] = guid(); nt['segments'] = [seg]
d['tracks'].append(nt)

json.dump(d, open(CF, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print(f'Added bg music: vol {VOL}, plays 0-{round(seg_dur/1e6,1)}s, fade {FADE_IN/1e6}s in / {FADE_OUT/1e6}s out')
