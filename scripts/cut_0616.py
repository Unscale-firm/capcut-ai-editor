"""Apply the 0616 rough cut INSIDE the CapCut draft.

Reduces the draft to a single angle (C9146) with its own audio, lip-synced cut,
keeping only the chosen keeper spans (in narrative order) and dropping all the
rehearsal junk/dupes. Re-runnable: edit SPANS and run again from the clean base.
"""
import sys, shutil, json
from pathlib import Path
sys.path.insert(0, 'src')
from smartcut.core.capcut_reader import CapCutProject

US = 1_000_000
OFF = 3.859        # 1.wav leads C9146 by this; C9146_time = wav_time - OFF
PAD = 0.25
P = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616')
CF = P / 'draft_content.json'
BASE = Path(str(CF) + '.before-cut925')   # clean re-pointed base (all 3 sources, aligned at 0)

# keeper spans in 1.wav / transcript seconds  [start, end, label]
SPANS = [
 (130.97, 144.27, "hook: congrats you just closed a round...15 don't count"),
 (156.37, 169.46, "you raise money to grow not improvise...DMs til midnight pray"),
 (296.03, 314.80, "Friday champagne/board deck/CRM 15 names/prayer not pipeline"),
 (317.03, 339.00, "improvise/CEO is the sales dept/can't scale yourself"),
 (341.33, 355.30, "most founders hire SDR/no playbook/nothing to show...or agency"),
 (371.83, 381.50, "agency: 15k/mo, burned 50-100k, no closed deal"),
 (385.33, 401.20, "survivors build a capability they own/CEO out of sales seat"),
 (404.23, 417.07, "Spiralize: 10 leads in 12h from a system they own"),
 (422.70, 426.60, "...sales team had to pause, couldn't keep up"),
 (450.17, 453.80, "different startup different industry, same result"),
 (455.83, 468.30, "Sismic: 10-15 meetings/mo x4, Peter CSO back to product"),
 (514.50, 527.70, "Standard.io: 2-3 demos, no agency no dependencies"),
 (538.73, 543.80, "that is our model: we build it, run it, you own it forever"),
 (544.83, 561.70, "CTA: diagnostic, book a call link below"),
]

shutil.copy2(BASE, CF)                       # restore clean base, then re-cut
proj = CapCutProject(P); C = proj._content
vmat = {m['id']: m for m in C['materials']['videos']}

# keep ONLY the angle-A (C9146) video track; drop angle B, master audio, captions
def is_a(tr):
    return tr['type'] == 'video' and 'C9146' in vmat.get(tr['segments'][0]['material_id'], {}).get('path', '')
C['tracks'] = [tr for tr in C['tracks'] if is_a(tr)]
assert len(C['tracks']) == 1, f"expected 1 angle-A track, got {len(C['tracks'])}"

vid_dur = C['tracks'][0]['segments'][0]['target_timerange']['duration']   # us

# keeper spans -> C9146 timeline (us), padded & clamped
keep = []
for a, b, _ in SPANS:
    ca = max(0.0, a - OFF - PAD)
    cb = min(vid_dur / US, b - OFF + PAD)
    keep.append((int(ca * US), int(cb * US)))
keep.sort()

# removal ranges = complement of keepers over [0, vid_dur]
cuts = []
prev = 0
for ks, ke in keep:
    if ks > prev:
        cuts.append((prev, ks))
    prev = max(prev, ke)
if prev < vid_dur:
    cuts.append((prev, vid_dur))

proj.remove_time_ranges(cuts)
proj.save()

kept_s = sum((ke - ks) for ks, ke in keep) / US
print(f"angle-A only | {len(SPANS)} keeper spans | removed {len(cuts)} ranges")
print(f"final duration ~{C['duration']/US:.1f}s ({C['duration']/US/60:.2f} min)")
