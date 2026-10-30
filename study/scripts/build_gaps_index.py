#!/usr/bin/env python3
"""
Rebuilds the auto-aggregated section of topics/gaps.md from every
topics/*.md dossier's own "## Open questions" section. Purely mechanical
mirroring - Claude/the user's job is writing a good Open-questions section in
the dossier itself, not remembering to copy it here by hand afterward.

A second block, between its own markers, lists every alternative that a
decision tree under ideation/ names but marks `identified`: listed, never
examined. Those are candidate gaps by construction (the same facts the
exploration map's gap view would show), mirrored mechanically. A gaps.md
without the second pair of markers still works; the feed is simply absent.

Only replaces the content between the BEGIN/END markers in gaps.md; the
"Flagged directly" freeform section (and everything else in the file) is
left untouched. If the dossier markers are missing, nothing is written and a
non-zero exit code is returned - re-add the markers (see gaps.md's own
history, or templates/) rather than have this script guess where to put
the block.

Usage: python scripts/build_gaps_index.py
"""

import re
import sys
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)
import build_decision_trees as trees

REPO_ROOT = Path(__file__).resolve().parent.parent
TOPICS_DIR = REPO_ROOT / "topics"
GAPS_PATH = TOPICS_DIR / "gaps.md"
SKIP = {"README.md", "gaps.md", "vocabulary.md", "families.md"}

BEGIN_MARKER = "<!-- BEGIN AUTO-GENERATED: scripts/build_gaps_index.py -->"
END_MARKER = "<!-- END AUTO-GENERATED -->"

TREE_BEGIN = "<!-- BEGIN AUTO-GENERATED: decision trees (scripts/build_gaps_index.py) -->"
TREE_END = "<!-- END AUTO-GENERATED: decision trees -->"

OPEN_QUESTIONS_RE = re.compile(
    r"^## Open questions.*?\n(.*?)(?=^## |\Z)", re.MULTILINE | re.DOTALL
)


def extract_open_questions(dossier_path: Path) -> str:
    text = dossier_path.read_text(encoding="utf-8")
    m = OPEN_QUESTIONS_RE.search(text)
    return m.group(1).strip() if m else ""


def tree_gap_lines(text):
    """Bullets for every `identified` answer in the decision trees of one
    document: a named alternative nobody has examined. Invalid trees are
    skipped here (the validator reports them)."""
    lines = []
    for m in trees.TABLE_RE.finditer(text):
        rows, problems = trees.parse_table(m.group(2))
        if problems or trees.validate(rows):
            continue
        question = {}
        for r in rows:
            if r["question"]:
                question.setdefault(r["Q"], r["question"])
        for r in rows:
            if r["status"] == "identified":
                lines.append(
                    f'- **{r["method"]}** (answer "{r["answer"]}" to {r["Q"]}: '
                    f'{question.get(r["Q"], "")}): listed, never examined'
                )
    return lines


def build_tree_block():
    """The generated content of the decision-tree block, and how many gaps."""
    blocks = [
        "<!-- Run `python scripts/build_gaps_index.py` after adding or updating a decision tree. -->",
        "Alternatives named in a decision tree but never examined. This list is "
        "mechanical: it does not judge scope, so check each against "
        "`ai_instructions/scope.md` (`/gap-check` does) before acting on it.",
    ]
    n = 0
    for path in trees.tree_files():
        if "_templates" in path.parts:
            continue
        lines = tree_gap_lines(path.read_text(encoding="utf-8"))
        if lines:
            n += len(lines)
            rel = path.relative_to(trees.IDEATION_DIR.parent).as_posix()
            blocks.append(f"\n### From `{rel}`\n\n" + "\n".join(lines))
    if not n:
        blocks.append("\n(None: every alternative in every tree has been examined, or there are no trees yet.)")
    return "\n".join(blocks), n


def replace_block(text, begin, end, generated):
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    return pattern.sub(lambda _m: f"{begin}\n{generated}\n{end}", text, count=1)


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

    new_text = replace_block(gaps_text, BEGIN_MARKER, END_MARKER, generated)

    n_tree = None
    if TREE_BEGIN in new_text and TREE_END in new_text:
        tree_block, n_tree = build_tree_block()
        new_text = replace_block(new_text, TREE_BEGIN, TREE_END, tree_block)
    else:
        print("Note: gaps.md has no decision-tree block, so unexamined tree alternatives are not "
              f"listed. Add the {TREE_BEGIN!r} / {TREE_END!r} markers to enable that feed.")

    tail = "" if n_tree is None else f", and {n_tree} unexamined tree alternative(s)"
    if new_text == gaps_text:
        print(f"No change. {n_with_content}/{len(dossiers)} dossiers had an Open questions section with content{tail}.")
        return 0

    GAPS_PATH.write_text(new_text, encoding="utf-8")
    print(f"Updated topics/gaps.md from {n_with_content}/{len(dossiers)} dossiers{tail}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
