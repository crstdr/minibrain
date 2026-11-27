#!/usr/bin/env python3
"""Collection reader, validator, attention derivation and standalone Roadmap viewer.

Reads a minibrain collection folder (collection.<name>/*.md) and produces:
  - open items with derived Attention, Blocked and Overdue flags for Agents Map;
  - a dependency graph document (needs/serves) for the Roadmap view;
  - CLI commands: check, summary, json and standalone serve on 127.0.0.1.

Read-only on every collection file. Bound to 127.0.0.1 only. Errors, warnings and
metadata never expose host filesystem paths; configured record fields and body prose
are served only to the local viewer. Python 3.9 standard library only.

Usage:
  python3 roadmap.py --collection PATH serve [--title TEXT] [--port 47615] [--no-open]
  python3 roadmap.py --collection PATH check
  python3 roadmap.py --collection PATH summary
  python3 roadmap.py --collection PATH json
"""
import argparse
import datetime
import difflib
import json
import os
import re
import stat
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEB_DIR = HERE / "web"
DEFAULT_PORT = 47615
MAX_REGISTRY_BYTES = 256 * 1024
MAX_COLLECTIONS = 50
ALLOWED_LINK_SCHEMES = ("repoprompt-ce",)

RESERVED_STATES = ("done", "in-progress", "blocked", "awaiting-user")
SEMANTIC_FIELDS = frozenset({"state", "needs", "serves", "due", "lane", "lane-link"})
RESERVED_IDS = frozenset({"default"})

SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
FIELD = re.compile(r"^- ([A-Za-z][\w-]*):(?:[ \t](.*)|$)")
FIELDLIKE = re.compile(r"^\s*[-*+][ \t]+[^\s:]+[ \t]*:(?!//)")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ARCHIVED = re.compile(r"<!-- archived: (\S+) (\d{4}-\d{2}-\d{2}) -->(\r?\n)")
ARCHIVE_MARKER = re.compile(r"<!--\s*(?:end\s+)?archived:", re.I)

