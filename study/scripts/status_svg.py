"""The status snapshot (status.py) drawn as one SVG, with no dependency and no model.

A row of boxes for the gates (colour is the state), a line saying what is next, and three cards:
the intake coverage, the catalog by method family, and the articles. The picture has its own
light background so it reads the same in a light or a dark viewer. `/where` sends it to the user
with `SendUserFile`; a few tokens, however full the picture is.
"""

import textwrap
from xml.sax.saxutils import escape

WIDTH = 1000
MARGIN = 24
FONT = "Segoe UI, Helvetica, Arial, sans-serif"
TEXT, MUTED, LINE, PAPER = "#1f2328", "#656d76", "#d0d7de", "#ffffff"
AMBER, GREEN = "#bf8700", "#1a7f37"
STATES = {   # state: (fill, stroke, dash)
    "passed": ("#dafbe1", "#1a7f37", ""),
    "open": ("#fff1d6", "#bf8700", ""),
    "ready": ("#ddf4ff", "#0969da", ""),
    "not-reached": ("#f6f8fa", "#afb8c1", ""),
    "skipped": ("#f6f8fa", "#afb8c1", "5 4"),
}
STATE_WORDS = {"passed": "passed", "skipped": "skipped", "open": "open",
               "ready": "ready to open", "not-reached": "not reached"}
SCOPE_WORDS = {"ok": "scope.md is in step with the definition",
               "ready": "scope.md can be written from the accepted definition",
               "waiting": "scope.md waits for the definition gate",
               "stale": "scope.md is behind the definition",
               "unstamped": "scope.md is not tied to the definition",
               "fallback": "scope.md was written without a definition",
               "no-pipeline": "no definition article in this repo"}
MAX_ROWS = 8


def clip(text, limit):
    return text if len(text) <= limit else text[:max(limit - 1, 1)] + "…"


def text(x, y, content, size=13, weight="normal", fill=TEXT, anchor="start", italic=False):
    style = ' font-style="italic"' if italic else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}" '
            f'text-anchor="{anchor}"{style}>{escape(content)}</text>')


def rect(x, y, w, h, fill, stroke, dash="", radius=8, width=1.2):
    dashed = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{radius}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}"{dashed}/>')


def wrapped(x, y, content, width_chars, size=13, fill=TEXT, line=18, weight="normal"):
    """Wrapped text; returns (elements, height used)."""
    lines = textwrap.wrap(content, width_chars) or [""]
    return [text(x, y + i * line, ln, size, weight, fill) for i, ln in enumerate(lines)], line * len(lines)


# ---- the gate row ----------------------------------------------------------------------------

def gate_row(data, y):
    gates = data["gates"]
    n = len(gates)
    gap = 22
    bw = (WIDTH - 2 * MARGIN - (n - 1) * gap) / n
    nxt = data["next"]["gate"]
    out = []
    for i, g in enumerate(gates):
        x = MARGIN + i * (bw + gap)
        fill, stroke, dash = STATES[g["state"]]
        is_next = g["id"] == nxt
        out.append(rect(x, y, bw, 96, fill, stroke, dash, width=3 if is_next else 1.2))
        cx = x + bw / 2
        out.append(text(cx, y + 28, clip(g["title"], int(bw / 8.5)), 15, "bold", anchor="middle"))
        out.append(text(cx, y + 50, clip(f"{g['weight']} · {STATE_WORDS[g['state']]}", int(bw / 6.6)), 12,
                        anchor="middle"))
        if g["detail"]:
            out.append(text(cx, y + 72, clip(g["detail"], int(bw / 6.6)), 12, fill=MUTED, anchor="middle"))
        if is_next:
            out.append(text(cx, y - 8, "next", 12, "bold", fill=stroke, anchor="middle"))
        if i < n - 1:
            ax = x + bw + 3
            out.append(f'<line x1="{ax:.1f}" y1="{y + 48}" x2="{ax + gap - 8:.1f}" y2="{y + 48}" '
                       f'stroke="{MUTED}" stroke-width="1.5" marker-end="url(#arrow)"/>')
    return out


# ---- the cards -------------------------------------------------------------------------------

def card_frame(x, y, w, h, title, subtitle=""):
    out = [rect(x, y, w, h, PAPER, LINE), text(x + 14, y + 26, title, 15, "bold")]
    if subtitle:
        out.append(text(x + w - 14, y + 26, subtitle, 12, fill=MUTED, anchor="end"))
    return out


def intake_card(data, x, y, w):
    coverage = data["intake"]["coverage"]
    body, row_y = [], y + 52
    for section, (answered, unknown) in coverage.items():
        body.append(text(x + 14, row_y, section, 12))
        cx = x + 112
        if not answered and not unknown:
            body.append(text(cx, row_y, "no answer yet", 12, fill=MUTED, italic=True))
        for k in range(min(answered, 10)):
            body.append(rect(cx + k * 14, row_y - 10, 10, 10, GREEN, GREEN, radius=2, width=1))
        if answered > 10:
            body.append(text(cx + 10 * 14, row_y, f"+{answered - 10}", 11, fill=MUTED))
        offset = min(answered, 10) * 14 + (22 if answered > 10 else 0)
        for k in range(min(unknown, 6)):
            body.append(rect(cx + offset + k * 14, row_y - 10, 10, 10, PAPER, AMBER, radius=2, width=1.5))
        row_y += 21
    row_y += 4
    body.append(text(x + 14, row_y, "answered", 11, fill=GREEN))
    body.append(text(x + 80, row_y, "unknown", 11, fill=AMBER))
    extra, used = wrapped(x + 14, row_y + 22, SCOPE_WORDS.get(data["scope"]["code"], data["scope"]["code"]),
                          int((w - 28) / 6.4), 12, MUTED)
    height = row_y + 22 + used - y + 8
    return card_frame(x, y, w, height, "Intake", f"{data['intake']['rows']} rows") + body + extra, height


