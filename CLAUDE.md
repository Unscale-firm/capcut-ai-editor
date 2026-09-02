# SmartCut MCP Server — Project Context

> **✂️ EDITING THE UNSCALE VSL?** All edit instructions + b-roll live in **`vsl-edit/`**
> — read `vsl-edit/CLAUDE.md` first. Pull before every session; only cut increments
> marked LIVE in `vsl-edit/CHANGELOG.md`.

## ADS — standing rules (read before any ad build or b-roll pass)

These are founder directives that apply to **every** ad, in every session. They do not
need to be restated in the prompt. Do not re-derive them, do not re-ask for approval on
them, and do not override them from a README or an older asset folder.

### Session hygiene (parallel sessions are normal here)

Several ad sessions usually run at once. Assume another session is writing the same
paths right now.

- Render from an isolated clone, never from `~/my-video`:
  `rsync -a --exclude node_modules ~/my-video/ ~/my-video-<ad>/ && ln -s ~/my-video/node_modules ~/my-video-<ad>/node_modules`
  Trim the clone's `public/` to only that ad's mp4s.
- `capcut-ai-editor/work_*` dirs are NOT session-private. Before reusing or copying a
  `base_cut.mp4`, check for a live writer (`pgrep -f <dir>`), and copy outputs into this
  session's clone as soon as they exist.
- Take the machine-wide render lock — `exec 9>/home/unscale/.remotion-render.lock; flock 9`
  — then also wait out lock-unaware renders (`pgrep -f "remotion render new-ad"`).
  Render with `--concurrency=2`, retry up to 3×. Two concurrent Remotion renders exhaust
  resources and kill each other.
- Check free disk before rendering. This machine has run at 97-100% full.

### Checkpoint before building

Ad prompts are often short ("build F25, hooks 1-3") because the founder is running
several chats at once. Short prompt ≠ free rein. Before the b-roll/FX pass, post the
plan — cut list and the b-roll beats with their anchor phrases — and wait. A wrong
decision caught at the plan costs one message; caught at the render it costs an hour.

### Founder-flagged mistakes (from 48 chat handoffs, 2026-09-02) — hard rules

Each of these was raised in many chats. Treat them as failures, not preferences.

1. **No clipped words, no dead air.** Cuts land on silence (`pipeline/seams.py`) and every
   assembled cut is re-listened to (`pipeline/verify_words.py`). Never surface a cut whose
   verdict is FAIL. When the founder names a timestamp ("at 45s"), open that exact moment,
   fix it, and re-check it at that timestamp before answering.
2. **Report per item, verified.** A fix request with N items gets N lines back: item → what
   changed → how it was checked (frame / timestamp / measurement). Never say "done" for a
   list where one item is untouched. Never claim a fix that was not looked at or listened to.
3. **Every delivery goes through the loudness gate.** No file reaches `/srv/media/all the ads/`
   or Downloads without `loudnorm` (I=-14, TP=-1.5) + `aresample=48000` and a `volumedetect`
   readout in the message. "Sound too low" is the #2 complaint; a quiet delivery is a failed one.
4. **Hooks are built on the shared body, never by re-rendering the body.** h1/h2/h3 share one
   body render; a fix to the body is applied once and all hooks re-assembled. The founder has
   said "don't re-render the body" 15+ times.
5. **Never delete, move, or overwrite another session's files.** Before any delete or cleanup:
   `pgrep -f <dir>` for a live writer, and leave anything modified in the last 2 hours. Never
   touch `/srv/media/pangeatwoFTP`. Wrong version used = check the ad index first (rule 8).
6. **Look at the frames before rendering.** One still at every angle switch and every b-roll
   peak, checked for: face centred after the switch, nothing over the mouth, card readable,
   correct camera at the head-turn. Over-zoom and late switches are caught here, not by the founder.
7. **Machine check before every render:** free disk ≥ 15 GB on `/` and `/srv/media`, and no
   `ollama` holding VRAM (`nvidia-smi`; stop it if it holds > 4 GB). A render that writes
   nothing because the GPU was full has happened.
8. **One source of truth per ad:** `vsl-edit/ads-edit/ADS_INDEX.md` — ad number, F-code, the
   one latest file per hook, work dir, session id. Read it before touching an ad; update it at
   the end of every build or delivery. "Which chat edited ad N" must be answerable from it.
