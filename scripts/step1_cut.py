"""STEP 1 - the cut, on the FRONT-CAMERA (picture) timeline so it matches what the
user sees in CapCut. Voice = front camera's OWN audio (perfect sync, no offset).
Keeps both angles (side hidden until step 2). Removes junk/dupes/silences.

All keeper times below are in FRONT-VIDEO seconds (what CapCut's playhead shows).
Re-runnable from the clean base.
"""
import sys, shutil
from pathlib import Path
sys.path.insert(0, 'src')
from smartcut.core.capcut_reader import CapCutProject

US = 1_000_000
P = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616')
CF = P / 'draft_content.json'
BASE = Path(str(CF) + '.before-cut925')

V = 'C:/Users/User/Downloads/Video'; A = 'C:/Users/User/Downloads/Audio'
FILES = {'C9146': (f'{V}/C9146-cut925.MP4', 565040000),
         'C9138': (f'{V}/C9138-cut925.MP4', 565040000)}
AUDIO = (f'{A}/1-cut925.wav', 565077333)
B_OFF = 5.511                      # C9138_time = C9146_time + 5.511 (for step-2 sync)
WAV2VID = 3.859                    # front-video time = master(1.wav) time + this

# HOOK: kept CONTINUOUS from 2:04 (user anchor) so nothing is skipped.
# hook = ONE continuous fluent take, 2:05->2:19 in the video, NO internal cuts (per user, reading the picture)
HOOK_VIDEO = [(125.5, 139.0)]
# BODY phrases are in master/1.wav seconds (from the transcript); converted to video below.
BODY_WAV = [
 # (hook-2 "you raise money to grow / DMs til midnight" removed per user — hook 1 -> body)
 (296.03,298.63),(298.63,301.60),(301.83,304.56),(304.57,306.70),(307.30,310.70),(310.90,314.67),
 (317.03,319.30),(319.57,322.54),(322.53,323.40),(323.40,327.30),(330.00,335.07),(335.20,338.87),
 (341.33,343.46),(343.70,345.23),(346.23,348.73),(348.73,351.13),(351.20,355.13),
 (371.83,374.83),(374.90,376.83),(376.83,378.16),(378.17,381.50),
 (385.33,387.70),(387.90,389.73),(389.77,392.07),(392.23,396.10),(396.10,397.57),(397.57,401.07),
 (404.23,406.13),(406.13,409.43),(409.50,412.00),(412.37,415.40),(415.40,417.07),(422.70,424.47),(424.73,426.50),
 (450.17,453.74),(455.83,457.80),(458.00,461.00),(461.00,462.60),(462.60,464.37),(464.37,465.54),(465.53,468.20),
 (514.50,515.60),(515.60,518.13),(518.13,521.40),(521.40,522.83),(523.77,527.67),
 (538.73,540.93),(540.93,543.73),
 (544.83,547.73),(547.73,549.33),(549.53,552.00),(552.00,554.43),(554.50,557.73),(558.00,560.83),(560.83,561.15),
]
# Build keepers from the camera transcript, cutting EVERY gap > MERGE_GAP (no dead air).
# Zones select the good content (hook 1 + body); junk/hooks2-3/asides/retakes fall outside.
import json as _json
# 1:30 version (approved): Hook -> CEO-is-pipeline -> SDR+agency -> reframe -> Spiralize -> offer -> CTA
KEEP_ZONES = [
 (125.0, 139.0),   # HOOK 1
 (311.0, 334.0),   # "so what do you do, improvise" -> "you cannot scale yourself"
 (335.0, 347.3),   # "what do most founders do / SDR" -> "nothing to show for"
 (363.0, 376.5),   # agency -> "single closed deal"
 (379.0, 396.0),   # reframe: build what you own -> "out of the sales seat for good"
 (398.0, 421.0),   # Proof: Spiralize -> "could not keep up"
 (534.0, 538.5),   # offer: "we build it, run it, you own it forever"
 (539.0, 559.0),   # CTA
]
MERGE_GAP = 1.20   # only cut real dead air; keep natural in-sentence pauses (fewer, smoother cuts)
_segs = sorted(_json.load(open('0616_camera_transcript.json', encoding='utf-8')), key=lambda s: s['start'])
_good = [s for s in _segs if any(lo <= (s['start']+s['end'])/2 <= hi for lo, hi in KEEP_ZONES)]
_blocks = []
for s in _good:
    if _blocks and s['start'] - _blocks[-1][1] < MERGE_GAP:
        _blocks[-1][1] = s['end']
    else:
        _blocks.append([s['start'], s['end']])
KEEP_VIDEO = [(max(0.0, a - 0.05), b + 0.10) for a, b in _blocks]

shutil.copy2(BASE, CF)
proj = CapCutProject(P); C = proj._content

# re-point
for v in C['materials']['videos']:
    for k, (path, dur) in FILES.items():
        if k in v.get('material_name', ''): v['path'] = path; v['duration'] = dur
for a in C['materials']['audios']:
    a['path'] = AUDIO[0]; a['duration'] = AUDIO[1]
vmat = {m['id']: m for m in C['materials']['videos']}

# front = master picture+sound (source==video time). side synced for step 2, muted.
front_len = FILES['C9146'][1]; side_len = FILES['C9138'][1] - int(B_OFF*US)
for tr in C['tracks']:
    if tr['type'] == 'video':
        for s in tr['segments']:
            mn = vmat[s['material_id']]['material_name']
            if 'C9146' in mn:
                s['source_timerange'] = {'start': 0, 'duration': front_len}
                s['target_timerange'] = {'start': 0, 'duration': front_len}
                s['volume'] = 1.0; s['last_nonzero_volume'] = 1.0       # voice from front camera
            else:
                s['source_timerange'] = {'start': int(B_OFF*US), 'duration': side_len}
                s['target_timerange'] = {'start': 0, 'duration': side_len}
                s['volume'] = 0.0; s['last_nonzero_volume'] = 0.0
# drop the separate 1.wav audio track (duplicate voice, caused the offset) and any text
C['tracks'] = [tr for tr in C['tracks'] if tr['type'] not in ('audio', 'text')]
C['duration'] = front_len

# front on top so it shows; side underneath (hidden until step 2)
def tk(tr): return 'C9146' if 'C9146' in vmat[tr['segments'][0]['material_id']]['material_name'] else 'C9138'
vtr = [tr for tr in C['tracks'] if tr['type'] == 'video']
a_tr = next(t for t in vtr if tk(t) == 'C9146'); b_tr = next(t for t in vtr if tk(t) == 'C9138')
C['tracks'] = [b_tr, a_tr]

# cut: keep KEEP_VIDEO, remove the complement (on the front-video timeline)
keep = sorted((int(s*US), int(e*US)) for s, e in KEEP_VIDEO)
merged = []
for s, e in keep:
    if merged and s <= merged[-1][1] + 1: merged[-1] = (merged[-1][0], max(merged[-1][1], e))
    else: merged.append((s, e))
cuts = []; prev = 0
for s, e in merged:
    if s > prev: cuts.append((prev, s))
    prev = max(prev, e)
if prev < front_len: cuts.append((prev, front_len))
proj.remove_time_ranges(cuts)
proj.save()
print(f"cut done | duration ~{C['duration']/US:.1f}s ({C['duration']/US/60:.2f} min) | front segs {len(a_tr['segments'])}")
print(f"debut: front starts at {min(s for s,_ in keep)/US:.1f}s = 2:{min(s for s,_ in keep)/US-120:04.1f}")
