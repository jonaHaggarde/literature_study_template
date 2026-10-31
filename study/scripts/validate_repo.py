#!/usr/bin/env python3
"""
Repo health check — rerun after every batch of new PDFs.

Deterministic, structural checks only (this is NOT a test of whether the
notes/summaries are factually correct — that still needs a human/AI
spot-check of a few real discovery queries, which this script cannot do).
What it *does* catch: catalog/notes/manifest going out of sync, missing
Implementation Notes, stale placeholder entries, tag-casing drift from
topics/vocabulary.md, type/contribution values drifting from
ai_instructions/catalog-schema.md, a stale "Comparison & survey papers"
quick-reference list, dossiers missing their required Open-questions
section, unbalanced mermaid fences, article citations without a
bibliography entry, malformed method cards, a stale article table, and whether reference-index.md and
catalog-index.md are up to date with the current notes/ and catalog.md.

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
    python scripts/validate_repo.py --no-rebuild-index   # skip rebuilding
                                                         # reference-index.md /
                                                         # catalog-index.md

Exit code: 1 if any FAIL, 0 otherwise (WARN/INFO never fail the run).
"""

import json
import os
from datetime import date
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import method_cards  # noqa: E402
import verification  # noqa: E402
import build_bibliography as bibliography  # noqa: E402
import article_version  # noqa: E402
import intake_check  # noqa: E402
import scope_sync  # noqa: E402
import style_check  # noqa: E402
import build_decision_trees as decision_trees  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog.md"
NOTES_DIR = REPO_ROOT / "notes"
TOPICS_DIR = REPO_ROOT / "topics"
VOCAB_PATH = TOPICS_DIR / "vocabulary.md"
SCHEMA_PATH = REPO_ROOT / "ai_instructions" / "catalog-schema.md"
MANIFEST_PATH = REPO_ROOT / "manifest.json"
REF_INDEX_PATH = REPO_ROOT / "reference-index.md"
BUILD_REF_INDEX_SCRIPT = REPO_ROOT / "scripts" / "build_reference_index.py"
CATALOG_INDEX_PATH = REPO_ROOT / "catalog-index.md"
BUILD_CATALOG_INDEX_SCRIPT = REPO_ROOT / "scripts" / "build_catalog_index.py"
# theory/ lives at the repo root, one level above study/, when this
# template is used with its full project layout. Checked opportunistically
# so study/ still validates standalone.
THEORY_DIR = REPO_ROOT.parent / "theory"
# articles/ holds the LaTeX articles, one folder each (review, ...), also at the repo root.
ARTICLES_DIR = REPO_ROOT.parent / "articles"
ARTICLE_DIR = ARTICLES_DIR / "review"  # the review article: its derived table and status banner
BUILD_ARTICLE_TABLE_SCRIPT = REPO_ROOT / "scripts" / "build_review_table.py"
BUILD_BIBLIOGRAPHY_SCRIPT = REPO_ROOT / "scripts" / "build_bibliography.py"
# Articles that report the literature and must contain no decisions; the rationale and the
# specification are *about* decisions, so decision language is expected there.
DECISION_FREE_ARTICLES = {"map", "review"}
ARTICLE_ROWS_PATH = ARTICLE_DIR / "sections" / "comparison_rows.tex"
ARTICLE_REFS_PATH = ARTICLE_DIR / "sections" / "references.tex"
ARTICLE_MAIN_PATH = ARTICLE_DIR / "main.tex"

# ai_instructions/catalog-schema.md's budget for the summary field. Past
# this it's a WARN, never a FAIL - a genuinely dense entry is allowed to
# run long, the budget is a nudge toward writing the complement of the
# other fields rather than a neutral abstract.
SUMMARY_BUDGET_CHARS = 400

# Values people write instead of leaving a field empty. The schema says
# to omit; a literal placeholder survives into the index and into every
# grep that filters on the field.
PLACEHOLDER_VALUES = {"n/a", "na", "none", "-", "--", "tbd", "null"}

