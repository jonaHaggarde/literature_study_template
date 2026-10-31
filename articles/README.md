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

The articles, in the order the work reaches them. Each is a sibling folder with its own
`main.tex` and a `README.md` stating its purpose and what it is written from; the folder
name follows the article, not the gate that accepts it.

| Article | Gate | Kind |
|---|---|---|
| `definition` | definition | light |
| `map` | map | light, mostly figures and tables |
| `review` | survey | full |
| `requirements` | requirements | medium, optional |
| `rationale` | concept | full |
| `specification-<name>` | split | full, one per chosen concept; copy `_templates/specification/` |

Folders starting with `_` (the templates) are ignored by the build and the validator.

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
- **No article is edited silently.** Each has a `versions.json` and a printed
  revision table (version `N.n`, time, kind, sections changed, summary, by). The first draft
  is `0.1`. Claude records every substantial edit with `python study/scripts/article_version.py
  <name> edit --summary "..."`, which bumps the minor number and computes which sections
  changed. Only the user bumps the major number (`review`), after a manual review, so major 0
  means never reviewed, and the title page says so. When the major number is bumped, the
  minor rows of the previous version collapse into one summary row in the printed table
  (`0.1` and every `N.0` row stay); `versions.json` keeps all rows. The validator compares
  each article with its last version and warns about a change with no row, and fails on it
  in CI.
- **Derived files are never hand-edited.** `references.bib` and
  `sections/references.tex` and `sections/versions.tex` in each article, and the review's
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
