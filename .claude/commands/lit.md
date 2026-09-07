---
description: Answer a literature question — a corpus-scout locates the material, this session draws the conclusion.
argument-hint: "<the literature question>"
---

Answer this literature question against the study corpus:

**$ARGUMENTS**

## How to run it

1. **Locate before you conclude.** Launch a **`corpus-scout`** agent with
   the question, restated so it is self-contained (the scout has no
   memory of this conversation). It returns `path:line` citations and
   short quotes, not bulk text — that is the point: its inputs never
   enter this session's context.

   For a narrow question with one obvious search term, a direct grep here
   is cheaper than a subagent. Delegate when the search is broad, spans
   many files, or would otherwise pull large amounts of text into this
   conversation. The rule is input/output asymmetry, not model cost — see
   `study/ai_instructions/delegation.md`.

2. **Read only what the scout points at.** Open the specific catalog
   entries and notes its citations name. Do not re-read what it already
   searched.

3. **Route by question type**, per
   `study/ai_instructions/workflow.md`:
   - *"Which method or finding should I trust?"* → the Comparison &
     survey quick-reference list, then an existing `study/topics/`
     dossier if one is current. If none exists or it predates documents
     now in the catalog, that is the signal to build or update one — a
     **`dossier-synthesist`** agent drafts it, you review and save it,
     then run `python scripts/build_gaps_index.py`.
   - *"What are my options for X?"* → all candidates tagged with the
     relevant domain, not just comparison studies, plus leads grepped
     out of `study/reference-index.md`. Present as a menu, marking each
     item as covered here or lead-only.
   - *"Find me a source on X"* → grep `study/reference-index.md` before
     saying nothing exists. Report matches as unverified leads and point
     at `project_documents/source-access.md` for where they might
     actually be obtained.

4. **Cite everything.** Every claim names its note file and page marker
   (`<!-- page: N -->`), so the source can be opened at the right spot.
   Anything from `reference-index.md` is labeled an unverified lead.

5. **Say what the corpus does not cover.** If the answer rests on thin
   coverage, say so plainly, check it against
   `study/ai_instructions/scope.md`, and log a genuine in-scope gap in
   `study/topics/gaps.md` rather than waiting to be asked.