9. **Names in captions:** AMINE, McKinsey, Unscale, Forbes 30 Under 30. Check every new
   `captionsData*.ts` for Whisper's spellings (Amin, McKenzie, OnScale, "430") before render.
10. **Time estimate first, then work.** Anything over 10 minutes gets a one-line estimate before
    starting. Work runs on this machine (hybrok), never on the founder's laptop.
11. **Ask once, then stop.** A gate question (b-roll folder, SFX, delete verdict) that gets no
    answer is not approval. Do not proceed, do not re-ask three times; park it in the handoff.
12. **Log the chat before it ends.** One line per session in `/srv/media/chat-handoffs/CHATLOG.md`
    (`Z:\chat-handoffs\CHATLOG.md` on Windows): `venv/bin/python pipeline/chatlog.py --session <id>
    --ads "F10, ad 13" "what was done, plain words"`. Run it at the end of every session and before
    every handoff. The founder searches this file by word; a chat that is not in it is lost.
13. **Commit after every pipeline change.** A script or doc edited in `pipeline/`, `.claude/commands/`
    or `vsl-edit/ads-edit/` gets committed in the same session (no Co-Authored-By trailer). Untracked
    scripts have been lost to reboots and cleanups before.

### B-roll pass

Full pass in one go, from repo assets plus your own designed motion-graphic cards. No
per-item approval gate — build it, then show the render for review.

- **Anchor every b-roll to the exact spoken phrase that names it.** Never filler
  placement. Get the timing from the caption frame (`from` + `rel` in
  `captionsData<AD>.ts`), never from a rough transcript estimate.
- **Collision-check in a script, not by eye.** Compare each b-roll's (start, end) AND
  vertical band against the other b-rolls and against the base's baked SpokenFX pops.
  Baked bands on 1080×1920 ads: stat pops y880-1020, qmarks y380-560, closing capital
  pop y1240-1400, CTAButton y1200, burned captions y1450-1560.
- **Never crop a source that is itself zooming.** Sample the clip across time (hstack of
  5 frames) and pick a window that is framed well throughout.
- **Magnifier lens only when one figure hides in dense text**, locked, not sweeping.
  Everywhere else: show the screenshot BIGGER and static. Legibility comes from size.
- **A word-slam over the mouth gets removed at source**, from the comp's FXS + re-render.
  Never patch it with a cover band.
- Locked looks: no flash/black on b-rolls, each animates in on its own, vary the
  treatment (never the same twice in a row), video inserts wrapped in their own
  `Sequence` (otherwise they clamp to the last frame).
- **Ship b-roll passes SILENT** (voice track only). No SFX on reveals unless explicitly
  asked. Removing them is an ffmpeg re-encode from `<ad>-brolls-raw.mp4`, never a
  re-render.
- Copy finished renders to the share `/srv/media/<ad>-brolls/`, not only `~/Downloads`.

### Assets

- **Forbes 30U30:** use `/srv/media/B-roll assets/increment-3_forbes+mirage/forbes-30u30_CANONICAL_2020_clean.png`
  for every ad. Static centered card, ~1000px wide. Every older Forbes still and the
  `.webm` capture are watermarked — superseded, never use them.
- **`social-proof/` is NOT VSL-exclusive.** `contracts/` and `payments/` may be cut into
  paid ads; the README's VSL-only table is overridden by the founder. Cleared client
  names: Fireside Dent, Savela & Associates, PangeaTwo, Jason Batt. Flag any file showing
  a name outside that list. Treatment rules still hold: invoice-POP style (amount + payer
  + Settled badge, 1-2s), contract headers/clauses rather than full terms, never
  un-redact anything.
- Invented graphics (stat / odds / contrast / timeline cards) are encouraged. Fake
  real-proof lookalikes (invented emails, invented payments) are forbidden — proof comes
  from the repo only.
- **Spelling: AMINE**, not AMIN. Whisper gets this wrong. Check it in every new ad's
  captions data.

### Render / audio

- GPU by default: `-c:v h264_nvenc -preset p4 -tune hq -rc vbr -cq 19 -b:v 0`, and
  `-hwaccel cuda` before `-i`. faster-whisper: `device="cuda", compute_type="float16"`.
  Remotion has no NVENC on Linux — it stays CPU, don't fight it.
