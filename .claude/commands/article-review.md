---
description: Build the review article from the study — preflight, cards, table, verification pass, checks. Reports what is missing; never decides the project.
argument-hint: "[optional: one step to run, e.g. verify | table | check]"
---

Run the review-article workflow in `articles/review/workflow.md` and report where
it stands.
$ARGUMENTS

The article is phase-1 output: it reports what the literature says and
contains **no decisions** (root `CLAUDE.md`). You build and check it; the
user chooses columns, families, and what the scope is.

## How to run it

1. **Preflight.** If `articles/review/` does not exist yet, create it from its template
   (`python study/scripts/new_article.py review`) and tell the user. Then read
   `articles/review/workflow.md` and
   `study/ai_instructions/scope.md`. If `scope.md` still carries the
   `<!-- placeholder -->` marker, stop: the article's scope section is that
   scope in prose, and filling it in with the user is the real task.

2. **Columns and families are settled?** Read
   `study/ai_instructions/method-card.md` (the column fields) and
   `study/topics/families.md` (the method families). If either is still the
   shipped default or empty and the catalog already has more than a dozen
   processed documents, say so and ask the user to settle them before more
   cards are written: changing a column later means revisiting every card.
   Propose a column set or family list from `study/topics/*.md` dossiers if
   they want one; the user chooses.

3. **Cards cover the corpus.** Read `study/catalog-index.md`. List the
   processed documents whose `contribution` suggests a method of their own
   (`novel-contribution`, `experimental-validation`, `comparison-study`,
   `applied-case-study`) and whose note has no `## Method Cards` section.
   Do **not** write cards yourself: report them, and offer to run
   `/process-batch` style `note-extractor` workers on that list. Cards are
   document-derived work for the worker; the `family` field is
   collection-derived, so you ratify the workers' proposed families and
   write them into the cards.

4. **Build the derived files.**
   `python study/scripts/build_review_table.py` rewrites
   `articles/review/sections/comparison_rows.tex`, and
   `python study/scripts/build_bibliography.py` writes each article's own
   `references.bib`. Sources not in the catalog go in
   `articles/common/references_extra.bib`.

5. **Verification pass.** `python study/scripts/verification.py todo`
   lists cards that are unverified or stale, grouped by note. For each note
   launch one `row-verifier` agent (cheap Haiku, one call per note, several
   in parallel) with the note path and that note's cards. Give it the cards'
   values and nothing from the article. When it reports, read the report
   yourself, then record each verdict:
   `python study/scripts/verification.py record "<note>#<method>" pass|fail|unclear "<comment>"`.
   A `fail` or `unclear` is not fixed by you silently: show the user the
   quote and the card, and fix the card or the note with their say-so.

6. **Check.** `python study/scripts/validate_repo.py`, then build:
   `python study/scripts/build_articles.py --only review` (the PDF lands in
   `articles/review.pdf`). Report: FAIL and WARN lines,
   the `\todo` count, verified vs total cards, and any `article-decision`
   warning. A decision-language warning is not a style nit: it means the
   article is drifting out of phase 1, so show the line and ask.

7. **Report, ranked by what blocks "done".** Done means (see
   `articles/review/workflow.md`): no `\todo`, every citation resolves, every card
   verified, scope final, status banner removed, and the user has read the
   whole PDF. Say which of those are not met. Never remove the status
   banner yourself.

If an argument names one step (`verify`, `table`, `check`), run only that
step plus its prerequisites.
