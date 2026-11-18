"""Synthetic release histories: never commit an adopter's instructions or notes."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.upgrade_base import estimate, fingerprint


class EstimateTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.repo = Path(td.name) / "repo"
        self.brain = Path(td.name) / "brain"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "test@example.invalid")
        self.release("v1.0.0", "old", "first")
        self.git("tag", "v1.0.1")
        self.release("v1.1.0", "old", "second")
        self.release("v2.0.0", "new", "third")
        self.write(self.brain, "old", "first", local=True)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args])

    def write(self, root, helper, rules, local=False):
        (root / "tools").mkdir(parents=True, exist_ok=True)
        name = "Map.md" if local else "MAP.md"
        (root / "tools/minibrain.py").write_text(f'MAP_FILE = "{name}"\nVERSION = "{helper}"\n')
        (root / "AGENTS.md").write_text(f"# Scope\n\nRule {rules}.\n")

    def release(self, tag, helper, rules):
        self.write(self.repo / "starter", helper, rules)
        self.git("add", "starter")
        self.git("commit", "-qm", tag)
        self.git("tag", tag)

    def run_estimate(self):
        return estimate(self.repo, "HEAD", self.brain)

    def test_equivalent_tags_share_a_review_without_provenance_claim(self):
        r = self.run_estimate()
        group = r["groups"][0]
        self.assertTrue(group["equivalent"])
        self.assertEqual(group["refs"], ["v1.0.0", "v1.0.1"])
        self.assertIn(r["recommended"], group["refs"])
        self.assertEqual(group["evidence"]["tools/minibrain.py"], "identical after config")

    def test_shared_helper_and_adapted_prose_are_not_enough(self):
        self.write(self.brain, "old", "locally chosen")
        self.assertIsNone(self.run_estimate()["recommended"])

    def test_conflicting_exact_evidence(self):
        self.write(self.brain, "new", "first")
        r = self.run_estimate()
        self.assertIsNone(r["recommended"])
        self.assertIn("conflict", r["reason"])

    def test_target_match_cannot_hide_an_unchecked_skill(self):
        self.write(self.brain, "new", "third")
        self.assertIsNone(self.run_estimate()["recommended"])

    def test_two_component_alpha_tag_is_not_dropped(self):
        self.git("tag", "v2.1-alpha.1")
        refs = [ref for g in self.run_estimate()["groups"] for ref in g["refs"]]
        self.assertIn("v2.1-alpha.1", refs)

    def test_no_tags_is_normal(self):
        self.git("tag", "-d", "v1.0.0", "v1.0.1", "v1.1.0", "v2.0.0")
        self.assertEqual(self.run_estimate()["groups"], [])

    def test_closer_future_tag_is_not_a_candidate(self):
        self.release("v3.0.0", "future", "later")
        r = estimate(self.repo, "v2.0.0", self.brain)
        self.assertNotIn("v3.0.0", [ref for g in r["groups"] for ref in g["refs"]])

    def test_config_mask_never_discards_executable_suffix(self):
        path = "tools/minibrain.py"
        for changed in ('MAP_FILE = "MAP.md"; run()\n', 'MAP_FILE = run()\n'):
            self.assertNotEqual(fingerprint(path, changed), fingerprint(path, 'MAP_FILE = "Map.md"\n'))
