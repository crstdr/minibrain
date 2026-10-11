"""Tests of the reference helper, not agent behaviour or the separate eval project."""
import contextlib
import errno
import importlib.util
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HELPER = Path(__file__).resolve().parents[1] / "examples/git-markdown/tools/kb.py"


@unittest.skipUnless(shutil.which("git"), "Git is required for the Git reference")
class GitReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="minibrain-reference-")
        self.root = Path(self.temp.name) / "brain"
        self.root.mkdir()
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="maintenance.auto",
                        GIT_CONFIG_VALUE_0="false", GIT_CONFIG_KEY_1="gc.auto", GIT_CONFIG_VALUE_1="0")
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        content = {
            "AGENTS.md": "# Synthetic instructions\n",
            "MEMORY.md": "# Memory\n\n## Focus\n\nSynthetic fixture.\n\n## Open threads\n\n",
            "Map.md": "# Map\n\n- [[Project]] — synthetic state.\n",
            "CHANGELOG.md": "# Changelog\n\n2026-01-01 - Created synthetic fixture.\n",
            "topics/Project.md": "# Project\n\n## Current status\n\nSynthetic.\n\n## History\n",
            "tools/kb.py": HELPER.read_text(),
        }
        for name, text in content.items():
            self.write(name, text)
        self.git("add", "--", *content)
        self.git("commit", "-qm", "Synthetic fixture")

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def git(self, *args, ok=True):
        r = subprocess.run(["git", "-C", str(self.root), *args],
                           env=self.env, text=True, capture_output=True)
        if ok:
            self.assertEqual(r.returncode, 0, r.stderr)
        return r

    def tool(self, *args, expected=0):
        r = subprocess.run([sys.executable, str(self.root / "tools/kb.py"), *args],
                           env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(r.returncode, expected, r.stdout + r.stderr)
        return r.stdout

    def acquire(self, seat="Alpha"):
        out = self.tool("lock", seat)
        match = re.search(r"lock acquired: ([A-Za-z0-9_-]+/[0-9a-f]+)", out)
        self.assertIsNotNone(match, out)
        return match.group(1)

    def test_check_is_clean_and_read_only(self):
        before = self.git("status", "--porcelain").stdout
        head = self.git("rev-parse", "HEAD").stdout
        self.assertIn("clean", self.tool("check"))
        self.assertEqual(self.git("status", "--porcelain").stdout, before)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)

    def test_a5_topic_requires_staged_changelog_then_one_commit(self):
        self.write("topics/Project.md", "# Project\n\n## Current status\nChanged.\n")
        self.git("add", "--", "topics/Project.md")
        self.assertIn("requires staged CHANGELOG", self.tool("check", expected=1))
        self.write("CHANGELOG.md", "# Changelog\n\n2026-01-02 - Changed synthetic state.\n")
        self.git("add", "--", "CHANGELOG.md")
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))
        self.git("commit", "-qm", "Synthetic coherent checkpoint")
        paths = set(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.splitlines())
        self.assertEqual(paths, {"topics/Project.md", "CHANGELOG.md"})
        self.assertIn("clean", self.tool("check"))

    def test_a6_reports_broken_link_and_thirteenth_thread(self):
        self.write("MEMORY.md", "# Memory\n## Focus\n[[Nowhere]]\n## Open threads\n" + "- item\n" * 13)
        out = self.tool("check", expected=1)
        self.assertIn("broken wikilink", out)
        self.assertIn("13 open threads", out)

    def test_memory_line_cap(self):
        self.write("MEMORY.md", "# Memory\n## Focus\n## Open threads\n" + "\n" * 150)
        self.assertIn("exceeds 150", self.tool("check", expected=1))

    def test_duplicate_and_reordered_headings(self):
        self.write("MEMORY.md", "## Open threads\n## Focus\n## Focus\n")
        out = self.tool("check", expected=1)
        self.assertIn("more than one", out)
        self.assertIn("must be ordered", out)

    def test_unregistered_and_duplicate_map_entries(self):
        self.write("Map.md", "# Map\n")
        self.assertIn("not registered", self.tool("check", expected=1))
        self.write("Map.md", "- [[Project]]\n- [[Project]]\n")
        self.assertIn("registered 2 times", self.tool("check", expected=1))

    def test_duplicate_supporting_basename(self):
        self.write("sources/Project.md", "# Supporting example\n")
        self.git("add", "--", "sources/Project.md")
        self.assertIn("duplicate Markdown basename", self.tool("check", expected=1))

    def test_ignored_managed_topic_is_rejected(self):
        self.write(".gitignore", "/topics/Hidden.md\n")
        self.write("topics/Hidden.md", "# Hidden\n")
        self.write("Map.md", "- [[Project]]\n- [[Hidden]]\n")
        self.assertIn("managed Markdown is ignored", self.tool("check", expected=1))

    def test_section_anchor_limit_is_explicit(self):
        self.write("MEMORY.md", "# Memory\n## Focus\n[[Project#Absent]]\n## Open threads\n")
        self.assertNotIn("PROBLEM", self.tool("check"))

    def test_topic_structure_is_not_semantically_validated(self):
        self.write("topics/Project.md", "# Project\nNo status/history headings.\n")
        self.assertNotIn("PROBLEM", self.tool("check"))

    def test_unknown_edits_are_reported_not_changed(self):
        self.write("topics/Project.md", "Unfinished synthetic work\n")
        before = (self.root / "topics/Project.md").read_bytes()
        self.assertIn("working tree is dirty", self.tool("check"))
        self.assertEqual((self.root / "topics/Project.md").read_bytes(), before)
        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout, "")

    def test_acquisition_persists_after_process_exit(self):
        label = self.acquire()
        self.assertTrue((self.root / ".git/kb-writer.lock").is_dir())
        self.assertIn(label, self.tool("check"))
        self.tool("unlock", label)

    def test_contending_seat_and_same_seat_both_refused(self):
        label = self.acquire()
        self.assertIn("LOCK HELD", self.tool("lock", "Beta", expected=1))
        self.assertIn("LOCK HELD", self.tool("lock", "Alpha", expected=1))
        self.tool("unlock", label)

    def test_wrong_label_cannot_release(self):
        label = self.acquire()
        self.assertIn("REFUSED", self.tool("unlock", "Alpha/wrong", expected=1))
        self.assertTrue((self.root / ".git/kb-writer.lock").exists())
        self.tool("unlock", label)

    def test_each_acquisition_issues_fresh_label(self):
        first = self.acquire()
        self.tool("unlock", first)
        second = self.acquire()
        self.assertNotEqual(first, second)
        self.tool("unlock", first, expected=1)
        self.tool("unlock", second)

    def test_staged_foreign_work_is_not_unstaged_or_committed(self):
        self.write("work.txt", "synthetic pending staging\n")
        self.git("add", "--", "work.txt")
        before = self.git("diff", "--cached").stdout
        head = self.git("rev-parse", "HEAD").stdout
        self.assertIn("REFUSED", self.tool("lock", "Alpha", expected=1))
        self.assertFalse((self.root / ".git/kb-writer.lock").exists())
        self.assertEqual(self.git("diff", "--cached").stdout, before)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)

    def test_unreadable_owner_is_preserved(self):
        label = self.acquire()
        self.write(".git/kb-writer.lock/meta.json", "not-json")
        self.assertIn("owner is unreadable", self.tool("check"))
        self.tool("unlock", label, expected=1)
        self.tool("lock", "Beta", expected=1)
        self.assertTrue((self.root / ".git/kb-writer.lock").is_dir())

    def test_force_is_only_mechanical(self):
        self.acquire()
        self.tool("unlock", "--force")
        self.assertFalse((self.root / ".git/kb-writer.lock").exists())

    def test_unexpected_lock_contents_never_deleted(self):
        label = self.acquire()
        self.write(".git/kb-writer.lock/unexpected.txt", "preserve")
        self.assertIn("unexpected lock contents", self.tool("unlock", label, expected=1))
        self.tool("unlock", "--force", expected=1)
        self.assertEqual((self.root / ".git/kb-writer.lock/unexpected.txt").read_text(), "preserve")

    def test_lock_symlink_is_refused(self):
        target = Path(self.temp.name) / "foreign"
        target.mkdir()
        self.symlink(self.root / ".git/kb-writer.lock", target, True)
        self.assertIn("not an ordinary directory", self.tool("check", expected=1))
        self.tool("lock", "Alpha", expected=1)
        self.tool("unlock", "--force", expected=1)
        self.assertTrue(target.is_dir())

    def test_lock_path_file_is_refused(self):
        self.write(".git/kb-writer.lock", "unknown")
        self.tool("check", expected=1)
        self.tool("lock", "Alpha", expected=1)
        self.tool("unlock", "--force", expected=1)

    def test_no_repo_does_not_check_parent(self):
        shutil.rmtree(self.root / ".git")
        self.assertIn("dedicated Git", self.tool("check", expected=1))
        self.tool("lock", "Alpha", expected=1)

    def test_worktree_is_explicitly_unsupported(self):
        worktree = Path(self.temp.name) / "worktree"
        self.git("worktree", "add", "--detach", "-q", str(worktree), "HEAD")
        old = self.root
        self.root = worktree
        try:
            self.assertIn("worktrees are unsupported", self.tool("check", expected=1))
            self.tool("lock", "Alpha", expected=1)
        finally:
            self.root = old

    def load_helper(self):
        spec = importlib.util.spec_from_file_location("synthetic_kb", self.root / "tools/kb.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        return helper

    def symlink(self, link, target, is_directory=False):
        try:
            link.symlink_to(target, target_is_directory=is_directory)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"Symlinks unavailable: {error}")

    def stage_outcome(self):
        self.write("CHANGELOG.md", "# Changelog\n2026-01-02 - Synthetic update.\n")
        self.git("add", "--", "CHANGELOG.md")

    def test_staged_check_cannot_resolve_an_untracked_topic(self):
        self.write("topics/New.md", "# New\n")
        self.write("Map.md", "- [[Project]]\n- [[New]]\n")
        self.write("MEMORY.md", "## Focus\n[[New]]\n## Open threads\n")
        self.stage_outcome()
        self.git("add", "--", "Map.md", "MEMORY.md")
        before = self.git("diff", "--cached").stdout
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.assertIn("broken wikilink", self.tool("check", "--staged", expected=1))
        self.assertEqual(before, self.git("diff", "--cached").stdout)
        self.git("add", "--", "topics/New.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def test_unstaged_map_cannot_mask_incomplete_index(self):
        self.write("topics/New.md", "# New\n")
        self.write("Map.md", "- [[Project]]\n- [[New]]\n")
        self.stage_outcome()
        self.git("add", "--", "topics/New.md")
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.assertIn("not registered", self.tool("check", "--staged", expected=1))

    def test_index_check_reads_staged_content_not_later_edits(self):
        self.write("MEMORY.md", "## Focus\n[[Missing]]\n## Open threads\n")
        self.stage_outcome()
        self.git("add", "--", "MEMORY.md")
        self.write("MEMORY.md", "## Focus\n[[Project]]\n## Open threads\n")
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.assertIn("broken wikilink", self.tool("check", "--staged", expected=1))

    def test_index_check_ignores_unstaged_damage_but_resume_reports_it(self):
        self.write("topics/Project.md", "# Project\nSynthetic changed state.\n")
        self.stage_outcome()
        self.git("add", "--", "topics/Project.md")
        self.write("MEMORY.md", "## Focus\n[[Missing]]\n## Open threads\n")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))
        self.assertIn("broken wikilink", self.tool("check", expected=1))

    def test_staged_deletion_of_control_is_not_an_outcome(self):
        self.git("rm", "--cached", "CHANGELOG.md")
        self.assertIn("CHANGELOG.md missing", self.tool("check", "--staged", expected=1))

    def test_symlinked_control_is_rejected(self):
        target = Path(self.temp.name) / "outside.md"
        target.write_text("# External instructions\n")
        (self.root / "AGENTS.md").unlink()
        self.symlink(self.root / "AGENTS.md", target)
        self.assertIn("not a regular file", self.tool("check", expected=1))

    def test_symlinked_topic_is_rejected_in_both_views(self):
        target = Path(self.temp.name) / "outside.md"
        target.write_text("# External knowledge\n")
        (self.root / "topics/Project.md").unlink()
        self.symlink(self.root / "topics/Project.md", target)
        self.assertIn("not a regular file", self.tool("check", expected=1))
        self.stage_outcome()
        self.git("add", "--", "topics/Project.md")
        self.assertIn("not a regular file", self.tool("check", "--staged", expected=1))

    def test_broken_symlink_is_named_not_opened(self):
        self.symlink(self.root / "topics/Broken.md", self.root / "absent")
        self.assertIn("not a regular file", self.tool("check", expected=1))

    def test_supporting_symlink_is_rejected(self):
        self.symlink(self.root / "Other.md", self.root / "topics/Project.md")
        (self.root / "sources").mkdir()
        (self.root / "Other.md").rename(self.root / "sources/Other.md")
        self.git("add", "--", "sources/Other.md")
        self.assertIn("not a regular file", self.tool("check", expected=1))
        self.assertIn("not a regular file", self.tool("check", "--staged", expected=1))

    def test_symlinked_topic_directory_is_not_followed(self):
        target = Path(self.temp.name) / "outside"
        target.mkdir()
        (target / "External.md").write_text("# External\n")
        self.symlink(self.root / "topics/external", target, True)
        self.assertIn("not an ordinary directory", self.tool("check", expected=1))
        self.git("add", "--", "topics/external")
        self.assertIn("not an ordinary directory", self.tool("check", "--staged", expected=1))

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO test requires POSIX")
    def test_fifo_topic_refused_without_reading(self):
        os.mkfifo(self.root / "topics/Pipe.md")
        self.assertIn("not a regular file", self.tool("check", expected=1))

    def test_acquisition_label_has_128_bit_random_component(self):
        label = self.acquire()
        self.assertRegex(label, r"^Alpha/[0-9a-f]{32}$")
        self.tool("unlock", label)

    def test_malformed_force_or_extra_label_never_unlocks(self):
        label = self.acquire()
        for args in [(label, "extra"), (label, "--force"), ("--force", "extra"), ()]:
            self.assertIn("usage:", self.tool("unlock", *args, expected=2))
            self.assertTrue((self.root / ".git/kb-writer.lock").exists())
        self.tool("unlock", label)

    def test_lock_metadata_symlink_is_not_read_or_deleted(self):
        label = self.acquire()
        metadata = self.root / ".git/kb-writer.lock/meta.json"
        target = Path(self.temp.name) / "foreign.json"
        target.write_bytes(metadata.read_bytes())
        metadata.unlink()
        self.symlink(metadata, target)
        self.assertIn("owner is unreadable", self.tool("check"))
        self.tool("unlock", label, expected=1)
        self.tool("unlock", "--force", expected=1)
        self.assertTrue(target.is_file())

    def test_ignore_command_failure_is_not_a_pass(self):
        helper = self.load_helper()
        original = helper.git
        def failing(*args, **kwargs):
            if args[0] == "check-ignore":
                return subprocess.CompletedProcess(args, 129, "", "synthetic unsupported option")
            return original(*args, **kwargs)
        with mock.patch.object(helper, "git", side_effect=failing), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(), 1)
        self.assertIn("cannot verify ignore rules", output.getvalue())

    def test_bad_utf8_memory_is_named_in_both_views(self):
        (self.root / "topics/Project.md").write_bytes(b"# Bad\n\xff")
        self.assertIn("cannot read Markdown", self.tool("check", expected=1))
        self.stage_outcome()
        self.git("add", "--", "topics/Project.md")
        self.assertIn("cannot read Markdown", self.tool("check", "--staged", expected=1))

    @unittest.skipUnless(os.name == "posix", "Byte filenames require POSIX")
    def test_non_utf8_work_filename_does_not_crash_diagnostics(self):
        try:
            with open(os.fsencode(self.root) + b"/work-\xff.txt", "wb") as f:
                f.write(b"synthetic")
        except OSError as error:
            if error.errno in (errno.EILSEQ, errno.EINVAL, errno.ENOTSUP):
                self.skipTest("Filesystem cannot create a non-UTF-8 filename")
            raise
        self.assertIn("working tree is dirty", self.tool("check"))

    def test_metadata_write_failure_retains_held_state(self):
        helper = self.load_helper()
        with mock.patch.object(Path, "write_text", side_effect=OSError("synthetic write failure")), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.lock(["Alpha"]), 1)
        self.assertTrue((self.root / ".git/kb-writer.lock").is_dir())
        self.assertIn("lock remains held", output.getvalue())

    def test_failed_rollback_reports_retained_lock(self):
        self.write("work.txt", "Synthetic staging\n")
        self.git("add", "--", "work.txt")
        helper = self.load_helper()
        with mock.patch.object(helper, "release_lock", return_value=False), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.lock(["Alpha"]), 1)
        self.assertIn("lock remains held", output.getvalue())
        self.assertTrue((self.root / ".git/kb-writer.lock").is_dir())

    def test_missing_git_is_reported_without_traceback(self):
        helper = self.load_helper()
        with mock.patch.object(helper.subprocess, "run", side_effect=FileNotFoundError("synthetic missing Git")), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(), 1)
        self.assertIn("Git unavailable", output.getvalue())

    def test_staged_rename_and_spaces_are_checked(self):
        self.git("mv", "topics/Project.md", "topics/Renamed topic.md")
        self.write("Map.md", "- [[Renamed topic]]\n")
        self.stage_outcome()
        self.git("add", "--", "Map.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def test_local_remote_policy_rejects_network_remote(self):
        helper = self.load_helper()
        self.git("remote", "add", "example", "https://example.invalid/repo.git")
        with mock.patch.object(helper, "REQUIRE_LOCAL_REMOTES", True), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(), 1)
        self.assertIn("remote is not an absolute filesystem path", output.getvalue())


if __name__ == "__main__":
    unittest.main()
