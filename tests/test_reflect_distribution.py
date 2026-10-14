"""Packaging invariants, not evidence of host discovery or agent compliance."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "starter/skills/reflect/SKILL.md"


class ReflectDistributionTests(unittest.TestCase):
    def test_skill_identity_matches_its_directory(self):
        text = SKILL.read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
        self.assertIsNotNone(match, "Skill metadata must be first")
        metadata = dict(line.split(": ", 1) for line in match[1].splitlines())
        self.assertEqual(metadata["name"], SKILL.parent.name)
        self.assertTrue(metadata["description"].strip())
        self.assertEqual(set(metadata), {"name", "description"})
        self.assertTrue(text[match.end():].strip(), "Procedure must not be empty")

    def test_setup_supplies_skill_and_runtime_uses_a_local_binding(self):
        setup = ROOT / "docs/setup.md"
        targets = re.findall(
            r"\[[^\]]+\]\(([^)]+/reflect/SKILL\.md)\)",
            setup.read_text(encoding="utf-8"),
        )
        self.assertTrue(targets, "Setup must link to the supplied procedure")
        self.assertEqual({(setup.parent / target).resolve() for target in targets}, {SKILL})
        self.assertTrue(SKILL.is_file())
        core = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        self.assertRegex(core, r"(?m)^Reflection: <[^\n]*local[^\n]*>")
        self.assertRegex(core, r"(?i)locally bound `reflect`")
        self.assertNotIn("skills/reflect/SKILL.md", core)

    def test_principles_have_one_empty_distribution_home(self):
        homes = []
        for area in ("starter", "examples"):
            for source in (ROOT / area).rglob("*.md*"):
                text = source.read_text(encoding="utf-8")
                opens = re.findall(r"^<principles>\s*$", text, re.MULTILINE)
                closes = re.findall(r"^</principles>\s*$", text, re.MULTILINE)
                self.assertEqual(len(opens), len(closes), str(source))
                if opens:
                    homes.append(source)
                    blocks = re.findall(
                        r"^<principles>\n(.*?)^</principles>$",
                        text, re.MULTILINE | re.DOTALL,
                    )
                    self.assertEqual(len(blocks), 1)
                    self.assertEqual(blocks[0].strip(), "")
        self.assertEqual(homes, [ROOT / "starter/instructions.md"])

    def test_skill_does_not_duplicate_root_control_blocks(self):
        text = SKILL.read_text(encoding="utf-8")
        for tag in ("before_you_act", "principles", "primitive_spaces"):
            self.assertNotRegex(text, rf"(?m)^<{tag}>")

    def test_runtime_skill_is_self_contained(self):
        text = SKILL.read_text(encoding="utf-8")
        # Runtime navigation is through local bindings, not a source checkout,
        # online file, or a developer's private absolute path.
        self.assertNotRegex(text, r"https?://|/Users/|/home/")
        self.assertEqual(re.findall(r"\[[^\]]+\]\(([^)]+)\)", text), [])


if __name__ == "__main__":
    unittest.main()
