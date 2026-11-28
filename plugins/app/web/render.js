import { canEdit, persistViewport } from './actions.js';
// Everything drawn on the map: boxes, chips, group frames, links, the view transform
// and the highlight. The only module that creates map DOM.

import { groupName } from './model.js';
import { app, currentLayout, groupOf } from './state.js';
import { stateText } from './model.js';
import { attentionIcon, glowDelay, phaseDelay } from './attention.js';
import { $, el, svg, clamp, store } from './util.js';
import { CHIP_W, CHIP_H, CW, CH, conflicts, framePixels } from './grid.js';
import { boxOf, openMembers, scene } from './layout.js';
import { applyFill, fillId, groupHue, heatFill, theme } from './colors.js';

export const WARN = 60, CRIT = 80;   // context-ring thresholds, percent
const VIEW_KEY = 'agents-map.view.v2';
const stage = $('stage'), world = $('world');
const layerFrames = $('layer-frames'), layerBg = $('layer-bg'), layerFg = $('layer-fg'), edgeG = $('edge-g');

export let frames = [];   // drawn group frames: {g, el, x, y, w, h, members}

function buildChip(a) {
  const node = el('div', 'agent ' + a.cliClass);
  node.tabIndex = 0;
  node.setAttribute('role', 'group');
  node.dataset.id = a.id;
  node.style.left = a.cx + 'px'; node.style.top = a.cy + 'px';
  if (a.out.length) node.classList.add('overseer');
  if (!a.linked) node.classList.add('unlinked');
  if (a.pinned) node.classList.add('pinned');
  if (a.run) node.classList.add(a.run);
  if (a.needs && !a.seen) {
    node.classList.add('glow');
    // Phase from the wall clock so a redraw carries on instead of restarting; inserted first
    // so the box's own badges and text paint over it.
    node.insertBefore(needRing(glowDelay()), node.firstChild);
  }
  if (a.state === 'failed') node.classList.add('failed');
  if (a.pct != null && a.pct >= CRIT) node.classList.add('crit');
  else if (a.pct != null && a.pct >= WARN) node.classList.add('warn');

  const disc = el('span', 'disc');
  const s = svg('svg', { viewBox: '0 0 32 32', 'aria-hidden': 'true' });
  s.appendChild(svg('circle', { 'class': 'track', cx: 16, cy: 16, r: 14 }));
  if (a.pct != null) {
    const C = 2 * Math.PI * 14;
    s.appendChild(svg('circle', { 'class': 'arc', cx: 16, cy: 16, r: 14, transform: 'rotate(-90 16 16)',
      'stroke-dasharray': (a.pct / 100 * C).toFixed(2) + ' ' + C.toFixed(2) }));
  }
  s.appendChild(svg('circle', { 'class': 'core', cx: 16, cy: 16, r: 10 }));
  disc.appendChild(s);
  disc.appendChild(el('span', 'abbr', a.abbr));
  disc.appendChild(el('span', 'run'));
  node.appendChild(disc);

  const txt = el('span', 'txt'), top = el('span', 'top');
  top.appendChild(el('span', 'name', a.name));
  if (a.pinned) top.appendChild(pinMark());
  const deg = (a.out.length ? '→' + a.out.length : '') + (a.out.length && a.inn.length > 1 ? ' ' : '') + (a.inn.length > 1 ? '←' + a.inn.length : '');
  if (deg) top.appendChild(el('span', 'deg', deg));
  txt.appendChild(top);
  const meta = el('span', 'meta');
  meta.appendChild(el('span', 'model', a.model + (a.effort ? ' · ' + a.effort : '')));
  if (a.wakeText) { meta.appendChild(el('span', 'wake', a.wakeText)); node.classList.add('has-wake'); }
  meta.appendChild(el('span', 'pct', a.pct != null ? Math.round(a.pct) + '%' : '–'));
  txt.appendChild(meta);
  node.appendChild(txt);

  const href = workspaceLink(a.ws, a.tab, a.id);
  if (href) {
    const open = el('a', 'agent-open', '↗');
    open.href = href;
    open.draggable = false;
    open.setAttribute('aria-label', 'Open in RepoPrompt');
    node.appendChild(open);
  }

  // Attention count badge (top-left) and open count / roadmap chip (top-right).
  if (a.attItems && a.attItems.length) {
    const activeCount = a.attItems.filter(it => !it.snoozedUntil).length;
    const muted = activeCount === 0;
    const left = el('span', 'att-left');
    const b = el('span', 'att-badge' + (muted ? ' muted' : ' alert'));
    b.appendChild(attentionIcon());
    b.appendChild(el('span', 'att-n', String(muted ? a.attItems.length : activeCount)));
    if (!muted) b.appendChild(el('span', 'att-word', 'attention'));
    left.appendChild(b);
    node.appendChild(left);
  }
  if (a.roadmaps && a.roadmaps.length) {
    const owned = a.roadmaps.filter(r => r.mode === 'owner');
    const first = owned[0] || a.roadmaps[0];
    const chip = el('button', 'rm-chip');
    chip.type = 'button';
    chip.dataset.roadmap = first.id;
    if (first.lane) chip.dataset.lane = first.lane;
    const ic = svg('svg', { viewBox: '0 0 12 12', 'aria-hidden': 'true' });
    ic.appendChild(svg('circle', { cx: 2.2, cy: 6, r: 1.6, fill: 'currentColor' }));
    ic.appendChild(svg('circle', { cx: 9.8, cy: 3, r: 1.6, fill: 'currentColor' }));
    ic.appendChild(svg('circle', { cx: 9.8, cy: 9, r: 1.6, fill: 'currentColor' }));
    ic.appendChild(svg('path', { d: 'M3.8 6 C6 6 6.5 3 8.2 3 M3.8 6 C6 6 6.5 9 8.2 9', stroke: 'currentColor', 'stroke-width': 1.3, fill: 'none' }));
    const openCount = a.items.length || first.open;
    const label = openCount ? openCount + ' open' : 'roadmap';
    chip.appendChild(ic);
    chip.appendChild(el('span', '', label));
    node.appendChild(chip);
  } else if (a.items && a.items.length) {
    const chip = el('button', 'open-chip', a.items.length + ' open');
    chip.type = 'button';
    node.appendChild(chip);
  }

  node.setAttribute('aria-label', a.name + ', ' + a.cliName + ' ' + a.model + (a.effort ? ' ' + a.effort : '') +
    ', context ' + (a.pct != null ? Math.round(a.pct) + ' percent' : 'unknown') + (a.pinned ? ', pinned' : '') +
    (a.linked ? ', oversees ' + a.out.length + ', overseen by ' + a.inn.length : ', no oversight links') +
    ', window ' + a.win.name + ', ' + stateText(a, true) +
    (a.attItems.length ? ', ' + a.attItems.length + ' attention' : '') +
    (a.items.length ? ', ' + a.items.length + ' open' : ''));
  a.el = node;
  return node;
}

