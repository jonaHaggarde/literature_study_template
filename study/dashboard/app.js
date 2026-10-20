// Frontend-only exploration map. No network calls, no backend, no Claude
// invocation anywhere in this file — see ../../gui-dev-notes.md for what's
// intentionally not built yet. All state (expand/collapse, dragged
// positions, "chosen" marks, user-added sub-branches) is persisted only
// in this browser's localStorage, keyed per this page — nothing here
// reaches a server.

const X_GAP = 190, LEVEL_GAP = 110, STAGE_GAP = 60;

const BASE_COLORS = { // flat colors for leaf nodes (no children of their own)
  explored: { background: "#f7e7c4", border: "#c08a2e" },
  identified: { background: "#f0e9dd", border: "#b8a98f" },
  "evaluated-not-favored": { background: "#f3dcd3", border: "#a24e36" },
  chosen: { background: "#dce8c8", border: "#6e8048" }
};

// Low-gap / high-gap endpoints used to shade any node that HAS children,
// based on the fraction of its leaf descendants still just "identified".
const GAP_SCALE = {
  stage:      { lowBg: "#f3ead6", highBg: "#c9a25c", lowBorder: "#cbb896", highBorder: "#71542c" },
  explored:   { lowBg: "#fbf3df", highBg: "#e0a53a", lowBorder: "#d8c48f", highBorder: "#a06f18" },
  identified: { lowBg: "#f6f1e8", highBg: "#d8c7a8", lowBorder: "#cfc3ab", highBorder: "#9c8862" },
  "evaluated-not-favored": { lowBg: "#f8e9e3", highBg: "#dba38f", lowBorder: "#dbb7a8", highBorder: "#8f4128" }
};

