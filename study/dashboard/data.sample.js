// SAMPLE / PLACEHOLDER DATA — not read from study/catalog.json or
// study/gaps.json because those don't exist yet (see ../../gui-dev-notes.md).
// This is a hand-transcribed snapshot of ../../calibration-pipeline-tree.md,
// used only so the frontend has something real to render while the
// backend and JSON schemas are designed. Nothing here is a logged
// decision — decisions.md has none yet — so no node starts "chosen";
// use the "Mark as chosen" button in the detail panel to preview that
// styling.
//
// Every node shares the same shape: { id, label, kind, description,
// detail, status, source, children }. "kind" is only used for the
// top-level pipeline stages (styled as containers); everything else is
// a plain explorable node that may itself have children — the map
// supports arbitrary nesting depth, and the "Add sub-branch" action in
// the UI adds more of these at runtime (persisted in localStorage, not
// in this file).

const STUDY_DATA = {
  roots: [
    {
      id: "s1", kind: "stage", label: "1. Excitation Design",
      description: "Which motion, for which sensor pair — the maneuver plan that everything downstream depends on.",
      handsOff: "An ordered maneuver plan: which driving pattern, targeting which sensor pair, in what sequence.",
      children: [
        { id: "s1-a", label: "A: Per-pair purpose-built motion", detail: "THEM-style two-phase: rotation pass + translation pass.", status: "explored", source: "01-excitation-design.md", children: [] },
        { id: "s1-b", label: "B: One generic rich drive", detail: "Not tailored per pair, simpler to execute. Not yet compared against A.", status: "identified", source: null, children: [] },
        { id: "s1-c", label: "C: Execution method", detail: "Scripted/autonomous vs. manual driving. Not yet explored.", status: "identified", source: null, children: [] }
      ]
    },
    {
      id: "s2", kind: "stage", label: "2. Data Acquisition & Sync",
      description: "Capture and timestamp raw per-sensor streams.",
      handsOff: "Per-sensor raw streams (point clouds, images, IMU samples, encoder ticks), timestamped, plus sync metadata.",
      children: [
        { id: "s2-a", label: "A: Hardware time sync", detail: "Common trigger / PTP clock. Depends on Toyota hardware — open question, not a literature question.", status: "identified", source: null, children: [] },
        { id: "s2-b", label: "B: Software-estimated time offset", detail: "Per-pair offset becomes its own calibrated state.", status: "explored", source: "02-data-acquisition-sync.md", children: [] }
      ]
    },
    {
      id: "s3", kind: "stage", label: "3. Per-Sensor Preprocessing",
      description: "Per-sensor feature / motion extraction.",
      handsOff: "Per-sensor motion estimates and/or extracted features, time-indexed to a shared reference.",
      children: [
        { id: "s3-lidar", label: "LiDAR odometry", detail: "KISS-ICP / LOAM family / CT-ICP.", status: "explored", source: "03-per-sensor-preprocessing.md", children: [] },
        { id: "s3-camera", label: "Camera feature detection / matching", detail: "Not yet explored — entirely unexplored per the status table.", status: "identified", source: null, children: [] },
        { id: "s3-imu", label: "IMU preintegration", detail: "Shared with the estimation stage's state space.", status: "explored", source: "05-calibration-estimation.md", children: [] },
        { id: "s3-encoder", label: "Encoder odometry", detail: "Tricycle / rear-steer-drive kinematic model.", status: "explored", source: "03-per-sensor-preprocessing.md", children: [] }
      ]
    },
    {
      id: "s4", kind: "stage", label: "4. Correspondence / Association",
      description: "Build residual-ready pairs across sensors.",
      handsOff: "Point correspondences (overlapping FOV) or paired motion-estimate segments (non-overlapping / non-LiDAR).",
      children: [
        { id: "s4-a", label: "A: Direct point cloud registration", detail: "ICP / GICP / NDT / TEASER++. Needs FOV overlap.", status: "explored", source: "04-correspondence-association.md", children: [] },
        { id: "s4-b", label: "B: Motion comparison (hand-eye)", detail: "No FOV overlap needed.", status: "explored", source: "04-correspondence-association.md", children: [] },
        { id: "s4-c", label: "C: Learned / cross-modal feature matching", detail: "One catalog paper flagged, not synthesized into the map yet.", status: "identified", source: null, children: [] }
      ]
    },
    {
      id: "s5", kind: "stage", label: "5. Calibration Estimation",
      description: "Solve for calibration parameters. The furthest-along stage — has its own deep-dive document.",
      handsOff: "The calibration parameter estimate plus its uncertainty/covariance, ideally per-DOF.",
      children: [
        { id: "s5-a", label: "A: EKF / UKF", detail: "Real-time capable, single-pass linearization. Evaluated — not favored, since this project has no real-time need.", status: "evaluated-not-favored", source: null, children: [] },
        { id: "s5-b", label: "B: Particle filter", detail: "No literature support found either way.", status: "identified", source: null, children: [] },
        { id: "s5-c", label: "C: Batch nonlinear least squares", detail: "Most accurate, solved once over all data (Rehder et al.). Same underlying math as D — see the deep-dive.", status: "explored", source: "05-calibration-estimation.md", children: [] },
        { id: "s5-d", label: "D: Incremental factor graph", detail: "Jointly re-optimized as each pair is added. Has its own deep-dive.", status: "explored", source: "05-calibration-estimation.md", children: [] },
        { id: "s5-e", label: "E: Strictly sequential pairwise", detail: "Freeze-then-chain. Known compounding-error failure mode — weakness identified, not excluded.", status: "explored", source: "05-calibration-estimation.md", children: [] }
      ]
    },
    {
      id: "s6", kind: "stage", label: "6. Validation",
      description: "Assess calibration quality. The most consequential gap — no fallback exists per unit if the no-ground-truth approach doesn't pan out.",
      handsOff: "Parameters annotated with a pass/fail or confidence judgment.",
      children: [
        { id: "s6-a", label: "A: No-ground-truth consistency check", detail: "REQUIRED per unit — no fallback exists. Seven candidate mechanisms (A1-A7).", status: "explored", source: "06-validation.md", children: [] },
        { id: "s6-b", label: "B: Semantic-feature cross-check", detail: "Usable per unit (Das et al.) — a special case of A3.", status: "explored", source: "06-validation.md", children: [] },
        { id: "s6-c", label: "C: Compare against CAD / design priors", detail: "Method validation only, never per unit.", status: "identified", source: null, children: [] },
        { id: "s6-d", label: "D: Compare against Toyota's reference calibration", detail: "Method validation only, never per unit.", status: "identified", source: null, children: [] },
        { id: "s6-e", label: "E: Independent validation drive", detail: "Usable per unit — partially explored, scored alongside A1-A4.", status: "explored", source: "06-validation.md", children: [] },
        { id: "s6-f", label: "F: Learned miscalibration classifier", detail: "Usable per unit, training needs a reference (Tahiraj et al. x2) — an actual accept/reject gate.", status: "explored", source: "06-validation.md", children: [] }
      ]
    },
    {
      id: "s7", kind: "stage", label: "7. Output / Integration",
      description: "Produce the final artifact. Least literature-dependent stage — mostly engineering/process design.",
      handsOff: "A calibration file/config the navigation stack actually consumes.",
      children: [
        { id: "s7-a", label: "A: Static config file", detail: "Extrinsics + encoder params.", status: "identified", source: null, children: [] },
        { id: "s7-b", label: "B: Per-DOF confidence alongside point estimates", detail: "Not yet explored.", status: "identified", source: null, children: [] },
        { id: "s7-c", label: "C: Versioning / audit trail", detail: "Which excitation drives contributed, when. Not yet explored.", status: "identified", source: null, children: [] }
      ]
    }
  ]
};
