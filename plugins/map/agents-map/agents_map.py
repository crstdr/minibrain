#!/usr/bin/env python3
"""Agents Map: a live map of your agents and how they are linked, served on this machine.

Starts a small server on 127.0.0.1 and opens the map in the browser. The page asks
the server for fresh data (Refresh) and stores what you arrange by hand: positions,
groups, link settings, View settings, undo history and named saves.

The data comes from a source module (sources/repoprompt.py reads RepoPrompt CE's saved
state, read-only). What the page receives holds names, models and usage numbers, never
transcripts or paths. With --attention FILE it also carries the items another program
lists there as needing you (attention.py describes the file).

What you arrange is kept in ~/Library/Application Support/agents-map (--state-dir),
never in a source's own folder.

Usage:
  python3 agents_map.py              start the server and open the map
  python3 agents_map.py --no-open    start the server only
  python3 agents_map.py --demo       show sample data without RepoPrompt CE
  python3 agents_map.py --json       print one collection and exit
  python3 agents_map.py --attention FILE   also show the attention items in FILE
"""
import argparse
import glob
import json
import os
import re
import signal
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from contextlib import nullcontext
from copy import deepcopy
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import attention
from sources import demo, repoprompt

STATE_DIR = os.path.expanduser("~/Library/Application Support/agents-map")
HERE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(HERE, "web")
DEFAULT_PORT = 47613  # fixed, so the page keeps one origin (browser settings stick to it)
GRID = [60, 31]  # cell size in page pixels; an arrangement stores positions in cells
HISTORY_LIMIT = 50
MAX_BODY = 1 << 20


# ---------------------------------------------------------------- arrangement store

def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


ID_RE = re.compile(r"^[0-9A-Z][0-9A-Z-]{0,79}$")  # the collector upper-cases every id
GROUP_ID_RE = re.compile(r"^g[0-9a-z]{4,12}$")
SAVE_ID_RE = re.compile(r"^s[0-9a-f]{8,20}$")
SLOT_RE = re.compile(r"^[a-z][a-z0-9]{0,7}$")
FILL_RE = re.compile(r"^[a-z]{3,8}-[1-9]$")  # background colour: hue-intensity, e.g. "blue-3"
HUE_IDS = ("red", "orange", "yellow", "green", "aqua", "blue", "violet", "magenta", "grey")  # as web/colors.js HUES
VIEW_SWITCHES = ("links", "counts", "wake", "recent", "live")  # the View panel's switches


class Invalid(ValueError):
    """An arrangement or request field that fails validation; the text names the field."""


class Conflict(Exception):
    """The caller's base revision is not the current one."""


def _integer(value, low, high, field):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise Invalid(field)
    return value


def _fill(raw, item, field):
    fill = raw.get("fill")
    if fill is not None:
        if not isinstance(fill, str) or not FILL_RE.match(fill):
            raise Invalid(field + ".fill")
        item["fill"] = fill


def _links(raw, item, field):
    """"show" or "hide": the item's links regardless of the page's Links button. Absent: follow it.
    The older "hide": true means "hide"."""
    links = raw.get("links")
    if links is None and raw.get("hide") is True:
        links = "hide"
    if links is not None:
        if links not in ("show", "hide"):
            raise Invalid(field + ".links")
        item["links"] = links


def _link_settings(raw, item, field):
    """Per-item settings: links shown or hidden, link colour, background colour."""
    _links(raw, item, field)
    color = raw.get("color")
    if color is not None:
        if not isinstance(color, str) or not SLOT_RE.match(color):
            raise Invalid(field + ".color")
        item["color"] = color
    _fill(raw, item, field)


def _text(value, limit, field):
    if not isinstance(value, str):
        raise Invalid(field)
    value = "".join(ch for ch in value if ch.isprintable()).strip()
    if not 1 <= len(value) <= limit:
        raise Invalid(field)
    return value


