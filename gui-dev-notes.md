> **Status: scratch / temporary.** This is a working log for the
> `gui-dashboard` branch, not a permanent repo document. Once the GUI
> work lands (or is abandoned), fold anything worth keeping into
> `study/ai_instructions/` and `README.md`, and delete this file.

# GUI + backend rework — progress and plan

## Goal

Turn this template from a purely terminal-driven workflow into one that
also has a local, interactive dashboard: milestones/checklist view, an
exploration map (nodes/edges you can click into), a gap browser you can
click into to launch new depth/broad studies, and per-node detail views.
The terminal workflow (`study/ai_instructions/`, the existing agents)
must keep working exactly as it does today — the GUI is additive, not a
replacement for running this from Claude Code directly.

All of this is happening on the `gui-dashboard` branch so `main` stays
untouched until it's ready.

## Architecture decisions made so far

**Local server, not a static-only page.** A static HTML+JSON viewer
would cover milestones/map/gap-browsing fine, but "click a gap to launch
a new study" means triggering the `claude` CLI from the page, which a
static page can't do alone. Decision: a small local server (Python,
Flask/FastAPI) that serves the dashboard's pages and exposes endpoints
to shell out to `claude` and report progress back to the page.

**Data model split by content type, not a blanket format switch.**
- Structured/relational data — catalog entries, gap list with status,
  milestone/checklist state, and the relationships that make the
  exploration map (paper↔topic, cites, depends-on) — moves to JSON
  (`study/catalog.json`, `study/gaps.json`, `study/milestones.json`).
  Markdown was always a workaround for this; parsing a table back into a
  graph is fragile, and the GUI needs to query this data directly.
- Narrative content — per-paper notes, topic-dossier prose (comparison
  discussion, recommendation, open questions) — stays Markdown. It's
  genuinely prose, not data, and Markdown is what both Claude and a
  human read/diff comfortably.

**One shared access layer, not two independent editors of the same
files.** The real risk to "works from both terminal and GUI" isn't file
format, it's an LLM hand-editing JSON via string replacement the way it
edits Markdown today — one dropped comma breaks the whole file, unlike
Markdown which tolerates a bad edit gracefully. Decision: a single
Python module (`study/scripts/lib/`) owns all reads/writes to the JSON
files, with validation on every write. Terminal Claude Code calls it
through a CLI (`study/scripts/cli.py ...`) instead of freehand-editing
JSON — `study/ai_instructions/` will need updating to say "use the CLI"
the same way it currently says "edit the Markdown." The GUI server
imports the same module directly. Same data, same validation, two
entry points, neither can corrupt the other's state.

