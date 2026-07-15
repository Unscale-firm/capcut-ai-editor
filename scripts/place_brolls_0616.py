"""Place the 5 b-rolls onto 0616 as full-screen clips on new top tracks at their windows.
Baked on-cam clips (#2,#4) already contain Amine's live footage; full-screen ones (#1,#3,#5)
cover the camera for their beat. CapCut MUST be closed.
"""
import json, shutil, copy, uuid, subprocess, os

PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
FFPROBE='ffprobe' if shutil.which('ffprobe') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
        r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffprobe.exe')
DL='C:/Users/User/Downloads/'
PLACEMENTS=[
    (DL+'0616_broll1_pipeline.mp4',       8.00),
    (DL+'0616_broll2_oneman_baked.mp4',  15.30),
    (DL+'0616_broll3_agencyburn.mp4',    43.50),
    (DL+'0616_broll4_10leads_baked.mp4', 75.50),
    (DL+'0616_broll5_buildrunown.mp4',   84.00),
]
def guid(): return str(uuid.uuid4()).upper()
def dur_us(p):
    r=subprocess.run([FFPROBE,'-v','error','-show_entries','format=duration','-of',
                      'default=noprint_wrappers=1:nokey=1',p],capture_output=True,text=True)
    return int(float(r.stdout)*1_000_000)

shutil.copy2(PROJ, PROJ+'.before-brolls')
d=json.load(open(PROJ,encoding='utf-8')); M=d['materials']
idmap={}
for k,v in M.items():
    if isinstance(v,list):
        for m in v:
            if isinstance(m,dict) and 'id' in m: idmap[m['id']]=(k,m)
anim_ids={m['id'] for m in M.get('material_animations',[])}
vtrack=next(tr for tr in d['tracks'] if tr['type']=='video')
vseg_tmpl=vtrack['segments'][0]

for mp4,start_s in PLACEMENTS:
    if not os.path.exists(mp4): raise SystemExit('missing '+mp4)
    DUR=dur_us(mp4); START=int(start_s*1_000_000)
    name='broll-'+os.path.splitext(os.path.basename(mp4))[0]
    vb=copy.deepcopy(M['videos'][0]); mid=guid()
    vb['id']=mid; vb['path']=mp4; vb['duration']=DUR; vb['width']=1080; vb['height']=1920
    vb['material_name']=name
    if 'crop' in vb:
        vb['crop']={'upper_left_x':0.0,'upper_left_y':0.0,'upper_right_x':1.0,'upper_right_y':0.0,
                    'lower_left_x':0.0,'lower_left_y':1.0,'lower_right_x':1.0,'lower_right_y':1.0}
    M['videos'].append(vb)
    seg=copy.deepcopy(vseg_tmpl); seg['id']=guid(); seg['material_id']=mid
    seg['target_timerange']={'start':START,'duration':DUR}
    seg['source_timerange']={'start':0,'duration':DUR}
    seg.setdefault('clip',{})['scale']={'x':1.0,'y':1.0}; seg['clip']['transform']={'x':0.0,'y':0.0}
    seg['volume']=0.0; seg['last_nonzero_volume']=0.0; seg['common_keyframes']=[]
    new_refs=[]
    for r in seg.get('extra_material_refs',[]):
        if r in anim_ids: continue
        if r in idmap:
            lst,orig=idmap[r]; c=copy.deepcopy(orig); c['id']=guid(); M[lst].append(c); new_refs.append(c['id'])
    seg['extra_material_refs']=new_refs
    nt=copy.deepcopy(vtrack); nt['id']=guid(); nt['segments']=[seg]; nt['flag']=0
    d['tracks'].append(nt)
    print(f'placed {name} at {start_s}-{round((START+DUR)/1e6,2)}s')

json.dump(d,open(PROJ,'w',encoding='utf-8'),ensure_ascii=False)
print('SAVED — relaunch CapCut to review')
