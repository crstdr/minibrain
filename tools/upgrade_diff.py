#!/usr/bin/env python3
"""Show an upgrading agent, change by change, which upstream starter edits a brain already has.

Run from a minibrain clone, outside the brain:
    python3 tools/upgrade_diff.py <target-ref> <brain-dir> [--from <adopted-ref>|auto] [--map starter/path=local/path]...
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
Helpers are compared with the target as a short diff (usually local configuration).
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


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def show(ref, path):
    out = git("show", f"{ref}:{path}")
    return out.stdout.splitlines() if out.returncode == 0 else None


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
                        found.setdefault(hidden.strip(), []).append((n, heading, True))
                    comment = not bool(end)
                else:
                    prefix, start, tail = tail.partition("<!--")
                    visible += prefix
                    comment = bool(start)
            s, inactive = visible.strip(), False
        if not inactive and re.match(r"#{1,6} |<[a-z_]+>$", s):
            heading = s.lstrip("# ")
        if s:
            found.setdefault(s, []).append((n, heading, inactive))
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
    args, maps, explicit = [], {}, None
    while argv:
        a = argv.pop(0)
        if a == "--map" and argv and "=" in argv[0]:
            src, dst = argv.pop(0).split("=", 1)
            maps[src] = dst
        elif a == "--from" and argv:
            explicit = argv.pop(0)
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
        paths = [p for p in git("diff", "--name-only", old, new, "--", "starter").stdout.splitlines() if p]
    else:  # target-only: every target line counts as added, so nothing is hidden
        paths = [p for p in git("ls-tree", "-r", "--name-only", new, "--", "starter").stdout.splitlines() if p]
        banner.append("TARGET-ONLY: each target line is checked against the brain, with no base to compare. "
                      "Text the brain adapted on purpose and text upstream changed look alike; "
                      "no 'upstream change' lines can be shown.")
    files, body = [], []
    totals = dict.fromkeys(("have", "example", "near", "partial", "missing"), 0)
    for path in paths:
        rel = maps.get(path, path.removeprefix("starter/"))
        previous, after = (show(old, path) if old else None), show(new, path)
        before = previous or []
        local_file = brain / rel
        if not old and path.removeprefix("starter/").startswith(SEEDS):  # by upstream path, not --map
            files.append(f"seed file, not compared line by line without a base: {rel}")
            continue
        if after is None:
            files.append(f"removed upstream: {rel} ({'still in brain' if local_file.exists() else 'absent'})")
            continue
        if not local_file.exists():
            origin = "in target" if not old else "present at both refs" if previous is not None else "new upstream"
            files.append(f"{rel}: absent locally; {origin} (--map if it lives elsewhere)")
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
                    body.append(f"  + {line}   [example {where(hits)}: only in an example or HTML comment]")
                    continue
                near = get_close_matches(s, live, n=1, cutoff=0.6)
                if near:
                    totals["near"] += 1
                    body.append(f"  + {line}   [near {where(found[near[0]])}]")
                    body.append(f"    local → target, comparison only: {word_diff(near[0], s)}")
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
    print(f"upgrade diff {old or '(no base)'} → {new} for {brain}")
    print("\n".join(banner))
    print("files:")
    print("\n".join(f"  {f}" for f in files) or "  no starter changes between these refs")
    print("added lines: " + ", ".join(f"{v} {k}" for k, v in totals.items()))
    print("Account for each line not marked have: take it, merge it, or record why the brain keeps its own.")
    print("\n".join(body))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
