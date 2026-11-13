#!/usr/bin/env python3
"""Local Markdown collections. Create and change records by editing collection.NAME/ID.md.
For wikilinks, avoid # and brackets in IDs. Put collection.NAME/ where its
records belong: usually inside the space that owns them, or at the root when it
spans spaces. NAME is unique across the brain; hidden folders are skipped.

Start with '# Title', optionally one blank line, then single-line '- key: value'
fields. Separate the body with a blank line. An ordinary prose list is body.
Keys are case-insensitive. needs accepts local IDs or NAME/ID separated by
spaces or commas. tags are space-separated #tags. source is 'location @ ref'
or 'unknown'. Source pointers are data and are never fetched.

query NAME [SQL|-] reads one SQLite SELECT from argv or stdin when SQL is '-'.
No SQL gives a summary and schema. Each local collection is a table.
In SQL names, characters other than letters, digits and underscores become
underscores, and a leading digit gains a leading underscore:
collection.sprint-tasks is sprint_tasks; assessed-on is assessed_on.
Use single quotes for strings.
_id, _ref, _title and _unmet are metadata. _unmet counts distinct unsatisfied
direct needs. Incomplete evidence below an item or a reachable cycle gives
NULL. A count conveys neither authority nor capacity. Other columns are
effective fields. Blanks and governed clearances are NULL. Only configured
numeric fields use REAL. The leading number is the score and trailing commentary
is non-computational. For example, 1 (1 day), 2 (1 week), 3 (1 month) score
1, 2, 3; no unit conversion occurs. COLLATE natural_id orders P2 before P10.
Use IS NULL for missing values. Inspect the records for rationale. Include
operands and known/total coverage in ranked briefs. Downstream sums do not
measure causal unlock value.

needs(item,need) and reach(item,need,depth) use qualified refs. reach excludes
self and gives shortest distances. graph NAME/ID lists one record's
prerequisites and dependants at every depth, with state and title.
Results are LF-ended, CSV-quoted TSV with headers. SQL NULL prints an empty
cell. SQL runs against memory with an instruction budget. No extension
loading, SQL writes, or source access. The budget excludes snapshot setup;
reach is built only when queried and can grow quadratically. This is not a
memory sandbox for adversarial SQL.

Promote within a collection by changing its locally defined state. Across
collections, create the destination record and close the source with a
wikilink to the destination's root-relative path, e.g.
[[spaces/Sorrel/collection.tasks/T-1]] for the ref tasks/T-1. Retain the
committed source. Keep one canonical home. Records require neither map
registration nor a routine collection-only changelog entry. Follow the brain's
Checkpoint procedure for durable outcomes.

Follow the brain's writer/delegation rules, edit only your own assessments,
and recheck waiting conditions at their approved sources before acting.

Set GOVERNED_FIELDS for authority-controlled fields across all collections.
Their values live only as dated entries under '## History', newest first;
check states the entry format when one is misplaced or malformed.
Configure numeric fields and satisfying prerequisite states per collection.
State values match exactly, including case. Changing governance or delegation
requires the brain's instruction authority.
Source-owned facts stay at their source. A waiting record describes the trigger,
where to check, its dated observation and the next permitted action in prose.

For example, with benefit/cost numeric and 'open' the local candidate state:
  query tasks "SELECT _id,benefit,cost,benefit/cost AS score FROM tasks WHERE state='open' AND _unmet=0 AND benefit IS NOT NULL AND cost>0 ORDER BY score DESC LIMIT 5"
  query tasks "SELECT item,depth FROM reach WHERE need='tasks/T-1' ORDER BY depth"
  graph tasks/T-1
The relation names needs, reach and sqlite_* are reserved.
An SQL error can follow streamed rows: nonzero exit means discard that result.

archive NAME ID... moves committed records whole into collection.NAME.archive.md
beside the folder; restore NAME ID moves one back. Neither commits. Archived
records stay in needs, reach, _unmet and graph, are not table rows, and their
IDs stay taken. Do not edit the archive.
"""

import argparse
from collections import defaultdict, deque
import csv
from datetime import date
import importlib.util
import io
import math
import os
from pathlib import Path
import re
import stat
import sys

COLLECTION_PREFIX = "collection."
ARCHIVE_SUFFIX = ".archive.md"
GOVERNED_FIELDS = set()
NUMERIC_FIELDS = {}       # collection name -> set of numeric field names
SATISFIED_STATES = {}     # target collection name -> set of satisfying state values
CORE_HELPER = "minibrain.py"  # sibling filename; retain an adopted helper's local name