// The dashed outline that travels around a box that needs the user (map.css: .need-ring; the rect's own
// animation carries the phase, set here from the clock).
function needRing(delay) {
  const s = svg('svg', { 'class': 'need-ring', 'aria-hidden': 'true' });
  const r = svg('rect', { width: '100%', height: '100%' });
  r.style.animationDelay = delay;
  s.appendChild(r);
  return s;
}

export function workspaceLink(ws, tab, session) {
  if (app.graph?.demo) return null;
  const params = new URLSearchParams({workspace_id: ws});
  if (tab) {
    params.set('tab_id', tab);
    if (session) params.set('session_id', session);
  }
  return 'repoprompt-ce://workspace/open?' + params;
}

export function pinMark() {
  const s = svg('svg', { 'class': 'pin', viewBox: '0 0 12 12', 'aria-hidden': 'true' });
  s.appendChild(svg('path', { d: 'M7.4 0.8 11.2 4.6 10.1 5.2 8 7.3 8.3 9.9 7.5 10.7 5.1 8.3 1.6 11.8 0.9 11.8 0.9 11.1 4.4 7.6 2 5.2 2.8 4.4 5.4 4.7 7.5 2.6Z' }));
  return s;
}

// Rebuilds the map's DOM from app.model. Used at start and by every Refresh, so there
// is one drawing path.
export function renderAll() {
  const m = app.model;
  const focused = document.activeElement;
  const focusedChip = focused.closest('.agent');
  layerBg.textContent = ''; layerFg.textContent = ''; edgeG.textContent = '';
  lit = [];
  m.wins.forEach(function (w) {
    w.bg = el('div', 'win-bg');
    w.fg = el('div', 'win' + (w.agents.length ? '' : ' empty'));
    w.fg.dataset.id = w.id;
    if (w.closed) { w.bg.classList.add('closed'); w.fg.classList.add('closed'); }
    const title = el('a', 'win-title');
    const href = workspaceLink(w.id, w.tab, w.session);
    if (href) title.href = href;
    title.draggable = false;
    if (w.workspaceColor) {
      const dot = el('span', 'workspace-dot');
      dot.dataset.color = w.workspaceColor;
      title.appendChild(dot);
    }
    title.appendChild(el('span', '', w.title));
    if (w.agents.length) title.appendChild(el('span', 'n', String(w.agents.length)));
    w.fg.appendChild(title);
    if (!w.agents.length) w.fg.appendChild(el('div', 'none', 'no agents shown'));
    w.agents.forEach(function (a) { w.fg.appendChild(buildChip(a)); });
    [w.bg, w.fg].forEach(function (e) { e.style.width = w.w + 'px'; e.style.height = w.h + 'px'; });
    layerBg.appendChild(w.bg);
    layerFg.appendChild(w.fg);
    w.titleEl = title;
  });
  m.links.forEach(function (l) {
    l.path = svg('path', { 'class': l.activity ? 'edge active ' + l.activity : 'edge' });
    if (l.activity) l.path.style.animationDelay = phaseDelay(1200);   // matches the edge march in map.css
    edgeG.appendChild(l.path);
  });
  sync();
  const nextChip = focusedChip && m.byId.get(focusedChip.dataset.id)?.el;
  if (nextChip) {
    const next = focused === focusedChip ? nextChip : nextChip.querySelector(
      focused.matches('.agent-open') ? '.agent-open' : focused.matches('.open-chip') ? '.open-chip' : '.rm-chip'
    );
    (next || nextChip).focus({ preventScroll: true });
  }
}

