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
        for folder in ("docs", "starter", "examples"):
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
    def test_readme_templates_form_a_valid_disposable_brain(self):
        readme = (ROOT / "examples/git-markdown/README.md").read_text(encoding="utf-8")
        files = {}
        for name in ("MEMORY.md", "Map.md", "spaces/Project.md", "CHANGELOG.md"):
            match = re.search(r"^### " + re.escape(name) + r"\n(?:(?!^### ).)*?^```markdown\n(.*?)^```",
                              readme, re.MULTILINE | re.DOTALL)
            self.assertIsNotNone(match, f"Missing concrete {name} template")
            # This is deliberately synthetic test data, not a claim that an
            # adopter may leave placeholders or invent a user's state.
            content = re.sub(r"<[^>\n]+>", "Synthetic fixture", match[1])
            files[name] = content.replace("YYYY-MM-DD", "2026-01-01")
        bindings = re.search(r"^### Example local bindings\n.*?^```text\n(.*?)^```",
                             readme, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(bindings, "Missing filled local-binding example")
        synthetic_bindings = re.sub(r"<[^>\n]+>", "Synthetic fixture", bindings[1])
        core = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        files["AGENTS.md"], substitutions = re.subn(
            r"```text\n.*?```", lambda match: "```text\n" + synthetic_bindings + "```",
            core, count=1, flags=re.DOTALL,
        )
        self.assertEqual(substitutions, 1, "Missing runtime binding template")
        files[".agents/skills/reflect/SKILL.md"] = (ROOT / "starter/skills/reflect/SKILL.md").read_text(encoding="utf-8")
        files["tools/kb.py"] = (ROOT / "examples/git-markdown/tools/kb.py").read_text(encoding="utf-8")

        env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="maintenance.auto", GIT_CONFIG_VALUE_0="false",
                   GIT_CONFIG_KEY_1="gc.auto", GIT_CONFIG_VALUE_1="0")
        with tempfile.TemporaryDirectory(prefix="minibrain-copied-templates-") as directory:
            brain = Path(directory)
            for name, content in files.items():
                target = brain / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            def run(*args, expected=0):
                result = subprocess.run(args, cwd=brain, env=env, text=True,
                                        capture_output=True, timeout=15)
                self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
                return result.stdout

            run("git", "init", "-q")
            run("git", "config", "user.name", "Synthetic Test")
            run("git", "config", "user.email", "test@example.invalid")
            run("git", "config", "commit.gpgsign", "false")
            run("git", "add", "--", *files)
            initial = run(sys.executable, "tools/kb.py", "check", "--staged", expected=1)
            problems = [line for line in initial.splitlines() if line.startswith("PROBLEM:")]
            self.assertEqual(len(problems), 1, initial)
            self.assertIn("no commits yet", problems[0])
            run("git", "commit", "-qm", "Create synthetic copied-template brain")
            reflection = ".agents/skills/reflect/SKILL.md"
            run("git", "cat-file", "-e", "HEAD:" + reflection)
            run("git", "check-ignore", "--no-index", "--", reflection, expected=1)
            for args in (("check",), ("check", "--staged")):
                self.assertNotIn("PROBLEM:", run(sys.executable, "tools/kb.py", *args))
            self.assertEqual(run("git", "status", "--porcelain"), "")


if __name__ == "__main__":
    unittest.main()
