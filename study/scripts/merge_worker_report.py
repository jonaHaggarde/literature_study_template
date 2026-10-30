#!/usr/bin/env python3
"""
Merges a note-extractor worker's structured report into catalog.md and the
notes, deterministically, so the coordinator does not hand-paste fields.

Why: hand-merging is where fields get lost (a worker's entry once came back
without `note:` and `source:`; the validator caught it, the worker's own
report did not). This script only ever replaces the document-derived fields
of a *stub* entry, never touches `note:` or `source:`, and refuses to
overwrite an entry that is already filled in unless told to.

Report format: the JSON block at the end of a worker's report (see
.claude/agents/note-extractor.md). The coordinator saves each block as a
file, ratifies the collection-derived fields by adding an "approved" object
to each document, then merges:

    {
      "documents": [{
        "entry_id": "Smith2020_Some_Title",
        "catalog": {"authors": "...", "year": "...", "type": "...", "approach": "...",
                    "contribution": "...", "compares": "", "summary": "..."},
        "proposed": {"tags": [], "scope_verdict": "in", "scope_reason": "...",
                     "gap_flags": [], "families": {"Method name": "family"}},
        "unknown": ["authors"],
        "approved": {"tags": ["tag-a", "tag-b"], "families": {"Method name": "family"}}
      }]
    }

Usage (from study/):
    python scripts/merge_worker_report.py --check-tags report1.json report2.json
        near-duplicate and not-in-vocabulary tag proposals across reports
    python scripts/merge_worker_report.py report1.json [report2.json ...] [--dry-run] [--force]
        write the catalog fields, the approved tags (catalog and note
        frontmatter) and the approved method-card families
"""

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog.md"
VOCAB_PATH = REPO_ROOT / "topics" / "vocabulary.md"

# Fields a worker may write: the document-derived ones. tags are collection-
# derived (ratified, then written from "approved"); note and source are the
# stub's own and are never touched.
DOC_FIELDS = ["title", "authors", "year", "type", "approach", "contribution", "compares", "summary"]
ALL_FIELDS = DOC_FIELDS + ["tags", "note", "source"]
FIELD_RE = re.compile(r"^(" + "|".join(ALL_FIELDS) + r"):[ \t]?(.*)$")


def one_line(value):
    return " ".join(str(value).split())


def entry_block_span(text, entry_id):
    m = re.search(r"(<!--\s*entry:" + re.escape(entry_id) + r"\s*-->)(.*?)(<!--\s*/entry\s*-->)", text, re.S)
    return m


def is_stub(block):
    m = re.search(r"(?m)^summary:[ \t]?(.*)$", block)
    return (not m) or (not m.group(1).strip()) or "TODO" in m.group(1)


def replace_fields(block, values):
    """Replace the given fields' lines in an entry block. A replaced field's
    old continuation lines (wrapped text) are dropped with it."""
    out, skipping = [], False
    seen = set()
    for line in block.split("\n"):
        fm = FIELD_RE.match(line)
        if fm:
            skipping = False
            key = fm.group(1)
            if key in values:
                value = one_line(values[key])
                out.append(f"{key}: {value}".rstrip())
                seen.add(key)
                skipping = True
                continue
        elif skipping and line.strip() and not line.lstrip().startswith("<!--"):
            continue  # continuation of a field being replaced
        else:
            skipping = False
        out.append(line)
    missing = set(values) - seen
    if missing:
        raise ValueError(f"entry has no line for: {', '.join(sorted(missing))}")
    return "\n".join(out)


def merge_entry(text, entry_id, fields, force=False):
    """Return the catalog text with the entry's fields replaced."""
    m = entry_block_span(text, entry_id)
    if not m:
        raise ValueError(f"no catalog entry '{entry_id}'")
    block = m.group(2)
    if not is_stub(block) and not force:
        raise ValueError(f"entry '{entry_id}' is already filled in (use --force to overwrite)")
    bad = set(fields) - set(DOC_FIELDS) - {"tags"}
    if bad:
        raise ValueError(f"fields not allowed in a merge: {', '.join(sorted(bad))}")
    before_note = re.search(r"(?m)^note:.*$", block).group(0) if re.search(r"(?m)^note:", block) else ""
    before_src = re.search(r"(?m)^source:.*$", block).group(0) if re.search(r"(?m)^source:", block) else ""
    new_block = replace_fields(block, fields)
    after_note = re.search(r"(?m)^note:.*$", new_block).group(0) if re.search(r"(?m)^note:", new_block) else ""
    after_src = re.search(r"(?m)^source:.*$", new_block).group(0) if re.search(r"(?m)^source:", new_block) else ""
    if (before_note, before_src) != (after_note, after_src):
        raise ValueError(f"merge would change note/source of '{entry_id}'; refusing")
    return text[:m.start(2)] + new_block + text[m.end(2):]


