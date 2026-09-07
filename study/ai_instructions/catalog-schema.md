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
  Omit for types listed under Field-exempt types below.
- `contribution` — one of the Contribution types below. This is the
  single most useful field for "which method/finding should I trust"
  questions, so check it deliberately on every document rather than
  defaulting to the first thing that seems to fit.
- `compares` — only for `contribution: comparison-study` (or `survey`, if
  it draws an explicit ranking/recommendation across methods/findings) —
  what specifically is being compared and on what basis, e.g. "CBT vs.
  medication vs. combined treatment (remission rate, 12-week RCT)". Omit
  for documents that only use/propose one method or report one finding.
- `tags` — comma-separated topic tags. **Three to five, and prefer too
  few** — see "Tags" below.
- `note` — path to the generated note (`notes/...`)
- `source` — path to the source PDF (`PDFs/...`)
- `summary` — the entry's substance, written under a hard rule; see
  "The summary field" below. Not the document's own abstract.

### Empty fields: omit, never write `n/a`

A field that does not apply is left **empty** — the key stays, the value
is blank:

```
compares:
```

Do not write `n/a`, `none`, `-`, or `N/A`. The parser treats an empty
value as absent; a literal `n/a` is a value, and it survives into the
index, into greps, and into every query that filters on the field. This
rule holds everywhere, including for the field-exempt types below.

## The summary field

The most common failure in this repo is a `summary` that reads like the
document's own abstract: fluent, neutral, and almost entirely redundant
with `approach`, `compares`, and `tags`, which sit two lines above it.
The information that actually decides whether to open the note — the
numbers, and the limitation — gets squeezed out.

So the summary is written as **the complement of the other fields.**

**Must contain, in this order:**

1. **The result, with numbers and the rig, dataset, or population it was
   measured on.** Never "achieves good accuracy."
2. **The comparison verdict only** — the outcome, not the list of
   baselines. `compares` already holds the list.
3. **The authors' own admitted limitation.** This is the sentence that
   most often decides whether the note is worth opening, and it is the
   first thing lost when people compress badly.
4. **Why this document is here, if that is not obvious from the document
   itself.** When a document was acquired to fill a specific gap, or
   sits partly outside scope, the summary says so and says how far it
   actually gets. A neutral summary is *actively misleading* for such an
   entry — it describes the document accurately and the entry wrongly.
   This clause can only be written by whoever knows why the document was
   acquired, which is why the summary is coordinator-ratified rather
   than worker-final (see `delegation.md`).

**Must not:**

- Restate `approach`, `compares`, or `tags`.
- Open with "Proposes a…" or "This paper presents…" — `contribution`
  already says what kind of document it is.
- Use hedging connectives. Sentence fragments are fine.

**Budget:** roughly 2 sentences / 400 characters.
`../scripts/validate_repo.py` *warns* past that, and never fails — the
budget is a nudge toward compression, and a genuinely dense entry is
allowed to exceed it.

The compression this rule buys is real rather than lossy: what it
deletes already exists in the adjacent fields, so nothing is lost from
the *entry*, only from the *field*. The side benefit matters as much as
the size — the rule forces the numbers out of the notes and into the
catalog, where they are greppable.

Neutral worked example. Before, 588 characters, mostly restating fields
that are already filled in:

> *Proposes a two-stage pipeline for the task. It first performs a
> coarse alignment step, then refines the result with a local method,
> using manually-measured starting values. Compared head-to-head against
> the manual baseline, method A, and method B on a four-unit rig, it
> achieves the lowest error among the automated approaches while
> remaining competitive on runtime.*

After, 330 characters, carrying strictly more information:

> *Lowest error among the automated methods (0.15–0.28%; manual still
> best at 0.11–0.17%) and fastest overall, 18 min vs. 20–37. Not
> rig-free: needs accurate manual initial measurements per unit,
> converges slowly on non-overlapping pairs, untested under mechanical
> deformation or hardware damage.*

## Tags

`tags` is comma-separated, and it is **not** a keyword dump. Two rules:

- **Three to five tags. Prefer too few.** Every extra tag is a promise
  that this document will be useful to someone querying that tag.
- **Tags describe what a document *contributes*, not what it
  *mentions*.** A survey that discusses method X at length but
  contributes nothing to X is not tagged X. Tagging it X surfaces it in
  every future query about X — which is exactly the thing the tag exists
  to prevent. This is the single most common tagging error and it is
  invisible until the corpus is large enough that it hurts.

Check `../topics/vocabulary.md` for canonical spelling before inventing
a new one. `validate_repo.py` **fails** on a non-canonical tag used by
two or more entries — at that point it is load-bearing, people will
query on it, and this is how one concept quietly acquires two spellings
and splits its own search results. A single-use tag is only a warning,
since a genuine one-off (a named dataset, a single instrument) is
legitimately free-form.

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

For these `type` values, `approach`, `contribution`, and `compares` are
left **empty** (see "Empty fields" above — the key stays, the value is
blank, and never `n/a`). Fill in `tags` and `summary` as normal:

- `standard`
- `dataset`

Add to this list if a project-specific type (defined above) also doesn't
fit the contribution/approach framing.
