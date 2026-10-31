#!/usr/bin/env python3
"""
Gates: the points where the user stops, reads an article and decides whether the study moves on.

`articles/gates/definitions.json` lists the gates (which article each accepts, what must have
passed before, whether it has the /understand check). `articles/gates/<id>.json` is the record
of one gate: when it was opened, the article's files at that moment (the soft freeze), whether
the understanding check was done and what Claude suggested, and the outcome. Records are written
by this script only.

A gate is never one click. It runs:  open -> (briefing, /understand) -> close.
  open      the user opens it, after the entry checks pass (or early, with a recorded reason).
  briefing  facts that need the user's attention, from scripts. Nothing is printed for what is fine.
  understand  records that the /understand check was done and Claude's suggestion (ready | slower).
            The suggestion has no effect on the gate; the user decides.
  close     the user passes the gate. This is `article_version.py accept` plus the record, so the
            article's status line and the gate record cannot disagree.
  skip      only for a skippable gate, with a reason.

Soft freeze: while a gate is open, the article is meant to stand still, because the user is
reading it. If it changes anyway, the validator warns; `refreeze` accepts the new state after
the user has been told.

A family gate (`split`: one specification article per chosen concept) passes with its first
article. Each later article joins by an amendment: `open split --article NAME` on the passed
gate, then the same briefing, check and `close` for that article, recorded under `amendments`.

The ad hoc gate (`adhoc`) is a stop-and-look with no article and no acceptance: the user pauses
the study, gets a briefing on the study as a whole, and may run /understand over the dossiers.
It leaves one record, `adhoc-<date>.json`.

A nudge, advisory only: when the number of processed catalog entries has grown by `nudge.documents`
(in definitions.json) since the last gate closed, the validator says it may be time for one.

Usage (from study/):
    python scripts/gate.py status [GATE]
    python scripts/gate.py open GATE [--article NAME] [--early REASON]
    python scripts/gate.py briefing GATE [--article NAME]
    python scripts/gate.py understand GATE --suggestion ready|slower [--article NAME]
    python scripts/gate.py close GATE --summary TEXT [--article NAME]
    python scripts/gate.py skip GATE --reason TEXT
    python scripts/gate.py refreeze GATE [--article NAME]

`open`, `close` and `skip` are the user's decisions and sit behind a permission prompt.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import article_version  # noqa: E402
from build_bibliography import ARTICLES_DIR, article_dirs  # noqa: E402

GATES_DIR = ARTICLES_DIR / "gates"
DEFINITIONS = "definitions.json"
SUGGESTIONS = ("ready", "slower")
TODO_RE = re.compile(r"\\todo\{")
OPENISSUE_RE = re.compile(r"\\openissue\{")
COMMENT_RE = re.compile(r"(?<!\\)%.*")
ADHOC = "adhoc"
ADHOC_DEFINITION = {"id": ADHOC, "title": "Ad hoc", "weight": "light", "article": None, "after": [],
                    "understand": True, "skippable": False,
                    "unlocks": "nothing: the study carries on from where it paused"}


# ---- definitions and records -----------------------------------------------------------------

def _read_definitions(gates_dir=GATES_DIR):
    path = gates_dir / DEFINITIONS
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def definitions(gates_dir=GATES_DIR):
    """The ordered list of gate definitions, or [] when the repo has none."""
    return _read_definitions(gates_dir).get("gates", [])


def nudge_threshold(gates_dir=GATES_DIR):
    """New processed catalog entries since the last gate after which the validator suggests one
    (None: no nudge)."""
    return _read_definitions(gates_dir).get("nudge", {}).get("documents")


def definition(gate, gates_dir=GATES_DIR):
    if gate == ADHOC:
        return ADHOC_DEFINITION if definitions(gates_dir) else None
    for d in definitions(gates_dir):
        if d["id"] == gate:
            return d
    return None


def record_path(gate, gates_dir=GATES_DIR):
    return gates_dir / f"{gate}.json"


def load_record(gate, gates_dir=GATES_DIR):
    """A gate's record. `adhoc` means the ad hoc gate that is currently open."""
    if gate == ADHOC:
        for record in reversed(adhoc_records(gates_dir)):
            if not record.get("outcome"):
                return record
        return None
    path = record_path(gate, gates_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def adhoc_records(gates_dir=GATES_DIR):
    if not gates_dir.exists():
        return []
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(gates_dir.glob("adhoc-*.json"))]


