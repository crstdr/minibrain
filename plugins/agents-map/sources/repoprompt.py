"""RepoPrompt CE source: reads the app's saved state and returns one graph document.

Read-only: no app, MCP or network call. What leaves this module holds names, models
and usage numbers, never transcripts or paths.

Files read (under ~/Library/Application Support/RepoPrompt CE):
  windowSessions.json                        open windows, one workspace each
  Overseer/continuity.sqlite                 oversight links (observer -> target)
  Overseer/link-activity.sqlite              last activity times per link
  DomainRuntime/v1/*/workspace-catalog.json  where each workspace is stored
  <workspace>/workspace.json                 open tabs and archived (stashed) tabs
  <workspace>/AgentSessions/                 session index and per-session files

Shown: open windows and known closed windows. Within each, show agents in saved tabs
if they are linked, pinned or (optionally) active in the last 24 hours. Archived agents
are counted, not drawn.
"""
import glob
import json
import os
import sqlite3
import subprocess
import time
import urllib.parse

APP_SUPPORT = os.path.expanduser("~/Library/Application Support/RepoPrompt CE")
APPLE_EPOCH = 978307200  # the app stores dates as seconds since 2001-01-01
EFFORTS = {"minimal", "low", "medium", "high", "xhigh", "max"}
RECENT_SECONDS = 24 * 3600  # "recently used" for agents without links
ACTIVE = {"running", "waitingForUser", "waitingForQuestion", "waitingForApproval"}
WORKSPACE_COLORS = {"red", "orange", "yellow", "lime", "green", "teal", "aqua",
                    "blue", "indigo", "violet", "magenta", "pink", "brown", "grey"}
APP_BINARY = "/RepoPrompt CE.app/Contents/MacOS/RepoPrompt"


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


_json_cache = {}  # path -> (mtime, size, parsed); the small index files are parsed again only when they change


def load_json(path):
    """A parsed index or workspace file. Shared between collections: callers only read it."""
    info = os.stat(path)
    hit = _json_cache.get(path)
    if not hit or hit[:2] != (info.st_mtime, info.st_size):
        hit = _json_cache[path] = (info.st_mtime, info.st_size, read_json(path))
    return hit[2]


def entries_of(path):
    """The "entries" list of one of the app's JSON files; ValueError if it has another shape."""
    data = load_json(path)
    entries = data.get("entries", []) if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise ValueError("unexpected shape")
    return [entry for entry in entries if isinstance(entry, dict)]


def upper(value):
    return value.upper() if isinstance(value, str) else None


def unix_time(apple_seconds):
    if isinstance(apple_seconds, (int, float)) and apple_seconds > 0:
        return int(apple_seconds + APPLE_EPOCH)
    return None


_links_cache = {}  # path -> last successful read


def read_links(db_path):
    """Read active oversight links in place, without locks or copies.

    If the app is mid-write, use the last good result (or no links) and try
    again on the next collection."""
    if os.path.exists(db_path):
        uri = "file:" + urllib.parse.quote(db_path) + "?mode=ro&immutable=1"
        query = "select owner_id, anchor_id from continuity_rows where kind='link' and terminal=0"
        for attempt in range(2):
            try:
                con = sqlite3.connect(uri, uri=True, timeout=1)
                try:
                    links = [(upper(o), upper(t)) for o, t in con.execute(query) if o and t and o != t]
                finally:
                    con.close()
            except sqlite3.Error:
                if attempt == 0:
                    time.sleep(0.3)
            else:
                _links_cache[db_path] = links
                return links
    return _links_cache.get(db_path, [])


_link_activity_cache = {}  # path -> (mtime, revision, activity by pair)


