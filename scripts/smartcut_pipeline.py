"""
SmartCut talking-head pipeline — one shot.

Given a CapCut project, applies the full edit we developed on "0607":
  1. Cut duplicate takes + silences + sub-second pauses (>0.35s, keeps 0.1s breathing room)
  2. If a separate extracted-audio track exists (same source as the video), sync it to the
     final cut and mute the video's built-in audio (no echo)
  3. Rebuild captions WORD-BY-WORD: each word appears as spoken — Montserrat ExtraBold,
     ALL CAPS, uniform size, white with a dark-grey outline, centered on screen,
     orange (#E8762D) on the keywords you pass
  4. Zoom the video 1.8x (4K source stays sharp)

CapCut MUST be closed first (it overwrites the draft otherwise). Backs up before editing.

Usage:
  python scripts/smartcut_pipeline.py "0607" --keywords ai,npc,mckinsey,mandates,placements
"""
import argparse, json, shutil, copy, uuid, re, subprocess, sys
from pathlib import Path

# ---- repo imports (for the all-tracks cutter + duplicate detection) ----
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'src'))
from smartcut.core.capcut_reader import CapCutProject
from smartcut.tools.capcut_projects import find_duplicate_takes

DRAFTS = Path(r'C:\Users\User\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft')

# ---- locked-in style (from project 0607) ----
FONT = 'C:/Users/User/AppData/Local/CapCut/Fonts/Montserrat-ExtraBold.ttf'
WHITE = [1.0, 1.0, 1.0]
ORANGE = [0.9098039, 0.4627451, 0.1764706]     # #E8762D
STROKE_RGB = [0.251, 0.251, 0.251]             # #404040 dark grey
STROKE_HEX = '#404040'
SIZE = 18.0
STROKE_W = 0.08
CENTER_X, CENTER_Y = 0.0, 0.0
ZOOM = 1.8
PAUSE_THRESH_US = int(0.35 * 1_000_000)
PAUSE_PAD_US = int(0.10 * 1_000_000)
US = 1_000_000

STOP = set("""a an the and or but so if of to in on at for with as by is are was were be been am
i you he she it we they me him her us them my your his its our their this that these those
what which who whom there here then than too very just do does did have has had will would
can could should im id ive youre dont its theres about into out up down over under all""".split())


def guid():
    return str(uuid.uuid4()).upper()


def clean(tok):
    return re.sub(r"[^a-z0-9]", "", tok.lower())


def capcut_running():
    out = subprocess.run(['tasklist'], capture_output=True, text=True).stdout.lower()
    return 'capcut.exe' in out


def find_project(name):
    matches = [p for p in DRAFTS.iterdir() if p.is_dir() and name.lower() in p.name.lower()]
    if not matches:
        raise SystemExit(f'No CapCut project matching "{name}" in {DRAFTS}')
    # prefer exact, else shortest name
    exact = [p for p in matches if p.name.lower() == name.lower()]
    return (exact or sorted(matches, key=lambda p: len(p.name)))[0]


# ---------------------------------------------------------------- cutting
def compute_cut_ranges(proj):
    subs = sorted(proj.get_subtitle_segments(), key=lambda s: s.timeline_start_us)
    ranges = []
    # sub-second pauses (with padding so it doesn't sound clipped)
    for i in range(len(subs) - 1):
        gap = subs[i + 1].timeline_start_us - subs[i].timeline_end_us
        if gap > PAUSE_THRESH_US:
            a = subs[i].timeline_end_us + PAUSE_PAD_US
            b = subs[i + 1].timeline_start_us - PAUSE_PAD_US
            if b > a:
                ranges.append((a, b))
    # duplicate takes (keeps the last take)
    ranges += list(find_duplicate_takes(subs))
    # dead air at very start / end
    if subs:
        if subs[0].timeline_start_us > 0:
            ranges.append((0, subs[0].timeline_start_us))
        if proj.duration_us > subs[-1].timeline_end_us:
            ranges.append((subs[-1].timeline_end_us, proj.duration_us))
    # merge into sorted non-overlapping
    ranges.sort()
    merged = []
    for a, b in ranges:
        if merged and a <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], b))
        else:
            merged.append((a, b))
    return merged


# ---------------------------------------------------------------- audio sync
def sync_audio(content):
    """If a separate audio track shares the video's source file, split it to mirror the
    final video cuts and mute the video's own audio. Returns a status string."""
    vids = [tr for tr in content['tracks'] if tr['type'] == 'video']
    auds = [tr for tr in content['tracks'] if tr['type'] == 'audio']
    if not vids or not auds:
        return 'no separate audio track — left video audio as-is'
    video_srcs = {m.get('path') for m in content['materials'].get('videos', [])}
    aud_mats = content['materials'].get('audios', [])
    # only sync when the audio is extracted from the same recording as the video
    same = [a for a in aud_mats if a.get('path') in video_srcs]
    if not same:
        return 'audio track is a different source (e.g. music) — left it untouched'
    vsegs = sorted(vids[0]['segments'], key=lambda s: s['target_timerange']['start'])
    for atr in auds:
        if not atr['segments']:
            continue
        tmpl = copy.deepcopy(atr['segments'][0])
        new = []
        for vs in vsegs:
            seg = copy.deepcopy(tmpl)
            seg['id'] = guid()
            seg['source_timerange'] = dict(vs['source_timerange'])
            seg['target_timerange'] = dict(vs['target_timerange'])
            seg['render_timerange'] = {'start': 0, 'duration': 0}
            seg['volume'] = 1.0
            new.append(seg)
        atr['segments'] = new
    for vtr in vids:
        for s in vtr['segments']:
            s['volume'] = 0.0
    return f'synced audio to {len(vsegs)} video cuts + muted video audio'


