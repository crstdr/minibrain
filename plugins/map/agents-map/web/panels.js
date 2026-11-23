// Everything around the map: the bar (stats, status, history, saves), the tooltip,
// the filter, the table, the group index and the legend's notes.

import { app, currentLayout, groupOf } from './state.js';
import { $, el, ago, byName, clamp, cleanName, fmtTokens, plural, store } from './util.js';
import { groupByPrefix, openMembers } from './layout.js';
import { duration, groupName, layoutName, stateText, wakingLanes } from './model.js';
import { addSave, deleteSave, listSaves } from './server.js';
import { CRIT, WARN, centerOn, fit, fitGroup, fitWindow, frames, workspaceLink } from './render.js';
import { OLD_LIST, itemMeta, kindIcon, setSnooze } from './attention.js';
import { canEdit, changeLayout, changed, doTidy, flash, rebuild, restoreNamedSave, retry, setBoxHidden, setHover, setPin } from './actions.js';

const STALE_MINUTES = 15;

/* ---------- tooltip ---------- */
const tip = $('tip');

function names(list, pick, hiddenCount) {
  const shown = list.slice(0, 6).map(function (l) { return pick(l).name; }).join(', ');
  const more = list.length > 6 ? ', +' + (list.length - 6) + ' more' : '';
  const hid = hiddenCount ? ' (+' + hiddenCount + ' not shown)' : '';
  return list.length ? list.length + ': ' + shown + more + hid : (hiddenCount ? 'none drawn' + hid : 'none');
}

function itemControls(it) {
  const controls = el('span', 'item-controls');
  function button(label, duration) {
    const b = el('button', '', label);
    b.type = 'button';
    b.addEventListener('click', function () {
      if (!canEdit()) return;
      setSnooze(it, duration);
      rebuild();
    });
    controls.appendChild(b);
  }
  if (it.snoozedUntil) {
    const until = new Date(it.snoozedUntil);
    const hhmm = [until.getHours(), until.getMinutes()].map(n => String(n).padStart(2, '0')).join(':');
    button('snoozed until ' + hhmm, null);
  } else {
    button('1 h', 'hour');
    button('Tomorrow', 'tomorrow');
  }
  const owner = app.model.attention?.owner;
  const href = owner && workspaceLink(owner.ws, owner.tab, owner.id);
  if (href) {
    const ask = el('a', 'item-ask', 'Ask ' + owner.name);
    ask.href = href;
    ask.draggable = false;
    controls.appendChild(ask);
  }
  return controls;
}

function itemClass(it) {
  return it.snoozedUntil ? ' snoozed' : it.alert !== 'none' ? ' alert' : '';
}

function tipRows(title, sub, rows, cls, items) {
  tip.textContent = '';
  const heading = el('div', 't-name', title);
  heading.id = 'tip-name';
  tip.appendChild(heading);
  if (sub) tip.appendChild(el('div', 't-sub', sub));
  // Attention items first, each with its kind's mark and any due/rank beneath the reason.
  if (items && items.length) {
    const list = el('ul', 't-items');
    items.forEach(function (it) {
      const li = el('li', 't-item' + itemClass(it));
      const mark = el('span', 't-kind');
      mark.appendChild(kindIcon(it.kind));
      li.appendChild(mark);
      const body = el('span', 't-body'), meta = itemMeta(it);
      body.appendChild(el('span', 't-reason', it.reason));
      if (meta) body.appendChild(el('span', 't-meta', meta));
      body.appendChild(itemControls(it));
      li.appendChild(body);
      list.appendChild(li);
    });
    tip.appendChild(list);
  }
  const dl = el('dl', cls || '');
  rows.forEach(function (r) { dl.appendChild(el('dt', '', r[0])); dl.appendChild(el('dd', '', r[1])); });
  tip.appendChild(dl);
}

