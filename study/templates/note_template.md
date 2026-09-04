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

## Content

<!-- page: 1 -->

... extracted text of page 1 ...

<!-- page: 2 -->

... extracted text of page 2 ...
