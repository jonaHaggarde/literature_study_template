# Delegation: what to hand to a subagent, and which tier

Situational — read before launching subagents, and read it in full
before changing any model assignment in `.claude/agents/`. The tiers
below are a shipped default, not an accident, and this file exists so
they can be explained and deliberately overridden rather than silently
obeyed or silently reverted.

## The rule that matters most: delegate on asymmetry

The primary reason to delegate is **not** that a cheaper model runs the
task. It is that **the subagent's inputs never enter the coordinator's
context.** A scout that reads 40 notes and returns twelve lines has
saved a coordinator's entire context window regardless of which model it
ran on. An expensive scout still saves more context than reading those
notes inline.

This is worth stating plainly because everyone assumes delegation is
about model cost. It is not, and the argument for the tiering below is
unconvincing without this part.

So, in priority order:

1. **Delegate anything whose inputs are large and whose outputs are
   small.** This is the decision that matters.
2. **Then** pick the cheapest tier that can be trusted with the judgment
   involved.
3. **Never** delegate something whose output is as large as its input —
   "summarize this note into a note" is pure overhead, and worse than
   doing it inline.

**Corollary: constrain the return format in the prompt.** A worker that
pastes back what it read has re-imported exactly the context you
delegated to avoid. `file:line` plus at most two sentences per hit, no
pasted paragraphs. The shipped `corpus-scout` agent has this baked in;
any ad-hoc worker prompt needs it stated explicitly.

## The tiers

The axis is **task shape**, not file type. The intuition that "reading a
document is mechanical, so give it to a cheap model" slices the work in
the wrong place: reading a document into a catalog entry also means
deciding whether it is in scope, picking canonical tags, and noticing a
coverage gap. Those are judgment calls, and they are the ones that
quietly poison the catalog when wrong, because nothing downstream
re-checks them. What is genuinely cheap is *locating* things.

| Tier | Task shape | Examples here | Agent |
| --- | --- | --- | --- |
| **Scout** | Retrieval. Large inputs, tiny outputs, no interpretation. Returns paths, line numbers, short verbatim quotes — never bulk text. | "Which notes cover X?" · "Which ideation files mention Y?" · grepping `reference-index.md` for leads | `corpus-scout` — Sonnet, low effort |
| **Extractor** | Structured fill-in under a schema that already exists. Bounded, checkable output. | Filling a `catalog.md` stub plus a note's `Key Findings` / `Implementation Notes` | `note-extractor` — Sonnet, medium effort |
| **Synthesist** | Judgment. Comparing sources against each other, forming a recommendation, deciding what is missing. | Building or updating a `topics/` dossier | `dossier-synthesist` — Opus, medium effort |
| **Coordinator** | The main session. Merges worker output, ratifies judgment calls, runs the scripts, commits. | Everything in `batch-orchestration.md`'s coordinator responsibilities | Whatever the session is running on |

"A scout finds it, the coordinator concludes from it" is the right
default for a literature question, and `/lit` is that path as a
one-liner. The refinement worth remembering: **extraction does not drop
to the scout tier**, and the judgment fields inside extraction stay
reviewable by the coordinator rather than being trusted silently.

## Why the tiers are drawn where they are

- **Retrieval is the cheapest tier because a wrong answer is *visibly*
  wrong.** You open the file the scout named and the passage either is
  there or it isn't. The failure mode is self-announcing, so it does not
  need an expensive model to prevent.
- **Extraction is Sonnet because the schema does most of the thinking.**
  The fields are fixed, the allowed values are enumerated in
  `catalog-schema.md`, and the tag vocabulary is closed. This is not a
  claim that "Sonnet is good enough for reading papers." It is the much
  narrower claim that Sonnet is good enough for *filling a fixed schema
  from a document, with a coordinator reviewing the judgment fields* —
  and the measurement below is what that rests on, including where it
  failed.
