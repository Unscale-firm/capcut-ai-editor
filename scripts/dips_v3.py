"""Dip-to-black ONLY, on the 3 major switches (22.77,53.70,69.20). Each half anchored to its
correct source (handles the content-cut so audio stays in sync). Removes all old angle-transition
clips; gaze flicks become clean cuts. CapCut MUST be closed.
"""
import json, os, subprocess, tempfile, shutil, copy, uuid
import numpy as np
from PIL import Image

W,H,FPS=1080,1920,30
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
FP=(FF.replace('ffmpeg.exe','ffprobe.exe') if FF.endswith('ffmpeg.exe') else 'ffprobe')
PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
DL='C:/Users/User/Downloads/'
SIDE_OFF=5.527
FCROP='crop=720:1280:180:200,scale=1080:1920,fps=30'   # front 1.5x
SCROP='scale=1080:1920,fps=30'                          # side original

d=json.load(open(PROJ,encoding='utf-8'))
track0=[t for t in d['tracks'] if t['type']=='video'][0]
FRONT=next(m['path'] for m in d['materials']['videos'] if 'C9146' in m['path'])
SIDE=next(m['path'] for m in d['materials']['videos'] if 'C9138' in m['path'])
def front_src_at(t):
    for s in track0['segments']:
        st=s['target_timerange']['start']/1e6; en=st+s['target_timerange']['duration']/1e6
        if st<=t<en: return s['source_timerange']['start']/1e6+(t-st)
    s=track0['segments'][-1]; return s['source_timerange']['start']/1e6+(t-s['target_timerange']['start']/1e6)
def src_at(tag,t): return front_src_at(t)+(SIDE_OFF if tag=='C9138' else 0.0)
def fileof(tag): return SIDE if tag=='C9138' else FRONT
def cropof(tag): return SCROP if tag=='C9138' else FCROP
def grab(tag,src0,n):
    tmp=tempfile.mkdtemp()
    subprocess.run([FF,'-y','-ss',str(src0),'-i',fileof(tag),'-vf',cropof(tag),'-frames:v',str(n),os.path.join(tmp,'p%03d.png')],capture_output=True)
    a=[np.asarray(Image.open(os.path.join(tmp,f'p{i+1:03d}.png')).convert('RGB'),np.float32) for i in range(n)]
    shutil.rmtree(tmp,ignore_errors=True); return a

def build_dip(cut,from_tag,to_tag):
    PRE=POST=6
    from_src0=src_at(from_tag,cut-PRE/FPS)   # pre-cut anchor
    to_src0=src_at(to_tag,cut)               # post-cut anchor
    A=grab(from_tag,from_src0,PRE); B=grab(to_tag,to_src0,POST)
    out=tempfile.mkdtemp()
    for i in range(PRE+POST):
        if i<PRE: b=max(0,(PRE-1-i)/(PRE-1)); fr=A[i]*b
        else: j=i-PRE; b=min(1,j/(POST-1)); fr=B[j]*b
        Image.fromarray(np.clip(fr,0,255).astype(np.uint8)).save(os.path.join(out,f'p{i:03d}.png'))
    mp4=DL+f'0616_dip_{str(cut).replace(".","")}.mp4'
    subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
    shutil.rmtree(out,ignore_errors=True)
    return mp4, round(cut-PRE/FPS,3)

MAJORS=[(22.77,'C9138','C9146'),(53.70,'C9146','C9138'),(69.20,'C9138','C9146')]
placements=[build_dip(c,a,b) for c,a,b in MAJORS]
for c,_ in zip(MAJORS,placements): pass
for (mp4,pt) in placements: print('built dip ->',pt,os.path.basename(mp4))

shutil.copy2(PROJ,PROJ+'.before-dipsv3')
M=d['materials']; vids={m['id']:m for m in M['videos']}
# remove ALL existing angle-transition clips (old _o, atr, etc.)
old=set(); kept=[]
for t in d['tracks']:
    drop=False
    if t['type']=='video':
        for s in t['segments']:
            p=vids.get(s['material_id'],{}).get('path','')
            if '0616_atr_' in p or '0616_dip_' in p: drop=True; old.add(s['material_id'])
    if not drop: kept.append(t)
d['tracks']=kept; M['videos']=[m for m in M['videos'] if m['id'] not in old]
print('removed old angle-transition tracks:',len(old))
# place 3 dips
idmap={}
for k,v in M.items():
    if isinstance(v,list):
        for m in v:
            if isinstance(m,dict) and 'id' in m: idmap[m['id']]=(k,m)
anim_ids={m['id'] for m in M.get('material_animations',[])}
vtrack=next(tr for tr in d['tracks'] if tr['type']=='video'); vseg_tmpl=vtrack['segments'][0]
def guid(): return str(uuid.uuid4()).upper()
def dur_us(p): return int(float(subprocess.run([FP,'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',p],capture_output=True,text=True).stdout)*1e6)
for mp4,pt in placements:
    DURv=dur_us(mp4); START=int(pt*1e6)
    vb=copy.deepcopy(M['videos'][0]); mid=guid()
    vb['id']=mid; vb['path']=mp4; vb['duration']=DURv; vb['width']=1080; vb['height']=1920; vb['material_name']='dip-'+os.path.basename(mp4)[:-4]
    if 'crop' in vb: vb['crop']={'upper_left_x':0.0,'upper_left_y':0.0,'upper_right_x':1.0,'upper_right_y':0.0,'lower_left_x':0.0,'lower_left_y':1.0,'lower_right_x':1.0,'lower_right_y':1.0}
    M['videos'].append(vb)
    seg=copy.deepcopy(vseg_tmpl); seg['id']=guid(); seg['material_id']=mid
    seg['target_timerange']={'start':START,'duration':DURv}; seg['source_timerange']={'start':0,'duration':DURv}
    seg.setdefault('clip',{})['scale']={'x':1.0,'y':1.0}; seg['clip']['transform']={'x':0.0,'y':0.0}
    seg['volume']=0.0; seg['last_nonzero_volume']=0.0; seg['common_keyframes']=[]
    refs=[]
    for r in seg.get('extra_material_refs',[]):
        if r in anim_ids: continue
        if r in idmap: lst,orig=idmap[r]; c=copy.deepcopy(orig); c['id']=guid(); M[lst].append(c); refs.append(c['id'])
    seg['extra_material_refs']=refs
    nt=copy.deepcopy(vtrack); nt['id']=guid(); nt['segments']=[seg]; nt['flag']=0
    d['tracks'].append(nt)
json.dump(d,open(PROJ,'w',encoding='utf-8'),ensure_ascii=False)
print('placed 3 dip-to-black (synced) | gaze flicks = clean cuts | SAVED')