ROOT = Path(__file__).resolve().parent.parent
FIELD = r"[A-Za-z][\w-]*"
HEADER = re.compile(r"^- (" + FIELD + r"):(?:[ \t](.*)|$)")
FIELDLIKE = re.compile(r"^\s*[-*+][ \t]+[^\s:]+[ \t]*:(?!//)")
NUMBER = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?=$|[\s(])")
ENTRY = re.compile(r"^- (\d{4}-\d{2}-\d{2}) (" + FIELD +
                   r"): (.+?) — (.+?); authority: ([^;]+?)(?:; assent: (.+?))?$")
EVENT = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\d{4}-\d{2}-\d{2}\s*[:—-]\s*|[^\s:]+\s+)?"
                   r"([*_`]*)(" + FIELD + r")[*_`]*\s*:")
FENCE = re.compile(r"^ {0,3}(\x60{3,}|~{3,})(.*)$")
ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*)|$)")
ARCHIVED = re.compile(r"<!-- archived: (\S+) (\d{4}-\d{2}-\d{2}) -->(\r?\n)")
MARKER = re.compile(r"<!--\s*(?:end\s+)?archived:", re.I)
ARCHIVE_HEADER = ("# Archived collection.{0} records\n\nWritten by tools/collection.py archive; "
                  "restore one with: python3 tools/collection.py restore {0} ID. Do not edit.\n\n")
SYSTEM = {"needs": ("item", "need"), "reach": ("item", "need", "depth")}
META = {"_id": "TEXT PRIMARY KEY", "_ref": "TEXT", "_title": "TEXT",
        "_unmet": "INTEGER"}


def die(message):
    raise ValueError(message)


def note(message):
    print(message, file=sys.stderr)


def day(value):
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            pass
    return None


def is_record(rel):
    parts = rel.split("/")
    return (len(parts) >= 2 and parts[-2].startswith(COLLECTION_PREFIX)
            and len(parts[-2]) > len(COLLECTION_PREFIX) and parts[-1].endswith(".md")
            and not any(p.startswith((".", COLLECTION_PREFIX)) for p in parts[:-2]))


def is_archive(rel):
    parts = rel.split("/")
    return (parts[-1].startswith(COLLECTION_PREFIX) and parts[-1].endswith(ARCHIVE_SUFFIX)
            and len(parts[-1]) > len(COLLECTION_PREFIX + ARCHIVE_SUFFIX)
            and not any(p.startswith((".", COLLECTION_PREFIX)) for p in parts[:-1]))


def folder_of(rel):
    """The collection.NAME folder of a record or archive path."""
    return rel[:-len(ARCHIVE_SUFFIX)] if is_archive(rel) else rel.rpartition("/")[0]


def name_of(folder):
    return folder.rpartition("/")[2][len(COLLECTION_PREFIX):]


def ref_of(rel):
    folder, _, item = rel.rpartition("/")
    return name_of(folder) + "/" + item[:-3]


def stamp(st):
    return st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns


def inventory():
    """Collection folders by name, at any depth outside hidden folders; stamps of records and archives."""
    folders, files = defaultdict(set), {}

    def fail(error):
        raise error

    for current, dirs, entries in os.walk(ROOT, onerror=fail):
        for entry in sorted(dirs + entries):
            if not entry.startswith(COLLECTION_PREFIX) or entry == COLLECTION_PREFIX:
                continue
            path = Path(current) / entry
            rel = path.relative_to(ROOT).as_posix()
            st = path.lstat()
            if stat.S_ISLNK(st.st_mode):
                die(f"symlink collection path: {rel}")
            if stat.S_ISDIR(st.st_mode):
                folders[name_of(rel)].add(rel)
                for child in path.iterdir():
                    record = rel + "/" + child.name
                    if is_record(record):
                        child_st = child.lstat()
                        if not stat.S_ISREG(child_st.st_mode):
                            die(f"record is not a regular file: {record}")
                        files[record] = stamp(child_st)
            elif is_archive(rel):
                if not stat.S_ISREG(st.st_mode):
                    die(f"archive is not a regular file: {rel}")
                folders[name_of(folder_of(rel))].add(rel)
                files[rel] = stamp(st)
        dirs[:] = [d for d in dirs if not d.startswith((".", COLLECTION_PREFIX))]
    return folders, files


def unpack(text):
    """Archive blocks by ID as (content, start, end); start and end are offsets into text.
    Markers are written with LF; a CRLF checkout converts them and the separator alike."""
    blocks, block, offset = {}, None, 0
    for line in re.findall(r"[^\n]*\n|[^\n]+\Z", text):
        start = ARCHIVED.fullmatch(line)
        if block is None and start:
            if start[1] in blocks:
                die(f"{start[1]} archived twice")
            block = (start[1], offset, offset + len(line), start[3])
        elif block and line in (f"<!-- end archived: {block[0]} -->" + end for end in ("\n", "\r\n")):
            content = text[block[2]:offset]
            if not content.endswith(block[3]):
                die(f"malformed archive block {block[0]}")
            blocks[block[0]] = (content[:-len(block[3])], block[1], offset + len(line))
            block = None
        elif MARKER.search(line) or (block is None and blocks):
            die(f"malformed archive line: {line.rstrip()}")
        offset += len(line)
    if block:
        die(f"archive block {block[0]} has no end marker")
    return blocks


