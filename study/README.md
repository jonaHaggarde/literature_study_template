# study/

The literature-review engine: drop PDFs in, let Claude build a
searchable, citation-grounded catalog of them, and track its own coverage
gaps against a scope you define. This file covers setup and day-to-day
mechanics; see `workflow-diagram.md` for a graphical walkthrough.

**This folder is deliberately self-contained.** Everything here is the
engine — nothing project-specific lives in it except
`ai_instructions/scope.md`. Project content (decisions, brainstorming,
background explainers, meeting notes, the schedule, provided material)
lives at the repo root, one level up. The root `README.md` explains why,
and the root `CLAUDE.md` carries the repo-wide conventions. Keeping the
split clean is also what makes it possible to pull a newer version of
this engine into an existing project later.

## Folder structure

```
study/
  README.md               <- this file
  CLAUDE.md                <- auto-loaded by Claude Code, points straight at ai_instructions/
  workflow-diagram.md       <- graphical overview of the whole process (Mermaid)
  leads.md                    <- documents heard of but not yet read, with their state (acquisition is its own step)
  catalog-index.md           <- one line per document, generated. Read this FIRST, in full.
  catalog.md                  <- the full per-entry record. Grep it; don't read it whole.
  reference-index.md           <- every processed document's own references, deduplicated — grep for new leads
  manifest.json                 <- tracks which PDFs have been converted (hash-based)
  scripts/
    setup.ps1 / setup.sh        <- one-time environment setup
    convert.py                   <- converts PDFs/ -> notes/, updates catalog.md, skips unchanged files
    build_reference_index.py      <- rebuilds reference-index.md from notes/
    build_catalog_index.py         <- rebuilds catalog-index.md from catalog.md
    build_gaps_index.py             <- rebuilds topics/gaps.md's auto-aggregated sections from dossiers and decision trees
    build_review_table.py           <- rebuilds ../articles/review/sections/comparison_rows.tex from the notes' method cards
    build_decision_trees.py           <- regenerates the mermaid diagram under each decision-tree table in ../ideation/
    method_cards.py                   <- shared helpers for method cards (imported, not run)
    ocr_support.py                     <- OCR tool discovery and OCR of scans (run it alone to see what is missing)
    vision_pages.py                    <- the budgeted way to read page images: plan, approve, ticket, record
    verification.py                    <- records and reports which method cards the row-verifier has checked
    merge_worker_report.py           <- merges a note-extractor worker's report into catalog.md and the notes
    convert_intake.py                <- converts the PDFs in ../intake/ to markdown next to them
    intake_check.py                  <- checks ../intake/intake.md: IDs, supersedes, coverage per section, uncited rows
    scope_sync.py                    <- keeps scope.md in step with the accepted definition (check, stamp)
    new_article.py                   <- creates an article from a template in ../articles/_templates/
    article_version.py               <- the version history of one article (draft, edit, refine, review, accept)
    gate.py                          <- the gates: status, open, briefing, understand, close, skip, refreeze
    build_articles.py                <- builds every article to a PDF
    build_bibliography.py            <- writes each article's references from what it cites
    build_article_parts.py           <- the generated parts: map coverage, requirements traceability, decision tree
    tree_latex.py                    <- the decision tree as TikZ (imported, not run)
    style_check.py                   <- advisory style check of an article
    status.py, status_svg.py         <- the status snapshot and its picture (/where)
    texutil.py, _console.py          <- shared helpers (imported, not run)
    tests/                           <- unit tests: python -m unittest discover -s scripts/tests
    validate_repo.py                 <- structural health check + --fix, rerun after every batch
    requirements.txt
  templates/
    note_template.md          <- reference only, shows the format convert.py generates
  ai_instructions/            <- read this first in every session — see ai_instructions/README.md
    README.md
    scope.md                   <- what this study is about — fill in before real work starts
    catalog-schema.md            <- catalog.md field definitions, the summary rule, allowed values
    workflow.md                   <- the operational playbook
    delegation.md                  <- which work to hand to a subagent, and which tier
    batch-orchestration.md          <- parallel workers on a real backlog
    long-running-sessions.md         <- overnight / multi-session autonomous runs
    mcp.md                            <- when an MCP server helps, and what it may not be trusted with
  PDFs/                          <- your source PDFs (NOT committed to git, see below)
  notes/                          <- one .md per PDF, generated by convert.py
  topics/                          <- synthesis dossiers, the tag vocabulary, and the gaps list
```

Four derived files are regenerated by script and **never hand-edited**:
`catalog-index.md`, `reference-index.md`, `topics/gaps.md`'s
auto-aggregated block, and `catalog.md`'s comparison quick-reference
list. `validate_repo.py` checks that each is fresh. This is the
convention that has held up best here: every convention a script
enforces survived contact with a real corpus, and every one a human
maintained drifted.

## One-time setup

Claude runs this itself on the first session, so you normally never do. By hand:

```powershell
cd study
.\scripts\setup.ps1        # or ./scripts/setup.sh on macOS/Linux
```

Creates `.venv/` and installs dependencies. Activate it afterward with
`.venv\Scripts\Activate.ps1` (`source .venv/bin/activate` on macOS/Linux).

## Getting started

1. Drop material handed down from outside the project (a brief,
   a proposal, a specification) into `../intake/received/`.