# ai_instructions/catalog-schema.md's tag ceiling. A WARN, not a FAIL -
# an occasional genuinely cross-cutting document exists, but over-tagging
# is the normal failure and it is invisible until the corpus is large.
MAX_TAGS_PER_ENTRY = 5

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
    "compares", "tags", "note", "source", "summary",
}
ENTRY_RE = re.compile(
    r"^<!--\s*entry:(?P<id>.+?)\s*-->(?P<body>.*?)^<!--\s*/entry\s*-->",
    re.DOTALL | re.MULTILINE,
)
FIELD_START_RE = re.compile(
    r"^(" + "|".join(ENTRY_FIELDS) + r"):[ \t]?(.*)$"
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
        is_stub = "TODO" in f["summary"] or not f["summary"]
        if is_stub:
            log("INFO", "unprocessed", f"'{title}' is still a stub (TODO summary) — not yet annotated")
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

        if len(f["summary"]) < 80:
            log("WARN", "schema", f"'{title}': summary looks unusually short ({len(f['summary'])} chars)")
        elif len(f["summary"]) > SUMMARY_BUDGET_CHARS:
            log(
                "WARN", "schema",
                f"'{title}': summary is {len(f['summary'])} chars, over the "
                f"{SUMMARY_BUDGET_CHARS}-char budget — check it isn't restating "
                "approach/compares/tags (see ai_instructions/catalog-schema.md)",
            )

        for field in ("approach", "contribution", "compares", "tags", "summary"):
            if f[field].strip().lower() in PLACEHOLDER_VALUES:
                log(
                    "FAIL", "schema",
                    f"'{title}': field '{field}' is the placeholder '{f[field].strip()}' — "
                    "leave it empty instead (see ai_instructions/catalog-schema.md, "
                    "'Empty fields: omit, never write n/a')",
                )

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
        if entry_id == "EXAMPLE" or "TODO" in f["summary"] or not f["summary"]:
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

    # Usage counts, not just presence: a non-canonical tag used once is a
    # legitimate one-off (a named dataset, a single instrument) and
    # vocabulary.md says so explicitly. A non-canonical tag used by two or
    # more entries has become load-bearing - people will query on it - and
    # is exactly how one concept quietly acquires two spellings and splits
    # its own search results. So: FAIL on recurring, WARN on single-use.
    usage = {}
    n_tagged_entries = 0
    for entry_id, f in entries:
        if entry_id == "EXAMPLE" or not f["tags"] or "TODO" in f["summary"] or not f["summary"]:
            continue
        n_tagged_entries += 1
        tags = [t.strip() for t in f["tags"].split(",") if t.strip()]
        for tag in set(tags):
            usage[tag] = usage.get(tag, 0) + 1
        if len(tags) > MAX_TAGS_PER_ENTRY:
            log(
                "WARN", "vocabulary",
                f"'{f['title'] or entry_id}': {len(tags)} tags, over the "
                f"{MAX_TAGS_PER_ENTRY}-tag ceiling — tags describe what a document "
                "contributes, not what it mentions (see ai_instructions/catalog-schema.md)",
            )

    one_offs = []
    for tag in sorted(usage):
        if tag in canonical:
            continue
        if tag.lower() in canonical_lower:
            log("FAIL", "tag-casing", f"tag '{tag}' differs only in case from canonical '{canonical_lower[tag.lower()]}' — fix casing")
        elif usage[tag] >= 2:
            log(
                "FAIL", "vocabulary",
                f"tag '{tag}' is used by {usage[tag]} entries but isn't in "
                "topics/vocabulary.md — a recurring tag is load-bearing, add it "
                "as canonical (or fold it into an existing canonical tag)",
            )
        else:
            one_offs.append(tag)
    if one_offs:
        log(
            "WARN", "vocabulary",
            f"{len(one_offs)} single-use tag(s) not in topics/vocabulary.md — fine as "
            f"genuine one-offs, but check for near-duplicates of canonical terms: {', '.join(one_offs)}",
        )


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
        if entry_id == "EXAMPLE" or "TODO" in f["summary"] or not f["summary"]:
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
        if entry_id == "EXAMPLE" or "TODO" in f["summary"] or not f["summary"]:
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
        if entry_id == "EXAMPLE" or "TODO" in f["summary"] or not f["summary"]:
            continue
        if not f["compares"]:
            continue
        lines.append(f"- **{f['title']}** — {f['compares']}")
    if not lines:
        # Nothing to list yet (e.g. a fresh template with no processed
        # comparison-study entries) - fall back to the placeholder rather
        # than collapsing the section to blank lines.
        lines.append("<!-- - **Title** — what's compared and on what basis -->")
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
            if fixed_tags == raw_tags:
                return lm.group(0)
            changed[0] = True
            return f"{lm.group(1)}: {', '.join(fixed_tags)}"

        return re.sub(r"^(tags):[ \t]?(.*)$", fix_tags_line, block, count=1, flags=re.MULTILINE)

    new_text = ENTRY_RE.sub(fix_entry, catalog_text)
    return new_text, changed[0]


def check_dossiers():
    if not TOPICS_DIR.exists():
        return
    skip = {"README.md", "gaps.md", "vocabulary.md", "families.md"}
    for p in sorted(TOPICS_DIR.glob("*.md")):
        if p.name in skip:
            continue
        text = p.read_text(encoding="utf-8")
        if not re.search(r"^## Open questions", text, re.MULTILINE):
            log("FAIL", "dossier", f"topics/{p.name}: missing a '## Open questions...' section")


MERMAID_FENCE_RE = re.compile(r"^\s*```", re.MULTILINE)


def check_mermaid(entries):
    """Two different checks, deliberately at different severities.

    Balanced fences are a hard error: an unclosed ```mermaid block renders
    the rest of the document as garbage, and that is mechanical, not a
    judgment call. A *missing* diagram is at most a warning - the diagram
    convention (see the repo root CLAUDE.md) is advisory, a document with
    no process or ordering to draw should not be forced to invent one, and
    a hard check on a judgment call is the kind of check people start
    routing around."""
    files = sorted(REPO_ROOT.rglob("*.md"))
    files = [f for f in files if "notes" not in f.relative_to(REPO_ROOT).parts]
    if THEORY_DIR.exists():
        files += sorted(THEORY_DIR.glob("*.md"))

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = "../" + path.relative_to(REPO_ROOT.parent).as_posix()

        if len(MERMAID_FENCE_RE.findall(text)) % 2 != 0:
            log(
                "FAIL", "mermaid",
                f"{rel}: odd number of ``` fences — an unclosed block renders "
                "the rest of the file as garbage",
            )

    # Advisory: dossiers and theory/ explainers are the two places where a
    # diagram carries most of the teaching, per the root CLAUDE.md.
    dossiers = [p for p in TOPICS_DIR.glob("*.md")
                if p.name not in {"README.md", "gaps.md", "vocabulary.md", "families.md"}] if TOPICS_DIR.exists() else []
    theory = [p for p in THEORY_DIR.glob("*.md") if p.name != "README.md"] if THEORY_DIR.exists() else []
    for path in dossiers + theory:
        text = path.read_text(encoding="utf-8")
        if "```mermaid" not in text:
            where = "topics" if path in dossiers else "../theory"
            log(
                "WARN", "mermaid",
                f"{where}/{path.name}: no mermaid diagram — advisory only, but this "
                "is the file type where one usually does the most work (see the "
                "repo root CLAUDE.md, 'Diagrams')",
            )


def check_articles():
    r"""Every article under articles/ has its own references.bib, generated from
    what it cites. A \cite with no entry there renders as [?] and nothing in the
    build fails, so it is a hard error. The remaining \todo count is information,
    never a failure: a draft is allowed to be unfinished."""
    comment_re = re.compile(r"(?<!\\)%.*")
    todo_re = re.compile(r"\\todo\{")
    dirs = bibliography.article_dirs()
    todos = 0
    for adir in dirs:
        bib_path = adir / "references.bib"
        have = bibliography.bib_keys(bib_path.read_text(encoding="utf-8")) if bib_path.exists() else set()
        for key in bibliography.cited_keys_in_order(adir):
            if key not in have:
                log("FAIL", "article",
                    f"articles/{adir.name}: \\cite{{{key}}} has no entry in its references.bib "
                    "(it is in neither study/catalog.md nor articles/common/references_extra.bib)")
        for path in adir.rglob("*.tex"):
            todos += len(todo_re.findall(comment_re.sub("", path.read_text(encoding="utf-8", errors="replace"))))
    if dirs:
        log("INFO", "article", f"{todos} \\todo marker(s) remaining in articles/")


def check_article_style():
    """Advisory style check on the hand-written article text (style_check.py, rules in
    ai_instructions/article-style.md). Clear problems are warnings, capped per article so one
    padded draft does not bury everything else; judgment calls are only counted. Nothing here
    fails a build: a style call is the kind of check people start routing around if it can."""
    phrases = style_check.load_phrases()
    for adir in bibliography.article_dirs():
        findings = style_check.check_article(adir, phrases)
        problems = [f for f in findings if f.severity == "problem"]
        for f in problems[:8]:
            log("WARN", "style", f"articles/{adir.name}/{f.file}:{f.line} {f.rule}: {f.text}")
        if len(problems) > 8:
            log("WARN", "style", f"articles/{adir.name}: {len(problems) - 8} more style problem(s); "
                                 f"run `python scripts/style_check.py {adir.name}`")
        judgments = len(findings) - len(problems)
        if judgments:
            log("INFO", "style", f"articles/{adir.name}: {judgments} style judgment call(s); "
                                 f"run `python scripts/style_check.py {adir.name}`")


def check_scope_sync():
    """scope.md follows the accepted definition article (scope_sync.py). Stale or never
    derived is a warning, not a failure: updating it waits until the user says they are ready
    after a few refinements, so a failure would only push for an update on every change."""
    code, message = scope_sync.state()
    if code in ("stale", "unstamped"):
        log("WARN", "scope", message)
    elif code != "no-pipeline":
        log("INFO", "scope", message)


def check_intake():
    """intake/intake.md is Claude's digest of the user's input and the definition article
    cites its IDs. A duplicate or sourceless line, or a cited ID that does not exist, breaks
    the trace from the accepted article back to what the user said, so those are hard errors."""
    found, count = intake_check.check_all()
    for severity, message in found:
        log(severity, "intake", message)
    for pdf in intake_check.pending():
        log("WARN", "intake",
            f"intake/{pdf.relative_to(intake_check.INTAKE_DIR).as_posix()}: not converted yet (or changed since); "
            "run `python study/scripts/convert_intake.py`")
    for path in intake_check.unreadable():
        log("INFO", "intake",
            f"intake/{path.relative_to(intake_check.INTAKE_DIR).as_posix()}: an image or office file is not "
            "converted; give a PDF or text, or decide on the vision step")
    log("INFO", "intake", f"{count} intake line(s)")


def check_article_versions():
    """Every article keeps a version history, so it is never edited silently. A file
    changed since the last recorded version is a warning, and a failure in CI (where the
    environment variable CI is set), so an edit that skipped `article_version.py edit`
    cannot be merged. The printed table is derived, and rewritten here."""
    severity = "FAIL" if os.environ.get("CI") else "WARN"
    for adir in bibliography.article_dirs():
        stale = article_version.stale_files(adir)
        if stale is None:
            log("WARN", "article-version",
                f"articles/{adir.name}: no versions.json; run `python scripts/article_version.py {adir.name} draft`")
            continue
        if stale:
            names = ", ".join(article_version.short_name(s) for s in stale)
            log(severity, "article-version",
                f"articles/{adir.name}: changed since version {article_version.load(adir)['rows'][-1]['version']} "
                f"({names}); record it with `python scripts/article_version.py {adir.name} edit --summary ...`")
        article_version.write_table(adir)


def value_is_unlisted(value, families):
    return bool(value.strip()) and value.strip() not in families


def check_method_cards(entries, exempt_types):
    """Method cards (ai_instructions/method-card.md) are free text in a
    note, and the article table is built from them, so a malformed card
    ends up in print. Structural problems are warnings except a literal
    placeholder value, which is a FAIL for the same reason it is in the
    catalog. A note with no cards is normal (a survey, a standard), so
    absence is only counted."""
    fields = set(method_cards.load_fields())
    families = method_cards.load_families()
    processed = n_with = n_cards = 0
    for entry_id, f in entries:
        if entry_id == "EXAMPLE" or not f["summary"] or "TODO" in f["summary"]:
            continue
        processed += 1
        note = REPO_ROOT / f["note"] if f["note"] else None
        if not note or not note.exists():
            continue
        cards = method_cards.parse_cards(note.read_text(encoding="utf-8"))
        if not cards:
            continue
        n_with += 1
        title = f["title"] or entry_id
        if f["type"] in exempt_types:
            log("WARN", "method-cards", f"'{title}': type '{f['type']}' is field-exempt but the note has method cards")
        seen = set()
        for name, values in cards:
            n_cards += 1
            if name.lower() in seen:
                log("WARN", "method-cards", f"'{title}': duplicate card name '{name}'")
            seen.add(name.lower())
            for key in values:
                if key == method_cards.READ_FROM_KEY:
                    if values[key] not in method_cards.READ_FROM_VALUES:
                        log("WARN", "method-cards",
                            f"'{title}' / '{name}': read_from must be one of "
                            f"{', '.join(method_cards.READ_FROM_VALUES)}, not '{values[key]}'")
                elif key == method_cards.FAMILY_KEY:
                    if value_is_unlisted(values[key], families):
                        log("WARN", "method-cards", f"'{title}' / '{name}': family '{values[key]}' is not in topics/families.md (propose it there, or fold it into an existing family)")
                elif key not in fields:
                    log("WARN", "method-cards", f"'{title}' / '{name}': field '{key}' is not in ai_instructions/method-card.md")
            if not any(values.get(k, "") for k in fields):
                log("WARN", "method-cards", f"'{title}' / '{name}': card has no filled fields; delete it rather than leave it empty")
            for key, value in values.items():
                if value.strip().lower() in PLACEHOLDER_VALUES:
                    log(
                        "FAIL", "method-cards",
                        f"'{title}' / '{name}': field '{key}' is the placeholder '{value}' — "
                        "leave it empty instead (see ai_instructions/method-card.md)",
                    )
    log("INFO", "method-cards", f"{n_with} of {processed} processed entries have method cards ({n_cards} card(s) in total)")


def check_article_table(rebuild=True):
    """The review's comparison_rows.tex and every article's references.bib and
    sections/references.tex are derived (from the method cards and the catalog). A
    stale table or bibliography silently describes an out-of-date corpus in print, so
    they are rebuilt here, with a warning when they had to change."""
    if not ARTICLES_DIR.exists():
        return
    scripts = ([BUILD_ARTICLE_TABLE_SCRIPT] if ARTICLE_DIR.exists() else []) + [BUILD_BIBLIOGRAPHY_SCRIPT]
    missing = [sc.name for sc in scripts if not sc.exists()]
    if missing:
        log("WARN", "article-table", f"scripts/{', '.join(missing)} not found")
        return

    def snapshot():
        paths = [ARTICLE_ROWS_PATH]
        for adir in bibliography.article_dirs():
            paths += [adir / "references.bib", adir / "sections" / "references.tex"]
        return tuple(p.read_text(encoding="utf-8") if p.exists() else "" for p in paths)

    before = snapshot()
    for sc in scripts:
        args = [sys.executable, str(sc)] + ([] if rebuild else ["--check"])
        proc = subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT)
        if rebuild and proc.returncode != 0:
            log("FAIL", "article-table", f"{sc.name} failed: {proc.stderr.strip()[:300]}")
            return
        if not rebuild and proc.returncode != 0:
            log("WARN", "article-table", f"articles/ derived files are stale; run scripts/{sc.name}")
    if rebuild and before != snapshot():
        log("WARN", "article-table",
            "articles/ derived files (the review's comparison_rows.tex, bibliographies) changed after "
            "rebuild: they were stale before this run (now fixed, remember to commit them)")


