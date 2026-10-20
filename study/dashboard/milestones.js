// Milestones page. Frontend-only, like the exploration map: everything
// persists in this browser's localStorage under "milestonesState_v1".
// "Evaluate progress" does NOT call Claude yet — simulateEvaluate()
// below is a stand-in that reasons only from checkbox state, clearly
// labeled as simulated. What IS real here is the caching contract: a
// content hash is stored alongside each evaluation, and re-clicking
// "Evaluate" on an unchanged milestone reuses the stored answer instead
// of generating (later: calling Claude) again — swap simulateEvaluate()
// for a real fetch() to the local server once it exists and the caching
// behavior around it needs no changes.

const STORAGE_KEY = "milestonesState_v1";
const MAX_DEPTH = 2; // depths 0, 1, 2 => three levels

function genId() {
  return "ms-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 7);
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function hashStr(s) {
  let h = 5381;
  for (let i = 0; i < s.length; i++) { h = ((h << 5) + h) + s.charCodeAt(i); h |= 0; }
  return h.toString(36);
}
function subtreeSnapshot(node) {
  return { text: node.text, checked: node.checked, date: node.date, children: (node.children || []).map(subtreeSnapshot) };
}
function contentHash(node) {
  return hashStr(JSON.stringify(subtreeSnapshot(node)));
}

// ---- persisted state ----------------------------------------------------

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) throw new Error("empty");
    const parsed = JSON.parse(raw);
    return { milestones: parsed.milestones || [], collapsed: new Set(parsed.collapsed || []) };
  } catch (e) {
    return { milestones: [], collapsed: new Set() };
  }
}

const state = loadState();
let selectedId = null;
let MS_INDEX = new Map();

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({ milestones: state.milestones, collapsed: [...state.collapsed] }));
}

function indexTree(list, depth, parent) {
  list.forEach(n => {
    n._depth = depth;
    n._parent = parent;
    MS_INDEX.set(n.id, n);
    indexTree(n.children || [], depth + 1, n);
  });
}

// ---- simulated evaluation -------------------------------------------------

function simulateEvaluate(node) {
  if (node.checked) {
    return { verdict: "done", summary: "Marked complete directly.", remaining: "Nothing — already checked off." };
  }
  const kids = node.children || [];
  if (kids.length === 0) {
    return {
      verdict: "not-started",
      summary: "No sub-milestones defined and not marked complete yet.",
      remaining: "Mark it complete once it's done, or break it into sub-milestones first."
    };
  }
  const doneCount = kids.filter(k => k.checked).length;
  if (doneCount === kids.length) {
    return { verdict: "done", summary: `All ${kids.length} sub-milestone(s) are checked off.`, remaining: "Confirm and check off this milestone itself." };
  }
  if (doneCount === 0) {
    return { verdict: "not-started", summary: `None of the ${kids.length} sub-milestone(s) are checked off yet.`, remaining: kids.map(k => k.text).join("; ") };
  }
  return {
    verdict: "in-progress",
    summary: `${doneCount} of ${kids.length} sub-milestone(s) checked off.`,
    remaining: kids.filter(k => !k.checked).map(k => k.text).join("; ")
  };
}

function subtreeHeight(node) {
  const kids = node.children || [];
  return kids.length === 0 ? 0 : 1 + Math.max(...kids.map(subtreeHeight));
}

function verdictClass(v) { return v === "done" ? "chosen" : v === "in-progress" ? "explored" : "identified"; }
function verdictLabel(v) { return v === "done" ? "Done" : v === "in-progress" ? "In progress" : "Not started"; }

function evaluate(node) {
  const hash = contentHash(node);
  if (node.evaluation && node.evaluation.hash === hash) {
    renderEvalResult(node, "cache-hit");
    return;
  }
  const result = simulateEvaluate(node);
  node.evaluation = Object.assign({ hash, at: new Date().toISOString() }, result);
  saveState();
  renderEvalResult(node, "new");
}

// ---- tree rendering -------------------------------------------------------

const msTree = document.getElementById("msTree");
const panel = document.getElementById("panel");