def clean_arrangement(raw):
    """Validated copy of an arrangement; raises Invalid naming the first bad field."""
    if not isinstance(raw, dict):
        raise Invalid("arrangement")
    if raw.get("grid") != GRID:
        raise Invalid("grid")
    windows, agents, groups = raw.get("windows", {}), raw.get("agents", {}), raw.get("groups", [])
    if not isinstance(windows, dict) or not isinstance(agents, dict) or len(windows) + len(agents) > 5000:
        raise Invalid("windows")
    if not isinstance(groups, list) or len(groups) > 200:
        raise Invalid("groups")
    out = {"grid": list(GRID), "windows": {}, "agents": {}, "groups": []}
    for wid, value in windows.items():
        if not ID_RE.match(wid) or not isinstance(value, dict):
            raise Invalid("windows")
        item = {}
        if "x" in value or "y" in value:
            item = {coord: _integer(value.get(coord), -100000, 100000, "windows." + coord) for coord in ("x", "y")}
        if value.get("cols") is not None:
            item["cols"] = _integer(value["cols"], 1, 6, "windows.cols")
            if value.get("fixed") is True:  # columns chosen by the user, not by agent count
                item["fixed"] = True
        _link_settings(value, item, "windows")
        out["windows"][wid] = item
    for sid, value in agents.items():
        if not ID_RE.match(sid) or not isinstance(value, dict):
            raise Invalid("agents")
        item = {}
        _link_settings(value, item, "agents")
        if item:
            out["agents"][sid] = item
    taken, group_ids = set(), set()
    for value in groups:
        if not isinstance(value, dict):
            raise Invalid("groups")
        gid, members = value.get("id"), value.get("members")
        if not isinstance(gid, str) or not GROUP_ID_RE.match(gid) or gid in group_ids:
            raise Invalid("groups.id")
        if not isinstance(members, list) or len(members) > 1000:
            raise Invalid("groups.members")
        for wid in members:
            if not isinstance(wid, str) or not ID_RE.match(wid) or wid in taken:
                raise Invalid("groups.members")
            taken.add(wid)
        group_ids.add(gid)
        group = {"id": gid, "name": _text(value.get("name"), 80, "groups.name"), "members": list(members)}
        _links(value, group, "groups")
        _fill(value, group, "groups")   # the older way to colour a group: kept; the page reads its hue until the group is given one
        if value.get("hue") is not None:
            if value["hue"] not in HUE_IDS:
                raise Invalid("groups.hue")
            group["hue"] = value["hue"]
        out["groups"].append(group)
    view = raw.get("view")
    if view is not None:   # the View panel's settings; absent ones take the page's defaults
        if not isinstance(view, dict):
            raise Invalid("view")
        out["view"] = {}
        for key in VIEW_SWITCHES:
            if key in view:
                if not isinstance(view[key], bool):
                    raise Invalid("view." + key)
                out["view"][key] = view[key]
        if view.get("theme") is not None:
            if view["theme"] not in ("light", "dark"):
                raise Invalid("view.theme")
            out["view"]["theme"] = view["theme"]
    return out


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, path)


LAYOUT_ID_RE = re.compile(r"main|l[0-9a-f]{12}")
CELL_LIMIT = 1_000_000
SWITCH_DEFAULTS = {"links": True, "counts": False, "wake": False, "recent": True}
SETTINGS_DEFAULTS = {"current": "main", "live": True, "theme": None}
LINK_KINDS = {"agents": ID_RE, "windows": ID_RE, "groups": GROUP_ID_RE}


def _fields(raw, allowed, field, required=()):
    if not isinstance(raw, dict) or raw.keys() - set(allowed) or set(required) - raw.keys():
        raise Invalid(field)
    return raw


def _id(value, pattern, field):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise Invalid(field)
    return value


def _bool(value, field):
    if not isinstance(value, bool):
        raise Invalid(field)
    return value


def _choice(value, choices, field):
    if value not in choices:
        raise Invalid(field)
    return value


def _pair(raw, keys, limit, field):
    _fields(raw, keys, field, keys)
    return {key: _integer(raw[key], -limit, limit, field + "." + key) for key in keys}


def _options(raw, patterns, field):
    return {key: _id(raw[key], pattern, field + "." + key)
            for key, pattern in patterns.items() if key in raw}


def clean_save(raw):
    """Shared structure only; layout-owned fields are errors."""
    _fields(raw, ("grid", "windows", "agents", "groups"), "save", ("grid",))
    if raw["grid"] != GRID:
        raise Invalid("grid")
    windows, agents, groups = raw.get("windows", {}), raw.get("agents", {}), raw.get("groups", [])
    if not isinstance(windows, dict) or not isinstance(agents, dict) or len(windows) + len(agents) > 5000:
        raise Invalid("windows/agents")
    if not isinstance(groups, list) or len(groups) > 200:
        raise Invalid("groups")
    taken, group_ids, clean_groups = set(), set(), []
    for group in groups:
        _fields(group, ("id", "name", "members", "hue", "fill"), "groups", ("id", "name", "members"))
        gid = _id(group["id"], GROUP_ID_RE, "groups.id")
        members = group["members"]
        if gid in group_ids or not isinstance(members, list) or len(members) > 1000:
            raise Invalid("groups")
        group_ids.add(gid)
        for member in members:
            _id(member, ID_RE, "groups.members")
            if member in taken:
                raise Invalid("groups.members")
            taken.add(member)
        item = dict(_options(group, {"fill": FILL_RE}, "groups"),
                    id=gid, name=_text(group["name"], 80, "groups.name"), members=list(members))
        if "hue" in group:
            item["hue"] = _choice(group["hue"], HUE_IDS, "groups.hue")
        clean_groups.append(item)

    options = {"color": SLOT_RE, "fill": FILL_RE}
    clean_windows, clean_agents = {}, {}
    for wid, raw_item in windows.items():
        _id(wid, ID_RE, "windows")
        _fields(raw_item, ("dx", "dy", "cols", "fixed", *options), "windows")
        item = _options(raw_item, options, "windows")
        if "cols" in raw_item:
            item["cols"] = _integer(raw_item["cols"], 1, 6, "windows.cols")
        if "fixed" in raw_item:
            if "cols" not in item:
                raise Invalid("windows.fixed")
            item["fixed"] = _bool(raw_item["fixed"], "windows.fixed")
        offsets = {key: raw_item[key] for key in ("dx", "dy") if key in raw_item}
        if offsets:
            if wid not in taken:
                raise Invalid("windows offsets")
            item.update(_pair(offsets, ("dx", "dy"), 2 * CELL_LIMIT, "windows"))
        clean_windows[wid] = item
    for aid, item in agents.items():
        _id(aid, ID_RE, "agents")
        _fields(item, options, "agents")
        clean_item = _options(item, options, "agents")
        if clean_item:
            clean_agents[aid] = clean_item
    return {"grid": list(GRID), "windows": clean_windows, "agents": clean_agents, "groups": clean_groups}


