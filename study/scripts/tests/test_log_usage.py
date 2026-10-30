"""Tests for .claude/log_usage.py.

Run from study/:  python -m unittest discover -s scripts/tests
"""

import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[3] / ".claude" / "log_usage.py"
_spec = importlib.util.spec_from_file_location("log_usage", _SCRIPT)
lu = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lu)

DAY = date(2026, 10, 30)


class Format(unittest.TestCase):
    def test_dated_one_line_entry(self):
        self.assertEqual(lu.format_entry("a short thing", today=DAY), "- **2026-10-30** — a short thing")

    def test_kind_tag(self):
        self.assertEqual(lu.format_entry("x", "friction", today=DAY), "- **2026-10-30** [friction] — x")

    def test_newlines_become_one_line(self):
        self.assertNotIn("\n", lu.format_entry("one\ntwo\n\nthree", today=DAY))


class Guards(unittest.TestCase):
    def refused(self, text):
        return bool(lu.check_text(text))

    def test_plain_workflow_text_passes(self):
        self.assertFalse(self.refused("asked for a structural rework of the article after reading the first draft"))

    def test_content_looking_text_is_refused(self):
        for bad in (
            "mail jane.doe@example.com about it",
            "see https://example.org/paper",
            r"edited C:\Users\someone\project\notes.md",
            "found it in /home/someone/work/file",
            "key was sk_live_" + "a" * 40,
            "password: hunter2",
            "api key = abc",
        ):
            self.assertTrue(self.refused(bad), bad)

    def test_a_url_is_reported_once_not_also_as_a_path(self):
        problems = lu.check_text("see https://example.org/page")
        self.assertEqual(len(problems), 1)
        self.assertIn("URL", problems[0])

    def test_a_windows_drive_path_is_still_caught(self):
        self.assertTrue(any("path" in p for p in lu.check_text(r"opened C:\work\file.md")))

    def test_too_long_is_refused_with_the_limit_named(self):
        problems = lu.check_text("x " * 300)
        self.assertTrue(any("limit" in p for p in problems))

    def test_empty_is_refused(self):
        self.assertTrue(self.refused("   "))


class Append(unittest.TestCase):
    def test_creates_the_file_with_header_then_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage-log.md"
            lu.append_entry("first", path=path, today=DAY)
            lu.append_entry("second", "bug", path=path, today=DAY)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("# Usage log"))
            self.assertIn("## Entries", text)
            self.assertEqual(lu.entries(path), ["- **2026-10-30** — first", "- **2026-10-30** [bug] — second"])

    def test_refused_entry_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage-log.md"
            lu.append_entry("ok", path=path, today=DAY)
            before = path.read_text(encoding="utf-8")
            with self.assertRaises(ValueError):
                lu.append_entry("see https://example.org", path=path, today=DAY)
            self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_unknown_kind_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                lu.append_entry("x", "nonsense", path=Path(tmp) / "l.md")

    def test_file_without_trailing_newline_is_handled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "usage-log.md"
            path.write_text("# Usage log\n\n## Entries\n\n- **2026-10-29** — old", encoding="utf-8")
            lu.append_entry("new", path=path, today=DAY)
            self.assertEqual(len(lu.entries(path)), 2)


if __name__ == "__main__":
    unittest.main()
