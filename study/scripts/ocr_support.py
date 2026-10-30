#!/usr/bin/env python3
"""
OCR support for scanned PDFs: find the tools, run OCR on a *copy*, and say
which pages are likely to contain equations or tables that OCR gets wrong.

Never modifies a PDF in PDFs/ (its hash must stay stable), and never installs
anything: when a tool is missing it returns the commands for the user to run.

Imported by convert.py and vision_pages.py; not run directly. `python
scripts/ocr_support.py` prints the tool status.
"""

import importlib.util
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

DEFAULT_LANG = "eng"
OCR_TIMEOUT = 1800  # seconds for one document; a long scan takes minutes
LOW_PAGE_CHARS = 40  # a page with fewer extracted characters than this is treated as a scan

# A page with this many '=' or a high share of symbols OCR confuses is likely
# to carry equations. Measured on one scanned paper: prose pages had 0 to 1 '=',
# equation pages 64 to 73. Crude, and tuned on a single document.
EQUALS_THRESHOLD = 10
ODD_SYMBOL_RATIO = 0.01
ODD_SYMBOLS = re.compile(r"[@\u00a2~\u00ab\u00bb\\^_{}|]")

SKIPPED_MARKER = "[skipped page]"


# ---- finding the tools -------------------------------------------------------------------

def candidate_dirs():
    """Directories where the OCR tools are usually installed but often not on PATH."""
    dirs = []
    if platform.system() == "Windows":
        for base in filter(None, (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                                  os.environ.get("LOCALAPPDATA"))):
            b = Path(base)
            dirs += [b / "Tesseract-OCR", b / "Programs" / "Tesseract-OCR"]
            gs = b / "gs"
            if gs.exists():
                dirs += sorted(gs.glob("gs*/bin"), reverse=True)
    else:
        dirs += [Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path("/usr/bin")]
    return [d for d in dirs if d.exists()]


def find_tool(names, search_dirs=None):
    """Path of the first of `names` found on PATH, then in the usual install
    directories; None if absent."""
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    for d in (search_dirs if search_dirs is not None else candidate_dirs()):
        for n in names:
            for suffix in ("", ".exe"):
                p = Path(d) / (n + suffix)
                if p.is_file():
                    return str(p)
    return None


def status(search_dirs=None):
    tesseract = find_tool(["tesseract"], search_dirs)
    languages = []
    if tesseract:
        try:
            out = subprocess.run([tesseract, "--list-langs"], capture_output=True, text=True, timeout=30).stdout
            languages = [ln.strip() for ln in out.splitlines()[1:] if ln.strip()]
        except (OSError, subprocess.TimeoutExpired):
            pass
    return {
        "ocrmypdf": importlib.util.find_spec("ocrmypdf") is not None,
        "tesseract": tesseract,
        "ghostscript": find_tool(["gswin64c", "gs"], search_dirs),
        "languages": languages,
    }


def ready(st):
    """OCR can run: the Python package and the Tesseract binary are both present.
    Ghostscript is recommended, not required."""
    return bool(st["ocrmypdf"] and st["tesseract"])


def install_hints(st, system=None):
    """Commands the user can run for whatever is missing. Nothing is run for them."""
    system = system or platform.system()
    hints = []
    if not st["ocrmypdf"]:
        hints.append("pip install ocrmypdf")
    if system == "Windows":
        if not st["tesseract"]:
            hints.append("winget install UB-Mannheim.TesseractOCR   (then add C:\\Program Files\\Tesseract-OCR to PATH, "
                         "or leave it: the scripts also look there)")
        if not st["ghostscript"]:
            hints.append("winget install ArtifexSoftware.GhostScript   (recommended)")
    elif system == "Darwin":
        if not st["tesseract"] or not st["ghostscript"]:
            hints.append("brew install tesseract ghostscript")
    else:
        if not st["tesseract"] or not st["ghostscript"]:
            hints.append("sudo apt install tesseract-ocr ghostscript   (or your distribution's equivalent)")
    return hints


