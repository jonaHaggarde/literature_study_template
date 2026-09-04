# Workflow

How to actually operate in this repo, once `scope.md` is real (see
`README.md` in this folder if it isn't yet).

## Processing new PDFs

1. User drops PDFs into `PDFs/` (subfolders are fine, the script
   recurses).
2. Run `python scripts/convert.py` from `study/`. It hashes every PDF,
   skips anything already converted and unchanged, and for everything
   new/changed writes a `.md` file into `notes/` (mirroring the `PDFs/`
   path) and appends a stub entry to `catalog.md`.
3. For every new stub: do a full, non-lazy read of the note — not just
   enough to write an abstract. Fill in:
   - `catalog.md`'s stub fields (`authors`, `year`, `type`, `approach`,
     `contribution`, `compares` if applicable, `tags`, `abstract`) — see
     `catalog-schema.md` for allowed values.
   - The note's own `## Key Findings` (3-6 sentences: method, key claims,
     results) and `## Implementation Notes` (tuning parameters/settings
     actually used, data/sample requirements, failure modes or
     limitations the authors themselves flag, released
     code/data/materials — omit sub-bullets that don't apply rather than
     forcing empty headers).
   - **Check the new document against `ai_instructions/scope.md` while
     reading it.** If it's a head-to-head comparison or a survey with an
     explicit ranking, set `contribution: comparison-study` (or add
     `compares` to a `survey` entry). You don't need to hand-edit
     catalog.md's "Comparison & survey papers (quick reference)" section
     — `validate_repo.py --fix` (step 5) regenerates it from the
     `compares` fields directly.
   - Title/authors/year in the stub are pre-filled from the PDF's own
     metadata by `convert.py` where available — often wrong or stale
     (especially authors), so verify against the actual text rather than
     trusting it, and correct it in `catalog.md` if it's off.
4. Rerun `python scripts/build_reference_index.py` so the new document's
   own citations become searchable leads for finding the *next* document
   — see `reference-index.md`'s own header for how to use it.
5. Run `python scripts/validate_repo.py --fix` after every *batch* (not
   per-PDF — batch-level is the right granularity). `--fix` mechanically
   corrects tag casing and regenerates the comparison quick-reference
   list; the checks themselves cover catalog/notes/manifest sync, no
   stray TODOs left in a note the catalog claims is processed, dossiers
   have their required Open-questions section, likely-duplicate entries
   by fuzzy title match, and reference-index.md freshness. None of this
   verifies factual accuracy. For that, spend two minutes running 2-3
   real discovery queries (see below) against the freshly-updated catalog
   and sanity-check the results by eye.
6. If a PDF is a scan and comes out with a `LOW TEXT YIELD` warning, OCR
   it first (`ocrmypdf`) and re-run `convert.py`.

## Answering literature questions

`catalog.md` is the cheap default and should answer most queries on its
own — read it in full, it's kept deliberately compact per entry so this
stays cheap even at 100+ documents. `notes/` is expensive by comparison
(one near-full-text conversion per PDF) — only open a specific note when
verifying a claim against the primary source, never read the folder in
bulk. `reference-index.md` is bigger still and reserved for the two query
types below — even then, grep it, never a full read.

Every claim should cite the note file and page marker
(`<!-- page: N -->`) so the source PDF can be opened at the right spot.

### "Which method/finding should I trust?" queries

1. Check catalog.md's **Comparison & survey papers** quick-reference list
   first, and grep entries' `compares` field for the relevant terms.
2. Check whether a relevant `topics/` dossier already exists; if so,
   answer from it and only go back to notes/PDFs to fill gaps.
3. If no dossier exists, or the existing one predates documents now in
   the catalog, build/update one — a comparison table plus a short prose
   recommendation with tradeoffs, not just a list of abstracts.

### "What are my options for X?" queries

Different, earlier question than the above — the user doesn't have
candidates in mind yet.

1. Search *all* candidates tagged with the relevant domain (using
   `topics/vocabulary.md`'s canonical terms), not just ones whose
   `contribution` is `comparison-study`/`survey` — a document whose main
   contribution is proposing one method still tells you that method
   exists as an option.
2. Also grep `reference-index.md` rather than opening each relevant note
   to scan its bibliography by hand. Report matches as unverified leads,
   clearly marked as "mentioned but not covered here in depth."
3. Present the result as a menu: name, one line on what distinguishes it,
   whether it's covered by a note here or only a lead from
   `reference-index.md`.
4. A non-trivial menu that's likely to recur is a signal to build a
   `topics/` comparison dossier next.

### Finding a new source on a specific/narrow topic

`grep -i` the relevant terms in `reference-index.md` before saying no
such source is known — something already cited by a document in this
catalog may be exactly it. Report matches as unverified leads
(title/authors/venue/year only, never read) — this repo has no way to
fetch or download sources itself.

## Gap-flagging

This is the workflow this template exists to support: know when an
answer rests on solid coverage vs. when the collection is thin or silent
on something that's actually in scope.

1. **Every `topics/*.md` dossier ends with an "## Open questions"
   section** — what hasn't been compared yet, what's only
   qualitative/single-source rather than a real head-to-head. After
   adding or updating a dossier, run
   `python scripts/build_gaps_index.py` to regenerate the auto-aggregated
   part of `topics/gaps.md` — this is mechanical, don't hand-copy it.
2. **When asked what's missing** ("what should I look into next," "what
   haven't we covered"), check `topics/gaps.md` first and suggest
   concrete acquisition directions — not just "I'm not sure."
3. **When a new document, or a conversation, surfaces a sub-topic that's
   in scope (check `ai_instructions/scope.md`) but thin or absent in the
   catalog**, say so and log it in `topics/gaps.md` — don't wait to be
   asked. This is the core judgment call: something *out* of scope being
   uncovered is not a gap, it's expected — don't flag it as one.
4. When a real gap is identified, ask the user directly whether they can
   source more material in that area, rather than silently working around
   the hole.

## Decisions grounded in the literature

If this study feeds real decisions or conclusions (not just a reference
catalog), use `../decisions.md` — see that file's own header for the
template and the literature-basis/project-context split, and
`../ideation/README.md` for how unverified brainstorming is kept
separate from both.
