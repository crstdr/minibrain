"""The upgrade diff reports upstream changes against a brain; it never edits the brain."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/upgrade_diff.py"


def has_ref(ref):
    return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "-q", "--verify", ref + "^{commit}"],
                          capture_output=True).returncode == 0


@unittest.skipUnless(shutil.which("git") and has_ref("v0.7.0") and has_ref("v0.8-alpha.1"), "needs release tags")
class UpgradeDiffTests(unittest.TestCase):
    def brain_at(self, ref):
        brain = Path(tempfile.mkdtemp(prefix="minibrain-upgrade-"))
        self.addCleanup(shutil.rmtree, brain)
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", ref, "starter"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "--strip-components=1", "-C", str(brain)], input=archive.stdout, check=True)
        return brain

    def run_tool(self, brain):
        out = subprocess.run([sys.executable, str(TOOL), "v0.7.0", "v0.8-alpha.1", str(brain)],
                             capture_output=True, text=True, check=True)
        return out.stdout

    def test_unupgraded_brain_shows_each_new_line_as_not_yet_present(self):
        brain = self.brain_at("v0.7.0")
        before = (brain / "AGENTS.md").read_bytes()
        out = self.run_tool(brain)
        self.assertRegex(out, r'\+ 3\. IMPROVE — New standing rule.*\[(near|missing)')
        self.assertIn("{-Recurring-}", out)
        self.assertEqual((brain / "AGENTS.md").read_bytes(), before)  # read-only

    def test_upgraded_brain_reports_identical_files(self):
        out = self.run_tool(self.brain_at("v0.8-alpha.1"))
        self.assertIn("identical to target", out)
        self.assertIn("0 example, 0 near, 0 partial, 0 missing", out)

    def test_upstream_change_is_shown_from_the_release_itself(self):
        out = self.run_tool(self.brain_at("v0.7.0"))
        self.assertIn("upstream change: 3. IMPROVE — {-Recurring-} {+New standing rule", out)

    def test_location_points_to_the_active_occurrence(self):
        brain = self.brain_at("v0.7.0")
        agents = brain / "AGENTS.md"
        lines = agents.read_text().splitlines()
        i = next(n for n, l in enumerate(lines) if l.startswith("3. IMPROVE"))
        agents.write_text("```\n" + lines[i] + "\n```\n" + "\n".join(lines) + "\n")
        self.assertRegex(self.run_tool(brain), rf"3\. IMPROVE — New standing rule.*\[near L{i + 4} ")

    def test_no_base_gives_a_target_only_review(self):
        out = subprocess.run([sys.executable, str(TOOL), "v0.8-alpha.1", str(self.brain_at("v0.7.0")), "--from", "auto"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("base:", out.stdout)
        if "TARGET-ONLY" in out.stdout:
            self.assertNotIn("upstream change:", out.stdout)
            self.assertRegex(out.stdout, r"3\. IMPROVE — New standing rule.*\[(near|partial|missing)")

    def test_new_form_with_known_base_matches_the_old_form(self):
        brain = str(self.brain_at("v0.7.0"))
        new = subprocess.run([sys.executable, str(TOOL), "v0.8-alpha.1", brain, "--from", "v0.7.0"],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("base: KNOWN v0.7.0", new)
        self.assertIn("upstream change: 3. IMPROVE", new)

    def test_unresolvable_explicit_base_fails(self):
        out = subprocess.run([sys.executable, str(TOOL), "v0.8-alpha.1", str(self.brain_at("v0.7.0")), "--from", "v9.9"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)

    def improve_line(self):
        new = subprocess.run(["git", "-C", str(ROOT), "show", "v0.8-alpha.1:starter/AGENTS.md"],
                             capture_output=True, text=True, check=True).stdout
        return next(l for l in new.splitlines() if l.startswith("3. IMPROVE"))

    def tool_args(self, brain, *extra):
        return subprocess.run([sys.executable, str(TOOL), "v0.8-alpha.1", str(brain), "--from", "v0.7.0", *extra],
                              capture_output=True, text=True, check=True).stdout

    def test_dash_and_spacing_differences_still_match(self):
        brain = self.brain_at("v0.7.0")
        agents = brain / "AGENTS.md"
        agents.write_text(agents.read_text() + "\n" + self.improve_line().replace("—", " ") + "\n")
        self.assertRegex(self.tool_args(brain), r"\+ 3\. IMPROVE — New standing rule.*\[have L")

    def test_a_sentence_inside_a_longer_line_counts_as_present(self):
        brain = self.brain_at("v0.7.0")
        agents = brain / "AGENTS.md"
        sentence = "User-stated decisions, deferrals, permission conditions, procedures, corrections and lessons are durable state—even when no action is due."
        agents.write_text(agents.read_text() + "\nLocal preamble words. " + sentence + " Local tail.\n")
        out = self.tool_args(brain)
        if "+ " + sentence in out:
            self.assertIn("[have, inside a longer line", out.split("+ " + sentence, 1)[1].splitlines()[0])

    def test_imports_are_followed(self):
        brain = self.brain_at("v0.7.0")
        (brain / "AGENTS.md").write_text((brain / "AGENTS.md").read_text() + "\n" + self.improve_line() + "\n")
        (brain / "CLAUDE.md").write_text("@AGENTS.md\n")
        self.assertIn("via @import", self.tool_args(brain))

    def test_skips_mark_declined_lines(self):
        brain = self.brain_at("v0.7.0")
        skips = brain.parent / (brain.name + "-skips.txt")
        skips.write_text("New standing rule, instruction\n")
        self.addCleanup(skips.unlink)
        out = self.tool_args(brain, "--skips", str(skips))
        self.assertRegex(out, r"3\. IMPROVE — New standing rule.*\[skipped")

    def test_map_to_a_section(self):
        brain = self.brain_at("v0.7.0")
        skill = brain / ".agents/skills/reflect/SKILL.md"
        (brain / "AGENTS.md").write_text((brain / "AGENTS.md").read_text() + "\n## Reflect\n\n" + skill.read_text())
        skill.unlink()
        out = self.tool_args(brain, "--map", "starter/.agents/skills/reflect/SKILL.md=AGENTS.md#reflect")
        self.assertIn("inspect: AGENTS.md#reflect", out)

    def test_bad_brain_path_fails(self):
        out = subprocess.run([sys.executable, str(TOOL), "v0.7.0", "v0.8-alpha.1", "/nonexistent-brain"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)

    def test_line_only_inside_a_fenced_example_is_not_counted_as_present(self):
        brain = self.brain_at("v0.7.0")
        agents = brain / "AGENTS.md"
        new = subprocess.run(["git", "-C", str(ROOT), "show", "v0.8-alpha.1:starter/AGENTS.md"],
                             capture_output=True, text=True, check=True).stdout
        improve = next(l for l in new.splitlines() if l.startswith("3. IMPROVE"))
        agents.write_text(agents.read_text() + "\n```\n" + improve + "\n```\n")
        self.assertRegex(self.run_tool(brain), r"3\. IMPROVE — New standing rule.*\[example L\d+")

    def test_inactive_examples_and_comments_do_not_supply_instructions(self):
        brain = self.brain_at("v0.7.0")
        agents = brain / "AGENTS.md"
        original = agents.read_text()
        target = subprocess.check_output(["git", "-C", str(ROOT), "show",
                                          "v0.8-alpha.1:starter/AGENTS.md"], text=True)
        rule = next(line for line in target.splitlines() if line.startswith("3. IMPROVE"))
        cases = [("~~~text", "~~~"), ("````text\n```", "````"), ("~~~\n```", "~~~~"),
                 ("<!--", "-->"), ("<!--\n~~~", "-->")]
        for opening, closing in cases:
            with self.subTest(opening=opening):
                agents.write_text(f"{original}\n{opening}\n{rule}\n{closing}\n")
                self.assertRegex(self.run_tool(brain), r'3\. IMPROVE — New standing rule.*\[example L')
                agents.write_text(agents.read_text() + rule + "\n")
                self.assertRegex(self.run_tool(brain), r'3\. IMPROVE — New standing rule.*\[have L')

    def test_absent_existing_file_and_comparison_direction(self):
        brain = self.brain_at("v0.7.0")
        (brain / "CLAUDE.md").unlink()
        out = self.run_tool(brain)
        self.assertIn("CLAUDE.md: absent locally; present at both refs", out)
        self.assertIn("local → target, comparison only:", out)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(shutil.which("git") and has_ref("v0.9.1"), "needs release tags")
class HostBlockAndPluginTests(unittest.TestCase):
    """Upgrades also cover the RepoPrompt CE block brains copy into AGENTS.md, and name changed plugins."""

    def brain(self, with_block):
        brain = Path(tempfile.mkdtemp(prefix="minibrain-upgrade-"))
        self.addCleanup(shutil.rmtree, brain)
        archive = subprocess.run(["git", "-C", str(ROOT), "archive", "v0.9.1", "starter"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "--strip-components=1", "-C", str(brain)], input=archive.stdout, check=True)
        if with_block:
            host = subprocess.run(["git", "-C", str(ROOT), "show", "v0.9.1:hosts/repoprompt.md"],
                                  capture_output=True, text=True, check=True).stdout
            agents = brain / "AGENTS.md"
            agents.write_text(agents.read_text() + "\n" + host[host.index("<rpce_tooling_guidance>"):])
        return brain

    def run_tool(self, brain):
        return subprocess.run([sys.executable, str(TOOL), "HEAD", str(brain), "--from", "v0.9.1"],
                              capture_output=True, text=True, check=True).stdout

    def test_block_is_compared_only_when_the_brain_has_it(self):
        out = self.run_tool(self.brain(with_block=True))
        self.assertIn("inspect: AGENTS.md (RepoPrompt CE block)", out)
        self.assertRegex(out, r"\+ - MAP — .*\[missing\]")
        without = self.run_tool(self.brain(with_block=False))
        self.assertIn("not compared; AGENTS.md has no RepoPrompt CE block", without)
        self.assertRegex(without, r"\+ - MAP — .*\[not compared\]")
        self.assertIn("--map hosts/repoprompt.md=AGENTS.md#<heading>", without)

    def test_block_kept_under_a_heading_is_compared_through_map(self):
        brain = self.brain(with_block=False)
        agents = brain / "AGENTS.md"
        agents.write_text(agents.read_text() + "\n## RepoPrompt tooling\n\n- NAME — local wording.\n")
        out = subprocess.run([sys.executable, str(TOOL), "HEAD", str(brain), "--from", "v0.9.1",
                              "--map", "hosts/repoprompt.md=AGENTS.md#RepoPrompt tooling"],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("inspect: AGENTS.md#RepoPrompt tooling (RepoPrompt CE block)", out)
        self.assertRegex(out, r"\+ - MAP — .*\[missing\]")

    def test_changed_and_removed_plugins_are_named(self):
        out = self.run_tool(self.brain(with_block=False))
        self.assertIn("plugins added upstream: app", out)
        self.assertIn("plugins removed upstream: map, roadmap", out)
