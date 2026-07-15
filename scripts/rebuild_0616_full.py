"""Rebuild 0616 the 0608 way: both angles + master audio, synced, PHRASE-TIGHT cut
(removes silences + rehearsal lead-ins), angle-switch only at narrative sections.

Base = .before-cut925 (original draft w/ both angles + master audio).
Captions + zoom + transition-FX are later steps.
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
FILES = {'C9146': (f'{V}/C9146-cut925.MP4', 565040000, 3859000),
         'C9138': (f'{V}/C9138-cut925.MP4', 565040000, 9386000)}
AUDIO = (f'{A}/1-cut925.wav', 565077333)

# sections: (angle 'F'=front/C9146 | 'S'=side/C9138, [ (phrase_start, phrase_end) in master sec ])
SECTIONS = [
 ('F', [(130.97,133.90),(133.90,135.50),(135.53,137.30),(137.30,138.80),(138.80,140.77),(140.77,142.70),(142.70,144.27)]),  # HOOK
 ('S', [(156.37,158.10),(158.10,160.37),(160.37,164.24),(164.23,165.53),(165.53,169.46)]),                                   # PROBLEM
 ('F', [(296.03,298.63),(298.63,301.60),(301.83,304.56),(304.57,306.70),(307.30,310.70),(310.90,314.67)]),                   # FRIDAY/PRAYER
 ('S', [(317.03,319.30),(319.57,322.54),(322.53,323.40),(323.40,327.30),(330.00,335.07),(335.20,338.87)]),                   # IMPROVISE/CEO
 ('F', [(341.33,343.46),(343.70,345.23),(346.23,348.73),(348.73,351.13),(351.20,355.13)]),                                   # SDR
 ('S', [(371.83,374.83),(374.90,376.83),(376.83,378.16),(378.17,381.50)]),                                                   # AGENCY
 ('F', [(385.33,387.70),(387.90,389.73),(389.77,392.07),(392.23,396.10),(396.10,397.57),(397.57,401.07)]),                   # SURVIVORS
 ('S', [(404.23,406.13),(406.13,409.43),(409.50,412.00),(412.37,415.40),(415.40,417.07),(422.70,424.47),(424.73,426.50)]),   # SPIRALIZE
 ('F', [(450.17,453.74),(455.83,457.80),(458.00,461.00),(461.00,462.60),(462.60,464.37),(464.37,465.54),(465.53,468.20)]),   # SISMIC
 ('S', [(514.50,515.60),(515.60,518.13),(518.13,521.40),(521.40,522.83),(523.77,527.67)]),                                   # STANDARD
 ('F', [(538.73,540.93),(540.93,543.73)]),                                                                                    # MODEL
 ('F', [(544.83,547.73),(547.73,549.33),(549.53,552.00),(552.00,554.43),(554.50,557.73),(558.00,560.83),(560.83,561.63)]),   # CTA
]

shutil.copy2(BASE, CF)
proj = CapCutProject(P); C = proj._content

# 1) re-point
for v in C['materials']['videos']:
    for k,(path,dur,_o) in FILES.items():
        if k in v.get('material_name',''): v['path']=path; v['duration']=dur
for a in C['materials']['audios']:
    a['path']=AUDIO[0]; a['duration']=AUDIO[1]
vmat={m['id']:m for m in C['materials']['videos']}

# 2) sync + mute angles ; master audio at source 0
for tr in C['tracks']:
    if tr['type']=='video':
        for s in tr['segments']:
            mn=vmat.get(s['material_id'],{}).get('material_name','')
            k='C9146' if 'C9146' in mn else 'C9138'; _p,dur,off=FILES[k]; length=dur-off
            s['source_timerange']={'start':off,'duration':length}
            s['target_timerange']={'start':0,'duration':length}
            s['volume']=0.0; s['last_nonzero_volume']=0.0
    elif tr['type']=='audio':
        for s in tr['segments']:
            s['source_timerange']={'start':0,'duration':AUDIO[1]}
            s['target_timerange']={'start':0,'duration':AUDIO[1]}; s['volume']=1.0
C['tracks']=[tr for tr in C['tracks'] if tr['type']!='text']
C['duration']=AUDIO[1]

# 3) phrase-tight cut: keep merged phrase intervals, remove everything else
phrases=[(s,e,ang) for ang,plist in SECTIONS for (s,e) in plist]
ivals=sorted((int(s*US),int(e*US)) for s,e,_ in phrases)
merged=[]
for s,e in ivals:
    if merged and s<=merged[-1][1]+1: merged[-1]=(merged[-1][0],max(merged[-1][1],e))
    else: merged.append((s,e))
cuts=[]; prev=0
for s,e in merged:
    if s>prev: cuts.append((prev,s))
    prev=max(prev,e)
if prev<AUDIO[1]: cuts.append((prev,AUDIO[1]))
proj.remove_time_ranges(cuts)

# 4) angle-switch by section: front(C9146)=base always on; side(C9138) revealed on 'S' sections
def section_angle(orig_s):  # orig master-time (s) -> 'F'/'S'
    for ang,plist in SECTIONS:
        lo=min(p[0] for p in plist)-0.06; hi=max(p[1] for p in plist)+0.06
        if lo<=orig_s<=hi: return ang
    return 'F'
def tk(tr): return 'C9146' if 'C9146' in vmat[tr['segments'][0]['material_id']]['material_name'] else 'C9138'
vtr=[tr for tr in C['tracks'] if tr['type']=='video']
a_tr=next(t for t in vtr if tk(t)=='C9146'); b_tr=next(t for t in vtr if tk(t)=='C9138')
A_OFF=FILES['C9146'][2]; B_OFF=FILES['C9138'][2]
keptB=0; kb=[]
for s in b_tr['segments']:
    orig=(s['source_timerange']['start']-B_OFF)/US
    if section_angle(orig)=='S':
        s['render_index']=1; s['track_render_index']=1; kb.append(s); keptB+=1
b_tr['segments']=kb
for s in a_tr['segments']:
    s['render_index']=0; s['track_render_index']=0
C['tracks']=[a_tr,b_tr]+[t for t in C['tracks'] if t['type']!='video']
proj.save()
print(f"final duration ~{C['duration']/US:.1f}s | A segs {len(a_tr['segments'])} | side(B) segs {keptB}")
