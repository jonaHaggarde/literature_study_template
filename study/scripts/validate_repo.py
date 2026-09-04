#!/usr/bin/env python3
"""
Repo health check — rerun after every batch of new PDFs.

Deterministic, structural checks only (this is NOT a test of whether the
notes/abstracts are factually correct — that still needs a human/AI
spot-check of a few real discovery queries, which this script cannot do).
What it *does* catch: catalog/notes/manifest going out of sync, missing
Implementation Notes, stale placeholder entries, tag-casing drift from
topics/vocabulary.md, type/contribution values drifting from
ai_instructions/catalog-schema.md, a stale "Comparison & survey papers"
quick-reference list, dossiers missing their required Open-questions
section, and whether reference-index.md is up to date with the current
notes/.

Allowed `type`/`contribution` values and field-exempt types are read from
ai_instructions/catalog-schema.md, not hardcoded here — edit that file to
change this study's schema, not this script.

Also flags likely-duplicate entries by fuzzy title match (e.g. a preprint
and its later published version both added separately).

Usage:
    python scripts/validate_repo.py                  # check only
    python scripts/validate_repo.py --fix             # also auto-fix tag
                                                        # casing and regenerate
                                                        # the quick-reference list
    python scripts/validate_repo.py --no-rebuild-index

Exit code: 1 if any FAIL, 0 otherwise (WARN/INFO never fail the run).
"""

import json
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog.md"
NOTES_DIR = REPO_ROOT / "notes"
TOPICS_DIR = REPO_ROOT / "topics"
VOCAB_PATH = TOPICS_DIR / "vocabulary.md"
SCHEMA_PATH = REPO_ROOT / "ai_instructions" / "catalog-schema.md"
MANIFEST_PATH = REPO_ROOT / "manifest.json"
REF_INDEX_PATH = REPO_ROOT / "reference-index.md"
BUILD_REF_INDEX_SCRIPT = REPO_ROOT / "scripts" / "build_reference_index.py"

# Fallback defaults, used only if ai_instructions/catalog-schema.md is
# missing or a section can't be parsed - the real source of truth is
# that file.
DEFAULT_TYPES = {"paper", "book", "article", "report", "thesis", "preprint", "dataset", "standard", "other"}
DEFAULT_CONTRIB = {
    "survey", "meta-analysis", "comparison-study", "novel-contribution",
    "experimental-validation", "applied-case-study", "other",
}
DEFAULT_EXEMPT_TYPES = {"standard", "dataset"}

ENTRY_FIELDS = {
    "title", "authors", "year", "type", "approach", "contribution",
    "compares", "tags", "note", "source", "abstract",
}
ENTRY_RE = re.compile(
    r"^<!--\s*entry:(?P<id>.+?)\s*-->(?P<body>.*?)^<!--\s*/entry\s*-->",
    re.DOTALL | re.MULTILINE,
)
FIELD_START_RE = re.compile(
    r"^(" + "|".join(ENTRY_FIELDS) + r"):\s?(.*)$"
)

results = []  # list of (level, category, message)


def log(level, category, message):
    results.append((level, category, message))


def parse_schema_section(text: str, heading: str) -> set:
    """Extract backtick-wrapped `values` listed under a '## heading' in
    catalog-schema.md, stopping at the next '## ' heading."""
    m = re.search(
        rf"^##\s*{re.escape(heading)}\s*\n(.*?)(?=^##\s|\Z)",
        text, re.DOTALL | re.MULTILINE,
    )
    if not m:
        return set()
    return set(re.findall(r"^- `([^`]+)`", m.group(1), re.MULTILINE))


def load_schema():
    if not SCHEMA_PATH.exists():
        log("WARN", "schema-file", "ai_instructions/catalog-schema.md not found — using built-in defaults")
        return DEFAULT_TYPES, DEFAULT_CONTRIB, DEFAULT_EXEMPT_TYPES
    text = SCHEMA_PATH.read_text(encoding="utf-8")
    types = parse_schema_section(text, "Document types") or DEFAULT_TYPES
    contrib = parse_schema_section(text, "Contribution types") or DEFAULT_CONTRIB
    exempt = parse_schema_section(text, "Field-exempt types") or DEFAULT_EXEMPT_TYPES
    return types, contrib, exempt


