"""Tests for merge_worker_report.py.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import merge_worker_report as m  # noqa: E402

STUB = (
    "<!-- entry:p1 -->\n"
    "title: Stub Title\n"
    "authors: \n"
    "year: \n"
    "type:\n"
    "approach:\n"
    "contribution:\n"
    "compares:\n"
    "tags:\n"
    "note: notes/p1.md\n"
    "source: PDFs/p1.pdf\n"
    "summary: TODO - fill in\n"
    "<!-- /entry -->\n"
)
FILLED = STUB.replace("p1", "p2").replace("summary: TODO - fill in", "summary: already written\n  and wrapped here")
NOTE = (
    "---\ntitle: \"p1\"\ntags: []\n---\n\n## Key Findings\n\nx\n\n## Method Cards\n\n"
    "### Alpha filter\n- input: a\n- technique: kf\n\n## Content\n"
)
FIELDS = {"authors": "A. One", "year": "2020", "type": "paper", "approach": "kf",
          "contribution": "novel-contribution", "compares": "", "summary": "Result, limit."}


class MergeEntry(unittest.TestCase):
    def test_fills_document_fields_and_keeps_note_and_source(self):
        out = m.merge_entry(STUB, "p1", FIELDS)
        self.assertIn("authors: A. One\n", out)
        self.assertIn("summary: Result, limit.\n", out)
        self.assertIn("compares:\n", out)  # empty stays empty, not "n/a"
        self.assertIn("note: notes/p1.md\n", out)
        self.assertIn("source: PDFs/p1.pdf\n", out)
        self.assertIn("tags:\nnote:", out)  # tags untouched, no line merging

    def test_refuses_to_overwrite_a_filled_entry(self):
        with self.assertRaises(ValueError):
            m.merge_entry(FILLED, "p2", FIELDS)

    def test_force_replaces_wrapped_summary_completely(self):
        out = m.merge_entry(FILLED, "p2", FIELDS, force=True)
        self.assertIn("summary: Result, limit.\n", out)
        self.assertNotIn("wrapped here", out)

    def test_refuses_note_and_source_as_fields(self):
        with self.assertRaises(ValueError):
            m.merge_entry(STUB, "p1", {"note": "notes/evil.md"})

    def test_unknown_entry(self):
        with self.assertRaises(ValueError):
            m.merge_entry(STUB, "nope", FIELDS)

    def test_crlf_catalog(self):
        out = m.merge_entry(STUB.replace("\n", "\r\n"), "p1", FIELDS)
        self.assertIn("note: notes/p1.md", out)
        self.assertIn("source: PDFs/p1.pdf", out)


class NoteEdits(unittest.TestCase):
    def test_tags_in_frontmatter(self):
        self.assertIn("tags: [a, b]", m.set_note_tags(NOTE, ["a", "b"]))

    def test_family_inserted_under_the_card(self):
        out = m.set_card_family(NOTE, "Alpha filter", "family-a")
        self.assertIn("### Alpha filter\n- family: family-a\n- input: a", out)

    def test_family_replaced_not_duplicated(self):
        once = m.set_card_family(NOTE, "Alpha filter", "x")
        twice = m.set_card_family(once, "Alpha filter", "y")
        self.assertEqual(twice.count("- family:"), 1)
        self.assertIn("- family: y", twice)

    def test_unknown_card(self):
        with self.assertRaises(ValueError):
            m.set_card_family(NOTE, "No such method", "x")


class TagReport(unittest.TestCase):
    def test_near_duplicates_across_workers(self):
        reps = [
            {"documents": [{"entry_id": "a", "proposed": {"tags": ["fault-detection"]}}]},
            {"documents": [{"entry_id": "b", "proposed": {"tags": ["fault-detections", "other"]}}]},
        ]
        text = "\n".join(m.tag_report(reps))
        self.assertIn("near-duplicate", text)
        self.assertIn("not in topics/vocabulary.md", text)


class ReportValidation(unittest.TestCase):
    def test_wrong_shape_is_an_error_not_a_silent_no_op(self):
        flat = {"id": "p1", "authors": "x", "summary": "y", "method_cards": []}
        problems = m.validate_report(flat, "r.json")
        self.assertEqual(len(problems), 1)
        self.assertIn("'documents'", problems[0])
        self.assertIn("method_cards", problems[0])  # shows what it found instead

    def test_note_source_and_tags_not_allowed_in_catalog(self):
        rep = {"documents": [{"entry_id": "p1", "catalog": {"summary": "s", "note": "n", "tags": "t"}}]}
        text = " ".join(m.validate_report(rep, "r.json"))
        self.assertIn("'note'", text)
        self.assertIn("tags go in", text)

    def test_valid_report_has_no_problems(self):
        rep = {"documents": [{"entry_id": "p1", "catalog": {"summary": "s"}, "approved": {"tags": ["a"]}}]}
        self.assertEqual(m.validate_report(rep, "r.json"), [])

    def test_main_rejects_wrong_shape_and_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "catalog.md").write_text(STUB, encoding="utf-8")
            rp = root / "r.json"
            rp.write_text(json.dumps({"id": "p1", "summary": "y"}), encoding="utf-8")
            old = (m.REPO_ROOT, m.CATALOG_PATH, m.VOCAB_PATH)
            m.REPO_ROOT, m.CATALOG_PATH, m.VOCAB_PATH = root, root / "catalog.md", root / "v.md"
            try:
                rc = m.main([str(rp)])
            finally:
                m.REPO_ROOT, m.CATALOG_PATH, m.VOCAB_PATH = old
            self.assertEqual(rc, 2)
            self.assertEqual((root / "catalog.md").read_text(encoding="utf-8"), STUB)


class EndToEnd(unittest.TestCase):
    def test_main_merges_catalog_note_tags_and_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes").mkdir()
            (root / "catalog.md").write_text(STUB, encoding="utf-8")
            (root / "notes" / "p1.md").write_text(NOTE, encoding="utf-8")
            report = {"documents": [{
                "entry_id": "p1", "catalog": FIELDS, "unknown": ["compares"],
                "approved": {"tags": ["t1", "t2"], "families": {"Alpha filter": "family-a"}},
            }]}
            rp = root / "r.json"
            rp.write_text(json.dumps(report), encoding="utf-8")
            old = (m.REPO_ROOT, m.CATALOG_PATH, m.VOCAB_PATH)
            m.REPO_ROOT, m.CATALOG_PATH, m.VOCAB_PATH = root, root / "catalog.md", root / "v.md"
            try:
                rc = m.main([str(rp)])
            finally:
                m.REPO_ROOT, m.CATALOG_PATH, m.VOCAB_PATH = old
            self.assertEqual(rc, 0)
            cat = (root / "catalog.md").read_text(encoding="utf-8")
            note = (root / "notes" / "p1.md").read_text(encoding="utf-8")
            self.assertIn("tags: t1, t2\n", cat)
            self.assertIn("note: notes/p1.md\n", cat)
            self.assertIn("tags: [t1, t2]", note)
            self.assertIn("- family: family-a", note)


if __name__ == "__main__":
    unittest.main()
