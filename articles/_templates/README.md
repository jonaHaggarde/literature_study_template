# articles/_templates/

Article templates. A template is a folder like any article (`main.tex`, `sections/`,
`README.md`) whose text has two tokens: `{{NAME}}` and `{{TITLE}}`. Folders starting with `_`
are ignored by the build and the validator, so a template is never built as it stands.

Create an article from one with `/new-article`, or:

```bash
python study/scripts/new_article.py --list
python study/scripts/new_article.py specification torque-allocation
```

That copies the template to `articles/<kind>-<name>/`, fills in the tokens, writes its
generated references file and records version `0.1`. From then on it is built, validated,
style-checked and version-tracked like every other article.

`study/scripts/tests/test_templates.py` instantiates **every** template and runs those checks
(and builds the PDF where LaTeX is installed), so a change to the shared preamble or a
checker cannot silently break one.

Today the only template is `specification`, the one article that is a family (one per chosen
concept). The other articles ship as ready folders; they move into templates when the gate
machinery is built, so that opening a gate creates its article.
