#!/usr/bin/env python3
"""
Shared helpers for method cards: the field list from
ai_instructions/method-card.md, card parsing from a note, and the
BibTeX-style citation key derived from a catalog entry.

Imported by validate_repo.py and build_article_table.py; not run directly.
"""

import re
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CARD_SCHEMA_PATH = REPO_ROOT / "ai_instructions" / "method-card.md"

# Used only if method-card.md is missing or has no parsable field list;
# the real source of truth is that file.
DEFAULT_FIELDS = ["input", "output", "model", "technique"]

SECTION_RE = re.compile(r"^## Method Cards\s*$", re.MULTILINE)
NEXT_H2_RE = re.compile(r"^## ", re.MULTILINE)
CARD_HEAD_RE = re.compile(r"^### (.+?)\s*$")
CARD_FIELD_RE = re.compile(r"^- ([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
SCHEMA_FIELD_RE = re.compile(r"^- `([a-z_][a-z0-9_]*)`")


def load_fields():
    """Ordered field keys from the '## Fields' list of method-card.md."""
    if not CARD_SCHEMA_PATH.exists():
        return list(DEFAULT_FIELDS)
    fields, in_fields = [], False
    for line in CARD_SCHEMA_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            in_fields = line.strip() == "## Fields"
            continue
        if in_fields:
            m = SCHEMA_FIELD_RE.match(line)
            if m:
                fields.append(m.group(1))
    return fields or list(DEFAULT_FIELDS)


def parse_cards(note_text):
    """Return a list of (method_name, {key: value}) from a note's
    '## Method Cards' section; [] if the note has no such section."""
    m = SECTION_RE.search(note_text)
    if not m:
        return []
    body = note_text[m.end():]
    nxt = NEXT_H2_RE.search(body)
    if nxt:
        body = body[:nxt.start()]
    cards, name, fields = [], None, {}
    for line in body.splitlines():
        h = CARD_HEAD_RE.match(line)
        if h:
            if name is not None:
                cards.append((name, fields))
            name, fields = h.group(1), {}
            continue
        f = CARD_FIELD_RE.match(line)
        if f and name is not None:
            fields[f.group(1)] = f.group(2).strip()
    if name is not None:
        cards.append((name, fields))
    return cards


def _ascii_letters(s):
    s = unicodedata.normalize("NFKD", s)
    return re.sub(r"[^a-z]", "", s.encode("ascii", "ignore").decode().lower())


def cite_key_base(authors, year):
    """First author's surname plus year, e.g. 'smith2020'. Assumes the
    catalog's 'First Last, First Last' author format; a 'Last, First'
    entry yields the wrong surname and should be fixed in the catalog."""
    first = re.split(r",| and ", authors)[0].strip() if authors else ""
    surname = _ascii_letters(first.split()[-1]) if first.split() else ""
    return f"{surname or 'anon'}{year or ''}"


def assign_cite_keys(entries):
    """Map entry_id -> unique cite key. Collisions get a, b, c suffixes in
    catalog order, so a key only changes if an earlier entry is added with
    the same surname and year."""
    keys, seen = {}, {}
    for entry_id, f in entries:
        base = cite_key_base(f.get("authors", ""), f.get("year", ""))
        n = seen.get(base, 0)
        seen[base] = n + 1
        keys[entry_id] = base if n == 0 else f"{base}{chr(ord('a') + n)}"
    return keys
