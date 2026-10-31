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

Usage (from study/):
    python scripts/gate.py status [GATE]
    python scripts/gate.py open GATE [--article NAME] [--early REASON]
    python scripts/gate.py briefing GATE
    python scripts/gate.py understand GATE --suggestion ready|slower
    python scripts/gate.py close GATE --summary TEXT
    python scripts/gate.py skip GATE --reason TEXT
    python scripts/gate.py refreeze GATE

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


# ---- definitions and records -----------------------------------------------------------------

def definitions(gates_dir=GATES_DIR):
    """The ordered list of gate definitions, or [] when the repo has none."""
    path = gates_dir / DEFINITIONS
    return json.loads(path.read_text(encoding="utf-8"))["gates"] if path.exists() else []


def definition(gate, gates_dir=GATES_DIR):
    for d in definitions(gates_dir):
        if d["id"] == gate:
            return d
    return None


def record_path(gate, gates_dir=GATES_DIR):
    return gates_dir / f"{gate}.json"


def load_record(gate, gates_dir=GATES_DIR):
    path = record_path(gate, gates_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


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


# ---- articles and entry checks ---------------------------------------------------------------

def article_folders(defn, articles_dir=ARTICLES_DIR):
    """The existing article folders a gate could accept."""
    if defn.get("family"):
        return [p for p in sorted(articles_dir.iterdir())
                if p.is_dir() and p.name.startswith(defn["article"]) and (p / "main.tex").exists()
                and not p.name.startswith("_")]
    path = articles_dir / defn["article"]
    return [path] if (path / "main.tex").exists() else []


def is_skeleton(adir):
    rows = article_version.load(adir)["rows"]
    return len(rows) == 1 and rows[0]["kind"] == "draft" and rows[0]["summary"].lower().startswith("skeleton")


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
    rows = article_version.load(adir)["rows"]
    if not rows:
        problems.append(f"articles/{adir.name} has no version history")
    elif is_skeleton(adir):
        problems.append(f"articles/{adir.name} is still the skeleton: nothing has been drafted")
    stale = article_version.stale_files(adir)
    if stale:
        problems.append(f"articles/{adir.name} changed since its last version "
                        f"({', '.join(article_version.short_name(s) for s in stale)}): record it with `edit`")
    return problems


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


# ---- the operations --------------------------------------------------------------------------

def now_label(now=None):
    return article_version.stamp(now)


def open_gate(gate, article=None, early=None, now=None, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    """Open a gate. Returns (record, error). Entry problems refuse it unless `early` gives a reason."""
    defn = definition(gate, gates_dir)
    if defn is None:
        return None, f"no gate named '{gate}'"
    if load_record(gate, gates_dir):
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
    rows = article_version.load(adir)["rows"]
    record = {"id": gate, "article": adir.name, "opened": now_label(now),
              "opened_version": rows[-1]["version"] if rows else None,
              "freeze": article_version.tracked_files(adir), "early": early if problems else None,
              "early_problems": problems if problems else [], "check": None, "outcome": None}
    save_record(record, gates_dir)
    return record, None


def note_check(gate, suggestion, now=None, gates_dir=GATES_DIR):
    """Record that the /understand check was done. Returns (record, error)."""
    record = load_record(gate, gates_dir)
    if not record or record.get("outcome"):
        return None, f"the `{gate}` gate is not open"
    if suggestion not in SUGGESTIONS:
        return None, f"the suggestion must be one of: {', '.join(SUGGESTIONS)}"
    record["check"] = {"time": now_label(now), "suggestion": suggestion}
    save_record(record, gates_dir)
    return record, None


def close_gate(gate, summary, now=None, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    """Pass a gate: accept the article and record it. Returns (record, error, warnings)."""
    defn = definition(gate, gates_dir)
    record = load_record(gate, gates_dir)
    if defn is None or not record or record.get("outcome"):
        return None, f"the `{gate}` gate is not open", []
    adir = articles_dir / record["article"]
    stale = article_version.stale_files(adir)
    if stale:
        return None, (f"articles/{adir.name} changed since its last version "
                      f"({', '.join(article_version.short_name(s) for s in stale)}); record it first"), []
    warnings = []
    if defn.get("understand") and not record.get("check"):
        warnings.append("the /understand check was not done for this gate")
    elif record.get("check") and record["check"]["suggestion"] == "slower":
        warnings.append("Claude suggested taking this gate slower after the /understand check")
    if frozen_changes(record, adir):
        warnings.append("the article changed while the gate was open")
    row, error = article_version.add_row(adir, "accept", summary, "User", now=now)
    if error:
        return None, error, warnings
    record.update({"outcome": "passed", "closed": now_label(now), "accepted_version": row["version"]})
    save_record(record, gates_dir)
    return record, None, warnings


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


def frozen_changes(record, adir):
    """Files of the article that differ from the state when the gate opened (while it is open)."""
    if not record or record.get("outcome") or not adir.exists():
        return []
    return article_version.changed_between(record.get("freeze", {}), article_version.tracked_files(adir))


def refreeze(gate, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    record = load_record(gate, gates_dir)
    if not record or record.get("outcome"):
        return None, f"the `{gate}` gate is not open"
    record["freeze"] = article_version.tracked_files(articles_dir / record["article"])
    save_record(record, gates_dir)
    return record, None


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


def briefing(gate, articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    """Lines about what needs the user's attention before deciding. Empty when nothing does."""
    import style_check
    record = load_record(gate, gates_dir)
    if not record or not record.get("article"):
        return []
    adir = articles_dir / record["article"]
    lines = []
    if record.get("early"):
        lines.append(f"opened early ({record['early']}); unmet at the time: " + "; ".join(record["early_problems"]))
    todos, issues = count_markers(adir)
    if todos:
        lines.append(f"{todos} \\todo marker(s) are still in the article")
    if issues:
        lines.append(f"{issues} open issue(s) (\\openissue) the sources do not settle")
    findings = style_check.check_article(adir)
    problems = sum(1 for f in findings if f.severity == "problem")
    if problems:
        lines.append(f"{problems} style problem(s): python scripts/style_check.py {adir.name}")
    changed = frozen_changes(record, adir)
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
        elif st == "skipped":
            extra = f" ({record.get('reason', '')})"
        elif st == "open":
            check = record.get("check")
            extra = (f" (since {record['opened'][:10]}; check done, suggestion: {check['suggestion']})" if check
                     else f" (since {record['opened'][:10]}; check not done)" if defn.get("understand")
                     else f" (since {record['opened'][:10]})")
        lines.append(f"{gate:<14}{defn["weight"]:<8}{st}{extra}")
    return lines


def problems_for_validator(articles_dir=ARTICLES_DIR, gates_dir=GATES_DIR):
    """Warnings for validate_repo: a changed open gate, and an acceptance with no gate behind it."""
    out = []
    defs = definitions(gates_dir)
    if not defs:
        return out
    for defn in defs:
        record = load_record(defn["id"], gates_dir)
        if record and not record.get("outcome") and record.get("article"):
            changed = frozen_changes(record, articles_dir / record["article"])
            if changed:
                out.append(f"the `{defn['id']}` gate is open and articles/{record['article']} changed since "
                           f"({', '.join(article_version.short_name(c) for c in changed)}); tell the user, then "
                           f"`python scripts/gate.py refreeze {defn['id']}`")
        for adir in article_folders(defn, articles_dir):
            accepted = article_version.accepted_version(article_version.load(adir)["rows"])
            gate_article = record.get("article") if record else None
            if accepted and not (record and record.get("outcome") == "passed" and gate_article == adir.name):
                out.append(f"articles/{adir.name} is accepted (v{accepted}) but the `{defn['id']}` gate has no "
                           "record of passing; accept through `python scripts/gate.py close`")
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
        if args.gate:
            defn = definition(args.gate)
            if state(args.gate) == "not-reached":
                folders = article_folders(defn)
                for problem in entry_problems(defn, folders[0] if folders else None):
                    print(f"  - {problem}")
            print(f"  unlocks: {defn['unlocks']}")
        return 0
    if not args.gate:
        print("gate: name the gate.", file=sys.stderr)
        return 1
    if args.command == "open":
        record, error = open_gate(args.gate, args.article, args.early)
        if error:
            print(f"gate: {error}", file=sys.stderr)
            return 1
        print(f"The `{args.gate}` gate is open on articles/{record['article']} "
              f"(v{record['opened_version']}). It is frozen until it closes.")
        return 0
    if args.command == "briefing":
        lines = briefing(args.gate)
        for line in lines:
            print(f"- {line}")
        if not lines:
            print("Nothing in the scripts' facts needs attention.")
        return 0
    if args.command == "understand":
        record, error = note_check(args.gate, args.suggestion)
        if error:
            print(f"gate: {error}", file=sys.stderr)
            return 1
        print(f"Check recorded for `{args.gate}`: suggestion {args.suggestion}.")
        return 0
    if args.command == "close":
        if not args.summary:
            print("--summary is required.", file=sys.stderr)
            return 1
        record, error, warnings = close_gate(args.gate, args.summary)
        for w in warnings:
            print(f"NOTE: {w}", file=sys.stderr)
        if error:
            print(f"gate: {error}", file=sys.stderr)
            return 1
        print(f"The `{args.gate}` gate passed: articles/{record['article']} accepted as v{record['accepted_version']}.")
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
    record, error = refreeze(args.gate)
    if error:
        print(f"gate: {error}", file=sys.stderr)
        return 1
    print(f"The `{args.gate}` gate is frozen at the article's current state.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
