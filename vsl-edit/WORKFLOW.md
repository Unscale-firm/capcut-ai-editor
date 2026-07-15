# WORKFLOW — Comment on travaille ensemble / How we work together
*(Français d'abord, English below. Les statuts LIVE / STAGED / REVISED restent en anglais partout.)*

---

## 🇫🇷 Comment on va travailler ensemble sur la VSL

Tout ce qui concerne le montage de la VSL vit dans ce dossier **`vsl-edit/`** — c'est la seule source de vérité. Ton Claude capte les règles automatiquement (`vsl-edit/CLAUDE.md`), mais voici le système :

1. **Commence chaque session par `git pull`** (ou dis à Claude « pull la dernière version et vérifie l'état du montage VSL »).
2. **`CHANGELOG.md` est ton tableau de bord.** Le tableau de statuts indique quels incréments sont **LIVE** (approuvés — monte-les) et lesquels sont **STAGED** (en relecture — n'y touche pas). Toute correction sur un incrément déjà LIVE apparaît comme ligne explicite type `REVISED 2.4` — rien ne change jamais en silence.
3. **`73_VSL_Edit_Map.md` est la feuille de montage** — instructions par tranches de 2 minutes, timecodées sur ton `vsl-captioned.mp4`. Chaque section donne : angle caméra, effet, text pops exacts (toujours les mots exacts d'Amine, ~5 mots max), et quel asset va où et quand.
4. **`B-roll assets/` contient tous les inserts** — clips de réaction, logos, images, captures — organisés par incrément, avec un README donnant les notes de découpe par clip (ex. « utiliser 0–7s uniquement »). De nouveaux b-rolls arrivent à chaque push d'incrément.
5. **Questions, blocages, liens de rendu :** ajoute-les dans `QUESTIONS.md` (crée-le s'il n'existe pas), commit, push. Le côté Unscale pull et répond dans le même fichier. Jamais de vidéo rendue dans git — uniquement des liens.
6. **Règle importante :** tous les timecodes sont calés sur `vsl-captioned.mp4` tel quel (18:20, 1.15x). Si tu recoupes ou re-times la vidéo de base, signale-le dans QUESTIONS.md **avant** de monter — sinon chaque timecode pointera sur le mauvais moment.

**Le flux :** Amine push un incrément → tu pull, tu montes, tu push tes questions / lien de rendu → il review, répond, et push l'incrément suivant.

---

## 🇬🇧 How we'll work together on the VSL

Everything for the VSL edit lives in this **`vsl-edit/`** folder — the single source of truth. Your Claude picks the rules up automatically (`vsl-edit/CLAUDE.md`), but here's the system:

1. **Start every session with `git pull`** (or tell Claude "pull latest and check the VSL edit state").
2. **`CHANGELOG.md` is your dashboard.** The status table says which increments are **LIVE** (approved — cut them) and which are **STAGED** (under review — don't touch). Any correction to a LIVE increment appears as an explicit `REVISED 2.4`-style line — nothing ever changes silently.
3. **`73_VSL_Edit_Map.md` is the edit map** — instructions in 2-minute increments, timestamped to your `vsl-captioned.mp4`. Each section gives: camera angle, effect, exact text pops (always Amine's exact spoken words, ~5 words max), and which asset goes where and when.
4. **`B-roll assets/` holds every insert** — reaction clips, logos, stills, captures — organized per increment, with a README carrying per-clip trim notes (e.g. "use 0–7s only"). New b-roll arrives with each increment push.
5. **Questions, blockers, render links:** add them to `QUESTIONS.md` (create if absent), commit, push. The Unscale side pulls and answers in the same file. Never commit rendered video — links only.
6. **One important rule:** all timestamps are pinned to `vsl-captioned.mp4` as-is (18:20, 1.15x). If you re-cut or re-time the base video, flag it in QUESTIONS.md **before** cutting — otherwise every timestamp points at the wrong moment.

**The flow:** Amine pushes an increment → you pull, cut it, push questions / render link → he reviews, answers, and pushes the next increment.
