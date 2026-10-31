#!/usr/bin/env python3
"""
Checks for intake/intake.md, Claude's digest of what the user handed over.

Each line of the digest is one table row with an ID (`I-12`), a kind, one statement and
its source (a file in intake/, or an interview answer with its date). The definition
article tags its statements with these IDs (`\\intake{I-12}`), so the IDs are what ties the
accepted article back to what the user said. They must therefore never repeat, never be
reused after a line is dropped, and every ID an article cites must exist.

Usage (from study/):
    python scripts/intake_check.py          # report problems, exit 1 if any
    python scripts/intake_check.py --next   # print the next free ID
"""

import re
import sys
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_bibliography import ARTICLES_DIR, COMMENT_RE, article_dirs  # noqa: E402

INTAKE_PATH = ARTICLES_DIR.parent / "intake" / "intake.md"
KINDS = ("fact", "goal", "constraint", "preference", "said", "unknown", "suspicion", "out-of-bounds")

ROW_RE = re.compile(r"^\|\s*(I-\d+)\s*\|(.*)\|\s*$")
CITE_RE = re.compile(r"\\intake\{([^}]*)\}")


def parse_intake(text):
    """[(id, kind, statement, source)] from the digest's table rows."""
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        cells += [""] * (3 - len(cells))
        rows.append((m.group(1), cells[0], cells[1], cells[2]))
    return rows


def problems(rows):
    """Plain-language problems in the digest itself."""
    found, seen = [], set()
    for rid, kind, statement, source in rows:
        if rid in seen:
            found.append(f"{rid} appears more than once")
        seen.add(rid)
        if kind not in KINDS:
            found.append(f"{rid}: kind '{kind}' is not one of {', '.join(KINDS)}")
        if not statement:
            found.append(f"{rid}: no statement")
        if not source:
            found.append(f"{rid}: no source (a file in intake/, or an interview answer with its date)")
    return found


def next_id(rows, dropped=()):
    """The next free ID. Numbers are never reused, so `dropped` IDs (kept elsewhere) count too."""
    numbers = [int(r[0][2:]) for r in rows] + [int(d[2:]) for d in dropped]
    return f"I-{max(numbers, default=0) + 1}"


def cited_ids(article_dir):
    """Every intake ID an article's hand-written text cites."""
    ids = []
    for path in sorted(article_dir.rglob("*.tex")):
        text = COMMENT_RE.sub("", path.read_text(encoding="utf-8", errors="replace"))
        for m in CITE_RE.finditer(text):
            ids += [i.strip() for i in m.group(1).split(",") if i.strip()]
    return ids


def check_all(intake_path=INTAKE_PATH, articles_dir=ARTICLES_DIR):
    """[(severity, message)] for the digest and for the articles citing it."""
    out = []
    rows = parse_intake(intake_path.read_text(encoding="utf-8")) if intake_path.exists() else []
    out += [("FAIL", p) for p in problems(rows)]
    known = {r[0] for r in rows}
    for adir in article_dirs(articles_dir):
        for rid in sorted(set(cited_ids(adir)) - known):
            out.append(("FAIL", f"articles/{adir.name}: \\intake{{{rid}}} is not in intake/intake.md"))
    return out, len(rows)


def main():
    rows = parse_intake(INTAKE_PATH.read_text(encoding="utf-8")) if INTAKE_PATH.exists() else []
    if "--next" in sys.argv:
        print(next_id(rows))
        return 0
    found, count = check_all()
    for severity, message in found:
        print(f"{severity}: {message}")
    print(f"{count} intake line(s); {len(found)} problem(s).")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
