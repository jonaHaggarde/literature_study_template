#!/usr/bin/env python3
"""
One-off/rerunnable extraction: pulls the References section out of every
note in notes/ and writes a deduplicated, grep-friendly index to
reference-index.md at the repo root. Notes with no References section
(or no heading match) simply contribute nothing - no special-casing by
document type needed.

Usage: python scripts/build_reference_index.py
"""

import re
from difflib import SequenceMatcher
from pathlib import Path

# Two refs in the same publication year with a normalized-text similarity
# above this are treated as the same source (different citation-style
# formatting of the same document), not two different documents.
SIMILARITY_THRESHOLD = 0.6

# Only the first COMPARE_LEN normalized characters (author list + year +
# opening of the title) are compared for similarity - enough to tell two
# citations of the same source apart from two different sources, without
# paying difflib's cost (which scales with string length) on full-length
# citations. Shortening this window is what keeps the O(n^2)-per-year-
# bucket cost manageable as the corpus grows, at the price of a small
# risk of merging two citations that differ only after this many
# characters.
COMPARE_LEN = 90

REPO_ROOT = Path(__file__).resolve().parent.parent
NOTES_DIR = REPO_ROOT / "notes"
OUT_PATH = REPO_ROOT / "reference-index.md"

REF_HEADING_RE = re.compile(r"^#+\s*\*{0,2}References\*{0,2}\s*$", re.IGNORECASE)
LEADING_MARKER_RE = re.compile(r"^[\-\>\s]*[\[\(]?\d{1,3}[\]\)\.]?\s*[\-\s]*")
YEAR_RE = re.compile(r"(19|20)\d{2}")
JUNK_RE = re.compile(
    r"^(<!--\s*page|[A-Z\.\s]{3,30}ET AL\.?$|Page \d)",
    re.IGNORECASE,
)


def extract_title(note_path: Path) -> str:
    text = note_path.read_text(encoding="utf-8")
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', text, re.MULTILINE)
    return m.group(1) if m else note_path.stem


def extract_references(note_path: Path) -> list[str]:
    lines = note_path.read_text(encoding="utf-8").splitlines()
    start = None
    for i, line in enumerate(lines):
        if REF_HEADING_RE.match(line.strip()):
            start = i + 1
            break
    if start is None:
        return []

    body = "\n".join(lines[start:])
    # split into paragraphs on blank lines
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]

    refs = []
    for p in paragraphs:
        p = " ".join(p.split())  # collapse internal whitespace/newlines
        if JUNK_RE.match(p):
            continue
        p = LEADING_MARKER_RE.sub("", p).strip()
        p = re.sub(r"^[\-\>]\s*", "", p).strip()  # any leftover bare bullet
        # a real citation is reasonably long and contains a plausible year
        if len(p) < 40 or not YEAR_RE.search(p):
            continue
        # drop stray running-header fragments that slipped through
        if JUNK_RE.match(p):
            continue
        refs.append(p)
    return refs


def normalize(ref: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", ref.lower()).strip()


def extract_year(ref: str) -> str:
    m = YEAR_RE.search(ref)
    return m.group(0) if m else "unknown"


# SequenceMatcher.ratio() = 2*M/T where T = len(a)+len(b) and M <= min(len(a),
# len(b)), so ratio() can mathematically never reach SIMILARITY_THRESHOLD if
# the shorter string is below this fraction of the longer one's length.
# Skipping those pairs before the expensive call is exact, not a heuristic -
# it cannot introduce a false negative that the full comparison would have
# caught. This is what keeps the O(n^2) per-year pass from taking minutes
# once the corpus's per-year reference count grows into the hundreds.
_MIN_LEN_RATIO = SIMILARITY_THRESHOLD / (2 - SIMILARITY_THRESHOLD)


def cluster_references(all_refs: list[tuple[str, str]]) -> list[dict]:
    """all_refs: list of (ref_text, source_title). Returns merged clusters,
    grouped by publication year (so different editions of the same source,
    which have different years, are correctly kept separate) and merged
    within a year by normalized-text similarity."""
    by_year: dict[str, list[dict]] = {}
    for ref, source in all_refs:
        year = extract_year(ref)
        norm = normalize(ref)[:COMPARE_LEN]
        norm_len = len(norm)
        clusters = by_year.setdefault(year, [])
        match = None
        for cluster in clusters:
            c_len = cluster["norm_len"]
            shorter, longer = (norm_len, c_len) if norm_len <= c_len else (c_len, norm_len)
            if longer == 0 or shorter / longer < _MIN_LEN_RATIO:
                continue  # provably can't reach the threshold, skip the expensive check
            if SequenceMatcher(None, norm, cluster["norm"]).ratio() >= SIMILARITY_THRESHOLD:
                match = cluster
                break
        if match is None:
            clusters.append({"text": ref, "norm": norm, "norm_len": norm_len, "sources": [source]})
        else:
            match["sources"].append(source)
            # keep the longer/more complete formatting as the canonical text
            if len(ref) > len(match["text"]):
                match["text"] = ref
                match["norm"] = norm
                match["norm_len"] = norm_len

    merged = [c for clusters in by_year.values() for c in clusters]
    return merged


def main():
    note_paths = sorted(NOTES_DIR.rglob("*.md"))

    all_refs: list[tuple[str, str]] = []
    for note_path in note_paths:
        title = extract_title(note_path)
        for ref in extract_references(note_path):
            all_refs.append((ref, title))

    entries = cluster_references(all_refs)
    entries.sort(key=lambda e: e["text"].lower())

    lines = []
    lines.append("# Reference index")
    lines.append("")
    lines.append(
        f"Auto-generated by `scripts/build_reference_index.py` from every "
        f"document's own References section in `notes/`. {len(entries)} "
        f"deduplicated entries from {len(note_paths)} source documents, "
        f"sorted alphabetically."
    )
    lines.append("")
    lines.append(
        "**Purpose**: when looking for a new source on a specific topic, "
        "grep this file before assuming nothing exists — a document "
        "already in the catalog may have already cited exactly what "
        "you're looking for. An entry here is a *lead*, not a verified "
        "source: none of these have been read, only cited by something "
        "we do have. Verify before trusting; add to `catalog.md` "
        "properly once you actually have the document."
    )
    lines.append("")
    lines.append(
        "**Dedup caveat**: entries are grouped by publication year, then "
        "merged within a year if normalized text similarity is >= "
        f"{SIMILARITY_THRESHOLD:.0%} (different citation-style formatting "
        "of the same source still matches; different editions of the "
        "same work, which have different years, are correctly kept "
        "separate). Not perfect — very short citations or unusual "
        "formatting can still slip through as duplicates — but far "
        "better than exact matching."
    )
    lines.append("")
    lines.append("Rerun with `python scripts/build_reference_index.py` after adding new documents.")
    lines.append("")
    lines.append("---")
    lines.append("")

    for e in entries:
        sources = "; ".join(sorted(set(e["sources"])))
        lines.append(f"- {e['text']}")
        lines.append(f"  - cited by: {sources}")
        lines.append("")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(entries)} entries from {len(note_paths)} documents to {OUT_PATH}")


if __name__ == "__main__":
    main()
