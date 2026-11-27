// Derived Attention, open collection items, Seen and Snooze state in the browser.
//
// An agent needs Attention when it waits in RepoPrompt CE (a.run === 'waiting') or has an
// unsnoozed collection item with derived `attention: true` (open and awaiting-user or past due).
// Seen and Snooze are browser-local calm controls that never edit collection files; both are
// keyed per collection source and reset automatically if an item's due date, title or state changes.

import { svg, store } from './util.js';

const KEY = 'agents-map.seen.v1';
const ITEM = 'item:';
const SNOOZE = 'agents-map.snooze.v1';
const snoozeKeys = new WeakMap();
export const GLOW_PERIOD = 600;    // ms, one dash-and-gap step of the outline (matches map.css)

function load(key = KEY) {
  const v = store('local', key);
  return v && typeof v === 'object' && !Array.isArray(v) ? v : {};
}

export function setSnooze(it, duration) {
  const pair = snoozeKeys.get(it);
  if (!pair) return;
  const [key, sig] = pair, saved = load(SNOOZE);
  if (!duration) delete saved[key];
  else {
    const now = new Date();
    const until = duration === 'hour' ? now.getTime() + 3600000
      : new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9).getTime();
    saved[key] = { until, sig };
  }
  store('local', SNOOZE, Object.keys(saved).length ? saved : null);
}

function marked(s, mark) {
  return Object.prototype.hasOwnProperty.call(s, mark[0]) && s[mark[0]] === mark[1];
}

function itemSig(due, title, stateRaw) {
  return JSON.stringify([due || '', title || '', stateRaw || '']);
}

function itemSeenKey(source, id, due, title, stateRaw) {
  return ITEM + JSON.stringify([source, id, due || '', title || '', stateRaw || '']);
}

function keySource(k) {
  if (k.indexOf(ITEM) !== 0) return null;
  try {
    const parsed = JSON.parse(k.slice(ITEM.length));
    if (Array.isArray(parsed) && typeof parsed[0] === 'string' && parsed[0]) return parsed[0];
  } catch (e) { /* malformed key */ }
  return '';
}

function compareItems(a, b) {
  const ra = a.attention ? 0 : 1, rb = b.attention ? 0 : 1;
  if (ra !== rb) return ra - rb;
  if (a.attention) {
    const oa = a.overdue ? 0 : 1, ob = b.overdue ? 0 : 1;
    if (oa !== ob) return oa - ob;
  } else {
    const sa = a.state === 'in-progress' ? 0 : a.blocked ? 1 : 2;
    const sb = b.state === 'in-progress' ? 0 : b.blocked ? 1 : 2;
    if (sa !== sb) return sa - sb;
  }
  const da = a.due || '9999', db = b.due || '9999';
  return da.localeCompare(db) || a.id.localeCompare(b.id);
}

