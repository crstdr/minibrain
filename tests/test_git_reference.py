"""Tests of the reference helper, not agent behaviour or the separate eval project."""
import contextlib
import errno
import importlib.util
import io
import json
import os
from pathlib import Path, PureWindowsPath
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
        # Inherited Git overrides must not redirect commands outside this fixture.
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_EDITOR="false",
                        GIT_CONFIG_COUNT="2", GIT_CONFIG_KEY_0="maintenance.auto",
                        GIT_CONFIG_VALUE_0="false", GIT_CONFIG_KEY_1="gc.auto", GIT_CONFIG_VALUE_1="0")
        self.root = Path(self.temp.name) / "brain"
        self.stage_fixture()
        self.git("commit", "-qm", "Synthetic fixture")

    def stage_fixture(self):
        """A fresh repository at self.root with the synthetic brain staged, not yet committed."""
        self.root.mkdir()
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

    def stage_change(self, status="Changed."):
        """A valid prospective checkpoint: a topic edit with its changelog line, staged by name."""
        self.write("topics/Project.md", f"# Project\n\n## Current status\n\n{status}\n\n## History\n")
        self.write("CHANGELOG.md", f"# Changelog\n\n2026-01-02 - {status}\n2026-01-01 - Created synthetic fixture.\n")
        self.git("add", "--", "topics/Project.md", "CHANGELOG.md")

    def commits(self):
        return self.git("rev-list", "--count", "HEAD").stdout.strip()

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

    def test_intent_to_add_is_not_committed_but_a_staged_empty_file_is(self):
        self.write("topics/New.md", "# New\n")
        self.write("MAP.md", "- [[Project]]\n- [[New]]\n")
        self.stage_outcome()
        self.git("add", "--", "MAP.md")
        self.git("add", "-N", "--", "topics/New.md")
        before = self.git("diff", "--cached", "--ita-visible-in-index").stdout
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.assertIn("broken wikilink", self.tool("check", "--staged", expected=1))
        self.assertEqual(before, self.git("diff", "--cached", "--ita-visible-in-index").stdout)
        self.write("topics/New.md", "")
        self.git("add", "--", "topics/New.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

    def test_deleted_then_intent_to_add_file_stays_out_of_prospective_commit(self):
        self.stage_outcome()
        self.git("rm", "--cached", "--", "topics/Project.md")
        self.git("add", "-N", "--", "topics/Project.md")
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.assertIn("broken wikilink", self.tool("check", "--staged", expected=1))

    def test_intent_to_add_is_filtered_before_prospective_path_validation(self):
        self.write("spaces/AGENTS.md", "# Not committed\n")
        self.git("add", "-N", "--", "spaces/AGENTS.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))
        self.assertIn("root-only", self.tool("check", expected=1))
        self.stage_outcome()
        self.git("add", "--", "spaces/AGENTS.md")
        self.assertIn("root-only", self.tool("check", "--staged", expected=1))

    def test_hidden_change_flags_fail_both_views_without_clearing_flags(self):
        for flag in ("assume-unchanged", "skip-worktree"):
            with self.subTest(flag=flag):
                self.git("update-index", "--" + flag, "--", "topics/Project.md")
                self.write("topics/Project.md", "# Changed but hidden\n")
                before = self.git("ls-files", "-v").stdout
                for args in (("check",), ("check", "--staged")):
                    out = self.tool(*args, expected=1)
                    self.assertIn("Git flags may hide unsaved changes: topics/Project.md", out)
                self.assertEqual(before, self.git("ls-files", "-v").stdout)
                self.git("update-index", "--no-" + flag, "--", "topics/Project.md")
                self.assertNotIn("PROBLEM", self.tool("check"))

    def test_mixed_thread_markers_count_as_separate_items_in_both_views(self):
        self.stage_outcome()
        for count in (12, 13):
            memory = "## Focus\n## Open threads\n" + "".join(
                "-*+"[i % 3] + " item\n  continuation\n" for i in range(count))
            self.write("MEMORY.md", memory)
            self.git("add", "--", "MEMORY.md")
            for args in (("check",), ("check", "--staged")):
                with self.subTest(count=count, args=args):
                    out = self.tool(*args, expected=int(count > 12))
                    self.assertEqual("13 open threads" in out, count > 12)
                    self.assertNotIn("thread over 400 characters", out)

    def test_acknowledgments_are_not_threads_but_their_links_are_checked(self):
        self.stage_outcome()
        for count, target in ((12, "Project"), (13, "Project"), (12, "Missing")):
            with self.subTest(threads=count, target=target):
                memory = ("## Focus\n## Open threads\n" + "- task\n" * count
                          + "\n## Awaiting acknowledgment\n"
                          + f"- 2026-01-02 — Outcome. Source: [[{target}]].\n" * 14)
                self.write("MEMORY.md", memory)
                self.git("add", "--", "MEMORY.md")
                expected = int(count > 12 or target == "Missing")
                for args in (("check",), ("check", "--staged")):
                    out = self.tool(*args, expected=expected)
                    self.assertEqual("13 open threads" in out, count > 12)
                    self.assertEqual("broken wikilink" in out, target == "Missing")

    def test_fenced_memory_examples_do_not_count_but_raw_lines_and_links_do(self):
        self.stage_outcome()
        for fence in ("```", "~~~~"):
            with self.subTest(fence=fence):
                memory = ("## Focus\n## Open threads\n- real\n" + fence + "markdown\n"
                          "## Open threads\n" + "- example\n" * 13 + fence + "\n")
                memory += "\n" * (150 - len(memory.splitlines()))
                self.write("MEMORY.md", memory)
                self.git("add", "--", "MEMORY.md")
                for args in (("check",), ("check", "--staged")):
                    out = self.tool(*args)
                    self.assertIn("MEMORY.md has 150 lines", out)
                    self.assertNotIn("PROBLEM", out)
                self.write("MEMORY.md", memory + fence + "\n[[Missing]]\n" + fence + "\n")
                self.git("add", "--", "MEMORY.md")
                for args in (("check",), ("check", "--staged")):
                    self.assertIn("broken wikilink", self.tool(*args, expected=1))

    def test_fenced_legacy_map_examples_neither_register_nor_duplicate_topics(self):
        self.stage_outcome()
        for fence in ("```", "~~~~"):
            for real in (True, False):
                with self.subTest(fence=fence, real=real):
                    sample = fence + "markdown\n- [[Project]]\n" + fence + "\n"
                    self.write("MAP.md", ("- [[Project]]\n" if real else "") + sample)
                    self.git("add", "--", "MAP.md")
                    for args in (("check",), ("check", "--staged")):
                        out = self.tool(*args, expected=int(not real))
                        self.assertEqual("not registered" in out, not real)

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

    def test_a8_staged_path_edited_after_staging_is_a_problem_in_staged_view_only(self):
        self.write("topics/Project.md", "# Project\n\n## Current status\nStaged version.\n")
        self.write("CHANGELOG.md", "# Changelog\n\n2026-01-02 - Changed synthetic state.\n")
        self.git("add", "--", "topics/Project.md", "CHANGELOG.md")
        self.write("topics/Project.md", "# Project\n\n## Current status\nEdited after staging.\n")
        out = self.tool("check", "--staged", expected=1)
        self.assertIn("edited after staging", out)
        self.assertIn("topics/Project.md", out)
        self.assertNotIn("edited after staging", self.tool("check"))
        self.git("add", "--", "topics/Project.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))

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
                # The working edit after staging is now itself a PROBLEM in the staged view (A8);
                # the view-specific threshold still comes from the index.
                staged_out = self.tool("check", "--staged", expected=1)
                self.assertIn("edited after staging", staged_out)
                self.assertEqual("review threshold" in staged_out, staged_count >= 150)

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
        # In-process calls need the same isolation as subprocesses; restore the
        # caller's environment even when import or the test itself fails.
        environment = mock.patch.dict(os.environ, self.env, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
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

    def test_commit_refuses_without_the_lock_holders_label_staged_paths_or_a_message(self):
        label = self.acquire()
        self.assertIn("nothing is staged", self.tool("commit", "--label", label, "-m", "x", expected=1))
        self.stage_change()
        self.assertIn("use this session's issued label", self.tool("commit", "-m", "x", expected=1))
        self.assertIn("not Alpha/0000", self.tool("commit", "--label", "Alpha/0000", "-m", "x", expected=1))
        for args in [(), ("-m",), ("-a", "-m", "x"), ("-m", "x", "topics/Project.md")]:
            self.assertIn("usage:", self.tool("commit", "--label", label, *args, expected=2))
        self.assertEqual(self.commits(), "1")
        self.tool("unlock", label)
        self.assertIn(f"no lock is held for {label}", self.tool("commit", "--label", label, "-m", "x", expected=1))
        self.assertIn("needs --label", self.tool("commit", "--amend", expected=1))
        self.assertEqual(self.commits(), "1")

    def test_commit_refuses_on_a_staged_problem_and_commits_only_the_index(self):
        label = self.acquire()
        self.write("topics/Project.md", "# Project\n\n## Current status\n\nNo changelog line.\n\n## History\n")
        self.git("add", "--", "topics/Project.md")
        out = self.tool("commit", "--label", label, "-m", "Alpha: x", expected=1)
        self.assertIn("PROBLEM", out)
        self.assertIn("REFUSED: fix the PROBLEMs", out)
        self.assertEqual(self.commits(), "1")
        self.stage_change("Second.")
        self.write("MEMORY.md", "# Memory\n\n## Focus\n\nUnstaged edit.\n\n## Open threads\n\n")
        out = self.tool("commit", "--label", label, "-m", "Alpha: Record state",
                        "-m", "Co-Authored-By: Synthetic <test@example.invalid>")
        self.assertIn("committed", out)
        self.assertIn("Alpha: Record state\n\nCo-Authored-By: Synthetic", self.git("log", "-1", "--format=%B").stdout)
        committed = set(self.git("diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.split())
        self.assertEqual(committed, {"topics/Project.md", "CHANGELOG.md"})  # no -a: MEMORY.md stays unstaged
        self.assertTrue((self.root / ".git/kb-writer.lock").is_dir())  # commit never releases
        self.tool("unlock", label)

    def test_commit_amend_is_bound_to_the_acquisitions_own_commit(self):
        label = self.acquire()
        meta = json.loads((self.root / ".git/kb-writer.lock/meta.json").read_text())
        self.assertEqual(meta["head"], self.git("rev-parse", "HEAD").stdout.strip())  # full hash
        self.stage_change("First.")
        self.tool("commit", "--label", label, "-m", "Alpha: First")
        self.write("MAP.md", "# Map\n\n- [[Project]] — synthetic state, amended.\n")
        self.git("add", "--", "MAP.md")
        self.assertIn("(amended)", self.tool("commit", "--label", label, "--amend"))  # keeps the message, no editor
        self.assertEqual(self.commits(), "2")
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), "Alpha: First")
        self.git("commit", "-q", "--allow-empty", "-m", "raw second commit")
        self.stage_change("Third.")
        out = self.tool("commit", "--label", label, "--amend", "-m", "x", expected=1)
        self.assertIn("not this acquisition's own commit", out)
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), "raw second commit")
        self.tool("unlock", label)

    def test_commit_amend_accepts_an_older_helpers_abbreviated_lock_head(self):
        label = self.acquire()
        metadata = self.root / ".git/kb-writer.lock/meta.json"
        meta = json.loads(metadata.read_text())
        meta["head"] = meta["head"][:7]
        metadata.write_text(json.dumps(meta))
        self.stage_change("First.")
        self.tool("commit", "--label", label, "-m", "Alpha: First")
        self.stage_change("Amended.")
        self.assertIn("(amended)", self.tool("commit", "--label", label, "--amend", "-m", "Alpha: Amended"))
        self.assertEqual(self.commits(), "2")
        self.tool("unlock", label)

    def test_amend_requires_created_commit_receipt_not_matching_parent(self):
        label = self.acquire()
        self.stage_change("Raw commit.")
        self.git("commit", "-qm", "Raw commit under the acquisition")
        self.stage_change("Not ours to rewrite.")
        self.assertIn("no matching gated-commit receipt",
                      self.tool("commit", "--label", label, "--amend", expected=1))
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(),
                         "Raw commit under the acquisition")
        self.tool("commit", "--label", label, "-m", "Additive correction")
        metadata = self.root / ".git/kb-writer.lock/meta.json"
        self.assertEqual(json.loads(metadata.read_text())["commit"], self.git("rev-parse", "HEAD").stdout.strip())
        self.git("commit", "--amend", "--no-edit", "--reset-author", "-qm", "Raw replacement")
        self.stage_change("Another change.")
        self.assertIn("no matching gated-commit receipt",
                      self.tool("commit", "--label", label, "--amend", expected=1))

    def test_commit_receipt_precedes_postcheck_and_failure_is_reported(self):
        label = self.acquire()
        self.stage_change()
        helper = self.load_helper()
        observations = []
        real_check = helper.check

        def check(*args, **kwargs):
            if not kwargs.get("staged_view"):
                metadata = json.loads((self.root / ".git/kb-writer.lock/meta.json").read_text())
                observations.append(metadata["commit"])
                self.assertEqual(metadata["commit"], self.git("rev-parse", "HEAD").stdout.strip())
                return 1
            return real_check(*args, **kwargs)

        with mock.patch.object(helper, "check", side_effect=check), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(helper.commit(["--label", label, "-m", "Created before postcheck"]), 1)
        self.assertEqual(len(observations), 1)
        self.stage_change("Amended after postcheck failure.")
        self.tool("commit", "--label", label, "--amend")
        self.assertNotEqual(json.loads((self.root / ".git/kb-writer.lock/meta.json").read_text())["commit"],
                            observations[0])
        self.stage_change("Metadata failure.")
        with mock.patch.object(Path, "write_text", side_effect=OSError("receipt write fails")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.commit(["--label", label, "-m", "Receipt failure"]), 1)
        self.assertIn("PROBLEM after committing", output.getvalue())
        self.assertIn("lock remains held", output.getvalue())
        self.assertEqual(self.git("log", "-1", "--format=%s").stdout.strip(), "Receipt failure")

    def test_own_initial_commit_can_amend_without_a_parent(self):
        self.root = Path(self.temp.name) / "fresh-owned"
        self.stage_fixture()
        self.git("read-tree", "--empty")
        label = self.acquire()
        self.git("add", "--", "AGENTS.md", "MEMORY.md", "MAP.md", "CHANGELOG.md", "topics", "tools")
        self.tool("commit", "--label", label, "-m", "Initial owned commit")
        self.stage_change("Initial amended.")
        self.tool("commit", "--label", label, "--amend")
        self.assertEqual(self.commits(), "1")

    def test_malformed_lock_head_does_not_crash_or_establish_amend_ownership(self):
        label = self.acquire()
        metadata = self.root / ".git/kb-writer.lock/meta.json"
        meta = json.loads(metadata.read_text())
        for bad in (123, ["not a hash"], {"head": "not a hash"}):
            with self.subTest(head=bad):
                meta["head"] = bad
                metadata.write_text(json.dumps(meta))
                self.assertIn("HEAD ?", self.tool("check"))
                self.tool("lock", "Other", expected=1)
                self.assertIn("no matching gated-commit receipt",
                              self.tool("commit", "--label", label, "--amend", expected=1))

    def test_repository_redirects_never_lock_commit_or_unlock(self):
        label = self.acquire()
        self.stage_change()
        head = self.git("rev-parse", "HEAD").stdout
        alternate = Path(self.temp.name) / "alternate-index"
        shutil.copyfile(self.root / ".git/index", alternate)
        metadata = (self.root / ".git/kb-writer.lock/meta.json").read_bytes()
        for key, value in (("GIT_INDEX_FILE", str(alternate)), ("GIT_DIR", str(self.root / ".git")),
                           ("GIT_WORK_TREE", str(self.root)), ("GIT_COMMON_DIR", str(self.root / ".git"))):
            with self.subTest(override=key), mock.patch.dict(self.env, {key: value}):
                for args in (("lock", "Other"), ("unlock", label), ("commit", "--label", label, "-m", "Wrong index")):
                    self.assertIn("overrides are unsupported", self.tool(*args, expected=1))
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, head)
        self.assertEqual((self.root / ".git/kb-writer.lock/meta.json").read_bytes(), metadata)
        self.assertEqual(alternate.read_bytes(), (self.root / ".git/index").read_bytes())
        (self.root / ".git/index").unlink()
        self.symlink(self.root / ".git/index", alternate)
        for args in (("lock", "Other"), ("unlock", label), ("commit", "--label", label, "-m", "Linked index")):
            self.assertIn("Git index is not an ordinary file", self.tool(*args, expected=1))

    def install_collection(self, governed=True):
        source = HELPER.with_name("collection.py").read_text()
        source = re.sub(r"^GOVERNED_FIELDS = .*", "GOVERNED_FIELDS = {'priority'}" if governed else
                        "GOVERNED_FIELDS = set()", source, flags=re.M)
        self.write("tools/collection.py", source)
        self.git("add", "--", "tools/collection.py")
        self.git("commit", "-qm", "Install collection helper")

    def test_staged_extension_must_match_index_before_any_import(self):
        self.install_collection()
        path = self.root / "tools/collection.py"
        content = path.read_bytes()
        marker = self.root / "executed.txt"
        variants = ("deleted", "policy", "symlink", "unindexed")
        for variant in variants:
            with self.subTest(variant=variant):
                if variant == "deleted":
                    path.unlink()
                elif variant == "policy":
                    path.write_bytes(content + b"\nfrom pathlib import Path\nPath(__file__).parents[1].joinpath('executed.txt').touch()\n")
                elif variant == "symlink":
                    target = Path(self.temp.name) / "outside-extension.py"
                    target.write_bytes(content)
                    path.unlink()
                    self.symlink(path, target)
                else:
                    self.git("rm", "--cached", "-q", "--", "tools/collection.py")
                self.assertIn("must match the index", self.tool("check", "--staged", expected=1))
                self.assertFalse(marker.exists())
                if path.is_symlink():
                    path.unlink()
                path.write_bytes(content)
                path.chmod(0o644)
                self.git("add", "--", "tools/collection.py")

    def test_unexpected_extension_exit_fails_checks_and_commit(self):
        self.write("MEMORY.md", "# Invalid memory\n")
        self.assertIn("no exact", self.tool("check", expected=1))
        for code in (0, 7):
            with self.subTest(code=code):
                self.write("tools/collection.py", f"raise SystemExit({code})\n")
                self.assertIn("PROBLEM:", self.tool("check", expected=1))
                self.git("add", "--", "tools/collection.py")
                self.assertIn("PROBLEM:", self.tool("check", "--staged", expected=1))
                self.assertIn("REFUSED:", self.tool("commit", "-m", "Must fail", expected=1))
                self.assertEqual(self.commits(), "1")

    def test_extension_check_exit_is_also_a_problem(self):
        self.install_collection(governed=False)
        path = self.root / "tools/collection.py"
        path.write_text(path.read_text() + "\ndef check(*args):\n    raise SystemExit(0)\n")
        self.git("add", "--", "tools/collection.py")
        for args in (("check",), ("check", "--staged")):
            self.assertIn("cannot run tools/collection.py checks", self.tool(*args, expected=1))

    def test_clean_crlf_extension_executes_indexed_source(self):
        self.install_collection(governed=False)
        path = self.root / "tools/collection.py"
        indexed = path.read_bytes()
        self.git("config", "core.autocrlf", "true")
        path.unlink()
        self.git("checkout", "--", "tools/collection.py")
        self.assertIn(b"\r\n", path.read_bytes())
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        helper = self.load_helper()
        with mock.patch("builtins.compile", wraps=compile) as compiler:
            helper.extension(staged=True)
        self.assertEqual(compiler.call_args.args[0], indexed)
        self.write("work.txt", "save\n")
        self.git("add", "--", "work.txt")
        self.tool("check", "--staged")
        self.tool("commit", "-m", "Save with CRLF checkout")
        self.assertEqual(self.commits(), "3")

    def test_regular_extension_executable_bit_is_not_policy(self):
        self.install_collection(governed=False)
        self.git("update-index", "--chmod=+x", "--", "tools/collection.py")
        self.git("commit", "-qm", "Executable extension")
        self.git("config", "core.fileMode", "false")
        (self.root / "tools/collection.py").chmod(0o644)
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        self.write("work.txt", "save\n")
        self.git("add", "--", "work.txt")
        self.tool("check", "--staged")
        self.tool("commit", "-m", "Save with ignored mode difference")

    def test_lone_cr_or_substantive_extension_difference_still_refused(self):
        self.install_collection(governed=False)
        path = self.root / "tools/collection.py"
        content = path.read_bytes()
        for changed in (content.replace(b"\n", b"\r", 1), content + b"\n# Other policy\n"):
            path.write_bytes(changed)
            self.assertIn("must match the index", self.tool("check", "--staged", expected=1))

    def test_hook_tree_change_reports_created_commit_without_receipt(self):
        self.install_collection()
        record = "collection.jobs/A.md"
        self.write(record, "# A\n\n## History\n- 2026-01-01 priority: P2 — initial; authority: user\n")
        self.git("add", "--", record)
        self.git("commit", "-qm", "Record baseline")
        label = self.acquire()
        self.write("work.txt", "unrelated save\n")
        self.git("add", "--", "work.txt")
        path = self.root / record
        path.write_text(path.read_text().replace("priority: P2", "priority: P1"))
        self.write(".git/hooks/pre-commit", "#!/bin/sh\ngit add -- collection.jobs/A.md\n")
        (self.root / ".git/hooks/pre-commit").chmod(0o755)
        before = self.git("rev-parse", "HEAD").stdout.strip()
        out = self.tool("commit", "--label", label, "-m", "Hook stages other work", expected=1)
        after = self.git("rev-parse", "HEAD").stdout.strip()
        self.assertNotEqual(before, after)  # detection, not prevention
        self.assertIn("priority: P1", self.git("show", f"HEAD:{record}").stdout)
        self.assertIn("PROBLEM after committing", out)
        self.assertIn(after, out)
        self.assertIn("tree", out)
        self.assertNotIn("clean", out)
        metadata = json.loads((self.root / ".git/kb-writer.lock/meta.json").read_text())
        self.assertNotIn("commit", metadata)
        self.assertIn("no matching gated-commit receipt",
                      self.tool("commit", "--label", label, "--amend", expected=1))
        self.assertTrue((self.root / ".git/kb-writer.lock").is_dir())

    def test_lockless_hook_tree_change_is_not_clean_success(self):
        self.write("work.txt", "staged\n")
        self.git("add", "--", "work.txt")
        self.write(".git/hooks/pre-commit", "#!/bin/sh\nprintf 'from hook\\n' > hook.txt\ngit add -- hook.txt\n")
        (self.root / ".git/hooks/pre-commit").chmod(0o755)
        out = self.tool("commit", "-m", "Hook changes tree", expected=1)
        self.assertEqual(self.commits(), "2")
        self.assertIn("a commit was already created", out)
        self.assertIn(self.git("rev-parse", "HEAD").stdout.strip(), out)
        self.assertNotIn("working-tree check follows", out)
        self.assertNotIn("clean", out)

    def test_tree_inspection_failures_never_grant_a_receipt(self):
        label = self.acquire()
        self.stage_change()
        helper = self.load_helper()
        original = helper.git
        metadata = self.root / ".git/kb-writer.lock/meta.json"
        for phase in ("before", "after"):
            def fail_tree(*args, **kwargs):
                if ((phase == "before" and args == ("write-tree",)) or
                        (phase == "after" and args[0] == "rev-parse" and args[-1].endswith("^{tree}"))):
                    return subprocess.CompletedProcess(args, 1, "", "synthetic tree inspection failure")
                return original(*args, **kwargs)

            with self.subTest(phase=phase), mock.patch.object(helper, "git", side_effect=fail_tree), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(helper.commit(["--label", label, "-m", "Tree inspection failure"]), 1)
            self.assertEqual(self.commits(), "1" if phase == "before" else "2")
            self.assertNotIn("commit", json.loads(metadata.read_text()))
            self.assertIn("REFUSED: cannot snapshot" if phase == "before" else "PROBLEM after committing",
                          output.getvalue())
            self.assertNotIn("working-tree check follows", output.getvalue())

    def test_hook_changed_amend_cannot_replace_the_receipt(self):
        label = self.acquire()
        self.stage_change()
        self.tool("commit", "--label", label, "-m", "Owned baseline")
        metadata = self.root / ".git/kb-writer.lock/meta.json"
        previous = json.loads(metadata.read_text())["commit"]
        self.stage_change("Amend this.")
        self.write(".git/hooks/pre-commit", "#!/bin/sh\nprintf 'from hook\\n' > hook.txt\ngit add -- hook.txt\n")
        (self.root / ".git/hooks/pre-commit").chmod(0o755)
        out = self.tool("commit", "--label", label, "--amend", expected=1)
        self.assertIn("a commit was already created", out)
        self.assertNotEqual(self.git("rev-parse", "HEAD").stdout.strip(), previous)
        self.assertEqual(json.loads(metadata.read_text())["commit"], previous)
        self.assertIn("no matching gated-commit receipt",
                      self.tool("commit", "--label", label, "--amend", expected=1))

    def test_normal_presence_based_extension_adoption_still_works(self):
        self.write("tools/collection.py", HELPER.with_name("collection.py").read_text())
        self.write("collection.jobs/A.md", "# A\n")
        self.assertNotIn("PROBLEM", self.tool("check"))
        self.git("add", "--", "tools/collection.py", "collection.jobs/A.md")
        self.tool("check", "--staged")
        self.tool("commit", "-m", "Adopt optional extension")

    def test_working_rename_source_cannot_commit_stale_stage(self):
        self.write("plan.txt", "old plan\n")
        self.git("add", "--", "plan.txt")
        self.git("commit", "-qm", "Plan baseline")
        self.write("plan.txt", "new plan\n")
        self.git("add", "--", "plan.txt")
        (self.root / "plan.txt").rename(self.root / "final.txt")
        self.git("add", "-N", "--", "final.txt")
        self.assertIn("R100", self.git("diff", "--name-status").stdout)
        before = self.git("rev-parse", "HEAD").stdout
        self.assertIn("staged paths edited after staging", self.tool("check", "--staged", expected=1))
        self.assertIn("plan.txt", self.tool("commit", "-m", "Stale plan", expected=1))
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)

    def test_collection_root_gitlink_refused_before_commit(self):
        self.install_collection(governed=False)
        nested = self.root / "collection.jobs"
        nested.mkdir()
        for args in (("init", "-q"), ("config", "user.name", "Synthetic Test"),
                     ("config", "user.email", "test@example.invalid"),
                     ("config", "commit.gpgsign", "false")):
            self.git("-C", str(nested), *args)
        self.write("collection.jobs/A.md", "# A\n")
        self.git("-C", str(nested), "add", "--", "A.md")
        self.git("-C", str(nested), "commit", "-qm", "Nested record")
        self.git("add", "--", "collection.jobs")
        self.assertIn("160000", self.git("ls-files", "--stage", "--", "collection.jobs").stdout)
        before = self.git("rev-parse", "HEAD").stdout
        self.assertIn("gitlink collection path", self.tool("check", "--staged", expected=1))
        self.tool("commit", "-m", "Must not claim record saved", expected=1)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)

    def test_staged_file_to_directory_replacement(self):
        self.write("plan", "original\n")
        self.git("add", "--", "plan")
        self.git("commit", "-qm", "Plan baseline")
        (self.root / "plan").unlink()
        self.write("plan/nested/overview.txt", "replacement\n")
        self.git("add", "--", "plan")
        self.assertEqual(self.git("diff", "--name-only").stdout, "")
        self.tool("check", "--staged")
        self.write("plan/nested/overview.txt", "stale child\n")
        self.assertIn("plan/nested/overview.txt", self.tool("check", "--staged", expected=1))
        self.git("add", "--", "plan")
        self.tool("commit", "-m", "Replace plan with directory")
        self.assertEqual(self.git("show", "HEAD:plan/nested/overview.txt").stdout, "stale child\n")

    def test_intent_only_directory_replacement_is_not_committed(self):
        self.write("plan", "original\n")
        self.git("add", "--", "plan")
        self.git("commit", "-qm", "Plan baseline")
        self.git("rm", "--", "plan")
        self.write("plan/note", "replacement\n")
        self.git("add", "-N", "--", "plan/note")
        before = self.git("rev-parse", "HEAD").stdout
        self.assertIn("plan", self.tool("check", "--staged", expected=1))
        self.tool("commit", "-m", "Incomplete replacement", expected=1)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)
        self.assertIn("plan", self.git("ls-tree", "HEAD", "--", "plan").stdout)
        self.git("add", "--", "plan/note")
        self.tool("check", "--staged")
        self.tool("commit", "-m", "Complete replacement")
        self.assertEqual(self.git("show", "HEAD:plan/note").stdout, "replacement\n")

    def test_nested_replacement_uses_git_posix_parents(self):
        self.write("src/plan", "original\n")
        self.git("add", "--", "src/plan")
        self.git("commit", "-qm", "Nested plan baseline")
        self.git("rm", "--", "src/plan")
        child = "src/plan/nested/overview.txt"
        self.write(child, "replacement\n")
        self.git("add", "--", child)
        helper = self.load_helper()

        def native_path(value):
            # Simulate native Windows parents for the indexed Git path only.
            return PureWindowsPath(value) if value == child else Path(value)

        with mock.patch.object(helper, "Path", side_effect=native_path), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(staged_view=True), 0, output.getvalue())
        self.tool("commit", "-m", "Nested replacement")
        self.assertEqual(self.git("show", "HEAD:" + child).stdout, "replacement\n")

    def test_staged_deletion_recreated_path_controls(self):
        for kind in ("absent", "regular", "ignored", "symlink", "dangling", "directory"):
            with self.subTest(kind=kind):
                name = "deleted-" + kind
                self.write(name, "original\n")
                self.git("add", "--", name)
                self.git("commit", "-qm", "Deletion baseline")
                self.git("rm", "--", name)
                if kind in ("regular", "ignored"):
                    self.write(name, "recreated\n")
                elif kind in ("symlink", "dangling"):
                    self.symlink(self.root / name, self.root / ("CHANGELOG.md" if kind == "symlink" else "missing"))
                elif kind == "directory":
                    self.write(name + "/unindexed.txt", "not staged\n")
                if kind == "ignored":
                    self.write(".git/info/exclude", name + "\n")
                before = self.git("rev-parse", "HEAD").stdout
                expected = 0 if kind == "absent" else 1
                out = self.tool("check", "--staged", expected=expected)
                if expected:
                    self.assertIn("staged paths edited after staging", out)
                self.tool("commit", "-m", "Delete path", expected=expected)
                if expected:
                    self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)
                    path = self.root / name
                    if path.is_dir() and not path.is_symlink():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    self.tool("commit", "-m", "Delete path after manual cleanup")

    def test_staged_collection_root_symlink_refused_before_commit(self):
        self.install_collection(governed=False)
        target = Path(self.temp.name) / "outside"
        target.mkdir()
        self.symlink(self.root / "collection.jobs", target, is_directory=True)
        self.git("add", "--", "collection.jobs")
        before = self.git("rev-parse", "HEAD").stdout
        self.assertIn("collection", self.tool("check", "--staged", expected=1))
        self.tool("commit", "-m", "Must not commit symlink", expected=1)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)

    def test_outgoing_record_links_checked_without_registration_or_changelog(self):
        self.install_collection(governed=False)
        self.write("collection.jobs/A.md", "# A\nSee [[collection.jobs/B]] and [[spaces/Missing]].\n")
        self.write("collection.jobs/B.md", "# B\nSee [[Project]].\n")
        self.git("add", "--", "collection.jobs/A.md", "collection.jobs/B.md")
        for args in (("check",), ("check", "--staged")):
            out = self.tool(*args, expected=1)
            self.assertIn("broken wikilink in collection.jobs/A.md: [[spaces/Missing]]", out)
            self.assertNotIn("not registered", out)
            self.assertNotIn("requires staged CHANGELOG", out)
        self.write("collection.jobs/A.md", "# A\nSee [[collection.jobs/typo]].\n")
        self.git("add", "--", "collection.jobs/A.md")
        before = self.git("rev-parse", "HEAD").stdout
        self.assertIn("broken wikilink", self.tool("commit", "-m", "Bad successor", expected=1))
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)
        self.write("collection.jobs/A.md", "# A\nSee [[collection.jobs/B]].\n")
        self.git("add", "--", "collection.jobs/A.md")
        self.tool("commit", "-m", "Valid links, no Map or changelog")

    def test_ignored_recreated_deletion_is_checked_without_ignored_tree_walk(self):
        self.write("work.txt", "baseline\n")
        self.git("add", "--", "work.txt")
        self.git("commit", "-qm", "Work baseline")
        self.git("rm", "-q", "--", "work.txt")
        self.write("work.txt", "recreated\n")
        self.write(".git/info/exclude", "work.txt\ncache/\n")
        self.write("cache/irrelevant.txt", "ignored\n")
        helper = self.load_helper()
        original = helper.git

        def no_ignored_walk(*args, **kwargs):
            self.assertFalse(args[0] == "ls-files" and "--others" in args)
            return original(*args, **kwargs)

        with mock.patch.object(helper, "git", side_effect=no_ignored_walk), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(staged_view=True), 1)
        self.assertIn("staged paths edited after staging", output.getvalue())
        self.assertIn("work.txt", output.getvalue())

    def test_stale_inspection_failure_reports_the_failing_command(self):
        self.stage_change()
        helper = self.load_helper()
        original = helper.git

        def failed_diff(*args, **kwargs):
            if args[:2] == ("diff", "--name-only"):
                return subprocess.CompletedProcess(args, 1, "", "synthetic stale diff failure")
            return original(*args, **kwargs)

        with mock.patch.object(helper, "git", side_effect=failed_diff), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(staged_view=True), 1)
        self.assertIn("cannot compare staged paths with the working tree: synthetic stale diff failure",
                      output.getvalue())
        def failed_inventory(*args, **kwargs):
            if args[:2] == ("ls-files", "--cached"):
                return subprocess.CompletedProcess(args, 1, "", "synthetic tracked inventory failure")
            return original(*args, **kwargs)

        with mock.patch.object(helper, "git", side_effect=failed_inventory), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(staged_view=True), 1)
        self.assertIn("cannot compare staged paths with the working tree: synthetic tracked inventory failure",
                      output.getvalue())
        with mock.patch.object(helper, "staged_paths", wraps=helper.staged_paths) as inspect, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(helper.check(staged_view=True), 0)
        self.assertEqual(inspect.call_count, 1)  # reuse the non-amend staged inspection
        # An aggregate amend baseline needs a separate current-HEAD inspection.
        with mock.patch.object(helper, "staged_paths", side_effect=[({"work.txt"}, None), (set(), "current staging failed")]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(helper.check(staged_view=True, base="HEAD^"), 1)
        self.assertIn("cannot compare staged paths with the working tree: current staging failed", output.getvalue())

    def test_collection_durability_and_ignore_ancestors_without_map_or_changelog(self):
        self.install_collection()
        self.write("collection.jobs/A.md", "# A\n")
        self.git("add", "--", "collection.jobs/A.md")
        self.assertNotIn("PROBLEM", self.tool("check", "--staged"))  # no Map/changelog obligations
        self.git("commit", "-qm", "Add record")
        self.write("collection.jobs/.gitignore", "*.md\n")
        self.assertIn("ignored and may disappear", self.tool("check", expected=1))
        self.assertIn("cannot validate staged ignore rules: collection.jobs/.gitignore",
                      self.tool("check", "--staged", expected=1))
        self.git("add", "--", "collection.jobs/.gitignore")
        self.assertIn("ignored and may disappear", self.tool("check", "--staged", expected=1))
        self.write("collection.jobs/ignored.md", "# Ignored record\n")
        self.assertIn("collection.jobs/ignored.md", self.tool("check", expected=1))

    def test_collection_control_names_checked_before_extension_filtering(self):
        self.install_collection()
        for name in ("AGENTS.md", "CLAUDE.MD", "nested/MEMORY.MD", "nested/map.md"):
            with self.subTest(name=name):
                rel = "collection.jobs/" + name
                self.write(rel, "# Control\n")
                self.assertIn("root-only control file inside a collection", self.tool("check", expected=1))
                self.git("add", "--", rel)
                self.assertIn("root-only control file inside a collection", self.tool("check", "--staged", expected=1))
                self.git("rm", "--cached", "-q", "--", rel)
                (self.root / rel).unlink()

    def test_amend_uses_current_history_not_the_acquisition_parent(self):
        self.install_collection()
        record = "collection.jobs/A.md"
        self.write(record, "# A\n")
        self.git("add", "--", record)
        self.git("commit", "-qm", "Record baseline")
        label = self.acquire()
        event = "- 2026-01-01 priority: P2 — chosen; authority: user\n"
        self.write(record, "# A\n\n## History\n" + event)
        self.git("add", "--", record)
        self.tool("commit", "--label", label, "-m", "Record governed choice")
        self.write(record, "# A\n\n## History\n" + event.replace("P2", "P3"))
        self.git("add", "--", record)
        self.assertIn("earlier governed entry altered", self.tool("commit", "--label", label, "--amend", expected=1))
        self.git("rm", "-fq", "--", record)
        self.assertIn("committed record deleted", self.tool("commit", "--label", label, "--amend", expected=1))

    def test_stale_staging_catches_recreated_deletion_and_revert_to_parent(self):
        self.write("work.txt", "base\n")
        self.git("add", "--", "work.txt")
        self.git("commit", "-qm", "Work baseline")
        label = self.acquire()
        self.write("work.txt", "own commit\n")
        self.git("add", "--", "work.txt")
        self.tool("commit", "--label", label, "-m", "Own work")
        self.write("work.txt", "base\n")
        self.git("add", "--", "work.txt")
        self.write("work.txt", "edited after reverting to parent\n")
        self.assertIn("staged paths edited after staging", self.tool("commit", "--label", label, "--amend", expected=1))
        self.git("rm", "-fq", "--", "work.txt")
        self.write("work.txt", "recreated but untracked\n")
        self.assertIn("staged paths edited after staging", self.tool("check", "--staged", expected=1))

    def test_commit_makes_the_first_commit_on_an_unborn_branch(self):
        self.root = Path(self.temp.name) / "fresh"
        self.stage_fixture()
        self.assertIn("no commits yet", self.tool("check", "--staged", expected=1))
        self.assertIn("committed", self.tool("commit", "-m", "Install the brain"))  # no lock, no label
        self.assertEqual(self.commits(), "1")
        self.assertNotIn("PROBLEM", self.tool("check"))
        label = self.acquire()
        self.stage_change("Second.")
        out = self.tool("commit", "--label", label, "--amend", "-m", "x", expected=1)
        self.assertIn("no matching gated-commit receipt", out)  # the acquisition's commit does not exist yet
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
