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

- Literature work (processing PDFs, answering a question from the
  catalog, building a dossier, gap-flagging) → read
  `study/ai_instructions/README.md` and follow its read order. Working
  with `study/` as the working directory (`cd study`) is also fully
  supported and is what `study/CLAUDE.md` is for.
- Project work (a decision, a brainstorm, an explainer, meeting notes,
  the timeline) → the relevant root folder's own `README.md` states what
  belongs in it and what doesn't. Read that before adding a file.

See `README.md` for the full layout and the reasoning behind the split.

## Citations outside `study/`

Files in the root-level folders (`ideation/`, `meetings/`, `theory/`,
`decisions.md`, and similar) that reference a specific external source —
a catalogued paper, a document provided by the client or institution, or
similar — use numbered inline markers (`[1]`, `[2]`, … `[n]`) **in order
of first appearance**, with a `## References` section at the bottom of
the file listing each source **once**: author(s), year, title, and a
relative path (into `study/notes/` for catalogued papers,
`project_documents/` for provided material, etc.).

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

**The convention is advisory.** `study/scripts/validate_repo.py` checks
that fenced ` ```mermaid ` blocks are *balanced* — that is a hard error,
since a broken fence renders as garbage — and warns when a dossier or a
`theory/` file has no diagram at all. It never fails a build for a
missing diagram. A document with no process, ordering, or structure to
draw should not be forced to invent one, and a hard check on a judgment
call is the kind of check people start routing around.

## Reasoning travels with the rule

**Every non-obvious default in this repo carries its reasoning next to
it.** A convention whose rationale is undocumented gets silently reverted
by the next person who finds it inconvenient. If you add a convention
here, add why — and if you find one whose why is missing, that is a bug
worth fixing rather than a licence to drop it.

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
