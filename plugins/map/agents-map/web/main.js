// Start-up and the controls in the bar and on the keyboard.

import { app } from './state.js';
import { $, el, store } from './util.js';
import { fit, fitWindow } from './render.js';
import { boot, canEdit, changeLayout, changed, expireSnoozes, flushViewport, history, rebuild, redraw, refresh, refreshFromServer, relayout, syncArrangement, setCounts, setDark, setHover, setLinks, setLive, setPin, setRecent, setWake, syncThemeColor } from './actions.js';
import { idle } from './server.js';
import { activeQuery, applyFilter, closePopover, groupByName, isActiveQuery, hideTip, initLegend, openAttention, openLayouts, openSaveForm, openSaves, queryKey, renderIndex, renderView, syncTableSelection, toggleTable } from './panels.js';
import { cancelDrag, closeMenu } from './interact.js';

const search = $('search');
const obfuscationKey = 'agents-map.obfuscate.v1';
app.ui.obfuscate = store('local', obfuscationKey) === true;

/* ---------- remembered preferences ---------- */
// Only the theme is cached here for first paint.
const savedTheme = store('local', 'agents-map.theme.v1');
if (savedTheme) document.documentElement.dataset.theme = savedTheme;
syncThemeColor();
app.ui.indexCollapsed = store('local', 'agents-map.index.v2') === true;
app.ui.legendOpen = store('local', 'agents-map.legend.v1') === true;
app.ui.sort = store('session', 'agents-map.sort.v2') || app.ui.sort;
app.ui.pin = store('session', 'agents-map.pin.v2');
search.value = store('session', queryKey()) || '';

/* ---------- bar ---------- */
// Most controls need a drawn map; until the first load succeeds only Refresh and Theme act.
function ready(run) { return function () { if (canEdit()) run(); }; }

const bar = $('bar'), barToggle = $('bar-toggle'), barItems = $('bar-items');
const barKey = 'agents-map.bar.v1';
function renderBar(open) {
  bar.classList.toggle('collapsed', !open);
  barToggle.textContent = open ? '▴' : '▾';
  barToggle.setAttribute('aria-expanded', String(open));
}
renderBar(store('local', barKey) === true);
function setBarOpen(open) {
  closePopover();
  store('local', barKey, open);
  renderBar(open);
  if (app.model && app.ui.view.auto) fit(false, false);
}
barToggle.addEventListener('click', () => setBarOpen(bar.classList.contains('collapsed')));
barItems.addEventListener('focusin', function (e) {
  if (bar.classList.contains('collapsed') &&
      e.target.getBoundingClientRect().bottom > barItems.getBoundingClientRect().bottom + 1) setBarOpen(true);
});

/* ---------- View panel ---------- */
function toggleView(open) {
  const panel = $('view-panel');
  panel.hidden = open === undefined ? !panel.hidden : !open;
  $('btn-view').setAttribute('aria-expanded', String(!panel.hidden));
}
$('btn-view').addEventListener('click', function () { renderView(); toggleView(); });
document.addEventListener('pointerdown', function (e) { if (!e.target.closest('#view')) toggleView(false); }, true);
renderView();
$('opt-obfuscate').addEventListener('change', function () {
  app.ui.obfuscate = $('opt-obfuscate').checked;
  store('local', obfuscationKey, app.ui.obfuscate);
  // A query written for the normal view may itself contain a private name.
  search.value = store('session', queryKey()) || '';
  closePopover();
  if (app.model) rebuild();
  else renderView();
});
$('opt-links').addEventListener('change', ready(function () { setLinks($('opt-links').checked); }));
$('opt-counts').addEventListener('change', ready(function () { setCounts($('opt-counts').checked); }));
$('opt-wake').addEventListener('change', ready(function () { setWake($('opt-wake').checked); }));
$('opt-recent').addEventListener('change', function () { setRecent($('opt-recent').checked); });
$('opt-live').addEventListener('change', function () { setLive($('opt-live').checked); });
window.setInterval(function () { if (app.ui.live && app.model && !document.hidden) refresh(); }, 5000);
window.setInterval(function () { if (!app.ui.live) expireSnoozes(); }, 60000);
$('btn-active').addEventListener('click', ready(function () {
  // Clears its own filter even when the counts have moved on to the other one.
  search.value = isActiveQuery(search.value.trim().toLowerCase()) ? '' : activeQuery();
  applyFilter();
}));
$('opt-dark').addEventListener('change', function () { setDark($('opt-dark').checked); });
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { syncThemeColor(); if (app.model) redraw(); });
$('btn-fit').addEventListener('click', ready(function () { fit(true); }));
$('btn-table').addEventListener('click', ready(function () { toggleTable(); }));
$('btn-layouts').addEventListener('click', ready(() => {
  if ($('popover').dataset.kind === 'layouts') closePopover(true);
  else openLayouts();
}));
$('btn-layout').addEventListener('click', ready(relayout));
$('btn-refresh').addEventListener('click', refreshFromServer);
$('btn-undo').addEventListener('click', function () { history('undo'); });
$('btn-redo').addEventListener('click', function () { history('redo'); });
$('btn-attention').addEventListener('click', ready(function () { if ($('popover').dataset.kind === 'attention') closePopover(); else openAttention($('btn-attention')); }));
$('btn-save').addEventListener('click', ready(function () { if ($('popover').hidden) openSaveForm(); else closePopover(); }));
$('btn-saves').addEventListener('click', ready(function () { if ($('popover').hidden) openSaves(); else closePopover(); }));
$('index-toggle').addEventListener('click', ready(function () {
  app.ui.indexCollapsed = !app.ui.indexCollapsed;
  store('local', 'agents-map.index.v2', app.ui.indexCollapsed);
  renderIndex();
}));
function renderLegend() {
  $('legend').classList.toggle('collapsed', !app.ui.legendOpen);
  $('legend-toggle').textContent = app.ui.legendOpen ? '▴' : '▾';
  $('legend-toggle').setAttribute('aria-expanded', String(app.ui.legendOpen));
}
renderLegend();
$('legend-toggle').addEventListener('click', function () {
  app.ui.legendOpen = !app.ui.legendOpen;
  store('local', 'agents-map.legend.v1', app.ui.legendOpen);
  renderLegend();
  if (app.model && app.ui.view.auto) fit(false, false);   // the map area changed height
});
$('btn-group-prefix').addEventListener('click', ready(groupByName));
search.addEventListener('input', applyFilter);

