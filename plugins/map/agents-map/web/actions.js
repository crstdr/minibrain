// What the map can do, as functions the input handlers call: refresh, record a
// change, undo, tidy, pin. Each keeps the drawing, the panels and the server in step.

import { app, currentLayout, membership } from './state.js';
import { store } from './util.js';
import { buildModel, heatOf, linkActivity } from './model.js';
import { autoLayout, placeMissing, tidyAll } from './layout.js';
import { catalogue, commit, commitLayout, commitSettings, discover, fetchGraph, forgetWindow, getSave, idle, loadArrangement, restoreSave, retryUnsaved, step } from './server.js';
import { fit, fitGroup, fitWindow, refreshHighlight, renderAll, restoreView, sync, targetAgents, visibleArea } from './render.js';
import { applyFilter, renderPanels, renderStatus, renderView, refreshTip, closePopover } from './panels.js';
import { cancelDrag, closeMenu, reconcilePointer } from './interact.js';

let transition = false, recovering = false, historyPending = 0, dragTurn = 0, layoutTurn = 0;
export function canEdit() { return !!app.model && !transition && !recovering && !historyPending; }
let busy = false, refreshWanted = false, again = false, graphKey = '';
export let dragging = false;
export function setDragging(on) {
  dragging = on;
  if (on) dragTurn++;
  if (!on && refreshWanted) { refreshWanted = false; refresh(); }
}

let flashTimer = 0;
export function flash(text) {
  app.flash = text;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(function () { app.flash = null; renderStatus(); }, 5000);
  renderStatus();
}

// The graph or the whole arrangement was replaced: build the model, give new windows
// a place, redraw everything. The one drawing path, used at start and by Refresh.
export function rebuild() {
  if (app.model) { cancelDrag(); closeMenu(); }   // both hold objects of the model being replaced
  const note = document.getElementById('empty');   // left by a start that could not load
  if (note) note.remove();
  if (applyView()) refresh();   // undo, a restore or another tab changed which agents to fetch (busy: fetched again afterwards)
  const layout = currentLayout();
  app.model = buildModel(app.graph, app.arr, layout, app.shared);
  const area = visibleArea();
  const {saveChanged, seeds, patch, visibilityChanged} = placeMissing(area.w, area.h);
  if (visibilityChanged) app.model = buildModel(app.graph, app.arr, layout, app.shared);
  const pin = app.ui.pin;
  if (pin && !targetAgents(pin).length && !(pin.kind === 'window' && app.model.winById.get(pin.id))) {
    app.ui.pin = null;   // not setPin: the new model is not drawn yet
    store('session', 'agents-map.pin.v2', null);
    flash('The pinned ' + pin.kind + ' is no longer shown');
  }
  renderAll();
  reconcilePointer();
  refreshTip();
  applyFilter();
  renderPanels();
  if (saveChanged) showResult(discover(seeds));
  if (Object.keys(patch.windows).length) showResult(commitLayout(patch));
}

export function expireSnoozes() {
  if (!canEdit() || dragging) return false;
  const now = Date.now();
  if (!app.model.attention?.items.some(it => it.snoozedUntil && it.snoozedUntil <= now)) return false;
  rebuild();
  return true;
}

// The arrangement changed in place (a move, a group, a link setting): redraw cheaply.
export function redraw() {
  if (expireSnoozes()) return;
  sync();
  renderPanels();
}

async function showResult(done) {
  const result = await done;
  if (result === 'conflict') {
    resetViewportTimer();
    rebuild();
    restoreView();
    flash('Layout changed in another tab; reloaded');
  }
  renderPanels();
  return result;
}

export function retry() { return showResult(retryUnsaved()); }

export function changed(label, full, seeds) {
  const done = showResult(commit(label, false, {seeds}));
  if (full) rebuild(); else redraw();
  return done;
}

export function layoutChanged(patch) {
  const done = showResult(commitLayout(patch));
  redraw();
  return done;
}

export function setBoxHidden(kind, id, hidden) {
  if (!canEdit()) return;
  const layout = currentLayout();
  if (!!layout.hidden[id] === hidden) return;
  layout.hidden[id] = hidden;
  showResult(commitLayout({hidden: {[id]: hidden}}));
  rebuild();
  if (hidden) return;
  if (kind === 'group') {
    const group = app.arr.groups.find(g => g.id === id);
    if (group) fitGroup(group, true);
  } else {
    const win = app.model.winById.get(id);
    if (win) fitWindow(win, true);
  }
}

