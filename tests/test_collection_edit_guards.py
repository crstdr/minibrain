"""Targeted editing must preserve body boundaries and tolerate unrelated damage."""
import shutil
import unittest

import test_collection as fixtures


@unittest.skipUnless(shutil.which("git"), "Git required")
class CollectionEditGuards(unittest.TestCase):
    # Share setup, not the fixture class's test methods.
    setUp = fixtures.Collections.setUp
    call = fixtures.Collections.call
    git = fixtures.Collections.git
    cli = fixtures.Collections.cli
    core = fixtures.Collections.core
    put = fixtures.Collections.put
    rows = fixtures.Collections.rows

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_unset_last_header_field_does_not_promote_body(self):
        record = self.put("jobs/A", "# A\n- state: open\n\n- state: done\n")
        self.cli("edit", "jobs/A", "--unset", "state")
        self.assertTrue(record.read_bytes().endswith(b"- state: done\n"))
        self.assertNotIn(b"- state: open", record.read_bytes())
        rows, _ = self.rows("query", "jobs", "SELECT state IS NULL FROM jobs")
        self.assertEqual(rows[1:], [["1"]])
        self.core("check")

    def test_setext_peer_headings_survive_section_edit(self):
        for peer in ("#risk\n-----\npeer body  \n",
                     "First peer line\nsecond peer line\n-----\npeer body  \n"):
            with self.subTest(peer=peer):
                record = self.put("jobs/A", "# A\n\n## Mine\nold\n\n" + peer)
                self.cli("edit", "jobs/A", "--section", "Mine", data="replacement\n\n")
                content = record.read_bytes()
                self.assertTrue(content.endswith(peer.encode()), content)
                self.assertIn(b"## Mine\nreplacement\n", content)
                self.assertNotIn(b"\nold\n", content)

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

    def test_unrelated_malformed_or_broken_dependency_does_not_block_edit(self):
        for unrelated in ("# B\n- **state**: open\n",
                          "# B\n- needs: missing\n"):
            with self.subTest(unrelated=unrelated):
                target = self.put("jobs/A", "# A\n- cost: 1\n")
                other = self.put("jobs/B", unrelated)
                self.cli("edit", "jobs/A", "--set", "cost", "2")
                self.assertEqual(target.read_bytes(), b"# A\n- cost: 2\n")
                self.assertEqual(other.read_bytes(), unrelated.encode())

    def test_dependency_repair_can_leave_an_unrelated_broken_dependency(self):
        target = self.put("jobs/A", "# A\n- needs: absent-a\n")
        unrelated = "# B\n- needs: absent-b\n"
        other = self.put("jobs/B", unrelated)
        self.cli("edit", "jobs/A", "--unset", "needs")
        self.assertNotIn(b"needs:", target.read_bytes())
        self.assertEqual(other.read_bytes(), unrelated.encode())

    def test_url_prose_bullet_after_title_is_not_a_malformed_header(self):
        for gap in ("", "\n"):
            with self.subTest(gap=gap):
                self.put("jobs/A", "# A\n" + gap + "- https://example.invalid/reference — prose\n")
                self.core("check")
                rows, _ = self.rows("graph", "jobs/A")
                self.assertEqual(len(rows), 2)  # header and origin only


if __name__ == "__main__":
    unittest.main()
