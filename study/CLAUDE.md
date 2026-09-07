# study/ — read this before anything else in this folder

This is the literature-review engine of a single-topic study. Before
doing *anything* else in this folder — including a bare "let's begin"
with no other context — read `ai_instructions/README.md` and follow its
read order (`scope.md` → `catalog-schema.md` → `workflow.md`).

Do this even if the user hasn't mentioned PDFs, scope, or any of this
explicitly. If they've just opened this folder and said something like
"let's start" or "go," that instruction *is* "read ai_instructions/ and
follow the onboarding flow described there" — don't wait to be told
literally.

In particular, check `ai_instructions/scope.md` first: if it still has
the `<!-- placeholder -->` marker at the top, your first task this
session is helping the user fill it in (see `ai_instructions/README.md`
for how) — before processing any PDFs sitting in `PDFs/`, before
answering any literature question. Everything downstream, especially
gap-flagging, depends on scope.md being real.

This file deliberately owns nothing but that read-order pointer. The
repo-wide conventions — the root/`study/` split, citations outside
`study/`, and the diagram convention — live in the repo root's own
`CLAUDE.md`, so the two files cannot contradict each other. Read it too
when this folder isn't the repo root.

See `workflow-diagram.md` for a graphical walkthrough of this same
sequence.
