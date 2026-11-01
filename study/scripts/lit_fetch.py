#!/usr/bin/env python3
"""
The fetch half of the search-and-select engine (design: study/search-engine-design.md).

Only runs on papers the user approved by number (`lit_search.py approve`), which wrote them to
leads.md as `found`. For each one this tries every open copy OpenAlex listed, one attempt per
location, and keeps a file only if it is a PDF whose first pages carry the expected title (or
DOI). A file that is not the paper, or a landing page saved as a PDF, never reaches PDFs/. The
lead moves to `fetched` (the file is in PDFs/, waiting for convert.py) or `blocked`, with the
reasons. Nothing is reported for the papers that went well beyond a count; only problems are
listed.

Papers with no open copy are fetched by the user with their own access: save the PDFs into
study/searches/inbox/ and run `match`, which reads each file's first pages, finds the lead it
belongs to, files it in PDFs/ under the standard name and marks the lead `user-fetched`.

Usage (from study/):
    python scripts/lit_fetch.py fetch --round 1
    python scripts/lit_fetch.py match [--folder PATH]
"""

import argparse
import re
import shutil
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lit_search as ls  # noqa: E402

PDFS = ls.STUDY / "PDFs"
MIN_BYTES = 10_000          # a real paper is larger; smaller is an error page or a stub
MAX_BYTES = 80_000_000
MATCH = 0.6                 # share of the expected title's words found on the first pages
AMBIGUOUS = 0.15            # a second lead this close to the best one makes a match ambiguous
PAGES = 2


class FetchError(Exception):
    pass


DOWNLOAD = None    # tests replace this: url -> bytes, or raise FetchError
PAGE_TEXT = None   # tests replace this: path -> text of the first pages, or None


def inbox():
    return ls.SEARCHES / "inbox"


def rejected():
    return ls.SEARCHES / "rejected"


# ---- downloading and checking -----------------------------------------------------------------