export function fillTip(target) {
  const m = app.model;
  if (target.kind === 'agent') {
    const a = m.byId.get(target.id);
    const rows = [
      ['Context', a.pct != null ? Math.round(a.pct) + '% · ' + fmtTokens(a.used) + ' of ' + fmtTokens(a.window)
        : (a.used ? fmtTokens(a.used) + ' used, window size unknown' : 'not recorded yet')],
      ['State', stateText(a) + (a.run && a.state_at ? ' · saved ' + ago(a.state_at) : '')],
      ['Last active', ago(a.last)],
      ['Window', a.win.name]
    ];
    if (a.linked) {
      rows.push(['Oversees', names(a.out, function (l) { return l.dst; }, a.out_hidden)]);
      rows.push(['Overseen by', names(a.inn, function (l) { return l.src; }, a.in_hidden)]);
    } else rows.push(['Links', 'no oversight links']);
    const items = m.attention?.owner === a ? a.items.concat(m.attention.loose) : a.items;
    if (a.lane_of && m.byId.get(a.lane_of)) rows.push(['Created by', m.byId.get(a.lane_of).name]);
    if (a.pinned) rows.push(['Pinned', 'yes, in the sidebar']);
    if (a.wakeText) {
      const w = a.wake, chosen = wakingLanes(a);
      rows.push(['Wakes on', w.all ? 'updates from every lane'
        : chosen.length ? 'updates from ' + chosen.map(function (l) { return l.dst.name; }).join(', ') : 'no lane updates (auto-wake off)']);
      if (w.all || chosen.length) rows.push(['At most', w.limit ? 'once every ' + duration(w.limit) : 'no delay']);
      rows.push(['Idle wake', w.idle ? 'after ' + duration(w.idle) + ' idle' : 'off']);
    }
    tipRows(a.name, a.cliName + ' · ' + a.model + (a.effort ? ' · ' + a.effort : ''), rows, 't-stats', items);
    return;
  }
  const g = app.arr.groups.filter(function (x) { return x.id === target.id; })[0];
  const wins = openMembers(g), title = groupName(g), sub = 'Group of ' + plural(wins.length, 'open window', 'open windows');
  const inside = new Set();
  let linked = 0, unlinked = 0;
  wins.forEach(function (w) { w.agents.forEach(function (a) { inside.add(a); if (a.linked) linked++; else unlinked++; }); });
  let out = 0, inn = 0, within = 0;
  inside.forEach(function (a) {
    a.out.forEach(function (l) { if (inside.has(l.dst)) within++; else out++; });
    a.inn.forEach(function (l) { if (!inside.has(l.src)) inn++; });
  });
  tipRows(title, sub, [
    ['Agents', linked + ' linked' + (unlinked ? ', ' + unlinked + ' without links' : '')],
    ['Links out', String(out)], ['Links in', String(inn)], ['Links inside', String(within)]
  ]);
}

// The card sits beside the selected agent's window, not in a corner and not under the pointer:
// to its right when the whole card fits in the map, else below, above or left; otherwise on the
// side with the most room, capped and scrolling as before. It never covers that window.
const TIP_INSET = 12, TIP_GAP = 10, TIP_MAX = 380;   // from the map's edges, from the window, and wide

function frameOf(target) {
  const m = app.model;
  if (!m) return null;
  if (target.kind === 'agent') {
    const a = m.byId.get(target.id);
    return a && a.win && a.win.fg ? a.win.fg.getBoundingClientRect() : null;
  }
  if (target.kind === 'window') {
    const w = m.winById.get(target.id);
    return w && w.fg ? w.fg.getBoundingClientRect() : null;
  }
  if (target.kind === 'group') {
    const f = frames.filter(function (x) { return x.g.id === target.id; })[0];
    return f ? f.el.getBoundingClientRect() : null;
  }
  return null;
}

function covers(a, b) {
  return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
}

