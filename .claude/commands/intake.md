---
description: Start of the pipeline. Read what the user put in intake/, interview them for the rest, and build intake.md (Claude's digest, source of the definition article).
argument-hint: "[optional: a topic to dig into, e.g. constraints | success | what exists]"
---

Build or extend `intake/intake.md` from the user's files and an interview.
$ARGUMENTS

`intake.md` is **for Claude**: it is not reviewed by the user and not meant to be read. The
definition article is the reviewed document. So the digest must be faithful and traceable,
not polished. You record; you do not decide, advise or propose solutions.

## How to run it

1. **Preflight.** Read `intake/README.md` and `intake/intake.md`. List the files in
   `intake/own/` (written by the user) and `intake/received/` (given to the user by someone
   else). If `intake.md` already has rows, you are extending it: never renumber, reuse
   or delete an ID. Get the next free one with `python study/scripts/intake_check.py --next`.

2. **Convert, then read.** Run `python study/scripts/convert_intake.py`. It turns each new or
   changed PDF into a `.md` next to it (scans are OCR'd). From then on read the `.md`, never
   the PDF again. Never edit any file in `own/` or `received/`; a converted `.md` is a machine
   conversion and is regenerated, not edited. Text and markdown are read directly. The script
   lists images and Word, PowerPoint and Excel files as not converted: tell the user which
   and ask for a PDF or text. Never render page images or read a scan's pages yourself
   (`study/ai_instructions/vision-budget.md`); OCR'd pages are marked `(ocr)` and are unreliable
   for equations and tables, so say so when a row depends on one.

3. **Digest into rows.** One row per claim, in the table in `intake.md`:
   `| I-n | kind | statement | source |`.
   - Kinds: `fact`, `goal`, `constraint`, `preference`, `said`, `suspicion`, `unknown`,
     `out-of-bounds`. A hunch is a `suspicion`, never a `fact`; the user's own words go in
     as `said`, quoted.
   - Source: the file and the place in it (page, heading), or `interview YYYY-MM-DD`. Cite
     the original (`received/brief.pdf, p. 3`), not its converted `.md`. A statement from
     `received/` is what someone else said; one from `own/` is what the user said.
   - One claim per row. If two sources disagree, add both rows and write
     `conflicts with I-n` in the second statement. Do not choose between them.
   - Keep values exactly as given (units, tolerances). Do not round, convert or infer.

4. **Find what is missing.** Check the rows against this list and note what no row answers:
   why the project exists; who it is for and who decides; what already exists; deadlines;
   given constraints (budget, rules, equipment, people); what is already known; what is only
   suspected; what is out of bounds; how success is judged.

5. **Interview.** Ask only about the gaps from step 4, three or four questions at a time,
   in plain chat. Record each answer the same turn as a row with source
   `interview YYYY-MM-DD`. An unanswered question becomes an `unknown` row, so the gap is
   visible later. Stop when the user says they are done; do not insist on completeness.

6. **Check and report.** Run `python study/scripts/intake_check.py`. Then say, in a few
   lines: how many rows by kind, which gaps are still `unknown`, and which rows conflict.
   The next step is the definition article; the user decides when to start it.

## Rules

- **Never write to the user's files**, and never put an interpretation where the user's words
  belong.
- **No solutions.** If the user starts proposing a design, record it as a `preference` or
  `said` and carry on; the design is decided later.
- **Confidential material stays in `intake/`.** Nothing from it goes into the usage log.
- **Why it is built this way:** the definition article cites these IDs, so every statement
  the user later reviews can be traced to what they actually said, and anything with no
  intake line is visibly Claude's inference.
