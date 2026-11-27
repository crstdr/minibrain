// Pointer input on the map: pan, zoom, dragging boxes and groups, hover, pinning and
// the right-click menu.

import { groupName } from './model.js';
import { app, groupOf, LINK_COLORS } from './state.js';
import { $, el, clamp, cleanName } from './util.js';
import { markSeen } from './attention.js';
import { HUES, fillId, groupHue, scheme, theme } from './colors.js';
import { CW, CH, framePixels } from './grid.js';
import { addToGroup, applyPositions, createGroup, landing, openMembers, removeFromGroup, setCols, setStandalone, translateGroup, ungroup } from './layout.js';
import { applyView, fitGroup, frames, linksOf, linksSetting, placeFrame, placeLinks, placeWin, sync, zoomAt } from './render.js';
import { canEdit, changed, flash, layoutChanged, persistViewport, removeWindow, setBoxHidden, setLinkOverride, setDragging, setHover, setPin, togglePin } from './actions.js';
import { closePopover, dismissTipOutside, openAttention, syncTableSelection, toggleTip } from './panels.js';
import { isDrawerOpen, openRoadmapDrawer, syncDrawerWithAgent } from './drawer.js';

const stage = $('stage'), layerFg = $('layer-fg'), layerFrames = $('layer-frames');
const landingEl = $('landing'), dots = $('dots'), menu = $('menu');
const CHROME = '#table-panel, #index, #view';

function groupById(id) { return app.arr.groups.filter(function (g) { return g.id === id; })[0]; }

/* ---------- drag: the background pans; a box or a group moves over the others and
   lands on the nearest free grid spot when released ---------- */
let drag = null, swallowClick = false, frame = 0;

function lift(d, on) {
  d.wins.forEach(function (w) { w.bg.classList.toggle('lifted', on); w.fg.classList.toggle('lifted', on); });
}

function showDots() {
  const view = app.ui.view;
  if (view.k * CW < 12) return;   // too dense to help when zoomed far out
  const x0 = Math.floor(-view.tx / view.k / CW) * CW, y0 = Math.floor(-view.ty / view.k / CH) * CH;
  dots.style.left = x0 + 'px'; dots.style.top = y0 + 'px';
  dots.style.width = (stage.clientWidth / view.k + 2 * CW) + 'px';
  dots.style.height = (stage.clientHeight / view.k + 2 * CH) + 'px';
  dots.hidden = false;
}

// Where the dragged boxes would land if released now: Map id -> cell box.
function target(d) {
  const wanted = new Map();
  if (d.kind === 'win') {
    const w = d.wins[0];
    wanted.set(w.id, { x: Math.round(w.px / CW), y: Math.round(w.py / CH) });
  } else {
    const dcx = Math.round((d.wins[0].px - d.start[0][0]) / CW), dcy = Math.round((d.wins[0].py - d.start[0][1]) / CH);
    d.wins.forEach(function (w) { const e = app.arr.windows[w.id]; wanted.set(w.id, { x: e.x + dcx, y: e.y + dcy }); });
  }
  return landing(d.wins, wanted);
}

function showLanding(d) {
  const cells = target(d);
  if (!cells) { landingEl.hidden = true; return; }   // nowhere to land: the drop will be refused
  let r;
  if (d.kind === 'win') {
    const c = cells.get(d.wins[0].id);
    r = { x: c.x * CW, y: c.y * CH, w: d.wins[0].w, h: d.wins[0].h };
  } else r = framePixels(Array.from(cells.values()));
  landingEl.style.transform = 'translate(' + r.x + 'px,' + r.y + 'px)';
  landingEl.style.width = r.w + 'px'; landingEl.style.height = r.h + 'px';
  landingEl.hidden = false;
}

function endDrag(d, apply) {
  cancelAnimationFrame(frame); frame = 0;
  landingEl.hidden = true; dots.hidden = true;
  document.body.classList.remove('dragging');
  if (d.kind === 'pan') {
    if (apply) persistViewport();
    else { Object.assign(app.ui.view, d.view); applyView(false); }
    setDragging(false);
    return;
  }
  lift(d, false);
  const cells = apply && d.moved ? target(d) : null;
  const first = d.wins[0], from = app.arr.windows[first.id], dx = cells ? cells.get(first.id).x - from.x : 0, dy = cells ? cells.get(first.id).y - from.y : 0;
  if (cells && (dx || dy)) {
    if (d.kind === 'group') layoutChanged(translateGroup(d.group, dx, dy));
    else if (groupOf(first.id)) {
      applyPositions(cells);
      changed('Moved ' + first.sourceName);
    } else layoutChanged(setStandalone(first.id, from.x + dx, from.y + dy));
  } else sync();
  if (apply && d.moved && !cells) flash('No free spot there');
  setDragging(false);
}

