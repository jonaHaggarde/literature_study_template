// Shared tree logic used by both the exploration map (app.js) and the
// gaps browser (gaps.js). Both read/write the SAME localStorage key, so
// a sub-branch added or a node marked "chosen" on one page shows up on
// the other — they're two views over one tree, not two datasets.
// Wrapped in an IIFE so app.js/gaps.js can each keep their own
// same-named local variables without a redeclaration clash.

const TreeLib = (function () {
  const STORAGE_KEY = "explorationMapState_v1";

  function loadState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) throw new Error("empty");
      const parsed = JSON.parse(raw);
      return {
        expanded: new Set(parsed.expanded || []),
        chosen: new Set(parsed.chosen || []),
        positions: parsed.positions || {},
        customChildren: parsed.customChildren || {}
      };
    } catch (e) {
      return { expanded: new Set(), chosen: new Set(), positions: {}, customChildren: {} };
    }
  }

  function saveState(state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      expanded: [...state.expanded],
      chosen: [...state.chosen],
      positions: state.positions,
      customChildren: state.customChildren
    }));
  }

  function cloneTree(node) {
    return Object.assign({}, node, { children: (node.children || []).map(cloneTree) });
  }

  function mergeCustom(node, customChildren) {
    const extra = (customChildren[node.id] || []).map(cloneTree);
    node.children = [...(node.children || []), ...extra];
    node.children.forEach(n => mergeCustom(n, customChildren));
    return node;
  }

  function getWorkingRoots(studyData, customChildren) {
    return studyData.roots.map(r => mergeCustom(cloneTree(r), customChildren));
  }

  function hasChildren(node) {
    return !!(node.children && node.children.length);
  }

  function collectLeafStatuses(node, out) {
    if (!hasChildren(node)) { out.push(node.status); return; }
    node.children.forEach(c => collectLeafStatuses(c, out));
  }

  function gapScore(node) {
    if (!hasChildren(node)) return null;
    const statuses = [];
    collectLeafStatuses(node, statuses);
    if (statuses.length === 0) return 0;
    return statuses.filter(s => s === "identified").length / statuses.length;
  }

  // Flat list of every node with its ancestor-label breadcrumb and depth.
  function flatten(roots) {
    const out = [];
    roots.forEach(root => {
      (function walk(node, path, depth) {
        out.push({ node, path, depth });
        (node.children || []).forEach(c => walk(c, path.concat([node.label]), depth + 1));
      })(root, [], 0);
    });
    return out;
  }

  return {
    STORAGE_KEY, loadState, saveState, cloneTree, mergeCustom,
    getWorkingRoots, hasChildren, collectLeafStatuses, gapScore, flatten
  };
})();
