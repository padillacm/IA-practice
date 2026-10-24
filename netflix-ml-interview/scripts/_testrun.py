"""Run unittest suites in a subprocess and summarize them (stdlib only).

Always uses ``sys.executable`` (Windows-portable). The child prints one JSON result
line so output of the code under test cannot confuse parsing.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

MARK = "@@SIMRESULT@@"

_RUNNER = r"""
import json, sys, unittest
mode, target = sys.argv[1], sys.argv[2]
sys.path.insert(0, ".")
loader = unittest.TestLoader()
suite = loader.discover(".") if mode == "discover" else loader.loadTestsFromName(target)
res = unittest.TestResult()
suite.run(res)
def name(t):
    return t.id().rsplit(".", 1)[-1] if "_FailedTest" not in t.id() else "import_error:" + str(t)
failing = [name(t) for t, _ in res.failures + res.errors]
print("@@SIMRESULT@@" + json.dumps({"total": res.testsRun, "failing": failing,
      "skipped": len(res.skipped),
      "detail": [tb[-400:] for _, tb in (res.failures + res.errors)][:3]}))
"""


def run_unittest(workdir, mode: str = "discover", target: str = "", timeout: int = 60) -> dict:
    """Run tests in ``workdir``; mode 'discover' or 'module' (target = dotted name)."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
    try:
        proc = subprocess.run([sys.executable, "-c", _RUNNER, mode, target], cwd=str(workdir),
                              capture_output=True, text=True, timeout=timeout, env=env,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return _result(error=f"timeout after {timeout}s")
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(MARK):
            data = json.loads(line[len(MARK):])
            passed = data["total"] - len(data["failing"])
            return _result(total=data["total"], passed=passed, failing=data["failing"],
                           detail=data["detail"], skipped=data["skipped"])
    return _result(error=(proc.stderr or proc.stdout or "no output")[-600:])


def _result(total=0, passed=0, failing=None, detail=None, skipped=0, error=None) -> dict:
    return {"total": total, "passed": passed, "failing": failing or [], "detail": detail or [],
            "skipped": skipped, "error": error}


def format_result(res: dict, label: str = "tests") -> str:
    """Render e.g. '[tests: 7/8 passed; failing: test_ties]'."""
    if res["error"]:
        return f"[{label}: error - {res['error'].strip().splitlines()[-1][:160]}]"
    text = f"{label}: {res['passed']}/{res['total']} passed"
    if res["failing"]:
        text += "; failing: " + ", ".join(res["failing"])
    return f"[{text}]"


def copy_tree(src, dst) -> None:
    """Copy a directory tree, skipping caches."""
    shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))


def run_in_scratch(files: dict, base=None, timeout: int = 60, mode: str = "discover", target: str = "") -> dict:
    """Run tests in a scratch dir populated from {name: Path|str}; ``base`` is copied first."""
    with tempfile.TemporaryDirectory(prefix="sim-tests-") as tmp:
        if base is not None and Path(base).is_dir():
            copy_tree(base, tmp)
        for name, src in files.items():
            dest = Path(tmp) / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(src, Path):
                shutil.copyfile(src, dest)
            else:
                dest.write_text(src, encoding="utf-8")
        return run_unittest(tmp, mode, target, timeout)
