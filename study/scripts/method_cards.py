#!/usr/bin/env python3
"""
Shared helpers for method cards: the field list from
ai_instructions/method-card.md, card parsing from a note, and the
BibTeX-style citation key derived from a catalog entry.

Imported by validate_repo.py and build_article_table.py; not run directly.
"""

import hashlib
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_catalog_index import is_processed  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CARD_SCHEMA_PATH = REPO_ROOT / "ai_instructions" / "method-card.md"
FAMILIES_PATH = REPO_ROOT / "topics" / "families.md"

# Reserved card key: groups rows in the article table. It is not a column,
# and it is collection-derived (proposed by a worker, ratified centrally),
# so it is not listed in method-card.md's '## Fields'.
FAMILY_KEY = "family"

# Used only if method-card.md is missing or has no parsable field list;
# the real source of truth is that file.
DEFAULT_FIELDS = ["input", "output", "model", "technique"]

SECTION_RE = re.compile(r"^## Method Cards\s*$", re.MULTILINE)
NEXT_H2_RE = re.compile(r"^## ", re.MULTILINE)
CARD_HEAD_RE = re.compile(r"^### (.+?)\s*$")
CARD_FIELD_RE = re.compile(r"^- ([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*)$")
SCHEMA_FIELD_RE = re.compile(r"^- `([a-z_][a-z0-9_]*)`")
FAMILY_LINE_RE = re.compile(r"^(?:- )?`([^`]+)`")


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


def load_families():
    """Ordered canonical family names from topics/families.md: one
    backtick-wrapped name at the start of a line (optionally after '- ').
    Empty when the file is missing or ships empty."""
    if not FAMILIES_PATH.exists():
        return []
    out = []
    for line in FAMILIES_PATH.read_text(encoding="utf-8").splitlines():
        m = FAMILY_LINE_RE.match(line.strip())
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def card_hash(name, values):
    """Short content hash of a card, so a verification record can tell
    whether the card changed after it was checked."""
    blob = name + "\n" + "\n".join(f"{k}={values[k]}" for k in sorted(values))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def iter_cards(entries):
    """Yield (entry_id, fields, note_rel, name, values, cite_key) for every
    card in every processed entry's note, in catalog order."""
    keys = assign_cite_keys(entries)
    for entry_id, f in entries:
        if entry_id == "EXAMPLE" or not is_processed(f) or not f.get("note"):
            continue
        note = REPO_ROOT / f["note"]
        if not note.exists():
            continue
        for name, values in parse_cards(note.read_text(encoding="utf-8")):
            yield entry_id, f, f["note"], name, values, keys[entry_id]


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
        if entry_id == "EXAMPLE":
            continue
        base = cite_key_base(f.get("authors", ""), f.get("year", ""))
        n = seen.get(base, 0)
        seen[base] = n + 1
        keys[entry_id] = base if n == 0 else f"{base}{chr(ord('a') + n)}"
    return keys
