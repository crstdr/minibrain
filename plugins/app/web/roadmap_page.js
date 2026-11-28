// Standalone roadmap page bootstrap (used by both tasks.py serve and agents_map.py /roadmap/<id>).
import { mountRoadmap } from './roadmap_view.js';

const THEME_KEY = 'agents-map.theme.v1';
const OBFUSCATE_KEY = 'agents-map.obfuscate.v1';

function readPref(key) {
  try { return JSON.parse(localStorage.getItem(key)); }
  catch (e) { return null; }
}

function applyTheme() {
  const saved = readPref(THEME_KEY);
  if (saved === 'dark' || saved === 'light') document.documentElement.dataset.theme = saved;
  else delete document.documentElement.dataset.theme;
}
applyTheme();

const parts = location.pathname.replace(/\/+$/, '').split('/').filter(Boolean);
const urlId = parts[0] === 'roadmap' && parts[1] ? decodeURIComponent(parts[1]) : null;
const params = new URLSearchParams(location.search);
const initialLane = params.get('lane') || null;
const initialNode = params.get('node') || null;

let roadmaps = [];
let collectionsCount = null;
let listFailed = false;
const fromMap = parts[0] === 'roadmap';
if (fromMap) {
  try {
    const r = await fetch('/api/roadmaps', { cache: 'no-store' });
    if (r.ok) {
      const data = await r.json();
      roadmaps = data.roadmaps || [];
      collectionsCount = typeof data.collections === 'number' ? data.collections : null;
    } else listFailed = true;
  } catch (e) {
    listFailed = true;
  }
}

const resolvedId = fromMap
  ? (urlId || (roadmaps.length ? roadmaps[0].id : null))
  : 'default';

const ctrl = mountRoadmap(document.getElementById('rm-page-root'), {
  roadmaps,
  roadmapId: resolvedId,
  collectionsCount,
  listUrl: fromMap ? '/api/roadmaps' : null,
  listFailed,
  lane: initialLane,
  nodeId: initialNode,
  obfuscate: readPref(OBFUSCATE_KEY) === true,
  standalone: true,
  apiBase: '/api/roadmap',
  apiUrl: fromMap ? null : '/api/roadmap',
  mapHref: fromMap ? '/' : null,
  onSwitchRoadmap(id) {
    if (fromMap) window.history.replaceState(null, '', '/roadmap/' + encodeURIComponent(id));
  },
});

window.addEventListener('storage', e => {
  if (e.key === OBFUSCATE_KEY || e.key === null) ctrl.setObfuscate(readPref(OBFUSCATE_KEY) === true);
  if (e.key === THEME_KEY || e.key === null) applyTheme();
});

window.setInterval(() => { if (!document.hidden) ctrl.refresh(); }, 5000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) ctrl.refresh(); });
