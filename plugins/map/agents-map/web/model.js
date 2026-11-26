import { app, membership, visible } from './state.js';
// Turns a graph document into linked objects: windows with their agents, agents with
// their links, and each box's size. No DOM apart from one canvas to measure text.

import { CHIP_W, CHIP_H, GAP, PAD, CW, GAPX, boxSize, colsFor } from './grid.js';
import { clamp } from './util.js';
import { applyAttention } from './attention.js';

const CLI = {
  codexExec: ['Codex', 'CX'], claudeCode: ['Claude Code', 'CC'], openCode: ['OpenCode', 'OC'],
  cursor: ['Cursor', 'CU'], grokBuild: ['Grok Build', 'GB'], antigravity: ['Antigravity', 'AG'],
  devin: ['Devin', 'DV'], claudeCodeGLM: ['Claude Code (GLM)', 'GL'], kimiCode: ['Kimi Code', 'KM'],
  customClaudeCompatible: ['Custom (Claude-compatible)', 'CM']
};

let measure = null;
function titleWidth(text) {
  if (!measure) { measure = document.createElement('canvas').getContext('2d'); measure.font = '650 13px system-ui, -apple-system, sans-serif'; }
  return measure.measureText(text).width;
}

export function duration(sec) { return sec >= 3600 ? Math.round(sec / 360) / 10 + ' h' : Math.round(sec / 60) + ' min'; }

// Which of an overseer's drawn lanes can wake it: every one, or those chosen one by one.
export function wakingLanes(a) {
  const w = a.wake || {}, chosen = new Set(w.lanes || []);
  return a.out.filter(function (l) { return w.all || chosen.has(l.dst.id); });
}

// One line for an overseer's auto-wake settings, as the app's panel sets them; null for others.
function wakeSummary(a) {
  if (!a.wake || !(a.out.length || a.out_hidden)) return null;
  const w = a.wake, n = wakingLanes(a).length;
  const who = w.all ? 'all lanes' : n ? n + ' of ' + a.out.length + ' lanes' : 'off';
  const parts = [who];
  if (who !== 'off') parts.push(w.limit ? '≤' + duration(w.limit) : 'no delay');
  if (w.idle) parts.push('idle ' + duration(w.idle));
  return 'wake: ' + parts.join(' · ');
}

function mainOverseer(a) {
  let best = null;
  a.inn.forEach(function (l) { if (!best || l.src.out.length > best.out.length) best = l.src; });
  return best;
}

// Sets a box's column count, pixel and cell size, and each chip's place inside it.
// Automatic columns follow the agents currently drawn, so boxes grow and shrink.
// Columns the user fixed stay as set.
export function sizeBox(w, arr, shared) {
  const stored = (arr.windows[w.id] || shared?.windows[w.id]);
  const n = w.agents.length;
  const kept = stored && stored.cols ? stored.cols : 0;
  const fixed = !!(kept && stored.fixed);
  const linked = w.agents.filter(function (a) { return a.linked || a.pinned; }).length;   // always drawn
  const cols = fixed ? kept : colsFor(n);
  // What the arrangement should remember. Agents without links are a view option, so
  // they may widen the box while shown but never change what is remembered.
  w.colsKeep = fixed ? kept : colsFor(linked);
  const emptyCells = clamp(Math.ceil((titleWidth(windowTitle(w.sourceName, w.count)) * 1.7 + 16 + GAPX) / CW), 4, 8);
  const s = boxSize(n, cols, emptyCells);
  w.cols = s.cols; w.w = s.w; w.h = s.h; w.wc = s.wc; w.hc = s.hc;
  w.agents.forEach(function (a, i) {
    a.col = i % cols;
    a.cx = PAD + a.col * (CHIP_W + GAP);
    a.cy = PAD + Math.floor(i / cols) * (CHIP_H + GAP);
  });
}

const WAITING = { waitingForUser: 'waiting for your reply', waitingForQuestion: 'waiting for your answer', waitingForApproval: 'waiting for your approval' };

