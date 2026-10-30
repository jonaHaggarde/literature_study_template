# Feedback notes: what real usage says about the template

**Status: analysis, not decisions. Written 2026-10-30 from `usage-log.md`**
(a log kept in a derived repo from 2026-09-07 to 2026-10-27, about 480
lines). Nothing here is built. Each item says what the log shows, what
this template does *today* (checked against the code on 2026-10-30, not
assumed), a proposal, and a rough size. Items link to `roadmap-notes.md`
where they belong to the phase model.

**`usage-log.md` was deleted from this repo on 2026-10-30** once its findings
were captured here. It was full of one project's content (a vehicle-control
design), and `main` has to stay topic-neutral and cloneable.

## Decisions taken (2026-10-30)

- **Articles are sibling `article-*/` folders** (`article-review/`,
  `article-spec/`, `article-manual/`, ...). A shared `article-common/`
  (preamble only; each article keeps its own reference list, per the
  per-file numbering rule) is created when the second article exists, not
  before. Settles L1.
- **Positioning: engineering-leaning, neutral core.** Most use is
  engineering projects, so the template should carry many tools for them,
  but nothing may be so built in that a non-engineering study cannot use it.
  Working rule: the **core** (catalog, notes, dossiers, scope, review
  article) must still pass the "eighteenth-century agriculture" test in the
  root README; **engineering tools are optional modules** at the root, each
  with its own README, absent from the validator's hard checks when the
  folder is missing or empty (the pattern `article-review/` already uses),
  and deletable without breaking anything. Settles the placement of L2.
- **Requirements engine (L2): to be investigated and developed, optional.**
  Not built yet; first a design discussion, then its own branch.
- **Usage log is automatic in every fork (L6, upgraded).** Every fork starts
  building a usage log without the user doing anything and without opening
  it. Location: `.claude/usage-log.md` (inside the harness folder, not the
  root). Written by Claude under a rule in the root `CLAUDE.md`, through a
  small script that dates and length-limits each entry. Entries describe the
  shape of a session, never content, and never confidential values. The README
  states it plainly (what it is, where it lives, how to turn it off). The user
  carries it back to this template by hand. Own branch, `dev-usage-log`.
- **`feedback-notes.md` stays separate from `roadmap-notes.md`** (Q1, no
  objection raised).

## Status board (updated 2026-10-30)

Built on three stacked branches, each pushed and **not merged**: merge them in
this order. Each is based on the one before it, because they touch the same
files (`convert.py`, the extractor contract).

| Branch | Contains | State |
|---|---|---|
| `dev-bugfixes` | B1, B2, B3, B5, B7, B8, B10, B11; regression tests and a CI step to run them | built, tested |
| `dev-convert-robustness` | B4 (timeout, fallback, save per file), F2 (`_deferred/`, duplicate check, `--only`, `--dry-run`); control characters stripped from extracted text (found by testing) | built, tested |
| `dev-worker-reports` | F1 (structured report, merge script, schema validation), B6, F6 (tag near-duplicates), reminders to add approved tags and families to the vocabulary files | built, tested |

Open from this file: B9 (tables and equations lost in conversion: depends on
the OCR / vision-read decision), F3, F4 (partly: the batch size is documented
but not yet a `/process-batch` argument), F5, F7, S1 to S7, L1 to L6, and the
`dev-usage-log` branch. OCR is deliberately not in these branches.

**Corrections found while building:**

- **B1's root cause was not carriage returns.** The regex `\s?` after the colon
  matches the *newline* of an empty `tags:` line, so the next line becomes the
  value (`tags: note: notes/x.md`). It reproduced here with a plain LF
  fixture, so it hits every platform, not only CRLF files. The fix is
  the same (`[ 	]?`), and a regression test pins it.
- **An agent definition edited mid-session may not reach a worker launched
  right after.** A worker reported that its contract had no JSON schema and
  invented a different shape. The merge script now rejects a wrong shape
  loudly (it first returned success and merged nothing), and the batch docs
  say to put the schema in the worker prompt.

