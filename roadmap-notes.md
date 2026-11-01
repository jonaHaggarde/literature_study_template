# Roadmap notes: how a study moves through phases

**Status: a design note, partly built.** Written 2026-10-29 from a
discussion; the gates, intake and article parts it anticipated are built (last section). The
rest is not a convention yet. It is parked so the larger
direction is not lost while the review article was built (`articles/review/`,
now merged). When a part is built, it moves to a `dev-<feature>` branch and
into the real docs.

## The idea: a study has phases, and the repo should know which one it is in

The template today is built for the first phase only. The author's actual
use runs three.

```mermaid
flowchart LR
  A[1. Survey] --> B[2. Concept and decisions]
  B --> C[3. Split]
  A -.-> AR[Review article]
  C -.-> SP[Spec article]
  C --> IMPL[Implementation repo]
```

| Phase | Goal | Output | Decisions allowed? |
|---|---|---|---|
| **1. Survey** | Understand every method that exists, find reviews and papers. May refine and update the *scope* of the papers and of the article. | Catalog, notes, dossiers, the **review article** | **No.** Nothing about the product is decided. |
| **2. Concept and decisions** | Discuss the actual thing being built: limits, requirements, priorities. Make assumptions, rule solutions out, decide. Done in the same repo because the knowledge (and the AI's context) is already there. | `decisions.md`, `ideation/`, `theory/` explainers | Yes, with the literature-basis / project-context split. |
| **3. Split** | Keep theory and concept here. Create a **separate implementation repo** (code, models) that looks clean to outsiders and carries none of the pre-study mess. | The implementation repo, plus a **spec article** that is the interface between the two repos | n/a |

The first phase is one of the first big milestones of a repo.

## Things this implies (all open)

- **A phase marker.** Somewhere the repo states which phase it is in, so
  Claude does not make decisions in phase 1 and does not treat phase-2
  material as literature. Candidate home: `timeline.md` plus a line in the
  root `CLAUDE.md`.
- **The review article stays decision-free.** Phase-2 content must not leak
  into it. The article is the artefact of phase 1 and is finished (or
  frozen) before phase 2 reasoning is written up.
- **The spec article as the repo-to-repo interface.** A second article,
  written at the end of phase 2, that describes the implementation well
  enough to build from. Inspired by the hand-written `algorithm/` folder in
  LiUFS-TorqueVectoringStudy (status banner per file, one document per goal
  and version, text only, the *why* linked to `ideation/`). Needs its own
  folder, template and status rules. Not designed yet.
- **A split procedure.** What moves to the new repo, what stays, how the
  implementation repo links back (by tag or commit of this repo, so a spec
  version is citable), and how it is kept clean. Possibly a `/split`
  command or a checklist.
- **Gates between phases.** Phase 1 to 2 is a natural place for a forced
  stop-and-read, which connects to `dev-gate-events` (printable report,
  debrief). Kept separate for now, but the two features should be designed
  so they can meet.

## Requirements in the phase model

Requirements are staged, and the stages line up with the phases above. Top-level
facts and goals belong to the **project definition** (before any search). A first
requirements list (version 1, with honest `TBD`s) is written **after the survey**,
using the review article as evidence of what is typical and achievable. Lower-level
requirements are written **after the concept decision** they depend on, so a number
cannot pre-decide the design. The optional `requirements/` module describes this;
its detailed per-type templates wait for real use. "Requirements v1 accepted" is a
candidate gate for the gate-events design.

## Project definition document (comes before the review article)

Added 2026-10-29. Before the review article, a repo gets **one standalone
`.tex` (built to PDF)** that defines the project: **scope, introduction and
problem description**. Purpose: a clearly defined project that everything
after it, the review article included, can be measured against. The
scope in `study/ai_instructions/scope.md` is derived from it, not the other
way round.

How it is produced is open. Likely a combination of:

- **A questionnaire from Claude**, asking the questions a project
  definition needs answered.
- **The user prompting**: free description, corrections, priorities.
- **The user adding documents** (briefs, rules, specifications) to
  `intake/received/`, which Claude reads and cites.

Needs a defined structure: what the questionnaire asks, how answers and
documents become sections, and what "defined enough to proceed" means.
Not designed. Not to be discussed in depth yet.

## Gates: where the bigger picture fits

The phase boundaries and the project definition are **gates**, so they
belong with the `dev-gate-events` design (forced stop, printable PDF,
debrief) rather than with the article. Candidate gates, none decided:

1. Project definition accepted (scope, introduction, problem description).
2. Survey finished (review article read and understood).
3. Concept decisions taken.
4. Split into the implementation repo.

The article work stays separate for now. The two should be designed so
they can meet.

## Onboarding slide (PowerPoint)

A **slide deck a new user opens and reads before using the repo**,
explaining the whole flow and every gate: what each phase is for, what is
frozen at each gate, what the user is expected to read and do. Depends on
the gate design, which is now built (2026-10-31), so it can be written. Not started.

## Scanned PDFs and OCR (built 2026-10-30, branch `dev-ocr`)

A hybrid, decided after testing on a scanned 1960 paper: **OCR by script is the
base layer** (free, good on prose, bad on equations, symbols and tables), and
**reading page images is on request only**, because it costs thousands of
tokens per page (not yet measured). `convert.py` OCRs a scan when `ocrmypdf` and Tesseract
exist (it also finds them in their default install folders, prints install hints
and never installs), on a copy, so the PDF and its hash never change. Pages are
marked `(ocr)`, the note lists the equation-heavy ones, and `--reocr` fixes scans
converted earlier without touching what is already written in their notes.

Reading page images is rationed by structure: a plan, the user's approval, small
one-at-a-time tickets, a per-request cap in `vision-budget.md` (no daily limit: every ticket is approved by hand, and measured token usage is recorded instead of estimated), and a
`page-reader` agent with only `Read` and `Write` whose launch asks the user each
time. Method cards that rest on OCR equations carry `read_from: ocr` and are not
counted as verified. Not built: tables were not tested, non-English text was not
tested, and a live `page-reader` launch was not exercised (see `feedback-notes.md`).

## Where each piece lives

- Phase 1 workflow and the review article: `articles/review/` (merged into
  `development` 2026-10-30; moved into `articles/` on `dev-articles-layout`).
- Gates: built on `development` (`articles/gates/`, `study/scripts/gate.py`). `dev-gate-events`
  holds the earlier parked design (printable report, debrief), superseded by the no-report decision.
- OCR and scanned PDFs: built and merged into `development` (branch `dev-ocr` deleted).
- What real usage says about the template (bug table, engine features,
  structure and larger ideas, suggested order): `feedback-notes.md`.
- Everything above beyond phase 1: this file only.

## Articles as templates (built 2026-10-31)

Every article is a template in `articles/_templates/`, created by `new_article.py` and
`/new-article` when the work reaches it; a fresh repo ships none. `test_templates.py`
instantiates every template, runs the article checks and builds the PDF where LaTeX is
installed. `review` was the awkward one: its table builder and the validator checks tolerate
its absence, and `/article-review` creates it when missing. The skeleton row at 0.1 stays, and
the first real draft replaces it with `draft --restart`, so a first draft is 0.1. Opening a gate
is expected to create its article once the gate machinery exists.

## Gates, intake and generated parts (built 2026-10-31 to 2026-11-01)

What the sections above called open is now built on `development`. Each item says what was
decided and why, so it is not reverted for being inconvenient.

**Pipeline before the survey.** `/intake` (interview, decided over a form because an interview
can follow up an unknown or a contradiction at once) builds `intake/intake.md`, Claude's digest
with `I-n` IDs. `/definition` drafts `articles/definition` from it, every statement tagged with
its IDs or marked inferred. Accepting it (the `definition` gate) writes `scope.md`; no papers are
gathered before that. A row can replace an earlier one with `supersedes I-n`, and
`intake_check.py --uncited` lists rows the definition left out.

**Gates.** Six, in `articles/gates/definitions.json`: `definition` (light), `map` (light),
`review` (full), `requirements` (medium, skippable), `concept` (full), `split` (full), plus an
`adhoc` stop-and-look with no article. `gate.py` keeps a record per gate with a hash of the
tracked files (soft freeze: the validator warns when an open gate's article changes). The gate
record, not the version row, is what `scope_sync` and the requirements warning read.

- **No gate report.** A separate document duplicated the version table, the chat briefing and the
  check, and cost reading time for no new information.
- **No rest day.** A forced wait between report and decision was disliked and had no reason that
  survived discussion.
- **`/understand` is a chat mode**, not a document: open question first, then questions on
  conclusions and gaps. It ends in a suggestion (`ready` or `slower`) with no effect on the
  gate, because its purpose is to slow the user down, not to block. Not offered for `definition`
  or `requirements`.
- **Gate commands run on the user's word in chat**, behind a permission prompt. `close` is
  `accept` plus the gate record, so no `review` precedes it.
- **Amendments:** a later specification article opens under the passed `split` gate.
- **Volume nudge:** an INFO line after 15 processed entries since the last gate.

**Assumptions have levels.** Top-level assumptions are `suspicion` rows in intake; an assumption
that matters to one article lives in that article's own section; chat-only premises go nowhere.
On "assume" Claude asks where it belongs, then runs the workflow. Reason: a register that took
everything would bury the top-level ones.

**Generated parts.** `build_article_parts.py` writes the map's coverage counts per method family
(counts only, no "found by" field), the requirements' traceability table (gaps flagged) and the
rationale's decision tree as TikZ, from the same table as the mermaid diagram (new status
`candidate`). The hand-written section `\input`s the generated file. `\tbdnote` prints what TBD
means under the status box of the articles that use it.

**Page-reader.** It records only equations, tables and figures below the OCR text and never
transcribes prose; the merge keeps OCR text and replaces earlier items. Reason: a verbatim page
transcription was blocked once by a content filter, and prose is what OCR already reads well.

**Tried once, then discarded (2026-11-01).** A trial intake and definition on a throwaway branch
gave six fixes, all merged: gate-command rule, no `review` before `close`, `supersedes`, a
working-language row, when a register row may be removed, and TBD owner and date.

**Still untested.** The page-reader against the real filter (needs an approved ticket, also
measures tokens); OCR on tables and non-English text; the style thresholds (Jaccard 0.6 and 0.4
are first guesses); whether the briefings and the ad hoc gate earn their reading time; the
TikZ tree's layout beyond compiling. CI skips the LaTeX tests (no `pdflatex` on the runner).
The next real test is the author's own large study.
