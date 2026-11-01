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
    python scripts/intake_check.py --coverage   # rows per definition section, and what is missing
    python scripts/intake_check.py --uncited    # live rows the definition article does not cite

A row can replace an earlier one by saying `supersedes I-n` in its statement (the user changed
their mind, or answered a question left `unknown`). The earlier row stays, because IDs are
never reused and the trace must stay whole, but it no longer counts: not as an answer, not as an
unknown, not as one side of a conflict. Two rows that say `conflicts with` each other stay an
open conflict until one of them is superseded.
"""

import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ocr_support  # noqa: E402
from build_bibliography import ARTICLES_DIR, COMMENT_RE, article_dirs  # noqa: E402

INTAKE_DIR = ARTICLES_DIR.parent / "intake"
INTAKE_PATH = INTAKE_DIR / "intake.md"
MANIFEST_PATH = INTAKE_DIR / ".converted.json"
SOURCE_FOLDERS = ("own", "received")
TEXT_SUFFIXES = {".md", ".txt", ".tex", ".csv", ".json"}
UNREADABLE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp",
                       ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xls", ".odt", ".odp", ".ods"}
LOW_YIELD_CHARS_PER_PAGE = 40
KINDS = ("fact", "goal", "constraint", "preference", "said", "unknown", "suspicion", "out-of-bounds")
# The definition article's sections, which the digest rows serve (`other` serves none yet).
SECTIONS = ("problem", "goal", "scope", "stakeholders", "constraints", "success", "assumptions")
ALL_SECTIONS = SECTIONS + ("other",)

ROW_RE = re.compile(r"^\|\s*(I-\d+)\s*\|(.*)\|\s*$")
CITE_RE = re.compile(r"\\intake\{([^}]*)\}")
SUPERSEDES_RE = re.compile(r"\bsupersedes\s+(I-\d+)", re.I)
CONFLICT_RE = re.compile(r"\bconflicts with\s+(I-\d+)", re.I)


def parse_intake(text):
    """[(id, section, kind, statement, source)] from the digest's table rows."""
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        cells += [""] * (4 - len(cells))
        rows.append((m.group(1), cells[0], cells[1], cells[2], cells[3]))
    return rows


def superseded(rows):
    """{replaced ID: ID of the row that replaces it}, from `supersedes I-n` in a statement."""
    out = {}
    for rid, _section, _kind, statement, _source in rows:
        for old in SUPERSEDES_RE.findall(statement):
            out[old] = rid
    return out


def live(rows):
    """The rows that still count: those no later row supersedes."""
    gone = superseded(rows)
    return [r for r in rows if r[0] not in gone]


def open_conflicts(rows):
    """[(id, id)] pairs that say `conflicts with` and where neither side is superseded."""
    gone = superseded(rows)
    known = {r[0] for r in rows}
    pairs = []
    for rid, _section, _kind, statement, _source in rows:
        for other in CONFLICT_RE.findall(statement):
            if other in known and rid not in gone and other not in gone:
                pairs.append((other, rid))
    return pairs


def problems(rows):
    """Plain-language problems in the digest itself."""
    found, seen = [], set()
    known = {r[0] for r in rows}
    for rid, section, kind, statement, source in rows:
        if rid in seen:
            found.append(f"{rid} appears more than once")
        seen.add(rid)
        for old in SUPERSEDES_RE.findall(statement):
            if old not in known:
                found.append(f"{rid}: supersedes {old}, which is not in the digest")
            elif int(old[2:]) >= int(rid[2:]):
                found.append(f"{rid}: supersedes {old}, but a row can only replace an earlier one")
        if section not in ALL_SECTIONS:
            found.append(f"{rid}: section '{section}' is not one of {', '.join(ALL_SECTIONS)}")
        if kind not in KINDS:
            found.append(f"{rid}: kind '{kind}' is not one of {', '.join(KINDS)}")
        if not statement:
            found.append(f"{rid}: no statement")
        if not source:
            found.append(f"{rid}: no source (a file in intake/, or an interview answer with its date)")
    return found


def coverage(rows):
    """{section: (rows that answer it, rows left unknown)} for each definition section, and
    the sections with no answering row. A row of kind `unknown` marks a question asked and not
    answered, so it does not count as an answer. A superseded row counts for nothing."""
    table = {sec: [0, 0] for sec in SECTIONS}
    for _rid, section, kind, _statement, _source in live(rows):
        if section in table:
            table[section][1 if kind == "unknown" else 0] += 1
    missing = [sec for sec in SECTIONS if table[sec][0] == 0]
    return {sec: tuple(v) for sec, v in table.items()}, missing


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


def uncited(rows, definition_dir):
    """IDs of the live rows the definition article does not cite. Empty when the article has no
    citations yet, since nothing has been drafted to compare with."""
    cited = set(cited_ids(definition_dir)) if definition_dir.exists() else set()
    if not cited:
        return []
    return [r[0] for r in live(rows) if r[0] not in cited]


