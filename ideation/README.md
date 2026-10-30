# Ideation

**Everything in this folder is unverified.** Brainstorming, half-formed
ideas, notes from conversations — not literature, not a decision. This is
a structural distinction, not just a disclaimer: a decision is only ever
recorded in `../decisions.md`, and a reference only ever enters
`../study/catalog.md` / `../study/notes/` if it turns out to be real,
verifiable literature that gets independently checked and added properly.

**A decided file stays.** When a recommendation here becomes a decision, the
decision goes in `../decisions.md` (linking back to the recommendation), and
the recommendation stays in place with one line added under its banner:
`Decided in: <decisions.md entry title>`. The full reasoning, including the
options that lost, then survives next to the one-paragraph decision. The banner
still applies to everything else in the file: being decided does not make the
brainstorm literature.

Every file added here must start with this banner:

> **Status: unverified ideation.** This is brainstorming, not literature
> or a decision. Nothing here should be treated as validated fact or
> cited as a literature basis for a decision — see `../decisions.md` for
> what's actually been decided and why.

Rules:

- **Never** cite anything from this folder as `literature basis:` in a
  `../decisions.md` entry.
- If a brainstorm file names something that looks like a real citable
  source (an author name, a specific named method or study), that is a
  signal to go verify it and, if real and relevant, add it properly to
  `../study/catalog.md` — don't leave a real reference sitting
  unverified in prose indefinitely. Flag these explicitly when spotted.

Never delete this `README.md` — it is what makes this folder
self-documenting if the project is picked up again long after the fact.

## Structure, not schedule

This folder holds the **structure** of the work: what the pieces are,
which stage a piece of work belongs to, what data crosses each boundary.
It deliberately does *not* hold the **order**: which decisions block
which stages, and how work parallelizes, live in `../timeline.md`.

The two get confused constantly, and keeping them apart is a deliberate
choice worth defending. A pipeline map and a dependency graph look
superficially alike and answer completely different questions; merging
them produces a diagram that answers neither.

## The stage-file pattern

Once this folder has more than a few files, organize it as:

- **One map file** naming the stages and how they connect — the entry
  point, with the pipeline diagram in it.
- **One deep-dive file per stage**, numbered in pipeline order
  (`1-<stage>.md`, `2-<stage>.md`, …).
- **Un-numbered shared files** for facts or derivations used by several
  stages (a system layout, a model everyone references).

New content goes into the stage it belongs to rather than becoming a new
top-level file. Anything used by two stages gets its own shared file
rather than being duplicated — a duplicated fact is a fact that will
diverge.

## Three kinds of file, with templates

`_templates/` holds a starting point for each kind. Copy one, delete its
comment, fill it in; each already begins with the required banner.

- **Map** (`_templates/map.md`): the entry point for a topic. Names the stages,
  states what each kind of edge means *before* drawing, carries the pipeline
  diagram, and lists the deep-dives, including ones not written yet.
- **Deep-dive** (`_templates/deep-dive.md`): one stage, neutral. The question it
  answers, what crosses its boundaries, the method families, and an
  *evidence-by-context* table. It does not pick a winner.
- **Recommendation** (`_templates/recommendation.md`): weighs candidates against
  stated criteria and reaches a conclusion. The only kind that argues for
  something, and still unverified until the user decides. It carries a
  **decision tree** (root `CLAUDE.md`, "Decision trees"): a table of questions
  and answers is the source, and `study/scripts/build_decision_trees.py`
  generates the diagram from it. Any file in this folder can hold a tree, not
  only a recommendation.

## When a topic needs its own folder

One file per stage is right until a topic outgrows it: it splits into several
surveys, or a stage's deep-dive passes what one file can hold. Then the topic
gets a subfolder, `<topic>/`, with its own `README.md` stating what belongs in
it, its own map, and its own numbered deep-dives (numbering restarts inside).
The top-level map links to the subfolder's map. Do not nest further: a
subfolder inside a subfolder means the topic should have been split earlier.

## Conventions

**Diagrams.** Stage files describe data flow and ordering, which is
exactly what the repo-wide diagram convention is for (root `CLAUDE.md`):
the map file gets the pipeline diagram, and each stage file gets a
diagram of what crosses that stage's boundaries. Short labels; the prose
around each diagram must stand alone.

**Citations.** If a brainstorm references an external source, use the
repo-wide convention — numbered `[1]`, `[2]` markers in order of first
appearance and a `## References` section at the bottom, numbering local
to the file. Links between sibling ideation files stay ordinary markdown
links, not numbered citations. Citing a source here does not promote the
file's content out of "unverified": the banner still applies.
