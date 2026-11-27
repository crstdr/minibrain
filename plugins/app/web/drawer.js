// Agents Map Variant B split-drawer controller: mounts the shared roadmap_view.js beside #stage.

import { app } from './state.js';
import { $, clamp, store } from './util.js';
import { fit, fitWindow, centerOn } from './render.js';
import { rebuild, setPin } from './actions.js';
import { hideTip, syncTableSelection } from './panels.js';

const WIDTH_KEY = 'agents-map.drawer-width.v1';
const PRESETS = [25, 50, 90];
const drawer = $('roadmap-drawer');
const resizer = $('split-resizer');
const tabBtn = $('roadmap-tab');
let controller = null;
let mountModule = null;
let collapsed = false;
let activePreset = null;
let customWidth = null;

function loadWidthPref() {
  const saved = store('local', WIDTH_KEY);
  if (saved && typeof saved === 'object' && PRESETS.includes(saved.preset)) {
    activePreset = saved.preset;
    customWidth = null;
  } else if (typeof saved === 'number' && Number.isFinite(saved)) {
    activePreset = null;
    customWidth = saved;
  } else {
    activePreset = 50;
    customWidth = null;
  }
}
loadWidthPref();

function applyWidth(px) {
  const workspace = $('workspace');
  if (!workspace || !drawer) return;
  const ws = workspace.clientWidth || window.innerWidth;
  const minW = Math.min(260, Math.max(200, Math.floor(ws * 0.25)));
  const maxW = Math.max(minW, Math.floor(ws * 0.92));
  const clamped = clamp(px, minW, maxW);
  drawer.style.width = clamped + 'px';
  return clamped;
}

function applySavedWidth() {
  const workspace = $('workspace');
  const ws = workspace ? workspace.clientWidth : window.innerWidth;
  if (activePreset) return applyWidth(Math.round(ws * (activePreset / 100)));
  return applyWidth(customWidth || Math.round(ws * 0.5));
}

function updateTabLabel() {
  if (!tabBtn) return;
  const label = tabBtn.querySelector('.rm-tab-label');
  if (!label) return;
  const cur = controller?.current();
  const title = !app.ui.obfuscate && cur?.title ? cur.title : 'Roadmap';
  label.textContent = title;
  tabBtn.title = title;
}

export function isDrawerOpen() {
  return !!(drawer && !drawer.hidden && !collapsed);
}

export function setDrawerPreset(pct) {
  if (!PRESETS.includes(pct) || !drawer) return;
  activePreset = pct;
  customWidth = null;
  store('local', WIDTH_KEY, { preset: pct });
  if (collapsed) expandRoadmapDrawer();
  applySavedWidth();
  if (controller) {
    controller.setActivePreset(pct);
    controller.setAsideCollapsed(pct <= 25, true);
    requestAnimationFrame(() => controller && controller.fit());
  }
  if (app.model && app.ui.view.auto) requestAnimationFrame(() => fit(false, false));
}

export function collapseRoadmapDrawer() {
  if (!drawer || drawer.hidden || !controller) return false;
  collapsed = true;
  drawer.hidden = true;
  if (resizer) resizer.hidden = true;
  updateTabLabel();
  if (tabBtn) tabBtn.hidden = false;
  if (app.model && app.ui.view.auto) requestAnimationFrame(() => fit(false, false));
  return true;
}

export function expandRoadmapDrawer() {
  if (!drawer || !controller || !collapsed) return false;
  collapsed = false;
  if (tabBtn) tabBtn.hidden = true;
  drawer.hidden = false;
  if (resizer) resizer.hidden = false;
  applySavedWidth();
  controller.refresh(app.model?.roadmaps || []);
  requestAnimationFrame(() => {
    if (controller) controller.fit();
    if (app.model && app.ui.view.auto) fit(false, false);
  });
  return true;
}