2. **Start Claude Code with this folder (`study/`) as its working
   directory** — `cd` here first, then launch it, so `CLAUDE.md` in this
   folder loads automatically as its memory file and points straight at
   `ai_instructions/README.md`. Starting from the repo root works too and
   is the better choice when the session will touch project content as
   well; the root `CLAUDE.md` routes literature work back here. Then just
   say you're ready to start. Claude's first job is helping you fill in
   `ai_instructions/scope.md` — everything downstream (gap-flagging in
   particular) depends on that being real.
3. Drop PDFs into `PDFs/` and work through "Adding PDFs" below.

## Adding PDFs

`/process-batch` runs this whole loop, including parallel workers for a
real backlog. By hand:

1. Drop new PDFs anywhere under `PDFs/` (subfolders are fine, the script
   recurses).
2. Run:
   ```powershell
   python scripts\convert.py
   ```
   Before a big pile, triage first: `python scripts\convert.py --dry-run`
   lists what would convert (with page counts) and converts nothing, and a
   PDF you do not want processed yet goes in `PDFs/_deferred/`, where it is
   ignored until you move it back. A PDF that is byte-identical to one
   already converted is skipped and reported, whatever its filename.
   `--only TEXT` converts only matching paths. Each file is extracted with a
   time limit (`--timeout`, default 300 s): on a hang the file is re-read as
   plain text and the note says so, since tables and structure are lost.
   The manifest and catalog stub are saved after every file.

   The script hashes every PDF, skips anything already converted and unchanged,
   and for everything new/changed writes a `.md` file into `notes/`
   (mirroring the `PDFs/` path) and appends a stub entry to `catalog.md`.
3. Ask Claude to fill in the TODO fields (summary, tags, type,
   contribution, key findings, implementation notes) for the new
   entries — see `ai_instructions/workflow.md` for exactly what's
   expected, and `ai_instructions/catalog-schema.md` for the summary
   rule and the three-to-five tag ceiling. This should be a full,
   non-lazy read of each document, not just enough to write a summary.
   (Title/authors/year are pre-filled from the PDF's own metadata where
   available — often wrong or stale, so verify rather than trust it.)
4. Rebuild the two indexes:
   ```powershell
   python scripts\build_reference_index.py
   python scripts\build_catalog_index.py
   ```
   The first makes each new document's own citations searchable as leads
   for finding the *next* one; the second regenerates the one-line-per-
   document index that every session reads in full.
5. Run the repo health check after every batch (not per-PDF):
   ```powershell
   python scripts\validate_repo.py --fix
   ```
   `--fix` mechanically corrects tag casing and regenerates the
   Comparison & survey papers quick-reference list — neither ever needs
   hand-editing. The checks themselves cover catalog/notes/manifest sync,
   stray TODOs, schema conformance, likely-duplicate entries by fuzzy
   title match, non-canonical tags, dossiers having their Open-questions
   section, balanced mermaid fences, and whether the two indexes are
   stale. Fails (exit code 1) only on real problems. This catches sync
   bugs, not factual accuracy — for that, spend two minutes running 2-3
   real discovery queries against the freshly-updated catalog and
   sanity-check the results by eye.
6. If any `topics/*.md` dossiers were added or updated, run
   ```powershell
   python scripts\build_gaps_index.py
   ```
   to regenerate the auto-aggregated part of `topics/gaps.md` from their
   Open-questions sections.
7. **Scans.** A PDF with no extractable text is OCR'd automatically when
   `ocrmypdf` and Tesseract are installed. `python scripts\ocr_support.py` shows
   what is missing and the commands to install it (nothing is installed for you;
   the scripts also look in the default install folders, so a Tesseract that is
   not on PATH still works). OCR runs on a copy and never changes the PDF. A scan
   converted earlier without OCR is fixed in place, keeping everything already
   written in its note, with `python scripts\convert.py --reocr`.
   OCR text is marked `(ocr)` per page. It is good on prose and bad on equations,
   symbols and tables, so the note lists the equation-heavy pages, and a method
   card that rests on one carries `read_from: ocr` and is not counted as verified.
   Reading such pages from their images is possible but costs tokens, so it is
   rationed: `/vision-read`, under the limits in
   `ai_instructions/vision-budget.md`, one small ticket at a time, with your
   approval.

## How Claude should use this repo

See `ai_instructions/README.md` — that folder is the actual operating
manual (scope-checking, the catalog schema, the query playbook, how
gap-flagging works, and which work to delegate to which tier of
subagent). This README only covers human-facing setup. For a graphical
overview, see `workflow-diagram.md`.

Three agent definitions and three slash commands ship with the template,
in `../.claude/`: `corpus-scout`, `note-extractor`, and
`dossier-synthesist`, driven by `/lit`, `/process-batch`, and
`/gap-check`. `ai_instructions/delegation.md` explains what each is for
and why the model tiers sit where they do.

## Copyright note

**Keep this repo private if your sources are copyrighted.** `PDFs/` is
gitignored (large binaries, and you likely don't want to distribute
copyrighted material), but `notes/` contains substantial extracted text
from those same sources, and `notes/` *is* committed. That's fine for a
private study; it is not fine to make public. Double-check the repo's
visibility before pushing if `notes/` might contain copyrighted extracted
text. `convert.py` repeats this warning every time it converts something,
because it is the highest-consequence mistake available in this template.
