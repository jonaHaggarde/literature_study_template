# meetings/

Meeting notes, one file per counterparty plus `internal.md` for the
team's own meetings. Splitting by counterparty rather than by date is
deliberate: the question people actually ask is "what did we agree with
*them*, and what is still open on their side" — which is impossible to
answer from a folder of dated files.

**What belongs here:** what was said, what was agreed, what was asked,
and by whom. Each file keeps three sections (see the stub below): open
questions, a decisions log, and the chronological log itself.

**What does not belong here:**

- **Not the decision record itself.** A decision reached in a meeting is
  logged here as *what happened*, then written up properly in
  `decisions.md` with its literature basis and project context. This
  folder is the minutes; `decisions.md` is the reasoning.
- **Not documents received in a meeting.** Those go in
  `project_documents/`; reference them from here by relative path.
- **Not speculation from a meeting.** An idea floated but not agreed is
  brainstorming — `ideation/`.

## Files

- `internal.md` — the team's own meetings.
- `<counterparty>.md` — one per external party (client, supervisor,
  institution). Rename the stub in this folder rather than adding a
  differently-shaped one.

## Conventions

Cite external sources by number per the repo-wide convention (root
`CLAUDE.md`): `[1]`, `[2]` inline, `## References` at the bottom,
numbering local to the file. A meeting note that quotes a figure from a
provided document should say where the figure came from — this is the
folder where undocumented numbers most often enter a project.
