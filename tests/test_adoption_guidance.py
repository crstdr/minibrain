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
        self.assertIn("May: [delegated actions and conditions]. Ask first: [decisions requiring approval].", self.core)
        self.assertIn("Storage: [approved storage, backup, remote and search-index policy].", self.core)
        for name in ("MEMORY.md", "spaces/Project.md"):
            text = (ROOT / "starter" / name).read_text()
            self.assertNotRegex(text, r"\b20\d{2}-\d{2}-\d{2}\b", "Starter must not invent evidence dates")
        setup = (ROOT / "SETUP.md").read_text()
        self.assertIn("destination root—not a nested `starter/` folder", setup)
        self.assertIn("in `AGENTS.md` and memory files", setup)
        self.assertIn("placeholders grant no authority", setup)
        self.assertIn("no unresolved adoption placeholders", setup)
        if (ROOT / "examples").exists():
            self.assertFalse([p for p in (ROOT / "examples").rglob("*")
                              if p.is_file() and p.name != ".DS_Store"], "No duplicate example package")

    def test_operating_blocks_are_present_once_with_standing_rules_first(self):
        opening = self.core.split("# Agent instructions", 1)[0]
        parts = re.findall(r"<([a-z_]+)>\n(.*?)\n</\1>", opening, re.DOTALL)
        self.assertEqual([name for name, body in parts], ["standing_rules", "communication_hygiene"])
        self.assertTrue(all(body.strip() for name, body in parts))
        # Host guidance ships separately and is added only for that host.
        host = (ROOT / "hosts/repoprompt.md").read_text(encoding="utf-8")
        blocks = re.findall(r"^<rpce_tooling_guidance>\n.*?\n</rpce_tooling_guidance>$", host, re.MULTILINE | re.DOTALL)
        self.assertEqual(len(blocks), 1)

    def test_starter_binds_real_local_procedures_and_navigation(self):
        for name in ("MEMORY.md", "MAP.md", "tools/minibrain.py",
                     ".agents/skills/reflect/SKILL.md", ".agents/skills/writers/SKILL.md"):
            self.assertIn(name, self.core)
            self.assertTrue((ROOT / "starter" / name).is_file())
        self.assertNotRegex(self.core, r"(?:\.\./|starter/|drafts/|/Users/|/home/)")
        for target in re.findall(r"\[\[([^]|#]+)(?:#[^]|]*)?(?:\|[^]]*)?\]\]", self.core):
            path = ROOT / "starter" / (target + ".md")
            self.assertTrue(path.is_file(), target)
        for heading in ("## This brain", "## Authority and privacy", "## Memory rules",
                        "## Resume", "## Checkpoint", "## Other writers"):
            self.assertTrue(section(self.core, heading).strip())

    def test_runtime_keeps_review_threshold_and_one_call_save(self):
        # The size review is advised by the helper's warning at save time, not by contract text.
        helper = (ROOT / "starter/tools/minibrain.py").read_text()
        self.assertRegex(helper, r"(?m)^MEMORY_REVIEW_LINES = 150\b")
        # One-call save: the helper runs the staged and working-tree checks itself.
        save = section(self.core, "## Checkpoint")
        self.assertIn("git add <files> && python3 tools/minibrain.py commit -m", save)
        self.assertIn("never `git add -A` or `git add .`", save)
        self.assertIn("It runs the checks", save)

    def test_upgrade_consent_and_durable_state_boundaries(self):
        # Deliberate safeguards, not a snapshot of the surrounding prose.
        authority = section(self.core, "## Authority and privacy")
        for concept in ("upgrading minibrain needs the user's approval", "A complaint alone is not a direction."):
            self.assertIn(concept, authority)
        setup = (ROOT / "SETUP.md").read_text(encoding="utf-8")
        for concept in ("Preserve user knowledge", "load the contract once"):
            self.assertIn(concept, setup)
        checkpoint = section(self.core, "## Checkpoint")
        for concept in ("permits", "even when no action is due"):
            self.assertIn(concept, checkpoint)

    def test_principle_edits_and_lock_release_have_explicit_guards(self):
        checkpoint = section(self.core, "## Checkpoint")
        self.assertIn("a change to these instructions, first read `.agents/skills/reflect/SKILL.md`", checkpoint)
        # A lone writer needs no lock; signs of another writer stop the save and go to the user.
        others = section(self.core, "## Other writers")
        for safeguard in ("Changes you didn't make or someone else's lock", "no discard, reset, stash or commit",
                          "ask the user", "Owners in `MEMORY.md`", ".agents/skills/writers/SKILL.md"):
            self.assertIn(safeguard, others)
        skill = (ROOT / "starter/.agents/skills/writers/SKILL.md").read_text(encoding="utf-8")
        for safeguard in ("lock <name>", "lock acquired", "unlock <label>", "one session per name",
                          "Never hold the lock while waiting", "`unlock --force` only with the user's approval",
                          "Re-read the files you will edit"):
            self.assertIn(safeguard, skill)
        # RepoPrompt guidance: authority and consent boundaries, not the surrounding advice.
        host = (ROOT / "hosts/repoprompt.md").read_text(encoding="utf-8")
        for safeguard in ("Oversight links grant no file-edit authority", "Never bypass missing links or tools"):
            self.assertIn(safeguard, host)
        for name in ("ORACLES", "WORKFLOWS", "CAPACITY"):
            with self.subTest(policy=name):
                policy = next(line for line in host.splitlines() if line.startswith(f"- {name} —"))
                self.assertIn("agreed user preferences and delegation; otherwise ask first", policy)
        oracles = next(line for line in host.splitlines() if line.startswith("- ORACLES —"))
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
