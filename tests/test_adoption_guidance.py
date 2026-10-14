"""Static distribution checks; not onboarding or agent-behaviour evidence."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Snapshot of the approved optional block; this is not the live instruction source.
APPROVED_RPCE = "<rpce_tooling_guidance>\nUse an available Oracle for consequential uncertainty; choose workflows and authorised delegation when they simplify the work. Keep simple work direct.\n1. Give collaborators the outcome, scope, authority and expected evidence. Do not assume they received this brain's memory or rules; share only permitted context.\n2. Verify consequential findings and save durable outcomes in canonical memory, not only chats or exports. Review agreement does not expand authority.\n3. For CAPACITY, save durable state and use self_compact at a safe boundary when needed.\nFollow live RPCE guidance for tool mechanics and permissions.\n</rpce_tooling_guidance>\n"

# Snapshot of the unchanged spaces primitive, not a second runtime source.
APPROVED_SPACES = """<primitive_spaces>
A memory space is a named area of knowledge with a clear purpose and one authoritative entrypoint: a note, or a folder as it grows.
1. When asked to create a space, find any existing home first; reuse it or create the smallest useful one and register it in its parent navigation.
2. Grow into child spaces and supporting assets only when useful. Propose consequential restructuring first; preserve knowledge, evidence and incoming links without competing copies.
3. Repeat navigation and knowledge structure, not root instructions, authority or writer machinery. Keep responsibilities visible in the root working index; load only spaces needed for the task.
</primitive_spaces>
"""


def section(text, heading):
    """Read an owned level-two/three section, without depending on its prose."""
    marker = heading + "\n"
    start = text.index(marker) + len(marker)
    level = len(heading) - len(heading.lstrip("#"))
    end = re.search(r"^#{1," + str(level) + r"} ", text[start:], re.MULTILINE)
    return text[start:start + end.start()] if end else text[start:]


class AdoptionGuidanceTests(unittest.TestCase):
    def test_readme_has_a_short_human_install_prompt_and_two_audiences(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^## .+$", text, re.MULTILINE),
                         ["## For humans", "## For agents installing minibrain"])
        humans = section(text, "## For humans")
        prompts = re.findall(r"^> .+$", humans, re.MULTILINE)
        self.assertEqual(prompts, [
            "> Install https://github.com/crstdr/minibrain into this folder, "
            "adapting it to my needs and preserving existing instructions and knowledge."
        ])

    def test_readme_routes_installers_and_orders_required_and_conditional_reading(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        agents = section(text, "## For agents installing minibrain")
        targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", agents)
        self.assertIn("docs/setup.md", targets)
        self.assertIn("docs/setup.md#upgrading", targets)
        items = re.findall(r"^\d+\. (.+)$", agents, re.MULTILINE)
        self.assertEqual(len(items), 4, "Installers need one four-item reading plan")
        for item, destination in ((items[0], "starter/instructions.md"),
                                  (items[1], "starter/skills/reflect/SKILL.md"),
                                  (items[3], "docs/acceptance.md")):
            self.assertIn(destination, re.findall(r"\[[^\]]+\]\(([^)]+)\)", item))
        # Setup owns conditional routes; the README need not duplicate its
        # links or turn optional implementation material into required reading.
        self.assertRegex(items[2], r"(?i)\b(modules|examples)\b")
        self.assertRegex(items[2], r"(?i)\bsetup\b")
        self.assertRegex(items[2], r"(?i)\b(only|when|if|applicable|conditional)\b")

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
        self.assertIn(APPROVED_SPACES.encode("utf-8"), (ROOT / "starter/instructions.md").read_bytes())
        self.assertTrue((ROOT / "docs/spaces.md").is_file())

    def test_runtime_has_bindings_and_procedures_not_an_installer_section(self):
        text = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        bindings = section(text, "## Local bindings")
        fields = re.findall(r"^([A-Z][A-Za-z ]+): <[^\n]+>$", bindings, re.MULTILINE)
        self.assertEqual(len(fields), len(set(fields)), "Bindings have one template home")
        self.assertEqual(set(fields), {
            "Purpose", "Instructions", "Memory", "History", "Startup budget",
            "Persistence", "Privacy", "Reflection", "Writers", "Environment", "Adoption",
        })
        for heading in ("## Memory spaces", "## Shared-writer trigger", "## Maintenance"):
            self.assertTrue(section(text, heading).strip())
        resume = section(text, "## Resume — before new work")
        self.assertRegex(resume, r"(?i)run \*?\*?resume\*?\*? before")
        self.assertNotIn("Install or upgrade — adopter only", text)
        # A copied runtime must not require the source checkout to navigate.
        targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
        for target in targets:
            with self.subTest(target=target):
                self.assertFalse((ROOT / "starter" / target).is_file(),
                                 "Runtime links must bind locally, not to supplied source files")
                self.assertNotRegex(target, r"^(?:https?://|\.\./)")

    def test_git_example_fills_the_canonical_binding_schema(self):
        core = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        example = (ROOT / "examples/git-markdown/README.md").read_text(encoding="utf-8")
        fields = lambda text: re.findall(r"^([A-Z][A-Za-z ]+):", text, re.MULTILINE)
        bindings = section(example, "### Example local bindings")
        self.assertEqual(fields(bindings), fields(section(core, "## Local bindings")))
        self.assertIn("../../starter/instructions.md#local-bindings", bindings)
        self.assertIn(".agents/skills/reflect/SKILL.md", bindings)

    def test_installed_maintenance_retains_authorised_upgrade_safeguards(self):
        text = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        bindings = section(text, "## Local bindings")
        adoption = next(line for line in bindings.splitlines() if line.startswith("Adoption:"))
        for concept in ("source URL", "release/ref", "exact source commit", "date", "adaptations"):
            self.assertIn(concept, adoption)
        maintenance = section(text, "## Maintenance")
        self.assertRegex(maintenance, r"(?i)upgrade\b[^.\n]*authori[sz]ed")
        for concept in ("Adoption", "adopted source", "proposed revision", "current local contract",
                        "user knowledge", "local adaptations", "comparison limit"):
            self.assertIn(concept, maintenance)
        self.assertRegex(maintenance, r"(?i)upstream[^.\n]*no new authority")

    def test_runtime_maintenance_preserves_gate_and_host_loading_rules(self):
        core = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        maintenance = section(core, "## Maintenance")
        # These must survive copying the runtime: installer-only coverage is
        # insufficient when later entrypoint changes happen without setup.
        gate_rules = [paragraph for paragraph in maintenance.split("\n\n")
                      if "gate" in paragraph.lower() and "placement" in paragraph.lower()]
        self.assertTrue(gate_rules, "Installed maintenance must retain adopted gate placement")
        self.assertRegex(" ".join(gate_rules), r"(?i)\b(preserve|retain|maintain|keep)\b")
        imports = [paragraph for paragraph in maintenance.split("\n\n")
                   if "import" in paragraph.lower()]
        self.assertTrue(imports, "Installed maintenance must govern future imports")
        import_rules = " ".join(imports)
        self.assertRegex(import_rules, r"(?i)verify[^.\n]*loading[^.\n]*before[^.\n]*imports")
        self.assertRegex(import_rules, r"(?i)after[^.\n]*entrypoint changes")
        self.assertRegex(import_rules, r"(?i)full[- ]contract")
        self.assertRegex(import_rules, r"(?i)(avoid|prevent|no |not |without)[^.\n]*(duplicat|again|twice)")

    def test_checkpoint_makes_saved_narrative_actionable_too(self):
        core = (ROOT / "starter/instructions.md").read_text(encoding="utf-8")
        checkpoint = section(core, "## Checkpoint — durable changes only")
        capture_steps = [line for line in checkpoint.splitlines()
                         if re.match(r"^\d+\. ", line) and "decisions" in line]
        self.assertTrue(capture_steps)
        capture = " ".join(capture_steps)
        for concept in ("conversation", "saved narrative", "actionable"):
            self.assertIn(concept, capture)

    def test_filled_bindings_retain_local_navigation_history_and_budget_rules(self):
        readme = (ROOT / "examples/git-markdown/README.md").read_text(encoding="utf-8")
        example = section(readme, "### Example local bindings")
        match = re.search(r"```text\n(.*?)```", example, re.DOTALL)
        self.assertIsNotNone(match)
        # Check what is copied, not explanatory prose left in the distribution.
        bindings = dict(line.split(": ", 1) for line in match[1].splitlines())
        memory = bindings["Memory"]
        for concept in ("root-relative", "qualified", "Map.md", "## Spaces"):
            self.assertIn(concept, memory)
        self.assertRegex(memory, r"(?i)(child|parent)[^.\n]*exact `?## Spaces`?")
        self.assertRegex(memory, r"(?i)((every|all)[^.\n]*leading[^.\n]*(bullet|link)|leading[^.\n]*anywhere)")
        history = bindings["History"]
        self.assertRegex(history, r"(?i)current[^.\n]*(first|before|preced)[^.\n]*newest-first")
        budget = bindings["Startup budget"]
        self.assertRegex(budget, r"(?i)helper constants[^.\n]*(together|alongside)")
        self.assertRegex(budget, r"(?i)(budget|rule|limit)")

    def test_setup_owns_adoption_record_and_upgrade_comparison(self):
        text = (ROOT / "docs/setup.md").read_text(encoding="utf-8")
        adoption = section(text, "### Record adoption and preserve adaptations")
        for concept in ("exact distribution commit", "uncertainty"):
            self.assertIn(concept, adoption)
        reading = section(text, "## Reading order")
        items = re.findall(r"^\d+\. (.+)$", reading, re.MULTILINE)
        self.assertEqual(len(items), 4)
        for item, destination in ((items[0], "../starter/instructions.md"),
                                  (items[1], "../starter/skills/reflect/SKILL.md"),
                                  (items[3], "acceptance.md")):
            self.assertIn(destination, re.findall(r"\[[^\]]+\]\(([^)]+)\)", item))
        self.assertRegex(items[2], r"(?i)only applicable")
        conditional_targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", items[2])
        for destination in ("../starter/shared-writers.md", "../starter/environments/rpce.md"):
            self.assertIn(destination, conditional_targets)
        self.assertTrue(section(text, "## Implementation limits").strip())
        upgrading = section(text, "## Upgrading")
        for concept in ("adopted source", "proposed upstream revision", "current local contract"):
            self.assertIn(concept, upgrading)
        self.assertRegex(upgrading, r"(?i)upgrade\b[^.\n]*authori[sz]ed")
        # Setup refers to the canonical runtime template rather than maintaining
        # a second generic binding schema that can drift from it.
        self.assertIn("../starter/instructions.md#local-bindings", text)
        self.assertNotRegex(text, r"(?m)^Purpose: <")


if __name__ == "__main__":
    unittest.main()
