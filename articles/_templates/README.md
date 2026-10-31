# articles/_templates/

Article templates. A template is a folder like any article (`main.tex`, `sections/`,
`README.md`) whose text has two tokens: `{{NAME}}` and `{{TITLE}}`. Folders starting with `_`
are ignored by the build and the validator, so a template is never built as it stands.

Create an article from one with `/new-article`, or:

```bash
python study/scripts/new_article.py --list
python study/scripts/new_article.py specification concept-a
```

That copies the template to `articles/<kind>-<name>/`, fills in the tokens, writes its
generated references file and records version `0.1`. From then on it is built, validated,
style-checked and version-tracked like every other article.

`study/scripts/tests/test_templates.py` instantiates **every** template and runs those checks
(and builds the PDF where LaTeX is installed), so a change to the shared preamble or a
checker cannot silently break one.

Every article has a template: `definition`, `map`, `review`, `requirements`, `rationale`
and `specification`. A singleton becomes `articles/<kind>/`. The specification is the one
family: one per chosen concept, so it takes a name and becomes `articles/specification-<name>/`.
A fresh repo ships no articles, so a project holds only the ones it has reached (the
requirements are optional and may never exist), and opening a gate and creating its article are
the same step.

An article starts as a skeleton at version `0.1`. The command that writes its first real draft
replaces that row (`article_version.py <folder> draft --restart`), so the first real draft is
`0.1`.
