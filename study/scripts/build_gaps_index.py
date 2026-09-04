#!/usr/bin/env python3
"""
Rebuilds the auto-aggregated section of topics/gaps.md from every
topics/*.md dossier's own "## Open questions" section. Purely mechanical
mirroring - Claude/the user's job is writing a good Open-questions section in
the dossier itself, not remembering to copy it here by hand afterward.

Only replaces the content between the BEGIN/END markers in gaps.md; the
"Flagged directly" freeform section (and everything else in the file) is
left untouched. If the markers are missing, nothing is written and a
non-zero exit code is returned - re-add the markers (see gaps.md's own
history, or templates/) rather than have this script guess where to put
the block.

Usage: python scripts/build_gaps_index.py
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOPICS_DIR = REPO_ROOT / "topics"
GAPS_PATH = TOPICS_DIR / "gaps.md"
SKIP = {"README.md", "gaps.md", "vocabulary.md"}

BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED: scripts/build_gaps_index.py -->"
END_MARKER = "<!-- END AUTO-GENERATED -->"

OPEN_QUESTIONS_RE = re.compile(
    r"^## Open questions.*?\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)


def extract_open_questions(dossier_path: Path) -> str:
    text = dossier_path.read_text(encoding="utf-8")
    m = OPEN_QUESTIONS_RE.search(text)
    return m.group(1).strip() if m else ""


def main():
    if not GAPS_PATH.exists():
        print(f"No {GAPS_PATH} found.", file=sys.stderr)
        return 1

    gaps_text = GAPS_PATH.read_text(encoding="utf-8")
    if BEGIN_MARKER not in gaps_text or END_MARKER not in gaps_text:
        print(
            f"gaps.md is missing the {BEGIN_MARKER!r} / {END_MARKER!r} markers - "
            "not touching the file. Re-add them (see the file's own section "
            "header/instructions) before rerunning.",
            file=sys.stderr,
        )
        return 1

    dossiers = sorted(p for p in TOPICS_DIR.glob("*.md") if p.name not in SKIP)

    blocks = [f"<!-- Run `python scripts/build_gaps_index.py` after adding/updating a topics/*.md dossier. -->"]
    n_with_content = 0
    for dossier in dossiers:
        content = extract_open_questions(dossier)
        if not content:
            continue
        n_with_content += 1
        blocks.append(f"\n### From `topics/{dossier.name}`\n\n{content}")

    generated = "\n".join(blocks)

    pattern = re.compile(
        re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL
    )
    new_text = pattern.sub(f"{BEGIN_MARKER}\n{generated}\n{END_MARKER}", gaps_text, count=1)

    if new_text == gaps_text:
        print(f"No change. {n_with_content}/{len(dossiers)} dossiers had an Open questions section with content.")
        return 0

    GAPS_PATH.write_text(new_text, encoding="utf-8")
    print(f"Updated topics/gaps.md from {n_with_content}/{len(dossiers)} dossiers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
