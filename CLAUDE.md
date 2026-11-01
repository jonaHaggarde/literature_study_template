# Repo conventions

Repo-wide conventions for this project. `study/CLAUDE.md` covers nothing
but the read-order pointer for the literature-review engine, so the two
files cannot contradict each other — this one owns everything else.

## What lives where

This repo has two halves, and keeping them apart is the point:

- **`study/`** — the literature-review engine: the catalog, the notes
  generated from PDFs, topic dossiers, the scripts, and the instructions
  Claude follows when operating it. Self-contained and replaceable as a
  unit. Nothing project-specific belongs in here except
  `ai_instructions/scope.md`.
- **Everything else at the root** — the actual project: decisions,
  brainstorming, background explainers, meeting notes, the schedule, and
  material handed down from outside. This is where a real project grows,
  and it grows fast.

Routing, for a session starting at the repo root:

- Starting a project, or `scope.md` still a placeholder → `/intake`, then the definition
  article (`articles/definition`), then the user accepts it (the `definition` gate), then
  `scope.md` is written from it, and only then are papers gathered. Always steer the user to
  this route; the original route (filling in `scope.md` together) remains as a fallback.
  See `intake/README.md`.
- Where things stand, what is next, what is missing → `/where`: a picture of the gates, the
  intake coverage, the catalog and the articles, drawn by `study/scripts/status.py` from the
  files. It only shows; every decision still happens here in chat.
- Literature work (processing PDFs, answering a question from the
  catalog, building a dossier, gap-flagging) → read
  `study/ai_instructions/README.md` and follow its read order. Working
  with `study/` as the working directory (`cd study`) is also fully
  supported and is what `study/CLAUDE.md` is for.
- Project work (a decision, a brainstorm, an explainer, meeting notes,
  the timeline) → the relevant root folder's own `README.md` states what
  belongs in it and what doesn't. Read that before adding a file.
- Requirements (optional module, for projects that build something) →
  `requirements/README.md`. Requirements are staged: top-level facts and goals
  belong in the project definition and `scope.md`, version 1 comes **after** the
  review article, and lower-level requirements come after the concept decision
  they depend on. If asked for requirements before the survey is finished, say
  why that tends to drive an unreasonable design (the README has the reasoning),
  offer top-level facts and `TBD` entries instead, and let the user decide; do not
  refuse. A value nobody knows yet is written `TBD`, with an owner, a resolve-by
  milestone and what it waits on. Never present a draft from outside, or an
  assumption, as a source of truth.
- Writing the study up as a literature review article (the comparison
  table, introduction, related work) → create the article if it does not exist
  (`/new-article review`), then `articles/review/README.md`, then follow
  `articles/review/workflow.md` (the `/article` command runs that sequence and
  reports what is missing). The article is a view of `study/`, written from
  the dossiers; findings are recorded in `study/` first and never only in
  the article. **The review article contains no decisions**: it reports
  what the literature says, never what the project chose or recommends.
  Deciding the product is a later phase (`decisions.md`, `ideation/`),
  kept out of the article so the review stays a neutral record of the
  field.

See `README.md` for the full layout and the reasoning behind the split.

## Citations outside `study/`

Files in the root-level folders (`ideation/`, `meetings/`, `theory/`,
`decisions.md`, and similar; the LaTeX files in `articles/review/` follow the same
rule with `\cite` and a `thebibliography` list) that reference a specific external source —
a catalogued paper, a document provided by the client or institution, or
similar — use numbered inline markers (`[1]`, `[2]`, … `[n]`) **in order
of first appearance**, with a `## References` section at the bottom of
the file listing each source **once**: author(s), year, title, and a
relative path (into `study/notes/` for catalogued papers,
`intake/received/` for provided material, etc.).

Numbering is **local to each file**, not shared across files.

This does **not** apply to plain cross-references between sibling files —
one ideation stage file linking to another stays an ordinary relative
markdown link, not a numbered citation.

`study/` keeps its own existing conventions (`study/catalog.md`,
`study/notes/`); this standard is for everything outside it.

Two parts of that rule are the ones that get lost, so they are worth
stating separately:

- **The two-tier distinction is the substance of it.** External source →
  numbered citation with a References entry. Sibling file → plain link.
  Without that split you either get a References section cluttered with
  internal links, or external claims with no traceable source — and the
  second is the one that damages the work.
- **Per-file numbering, not global.** Making numbering repo-wide so
  `[7]` always means the same paper is tempting and wrong: every edit to
  any file would then renumber every other file. Per-file numbering keeps
  each document independently editable, which is what matters when
  several people edit in parallel.

Set this convention before anyone writes prose. Retrofitting citations
into files that already accumulated inconsistent references is avoidable
work, and it is the mistake this template ships pre-solved.

## Diagrams

**When a document describes a process, a method, an algorithm, a data
flow, or an ordering, it gets a mermaid diagram.** The audience for most
documents here is a teammate who hasn't seen the concept before, and the
diagram is usually the part that does the actual teaching. Mermaid
renders natively on GitHub and in most markdown viewers, so this costs
nothing to read.