def tool_env(st):
    """Environment for a subprocess, with the found tools' directories on PATH."""
    env = dict(os.environ)
    extra = [str(Path(p).parent) for p in (st["tesseract"], st["ghostscript"]) if p]
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


# ---- running OCR -------------------------------------------------------------------------

def run_ocr(pdf_path, lang=DEFAULT_LANG, timeout=OCR_TIMEOUT, st=None):
    """OCR a PDF into per-page text without writing a PDF. Returns (pages, error):
    pages is a list with one string per page, or None for a page ocrmypdf skipped
    because it already had text; error is a string or None."""
    st = st or status()
    if not ready(st):
        return None, "OCR tools are not available"
    if st["languages"] and lang.split("+")[0] not in st["languages"]:
        return None, f"Tesseract has no '{lang}' language data (installed: {', '.join(st['languages'])})"
    with tempfile.TemporaryDirectory() as tmp:
        sidecar = Path(tmp) / "sidecar.txt"
        cmd = [sys.executable, "-m", "ocrmypdf", "--skip-text", "--output-type", "none",
               "--sidecar", str(sidecar), "-l", lang, str(pdf_path), "-"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=tool_env(st))
        except subprocess.TimeoutExpired:
            return None, f"OCR timed out after {timeout:.0f}s"
        if proc.returncode != 0 or not sidecar.exists():
            tail = (proc.stderr or "").strip().splitlines()[-1:] or ["unknown error"]
            return None, f"OCR failed: {tail[0]}"
        text = sidecar.read_text(encoding="utf-8", errors="replace")
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return [None if p.strip() == SKIPPED_MARKER else p for p in pages], None


# ---- using the result --------------------------------------------------------------------

def suspect_pages(pages):
    """1-based numbers of pages whose OCR text probably contains equations or
    tables that OCR garbles (so a model should read those page images if they matter)."""
    out = []
    for i, p in enumerate(pages, 1):
        if not p:
            continue
        letters = len(re.findall(r"[A-Za-z]", p))
        odd = len(ODD_SYMBOLS.findall(p))
        if p.count("=") >= EQUALS_THRESHOLD or (letters and odd / letters >= ODD_SYMBOL_RATIO):
            out.append(i)
    return out


def merge_pages(original_texts, ocr_pages, low_chars=LOW_PAGE_CHARS):
    """Take OCR text for pages whose own extraction was empty or tiny, keep the
    original elsewhere. Returns (texts, ocr_page_numbers)."""
    merged, used = [], []
    for i, orig in enumerate(original_texts):
        ocr = ocr_pages[i] if i < len(ocr_pages) else None
        if len((orig or "").strip()) < low_chars and ocr and ocr.strip():
            merged.append(ocr.strip())
            used.append(i + 1)
        else:
            merged.append(orig)
    return merged, used


OCR_NOTICE = (
    "<!-- OCR: pages marked (ocr) below were read by optical character recognition. Prose is "
    "usually reliable; equations, symbols, tables and figures are NOT (symbols come out as "
    "look-alike characters, formulas lose their structure). Pages likely to contain such "
    "content: {suspect}. Do not treat a value that rests on an (ocr) equation or table as "
    "read: either have the page read from its image (see ai_instructions/vision-budget.md) "
    "or mark it unread. -->"
)


def notice(suspect):
    return OCR_NOTICE.format(suspect=", ".join(str(n) for n in suspect) if suspect else "none detected")


if __name__ == "__main__":
    st = status()
    print(f"ocrmypdf (Python package): {'yes' if st['ocrmypdf'] else 'no'}")
    print(f"tesseract: {st['tesseract'] or 'not found'}")
    print(f"ghostscript: {st['ghostscript'] or 'not found (recommended)'}")
    print(f"languages: {', '.join(st['languages']) or 'unknown'}")
    print("OCR ready." if ready(st) else "OCR is NOT ready. To enable it, run yourself:")
    if not ready(st):
        for h in install_hints(st):
            print(f"  {h}")
    sys.exit(0 if ready(st) else 1)
