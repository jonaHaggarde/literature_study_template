// Gaps browser. Reads the SAME tree as the exploration map (via tree.js
// + data.sample.js) rather than a separate dataset — a sub-branch added
// or a node marked "chosen" on the map shows up here too. No writes
// happen from this page; it's a browsing/triage lens on the map's data,
// plus a batch "explore more" request composer that isn't wired to
// Claude yet (see ../../gui-dev-notes.md).

const state = TreeLib.loadState();
const selected = new Set();      // multi-select for batch explore, in-memory only
let selectedDetailId = null;
let showRejected = false;
let searchText = "";

const gapList = document.getElementById("gapList");
const panel = document.getElementById("panel");

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function computeItems() {
  const roots = TreeLib.getWorkingRoots(STUDY_DATA, state.customChildren);
  const flat = TreeLib.flatten(roots);
  const nodeIndex = new Map(flat.map(i => [i.node.id, i]));

  const statuses = showRejected ? ["identified", "evaluated-not-favored"] : ["identified"];
  let items = flat.filter(item => !TreeLib.hasChildren(item.node) && statuses.includes(item.node.status));

  if (searchText) {
    const q = searchText.toLowerCase();
    items = items.filter(item =>
      (item.node.label + " " + (item.node.detail || "") + " " + item.path.join(" ")).toLowerCase().includes(q));
  }

  items.sort((a, b) => (state.chosen.has(a.node.id) ? 0 : 1) - (state.chosen.has(b.node.id) ? 0 : 1));
  return { items, nodeIndex };
}

function rowHtml(item) {
  const node = item.node;
  const isChosen = state.chosen.has(node.id);
  return `
    <div class="ms-row gap-row ${selectedDetailId === node.id ? "selected" : ""}" data-id="${node.id}">
      <input type="checkbox" class="ms-check" data-action="select-check" ${selected.has(node.id) ? "checked" : ""}>
      <span class="ms-text" data-action="open">
        <span class="gap-breadcrumb">${escapeHtml(item.path.join(" › "))}</span>
        <strong>${escapeHtml(node.label)}</strong>
        ${isChosen ? '<span class="status-pill chosen" style="margin-left:6px;">Chosen</span>' : ""}
        ${node.status === "evaluated-not-favored" ? '<span class="status-pill evaluated-not-favored" style="margin-left:6px;">Not favored</span>' : ""}
      </span>
    </div>`;
}

function render() {
  const { items, nodeIndex } = computeItems();

  gapList.innerHTML = items.length
    ? items.map(rowHtml).join("")
    : `<p class="hint">No open gaps match right now. Try clearing the search or toggling "Also show evaluated-not-favored".</p>`;

  const btn = document.getElementById("exploreMoreBtn");
  btn.textContent = `Explore more on selected (${selected.size})`;
  btn.disabled = selected.size === 0;

  if (selectedDetailId && nodeIndex.has(selectedDetailId)) renderDetailPanel(nodeIndex.get(selectedDetailId));
  else renderDefaultPanel(items.length);
}

gapList.addEventListener("click", e => {
  const row = e.target.closest(".gap-row");
  if (!row) return;
  const id = row.dataset.id;
  if (e.target.dataset.action === "select-check") {
    if (e.target.checked) selected.add(id); else selected.delete(id);
    render();
    return;
  }
  selectedDetailId = id;
  render();
});

document.getElementById("gapSearch").addEventListener("input", e => { searchText = e.target.value; render(); });
document.getElementById("showRejected").addEventListener("change", e => { showRejected = e.target.checked; render(); });
document.getElementById("selectAllBtn").onclick = () => {
  computeItems().items.forEach(i => selected.add(i.node.id));
  render();
};
document.getElementById("clearSelectionBtn").onclick = () => { selected.clear(); render(); };
document.getElementById("exploreMoreBtn").onclick = () => {
  const { nodeIndex } = computeItems();
  renderBatchPreview([...selected].map(id => nodeIndex.get(id)).filter(Boolean));
};

// ---- side panel ----------------------------------------------------------

function renderDefaultPanel(count) {
  panel.innerHTML = `
    <h2>Gaps</h2>
    <p class="hint">
      ${count} open gap${count === 1 ? "" : "s"} shown below — leaf
      branches in the exploration map that are still just "identified,"
      not explored. Click one for details, or check several and use
      "Explore more on selected" to research them together.
    </p>`;
}

function renderDetailPanel(item) {
  const node = item.node;
  const isChosen = state.chosen.has(node.id);
  const pillClass = isChosen ? "chosen" : node.status;
  const pillLabel = isChosen ? "Chosen, still unexplored"
    : node.status === "identified" ? "Identified, not yet explored" : "Evaluated — not favored";
  panel.innerHTML = `
    <h2>${escapeHtml(node.label)}</h2>
    <p class="detail-source">${escapeHtml(item.path.join(" › "))}</p>
    <span class="status-pill ${pillClass}">${pillLabel}</span>
    <p class="detail-desc">${escapeHtml(node.detail || "")}</p>
    <div class="action-row">
      <a class="action" style="display:block; text-decoration:none; text-align:left; box-sizing:border-box;" href="index.html?focus=${encodeURIComponent(node.id)}">View in exploration map</a>
    </div>`;
}

function renderBatchPreview(items) {
  const lines = items.map(i => `- ${i.path.concat([i.node.label]).join(" > ")}: ${i.node.detail || ""}`);
  const text = "Explore these gaps further and report back findings:\n\n" + lines.join("\n");
  panel.innerHTML = `
    <h2>Explore more — preview</h2>
    <p class="hint">${items.length} gap(s) selected. This is the request that would be handed to Claude once the local server exists.</p>
    <textarea readonly style="width:100%; height:180px; padding:8px; border-radius:8px; border:1px solid var(--panel-border); font-family:inherit; font-size:0.85rem;">${escapeHtml(text)}</textarea>
    <div class="action-row">
      <button class="action disabled" id="sendBtn">Send to Claude</button>
      <p class="disabled-note">Not connected yet — see ../../gui-dev-notes.md.</p>
    </div>`;
}

render();
