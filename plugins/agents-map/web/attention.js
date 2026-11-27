// "Needs you": the agents that wait for the user's reply, answer or approval, and the agents
// an attention item with an alert level points at. The map's motion, the bar count and its
// filter all read a.needs, so every source of need feeds that one flag (a.needMarks lists
// them); a.alert says how loudly ("glow" or "pulse"; a waiting agent glows, and the
// stronger level wins).
//
// Attention items come from another program through the server (graph.attention, already
// validated there); the writer chooses each item's alert level. An item is shown on its agent
// when that agent is drawn; otherwise it is listed under the owner (the agent that wrote the
// list), or in the bar when the owner is not drawn either.
//
// Seen is a transient acknowledgment kept in the browser, not in the layout or undo: it stops
// the motion of one agent until what made it need the user changes. A waiting agent's mark is
// its state_at; an item's is its id, due and reason.

import { svg, store } from './util.js';

const KEY = 'agents-map.seen.v1';   // {agent id: state_at, 'item:' + [id, due, reason]: true}
const ITEM = 'item:';
const SNOOZE = 'agents-map.snooze.v1';
const snoozeKeys = new WeakMap();
export const GLOW_PERIOD = 600;    // ms, one dash-and-gap step of the outline (must match the march animation in map.css)
export const PULSE_PERIOD = 300;   // ms, the same step at the stronger level, twice as fast (likewise map.css)
export const HALO_PERIOD = 600;    // ms, one breath of the pulse's halo (likewise map.css)
export const OLD_LIST = 6 * 3600;   // seconds: a list older than this is reported
const SEVERITY = { blocker: 0, deadline: 1, calendar: 2, watch: 3 };
const LEVEL = { none: 0, glow: 1, pulse: 2 };
const LEVEL_NAME = ['none', 'glow', 'pulse'];

function load(key = KEY) {
  const v = store('local', key);
  return v && typeof v === 'object' && !Array.isArray(v) ? v : {};
}

export function setSnooze(it, duration) {
  const [key, sig] = snoozeKeys.get(it), saved = load(SNOOZE);
  if (!duration) delete saved[key];
  else {
    const now = new Date();
    const until = duration === 'hour' ? now.getTime() + 3600000
      : new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 9).getTime();
    saved[key] = {until, sig};
  }
  store('local', SNOOZE, Object.keys(saved).length ? saved : null);
}

function marked(s, mark) { return Object.prototype.hasOwnProperty.call(s, mark[0]) && s[mark[0]] === mark[1]; }

// Most pressing first: the louder alert level, then blocker before deadline before calendar
// before watch, then the lower rank number, then the earlier due time.
function compare(a, b) {
  const rank = function (it) { return it.rank == null ? 99 : it.rank; }, due = function (it) { return it.due == null ? Infinity : it.due; };
  return (LEVEL[b.alert] - LEVEL[a.alert]) || (SEVERITY[a.kind] - SEVERITY[b.kind]) || (rank(a) - rank(b)) || (due(a) - due(b));
}

function seenKeyOwner(k) {
  if (k.indexOf(ITEM) !== 0) return null;
  try {
    const parsed = JSON.parse(k.slice(ITEM.length));
    if (Array.isArray(parsed) && parsed.length === 4 && typeof parsed[0] === 'string' && parsed[0]) {
      return { primary: false, source: parsed[0] };
    }
  } catch (e) { /* treat malformed key as legacy primary */ }
  return { primary: true, source: '' };
}

function snoozeKeyOwner(k, primaryNs) {
  if (k.indexOf(ITEM) !== 0) return null;
  try {
    const parsed = JSON.parse(k.slice(ITEM.length));
    if (Array.isArray(parsed) && parsed.length >= 2 && typeof parsed[0] === 'string') {
      const ns = parsed[0];
      if (ns === '' || ns === primaryNs) return { primary: true, source: '' };
      return { primary: false, source: ns };
    }
  } catch (e) { /* malformed key */ }
  return { primary: true, source: '' };
}