def _download(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; literature-study-template)",
        "Accept": "application/pdf,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as err:
        raise FetchError(f"HTTP {err.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise FetchError(f"unreachable ({getattr(err, 'reason', err)})")
    if len(data) > MAX_BYTES:
        raise FetchError("file larger than the size limit")
    return data


def get_pdf(url):
    data = (DOWNLOAD or _download)(url)
    if not data.startswith(b"%PDF"):
        raise FetchError("not a PDF (a landing page or a login page)")
    if len(data) < MIN_BYTES:
        raise FetchError("file too small to be a paper")
    return data


def page_text(path):
    """Text of the first pages, or None when it cannot be read (no library, a scan)."""
    if PAGE_TEXT:
        return PAGE_TEXT(path)
    try:
        import pymupdf
        with pymupdf.open(path) as doc:
            return " ".join(doc[i].get_text() for i in range(min(PAGES, len(doc))))
    except Exception:
        return None


def title_score(text, title, doi):
    """1.0 if the DOI is on the pages, else the share of the title's words that are."""
    squeezed = re.sub(r"\s+", "", text.lower())
    if doi and doi.lower().replace(" ", "") in squeezed:
        return 1.0
    wanted = ls.words(title)
    if not wanted:
        return 0.0
    present = set(re.findall(r"[a-z0-9]+", text.lower()))
    return len(wanted & present) / len(wanted)


def check_file(path, title, doi):
    """'ok', 'mismatch' or 'unchecked' (the first pages carry no readable text)."""
    text = page_text(path)
    if text is None or len(text.strip()) < 50:
        return "unchecked"
    return "ok" if title_score(text, title, doi) >= MATCH else "mismatch"


def unique_path(folder, name):
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    n = 2
    while path.exists():
        path = folder / f"{path.stem.rsplit('~', 1)[0]}~{n}{path.suffix}"
        n += 1
    return path


# ---- leads.md ---------------------------------------------------------------------------------

def read_leads():
    """(lines, rows): the file's lines and one dict per table row, with its line index."""
    lines = ls.read_text(ls.LEADS).split("\n")
    rows, in_table = [], False
    for i, line in enumerate(lines):
        if line.startswith("| Lead |"):
            in_table = True
            continue
        if in_table and line.startswith("|") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 6:
                rows.append({"i": i, "cells": cells})
    return lines, rows


def update_lead(row, state, note_add):
    lines, rows = read_leads()
    target = next((r for r in rows if r["i"] == row["i"]), None)
    if target is None:
        return
    cells = target["cells"]
    cells[3] = state
    cells[4] = f"{cells[4]}; {ls.cell(note_add)}" if cells[4] else ls.cell(note_add)
    cells[5] = date.today().isoformat()
    lines[target["i"]] = "| " + " | ".join(cells) + " |"
    ls.write_text(ls.LEADS, "\n".join(lines))


def lead_for(title):
    key = ls.norm_title(ls.cell(title))
    _, rows = read_leads()
    return next((r for r in rows if ls.norm_title(r["cells"][0]) == key), None)


# ---- fetch ------------------------------------------------------------------------------------

def fetch_one(c):
    """Try each open copy once; keep the first that passes. Returns the record to store."""
    tried = []
    name = ls.filename(c)
    if not c["copies"]:
        return {"state": "blocked", "reason": "no open copy listed", "tried": tried}
    for copy in c["copies"]:
        try:
            data = get_pdf(copy["pdf"])
        except FetchError as err:
            tried.append({"url": copy["pdf"], "result": str(err)})
            continue
        staged = unique_path(rejected(), name)
        staged.write_bytes(data)
        verdict = check_file(staged, c["title"], c["doi"])
        if verdict == "mismatch":
            tried.append({"url": copy["pdf"], "result": "first pages do not match the title"})
            continue
        final = unique_path(PDFS, name)
        shutil.move(str(staged), str(final))
        tried.append({"url": copy["pdf"], "result": verdict})
        return {"state": "fetched", "file": f"PDFs/{final.name}", "check": verdict,
                "source": copy["pdf"], "tried": tried}
    reasons = "; ".join(f"{t['result']}" for t in tried)
    return {"state": "blocked", "reason": reasons, "tried": tried}


def fetch_round(rnd):
    done = rnd.setdefault("fetch", {})
    out = []
    for pid in rnd["approved"]:
        if done.get(pid, {}).get("state") in ("fetched", "user-fetched"):
            continue
        c = rnd["candidates"][pid]
        row = lead_for(c["title"])
        result = fetch_one(c)
        done[pid] = result
        if row:
            if result["state"] == "fetched":
                note = f"file {result['file']}" + (" (title not checked: no readable text)"
                                                   if result["check"] == "unchecked" else "")
                update_lead(row, "fetched", note)
            else:
                update_lead(row, "blocked", f"could not fetch: {result['reason']}")
        out.append((pid, c, result))
    return out


# ---- the user's own downloads -----------------------------------------------------------------

def find_candidate(title, doi):
    for n in ls.round_numbers():
        for c in ls.load_round(n)["candidates"].values():
            if (doi and c["doi"] == doi) or ls.norm_title(c["title"]) == ls.norm_title(title):
                return c
    return None


def match_folder(folder):
    """File each PDF in `folder` under the lead it belongs to. Returns (matched, problems)."""
    _, rows = read_leads()
    open_rows = [r for r in rows if r["cells"][3] in ("found", "blocked")]
    matched, problems = [], []
    for pdf in sorted(folder.glob("*.pdf")):
        text = page_text(pdf)
        if text is None or len(text.strip()) < 50:
            problems.append((pdf.name, "no readable text on the first pages; cannot match it"))
            continue
        scored = []
        for r in open_rows:
            doi = (ls.DOI_RE.findall(r["cells"][4]) or [""])[0].rstrip(".,;")
            scored.append((title_score(text, r["cells"][0], ls.norm_doi(doi)), r))
        scored.sort(key=lambda s: -s[0])
        if not scored or scored[0][0] < MATCH:
            problems.append((pdf.name, "no lead matches this file (a paper of your own? move it "
                                       "into PDFs/ yourself)"))
            continue
        if len(scored) > 1 and scored[1][0] >= MATCH and scored[0][0] - scored[1][0] < AMBIGUOUS:
            problems.append((pdf.name, "matches two leads about equally: "
                                       f"\"{scored[0][1]['cells'][0]}\" and \"{scored[1][1]['cells'][0]}\""))
            continue
        row = scored[0][1]
        doi = ls.norm_doi((ls.DOI_RE.findall(row["cells"][4]) or [""])[0].rstrip(".,;"))
        cand = find_candidate(row["cells"][0], doi)
        name = ls.filename(cand) if cand else (
            "-".join(re.findall(r"[a-z0-9]+", row["cells"][0].lower())[:6]) + ".pdf")
        final = unique_path(PDFS, name)
        shutil.move(str(pdf), str(final))
        update_lead(row, "user-fetched", f"file PDFs/{final.name}")
        open_rows.remove(row)
        matched.append((pdf.name, final.name, row["cells"][0]))
    return matched, problems


# ---- command line -----------------------------------------------------------------------------

def report_fetch(results):
    fetched = [r for r in results if r[2]["state"] == "fetched"]
    unchecked = [r for r in fetched if r[2]["check"] == "unchecked"]
    blocked = [r for r in results if r[2]["state"] == "blocked"]
    ok = len(fetched) - len(unchecked)
    print(f"{ok} fetched and matched to their titles.")
    for _, c, res in unchecked:
        print(f"  fetched but not checked (no readable text on its first pages): {c['title'][:70]}"
              f" -> {res['file']}")
    for _, c, res in blocked:
        link = f"https://doi.org/{c['doi']}" if c["doi"] else c["landing"]
        print(f"  blocked: {c['title'][:70]}\n    why: {res['reason']}\n    by hand: {link}"
              f"  save as {ls.filename(c)}")
    if blocked:
        print(f"\nSave the {len(blocked)} blocked paper(s) into {inbox()} and run: "
              "lit_fetch.py match")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch")
    p.add_argument("--round", type=int)
    p = sub.add_parser("match")
    p.add_argument("--folder", type=Path)
    args = ap.parse_args(argv)

    if args.cmd == "fetch":
        rnd = ls.load_round(ls.pick_round(args.round))
        if not rnd["approved"]:
            print("Nothing approved in this round yet: run lit_search.py approve with the "
                  "user's numbers first.")
            return 1
        results = fetch_round(rnd)
        ls.save_round(rnd)
        ls.write_view(rnd)
        if not results:
            print("Everything approved in this round has been fetched already.")
        else:
            report_fetch(results)
    else:
        folder = args.folder or inbox()
        if not folder.is_dir():
            folder.mkdir(parents=True, exist_ok=True)
            print(f"{folder} did not exist and is now created: save the PDFs there, then run "
                  "match again.")
            return 0
        matched, problems = match_folder(folder)
        print(f"{len(matched)} file(s) matched and filed in PDFs/.")
        for src, dst, title in matched:
            print(f"  {src} -> PDFs/{dst}  ({title[:60]})")
        for name, why in problems:
            print(f"  {name}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