def parse_catalog(text):
    entries = []
    for m in ENTRY_RE.finditer(text):
        entry_id = m.group("id").strip()
        fields = {k: "" for k in ENTRY_FIELDS}
        current = None
        for line in m.group("body").splitlines():
            fm = FIELD_START_RE.match(line)
            if fm:
                current = fm.group(1)
                fields[current] = fm.group(2).strip()
            elif current and line.strip():
                fields[current] = (fields[current] + " " + line.strip()).strip()
        entries.append((entry_id, fields))
    return entries


def check_catalog_entries(entries, allowed_types, allowed_contrib, exempt_types):
    seen_titles = {}
    for entry_id, f in entries:
        if entry_id == "EXAMPLE":
            continue
        title = f["title"] or entry_id
        is_stub = "TODO" in f["abstract"] or not f["abstract"]
        if is_stub:
            log("INFO", "unprocessed", f"'{title}' is still a stub (TODO abstract) — not yet annotated")
            continue  # don't apply the "fully processed" rules to stubs

        note_path = REPO_ROOT / f["note"] if f["note"] else None
        if not note_path or not note_path.exists():
            log("FAIL", "catalog-notes", f"'{title}': note path '{f['note']}' does not exist on disk")

        source_path = REPO_ROOT / f["source"] if f["source"] else None
        if not source_path or not source_path.exists():
            log("WARN", "catalog-source", f"'{title}': source PDF '{f['source']}' not found on disk (ok if PDFs/ was cleaned up)")

        if not f["authors"]:
            log("FAIL", "schema", f"'{title}': missing authors")
        if not f["year"]:
            log("FAIL", "schema", f"'{title}': missing year")
        if f["type"] not in allowed_types:
            log("FAIL", "schema", f"'{title}': type '{f['type']}' not in {sorted(allowed_types)} (see ai_instructions/catalog-schema.md)")
        if not f["tags"]:
            log("FAIL", "schema", f"'{title}': missing tags")

        if f["type"] not in exempt_types:
            contribs = [c.strip() for c in f["contribution"].split(",") if c.strip()]
            if not contribs:
                log("FAIL", "schema", f"'{title}': missing contribution")
            for c in contribs:
                if c not in allowed_contrib:
                    log("FAIL", "schema", f"'{title}': contribution '{c}' not in {sorted(allowed_contrib)} (see ai_instructions/catalog-schema.md)")

            has_compares_field = bool(f["compares"])
            claims_comparison = any(c in ("comparison-study", "survey") for c in contribs)
            if has_compares_field and not claims_comparison:
                log("WARN", "schema", f"'{title}': has 'compares' but contribution doesn't include comparison-study/survey")
            if claims_comparison and "comparison-study" in contribs and not has_compares_field:
                log("WARN", "schema", f"'{title}': contribution includes comparison-study but 'compares' is empty")

        if len(f["abstract"]) < 80:
            log("WARN", "schema", f"'{title}': abstract looks unusually short ({len(f['abstract'])} chars)")

        key = title.lower()
        if key in seen_titles:
            log("FAIL", "duplicate", f"Duplicate title (case-insensitive): '{title}' (entries '{seen_titles[key]}' and '{entry_id}')")
        else:
            seen_titles[key] = entry_id

    return seen_titles


def check_notes_cross_consistency(entries):
    catalog_note_paths = {f["note"] for _, f in entries if f["note"]}
    disk_notes = {
        p.relative_to(REPO_ROOT).as_posix()
        for p in NOTES_DIR.rglob("*.md")
    }
    orphaned_notes = disk_notes - catalog_note_paths
    for p in sorted(orphaned_notes):
        log("FAIL", "catalog-notes", f"note file '{p}' exists on disk but has no catalog.md entry pointing to it")

    if not MANIFEST_PATH.exists():
        log("WARN", "manifest", "manifest.json not found")
        return
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_note_paths = {v["notes_path"] for v in manifest.values() if "notes_path" in v}
    for pdf, v in manifest.items():
        np = REPO_ROOT / v["notes_path"]
        if not np.exists():
            log("FAIL", "manifest", f"manifest.json entry '{pdf}' points to missing note '{v['notes_path']}'")
    orphaned_vs_manifest = disk_notes - manifest_note_paths
    for p in sorted(orphaned_vs_manifest):
        log("WARN", "manifest", f"note file '{p}' has no manifest.json entry")