// Attaches open items from all registered collections to agents, derives a.needs / a.seen,
// and returns unattached attention items ({ general, activeGeneral }) for the top bar.
export function applyCollections(collections, agents, allById, drawnById, obscure) {
  const s = load(), live = new Set(), snoozes = load(SNOOZE), activeSnoozes = new Set(), now = Date.now();
  const authoritative = new Set();
  const general = [], activeGeneral = [];

  agents.forEach(function (a) {
    a.attItems = [];
    a.otherItems = [];
    a.items = [];
    a.needMarks = a.run === 'waiting' ? [[a.id, a.state_at == null ? null : a.state_at]] : [];
  });

  (Array.isArray(collections) ? collections : []).forEach(function (col) {
    if (!col || !Array.isArray(col.items) || !col.id) return;
    if (!col.incomplete) authoritative.add(col.id);
    col.items.forEach(function (raw) {
      const snKey = ITEM + JSON.stringify([col.id, raw.id]);
      const sig = itemSig(raw.due, raw.title, raw.state_raw);
      let snoozedUntil = null;
      if (raw.attention) {
        const saved = snoozes[snKey];
        if (saved?.sig === sig && Number.isFinite(saved.until) && saved.until > now) {
          snoozedUntil = saved.until;
          activeSnoozes.add(snKey);
        }
      }
      const it = {
        ...raw,
        source: col.id,
        sourceTitle: obscure ? 'Collection' : (raw.source_title || col.title || col.id),
        title: obscure ? '•••' : raw.title,
        stateDetail: obscure && raw.state_detail ? '•••' : (raw.state_detail || ''),
        lane: obscure && raw.lane ? 'Agent' : (raw.lane || ''),
        kind: obscure && raw.kind ? '•••' : (raw.kind || ''),
        snoozedUntil,
      };
      if (raw.attention) snoozeKeys.set(it, [snKey, sig]);

      const target = raw.agent ? allById.get(raw.agent) : null;
      if (target) {
        if (it.attention) target.attItems.push(it);
        else target.otherItems.push(it);
      } else if (it.attention) {
        general.push(it);
        if (!snoozedUntil) activeGeneral.push(it);
      }

      if (it.attention) {
        const mark = itemSeenKey(col.id, raw.id, raw.due, raw.title, raw.state_raw);
        live.add(mark);
        if (target && !snoozedUntil) target.needMarks.push([mark, true]);
      }
    });
  });

  if (general.length > 1) {
    general.sort(compareItems);
    activeGeneral.sort(compareItems);
  }

  agents.forEach(function (a) {
    if (a.attItems.length > 1) a.attItems.sort(compareItems);
    if (a.otherItems.length > 1) a.otherItems.sort(compareItems);
    a.items = a.attItems.concat(a.otherItems);
    a.needs = a.needMarks.length > 0;
    a.seen = a.needs && a.needMarks.every(function (m) { return marked(s, m); });
    a.needMarks.forEach(function (m) { live.add(m[0]); });
    if (a.items.length) {
      a.hay += ' ' + a.items.map(function (it) {
        return [it.title, it.state, it.stateDetail, it.blocked ? 'blocked' : '', it.overdue ? 'overdue' : '', it.kind].filter(Boolean).join(' ');
      }).join(' ').toLowerCase();
    }
    if (a.needs && a.hay.indexOf('attention') < 0) a.hay += ' attention';
  });

  // Prune per source: keep marks/snoozes for sources that were not authoritatively loaded.
  let pruned = false;
  Object.keys(s).forEach(function (k) {
    if (live.has(k)) return;
    const src = keySource(k);
    if (src !== null && !authoritative.has(src)) return;
    delete s[k];
    pruned = true;
  });
  if (pruned) store('local', KEY, Object.keys(s).length ? s : null);

  pruned = false;
  Object.keys(snoozes).forEach(function (k) {
    if (activeSnoozes.has(k)) return;
    const active = Number.isFinite(snoozes[k]?.until) && snoozes[k].until > now;
    if (active) {
      const src = keySource(k);
      if (src !== null && !authoritative.has(src)) return;
    }
    delete snoozes[k];
    pruned = true;
  });
  if (pruned) store('local', SNOOZE, Object.keys(snoozes).length ? snoozes : null);

  return { general, activeGeneral };
}

export function markSeen(a) {
  const s = load();
  a.needMarks.forEach(function (m) { s[m[0]] = m[1]; });
  store('local', KEY, s);
  a.seen = true;
}

// Crisp diamond mark for Attention badges and items.
export function attentionIcon() {
  const s = svg('svg', { class: 'att-ic', viewBox: '0 0 12 12', 'aria-hidden': 'true' });
  s.appendChild(svg('path', { d: 'M6 1L11 6L6 11L1 6Z' }));
  return s;
}

export function itemStateText(it) {
  if (!it.state) return '';
  return it.stateDetail ? it.state + ' ' + it.stateDetail : it.state;
}

export function itemMeta(it) {
  const parts = [];
  const st = itemStateText(it);
  if (st) parts.push(st);
  if (it.overdue) parts.push('overdue');
  if (it.due) parts.push('due ' + it.due);
  if (it.blocked && it.state !== 'blocked') parts.push('blocked');
  if (it.kind) parts.push(it.kind);
  return parts.join(' · ');
}

export function phaseDelay(period) { return '-' + (Date.now() % period) / 1000 + 's'; }
export function glowDelay() { return phaseDelay(GLOW_PERIOD); }
