// Operations on the arrangement: where boxes sit and which group they belong to.
// They update absolute positions and the current layout without drawing or writing.
// Automatic placement never shifts an established box.

import { app, compose, currentLayout, groupOf, membership, visible } from './state.js';
import { CW, CH, GAPX, GAPY, bounds, framePixels, gather, nearestFree, settle, tidy } from './grid.js';
import { discoveryPoint } from './server.js';
import { forceLayout } from './forces.js';
import { sizeBox } from './model.js';
import { byName, cleanName } from './util.js';

function entry(wid) { return app.arr.windows[wid]; }

function setPos(wid, x, y) {
  const e = app.arr.windows[wid];
  if (e) { e.x = x; e.y = y; } else app.arr.windows[wid] = { x: x, y: y };
}

export function boxOf(w) {
  const e = entry(w.id), g = groupOf(w.id);
  return { id: w.id, x: e.x, y: e.y, w: w.wc, h: w.hc, g: g ? g.id : null };
}

export function scene(layoutId = currentLayout().id) {
  const layout = app.layouts.find(l => l.id === layoutId);
  const arr = layout === currentLayout() ? app.arr : compose(app.shared, layout);
  const boxes = boxesFor(arr, layout);
  if (layout.id === 'main' && layout !== currentLayout()) {
    const members = membership(arr.groups);
    for (const w of app.model.allWins) {
      const p = discoveryPoint(w.id);
      if (p && !arr.windows[w.id] && !members.has(w.id) && visible(layout, w.id)) {
        boxes.set(w.id, {id: w.id, ...p, w: w.wc, h: w.hc, g: null});
      }
    }
  }
  return boxes;
}

function boxesFor(arr, layout) {
  const boxes = new Map(), members = membership(arr.groups);
  for (const w of app.model.allWins) {
    const p = arr.windows[w.id], g = members.get(w.id);
    if (p && visible(layout, w.id, g)) boxes.set(w.id, {id: w.id, x: p.x, y: p.y, w: w.wc, h: w.hc, g});
  }
  return boxes;
}

export function translateGroup(g, dx, dy) {
  const anchor = currentLayout().groups[g.id];
  const point = {x: anchor.x + dx, y: anchor.y + dy};
  currentLayout().groups[g.id] = point;
  for (const id of g.members) {
    const w = entry(id);
    if (w) setPos(id, w.x + dx, w.y + dy);
  }
  return {groups: {[g.id]: point}};
}

export function setStandalone(id, x, y) {
  setPos(id, x, y);
  const point = currentLayout().windows[id] = {x, y};
  return {windows: {[id]: point}};
}

export function openMembers(g) {
  return g.members.map(function (id) { return app.model.winById.get(id); }).filter(Boolean);
}

function readingOrder(a, b) {
  const ea = entry(a.id), eb = entry(b.id);
  if (!ea || !eb) return byName(a, b);
  return ea.y - eb.y || ea.x - eb.x || byName(a, b);
}

// Moves these windows (one box, or members of one group) together to the nearest free spot.
function ensureClear(wins) {
  const moving = wins.filter(function (w) { return entry(w.id); }).map(boxOf);
  if (!moving.length) return;
  const off = nearestFree(scene(), moving);   // if a member has no free spot it stays and is marked too close
  if (off.dx || off.dy) moving.forEach(function (b) { setPos(b.id, b.x + off.dx, b.y + off.dy); });
}

// Find a missing position near its siblings, linked neighbours, or below the map.
function place(w, g, boxes, fallback) {
  const peers = [...w.peers.keys()].map(peer => boxes.get(peer.id)).filter(Boolean);
  const bb = bounds([...boxes.values()]);
  const siblings = g ? [...boxes.values()].filter(b => b.g === g) : [];
  const gb = bounds(siblings);
  const mean = coord => Math.round(peers.reduce((sum, p) => sum + p[coord], 0) / peers.length);
  const at = siblings.length ? {x: gb.x1, y: gb.y0}
    : fallback || (peers.length ? {x: mean('x'), y: mean('y')} : {x: bb.x0, y: bb.y1});
  const b = {id: w.id, ...at, w: w.wc, h: w.hc, g};
  const {dx, dy} = nearestFree(boxes, [b]);
  return {x: b.x + dx, y: b.y + dy};
}

