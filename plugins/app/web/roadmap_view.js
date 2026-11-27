// Shared Roadmap graph renderer: mounts into Agents Map's split drawer or standalone roadmap.html.
// Zero external imports so the same file works standalone and inside Agents Map.
// Every record string is untrusted text: rendered via textContent, never innerHTML.

const SEEN_KEY = 'agents-map.seen.v1';
const SNOOZE_KEY = 'agents-map.snooze.v1';
const ITEM_PREFIX = 'item:';
const NONE_GROUP = '~unlinked';
const W = 220, H = 50, CX = 285, RY = 62, PAD = 54;

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

function diamondIcon() {
  const s = svgEl('svg', { viewBox: '0 0 12 12', 'aria-hidden': 'true' });
  s.appendChild(svgEl('path', { d: 'M6 1L11 6L6 11L1 6Z', fill: 'currentColor' }));
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

// Matches web/attention.js key rules so Seen and Snooze stay in sync across Agents Map and Roadmap.
function itemSig(due, title, stateRaw) {
  return JSON.stringify([due || '', title || '', stateRaw || '']);
}

function seenKey(source, id, due, title, stateRaw) {
  return ITEM_PREFIX + JSON.stringify([source, id, due || '', title || '', stateRaw || '']);
}

function snoozeKey(source, id) {
  return ITEM_PREFIX + JSON.stringify([source || '', id]);
}

function calmState(source, n) {
  if (!n || !n.attention) return { seen: false, until: null };
  const src = n.source || source;
  const rid = n.source_id || n.id;
  const s = loadStore(SEEN_KEY);
  const sn = loadStore(SNOOZE_KEY);
  const sk = seenKey(src, rid, n.due, n.title, n.state_raw);
  const seen = s[sk] === true;
  const nk = snoozeKey(src, rid);
  const saved = sn[nk];
  const sig = itemSig(n.due, n.title, n.state_raw);
  const until = saved && saved.sig === sig && Number.isFinite(saved.until) && saved.until > Date.now() ? saved.until : null;
  return { seen, until };
}

function setItemSeen(source, n, on) {
  const src = n.source || source;
  const rid = n.source_id || n.id;
  const s = loadStore(SEEN_KEY);
  const k = seenKey(src, rid, n.due, n.title, n.state_raw);
  if (on) s[k] = true;
  else delete s[k];
  saveStore(SEEN_KEY, s);
}

function setItemSnooze(source, n, duration) {
  const src = n.source || source;
  const rid = n.source_id || n.id;
  const sn = loadStore(SNOOZE_KEY);
  const k = snoozeKey(src, rid);
  if (!duration) delete sn[k];
  else {
    const now = new Date();
    const until = duration === 'hour'
      ? now.getTime() + 3600000
      : new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9).getTime();
    sn[k] = { until, sig: itemSig(n.due, n.title, n.state_raw) };
  }
  saveStore(SNOOZE_KEY, sn);
}

function stateClass(n) {
  if (n.id === NONE_GROUP) return 'group';
  if (n.state === 'done') return 'done';
  if (n.blocked) return 'blocked';
  if (n.state === 'in-progress') return 'wip';
  return 'neutral';
}