def set_note_tags(note_text, tags):
    line = "tags: [" + ", ".join(tags) + "]"
    if re.search(r"(?m)^tags:.*$", note_text):
        return re.sub(r"(?m)^tags:.*$", lambda _m: line, note_text, count=1)
    return note_text


def set_card_family(note_text, method, family):
    """Insert '- family: x' under the card headed '### method' (or replace it)."""
    lines = note_text.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == f"### {method}":
            j = i + 1
            while j < len(lines) and not lines[j].startswith("#"):
                if re.match(r"^- family:", lines[j]):
                    lines[j] = f"- family: {family}"
                    return "\n".join(lines)
                j += 1
            lines.insert(i + 1, f"- family: {family}")
            return "\n".join(lines)
    raise ValueError(f"no method card '{method}' in the note")


# ---- tag proposals across workers ----------------------------------------------------------

def tag_key(tag):
    t = re.sub(r"[^a-z0-9]+", "", tag.lower())
    return t[:-1] if t.endswith("s") and len(t) > 3 else t


def canonical_tags():
    if not VOCAB_PATH.exists():
        return set()
    return set(re.findall(r"(?m)^- `([^`]+)`", VOCAB_PATH.read_text(encoding="utf-8")))


def listed_families():
    path = REPO_ROOT / "topics" / "families.md"
    if not path.exists():
        return set()
    return set(re.findall(r"(?m)^(?:- )?`([^`]+)`", path.read_text(encoding="utf-8")))


def tag_report(reports):
    """Lines describing proposed tags: near-duplicates across reports and
    tags that are not in the vocabulary yet."""
    canon = canonical_tags()
    proposed = {}  # tag -> set of entry ids
    for rep in reports:
        for doc in rep.get("documents", []):
            for t in doc.get("proposed", {}).get("tags", []):
                proposed.setdefault(t, set()).add(doc.get("entry_id", "?"))
    names = sorted(proposed)
    lines = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if tag_key(a) == tag_key(b) or SequenceMatcher(None, a, b).ratio() >= 0.85:
                lines.append(f"near-duplicate proposals: '{a}' and '{b}' - pick one spelling")
    for t in names:
        for c in canon:
            if t != c and (tag_key(t) == tag_key(c) or SequenceMatcher(None, t, c).ratio() >= 0.85):
                lines.append(f"'{t}' looks like the canonical '{c}' - use the canonical tag")
    new = [t for t in names if t not in canon]
    if new:
        lines.append(f"{len(new)} proposal(s) not in topics/vocabulary.md yet: " + ", ".join(new))
    return lines


# ---- schema validation ---------------------------------------------------------------------

def validate_report(rep, name):
    """Problems with a report's shape, as readable strings. A report in the
    wrong shape must fail loudly: silently merging nothing is how fields get
    lost without anyone noticing."""
    hint = " (the schema is in .claude/agents/note-extractor.md, 'The structured block')"
    if not isinstance(rep, dict) or not isinstance(rep.get("documents"), list) or not rep["documents"]:
        found = ", ".join(sorted(rep)) if isinstance(rep, dict) else type(rep).__name__
        return [f"{name}: no non-empty 'documents' list (top-level keys found: {found}){hint}"]
    problems = []
    for i, doc in enumerate(rep["documents"]):
        where = f"{name}: documents[{i}]"
        if not isinstance(doc, dict):
            problems.append(f"{where} is not an object")
            continue
        if not isinstance(doc.get("entry_id"), str) or not doc["entry_id"]:
            problems.append(f"{where} has no 'entry_id'{hint}")
        cat = doc.get("catalog")
        if not isinstance(cat, dict):
            problems.append(f"{where} has no 'catalog' object{hint}")
        else:
            for k in cat:
                if k in ("note", "source"):
                    problems.append(f"{where}: 'catalog' must not contain '{k}' (the stub's own)")
                elif k == "tags":
                    problems.append(f"{where}: tags go in 'proposed', then 'approved', not 'catalog'")
                elif k not in DOC_FIELDS:
                    problems.append(f"{where}: unknown catalog field '{k}' (allowed: {', '.join(DOC_FIELDS)})")
            if not cat.get("summary"):
                problems.append(f"{where}: 'catalog' has no summary")
        appr = doc.get("approved", {})
        if not isinstance(appr, dict):
            problems.append(f"{where}: 'approved' must be an object")
        else:
            if "tags" in appr and not (isinstance(appr["tags"], list) and all(isinstance(t, str) for t in appr["tags"])):
                problems.append(f"{where}: approved.tags must be a list of strings")
            if "families" in appr and not isinstance(appr["families"], dict):
                problems.append(f"{where}: approved.families must be an object")
    return problems