export function placeMissing(viewW, viewH) {
  const current = currentLayout(), main = app.layouts[0], arr = app.arr;
  const mainArr = current === main ? arr : compose(app.shared, main);
  const boxes = scene(main.id), localBoxes = current === main ? boxes : scene();
  const members = membership(arr.groups), seeds = {main_windows: {}}, patch = {windows: {}};
  let saveChanged = false, visibilityChanged = false;
  const wins = app.model.allWins.filter(w => !w.closed).sort((a, b) => b.peers.size - a.peers.size || byName(a, b));
  const first = !boxes.size && wins.length
    ? forcePositions(wins.filter(w => !members.has(w.id) && visible(main, w.id)), boxes, viewW, viewH)
    : new Map();
  for (const w of wins) {
    const id = w.id, gid = members.get(id);
    const options = app.shared.windows[id] || {};
    const mainAnchor = gid && (main.groups[gid] || current.groups[gid] || {x: 0, y: 0});
    const priorPoint = discoveryPoint(id);
    const discovered = !main.windows[id] && !priorPoint;
    let mainPoint = mainArr.windows[id] || (!gid && priorPoint);
    if (!mainPoint || discovered) {
      const p = mainPoint || first.get(id) || place(w, gid, boxes, mainAnchor);
      if (!mainPoint) {
        mainPoint = {x: p.x, y: p.y};
        if (visible(main, id, gid)) boxes.set(id, {id, ...mainPoint, w: w.wc, h: w.hc, g: gid});
      }
      if (discovered) {
        const point = {x: p.x, y: p.y};
        seeds.main_windows[id] = point;
        if (current === main) main.hidden[id] ??= false;
        current.windows[id] ??= point;
        if (current !== main && current.hidden[id] === undefined) {
          current.hidden[id] = true;
          if (!gid) visibilityChanged = true;
        }
        saveChanged = true;
      }
    }
    if (!entry(id)) {
      if (gid) {
        // A migrated group can have no positioned members and no anchor.
        // With no prior effective member position, reconciliation uses the origin.
        const anchor = current.groups[gid] ??= {x: 0, y: 0};
        const dx = options.dx ?? mainPoint.x - mainAnchor.x;
        const dy = options.dy ?? mainPoint.y - mainAnchor.y;
        const point = {x: anchor.x + dx, y: anchor.y + dy};
        arr.windows[id] = {...options, ...point};
        delete arr.windows[id].dx; delete arr.windows[id].dy;
        if (!('dx' in options)) saveChanged = true;
      } else {
        const p = current.windows[id] || (current === main ? mainPoint : place(w, null, localBoxes));
        if (!current.windows[id]) {
          current.windows[id] = patch.windows[id] = {x: p.x, y: p.y};
        }
        arr.windows[id] = {...options, x: p.x, y: p.y};
      }
      if (current.links.windows[id]) entry(id).links = current.links.windows[id];
      if (visible(current, id, gid)) localBoxes.set(id, boxOf(w));
    }
    if (w.colsKeep && entry(id).cols !== w.colsKeep) { entry(id).cols = w.colsKeep; saveChanged = true; }
  }
  return {saveChanged, seeds, patch, visibilityChanged};
}

// Temporarily normalise each rigid block for the force solver.
function forcePositions(wins, boxes, viewW, viewH) {
  const nodes = [], nodeOf = new Map(), empties = [], groups = new Map();
  for (const w of wins) {
    const b = boxes.get(w.id);
    if (!b?.g) continue;
    if (!groups.has(b.g)) groups.set(b.g, []);
    groups.get(b.g).push(w);
  }
  for (const [gid, members] of groups) {
    const cells = members.map(w => boxes.get(w.id)), bb = bounds(cells);
    const block = cells.map(b => ({...b, x: b.x - bb.x0, y: b.y - bb.y0}));
    const frame = framePixels(block);
    const g = app.arr.groups.find(g => g.id === gid);
    const node = {id: 'group:' + gid, name: g.name, w: frame.w, h: frame.h + CH, peers: new Map(), weight: 0, block, group: true};
    members.forEach(w => { node.weight += w.agents.length; nodeOf.set(w, node); });
    nodes.push(node);
  }
  wins.forEach(function (w) {
    if (nodeOf.has(w)) return;
    if (!w.agents.length) { empties.push(w); return; }
    const node = { id: w.id, name: w.sourceName, w: w.w, h: w.h, peers: new Map(), weight: w.agents.length,
      block: [{ id: w.id, x: 0, y: 0, w: w.wc, h: w.hc, g: null }] };
    nodeOf.set(w, node);
    nodes.push(node);
  });
  wins.forEach(function (w) {
    const a = nodeOf.get(w);
    if (a) w.peers.forEach(function (count, peer) {
      const b = nodeOf.get(peer);
      if (b && b !== a) a.peers.set(b, (a.peers.get(b) || 0) + count);
    });
  });
  forceLayout(nodes, Math.max(300, viewW || 1400), Math.max(300, viewH || 800), GAPX + 16, GAPY);
  // nearest to the middle first, so rounding pushes boxes outwards, not into each other
  nodes.sort(function (a, b) { return Math.hypot(a.x, a.y) - Math.hypot(b.x, b.y) || byName(a, b); });
  const placed = settle(nodes.map(function (node) {
    let x0, y0;
    if (node.group) {   // the node is the frame plus its title; the block starts 30 px in and two cells down
      x0 = Math.round((node.x - node.w / 2 + 30) / CW);
      y0 = Math.round((node.y - node.h / 2 + CH) / CH) + 2;
    } else {
      x0 = Math.round((node.x - node.w / 2) / CW);
      y0 = Math.round((node.y - node.h / 2) / CH);
    }
    return node.block.map(function (b) { return Object.assign({}, b, { x: b.x + x0, y: b.y + y0 }); });
  }));
  // windows with no agents: a tidy row under the map
  const bb = bounds(Array.from(placed.values()));
  let cx = bb.x0, cy = bb.y1 + 1;
  empties.sort(byName).forEach(function (w) {
    if (cx > bb.x0 && cx + w.wc > Math.max(bb.x1, bb.x0 + 24)) { cx = bb.x0; cy += w.hc; }
    const b = { id: w.id, x: cx, y: cy, w: w.wc, h: w.hc, g: null };
    const off = nearestFree(placed, [b]);
    b.x += off.dx; b.y += off.dy;
    placed.set(w.id, b);
    cx = b.x + b.w; cy = b.y;
  });
  return placed;
}

