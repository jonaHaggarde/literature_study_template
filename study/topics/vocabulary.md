# Tag vocabulary

Canonical tag names for recurring concepts, so `tags:` fields stay
consistent across `catalog.md` and every note's frontmatter as the corpus
grows. Check here before inventing a new tag; add a new canonical term
the first time a genuinely new one shows up, rather than letting
near-duplicates accumulate (e.g. two spellings, or a synonym, of the same
concept).

This file ships empty on purpose. A tag vocabulary is the one part of
this template that cannot be pre-written: it has to come from the actual
documents. It grows, a term at a time, as the corpus does.

## What a good tag looks like

- **It names something a document can *contribute to*, not just mention.**
  This is the rule that keeps the vocabulary useful. A tag is a promise
  that entries carrying it are worth opening for that subject; a tag
  applied to everything that mentions the subject is a promise nobody
  can keep.
- **It is at the granularity people actually query at.** Too broad
  ("methods") matches everything and distinguishes nothing. Too narrow
  ("method-X-variant-3-on-dataset-Y") matches one entry and would have
  been better as free text in `approach`. The test: would you ever ask
  "what do we have on this?"
- **It is one concept with one spelling.** Pick a form — lowercase,
  hyphenated, singular — and hold to it. `validate_repo.py` fails on a
  tag that differs only in case from a canonical one, and on any
  non-canonical tag used by two or more entries, precisely because a
  concept with two spellings silently splits its own search results.
- **It survives the corpus growing.** A tag that made sense across five
  documents and matches sixty is no longer a filter. When that happens,
  split it and say so here rather than leaving it to rot.

**One-off specifics** — a named study, a specific dataset, a single named
instrument — are fine as free-form tags and don't need to be
canonicalized here; the validator warns about them rather than failing,
so near-duplicates still get eyes on them. This list is for concepts that
recur across multiple documents. The moment a one-off is used by a second
entry, it has stopped being a one-off: add it here.

**Three to five tags per entry**, and prefer too few. See
`../ai_instructions/catalog-schema.md`.

Format: one canonical tag per line, backtick-wrapped, under a heading
grouping related concepts — `scripts/validate_repo.py` parses this
format, so keep it. A one-line gloss after the tag is welcome where the
term is ambiguous; the parser only reads the backticked part.

## Methods / approaches

<!-- e.g. `randomized-controlled-trial`, `grounded-theory`,
     `finite-element-model` — add as they show up. -->

## Problem domains / estimated quantities

<!-- The recurring subjects this study's documents actually measure or
     address. -->

## Populations / contexts

<!-- If relevant to this field — study populations, settings, or
     application contexts that recur. Delete this section if not
     applicable. -->
