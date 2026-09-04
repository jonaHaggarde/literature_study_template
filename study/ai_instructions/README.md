# Claude instructions

Read this folder first, in this order, at the start of every session in
this repo:

1. **`scope.md`** — what this study is actually about. Everything else
   depends on this being real. If it still looks like the placeholder
   template (check for the `<!-- placeholder -->` marker at the top),
   **your first job this session is helping the user fill it in** —
   before processing any PDFs, before answering literature questions.
   Ask about the topic, its boundaries, and what the study needs to
   answer. See `scope.md` itself for the exact questions to work through.
2. **`catalog-schema.md`** — the field definitions for `../catalog.md`
   entries (title, type, contribution, tags, etc.) and this project's
   allowed values for `type`/`contribution`. Check it before adding or
   editing a catalog entry.
3. **`workflow.md`** — the operational playbook: how to process new PDFs,
   how to answer different kinds of literature questions, when to build a
   `../topics/` dossier, how gap-flagging works, and token-cost discipline
   for a corpus that can grow into the hundreds of documents. See
   `../workflow-diagram.md` for a graphical walkthrough of the same
   process (the PDF batch pipeline, the query routing, and which script
   touches which file) — useful for a fast orientation before reading the
   full text version.

## Why scope.md matters so much

The single hardest judgment call this template asks Claude to make is:
*is the fact that nobody's written about X a genuine gap in the
literature worth flagging to the user, or is X just outside what this
study is about?* There's no way to make that call without a clear,
current statement of what the study's boundaries actually are — that's
what `scope.md` is for. Keep it current as the study's understanding of
its own scope evolves; a stale scope.md produces both false gaps (things
correctly excluded, flagged as missing) and real misses (things inside
scope, never flagged because scope.md never mentioned that area).

## Relationship to project_documents/

`../project_documents/` holds the user's own primary materials — a
project brief, a proposal, existing drafts, whatever explains why this
study exists. Those documents are the source of truth but can be long.
`scope.md` is a short, Claude-maintained *distillation* of them, kept small
enough to read in full every session without burning context — update it
whenever `project_documents/` changes or a conversation reveals the
existing distillation is wrong or incomplete, don't let it silently drift
out of sync.