def check_all(intake_path=INTAKE_PATH, articles_dir=ARTICLES_DIR):
    """[(severity, message)] for the digest and for the articles citing it."""
    out = []
    rows = parse_intake(intake_path.read_text(encoding="utf-8")) if intake_path.exists() else []
    out += [("FAIL", p) for p in problems(rows)]
    known = {r[0] for r in rows}
    gone = superseded(rows)
    for a, b in open_conflicts(rows):
        out.append(("WARN", f"{a} and {b} conflict and neither is superseded; the definition must set both out"))
    for adir in article_dirs(articles_dir):
        cited = set(cited_ids(adir))
        for rid in sorted(cited - known):
            out.append(("FAIL", f"articles/{adir.name}: \\intake{{{rid}}} is not in intake/intake.md"))
        for rid in sorted(cited & set(gone)):
            out.append(("WARN", f"articles/{adir.name}: cites {rid}, which {gone[rid]} supersedes"))
    missing = uncited(rows, articles_dir / "definition")
    if missing:
        out.append(("INFO", f"{len(missing)} intake row(s) are not cited by the definition: {', '.join(missing)}"))
    return out, len(rows)


# ---- the files the user hands over ---------------------------------------------------------

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def source_files(intake_dir=INTAKE_DIR):
    """Every file the user put under intake/own/ or intake/received/, sorted."""
    files = []
    for folder in SOURCE_FOLDERS:
        base = intake_dir / folder
        if base.exists():
            files += [p for p in sorted(base.rglob("*")) if p.is_file() and p.name != "README.md"]
    return files


def pdfs(intake_dir=INTAKE_DIR):
    return [p for p in source_files(intake_dir) if p.suffix.lower() == ".pdf"]


def unreadable(intake_dir=INTAKE_DIR):
    """Files that are not converted and not text: images and office documents."""
    return [p for p in source_files(intake_dir) if p.suffix.lower() in UNREADABLE_SUFFIXES]


def load_manifest(intake_dir=INTAKE_DIR):
    path = intake_dir / MANIFEST_PATH.name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def pending(intake_dir=INTAKE_DIR):
    """PDFs with no converted .md next to them, or whose content changed since conversion."""
    manifest = load_manifest(intake_dir)
    out = []
    for pdf in pdfs(intake_dir):
        rel = pdf.relative_to(intake_dir).as_posix()
        if not pdf.with_suffix(".md").exists() or manifest.get(rel, {}).get("hash") != sha256_file(pdf):
            out.append(pdf)
    return out


def build_markdown(pdf_name, sha, pages, extraction="layout", ocr_suspect=None, today=None):
    """The converted text of a PDF, to sit next to it. Starts with a line saying what it is."""
    total = sum(len(p.get("text", "")) for p in pages)
    lines = [
        f"<!-- Converted from {pdf_name} (sha256 {sha[:12]}, {(today or date.today()).isoformat()}) by "
        "study/scripts/convert_intake.py. A machine conversion, not authored: the text is the "
        "source's, and tables and equations may be wrong. Regenerated when the PDF changes; do not edit. -->",
        "",
    ]
    if extraction == "plain-text-fallback":
        lines += ["<!-- WARNING: layout extraction timed out, so tables, equations and structure are "
                  "lost or scrambled. Treat anything that depends on one as unread. -->", ""]
    if pages and total / len(pages) < LOW_YIELD_CHARS_PER_PAGE and extraction != "ocr":
        lines += ["<!-- WARNING: almost no text, so this PDF is probably a scan and OCR did not run. "
                  "Nothing here has been read. -->", ""]
    if extraction == "ocr":
        lines += [ocr_support.notice(ocr_suspect or []), ""]
    for i, page in enumerate(pages, start=1):
        tag = " (ocr)" if page.get("ocr") else ""
        lines += [f"<!-- page: {i}{tag} -->", "", page.get("text", "").strip(), ""]
    return "\n".join(lines)


def main():
    rows = parse_intake(INTAKE_PATH.read_text(encoding="utf-8")) if INTAKE_PATH.exists() else []
    if "--next" in sys.argv:
        print(next_id(rows))
        return 0
    if "--coverage" in sys.argv:
        table, missing = coverage(rows)
        for sec in SECTIONS:
            answered, unknown = table[sec]
            print(f"{sec:<13} {answered} answered, {unknown} unknown")
        print("Every definition section has an answer: ready to suggest a draft." if not missing
              else f"No answer yet for: {', '.join(missing)}.")
        return 0
    if "--uncited" in sys.argv:
        missing = uncited(rows, ARTICLES_DIR / "definition")
        print(", ".join(missing) if missing else "Every live intake row is cited by the definition.")
        return 0
    found, count = check_all()
    for severity, message in found:
        print(f"{severity}: {message}")
    failures = [f for f in found if f[0] == "FAIL"]
    print(f"{count} intake line(s); {len(failures)} problem(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