def stored(rel, text):
    """Archived content by the record's former path."""
    try:
        blocks = unpack(text)
    except ValueError as error:
        die(f"{rel}: {error}")
    return {f"{folder_of(rel)}/{item}.md": content for item, (content, _, _) in blocks.items()}


def archived_paths(documents):
    """Former paths of archived records, which stay valid wikilink targets."""
    paths = set()
    for rel, content in documents.items():
        if is_archive(rel):
            try:
                paths.update(stored(rel, content))
            except ValueError:
                pass  # check reports the malformed archive
    return paths


def conflicts(folders, records, archived):
    # An archive is named only when its folder is absent.
    places = {name: {p for p in paths if not (is_archive(p) and folder_of(p) in paths)}
              for name, paths in folders.items()}
    return ([f"duplicate collection name {name}: {', '.join(sorted(paths))}"
             for name, paths in sorted(places.items()) if len(paths) > 1]
            + [f"archived ID reused by an active record: {records[ref].rel}"
               for ref in sorted(records.keys() & archived.keys())])


def read_bytes(rel, expected):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(ROOT / rel, flags), "rb") as stream:
        if stamp(os.fstat(stream.fileno())) != expected:
            die(f"record changed during read: {rel}")
        return stream.read()


def physical_lines(text):
    return re.findall(r"[^\r\n]*(?:\r\n|\r|\n)|[^\r\n]+$", text)


