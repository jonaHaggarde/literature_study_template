# Source access

Where papers can actually be sourced from, so a recommendation to "go
find this paper" points somewhere real instead of nowhere. This is
personal/institutional (tied to real subscriptions and affiliations), not
a generic template convention — it lives here in `project_documents/`,
not in `ai_instructions/`, and needs re-specifying by anyone else who
forks this template. Update it as access changes (a new subscription,
access lost, a school/employer change).

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
  are sometimes open access; check per-article rather than assuming.

## Discovery, not access

- **Google Scholar** — for finding a paper and its DOI/citation details
  and for chasing citation trails, not itself a source of full text. Use
  it to identify the paper, then check the channels above for actual
  access.

## Not included: unauthorized-access sites

Sites that host copyrighted papers without publisher/author
authorization (e.g. Sci-Hub) are deliberately left off this list — courts
have found this to constitute copyright infringement (Elsevier v.
Sci-Hub, ACS v. Sci-Hub, among others), and this file feeds a workflow
that's part of a public template, not a one-off personal note. If a
specific paper genuinely isn't reachable through any channel above,
that's a real gap worth logging in `topics/gaps.md`, not a reason to
route around it.

## How this feeds the workflow

When `topics/gaps.md` or a `reference-index.md` lead names a source not
yet in the catalog (see `ai_instructions/workflow.md`'s "Finding a new
source" and "Gap-flagging" sections), suggest checking institutional
access first for likely-paywalled venues (VSD/IEEE/SAE-type journals),
open access next, and use Google Scholar to actually locate the
paper/DOI to start from. If it isn't reachable through any of these, say
so plainly and log it as a gap rather than letting the recommendation
just trail off.
