"""Fix 31-44s angle switching to follow his gaze, and ease the zoom.
Gaze (verified from front cam):
  31.33-33.40 straight -> FRONT
  33.40-34.70 turn     -> SIDE   (trim existing side seg D9CD1421 start to 33.40)
  34.70-41.53 straight -> FRONT  (delete side seg 53E7FEAA)
  41.53-43.90 turn     -> SIDE   (add new side seg)
  43.90+      straight -> FRONT
Zoom: front 1.8x -> 1.5x.
"""
import json, uuid
from pathlib import Path

US = 1_000_000
P = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json')
FRONT_OFFSET = 3_859_000
SIDE_OFFSET  = 9_386_000
ZOOM = 1.5

W1_START = 33_400_000          # cut to side as he turns
W2_START = 41_533_333          # exact seg5 boundary (source jump), he's already turned
W2_END   = 43_900_000          # back to front as he faces forward

d = json.load(open(P, encoding='utf-8'))
vids = {m['id']: m for m in d['materials']['videos']}
def is_front(s): return 'C9146' in vids.get(s['material_id'], {}).get('path', '')
def is_side(s):  return 'C9138' in vids.get(s['material_id'], {}).get('path', '')

vtracks = [t for t in d['tracks'] if t['type'] == 'video']
track0 = vtracks[0]

def front_src_at(t):
    # half-open [start, end): at a boundary, resolve to the segment that PLAYS at t
    for s in track0['segments']:
        st = s['target_timerange']['start']; du = s['target_timerange']['duration']
        if st <= t < st + du:
            return s['source_timerange']['start'] + (t - st)
    # fall back to last segment if t is the very end
    s = track0['segments'][-1]
    return s['source_timerange']['start'] + (t - s['target_timerange']['start'])
def side_src_at(t):
    return front_src_at(t) - FRONT_OFFSET + SIDE_OFFSET   # master then to side clock

# locate the track holding the side segments we edit (track1)
side_track = next(t for t in vtracks if any(is_side(s) for s in t['segments']) and len(t['segments']) > 1)
segs = side_track['segments']
byid = {s['id'][:8]: s for s in segs}

# 1) trim D9CD1421 -> start at 33.40, keep its end (34.70)
a = byid['D9CD1421']
old_end = a['target_timerange']['start'] + a['target_timerange']['duration']
newdur = old_end - W1_START
a['source_timerange']['start'] = side_src_at(W1_START)
a['source_timerange']['duration'] = newdur
a['target_timerange']['start'] = W1_START
a['target_timerange']['duration'] = newdur
print(f"W1 side: {W1_START/US:.2f}-{old_end/US:.2f}  side_src={a['source_timerange']['start']/US:.2f}")

# 2) delete 53E7FEAA (he is straight 34.70-41.53)
segs[:] = [s for s in segs if s['id'][:8] != '53E7FEAA']
print('deleted side seg 53E7FEAA (34.70-41.53 -> front)')

# 3) add new side window 41.53-43.90 (clone a's structure)
b = json.loads(json.dumps(a))
b['id'] = str(uuid.uuid4()).upper()
b['target_timerange'] = {'start': W2_START, 'duration': W2_END - W2_START}
b['source_timerange'] = {'start': side_src_at(W2_START), 'duration': W2_END - W2_START}
segs.append(b)
segs.sort(key=lambda s: s['target_timerange']['start'])
print(f"W2 side: {W2_START/US:.2f}-{W2_END/US:.2f}  side_src={b['source_timerange']['start']/US:.2f}")

# 4) ease zoom on front clips
zc = 0
for t in vtracks:
    for s in t['segments']:
        if is_front(s):
            s.setdefault('clip', {}).setdefault('scale', {})
            s['clip']['scale']['x'] = ZOOM; s['clip']['scale']['y'] = ZOOM; zc += 1
print(f'zoom -> {ZOOM}x on {zc} front clips')

json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False)
print('SAVED')
