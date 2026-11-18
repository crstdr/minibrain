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
        self.assertRegex(out, r'\+ 3\. IMPROVE — New standing rule.*\[(near|missing)\]')
        self.assertIn("brain: 3. IMPROVE — Recurring friction", out)
        self.assertEqual((brain / "AGENTS.md").read_bytes(), before)  # read-only

    def test_upgraded_brain_reports_identical_files(self):
        out = self.run_tool(self.brain_at("v0.8-alpha.1"))
        self.assertIn("identical to target", out)
        self.assertIn("0 near, 0 missing", out)


if __name__ == "__main__":
    unittest.main()
