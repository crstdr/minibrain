"""Tests of the reference helper, not agent behaviour or the separate eval project."""
import contextlib
import errno
import importlib.util
import io
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HELPER = Path(__file__).resolve().parents[1] / "starter/tools/minibrain.py"


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
            "MAP.md": "# Map\n\n- [[Project]] — synthetic state.\n",
            "CHANGELOG.md": "# Changelog\n\n2026-01-01 - Created synthetic fixture.\n",
            "topics/Project.md": "# Project\n\n## Current status\n\nSynthetic.\n\n## History\n",
            "tools/minibrain.py": HELPER.read_text(),
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
        r = subprocess.run([sys.executable, str(self.root / "tools/minibrain.py"), *args],
                           env=self.env, text=True, capture_output=True, timeout=15)
        self.assertEqual(r.returncode, expected, r.stdout + r.stderr)
        return r.stdout

    def acquire(self, seat="Alpha"):
        out = self.tool("lock", seat)
        match = re.search(r"lock acquired: ([A-Za-z0-9_-]+/[0-9a-f]+)", out)
        self.assertIsNotNone(match, out)
        self.assertIn(f"tools/minibrain.py unlock {match.group(1)}", out)
        return match.group(1)

    def test_map_case_requires_an_explicit_legacy_binding(self):
        # Two steps work on case-insensitive filesystems too; the helper uses
        # exact inventory names rather than relying on Path.exists casing.
        self.git("mv", "MAP.md", "temporary-map.md")
        self.git("mv", "temporary-map.md", "Map.md")
        self.write("CHANGELOG.md", "# Changelog\n\n2026-01-02 - Use the legacy map spelling.\n")
        self.git("add", "--", "CHANGELOG.md")
        out = self.tool("check", expected=1)
        self.assertIn("MAP.md", out)
        helper = (self.root / "tools/minibrain.py").read_text()
        self.write("tools/minibrain.py", helper.replace('MAP_FILE = "MAP.md"', 'MAP_FILE = "Map.md"'))
        self.assertNotIn("PROBLEM:", self.tool("check"))

    def test_cli_usage_names_the_installed_helper(self):
        for args in (("unknown",), ("check", "--unknown"), ("lock",), ("unlock",)):
            with self.subTest(args=args):
                out = self.tool(*args, expected=2)
                self.assertIn("usage: python3 tools/minibrain.py", out)
                self.assertNotIn("kb.py", out)

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

    def memory_with_lines(self, count):
        return "# Memory\n## Focus\n## Open threads\n" + "\n" * (count - 3)

    def test_memory_review_threshold_is_advisory_in_both_views(self):
        self.stage_outcome()
        for count in (149, 150, 151, 200):
            memory = self.memory_with_lines(count)
            self.assertEqual(len(memory.splitlines()), count)
            self.write("MEMORY.md", memory)
            self.git("add", "--", "MEMORY.md")
            before = self.git("diff", "--cached").stdout
            for args in (("check",), ("check", "--staged")):
                with self.subTest(lines=count, args=args):
                    out = self.tool(*args)
                    self.assertNotIn("PROBLEM:", out)
                    if count >= 150:
                        self.assertIn(f"warning: MEMORY.md has {count} lines", out)
                        self.assertIn("review threshold: 150", out)
                        self.assertIn("consider reflect at the next useful boundary", out)
                    else:
                        self.assertNotIn("review threshold", out)
            self.assertEqual((self.root / "MEMORY.md").read_text(), memory)
            self.assertEqual(self.git("diff", "--cached").stdout, before)

    def test_memory_review_uses_the_requested_view(self):
        self.stage_outcome()
        for staged_count, working_count in ((150, 149), (149, 150)):
            with self.subTest(staged=staged_count, working=working_count):
                self.write("MEMORY.md", self.memory_with_lines(staged_count))
                self.git("add", "--", "MEMORY.md")
                self.write("MEMORY.md", self.memory_with_lines(working_count))
                self.assertEqual("review threshold" in self.tool("check"), working_count >= 150)
                self.assertEqual("review threshold" in self.tool("check", "--staged"), staged_count >= 150)

    def test_memory_review_warning_does_not_hide_real_errors(self):
        memory = "# Memory\n## Focus\n[[Nowhere]]\n## Open threads\n" + "- item\n" * 13
        memory += "\n" * (150 - len(memory.splitlines()))
        self.write("MEMORY.md", memory)
        self.stage_outcome()
        self.git("add", "--", "MEMORY.md")
        for args in (("check",), ("check", "--staged")):
            with self.subTest(args=args):
                out = self.tool(*args, expected=1)
                self.assertIn("warning: MEMORY.md has 150 lines", out)
                self.assertIn("broken wikilink", out)
                self.assertIn("13 open threads", out)

    def test_thread_limits_stay_independent_of_memory_review(self):
        self.stage_outcome()
        for length in (400, 401):
            long_thread = "- " + "x" * (length - 2)
            memory = "# Memory\n## Focus\n## Open threads\n" + "- item\n" * 11 + long_thread + "\n"
            self.write("MEMORY.md", memory)
            self.git("add", "--", "MEMORY.md")
            for args in (("check",), ("check", "--staged")):
                with self.subTest(length=length, args=args):
                    out = self.tool(*args)
                    self.assertNotIn("PROBLEM:", out)
                    self.assertNotIn("review threshold", out)
                    self.assertEqual("warning: thread over 400 characters" in out, length > 400)

    def test_duplicate_and_reordered_headings(self):
        self.write("MEMORY.md", "## Open threads\n## Focus\n## Focus\n")
        out = self.tool("check", expected=1)
        self.assertIn("more than one", out)
        self.assertIn("must be ordered", out)

    def test_unregistered_and_duplicate_map_entries(self):
        self.write("MAP.md", "# Map\n")
        self.assertIn("not registered", self.tool("check", expected=1))
        self.write("MAP.md", "- [[Project]]\n- [[Project]]\n")
        self.assertIn("registered 2 times", self.tool("check", expected=1))

    def test_duplicate_supporting_basename(self):
        self.write("sources/Project.md", "# Supporting example\n")
        self.git("add", "--", "sources/Project.md")
        self.assertIn("duplicate Markdown basename", self.tool("check", expected=1))

    def test_ignored_managed_topic_is_rejected(self):
        self.write(".gitignore", "/topics/Hidden.md\n")
        self.write("topics/Hidden.md", "# Hidden\n")
        self.write("MAP.md", "- [[Project]]\n- [[Hidden]]\n")
        self.assertIn("managed Markdown is ignored", self.tool("check", expected=1))

    def test_staged_ignore_policy_cannot_be_hidden_by_later_working_edit(self):
        self.write(".gitignore", "/topics/Project.md\n")
        self.git("add", "--", ".gitignore")
        self.write(".gitignore", "")
        before = self.git("diff", "--cached").stdout
        self.assertNotIn("PROBLEM", self.tool("check"))
        out = self.tool("check", "--staged", expected=1)
        self.assertIn("cannot validate staged ignore rules: .gitignore", out)
        self.assertEqual(self.git("diff", "--cached").stdout, before)
        self.assertEqual((self.root / ".gitignore").read_text(), "")

    def test_working_ignore_policy_is_not_reported_as_staged_policy(self):
        self.write(".gitignore", "")
        self.git("add", "--", ".gitignore")
        self.write(".gitignore", "/topics/Project.md\n")
        self.assertIn("managed Markdown is ignored", self.tool("check", expected=1))
        out = self.tool("check", "--staged", expected=1)
        self.assertIn("cannot validate staged ignore rules: .gitignore", out)
        self.assertNotIn("managed Markdown is ignored", out)

    def test_untracked_root_and_nested_ignore_files_block_staged_view(self):
        # Excluding the ignore files themselves keeps them out of git status;
        # neither staged-change nor dirty-path checks can establish this boundary.
        self.write(".git/info/exclude", ".gitignore\n")
        for rel in (".gitignore", "topics/.gitignore"):
            with self.subTest(rel=rel):
                self.write(rel, "Project.md\n")
                self.assertEqual(self.git("status", "--porcelain").stdout, "")
                out = self.tool("check", "--staged", expected=1)
                self.assertIn(f"cannot validate staged ignore rules: {rel}", out)
                self.assertNotIn("managed Markdown is ignored", out)
                (self.root / rel).unlink()

    def test_unstaged_ignore_deletion_blocks_staged_view(self):
        for rel in (".gitignore", "topics/.gitignore"):
            with self.subTest(rel=rel):
                self.write(rel, "Project.md\n")
                self.git("add", "--", rel)
                self.git("commit", "-qm", "Synthetic ignore policy")
                (self.root / rel).unlink()
                self.assertEqual(self.git("diff", "--cached", "--name-only").stdout, "")
                out = self.tool("check", "--staged", expected=1)
                self.assertIn(f"cannot validate staged ignore rules: {rel}", out)
                self.git("rm", "--cached", "--", rel)
                self.git("commit", "-qm", "Remove synthetic ignore policy")

    def test_new_indexed_ignore_file_missing_on_disk_blocks_staged_view(self):
        self.write(".gitignore", "Project.md\n")
        self.git("add", "--", ".gitignore")
        (self.root / ".gitignore").unlink()
        self.assertIn("cannot validate staged ignore rules: .gitignore",
                      self.tool("check", "--staged", expected=1))

    def test_staged_ignore_deletion_cannot_use_retained_working_file(self):
        self.write(".gitignore", "Project.md\n")
        self.git("add", "--", ".gitignore")
        self.git("commit", "-qm", "Synthetic ignore policy")
        self.git("rm", "--cached", "--", ".gitignore")
        out = self.tool("check", "--staged", expected=1)
        self.assertIn("cannot validate staged ignore rules: .gitignore", out)
        self.assertNotIn("managed Markdown is ignored", out)
        (self.root / ".gitignore").unlink()
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def test_matching_new_nested_ignore_policy_is_checked(self):
        self.write("topics/.gitignore", "Project.md\n")
        self.git("add", "--", "topics/.gitignore")
        out = self.tool("check", "--staged", expected=1)
        self.assertIn("managed Markdown is ignored", out)
        self.assertNotIn("cannot validate staged ignore rules", out)
        self.write("topics/.gitignore", "Scratch.txt\n")
        self.git("add", "--", "topics/.gitignore")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def test_staged_ignore_allows_autocrlf_but_refuses_real_edits(self):
        self.write(".gitignore", "Scratch.txt\n")
        self.git("add", "--", ".gitignore")
        self.git("commit", "-qm", "Synthetic ignore policy")
        self.git("config", "core.autocrlf", "true")
        (self.root / ".gitignore").unlink()
        self.git("checkout", "--", ".gitignore")
        self.assertEqual((self.root / ".gitignore").read_bytes(), b"Scratch.txt\r\n")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))
        (self.root / ".gitignore").write_bytes(b"Project.md\r\n")
        self.assertIn("cannot validate staged ignore rules", self.tool("check", "--staged", expected=1))

    def test_staged_ignore_does_not_normalize_lone_carriage_returns(self):
        self.write(".gitignore", "Scratch.txt\nProject.md\n")
        self.git("add", "--", ".gitignore")
        (self.root / ".gitignore").write_bytes(b"Scratch.txt\rProject.md\n")
        self.assertIn("cannot validate staged ignore rules", self.tool("check", "--staged", expected=1))

    def test_staged_ignore_refuses_transformed_rules_without_running_clean_filter(self):
        marker = Path(self.temp.name) / "filter-ran"
        script = Path(self.temp.name) / "ignore-filter.py"
        script.write_text("import pathlib, sys\n"
                          f"pathlib.Path({str(marker)!r}).write_text('ran')\n"
                          "sys.stdout.buffer.write(sys.stdin.buffer.read().replace(b'Scratch.txt', b'Project.md'))\n")
        self.git("config", "filter.ignore-policy.clean", shlex.join([sys.executable, str(script)]))
        self.write(".gitattributes", ".gitignore filter=ignore-policy\n")
        self.write(".gitignore", "Scratch.txt\n")
        self.git("add", "--", ".gitignore", ".gitattributes")
        self.assertEqual(self.git("show", ":.gitignore").stdout, "Project.md\n")
        marker.unlink()
        self.assertIn("cannot validate staged ignore rules", self.tool("check", "--staged", expected=1))
        self.assertFalse(marker.exists(), "staged ignore validation must not execute clean filters")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO test requires POSIX")
    def test_staged_fifo_ignore_is_reported_before_git_status_can_reopen_it(self):
        os.mkfifo(self.root / ".gitignore")
        self.assertIn("cannot validate staged ignore rules: .gitignore",
                      self.tool("check", "--staged", expected=1))

    def test_nested_space_ancestor_ignore_file_is_relevant(self):
        self.add_spaces()
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces")
        self.write("spaces/Garden/spaces/.gitignore", "Budget.md\n")
        out = self.tool("check", "--staged", expected=1)
        self.assertIn("cannot validate staged ignore rules: spaces/Garden/spaces/.gitignore", out)

    def test_ignore_files_outside_indexed_managed_ancestors_do_not_block(self):
        self.write("sources/.gitignore", "*\n")
        self.write("topics/unused/.gitignore", "*\n")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def test_staged_ignore_guard_does_not_follow_symlinks(self):
        self.write(".gitignore", "Scratch.txt\n")
        self.git("add", "--", ".gitignore")
        target = Path(self.temp.name) / "outside-ignore"
        target.write_text("Scratch.txt\n")
        (self.root / ".gitignore").unlink()
        self.symlink(self.root / ".gitignore", target)
        self.assertIn("cannot validate staged ignore rules", self.tool("check", "--staged", expected=1))

    def test_staged_ignore_guard_reports_unreadable_file(self):
        self.write(".gitignore", "Scratch.txt\n")
        self.git("add", "--", ".gitignore")
        helper = self.load_helper()
        original = helper.git
        def failing(*args, **kwargs):
            if args[0] == "cat-file" and kwargs.get("binary"):
                return subprocess.CompletedProcess(args, 128, b"", b"synthetic unreadable ignore file")
            return original(*args, **kwargs)
        with mock.patch.object(helper, "git", side_effect=failing), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(staged_view=True), 1)
        self.assertIn("cannot validate staged ignore rules", output.getvalue())
        self.assertIn("synthetic unreadable ignore file", output.getvalue())

    def test_inaccessible_ignore_path_is_not_treated_as_absent(self):
        helper = self.load_helper()
        problems = []
        with mock.patch.object(Path, "lstat", side_effect=PermissionError("synthetic inaccessible path")):
            self.assertFalse(helper.staged_ignore_rules_match({"topics/Project.md"}, {}, problems))
        self.assertTrue(any("cannot validate staged ignore rules" in problem and
                            "synthetic inaccessible path" in problem for problem in problems))

    def test_local_and_global_exclusions_remain_active_in_both_views(self):
        for rel in (".git/info/exclude", "global-ignore"):
            with self.subTest(rel=rel):
                self.write(rel, "Project.md\n")
                if rel == "global-ignore":
                    self.git("config", "core.excludesFile", str(self.root / rel))
                for args in [("check",), ("check", "--staged")]:
                    self.assertIn("managed Markdown is ignored", self.tool(*args, expected=1))
                (self.root / rel).unlink()

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
        spec = importlib.util.spec_from_file_location("synthetic_minibrain", self.root / "tools/minibrain.py")
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
        self.write("MAP.md", "- [[Project]]\n- [[New]]\n")
        self.write("MEMORY.md", "## Focus\n[[New]]\n## Open threads\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "MEMORY.md")
        before = self.git("diff", "--cached").stdout
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.assertIn("broken wikilink", self.tool("check", "--staged", expected=1))
        self.assertEqual(before, self.git("diff", "--cached").stdout)
        self.git("add", "--", "topics/New.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def test_unstaged_map_cannot_mask_incomplete_index(self):
        self.write("topics/New.md", "# New\n")
        self.write("MAP.md", "- [[Project]]\n- [[New]]\n")
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
        self.write("MAP.md", "- [[Renamed topic]]\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def add_spaces(self):
        self.write("MAP.md", "# Map\n- [[Project]]\n- [[spaces/Garden/index]]\n- [[spaces/Travel/index.md|Travel]]\n")
        for name in ("Garden", "Travel"):
            self.write(f"spaces/{name}/index.md", f"# {name}\n\n## Current status\nSynthetic.\n\n## Spaces\n- [[spaces/{name}/spaces/Budget]]\n")
            self.write(f"spaces/{name}/spaces/Budget.md", "# Budget\nSynthetic.\n")

    def test_spaces_repeat_index_and_leaf_names_with_qualified_links(self):
        self.add_spaces()
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces/Garden/index.md", "spaces/Garden/spaces/Budget.md",
                 "spaces/Travel/index.md", "spaces/Travel/spaces/Budget.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def test_spaces_reject_ambiguous_bare_links(self):
        self.add_spaces()
        self.write("MEMORY.md", "# Memory\n## Focus\n[[Budget]] [[index]]\n## Open threads\n")
        self.assertIn("ambiguous wikilink", self.tool("check", expected=1))

    def test_spaces_require_the_correct_parent_registry(self):
        self.add_spaces()
        self.write("spaces/Garden/index.md", "# Garden\n## Spaces\n")
        with (self.root / "MAP.md").open("a") as out:
            out.write("- [[spaces/Garden/spaces/Budget]]\n")
        out = self.tool("check", expected=1)
        self.assertIn("outside its parent index", out)
        self.assertIn("not registered in spaces/Garden/index.md", out)

    def test_spaces_require_missing_parent_index(self):
        self.add_spaces()
        (self.root / "spaces/Garden/index.md").unlink()
        self.assertIn("space missing parent index", self.tool("check", expected=1))

    def test_spaces_count_resolved_alias_registrations(self):
        self.add_spaces()
        with (self.root / "spaces/Garden/index.md").open("a") as out:
            out.write("- [[spaces/Garden/spaces/Budget.md|Budget details]]\n")
        self.assertIn("registered 2 times", self.tool("check", expected=1))

    def test_spaces_support_direct_children_and_recursive_namespaces(self):
        self.add_spaces()
        self.write("spaces/Garden/Notes.md", "# Notes\n")
        with (self.root / "spaces/Garden/index.md").open("a") as out:
            out.write("- [[spaces/Garden/Notes]]\n- [[spaces/Garden/spaces/Seeds/index]]\n")
        self.write("spaces/Garden/spaces/Seeds/index.md", "# Seeds\n## Spaces\n- [[spaces/Garden/spaces/Seeds/spaces/Suppliers]]\n")
        self.write("spaces/Garden/spaces/Seeds/spaces/Suppliers.md", "# Suppliers\n")
        self.assertNotIn("PROBLEM", self.tool("check"))

    def test_spaces_asset_markdown_is_data_not_canonical_registration(self):
        self.add_spaces()
        self.write("spaces/Garden/assets/Excerpt.md", "# Quoted source\n[[Not a memory instruction]]\n")
        self.assertNotIn("PROBLEM", self.tool("check"))

    def test_spaces_asset_examples_do_not_become_structural_names(self):
        self.add_spaces()
        self.write("spaces/Garden/assets/source/spaces/index.md", "# Quoted example\n[[Not canonical]]\n")
        self.write("spaces/Garden/assets/source/spaces/assets.md", "# Quoted example\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces")
        for args in [("check",), ("check", "--staged")]:
            self.assertNotIn("PROBLEM", self.tool(*args))

    def test_spaces_binary_only_change_requires_outcome(self):
        self.write("spaces/Photo/index.md", "# Photo\n")
        self.write("MAP.md", "- [[Project]]\n- [[spaces/Photo/index]]\n")
        self.write("spaces/Photo/assets/image.bin", "synthetic non-secret asset")
        self.git("add", "--", "spaces/Photo/assets/image.bin")
        self.assertIn("requires staged CHANGELOG", self.tool("check", expected=1))

    def test_spaces_do_not_clone_root_controls(self):
        self.add_spaces()
        for filename in ("AGENTS.md", "CLAUDE.md", "MEMORY.md", "MAP.md", "CHANGELOG.md"):
            with self.subTest(filename=filename):
                rel = f"spaces/Garden/assets/{filename}"
                self.write(rel, "# Must not be auto-loaded\n")
                self.assertIn("root-only control file", self.tool("check", expected=1))
                (self.root / rel).unlink()

    def test_spaces_qualified_links_do_not_normalise_outside_paths(self):
        self.add_spaces()
        for target in ("../outside", "/spaces/Garden/index", "spaces//Garden/index", "spaces/./Garden/index"):
            with self.subTest(target=target):
                self.write("MEMORY.md", f"# Memory\n## Focus\n[[{target}]]\n## Open threads\n")
                self.assertIn("invalid root-relative", self.tool("check", expected=1))

    def test_spaces_prospective_view_cannot_use_unstaged_indexes(self):
        self.add_spaces()
        self.stage_outcome()
        self.git("add", "--", "MAP.md")
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.assertIn("broken wikilink", self.tool("check", "--staged", expected=1))

    def test_spaces_ignored_markdown_is_not_durable(self):
        self.add_spaces()
        self.write(".gitignore", "/spaces/Garden/spaces/Budget.md\n")
        self.assertIn("managed Markdown is ignored", self.tool("check", expected=1))

    def test_spaces_asset_symlink_is_rejected_without_following(self):
        self.add_spaces()
        target = self.root / "synthetic.bin"
        target.write_bytes(b"synthetic")
        link = self.root / "spaces/Garden/assets/image.bin"
        link.parent.mkdir(parents=True)
        self.symlink(link, target)
        self.assertIn("space material is not a regular file", self.tool("check", expected=1))
        self.git("add", "--", "spaces/Garden/assets/image.bin")
        self.stage_outcome()
        self.assertIn("not an ordinary directory or regular file", self.tool("check", "--staged", expected=1))

    def test_spaces_promote_note_to_folder_with_updated_references(self):
        self.write("spaces/Garden.md", "# Garden\n## Current status\nSynthetic.\n")
        self.write("MAP.md", "- [[Project]]\n- [[spaces/Garden]]\n")
        self.write("MEMORY.md", "# Memory\n## Focus\n[[spaces/Garden#Current status]]\n## Open threads\n")
        self.assertNotIn("PROBLEM", self.tool("check"))
        folder = self.root / "spaces/Garden"
        folder.mkdir()
        (self.root / "spaces/Garden.md").rename(folder / "index.md")
        # A logical space link survives note-to-folder growth unchanged.
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.write("MAP.md", "- [[Project]]\n- [[spaces/Garden/index]]\n")
        self.write("MEMORY.md", "# Memory\n## Focus\n[[spaces/Garden/index#Current status]]\n## Open threads\n")
        self.assertNotIn("PROBLEM", self.tool("check"))

    def test_spaces_reject_note_and_folder_collision(self):
        self.add_spaces()
        self.write("spaces/Garden.md", "# Conflicting home\n")
        self.write("MAP.md", "- [[Project]]\n- [[spaces/Garden]]\n- [[spaces/Travel]]\n")
        out = self.tool("check", expected=1)
        self.assertIn("both note and folder entrypoints", out)
        self.assertIn("ambiguous wikilink", out)

    def test_spaces_require_qualified_links_even_before_ambiguity(self):
        self.write("spaces/Garden.md", "# Garden\n")
        self.write("MAP.md", "- [[Project]]\n- [[Garden]]\n")
        self.assertIn("needs a qualified path", self.tool("check", expected=1))

    def test_spaces_do_not_collide_with_legacy_or_supporting_names(self):
        self.add_spaces()
        self.write("archive/Retired/index.md", "# Archived supporting index\n")
        self.write("spaces/Garden/assets/Project.md", "# Quoted source\n")
        self.write("spaces/Project.md", "# New qualified space\n")
        with (self.root / "MAP.md").open("a") as out:
            out.write("- [[spaces/Project]]\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces", "archive/Retired/index.md")
        for args in [("check",), ("check", "--staged")]:
            self.assertNotIn("PROBLEM", self.tool(*args))

    def test_legacy_section_navigation_is_not_a_second_registration(self):
        self.write("MAP.md", "- [[Project]]\n## Related sections\n- [[Project#Current status]]\n- [[Project|Other label]]\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md")
        for args in [("check",), ("check", "--staged")]:
            self.assertNotIn("PROBLEM", self.tool(*args))
        with (self.root / "MAP.md").open("a") as out:
            out.write("- [[Project]]\n")
        self.git("add", "--", "MAP.md")
        for args in [("check",), ("check", "--staged")]:
            self.assertIn("registered 2 times", self.tool(*args, expected=1))

    def test_explicit_root_markdown_link_does_not_fall_back_to_basename(self):
        self.write("MEMORY.md", "## Focus\n[[Project.md]]\n## Open threads\n")
        self.stage_outcome()
        self.git("add", "--", "MEMORY.md")
        for args in [("check",), ("check", "--staged")]:
            self.assertIn("broken wikilink", self.tool(*args, expected=1))

    def test_explicit_root_links_and_reserved_bare_controls(self):
        self.write("README.md", "# Root\n")
        self.write("sources/README.md", "# Supporting readme\n")
        self.write("work/app/AGENTS.md", "# Supporting app instructions\n")
        self.write("MEMORY.md", "## Focus\n[[README.md]] [[AGENTS]]\n## Open threads\n")
        self.stage_outcome()
        self.git("add", "--", "README.md", "sources/README.md", "work/app/AGENTS.md", "MEMORY.md")
        for args in [("check",), ("check", "--staged")]:
            self.assertNotIn("PROBLEM", self.tool(*args))

    def test_spaces_control_filename_guard_precedes_extension_filtering(self):
        self.add_spaces()
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces")
        for folder in ("spaces/Garden", "spaces/Garden/assets"):
            for name in ("agents.md", "AGENTS.MD", "Claude.md", "CLAUDE.MD", "memory.MD", "map.md", "changelog.MD"):
                with self.subTest(folder=folder, name=name):
                    rel = f"{folder}/{name}"
                    self.write(rel, "# Nested control\n")
                    self.assertIn("root-only control file", self.tool("check", expected=1))
                    self.git("add", "--", rel)
                    self.assertIn("root-only control file", self.tool("check", "--staged", expected=1))
                    self.git("rm", "--cached", "-q", "--", rel)
                    (self.root / rel).unlink()
        self.write("spaces/Garden/assets/AGENTS.md.example", "# Data, not a host entrypoint\n")
        self.git("add", "--", "spaces/Garden/assets/AGENTS.md.example")
        for args in [("check",), ("check", "--staged")]:
            self.assertNotIn("PROBLEM", self.tool(*args))

    def test_spaces_duplicate_navigation_sections_are_refused(self):
        self.add_spaces()
        with (self.root / "spaces/Garden/index.md").open("a") as out:
            out.write("\n## Spaces\n- [[spaces/Garden/spaces/Budget]]\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces")
        for args in [("check",), ("check", "--staged")]:
            self.assertIn("multiple active ## Spaces sections", self.tool(*args, expected=1))

    def test_spaces_fenced_navigation_does_not_register_children(self):
        self.add_spaces()
        for fence in ("```", "~~~~"):
            with self.subTest(fence=fence):
                self.write("spaces/Garden/index.md", f"# Garden\n## History\n{fence}markdown\n## Spaces\n- [[spaces/Garden/spaces/Budget]]\n{fence}\n")
                self.stage_outcome()
                self.git("add", "--", "MAP.md", "spaces")
                for args in [("check",), ("check", "--staged")]:
                    self.assertIn("not registered", self.tool(*args, expected=1))

    def test_spaces_real_navigation_ignores_examples_and_related_links(self):
        self.add_spaces()
        self.write("spaces/Garden/index.md", "# Garden\n```markdown\n## Spaces\n- [[spaces/Garden/spaces/Budget]]\n```\n## Spaces\n- [[spaces/Garden/spaces/Budget]]\n## Related\n- [[spaces/Garden/spaces/Budget]]\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces")
        for args in [("check",), ("check", "--staged")]:
            self.assertNotIn("PROBLEM", self.tool(*args))

    def test_spaces_registry_entries_must_be_child_spaces(self):
        self.add_spaces()
        self.write("spaces/Garden/assets/Excerpt.md", "# Quotation\n")
        with (self.root / "spaces/Garden/index.md").open("a") as out:
            out.write("- [[Project]]\n- [[spaces/Garden/assets/Excerpt.md]]\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces")
        for args in [("check",), ("check", "--staged")]:
            self.assertIn("not a direct child space", self.tool(*args, expected=1))

    def test_spaces_reserve_structural_names_before_promotion(self):
        self.add_spaces()
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces")
        for rel in ("spaces/assets.md", "spaces/spaces.md", "spaces/index.md", "spaces/assets/index.md", "spaces/Garden/spaces/assets/index.md", "spaces/Garden/spaces/index.md", "spaces/Garden/assets.md"):
            with self.subTest(rel=rel):
                self.write(rel, "# Reserved canonical name\n")
                self.assertIn("reserved space name", self.tool("check", expected=1))
                self.git("add", "--", rel)
                self.assertIn("reserved space name", self.tool("check", "--staged", expected=1))
                self.git("rm", "--cached", "-q", "--", rel)
                (self.root / rel).unlink()

    def test_spaces_staged_promotion_needs_both_halves(self):
        text = "# Garden\n## Current status\nPreserved synthetic knowledge.\n"
        self.write("spaces/Garden.md", text)
        self.write("MAP.md", "- [[Project]]\n- [[spaces/Garden]]\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md", "spaces/Garden.md")
        self.git("commit", "-qm", "Synthetic space")
        (self.root / "spaces/Garden").mkdir()
        (self.root / "spaces/Garden.md").rename(self.root / "spaces/Garden/index.md")
        self.write("CHANGELOG.md", "# Changelog\n2026-01-03 - Promoted synthetic Garden.\n")
        self.git("add", "--", "CHANGELOG.md", "spaces/Garden/index.md")
        self.assertIn("both note and folder entrypoints", self.tool("check", "--staged", expected=1))
        self.git("rm", "--cached", "-q", "--", "spaces/Garden.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))
        self.assertEqual((self.root / "spaces/Garden/index.md").read_text(), text)
        self.assertIn("[[spaces/Garden]]", (self.root / "MAP.md").read_text())

    def test_spaces_staged_child_requires_staged_parent(self):
        self.add_spaces()
        self.stage_outcome()
        self.git("add", "--", "spaces/Garden/spaces/Budget.md")
        self.assertIn("space missing parent index", self.tool("check", "--staged", expected=1))

    def test_local_remote_policy_rejects_network_remote(self):
        helper = self.load_helper()
        self.git("remote", "add", "example", "https://example.invalid/repo.git")
        with mock.patch.object(helper, "REQUIRE_LOCAL_REMOTES", True), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(), 1)
        self.assertIn("remote is not an absolute filesystem path", output.getvalue())


if __name__ == "__main__":
    unittest.main()
