# Article

A literature review article in LaTeX: a **comparison of methods** plus a
real introduction and related-work text. No new results. The value is the
side-by-side table and the pointers to where each method is described.

The working title and folder name are provisional.

## Layout

| Path | Holds |
|---|---|
| `main.tex` | Preamble, title, abstract, and the `\input` order of the sections |
| `sections/` | One `.tex` file per section, plus `references.tex` |
| `figs/` | TikZ sources, one file per figure, `\input` from the sections |

## Shape of the paper

The sections run in this order, and the comparison is the core.

```mermaid
flowchart LR
  I[Introduction] --> R[Related work]
  R --> M[Scope and method]
  M --> C[Comparison]
  C --> D[Discussion]
  D --> K[Conclusion]
```

The comparison section is a taxonomy figure of the method families, then
one wide table with the columns *measurements used*, *estimated quantity*,
*model used*, *methodology*, *reference*. That is the format of Table 1 in
Singh et al., "Literature review and fundamental approaches for vehicle and
tire state estimation". Every row needs a reference; do not add an entry
without one.

## Conventions

- `\todo{...}` marks unwritten text. Grep for it before sharing a draft.
- References are a plain `thebibliography` list in `sections/references.tex`
  (no bibtex run), numbered in order of first citation, and each source should
  be in `study/catalog.md` with a note in `study/notes/`.
- The abstract carries a status banner saying the draft is AI-assisted and
  unverified. Remove it only after every entry has been checked against its
  source.

## Build

```bash
pdflatex main.tex
```

Run it twice so cross-references resolve, or use `latexmk -pdf main.tex`.
