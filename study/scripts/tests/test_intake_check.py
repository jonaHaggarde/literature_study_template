"""Tests for intake_check.py: IDs that tie the definition article to what the user said.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import intake_check as ic  # noqa: E402

DIGEST = """# Intake digest

| ID | Kind | Statement | Source |
|---|---|---|---|
| I-1 | goal | Cut lap time | brief.md, p. 1 |
| I-2 | unknown | Budget | interview 2026-11-02 |
"""


class Parsing(unittest.TestCase):
    def test_rows_are_read_and_the_header_is_skipped(self):
        self.assertEqual(ic.parse_intake(DIGEST),
                         [("I-1", "goal", "Cut lap time", "brief.md, p. 1"),
                          ("I-2", "unknown", "Budget", "interview 2026-11-02")])

    def test_a_clean_digest_has_no_problems(self):
        self.assertEqual(ic.problems(ic.parse_intake(DIGEST)), [])

    def test_duplicates_missing_source_and_unknown_kind_are_found(self):
        rows = ic.parse_intake("| I-1 | goal | a | s |\n| I-1 | hunch | b | |\n")
        text = " ".join(ic.problems(rows))
        self.assertIn("more than once", text)
        self.assertIn("kind 'hunch'", text)
        self.assertIn("no source", text)

    def test_next_id_never_reuses_a_number(self):
        rows = ic.parse_intake(DIGEST)
        self.assertEqual(ic.next_id(rows), "I-3")
        self.assertEqual(ic.next_id(rows, dropped=["I-9"]), "I-10")
        self.assertEqual(ic.next_id([]), "I-1")


class Citations(unittest.TestCase):
    def make(self, tmp, tex):
        root = Path(tmp)
        (root / "intake").mkdir()
        (root / "intake" / "intake.md").write_text(DIGEST, encoding="utf-8")
        art = root / "articles" / "definition"
        (art / "sections").mkdir(parents=True)
        (art / "main.tex").write_text("\\begin{document}\\end{document}\n", encoding="utf-8")
        (art / "sections" / "problem.tex").write_text(tex, encoding="utf-8")
        return root

    def test_a_cited_id_that_exists_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make(tmp, "Goal.\\intake{I-1} Budget.\\intake{I-1,I-2}\n")
            found, count = ic.check_all(root / "intake" / "intake.md", root / "articles")
            self.assertEqual((found, count), ([], 2))

    def test_a_cited_id_that_does_not_exist_fails_and_a_comment_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make(tmp, "Claim.\\intake{I-7} % \\intake{I-8}\n")
            found, _ = ic.check_all(root / "intake" / "intake.md", root / "articles")
            self.assertEqual(len(found), 1)
            self.assertIn("I-7", found[0][1])


class Handover(unittest.TestCase):
    def make(self, tmp):
        root = Path(tmp)
        for folder in ("own", "received"):
            (root / folder).mkdir()
        (root / "own" / "notes.md").write_text("mine\n", encoding="utf-8")
        (root / "own" / "README.md").write_text("readme\n", encoding="utf-8")
        (root / "received" / "brief.pdf").write_bytes(b"%PDF-1.4 fake")
        (root / "received" / "photo.PNG").write_bytes(b"png")
        (root / "received" / "plan.docx").write_bytes(b"docx")
        return root

    def test_pdfs_and_unreadable_files_are_found_in_both_folders_and_readmes_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make(tmp)
            self.assertEqual([p.name for p in ic.pdfs(root)], ["brief.pdf"])
            self.assertEqual(sorted(p.name for p in ic.unreadable(root)), ["photo.PNG", "plan.docx"])
            self.assertEqual("README.md" in [p.name for p in ic.source_files(root)], False)

    def test_a_pdf_is_pending_until_converted_and_again_when_it_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.make(tmp)
            pdf = root / "received" / "brief.pdf"
            self.assertEqual(ic.pending(root), [pdf])
            pdf.with_suffix(".md").write_text("converted\n", encoding="utf-8")
            (root / ".converted.json").write_text(
                '{"received/brief.pdf": {"hash": "%s"}}' % ic.sha256_file(pdf), encoding="utf-8")
            self.assertEqual(ic.pending(root), [])
            pdf.write_bytes(b"%PDF-1.4 changed")
            self.assertEqual(ic.pending(root), [pdf])

    def test_the_converted_file_says_what_it_is_and_marks_ocr_pages(self):
        pages = [{"text": "Weight limit 200 kg " * 5}, {"text": "scanned text " * 5, "ocr": True}]
        text = ic.build_markdown("brief.pdf", "ab" * 32, pages, "layout", today=date(2026, 11, 1))
        self.assertTrue(text.startswith("<!-- Converted from brief.pdf (sha256 abababababab, 2026-11-01)"))
        self.assertIn("not authored", text)
        self.assertIn("<!-- page: 1 -->", text)
        self.assertIn("<!-- page: 2 (ocr) -->", text)

    def test_a_scan_with_no_text_and_no_ocr_is_flagged_as_unread(self):
        text = ic.build_markdown("scan.pdf", "cd" * 32, [{"text": ""}, {"text": ""}], "layout")
        self.assertIn("probably a scan and OCR did not run", text)


if __name__ == "__main__":
    unittest.main()