## 1. Bugs that are real in this template today

These were found and fixed in the derived repo. Check whether the fix has
been ported here: it has not.

| # | Bug | Evidence | In this template now | Fix | Size |
|---|---|---|---|---|---|
| B1 | `--fix` tag-casing pass corrupts entries on CRLF files: `\s?` swallows the line's `\r`, merging an empty `tags:` line into the next field. Broke 29 then 23 stub entries; first blamed on `convert.py`, re-diagnosed a batch later. | log, mid-sweep | **Still present**: `validate_repo.py` has `r"^(tags):\s?(.*)$"` and the same `\s?` in `FIELD_START_RE`. | Use `[ \t]?`, and skip the rewrite when nothing needs fixing. Add a regression test with a CRLF fixture. | small |
| B2 | Validator crashes printing a non-cp1252 character (an `∞` in a paper title) on Windows. | log | Still present. Our own runs print `?`-style replacement characters for an em dash. | `sys.stdout.reconfigure(encoding="utf-8")` at the top of every script that prints. | small |
| B3 | A long filename passes conversion but fails at `git add` once `study/PDFs/`, `study/notes/` and the repo path are added together. Worked around by renaming to a slug. | log | `convert.py` uses the PDF stem for both note path and entry ID, unbounded. | Cap the slug (about 80 chars) and warn when the repo-relative path will exceed a threshold. Keep the full title in `title:`. | small |
| B4 | `pymupdf4llm` hangs on specific PDFs; killing the run lost the catalog stubs of the whole run. Diagnosed by CPU time (slow vs. stuck); routed around with `pdftotext`. | log, autonomous run | `convert.py` has no timeout, and writes the manifest and catalog stubs only **after the whole loop**. | Per-file timeout, automatic fallback to plain text extraction (flagged low-fidelity), and save manifest + stub after **each** file. | medium |
| B5 | Docs say "commit and push after every batch", but notes hold extracted paper text, so a push needs an explicit go-ahead. 40-odd local commits sat unpushed. | log | `batch-orchestration.md` says push after every batch; the copyright warning lives elsewhere. The two never meet. | Say "commit after every batch; push only with the user's go-ahead, because notes contain copyrighted text", and have the coordinator mention the unpushed count every N batches. | small |
| B6 | The `note-extractor` silently dropped `note:`/`source:` from every entry it filled in. Caught by the validator, not by the worker's own report. | log | Our contract forbids editing `catalog.md` and asks for "fields ready to paste", so the *coordinator* hand-merges. Our own test run needed an ad hoc `merge.py` for the same reason. | See F1: a structured report plus a merge script. | medium |

Also from our own test run on 2026-10-30 (not in the log):

- **B7.** Stub metadata prefills `year` from PDF properties: a 1960 paper got
  `year: 2023`. A confident wrong value is worse than a blank. Leave `year`
  empty unless the first page confirms it. (Small.)
- **B8.** A DOI picked up with a trailing underscore
  (`10.1109/ACCESS.2024.3402429_`). Strip trailing punctuation. (Small.)
- **B9.** Tables and equations did not convert (all six tables of one survey
  were empty; equations stripped). This caps what method cards and the
  `row-verifier` can see. Track as a conversion-quality limit; relates to
  the OCR / vision-read decision in `roadmap-notes.md`.
- **B10.** A worker could not read a long note in one `Read` (cap at about
  line 457) and skipped the end. The extractor contract should say to read
  long notes in ranges. (Small.)
- **B11.** The `row-verifier` accepted a quote that supported the *topic*,
  not the specific value (a generic uncertainty sentence for the `input`
  field). Tighten its prompt: the quote must contain the claimed value or an
  unambiguous restatement. (Small, in `.claude/agents/row-verifier.md`.)

## 2. Engine features the log asks for