// Which way a link is drawn: hidden when either end (agent or its window) hides its
// links; coloured by the first colour set among overseer, overseen, overseer's window,
// overseen's window.
// What an agent, window or group asks for its links: 'show' or 'hide' regardless of the
// All links switch, or null to follow it.
export function linksSetting(e) {
  if (!e) return null;
  return e.links === 'show' || e.links === 'hide' ? e.links : e.hide ? 'hide' : null;
}

// One end of a link follows the most specific choice: its agent's, else its window's, else
// the window's group's.
function endSetting(a) {
  return linksSetting(app.arr.agents[a.id]) || linksSetting(app.arr.windows[a.win.id]) || linksSetting(groupOf(a.win.id));
}

// A link is shown if either end asks to show its links (asking to see something's links
// means all of them), hidden if an end asks to hide them, and otherwise follows the button.
function linkStyle(l) {
  const A = app.arr.agents, W = app.arr.windows;
  const ends = [endSetting(l.src), endSetting(l.dst)], show = ends.indexOf('show') >= 0;
  let color = null;
  [A[l.src.id], A[l.dst.id], W[l.src.win.id], W[l.dst.win.id]].forEach(function (e) { if (e && e.color && !color) color = e.color; });
  return { show: show, off: !show && ends.indexOf('hide') >= 0, color: /^c[123]$/.test(color || '') ? color : null };
}

