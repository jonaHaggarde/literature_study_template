# Workflow

How to actually operate in this repo, once `scope.md` is real (see
`README.md` in this folder if it isn't yet).

## Processing new PDFs

For a large backlog processed in parallel via subagents (especially an
unattended/overnight run), see `batch-orchestration.md` first — it
covers worker scoping and a real, documented rogue-agent failure mode
this template's design specifically guards against, and
`delegation.md` for which tier each part of the work belongs to. The
`/process-batch` command runs this whole loop. The steps below are
per-document and apply whether run serially or inside a worker.

1. User drops PDFs into `PDFs/` (subfolders are fine, the script
   recurses).
2. Run `python scripts/convert.py` from `study/`. It hashes every PDF,
   skips anything already converted and unchanged, and for everything
   new/changed writes a `.md` file into `notes/` (mirroring the `PDFs/`
   path) and appends a stub entry to `catalog.md`.
3. For every new stub: do a full, non-lazy read of the note — not just
   enough to write a summary. Fill in:
   - `catalog.md`'s stub fields (`authors`, `year`, `type`, `approach`,
     `contribution`, `compares` if applicable, `tags`, `summary`) — see
     `catalog-schema.md` for allowed values, the summary rule, and the
     three-to-five tag ceiling. A field that doesn't apply is left
     **empty**, never `n/a`.
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
     — `validate_repo.py --fix` (step 6) regenerates it from the
     `compares` fields directly.
   - Title/authors/year in the stub are pre-filled from the PDF's own
     metadata by `convert.py` where available — often wrong or stale
     (especially authors), so verify against the actual text rather than
     trusting it, and correct it in `catalog.md` if it's off.
4. **Ratify the collection-derived fields.** If a subagent did the
   extraction, this step is not optional and not a formality — it is the
   one place where a self-contained worker structurally cannot be right,
   because these three outputs depend on the state of the collection
   rather than on the document:
   - **`tags`** — three to five, canonical spelling, describing what the
     document *contributes* rather than what it *mentions*. Over-tagging
     is the normal failure mode. Reconcile conflicts between workers
     here, and add a genuinely new canonical tag to
     `../topics/vocabulary.md` when one is warranted.
   - **The scope verdict** — a worker reasons about the document; the
     catalog records the document's relationship to *this study*. A
     document acquired deliberately to fill a known gap can read as out
     of scope from the inside.
   - **Any gap flag** — checked against `scope.md` before it is logged.

   The same applies to the `summary`'s fourth clause: when a document was
   acquired for a specific gap or sits partly outside scope, the summary
   has to say so and say how far it actually gets. Only whoever knows why
   the document was acquired can write that. `delegation.md` has the
   measurement this rule came out of.
5. Rerun `python scripts/build_reference_index.py` so the new document's
   own citations become searchable leads for finding the *next* document
   — see `reference-index.md`'s own header for how to use it. Then
   `python scripts/build_catalog_index.py` to regenerate
   `catalog-index.md` from the entries you just filled in.
6. Run `python scripts/validate_repo.py --fix` after every *batch* (not
   per-PDF — batch-level is the right granularity). `--fix` mechanically
   corrects tag casing and regenerates the comparison quick-reference
   list; the checks themselves cover catalog/notes/manifest sync, no
   stray TODOs left in a note the catalog claims is processed, dossiers
   have their required Open-questions section, likely-duplicate entries
   by fuzzy title match, non-canonical tags, balanced mermaid fences, and
   whether `reference-index.md` and `catalog-index.md` are stale. None of
   this verifies factual accuracy. For that, spend two minutes running
   2-3 real discovery queries (see below) against the freshly-updated
   catalog and sanity-check the results by eye.
7. If a PDF is a scan and comes out with a `LOW TEXT YIELD` warning, OCR
   it first (`ocrmypdf`) and re-run `convert.py`.

## Answering literature questions

The read order, cheapest first — and the cost differences between these
are large enough that the order matters more than any single technique:

1. **`catalog-index.md`** — one line per document. **Read this in full.**
   It is the cheap default and answers most questions on its own.
2. **`catalog.md`** — the full per-entry record. **Do not read it in
   full**, at any corpus size. Grep it and read the single
   `<!-- entry:ID -->` … `<!-- /entry -->` block you need.
3. **`topics/*.md`** — a dossier, if one exists for the topic. Cheap
   relative to what it replaces, since the synthesis is already done.
4. **`notes/`** — expensive (one near-full-text conversion per PDF).
   Open a specific note to verify a claim against the primary source;
   never read the folder in bulk.
5. **`reference-index.md`** — bigger still, and reserved for the two
   query types below. **Grep it, never read it in full**, at any size.
   This rule has held up at three-quarters of a megabyte and is the model
   the rest of this file follows.

When a search would pull a lot of text into the conversation, delegate it
to a `corpus-scout` instead of reading inline — the point is that its
inputs never enter this session's context. See `delegation.md`;
`/lit` runs that path directly.

Every claim should cite the note file and page marker
(`<!-- page: N -->`) so the source PDF can be opened at the right spot.

### "Which method/finding should I trust?" queries

1. Check catalog.md's **Comparison & survey papers** quick-reference list
   first, and grep entries' `compares` field for the relevant terms.
2. Check whether a relevant `topics/` dossier already exists; if so,
   answer from it and only go back to notes/PDFs to fill gaps.
3. If no dossier exists, or the existing one predates documents now in
   the catalog, build/update one — a comparison table plus a short prose
   recommendation with tradeoffs, not just a list of summaries, and a
   diagram of the method families before the table. This is
   synthesist-tier work (`delegation.md`); the `dossier-synthesist` agent
   drafts it and this session reviews and saves it.

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
(title/authors/venue/year only, never read).

This repo cannot fetch or download sources on its own. Two ways forward,
in order:

- If a **source-acquisition MCP server** is attached to the session (a
  bibliographic-metadata service, a preprint repository, a reference
  manager), use it to resolve the lead into real metadata, an abstract,
  and either an open-access link or a DOI plus a paywall verdict. See
  `mcp.md` — including the rule that anything it returns stays an
  unverified lead until the document itself is converted and read.
- Otherwise, use `../../project_documents/source-access.md` to point the
  user at where they might actually get the document (institutional
  access, open access, or a discovery tool to locate it first) instead of
  leaving "go find this" with nowhere to go.

## Gap-flagging

This is the workflow this template exists to support: know when an
answer rests on solid coverage vs. when the collection is thin or silent
on something that's actually in scope. `/gap-check` runs this as an
audit.

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
   the hole — check `../../project_documents/source-access.md` first so
   the suggestion points at somewhere real to look.

## Decisions grounded in the literature

Decisions live *outside* `study/`, at the repo root, because they are
project content rather than part of the literature-review engine. If this
study feeds real decisions or conclusions (not just a reference catalog),
use `../../decisions.md` — see that file's own header for the template
and the literature-basis / project-context split, and
`../../ideation/README.md` for how unverified brainstorming is kept
separate from both.

Anything written outside `study/` follows the repo-wide citation
convention — numbered `[1]`, `[2]` markers plus a `## References`
section, numbering local to each file. See the root `CLAUDE.md`.
