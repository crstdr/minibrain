"""Focused regressions from the final collections review."""
import shutil
import sys
import unittest

import test_collection as fixtures


@unittest.skipUnless(shutil.which("git"), "Git required")
class CollectionFollowup(unittest.TestCase):
    setUp = fixtures.Collections.setUp
    call = fixtures.Collections.call
    git = fixtures.Collections.git
    cli = fixtures.Collections.cli
    core = fixtures.Collections.core
    put = fixtures.Collections.put
    rows = fixtures.Collections.rows

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_reach_case_and_main_qualification_do_not_change_results(self):
        self.put("jobs/A", "# A\n- needs: B\n")
        self.put("jobs/B", "# B\n- state: done\n")
        for relation in ("reach", "REACH", "ReAcH", "main.reach", "main.REACH", "MAIN.reach", "MAIN.REACH"):
            for expression in ("count(*)", "count(depth)", "EXISTS(SELECT 1 FROM " + relation + ")"):
                with self.subTest(relation=relation, expression=expression):
                    sql = ("SELECT " + expression if expression.startswith("EXISTS") else
                           "SELECT " + expression + " FROM " + relation)
                    self.assertEqual(self.rows("query", "jobs", sql)[0][1:], [["1"]])
        for relation in ("JOBS", "MAIN.JOBS"):
            self.assertEqual(self.rows("query", "jobs", "SELECT count(*) FROM " + relation)[0][1:], [["2"]])
        self.assertEqual(self.rows("query", "jobs", "WITH REACH AS (SELECT 1) SELECT count(*) FROM REACH")[0][1:], [["1"]])

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_sqlite_name_folding_is_ascii_only_and_private_schema_stays_denied(self):
        self.put("jobs/A", "# A\n")
        # Use an in-memory schema: macOS can normalize these directory names.
        self.call(sys.executable, "-B", "-c", """import sqlite3, sys
sys.path.insert(0, 'tools')
import collection as c
tables = c.schema({'K', 'K'}, {})
db = sqlite3.connect(':memory:')
c.fill(db, tables, {})
c.restrict(db, sqlite3, tables)
for name in tables:
    assert db.execute('SELECT count(*) FROM ' + c.quote(c.mapped_name(name))).fetchone() == (0,)
""")
        for relation in ("sqlite_master", "SQLITE_MASTER", "sqlite_schema", "SQLITE_SCHEMA",
                         "main.sqlite_schema", "MAIN.SQLITE_SCHEMA"):
            for expression in ("count(*)", "name"):
                with self.subTest(relation=relation, expression=expression):
                    self.cli("query", "jobs", "SELECT " + expression + " FROM " + relation, ok=False)
        self.cli("query", "jobs", "WITH c AS (SELECT name FROM MAIN.SQLITE_SCHEMA) SELECT count(*) FROM c", ok=False)




    def test_malformed_history_candidates_fail_instead_of_returning_stale_values(self):
        for candidate in ("- 2026-11-08: priority:", "- 2026-11-08 — priority:",
                          "- 2026-11-08 - priority:", "1. 2026-11-08 priority:"):
            for old in ("", fixtures.EVENT + "\n"):
                with self.subTest(candidate=candidate, old=old):
                    self.put("jobs/A", "# A\n\n## History\n" + candidate + " P1 — reviewed; authority: D8\n" + old)
                    self.assertIn("malformed governed entry", self.core("check", ok=False))
                    self.git("add", "--", "collection.jobs/A.md")
                    self.assertIn("malformed governed entry", self.core("check", "--staged", ok=False))
                    if fixtures.sqlite3:
                        self.assertIn("malformed governed entry", self.cli("query", "jobs", "SELECT priority FROM jobs", ok=False)[1])
        self.put("jobs/A", "# A\n\n## History\n- 2026-11-08 priority: P1 — reviewed; authority: D8\n" +
                 fixtures.EVENT + "\n\nFree **priority** prose.\n- note: keep editable\n"
                 "1. Review priority before deciding.\n```md\n1. 2026-11-08 priority: example\n```\n")
        self.core("check")
        self.git("add", "--", "collection.jobs/A.md")
        self.core("check", "--staged")
        if fixtures.sqlite3:
            self.assertEqual(self.rows("query", "jobs", "SELECT priority FROM jobs")[0][1:], [["P1"]])

    def test_numbered_priority_prose_outside_history_is_not_a_decision(self):
        for prose in ("1. Priority: P1 — foundational", "2) Recommended priority: P1",
                      "1. Proposed priority: P1 until costs are known.",
                      "- Proposed priority: P1 until costs are known."):
            with self.subTest(prose=prose):
                self.put("jobs/A", "# A\n\n## Assessment\n" + prose + "\n")
                self.core("check")
                self.git("add", "--", "collection.jobs/A.md")
                self.core("check", "--staged")
                self.cli("graph", "jobs/A")
                if fixtures.sqlite3:
                    self.rows("query", "jobs", "SELECT priority FROM jobs")

    def test_dated_governed_lists_outside_history_still_fail(self):
        for marker in ("-", "*", "+", "1.", "2)"):
            for date in ("2026-11-08", "2026-11-99"):
                with self.subTest(marker=marker, date=date):
                    self.put("jobs/A", "# A\n\n## Assessment\n" + marker + " " + date +
                             " priority: P1 — reviewed; authority: D8\n")
                    self.assertIn("governed entry outside", self.core("check", ok=False))
                    self.git("add", "--", "collection.jobs/A.md")
                    self.assertIn("governed entry outside", self.core("check", "--staged", ok=False))
                    self.assertIn("governed entry outside", self.cli("graph", "jobs/A", ok=False)[1])
                    if fixtures.sqlite3:
                        self.assertIn("governed entry outside", self.cli(
                            "query", "jobs", "SELECT priority FROM jobs", ok=False)[1])


    def test_malformed_new_governed_entries_cannot_hide_behind_old_value(self):
        original = "# A\n\n## History\n" + fixtures.EVENT + "\n"
        self.put("jobs/A", original)
        self.git("add", "--", "collection.jobs/A.md")
        self.git("commit", "-qm", "record")
        event = "2026-11-07 priority: P1 — changed; authority: D8"
        for prefix in ("  - ", "-  "):
            with self.subTest(prefix=prefix):
                self.put("jobs/A", original.replace("## History\n", "## History\n" + prefix + event + "\n"))
                self.git("add", "--", "collection.jobs/A.md")
                self.assertIn("PROBLEM", self.core("check", "--staged", ok=False))
                if fixtures.sqlite3:
                    self.cli("query", "jobs", "SELECT priority FROM jobs", ok=False)


    def test_url_prose_bullet_after_title_is_not_a_malformed_header(self):
        for gap in ("", "\n"):
            with self.subTest(gap=gap):
                self.put("jobs/A", "# A\n" + gap + "- https://example.invalid/reference — prose\n")
                self.core("check")
                rows, _ = self.rows("graph", "jobs/A")
                self.assertEqual(len(rows), 2)  # header and origin only


if __name__ == "__main__":
    unittest.main()
