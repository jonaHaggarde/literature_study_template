# Workflow diagrams

Five diagrams covering this repo's process end to end: starting a new
study, the PDF batch pipeline, how Claude answers a literature question,
which script reads/writes which file, and how the pipeline itself grows.
These render natively on GitHub and in most markdown viewers (no
extension needed). Read alongside `ai_instructions/workflow.md`, which
these diagrams summarize graphically — that file is the authoritative
text version if the two ever disagree. Not depicted here, to keep these
diagrams readable: `ai_instructions/batch-orchestration.md`,
`long-running-sessions.md`, and `project_documents/source-access.md` —
situational extensions to diagram 2's pipeline, read directly rather than
via a diagram.

## 1. Starting a new study

From "just cloned the template" to "ready to process real PDFs." Note on
step E: `study/CLAUDE.md` only loads automatically as Claude Code's
memory file when `study/` is the actual working directory it was started
in — starting from the repo root instead isn't guaranteed to pick it up
until Claude happens to explore into `study/` on its own, so `cd study`
first is the reliable path.

```mermaid
flowchart TD
    A["'Use this template' on GitHub<br/>(or clone + re-init git)"] --> B["Rename repo for the new topic"]
    B --> C["Run scripts/setup.ps1 or setup.sh<br/>creates .venv, installs dependencies"]
    C --> D["User drops project_documents/<br/>project brief, purpose, existing drafts"]
    D --> E["cd study, then open Claude Code there<br/>(working dir matters - see note above)"]
    E --> F["study/CLAUDE.md auto-loads as the memory file,<br/>points straight at ai_instructions/README.md"]
    F --> G{"Is ai_instructions/scope.md<br/>still the placeholder?"}
    G -- yes --> H["Claude reads project_documents/<br/>and interviews the user about the topic"]
    H --> I["Claude writes a real scope.md:<br/>in scope / out of scope / what counts as a gap"]
    G -- no --> J["Scope already defined"]
    I --> K["Study is ready for real work"]
    J --> K
    K --> L["User drops PDFs into PDFs/"]
    L --> M(["Continue: diagram 2, Adding PDFs"])
```

## 2. Adding PDFs (the batch pipeline)

The core loop, run once per batch of new PDFs — mirrors
`ai_instructions/workflow.md`'s "Processing new PDFs" section exactly.

```mermaid
flowchart TD
    A["User drops new PDFs into PDFs/"] --> B["Run: python scripts/convert.py"]
    B --> B1["Hash-checks every PDF against manifest.json<br/>unchanged files are skipped"]
    B1 --> B2["New/changed PDFs: extract text (pymupdf4llm)<br/>+ best-effort metadata (title/authors/year/DOI)"]
    B2 --> C["Writes notes/&lt;name&gt;.md<br/>Key Findings left as TODO"]
    C --> D["Appends a stub entry to catalog.md"]
    D --> E["Updates manifest.json"]
    E --> F["Claude does a full, non-lazy read of each new note"]
    F --> G{"In scope?<br/>checked against ai_instructions/scope.md"}
    G -- no --> G1["Left excluded, reason noted"]
    G -- yes --> H["Claude fills catalog.md fields<br/>+ note's Key Findings / Implementation Notes"]
    H --> I{"Head-to-head comparison<br/>or ranked survey?"}
    I -- yes --> I1["contribution: comparison-study<br/>quick-reference list regenerated later, not by hand"]
    I -- no --> J{"Dense cluster of related<br/>papers now exists?"}
    I1 --> J
    J -- yes --> J1["Claude builds/updates a topics/*.md dossier<br/>comparison table + Open questions section"]
    J -- no --> K
    J1 --> K["Run: python scripts/build_reference_index.py<br/>rebuilds reference-index.md"]
    H --> GAP{"Reveals an in-scope sub-topic<br/>that's thin/absent in the catalog?"}
    GAP -- yes --> GAP1["Log to topics/gaps.md<br/>'Flagged directly' section, ask user for more sources"]
    GAP -- no --> K
    K --> L["Run: python scripts/validate_repo.py --fix<br/>fixes tag casing + quick-reference list"]
    L --> M{"Any FAIL?"}
    M -- yes --> N["Fix the underlying issue"]
    N --> L
    M -- no --> O{"Any topics/*.md dossier<br/>changed this batch?"}
    O -- yes --> O1["Run: python scripts/build_gaps_index.py"]
    O -- no --> P
    O1 --> P["Claude runs 2-3 real discovery queries by hand<br/>the actual usability check, scripts can't verify this"]
    P --> Q["Batch done"]
```

