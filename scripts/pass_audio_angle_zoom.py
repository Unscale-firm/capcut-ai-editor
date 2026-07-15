"""0616 pass: clean-audio swap+sync, mute camera audio, 41s angle cut, sliver cleanup, 1.8x front zoom.
Surgical edits to the LIVE draft — captions/text tracks untouched.
Run with venv python. CapCut MUST be closed.
"""
import json, uuid
from pathlib import Path

US = 1_000_000
P = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json')

CLEAN_AUDIO = 'C:/Users/User/Downloads/Audio/1-cut925.wav'
CLEAN_DUR_US = 565_077_333          # length of 1-cut925.wav
FRONT_OFFSET_US = 3_859_000         # master = C9146_source - 3.859s
ANGLE_CUT_US = 41_000_000           # pull the side->front cut to exactly 41.0s
ZOOM = 1.8                          # static zoom on front clips

d = json.load(open(P, encoding='utf-8'))
vids = {m['id']: m for m in d['materials']['videos']}
def is_front(seg): return 'C9146' in vids.get(seg['material_id'], {}).get('path', '')

vtracks = [t for t in d['tracks'] if t['type'] == 'video']
track0 = vtracks[0]                 # front, continuous, defines audio timeline
side_tracks = vtracks[1:]

# ---- 1) AUDIO: repoint material to synced master, rebuild track to mirror track0 ----
amats = d['materials']['audios']
assert len(amats) == 1, f'expected 1 audio material, got {len(amats)}'
amat = amats[0]
amat['path'] = CLEAN_AUDIO
amat['duration'] = CLEAN_DUR_US
amat['name'] = '1-cut925'

atrack = next(t for t in d['tracks'] if t['type'] == 'audio')
template = dict(atrack['segments'][0])      # reuse structure/material_id
new_aud = []
for vs in track0['segments']:
    tr = vs['target_timerange']; sr = vs['source_timerange']
    seg = json.loads(json.dumps(template))  # deep copy
    seg['id'] = str(uuid.uuid4()).upper()
    seg['target_timerange'] = {'start': tr['start'], 'duration': tr['duration']}
    seg['source_timerange'] = {'start': sr['start'] - FRONT_OFFSET_US, 'duration': sr['duration']}
    seg['volume'] = 1.0
    seg['last_nonzero_volume'] = 1.0
    new_aud.append(seg)
atrack['segments'] = new_aud
print(f'audio: rebuilt {len(new_aud)} synced segments from track0')

# ---- 2) MUTE all camera audio ----
muted = 0
for t in vtracks:
    for s in t['segments']:
        s['volume'] = 0.0
        s['last_nonzero_volume'] = 0.0
        muted += 1
print(f'muted {muted} video segments')

# ---- 3) 41s angle cut: trim the side segment that currently runs through 41s ----
trimmed = None
for t in side_tracks:
    for s in t['segments']:
        st = s['target_timerange']['start']
        en = st + s['target_timerange']['duration']
        if st < ANGLE_CUT_US < en:          # spans 41.0s
            newdur = ANGLE_CUT_US - st
            s['target_timerange']['duration'] = newdur
            s['source_timerange']['duration'] = newdur
            trimmed = (st/US, en/US, ANGLE_CUT_US/US)
print(f'41s cut: side segment {trimmed[0]:.2f}-{trimmed[1]:.2f} -> ends {trimmed[2]:.2f}' if trimmed else 'WARN: no side seg spans 41s')

# ---- 4) remove sub-frame side slivers (< 0.12s) ----
SLIVER = int(0.12 * US)
for t in side_tracks:
    before = len(t['segments'])
    t['segments'] = [s for s in t['segments'] if s['target_timerange']['duration'] >= SLIVER]
    removed = before - len(t['segments'])
    if removed:
        print(f'removed {removed} sliver(s) from a side track')

# ---- 5) ZOOM: static 1.8x on front (C9146) clips ----
zoomed = 0
for t in vtracks:
    for s in t['segments']:
        if is_front(s):
            clip = s.setdefault('clip', {})
            clip.setdefault('scale', {})
            clip['scale']['x'] = ZOOM
            clip['scale']['y'] = ZOOM
            zoomed += 1
print(f'zoom {ZOOM}x applied to {zoomed} front clips')

json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False)
print('SAVED', P)