const STATUS_LABEL = {
  explored: "Explored",
  identified: "Identified, not yet explored",
  "evaluated-not-favored": "Evaluated — not favored"
};

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function rgbToHex(r, g, b) {
  return "#" + [r, g, b].map(v => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("");
}
function lerpHex(a, b, t) {
  const [r1, g1, b1] = hexToRgb(a), [r2, g2, b2] = hexToRgb(b);
  return rgbToHex(r1 + (r2 - r1) * t, g1 + (g2 - g1) * t, b1 + (b2 - b1) * t);
}
function genId() {
  return "custom-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
}

// ---- persisted state (shared with gaps.js via tree.js) -----------------

const state = TreeLib.loadState();
function saveState() { TreeLib.saveState(state); }
function getWorkingRoots() { return TreeLib.getWorkingRoots(STUDY_DATA, state.customChildren); }
function hasChildren(node) { return TreeLib.hasChildren(node); }
function gapScore(node) { return TreeLib.gapScore(node); }

function colorForNode(node) {
  if (state.chosen.has(node.id)) return BASE_COLORS.chosen;
  if (hasChildren(node)) {
    const scale = GAP_SCALE[node.kind === "stage" ? "stage" : node.status] || GAP_SCALE.identified;
    const score = gapScore(node) || 0;
    return {
      background: lerpHex(scale.lowBg, scale.highBg, score),
      border: lerpHex(scale.lowBorder, scale.highBorder, score)
    };
  }
  return BASE_COLORS[node.status] || BASE_COLORS.identified;
}

function isVisible(node, index) {
  if (node._depth === 0) return true;
  const parent = index.get(node._parentId);
  if (!parent) return true;
  return state.expanded.has(parent.id) && isVisible(parent, index);
}

// ---- layout: computed once per rebuild, only used when no saved position exists ----

function layoutRoots(roots) {
  let baseY = 0;
  roots.forEach(root => {
    let slotCounter = 0;
    (function assignSlots(node, depth, parentId) {
      node._depth = depth;
      node._parentId = parentId;
      if (!hasChildren(node)) { node._slot = slotCounter++; return; }
      node.children.forEach(c => assignSlots(c, depth + 1, node.id));
      const slots = node.children.map(c => c._slot);
      node._slot = (Math.min(...slots) + Math.max(...slots)) / 2;
    })(root, 0, null);

    function maxDepth(node) {
      return hasChildren(node) ? 1 + Math.max(...node.children.map(maxDepth)) : 0;
    }
    const depth = maxDepth(root);

    (function place(node) {
      node._defaultX = node._slot * X_GAP;
      node._defaultY = baseY + node._depth * LEVEL_GAP;
      (node.children || []).forEach(place);
    })(root);

    baseY += (depth + 1) * LEVEL_GAP + STAGE_GAP;
  });
}

// ---- graph build / rebuild --------------------------------------------

const nodesDS = new vis.DataSet();
const edgesDS = new vis.DataSet();
let NODE_INDEX = new Map();

function labelFor(node) {
  if (!hasChildren(node)) return node.label;
  return (state.expanded.has(node.id) ? "▾ " : "▸ ") + node.label;
}

function rebuild(preserveSelection) {
  const roots = getWorkingRoots();
  layoutRoots(roots);

  NODE_INDEX = new Map();
  function index(node) { NODE_INDEX.set(node.id, node); (node.children || []).forEach(index); }
  roots.forEach(index);

  nodesDS.clear();
  edgesDS.clear();

  NODE_INDEX.forEach(node => {
    const pos = state.positions[node.id];
    const col = colorForNode(node);
    const isStage = node.kind === "stage";
    nodesDS.add({
      id: node.id,
      label: labelFor(node),
      x: pos ? pos.x : node._defaultX,
      y: pos ? pos.y : node._defaultY,
      shape: "box",
      shapeProperties: { borderRadius: isStage ? 6 : 10 },
      margin: isStage ? 10 : 8,
      font: { face: "Segoe UI", size: isStage ? 15 : 12, color: "#3a2e22" },
      color: { background: col.background, border: col.border, highlight: col },
      borderWidth: isStage ? 1.5 : (node.status === "identified" ? 1 : 1.5),
      borderWidthSelected: 2.5,
      hidden: !isVisible(node, NODE_INDEX),
      raw: node
    });
    if (node._parentId) {
      edgesDS.add({
        from: node._parentId, to: node.id,
        arrows: "", dashes: true, color: { color: "#ddcdaf" }, width: 1
      });
    }
  });

  // stage sequence edges
  for (let i = 1; i < roots.length; i++) {
    edgesDS.add({ from: roots[i - 1].id, to: roots[i].id, arrows: "to", color: { color: "#c9b79c" }, width: 2 });
  }

  if (preserveSelection) {
    const node = NODE_INDEX.get(preserveSelection);
    if (node) renderPanel(node); else renderDefaultPanel();
  }
}

const container = document.getElementById("map");
const panel = document.getElementById("panel");
const network = new vis.Network(container, { nodes: nodesDS, edges: edgesDS }, {
  layout: { hierarchical: { enabled: false } },
  physics: false,
  interaction: { hover: true, dragNodes: true, dragView: true },
  edges: { smooth: { type: "cubicBezier", forceDirection: "vertical", roundness: 0.6 } }
});

rebuild();
network.fit();
renderDefaultPanel();

// If arriving from the gaps browser as index.html?focus=<id>, expand
// every ancestor of that node and pan to it.
(function focusOnQueryParam() {
  const focusId = new URLSearchParams(location.search).get("focus");
  if (!focusId) return;
  let cur = NODE_INDEX.get(focusId);
  if (!cur) return;
  while (cur._parentId) {
    state.expanded.add(cur._parentId);
    cur = NODE_INDEX.get(cur._parentId);
  }
  saveState();
  rebuild(focusId);
  network.selectNodes([focusId]);
  network.focus(focusId, { scale: 1, animation: { duration: 400 } });
})();

// Dragging a node also drags everything beneath it in the tree, keeping
// each child's position relative to its parent.
function collectDescendantIds(node, out) {
  (node.children || []).forEach(c => { out.push(c.id); collectDescendantIds(c, out); });
  return out;
}

let dragCtx = null;

network.on("dragStart", params => {
  if (params.nodes.length !== 1) return;
  const node = NODE_INDEX.get(params.nodes[0]);
  if (!node) return;
  const descIds = collectDescendantIds(node, []);
  dragCtx = { id: node.id, descIds, startPositions: network.getPositions([node.id, ...descIds]) };
});

network.on("dragging", () => {
  if (!dragCtx) return;
  const cur = network.getPositions([dragCtx.id])[dragCtx.id];
  const start = dragCtx.startPositions[dragCtx.id];
  const dx = cur.x - start.x, dy = cur.y - start.y;
  dragCtx.descIds.forEach(id => {
    const s = dragCtx.startPositions[id];
    nodesDS.update({ id, x: s.x + dx, y: s.y + dy });
  });
});

network.on("dragEnd", () => {
  if (!dragCtx) return;
  const allIds = [dragCtx.id, ...dragCtx.descIds];
  const finalPositions = network.getPositions(allIds);
  allIds.forEach(id => { state.positions[id] = { x: finalPositions[id].x, y: finalPositions[id].y }; });
  saveState();
  dragCtx = null;
});

// ---- spacebar = fit view ------------------------------------------------

document.addEventListener("keydown", e => {
  const t = e.target;
  const typing = t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);
  if (e.code === "Space" && !typing) {
    e.preventDefault();
    network.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });
  }
});

// ---- side panel ----------------------------------------------------------

function renderDefaultPanel() {
  panel.innerHTML = `
    <h2>Exploration map</h2>
    <p class="hint">
      Click a node to see its details. Nodes with children can be
      expanded/collapsed by clicking them. Drag any node to rearrange it —
      its position is remembered. Press <strong>spacebar</strong> to fit
      the whole map in view.
    </p>
    <p class="hint">
      Sample data transcribed from <code>calibration-pipeline-tree.md</code>
      — nothing here is wired to <code>study/catalog.json</code> or
      <code>study/gaps.json</code> yet (neither file exists yet).
    </p>`;
}

function gapReadout(node) {
  const score = gapScore(node);
  if (score === null) return "";
  return `<p class="detail-source"><strong>Gap:</strong> ${Math.round(score * 100)}% of this node's branches are still just identified, not explored — reflected in how deep the fill color is.</p>`;
}

