"""Loading structure, not agent-behaviour evidence."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class OperatingGateTests(unittest.TestCase):
    def test_claude_imports_the_contract_once(self):
        # A host that reads CLAUDE.md loads the one contract; no copied rules to drift.
        self.assertEqual((ROOT / "starter/CLAUDE.md").read_text(), "@AGENTS.md\n")

    def test_readme_routes_through_setup(self):
        readme = (ROOT / "README.md").read_text()
        self.assertRegex(readme, r"\[[^\]]+\]\(SETUP\.md\)")
        setup = (ROOT / "SETUP.md").read_text()
        self.assertRegex(setup, r"\[[^\]]+\]\(starter/AGENTS\.md\)")


if __name__ == "__main__":
    unittest.main()
