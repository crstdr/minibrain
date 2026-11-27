// Shared roadmap renderer: mounts into Agents Map's split drawer or standalone roadmap.html.
// Zero external imports so the same file works byte-identical in both plugins/roadmap/ and plugins/agents-map/.
// Every record string is untrusted text: rendered via textContent, never innerHTML.

const SEEN_KEY = 'agents-map.seen.v1';
const SNOOZE_KEY = 'agents-map.snooze.v1';
const ITEM_PREFIX = 'item:';
const NONE_GROUP = '~none';
const W = 220, H = 50, PH = 60, CX = 285, RY = 62, PAD = 54;

const STATE_LABEL = {
  'awaiting-user': 'Needs you',
  missing: "Doesn't exist yet",
  'built-off': 'Built, switched off',
  partial: 'Partly built',
  unknown: 'State unknown',
  discussed: 'Discussed only',
  specified: 'Designed, not built',
  paused: 'Paused',
  'in-progress': 'In progress',
  live: 'Live',
  done: 'Done',
  blocked: 'Blocked',
  mapped: 'Priority',
};

const ICON_PARTS = {
  blocker: [['path', { 'fill-rule': 'evenodd', d: 'M3.8 0.6H8.2L11.4 3.8V8.2L8.2 11.4H3.8L0.6 8.2V3.8ZM3.2 5.1H8.8V6.9H3.2Z' }]],
  deadline: [['path', { d: 'M1.7 0.7H10.3V2.3L7.1 6 10.3 9.7V11.3H1.7V9.7L4.9 6 1.7 2.3Z' }]],
  calendar: [
    ['rect', { x: 2.7, y: 0.7, width: 1.5, height: 3.1, rx: 0.75 }],
    ['rect', { x: 7.8, y: 0.7, width: 1.5, height: 3.1, rx: 0.75 }],
    ['rect', { x: 1.4, y: 2.6, width: 9.2, height: 8, rx: 1.1, fill: 'none', stroke: 'currentColor', 'stroke-width': 1.5 }],
    ['path', { d: 'M1.4 5.7H10.6', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.5 }],
  ],
  watch: [['path', { 'fill-rule': 'evenodd', d: 'M0.7 6C2.7 2.6 9.3 2.6 11.3 6C9.3 9.4 2.7 9.4 0.7 6ZM6 4.1A1.9 1.9 0 1 0 6 7.9A1.9 1.9 0 1 0 6 4.1Z' }]],
};

function h(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function svgEl(tag, attrs) {
  const e = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const k in attrs) e.setAttribute(k, String(attrs[k]));
  return e;
}

function kindIcon(kind) {
  const s = svgEl('svg', { viewBox: '0 0 12 12', 'aria-hidden': 'true' });
  (ICON_PARTS[kind] || []).forEach(([t, a]) => s.appendChild(svgEl(t, a)));
  return s;
}

function loadStore(key) {
  try {
    const v = JSON.parse(localStorage.getItem(key));
    return v && typeof v === 'object' && !Array.isArray(v) ? v : {};
  } catch (e) {
    return {};
  }
}

function saveStore(key, value) {
  try {
    if (Object.keys(value).length) localStorage.setItem(key, JSON.stringify(value));
    else localStorage.removeItem(key);
  } catch (e) { /* storage unavailable */ }
}

function dueEpoch(value) {
  if (typeof value === 'number') return value;
  if (!value || typeof value !== 'string') return null;
  const s = value.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const [y, m, d] = s.split('-').map(Number);
    return Math.floor(new Date(y, m - 1, d).getTime() / 1000);
  }
  const ms = Date.parse(s);
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null;
}

// Matches web/attention.js key rules so Seen and snooze stay in sync across map and roadmap.
function seenKey(source, id, due, reason) {
  return ITEM_PREFIX + JSON.stringify(source ? [source, id, due, reason] : [id, due, reason]);
}

function snoozeKey(source, id) {
  return ITEM_PREFIX + JSON.stringify([source || '', id]);
}

function itemSig(due, reason, alert) {
  return JSON.stringify([due, reason, alert]);
}

function calmState(source, id, att) {
  if (!att) return { seen: false, until: null };
  const due = dueEpoch(att.due);
  const s = loadStore(SEEN_KEY);
  const sn = loadStore(SNOOZE_KEY);
  const sk = seenKey(source, id, due, att.reason);
  const seen = s[sk] === true;
  const nk = snoozeKey(source, id);
  const saved = sn[nk];
  const sig = itemSig(due, att.reason, att.alert);
  const until = saved && saved.sig === sig && Number.isFinite(saved.until) && saved.until > Date.now() ? saved.until : null;
  return { seen, until };
}

function setItemSeen(source, id, att, on) {
  const due = dueEpoch(att.due);
  const s = loadStore(SEEN_KEY);
  const k = seenKey(source, id, due, att.reason);
  if (on) s[k] = true;
  else delete s[k];
  saveStore(SEEN_KEY, s);
}

