#!/usr/bin/env python3
"""Memory checks and cooperative writer locking.

check / check --staged: validate working tree / prospective commit; read-only.
PROBLEMs fail; warnings don't. A pass proves structure, not completeness.
lock <name> / unlock <label>: acquisition-specific ownership, not enforcement.
unlock --force requires user approval. No cross-clone coordination.
commit [--label <label>] -m <message> [-m <paragraph>...] [--amend]: gated
commit of the index. Refuses under a lock unless the label is its owner's, and
on any check --staged PROBLEM; commits without -a; then runs check (a PROBLEM
then exits non-zero and keeps the lock). --amend needs the label and recommits
only a commit recorded as made by this acquisition; it keeps
the message unless -m is given and never opens an editor. Never releases the
lock. Cooperative: raw Git bypasses it; a host grant for
"python3 tools/minibrain.py *" also permits commits.

Normal dedicated Git working copy. Configuration and limits below.
Managed Markdown: root *.md, topics/**/*.md, spaces/**/*.md;
ordinary UTF-8 files, no symlinks.

Links: root-relative; [[spaces/X]] resolves to X.md or X/index.md under spaces/,
never both. Explicit .md = exact file; bare names = legacy non-space targets.
Register spaces once: top-level in MAP_FILE, children under parent ## Spaces,
using leading "- [[path]]" bullets. Assets aren't registered spaces.

Staged memory changes—including space assets—require staged CHANGELOG.md.
A staged path edited again after staging is a PROBLEM in check --staged.
Relevant .gitignore files must match the index, except CRLF/LF endings.

With tools/collection.py installed, check also runs its collection checks and
keeps record ids out of the bare-name link namespace. Staged checks require the
extension to match its indexed bytes. Collection folders may not contain root
control files, even before the extension is installed.

Not checked: factual truth, complete capture, status/history order, section
anchors, ordinary Markdown links, hidden skills or attachment retention/privacy.
"""

from pathlib import Path, PurePosixPath
import datetime
import importlib.util
import json
import os
import re
import secrets
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = "MAP.md"
REQUIRED_FILES = ("AGENTS.md", "MEMORY.md", "CHANGELOG.md", MAP_FILE)
MANAGED_DIRS = {"topics", "spaces"}  # legacy topics stay supported; root *.md is managed too
RESERVED = {"AGENTS", "CLAUDE", "MEMORY", "CHANGELOG", Path(MAP_FILE).stem, "README"}
ROOT_ONLY = {"AGENTS.md", "CLAUDE.md", "MEMORY.md", "CHANGELOG.md", MAP_FILE}
MEMORY_REVIEW_LINES = 150  # advisory reflection threshold, not a cap
THREADS_MAX = 12
THREAD_SOFT_CHARS = 400     # warning only: line count alone hides long bullets' reading cost
REQUIRE_LOCAL_REMOTES = False  # True: every Git remote must be an absolute filesystem path
LOCK = ROOT / ".git" / "kb-writer.lock"  # Keep compatible with older installed helpers.
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")  # lock takes a bare writer name; the tool issues the label

# Validate file targets, not section anchors or ordinary Markdown/asset links.
WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def git(*args, input=None, binary=False):
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                              encoding=None if binary else "utf-8",
                              errors=None if binary else "surrogateescape", env=env, input=input)
    except OSError as error:
        message = f"Git unavailable: {error}"
        return subprocess.CompletedProcess(args, 127, b"" if binary else "",
                                           message.encode() if binary else message)


def repository_error():
    """Fail explicitly instead of checking or locking a parent repository."""
    redirected = sorted(name for name in ("GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE",
                                          "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE")
                        if name in os.environ)
    if redirected:
        return "Git repository/index overrides are unsupported: " + ", ".join(redirected)
    if not (ROOT / ".git").is_dir() or (ROOT / ".git").is_symlink():
        return "requires a normal dedicated Git working copy (.git directory); worktrees are unsupported"
    top = git("rev-parse", "--show-toplevel")
    if top.returncode:
        return f"cannot inspect Git root: {top.stderr.strip()}"
    if Path(top.stdout.strip()).resolve() != ROOT.resolve():
        return "Git working-copy root does not match the installed helper's root"
    directory = git("rev-parse", "--absolute-git-dir")
    if directory.returncode or Path(directory.stdout.strip()).resolve() != (ROOT / ".git").resolve():
        return "Git directory does not match the installed helper's dedicated working copy"
    index = ROOT / ".git" / "index"
    if index.is_symlink() or (index.exists() and not index.is_file()):
        return "Git index is not an ordinary file in the dedicated working copy"
    if LOCK.is_symlink() or (LOCK.exists() and not LOCK.is_dir()):
        return "writer lock path is not an ordinary directory; preserve it and report"
    return None


