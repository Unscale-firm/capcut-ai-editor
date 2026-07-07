---
description: Edit a two-angle talking-head ad end-to-end (UNSCALE pipeline) — sync, cut, captions, b-rolls, transitions, export-fix, grade
argument-hint: "[capcut-project-name] (e.g. 0609)"
---

# /edit-video — Two-angle talking-head ad pipeline (UNSCALE)

Run the full editing pipeline that produced the 0608 ad. Project/draft name = `$1` (ask if missing).

## STEP 0 — Confirm inputs (ask the user)
- **CapCut draft name** (folder under `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\`)
- **Sources in Downloads**: front angle `.MOV`, side angle `.MOV`, voiceover `.wav`, music `.mp3`
- **Narrative beats** → which b-rolls to build (see Phase 7)
- **Brand** (default = UNSCALE below)

## ALWAYS-TRUE RULES
- **CapCut must be CLOSED** before editing `draft_content.json`: `taskkill //F //IM CapCut.exe`, then verify it didn't respawn before writing. Edits while open are erased.
- **Re-baked clips need a NEW filename** every time (e.g. `blurTb-…`, `blurTc-…`) — CapCut caches media by path and shows stale frames otherwise.
- After each project edit, tell the user to **launch CapCut fresh** to review.
- Back up `draft_content.json` to `.before-<step>` before every edit.

## UNSCALE BRAND DEFAULTS
- Colors: bg `#0D0D0D`, orange `#E8762D`, gold `#C8943E`, dark cards `#141414`
- Fonts: `brandfonts/DMSans.ttf` (variable, axes opsz 9–40 / wght 100–1000), `brandfonts/Playfair-Italic.ttf` for serif-italic accents. Captions = `Montserrat-ExtraBold.ttf` (in CapCut Fonts).
- **Captions**: word-by-word, ALL CAPS, lower-third, white + **orange** keywords + **red** on negatives, **drop shadow = a duplicate black caption layer** offset down-right behind the main one (CapCut's shadow setting won't render — render_index of the shadow must be LOWER than the captions).
- **Music**: ~`0.05` volume (5%), 2s fade-out, trimmed to video length.

## PIPELINE
1. **Sync** the two angles by audio (FFT cross-correlation, numpy).
2. **Cut** junk/silences/duplicate takes; trim the voiceover to match.
3. **Angle-switch** front↔side to hide cuts. (`scripts/rebuild_0608_full.py` does cut+zoom+angle+captions in one pass.)
4. **Captions** word-by-word, brand style + shadow layer.
5. **Zoom**: static `1.8×`+ on front clips (set `clip.scale`, NOT a CapCut animation).
6. **Music**: add at 0.05 vol + fade.
7. **B-rolls** — build them **ONE AT A TIME**, and for EACH one: render the graphic, **show the user a preview frame and WAIT for their explicit approval before crossfading/placing it in the video**. Never place a b-roll the user hasn't seen and OK'd; if they want changes, iterate on the preview until approved, then place. Vary the layout per beat (don't reuse one skeleton). Scripts:
   - `scripts/make_broll*.py` build the graphic mp4
   - `scripts/crossfade_broll.py <mp4> <start_s> <4106|4571> <fade_out 0|1>` → `-final.mp4` (blends edges with the camera)
   - `scripts/bake_bg_broll.py` = on-camera background replacement (rembg cutout, contained card behind head)
   - `scripts/place_baked.py <mp4> <start_s>` → drops it full-screen on a new top track
   - 0608 used: copy-paste wall, cold-email, IGNORED card, job-board feed, HR-vs-Hiring-Manager, autopilot loop.
8. **Transitions/FX**:
   - `scripts/make_blur_transition.py <cut_s> <from_tag> <to_tag> <out.mp4>` = blur-whip + white flash at angle switches; place at `cut-0.2`.
   - White **flash pop** (4-frame white mp4) at each b-roll entrance via `place_baked.py`.
9. **Export prep (free plan)** — edit `draft_content.json`:
   - Strip Pro animations from `material_animations[].animations[]`: **Zoom 1, Blur Out, Brighten In, Glow Flash**.
   - Convert auto-captions: `type:"subtitle"`+`recognize_task_id` → `type:"text"`, `recognize_task_id:""`.
10. **User exports** from CapCut (1080×1920) → `%LOCALAPPDATA%\CapCut\Videos\<name>.mp4`.
11. **Post-export finishing — all ffmpeg, no CapCut** (winget ffmpeg at `...Gyan.FFmpeg...\bin\ffmpeg.exe`):
    - **Recover audio** (CapCut silently drops the Pro voiceover → export is −91 dB AND deletes the audio tracks). Run `scripts/reconstruct_audio.py` (reads voiceover chunks + music from a `.before-*` backup that still has audio tracks; `MUSIC_SCALE` ≈ 0.6 of the project's music vol). Mux: `-map 0:v -c:v copy -map 1:a -c:a aac`.
    - **Glitch patch**: freeze a good frame over any 1-2 frame side-sliver — extract freeze.png, `overlay=enable='between(t,A,B)'`.
    - **Grade**: `-vf "eq=contrast=1.06:saturation=1.05,colorbalance=rm=0.03:bm=-0.03:rh=0.02:bh=-0.02,vignette=PI/5,noise=alls=8:allf=t+u" -crf 16 -preset slow` (subtle — "whisper, not filter").
    - **Re-frame zoom** if headroom: crop+scale the FINAL to tighten the talking head, and `overlay` the original b-rolls back during their time windows so their text stays un-zoomed. 0608 final crop = `crop=844:1500:118:223,scale=1080:1920` (~1.28×).

## OUTPUT
`Downloads/<name>-FINAL.mp4` — 1080×1920, with audio. Show the user a few frames + confirm audio level, then iterate.

Reference memories: capcut-must-be-closed-when-editing, capcut-filename-cache, capcut-pro-export-workaround, capcut-grade-pass, capcut-two-angle-workflow.