def check_note_content(entries):
    for entry_id, f in entries:
        if entry_id == "EXAMPLE" or "TODO" in f["abstract"] or not f["abstract"]:
            continue
        note_path = REPO_ROOT / f["note"] if f["note"] else None
        if not note_path or not note_path.exists():
            continue  # already reported above
        text = note_path.read_text(encoding="utf-8")
        if "## Implementation Notes" not in text:
            log("WARN", "note-content", f"'{f['title']}': note has no '## Implementation Notes' section")
        kf_match = re.search(r"## Key Findings\s*(.*?)(?=\n## )", text, re.DOTALL)
        if kf_match and "TODO" in kf_match.group(1):
            log("FAIL", "note-content", f"'{f['title']}': catalog entry looks processed but Key Findings still has a TODO")
        content_headings = len(re.findall(r"^## Content\s*$", text, re.MULTILINE))
        if content_headings > 1:
            log("FAIL", "note-content", f"'{f['title']}': '## Content' heading appears {content_headings} times (duplication bug)")


def check_tag_vocabulary(entries):
    if not VOCAB_PATH.exists():
        log("WARN", "vocabulary", "topics/vocabulary.md not found")
        return
    vocab_text = VOCAB_PATH.read_text(encoding="utf-8")
    canonical = set(re.findall(r"^- `([^`]+)`", vocab_text, re.MULTILINE))
    canonical_lower = {t.lower(): t for t in canonical}

    used = set()
    for entry_id, f in entries:
        if entry_id == "EXAMPLE" or not f["tags"] or "TODO" in f["abstract"] or not f["abstract"]:
            continue
        used.update(t.strip() for t in f["tags"].split(",") if t.strip())

    uncanonicalized = []
    for tag in sorted(used):
        if tag in canonical:
            continue
        if tag.lower() in canonical_lower:
            log("FAIL", "tag-casing", f"tag '{tag}' differs only in case from canonical '{canonical_lower[tag.lower()]}' — fix casing")
        else:
            uncanonicalized.append(tag)
    if uncanonicalized:
        log("INFO", "vocabulary", f"{len(uncanonicalized)} tag(s) not in topics/vocabulary.md (may be legitimate one-offs): {', '.join(uncanonicalized)}")


def normalize_title(t):
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def check_comparison_quickref(entries, catalog_text):
    section_match = re.search(
        r"## Comparison & survey papers \(quick reference\)\s*(.*?)\n---",
        catalog_text, re.DOTALL,
    )
    quickref_text = section_match.group(1) if section_match else ""
    quickref_titles = {normalize_title(t) for t in re.findall(r"\*\*(.+?)\*\*", quickref_text)}

    for entry_id, f in entries:
        if entry_id == "EXAMPLE" or "TODO" in f["abstract"] or not f["abstract"]:
            continue
        if not f["compares"]:
            continue
        title = f["title"]
        norm = normalize_title(title)
        if not any(norm in qt or qt in norm for qt in quickref_titles):
            log("FAIL", "quickref", f"'{title}' has a 'compares' field but isn't listed in the Comparison & survey papers quick-reference section")


NEAR_DUP_THRESHOLD = 0.82
_NEAR_DUP_MIN_LEN_RATIO = NEAR_DUP_THRESHOLD / (2 - NEAR_DUP_THRESHOLD)