def index_entries(problems, staged=False):
    """Index entries define prospective content, including repository ignore rules."""
    result = git("ls-files", "--stage", "-v", "-z")
    if result.returncode:
        problems.append(f"cannot list index: {result.stderr.strip()}")
        return {}
    entries = {}
    for record in filter(None, result.stdout.split("\0")):
        try:
            header, rel = record.split("\t", 1)
            tag, mode, oid, stage = header.split()
        except ValueError:
            problems.append("cannot parse Git index")
            return {}
        # Lowercase = assume-unchanged; S = skip-worktree. Both can hide edits.
        if tag.islower() or tag == "S":
            problems.append(
                f"Git flags may hide unsaved changes: {rel}"
            )
        if stage != "0":
            problems.append(f"unmerged index entry: {rel}")
            continue
        entries[rel] = (mode, oid)
    if staged:
        paths = []
        for visibility, status in (("visible", "A"), ("invisible", "A"), ("invisible", "D")):
            result = git("diff", "--cached", "--name-only", "--no-renames", "-z",
                         f"--ita-{visibility}-in-index", f"--diff-filter={status}")
            if result.returncode:
                problems.append(f"cannot inspect prospective paths: {result.stderr.strip()}")
                return {}
            paths.append(set(filter(None, result.stdout.split("\0"))))
        # Intent-to-add entries are not part of the prospective commit.
        for rel in (paths[0] - paths[1]) | paths[2]:
            entries.pop(rel, None)
    for rel, (mode, _) in entries.items():
        if rel in MANAGED_DIRS or (Path(rel).parts[0] in MANAGED_DIRS and mode not in ("100644", "100755")):
            problems.append(f"managed path is not an ordinary directory or regular file in index: {rel}")
        if staged:
            check_space_path(rel, problems)
            check_collection_control_path(rel, problems)
    return entries


def working_markdown(problems):
    files = {relative(p) for p in ROOT.glob("*.md")}
    def walk_error(error):
        problems.append(f"cannot inspect managed directory: {error}")
    # Check all names, not only records: host entrypoints are case-insensitive
    # and nested controls remain dangerous even outside the queried layout.
    for folder in ROOT.glob("collection.*"):
        if folder.is_dir() and not folder.is_symlink():
            for current, dirs, names in os.walk(folder, followlinks=False, onerror=walk_error):
                for name in dirs + names:
                    check_collection_control_path(relative(Path(current) / name), problems)
    for dirname in sorted(MANAGED_DIRS):
        folder = ROOT / dirname
        if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
            problems.append(f"managed path is not an ordinary directory: {dirname}")
            continue
        if not folder.exists():
            continue
        for current, dirs, names in os.walk(folder, followlinks=False, onerror=walk_error):
            for name in dirs[:]:
                path = Path(current) / name
                if path.is_symlink():
                    problems.append(f"managed path is not an ordinary directory: {relative(path)}")
                    dirs.remove(name)
                elif name.endswith(".md"):
                    files.add(relative(path))  # named as Markdown but not a regular file
            for name in names:
                path = Path(current) / name
                if dirname == "spaces":
                    check_space_path(relative(path), problems)
                    try:
                        if not stat.S_ISREG(path.lstat().st_mode):
                            problems.append(f"space material is not a regular file: {relative(path)}")
                    except OSError as error:
                        problems.append(f"cannot inspect space material {relative(path)}: {error}")
                if name.endswith(".md"):
                    files.add(relative(path))
    return files


def regular_working_file(rel):
    """Reject links/special files and linked parents before opening Markdown."""
    path = ROOT
    parts = Path(rel).parts
    for i, part in enumerate(parts):
        path /= part
        mode = path.lstat().st_mode
        if i < len(parts) - 1:
            if not stat.S_ISDIR(mode):
                return False
        elif not stat.S_ISREG(mode):
            return False
    return True


def staged_ignore_rules_match(paths, entries, problems):
    """check-ignore reads the working tree: refuse mixed policy, including untracked rules."""
    ignore_files = {str(parent / ".gitignore")
                    for rel in paths for parent in PurePosixPath(rel).parents}
    matches = True
    for rel in sorted(ignore_files):
        entry = entries.get(rel)
        try:
            try:
                (ROOT / rel).lstat()
                present = True
            except FileNotFoundError:
                present = False
            if not present:
                if entry is None:
                    continue
            elif regular_working_file(rel) and entry and entry[0] in ("100644", "100755"):
                working = (ROOT / rel).read_bytes()
                result = git("cat-file", "blob", entry[1], binary=True)
                if result.returncode:
                    raise OSError(result.stderr.decode("utf-8", "replace").strip())
                # Git accepts CRLF rules. Do not apply clean filters or normalize
                # lone CR bytes: either could mask different actual ignore rules.
                if working.replace(b"\r\n", b"\n") == result.stdout.replace(b"\r\n", b"\n"):
                    continue
            detail = ("must match the index as a regular file except CRLF/LF endings (or be absent from both); "
                      "stage or restore the intended ignore policy")
        except OSError as error:
            detail = str(error)
        problems.append(f"cannot validate staged ignore rules: {rel}: {detail}")
        matches = False
    return matches


