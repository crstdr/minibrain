// Colour schemes: a grid of hues (columns) by intensities (rows). A group's hue says
// which group an agent belongs to; the intensity says how active it is (heatFill). One
// scheme is a whole set: a tint for the background, a stronger shade of the same hue for
// the border, and text in whichever of dark or light ink reads better on that tint.
// Pure: no DOM apart from reading which theme is in effect.
//
// The palette has eight categorical hues plus grey, with a step for each theme. These are personal markings, not data: every marked thing keeps its
// own label, so a colour never has to identify anything on its own. The server
// validates a group's hue against these ids (agents_map.py, HUE_IDS): change both together.

export const HUES = [
  ['red', 'Red', '#e34948', '#e66767'], ['orange', 'Orange', '#eb6834', '#d95926'],
  ['yellow', 'Yellow', '#eda100', '#c98500'], ['green', 'Green', '#008300', '#008300'],
  ['aqua', 'Aqua', '#1baf7a', '#199e70'], ['blue', 'Blue', '#2a78d6', '#3987e5'],
  ['violet', 'Violet', '#6250d6', '#9085e9'], ['magenta', 'Pink', '#e87ba4', '#d55181'],
  ['grey', 'Grey', '#7a7974', '#8a8983']
];
// Share of the hue mixed into the theme's surface, lightest row first. Dark tints need
// more of the hue to show against a dark surface.
const LEVELS = { light: [0.10, 0.22, 0.38, 0.62, 1], dark: [0.16, 0.30, 0.48, 0.72, 1] };
export const LEVEL_COUNT = 5;
const SURFACE = { light: '#fcfcfb', dark: '#1a1a19' };
const INKS = ['#000000', '#ffffff'];   // pure ends: on the strongest blue, green and grey only these reach 4.5:1
const FILL_RE = /^([a-z]{3,8})-([1-5])$/;

function rgb(h) { return [1, 3, 5].map(function (i) { return parseInt(h.slice(i, i + 2), 16); }); }
function hex(c) { return '#' + c.map(function (v) { return Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0'); }).join(''); }
export function mix(a, b, t) { const x = rgb(a), y = rgb(b); return hex(x.map(function (v, i) { return v * t + y[i] * (1 - t); })); }
function luminance(h) {
  const c = rgb(h).map(function (v) { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
export function contrast(a, b) {
  const x = luminance(a), y = luminance(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

export function theme() {
  return document.documentElement.dataset.theme || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

export function fillId(hue, level) { return hue + '-' + level; }

// The hue id a group asks for: its hue, else the hue of the fill it had before groups
// took a hue (the fill itself stays in the arrangement), else none.
export function groupHue(g) {
  const known = function (id) { return HUES.some(function (h) { return h[0] === id; }) ? id : null; };
  if (!g) return null;
  if (g.hue) return known(g.hue);
  const m = FILL_RE.exec(g.fill || '');
  return m ? known(m[1]) : null;
}

// Heat 1 (quiet) to 4 (running or waiting) as an intensity row; agents outside a hued group are grey.
const HEAT_LEVEL = [1, 1, 2, 3, 4];
export function heatFill(hue, heat) { return fillId(hue || 'grey', HEAT_LEVEL[heat] || 1); }

// The scheme for a fill id in a theme, or null for an id this page does not know.
export function scheme(id, mode) {
  const m = FILL_RE.exec(id || '');
  const h = m && HUES.filter(function (x) { return x[0] === m[1]; })[0];
  if (!h) return null;
  mode = mode === 'dark' ? 'dark' : 'light';
  const base = h[mode === 'dark' ? 3 : 2], surface = SURFACE[mode], f = LEVELS[mode][Number(m[2]) - 1];
  const bg = mix(base, surface, f);
  const text = contrast(INKS[0], bg) >= contrast(INKS[1], bg) ? INKS[0] : INKS[1];
  let text2 = mix(text, bg, 0.75);   // secondary text, unless that would read too faintly
  if (contrast(text2, bg) < 4.5) text2 = text;
  const strong = Math.min(1, f + 0.55);
  const border = strong < 1 ? mix(base, surface, strong) : mix(base, mode === 'dark' ? '#ffffff' : '#000000', mode === 'dark' ? 0.62 : 0.68);
  return { bg: bg, border: border, text: text, text2: text2, track: mix(text, bg, 0.18) };
}

// Sets (or, for no fill, clears) the scheme on an element; the stylesheet reads these.
export function applyFill(node, id, mode) {
  const s = scheme(id, mode);
  node.classList.toggle('filled', !!s);
  [['--fill-bg', 'bg'], ['--fill-border', 'border'], ['--fill-text', 'text'], ['--fill-text2', 'text2'], ['--fill-track', 'track']]
    .forEach(function (p) { if (s) node.style.setProperty(p[0], s[p[1]]); else node.style.removeProperty(p[0]); });
}