// Applies the arrangement to what is drawn: box positions, group frames, link styles
// and the too-close marks. Cheap; called after every arrangement change.
export function sync() {
  const m = app.model, mode = theme();
  m.wins.forEach(function (w) {
    const e = app.arr.windows[w.id];
    if (e) { w.px = e.x * CW; w.py = e.y * CH; }
  });
  // Boxes further right paint later, so a long title that reaches over its right-hand
  // neighbour's is cut by it, and every title's start stays readable (hover shows it whole).
  m.wins.slice().sort(function (a, b) { return a.px - b.px || a.py - b.py; })
    .forEach(function (w) { layerFg.appendChild(w.fg); });
  layerFrames.textContent = '';
  frames = [];
  app.arr.groups.forEach(function (g) {
    const members = openMembers(g).filter(function (w) { return app.arr.windows[w.id]; });
    if (!members.length) return;
    const r = framePixels(members.map(boxOf));
    const node = el('div', 'frame'), title = el('div', 'frame-title');
    node.dataset.gid = g.id; title.dataset.gid = g.id;
    title.appendChild(el('span', '', groupName(g)));
    title.appendChild(el('span', 'n', String(members.length)));
    node.appendChild(title);
    node.style.width = r.w + 'px'; node.style.height = r.h + 'px';
    layerFrames.appendChild(node);
    frames.push({ g: g, el: node, title: title, x: r.x, y: r.y, w: r.w, h: r.h, members: members });
    const hue = groupHue(g);
    applyFill(node, hue && fillId(hue, 1), mode, true);
  });
  const c = conflicts(scene());
  m.wins.forEach(function (w) {
    w.bg.classList.toggle('overlap', c.boxes.has(w.id));
  });
  // An agent's colour: its group's hue at its activity's intensity. Fills set earlier on a
  // window or an agent stay in the arrangement but are not used.
  m.agents.forEach(function (a) {
    applyFill(a.el, heatFill(groupHue(groupOf(a.win.id)), a.heat), mode);
    a.el.dataset.heat = a.heat;
  });
  frames.forEach(function (f) { f.el.classList.toggle('overlap', c.groups.has(f.g.id)); });
  app.externalConflicts = c.external.size;
  app.tooClose = c.boxes.size + c.groups.size;
  m.links.forEach(function (l) {
    const s = linkStyle(l);
    l.path.classList.toggle('off', s.off);
    l.path.classList.toggle('force', s.show);
    ['c1', 'c2', 'c3'].forEach(function (slot) { l.path.classList.toggle(slot, s.color === slot); });
  });
  world.classList.toggle('nolinks', !app.ui.links);
  world.classList.toggle('wake', app.ui.wake);
  world.classList.toggle('nocounts', !app.ui.counts);
  $('index').classList.toggle('nocounts', !app.ui.counts);
  place();
  refreshHighlight();
}

/* ---------- geometry ---------- */
function rectOf(a) { return { x: a.win.px + a.cx, y: a.win.py + a.cy, w: CHIP_W, h: CHIP_H }; }

function edgePath(S, T, sameSideLeft) {
  const sx = S.x + S.w / 2, sy = S.y + S.h / 2, tx = T.x + T.w / 2, ty = T.y + T.h / 2;
  if (Math.abs(tx - sx) < (S.w + T.w) / 2 + 26) {
    // stacked or same column: leave and arrive on the same side with a bulge
    const side = sameSideLeft ? -1 : 1;
    const x0 = sx + side * S.w / 2, x1 = tx + side * T.w / 2;
    const b = side * clamp(26 + Math.abs(ty - sy) * 0.16, 30, 150);
    const far = side > 0 ? Math.max(x0, x1) : Math.min(x0, x1);
    return 'M' + x0 + ',' + sy + ' C' + (far + b) + ',' + sy + ' ' + (far + b) + ',' + ty + ' ' + x1 + ',' + ty;
  }
  const dir = tx > sx ? 1 : -1;
  const ax = sx + dir * S.w / 2, bx = tx - dir * T.w / 2;
  const c = Math.max(46, Math.abs(bx - ax) * 0.42);
  return 'M' + ax + ',' + sy + ' C' + (ax + dir * c) + ',' + sy + ' ' + (bx - dir * c) + ',' + ty + ' ' + bx + ',' + ty;
}

export function placeWin(w) {
  const css = 'translate(' + w.px + 'px,' + w.py + 'px)';
  w.bg.style.transform = css; w.fg.style.transform = css;
}

export function placeLinks(list) {
  list.forEach(function (l) {
    l.path.setAttribute('d', edgePath(rectOf(l.src), rectOf(l.dst), l.src.win === l.dst.win && l.src.col === 0 && l.dst.col === 0));
  });
}

export function placeFrame(f, dx, dy) {
  f.el.style.transform = 'translate(' + (f.x + (dx || 0)) + 'px,' + (f.y + (dy || 0)) + 'px)';
}