# ---- driver ------------------------------------------------------------------------------

def load_report(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    dry = "--dry-run" in argv
    force = "--force" in argv
    check = "--check-tags" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__)
        return 2
    reports = []
    for f in files:
        try:
            reports.append(load_report(f))
        except (OSError, ValueError) as e:
            print(f"ERROR {f}: cannot read as JSON ({e})", file=sys.stderr)
            return 2
    problems = [msg for f, rep in zip(files, reports) for msg in validate_report(rep, f)]
    if problems:
        for msg in problems:
            print(f"ERROR {msg}", file=sys.stderr)
        print("Nothing was merged.", file=sys.stderr)
        return 2

    if check:
        lines = tag_report(reports)
        print("\n".join(lines) if lines else "No tag conflicts.")
        return 0

    text = CATALOG_PATH.read_text(encoding="utf-8")
    errors, merged = [], 0
    note_edits, reminders = [], []
    for rep in reports:
        for doc in rep.get("documents", []):
            entry_id = doc.get("entry_id", "")
            fields = {k: v for k, v in doc.get("catalog", {}).items() if k in DOC_FIELDS}
            approved = doc.get("approved", {})
            if approved.get("tags"):
                fields["tags"] = ", ".join(approved["tags"])
            try:
                text = merge_entry(text, entry_id, fields, force=force)
            except ValueError as e:
                errors.append(f"{entry_id or '?'}: {e}")
                continue
            vocab_missing = [t for t in approved.get("tags", []) if t not in canonical_tags()]
            fam_missing = [f for f in approved.get("families", {}).values() if f not in listed_families()]
            if vocab_missing and not dry:
                reminders.append(f"{entry_id}: add to topics/vocabulary.md: {', '.join(vocab_missing)}")
            if fam_missing and not dry:
                reminders.append(f"{entry_id}: add to topics/families.md: {', '.join(sorted(set(fam_missing)))}")
            m = re.search(r"(?m)^note:[ \t]?(.*)$", entry_block_span(text, entry_id).group(2))
            note_edits.append((entry_id, REPO_ROOT / m.group(1).strip(), approved))
            merged += 1
            print(f"{'Would merge' if dry else 'Merged'}: {entry_id}"
                  + ("" if approved.get("tags") else "  (no approved tags: tags left empty)"))
            for k in doc.get("unknown", []):
                print(f"  unknown, left to fill: {k}")

    notes_done = []
    for entry_id, note_path, approved in note_edits:
        if not note_path.exists():
            errors.append(f"{entry_id}: note file {note_path} not found")
            continue
        note_text = note_path.read_text(encoding="utf-8")
        try:
            if approved.get("tags"):
                note_text = set_note_tags(note_text, approved["tags"])
            for method, family in approved.get("families", {}).items():
                note_text = set_card_family(note_text, method, family)
        except ValueError as e:
            errors.append(f"{entry_id}: {e}")
            continue
        notes_done.append((note_path, note_text))

    for e in errors:
        print(f"ERROR {e}", file=sys.stderr)
    if dry:
        print(f"Dry run: {merged} entr{'y' if merged == 1 else 'ies'} would be merged, {len(errors)} error(s).")
        return 1 if errors else 0
    if not merged and not errors:
        print("Nothing merged.", file=sys.stderr)
        return 1
    if merged:
        CATALOG_PATH.write_text(text, encoding="utf-8")
        for path, note_text in notes_done:
            path.write_text(note_text, encoding="utf-8")
        for r in reminders:
            print(f"Reminder: {r}")
        print("Next: build_reference_index.py, build_catalog_index.py, validate_repo.py --fix.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
