---
description: Show where the study stands as a picture in chat: the gates, what is next, intake coverage, the catalog by method family, the articles.
---

A read-only status view. A script draws it, so it costs a few tokens and cannot disagree with the
files. It never opens or closes a gate and never edits an article.

1. Run `python study/scripts/status.py --write`. It rewrites `STATUS.svg` and `STATUS.md` at the
   repo root (both git-ignored, so they never show up in a commit).
2. Send the picture: `SendUserFile` with `files: ["STATUS.svg"]` and `display: "render"`. Where
   files cannot be sent (a plain terminal), run `python study/scripts/status.py --md` and show its
   text instead.
3. Say in three lines at most what the picture does not: the next step in plain words, and
   anything it flags (a gate open for a long time, the volume nudge, `scope.md` behind the
   definition, intake questions still `unknown`). Do not describe what the picture already shows.

To answer a question about one number, read the snapshot (`python study/scripts/status.py`, JSON)
instead of drawing again.

**Why a script and not a drawing by Claude:** an inline drawing means writing the whole graphic
on every call. The script writes it once from the same facts the validator and the gates use, and
the picture looks the same every time you ask.
