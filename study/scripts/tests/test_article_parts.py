"""Tests for build_article_parts.py and tree_latex.py: the generated parts of the map, requirements
and rationale articles.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import article_version as av  # noqa: E402
import build_article_parts as bap  # noqa: E402
import build_articles as ba  # noqa: E402
import build_bibliography as bib  # noqa: E402
import build_decision_trees as bdt  # noqa: E402
import new_article as na  # noqa: E402
import tree_latex  # noqa: E402
from ocr_support import find_tool  # noqa: E402

PRIMARY = r"""P-1 & Latency & 20 & ms & 1 & Interview & A & agreed \\
P-2 & Range & TBD & m & & Datasheet & A & open \\
P-3 & Budget & 5 & k & & assumed from last year & A & open \\
P-4 & Weight & 2 & kg & & & A & open \\
"""
DERIVED = r"""D-1 & Update rate & P-1 & from latency & TBD & open \\
D-2 & Buffer size & D-1, P-2 & from rate and range & TBD & open \\
D-3 & Orphan & & & TBD & open \\
D-4 & Lost & P-9 & & TBD & open \\
D-5 & Loop a & D-6 & & TBD & open \\
D-6 & Loop b & D-5 & & TBD & open \\
"""

TREE = """| Q | question | answer | status | then | method | source | motivation |
|---|---|---|---|---|---|---|---|
| Q1 | Which family fits the constraint? | Family A | chosen | Q2 | | | |
| Q1 | | Family B | explored | | Method B | | |
| Q1 | | Family C | identified | | Method C | | |
| Q2 | Which variant? | Variant 1 | chosen | END | Method A1 | | |
| Q2 | | Variant 2 | candidate | | Method A2 | | |
"""


class Traceability(unittest.TestCase):
    def test_a_placeholder_row_is_not_a_requirement(self):
        rows = bap.table_rows("P-1 & \\todo{parameter} & & \\\\\nnot a row\nP-2 & Real & 1 & \\\\\n")
        self.assertEqual([r[0] for r in rows], ["P-2"])

    def test_derived_requirements_are_traced_up_and_gaps_are_flagged(self):
        derived, primary, problems = bap.traceability(PRIMARY, DERIVED)
        by_id = {r[0]: r for r in derived}
        self.assertEqual(by_id["D-2"][3], "P-1, P-2")
        self.assertEqual(by_id["D-1"][4], [])
        self.assertIn("no parent", by_id["D-3"][4])
        self.assertIn("unknown parent P-9", by_id["D-4"][4])
        self.assertIn("cycle", by_id["D-5"][4])
        self.assertTrue(any("D-3: no parent" in p for p in problems))

    def test_primary_requirements_with_no_source_an_assumed_source_or_a_tbd_value_are_flagged(self):
        _, primary, problems = bap.traceability(PRIMARY, DERIVED)
        notes = {r[0]: r[4] for r in primary}
        self.assertEqual(notes["P-1"], [])
        self.assertEqual(notes["P-2"], ["value TBD"])
        self.assertIn("source is an assumption", notes["P-3"])
        self.assertIn("no source", notes["P-4"])
        used = {r[0]: r[3] for r in primary}
        self.assertEqual(used["P-1"], "D-1")
        self.assertFalse(any("value TBD" in p for p in problems))

    def test_the_rendered_table_names_the_rows_and_an_empty_one_says_so(self):
        text = bap.render_traceability(PRIMARY, DERIVED)
        self.assertIn("P-1 & Latency", text)
        self.assertIn("no path", bap.render_traceability(PRIMARY, "D-1 & X & P-9 & & TBD & open \\\\\n") + "no path")
        self.assertIn("No requirements recorded yet", bap.render_traceability("", ""))


class Coverage(unittest.TestCase):
    def test_counts_are_distinct_sources_and_cards_per_family(self):
        cards = [("a", "fam-1"), ("a", "fam-1"), ("a", "fam-2"), ("b", "fam-1"), ("c", "")]
        self.assertEqual(bap.coverage_counts(cards), {"fam-1": (2, 3), "fam-2": (1, 1), "": (1, 1)})

    def test_the_table_lists_the_families_the_total_and_the_unsorted_ones(self):
        text = bap.render_coverage([("a", "fam-1"), ("b", "fam-1"), ("c", "")], canonical=["fam-1"])
        self.assertIn("fam-1 & 2 & 2 & 67", text)
        self.assertIn("no family", text)
        self.assertIn("Distinct sources", text)
        self.assertIn("No method cards yet", bap.render_coverage([]))


class Tree(unittest.TestCase):
    def test_candidate_is_a_valid_leaf_status_and_needs_a_method(self):
        rows, problems = bdt.parse_table(TREE)
        self.assertEqual(problems, [])
        self.assertEqual(bdt.validate(rows), [])
        bad = TREE.replace("Method A2", "")
        rows, _ = bdt.parse_table(bad)
        self.assertTrue(any("candidate answer must name" in p for p in bdt.validate(rows)))
        self.assertIn("candidate", bdt.render_mermaid(bdt.parse_table(TREE)[0]))

    def test_the_latex_tree_has_a_node_per_question_and_leaf_and_the_recommendation(self):
        rows, _ = bdt.parse_table(TREE)
        text = tree_latex.render_latex(rows)
        for node in ("(Q1)", "(Q2)", "(Q1L1)", "(Q1L2)", "(Q2L1)", "(R)"):
            self.assertIn(node, text)
        self.assertIn("Method A1", text)
        self.assertIn("candidate, to be settled", text)


def workspace(tmp):
    root = Path(tmp) / "articles"
    root.mkdir()
    for name in ("_templates", "common"):
        shutil.copytree(bib.ARTICLES_DIR / name, root / name)
    return root


class InAnArticle(unittest.TestCase):
    def test_the_rationale_tree_is_generated_from_the_table_and_the_table_is_version_tracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(tmp)
            folder, _ = na.instantiate("rationale", "", root)
            self.assertIn("decision_tree.md", av.tracked_files(folder))
            (folder / "decision_tree.md").write_text(
                "<!-- decision-tree -->\n" + TREE + "<!-- /decision-tree -->\n", encoding="utf-8")
            self.assertEqual(av.stale_files(folder), ["decision_tree.md"])
            changed, problems = bap.build("rationale", articles_dir=root)
            self.assertEqual((changed, problems), (["decision_tree.tex"], []))
            self.assertEqual(bap.build("rationale", articles_dir=root), ([], []))
            self.assertEqual(av.stale_files(folder), ["decision_tree.md"])   # the generated file is not tracked

    def test_an_invalid_table_is_reported_and_leaves_the_old_picture_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(tmp)
            folder, _ = na.instantiate("rationale", "", root)
            (folder / "decision_tree.md").write_text(
                "<!-- decision-tree -->\n" + TREE.replace("| chosen | END ", "| chosen | ") + "<!-- /decision-tree -->\n",
                encoding="utf-8")
            changed, problems = bap.build("rationale", articles_dir=root)
            self.assertEqual(changed, [])
            self.assertTrue(problems)

    def test_requirements_and_map_are_generated_into_their_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(tmp)
            req, _ = na.instantiate("requirements", "", root)
            (req / "sections" / "primary.tex").write_text(PRIMARY, encoding="utf-8")
            changed, _ = bap.build("requirements", articles_dir=root)
            self.assertEqual(changed, ["traceability_table.tex"])
            self.assertIn("P-1 & Latency", (req / "sections" / "traceability_table.tex").read_text(encoding="utf-8"))
            na.instantiate("map", "", root)
            changed, _ = bap.build("map", articles_dir=root, cards=[("a", "fam-1")])
            self.assertEqual(changed, ["coverage_table.tex"])

    def test_the_generated_parts_compile_when_latex_is_installed(self):
        pdflatex = find_tool(["pdflatex"], ba.latex_dirs())
        if not pdflatex:
            self.skipTest("pdflatex is not installed")
        bibtex = find_tool(["bibtex"], ba.latex_dirs())
        with tempfile.TemporaryDirectory() as tmp:
            root = workspace(tmp)
            rat, _ = na.instantiate("rationale", "", root)
            req, _ = na.instantiate("requirements", "", root)
            mp, _ = na.instantiate("map", "", root)
            (rat / "decision_tree.md").write_text(
                "<!-- decision-tree -->\n" + TREE + "<!-- /decision-tree -->\n", encoding="utf-8")
            (req / "sections" / "primary.tex").write_text(
                "\\section{Primary}\n\\begin{tabularx}{\\linewidth}{@{}l L r l l L l l@{}}\n" + PRIMARY
                + "\\end{tabularx}\n", encoding="utf-8")
            (req / "sections" / "derived.tex").write_text(
                "\\section{Derived}\n\\begin{tabularx}{\\linewidth}{@{}l L l L L l@{}}\n" + DERIVED
                + "\\end{tabularx}\n", encoding="utf-8")
            bap.build("rationale", articles_dir=root)
            bap.build("requirements", articles_dir=root)
            bap.build("map", articles_dir=root, cards=[("a", "fam-1"), ("b", "")])
            with mock.patch.object(ba, "ARTICLES_DIR", root):
                for folder in (rat, req, mp):
                    with self.subTest(article=folder.name):
                        ok, message = ba.build_pdf(folder, pdflatex, bibtex)
                        self.assertTrue(ok, message)


if __name__ == "__main__":
    unittest.main()
