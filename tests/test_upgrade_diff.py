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


if __name__ == "__main__":
    unittest.main()
