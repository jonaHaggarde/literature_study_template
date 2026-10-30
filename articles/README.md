# articles/

The LaTeX articles of a study, one folder each, and their generated PDFs. Every
stage of the work that is accepted at a gate has an article here, so the root
stays clear and the PDFs are easy to find.

```
articles/
  README.md
  common/           shared preamble, and the hand-written extra sources
  review/           main.tex, sections/, figs/, references.bib (generated)
  review.pdf        generated; PDFs sit here, directly in articles/
  gates/            reserved for gate definitions and records (not built yet)
  .build/           LaTeX auxiliary files (ignored)
```

More articles are added as the work reaches them (the project definition, the
rationale, the specification, and so on). Each is a sibling folder with its own
`main.tex`; the folder name follows the article (`review`, `rationale`), not the gate
that accepts it.

## Rules

- **One folder per article, and one PDF per article, directly in `articles/`.** The
  folder holds `main.tex`, its section files in `sections/`, and its figures.
  Several specification documents are separate articles (`specification-<name>`),
  never one document with several parts.
- **A shared preamble.** `common/preamble.tex` holds the packages and the generic
  macros (`\todo`, `\openissue`). Each `main.tex` starts with its `\documentclass`
  and `\input{../common/preamble}`. Notation that belongs to one article (its
  symbols) goes in that article's own `main.tex`.
- **A bibliography per article, only if it cites sources.** Articles do not cite
  the same sources, and each should be self-contained and movable. Each article has
  its own generated `references.bib` holding exactly what it cites; BibTeX (the
  `unsrt` style) numbers the entries in order of first citation, local to the
  article. An article that cites nothing has no `references.bib` and no bibliography.
- **Where a source comes from.** A source in `study/catalog.md` is cited by its
  derived key (first author's surname plus year) and written into the `.bib`
  from the catalog. Any other source (a provided document, a rulebook) is a
  hand-written entry in `common/references_extra.bib`.
- **Derived files are never hand-edited.** `references.bib` and
  `sections/references.tex` in each article, and the review's
  `sections/comparison_rows.tex`, are regenerated (by `build_articles.py`, and by
  every `validate_repo.py` run).

## Building

```bash
python study/scripts/build_articles.py              # every article
python study/scripts/build_articles.py --only review
python study/scripts/build_articles.py --no-latex   # derived files only
```

It regenerates the derived files, runs `pdflatex` (and `bibtex` where an article
cites sources) with all auxiliary files in `articles/.build/<name>/`, and copies
each PDF to `articles/<name>.pdf`. It needs a LaTeX distribution (MiKTeX or TeX
Live) and says so if it is missing. The PDFs and `.build/` are build output and are
not committed.

## Why it is laid out this way

The root of the repo grows fast, and an article per stage would add a root folder
each. One folder holds them all. PDFs next to the folders, not inside them, means one
place to look for what to read. A bibliography per article keeps each document
independent: a specification written here and implemented elsewhere carries only its
own sources. The shared preamble is the only thing that keeps a macro meaning the same
thing in every article.