function moveBlocks(positions) {
  const patch = {groups: {}, windows: {}};
  for (const [id, p] of positions) {
    const before = entry(id), g = groupOf(id);
    if (g && g.id in patch.groups) continue;
    const dx = p.x - before.x, dy = p.y - before.y;
    if (!dx && !dy) continue;
    if (g) Object.assign(patch.groups, translateGroup(g, dx, dy).groups);
    else Object.assign(patch.windows, setStandalone(id, p.x, p.y).windows);
  }
  return patch;
}

export function autoLayout(viewW, viewH) {
  const boxes = scene();
  return moveBlocks(forcePositions(app.model.wins.filter(w => boxes.has(w.id)), boxes, viewW, viewH));
}

export function tidyAll() { return moveBlocks(tidy(scene())); }

// Drops one box, or the open members of one group shifted together, at the free spot
// nearest to the wanted cells. `wanted` maps window id -> {x, y}. Returns the final
// cells per id (same shape), without changing the arrangement; null when a group
// member has no free spot (its group's frame would cover other boxes wherever it went).
export function landing(wins, wanted) {
  const moving = wins.map(function (w) {
    const g = groupOf(w.id), p = wanted.get(w.id);
    return { id: w.id, x: p.x, y: p.y, w: w.wc, h: w.hc, g: g ? g.id : null };
  });
  const off = nearestFree(scene(), moving), out = new Map();
  if (off.stuck) return null;
  moving.forEach(function (b) { out.set(b.id, { x: b.x + off.dx, y: b.y + off.dy, w: b.w, h: b.h, g: b.g }); });
  return out;
}

export function applyPositions(cells) {
  let changed = false;
  cells.forEach(function (p, id) {
    const e = entry(id);
    if (!e || e.x !== p.x || e.y !== p.y) { setPos(id, p.x, p.y); changed = true; }
  });
  return changed;
}

// cols: a number the user fixes, or null for automatic (by agent count).
export function setCols(w, cols) {
  const e = entry(w.id);
  if (cols) { e.cols = cols; e.fixed = true; } else { delete e.cols; delete e.fixed; }
  sizeBox(w, app.arr);
  if (w.colsKeep) e.cols = w.colsKeep;
}

// ---- groups: membership is stored; the frame is always derived from the members ----

function leaveGroups(wid) {
  app.arr.groups.forEach(function (g) { g.members = g.members.filter(function (id) { return id !== wid; }); });
  app.arr.groups = app.arr.groups.filter(function (g) { return g.members.length; });
}

function newGroup(name, wins) {
  let id;
  do { id = 'g' + Array.from(crypto.getRandomValues(new Uint8Array(6)), n => n.toString(16).padStart(2, '0')).join(''); }
  while (app.arr.groups.some(g => g.id === id) || app.layouts.some(l => id in l.groups || id in l.hidden || id in l.links.groups));
  wins.forEach(function (w) { leaveGroups(w.id); });
  const g = { id: id, name: cleanName(name) || 'group', members: wins.map(function (w) { return w.id; }) };
  app.arr.groups.push(g);
  return g;
}

export function createGroup(name, w) {
  const g = newGroup(name, [w]);
  ensureClear([w]);   // the frame claims more room than the bare box did
  return seedGroup(g);
}