def catalog_card(data, x, y, w):
    fams, count = data["families"], data["catalog"]["processed"]
    body, row_y = [], y + 52
    body.append(text(x + 14, row_y, f"{count} processed {'entry' if count == 1 else 'entries'}", 13))
    row_y += 24
    if not fams:
        body.append(text(x + 14, row_y, "no method cards yet", 12, fill=MUTED, italic=True))
        row_y += 6
    biggest = max((f["sources"] for f in fams), default=1)
    track = w - 28 - 114 - 112   # room for the label on the left and "999 src, 999 cards" on the right
    for fam in fams[:MAX_ROWS]:
        body.append(text(x + 14, row_y, clip(fam["name"], 16), 12))
        body.append(rect(x + 114, row_y - 11, max(track * fam["sources"] / biggest, 3), 11, "#0969da", "#0969da",
                         radius=2, width=1))
        body.append(text(x + w - 14, row_y, f"{fam['sources']} src, {fam['cards']} cards", 11, fill=MUTED,
                         anchor="end"))
        row_y += 21
    if len(fams) > MAX_ROWS:
        body.append(text(x + 14, row_y, f"+{len(fams) - MAX_ROWS} more families", 11, fill=MUTED))
        row_y += 18
    if data["catalog"]["nudge"]:
        extra, used = wrapped(x + 14, row_y + 8, data["catalog"]["nudge"], int((w - 28) / 6.4), 12, AMBER)
        body += extra
        row_y += used + 8
    height = row_y - y + 12
    return card_frame(x, y, w, height, "Catalog") + body, height


def articles_card(data, x, y, w):
    arts = data["articles"]
    body, row_y = [], y + 52
    if not arts:
        body.append(text(x + 14, row_y, "no articles yet", 12, fill=MUTED, italic=True))
        row_y += 6
    for art in arts[:MAX_ROWS]:
        body.append(text(x + 14, row_y, clip(art["name"], 18), 13, "bold"))
        body.append(text(x + 14 + 138, row_y, f"v{art['version']}", 12))
        marks = f"{art['todos']} todo, {art['open_issues']} open"
        body.append(text(x + w - 14, row_y, marks, 11, fill=AMBER if art["todos"] or art["open_issues"] else MUTED,
                         anchor="end"))
        row_y += 21
    if len(arts) > MAX_ROWS:
        body.append(text(x + 14, row_y, f"+{len(arts) - MAX_ROWS} more articles", 11, fill=MUTED))
        row_y += 18
    height = row_y - y + 12
    return card_frame(x, y, w, height, "Articles") + body, height


# ---- the page --------------------------------------------------------------------------------

def render(data):
    out = [text(MARGIN, 36, "Where the study stands", 20, "bold"),
           text(WIDTH - MARGIN, 36, data["date"], 12, fill=MUTED, anchor="end")]
    row_y = 72
    out += gate_row(data, row_y)
    y = row_y + 96 + 22
    if data["adhoc_open_since"]:
        out.append(text(MARGIN, y + 4, f"An ad hoc stop-and-look is open (since {data['adhoc_open_since']}).", 12,
                        fill=AMBER))
        y += 22

    chars = int((WIDTH - 2 * MARGIN - 100) / 6.6)
    next_lines, used = wrapped(MARGIN + 70, y + 29, data["next"]["text"], chars, 14)
    hint_lines = []
    if data["next"]["hint"]:
        hint_lines, hint_used = wrapped(MARGIN + 70, y + 29 + used + 4, "The last gate unlocked: " + data["next"]["hint"],
                                        chars, 12, MUTED, line=16)
        used += hint_used + 4
    panel = used + 26
    out += [rect(MARGIN, y, WIDTH - 2 * MARGIN, panel, "#f6f8fa", LINE), text(MARGIN + 14, y + 29, "Next", 14, "bold",
                                                                              fill="#0969da")]
    out += next_lines + hint_lines
    y += panel + 18

    gap = 16
    cw = (WIDTH - 2 * MARGIN - 2 * gap) / 3
    cards = [intake_card(data, MARGIN, y, cw), catalog_card(data, MARGIN + cw + gap, y, cw),
             articles_card(data, MARGIN + 2 * (cw + gap), y, cw)]
    tallest = max(h for _e, h in cards)
    for k, (elements, h) in enumerate(cards):
        if h < tallest:   # keep the three cards the same height
            elements[0] = elements[0].replace(f'height="{h:.1f}"', f'height="{tallest:.1f}"', 1)
        out += elements
    height = y + tallest + MARGIN
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height:.0f}" '
            f'viewBox="0 0 {WIDTH} {height:.0f}" font-family="{FONT}" role="img" '
            'style="max-width:100%;height:auto">'
            f'<title>Where the study stands, {escape(data["date"])}</title>'
            '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>'
            f'<rect width="{WIDTH}" height="{height:.0f}" fill="{PAPER}"/>')
    return head + "\n" + "\n".join(out) + "\n</svg>\n"
