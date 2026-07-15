"""STEP 2 - angle-switch with PRECISE edited-time inserts. For each (start,end) edited
range, shows the SIDE angle (C9138) over the front for exactly that span (splitting as
needed), placed at head-turns. Front audio carries the voice. Re-runnable on the step-1 cut.
"""
import json, os, uuid

# EDITED-video time ranges (seconds) to show the SIDE angle.
# full-section side switches (longer, alternating like the 0608 ad), aligned to segment bounds
SIDE_EDITED = [
 (13.0, 22.8),    # "so what do you do / improvise"
 (31.3, 41.5),    # "what do most founders do / SDR" (incl. the 0:32 head-turn)
 (53.7, 69.2),    # reframe: "build what you own"
 (76.7, 85.1),    # Spiralize proof (second half)
]
US = 1_000_000
def guid(): return str(uuid.uuid4()).upper()

d0 = os.path.join(os.environ['LOCALAPPDATA'], 'CapCut', 'User Data', 'Projects', 'com.lveditor.draft', '0616')
cf = os.path.join(d0, 'draft_content.json')
d = json.load(open(cf, encoding='utf-8'))
vmat = {m['id']: m for m in d['materials']['videos']}
def tk(tr): return 'C9146' if 'C9146' in vmat[tr['segments'][0]['material_id']]['material_name'] else 'C9138'
vtr = [t for t in d['tracks'] if t['type'] == 'video']
a_tr = next(t for t in vtr if tk(t) == 'C9146')   # front (audio)
b_tr = next(t for t in vtr if tk(t) == 'C9138')   # side

ranges = [(int(a*US), int(b*US)) for a, b in SIDE_EDITED]
pieces = []
for seg in b_tr['segments']:
    ts = seg['target_timerange']['start']; tdur = seg['target_timerange']['duration']; te = ts + tdur
    ss = seg['source_timerange']['start']
    for a, b in ranges:
        lo = max(ts, a); hi = min(te, b)
        if hi <= lo: continue
        p = json.loads(json.dumps(seg))          # deep copy
        p['id'] = guid()
        p['target_timerange'] = {'start': lo, 'duration': hi - lo}
        p['source_timerange'] = {'start': ss + (lo - ts), 'duration': hi - lo}
        p['volume'] = 0.0; p['render_index'] = 1; p['track_render_index'] = 1
        pieces.append(p)
b_tr['segments'] = pieces
for s in a_tr['segments']:
    s['render_index'] = 0; s['track_render_index'] = 0

d['tracks'] = [t for t in d['tracks'] if t['type'] != 'video']
d['tracks'] = [a_tr, b_tr] + d['tracks']
json.dump(d, open(cf, 'w', encoding='utf-8'), ensure_ascii=False)
print(f"angle-switch: {len(pieces)} side insert(s) at {SIDE_EDITED}")
