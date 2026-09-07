---
description: Audit the study's coverage — read the known gaps, cross-check them against scope, and report what is genuinely thin.
argument-hint: "[optional: a specific area to focus on]"
---

Audit this study's coverage and report what is genuinely thin.
$ARGUMENTS

## How to run it

1. **Read `study/ai_instructions/scope.md` first.** Every judgment below
   depends on it. If it still carries the `<!-- placeholder -->` marker,
   stop: no coverage claim means anything without a real scope
   statement, and filling it in with the user is the actual task.

2. **Read `study/topics/gaps.md`.** It has two halves with different
   trust levels: the auto-aggregated block is mirrored from each
   dossier's `## Open questions` section and is only as fresh as the last
   `python scripts/build_gaps_index.py` run — re-run it before trusting
   the block. The "Flagged directly" section is hand-written and may
   contain items a dossier has since covered.

3. **Cross-check each gap against scope.** For every entry, decide:
   - **Genuine gap** — inside scope, thin or absent in the collection.
   - **Expected absence** — outside scope. Say so and propose removing
     it. This is the judgment the whole gap-flagging design exists to
     make, and a gaps file full of out-of-scope entries is worse than an
     empty one, because it makes the real gaps unfindable.
   - **Already closed** — a document added since the entry was written
     covers it. Verify against `study/catalog-index.md` rather than
     assuming, and propose moving or deleting it.

4. **Look for gaps nobody logged.** Compare `scope.md`'s in-scope list
   against what the catalog actually covers — read
   `study/catalog-index.md` in full, that is what it is for. An in-scope
   area with no entries at all is the most important kind of gap and the
   least likely to be already written down, because nothing ever
   prompted anyone to notice it.

5. **Report, ranked by consequence.** For each genuine gap: what is
   missing, what currently rests on it (a dossier recommendation, a
   `decisions.md` entry), and a concrete acquisition direction — a
   search term, a venue, a citation trail in
   `study/reference-index.md`. Check
   `project_documents/source-access.md` so each suggestion points
   somewhere real rather than trailing off.

6. **Ask the user directly** whether they can source material for the
   top gaps, rather than silently working around the hole. Update
   `study/topics/gaps.md`'s "Flagged directly" section with anything new
   you found — do not hand-edit the auto-aggregated block.
