"""Rebuild the synced audio (voiceover chunks + music) from the project backup, since CapCut
stripped the audio on the free export. Output: a single mixed audio track matching the 55s video."""
import json, subprocess, os, tempfile
FF = (r'C:\Users\User\AppData\Local\Microsoft\WinGet\Packages'
      r'\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe')
BK = r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\0608\draft_content.json.before-stripPro2'
OUT = 'C:/Users/User/Downloads/0608-audio-q.m4a'
MUSIC_SCALE = 0.6   # lower the music ~-4.4dB per user (voiceover untouched)

d = json.load(open(BK, encoding='utf-8'))
am = {m['id']: m for m in d['materials']['audios']}
vo, music = None, None
for tr in d['tracks']:
    if tr['type'] == 'audio':
        p = am.get(tr['segments'][0]['material_id'], {}).get('path', '')
        if 'script1-2' in p: vo = sorted(tr['segments'], key=lambda s: s['target_timerange']['start'])
        elif 'paulyudin' in p: music = tr['segments'][0]
VOWAV = am[vo[0]['material_id']]['path']
MP3 = am[music['material_id']]['path']

tmp = tempfile.mkdtemp()
# 1) extract each voiceover chunk at its SOURCE range, concat in timeline order
listf = os.path.join(tmp, 'l.txt')
with open(listf, 'w') as lf:
    for i, s in enumerate(vo):
        ss = s['source_timerange']['start'] / 1e6; du = s['source_timerange']['duration'] / 1e6
        c = os.path.join(tmp, f'v{i:02d}.wav')
        subprocess.run([FF, '-y', '-ss', f'{ss:.4f}', '-t', f'{du:.4f}', '-i', VOWAV,
                        '-ar', '48000', '-ac', '2', c], capture_output=True)
        lf.write(f"file '{c}'\n")
vowav = os.path.join(tmp, 'voice.wav')
subprocess.run([FF, '-y', '-f', 'concat', '-safe', '0', '-i', listf, '-ar', '48000', '-ac', '2', vowav], capture_output=True)

# 2) music: volume + fade-out, trimmed to video length
mdur = music['target_timerange']['duration'] / 1e6
mss = music['source_timerange']['start'] / 1e6
mvol = music.get('volume', 1.0) * MUSIC_SCALE
mufade = 2.0
muwav = os.path.join(tmp, 'music.wav')
subprocess.run([FF, '-y', '-ss', f'{mss:.4f}', '-t', f'{mdur:.4f}', '-i', MP3,
                '-af', f'volume={mvol},afade=t=out:st={mdur-mufade:.2f}:d={mufade}', '-ar', '48000', '-ac', '2', muwav], capture_output=True)

# 3) mix voiceover (full) + music (already attenuated), no normalize so levels stay
subprocess.run([FF, '-y', '-i', vowav, '-i', muwav, '-filter_complex',
                '[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]',
                '-map', '[a]', '-c:a', 'aac', '-b:a', '256k', OUT], capture_output=True)
# report
import subprocess as sp
dur = sp.run([FF.replace('ffmpeg.exe','ffprobe.exe'), '-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1', OUT], capture_output=True, text=True).stdout.strip()
print(f'rebuilt audio: {len(vo)} voice chunks + music({mvol} vol, {mufade}s fade) -> {OUT} | dur {dur}s')
