#!/usr/bin/env python3
"""
The budgeted way to read page images of an OCR'd scan: plan, approve, ticket,
record. See ai_instructions/vision-budget.md for why it exists and its limits.

The point of the design is that spending is hard to do by accident:

  plan     names a document and exact pages, checks the per-request cap.
           Does nothing by itself.
  approve  is a human decision. It is not pre-approved in .claude/settings.json,
           so running it asks the user for permission.
  ticket   renders at most `pages_per_ticket` pages of an approved request into a
           folder that exists for that ticket only, records them in the page ledger,
           and refuses to issue another ticket until this one is recorded.
           Also not pre-approved, so every batch is a visible decision.
  record   adds the equations, tables and figures the page-reader found below each
           page's OCR text in the note and marks those pages `(vision)`.

No ticket means no images, so an agent has nothing to read.

Usage (from study/):
    python scripts/vision_pages.py status
    python scripts/vision_pages.py plan DOC --pages 5,6,7
    python scripts/vision_pages.py approve R1
    python scripts/vision_pages.py ticket R1
    python scripts/vision_pages.py record R1-T1 [--tokens N]   # N: usage the harness reported
    python scripts/vision_pages.py cancel R1          # close a request
    python scripts/vision_pages.py abandon R1-T1      # close a stuck ticket (its pages stay counted)
"""

import json
import re
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import _console  # noqa: F401  (UTF-8 console output on Windows)

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / ".ocr"
CAPS_PATH = REPO_ROOT / "ai_instructions" / "vision-budget.md"
MANIFEST_PATH = REPO_ROOT / "manifest.json"
PDFS_DIR = REPO_ROOT / "PDFs"

DEFAULT_CAPS = {
    "pages_per_ticket": 4,
    "pages_per_request": 12,
}
CAP_RE = re.compile(r"^- `([a-z_]+)`\s*=\s*(\d+)", re.MULTILINE)
RENDER_DPI = 110


class Refused(Exception):
    """A rule of the budget was hit. The message says which and what to do."""


# ---- configuration and state ----------------------------------------------------------------

def load_caps(path=CAPS_PATH):
    caps = dict(DEFAULT_CAPS)
    if path.exists():
        for key, value in CAP_RE.findall(path.read_text(encoding="utf-8")):
            if key in caps:
                caps[key] = int(value)
    return caps


class Store:
    """The request and ledger files, under .ocr/ (gitignored)."""

    def __init__(self, root=STATE_DIR):
        self.root = Path(root)

    def _read(self, name, default):
        p = self.root / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default

    def _write(self, name, data):
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def requests(self):
        return self._read("requests.json", {})

    def save_requests(self, data):
        self._write("requests.json", data)

    def ledger(self):
        return self._read("ledger.json", {})

    def save_ledger(self, data):
        self._write("ledger.json", data)

    def ticket_dir(self, tid):
        return self.root / "tickets" / tid


def parse_pages(text):
    """'5,6,8-10' -> [5, 6, 8, 9, 10]."""
    pages = set()
    for part in str(text).split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not m:
            raise Refused(f"'{part}' is not a page or a range")
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        if a < 1 or b < a:
            raise Refused(f"'{part}' is not a valid page range")
        pages.update(range(a, b + 1))
    if not pages:
        raise Refused("no pages given")
    return sorted(pages)


def active_request(requests):
    return next((rid for rid, r in requests.items() if r["status"] in ("planned", "approved")), None)


def open_ticket(requests):
    for rid, r in requests.items():
        for tid, t in r["tickets"].items():
            if t["status"] == "issued":
                return tid
    return None


def spent_today(ledger, today):
    return int(ledger.get(today, 0))


# ---- the five commands ---------------------------------------------------------------------