// Gives every agent its items (a.items), its sources of need (a.needMarks) and a.needs, a.seen;
// forgets Seen marks that no longer match anything in sources authoritatively received in this
// snapshot. Returns the primary list as the model keeps it:
// {updated, owner (a drawn agent or null), items, loose, activeLoose}, or null.
export function applyAttention(att, agents, allById, drawnById, obscure, attentions = null) {
  const s = load(), live = new Set(), snoozes = load(SNOOZE), keys = new Set(), now = Date.now();
  agents.forEach(function (a) {
    a.items = [];
    a.needMarks = a.run === 'waiting' ? [[a.id, a.state_at == null ? null : a.state_at, 'glow']] : [];
  });
  const sources = [];
  const seenRoadmapSources = new Set();
  const authoritativeRoadmapSources = new Set();
  let hasPrimary = false;
  if (att && Array.isArray(att.items)) {
    sources.push({ ...att, _primary: true });
    hasPrimary = true;
  }
  if (Array.isArray(attentions)) {
    attentions.forEach(function (src) {
      if (!src || !Array.isArray(src.items)) return;
      const isPrimaryBlock = src.primary === true || !src.source;
      if (isPrimaryBlock) {
        if (!hasPrimary) {
          sources.push({ ...src, _primary: true });
          hasPrimary = true;
        }
        return;
      }
      if (!seenRoadmapSources.has(src.source)) {
        seenRoadmapSources.add(src.source);
        if (!src.incomplete) authoritativeRoadmapSources.add(src.source);
        sources.push({ ...src, _primary: false });
      }
    });
  }
  const primarySrc = sources.find(function (src) { return src._primary; }) || null;
  const primaryNs = (primarySrc && primarySrc.owner) || '';
  let list = null;
  if (primarySrc) {
    list = { updated: primarySrc.updated, owner: drawnById.get(primarySrc.owner) || null, items: [], loose: [], activeLoose: [] };
  }
  sources.forEach(function (src) {
    const isPrimary = !!src._primary;
    const ns = isPrimary ? (src.owner || '') : src.source;
    src.items.slice().sort(compare).forEach(function (raw) {
      const key = ITEM + JSON.stringify([ns, raw.id]);
      const sig = JSON.stringify([raw.due, raw.reason, raw.alert]);
      const saved = snoozes[key];
      const snoozedUntil = saved?.sig === sig && Number.isFinite(saved.until) && saved.until > now ? saved.until : null;
      if (snoozedUntil) keys.add(key);
      const it = { ...raw, source: isPrimary ? null : (raw.source || src.source || null), sourceOwner: src.owner || null,
        reason: obscure ? '•••' : raw.reason, snoozedUntil };
      snoozeKeys.set(it, [key, sig]);
      if (isPrimary && list) {
        list.items.push(it);
        if (!drawnById.has(it.agent)) {
          list.loose.push(it);
          if (!snoozedUntil) list.activeLoose.push(it);
        }
      }
      const on = allById.get(it.agent);
      if (on) on.items.push(it);
      else if (!isPrimary && src.owner && allById.has(src.owner)) allById.get(src.owner).items.push(it);
      const target = on || (src.owner ? allById.get(src.owner) : null);
      if (it.alert !== 'none') {
        const mark = ITEM + JSON.stringify(it.source ? [it.source, it.id, it.due, raw.reason] : [it.id, it.due, raw.reason]);
        live.add(mark);
        if (target && !snoozedUntil) target.needMarks.push([mark, true, it.alert]);
      }
    });
  });
  agents.forEach(function (a) {
    if (a.items.length > 1) a.items.sort(compare);
    let level = 0;
    a.needMarks.forEach(function (m) { level = Math.max(level, LEVEL[m[2]]); });   // the stronger level wins
    a.alert = LEVEL_NAME[level];
    a.needs = level > 0;
    a.seen = a.needs && a.needMarks.every(function (m) { return marked(s, m); });
    a.needMarks.forEach(function (m) { live.add(m[0]); });
    if (a.items.length) a.hay += ' ' + a.items.map(function (it) { return it.kind + ' ' + it.reason; }).join(' ').toLowerCase();
    if (a.needs && a.hay.indexOf('needs-you') < 0) a.hay += ' needs-you';
  });
  // Prune per source: a mark or active snooze is deleted only when its own source returned an
  // authoritative (complete) list in this snapshot, so a missing or partial read keeps its state.
  let pruned = false;
  Object.keys(s).forEach(function (k) {
    if (live.has(k)) return;
    const owner = seenKeyOwner(k);
    if (owner) {
      const authoritative = owner.primary ? hasPrimary : authoritativeRoadmapSources.has(owner.source);
      if (!authoritative) return;
    }
    delete s[k]; pruned = true;
  });
  if (pruned) store('local', KEY, Object.keys(s).length ? s : null);
  pruned = false;
  Object.keys(snoozes).forEach(function (k) {
    if (keys.has(k)) return;
    const active = Number.isFinite(snoozes[k]?.until) && snoozes[k].until > now;
    if (active) {
      const owner = snoozeKeyOwner(k, primaryNs);
      const authoritative = owner ? (owner.primary ? hasPrimary : authoritativeRoadmapSources.has(owner.source)) : false;
      if (!authoritative) return;
    }
    delete snoozes[k]; pruned = true;
  });
  if (pruned) store('local', SNOOZE, Object.keys(snoozes).length ? snoozes : null);
  return list;
}

