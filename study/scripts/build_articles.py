#!/usr/bin/env python3
"""
Builds every article under articles/ into a PDF placed directly in articles/ (so
the PDFs are easy to find): articles/<name>.pdf for articles/<name>/main.tex.

For each article it first regenerates its derived files (the review's comparison
table, every article's bibliography), then runs LaTeX with all auxiliary files in
articles/.build/<name>/ so the source folders stay clean. If an article has a
references.bib it also runs BibTeX; an article that cites nothing has none and gets
no bibliography. The PDFs and the build folder are build output and are gitignored.

Needs pdflatex (and bibtex, for articles that cite sources) from a LaTeX
distribution such as MiKTeX or TeX Live. If they are missing it says so and still
regenerates the derived files.

Usage (from study/):
    python scripts/build_articles.py                # every article
    python scripts/build_articles.py --only review  # one article
    python scripts/build_articles.py --no-latex     # derived files only
"""

import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_bibliography import ARTICLES_DIR, article_dirs  # noqa: E402
import article_version  # noqa: E402
from ocr_support import find_tool  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
LATEX_TIMEOUT = 300


def latex_dirs():
    """Where a LaTeX distribution is usually installed but not always on PATH."""
    dirs = []
    if platform.system() == "Windows":
        local = os.environ.get("LOCALAPPDATA")
        for base in filter(None, (local and Path(local) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
                                  os.environ.get("ProgramFiles") and
                                  Path(os.environ["ProgramFiles"]) / "MiKTeX" / "miktex" / "bin" / "x64")):
            dirs.append(base)
    else:
        dirs += [Path("/Library/TeX/texbin"), Path("/usr/local/texlive"), Path("/usr/bin")]
    return [d for d in dirs if Path(d).exists()]


def parse_log(log_text):
    """(pages, undefined) from a LaTeX log: the page count of the output and the
    number of undefined citations and references."""
    m = re.search(r"Output written on.*?\((\d+) pages?", log_text, re.S)
    pages = int(m.group(1)) if m else None
    undefined = len(re.findall(r"(?:Citation|Reference) `[^']*' .*?undefined", log_text))
    return pages, undefined


def run(cmd, cwd, timeout=LATEX_TIMEOUT):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=timeout)


def generate_derived(name, scripts=SCRIPTS):
    """Regenerate the files an article's text depends on, before LaTeX."""
    steps = []
    if name == "review":
        steps.append("build_review_table.py")
    if name in ("map", "requirements", "rationale"):
        steps.append(f"build_article_parts.py {name}")
    steps.append("build_bibliography.py")
    article_version.write_table(ARTICLES_DIR / name)
    for step in steps:
        script, *step_args = step.split()
        proc = run([sys.executable, str(scripts / script), *step_args], cwd=scripts.parent, timeout=120)
        if proc.returncode != 0:
            return f"{step} failed: {(proc.stderr or proc.stdout).strip()[-200:]}"
    return None


def build_pdf(adir, pdflatex, bibtex):
    """Build one article. Returns (ok, message)."""
    name = adir.name
    outdir = ARTICLES_DIR / ".build" / name
    outdir.mkdir(parents=True, exist_ok=True)
    base = [pdflatex, "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={outdir}", "main.tex"]
    passes = 3
    first = run(base, adir)
    if first.returncode != 0:
        log = (outdir / "main.log").read_text(encoding="utf-8", errors="replace") if (outdir / "main.log").exists() else ""
        err = next((ln for ln in log.splitlines() if ln.startswith("!")), "see articles/.build/%s/main.log" % name)
        return False, f"LaTeX failed: {err}"
    bib = adir / "references.bib"
    if bib.exists():
        if not bibtex:
            return False, "this article has sources but bibtex was not found"
        shutil.copy(bib, outdir / "references.bib")
        b = run([bibtex, "main"], outdir)
        if b.returncode not in (0, 1):  # 1 = warnings
            return False, f"bibtex failed: {(b.stdout or b.stderr).strip()[-200:]}"
    else:
        passes = 2
    for _ in range(passes - 1):
        again = run(base, adir)
        if again.returncode != 0:
            return False, "LaTeX failed on a later pass"
    pdf = outdir / "main.pdf"
    if not pdf.exists():
        return False, "no PDF was produced"
    shutil.copy(pdf, ARTICLES_DIR / f"{name}.pdf")
    pages, undefined = parse_log((outdir / "main.log").read_text(encoding="utf-8", errors="replace"))
    note = f"{pages} page(s)" if pages else "built"
    if undefined:
        note += f", {undefined} undefined citation/reference warning(s)"
    return True, note


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    no_latex = "--no-latex" in argv
    articles = [a for a in article_dirs() if only in (None, a.name)]
    if not articles:
        print("No articles found." if not only else f"No article named '{only}'.", file=sys.stderr)
        return 1
    pdflatex = find_tool(["pdflatex"], latex_dirs())
    bibtex = find_tool(["bibtex"], latex_dirs())
    if not no_latex and not pdflatex:
        print("pdflatex was not found: install a LaTeX distribution (MiKTeX or TeX Live) to build PDFs. "
              "Derived files are still regenerated.", file=sys.stderr)
        no_latex = True
    failed = 0
    for adir in articles:
        problem = generate_derived(adir.name)
        if problem:
            print(f"{adir.name}: {problem}", file=sys.stderr)
            failed += 1
            continue
        if no_latex:
            print(f"{adir.name}: derived files regenerated (no PDF).")
            continue
        ok, msg = build_pdf(adir, pdflatex, bibtex)
        print(f"{adir.name}: {'articles/' + adir.name + '.pdf, ' if ok else 'FAILED: '}{msg}")
        failed += 0 if ok else 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
