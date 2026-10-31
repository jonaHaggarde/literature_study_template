# specification (template)

Not built as it stands: folders starting with `_` are ignored by the build and the validator.
To start a specification, copy this folder:

```bash
cp -r articles/_templates/specification articles/specification-<name>
python study/scripts/article_version.py specification-<name> draft
```

Name the folder after the concept (`specification-<concept>`). One specification is one
article; several concepts or components that need their own document get their own
folder, never sections of one.

| | |
|---|---|
| Gate | `split` (full): passes on the first specification, later ones join by a recorded amendment |
| Written from | the rationale (the chosen concept), the requirements and the review |
| Stands alone | a teammate can take it as the only source for the implementation; it cites the rationale and the review (as entries in `articles/common/references_extra.bib`, by article and version) for the reasoning and the methods not chosen |
| Contains no | the argument for the choice (that is the rationale) |

**Varies per project:** the derivation in each component is an interface and behaviour
specification for software, and the symbol table is a glossary for a non-engineering
project. Component files are copied once per component.

The structure follows the LiUFS algorithm specification: introduction, conventions, structure,
one section per component, parameters, evaluation.
