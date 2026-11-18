#!/usr/bin/env python3
"""Show an upgrading agent, change by change, which upstream starter edits a brain already has.

Run from a minibrain clone, outside the brain:
    python3 tools/upgrade_diff.py <adopted-ref> <target-ref> <brain-dir> [--map starter/path=local/path]...

Prints a summary first (files needing inspection, line counts), then every upstream hunk:
the lines removed and added upstream and, for each added line, where the brain has it:
  [have L12 § Heading]      the same line, outside fenced examples
  [example L40 § Heading]   the same line, but only inside a fenced block
  [near L12 § Heading]      a reworded line; the changed words follow as {-brain-}{+upstream+}
  [partial 2/3]             no matching line, but some clauses appear literally; the closest local
                            line is located and the rest are listed as "no literal match"
For replaced lines, "upstream change" first shows what the release itself changed, old → new.
  [missing]                 nothing comparable found
Helpers are compared with the target as a short diff (usually local configuration).
Read-only. Evidence, not a verdict: the upgrading agent decides what to take, merge or keep.
Exit 2 on bad arguments, unknown refs or a brain folder without AGENTS.md.
"""
from difflib import SequenceMatcher, get_close_matches, unified_diff
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parent.parent
HELPER_DIFF_LINES = 40


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def show(ref, path):
    out = git("show", f"{ref}:{path}")
    return out.stdout.splitlines() if out.returncode == 0 else None


def index(lines):
    """Stripped line -> list of (line number, heading, in a fenced block)."""
    found, heading, fenced = {}, "(top)", False
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```"):
            fenced = not fenced
            continue
        if not fenced and re.match(r"#{1,6} |<[a-z_]+>$", s):
            heading = s.lstrip("# ")
        if s:
            found.setdefault(s, []).append((n, heading, fenced))
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
    n, heading, _ = hits[0]
    return f"L{n} § {heading[:40]}"


def main(argv):
    args, maps = [], {}
    while argv:
        a = argv.pop(0)
        if a == "--map" and argv and "=" in argv[0]:
            src, dst = argv.pop(0).split("=", 1)
            maps[src] = dst
        else:
            args.append(a)
    if len(args) != 3:
        print(__doc__.strip())
        return 2
    old, new, brain = args[0], args[1], Path(args[2])
    for ref in (old, new):
        if git("rev-parse", "-q", "--verify", f"{ref}^{{commit}}").returncode:
            print(f"ERROR: unknown ref {ref} in {REPO}")
            return 2
    if not (brain / "AGENTS.md").is_file():
        print(f"ERROR: {brain} has no AGENTS.md; check the brain path")
        return 2
    paths = [p for p in git("diff", "--name-only", old, new, "--", "starter").stdout.splitlines() if p]
    files, body = [], []
    totals = dict.fromkeys(("have", "example", "near", "partial", "missing"), 0)
    for path in paths:
        rel = maps.get(path, path.removeprefix("starter/"))
        before, after = show(old, path) or [], show(new, path)
        local_file = brain / rel
        if after is None:
            files.append(f"removed upstream: {rel} ({'still in brain' if local_file.exists() else 'absent'})")
            continue
        if not local_file.exists():
            files.append(f"absent in brain: {rel} (new or renamed upstream; --map if it lives elsewhere)")
            continue
        local = local_file.read_text(encoding="utf-8", errors="replace").splitlines()
        if local == after:
            files.append(f"identical to target: {rel}")
            continue
        if path.endswith(".py"):
            diff = list(unified_diff(after, local, f"target/{rel}", f"brain/{rel}", n=0, lineterm=""))
            files.append(f"helper differs: {rel} ({sum(1 for d in diff if d[:1] in '+-' and d[:3] not in ('+++', '---'))} lines; diff below)")
            body.append(f"\n=== {rel}: target → brain (expect only local configuration)")
            body.extend(diff[:HELPER_DIFF_LINES] + ([f"… {len(diff) - HELPER_DIFF_LINES} more diff lines"] if len(diff) > HELPER_DIFF_LINES else []))
            continue
        files.append(f"inspect: {rel}")
        found = index(local)
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
                    hits = [h for h in found.get(line.strip(), []) if not h[2]]
                    body.append(f"  - {line}" + (f"   [old text still in brain {where(hits)}]" if hits else ""))
            for line in after[j1:j2]:
                s = line.strip()
                if not s or s.startswith("```"):
                    continue
                hits = found.get(s, [])
                if any(not h[2] for h in hits):
                    totals["have"] += 1
                    body.append(f"  + {line}   [have {where([h for h in hits if not h[2]])}]")
                    continue
                if hits:
                    totals["example"] += 1
                    body.append(f"  + {line}   [example {where(hits)}: only inside a fenced block]")
                    continue
                near = get_close_matches(s, live, n=1, cutoff=0.6)
                if near:
                    totals["near"] += 1
                    body.append(f"  + {line}   [near {where(found[near[0]])}]")
                    body.append(f"    changes: {word_diff(near[0], s)}")
                    continue
                parts = clauses(s)
                have = [c for c in parts if any(c in l for l in live)]
                if parts and have:
                    totals["partial"] += 1
                    closest = get_close_matches(s, live, n=1, cutoff=0.3)
                    body.append(f"  + {line}   [partial {len(have)}/{len(parts)}]"
                                + (f"   closest local: {where(found[closest[0]])}" if closest else ""))
                    body.extend(f"    no literal match: {c}" for c in parts if c not in have)
                    continue
                totals["missing"] += 1
                body.append(f"  + {line}   [missing]")
    print(f"upgrade diff {old} → {new} for {brain}")
    print("files:")
    print("\n".join(f"  {f}" for f in files) or "  no starter changes between these refs")
    print("added lines: " + ", ".join(f"{v} {k}" for k, v in totals.items()))
    print("Account for each line not marked have: take it, merge it, or record why the brain keeps its own.")
    print("\n".join(body))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