export function setLinkOverride(kind, id, value) {
  currentLayout().links[kind][id] = value;
  return layoutChanged({links: {[kind]: {[id]: value}}});
}

let viewTimer = 0, sendViewport = null;
function resetViewportTimer() {
  clearTimeout(viewTimer);
  viewTimer = 0;
  sendViewport = null;
}
export function persistViewport(debounce = false) {
  resetViewportTimer();
  const layout = currentLayout();
  if (!layout) return;
  const viewport = layout.viewport = {...app.ui.view};
  sendViewport = () => {
    resetViewportTimer();
    if (currentLayout() === layout) showResult(commitLayout({viewport}));
  };
  if (debounce) viewTimer = setTimeout(sendViewport, 500);
  else sendViewport();
}
export function flushViewport() {
  if (sendViewport) sendViewport();
}

export async function syncArrangement() {
  if (transition || dragging || historyPending || viewTimer || app.unsaved) return;
  const made = dragTurn, outgoing = currentLayout()?.id;
  try {
    const changed = await loadArrangement(() => !transition && !dragging && !historyPending && !viewTimer && made === dragTurn);
    if (changed && app.graph) {
      if (outgoing !== currentLayout().id) { layoutTurn++; closePopover(); }
      rebuild();
      restoreView();
    }
    recovering = false;
    if (changed || app.ui.refreshError) {
      app.ui.refreshError = null;
      if (app.model) renderPanels();
    }
  } catch (e) {
    app.ui.refreshError = e.message;
    if (app.model) renderPanels();
  }
}

export async function refreshFromServer() {
  flushViewport();
  await idle();
  await syncArrangement();
  if (!recovering && currentLayout()) { applyView(); return refresh(); }
}

export async function changeLayout(op, fields = {}) {
  if (!canEdit() || app.unsaved) return 'dropped';
  transition = true;
  cancelDrag();
  closeMenu();
  closePopover();
  flushViewport();
  layoutTurn++;
  const result = await catalogue({op, ...fields});
  if (result === 'ok' || result === 'conflict') {
    rebuild();
    restoreView();
  }
  recovering = result === 'failed';
  transition = false;
  renderPanels();
  if (app.ui.recent !== lastRecent) refresh();
  return result;
}

export async function removeWindow(w) {
  if (!canEdit() || app.unsaved || !app.model.winById.get(w.id)?.closed) return;
  transition = true;
  layoutTurn++;
  flushViewport();
  try {
    const result = await showResult(forgetWindow(w.id, 'Removed ' + w.sourceName));
    if (result === 'ok') rebuild();
    if (result === 'failed') flash('Could not remove window');
  } finally {
    transition = false;
    refresh();
  }
}

export async function restoreNamedSave(id, name) {
  if (!canEdit() || app.unsaved) return;
  transition = true;
  cancelDrag();
  flushViewport();
  try {
    await idle();
    if (app.unsaved) return;
    const {save} = await getSave(id);
    const members = membership(save.groups), previous = membership(app.shared.groups);
    for (const w of app.model.allWins) {
      const old = app.shared.windows[w.id];
      if (!old || save.windows[w.id]) continue;
      const item = save.windows[w.id] = {...old};
      if (!members.has(w.id) || members.get(w.id) !== previous.get(w.id)) {
        delete item.dx; delete item.dy;
      }
    }
    const result = await showResult(restoreSave(save, 'Restored "' + name + '"'));
    if (result === 'ok') { rebuild(); restoreView(); }
    else if (result === 'failed' && !app.unsaved) recovering = true;
  } catch (e) { flash('Not restored: ' + e.message); }
  finally { transition = false; renderPanels(); if (app.ui.recent !== lastRecent) refresh(); }
}