def plan(store, caps, manifest, doc, pages, today):
    matches = [k for k, m in manifest.items() if doc.lower() in k.lower() and m.get("extraction") == "ocr"]
    if len(matches) != 1:
        raise Refused(f"'{doc}' must match exactly one OCR'd document; it matches {len(matches)}"
                      + (f": {', '.join(matches)}" if matches else " (only OCR'd documents can be read from images)"))
    relpath = matches[0]
    entry = manifest[relpath]
    unknown = [p for p in pages if p not in entry.get("ocr_pages", [])]
    if unknown:
        raise Refused(f"page(s) {unknown} were not OCR'd in {relpath}; only OCR'd pages can be read from images")
    done = [p for p in pages if p in entry.get("vision_pages", [])]
    if done:
        raise Refused(f"page(s) {done} of {relpath} have already been read from images")
    if len(pages) > caps["pages_per_request"]:
        raise Refused(f"{len(pages)} pages is over the limit of {caps['pages_per_request']} per request "
                      "(ai_instructions/vision-budget.md). Pick the pages that matter most.")
    requests = store.requests()
    if active_request(requests):
        raise Refused(f"request {active_request(requests)} is still open; finish or cancel it first")
    rid = f"R{len(requests) + 1}"
    requests[rid] = {
        "doc": relpath, "pages": pages, "status": "planned", "created": today,
        "tickets": {},
    }
    store.save_requests(requests)
    return rid, requests[rid]


def approve(store, rid, now):
    requests = store.requests()
    r = requests.get(rid)
    if not r:
        raise Refused(f"no request {rid}")
    if r["status"] != "planned":
        raise Refused(f"{rid} is {r['status']}, not planned")
    r["status"] = "approved"
    r["approved_at"] = now
    store.save_requests(requests)
    return r


def ticket(store, caps, rid, today, render):
    """Issue the next ticket of an approved request. `render(doc, pages, dest)`
    writes the page images; it is only ever called here."""
    requests = store.requests()
    r = requests.get(rid)
    if not r:
        raise Refused(f"no request {rid}")
    if r["status"] != "approved":
        raise Refused(f"{rid} is {r['status']}: it must be approved before any ticket is issued")
    pending = open_ticket(requests)
    if pending:
        raise Refused(f"ticket {pending} is still open: record it (or abandon it) before issuing another. "
                      "Tickets are one at a time, on purpose.")
    taken = {p for t in r["tickets"].values() for p in t["pages"]}
    remaining = [p for p in r["pages"] if p not in taken]
    if not remaining:
        raise Refused(f"every page of {rid} already has a ticket")
    batch = remaining[:caps["pages_per_ticket"]]
    ledger = store.ledger()
    tid = f"{rid}-T{len(r['tickets']) + 1}"
    dest = store.ticket_dir(tid)
    dest.mkdir(parents=True, exist_ok=True)
    images = render(r["doc"], batch, dest)
    r["tickets"][tid] = {"pages": batch, "status": "issued", "issued": today}
    ledger[today] = spent_today(ledger, today) + len(batch)
    store.save_requests(requests)
    store.save_ledger(ledger)
    return tid, batch, images, dest / "out.md", len(remaining) - len(batch)


PAGE_BLOCK_RE = re.compile(r"^<!--\s*page:\s*(\d+)\s*\(vision\)\s*-->\s*$", re.MULTILINE)


def parse_transcription(text):
    """{page: text} from the agent's output file."""
    marks = list(PAGE_BLOCK_RE.finditer(text))
    out = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[int(m.group(1))] = text[m.end():end].strip()
    return out


VISION_ITEMS_MARK = "<!-- vision-items: equations, tables and figures read from the page image; where the OCR text above disagrees, this is the reading to trust -->"
VISION_ITEMS_RE = re.compile(r"\n*<!-- vision-items:.*?-->\n.*\Z", re.DOTALL)


def merge_vision_pages(note_text, texts):
    """Add each page's image-read items (equations, tables, figures) below its OCR text, and
    mark the page (vision). The OCR prose stays: the page-reader no longer transcribes prose,
    which OCR gets right and which costs most of the output. A second reading of the same page
    replaces the earlier items and keeps the OCR text."""
    for n, body in texts.items():
        block = re.compile(r"^<!-- page: " + str(n) + r"(?: \((?:ocr|vision)\))? -->\n(.*?)(?=^<!-- page: \d+|\Z)",
                           re.MULTILINE | re.DOTALL)
        if not block.search(note_text):
            raise Refused(f"the note has no page marker for page {n}")

        def rebuild(m, n=n, body=body):
            ocr = VISION_ITEMS_RE.sub("", m.group(1)).strip()
            return f"<!-- page: {n} (vision) -->\n\n{ocr}\n\n{VISION_ITEMS_MARK}\n{body}\n\n"
        note_text = block.sub(rebuild, note_text, count=1)
    return note_text