Where this applies by default:

- **`theory/` explainers** — lead with a diagram of the mechanism, then
  explain it. A document comparing two concepts benefits from two small
  diagrams side by side more than from any amount of prose.
- **`study/topics/` dossiers** — a diagram of the method *families*
  being compared, and what each needs as input, placed before the
  comparison table. The tables are dense and the taxonomy is invisible
  in them; this is the single highest-value diagram in the repo.
- **`ideation/` stage files** — the pipeline map, plus a diagram per
  stage of what crosses that stage's boundaries.
- **`timeline.md`** — a dependency graph of which decisions block which
  stages. This is a genuinely different diagram from the pipeline map and
  should not be merged with it.
- **`study/workflow-diagram.md`** — already exists.

Style rules, learned the hard way:

- Keep node and edge labels to a few words. Put the explanation in the
  prose immediately around the diagram, not packed into the labels — a
  diagram whose nodes are sentences is worse than no diagram.
- Keep an edge label only when it says something the structure doesn't
  already make obvious.
- Every diagram gets a sentence before it saying what question it
  answers, and the surrounding prose must stand alone. Anything rendering
  the file without mermaid support — a plain-text grep, a subagent
  reading it — still has to get the point.
- Prefer several small diagrams over one large one. A diagram nobody can
  read at a glance has failed at the only thing it was for.

**Decision trees: one more named style, for any document that weighs
alternatives and reaches a conclusion** (a recommendation, the reasoning behind
a `decisions.md` entry). Every internal node is a **question**, never a
statement. Every outgoing edge is **one possible answer**, and *all* the real
answers are drawn as sibling edges from the same node, not only the one that
wins. Only the chosen answer continues downward to the next question; every
other answer stops at once in a leaf naming the method it would have given
(solid if it was examined, dashed if it was only listed). The recommended path
is styled differently from the rejected leaves, and the bottom of it is a
single leaf stating the assembled recommendation.

**Why this and not a linear chain or a pros-and-cons list:** it shows every
choice *before* one is taken, so a reader can see what was on the table and what
was never examined, and each edge is a placeholder for the reason the team
gives when it decides. The tree doubles as that decision's checklist, not only
an illustration of a conclusion already reached in the prose.

**The table is the source, the diagram is derived.** The tree is written as a
table (`ideation/_templates/recommendation.md` has the columns), and
`study/scripts/build_decision_trees.py` generates the mermaid from it. Never
edit the diagram by hand: it is overwritten, exactly like
`study/catalog-index.md`. The validator checks the table (one chosen answer per
question, every question reachable) and reports how many rejected alternatives
were actually examined, so a decision resting on options nobody looked at is
visible as such.