def check_near_duplicate_titles(entries):
    """Flags likely-duplicate catalog entries (e.g. a preprint and its
    later published version) that don't already match exactly - an exact
    case-insensitive match is caught as a hard FAIL elsewhere, this is
    the fuzzy, WARN-level sibling of that check."""
    titles = []
    for entry_id, f in entries:
        if entry_id == "EXAMPLE" or "TODO" in f["abstract"] or not f["abstract"]:
            continue
        titles.append((entry_id, f["title"], normalize_title(f["title"])))

    for i in range(len(titles)):
        id1, t1, n1 = titles[i]
        for j in range(i + 1, len(titles)):
            id2, t2, n2 = titles[j]
            if t1.lower() == t2.lower() or n1 == n2:
                continue  # exact match, already a FAIL via check_catalog_entries

            # Catches "Title" vs. "Title (Preprint Version)"/"Title: A Review" -
            # SequenceMatcher.ratio() is length-sensitive and can mathematically
            # fail to reach the threshold here even though this is exactly the
            # pattern most worth flagging (same work, an appended qualifier).
            shorter_n, longer_n = sorted((n1, n2), key=len)
            if len(shorter_n) >= 12 and shorter_n in longer_n:
                log(
                    "WARN", "near-duplicate",
                    f"'{t1}' ({id1}) and '{t2}' ({id2}) - one title is a prefix/substring "
                    "of the other - check whether these are the same source (e.g. "
                    "preprint vs. published version) before treating them as two entries",
                )
                continue

            shorter, longer = sorted((len(n1), len(n2)))
            if longer == 0 or shorter / longer < _NEAR_DUP_MIN_LEN_RATIO:
                continue  # provably can't reach the threshold, skip the expensive check
            ratio = SequenceMatcher(None, n1, n2).ratio()
            if ratio >= NEAR_DUP_THRESHOLD:
                log(
                    "WARN", "near-duplicate",
                    f"'{t1}' ({id1}) and '{t2}' ({id2}) are {ratio:.0%} similar by title "
                    "- check whether these are the same source (e.g. preprint vs. "
                    "published version) before treating them as two entries",
                )


def build_quickref_lines(entries):
    lines = []
    for entry_id, f in entries:
        if entry_id == "EXAMPLE" or "TODO" in f["abstract"] or not f["abstract"]:
            continue
        if not f["compares"]:
            continue
        lines.append(f"- **{f['title']}** — {f['compares']}")
    return lines


def fix_quickref(catalog_text, entries):
    """Regenerates the Comparison & survey papers quick-reference section
    from entries' own compares fields, replacing whatever was there by
    hand - this section should never need manual upkeep."""
    generated = "\n".join(build_quickref_lines(entries))
    pattern = re.compile(
        r"(## Comparison & survey papers \(quick reference\)\s*\n\n"
        r"Entries with a populated `compares` field.*?\n\n)"
        r".*?"
        r"(\n\n---)",
        re.DOTALL,
    )
    new_text, n = pattern.subn(lambda m: m.group(1) + generated + m.group(2), catalog_text, count=1)
    if n == 0:
        return catalog_text, False
    return new_text, new_text != catalog_text


def fix_tag_casing(catalog_text, canonical_lower):
    """Rewrites each entry's tags: line so every tag matching a canonical
    name (case-insensitively) uses the canonical casing exactly."""
    changed = [False]

    def fix_entry(m):
        block = m.group(0)

        def fix_tags_line(lm):
            raw_tags = [t.strip() for t in lm.group(2).split(",") if t.strip()]
            fixed_tags = [canonical_lower.get(t.lower(), t) for t in raw_tags]
            if fixed_tags != raw_tags:
                changed[0] = True
            return f"{lm.group(1)}: {', '.join(fixed_tags)}"

        return re.sub(r"^(tags):\s?(.*)$", fix_tags_line, block, count=1, flags=re.MULTILINE)

    new_text = ENTRY_RE.sub(fix_entry, catalog_text)
    return new_text, changed[0]


def check_dossiers():
    if not TOPICS_DIR.exists():
        return
    skip = {"README.md", "gaps.md", "vocabulary.md"}
    for p in sorted(TOPICS_DIR.glob("*.md")):
        if p.name in skip:
            continue
        text = p.read_text(encoding="utf-8")
        if not re.search(r"^## Open questions", text, re.MULTILINE):
            log("FAIL", "dossier", f"topics/{p.name}: missing a '## Open questions...' section")


