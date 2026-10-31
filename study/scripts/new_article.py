#!/usr/bin/env python3
"""
Creates an article from a template in articles/_templates/.

A template is a folder like any article (main.tex, sections/, README.md) with two tokens in
its text: `{{NAME}}` (the folder name given here) and `{{TITLE}}` (the same, with spaces). The
new article gets its own folder under articles/, a generated references file, and its first
version row (0.1, draft), so it is built, validated and version-tracked from the start.

Every article is created this way: the repo ships no articles. A singleton (`definition`,
`map`, `review`, `requirements`, `rationale`) becomes `articles/<kind>/`. A family article, today
only `specification` (one per chosen concept), takes a name and becomes `articles/<kind>-<name>/`.

The new article starts with a skeleton row, version 0.1. The command that writes its first real
draft replaces that row with `article_version.py <folder> draft --restart`, so the first real
draft is 0.1 and not 0.2.

Usage (from study/):
    python scripts/new_article.py --list
    python scripts/new_article.py definition
    python scripts/new_article.py specification concept-a
"""

import re
import shutil
import sys
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import article_version  # noqa: E402
import build_bibliography as bibliography  # noqa: E402

ARTICLES_DIR = bibliography.ARTICLES_DIR
TEMPLATES_DIR = ARTICLES_DIR / "_templates"
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TEXT_SUFFIXES = {".tex", ".md", ".bib", ".json", ".txt"}
FAMILY_KINDS = {"specification"}   # kinds whose folder is `<kind>-<name>`; the others are singletons


def templates(templates_dir=TEMPLATES_DIR):
    """Names of the available templates."""
    if not templates_dir.exists():
        return []
    return sorted(p.name for p in templates_dir.iterdir() if p.is_dir() and (p / "main.tex").exists())


def folder_name(kind, name):
    return f"{kind}-{name}" if kind in FAMILY_KINDS else kind


def instantiate(kind, name, articles_dir=ARTICLES_DIR, today_label="Skeleton from the template"):
    """Create articles_dir/<folder> from the template. Returns (folder_path, warnings) or raises
    ValueError with a plain-language reason."""
    templates_dir = articles_dir / "_templates"
    if kind not in templates(templates_dir):
        have = ", ".join(templates(templates_dir)) or "none"
        raise ValueError(f"no template named '{kind}' (available: {have})")
    if kind in FAMILY_KINDS and not name:
        raise ValueError(f"a {kind} needs a name: new_article.py {kind} <name>")
    if name and not SLUG_RE.match(name):
        raise ValueError("the name must be lowercase letters, digits and single hyphens, e.g. concept-a")
    if kind not in FAMILY_KINDS:
        name = kind   # a singleton has one folder, named after it
    folder = articles_dir / folder_name(kind, name)
    if folder.exists():
        raise ValueError(f"articles/{folder.name} already exists")

    shutil.copytree(templates_dir / kind, folder,
                    ignore=shutil.ignore_patterns("versions.json", "versions.tex", "references.tex",
                                                  "references.bib", ".build"))
    tokens = {"{{NAME}}": name, "{{TITLE}}": name.replace("-", " ")}
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8")
            for token, value in tokens.items():
                text = text.replace(token, value)
            path.write_text(text, encoding="utf-8")

    (folder / "sections").mkdir(exist_ok=True)
    (folder / "sections" / "references.tex").write_text(bibliography.REFS_NONE, encoding="utf-8")
    row, error = article_version.add_row(folder, "draft", today_label, "Claude")
    if error:
        raise ValueError(error)

    warnings = []
    if kind == "specification":
        rationale = articles_dir / "rationale"
        if rationale.exists() and not article_version.accepted_version(article_version.load(rationale)["rows"]):
            warnings.append("the rationale is not accepted yet (the `concept` gate); a specification normally "
                            "follows it")
    return folder, warnings


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--list":
        have = templates()
        print("Templates: " + (", ".join(have) if have else "none"))
        return 0
    kind, name = argv[0], (argv[1] if len(argv) > 1 else "")
    try:
        folder, warnings = instantiate(kind, name)
    except ValueError as err:
        print(f"new_article: {err}", file=sys.stderr)
        return 1
    import build_articles   # regenerates the files an article derives (the review's table, bibliographies)
    problem = build_articles.generate_derived(folder.name)
    if problem:
        warnings.append(f"derived files were not regenerated: {problem}")
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    print(f"Created articles/{folder.name}/ at version 0.1. Next: write it (see its README.md), "
          f"record changes with article_version.py {folder.name} edit, build with "
          f"build_articles.py --only {folder.name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
