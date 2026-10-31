"""Tests for gate.py: opening, the soft freeze, the understanding-check record, closing and skipping.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import shutil
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import article_version as av  # noqa: E402
import build_bibliography as bib  # noqa: E402
import gate  # noqa: E402
import new_article as na  # noqa: E402


_PATCH = mock.patch.object(gate, "catalog_count", lambda: 0)


def setUpModule():
    _PATCH.start()


def tearDownModule():
    _PATCH.stop()


def workspace(tmp):
    """A temporary articles folder with the templates, the preamble and the real gate definitions."""
    root = Path(tmp) / "articles"
    root.mkdir()
    for name in ("_templates", "common"):
        shutil.copytree(bib.ARTICLES_DIR / name, root / name)
    shutil.copytree(bib.ARTICLES_DIR / "gates", root / "gates")
    for f in (root / "gates").glob("*.json"):
        if f.name != gate.DEFINITIONS:
            f.unlink()
    return root, root / "gates"


def drafted(root, kind, name=""):
    folder, _ = na.instantiate(kind, name, root)
    (folder / "sections" / "abstract.tex").write_text("A drafted abstract.\n", encoding="utf-8") \
        if (folder / "sections" / "abstract.tex").exists() else None
    av.add_row(folder, "draft", "First draft", "Claude", restart=True)
    return folder


def open_args(root, gates):
    return {"articles_dir": root, "gates_dir": gates}


class Definitions(unittest.TestCase):
    def test_every_gate_names_a_template_and_only_earlier_gates(self):
        defs = gate.definitions()
        ids = [d["id"] for d in defs]
        self.assertEqual(len(ids), len(set(ids)))
        templates = na.templates()
        for position, d in enumerate(defs):
            kind = d["article"].rstrip("-")
            self.assertIn(kind, templates)
            for earlier in d["after"]:
                self.assertLess(ids.index(earlier), position)

    def test_definition_and_requirements_have_no_understanding_check(self):
        flags = {d["id"]: d["understand"] for d in gate.definitions()}
        self.assertFalse(flags["definition"])
        self.assertFalse(flags["requirements"])
        self.assertTrue(flags["review"])


class Opening(unittest.TestCase):
    def test_a_missing_article_and_a_skeleton_stop_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            _, error = gate.open_gate("definition", **open_args(root, gates))
            self.assertIn("does not exist", error)
            na.instantiate("definition", "", root)
            _, error = gate.open_gate("definition", **open_args(root, gates))
            self.assertIn("skeleton", error)
            self.assertEqual(gate.state("definition", **open_args(root, gates)), "not-reached")

    def test_an_earlier_gate_that_has_not_passed_stops_a_later_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            drafted(root, "map")
            _, error = gate.open_gate("map", **open_args(root, gates))
            self.assertIn("`definition` gate has not passed", error)

    def test_early_opens_with_the_reason_and_the_problems_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            drafted(root, "map")
            record, error = gate.open_gate("map", early="deadline", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertEqual(record["early"], "deadline")
            self.assertTrue(record["early_problems"])
            self.assertTrue(any("opened early" in line for line in gate.briefing("map", **open_args(root, gates))))

    def test_a_ready_gate_opens_and_cannot_open_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            drafted(root, "definition")
            self.assertEqual(gate.state("definition", **open_args(root, gates)), "ready")
            record, error = gate.open_gate("definition", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertEqual(record["article"], "definition")
            self.assertEqual(gate.state("definition", **open_args(root, gates)), "open")
            _, error = gate.open_gate("definition", **open_args(root, gates))
            self.assertIn("already", error)

    def test_a_family_gate_needs_the_article_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            drafted(root, "specification", "alpha")
            for g in ("definition", "map", "review", "requirements", "concept"):
                gate.save_record({"id": g, "article": None, "outcome": "passed"}, gates)
            _, error = gate.open_gate("split", **open_args(root, gates))
            self.assertIn("--article", error)
            record, error = gate.open_gate("split", article="specification-alpha", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertEqual(record["article"], "specification-alpha")


class FreezeAndClosing(unittest.TestCase):
    def setup_open(self, tmp):
        root, gates = workspace(tmp)
        folder = drafted(root, "definition")
        gate.open_gate("definition", **open_args(root, gates))
        return root, gates, folder

    def test_a_change_while_open_is_reported_until_refrozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates, folder = self.setup_open(tmp)
            self.assertEqual(gate.problems_for_validator(root, gates), [])
            (folder / "sections" / "goal.tex").write_text("changed\n", encoding="utf-8")
            self.assertTrue(any("changed since" in m for m in gate.problems_for_validator(root, gates)))
            gate.refreeze("definition", **open_args(root, gates))
            self.assertEqual(gate.problems_for_validator(root, gates), [])

    def test_close_accepts_the_article_and_records_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates, folder = self.setup_open(tmp)
            record, error, warnings = gate.close_gate("definition", "Accepted", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertEqual(record["outcome"], "passed")
            self.assertEqual(av.accepted_version(av.load(folder)["rows"]), record["accepted_version"])
            self.assertEqual(gate.state("definition", **open_args(root, gates)), "passed")
            self.assertEqual(gate.problems_for_validator(root, gates), [])

    def test_close_refuses_unrecorded_edits_and_a_gate_that_is_not_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates, folder = self.setup_open(tmp)
            (folder / "sections" / "goal.tex").write_text("changed\n", encoding="utf-8")
            _, error, _ = gate.close_gate("definition", "x", **open_args(root, gates))
            self.assertIn("record it first", error)
            _, error, _ = gate.close_gate("map", "x", **open_args(root, gates))
            self.assertIn("not open", error)

    def test_an_acceptance_with_no_gate_record_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            folder = drafted(root, "definition")
            av.add_row(folder, "accept", "raw accept", "User")
            self.assertTrue(any("no record of passing" in m for m in gate.problems_for_validator(root, gates)))


class UnderstandingCheck(unittest.TestCase):
    def test_the_check_is_recorded_and_close_notes_a_missing_or_slower_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            drafted(root, "map")
            gate.save_record({"id": "definition", "article": None, "outcome": "passed"}, gates)
            gate.open_gate("map", **open_args(root, gates))
            record = gate.load_record("map", gates)
            self.assertIsNone(record["check"])
            _, error = gate.note_check("map", "maybe", gates_dir=gates)
            self.assertIn("must be one of", error)
            gate.note_check("map", "slower", gates_dir=gates)
            _, error, warnings = gate.close_gate("map", "x", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertTrue(any("slower" in w for w in warnings))

    def test_a_missing_check_is_noted_not_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            drafted(root, "map")
            gate.save_record({"id": "definition", "article": None, "outcome": "passed"}, gates)
            gate.open_gate("map", **open_args(root, gates))
            record, error, warnings = gate.close_gate("map", "x", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertTrue(any("not done" in w for w in warnings))


class Skipping(unittest.TestCase):
    def test_only_a_skippable_gate_can_be_skipped_and_it_unlocks_the_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            _, error = gate.skip_gate("review", "x", gates_dir=gates)
            self.assertIn("cannot be skipped", error)
            record, error = gate.skip_gate("requirements", "not a build project", gates_dir=gates)
            self.assertIsNone(error)
            self.assertTrue(gate.passed("requirements", gates))
            self.assertEqual(gate.status_lines(root, gates)[3].split()[2], "skipped")


class Amendments(unittest.TestCase):
    def passed_split(self, tmp):
        root, gates = workspace(tmp)
        drafted(root, "specification", "alpha")
        for g in ("definition", "map", "review", "requirements", "concept"):
            gate.save_record({"id": g, "article": None, "outcome": "passed"}, gates)
        gate.open_gate("split", article="specification-alpha", **open_args(root, gates))
        gate.close_gate("split", "first", **open_args(root, gates))
        return root, gates

    def test_a_later_specification_joins_through_an_amendment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = self.passed_split(tmp)
            beta = drafted(root, "specification", "beta")
            part, error = gate.open_gate("split", article="specification-beta", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertEqual(part["article"], "specification-beta")
            self.assertIn("amendment open", gate.status_lines(root, gates)[5])
            part, error, _ = gate.close_gate("split", "second", article="specification-beta", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertEqual(av.accepted_version(av.load(beta)["rows"]), part["accepted_version"])
            self.assertEqual(gate.problems_for_validator(root, gates), [])
            self.assertIn("1 amendment", gate.status_lines(root, gates)[5])

    def test_an_accepted_specification_with_no_amendment_is_reported_and_a_repeat_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = self.passed_split(tmp)
            beta = drafted(root, "specification", "beta")
            av.add_row(beta, "accept", "raw", "User")
            self.assertTrue(any("specification-beta" in m for m in gate.problems_for_validator(root, gates)))
            _, error = gate.open_gate("split", article="specification-alpha", **open_args(root, gates))
            self.assertIn("already part", error)


class AdHocAndNudge(unittest.TestCase):
    def test_an_ad_hoc_gate_opens_checks_and_closes_with_no_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            part, error = gate.open_gate("adhoc", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertTrue(part["id"].startswith("adhoc-"))
            _, error = gate.open_gate("adhoc", **open_args(root, gates))
            self.assertIn("already open", error)
            gate.note_check("adhoc", "ready", gates_dir=gates)
            part, error, warnings = gate.close_gate("adhoc", "paused to look", **open_args(root, gates))
            self.assertIsNone(error)
            self.assertEqual(part["outcome"], "done")
            self.assertEqual(warnings, [])
            self.assertIsNone(gate.load_record("adhoc", gates))
            second, _ = gate.open_gate("adhoc", **open_args(root, gates))
            self.assertNotEqual(second["id"], part["id"])

    def test_the_nudge_counts_entries_since_the_last_closed_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, gates = workspace(tmp)
            self.assertIsNone(gate.nudge(14, gates))
            self.assertIn("15 documents", gate.nudge(15, gates))
            gate.save_record({"id": "definition", "article": "definition", "outcome": "passed",
                              "closed": "2026-01-01 10:00", "catalog_count": 20}, gates)
            self.assertIsNone(gate.nudge(30, gates))
            self.assertIn("16 documents", gate.nudge(36, gates))


if __name__ == "__main__":
    unittest.main()