def structure(lines):
    """Headings as (level, title, start, body start), plus open fence/comment state."""
    headings, literal, fence = [], set(), ""
    comment = False
    for i, raw in enumerate(lines):
        s = raw.rstrip("\r\n")
        if not fence and (comment or re.match(r"^ {0,3}<!--", s)):
            literal.add(i)
            comment = "-->" not in s
            continue
        mark = FENCE.match(s)
        if not fence and mark and mark[1][0] == "`" and "`" in mark[2]:
            mark = None  # A backtick fence cannot have a backtick in its info string.
        if fence or mark:
            literal.add(i)
            if not fence:
                fence = mark[1]
            elif mark and mark[1][0] == fence[0] and len(mark[1]) >= len(fence) and not mark[2].strip():
                fence = ""
            continue
        match = ATX.fullmatch(s)
        if match:
            title = re.sub(r"(?:^|[ \t]+)#+[ \t]*$", "", match[2] or "").strip()
            headings.append((len(match[1]), title, i, i + 1))
        elif i and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", s) and i - 1 not in literal:
            prev = lines[i - 1].strip()
            def paragraph_line(j):
                value = lines[j].rstrip("\r\n")
                return (j not in literal and value.strip() and not ATX.fullmatch(value)
                        and not re.match(r"^ {0,3}(?:[-*+]\s|\d+[.)]\s|>)", value)
                        and not re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", value))
            if prev and paragraph_line(i - 1):
                start = i - 1
                while start and paragraph_line(start - 1):
                    start -= 1
                # Setext paragraphs can have indented continuations after an unindented start.
                while start < i and re.match(r"^(?: {4}|\t)", lines[start]):
                    start += 1
                if start == i:
                    continue
                title = " ".join(line.strip() for line in lines[start:i])
                headings.append((1 if s.strip()[0] == "=" else 2, title, start, i + 1))
    return headings, literal, fence or ("<!--" if comment else "")


class Record:
    archived = False

    def __init__(self, rel, text):
        self.rel = rel
        self.ref = ref_of(rel)
        self.name, self.id = self.ref.split("/", 1)
        self.lines = lines = physical_lines(text)
        self.title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else ""
        self.errors, self.fields, self.at, self.events = [], {}, {}, []
        if not self.id or re.search(r"[\s,]", self.id):
            self.error("record id must be nonempty and contain no whitespace or comma")
        if not self.title:
            self.error("record needs a # Title line")

        governed = {k.lower() for k in GOVERNED_FIELDS}
        i = 1
        if i < len(lines) and not lines[i].strip():
            i += 1
        while i < len(lines):
            s = lines[i].rstrip("\r\n")
            match = HEADER.fullmatch(s)
            if match:
                key = match[1].lower()
                if key in self.at:
                    self.error(f"duplicate header field {key}")
                self.at[key] = i
                if key in governed:
                    self.error(f"{key} is governed: remove it from the header and prepend under ## History: - YYYY-MM-DD {key}: VALUE — REASON; authority: REF[; assent: NAMES] (VALUE 'cleared' clears it)")
                else:
                    self.fields[key] = (match[2] or "").strip() or None
            elif FIELDLIKE.match(s):
                self.error(f"malformed header field: {s}")
            else:
                if self.at and s.strip():
                    self.error(f"malformed header line: {s} (separate the body with a blank line)")
                break
            i += 1
        self.header_end = i

        self.heads, literal, _ = structure(lines)
        self.sections = defaultdict(list)
        end = len(lines)
        for level, title, start, body in reversed(self.heads):
            if level <= 2:
                if level == 2:
                    self.sections[title].append((body, end))
                end = start
        history = self.sections.get("History", [])
        if len(history) > 1:
            self.error("duplicate History heading")
        lo, hi = history[0] if history else (0, 0)

        seen, last = set(), ""
        for i, raw in enumerate(lines):
            s = raw.rstrip("\r\n")
            if i in literal or i < self.header_end:
                continue
            match = ENTRY.fullmatch(s)
            valid = (match and day(match[1])
                     and all(v.strip() for v in match.groups()[2:] if v is not None))
            # Retain canonical decisions independently of current governance.
            if lo <= i < hi and valid:
                self.events.append(s)
            event = EVENT.match(s)
            if not event or event[2].rstrip(event[1]).lower() not in governed:
                continue
            if not lo <= i < hi:
                if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+\d", s):
                    self.error("governed entry outside ## History")
                continue
            if not valid:
                self.error(f"malformed governed entry: {s} — expected: - YYYY-MM-DD field: value — reason; authority: ref[; assent: names]")
                continue
            if i + 1 < hi and lines[i + 1].strip() and not lines[i + 1].startswith("- "):
                self.error("governed entries must use one line each")
            if last and last < match[1]:
                self.error("governed history is not newest first")
            last = match[1]
            key, value = match[2].lower(), match[3].strip()
            if key not in seen:
                self.fields[key] = None if value.lower() == "cleared" else value
                seen.add(key)

        self.tags = (self.fields.get("tags") or "").split()
        if any(not t.startswith("#") or len(t) == 1 for t in self.tags):
            self.error("tags must start with # and have a name")
        source = self.fields.get("source")
        if "source" in self.at or source is not None:
            loc, sep, obs = (source or "").rpartition(" @ ")
            if source != "unknown" and not (sep and loc.strip() and obs.strip()):
                self.error("source needs '<location> @ <observation>' or unknown")
        tokens = re.findall(r"[^,\s]+", self.fields.get("needs") or "")
        self.needs = list(dict.fromkeys(t if "/" in t else self.name + "/" + t for t in tokens))

    def error(self, message):
        self.errors.append(f"{self.rel}: {message}")


def snapshot():
    """Active and archived records by ref; archived ones are flagged."""
    before = inventory()
    records, archived = {}, {}
    for rel, sig in sorted(before[1].items()):
        try:
            content = read_bytes(rel, sig).decode("utf-8")
        except UnicodeDecodeError as error:
            die(f"{rel}: invalid UTF-8: {error}")
        if is_archive(rel):
            for path, body in stored(rel, content).items():
                rec = Record(path, body)
                rec.archived = True
                archived[rec.ref] = rec
        else:
            rec = Record(rel, content)
            records[rec.ref] = rec
    if inventory() != before:
        die("collections changed during snapshot; take a consistent read")
    problems = conflicts(before[0], records, archived)
    if problems:
        die("\n".join(problems))
    return before, {**archived, **records}


class Network:
    def __init__(self, records):
        self.forward = {ref: r.needs for ref, r in records.items()}
        self.back = defaultdict(list)
        self.errors, self.order = [], []
        for ref, targets in self.forward.items():
            for t in targets:
                self.back[t].append(ref)
                if t not in records:
                    self.errors.append(f"{ref} needs unknown record {t}")

        # Finish dependencies first. An edge back into the active stack names a cycle.
        done, active = set(), {}
        for root in self.forward:
            if root in done:
                continue
            stack = [(root, iter(self.forward[root]))]
            active[root] = 0
            while stack:
                node, children = stack[-1]
                child = next(children, None)
                if child is None:
                    self.order.append(node)
                    done.add(node)
                    del active[node]
                    stack.pop()
                elif child in active:
                    cycle = [n for n, _ in stack[active[child]:]] + [child]
                    self.errors.append("needs cycle: " + " -> ".join(cycle))
                elif child in records and child not in done:
                    active[child] = len(stack)
                    stack.append((child, iter(self.forward[child])))

    def unmet(self, records):
        counts = {}
        for ref in self.order:
            value = 0
            for t in self.forward[ref]:
                target = records.get(t)
                if target is None or counts.get(t) is None:
                    value = None
                    break
                state = target.fields.get("state")
                if state is None or target.name not in SATISFIED_STATES:
                    value = None
                    break
                value += state not in SATISFIED_STATES[target.name]
            counts[ref] = value
            if value is None and not records[ref].archived:
                note(f"{ref}: _unmet unknown; check reachable needs, states and SATISFIED_STATES")
        return counts


def walk(edges, origin):
    seen, queue = {origin}, deque([(origin, 0)])
    while queue:
        ref, depth = queue.popleft()
        for other in edges.get(ref, ()):
            if other not in seen:
                seen.add(other)
                queue.append((other, depth + 1))
                yield other, depth + 1


def check(staged_view, documents, problems, warnings, git, base="HEAD"):
    records, archived, contents, origin, folders = {}, {}, {}, {}, defaultdict(set)
    for rel, content in documents.items():
        if not (is_record(rel) or is_archive(rel)):
            continue
        folders[name_of(folder_of(rel))].add(rel if is_archive(rel) else folder_of(rel))
        if is_record(rel):
            r = Record(rel, content)
            records[r.ref] = r
            problems.extend(r.errors)
            continue
        try:
            found = stored(rel, content)
        except ValueError as error:
            problems.append(str(error))
            continue
        for path, body in found.items():
            r = Record(path, body)
            archived[r.ref], contents[r.ref], origin[r.ref] = r, body, rel
    problems.extend(conflicts(folders, records, archived))
    problems.extend(Network({**archived, **records}).errors)
    if not staged_view:
        return

    def changed(kind, test=is_record):
        args = ["diff", "--cached", "--no-renames", "--name-only", "-z", "--diff-filter=" + kind]
        result = git(*args, *([base] if base != "HEAD" else []))
        if result.returncode:
            problems.append(f"cannot inspect staged {kind} paths: {result.stderr.strip()}")
            return []
        return [p for p in result.stdout.split("\0") if test(p)]

    def committed(rel):
        result = git("show", f"{base}:{rel}")
        if result.returncode:
            problems.append(f"cannot read {base}:{rel}: {result.stderr.strip()}")
            return None
        return result.stdout

    # Archiving is a pure move of committed content, and archived content is frozen.
    previous = {}
    for rel in changed("DMT", is_archive):
        try:
            previous.update((ref_of(p), (p, body)) for p, body in stored(rel, committed(rel) or "").items())
        except ValueError:
            pass  # a malformed committed archive was reported when it was committed
    rewritten = set(changed("AMT", is_archive))
    deleted = changed("D")
    for rel in deleted:
        ref = ref_of(rel)
        if ref in contents:
            if ref not in previous and contents[ref] != committed(rel):
                problems.append(f"archived record differs from its committed version: {rel}")
        # A moved collection keeps each record, unchanged, at its new path.
        elif not (ref in records and records[ref].rel != rel
                  and documents[records[ref].rel] == committed(rel)):
            problems.append(f"committed record deleted: {rel} (close it by state or use the archive command; do not delete)")
    for ref in sorted(contents.keys() - previous.keys() - {ref_of(rel) for rel in deleted}):
        if origin[ref] in rewritten:
            problems.append(f"archive block has no committed record deleted in this save: {archived[ref].rel}")
    for ref, (path, body) in sorted(previous.items()):
        if ref in contents:
            if contents[ref] != body:
                problems.append(f"archived record altered: {path}; archived content is frozen")
        elif ref not in records:
            problems.append(f"archived record removed: {path} (restore it or keep it archived)")
        else:
            old = Record(path, body).events
            if old and records[ref].events[-len(old):] != old:
                problems.append(f"earlier governed entry altered or removed in {records[ref].rel}: prepend a new entry")
    for rel in changed("MT"):
        r = records.get(ref_of(rel))
        if r is None:
            continue
        previous = git("show", f"{base}:{rel}")
        if previous.returncode:
            problems.append(f"cannot read {base}:{rel}: {previous.stderr.strip()}")
            continue
        old = Record(rel, previous.stdout).events
        if old and r.events[-len(old):] != old:
            problems.append(f"earlier governed entry altered or removed in {rel}: prepend a new entry")


def tsv(columns, rows):
    def cell(value):
        if isinstance(value, float):
            text = str(value)
            return text[:-2] if text.endswith(".0") else text
        return value

    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\r\n")

    def output(values):
        # Let CSV quote both CR and LF inside cells; normalise only the record
        # ending, so ordinary TSV lines also work with shell text tools.
        writer.writerow(values)
        sys.stdout.write(buffer.getvalue()[:-2] + "\n")
        buffer.seek(0)
        buffer.truncate(0)

    output(columns)
    for row in rows:
        output([cell(value) for value in row])


def graph(records, ref):
    if ref not in records:
        die(f"unknown record: {ref}")
    net = Network(records)

    def row(direction, depth, key):
        r = records.get(key)
        return direction, depth, key, (r.fields.get("state") if r else None), (r.title if r else None)

    def rows():
        yield row("origin", 0, ref)
        for label, edges in (("prerequisites", net.forward), ("dependants", net.back)):
            for key, depth in walk(edges, ref):
                yield row(label, depth, key)

    tsv(("direction", "depth", "id", "state", "title"), rows())
    for error in net.errors:
        note(error)


_CORE = None


def core():
    # Read-only commands must not leave an import cache in an installed brain.
    global _CORE
    if _CORE is not None:
        return _CORE
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location("_collection_core", Path(__file__).with_name(CORE_HELPER))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CORE = module
        return module
    finally:
        sys.dont_write_bytecode = previous


def head():
    error = core().repository_error()
    if error:
        die(error)
    result = core().git("rev-parse", "--verify", "--quiet", "HEAD")
    if result.returncode not in (0, 1):
        die(f"cannot inspect HEAD: {result.stderr.strip()}")
    return result.stdout.strip()


def quote(name):
    return "[" + name + "]"


def natural(left, right):
    def key(value):
        # Compare digit runs without converting arbitrarily long integers.
        return [(1, len(p.lstrip("0")), p.lstrip("0")) if i % 2 else (0, p)
                for i, p in enumerate(re.split(r"([0-9]+)", value.casefold()))]

    a, b = key(left), key(right)
    return (a > b) - (a < b)


def sql_name(value):
    """SQLite identifier comparison folds ASCII letters only."""
    return value.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))


