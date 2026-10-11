#!/usr/bin/env python3
"""Read-only structural check: check [--staged] | lock | unlock.

`check` reads the working tree; `check --staged` validates the prospective commit.
Neither modifies files or Git state. `lock`/`unlock` manage a cooperative writer
flag at .git/kb-writer.lock; single-writer installs never call them (guide, Appendix A).
Derived from the lean memory guide (2026-09-26).
Adapt the constants for this reference; preserve the verified properties.
Only a normal dedicated Git working copy is supported, not worktrees or distributed sync.
"""

from pathlib import Path
import datetime
import json
import os
import re
import secrets
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = "Map.md"
REQUIRED_FILES = ("AGENTS.md", "MEMORY.md", "CHANGELOG.md", MAP_FILE)
MANAGED_DIRS = {"topics"}   # canonical topics; root *.md is always managed too
RESERVED = {"AGENTS", "CLAUDE", "MEMORY", "CHANGELOG", Path(MAP_FILE).stem, "README"}
MEMORY_MAX_LINES = 150
THREADS_MAX = 12
THREAD_SOFT_CHARS = 400     # warning only: a longer bullet hides reading cost from the line cap
REQUIRE_LOCAL_REMOTES = False  # True: every Git remote must be an absolute filesystem path
LOCK = ROOT / ".git" / "kb-writer.lock"
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")  # lock takes a bare writer name; the tool issues the label

WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def git(*args, input=None):
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                              encoding="utf-8", errors="surrogateescape", env=env, input=input)
    except OSError as error:
        return subprocess.CompletedProcess(args, 127, "", f"Git unavailable: {error}")


def repository_error():
    """Fail explicitly instead of checking or locking a parent repository."""
    if not (ROOT / ".git").is_dir() or (ROOT / ".git").is_symlink():
        return "requires a normal dedicated Git working copy (.git directory); worktrees are unsupported"
    top = git("rev-parse", "--show-toplevel")
    if top.returncode:
        return f"cannot inspect Git root: {top.stderr.strip()}"
    if Path(top.stdout.strip()).resolve() != ROOT.resolve():
        return "Git working-copy root does not match the installed helper's root"
    if LOCK.is_symlink() or (LOCK.exists() and not LOCK.is_dir()):
        return "writer lock path is not an ordinary directory; preserve it and report"
    return None


def markdown_index(problems):
    """Index entries define the prospective commit and tracked supporting targets."""
    result = git("ls-files", "--stage", "-z")
    if result.returncode:
        problems.append(f"cannot list index: {result.stderr.strip()}")
        return {}
    entries = {}
    for record in filter(None, result.stdout.split("\0")):
        try:
            header, rel = record.split("\t", 1)
            mode, oid, stage = header.split()
        except ValueError:
            problems.append("cannot parse Git index")
            return {}
        if stage != "0":
            problems.append(f"unmerged index entry: {rel}")
            continue
        if rel in MANAGED_DIRS or (Path(rel).parts[0] in MANAGED_DIRS and mode not in ("100644", "100755")):
            problems.append(f"managed path is not an ordinary directory or regular file in index: {rel}")
        if rel.endswith(".md") and (is_managed_path(rel) or
                not any(part.startswith(".") for part in Path(rel).parts)):
            entries[rel] = (mode, oid)
    return entries


def working_markdown(problems):
    files = {relative(p) for p in ROOT.glob("*.md")}
    def walk_error(error):
        problems.append(f"cannot inspect managed directory: {error}")
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
            files.update(relative(Path(current) / name) for name in names if name.endswith(".md"))
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


def load_markdown(staged, problems):
    entries = markdown_index(problems)
    paths = set(entries) if staged else working_markdown(problems)
    if not staged:
        # Supporting targets are tracked, present Markdown outside hidden folders.
        paths.update(rel for rel in entries if os.path.lexists(ROOT / rel))
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
    managed = {rel for rel in paths if is_managed_path(rel)}
    if managed:
        ignored = git("check-ignore", "--no-index", "-z", "--stdin",
                      input="\0".join(sorted(managed)) + "\0")
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


def staged_paths():
    result = git("diff", "--cached", "--name-status", "-z", "-M")
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


