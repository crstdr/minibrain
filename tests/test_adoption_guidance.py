"""Static distribution checks; not onboarding or agent-behaviour evidence."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
# Snapshot of the approved optional block; this is not the live instruction source.
APPROVED_RPCE = "<rpce_tooling_guidance>\nUse an available Oracle for consequential uncertainty; choose workflows and authorised delegation when they simplify the work. Keep simple work direct.\n1. Give collaborators the outcome, scope, authority and expected evidence. Do not assume they received this brain's memory or rules; share only permitted context.\n2. Verify consequential findings and save durable outcomes in canonical memory, not only chats or exports. Review agreement does not expand authority.\n3. For CAPACITY, save durable state and use self_compact at a safe boundary when needed.\n</rpce_tooling_guidance>\n"

# Snapshot of the approved spaces block, not a second runtime source.
APPROVED_SPACES = """<spaces>
Named knowledge scope; one canonical entrypoint: a note or folder index.
1. Find existing homes before creating; reuse or create the smallest useful space. Register in parent navigation.
2. Add children and assets only as needed. Propose consequential restructuring; preserve knowledge, evidence and incoming links. No competing copies.
3. Nest knowledge and navigation—not root instructions, authority or writer controls. Keep responsibilities visible in the root working index; load only relevant spaces.
</spaces>
"""


# Snapshot of approved rules, not a second instruction source.
APPROVED_SHARED_WRITERS = '<shared_writers>\nWhen writers may overlap:\n- IDENTITY — Each writer needs a stable, user-assigned name and scope, recorded in the canonical ownership record. One active session per name; unassigned agents remain read-only.\n- CONSISTENCY — Ensure consistent reads. Protect shared memory, instructions and Git index through commit and verification.\n- OWNERSHIP — Respect unfinished work. Release only your acquisition; never infer abandonment or take over without user approval.\n- CONTINUITY — Keep saves coherent and attributable. No locks across planned waits; report interrupted work and retained protection.\n</shared_writers>\n'

def section(text, heading):
    """Read an owned level-two/three section, without depending on its prose."""
    marker = heading + "\n"
    start = text.index(marker) + len(marker)
    level = len(heading) - len(heading.lstrip("#"))
    end = re.search(r"^#{1," + str(level) + r"} ", text[start:], re.MULTILINE)
    return text[start:start + end.start()] if end else text[start:]


class AdoptionGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.core = (ROOT / "starter/AGENTS.md").read_text(encoding="utf-8")

    def test_readme_keeps_the_two_audiences_and_routes_to_setup(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^## .+$", text, re.MULTILINE),
                         ["## For humans", "## For agents installing minibrain"])
        for target in ("docs/setup.md", "docs/setup.md#upgrading", "starter/AGENTS.md"):
            self.assertIn(target, re.findall(r"\[[^\]]+\]\(([^)]+)\)", text))
        self.assertIn("preserving existing instructions and knowledge", text)

    def test_setup_reads_operating_starter_and_local_skill_before_acceptance(self):
        setup = (ROOT / "docs/setup.md").read_text(encoding="utf-8")
        items = re.findall(r"^\d+\. (.+)$", section(setup, "## Reading order"), re.MULTILINE)
        self.assertEqual(len(items), 4)
        for item, destination in ((items[0], "../starter/AGENTS.md"),
                                  (items[1], "../starter/.agents/skills/reflect/SKILL.md"),
                                  (items[3], "acceptance.md")):
            self.assertIn(destination, re.findall(r"\[[^\]]+\]\(([^)]+)\)", item))
        self.assertIn("Applicable references", items[2])
        self.assertTrue(section(setup, "## Upgrading").strip())
        self.assertTrue(section(setup, "## Implementation limits").strip())

    def test_starter_separates_adoption_fields_from_operating_rules(self):
        self.assertIn("Purpose: [user's intended outcomes and scope].", self.core)
        self.assertIn("May: [delegated actions and conditions]. Ask: [decisions requiring approval].", self.core)
        self.assertIn("Storage: [approved storage, backup, remote and search-index policy].", self.core)
        for name in ("MEMORY.md", "CHANGELOG.md", "spaces/Project.md"):
            text = (ROOT / "starter" / name).read_text()
            self.assertNotRegex(text, r"\b20\d{2}-\d{2}-\d{2}\b", "Starter must not invent evidence dates")
            self.assertNotIn("issue-tracking", text)
        setup = (ROOT / "docs/setup.md").read_text()
        self.assertIn("destination root—not a nested `starter/` folder", setup)
        self.assertIn("below the XML blocks and in memory files", setup)
        self.assertIn("placeholders grant no authority", setup)
        self.assertIn("no unresolved adoption placeholders", setup)
        if (ROOT / "examples").exists():
            self.assertFalse([p for p in (ROOT / "examples").rglob("*")
                              if p.is_file() and p.name != ".DS_Store"], "No duplicate example package")

    def test_opening_operating_blocks_are_contiguous_and_preserve_agreed_copy(self):
        opening = self.core.split("# Agent instructions", 1)[0]
        parts = re.findall(r"<([a-z_]+)>\n(.*?)\n</\1>", opening, re.DOTALL)
        self.assertEqual([name for name, body in parts], [
            "orient", "principles", "temporal_reasoning",
            "communication_hygiene", "spaces", "shared_writers", "rpce_tooling_guidance",
        ])
        remainder = re.sub(r"<([a-z_]+)>\n.*?\n</\1>", "", opening, flags=re.DOTALL)
        remainder = re.sub(r"<!--.*?-->", "", remainder, flags=re.DOTALL)
        self.assertFalse(remainder.strip(), "No wrapper prose between blocks")
        self.assertIn(APPROVED_SPACES, self.core)
        self.assertIn(APPROVED_RPCE, self.core)
        self.assertIn(APPROVED_SHARED_WRITERS, self.core)
        self.assertNotIn("````", self.core)
        self.assertNotIn("COPY →", self.core)

    def test_starter_binds_real_local_procedures_and_navigation(self):
        for name in ("MEMORY.md", "MAP.md", "CHANGELOG.md", "tools/minibrain.py",
                     ".agents/skills/reflect/SKILL.md"):
            self.assertIn(name, self.core)
            self.assertTrue((ROOT / "starter" / name).is_file())
        self.assertNotIn("Map.md", self.core)
        self.assertNotRegex(self.core, r"(?:\.\./|starter/|drafts/|/Users/|/home/)")
        for target in re.findall(r"\[\[([^]|#]+)(?:#[^]|]*)?(?:\|[^]]*)?\]\]", self.core):
            path = ROOT / "starter" / (target + ".md")
            self.assertTrue(path.is_file(), target)
        for heading in ("## Authority and privacy", "## Memory rules",
                        "## Memory spaces", "## Resume — before new work",
                        "## Checkpoint — durable changes only", "## Maintenance",
                        "## Writer bindings"):
            self.assertTrue(section(self.core, heading).strip())

    def test_runtime_keeps_local_limits_and_prospective_commit_check(self):
        for setting, value in (("MEMORY_REVIEW_LINES", 150), ("THREADS_MAX", 12), ("THREAD_SOFT_CHARS", 400)):
            helper = (ROOT / "starter/tools/minibrain.py").read_text()
            self.assertRegex(helper, rf"(?m)^{setting} = {value}\b")
            self.assertIn(str(value), section(self.core, "## Memory rules"))
        rules = section(self.core, "## Memory rules")
        self.assertIn("At ≥150 lines, consider `reflect` at the next useful boundary", rules)
        self.assertIn("No forced trimming or repeated review of unchanged content", rules)
        self.assertIn("check --staged", section(self.core, "## Checkpoint — durable changes only"))
        self.assertIn("latest three", section(self.core, "## Resume — before new work"))

    def test_local_maintenance_retains_upgrade_and_writer_boundaries(self):
        maintenance = section(self.core, "## Maintenance")
        for concept in ("only when authorised", "adopted source", "proposed revision",
                        "local instructions", "comparison limits", "before imports",
                        "after entrypoint changes", "duplicate full-contract",
                        "read-only during protocol changes"):
            self.assertIn(concept, maintenance)
        self.assertIn("upstream grants no authority", maintenance)
        checkpoint = section(self.core, "## Checkpoint — durable changes only")
        for concept in ("principles", "permission conditions", "conversation", "saved narrative", "actionable"):
            self.assertIn(concept, checkpoint)

    def test_principle_edits_and_lock_release_have_explicit_guards(self):
        checkpoint = section(self.core, "## Checkpoint — durable changes only")
        self.assertIn("Before principle or constraint changes, read `reflect`'s Principles section", checkpoint)
        self.assertIn("Only after successful verification, release", checkpoint)
        self.assertIn("preserve and report unfinished work and held protection", checkpoint)
        writers = section(self.core, "## Writer bindings")
        self.assertIn("when writers may overlap", writers)
        self.assertIn("`MEMORY.md` → Owners", writers)
        self.assertIn("lock <name>", writers)
        self.assertIn("unlock <issued-label>", writers)
        self.assertNotIn("## Shared writers", self.core)
        self.assertEqual(self.core.count("<shared_writers>"), 1)
        acceptance = (ROOT / "docs/acceptance.md").read_text()
        self.assertIn("On disposable data", section(acceptance, "## Shared writers"))

    def test_starter_wikilinks_and_anchors_resolve_locally(self):
        for source in (ROOT / "starter").rglob("*.md"):
            for link in re.findall(r"\[\[([^]]+)\]\]", source.read_text()):
                target, _, heading = link.split("|", 1)[0].partition("#")
                path = ROOT / "starter" / (target if target.endswith(".md") else target + ".md")
                self.assertTrue(path.is_file(), (source, target))
                if heading:
                    headings = re.findall(r"^#{1,6} (.+)$", path.read_text(), re.MULTILINE)
                    self.assertIn(heading, headings, (source, link))


if __name__ == "__main__":
    unittest.main()