def load_markdown(staged, problems, records=None):
    entries = index_entries(problems, staged)
    indexed_markdown = {rel for rel in entries if rel.endswith(".md") and
                        (is_managed_path(rel) or (records and records.is_record(rel))
                         or not any(part.startswith(".") for part in Path(rel).parts))}
    paths = indexed_markdown if staged else working_markdown(problems)
    if not staged:
        if records:
            paths.update(records.inventory()[1])
        # Supporting targets are tracked, present Markdown outside hidden folders.
        paths.update(rel for rel in indexed_markdown if os.path.lexists(ROOT / rel))
    documents = {}
    for rel in sorted(paths):
        try:
            if staged:
                mode, oid = entries[rel]
                if mode not in ("100644", "100755"):
                    problems.append(f"Markdown is not a regular file in index: {rel}")
                    continue
                result = git("cat-file", "blob", oid)
                if result.returncode:
                    raise OSError(result.stderr.strip())
                # Paths may contain arbitrary bytes; document content must be UTF-8.
                content = result.stdout.encode("utf-8", "surrogateescape").decode("utf-8")
            else:
                if not regular_working_file(rel):
                    problems.append(f"Markdown is not a regular file: {rel}")
                    continue
                content = (ROOT / rel).read_text(encoding="utf-8")
            documents[rel] = content
        except (OSError, UnicodeError) as error:
            problems.append(f"cannot read Markdown {rel}: {error}")
    durable = {rel for rel in paths if is_managed_path(rel) or (records and records.is_record(rel))}
    if durable and staged and not staged_ignore_rules_match(durable, entries, problems):
        return None  # Later Git operations could reopen a rejected special file.
    if durable:
        ignored = git("check-ignore", "--no-index", "-z", "--stdin",
                      input="\0".join(sorted(durable)) + "\0")
        if ignored.returncode not in (0, 1):
            problems.append(f"cannot verify ignore rules: {ignored.stderr.strip()}")
        else:
            problems.extend(f"managed Markdown is ignored and may disappear on clone: {rel}"
                            for rel in ignored.stdout.split("\0") if rel)
    return documents


def relative(path):
    return path.relative_to(ROOT).as_posix()


def status_paths():
    result = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    if result.returncode != 0:
        return set(), result.stderr.strip() or "git status failed"
    records = result.stdout.split("\0")
    if records and records[-1] == "":
        records.pop()
    paths, index = set(), 0
    while index < len(records):
        record = records[index]
        if len(record) < 4:
            return set(), "could not parse git status output"
        status = record[:2]
        paths.add(record[3:])
        index += 1
        if "R" in status or "C" in status:
            if index >= len(records):
                return set(), "could not parse renamed path from git status"
            paths.add(records[index])
            index += 1
    return paths, None


def staged_paths(base="HEAD"):
    """Paths the prospective commit changes against base; HEAD^ while amending, so the gate sees the whole commit."""
    result = git("diff", "--cached", "--name-status", "-z", "-M", *([base] if base != "HEAD" else []))
    if result.returncode != 0:
        return set(), result.stderr.strip() or "git diff --cached failed"
    records = result.stdout.split("\0")
    if records and records[-1] == "":
        records.pop()
    paths, index = set(), 0
    while index < len(records):
        status = records[index]
        index += 1
        count = 2 if status.startswith(("R", "C")) else 1
        if index + count > len(records):
            return set(), "could not parse git diff --cached output"
        paths.update(records[index:index + count])
        index += count
    return paths, None


def is_managed_path(path):
    candidate = Path(path)
    if candidate.suffix != ".md":
        return False
    return len(candidate.parts) == 1 or candidate.parts[0] in MANAGED_DIRS


def is_space_path(rel):
    return PurePosixPath(rel).parts[0] == "spaces"


def is_space_asset(rel):
    return is_space_path(rel) and "assets" in PurePosixPath(rel).parts[1:-1]


def check_collection_control_path(rel, problems):
    path = PurePosixPath(rel)
    if (len(path.parts) > 1 and path.parts[0].startswith("collection.")
            and path.name.casefold() in {name.casefold() for name in ROOT_ONLY}):
        problems.append(f"root-only control file inside a collection: {rel}; use a non-entrypoint name")