def check_verification(entries):
    """Method cards are checked against their source by the row-verifier
    agent (articles/review/workflow.md, step 6). Verdicts are stored against a hash
    of the card, so an edited card is stale. The article's status banner
    says 'not verified'; removing it while cards are unchecked is the one
    thing here that is warned about, because that banner is the only thing
    telling a reader how far to trust the table."""
    statuses = verification.card_statuses(entries)
    counts = {}
    for _key, status in statuses:
        counts[status] = counts.get(status, 0) + 1
    log(
        "INFO", "verification",
        f"{counts.get('verified', 0)} of {len(statuses)} method card(s) verified "
        f"({counts.get('unverified', 0)} unverified, {counts.get('stale', 0)} stale, "
        f"{counts.get('failed', 0)} failed/unclear, {counts.get('ocr-only', 0)} resting on OCR text)",
    )
    for key, status in statuses:
        if status == "stale":
            log("WARN", "verification", f"{key}: card changed since it was verified — verify again")
        elif status == "failed":
            log("WARN", "verification", f"{key}: last verification did not pass — fix the card or the note")
    for key in verification.orphan_records(entries):
        log("WARN", "verification", f"verification.json has a record for a card that no longer exists: {key}")
    if ARTICLE_MAIN_PATH.exists() and statuses:
        banner = "not verified" in ARTICLE_MAIN_PATH.read_text(encoding="utf-8")
        unchecked = len(statuses) - counts.get("verified", 0)
        if not banner and unchecked:
            log(
                "WARN", "verification",
                f"articles/review/main.tex no longer carries the 'not verified' banner, but "
                f"{unchecked} method card(s) are not verified",
            )


