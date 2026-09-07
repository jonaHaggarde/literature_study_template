---
description: Process a backlog of new documents into the catalog via parallel note-extractor workers, then merge, validate, and commit centrally.
argument-hint: "[optional: how many documents per worker, default 5-10]"
---

Process the outstanding document backlog for this literature study.
$ARGUMENTS

You are the **coordinator** for this run. Read
`study/ai_instructions/batch-orchestration.md` and
`study/ai_instructions/delegation.md` before launching anything.

## 1. Establish real state — never trust a prior self-report

```
git log --oneline -10
cd study && python scripts/validate_repo.py
```

Cross-check `study/PDFs/` against `study/manifest.json` and
`study/catalog.md` to find what is genuinely outstanding: converted but
un-annotated (a stub entry with a `TODO` summary), or not yet converted
at all. Run `python scripts/convert.py` from `study/` for anything not
yet converted.

If `study/ai_instructions/scope.md` still carries the
`<!-- placeholder -->` marker, stop and fill it in with the user first.
Nothing downstream works without it.

## 2. Launch workers

Split the outstanding documents into batches of roughly 5-10 and launch
one **`note-extractor`** agent per batch, **all in one message** so they
run concurrently. Each worker's prompt must name its exact document list
and must be fully self-contained — a worker has no memory of this
conversation.

Use the defined `note-extractor` agent type. Do not fork this session
into a worker: a fresh agent is fresh by construction, and that is what
prevents the documented failure mode where a worker inherits the
coordinator's context, decides it is the coordinator, and starts editing
shared files and committing on its own.

## 3. Merge, and ratify the judgment fields

Merge each worker's proposed entries into `study/catalog.md` yourself.
Workers do not write shared files.

Then **explicitly review the collection-derived fields** for every
document — this is a required step, not a nicety, because it is the one
place where a self-contained worker structurally cannot be right:

- **Tags.** Three to five, canonical spelling from
  `study/topics/vocabulary.md`, describing what the document
  *contributes* rather than what it *mentions*. Over-tagging is the
  normal failure. Reconcile tag conflicts between workers here; add a
  genuinely new canonical tag to `vocabulary.md` if one is warranted.
- **The scope verdict.** A worker reasons about the document; the
  catalog records the document's relationship to *this study*. A
  document acquired deliberately to fill a known gap will often look out
  of scope from the inside. Check `study/topics/gaps.md` and your own
  knowledge of why each document was acquired.
- **Gap flags.** Check each against `study/ai_instructions/scope.md`
  before logging it — something out of scope being uncovered is expected
  absence, not a gap.
- **The `summary` field**, where a document was acquired for a specific
  gap or sits partly outside scope. Only you can write that clause; a
  neutral summary is actively misleading for such an entry.

## 4. Run the scripts once, centrally

From `study/`, in this order — never per-worker, never concurrently:

```
python scripts/build_reference_index.py
python scripts/build_catalog_index.py
python scripts/validate_repo.py --fix
python scripts/build_gaps_index.py     # only if a dossier changed
```

Fix any FAIL at its source rather than working around it, and re-run.

## 5. Spot-check, then commit

Structural checks passing does not mean the batch is factually sound.
Run 2-3 real discovery queries against the freshly-updated catalog (see
`study/ai_instructions/workflow.md`) and sanity-check the results by eye.

Then commit and push. **Commit after every batch** — never let more than
one batch's work sit uncommitted, so an interruption (a rate limit, a
crash, a closed laptop) costs at most one batch.

If more batches remain, return to step 2.
