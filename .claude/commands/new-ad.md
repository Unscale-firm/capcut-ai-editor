---
description: Build a new ad from a folder of raw footage (two angles + clean mic) — CapCut-free
---

# /new-ad — automated ad builder

Input: `$ARGUMENTS` = path to a folder containing the **two camera videos** + the **clean mic** audio.

Run the whole pipeline. All commands run from `C:\Users\User\capcut-ai-editor`. Use the venv python
(`venv/Scripts/python.exe`) for the pipeline scripts. Work dir: `work_cut` (or `work_<adname>`).

## Steps

1. **Find the files** in `$ARGUMENTS`: the two `.mp4`/`.mov` files are the camera angles, the
   `.wav`/`.mp3` is the mic. **Ask the user which video is the FRONT camera** (the main one he faces) —
   that one defines the cut. The other is the side angle.

2. **Sync + transcribe** (CapCut-free; Whisper does the transcript, audio cross-correlation does the sync):
   ```
   venv/Scripts/python.exe pipeline/sync_transcribe.py --front <FRONT> --side <SIDE> --mic <MIC> --work work_cut
   ```
   Report the offsets and word count.

3. **Cut — best-take selection.** First run WITHOUT assembling to see the kept-line list:
   ```
   venv/Scripts/python.exe pipeline/cut_heuristic.py --work work_cut
   ```
   **You (the assistant) act as the editor:** read the numbered kept lines and decide which to drop —
   the warmup/slate/chatter and, where a line was filmed several times with different wordings, keep the
   single best take (cleanest, most complete, best delivery). The user does NOT pick. Then assemble:
   ```
   venv/Scripts/python.exe pipeline/cut_heuristic.py --work work_cut --front <FRONT> --drop "<your,drops>" --assemble
   ```

4. **Finalize into Remotion** (installs footage, generates captions, sets duration):
   ```
   venv/Scripts/python.exe pipeline/finalize.py --work work_cut
   ```

5. **Show the result.** Render a still or the full `new-ad` composition and open it:
   ```
   cd C:/Users/User/my-video && npx remotion render new-ad C:/Users/User/Downloads/new-ad.mp4 --codec=h264
   ```
   Open it for the user. This is the cut + standard look (1.1x speed, steady zoom, captions).

5b. **SPOKEN WORD & NUMBER EFFECTS — small pop-ups synced to what he says (placed by you, NOT gated).**
   These are the little on-screen reactions that fire on *special spoken words* — a word slam, question
   marks, a stat number, spelled-out rule counters, a pull-quote. They are **small, tasteful pop-ups tied
   to the transcript**, NOT big full-frame graphic panels (those are b-rolls, which the user often does
   *not* want — do not confuse the two). You place them yourself during the silent build (same as angle
   switches), synced to the step-2 word-timings; the user reviews after surfacing. All live in
   `my-video/src/SpokenFX.tsx`, rendered via `<SpokenFX fx={FXS} />`. Effect kinds:

   | Kind | When | Look (LOCKED from user feedback) |
   |------|------|----------------------------------|
   | `word` | a punchy word ("a big **YES**") | white slam, **straight — no tilt/bend**, big; slams in from oversized. Nudge slightly EARLY-safe (user found it landing a hair late). |
   | `qmarks` | a rhetorical question ("what do these have in **common?**") | two orange "?" bob around the head (one each side). Don't fire them too early — land them ON the question, not before. |
   | `num` | a real stat is spoken ("**19%** reply rate", "**10–50** meetings") | big, **FADED WARM ORANGE (never grey)**, sits **LOW in the lower third — off his face**, with a caps label under it. Best for genuine stats; a bare small integer ("7") can "feel wrong" — prefer it only for real numbers/percentages. If the label carries the words, **delete that phrase from the caption** so they don't double up. |
   | `rulword` | enumerating rules ("number **one**…") | spell out the **actual word** ("ONE", not "1"), elegant **gold serif**, floated **above his head but kept low** (not a floating billboard). |
   | `quote` | a prospect's actual words ("your email scared me") | serif pull-quote card with oversized orange quotation marks. |
   | `industry` | listing verticals ("SaaS, consulting…") | names build one-by-one in a **distinct elegant serif** (Georgia/Playfair italic), NOT the caption font. |

   Locked rules (from this session's feedback):
   - **Small + special, not billboards.** The ask is "small pop-ups when he says special words / a question in
     a special font / emoji accents" — creative but restrained. If it reads like a full graphic panel it's a
     b-roll, and those aren't wanted here.
   - **Good fonts only.** Montserrat ExtraBold for slams/stats, an elegant serif (Georgia/Playfair italic) for
     rule words / quotes / industries. **Never a generic/ugly label font** — the user flat-out rejected a bad
     label font ("the outbound message is a really bad font"). Emoji accents are welcome where they fit.
   - **Never cover his face.** Stats sit low, rule words sit above/low on the head, the slam is centered but
     brief. Suppress the burned-in caption under any FX window so the words don't clash (the composition
     filters caption lines that overlap an FX window).
   - **Timing is everything.** Sync each to the exact spoken word from the step-2 word-timings; a beat late or
     early reads wrong (the user caught both). Snapshot the peak frame and LOOK before rendering.
   - You place these silently during the build (not gated); the user tweaks timing/size on review.

