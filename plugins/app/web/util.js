// Small helpers shared by every module. No state.

const SVGNS = 'http://www.w3.org/2000/svg';

export function $(id) { return document.getElementById(id); }

// Every name on the map is untrusted text: nodes are built here and text goes in as textContent only.
export function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

export function svg(tag, attrs) {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  return e;
}

// store('local'|'session', key) reads; with a value it writes; null removes.
export function store(kind, key, value) {
  try {
    const s = kind === 'local' ? window.localStorage : window.sessionStorage;
    if (value === undefined) { const raw = s.getItem(key); return raw ? JSON.parse(raw) : null; }
    if (value === null) s.removeItem(key); else s.setItem(key, JSON.stringify(value));
  } catch (e) { /* storage unavailable: the map still works, it just forgets */ }
  return null;
}

export function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

export function fmtTokens(n) {
  if (n == null) return '';
  if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M';
  if (n >= 1000) return Math.round(n / 1000) + 'k';
  return String(n);
}

export function ago(sec, short) {
  if (!sec) return short ? '–' : 'unknown';
  const d = Math.max(0, Date.now() / 1000 - sec);
  const tail = short ? '' : ' ago';
  if (d < 90) return short ? 'now' : 'just now';
  if (d < 3600) return Math.round(d / 60) + ' min' + tail;
  if (d < 172800) return Math.round(d / 3600) + ' h' + tail;
  return Math.round(d / 86400) + ' d' + tail;
}

// A name the user typed, as the server will keep it: no control or format characters,
// single spaces, at most 80 characters. Empty means the name is refused.
export function cleanName(text) {
  return String(text).replace(/[\p{C}\p{Zl}\p{Zp}]/gu, '').replace(/\s+/g, ' ').trim().slice(0, 80).trim();
}

export function plural(n, one, many) { return n + ' ' + (n === 1 ? one : many); }

export function byName(a, b) { return a.name.localeCompare(b.name) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0); }