_COLLAPSED_STATES = {re.sub(r"[^a-z]", "", s): s for s in RESERVED_STATES}
_NEAR_MISS_EXACT = {
    "dnoe": "done",
    "don": "done",
    "block": "blocked",
    "blocking": "blocked",
    "blockd": "blocked",
    "bloked": "blocked",
    "in-prog": "in-progress",
    "in_prog": "in-progress",
    "inprog": "in-progress",
    "in-progres": "in-progress",
    "waiting-user": "awaiting-user",
    "waiting_user": "awaiting-user",
    "waiting-for-user": "awaiting-user",
    "waiting_for_user": "awaiting-user",
    "await-user": "awaiting-user",
    "await_user": "awaiting-user",
    "needs-user": "awaiting-user",
    "needs_user": "awaiting-user",
    "need-user": "awaiting-user",
    "need_user": "awaiting-user",
    "needs-you": "awaiting-user",
    "needs_you": "awaiting-user",
}
_NEAR_MISS_TWO = {
    ("in", "progress"): "in-progress",
    ("in", "prog"): "in-progress",
    ("awaiting", "user"): "awaiting-user",
    ("waiting", "user"): "awaiting-user",
    ("await", "user"): "awaiting-user",
    ("needs", "user"): "awaiting-user",
    ("need", "user"): "awaiting-user",
    ("needs", "you"): "awaiting-user",
}
_NEAR_MISS_THREE = {
    ("waiting", "for", "user"): "awaiting-user",
    ("waiting", "on", "user"): "awaiting-user",
    ("waiting", "for", "you"): "awaiting-user",
    ("waiting", "on", "you"): "awaiting-user",
}

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
}
STATIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*\.(?:html|css|js|svg)$")
RESPONSE_HEADERS = (
    ("Cache-Control", "no-store"),
    ("X-Content-Type-Options", "nosniff"),
    ("Referrer-Policy", "no-referrer"),
    ("X-Roadmap-Server", "1"),
    ("Content-Security-Policy",
     "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; "
     "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
)


# ---------------------------------------------------------------- parsing & validation

def _parse_record(text):
    """(title, headers, fields, body, seen_keys, parse_errors) matching minibrain header rules."""
    lines = re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$", text)
    first = lines[0].rstrip("\r\n") if lines else ""
    title = first[2:].strip() if first.startswith("# ") else ""
    at = 1
    if at < len(lines) and not lines[at].strip():
        at += 1
    headers, fields, seen_keys, errors = [], {}, set(), []
    while at < len(lines):
        raw = lines[at].rstrip("\r\n")
        match = FIELD.fullmatch(raw)
        if match:
            key = match.group(1).lower()
            value = (match.group(2) or "").strip()
            if key in seen_keys:
                errors.append("duplicate header field %s" % key)
            else:
                seen_keys.add(key)
                fields[key] = value
                headers.append((key, value))
        elif FIELDLIKE.match(raw):
            errors.append("malformed header field: %s" % raw[:60])
        else:
            if seen_keys and raw.strip():
                errors.append("malformed header line (separate the body with a blank line)")
            break
        at += 1
    body = "".join(lines[at:]).strip()
    return title, headers, fields, body, seen_keys, errors


def parse(text):
    """(title, fields, body) of one record: '# Title', '- key: value' lines, optional blank line, body."""
    title, _, fields, body, _, _ = _parse_record(text)
    return title, fields, body


def parse_state(raw):
    """(first_word, detail) from a raw state header value."""
    text = (raw or "").strip()
    if not text:
        return "", ""
    parts = text.split(None, 1)
    return parts[0], (parts[1].strip() if len(parts) > 1 else "")


def near_miss_state(raw):
    """Reserved state name if raw state is a likely near-miss, else None."""
    text = (raw or "").strip()
    if not text:
        return None
    words = text.split()
    first = words[0]
    if first in RESERVED_STATES:
        return None
    cleaned = first.rstrip(":;,.").lower()
    if cleaned in RESERVED_STATES:
        return cleaned
    if cleaned in _NEAR_MISS_EXACT:
        return _NEAR_MISS_EXACT[cleaned]
    collapsed = re.sub(r"[^a-z]", "", cleaned)
    if collapsed in _COLLAPSED_STATES:
        return _COLLAPSED_STATES[collapsed]
    if len(words) >= 3:
        tri = tuple(w.rstrip(":;,.").lower() for w in words[:3])
        if tri in _NEAR_MISS_THREE:
            return _NEAR_MISS_THREE[tri]
    if len(words) >= 2:
        pair = (cleaned, words[1].rstrip(":;,.").lower())
        if pair in _NEAR_MISS_TWO:
            return _NEAR_MISS_TWO[pair]
    norm = cleaned.replace("_", "-")
    if len(norm) >= 5:
        hit = difflib.get_close_matches(norm, ("in-progress", "blocked", "awaiting-user"), n=1, cutoff=0.78)
        if hit:
            return hit[0]
    return None


def _day(value):
    text = (value or "").strip()
    if not DATE.match(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def _due_epoch(day_obj):
    if not day_obj:
        return None
    return int(datetime.datetime(day_obj.year, day_obj.month, day_obj.day).timestamp())


def _collection_name(folder):
    name = Path(folder).name
    return name[len("collection."):] if name.startswith("collection.") else name


def _parse_refs(value, collection_name):
    """(local_ids, external_refs) from a needs/serves value.

    A bare ID or '<this-collection>/ID' is local; '<other>/ID' is cross-collection.
    """
    prefix = collection_name + "/"
    local, external = [], []
    for raw in re.findall(r"[^,\s]+", value or ""):
        if raw.startswith(prefix):
            ref = raw[len(prefix):]
            if ref and ref not in local:
                local.append(ref)
        elif "/" in raw:
            if raw not in external:
                external.append(raw)
        elif raw not in local:
            local.append(raw)
    return local, external


def is_open(item):
    return item["state"] != "done"


def _clean_text(value, limit):
    if not isinstance(value, str):
        return ""
    value = "".join(ch for ch in value if ch.isprintable()).strip()
    return value[:limit] if value else ""


def _build_item(label, title, headers, fields, body, cname, archived=False):
    state_raw = fields.get("state", "").strip()
    state, state_detail = parse_state(state_raw)
    needs_local, needs_ext = _parse_refs(fields.get("needs"), cname)
    serves_local, serves_ext = _parse_refs(fields.get("serves"), cname)
    generic = [[k, v] for k, v in headers if k not in SEMANTIC_FIELDS and v]
    return {
        "id": label,
        "title": title,
        "body": body,
        "archived": archived,
        "state_raw": state_raw,
        "state": state,
        "state_detail": state_detail,
        "due": fields.get("due", "").strip(),
        "lane": fields.get("lane", "").strip(),
        "lane_link": fields.get("lane-link", "").strip(),
        "kind": fields.get("kind", "").strip(),
        "tags": fields.get("tags", "").strip(),
        "source": fields.get("source", "").strip(),
        "headers": generic,
        "_needs_local": needs_local,
        "_needs_ext": needs_ext,
        "_serves_local": serves_local,
        "_serves_ext": serves_ext,
        "needs": [],
        "serves": [],
        "archived_needs": [],
        "unresolved_needs": [],
        "unresolved_serves": [],
    }


def _load_archived(folder, cname):
    """(archived_items_by_id, problems, incomplete) from optional collection.<name>.archive.md."""
    archive_path = folder.parent / (folder.name + ".archive.md")
    try:
        st = archive_path.lstat()
    except FileNotFoundError:
        return {}, [], False
    except OSError:
        return {}, ["%s: archive file is unreadable" % archive_path.name], True
    if not stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode):
        return {}, ["%s: archive is not a regular file" % archive_path.name], True
    try:
        text = archive_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return {}, ["%s: unreadable (%s)" % (archive_path.name, type(error).__name__)], True
    archived, block, problems, incomplete = {}, None, [], False
    for line in re.findall(r"[^\n]*\n|[^\n]+\Z", text):
        start = ARCHIVED.fullmatch(line)
        if block is None and start:
            rid = start.group(1)
            if rid in archived:
                problems.append("%s: %s archived twice" % (archive_path.name, rid))
            block = (rid, [])
        elif block and line in ("<!-- end archived: %s -->%s" % (block[0], end) for end in ("\n", "\r\n")):
            rid, block_lines = block
            if rid not in archived:
                title, headers, fields, body, _, _ = _parse_record("".join(block_lines))
                archived[rid] = _build_item(rid, title, headers, fields, body, cname, archived=True)
            block = None
        elif block is not None:
            block[1].append(line)
        elif ARCHIVE_MARKER.search(line) or (archived and line.strip()):
            problems.append("%s: malformed archive marker" % archive_path.name)
            incomplete = True
            break
    if block:
        problems.append("%s: archive block %s has no end marker" % (archive_path.name, block[0]))
        incomplete = True
    return archived, problems, incomplete


def _closure(start, edges):
    seen, stack = set(), list(edges.get(start, ()))
    while stack:
        node = stack.pop()
        if node not in seen and node != start:
            seen.add(node)
            stack.extend(edges.get(node, ()))
    return seen


def _cycle(edges):
    """One cycle in an adjacency mapping {id: [dep_id, ...]} as a list of IDs, or None."""
    done, active = set(), []

    def visit(node):
        if node in done:
            return None
        if node in active:
            return active[active.index(node):] + [node]
        active.append(node)
        for other in edges.get(node, ()):
            if other in edges:
                found = visit(other)
                if found:
                    return found
        active.pop()
        done.add(node)
        return None

    for node in edges:
        found = visit(node)
        if found:
            return found
    return None


def _graph_edges(items, archived=None):
    """Build directed dependency edges (needs + non-redundant reversed serves) for layout and cycles."""
    all_items = dict(archived or {})
    all_items.update(items)
    deps = {}
    for key, item in all_items.items():
        row = [ref for ref in item["needs"] if ref in all_items]
        for ref_info in item.get("archived_needs", ()):
            ref = ref_info["id"] if isinstance(ref_info, dict) else ref_info
            if ref in all_items and ref not in row:
                row.append(ref)
        deps[key] = row
    # Reverse serves: if child serves parent, parent sits left of child in the dependency graph.
    for child_id, item in all_items.items():
        for target_id in item["serves"]:
            if target_id not in all_items:
                continue
            if target_id == child_id:
                if child_id not in deps[target_id]:
                    deps[target_id].append(child_id)
                continue
            if child_id not in _closure(target_id, deps):
                deps[target_id].append(child_id)
    return deps


def _load_all(collection_dir, warn_external=True):
    """(active_items, archived_items, problems, warnings, incomplete) for one collection."""
    folder = Path(collection_dir)
    cname = _collection_name(folder)
    items, problems, warnings = {}, [], []
    try:
        st = folder.lstat()
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            return {}, {}, ["collection folder is not a regular directory: %s" % cname], [], True
        entries = sorted(folder.iterdir(), key=lambda p: p.name)
    except OSError:
        return {}, {}, ["collection folder is unreadable: %s" % cname], [], True

    archived, archive_problems, incomplete = _load_archived(folder, cname)
    problems.extend(archive_problems)

    seen_keys_by_id = {}
    for path in entries:
        if path.suffix != ".md":
            continue
        try:
            pst = path.lstat()
            if not stat.S_ISREG(pst.st_mode):
                problems.append("%s: skipped non-regular file" % path.name)
                incomplete = True
                continue
            title, headers, fields, body, seen_keys, parse_errors = _parse_record(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            problems.append("%s: unreadable (%s)" % (path.name, type(error).__name__))
            incomplete = True
            continue
        label = path.stem
        for err in parse_errors:
            problems.append("%s: %s" % (label, err))
        if label in archived:
            problems.append("%s: archived ID reused by an active record" % label)
        items[label] = _build_item(label, title, headers, fields, body, cname, archived=False)
        seen_keys_by_id[label] = seen_keys

    # Resolve archived internal needs/serves so multi-hop archived chains work cleanly.
    for item in archived.values():
        item["needs"] = [r for r in item["_needs_local"] if r in items]
        item["archived_needs"] = [
            {"id": r, "done": archived[r]["state"] == "done"}
            for r in item["_needs_local"] if r in archived
        ]
        item["serves"] = [r for r in item["_serves_local"] if r in items or r in archived]

    for item in items.values():
        label = item["id"]
        seen_keys = seen_keys_by_id[label]
        if not item["title"]:
            problems.append("%s: missing '# Title' line" % label)
        if not SLUG.match(label):
            warnings.append("%s: id is not a valid slug" % label)
        near = near_miss_state(item["state_raw"])
        if near:
            warnings.append("%s: state '%s' looks like reserved '%s'" % (label, item["state_raw"], near))
        if item["due"] and _day(item["due"]) is None:
            problems.append("%s: due must be YYYY-MM-DD" % label)
        if item["tags"]:
            bad_tags = [t for t in item["tags"].split() if not t.startswith("#") or len(t) == 1]
            if bad_tags:
                problems.append("%s: tags must start with # and have a name" % label)
        if "source" in seen_keys:
            src = item["source"]
            loc, sep, obs = src.rpartition(" @ ")
            if src != "unknown" and not (sep and loc.strip() and obs.strip()):
                problems.append("%s: source needs '<location> @ <observation>' or unknown" % label)

        # Resolve local needs and serves; external 'col/id' refs are resolved across the registry
        # when registered collections are loaded, or reported unresolved standalone.
        for ref in item["_needs_local"]:
            if ref in items:
                item["needs"].append(ref)
            elif ref in archived:
                item["archived_needs"].append({"id": ref, "done": archived[ref]["state"] == "done"})
            else:
                item["unresolved_needs"].append(ref)
        for ref in item["_serves_local"]:
            if ref in items:
                item["serves"].append(ref)
            elif ref in archived:
                continue
            else:
                item["unresolved_serves"].append(ref)
        if warn_external:
            item["unresolved_needs"].extend(item["_needs_ext"])
            item["unresolved_serves"].extend(item["_serves_ext"])
            if item["unresolved_needs"]:
                warnings.append("%s: unresolved needs: %s" % (label, ", ".join(item["unresolved_needs"])))
            if item["unresolved_serves"]:
                warnings.append("%s: unresolved serves: %s" % (label, ", ".join(item["unresolved_serves"])))

    deps = _graph_edges(items, archived)
    cycle = _cycle(deps)
    if cycle:
        problems.append("needs cycle: " + " -> ".join(cycle))
    return items, archived, problems, warnings, incomplete


def load(collection_dir):
    """(items_by_id, problems, warnings) for one collection.<name>/ folder.

    Read-only. Messages never contain host filesystem paths beyond the collection folder name.
    """
    items, _, problems, warnings, _ = _load_all(collection_dir)
    return items, problems, warnings


# ---------------------------------------------------------------- derivation & graph

def _local_today(now=None):
    if now is None:
        return datetime.date.today()
    if isinstance(now, datetime.datetime):
        dt = now if now.tzinfo is None else now.astimezone()
        return dt.date()
    return now


def derive(items, archived=None, now=None, external_items=None):
    """Compute open, overdue, attention and blocked on every active item in place."""
    today = _local_today(now)
    ext = external_items or {}
    for item in items.values():
        opened = is_open(item)
        due_day = _day(item["due"]) if item["due"] else None
        overdue = bool(opened and due_day is not None and due_day < today)
        att = bool(opened and (item["state"] == "awaiting-user" or overdue))
        unmet = False
        if opened:
            for ref in item["needs"]:
                target = items.get(ref) if ref in items else ext.get(ref)
                if target is not None and target["state"] != "done":
                    unmet = True
                    break
            if not unmet and any(not entry["done"] for entry in item["archived_needs"]):
                unmet = True
        blocked = bool(opened and (item["state"] == "blocked" or unmet))
        item["open"] = opened
        item["overdue"] = overdue
        item["attention"] = att
        item["blocked"] = blocked
        item["due_epoch"] = _due_epoch(due_day)


def has_graph_links(items, has_incoming=False):
    """True when at least one active item declares needs/serves or receives cross-collection links."""
    if has_incoming:
        return True
    return any(
        item["needs"] or item["serves"] or item["archived_needs"]
        or item["unresolved_needs"] or item["unresolved_serves"]
        for item in items.values()
    )


def graph(items, archived=None):
    """(active_deps, roots, loose, waiting_counts) for layout and graph rendering."""
    all_items = dict(archived or {})
    all_items.update(items)
    deps = _graph_edges(items, archived)
    active_deps = {k: [ref for ref in deps.get(k, ()) if ref in items] for k in items}

    in_deg = {k: 0 for k in items}
    for k, targets in active_deps.items():
        for t in targets:
            if t in in_deg and t != k:
                in_deg[t] += 1

    sort_key = lambda k: ((items[k]["title"] or k).lower(), k)
    roots = sorted((k for k in items if in_deg[k] == 0 and active_deps[k]), key=sort_key)
    loose = sorted((k for k in items if in_deg[k] == 0 and not active_deps[k]), key=sort_key)

    # Any node trapped in a cycle with no in-degree-0 ancestor still gets a root so nothing vanishes.
    reached = set(roots) | set(loose)
    for r in roots:
        reached |= _closure(r, active_deps)
    for k in sorted(items, key=sort_key):
        if k not in reached:
            roots.append(k)
            reached.add(k)
            reached |= _closure(k, active_deps)

    waiting = {k: 0 for k in all_items}
    for k, item in all_items.items():
        if is_open(item):
            for prereq in _closure(k, deps):
                if prereq in waiting:
                    waiting[prereq] += 1
    return active_deps, roots, loose, waiting


# ---------------------------------------------------------------- lane resolution

def resolve_lanes(lanes, agents):
    """lane name -> session id from Agents Map agents ([{id, name}, ...]).

    An exact case-insensitive match wins; otherwise a unique name beginning with the lane
    followed by a separator ('-', ':', '(' or unicode dash).
    """
    found = {}
    for lane in lanes:
        if not lane:
            continue
        want = lane.strip().lower()
        exact = [a["id"] for a in agents if (a.get("name") or "").strip().lower() == want]
        if len(exact) != 1:
            exact = exact or [
                a["id"] for a in agents
                if re.match(re.escape(want) + r"(?=\s*[\u2014\u2013\-:(])", (a.get("name") or "").strip().lower())
            ]
        found[lane] = exact[0] if len(exact) == 1 else None
    return found


def resolve_lane_link(raw_link, agents, allowed_schemes=ALLOWED_LINK_SCHEMES):
    """Resolve a harness deep link to a unique open agent id, or None.

    Only link schemes in `allowed_schemes` are accepted so a record can never inject an
    arbitrary URL into the browser.
    """
    text = (raw_link or "").strip()
    if not text or not agents:
        return None
    parsed = urllib.parse.urlsplit(text)
    scheme = (parsed.scheme or "").lower()
    if not scheme or scheme not in allowed_schemes:
        return None
    if scheme != "repoprompt-ce":
        return None
    if parsed.netloc.lower() != "workspace" or parsed.path.rstrip("/") != "/open":
        return None
    qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
    sid_q = (qs.get("session_id") or [""])[0].strip().lower()
    ws_q = (qs.get("workspace_id") or [""])[0].strip().lower()
    tab_q = (qs.get("tab_id") or [""])[0].strip().lower()
    if sid_q:
        matches = [
            a["id"] for a in agents
            if (a.get("id") or "").strip().lower() == sid_q
            and (not ws_q or (a.get("ws") or "").strip().lower() == ws_q)
        ]
        return matches[0] if len(matches) == 1 else None
    if ws_q and tab_q:
        matches = [
            a["id"] for a in agents
            if (a.get("ws") or "").strip().lower() == ws_q
            and (a.get("tab") or "").strip().lower() == tab_q
        ]
        return matches[0] if len(matches) == 1 else None
    if ws_q:
        matches = [a["id"] for a in agents if (a.get("ws") or "").strip().lower() == ws_q]
        return matches[0] if len(matches) == 1 else None
    return None


def _item_sort_key(item):
    """Attention first (overdue, awaiting-user), then in-progress, blocked, neutral; earliest due first."""
    rank = 0 if item["attention"] else 1
    sub = (
        (0 if item["overdue"] else 1) if item["attention"]
        else (0 if item["state"] == "in-progress" else 1 if item["blocked"] else 2)
    )
    return (rank, sub, item["due"] or "9999", item["id"])


def _summarize_loaded(entry, items, archived, incomplete, agents, now=None, allowed_schemes=ALLOWED_LINK_SCHEMES, external_items=None, has_incoming=False):
    """Build one unified Agents Map collection block from already-loaded items."""
    derive(items, archived=archived, now=now, external_items=external_items)
    is_graph = has_graph_links(items, has_incoming=has_incoming)
    lanes_needed = {it["lane"] for it in items.values() if it["open"] and it["lane"]}
    if entry["lane"]:
        lanes_needed.add(entry["lane"])
    resolved = resolve_lanes(lanes_needed, agents)
    owner_id = (
        resolve_lane_link(entry["lane_link"], agents, allowed_schemes=allowed_schemes)
        or (resolved.get(entry["lane"]) if entry["lane"] else None)
    )
    open_items = sorted((it for it in items.values() if it["open"]), key=_item_sort_key)
    out, lane_counts = [], {}
    for it in open_items:
        agent_id = (
            resolve_lane_link(it["lane_link"], agents, allowed_schemes=allowed_schemes)
            or (resolved.get(it["lane"]) if it["lane"] else None)
            or owner_id
        )
        eff_lane = it["lane"] or entry["lane"]
        if agent_id:
            slot = lane_counts.setdefault(agent_id, {"lane": eff_lane, "open": 0, "attention": 0})
            slot["open"] += 1
            if it["attention"]:
                slot["attention"] += 1
        out.append({
            "id": it["id"],
            "source": entry["id"],
            "source_title": entry["title"],
            "has_graph": is_graph,
            "title": it["title"] or it["id"],
            "state": it["state"],
            "state_detail": it["state_detail"],
            "state_raw": it["state_raw"],
            "due": it["due"],
            "due_epoch": it["due_epoch"],
            "attention": it["attention"],
            "blocked": it["blocked"],
            "overdue": it["overdue"],
            "lane": eff_lane,
            "kind": it["kind"],
            "agent": agent_id,
        })
    block = {
        "id": entry["id"],
        "title": entry["title"],
        "lane": entry["lane"],
        "owner_id": owner_id,
        "has_graph": is_graph,
        "open": len(out),
        "attention": sum(1 for it in out if it["attention"]),
        "lanes": lane_counts,
        "items": out,
    }
    warnings = []
    if incomplete:
        block["incomplete"] = True
        warnings.append("Collection '%s' is partly unreadable." % entry["title"])
    return block, warnings


def collection_summary(
    collection_dir,
    agents,
    source_id,
    title="",
    lane="",
    lane_link="",
    now=None,
    allowed_schemes=ALLOWED_LINK_SCHEMES,
):
    """Build one unified Agents Map collection block (open items + graph flag) without writing files.

    Returns (block_or_none, warnings). Never leaks host paths.
    """
    label = title or _collection_name(collection_dir).replace("-", " ").title()
    items, archived, _, _, incomplete = _load_all(collection_dir)
    if not items and incomplete:
        return None, ["Collection '%s' is unreadable." % label]
    entry = {"id": source_id, "title": label, "lane": lane, "lane_link": lane_link}
    return _summarize_loaded(entry, items, archived, incomplete, agents, now=now, allowed_schemes=allowed_schemes)


# ---------------------------------------------------------------- validation, document & registry

def validate(collection_dir, now=None):
    """(record_count, problems, warnings) without depending on full document rendering."""
    items, archived, problems, warnings, _ = _load_all(collection_dir)
    if items:
        derive(items, archived=archived, now=now)
    return len(items), problems, warnings


def _build_document(items, archived, problems, warnings, cname, title="", lane="", collection_id="", now=None, is_graph=None):
    """Serialize one already-derived item graph into a schema-2 Roadmap document."""
    active_deps, roots, loose, waiting = graph(items, archived=archived)
    if is_graph is None:
        is_graph = has_graph_links(items)
    cid = collection_id or cname
    doc_title = title or cname.replace("-", " ").title()

    ordered = list(roots) + [k for k in sorted(items) if k not in set(roots)]
    nodes = []
    for key in ordered:
        it = items[key]
        nodes.append({
            "id": it["id"],
            "title": it["title"] or it["id"],
            "external": bool(it.get("external")),
            "source": it.get("source") or cid,
            "source_id": it.get("source_id") or it["id"],
            "source_title": it.get("source_title") or doc_title,
            "state": it["state"],
            "state_detail": it["state_detail"],
            "state_raw": it["state_raw"],
            "due": it["due"],
            "due_epoch": it["due_epoch"],
            "lane": it["lane"],
            "open": it["open"],
            "attention": it["attention"],
            "blocked": it["blocked"],
            "overdue": it["overdue"],
            "needs": it["needs"],
            "serves": it["serves"],
            "graph_deps": active_deps[key],
            "archived_needs": it["archived_needs"],
            "unresolved_needs": it["unresolved_needs"],
            "unresolved_serves": it["unresolved_serves"],
            "behind": waiting[key],
            "headers": it["headers"],
            "body": it["body"],
        })
    stamp = (now or datetime.datetime.now()).astimezone()
    return {
        "schema": 2,
        "id": cid,
        "title": doc_title,
        "collection": "collection." + cname,
        "generated": stamp.isoformat(timespec="seconds"),
        "lane": lane or "",
        "has_graph": is_graph,
        "nodes": nodes,
        "roots": roots,
        "loose": loose,
        "problems": problems[:20],
        "warnings": warnings[:20],
    }


def document(collection_dir, title="", lane="", collection_id="", now=None):
    """Build the Roadmap graph document from a single collection folder (standalone mode).

    Never exposes host filesystem paths outside the user's configured record text.
    """
    items, archived, problems, warnings, _ = _load_all(collection_dir)
    derive(items, archived=archived, now=now)
    cname = _collection_name(collection_dir)
    return _build_document(items, archived, problems, warnings, cname,
                           title=title, lane=lane, collection_id=collection_id, now=now)


def _canonical_path(path_str):
    try:
        return os.path.realpath(path_str)
    except OSError:
        return os.path.normpath(os.path.abspath(path_str))


def read_registry(path):
    """Read and validate the collections registry JSON file.

    Returns (entries, warnings). Warnings never expose host filesystem paths.
    Format:
      {"version": 1,
       "collections": [
         {"id": "studio-roadmap", "collection": "/path/to/collection.roadmap",
          "title": "Studio roadmap", "lane": "Studio lead", "lane_link": "repoprompt-ce://..."}
       ]}
    Also accepts a bare JSON array of entry objects.
    """
    if not path:
        return [], []
    reg_path = Path(os.path.expanduser(path))
    try:
        if reg_path.stat().st_size > MAX_REGISTRY_BYTES:
            return [], ["Collections registry is too large."]
        raw = json.loads(reg_path.read_bytes()[:MAX_REGISTRY_BYTES + 1].decode("utf-8"))
    except FileNotFoundError:
        return [], []
    except (OSError, ValueError, RecursionError):
        return [], ["Collections registry is unreadable."]

    if isinstance(raw, list):
        raw_list = raw
    elif (isinstance(raw, dict) and raw.get("version") == 1
          and not isinstance(raw.get("version"), bool)
          and isinstance(raw.get("collections"), list)):
        raw_list = raw["collections"]
    else:
        return [], ["Collections registry ignored: bad header."]

    base = reg_path.parent
    entries, seen_ids, seen_paths, dropped = [], set(), set(), []
    for index, item in enumerate(raw_list, 1):
        try:
            if index > MAX_COLLECTIONS:
                raise ValueError("beyond %d" % MAX_COLLECTIONS)
            if not isinstance(item, dict):
                raise ValueError("entry")
            cid = item.get("id")
            if not isinstance(cid, str) or not SLUG.match(cid):
                raise ValueError("id")
            if cid in RESERVED_IDS:
                raise ValueError("id reserved")
            if cid in seen_ids:
                raise ValueError("id repeated")
            col = item.get("collection")
            if not isinstance(col, str) or not col.strip():
                raise ValueError("collection")
            col_str = os.path.expanduser(col.strip())
            if not os.path.isabs(col_str):
                # Lexical normalization only (no symlink dereference) so relative and absolute
                # collection symlinks follow the same lstat() policy in load().
                col_str = os.path.normpath(os.path.join(str(base), col_str))
            col_path = str(Path(col_str))
            canon = _canonical_path(col_path)
            if canon in seen_paths:
                raise ValueError("collection repeated")
            if "title" in item and item["title"] is not None and not isinstance(item["title"], str):
                raise ValueError("title")
            title = _clean_text(item.get("title"), 80) or _collection_name(col_path).replace("-", " ").title()
            if "lane" in item and item["lane"] is not None and not isinstance(item["lane"], str):
                raise ValueError("lane")
            lane = _clean_text(item.get("lane"), 80)
            if "lane_link" in item and item["lane_link"] is not None and not isinstance(item["lane_link"], str):
                raise ValueError("lane_link")
            lane_link = _clean_text(item.get("lane_link"), 512)
            seen_ids.add(cid)
            seen_paths.add(canon)
            entries.append({
                "id": cid,
                "collection": col_path,
                "title": title,
                "lane": lane,
                "lane_link": lane_link,
            })
        except ValueError as error:
            dropped.append("%d: %s" % (index, error))
        except (OSError, RuntimeError):
            dropped.append("%d: collection path invalid" % index)

    warnings = []
    if dropped:
        warnings.append("Collections registry: skipped %d entries (%s)." % (len(dropped), ", ".join(dropped[:5])))
    return entries, warnings


def _load_registry_graph(entries, now=None):
    """Load all registered collections once and resolve cross-collection needs/serves edges.

    Returns (records, by_id, external_items, incoming).
    """
    records, by_id, by_ref_name, collisions = [], {}, {}, set()
    for entry in entries:
        label = entry["title"]
        try:
            items, archived, problems, warnings, incomplete = _load_all(entry["collection"], warn_external=False)
        except Exception as error:
            print("collection load failed (%s): %r" % (entry["id"], error), file=sys.stderr)
            rec = {"entry": entry, "items": None, "archived": None, "problems": [], "warnings": [],
                   "incomplete": True, "load_errors": ["Collection '%s' is unreadable." % label]}
            records.append(rec)
            by_id[entry["id"]] = rec
            continue
        if not items and incomplete:
            rec = {"entry": entry, "items": None, "archived": None, "problems": problems, "warnings": warnings,
                   "incomplete": True, "load_errors": ["Collection '%s' is unreadable." % label]}
            records.append(rec)
            by_id[entry["id"]] = rec
            continue
        rec = {"entry": entry, "items": items, "archived": archived, "problems": problems, "warnings": warnings,
               "incomplete": incomplete, "load_errors": [], "cname": _collection_name(entry["collection"])}
        records.append(rec)
        by_id[entry["id"]] = rec
        for key in (rec["cname"], entry["id"]):
            if key in by_ref_name and by_ref_name[key] is not rec:
                collisions.add(key)
            else:
                by_ref_name[key] = rec
    for key in collisions:
        by_ref_name.pop(key, None)

    incoming = {rec["entry"]["id"]: set() for rec in records}
    external_items = {}
    for rec in records:
        if rec["items"] is None:
            continue
        cid = rec["entry"]["id"]
        for rid, item in rec["items"].items():
            external_items["%s/%s" % (cid, rid)] = item

    # Resolve cross-collection needs and serves across all registered collections.
    for rec in records:
        if rec["items"] is None:
            continue
        cid = rec["entry"]["id"]
        items, archived = rec["items"], rec["archived"]
        for item in items.values():
            label = item["id"]
            for raw_ref in item["_needs_ext"]:
                col, _, rid = raw_ref.partition("/")
                target = by_ref_name.get(col)
                if target is rec:
                    if rid in items:
                        if rid not in item["needs"]:
                            item["needs"].append(rid)
                    elif rid in archived:
                        if not any(e["id"] == rid for e in item["archived_needs"]):
                            item["archived_needs"].append({"id": rid, "done": archived[rid]["state"] == "done"})
                    elif raw_ref not in item["unresolved_needs"]:
                        item["unresolved_needs"].append(raw_ref)
                elif target is not None:
                    tid = target["entry"]["id"]
                    qid = "%s/%s" % (tid, rid)
                    if rid in target["items"]:
                        if qid not in item["needs"]:
                            item["needs"].append(qid)
                        incoming[tid].add((cid, label))
                    elif rid in target["archived"]:
                        if not any(e["id"] == qid for e in item["archived_needs"]):
                            item["archived_needs"].append({"id": qid, "done": target["archived"][rid]["state"] == "done"})
                    elif raw_ref not in item["unresolved_needs"]:
                        item["unresolved_needs"].append(raw_ref)
                elif raw_ref not in item["unresolved_needs"]:
                    item["unresolved_needs"].append(raw_ref)

            for raw_ref in item["_serves_ext"]:
                col, _, rid = raw_ref.partition("/")
                target = by_ref_name.get(col)
                if target is rec:
                    if rid in items:
                        if rid not in item["serves"]:
                            item["serves"].append(rid)
                    elif rid in archived:
                        continue
                    elif raw_ref not in item["unresolved_serves"]:
                        item["unresolved_serves"].append(raw_ref)
                elif target is not None:
                    tid = target["entry"]["id"]
                    qid = "%s/%s" % (tid, rid)
                    if rid in target["items"]:
                        if qid not in item["serves"]:
                            item["serves"].append(qid)
                        incoming[tid].add((cid, label))
                    elif rid in target["archived"]:
                        continue
                    elif raw_ref not in item["unresolved_serves"]:
                        item["unresolved_serves"].append(raw_ref)
                elif raw_ref not in item["unresolved_serves"]:
                    item["unresolved_serves"].append(raw_ref)

            if item["unresolved_needs"]:
                rec["warnings"].append("%s: unresolved needs: %s" % (label, ", ".join(item["unresolved_needs"])))
            if item["unresolved_serves"]:
                rec["warnings"].append("%s: unresolved serves: %s" % (label, ", ".join(item["unresolved_serves"])))

    for rec in records:
        if rec["items"] is None:
            continue
        derive(rec["items"], archived=rec["archived"], now=now, external_items=external_items)
        rec["has_graph"] = has_graph_links(rec["items"], has_incoming=bool(incoming.get(rec["entry"]["id"])))
    return records, by_id, external_items, incoming


def load_collections(entries, agents, now=None, allowed_schemes=ALLOWED_LINK_SCHEMES):
    """Load all registered collections in a single pass, resolving cross-collection needs and serves.

    Returns (blocks, warnings). Zero host paths returned.
    """
    records, _, external_items, incoming = _load_registry_graph(entries, now=now)
    blocks, warnings = [], []
    for rec in records:
        if rec["items"] is None:
            warnings.extend(rec["load_errors"])
            continue
        block, notes = _summarize_loaded(
            rec["entry"], rec["items"], rec["archived"], rec["incomplete"], agents,
            now=now, allowed_schemes=allowed_schemes, external_items=external_items,
            has_incoming=bool(incoming.get(rec["entry"]["id"])),
        )
        blocks.append(block)
        warnings.extend(notes)
    return blocks, warnings


def document_from_registry(entries, collection_id, now=None):
    """Build a schema-2 Roadmap document for one registered collection with cross-collection nodes and edges.

    Returns (doc, node_routing) where node_routing maps node_id -> (lane, lane_link, owner_lane, owner_lane_link)
    for internal agent resolution without exposing raw lane-link URLs.
    """
    _, by_id, _, incoming = _load_registry_graph(entries, now=now)
    rec = by_id.get(collection_id)
    if not rec or rec["items"] is None or not rec.get("has_graph"):
        raise KeyError(collection_id)

    entry = rec["entry"]
    cid = entry["id"]
    local_prefix = cid + "/"
    doc_items = {}
    node_routing = {}
    for rid, item in rec["items"].items():
        copy = dict(item)
        copy["external"] = False
        copy["source"] = cid
        copy["source_id"] = rid
        copy["source_title"] = entry["title"]
        doc_items[rid] = copy
        node_routing[rid] = (item["lane"], item["lane_link"], entry["lane"], entry["lane_link"])

    neighbour_pairs = set(incoming.get(cid, ()))
    for item in rec["items"].values():
        for ref in item["needs"] + item["serves"]:
            if "/" in ref:
                oid, _, orid = ref.partition("/")
                if oid != cid:
                    neighbour_pairs.add((oid, orid))

    for oid, orid in sorted(neighbour_pairs):
        other = by_id.get(oid)
        if not other or other["items"] is None or orid not in other["items"]:
            continue
        o_entry = other["entry"]
        o_item = other["items"][orid]
        qid = "%s/%s" % (oid, orid)
        ext_needs = [
            ref[len(local_prefix):]
            for ref in o_item["needs"]
            if ref.startswith(local_prefix) and ref[len(local_prefix):] in rec["items"]
        ]
        ext_serves = [
            ref[len(local_prefix):]
            for ref in o_item["serves"]
            if ref.startswith(local_prefix) and ref[len(local_prefix):] in rec["items"]
        ]
        eff_lane = o_item["lane"] or o_entry["lane"]
        copy = dict(o_item)
        copy["id"] = qid
        copy["external"] = True
        copy["source"] = oid
        copy["source_id"] = orid
        copy["source_title"] = o_entry["title"]
        copy["lane"] = eff_lane
        copy["needs"] = ext_needs
        copy["serves"] = ext_serves
        copy["archived_needs"] = []
        copy["unresolved_needs"] = []
        copy["unresolved_serves"] = []
        doc_items[qid] = copy
        node_routing[qid] = (o_item["lane"], o_item["lane_link"], o_entry["lane"], o_entry["lane_link"])

    problems = list(rec["problems"])
    cycle = _cycle(_graph_edges(doc_items, rec["archived"]))
    if cycle:
        msg = "needs cycle: " + " -> ".join(cycle)
        if msg not in problems:
            problems.append(msg)

    doc = _build_document(
        doc_items, rec["archived"], problems, rec["warnings"], rec["cname"],
        title=entry["title"], lane=entry["lane"], collection_id=cid, now=now, is_graph=True,
    )
    return doc, node_routing


def summary(collection_dir, title="", lane="", now=None):
    """Human-readable summary of open items and attention items."""
    doc = document(collection_dir, title=title, lane=lane, now=now)
    nodes = doc["nodes"]
    open_nodes = [n for n in nodes if n["open"]]
    att_nodes = [n for n in open_nodes if n["attention"]]
    other_nodes = [n for n in open_nodes if not n["attention"]]
    lines = ["%s: %d items, %d open, %d attention" % (doc["title"], len(nodes), len(open_nodes), len(att_nodes))]

    def fmt(node):
        extra = []
        if node["state_raw"]:
            extra.append(node["state_raw"])
        if node["overdue"]:
            extra.append("overdue")
        if node["due"]:
            extra.append("due " + node["due"])
        if node["blocked"] and node["state"] != "blocked":
            extra.append("blocked")
        if node["behind"]:
            extra.append("unlocks %d" % node["behind"])
        if node["lane"]:
            extra.append(node["lane"])
        suffix = " [%s]" % ", ".join(extra) if extra else ""
        return "  %s: %s%s" % (node["id"], node["title"], suffix)

    if att_nodes:
        lines += ["", "Attention:"] + [fmt(n) for n in sorted(att_nodes, key=_item_sort_key)]
    if other_nodes:
        lines += ["", "Open:"] + [fmt(n) for n in sorted(other_nodes, key=_item_sort_key)]
    for label, entries in (("Problems", doc["problems"]), ("Warnings", doc["warnings"])):
        if entries:
            lines += ["", label + ":"] + ["  " + entry for entry in entries]
    return "\n".join(lines)


# ---------------------------------------------------------------- standalone HTTP server

class RoadmapServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, port, collection_dir, title="", lane="", web_dir=WEB_DIR):
        self.collection_dir = str(collection_dir)
        self.roadmap_title = title
        self.default_lane = lane
        self.static = {
            name: os.path.join(web_dir, name)
            for name in os.listdir(web_dir)
            if STATIC_NAME_RE.match(name)
        }
        if "roadmap.html" not in self.static:
            raise SystemExit("roadmap page files not found in " + str(web_dir))
        super().__init__(("127.0.0.1", port), StandaloneHandler)


class StandaloneHandler(BaseHTTPRequestHandler):
    server_version = "minibrain-roadmap/2"
    protocol_version = "HTTP/1.1"
    timeout = 30

    def log_message(self, format, *args):
        pass

    def reply(self, code, body=b"", content_type="application/json; charset=utf-8"):
        self.send_response(code)
        for name, value in RESPONSE_HEADERS:
            self.send_header(name, value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if code >= 400:
            self.close_connection = True
            self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def reply_json(self, code, data):
        self.reply(code, json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))

    def refused(self, api):
        port = self.server.server_address[1]
        hosts = ("127.0.0.1:%d" % port, "localhost:%d" % port)
        if self.headers.get("Host") not in hosts:
            return 403
        origin = self.headers.get("Origin")
        if origin is not None and origin not in tuple("http://" + host for host in hosts):
            return 403
        if api and self.headers.get("Sec-Fetch-Site") not in (None, "same-origin", "none"):
            return 403
        return 0

    def route(self):
        url = urllib.parse.urlsplit(self.path)
        path, method = url.path, "GET" if self.command == "HEAD" else self.command
        status = self.refused(path.startswith("/api/"))
        if status:
            return self.reply_json(status, {"error": "refused"})
        if method != "GET":
            return self.reply_json(405, {"error": "roadmap is read-only"})
        try:
            if path in ("/api/roadmap", "/api/roadmap/default"):
                doc = document(self.server.collection_dir, title=self.server.roadmap_title,
                               lane=self.server.default_lane, collection_id="default")
                return self.reply_json(200, doc)
            if path in ("/", "/roadmap", "/roadmap/"):
                name = "roadmap.html"
            elif path.startswith("/static/"):
                name = path[len("/static/"):]
            else:
                return self.reply_json(404, {"error": "not found"})
            found = self.server.static.get(name)
            if not found:
                return self.reply_json(404, {"error": "not found"})
            with open(found, "rb") as handle:
                return self.reply(200, handle.read(), CONTENT_TYPES[os.path.splitext(name)[1]])
        except ConnectionError:
            return None
        except Exception as error:
            print("roadmap request failed: %r" % error, file=sys.stderr)
            return self.reply_json(500, {"error": "roadmap unavailable"})

    do_GET = do_HEAD = do_PUT = do_POST = do_DELETE = route


def _default_collection():
    for candidate in (Path.cwd() / "collection.roadmap", HERE / "sample" / "collection.roadmap"):
        if candidate.is_dir():
            return str(candidate)
    return str(Path.cwd() / "collection.roadmap")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--collection", default=None, help="path to a collection.<name>/ folder")
    parser.add_argument("--title", default="", help="display title for the roadmap")
    parser.add_argument("--lane", default="", help="default lane name")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="port on 127.0.0.1 (default: %(default)s)")
    parser.add_argument("--no-open", action="store_true", help="do not open a browser")
    parser.add_argument("command", nargs="?", default="serve", choices=("serve", "check", "summary", "json"))
    args = parser.parse_args(argv)
    collection_dir = os.path.expanduser(args.collection) if args.collection else _default_collection()

    if args.command == "check":
        count, problems, warnings = validate(collection_dir)
        for entry in problems:
            print("PROBLEM:", entry)
        for entry in warnings:
            print("warning:", entry)
        if not problems and not warnings:
            print("clean: %d items" % count)
        return 1 if problems else 0
    if args.command == "summary":
        print(summary(collection_dir, title=args.title, lane=args.lane))
        return 0
    if args.command == "json":
        json.dump(document(collection_dir, title=args.title, lane=args.lane),
                  sys.stdout, ensure_ascii=False, indent=1, allow_nan=False)
        print()
        return 0

    try:
        server = RoadmapServer(args.port, collection_dir, title=args.title, lane=args.lane)
    except OSError:
        raise SystemExit("port %d is in use; pass --port" % args.port)
    url = "http://127.0.0.1:%d/" % server.server_address[1]
    print("Roadmap at %s  (Ctrl-C stops it)" % url, flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
