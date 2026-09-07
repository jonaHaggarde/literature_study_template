# Batch orchestration (parallel workers, long unattended runs)

Situational, not part of the standard per-session read order — only
needed for a real backlog (dozens of PDFs) processed via parallel
subagents, often unattended (overnight, or while the user is away).
Read this before launching that kind of run, together with
`delegation.md`, which covers which tier each piece of the work belongs
to and why. `/process-batch` runs the loop described here.

## Fresh agents, never forks

Launch each worker as a fresh, self-contained agent (zero conversation
history) — **never** a fork. A fork inherits this entire coordinating
session's history, and that specific setup has a documented failure
mode: a forked worker, mid-batch, loses track of being a single-paper
worker and starts acting as a full autonomous coordinator instead —
merging other workers' results, updating shared files like `catalog.md`
or `topics/gaps.md`, committing, and pushing, entirely on its own,
because it can see (and gets confused for) the coordinator's own context
and tool history. Switching worker agents to fresh, zero-history agents
with a fully self-contained prompt eliminated the failure mode
completely — a worker with nothing to confuse itself with stays scoped
to exactly what its prompt says.

**Use the `note-extractor` agent type** (`.claude/agents/note-extractor.md`)
rather than describing a worker ad hoc in a prompt. This is the same
rule made structural instead of remembered: a defined agent type is
fresh by construction and cannot inherit the parent conversation. It
also carries the full scope contract — the read order, the summary rule,
the tag ceiling, the propose-vs-decide split, and the "do not, under any
circumstance" list — so none of that depends on the coordinator
remembering to paste it.

Practical consequence, whichever way a worker is launched: every worker
prompt must contain everything the worker needs (it has no memory of
this conversation) and nothing it doesn't. Name the exact documents.
Don't rely on "as discussed" or on shared context.

## Batch size

Split the backlog into batches of roughly 5-10 PDFs per worker, launched
in parallel (one message, multiple worker launches) so independent
full-non-lazy-reads run concurrently instead of serially. Bigger batches
raise the cost of a single worker going wrong; smaller batches raise
coordination and merge overhead — 5-10 is a reasonable starting point,
adjust based on how the first batch goes.

## Coordinator responsibilities (never delegated to a worker)

After every parallel batch, the coordinating session — not a worker:

1. **Merges** each worker's proposed entries and note content into the
   shared files. Workers never write shared state.
2. **Ratifies the collection-derived fields.** This is a required step,
   not a review-if-you-have-time. `tags`, the in/out-of-scope verdict,
   and any gap flag depend on the state of the collection — which tags
   already exist and what they are used for, what `topics/gaps.md` says
   is missing, why a document was acquired — and a worker with a
   self-contained prompt structurally cannot know any of that. This is a
   property of the worker contract rather than of the model: a
   more capable worker with the same prompt makes the same mistakes.
   `delegation.md` has the measurement, including the case where a
   worker wrote an excellent summary of a document and an actively wrong
   catalog entry for it.
3. **Resolves tag and vocabulary conflicts** between workers, and adds
   any genuinely new canonical tag to `topics/vocabulary.md`.
4. **Runs the scripts once, centrally** — `build_reference_index.py`,
   `build_catalog_index.py`, `validate_repo.py --fix`, and
   `build_gaps_index.py` if a dossier changed. Never per-worker: running
   these concurrently across workers risks concurrent-edit conflicts on
   the same shared files.
5. **Commits and pushes.**

## Resilience: commit after every batch, never accumulate

Commit and push after every single batch — never let more than one
batch's worth of work sit uncommitted. This is what makes an interrupted
run (a rate limit, a token/usage reset, a crash, the user closing their
laptop) safe: at most one batch is ever at risk, and recovery is cheap.

## Resuming after an interruption

Don't trust any prior self-report of what got done — verify actual
state first:

```
git log --oneline -10
python scripts/validate_repo.py
```

Cross-check `PDFs/` against `manifest.json` and `catalog.md` for which
documents are actually converted/annotated vs. still pending, and only
launch new workers for what's genuinely still outstanding.