def _positions(raw, pattern, field):
    if not isinstance(raw, dict):
        raise Invalid(field)
    return {_id(key, pattern, field): _pair(value, ("x", "y"), CELL_LIMIT, field)
            for key, value in raw.items()}


def _viewport(raw):
    keys = ("k", "tx", "ty", "auto")
    _fields(raw, keys, "viewport", keys)
    for key, low, high in (("k", .12, 2.6), ("tx", -1e9, 1e9), ("ty", -1e9, 1e9)):
        value = raw[key]
        if type(value) not in (int, float) or not low <= value <= high:
            raise Invalid("viewport." + key)
    _bool(raw["auto"], "viewport.auto")
    return dict(raw)


def _layout_patch(raw, stored=False):
    keys = ("groups", "windows", "hidden", "viewport", "switches", "links")
    _fields(raw, keys, "patch", keys if stored else ())
    out = {}
    for kind in ("groups", "windows"):
        if kind in raw:
            out[kind] = _positions(raw[kind], LINK_KINDS[kind], kind)
    if "hidden" in raw:
        out["hidden"] = {}
        if not isinstance(raw["hidden"], dict):
            raise Invalid("hidden")
        for key, value in raw["hidden"].items():
            if not (ID_RE.fullmatch(key) or GROUP_ID_RE.fullmatch(key)):
                raise Invalid("hidden")
            out["hidden"][key] = _bool(value, "hidden")
    if "viewport" in raw:
        # Null is the initial value and can also appear in a full Retry snapshot.
        out["viewport"] = None if raw["viewport"] is None else _viewport(raw["viewport"])
    if "switches" in raw:
        switches = _fields(raw["switches"], SWITCH_DEFAULTS, "switches", SWITCH_DEFAULTS if stored else ())
        out["switches"] = {key: _bool(value, "switches." + key) for key, value in switches.items()}
    if "links" in raw:
        links = _fields(raw["links"], LINK_KINDS, "links", LINK_KINDS if stored else ())
        choices = ("show", "hide") if stored else ("show", "hide", None)
        out["links"] = {}
        for kind, values in links.items():
            if not isinstance(values, dict):
                raise Invalid("links." + kind)
            out["links"][kind] = {_id(key, LINK_KINDS[kind], "links"): _choice(value, choices, "links")
                                  for key, value in values.items()}
    return out


def _settings_patch(raw):
    _fields(raw, ("live", "theme"), "settings")
    if "live" in raw:
        _bool(raw["live"], "live")
    if "theme" in raw:
        _choice(raw["theme"], (None, "light", "dark"), "theme")
    return dict(raw)


def _main_layout():
    return {"id": "main", "name": "Main", "groups": {}, "windows": {}, "hidden": {},
            "viewport": None, "switches": dict(SWITCH_DEFAULTS), "links": {kind: {} for kind in LINK_KINDS}}


def _legacy_parts(raw):
    arrangement = clean_arrangement(raw)
    main = _main_layout()
    view = arrangement.get("view", {})
    main["switches"].update({key: view[key] for key in SWITCH_DEFAULTS if key in view})
    settings = dict(SETTINGS_DEFAULTS)
    settings.update(_settings_patch({key: view[key] for key in ("live", "theme") if key in view}))

    windows, agents, groups = arrangement["windows"], arrangement["agents"], arrangement["groups"]
    for kind, items in (("windows", windows.items()), ("agents", agents.items()),
                        ("groups", ((group["id"], group) for group in groups))):
        for key, item in items:
            if "links" in item:
                main["links"][kind][key] = item.pop("links")
    for wid, item in windows.items():
        if "x" in item:
            main["windows"][wid] = {coord: item.pop(coord) for coord in ("x", "y")}
    for group in groups:
        positioned = [wid for wid in group["members"] if wid in main["windows"]]
        if positioned:
            origin = {coord: min(main["windows"][wid][coord] for wid in positioned) for coord in ("x", "y")}
            main["groups"][group["id"]] = origin
            for wid in positioned:
                windows[wid].update({"d" + coord: main["windows"][wid][coord] - origin[coord] for coord in origin})
    return clean_save({"grid": GRID, "windows": windows, "agents": agents, "groups": groups}), main, settings


def _revision(raw):
    if type(raw) is not int or raw < 0:
        raise Invalid("base_rev/rev")
    return raw