export function markSeen(a) {
  const s = load();
  a.needMarks.forEach(function (m) { s[m[0]] = m[1]; });
  store('local', KEY, s);
  a.seen = true;
}

// Each kind as a small mark drawn for a 12 px box, filled with currentColor so it takes the
// badge's colour: an octagon with a bar (stop), an hourglass, a calendar page and an eye. Bold
// shapes with no fine detail, so they read at ~10 px on screen. The calendar's outline parts
// keep fill="none" as attributes, which win over the svg's inherited fill.
const ICON = {
  blocker: [['path', { 'fill-rule': 'evenodd', d: 'M3.8 0.6H8.2L11.4 3.8V8.2L8.2 11.4H3.8L0.6 8.2V3.8ZM3.2 5.1H8.8V6.9H3.2Z' }]],
  deadline: [['path', { d: 'M1.7 0.7H10.3V2.3L7.1 6 10.3 9.7V11.3H1.7V9.7L4.9 6 1.7 2.3Z' }]],
  calendar: [
    ['rect', { x: 2.7, y: 0.7, width: 1.5, height: 3.1, rx: 0.75 }],
    ['rect', { x: 7.8, y: 0.7, width: 1.5, height: 3.1, rx: 0.75 }],
    ['rect', { x: 1.4, y: 2.6, width: 9.2, height: 8, rx: 1.1, fill: 'none', stroke: 'currentColor', 'stroke-width': 1.5 }],
    ['path', { d: 'M1.4 5.7H10.6', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.5 }]
  ],
  watch: [['path', { 'fill-rule': 'evenodd', d: 'M0.7 6C2.7 2.6 9.3 2.6 11.3 6C9.3 9.4 2.7 9.4 0.7 6ZM6 4.1A1.9 1.9 0 1 0 6 7.9A1.9 1.9 0 1 0 6 4.1Z' }]]
};

// The mark for a kind, shared by the badge, the owner's item list and the legend: one drawing
// per kind, so the word and the shape always match.
export function kindIcon(kind) {
  const s = svg('svg', { class: 'att-ic k-' + kind, viewBox: '0 0 12 12', 'aria-hidden': 'true' });
  (ICON[kind] || []).forEach(function (part) { s.appendChild(svg(part[0], part[1])); });
  return s;
}

// The items that get a badge on the agent: a blocker on an agent that is waiting adds nothing,
// the waiting mark already says so.
export function badgeItems(a) {
  return a.items.filter(function (it) { return !it.snoozedUntil && !(it.kind === 'blocker' && a.run === 'waiting'); });
}

// "due Wed 18 Nov, 09:30 · rank 2": what an item says besides its reason.
export function itemMeta(it) {
  const parts = [];
  if (it.due != null) {
    const d = new Date(it.due * 1000), day = d.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short' });
    parts.push('due ' + (it.all_day ? day : day + ', ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })));
  }
  if (it.rank != null) parts.push('rank ' + it.rank);
  return parts.join(' · ');
}

// Delay that puts an animation of the given period at the phase the wall clock says, so a
// redrawn box continues the motion instead of restarting it, and every box breathes together.
export function phaseDelay(period) { return '-' + (Date.now() % period) / 1000 + 's'; }
export function glowDelay() { return phaseDelay(GLOW_PERIOD); }
export function pulseDelay() { return phaseDelay(PULSE_PERIOD); }
export function haloDelay() { return phaseDelay(HALO_PERIOD); }