export function place() {
  app.model.wins.forEach(placeWin);
  frames.forEach(function (f) { placeFrame(f); });
  placeLinks(app.model.links);
}

export function linksOf(wins) {
  const seen = new Set();
  wins.forEach(function (w) { w.agents.forEach(function (a) { a.out.forEach(function (l) { seen.add(l); }); a.inn.forEach(function (l) { seen.add(l); }); }); });
  return Array.from(seen);
}

/* ---------- view: pan, zoom, fit ---------- */
export function applyView(animate) {
  const view = app.ui.view;
  if (animate) { world.classList.add('anim'); setTimeout(function () { world.classList.remove('anim'); }, 300); }
  world.style.transform = 'translate(' + view.tx + 'px,' + view.ty + 'px) scale(' + view.k + ')';
  world.style.setProperty('--title-scale', clamp(0.95 / view.k, 1, 3.4).toFixed(3));
  const nameSize = clamp(9.4 / view.k, 12.5, 20);          // world px; about 9 px on screen when far out
  world.style.setProperty('--name-fs', nameSize.toFixed(2) + 'px');
  world.style.setProperty('--inv-k', (1 / view.k).toFixed(4));   // world px per screen px, so marching dashes keep their size on screen
  world.style.setProperty('--att-scale', Math.max(1, 1 / view.k).toFixed(3));   // badges never read smaller than at zoom 1
  // Enlarged badges keep the mark and count only: the word would run over the box's name and its neighbour.
  world.classList.toggle('tight', view.k < 1);
  world.classList.toggle('far', nameSize > 16.5);          // no room left for the model line
  let gw = (CW / 2) * view.k, gh = CH * view.k;
  if (gw < 14) { gw = CW * view.k; gh = 2 * CH * view.k; }
  if (gw < 12) {
    stage.style.backgroundImage = 'none';
  } else {
    stage.style.backgroundImage = '';
    stage.style.backgroundSize = gw.toFixed(2) + 'px ' + gh.toFixed(2) + 'px';
    stage.style.backgroundPosition = view.tx.toFixed(2) + 'px ' + view.ty.toFixed(2) + 'px';
  }
}

export function restoreView() {
  const layout = currentLayout(), viewport = layout.viewport;
  const saved = viewport || (layout.id === 'main' && store('session', VIEW_KEY));
  if (saved && !saved.auto && Number.isFinite(saved.k) && saved.k >= 0.12 && saved.k <= 2.6
      && [saved.tx, saved.ty].every(n => Number.isFinite(n) && Math.abs(n) <= 1e9)) {
    app.ui.view = {k: saved.k, tx: saved.tx, ty: saved.ty, auto: false};
    applyView(false);
  } else fit(false, false);
  if (!viewport) persistViewport();
  if (layout.id === 'main') store('session', VIEW_KEY, null);
}

// The part of the stage not covered by the group index (left) or the table (right).
export function visibleArea() {
  const index = $('index'), table = $('table-panel');
  const left = index.classList.contains('collapsed') ? 0 : index.offsetWidth + 20;
  const right = table.hidden ? 0 : table.offsetWidth;
  return { left: left, w: Math.max(200, stage.clientWidth - left - right), h: Math.max(200, stage.clientHeight) };
}

function mapBounds() {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  function add(x, y, w, h) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x + w); y1 = Math.max(y1, y + h); }
  app.model.wins.forEach(function (w) { add(w.px, w.py, w.w, w.h); });
  frames.forEach(function (f) { add(f.x, f.y - CH, f.w, f.h + CH); });
  return isFinite(x0) ? { x0: x0, y0: y0, x1: x1, y1: y1 } : { x0: 0, y0: 0, x1: 0, y1: 0 };
}

export function fitRect(b, animate, persist = true) {
  if (persist && !canEdit()) return;
  const view = app.ui.view, area = visibleArea(), m = 56;
  const bw = b.x1 - b.x0 + 2 * m, bh = b.y1 - b.y0 + 2 * m + 40;   // 40: titles above the top row
  view.k = clamp(Math.min(area.w / bw, area.h / bh), 0.12, 1.25);
  view.tx = area.left + (area.w - (b.x0 + b.x1) * view.k) / 2;
  view.ty = (area.h - (b.y0 + b.y1 - 40) * view.k) / 2;
  view.auto = false;
  applyView(animate);
  if (persist) persistViewport();
}