export async function openRoadmapDrawer(roadmapId, lane = null, nodeId = null) {
  if (!drawer) return;
  hideTip();
  if (!mountModule) mountModule = await import('./roadmap_view.js');
  const roadmaps = app.model?.roadmaps || [];
  const targetId = roadmapId || roadmaps[0]?.id;
  if (!targetId) return;
  const wasHidden = drawer.hidden;
  collapsed = false;
  if (tabBtn) tabBtn.hidden = true;
  drawer.hidden = false;
  if (resizer) resizer.hidden = false;
  const width = applySavedWidth();
  const narrow = activePreset ? activePreset <= 25 : (width < 520);
  if (!controller) {
    controller = mountModule.mountRoadmap(drawer, {
      roadmaps,
      roadmapId: targetId,
      lane,
      nodeId,
      obfuscate: app.ui.obfuscate,
      standalone: false,
      apiBase: '/api/roadmap',
      sizePresets: PRESETS,
      activePreset,
      asideCollapsed: narrow,
      onSizePreset: setDrawerPreset,
      onCollapse: collapseRoadmapDrawer,
      onClose: closeRoadmapDrawer,
      onSelectNode(node, doc) {
        if (!node || !app.model) return;
        const targetLane = node.lane || doc.lane;
        const sid = (doc.node_agents && doc.node_agents[node.id])
          || (doc.lanes && targetLane ? doc.lanes[targetLane] : null);
        if (sid && app.model.byId.has(sid)) {
          setPin({ kind: 'agent', id: sid });
          syncTableSelection();
        }
      },
      onShowAgent(sid) {
        if (!app.model || !app.model.byId.has(sid)) return;
        const a = app.model.byId.get(sid);
        setPin({ kind: 'agent', id: sid });
        syncTableSelection();
        centerOn(a);
      },
      onSeenChange() {
        if (app.model) rebuild();
      },
    });
  } else {
    controller.load(targetId, lane, nodeId, roadmaps);
    if (wasHidden) requestAnimationFrame(() => controller && controller.fit());
  }
  if (wasHidden && app.model && app.ui.view.auto) requestAnimationFrame(() => fit(false, false));
}

export function closeRoadmapDrawer() {
  if (!drawer || (drawer.hidden && !collapsed)) return false;
  collapsed = false;
  drawer.hidden = true;
  if (resizer) resizer.hidden = true;
  if (tabBtn) tabBtn.hidden = true;
  if (controller) { controller.destroy(); controller = null; }
  if (app.model && app.ui.view.auto) requestAnimationFrame(() => fit(false, false));
  return true;
}

export function syncDrawerWithAgent(agent) {
  if (!isDrawerOpen() || !agent || !agent.roadmaps || !agent.roadmaps.length) return false;
  const curId = controller?.current()?.roadmapId;
  const match = agent.roadmaps.find(r => r.id === curId) || agent.roadmaps[0];
  openRoadmapDrawer(match.id, match.mode === 'owner' ? null : match.lane, null);
  return true;
}

export function refreshDrawer() {
  if (!controller) return;
  const roadmaps = app.model?.roadmaps || [];
  if (!roadmaps.length) { closeRoadmapDrawer(); return; }
  if (isDrawerOpen()) controller.refresh(roadmaps);
  else if (collapsed) updateTabLabel();
}

export function syncDrawerObfuscate() {
  if (controller) controller.setObfuscate(app.ui.obfuscate);
  if (collapsed) updateTabLabel();
}

window.addEventListener('agents-map-rebuilt', refreshDrawer);
window.addEventListener('resize', () => {
  if (isDrawerOpen() && activePreset) {
    applySavedWidth();
    if (controller) controller.fit();
  }
});
if (tabBtn) tabBtn.addEventListener('click', expandRoadmapDrawer);

// Draggable vertical divider
if (resizer) {
  let dragging = null;
  resizer.addEventListener('pointerdown', e => {
    if (e.button !== 0 || drawer.hidden) return;
    dragging = { startX: e.clientX, startW: drawer.offsetWidth };
    resizer.setPointerCapture(e.pointerId);
    resizer.classList.add('dragging');
  });
  resizer.addEventListener('pointermove', e => {
    if (!dragging) return;
    const width = applyWidth(dragging.startW + (dragging.startX - e.clientX));
    activePreset = null;
    customWidth = width;
    store('local', WIDTH_KEY, width);
    if (controller) {
      controller.setActivePreset(null);
      controller.fit();
    }
  });
  const end = () => {
    if (!dragging) return;
    dragging = null;
    resizer.classList.remove('dragging');
    if (app.model && app.ui.view.auto) fit(false, false);
  };
  resizer.addEventListener('pointerup', end);
  resizer.addEventListener('pointercancel', end);
}
