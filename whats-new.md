# What is new in this release

The difference between the previous `main` and this one: 71 commits, 183 files changed. `main`
held the literature-review engine and a first review-article scaffold; this release turns it into a
pipeline you drive from chat, from the first interview to a specification. Delete this file once it
is no longer news.

## The change in one picture

| | Previous `main` | This release |
|---|---|---|
| Start | Fill in `scope.md` by hand | "let's start": Claude sets up, shows a ten-slide deck, recommends `/intake` |
| Order of work | Collect papers, then write a review | Intake, definition, map, review, requirements, rationale, specification, each a LaTeX article with a version history |
| Decisions | Yours alone | Gates after each article: Claude briefs you, you decide when to pass |
| Finding papers | You bring PDFs | `/find-papers` searches OpenAlex, proposes a table, downloads only the numbers you approve |
| Scanned PDFs | Not handled | OCR by script, budgeted page-image reading for equations and tables |
| Where am I | Read the files | `/where` draws the gates, intake, catalog and articles from the files |
| Writing quality | None | An advisory style check for padded and machine-written prose |

## What was added

- **Pipeline:** intake folders (`intake/own`, `intake/received`), an intake digest with IDs that the
  definition article cites, and `/intake`, `/definition`, `/new-article`, `/article-review`, `/gate`,
  `/understand`. Articles are created from templates and generated parts (comparison tables, coverage
  counts, a decision tree) are built by scripts.
- **Gates:** six gates and an ad hoc one; Claude never passes one for you. `scope.md` is written from
  the accepted definition and flagged stale when the definition changes.
- **Search and fetch:** `lit_search.py` and `lit_fetch.py`. Angles are declared before any query,
  surveys come first, the table never claims a topic is covered, and a downloaded file is kept only if
  its first pages carry the expected title. Paywalled papers are yours to fetch; a script files them
  under the right lead. Design and reasons: `study/search-engine-design.md`.
- **Status view and onboarding:** `/where` (a picture), `onboarding-deck/` (source of the slides).
- **Engine hardening:** robust conversion (timeouts, duplicate detection), structured worker reports,
  `leads.md` for papers heard of but not read, optional requirements module.
- **Style:** `style_check.py` with a phrase list that grows from your reviews, and rules for the
  patterns that read as machine-written.
- **Usage log:** a one-line record of how the template is used; off in the template's own repo.

## Known limits

- The search engine is built from tests and one live search; no study has run a full round yet.
- No progress display during a search, and no coverage matrix in `/where`.
- Summaries are not yet audited for invented content (planned, see `roadmap-notes.md`).
- No `LICENSE` file.
- `dev-gui-dashboard` (an earlier prototype) is not part of the release.
