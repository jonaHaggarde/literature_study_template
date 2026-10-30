"""Imported for its side effect: make stdout/stderr UTF-8 so a paper title
containing a character outside the Windows console code page (an infinity
sign, say) cannot crash a script that prints it. The scripts print titles,
tags and quotes taken from documents, so this is not hypothetical."""

import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
