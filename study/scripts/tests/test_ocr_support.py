"""Tests for ocr_support.py (the parts that need no OCR tools).

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ocr_support as o  # noqa: E402

PROSE = "This is an ordinary paragraph of running text with no formulas at all. " * 20
MATH = ("x = y + z\n" * 12) + "Phi(1) @ exp F = sum F^i / i\n"


class Suspect(unittest.TestCase):
    def test_prose_pages_are_not_suspect_and_equation_pages_are(self):
        self.assertEqual(o.suspect_pages([PROSE, MATH, PROSE, MATH]), [2, 4])

    def test_skipped_pages_are_ignored(self):
        self.assertEqual(o.suspect_pages([None, MATH]), [2])

    def test_a_high_symbol_ratio_flags_a_page_even_without_equals_signs(self):
        symbolic = "a @ b ~ c ^ d _ e { f } | " * 30
        self.assertEqual(o.suspect_pages([symbolic]), [1])


class Merge(unittest.TestCase):
    def test_ocr_replaces_only_empty_pages(self):
        merged, used = o.merge_pages(["", "real text of a normal page " * 5, "  "], ["ocr one", "ocr two", "ocr three"])
        self.assertEqual(used, [1, 3])
        self.assertEqual(merged[0], "ocr one")
        self.assertTrue(merged[1].startswith("real text"))
        self.assertEqual(merged[2], "ocr three")

    def test_a_skipped_ocr_page_keeps_the_original(self):
        merged, used = o.merge_pages(["", "x"], [None, None])
        self.assertEqual((merged, used), (["", "x"], []))

    def test_fewer_ocr_pages_than_original_is_safe(self):
        merged, used = o.merge_pages(["", ""], ["only one"])
        self.assertEqual(used, [1])


class Tools(unittest.TestCase):
    def test_find_tool_looks_in_extra_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "tesseract.exe"
            fake.write_text("", encoding="utf-8")
            self.assertEqual(Path(o.find_tool(["definitely-not-on-path-tool", "tesseract"], [tmp])).name, "tesseract.exe")

    def test_find_tool_returns_none_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(o.find_tool(["definitely-not-on-path-tool"], [tmp]))

    def test_ready_needs_both_the_package_and_tesseract(self):
        self.assertFalse(o.ready({"ocrmypdf": True, "tesseract": None}))
        self.assertFalse(o.ready({"ocrmypdf": False, "tesseract": "/x"}))
        self.assertTrue(o.ready({"ocrmypdf": True, "tesseract": "/x"}))

    def test_hints_name_only_what_is_missing_and_install_nothing(self):
        st = {"ocrmypdf": True, "tesseract": None, "ghostscript": "/gs", "languages": []}
        hints = o.install_hints(st, system="Windows")
        self.assertEqual(len(hints), 1)
        self.assertIn("winget install", hints[0])
        self.assertEqual(o.install_hints({"ocrmypdf": True, "tesseract": "/t", "ghostscript": "/g", "languages": []}, "Linux"), [])

    def test_run_ocr_refuses_cleanly_when_tools_are_missing(self):
        pages, err = o.run_ocr("x.pdf", st={"ocrmypdf": False, "tesseract": None, "ghostscript": None, "languages": []})
        self.assertIsNone(pages)
        self.assertIn("not available", err)

    def test_run_ocr_refuses_a_language_that_is_not_installed(self):
        pages, err = o.run_ocr("x.pdf", lang="deu", st={"ocrmypdf": True, "tesseract": "/t", "ghostscript": None,
                                                        "languages": ["eng", "osd"]})
        self.assertIsNone(pages)
        self.assertIn("deu", err)


class Notice(unittest.TestCase):
    def test_notice_lists_the_suspect_pages(self):
        self.assertIn("5, 6, 7", o.notice([5, 6, 7]))
        self.assertIn("none detected", o.notice([]))


if __name__ == "__main__":
    unittest.main()
