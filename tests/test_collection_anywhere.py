"""Collections at any depth, and archive/restore."""
import os
import shutil
import subprocess
import sys
import unittest

import test_collection as fixtures


@unittest.skipUnless(shutil.which("git"), "Git required")
class CollectionAnywhere(unittest.TestCase):
    setUp = fixtures.Collections.setUp
    call = fixtures.Collections.call
    git = fixtures.Collections.git
    cli = fixtures.Collections.cli
    core = fixtures.Collections.core
    put = fixtures.Collections.put
    rows = fixtures.Collections.rows

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode())
        return path

    def save(self, *paths):
        self.git("add", "--", *paths)
        self.assertNotIn("PROBLEM", self.core("check", "--staged"))
        self.git("commit", "-qm", "save")

    def problems(self, *args):
        return self.call(fixtures.sys.executable, "tools/minibrain.py", "check", *args, ok=False)[0]

    def add_space(self):
        self.write("spaces/Sorrel.md", "# Sorrel\n")
        self.write("MAP.md", "# MAP\n- [[spaces/Sorrel]]\n")
        self.write("CHANGELOG.md", "# CHANGELOG\n- Sorrel\n")
        self.save("spaces/Sorrel.md", "MAP.md", "CHANGELOG.md")

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_nested_and_root_collections_query_needs_and_graph(self):
        self.add_space()
        self.put("jobs/A", "# A\n- state: open\n- needs: other/X\n\n[[spaces/Sorrel/collection.other/X]]\n")
        self.write("spaces/Sorrel/collection.other/X.md", "# X\n- state: ok\n- needs: jobs/B\n")
        self.put("jobs/B", "# B\n- state: done\n")
        self.assertEqual(self.rows("query", "jobs", "SELECT _id,_unmet FROM jobs ORDER BY _id")[0],
                         [["_id", "_unmet"], ["A", "0"], ["B", "0"]])
        self.assertEqual(self.rows("query", "other", "SELECT _ref,_unmet FROM other")[0][1:], [["other/X", "0"]])
        self.assertEqual(self.rows("query", "jobs", "SELECT need,depth FROM reach WHERE item='jobs/A' ORDER BY depth")[0][1:],
                         [["other/X", "1"], ["jobs/B", "2"]])
        graph = self.rows("graph", "other/X")[0]
        self.assertIn(["prerequisites", "1", "jobs/B", "done", "B"], graph)
        self.assertIn(["dependants", "1", "jobs/A", "open", "A"], graph)
        # Nested records are neither space notes nor changelog triggers.
        self.save("collection.jobs", "spaces/Sorrel/collection.other")
        self.assertNotIn("PROBLEM", self.core("check"))

    def test_moved_collection_saves_but_plain_deletion_does_not(self):
        self.put("jobs/A", "# A\n- needs: B\n")
        self.put("jobs/B", "# B\n- state: done\n")
        self.save("collection.jobs")
        self.cli("archive", "jobs", "B")
        self.save("collection.jobs/B.md", "collection.jobs.archive.md")
        (self.root / "spaces/Project").mkdir(parents=True)
        self.git("mv", "collection.jobs", "spaces/Project/collection.jobs")
        self.git("mv", "collection.jobs.archive.md", "spaces/Project/collection.jobs.archive.md")
        self.assertNotIn("PROBLEM", self.core("check", "--staged"))
        self.git("commit", "-qm", "move")
        self.git("rm", "-q", "--", "spaces/Project/collection.jobs/A.md")
        self.assertIn("committed record deleted: spaces/Project/collection.jobs/A.md", self.problems("--staged"))

    def test_orphan_archive_clash_names_the_archive_file(self):
        self.put("jobs/A")
        self.write("spaces/Sorrel/collection.jobs.archive.md", "# Archive\n")
        message = "duplicate collection name jobs: collection.jobs, spaces/Sorrel/collection.jobs.archive.md"
        self.assertIn(message, self.cli("query", "jobs", ok=False)[1])
        self.assertIn(message, self.problems())

    def test_ignored_archive_is_reported(self):
        self.archive_ready()
        self.cli("archive", "jobs", "B")
        self.write(".gitignore", "*.archive.md\n")
        self.assertIn("managed Markdown is ignored and may disappear on clone: collection.jobs.archive.md",
                      self.problems())

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_crlf_checkout_reads_and_restores_archives(self):
        self.archive_ready()
        self.cli("archive", "jobs", "B")
        self.save("collection.jobs/B.md", "collection.jobs.archive.md")
        clone = self.root / "crlf"
        self.git("clone", "-q", "-c", "core.autocrlf=true", ".", "crlf")
        self.assertIn(b"-->\r\n", (clone / "collection.jobs.archive.md").read_bytes())

        def run(*args):
            p = subprocess.run([sys.executable, "tools/collection.py", *args], cwd=clone, env=self.env,
                               capture_output=True, timeout=30)
            self.assertEqual(p.returncode, 0, p.stderr)
            return p.stdout.decode()
        self.assertIn("A", run("query", "jobs", "SELECT _id,_unmet FROM jobs"))
        self.assertEqual(run("restore", "jobs", "B"), "restored jobs/B\n")
        self.assertEqual((clone / "collection.jobs/B.md").read_bytes(), b"# B\r\n- state: done\r\n")
        self.assertNotIn("archived:", (clone / "collection.jobs.archive.md").read_text(encoding="utf-8"))

    def test_duplicate_names_are_refused_naming_both_paths(self):
        self.put("jobs/A")
        self.write("spaces/Sorrel/collection.jobs/B.md", "# B\n")
        message = "duplicate collection name jobs: collection.jobs, spaces/Sorrel/collection.jobs"
        for args in (("query", "jobs"), ("graph", "jobs/A")):
            self.assertIn(message, self.cli(*args, ok=False)[1])
        self.assertIn("PROBLEM: " + message, self.problems())

    def test_hidden_and_inner_folders_are_not_collections(self):
        self.write(".hidden/collection.secret/A.md", "# A\n")
        self.write("collection.jobs/collection.inner/A.md", "# A\n")
        self.put("jobs/A")
        for name in ("secret", "inner"):
            self.assertIn("unknown collection: " + name, self.cli("query", name, "SELECT 1", ok=False)[1])

    def test_core_rules_apply_at_depth(self):
        self.write("projects/collection.jobs/AGENTS.md", "# A\n")
        self.assertIn("root-only control file inside a collection: projects/collection.jobs/AGENTS.md",
                      self.problems())
        os.remove(self.root / "projects/collection.jobs/AGENTS.md")
        target = self.root / "elsewhere"
        target.mkdir()
        os.rmdir(self.root / "projects/collection.jobs")
        os.symlink(target, self.root / "projects/collection.jobs", target_is_directory=True)
        self.git("add", "--", "projects/collection.jobs")
        self.assertIn("symlink or gitlink collection path in index: projects/collection.jobs",
                      self.problems("--staged"))

    def archive_ready(self, text="# B\n- state: done\n"):
        self.put("jobs/A", "# A\n- state: open\n- needs: B\n\n[[collection.jobs/B]]\n")
        path = self.put("jobs/B", text)
        self.save("collection.jobs")
        return path

    def test_archive_then_restore_returns_identical_bytes(self):
        text = "# B\r\n- state: done\r\n\r\nNo final newline — ü"
        path = self.archive_ready(text)
        self.assertEqual(self.cli("archive", "jobs", "B")[0], "archived jobs/B\n")
        self.assertFalse(path.exists())
        archive = self.root / "collection.jobs.archive.md"
        self.assertEqual(sorted(p.name for p in self.root.glob("collection.jobs/*.md")), ["A.md"])
        # The deleted-record check accepts the archived move; the link stays valid.
        self.save("collection.jobs/B.md", "collection.jobs.archive.md")
        self.assertNotIn("PROBLEM", self.core("check"))
        self.assertEqual(self.cli("restore", "jobs", "B")[0], "restored jobs/B\n")
        self.assertEqual(path.read_bytes(), text.encode())
        self.assertNotIn("archived:", archive.read_text(encoding="utf-8"))
        self.save("collection.jobs/B.md", "collection.jobs.archive.md")

    def test_archive_and_restore_refusals_have_no_effect(self):
        path = self.archive_ready()
        self.put("jobs/New")
        cases = {"Missing": "no such active record", "New": "uncommitted or changed since commit; save it first"}
        for item, reason in cases.items():
            self.assertIn(f"REFUSED: jobs/{item}: {reason}", self.cli("archive", "jobs", item, ok=False)[1])
        path.write_bytes(b"# B\n- state: open\n")
        self.assertIn("uncommitted or changed since commit", self.cli("archive", "jobs", "B", ok=False)[1])
        self.git("checkout", "--", "collection.jobs/B.md")
        self.put("jobs/C", "# C\n\n<!-- end archived: C -->\n")
        self.save("collection.jobs/C.md")
        self.assertIn("content contains archive-marker text (<!-- archived:)", self.cli("archive", "jobs", "C", ok=False)[1])
        self.assertFalse((self.root / "collection.jobs.archive.md").exists())
        # One refusal does not block the others, but the exit status reports it.
        err = self.cli("archive", "jobs", "B", "Missing", ok=False)[1]
        self.assertIn("REFUSED: jobs/Missing", err)
        self.assertFalse(path.exists())
        self.assertIn("already archived", self.cli("archive", "jobs", "B", ok=False)[1])
        archive = (self.root / "collection.jobs.archive.md").read_bytes()
        self.assertIn("REFUSED: jobs/A: active record exists: collection.jobs/A.md", self.cli("restore", "jobs", "A", ok=False)[1])
        self.assertIn("REFUSED: jobs/Missing: not archived", self.cli("restore", "jobs", "Missing", ok=False)[1])
        self.assertEqual((self.root / "collection.jobs.archive.md").read_bytes(), archive)

    def test_plain_deletion_and_tampered_archive_are_problems(self):
        path = self.archive_ready()
        path.unlink()
        self.git("add", "--", "collection.jobs/B.md")
        self.assertIn("committed record deleted: collection.jobs/B.md (close it by state or use the archive command; do not delete)",
                      self.problems("--staged"))
        # Moving different content into the archive is not archiving.
        self.write("collection.jobs.archive.md", "# Archive\n\n<!-- archived: B 2026-11-13 -->\n"
                   "# B\n- state: open\n\n<!-- end archived: B -->\n")
        self.git("add", "--", "collection.jobs.archive.md")
        self.assertIn("archived record differs from its committed version: collection.jobs/B.md",
                      self.problems("--staged"))
        self.git("reset", "-q")
        self.git("checkout", "--", "collection.jobs/B.md")
        os.remove(self.root / "collection.jobs.archive.md")
        self.cli("archive", "jobs", "B")
        self.save("collection.jobs/B.md", "collection.jobs.archive.md")
        archive = self.root / "collection.jobs.archive.md"
        archive.write_text(archive.read_text(encoding="utf-8").replace("state: done", "state: open"), encoding="utf-8")
        self.git("add", "--", "collection.jobs.archive.md")
        self.assertIn("archived record altered: collection.jobs/B.md", self.problems("--staged"))
        archive.write_text("# Archive\n", encoding="utf-8")
        self.git("add", "--", "collection.jobs.archive.md")
        self.assertIn("archived record removed: collection.jobs/B.md", self.problems("--staged"))
        # A block for a record that was never committed is not an archived move.
        self.git("checkout", "HEAD", "--", "collection.jobs.archive.md")
        with archive.open("a", encoding="utf-8", newline="") as stream:
            stream.write("<!-- archived: Z 2026-11-13 -->\n# Z\n\n<!-- end archived: Z -->\n")
        self.git("add", "--", "collection.jobs.archive.md")
        self.assertIn("archive block has no committed record deleted in this save: collection.jobs/Z.md",
                      self.problems("--staged"))

    @unittest.skipUnless(fixtures.sqlite3, "sqlite3 required")
    def test_archived_prerequisite_satisfies_and_its_id_stays_reserved(self):
        self.archive_ready()
        self.cli("archive", "jobs", "B")
        self.assertEqual(self.rows("query", "jobs", "SELECT _id,_unmet FROM jobs")[0][1:], [["A", "0"]])
        self.assertEqual(self.rows("query", "jobs", "SELECT item,need FROM needs")[0][1:], [["jobs/A", "jobs/B"]])
        rows, err = self.rows("query", "jobs")
        self.assertEqual([row[0] for row in rows[1:]], ["A"])
        self.assertIn("1 archived records in collection.jobs.archive.md: not table rows", err)
        self.assertIn(["prerequisites", "1", "jobs/B", "done", "B"], self.rows("graph", "jobs/A")[0])
        self.put("jobs/B", "# B again\n")
        self.assertIn("archived ID reused by an active record: collection.jobs/B.md",
                      self.cli("query", "jobs", ok=False)[1])
        self.assertIn("archived ID reused by an active record: collection.jobs/B.md", self.problems())

    def test_restored_record_keeps_governed_history(self):
        self.put("jobs/G", "# G\n\n## History\n" + fixtures.EVENT + "\n")
        self.save("collection.jobs")
        self.cli("archive", "jobs", "G")
        self.save("collection.jobs/G.md", "collection.jobs.archive.md")
        path = self.root / "collection.jobs/G.md"
        self.cli("restore", "jobs", "G")
        path.write_text("# G\n\n## History\n" + fixtures.EVENT.replace("P2", "P1") + "\n", encoding="utf-8")
        self.git("add", "--", "collection.jobs/G.md", "collection.jobs.archive.md")
        self.assertIn("earlier governed entry altered or removed in collection.jobs/G.md", self.problems("--staged"))

    def test_archive_works_at_depth(self):
        self.add_space()
        path = self.write("spaces/Sorrel/collection.other/X.md", "# X\n- state: ok\n")
        self.save("spaces/Sorrel/collection.other")
        self.cli("archive", "other", "X")
        self.assertTrue((self.root / "spaces/Sorrel/collection.other.archive.md").exists())
        # The archive is collection material: no Map registration or changelog line needed.
        self.save("spaces/Sorrel/collection.other/X.md", "spaces/Sorrel/collection.other.archive.md")
        self.assertNotIn("PROBLEM", self.core("check"))
        # A clone has no empty folder; the archive alone keeps the collection.
        os.rmdir(path.parent)
        self.assertIn(["origin", "0", "other/X", "ok", "X"], self.rows("graph", "other/X")[0])
        self.cli("restore", "other", "X")
        self.assertEqual(path.read_text(encoding="utf-8"), "# X\n- state: ok\n")


if __name__ == "__main__":
    unittest.main()
