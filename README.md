# literature_study_template

A template repo for running a focused, AI-assisted literature study on a
single topic. Fork or download this repo per new topic/project — it is
deliberately scoped to **one study at a time**, not a shared multi-project
knowledge base.

The idea: drop PDFs in, drop your own project documents in, tell the AI
what the study is actually about, and let it build a searchable,
citation-grounded catalog of the literature — one that tracks its own
knowledge gaps against your stated scope instead of silently pretending
to be complete.

Everything that matters lives under `study/` — see `study/README.md` for
setup and day-to-day usage, and `study/ai_instructions/README.md` for how
an AI assistant should operate in this repo. A GitHub Actions check
(`.github/workflows/validate.yml`) runs `study/scripts/validate_repo.py`
on every push, so structural mistakes (a broken catalog entry, a stale
quick-reference list) surface automatically, without needing an AI
session to catch them.

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
5. Drop any of your own project materials (a project description, a
   brief, existing drafts — anything that defines *why* this study exists)
   into `study/project_documents/`.
6. Open Claude Code (or another AI coding assistant) in this repo and ask
   it to read `study/ai_instructions/README.md` and get started. Its first
   job will be helping you fill in `study/ai_instructions/scope.md` —
   everything downstream (gap-flagging in particular) depends on that
   being real, not a placeholder.
7. Then work through `study/README.md`'s "Adding PDFs" section.
