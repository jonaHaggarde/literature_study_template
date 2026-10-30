#!/usr/bin/env python3
"""
Converts PDFs under PDFs/ into markdown notes under notes/, tracking
already-converted files by content hash so re-runs only touch new or
changed PDFs. Also appends stub entries to catalog.md for anything new.

Usage (from study/, with dependencies installed):
    python scripts/convert.py                      # convert everything new or changed
    python scripts/convert.py --dry-run            # list what would happen, convert nothing
    python scripts/convert.py --only Smith2020     # only PDFs whose path contains this
    python scripts/convert.py --timeout 120        # per-file extraction limit, seconds

Triage, before converting a pile of new documents: move a PDF you do not
want processed (a whole edited book of which one chapter matters, a thesis
on an out-of-scope subject) into PDFs/_deferred/, where it is ignored until
you move it back. A PDF that is byte-identical to one already converted is
skipped and reported, whatever its filename.

Each file is extracted in a child process with a time limit, because the
layout extractor can hang on a particular PDF. On a timeout the file is
re-extracted as plain text (tables and structure are lost, and the note says
so). The manifest and catalog stub are saved after every file, so an
interrupted run loses at most the file it was on.

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
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

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

    # The PDF's creation date is when the *file* was made, which for a scan
    # or a re-hosted paper is often decades after publication (a 1960 paper
    # came out as 2023). Only prefill the year when the first pages' own text
    # contains it; a blank is better than a confident wrong value.
    creation_date = meta.get("creationDate") or ""
    m = CREATION_DATE_RE.search(creation_date)
    if m and re.search(r"(?<!\d)" + m.group(1) + r"(?!\d)", first_pages_text):
        guess["year"] = m.group(1)

    doi_match = DOI_RE.search(first_pages_text)
    if doi_match:
        guess["doi"] = doi_match.group(0).rstrip(".,);]_-")

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


# Windows limits a full path to about 260 characters, and the repo prefix,
# study/notes/ and the filename add up. conversion succeeds and `git add`
# fails much later, so note names are capped here instead. The full title
# stays in the catalog entry.
MAX_STEM = 80


def short_note_relpath(relpath: str) -> str:
    """Note path (relative to notes/) for a PDF path, with an over-long stem
    shortened to a readable prefix plus a short hash of the full stem."""
    p = Path(relpath)
    stem = p.stem
    if len(stem) > MAX_STEM:
        digest = hashlib.sha1(stem.encode("utf-8")).hexdigest()[:6]
        stem = f"{stem[:MAX_STEM - 7].rstrip('-_ ')}-{digest}"
    return p.with_name(stem + ".md").as_posix()


def entry_id_for(relpath_no_ext: str) -> str:
    return relpath_no_ext


def build_note_markdown(relpath: str, pdf_hash: str, pages: list, meta_guess: dict,
                        extraction: str = "layout") -> tuple[str, bool]:
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
    if extraction != "layout":
        lines.append(
            "<!-- WARNING: layout extraction timed out on this PDF, so the text below is a "
            "plain-text fallback: tables, equations and structure are lost or scrambled. "
            "Treat anything that depends on a table or a formula as unread. -->"
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


DEFERRED_DIR = "_deferred"
DEFAULT_TIMEOUT = 300  # seconds per file for layout extraction


CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(text: str) -> str:
    """Drop control characters (NUL, SOH, ...). Scrambled equation glyphs come
    out of the extractor as these, and one NUL makes the whole note look binary
    to grep, to git and to the tools that read it."""
    return CONTROL_RE.sub("", text)


def extract_one(pdf: str, mode: str, out: str) -> int:
    """Child-process entry point: write [{"text": ...}, ...] for one PDF."""
    if mode == "layout":
        pages = pymupdf4llm.to_markdown(pdf, page_chunks=True)
        data = [{"text": clean_text(p.get("text", ""))} for p in pages]
    else:
        doc = pymupdf.open(pdf)
        data = [{"text": clean_text(page.get_text())} for page in doc]
        doc.close()
    Path(out).write_text(json.dumps(data), encoding="utf-8")
    return 0


def extract_pages(pdf_path: Path, timeout: float) -> tuple[list, str]:
    """Extract in a child process so a hang can be killed. Returns (pages,
    extraction) where extraction is "layout" or "plain-text-fallback"."""
    last_error = ""
    for mode, limit in (("layout", timeout), ("plain", max(30.0, timeout / 4))):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "pages.json")
            try:
                proc = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--extract-one", str(pdf_path),
                     "--mode", mode, "--out", out],
                    capture_output=True, text=True, timeout=limit,
                )
            except subprocess.TimeoutExpired:
                last_error = f"{mode} extraction timed out after {limit:.0f}s"
                print(f"  {last_error}", file=sys.stderr)
                continue
            if proc.returncode == 0 and Path(out).exists():
                pages = json.loads(Path(out).read_text(encoding="utf-8"))
                return pages, ("layout" if mode == "layout" else "plain-text-fallback")
            last_error = (proc.stderr or "").strip().splitlines()[-1:] or ["unknown error"]
            last_error = f"{mode} extraction failed: {last_error[0]}"
            print(f"  {last_error}", file=sys.stderr)
    raise RuntimeError(last_error)


def page_count(pdf_path: Path) -> str:
    try:
        doc = pymupdf.open(str(pdf_path))
        n = len(doc)
        doc.close()
        return str(n)
    except Exception:  # noqa: BLE001
        return "?"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdfs-dir", default=str(REPO_ROOT / "PDFs"))
    parser.add_argument("--notes-dir", default=str(REPO_ROOT / "notes"))
    parser.add_argument("--catalog", default=str(REPO_ROOT / "catalog.md"))
    parser.add_argument("--manifest", default=str(REPO_ROOT / "manifest.json"))
    parser.add_argument("--only", action="append", default=[], metavar="TEXT",
                        help="only PDFs whose path contains TEXT (repeatable)")
    parser.add_argument("--dry-run", action="store_true",
                        help="list what would be converted, deferred or skipped; convert nothing")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"seconds allowed for layout extraction of one file (default {DEFAULT_TIMEOUT})")
    parser.add_argument("--extract-one", help=argparse.SUPPRESS)
    parser.add_argument("--mode", default="layout", help=argparse.SUPPRESS)
    parser.add_argument("--out", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.extract_one:
        return extract_one(args.extract_one, args.mode, args.out)

    pdfs_dir = Path(args.pdfs_dir)
    notes_dir = Path(args.notes_dir)
    catalog_path = Path(args.catalog)
    manifest_path = Path(args.manifest)

    if not pdfs_dir.exists():
        print(f"No PDFs directory at {pdfs_dir}", file=sys.stderr)
        sys.exit(1)

    manifest = load_json(manifest_path)
    all_pdfs = sorted(pdfs_dir.rglob("*.pdf"))
    deferred = [p for p in all_pdfs if DEFERRED_DIR in p.relative_to(pdfs_dir).parts]
    pdf_files = [p for p in all_pdfs if p not in deferred]
    if args.only:
        pdf_files = [p for p in pdf_files
                     if any(t.lower() in p.relative_to(pdfs_dir).as_posix().lower() for t in args.only)]

    if not all_pdfs:
        print(f"No PDFs found under {pdfs_dir}")
        return 0

    known_hashes = {m.get("hash"): rel for rel, m in manifest.items() if m.get("hash")}
    converted, skipped, duplicates, warnings = 0, 0, 0, []

    for pdf_path in pdf_files:
        relpath = pdf_path.relative_to(pdfs_dir).as_posix()
        pdf_hash = sha256_of(pdf_path)

        existing = manifest.get(relpath)
        if existing and existing.get("hash") == pdf_hash:
            skipped += 1
            continue

        twin = known_hashes.get(pdf_hash)
        if twin and twin != relpath:
            duplicates += 1
            msg = f"{relpath}: byte-identical to already-converted {twin}; skipped"
            warnings.append(msg)
            print(f"Duplicate:  {msg}")
            continue

        if args.dry_run:
            print(f"Would convert: {relpath}  ({page_count(pdf_path)} pages, "
                  f"{pdf_path.stat().st_size // 1024} KB)")
            continue

        print(f"Converting: {relpath}")
        try:
            pages, extraction = extract_pages(pdf_path, args.timeout)
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e}", file=sys.stderr)
            warnings.append(f"{relpath}: conversion failed ({e})")
            continue
        if extraction != "layout":
            warnings.append(f"{relpath}: layout extraction timed out, used plain-text fallback "
                            f"(tables and structure lost)")

        first_pages_text = "\n".join(p.get("text", "") for p in pages[:2])
        meta_guess = best_effort_metadata(pdf_path, first_pages_text)

        note_content, low_yield = build_note_markdown(relpath, pdf_hash, pages, meta_guess, extraction)

        note_relpath = short_note_relpath(relpath)
        note_path = notes_dir / note_relpath
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(note_content, encoding="utf-8")

        manifest[relpath] = {
            "hash": pdf_hash,
            "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes_path": f"notes/{note_relpath}",
            "low_text_yield": low_yield,
            "extraction": extraction,
        }
        known_hashes[pdf_hash] = relpath
        converted += 1
        if low_yield:
            warnings.append(f"{relpath}: LOW TEXT YIELD, likely scanned - consider OCR")

        entry_id = entry_id_for(Path(note_relpath).with_suffix("").as_posix())
        # Saved per file: a killed run keeps everything finished so far.
        save_json(manifest_path, manifest)
        append_catalog_stubs(catalog_path, [(
            entry_id,
            meta_guess["title"] or Path(relpath).stem,
            f"notes/{note_relpath}",
            f"PDFs/{relpath}",
            meta_guess["authors"],
            meta_guess["year"],
        )])

    if args.dry_run:
        print(f"\nDry run. Would convert the files listed above; unchanged: {skipped}, "
              f"duplicates: {duplicates}, deferred: {len(deferred)}.")
        return 0

    print(f"\nDone. Converted: {converted}, skipped (unchanged): {skipped}, "
          f"duplicates: {duplicates}, deferred: {len(deferred)}")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