stage.addEventListener('pointerdown', function (e) {
  if (!canEdit() || e.button !== 0 || e.ctrlKey || e.metaKey || e.target.closest(CHROME + ', .agent-open, .rm-chip')) return;
  closeMenu(); closePopover();
  const title = e.target.closest('.frame-title'), winEl = e.target.closest('.win');
  const view = app.ui.view;
  if (title && groupById(title.dataset.gid)) {
    const g = groupById(title.dataset.gid);
    const wins = openMembers(g).filter(function (w) { return app.arr.windows[w.id]; });
    drag = { kind: 'group', group: g, wins: wins, frame: frames.filter(function (f) { return f.g.id === g.id; })[0] };
  } else if (winEl && app.model.winById.get(winEl.dataset.id)) {
    drag = { kind: 'win', wins: [app.model.winById.get(winEl.dataset.id)] };
  } else drag = { kind: 'pan', wins: [], view: {...view} };
  drag.sx = e.clientX; drag.sy = e.clientY; drag.moved = false;
  drag.start = drag.wins.map(function (w) { return [w.px, w.py]; });
  drag.links = linksOf(drag.wins);
  setDragging(true);
});

window.addEventListener('pointermove', function (e) {
  if (!drag) return;
  const d = drag, view = app.ui.view;
  const dx = e.clientX - d.sx, dy = e.clientY - d.sy;
  if (!d.moved) {
    if (Math.hypot(dx, dy) < 4) return;
    d.moved = true;
    document.body.classList.add('dragging');
    setHover(null);
    if (d.kind !== 'pan') { lift(d, true); showDots(); }
  }
  if (d.kind === 'pan') { view.tx = d.view.tx + dx; view.ty = d.view.ty + dy; view.auto = false; applyView(false); return; }
  d.wins.forEach(function (w, i) { w.px = d.start[i][0] + dx / view.k; w.py = d.start[i][1] + dy / view.k; placeWin(w); });
  if (d.frame) placeFrame(d.frame, dx / view.k, dy / view.k);
  placeLinks(d.links);
  if (!frame) frame = requestAnimationFrame(function () { frame = 0; if (drag === d) showLanding(d); });
});

window.addEventListener('pointerup', function () {
  if (!drag) return;
  const d = drag;
  drag = null;
  if (!d.moved) { setDragging(false); return; }
  swallowClick = true; setTimeout(function () { swallowClick = false; }, 0);
  endDrag(d, true);
});

// Drops any drag in progress and puts things back. True if something was being moved.
// `held`: the button is still down, so the click its release produces must be ignored.
function abortDrag(held) {
  const d = drag;
  drag = null;
  if (!d) return false;
  if (!d.moved) { setDragging(false); return false; }
  if (held) {
    swallowClick = true;
    window.addEventListener('pointerup', function () { setTimeout(function () { swallowClick = false; }, 0); }, { once: true });
  }
  endDrag(d, false);
  return true;
}

export function cancelDrag() { return abortDrag(true); }

window.addEventListener('pointercancel', function () { abortDrag(false); });

stage.addEventListener('dragstart', function (e) { e.preventDefault(); });

stage.addEventListener('wheel', function (e) {
  if (!canEdit() || drag || e.target.closest('#table-panel, #index')) return;
  e.preventDefault();
  closeMenu();
  const box = stage.getBoundingClientRect();
  zoomAt(e.clientX - box.left, e.clientY - box.top, Math.exp(-e.deltaY * (e.ctrlKey ? 0.011 : 0.0017)));
}, { passive: false });

/* ---------- click: agent card, chat link, or highlight pin ---------- */
document.addEventListener('click', function (e) {
  if (!swallowClick && !e.target.closest('#tip')) dismissTipOutside(e.target.closest('.agent'));
}, true);