def mapped_name(value, collection=False):
    mapped = re.sub(r"[^A-Za-z0-9_]", "_", value)
    return "_" + mapped if collection and mapped[:1].isdigit() else mapped


def schema(names, records):
    tables, relations = {}, {n: n for n in SYSTEM}
    for name in sorted(names):
        mapped = mapped_name(name, collection=True)
        folded = sql_name(mapped)
        if folded in relations or folded.startswith("sqlite_"):
            other = relations.get(folded, "sqlite_*")
            die(f"SQL relation name collision: {name!r} maps to {mapped!r}, reserved or used by {other!r}")
        relations[folded] = name
        numeric = {k.lower() for k in NUMERIC_FIELDS.get(name, ())}
        keys = ["state"] + sorted(GOVERNED_FIELDS) + sorted(NUMERIC_FIELDS.get(name, ()))
        for r in records.values():
            if r.name == name and not r.archived:
                keys.extend(r.lines[i][2:].split(":", 1)[0] for i in r.at.values())
        spellings, columns = {}, {}
        tables[name] = dict(META)
        for k in keys:
            if not re.fullmatch(FIELD, k):
                die(f"invalid configured field name {k!r} in {name!r}")
            if k.lower() in spellings:
                previous = spellings[k.lower()]
                mapped = mapped_name(k)
                if sql_name(mapped_name(previous)) != sql_name(mapped):
                    die(f"SQL field name collision: {k!r} and {previous!r} map to {mapped!r} in {name!r}")
                continue
            mapped = mapped_name(k)
            folded = sql_name(mapped)
            if folded in columns:
                die(f"SQL field name collision: {k!r} and {columns[folded]!r} map to {mapped!r} in {name!r}")
            spellings[k.lower()] = k
            columns[folded] = k
        for key, spelling in sorted(spellings.items()):
            tables[name][spelling] = "REAL" if key in numeric else "TEXT"
    return tables