def record(store, tid, manifest, note_path_for, tokens=None):
    """Merge a finished ticket into its note. `note_path_for(doc)` gives the note path.
    `tokens` is what the harness reported the page-reader used, if known: a measured
    number, stored so `status` can show what pages actually cost."""
    requests = store.requests()
    found = next(((rid, r, t) for rid, r in requests.items() for k, t in r["tickets"].items() if k == tid), None)
    if not found:
        raise Refused(f"no ticket {tid}")
    rid, r, t = found
    if t["status"] != "issued":
        raise Refused(f"ticket {tid} is {t['status']}, not issued")
    out = store.ticket_dir(tid) / "out.md"
    if not out.exists():
        raise Refused(f"no transcription at {out}: the page-reader has not written it")
    texts = parse_transcription(out.read_text(encoding="utf-8"))
    if set(texts) != set(t["pages"]):
        raise Refused(f"the transcription covers pages {sorted(texts)} but the ticket is for {t['pages']}; "
                      "nothing was merged")
    empty = [p for p, body in texts.items() if len(body) < 20]
    if empty:
        raise Refused(f"page(s) {empty} have no items and no `[no equations, tables or figures]` line; "
                      "nothing was merged")
    note = note_path_for(r["doc"])
    note.write_text(merge_vision_pages(note.read_text(encoding="utf-8"), texts), encoding="utf-8")
    entry = manifest[r["doc"]]
    entry["vision_pages"] = sorted(set(entry.get("vision_pages", [])) | set(t["pages"]))
    t["status"] = "recorded"
    if tokens is not None:
        t["tokens"] = int(tokens)
    if all(p in entry["vision_pages"] for p in r["pages"]):
        r["status"] = "closed"
    store.save_requests(requests)
    shutil.rmtree(store.ticket_dir(tid), ignore_errors=True)
    return rid, r["status"], t["pages"]


def cancel(store, rid):
    requests = store.requests()
    r = requests.get(rid)
    if not r:
        raise Refused(f"no request {rid}")
    if open_ticket({rid: r}):
        raise Refused("a ticket of this request is still open: record or abandon it first")
    r["status"] = "cancelled"
    store.save_requests(requests)


def abandon(store, tid):
    requests = store.requests()
    for r in requests.values():
        if tid in r["tickets"]:
            r["tickets"][tid]["status"] = "abandoned"
            store.save_requests(requests)
            shutil.rmtree(store.ticket_dir(tid), ignore_errors=True)
            return
    raise Refused(f"no ticket {tid}")


# ---- rendering and the command line ----------------------------------------------------------

def render_pages(doc_relpath, pages, dest):
    """Write PNGs of the given pages (1-based) of PDFs/<doc>. pymupdf is imported
    here so the rest of the module needs only the standard library."""
    import pymupdf
    doc = pymupdf.open(str(PDFS_DIR / doc_relpath))
    images = []
    try:
        for n in pages:
            path = Path(dest) / f"p{n}.png"
            doc[n - 1].get_pixmap(dpi=RENDER_DPI).save(str(path))
            images.append(path)
    finally:
        doc.close()
    return images


def _load_manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}


def _note_path(manifest):
    return lambda doc: REPO_ROOT / manifest[doc]["notes_path"]


def measured_usage(requests):
    """(tokens, pages) over every recorded ticket that has a measured token count."""
    tokens = pages = 0
    for r in requests.values():
        for t in r["tickets"].values():
            if t["status"] == "recorded" and t.get("tokens"):
                tokens += t["tokens"]
                pages += len(t["pages"])
    return tokens, pages