def check_space_path(rel, problems):
    """Path-only guards run before filtering Markdown, including attachments."""
    if not is_space_path(rel):
        return
    path = PurePosixPath(rel)
    if path.name.casefold() in {name.casefold() for name in ROOT_ONLY}:
        problems.append(f"root-only control file inside a space: {rel}; use a non-entrypoint name")
    parts = path.parts
    # Keep root-control protection above, but do not interpret quoted asset trees
    # as live space structure. Include the first assets segment to refuse a space
    # named assets directly inside a spaces namespace.
    if is_space_asset(rel):
        parts = parts[:parts.index("assets", 1) + 1]
    reserved = any(parts[i - 1] == "spaces" and part.casefold() in
                   {"assets", "spaces", "assets.md", "spaces.md", "index.md"}
                   for i, part in enumerate(parts[1:], 1))
    if not is_space_asset(rel):
        name = path.parent.name if path.name == "index.md" else path.stem
        reserved |= name.casefold() in {"assets", "spaces"}
    if reserved:
        problems.append(f"reserved space name in {rel}; assets/spaces are structure, "
                        "index.md belongs only to a folder space; choose a descriptive name")


def space_registry(rel):
    """The containing space owns discovery; namespaces themselves are not spaces."""
    path = PurePosixPath(rel)
    parent = path.parent.parent if path.name == "index.md" else path.parent
    if parent.name == "spaces":
        parent = parent.parent
    return MAP_FILE if parent == PurePosixPath(".") else str(parent / "index.md")


def resolve_link(target, documents, by_basename):
    """Exact .md paths, qualified logical spaces, or legacy extensionless names."""
    target = target.strip()
    # Do not normalise ambiguous/outside-root spellings into an accepted target.
    if any(part in ("", ".", "..") for part in target.split("/")):
        return None, "invalid root-relative"
    if target.endswith(".md"):
        return (target, None) if target in documents else (None, "broken")
    if "/" in target:
        candidates = [target + ".md"]
        index = target + "/index.md"
        if is_space_path(index) and not is_space_asset(index):
            candidates.append(index)
        present = [rel for rel in candidates if rel in documents]
        if len(present) == 1:
            return present[0], None
        return None, "ambiguous" if present else "broken"
    found = by_basename.get(target, [])
    legacy = [rel for rel in found if not is_space_path(rel)]
    if target in RESERVED and target + ".md" in legacy:
        return target + ".md", None
    if len(legacy) == 1:
        return legacy[0], None
    if legacy:
        return None, "ambiguous"
    if found:
        return None, "ambiguous" if len(found) > 1 else "unqualified space (needs a qualified path)"
    return None, "broken"


def unfenced_lines(content):
    """Exclude fenced examples without joining surrounding text."""
    fence = None
    for line in content.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if (marker and marker.group(1)[0] == fence[0] and
                    len(marker.group(1)) >= len(fence) and not marker.group(2).strip()):
                fence = None
            yield ""
            continue
        if marker:
            fence = marker.group(1)
            yield ""
            continue
        yield line


def registration_targets(content, nested=False):
    """Leading wikilinks register spaces: all MAP sections, only ## Spaces in parents.

    Fragments/labels still register; use ordinary Markdown links for other navigation.
    Fenced examples are excluded.
    """
    targets, sections = [], 0
    active = not nested
    for line in unfenced_lines(content):
        if nested and re.match(r"^#{1,2} ", line):
            active = bool(re.fullmatch(r"## Spaces[ \t]*", line))
            sections += int(active)
        if active and line.startswith("- ") and (match := WIKILINK.match(line[2:])):
            targets.append(match.group(1).strip())
    return targets, sections


def lock_meta():
    """The held lock's metadata, or {} when it is missing or names no usable owner."""
    try:
        path = LOCK / "meta.json"
        if not stat.S_ISREG(path.lstat().st_mode):
            return {}
        with path.open(encoding="utf-8") as source:
            meta = json.load(source)
    except (OSError, ValueError):
        return {}
    if not isinstance(meta, dict) or not isinstance(meta.get("owner"), str) or not meta["owner"]:
        return {}
    return meta


def shown_head(meta):
    """The acquisition HEAD for messages: abbreviated, since the lock stores the full hash."""
    head = meta.get("head") or ""
    return head[:12] if isinstance(head, str) and head else "?"


def release_lock():
    try:
        items = list(LOCK.iterdir())
        if any(item.name != "meta.json" or not stat.S_ISREG(item.lstat().st_mode) for item in items):
            print("REFUSED: unexpected lock contents; preserve them and ask the user to resolve")
            return False
        for item in items:
            item.unlink()
        LOCK.rmdir()
        return True
    except OSError as error:
        print(f"REFUSED: cannot finish lock release ({error}); preserve remaining state and report")
        return False


