#!/usr/bin/env python3
"""Collection-backed roadmap: dependency graph, validation, attention items and standalone viewer.

Reads one minibrain collection folder (collection.<name>/*.md, compatible with tools/collection.py)
and produces:
  - a dependency graph document for the browser renderer (document());
  - attention items compatible with Agents Map (attention_list());
  - CLI validation (check), text digest (summary), JSON output (json), and a standalone server (serve).

Read-only on every collection file. Bound to 127.0.0.1 only. Server errors, registry warnings and
metadata never expose host filesystem paths; configured record fields and body prose are served
only to the local viewer. Python 3.9 standard library only.

Usage:
  python3 roadmap.py --collection PATH serve [--title TEXT] [--port 47615] [--no-open]
  python3 roadmap.py --collection PATH check
  python3 roadmap.py --collection PATH summary
  python3 roadmap.py --collection PATH json
"""
import argparse
import datetime
import json
import math
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
MAX_ROADMAPS = 50
MAX_ITEMS = 50
REASON_MAX = 80
GLOW_BLOCKERS = 5
SOON_WORKDAYS = 2

KINDS = ("priority", "project", "decision", "gap")
STATES = (
    "mapped", "awaiting-user", "missing", "blocked", "built-off", "partial",
    "unknown", "discussed", "specified", "paused", "in-progress", "live", "done",
)
CLOSED = ("done", "live")
ATTENTION_KINDS = ("blocker", "deadline", "calendar", "watch")
ALERTS = ("none", "glow", "pulse")
SEVERITY = {"blocker": 0, "deadline": 1, "calendar": 2, "watch": 3}
LEVEL = {"none": 0, "glow": 1, "pulse": 2}
RESERVED_IDS = frozenset({"default"})

SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
FIELD = re.compile(r"^- ([A-Za-z][\w-]*):(?:[ \t](.*)|$)")
FIELDLIKE = re.compile(r"^\s*[-*+][ \t]+[^\s:]+[ \t]*:(?!//)")
FINITE_NUM = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ARCHIVED = re.compile(r"<!-- archived: (\S+) (\d{4}-\d{2}-\d{2}) -->(\r?\n)")
ARCHIVE_MARKER = re.compile(r"<!--\s*(?:end\s+)?archived:", re.I)
LISTS = ("serves", "needs", "related")
TEXTS = (
    "kind", "state", "owner", "lane", "suggested", "due", "when", "since",
    "short", "attention", "alert", "ask", "by", "checked", "source", "tags",
)

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
    """(title, fields, body, seen_keys, parse_errors) matching minibrain core header rules."""
    lines = re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$", text)
    first = lines[0].rstrip("\r\n") if lines else ""
    title = first[2:].strip() if first.startswith("# ") else ""
    at = 1
    if at < len(lines) and not lines[at].strip():
        at += 1
    fields, seen_keys, errors = {}, set(), []
    while at < len(lines):
        raw = lines[at].rstrip("\r\n")
        match = FIELD.fullmatch(raw)
        if match:
            key = match.group(1).lower()
            if key in seen_keys:
                errors.append("duplicate header field %s" % key)
            else:
                seen_keys.add(key)
                fields[key] = (match.group(2) or "").strip()
        elif FIELDLIKE.match(raw):
            errors.append("malformed header field: %s" % raw[:60])
        else:
            if seen_keys and raw.strip():
                errors.append("malformed header line (separate the body with a blank line)")
            break
        at += 1
    body = "".join(lines[at:]).strip()
    return title, fields, body, seen_keys, errors


def parse(text):
    """(title, fields, body) of one record: '# Title', '- key: value' lines, optional blank line, body."""
    title, fields, body, _, _ = _parse_record(text)
    return title, fields, body


def _parse_number(value):
    """(float_or_none, ok) requiring a complete, finite decimal/scientific number."""
    text = (value or "").strip()
    if not text:
        return None, True
    if not FINITE_NUM.fullmatch(text):
        return None, False
    try:
        num = float(text)
    except ValueError:
        return None, False
    return (num, True) if math.isfinite(num) else (None, False)