function placeTip(target) {
  const stage = $('stage').getBoundingClientRect(), index = $('index').getBoundingClientRect();
  const box = frameOf(target);
  const bounds = {
    left: stage.left + TIP_INSET, top: stage.top + TIP_INSET,
    right: Math.max(stage.left + TIP_INSET, stage.right - TIP_INSET),
    bottom: Math.max(stage.top + TIP_INSET, stage.bottom - TIP_INSET)
  };
  const bw = bounds.right - bounds.left, bh = bounds.bottom - bounds.top;
  const measure = function (maxW, maxH) {
    tip.style.maxWidth = Math.max(1, Math.min(TIP_MAX, maxW)) + 'px';
    tip.style.maxHeight = Math.max(1, Math.min(bh, maxH)) + 'px';
    tip.style.left = '0px'; tip.style.top = '0px';   // measure at a known spot
    return { w: tip.offsetWidth, h: tip.offsetHeight };
  };
  const size = measure(bw, bh);
  if (!box) {   // never for a drawn target, but the card still needs a spot
    tip.style.left = (bounds.right - size.w) + 'px'; tip.style.top = bounds.top + 'px';
    return;
  }
  const rect = function (c) { return { left: c.left, right: c.left + c.w, top: c.top, bottom: c.top + c.h }; };
  const inside = function (r) {
    return r.left >= bounds.left - 0.5 && r.right <= bounds.right + 0.5 &&
           r.top >= bounds.top - 0.5 && r.bottom <= bounds.bottom + 0.5;
  };
  // Aligned with the window's top (right/left) or left edge (below/above), clamped into the map.
  const put = function (side, w, h) {
    const y = clamp(box.top, bounds.top, Math.max(bounds.top, bounds.bottom - h));
    const x = clamp(box.left, bounds.left, Math.max(bounds.left, bounds.right - w));
    if (side === 'right') return { side: side, left: box.right + TIP_GAP, top: y, w: w, h: h };
    if (side === 'left') return { side: side, left: box.left - TIP_GAP - w, top: y, w: w, h: h };
    if (side === 'below') return { side: side, left: x, top: box.bottom + TIP_GAP, w: w, h: h };
    return { side: side, left: x, top: box.top - TIP_GAP - h, w: w, h: h };
  };
  // Clear the left index panel when the card would cover it, if a shift right still fits.
  const clearIndex = function (c) {
    if (!covers(rect(c), index)) return c;
    if (c.side === 'left') return null;   // shifting right would cover the window
    const left = index.right + TIP_GAP;
    if (left + c.w > bounds.right) return null;
    return { side: c.side, left: left, top: c.top, w: c.w, h: c.h };
  };

  let pick = null;
  ['right', 'below', 'above', 'left'].some(function (side) {
    const c = clearIndex(put(side, size.w, size.h));
    if (c && inside(rect(c))) { pick = c; return true; }
    return false;
  });
  if (pick) { tip.style.left = pick.left + 'px'; tip.style.top = pick.top + 'px'; return; }

  // No side holds the whole card: take the roomiest, capped so it stays clear of the window.
  const room = {
    right: bounds.right - (box.right + TIP_GAP), below: bounds.bottom - (box.bottom + TIP_GAP),
    above: (box.top - TIP_GAP) - bounds.top, left: (box.left - TIP_GAP) - bounds.left
  };
  let side = 'right';
  ['below', 'above', 'left'].forEach(function (s) { if (room[s] > room[side]) side = s; });
  const sideways = side === 'right' || side === 'left';
  const capped = measure(sideways ? Math.min(TIP_MAX, bw, Math.max(1, room[side])) : bw,
                         sideways ? bh : Math.min(bh, Math.max(1, room[side])));
  let c = put(side, capped.w, capped.h);
  if (covers(rect(c), index)) {   // shrink into the strip clear of the index panel
    let left = c.left;
    if (side === 'left') left = box.left - TIP_GAP - capped.w;
    else left = Math.max(c.left, index.right + TIP_GAP);
    const avail = side === 'left' ? box.left - TIP_GAP - (index.right + TIP_GAP) : bounds.right - left;
    if (avail > 20) {
      const narrower = measure(Math.min(capped.w, avail), capped.h);
      c = put(side, narrower.w, narrower.h);
      if (side !== 'left') c.left = left;
    }
  }
  c.left = clamp(c.left, bounds.left, Math.max(bounds.left, bounds.right - c.w));
  c.top = clamp(c.top, bounds.top, Math.max(bounds.top, bounds.bottom - c.h));
  tip.style.left = c.left + 'px'; tip.style.top = c.top + 'px';
}

let tipTarget = null, keptId = null;

export function showTip(target) {
  tipTarget = target;
  fillTip(target); tip.hidden = false; placeTip(target);
}

export function toggleTip(id) {
  if (keptId === id) { hideTip(); return; }
  keptId = id;
  showTip({ kind: 'agent', id });
}

export function dismissTipOutside(chip) {
  if (keptId !== null && chip?.dataset.id !== keptId) hideTip();
}

export function refreshTip() {
  if (tipTarget && app.model.byId.has(tipTarget.id)) showTip(tipTarget);
  else if (tipTarget) hideTip();
}

export function hideTip() {
  tip.hidden = true; tipTarget = null; keptId = null;
}

