<!--
  Reference only — this is the format scripts/convert.py generates
  automatically for each PDF. You don't need to create these by hand.
-->
---
title: ""
authors: ""
year: ""
type: ""
tags: []
source_pdf: PDFs/relative/path.pdf
pdf_hash: sha256-hash-of-source-pdf
converted_at: 2026-01-01T00:00:00Z
doi: "10.xxxx/xxxxx"
---

<!-- NOTE: title/authors/year above are best-effort from the PDF's own
     metadata (or blank if metadata was empty/unusable) - PDF metadata is
     frequently wrong or stale, verify against the actual text before
     trusting, especially authors/year. This comment (and the doi: line
     above, which is entirely omitted when no DOI is found on the first
     two pages) only appear when convert.py actually found something. -->

## Key Findings

<!-- TODO: 3-6 sentence summary of method, key claims, and results.
     Fill in via Claude after conversion — this block is what
     gets read first when narrowing a large set of candidates on the same
     topic, before opening the full text below. -->

## Implementation Notes

<!-- Added once, when the document is first properly read (not lazily
     deferred): parameters/settings actually used with their values,
     data/sample requirements, failure modes or limitations the authors
     themselves flag, and any released code/data/materials. Omit
     sub-bullets that genuinely don't apply (e.g. a pure literature review
     has no tuning parameters) rather than forcing empty headers. -->

## Method Cards

<!-- Optional. One "### Method name" block per method the document itself
     proposes, tests or compares, with the fields defined in
     ai_instructions/method-card.md (defaults: input, output, model,
     technique), one "- key: value" line each. Plain text; leave a value
     empty rather than write n/a. Omit the whole section for a document
     with no method of its own. These cards become the rows of the
     review article's comparison table (scripts/build_review_table.py). -->

### Example method
- input:
- output:
- model:
- technique:

## Content

<!-- page: 1 -->

... extracted text of page 1 ...

<!-- page: 2 -->

... extracted text of page 2 ...
