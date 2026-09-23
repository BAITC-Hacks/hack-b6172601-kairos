"use strict";

const $ = (id) => document.getElementById(id);
const canvas = $("graph-canvas");
const ctx = canvas.getContext("2d");
const roleOrder = ["coordinator", "consolidator", "transit", "distributor", "terminal", "peripheral"];
const state = {nodes: [], edges: [], byId: new Map(), incoming: new Map(), outgoing: new Map(), top: [], selected: null, focus: new Set(), ego: false, egoDepth: 1, egoColumns: [], inspectionScale: 1, collisionPositions: new Map(), collisionKey: null, egoPositions: new Map(), skeleton: false, skeletonPositions: new Map(), skeletonRows: [], skeletonEdges: null, colourBy: "role", visibleRoles: new Set(roleOrder.filter((role) => role !== "peripheral")), scale: 1, panX: 0, panY: 0, width: 0, height: 0, dirty: false, dragPositions: new Map(), dragNode: null, dragging: false, moved: false, cameraFrame: null};
const roleColours = Object.fromEntries(roleOrder.map((role) => [role, getComputedStyle(document.documentElement).getPropertyValue(`--role-${role}`).trim()]));
const canvasColours = Object.fromEntries(["--label-background", "--text-primary", "--node-ring", "--surface-1", "--edge-focus", "--edge-muted"].map((name) => [name, getComputedStyle(document.documentElement).getPropertyValue(name).trim()]));
const cssColour = (name) => canvasColours[name];