/* ---------- filter ---------- */
const search = $('search');
export function queryKey() { return app.ui.obfuscate ? 'agents-map.obfuscated-query.v1' : 'agents-map.query.v2'; }

// What the bar count filters to: the agents that need the user, or if none does, those at work.
export function activeQuery() {
  return app.model && app.model.allAgents.some(function (a) { return a.needs; }) ? 'needs-you' : 'active';
}

// The button's own filters: a click sets one or clears whichever is on, and it counts as pressed while one is.
export function isActiveQuery(q) { return q === 'needs-you' || q === 'active'; }

export function applyFilter() {
  const m = app.model;
  if (!m) return;
  const q = search.value.trim().toLowerCase();
  const terms = q ? q.split(/\s+/) : [];
  let hits = 0;
  m.agents.forEach(function (a) {
    a.match = terms.every(function (t) { return a.hay.indexOf(t) >= 0; });
    a.el.classList.toggle('nomatch', !a.match);
    if (a.match) hits++;
  });
  m.links.forEach(function (l) { l.path.classList.toggle('nomatch', !(l.src.match && l.dst.match)); });
  $('world').classList.toggle('filtering', terms.length > 0);
  $('btn-active').setAttribute('aria-pressed', String(isActiveQuery(q)));
  $('match').textContent = terms.length ? hits + ' of ' + m.agents.length + ' match' : '';
  store('session', queryKey(), q || null);
  renderTable();
}

/* ---------- table ---------- */
const COLS = [
  { key: 'name', label: 'Agent', get: function (a) { return a.name.toLowerCase(); } },
  { key: 'win', label: 'Window', get: function (a) { return a.win.name.toLowerCase(); } },
  { key: 'cli', label: 'CLI', get: function (a) { return a.cliName; } },
  { key: 'model', label: 'Model · effort', get: function (a) { return a.model + ' ' + (a.effort || ''); } },
  { key: 'pct', label: 'Context', num: true, get: function (a) { return a.pct == null ? -1 : a.pct; } },
  { key: 'out', label: '→', title: 'Oversees: how many agents this one watches', num: true, get: function (a) { return a.out.length; } },
  { key: 'inn', label: '←', title: 'Overseen by: how many agents watch this one', num: true, get: function (a) { return a.inn.length; } },
  { key: 'state', label: 'State', get: function (a) { return stateText(a, true); } },
  { key: 'last', label: 'Active', title: 'Time since the last activity', num: true, get: function (a) { return a.last || 0; } }
];
const rowById = new Map();

function renderHead() {
  const tr = $('thead-row'), sort = app.ui.sort;
  tr.textContent = '';
  COLS.forEach(function (c) {
    const th = el('th', c.num ? 'num' : '', c.label);
    th.tabIndex = 0;
    if (c.title) { th.title = c.title; th.setAttribute('aria-label', c.title); }
    if (sort.key === c.key) th.setAttribute('aria-sort', sort.dir > 0 ? 'ascending' : 'descending');
    function go() {
      app.ui.sort = { key: c.key, dir: sort.key === c.key ? -sort.dir : (c.num ? -1 : 1) };
      store('session', 'agents-map.sort.v2', app.ui.sort);
      renderHead(); renderTable();
    }
    th.addEventListener('click', go);
    th.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } });
    tr.appendChild(th);
  });
}

export function renderTable() {
  if ($('table-panel').hidden || !app.model) return;
  const m = app.model, sort = app.ui.sort;
  const col = COLS.filter(function (c) { return c.key === sort.key; })[0] || COLS[0];
  const rows = m.agents.filter(function (a) { return a.match !== false; }).sort(function (a, b) {
    const x = col.get(a), y = col.get(b);
    return (x < y ? -1 : x > y ? 1 : 0) * sort.dir || byName(a, b);
  });
  const body = $('tbody');
  body.textContent = ''; rowById.clear();
  rows.forEach(function (a) {
    const tr = el('tr');
    const name = el('td', 'agent-cell', a.name);
    if (!app.graph?.demo) {
      const open = el('a', 'open', 'open'); open.href = a.el.href;
      name.appendChild(open);
    }
    tr.appendChild(name);
    tr.appendChild(el('td', '', a.win.name));
    const cli = el('td'), k = el('span', 'k');
    k.appendChild(el('span', 'sw ' + a.cliClass)); k.appendChild(el('span', '', a.cliName)); cli.appendChild(k);
    tr.appendChild(cli);
    tr.appendChild(el('td', '', a.model + (a.effort ? ' · ' + a.effort : '')));
    tr.appendChild(el('td', 'num', a.pct != null ? Math.round(a.pct) + '% of ' + fmtTokens(a.window) : (a.used ? fmtTokens(a.used) : '–')));
    tr.appendChild(el('td', 'num', String(a.out.length)));
    tr.appendChild(el('td', 'num', String(a.inn.length)));
    tr.appendChild(el('td', '', stateText(a, true)));
    tr.appendChild(el('td', 'num', ago(a.last, true)));
    tr.addEventListener('click', function (e) {
      if (e.target.closest('a')) return;
      setPin({ kind: 'agent', id: a.id }); centerOn(a); syncTableSelection();
    });
    rowById.set(a.id, tr);
    body.appendChild(tr);
  });
  $('table-count').textContent = rows.length === m.agents.length ? String(m.agents.length) : rows.length + ' of ' + m.agents.length;
  syncTableSelection();
}

