# Method families

The canonical names of the **method families** of this study: the groups
the review article's comparison table is divided into, and the structure
its taxonomy figure and comparison subsections follow. A family is a set
of methods that share an approach and so are compared on the same footing
(for instance, all methods that estimate a quantity by the same kind of
technique).

This file ships empty on purpose. A taxonomy cannot be written before the
literature has been read, and a template that guessed one would impose it.
Fill it in with Claude once the first dozen or so documents are processed
and the shape of the field is visible, then keep it current.

## What a good family looks like

- **It groups methods by what they are, not by who wrote them or when.** A
  reader should be able to say why two methods share a family.
- **It is at the granularity of the comparison.** Too many families give a
  table of one-row groups; too few give a group nobody can compare within.
  Roughly three to eight is the useful range for one article.
- **Families do not overlap.** A method belongs to exactly one. If a
  method is genuinely a hybrid, put it in the family of its dominant
  technique and say so in its card, or define the hybrid as a family of
  its own.
- **One concept, one spelling.** Lowercase, hyphenated, singular, like the
  tag vocabulary.

## How a card gets a family

A card carries an optional `- family: name` line (see
`../ai_instructions/method-card.md`). The family is
**collection-derived**: it depends on the other methods in the corpus, so
a `note-extractor` worker does not write it. The worker **proposes** a
family in its report, and the coordinator adds the line to the card after
ratifying against this file, exactly as for `tags`
(`../ai_instructions/delegation.md`).

`validate_repo.py` warns when a card's family is not listed here. When
any card has a family, `scripts/build_article_table.py` groups the table
rows by family, in the order listed below, with unlisted families after
and cards without one last under "Ungrouped".

## Using the taxonomy in the article

The families are the skeleton of `../../article/`: one subsection of
`sections/comparison.tex` per family, and the nodes of
`figs/taxonomy.tex`. Writing the families is the hand-off from reading
the literature to writing about it, which is why the user settles them
before the prose is drafted.

Format: one canonical family per line, backtick-wrapped, at the start of
the line, optionally under headings. A short gloss after the name is
welcome; the parser only reads the backticked part. Order is the order of
the table groups.

## Families