def check_reference_index(rebuild=True):
    if not BUILD_REF_INDEX_SCRIPT.exists():
        log("WARN", "reference-index", "scripts/build_reference_index.py not found")
        return
    before = REF_INDEX_PATH.read_text(encoding="utf-8") if REF_INDEX_PATH.exists() else ""
    if rebuild:
        proc = subprocess.run(
            [sys.executable, str(BUILD_REF_INDEX_SCRIPT)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if proc.returncode != 0:
            log("FAIL", "reference-index", f"build_reference_index.py failed: {proc.stderr.strip()[:300]}")
            return
    after = REF_INDEX_PATH.read_text(encoding="utf-8") if REF_INDEX_PATH.exists() else ""
    n_entries = len(re.findall(r"^- ", after, re.MULTILINE))
    log("INFO", "reference-index", f"reference-index.md has ~{n_entries} entries")
    if rebuild and before != after:
        log("WARN", "reference-index", "reference-index.md changed after rebuild — was stale before this run (now fixed, remember to commit it)")


def summary_stats(entries, catalog_text):
    processed = [f for eid, f in entries if eid != "EXAMPLE" and f["abstract"] and "TODO" not in f["abstract"]]
    by_type = {}
    by_contrib = {}
    n_compares = 0
    for f in processed:
        by_type[f["type"]] = by_type.get(f["type"], 0) + 1
        for c in [c.strip() for c in f["contribution"].split(",") if c.strip()]:
            by_contrib[c] = by_contrib.get(c, 0) + 1
        if f["compares"]:
            n_compares += 1
    log("INFO", "summary", f"{len(processed)} processed entries by type: {dict(sorted(by_type.items()))}")
    log("INFO", "summary", f"{len(processed)} processed entries by contribution: {dict(sorted(by_contrib.items()))}")
    log("INFO", "summary", f"{n_compares} entries with a populated 'compares' field")
    log(
        "INFO", "summary",
        "Structural checks passed doesn't mean the batch is factually sound — "
        "run 2-3 real discovery queries against the catalog by hand (see "
        "ai_instructions/workflow.md) as the actual test of whether it's usable.",
    )


def load_canonical_lower():
    if not VOCAB_PATH.exists():
        return {}
    vocab_text = VOCAB_PATH.read_text(encoding="utf-8")
    canonical = set(re.findall(r"^- `([^`]+)`", vocab_text, re.MULTILINE))
    return {t.lower(): t for t in canonical}


def apply_fixes(catalog_text, entries):
    """Mechanical fixes only - tag casing and the quick-reference list are
    both pure derived views of data already in the entries, so there's
    never a judgment call in rewriting them. Returns the fixed text and a
    list of human-readable descriptions of what changed."""
    changes = []

    canonical_lower = load_canonical_lower()
    if canonical_lower:
        catalog_text, tags_changed = fix_tag_casing(catalog_text, canonical_lower)
        if tags_changed:
            changes.append("fixed tag casing to match topics/vocabulary.md")

    # Re-parse after the tag fix so the quickref regeneration (which only
    # reads title/compares, unaffected by tags) still works off matching text.
    entries = parse_catalog(catalog_text)
    catalog_text, quickref_changed = fix_quickref(catalog_text, entries)
    if quickref_changed:
        changes.append("regenerated the Comparison & survey papers quick-reference list")

    return catalog_text, changes


def main():
    rebuild = "--no-rebuild-index" not in sys.argv
    do_fix = "--fix" in sys.argv
    catalog_text = CATALOG_PATH.read_text(encoding="utf-8")
    entries = parse_catalog(catalog_text)

    if do_fix:
        fixed_text, changes = apply_fixes(catalog_text, entries)
        if changes:
            CATALOG_PATH.write_text(fixed_text, encoding="utf-8")
            print("Applied fixes:")
            for c in changes:
                print(f"  - {c}")
        else:
            print("--fix: nothing to fix.")
        catalog_text = fixed_text
        entries = parse_catalog(catalog_text)

    allowed_types, allowed_contrib, exempt_types = load_schema()

    check_catalog_entries(entries, allowed_types, allowed_contrib, exempt_types)
    check_notes_cross_consistency(entries)
    check_note_content(entries)
    check_tag_vocabulary(entries)
    check_comparison_quickref(entries, catalog_text)
    check_near_duplicate_titles(entries)
    check_dossiers()
    check_reference_index(rebuild=rebuild)
    summary_stats(entries, catalog_text)

    n_fail = sum(1 for lvl, _, _ in results if lvl == "FAIL")
    n_warn = sum(1 for lvl, _, _ in results if lvl == "WARN")
    n_info = sum(1 for lvl, _, _ in results if lvl == "INFO")

    for lvl in ("FAIL", "WARN", "INFO"):
        rows = [r for r in results if r[0] == lvl]
        if not rows:
            continue
        print(f"\n=== {lvl} ({len(rows)}) ===")
        for _, cat, msg in rows:
            print(f"[{cat}] {msg}")

    print(f"\n{len(entries)} catalog entries checked — {n_fail} FAIL, {n_warn} WARN, {n_info} INFO")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
