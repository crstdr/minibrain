"""Conservative release-base estimation. Evidence of resemblance, never provenance.

Only release tags reachable from target are candidates. Equal starter tree IDs
give identical upstream deltas. Rank near matches for inspection, but recommend
only on independent exact evidence; the caller retains the target-only fallback.
"""
import ast
from functools import lru_cache
from pathlib import Path
import re
import subprocess


# CLAUDE.md often mirrors AGENTS.md; it isn't independent evidence. Working
# notes, templates populated with private knowledge, and archives aren't read.
FILES = ("tools/minibrain.py", "tools/collection.py", "AGENTS.md",
         ".agents/skills/reflect/SKILL.md")
CONFIG = {
    FILES[0]: {"MAP_FILE", "REQUIRE_LOCAL_REMOTES"},
    FILES[1]: {"GOVERNED_FIELDS", "NUMERIC_FIELDS", "SATISFIED_STATES", "CORE_HELPER"},
}
RELEASE = re.compile(r"v\d+(?:\.\d+){1,2}(?:[-+][\w.+-]+)?\Z")


def fingerprint(path, content):
    if path not in CONFIG:
        return content
    result = []
    for line in content.splitlines(keepends=True):
        name = line.split("=", 1)[0].rstrip()
        if name in CONFIG[path]:
            try:
                node, = ast.parse(line).body
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name):
                    ast.literal_eval(node.value)  # Never mask executable changes.
                    line = name + " = <local configuration>\n"
            except (SyntaxError, ValueError, TypeError):
                pass
        result.append(line)
    return "".join(result)


def estimate(repo: Path, target: str, brain: Path) -> dict:
    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args])

    def fallback(reason):
        return {"groups": [], "recommended": None, "reason": reason}

    tags = git("tag", "--merged", target, "--sort=version:refname").decode().splitlines()
    @lru_cache(None)
    def entries(tree):
        result = {}
        for row in git("ls-tree", "-r", "-z", tree).split(b"\0"):
            if row:
                meta, path = row.split(b"\t", 1)
                mode, kind, oid = meta.split()
                if kind == b"blob" and mode in (b"100644", b"100755"):
                    result[path.decode(errors="surrogateescape")] = oid.decode()
        return result

    @lru_cache(None)
    def blob(oid):
        return git("cat-file", "blob", oid).decode("utf-8")

    def starter(ref):
        row = git("ls-tree", ref, "--", "starter").split()
        return row[2].decode() if row and row[1] == b"tree" else None

    families = {}
    for tag in filter(RELEASE.fullmatch, tags):
        tree = starter(tag)
        if tree:
            families.setdefault(tree, []).append(tag)
    if not families:
        return fallback("No reachable release tags with a starter tree are available locally.")

    local = {}
    for path in FILES:
        file = brain / path
        if file.resolve() == brain.resolve() / path and file.is_file():
            try:
                local[path] = file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

    matches = {path: set() for path in local}
    rows = []
    for tree, refs in families.items():
        evidence, exact, similarity = {}, set(), []
        for path, text in local.items():
            oid = entries(tree).get(path)
            if not oid:
                evidence[path] = "absent at release path"
                continue
            upstream = blob(oid)
            if text.strip() and fingerprint(path, text) == fingerprint(path, upstream):
                exact.add(path)
                matches[path].add(tree)
                evidence[path] = "identical" if text == upstream else "identical after config"
            else:
                a, b = ({line.strip() for line in data.splitlines() if line.strip()}
                        for data in (text, upstream))
                overlap = len(a & b) / max(1, len(a | b))
                similarity.append(overlap)
                evidence[path] = f"{overlap:.0%} distinct-line overlap"
        # Similarity breaks display ties only. It cannot authorise skipping a delta.
        rank = (len(exact), len(exact.intersection(CONFIG)), sum(similarity) / max(1, len(similarity)))
        rows.append((rank, tree, {"refs": refs, "equivalent": len(refs) > 1, "evidence": evidence}))

    rows.sort(key=lambda row: row[0], reverse=True)
    groups = [row[2] for row in rows]
    winners = [s for s in matches.values() if s]
    compatible = set.intersection(*winners) if winners else set()
    recommended = None
    if winners and not compatible:
        reason = "Exact file evidence conflicts across release families; inspect the target directly."
    elif len(winners) < 2 or not any(len(s) == 1 for s in winners):
        reason = "No discriminating exact file with independent exact corroboration; inspect the target directly."
    else:
        tree, = compatible
        refs = families[tree]
        if tree == starter(target):
            reason = "The strongest match is the target itself; inspect the target rather than assume a complete upgrade."
        else:
            recommended = refs[-1]
            reason = ("Equivalent tags share one starter tree and review." if len(refs) > 1
                      else "A discriminating exact file is corroborated by a separate file without conflicting exact evidence.")
    return {"groups": groups, "recommended": recommended, "reason": reason}
