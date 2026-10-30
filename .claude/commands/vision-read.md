---
description: Read a few equation- or table-heavy pages of an OCR'd scan from their images, under a ticket and a token budget. Plans first, needs the user's approval, one ticket at a time.
argument-hint: "<document> <pages, e.g. 5,6,7>"
---

Read specific pages of an OCR'd scan from their images.
$ARGUMENTS

This costs real tokens, so it runs under a budget the user set
(`study/ai_instructions/vision-budget.md`) and a process that is built to be hard
to overspend. **Follow it exactly. The process is the point.**

## Hard rules

- **Never read a page image yourself, and never launch the `page-reader` agent,
  outside this process.** No ticket means no images, and no images means nothing
  to read. If something seems to need a shortcut, stop and ask the user.
- **One `page-reader` at a time, never in parallel.** The script refuses a second
  ticket until the first is recorded; do not try to work around that.
- **Never run `approve` on your own initiative.** Approval is the user's decision.
  Running it asks them for permission; if they have not clearly told you to
  approve this request, ask them first.
- **Never edit `vision-budget.md`.** The limits are the user's.
- **Never loop.** After each ticket, stop and report. Issue the next ticket only
  after the user says to.

## Steps

1. **Pick pages worth the cost.** Read the OCR notice at the top of the note's
   `## Content` (it lists the pages likely to hold equations or tables), and choose
   only pages that matter to the work. Fewer is better. If none matter, say so and
   stop: that is a good outcome.

2. **Plan.** `python study/scripts/vision_pages.py plan "<document>" --pages 5,6,7`.
   It refuses pages that were not OCR'd, too many pages, or a day's limit already
   used, and says why. Show the user the plan and its estimate, and ask whether to
   approve it.

3. **Approve (user's decision).** Once the user says yes, run
   `python study/scripts/vision_pages.py approve R1`. It prompts for permission.

4. **Ticket.** `python study/scripts/vision_pages.py ticket R1`. It renders at most
   a few pages and prints their paths and the one output path. It prompts for
   permission.

5. **Launch exactly one `page-reader` agent** (it will ask the user to allow it).
   Give it the image paths and the output path from the ticket, and nothing else.

6. **Record.** `python study/scripts/vision_pages.py record R1-T1`. It merges the
   transcription into the note, marks those pages `(vision)`, and refuses (merging
   nothing) if the transcription does not cover exactly the ticket's pages.

7. **Report and stop.** Say which pages are now `(vision)`, what is left in the
   request, and what has been spent today (`status`). If a method card rested on
   these pages, say so: its `read_from: ocr` line can be updated once the user has
   looked at the transcription.

If the page-reader's file is missing or wrong, `record` will refuse. Do not rerun
the agent blindly: tell the user, and `abandon` the ticket only if they agree (its
pages stay counted against the day's limit).
