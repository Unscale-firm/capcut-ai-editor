"""Rebuild the clean-voice audio from the draft's audio segments (1-cut925.wav, following the cut),
then mux it onto the silent CapCut export. No music. Output: Downloads/0616-withaudio.mp4
"""
import json, os, subprocess, tempfile, shutil
FF='ffmpeg' if shutil.which('ffmpeg') else (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
    r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
PROJ=r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0616\draft_content.json'
EXPORT='C:/Users/User/AppData/Local/CapCut/Videos/0616(1).mp4'
OUT='C:/Users/User/Downloads/0616-withaudio.mp4'

import glob
def load_audio(path):
    dd=json.load(open(path,encoding='utf-8'))
    at=[t for t in dd['tracks'] if t['type']=='audio']
    if not at or not at[0]['segments']: return None,None
    am={m['id']:m for m in dd['materials']['audios']}
    wav=am[at[0]['segments'][0]['material_id']]['path']
    return wav, sorted(at[0]['segments'],key=lambda s:s['target_timerange']['start'])

WAV,segs=load_audio(PROJ)
if not segs:
    # current draft lost its audio track (export clobber) -> use most recent backup that has it
    for b in sorted(glob.glob(PROJ+'.before-*'),key=os.path.getmtime,reverse=True):
        WAV,segs=load_audio(b)
        if segs: print('recovered audio track from backup:',os.path.basename(b)); break
if not segs: raise SystemExit('no audio track found in draft or backups')
print('clean mic:',WAV)

tmp=tempfile.mkdtemp(); parts=[]
total=0.0
for i,s in enumerate(segs):
    src=s['source_timerange']['start']/1e6; dur=s['source_timerange']['duration']/1e6
    vol=s.get('volume',1.0)
    p=os.path.join(tmp,f'a{i:02d}.wav')
    subprocess.run([FF,'-y','-ss',str(src),'-t',str(dur),'-i',WAV,'-ar','48000','-ac','2',
                    '-af',f'volume={vol}','-acodec','pcm_s16le',p],check=True,capture_output=True)
    parts.append(p); total+=dur
print(f'{len(parts)} voice chunks, total {total:.2f}s')
# concat
lst=os.path.join(tmp,'list.txt')
open(lst,'w').write('\n'.join(f"file '{p}'" for p in parts))
voice=os.path.join(tmp,'voice.wav')
subprocess.run([FF,'-y','-f','concat','-safe','0','-i',lst,'-c','copy',voice],check=True,capture_output=True)
# mux onto export (copy video, replace audio)
subprocess.run([FF,'-y','-i',EXPORT,'-i',voice,'-map','0:v','-c:v','copy','-map','1:a','-c:a','aac','-b:a','256k','-shortest',OUT],check=True,capture_output=True)
shutil.rmtree(tmp,ignore_errors=True)
print('SAVED',OUT)