## 3. Answering a literature question

How Claude routes a question and how much it reads to answer it — cost
discipline matters here since `notes/` and `reference-index.md` get
expensive at scale.

```mermaid
flowchart TD
    Q["User asks a literature question"] --> T{"What kind of question?"}
    T -- "Which method/finding<br/>should I trust?" --> A1["Check catalog.md's Comparison &amp;<br/>survey papers quick-reference list"]
    A1 --> A2{"Relevant topics/*.md<br/>dossier exists and is current?"}
    A2 -- yes --> A3["Answer from the dossier:<br/>comparison table + recommendation"]
    A2 -- no --> A4["Build or update the dossier,<br/>then answer from it"]
    T -- "What are my options<br/>for X?" --> B1["Read catalog.md in full,<br/>filter by topics/vocabulary.md tags"]
    B1 --> B2["grep reference-index.md for<br/>leads not yet in the catalog"]
    B2 --> B3["Present as a menu:<br/>covered here vs. lead only"]
    T -- "Find a new source on<br/>a narrow topic" --> C1["grep -i reference-index.md<br/>for the specific terms"]
    C1 --> C2["Report matches as unverified leads<br/>title/authors/venue/year only, never read"]
    T -- "What's missing? What<br/>should I look into next?" --> D1["Check topics/gaps.md<br/>cross-referenced against scope.md"]
    D1 --> D2["Suggest concrete sourcing directions,<br/>not just 'not sure'"]

    subgraph COST["Read-cost discipline, cheapest first"]
        direction LR
        X1["catalog.md<br/>read in full, always"] --> X2["topics/*.md dossier<br/>pre-synthesized, cheap"]
        X2 --> X3["notes/*.md<br/>expensive, only to verify one claim"]
        X3 --> X4["reference-index.md<br/>large, grep only, never full-read"]
    end
```

## 4. System map: which script touches which file

Deterministic scripts move data mechanically; Claude is the only actor
that makes judgment calls, and it's also what triggers the scripts.

```mermaid
flowchart LR
    subgraph INPUTS["Inputs, user-provided"]
        PDFs["PDFs/"]
        ProjDocs["project_documents/"]
    end

    CLAUDE(["Claude<br/>judgment calls"])

    subgraph SCRIPTS["scripts/, deterministic, no Claude needed"]
        Convert["convert.py"]
        RefIdx["build_reference_index.py"]
        GapsIdx["build_gaps_index.py"]
        Validate["validate_repo.py --fix"]
    end

    subgraph FILES["Data files"]
        Notes["notes/*.md"]
        Manifest["manifest.json"]
        Catalog["catalog.md"]
        RefIndexFile["reference-index.md"]
        Topics["topics/*.md dossiers"]
        Gaps["topics/gaps.md"]
        Scope["ai_instructions/scope.md"]
        Decisions["decisions.md"]
    end

    PDFs --> Convert
    Convert --> Notes
    Convert --> Catalog
    Convert --> Manifest

    Notes --> RefIdx --> RefIndexFile
    Topics --> GapsIdx --> Gaps

    Catalog --> Validate
    Notes --> Validate
    Manifest --> Validate
    Topics --> Validate
    Validate -. "fix mode rewrites" .-> Catalog

    ProjDocs --> CLAUDE
    CLAUDE -- "reads / writes" --> Scope
    CLAUDE -- "reads notes, fills fields" --> Catalog
    CLAUDE -- "writes Key Findings +<br/>Implementation Notes" --> Notes
    CLAUDE -- "builds dossiers" --> Topics
    CLAUDE -- "logs gaps, checks against scope" --> Gaps
    CLAUDE -- "logs conclusions" --> Decisions
    CLAUDE -- runs --> Convert
    CLAUDE -- runs --> RefIdx
    CLAUDE -- runs --> GapsIdx
    CLAUDE -- runs --> Validate
```

## 5. Extending the pipeline (adding a new script)

What happens when a new repetitive manual step shows up and someone
decides it's worth automating.

```mermaid
flowchart TD
    N["New repetitive manual step identified"] --> D{"Purely mechanical?<br/>no judgment required"}
    D -- yes --> S["Write scripts/new_script.py<br/>reading/writing existing files, same pattern as the others"]
    S --> W["Document it in ai_instructions/workflow.md:<br/>what it does, when to run it"]
    W --> V["Optionally wire it into<br/>validate_repo.py's checks or --fix path"]
    D -- no --> J["Stays a Claude-driven step,<br/>documented in ai_instructions/workflow.md instead"]
```