# Phrases that signal a decision about the project rather than a report of
# the literature. The review article must contain none (root CLAUDE.md).
# Advisory: a quoted source can legitimately say "we chose", and a check on
# a judgment call that fails builds is one people learn to route around.
DECISION_PHRASES = [
    r"\bwe (?:chose|choose|decided|decide|selected|select|adopted|adopt|recommend|will use|opted)\b",
    r"\bour (?:design|choice|choices|decision|algorithm|controller|system|solution|implementation)\b",
    r"\b(?:is|are) the (?:best|preferred|recommended) (?:choice|option|method|approach|solution)\b",
    r"\bshould be (?:used|chosen|adopted|selected)\b",
    r"\bfor (?:this|our) project\b",
]
DECISION_RE = re.compile("|".join(DECISION_PHRASES), re.IGNORECASE)


def check_article_decisions():
    """Warn on decision language in the survey-phase articles (DECISION_FREE_ARTICLES).
    They report what the literature says; deciding the product is a later phase. The
    rationale and specification articles are about decisions, so they are not checked."""
    comment_re = re.compile(r"(?<!\\)%.*")
    for adir in bibliography.article_dirs():
        if adir.name not in DECISION_FREE_ARTICLES:
            continue
        for path in sorted(adir.rglob("*.tex")):
            rel = path.relative_to(ARTICLES_DIR.parent).as_posix()
            for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                m = DECISION_RE.search(comment_re.sub("", line))
                if m:
                    log(
                        "WARN", "article-decision",
                        f"{rel}:{lineno}: '{m.group(0)}' reads like a decision, not a report of the "
                        "literature: this article contains no decisions (root CLAUDE.md)",
                    )


