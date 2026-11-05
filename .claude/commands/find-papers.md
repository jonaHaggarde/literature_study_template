---
description: Find new papers for a scope item or gap — search, propose a table, fetch only what the user numbers.
argument-hint: "[scope item, gap, or seed paper — optional]"
---

Run one search round: find candidate papers for **$ARGUMENTS** (if empty, ask which scope item
or gap, offering the thinnest ones from `study/topics/gaps.md` and `study/ai_instructions/scope.md`).

The design and the reasons are in `study/search-engine-design.md`; read it once per session
before the first round. The two scripts do the mechanical parts and no judgment; the judgment
(angles, fit, what to propose) is yours.

## Before the first query

1. `python study/scripts/scope_sync.py check`. If `scope.md` is still a placeholder, stop and
   steer to `/intake`; nothing is searched before the scope exists. If it says the scope is
   stale, say so once and carry on only if the user agrees.
2. If `study/.venv` is missing, run `study/scripts/setup.ps1` (or `setup.sh`) first.
3. `python study/scripts/lit_search.py new --item "<the scope item or gap, in the user's words>"`.
4. **Write the angles from `scope.md` alone, before any result is on screen**, and declare them
   with `lit_search.py angles`. Cover: the problem in plain words; each method family the scope
   or a dossier names; neighbouring fields that solve a similar problem under another name; older
   terminology for the same thing; and "comparison of", "limitations of" and "survey of" forms.
   The script refuses a query on an undeclared angle. Why: queries written from the papers
   already found only return that corner of the field.

## Searching

5. **Reviews first** for a scope item with nothing yet: `lit_search.py search --reviews` on the
   plain-words angle. A review shows how the field divides itself and its reference lists seed
   later rounds. It never replaces the other angles.
6. One `search` per angle, queries in English. Papers in other languages are never filtered out.
   No year cutoff: an older paper stays when it is heavily cited or several candidates cite it.
7. To judge fit read the record, not the title: `lit_search.py show W1 W2 ...` prints the abstract
   exactly as OpenAlex holds it. When there is none, say so; do not fill it in.
8. `lit_search.py seed` (references or cited-by) only when the user names a seed paper. A round
   is normally not mostly seeds; the table reports the share.
9. After the queries, `lit_search.py vocab`. Propose a few of the new terms as further angles,
   saying where each came from (abstract or topic label). Do not run them without telling the
   user, and do not loop on it: one more pass is a new round.

## Proposing

10. `lit_search.py pick --id W.. --reason ".." --covers ".."` for each paper worth reading, **at
    most 15**, the best fit to the named scope item first. Published articles before theses (a
    thesis only where no article covers the point). Keep a few places, by judgment, for recent
    papers with few citations and for papers from a neighbouring field (`--slot unfamiliar`);
    leave them empty when nothing deserves them.
    **Only papers the search returned can be picked.** A paper you remember is searched for
    first and proposed only if it is found.
11. `lit_search.py table`, then show the user the table from its output (the file is
    `study/searches/round-NN.md`): the reading of the round, the table, the reasons, the list to
    fetch by hand, and the angles not yet searched. Say plainly if a round was thin and which
    angles it did not try. **Never say the topic is covered**; whether it is enough is the user's
    call.
12. **Stop and ask.** Nothing is downloaded before the user answers with numbers ("download
    1,2,3,6,7,9").

## After the user's numbers

13. `lit_search.py approve "1,2,3,6,7,9"` then `python study/scripts/lit_fetch.py fetch`.
    Report in a few lines: how many were fetched and matched their titles, and only the problems
    (blocked, wrong paper, not checkable). Do not list the successes one by one.
14. For papers with no open copy, point to the "to fetch by hand" list: the user saves the PDFs
    into `study/searches/inbox/` with their own access, then `lit_fetch.py match` files them.
    Never use the user's login, never try to get around a paywall or a bot check. For a paper
    with no open copy listed, the table's Scholar link opens "All versions" for the user.
15. Fetched papers wait in `study/PDFs/`. Converting them is `/process-batch`, on the user's word.
16. Offer the next step in one line: another angle, a seed from a paper just fetched, or the next
    scope item.

## Rules

- **The round file is the record.** The queries are shown there, in full, with their angles, after
  the fact; the user does not approve them first.
- **No hard limits except the table's size.** The shares in the reading (references or
  citations, new angles) are signals to comment on, not limits; the field decides what is normal.
- **Never edit `leads.md` by hand for these papers**; the scripts own those rows.
- **A search or fetch tool problem** (an API error, a pattern of blocked hosts) goes in the usage
  log (`python .claude/log_usage.py --kind friction "..."`), one line, no titles.