function renderNode(node) {
  const hasKids = node.children && node.children.length > 0;
  const expanded = !state.collapsed.has(node.id);
  let html = `<div class="ms-row ${selectedId === node.id ? "selected" : ""}" data-id="${node.id}">`;
  html += `<span class="ms-drag-handle" draggable="true" title="Drag to reorder or nest">⋮⋮</span>`;
  html += `<span class="ms-toggle" data-action="toggle">${hasKids ? (expanded ? "▾" : "▸") : ""}</span>`;
  html += `<input type="checkbox" class="ms-check" data-action="check" ${node.checked ? "checked" : ""}>`;
  html += `<span class="ms-text" data-action="select">${escapeHtml(node.text)}</span>`;
  if (node.date) html += `<span class="ms-date-badge">${escapeHtml(node.date)}</span>`;
  if (node._depth < MAX_DEPTH) html += `<button class="ms-quick-btn" data-action="quick-add" title="Add sub-milestone">+</button>`;
  html += `<button class="ms-quick-btn" data-action="quick-eval" title="Evaluate progress">▶</button>`;
  html += `</div>`;
  if (hasKids && expanded) {
    html += `<div class="ms-children">` + node.children.map(renderNode).join("") + `</div>`;
  }
  return html;
}

function render() {
  MS_INDEX = new Map();
  indexTree(state.milestones, 0, null);

  msTree.innerHTML = state.milestones.length
    ? state.milestones.map(renderNode).join("")
    : `<p class="hint">No milestones yet. These can be defined early — e.g. while scoping from <code>project_documents/</code> — or added continuously as the project grows. Click "+ Add milestone" to create the first one.</p>`;

  if (selectedId && MS_INDEX.has(selectedId)) renderPanel(MS_INDEX.get(selectedId));
  else { selectedId = null; renderDefaultPanel(); }
}

msTree.addEventListener("click", e => {
  const row = e.target.closest(".ms-row");
  if (!row) return;
  const id = row.dataset.id;
  const action = e.target.dataset.action;
  if (action === "toggle") {
    if (state.collapsed.has(id)) state.collapsed.delete(id); else state.collapsed.add(id);
    saveState(); render();
    return;
  }
  if (action === "check") {
    MS_INDEX.get(id).checked = e.target.checked;
    saveState(); render();
    return;
  }
  if (action === "quick-add") {
    const parent = MS_INDEX.get(id);
    const child = { id: genId(), text: "New milestone", checked: false, date: null, children: [], evaluation: null };
    parent.children = parent.children || [];
    parent.children.push(child);
    state.collapsed.delete(parent.id);
    selectedId = child.id;
    saveState(); render();
    return;
  }
  if (action === "quick-eval") {
    const node = MS_INDEX.get(id);
    selectedId = id;
    render();
    evaluate(node);
    return;
  }
  selectedId = id;
  render();
});

// ---- drag to reorder / drag onto another to nest -------------------------

function isSelfOrDescendant(ancestorId, targetId) {
  let node = MS_INDEX.get(targetId);
  while (node) {
    if (node.id === ancestorId) return true;
    node = node._parent;
  }
  return false;
}

function clearDropIndicators() {
  msTree.querySelectorAll(".drop-before, .drop-after, .drop-nest").forEach(el => {
    el.classList.remove("drop-before", "drop-after", "drop-nest");
  });
}

function dropModeFor(e, row) {
  const rect = row.getBoundingClientRect();
  const offset = (e.clientY - rect.top) / rect.height;
  return offset < 0.25 ? "before" : offset > 0.75 ? "after" : "nest";
}

let dragId = null;

msTree.addEventListener("dragstart", e => {
  const row = e.target.closest(".ms-row");
  if (!row) return;
  dragId = row.dataset.id;
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData("text/plain", dragId);
});

msTree.addEventListener("dragover", e => {
  const row = e.target.closest(".ms-row");
  if (!row || !dragId) return;
  e.preventDefault();
  clearDropIndicators();
  const targetId = row.dataset.id;
  if (isSelfOrDescendant(dragId, targetId)) return;
  row.classList.add("drop-" + dropModeFor(e, row));
});

msTree.addEventListener("drop", e => {
  const row = e.target.closest(".ms-row");
  clearDropIndicators();
  if (!row || !dragId) { dragId = null; return; }
  e.preventDefault();
  const targetId = row.dataset.id;
  if (!isSelfOrDescendant(dragId, targetId)) {
    performDrop(dragId, targetId, dropModeFor(e, row));
  }
  dragId = null;
});

msTree.addEventListener("dragend", () => { dragId = null; clearDropIndicators(); });

function performDrop(draggedId, targetId, mode) {
  const draggedNode = MS_INDEX.get(draggedId);
  const targetNode = MS_INDEX.get(targetId);
  if (!draggedNode || !targetNode) return;

  const newDepth = mode === "nest" ? targetNode._depth + 1 : targetNode._depth;
  if (newDepth + subtreeHeight(draggedNode) > MAX_DEPTH) return; // would exceed 3 levels

  const oldArr = draggedNode._parent ? draggedNode._parent.children : state.milestones;
  const oldIdx = oldArr.findIndex(n => n.id === draggedId);
  if (oldIdx === -1) return;
  oldArr.splice(oldIdx, 1);

  if (mode === "nest") {
    targetNode.children = targetNode.children || [];
    targetNode.children.push(draggedNode);
    state.collapsed.delete(targetNode.id);
  } else {
    const newArr = targetNode._parent ? targetNode._parent.children : state.milestones;
    let idx = newArr.findIndex(n => n.id === targetId);
    if (mode === "after") idx += 1;
    newArr.splice(idx, 0, draggedNode);
  }

  saveState();
  render();
}

