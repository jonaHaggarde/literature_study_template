---
description: Show where the gates stand, or open a gate and brief the user before the decision. Never closes one.
argument-hint: "[optional: gate id, e.g. map | review | concept | split]"
---

Gates are the points where the user stops, reads an article and decides whether the study moves
on. `articles/gates/definitions.json` lists them; `study/scripts/gate.py` keeps their state.
$ARGUMENTS

## No argument: status

Run `python study/scripts/gate.py status` and say, in a few lines, which gate is next, which is
open, and what stops the next one from opening. Do not open anything.

## With a gate id

1. `python study/scripts/gate.py status <gate>`. If it is not ready, say what is missing. Offer
   to do the missing work; open early only if the user asks for it and gives a reason
   (`--early "reason"`), and say what the reason records.
2. If it is ready, **ask the user whether to open it.** Opening is theirs: it freezes the article
   while they read. `python study/scripts/gate.py open <gate>` (a family gate also takes
   `--article <folder>`) sits behind a permission prompt.
3. **Briefing**, in chat, once the gate is open. Two parts and nothing else:
   - **Facts:** `python study/scripts/gate.py briefing <gate>`. Pass on only what it prints.
     When it prints nothing, say that and do not pad.
   - **Critique:** your own, short. The silent assumptions you made while writing, the strongest
     case against the article's conclusion, and anything you are unsure of. Say "none" when
     there is none. A real problem goes where it belongs (an `\openissue` in the article, a gap
     in `study/`), not into a separate document. Read `study/ai_instructions/article-style.md`
     first: the same fact once, in one wording.
4. If the gate has the `understand` flag (the status line shows "check not done"), offer
   `/understand <gate>`. Definition and requirements do not have one.
5. **The article stands still while the gate is open.** If the user's reading leads to a change,
   make it with `article_version.py <name> edit`, tell them, and say the validator will warn
   until `python study/scripts/gate.py refreeze <gate>` is run after they have been told.

## Closing

Never run `close` or `skip` yourself. When the user says the gate has passed, tell them the
command and let them run it:
`python study/scripts/gate.py close <gate> --summary "..."` (this is `accept` plus the gate
record). It prints what the gate unlocks; carry that out when they ask.
