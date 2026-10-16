"""Loading structure and mirror integrity, not agent-behaviour evidence."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OperatingGateTests(unittest.TestCase):
    def setUp(self):
        self.starter = (ROOT / "starter/AGENTS.md").read_bytes()
        match = re.match(rb"\A<orient>\n(.*?)\n</orient>\n", self.starter, re.DOTALL)
        self.assertIsNotNone(match, "The canonical gate must load first")
        self.assertTrue(match[1].strip(), "The canonical gate must not be empty")
        self.gate = match[0]

    def test_canonical_starter_has_one_leading_gate(self):
        self.assertEqual(self.starter.count(b"<orient>"), 1)
        self.assertEqual(self.starter.count(b"</orient>"), 1)

    def test_claude_mirrors_live_gate_then_imports_one_contract(self):
        example = (ROOT / "starter/CLAUDE.md").read_bytes()
        # Equality prevents mirror drift and duplicate full-contract loading;
        # intentional edits to the canonical prose need no test snapshot update.
        self.assertEqual(example, self.gate + b"\n@AGENTS.md\n")

    def test_readme_routes_through_setup_without_copying_the_gate(self):
        readme = (ROOT / "README.md").read_bytes()
        self.assertNotIn(b"<orient>", readme)
        self.assertNotIn(b"</orient>", readme)
        self.assertRegex(readme, rb"\[[^\]]+\]\(SETUP\.md\)")
        setup = (ROOT / "SETUP.md").read_bytes()
        self.assertRegex(setup, rb"\[[^\]]+\]\(starter/AGENTS\.md\)")


if __name__ == "__main__":
    unittest.main()
