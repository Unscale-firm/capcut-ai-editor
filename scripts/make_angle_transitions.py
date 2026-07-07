"""Build + place angle-switch transition clips on 0616:
  dip-to-black on majors (22.77,53.70,69.20), zoom-punch on gaze flicks (33.40,34.70,41.53).
Each clip spans the cut, built from both camera angles (multicam) with the effect; reframed side.
CapCut MUST be closed (it places onto the draft).
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
SIDE_OFF=5.527   # side_src = front_src + 5.527 (same master moment)
FCROP='crop=720:1280:180:200,scale=1080:1920,fps=30'
SCROP='crop=755:1342:303:135,scale=1080:1920,fps=30'   # reframed side (matches held side)

d=json.load(open(PROJ,encoding='utf-8'))
track0=[t for t in d['tracks'] if t['type']=='video'][0]
FRONT=next(m['path'] for m in d['materials']['videos'] if 'C9146' in m['path'])
SIDE=next(m['path'] for m in d['materials']['videos'] if 'C9138' in m['path'])
def front_src_at(t):
    for s in track0['segments']:
        st=s['target_timerange']['start']/1e6; en=st+s['target_timerange']['duration']/1e6
        if st<=t<en: return s['source_timerange']['start']/1e6+(t-st)
    s=track0['segments'][-1]; return s['source_timerange']['start']/1e6+(t-s['target_timerange']['start']/1e6)

def zoom(a,f):
    if f<=1.001: return a
    nh,nw=int(H*f),int(W*f); big=np.asarray(Image.fromarray(a.astype(np.uint8)).resize((nw,nh),Image.BILINEAR),np.float32)
    oy,ox=(nh-H)//2,(nw-W)//2; return big[oy:oy+H,ox:ox+W]

def grab(src_file,crop,src0,nframes):
    tmp=tempfile.mkdtemp()
    subprocess.run([FF,'-y','-ss',str(src0),'-i',src_file,'-vf',crop,'-frames:v',str(nframes),os.path.join(tmp,'p%03d.png')],capture_output=True)
    arr=[np.asarray(Image.open(os.path.join(tmp,f'p{i+1:03d}.png')).convert('RGB'),np.float32) for i in range(nframes)]
    shutil.rmtree(tmp,ignore_errors=True); return arr

def build(cut,from_tag,to_tag,effect):
    if effect=='dip': PRE,POST=6,6
    else: PRE,POST=4,9
    NF=PRE+POST; ci=PRE
    fs0=front_src_at(cut)-PRE/FPS; ss0=fs0+SIDE_OFF
    Fr=grab(FRONT,FCROP,fs0,NF); Sd=grab(SIDE,SCROP,ss0,NF)
    A=Fr if from_tag=='C9146' else Sd; B=Fr if to_tag=='C9146' else Sd
    out=tempfile.mkdtemp()
    for i in range(NF):
        if effect=='dip':
            if i<=ci-1: b=max(0,(ci-1-i)/(ci-1)); fr=A[i]*b
            else: k=i-ci; b=min(1,k/(POST-1)); fr=B[i]*b
        else:  # zoom-punch
            if i<ci: f=1+0.09*(i/ci); fr=zoom(A[i],f)
            else: k=i-ci; f=1+0.14*max(0,(POST-1-k))/(POST-1); fr=zoom(B[i],f)
        Image.fromarray(np.clip(fr,0,255).astype(np.uint8)).save(os.path.join(out,f'p{i:03d}.png'))
    mp4=DL+f'0616_atr_{str(cut).replace(".","")}.mp4'
    subprocess.run([FF,'-y','-framerate',str(FPS),'-i',os.path.join(out,'p%03d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-r',str(FPS),mp4],capture_output=True)
    shutil.rmtree(out,ignore_errors=True)
    return mp4, round(cut-PRE/FPS,3)

CUTS=[(22.77,'C9138','C9146','dip'),(53.70,'C9146','C9138','dip'),(69.20,'C9138','C9146','dip'),
      (33.40,'C9146','C9138','punch'),(34.70,'C9138','C9146','punch'),(41.53,'C9146','C9138','punch')]
placements=[]
for cut,a,b,eff in CUTS:
    mp4,pt=build(cut,a,b,eff); placements.append((mp4,pt)); print(f'built {eff} @ {cut} -> place {pt}')

# ---- place ----
shutil.copy2(PROJ,PROJ+'.before-atrans')
M=d['materials']
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
    vb['id']=mid; vb['path']=mp4; vb['duration']=DURv; vb['width']=1080; vb['height']=1920; vb['material_name']='atr-'+os.path.basename(mp4)[:-4]
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
print('placed',len(placements),'angle transitions | SAVED')