- **Synthesis is Opus because nothing downstream re-checks it.** A wrong
  dossier recommendation propagates into `decisions.md` and never gets
  caught. There is no validator for "this comparison is wrong."

## What the tiering does not cover: collection-derived fields

This is the important refinement, and it came out of measurement rather
than intuition. The extractor's boundary is **not** document reading vs.
synthesis. It is:

| | Fields | Handling |
| --- | --- | --- |
| **Document-derived** | title, authors, year, type, approach, compares, summary, Key Findings, Implementation Notes | Worker writes them, accepted as-is |
| **Collection-derived** | `tags`, the scope verdict, any gap flag | Worker **proposes**, coordinator **ratifies** |

Collection-derived fields depend on the state of the collection: which
tags already exist and what they are used for, what `topics/gaps.md`
says is missing, why a document was acquired in the first place. A
worker with a self-contained prompt structurally cannot know these
things.

**This is a property of the worker contract, not of the model.** An Opus
worker with the same self-contained prompt makes the same mistakes.
Raising the tier does not fix it; moving the decision does. That is why
`/process-batch` has ratification as a numbered step rather than as
advice.

## The measurement this rests on

Run on a real corpus of ~85 documents: three already-catalogued
documents spanning a clean comparison study, a borderline-scope paper,
and a very large systematic review were re-extracted from scratch by
three fresh Sonnet workers. Each got a copy of the note with the
existing `Key Findings` / `Implementation Notes` stripped out, and was
forbidden from opening the catalog, other notes, or dossiers — so it
could not read the answer it was being scored against. Results were
compared against the committed entries.

**What held up:**

- Facts and metadata: 3/3 correct, including one case where the worker
  caught the source file's metadata claiming the wrong year and
  corrected it against the document text. No fabricated numbers were
  detectable.
- Schema-structured fields (`type`, `contribution`, `approach`,
  `compares`): 3/3 good, and in two cases *richer* than what was
  committed.
- `Key Findings` and `Implementation Notes`: consistently strong,
  including the authors' self-flagged limitations — the part most often
  skipped by a lazy read.

**What failed, systematically rather than randomly:**

- **Tags: 3/3 diverged, all by over-tagging.** One invented tag not in
  the vocabulary at all; one misleading tag that was literally
  defensible but would surface the document in every future query for a
  property it does not have; one survey tagged with topics that appear
  *inside* it rather than topics it contributes to. Two deliberately
  narrow committed tags became five.
- **Scope: 2/3 contradicted the committed verdict**, both for the same
  structural reason — the worker reasoned about the document, while the
  catalog records the document's relationship to *this study*. In the
  clearest case, a large review had been deliberately acquired to fill a
  known gap; that fact lived in `gaps.md` and in the conversation that
  sourced it, nowhere in the document. The worker produced a better
  summary of the document and a worse catalog entry.
- **One schema violation**, partly the template's own fault: `n/a` was
  emitted for a field the schema says to omit, because the schema itself
  used `n/a` elsewhere. That ambiguity has since been resolved in
  `catalog-schema.md`.

**Verdict.** The tiering is not a false economy — Sonnet's
document-level extraction was accurate and occasionally better than what
was committed. But "the coordinator reviews the judgment fields" has to
be a hard step in the workflow rather than an aspiration, and the fields
it must review are now known by name.

## Fresh agents, never forks

Every worker is a **fresh, zero-history agent**, never a fork of the
coordinating session. `batch-orchestration.md` documents the failure
mode this prevents in detail. Using the defined agent types in
`.claude/agents/` makes this structural rather than a rule someone has
to remember: a defined agent type is fresh by construction and cannot
inherit the parent conversation.

## How to override the tiering

Any tier can be raised for a specific document or question. The signal
to do so is simple: **a document the coordinator finds itself rewriting
belongs a tier up.** Pass a different `model` when launching, or edit
the agent definition if the change should be permanent — and if you edit
it, update the reasoning here too, per the root `CLAUDE.md`'s rule that
every non-obvious default carries its reasoning next to it.
