"""The Watch index and the attention block: helper behaviour and contract/helper agreement."""
import datetime
import importlib.util
from pathlib import Path
import re
import shutil
import unittest

import test_git_reference as fixtures

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("brain_helper", fixtures.HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

TODAY = "2026-11-10"  # a Tuesday


def day(text):
    return datetime.date.fromisoformat(text)


class WorkingDays(unittest.TestCase):
    def test_weekends_do_not_count(self):
        friday, saturday, monday, wednesday = day("2026-11-13"), day("2026-11-14"), day("2026-11-16"), day("2026-11-18")
        self.assertEqual(friday.weekday(), 4)
        self.assertEqual(helper.working_days_until(friday, friday), 0)
        self.assertEqual(helper.working_days_until(friday, saturday), 0)
        self.assertEqual(helper.working_days_until(friday, monday), 1)
        self.assertEqual(helper.working_days_until(friday, wednesday), 3)


@unittest.skipUnless(shutil.which("git"), "Git required")
class WatchCheck(unittest.TestCase):
    setUp = fixtures.GitReferenceTests.setUp
    stage_fixture = fixtures.GitReferenceTests.stage_fixture
    tearDown = fixtures.GitReferenceTests.tearDown
    write = fixtures.GitReferenceTests.write
    git = fixtures.GitReferenceTests.git
    tool = fixtures.GitReferenceTests.tool

    def watch(self, *lines, threads="", extra=""):
        self.write("MEMORY.md", "# Memory\n\n## Focus\n\nSynthetic fixture.\n\n## Open threads\n\n" + threads
                   + "\n## Watch\n\n" + "".join(f"- {line}\n" for line in lines) + extra)
        self.git("add", "--", "MEMORY.md")
        self.git("commit", "-qm", "Watch fixture")

    def test_overdue_and_near_lines_are_shown_and_the_rest_counted(self):
        self.watch("due 2026-11-07: file the clinic notice. Look: outbox.",
                   "due 2026-11-10: send the quote. Look: tracker.",
                   "due 2026-11-12: chase the reply. Look: inbox.",
                   "due 2026-11-13: not yet. Look: inbox.",
                   "when the PR merges: send the release note. Look: tracker.",
                   "when the client signs: start the pilot. Look: inbox.")
        out = self.tool("check", "--today", TODAY)
        self.assertIn(f"== attention == (today {TODAY}, from --today)", out)
        self.assertIn("OVERDUE 3 days: due 2026-11-07: file the clinic notice.", out)
        self.assertIn("DUE TODAY: due 2026-11-10: send the quote.", out)
        self.assertIn("DUE in 2 working days: due 2026-11-12: chase the reply.", out)
        self.assertNotIn("not yet", out)
        self.assertIn("1 dated line further out", out)
        self.assertIn("2 condition lines", out)
        self.assertNotIn("send the release note", out)  # conditions are counted, not reprinted
        self.assertLess(out.index("OVERDUE"), out.index("DUE TODAY"))

    def test_nothing_due_is_said_plainly(self):
        self.watch("due 2026-12-24: far away. Look: inbox.")
        out = self.tool("check", "--today", TODAY)
        self.assertIn("No dated Watch line is overdue or due within 2 working days.", out)
        self.assertNotIn("far away", out)

    def test_overflow_is_visible(self):
        self.watch(*[f"due 2026-11-0{n}: item {n}. Look: inbox." for n in range(1, 10)])
        out = self.tool("check", "--today", TODAY)
        self.assertEqual(out.count("OVERDUE"), helper.WATCH_SHOWN_MAX)
        self.assertIn(f"{9 - helper.WATCH_SHOWN_MAX} more overdue or due lines", out)
        self.assertLess(out.index("item 1."), out.index("item 8."))  # oldest first

    def test_attention_never_changes_the_exit_status_and_is_read_only(self):
        self.watch("due 2026-01-01: long overdue. Look: inbox.")
        before = (self.git("status", "--porcelain").stdout, self.git("rev-parse", "HEAD").stdout)
        out = self.tool("check", "--today", TODAY)
        self.assertIn("OVERDUE", out)
        self.assertEqual(before, (self.git("status", "--porcelain").stdout, self.git("rev-parse", "HEAD").stdout))
        self.write("MAP.md", "")  # a PROBLEM still fails the check, and attention still shows
        out = self.tool("check", "--today", TODAY, expected=1)
        self.assertIn("PROBLEM", out)
        self.assertIn("OVERDUE", out)

    def test_staged_checks_and_commit_stay_quiet(self):
        self.watch("due 2026-01-01: long overdue. Look: inbox.")
        self.write("topics/Project.md", "# Project\n\n## Current status\n\nChanged.\n\n## History\n")
        self.write("CHANGELOG.md", "# Changelog\n\n2026-01-02 - Changed.\n2026-01-01 - Created synthetic fixture.\n")
        self.git("add", "--", "topics/Project.md", "CHANGELOG.md")
        self.assertNotIn("attention", self.tool("check", "--staged"))
        out = self.tool("commit", "-m", "Change")
        self.assertIn("committed", out)
        self.assertNotIn("attention", out)

    def test_without_a_watch_section_nothing_is_printed(self):
        self.assertNotIn("attention", self.tool("check"))

    def test_machine_clock_is_named_when_today_is_not_given(self):
        self.watch("due 2000-01-01: long overdue. Look: inbox.")
        out = self.tool("check")
        self.assertIn("machine clock", out)
        self.assertIn("OVERDUE", out)

    def test_bad_arguments_print_usage(self):
        for args in (("--today",), ("--today", "10-11-2026"), ("--today", "2026-13-40"),
                     ("--staged", "--today", TODAY), ("--today", TODAY, "--staged")):
            with self.subTest(args=args):
                self.assertIn("usage: python3 tools/minibrain.py check", self.tool("check", *args, expected=2))

    def test_unreadable_date_warns_and_counts_as_a_condition(self):
        self.watch("due 2026-02-30: impossible date. Look: inbox.",
                   "due 2026-11-1: short spelling. Look: inbox.",
                   "due diligence on the vendor: not a date, and not a warning. Look: inbox.")
        out = self.tool("check", "--today", TODAY)
        self.assertEqual(out.count("unreadable date"), 2)
        self.assertIn("3 condition lines", out)

    def test_only_the_template_placeholder_is_skipped(self):
        self.watch("[due YYYY-MM-DD, or when <condition>]: [next action]. Look: [where]. Rule: [[Project]].")
        out = self.tool("check", "--today", TODAY)
        self.assertIn("No dated Watch line is overdue", out)
        self.assertNotIn("condition line", out)
        self.watch("[ ] due 2026-11-01: a real line written as a task. Look: inbox.")
        self.assertIn("1 condition line", self.tool("check", "--today", TODAY))

    def test_watch_lines_do_not_count_as_open_threads(self):
        threads = "".join(f"- **Thread {n}** — open.\n" for n in range(helper.THREADS_MAX))
        self.watch(*[f"when thing {n}: act. Look: inbox." for n in range(5)], threads=threads)
        self.assertNotIn("PROBLEM", self.tool("check"))

    def test_long_lists_and_long_lines_warn_without_hiding_work(self):
        self.watch(*[f"when thing {n}: act. Look: inbox." for n in range(helper.WATCH_SOFT_MAX + 1)],
                   "when " + "x" * helper.WATCH_LINE_SOFT_CHARS + ": act.")
        out = self.tool("check")
        self.assertIn("Watch lines (soft limit", out)
        self.assertIn("Watch line over", out)
        self.assertIn(f"{helper.WATCH_SOFT_MAX + 2} condition lines", out)

    def test_a_second_watch_heading_is_a_problem(self):
        self.watch("when x: act.", extra="\n## Watch\n\n- when y: act.\n")
        self.assertIn("more than one `## Watch` heading", self.tool("check", expected=1))


class ContractAgreement(unittest.TestCase):
    """The contract, the starter index and the helper must describe the same line format."""

    def test_starter_index_and_contract_use_the_format_the_helper_parses(self):
        memory = (ROOT / "starter/MEMORY.md").read_text()
        self.assertEqual(len(re.findall(r"(?m)^## Watch$", memory)), 1)
        core = (ROOT / "starter/AGENTS.md").read_text()
        self.assertIn("`due YYYY-MM-DD`", core)
        self.assertTrue(helper.WATCH_DUE.match("due 2026-11-12: act"))
        self.assertIn("Watch", core.split("## Resume")[1].split("## Checkpoint")[0])
        self.assertIn("recorded delegation", core)

    def test_starter_template_line_is_skipped_by_the_helper(self):
        memory = (ROOT / "starter/MEMORY.md").read_text()
        headings = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^## (.+?)\s*$", memory, re.MULTILINE)]
        bullets = helper.section_bullets(memory, headings, "Watch")
        self.assertEqual(len(bullets), 1)
        self.assertEqual(helper.watch_items(bullets, []), [])


if __name__ == "__main__":
    unittest.main()
