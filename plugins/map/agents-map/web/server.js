// The only module that talks to the local server. Full state replaces the working
// copy; write acknowledgments never do.

import { app, compose, currentLayout, decompose, emptyArrangement } from './state.js';

async function api(method, path, body) {
  const init = { method: method, headers: {} };
  if (method !== 'GET') { init.headers['Content-Type'] = 'application/json'; init.body = JSON.stringify(body || {}); }
  let res;
  try { res = await fetch(path, init); }
  catch (e) { const down = new Error('the map server is not running'); down.status = 0; throw down; }
  let data = null;
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const err = new Error((data && data.error) || ('HTTP ' + res.status));
    err.status = res.status; err.data = data;
    throw err;
  }
  return data;
}

// Only a full state replaces the working copy, invalidating queued captures.
let generation = 0, turn = 0, pending = 0;
let queue = Promise.resolve();
const dirtySettings = new Map(), pendingDiscovery = {}, discoveredPoints = {};

function acknowledge({rev, undo, redo}) { Object.assign(app, {rev, undo, redo}); }

function adopt(state) {
  acknowledge(state);
  app.shared = state.save || emptyArrangement();
  app.layouts = state.layouts;
  app.settings = state.settings;
  app.arr = compose(app.shared, currentLayout());
  app.unsaved = null;
  dirtySettings.clear();
  forgetDiscovery(discoveredPoints, discoveredPoints);
  forgetDiscovery(pendingDiscovery);
  generation++;
}

export function fetchGraph(recent) { return api('GET', '/api/graph' + (recent ? '?recent=1' : '')); }

function enqueue(run) {
  turn++;
  pending++;
  queue = queue.then(run).finally(() => { pending--; });
  return queue;
}

export async function loadArrangement(allowed = () => true) {
  if (pending || app.unsaved || !allowed()) return false;
  const made = ++turn, state = await api('GET', '/api/arrangement');
  if (made !== turn || pending || app.unsaved || !allowed()) return false;
  const next = state.layouts.find(l => l.id === state.settings.current);
  const changed = app.rev !== state.rev || !same(currentLayout(), next) || !same(app.settings, state.settings);
  if (changed) adopt(state);
  else app.layouts = state.layouts;
  return changed;
}

// Store order is irrelevant; null link entries are optimistic deletions.
function same(a, b) {
  if (a === b) return true;
  if (!a || !b || typeof a !== 'object' || typeof b !== 'object') return false;
  return Object.keys(a).every(k => same(a[k] ?? null, b[k] ?? null))
    && Object.keys(b).every(k => same(a[k] ?? null, b[k] ?? null));
}

function handleWriteError(e, label) {
  if (e.status === 409 && e.data?.version === 2) { adopt(e.data); return 'conflict'; }
  app.unsaved = { reason: e.message, label };
  return 'failed';
}

async function write(body) {
  if (body.op === 'save' || body.op === 'forget' || body.op === 'layout' && ['groups', 'windows', 'hidden'].some(k => k in body.patch)) body.base_rev = app.rev;
  const reply = await api('PUT', '/api/arrangement', body);
  if (body.op === 'save' || body.op === 'forget') acknowledge(reply);
}

function mutation(body, label) {
  const made = generation, payload = structuredClone(body);
  return enqueue(async () => {
    if (made !== generation) return 'dropped';
    if (app.unsaved) return 'failed';
    try { await write(payload); return 'ok'; }
    catch (e) { return handleWriteError(e, label); }
  });
}

function captureSave() {
  const layout = currentLayout();
  // A migrated group can lack an anchor and a visibility entry until its first save.
  for (const g of app.arr.groups) {
    layout.groups[g.id] ??= {x: 0, y: 0};
    layout.hidden[g.id] ??= false;
  }
  app.shared = decompose(app.arr, app.shared, layout);
  return app.shared;
}

export function commit(label, amend, { seeds = {} } = {}) {
  captureSave();
  return mutation({ op: 'save', layout_id: currentLayout().id, save: app.shared, label: label.slice(0, 120), amend: !!amend, mode: 'edit', seeds }, label);
}

export function forgetWindow(id, label) {
  const made = generation;
  return enqueue(async () => {
    if (made !== generation || app.unsaved) return 'dropped';
    try { await write({op: 'forget', window_id: id, label: label.slice(0, 120)}); }
    catch (e) {
      if (e.status === 409 && e.data?.version === 2) { adopt(e.data); return 'conflict'; }
      return 'failed';
    }
    delete app.shared.windows[id];
    for (const group of app.shared.groups) group.members = group.members.filter(wid => wid !== id);
    for (const layout of app.layouts) {
      delete layout.windows[id];
      delete layout.hidden[id];
      delete layout.links.windows[id];
    }
    delete discoveredPoints[id];
    app.arr = compose(app.shared, currentLayout());
    return 'ok';
  });
}

