# literature_study_template

A template repo for running a focused, AI-assisted literature study on a
single topic, and for the project that grows around it. Fork or download
it per new topic/project — it is deliberately scoped to **one study at a
time**, not a shared multi-project knowledge base.

The idea: drop PDFs in, drop the material you were handed in, tell Claude
what the study is actually about, and let it build a searchable,
citation-grounded catalog of the literature — one that tracks its own
knowledge gaps against your stated scope instead of silently pretending
to be complete.

## Topic-agnostic in content, opinionated in method

This is the line the whole template walks, and it is worth stating up
front so nobody has to guess:

- **Nothing applied ships.** No robotics, no medicine, no law, no
  economics. The template forks cleanly for any subject:
  `study/topics/vocabulary.md` ships empty with an explanation of what a
  good tag vocabulary looks like, `study/ai_instructions/scope.md` is a
  placeholder, and no example in any instruction file requires domain
  knowledge to follow.
- **The working method ships fully formed.** Scope-first onboarding, the
  derived-files-never-hand-edited discipline, the fresh-agent worker
  contract, the model tiering, the diagram convention, the summary rule,
  the literature-basis / project-context split, the root/`study/`
  separation — all of it opinionated, and all of it shipping with its
  reasoning attached, because a convention whose rationale is
  undocumented gets silently reverted by the next person who finds it
  inconvenient.

The test for anything added here: **would this still be right for a
literature study about eighteenth-century agriculture?** If yes, it
belongs in the template. If it only makes sense for one field, it belongs
in the fork.

## Layout: the root / `study/` split

The template ships this split from day one, because every real project
grows content that is not literature review, and putting it inside
`study/` pollutes the one part that was meant to stay reusable.

```
CLAUDE.md               repo-wide conventions; routes literature work into study/
README.md               this file
decisions.md            decision log, with the literature-basis / project-context split
timeline.md             milestones, dependencies, blockers
project_documents/      material handed down from outside — nothing self-authored
ideation/               unverified brainstorming, never citable as literature
theory/                 explainers of background concepts, for teammates
meetings/               one file per counterparty, plus internal.md
study/                  the literature-review engine — self-contained
.claude/                agent definitions, slash commands, permissions
.github/workflows/      CI: runs the structural validator on every push
```

Each of those folders ships with a `README.md` and little else — git
cannot track an empty directory, and the README is the valuable part
anyway. Each states not just what belongs in it but what **doesn't**: in
practice the folders that stay clean are the ones with an explicit
exclusion rule.

`study/` is the engine — catalog, notes, dossiers, scripts, and the
instructions Claude follows. Keeping it self-contained is deliberate:
it is what makes it possible to drop a newer version of the engine into
an existing project later.

## What ships in `.claude/`

Three agent definitions and three slash commands, all in Claude Code's
own format:

| | What it is |
| --- | --- |
| `corpus-scout` | Retrieval. Large inputs, tiny outputs, returns `file:line` citations and short quotes rather than text. |
| `note-extractor` | Fills a catalog entry and note sections for a named list of documents. Carries the full worker contract. |
| `dossier-synthesist` | Drafts one topic dossier: comparison table, recommendation, open questions. |
| `/lit` | Answer a literature question — scout locates, the session concludes. |
| `/process-batch` | The full batch loop: parallel workers, central merge, ratify, validate, commit. |
| `/gap-check` | Audit coverage against scope and report what is genuinely thin. |

`study/ai_instructions/delegation.md` explains what each is for, why the
model tiers sit where they do, and the rule that matters most — that the
primary reason to delegate is keeping large inputs out of the
coordinating session's context, with the model tier a second-order saving
on top of that. Any fork that doesn't want these can delete `.claude/`;
the workflow still works, it just becomes advice rather than
infrastructure.

## Starting a new study from this template

1. **Use "Use this template" on GitHub, not fork.** If this repo is
   marked as a GitHub template repository (Settings → General → Template
   repository), click "Use this template" to get an independent new repo
   with no shared git history and no link back here — a much better fit
   for a personal one-off study than a fork, which stays attached to this
   repo's network. Otherwise, download/clone and re-init git yourself.
2. Rename the repo for your topic.
3. Run the one-time setup:
   ```powershell
   cd study
   .\scripts\setup.ps1        # or ./scripts/setup.sh on macOS/Linux
   ```
4. Drop your source PDFs into `study/PDFs/`.
5. Drop material you were handed from outside — a brief, a proposal, a
   specification — into `project_documents/`, and check
   `project_documents/source-access.md` against your own situation. It
   ships with a real, working list of access channels rather than a
   placeholder; edit it where yours differ.
6. **Open Claude Code**, either at the repo root (the root `CLAUDE.md`
   loads and routes literature work into `study/`) or with `cd study`
   first (`study/CLAUDE.md` loads and points straight at the operating
   manual). Then just say you're ready to start. Claude's first job is
   helping you fill in `study/ai_instructions/scope.md` — everything
   downstream, gap-flagging in particular, depends on that being real
   rather than a placeholder.
7. Then work through `study/README.md`'s "Adding PDFs" section, or run
   `/process-batch`.

For a graphical walkthrough of the whole process — onboarding, the PDF
batch pipeline, how a question gets answered, which script touches which
file — see `study/workflow-diagram.md`.

## Copyright: read this before making a repo public

**Keep the repo private if your sources are copyrighted.**
`study/PDFs/` is gitignored, but `study/notes/` holds substantial
extracted text from those same PDFs and *is* committed. That is fine for
a private study and not fine to publish. Check the repository's
visibility before pushing. `convert.py` repeats this warning every time
it runs, because it is the highest-consequence mistake available here.

## CI

A GitHub Actions check (`.github/workflows/validate.yml`) runs
`study/scripts/validate_repo.py` on every push, so structural mistakes —
a broken catalog entry, a stale derived index, a non-canonical tag used
across several entries, an unbalanced mermaid fence — surface
automatically without needing a Claude session to catch them. It is
cheap, and it is what stops the derived files from quietly rotting.
