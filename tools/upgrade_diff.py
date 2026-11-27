#!/usr/bin/env python3
"""Show an upgrading agent, change by change, which upstream starter edits a brain already has,
including its RepoPrompt CE block, and which plugins changed.

Run from a minibrain clone, outside the brain:
    python3 tools/upgrade_diff.py <target-ref> <brain-dir> [--from <adopted-ref>|auto]
        [--map starter/path=local/path[#heading]]... [--skips <file>]
    (older form: python3 tools/upgrade_diff.py <adopted-ref> <target-ref> <brain-dir>)

Base: --from <ref> uses a known adopted ref, tagged or not. Without it the tool estimates the base
from the brain's files and uses the estimate only when one candidate is clearly ahead; otherwise it
lists the candidates with their evidence and gives a target-only review. The banner says which.

Prints a summary first (files needing inspection, line counts), then every upstream hunk:
the lines removed and added upstream and, for each added line, where the brain has it:
  [have L12 § Heading]      the same line, outside fenced examples
  [example L40 § Heading]   the same line, but only in an example or HTML comment
  [near L12 § Heading]      a reworded line; the changed words follow as {-brain-}{+upstream+}
  [partial 2/3]             no matching line, but some clauses appear literally; the closest local
                            line is located and the rest are listed as "no literal match"
For replaced lines, "upstream change" first shows what the release itself changed, old → new.
  [missing]                 nothing comparable found
  [skipped: listed in --skips]  the line contains a phrase from the --skips file (one per line):
                            changes the brain declined on purpose, kept wherever it records them
--map to path#heading compares a starter file with one section of a brain file. CLAUDE.md-style
@file imports are followed. Dash variants and spacing are ignored when matching.
Helpers are compared with the target as a short diff, with functions present only in the target named.
hosts/repoprompt.md: its <rpce_tooling_guidance> block is compared with AGENTS.md when the brain has that block.
Plugins install outside brains: changed plugin folders are listed, for their own Update steps.
Read-only. Evidence, not a verdict: the upgrading agent decides what to take, merge or keep.
Exit 2 on bad arguments, an unresolvable ref or a brain folder without AGENTS.md; a review with no\nusable base is still a valid result (exit 0).
"""
from difflib import SequenceMatcher, get_close_matches, unified_diff
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parent.parent
HELPER_DIFF_LINES = 40
SEEDS = ("MEMORY.md", "CHANGELOG.md", "MAP.md", "spaces/")  # starter seeds that hold the brain's own memory
HOST = "hosts/repoprompt.md"  # brains copy its block into AGENTS.md
HOST_BLOCK = ("<rpce_tooling_guidance>", "</rpce_tooling_guidance>")


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def show(ref, path):
    out = git("show", f"{ref}:{path}")
    return out.stdout.splitlines() if out.returncode == 0 else None


def norm(text):
    """Matching key: dash variants and runs of spaces are formatting, not wording."""
    return re.sub(r"\s+", " ", re.sub(r"\s*[—–]\s*|\s+-\s+", " ", text)).strip()


def host_block(lines):
    """The block lines a brain copies from hosts/repoprompt.md, without the file's own introduction."""
    if lines is None or HOST_BLOCK[0] not in lines or HOST_BLOCK[1] not in lines:
        return lines
    start = lines.index(HOST_BLOCK[0])
    return lines[start + 1:lines.index(HOST_BLOCK[1], start)]


def section(lines, name):
    """Lines of the first heading whose text contains name, up to the next heading of the same or higher level."""
    start = level = None
    for n, line in enumerate(lines):
        m = re.match(r"(#{1,6}) +(.*)", line)
        if m and start is None and name.lower() in m[2].lower():
            start, level = n, len(m[1])
        elif m and start is not None and len(m[1]) <= level:
            return lines[start:n]
    return lines[start:] if start is not None else None


def index(lines):
    """Map each line to its position, heading and whether it is example/comment text."""
    found, heading, fence, comment = {}, "(top)", None, False
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if fence:
            if re.fullmatch(r" {0,3}" + fence[0] + "{" + str(len(fence)) + r",}[ \t]*", line):
                fence = None
                continue
            inactive = True
        else:
            opener = re.match(r"^ {0,3}(`{3,}(?!`)|~{3,})(.*)$", line)
            if not comment and opener and (opener[1][0] != "`" or "`" not in opener[2]):
                fence = opener[1]
                continue
            tail, visible = line, ""
            while tail:
                if comment:
                    hidden, end, tail = tail.partition("-->")
                    if hidden.strip():
                        found.setdefault(norm(hidden), []).append((n, heading, True))
                    comment = not bool(end)
                else:
                    prefix, start, tail = tail.partition("<!--")
                    visible += prefix
                    comment = bool(start)
            s, inactive = visible.strip(), False
        if not inactive and re.match(r"#{1,6} |<[a-z_]+>$", s):
            heading = s.lstrip("# ")
        if s:
            found.setdefault(norm(s), []).append((n, heading, inactive))
    return found