def _history_parts(raw, version):
    if not isinstance(raw, dict) or type(raw.get("version")) is not int or raw["version"] != version:
        raise Invalid("version")
    entries = raw.get("entries")
    if not isinstance(entries, list) or len(entries) > HISTORY_LIMIT:
        raise Invalid("entries")
    cursor = _integer(raw.get("cursor"), 0 if entries else -1, len(entries) - 1, "cursor")
    return _revision(raw.get("rev")), cursor, entries


def _entry_meta(entry):
    if not isinstance(entry, dict) or type(entry.get("t")) is not int:
        raise Invalid("entry timestamp")
    _text(entry.get("label"), 120, "label")
    return {"t": entry["t"], "label": entry["label"]}


def _migrate(raw):
    rev, cursor, entries = _history_parts(raw, 1)
    converted, main, settings = [], _main_layout(), dict(SETTINGS_DEFAULTS)
    for index, entry in enumerate(entries):
        meta = _entry_meta(entry)
        save, layout, prefs = _legacy_parts(entry["arrangement"])
        converted.append(dict(meta, save=save))
        if index == cursor:
            main, settings = layout, prefs
    return {"version": 2, "rev": rev, "cursor": cursor, "entries": converted,
            "layouts": [main], "settings": settings}


def _load_v2(raw):
    rev, cursor, entries = _history_parts(raw, 2)
    _fields(raw, ("version", "rev", "cursor", "entries", "layouts", "settings"), "state")
    history = []
    for entry in entries:
        _fields(entry, ("t", "label", "save"), "entry")
        history.append(dict(_entry_meta(entry), save=clean_save(entry.get("save"))))
    layouts, ids = [], set()
    if not isinstance(raw.get("layouts"), list) or not 1 <= len(raw["layouts"]) <= 20:
        raise Invalid("layouts")
    for record in raw["layouts"]:
        if not isinstance(record, dict):
            raise Invalid("layouts")
        lid = _id(record.get("id"), LAYOUT_ID_RE, "layouts.id")
        if lid in ids or (not layouts and lid != "main"):
            raise Invalid("layouts.id")
        ids.add(lid)
        patch = _layout_patch({key: val for key, val in record.items() if key not in ("id", "name")}, stored=True)
        layouts.append(dict(patch, id=lid, name=_text(record.get("name"), 80, "name")))
    prefs = _fields(raw.get("settings"), SETTINGS_DEFAULTS, "settings", SETTINGS_DEFAULTS)
    current = _id(prefs["current"], LAYOUT_ID_RE, "settings.current")
    if current not in ids:
        raise Invalid("settings.current")
    return {"version": 2, "rev": rev, "cursor": cursor, "entries": history, "layouts": layouts,
            "settings": dict(_settings_patch({key: prefs[key] for key in ("live", "theme")}), current=current)}


def _membership(save):
    return {wid: group["id"] for group in save["groups"] for wid in group["members"]}


def _effective(save, membership, layout, wid):
    gid = membership.get(wid)
    if gid is None:
        return layout["windows"].get(wid)
    anchor, window = layout["groups"].get(gid), save["windows"].get(wid, {})
    if anchor is not None and "dx" in window:
        return {coord: anchor[coord] + window["d" + coord] for coord in ("x", "y")}
    return None


def _derived_slot(point):
    # A composed position can exceed the stored slot limits. Keep the candidate reloadable.
    return {key: max(-CELL_LIMIT, min(CELL_LIMIT, value)) for key, value in point.items()}


def reconcile(before, after, layouts, initiating_id, mode, seeds, *, history_step=False):
    before = before or {"windows": {}, "groups": []}
    old_members, new_members = _membership(before), _membership(after)
    old_groups = {g["id"]: g["members"] for g in before["groups"]}
    detached = old_members.keys() - new_members.keys()
    main = layouts[0]
    initiating = next(layout for layout in layouts if layout["id"] == initiating_id)
    group_seeds, window_seeds, discovery = (seeds.get(key, {}) for key in ("groups", "windows", "main_windows"))
    changed_groups = {g["id"] for g in after["groups"] if old_groups.get(g["id"]) != g["members"]}
    standalone = after["windows"].keys() - new_members.keys()
    known = after["windows"].keys() | new_members.keys()
    if (group_seeds.keys() - changed_groups
            or group_seeds.keys() & old_groups.keys() & initiating["groups"].keys()
            or window_seeds.keys() - (detached | (standalone - initiating["windows"].keys()))
            or discovery.keys() - (known - main["windows"].keys())):
        raise Invalid("seeds")

    ordered = [initiating] + [layout for layout in layouts if layout is not initiating]
    for layout in ordered:
        primary = layout is initiating
        # Read former geometry and visibility before making any changes in this layout.
        positions = {wid: _effective(before, old_members, layout, wid) for wid in known | detached}
        hidden = dict(layout["hidden"])
        for group in after["groups"]:
            gid, members = group["id"], group["members"]
            if primary and gid in group_seeds:
                layout["groups"][gid] = group_seeds[gid]
            if gid not in layout["groups"]:
                anchor = next(({coord: positions[wid][coord] - after["windows"][wid]["d" + coord]
                                for coord in ("x", "y")}
                               for wid in members if positions[wid] is not None
                               and "dx" in after["windows"].get(wid, {})), None)
                layout["groups"][gid] = _derived_slot(
                    anchor if anchor is not None else initiating["groups"].get(gid, {"x": 0, "y": 0}))
            if mode == "edit" and gid not in old_groups and primary:
                layout["hidden"][gid] = False
            else:
                contributors = [old_members.get(wid, wid) for wid in members
                                if wid in old_members or wid in before["windows"]
                                or positions[wid] is not None or wid in hidden]
                layout["hidden"].setdefault(gid, bool(contributors) and all(hidden.get(key, False) for key in contributors))

        for wid in detached:
            if history_step and wid not in known and wid not in layout["windows"]:
                continue
            if mode == "edit":
                if positions[wid] is not None:
                    layout["windows"][wid] = _derived_slot(positions[wid])
                layout["hidden"][wid] = not primary
            else:
                if positions[wid] is not None:
                    layout["windows"].setdefault(wid, _derived_slot(positions[wid]))
                layout["hidden"].setdefault(wid, hidden.get(old_members[wid], layout is not main))
        if mode == "restore":
            for wid in standalone - detached:
                layout["hidden"].setdefault(wid, layout is not main)
        for wid, point in discovery.items():
            layout["windows"].setdefault(wid, point)
            layout["hidden"].setdefault(wid, layout is not main)
        if primary:
            layout["windows"].update(window_seeds)


