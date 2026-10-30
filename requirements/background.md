> **Status: unverified background notes.** Gathered on 2026-10-30 from web search
> summaries; **none of the sources below was read in full**, and most are secondary
> descriptions of a standard, not the standard. Treat this as a map of where to
> look, not as authority. Nothing here is a requirement or a decision.

# Requirements: background and prior practice

What is known about how requirements are written and managed, collected as input
for designing this module per project type later. Nothing is copied from any
source: each entry says in our own words what the source is for and what to check
before relying on it.

## Why requirements are staged and allowed to be unknown

- **Feasibility is part of what makes a requirement good.** ISO/IEC/IEEE 29148
  lists characteristics of a good individual requirement, among them necessary,
  unambiguous, verifiable and feasible; feasible means realizable within the
  constraints at acceptable risk [1]. Feasibility cannot be judged before the
  concept is understood, which is the argument for not fixing low-level numbers
  early.
- **Unknowns are recorded, not guessed.** Systems-engineering practice marks an
  unknown value `TBD` (to be determined) or `TBR` (to be resolved), requires a
  closure plan for each, and ties the plan to a project phase [2]. This is the
  basis for treating `TBD` as a normal state.
- **The list stays alive.** As secondary sources describe the Pahl and Beitz
  method, the requirements list is the central output of task clarification and
  is maintained throughout the project, because knowledge of the requirements
  grows with knowledge of the problem [3][4]. Each entry is recorded with a name,
  a characteristic, a form, a responsibility and a date, and requirements are
  classed as *demands* (compulsory) or *wishes* (not compulsory) [3][4].
- **Early solution ideas have a home that is not a requirement.** The Volere
  template groups project drivers and mandated constraints ahead of the
  requirements themselves, and has sections for ideas for solutions and for items
  deferred to later [5].

## Writing a good requirement statement

- The INCOSE Guide to Writing Requirements ties characteristics of single
  statements and of requirement *sets* to a list of rules; the free summary sheet
  is the accessible entry point, the full guide is sold [6]. Use it as a checklist
  for wording (one statement, no solution, verifiable), once the module has
  templates to apply it to.

## How project types differ

These are descriptions of what each type tends to cover, as prompts for the
per-type design. They are not templates.

**Software.** A requirements specification typically separates functional from
non-functional requirements and adds external interfaces. A public-domain (CC0)
Markdown template aligned with IEEE 830 and ISO/IEC/IEEE 29148 exists and is a
reasonable base for a version-controlled specification [7]. Non-functional
requirements are commonly organized by the ISO 25010 quality model; the names of
its characteristics were **not verified** here.

**Control systems.** Specifications typically cover time-domain behaviour
(settling time, overshoot), stability margins (gain and phase margin), and
robustness. Tooling treats settling time and overshoot as bounds that are exact
only for a second-order system and approximate for higher orders [8]. Bounds on
the peaks of the sensitivity and complementary-sensitivity functions are a common
way to state robustness, with the point that margins alone may fail to bound
those peaks; lecture notes give peak limits as *typical* values, not universal
ones [9]. High-frequency limits for noise and for actuator effort usually belong
too; that is standard control practice but **was not confirmed** by the sources
found.

**State estimation.** The aviation-navigation vocabulary is a useful starting
point: accuracy, integrity (the ability to warn when the output should not be
used), continuity, and availability (the fraction of time all three hold), and
time to first fix for initialization [10]. Accuracy against truth cannot be
measured in operation, which is why a bound on the error, such as a protection
level, is used instead [10]. Filter *consistency* is commonly checked with the
normalized estimation error squared (NEES, needs ground truth) and the normalized
innovation squared (NIS, does not); the average NEES of a well-tuned filter
should be close to the state dimension, and passing such tests alone does not
prove a filter is tuned [11]. Observability conditions, initialization
requirements and degraded-mode behaviour were **not found** in the searches and
need their own sourcing.