def check(staged_view=False):
    error = repository_error()
    if error:
        print(f"PROBLEM: {error}")
        return 1
    problems, warnings = [], []

    if git("rev-parse", "--verify", "HEAD").returncode != 0:
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
                f"(HEAD {meta.get('head', '?')}) — memory files, staging and commits belong to that "
                "checkpoint until release; if this session did not acquire it, do not touch them"
            )
        else:
            warnings.append("writer lock held but its owner is unreadable — treat it as held and "
                            "report it to the person")

    documents = load_markdown(staged_view, problems)
    for name in REQUIRED_FILES:
        if name not in documents:
            problems.append(f"{name} missing")

    if "MEMORY.md" in documents:
        memory = documents["MEMORY.md"]
        if len(memory.splitlines()) > MEMORY_MAX_LINES:
            problems.append(f"MEMORY.md exceeds {MEMORY_MAX_LINES} lines")
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
            bullets = re.findall(r"^- .*(?:\n(?!- |## |\s*$).*)*", block, re.MULTILINE)  # an item runs to the next bullet, heading or blank line
            if len(bullets) > THREADS_MAX:
                problems.append(f"MEMORY.md has {len(bullets)} open threads; maximum is {THREADS_MAX}")
            for bullet in bullets:
                if len(bullet) > THREAD_SOFT_CHARS:
                    warnings.append(
                        f"thread over {THREAD_SOFT_CHARS} characters (an index line cites, it does not store): "
                        f"{bullet[:60]}…"
                    )

    managed = {rel: content for rel, content in documents.items() if is_managed_path(rel)}
    by_basename = {}
    for rel in documents:
        by_basename.setdefault(Path(rel).stem, []).append(rel)
    for basename, paths in sorted(by_basename.items()):
        if len(paths) > 1 and basename not in RESERVED:
            problems.append(f"duplicate Markdown basename {basename}.md: {', '.join(paths)}")
    known = set(by_basename)
    for rel, content in managed.items():
        if Path(rel).name == "CHANGELOG.md":
            continue
        for match in WIKILINK.finditer(content):
            target = match.group(1).strip()
            if target not in known:
                problems.append(f"broken wikilink in {rel}: [[{target}]]")

    if MAP_FILE in documents:
        map_text = documents[MAP_FILE]
        for rel in managed:
            basename = Path(rel).stem
            if basename in RESERVED:
                continue
            count = len(re.findall(rf"^- \[\[{re.escape(basename)}\]\]", map_text, re.MULTILINE))
            if count == 0:
                problems.append(f"topic not registered in {MAP_FILE}: {rel}")
            elif count > 1:
                problems.append(f"topic registered {count} times in {MAP_FILE}: {rel}")

    changed, status_error = status_paths()
    if status_error:
        problems.append(f"cannot inspect working tree: {status_error}")
    elif changed:
        shown = ", ".join(sorted(changed)[:8]) + (" …" if len(changed) > 8 else "")
        warnings.append(f"working tree is dirty ({len(changed)} paths): {shown}")

    staged, staged_error = staged_paths()
    if staged_error:
        problems.append(f"cannot inspect staged changes: {staged_error}")
    else:
        staged_managed = {p for p in staged if is_managed_path(p) and p != "CHANGELOG.md"}
        if staged_managed and "CHANGELOG.md" not in staged:
            problems.append("staged canonical Markdown requires staged CHANGELOG.md: "
                            + ", ".join(sorted(staged_managed)))
        if staged and LOCK.is_dir():
            shown = ", ".join(sorted(staged)[:8]) + (" …" if len(staged) > 8 else "")
            warnings.append(f"{len(staged)} staged paths while the writer lock is held: {shown} "
                            "— only the lock holder stages; anyone else stop and report")

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
    """Cooperative writer flag for concurrent writers (Appendix A); issues a fresh label per acquisition."""
    name = args[0].strip() if len(args) == 1 else ""
    if not NAME.fullmatch(name):
        print("usage: python3 tools/kb.py lock <name>   e.g. lock assistant\n"
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
              f"(HEAD {meta.get('head', '?')}).\n"
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
            "head": git("rev-parse", "--short", "HEAD").stdout.strip()}
    try:
        (LOCK / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    except OSError as error:
        print(f"REFUSED: cannot record acquisition ({error}); lock remains held. "
              "Preserve state and report to the person; do not treat this as successful acquisition.")
        return 1
    print(f"lock acquired: {owner} — keep this label; release with: python3 tools/kb.py unlock {owner}")
    return 0


def unlock(args):
    if len(args) != 1 or not args[0].strip() or (args[0].startswith("--") and args[0] != "--force"):
        print("usage: python3 tools/kb.py unlock <issued-label> | unlock --force")
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
              "Only the person overrides it, with: python3 tools/kb.py unlock --force")
        return 1
    held = meta.get("owner", "(owner unreadable)")
    if not force and held != owner:
        print(f"REFUSED: the lock belongs to {held} (since {meta.get('at', '?')}), not {owner or '(no label)'}.\n"
              "Never remove another writer's lock: it may be a live session mid-checkpoint.\n"
              "Only the person overrides it, with: python3 tools/kb.py unlock --force")
        return 1
    if not release_lock():
        return 1
    print(f"lock released ({held})")
    return 0


if __name__ == "__main__":
    # Keep diagnostics readable even for POSIX filenames with non-UTF-8 bytes.
    sys.stdout.reconfigure(errors="backslashreplace")
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "check"
    if cmd == "check":
        if argv[1:] not in ([], ["--staged"]):
            print("usage: python3 tools/kb.py check [--staged]")
            sys.exit(2)
        sys.exit(check(staged_view=argv[1:] == ["--staged"]))
    handler = {"lock": lock, "unlock": unlock}.get(cmd)
    if handler is None:
        print("usage: python3 tools/kb.py [check [--staged] | lock <name> | unlock <label> | unlock --force]")
        sys.exit(2)
    sys.exit(handler(argv[1:]))