class Store:
    """Atomic shared history, layout catalogue and settings; named saves stay separate."""

    def __init__(self, state_dir, forbidden=()):
        self.dir = os.path.realpath(os.path.expanduser(state_dir))
        for parent in forbidden:
            parent = os.path.realpath(parent)
            if self.dir == parent or self.dir.startswith(parent + os.sep):
                raise SystemExit("state folder must not be inside " + parent)
        self.saves_dir = os.path.join(self.dir, "saves")
        self.path = os.path.join(self.dir, "state.v2.json")
        self.lock = threading.Lock()
        os.makedirs(self.saves_dir, exist_ok=True)
        if os.path.lexists(self.path):
            self.history = self._read_state(self.path, _load_v2)
        else:
            legacy = os.path.join(self.dir, "history.json")
            empty = {"version": 1, "rev": 0, "cursor": -1, "entries": []}
            candidate = self._read_state(legacy, _migrate) if os.path.lexists(legacy) else _migrate(empty)
            self._publish(candidate)

    @staticmethod
    def _read_state(path, convert):
        try:
            return convert(load_json(path))
        except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
            raise SystemExit("%s unreadable or invalid: %s" % (os.path.basename(path), error)) from None

    @staticmethod
    def _save(doc):
        cursor = doc["cursor"]
        return doc["entries"][cursor]["save"] if cursor >= 0 else None

    def _state(self, full=True):
        hist = self.history
        entries, cursor = hist["entries"], hist["cursor"]
        state = {
            "rev": hist["rev"],
            "undo": entries[cursor]["label"] if cursor > 0 else None,
            "redo": entries[cursor + 1]["label"] if cursor + 1 < len(entries) else None,
        }
        if full:
            state.update(version=2, save=self._save(hist), layouts=hist["layouts"], settings=hist["settings"])
        return state

    def _expect(self, base_rev):
        if base_rev != self.history["rev"]:
            raise Conflict()

    def _publish(self, candidate):
        write_json(self.path, candidate)
        self.history = candidate

    def current(self):
        with self.lock:
            return self._state()

    def known_windows(self):
        state = self.current()
        save = state["save"] or {}
        ids = set(save.get("windows", {}))
        for group in save.get("groups", ()):
            ids.update(group["members"])
        for layout in state["layouts"]:
            ids.update(layout["windows"])
        return ids

    def put(self, data):
        op = data.get("op")
        base_rev = None
        if op == "save":
            _fields(data, ("op", "base_rev", "layout_id", "save", "label", "amend", "mode", "seeds"), "save request")
            save = clean_save(data.get("save"))
            label = _text(data.get("label"), 120, "label")
            mode = _choice(data.get("mode"), ("edit", "restore"), "mode")
            amend = _bool(data.get("amend", False), "amend")
            if mode == "restore" and data.get("amend") is not False:
                raise Invalid("restore requires amend:false")
            base_rev = _revision(data.get("base_rev"))
            raw_seeds = _fields(data.get("seeds", {}), ("groups", "windows", "main_windows"), "seeds")
            seeds = {key: _positions(val, GROUP_ID_RE if key == "groups" else ID_RE, "seeds." + key)
                     for key, val in raw_seeds.items()}
            if (mode == "restore" and any(seeds.values())) or (seeds.get("main_windows") and not amend):
                raise Invalid("seeds")
        elif op == "forget":
            _fields(data, ("op", "base_rev", "window_id", "label"), "forget request")
            wid = _id(data.get("window_id"), ID_RE, "window id")
            label = _text(data.get("label"), 120, "label")
            base_rev = _revision(data.get("base_rev"))
            amend = False
        elif op == "layout":
            _fields(data, ("op", "layout_id", "patch", "base_rev"), "layout request")
            patch = _layout_patch(data.get("patch"))
            if patch.keys() & {"groups", "windows", "hidden"}:
                base_rev = _revision(data.get("base_rev"))
        elif op == "settings":
            _fields(data, ("op", "patch"), "settings request")
            patch = _settings_patch(data.get("patch"))
        elif op in ("create", "rename"):
            _fields(data, ("op", "source_id" if op == "create" else "layout_id", "name"), op)
            name = _text(data.get("name"), 80, "name")
        elif op in ("delete", "select"):
            _fields(data, ("op", "layout_id"), op)
        else:
            raise Invalid("op")

        lid = None if op in ("settings", "forget") else _id(data.get("source_id" if op == "create" else "layout_id"),
                                                LAYOUT_ID_RE, "layout id")
        with self.lock:
            if base_rev is not None:
                self._expect(base_rev)
            # Entries are immutable after publication; only the catalogue needs a deep copy.
            doc = dict(self.history, layouts=deepcopy(self.history["layouts"]), settings=dict(self.history["settings"]))
            layouts, settings = doc["layouts"], doc["settings"]
            layout = next((item for item in layouts if item["id"] == lid), None)
            ack = {"ok": True}
            if layout is None and lid is not None:
                if op == "delete":
                    return ack
                raise Conflict()

            if op == "save":
                reconcile(self._save(doc), save, layouts, lid, mode, seeds)
            elif op == "forget":
                save = deepcopy(self._save(doc)) or clean_save({"grid": GRID})
                save["windows"].pop(wid, None)
                for group in save["groups"]:
                    if wid in group["members"]:
                        group["members"].remove(wid)
                for item in layouts:
                    item["windows"].pop(wid, None)
                    item["hidden"].pop(wid, None)
                    item["links"]["windows"].pop(wid, None)

            if op in ("save", "forget"):
                entries, cursor = doc["entries"], doc["cursor"]
                if amend and cursor >= 0:
                    entries = list(entries)
                    entries[cursor] = dict(entries[cursor], save=save)
                else:
                    entries = (entries[:cursor + 1] + [{"t": int(time.time()), "label": label, "save": save}])[-HISTORY_LIMIT:]
                    cursor = len(entries) - 1
                doc.update(entries=entries, cursor=cursor, rev=doc["rev"] + 1)
            elif op == "layout":
                for key in ("groups", "windows", "hidden", "switches"):
                    if key in patch:
                        layout[key].update(patch[key])
                if "viewport" in patch:
                    layout["viewport"] = patch["viewport"]
                for kind, values in patch.get("links", {}).items():
                    for key, value in values.items():
                        if value is None:
                            layout["links"][kind].pop(key, None)
                        else:
                            layout["links"][kind][key] = value
            elif op == "settings":
                settings.update(patch)
            elif op == "create":
                if len(layouts) >= 20:
                    raise Invalid("layout count")
                ids = {item["id"] for item in layouts}
                new_id = "l" + os.urandom(6).hex()
                while new_id in ids:
                    new_id = "l" + os.urandom(6).hex()
                layouts.append(dict(deepcopy(layout), id=new_id, name=name))
                settings["current"] = ack["id"] = new_id
            elif op == "rename":
                layout["name"] = name
            elif op == "delete":
                if lid == "main":
                    raise Invalid("Main cannot be deleted")
                layouts.remove(layout)
                if settings["current"] == lid:
                    settings["current"] = "main"
            elif op == "select":
                settings["current"] = lid

            self._publish(doc)
            return self._state(full=False) if op in ("save", "forget") else ack

    def step(self, base_rev, offset):
        _revision(base_rev)
        with self.lock:
            self._expect(base_rev)
            hist = self.history
            target = hist["cursor"] + offset
            if hist["cursor"] >= 0 and 0 <= target < len(hist["entries"]):
                doc = dict(hist, cursor=target, rev=hist["rev"] + 1, layouts=deepcopy(hist["layouts"]))
                reconcile(self._save(hist), self._save(doc), doc["layouts"], doc["settings"]["current"], "restore", {}, history_step=True)
                self._publish(doc)
            return self._state()

    def _save_path(self, save_id):
        if not isinstance(save_id, str) or not SAVE_ID_RE.fullmatch(save_id):
            raise KeyError(save_id)
        return os.path.join(self.saves_dir, save_id + ".json")

    @staticmethod
    def _read_save(path, save_id):
        raw = load_json(path)
        version = raw["version"]
        if version == 2:
            save = clean_save(raw["save"])
        elif version == 1:
            save, _, _ = _legacy_parts(raw["arrangement"])
        else:
            raise Invalid("save version")
        return {"version": 2, "id": save_id, "name": _text(raw["name"], 80, "name"),
                "t": int(raw["t"]), "save": save}

    def saves(self):
        found = []
        with self.lock:
            for path in glob.glob(os.path.join(self.saves_dir, "s*.json")):
                try:
                    save = self._read_save(path, os.path.basename(path)[:-5])
                    found.append({"id": save["id"], "name": save["name"], "t": save["t"],
                                  "windows": len(save["save"]["windows"])})
                except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):
                    print("unreadable save skipped: " + os.path.basename(path), file=sys.stderr)
        return sorted(found, key=lambda s: -s["t"])

    def add_save(self, name, save):
        name = _text(name, 80, "name")
        save = clean_save(save)
        with self.lock:
            save_id = "s%x%s" % (int(time.time()), os.urandom(3).hex())
            write_json(self._save_path(save_id), {"version": 2, "id": save_id, "name": name,
                                                  "t": int(time.time()), "save": save})
            return {"id": save_id}

    def get_save(self, save_id):
        with self.lock:
            try:
                return self._read_save(self._save_path(save_id), save_id)
            except (OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError):
                raise KeyError(save_id)

    def delete_save(self, save_id):
        with self.lock:
            try:
                os.remove(self._save_path(save_id))
            except OSError:
                raise KeyError(save_id)


