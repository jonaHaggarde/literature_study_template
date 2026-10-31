"""Tests for intake_check.py: IDs that tie the definition article to what the user said.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