def save_record(record, gates_dir=GATES_DIR):
    gates_dir.mkdir(parents=True, exist_ok=True)
    record_path(record["id"], gates_dir).write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def outcome(gate, gates_dir=GATES_DIR):
    """'passed', 'skipped' or None."""
    record = load_record(gate, gates_dir)
    return record.get("outcome") if record else None


def passed(gate, gates_dir=GATES_DIR):
    """Whether a gate has passed or been skipped (so the next may start)."""
    return outcome(gate, gates_dir) in ("passed", "skipped")


def target(record, article=None):
    """The part of a record being worked on: the gate itself while it is open, otherwise the
    amendment for `article` (or the only open one). None when there is nothing open."""
    if record is None:
        return None
    if article:
        if record.get("article") == article:
            return record
        return next((a for a in record.get("amendments", []) if a["article"] == article), None)
    if not record.get("outcome"):
        return record
    open_ones = [a for a in record.get("amendments", []) if not a.get("outcome")]
    return open_ones[0] if len(open_ones) == 1 else None


# ---- articles and entry checks ---------------------------------------------------------------

def article_folders(defn, articles_dir=ARTICLES_DIR):
    """The existing article folders a gate could accept."""
    if not defn.get("article"):
        return []
    if defn.get("family"):
        return [p for p in sorted(articles_dir.iterdir())
                if p.is_dir() and p.name.startswith(defn["article"]) and (p / "main.tex").exists()
                and not p.name.startswith("_")]
    path = articles_dir / defn["article"]
    return [path] if (path / "main.tex").exists() else []


def is_skeleton(adir):
    rows = article_version.load(adir)["rows"]
    return len(rows) == 1 and rows[0]["kind"] == "draft" and rows[0]["summary"].lower().startswith("skeleton")


def article_problems(adir):
    """What stops an article from being read at a gate."""
    rows = article_version.load(adir)["rows"]
    problems = []
    if not rows:
        problems.append(f"articles/{adir.name} has no version history")
    elif is_skeleton(adir):
        problems.append(f"articles/{adir.name} is still the skeleton: nothing has been drafted")
    stale = article_version.stale_files(adir)
    if stale:
        problems.append(f"articles/{adir.name} changed since its last version "
                        f"({', '.join(article_version.short_name(s) for s in stale)}): record it with `edit`")
    return problems


def entry_problems(defn, adir, gates_dir=GATES_DIR):
    """What stops the gate from opening, as readable strings."""
    problems = []
    for earlier in defn["after"]:
        if not passed(earlier, gates_dir):
            problems.append(f"the `{earlier}` gate has not passed")
    if adir is None:
        problems.append(f"articles/{defn['article']}{'<name>' if defn.get('family') else ''} does not exist "
                        f"(create it: python scripts/new_article.py {defn['article'].rstrip('-')}"
                        f"{' <name>' if defn.get('family') else ''})")
        return problems
    return problems + article_problems(adir)


