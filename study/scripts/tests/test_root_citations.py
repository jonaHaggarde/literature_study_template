"""Tests for the root-citation check in validate_repo.py.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import validate_repo as v  # noqa: E402


class FindNoteRefs(unittest.TestCase):
    def test_finds_relative_and_plain_paths_once_each(self):
        text = (
            "See [1] and [2].\n\n## References\n"
            "[1] A. Author, 2020, Title: ../study/notes/a_paper.md\n"
            "[2] B. Author, 2021, Other: study/notes/sub/b_paper.md\n"
            "Again [1]: ../study/notes/a_paper.md\n"
        )
        self.assertEqual(v.find_note_refs(text), ["a_paper.md", "sub/b_paper.md"])

    def test_ignores_prose_about_the_folder_and_placeholders(self):
        text = "Notes live in `study/notes/`. Template: study/notes/<file>.md and study/notes/*.md"
        self.assertEqual(v.find_note_refs(text), [])

    def test_does_not_match_inside_a_longer_word(self):
        self.assertEqual(v.find_note_refs("mystudy/notes/x.md"), [])


if __name__ == "__main__":
    unittest.main()
