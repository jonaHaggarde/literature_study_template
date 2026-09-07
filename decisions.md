# Decision log

Real decisions or conclusions this project has actually produced,
grounded in the literature in `study/catalog.md` / `study/notes/` but
kept clearly separate from it. Nothing here is literature — this is
*your* synthesis, informed by the literature plus context the literature
cannot supply (constraints, priorities, judgment calls).

Not a place for requirements or a spec. This is a general decision /
conclusion log, useful for any project that needs to go beyond "here's
what the literature says" into "here's what we're doing about it and
why." If this project never needs that, this file can stay empty.

Copy this block per decision:

```markdown
## <short decision or conclusion title>
- date:
- literature basis: <cite study/topics/ or study/notes/ + page marker, or
  "none — no literature covers this, see study/topics/gaps.md">
- project context (from you, not the literature): <constraints/judgment
  driving this>
- decision / conclusion:
- rationale: <synthesis of the above>
- revisit if: <what would invalidate this>
```

**Why the split between "literature basis" and "project context":** the
literature-basis part should be re-derivable from `study/notes/` and
`study/topics/`, and held to the same citation standard as everything
else in this repo. The project-context part is *not* in any source
document — it is your constraints, judgment, or priorities — and must
stay clearly separate so a future read of this log never mistakes "this
is what I decided given my own constraints" for "this is what the
literature says." Keeping the two apart is the single most useful
convention in this file; a decision that blurs them cannot be audited
later.

**Decisions are living entries, not an append-only log.** When new
context changes your reasoning on something already decided, update that
entry in place (with a short changelog line noting what changed and why)
rather than leaving stale reasoning next to new reasoning that
contradicts it.

**Never cite `ideation/` as literature basis** — see `ideation/README.md`.
If something brainstormed there turns out to be right, verify it against
real literature first and cite that, or label it clearly as your own
reasoning rather than an established finding.

**Citations.** This file follows the repo-wide convention for anything
outside `study/`: numbered `[1]`, `[2]` markers in order of first
appearance and a `## References` section at the bottom listing each
source once with a relative path. Numbering is local to this file. See
the root `CLAUDE.md`. In practice the `literature basis:` line and the
References section carry the same sources — that is fine, the line says
*which* claim rests on what, the section says where to find it.

---

Empty for now — no decisions logged yet.
