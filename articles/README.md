# articles/

The LaTeX articles of a study, one folder each, and their generated PDFs. Every
stage of the work that is accepted at a gate has an article here, so the root
stays clear and the PDFs are easy to find. A fresh repo holds **no articles**, only
their templates: each article is created when the work reaches it.

```
articles/
  README.md
  common/           shared preamble, and the hand-written extra sources
  _templates/       one template per article (ignored by the build and the validator)
  <name>/           a created article: main.tex, sections/, versions.json, references.bib (generated)
  <name>.pdf        generated; PDFs sit here, directly in articles/
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
| `specification-<name>` | split | full, one per chosen concept |

Create one with `/new-article <kind> [name]` (or `python study/scripts/new_article.py ...`),
never by copying a folder by hand. The commands that work on an article create it themselves
when it is missing (`/definition` creates the definition, `/article-review` the review).
Folders starting with `_` are ignored by the build and the validator; `_templates/README.md`
explains the mechanism.

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
  is `0.1`. Five kinds of row:

  | Kind | Who | Number | When |
  |---|---|---|---|
  | `draft` | Claude | 0.1 | the first draft |
  | `edit` | Claude | minor | a substantial change before acceptance |
  | `review` | the user | major | after a manual review (major 0 = never reviewed) |
  | `accepted` | the user | major | a review that also passes the article's gate |
  | `refined` | Claude, on the user's request | minor | any change to an accepted article |

  Claude records an edit with `python study/scripts/article_version.py <name> edit --summary
  "..."`, which computes which sections changed. After acceptance `edit` is refused and
  `refine` (which prompts the user) is the only way in; `review` and `accept` are the user's.
  In the printed table, runs of `edit` rows fold into one summary row when the major number
  is bumped; `0.1`, every `review`/`accepted` row and every `refined` row stay, and the
  refinements fold only when the article is accepted again. `versions.json` keeps all rows.
  The validator compares each article with its last version and warns about a change with
  no row, and fails on it in CI.
- **Gates.** An article is accepted at a gate (`articles/gates/definitions.json` lists them;
  `/gate` shows where they stand). A gate runs `open` (the user, once the entry checks pass),
  a briefing in chat (script facts that need attention, and Claude's critique), for most gates
  the `/understand` check (questions in chat, answered from memory; Claude ends with a
  suggestion, ready or slower, which has no effect), then `close`, which is `accept` plus
  `articles/gates/<id>.json`, so the article's status and the gate record cannot disagree.
  While a gate is open the article stands still; the validator warns if it changes. There is
  no gate report: the version table is the record, the briefing and the check are the
  conversation, and a document nobody asked for would only duplicate both.
- **Computed parts are generated.** `python study/scripts/build_article_parts.py <name>` (run by
  the build) writes the map's coverage counts per method family, the requirements' traceability
  tables (each derived requirement's path up to the primary ones, gaps flagged) and the
  rationale's decision tree (from `decision_tree.md`, status `candidate` marks an alternative that
  goes on to a trial). The hand-written section `\input`s the generated file, so the explanation
  is hand-written and the numbers and picture are not. The validator warns about a stale file.
- **TBD is explained in the article.** `\tbdnote` (in `common/preamble.tex`) prints one line under
  the status box saying that TBD marks a value nobody can give yet and names an owner and, where
  set, a resolve-by date. The definition, requirements and specification templates include it;
  any article that writes TBD should too, so a reader never meets the word undefined.
- **Dense writing.** The text follows `study/ai_instructions/article-style.md`: each fact
  once, never restated in other words (an abstract and a conclusion may restate), numbers
  over adjectives. `python study/scripts/style_check.py <name>` reports what it can find;
  the validator warns about clear problems and never fails on style.
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