- **Fresh Remotion renders come out ~19 dB quiet.** Staged footage carries raw mic audio;
  the approved base renders were loudness-passed after Remotion. Normalize the voice in
  the final ffmpeg pass:
  `[0:a]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[voice]`
- `loudnorm` silently resamples to 96 kHz — always chain `aresample=48000` and pass
  `-ar 48000`, or the mic-quality check fails.
- Verify with `volumedetect` against the base render: mean near -18 dB, peak near -1 dB.
  It prints `mean_volume` before `max_volume` — grep the labels, don't parse by position.

## What is this?

MCP server for automated "talking head" video editing. Works with Claude Code to:
- Read CapCut's auto-generated subtitles
- Heuristically find silences (gaps > 1 sec between subtitles)
- Detect duplicate takes (keeps the last one)
- Cut directly in the CapCut project (no backups, no copies)
- Optionally use OpenAI GPT for better duplicate detection

## Project Structure

```
src/smartcut/
├── __init__.py              # Version
├── config.py                # Settings, env vars, constants
├── server.py                # MCP server entry point, 3 tools
├── core/
│   ├── models.py            # Pydantic models (CapCutSubtitleSegment, etc.)
│   ├── whisper_client.py    # OpenAI Whisper API wrapper (optional)
│   ├── llm_client.py        # GPT for duplicate detection (optional)
│   ├── ffmpeg_utils.py      # FFmpeg audio extraction (optional, for Whisper)
│   ├── capcut_reader.py     # CapCut project reader/modifier + subtitle parser
│   └── capcut_finder.py     # CapCut project discovery
└── tools/
    └── capcut_projects.py   # All 3 MCP tools + heuristic analysis engine
```

## Key Files

### config.py
- `Settings` class with env vars: `OPENAI_API_KEY` (optional), `CAPCUT_DRAFTS_DIR`
- Constants: `SILENCE_THRESHOLD_SEC = 1.0`, `DUPLICATE_SIMILARITY_THRESHOLD = 0.6`

### server.py
- 3 MCP tools: `list_capcut_projects`, `open_capcut_project`, `smart_cut_project`

### capcut_reader.py
- `CapCutProject` class for loading/modifying existing CapCut projects
- Key methods: `load()`, `save()`, `get_subtitle_segments()`, `remove_time_ranges()`
- Reads `draft_info.json` (content) and `draft_meta_info.json` (metadata)

### tools/capcut_projects.py
- Main tool: `smart_cut_project()` — the core function
- Heuristic engine: `find_gaps()`, `find_duplicate_takes()`, `compute_text_similarity()`
- Optional: `_detect_duplicates_with_llm()` for OpenAI-enhanced detection

### capcut_finder.py
- `get_capcut_drafts_dir()` - auto-detects CapCut drafts location
- macOS: `~/Movies/CapCut/User Data/Projects/com.lveditor.draft/`
- Windows: `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft\`

## CapCut Format Notes

- Times are in **microseconds** (1 sec = 1,000,000 μs)
- Video segments have `source_timerange` (where in source) and `target_timerange` (where on timeline)
- Text segments have `target_timerange` only (`source_timerange` is null)
- Auto-generated subtitles: `materials.texts[]` with `recognize_task_id != ""`
- Subtitle word timing: `words.start_time[]` / `words.end_time[]` in **milliseconds**, relative to segment start
- Display text is in `content` JSON field (not top-level `text`)
- CapCut monitors drafts folder via FSEvents and may rename/move folders

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| OPENAI_API_KEY | No | - | OpenAI API key (for GPT duplicate detection) |
| CAPCUT_DRAFTS_DIR | No | auto | Path to CapCut drafts folder |

## Running

```bash
cd capcut-ai-editor
python -m venv venv
source venv/bin/activate
pip install -e .
python -m smartcut.server
```

## Common Tasks

### Add new tool
1. Create function in `tools/capcut_projects.py`
2. Add Tool schema in `server.py`
3. Add handler in `call_tool()`

### Debug CapCut issues
- Check `.recycle_bin/` folder in drafts dir — CapCut may move "invalid" projects there
- Verify `draft_info.json` exists (not just `draft_meta_info.json`)
- CapCut may need restart to see changes