export function syncTableSelection() {
  const pin = app.ui.pin;
  rowById.forEach(function (tr, id) { tr.classList.toggle('sel', !!pin && pin.kind === 'agent' && pin.id === id); });
}

export function toggleTable(show) {
  const panel = $('table-panel');
  panel.hidden = show === undefined ? !panel.hidden : !show;
  app.ui.tableOpen = !panel.hidden;
  $('btn-table').setAttribute('aria-pressed', String(!panel.hidden));
  document.body.classList.toggle('table-open', !panel.hidden);
  store('session', 'agents-map.table.v2', !panel.hidden);
  if (!panel.hidden) { renderHead(); renderTable(); }
}

/* ---------- bar: stats, status, history, snapshot age ---------- */
export function renderStatus() {
  const s = $('status');
  let text = null, action = null;
  if (app.unsaved) { text = 'Not saved: ' + app.unsaved.reason; action = ['Retry', retry]; }
  else if (app.flash) text = app.flash;
  else if (app.tooClose) { text = plural(app.tooClose, 'box is', 'boxes are') + ' too close'; if (app.externalConflicts) action = ['Tidy', doTidy]; }
  s.textContent = '';
  s.hidden = !text;
  s.classList.toggle('info', !action);   // a plain notice carries no warning mark
  if (!text) return;
  s.appendChild(el('span', '', text));
  if (action) {
    const b = el('button', '', action[0]);
    b.type = 'button'; b.id = 'btn-status';
    b.addEventListener('click', action[1]);
    s.appendChild(b);
  }
}

// Warnings live outside the clipped toolbar row.
function placeAge(age) {
  const destination = $(age.matches('.stale, .failed') ? 'bar-alerts' : 'bar-items');
  if (age.parentNode !== destination) destination.appendChild(age);
}

