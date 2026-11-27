export const GRID = [60, 31];

export function emptyArrangement() { return { grid: GRID.slice(), windows: {}, agents: {}, groups: [] }; }

export const app = {
  graph: null,          // last graph document from the server
  model: null,          // graph turned into linked objects (model.js)
  arr: emptyArrangement(),
  shared: emptyArrangement(),
  layouts: [],
  settings: { current: "main", live: true, theme: null },
  rev: 0,               // server revision of the arrangement
  undo: null,           // label of the step Undo would take back, or null
  redo: null,
  unsaved: null,        // {label, amend} of a change the server did not accept yet
  ui: {
    view: { k: 1, tx: 0, ty: 0, auto: true },   // auto: keep fitting on resize until the user pans or zooms
    links: true,        // global links toggle
    recent: true,       // also show recent agents without links
    wake: false,        // overseers' second line shows their auto-wake settings
    live: true,         // refresh on a timer
    obfuscate: false,
    counts: false,      // numbers after window, group and index names
    pin: null,          // {kind: 'agent'|'window', id} kept highlighted
    hover: null,        // {kind: 'agent'|'window'|'group', id} under the pointer
    indexCollapsed: false,
    tableOpen: false,
    sort: { key: 'win', dir: 1 },
    refreshError: null
  }
};

export function groupOf(wid) {
  for (const g of app.arr.groups) if (g.members.indexOf(wid) >= 0) return g;
  return null;
}

// Link colours a user can assign: the three validated categorical slots (see map.css).
export const LINK_COLORS = [['c1', 'Blue'], ['c2', 'Orange'], ['c3', 'Aqua']];

export function currentLayout() { return app.layouts.find(l => l.id === app.settings.current); }

export function membership(groups) {
  return new Map(groups.flatMap(g => g.members.map(id => [id, g.id])));
}

export function visible(layout, id, gid) { return !layout.hidden[gid || id]; }

export function effectivePosition(shared, layout, wid, members = membership(shared.groups)) {
  const gid = members.get(wid);
  if (!gid) return layout.windows[wid] || null;
  const p = layout.groups[gid], w = shared.windows[wid];
  return p && Number.isInteger(w?.dx) && Number.isInteger(w.dy) ? { x: p.x + w.dx, y: p.y + w.dy } : null;
}

function pick(source, keys) {
  return Object.fromEntries(keys.filter(k => source[k] !== undefined).map(k => [k, source[k]]));
}

const windowKeys = ['cols', 'fixed', 'color', 'fill'];
export function compose(shared, layout) {
  const arr = emptyArrangement(), members = membership(shared.groups);
  for (const id of new Set([...Object.keys(shared.windows), ...Object.keys(layout.windows)])) {
    const w = shared.windows[id] || {};
    const p = effectivePosition(shared, layout, id, members);
    if (!p) continue;
    arr.windows[id] = { ...pick(w, windowKeys), ...p };
    if (layout.links.windows[id]) arr.windows[id].links = layout.links.windows[id];
  }
  arr.agents = structuredClone(shared.agents);
  for (const [id, links] of Object.entries(layout.links.agents)) {
    if (links) (arr.agents[id] ||= {}).links = links;
  }
  arr.groups = shared.groups.map(g => {
    const item = structuredClone(g);
    if (layout.links.groups[g.id]) item.links = layout.links.groups[g.id];
    return item;
  });
  return arr;
}

export function decompose(arr, previousShared, layout) {
  const save = emptyArrangement(), members = membership(arr.groups);
  const previous = membership(previousShared.groups);
  save.groups = arr.groups.map(g => ({ ...pick(g, ['id', 'name', 'hue', 'fill']), members: g.members.slice() }));
  for (const id of new Set([...Object.keys(previousShared.windows), ...Object.keys(arr.windows)])) {
    const w = arr.windows[id], gid = members.get(id), anchor = layout.groups[gid];
    const old = previousShared.windows[id] || {};
    const item = save.windows[id] = pick(w || old, windowKeys);
    if (gid && anchor && w) Object.assign(item, { dx: w.x - anchor.x, dy: w.y - anchor.y });
    else if (!w && gid && gid === previous.get(id)) Object.assign(item, pick(old, ['dx', 'dy']));
  }
  for (const [id, a] of Object.entries(arr.agents)) {
    const item = pick(a, ['color', 'fill']);
    if (Object.keys(item).length) save.agents[id] = item;
  }
  return save;
}