def extension(staged=False):
    """tools/collection.py when installed: an optional extension whose checks run only then."""
    path = ROOT / "tools" / "collection.py"
    present = os.path.lexists(path)
    content = None
    if staged:
        result = git("ls-files", "--stage", "-z", "--", "tools/collection.py")
        if result.returncode:
            raise ValueError(f"cannot inspect tools/collection.py in index: {result.stderr.strip()}")
        entries = list(filter(None, result.stdout.split("\0")))
        if not present and not entries:
            return None
        mismatch = "tools/collection.py must match the index in presence, regular mode and bytes before staged checks"
        if not present or len(entries) != 1 or not regular_working_file("tools/collection.py"):
            raise ValueError(mismatch)
        mode, oid, stage = entries[0].split("\t", 1)[0].split()
        working_mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        if stage != "0" or mode != working_mode:
            raise ValueError(mismatch)
        content = path.read_bytes()
        blob = git("cat-file", "blob", oid, binary=True)
        if blob.returncode or blob.stdout != content:
            raise ValueError(mismatch)
    if not present:
        return None
    if not regular_working_file("tools/collection.py"):
        raise ValueError("tools/collection.py must be a regular file, with no linked parents")
    spec = importlib.util.spec_from_file_location("collection", path)
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        # Execute precisely the checked bytes, not a possibly stale bytecode cache.
        exec(compile(content if content is not None else path.read_bytes(), str(path), "exec"), module.__dict__)
    finally:
        sys.dont_write_bytecode = previous
    return module


