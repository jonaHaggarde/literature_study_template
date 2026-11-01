---
description: Draft the project definition article from intake.md, revise it after the user's review, refine it after acceptance, and write scope.md from it once accepted.
argument-hint: "[optional: draft | revise | refine | scope]"
---

Work on `articles/definition`, the document the user reviews and accepts at the `definition`
gate, and that `scope.md` is written from.
$ARGUMENTS

## Which mode

If `articles/definition/` does not exist yet, create it first from its template
(`python study/scripts/new_article.py definition`); it starts as a skeleton at version 0.1.
Then, if an argument names a mode, use it. Otherwise read `articles/definition/versions.json`
and choose:

| State of the article | Mode |
|---|---|
| only the skeleton row, no `\intake` tags in the sections | **draft** |
| drafted, not accepted | **revise** (when the user brings review comments) |
| accepted | **refine** (only when the user asks for a change) and **scope** |

Read `articles/definition/README.md` first. The skeleton's `\todo` text in each section file
states what that section must contain and must not contain; it is the specification.

## draft

1. **Preflight.** Read `intake/intake.md`. If it has no rows, stop and say to run `/intake`
   first. Run `python study/scripts/intake_check.py --coverage`. If a section has no answer,
   say which, and ask whether to draft with `TBD` there or interview more; do not guess.

2. **Write each section from the rows that serve it.**
   - **Every statement is tagged** with the intake rows it comes from, `\intake{I-4}` or
     `\intake{I-4,I-9}`, at the end of the sentence or the table cell, or marked `\inferred`
     when it is your inference. Keep inferences few; the user confirms or strikes each one.
   - **Values exactly as given** (units, tolerances). Never round, convert or tidy.
   - **Working language** goes in the constraints table as its own row (sources, notes and
     analysis, quotations), because `scope.md` is written from the definition and has a
     section for it. When intake has no row for it, write `TBD` and say so in the report.
   - `unknown` rows: write `TBD` in the section, with the owner and resolve-by date the intake
     gives, and an open row in the assumption register. In a study with one person the owner is
     that person, and a resolve-by date nobody gave is written "not set", never invented
     (a demanded date produces a made-up one).
   - `suspicion` rows are assumptions (status open), never facts.
   - Rows marked `conflicts with I-n`: set both out in an `\openissue{...}` naming both IDs.
     Do not choose.
   - A `preference` or `said` row that names a solution is not put in the definition (it
     contains no solutions). List these in your report; they stay in `intake.md` for the
     rationale.
   - A section with no rows keeps its `\todo`; say so in your report.
   - The assumption register's "Added in" is the version this draft will have, `v0.1`.
   - Write the abstract last, four sentences at most.
   - **Style:** follow `study/ai_instructions/article-style.md` (read it first). Each fact
     once, never restated in other words; list the claims, write, then cut.

3. **Record, build, check.**
   - `python study/scripts/article_version.py definition draft --restart --summary "First draft from intake.md"`
     (`--restart` replaces the skeleton's row so the first real draft is `0.1`)
   - `python study/scripts/build_articles.py --only definition`
   - `python study/scripts/validate_repo.py` (it fails on an `\intake{I-n}` that does not exist).
     Fix what it reports.
   - `python study/scripts/style_check.py definition`: fix every problem, and decide each
     judgment call.

4. **Report** in a few lines: the sections drafted and the ones left; how many statements are
   `\inferred`; the `TBD`s; the conflicts; the preferences set aside. Point to
   `articles/definition.pdf`. Say it is to be read on paper. The gate is passed with `/gate definition`: you brief them,
   and when they tell you to, you run `gate.py open` and then
   `gate.py close definition --summary "..."`, which records the acceptance. No `review`
   comes first.

## revise (drafted, not accepted)

The user brings review comments. For each: if it is new information, add a row to
`intake/intake.md` first (kind `said`, source `interview YYYY-MM-DD`) and cite its ID in the
text, so the trace stays whole. If it replaces what an earlier row said, the new row says
`supersedes I-n`. Make the change, then
`article_version.py definition edit --summary "..."`, rebuild, and report which sections
moved and the new version.

## refine (accepted)

Only when the user asks for a change. Same as revise, but record it with
`article_version.py definition refine --summary "..."`, which prompts the user each time.
Afterwards run `python study/scripts/scope_sync.py check`. If it says `scope.md` is stale,
**say so and suggest updating it, but do not update it now**: wait until the user says they
are ready (a few refinements usually come together).

## scope (accepted)

Run when the user says they are ready, or when `scope.md` is still the placeholder and the
definition is accepted.

1. Read the accepted definition and `study/ai_instructions/scope.md` (its questions give the
   structure: what the study is about, in scope, out of scope, borderline cases).
2. Write `scope.md` from the definition's problem, goal, scope table and constraints, and
   nothing else: no new items, no reading of the literature. Keep it to about a page, and
   remove the placeholder marker and its comment block. If `scope.md` already held content,
   add a dated line under "Scope changes" naming the definition version.
3. Run `python study/scripts/scope_sync.py stamp`.
4. Say that papers can now be gathered and converted.

## Rules

- **Never run `review` or `accept`.** They are the user's.
- **Never edit the user's intake files**, and never change an accepted article unless the user
  asked.
- **No solutions, no literature, no requirements on a design** in the definition.
- **Why:** the user accepts this article, so everything in it must be traceable to something
  they said or be visibly marked as inferred; and everything after it rests on it.
