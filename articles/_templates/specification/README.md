# specification-{{NAME}}

A specification of one chosen concept, detailed enough that the implementation can be built
from it alone.

| | |
|---|---|
| Gate | `split` (full): passes on the first specification; later ones join by a recorded amendment |
| Written from | the rationale (the chosen concept), the requirements and the review |
| Stands alone | a teammate can take it as the only source for the implementation. It cites the rationale and the review (as entries in `articles/common/references_extra.bib`, by article and version) for the reasoning and the methods not chosen |
| Contains no | the argument for the choice (that is the rationale) |

**Varies per project:** for software the derivation in each component is an interface and
behaviour specification, and for a non-engineering project the symbol table is a glossary.
Copy `sections/component.tex` once per component, named after it, and add each to `main.tex`.

The structure: introduction, assumptions, conventions, structure, one section per
component, parameters, verification.
