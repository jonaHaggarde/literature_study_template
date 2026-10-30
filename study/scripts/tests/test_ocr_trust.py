"""Tests for the OCR trust rules: an OCR-only card is never verified, and the
validator's OCR checks.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import validate_repo as v  # noqa: E402
import verification  # noqa: E402
import method_cards  # noqa: E402


class StatusFor(unittest.TestCase):
    CARD = {"input": "a", "technique": "b"}

    def rec(self, values=None, verdict="pass"):
        return {"hash": method_cards.card_hash("M", values or self.CARD), "verdict": verdict}

    def test_a_normal_card_is_verified_after_a_pass(self):
        self.assertEqual(verification.status_for("M", self.CARD, self.rec()), "verified")

    def test_unverified_stale_and_failed(self):
        self.assertEqual(verification.status_for("M", self.CARD, None), "unverified")
        self.assertEqual(verification.status_for("M", self.CARD, self.rec({"input": "other"})), "stale")
        self.assertEqual(verification.status_for("M", self.CARD, self.rec(verdict="fail")), "failed")

    def test_a_card_resting_on_ocr_is_never_verified_even_with_a_pass(self):
        card = dict(self.CARD, read_from="ocr")
        self.assertEqual(verification.status_for("M", card, self.rec(card)), "ocr-only")

    def test_once_read_from_the_image_the_card_can_be_verified(self):
        card = dict(self.CARD, read_from="vision")
        self.assertEqual(verification.status_for("M", card, self.rec(card)), "verified")


class OcrCheck(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "notes").mkdir()
        self.saved = (v.REPO_ROOT, v.MANIFEST_PATH, list(v.results))
        v.REPO_ROOT, v.MANIFEST_PATH = self.root, self.root / "manifest.json"
        v.results.clear()

    def tearDown(self):
        v.REPO_ROOT, v.MANIFEST_PATH = self.saved[0], self.saved[1]
        v.results[:] = self.saved[2]
        self._tmp.cleanup()

    def run_check(self, manifest, notes=None, ledger=None):
        v.MANIFEST_PATH.write_text(json.dumps(manifest), encoding="utf-8")
        for name, text in (notes or {}).items():
            (self.root / "notes" / name).write_text(text, encoding="utf-8")
        if ledger is not None:
            (self.root / ".ocr").mkdir(exist_ok=True)
            (self.root / ".ocr" / "ledger.json").write_text(json.dumps(ledger), encoding="utf-8")
        v.check_ocr()
        return [(lvl, msg) for lvl, cat, msg in v.results if cat == "ocr"]

    def test_a_scan_that_was_never_ocrd_is_a_warning(self):
        out = self.run_check({"s.pdf": {"low_text_yield": True, "extraction": "layout", "notes_path": "notes/s.md"}})
        warns = [m for lvl, m in out if lvl == "WARN"]
        self.assertEqual(len(warns), 1)
        self.assertIn("not OCR'd", warns[0])
        self.assertIn("--reocr", warns[0])

    def test_an_ocrd_document_is_counted_with_its_unread_equation_pages(self):
        out = self.run_check({"s.pdf": {"extraction": "ocr", "ocr_suspect_pages": [2, 4, 5], "vision_pages": [4],
                                        "notes_path": "notes/s.md"}})
        info = [m for lvl, m in out if lvl == "INFO"][0]
        self.assertIn("1 OCR'd", info)
        self.assertIn("2 equation-heavy", info)

    def test_a_hand_edited_vision_marker_is_a_warning(self):
        note = "## Content\n\n<!-- page: 5 (vision) -->\n\ntext\n\n<!-- page: 6 (vision) -->\n\ntext\n"
        out = self.run_check({"s.pdf": {"extraction": "ocr", "vision_pages": [5], "notes_path": "notes/s.md"}},
                             notes={"s.md": note})
        warns = [m for lvl, m in out if lvl == "WARN"]
        self.assertEqual(len(warns), 1)
        self.assertIn("[6]", warns[0])
        self.assertIn("budget", warns[0])

    def test_recorded_vision_pages_raise_no_warning(self):
        note = "## Content\n\n<!-- page: 5 (vision) -->\n\ntext\n"
        out = self.run_check({"s.pdf": {"extraction": "ocr", "vision_pages": [5], "notes_path": "notes/s.md"}},
                             notes={"s.md": note})
        self.assertFalse([m for lvl, m in out if lvl == "WARN"])

    def test_todays_ledger_is_reported(self):
        out = self.run_check({}, ledger={date.today().isoformat(): 3})
        self.assertTrue(any("3 page(s) read from images today" in m for _l, m in out))


if __name__ == "__main__":
    unittest.main()