// The run state in words; `short` for a table cell.
export function stateText(a, short) {
  if (a.closed) return short ? 'closed' : 'workspace closed';
  if (a.stale) return short ? 'not confirmed' : 'not confirmed: saved as ' + (WAITING[a.state] || a.state) + ' before the app last started';
  if (a.run === 'waiting') return WAITING[a.state] || 'waiting';
  if (a.run === 'running') return 'running';
  return short ? a.state : 'idle, last run ' + a.state;
}

// How active an agent is, 1 (quiet) to 4, from what the snapshot says: 4 running or waiting
// for the user (and confirmed), 3 active within 15 minutes, 2 within 3 hours, 1 older or unknown.
// Takes a graph document's raw agent; the link estimate and the redraw key use it too.
export const HEAT_ACTIVE = 15 * 60, HEAT_RECENT = 3 * 3600;   // seconds
export function heatOf(raw, generated) {
  if (raw.stale !== true && (raw.state === 'running' || String(raw.state).indexOf('waitingFor') === 0)) return 4;
  if (typeof raw.last !== 'number' || typeof generated !== 'number') return 1;
  const age = Math.max(0, generated - raw.last);
  return age <= HEAT_ACTIVE ? 3 : age <= HEAT_RECENT ? 2 : 1;
}

// Follow the latest recent event. An instruction lasts longer while its target is working.
export function linkActivity(raw, target, generated) {
  if (!Number.isFinite(generated)) return null;
  let latest = -Infinity, direction = null;
  for (const kind of ['msg', 'watch', 'wake', 'attn']) {
    const at = raw[kind];
    if (Number.isFinite(at) && at > latest && generated - at <= HEAT_ACTIVE) {
      latest = at;
      direction = kind === 'msg' || kind === 'watch' ? 'down' : 'up';
    }
  }
  return direction || (target.heat === 4 && Number.isFinite(raw.msg) && generated - raw.msg <= HEAT_RECENT ? 'down' : null);
}

function windowTitle(name, count) { return name + (count > 1 ? ' ×' + count : ''); }

function groupLetters(n) {
  return (n >= 26 ? groupLetters(Math.floor(n / 26) - 1) : '') + String.fromCharCode(65 + n % 26);
}

function aliases(items, label) {
  return new Map(items.map(item => item.id).sort().map((id, i) => [id, label(i)]));
}

export function layoutName(layout) {
  return app.ui.obfuscate ? 'Layout ' + (app.layouts.indexOf(layout) + 1) : layout.name;
}

export function groupName(group) { return app.ui.obfuscate ? app.model.groupNames.get(group.id) ?? 'Group' : group.name; }

