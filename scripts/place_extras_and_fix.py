"""Fix the two mis-transcribed caption words (ONCE->RUNS, VIRALIZED->SPIRALYZE) and place the
two new b-rolls (NO PIPELINE bg @27.7, Spiralyze logo @71.5). CapCut MUST be closed.
"""
import json, shutil, copy, uuid, subprocess, os

PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
FFPROBE='ffprobe' if shutil.which('ffprobe') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
        r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffprobe.exe')
DL='C:/Users/User/Downloads/'
NEW=[(DL+'0616_broll_nopipeline_baked.mp4',27.70),(DL+'0616_broll_spiralyze.mp4',71.50)]
FIX={'ONCE':'RUNS','VIRALIZED':'SPIRALYZE'}   # same char length -> style ranges stay valid
def guid(): return str(uuid.uuid4()).upper()
def dur_us(p):
    r=subprocess.run([FFPROBE,'-v','error','-show_entries','format=duration','-of',
                      'default=noprint_wrappers=1:nokey=1',p],capture_output=True,text=True)
    return int(float(r.stdout)*1_000_000)

shutil.copy2(PROJ,PROJ+'.before-extras')
d=json.load(open(PROJ,encoding='utf-8')); M=d['materials']
texts={m['id']:m for m in M.get('texts',[])}

# ---- caption fix (match by text + time window 70.5-73s) ----
fixed=0
for tr in d['tracks']:
    if tr['type']!='text': continue
    for s in tr['segments']:
        ts=s['target_timerange']['start']/1e6
        if not (70.5<=ts<=73.0): continue
        m=texts.get(s['material_id'])
        if not m: continue
        try: c=json.loads(m['content'])
        except: continue
        old=c.get('text','')
        if old in FIX:
            c['text']=FIX[old]; m['content']=json.dumps(c,ensure_ascii=False)
            if m.get('text')==old: m['text']=FIX[old]
            print(f"caption {ts:.2f}s: {old} -> {FIX[old]}"); fixed+=1
print(f'captions fixed: {fixed}')

# ---- place the 2 new b-rolls ----
idmap={}
for k,v in M.items():
    if isinstance(v,list):
        for m in v:
            if isinstance(m,dict) and 'id' in m: idmap[m['id']]=(k,m)
anim_ids={m['id'] for m in M.get('material_animations',[])}
vtrack=next(tr for tr in d['tracks'] if tr['type']=='video')
vseg_tmpl=vtrack['segments'][0]
for mp4,start_s in NEW:
    if not os.path.exists(mp4): raise SystemExit('missing '+mp4)
    DURv=dur_us(mp4); START=int(start_s*1_000_000)
    name='broll-'+os.path.splitext(os.path.basename(mp4))[0]
    vb=copy.deepcopy(M['videos'][0]); mid=guid()
    vb['id']=mid; vb['path']=mp4; vb['duration']=DURv; vb['width']=1080; vb['height']=1920; vb['material_name']=name
    if 'crop' in vb:
        vb['crop']={'upper_left_x':0.0,'upper_left_y':0.0,'upper_right_x':1.0,'upper_right_y':0.0,
                    'lower_left_x':0.0,'lower_left_y':1.0,'lower_right_x':1.0,'lower_right_y':1.0}
    M['videos'].append(vb)
    seg=copy.deepcopy(vseg_tmpl); seg['id']=guid(); seg['material_id']=mid
    seg['target_timerange']={'start':START,'duration':DURv}
    seg['source_timerange']={'start':0,'duration':DURv}
    seg.setdefault('clip',{})['scale']={'x':1.0,'y':1.0}; seg['clip']['transform']={'x':0.0,'y':0.0}
    seg['volume']=0.0; seg['last_nonzero_volume']=0.0; seg['common_keyframes']=[]
    refs=[]
    for r in seg.get('extra_material_refs',[]):
        if r in anim_ids: continue
        if r in idmap:
            lst,orig=idmap[r]; c=copy.deepcopy(orig); c['id']=guid(); M[lst].append(c); refs.append(c['id'])
    seg['extra_material_refs']=refs
    nt=copy.deepcopy(vtrack); nt['id']=guid(); nt['segments']=[seg]; nt['flag']=0
    d['tracks'].append(nt)
    print(f'placed {name} at {start_s}-{round((START+DURv)/1e6,2)}s')

json.dump(d,open(PROJ,'w',encoding='utf-8'),ensure_ascii=False)
print('SAVED — relaunch CapCut to review')