6. **B-rolls = the ONLY approval gate.** Angle switches are NOT gated anymore — you place them yourself
   (same as the take/cut calls). Build the entire ad **silently** (cut → switches → captions → spoken
   word/number effects → transition look → render) and do NOT message the user at all until this last
   pre-broll step is done. Only then surface. If the user wants a switch changed, they will tell you BEFORE
   the b-roll review.

   **6a. ALWAYS ASK FOR THE B-ROLL FOLDER FIRST.** The moment the b-roll gate opens, ask the user for the
   **path to the folder holding the b-roll assets** (screenshots, email replies, dashboards, stock, etc.).
   Never guess it, never assume the last ad's folder, never invent b-rolls from nothing. Then `ls` it and
   show the user what you found (grouped by kind — email replies / stat screenshots / other) before
   proposing anything. If the folder is empty or missing, say so and stop — do not fabricate social proof.

   **6b. Match assets to the script.** Read the transcript word-timings (step 2). A talking-head ad usually
   *names* its own b-rolls ("this is the outbound message", "your email scared me") — those phrases are the
   placements. Sync each asset to the moment its phrase is spoken; don't scatter them evenly.

   **6c. LOAD THE HYPERFRAMES SKILLS BEFORE DESIGNING B-ROLLS.** Invoke the `hyperframes` skill (the router)
   and let it point you at the right workflow — `talking-head-recut` for graphic overlay cards on existing
   footage, `motion-graphics` for a short unnarrated sting or a transparent lower-third. Pull in
   `hyperframes-animation` / `hyperframes-creative` on demand for motion and design direction. Use them for
   the **design thinking** (card archetypes, motion vocabulary, pacing) even when the b-roll is ultimately
   built as a Remotion component — the skills are the reference, Remotion is usually the renderer.
   Installed at `~/.claude/skills/hyperframes*`.

   Then b-rolls one at a time: build → show a preview frame → wait for the user's **yes / no / pick** →
   only then place. NEVER auto-place a b-roll. (See the broll-approval-first memory.)

   **6d. SOUND EFFECTS — part of THIS gate, not a later step.** SFX belong to the b-roll gate (the
   pre-broll cut reveal), proposed the SAME way as b-rolls — one short list → user says **yes / no / tweak**
   → then apply. They are NOT a separate trailing step after the b-rolls are done. SFX are OPTIONAL polish
   and must be **SPARSE** — a ~25s talking-head ad wants **~5–8 hits total, never one per cut**. Overusing
   them kills the effect. Bundled library: `C:\Users\User\.claude\skills\media-use\audio\assets\sfx\`.

   | On-screen moment | Sound | Vol |
   |------------------|-------|-----|
   | biggest 1–2 pivots / angle switches (NOT every switch) | `whoosh` | 0.20 |
   | a graphic/word reveal pop ("YES", a stat number, "KUDOS") | `pop` | 0.32 |
   | a **question-mark graphic** — one `ping` **per "?"** (two ?'s → two pings ~0.25s apart) | `ping` | 0.28 |
   | one light emphasis tap on a key stat/word (use **once**) | `click-soft` | 0.25 |
   | (optional) a "reply / message received" beat | `notification` | 0.32 |
   | (optional) an email-being-written / "message" beat | `typing` | 0.25 |

   Locked rules (from user feedback — see the SFX memory):
   - **Volumes LOW.** SFX sit UNDER the voice, never jump out. Table levels are the ceiling; go quieter if unsure.
   - **`whoosh` soft + sparse** — max ~2 per ad, biggest pivots only. Never one per transition.
   - **`click-soft` at most once or twice** — overusing it kills it.
   - **Match the sound to the moment.** A sound in the wrong place is worse than none — no `typing` unless
     something is actually being written; no `notification` unless it's a genuine reply/message beat.
   - Get exact timestamps from the transcript word-timings (step 2) + the cut / b-roll frames.

   Apply as a **final ffmpeg AUDIO pass** on the rendered mp4 (ffmpeg = audio only, consistent with the
   Remotion rule): per cue `[i:a]adelay=<ms>:all=1,volume=<v>`, then
   `amix=inputs=N:duration=first:normalize=0`, `-c:v copy -c:a aac`. Re-open for the user.

7. **STANDARD TRANSITION — ANGLE SWITCHES ONLY (updated 2026-07-06).** The full beat —
   **zoom-punch + orange FLASH (out) → BLACK dip → orange FLASH (in)** — goes on **angle switches only**.
   **B-rolls get NO flash and NO black dip** — they animate in on their own (slide from a side, rise
   from the bottom, or fade), so they never take the flash/black/punch. All drop-ins live in `my-video/src/OrangeFlash.tsx`:
   - Overlay `<TransitionFX cut={frame} />` at every transition frame — this renders flash→black→flash.
   - Scale the footage layer by `transitionZoom(frame, cut)` (1.2× punch on both flashes; parent needs `overflow:hidden`).
   - Switch the underlying footage A→B AT `cut` (hidden under the black dip).
   e.g. `{CUTS.map((c,i)=><TransitionFX key={i} cut={c}/>)}`.
   Locked look: fast/punchy (`FLASH_W=4`), rich orange gradient, low-key/semi-transparent, sweeps LEFT
   → top-right, FILLS the frame, NOT blinding; black dip ~3 frames marks the switch. No need to ask —
   it goes on every transition by default.

7b. **SCREENSHOT B-ROLLS — CENTERED MAGNIFIER (locked look, 2026-07-09).** Any b-roll that is a
   *readable screenshot* (email reply, Slack message, dashboard) uses `my-video/src/SocialProofMagnifier.tsx`.
   Readability is the whole point — never shrink a screenshot to make it fit.

   - **Placement: chest level, `centerY = 1132`** on the 1080×1920 canvas. This is locked. Above the head
     reads as a floating billboard and the user rejected it; true centre (y=960) covers his mouth; the desk
     is too cramped. 1132 sits below the chin and above the burned-in captions.
   - **Width ~1000px, horizontally centred**, white rounded panel + heavy drop shadow.
   - **A magnifier lens sweeps the key sentence** as it is spoken — a circular lens holding a `z = 2.25`
     copy of the screenshot, radius `r = 108`, tracking left→right along that line. Time `lens.start` /
     `lens.end` to the transcript word-timings of the exact phrase.
   - Measure `focus.y` / `focus.x0` / `focus.x1` in **display pixels** (i.e. against the image scaled to the
     panel width), not the source image's native pixels. `ox` / `oy` account for panel borders.
   - **Verify before rendering.** Snapshot one frame mid-sweep and LOOK at it — lens geometry is easy to get
     subtly wrong, and a misaligned lens magnifies the wrong words.

   ```tsx
   <SocialProofMagnifier
     src="proof/outbound.jpg" w={1000} h={231}
     chip="NEW REPLY"
     focus={{ y: 190, x0: 48, x1: 298 }}
     lens={{ start: 20, end: 55 }}
     highlight={{ x: 24, y: 180, w: 288, h: 20, at: 12 }}
   />
   ```

   Optional: a `<1%`-style stat card (scrim + count-down) or a count-up dashboard card make good non-screenshot
   beats between magnifier cards — vary the pattern, never the same treatment twice in a row.

## Rules
- No CapCut, ever. **Remotion owns the timeline and the final render** — no ffmpeg-baked video (base cut,
  side framing, effects all done natively in Remotion via Sequences/OffthreadVideo). Whisper is the ONLY
  non-Remotion step (transcript can't be produced in Remotion); audio sync analysis is data-gathering, not editing.
- **HyperFrames is allowed as a b-roll asset factory** (2026-07-09). Author an overlay in HTML, bake it with
  `npx hyperframes render <dir> --format=webm` (transparent), then composite it in Remotion via
  `<OffthreadVideo transparent />`. HyperFrames must NEVER own the final render of an ad — that would
  re-implement the cut. Prefer a Remotion component for anything parameterized per-ad or needing frame-exact
  retiming; reach for HyperFrames for one-off set-pieces. Its skills live in `~/.claude/skills/hyperframes*`.
- **Time cap: keep each ad under 1h, hard ceiling 1h15.** Don't open-endedly rework — pick a good take and move on.
- **Mic-quality check (mandatory):** after building, ffprobe the final audio and confirm it is NOT degraded
  (must match the source mic's sample-rate/channels, e.g. 48 kHz — never the 16 kHz mono transcription copy).
- **Side angle is never zoomed** — it stays at natural size (only the front camera gets the steady zoom + punch).
  Side clips are `muted` (their mic must not echo over the main track).
- The standard look is fixed: 1.1x speed + slow steady continuous zoom (front only) + captions (white, orange keyword).
- You make the take/cut **and angle-switch** calls automatically; the user only reviews the result and approves b-rolls.
- **Always ask the user for the b-roll asset folder** at the b-roll gate (step 6a). Never guess it, never
  reuse a previous ad's folder, never invent social proof that isn't in that folder.
- **Screenshot b-rolls use the centered magnifier** (step 7b) — `centerY=1132`, ~1000px wide, lens sweeping
  the spoken sentence. Legibility beats composition; if the text can't be read, the b-roll has failed.
- **Spoken word/number effects** (step 5b, `SpokenFX.tsx`) are small pop-ups synced to special spoken words —
  placed by you during the silent build (not gated), good fonts only, never over his face, never billboard-sized.
- **SFX are optional, sparse, and quiet** — propose them at the b-roll gate (step 6d), never auto-place.
- Build silently — no messages to the user until the last pre-broll step (the rendered cut) is finished.