def read_link_activity(db_path):
    """Read one snapshot, reusing the last good result if the app is mid-write."""
    try:
        mtime = os.stat(db_path).st_mtime_ns
    except FileNotFoundError:
        return {}
    except OSError:
        return _link_activity_cache.get(db_path, (None, None, {}))[2]

    uri = "file:" + urllib.parse.quote(db_path) + "?mode=ro"
    hit = _link_activity_cache.get(db_path)
    try:
        con = sqlite3.connect(uri, uri=True, timeout=0.05)
        try:
            con.execute("BEGIN")
            if con.execute("PRAGMA user_version").fetchone() != (1,):
                raise ValueError("unexpected link activity schema")
            revision, = con.execute("SELECT revision FROM activity_state WHERE singleton = 1").fetchone()
            if hit and hit[:2] == (mtime, revision):
                return hit[2]
            activity = {}
            for observer, target, *times in con.execute(
                "SELECT observer_session_id, target_session_id, last_wake_at, "
                "last_watch_at, last_attention_at, last_instruction_at FROM link_activity"
            ):
                activity[upper(observer), upper(target)] = {
                    kind: int(at) for kind, at in zip(("wake", "watch", "attn", "msg"), times)
                    if at is not None
                }
        finally:
            con.close()
    except (sqlite3.Error, OSError, TypeError, ValueError, OverflowError):
        return hit[2] if hit else {}

    _link_activity_cache[db_path] = (mtime, revision, activity)
    return activity


def workspace_files(base):
    """Workspace paths and catalog names, keyed by workspace id."""
    found, names = {}, {}
    catalogs = glob.glob(os.path.join(base, "DomainRuntime", "v1", "*", "workspace-catalog.json"))
    for catalog in sorted(catalogs, key=os.path.getmtime):  # newest wins
        try:
            entries = entries_of(catalog)
        except (OSError, ValueError):
            continue
        for entry in entries:
            url = entry.get("fileURL")
            wid = upper(entry.get("workspaceID"))
            if wid and isinstance(url, str) and url.startswith("file://"):
                found[wid] = urllib.parse.unquote(urllib.parse.urlparse(url).path)
                names[wid] = entry.get("workspaceName") or entry.get("name")
    for path in glob.glob(os.path.join(base, "Workspaces", "*", "workspace.json")):
        wid = os.path.basename(os.path.dirname(path))[-36:].upper()
        found.setdefault(wid, path)
    return found, names


def split_model(kind, model, effort):
    """Display model and effort. A trailing effort in the model name is the option's
    default; the session's own effort setting wins when both exist."""
    model = (model or "").strip()
    effort = (effort or "").strip().lower() or None
    if ":" in model:
        head, _, tail = model.rpartition(":")
        if head and tail.lower() in EFFORTS:
            model, effort = head, effort or tail.lower()
    if effort and kind == "codexExec" and model.lower().endswith("-" + effort):
        model = model[: -len(effort) - 1]
    return model or "default", effort


