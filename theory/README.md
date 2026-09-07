# theory/

Explainers of background concepts, written for a teammate who hasn't
seen them before. If half the team knows a method cold and half has
never met it, the explainer that closes that gap goes here.

**What belongs here:** teaching material. A walkthrough of a technique
the project depends on, a comparison of two concepts the team keeps
conflating, a derivation someone will otherwise re-derive from scratch
next month.

**What does not belong here — the exclusion rule matters more than the
purpose statement:**

- **Not claims about this project.** An explainer says how something
  works in general. The moment it says what *we* should do, it is a
  decision (`decisions.md`) or a brainstorm (`ideation/`).
- **Not literature summaries.** A summary of one specific paper belongs
  in `study/notes/` and `study/catalog.md`; a synthesis across several
  belongs in a `study/topics/` dossier. An explainer here draws on those
  but is written to teach a concept, not to report a source.
- **Not project-provided material.** Anything handed down from outside
  goes in `project_documents/` untouched.

## Conventions

**Lead with a diagram.** These files describe mechanisms, which is
exactly the case the repo-wide diagram convention is for (root
`CLAUDE.md`). A concept-comparison explainer generally wants two small
diagrams side by side rather than one large merged one. The prose around
each diagram must stand alone for anyone reading the file as plain text.

**Cite external sources by number.** Every explainer that draws on a
catalogued paper or provided document uses the repo-wide citation
convention: inline `[1]`, `[2]` markers in order of first appearance,
plus a `## References` section at the bottom listing each source once
with a relative path (`study/notes/...`, `project_documents/...`).
Numbering is local to this file. Plain links to sibling files are *not*
citations and stay ordinary markdown links.

## Shape of an explainer

Neutral placeholder — the shape, not the content:

```markdown
# <Concept>, and how it differs from <the thing the team already knows>

The question this file answers: <one sentence>.

## The mechanism

<diagram>

<Prose walking through the diagram, standing alone without it.>

## Where it differs from <familiar thing>

<diagram, or a short table>

<What changes in practice, and when the difference actually matters.>

## When you would reach for it here

<One short paragraph tying it to this project — without deciding
anything. A decision goes in decisions.md.>

## References

1. Author, A. (Year). *Title*. `study/notes/path.md`
```