function setItemSnooze(source, id, att, duration) {
  const due = dueEpoch(att.due);
  const sn = loadStore(SNOOZE_KEY);
  const k = snoozeKey(source, id);
  if (!duration) delete sn[k];
  else {
    const now = new Date();
    const until = duration === 'hour'
      ? now.getTime() + 3600000
      : new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9).getTime();
    sn[k] = { until, sig: itemSig(due, att.reason, att.alert) };
  }
  saveStore(SNOOZE_KEY, sn);
}

function catOf(n) {
  if (n.kind === 'priority' || n.kind === 'group') return 'priority';
  if (n.kind === 'decision' && n.state === 'awaiting-user') return 'dec';
  if (n.kind === 'gap' || n.state === 'missing' || n.state === 'blocked') return 'gap';
  if (n.state === 'live' || n.state === 'done') return 'ok';
  if (n.state === 'in-progress' || n.state === 'partial' || n.state === 'built-off') return 'wip';
  return 'idle';
}

function dotColor(c) {
  return c === 'dec' ? 'var(--rm-dec)' : c === 'gap' ? 'var(--rm-gap)' : c === 'wip' ? 'var(--rm-wip)' : c === 'ok' ? 'var(--rm-ok)' : 'var(--rm-idle)';
}

export function mountRoadmap(container, opts = {}) {
  const st = {
    roadmaps: opts.roadmaps || [],
    roadmapId: opts.roadmapId || 'default',
    apiBase: opts.apiBase || '/api/roadmap',
    apiUrl: opts.apiUrl || null,
    lane: opts.lane || null,
    sel: opts.nodeId || null,
    view: 'all',
    needOnly: false,
    obfuscate: !!opts.obfuscate,
    standalone: !!opts.standalone,
    doc: null,
    key: '',
    N: new Map(),
    parents: new Map(),
    pos: new Map(),
    vis: new Set(),
    size: { w: 1200, h: 700 },
    T: { x: 36, y: 36, k: 0.78 },
    fitted: false,
    failed: 0,
    stamp: null,
    reqSeq: 0,
    abortCtrl: null,
    inFlightId: null,
    asideCollapsed: !!opts.asideCollapsed,
    asideAutoOpened: false,
    asideUserChoice: null,
    destroyed: false,
  };

  container.textContent = '';
  const root = h('div', 'rm-root');
  const header = h('div', 'rm-header');
  const titleWrap = h('div', 'rm-title-wrap');
  const titleEl = h('h2', 'rm-title', 'Roadmap');
  const tabsEl = h('div', 'rm-tabs');
  const statusEl = h('span', 'rm-status', '');
  statusEl.hidden = true;
  titleWrap.append(titleEl, tabsEl, statusEl);

  const chipsEl = h('div', 'rm-chips');
  const toolsEl = h('div', 'rm-tools');
  const laneSel = h('select');
  laneSel.setAttribute('aria-label', 'Lane');
  const btnNeed = h('button', '', '');
  btnNeed.type = 'button';
  btnNeed.hidden = true;
  const btnAside = h('button', 'rm-aside-btn', 'Details');
  btnAside.type = 'button';
  btnAside.setAttribute('aria-label', 'Toggle details panel');
  toolsEl.append(laneSel, btnNeed, btnAside);

  let sizeButtons = [];
  let popoutLink = null;
  if (st.standalone && opts.mapHref) {
    const a = h('a', 'rm-tool-link', 'Agents Map');
    a.href = opts.mapHref;
    toolsEl.append(a);
  } else if (!st.standalone) {
    if (Array.isArray(opts.sizePresets) && opts.sizePresets.length && opts.onSizePreset) {
      const sizesEl = h('div', 'rm-sizes');
      sizesEl.setAttribute('role', 'group');
      sizesEl.setAttribute('aria-label', 'Roadmap width');
      opts.sizePresets.forEach(pct => {
        const b = h('button', '', pct + '%');
        b.type = 'button';
        b.dataset.pct = String(pct);
        b.setAttribute('aria-pressed', String(opts.activePreset === pct));
        b.onclick = () => opts.onSizePreset(pct);
        sizesEl.append(b);
        sizeButtons.push(b);
      });
      toolsEl.append(sizesEl);
    }
    popoutLink = h('a', 'rm-tool-link', '↗ Tab');
    popoutLink.target = '_blank';
    popoutLink.rel = 'noopener';
    toolsEl.append(popoutLink);
    if (opts.onCollapse) {
      const colBtn = h('button', 'rm-collapse-btn', '▸');
      colBtn.type = 'button';
      colBtn.setAttribute('aria-label', 'Collapse roadmap');
      colBtn.onclick = () => opts.onCollapse();
      toolsEl.append(colBtn);
    }
    if (opts.onClose) {
      const closeBtn = h('button', 'rm-close-btn', '×');
      closeBtn.type = 'button';
      closeBtn.setAttribute('aria-label', 'Close roadmap');
      closeBtn.onclick = () => opts.onClose();
      toolsEl.append(closeBtn);
    }
  }
  header.append(titleWrap, chipsEl, toolsEl);

  const body = h('div', 'rm-body');
  function syncAsideToggle(refit = false) {
    body.classList.toggle('aside-collapsed', st.asideCollapsed);
    btnAside.setAttribute('aria-pressed', String(!st.asideCollapsed));
    if (refit && st.doc) requestAnimationFrame(fit);
  }
  btnAside.onclick = () => {
    st.asideCollapsed = !st.asideCollapsed;
    st.asideAutoOpened = false;
    st.asideUserChoice = st.asideCollapsed;
    syncAsideToggle(true);
  };
  syncAsideToggle(false);
  const stage = h('div', 'rm-stage');
  const world = h('div', 'rm-world');
  const edges = svgEl('svg', { class: 'rm-edges', 'aria-hidden': 'true' });
  const zoomBox = h('div', 'rm-zoom');
  const zi = h('button', '', '+'), zo = h('button', '', '−'), zf = h('button', '', 'Fit');
  [zi, zo, zf].forEach(b => { b.type = 'button'; });
  zoomBox.append(zi, zo, zf);
  const noticeEl = h('button', 'rm-notice', '');
  noticeEl.type = 'button';
  noticeEl.setAttribute('aria-expanded', 'false');
  noticeEl.hidden = true;
  let noticeAlerts = [];
  let noticeOpen = false;
  function renderNotice() {
    if (!noticeAlerts.length || st.obfuscate) {
      noticeEl.hidden = true;
      noticeEl.classList.remove('open');
      noticeEl.setAttribute('aria-expanded', 'false');
      return;
    }
    noticeEl.hidden = false;
    noticeEl.classList.toggle('open', noticeOpen);
    noticeEl.setAttribute('aria-expanded', String(noticeOpen));
    noticeEl.textContent = noticeOpen
      ? noticeAlerts.join('\n')
      : `${noticeAlerts.length} schema ${noticeAlerts.length === 1 ? 'note' : 'notes'}`;
  }
  noticeEl.onclick = e => {
    e.stopPropagation();
    noticeOpen = !noticeOpen;
    renderNotice();
  };
  stage.append(world, zoomBox, noticeEl);

  const aside = h('aside', 'rm-aside');
  body.append(stage, aside);
  root.append(header, body);
  container.append(root);

  function mask(text, fallback = '•••') {
    if (!st.obfuscate) return text;
    return text ? fallback : '';
  }

  function displayTitle(doc) {
    if (!st.obfuscate) return doc.title;
    const idx = st.roadmaps.findIndex(r => r.id === doc.id);
    return 'Roadmap ' + (idx >= 0 ? idx + 1 : 1);
  }

  function displayNodeTitle(n, index) {
    if (!st.obfuscate) return n.title;
    return n.kind === 'priority' ? 'Priority ' + (index + 1) : 'Item ' + (index + 1);
  }

  function displayLane(lane) {
    if (!lane) return '';
    return st.obfuscate ? 'Agent' : lane;
  }

  function closure(id, nextFn) {
    const out = new Set(), stack = [id];
    while (stack.length) {
      for (const k of nextFn(stack.pop())) {
        if (st.N.has(k) && !out.has(k)) { out.add(k); stack.push(k); }
      }
    }
    return out;
  }

  function agentIdOf(lane) {
    const m = st.doc && st.doc.lanes;
    return (m && lane && Object.prototype.hasOwnProperty.call(m, lane) && m[lane]) || null;
  }

  function sameLane(a, b) {
    if (!a || !b) return false;
    if (a.toLowerCase() === b.toLowerCase()) return true;
    const ia = agentIdOf(a), ib = agentIdOf(b);
    return !!(ia && ib && ia === ib);
  }

  function updatePopoutHref() {
    if (!popoutLink) return;
    const q = st.lane ? '?lane=' + encodeURIComponent(st.lane) : '';
    popoutLink.href = '/roadmap/' + encodeURIComponent(st.roadmapId) + q;
  }

  function renderTabs() {
    tabsEl.textContent = '';
    if (st.roadmaps.length <= 1) return;
    st.roadmaps.forEach((rm, idx) => {
      const b = h('button', 'rm-tab' + (rm.id === st.roadmapId ? ' active' : ''), st.obfuscate ? 'Roadmap ' + (idx + 1) : rm.title);
      b.type = 'button';
      b.onclick = () => {
        if (rm.id === st.roadmapId) return;
        st.roadmapId = rm.id;
        st.lane = null;
        st.sel = null;
        st.view = 'all';
        st.fitted = false;
        st.key = '';
        if (opts.onSwitchRoadmap) opts.onSwitchRoadmap(rm.id);
        fetchDoc(true);
      };
      tabsEl.append(b);
    });
  }

  function buildIndex() {
    const d = st.doc;
    st.N = new Map();
    d.nodes.forEach((n, idx) => st.N.set(n.id, { ...n, _idx: idx }));
    if (d.loose && d.loose.length) {
      const inner = new Set(d.loose.flatMap(id => (st.N.get(id)?.needs || [])));
      st.N.set(NONE_GROUP, {
        id: NONE_GROUP, title: 'Tied to no priority', short: 'No priority',
        kind: 'group', state: 'mapped', open: true, behind: 0,
        needs: d.loose.filter(id => !inner.has(id)), related: [], serves: [], body: '', _idx: d.nodes.length,
      });
    }
    st.parents = new Map();
    for (const id of st.N.keys()) st.parents.set(id, []);
    for (const n of st.N.values()) {
      for (const dep of n.needs || []) {
        if (st.parents.has(dep)) st.parents.get(dep).push(n.id);
      }
    }
  }

  function renderChips() {
    chipsEl.textContent = '';
    const d = st.doc;
    if (!d) return;
    const mk = (id, label, full) => {
      const b = h('button', 'rm-chip-btn', label);
      b.type = 'button';
      if (full && full !== label) b.title = full;
      else if (label.length > 22) b.title = label;
      b.setAttribute('aria-pressed', String(st.view === id));
      b.onclick = () => { st.view = id; st.fitted = false; draw(); };
      chipsEl.append(b);
    };
    mk('all', 'All');
    const order = d.order.slice();
    if (st.N.has(NONE_GROUP)) order.push(NONE_GROUP);
    order.forEach((pid, idx) => {
      const p = st.N.get(pid);
      if (p) mk(pid, st.obfuscate ? (pid === NONE_GROUP ? 'Other' : 'Priority ' + (idx + 1)) : (p.short || p.title), st.obfuscate ? '' : p.title);
    });
  }

  function renderLaneSelect() {
    laneSel.textContent = '';
    const d = st.doc;
    if (!d) return;
    const counts = new Map();
    let totalOpen = 0;
    for (const n of d.nodes) {
      if (n.open && n.kind !== 'priority') {
        totalOpen++;
        if (n.lane) counts.set(n.lane, (counts.get(n.lane) || 0) + 1);
      }
    }
    const allOpt = h('option', '', `All lanes (${totalOpen} open)`);
    allOpt.value = '';
    laneSel.append(allOpt);
    const list = [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
    if (st.lane && !list.some(([l]) => sameLane(l, st.lane))) list.unshift([st.lane, 0]);
    list.forEach(([lane, cnt], idx) => {
      const o = h('option', '', `${st.obfuscate ? 'Agent ' + (idx + 1) : lane} (${cnt})`);
      o.value = lane;
      if (st.lane && sameLane(lane, st.lane)) o.selected = true;
      laneSel.append(o);
    });
    laneSel.onchange = () => {
      st.lane = laneSel.value || null;
      st.sel = null;
      updatePopoutHref();
      marks();
      renderAside();
    };
  }

  function computeLayout() {
    const d = st.doc;
    const vis = new Set();
    if (st.view === 'all') st.N.forEach((_, id) => vis.add(id));
    else if (st.N.has(st.view)) {
      vis.add(st.view);
      closure(st.view, i => st.N.get(i)?.needs || []).forEach(x => vis.add(x));
    }
    st.vis = vis;

    const memo = new Map();
    function getDepth(id, seen = new Set()) {
      if (memo.has(id)) return memo.get(id);
      const n = st.N.get(id);
      if (!n || n.kind === 'priority' || n.kind === 'group') { memo.set(id, 0); return 0; }
      if (seen.has(id)) return 1;
      seen.add(id);
      const ps = (st.parents.get(id) || []).filter(p => vis.has(p));
      const depth = ps.length ? 1 + Math.max(...ps.map(p => getDepth(p, new Set(seen)))) : 1;
      memo.set(id, depth);
      return depth;
    }
    const depthMap = new Map();
    vis.forEach(id => depthMap.set(id, getDepth(id)));
    const maxCol = Math.max(1, ...depthMap.values());
    const cols = Array.from({ length: maxCol + 1 }, () => []);
    vis.forEach(id => cols[depthMap.get(id)].push(id));

    const orderList = d.order.concat(st.N.has(NONE_GROUP) ? [NONE_GROUP] : []);
    const priRank = new Map(orderList.map((id, i) => [id, i]));
    cols[0].sort((a, b) => (priRank.get(a) ?? 999) - (priRank.get(b) ?? 999));

    const pos = new Map();
    const maxRows = Math.max(1, ...cols.slice(1).map(c => c.length));
    const totalH = Math.max(420, maxRows * RY) + PAD * 2;
    const step0 = cols[0].length > 1 ? (totalH - PAD * 2 - PH) / (cols[0].length - 1) : 0;
    cols[0].forEach((id, i) => pos.set(id, { x: PAD, y: PAD + i * Math.max(PH + 24, step0), w: W, h: PH, col: 0 }));

    for (let c = 1; c <= maxCol; c++) {
      cols[c].sort((a, b) => {
        const pa = (st.parents.get(a) || []).filter(p => pos.has(p));
        const pb = (st.parents.get(b) || []).filter(p => pos.has(p));
        const ya = pa.length ? (c === 1 ? Math.min(...pa.map(p => pos.get(p).y)) : pa.reduce((s, p) => s + pos.get(p).y, 0) / pa.length) : 1e6;
        const yb = pb.length ? (c === 1 ? Math.min(...pb.map(p => pos.get(p).y)) : pb.reduce((s, p) => s + pos.get(p).y, 0) / pb.length) : 1e6;
        return ya - yb || ((st.N.get(b)?.behind || 0) - (st.N.get(a)?.behind || 0)) || a.localeCompare(b);
      });
      cols[c].forEach((id, i) => pos.set(id, { x: PAD + c * CX, y: PAD + i * RY, w: W, h: H, col: c }));
    }

    st.pos = pos;
    const maxY = pos.size ? Math.max(...[...pos.values()].map(p => p.y + p.h)) : 400;
    st.size = { w: PAD * 2 + (maxCol + 1) * CX, h: maxY + PAD * 2 };
    return maxCol;
  }

  function applyTransform() {
    world.style.transform = `translate(${st.T.x}px,${st.T.y}px) scale(${st.T.k})`;
    world.style.setProperty('--rm-inv-k', String(1 / st.T.k));
  }

  function fit() {
    const r = stage.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const k = Math.min(1.05, Math.max(0.24, Math.min((r.width - 32) / st.size.w, (r.height - 48) / st.size.h)));
    st.T = {
      x: Math.max(16, (r.width - st.size.w * k) / 2),
      y: Math.max(36, (r.height - st.size.h * k) / 2),
      k,
    };
    applyTransform();
  }

  function draw() {
    if (!st.doc) return;
    titleEl.textContent = displayTitle(st.doc);
    renderTabs();
    renderChips();
    renderLaneSelect();
    updatePopoutHref();

    const maxCol = computeLayout();
    world.textContent = '';
    edges.textContent = '';
    world.append(edges);

    const colHeaders = [[0, 'Priority'], [1, 'Depends on →'], [maxCol, 'Needed first']];
    const shownCols = new Set();
    for (const [c, label] of colHeaders) {
      if (c > maxCol || shownCols.has(c)) continue;
      shownCols.add(c);
      const colEl = h('div', 'rm-col', label);
      colEl.style.left = (PAD + c * CX) + 'px';
      world.append(colEl);
    }

    const relSeen = new Set();
    for (const id of st.vis) {
      const a = st.pos.get(id), n = st.N.get(id);
      for (const dep of n.needs || []) {
        if (!st.vis.has(dep)) continue;
        const b = st.pos.get(dep);
        const x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2;
        const dx = Math.max(38, Math.abs(x2 - x1) * 0.45);
        const p = svgEl('path', { d: `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}` });
        p.dataset.from = id; p.dataset.to = dep;
        edges.append(p);
      }
      for (const rel of n.related || []) {
        if (!st.vis.has(rel) || id === rel) continue;
        const pair = id < rel ? id + '\0' + rel : rel + '\0' + id;
        if (relSeen.has(pair)) continue;
        relSeen.add(pair);
        const b = st.pos.get(rel);
        const x1 = a.x + a.w / 2, y1 = a.y + a.h / 2, x2 = b.x + b.w / 2, y2 = b.y + b.h / 2;
        const p = svgEl('path', { d: `M${x1},${y1} L${x2},${y2}`, class: 'rel' });
        p.dataset.from = id; p.dataset.to = rel;
        edges.append(p);
      }
    }

    for (const id of st.vis) {
      const n = st.N.get(id), p = st.pos.get(id);
      const el = h('div', 'rm-nd ' + catOf(n));
      el.dataset.id = id;
      el.style.left = p.x + 'px';
      el.style.top = p.y + 'px';
      el.append(h('b', '', displayNodeTitle(n, n._idx)));

      el.onclick = e => {
        e.stopPropagation();
        st.sel = st.sel === id ? null : id;
        if (st.sel && st.asideCollapsed) {
          st.asideCollapsed = false;
          st.asideAutoOpened = true;
          syncAsideToggle(false);
        } else if (!st.sel && st.asideAutoOpened) {
          st.asideCollapsed = true;
          st.asideAutoOpened = false;
          syncAsideToggle(true);
        }
        marks();
        renderAside();
        if (opts.onSelectNode) opts.onSelectNode(st.sel ? st.N.get(st.sel) : null, st.doc);
      };
      world.append(el);
    }

    noticeAlerts = [...(st.doc.problems || []), ...(st.doc.warnings || [])];
    renderNotice();

    marks();
    renderAside();
    if (!st.fitted) { st.fitted = true; requestAnimationFrame(fit); }
    else applyTransform();
  }

  function syncAlerts() {
    if (!st.doc) return;
    world.querySelectorAll('.rm-nd').forEach(el => {
      const n = st.N.get(el.dataset.id);
      el.classList.remove('glow', 'pulse');
      const oldRing = el.querySelector('.rm-ring');
      if (oldRing) oldRing.remove();
      const oldBadge = el.querySelector('.rm-badge');
      if (oldBadge) oldBadge.remove();
      if (!n || !n.attention) return;
      const calm = calmState(st.doc.id, n.id, n.attention);
      const loud = n.attention.alert !== 'none' && !calm.seen && !calm.until;
      if (loud) {
        el.classList.add(n.attention.alert);
        const ring = svgEl('svg', { class: 'rm-ring', 'aria-hidden': 'true' });
        ring.append(svgEl('rect', { width: '100%', height: '100%' }));
        el.append(ring);
      }
      const badge = h('span', 'rm-badge' + (loud ? ' alert' : ''));
      badge.append(kindIcon(n.attention.kind));
      el.append(badge);
    });
  }

  function marks() {
    if (!st.doc) return;
    syncAlerts();
    const needCount = st.doc.nodes.filter(n => {
      if (!n.attention || n.attention.alert === 'none') return false;
      const c = calmState(st.doc.id, n.id, n.attention);
      return !c.seen && !c.until;
    }).length;
    btnNeed.hidden = needCount === 0 && !st.needOnly;
    btnNeed.textContent = `${needCount} need you`;
    btnNeed.setAttribute('aria-pressed', String(st.needOnly));

    let keep = null, up = new Set(), down = new Set();
    if (st.sel && st.N.has(st.sel)) {
      up = closure(st.sel, i => st.N.get(i)?.needs || []);
      down = closure(st.sel, i => st.parents.get(i) || []);
      keep = new Set([st.sel, ...up, ...down]);
    } else if (st.needOnly) {
      const seeds = st.doc.nodes.filter(n => n.open && (n.state === 'awaiting-user' || (n.attention && n.attention.alert !== 'none'))).map(n => n.id);
      keep = new Set(seeds);
      seeds.forEach(s => closure(s, i => st.parents.get(i) || []).forEach(x => keep.add(x)));
    } else if (st.lane) {
      const seeds = st.doc.nodes.filter(n => n.open && n.kind !== 'priority' && sameLane(n.lane, st.lane)).map(n => n.id);
      keep = new Set(seeds);
      seeds.forEach(s => {
        closure(s, i => st.N.get(i)?.needs || []).forEach(x => keep.add(x));
        closure(s, i => st.parents.get(i) || []).forEach(x => keep.add(x));
      });
    }

    world.querySelectorAll('.rm-nd').forEach(el => {
      const id = el.dataset.id;
      el.classList.toggle('sel', id === st.sel);
      el.classList.toggle('off', !!keep && !keep.has(id));
    });
    edges.querySelectorAll('path').forEach(p => {
      const a = p.dataset.from, b = p.dataset.to;
      const isUp = st.sel && (a === st.sel || up.has(a)) && up.has(b);
      const isDown = st.sel && (b === st.sel || down.has(b)) && down.has(a);
      p.classList.toggle('up', !!isUp);
      p.classList.toggle('down', !!isDown);
      p.classList.toggle('off', !!keep && !(keep.has(a) && keep.has(b)));
    });
  }

  function renderAside() {
    aside.textContent = '';
    if (!st.doc) { aside.append(h('div', 'rm-empty', 'Loading…')); return; }

    const pickNode = id => {
      if (!st.vis.has(id)) { st.view = 'all'; st.sel = id; st.fitted = false; draw(); }
      else { st.sel = id; marks(); renderAside(); }
      if (opts.onSelectNode) opts.onSelectNode(st.N.get(id) || null, st.doc);
    };

    const mkList = (heading, ids, showBehind = false) => {
      const valid = ids.filter(id => st.N.has(id));
      if (!valid.length) return;
      aside.append(h('h4', '', `${heading} (${valid.length})`));
      const ul = h('ul', 'rm-list');
      valid.forEach(id => {
        const item = st.N.get(id);
        const li = h('li');
        const dot = h('i', 'rm-dot');
        dot.style.background = dotColor(catOf(item));
        const suffix = showBehind && item.behind ? ` (${item.behind})` : '';
        li.append(dot, h('span', '', displayNodeTitle(item, item._idx) + suffix));
        li.onclick = () => pickNode(id);
        ul.append(li);
      });
      aside.append(ul);
    };

    if (st.sel && st.N.has(st.sel)) {
      const n = st.N.get(st.sel);
      aside.append(h('span', 'rm-tag', `${n.kind} · ${STATE_LABEL[n.state] || n.state}`));
      aside.append(h('h3', '', displayNodeTitle(n, n._idx)));
      const kv = (label, value) => {
        if (!value) return;
        const d = h('div', 'rm-kv');
        d.append(h('strong', '', label + ': '), document.createTextNode(value));
        aside.append(d);
      };
      kv('Lane', displayLane(n.lane));
      if (!n.lane && n.suggested) kv('Suggested', displayLane(n.suggested));
      kv('Owner', mask(n.owner));
      if (n.behind) kv('Unlocks', `${n.behind} open`);
      if (n.due) kv('Due', n.due);
      if (n.when) kv('When', n.when);
      if (n.days != null) kv('Estimate', `${n.days} d`);
      kv('Source', mask(n.source));

      const acts = h('div', 'rm-actions');
      const targetLane = n.lane || n.suggested || st.doc.owner_lane;
      const sid = agentIdOf(targetLane);
      if (sid && opts.onShowAgent) {
        const b = h('button', 'primary', st.obfuscate ? 'Show on map' : `Show ${targetLane}`);
        b.type = 'button';
        b.onclick = () => opts.onShowAgent(sid);
        acts.append(b);
      } else if (sid && st.standalone && opts.mapHref) {
        const a = h('a', '', st.obfuscate ? 'Show on map' : `Show ${targetLane}`);
        a.href = opts.mapHref + '?agent=' + encodeURIComponent(sid);
        acts.append(a);
      }
      const openInfo = st.doc.open && targetLane && Object.prototype.hasOwnProperty.call(st.doc.open, targetLane) ? st.doc.open[targetLane] : null;
      if (openInfo && openInfo.href) {
        const a = h('a', '', openInfo.open ? 'Open agent ↗' : 'Open workspace ↗');
        a.href = openInfo.href;
        acts.append(a);
      }
      if (n.attention) {
        const calm = calmState(st.doc.id, n.id, n.attention);
        const changed = () => { draw(); if (opts.onSeenChange) opts.onSeenChange(); };
        if (n.attention.alert !== 'none') {
          const bSeen = h('button', '', calm.seen ? 'Restore alert' : 'Seen');
          bSeen.type = 'button';
          bSeen.onclick = () => { setItemSeen(st.doc.id, n.id, n.attention, !calm.seen); changed(); };
          acts.append(bSeen);
        }
        if (calm.until) {
          const t = new Date(calm.until);
          const hhmm = [t.getHours(), t.getMinutes()].map(v => String(v).padStart(2, '0')).join(':');
          const bUnsnooze = h('button', '', `Snoozed until ${hhmm}`);
          bUnsnooze.type = 'button';
          bUnsnooze.onclick = () => { setItemSnooze(st.doc.id, n.id, n.attention, null); changed(); };
          acts.append(bUnsnooze);
        } else {
          const b1h = h('button', '', '1 h');
          b1h.type = 'button';
          b1h.onclick = () => { setItemSnooze(st.doc.id, n.id, n.attention, 'hour'); changed(); };
          const bTom = h('button', '', 'Tomorrow');
          bTom.type = 'button';
          bTom.onclick = () => { setItemSnooze(st.doc.id, n.id, n.attention, 'tomorrow'); changed(); };
          acts.append(b1h, bTom);
        }
      }
      if (acts.childNodes.length) aside.append(acts);
      if (n.body) aside.append(h('p', 'rm-p', mask(n.body)));

      mkList('Needs first', n.needs || []);
      mkList('Blocks', st.parents.get(n.id) || []);
      if (n.related && n.related.length) mkList('Related', n.related);
      if (n.ext && n.ext.length) {
        aside.append(h('h4', '', `External prerequisites (${n.ext.length})`));
        const ul = h('ul', 'rm-list');
        n.ext.forEach(ref => {
          const li = h('li');
          li.style.cursor = 'default';
          const dot = h('i', 'rm-dot');
          dot.style.background = 'var(--rm-idle)';
          li.append(dot, h('span', '', mask(ref, 'external/•••')));
          ul.append(li);
        });
        aside.append(ul);
      }
      if (n.archived_needs && n.archived_needs.length) {
        aside.append(h('h4', '', `Archived prerequisites (${n.archived_needs.length})`));
        const ul = h('ul', 'rm-list');
        n.archived_needs.forEach(ref => {
          const li = h('li');
          li.style.cursor = 'default';
          const dot = h('i', 'rm-dot');
          dot.style.background = 'var(--rm-ok)';
          li.append(dot, h('span', '', mask(ref, 'archived/•••')));
          ul.append(li);
        });
        aside.append(ul);
      }
      return;
    }

    // Overview sidebar
    aside.append(h('span', 'rm-tag', st.obfuscate ? 'collection' : st.doc.collection));
    aside.append(h('h3', '', st.lane ? `${displayLane(st.lane)}'s lane` : displayTitle(st.doc)));
    const scope = st.lane
      ? st.doc.nodes.filter(n => n.open && n.kind !== 'priority' && sameLane(n.lane, st.lane))
      : st.doc.nodes.filter(n => n.open && n.kind !== 'priority');
    const waiting = scope.filter(n => n.state === 'awaiting-user').sort((a, b) => (b.behind - a.behind) || a.id.localeCompare(b.id));
    aside.append(h('div', 'rm-kv', `${scope.length} open · ${waiting.length} waiting on you`));
    mkList('Waiting on you', waiting.map(n => n.id), true);
    if (st.lane) mkList('Open in lane', scope.map(n => n.id));
  }

  function updateStatus() {
    if (st.failed) {
      statusEl.textContent = st.doc ? 'Server unreachable; showing last read' : 'Server unreachable';
      statusEl.className = 'rm-status stale';
      statusEl.hidden = false;
    } else {
      statusEl.textContent = '';
      statusEl.className = 'rm-status';
      statusEl.hidden = true;
    }
  }

  async function fetchDoc(force = false) {
    if (st.destroyed) return;
    const reqId = st.roadmapId;
    if (!force && st.inFlightId === reqId) return;
    const seq = ++st.reqSeq;
    if (st.abortCtrl) {
      try { st.abortCtrl.abort(); } catch (e) { /* ignore */ }
    }
    const ctrl = typeof AbortController === 'function' ? new AbortController() : null;
    st.abortCtrl = ctrl;
    st.inFlightId = reqId;
    const url = st.apiUrl
      ? st.apiUrl
      : `${st.apiBase}/${encodeURIComponent(reqId)}`;
    try {
      const fetchOpts = ctrl ? { cache: 'no-store', signal: ctrl.signal } : { cache: 'no-store' };
      const r = await fetch(url, fetchOpts);
      if (st.destroyed || seq !== st.reqSeq || reqId !== st.roadmapId) return;
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const doc = await r.json();
      if (st.destroyed || seq !== st.reqSeq || reqId !== st.roadmapId) return;
      st.failed = 0;
      st.stamp = new Date();
      const sig = JSON.stringify([doc.id, doc.title, doc.nodes, doc.order, doc.loose, doc.lanes, doc.open, doc.problems, doc.warnings]);
      if (sig !== st.key) {
        st.key = sig;
        st.doc = doc;
        buildIndex();
        if (st.sel && st.N.has(st.sel) && st.view !== 'all' && !st.vis.has(st.sel)) st.view = 'all';
        draw();
      } else {
        marks();
        renderAside();
      }
      updateStatus();
    } catch (e) {
      if (st.destroyed || seq !== st.reqSeq || reqId !== st.roadmapId || e?.name === 'AbortError') return;
      st.failed++;
      updateStatus();
    } finally {
      if (seq === st.reqSeq) {
        st.inFlightId = null;
        if (st.abortCtrl === ctrl) st.abortCtrl = null;
      }
    }
  }

  btnNeed.onclick = () => { st.needOnly = !st.needOnly; st.sel = null; marks(); renderAside(); };
  zi.onclick = () => { st.T.k = Math.min(2.2, st.T.k * 1.25); applyTransform(); };
  zo.onclick = () => { st.T.k = Math.max(0.2, st.T.k / 1.25); applyTransform(); };
  zf.onclick = fit;

  let drag = null;
  stage.onpointerdown = e => {
    if (e.button !== 0 || e.target.closest('.rm-nd, button')) return;
    drag = { x: e.clientX - st.T.x, y: e.clientY - st.T.y, moved: false };
    stage.classList.add('drag');
  };
  stage.onpointermove = e => {
    if (!drag) return;
    const nx = e.clientX - drag.x, ny = e.clientY - drag.y;
    if (Math.hypot(nx - st.T.x, ny - st.T.y) >= 3) drag.moved = true;
    st.T.x = nx; st.T.y = ny;
    applyTransform();
  };
  stage.onpointerup = stage.onpointercancel = () => {
    const moved = drag && drag.moved;
    drag = null;
    stage.classList.remove('drag');
    if (moved) stage.dataset.swallow = '1';
  };
  stage.onclick = e => {
    if (stage.dataset.swallow) { delete stage.dataset.swallow; return; }
    if (!e.target.closest('.rm-nd, button') && st.sel) {
      st.sel = null;
      if (st.asideAutoOpened) {
        st.asideCollapsed = true;
        st.asideAutoOpened = false;
        syncAsideToggle(true);
      }
      marks();
      renderAside();
      if (opts.onSelectNode) opts.onSelectNode(null, st.doc);
    }
  };
  stage.addEventListener('wheel', e => {
    e.preventDefault();
    const r = stage.getBoundingClientRect();
    const cx = e.clientX - r.left, cy = e.clientY - r.top;
    const f = Math.exp(-e.deltaY * (e.ctrlKey ? 0.011 : 0.0017));
    const nk = Math.min(2.2, Math.max(0.18, st.T.k * f));
    st.T.x = cx - (cx - st.T.x) * (nk / st.T.k);
    st.T.y = cy - (cy - st.T.y) * (nk / st.T.k);
    st.T.k = nk;
    applyTransform();
  }, { passive: false });

  const onStorage = e => {
    if (st.destroyed || !st.doc) return;
    if (e.key === SEEN_KEY || e.key === SNOOZE_KEY || e.key === null) {
      marks();
      renderAside();
    }
  };
  window.addEventListener('storage', onStorage);

  fetchDoc(true);

  return {
    load(roadmapId, lane = null, nodeId = null, roadmaps = null) {
      if (roadmaps) st.roadmaps = roadmaps;
      const changedId = roadmapId && roadmapId !== st.roadmapId;
      if (roadmapId) st.roadmapId = roadmapId;
      st.lane = lane || null;
      st.sel = nodeId || null;
      if (changedId) { st.view = 'all'; st.fitted = false; st.key = ''; }
      if (changedId) fetchDoc(true);
      else if (!st.doc) fetchDoc(false);
      else if (st.sel && st.N.has(st.sel) && !st.vis.has(st.sel)) {
        st.view = 'all';
        st.fitted = false;
        draw();
      } else {
        renderTabs(); renderLaneSelect(); updatePopoutHref(); marks(); renderAside();
      }
    },
    refresh(roadmaps = null) {
      if (roadmaps) st.roadmaps = roadmaps;
      fetchDoc(false);
    },
    setObfuscate(on) {
      st.obfuscate = !!on;
      if (st.doc) draw();
    },
    setAsideCollapsed(on, respectUser = true) {
      if (respectUser && st.asideUserChoice !== null) return;
      st.asideCollapsed = !!on;
      st.asideAutoOpened = false;
      syncAsideToggle(false);
    },
    setActivePreset(pct) {
      sizeButtons.forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.pct) === pct)));
    },
    fit,
    current() { return { roadmapId: st.roadmapId, lane: st.lane, sel: st.sel, title: st.doc?.title || '' }; },
    destroy() {
      st.destroyed = true;
      st.reqSeq++;
      st.inFlightId = null;
      if (st.abortCtrl) {
        try { st.abortCtrl.abort(); } catch (e) { /* ignore */ }
        st.abortCtrl = null;
      }
      window.removeEventListener('storage', onStorage);
      container.textContent = '';
    },
  };
}
