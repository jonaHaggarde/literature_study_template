#!/usr/bin/env python3
"""
One snapshot of where the study stands, from the files, with no model involved.

`collect()` gathers what the other scripts already know (the gates, the intake coverage, whether
`scope.md` follows the definition, the catalog and its method families, each article's version
and open markers) into one dictionary. The views are drawn from it, so they cannot disagree:
`status_svg.py` draws the picture that `/where` shows in chat, and `render_markdown` writes the
same facts as text with a mermaid diagram, for a terminal or for GitHub.

Usage (from the repo root or study/):
    python scripts/status.py            # the snapshot as JSON
    python scripts/status.py --md       # the snapshot as markdown, to the terminal
    python scripts/status.py --write    # STATUS.svg and STATUS.md at the repo root (git-ignored)
"""

import json
import sys
from datetime import date
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import article_version  # noqa: E402
import build_article_parts  # noqa: E402
import gate  # noqa: E402
import intake_check  # noqa: E402
import scope_sync  # noqa: E402
from build_bibliography import ARTICLES_DIR, article_dirs  # noqa: E402

REPO_ROOT = ARTICLES_DIR.parent
SVG_PATH = REPO_ROOT / "STATUS.svg"
MD_PATH = REPO_ROOT / "STATUS.md"

STATE_WORDS = {"passed": "passed", "skipped": "skipped", "open": "open",
               "ready": "ready to open", "not-reached": "not reached"}


# ---- the facts -------------------------------------------------------------------------------

def gate_rows(articles_dir, gates_dir):
    """One row per gate, in order: id, title, weight, state, and a short detail."""
    rows = []
    for defn in gate.definitions(gates_dir):
        st = gate.state(defn["id"], articles_dir, gates_dir)
        record = gate.load_record(defn["id"], gates_dir) or {}
        detail = ""
        if st == "passed":
            detail = f"v{record.get('accepted_version')}, {record.get('closed', '')[:10]}"
        elif st == "open":
            detail = f"since {record.get('opened', '')[:10]}"
        elif st == "skipped":
            detail = record.get("reason", "")
        rows.append({"id": defn["id"], "title": defn["title"], "weight": defn["weight"], "state": st,
                     "detail": detail, "skippable": bool(defn.get("skippable"))})
    adhoc = gate.load_record(gate.ADHOC, gates_dir)
    return rows, (adhoc["opened"][:10] if adhoc else None)


def next_step(rows, articles_dir, gates_dir):
    """The first gate that has neither passed nor been skipped, and what to do about it."""
    done = ("passed", "skipped")
    pending = next((r for r in rows if r["state"] not in done), None)
    unlocked = [gate.definition(r["id"], gates_dir).get("unlocks", "") for r in rows if r["state"] == "passed"]
    hint = unlocked[-1] if unlocked else ""
    if pending is None:
        return {"gate": None, "state": "done", "text": "Every gate has passed or been skipped.", "hint": ""}
    gid, title = pending["id"], pending["title"]
    if pending["state"] == "ready":
        text = f"The {title} gate is ready: run /gate {gid} to open it and get the briefing."
    elif pending["state"] == "open":
        text = f"The {title} gate is open: read its article, then tell Claude to close it (/gate {gid})."
    else:
        defn = gate.definition(gid, gates_dir)
        folders = gate.article_folders(defn, articles_dir)
        problems = gate.entry_problems(defn, folders[0] if folders else None, gates_dir)
        if not folders and defn.get("start"):
            text = f"The {title} gate is not ready yet. {defn['start']}"
        else:
            text = f"The {title} gate is not ready: {problems[0] if problems else 'an earlier gate is still open'}."
    return {"gate": gid, "state": pending["state"], "text": text, "hint": hint}


def intake_facts(intake_path):
    rows = intake_check.parse_intake(intake_path.read_text(encoding="utf-8")) if intake_path.exists() else []
    table, missing = intake_check.coverage(rows)
    return {"rows": len(rows), "coverage": {k: list(v) for k, v in table.items()}, "missing": missing}


def article_facts(articles_dir):
    out = []
    for adir in article_dirs(articles_dir):
        history = article_version.load(adir)["rows"]
        todos, issues = gate.count_markers(adir)
        out.append({"name": adir.name, "version": history[-1]["version"] if history else "-",
                    "status": article_version.status_text(history) if history else "no versions yet",
                    "todos": todos, "open_issues": issues})
    return out