function renderAge() {
  const age = $('age'), m = app.model;
  if (!m) {   // Before the first load, show only refresh errors.
    age.textContent = app.ui.refreshError ? 'Refresh failed: ' + app.ui.refreshError : '';
    age.classList.toggle('failed', !!app.ui.refreshError);
    placeAge(age);
    return;
  }
  const mins = (Date.now() / 1000 - m.generated) / 60;
  const at = new Date(m.generated * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const failed = app.ui.refreshError;
  age.textContent = failed ? 'Refresh failed: ' + failed + ' · showing ' + at : 'Snapshot ' + at + ' · ' + ago(m.generated);
  age.classList.toggle('failed', !!failed);
  const old = !failed && m.attention && m.generated - m.attention.updated > OLD_LIST;
  if (old) age.textContent += ' · Attention list from ' + stamp(m.attention.updated);
  age.classList.toggle('stale', !failed && (mins > STALE_MINUTES || old));
  age.title = !failed && mins > STALE_MINUTES ? 'Old snapshot' : '';
  placeAge(age);
}

// The View panel's switches mirror the state they control.
export function renderView() {
  $('opt-obfuscate').checked = app.ui.obfuscate;
  $('opt-links').checked = app.ui.links;
  $('opt-counts').checked = app.ui.counts;
  $('opt-wake').checked = app.ui.wake;
  $('opt-recent').checked = app.ui.recent;
  $('opt-live').checked = app.ui.live;
  $('opt-dark').checked = document.documentElement.dataset.theme
    ? document.documentElement.dataset.theme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
}

export function renderPanels() {
  $('sample-data').hidden = !app.graph?.demo;
  const m = app.model;
  if (!m) { renderAge(); return; }
  const linked = m.allAgents.filter(a => a.linked).length;
  $('stats').textContent = plural(m.allWins.filter(w => !w.closed).length, 'window', 'windows') + ' · ' + plural(linked, 'linked agent', 'linked agents') +
    (m.allAgents.length > linked ? ' (+' + (m.allAgents.length - linked) + ' without links)' : '') +
    ' · ' + plural(m.overseerCount, 'overseer', 'overseers') + ' · ' + plural(m.linkCount, 'link', 'links');

  const running = m.allAgents.filter(a => a.run === 'running').length;
  const needing = m.allAgents.filter(a => a.needs).length;
  const active = $('btn-active');
  active.hidden = !running && !needing;
  active.textContent = [needing ? needing + (needing === 1 ? ' needs you' : ' need you') : '', running ? running + ' running' : ''].filter(Boolean).join(' · ');
  active.classList.toggle('waiting', needing > 0);
  // Items with no drawn agent are listed under their owner's box; with no owner drawn either, in the bar.
  const loose = m.attention && !m.attention.owner ? m.attention : null;
  const pendingItems = loose?.activeLoose || [];
  const items = $('btn-attention');
  items.hidden = !loose?.loose.length;
  items.textContent = pendingItems.length ? plural(pendingItems.length, 'attention item', 'attention items') : 'Attention';
  items.classList.toggle('waiting', pendingItems.some(function (it) { return it.alert !== 'none'; }));
  if (popover.dataset.kind === 'attention') fillAttention();

  const notes = [];   // only what is wrong now; the counts of hidden agents are in the table's data, not the footer
  if (!m.appRunning) notes.push('run states (RepoPrompt CE is not running)');
  m.warnings.forEach(function (w) { notes.push(String(w).replace(/\.$/, '')); });
  $('notes').textContent = notes.length ? notes.join('; ') + '.' : '';

  const undo = $('btn-undo'), redo = $('btn-redo');
  const pending = app.unsaved;   // a change the server does not have: Undo takes it back, Redo has to wait
  undo.disabled = !app.undo && !pending;
  undo.title = pending ? 'Undo: ' + (app.ui.obfuscate ? 'change' : pending.label) + ' (not saved)' : app.undo ? 'Undo: ' + (app.ui.obfuscate ? 'change' : app.undo) + '  (Left arrow)' : 'Nothing to undo';
  redo.disabled = !app.redo || !!pending;
  redo.title = app.redo && !pending ? 'Redo: ' + (app.ui.obfuscate ? 'change' : app.redo) + '  (Right arrow)' : 'Nothing to redo';
  const layoutButton = $('btn-layouts');
  layoutButton.textContent = 'Layout: ' + layoutName(currentLayout()) + ' ▾';
  layoutButton.disabled = !!pending;
  renderView();
  renderStatus();
  renderAge();
  renderIndex();
  renderTable();
}

/* ---------- group index ---------- */
function indexItem(cls, name, count, target, onClick, needs = false) {
  const b = el('button', 'i-item ' + cls);
  b.type = 'button';
  b.appendChild(el('span', 'i-name', name));
  if (needs) {
    const mark = el('span', 'i-need', '◆');
    mark.setAttribute('role', 'img');
    mark.setAttribute('aria-label', 'Needs you');
    b.appendChild(mark);
  }
  if (count != null) b.appendChild(el('span', typeof count === 'number' ? 'i-n count' : 'i-n', String(count)));
  b.addEventListener('click', onClick);
  if (target) {
    b.addEventListener('pointerenter', function () { setHover(target); });
    b.addEventListener('pointerleave', function () { setHover(null); });
  }
  return b;
}

export function renderIndex() {
  const m = app.model, body = $('index-body'), index = $('index');
  index.classList.toggle('collapsed', app.ui.indexCollapsed);
  $('index-toggle').textContent = app.ui.indexCollapsed ? '▸' : '◂';
  $('index-toggle').setAttribute('aria-expanded', String(!app.ui.indexCollapsed));
  body.textContent = '';
  body.appendChild(indexItem('all', 'Whole map', m.wins.length, null, function () { fit(true); }));
  const {hidden} = currentLayout();
  function box(kind, id, name, count, wins, fitBox) {
    const off = !!hidden[id], closed = !wins.length;
    const target = off || closed ? null : {kind, id};
    const row = indexItem(kind + (off ? ' i-hidden' : closed ? ' gone' : ''), name, count, target,
      () => off ? setBoxHidden(kind, id, false) : !closed && fitBox(),
      off && wins.some(w => w.agents.some(a => a.needs)));
    if (off) row.appendChild(el('span', 'i-n', 'hidden'));
    row.dataset.id = id;
    body.appendChild(row);
  }
  const groups = app.arr.groups.slice().sort(byName);
  if (groups.length) body.appendChild(el('div', 'i-head', 'Groups'));
  for (const g of groups) {
    const wins = g.members.map(id => m.allWinById.get(id)).filter(Boolean);
    box('group', g.id, groupName(g), wins.length || (hidden[g.id] ? null : 'closed'), wins, () => fitGroup(g, true));
  }
  const loose = m.allWins.filter(w => !groupOf(w.id) && (!w.closed || app.arr.windows[w.id])).sort(byName);
  if (loose.length) body.appendChild(el('div', 'i-head', groups.length ? 'Ungrouped' : 'Windows'));
  for (const w of loose) box('window', w.id, w.title, w.agents.length, [w], () => fitWindow(w, true));
  $('btn-group-prefix').hidden = loose.filter(w => !hidden[w.id]).length < 2;
}

export function groupByName() {
  if (!canEdit()) return;
  const {names, seeds} = groupByPrefix();
  if (!names.length) { flash('Nothing to group'); return; }
  changed('Grouped by name', true, seeds);
}

/* ---------- popover: Save and Saves ---------- */
const popover = $('popover');
let popoverTurn = 0;   // answers that arrive for an earlier opening are ignored

export function closePopover(restoreFocus = false) {
  const layouts = popover.dataset.kind === 'layouts';
  popoverTurn++;
  popover.hidden = true;
  popover.textContent = '';
  delete popover.dataset.kind;
  popover.removeAttribute('role');
  popover.removeAttribute('aria-labelledby');
  $('btn-layouts').setAttribute('aria-expanded', 'false');
  if (layouts && restoreFocus) $('btn-layouts').focus();
}

function openPopover(anchor) {
  closePopover();
  popover.hidden = false;
  const r = anchor.getBoundingClientRect();
  popover.style.left = clamp(r.left, 8, window.innerWidth - 310) + 'px';
  popover.style.top = (r.bottom + 6) + 'px';
}

export function openLayouts() {
  const anchor = $('btn-layouts'), current = currentLayout();
  openPopover(anchor);
  const turn = popoverTurn;
  popover.dataset.kind = 'layouts';
  popover.setAttribute('role', 'dialog');
  popover.setAttribute('aria-labelledby', 'layouts-title');
  anchor.setAttribute('aria-expanded', 'true');
  const title = el('div', 'p-title', 'Layouts');
  title.id = 'layouts-title';
  popover.appendChild(title);

  function button(label, run, cls = '') {
    const b = el('button', cls, label);
    b.type = 'button';
    b.addEventListener('click', run);
    return b;
  }

  async function run(op, fields) {
    await changeLayout(op, fields);
    if (popoverTurn === turn + 1 && document.activeElement === document.body) anchor.focus();
  }

  function nameForm(op, value, fields) {
    popover.querySelector('form')?.remove();
    const form = el('form'), input = el('input'), submit = el('button', '', op === 'create' ? 'Create' : 'Rename');
    input.type = 'text';
    input.value = value;
    input.maxLength = 80;
    input.required = true;
    input.setAttribute('aria-label', 'Layout name');
    submit.type = 'submit';
    form.append(input, submit);
    form.addEventListener('submit', e => {
      e.preventDefault();
      const name = cleanName(input.value);
      if (name) run(op, {...fields, name});
    });
    popover.appendChild(form);
    input.focus();
    input.select();
  }

  let selected;
  for (const [index, layout] of app.layouts.entries()) {
    const row = el('div', 'p-row');
    const select = button(layoutName(layout), () => {
      if (layout.id === current.id) closePopover(true);
      else run('select', {layout_id: layout.id});
    }, 'p-name layout-choice');
    if (layout.id === current.id) {
      select.setAttribute('aria-current', 'true');
      selected = select;
    }
    row.appendChild(select);
    if (index < 9) row.appendChild(el('span', 'p-key', '⌘' + (index + 1)));
    if (layout.id === current.id) {
      row.appendChild(button('Rename', () => nameForm('rename', app.ui.obfuscate ? '' : layout.name, {layout_id: layout.id})));
      const del = button('Delete', () => {
        if (del.textContent === 'Delete') {
          del.textContent = 'Really delete?';
          del.classList.add('confirm');
        } else run('delete', {layout_id: layout.id});
      });
      del.disabled = layout.id === 'main';
      row.appendChild(del);
    }
    popover.appendChild(row);
  }
  const tools = el('div', 'p-row');
  tools.appendChild(button('New', () => nameForm('create', '', {source_id: current.id})));
  popover.appendChild(tools);
  selected?.focus();
}

function stamp(seconds) {
  return new Date(seconds * 1000).toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

// The attention items that have no drawn agent, as the owner's badge or the bar button opens them.
function fillAttention() {
  const m = app.model, loose = m && m.attention ? m.attention.loose : [];
  popover.textContent = '';
  popover.dataset.kind = 'attention';
  if (!loose.length) { closePopover(); return; }
  popover.appendChild(el('div', 'p-title', 'Attention'));
  loose.forEach(function (it) {
    const row = el('div', 'p-item' + itemClass(it));
    row.appendChild(el('div', 'p-name', it.reason));
    const sub = el('div', 'p-sub');
    sub.appendChild(kindIcon(it.kind));
    sub.appendChild(el('span', '', [it.kind, itemMeta(it)].filter(Boolean).join(' · ')));
    row.appendChild(sub);
    row.appendChild(itemControls(it));
    popover.appendChild(row);
  });
}

export function openAttention(anchor) {
  openPopover(anchor);
  fillAttention();
}

export function openSaveForm() {
  openPopover($('btn-save'));
  popover.appendChild(el('div', 'p-title', 'Save arrangement'));
  const form = el('form'), input = el('input'), ok = el('button', '', 'Save');
  input.type = 'text'; input.maxLength = 80; input.value = stamp(Date.now() / 1000); input.setAttribute('aria-label', 'Name of the save');
  ok.type = 'submit';
  form.appendChild(input); form.appendChild(ok);
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const name = cleanName(input.value);
    if (!name) { input.focus(); return; }
    addSave(name).then(function () { closePopover(); flash('Saved "' + name + '"'); },
      function (err) { flash('Not saved: ' + err.message); });
  });
  popover.appendChild(form);
  input.focus(); input.select();
}

