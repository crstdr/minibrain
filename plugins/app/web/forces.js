// Automatic layout: springs between linked nodes, nodes never overlap. Pure: no DOM,
// no state. A node is {id, name, w, h, peers: Map(node -> link count), weight}; the
// result is each node's centre in pixels (x, y). The grid module then snaps them.

import { byName, clamp } from './util.js';

function collide(list, iterations, padX, padY) {
  for (let it = 0; it < iterations; it++) {
    let moved = false;
    for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
      const a = list[i], b = list[j];
      const dx = b.x - a.x, dy = b.y - a.y;
      const ox = (a.w + b.w) / 2 + padX - Math.abs(dx), oy = (a.h + b.h) / 2 + padY - Math.abs(dy);
      if (ox <= 0 || oy <= 0) continue;
      moved = true;
      if (ox < oy) { const sx = (dx < 0 ? -1 : 1) * ox; a.x -= sx / 2; b.x += sx / 2; }
      else { const sy = (dy < 0 ? -1 : 1) * oy; a.y -= sy / 2; b.y += sy / 2; }
    }
    if (!moved) break;
  }
}

function reach(w, ux, uy) {   // centre-to-edge distance of a box along a direction
  const ax = Math.abs(ux), ay = Math.abs(uy);
  return Math.min(ax > 1e-6 ? w.w / 2 / ax : Infinity, ay > 1e-6 ? w.h / 2 / ay : Infinity);
}

function runForces(nodes, pairs, squash, turn, padX, padY) {
  nodes.forEach(function (w, i) {
    const r = 200 * Math.sqrt(i + 0.35), th = i * 2.39996323 + turn;
    w.x = r * Math.cos(th) * 1.5; w.y = r * Math.sin(th); w.vx = 0; w.vy = 0;
  });
  const T = 480;
  for (let t = 0; t < T; t++) {
    const cooling = Math.pow(1 - t / T, 1.3);
    pairs.forEach(function (p) {
      const a = p[0], b = p[1], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
      const ux = dx / d, uy = dy / d;
      const rest = reach(a, ux, uy) + reach(b, ux, uy) + 80;
      const k = 0.085 / Math.sqrt(Math.min(a.peers.size, b.peers.size)) * Math.min(1.7, 0.6 + 0.16 * p[2]);
      const f = (d - rest) * k * cooling;
      a.vx += ux * f; a.vy += uy * f; b.vx -= ux * f; b.vy -= uy * f;
    });
    for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1;
      const ux = dx / d, uy = dy / d;
      const gap = Math.max(50, d - reach(a, ux, uy) - reach(b, ux, uy));
      const f = 52000 / (gap * gap) * cooling;
      a.vx -= ux * f; a.vy -= uy * f; b.vx += ux * f; b.vy += uy * f;
    }
    nodes.forEach(function (w) {
      const g = w.peers.size ? 0.0055 : 0.0085;
      w.vx -= w.x * g * cooling; w.vy -= w.y * g * squash * cooling;
      w.vx *= 0.62; w.vy *= 0.62;
      w.x += w.vx; w.y += w.vy;
    });
    collide(nodes, 2, padX, padY);
  }
  // tighten: slide every box towards the middle until its neighbours stop it
  for (let n = 0; n < 140; n++) {
    nodes.forEach(function (w) { w.x -= w.x * 0.03; w.y -= w.y * 0.03 * Math.min(squash, 4); });
    collide(nodes, 3, padX, padY);
  }
  collide(nodes, 80, padX, padY);
}

// Different settings of the same forces give differently shaped maps; the one that shows
// largest in a W x H view is kept. Same nodes and view always give the same map.
export function forceLayout(nodes, W, H, padX, padY) {
  nodes.sort(function (a, b) { return b.peers.size - a.peers.size || b.weight - a.weight || byName(a, b); });
  const pairs = [];
  nodes.forEach(function (a) { a.peers.forEach(function (n, b) { if (a.id < b.id) pairs.push([a, b, n]); }); });
  const aspect = clamp(W / H, 1, 2.6);
  let best = null;
  [1.4, 2.2, 3.0, 3.8].forEach(function (power) {
    [0, 2.1, 4.2].forEach(function (turn) {
      runForces(nodes, pairs, Math.pow(aspect, power), turn, padX, padY);
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      nodes.forEach(function (w) {
        x0 = Math.min(x0, w.x - w.w / 2); x1 = Math.max(x1, w.x + w.w / 2);
        y0 = Math.min(y0, w.y - w.h / 2); y1 = Math.max(y1, w.y + w.h / 2);
      });
      const k = Math.min(W / (x1 - x0 + 112), H / (y1 - y0 + 200));
      if (!best || k > best.k) best = { k: k, at: nodes.map(function (w) { return [w.x, w.y]; }) };
    });
  });
  if (best) nodes.forEach(function (w, i) { w.x = best.at[i][0]; w.y = best.at[i][1]; });
}