stage.addEventListener('keydown', function (e) {
  if (e.key !== 'Enter' || !e.target.matches('.agent')) return;
  e.preventDefault();
  if (e.repeat) return;
  if (e.metaKey || e.ctrlKey) e.target.querySelector('.agent-open')?.click();
  else toggleTip(e.target.dataset.id);
});
stage.addEventListener('click', function (e) {
  if (swallowClick) { e.preventDefault(); e.stopPropagation(); return; }
  if (e.target.closest(CHROME)) return;
  const chip = e.target.closest('.agent'), winEl = e.target.closest('.win');
  if (e.target.closest('.att-count')) { e.preventDefault(); e.stopPropagation(); openAttention(e.target.closest('.att-count')); return; }   // not the chip's link
  const rmChip = e.target.closest('.rm-chip');
  if (rmChip) {
    e.preventDefault(); e.stopPropagation();
    if (chip) setPin({ kind: 'agent', id: chip.dataset.id });
    openRoadmapDrawer(rmChip.dataset.roadmap, rmChip.dataset.lane || null, null);
    syncTableSelection();
    return;
  }
  const rmBadge = e.target.closest('.att-badge[data-roadmap]');
  if (rmBadge) {
    e.preventDefault(); e.stopPropagation();
    const a = chip && app.model.byId.get(chip.dataset.id);
    if (a) setPin({ kind: 'agent', id: a.id });
    const owned = a?.roadmaps?.some(r => r.id === rmBadge.dataset.roadmap && r.mode === 'owner');
    openRoadmapDrawer(rmBadge.dataset.roadmap, owned ? null : (a?.sourceName || null), rmBadge.dataset.ticket || null);
    syncTableSelection();
    return;
  }
  if (e.target.closest('.agent-open')) return;
  if (chip && !e.shiftKey) {
    if (e.metaKey || e.ctrlKey) chip.querySelector('.agent-open')?.click();
    else if (isDrawerOpen() && syncDrawerWithAgent(app.model.byId.get(chip.dataset.id))) {
      setPin({ kind: 'agent', id: chip.dataset.id });
      syncTableSelection();
    } else toggleTip(chip.dataset.id);
    return;
  }
  if (chip) togglePin({ kind: 'agent', id: chip.dataset.id });
  else if (winEl && e.shiftKey) { e.preventDefault(); togglePin({ kind: 'window', id: winEl.dataset.id }); }
  else if (e.target.closest('a.win-title')) return;   // a plain click on a title opens that window
  else if (e.target.closest('.frame-title') && groupById(e.target.closest('.frame-title').dataset.gid)) {
    togglePin({ kind: 'group', id: e.target.closest('.frame-title').dataset.gid });
    if (!app.ui.pin) setHover(null);   // let go at once, though the pointer still rests on the name
  }
  else setPin(null);
  syncTableSelection();
}, true);

/* ---------- hover ---------- */
function hoverTarget(node) {
  const chip = node.closest('.agent');
  if (chip) return { kind: 'agent', id: chip.dataset.id };
  const winEl = node.closest('.win');
  if (winEl) return { kind: 'window', id: winEl.dataset.id };
  const title = node.closest('.frame-title');
  if (title && groupById(title.dataset.gid)) return { kind: 'group', id: title.dataset.gid };
  return null;
}

let pointer = null;
function rememberPointer(e) { pointer = [e.clientX, e.clientY]; }

function hoverNode(node) {
  if (drag || !menu.hidden) return;
  const t = node && hoverTarget(node);
  // Only a window's title lights the window; its empty area does not.
  const hov = t && t.kind === 'window' && !node.closest('.win-title') ? null : t;
  setHover(hov);
}

export function reconcilePointer() {
  if (pointer) hoverNode(document.elementFromPoint(...pointer));
}

function onOver(e) {
  rememberPointer(e);
  hoverNode(e.target);
}

function onOut(e) {
  if (e.relatedTarget && (layerFg.contains(e.relatedTarget) || layerFrames.contains(e.relatedTarget))) return;
  pointer = null;
  setHover(null);
}

[layerFg, layerFrames].forEach(function (layer) {
  layer.addEventListener('pointerover', onOver);
  layer.addEventListener('pointermove', rememberPointer);
  layer.addEventListener('pointerout', onOut);
});

layerFg.addEventListener('focusin', function (e) {
  const chip = e.target.closest('.agent');
  if (!chip || !menu.hidden) return;
  const t = { kind: 'agent', id: chip.dataset.id };
  setHover(t);
});
layerFg.addEventListener('focusout', function (e) {
  if (e.relatedTarget?.closest('.agent') === e.target.closest('.agent')) return;
  if (pointer) reconcilePointer(); else setHover(null);
});

/* ---------- right-click menu ---------- */
export function closeMenu() {
  if (menu.hidden) return false;
  menu.hidden = true; menu.textContent = '';
  return true;
}

