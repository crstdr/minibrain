"""Distribution packaging checks, not host-loading or fresh-agent evidence."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


def outside_fences(text):
    """Only the prose syntax used here; illustrative code is not a live link."""
    fence = None
    lines = []
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
        elif marker:
            fence = marker[1]
        else:
            lines.append(line)
    return "\n".join(lines)


def heading_anchors(text):
    """GitHub-style anchors for this distribution's simple ATX headings."""
    anchors = set()
    for heading in re.findall(r"^#{1,6} (.+?)\s*#*\s*$", outside_fences(text), re.MULTILINE):
        base = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        anchor = base
        suffix = 0
        while anchor in anchors:
            suffix += 1
            anchor = f"{base}-{suffix}"
        anchors.add(anchor)
    return anchors


class DistributionLinkTests(unittest.TestCase):
    def test_relative_markdown_links_and_section_anchors_resolve(self):
        # Historical source accounts are prose; template snippets inside fences
        # and intentionally synthetic [[wikilinks]] are not installed targets.
        sources = [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
        for folder in ("docs", "starter"):
            sources.extend(sorted((ROOT / folder).rglob("*.md")))
        checked = 0
        for source in sources:
            text = outside_fences(source.read_text(encoding="utf-8"))
            for destination in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", text):
                link = urlsplit(destination)
                if link.scheme or link.netloc:
                    continue
                with self.subTest(source=source.relative_to(ROOT), destination=destination):
                    target = (source.parent / unquote(link.path)).resolve() if link.path else source
                    self.assertTrue(ROOT in target.parents, "Distribution link escapes its root")
                    self.assertTrue(target.is_file(), "Relative link target is missing")
                    if link.fragment:
                        self.assertIn(unquote(link.fragment), heading_anchors(target.read_text(encoding="utf-8")))
                    checked += 1
        self.assertGreater(checked, 0)


@unittest.skipUnless(shutil.which("git"), "Git is required for the copied-template smoke test")
class CopiedTemplateSmokeTests(unittest.TestCase):
    def test_adapted_starter_forms_a_valid_disposable_brain(self):
        source = ROOT / "starter"
        files = [path.relative_to(source).as_posix() for path in source.rglob("*")
                 if path.is_file() and not any(part == "__pycache__" for part in path.parts)
                 and path.name != ".DS_Store" and path.suffix != ".pyc"]
        self.assertIn(".agents/skills/reflect/SKILL.md", files)
        self.assertIn("MAP.md", files)
        self.assertIn("tools/minibrain.py", files)
        self.assertNotIn("tools/kb.py", files)
        self.assertFalse(any(path.endswith(".example") for path in files))

        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="maintenance.auto", GIT_CONFIG_VALUE_0="false",
                   GIT_CONFIG_KEY_1="gc.auto", GIT_CONFIG_VALUE_1="0")
        with tempfile.TemporaryDirectory(prefix="minibrain-copied-templates-") as directory:
            brain = Path(directory)
            for name in files:
                target = brain / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / name, target)

            # Synthetic adoption values belong in this fixture, not the starter.
            # Evidence labels inside XML blocks and [[wikilinks]] are not fields.
            fields = {
                "user's intended outcomes and scope": "Maintain a synthetic project memory",
                "delegated actions and conditions": "maintain this synthetic memory",
                "decisions requiring approval": "scope changes, spending and publication",
                "approved storage, backup, remote and search-index policy": "private local Git only; no remote, backup or search index",
                "evidence date": "2026-01-01",
                "current goal": "Choose the next synthetic task",
                "area": "Synthetic memory",
                "user-assigned seat": "TestWriter",
                "assignment date": "2026-01-01",
                "scope and overlap constraints": "One writer; helpers read-only",
                "subject": "Next task",
                "state": "WAITING on user",
                "owner": "TestWriter",
                "next action": "obtain the task choice",
                "hold and reopening condition, or none": "await user choice; reopen on response",
                "date": "2026-01-01",
                "durable outcome": "Established synthetic memory; task choice awaits the user",
                "current state, decisions and constraints": "The synthetic user has not chosen a task; no implementation is authorised",
                "owner, next action, decision-maker and reopening condition where applicable": "TestWriter requests the user's task choice; reopen on response",
                "ref or commit; note uncommitted source changes": "disposable test fixture; no published source revision claimed",
                "adoption date": "2026-01-01",
                "changes and reasons, or none": "synthetic values for packaging verification only",
                "checks, results and limitations": "checks pending; no host-loading claim",
                "durable decision or change; superseded state and effects on pending work, if any": "Synthetic user reserved the task choice; no previous decision superseded",
            }
            placeholder = re.compile(r"(?<!\[)\[([^\[\]\n]+)\](?![\](])")
            seen = set()

            def fill(match):
                key = match[1]
                self.assertIn(key, fields, "New adoption field needs an explicit fixture value")
                seen.add(key)
                return fields[key]

            for path in brain.rglob("*.md"):
                text = path.read_text(encoding="utf-8")
                if path == brain / "AGENTS.md":
                    opening, body = text.split("# Agent instructions", 1)
                    text = opening + "# Agent instructions" + placeholder.sub(fill, body)
                    self.assertFalse(placeholder.search(text.split("# Agent instructions", 1)[1]))
                elif path != brain / "CLAUDE.md":
                    text = placeholder.sub(fill, text)
                    self.assertFalse(placeholder.search(text))
                path.write_text(text, encoding="utf-8")
            self.assertEqual(seen, set(fields), "Fixture values must match the actual starter fields")

            def run(*args, expected=0):
                result = subprocess.run(args, cwd=brain, env=env, text=True,
                                        capture_output=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                return result.stdout

            gate = (brain / "AGENTS.md").read_text().split("</orient>", 1)[0] + "</orient>\n"
            self.assertEqual((brain / "CLAUDE.md").read_text(), gate + "\n@AGENTS.md\n")
            self.assertIn("**[verified: source]**", (brain / "AGENTS.md").read_text())

            run("git", "init", "-q")
            run("git", "config", "user.name", "Synthetic Test")
            run("git", "config", "user.email", "test@example.invalid")
            run("git", "config", "commit.gpgsign", "false")
            run("git", "add", "--", *files)
            initial = run(sys.executable, "tools/minibrain.py", "check", "--staged", expected=1)
            problems = [line for line in initial.splitlines() if line.startswith("PROBLEM:")]
            self.assertEqual(len(problems), 1, initial)
            self.assertIn("no commits yet", problems[0])
            run("git", "commit", "-qm", "Create synthetic copied-template brain")
            for name in ("reflect", "resume", "checkpoint"):
                skill = f".agents/skills/{name}/SKILL.md"
                run("git", "cat-file", "-e", "HEAD:" + skill)
                run("git", "check-ignore", "--no-index", "--", skill, expected=1)
            for args in (("check",), ("check", "--staged")):
                self.assertNotIn("PROBLEM:", run(sys.executable, "tools/minibrain.py", *args))
            self.assertEqual(run("git", "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
