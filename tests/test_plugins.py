"""Distribution checks for the optional plugins."""

from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
ROADMAP = PLUGINS / "roadmap/roadmap.html"
DATA_BLOCK = re.compile(r"^const DATA = (\{.*?\});$", re.MULTILINE | re.DOTALL)


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
        for path in ("README.md", "map/SETUP.md", "roadmap/SETUP.md", "roadmap/roadmap.html"):
            with self.subTest(path=path):
                self.assertTrue((PLUGINS / path).is_file())

    def test_plugin_setup_has_no_unresolved_placeholders(self):
        for path in PLUGINS.rglob("SETUP.md"):
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertNotIn("TODO", path.read_text(encoding="utf-8"))

    def test_roadmap_has_no_external_loads(self):
        html = ROADMAP.read_text(encoding="utf-8")
        parser = ResourceReferences()
        parser.feed(html)
        self.assertEqual(parser.references, [])
        self.assertNotRegex(html, r"(?i)https?://|@import\b|\burl\s*\(")

    def test_roadmap_data_matches_the_renderer(self):
        html = ROADMAP.read_text(encoding="utf-8")
        match = DATA_BLOCK.search(html)
        self.assertIsNotNone(match)
        data = json.loads(match[1])
        self.assertEqual(set(data), {"nodes", "order", "short", "generated"})
        nodes = {item["id"]: item for item in data["nodes"]}
        self.assertEqual(len(nodes), len(data["nodes"]))
        self.assertEqual(set(data["order"]), {key for key in nodes if nodes[key]["kind"] == "priority"})
        self.assertEqual(set(data["short"]), set(data["order"]))
        self.assertGreaterEqual(sum(item["state"] == "awaiting-user" for item in nodes.values()), 2)
        self.assertTrue(any(item["state"] == "blocked" for item in nodes.values()))
        for key, item in nodes.items():
            with self.subTest(item=key):
                self.assertEqual(set(item) - {"daysLeft"}, {
                    "id", "title", "kind", "state", "owner", "serves", "by", "source",
                    "importance", "body", "needs", "related", "ext",
                })
                self.assertLessEqual(set(item["needs"] + item["related"]), set(nodes))
                days = item.get("daysLeft")
                if days is not None:
                    self.assertIn(type(days), (int, float))
                    self.assertGreaterEqual(days, 0)

    @unittest.skipUnless(shutil.which("node"), "Node.js required for the renderer smoke test")
    def test_roadmap_warns_about_a_dependency_cycle(self):
        html = ROADMAP.read_text(encoding="utf-8")
        script = html.split("<script>", 1)[1].split("</script>", 1)[0]
        match = DATA_BLOCK.search(script)
        self.assertIsNotNone(match)
        data = json.loads(match[1])
        nodes = {item["id"]: item for item in data["nodes"]}
        nodes["assemble"]["needs"].append("verify")
        script = script[:match.start(1)] + json.dumps(data) + script[match.end(1):]
        harness = """
const elements = new Map();
const document = {getElementById(id) {
  if (!elements.has(id)) elements.set(id, {addEventListener(){}, querySelectorAll(){return [];}});
  return elements.get(id);
}};
const location = {hash: ""};
function addEventListener() {}
"""
        probe = """
const assert = require("node:assert/strict");
const warning = document.getElementById("panel").innerHTML;
assert.match(warning, /role="alert"/);
assert.match(warning, /Dependency cycle:.*verify → assemble → verify/);
assert.doesNotMatch(warning, /Critical path/);
assert.equal(document.getElementById("sub").textContent,
  `Derived view generated ${DATA.generated}. The notes are the source.`);
"""
        result = subprocess.run(
            ["node", "-"], input=harness + script + probe, text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_plugin_copy_has_no_local_paths_or_banned_wording(self):
        sources = {
            path.relative_to(ROOT): path.read_text(encoding="utf-8")
            for path in PLUGINS.rglob("*") if path.is_file()
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