export function buildModel(graph, arr, layout, shared) {
  const obscure = app.ui.obfuscate;
  const windowNames = obscure && aliases(graph.windows, i => 'window ' + String(i + 1).padStart(2, '0'));
  const agentNames = obscure && aliases(graph.agents, i => 'agent ' + (i + 1));
  const groupNames = obscure && aliases(arr.groups, i => 'Group ' + groupLetters(i));
  const allById = new Map(), allWinById = new Map();
  const allWins = graph.windows.map(function (w) {
    const count = w.count || 1;
    const sourceName = String(w.name), name = windowNames ? windowNames.get(w.id) : sourceName;
    const o = { id: w.id, name, sourceName, count, title: windowTitle(name, count),
      workspaceColor: w.color, tab: w.tab || null, session: w.session || null, closed: w.closed === true,
      agents: [], peers: new Map(), px: 0, py: 0 };
    allWinById.set(o.id, o);
    return o;
  });
  const allAgents = [];
  graph.agents.forEach(function (raw) {
    const win = allWinById.get(raw.ws);
    if (!win) return;
    const a = Object.assign({}, raw);
    a.out = []; a.inn = []; a.win = win;
    a.sourceName = String(a.name); a.name = agentNames ? agentNames.get(a.id) : a.sourceName; a.model = String(a.model); a.state = String(a.state); a.cli = String(a.cli);
    // What the app last saved, shown only while it can still be true (the server marks the rest stale).
    a.stale = a.stale === true;
    a.run = a.stale ? null : a.state === 'running' ? 'running' : a.state.indexOf('waitingFor') === 0 ? 'waiting' : null;
    a.needs = a.run === 'waiting';   // needs the user: the one flag the motion, the bar count and its filter read
    a.heat = heatOf(raw, graph.generated);
    a.pct = a.used && a.window ? Math.min(100, a.used / a.window * 100) : null;
    const c = Object.prototype.hasOwnProperty.call(CLI, a.cli) ? CLI[a.cli] : [a.cli, a.cli.slice(0, 2).toUpperCase()];
    a.cliName = c[0]; a.abbr = c[1];
    a.cliClass = a.cli === 'codexExec' ? 'codex' : a.cli === 'claudeCode' ? 'claude' : 'other';
    a.hay = (a.name + ' ' + a.model + ' ' + (a.effort || '') + ' ' + a.cliName + ' ' + win.name + ' ' + (a.stale ? 'unconfirmed' : a.state) + (a.run ? ' active ' + a.run : '') + (a.needs ? ' needs-you' : '') + (a.pinned ? ' pinned' : '')).toLowerCase();
    allById.set(a.id, a);
    win.agents.push(a);
    allAgents.push(a);
  });
  const members = membership(arr.groups);
  const wins = allWins.filter(w => (!w.closed || arr.windows[w.id]) && visible(layout, w.id, members.get(w.id)));
  const winById = new Map(wins.map(w => [w.id, w]));
  const agents = allAgents.filter(a => winById.has(a.win.id));
  const byId = new Map(agents.map(a => [a.id, a]));
  const attention = applyAttention(graph.attention, allAgents, allById, byId, obscure);
  const links = [], overseers = new Set();
  let linkCount = 0;
  graph.links.forEach(function (raw) {
    const l = { src: allById.get(raw.o), dst: allById.get(raw.t) };
    if (!l.src || !l.dst) return;
    l.activity = linkActivity(raw, l.dst, graph.generated);
    linkCount++;
    overseers.add(raw.o);
    if (l.src.win !== l.dst.win) {
      l.src.win.peers.set(l.dst.win, (l.src.win.peers.get(l.dst.win) || 0) + 1);
      l.dst.win.peers.set(l.src.win, (l.dst.win.peers.get(l.src.win) || 0) + 1);
    }
    const src = byId.has(raw.o), dst = byId.has(raw.t);
    if (!src || !dst) {
      if (src) l.src.out_hidden = (l.src.out_hidden || 0) + 1;
      if (dst) l.dst.in_hidden = (l.dst.in_hidden || 0) + 1;
      return;
    }
    l.src.out.push(l); l.dst.inn.push(l);
    links.push(l);
  });
  agents.forEach(function (a) {
    a.wakeText = wakeSummary(a);
    if (a.wakeText) a.hay += ' ' + a.wakeText.toLowerCase();
  });
  allWins.forEach(function (w) {
    // overseers first (busiest first), then agents grouped under their main overseer,
    // agents without links last
    w.agents.forEach(function (a) { a.boss = mainOverseer(a); });
    w.agents.sort(function (a, b) {
      const ra = a.linked ? 0 : a.pinned ? 1 : 2, rb = b.linked ? 0 : b.pinned ? 1 : 2;   // linked, pinned, the rest
      if (ra !== rb) return ra - rb;
      const ao = a.out.length > 0, bo = b.out.length > 0;
      if (ao !== bo) return ao ? -1 : 1;
      const bySource = a.sourceName.localeCompare(b.sourceName) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
      if (ao) return b.out.length - a.out.length || bySource;
      const ka = a.boss ? a.boss.sourceName + a.boss.id : '', kb = b.boss ? b.boss.sourceName + b.boss.id : '';
      return ka.localeCompare(kb) || bySource;
    });
    sizeBox(w, arr, shared);
  });
  return { groupNames, linkCount, overseerCount: overseers.size, allWins, allWinById, allAgents, allById, wins: wins, agents: agents, links: links, byId: byId, winById: winById,
    generated: graph.generated, appRunning: graph.app_running !== false, hidden: graph.hidden || {}, warnings: (graph.warnings || []).map(w => obscure ? w.replace(/^(.*? unreadable for (?:window )?)'.*'\.$/s, '$1•••.') : w), attention: attention };
}
