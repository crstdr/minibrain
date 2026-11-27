"""Distribution checks for the optional plugins."""

from html import unescape
from html.parser import HTMLParser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
ROADMAP = PLUGINS / "roadmap"
AGENTS_MAP = PLUGINS / "agents-map"
SAMPLE = ROADMAP / "sample/collection.roadmap"


class ResourceReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in {"src", "srcset", "href", "xlink:href", "poster"}:
                if not (name == "href" and value and value.startswith("#")):
                    self.references.append((tag, name, value))


class PluginTests(unittest.TestCase):
    def test_plugin_entrypoints_exist(self):
        for path in ("README.md", "agents-map/SETUP.md", "agents-map/agents_map.py",
                     "roadmap/SETUP.md", "roadmap/roadmap.py", "roadmap/web/roadmap.html"):
            with self.subTest(path=path):
                self.assertTrue((PLUGINS / path).is_file())

    def test_plugin_setup_has_no_unresolved_placeholders(self):
        for path in PLUGINS.rglob("SETUP.md"):
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("TODO", path.read_text(encoding="utf-8"))

    def test_plugin_folders_match_their_manifests(self):
        for folder in (ROADMAP, AGENTS_MAP):
            listed = {}
            for line in (folder / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
                digest, name = line.split(None, 1)
                listed[name.lstrip("*").removeprefix("./")] = digest
            present = {path.relative_to(folder).as_posix() for path in folder.rglob("*")
                       if path.is_file() and path.name != "MANIFEST.sha256"}
            with self.subTest(folder=folder.name):
                self.assertEqual(set(listed), present)
                for name, digest in listed.items():
                    self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest, name)

    def test_shared_roadmap_files_are_identical_in_both_plugins(self):
        shared = [path.relative_to(ROADMAP) for path in ROADMAP.rglob("*") if path.is_file()
                  and path.name not in {"MANIFEST.sha256", "README.md", "SETUP.md"}]
        self.assertGreater(len(shared), 0)
        for name in shared:
            with self.subTest(path=name.as_posix()):
                self.assertEqual((AGENTS_MAP / name).read_bytes(), (ROADMAP / name).read_bytes())

    def test_roadmap_pages_have_no_external_loads(self):
        for folder in (ROADMAP, AGENTS_MAP):
            for path in sorted((folder / "web").glob("*.html")) + sorted((folder / "web").glob("*.css")):
                with self.subTest(path=path.relative_to(ROOT)):
                    text = path.read_text(encoding="utf-8")
                    if path.suffix == ".html":
                        parser = ResourceReferences()
                        parser.feed(text)
                        self.assertFalse([ref for ref in parser.references if re.match(r"(?i)[a-z]+:|//", ref[2] or "")])
                    self.assertNotRegex(text, r"(?i)https?://|@import\b")

    def roadmap(self, *args, collection=SAMPLE):
        return subprocess.run([sys.executable, "-B", str(ROADMAP / "roadmap.py"), "--collection", str(collection), *args],
                              text=True, capture_output=True, timeout=30)

    def test_sample_roadmap_passes_both_checks(self):
        result = self.roadmap("check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        with tempfile.TemporaryDirectory() as tmp:
            brain = Path(tmp)
            shutil.copytree(ROOT / "starter", brain, dirs_exist_ok=True)
            shutil.copytree(SAMPLE, brain / "collection.roadmap")
            for command in (["init", "-q"], ["add", "-A"],
                            ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "init"]):
                subprocess.run(["git", *command], cwd=brain, env=env, check=True, capture_output=True)
            result = subprocess.run([sys.executable, "-B", "tools/minibrain.py", "check"],
                                    cwd=brain, env=env, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("PROBLEM", result.stdout)

    def test_roadmap_check_reports_a_dependency_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "collection.roadmap"
            shutil.copytree(SAMPLE, copy)
            record = copy / "pick-cover.md"
            lines = record.read_text(encoding="utf-8").splitlines()
            last = max(index for index, line in enumerate(lines) if line.startswith("- "))
            lines.insert(last + 1, "- needs: layout-pages")
            record.write_text("\n".join(lines) + "\n", encoding="utf-8")
            result = self.roadmap("check", collection=copy)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cycle", result.stdout + result.stderr)

    def edited_sample(self, tmp, record, change):
        copy = Path(tmp) / "collection.roadmap"
        shutil.copytree(SAMPLE, copy)
        path = copy / record
        path.write_text(change(path.read_text(encoding="utf-8")), encoding="utf-8")
        return copy

    def test_roadmap_check_reports_a_bad_alert_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = self.edited_sample(tmp, "approve-estimate.md", lambda text: text.replace("- alert: glow", "- alert: red"))
            result = self.roadmap("check", collection=copy)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("approve-estimate", result.stdout + result.stderr)

    def test_roadmap_check_reports_a_cycle_through_serves(self):
        def needs_its_priority(text):
            lines = text.splitlines()
            last = max(index for index, line in enumerate(lines) if line.startswith("- "))
            lines.insert(last + 1, "- needs: accounts")
            return "\n".join(lines) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            copy = self.edited_sample(tmp, "approve-estimate.md", needs_its_priority)
            result = self.roadmap("check", collection=copy)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("cycle", result.stdout + result.stderr)

    def test_plugin_copy_has_no_local_paths_or_banned_wording(self):
        sources = {
            path.relative_to(ROOT): path.read_text(encoding="utf-8")
            for path in PLUGINS.rglob("*") if path.is_file() and path.suffix != ".png"  # icons are binary
        }
        for filename, heading in (("README.md", "Plugins"), ("SETUP.md", "Optional plugins")):
            match = re.search(
                rf"^## {heading} \(beta\)\n(.*?)(?=^## |\Z)",
                (ROOT / filename).read_text(encoding="utf-8"), re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(match)
            sources[filename] = match[0]
        for path, source in sources.items():
            with self.subTest(path=path):
                source = unescape(source)
                self.assertNotIn("/" + "Users/", source)
                self.assertNotIn("LE" + "GO", source)
                self.assertNotIn("\u2014", source)


if __name__ == "__main__":
    unittest.main()