let lastRecent;
export async function refresh() {
  if (transition || recovering || !currentLayout()) return;
  if (dragging) { refreshWanted = true; return; }
  if (busy) { again = true; return; }   // asked again while loading: load once more afterwards
  busy = true;
  document.getElementById('btn-refresh').classList.add('busy');
  const recent = app.ui.recent, first = !app.model, layoutId = currentLayout().id, turn = layoutTurn;
  try {
    const graph = await fetchGraph(recent);
    if (transition || recovering || turn !== layoutTurn || layoutId !== currentLayout().id || recent !== app.ui.recent) {
      if (lastRecent !== app.ui.recent) again = true;
    }
    else if (dragging) refreshWanted = true;
    else {
      // Live asks every few seconds: redraw only when something other than the time changed.
      // An agent crossing a heat threshold is a change too, though only the time moved.
      lastRecent = recent;
      const heat = new Map(graph.agents.map(function (a) { return [a.id, heatOf(a, graph.generated)]; }));
      // Link timestamps matter only when they change whether or which way a link moves.
      const links = graph.links.map(({ wake, watch, attn, msg, ...link }) =>
        Object.assign(link, { activity: linkActivity({ wake, watch, attn, msg }, { heat: heat.get(link.t) }, graph.generated) }));
      const key = JSON.stringify(Object.assign({}, graph, { generated: 0, links })) + Array.from(heat.values()).join('');
      app.ui.refreshError = null;
      if (first || key !== graphKey) {
        graphKey = key;
        app.graph = graph;
        rebuild();
        if (first) restoreView();
      } else app.graph.generated = app.model.generated = graph.generated;
    }
  } catch (e) {
    if (!transition && !recovering && turn === layoutTurn && layoutId === currentLayout().id) app.ui.refreshError = e.message;
  }
  busy = false;
  expireSnoozes();
  document.getElementById('btn-refresh').classList.remove('busy');
  renderPanels();
  if (again) { again = false; return refresh(); }
}

export async function boot() {
  await loadArrangement();
  applyView();   // before the first fetch, so it already asks for the arrangement's set of agents
  await refresh();
  if (!app.model) throw new Error(app.ui.refreshError || 'no data');
}

export async function history(kind) {
  if (!app.model || transition || recovering || app.unsaved && kind !== 'undo') return;
  flushViewport();
  historyPending++;
  cancelDrag();
  try {
    const result = await step(kind);
    if (result === 'failed') { flash('Could not load the server state'); return; }
    if (result === 'dropped') return;
    rebuild();
    restoreView();
    if (result === 'discarded') flash('The change that was not saved was taken back');
    if (result === 'conflict') flash('Layout changed in another tab; reloaded');
    if (result === 'ok') refresh();
  } finally { historyPending--; }
}

function moveLayout(patch) {
  if (Object.keys(patch.groups).length || Object.keys(patch.windows).length) layoutChanged(patch);
}

export function doTidy() { if (canEdit()) moveLayout(tidyAll()); }

export function relayout() {
  if (!canEdit()) return;
  const {w, h} = visibleArea();
  moveLayout(autoLayout(w, h));
  fit(true);
}

export function setPin(pin) {
  app.ui.pin = pin;
  store('session', 'agents-map.pin.v2', pin);
  if (app.model) refreshHighlight();
}

export function togglePin(pin) {
  const now = app.ui.pin;
  setPin(now && now.kind === pin.kind && now.id === pin.id ? null : pin);
}

export function setHover(hover) {
  const now = app.ui.hover;
  if (dragging && hover) return false;   // nothing lights up while a box is being moved
  if ((now && now.kind) === (hover && hover.kind) && (now && now.id) === (hover && hover.id)) return false;
  app.ui.hover = hover;
  refreshHighlight();
  return true;
}

/* ---------- View ---------- */
export function syncThemeColor() {
  document.getElementById('theme-color').content = getComputedStyle(document.documentElement).getPropertyValue('--surface').trim();
}

export function currentView() { return {...currentLayout().switches}; }

export function applyView() {
  const recent = app.ui.recent, {live, theme} = app.settings;
  Object.assign(app.ui, currentView(), {live});
  if (theme) document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
  store('local', 'agents-map.theme.v1', theme);
  syncThemeColor();
  return app.ui.recent !== recent;
}

function setView(key, value) {
  if (!canEdit()) { renderView(); return; }
  const patch = {[key]: value};
  const global = key === 'live' || key === 'theme';
  Object.assign(global ? app.settings : currentLayout().switches, patch);
  const refetch = applyView();
  if (global) { showResult(commitSettings(patch)); redraw(); }
  else layoutChanged({switches: patch});
  if (refetch || (key === 'live' && value)) refresh();
}

export function setLinks(on) { setView('links', on); }
export function setCounts(on) { setView('counts', on); }
export function setWake(on) { setView('wake', on); }
export function setLive(on) { setView('live', on); }
export function setRecent(on) { setView('recent', on); }
export function setDark(on) { setView('theme', on ? 'dark' : 'light'); }
