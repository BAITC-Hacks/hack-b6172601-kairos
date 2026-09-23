/* Optional Node check of the shipped canvas component selection and camera bounds. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "static/app.js"), "utf8");
const start = source.indexOf("function largestComponent(");
const end = source.indexOf("function fitFocus(", start);
assert.ok(start >= 0 && end > start);
const context = {Map, Set, Math, num: Number, state: {}, moveCamera: (...args) => { context.camera = args; }};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
function component(nodes, edges) {
  const incoming = new Map(), outgoing = new Map();
  for (const edge of edges) {
    if (!incoming.has(edge.target)) incoming.set(edge.target, []);
    if (!outgoing.has(edge.source)) outgoing.set(edge.source, []);
    incoming.get(edge.target).push(edge); outgoing.get(edge.source).push(edge);
  }
  return context.largestComponent(nodes, incoming, outgoing);
}
const nodes = ["9", "4", "3", "2", "1"].map((id) => ({id}));
const edges = [{source:"2",target:"1"}, {source:"4",target:"3"}];
assert.deepEqual(Array.from(component(nodes, edges), (n) => n.id).sort(), ["1", "2"]);
assert.deepEqual(Array.from(component(nodes, []), (n) => n.id), ["1"]);
assert.equal(component([], []).length, 0);
const graph = JSON.parse(fs.readFileSync(path.join(root, "out/graph.json"), "utf8"));
const largest = component(graph.nodes, graph.edges);
assert.equal(largest.length, 1877);
context.state = {nodes: graph.nodes, overviewNodes: largest, width: 1000, height: 700};
context.fitOverview(true);
const [scale, panX, panY, animate] = context.camera;
assert.equal(animate, true);
assert.ok(scale > 0 && Number.isFinite(scale));
for (const node of largest) {
  const x = 500 + panX + node.x * scale, y = 350 + panY + node.y * scale;
  assert.ok(x >= 44.99 && x <= 955.01 && y >= 54.99 && y <= 645.01);
}
assert.ok(graph.nodes.some((node) => Math.abs(panX + node.x * scale) > 500 || Math.abs(panY + node.y * scale) > 350));
context.state = {nodes: [{id:"solo", x:4, y:8}], overviewNodes: [{id:"solo", x:4, y:8}], width:500, height:400};
context.fitOverview();
assert.ok(context.camera.slice(0, 3).every(Number.isFinite));
console.log("Viewer layout checks passed: weak components, ties, isolates, official count and fit bounds.");
