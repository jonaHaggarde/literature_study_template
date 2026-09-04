# Topic dossiers

Don't pre-build these for every tag. Build one here the first time a
query actually needs to cross-reference a dense cluster of documents
against each other. A dossier is a real synthesis, not a list: which
sources agree, which contradict each other, which approach each uses,
open questions across the set.

Once it exists, it becomes a standing asset — the next query about that
topic reads the dossier instead of re-deriving the comparison from raw
notes. Update it when new relevant PDFs are added.

Suggested filename: `topics/<topic-tag>.md`.

Two other files in this directory support every dossier:

- `topics/vocabulary.md` — canonical tag names. Check before tagging a
  new document or inventing a term for a dossier's comparison table.
- `topics/gaps.md` — a running aggregation of every dossier's "Open
  questions" section, cross-referenced against
  `ai_instructions/scope.md`. **Every dossier must end with its own
  "Open questions" section** — what hasn't been compared yet, what
  claims are only qualitative/single-source rather than a real
  head-to-head. After adding or updating a dossier, run
  `python scripts/build_gaps_index.py` to regenerate the auto-aggregated
  part of `topics/gaps.md` — don't hand-copy the section, the script does
  it deterministically.
