"""Tests for lit_search.py: rounds, the held-paper filter, picks, the table and the vocabulary step.

No network: lit_search.FETCH is replaced by a function that answers from a small fake.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lit_search as ls  # noqa: E402

LEADS_TEXT = """# Leads

## Table

| Lead | Serves (scope item or gap) | Found via | State | Access note (DOI, URL, why blocked) | Date |
|---|---|---|---|---|---|
| A paper we already track | item | search | found | DOI 10.1000/held.1 | 2026-01-01 |
"""

CATALOG_TEXT = """<!-- entry:one -->
title: A Catalogued Study of Things
year: 2020
<!-- /entry -->
"""


def work(wid, title, year=2020, cited=10, doi=None, pdf=None, oa=False, wtype="article",
         lang="en", abstract=None, topics=(), refs=(), venue="Journal X", author="Ann Writer"):
    inverted = None
    if abstract:
        inverted = {}
        for i, w in enumerate(abstract.split()):
            inverted.setdefault(w, []).append(i)
    return {
        "id": f"https://openalex.org/{wid}", "doi": f"https://doi.org/{doi}" if doi else None,
        "title": title, "publication_year": year, "type": wtype, "language": lang,
        "cited_by_count": cited,
        "primary_location": {"source": {"display_name": venue}, "landing_page_url": "https://x.example/p"},
        "best_oa_location": {"pdf_url": pdf, "source": {"display_name": "Repo"}, "version": "publishedVersion"} if pdf else None,
        "locations": [], "open_access": {"is_oa": oa},
        "abstract_inverted_index": inverted,
        "topics": [{"display_name": t} for t in topics],
        "referenced_works": [f"https://openalex.org/{r}" for r in refs],
        "authorships": [{"author": {"display_name": author}}],
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.saved = (ls.SEARCHES, ls.CATALOG, ls.LEADS, ls.FETCH)
        ls.SEARCHES, ls.CATALOG, ls.LEADS = root / "searches", root / "catalog.md", root / "leads.md"
        ls.LEADS.write_text(LEADS_TEXT, encoding="utf-8")
        ls.CATALOG.write_text(CATALOG_TEXT, encoding="utf-8")
        self.works = []
        self.urls = []
        ls.FETCH = self.fake

    def tearDown(self):
        ls.SEARCHES, ls.CATALOG, ls.LEADS, ls.FETCH = self.saved
        self.tmp.cleanup()

    def fake(self, url):
        self.urls.append(url)
        parsed = urlparse(url)
        if parsed.path.startswith("/works/") and parsed.path != "/works":
            ident = parsed.path.rsplit("/", 1)[-1]
            return next(w for w in self.works if w["id"].endswith(ident))
        return {"results": list(self.works)}

    def start(self, angles=("plain: the problem in plain words",)):
        rnd = ls.new_round("an item")
        ls.declare_angles(rnd, list(angles))
        return rnd


class Helpers(unittest.TestCase):
    def test_titles_and_dois_are_normalised(self):
        self.assertEqual(ls.norm_title("A  Study: of THINGS!"), "a study of things")
        self.assertEqual(ls.norm_doi("https://doi.org/10.1/ABC"), "10.1/abc")

    def test_abstract_is_rebuilt_in_order(self):
        self.assertEqual(ls.abstract_text({"world": [1], "hello": [0]}), "hello world")

    def test_similar_queries_are_close(self):
        self.assertGreaterEqual(ls.similarity("kalman filter estimation", "estimation kalman filter"), 0.8)
        self.assertLess(ls.similarity("kalman filter estimation", "neural network survey"), 0.3)


class Search(Base):
    def test_an_undeclared_angle_is_refused(self):
        rnd = ls.new_round("x")
        with self.assertRaises(SystemExit):
            ls.search_round(rnd, "plain", "q", False, None, 25)

    def test_new_candidates_are_stored_with_how_they_were_found(self):
        self.works = [work("W1", "Alpha methods", doi="10.1/a", pdf="https://r.example/a.pdf")]
        rnd = self.start()
        found, new, n_held, n_prop, flags = ls.search_round(rnd, "plain", "alpha", False, None, 25)
        self.assertEqual((len(found), new, n_held), (1, 1, 0))
        cand = rnd["candidates"]["W1"]
        self.assertEqual(cand["access"], "open copy found")
        self.assertEqual(cand["found_via"], [{"kind": "query", "angle": "plain"}])

    def test_papers_in_the_catalog_or_leads_never_come_back(self):
        self.works = [work("W2", "A Catalogued Study of Things"),
                      work("W3", "Different title", doi="10.1000/HELD.1"),
                      work("W4", "A paper we already track"),
                      work("W5", "Fresh paper")]
        rnd = self.start()
        _, new, n_held, _, _ = ls.search_round(rnd, "plain", "q", False, None, 25)
        self.assertEqual((new, n_held), (1, 3))
        self.assertEqual(list(rnd["candidates"]), ["W5"])

    def test_a_paper_proposed_in_an_earlier_round_is_not_proposed_again(self):
        self.works = [work("W6", "Once proposed")]
        first = self.start()
        ls.search_round(first, "plain", "q", False, None, 25)
        ls.add_pick(first, "W6", "r", "c")
        ls.save_round(first)
        second = self.start()
        _, new, _, n_prop, _ = ls.search_round(second, "plain", "q", False, None, 25)
        self.assertEqual((new, n_prop), (0, 1))

    def test_a_second_angle_adds_to_found_via_not_a_duplicate(self):
        self.works = [work("W7", "Seen twice")]
        rnd = self.start(["plain: a", "method: b"])
        ls.search_round(rnd, "plain", "one", False, None, 25)
        ls.search_round(rnd, "method", "two", False, None, 25)
        self.assertEqual(len(rnd["candidates"]), 1)
        self.assertEqual(len(rnd["candidates"]["W7"]["found_via"]), 2)

    def test_access_is_paywalled_unknown_or_open(self):
        self.assertEqual(ls.candidate(work("W8", "t"))["access"], "paywalled (you fetch)")
        self.assertEqual(ls.candidate(work("W8", "t", oa=True))["access"], "unknown")
        self.assertEqual(ls.candidate(work("W8", "t", oa=True, pdf="https://x/p.pdf"))["access"],
                         "open copy found")

    def test_a_reworded_query_is_flagged(self):
        self.works = [work("W9", "x")]
        rnd = self.start()
        ls.search_round(rnd, "plain", "kalman filter vehicle estimation", False, None, 25)
        *_, flags = ls.search_round(rnd, "plain", "vehicle estimation kalman filter", False, None, 25)
        self.assertEqual(len(flags), 1)

    def test_reviews_mode_asks_for_reviews_and_for_surveys_in_title_or_abstract(self):
        self.works = [work("W10", "A survey")]
        rnd = self.start()
        ls.search_round(rnd, "plain", "q", True, 2015, 25)
        joined = " ".join(self.urls)
        self.assertIn("type:review", joined)
        self.assertIn("title_and_abstract.search:survey|review|overview", joined)
        self.assertIn("from_publication_date:2015-01-01", joined)

    def test_cited_by_seed_records_where_it_came_from(self):
        self.works = [work("W99", "The seed"), work("W11", "Citing paper")]
        rnd = self.start()
        ls.seed_round(rnd, "W99", "cited-by", 25)
        self.assertEqual(rnd["candidates"]["W11"]["found_via"],
                         [{"kind": "cited-by", "seed": "W99"}])

    def test_references_seed_fetches_the_listed_works(self):
        self.works = [work("W12", "Seed", refs=["W20", "W21"])]
        rnd = self.start()
        seed, found, *_ = ls.seed_round(rnd, "W12", "references", 25)
        self.assertTrue(any("openalex:W20|W21" in u for u in self.urls))


class Show(Base):
    def test_describe_gives_the_records_own_words_and_says_when_there_is_no_abstract(self):
        with_abs = ls.candidate(work("W1", "Alpha", abstract="a plain abstract", topics=["Control"]))
        text = ls.describe(with_abs)
        self.assertIn("abstract: a plain abstract", text)
        self.assertIn("topics: Control", text)
        self.assertIn("publisher withholds", ls.describe(ls.candidate(work("W2", "Beta"))))


class Picks(Base):
    def test_only_returned_papers_can_be_proposed(self):
        rnd = self.start()
        with self.assertRaises(SystemExit):
            ls.add_pick(rnd, "W404", "from memory", "item")

    def test_a_paper_is_picked_once(self):
        self.works = [work("W1", "t")]
        rnd = self.start()
        ls.search_round(rnd, "plain", "q", False, None, 25)
        ls.add_pick(rnd, "W1", "r", "c")
        with self.assertRaises(SystemExit):
            ls.add_pick(rnd, "W1", "r", "c")


class View(Base):
    def make_round(self):
        self.works = [
            work("W1", "Open paper", year=2019, cited=212, doi="10.1/open", pdf="https://r.example/o.pdf"),
            work("W2", "Paywalled paper", year=2021, cited=87, doi="10.1/pay", venue="IEEE Trans X"),
            work("W3", "Eine Arbeit", year=2018, lang="de"),
            work("W4", "A master thesis", wtype="dissertation"),
        ]
        rnd = self.start(["plain: a", "method: never searched"])
        ls.search_round(rnd, "plain", "q", False, None, 25)
        for wid in ("W1", "W2", "W3", "W4"):
            ls.add_pick(rnd, wid, f"why {wid}", "item one")
        return rnd

    def test_table_has_the_agreed_columns_and_no_have_column(self):
        text = ls.render_round(self.make_round(), None)
        self.assertIn("| # | Title | Year | Venue | Cited | Access | Covers | Found via |", text)
        self.assertNotIn("Have?", text)

    def test_language_and_thesis_show_in_the_venue_cell(self):
        text = ls.render_round(self.make_round(), None)
        self.assertIn("(de)", text)
        self.assertIn("thesis", text)

    def test_only_papers_without_an_open_copy_are_listed_to_fetch_by_hand(self):
        text = ls.render_round(self.make_round(), None)
        manual = text.split("## To fetch by hand")[1].split("## Queries run")[0]
        self.assertIn("https://doi.org/10.1/pay", manual)
        self.assertNotIn("10.1/open", manual)
        self.assertIn("scholar.google.com", manual)

    def test_the_reading_names_untried_angles_and_never_says_covered(self):
        text = ls.render_round(self.make_round(), None)
        self.assertIn("Angles declared but not yet searched: method", text)
        self.assertIn("does not say a topic is covered", text)

    def test_reading_reports_the_share_from_citations(self):
        rnd = self.make_round()
        rnd["candidates"]["W1"]["found_via"] = [{"kind": "cited-by", "seed": "W9"}]
        text = ls.render_round(rnd, None)
        self.assertIn("references or citations: 25%", text)

    def test_fresh_angle_share_compares_with_the_previous_round(self):
        previous = {"queries": [{"angle": "plain"}]}
        rnd = self.make_round()
        rnd["candidates"]["W1"]["found_via"] = [{"kind": "query", "angle": "method"}]
        _, fresh = ls.drift(rnd, previous)
        self.assertEqual(fresh, 0.25)

    def test_filename_is_surname_year_and_title_words(self):
        c = ls.candidate(work("W1", "Estimating the Road Bank Angle", year=2022, author="Ann Q. Writer"))
        self.assertEqual(ls.filename(c), "Writer2022-estimating-the-road-bank.pdf")


class Approve(Base):
    def test_numbers_become_found_rows_in_leads_and_are_not_added_twice(self):
        self.works = [work("W1", "First", doi="10.1/f", pdf="https://r.example/f.pdf"),
                      work("W2", "Second", doi="10.1/s")]
        rnd = self.start()
        ls.search_round(rnd, "plain", "q", False, None, 25)
        ls.add_pick(rnd, "W1", "r", "item one")
        ls.add_pick(rnd, "W2", "r", "item one")
        rows = ls.approve(rnd, ls.parse_numbers("1", 2))
        self.assertEqual(len(rows), 1)
        text = ls.LEADS.read_text(encoding="utf-8")
        self.assertIn("| First | item one | round 1: plain | found | DOI 10.1/f; open copy: https://r.example/f.pdf |", text)
        self.assertNotIn("| Second |", text)
        self.assertEqual(ls.approve(rnd, [1]), [])

    def test_numbers_accept_lists_and_ranges_and_reject_strangers(self):
        self.assertEqual(ls.parse_numbers("1,2, 6-8", 9), [1, 2, 6, 7, 8])
        with self.assertRaises(SystemExit):
            ls.parse_numbers("3,12", 5)

    def test_crlf_in_leads_is_kept(self):
        ls.LEADS.write_bytes(LEADS_TEXT.replace("\n", "\r\n").encode("utf-8"))
        self.works = [work("W1", "First", doi="10.1/f")]
        rnd = self.start()
        ls.search_round(rnd, "plain", "q", False, None, 25)
        ls.add_pick(rnd, "W1", "r", "c")
        ls.approve(rnd, [1])
        raw = ls.LEADS.read_bytes()
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))


class Vocabulary(Base):
    def test_terms_not_yet_searched_come_back_with_their_source(self):
        self.works = [
            work("W1", "Slip estimation", abstract="a sliding mode observer for tyre slip", topics=["Vehicle Dynamics"]),
            work("W2", "Grip estimation", abstract="sliding mode observer applied to grip", topics=["Vehicle Dynamics"]),
        ]
        rnd = self.start()
        ls.search_round(rnd, "plain", "estimation of tyre slip", False, None, 25)
        terms = {(t, src) for t, _, src in ls.vocabulary(rnd)}
        self.assertIn(("sliding mode", "abstract"), terms)
        self.assertIn(("Vehicle Dynamics", "topic label"), terms)
        self.assertNotIn("tyre slip", {t for t, _ in terms})


if __name__ == "__main__":
    unittest.main()