export function commitLayout(patch) {
  return mutation({ op: 'layout', layout_id: currentLayout().id, patch }, 'Layout');
}

function captureSettings(patch) {
  const tokens = Object.keys(patch).map(key => [key, {}]);
  for (const [key, token] of tokens) dirtySettings.set(key, token);
  return () => {
    for (const [key, token] of tokens) if (dirtySettings.get(key) === token) dirtySettings.delete(key);
  };
}

export function commitSettings(patch) {
  const saved = captureSettings(patch);
  return mutation({ op: 'settings', patch }, 'Settings').then(status => {
    if (status === 'ok') saved();
    return status;
  });
}

export function retryUnsaved() {
  if (!app.unsaved) return Promise.resolve('dropped');
  const save = structuredClone(captureSave());
  const {id, name, ...patch} = structuredClone(currentLayout());
  const settings = Object.fromEntries([...dirtySettings.keys()].map(k => [k, app.settings[k]]));
  const settingsSaved = captureSettings(settings);
  const label = app.unsaved.label, made = generation;
  // A discovery that did not reach the server still needs its atomic cross-layout seeds.
  const seeds = {main_windows: {...pendingDiscovery}};
  return enqueue(async () => {
    if (made !== generation || !app.unsaved) return 'dropped';
    try {
      await write({ op: 'save', layout_id: id, save, label: label.slice(0, 120), amend: true, mode: 'edit', seeds });
      forgetDiscovery(seeds.main_windows);
      await write({ op: 'layout', layout_id: id, patch });
      if (Object.keys(settings).length) { await write({ op: 'settings', patch: settings }); settingsSaved(); }
      app.unsaved = null;
      return 'ok';
    } catch (e) { return handleWriteError(e, label); }
  });
}

function forgetDiscovery(points, target = pendingDiscovery) {
  for (const id of Object.keys(points)) delete target[id];
}
export function discoveryPoint(id) { return discoveredPoints[id]; }
export function discover(seeds) {
  const points = seeds.main_windows || {};
  Object.assign(pendingDiscovery, points);
  Object.assign(discoveredPoints, points);
  return commit('Placed windows', true, {seeds}).then(result => {
    if (result === 'ok') forgetDiscovery(points);
    return result;
  });
}

export function step(kind) {
  return enqueue(async () => {
    if (app.unsaved) {
      if (kind !== 'undo') return 'dropped';
      return await reloadNow() ? 'discarded' : 'failed';
    }
    try { adopt(await api('POST', '/api/' + kind, {base_rev: app.rev})); return 'ok'; }
    catch (e) {
      if (e.status === 409 && e.data?.version === 2) { adopt(e.data); return 'conflict'; }
      return 'failed';
    }
  });
}

async function reloadNow() {
  try { adopt(await api('GET', '/api/arrangement')); return true; }
  catch (e) { app.ui.refreshError = e.message; return false; }
}

export function catalogue(body) {
  return enqueue(async () => {
    if (app.unsaved) return 'dropped';
    try { await write(body); }
    catch (e) {
      if (e.status === 409 && e.data?.version === 2) { adopt(e.data); return 'conflict'; }
      app.ui.refreshError = e.message;
      return 'failed';
    }
    return await reloadNow() ? 'ok' : 'failed';
  });
}

export function restoreSave(save, label) {
  const layout_id = currentLayout().id, snapshot = structuredClone(save);
  return enqueue(async () => {
    if (app.unsaved) return 'dropped';
    try { await write({op: 'save', layout_id, save: snapshot, label: label.slice(0, 120), amend: false, mode: 'restore'}); }
    catch (e) { return handleWriteError(e, label); }
    return await reloadNow() ? 'ok' : 'failed';
  });
}

export function idle() { return queue.then(() => true); }
export function listSaves() { return api('GET', '/api/saves'); }
export function addSave(name) {
  return api('POST', '/api/saves', {name, save: decompose(app.arr, app.shared, currentLayout())});
}
export function getSave(id) { return api('GET', '/api/saves/' + encodeURIComponent(id)); }
export function deleteSave(id) { return api('DELETE', '/api/saves/' + encodeURIComponent(id)); }
