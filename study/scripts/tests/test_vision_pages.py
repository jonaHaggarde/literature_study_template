"""Tests for the vision budget (vision_pages.py): every rule that keeps spending small.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vision_pages as v  # noqa: E402

DAY = "2026-10-30"
CAPS = {"pages_per_ticket": 2, "pages_per_request": 5, "pages_per_day": 6, "tokens_per_page_estimate": 1000}
MANIFEST = {"scan.pdf": {"extraction": "ocr", "ocr_pages": [1, 2, 3, 4, 5, 6, 7, 8], "notes_path": "notes/scan.md"},
            "plain.pdf": {"extraction": "layout"}}
NOTE = ("---\ntitle: t\n---\n\n## Key Findings\n\nwritten\n\n## Content\n\n"
        + "".join(f"<!-- page: {n} (ocr) -->\n\nocr text of page {n}\n\n" for n in range(1, 9)))


def fake_render(doc, pages, dest):
    out = []
    for n in pages:
        p = Path(dest) / f"p{n}.png"
        p.write_bytes(b"png")
        out.append(p)
    return out


class Env(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = v.Store(self.root / ".ocr")
        self.manifest = {k: dict(m) for k, m in MANIFEST.items()}
        self.note = self.root / "scan.md"
        self.note.write_text(NOTE, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def planned(self, pages=(5, 6, 7)):
        return v.plan(self.store, CAPS, self.manifest, "scan", list(pages), DAY)[0]

    def approved(self, pages=(5, 6, 7)):
        rid = self.planned(pages)
        v.approve(self.store, rid, "now")
        return rid

    def ticket(self, rid):
        return v.ticket(self.store, CAPS, rid, DAY, fake_render)

    def write_out(self, tid, pages, body="a real transcription of the page"):
        d = self.store.ticket_dir(tid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "out.md").write_text("".join(f"<!-- page: {n} (vision) -->\n{body} {n}\n" for n in pages), encoding="utf-8")


class Parsing(unittest.TestCase):
    def test_pages_and_ranges(self):
        self.assertEqual(v.parse_pages("5,6,8-10"), [5, 6, 8, 9, 10])

    def test_bad_input_is_refused(self):
        for bad in ("", "x", "0", "5-3"):
            with self.assertRaises(v.Refused):
                v.parse_pages(bad)


class Plan(Env):
    def test_a_good_plan_has_an_estimate_and_is_not_approved(self):
        rid, r = v.plan(self.store, CAPS, self.manifest, "scan", [5, 6, 7], DAY)
        self.assertEqual(r["status"], "planned")
        self.assertEqual(r["estimated_tokens"], 3000)

    def test_only_ocr_documents_can_be_read_from_images(self):
        with self.assertRaises(v.Refused):
            v.plan(self.store, CAPS, self.manifest, "plain", [1], DAY)

    def test_the_document_must_match_exactly_one(self):
        self.manifest["scan2.pdf"] = dict(MANIFEST["scan.pdf"])
        with self.assertRaises(v.Refused):
            v.plan(self.store, CAPS, self.manifest, "scan", [1], DAY)

    def test_pages_that_were_not_ocrd_are_refused(self):
        with self.assertRaises(v.Refused):
            v.plan(self.store, CAPS, self.manifest, "scan", [99], DAY)

    def test_the_per_request_cap(self):
        with self.assertRaises(v.Refused) as cm:
            v.plan(self.store, CAPS, self.manifest, "scan", [1, 2, 3, 4, 5, 6], DAY)
        self.assertIn("per request", str(cm.exception))

    def test_only_one_request_open_at_a_time(self):
        self.planned()
        with self.assertRaises(v.Refused):
            self.planned((1,))

    def test_pages_already_read_are_refused(self):
        self.manifest["scan.pdf"]["vision_pages"] = [5]
        with self.assertRaises(v.Refused):
            self.planned((5, 6))

    def test_the_daily_cap_is_checked_at_plan_time(self):
        self.store.save_ledger({DAY: 5})
        with self.assertRaises(v.Refused) as cm:
            self.planned((1, 2))
        self.assertIn("today", str(cm.exception))


class Approval(Env):
    def test_no_ticket_before_approval(self):
        rid = self.planned()
        with self.assertRaises(v.Refused) as cm:
            self.ticket(rid)
        self.assertIn("approved", str(cm.exception))
        self.assertFalse((self.store.root / "tickets").exists())  # nothing was rendered

    def test_approval_changes_the_status(self):
        rid = self.approved()
        self.assertEqual(self.store.requests()[rid]["status"], "approved")

    def test_a_request_cannot_be_approved_twice(self):
        rid = self.approved()
        with self.assertRaises(v.Refused):
            v.approve(self.store, rid, "now")


class Tickets(Env):
    def test_a_ticket_is_limited_to_the_per_ticket_cap(self):
        rid = self.approved((5, 6, 7))
        tid, batch, images, out, left = self.ticket(rid)
        self.assertEqual(batch, [5, 6])
        self.assertEqual(left, 1)
        self.assertEqual(len(images), 2)

    def test_only_the_ticket_pages_are_rendered(self):
        rid = self.approved((5, 6, 7))
        tid, *_ = self.ticket(rid)
        names = sorted(p.name for p in self.store.ticket_dir(tid).iterdir())
        self.assertEqual(names, ["p5.png", "p6.png"])

    def test_tickets_are_one_at_a_time(self):
        rid = self.approved((5, 6, 7))
        self.ticket(rid)
        with self.assertRaises(v.Refused) as cm:
            self.ticket(rid)
        self.assertIn("one at a time", str(cm.exception))

    def test_pages_are_counted_when_the_ticket_is_issued(self):
        rid = self.approved((5, 6, 7))
        self.ticket(rid)
        self.assertEqual(v.spent_today(self.store.ledger(), DAY), 2)

    def test_the_daily_cap_stops_a_ticket(self):
        rid = self.approved((5, 6, 7))
        self.store.save_ledger({DAY: 5})
        with self.assertRaises(v.Refused) as cm:
            self.ticket(rid)
        self.assertIn("today", str(cm.exception))

    def test_a_pending_ticket_blocks_even_a_new_request(self):
        rid = self.approved((5, 6))
        tid, *_ = self.ticket(rid)
        self.assertEqual(v.open_ticket(self.store.requests()), tid)

    def test_abandoning_frees_the_slot_but_keeps_the_pages_counted(self):
        rid = self.approved((5, 6, 7))
        tid, *_ = self.ticket(rid)
        v.abandon(self.store, tid)
        self.assertEqual(v.spent_today(self.store.ledger(), DAY), 2)
        self.assertIsNone(v.open_ticket(self.store.requests()))
        self.assertFalse(self.store.ticket_dir(tid).exists())


class Record(Env):
    def record(self, tid):
        return v.record(self.store, tid, self.manifest, lambda doc: self.note)

    def test_record_merges_only_the_ticket_pages_and_marks_them_vision(self):
        rid = self.approved((5, 6))
        tid, *_ = self.ticket(rid)
        self.write_out(tid, [5, 6])
        self.record(tid)
        text = self.note.read_text(encoding="utf-8")
        self.assertIn("<!-- page: 5 (vision) -->\n\na real transcription of the page 5", text)
        self.assertIn("<!-- page: 6 (vision) -->", text)
        self.assertIn("<!-- page: 7 (ocr) -->\n\nocr text of page 7", text)  # untouched
        self.assertIn("written", text)  # the note's own sections survive
        self.assertEqual(self.manifest["scan.pdf"]["vision_pages"], [5, 6])

    def test_a_transcription_that_misses_a_page_merges_nothing(self):
        rid = self.approved((5, 6))
        tid, *_ = self.ticket(rid)
        self.write_out(tid, [5])
        before = self.note.read_text(encoding="utf-8")
        with self.assertRaises(v.Refused):
            self.record(tid)
        self.assertEqual(self.note.read_text(encoding="utf-8"), before)

    def test_a_transcription_with_an_extra_page_merges_nothing(self):
        rid = self.approved((5, 6))
        tid, *_ = self.ticket(rid)
        self.write_out(tid, [5, 6, 7])
        with self.assertRaises(v.Refused):
            self.record(tid)

    def test_an_empty_transcription_is_refused(self):
        rid = self.approved((5, 6))
        tid, *_ = self.ticket(rid)
        self.write_out(tid, [5, 6], body="x")
        with self.assertRaises(v.Refused):
            self.record(tid)

    def test_no_output_file_is_refused(self):
        rid = self.approved((5, 6))
        tid, *_ = self.ticket(rid)
        with self.assertRaises(v.Refused):
            self.record(tid)

    def test_the_request_closes_when_all_its_pages_are_read(self):
        rid = self.approved((5, 6))
        tid, *_ = self.ticket(rid)
        self.write_out(tid, [5, 6])
        _rid, status, _pages = self.record(tid)
        self.assertEqual(status, "closed")
        self.assertIsNone(v.active_request(self.store.requests()))

    def test_the_images_are_deleted_after_recording(self):
        rid = self.approved((5, 6))
        tid, *_ = self.ticket(rid)
        self.write_out(tid, [5, 6])
        self.record(tid)
        self.assertFalse(self.store.ticket_dir(tid).exists())

    def test_a_second_ticket_can_follow_the_first(self):
        rid = self.approved((5, 6, 7))
        t1, *_ = self.ticket(rid)
        self.write_out(t1, [5, 6])
        self.record(t1)
        t2, batch, *_ = self.ticket(rid)
        self.assertEqual(batch, [7])


class Caps(unittest.TestCase):
    def test_defaults_when_the_file_is_missing(self):
        self.assertEqual(v.load_caps(Path("no-such-file.md")), v.DEFAULT_CAPS)

    def test_values_come_from_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "b.md"
            p.write_text("- `pages_per_ticket` = 2 — x\n- `pages_per_day` = 10 — y\n", encoding="utf-8")
            caps = v.load_caps(p)
            self.assertEqual(caps["pages_per_ticket"], 2)
            self.assertEqual(caps["pages_per_day"], 10)
            self.assertEqual(caps["pages_per_request"], v.DEFAULT_CAPS["pages_per_request"])

    def test_the_shipped_caps_file_parses_to_sane_limits(self):
        caps = v.load_caps()
        self.assertTrue(0 < caps["pages_per_ticket"] <= caps["pages_per_request"] <= caps["pages_per_day"])


if __name__ == "__main__":
    unittest.main()