# A relative path into study/notes/, as written in a root document's
# References section (root CLAUDE.md): `../study/notes/x.md`, `study/notes/x.md`.
NOTE_REF_RE = re.compile(r"(?<![A-Za-z0-9_])study/notes/([^\s)\]`'\"<>*]+?\.md)")
# Root-level folders and files that cite catalogued sources.
ROOT_CITING_DOCS = ["decisions.md", "timeline.md"]
ROOT_CITING_DIRS = ["ideation", "theory", "meetings", "articles", "requirements"]


def find_note_refs(text):
    """Note paths (relative to study/notes/) cited in a root document."""
    return list(dict.fromkeys(NOTE_REF_RE.findall(text)))


def check_root_citations(entries):
    """Root documents cite catalogued papers by path into study/notes/. A
    citation of a note that does not exist is a broken link, so it fails, as a
    \\cite with no \\bibitem does. A citation of a note whose catalog entry is
    still an unfilled stub is only a warning: the file exists, but the document
    is leaning on something nobody has read yet, and a structural check cannot
    see that any other way (a crashed session once left a document resting on
    exactly such a stub, and everything still validated). README.md files are
    skipped: they document the convention with example paths and cite nothing."""
    root = REPO_ROOT.parent
    files = [root / name for name in ROOT_CITING_DOCS]
    for d in ROOT_CITING_DIRS:
        base = root / d
        if base.exists():
            files += [p for p in sorted(base.rglob("*.md"))
                      if "_templates" not in p.parts and p.name != "README.md"]
    stubs = {f["note"] for _id, f in entries
             if f["note"] and (not f["summary"] or "TODO" in f["summary"])}
    for path in files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(root).as_posix()
        for name in find_note_refs(text):
            note = REPO_ROOT / "notes" / name
            if not note.exists():
                log("FAIL", "root-citation", f"{rel}: cites study/notes/{name}, which does not exist")
            elif f"notes/{name}" in stubs:
                log("WARN", "root-citation",
                    f"{rel}: cites study/notes/{name}, whose catalog entry is still an unfilled stub")