def clauses(line):
    return [c.strip(" .;") for c in re.split(r"(?<=[.;?])\s+", line.strip()) if len(c.strip(" .;")) > 12]


def word_diff(old, new):
    a, b = old.split(), new.split()
    out = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            out.append(" ".join(a[i1:i2]) if i2 - i1 <= 6 else f"{' '.join(a[i1:i1+3])} … {' '.join(a[i2-3:i2])}")
        else:
            if i2 > i1: out.append("{-" + " ".join(a[i1:i2]) + "-}")
            if j2 > j1: out.append("{+" + " ".join(b[j1:j2]) + "+}")
    return " ".join(out)


def where(hits):
    n, heading, _ = next((h for h in hits if not h[2]), hits[0])  # prefer an active occurrence
    return f"L{n} § {heading[:40]}"


def resolves(ref):
    return git("rev-parse", "-q", "--verify", f"{ref}^{{commit}}").returncode == 0


def recorded_bases(brain):
    """Versions the brain's own notes mention near adoption words: hints to confirm, never used as the base."""
    hits = {}
    for f in [brain / "AGENTS.md"] + sorted(brain.glob("topics/*.md")) + sorted(brain.glob("spaces/**/*.md")):
        try:
            text = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for n, line in enumerate(text, 1):
            if re.search(r"adopt|upgrad|base|install", line, re.I):
                for v in re.findall(r"\bv?(0\.\d+(?:\.\d+)?(?:-alpha\.\d+)?)\b", line):
                    ref = f"v{v}"
                    if ref not in hits and resolves(ref):
                        hits[ref] = f"{f.relative_to(brain)} L{n}"
    return hits


