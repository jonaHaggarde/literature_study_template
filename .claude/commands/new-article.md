---
description: Create a new article from a template in articles/_templates/ (today: a specification, one per chosen concept).
argument-hint: "[kind] [name], e.g. specification torque-allocation"
---

Create an article from a template.
$ARGUMENTS

1. **Which template.** Run `python study/scripts/new_article.py --list`. If the user named a
   kind, use it. If none is named, show the list and ask. Only templates that exist can be
   created: the other articles (`definition`, `map`, `review`, `requirements`, `rationale`)
   already exist as folders under `articles/`; say so if the user asks for one of them.

2. **A name, for a specification.** One specification per chosen concept, named after the
   concept (`torque-allocation`): lowercase letters, digits and single hyphens. If it is
   missing, ask. Several concepts or components that need their own document get their own
   specification, never sections of one.

3. **Check the gate before it.** A specification normally follows an accepted rationale (the
   `concept` gate). The script warns if `articles/rationale` exists and is not accepted. Pass
   the warning on to the user and let them decide; do not block.

4. **Create it.** `python study/scripts/new_article.py <kind> <name>`. It copies the template to
   `articles/<kind>-<name>/`, fills in the name, and records version `0.1`. Never copy the
   folder by hand.

5. **Report** the folder, that it is at `0.1`, and the next step: the article's own
   `README.md` says what it is written from and what it must not contain; each section file
   says what it must contain. Writing it follows `study/ai_instructions/article-style.md`;
   record each substantial edit with `article_version.py <folder> edit`, build with
   `build_articles.py --only <folder>`, and run `style_check.py <folder>`.

Do not write the article's text in this command: creating it and drafting it are separate
steps, and the user decides when to draft.
