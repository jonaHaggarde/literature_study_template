---
description: Create an article from a template in articles/_templates/ (definition, map, review, requirements, rationale, or a specification per chosen concept).
argument-hint: "[kind] [name], e.g. definition, or specification concept-a"
---

Create an article from a template.
$ARGUMENTS

The repo ships no articles: each is created when the work reaches it.

1. **Which template.** Run `python study/scripts/new_article.py --list`. If the user named a
   kind, use it. If none is named, show the list and ask. A kind whose folder already exists
   under `articles/` cannot be created again: say so and point to the existing article.

2. **A name, for a specification only.** One specification per chosen concept, named after
   the concept (`concept-a`): lowercase letters, digits and single hyphens. If it is
   missing, ask. Several concepts or components that need their own document get their own
   specification, never sections of one. The other kinds have one folder named after them and
   take no name.

3. **Check the gate before it.** Each article follows an earlier gate (the definition follows
   the intake; the map, the accepted definition; the review, the map; the requirements, the
   review; the rationale, the review and the requirements; a specification, the rationale).
   The script only warns for a specification whose rationale is not accepted. For the others,
   look at the earlier article's status in `articles/<name>/versions.json` and tell the user if
   it is not accepted; let them decide, do not block. The requirements are optional: say so.

4. **Create it.** `python study/scripts/new_article.py <kind> [name]`. It copies the template to
   `articles/<folder>/`, fills in the name, and records a skeleton row at version `0.1`. Never
   copy a folder by hand.

5. **Report** the folder and the next step: the article's own `README.md` says what it is
   written from and what it must not contain, and each section file says what it must contain.
   Writing it follows `study/ai_instructions/article-style.md`. The first real draft is
   recorded with `article_version.py <folder> draft --restart` (it replaces the skeleton row,
   so the first draft is `0.1`); later changes with `edit`. Build with
   `build_articles.py --only <folder>` and check with `style_check.py <folder>`.

Do not write the article's text in this command: creating it and drafting it are separate
steps, and the user decides when to draft.
