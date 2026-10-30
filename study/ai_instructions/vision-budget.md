# Reading page images: the budget

OCR (see `../README.md`) reads a scanned PDF as text. It is good on prose and
bad on equations, symbols and tables. When a page that matters is one of those,
the only fix is to have a model *look at the page image* and transcribe it. That
works well (equations and block diagrams came out readable in testing), and it
**costs real tokens**: each page is an image to read plus a transcription to
write, roughly 5,000 to 8,000 tokens for a dense page (an image of about 3,000 tokens to read, plus 2,000 to 4,000 tokens of transcription; a scanned book spread like the test document is at the high end, a single-column paper page is cheaper). A long scanned thesis read this way would
be expensive, and a coordinator that fanned out one subagent per page could spend
a great deal before anyone noticed.

So this step is built to be hard to overspend, by structure and not by good
behaviour. This file defines the limits and explains the mechanism.

## The limits

Edit the numbers to fit your budget; the scripts read them from here. They are
**yours to set**: Claude never edits this file.

- `pages_per_ticket` = 4 — most pages one subagent call may be given
- `pages_per_request` = 12 — most pages one planned request may cover
- `pages_per_day` = 24 — most pages issued in total on one calendar day, across everything
- `tokens_per_page_estimate` = 6000 — a rough guess used only to show a cost estimate; adjust it after you have seen real usage

## The mechanism: five layers

1. **No ticket, no images.** Page images are rendered only when a *ticket* is
   issued, into a folder that exists for that ticket alone. The page-reading
   agent is handed that folder's paths and nothing else. Without a ticket there is
   nothing for it to read.
2. **A plan, then your approval.** A request names the document and the exact
   pages, and shows the estimate. It does nothing until **you** approve it. The
   approve command is deliberately not on the pre-approved list in
   `.claude/settings.json`, so running it asks you for permission, and you can
   also run it yourself in your own terminal.
3. **Tickets are small and one at a time.** A ticket is at most
   `pages_per_ticket` pages, and the next ticket is refused until the previous one
   has been recorded. That makes parallel page-reading impossible by construction.
   Issuing a ticket also asks you for permission, so every batch of pages is
   a decision you see.
4. **Hard caps.** A request cannot exceed `pages_per_request`, and the total
   issued per day cannot exceed `pages_per_day`. Pages are counted when the ticket
   is issued, even if the reading then fails, because that is when the cost is
   incurred. Only one request can be open at a time.
5. **The agent can do almost nothing else.** The `page-reader` agent has only
   the tools to read an image and write one output file. It cannot run commands or
   start other agents. Launching it asks you for permission each time (an `ask`
   rule on `Agent(page-reader)`).

## What this does not stop

Be honest about the edge: nothing technical stops a coordinator from rendering a
page itself and reading it in its own context, outside the ticket process. That
costs tokens in the main session, where you can see it, but it is not blocked. The
rule against it is in the root `CLAUDE.md`, and it is the rule that matters most
if the layers above are ever worked around.

## Which pages to read

Only pages that (a) are OCR'd, (b) are likely to contain equations or tables, and
(c) matter to the work. The notice at the top of an OCR'd note lists the likely
pages; most of them usually do not matter. A method card's value that rests on an
OCR'd equation or table keeps `read_from: ocr` until its page has been read from
the image, and the validator will not count such a card as verified until then.
