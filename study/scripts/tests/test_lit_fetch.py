"""Tests for lit_fetch.py: downloading, the first-page check, leads states, the user's own files.

No network and no PDF library: lit_fetch.DOWNLOAD and lit_fetch.PAGE_TEXT are replaced.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lit_fetch as lf  # noqa: E402
import lit_search as ls  # noqa: E402
from test_lit_search import LEADS_TEXT, work  # noqa: E402

PDF = b"%PDF-1.7\n" + b"x" * 20_000


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.saved = (ls.SEARCHES, ls.CATALOG, ls.LEADS, ls.FETCH, lf.PDFS, lf.DOWNLOAD, lf.PAGE_TEXT)
        ls.SEARCHES, ls.CATALOG, ls.LEADS = root / "searches", root / "catalog.md", root / "leads.md"
        lf.PDFS = root / "PDFs"
        ls.LEADS.write_text(LEADS_TEXT, encoding="utf-8")
        ls.CATALOG.write_text("", encoding="utf-8")
        self.files = {}        # url -> bytes, or an Exception to raise
        self.texts = {}        # file name (or "*") -> first-pages text
        self.calls = []
        lf.DOWNLOAD = self.download
        lf.PAGE_TEXT = lambda path: self.texts.get(Path(path).name, self.texts.get("*"))
        self.works = []
        ls.FETCH = lambda url: {"results": list(self.works)}

    def tearDown(self):
        (ls.SEARCHES, ls.CATALOG, ls.LEADS, ls.FETCH, lf.PDFS, lf.DOWNLOAD, lf.PAGE_TEXT) = self.saved
        self.tmp.cleanup()

    def download(self, url):
        self.calls.append(url)
        got = self.files.get(url, lf.FetchError("HTTP 403"))
        if isinstance(got, Exception):
            raise got
        return got

    def approved_round(self, *works):
        self.works = list(works)
        rnd = ls.new_round("item")
        ls.declare_angles(rnd, ["plain: a"])
        ls.search_round(rnd, "plain", "q", False, None, 25)
        for w in works:
            ls.add_pick(rnd, ls.short_id(w["id"]), "r", "item one")
        ls.approve(rnd, list(range(1, len(works) + 1)))
        return rnd

    def lead_state(self, title):
        row = lf.lead_for(title)
        return row["cells"][3], row["cells"][4]


TITLE = "Estimating the road bank angle"


class Fetch(Base):
    def test_a_matching_pdf_is_filed_and_the_lead_becomes_fetched(self):
        w = work("W1", TITLE, year=2020, doi="10.1/a", pdf="https://r.example/a.pdf")
        self.files["https://r.example/a.pdf"] = PDF
        self.texts["*"] = f"{TITLE}\nAnn Writer\nAbstract " + "word " * 30
        rnd = self.approved_round(w)
        results = lf.fetch_round(rnd)
        self.assertEqual(results[0][2]["state"], "fetched")
        self.assertTrue((lf.PDFS / "Writer2020-estimating-the-road-bank.pdf").exists())
        state, note = self.lead_state(TITLE)
        self.assertEqual(state, "fetched")
        self.assertIn("PDFs/Writer2020-estimating-the-road-bank.pdf", note)

    def test_a_landing_page_saved_as_a_pdf_is_not_kept(self):
        w = work("W1", TITLE, pdf="https://r.example/a.pdf")
        self.files["https://r.example/a.pdf"] = b"<html>login</html>" + b"x" * 20_000
        rnd = self.approved_round(w)
        results = lf.fetch_round(rnd)
        self.assertEqual(results[0][2]["state"], "blocked")
        self.assertIn("not a PDF", results[0][2]["reason"])
        self.assertEqual(self.lead_state(TITLE)[0], "blocked")
        self.assertFalse(list(lf.PDFS.glob("*.pdf")) if lf.PDFS.exists() else [])

    def test_a_pdf_of_another_paper_is_rejected_and_the_next_location_is_tried(self):
        w = work("W1", TITLE, pdf="https://r.example/wrong.pdf")
        w["locations"] = [{"pdf_url": "https://s.example/right.pdf", "is_oa": True,
                           "source": {"display_name": "Other"}, "version": ""}]
        self.files["https://r.example/wrong.pdf"] = PDF
        self.files["https://s.example/right.pdf"] = PDF + b"y"
        texts = {"wrong": "An entirely different paper about batteries and cells " * 3,
                 "right": f"{TITLE} " + "body " * 30}
        order = iter(["wrong", "right"])
        lf.PAGE_TEXT = lambda path: texts[next(order)]
        rnd = self.approved_round(w)
        result = lf.fetch_round(rnd)[0][2]
        self.assertEqual(result["state"], "fetched")
        self.assertEqual(len(result["tried"]), 2)
        self.assertIn("do not match", result["tried"][0]["result"])
        self.assertEqual(result["source"], "https://s.example/right.pdf")

    def test_every_location_is_tried_once_then_the_lead_is_blocked_with_the_reasons(self):
        w = work("W1", TITLE, pdf="https://r.example/a.pdf")
        w["locations"] = [{"pdf_url": "https://s.example/b.pdf", "is_oa": True,
                           "source": {"display_name": "Other"}, "version": ""}]
        rnd = self.approved_round(w)
        result = lf.fetch_round(rnd)[0][2]
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(self.calls, ["https://r.example/a.pdf", "https://s.example/b.pdf"])
        self.assertIn("HTTP 403", self.lead_state(TITLE)[1])

    def test_a_scan_is_kept_but_reported_as_unchecked(self):
        w = work("W1", TITLE, pdf="https://r.example/a.pdf")
        self.files["https://r.example/a.pdf"] = PDF
        self.texts["*"] = ""
        rnd = self.approved_round(w)
        result = lf.fetch_round(rnd)[0][2]
        self.assertEqual((result["state"], result["check"]), ("fetched", "unchecked"))
        self.assertIn("not checked", self.lead_state(TITLE)[1])

    def test_a_paper_already_fetched_is_not_fetched_twice(self):
        w = work("W1", TITLE, pdf="https://r.example/a.pdf")
        self.files["https://r.example/a.pdf"] = PDF
        self.texts["*"] = f"{TITLE} " + "body " * 30
        rnd = self.approved_round(w)
        lf.fetch_round(rnd)
        self.assertEqual(lf.fetch_round(rnd), [])
        self.assertEqual(len(self.calls), 1)

    def test_a_paper_without_an_open_copy_is_blocked_without_a_request(self):
        rnd = self.approved_round(work("W1", TITLE, doi="10.1/p"))
        result = lf.fetch_round(rnd)[0][2]
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(self.calls, [])

    def test_the_view_lists_blocked_papers_to_fetch_by_hand(self):
        rnd = self.approved_round(work("W1", TITLE, doi="10.1/p", pdf="https://r.example/a.pdf"))
        lf.fetch_round(rnd)
        text = ls.render_round(rnd, None)
        self.assertIn("## To fetch by hand", text)
        self.assertIn("https://doi.org/10.1/p", text)
        self.assertIn("## Fetch results", text)

    def test_the_doi_on_the_first_page_counts_as_a_match(self):
        self.assertEqual(lf.title_score("see doi: 10.1/ a", "Totally different title words", "10.1/a"), 1.0)

    def test_a_clash_in_the_target_name_gets_a_suffix(self):
        lf.PDFS.mkdir(parents=True)
        (lf.PDFS / "a.pdf").write_bytes(b"x")
        self.assertEqual(lf.unique_path(lf.PDFS, "a.pdf").name, "a~2.pdf")


class MatchOwnFiles(Base):
    def setUp(self):
        super().setUp()
        self.rnd = self.approved_round(
            work("W1", TITLE, year=2020, doi="10.1/a"),
            work("W2", "A study of tyre grip on wet surfaces", year=2019, doi="10.1/b"))
        lf.fetch_round(self.rnd)         # both blocked: no open copy
        ls.save_round(self.rnd)
        self.inbox = ls.SEARCHES / "inbox"
        self.inbox.mkdir(parents=True)

    def test_a_saved_file_is_matched_filed_and_marked_user_fetched(self):
        (self.inbox / "download (1).pdf").write_bytes(PDF)
        self.texts["download (1).pdf"] = f"{TITLE} Ann Writer " + "text " * 30
        matched, problems = lf.match_folder(self.inbox)
        self.assertEqual((len(matched), problems), (1, []))
        self.assertTrue((lf.PDFS / "Writer2020-estimating-the-road-bank.pdf").exists())
        self.assertFalse((self.inbox / "download (1).pdf").exists())
        self.assertEqual(self.lead_state(TITLE)[0], "user-fetched")
        self.assertEqual(self.lead_state("A study of tyre grip on wet surfaces")[0], "blocked")

    def test_a_file_matching_no_lead_is_left_in_the_inbox_and_reported(self):
        (self.inbox / "mine.pdf").write_bytes(PDF)
        self.texts["mine.pdf"] = "Something about gearboxes and nothing else " * 5
        matched, problems = lf.match_folder(self.inbox)
        self.assertEqual(matched, [])
        self.assertIn("no lead matches", problems[0][1])
        self.assertTrue((self.inbox / "mine.pdf").exists())

    def test_a_file_with_no_text_cannot_be_matched(self):
        (self.inbox / "scan.pdf").write_bytes(PDF)
        self.texts["scan.pdf"] = ""
        matched, problems = lf.match_folder(self.inbox)
        self.assertEqual(matched, [])
        self.assertIn("no readable text", problems[0][1])

    def test_a_file_that_fits_two_leads_equally_is_not_guessed(self):
        (self.inbox / "both.pdf").write_bytes(PDF)
        self.texts["both.pdf"] = f"{TITLE} and also A study of tyre grip on wet surfaces " + "x " * 30
        matched, problems = lf.match_folder(self.inbox)
        self.assertEqual(matched, [])
        self.assertIn("two leads", problems[0][1])


if __name__ == "__main__":
    unittest.main()
