"""Collection integrity regressions in disposable installed brains."""
import re
import shlex
import shutil
import sys
import unittest

import test_collection as fixtures


@unittest.skipUnless(shutil.which("git"), "Git required")
class CollectionRepairs(unittest.TestCase):
    setUp = fixtures.Collections.setUp
    call = fixtures.Collections.call
    git = fixtures.Collections.git
    cli = fixtures.Collections.cli
    core = fixtures.Collections.core
    put = fixtures.Collections.put
    rows = fixtures.Collections.rows

    def test_section_edits_refuse_existing_unclosed_fence_or_comment(self):
        for opener in ("```", "<!--"):
            for heading in ("Reviewer A", "Earlier", "New review"):
                with self.subTest(opener=opener, heading=heading):
                    original = ("# A\n- cost: 1\n\n## Earlier\nsafe\n\n"
                                "## Reviewer A\nold\n" + opener +
                                "\n## Reviewer B\nKeep exact.  \r\n")
                    record = self.put("jobs/A", original)
                    _, err = self.cli("edit", "jobs/A", "--section", heading,
                                      data="replacement\n", ok=False)
                    self.assertIn("close it or edit manually", err)
                    self.assertEqual(record.read_bytes(), original.encode())
                    self.cli("edit", "jobs/A", "--set", "cost", "2")
                    self.assertEqual(record.read_bytes(), original.replace("cost: 1", "cost: 2").encode())

    def test_section_edits_allow_existing_closed_fence_or_comment(self):
        for opener, closer in (("```", "```"), ("<!--", "-->")):
            with self.subTest(opener=opener):
                peer = "## Reviewer B\nKeep exact.  \r\n"
                record = self.put("jobs/A", "# A\n\n## Reviewer A\nold\n" +
                                  opener + "\nliteral\n" + closer + "\n" + peer)
                self.cli("edit", "jobs/A", "--section", "Reviewer A", data="replacement\n")
                self.assertEqual(record.read_bytes(), ("# A\n\n## Reviewer A\nreplacement\n" + peer).encode())

    def test_section_edit_preserves_indented_setext_peer(self):
        for continuation in ("    from Sam", "\tfrom Sam"):
            with self.subTest(continuation=continuation):
                peer = "Peer review\n" + continuation + "\n-----------\nPeer assessment, keep exact.  \r\n"
                record = self.put("jobs/A", "# A\n\n## Mine\nold\n\n" + peer)
                self.cli("edit", "jobs/A", "--section", "Mine", data="replacement\n\n")
                self.assertEqual(record.read_bytes(), ("# A\n\n## Mine\nreplacement\n\n" + peer).encode())

    def test_section_edit_ignores_fence_inside_html_comment(self):
        for comment in ("<!--\n```\n-->\n", "  <!-- comment\n~~~\n-->\n"):
            with self.subTest(comment=comment):
                peer = "## Peer\nPeer assessment, keep exact.  \r\n"
                record = self.put("jobs/A", "# A\n\n## Mine\nold\n" + comment + "\n" + peer)
                self.cli("edit", "jobs/A", "--section", "Mine", data="replacement\n")
                self.assertEqual(record.read_bytes(), ("# A\n\n## Mine\nreplacement\n" + peer).encode())

    def test_section_payload_cannot_open_comment_over_peer(self):
        original = "# A\n\n## Mine\nold\n## Peer\nkeep\n"
        record = self.put("jobs/A", original)
        self.cli("edit", "jobs/A", "--section", "Mine", data="<!--\n```\n", ok=False)
        self.assertEqual(record.read_bytes(), original.encode())
        self.cli("edit", "jobs/A", "--section", "Mine", data="<!--\n```\n-->\n")
        self.assertTrue(record.read_bytes().endswith(b"## Peer\nkeep\n"))

    def test_indented_code_is_not_a_setext_heading(self):
        original = "# A\n\n## Mine\nold\n\n    code\n    continuation\n----\n"
        record = self.put("jobs/A", original)
        self.cli("edit", "jobs/A", "--section", "Mine", data="replacement\n")
        self.assertEqual(record.read_bytes(), b"# A\n\n## Mine\nreplacement\n")

    def test_retired_governance_preserves_canonical_history_not_prose(self):
        second = fixtures.EVENT.replace("P2", "P3")
        old = fixtures.EVENT + "\n" + second + "\n" + second + "\n"
        original = "# A\n- cost: 1\n\n## History\nReview notes.\n\n" + old
        record = self.put("jobs/A", original)
        self.git("add", "--", "collection.jobs/A.md")
        self.git("commit", "-qm", "record")
        helper = self.root / "tools/collection.py"
        helper.write_text(re.sub(r"^GOVERNED_FIELDS = .*$", "GOVERNED_FIELDS = set()",
                                 helper.read_text(), flags=re.M))
        (self.root / "CHANGELOG.md").write_text("2026-11-08 - Retire governance in fixture.\n")
        self.git("add", "--", "tools/collection.py", "CHANGELOG.md")
        self.core("check", "--staged")
        self.git("commit", "-qm", "retire governance")
        for revised in (old.replace("P2", "P1", 1), second + "\n" + fixtures.EVENT + "\n" + second + "\n",
                        fixtures.EVENT + "\n", ""):
            with self.subTest(revised=revised):
                self.put("jobs/A", original.replace(old, revised))
                self.git("add", "--", "collection.jobs/A.md")
                self.assertIn("earlier governed entry", self.core("check", "--staged", ok=False))
        record.write_text(original.replace("Review notes.", "Revised free prose."))
        self.git("add", "--", "collection.jobs/A.md")
        self.core("check", "--staged")
        record.write_text(record.read_text().replace("## History\n", "## History\n" + second + "\n"))
        self.git("add", "--", "collection.jobs/A.md")
        self.core("check", "--staged")
        self.cli("edit", "jobs/A", "--set", "cost", "2")
        self.assertTrue(record.read_bytes().endswith(old.encode()))
        self.cli("edit", "jobs/A", "--section", "Review", data="free assessment\n")
        self.assertIn(old.encode(), record.read_bytes())

    def test_emphasized_decision_fields_fail_without_freezing_history_prose(self):
        for field in ("**priority**:", "**priority:**", "*priority*:", "`priority`:",
                      "__priority__:", "_priority_:"):
            with self.subTest(field=field):
                self.put("jobs/A", "# A\n\n## History\n- 2026-11-07 " + field +
                         " P1 — changed; authority: D8\n" + fixtures.EVENT + "\n")
                self.assertIn("malformed governed entry", self.core("check", ok=False))
                self.git("add", "--", "collection.jobs/A.md")
                self.assertIn("malformed governed entry", self.core("check", "--staged", ok=False))
                if fixtures.sqlite3:
                    self.assertIn("malformed governed entry", self.cli(
                        "query", "jobs", "SELECT priority FROM jobs", ok=False)[1])
        self.put("jobs/A", "# A\n\n## History\nFree **priority** prose.\n"
                 "- note: keep editable\n\n```md\n- 2026-11-07 **priority**: example\n```\n")
        self.core("check")

    def test_added_cycle_cannot_hide_behind_existing_cycle(self):
        self.put("jobs/A", "# A\n- needs: B C\n")
        self.put("jobs/B", "# B\n- needs: A\n")
        record = self.put("jobs/C", "# C\n")
        self.assertIn("cycle", self.cli("edit", "jobs/C", "--set", "needs", "B", ok=False)[1])
        self.assertEqual(record.read_bytes(), b"# C\n")
        self.cli("edit", "jobs/C", "--set", "cost", "2")
        self.cli("edit", "jobs/A", "--set", "needs", "C")
        self.core("check")
        self.cli("edit", "jobs/C", "--set", "needs", "B", ok=False)
        self.cli("edit", "jobs/C", "--set", "needs", "C", ok=False)
        self.cli("edit", "jobs/C", "--set", "needs", "missing", ok=False)

    def test_unrelated_edit_does_not_scan_network(self):
        self.put("jobs/A", "# A\n- cost: 1\n")
        code = """import argparse
import sys
sys.path.insert(0, 'tools')
import collection as c
before, records = c.snapshot()
def forbidden(*args):
    raise AssertionError('unrelated edit scanned graph')
c.Network = c.walk = forbidden
args = argparse.Namespace(ref='jobs/A', expect=None, section=None, set=['cost', '2'],
                          unset=None, reason=None, authority=None, assent=None, label=None)
c.edit(before, records, args)
"""
        self.call(sys.executable, "-B", "-c", code)

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_private_index_names_do_not_restrict_collection_names(self):
        for name in ("reach_need", "reach_need_", "REACH_NEED__", "needs_item", "tags_item", "sections_item"):
            self.put(name + "/X", "# X\n- state: done\n")
        self.put("jobs/A", "# A\n- needs: reach_need/X\n")
        rows, _ = self.rows("query", "jobs", "SELECT 1")
        self.assertEqual(rows[1:], [["1"]])
        rows, _ = self.rows("query", "jobs", "SELECT need,depth FROM reach WHERE item='jobs/A'")
        self.assertEqual(rows[1:], [["reach_need/X", "1"]])

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_documented_ranking_excludes_non_candidates_and_unusable_scores(self):
        helper = self.root / "tools/collection.py"
        helper.write_text(re.sub(r"^NUMERIC_FIELDS = .*$", "NUMERIC_FIELDS = {'tasks': {'benefit', 'cost'}}",
                                 helper.read_text(), flags=re.M))
        for ident, state, benefit, cost in (("Done", "done", "100", "1"),
                                            ("Waiting", "waiting", "50", "1"),
                                            ("Ready", "open", "6", "2"),
                                            ("Unestimated", "open", "", ""),
                                            ("NoBenefit", "open", "", "1"),
                                            ("ZeroCost", "open", "8", "0")):
            self.put("tasks/" + ident, f"# Item\n- state: {state}\n- benefit: {benefit}\n- cost: {cost}\n")
        help_text, _ = self.cli("--help")
        example = next(line.strip() for line in help_text.splitlines() if line.strip().startswith("query tasks "))
        rows, _ = self.rows(*shlex.split(example))
        self.assertEqual(rows[1:], [["Ready", "6", "2", "3"]])
        edit_help, _ = self.cli("edit", "--help")
        self.assertIn("--set KEY VALUE", edit_help)

    def test_approved_manual_governance_conversion_preserves_body_and_history(self):
        record = self.put("jobs/A", "# A\n- decision: accepted\n\n## Review\nKeep this prose.\n"
                          "\n## History\n" + fixtures.EVENT + "\n")
        self.git("add", "--", "collection.jobs/A.md")
        self.git("commit", "-qm", "record")
        helper = self.root / "tools/collection.py"
        helper.write_text(re.sub(r"^GOVERNED_FIELDS = .*$", "GOVERNED_FIELDS = {'priority', 'decision'}",
                                 helper.read_text(), flags=re.M))
        before = record.read_bytes()
        self.assertIn("is governed", self.cli("edit", "jobs/A", "--set", "decision", "accepted",
                      "--reason", "adopt", "--authority", "D8", ok=False)[1])
        self.assertEqual(record.read_bytes(), before)
        event = "- 2026-11-08 decision: accepted — approved conversion; authority: D8\n"
        record.write_bytes(before.replace(b"- decision: accepted\n", b"")
                           .replace(b"## History\n", b"## History\n" + event.encode()))
        (self.root / "CHANGELOG.md").write_text("2026-11-08 - Govern decisions in fixture.\n")
        self.git("add", "--", "tools/collection.py", "collection.jobs/A.md", "CHANGELOG.md")
        self.core("check", "--staged")
        self.assertIn(b"## Review\nKeep this prose.\n", record.read_bytes())
        self.assertTrue(record.read_bytes().endswith((fixtures.EVENT + "\n").encode()))

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_state_values_match_exactly_and_promotion_retains_source(self):
        self.put("jobs/A", "# A\n- needs: B\n")
        self.put("jobs/B", "# B\n- state: Done\n")
        self.assertEqual(self.rows("query", "jobs", "SELECT _unmet FROM jobs WHERE _id='A'")[0][1:], [["1"]])
        self.cli("edit", "jobs/B", "--set", "state", "done")
        self.assertEqual(self.rows("query", "jobs", "SELECT _unmet FROM jobs WHERE _id='A'")[0][1:], [["0"]])
        source = self.put("jobs/Inbox", "# Inbox\n- state: inbox\n")
        self.cli("edit", "jobs/Inbox", "--set", "state", "roadmap")
        self.put("roadmap/Promoted", "# Promoted\n- state: planned\n")
        self.cli("edit", "jobs/Inbox", "--set", "state", "archived")
        self.cli("edit", "jobs/Inbox", "--section", "Successor", data="See [[collection.roadmap/Promoted]].\n")
        self.git("add", "--", "collection.jobs", "collection.roadmap")
        self.core("check", "--staged")
        self.assertIn(b"[[collection.roadmap/Promoted]]", source.read_bytes())

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_documented_section_stdin_and_assessment_date(self):
        peer = "## Peer\nPreserve this.  \r\n"
        record = self.put("tasks/T-1", "# Task\n- assessed-on: 2026-11-08\n\n" + peer)
        help_text, _ = self.cli("--help")
        command, body = help_text.split("  edit tasks/T-1 --section ", 1)[1].split(" <<'EOF'\n", 1)
        body = body.split("\nEOF", 1)[0] + "\n"
        self.cli("edit", "tasks/T-1", "--section", shlex.split(command)[0], data=body)
        self.assertIn(peer.encode(), record.read_bytes())
        self.assertIn(body.encode(), record.read_bytes())
        self.assertEqual(self.rows("query", "tasks", "SELECT day([assessed-on]) FROM tasks")[0][1:],
                         [["2026-11-08"]])

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_leading_numeric_scores_ignore_all_trailing_commentary(self):
        for ident, value in (("A", "1 (1 day)"), ("B", "2 (1 week)"), ("C", "3 (1 month)"),
                             ("D", "2 to 4 days"), ("E", "2 days")):
            self.put("jobs/" + ident, "# Item\n- cost: " + value + "\n")
        rows, err = self.rows("query", "jobs", "SELECT _id,cost FROM jobs ORDER BY _id")
        self.assertEqual(rows[1:], [["A", "1"], ["B", "2"], ["C", "3"], ["D", "2"], ["E", "2"]])
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
