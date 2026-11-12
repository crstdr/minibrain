"""Integration tests against disposable installed brains."""
import csv
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

try:
    import sqlite3
except ImportError:
    sqlite3 = None

TOOLS = Path(__file__).resolve().parents[1] / "starter" / "tools"
EVENT = "- 2020-01-01 priority: P2 — reviewed; authority: D7"


@unittest.skipUnless(shutil.which("git"), "Git required")
class Collections(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_EDITOR="false")
        self.git("init", "-q")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.root / "tools").mkdir()
        for name in ("minibrain.py", "collection.py"):
            shutil.copyfile(TOOLS / name, self.root / "tools" / name)
        path = self.root / "tools/collection.py"
        s = path.read_text(encoding="utf-8")
        for key, value in {
            "GOVERNED_FIELDS": "{'PrIoRiTy'}",
            "NUMERIC_FIELDS": "{'jobs': {'cost', 'benefit', 'never-used'}}",
            "SATISFIED_STATES": "{'jobs': {'done'}, 'other': {'ok'}}",
        }.items():
            s, n = re.subn("^" + key + r" = .*?$", key + " = " + value, s, flags=re.M)
            self.assertEqual(n, 1)
        path.write_text(s, encoding="utf-8")
        for name in ("AGENTS", "CHANGELOG", "MAP", "MEMORY"):
            text = "## Focus\n## Open threads\n" if name == "MEMORY" else "# " + name + "\n"
            (self.root / (name + ".md")).write_text(text, encoding="utf-8")
        self.git("add", "--", "AGENTS.md", "CHANGELOG.md", "MAP.md", "MEMORY.md", "tools")
        self.git("commit", "-qm", "fixture")

    def call(self, *argv, data="", ok=True):
        p = subprocess.run(argv, cwd=self.root, env=self.env, input=data.encode(),
                           capture_output=True, timeout=30)
        self.assertEqual(p.returncode == 0, ok, (p.stdout, p.stderr, argv))
        return p.stdout.decode(), p.stderr.decode()

    def git(self, *args):
        return self.call("git", *args)[0]

    def cli(self, *args, **kw):
        return self.call(sys.executable, "tools/collection.py", *args, **kw)

    def core(self, *args, **kw):
        return self.call(sys.executable, "tools/minibrain.py", *args, **kw)[0]

    def put(self, ref, text="# Item\n"):
        name, item = ref.split("/")
        path = self.root / ("collection." + name) / (item + ".md")
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(text.encode())
        return path

    def rows(self, *args, **kw):
        out, err = self.cli(*args, **kw)
        return list(csv.reader(io.StringIO(out, newline=""), delimiter="\t")), err

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_query_types_schema_filters_and_tsv(self):
        self.put("jobs/001", '# One\t"quoted"\n\n- cost: 2.5 (days)\n- benefit: 0\n'
                 '- code: 0012\n- review-a: P10\n- tags: #go\n\n## Reviewer\n\n## History\n' + EVENT + "\n")
        self.put("jobs/B", "# B\n- cost: 3oops\n- review-a: P2\n")
        rows, err = self.rows("query", "jobs", "-", data="""SELECT _id,_title,typeof(cost),cost,
            typeof(benefit),benefit/nullif(cost,0),code,never_used,priority FROM jobs ORDER BY _id""")
        self.assertEqual(rows[1], ["001", 'One\t"quoted"', "real", "2.5", "real", "0", "0012", "", "P2"])
        self.assertEqual(rows[2][2:4], ["null", ""])
        self.assertIn("invalid numeric", err)
        rows, _ = self.rows("query", "jobs", """SELECT _id FROM jobs ORDER BY review_a COLLATE natural_id""")
        self.assertEqual(rows[1:], [["B"], ["001"]])
        self.git("add", "--", "collection.jobs")
        self.git("commit", "-qm", "records")
        rows, err = self.rows("query", "jobs")
        self.assertEqual(rows[0], ["_id", "state", "_title"])
        self.assertIn("jobs (", err)
        self.assertIn("never_used REAL", err)
        for name, identifier in (('a"b', 'a_b'), ('a]b`c', 'a_b_c')):
            with self.subTest(name=name):
                (self.root / ("collection." + name)).mkdir()
                rows, _ = self.rows("query", name, "SELECT _id FROM " + identifier)
                self.assertEqual(rows, [["_id"]])
                _, err = self.rows("query", name)
                self.assertIn(identifier + " (", err)
        self.assertIn("unknown collection", self.cli("query", "nope", ok=False)[1])
        (self.root / "collection.reach").mkdir()
        self.assertIn("collision", self.cli("query", "jobs", ok=False)[1])

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_query_tsv_uses_lf_row_terminators(self):
        self.put("jobs/A", "# A\n")
        out, _ = self.cli("query", "jobs", "SELECT _id,_title FROM jobs")
        self.assertEqual(out, "_id\t_title\nA\tA\n")

    def test_graph_tsv_uses_lf_and_quotes_tabs_and_quotes(self):
        self.put("jobs/A", "# A\n- state: open\n")
        out, _ = self.cli("graph", "jobs/A")
        self.assertEqual(out, "direction\tdepth\tid\tstate\ttitle\n"
                             "origin\t0\tjobs/A\topen\tA\n")
        self.put("jobs/A", '# A\t"quoted"\n- state: open\n')
        rows, _ = self.rows("graph", "jobs/A")
        self.assertEqual(rows[1], ["origin", "0", "jobs/A", "open", 'A\t"quoted"'])

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_query_tsv_round_trips_control_characters_in_cells_and_aliases(self):
        self.put("jobs/A")
        aliases = ["cr\rheader", "lf\nheader", "tab\theader", 'quote"header',
                   "pair\r\nheader", "last-cr\r"]
        values = ["carriage\rreturn", "line\nfeed", "tab\tvalue", 'double"quote',
                  "pair\r\nvalue", "ending\r"]
        sql = "SELECT " + ", ".join("'" + value + "' AS [" + alias + "]"
                                    for alias, value in zip(aliases, values))
        out, _ = self.cli("query", "jobs", sql)
        self.assertTrue(out.endswith("\n"))
        rows = list(csv.reader(io.StringIO(out, newline=""), delimiter="\t"))
        self.assertEqual(rows, [aliases, values])

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_graph_readiness_and_distinct_downstream_coverage(self):
        for ref, state, needs in (("jobs/A", "open", "B, B other/X"), ("jobs/B", "done", "other/X"),
                                  ("other/X", "ok", ""), ("jobs/C", "open", "A"),
                                  ("jobs/D", "open", "missing"), ("jobs/E", "open", "D"),
                                  ("jobs/F", "open", "G"), ("jobs/G", "open", "F"),
                                  ("jobs/H", "open", "F"), ("jobs/I", "open", "raw/Y"),
                                  ("raw/Y", "anything", ""), ("jobs/J", "open", "K"), ("jobs/K", "", "")):
            self.put(ref, f"# X\n- state: {state}\n- needs: {needs}\n" +
                     ("- benefit: 4\n" if ref == "jobs/A" else ""))
        rows, err = self.rows("query", "jobs", "SELECT _id,_unmet FROM jobs")
        self.assertEqual(dict(rows[1:]), dict(A="0", B="0", C="1", D="", E="", F="", G="",
                                              H="", I="", J="", K="0"))
        self.assertIn("needs cycle", err)
        rows, _ = self.rows("graph", "other/X")
        self.assertEqual(rows[0], ["direction", "depth", "id", "state", "title"])
        self.assertEqual([(r[0], r[1], r[2]) for r in rows[1:]], [
            ("origin", "0", "other/X"), ("dependants", "1", "jobs/A"),
            ("dependants", "1", "jobs/B"), ("dependants", "2", "jobs/C")])
        rows, _ = self.rows("query", "other", """SELECT count(*),count(benefit),sum(benefit),max(depth)
            FROM reach JOIN jobs ON _ref=item WHERE need='other/X'""")
        self.assertEqual(rows[1:], [["3", "1", "4", "2"]])
        rows, _ = self.rows("query", "jobs", "SELECT count(*) FROM reach WHERE item=need")
        self.assertEqual(rows[1:], [["0"]])

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_count_star_over_recursive_and_ordinary_ctes(self):
        self.put("jobs/A")
        for sql, expected in (
            ("WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM c WHERE n < 3) "
             "SELECT count(*) FROM c", "3"),
            ("WITH c AS (SELECT _id FROM jobs) SELECT count(*) FROM c", "1"),
            ("WITH c(n) AS (VALUES(1),(2),(3)) SELECT count(*) FROM c", "3"),
        ):
            with self.subTest(sql=sql):
                rows, _ = self.rows("query", "jobs", sql)
                self.assertEqual(rows[1:], [[expected]])

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_real_tsv_values_are_compact_without_changing_text_or_fractions(self):
        self.put("jobs/A", "# A\n- benefit: 8\n- cost: 2.5\n- code: 0012\n")
        rows, _ = self.rows("query", "jobs", "SELECT typeof(benefit),benefit,cost,code,"
                            "8.0 AS calculated,1.25 AS fraction FROM jobs")
        self.assertEqual(rows[1:], [["real", "8", "2.5", "0012", "8", "1.25"]])

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_sql_guards(self):
        self.put("jobs/A")
        for sql in ("DELETE FROM jobs", "ATTACH 'external' AS x", "PRAGMA table_info(jobs)",
                    "SELECT * FROM pragma_table_info('jobs')", "SELECT load_extension('x')",
                    "SELECT writefile('external','x')", "SELECT * FROM sqlite_master",
                    "SELECT count(*) FROM sqlite_master", "SELECT count(*) FROM sqlite_schema",
                    "WITH c AS (SELECT name FROM sqlite_master) SELECT count(*) FROM c",
                    "CREATE TEMP TABLE t(x)", "SELECT 1; SELECT 2"):
            with self.subTest(sql=sql):
                self.assertTrue(self.cli("query", "jobs", sql, ok=False)[1])
        self.assertFalse((self.root / "external").exists())
        for aggregate in ("sum(x)", "count(*)"):
            with self.subTest(aggregate=aggregate):
                err = self.cli("query", "jobs", "WITH RECURSIVE loop(x) AS "
                               "(VALUES(1) UNION ALL SELECT x+1 FROM loop) "
                               f"SELECT {aggregate} FROM loop", ok=False)[1]
                self.assertIn("budget", err)
        if hasattr(sqlite3.Connection, "setconfig") and hasattr(sqlite3, "SQLITE_DBCONFIG_DQS_DML"):
            self.assertIn("no such column", self.cli("query", "jobs", 'SELECT "typo" FROM jobs', ok=False)[1])

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_optional_sqlite_controls(self):
        code = """import sys, sqlite3
sys.path.insert(0, 'tools')
import collection
db = sqlite3.connect(':memory:')
class Legacy:
    def __getattr__(self, name):
        if name in ('setconfig', 'setlimit'):
            raise AttributeError(name)
        return getattr(db, name)
collection.restrict(Legacy(), sqlite3, {}, 'SELECT "unknown"')
assert db.execute('SELECT 1').fetchone() == (1,)
try:
    db.execute('ATTACH :name AS x', {'name': 'external'})
except sqlite3.DatabaseError:
    pass
else:
    raise AssertionError('attach succeeded')
db.close()"""
        self.assertIn("double-quoted unknown", self.call(sys.executable, "-B", "-c", code)[1])
        self.assertFalse((self.root / "external").exists())

    def test_parser_namespace_and_staged_stability(self):
        path = self.put("jobs/X", "# X\n\n- stretch your legs\n- pick something\n")
        self.put("other/X")
        (self.root / "MEMORY.md").write_text("## Focus\n[[collection.jobs/X]]\n## Open threads\n")
        self.core("check")
        (self.root / "MEMORY.md").write_text("## Focus\n[[X]]\n## Open threads\n")
        self.assertIn("broken wikilink", self.core("check", ok=False))
        self.git("restore", "--", "MEMORY.md")
        for line in ("* cost: 1", "- **priority:** P1", "- cost:1", "- cost: 1\n- COST: 2",
                     "- priority: P1", "- _ref: forged"):
            self.put("jobs/X", "# X\n\n" + line + "\n")
            self.assertIn("PROBLEM:", self.core("check", ok=False))
        self.put("jobs/X", "# X\n- source: nowhere\n- tags: wrong\n")
        out = self.core("check", ok=False)
        self.assertIn("source needs", out)
        self.assertIn("tags must", out)
        self.put("jobs/X", "# X\n## History\n" + EVENT + "\n  wrapped\n")
        self.assertIn("one line", self.core("check", ok=False))
        self.put("jobs/X")
        hidden = self.put("jobs/.hidden")
        self.git("add", "--", "collection.jobs")
        self.core("check", "--staged")
        self.git("rm", "-qf", "--", str(hidden.relative_to(self.root)))
        self.core("check", "--staged")
        self.git("commit", "-qm", "collection only")
        for dest in ("collection.jobs/Y.md", "elsewhere.md.txt"):
            self.git("mv", str(path.relative_to(self.root)), dest)
            self.assertIn("committed record deleted", self.core("check", "--staged", ok=False))
            self.git("mv", dest, str(path.relative_to(self.root)))

    def test_suffix_order_multiplicity_and_amend(self):
        second = EVENT.replace("P2", "P3")

        def put_events(events):
            self.put("jobs/A", "# A\n\n## History\n" + "\n".join(events) + "\n")
            self.git("add", "--", "collection.jobs")

        old = [EVENT, second, second]
        put_events(old)
        self.git("commit", "-qm", "history")
        label = self.core("lock", "Writer").split("lock acquired: ")[1].split()[0]
        for revised in ([second, EVENT, second], [EVENT, second], [EVENT + " ", second, second]):
            put_events(revised)
            self.assertIn("earlier governed entry", self.core("check", "--staged", ok=False))
        put_events([second] + old)
        self.core("commit", "--label", label, "-m", "Writer: prepend")
        self.git("mv", "collection.jobs/A.md", "collection.jobs/B.md")
        self.assertIn("committed record deleted", self.core("commit", "--label", label, "--amend", ok=False))
        self.core("unlock", label)


    def test_duplicate_section_symlink_and_optional_install(self):
        path = self.put("jobs/A", "# A\n\n## Mine\none\n## Mine\ntwo\n")
        if hasattr(os, "symlink"):
            link = path.parent / "link.md"
            try:
                link.symlink_to(path)
            except OSError:
                pass
            else:
                self.assertIn("regular file", self.cli("graph", "jobs/link", ok=False)[1])
                link.unlink()
        self.put("jobs/A", "# A\n- priority: forbidden\n")
        (self.root / "tools/collection.py").unlink()
        self.core("check")

    def test_no_sqlite_and_failed_deletion_diff(self):
        self.put("jobs/A")
        boot = """import sys, runpy
sys.path.insert(0, 'tools')
sys.modules['sqlite3'] = None
runpy.run_path(sys.argv[0], run_name='__main__')"""
        for script, args, ok in (("collection", ["graph", "jobs/A"], True),
                                 ("minibrain", ["check"], True), ("collection", ["query", "jobs"], False)):
            code = "import sys; sys.argv=sys.argv[1:]\n" + boot
            _, err = self.call(sys.executable, "-c", code, "tools/" + script + ".py", *args, ok=ok)
            if not ok:
                self.assertIn("requires the optional", err)

        code = """import sys, subprocess
sys.path.insert(0,'tools')
import collection as c
errors = []
def git(*args):
    assert '--no-renames' in args and 'HEAD^' in args
    return subprocess.CompletedProcess(args, int('--diff-filter=D' in args), '', 'failure')
c.check(True, {}, errors, [], git, 'HEAD^')
assert len(errors) == 1 and 'failure' in errors[0], errors"""
        self.call(sys.executable, "-B", "-c", code)

    def test_400_records(self):
        for i in range(400):
            self.put(f"jobs/{i}", "# Item\n" + (f"- needs: {i+1}\n" if i < 399 else "") + "- state: done\n")
        self.core("check")
        if sqlite3:
            rows, _ = self.rows("query", "jobs", "SELECT count(*), max(depth) FROM reach")
            self.assertEqual(rows[1:], [["79800", "399"]])

    @unittest.skipUnless(sqlite3, "sqlite3 required for SQL tests")
    def test_plain_query_does_not_build_transitive_closure(self):
        self.put("jobs/A", "# A\n- needs: B\n")
        self.put("jobs/B", "# B\n- state: done\n")
        script = """import sys
sys.path.insert(0, 'tools')
import collection as c
def forbidden(*args):
    raise AssertionError('ordinary query built reach')
c.walk = forbidden
before, records = c.snapshot()
c.query(before[0], records, 'jobs', 'SELECT _id,_unmet FROM jobs ORDER BY _id', c.head())
"""
        out, _ = self.call(sys.executable, "-B", "-c", script)
        self.assertEqual(list(csv.reader(io.StringIO(out), delimiter="\t"))[1:], [["A", "0"], ["B", "0"]])

    def test_retained_core_filename_and_isolated_python(self):
        self.put("jobs/A", "# A\n- state: open\n")
        (self.root / "tools/minibrain.py").rename(self.root / "tools/kb.py")
        path = self.root / "tools/collection.py"
        path.write_text(path.read_text().replace('CORE_HELPER = "minibrain.py"', 'CORE_HELPER = "kb.py"'))
        if sqlite3:
            out, _ = self.call(sys.executable, "-I", "tools/collection.py", "query", "jobs", "SELECT state FROM jobs")
            self.assertEqual(list(csv.reader(io.StringIO(out), delimiter="\t")), [["state"], ["open"]])

    def test_sql_name_mapping_and_refusals(self):
        self.put('sprint-tasks/A', '# A\n- assessed-on: 2020-01-01\n')
        self.assertEqual(self.rows('query', 'sprint-tasks', 'SELECT assessed_on FROM sprint_tasks')[0][1:], [['2020-01-01']])
        self.assertIn('sprint_tasks (', self.cli('query', 'sprint-tasks')[1])
        self.put('2026-plan/A', '# Plan\n')
        self.assertIn('_2026_plan (', self.cli('query', '2026-plan')[1])
        self.assertEqual(self.rows('query', '2026-plan', 'SELECT _id FROM _2026_plan')[0][1:], [['A']])
        folder = self.root / 'collection._2026_plan'
        folder.mkdir()
        err = self.cli('query', 'sprint-tasks', ok=False)[1]
        self.assertIn('2026-plan', err)
        self.assertIn('_2026_plan', err)
        folder.rmdir()
        for name in ('sprint_tasks', 'needs', 'reach', 'sqlite_reserved'):
            folder = self.root / ('collection.' + name)
            folder.mkdir()
            err = self.cli('query', 'sprint-tasks', ok=False)[1]
            self.assertIn(name, err)
            if name == 'sprint_tasks':
                self.assertIn('sprint-tasks', err)
            folder.rmdir()
        for fields in ('- assessed-on: x\n- assessed_on: y\n', '- assessed-on: x\n- ASSESSED_ON: y\n'):
            self.put('sprint-tasks/A', '# A\n' + fields)
            err = self.cli('query', 'sprint-tasks', ok=False)[1]
            self.assertIn('collision', err)
            self.assertIn('assessed-on', err)
            self.assertIn('assessed_on' if 'assessed_on' in fields else 'ASSESSED_ON', err)
        self.put('sprint-tasks/A', '# A\n- needs: \n- tags: #tag\n- source: unknown\n- reach: x\n- sqlite_reserved: y\n')
        self.assertEqual(self.rows('query', 'sprint-tasks', 'SELECT needs,tags,source,reach,sqlite_reserved FROM sprint_tasks')[0][1:], [['', '#tag', 'unknown', 'x', 'y']])
        _, err = self.cli('edit', 'sprint-tasks/A', ok=False)
        self.assertIn('invalid choice', err)

    def test_governed_refusals_include_format(self):
        self.put('jobs/A', '# A\n- priority: P1\n')
        self.assertIn("priority is governed: remove it from the header and prepend under ## History: - YYYY-MM-DD priority: VALUE — REASON; authority: REF[; assent: NAMES] (VALUE 'cleared' clears it)", self.core('check', ok=False))
        self.put('jobs/A', '# A\n\n## History\n- priority: P1\n')
        self.assertIn('malformed governed entry: - priority: P1 — expected: - YYYY-MM-DD field: value — reason; authority: ref[; assent: names]', self.core('check', ok=False))

    def test_docstring_examples(self):
        import shlex
        helper = self.root / 'tools/collection.py'
        helper.write_text(re.sub(r'^NUMERIC_FIELDS = .*$', "NUMERIC_FIELDS = {'tasks': {'benefit', 'cost'}}", helper.read_text(), flags=re.M))
        self.put('tasks/T-1', '# First\n- state: open\n- benefit: 6\n- cost: 2\n')
        self.put('tasks/T-2', '# Second\n- state: open\n- needs: T-1\n')
        help_text, _ = self.cli('--help')
        examples = [shlex.split(line.strip()) for line in help_text.splitlines() if line.startswith(('  query tasks ', '  graph tasks/'))]
        self.assertEqual(len(examples), 3)
        self.assertEqual(self.rows(*examples[0])[0][1:], [['T-1', '6', '2', '3']])
        self.assertEqual(self.rows(*examples[1])[0][1:], [['tasks/T-2', '1']])
        self.assertEqual(len(self.rows(*examples[2])[0]), 3)

    @unittest.skipUnless(sqlite3, "sqlite3 required")
    def test_removed_query_extras_are_unavailable(self):
        self.put("jobs/A", "# A\n- tags: #kept\n\n## Review\nBody.\n")
        for sql in ("SELECT _rev FROM jobs", "SELECT _age FROM jobs",
                    "SELECT day('2020-01-01')", "SELECT * FROM tags", "SELECT * FROM sections"):
            with self.subTest(sql=sql):
                self.cli("query", "jobs", sql, ok=False)
        self.assertEqual(self.rows("query", "jobs", "SELECT tags FROM jobs")[0][1:], [["#kept"]])
