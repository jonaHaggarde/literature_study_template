# Leads

Every document this study has *heard of but not yet read*, and where each
one stands. Acquisition is its own step, separate from conversion: finding
a lead, getting the file, and processing it often happen in different
sessions, and about half of a typical set of finds cannot be fetched
automatically (bot-protected hosts, paywalls, request-a-copy pages). This
file is what stops those from being forgotten between sessions.

## Rules

- **Scope first.** A lead is added against `ai_instructions/scope.md`: say
  which in-scope item or logged gap it serves. Searching before the scope is
  defined produces a pile nobody can judge. If a lead shows the scope is
  wrong (too narrow, too broad, missing an area), change `scope.md` first and
  log it under "Scope changes" there, then continue. The scope is allowed to
  change during the project; it is not allowed to change silently.
- **One row per lead,** never deleted. A lead that turns out irrelevant
  becomes `deferred` with the reason, so the same search is not repeated.
- **State is one of:** `found` (heard of, not fetched), `fetched` (file is in
  `PDFs/`, not converted), `blocked` (could not be fetched; the access note
  says why), `user-fetched` (the user obtained it by hand), `converted` (in
  the catalog), `deferred` (decided not to pursue; say why).
- **Check open access before assuming it.** An institutional repository can
  serve a full file with no login while its own page offers only "request a
  copy". That does not make the file openly licensed. Look for an explicit
  licence or open-access statement on the publisher or landing page; if there
  is none, record it as `blocked` with that note and let the user decide.
  See `../intake/own/source-access.md` for the channels this study can
  actually use.

## Table

| Lead | Serves (scope item or gap) | Found via | State | Access note (DOI, URL, why blocked) | Date |
|---|---|---|---|---|---|