/* ---------- keyboard ---------- */
document.addEventListener('keydown', function (e) {
  const typing = e.target instanceof HTMLInputElement && e.target.type !== 'checkbox';   // a focused switch still lets keys through
  if (e.key === 'Escape') {
    hideTip();
    if (cancelDrag() || closeMenu()) return;
    if (!$('view-panel').hidden) { toggleView(false); return; }
    if (!$('popover').hidden) { closePopover(true); return; }
    // Escape clears the filter from anywhere, not only while the box has focus.
    if (search.value) { search.value = ''; applyFilter(); }
    if (e.target === search) search.blur();
    if (app.model) { setPin(null); setHover(null); syncTableSelection(); }
    return;
  }
  if (typing) return;
  // Undo only when there is a step to take back (or an unsaved change), redo only when one waits.
  const canUndo = app.undo || app.unsaved, canRedo = app.redo && !app.unsaved;
  if ((e.metaKey || e.ctrlKey) && !e.altKey && (e.key === 'z' || e.key === 'Z')) {
    e.preventDefault();
    if (e.shiftKey ? canRedo : canUndo) history(e.shiftKey ? 'redo' : 'undo');
    return;
  }
  // 1-9 pick the 1st-9th layout, with or without ⌘/Ctrl (Chrome keeps ⌘1-8 for its tabs).
  if (/^[1-9]$/.test(e.key) && !e.altKey && !e.shiftKey) {
    e.preventDefault();
    const layout = app.layouts[+e.key - 1];
    if (layout && layout.id !== app.settings.current) changeLayout('select', {layout_id: layout.id});
    return;
  }
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key === 'r' || e.key === 'R') { refreshFromServer(); return; }
  if (!app.model) return;
  const inTable = e.target instanceof Element && e.target.closest('#table-panel');
  if (e.key === 'ArrowLeft' && !inTable) { e.preventDefault(); if (canUndo) history('undo'); }
  else if (e.key === 'ArrowRight' && !inTable) { e.preventDefault(); if (canRedo) history('redo'); }
  else if (e.key === '/') { e.preventDefault(); search.focus(); search.select(); }
  else if ((e.key === 'f' || e.key === 'F') && canEdit()) fit(true);
  else if (e.key === 't' || e.key === 'T') toggleTable();
  else if (e.key === 'l' || e.key === 'L') setLinks(!app.ui.links);
  else if (e.key === 'w' || e.key === 'W') setWake(!app.ui.wake);
});

window.addEventListener('resize', function () { if (app.model && app.ui.view.auto) fit(false, false); });

async function syncOnFocus() {
  if (!app.model) return;
  flushViewport();
  await idle();
  return syncArrangement();
}
window.addEventListener('focus', syncOnFocus);
document.addEventListener('visibilitychange', () => {
  if (document.hidden) flushViewport();
  else syncOnFocus();
});

/* ---------- go ---------- */
initLegend();
boot().then(function () {
  if (store('session', 'agents-map.table.v2')) toggleTable(true);
}, function (error) {
  const note = el('div', '', app.ui.obfuscate ? 'The map could not load' : 'The map could not load: ' + error.message);
  note.id = 'empty';
  $('stage').appendChild(note);
});

window.agents_map = { app: app, rebuild: rebuild, idle: idle, history: history, changed: changed, changeLayout, fitWindow: fitWindow };   // for the page checks and the console
