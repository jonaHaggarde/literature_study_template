"""Tests for build_decision_trees.py.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_decision_trees as t  # noqa: E402

HEAD = "| Q | question | answer | status | then | method | source | motivation |\n|---|---|---|---|---|---|---|---|\n"
GOOD = (
    HEAD
    + "| Q1 | How is it estimated? | model-based | explored | | Method P | | too fragile |\n"
    + "| Q1 | | filter-based | chosen | Q2 | | | proven |\n"
    + "| Q1 | | data-driven | identified | | Method Q | | |\n"
    + "| Q2 | Which filter? | linear | chosen | END | Linear filter | | simplest |\n"
    + "| Q2 | | nonlinear | explored | | Nonlinear filter | | costly |\n"
)


def doc(table):
    return f"intro\n\n<!-- decision-tree -->\n{table}<!-- /decision-tree -->\n\nafter\n"


class Parse(unittest.TestCase):
    def test_good_table_parses_and_validates(self):
        rows, problems = t.parse_table(GOOD)
        self.assertEqual(problems, [])
        self.assertEqual(len(rows), 5)
        self.assertEqual(t.validate(rows), [])

    def test_wrong_header_is_reported(self):
        _rows, problems = t.parse_table("| a | b |\n|---|---|\n| 1 | 2 |\n")
        self.assertIn("header", problems[0])

    def test_pipe_inside_a_cell_is_reported(self):
        bad = GOOD.replace("too fragile", "too | fragile")
        _rows, problems = t.parse_table(bad)
        self.assertTrue(any("cells" in p for p in problems))


class Rules(unittest.TestCase):
    def rows(self, text):
        rows, problems = t.parse_table(text)
        self.assertEqual(problems, [])
        return rows

    def test_two_chosen_answers(self):
        bad = GOOD.replace("| data-driven | identified | | Method Q | |", "| data-driven | chosen | Q2 | Method Q | |")
        self.assertTrue(any("more than one chosen" in p for p in t.validate(self.rows(bad))))

    def test_dangling_then(self):
        bad = GOOD.replace("| chosen | Q2 |", "| chosen | Q9 |")
        self.assertTrue(any("Q9" in p for p in t.validate(self.rows(bad))))

    def test_unreachable_question(self):
        bad = GOOD.replace("| chosen | Q2 |", "| chosen | END |").replace("| | Q2 |", "| | Q2 |")
        bad = bad.replace("| Q1 | | filter-based | chosen | END | |", "| Q1 | | filter-based | chosen | END | Final |")
        self.assertTrue(any("not reachable" in p for p in t.validate(self.rows(bad))))

    def test_rejected_answer_needs_a_method(self):
        bad = GOOD.replace("Method P", "")
        self.assertTrue(any("must name the method" in p for p in t.validate(self.rows(bad))))

    def test_then_only_on_chosen(self):
        bad = GOOD.replace("| explored | | Method P |", "| explored | Q2 | Method P |")
        self.assertTrue(any("only a chosen answer" in p for p in t.validate(self.rows(bad))))

    def test_unknown_status(self):
        bad = GOOD.replace("explored | | Method P", "rejected | | Method P")
        self.assertTrue(any("status" in p for p in t.validate(self.rows(bad))))

    def test_open_question_is_allowed(self):
        open_q = HEAD + "| Q1 | Which? | a | identified | | A | | |\n| Q1 | | b | identified | | B | | |\n"
        rows = self.rows(open_q)
        self.assertEqual(t.validate(rows), [])
        self.assertEqual(t.stats(rows)["decided"], 0)


class Stats(unittest.TestCase):
    def test_counts(self):
        rows, _ = t.parse_table(GOOD)
        s = t.stats(rows)
        self.assertEqual(s["questions"], 2)
        self.assertEqual(s["decided"], 2)
        self.assertEqual(s["alternatives"], 3)
        self.assertEqual(s["explored"], 2)
        self.assertEqual(s["motivations_missing"], 0)

    def test_missing_motivations_counted(self):
        rows, _ = t.parse_table(GOOD.replace("simplest", ""))
        self.assertEqual(t.stats(rows)["motivations_missing"], 1)


class Render(unittest.TestCase):
    def setUp(self):
        self.rows, _ = t.parse_table(GOOD)
        self.mm = t.render_mermaid(self.rows)

    def test_chosen_edges_are_thick_and_rejected_are_thin(self):
        self.assertIn('Q1 ==>|"filter-based"| Q2', self.mm)
        self.assertIn('Q1 -->|"model-based"| L_Q1_1', self.mm)
        # edges in order: Q1 model(0), Q1 filter(1, chosen), Q1 data(2), Q2 linear(3, chosen), Q2 nonlinear(4)
        self.assertIn("linkStyle 1,3 stroke:#0F6E56", self.mm)

    def test_statuses_become_classes(self):
        self.assertIn(":::explored", self.mm)
        self.assertIn(":::identified", self.mm)
        self.assertIn("(not examined)", self.mm)
        self.assertIn('R["Recommended: Linear filter"]:::recommended', self.mm)

    def test_quotes_are_escaped(self):
        rows, _ = t.parse_table(GOOD.replace("model-based", 'a "quoted" answer'))
        self.assertNotIn('"quoted"', t.render_mermaid(rows).replace("#quot;", ""))


class Escaping(unittest.TestCase):
    def test_angle_brackets_do_not_reach_mermaid_as_tags(self):
        rows, _ = t.parse_table(GOOD.replace("model-based", "<placeholder answer>"))
        mm = t.render_mermaid(rows)
        self.assertIn("#lt;placeholder answer#gt;", mm)
        self.assertNotIn("<placeholder", mm)
        self.assertIn("<br/>", mm)  # the generator's own line break survives


class InPlace(unittest.TestCase):
    def test_diagram_is_added_after_the_table(self):
        new, results = t.process_text(doc(GOOD))
        self.assertEqual(results[0][1], [])
        self.assertIn("```mermaid\nflowchart TD", new)
        self.assertLess(new.index("<!-- /decision-tree -->"), new.index("```mermaid"))
        self.assertTrue(new.rstrip().endswith("after"))

    def test_second_run_changes_nothing(self):
        once, _ = t.process_text(doc(GOOD))
        twice, _ = t.process_text(once)
        self.assertEqual(once, twice)

    def test_stale_diagram_is_replaced_not_duplicated(self):
        once, _ = t.process_text(doc(GOOD))
        edited = once.replace("simplest", "simplest and proven")
        again, _ = t.process_text(edited)
        self.assertEqual(again.count("```mermaid"), 1)

    def test_invalid_table_leaves_the_table_and_reports(self):
        bad = GOOD.replace("explored | | Method P", "rejected | | Method P")
        new, results = t.process_text(doc(bad))
        self.assertTrue(results[0][1])
        self.assertIn("rejected", new)
        self.assertNotIn("```mermaid", new)


if __name__ == "__main__":
    unittest.main()