export function openSaves() {
  openPopover($('btn-saves'));
  popover.appendChild(el('div', 'p-title', 'Saved arrangements'));
  const turn = popoverTurn;
  listSaves().then(function (saves) {
    if (turn !== popoverTurn) return;
    if (!saves.length) { popover.appendChild(el('div', 'p-empty', 'No saved arrangements')); return; }
    saves.forEach(function (s) {
      const row = el('div', 'p-row'), restore = el('button', '', 'Restore'), del = el('button', '', 'Delete');
      restore.type = 'button'; del.type = 'button';
      row.appendChild(el('span', 'p-name', s.name));
      row.appendChild(el('span', 'p-sub', stamp(s.t) + ' · ' + plural(s.windows, 'window', 'windows')));
      row.appendChild(restore); row.appendChild(del);
      restore.addEventListener('click', function () {
        if (!canEdit() || app.unsaved) return;
        closePopover();
        restoreNamedSave(s.id, s.name);
      });
      del.addEventListener('click', function () {
        if (del.textContent === 'Delete') { del.textContent = 'Really delete?'; return; }
        deleteSave(s.id).then(openSaves, function (err) { flash('Not deleted: ' + err.message); });
      });
      popover.appendChild(row);
    });
  }, function (err) { if (turn === popoverTurn) popover.appendChild(el('div', 'p-empty', 'Could not load: ' + err.message)); });
}

export function initLegend() {
  $('lg-warn').textContent = WARN + '% or more';
  $('lg-crit').textContent = CRIT + '% or more';
  ['blocker', 'deadline', 'calendar', 'watch'].forEach(function (kind) {
    const item = el('span', 'item');
    item.appendChild(kindIcon(kind));
    item.appendChild(el('span', '', kind));
    $('lg-kinds').appendChild(item);
  });
  setInterval(renderAge, 15000);
}