function seedGroup(g) {
  const bb = bounds(g.members.filter(entry).map(entry).map(p => ({...p, w: 0, h: 0})));
  const point = currentLayout().groups[g.id] = {x: bb.x0, y: bb.y0};
  currentLayout().hidden[g.id] = false;
  return {groups: {[g.id]: point}};
}

export function addToGroup(g, w) {
  const others = g.members.map(id => app.model.allWinById.get(id)).filter(o => o && o !== w && entry(o.id));
  leaveGroups(w.id);
  g = app.arr.groups.filter(function (x) { return x.id === g.id; })[0] || g;
  if (g.members.indexOf(w.id) < 0) g.members.push(w.id);
  if (app.arr.groups.indexOf(g) < 0) app.arr.groups.push(g);
  if (others.length) {   // drop it beside the group's other members
    const bb = bounds(others.map(boxOf));
    setPos(w.id, bb.x1, bb.y0);
  }
  if (visible(currentLayout(), w.id, g.id)) ensureClear([w]);
}

export function removeFromGroup(w) {
  leaveGroups(w.id);
  currentLayout().hidden[w.id] = false;
  ensureClear([w]);   // it may sit inside its former group's frame
  return detach([w.id]);
}

export function ungroup(g) {
  app.arr.groups = app.arr.groups.filter(function (x) { return x.id !== g.id; });
  return detach(g.members);
}

function detach(ids) {
  const windows = {};
  for (const id of ids) {
    currentLayout().hidden[id] = false;
    const p = entry(id);
    if (p) Object.assign(windows, setStandalone(id, p.x, p.y).windows);
  }
  return {windows};
}

function tokens(name) { return name.split(/[-_.\s]+/).filter(Boolean); }

// Packs a group's open members into one block near where they were.
function gatherGroup(g) {
  const members = openMembers(g).filter(function (w) { return entry(w.id); }).sort(readingOrder);
  if (!members.length) return;
  const rel = gather(members.map(function (w) { return { id: w.id, w: w.wc, h: w.hc }; }));
  const bb = bounds(members.map(boxOf));
  let wide = 0, high = 0;
  members.forEach(function (w) { wide = Math.max(wide, rel.get(w.id).x + w.wc); high = Math.max(high, rel.get(w.id).y + w.hc); });
  const x0 = Math.round((bb.x0 + bb.x1 - wide) / 2), y0 = Math.round((bb.y0 + bb.y1 - high) / 2);
  const wanted = new Map();
  members.forEach(function (w) { wanted.set(w.id, { x: x0 + rel.get(w.id).x, y: y0 + rel.get(w.id).y }); });
  applyPositions(landing(members, wanted) || wanted);
}

// Proposes groups for ungrouped windows from their names: windows sharing their first
// two name parts ("studio-print-…") form a group; what is left of those sharing the
// first part ("gallery-…") forms another. Existing groups are not touched.
// Returns the names of the groups created.
export function groupByPrefix() {
  const buckets = new Map();
  app.model.wins.forEach(function (w) {
    if (groupOf(w.id)) return;
    const t = tokens(w.sourceName.toLowerCase());
    if (!t.length) return;
    if (!buckets.has(t[0])) buckets.set(t[0], []);
    buckets.get(t[0]).push(w);
  });
  const plans = [];
  function make(wins) {
    const parts = wins.map(function (w) { return tokens(w.sourceName); });
    let n = 0;
    while (parts.every(function (p) { return p.length > n && p[n].toLowerCase() === parts[0][n].toLowerCase(); })) n++;
    plans.push({ name: parts[0].slice(0, Math.max(1, n)).join('-'), wins: wins.slice().sort(byName) });
  }
  buckets.forEach(function (wins) {
    if (wins.length < 2) return;
    const subs = new Map(), rest = [];
    wins.forEach(function (w) {
      const key = tokens(w.sourceName.toLowerCase())[1] || '';
      if (!subs.has(key)) subs.set(key, []);
      subs.get(key).push(w);
    });
    subs.forEach(function (sub, key) {
      if (key && sub.length >= 2 && sub.length < wins.length) make(sub); else rest.push.apply(rest, sub);
    });
    if (rest.length >= 2) make(rest);
  });
  // One group at a time, largest first: a group that exists but is not packed yet has a
  // frame spanning wherever its windows happen to be, and would push the others away.
  plans.sort(function (a, b) { return b.wins.length - a.wins.length || a.name.localeCompare(b.name); });
  const seeds = {groups: {}};
  const names = plans.map(function (plan) {
    const g = newGroup(plan.name, plan.wins);
    gatherGroup(g);
    Object.assign(seeds.groups, seedGroup(g).groups);
    return g.name;
  });
  return {names, seeds};
}
