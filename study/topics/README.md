# Topic dossiers

Don't pre-build these for every tag. Build one here the first time a
query actually needs to cross-reference a dense cluster of documents
against each other. A dossier is a real synthesis, not a list: which
sources agree, which contradict each other, which approach each uses,
open questions across the set.

Once it exists, it becomes a standing asset — the next query about that
topic reads the dossier instead of re-deriving the comparison from raw
notes. Update it when new relevant PDFs are added.

Suggested filename: `topics/<topic-tag>.md`.

Dossiers are the one place in this repo where nothing downstream
re-checks the work: a wrong recommendation propagates into
`../../decisions.md` and is never caught. That is why this is
synthesist-tier work — see `../ai_instructions/delegation.md`, and the
`dossier-synthesist` agent, which drafts a dossier for review rather than
writing it directly.

## Shape of a dossier

Neutral placeholder — the structure, not the content:

```markdown
# <Topic>

What question this dossier answers, and which entries it covers.

## The families

<A mermaid diagram of the method families being compared and what each
needs as input. This goes BEFORE the table: the table is dense and the
taxonomy is invisible in it. Short node labels, a few words each; the
prose around it must stand alone for a reader without mermaid support.>

## Comparison

| Method | Needs as input | Validated on | Reported result | Source |
| --- | --- | --- | --- | --- |
| … | … | … | … | `notes/x.md` <!-- page: 4 --> |

## Recommendation

<Which holds up best for this study's stated purpose, and under what
conditions that flips. Not "it depends.">

## Open questions

<Required — see below.>
```

Every number cites its note file and page marker (`<!-- page: N -->`).
A claim that can't be cited is dropped, or explicitly labelled as your
own inference.

## Required: the diagram and the Open questions section

**The families diagram** is the single highest-value thing in a dossier
and the repo-wide diagram convention (root `CLAUDE.md`) applies here by
default. `../scripts/validate_repo.py` warns about a dossier with no
mermaid diagram at all — advisory, never a build failure, since a topic
with no real taxonomy to draw shouldn't have one invented for it. An
unbalanced fence *is* a hard error, because a broken diagram renders the
rest of the file as garbage.

**`## Open questions` is mandatory** and is checked as a hard failure.
What hasn't been compared yet, what claims are only qualitative or
single-source rather than a real head-to-head. Write it specifically
enough that someone could go source a document to close each item.

## Supporting files

- `vocabulary.md` — canonical tag names. Check before tagging a new
  document or inventing a term for a dossier's comparison table.
- `gaps.md` — a running aggregation of every dossier's "Open questions"
  section, cross-referenced against `../ai_instructions/scope.md`. After
  adding or updating a dossier, run
  `python scripts/build_gaps_index.py` to regenerate the auto-aggregated
  part — don't hand-copy the section, the script does it
  deterministically.
