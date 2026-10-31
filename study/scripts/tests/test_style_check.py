"""Tests for style_check.py: the advisory check for padded writing.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import style_check as sc  # noqa: E402

PHRASES = sc.load_phrases()


def article(tmp, **sections):
    d = Path(tmp) / "a"
    (d / "sections").mkdir(parents=True)
    (d / "main.tex").write_text("\\begin{document}\n\\end{document}\n", encoding="utf-8")
    for name, text in sections.items():
        (d / "sections" / f"{name}.tex").write_text(text, encoding="utf-8")
    return d


def rules(findings, severity=None):
    return [f.rule for f in findings if severity in (None, f.severity)]


class Phrases(unittest.TestCase):
    def test_a_filler_phrase_is_a_problem_and_a_clean_sentence_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="It is important to note that the filter has a delay of 12 ms.\n"
                                    "The filter has a delay of 12 ms [x].\n")
            found = sc.check_article(d, PHRASES)
            self.assertEqual(rules(found, "problem").count("filler phrase"), 1)

    def test_a_summary_phrase_is_fine_in_a_conclusion_but_not_elsewhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="In summary, the estimator drifts after 40 s of dead reckoning.\n",
                        conclusion="In summary, the estimator drifts after 40 s of dead reckoning.\n")
            found = [f for f in sc.check_article(d, PHRASES) if f.rule.startswith("summary phrase")]
            self.assertEqual([f.file for f in found], ["sections/intro.tex"])

    def test_an_evaluative_word_is_only_a_judgment_when_nothing_backs_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="The method is robust against noise in every test case we ran.\n"
                                    "The method keeps the error under 2 percent, which is robust enough.\n")
            found = [f for f in sc.check_article(d, PHRASES) if f.rule.startswith("evaluative")]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].severity, "judgment")
            self.assertEqual(found[0].line, 1)

    def test_a_claim_with_no_source_is_a_problem_unless_it_cites(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="Studies show that the error grows with speed.\n"
                                    "Studies show that the error grows with speed \\cite{x2020}.\n")
            found = [f for f in sc.check_article(d, PHRASES) if f.rule == "claim with no named source"]
            self.assertEqual([f.line for f in found], [1])

    def test_stacked_hedges_are_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="The delay could potentially exceed the limit at low speed.\n")
            self.assertIn("stacked hedges", rules(sc.check_article(d, PHRASES), "problem"))


class Restating(unittest.TestCase):
    A = "The estimator combines readings from two independent sensors to estimate the unknown quantity during every transition phase."
    B = "To estimate the unknown quantity during every transition phase, the estimator combines readings from two independent sensors."

    def test_the_same_content_in_two_sections_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro=self.A + "\n", method=self.B + "\n")
            self.assertIn("says what another sentence says", rules(sc.check_article(d, PHRASES), "problem"))

    def test_a_conclusion_may_restate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro=self.A + "\n", conclusion=self.B + "\n")
            self.assertEqual(rules(sc.check_article(d, PHRASES)), [])

    def test_an_abstract_may_restate(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro=self.A + "\n")
            (d / "main.tex").write_text(
                "\\begin{document}\n\\begin{abstract}\n" + self.B + "\n\\end{abstract}\n\\end{document}\n",
                encoding="utf-8")
            self.assertEqual(rules(sc.check_article(d, PHRASES)), [])

    def test_a_nearby_sentence_that_repeats_is_a_judgment_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="The scheduler limits the batch size to protect memory headroom on small machines. "
                                    "Small machines have little memory headroom, so the limit on batch size applies there.\n")
            self.assertIn("restated in a nearby sentence", rules(sc.check_article(d, PHRASES), "judgment"))

    def test_two_clauses_of_one_sentence_saying_the_same_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="The filter removes high frequency measurement noise from the signal, "
                                    "removing measurement noise at high frequency from the signal.\n")
            self.assertIn("two clauses of one sentence say the same", rules(sc.check_article(d, PHRASES)))

    def test_different_content_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="The estimator combines two sensor readings into one position estimate.\n",
                        method="The planner assigns each task to a worker from the current queue length.\n")
            self.assertEqual(rules(sc.check_article(d, PHRASES)), [])


class Masking(unittest.TestCase):
    def test_todo_text_comments_math_tables_and_ignored_lines_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro=(
                "\\todo{It is important to note that this is robust and comprehensive.}\n"
                "% it is important to note this comment\n"
                "$a = b$ and \\begin{equation} it is important to note \\end{equation}\n"
                "\\begin{tabularx}{\\linewidth}{LL} it is important to note & x \\end{tabularx}\n"
                "A novel remark kept on purpose. % style-ignore\n"))
            self.assertEqual(rules(sc.check_article(d, PHRASES)), [])

    def test_generated_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, references="It is important to note this generated text.\n")
            self.assertEqual(rules(sc.check_article(d, PHRASES)), [])

    def test_a_citation_and_an_abbreviation_do_not_break_a_sentence(self):
        sentences = sc.split_sentences("The gain is 3.5 e.g. at low speed, as in Fig. 2 and Eq. 4 of the paper.")
        self.assertEqual(len(sentences), 1)


class Lists(unittest.TestCase):
    def test_a_list_of_bare_phrases_is_a_judgment_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro="\\begin{itemize}\n\\item Alpha\n\\item Beta\n\\item Gamma\n"
                                    "\\item Delta\n\\end{itemize}\n")
            self.assertIn("list of bare phrases", rules(sc.check_article(d, PHRASES), "judgment"))


class Length(unittest.TestCase):
    def test_a_very_long_sentence_is_a_judgment_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = article(tmp, intro=" ".join(["word%d" % i for i in range(45)]).replace("word", "alpha") + ".\n")
            self.assertTrue(any(r.startswith("sentence of") for r in rules(sc.check_article(d, PHRASES))))


if __name__ == "__main__":
    unittest.main()