**F1. Structured worker reports and a merge script.** (Fixes B6, helps F6.)
The log shows ratification doing real work (wrong titles and authors, scope
calls a worker cannot make, tag reconciliation) and also shows the manual
merge being where things break. Proposal: workers end with a machine-readable
block (catalog fields, proposed tags, scope verdict, proposed family); a
script `merge_worker_report.py` writes the fields into the stub and leaves
`note:`/`source:` alone; the coordinator still ratifies the judgment fields
before the script runs. This is the "prefer scripts over AI calls" rule
applied to the one step that is currently hand-pasted. Medium.

**F2. Triage before conversion.** The log asked "are the long documents worth
converting at all?", found a whole book of which one chapter mattered, a
byte-identical duplicate, and a thesis on an out-of-scope layout, and could
only exclude by physically moving files. Today `convert.py` takes no
per-file argument and scans `PDFs/` recursively. Proposal: `PDFs/_deferred/`
ignored by the scan; a hash-based duplicate check against the manifest;
`--only` and `--dry-run` (list what would convert, with page counts, before
converting). Small to medium.

**F3. Acquisition as its own step.** The log split "search and download" from
"convert" twice, found that only about half of the finds can be fetched
(bot-protected hosts, paywalls), and hit a judgment the template does not
cover: an institutional repository can serve a full file with no auth while
its page says "request a copy". Proposal: a `leads.md` tracking each lead
(found, fetched, blocked with DOI, user-fetched, deferred) so blocked items
survive between sessions, and a short rule in
`project_documents/source-access.md` for verifying whether a file is really
open access. Possibly an `/acquire` command. Small (docs and a template file)
to medium (command).

**F4. Batch size semantics.** "Process in batches of 6" is ambiguous between
converting N at a time and handing N to a worker at a time, and only the
second is controllable. Proposal: document that conversion is one pass and
the batch size governs dispatch and ratification; make the size an argument
of `/process-batch`. Small.

**F5. Cross-reference check from root docs into `study/`.** After a crash the
log found a document leaning hardest on a paper whose catalog entry was still
an unfilled stub, and a state vector described two ways; both passed the
validator. A script cannot catch contradiction, but it can catch the first
kind: root files already cite catalogued sources by relative path into
`study/notes/` (root `CLAUDE.md`), so the validator can check each cited note
exists and is not a stub. Small. (Contradiction stays a read; a `/reread
<file>` command that checks a file against its own cited notes is possible
but is judgment, so deferred.)

**F6. Single owner for the tag vocabulary during a batch.** Parallel workers
proposed three names for the same detection concept. F1's structured block
lets a script list near-duplicates across workers before the coordinator
merges (fuzzy match, as the catalog already does for titles). Small, after F1.

**F7. Scope drift warning.** A new project goal (tyre modelling for a later
phase) silently contradicted an out-of-scope line in the scope file that
governs catalog verdicts, and nothing noticed. The planned project
definition document (`roadmap-notes.md`) is the structural fix, since scope
is then derived from it. Meanwhile `/gap-check` can add a step: compare goals
in `decisions.md` / `ideation/` against `scope.md` exclusions. Docs only.

## 3. Structure and documentation the log asks for

**S1. `ideation/` needs stage types and subfolder guidance.** Three document
types recur: a *map* (broad, links to deep-dives, graph with edge semantics
fixed up front), a *deep-dive* (one method family, with an
evidence-by-context grid so "closest layout" and "best validated" can be seen
to be different papers), and a *recommendation* (weighs candidates and
reaches a conclusion, unlike a deep-dive). `ideation/` got its first
subfolder when a topic outgrew one file, and the README had no guidance.
Proposal: three small templates, plus a README paragraph on when a topic
becomes a subfolder (own README, stage files inside). Small.