**Scripts for as much as possible, AI for as little as possible** (the
user's explicit standing preference for this project). Catalog CRUD,
gap-status changes, milestone updates, graph derivation, and validation
are all plain deterministic scripts — no model call involved. AI is
reserved for steps that inherently require judgment: reading a PDF and
drafting notes, synthesizing a dossier across sources, answering an
open-ended literature question, or judging whether a rule-flagged gap is
worth pursuing. The GUI's "launch" buttons split the same way: most
map/gap/milestone interactions trigger a script and refresh instantly;
only buttons that start an actual research task shell out to `claude`.

**Multi-page, not one long HTML file.** Separate pages/routes: an
overview/milestones dashboard, the exploration map, a gap browser, and
paper/topic detail views — served by the local server rather than
bundled into a single page.

## Current phase: frontend only, no wiring

Per the user's instruction, the current step is designing the GUI's
*frontend* only — clickable, but not yet talking to Claude or any
backend. Visual direction: a light, warm theme (warm ivory background,
terracotta/amber/sage accents — not a cold neon palette). First page
being built: the main page, which doubles as the exploration map view,
since that's the centerpiece interaction described below.

Files so far live under `study/dashboard/` (the dashboard is part of the
literature-review engine per `study/CLAUDE.md`'s root/`study/` split, so
it belongs there, not at the repo root):

- `study/dashboard/index.html` — main page / exploration map
- `study/dashboard/style.css` — light warm theme (shared by both pages)
- `study/dashboard/app.js` — the map: rendering, expand/collapse,
  free-form drag with persisted positions, gap-intensity coloring, the
  "chosen" toggle, and the "add sub-branch" flow — all client-side,
  nothing calls a network
- `study/dashboard/data.sample.js` — hardcoded sample data derived from
  `../calibration-pipeline-tree.md`, standing in for the future
  `catalog.json`/`gaps.json`-derived graph. Clearly a placeholder — real
  data wiring is a later step, once the backend and JSON schemas exist.
- `study/dashboard/console.html` / `console.js` — a second page, a
  terminal-styled input/scrollback UI that currently just echoes back
  "not connected yet." Stands in for the future page that will actually
  talk to Claude through the local server.

Map interactions implemented so far (all frontend-only, persisted via
this browser's `localStorage` under one key, `explorationMapState_v1` —
not a backend, and specific to this browser/profile until real
persistence exists):

- Any node with children can be expanded/collapsed by clicking it, and
  can have further sub-branches added to it via an in-panel form,
  arbitrarily deep — not just the two levels the sample data happens to
  use.
- Dragging the background pans the view (vis-network's default);
  dragging a node moves just that node, and its new position is
  remembered across expand/collapse and across reloading the page.
- Spacebar fits the whole visible map into view (mirrors Simulink's
  fit-to-view convention).
- A node with children is shaded by its own "gap score" — the fraction
  of its leaf descendants that are still just "identified" rather than
  explored — as color intensity within that node's status-color family
  (e.g. a pale vs. a deep amber for two "explored" containers with very
  different amounts of unexplored territory beneath them), rather than
  a separate indicator element.
- A "Preview: empty project" toggle in the top bar shows the empty-state
  card a brand-new study would see, with a "Start first exploration"
  entry point — a real UI element now, not yet wired to anything.

## The exploration-map concept (what the frontend needs to express)

Described by the user as the actual shape of how a study grows:

1. A new project starts one of two ways: the user describes what they
   want to Claude directly, or drops documents into `project_documents/`
   to set scope (see `study/workflow-diagram.md`, diagram 1).
2. From there, the user explores and starts identifying distinct
   **stages** — `calibration-pipeline-tree.md` is a real example of this
   for the calibration project (7 pipeline stages, e.g. Excitation
   Design → Data Acquisition → ... → Output/Integration).
3. Within and across stages, exploration branches two ways: **broad**
   (different approaches to the same problem — e.g. Stage 5's five
   estimation-method candidates) or **deep** (digging further into one
   specific method/topic).
4. Checkpoints and scope can be added or refined continuously, not just
   once at the start.
5. **Decisions taken are tracked on the map itself**: a chosen branch is
   highlighted (green), but every other explored or identified
   alternative stays visible — nothing gets hidden once it's been
   looked at, so the map always shows both the chosen path and the full
   set of alternatives it was chosen from.

This is a more general concept than the calibration example — any study
built from this template should be able to represent the same
stage/branch/decision structure — but `calibration-pipeline-tree.md` is
being used as real sample content while building the frontend, since
`decisions.md` has no logged decisions yet (nothing is really "chosen"
in this project yet; the mockup marks a couple of branches as chosen
purely to demonstrate the highlight styling).

## Milestones page

`study/dashboard/milestones.html` / `milestones.js`. A tree (up to three
levels deep) of milestones, each with a definition, an optional date, a
checkbox, and an "Evaluate progress" button. Same persistence pattern as
the map: everything lives in this browser's `localStorage`
(`milestonesState_v1`).

**"Evaluate progress" does not call Claude yet** — `simulateEvaluate()`
in `milestones.js` reasons only from checkbox state (own + direct
children) as a stand-in, clearly labeled as simulated in the result
panel. What *is* real and meant to carry over unchanged once a real
Claude call exists: each evaluation is stored with a content hash of its
subtree (text/checked/date, recursively); re-clicking "Evaluate" on an
unchanged milestone reuses the stored answer and says so explicitly
("no new Claude call"), rather than regenerating — this is the caching
behavior the user asked for, so a real backend call only needs to
replace `simulateEvaluate()`, not the caching logic around it.

## Gaps page

`study/dashboard/gaps.html` / `gaps.js`. Deliberately **not** a separate
dataset — it reads the same tree as the exploration map (a leaf node
with no children of its own, and status `identified`, i.e. still
unexplored). A sub-branch added on the map, or a node marked "chosen,"
shows up here immediately, since both pages read/write the same
`localStorage` key via the new shared `tree.js`.

- List view (not a graph) — the point of this page is triage/batch
  action across many gaps, which a spatial map doesn't help with.
- Search box, and a toggle to also include "evaluated — not
  favored" leaves (off by default, since those already had a judgment
  made on them, unlike a true unexplored gap).
- Checkbox per row for multi-select, "Select all shown" / "Clear
  selection", and "Explore more on selected (N)" — the user's own
  idea. Clicking it composes a preview of the batch request in the side
  panel (a read-only textarea) rather than doing anything yet, since
  there's still no backend to send it to.
- Clicking a row (not its checkbox) shows that gap's detail plus a
  "View in exploration map" link — `index.html?focus=<id>`, which the
  map now supports: it expands every ancestor of that node and pans to
  it. This is the first real cross-page integration point.
- "Chosen" gaps sort to the top of the list, since an under-explored
  branch that's already the decided path is higher-priority than one
  that isn't being pursued.

This prompted extracting `study/dashboard/tree.js`: the tree-merging
(sample data + user-added sub-branches), `hasChildren`, and `gapScore`
logic used to live only in `app.js`; now both `app.js` and `gaps.js`
call the same `TreeLib` functions against the same storage key, so the
two pages can't drift into disagreeing about the same tree.

## Milestone drag-and-drop and quick actions

Implemented using native HTML5 drag-and-drop on the milestone rows:
dropping in a row's top quarter inserts *before* it, the bottom quarter
inserts *after* it (both as a sibling reorder), and dropping on the
middle nests the dragged milestone *into* it as a child — "like dragging
a file onto a folder," per the user's framing. A drop is rejected
(silently, no state change) if it would drop a node onto itself or one
of its own descendants, or if the moved subtree would push past the
3-level depth cap at its new position (checked via each milestone's own
subtree height, not just its own depth). Dropped milestones bring their
whole subtree with them.

Also added a "+" and a "▶" (evaluate) button directly on each row,
so adding a sub-milestone or evaluating no longer requires selecting the
parent/milestone first and finding the same action inside the side
panel — that two-click pattern was the friction the user pointed out.
Both quick actions still open the side panel (selecting that milestone)
so the result/editor is visible immediately.

## Known bug: milestones page needs a second click (unresolved)

The user reports that on the milestones page, clicking something has no
visible effect until a *different* element is then clicked, at which
point the first click's effect appears. Reproduced only via the user's
report — not yet confirmed directly (no browser automation available
this session; the user declined the Chrome extension for now).

Tried so far, neither fixed it:
1. Suspected the whole `.ms-row` being `draggable="true"` was causing
   the browser to swallow clicks on checkboxes/buttons inside it as
   drag-gesture starts. Fixed by moving `draggable` onto a dedicated
   small handle (`⋮⋮`) instead of the whole row. User confirmed
   this did not fix the issue (though they liked the handle itself).
2. Added a cache-busting `?v=2` query string to `milestones.html`'s
   `style.css`/`milestones.js` includes, in case the browser was
   reusing an already-open tab instead of reloading after edits. Also
   unconfirmed whether this was ever actually the cause.

Static re-reading of every click/change handler in `milestones.js`
(toggle, check, quick-add, quick-eval, the drag handlers, and all of the
side panel's inputs) did not surface a handler that mutates state
without triggering a re-render, which would be the obvious explanation
for "the effect shows up only after a second, unrelated click."

**Next time this is picked up:** get either (a) the exact element and
click sequence that reproduces it, (b) a browser console error/warning
from the moment it happens, or (c) direct browser access (e.g. via the
`claude-in-chrome` extension, if the user enables it) — static reading
of the source has been exhausted without finding the cause.

## Dashboard page

`study/dashboard/dashboard.html`. Originally proposed as a live-data
summary page (milestone progress, gap counts); the user redirected this
— Dashboard is a purely **informational landing page**: what this
tool is, the two ways a study starts, how exploration branches broad vs.
deep, and how the four pages (Map, Gaps, Milestones, Console) relate to
each other. No interactivity, no data pulled from the other pages.

Uses Mermaid (via CDN, `theme: "base"` with warm `themeVariables`
matching the rest of the palette) for two diagrams: the getting-started
flow, and how the four pages connect. This mirrors the root repo's own
"every process gets a diagram" convention from the root `CLAUDE.md`,
just rendered live instead of as a static `.md` fence.

## Not started yet

- Gap browser page
- Paper/topic detail page
- Making the console page, the map's "Explore deeper/broader" and
  "Start first exploration" actions, and milestones' "Evaluate progress"
  actually reach Claude
- The local server itself, and its endpoints
- `study/catalog.json` / `study/gaps.json` / `study/milestones.json`
  schemas
- `study/scripts/lib/` shared module + `study/scripts/cli.py`
- Updating `study/ai_instructions/` to point terminal Claude Code at the
  CLI instead of freehand Markdown/JSON edits