# ---------------------------------------------------------------- word-by-word captions
def rebuild_captions(content, keywords):
    kw = {clean(k) for k in keywords}
    text_tracks = [tr for tr in content['tracks'] if tr['type'] == 'text']
    if not text_tracks:
        return 'no captions found'
    mat_by_id = {m['id']: m for m in content['materials']['texts']}
    tmpl_mat = copy.deepcopy(content['materials']['texts'][0])
    tmpl_seg = copy.deepcopy(text_tracks[0]['segments'][0])

    words = []
    for tr in text_tracks:
        for seg in tr['segments']:
            mat = mat_by_id.get(seg['material_id'])
            if not mat:
                continue
            w = mat.get('words') or {}
            toks, starts = w.get('text') or [], w.get('start_time') or []
            seg_start = seg['target_timerange']['start']
            real = [(toks[i], starts[i]) for i in range(min(len(toks), len(starts))) if toks[i].strip()]
            if not real:
                real = [(json.loads(mat['content']).get('text', ''), 0)]
            for tok, st_ms in real:
                color = ORANGE if clean(tok) in kw else WHITE
                words.append({'start_us': seg_start + st_ms * 1000, 'text': tok.upper(), 'color': color})

    words.sort(key=lambda x: x['start_us'])
    for i in range(1, len(words)):
        if words[i]['start_us'] <= words[i - 1]['start_us']:
            words[i]['start_us'] = words[i - 1]['start_us'] + 1
    proj_end = content['duration']
    for i, wd in enumerate(words):
        nxt = words[i + 1]['start_us'] if i + 1 < len(words) else proj_end
        wd['dur'] = max(1, nxt - wd['start_us'])

    new_mats, new_segs = [], []
    for wd in words:
        mid, txt = guid(), wd['text']
        m = copy.deepcopy(tmpl_mat); m['id'] = mid
        content_obj = {
            'styles': [{
                'fill': {'alpha': 1.0, 'content': {'render_type': 'solid',
                         'solid': {'alpha': 1.0, 'color': wd['color'][:]}}},
                'strokes': [{'content': {'render_type': 'solid',
                            'solid': {'alpha': 1.0, 'color': STROKE_RGB[:]}}, 'width': STROKE_W}],
                'font': {'id': '', 'path': FONT},
                'range': [0, len(txt)], 'size': SIZE,
            }],
            'text': txt,
        }
        m['content'] = json.dumps(content_obj, ensure_ascii=False)
        m['words'] = {'text': [txt], 'start_time': [0], 'end_time': [int(wd['dur'] / 1000)]}
        m['font_path'] = FONT; m['font_name'] = 'Montserrat'; m['font_title'] = 'Montserrat ExtraBold'
        m['font_id'] = ''; m['font_resource_id'] = ''
        m['text_color'] = '#%02X%02X%02X' % tuple(int(x * 255) for x in wd['color'])
        m['font_size'] = SIZE; m['text_size'] = int(SIZE * 3); m['letter_spacing'] = -0.04
        m['alignment'] = 1; m['line_max_width'] = 1.0; m['force_apply_line_max_width'] = False
        m['is_rich_text'] = False
        m['border_color'] = STROKE_HEX; m['border_alpha'] = 1.0
        m['border_width'] = STROKE_W; m['border_mode'] = 0
        new_mats.append(m)

        s = copy.deepcopy(tmpl_seg); s['id'] = guid(); s['material_id'] = mid
        s['target_timerange'] = {'start': wd['start_us'], 'duration': wd['dur']}
        s['source_timerange'] = None
        s['clip']['transform']['x'] = CENTER_X; s['clip']['transform']['y'] = CENTER_Y
        s['clip']['scale']['x'] = 1.0; s['clip']['scale']['y'] = 1.0
        new_segs.append(s)

    content['materials']['texts'] = new_mats
    nt = copy.deepcopy(text_tracks[0]); nt['id'] = guid(); nt['segments'] = new_segs
    content['tracks'] = [tr for tr in content['tracks'] if tr['type'] != 'text'] + [nt]
    n_orange = sum(1 for w in words if w['color'] == ORANGE)
    return f'{len(new_segs)} word segments, {n_orange} orange'


def apply_zoom(content):
    n = 0
    for tr in content['tracks']:
        if tr['type'] == 'video':
            for s in tr['segments']:
                s['clip']['scale']['x'] = ZOOM; s['clip']['scale']['y'] = ZOOM
                n += 1
    return f'{ZOOM}x on {n} clips'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project', help='project name (partial match)')
    ap.add_argument('--keywords', default='', help='comma-separated words to highlight orange')
    args = ap.parse_args()

    if capcut_running():
        raise SystemExit('CapCut is OPEN — fully quit it first (it overwrites the draft), then re-run.')

    path = find_project(args.project)
    keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]
    print(f'Project: {path.name}')
    print(f'Keywords (orange): {keywords or "(none)"}')

    proj = CapCutProject(path)
    backup = proj.content_file.with_suffix(proj.content_file.suffix + '.pipeline-bak')
    shutil.copy2(proj.content_file, backup)
    print(f'Backup: {backup.name}')

    cuts = compute_cut_ranges(proj)
    proj.remove_time_ranges(cuts)
    print(f'1. Cut {len(cuts)} ranges (dups + silences + pauses), removed '
          f'{round(sum(b-a for a,b in cuts)/US,2)}s')

    print('2.', sync_audio(proj._content))
    print('3.', rebuild_captions(proj._content, keywords))
    print('4. Zoom', apply_zoom(proj._content))

    proj.save()
    print(f'Saved. Duration: {round(proj._content["duration"]/US,2)}s — reopen CapCut to review.')


if __name__ == '__main__':
    main()
