"""Regression tests for the catalog tag-casing fix and the field parser.

Run from study/:  python -m unittest discover -s scripts/tests

Why this exists: the tag-casing pass once merged an empty `tags:` line into
the following `note:` line (the regex `\s?` after the colon matched the
newline, so the next line became the value). It only showed on unprocessed
stub entries, only when something else made --fix write the file, and it was
first blamed on convert.py. A fixture keeps it from coming back.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import validate_repo as v  # noqa: E402

STUB = (
    "<!-- entry:stub -->\n"
    "title: A Stub\n"
    "authors: \n"
    "year: \n"
    "type:\n"
    "approach:\n"
    "contribution:\n"
    "compares:\n"
    "tags:\n"
    "note: notes/stub.md\n"
    "source: PDFs/stub.pdf\n"
    "summary: TODO - fill in\n"
    "<!-- /entry -->\n"
)
DONE = STUB.replace("stub", "done").replace("tags:\n", "tags: Kalman-Filtering, other\n").replace(
    "summary: TODO - fill in", "summary: a real summary"
)
CANON = {"kalman-filtering": "kalman-filtering"}


class TagCasingFix(unittest.TestCase):
    def check(self, text):
        fixed, changed = v.fix_tag_casing(text, CANON)
        return fixed, changed

    def test_empty_tags_line_is_left_alone(self):
        fixed, changed = self.check(STUB)
        self.assertEqual(fixed, STUB)
        self.assertFalse(changed)

    def test_stub_survives_a_real_casing_fix_next_to_it(self):
        fixed, changed = self.check(STUB + "\n" + DONE)
        self.assertTrue(changed)
        self.assertIn("tags:\nnote: notes/stub.md\n", fixed)
        self.assertIn("tags: kalman-filtering, other\n", fixed)

    def test_crlf_text_keeps_empty_tags_line(self):
        crlf = (STUB + "\n" + DONE).replace("\n", "\r\n")
        fixed, _ = self.check(crlf)
        self.assertIn("tags:\r\nnote: notes/stub.md", fixed)

    def test_parser_reads_empty_fields_as_empty(self):
        entries = dict(v.parse_catalog(STUB))
        self.assertEqual(entries["stub"]["tags"], "")
        self.assertEqual(entries["stub"]["note"], "notes/stub.md")


if __name__ == "__main__":
    unittest.main()