function openMenu(x, y, build) {
  closePopover(); setHover(null);
  menu.textContent = '';
  build();
  menu.hidden = false;
  menu.style.left = clamp(x, 8, window.innerWidth - menu.offsetWidth - 8) + 'px';
  menu.style.top = clamp(y, 8, window.innerHeight - menu.offsetHeight - 8) + 'px';
  const first = menu.querySelector('button');
  if (first) first.focus({ preventScroll: true });
}

function mHead(text) { menu.appendChild(el('div', 'm-head', text)); }
function mSep() { menu.appendChild(el('div', 'm-sep')); }

function mItem(label, run, confirmLabel) {
  const b = el('button', 'm-item', label);
  b.type = 'button'; b.setAttribute('role', 'menuitem');
  b.addEventListener('click', function () {
    if (confirmLabel && b.textContent === label) {
      b.textContent = confirmLabel;
      b.classList.add('confirm');
      return;
    }
    closeMenu();
    run();
  });
  menu.appendChild(b);
}

// A row of small choices; each option is [label, pressed, run, swatch class or null, tooltip].
function mRow(label, options) {
  const row = el('div', 'm-row');
  row.appendChild(el('span', 'm-label', label));
  options.forEach(function (o) {
    const b = el('button');
    b.type = 'button'; b.setAttribute('aria-pressed', String(!!o[1]));
    if (o[3]) { b.appendChild(el('span', 'ln ' + o[3])); b.title = o[0]; b.setAttribute('aria-label', o[0]); }
    else b.textContent = o[0];
    if (o[4]) b.title = o[4];
    b.addEventListener('click', function () { closeMenu(); o[2](); });
    row.appendChild(b);
  });
  menu.appendChild(row);
}

function mForm(placeholder, value, submit, run) {
  const form = el('form'), input = el('input'), ok = el('button', '', submit);
  input.type = 'text'; input.maxLength = 80; input.placeholder = placeholder; input.value = value; input.setAttribute('aria-label', placeholder);
  ok.type = 'submit';
  form.appendChild(input); form.appendChild(ok);
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const text = cleanName(input.value);
    if (!text) { input.focus(); return; }   // an empty name is refused
    closeMenu(); run(text);
  });
  menu.appendChild(form);
}

// Link settings (hide, colour) live in the arrangement per agent or per window.
function setting(kind, id) { return app.arr[kind][id] || {}; }

function setSetting(kind, id, key, value, label) {
  const bag = app.arr[kind];
  const e = bag[id] || (bag[id] = {});
  if (value == null) delete e[key]; else e[key] = value;
  if (key === 'links') delete e.hide;   // the older form of "hide"
  if (kind === 'agents' && !Object.keys(e).length) delete bag[id];
  if (key === 'links') setLinkOverride(kind, id, value);
  else changed(label);
}

// Links: Default follows the All links switch; Show and Hide override it.
function linksRow(current, set) {
  mRow('Links', [
    ['Default', !current, function () { if (current) set(null, 'default'); }, null],
    ['Show', current === 'show', function () { if (current !== 'show') set('show', 'always shown'); }, null],
    ['Hide', current === 'hide', function () { if (current !== 'hide') set('hide', 'always hidden'); }, null]
  ]);
}

function linkRows(kind, id, name) {
  const s = setting(kind, id);
  linksRow(linksSetting(s), function (value, what) { setSetting(kind, id, 'links', value, 'Links of ' + name + ': ' + what); });
  mRow('Link colour', [['Default', !s.color, function () { setSetting(kind, id, 'color', null, 'Default link colour for ' + name); }, 'plain']]
    .concat(LINK_COLORS.map(function (c) {
      return [c[1], s.color === c[0], function () { setSetting(kind, id, 'color', c[0], 'Coloured links of ' + name); }, c[0]];
    })));
}

// A group's hue: one row of hues, plus None. `current` is the hue id now set; `set(value)` stores
// a hue id, or null for none.
function hueRow(current, set) {
  mRow('Colour', [['None', !current, function () { if (current) set(null); }, null]]);
  const grid = el('div', 'm-grid'), mode = theme();
  grid.setAttribute('role', 'group'); grid.setAttribute('aria-label', 'Colour');
  HUES.forEach(function (h) {
    const s = scheme(fillId(h[0], 3), mode), b = el('button');
    b.type = 'button';
    b.style.background = s.bg; b.style.borderColor = s.border;
    b.title = h[1]; b.setAttribute('aria-label', h[1]);
    b.setAttribute('aria-pressed', String(current === h[0]));
    b.addEventListener('click', function () { closeMenu(); if (current !== h[0]) set(h[0]); });
    grid.appendChild(b);
  });
  menu.appendChild(grid);
}