def check_path_lengths():
    """Windows rejects paths past about 260 characters, and the failure shows
    up at `git add`, long after the file was created. Warn well before."""
    limit = 230
    for base in (NOTES_DIR, REPO_ROOT / "PDFs"):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and len(str(path)) > limit:
                log(
                    "WARN", "path-length",
                    f"{path.relative_to(REPO_ROOT).as_posix()}: full path is {len(str(path))} "
                    f"characters (Windows limit is about 260) - shorten the filename",
                )


def check_decision_trees(rebuild=True):
    """A decision tree is a table (the source) plus a generated mermaid diagram.
    A malformed table is a FAIL, since the diagram built from it would be wrong;
    a stale diagram is rebuilt (or warned about), like the other derived files.
    The statistics are information only: they say how much of a decision rests on
    options nobody examined, which no structural rule can judge."""
    for path in decision_trees.tree_files():
        text = path.read_text(encoding="utf-8")
        if "<!-- decision-tree" not in text:
            continue
        rel = path.relative_to(REPO_ROOT.parent).as_posix()
        new_text, results = decision_trees.process_text(text)
        any_problem = False
        for rows, problems in results:
            for pr in problems:
                log("FAIL", "decision-tree", f"{rel}: {pr}")
                any_problem = True
            if rows and "_templates" not in path.parts:
                st = decision_trees.stats(rows)
                log(
                    "INFO", "decision-tree",
                    f"{rel}: {st['decided']} of {st['questions']} questions decided; "
                    f"{st['explored']} of {st['alternatives']} rejected alternatives examined; "
                    f"{st['motivations_missing']} motivation(s) still to write",
                )
        if new_text != text and not any_problem:
            if rebuild:
                path.write_text(new_text, encoding="utf-8")
                log("WARN", "decision-tree", f"{rel}: diagram was stale, rebuilt (remember to commit it)")
            else:
                log("WARN", "decision-tree", f"{rel}: diagram is stale; run scripts/build_decision_trees.py")


