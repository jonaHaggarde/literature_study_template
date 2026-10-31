"""The decision tree as a TikZ picture, drawn from the same table as the mermaid diagram.

The chosen path runs down the left. Each question's other answers are leaves to the right,
styled by status (explored, not examined, candidate). Every internal node is a question and
every edge is an answer, as in the mermaid version (root CLAUDE.md, "Decision trees").
"""

from build_decision_trees import question_order
from texutil import tex_escape as esc

PICTURE_HEAD = r"""\begin{center}
\begin{tikzpicture}[x=1cm, y=1cm, font=\small,
  q/.style={draw, rounded corners, fill=green!10, text width=6.2cm, align=left, inner sep=4pt},
  rec/.style={draw, very thick, rounded corners, fill=green!18, text width=6.2cm, align=left, inner sep=4pt},
  leaf/.style={draw, rounded corners, text width=4.6cm, align=left, inner sep=3pt, font=\footnotesize},
  explored/.style={leaf, fill=gray!15}, identified/.style={leaf, dashed},
  candidate/.style={leaf, thick, fill=blue!8},
  ans/.style={font=\scriptsize\itshape, fill=white, inner sep=1pt, text width=3.0cm, align=center}]"""

TAGS = {"explored": "explored", "candidate": "candidate, to be settled", "identified": "not examined"}
LEAF_STEP = 1.35


def render_latex(rows):
    order = question_order(rows)
    text = {}
    for r in rows:
        if r["question"]:
            text.setdefault(r["Q"], r["question"])
    chosen = {r["Q"]: r for r in rows if r["status"] == "chosen"}
    out = [PICTURE_HEAD]
    y = 0.0
    previous = None
    for q in order:
        leaves = [r for r in rows if r["Q"] == q and r["status"] != "chosen"]
        height = max(1.5, LEAF_STEP * len(leaves) + 0.4)
        out.append(f"\\node[q, anchor=north west] ({q}) at (0,{-y:.2f}) "
                   f"{{\\textbf{{{esc(q)}}}: {esc(text.get(q, ''))}}};")
        if previous:
            out.append(f"\\draw[->, very thick, green!50!black] ({previous[0]}.south) -- "
                       f"node[ans, right=2pt] {{{esc(previous[1])}}} ({q}.north);")
        for k, r in enumerate(leaves):
            leaf = f"{q}L{k + 1}"
            out.append(f"\\node[{r['status']}, anchor=west] ({leaf}) at (8.4,{-y - 0.7 - LEAF_STEP * k:.2f}) "
                       f"{{{esc(r['method'])} \\textit{{({TAGS[r['status']]})}}}};")
            out.append(f"\\draw[->] ({q}.east) -- node[ans, pos=0.55, above] {{{esc(r['answer'])}}} ({leaf}.west);")
        pick = chosen.get(q)
        previous = (q, pick["answer"]) if pick and pick["then"] != "END" else None
        if pick and pick["then"] == "END":
            out.append(f"\\node[rec, anchor=north west] (R) at (0,{-y - height:.2f}) "
                       f"{{\\textbf{{Recommended:}} {esc(pick['method'])}}};")
            out.append(f"\\draw[->, very thick, green!50!black] ({q}.south) -- "
                       f"node[ans, right=2pt] {{{esc(pick['answer'])}}} (R.north);")
            y += 1.2
        y += height
    out += [r"\end{tikzpicture}", r"\end{center}", ""]
    return "\n".join(out)