def choose_base(new, brain):
    """(base ref or None, banner lines). Uses the estimator when present; never a weak guess."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from upgrade_base import estimate
    except ImportError:
        return None, ["base: unknown (no estimator available); target-only review"]
    result = estimate(REPO, new, brain)
    groups = result.get("groups", [])
    lines = []
    recorded = recorded_bases(brain)
    if recorded:
        key = lambda r: [int(x) for x in re.findall(r"\d+", r)]
        newest, *older = sorted(recorded, key=key, reverse=True)
        lines.append(f"  recorded in the brain's notes (a claim to confirm, not used): newest {newest} at {recorded[newest]}"
                     + (f"; older mentions, likely history: {', '.join(older[:3])}" if older else ""))
        lines.append(f"  if one is right: python3 tools/upgrade_diff.py {new} <brain-dir> --from <that ref>")
    exact = any("identical" in e for g in groups for e in g.get("evidence", {}).values())
    if groups and not exact and not result.get("recommended"):
        lines.append("  no release matches any brain file exactly (files mostly local); candidates omitted")
        groups = []
    for g in groups[:3]:
        same = " (equivalent: same review)" if g.get("equivalent") and len(g["refs"]) > 1 else ""
        lines.append(f"  candidate {', '.join(g['refs'])}{same}")
        lines.extend(f"    {f}: {e}" for f, e in g.get("evidence", {}).items())
    base, reason = result.get("recommended"), result.get("reason", "")
    if base:
        group = next((g["refs"] for g in groups if base in g["refs"]), [base])
        label = f"SHARED REVIEW of {', '.join(group)} (same starter files)" if len(group) > 1 else f"ESTIMATED {base}"
        return base, [f"base: {label}: {reason}",
                      "Every result below assumes that base; rerun with --from <ref> if you know the real one."] + lines
    return None, [f"base: unknown, so this is a target-only review: {reason}"] + lines + [
                 f"  if you know the base: python3 tools/upgrade_diff.py {new} <brain-dir> --from <ref>"]


def main(argv):
    args, maps, explicit, skips = [], {}, None, []
    while argv:
        a = argv.pop(0)
        if a == "--map" and argv and "=" in argv[0]:
            src, dst = argv.pop(0).split("=", 1)
            maps[src] = dst
        elif a == "--from" and argv:
            explicit = argv.pop(0)
        elif a == "--skips" and argv:
            skip_file = Path(argv.pop(0))
            if not skip_file.is_file():
                print(f"ERROR: --skips file not found: {skip_file}")
                return 2
            skips.extend(norm(l).lower() for l in skip_file.read_text(encoding="utf-8").splitlines()
                         if l.strip() and not l.lstrip().startswith("#"))
        else:
            args.append(a)
    if len(args) == 3 and explicit is None:  # older form: <adopted-ref> <target-ref> <brain-dir>
        explicit, args = args[0], args[1:]
    if len(args) != 2:
        print(__doc__.strip())
        return 2
    new, brain = args[0], Path(args[1])
    for ref in [new] + ([explicit] if explicit not in (None, "auto") else []):
        if not resolves(ref):
            print(f"ERROR: unknown ref {ref} in {REPO}")
            return 2
    if not (brain / "AGENTS.md").is_file():
        print(f"ERROR: {brain} has no AGENTS.md; check the brain path")
        return 2
    if explicit not in (None, "auto"):
        old, banner = explicit, [f"base: KNOWN {explicit}"]
    else:
        old, banner = choose_base(new, brain)
        if old and maps:  # the estimator reads default paths; remapped files could mislead it
            old, banner = None, ["base: estimate not used because --map changes file paths; "
                                 "pass --from <ref> for a full review"]
    if old:
        paths = [p for p in git("diff", "--name-only", old, new, "--", "starter", HOST).stdout.splitlines() if p]
    else:  # target-only: every target line counts as added, so nothing is hidden
        paths = [p for p in git("ls-tree", "-r", "--name-only", new, "--", "starter", HOST).stdout.splitlines() if p]
        banner.append("TARGET-ONLY: each target line is checked against the brain, with no base to compare. "
                      "Text the brain adapted on purpose and text upstream changed look alike; "
                      "no 'upstream change' lines can be shown.")
    files, body = [], []
    totals = dict.fromkeys(("have", "example", "near", "partial", "missing", "skipped"), 0)
    for path in paths:
        host = path == HOST
        if host and path not in maps:
            agents = (brain / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
            if HOST_BLOCK[0] not in agents:
                files.append(f"{HOST}: not compared; AGENTS.md has no RepoPrompt CE block")
                continue
        rel = maps.get(path, "AGENTS.md" if host else path.removeprefix("starter/"))
        previous, after = (show(old, path) if old else None), show(new, path)
        if host:
            previous, after = host_block(previous), host_block(after)
            if old and previous == after:
                continue  # only the file's introduction changed
        before = previous or []
        rel, _, part = rel.partition("#")
        local_file = brain / rel
        if not old and path.removeprefix("starter/").startswith(SEEDS):  # by upstream path, not --map
            files.append(f"seed file, not compared line by line without a base: {rel}"
                         + (" (its --map is not used)" if path in maps else ""))
            continue
        if after is None:
            files.append(f"removed upstream: {rel} ({'still in brain' if local_file.exists() else 'absent'})")
            continue
        if not local_file.exists():
            origin = "in target" if not old else "present at both refs" if previous is not None else "new upstream"
            files.append(f"{rel}: absent locally; {origin} (--map if it lives elsewhere; it may also live as a section of another file)")
            continue
        local = local_file.read_text(encoding="utf-8", errors="replace").splitlines()
        if part:
            local = section(local, part)
            if local is None:
                files.append(f"{rel}#{part}: no heading containing '{part}' in {rel}")
                continue
            rel = f"{rel}#{part}"
        if local == after:
            files.append(f"identical to target: {rel}")
            continue
        if path.endswith(".py"):
            diff = list(unified_diff(after, local, f"target/{rel}", f"brain/{rel}", n=0, lineterm=""))
            changed = [d for d in diff if d[:1] in "+-" and d[:3] not in ("+++", "---")]
            config = [d for d in changed if re.match(r"[+-][A-Z][A-Z0-9_]* = ", d)]
            kind = ("configuration assignments only" if len(config) == len(changed)
                    else f"{len(config)} configuration lines, {len(changed) - len(config)} other changed lines")
            defs = lambda text: set(re.findall(r"^def (\w+)\(", "\n".join(text), re.M))
            added = sorted(defs(after) - defs(local))
            if added:
                kind += "; functions only in target: " + ", ".join(added[:8]) + (" …" if len(added) > 8 else "")
            files.append(f"helper differs: {rel} ({len(changed)} changed lines: {kind})")
            body.append(f"\n=== {rel}: target → brain diff ({kind})")
            body.extend(diff[:HELPER_DIFF_LINES])
            if len(diff) > HELPER_DIFF_LINES:
                body.append(f"… {len(diff) - HELPER_DIFF_LINES} more diff lines; full diff: "
                            f"git -C {REPO} show {new}:{path} | diff -u - {local_file}")
            continue
        files.append(f"inspect: {rel}" + (" (RepoPrompt CE block)" if host else ""))
        imported = []  # follow @file imports such as CLAUDE.md's @AGENTS.md
        for line in local:
            m = re.fullmatch(r"\s*@([\w./-]+\.md)\s*", line)
            if m and (brain / m[1]).is_file():
                imported += (brain / m[1]).read_text(encoding="utf-8", errors="replace").splitlines()
        found = index(local)
        for key, hits in index(imported).items():
            found.setdefault(key, []).extend((n, f"via @import § {h}", f) for n, h, f in hits)
        live = [s for s, hits in found.items() if any(not f for *_, f in hits)]
        body.append(f"\n=== {path} -> {rel}")
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            body.append(f"\n@@ upstream {new} lines {j1 + 1}-{j2} ({tag})")
            if tag == "replace":  # what the release itself changed, before any local comparison
                olds = [l.strip() for l in before[i1:i2] if l.strip()]
                for line in after[j1:j2]:
                    prior = get_close_matches(line.strip(), olds, n=1, cutoff=0.5)
                    if prior and prior[0] != line.strip():
                        body.append(f"  upstream change: {word_diff(prior[0], line.strip())}")
            for line in before[i1:i2]:
                if line.strip():
                    hits = [h for h in found.get(norm(line), []) if not h[2]]
                    body.append(f"  - {line}" + (f"   [old text still in brain {where(hits)}]" if hits else ""))
            for line in after[j1:j2]:
                s = line.strip()
                if not s or s.startswith("```"):
                    continue
                renamed = [f"{a.removeprefix('starter/')} is {b} here" for a, b in maps.items()
                           if a.removeprefix("starter/") in s and a.removeprefix("starter/") != b]
                if renamed:
                    line = f"{line}   (mapped: {'; '.join(renamed)})"
                if any(k in norm(s).lower() for k in skips):
                    totals["skipped"] += 1
                    body.append(f"  + {line}   [skipped: listed in --skips]")
                    continue
                hits = found.get(norm(s), [])
                if any(not h[2] for h in hits):
                    totals["have"] += 1
                    body.append(f"  + {line}   [have {where([h for h in hits if not h[2]])}]")
                    continue
                if hits:
                    totals["example"] += 1
                    body.append(f"  + {line}   [example {where(hits)}: only in an example or HTML comment]")
                    continue
                near = get_close_matches(norm(s), live, n=1, cutoff=0.6)
                if near:
                    totals["near"] += 1
                    body.append(f"  + {line}   [near {where(found[near[0]])}]")
                    body.append(f"    local → target, comparison only: {word_diff(near[0], norm(s))}")
                    continue
                parts = clauses(s)
                have = [c for c in parts if any(norm(c) in l for l in live)]
                if parts and len(have) == len(parts):
                    host = next(l for l in live if all(norm(c) in l for c in parts))
                    totals["have"] += 1
                    body.append(f"  + {line}   [have, inside a longer line {where(found[host])}]")
                    continue
                if parts and have:
                    totals["partial"] += 1
                    closest = get_close_matches(norm(s), live, n=1, cutoff=0.3)
                    body.append(f"  + {line}   [partial {len(have)}/{len(parts)}]"
                                + (f"   closest local: {where(found[closest[0]])}" if closest else ""))
                    unmatched = [c for c in parts if c not in have]
                    body.extend(f"    no literal match: {c}" for c in unmatched[:3])
                    if len(unmatched) > 3:
                        body.append(f"    … {len(unmatched) - 3} more clauses with no literal match")
                    continue
                totals["missing"] += 1
                body.append(f"  + {line}   [missing]")
    if old:
        plugins = sorted({p.split("/")[1] for p in git("diff", "--name-only", old, new, "--", "plugins").stdout.splitlines()
                          if p.count("/") >= 2})
        kept = set(git("ls-tree", "--name-only", f"{new}:plugins").stdout.split())
        if [p for p in plugins if p in kept]:
            files.append("plugins changed (installed outside the brain; update each installed copy by its SETUP's "
                         "Update steps): " + ", ".join(p for p in plugins if p in kept))
        if [p for p in plugins if p not in kept]:
            files.append("plugins removed upstream: " + ", ".join(p for p in plugins if p not in kept))
    unused = [src for src in maps if src not in paths]
    if unused:
        files.append("--map not used (file unchanged between these refs): " + ", ".join(unused))
    print(f"upgrade diff {old or '(no base)'} → {new} for {brain}")
    print("\n".join(banner))
    print("files:")
    print("\n".join(f"  {f}" for f in files) or "  no starter or RepoPrompt CE block changes between these refs")
    print("added lines: " + ", ".join(f"{v} {k}" for k, v in totals.items()))
    print("Labels are text matches, not coverage verdicts: a line marked missing may be covered in other words.")
    print("Account for each line not marked have: take it, merge it, or record why the brain keeps its own.")
    print("\n".join(body))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
