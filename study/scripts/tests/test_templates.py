"""Tests for new_article.py and for every article template in articles/_templates/.

Every template is instantiated into a temporary articles folder and put through the checks the
real articles get, so a change to the shared preamble or to a checker cannot silently break a
template that nobody has instantiated lately.

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
import build_articles as ba  # noqa: E402
import build_bibliography as bib  # noqa: E402
import new_article as na  # noqa: E402
import style_check as sc  # noqa: E402
from ocr_support import find_tool  # noqa: E402

REAL_ARTICLES = bib.ARTICLES_DIR
KIND_NAMES = {"specification": "test-concept"}


def articles_copy(tmp):
    """A temporary articles folder holding the real templates and the shared preamble."""
    root = Path(tmp) / "articles"
    root.mkdir()
    shutil.copytree(REAL_ARTICLES / "_templates", root / "_templates")
    shutil.copytree(REAL_ARTICLES / "common", root / "common")
    return root


class Instantiating(unittest.TestCase):
    def test_the_name_must_be_a_clean_slug_and_a_specification_needs_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = articles_copy(tmp)
            for bad in ("Bad_Name", "two  words", "-lead", "trail-", "UPPER"):
                with self.assertRaises(ValueError):
                    na.instantiate("specification", bad, root)
            with self.assertRaises(ValueError):
                na.instantiate("specification", "", root)

    def test_an_unknown_template_and_a_second_creation_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = articles_copy(tmp)
            with self.assertRaises(ValueError):
                na.instantiate("nonsense", "x", root)
            na.instantiate("specification", "alpha", root)
            with self.assertRaises(ValueError):
                na.instantiate("specification", "alpha", root)

    def test_the_tokens_are_filled_in_and_the_article_starts_at_0_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = articles_copy(tmp)
            folder, _ = na.instantiate("specification", "concept-a", root)
            self.assertEqual(folder.name, "specification-concept-a")
            text = "".join(p.read_text(encoding="utf-8") for p in folder.rglob("*") if p.suffix in (".tex", ".md"))
            self.assertNotIn("{{NAME}}", text)
            self.assertNotIn("{{TITLE}}", text)
            self.assertIn("Specification: concept a", text)
            self.assertEqual([r["version"] for r in av.load(folder)["rows"]], ["0.1"])

    def test_a_specification_warns_when_the_rationale_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = articles_copy(tmp)
            rationale = root / "rationale"
            (rationale / "sections").mkdir(parents=True)
            (rationale / "main.tex").write_text("x\n", encoding="utf-8")
            av.add_row(rationale, "draft", "d", "Claude")
            _, warnings = na.instantiate("specification", "alpha", root)
            self.assertEqual(len(warnings), 1)
            av.add_row(rationale, "accept", "a", "User")
            _, warnings = na.instantiate("specification", "beta", root)
            self.assertEqual(warnings, [])


class EveryTemplate(unittest.TestCase):
    def instances(self, tmp):
        root = articles_copy(tmp)
        kinds = na.templates(root / "_templates")
        self.assertTrue(kinds, "no templates found")
        return root, [na.instantiate(k, KIND_NAMES.get(k, ""), root)[0] for k in kinds]

    def test_each_instance_is_a_recognised_article_with_matching_versions_and_clean_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, folders = self.instances(tmp)
            self.assertEqual({f.name for f in folders}, {d.name for d in bib.article_dirs(root)})
            phrases = sc.load_phrases()
            extras = bib.parse_bib_entries((root / "common" / "references_extra.bib").read_text(encoding="utf-8"))
            for folder in folders:
                with self.subTest(article=folder.name):
                    self.assertEqual(av.stale_files(folder), [])
                    _bibtex, _refs, unresolved = bib.build_for_article(folder, [], extras)
                    self.assertEqual(unresolved, [])
                    problems = [f for f in sc.check_article(folder, phrases) if f.severity == "problem"]
                    self.assertEqual(problems, [])

    def test_each_instance_builds_a_pdf_when_latex_is_installed(self):
        pdflatex = find_tool(["pdflatex"], ba.latex_dirs())
        if not pdflatex:
            self.skipTest("pdflatex is not installed")
        bibtex = find_tool(["bibtex"], ba.latex_dirs())
        with tempfile.TemporaryDirectory() as tmp:
            root, folders = self.instances(tmp)
            with mock.patch.object(ba, "ARTICLES_DIR", root):
                for folder in folders:
                    with self.subTest(article=folder.name):
                        ok, message = ba.build_pdf(folder, pdflatex, bibtex)
                        self.assertTrue(ok, message)
                        self.assertTrue((root / f"{folder.name}.pdf").exists())


if __name__ == "__main__":
    unittest.main()
