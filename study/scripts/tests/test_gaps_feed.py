"""Tests for the decision-tree feed into topics/gaps.md.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_gaps_index as g  # noqa: E402

HEAD = "| Q | question | answer | status | then | method | source | motivation |\n|---|---|---|---|---|---|---|---|\n"
TREE = (
    "<!-- decision-tree -->\n" + HEAD
    + "| Q1 | Which family? | filter | chosen | END | Filter method | | proven |\n"
    + "| Q1 | | table | explored | | Table method | | coarse |\n"
    + "| Q1 | | learned | identified | | Learned model | | |\n"
    + "| Q1 | | hybrid | identified | | Hybrid method | | |\n"
    + "<!-- /decision-tree -->\n"
)


class TreeGapLines(unittest.TestCase):
    def test_only_identified_answers_become_gaps(self):
        lines = g.tree_gap_lines(TREE)
        self.assertEqual(len(lines), 2)
        self.assertIn("**Learned model**", lines[0])
        self.assertIn('answer "learned" to Q1: Which family?', lines[0])
        self.assertIn("never examined", lines[0])
        self.assertFalse(any("Table method" in ln for ln in lines))

    def test_an_invalid_tree_is_skipped_not_half_listed(self):
        bad = TREE.replace("| chosen | END |", "| chosen | Q9 |")
        self.assertEqual(g.tree_gap_lines(bad), [])

    def test_no_tree_no_gaps(self):
        self.assertEqual(g.tree_gap_lines("just prose"), [])

    def test_two_trees_in_one_file(self):
        self.assertEqual(len(g.tree_gap_lines(TREE + "\n" + TREE)), 4)


class ReplaceBlock(unittest.TestCase):
    def test_replaces_only_between_the_markers_and_is_idempotent(self):
        text = f"before\n{g.TREE_BEGIN}\nold\n{g.TREE_END}\nafter\n"
        once = g.replace_block(text, g.TREE_BEGIN, g.TREE_END, "new content")
        self.assertIn("new content", once)
        self.assertNotIn("old", once)
        self.assertTrue(once.startswith("before\n") and once.endswith("after\n"))
        self.assertEqual(g.replace_block(once, g.TREE_BEGIN, g.TREE_END, "new content"), once)

    def test_the_two_blocks_do_not_collide(self):
        text = (f"{g.BEGIN_MARKER}\nA\n{g.END_MARKER}\n\n{g.TREE_BEGIN}\nB\n{g.TREE_END}\n")
        out = g.replace_block(text, g.BEGIN_MARKER, g.END_MARKER, "A2")
        out = g.replace_block(out, g.TREE_BEGIN, g.TREE_END, "B2")
        self.assertIn("A2", out)
        self.assertIn("B2", out)
        self.assertNotIn("\nA\n", out)
        self.assertNotIn("\nB\n", out)


if __name__ == "__main__":
    unittest.main()
