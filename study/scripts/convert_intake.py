#!/usr/bin/env python3
"""
Converts the PDFs the user put in intake/own/ and intake/received/ into markdown files
next to them (brief.pdf -> brief.md), so a long document is read from text and not from the
PDF again. The converted file starts with a line saying it is a machine conversion of that
PDF; for a received PDF it is still the sender's text, which is why it stays beside the
original and does not move up to the self-written level.

It reuses the extraction and OCR of convert.py (layout extraction in a child process with a
time limit, OCR for scans, `(ocr)` page markers and the notice about equations and tables),
without the catalog stub and the notes. A PDF is converted once: a hash manifest in
intake/.converted.json skips it until its content changes.

Images and Word, PowerPoint and Excel files are not converted. They are listed, so they are
not forgotten: give a PDF or text instead, or decide whether an image is worth the budgeted
vision step (study/ai_instructions/vision-budget.md).

Usage (from study/):
    python scripts/convert_intake.py                # convert everything new or changed
    python scripts/convert_intake.py --dry-run      # list what would happen
    python scripts/convert_intake.py --ocr off      # never OCR (default: auto)
    python scripts/convert_intake.py --timeout 120  # per-file extraction limit, seconds
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import convert  # noqa: E402  (needs pymupdf4llm, like convert.py itself)
import intake_check  # noqa: E402

COPYRIGHT_NOTICE = (
    "Note: the converted .md files contain the full text of your documents. Check this "
    "repository's visibility before pushing it."
)


def convert_one(pdf, mode, lang, timeout, warnings):
    """(markdown, extraction, ocr_info) for one PDF."""
    rel = pdf.relative_to(intake_check.INTAKE_DIR).as_posix()
    pages, extraction = convert.extract_pages(pdf, timeout)
    pages, ocr_extraction, info = convert.apply_ocr(pdf, pages, mode, lang, timeout, warnings, rel)
    if ocr_extraction:
        extraction = ocr_extraction
    markdown = intake_check.build_markdown(
        pdf.name, intake_check.sha256_file(pdf), pages, extraction, (info or {}).get("suspect"))
    return markdown, extraction, info


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--ocr", choices=["auto", "off", "require"], default="auto")
    p.add_argument("--lang", default="eng")
    p.add_argument("--timeout", type=float, default=300.0)
    args = p.parse_args(argv)

    todo = intake_check.pending()
    skipped = len(intake_check.pdfs()) - len(todo)
    for path in intake_check.unreadable():
        print(f"not converted (give a PDF or text): {path.relative_to(intake_check.INTAKE_DIR).as_posix()}")
    if not todo:
        print(f"Nothing to convert ({skipped} PDF(s) already converted).")
        return 0
    if args.dry_run:
        for pdf in todo:
            print(f"would convert: {pdf.relative_to(intake_check.INTAKE_DIR).as_posix()}")
        return 0

    manifest = intake_check.load_manifest()
    warnings, failed = [], 0
    for pdf in todo:
        rel = pdf.relative_to(intake_check.INTAKE_DIR).as_posix()
        print(f"converting {rel}")
        try:
            markdown, extraction, info = convert_one(pdf, args.ocr, args.lang, args.timeout, warnings)
        except RuntimeError as err:
            print(f"  FAILED: {err}", file=sys.stderr)
            failed += 1
            continue
        pdf.with_suffix(".md").write_text(markdown, encoding="utf-8")
        manifest[rel] = {"hash": intake_check.sha256_file(pdf), "extraction": extraction,
                         "converted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         "ocr_pages": (info or {}).get("ocr_pages", [])}
        (intake_check.INTAKE_DIR / intake_check.MANIFEST_PATH.name).write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8")  # saved after each file
        note = f"{rel[:-4]}.md ({extraction})"
        if info:
            note += f", {len(info['ocr_pages'])} page(s) OCR'd"
        print(f"  wrote {note}")
    for w in warnings:
        print(f"WARNING {w}", file=sys.stderr)
    print(COPYRIGHT_NOTICE)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
