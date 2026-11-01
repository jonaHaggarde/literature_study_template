"""Tests for status.py and status_svg.py: the status snapshot and the views drawn from it.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import shutil
import sys
import tempfile
import unittest
import xml.dom.minidom
from datetime import date
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build_bibliography as bib  # noqa: E402
import gate  # noqa: E402
import new_article as na  # noqa: E402
import scope_sync  # noqa: E402
import status  # noqa: E402
import status_svg  # noqa: E402

TODAY = date(2026, 11, 1)
INTAKE = """| ID | Section | Kind | Statement | Source |
|---|---|---|---|---|
| I-1 | goal | goal | Cut lap time | interview 2026-11-01 |
| I-2 | scope | unknown | Exclusions | interview 2026-11-01 |
"""


def workspace(tmp):
    root = Path(tmp) / "articles"
    root.mkdir()
    for name in ("_templates", "common"):
        shutil.copytree(bib.ARTICLES_DIR / name, root / name)
    (root / "gates").mkdir()
    shutil.copy(bib.ARTICLES_DIR / "gates" / "definitions.json", root / "gates" / "definitions.json")
    intake = Path(tmp) / "intake.md"
    intake.write_text(INTAKE, encoding="utf-8")
    return root, intake


def collect(root, intake, **kwargs):
    with mock.patch.object(scope_sync, "state", lambda: ("waiting", "the definition gate has not passed")):
        return status.collect(root, intake_path=intake, processed=kwargs.get("processed", 0),
                              cards=kwargs.get("cards", []), today=TODAY)


class Snapshot(unittest.TestCase):
    def test_a_fresh_study_points_to_the_intake(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, intake = workspace(tmp)
            data = collect(root, intake)
            self.assertEqual([g["state"] for g in data["gates"]], ["not-reached"] * 6)
            self.assertEqual(data["next"]["gate"], "definition")
            self.assertIn("/intake", data["next"]["text"])
            self.assertEqual(data["intake"]["rows"], 2)
            self.assertEqual(data["intake"]["coverage"]["scope"], [0, 1])
            self.assertEqual(data["articles"], [])

    def test_a_passed_gate_moves_the_next_step_on_and_unlocks_a_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, intake = workspace(tmp)
            na.instantiate("definition", "", root)
            gate.save_record({"id": "definition", "outcome": "passed", "accepted_version": "1.0",
                              "closed": "2026-11-01 10:00"}, root / "gates")
            data = collect(root, intake)
            states = {g["id"]: g for g in data["gates"]}
            self.assertEqual(states["definition"]["state"], "passed")
            self.assertEqual(states["definition"]["detail"], "v1.0, 2026-11-01")
            self.assertEqual(data["next"]["gate"], "map")
            self.assertIn("scope.md", data["next"]["hint"])
            self.assertEqual([a["name"] for a in data["articles"]], ["definition"])

    def test_an_open_gate_is_the_next_step_and_an_open_adhoc_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, intake = workspace(tmp)
            na.instantiate("definition", "", root)
            gate.save_record({"id": "definition", "opened": "2026-11-01 09:00"}, root / "gates")
            gate.save_record({"id": "adhoc-2026-11-01", "opened": "2026-11-01 09:30"}, root / "gates")
            data = collect(root, intake)
            self.assertEqual(data["next"]["state"], "open")
            self.assertEqual(data["adhoc_open_since"], "2026-11-01")

    def test_families_are_counted_and_unsorted_cards_are_labelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, intake = workspace(tmp)
            data = collect(root, intake, processed=3, cards=[("a", "fam-1"), ("b", "fam-1"), ("c", "")])
            self.assertEqual(data["families"], [{"name": "fam-1", "sources": 2, "cards": 2},
                                                {"name": "(no family)", "sources": 1, "cards": 1}])
            self.assertEqual(data["catalog"]["processed"], 3)


class Views(unittest.TestCase):
    def data(self, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            root, intake = workspace(tmp)
            na.instantiate("definition", "", root)
            return collect(root, intake, **kwargs)

    def test_the_svg_is_well_formed_and_names_every_gate(self):
        data = self.data(processed=2, cards=[("a", "fam-1")])
        svg = status_svg.render(data)
        xml.dom.minidom.parseString(svg)
        for g in data["gates"]:
            self.assertIn(g["title"], svg)
        self.assertIn("fam-1", svg)

    def test_text_from_the_study_is_escaped_in_the_svg(self):
        data = self.data(cards=[("a", "R&D <x>")])
        data["articles"].append({"name": "a&b", "version": "0.1", "status": "", "todos": 1, "open_issues": 0})
        svg = status_svg.render(data)
        xml.dom.minidom.parseString(svg)
        self.assertIn("R&amp;D &lt;x&gt;", svg)

    def test_more_rows_than_fit_are_summarised_and_the_picture_stays_valid(self):
        data = self.data(cards=[(f"e{i}", f"family-{i}") for i in range(12)])
        data["articles"] = [{"name": f"article-{i}", "version": "0.1", "status": "", "todos": 0, "open_issues": 0}
                            for i in range(11)]
        svg = status_svg.render(data)
        xml.dom.minidom.parseString(svg)
        self.assertIn("+4 more families", svg)
        self.assertIn("+3 more articles", svg)

    def test_the_markdown_has_a_balanced_diagram_and_the_same_facts(self):
        data = self.data(processed=1, cards=[("a", "fam-1")])
        md = status.render_markdown(data)
        self.assertEqual(md.count("```mermaid"), 1)
        self.assertEqual(md.count("```") % 2, 0)
        for g in data["gates"]:
            self.assertIn(f'{g["id"]}["{g["title"]}', md)
        self.assertIn("**Next:**", md)
        self.assertIn("fam-1", md)


if __name__ == "__main__":
    unittest.main()