**S2. The decision-tree diagram style belongs in the repo's Diagrams
convention.** The user named it as a standing preference: every internal node
is a question; every outgoing edge is one possible answer, all drawn as
siblings; only the chosen answer continues downward, every other answer ends
in a leaf naming the alternative it would produce; the recommended path is
styled differently; the bottom is one leaf stating the assembled method. The
reason given: it shows all choices before one is taken, and each edge is a
placeholder for a motivation the team writes when it decides. Add to root
`CLAUDE.md` "Diagrams" (with the reason, per the repo's own rule) and ship a
mermaid skeleton in the recommendation template. Small.

**S3. Decisions carry a fixed block, specs carry assumptions up front.** Two
conventions the user adopted after reviewing prose they called padded: a
fixed *choice / why / not* block per decision, and a "what this rests on"
list at the top of any recommendation or spec (the user's scepticism went
at hidden assumptions: a constant friction coefficient, a quoted bandwidth).
Also: **questions asked in review are answered inside the documents, as
decisions, not only in chat**, so the answer survives the session. Add to the
recommendation and spec templates and to `CLAUDE.md`. Small.

**S4. "Symbols in the spec, numbers in the manual."** A specification derives
with symbols; values live in a separate tuning manual that goes to the
implementation repo. Part of the document triple below. Small once the
triple exists.

**S5. Versioning: one stable file with revision notes.** The rule "a new
version is a new file" invited churn (`v3` renamed back to `v1` the next day;
"old versions stay" had to be amended). The user's rule: the version number
changes only for a bigger change. Proposal: a spec is one stable file with a
revision-notes section; superseded drafts are deleted, decided ones kept.
Docs only.

**S6. A rule and a folder for confidential inputs.** A confidential tyre file
had to stay out of a repo with a shared remote. Proposal: ship a gitignored
`confidential/` folder with a README, the rule that no value or
value-derived number is copied into tracked results, and a check that the
folder is ignored. Small. (Cannot be enforced beyond the ignore rule; the
README must say so.)

**S7. A bench between spec and implementation.** The log shows a simulation
bench living in the study repo for a month (interim, before the plant model
arrived), then moving out; and a rule set it needed: group into subfolders at
about 15 files with a one-line path helper, a results folder that is ignored
by default, figures tracked only when placeholder-only (tyre-file figures
forced into an ignored folder *by the code*), each output tied to a named
decision question with a note on how to read it, and comparisons on an equal
task, not an equal input. This cuts against "implementation lives in a
separate repo", so the phase model needs an explicit *phase 2.5: interim
bench* (see `roadmap-notes.md`). Medium, design first.

## 4. Larger ideas the log supports

**L1. The document triple.** The user split one long paper into three
documents by reader and rate of change: **why** (design rationale with a
broader literature review), **what** (the specification, derives the
equations and holds the analysis, stand-alone from page one), and **how to set
it** (parameter and tuning manual). The specification stayed in the study
repo, the manual went to the implementation repo. This is the spec article of
`roadmap-notes.md` phase 3, and it says the spec article is really two or
three. The current `article-review/` is the first of these. Structure
question for the user: keep sibling folders (`article-review/`,
`article-spec/`, `article-manual/`) with a shared preamble in
`article-common/` once a second article exists, or nest under `articles/`?
Recommendation: siblings now (matches the rename already done), add
`article-common/` when the second one is created, not before. Note that a
shared *bibliography* conflicts with the per-file numbering rule in root
`CLAUDE.md`; share the preamble, keep the reference list per article.