function el(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = String(value);
  return node;
}
function num(value) { return Number.isFinite(Number(value)) ? Number(value) : 0; }
function amount(value) {
  const n = num(value);
  if (Math.abs(n) >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (Math.abs(n) >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `${(n / 1e3).toFixed(1)}K`;
  return Math.round(n).toLocaleString("en-US");
}
function fullAmount(value) { return `${num(value).toLocaleString("en-US", {maximumFractionDigits: 2})} KZT`; }
function percent(value) { return `${Math.round(num(value) * 100)}%`; }
function shortId(id) { return `…${String(id).slice(-6)}`; }
function clusterColour(value) { return `hsl(${(num(value) * 137.508) % 360}, 55%, 52%)`; }
function nodeColour(node) { return state.colourBy === "role" ? (roleColours[node.role] || roleColours.peripheral) : clusterColour(node.cluster); }
function nodeRadius(node) { return 3 + 9 * num(node?.priority); }
function visible(node) { return state.skeleton ? !!node.skeleton : state.ego ? state.egoPositions.has(node.id) : state.visibleRoles.has(node.role) || node.id === state.selected; }
async function getJson(url) {
  const response = await fetch(url);
  let data;
  try { data = await response.json(); } catch { throw new Error(`Server returned status ${response.status}.`); }
  if (!response.ok) throw new Error(typeof data.error === "string" ? data.error : `Request failed (${response.status}).`);
  return data;
}

function cancelCamera() {
  if (state.cameraFrame !== null) cancelAnimationFrame(state.cameraFrame);
  state.cameraFrame = null;
}
function moveCamera(scale, panX, panY, animate = true) {
  cancelCamera();
  const start = {scale: state.scale, panX: state.panX, panY: state.panY};
  if (!animate || window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches) {
    state.scale = scale; state.panX = panX; state.panY = panY; requestDraw(); return;
  }
  let started = null;
  function step(time) {
    if (started === null) started = time;
    const progress = Math.min(1, (time - started) / 360);
    const eased = 1 - Math.pow(1 - progress, 3);
    state.scale = start.scale + (scale - start.scale) * eased;
    state.panX = start.panX + (panX - start.panX) * eased;
    state.panY = start.panY + (panY - start.panY) * eased;
    requestDraw();
    state.cameraFrame = progress < 1 ? requestAnimationFrame(step) : null;
  }
  state.cameraFrame = requestAnimationFrame(step);
}
function largestComponent(nodes, incoming, outgoing) {
  const byId = new Map(nodes.map((node) => [node.id, node])), seen = new Set();
  let largest = [];
  // Sorted roots make equal-size component selection deterministic, including isolates.
  for (const root of [...byId.keys()].sort()) {
    if (seen.has(root)) continue;
    const component = [root]; seen.add(root);
    for (let index = 0; index < component.length; index++) {
      const id = component[index];
      for (const edge of [...(incoming.get(id) || []), ...(outgoing.get(id) || [])]) {
        const other = edge.source === id ? edge.target : edge.source;
        if (byId.has(other) && !seen.has(other)) { seen.add(other); component.push(other); }
      }
    }
    if (component.length > largest.length) largest = component;
  }
  return largest.map((id) => byId.get(id));
}
function fitOverview(animate = false) {
  if (!state.nodes.length || !state.width || !state.height) return;
  const nodes = state.overviewNodes?.length ? state.overviewNodes : state.nodes;
  const xs = nodes.map((n) => num(n.x));
  const ys = nodes.map((n) => num(n.y));
  const left = Math.min(...xs), right = Math.max(...xs), top = Math.min(...ys), bottom = Math.max(...ys);
  const scale = Math.min((state.width - 90) / Math.max(1, right - left), (state.height - 110) / Math.max(1, bottom - top));
  moveCamera(scale, -(left + right) / 2 * scale, -(top + bottom) / 2 * scale, animate);
}
function fitFocus() {
  if (!state.selected || !state.width || !state.height) return;
  const nodes = [...state.focus].map((id) => state.byId.get(id)).filter(Boolean);
  if (!nodes.length) return;
  const xs = nodes.map((node) => num(basePosition(node).x)), ys = nodes.map((node) => num(basePosition(node).y));
  const left = Math.min(...xs), right = Math.max(...xs), top = Math.min(...ys), bottom = Math.max(...ys);
  // A minimum extent keeps isolated and tightly packed accounts at a useful size.
  const scale = Math.min(3, state.width * .8 / Math.max(100, right - left), state.height * .8 / Math.max(100, bottom - top));
  state.inspectionScale = scale; state.collisionKey = null;
  moveCamera(scale, -(left + right) / 2 * scale, -(top + bottom) / 2 * scale);
}
function buildSkeleton() {
  const groups = new Map();
  for (const node of state.nodes) {
    if (!node.skeleton) continue;
    const level = Number.isInteger(Number(node.level)) && Number(node.level) >= 0 ? Number(node.level) : -1;
    if (!groups.has(level)) groups.set(level, []);
    groups.get(level).push(node);
  }
  const levels = [...groups.keys()].sort((a, b) => b - a);
  if (levels.includes(-1)) { levels.splice(levels.indexOf(-1), 1); levels.unshift(-1); }
  state.skeletonPositions.clear();
  state.skeletonRows = [];
  let y = 0;
  for (const level of levels) {
    const nodes = groups.get(level).sort((a, b) => num(b.priority) - num(a.priority) || a.id.localeCompare(b.id));
    state.skeletonRows.push({level, y});
    for (let start = 0; start < nodes.length; start += 18) {
      const row = nodes.slice(start, start + 18);
      row.forEach((node, index) => state.skeletonPositions.set(node.id, {x: (index - (row.length - 1) / 2) * 52, y}));
      y += 64;
    }
    y += 100;
  }
}
function fitSkeleton() {
  const positions = [...state.skeletonPositions.values()];
  if (!positions.length || !state.width || !state.height) return;
  const xs = positions.map((p) => p.x), ys = positions.map((p) => p.y);
  const left = Math.min(...xs), right = Math.max(...xs), top = Math.min(...ys), bottom = Math.max(...ys);
  const scale = Math.min(1.5, (state.width - 90) / Math.max(100, right - left), (state.height - 110) / Math.max(100, bottom - top));
  state.inspectionScale = scale; state.collisionKey = null;
  moveCamera(scale, -(left + right) / 2 * scale, -(top + bottom) / 2 * scale, false);
}
function resize() {
  cancelCamera();
  const rect = canvas.getBoundingClientRect();
  const oldWidth = state.width;
  state.width = Math.max(1, rect.width);
  state.height = Math.max(1, rect.height);
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(state.width * dpr);
  canvas.height = Math.round(state.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  if (!oldWidth && state.nodes.length) fitOverview(); else requestDraw();
}
// Highest priority owns the original position; lower priorities move to free space.
// The spatial hash bounds neighbour checks. The final placement has no pass limit:
// each accepted circle is checked against every nearby accepted circle.
function separateCircles(nodes, positions, scale, verticalOnly = false, anchor = null) {
  const result = new Map(), grid = new Map(), cell = 36 / scale;
  const ordered = [...nodes].sort((a, b) => Number(b.id === anchor) - Number(a.id === anchor) || num(b.priority) - num(a.priority) || a.id.localeCompare(b.id));
  function key(x, y) { return `${x},${y}`; }
  function free(p, radius) {
    const gx = Math.floor(p.x / cell), gy = Math.floor(p.y / cell);
    for (let x = gx - 1; x <= gx + 1; x++) for (let y = gy - 1; y <= gy + 1; y++) {
      for (const other of grid.get(key(x, y)) || []) {
        if (Math.hypot(p.x - other.x, p.y - other.y) < radius + other.radius + 8 / scale) return false;
      }
    }
    return true;
  }
  for (const node of ordered) {
    const original = positions.get(node.id); if (!original) continue;
    const radius = nodeRadius(node) / scale;
    let p = {...original}, ring = 0;
    while (!free(p, radius)) {
      ring++;
      if (verticalOnly) {
        p = {x: original.x, y: original.y + Math.ceil(ring / 2) * cell * (ring % 2 ? 1 : -1)};
      } else {
        // Golden-angle spiral searches outward without favouring an axis.
        const angle = ring * 2.399963229728653;
        const distance = cell * Math.sqrt(ring);
        p = {x: original.x + Math.cos(angle) * distance, y: original.y + Math.sin(angle) * distance};
      }
    }
    result.set(node.id, p);
    const k = key(Math.floor(p.x / cell), Math.floor(p.y / cell));
    if (!grid.has(k)) grid.set(k, []);
    grid.get(k).push({...p, radius});
  }
  return result;
}
function layoutKey() { return state.skeleton ? "skeleton" : state.ego ? `ego:${state.selected}:${state.egoDepth}` : "overview"; }
function basePosition(node) {
  const dragged = state.dragPositions?.get(layoutKey())?.get(node.id);
  if (dragged) return dragged;
  return state.skeleton ? state.skeletonPositions.get(node.id) : state.ego ? state.egoPositions.get(node.id) : node;
}
function ensureCollisionPositions() {
  const nodes = state.nodes.filter(visible);
  const key = `${state.skeleton}:${state.ego}:${state.egoDepth}:${state.selected}:${state.inspectionScale}:${nodes.map(n => n.id).join(",")}`;
  if (state.collisionKey === key) return;
  state.collisionPositions = separateCircles(nodes, new Map(nodes.map(n => [n.id, basePosition(n)])), state.inspectionScale, state.ego);
  state.collisionKey = key;
}
function point(node) {
  const pos = state.scale >= state.inspectionScale - 1e-9 ? state.collisionPositions.get(node.id) || basePosition(node) : basePosition(node);
  if (!pos) return null;
  return {x: state.width / 2 + state.panX + num(pos.x) * state.scale, y: state.height / 2 + state.panY + num(pos.y) * state.scale};
}
function labelClear(x, y, width, height) {
  return !(state.drawCircles || []).some(circle => {
    const dx = circle.x - Math.max(x, Math.min(circle.x, x + width));
    const dy = circle.y - Math.max(y, Math.min(circle.y, y + height));
    return dx * dx + dy * dy <= (circle.radius + 2) ** 2;
  });
}
function requestDraw() {
  if (state.dirty) return;
  state.dirty = true;
  requestAnimationFrame(() => { state.dirty = false; draw(); });
}
function drawArrow(a, b, radius, alpha, width, colour, label, labelFraction = .5) {
  const dx = b.x - a.x, dy = b.y - a.y, length = Math.hypot(dx, dy);
  if (length < 2) return;
  const ux = dx / length, uy = dy / length;
  const endX = b.x - ux * (radius + 2), endY = b.y - uy * (radius + 2);
  ctx.globalAlpha = alpha;
  ctx.strokeStyle = colour;
  ctx.fillStyle = colour;
  ctx.lineWidth = width;
  ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(endX, endY); ctx.stroke();
  const head = alpha > .3 ? 7 : 3;
  ctx.beginPath(); ctx.moveTo(endX, endY); ctx.lineTo(endX - ux * head - uy * head * .55, endY - uy * head + ux * head * .55); ctx.lineTo(endX - ux * head + uy * head * .55, endY - uy * head - ux * head * .55); ctx.closePath(); ctx.fill();
  if (label) {
    ctx.globalAlpha = 1;
    ctx.font = "11px system-ui";
    const x = a.x + dx * labelFraction - uy * 12, y = a.y + dy * labelFraction + ux * 12;
    const textWidth = ctx.measureText(label).width;
    if (!labelClear(x - textWidth / 2 - 3, y - 13, textWidth + 6, 16)) return;
    ctx.fillStyle = cssColour("--label-background");
    ctx.fillRect(x - textWidth / 2 - 3, y - 13, textWidth + 6, 16);
    ctx.fillStyle = cssColour("--text-primary");
    ctx.textAlign = "center";
    ctx.fillText(label, x, y);
  }
}
function drawNode(node, p, alpha) {
  const radius = nodeRadius(node);
  ctx.globalAlpha = alpha;
  ctx.lineWidth = node.id === state.selected ? 3 : node.seed ? 2 : 1;
  ctx.strokeStyle = node.id === state.selected ? cssColour("--text-primary") : node.seed ? cssColour("--node-ring") : nodeColour(node);
  ctx.fillStyle = node.truncated ? cssColour("--surface-1") : nodeColour(node);
  ctx.beginPath(); ctx.arc(p.x, p.y, radius, 0, Math.PI * 2); ctx.fill();
  if (node.truncated || node.seed || node.id === state.selected) ctx.stroke();
  if (node.id === state.selected) { ctx.globalAlpha = .5; ctx.beginPath(); ctx.arc(p.x, p.y, radius + 5, 0, Math.PI * 2); ctx.stroke(); }
}
function draw() {
  ctx.clearRect(0, 0, state.width, state.height);
  if (!state.nodes.length) return;
  ensureCollisionPositions();
  const positions = new Map();
  for (const node of state.nodes) {
    if (!visible(node) || (state.ego && !state.egoPositions.has(node.id))) continue;
    const p = point(node);
    if (p.x < -30 || p.x > state.width + 30 || p.y < -30 || p.y > state.height + 30) continue;
    positions.set(node.id, p);
  }
  state.drawCircles = [...positions].map(([id, p]) => ({...p, radius: nodeRadius(state.byId.get(id))}));
  const focusMode = !!state.selected && !state.skeleton && !state.ego;
  for (const edge of state.skeleton ? state.skeletonEdges || [] : state.edges) {
    const a = positions.get(edge.source), b = positions.get(edge.target);
    if (!a || !b) continue;
    const focused = !focusMode || (state.focus.has(edge.source) && state.focus.has(edge.target));
    if (state.ego && !focused) continue;
    const alpha = state.ego ? .78 : state.skeleton ? .48 : focusMode ? (focused ? .78 : .025) : .1;
    const label = state.ego ? amount(edge.sum_kzt) : focusMode && focused && (edge.source === state.selected || edge.target === state.selected) ? amount(edge.sum_kzt) : null;
    const labelFraction = state.ego ? (Math.abs(a.x - state.width / 2 - state.panX) > Math.abs(b.x - state.width / 2 - state.panX) ? .2 : .8) : .5;
    drawArrow(a, b, nodeRadius(state.byId.get(edge.target)), alpha, (state.skeleton ? Math.min(1, state.scale) : 1) * Math.min(3.3, .5 + Math.log10(Math.max(1, num(edge.sum_kzt))) * .28), focused ? cssColour("--edge-focus") : cssColour("--edge-muted"), label, labelFraction);
  }
  for (const node of [...state.nodes].sort((a, b) => num(a.priority) - num(b.priority) || b.id.localeCompare(a.id))) {
    const p = positions.get(node.id);
    if (!p) continue;
    drawNode(node, p, focusMode && !state.focus.has(node.id) ? .12 : 1);
  }
  if (state.skeleton) {
    ctx.font = "11px system-ui";
    ctx.textAlign = "left";
    for (const row of state.skeletonRows) {
      const y = state.height / 2 + state.panY + row.y * state.scale - 17;
      if (y < -15 || y > state.height + 15) continue;
      const label = row.level < 0 ? "Unassigned" : row.level === 0 ? "Seeds · level 0" : `Observed seed hops · level ${row.level}`;
      const width = ctx.measureText(label).width + 12;
      if (!labelClear(7, y - 12, width, 18)) continue;
      ctx.globalAlpha = .9; ctx.fillStyle = cssColour("--label-background"); ctx.fillRect(7, y - 12, width, 18);
      ctx.globalAlpha = 1; ctx.fillStyle = cssColour("--text-primary"); ctx.fillText(label, 13, y + 1);
    }
  }
  if (state.ego) {
    ctx.font = "11px system-ui"; ctx.textAlign = "center"; ctx.globalAlpha = 1;
    for (const column of state.egoColumns) {
      const positions = column.ids.map(id => point(state.byId.get(id)));
      const x = state.width / 2 + state.panX + column.column * state.egoGap * state.scale;
      const labels = [{text: column.label, y: Math.min(...positions.map(p => p.y)) - 30}];
      if (column.more) labels.push({text: `+${column.more} more`, y: Math.max(...positions.map(p => p.y)) + 35});
      for (const label of labels) {
        const lines = label.text.split(" of ").map((line, index) => index ? `of ${line}` : line);
        const fontSize = Math.min(11, Math.max(7, state.egoGap * state.scale / 7));
        ctx.font = `${fontSize}px system-ui`;
        const width = Math.max(...lines.map(line => ctx.measureText(line).width)) + 6;
        const height = lines.length * 13 + 4, top = label.y - height + 4;
        if (!labelClear(x - width / 2, top, width, height)) continue;
        ctx.fillStyle = cssColour("--label-background"); ctx.fillRect(x - width / 2, top, width, height);
        ctx.fillStyle = cssColour("--text-primary");
        lines.forEach((line, index) => ctx.fillText(line, x, top + 12 + index * 13));
      }
    }
  }
  ctx.globalAlpha = 1;
}

function buildFocus(id) {
  const seen = new Set([id]);
  let frontier = [id];
  for (let depth = 0; depth < 2; depth++) {
    const next = [];
    for (const current of frontier) for (const edge of [...(state.incoming.get(current) || []), ...(state.outgoing.get(current) || [])]) {
      const other = edge.source === current ? edge.target : edge.source;
      if (!seen.has(other)) { seen.add(other); next.push(other); }
    }
    frontier = next;
  }
  state.focus = seen;
}
function buildEgo() {
  const selected = state.selected, used = new Set([selected]);
  state.egoPositions = new Map([[selected, {x: 0, y: 0}]]);
  state.egoColumns = [{column: 0, ids: [selected], label: "Selected", more: 0}];
  // Columns fit horizontally; long columns remain pannable rather than shrinking circles.
  state.scale = Math.max(.05, Math.min(1.15, (state.width - 100) / (state.egoDepth * 480 + 100)));
  state.egoGap = 240;
  const spacing = 48 / state.scale;
  const frontiers = new Map([[-1, [selected]], [1, [selected]]]);
  for (let depth = 1; depth <= state.egoDepth; depth++) for (const direction of [-1, 1]) {
    const candidates = new Map();
    for (const parent of frontiers.get(direction)) {
      const edges = (direction < 0 ? state.incoming : state.outgoing).get(parent) || [];
      for (const edge of edges) {
        const id = direction < 0 ? edge.source : edge.target;
        if (used.has(id)) continue;
        if (!candidates.has(id)) candidates.set(id, {id, amount: 0, parents: new Set()});
        const candidate = candidates.get(id); candidate.amount += num(edge.sum_kzt); candidate.parents.add(parent);
      }
    }
    const ranked = [...candidates.values()].sort((a, b) => b.amount - a.amount || a.id.localeCompare(b.id));
    const shown = ranked.slice(0, 25);
    for (const node of shown) node.barycentre = [...node.parents].reduce((sum, id) => sum + state.egoPositions.get(id).y, 0) / node.parents.size;
    shown.sort((a, b) => a.barycentre - b.barycentre || b.amount - a.amount || a.id.localeCompare(b.id));
    let previous = -Infinity;
    const ys = shown.map(node => { previous = Math.max(node.barycentre, previous + spacing); return previous; });
    const offset = shown.length ? ys.reduce((sum, y, i) => sum + y - shown[i].barycentre, 0) / shown.length : 0;
    shown.forEach((node, index) => {
      used.add(node.id); state.egoPositions.set(node.id, {x: direction * depth * state.egoGap, y: ys[index] - offset});
    });
    const ids = shown.map(node => node.id); frontiers.set(direction, ids);
    if (ids.length) {
      const noun = direction < 0 ? "Payers" : "Recipients";
      const label = noun + (depth > 1 ? ` of ${noun.toLowerCase()}`.repeat(depth - 1) : "");
      state.egoColumns.push({column: direction * depth, ids, label, more: ranked.length - shown.length});
    }
  }
  state.inspectionScale = state.scale; state.collisionKey = null;
  state.panX = 0; state.panY = 0;
}
function setEgo(enabled) {
  if (!state.selected) return;
  cancelCamera();
  if (enabled && state.skeleton) { state.skeleton = false; $("skeleton-view").setAttribute("aria-pressed", "false"); }
  state.ego = enabled; state.egoDepth = 1; $("ego-depth").value = "1";
  if (enabled) buildEgo(); else fitFocus();
  $("ego-view").textContent = enabled ? "Overview layout" : "Ego view";
  $("ego-hop").hidden = !enabled;
  $("view-label").textContent = enabled ? "Directional ego · money flows left to right · pan to inspect" : "Two-hop focus · drag to pan · wheel to zoom";
  updateVisibleCount(); requestDraw();
}
function changeEgoDepth() {
  if (!state.ego) return;
  cancelCamera(); state.egoDepth = Number($("ego-depth").value); buildEgo();
  updateVisibleCount(); requestDraw();
}
async function setSkeleton() {
  if (state.skeleton) { resetView(); return; }
  const button = $("skeleton-view");
  button.disabled = true;
  try {
    if (!state.skeletonEdges) state.skeletonEdges = await getJson("/api/skeleton");
    cancelCamera();
    state.skeleton = true; state.ego = false; state.egoDepth = 1; state.egoPositions.clear(); $("ego-hop").hidden = true;
    if (state.selected && !state.byId.get(state.selected)?.skeleton) {
      state.selected = null; state.focus.clear();
      $("node-card").replaceChildren(el("div", "empty-detail", "Select a skeleton account to inspect its observed money flow."));
      document.querySelectorAll(".top-list button").forEach((item) => item.classList.remove("active"));
    }
    buildSkeleton(); fitSkeleton(); updateVisibleCount();
    button.setAttribute("aria-pressed", "true");
    $("ego-view").disabled = !state.selected;
    $("ego-view").textContent = "Ego view";
    $("view-label").textContent = "Hierarchy skeleton · observed seed-hop levels, seeds below · drag and wheel to inspect";
    requestDraw();
  } catch (error) {
    $("view-label").textContent = `Hierarchy skeleton unavailable: ${error.message}`;
  } finally { button.disabled = false; }
}
function resetView() {
  state.dragPositions.clear(); state.dragNode = null;
  state.inspectionScale = 1; state.collisionKey = null;
  state.selected = null; state.focus.clear(); state.ego = false; state.egoDepth = 1; state.egoPositions.clear(); state.skeleton = false;
  $("ego-hop").hidden = true;
  $("skeleton-view").setAttribute("aria-pressed", "false");
  $("ego-view").disabled = true; $("ego-view").textContent = "Ego view";
  $("view-label").textContent = "Overview · drag to pan · wheel to zoom · click a node";
  $("node-card").replaceChildren(el("div", "empty-detail", "Select an account to inspect its role and money flow."));
  document.querySelectorAll(".top-list button").forEach((button) => button.classList.remove("active"));
  updateVisibleCount();
  fitOverview(true);
}
async function selectNode(id) {
  if (!state.byId.has(id)) return;
  const inSkeleton = state.skeleton && !!state.byId.get(id).skeleton;
  if (state.skeleton && !inSkeleton) { state.skeleton = false; $("skeleton-view").setAttribute("aria-pressed", "false"); }
  state.selected = id; state.ego = false; state.egoDepth = 1; state.egoPositions.clear(); $("ego-hop").hidden = true; buildFocus(id);
  updateVisibleCount();
  $("ego-view").disabled = false; $("ego-view").textContent = "Ego view";
  $("view-label").textContent = inSkeleton ? "Hierarchy skeleton · observed seed-hop levels, seeds below · drag and wheel to inspect" : "Two-hop focus · drag to pan · wheel to zoom";
  if (!inSkeleton) fitFocus();
  document.querySelectorAll(".top-list button").forEach((button) => button.classList.toggle("active", button.dataset.gid === id));
  requestDraw();
  $("node-card").replaceChildren(el("p", "subtle", "Loading account…"));
  try { const details = await getJson(`/api/node/${encodeURIComponent(id)}`); if (state.selected === id) renderCard(details); }
  catch (error) { if (state.selected === id) $("node-card").replaceChildren(el("p", "subtle", error.message)); }
}

function addMetric(list, label, value) { list.append(el("dt", "", label), el("dd", "", value)); }
function explanationSections(node) {
  const role = el("section", "card-section"), priority = el("section", "card-section");
  role.append(el("h3", "", "Why this role"));
  for (const rule of node.role_explanation || []) {
    role.append(el("p", rule.matched ? "evidence" : "subtle", `Rule ${rule.rule} ${rule.role}: ${rule.detail} ${rule.matched ? "✓" : "✗"}`));
  }
  if (!node.role_explanation?.length) role.append(el("p", "subtle", "Run the pipeline to generate rule explanations."));
  priority.append(el("h3", "", "Why this priority"));
  const explanation = node.priority_explanation;
  if (explanation) {
    const list = el("dl", "metrics");
    const names = {taint: "Case-money taint", seed_sources: "Seeds within 2 hops", pagerank: "Weighted PageRank", betweenness: "Betweenness", role: "Role support weight"};
    for (const component of explanation.components) {
      addMetric(list, `${names[component.name] || component.name} · ${percent(component.weight)} weight`, `${num(component.value).toFixed(4)} → ${num(component.contribution).toFixed(4)}`);
    }
    addMetric(list, "Finding bonus (before multipliers)", `+${num(explanation.finding_bonus).toFixed(4)}`);
    addMetric(list, "Seed multiplier", `×${explanation.seed_multiplier}`);
    addMetric(list, "Traversal cut-off multiplier", `×${explanation.truncated_multiplier}`);
    addMetric(list, "Global maximum normalization", `÷${num(explanation.normalization_divisor).toFixed(6)}`);
    addMetric(list, "Likely legitimate payouts multiplier", `×${explanation.payout_multiplier}`);
    addMetric(list, "Final priority", num(explanation.score).toFixed(6));
    priority.append(list, el("p", "subtle", "Values are percentile ranks, except the configured role weight. Contributions plus the finding bonus are multiplied, normalized, then adjusted for payout evidence. This is an investigation score, not a probability."));
  } else priority.append(el("p", "subtle", "Run the pipeline to generate priority explanations."));
  return [role, priority];
}
function linkSection(title, rows) {
  const section = el("section", "card-section"); section.append(el("h3", "", `${title} (${rows.length})`));
  if (!rows.length) { section.append(el("p", "subtle", "No observed links.")); return section; }
  const table = el("table", "link-table"), head = el("thead"), tr = el("tr");
  for (const label of ["Gid / role", "KZT", "Tx"]) tr.append(el("th", "", label));
  head.append(tr); table.append(head);
  const body = el("tbody");
  for (const row of rows) {
    const item = el("tr"), first = el("td"), button = el("button", "", shortId(row.gid));
    button.type = "button"; button.title = String(row.gid); button.addEventListener("click", () => selectNode(String(row.gid)));
    first.append(button, el("span", "role-chip", row.role || "unknown"));
    item.append(first, el("td", "", amount(row.sum_kzt)), el("td", "", row.n_tx)); body.append(item);
  }
  table.append(body); section.append(table); return section;
}
function renderCard(data) {
  const n = data.node || {}, cluster = data.cluster || {}, card = $("node-card"), gid = String(n.gid || state.selected);
  card.replaceChildren();
  const header = el("div", "card-head"), title = el("div"); title.append(el("p", "subtle", "Selected account"), el("div", "gid", gid));
  const copy = el("button", "mini-button", "Copy gid"); copy.type = "button";
  copy.addEventListener("click", async () => { try { await navigator.clipboard.writeText(gid); copy.textContent = "Copied"; } catch { copy.textContent = "Copy failed"; } });
  header.append(title, copy); card.append(header);
  const badges = el("div", "card-badges");
  for (const text of [`${n.role || "unknown"} · role support ${percent(n.role_score)}`, `Priority ${percent(n.priority_score)}`, ...(state.top.find((item) => String(item.gid) === gid) ? [`Rank #${state.top.find((item) => String(item.gid) === gid).rank}`] : []), `Cluster ${n.cluster_id ?? "—"}`, ...(String(n.is_seed).toLowerCase() === "true" ? ["Seed"] : []), ...(String(n.truncated).toLowerCase() === "true" ? ["Traversal cut-off"] : [])]) badges.append(el("span", "badge", text));
  card.append(badges);
  if (Array.isArray(n.twin_gids) && n.twin_gids.length) {
    const twins = el("section", "card-section");
    twins.append(el("h3", "", "Twin accounts"));
    for (const other of n.twin_gids) {
      const button = el("button", "gid-link", `${shortId(other)} (${num(n.twin_shared_payers?.[other])} shared payers)`);
      button.type = "button"; button.title = String(other);
      button.addEventListener("click", () => selectNode(String(other)));
      twins.append(el("p", "", "")); twins.lastChild.append(button);
    }
    twins.append(el("p", "subtle", `Review group ${n.twin_group}. Shared payers suggest possible common control, not proven identity. Listed accounts are direct pair matches; groups can connect transitively.`));
    card.append(twins);
  }
  const evidence = el("section", "card-section"); evidence.append(el("h3", "", "Role evidence"), el("p", "evidence", n.evidence || "No evidence recorded.")); card.append(evidence);
  card.append(...explanationSections(n));
  const community = el("section", "card-section"); community.append(el("h3", "", "Cluster hypothesis"), el("p", "", cluster.hypothesis || "No cluster description.")); card.append(community);
  if (n.findings) {
    const findings = el("section", "card-section");
    findings.append(el("h3", "", "Findings"), el("p", "evidence", n.findings)); card.append(findings);
  }
  const metricsSection = el("section", "card-section"), metrics = el("dl", "metrics"); metricsSection.append(el("h3", "", "Observed metrics"), metrics);
  addMetric(metrics, "Incoming payers", n.in_deg ?? "—"); addMetric(metrics, "Outgoing recipients", n.out_deg ?? "—");
  addMetric(metrics, "Incoming KZT", fullAmount(n.in_kzt)); addMetric(metrics, "Outgoing KZT", fullAmount(n.out_kzt));
  addMetric(metrics, "Pass-through", n.pass_through === "" || n.pass_through == null ? "Unknown" : percent(n.pass_through));
  addMetric(metrics, "Case-money trace", fullAmount(n.taint_kzt)); addMetric(metrics, "Seeds within 2 hops", n.seed_sources_2hop ?? "—");
  addMetric(metrics, "Fast-pass share", n.fast_pass_share === "" || n.fast_pass_share == null ? "Unknown" : percent(n.fast_pass_share));
  addMetric(metrics, "Depth", n.depth ?? "—"); addMetric(metrics, "Seed", String(n.is_seed).toLowerCase() === "true" ? "Yes" : "No");
  if (n.peripheral_reason) addMetric(metrics, "Peripheral reason", n.peripheral_reason);
  card.append(metricsSection, linkSection("Incoming money", data.incoming || []), linkSection("Outgoing money", data.outgoing || []));
  card.append(el("p", "subtle card-section", "These roles and cluster narratives are hypotheses from observed transfers. Missing flows remain unknown."));
}

function renderFilters(counts) {
  const parent = $("role-filters"); parent.replaceChildren();
  for (const role of roleOrder) {
    const label = el("div", "role-filter"), input = el("input"), swatch = el("span", "swatch"), browse = el("button", "role-browse", role);
    input.type = "checkbox"; input.checked = state.visibleRoles.has(role); input.dataset.role = role; swatch.style.background = roleColours[role];
    input.setAttribute("aria-label", `Show ${role} accounts`);
    browse.type = "button"; browse.title = `List ${role} accounts by priority`;
    browse.addEventListener("click", () => browseAccounts("role", role, role));
    input.addEventListener("change", () => { if (input.checked) state.visibleRoles.add(role); else state.visibleRoles.delete(role); updateVisibleCount(); requestDraw(); });
    label.append(input, swatch, browse, el("span", "role-count", counts[role] || 0)); parent.append(label);
  }
  updateVisibleCount();
}
function updateVisibleCount() { $("visible-count").textContent = `(${state.nodes.filter(visible).length.toLocaleString("en-US")} shown)`; }
let browseRequest = 0;
async function browseAccounts(kind, value, title) {
  const request = ++browseRequest, list = $("browse-list"), status = $("browse-status");
  $("browse-section").hidden = false;
  $("browse-title").textContent = title;
  list.replaceChildren(); status.textContent = "Loading accounts…";
  $("browse-section").scrollIntoView({block: "nearest"});
  try {
    const rows = await getJson(`/api/accounts?${kind}=${encodeURIComponent(value)}`);
    if (request !== browseRequest) return;
    status.textContent = `${rows.length} accounts · highest priority first`;
    for (const row of rows) {
      const li = el("li"), button = el("button", "browse-account"), main = el("span", "top-main");
      button.type = "button"; button.dataset.gid = row.gid; button.title = row.gid;
      main.append(el("span", "short-gid", shortId(row.gid)), el("span", "role-chip", row.role));
      const finding = (row.findings || "").split(/(?<=\.)\s+/)[0];
      main.append(el("span", "first-finding", finding || "No additional finding recorded."));
      button.append(main, el("span", "score", percent(row.priority_score)));
      button.addEventListener("click", () => selectNode(row.gid)); li.append(button); list.append(li);
    }
  } catch (error) { if (request === browseRequest) status.textContent = error.message; }
}
function renderFindingFilters() {
  const filters = [["shared_sources_twin", "Shared-source twins"], ["common_counterparty", "Common counterparty"], ["synchronous_inflow", "Synchronous inflow"], ["scatter_gather", "Scatter / gather"], ["likely_legit_payouts", "Likely legitimate payouts"], ["extension_requests", "Extension requests"]];
  for (const [flag, label] of filters) {
    const button = el("button", "", label); button.type = "button";
    button.addEventListener("click", () => browseAccounts("flag", flag, label)); $("finding-filters").append(button);
  }
}
function renderTop(rows) {
  state.top = rows; const list = $("top-list"); list.replaceChildren();
  for (const row of rows) {
    const li = el("li"), button = el("button"), main = el("span", "top-main"); button.type = "button"; button.dataset.gid = String(row.gid); button.title = String(row.gid);
    main.append(el("span", "short-gid", shortId(row.gid)), el("span", "role-chip", row.role));
    button.append(el("span", "rank", row.rank), main, el("span", "score", percent(row.priority_score)));
    button.addEventListener("click", () => selectNode(String(row.gid))); li.append(button); list.append(li);
  }
}
function hitTest(x, y) {
  ensureCollisionPositions();
  let best = null;
  for (const node of state.nodes) {
    if (!visible(node)) continue;
    const p = point(node), d = Math.hypot(x - p.x, y - p.y);
    if (d <= nodeRadius(node) + 2 && (!best || num(node.priority) > num(best.priority) || (num(node.priority) === num(best.priority) && node.id < best.id))) best = node;
  }
  return best;
}

function dragNodeTo(id, x, y) {
  ensureCollisionPositions();
  const nodes = state.nodes.filter(visible), close = state.scale >= state.inspectionScale - 1e-9;
  let positions = new Map(nodes.map(node => [node.id, {...(close ? state.collisionPositions.get(node.id) : basePosition(node))}]));
  positions.set(id, {x, y});
  // Keep the dragged account under the pointer and move its neighbours out of
  // the way. Separate at the inspection threshold, so zooming back stays safe.
  if (close) positions = separateCircles(nodes, positions, state.inspectionScale, state.ego, id);
  state.dragPositions.set(layoutKey(), positions); state.collisionKey = null;
}
canvas.addEventListener("pointerdown", (event) => {
  if (event.button !== 0) return;
  cancelCamera();
  const rect = canvas.getBoundingClientRect(), node = hitTest(event.clientX - rect.left, event.clientY - rect.top);
  state.dragging = true; state.moved = false; state.dragNode = node?.id || null;
  state.startX = state.lastX = event.clientX; state.startY = state.lastY = event.clientY;
  if (node) {
    const p = point(node);
    state.dragStart = {x: (p.x - state.width / 2 - state.panX) / state.scale, y: (p.y - state.height / 2 - state.panY) / state.scale};
  }
  canvas.classList.add("dragging"); canvas.setPointerCapture(event.pointerId);
});
canvas.addEventListener("pointermove", (event) => {
  if (state.dragging) {
    const dx = event.clientX - state.lastX, dy = event.clientY - state.lastY;
    const totalX = event.clientX - state.startX, totalY = event.clientY - state.startY;
    if (Math.hypot(totalX, totalY) > 3) state.moved = true;
    if (state.dragNode) {
      if (state.moved) dragNodeTo(state.dragNode, state.dragStart.x + totalX / state.scale, state.dragStart.y + totalY / state.scale);
    } else { state.panX += dx; state.panY += dy; }
    state.lastX = event.clientX; state.lastY = event.clientY; requestDraw(); $("tooltip").hidden = true; return;
  }
  const rect = canvas.getBoundingClientRect(), node = hitTest(event.clientX - rect.left, event.clientY - rect.top), tip = $("tooltip");
  if (!node) { tip.hidden = true; return; }
  tip.textContent = `${node.id} · ${node.role} · priority ${percent(node.priority)}`;
  tip.style.left = `${Math.min(event.clientX - rect.left + 12, state.width - 230)}px`; tip.style.top = `${event.clientY - rect.top + 12}px`; tip.hidden = false;
});
canvas.addEventListener("pointerup", (event) => {
  if (!state.dragging) return;
  state.dragging = false; state.dragNode = null; canvas.classList.remove("dragging");
  if (!state.moved) { const rect = canvas.getBoundingClientRect(), node = hitTest(event.clientX - rect.left, event.clientY - rect.top); if (node) selectNode(node.id); }
});
canvas.addEventListener("pointercancel", () => { state.dragging = false; state.dragNode = null; canvas.classList.remove("dragging"); });
canvas.addEventListener("pointerleave", () => { $("tooltip").hidden = true; });
canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  cancelCamera();
  const rect = canvas.getBoundingClientRect(), x = event.clientX - rect.left - state.width / 2, y = event.clientY - rect.top - state.height / 2;
  const next = Math.max(.03, Math.min(40, state.scale * Math.exp(-event.deltaY * .001)));
  const factor = next / state.scale; state.panX = x - (x - state.panX) * factor; state.panY = y - (y - state.panY) * factor; state.scale = next; requestDraw();
}, {passive: false});
$("search-form").addEventListener("submit", async (event) => {
  event.preventDefault(); const q = $("search-input").value.trim(), message = $("search-message");
  if (!q) { message.textContent = "Enter a gid or its last digits."; return; }
  message.textContent = "Searching…";
  try { const matches = await getJson(`/api/search?q=${encodeURIComponent(q)}`); if (!matches.length) { message.textContent = "No account found for those digits."; return; } message.textContent = matches.length > 1 ? `${matches.length} matches; showing the first. Enter more digits to narrow it.` : "Account found."; await selectNode(String(matches[0])); }
  catch (error) { message.textContent = error.message; }
});
$("colour-role").addEventListener("click", () => setColour("role"));
$("colour-cluster").addEventListener("click", () => setColour("cluster"));
function setColour(value) { state.colourBy = value; $("colour-role").setAttribute("aria-pressed", value === "role"); $("colour-cluster").setAttribute("aria-pressed", value === "cluster"); requestDraw(); }
$("ego-view").addEventListener("click", () => setEgo(!state.ego));
$("ego-depth").addEventListener("change", changeEgoDepth);
$("skeleton-view").addEventListener("click", setSkeleton);
$("reset-view").addEventListener("click", resetView);
$("method-open").addEventListener("click", async () => {
  const dialog = $("method-dialog"), content = $("method-content");
  content.replaceChildren(el("p", "subtle", "Loading method…")); dialog.showModal();
  try {
    const method = await getJson("/api/method"), steps = el("ol", "method-steps"), table = el("table", "method-table"), head = el("thead"), headings = el("tr"), body = el("tbody");
    for (const step of method.steps) steps.append(el("li", "", step));
    headings.append(el("th", "", "Role"), el("th", "", "First-matching rule")); head.append(headings);
    for (const rule of method.rules) { const row = el("tr"); row.append(el("th", "", rule.role), el("td", "", rule.rule)); body.append(row); }
    table.append(head, body);
    content.replaceChildren(el("h3", "", "Pipeline steps"), steps, el("h3", "", "Role rules in precedence order"), table, el("p", "subtle", "Roles are hypotheses and priority scores are heuristic investigation signals, not probabilities of guilt. Incoming transfers are incomplete; outgoing transfers at the depth-4 boundary are unknown."));
  } catch (error) { content.replaceChildren(el("p", "subtle", error.message)); }
});
$("method-close").addEventListener("click", () => $("method-dialog").close());
document.addEventListener("keydown", (event) => { if (event.key === "Escape" && !$("method-dialog").open) resetView(); });
new ResizeObserver(resize).observe(canvas);

async function start() {
  try {
    const [graph, top] = await Promise.all([getJson("/api/graph"), getJson("/api/top")]);
    state.nodes = graph.nodes; state.edges = graph.edges; state.byId = new Map(state.nodes.map((node) => [node.id, node]));
    for (const edge of state.edges) {
      if (!state.outgoing.has(edge.source)) state.outgoing.set(edge.source, []);
      if (!state.incoming.has(edge.target)) state.incoming.set(edge.target, []);
      state.outgoing.get(edge.source).push(edge); state.incoming.get(edge.target).push(edge);
    }
    state.overviewNodes = largestComponent(state.nodes, state.incoming, state.outgoing);
    renderFilters(graph.roles_count || {}); renderTop(top); renderFindingFilters();
    $("graph-status").textContent = `${state.nodes.length.toLocaleString("en-US")} accounts · ${state.edges.length.toLocaleString("en-US")} directed links`;
    fitOverview();
  } catch (error) { $("graph-status").textContent = "Graph unavailable"; $("map-error").textContent = error.message; $("map-error").hidden = false; }
}
start();