function pinItem(pin) {
  const now = app.ui.pin, on = now && now.kind === pin.kind && now.id === pin.id;
  mItem(on ? 'Stop highlighting' : 'Keep highlighted', function () { togglePin(pin); syncTableSelection(); });
}

function agentMenu(a) {
  mHead(a.name);
  if (a.needs && !a.seen) { mItem('Seen', function () { markSeen(a); a.el.classList.remove('glow', 'pulse'); a.el.style.animationDelay = ''; }); mSep(); }
  linkRows('agents', a.id, a.sourceName);
  mSep();
  pinItem({ kind: 'agent', id: a.id });
}

function windowMenu(w) {
  const g = groupOf(w.id);
  mHead(w.title);
  linkRows('windows', w.id, w.sourceName);
  if (w.agents.length) {
    const fixed = !!app.arr.windows[w.id].fixed;
    mRow('Columns', [['Auto', !fixed, function () { if (fixed) { setCols(w, null); changed('Columns of ' + w.sourceName, true); } }, null]]
      .concat([1, 2, 3, 4].map(function (n) {
        return [String(n), fixed && w.cols === n, function () { setCols(w, n); changed('Columns of ' + w.sourceName, true); }, null];
      })));
  }
  mSep();
  if (g) mItem((app.ui.obfuscate ? 'Remove from ' : 'Remove from group ') + groupName(g), function () { const seeds = removeFromGroup(w); changed('Removed ' + w.sourceName + ' from ' + g.name, true, seeds); });
  app.arr.groups.slice().sort(function (a, b) { return a.name.localeCompare(b.name); }).forEach(function (other) {
    if (g && other.id === g.id) return;
    mItem((g ? 'Move to ' : 'Add to ') + (app.ui.obfuscate ? '' : 'group ') + groupName(other), function () { addToGroup(other, w); changed('Added ' + w.sourceName + ' to ' + other.name, true); });
  });
  mForm('New group name', '', 'New group', function (name) { const seeds = createGroup(name, w); changed('Grouped ' + w.sourceName + ' as ' + name, true, seeds); });
  mSep();
  if (!g) mItem('Hide window', () => setBoxHidden('window', w.id, true));
  if (w.closed) mItem('Remove from map', () => removeWindow(w), 'Really remove?');
  pinItem({ kind: 'window', id: w.id });
}

function groupMenu(g) {
  mHead(app.ui.obfuscate ? groupName(g) : 'Group ' + groupName(g));
  mForm('Group name', app.ui.obfuscate ? '' : groupName(g), 'Rename', function (name) { if (name !== g.name) { g.name = name; changed('Renamed group to ' + name); } });
  linksRow(linksSetting(g), function (value, what) {
    if (value) g.links = value; else delete g.links;
    delete g.hide;
    setLinkOverride('groups', g.id, value);
  });
  hueRow(groupHue(g), function (value) {
    if (value) g.hue = value; else delete g.hue;
    delete g.fill;   // the older colour is superseded: its hue was taken, or None was chosen
    changed((value ? 'Coloured group ' : 'Removed the colour of group ') + g.name);
  });
  mItem('Hide group', () => setBoxHidden('group', g.id, true));
  mItem('Zoom to group', function () { fitGroup(g, true); });
  mItem('Ungroup', function () { const seeds = ungroup(g); changed('Ungrouped ' + g.name, true, seeds); });
}

stage.addEventListener('contextmenu', function (e) {
  if (!canEdit()) return;
  if (e.target.closest(CHROME)) return;
  if (drag) { e.preventDefault(); return; }   // no menu in the middle of a move
  const t = hoverTarget(e.target);
  if (!t) { closeMenu(); return; }   // background: the browser's own menu
  e.preventDefault();
  const m = app.model;
  openMenu(e.clientX, e.clientY, function () {
    if (t.kind === 'agent') agentMenu(m.byId.get(t.id));
    else if (t.kind === 'window') windowMenu(m.winById.get(t.id));
    else groupMenu(groupById(t.id));
  });
});

document.addEventListener('pointerdown', function (e) {
  if (!menu.hidden && !menu.contains(e.target)) closeMenu();
  const popover = $('popover');
  if (!popover.hidden && !popover.contains(e.target) && !e.target.closest('#btn-save, #btn-saves, #btn-attention, #btn-layouts')) closePopover();
}, true);