def seconds(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def wake_settings(entry):
    """An overseer's auto-wake settings, as the app's panel shows them:
    all    updates from every lane can wake it ("Auto-wake on overseen lane updates")
    lanes  otherwise, the lanes chosen one by one that can
    limit  "No more often than", in seconds; 0 is "No delay"
    idle   "Wake after being idle for", in seconds; 0 is off"""
    lanes = entry.get("agentSessionLinkAutoWakeTargetSessionIDs")
    return {
        "all": entry.get("autoWakeOnOversightUpdates") is True,
        "lanes": sorted(upper(x) for x in lanes if isinstance(x, str)) if isinstance(lanes, list) else [],
        "limit": seconds(entry.get("routineWakeIntervalSeconds")) if entry.get("routineWakeIntervalEnabled") is True else 0,
        "idle": seconds(entry.get("periodicIdleWakeIntervalSeconds")) if entry.get("periodicIdleWakeEnabled") is True else 0,
    }


def context_usage(session):
    """(used tokens, window tokens) from a saved session; either may be None."""
    used = session.get("codexLastTotalTokens")
    window = session.get("codexContextWindow")
    capacity = session.get("contextWindowCapacity")
    if not window and isinstance(capacity, dict):
        window = capacity.get("tokens")
    used = used if isinstance(used, int) and used > 0 else None
    window = window if isinstance(window, int) and window > 0 else None
    return used, window


def app_started():
    """When the running app was launched (unix seconds), or None when it is not running.
    Reads the process list only; the app is never contacted."""
    try:
        out = subprocess.run(["/bin/ps", "-axo", "lstart=,comm="], capture_output=True, text=True, timeout=5,
                             env=dict(os.environ, LC_ALL="C")).stdout  # C locale: one date format to parse
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        if line.rstrip().endswith(APP_BINARY):
            try:
                return time.mktime(time.strptime(line[:24].strip(), "%a %b %d %H:%M:%S %Y"))
            except ValueError:
                return None
    return None


_session_cache = {}  # session file path -> (mtime, size, (used, window, state, sent)); a file is parsed again only when it changed


def sent_times(session):
    """{sending session id: unix seconds of its latest message to this session}: numbers only, no text or names."""
    sent = {}
    turns = (session.get("transcript") or {}).get("turns") if isinstance(session.get("transcript"), dict) else None
    for turn in turns if isinstance(turns, list) else []:
        row = turn.get("request") if isinstance(turn, dict) else None
        origin = row.get("crossSessionAttribution") if isinstance(row, dict) else None
        source = upper(origin.get("sourceSessionID")) if isinstance(origin, dict) else None
        at = unix_time(row.get("timestamp")) if source else None
        if at and at > sent.get(source, 0):
            sent[source] = at
    return sent


def session_facts(path):
    """(used tokens, window tokens, saved run state, messages received by sender, when it was saved) of one session file."""
    info = os.stat(path)
    hit = _session_cache.get(path)
    if not hit or hit[:2] != (info.st_mtime, info.st_size):
        session = read_json(path)   # large: only the facts are kept
        if not isinstance(session, dict):
            raise ValueError("not an object")
        state = session.get("lastRunState")
        hit = (info.st_mtime, info.st_size, context_usage(session) + (state if isinstance(state, str) else None, sent_times(session)))
        _session_cache[path] = hit
    return hit[2] + (info.st_mtime,)


def collect(base, recent=False, known=()):
    """One graph document. Only the fields named here leave the app's files."""
    warnings = []
    windows, seen = [], {}
    for entry in load_json(os.path.join(base, "windowSessions.json")).get("windows", []):
        wid = upper(entry.get("workspaceID")) if isinstance(entry, dict) else None
        if not wid:
            continue
        if wid in seen:  # two windows on one workspace share its tabs: one box
            seen[wid]["count"] += 1
            continue
        seen[wid] = {"id": wid, "name": str(entry.get("workspaceName") or "Untitled workspace"), "count": 1,
                     "tab": None, "session": None}
        windows.append(seen[wid])

    started = app_started()
    links = sorted(set(read_links(os.path.join(base, "Overseer", "continuity.sqlite"))))
    linked = {sid for pair in links for sid in pair}
    recent_after = time.time() - APPLE_EPOCH - RECENT_SECONDS

    ws_files, names = workspace_files(base)
    # Read saved tabs for open windows and known closed workspaces.
    open_tab, pinned, stashed = {}, set(), set()
    for wid in [*seen, *sorted(set(known) & ws_files.keys() - seen.keys())]:
        path = ws_files.get(wid)
        try:
            workspace = load_json(path) if path else {}
            if not isinstance(workspace, dict):
                raise ValueError("not an object")
        except (OSError, ValueError):
            if wid not in seen:
                continue
            workspace = {}
            warnings.append("Tabs unreadable for window '%s'." % seen[wid]["name"])
        if wid not in seen:
            name = names.get(wid) or workspace.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            seen[wid] = {"id": wid, "name": name, "count": 0, "closed": True,
                         "tab": None, "session": None}
            windows.append(seen[wid])
        color = workspace.get("color")
        if isinstance(color, str) and color in WORKSPACE_COLORS:
            seen[wid]["color"] = color
        active = seen[wid]["tab"] = upper(workspace.get("activeComposeTabID"))
        for tab in workspace.get("composeTabs") or []:
            sid = upper(tab.get("activeAgentSessionID")) if isinstance(tab, dict) else None
            if sid and isinstance(tab.get("id"), str):
                open_tab[sid] = upper(tab["id"])
                if tab.get("isPinned") is True:
                    pinned.add(sid)
                if open_tab[sid] == active:  # the chat the window shows: a link to it just brings the window forward
                    seen[wid]["session"] = sid
        for stash in workspace.get("stashedTabs") or []:
            tab = stash.get("tab") if isinstance(stash, dict) else None
            sid = upper(tab.get("activeAgentSessionID")) if isinstance(tab, dict) else None
            if sid:
                stashed.add(sid)

    received = {}  # session id -> {sender id: unix seconds of its last message to it}
    records = {}  # session id -> (workspace id, index entry, workspace dir)
    for wid, ws_path in ws_files.items():
        ws_dir = os.path.dirname(ws_path)
        index_path = os.path.join(ws_dir, "AgentSessions", "AgentSessionIndex.json")
        if not os.path.exists(index_path):
            continue
        try:
            entries = entries_of(index_path)
        except (OSError, ValueError):
            if wid in seen:
                warnings.append("Session index unreadable for window '%s'." % seen[wid]["name"])
            continue
        for entry in entries:
            sid = upper(entry.get("id"))
            if not sid:
                continue
            owner = upper(entry.get("workspaceID")) or wid
            if sid in linked or (sid in pinned and owner in seen):
                records[sid] = (owner, entry, ws_dir)
            elif recent and owner in seen:
                last = entry.get("lastActivityAt")
                if isinstance(last, (int, float)) and last >= recent_after:
                    records[sid] = (owner, entry, ws_dir)

    hidden = {"archived": 0, "no_window": 0, "no_tab": 0, "missing": 0}
    agents = {}
    for sid in sorted(set(records) | linked):
        is_linked = sid in linked
        if sid not in records:
            hidden["missing"] += 1
            continue
        wid, entry, ws_dir = records[sid]
        if wid not in seen:
            if is_linked:
                hidden["no_window"] += 1
            continue
        if sid not in open_tab:
            if is_linked:
                hidden["archived" if sid in stashed else "no_tab"] += 1
            continue
        kind = str(entry.get("agentKindRaw") or "unknown")
        model, effort = split_model(kind, entry.get("agentModelRaw"), entry.get("agentReasoningEffortRaw"))
        used = window = saved = None
        sent = {}
        state = entry.get("lastRunStateRaw")
        filename = os.path.basename(str(entry.get("filename") or ("AgentSession-%s.json" % sid)))
        try:
            used, window, file_state, sent, saved = session_facts(os.path.join(ws_dir, "AgentSessions", filename))
            state = file_state or state
        except (OSError, ValueError):
            warnings.append("Session file unreadable for '%s'." % (entry.get("name") or sid[:8]))
        agents[sid] = {
            "id": sid,
            "ws": wid,
            "tab": open_tab[sid],
            "name": str(entry.get("name") or "").strip() or "Untitled",
            "cli": kind,
            "model": model,
            "effort": effort,
            "used": used,
            "window": window,
            "state": state if isinstance(state, str) and state else "unknown",
            # The app saves a state about a second after it changes, but a crash leaves the last
            # one behind: a running or waiting state from before this launch is not confirmed.
            "stale": state in ACTIVE and (started is None or saved is None or saved < started),
            "state_at": int(saved) if saved else None,
            # The index often leaves lastActivityAt out (most entries): fall back to when the session
            # file was last saved, which tracks real activity where it exists. A save time can also
            # move without the agent doing anything (rare), so it is a fallback, not the truth.
            "last": unix_time(entry.get("lastActivityAt")) or (int(saved) if saved else None),
            "lane_of": upper(entry.get("createdByOverseerSessionID")),
            "wake": wake_settings(entry),
            "out_hidden": 0,
            "in_hidden": 0,
            "linked": is_linked,
            "pinned": sid in pinned,
        }
        if seen[wid].get("closed"):
            agents[sid].update(closed=True, stale=True)
        received[sid] = sent

    activity = read_link_activity(os.path.join(base, "Overseer", "link-activity.sqlite"))
    shown_links, hidden_links = [], 0
    for observer, target in links:
        if (observer in agents and target in agents
                and not agents[observer].get("closed") and not agents[target].get("closed")):
            link = {"o": observer, "t": target, **activity.get((observer, target), {})}
            msg = received.get(target, {}).get(observer)
            if msg is not None:
                link["msg"] = max(msg, link.get("msg", msg))
            shown_links.append(link)
            continue
        hidden_links += 1
        if observer in agents:
            agents[observer]["out_hidden"] += 1
        if target in agents:
            agents[target]["in_hidden"] += 1
    for agent in agents.values():
        if agent["lane_of"] not in agents:
            agent["lane_of"] = None

    return {
        "schema": 2,
        "generated": int(time.time()),
        "windows": windows,
        "agents": sorted(agents.values(), key=lambda a: (a["ws"], a["name"].lower(), a["id"])),
        "links": shown_links,
        "hidden": dict(hidden, links=hidden_links),
        "app_running": started is not None,
        "warnings": warnings[:20],
    }