def state(gate, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    """not-reached | ready | open | passed | skipped."""
    record = load_record(gate, gates_dir)
    if record and record.get("outcome"):
        return record["outcome"]
    if record:
        return "open"
    defn = definition(gate, gates_dir)
    if defn is None:
        return "not-reached"
    folders = article_folders(defn, articles_dir)
    return "ready" if not entry_problems(defn, folders[0] if folders else None, gates_dir) else "not-reached"


# ---- the catalog, for the nudge and the ad hoc briefing --------------------------------------

def catalog_count():
    """Processed entries in the catalog (not the example, not stubs)."""
    import build_catalog_index as bci
    if not bci.CATALOG_PATH.exists():
        return 0
    entries = bci.parse_catalog(bci.CATALOG_PATH.read_text(encoding="utf-8"))
    return sum(1 for i, f in entries if i != "EXAMPLE" and bci.is_processed(f))


def last_gate_count(gates_dir=GATES_DIR):
    """The catalog size when the most recent gate closed (0 if none has)."""
    closed = []
    for path in sorted(gates_dir.glob("*.json")) if gates_dir.exists() else []:
        if path.name == DEFINITIONS:
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        for part in [record] + record.get("amendments", []):
            if part.get("closed") and part.get("catalog_count") is not None:
                closed.append((part["closed"], part["catalog_count"]))
    return max(closed)[1] if closed else 0


def nudge(count_now, gates_dir=GATES_DIR):
    """A sentence when enough documents have entered the catalog since the last gate, else None."""
    threshold = nudge_threshold(gates_dir)
    if not threshold:
        return None
    grown = count_now - last_gate_count(gates_dir)
    if grown >= threshold:
        return (f"{grown} documents have entered the catalog since the last gate closed "
                f"(nudge at {threshold}): consider `/gate adhoc` or the next gate")
    return None


# ---- the operations --------------------------------------------------------------------------

def now_label(now=None):
    return article_version.stamp(now)


def new_part(adir, early, problems, now, count):
    rows = article_version.load(adir)["rows"]
    return {"article": adir.name, "opened": now_label(now), "opened_version": rows[-1]["version"] if rows else None,
            "freeze": article_version.tracked_files(adir), "early": early if problems else None,
            "early_problems": problems, "check": None, "outcome": None, "catalog_count": count}


def open_adhoc(now=None, gates_dir=GATES_DIR, count=0):
    if load_record(ADHOC, gates_dir):
        return None, "an ad hoc gate is already open"
    stamp = now_label(now)[:10]
    n = 1 + sum(1 for r in adhoc_records(gates_dir) if r["id"].startswith(f"adhoc-{stamp}"))
    record = {"id": f"adhoc-{stamp}" + (f"-{n}" if n > 1 else ""), "article": None, "opened": now_label(now),
              "check": None, "outcome": None, "catalog_count": count, "kind": "adhoc"}
    save_record(record, gates_dir)
    return record, None


def open_gate(gate, article=None, early=None, now=None, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR,
              count=None):
    """Open a gate (or, on a passed family gate, an amendment for another article).
    Returns (record, error). Entry problems refuse it unless `early` gives a reason."""
    defn = definition(gate, gates_dir)
    if defn is None:
        return None, f"no gate named '{gate}'"
    count = catalog_count() if count is None else count
    if gate == ADHOC:
        return open_adhoc(now, gates_dir, count)
    record = load_record(gate, gates_dir)
    if record and defn.get("family") and record.get("outcome") == "passed":
        return open_amendment(defn, record, article, now, articles_dir, gates_dir, count)
    if record:
        return None, f"the `{gate}` gate is already {state(gate, articles_dir, gates_dir)}"
    folders = article_folders(defn, articles_dir)
    if defn.get("family"):
        chosen = [f for f in folders if f.name == article]
        if not chosen:
            names = ", ".join(f.name for f in folders) or "none yet"
            return None, f"name the article this gate accepts: --article NAME (existing: {names})"
        adir = chosen[0]
    else:
        adir = folders[0] if folders else None
    problems = entry_problems(defn, adir, gates_dir)
    if problems and not early:
        return None, ("cannot open yet: " + "; ".join(problems)
                      + ". To open anyway, give a reason with --early (it is recorded).")
    if adir is None:
        return None, "cannot open: " + "; ".join(problems)
    record = {"id": gate, **new_part(adir, early, problems, now, count)}
    save_record(record, gates_dir)
    return record, None


def open_amendment(defn, record, article, now, articles_dir, gates_dir, count):
    """A later article of a family gate that has already passed."""
    chosen = [f for f in article_folders(defn, articles_dir) if f.name == article]
    if not chosen:
        return None, f"name the article to add: --article NAME (the `{defn['id']}` gate has passed)"
    adir = chosen[0]
    if article == record["article"] or any(a["article"] == article for a in record.get("amendments", [])):
        return None, f"articles/{article} is already part of the `{defn['id']}` gate"
    problems = article_problems(adir)
    if problems:
        return None, "cannot open the amendment: " + "; ".join(problems)
    part = new_part(adir, None, [], now, count)
    record.setdefault("amendments", []).append(part)
    save_record(record, gates_dir)
    return part, None


def note_check(gate, suggestion, article=None, now=None, gates_dir=GATES_DIR):
    """Record that the /understand check was done. Returns (part, error)."""
    record = load_record(gate, gates_dir)
    part = target(record, article)
    if part is None or part.get("outcome"):
        return None, f"the `{gate}` gate is not open"
    if suggestion not in SUGGESTIONS:
        return None, f"the suggestion must be one of: {', '.join(SUGGESTIONS)}"
    part["check"] = {"time": now_label(now), "suggestion": suggestion}
    save_record(record, gates_dir)
    return part, None


def close_gate(gate, summary, article=None, now=None, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR, count=None):
    """Pass a gate (or an amendment): accept the article and record it. Returns (part, error, warnings)."""
    defn = definition(gate, gates_dir)
    record = load_record(gate, gates_dir)
    part = target(record, article)
    if defn is None or part is None or part.get("outcome"):
        return None, f"the `{gate}` gate is not open", []
    count = catalog_count() if count is None else count
    warnings = []
    if defn.get("understand") and not part.get("check"):
        warnings.append("the /understand check was not done for this gate")
    elif part.get("check") and part["check"]["suggestion"] == "slower":
        warnings.append("Claude suggested taking this gate slower after the /understand check")
    if gate == ADHOC:
        part.update({"outcome": "done", "closed": now_label(now), "summary": summary, "catalog_count": count})
        save_record(part, gates_dir)
        return part, None, warnings
    adir = articles_dir / part["article"]
    stale = article_version.stale_files(adir)
    if stale:
        return None, (f"articles/{adir.name} changed since its last version "
                      f"({', '.join(article_version.short_name(s) for s in stale)}); record it first"), []
    if frozen_changes(part, adir):
        warnings.append("the article changed while the gate was open")
    row, error = article_version.add_row(adir, "accept", summary, "User", now=now)
    if error:
        return None, error, warnings
    part.update({"outcome": "passed", "closed": now_label(now), "accepted_version": row["version"],
                 "catalog_count": count})
    save_record(record, gates_dir)
    return part, None, warnings


def skip_gate(gate, reason, now=None, gates_dir=GATES_DIR):
    defn = definition(gate, gates_dir)
    if defn is None:
        return None, f"no gate named '{gate}'"
    if not defn.get("skippable"):
        return None, f"the `{gate}` gate cannot be skipped"
    if load_record(gate, gates_dir):
        return None, f"the `{gate}` gate is already {state(gate, gates_dir=gates_dir)}"
    record = {"id": gate, "article": None, "opened": now_label(now), "outcome": "skipped",
              "closed": now_label(now), "reason": reason, "check": None}
    save_record(record, gates_dir)
    return record, None


def frozen_changes(part, adir):
    """Files of the article that differ from the state when the gate opened (while it is open)."""
    if not part or part.get("outcome") or not part.get("article") or not adir.exists():
        return []
    return article_version.changed_between(part.get("freeze", {}), article_version.tracked_files(adir))


def refreeze(gate, article=None, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    record = load_record(gate, gates_dir)
    part = target(record, article)
    if part is None or part.get("outcome") or not part.get("article"):
        return None, f"the `{gate}` gate is not open on an article"
    part["freeze"] = article_version.tracked_files(articles_dir / part["article"])
    save_record(record, gates_dir)
    return part, None


# ---- facts for the briefing ------------------------------------------------------------------

def count_markers(adir):
    todos = issues = 0
    for path in sorted((adir / "sections").glob("*.tex")) + [adir / "main.tex"]:
        if path.name in article_version.GENERATED_SECTIONS or not path.exists():
            continue
        text = COMMENT_RE.sub("", path.read_text(encoding="utf-8", errors="replace"))
        todos += len(TODO_RE.findall(text))
        issues += len(OPENISSUE_RE.findall(text))
    return todos, issues


def adhoc_briefing(part, articles_dir, gates_dir):
    """Facts about the study as a whole, for a stop-and-look."""
    lines = []
    since = catalog_count() - last_gate_count(gates_dir)
    if since:
        lines.append(f"{since} processed catalog entr{'y' if since == 1 else 'ies'} since the last gate closed")
    issues = todos = 0
    for adir in article_dirs(articles_dir):
        t, i = count_markers(adir)
        todos, issues = todos + t, issues + i
        stale = article_version.stale_files(adir)
        if stale:
            lines.append(f"articles/{adir.name} changed since its last version "
                         f"({', '.join(article_version.short_name(s) for s in stale)})")
    if issues:
        lines.append(f"{issues} open issue(s) (\\openissue) across the articles")
    if todos:
        lines.append(f"{todos} \\todo marker(s) across the articles")
    return lines


def briefing(gate, article=None, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    """Lines about what needs the user's attention before deciding. Empty when nothing does."""
    import style_check
    record = load_record(gate, gates_dir)
    part = target(record, article)
    if part is None:
        return []
    if gate == ADHOC:
        return adhoc_briefing(part, articles_dir, gates_dir)
    adir = articles_dir / part["article"]
    lines = []
    if part.get("early"):
        lines.append(f"opened early ({part['early']}); unmet at the time: " + "; ".join(part["early_problems"]))
    todos, issues = count_markers(adir)
    if todos:
        lines.append(f"{todos} \\todo marker(s) are still in the article")
    if issues:
        lines.append(f"{issues} open issue(s) (\\openissue) the sources do not settle")
    findings = style_check.check_article(adir)
    problems = sum(1 for f in findings if f.severity == "problem")
    if problems:
        lines.append(f"{problems} style problem(s): python scripts/style_check.py {adir.name}")
    changed = frozen_changes(part, adir)
    if changed:
        lines.append("changed since the gate opened: " + ", ".join(article_version.short_name(c) for c in changed))
    return lines


# ---- status ----------------------------------------------------------------------------------

def status_lines(articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    lines = []
    for defn in definitions(gates_dir):
        gate = defn["id"]
        st = state(gate, articles_dir, gates_dir)
        record = load_record(gate, gates_dir) or {}
        extra = ""
        if st == "passed":
            extra = f" (v{record.get('accepted_version')}, {record.get('closed', '')[:10]})"
            waiting = [a["article"] for a in record.get("amendments", []) if not a.get("outcome")]
            added = sum(1 for a in record.get("amendments", []) if a.get("outcome") == "passed")
            if added:
                extra += f", {added} amendment(s)"
            if waiting:
                extra += f", amendment open: {', '.join(waiting)}"
        elif st == "skipped":
            extra = f" ({record.get('reason', '')})"
        elif st == "open":
            check = record.get("check")
            extra = (f" (since {record['opened'][:10]}; check done, suggestion: {check['suggestion']})" if check
                     else f" (since {record['opened'][:10]}; check not done)" if defn.get("understand")
                     else f" (since {record['opened'][:10]})")
        lines.append(f"{gate:<14}{defn['weight']:<8}{st}{extra}")
    open_adhoc_record = load_record(ADHOC, gates_dir)
    if open_adhoc_record:
        lines.append(f"{'adhoc':<14}{'light':<8}open (since {open_adhoc_record['opened'][:10]})")
    return lines


def problems_for_validator(articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    """Warnings for validate_repo: a changed open gate, and an acceptance with no gate behind it."""
    out = []
    defs = definitions(gates_dir)
    if not defs:
        return out
    for defn in defs:
        record = load_record(defn["id"], gates_dir)
        parts = [record] + record.get("amendments", []) if record else []
        for part in parts:
            if not part.get("outcome") and part.get("article"):
                changed = frozen_changes(part, articles_dir / part["article"])
                if changed:
                    out.append(f"the `{defn['id']}` gate is open and articles/{part['article']} changed since "
                               f"({', '.join(article_version.short_name(c) for c in changed)}); tell the user, "
                               f"then `python scripts/gate.py refreeze {defn['id']}`")
        passed_articles = {p["article"] for p in parts if p.get("outcome") == "passed"}
        for adir in article_folders(defn, articles_dir):
            accepted = article_version.accepted_version(article_version.load(adir)["rows"])
            if accepted and adir.name not in passed_articles:
                out.append(f"articles/{adir.name} is accepted (v{accepted}) but the `{defn['id']}` gate has no "
                           "record of passing it; accept through `python scripts/gate.py close`")
    return out


# ---- command line ----------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("command", choices=["status", "open", "briefing", "understand", "close", "skip", "refreeze"])
    p.add_argument("gate", nargs="?")
    p.add_argument("--article", default=None)
    p.add_argument("--early", default=None)
    p.add_argument("--suggestion", default="")
    p.add_argument("--summary", default="")
    p.add_argument("--reason", default="")
    args = p.parse_args(argv)

    if not definitions():
        print("gate: no articles/gates/definitions.json in this repo.", file=sys.stderr)
        return 1
    if args.command == "status":
        if args.gate and not definition(args.gate):
            print(f"gate: no gate named '{args.gate}'", file=sys.stderr)
            return 1
        for line in status_lines():
            if not args.gate or line.startswith(args.gate):
                print(line)
        if args.gate and args.gate != ADHOC:
            defn = definition(args.gate)
            if state(args.gate) == "not-reached":
                folders = article_folders(defn)
                for problem in entry_problems(defn, folders[0] if folders else None):
                    print(f"  - {problem}")
            print(f"  unlocks: {defn['unlocks']}")
        if not args.gate:
            message = nudge(catalog_count())
            if message:
                print(f"\nNote: {message}")
        return 0
    if not args.gate:
        print("gate: name the gate.", file=sys.stderr)
        return 1
    if args.command == "open":
        part, error = open_gate(args.gate, args.article, args.early)
        if error:
            print(f"gate: {error}", file=sys.stderr)
            return 1
        if args.gate == ADHOC:
            print("The ad hoc gate is open: a stop-and-look at the whole study.")
        else:
            print(f"The `{args.gate}` gate is open on articles/{part['article']} "
                  f"(v{part['opened_version']}). It is frozen until it closes.")
        return 0
    if args.command == "briefing":
        lines = briefing(args.gate, args.article)
        for line in lines:
            print(f"- {line}")
        if not lines:
            print("Nothing in the scripts' facts needs attention.")
        return 0
    if args.command == "understand":
        part, error = note_check(args.gate, args.suggestion, args.article)
        if error:
            print(f"gate: {error}", file=sys.stderr)
            return 1
        print(f"Check recorded for `{args.gate}`: suggestion {args.suggestion}.")
        return 0
    if args.command == "close":
        if not args.summary:
            print("--summary is required.", file=sys.stderr)
            return 1
        part, error, warnings = close_gate(args.gate, args.summary, args.article)
        for w in warnings:
            print(f"NOTE: {w}", file=sys.stderr)
        if error:
            print(f"gate: {error}", file=sys.stderr)
            return 1
        if args.gate == ADHOC:
            print("The ad hoc gate is closed.")
        else:
            print(f"The `{args.gate}` gate passed: articles/{part['article']} accepted as v{part['accepted_version']}.")
            print(f"Next: {definition(args.gate)['unlocks']}")
        return 0
    if args.command == "skip":
        if not args.reason:
            print("--reason is required.", file=sys.stderr)
            return 1
        record, error = skip_gate(args.gate, args.reason)
        if error:
            print(f"gate: {error}", file=sys.stderr)
            return 1
        print(f"The `{args.gate}` gate is skipped ({args.reason}).")
        return 0
    part, error = refreeze(args.gate, args.article)
    if error:
        print(f"gate: {error}", file=sys.stderr)
        return 1
    print(f"The `{args.gate}` gate is frozen at the article's current state.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
