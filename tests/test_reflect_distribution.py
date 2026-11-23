"""Local skill packaging, not evidence of host discovery or agent compliance."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "starter"


class ReflectDistributionTests(unittest.TestCase):
    def test_skill_identities_and_local_procedures(self):
        for name in ("reflect", "resume", "checkpoint"):
            text = (STARTER / f".agents/skills/{name}/SKILL.md").read_text()
            match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
            self.assertIsNotNone(match, "Skill frontmatter must be first")
            metadata = dict(line.split(": ", 1) for line in match[1].splitlines())
            self.assertEqual(metadata["name"], name)
            self.assertTrue(metadata["description"].strip())
            self.assertTrue(text[match.end():].strip())
            self.assertNotRegex(text, r"/Users/|/home/|starter/")
            for tag in ("standing_rules", "principles", "communication_hygiene"):
                self.assertNotRegex(text, rf"(?m)^<{tag}>")
            if name != "reflect":
                self.assertIn("AGENTS.md", text)

    def test_only_root_starter_owns_the_standing_rules_block(self):
        homes = []
        for source in STARTER.rglob("*.md"):
            blocks = re.findall(r"^<standing_rules>\n(.*?)^</standing_rules>$", source.read_text(),
                                re.MULTILINE | re.DOTALL)
            if blocks:
                homes.append(source)
                self.assertEqual(len(blocks), 1)
                self.assertTrue(blocks[0].strip())
        self.assertEqual(homes, [STARTER / "AGENTS.md"])

    def test_reflection_is_bound_locally_and_preserves_confirmation(self):
        core = (STARTER / "AGENTS.md").read_text()
        self.assertIn(".agents/skills/reflect/SKILL.md", core)
        skill = (STARTER / ".agents/skills/reflect/SKILL.md").read_text()
        self.assertIn("confirm inferred generalisations", skill)
        self.assertIn("normal approval and writer safeguards", skill)


if __name__ == "__main__":
    unittest.main()
