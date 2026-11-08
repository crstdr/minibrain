"""Regression probes for canonical values, parsing boundaries and targeted writes."""
import hashlib
import re
import shutil
import unittest

import test_collection as fixtures


@unittest.skipUnless(shutil.which("git"), "Git required")
class CollectionSafety(unittest.TestCase):
    # Reuse the installed-brain fixture without inheriting its test cases.
    setUp = fixtures.Collections.setUp
    call = fixtures.Collections.call
    git = fixtures.Collections.git
    cli = fixtures.Collections.cli
    core = fixtures.Collections.core
    put = fixtures.Collections.put
    rows = fixtures.Collections.rows

    def configure(self, name, expression):
        helper = self.root / "tools/collection.py"
        text, count = re.subn("^" + name + r" = .*?$", name + " = " + expression,
                              helper.read_text(encoding="utf-8"), flags=re.M)
        self.assertEqual(count, 1)
        helper.write_text(text, encoding="utf-8")

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_effective_governed_state_needs_and_numeric_value(self):
        self.configure("GOVERNED_FIELDS", "{'state', 'needs', 'benefit'}")
        self.put("jobs/A", "# A\n\n## History\n"
                 "- 2020-02-01 benefit: 8 — estimated; authority: D1\n"
                 "- 2020-02-01 needs: B other/X — linked; authority: D1\n"
                 "- 2020-01-01 needs: missing — superseded; authority: D0\n")
        self.put("jobs/B", "# B\n\n## History\n"
                 "- 2020-02-01 state: done — delivered; authority: D1\n"
                 "- 2020-01-01 state: open — captured; authority: D0\n")
        self.put("other/X", "# X\n\n## History\n"
                 "- 2020-02-01 state: ok — accepted; authority: D1\n")
        rows, _ = self.rows("query", "jobs",
                            "SELECT _id,_unmet,typeof(benefit),benefit FROM jobs WHERE _id='A'")
        self.assertEqual(rows[1:], [["A", "0", "real", "8"]])
        rows, _ = self.rows("query", "jobs", "SELECT need FROM needs WHERE item='jobs/A' ORDER BY need")
        self.assertEqual(rows[1:], [["jobs/B"], ["other/X"]])
        self.core("check")

    def test_dot_stem_is_a_stable_checked_record_id(self):
        self.put("jobs/.kept", "# Kept\n- state: done\n")
        self.put("jobs/A", "# A\n- needs: .kept\n")
        self.core("check")
        rows, _ = self.rows("graph", "jobs/A")
        self.assertEqual([row[2] for row in rows[1:]], ["jobs/A", "jobs/.kept"])
        self.git("add", "--", "collection.jobs")
        self.core("check", "--staged")
        self.git("commit", "-qm", "records")
        self.git("mv", "collection.jobs/.kept.md", "collection.jobs/.renamed.md")
        self.assertIn("committed record deleted", self.core("check", "--staged", ok=False))

    def test_nonblank_line_cannot_silently_end_started_header(self):
        self.put("jobs/A", "# A\n\n- state: open\ncost = 2\n- needs: missing\n")
        self.assertIn("PROBLEM", self.core("check", ok=False))

    def test_body_lists_are_not_headers_after_the_body_boundary(self):
        for text in (
            "# A\n\n- stretch your legs\n- choose something\n",
            "# A\n\nOrdinary body.\n\n- needs: this-is-only-prose\n",
            "# A\n\n- state: open\n\n- needs: this-is-only-prose\n",
        ):
            with self.subTest(text=text):
                self.put("jobs/A", text)
                self.core("check")
                rows, _ = self.rows("graph", "jobs/A")
                self.assertEqual(len(rows), 2)  # header and origin, no invented edge

    def test_setext_section_body_preserves_other_sections_and_fenced_headings(self):
        original = ("# A\r\n\r\nMine\r\n----\r\nold\r\n"
                    "## mine\r\nother-case\r\n## Peer\r\nkeep\n")
        record = self.put("jobs/A", original)
        payload = "### Detail\nnew\n```md\n## Peer\n```\n"
        self.cli("edit", "jobs/A", "--section", "Mine", data=payload)
        expected = original.replace("old\r\n", payload.replace("\n", "\r\n"))
        self.assertEqual(record.read_bytes(), expected.encode())
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "")

    def test_duplicate_atx_and_setext_heading_refuses_without_mutation(self):
        original = "# A\n\n## Mine\none\nMine\n----\ntwo\n"
        record = self.put("jobs/A", original)
        self.cli("edit", "jobs/A", "--section", "Mine", data="replacement\n", ok=False)
        self.assertEqual(record.read_bytes(), original.encode())

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_query_does_not_mutate_crlf_records_or_create_import_cache(self):
        content = "# A\r\n\r\n- cost: 3\r\n\r\n## Review\r\nkeep  \r\n"
        record = self.put("jobs/A", content)
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*")
                  if p.is_file() and ".git" not in p.parts}
        rows, _ = self.rows("query", "jobs", "SELECT _rev,cost FROM jobs")
        self.assertEqual(rows[1][0], hashlib.sha256(content.encode()).hexdigest())
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*")
                 if p.is_file() and ".git" not in p.parts}
        self.assertEqual(after, before)
        self.assertEqual(record.read_bytes(), content.encode())

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_invalid_numeric_edits_remain_raw_and_query_reports_null(self):
        record = self.put("jobs/A", "# A\n- code: 0012\n- cost: 3\n")
        self.cli("edit", "jobs/A", "--set", "cost", "unknown")
        rows, err = self.rows("query", "jobs", "SELECT code,typeof(code),cost IS NULL FROM jobs")
        self.assertEqual(rows[1:], [["0012", "text", "1"]])
        self.assertIn("jobs/A", err)
        self.assertIn("unknown", err)
        self.assertIn(b"- cost: unknown\n", record.read_bytes())

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_unmet_counts_direct_edges_but_propagates_unknown_evidence(self):
        self.put("jobs/A", "# A\n- needs: other/B\n")
        self.put("other/B", "# B\n- state: ok\n- needs: jobs/C\n")
        self.put("jobs/C", "# C\n- state: open\n")
        rows, _ = self.rows("query", "jobs", "SELECT _unmet FROM jobs WHERE _id='A'")
        self.assertEqual(rows[1:], [["0"]])  # direct B is satisfied; do not count C twice
        self.put("jobs/C", "# C\n")
        rows, err = self.rows("query", "jobs", "SELECT _unmet FROM jobs WHERE _id='A'")
        self.assertEqual(rows[1:], [[""]])
        self.assertIn("unknown", err)
        self.configure("SATISFIED_STATES", "{'jobs': {'done'}}")
        self.put("jobs/C", "# C\n- state: done\n")
        rows, _ = self.rows("query", "jobs", "SELECT _unmet FROM jobs WHERE _id='A'")
        self.assertEqual(rows[1:], [[""]])  # other/B has no state configuration


if __name__ == "__main__":
    unittest.main()
