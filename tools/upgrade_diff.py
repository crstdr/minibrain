#!/usr/bin/env python3
"""Show an upgrading agent, change by change, which upstream starter edits a brain already has.

Run from a minibrain clone, outside the brain:
    python3 tools/upgrade_diff.py <adopted-ref> <target-ref> <brain-dir> [--map starter/path=local/path]...

For every starter file that changed between the two refs it prints each upstream hunk:
the lines removed and added upstream, whether each added line is in the brain's copy
("have"), and otherwise the closest local line ("near") or nothing ("missing").
Read-only. It reports evidence; the upgrading agent decides what to take, merge or skip.
Matching ignores surrounding whitespace only, so an adapted sentence shows as "near".
"""
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parent.parent


def show(ref, path):
    out = subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:{path}"], capture_output=True, text=True)
    return out.stdout.splitlines() if out.returncode == 0 else None


def changed(old, new):
    out = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", old, new, "--", "starter"],
                         capture_output=True, text=True, check=True)
    return [p for p in out.stdout.splitlines() if p]


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
    totals = {"have": 0, "near": 0, "missing": 0}
    for path in changed(old, new):
        rel = maps.get(path, path.removeprefix("starter/"))
        before, after = show(old, path) or [], show(new, path)
        local_file = brain / rel
        print(f"\n=== {path} -> {rel}")
        if after is None:
            print(f"removed upstream; brain copy {'exists' if local_file.exists() else 'absent'}")
            continue
        if not local_file.exists():
            print("MISSING in brain (new or renamed upstream file); use --map if it lives elsewhere")
            continue
        local = local_file.read_text(encoding="utf-8", errors="replace").splitlines()
        if local == after:
            print("identical to target")
            continue
        if path.endswith(".py"):
            print("differs from target; helpers are taken whole: compare configuration constants, then replace")
            continue
        stripped = {l.strip() for l in local}
        for tag, i1, i2, j1, j2 in SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
            if tag == "equal":
                continue
            print(f"\n@@ upstream lines {j1 + 1}-{j2} ({tag})")
            for line in before[i1:i2]:
                print(f"  - {line}" + ("   [still in brain]" if line.strip() in stripped and line.strip() else ""))
            for line in after[j1:j2]:
                if not line.strip():
                    continue
                if line.strip() in stripped:
                    totals["have"] += 1
                    print(f"  + {line}   [have]")
                    continue
                near = get_close_matches(line.strip(), list(stripped), n=1, cutoff=0.6)
                key = "near" if near else "missing"
                totals[key] += 1
                print(f"  + {line}   [{key}]")
                if near:
                    print(f"    brain: {near[0]}")
    print(f"\nadded upstream lines: {totals['have']} have, {totals['near']} near, {totals['missing']} missing. "
          "Account for each near or missing line: take it, merge it, or record why the brain keeps its own.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