def check_gaps_index(rebuild=True):
    """topics/gaps.md's auto-aggregated blocks are derived from the dossiers'
    Open questions and from the unexamined alternatives of decision trees. A
    stale block lists gaps that are closed or misses ones that were just
    created, so it is rebuilt here, with a warning when it had to change."""
    script = REPO_ROOT / "scripts" / "build_gaps_index.py"
    gaps = TOPICS_DIR / "gaps.md"
    if not rebuild or not script.exists() or not gaps.exists():
        return
    before = gaps.read_text(encoding="utf-8")
    proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, cwd=REPO_ROOT)
    if proc.returncode != 0:
        log("FAIL", "gaps-index", f"build_gaps_index.py failed: {proc.stderr.strip()[:300]}")
        return
    if gaps.read_text(encoding="utf-8") != before:
        log("WARN", "gaps-index",
            "topics/gaps.md changed after rebuild - was stale before this run (now fixed, remember to commit it)")


def check_usage_log():
    """.claude/usage-log.md records how the repo is used. It is written by a
    script that enforces its own format, so a problem here means someone edited
    it by hand. Entries that look like content are worth a warning because the
    log must never carry the project's subject; the count is information only."""
    script = REPO_ROOT.parent / ".claude" / "log_usage.py"
    log_path = REPO_ROOT.parent / ".claude" / "usage-log.md"
    if not script.exists() or not log_path.exists():
        return
    import importlib.util
    spec = importlib.util.spec_from_file_location("log_usage", script)
    lu = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lu)
    entry_re = re.compile(r"^- \*\*\d{4}-\d{2}-\d{2}\*\*( \[(" + "|".join(lu.KINDS) + r")\])? \u2014 (.+)$")
    n = 0
    for lineno, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("- **"):
            continue
        n += 1
        m = entry_re.match(line)
        if not m:
            log("WARN", "usage-log", f".claude/usage-log.md:{lineno}: not in the entry format "
                "(`- **date** [kind] \u2014 text`); entries are written by .claude/log_usage.py")
            continue
        for problem in lu.check_text(m.group(3)):
            log("WARN", "usage-log", f".claude/usage-log.md:{lineno}: {problem}")
    off = (log_path.parent / lu.OFF_MARKER).exists()
    log("INFO", "usage-log", f"{n} entr{'y' if n == 1 else 'ies'} in .claude/usage-log.md"
        + (" (logging is switched off in this working copy)" if off else ""))


REQUIREMENTS_DIR = REPO_ROOT.parent / "requirements"
REQUIREMENTS_DESCRIPTIVE = {"README.md", "background.md"}
TBD_RE = re.compile(r"\bTB[DR]\b")


def requirements_too_early_reasons(scope_placeholder, n_processed, article_unfinished):
    """Why requirements written now would be premature, as readable strings
    (empty when nothing says so). Pure, so it can be tested."""
    reasons = []
    if scope_placeholder:
        reasons.append("scope.md is still a placeholder, so there is nothing defined to build requirements on")
    elif n_processed == 0:
        reasons.append("no document has been processed into the catalog yet, so there is no survey to ground values in")
    if article_unfinished:
        reasons.append("the review article is not finished (its 'not verified' status banner is still in place)")
    return reasons


def check_requirements(entries):
    """requirements/ is an optional module, described in its own README. Low-level
    requirements set before the survey is done tend to be guesses that the design
    then bends to meet, so writing them early gets a warning (never a failure: a
    project can legitimately start from a fixed customer specification). The count
    of TBD/TBR markers is information only; an honest TBD is not a defect."""
    if not REQUIREMENTS_DIR.exists():
        return
    files = [p for p in sorted(REQUIREMENTS_DIR.rglob("*"))
             if p.is_file() and p.name not in REQUIREMENTS_DESCRIPTIVE and not p.name.startswith(".")]
    if not files:
        return
    scope = REPO_ROOT / "ai_instructions" / "scope.md"
    scope_placeholder = (not scope.exists()) or "<!-- placeholder -->" in scope.read_text(encoding="utf-8")
    n_processed = sum(1 for i, f in entries
                      if i != "EXAMPLE" and f["summary"] and "TODO" not in f["summary"])
    main_tex = REPO_ROOT.parent / "articles" / "review" / "main.tex"
    article_unfinished = main_tex.exists() and "not verified" in main_tex.read_text(encoding="utf-8")
    reasons = requirements_too_early_reasons(scope_placeholder, n_processed, article_unfinished)
    if reasons:
        log(
            "WARN", "requirements",
            f"requirements/ holds {len(files)} file(s) beyond its README, written early: "
            + "; ".join(reasons)
            + ". Low-level requirements set this early tend to drive the design (see "
            "requirements/README.md): keep top-level facts in the project definition and "
            "write unknown values as TBD.",
        )
    tbd = 0
    for path in files:
        if path.suffix.lower() in {".md", ".txt", ".csv", ".tex"}:
            tbd += len(TBD_RE.findall(path.read_text(encoding="utf-8", errors="replace")))
    log("INFO", "requirements", f"{len(files)} requirements file(s), {tbd} TBD/TBR marker(s) remaining")


