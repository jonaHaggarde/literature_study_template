# Method cards

A **method card** is a short, structured record of one method, kept in the
note of the document that describes it. The cards feed the comparison table
in the review article (`../../article/`): `scripts/build_article_table.py`
turns every card into one table row. This file defines what a card holds.

It is read by `scripts/method_cards.py`, `scripts/validate_repo.py` and
`scripts/build_article_table.py`. **Edit the field list below to fit this
study; do not edit the scripts.** Keep each field as a backtick-wrapped key
at the start of a bullet under `## Fields`, one per line, and the scripts
stay in sync. The order here is the column order in the table.

## Fields

- `input` — what the method needs in order to run: the data, signals or
  resources it consumes
- `output` — what the method produces or decides
- `model` — the model or assumptions it rests on, if any
- `technique` — the method or algorithm itself, in a few words

The defaults above are deliberately topic-neutral. A study replaces them
with whatever columns its comparison needs (for instance a validation
level, or a cost). **Settle the columns before extracting many cards.**
Changing a field afterwards means revisiting every card, which is the main
cost of this design; the first dozen documents are the right time to find
out the columns are wrong.

## Grouping: the `family` key

A card may carry one more key, `- family: name`, which is **not** a column.
It groups the rows of the table by method family and is defined in
`../topics/families.md` (which ships empty). Unlike the fields above it is
**collection-derived**: it depends on the other methods in the corpus, so a
worker proposes it in its report and the coordinator writes it into the card
after ratifying, as for `tags`.

## Where a card lives

In the document's note, after `## Implementation Notes`, as one
`### Method name` block per method:

```
## Method Cards

### Name of the method
- input: ...
- output: ...
- model: ...
- technique: ...
```

The heading is the method's name and becomes the first column of the table.
The table's reference column is derived from the catalog entry (see
`../../article/README.md`); a card does not repeat it.

## Rules

- **One card per method the document itself proposes, tests, or compares as
  its subject.** A comparison study that evaluates four methods gets four
  cards. A survey that merely *describes* other people's methods gets none:
  those methods belong to the papers that introduced them, and each of those
  has its own note. A document with no method of its own (a standard, a
  dataset, a pure theory text) has no `## Method Cards` section at all.
  Leaving the section out is the honest answer; an empty or invented card is
  not.
- **Document-derived, so the worker writes it** and it is accepted as-is,
  like `approach` and `summary` (see `delegation.md`). It records what the
  document reports. It is not a judgment of the method and never a
  recommendation.
- **Plain text.** No LaTeX, no markdown formatting: the table script
  escapes special characters. Keep each value to a short phrase; a cell is
  a pointer, the note is where the detail lives.
- **Empty fields: omit, never write `n/a`.** Same rule as the catalog
  (`catalog-schema.md`). Leave the value blank.
- **Use the document's own terms where it has them,** so the table stays
  checkable against the source. The verification pass compares a row to the
  document, and a paraphrase makes that harder.

## Why cards live in notes and not in a table file

Each cell is written once, by the worker that has the whole document in
context, and sits next to the text it came from. The table is then a
*derived* file, regenerated and never hand-edited, the same discipline as
`../catalog-index.md`. The cost is that the columns must be fixed early and
that a fixed field flattens nuance (a hybrid method, several models); a
value that needs more than a phrase belongs in `## Implementation Notes`,
with the card pointing at the simplest true statement.
