# Long-running / unattended sessions

Situational, read when the user asks for an overnight, multi-hour, or
multi-session autonomous batch run (typically processing a PDF backlog
via `batch-orchestration.md`). Requests like "run overnight" or "keep
going until tomorrow" are almost always under-specified relative to what
execution actually needs — this file is a checklist for turning them into
a concrete plan before starting, not a plan itself.

## Real limitations — don't paper over these

- **No tool exists to query the account's remaining token/usage budget or
  exact time until the next usage-window reset from within a session.**
  If pacing needs to be tied to that, the user has to state it explicitly
  — they can see their own usage/reset countdown in their client; Claude
  can't see it from inside the session.
- **Nothing guarantees survival across a full token exhaustion + reset
  wait inside the same interactive session** if the underlying
  process/terminal doesn't stay alive (laptop sleep, closed terminal).
  This is exactly why the mechanism choice below matters — don't assume
  a local session will just pick back up on its own.
- **Multi-session continuity means resuming from repo state, not
  conversation memory.** A resumed run is very likely a fresh
  session/agent with no memory of the one before it — see
  `batch-orchestration.md`'s "Resuming after an interruption" (`git log`,
  `validate_repo.py`, cross-check `PDFs/` against `manifest.json`).

## Vocabulary

- **Session / usage window** — the cadence at which the user's own Claude
  usage resets (e.g. a rolling multi-hour window). The user knows their
  own schedule; Claude doesn't, unless told.
- **Reset boundary** — the moment one usage window ends and the next
  begins, given as an absolute clock time ("3:15pm") or a relative
  countdown ("4:40 hours from now"). A relative countdown goes stale as
  the conversation continues — convert it to an absolute time immediately
  and work from that, don't keep re-deriving it.
- **"0% used" / "leave a window untouched"** — a specific future usage
  window the user wants fully reserved for their own manual use. No
  autonomous work should run in it at all, not even a small amount —
  this is a hard boundary, not a soft target.

## Questions to nail down before starting

1. **How many reset boundaries should the work span?** "This window
   only," "this window plus the next," and "indefinitely until told to
   stop" are three different plans — don't assume which one was meant.
2. **Which specific upcoming window(s), if any, must be left completely
   untouched?** Get an explicit boundary (a clock time, or "the Nth reset
   from now"), not just "eventually stop."
3. **State absolute times, not relative ones.** Convert "X hours from
   now" into a real clock time immediately and repeat it back — this is
   the single most common way these plans go wrong.
4. **What happens at each boundary** — auto-resume immediately into the
   next window, or wait for an explicit go-ahead? Default to auto-resume
   only if that's clearly the point (unattended operation); confirm
   otherwise.
5. **What ends the whole chain?** A finished backlog, a fixed number of
   windows, or an explicit check-in — don't assume "runs forever."
6. **Which mechanism** (below) fits what's actually needed.

## Which mechanism: `/loop` vs `/schedule`

- **`/loop`** (dynamic self-pacing) stays inside the current interactive
  session, waking itself up periodically. Simple, stays in the same
  conversation — but depends on that session/terminal staying alive.
  Reasonable for "keep going for the next couple hours while I'm at my
  desk," questionable for "run all night while my laptop sleeps."
- **`/schedule`** runs as a separate scheduled cloud agent, decoupled
  from any particular terminal session. The more likely fit for genuine
  unattended/overnight operation — but it executes outside the current
  conversation, so results come back as a separate report rather than
  live in front of the user.

When in doubt for a real overnight/away-from-laptop run, lean `/schedule`
and say why, rather than defaulting to `/loop` for convenience.

## Worked example

A request actually given in this shape: "Next session begins in 4:40
hours. Run as long as you can until then, then restart. Then do that
entire session as well, but then I don't want you to restart because I
want 0% tokens used in the session after that."

Restated as an execution plan (this is the kind of restatement to read
back to the user for confirmation before starting anything):

- Convert "4:40 hours from now" to an absolute clock time, e.g. 3:15pm.
- **Window A** (now → 3:15pm): work the backlog as hard as possible.
- At/after 3:15pm: auto-resume into **Window B**, continue working the
  backlog to Window B's own end (its own reset boundary).
- At Window B's end: **stop entirely.** Do not resume into Window C —
  it's reserved untouched for the user.

Two reset boundaries are in play, not one, and they're treated
differently (auto-resume across the first, hard-stop before the second)
— exactly the kind of distinction to confirm explicitly rather than
infer.
