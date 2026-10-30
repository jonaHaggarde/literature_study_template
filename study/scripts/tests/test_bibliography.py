"""Tests for build_bibliography.py: per-article bibliographies.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_bibliography as b  # noqa: E402

CATALOG = [
    ("p1", {"authors": "Antonio Leanza, Giulio Reina and Jose Blanco", "title": "A Factor-Graph & Approach",
            "year": "2021"}),
    ("p2", {"authors": "Mia Muller", "title": "Beta Method", "year": "2018"}),
]
EXTRAS = {"rules2026": "@misc{rules2026,\n  title = {Rules},\n  year = {2026},\n}"}


def make_article(root, name, body):
    d = Path(root) / name
    (d / "sections").mkdir(parents=True)
    (d / "main.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n\\input{sections/intro}\n\\input{sections/references}\n\\end{document}\n",
        encoding="utf-8")
    (d / "sections" / "intro.tex").write_text(body, encoding="utf-8")
    return d


class Citations(unittest.TestCase):
    def test_keys_come_out_in_order_of_first_citation_and_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp, "a", "See \\cite{muller2018} and \\cite{leanza2021,muller2018}. % \\cite{ignored}\n")
            self.assertEqual(b.cited_keys_in_order(d), ["muller2018", "leanza2021"])

    def test_the_generated_references_file_is_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp, "a", "text\n")
            (d / "sections" / "references.tex").write_text("\\cite{shouldnotcount}\n", encoding="utf-8")
            self.assertEqual(b.cited_keys_in_order(d), [])


class Building(unittest.TestCase):
    def test_an_article_holds_only_what_it_cites(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp, "a", "\\cite{leanza2021}\n")
            bib, refs, unresolved = b.build_for_article(d, CATALOG, EXTRAS)
            self.assertEqual(b.bib_keys(bib), {"leanza2021"})
            self.assertEqual(unresolved, [])
            self.assertIn("\\bibliography{references}", refs)
            self.assertIn("\\bibliographystyle{unsrt}", refs)

    def test_two_articles_get_different_bibliographies(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = make_article(tmp, "a", "\\cite{leanza2021}\n")
            c = make_article(tmp, "c", "\\cite{muller2018,rules2026}\n")
            self.assertEqual(b.bib_keys(b.build_for_article(a, CATALOG, EXTRAS)[0]), {"leanza2021"})
            self.assertEqual(b.bib_keys(b.build_for_article(c, CATALOG, EXTRAS)[0]), {"muller2018", "rules2026"})

    def test_an_article_with_no_sources_gets_no_bib_and_no_bibliography_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp, "a", "No citations here.\n")
            bib, refs, unresolved = b.build_for_article(d, CATALOG, EXTRAS)
            self.assertIsNone(bib)
            self.assertNotIn("\\bibliography{", refs)
            self.assertIn("cites no sources", refs)

    def test_a_key_found_nowhere_is_reported_and_left_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp, "a", "\\cite{leanza2021,nowhere}\n")
            bib, _refs, unresolved = b.build_for_article(d, CATALOG, EXTRAS)
            self.assertEqual(unresolved, ["nowhere"])
            self.assertEqual(b.bib_keys(bib), {"leanza2021"})


class Entries(unittest.TestCase):
    def test_a_catalog_entry_becomes_a_misc_with_escaped_text_and_joined_authors(self):
        e = b.catalog_bib_entry("p1", CATALOG[0][1], "leanza2021")
        self.assertIn("@misc{leanza2021,", e)
        self.assertIn("author = {Antonio Leanza and Giulio Reina and Jose Blanco}", e)
        self.assertIn("{{A Factor-Graph \\& Approach}}", e)
        self.assertIn("year = {2021}", e)

    def test_parser_takes_nested_braces_whole(self):
        text = "@article{k1,\n  title = {{A {B} C}},\n  year = {2020}\n}\n@misc{k2, title={x}}\n"
        entries = b.parse_bib_entries(text)
        self.assertEqual(set(entries), {"k1", "k2"})
        self.assertIn("{A {B} C}", entries["k1"])
        self.assertTrue(entries["k1"].endswith("}"))

    def test_the_parser_ignores_comment_blocks(self):
        self.assertEqual(b.bib_keys("@comment{not an entry,}\n@misc{k, title={x}}"), {"k"})


class Discovery(unittest.TestCase):
    def test_only_folders_with_a_main_tex_count_and_common_and_gates_do_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make_article(root, "review", "x")
            (root / "common").mkdir()
            (root / "common" / "main.tex").write_text("x", encoding="utf-8")
            (root / "gates").mkdir()
            (root / "empty").mkdir()
            (root / ".build").mkdir()
            self.assertEqual([p.name for p in b.article_dirs(root)], ["review"])


if __name__ == "__main__":
    unittest.main()
