"""Tests for the early-writing warning on requirements/.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import validate_repo as v  # noqa: E402


class TooEarly(unittest.TestCase):
    def test_nothing_wrong_means_no_reasons(self):
        self.assertEqual(v.requirements_too_early_reasons(False, 5, False), [])

    def test_a_placeholder_scope_is_one_reason_and_hides_the_catalog_count(self):
        reasons = v.requirements_too_early_reasons(True, 0, False)
        self.assertEqual(len(reasons), 1)
        self.assertIn("scope.md", reasons[0])

    def test_no_processed_documents(self):
        reasons = v.requirements_too_early_reasons(False, 0, False)
        self.assertEqual(len(reasons), 1)
        self.assertIn("no document", reasons[0])

    def test_unfinished_review_article(self):
        reasons = v.requirements_too_early_reasons(False, 3, True)
        self.assertEqual(len(reasons), 1)
        self.assertIn("review article", reasons[0])

    def test_reasons_add_up(self):
        self.assertEqual(len(v.requirements_too_early_reasons(False, 0, True)), 2)


class TbdCount(unittest.TestCase):
    def test_counts_tbd_and_tbr_as_whole_words(self):
        text = "Settling time: TBD. Margin: TBR by M2. Value 12, not TBDX, nor XTBD."
        self.assertEqual(len(v.TBD_RE.findall(text)), 2)


if __name__ == "__main__":
    unittest.main()