# ---------------------------------------------------------------- server

def graph_document(collect, recent, attention_file, known=()):
    """The source's graph document plus the validated attention items (null: none) and their warnings."""
    data = collect(recent=recent, known=known)
    try:
        data["attention"], notes = attention.read(attention_file)
    except Exception as error:   # input from another program must never cost the map
        print("attention file failed: %r" % error, file=sys.stderr)
        data["attention"], notes = None, ["Attention file is unreadable."]
    data["warnings"] = (notes + data["warnings"])[:20]
    return data


CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
                 ".js": "text/javascript; charset=utf-8", ".webmanifest": "application/manifest+json",
                 ".png": "image/png", ".svg": "image/svg+xml"}
STATIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*\.(?:html|css|js|webmanifest|png|svg)$")
RESPONSE_HEADERS = (
    ("Cache-Control", "no-store"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Agents-Map", "2"),
    ("Content-Security-Policy",
     "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; manifest-src 'self'; "
     "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
)


class MapServer(ThreadingHTTPServer):
    daemon_threads = True
    # A page load asks for all its files at once. The default backlog of 5 dropped one
    # request in about 25 loads, which left the page blank.
    request_queue_size = 128

    def __init__(self, port, collect, store, web_dir=WEB_DIR, attention_file=None):
        self.collect = collect
        self.store = store
        self.attention_file = attention_file   # read at every request; never sent to the page
        # the only files ever served: names found in the page folder at start
        self.static = {name: os.path.join(web_dir, name) for name in os.listdir(web_dir) if STATIC_NAME_RE.match(name)}
        if "index.html" not in self.static:
            raise SystemExit("page files not found in " + web_dir)
        super().__init__(("127.0.0.1", port), Handler)  # loopback only


class Handler(BaseHTTPRequestHandler):
    server_version = "agents-map/2"
    protocol_version = "HTTP/1.1"  # the browser reuses a few connections instead of opening one per file
    timeout = 30  # browsers open spare connections and leave them idle; do not keep a thread for each

    def log_message(self, format, *args):  # quiet: only problems are printed
        pass

    def reply(self, code, body=b"", content_type="application/json; charset=utf-8"):
        self.send_response(code)
        for name, value in RESPONSE_HEADERS:
            self.send_header(name, value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if code >= 400:  # the request's body may be unread: do not reuse the connection
            self.close_connection = True
            self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def reply_json(self, code, data):
        self.reply(code, json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    def refused(self, api, mutating):
        """HTTP status for a request this server must not answer, or 0. Only this page,
        on this machine, may use the server: checks the address asked for (DNS rebinding)
        and where the request comes from (other pages)."""
        port = self.server.server_address[1]
        hosts = ("127.0.0.1:%d" % port, "localhost:%d" % port)
        if self.headers.get("Host") not in hosts:
            return 403
        origin = self.headers.get("Origin")
        if origin is not None and origin not in tuple("http://" + host for host in hosts):
            return 403
        if api and self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
            return 403
        if mutating:
            if origin is None:
                return 403
            if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
                return 415
        return 0

    def body(self):
        try:
            length = int(self.headers.get("Content-Length") or "")
        except ValueError:
            raise Invalid("length")
        if length < 0:
            raise Invalid("length")
        if length > MAX_BODY:
            raise OverflowError()
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except ValueError:
            raise Invalid("json")
        if not isinstance(data, dict):
            raise Invalid("body")
        return data

    def route(self):
        url = urllib.parse.urlsplit(self.path)
        path, method = url.path, "GET" if self.command == "HEAD" else self.command
        api = path.startswith("/api/")
        status = self.refused(api, method != "GET")
        if status:
            return self.reply_json(status, {"error": "refused"})
        store = self.server.store
        try:
            data = None if method == "GET" else self.body()  # always read: the connection is reused
            if method == "GET" and path == "/":
                return self.static_file("index.html")
            if method == "GET" and path.startswith("/static/"):
                return self.static_file(path[len("/static/"):])
            if method == "GET" and path == "/api/graph":
                return self.graph(urllib.parse.parse_qs(url.query).get("recent") == ["1"])
            if method == "GET" and path == "/api/arrangement":
                return self.reply_json(200, store.current())
            if method == "PUT" and path == "/api/arrangement":
                return self.reply_json(200, store.put(data))
            if method == "POST" and path in ("/api/undo", "/api/redo"):
                return self.reply_json(200, store.step(data.get("base_rev"), -1 if path == "/api/undo" else 1))
            if method == "GET" and path == "/api/saves":
                return self.reply_json(200, store.saves())
            if method == "POST" and path == "/api/saves":
                return self.reply_json(200, store.add_save(data.get("name"), data.get("save")))
            if path.startswith("/api/saves/"):
                save_id = path[len("/api/saves/"):]
                if method == "GET":
                    return self.reply_json(200, store.get_save(save_id))
                if method == "DELETE":
                    store.delete_save(save_id)
                    return self.reply_json(200, {})
            return self.reply_json(404, {"error": "not found"})
        except Conflict:
            return self.reply_json(409, store.current())
        except Invalid as error:
            return self.reply_json(400, {"error": "invalid: %s" % error})
        except OverflowError:
            return self.reply_json(413, {"error": "too large"})
        except KeyError:
            return self.reply_json(404, {"error": "not found"})
        except ConnectionError:
            return None  # the browser went away mid-reply
        except OSError as error:  # the text holds a path: terminal only
            print("disk error: %r" % error, file=sys.stderr)
            return self.reply_json(500, {"error": "could not read or write the layout files"})

    def static_file(self, name):
        path = self.server.static.get(name)
        if not path:
            return self.reply_json(404, {"error": "not found"})
        with open(path, "rb") as handle:
            self.reply(200, handle.read(), CONTENT_TYPES[os.path.splitext(name)[1]])

    def graph(self, recent):
        # Errors can disclose file paths; log them only to the terminal.
        try:
            data = graph_document(self.server.collect, recent, self.server.attention_file,
                                  known=self.server.store.known_windows())
        except ValueError as error:
            print("collection failed: %r" % error, file=sys.stderr)
            return self.reply_json(503, {"error": "app data is being written; try again"})
        except Exception as error:  # the server must outlive any unreadable app state
            print("collection failed: %r" % error, file=sys.stderr)
            return self.reply_json(503, {"error": "app data unreadable"})
        self.reply_json(200, data)

    do_GET = do_HEAD = do_PUT = do_POST = do_DELETE = route


def map_server_running(port):
    """True when the port is already held by a map server."""
    request = urllib.request.Request("http://127.0.0.1:%d/" % port, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return "X-Agents-Map" in response.headers
    except OSError:
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=int, help="port on 127.0.0.1 (default: 47613, demo: 47614)")
    parser.add_argument("--demo", action="store_true", help="show sample data without RepoPrompt CE")
    parser.add_argument("--no-open", action="store_true", help="do not open the map in the browser")
    parser.add_argument("--app-support", default=repoprompt.APP_SUPPORT, help="RepoPrompt CE data folder")
    parser.add_argument("--state-dir", help="where layouts are kept (temporary by default in demo mode)")
    parser.add_argument("--attention", metavar="FILE", help="a file of items that need you, written by another program (off when absent)")
    parser.add_argument("--json", action="store_true", help="print one collection and exit")
    parser.add_argument("--recent", action="store_true", help="with --json: include recent agents without links")
    args = parser.parse_args(argv)
    args.attention = os.path.expanduser(args.attention) if args.attention else None
    if args.port is None:
        args.port = 47614 if args.demo else DEFAULT_PORT

    if not args.demo and not os.path.isdir(args.app_support):
        raise SystemExit("RepoPrompt CE data folder not found: " + args.app_support)
    collect = demo.collect if args.demo else partial(repoprompt.collect, args.app_support)
    forbidden = (args.app_support, HERE)
    with tempfile.TemporaryDirectory(prefix="agents-map-demo-") if args.demo else nullcontext() as temporary:
        if args.demo:
            args.state_dir = args.state_dir or temporary
            forbidden += (STATE_DIR, repoprompt.APP_SUPPORT)
            if args.attention is None:
                args.attention = os.path.join(temporary, "attention.json")
                write_json(args.attention, demo.attention_document())
        else:
            if args.state_dir is None:
                args.state_dir = STATE_DIR
        if args.json:
            json.dump(graph_document(collect, args.recent, args.attention), sys.stdout, ensure_ascii=False, indent=1)
            print()
            return
        if args.demo:
            previous = signal.signal(signal.SIGTERM, stop_demo)
            try:
                serve(args, collect, forbidden)
            finally:
                signal.signal(signal.SIGTERM, previous)
        else:
            serve(args, collect, forbidden)


def stop_demo(signum, frame):
    raise SystemExit(0)  # unwind the temporary state directory on termination too


def serve(args, collect, forbidden):
    url = "http://127.0.0.1:%d/" % args.port
    store = Store(args.state_dir, forbidden=forbidden)
    try:
        server = MapServer(args.port, collect, store, attention_file=args.attention)
    except OSError:
        if args.demo or not map_server_running(args.port):
            raise SystemExit("port %d is in use; pass --port" % args.port)
        print("the map is already running at " + url)
        if not args.no_open:
            webbrowser.open(url)
        return
    print("Agents Map at %s  (Ctrl-C stops it)" % url.replace(str(args.port), str(server.server_address[1])), flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
