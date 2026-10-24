"""Test helper: builds a complete, VALID simulator content tree in a temp directory.

The real catalog.yaml, templates and sources.md are copied; stage content (brief,
questions, rubric, problems, repos, take-homes, agents, study map) is generated from the
catalog so tests can break one thing at a time.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import _yamlish as yamlish

KB = Path(__file__).resolve().parent.parent
ROLES = ("mle", "rs", "ds")
MEMO = ["candor", "judgment", "courage"]
OPUS = {"netflix-ml-system-design", "netflix-hm-onsite", "netflix-evaluator", "netflix-hm-debrief"}


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def load_catalog() -> dict:
    return yamlish.loads((KB / "catalog.yaml").read_text(encoding="utf-8"))


def question_md(qid: str, variant: str, kind: str = "main", domain: str = "any") -> str:
    meta = {"roles": list(ROLES), "levels": ["L4", "L5", "L6"], "variant": variant, "domain": domain,
            "kind": kind, "signal_points": [f"signal {qid} a", f"signal {qid} b"]}
    return f"### {qid}\n\n```yaml\n{yamlish.dumps(meta)}```\n\nStatement of {qid}. What would you do?\n\nFollow-up: why?\n\n"


def stage_questions(stage: dict) -> str:
    variants = [v["id"] for v in stage["variants"]] or ["default"]
    out = "# Questions\n\n"
    for v in variants:
        out += question_md(f"{v}-q1", v) + question_md(f"{v}-q2", v)
        out += question_md(f"{v}-q3", v, domain="recsys")
    if stage["id"] != "culture":
        out += question_md("probe-1", variants[0], kind="culture")
    return out


def rubric_md(stage: dict) -> str:
    out = (f"---\nstage: {stage['id']}\nrubric_version: 1\n---\n\n# Rubric\n\n"
           "Strong No: contradicts the Yes bar or has serious errors. No: does not reach the bar. "
           "Strong Yes: reaches the bar of the next level.\n\n")
    for c in stage["competencies"]:
        out += f"## {c['id']}\n\ncore: {'true' if c['core'] else 'false'}\n"
        if c["id"].startswith("culture"):
            out += f"memo_values: [{', '.join(MEMO)}]\n"
        out += ("\n| Level | Yes bar |\n|---|---|\n"
                f"| L4 | Names one concrete case for {c['id']} and states its result |\n"
                f"| L5 | Compares two options for {c['id']} and quantifies the trade-off |\n"
                f"| L6 | Sets cross-team direction for {c['id']} and measures its outcome |\n\n")
    return out


def agent_md(name: str, **over) -> str:
    fm = {"name": name, "description": f"Agent {name}. Use for tests.", "tools": "Read, Glob, Grep",
          "model": "opus" if name in OPUS else "sonnet"}
    fm.update(over)
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + f"---\n\nBody of {name}.\n"


SETTINGS = ('{"permissions": {"allow": ["Bash(python netflix-ml-interview/scripts/sim.py:*)", '
            '"Bash(python3 netflix-ml-interview/scripts/sim.py:*)", "Bash(py netflix-ml-interview/scripts/sim.py:*)"]}}\n')
PROBLEM_TESTS = ("import unittest\nfrom solution import add\n\n\nclass T(unittest.TestCase):\n"
                 "    def test_add(self):\n        self.assertEqual(add(1, 2), 3)\n\n"
                 "    def test_neg(self):\n        self.assertEqual(add(-1, 1), 0)\n")


def add_problem(stage_dir: Path, pid: str, variant: str, roles=ROLES) -> Path:
    d = stage_dir / "problems" / pid
    meta = {"variant": variant, "roles": list(roles), "levels": ["L4", "L5", "L6"]}
    write(d / "problem.md", "---\n" + yamlish.dumps(meta) + "---\n\n# Problem\n\nImplement add(a, b).\n")
    write(d / "starter.py", "def add(a, b):\n    raise NotImplementedError\n")
    write(d / "tests.py", PROBLEM_TESTS)
    write(d / "reference.py", "def add(a, b):\n    return a + b\n")
    write(d / "followups.md", "# Follow-ups\n\nHow does it scale? What if called from many threads (concurrency)?\n")
    return d


def add_repo(stage_dir: Path, rid: str, n_flaws: int) -> Path:
    d = stage_dir / "repos" / rid
    write(d / "workspace" / "lib.py", "def double(x):\n    return x * 2\n")
    write(d / "workspace" / "test_lib.py", "import unittest\nfrom lib import double\n\n\nclass T(unittest.TestCase):\n"
          "    def test_double(self):\n        self.assertEqual(double(2), 4)\n")
    write(d / "tasks.md", "# Tasks\n\nAdd triple().\n")
    write(d / "notes.md", "# Notes\n\nInterviewer notes.\n")
    flaws = []
    for i in range(n_flaws):
        fid = f"flaw{i + 1}"
        write(d / "hidden" / f"test_{fid}.py", "import unittest\nfrom lib import double\n\n\nclass H(unittest.TestCase):\n"
              "    def test_hidden(self):\n        self.assertEqual(double(0), 0)\n")
        flaws.append({"id": fid, "zone": "lib.py", "trigger_keywords": ["double", "triple"],
                      "description": "AI returns wrong value", "hidden_test": f"hidden/test_{fid}.py"})
    write(d / "flaws.yaml", yamlish.dumps({"flaws": flaws}))
    return d


def add_takehome(stage_dir: Path, tid: str, deterministic: bool = True) -> Path:
    d = stage_dir / "takehomes" / tid
    write(d / "prompt.md", "# Take-home\n\nAnalyze the dataset.\n")
    body = ("import random, sys, pathlib\nout = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')\n"
            + ("random.seed(7)\n" if deterministic else "random.seed()\n")
            + "(out / 'data.csv').write_text('\\n'.join(str(random.random()) for _ in range(5)))\n")
    write(d / "generate_data.py", body)
    return d


def build_tree(root: Path, with_git: bool = False) -> Path:
    """Create a valid repo layout under ``root`` and return the repo root."""
    root = Path(root)
    kb = root / "netflix-ml-interview"
    cat = load_catalog()
    kb.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(KB / "catalog.yaml", kb / "catalog.yaml")
    shutil.copytree(KB / "templates", kb / "templates", dirs_exist_ok=True)
    shutil.copyfile(KB / "sources.md", kb / "sources.md")
    write(root / ".gitignore", "netflix-ml-interview/sessions/\n")
    write(root / ".claude" / "settings.json", SETTINGS)
    write(root / ".claude" / "skills" / "netflix-ml-interview" / "SKILL.md", "# Skill\n\nRun sim.py guard before writing.\n")
    for st in cat["stages"]:
        sd = kb / "stages" / st["id"]
        write(sd / "brief.md", f"# {st['id']}\n\nBrief.\n\n## Sources\n\n- [interviewing.io] guide\n")
        write(sd / "questions.md", stage_questions(st))
        write(sd / "rubric.md", rubric_md(st))
        write(root / ".claude" / "agents" / f"{st['agent']}.md", agent_md(st["agent"]))
    for name in ("netflix-evaluator", "netflix-hm-debrief", "netflix-ai-pair"):
        write(root / ".claude" / "agents" / f"{name}.md", agent_md(name))
    (root / "recsys-course" / "15_online_experimentation").mkdir(parents=True, exist_ok=True)
    study = {f"{s['id']}.{c['id']}": {"course": ["recsys-course/15_online_experimentation/"]}
             for s in cat["stages"] for c in s["competencies"]}
    write(kb / "study-map.yaml", yamlish.dumps(study))
    coding = kb / "stages" / "coding"
    for i, v in enumerate(("practical", "ml-coding", "sql-pandas", "lc-style", "practical", "practical")):
        add_problem(coding, f"p{i}-{v}", v)
    ts = kb / "stages" / "technical-screen"
    for v in ("ml-coding", "ml-framing-coding"):
        add_problem(ts, f"tp-{v}", v)
    write(ts / "datasets" / "movies.sql", "CREATE TABLE t(x INT); INSERT INTO t VALUES (1),(2);\n")
    write(ts / "prs" / "pr1" / "pr.diff", "--- a/x\n+++ b/x\n")
    ai = kb / "stages" / "ai-assisted-coding"
    for n in range(3):
        add_repo(ai, f"repo{n}", n)
    for t in ("th1", "th2"):
        add_takehome(kb / "stages" / "presentation", t)
    if with_git:
        git_init(root)
    return root


def git_init(root: Path) -> None:
    for cmd in (["init", "-q"], ["config", "user.email", "t@example.com"], ["config", "user.name", "t"]):
        subprocess.run(["git", *cmd], cwd=str(root), check=True, capture_output=True)