def sql_value(r, key, typ):
    value = r.fields.get(key.lower())
    if value is None or typ != "REAL":
        return value
    match = NUMBER.match(value)
    if match:
        number = float(match[0])
        if math.isfinite(number):
            return number
    note(f"{r.ref}: invalid numeric {key}={value!r}; using NULL")
    return None


def fill(db, tables, records):
    net = Network(records)
    for error in net.errors:
        note(error)
    unmet = net.unmet(records)
    for name, cols in tables.items():
        definition = ", ".join(quote(mapped_name(k)) + " " + t for k, t in cols.items())
        db.execute(f"CREATE TABLE {quote(mapped_name(name, collection=True))} ({definition}) WITHOUT ROWID")
    for name, cols in SYSTEM.items():
        definition = ", ".join(k + (" INTEGER" if k == "depth" else " TEXT") for k in cols)
        db.execute(f"CREATE TABLE {name} ({definition})")
    for ref, r in records.items():
        if not r.archived:
            cols = tables[r.name]
            values = [r.id, ref, r.title, unmet[ref]]
            values.extend(sql_value(r, k, t) for k, t in cols.items() if k not in META)
            db.execute(f"INSERT INTO {quote(mapped_name(r.name, collection=True))} VALUES ({','.join('?' for _ in values)})", values)
        db.executemany("INSERT INTO needs VALUES (?,?)", ((ref, n) for n in r.needs))
    public_names = {sql_name(mapped_name(name, collection=True)) for name in tables}
    for name, col in [(name, cols[0]) for name, cols in SYSTEM.items()] + [("reach", "need")]:
        index = name + "_" + col
        while sql_name(index) in public_names:
            index += "_"
        db.execute(f"CREATE INDEX {quote(index)} ON {name} ({col})")
    db.commit()


