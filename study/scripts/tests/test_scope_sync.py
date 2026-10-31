"""Tests for scope_sync.py: scope.md follows the accepted definition article.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import article_version as av  # noqa: E402
import scope_sync as ss  # noqa: E402


def make(tmp, scope_text="<!-- placeholder -->\nTemplate\n"):
    root = Path(tmp)
    d = root / "definition"
    (d / "sections").mkdir(parents=True)
    (d / "main.tex").write_text("main\n", encoding="utf-8")
    for name in ss.SCOPE_SECTIONS + ("stakeholders",):
        (d / "sections" / f"{name}.tex").write_text(f"{name} text\n", encoding="utf-8")
    scope = root / "scope.md"
    scope.write_text(scope_text, encoding="utf-8")
    av.add_row(d, "draft", "First draft", "Claude")
    return d, scope


def real_scope():
    return "# Study scope\n\nIn scope: things.\n"


class States(unittest.TestCase):
    def test_no_definition_article_means_the_original_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ss.state(Path(tmp) / "scope.md", Path(tmp) / "nope")[0], "no-pipeline")

    def test_placeholder_waits_until_the_definition_is_accepted_then_is_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, scope = make(tmp)
            self.assertEqual(ss.state(scope, d)[0], "waiting")
            av.add_row(d, "review", "r", "User")
            self.assertEqual(ss.state(scope, d)[0], "waiting")  # a review is not acceptance
            av.add_row(d, "accept", "a", "User")
            self.assertEqual(ss.state(scope, d)[0], "ready")

    def test_a_real_scope_with_no_accepted_definition_is_the_fallback_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, scope = make(tmp, real_scope())
            self.assertEqual(ss.state(scope, d)[0], "fallback")

    def test_accepted_but_unstamped_then_stamped_then_stale_after_a_refinement(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, scope = make(tmp, real_scope())
            av.add_row(d, "accept", "a", "User")
            self.assertEqual(ss.state(scope, d)[0], "unstamped")
            self.assertTrue(ss.stamp(scope, d)[0])
            self.assertEqual(ss.state(scope, d)[0], "ok")
            (d / "sections" / "goal.tex").write_text("a new goal\n", encoding="utf-8")
            av.add_row(d, "refine", "changed the goal", "Claude")
            code, message = ss.state(scope, d)
            self.assertEqual(code, "stale")
            self.assertIn("goal", message)
            self.assertNotIn("problem", message)

    def test_a_change_to_a_section_scope_is_not_drawn_from_does_not_make_it_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, scope = make(tmp, real_scope())
            av.add_row(d, "accept", "a", "User")
            ss.stamp(scope, d)
            (d / "sections" / "stakeholders.tex").write_text("other\n", encoding="utf-8")
            av.add_row(d, "refine", "stakeholders", "Claude")
            self.assertEqual(ss.state(scope, d)[0], "ok")


class Stamping(unittest.TestCase):
    def test_stamp_is_refused_before_acceptance_and_for_a_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, scope = make(tmp, real_scope())
            self.assertFalse(ss.stamp(scope, d)[0])
            av.add_row(d, "accept", "a", "User")
            scope.write_text("<!-- placeholder -->\n", encoding="utf-8")
            self.assertFalse(ss.stamp(scope, d)[0])

    def test_stamping_twice_replaces_the_header_and_keeps_the_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, scope = make(tmp, real_scope())
            av.add_row(d, "accept", "a", "User")
            ss.stamp(scope, d)
            ss.stamp(scope, d)
            text = scope.read_text(encoding="utf-8")
            self.assertEqual(text.count("derived-from"), 1)
            self.assertIn("In scope: things.", text)
            self.assertTrue(text.startswith("<!-- derived-from: definition v1.0 "))


class ConvertWarning(unittest.TestCase):
    def test_warns_only_when_the_pipeline_is_present_and_the_definition_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, _ = make(tmp)
            self.assertIsNotNone(ss.convert_warning(d))
            av.add_row(d, "accept", "a", "User")
            self.assertIsNone(ss.convert_warning(d))
            self.assertIsNone(ss.convert_warning(Path(tmp) / "nope"))


if __name__ == "__main__":
    unittest.main()
