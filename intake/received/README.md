# intake/received/

**Only material handed down from outside this project** — from a client, a customer, a
university, an institution, or a predecessor project. A brief, a requirements document, a
proposal you were given, a specification, a user manual for equipment you were handed.

What you wrote yourself goes in `../own/`. Keeping the two apart is the point of the split.

## The exclusion rule

**Nothing you authored yourself belongs here.** It is the rule that gets broken first: a
self-authored tracker, a status document or a working draft lands here because it "feels
official," and from then on nobody can tell provided ground truth from the team's own output.
The value of this folder is that everything in it can be trusted as *given*, not derived.

| If you wrote it… | It goes in |
| --- | --- |
| input for the project definition (a note, a brief of your own) | `../own/` |
| a decision or conclusion | `../../decisions.md` |
| an unverified idea | `../../ideation/` |
| an explainer of a concept | `../../theory/` |
| minutes or an agreement | `../../meetings/` |
| a schedule or blocker list | `../../timeline.md` |
| a summary of a paper | `../../study/notes/` + `../../study/catalog.md` |

## Files, and their converted text

Drop files in as they arrived and never edit them; annotate in a separate file next to them if
something needs commenting on.

`python study/scripts/convert_intake.py` (run by `/intake`) turns each PDF into a markdown
file **next to it**, so a long document is read from text and not from the PDF again:
`brief.pdf` gets `brief.md`. The converted file starts with a line saying it is a machine
conversion of that PDF, and it is still the sender's text, not yours. Scans are OCR'd;
OCR'd pages are marked, and OCR garbles equations and tables. A changed PDF is converted again.
Images, Word, PowerPoint and Excel files are not converted: give a PDF or text, or say what to
look at (an image needs the budgeted vision step).

<!-- List further documents here as they're dropped in, one line each
     with a short description of what it is and who provided it. -->

## Citations

If a file you add here (an annotation, an index) references an external source, use the
repo-wide convention: numbered `[1]`, `[2]` markers in order of first appearance and a
`## References` section at the bottom, numbering local to the file. See the root `CLAUDE.md`.
Provided documents themselves are left exactly as they arrived.