def collect(articles_dir=ARTICLES_DIR, gates_dir=None, intake_path=intake_check.INTAKE_PATH,
            processed=None, cards=None, today=None):
    """The snapshot. `processed` (catalog entries) and `cards` ((entry, family) pairs) are read
    from the study when not given."""
    gates_dir = gates_dir or articles_dir / "gates"
    rows, adhoc = gate_rows(articles_dir, gates_dir)
    processed = gate.catalog_count() if processed is None else processed
    cards = build_article_parts.map_cards() if cards is None else cards
    families = build_article_parts.coverage_counts(cards)
    code, message = scope_sync.state()
    return {
        "date": (today or date.today()).isoformat(),
        "gates": rows,
        "adhoc_open_since": adhoc,
        "next": next_step(rows, articles_dir, gates_dir),
        "intake": intake_facts(intake_path),
        "scope": {"code": code, "message": message},
        "catalog": {"processed": processed, "nudge": gate.nudge(processed, gates_dir)},
        "families": [{"name": name or "(no family)", "sources": n, "cards": c}
                     for name, (n, c) in sorted(families.items(), key=lambda kv: (kv[0] == "", kv[0]))],
        "articles": article_facts(articles_dir),
    }


# ---- the text view ---------------------------------------------------------------------------

def render_markdown(data):
    """The same facts as markdown: a mermaid diagram of the gates, then the numbers as tables."""
    lines = ["# Where the study stands", "",
             f"Generated {data['date']} by `study/scripts/status.py`. Do not edit.", "",
             "## Gates", "",
             "Which gates have passed, which one is next, and what comes after it:", "",
             "```mermaid", "flowchart LR"]
    ids = [g["id"] for g in data["gates"]]
    for g in data["gates"]:
        label = f"{g['title']}<br/>{STATE_WORDS[g['state']]}"
        lines.append(f'  {g["id"]}["{label}"]:::{g["state"].replace("-", "")}')
    lines += [f"  {a} --> {b}" for a, b in zip(ids, ids[1:])]
    lines += ["  classDef passed fill:#c8e6c9,stroke:#2e7d32",
              "  classDef open fill:#ffe0b2,stroke:#ef6c00",
              "  classDef ready fill:#bbdefb,stroke:#1565c0",
              "  classDef notreached fill:#eeeeee,stroke:#9e9e9e",
              "  classDef skipped fill:#eeeeee,stroke:#9e9e9e,stroke-dasharray:4",
              "```", ""]
    lines += ["| Gate | Weight | State | Detail |", "|---|---|---|---|"]
    lines += [f"| {g['title']} | {g['weight']} | {STATE_WORDS[g['state']]} | {g['detail']} |" for g in data["gates"]]
    if data["adhoc_open_since"]:
        lines.append(f"\nAn ad hoc stop-and-look has been open since {data['adhoc_open_since']}.")
    lines += ["", f"**Next:** {data['next']['text']}"]
    if data["next"]["hint"]:
        lines.append(f"\nThe last gate unlocked: {data['next']['hint']}.")
    cov = data["intake"]
    lines += ["", "## Intake", "", f"{cov['rows']} intake row(s). Rows answering each definition section, "
              "and rows left unknown:", "", "| Section | Answered | Unknown |", "|---|---|---|"]
    lines += [f"| {k} | {v[0]} | {v[1]} |" for k, v in cov["coverage"].items()]
    lines += ["", f"`scope.md`: {data['scope']['message']}.", "", "## Catalog", "",
              f"{data['catalog']['processed']} processed entr{'y' if data['catalog']['processed'] == 1 else 'ies'}."]
    if data["catalog"]["nudge"]:
        lines.append(f"\n{data['catalog']['nudge']}.")
    if data["families"]:
        lines += ["", "| Method family | Sources | Cards |", "|---|---|---|"]
        lines += [f"| {f['name']} | {f['sources']} | {f['cards']} |" for f in data["families"]]
    lines += ["", "## Articles", ""]
    if data["articles"]:
        lines += ["| Article | Version | Status | `\\todo` | `\\openissue` |", "|---|---|---|---|---|"]
        lines += [f"| {a['name']} | {a['version']} | {a['status']} | {a['todos']} | {a['open_issues']} |"
                  for a in data["articles"]]
    else:
        lines.append("No articles yet.")
    return "\n".join(lines) + "\n"


# ---- command line ----------------------------------------------------------------------------

def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    data = collect()
    if "--write" in args:
        import status_svg
        SVG_PATH.write_text(status_svg.render(data), encoding="utf-8")
        MD_PATH.write_text(render_markdown(data), encoding="utf-8")
        print(f"Wrote {SVG_PATH.name} and {MD_PATH.name} at the repo root.")
    elif "--md" in args:
        print(render_markdown(data), end="")
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
