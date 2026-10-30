#!/usr/bin/env python3
"""
Records and reports which method cards have been checked against their
source document by the row-verifier agent.

A verification is stored against a hash of the card's content
(study/verification.json), so editing a card invalidates its verdict and
it shows up as stale. The agent never writes this file; the coordinating
session records each verdict after reading the agent's report.

Usage:
    python scripts/verification.py status              # one line per card
    python scripts/verification.py todo                # cards needing a check, by note
    python scripts/verification.py record KEY VERDICT [comment...]
        KEY      "notes/file.md#Method name", as printed by status/todo
        VERDICT  pass | fail | unclear
"""

import json
import sys
from datetime import date
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_catalog_index import parse_catalog  # noqa: E402
from method_cards import card_hash, iter_cards  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog.md"
RECORD_PATH = REPO_ROOT / "verification.json"
VERDICTS = ("pass", "fail", "unclear")


def load_record():
    if RECORD_PATH.exists():
        return json.loads(RECORD_PATH.read_text(encoding="utf-8"))
    return {}


def save_record(record):
    RECORD_PATH.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def card_key(note_rel, name):
    return f"{note_rel}#{name}"


def status_for(name, values, rec):
    """Status of one card given its verification record (or None): ocr-only (the
    card rests on OCR text of an equation or table, so it cannot be verified
    until the page is read from its image), verified (current hash, verdict pass),
    failed (current hash, verdict fail or unclear), stale (the card changed since
    it was checked), or unverified."""
    if values.get("read_from") == "ocr":
        return "ocr-only"
    if rec is None:
        return "unverified"
    if rec.get("hash") != card_hash(name, values):
        return "stale"
    return "verified" if rec.get("verdict") == "pass" else "failed"


def card_statuses(entries):
    """[(key, status)] for every card; see status_for."""
    record = load_record()
    out = []
    for _id, _f, note_rel, name, values, _ck in iter_cards(entries):
        key = card_key(note_rel, name)
        out.append((key, status_for(name, values, record.get(key))))
    return out


def orphan_records(entries):
    live = {card_key(n, name) for _i, _f, n, name, _v, _k in iter_cards(entries)}
    return sorted(set(load_record()) - live)


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] not in ("status", "todo", "record"):
        print(__doc__)
        return 2
    entries = parse_catalog(CATALOG_PATH.read_text(encoding="utf-8"))

    if argv[0] == "status":
        for key, status in card_statuses(entries):
            print(f"{status:10} {key}")
        return 0

    if argv[0] == "todo":
        by_note, waiting = {}, []
        for key, status in card_statuses(entries):
            if status == "ocr-only":
                waiting.append(key)
            elif status != "verified":
                note, name = key.split("#", 1)
                by_note.setdefault(note, []).append((name, status))
        for note, cards in sorted(by_note.items()):
            print(note)
            for name, status in cards:
                print(f"  {status:10} {name}")
        if waiting:
            print("\nWaiting for page images (rest on OCR text; do not send to the verifier yet):")
            for key in waiting:
                print(f"  {key}")
        return 0

    if len(argv) < 3 or argv[2] not in VERDICTS:
        print("record needs: KEY VERDICT (pass|fail|unclear) [comment]", file=sys.stderr)
        return 2
    key, verdict, comment = argv[1], argv[2], " ".join(argv[3:])
    cards = {card_key(n, name): (name, v) for _i, _f, n, name, v, _k in iter_cards(entries)}
    if key not in cards:
        print(f"No such card: {key}", file=sys.stderr)
        return 1
    name, values = cards[key]
    record = load_record()
    record[key] = {
        "hash": card_hash(name, values), "verdict": verdict,
        "date": date.today().isoformat(), "comment": comment,
    }
    save_record(record)
    print(f"Recorded {verdict}: {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