**The convention is advisory.** `study/scripts/validate_repo.py` checks
that fenced ` ```mermaid ` blocks are *balanced* — that is a hard error,
since a broken fence renders as garbage — and warns when a dossier or a
`theory/` file has no diagram at all. It never fails a build for a
missing diagram. A document with no process, ordering, or structure to
draw should not be forced to invent one, and a hard check on a judgment
call is the kind of check people start routing around.

## Writing articles

Before writing or editing the text of an article or a gate report, read
`study/ai_instructions/article-style.md`. The one failure it exists to prevent is the same
content twice in different words (in a sentence, a section, or across sections); that style
helps in chat and costs the reader time in an article. After writing, run
`python study/scripts/style_check.py <article>`, fix every problem it reports and decide each
judgment call. A phrase the user flags in a review goes into
`study/ai_instructions/style-phrases.txt`.

## Articles are never edited silently

Every article under `articles/` has a version history (`articles/README.md`). After a
substantial edit to an article (a claim, number, source, equation, table row or structure),
run `python study/scripts/article_version.py <name> edit --summary "one line"` in the same
turn, and tell the user which article moved to which version.

- **Never run `review` or `accept`.** The major number is the user's, bumped after their own
  review.
- **Run `gate.py open`, `gate.py close` or `gate.py skip` only when the user tells you to, in
  that message.** "Looks good" or "I have reviewed it" is not that: say what the command is
  and ask. Each sits behind a permission prompt, which is the user's second confirmation.
  `close` is `accept` plus the gate record, so no `review` comes before it; `review` is for a
  review that is not at a gate.
- **After acceptance, `edit` is refused.** An accepted article changes only when the user
  asks, with `refine --summary "..."`, which prompts them each time. Do not refine an
  accepted article on your own initiative.
- **Scope follows the definition, but not at once.** After a refinement of the definition,
  `study/scripts/scope_sync.py check` will say `scope.md` is stale. Do not update it after
  each refinement: say so, suggest updating it, and do it when the user says they are ready.
  If they forget, warn them once at the start of literature work.

- **Gates are the user's decision.** `/gate` briefs them (facts from `gate.py briefing`, your
  own critique, both short) and `/understand` runs the check. Neither blocks the gate; the
  user passes it by running `gate.py close` or by telling you to. There is no gate report.

The reason for the gate rule: the decision to pass a gate is the user's, not the typing of the
command, and a command run only on their word in chat, behind a prompt, keeps it deliberate
without making them type it every time.

The reason: the user reads these articles on paper at gates and must be able to trust that
what they reviewed is what they are shown.

## Assumptions made along the way

When the user writes "assume", "let's assume" or similar, do not file it on a guess. Ask one
short question with a recommendation: where does it live?

| Level | Test | Where | Workflow to run, without asking again |
|---|---|---|---|
| Top-level | It changes the problem, goal, scope or constraints | a `suspicion` row in `intake/intake.md`, source `study <date>`; it reaches the definition when the user asks for a refinement | `intake_check.py --next` for the ID, add the row, `intake_check.py`, then say that the definition's register is behind and `scope.md` may be |
| One article | It matters to that article only (an algorithm or specification choice) | that article's own assumptions section: a row with an ID, what breaks if false, the date | edit the section, `article_version.py <name> edit` (or `refine` if accepted, which prompts the user), rebuild, `style_check.py` |
| This chat only | A working premise with no lasting effect | nowhere | none |

The reason: a register that took every small assumption would bury the top-level ones, and one
that took none would hide what a later article rests on. An assumption in a definition changes
what the study is about, so it goes through intake, where the trace to what the user said stays
whole.

## Reasoning travels with the rule

**Every non-obvious default in this repo carries its reasoning next to
it.** A convention whose rationale is undocumented gets silently reverted
by the next person who finds it inconvenient. If you add a convention
here, add why — and if you find one whose why is missing, that is a bug
worth fixing rather than a licence to drop it.

## Spending tokens: page images, and fanning out subagents

Scanned PDFs are OCR'd by script, which costs no tokens. OCR gets equations and
tables wrong, and the only fix is to have a model look at the page image, which
costs thousands of tokens per page (not yet measured). So that is rationed, by a process and not by
good intentions (`study/ai_instructions/vision-budget.md`):

- **Never read a page image, never render a page, and never launch the
  `page-reader` agent outside `/vision-read` and its ticket process.** No ticket
  means no images. One `page-reader` at a time, never in parallel.
- **Never run `approve` without the user's clear go-ahead, and never edit
  `vision-budget.md` or the `ask` rules in `.claude/settings.json`.** The limits
  are the user's.
- **More generally, before launching more than three subagents for one task, tell
  the user how many and a rough cost, and wait for a yes.** A command the user
  invoked that defines its own fan-out (`/process-batch` with its batch size)
  counts as that yes; anything you decide to fan out yourself does not.

## Usage log

Every repo made from this template keeps a short running record of how it is
actually used, at `.claude/usage-log.md`. It exists so the template can be
designed from real use instead of guesses about how people work. The user is
not expected to read it, and nothing in normal work reads it.

**When to add an entry.** At the end of a turn in which one of these happened,
append one line:

- the user asked for a kind of thing the template has no step for (`request`);
- the user asked for a structural change, not a tweak (`rework`);
- a template convention fit badly or needed a workaround (`friction`);
- a script, check or instruction misbehaved (`bug`);
- the user said, in passing, what the template should have (`idea`).

Routine work (processing a document, answering a question, a small edit) is not
logged. Most sessions log nothing or one line; ten lines from one session means
the log is being used as a transcript, which defeats its purpose.

**How.** `python .claude/log_usage.py --kind friction "what happened, in a
line"`. The script dates the entry, holds it to one short line, and refuses text
that looks like content (an address, a URL, a path, a secret). Do it in the same
turn, without interrupting the user. Never edit or delete earlier entries.

**What never goes in.** Anything about the project's subject: no names, no
quantities, no file contents, no confidential material. If a line would only make
sense to someone who knows the project, it does not belong. The log records the
shape of a session, not what it was about.

**Off in the template's own repo.** If `.claude/no-usage-log` exists, logging is
switched off and the script refuses (it exits normally and writes nothing). That
file is deliberately not committed, so repos made from the template log as usual
and the template's own development does not. Creating the file is also the easy
way for anyone to turn logging off.

**Honesty about what this is.** The rule is followed because it is written here,
not enforced by a hook, so entries will sometimes be missed. That is acceptable:
the log is a sample of how the template gets used, not an audit. It is committed
with the repo, so the user can see exactly what is recorded. To turn logging off,
create that file or delete this section; the README says the same in plain words.

## Git

### Commit style

Do not add any "Co-authored-by" or AI attribution lines to commit
messages.

## Assumed assistant

This template assumes Claude Code specifically, not a generic "AI coding
assistant" — docs throughout say "Claude," `study/CLAUDE.md` relies on
Claude Code's auto-load behavior for onboarding, and `.claude/` ships
agent definitions and slash commands in Claude Code's own format. If a
fork of this template is ever used with a different tool, adapting the
wording, the auto-load mechanism, and `.claude/` is that user's
responsibility, not something this template hedges for by default.