function dotColor(cls) {
  if (cls === 'wip') return 'var(--rm-wip)';
  if (cls === 'blocked') return 'var(--rm-blocked)';
  if (cls === 'done') return 'var(--rm-done)';
  return 'var(--rm-neutral-dot)';
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
    attOnly: false,
    obfuscate: !!opts.obfuscate,
    standalone: !!opts.standalone,
    doc: null,
    key: '',
    N: new Map(),
    parents: new Map(),
    neededBy: new Map(),
    servedBy: new Map(),
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
  const btnAtt = h('button', '', '');
  btnAtt.type = 'button';
  btnAtt.hidden = true;
  const btnAside = h('button', 'rm-aside-btn', 'Details');
  btnAside.type = 'button';
  btnAside.setAttribute('aria-label', 'Toggle details panel');
  toolsEl.append(laneSel, btnAtt, btnAside);

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
      : `${noticeAlerts.length} ${noticeAlerts.length === 1 ? 'note' : 'notes'}`;
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
    if (n.id === NONE_GROUP) return 'Unlinked';
    if (!st.obfuscate) return n.title;
    return 'Item ' + (index + 1);
  }

  function displayState(n) {
    if (!n.state) return 'open';
    if (!n.state_detail) return n.state;
    return n.state + ' ' + (st.obfuscate ? '•••' : n.state_detail);
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

  function effectiveLane(n) {
    if (n.external) return n.lane || '';
    return n.lane || (st.doc && st.doc.lane) || '';
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
    const roots = d.roots || [];
    const loose = d.loose || [];
    if (roots.length && loose.length) {
      st.N.set(NONE_GROUP, {
        id: NONE_GROUP, title: 'Unlinked', state: '', state_detail: '', state_raw: '',
        open: true, attention: false, blocked: false, overdue: false, behind: 0,
        needs: [], serves: [], graph_deps: loose.slice(), headers: [], body: '', _idx: d.nodes.length,
      });
    }
    st.parents = new Map();
    st.neededBy = new Map();
    st.servedBy = new Map();
    for (const id of st.N.keys()) {
      st.parents.set(id, []);
      st.neededBy.set(id, []);
      st.servedBy.set(id, []);
    }
    for (const n of st.N.values()) {
      for (const dep of n.graph_deps || n.needs || []) {
        if (st.parents.has(dep)) st.parents.get(dep).push(n.id);
      }
      for (const req of n.needs || []) {
        if (st.neededBy.has(req)) st.neededBy.get(req).push(n.id);
      }
      for (const tgt of n.serves || []) {
        if (st.servedBy.has(tgt)) st.servedBy.get(tgt).push(n.id);
      }
    }
  }

  function renderChips() {
    chipsEl.textContent = '';
    const d = st.doc;
    if (!d) return;
    const roots = (d.roots || []).slice();
    if (st.N.has(NONE_GROUP)) roots.push(NONE_GROUP);
    if (roots.length <= 1) return;
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
    roots.forEach((pid, idx) => {
      const p = st.N.get(pid);
      if (p) mk(pid, st.obfuscate ? (pid === NONE_GROUP ? 'Unlinked' : 'Item ' + (idx + 1)) : p.title, st.obfuscate ? '' : p.title);
    });
  }

  function renderLaneSelect() {
    laneSel.textContent = '';
    const d = st.doc;
    if (!d) return;
    const counts = new Map();
    let totalOpen = 0;
    for (const n of d.nodes) {
      if (n.open && !n.external) {
        totalOpen++;
        const ln = effectiveLane(n);
        if (ln) counts.set(ln, (counts.get(ln) || 0) + 1);
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
      closure(st.view, i => st.N.get(i)?.graph_deps || []).forEach(x => vis.add(x));
    }
    st.vis = vis;

    const rootSet = new Set((d.roots || []).concat(st.N.has(NONE_GROUP) ? [NONE_GROUP] : []));
    const memo = new Map();
    function getDepth(id, seen = new Set()) {
      if (memo.has(id)) return memo.get(id);
      if (rootSet.has(id)) { memo.set(id, 0); return 0; }
      if (seen.has(id)) return 1;
      seen.add(id);
      const ps = (st.parents.get(id) || []).filter(p => vis.has(p));
      const depth = ps.length ? 1 + Math.max(...ps.map(p => getDepth(p, new Set(seen)))) : 0;
      memo.set(id, depth);
      return depth;
    }
    const depthMap = new Map();
    vis.forEach(id => depthMap.set(id, getDepth(id)));
    const maxCol = depthMap.size ? Math.max(0, ...depthMap.values()) : 0;
    const cols = Array.from({ length: maxCol + 1 }, () => []);
    vis.forEach(id => cols[depthMap.get(id)].push(id));

    const orderList = (d.roots || []).concat(st.N.has(NONE_GROUP) ? [NONE_GROUP] : []);
    const rootRank = new Map(orderList.map((id, i) => [id, i]));
    cols[0].sort((a, b) => (rootRank.get(a) ?? 999) - (rootRank.get(b) ?? 999) || a.localeCompare(b));

    const pos = new Map();
    const maxRows = Math.max(1, ...cols.map(c => c.length));
    const totalH = Math.max(360, maxRows * RY) + PAD * 2;
    const step0 = cols[0].length > 1 && maxCol > 0
      ? Math.max(H + 18, Math.min(140, (totalH - PAD * 2 - H) / (cols[0].length - 1)))
      : RY;
    cols[0].forEach((id, i) => pos.set(id, { x: PAD, y: PAD + i * step0, w: W, h: H, col: 0 }));

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

    const colHeaders = maxCol === 0 ? [[0, 'Items']] : [[0, 'Depends on →'], [maxCol, 'Needed first']];
    for (const [c, label] of colHeaders) {
      const colEl = h('div', 'rm-col', label);
      colEl.style.left = (PAD + c * CX) + 'px';
      world.append(colEl);
    }

    for (const id of st.vis) {
      const a = st.pos.get(id), n = st.N.get(id);
      for (const dep of n.graph_deps || []) {
        if (!st.vis.has(dep)) continue;
        const b = st.pos.get(dep);
        const x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x, y2 = b.y + b.h / 2;
        const dx = Math.max(38, Math.abs(x2 - x1) * 0.45);
        const p = svgEl('path', { d: `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}` });
        p.dataset.from = id; p.dataset.to = dep;
        edges.append(p);
      }
    }

    for (const id of st.vis) {
      const n = st.N.get(id), p = st.pos.get(id);
      const el = h('div', 'rm-nd ' + stateClass(n) + (n.external ? ' ext' : ''));
      el.dataset.id = id;
      el.style.left = p.x + 'px';
      el.style.top = p.y + 'px';
      if (n.external && n.source_title) {
        el.append(h('span', 'rm-src', mask(n.source_title, 'Collection')));
      }
      el.append(h('b', '', displayNodeTitle(n, n._idx)));

      el.onclick = e => {
        e.stopPropagation();
        if (id === NONE_GROUP) return;
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
      el.classList.remove('glow');
      el.querySelector('.rm-ring')?.remove();
      el.querySelector('.rm-badge')?.remove();
      if (!n || !n.attention) return;
      const calm = calmState(st.doc.id, n);
      const active = !calm.seen && !calm.until;
      if (active) {
        el.classList.add('glow');
        const ring = svgEl('svg', { class: 'rm-ring', 'aria-hidden': 'true' });
        ring.append(svgEl('rect', { width: '100%', height: '100%' }));
        el.append(ring);
      }
      const badge = h('span', 'rm-badge' + (active ? ' alert' : ''));
      badge.append(diamondIcon());
      if (n.overdue) badge.append(h('span', '', 'overdue'));
      el.append(badge);
    });
  }

  function marks() {
    if (!st.doc) return;
    syncAlerts();
    const attCount = st.doc.nodes.filter(n => {
      if (!n.attention) return false;
      const c = calmState(st.doc.id, n);
      return !c.seen && !c.until;
    }).length;
    btnAtt.hidden = attCount === 0 && !st.attOnly;
    btnAtt.textContent = `${attCount} attention`;
    btnAtt.setAttribute('aria-pressed', String(st.attOnly));

    let keep = null, up = new Set(), down = new Set();
    if (st.sel && st.N.has(st.sel)) {
      up = closure(st.sel, i => st.N.get(i)?.graph_deps || []);
      down = closure(st.sel, i => st.parents.get(i) || []);
      keep = new Set([st.sel, ...up, ...down]);
    } else if (st.attOnly) {
      const seeds = st.doc.nodes.filter(n => n.attention).map(n => n.id);
      keep = new Set(seeds);
      seeds.forEach(s => closure(s, i => st.parents.get(i) || []).forEach(x => keep.add(x)));
    } else if (st.lane) {
      const seeds = st.doc.nodes.filter(n => n.open && sameLane(effectiveLane(n), st.lane)).map(n => n.id);
      keep = new Set(seeds);
      seeds.forEach(s => {
        closure(s, i => st.N.get(i)?.graph_deps || []).forEach(x => keep.add(x));
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
        dot.style.background = dotColor(stateClass(item));
        const suffix = showBehind && item.behind ? ` (${item.behind})` : '';
        li.append(dot, h('span', '', displayNodeTitle(item, item._idx) + suffix));
        li.onclick = () => pickNode(id);
        ul.append(li);
      });
      aside.append(ul);
    };

    if (st.sel && st.N.has(st.sel)) {
      const n = st.N.get(st.sel);
      const tags = h('div', 'rm-tags');
      tags.append(h('span', 'rm-tag', displayState(n)));
      if (n.attention) tags.append(h('span', 'rm-tag att', 'Attention'));
      if (n.overdue) tags.append(h('span', 'rm-tag blocked', 'Overdue'));
      if (n.blocked && n.state !== 'blocked') tags.append(h('span', 'rm-tag blocked', 'Blocked'));
      aside.append(tags);
      aside.append(h('h3', '', displayNodeTitle(n, n._idx)));

      const kv = (label, value) => {
        if (!value) return;
        const d = h('div', 'rm-kv');
        d.append(h('strong', '', label + ': '), document.createTextNode(value));
        aside.append(d);
      };
      const targetLane = effectiveLane(n);
      if (n.external && n.source_title) kv('Collection', mask(n.source_title, 'Collection'));
      kv('Lane', displayLane(targetLane));
      if (n.due) kv('Due', n.due + (n.overdue ? ' (overdue)' : ''));
      if (n.behind) kv('Unlocks', `${n.behind} open`);
      (n.headers || []).forEach(([k, v]) => kv(k, mask(v)));

      const acts = h('div', 'rm-actions');
      if (n.external && n.source && st.roadmaps.some(r => r.id === n.source)) {
        const b = h('button', '', st.obfuscate ? 'Open collection' : `Open ${n.source_title || n.source}`);
        b.type = 'button';
        b.onclick = () => {
          st.roadmapId = n.source;
          st.lane = null;
          st.sel = n.source_id || null;
          st.view = 'all';
          st.fitted = false;
          st.key = '';
          if (opts.onSwitchRoadmap) opts.onSwitchRoadmap(n.source);
          fetchDoc(true);
        };
        acts.append(b);
      }
      const sid = (st.doc.node_agents && st.doc.node_agents[n.id]) || agentIdOf(targetLane);
      const openInfo = (st.doc.node_open && st.doc.node_open[n.id])
        || (st.doc.open && targetLane && Object.prototype.hasOwnProperty.call(st.doc.open, targetLane) ? st.doc.open[targetLane] : null);
      const laneLabel = (openInfo && openInfo.name) || targetLane;
      if (sid && opts.onShowAgent) {
        const b = h('button', 'primary', st.obfuscate ? 'Show on map' : `Show ${laneLabel}`);
        b.type = 'button';
        b.onclick = () => opts.onShowAgent(sid);
        acts.append(b);
      } else if (sid && st.standalone && opts.mapHref) {
        const a = h('a', '', st.obfuscate ? 'Show on map' : `Show ${laneLabel}`);
        a.href = opts.mapHref + '?agent=' + encodeURIComponent(sid);
        acts.append(a);
      }
      if (openInfo && openInfo.href) {
        const a = h('a', '', openInfo.open ? 'Open agent ↗' : 'Open workspace ↗');
        a.href = openInfo.href;
        acts.append(a);
      }
      if (n.attention) {
        const calm = calmState(st.doc.id, n);
        const changed = () => { draw(); if (opts.onSeenChange) opts.onSeenChange(); };
        const bSeen = h('button', '', calm.seen ? 'Restore alert' : 'Seen');
        bSeen.type = 'button';
        bSeen.onclick = () => { setItemSeen(st.doc.id, n, !calm.seen); changed(); };
        acts.append(bSeen);
        if (calm.until) {
          const t = new Date(calm.until);
          const hhmm = [t.getHours(), t.getMinutes()].map(v => String(v).padStart(2, '0')).join(':');
          const bUnsnooze = h('button', '', `Snoozed until ${hhmm}`);
          bUnsnooze.type = 'button';
          bUnsnooze.onclick = () => { setItemSnooze(st.doc.id, n, null); changed(); };
          acts.append(bUnsnooze);
        } else {
          const b1h = h('button', '', '1 h');
          b1h.type = 'button';
          b1h.onclick = () => { setItemSnooze(st.doc.id, n, 'hour'); changed(); };
          const bTom = h('button', '', 'Tomorrow');
          bTom.type = 'button';
          bTom.onclick = () => { setItemSnooze(st.doc.id, n, 'tomorrow'); changed(); };
          acts.append(b1h, bTom);
        }
      }
      if (acts.childNodes.length) aside.append(acts);
      if (n.body) aside.append(h('p', 'rm-p', mask(n.body)));

      mkList('Needs', n.needs || []);
      mkList('Needed by', st.neededBy.get(n.id) || []);
      mkList('Serves', n.serves || []);
      mkList('Served by', st.servedBy.get(n.id) || []);

      const mkStaticList = (heading, entries, dotFn) => {
        if (!entries || !entries.length) return;
        aside.append(h('h4', '', `${heading} (${entries.length})`));
        const ul = h('ul', 'rm-list');
        entries.forEach(entry => {
          const li = h('li');
          li.style.cursor = 'default';
          const dot = h('i', 'rm-dot');
          dot.style.background = dotFn(entry);
          li.append(dot, h('span', '', entry.label));
          ul.append(li);
        });
        aside.append(ul);
      };
      mkStaticList('Archived prerequisites', (n.archived_needs || []).map(e => ({
        done: e.done, label: mask(e.id, 'archived/•••') + (e.done ? '' : ' (open)'),
      })), e => e.done ? 'var(--rm-done)' : 'var(--rm-blocked)');
      const unresolved = [
        ...(n.unresolved_needs || []).map(ref => ({ label: 'needs: ' + mask(ref, '•••') + ' (unresolved)' })),
        ...(n.unresolved_serves || []).map(ref => ({ label: 'serves: ' + mask(ref, '•••') + ' (unresolved)' })),
      ];
      mkStaticList('Unresolved', unresolved, () => 'var(--rm-neutral-dot)');
      return;
    }

    // Overview sidebar
    aside.append(h('span', 'rm-tag', st.obfuscate ? 'collection' : st.doc.collection));
    aside.append(h('h3', '', st.lane ? `${displayLane(st.lane)}'s lane` : displayTitle(st.doc)));
    const scope = st.lane
      ? st.doc.nodes.filter(n => !n.external && n.open && sameLane(effectiveLane(n), st.lane))
      : st.doc.nodes.filter(n => !n.external && n.open);
    const attList = scope.filter(n => n.attention).sort((a, b) => (b.behind - a.behind) || a.id.localeCompare(b.id));
    const blkList = scope.filter(n => !n.attention && n.blocked).sort((a, b) => (b.behind - a.behind) || a.id.localeCompare(b.id));
    aside.append(h('div', 'rm-kv', `${scope.length} open · ${attList.length} attention`));
    mkList('Attention', attList.map(n => n.id), true);
    mkList('Blocked', blkList.map(n => n.id), true);
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
      const sig = JSON.stringify([doc.id, doc.title, doc.nodes, doc.roots, doc.loose, doc.lanes, doc.open, doc.node_agents, doc.node_open, doc.problems, doc.warnings]);
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

  btnAtt.onclick = () => { st.attOnly = !st.attOnly; st.sel = null; marks(); renderAside(); };
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
