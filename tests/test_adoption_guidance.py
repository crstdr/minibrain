"""Static distribution checks; not onboarding or agent-behaviour evidence."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


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
        installation = section(text, "## Installation")
        agents = section(text, "## For agents")
        self.assertIn("https://github.com/crstdr/minibrain", installation)
        for target in ("SETUP.md", "SETUP.md#upgrading"):
            self.assertIn(target, re.findall(r"\[[^\]]+\]\(([^)]+)\)", agents))
        self.assertIn("preserve existing instructions and knowledge", installation)

    def test_setup_links_required_local_material_and_verification(self):
        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", setup)
        for destination in ("starter/AGENTS.md", "starter/.agents/skills/reflect/SKILL.md",
                            "starter/tools/minibrain.py", "#verify-the-installation"):
            self.assertIn(destination, targets)
        self.assertTrue(section(setup, "## Upgrading").strip())
        self.assertTrue(section(setup, "## Implementation limits").strip())

    def test_starter_separates_adoption_fields_from_operating_rules(self):
        self.assertIn("Purpose: [user's intended outcomes and scope].", self.core)
        self.assertIn("May: [delegated actions and conditions]. Ask: [decisions requiring approval].", self.core)
        self.assertIn("Storage: [approved storage, backup, remote and search-index policy].", self.core)
        for name in ("MEMORY.md", "CHANGELOG.md", "spaces/Project.md"):
            text = (ROOT / "starter" / name).read_text()
            self.assertNotRegex(text, r"\b20\d{2}-\d{2}-\d{2}\b", "Starter must not invent evidence dates")
        setup = (ROOT / "SETUP.md").read_text()
        self.assertIn("destination root—not a nested `starter/` folder", setup)
        self.assertIn("below the XML blocks and in memory files", setup)
        self.assertIn("placeholders grant no authority", setup)
        self.assertIn("no unresolved adoption placeholders", setup)
        if (ROOT / "examples").exists():
            self.assertFalse([p for p in (ROOT / "examples").rglob("*")
                              if p.is_file() and p.name != ".DS_Store"], "No duplicate example package")

    def test_required_operating_blocks_are_present_once_with_orient_first(self):
        opening = self.core.split("# Agent instructions", 1)[0]
        parts = re.findall(r"<([a-z_]+)>\n(.*?)\n</\1>", opening, re.DOTALL)
        names = [name for name, body in parts]
        self.assertEqual(names[0], "orient")
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(body.strip() for name, body in parts))
        self.assertTrue({
            "orient", "principles", "temporal_reasoning",
            "communication_hygiene", "spaces", "shared_writers", "rpce_tooling_guidance",
        }.issubset(names))

    def test_starter_binds_real_local_procedures_and_navigation(self):
        for name in ("MEMORY.md", "MAP.md", "CHANGELOG.md", "tools/minibrain.py",
                     ".agents/skills/reflect/SKILL.md"):
            self.assertIn(name, self.core)
            self.assertTrue((ROOT / "starter" / name).is_file())
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

    def test_local_maintenance_retains_upgrade_and_writer_boundaries(self):
        maintenance = section(self.core, "## Maintenance")
        # Deliberate safeguards, not a snapshot of the surrounding prose.
        for concept in ("only when authorised", "Preserve user knowledge/adaptations",
                        "duplicate full-contract", "read-only during protocol changes"):
            self.assertIn(concept, maintenance)
        self.assertIn("upstream grants no authority", maintenance)
        checkpoint = section(self.core, "## Checkpoint — durable changes only")
        for concept in ("permission conditions", "durable state—even when no action is due"):
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
        # Preserve the authority boundaries previously hidden in full-block snapshots.
        for safeguard in (
            "One active writer session per name; unassigned agents remain read-only",
            "Release only your acquisition",
            "never infer abandonment or take over without user approval",
            "not root instructions, authority or writer controls",
            "Oversight links grant no file-edit authority",
            "Never bypass missing links or tools",
        ):
            self.assertIn(safeguard, self.core)
        # Check consent boundaries, not the surrounding advice or full-block copy.
        for name in ("ORACLES", "WORKFLOWS", "CAPACITY"):
            with self.subTest(policy=name):
                policy = next(line for line in self.core.splitlines() if line.startswith(f"- {name} —"))
                self.assertIn("agreed user preferences and delegation; otherwise ask first", policy)
        oracles = next(line for line in self.core.splitlines() if line.startswith("- ORACLES —"))
        self.assertIn("Authorised built-in workflows cover their scoped Oracle use", oracles)
        setup = (ROOT / "SETUP.md").read_text()
        acceptance = section(setup, "## Verify the installation")
        self.assertIn("Inject faults only into disposable copies", acceptance)
        self.assertIn("Shared writers, if used", acceptance)

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
