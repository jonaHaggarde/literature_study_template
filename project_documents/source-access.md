# Source access

Where documents can actually be sourced from, so a recommendation to "go
find this paper" points somewhere real instead of nowhere. This is
personal and institutional — tied to real subscriptions and affiliations
— which is why it lives in `project_documents/` rather than in
`../study/ai_instructions/`: it is ground truth about *your* situation,
not a convention of this template.

**The list below is a real, working default, not a placeholder.** It
covers the access most projects started from this template will have.
Edit it for your own situation — add what you can reach, delete what you
can't, and keep it current as access changes (a new subscription, access
lost, a change of school or employer). Anyone forking this template from
a different institution should expect to rewrite the first section
entirely.

## Institutional / subscription access

- **Taylor & Francis** — e.g. *Vehicle System Dynamics* and other T&F
  journals.
- **IEEE** (IEEE Xplore).
- **SAE** (SAE Mobilus — journals, standards, and technical papers).
- **EBSCO, via Linköping University Library**:
  https://research-ebsco-com.e.bibl.liu.se/c/xjonn2/search/advanced/search-options
  (requires LiU SSO login).

## Open access

- **MDPI** — e.g. the *Sensors* journal, and other MDPI journals; fully
  open access.
- **ScienceDirect** — subscription-based overall, but individual articles
  are sometimes open access; check per article rather than assuming.

Keep this distinction sharp when adding entries: "fully open" and "open
per article" behave differently, because the second has to be checked
one document at a time rather than assumed.

## Discovery, not access

- **Google Scholar** — for finding a document and its DOI/citation
  details and for chasing citation trails, not itself a source of full
  text. Use it to identify the document, then check the channels above
  for actual access.

Keep discovery tools separate from the sections above: mixing them is
how "I found it" gets mistaken for "I can read it."

## Not included: unauthorized-access sites

Sites that host copyrighted papers without publisher/author
authorization (e.g. Sci-Hub) are deliberately left off this list —
courts have found this to constitute copyright infringement (Elsevier v.
Sci-Hub, ACS v. Sci-Hub, among others), and this file feeds a workflow
that's part of a public template, not a one-off personal note. If a
specific paper genuinely isn't reachable through any channel above,
that's a real gap worth logging in `../study/topics/gaps.md`, not a
reason to route around it.

## How this feeds the workflow

When `../study/topics/gaps.md` or a lead from
`../study/reference-index.md` names a source not yet in the catalog (see
`../study/ai_instructions/workflow.md`, "Finding a new source on a
specific/narrow topic" and "Gap-flagging"), suggest checking
institutional access first for likely-paywalled venues, open access
next, and use Google Scholar to actually locate the paper/DOI to start
from. If it isn't reachable through any of these, say so plainly and log
it as a gap rather than letting the recommendation just trail off.

If a source-acquisition MCP server is attached to this session, it
short-circuits most of this — see `../study/ai_instructions/mcp.md` for
what such a server can and cannot be trusted to do.