def restrict(db, sqlite, tables, sql="", reads=None):
    if not all(callable(getattr(db, method, None)) for method in ("set_authorizer", "set_progress_handler")):
        die("query requires SQLite authorizer and progress-handler support")
    allowed = {sql_name(mapped_name(name, collection=True)) for name in tables} | set(SYSTEM)
    functions = set("""abs avg ceil ceiling coalesce count cume_dist date datetime
        dense_rank first_value floor glob group_concat hex ifnull iif instr julianday
        lag last_value lead length like likelihood likely lower ltrim max min nth_value
        ntile nullif percent_rank rank replace round row_number rtrim sign strftime
        substr substring sum time total trim typeof unicode unixepoch unlikely upper""".split())

    def authorize(action, arg1, arg2, database, source):
        arg1, database = sql_name(arg1 or ""), sql_name(database or "")
        if action == sqlite.SQLITE_READ and reads is not None:
            reads.add(arg1)
        # Columnless reads with no database include CTE counts and some
        # table-valued-function cardinalities. Column reads remain checked
        # separately; SQLite's schema names are denied even for counts.
        cte_count = (not database and arg2 == "" and bool(arg1)
                     and not arg1.startswith("sqlite_"))
        ok = (action in (sqlite.SQLITE_SELECT, getattr(sqlite, "SQLITE_RECURSIVE", -1))
              or (action == sqlite.SQLITE_READ and database in ("", "main") and arg1 in allowed)
              or (action == sqlite.SQLITE_READ and cte_count)
              or (action == sqlite.SQLITE_FUNCTION and (arg2 or "").lower() in functions))
        return sqlite.SQLITE_OK if ok else sqlite.SQLITE_DENY

    db.execute("PRAGMA query_only=ON")
    if hasattr(db, "setconfig") and hasattr(sqlite, "SQLITE_DBCONFIG_DQS_DML"):
        db.setconfig(sqlite.SQLITE_DBCONFIG_DQS_DML, False)
    elif '"' in sql:
        note("SQLite may treat a double-quoted unknown identifier as text on this runtime")
    if hasattr(db, "setlimit"):
        for key, limit in (("LENGTH", 4_000_000), ("SQL_LENGTH", 65536), ("EXPR_DEPTH", 100),
                           ("COMPOUND_SELECT", 50), ("LIKE_PATTERN_LENGTH", 1024), ("ATTACHED", 0)):
            cat = getattr(sqlite, "SQLITE_LIMIT_" + key, None)
            if cat is not None:
                db.setlimit(cat, limit)
    ticks = 0

    def progress():
        nonlocal ticks
        ticks += 1
        return ticks > 10000

    db.set_authorizer(authorize)
    db.set_progress_handler(progress, 1000)
    return lambda: ticks > 10000


def query(names, records, name, sql):
    try:
        import sqlite3
    except ImportError:
        die("query requires the optional Python sqlite3 module")
    if name not in names:
        die(f"unknown collection: {name}")
    tables = schema(names, records)
    if sql == "-":
        sql = sys.stdin.read(65537)
    if sql is not None and len(sql.encode("utf-8")) > 65536:
        die("SQL exceeds 65536 bytes")
    supplied_sql = sql or ""
    if sql is None or not sql.strip():
        for n, cols in tables.items():
            note(mapped_name(n, collection=True) + " (" + ", ".join(mapped_name(k) + " " + t for k, t in cols.items()) + ")")
        for n, cols in SYSTEM.items():
            note(n + "(" + ", ".join(cols) + ")")
        note("Use query NAME 'SELECT ...', COLLATE natural_id; NULL prints empty.")
        count = sum(r.archived and r.name == name for r in records.values())
        if count:
            note(f"{count} archived records in {location(names, name)}{ARCHIVE_SUFFIX}: not table rows; needs, reach, _unmet and graph include them.")
        sql = f"SELECT _id, state, _title FROM {quote(mapped_name(name, collection=True))} ORDER BY _id"

    db = sqlite3.connect(":memory:")
    try:
        db.execute("PRAGMA temp_store=MEMORY")
        db.create_collation("natural_id", natural)
        fill(db, tables, records)
        reads = set()
        exhausted = restrict(db, sqlite3, tables, supplied_sql, reads)
        try:
            # Let SQLite resolve references; never parse SQL ourselves. Ordinary
            # field queries need no potentially quadratic transitive closure.
            db.execute("EXPLAIN " + sql).close()
            if "reach" in reads:
                # Python <3.11 does not support None to remove the authorizer.
                # Only our fixed inserts run while it permits writes.
                db.set_authorizer(lambda *args: sqlite3.SQLITE_OK)
                db.set_progress_handler(None, 0)
                db.execute("PRAGMA query_only=OFF")
                edges = {ref: r.needs for ref, r in records.items()}
                for ref in records:
                    db.executemany("INSERT INTO reach VALUES (?,?,?)",
                                   ((ref, n, d) for n, d in walk(edges, ref)))
                db.commit()
                exhausted = restrict(db, sqlite3, tables)
            cur = db.execute(sql)
            if cur.description is None:
                die("expected a single result-producing statement")
            tsv([col[0] for col in cur.description], cur)
        except sqlite3.Error:
            if exhausted():
                die("SQL execution budget exceeded")
            raise
    except (sqlite3.Error, sqlite3.Warning) as error:
        die(f"SQLite: {error}")
    finally:
        db.close()


