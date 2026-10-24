"""Tests for check_simulator.py using temporary fixture trees (pass and fail cases)."""
import io
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _fixtures as fx  # noqa: E402
import _yamlish as yamlish  # noqa: E402
import check_simulator as chk  # noqa: E402


class TreeCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        fx.build_tree(self.root)
        self.kb = self.root / "netflix-ml-interview"

    def tearDown(self):
        self._tmp.cleanup()

    def run_checks(self, only=None, stage=None):
        return chk.run(chk.Env(self.root), only, stage)

    def assertFails(self, check, fragment, **kw):
        rep = self.run_checks(only=check, **kw)
        joined = "\n".join(rep.errors.get(check, []))
        self.assertIn(fragment, joined, f"errors were: {joined or 'none'}")

    def edit(self, rel, fn):
        p = self.root / rel
        p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")


class ValidTree(TreeCase):
    def test_all_checks_pass_on_valid_tree(self):
        rep = self.run_checks()
        self.assertTrue(rep.ok, chk.render(rep))
        self.assertEqual(len(rep.ran), 16)

    def test_real_catalog_is_valid(self):
        real = chk.Env(fx.KB.parent)
        rep = chk.run(real, only="catalog")
        self.assertTrue(rep.ok, chk.render(rep))

    def test_stage_filter_only_runs_that_stage(self):
        self.edit("netflix-ml-interview/stages/hm-screen/rubric.md", lambda t: "broken")
        self.assertTrue(self.run_checks(stage="coding").ok)
        self.assertFalse(self.run_checks(stage="hm-screen").ok)

    def test_main_returns_nonzero_on_failure_and_zero_on_success(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(chk.main(["--root", str(self.root)]), 0)
            (self.root / ".gitignore").unlink()
            self.assertEqual(chk.main(["--root", str(self.root)]), 1)
        self.assertIn("[FAIL] gitignore", buf.getvalue())


class CatalogChecks(TreeCase):
    def mutate(self, fn):
        p = self.kb / "catalog.yaml"
        cat = yamlish.loads(p.read_text(encoding="utf-8"))
        fn(cat)
        p.write_text(yamlish.dumps(cat), encoding="utf-8")

    def test_missing_stage(self):
        self.mutate(lambda c: c["stages"].pop())
        self.assertFails("catalog", "exactly the 14 catalog stages")

    def test_loop_entry_unknown_variant(self):
        self.mutate(lambda c: c["roles"]["mle"]["loop"]["vo1"].__setitem__(0, "coding@foo"))
        self.assertFails("catalog", "variant that does not exist")

    def test_loop_entry_incompatible_with_role(self):
        self.mutate(lambda c: c["roles"]["mle"]["loop"]["vo1"].__setitem__(0, "coding@sql-pandas"))
        self.assertFails("catalog", "not compatible with role mle")

    def test_loop_entry_without_weight(self):
        self.mutate(lambda c: c["roles"]["mle"]["weights"].pop("ml-system-design"))
        self.assertFails("catalog", "has no weight")

    def test_competency_without_core(self):
        def drop_core(c):
            for comp in c["stages"][0]["competencies"]:
                comp["core"] = False
        self.mutate(drop_core)
        self.assertFails("catalog", "at least one competency must be core")

    def test_missing_catalog_file(self):
        (self.kb / "catalog.yaml").unlink()
        self.assertFails("catalog", "file is missing")


class StageContentChecks(TreeCase):
    def test_missing_brief_questions_rubric_are_reported(self):
        for name in ("brief.md", "questions.md", "rubric.md"):
            (self.kb / "stages" / "culture" / name).unlink()
        for check, name in (("brief", "brief.md"), ("questions", "questions.md"), ("rubric", "rubric.md")):
            self.assertFails(check, f"{name} is missing", stage="culture")

    def test_brief_without_sources(self):
        self.edit("netflix-ml-interview/stages/culture/brief.md", lambda t: t.split("## Sources")[0])
        self.assertFails("brief", "Sources")

    def test_too_few_main_questions(self):
        self.edit("netflix-ml-interview/stages/culture/questions.md", lambda t: t.replace("kind: main", "kind: followup", 2))
        self.assertFails("questions", ">= 2 'main' questions")

    def test_question_with_bad_variant(self):
        self.edit("netflix-ml-interview/stages/coding/questions.md", lambda t: t.replace("variant: practical", "variant: nope", 1))
        self.assertFails("questions", "variant 'nope' invalid")

    def test_rubric_vague_adjective(self):
        self.edit("netflix-ml-interview/stages/culture/rubric.md", lambda t: t.replace("Names one concrete case", "Gives a good case", 1))
        self.assertFails("rubric", "vague adjectives")

    def test_rubric_identical_bars(self):
        def same(t):
            return re.sub(r"\| (L[456]) \|[^\n]*", r"| \1 | Names one concrete case |", t)
        self.edit("netflix-ml-interview/stages/culture/rubric.md", same)
        self.assertFails("rubric", "must differ")

    def test_rubric_culture_without_memo_values(self):
        self.edit("netflix-ml-interview/stages/culture/rubric.md", lambda t: t.replace("memo_values:", "values:"))
        self.assertFails("rubric", "memo_values")

    def test_rubric_ids_must_match_catalog(self):
        self.edit("netflix-ml-interview/stages/culture/rubric.md", lambda t: t.replace("## candidate_questions", "## extra_one"))
        self.assertFails("rubric", "differ from the catalog")

    def test_rubric_without_version(self):
        self.edit("netflix-ml-interview/stages/culture/rubric.md", lambda t: t.replace("rubric_version: 1\n", ""))
        self.assertFails("rubric", "rubric_version")

    def test_empty_tree_reports_missing_content_without_crashing(self):
        empty = Path(tempfile.mkdtemp())
        (empty / "netflix-ml-interview").mkdir()
        import shutil
        shutil.copyfile(fx.KB / "catalog.yaml", empty / "netflix-ml-interview" / "catalog.yaml")
        rep = chk.run(chk.Env(empty))
        self.assertFalse(rep.ok)
        for check in ("brief", "questions", "rubric", "agents", "gitignore", "settings", "skill", "studymap"):
            self.assertIn(check, rep.errors)


class AgentChecks(TreeCase):
    def agent(self, name):
        return f".claude/agents/{name}.md"

    def test_name_must_match_file(self):
        self.edit(self.agent("netflix-culture"), lambda t: t.replace("name: netflix-culture", "name: other"))
        self.assertFails("agents", "must equal the file name")

    def test_bash_tool_forbidden(self):
        self.edit(self.agent("netflix-coding"), lambda t: t.replace("Read, Glob, Grep", "Read, Bash"))
        self.assertFails("agents", "forbidden tools")

    def test_model_rules(self):
        self.edit(self.agent("netflix-ml-system-design"), lambda t: t.replace("model: opus", "model: sonnet"))
        self.assertFails("agents", "model must be opus")

    def test_missing_agent(self):
        (self.root / self.agent("netflix-evaluator")).unlink()
        self.assertFails("agents", "agent file is missing")

    def test_unexpected_agent(self):
        fx.write(self.root / self.agent("netflix-extra"), fx.agent_md("netflix-extra"))
        self.assertFails("agents", "unexpected agent")


class RepoFileChecks(TreeCase):
    def test_gitignore_entry_required(self):
        (self.root / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
        self.assertFails("gitignore", "missing entry")

    def test_settings_permissions_required(self):
        (self.root / ".claude" / "settings.json").write_text('{"permissions": {"allow": []}}', encoding="utf-8")
        self.assertFails("settings", "lacks")

    def test_skill_must_not_contain_git_write_commands(self):
        for bad in ("git add .", "git commit -m x", "git  push origin"):
            fx.write(self.root / ".claude/skills/netflix-ml-interview/SKILL.md", f"# Skill\n\nRun {bad}\n")
            self.assertFails("skill", "forbidden command")

    def test_skill_allows_disagree_then_commit(self):
        fx.write(self.root / ".claude/skills/netflix-ml-interview/SKILL.md", "# Skill\n\nDisagree then commit.\n")
        self.assertTrue(self.run_checks(only="skill").ok)

    def test_studymap_unknown_course_path(self):
        self.edit("netflix-ml-interview/study-map.yaml", lambda t: t.replace("15_online_experimentation", "99_nope", 1))
        self.assertFails("studymap", "course path does not exist")

    def test_studymap_missing_competency(self):
        self.edit("netflix-ml-interview/study-map.yaml", lambda t: "\n".join(t.split("\n")[:-3]) + "\n")
        self.assertFails("studymap", "no entry for")

    def test_sources_requires_sections(self):
        self.edit("netflix-ml-interview/sources.md", lambda t: t.replace("## coding\n", "## coding-x\n"))
        self.assertFails("sources", "no '## coding' section")

    def test_templates_missing(self):
        (self.kb / "templates" / "debrief.md").unlink()
        self.assertFails("templates", "file is missing")


class ExecutableContentChecks(TreeCase):
    def test_reference_failing_tests_is_reported(self):
        ref = self.kb / "stages/coding/problems/p0-practical/reference.py"
        ref.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
        self.assertFails("coding", "reference.py does not pass tests.py")

    def test_problem_missing_file(self):
        (self.kb / "stages/coding/problems/p0-practical/followups.md").unlink()
        self.assertFails("coding", "missing followups.md")

    def test_problem_missing_dependency_is_skipped_with_warning(self):
        p = self.kb / "stages/coding/problems/p0-practical/problem.md"
        p.write_text(p.read_text(encoding="utf-8").replace("variant:", "requires: [definitely_not_installed_pkg]\nvariant:", 1), encoding="utf-8")
        rep = self.run_checks(only="coding")
        self.assertTrue(rep.ok, chk.render(rep))
        self.assertTrue(any("definitely_not_installed_pkg" in w for w in rep.warnings))

    def test_ai_repo_failing_workspace_tests(self):
        t = self.kb / "stages/ai-assisted-coding/repos/repo0/workspace/test_lib.py"
        t.write_text(t.read_text(encoding="utf-8").replace("4)", "5)"), encoding="utf-8")
        self.assertFails("aicoding", "workspace tests must be green")

    def test_ai_hidden_test_that_fails_on_clean_workspace(self):
        h = self.kb / "stages/ai-assisted-coding/repos/repo1/hidden/test_flaw1.py"
        h.write_text(h.read_text(encoding="utf-8").replace("double(0), 0", "double(0), 1"), encoding="utf-8")
        self.assertFails("aicoding", "hidden_test must pass on the clean workspace")

    def test_ai_too_many_flaws(self):
        fx.add_repo(self.kb / "stages/ai-assisted-coding", "repo9", 3)
        self.assertFails("aicoding", "at most 2 flaws")

    def test_nondeterministic_takehome(self):
        fx.add_takehome(self.kb / "stages/presentation", "th3", deterministic=False)
        self.assertFails("takehomes", "not deterministic")

    def test_deterministic_takehomes_pass(self):
        self.assertTrue(self.run_checks(only="takehomes").ok)

    def test_bad_sql_dataset(self):
        fx.write(self.kb / "stages/technical-screen/datasets/bad.sql", "CREATE TABL nope;")
        self.assertFails("sql", "does not run on sqlite3")

    def test_declared_materials_must_exist(self):
        import shutil
        shutil.rmtree(self.kb / "stages/technical-screen/prs")
        self.assertFails("materials", "declares materials 'prs'")


if __name__ == "__main__":
    unittest.main(verbosity=1)
