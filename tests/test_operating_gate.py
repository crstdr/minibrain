"""Static distribution checks, not a test of an agent's behaviour or host loading."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
# Review snapshot. The live canonical source is starter/AGENTS.md.
# An intentional wording revision updates this snapshot and CHANGELOG; earlier
# reviews/evaluations do not establish results for the new wording.
REVIEWED_GATE = '<orient>\nBefore substantive replies or consequential actions:\n1. PURPOSE — User outcome? Does this step advance it?\n2. GROUND — Evidence, assumptions, commitments, authority?\n3. IMPROVE — Recurring friction or changed guidance? Use `reflect`. Preserve safeguard purpose; act within authority, otherwise propose.\n4. CAPACITY — Context fit? If compaction needed: save durable state first; compact at a safe boundary.\n5. CEREMONY — Match effort and process to stakes and context. Preserve safeguards; skip ritual. Ask only when uncertainty is consequential.\nApply proportionately; don’t narrate the checklist.\n</orient>\n'.encode("utf-8")


class OperatingGateTests(unittest.TestCase):
    def test_canonical_starter_begins_with_reviewed_gate(self):
        starter = (ROOT / "starter/AGENTS.md").read_bytes()
        self.assertTrue(starter.startswith(REVIEWED_GATE + b"\n<principles>"))
        self.assertEqual(starter.count(b"<orient>"), 1)
        self.assertEqual(starter.count(b"</orient>"), 1)

    def test_claude_starter_begins_with_identical_gate(self):
        example = (ROOT / "starter/CLAUDE.md").read_bytes()
        self.assertTrue(example.startswith(REVIEWED_GATE))
        self.assertEqual(example.count(b"<orient>"), 1)
        self.assertEqual(example.count(b"</orient>"), 1)

    def test_starter_import_follows_gate_without_a_second_contract(self):
        example = (ROOT / "starter/CLAUDE.md").read_bytes()
        self.assertEqual(example, REVIEWED_GATE + b"\n@AGENTS.md\n")

    def test_readme_links_to_the_canonical_contract_without_copying_the_gate(self):
        readme = (ROOT / "README.md").read_bytes()
        self.assertNotIn(REVIEWED_GATE, readme)
        self.assertNotIn(b"<orient>", readme)
        self.assertNotIn(b"</orient>", readme)
        self.assertRegex(readme, rb"\[[^\]]+\]\(starter/AGENTS\.md\)")


if __name__ == "__main__":
    unittest.main()
