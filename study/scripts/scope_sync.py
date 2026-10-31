#!/usr/bin/env python3
"""
Keeps study/ai_instructions/scope.md in step with the accepted definition article.

The pipeline: intake -> definition article -> the user accepts it (the `definition` gate) ->
scope.md is written from it -> papers are gathered. scope.md is a short distillation that
Claude writes, not a generated file, so the link is a header on its first line:

    <!-- derived-from: definition v1.2 problem=ab12cd34 goal=... scope=... constraints=... -->

It names the definition version and a short hash of each section scope.md is drawn from.
This script compares that header with the definition on disk, so a change to the definition
after the gate shows up as "scope.md is stale" and names the sections, without anyone
re-reading both files.

Updating scope.md is deliberately not automatic and not done per change: after one or two
refinements, wait until the user says they are ready, then update scope.md and run `stamp`.
Until then the check only warns.

Usage (from study/):
    python scripts/scope_sync.py check    # what is the state, exit 1 if scope.md is stale
    python scripts/scope_sync.py stamp    # after updating scope.md: record what it was derived from
"""

import hashlib
import re
import sys
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import article_version  # noqa: E402
import gate  # noqa: E402
from build_bibliography import ARTICLES_DIR  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
SCOPE_PATH = REPO_ROOT / "ai_instructions" / "scope.md"
DEFINITION_DIR = ARTICLES_DIR / "definition"
SCOPE_SECTIONS = ("problem", "goal", "scope", "constraints")  # the sections scope.md is drawn from
PLACEHOLDER = "<!-- placeholder -->"
HEADER_RE = re.compile(r"^<!-- derived-from: definition v(\S+)((?: \w+=[0-9a-f]{8})*) -->\s*$")
PAIR_RE = re.compile(r"(\w+)=([0-9a-f]{8})")


def section_hashes(definition_dir=DEFINITION_DIR):
    """{section: 8-hex hash of its text} for the sections scope.md is drawn from."""
    out = {}
    for name in SCOPE_SECTIONS:
        path = definition_dir / "sections" / f"{name}.tex"
        if path.exists():
            text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
            out[name] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return out


def read_header(scope_text):
    """(version, {section: hash}) from scope.md's first line, or None."""
    first = scope_text.splitlines()[0] if scope_text.strip() else ""
    m = HEADER_RE.match(first)
    return (m.group(1), dict(PAIR_RE.findall(m.group(2)))) if m else None


def header_line(version, hashes):
    pairs = "".join(f" {k}={v}" for k, v in hashes.items())
    return f"<!-- derived-from: definition v{version}{pairs} -->"


def accepted_version(definition_dir=DEFINITION_DIR):
    """The version the `definition` gate accepted, or None. The gate record is the source of
    truth (gate.py close writes it together with the article's `accepted` row)."""
    record = gate.load_record("definition", definition_dir.parent / "gates")
    return record.get("accepted_version") if record and record.get("outcome") == "passed" else None


def pipeline_present(definition_dir=DEFINITION_DIR):
    """Whether the repo has the intake pipeline: a definition article, or at least its template
    (the article is created when the work reaches it, so it may not exist yet)."""
    return definition_dir.exists() or (definition_dir.parent / "_templates" / "definition").exists()


def state(scope_path=SCOPE_PATH, definition_dir=DEFINITION_DIR):
    """(code, message). Codes: no-pipeline, waiting, ready, fallback, unstamped, stale, ok."""
    if not pipeline_present(definition_dir):
        return "no-pipeline", "no definition article: scope.md is written the original way"
    rows = article_version.load(definition_dir)["rows"] if definition_dir.exists() else []
    accepted = accepted_version(definition_dir)
    scope = scope_path.read_text(encoding="utf-8") if scope_path.exists() else ""
    if PLACEHOLDER in scope[:200] or not scope.strip():
        if accepted:
            return "ready", f"the definition is accepted (v{accepted}): scope.md can be written from it"
        return "waiting", ("the `definition` gate has not passed"
                           + (" (it has not been started)" if not definition_dir.exists() else "")
                           + ": scope.md comes after that gate, and no papers should be gathered or "
                           "converted before it. Start with /intake, then /definition")
    header = read_header(scope)
    if not accepted:
        return "fallback", ("scope.md was written without an accepted definition (the original route); "
                            "the intake pipeline is the recommended one")
    latest = rows[-1]["version"]
    if header is None:
        return "unstamped", ("scope.md is not derived from the accepted definition: update it from "
                             f"definition v{latest}, then run `python scripts/scope_sync.py stamp`")
    version, hashes = header
    current = section_hashes(definition_dir)
    changed = [k for k in current if hashes.get(k) != current[k]]
    if changed:
        return "stale", (f"scope.md is stale: the definition changed since v{version} "
                         f"({', '.join(changed)}). Update scope.md when you are ready, then run "
                         "`python scripts/scope_sync.py stamp`")
    return "ok", f"scope.md matches definition v{version}"


def convert_warning(definition_dir=DEFINITION_DIR):
    """A warning for convert.py when the intake pipeline is present and the definition is not
    accepted, else None. A warning only: the engine must stay usable on its own."""
    if not pipeline_present(definition_dir):
        return None
    if accepted_version(definition_dir):
        return None
    return ("the `definition` gate has not passed. scope.md should come "
            "from it, and papers should wait. Converting anyway.")


def stamp(scope_path=SCOPE_PATH, definition_dir=DEFINITION_DIR):
    """Write the derived-from header into scope.md. Returns (ok, message)."""
    rows = article_version.load(definition_dir)["rows"] if definition_dir.exists() else []
    if not accepted_version(definition_dir):
        return False, "the `definition` gate has not passed; scope.md is written only after it"
    scope = scope_path.read_text(encoding="utf-8") if scope_path.exists() else ""
    if PLACEHOLDER in scope[:200] or not scope.strip():
        return False, "scope.md is still the placeholder: write it from the definition first"
    body = scope.split("\n", 1)[1] if read_header(scope) else scope
    line = header_line(rows[-1]["version"], section_hashes(definition_dir))
    scope_path.write_text(line + "\n" + body.lstrip("\n"), encoding="utf-8")
    return True, f"scope.md stamped: derived from definition v{rows[-1]['version']}"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else "check"
    if command == "stamp":
        ok, message = stamp()
        print(message, file=sys.stderr if not ok else sys.stdout)
        return 0 if ok else 1
    code, message = state()
    print(message)
    return 1 if code == "stale" else 0


if __name__ == "__main__":
    sys.exit(main())