function addSubBranchForm(node) {
  return `
    <button class="action" id="addBtn">+ Add sub-branch</button>
    <div id="addForm" style="display:none; margin-top:8px;">
      <input type="text" id="newLabel" placeholder="Label" style="width:100%; margin-bottom:6px; padding:6px; border-radius:6px; border:1px solid var(--panel-border); font-family:inherit;">
      <textarea id="newDetail" placeholder="Detail / notes" style="width:100%; height:54px; margin-bottom:6px; padding:6px; border-radius:6px; border:1px solid var(--panel-border); font-family:inherit;"></textarea>
      <select id="newStatus" style="width:100%; margin-bottom:6px; padding:6px; border-radius:6px; border:1px solid var(--panel-border); font-family:inherit;">
        <option value="identified">Identified, not yet explored</option>
        <option value="explored">Explored</option>
        <option value="evaluated-not-favored">Evaluated — not favored</option>
      </select>
      <div style="display:flex; gap:8px;">
        <button class="action" id="saveAddBtn">Save</button>
        <button class="action" id="cancelAddBtn">Cancel</button>
      </div>
    </div>`;
}

function wireAddSubBranchForm(node) {
  const addBtn = document.getElementById("addBtn");
  const form = document.getElementById("addForm");
  addBtn.onclick = () => { form.style.display = "block"; addBtn.style.display = "none"; };
  document.getElementById("cancelAddBtn").onclick = () => { form.style.display = "none"; addBtn.style.display = "block"; };
  document.getElementById("saveAddBtn").onclick = () => {
    const label = document.getElementById("newLabel").value.trim();
    if (!label) return;
    const detail = document.getElementById("newDetail").value.trim();
    const status = document.getElementById("newStatus").value;
    const child = { id: genId(), label, detail, status, source: null, children: [] };
    if (!state.customChildren[node.id]) state.customChildren[node.id] = [];
    state.customChildren[node.id].push(child);
    state.expanded.add(node.id);
    saveState();
    rebuild(node.id);
  };
}

function renderPanel(node) {
  const isStage = node.kind === "stage";
  const isChosen = state.chosen.has(node.id);
  const canExpand = hasChildren(node);

  let html = `<h2>${node.label}</h2>`;

  if (isStage) {
    html += `<p class="detail-desc">${node.description}</p>
      <p class="detail-source"><strong>Hands off downstream:</strong> ${node.handsOff}</p>`;
  } else {
    const pillClass = isChosen ? "chosen" : node.status;
    const pillText = isChosen ? "Chosen" : STATUS_LABEL[node.status];
    html += `<span class="status-pill ${pillClass}">${pillText}</span>
      <p class="detail-desc">${node.detail || ""}</p>
      <p class="detail-source">${node.source ? "Deep-dive: " + node.source : "No deep-dive document yet."}</p>`;
  }

  html += gapReadout(node);
  html += `<div class="action-row">`;
  if (canExpand) {
    html += `<button class="action" id="toggleBtn">${state.expanded.has(node.id) ? "Collapse branches" : "Expand branches"}</button>`;
  }
  if (!isStage) {
    html += `<button class="action ${isChosen ? "chosen-on" : ""}" id="chosenBtn">
        ${isChosen ? "✓ Marked as chosen — click to unmark" : "Mark as chosen"}
      </button>
      <button class="action disabled" id="deepBtn">Explore deeper (new study)</button>
      <button class="action disabled" id="broadBtn">Explore broader (new study)</button>
      <p class="disabled-note">
        These will launch a Claude study once the local server exists —
        not wired up yet, by design (see ../../gui-dev-notes.md).
      </p>`;
  }
  html += addSubBranchForm(node);
  html += `</div>`;

  panel.innerHTML = html;

  if (canExpand) {
    document.getElementById("toggleBtn").onclick = () => {
      if (state.expanded.has(node.id)) state.expanded.delete(node.id); else state.expanded.add(node.id);
      saveState();
      rebuild(node.id);
    };
  }
  if (!isStage) {
    document.getElementById("chosenBtn").onclick = () => {
      if (isChosen) state.chosen.delete(node.id); else state.chosen.add(node.id);
      saveState();
      rebuild(node.id);
    };
  }
  wireAddSubBranchForm(node);
}

network.on("click", params => {
  if (params.nodes.length === 0) return; // keep whatever panel is open; background click only pans
  const node = NODE_INDEX.get(params.nodes[0]);
  renderPanel(node);
});

// ---- empty-project preview ----------------------------------------------

const emptyState = document.getElementById("emptyState");
const previewBtn = document.getElementById("previewEmptyBtn");
let previewingEmpty = false;

previewBtn.onclick = () => {
  previewingEmpty = !previewingEmpty;
  emptyState.style.display = previewingEmpty ? "flex" : "none";
  document.getElementById("map").style.visibility = previewingEmpty ? "hidden" : "visible";
  previewBtn.textContent = previewingEmpty ? "Back to map" : "Preview: empty project";
};

document.getElementById("startExplorationBtn").onclick = () => {
  document.getElementById("startExplorationForm").style.display = "block";
  document.getElementById("startExplorationBtn").style.display = "none";
};