def check(staged_view=False, allow_unborn=False, base="HEAD"):
    error = repository_error()
    if error:
        print(f"PROBLEM: {error}")
        return 1
    problems, warnings = [], []

    if not allow_unborn and git("rev-parse", "--verify", "HEAD").returncode != 0:
        problems.append("no commits yet, or Git is not functioning")

    if REQUIRE_LOCAL_REMOTES:
        remotes = git("remote", "-v")
        if remotes.returncode:
            problems.append(f"cannot inspect remotes: {remotes.stderr.strip()}")
        for line in remotes.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and not parts[1].startswith("/"):
                problems.append(f"remote is not an absolute filesystem path: {line.strip()}")

    if LOCK.is_dir():
        meta = lock_meta()
        if meta:
            warnings.append(
                f"writer lock held by {meta['owner']} since {meta.get('at', '?')} "
                f"(HEAD {shown_head(meta)}) — memory files, staging and commits belong to that "
                "checkpoint until release; if this session did not acquire it, do not touch them"
            )
        else:
            warnings.append("writer lock held but its owner is unreadable — treat it as held and "
                            "report it to the person")

    try:
        records = extension(staged_view)
        documents = load_markdown(staged_view, problems, records)
        record_paths = {rel for rel in (documents or {}) if records and records.is_record(rel)}
    except Exception as error:
        print(f"PROBLEM: cannot load Markdown or tools/collection.py: {error}")
        return 1
    if documents is None:
        for item in problems:
            print("PROBLEM:", item)
        for item in warnings:
            print("warning:", item)
        return 1
    for name in REQUIRED_FILES:
        if name not in documents:
            problems.append(f"{name} missing")

    if "MEMORY.md" in documents:
        memory = documents["MEMORY.md"]
        line_count = len(memory.splitlines())
        if line_count >= MEMORY_REVIEW_LINES:
            warnings.append(
                f"MEMORY.md has {line_count} lines (review threshold: {MEMORY_REVIEW_LINES}); "
                "consider reflect at the next useful boundary — no forced trimming or "
                "repeated review of unchanged content"
            )
        memory = "\n".join(unfenced_lines(memory))
        headings = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^## (.+?)\s*$", memory, re.MULTILINE)]
        seen = {}
        for pos, title in headings:
            seen.setdefault(title, []).append(pos)
        for title, positions in seen.items():
            if len(positions) > 1:
                problems.append(f"MEMORY.md has more than one `## {title}` heading")
        for title in ("Focus", "Open threads"):
            if title not in seen:
                problems.append(f"no exact `## {title}` heading in MEMORY.md")
        if "Focus" in seen and "Open threads" in seen:
            focus_at, threads_at = seen["Focus"][0], seen["Open threads"][0]
            if not focus_at < threads_at:
                problems.append("MEMORY.md headings must be ordered: Focus, then Open threads")
            later = [pos for pos, _ in headings if pos > threads_at]
            block = memory[threads_at:min(later) if later else len(memory)]
            bullets = re.findall(r"^[-*+] .*(?:\n(?![-*+] |## |\s*$).*)*", block, re.MULTILINE)  # an item runs to the next bullet, heading or blank line
            if len(bullets) > THREADS_MAX:
                problems.append(f"MEMORY.md has {len(bullets)} open threads; maximum is {THREADS_MAX}")
            for bullet in bullets:
                if len(bullet) > THREAD_SOFT_CHARS:
                    warnings.append(
                        f"thread over {THREAD_SOFT_CHARS} characters (an index line cites, it does not store): "
                        f"{bullet[:60]}…"
                    )

    managed = {rel: content for rel, content in documents.items() if is_managed_path(rel)}
    canonical = {rel: content for rel, content in managed.items() if not is_space_asset(rel)}
    by_basename = {}
    for rel in documents:
        if rel in record_paths:
            continue  # records are reached by qualified links only, so ids may repeat across collections
        by_basename.setdefault(Path(rel).stem, []).append(rel)
    for basename, paths in sorted(by_basename.items()):
        # Qualified spaces/assets cannot collide with the legacy bare-name namespace.
        legacy = [rel for rel in paths if not is_space_path(rel)]
        if len(legacy) > 1 and basename not in RESERVED:
            problems.append(f"duplicate Markdown basename {basename}.md: {', '.join(legacy)}")
    # Check wikilinks even in fences; space assets and CHANGELOG history are excluded.
    for rel, content in canonical.items():
        if Path(rel).name == "CHANGELOG.md":
            continue
        for match in WIKILINK.finditer(content):
            target = match.group(1).strip()
            _, error = resolve_link(target, documents, by_basename)
            if error:
                problems.append(f"{error} wikilink in {rel}: [[{target}]]")

    if records:
        try:
            # Amend's parent baseline is only for the aggregate changelog gate.
            # Already committed history, including this acquisition's event, is immutable.
            records.check(staged_view, documents, problems, warnings, git, "HEAD")
        except Exception as error:
            problems.append(f"cannot run tools/collection.py checks: {error}")

    for rel in canonical:
        if is_space_path(rel) and PurePosixPath(rel).name == "index.md":
            sibling_note = str(PurePosixPath(rel).parent) + ".md"
            if sibling_note in canonical:
                problems.append(f"space has both note and folder entrypoints: {sibling_note}, {rel}")

    registries = {MAP_FILE} | {rel for rel in canonical
                               if is_space_path(rel) and Path(rel).name == "index.md"}
    registrations = {}
    for registry in sorted(registries):
        if registry not in documents:
            continue
        resolved = []
        targets, sections = registration_targets(documents[registry], registry != MAP_FILE)
        if registry != MAP_FILE and sections > 1:
            problems.append(f"multiple active ## Spaces sections in {registry}")
        for target in targets:
            rel, error = resolve_link(target, documents, by_basename)
            if error:
                continue  # link diagnostics above retain the actual invalid spelling
            if is_space_path(rel) and not is_space_asset(rel):
                if space_registry(rel) != registry:
                    problems.append(f"space registered outside its parent index {registry}: {rel}")
                resolved.append(rel)
            elif registry != MAP_FILE:
                problems.append(f"registry entry is not a direct child space in {registry}: {rel}")
        registrations[registry] = resolved
    map_structure = "\n".join(unfenced_lines(documents.get(MAP_FILE, "")))
    for rel in canonical:
        if is_space_path(rel):
            registry = space_registry(rel)
            if registry not in documents:
                problems.append(f"space missing parent index {registry}: {rel}")
                continue
            count = registrations.get(registry, []).count(rel)
        else:
            if Path(rel).stem in RESERVED or MAP_FILE not in documents:
                continue
            registry = MAP_FILE
            # Retain the original exact spelling: section/display links are navigation,
            # not additional legacy registrations.
            basename = re.escape(Path(rel).stem)
            count = len(re.findall(rf"^- \[\[{basename}\]\]", map_structure, re.MULTILINE))
        kind = "space" if is_space_path(rel) else "topic"
        if count == 0:
            problems.append(f"{kind} not registered in {registry}: {rel}")
        elif count > 1:
            problems.append(f"{kind} registered {count} times in {registry}: {rel}")

    changed, status_error = status_paths()
    if status_error:
        problems.append(f"cannot inspect working tree: {status_error}")
    elif changed:
        shown = ", ".join(sorted(changed)[:8]) + (" …" if len(changed) > 8 else "")
        warnings.append(f"working tree is dirty ({len(changed)} paths): {shown}")

    staged, staged_error = staged_paths(base)
    if staged_error:
        problems.append(f"cannot inspect staged changes: {staged_error}")
    else:
        # All space changes; only managed Markdown elsewhere. Presence does not prove a meaningful outcome.
        staged_managed = {p for p in staged
                          if (is_managed_path(p) or is_space_path(p)) and p != "CHANGELOG.md"}
        if staged_managed and "CHANGELOG.md" not in staged:
            problems.append("staged memory requires staged CHANGELOG.md: "
                            + ", ".join(sorted(staged_managed)))
        if staged and LOCK.is_dir():
            shown = ", ".join(sorted(staged)[:8]) + (" …" if len(staged) > 8 else "")
            warnings.append(f"{len(staged)} staged paths while the writer lock is held: {shown} "
                            "— only the lock holder stages; anyone else stop and report")
        if staged_view:
            # The index is what would be committed; a later working-tree edit to the same path is
            # a stale staged version (the slip behind re-staging instructions).
            current_staged, current_error = staged_paths()
            stale = git("diff", "--name-only", "-z")  # no pathspec: bulk changes exceed argument limits
            recreated = git("ls-files", "--others", "-z")  # includes ignored recreations of staged deletions
            if current_error or stale.returncode != 0 or recreated.returncode != 0:
                problems.append(f"cannot compare staged paths with the working tree: {stale.stderr.strip()}")
            else:
                edited = sorted(set(filter(None, (stale.stdout + recreated.stdout).split("\0")))
                                & (staged | current_staged))
                if edited:
                    problems.append("staged paths edited after staging (re-stage or restore them): "
                                    + ", ".join(edited))

    short_head = git("rev-parse", "--short", "HEAD").stdout.strip() or "none"
    view = "index / prospective commit" if staged_view else "working tree"
    print(f"== memory check == (HEAD {short_head}; {view})")
    for item in problems:
        print("PROBLEM:", item)
    for item in warnings:
        print("warning:", item)
    if not problems and not warnings:
        print("clean")
    return 1 if problems else 0