**Mechanical development.** The Pahl and Beitz requirements list is the model
(see above), and general-purpose requirements checklists exist to check a design
specification for completeness against it [12]. The checklist's own headings were
**not retrieved**; check the book or [12] before listing categories.

## Licensing notes

- The Volere template is copyrighted and is free only for some uses [5]. Use its
  *idea* of grouping, in our own words; do not copy its text into a fork.
- ISO/IEC/IEEE 29148 and IEEE 830 are paid standards [1][7]. Nothing from their
  text belongs in the template.
- The SRS Markdown template in [7] is stated to be CC0 (public domain). Check the
  repository's licence file before copying from it.
- The NASA systems engineering handbook and procedural requirements are US
  government documents, but only a secondary page citing them was seen [2].

## Open questions for the per-type design

Left open on purpose, to be settled from real use:

- Which types ship a template first, and what each one asks for.
- Whether a requirement should name the decision-tree question it depends on, so
  the validator can warn when that question is still undecided.
- How a requirement's basis is recorded (a small fixed vocabulary, or free text
  with a citation), and whether a weakest-basis audit is worth its cost.
- How `TBD` entries are collected into one register, and whether their resolve-by
  milestones are checked against `../timeline.md`.
- Whether requirements need tiers per milestone, or whether staging plus `TBD`
  covers it.
- What an accepted requirement looks like in the file, and how acceptance is
  recorded.

## References

[1] ISO/IEC/IEEE 29148 characteristics, as described in: *Leveraging LLMs for the
Quality Assurance of Software Requirements*. https://arxiv.org/pdf/2408.10886
(secondary description of the standard)

[2] Aerospace Corporation Mission Assurance Guide, "Space Segment Systems
Engineering", on closure plans for TBD/TBR requirements citing the NASA Systems
Engineering Handbook. https://mab.aerospace.org/lvl2/4_2_4.2-3 (secondary)

[3] Methods wiki, "Requirements quantification through requirements list"
(summarizing Pahl and Beitz and VDI 2221). https://methods.mywikis.eu/wiki/Requirements_quantification_through_requirements_list
(secondary; primary source: Pahl, Beitz et al., *Engineering Design: A Systematic
Approach*, 3rd ed., Springer, 2007)

[4] Product requirements specification process in product development,
Proceedings of the Design Society (Cambridge Core).
https://www.cambridge.org/core/journals/proceedings-of-the-design-society/article/product-requirements-specification-process-in-product-development/8A6CE2DA5FEAFB211EDB878416546D6E
(secondary on Pahl and Beitz's requirements list)

[5] Volere Requirements Specification Template, overview.
https://www.modernrequirements.com/blogs/volere-requirements-specification-template/
(secondary; copyrighted template)

[6] INCOSE, Guide to Writing Requirements v4 summary sheet.
https://www.incose.org/docs/default-source/working-groups/requirements-wg/guidetowritingrequirements/incose_rwg_gtwr_v4_summary_sheet.pdf

[7] SRS Template (Markdown, aligned with IEEE 830 and ISO/IEC/IEEE 29148).
https://github.com/jam01/SRS-Template

[8] MathWorks, "Design Requirements" (Control System Toolbox documentation).
https://www.mathworks.com/help/control/ug/design-requirements.html

[9] Lecture notes on sensitivity and complementary sensitivity peaks.
https://www.lehigh.edu/~eus204/teaching/ME450_MRC/lectures/lecture02.pdf

[10] ESA Navipedia, "GNSS Performances" (accuracy, integrity, continuity,
availability, time to first fix). https://gssc.esa.int/navipedia/index.php/GNSS_Performances

[11] "Normalized estimation error squared" and related pages on consistency tests.
https://kalman-filter.com/normalized-estimation-error-squared

[12] Becattini, Cascini, Rotini, "General purpose requirements checklist for
improving the completeness of a design specification", Design Society (ICED).
https://www.designsociety.org/download-publication/35156/general-purpose_requirements_checklist_for_improving_the_completeness_of_a_design_specification
