---
description: The understanding check before a gate: questions in chat, answered from memory, so the user slows down and thinks about what was produced. No hard effect on the gate.
argument-hint: "<gate id>  (map | review | concept | split | adhoc)"
---

Run the understanding check for the gate in $ARGUMENTS. Its purpose is to make the user think
about the article before deciding, not to grade them. It does not apply to `definition` or
`requirements`; if asked for one of those, say so.

## Before starting

- The gate must be open (`python study/scripts/gate.py status <gate>`). If not, say so; the
  check belongs after the briefing.
- Read the article, and the catalog and notes it rests on, so you can tell a right answer from
  a plausible one. Do not show or quote the article while asking.

## The rules

- **One question at a time.** Wait for the answer.
- **The user answers from memory, without the article open.** Say so at the start. "Skip" is a
  valid answer and is simply a gap.
- **After each answer**, say what matched, what was missing and what was wrong, in a few lines.
  Never fill in a hint before they answer.
- **No score, no pass mark.** Right answers need no comment beyond "yes".

## The questions

1. **Open:** summarise the article and its findings.
2. **Conclusions:** what does it conclude, and how strong is the evidence for each?
3. **Gaps:** what does it say is unknown or unsupported?
4. **Weakest point:** which claim would you doubt first, and what would change it?
5. **Gate-specific**, one or two:
   - `map`: which areas got depth, which were left out, and why?
   - `review`: where do two methods disagree, and what explains it?
   - `concept`: why was each rejected concept rejected?
   - `split`: what has to hold for the chosen concept to work?
6. **Spot check:** name one claim from the article and ask which source backs it.

For `adhoc` there is no article: ask 1 to 4 over the dossiers and what the study has found so
far, and 5 as "which area of the scope has the least support, and why".

Ask more or fewer when the article calls for it; this is a sequence to start from, not a form.

## When something was not understood

Offer two ways forward and let them choose: you explain that part in more detail, or they
reread that part of the article and you ask new questions on it. Neither blocks anything.

## At the end

Say in two or three lines whether you think they understand the article well enough to decide
at this gate, or whether they should take it slower, and why. It is a suggestion; the decision
is theirs. Then record it, without their answers:
`python study/scripts/gate.py understand <gate> --suggestion ready` (or `slower`).