**L2. A requirements engine with provenance.** A run of log entries
(10-05 to 10-07) is one pattern, and the user's rules are specific:
every number traces back to an explicit, **owned** bound ("I accept this
error here to guarantee x"); every proposed bound is marked as needing the
user's yes; draft requirements from the team are placeholders, not sources;
each bound carries a **strength** (physics, rule, measured, inherited draft,
assumption) and a **confidence**; bounds come in **tiers** per milestone; a
budget file holds only top-level design inputs, derived numbers live in the
files that use them (the user rejected an intermediate derived-bounds layer);
and a periodic merge-and-prune pass (22 bounds became 13) under a stated
simplicity principle. This is topic-neutral and clearly phase 2. Proposal:
a `requirements/` folder with a README and one bounds-file template whose
columns are id, bound, value, owner, user-accepted flag, strength, confidence,
tier, used-by; the validator checks that every row has an owner and an
accepted flag. Medium. **Discuss before building.**

**L3. A hub that commissions work from sibling repos.** The user asked for a
prompt to paste into Claude in a different repo (track logs) so that session
summarises what this one needs; later brought findings back. Recurring output
types: a *review of someone else's document* (verdict table plus asks list),
and a *reconcile-against-an-external-draft* cross-walk with a common
error-measure vocabulary. Proposal: a `/handoff-prompt` that carries this
repo's open numbers and file conventions; two small templates. Low priority;
optional module.

**L4. A presentation output type.** A design-review deck was planned before it
was built and cut from 14 slides to 7 to 8 for a 5-minute slot. What worked:
content and figures separate from styling, sources traced to repo files, and
**offering the user's own narrative skeleton as the first question** (the
user re-ordered Claude's feedback-question structure around their outline:
purpose, rules, functionality, system concept, roadmap, tuning, simulations,
testing). Ties to the onboarding slide already in `roadmap-notes.md`.
Proposal: a deck workflow doc (outline first, one feedback question per
slide) and an outline-first rule. Low priority.

**L5. Gates are visible all through the log.** Many places where the user
stopped, read, challenged one step of reasoning, or reframed ("not in the
catalog" is not "doesn't work"; "I'm sceptical"; "this is too padded"). They
are the best evidence for `dev-gate-events`. Two design inputs: (a) the user
turns a fourth question into a discussion, so a gate must allow any question
to become one; (b) the single most useful pre-gate artefact was a list of
*what this rests on*, which is S3. Also: the user **set constraints before a
draft existed** (state estimation, controller choice) rather than correcting a
draft; gates should offer to collect constraints first.

**L6. A log of use, as a first-class convention.** The log exists because the
user asked for it, and it is what produced this file. Proposal: ship an
optional `usage-log.md` convention (gitignored by default, because it holds
project content), with the rule that Claude appends one or two lines per
session shape, tagged *template-relevant*, and that it is redacted before
anything moves into the template. The real log ignores its own "one or two
lines" rule often; the convention should say so and enforce brevity. Small.

## 5. Suggested order

1. **Port the bugs** (B1, B2, B5 doc, B3, B7, B8, B10, B11): small, no design,
   and B1 corrupts data. One `dev-bugfixes` branch.
2. **Conversion robustness** (B4, F2, B3): one `dev-convert-robustness`
   branch, together with the OCR decision from `roadmap-notes.md`, since they
   touch the same script and the same question (what to do with a document the
   converter cannot read).
3. **Worker reports and merge script** (F1, B6, F6): own branch; changes the
   extractor contract.
4. **Docs and templates** (S1, S2, S3, S5, S6, F3, F4, F5, F7): can go on one
   `dev-docs-templates` branch; no engine risk.
5. **Design-first items** (L1 triple, L2 requirements, S7 bench, L3, L4, L5
   gates): discuss, then one branch each; L1 and L5 first, since the phase
   model depends on them.

## 6. Questions (answered 2026-10-30, see "Decisions taken")

1. Is `feedback-notes.md` the right place, or should its contents be merged into
   `roadmap-notes.md`? (I kept them apart: roadmap = where the template is
   going, feedback = what usage says, with a bug table.)
2. L1: sibling `article-*` folders (recommended) or one nested `articles/`?
3. L2: is the requirements engine in scope for the template, or specific to
   how you work in engineering projects? It is topic-neutral, but it is the
   largest item here.
4. Should `usage-log.md` stay local and untracked, or be gitignored explicitly
   so it cannot be committed by accident?
