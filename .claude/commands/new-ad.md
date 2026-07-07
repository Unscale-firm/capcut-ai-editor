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

6. **B-rolls = the ONLY approval gate.** Angle switches are NOT gated anymore — you place them yourself
   (same as the take/cut calls). Build the entire ad **silently** (cut → switches → captions → transition
   look → render) and do NOT message the user at all until this last pre-broll step is done. Only then
   surface. If the user wants a switch changed, they will tell you BEFORE the b-roll review.
   Then b-rolls one at a time: build → show a preview frame → wait for the user's **yes / no / pick** →
   only then place. NEVER auto-place a b-roll. (See the broll-approval-first memory.)

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

## Rules
- No CapCut, ever. **Remotion only** for all visual editing/compositing — no ffmpeg-baked video (base cut,
  side framing, effects all done natively in Remotion via Sequences/OffthreadVideo). Whisper is the ONLY
  non-Remotion step (transcript can't be produced in Remotion); audio sync analysis is data-gathering, not editing.
- **Time cap: keep each ad under 1h, hard ceiling 1h15.** Don't open-endedly rework — pick a good take and move on.
- **Mic-quality check (mandatory):** after building, ffprobe the final audio and confirm it is NOT degraded
  (must match the source mic's sample-rate/channels, e.g. 48 kHz — never the 16 kHz mono transcription copy).
- **Side angle is never zoomed** — it stays at natural size (only the front camera gets the steady zoom + punch).
  Side clips are `muted` (their mic must not echo over the main track).
- The standard look is fixed: 1.1x speed + slow steady continuous zoom (front only) + captions (white, orange keyword).
- You make the take/cut **and angle-switch** calls automatically; the user only reviews the result and approves b-rolls.
- Build silently — no messages to the user until the last pre-broll step (the rendered cut) is finished.
