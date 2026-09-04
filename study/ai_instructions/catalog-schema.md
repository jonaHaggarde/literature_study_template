# Catalog schema

Field definitions and allowed values for entries in `../catalog.md`. Edit
the allowed-value lists below to fit this study's actual field — they're
read by `../scripts/validate_repo.py`, so keep entries backtick-wrapped,
one per line, under their heading, and the script stays in sync
automatically. Don't edit the script itself to change these lists.

## Fields

- `title` — document title
- `authors` — comma-separated
- `year` — publication year
- `type` — one of the Document types below
- `approach` — the specific method/model/framework used, if applicable
  (e.g. "randomized controlled trial", "finite element model", "grounded
  theory") — helps narrow within a crowded topic without opening files.
  Not applicable for types listed under Field-exempt types below.
- `contribution` — one of the Contribution types below. This is the
  single most useful field for "which method/finding should I trust"
  questions, so check it deliberately on every document rather than
  defaulting to the first thing that seems to fit.
- `compares` — only for `contribution: comparison-study` (or `survey`, if
  it draws an explicit ranking/recommendation across methods/findings) —
  what specifically is being compared and on what basis, e.g. "CBT vs.
  medication vs. combined treatment (remission rate, 12-week RCT)". Omit
  for documents that only use/propose one method or report one finding.
- `tags` — comma-separated topic tags — see `../topics/vocabulary.md` for
  canonical names, check before inventing a new one
- `note` — path to the generated note (`notes/...`)
- `source` — path to the source PDF (`PDFs/...`)
- `abstract` — 2-3 sentence summary

## Document types

- `paper` — peer-reviewed journal or conference paper
- `book`
- `article` — non-peer-reviewed article (magazine, trade press, blog)
- `report` — technical report, white paper, working paper
- `thesis` — MSc/PhD thesis or dissertation — flag explicitly wherever
  cited as a decision's literature basis; not peer-reviewed, weight with
  appropriate caution rather than treating as equal to peer-reviewed work
- `preprint` — not yet peer-reviewed; same caution flag as `thesis`
- `dataset`
- `standard` — a standard, regulation, or handbook rather than a research
  work
- `other`

Add project-specific types here if the field needs them (e.g.
`clinical-trial-registration`, `case-law`, `patent`) — just document what
they mean and whether they're field-exempt (below).

## Contribution types

- `survey` — broad narrative literature review, many methods/findings
  described but not necessarily tested/compared head-to-head
- `meta-analysis` — quantitative pooled synthesis across multiple studies
  (distinct from `survey`, which is narrative)
- `comparison-study` — the document itself puts two or more
  methods/approaches/findings head-to-head on shared data/conditions and
  reports which performs better or holds up — use whenever applicable,
  it's the most useful tag for deciding between options
- `novel-contribution` — proposes/reports something new (a method, model,
  theory, finding) without head-to-head comparison against alternatives
- `experimental-validation` — tests an existing method/hypothesis rather
  than proposing something new or comparing alternatives
- `applied-case-study`
- `other`

## Field-exempt types

For these `type` values, `approach`/`contribution`/`compares` are `n/a` —
just fill in `tags` and `abstract`:

- `standard`
- `dataset`

Add to this list if a project-specific type (defined above) also doesn't
fit the contribution/approach framing.
