# project_documents/

**Only material handed down from outside this project** — from a client,
a customer, a university, an institution, or a predecessor project. A
brief, a requirements document, a proposal you were given, a
specification, a user manual for equipment you were handed.

## The exclusion rule

**Nothing you authored yourself belongs here.** This is the rule that
keeps the folder useful, and it is the one that gets broken first: a
self-authored tracker, a status document, or a working draft lands here
because it "feels official," and from then on nobody can tell provided
ground truth from the team's own output. Those go elsewhere:

| If you wrote it… | It goes in |
| --- | --- |
| a decision or conclusion | `../decisions.md` |
| an unverified idea | `../ideation/` |
| an explainer of a concept | `../theory/` |
| minutes or an agreement | `../meetings/` |
| a schedule or blocker list | `../timeline.md` |
| a summary of a paper | `../study/notes/` + `../study/catalog.md` |

The value of this folder is precisely that everything in it can be
trusted as *given*, not derived. A folder whose contents are half
provided and half self-authored has no value at all.

## Contents

Keep files here in their original form where that makes sense (a PDF
brief is fine to drop in as-is); otherwise kebab-case `.md`. Do not edit
provided documents — annotate in a separate file next to them if
something needs commenting on, so the original stays verbatim.

- `source-access.md` — where papers can actually be sourced from
  (institutional/subscription access, open access, discovery tools), so
  the literature study's gap-flagging recommendations point somewhere
  real. This one is the exception to the rule above: it describes *your*
  access, so it is self-authored — it lives here because it is
  personal/institutional ground truth rather than a project conclusion,
  and it must be re-specified by anyone who forks this template.

<!-- List further documents here as they're dropped in, one line each
     with a short description of what it is and who provided it. -->

## How this relates to `../study/ai_instructions/scope.md`

`scope.md` is a short, Claude-maintained *distillation* of what is in
here, kept small enough to read in full at the start of every literature
session. This folder is the source of truth — when a document here
changes, or a conversation reveals `scope.md` is stale or incomplete,
update `scope.md` to match. Don't let the two drift apart.

## Citations

If a file you add here (an annotation, an index) references an external
source, use the repo-wide convention: numbered `[1]`, `[2]` markers in
order of first appearance and a `## References` section at the bottom,
numbering local to the file. See the root `CLAUDE.md`. Provided
documents themselves are of course left exactly as they arrived.