def _status_lines(store, caps, today):
    requests = store.requests()
    lines = [f"Pages issued today: {spent_today(store.ledger(), today)} (there is no daily limit: every request and "
             f"ticket is approved by hand). Limits: {caps['pages_per_ticket']} per ticket, "
             f"{caps['pages_per_request']} per request."]
    tokens, pages = measured_usage(requests)
    if pages:
        lines.append(f"Measured so far: {tokens:,} subagent tokens over {pages} page(s), about "
                     f"{tokens // pages:,} per page (as reported for each page-reader run; the coordinator's "
                     "own tokens are not included). Past pages are not a promise about future ones.")
    else:
        lines.append("No measured usage yet. Cost is not estimated: it depends on the page and has not been "
                     "measured. After a page-reader run, `record --tokens N` stores what the harness reported.")
    if not requests:
        lines.append("No requests.")
    for rid, r in requests.items():
        lines.append(f"{rid} [{r['status']}] {r['doc']} pages {r['pages']}")
        for tid, t in r["tickets"].items():
            used = f", {t['tokens']:,} tokens measured" if t.get("tokens") else ""
            lines.append(f"    {tid} [{t['status']}] pages {t['pages']}{used}")
    return lines


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("status", "plan", "approve", "ticket", "record", "cancel", "abandon"):
        print(__doc__)
        return 2
    cmd, caps, store = argv[0], load_caps(), Store()
    today = date.today().isoformat()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        if cmd == "status":
            print("\n".join(_status_lines(store, caps, today)))
            return 0
        manifest = _load_manifest()
        if cmd == "plan":
            if "--pages" not in argv or len(argv) < 4:
                raise Refused("usage: plan DOC --pages 5,6,7")
            doc = argv[1]
            pages = parse_pages(argv[argv.index("--pages") + 1])
            rid, r = plan(store, caps, manifest, doc, pages, today)
            print(f"Planned {rid}: {len(pages)} page(s) of {r['doc']}: {pages}")
            print("Cost is not estimated: it depends on the page and has not been measured reliably. "
                  "`status` shows measured usage once tickets are recorded.")
            print(f"NOT approved. Approval is the user's decision: they run "
                  f"`python scripts/vision_pages.py approve {rid}` (this asks for permission), "
                  "or approve it in their own terminal.")
        elif cmd == "approve":
            r = approve(store, argv[1], now)
            print(f"Approved {argv[1]} ({len(r['pages'])} pages of {r['doc']}). Active limits: "
                  f"{caps['pages_per_ticket']} per ticket, {caps['pages_per_request']} per request. "
                  "Every ticket still needs approval.")
        elif cmd == "ticket":
            tid, batch, images, out, left = ticket(store, caps, argv[1], today, render_pages)
            print(f"Ticket {tid}: pages {batch}.")
            print("Images:")
            for p in images:
                print(f"  {Path(p).as_posix()}")
            print(f"Output file the page-reader must write: {Path(out).as_posix()}")
            print(f"Pages still without a ticket in this request: {left}. Do not issue another ticket "
                  "until this one is recorded and the user has been told.")
            print("When the page-reader finishes, record with `--tokens N`, where N is the token usage the "
                  "harness reported for that run.")
        elif cmd == "record":
            tokens = None
            if "--tokens" in argv:
                try:
                    tokens = int(argv[argv.index("--tokens") + 1])
                except (IndexError, ValueError):
                    raise Refused("--tokens needs a whole number")
            rid, status, pages = record(store, argv[1], manifest, _note_path(manifest), tokens)
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(f"Recorded {argv[1]}: pages {pages} are now marked (vision) in the note. Request {rid} is {status}.")
            print("If a method card rested on these pages, update or remove its `read_from: ocr` line.")
        elif cmd == "cancel":
            cancel(store, argv[1])
            print(f"Cancelled {argv[1]}.")
        elif cmd == "abandon":
            abandon(store, argv[1])
            print(f"Abandoned {argv[1]}. Its pages stay in the page ledger.")
    except (Refused, IndexError, KeyError) as e:
        print(f"Refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
