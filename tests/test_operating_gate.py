"""Static distribution checks, not a test of an agent's behaviour or host loading."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
# Review snapshot. The live canonical source is starter/instructions.md.
# An intentional wording revision updates this snapshot and CHANGELOG; earlier
# reviews/evaluations do not establish results for the new wording.
REVIEWED_GATE = """<before_you_act>
Before each substantive response or consequential action:
1. PURPOSE — What outcome is the user pursuing, and does this step advance it?
2. GROUND — What evidence, assumptions, commitments and authority boundaries matter?
3. IMPROVE — Does recurring friction reveal a problem in the approach? Preserve the safeguard's purpose; improve within your authority or propose a change.
4. CAPACITY — Is context still fit for this work? At a safe boundary, preserve continuity and compact when needed.
Apply proportionately. Do not recite the checklist or invent extra work.
</before_you_act>
""".encode("utf-8")


class OperatingGateTests(unittest.TestCase):
    def test_canonical_starter_begins_with_reviewed_gate(self):
        starter = (ROOT / "starter/instructions.md").read_bytes()
        self.assertTrue(starter.startswith(REVIEWED_GATE + b"\n# "))
        self.assertEqual(starter.count(b"<before_you_act>"), 1)
        self.assertEqual(starter.count(b"</before_you_act>"), 1)

    def test_claude_example_begins_with_identical_gate(self):
        example = (ROOT / "examples/git-markdown/CLAUDE.md.example").read_bytes()
        self.assertTrue(example.startswith(REVIEWED_GATE))
        self.assertEqual(example.count(b"<before_you_act>"), 1)
        self.assertEqual(example.count(b"</before_you_act>"), 1)

    def test_example_import_follows_gate_without_a_second_contract(self):
        example = (ROOT / "examples/git-markdown/CLAUDE.md.example").read_bytes()
        self.assertEqual(example, REVIEWED_GATE + b"\n@AGENTS.md\n")

    def test_readme_displays_reviewed_gate_in_a_code_fence(self):
        readme = (ROOT / "README.md").read_bytes()
        self.assertIn(b"```text\n" + REVIEWED_GATE + b"```", readme)
        self.assertEqual(readme.count(b"<before_you_act>"), 1)
        self.assertEqual(readme.count(b"</before_you_act>"), 1)


if __name__ == "__main__":
    unittest.main()
