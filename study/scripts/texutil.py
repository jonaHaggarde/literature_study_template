#!/usr/bin/env python3
"""Small LaTeX helpers shared by the scripts that write .tex and .bib files.

Imported, not run."""

_TEX_SPECIAL = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def tex_escape(s):
    """Escape the characters LaTeX treats as special, for text taken from a catalog
    entry or a method card."""
    return "".join(_TEX_SPECIAL.get(c, c) for c in s)
