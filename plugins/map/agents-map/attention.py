"""The attention file: things that need the user, written by another program.

The server reads one file, given with --attention, and puts its validated items into the
graph document. The file is input from another program, so it is checked strictly: a bad
item is dropped (with a note in the document's warnings), a bad header drops the whole
list, and a missing file is no attention and no warning. The path never reaches the page.

Format, version 1 (the writer replaces the file atomically: temp file, then rename):

  {"version": 1,
   "updated": "2026-11-17T09:30:00+02:00",     ISO date-time of this write (no zone: local time)
   "owner": "<session id of the writer>",       its box carries the items that have no shown agent
   "items": [{"id": "invoice-q4",               slug, unique in the file
              "kind": "blocker",                blocker | deadline | calendar | watch
              "rank": 2,                        optional, 1 (most important) to 10
              "reason": "Waiting for approval", 1 to 80 characters
              "due": "2026-11-18",              optional, ISO date or date-time
              "agent": "<session id>",          optional, or null: not about one agent
              "alert": "glow"}]}                optional, none | glow | pulse

The writer chooses each item's alert level: "none" (default) is a still badge, "glow" is
a slow amber breath and "pulse" a stronger, faster one. Glow and pulse also make their
agent "need you" and count in the bar; Seen calms them. kind, due and rank are information
only. Dates without a zone are local time.
"""
import json
import os
import re
from datetime import date, datetime

MAX_BYTES = 256 * 1024
MAX_ITEMS = 50
KINDS = ("blocker", "deadline", "calendar", "watch")
ALERTS = ("none", "glow", "pulse")
SESSION_RE = re.compile(r"^[0-9A-Z][0-9A-Z-]{0,79}$")   # as agents_map.ID_RE: ids are upper-cased
SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REASON_MAX = 80
NOTED = 5   # dropped items named in the warning


def _moment(value):
    """Epoch seconds of an ISO date-time string; no zone means local time."""
    if not isinstance(value, str):
        raise ValueError("not text")
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    return int(datetime.fromisoformat(text).timestamp())


def _due(value):
    """(epoch seconds, all_day): an ISO date is the start of that local day."""
    if isinstance(value, str) and DATE_RE.match(value.strip()):
        day = date.fromisoformat(value.strip())
        return int(datetime(day.year, day.month, day.day).timestamp()), True
    return _moment(value), False


def _session(value):
    if not isinstance(value, str) or not SESSION_RE.match(value.strip().upper()):
        raise ValueError("not a session id")
    return value.strip().upper()


def _item(raw):
    """One validated item, or ValueError naming the field."""
    if not isinstance(raw, dict):
        raise ValueError("item")
    item_id, kind = raw.get("id"), raw.get("kind")
    if not isinstance(item_id, str) or not SLUG_RE.match(item_id):
        raise ValueError("id")
    if kind not in KINDS:
        raise ValueError("kind")
    rank = raw.get("rank")
    if rank is not None and (isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= 10):
        raise ValueError("rank")
    reason = raw.get("reason")
    if isinstance(reason, str):
        reason = "".join(ch for ch in reason if ch.isprintable()).strip()
    if not isinstance(reason, str) or not 1 <= len(reason) <= REASON_MAX:
        raise ValueError("reason")
    due, all_day = None, False
    if raw.get("due") is not None:
        try:
            due, all_day = _due(raw["due"])
        except (ValueError, OverflowError, OSError):
            raise ValueError("due")
    agent = raw.get("agent")
    try:
        agent = None if agent is None else _session(agent)
    except ValueError:
        raise ValueError("agent")
    alert = raw.get("alert")
    if alert is None:
        alert = "none"
    if alert not in ALERTS:
        raise ValueError("alert")
    return {"id": item_id, "kind": kind, "rank": rank, "reason": reason, "due": due, "all_day": all_day,
            "agent": agent, "alert": alert}


def read(path):
    """(attention, warnings). attention is None for no file or an unusable one, else
    {"updated": epoch seconds, "owner": session id, "items": [...]}. Warnings never hold the path."""
    if not path:
        return None, []
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None, ["Attention file is too large."]
        with open(path, "rb") as handle:
            raw = json.loads(handle.read(MAX_BYTES + 1).decode("utf-8"))
    except FileNotFoundError:
        return None, []
    except (OSError, ValueError, RecursionError):   # unreadable, not JSON, not UTF-8
        return None, ["Attention file is unreadable."]
    field = "file"
    try:
        if not isinstance(raw, dict) or raw.get("version") != 1 or isinstance(raw.get("version"), bool):
            raise ValueError
        field = "updated"
        updated = _moment(raw.get("updated"))
        field = "owner"
        owner = _session(raw.get("owner"))
        field = "items"
        if not isinstance(raw.get("items"), list):
            raise ValueError
    except (ValueError, OverflowError, OSError):
        return None, ["Attention file ignored: bad %s." % ("version" if field == "file" else field)]
    items, seen, dropped = [], set(), []
    for number, entry in enumerate(raw["items"], 1):
        try:
            if number > MAX_ITEMS:
                raise ValueError("beyond %d" % MAX_ITEMS)
            item = _item(entry)
            if item["id"] in seen:
                raise ValueError("id repeated")
            seen.add(item["id"])
            items.append(item)
        except ValueError as error:
            dropped.append("%d: %s" % (number, error))
    warnings = []
    if dropped:
        more = len(dropped) - NOTED
        warnings.append("Attention file: dropped %d of %d items (%s%s)." % (
            len(dropped), len(raw["items"]), ", ".join(dropped[:NOTED]), ", +%d more" % more if more > 0 else ""))
    return {"updated": updated, "owner": owner, "items": items}, warnings
