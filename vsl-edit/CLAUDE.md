# vsl-edit/ — Unscale VSL edit handoff (instructions + b-roll)

This folder is the single source of truth for editing the Unscale partner-program VSL.
It is maintained by the Unscale side (Amine + his Claude); the editor pulls, cuts
(SmartCut/CapCut lives in the rest of this repo), and reports back.

## Session start — ALWAYS
1. `git pull` before anything else.
2. Read `CHANGELOG.md` — it says which increments are LIVE (approved for editing) and
   what changed since the last pull. **Only cut increments marked LIVE.** Increments
   present in the map but not LIVE are staged drafts and may still change.
3. The master instruction file is `73_VSL_Edit_Map.md`. Read its GLOBAL SPEC section
   once per session — brand palette, camera rules, text-pop rules, caption-correction
   table, compliance notes. Those rules override anything else.

## Files
- `73_VSL_Edit_Map.md` — THE edit map, built in 2-minute increments. Timestamps match
  the final video (`vsl-captioned.mp4`, 18:20, 1.15x).
- `VSL_final_script_timestamps.pdf` — verbatim transcript with timestamps and [SIDE]
  camera tags. NOTE: image-based PDF (no text layer) — render pages to images to read it.
- `B-roll assets/` — every insert clip, logo, and still, organized per increment.
  `B-roll assets/README.md` has per-clip trim notes. Client tiles run CLEAN: no music
  over them, no captions burned onto the tile.
- `CHANGELOG.md` — push log + LIVE status per increment. Append-only.

## What is NOT in this folder
- The source video `vsl-captioned.mp4` and raw camera footage — the EDITOR owns these
  (they produced the captioned cut). The Unscale side supplies only instructions,
  feedback, and b-roll (clips, reactions, images) through this folder.
  ⚠️ Timestamps in the map are pinned to vsl-captioned.mp4 at 18:20 / 1.15x — if the
  editor ever re-cuts or re-times the base video, flag it in QUESTIONS.md BEFORE
  cutting, because every timestamp in the map shifts.
- Anything else about the business. If an instruction references a file that isn't
  here (e.g. E3.25 substantiation, proof originals), that's an Unscale-side item —
  flag it, don't hunt for it.

## Ground rules for the edit
- Never paraphrase Amine in on-screen text — text pops quote his exact words, ~5 words max.
- Apply the caption-correction table in the map to ALL captions (Amine, Cara Delevingne,
  Spiralyze, Scismic, Unscale, Meta, Rayan…).
- Approved increments are append-only: if a correction to an already-LIVE increment is
  needed, it appears in CHANGELOG.md as an explicit `REVISED <section>` line. Never
  assume a silent change.
- Dignity-gated beats (the father passage, Rayan) — follow the map exactly: where it
  says "nothing on screen," put nothing on screen. No stock footage anywhere in this video.

## Reporting back
- Questions/blockers: append them to `QUESTIONS.md` in this folder (create if absent),
  commit, and `git push`. The Unscale side pulls and answers in the same file.
- Do NOT commit rendered video (exports, proxies, project caches) — share render links
  in `QUESTIONS.md` instead. The repo .gitignore whitelists ONLY the b-roll in this
  folder; everything else media-shaped stays ignored.
