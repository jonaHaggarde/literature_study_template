#!/usr/bin/env python3
"""
Appends one dated entry to .claude/usage-log.md, the running record of how
this repo is actually used. The log exists so the template's author can base
its design on real use rather than guesses; nothing reads it during normal
work, and nobody needs to open it.

This script exists so entries are uniform and cannot drift into something
else: it dates the entry, keeps it to one short line, and refuses text that
looks like content (an address, a URL, a file path, a secret) because the log
records the *shape* of a session, never what it was about.

It does nothing in a working copy where the file .claude/no-usage-log exists. That
file is not committed (it is in .gitignore): the template's own maintainers create
it in their working copy, so repos made from the template log and the template's
own development does not. Anyone can switch logging off the same way.

Usage:
    python .claude/log_usage.py "what happened, in a line"
    python .claude/log_usage.py --kind friction "the template's step X did not fit because Y"
    python .claude/log_usage.py --tail 5      # show the last entries
    python .claude/log_usage.py --count       # how many entries

Kinds (optional, they make the log easier to analyse later):
    request   a new kind of ask the template had no step for
    rework    the user asked for a structural change, not a tweak
    friction  a template convention fit badly, or needed a workaround
    bug       a script, check or instruction misbehaved
    idea      something the template should have, said in passing
"""

import re
import sys
from datetime import date
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

LOG_PATH = Path(__file__).resolve().parent / "usage-log.md"
KINDS = ("request", "rework", "friction", "bug", "idea")
MAX_CHARS = 400
OFF_MARKER = "no-usage-log"

HEADER = """# Usage log

A running record of how this repo actually gets used: the *shape* of a session,
never what it was about. It exists so the template this repo came from can be
designed from real use. Nothing reads it during normal work, and you do not
need to open it.

**What an entry is.** One short line: a new kind of request the template had no
step for, a moment the user asked for a structural rework and not a tweak, a
convention that fit badly, a script or check that misbehaved, an idea said in
passing. Claude appends entries with `.claude/log_usage.py` (see the "Usage
log" section of the root `CLAUDE.md`).

**What never goes in.** Anything about the project's subject: no names, no
quantities, no file contents, no paths, no URLs, no secrets. The script refuses
text that looks like any of these. If a line would only make sense to someone
who knows the project, it does not belong here.

**What to do with it.** Nothing, until you want to give feedback to the template:
copy the file to wherever that is tracked. It is committed with the repo; if the
remote is shared or public and you would rather it stayed local, add
`.claude/usage-log.md` to `.gitignore`. To turn logging off, create an empty
file `.claude/no-usage-log` (it is not committed), or delete the "Usage log" section
from the root `CLAUDE.md`.

## Entries

"""

# Text that looks like content rather than workflow shape.
GUARDS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "an email address"),
    (re.compile(r"https?://|www\."), "a URL"),
    (re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|(?:^|\s)/(?:home|Users|mnt|var|etc)/"), "a file path"),
    (re.compile(r"\b[A-Za-z0-9_\-]{32,}\b"), "a long token-like string"),
    (re.compile(r"(?i)\b(password|passwd|secret|api[_ -]?key|token)\s*[:=]"), "a credential"),
]


class LoggingOff(Exception):
    """Logging is switched off in this working copy (the marker file exists)."""


def logging_off(path=LOG_PATH):
    return (Path(path).parent / OFF_MARKER).exists()


def check_text(text):
    """Problems with an entry's text, as readable strings."""
    problems = []
    if not text.strip():
        problems.append("the entry is empty")
    if len(text) > MAX_CHARS:
        problems.append(f"the entry is {len(text)} characters; the limit is {MAX_CHARS}. "
                        "Say the shape of what happened in one line, not the story.")
    for pattern, what in GUARDS:
        if pattern.search(text):
            problems.append(f"the entry contains {what}; log the shape of the session, not its content")
    return problems


def format_entry(text, kind=None, today=None):
    text = " ".join(text.split())
    stamp = (today or date.today()).isoformat()
    tag = f" [{kind}]" if kind else ""
    return f"- **{stamp}**{tag} — {text}"


def append_entry(text, kind=None, path=LOG_PATH, today=None):
    """Append an entry; returns the line written. Raises ValueError with all
    the reasons if the entry is refused."""
    if logging_off(path):
        raise LoggingOff(f"usage logging is switched off in this working copy ({OFF_MARKER} exists)")
    text = " ".join(text.split())
    problems = check_text(text)
    if kind is not None and kind not in KINDS:
        problems.append(f"kind '{kind}' must be one of {', '.join(KINDS)}")
    if problems:
        raise ValueError("; ".join(problems))
    line = format_entry(text, kind, today)
    if not path.exists():
        path.write_text(HEADER, encoding="utf-8")
    current = path.read_text(encoding="utf-8")
    if not current.endswith("\n"):
        current += "\n"
    path.write_text(current + line + "\n", encoding="utf-8")
    return line


def entries(path=LOG_PATH):
    if not path.exists():
        return []
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("- **")]


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "--count":
        print(len(entries()))
        return 0
    if argv[0] == "--tail":
        n = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 5
        print("\n".join(entries()[-n:]) or "(no entries)")
        return 0
    kind = None
    if argv[0] == "--kind":
        if len(argv) < 3:
            print("--kind needs a kind and the entry text", file=sys.stderr)
            return 2
        kind, argv = argv[1], argv[2:]
    try:
        line = append_entry(" ".join(argv), kind)
    except LoggingOff as e:
        print(f"Not logged: {e}.")
        return 0
    except ValueError as e:
        print(f"Not logged: {e}", file=sys.stderr)
        return 1
    print(f"Logged: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