def check_ocr():
    """Scanned PDFs and the budgeted reading of their page images.

    A scan with no usable text that was never OCR'd is a document the study cannot
    read at all, so it is a warning (it used to be a quiet info line). OCR'd
    documents are counted, with how many equation-heavy pages have not been read
    from their images; that number is information, since most such pages do not
    matter. Pages marked (vision) must have been recorded through
    scripts/vision_pages.py: a hand-edited marker would bypass the budget's audit."""
    if not MANIFEST_PATH.exists():
        return
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    n_ocr = unread = 0
    for relpath, m in sorted(manifest.items()):
        if m.get("extraction") == "ocr":
            n_ocr += 1
            unread += len([p for p in m.get("ocr_suspect_pages", []) if p not in m.get("vision_pages", [])])
        elif m.get("low_text_yield"):
            log("WARN", "ocr",
                f"{relpath}: a scan with no usable text, not OCR'd, so the study cannot read it. "
                "Run `python scripts/ocr_support.py` to see whether OCR is available, then "
                "`python scripts/convert.py --reocr`.")
        note = REPO_ROOT / m.get("notes_path", "")
        if m.get("notes_path") and note.exists():
            marked = {int(n) for n in re.findall(r"<!-- page: (\d+) \(vision\) -->",
                                                 note.read_text(encoding="utf-8", errors="replace"))}
            stray = sorted(marked - set(m.get("vision_pages", [])))
            if stray:
                log("WARN", "ocr",
                    f"{m['notes_path']}: page(s) {stray} are marked (vision) but were not recorded through "
                    "scripts/vision_pages.py, so they escaped the page budget's audit (hand-edited?)")
    log("INFO", "ocr", f"{n_ocr} OCR'd document(s); {unread} equation-heavy page(s) not read from images")
    ledger = REPO_ROOT / ".ocr" / "ledger.json"
    if ledger.exists():
        try:
            used = int(json.loads(ledger.read_text(encoding="utf-8")).get(date.today().isoformat(), 0))
        except (ValueError, OSError):
            used = 0
        log("INFO", "ocr", f"vision usage: {used} page(s) read from images today")


def check_catalog_index(rebuild=True):
    """catalog-index.md is a derived view of catalog.md, read in full at
    the start of most sessions. A stale index is worse than no index: it
    silently answers questions from an out-of-date corpus."""
    if not BUILD_CATALOG_INDEX_SCRIPT.exists():
        log("WARN", "catalog-index", "scripts/build_catalog_index.py not found")
        return
    before = CATALOG_INDEX_PATH.read_text(encoding="utf-8") if CATALOG_INDEX_PATH.exists() else ""
    if rebuild:
        proc = subprocess.run(
            [sys.executable, str(BUILD_CATALOG_INDEX_SCRIPT)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        if proc.returncode != 0:
            log("FAIL", "catalog-index", f"build_catalog_index.py failed: {proc.stderr.strip()[:300]}")
            return
    after = CATALOG_INDEX_PATH.read_text(encoding="utf-8") if CATALOG_INDEX_PATH.exists() else ""
    if rebuild and before != after:
        log(
            "WARN", "catalog-index",
            "catalog-index.md changed after rebuild — was stale before this run "
            "(now fixed, remember to commit it)",
        )


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
    processed = [f for eid, f in entries if eid != "EXAMPLE" and f["summary"] and "TODO" not in f["summary"]]
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
    check_mermaid(entries)
    check_path_lengths()
    check_root_citations(entries)
    check_decision_trees(rebuild=rebuild)
    check_gaps_index(rebuild=rebuild)
    check_article_versions()
    check_intake()
    check_scope_sync()
    check_article_style()
    check_usage_log()
    check_ocr()
    check_requirements(entries)
    check_method_cards(entries, exempt_types)
    check_article_table(rebuild=rebuild)
    check_articles()
    check_verification(entries)
    check_article_decisions()
    check_reference_index(rebuild=rebuild)
    check_catalog_index(rebuild=rebuild)
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