export function fit(animate, persist = true) {
  if (persist && !canEdit()) return;
  fitRect(mapBounds(), animate, false);
  app.ui.view.auto = true;   // keep fitting when the browser window is resized
  applyView(false);
  if (persist) persistViewport();
}

export function fitWindow(w, animate, persist = true) { fitRect({ x0: w.px, y0: w.py, x1: w.px + w.w, y1: w.py + w.h }, animate, persist); }

export function fitGroup(g, animate, persist = true) {
  const f = frames.filter(function (x) { return x.g.id === g.id; })[0];
  if (f) fitRect({ x0: f.x, y0: f.y - CH, x1: f.x + f.w, y1: f.y + f.h }, animate, persist);
}

export function zoomAt(px, py, factor) {
  const view = app.ui.view, k = clamp(view.k * factor, 0.12, 2.6);
  view.tx = px - (px - view.tx) * (k / view.k);
  view.ty = py - (py - view.ty) * (k / view.k);
  view.k = k; view.auto = false;
  applyView(false);
  persistViewport(true);
}

export function centerOn(a) {
  if (!canEdit()) return;
  const view = app.ui.view, r = rectOf(a), area = visibleArea();
  view.k = Math.max(view.k, 0.9);
  view.tx = area.left + area.w / 2 - (r.x + r.w / 2) * view.k;
  view.ty = area.h / 2 - (r.y + r.h / 2) * view.k;
  view.auto = false;
  applyView(true);
  persistViewport();
}

/* ---------- highlight: what is lit for the thing hovered or pinned ---------- */
let lit = [];

export function targetAgents(t) {
  const m = app.model;
  if (!t) return [];
  if (t.kind === 'agent') { const a = m.byId.get(t.id); return a ? [a] : []; }
  if (t.kind === 'window') { const w = m.winById.get(t.id); return w ? w.agents : []; }
  const g = app.arr.groups.filter(function (x) { return x.id === t.id; })[0];
  return g ? [].concat.apply([], openMembers(g).map(function (w) { return w.agents; })) : [];
}

export function refreshHighlight() {
  const m = app.model;
  lit.forEach(function (x) { x.classList.remove('hl', 'hl-self', 'on', 'in'); });
  lit = [];
  m.agents.forEach(function (a) { a.el.classList.remove('selected'); });
  m.wins.forEach(function (w) { w.fg.classList.remove('selected'); });
  const pin = app.ui.pin;
  if (pin && pin.kind === 'agent' && m.byId.get(pin.id)) m.byId.get(pin.id).el.classList.add('selected');
  if (pin && pin.kind === 'window' && m.winById.get(pin.id)) m.winById.get(pin.id).fg.classList.add('selected');

  const t = app.ui.hover || pin;
  const list = targetAgents(t), set = new Set(list);
  world.classList.toggle('dim', list.length > 0);
  function light(node, a, b) { node.classList.add(a); if (b) node.classList.add(b); lit.push(node); }
  if (t && t.kind === 'window' && m.winById.get(t.id)) light(m.winById.get(t.id).bg, 'hl');
  if (t && t.kind === 'group') frames.forEach(function (f) { if (f.g.id === t.id) light(f.el, 'hl'); });
  list.forEach(function (a) { light(a.el, 'hl', t.kind === 'agent' ? 'hl-self' : null); });
  // Lit links go last so they paint over dimmed ones. A state-preserving move keeps
  // an active path's CSS animation running.
  function raise(path) {
    if (edgeG.moveBefore) edgeG.moveBefore(path, null);
    else edgeG.appendChild(path);
  }
  list.forEach(function (a) {
    a.out.forEach(function (l) { light(l.dst.el, 'hl'); light(l.path, 'on'); raise(l.path); });
    a.inn.forEach(function (l) {
      if (set.has(l.src)) return;   // drawn as an outgoing link of another agent in the set
      light(l.src.el, 'hl'); light(l.path, 'on', 'in'); raise(l.path);
    });
  });
}

export function winOfGroupLabel(wid) { const g = groupOf(wid); return g ? groupName(g) : null; }
