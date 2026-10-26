"""Exercise the actual Git fixtures without poisoning this test runner's environment."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import test_git_reference


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("git"), "Git is required for fixture isolation checks")
class FixtureEnvironmentTests(unittest.TestCase):
    def test_inherited_git_environment_cannot_redirect_fixture_commands(self):
        fixtures = (
            ("test_distribution_integrity.py", "CopiedTemplateSmokeTests.test_adapted_starter_forms_a_valid_disposable_brain"),
            ("test_git_reference.py", "GitReferenceTests.test_check_is_clean_and_read_only"),
            ("test_git_reference.py", "GitReferenceTests.test_ignore_command_failure_is_not_a_pass"),
            ("test_git_reference.py", "GitReferenceTests.test_metadata_write_failure_retains_held_state"),
        )
        clean_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        clean_env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                         GIT_CONFIG_COUNT="0")
        for filename, test in fixtures:
            for poison in ("index", "repository"):
                with self.subTest(fixture=filename, test=test, poison=poison), tempfile.TemporaryDirectory(
                        prefix="minibrain-fixture-env-") as directory:
                    external = Path(directory)
                    repo = external / "unrelated-repo"
                    repo.mkdir()

                    def git(*args):
                        result = subprocess.run(["git", "-C", str(repo), *args], env=clean_env,
                                                text=True, capture_output=True, timeout=15)
                        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

                    git("init", "-q")
                    (repo / "sentinel.txt").write_text("Unrelated disposable repository.\n")
                    git("add", "--", "sentinel.txt")
                    git("-c", "user.name=Synthetic Test", "-c", "user.email=test@example.invalid",
                        "-c", "commit.gpgsign=false", "-c", "maintenance.auto=false",
                        "-c", "gc.auto=0", "commit", "-qm", "Create disposable sentinel")
                    index = external / "index-sentinel"
                    index.write_bytes(b"Not a Git index; must remain untouched.\n")

                    def snapshot():
                        return {path.relative_to(external).as_posix():
                                path.read_bytes() if path.is_file() else None
                                for path in external.rglob("*")}

                    before = snapshot()
                    poisoned_env = dict(clean_env)
                    if poison == "index":
                        poisoned_env["GIT_INDEX_FILE"] = str(index)
                    else:
                        poisoned_env.update(
                            GIT_DIR=str(repo / ".git"), GIT_COMMON_DIR=str(repo / ".git"),
                            GIT_WORK_TREE=str(repo), GIT_INDEX_FILE=str(repo / ".git/index"),
                            GIT_OBJECT_DIRECTORY=str(repo / ".git/objects"),
                        )
                    # Run only the named existing case, never this regression or
                    # full discovery. The real caller's environment stays intact.
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "tests" / filename), test],
                        cwd=ROOT, env=poisoned_env, text=True, capture_output=True, timeout=60,
                    )
                    output = result.stdout + result.stderr
                    after = snapshot()
                    changed = sorted(name for name in before.keys() | after.keys()
                                     if name not in before or name not in after or before[name] != after[name])
                    self.assertEqual(changed, [], output)
                    self.assertEqual(result.returncode, 0, output)
                    self.assertIn("Ran 1 test", output)
                    self.assertNotIn("skipped", output)

    def test_in_process_helper_restores_environment_after_success_and_failure(self):
        for fail in (False, True):
            with self.subTest(fail=fail), mock.patch.dict(os.environ):
                class HelperFixture(test_git_reference.GitReferenceTests):
                    def runTest(self):
                        self.load_helper()
                        # Do not render potentially sensitive environment values on failure.
                        self.assertTrue(dict(os.environ) == self.env,
                                        "In-process helper did not receive the fixture environment")
                        if fail:
                            raise RuntimeError("synthetic test failure")

                before = dict(os.environ)
                result = unittest.TestResult()
                HelperFixture().run(result)
                self.assertTrue(dict(os.environ) == before, "Caller environment was not restored")
                self.assertEqual(result.failures, [])
                self.assertEqual(len(result.errors), int(fail))
                if fail:
                    self.assertIn("synthetic test failure", result.errors[0][1])


if __name__ == "__main__":
    unittest.main()
