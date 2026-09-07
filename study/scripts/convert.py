#!/usr/bin/env python3
"""
Converts PDFs under PDFs/ into markdown notes under notes/, tracking
already-converted files by content hash so re-runs only touch new or
changed PDFs. Also appends stub entries to catalog.md for anything new.

Usage (from study/, with dependencies installed):
    python scripts/convert.py
    python scripts/convert.py --pdfs-dir PDFs --notes-dir notes

title/authors/year are best-effort pre-filled from each PDF's own
metadata (often empty or wrong - treat as a starting point, not fact).
Everything else (type/approach/contribution/tags/summary, and the note's
Key Findings/Implementation Notes) is left as TODO, meant to be filled in
by asking Claude to read the new notes and complete them - see
ai_instructions/workflow.md.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import pymupdf4llm
    import pymupdf
except ImportError:
    print(
        "Missing dependency 'pymupdf4llm'. Install with:\n"
        "  pip install -r scripts/requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

COPYRIGHT_NOTICE = """
--------------------------------------------------------------------
COPYRIGHT: notes/ now contains substantial extracted text from your
source documents. PDFs/ is gitignored; notes/ is NOT. That is fine for
a private study and not fine to publish - check this repository's
visibility before pushing. See README.md, "Copyright note".
--------------------------------------------------------------------"""

REPO_ROOT = Path(__file__).resolve().parent.parent
LOW_YIELD_CHARS_PER_PAGE = 40  # below this average, flag as likely-scanned

DOI_RE = re.compile(r'\b10\.\d{4,9}/[^\s"<>,]+\b')
CREATION_DATE_RE = re.compile(r"D:(\d{4})")
# Metadata titles that are just software-generated junk (export filenames,
# "Microsoft Word - X.docx", etc.) rather than a real title - not worth
# prefilling over the PDF-filename fallback.
JUNK_TITLE_RE = re.compile(r"\.(docx?|tex|pdf|rtf)\b|^Microsoft Word", re.IGNORECASE)


def best_effort_metadata(pdf_path: Path, first_pages_text: str) -> dict:
    """Pulls a best-effort title/author/year/doi from the PDF's own
    metadata and page text. PDF metadata is frequently empty, stale, or
    wrong (e.g. left over from a Word export) - this is a starting point
    for Claude/the user to verify, never treated as ground truth."""
    guess = {"title": "", "authors": "", "year": "", "doi": ""}
    try:
        doc = pymupdf.open(str(pdf_path))
        meta = doc.metadata or {}
        doc.close()
    except Exception:  # noqa: BLE001
        meta = {}

    title = (meta.get("title") or "").strip()
    if title and not JUNK_TITLE_RE.search(title) and len(title) > 4:
        guess["title"] = title

    author = (meta.get("author") or "").strip()
    if author and not JUNK_TITLE_RE.search(author):
        guess["authors"] = author

    creation_date = meta.get("creationDate") or ""
    m = CREATION_DATE_RE.search(creation_date)
    if m:
        guess["year"] = m.group(1)

    doi_match = DOI_RE.search(first_pages_text)
    if doi_match:
        guess["doi"] = doi_match.group(0).rstrip(".,);]")

    return guess


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def entry_id_for(relpath_no_ext: str) -> str:
    return relpath_no_ext


def build_note_markdown(relpath: str, pdf_hash: str, pages: list, meta_guess: dict) -> tuple[str, bool]:
    total_chars = sum(len(p.get("text", "")) for p in pages)
    avg_chars = total_chars / len(pages) if pages else 0
    low_yield = avg_chars < LOW_YIELD_CHARS_PER_PAGE

    stem = Path(relpath).stem
    title = meta_guess["title"] or stem
    lines = []
    lines.append("---")
    lines.append(f'title: "{title}"')
    lines.append(f'authors: "{meta_guess["authors"]}"')
    lines.append(f'year: "{meta_guess["year"]}"')
    lines.append('type: ""')
    lines.append("tags: []")
    lines.append(f"source_pdf: PDFs/{relpath}")
    lines.append(f"pdf_hash: {pdf_hash}")
    lines.append(f"converted_at: {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    if meta_guess["doi"]:
        lines.append(f'doi: "{meta_guess["doi"]}"')
    lines.append("---")
    lines.append("")
    if meta_guess["title"] or meta_guess["authors"] or meta_guess["year"]:
        lines.append(
            "<!-- NOTE: title/authors/year above are best-effort from the PDF's "
            "own metadata (or blank if metadata was empty/unusable) - PDF "
            "metadata is frequently wrong or stale, verify against the actual "
            "text before trusting, especially authors/year. -->"
        )
        lines.append("")
    if low_yield:
        lines.append(
            "<!-- WARNING: low text yield, this PDF may be scanned/image-based. "
            "Consider OCR (see study/README.md) and re-running convert.py. -->"
        )
        lines.append("")
    lines.append("## Key Findings")
    lines.append("")
    lines.append(
        "<!-- TODO: 3-6 sentence summary of method, key claims, and results. "
        "Fill in via Claude after conversion. -->"
    )
    lines.append("")
    lines.append("## Content")
    lines.append("")
    for i, page in enumerate(pages, start=1):
        lines.append(f"<!-- page: {i} -->")
        lines.append("")
        lines.append(page.get("text", "").strip())
        lines.append("")

    return "\n".join(lines), low_yield


CATALOG_STUB_TEMPLATE = """<!-- entry:{id} -->
title: {title}
authors: {authors}
year: {year}
type:
approach:
contribution:
compares:
tags:
note: {note_path}
source: {source_path}
summary: TODO - ask Claude to read {note_path} and fill this in (see ai_instructions/catalog-schema.md for the summary rule).
<!-- /entry -->
"""


def append_catalog_stubs(catalog_path: Path, new_entries: list) -> None:
    if not new_entries:
        return
    text = catalog_path.read_text(encoding="utf-8") if catalog_path.exists() else ""
    additions = []
    for entry_id, title, note_path, source_path, authors, year in new_entries:
        marker = f"<!-- entry:{entry_id} -->"
        if marker in text:
            continue  # already present, don't duplicate
        additions.append(
            CATALOG_STUB_TEMPLATE.format(
                id=entry_id,
                title=title,
                note_path=note_path,
                source_path=source_path,
                authors=authors,
                year=year,
            )
        )
    if additions:
        with catalog_path.open("a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(additions))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdfs-dir", default=str(REPO_ROOT / "PDFs"))
    parser.add_argument("--notes-dir", default=str(REPO_ROOT / "notes"))
    parser.add_argument("--catalog", default=str(REPO_ROOT / "catalog.md"))
    parser.add_argument("--manifest", default=str(REPO_ROOT / "manifest.json"))
    args = parser.parse_args()

    pdfs_dir = Path(args.pdfs_dir)
    notes_dir = Path(args.notes_dir)
    catalog_path = Path(args.catalog)
    manifest_path = Path(args.manifest)

    if not pdfs_dir.exists():
        print(f"No PDFs directory at {pdfs_dir}", file=sys.stderr)
        sys.exit(1)

    manifest = load_json(manifest_path)
    pdf_files = sorted(pdfs_dir.rglob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found under {pdfs_dir}")
        return

    converted, skipped, warnings = 0, 0, []
    new_catalog_entries = []

    for pdf_path in pdf_files:
        relpath = pdf_path.relative_to(pdfs_dir).as_posix()
        pdf_hash = sha256_of(pdf_path)

        existing = manifest.get(relpath)
        if existing and existing.get("hash") == pdf_hash:
            skipped += 1
            continue

        print(f"Converting: {relpath}")
        try:
            pages = pymupdf4llm.to_markdown(str(pdf_path), page_chunks=True)
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e}", file=sys.stderr)
            warnings.append(f"{relpath}: conversion failed ({e})")
            continue

        first_pages_text = "\n".join(p.get("text", "") for p in pages[:2])
        meta_guess = best_effort_metadata(pdf_path, first_pages_text)

        note_content, low_yield = build_note_markdown(relpath, pdf_hash, pages, meta_guess)

        note_relpath = Path(relpath).with_suffix(".md").as_posix()
        note_path = notes_dir / note_relpath
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(note_content, encoding="utf-8")

        manifest[relpath] = {
            "hash": pdf_hash,
            "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes_path": f"notes/{note_relpath}",
            "low_text_yield": low_yield,
        }
        converted += 1
        if low_yield:
            warnings.append(f"{relpath}: LOW TEXT YIELD, likely scanned - consider OCR")

        entry_id = entry_id_for(Path(relpath).with_suffix("").as_posix())
        new_catalog_entries.append((
            entry_id,
            meta_guess["title"] or Path(relpath).stem,
            f"notes/{note_relpath}",
            f"PDFs/{relpath}",
            meta_guess["authors"],
            meta_guess["year"],
        ))

    save_json(manifest_path, manifest)
    append_catalog_stubs(catalog_path, new_catalog_entries)

    print(f"\nDone. Converted: {converted}, skipped (unchanged): {skipped}")
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  - {w}")
    if converted:
        print(
            "\nNext step: open Claude Code in this folder and ask it to fill in the "
            "TODO fields (summary, tags, authors, key findings) for the newly added "
            "catalog entries and notes - see ai_instructions/README.md."
        )
        print(
            "Then rebuild the derived files: build_reference_index.py, "
            "build_catalog_index.py, validate_repo.py --fix."
        )
        print(COPYRIGHT_NOTICE)


if __name__ == "__main__":
    main()