document.getElementById("addRootBtn").onclick = () => {
  const node = { id: genId(), text: "New milestone", checked: false, date: null, children: [], evaluation: null };
  state.milestones.push(node);
  selectedId = node.id;
  saveState(); render();
};

// ---- side panel -------------------------------------------------------

function renderDefaultPanel() {
  panel.innerHTML = `
    <h2>Milestones</h2>
    <p class="hint">
      Click a milestone in the list to edit its definition, set an
      optional date, mark it complete, or evaluate progress. Milestones
      can be nested up to three levels deep.
    </p>`;
}

function renderEvalResult(node, source) {
  const box = document.getElementById("msEvalResult");
  if (!box) return;
  const ev = node.evaluation;
  if (!ev) { box.innerHTML = ""; return; }
  const sourceNote = source === "cache-hit"
    ? "No new Claude call — nothing has changed since the last evaluation, so the stored answer is shown."
    : source === "new"
      ? "Simulated response — will be a real Claude call once the local server exists."
      : "Last evaluation, loaded from storage.";
  box.innerHTML = `
    <div class="ms-eval-box">
      <span class="status-pill ${verdictClass(ev.verdict)}">${verdictLabel(ev.verdict)}</span>
      <p class="detail-desc">${escapeHtml(ev.summary)}</p>
      <p class="detail-desc"><strong>Remaining:</strong> ${escapeHtml(ev.remaining)}</p>
      <p class="detail-source">${new Date(ev.at).toLocaleString()} — ${sourceNote}</p>
    </div>`;
}

function renderPanel(node) {
  const canAddChild = node._depth < MAX_DEPTH;
  panel.innerHTML = `
    <h2>Milestone</h2>
    <textarea id="msTextInput" class="ms-edit-text" placeholder="Definition...">${escapeHtml(node.text)}</textarea>
    <div class="ms-panel-row">
      <label class="ms-check-label"><input type="checkbox" id="msCheckInput" ${node.checked ? "checked" : ""}> Completed</label>
      <span class="hint">Level ${node._depth + 1} of 3</span>
    </div>
    <div class="ms-panel-row">
      <label class="hint">Target date (optional)</label><br>
      <input type="date" id="msDateInput" value="${node.date || ""}">
      <button class="action" id="msClearDateBtn">Clear date</button>
    </div>
    <div class="action-row">
      ${canAddChild ? `<button class="action" id="msAddChildBtn">+ Add sub-milestone</button>` : `<p class="disabled-note">Maximum depth (3 levels) reached here.</p>`}
      <button class="action" id="msRemoveBtn">Remove milestone</button>
      <button class="action" id="msEvalBtn">Evaluate progress</button>
    </div>
    <div id="msEvalResult"></div>`;

  document.getElementById("msTextInput").addEventListener("change", e => {
    node.text = e.target.value.trim() || node.text;
    saveState(); render();
  });
  document.getElementById("msCheckInput").addEventListener("change", e => {
    node.checked = e.target.checked;
    saveState(); render();
  });
  document.getElementById("msDateInput").addEventListener("change", e => {
    node.date = e.target.value || null;
    saveState(); render();
  });
  document.getElementById("msClearDateBtn").onclick = () => {
    node.date = null; saveState(); render();
  };
  if (canAddChild) {
    document.getElementById("msAddChildBtn").onclick = () => {
      const child = { id: genId(), text: "New milestone", checked: false, date: null, children: [], evaluation: null };
      node.children = node.children || [];
      node.children.push(child);
      state.collapsed.delete(node.id);
      selectedId = child.id;
      saveState(); render();
    };
  }
  document.getElementById("msRemoveBtn").onclick = () => {
    if (node.children && node.children.length && !confirm("This milestone has sub-milestones. Remove it and all of them?")) return;
    const arr = node._parent ? node._parent.children : state.milestones;
    const idx = arr.findIndex(n => n.id === node.id);
    if (idx >= 0) arr.splice(idx, 1);
    selectedId = null;
    saveState(); render();
  };
  document.getElementById("msEvalBtn").onclick = () => evaluate(node);

  if (node.evaluation) renderEvalResult(node, "stored");
}

render();
