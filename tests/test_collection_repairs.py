"""Collection integrity regressions in disposable installed brains."""
import re
import shlex
import shutil
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

    def test_approved_manual_governance_conversion_preserves_body_and_history(self):
        record = self.put("jobs/A", "# A\n- decision: accepted\n\n## Review\nKeep this prose.\n"
                          "\n## History\n" + fixtures.EVENT + "\n")
        self.git("add", "--", "collection.jobs/A.md")
        self.git("commit", "-qm", "record")
        helper = self.root / "tools/collection.py"
        helper.write_text(re.sub(r"^GOVERNED_FIELDS = .*$", "GOVERNED_FIELDS = {'priority', 'decision'}",
                                 helper.read_text(), flags=re.M))
        before = record.read_bytes()
        self.assertIn("is governed", self.core("check", ok=False))
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
        self.put("jobs/B", "# B\n- state: done\n")
        self.assertEqual(self.rows("query", "jobs", "SELECT _unmet FROM jobs WHERE _id='A'")[0][1:], [["0"]])
        source = self.put("jobs/Inbox", "# Inbox\n- state: inbox\n")
        source.write_text(source.read_text().replace("state: inbox", "state: roadmap"))
        self.put("roadmap/Promoted", "# Promoted\n- state: planned\n")
        source.write_text(source.read_text().replace("state: roadmap", "state: archived"))
        source.write_text(source.read_text() + "\n## Successor\nSee [[collection.roadmap/Promoted]].\n")
        self.git("add", "--", "collection.jobs", "collection.roadmap")
        self.core("check", "--staged")
        self.assertIn(b"[[collection.roadmap/Promoted]]", source.read_bytes())


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
