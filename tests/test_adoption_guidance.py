"""Static distribution checks; not onboarding or agent-behaviour evidence."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Snapshot of the approved optional block; this is not the live instruction source.
APPROVED_RPCE = "<rpce_tooling_guidance>\nUse an available Oracle for consequential uncertainty; choose workflows and authorised delegation when they simplify the work. Keep simple work direct.\n1. Give collaborators the outcome, scope, authority and expected evidence. Do not assume they received this brain's memory or rules; share only permitted context.\n2. Verify consequential findings and save durable outcomes in canonical memory, not only chats or exports. Review agreement does not expand authority.\n3. For CAPACITY, save durable state and use self_compact at a safe boundary when needed.\nFollow live RPCE guidance for tool mechanics and permissions.\n</rpce_tooling_guidance>\n"


class AdoptionGuidanceTests(unittest.TestCase):
    def test_adoption_prompt_is_a_short_point_to_the_source(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        prompts = re.findall(r"^> Adopt .+$", text, re.MULTILINE)
        self.assertEqual(prompts, ["> Adopt a memory system like https://github.com/crstdr/minibrain, adapted to this folder."])

    def test_optional_rpce_binding_preserves_approved_block(self):
        text = (ROOT / "starter/environments/rpce.md").read_text(encoding="utf-8")
        self.assertIn("```text\n" + APPROVED_RPCE + "```", text)
        self.assertEqual(text.count("<rpce_tooling_guidance>"), 1)
        self.assertNotIn("<rpce_tooling_guidance>", (ROOT / "starter/instructions.md").read_text(encoding="utf-8"))

    def test_spaces_primitive_has_one_authoritative_core_home(self):
        text = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        self.assertEqual(text.count("<primitive_spaces>"), 1)
        self.assertEqual(text.count("</primitive_spaces>"), 1)
        self.assertLess(text.index("<before_you_act>"), text.index("<primitive_spaces>"))
        self.assertTrue((ROOT / "docs/spaces.md").is_file())

    def test_installed_contract_carries_provenance_and_upgrade_rule(self):
        text = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        self.assertIn("exact source commit", text)
        self.assertIn("Before upgrading, compare", text)
        self.assertIn("preserve local adaptations", text)

    def test_setup_exposes_adoption_record_and_upgrade_path(self):
        text = (ROOT / "docs/setup.md").read_text(encoding="utf-8")
        self.assertIn("### Record adoption and preserve adaptations", text)
        self.assertIn("exact distribution commit", text)
        self.assertIn("record the uncertainty", text)
        self.assertIn("Compare the adopted source", text)


if __name__ == "__main__":
    unittest.main()