def location(folders, name):
    if name not in folders:
        die(f"unknown collection: {name}")
    place = min(folders[name])
    return folder_of(place) if is_archive(place) else place


def refuse(ref, reason):
    note(f"REFUSED: {ref}: {reason}")


def archive(folders, records, name, items):
    head()
    folder = location(folders, name)
    path = ROOT / (folder + ARCHIVE_SUFFIX)
    refused = 0
    for item in dict.fromkeys(items):
        ref = name + "/" + item
        reason = None
        if ref in records and records[ref].archived:
            reason = "already archived"
        elif ref not in records:
            reason = "no such active record"
        else:
            rel = records[ref].rel
            data = (ROOT / rel).read_bytes()
            committed = core().git("show", f"HEAD:{rel}", binary=True)
            if committed.returncode or committed.stdout.replace(b"\r\n", b"\n") != data.replace(b"\r\n", b"\n"):
                reason = "uncommitted or changed since commit; save it first"
            elif MARKER.search(data.decode("utf-8")):
                reason = "content contains archive-marker text (<!-- archived:)"
        if reason:
            refuse(ref, reason)
            refused += 1
            continue
        if not path.exists():
            path.write_bytes(ARCHIVE_HEADER.format(name).encode("utf-8"))
        with open(path, "ab") as stream:
            stream.write(f"<!-- archived: {item} {date.today().isoformat()} -->\n".encode("utf-8")
                         + data + f"\n<!-- end archived: {item} -->\n".encode("utf-8"))
        (ROOT / rel).unlink()
        print(f"archived {ref}")
    if refused:
        sys.exit(1)


def restore(folders, records, name, item):
    folder = location(folders, name)
    ref, rel = name + "/" + item, f"{folder}/{item}.md"
    path = ROOT / (folder + ARCHIVE_SUFFIX)
    text = path.read_bytes().decode("utf-8") if path.exists() else ""
    blocks = unpack(text)
    if ref in records and not records[ref].archived:
        refuse(ref, f"active record exists: {records[ref].rel}")
        sys.exit(1)
    if item not in blocks:
        refuse(ref, "not archived")
        sys.exit(1)
    content, start, end = blocks[item]
    (ROOT / folder).mkdir(exist_ok=True)
    with open(ROOT / rel, "xb") as stream:
        stream.write(content.encode("utf-8"))
    path.write_bytes((text[:start] + text[end:]).encode("utf-8"))
    print(f"restored {ref}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                     allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    q = sub.add_parser("query")
    q.add_argument("name")
    q.add_argument("sql", nargs="?")
    sub.add_parser("graph").add_argument("ref")
    a = sub.add_parser("archive")
    a.add_argument("name")
    a.add_argument("ids", nargs="+")
    r = sub.add_parser("restore")
    r.add_argument("name")
    r.add_argument("id")
    if len(sys.argv) == 1:
        parser.print_help()
        return
    args = parser.parse_args()
    revision = head() if args.command == "query" else None
    before, records = snapshot()
    errors = [err for r in records.values() if not r.archived for err in r.errors]
    if errors:
        die("\n".join(errors))
    if args.command == "graph":
        graph(records, args.ref)
    elif args.command == "archive":
        archive(before[0], records, args.name, args.ids)
    elif args.command == "restore":
        restore(before[0], records, args.name, args.id)
    else:
        if head() != revision:
            die("HEAD changed during snapshot")
        query(before[0], records, args.name, args.sql)


if __name__ == "__main__":
    sys.stdout.reconfigure(newline="")
    try:
        main()
    except (ValueError, OSError) as error:
        note(f"PROBLEM: {error}")
        sys.exit(1)
