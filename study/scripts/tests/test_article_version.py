"""Tests for article_version.py: the version history that stops silent edits.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import article_version as v  # noqa: E402


def make_article(root, name="a"):
    d = Path(root) / name
    (d / "sections").mkdir(parents=True)
    (d / "main.tex").write_text("main\n", encoding="utf-8")
    (d / "sections" / "intro.tex").write_text("intro\n", encoding="utf-8")
    (d / "sections" / "method.tex").write_text("method\n", encoding="utf-8")
    return d


def write(d, rel, text):
    (d / rel).write_text(text, encoding="utf-8")


class Recording(unittest.TestCase):
    def test_draft_is_0_1_and_lists_every_tracked_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            row, err = v.add_row(d, "draft", "First draft", "Claude")
            self.assertIsNone(err)
            self.assertEqual(row["version"], "0.1")
            self.assertEqual(row["changed"], ["main.tex", "sections/intro.tex", "sections/method.tex"])

    def test_edit_bumps_the_minor_number_and_names_what_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            write(d, "sections/method.tex", "method changed\n")
            row, err = v.add_row(d, "edit", "Rewrote the method", "Claude")
            self.assertIsNone(err)
            self.assertEqual(row["version"], "0.2")
            self.assertEqual(row["changed"], ["sections/method.tex"])

    def test_an_edit_with_no_change_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            row, err = v.add_row(d, "edit", "nothing", "Claude")
            self.assertIsNone(row)
            self.assertIn("nothing changed", err)

    def test_review_bumps_the_major_number_and_resets_the_minor(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            write(d, "sections/intro.tex", "x\n")
            v.add_row(d, "edit", "e", "Claude")
            row, err = v.add_row(d, "review", "Reviewed", "User")
            self.assertIsNone(err)
            self.assertEqual(row["version"], "1.0")

    def test_a_second_draft_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            self.assertIsNotNone(v.add_row(d, "draft", "again", "Claude")[1])

    def test_the_time_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            row, _ = v.add_row(d, "draft", "First draft", "Claude", now=datetime(2026, 10, 31, 14, 5))
            self.assertEqual(row["time"], "2026-10-31 14:05")


class SilentEdits(unittest.TestCase):
    def test_an_edit_without_a_version_row_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            self.assertIsNone(v.stale_files(d))
            v.add_row(d, "draft", "First draft", "Claude")
            self.assertEqual(v.stale_files(d), [])
            write(d, "sections/intro.tex", "sneaky\n")
            self.assertEqual(v.stale_files(d), ["sections/intro.tex"])

    def test_generated_files_and_line_endings_do_not_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            write(d, "sections/references.tex", "generated\n")
            (d / "sections" / "intro.tex").write_bytes(b"intro\r\n")
            self.assertEqual(v.stale_files(d), [])


class PrintedTable(unittest.TestCase):
    def history(self, d, minors_in_first, minors_in_second):
        v.add_row(d, "draft", "First draft", "Claude")
        for i in range(minors_in_first):
            write(d, "sections/intro.tex", f"a{i}\n")
            v.add_row(d, "edit", f"edit {i}", "Claude")
        v.add_row(d, "review", "Reviewed", "User", condensed="Everything between.")
        for i in range(minors_in_second):
            write(d, "sections/method.tex", f"b{i}\n")
            v.add_row(d, "edit", f"second {i}", "Claude")
        return v.load(d)["rows"]

    def test_the_open_major_version_is_shown_in_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            rows = self.history(d, 0, 3)
            self.assertEqual([r["version"] for r in v.display_rows(rows)], ["0.1", "1.0", "1.1", "1.2", "1.3"])

    def test_a_closed_major_version_folds_its_minor_rows_but_keeps_0_1_and_the_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            rows = self.history(d, 4, 1)
            shown = v.display_rows(rows)
            self.assertEqual([r["version"] for r in shown], ["0.1", "0.2–0.5", "1.0", "1.1"])
            self.assertEqual(shown[1]["summary"], "Everything between.")
            self.assertEqual(shown[1]["changed"], ["sections/intro.tex"])

    def test_the_data_file_keeps_every_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            self.assertEqual(len(self.history(d, 4, 1)), 7)

    def test_without_a_condensed_text_the_summaries_are_joined(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            for i in range(2):
                write(d, "sections/intro.tex", f"{i}\n")
                v.add_row(d, "edit", f"e{i}", "Claude")
            v.add_row(d, "review", "Reviewed", "User")
            shown = v.display_rows(v.load(d)["rows"])
            self.assertEqual(shown[1]["summary"], "e0; e1")

    def test_status_says_unreviewed_until_the_user_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            self.assertEqual(v.status_text(v.load(d)["rows"]), "not reviewed by the user")
            v.add_row(d, "review", "ok", "User", now=datetime(2026, 11, 2, 9, 0))
            self.assertEqual(v.status_text(v.load(d)["rows"]), "reviewed as v1.0 (2026-11-02)")
            write(d, "sections/intro.tex", "z\n")
            v.add_row(d, "edit", "e", "Claude")
            self.assertTrue(v.status_text(v.load(d)["rows"]).endswith("edited since"))

    def test_the_generated_file_defines_the_macros_and_escapes_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "Costs & 50% more", "Claude")
            text = (d / "sections" / "versions.tex").read_text(encoding="utf-8")
            self.assertIn("\\newcommand{\\articleversion}{0.1}", text)
            self.assertIn("Costs \\& 50\\% more", text)
            self.assertIn("\\newcommand{\\versiontable}", text)


class Acceptance(unittest.TestCase):
    def accepted_article(self, tmp):
        d = make_article(tmp)
        v.add_row(d, "draft", "First draft", "Claude")
        write(d, "sections/intro.tex", "a\n")
        v.add_row(d, "edit", "e", "Claude")
        row, err = v.add_row(d, "accept", "Accepted", "User")
        self.assertIsNone(err)
        self.assertEqual((row["version"], row["kind"]), ("1.0", "accepted"))
        return d

    def test_an_accepted_article_refuses_edit_and_takes_refine(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.accepted_article(tmp)
            write(d, "sections/method.tex", "changed\n")
            row, err = v.add_row(d, "edit", "e", "Claude")
            self.assertIsNone(row)
            self.assertIn("use refine", err)
            row, err = v.add_row(d, "refine", "Changed the method", "Claude")
            self.assertIsNone(err)
            self.assertEqual((row["version"], row["kind"]), ("1.1", "refined"))

    def test_refine_is_refused_before_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            write(d, "sections/intro.tex", "a\n")
            self.assertIn("use edit", v.add_row(d, "refine", "r", "Claude")[1])

    def test_status_follows_acceptance_and_counts_refinements(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.accepted_article(tmp)
            self.assertTrue(v.status_text(v.load(d)["rows"]).startswith("accepted as v1.0"))
            for i in range(2):
                write(d, "sections/method.tex", f"r{i}\n")
                v.add_row(d, "refine", f"r{i}", "Claude")
            self.assertTrue(v.status_text(v.load(d)["rows"]).endswith("refined since (2 changes)"))
            self.assertEqual(v.accepted_version(v.load(d)["rows"]), "1.0")

    def test_refinements_stay_visible_until_the_article_is_accepted_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.accepted_article(tmp)
            for i in range(3):
                write(d, "sections/method.tex", f"r{i}\n")
                v.add_row(d, "refine", f"r{i}", "Claude")
            v.add_row(d, "review", "Reviewed", "User")  # a review does not fold them
            shown = [r["version"] for r in v.display_rows(v.load(d)["rows"])]
            self.assertEqual(shown, ["0.1", "0.2", "1.0", "1.1", "1.2", "1.3", "2.0"])
            v.add_row(d, "accept", "Accepted again", "User", condensed="Three refinements.")
            shown = v.display_rows(v.load(d)["rows"])
            self.assertEqual([r["version"] for r in shown], ["0.1", "0.2", "1.0", "1.1–1.3", "2.0", "3.0"])
            self.assertEqual(shown[3]["summary"], "Three refinements.")

    def test_edits_still_fold_when_a_review_closes_their_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = make_article(tmp)
            v.add_row(d, "draft", "First draft", "Claude")
            for i in range(3):
                write(d, "sections/intro.tex", f"{i}\n")
                v.add_row(d, "edit", f"e{i}", "Claude")
            v.add_row(d, "review", "Reviewed", "User")
            shown = [r["version"] for r in v.display_rows(v.load(d)["rows"])]
            self.assertEqual(shown, ["0.1", "0.2–0.4", "1.0"])


if __name__ == "__main__":
    unittest.main()
