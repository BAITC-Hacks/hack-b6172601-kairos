const fs = require('fs'), vm = require('vm');
const assert = require('node:assert/strict');
const root = require('node:path').join(__dirname, '..');
const source = fs.readFileSync(root + '/static/app.js', 'utf8');
function slice(a,b){const i=source.indexOf(a),j=source.indexOf(b,i);if(i<0||j<i)throw Error(a);return source.slice(i,j)}
const context={Map,Set,Math,Number,console,state:{},num:v=>Number.isFinite(Number(v))?Number(v):0,nodeRadius:n=>3+9*(Number(n?.priority)||0)};
vm.createContext(context);
vm.runInContext(slice('function separateCircles(', 'function labelClear(')+slice('function buildEgo(', 'function setEgo(')+slice('function hitTest(', 'canvas.addEventListener('),context);
const graph=JSON.parse(fs.readFileSync(root+'/out/graph.json','utf8'));
const s=context.state;
s.nodes=graph.nodes;s.edges=graph.edges;s.byId=new Map(s.nodes.map(n=>[n.id,n]));s.incoming=new Map();s.outgoing=new Map();s.visibleRoles=new Set(['coordinator','consolidator','distributor','transit','terminal','peripheral']);
for(const e of s.edges){if(!s.incoming.has(e.target))s.incoming.set(e.target,[]);if(!s.outgoing.has(e.source))s.outgoing.set(e.source,[]);s.incoming.get(e.target).push(e);s.outgoing.get(e.source).push(e)}
s.width=1200;s.height=800;s.panX=0;s.panY=0;s.ego=false;s.skeleton=false;s.selected=null;s.inspectionScale=1;
context.visible=n=>s.ego?s.egoPositions.has(n.id):true;
function verify(scale){s.scale=scale;s.inspectionScale=scale;s.collisionKey=null;context.ensureCollisionPositions();const p=s.nodes.map(n=>({n,p:context.point(n)}));let worst=Infinity,pair=null;for(let i=0;i<p.length;i++)for(let j=i+1;j<p.length;j++){const d=Math.hypot(p[i].p.x-p[j].p.x,p[i].p.y-p[j].p.y)-context.nodeRadius(p[i].n)-context.nodeRadius(p[j].n);if(d<worst){worst=d;pair=[p[i].n.id,p[j].n.id]}}assert.ok(worst >= 7.999, `Overlap at scale ${scale}: ${pair}`);}
for(const z of [.4,1,2,3])verify(z);
// Far-out exact overlap must pick priority, then id; hitTest uses actual point/visible code.
let a={id:'z',priority:.1,x:1e8,y:1e8},b={id:'a',priority:.9,x:1e8,y:1e8};s.nodes=[a,b];s.byId=new Map(s.nodes.map(n=>[n.id,n]));s.scale=.1;s.inspectionScale=1;s.collisionKey=null;s.panX=-1e7;s.panY=-1e7;assert.equal(context.hitTest(600,400)?.id, 'a');
function ego(edges,depth){s.nodes=[...new Set(edges.flatMap(e=>[e.source,e.target]))].map(id=>({id,priority:.5}));s.byId=new Map(s.nodes.map(n=>[n.id,n]));s.incoming=new Map();s.outgoing=new Map();for(const e of edges){if(!s.incoming.has(e.target))s.incoming.set(e.target,[]);if(!s.outgoing.has(e.source))s.outgoing.set(e.source,[]);s.incoming.get(e.target).push(e);s.outgoing.get(e.source).push(e)}s.selected='S';s.ego=true;s.egoDepth=depth;context.buildEgo();assert.ok(s.egoColumns.every(c => c.ids.length <= 25 && Math.abs(c.column) <= depth)); assert.equal(new Set(s.egoColumns.flatMap(c => c.ids)).size, s.egoPositions.size)}
const E=(a,b,v=1)=>({source:a,target:b,sum_kzt:v});
let edges=[E('L2','L1'),E('L1','S'),E('S','R1'),E('R1','R2'),E('R2','R3'),E('R3','R4'),E('R2','S'),E('R1','R3')];
for(let d=1;d<=4;d++)ego(edges,d);
edges=[...Array.from({length:30},(_,i)=>E('S','X'+String(i).padStart(2,'0'),30-i)),E('X00','Y',1),E('X01','Y',2)];ego(edges,2);

assert.equal(s.egoColumns.find(c => c.column === 1).more, 5);
assert.ok(s.egoColumns.find(c => c.column === 2).ids.includes('Y'));
assert.equal(s.egoColumns.find(c => c.column === 1).ids.includes('X29'), false);
console.log('Collision, hit priority, directional hops, convergence and cap checks passed.');
// Dragging moves the active layout and connected endpoints together, retaining
// circle separation even when the pointer moves directly over another account.
s.dragPositions = new Map();
for (const mode of ['overview', 'ego', 'skeleton']) {
  s.nodes = [{id:'a', priority:.1, x:0, y:0}, {id:'b', priority:1, x:100, y:100}];
  s.byId = new Map(s.nodes.map(n => [n.id, n]));
  s.ego = mode === 'ego'; s.skeleton = mode === 'skeleton';
  s.egoPositions = new Map(s.nodes.map(n => [n.id, {x:n.x,y:n.y}]));
  s.skeletonPositions = new Map(s.egoPositions); s.selected = 'a'; s.egoDepth = 1;
  s.inspectionScale = .5; s.scale = 2; s.panX = s.panY = 0; s.collisionKey = null;
  context.dragNodeTo('a', 100, 100); context.ensureCollisionPositions();
  const a = context.point(s.byId.get('a')), b = context.point(s.byId.get('b'));
  assert.equal(a.x, s.width / 2 + 200); assert.equal(a.y, s.height / 2 + 200);
  assert.ok(Math.hypot(a.x-b.x,a.y-b.y) > 24);
  assert.equal(s.nodes[0].x, 0, 'Exported coordinates must stay immutable');
  s.scale = .5;
  const backA = context.point(s.byId.get('a')), backB = context.point(s.byId.get('b'));
  assert.ok(Math.hypot(backA.x-backB.x,backA.y-backB.y) >= context.nodeRadius(s.nodes[0]) + context.nodeRadius(s.nodes[1]) + 7.999);
}
context.$ = () => ({setAttribute(){}, replaceChildren(){}});
context.el = () => ({}); context.document = {querySelectorAll: () => []};
context.updateVisibleCount = () => {}; context.fitOverview = () => {};
s.focus = new Set();
vm.runInContext(slice('function resetView(', 'async function selectNode('), context);
context.resetView(); assert.equal(s.dragPositions.size, 0); assert.equal(s.dragNode, null);
console.log('Dragging in every layout, zoom-back separation and Overview reset passed.');
