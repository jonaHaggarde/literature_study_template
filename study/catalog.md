# Catalog

Master index of every document in this study. Read this file in full
before opening anything in `notes/` — it's kept deliberately short per
entry so it stays cheap to read completely even with 100+ documents.

Each entry is a fixed block of fields (grep-friendly, one `key: value`
per line) between an `<!-- entry:ID -->` / `<!-- /entry -->` comment
pair. `scripts/convert.py` appends a stub block for every newly-converted
PDF; fill in the rest afterward — see `ai_instructions/workflow.md`.

Field definitions and allowed values: `ai_instructions/catalog-schema.md`.
Tag vocabulary: `topics/vocabulary.md`.

---

## Comparison & survey papers (quick reference)

Entries with a populated `compares` field, i.e. the ones most useful for
deciding between methods/findings. Keep this list in sync when adding
entries with `contribution: comparison-study` or a `compares`-bearing
`survey`.

<!-- - **Title** — what's compared and on what basis -->

---

Example entry format (not a real document — copy this block below the
line, replace the ID and fields; `scripts/validate_repo.py` skips an
entry literally named `EXAMPLE` so this reference block doesn't trip
validation, but don't leave a *real* entry using that ID):

```
<!-- entry:EXAMPLE -->
title: Example Title
authors: A. Author, B. Author
year: 2026
type: paper
approach: example method
contribution: experimental-validation
compares:
tags: example-tag
note: notes/example.md
source: PDFs/example.pdf
abstract: Two to three sentences summarizing the document.
<!-- /entry -->
```