def lock(args):
    """Cooperative writer flag for concurrent writers; issues a fresh label per acquisition."""
    name = args[0].strip() if len(args) == 1 else ""
    if not NAME.fullmatch(name):
        print("usage: python3 tools/minibrain.py lock <name>   e.g. lock assistant\n"
              "name: what the person calls this writer (no two writers share one). The tool issues\n"
              "a fresh label for this acquisition (assistant/<32 hex characters>); keep it for unlock.")
        return 2
    error = repository_error()
    if error:
        print(f"REFUSED: {error}")
        return 1
    try:
        LOCK.mkdir()
    except FileExistsError:
        meta = lock_meta()
        print(f"LOCK HELD: {meta.get('owner', '(owner unreadable)')} since {meta.get('at', '?')} "
              f"(HEAD {shown_head(meta)}).\n"
              "A lock this session did not acquire is never its own, whatever name it carries.\n"
              "Do not change shared memory files or stage anything; continue read-only.\n"
              "Recheck at an appropriate later point; report owner, timestamp and unfinished state\n"
              "if it remains held and blocks work (unreadable ownership: report now). No automatic retry loop or expiry.\n"
              "Never unlock it.")
        return 1
    except OSError as error:
        print(f"REFUSED: cannot acquire writer lock ({error}); inspect and report, do not retry automatically")
        return 1
    staged, staged_error = staged_paths()
    if staged_error or staged:
        released = release_lock()  # no checkpoint work was done under it
        if staged_error:
            print(f"cannot inspect the staging area ({staged_error})")
        else:
            print(f"REFUSED: {len(staged)} paths were staged before any checkpoint began: "
                  + ", ".join(sorted(staged)[:8]) + ".\nDo not unstage or commit them; report to the person.")
        print("Acquisition cancelled; lock released." if released else
              "Acquisition incomplete; lock remains held. Preserve state and report to the person.")
        return 1
    owner = f"{name}/{secrets.token_hex(16)}"
    meta = {"owner": owner, "at": datetime.datetime.now().isoformat(timespec="seconds"),
            "head": git("rev-parse", "--verify", "HEAD").stdout.strip()}
    try:
        (LOCK / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    except OSError as error:
        print(f"REFUSED: cannot record acquisition ({error}); lock remains held. "
              "Preserve state and report to the person; do not treat this as successful acquisition.")
        return 1
    print(f"lock acquired: {owner} — keep this label; release with: python3 tools/minibrain.py unlock {owner}")
    return 0


def unlock(args):
    if len(args) != 1 or not args[0].strip() or (args[0].startswith("--") and args[0] != "--force"):
        print("usage: python3 tools/minibrain.py unlock <issued-label> | unlock --force")
        return 2
    error = repository_error()
    if error:
        print(f"REFUSED: {error}")
        return 1
    if not LOCK.is_dir():
        print("no lock held — nothing to release")
        return 1
    meta = lock_meta()
    force = args == ["--force"]
    owner = "" if force else args[0].strip()
    if not force and not meta:
        print("REFUSED: the lock's owner is unreadable, so no label can prove whose it is.\n"
              "Only the person overrides it, with: python3 tools/minibrain.py unlock --force")
        return 1
    held = meta.get("owner", "(owner unreadable)")
    if not force and held != owner:
        print(f"REFUSED: the lock belongs to {held} (since {meta.get('at', '?')}), not {owner or '(no label)'}.\n"
              "Never remove another writer's lock: it may be a live session mid-checkpoint.\n"
              "Only the person overrides it, with: python3 tools/minibrain.py unlock --force")
        return 1
    if not release_lock():
        return 1
    print(f"lock released ({held})")
    return 0


def writer_guard(label):
    """Return (lock metadata, refusal). A lockless single writer passes without a label."""
    error = repository_error()
    if error:
        return {}, error
    if not LOCK.is_dir():
        return {}, (f"no lock is held, so {label} proves nothing; acquire the lock first or omit --label"
                    if label else None)
    meta = lock_meta()
    if not meta:
        return {}, "a writer lock is held but its owner is unreadable; treat it as held and report it to the person"
    if meta["owner"] != label:
        detail = f", not {label}" if label else "; pass --label with the label this session received"
        return {}, f"the lock belongs to {meta['owner']} (since {meta.get('at', '?')}){detail}"
    return meta, None


def commit(args):
    """Gated commit of the index: the staged check, git commit without -a, then the working-tree check."""
    usage = ("usage: python3 tools/minibrain.py commit [--label <label>] -m <message> [-m <paragraph>]... [--amend]\n"
             "Commits only what is staged; stage by name first. --label: the label this session's lock\n"
             "acquisition issued (required while a lock is held). --amend: this acquisition's own commit only.")
    label, messages, amend, rest = "", [], False, list(args)
    while rest:
        arg = rest.pop(0)
        if arg == "--label" and rest and not label and rest[0].strip():
            label = rest.pop(0).strip()
        elif arg == "-m" and rest:
            messages.append(rest.pop(0))
        elif arg == "--amend" and not amend:
            amend = True
        else:
            print(usage)
            return 2
    if not messages and not amend:
        print(usage)
        return 2
    meta, error = writer_guard(label)
    if error:
        print(f"REFUSED: {error}")
        return 1
    current = git("rev-parse", "--verify", "HEAD")
    unborn = current.returncode != 0
    check_base = "HEAD"
    if amend:
        if not label:
            print("REFUSED: --amend needs --label; only this acquisition's own commit is amended")
            return 1
        if unborn or meta.get("commit") != current.stdout.strip():
            print("REFUSED: HEAD is not this acquisition's own commit; no matching gated-commit receipt "
                  "under this lock. Use an additive commit, never infer ownership from ancestry")
            return 1
        parent = git("rev-parse", "--verify", "HEAD^")
        if parent.returncode == 0:
            check_base = parent.stdout.strip()
        else:
            # An owned initial commit has no parent. The empty tree works with
            # the repository's object format and does not write an object.
            empty = git("hash-object", "-t", "tree", "--stdin", input="")
            if empty.returncode:
                print(f"REFUSED: cannot inspect initial commit baseline: {empty.stderr.strip()}")
                return 1
            check_base = empty.stdout.strip()
    staged, staged_error = staged_paths()
    if staged_error:
        print(f"REFUSED: cannot inspect the staging area ({staged_error})")
        return 1
    if not staged:
        print("REFUSED: nothing is staged; stage the intended files by name")
        return 1
    if check(staged_view=True, allow_unborn=unborn, base=check_base) != 0:
        print("REFUSED: fix the PROBLEMs above, re-stage and run commit again")
        return 1
    command = ["commit"] + (["--amend"] if amend else []) + (["--no-edit"] if amend and not messages else [])
    for message in messages:
        command += ["-m", message]
    result = git(*command)
    if result.returncode != 0:
        print(f"REFUSED by git: {(result.stderr or result.stdout).strip()}")
        return 1
    created = git("rev-parse", "--verify", "HEAD")
    head = created.stdout.strip()
    print(f"committed {head[:12]}{' (amended)' if amend else ''}; working-tree check follows")
    if label:
        try:
            if created.returncode or not head:
                raise OSError("cannot read the created commit ID")
            meta["commit"] = head
            (LOCK / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        except OSError as error:
            print(f"PROBLEM after committing: cannot record this acquisition's commit ({error}); "
                  "lock remains held, do not amend without its receipt; preserve state and report")
            return 1
    code = check()
    if code:
        print(f"PROBLEM after committing {head}: fix it, re-stage and recommit (--amend with the same label under "
              "a lock, a further commit otherwise); nothing was released")
    return code


if __name__ == "__main__":
    # Keep diagnostics readable even for POSIX filenames with non-UTF-8 bytes.
    sys.stdout.reconfigure(errors="backslashreplace")
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        if argv[1:] not in ([], ["--staged"]):
            print("usage: python3 tools/minibrain.py check [--staged]")
            sys.exit(2)
        sys.exit(check(staged_view=argv[1:] == ["--staged"]))
    handler = {"lock": lock, "unlock": unlock, "commit": commit}.get(cmd)
    if handler is None:
        print("usage: python3 tools/minibrain.py [check [--staged] | lock <name> | unlock <label> | unlock --force\n"
              "        | commit [--label <label>] -m <message> [-m <paragraph>]... [--amend]]")
        sys.exit(2)
    sys.exit(handler(argv[1:]))
