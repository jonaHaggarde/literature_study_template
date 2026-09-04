# Batch orchestration (parallel workers, long unattended runs)

Situational, not part of the standard per-session read order — only
needed for a real backlog (dozens of PDFs) processed via parallel
subagents, often unattended (overnight, or while the user is away).
Read this before launching that kind of run.

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
with a fully self-contained prompt eliminated the failure mode completely
— a worker with nothing to confuse itself with stays scoped to exactly
what its prompt says.

Practical consequence: every worker prompt must contain everything the
worker needs (it has no memory of this conversation) and nothing it
doesn't — don't rely on "as discussed" or shared context.

## Batch size

Split the backlog into batches of roughly 5-10 PDFs per worker, launched
in parallel (one message, multiple worker launches) so independent
full-non-lazy-reads run concurrently instead of serially. Bigger batches
raise the cost of a single worker going wrong; smaller batches raise
coordination and merge overhead — 5-10 is a reasonable starting point,
adjust based on how the first batch goes.

## The worker scope contract

Every worker prompt should look like this — explicit, bounded, and
self-contained:

```
You are processing exactly these N PDFs for this literature study's
catalog: [list titles/paths].

For each PDF, follow ai_instructions/workflow.md's per-document steps:
full non-lazy read, Key Findings + Implementation Notes in its note,
catalog.md fields (checked against ai_instructions/scope.md for in/out
of scope), tags checked against topics/vocabulary.md.

When you have processed all N, STOP. Report back your proposed catalog
entries and note content for review — do not write directly to shared
files.

Do not, under any circumstance:
- process any PDF outside this list, or decide the batch should be
  bigger/smaller than assigned
- edit topics/*.md dossiers, topics/gaps.md, or catalog.md's
  Comparison & survey papers quick-reference section (shared, cross-worker
  state — the coordinator handles this centrally after every worker
  reports back)
- run scripts/build_reference_index.py, scripts/validate_repo.py, or
  scripts/build_gaps_index.py
- commit or push
- spawn further subagents, or continue doing anything after reporting back
```

## Coordinator responsibilities (never delegated to a worker)

After every parallel batch, the coordinating session (not a worker):
merges each worker's proposed entries/note content, resolves any
tag/vocabulary conflicts between workers, runs
`build_reference_index.py`, `validate_repo.py --fix`, and
`build_gaps_index.py` **once, centrally** (not per-worker — running
these concurrently across workers risks concurrent-edit conflicts on the
same shared files), then commits and pushes.

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