def _number(value):
    num, ok = _parse_number(value)
    return num if ok else None


def _day(value):
    text = (value or "").strip()
    if not DATE.match(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def _moment(value):
    """A datetime for an ISO date or date-time; no zone means local time."""
    text = (value or "").strip()
    day = _day(text)
    if day:
        return datetime.datetime(day.year, day.month, day.day)
    try:
        return datetime.datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text)
    except ValueError:
        return None


def _due_epoch(value):
    """(epoch_seconds, all_day) for a validated due/when string, or (None, False)."""
    if not value:
        return None, False
    day = _day(value)
    if day:
        return int(datetime.datetime(day.year, day.month, day.day).timestamp()), True
    moment = _moment(value)
    if moment:
        return int(moment.timestamp()), False
    return None, False


def _collection_name(folder):
    name = Path(folder).name
    return name[len("collection."):] if name.startswith("collection.") else name


def _refs(value, collection_name):
    """(local_ids, external_refs) from a needs/serves/related value.

    Accepts both local IDs ('decide') and collection-qualified refs ('roadmap/decide').
    Refs pointing to another collection ('other/item') are returned in external_refs.
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


def is_open(ticket):
    return ticket["state"] not in CLOSED


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


def _effective_needs(tickets, archived=None):
    """Effective needs mapping (including archived records and priority-to-task serves edges)."""
    all_tickets = dict(archived or {})
    all_tickets.update(tickets)
    needs = {}
    for key, ticket in all_tickets.items():
        deps = [ref for ref in ticket["needs"] if ref in all_tickets]
        for ref in ticket.get("archived_needs", ()):
            if ref in all_tickets and ref not in deps:
                deps.append(ref)
        needs[key] = deps
    all_priorities = [key for key, ticket in all_tickets.items() if ticket["kind"] == "priority"]
    for priority in all_priorities:
        behind = _closure(priority, needs)
        for key, ticket in all_tickets.items():
            if priority in ticket["serves"] and key not in behind and key != priority:
                needs[priority].append(key)
                behind = _closure(priority, needs)
    priorities = [key for key, ticket in tickets.items() if ticket["kind"] == "priority"]
    return needs, priorities


def _build_ticket(label, title, fields, body, cname, archived=False):
    ticket = {"id": label, "title": title, "body": body, "archived": archived}
    for key in TEXTS:
        ticket[key] = fields.get(key, "")
    ext = []
    for key in LISTS:
        local, other = _refs(fields.get(key), cname)
        ticket[key] = local
        if key == "needs":
            ext.extend(other)
    ticket["ext"] = ext
    ticket["archived_needs"] = []
    rank_num, rank_ok = _parse_number(fields.get("rank"))
    days_num, days_ok = _parse_number(fields.get("days"))
    ticket["rank"] = rank_num
    ticket["days"] = days_num
    ticket["focus"] = fields.get("focus", "").lower() in ("yes", "true", "1")
    return ticket, rank_ok, days_ok


def _load_archived(folder, cname):
    """(archived_tickets_by_id, problems, incomplete) from optional collection.<name>.archive.md."""
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
                title, fields, body, _, _ = _parse_record("".join(block_lines))
                ticket, _, _ = _build_ticket(rid, title, fields, body, cname, archived=True)
                archived[rid] = ticket
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


def _load_all(collection_dir):
    """(active_tickets, archived_tickets, problems, warnings, incomplete) for one collection."""
    folder = Path(collection_dir)
    cname = _collection_name(folder)
    tickets, problems, warnings = {}, [], []
    try:
        st = folder.lstat()
        if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
            return {}, {}, ["collection folder is not a regular directory: %s" % cname], [], True
        entries = sorted(folder.iterdir(), key=lambda p: p.name)
    except OSError:
        return {}, {}, ["collection folder is unreadable: %s" % cname], [], True

    archived, archive_problems, incomplete = _load_archived(folder, cname)
    problems.extend(archive_problems)

    meta_by_id = {}
    for path in entries:
        if path.suffix != ".md":
            continue
        try:
            pst = path.lstat()
            if not stat.S_ISREG(pst.st_mode):
                problems.append("%s: skipped non-regular file" % path.name)
                incomplete = True
                continue
            title, fields, body, seen_keys, parse_errors = _parse_record(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as error:
            problems.append("%s: unreadable (%s)" % (path.name, type(error).__name__))
            incomplete = True
            continue
        label = path.stem
        for err in parse_errors:
            problems.append("%s: %s" % (label, err))
        if label in archived:
            problems.append("%s: archived ID reused by an active record" % label)
        ticket, rank_ok, days_ok = _build_ticket(label, title, fields, body, cname, archived=False)
        tickets[label] = ticket
        meta_by_id[label] = (seen_keys, rank_ok, days_ok)

    for ticket in tickets.values():
        label = ticket["id"]
        seen_keys, rank_ok, days_ok = meta_by_id[label]
        if not ticket["title"]:
            problems.append("%s: missing '# Title' line" % label)
        if ticket["kind"] not in KINDS:
            problems.append("%s: kind must be one of %s" % (label, ", ".join(KINDS)))
        if ticket["state"] not in STATES:
            problems.append("%s: state must be one of %s" % (label, ", ".join(STATES)))
        if not rank_ok:
            problems.append("%s: rank must be a finite number" % label)
        elif ticket["kind"] == "priority" and ticket["rank"] is None:
            problems.append("%s: priority requires numeric 'rank'" % label)
        if not days_ok:
            problems.append("%s: days must be a finite number" % label)
        if ticket["attention"] and ticket["attention"] not in ATTENTION_KINDS + ("none",):
            problems.append("%s: attention must be one of %s, none" % (label, ", ".join(ATTENTION_KINDS)))
        if ticket["alert"] and ticket["alert"] not in ALERTS:
            problems.append("%s: alert must be one of %s" % (label, ", ".join(ALERTS)))
        if ticket["due"] and _day(ticket["due"]) is None:
            problems.append("%s: due must be YYYY-MM-DD" % label)
        if ticket["when"] and _moment(ticket["when"]) is None:
            problems.append("%s: when must be an ISO date or date-time" % label)
        if len(ticket["ask"]) > REASON_MAX:
            problems.append("%s: ask is %d characters (max %d)" % (label, len(ticket["ask"]), REASON_MAX))
        if ticket["tags"]:
            bad_tags = [t for t in ticket["tags"].split() if not t.startswith("#") or len(t) == 1]
            if bad_tags:
                problems.append("%s: tags must start with # and have a name" % label)
        if "source" in seen_keys:
            src = ticket["source"]
            loc, sep, obs = src.rpartition(" @ ")
            if src != "unknown" and not (sep and loc.strip() and obs.strip()):
                problems.append("%s: source needs '<location> @ <observation>' or unknown" % label)
        if not SLUG.match(label):
            warnings.append("%s: id cannot be used as an attention item id" % label)
        for key in LISTS:
            kept, unknown = [], []
            for ref in ticket[key]:
                if ref in tickets:
                    kept.append(ref)
                elif key == "needs" and ref in archived:
                    if ref not in ticket["archived_needs"]:
                        ticket["archived_needs"].append(ref)
                elif key == "related" and ref in archived:
                    continue
                else:
                    unknown.append(ref)
            if unknown:
                problems.append("%s: %s names unknown records: %s" % (label, key, ", ".join(unknown)))
            ticket[key] = kept
        if ticket["ext"]:
            warnings.append("%s: external prerequisite not validated here: %s" % (label, ", ".join(ticket["ext"])))
        stray = [ref for ref in ticket["serves"] if tickets[ref]["kind"] != "priority"]
        if stray:
            problems.append("%s: serves must name priorities: %s" % (label, ", ".join(stray)))
            ticket["serves"] = [ref for ref in ticket["serves"] if ref not in stray]

    effective_needs, _ = _effective_needs(tickets, archived)
    cycle = _cycle(effective_needs)
    if cycle:
        problems.append("needs cycle: " + " -> ".join(cycle))
    return tickets, archived, problems, warnings, incomplete


def load(collection_dir):
    """(tickets_by_id, problems, warnings) for one collection.<name>/ folder.

    Read-only. Messages never contain host filesystem paths beyond the collection folder name.
    """
    tickets, _, problems, warnings, _ = _load_all(collection_dir)
    return tickets, problems, warnings


# ---------------------------------------------------------------- graph

def _closure(start, edges):
    seen, stack = set(), list(edges.get(start, ()))
    while stack:
        node = stack.pop()
        if node not in seen and node != start:
            seen.add(node)
            stack.extend(edges.get(node, ()))
    return seen


def graph(tickets, archived=None):
    """(needs_by_id, ordered_priorities, loose_ids, waiting_counts)."""
    all_tickets = dict(archived or {})
    all_tickets.update(tickets)
    needs, priorities = _effective_needs(tickets, archived)

    def order(key):
        ticket = tickets[key]
        return (
            0 if ticket["focus"] else 1,
            ticket["rank"] if ticket["rank"] is not None else float("inf"),
            ticket["since"] or "9999",
            key,
        )

    priorities.sort(key=order)
    active_needs = {k: [ref for ref in needs.get(k, ()) if ref in tickets] for k in tickets}
    reached = set(priorities)
    for priority in priorities:
        reached |= _closure(priority, active_needs)
    loose = sorted(key for key in tickets if key not in reached)
    waiting = {key: 0 for key in all_tickets}
    for key, ticket in all_tickets.items():
        if is_open(ticket):
            for prereq in _closure(key, needs):
                waiting[prereq] += 1
    return needs, priorities, loose, waiting


# ---------------------------------------------------------------- attention

def _workdays_until(target_day, today):
    """Working days from tomorrow to target_day inclusive; negative if passed."""
    if target_day < today:
        return -1
    count, at = 0, today
    while at < target_day:
        at += datetime.timedelta(days=1)
        if at.weekday() < 5:
            count += 1
    return count


def attention(tickets, needs, waiting, now=None, archived=None):
    """(items, warnings) ordered most pressing first.

    Explicit `alert` on a record always wins. Default loudness: overdue items or blockers
    holding soon-due work pulse; top GLOW_BLOCKERS blockers by waiting count or deadlines
    due within SOON_WORKDAYS workdays glow; everything else is still (`none`).
    """
    now = now or datetime.datetime.now()
    today, warnings, items = now.date(), [], []
    all_tickets = dict(archived or {})
    all_tickets.update(tickets)
    dependants = {key: set() for key in all_tickets}
    for key in all_tickets:
        for prereq in _closure(key, needs):
            if prereq in dependants:
                dependants[prereq].add(key)

    for key, ticket in tickets.items():
        raw_att = ticket["attention"] if ticket["attention"] in ATTENTION_KINDS + ("none",) else ""
        raw_alert = ticket["alert"] if ticket["alert"] in ALERTS else ""
        if not is_open(ticket) or raw_att == "none" or ticket["kind"] == "priority":
            continue
        when = _moment(ticket["when"]) if ticket["when"] else None
        due = _day(ticket["due"]) if ticket["due"] else None
        kind = raw_att or (
            "blocker" if ticket["kind"] == "decision" and ticket["state"] == "awaiting-user"
            else "calendar" if when else "deadline" if due else ""
        )
        if not kind or not SLUG.match(key):
            continue
        if kind == "calendar":
            if not when:
                continue
            local_when = when.replace(tzinfo=None) if when.tzinfo is None else when.astimezone().replace(tzinfo=None)
            if local_when <= now:
                continue
        reason = "".join(ch for ch in (ticket["ask"] or ticket["title"]) if ch.isprintable()).strip()
        if not reason:
            continue
        if len(reason) > REASON_MAX:
            warnings.append("%s: title exceeds %d characters; add a shorter 'ask'" % (key, REASON_MAX))
            reason = reason[:REASON_MAX - 1].rstrip() + "..."
        soon_dates = [
            d for d in (
                [due] + [_day(all_tickets[other]["due"]) for other in dependants[key]
                         if is_open(all_tickets[other]) and all_tickets[other]["due"]]
            ) if d
        ]
        items.append({
            "id": key,
            "kind": kind,
            "alert": raw_alert,
            "reason": reason,
            "due": ticket["when"] if kind == "calendar" else ticket["due"],
            "lane": ticket["lane"],
            "behind": waiting[key],
            "_overdue": bool(due and due < today),
            "_soon": any(0 <= _workdays_until(d, today) <= SOON_WORKDAYS for d in soon_dates),
        })

    blockers = sorted(
        (item for item in items if item["kind"] == "blocker" and item["behind"] > 0),
        key=lambda item: (-item["behind"], item["id"]),
    )
    glowing = {item["id"] for item in blockers[:GLOW_BLOCKERS]}
    for item in items:
        if not item["alert"]:
            if item["_overdue"] or (item["kind"] == "blocker" and item["_soon"]):
                item["alert"] = "pulse"
            elif item["id"] in glowing or (item["kind"] == "deadline" and item["_soon"]):
                item["alert"] = "glow"
            else:
                item["alert"] = "none"
        del item["_overdue"], item["_soon"]

    items.sort(key=lambda item: (
        -LEVEL[item["alert"]], SEVERITY[item["kind"]], -item["behind"], item["due"] or "9999", item["id"]
    ))
    if len(items) > MAX_ITEMS:
        warnings.append("%d attention items; showing the first %d" % (len(items), MAX_ITEMS))
        items = items[:MAX_ITEMS]
    for position, item in enumerate(items, 1):
        item["rank"] = position if position <= 10 else None
    return items, warnings


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


def validate(collection_dir, now=None):
    """(record_count, problems, warnings) without depending on full document rendering."""
    tickets, archived, problems, warnings, _ = _load_all(collection_dir)
    notes = []
    if tickets:
        needs, _, _, waiting = graph(tickets, archived=archived)
        _, notes = attention(tickets, needs, waiting, now, archived=archived)
    return len(tickets), problems, warnings + notes


def attention_list(collection_dir, agents, roadmap_id, title="", owner_lane="", now=None):
    """Build one Agents Map attention block directly from a collection, without writing files.

    Returns (block_or_none, warnings) where block matches attention.read()'s shape plus
    `source` (roadmap_id) and `title` for multi-source merging and click-through.
    """
    tickets, archived, problems, warnings, incomplete = _load_all(collection_dir)
    if not tickets:
        return None, problems[:5]
    needs, _, _, waiting = graph(tickets, archived=archived)
    items, notes = attention(tickets, needs, waiting, now, archived=archived)
    lanes_needed = {item["lane"] for item in items if item["lane"]}
    if owner_lane:
        lanes_needed.add(owner_lane)
    resolved = resolve_lanes(lanes_needed, agents)
    owner_id = resolved.get(owner_lane) if owner_lane else None
    out = []
    for item in items:
        due_epoch, all_day = _due_epoch(item["due"])
        out.append({
            "id": item["id"],
            "ticket": item["id"],
            "source": roadmap_id,
            "kind": item["kind"],
            "rank": item["rank"],
            "reason": item["reason"],
            "due": due_epoch,
            "all_day": all_day,
            "agent": resolved.get(item["lane"]) if item["lane"] else None,
            "alert": item["alert"],
        })
    ts = int((now or datetime.datetime.now().astimezone()).timestamp())
    label = title or _collection_name(collection_dir)
    block = {
        "source": roadmap_id,
        "title": label,
        "updated": ts,
        "owner": owner_id,
        "items": out,
    }
    extra_warnings = []
    if incomplete:
        block["incomplete"] = True
        extra_warnings.append("Roadmap '%s' is partly unreadable." % label)
    return block, (extra_warnings + notes)[:5]


# ---------------------------------------------------------------- document & registry

def document(collection_dir, title="", owner_lane="", roadmap_id="", now=None):
    """Build the roadmap graph document from a collection folder.

    Never exposes host filesystem paths outside the user's configured record text.
    """
    tickets, archived, problems, warnings, _ = _load_all(collection_dir)
    needs, priorities, loose, waiting = graph(tickets, archived=archived)
    items, notes = attention(tickets, needs, waiting, now, archived=archived)
    marks = {item["id"]: item for item in items}
    cname = _collection_name(collection_dir)
    nodes = []
    for key in priorities + sorted(k for k in tickets if tickets[k]["kind"] != "priority"):
        ticket = tickets[key]
        node = {
            name: ticket[name]
            for name in (
                "id", "title", "kind", "state", "owner", "lane", "suggested",
                "serves", "related", "ext", "archived_needs", "due", "when", "since",
                "focus", "short", "ask", "by", "checked", "source", "tags", "body",
            )
        }
        node.update(
            needs=[ref for ref in needs[key] if ref in tickets],
            rank=ticket["rank"],
            days=ticket["days"],
            open=is_open(ticket),
            behind=waiting[key],
            attention=None,
        )
        mark = marks.get(key)
        if mark:
            node["attention"] = {
                "kind": mark["kind"],
                "alert": mark["alert"],
                "reason": mark["reason"],
                "rank": mark["rank"],
                "due": mark["due"],
            }
        nodes.append(node)
    stamp = (now or datetime.datetime.now()).astimezone()
    return {
        "schema": 1,
        "id": roadmap_id or cname,
        "title": title or cname.replace("-", " ").title(),
        "collection": "collection." + cname,
        "generated": stamp.isoformat(timespec="seconds"),
        "owner_lane": owner_lane or "",
        "nodes": nodes,
        "order": priorities,
        "loose": loose,
        "attention": items,
        "problems": problems[:20],
        "warnings": (warnings + notes)[:20],
    }


def _clean_text(value, limit):
    if not isinstance(value, str):
        return ""
    value = "".join(ch for ch in value if ch.isprintable()).strip()
    return value[:limit] if value else ""


def read_registry(path):
    """Read and validate a --roadmaps JSON file. Warnings never expose filesystem paths.

    Format:
      {"version": 1,
       "roadmaps": [{"id": "studio-work", "title": "Studio roadmap",
                     "collection": "/abs/or/~/path/collection.roadmap",
                     "owner_lane": "Studio lead", "attention": true}]}
    """
    if not path:
        return [], []
    reg_path = Path(os.path.expanduser(path))
    try:
        if reg_path.stat().st_size > MAX_REGISTRY_BYTES:
            return [], ["Roadmaps config is too large."]
        raw = json.loads(reg_path.read_bytes()[:MAX_REGISTRY_BYTES + 1].decode("utf-8"))
    except FileNotFoundError:
        return [], []
    except (OSError, ValueError, RecursionError):
        return [], ["Roadmaps config is unreadable."]

    if (not isinstance(raw, dict) or raw.get("version") != 1
            or isinstance(raw.get("version"), bool) or not isinstance(raw.get("roadmaps"), list)):
        return [], ["Roadmaps config ignored: bad header."]

    base = reg_path.parent
    entries, seen, dropped = [], set(), []
    for index, item in enumerate(raw["roadmaps"], 1):
        try:
            if index > MAX_ROADMAPS:
                raise ValueError("beyond %d" % MAX_ROADMAPS)
            if not isinstance(item, dict):
                raise ValueError("entry")
            rid = item.get("id")
            if not isinstance(rid, str) or not SLUG.match(rid):
                raise ValueError("id")
            if rid in RESERVED_IDS:
                raise ValueError("id reserved")
            if rid in seen:
                raise ValueError("id repeated")
            title = _clean_text(item.get("title"), 80)
            if not title:
                raise ValueError("title")
            col = item.get("collection")
            if not isinstance(col, str) or not col.strip():
                raise ValueError("collection")
            col_str = os.path.expanduser(col.strip())
            if not os.path.isabs(col_str):
                # Lexical normalization only (no symlink dereference) so relative and absolute
                # collection symlinks follow the same lstat() policy in load().
                col_str = os.path.normpath(os.path.join(str(base), col_str))
            col_path = Path(col_str)
            owner_lane = _clean_text(item.get("owner_lane", ""), 80)
            emit_att = bool(item.get("attention", False))
            if "attention" in item and not isinstance(item["attention"], bool):
                raise ValueError("attention")
            seen.add(rid)
            entries.append({
                "id": rid,
                "title": title,
                "collection": str(col_path),
                "owner_lane": owner_lane,
                "attention": emit_att,
            })
        except ValueError as error:
            dropped.append("%d: %s" % (index, error))
        except (OSError, RuntimeError):
            dropped.append("%d: collection path invalid" % index)
    warnings = []
    if dropped:
        warnings.append("Roadmaps config: skipped %d entries (%s)." % (len(dropped), ", ".join(dropped[:5])))
    return entries, warnings


def summary(collection_dir, title="", owner_lane="", now=None):
    """Human-readable summary of priorities, open work and attention items."""
    doc = document(collection_dir, title=title, owner_lane=owner_lane, now=now)
    nodes = {node["id"]: node for node in doc["nodes"]}
    lines = ["%s: %d records, %d open" % (
        doc["title"], len(nodes), sum(1 for n in nodes.values() if n["open"] and n["kind"] != "priority")
    )]
    lines += ["", "Priorities:"]
    for key in doc["order"]:
        node = nodes[key]
        behind = _closure(key, {k: n["needs"] for k, n in nodes.items()})
        tag = "focus" if node["focus"] else "#%g" % node["rank"] if node["rank"] is not None else "unranked"
        waits = sum(1 for other in behind if nodes[other]["state"] == "awaiting-user")
        open_count = sum(1 for other in behind if nodes[other]["open"] and nodes[other]["kind"] != "priority")
        lines.append("  %-8s %s (%d open, %d waiting on you)" % (tag, node["title"], open_count, waits))
    lines += ["", "Needs you, most pressing first:"]
    for item in doc["attention"]:
        extra = [item["kind"]]
        if item["alert"] != "none":
            extra.append(item["alert"])
        if item["due"]:
            extra.append("due " + item["due"])
        if item["behind"]:
            extra.append("%d waiting" % item["behind"])
        if item["lane"]:
            extra.append(item["lane"])
        lines.append("  %s: %s [%s]" % (item["id"], item["reason"], ", ".join(extra)))
    for label, entries in (("Problems", doc["problems"]), ("Warnings", doc["warnings"])):
        if entries:
            lines += ["", label + ":"] + ["  " + entry for entry in entries]
    return "\n".join(lines)


# ---------------------------------------------------------------- standalone HTTP server

class RoadmapServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, port, collection_dir, title="", owner_lane="", web_dir=WEB_DIR):
        self.collection_dir = str(collection_dir)
        self.roadmap_title = title
        self.owner_lane = owner_lane
        self.static = {
            name: os.path.join(web_dir, name)
            for name in os.listdir(web_dir)
            if STATIC_NAME_RE.match(name)
        }
        if "roadmap.html" not in self.static:
            raise SystemExit("roadmap page files not found in " + str(web_dir))
        super().__init__(("127.0.0.1", port), StandaloneHandler)


class StandaloneHandler(BaseHTTPRequestHandler):
    server_version = "minibrain-roadmap/1"
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
                               owner_lane=self.server.owner_lane, roadmap_id="default")
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
    parser.add_argument("--owner", default="", help="default owner lane name")
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
            print("clean: %d records" % count)
        return 1 if problems else 0
    if args.command == "summary":
        print(summary(collection_dir, title=args.title, owner_lane=args.owner))
        return 0
    if args.command == "json":
        json.dump(document(collection_dir, title=args.title, owner_lane=args.owner),
                  sys.stdout, ensure_ascii=False, indent=1, allow_nan=False)
        print()
        return 0

    try:
        server = RoadmapServer(args.port, collection_dir, title=args.title, owner_lane=args.owner)
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
