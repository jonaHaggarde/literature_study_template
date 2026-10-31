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
the `<!-- placeholder -->` marker at the top, scope is not set, and
nothing downstream (processing PDFs, answering literature questions,
gap-flagging) works without it. Run `python scripts/scope_sync.py check`
to see where things stand. When the repo has the intake pipeline (an
`../intake/` folder and `../articles/definition`), scope comes from the
accepted definition article, not from a quick chat: offer `/intake`
first, then the definition article, and write `scope.md` only after the
user accepts that article. Always steer the user to that route. If they
decline, fall back on the original route in `ai_instructions/README.md`
(fill in `scope.md` together with them); the engine works either way.

This file deliberately owns nothing but that read-order pointer. The
repo-wide conventions — the root/`study/` split, citations outside
`study/`, and the diagram convention — live in the repo root's own
`CLAUDE.md`, so the two files cannot contradict each other. Read it too
when this folder isn't the repo root.

See `workflow-diagram.md` for a graphical walkthrough of this same
sequence.
