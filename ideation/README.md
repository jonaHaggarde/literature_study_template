# Ideation

**Everything in this folder is unverified.** Brainstorming, half-formed
ideas, notes from conversations — not literature, not a decision. This is
a structural distinction, not just a disclaimer: content only ever moves
*out* of `ideation/` into `../decisions.md` once it has actually been
decided, and only ever moves into `../study/catalog.md` /
`../study/notes/` if it turns out to reference real, verifiable
literature that gets independently checked and added properly.

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
