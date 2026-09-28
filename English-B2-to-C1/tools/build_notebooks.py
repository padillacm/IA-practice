"""Builds the study notebooks and the answer-key JSON files.

Content lives in tools/content/*.py. Each module defines NOTEBOOK = {
    "file": "01_....ipynb", "title": "...", "cells": [ ... ] }
where a cell is ("md", text), ("code", text) or ("ex", exercise_dict).

Run from anywhere:  python tools/build_notebooks.py
"""

import importlib
import json
import random
import sys
import zlib
from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

SETUP = '''# Run this cell first: it loads the helper toolkit (english_tools.py)
import sys, pathlib
for _p in [pathlib.Path.cwd(), *pathlib.Path.cwd().parents]:
    if (_p / "english_tools.py").exists():
        sys.path.insert(0, str(_p)); break
from english_tools import *'''


def _gap(text):
    return text.replace("______", "\\_\\_\\_\\_\\_\\_")


def _prepare(ex):
    """Shuffle multiple-choice options deterministically and fix answers."""
    ex = json.loads(json.dumps(ex))
    for i, item in enumerate(ex["items"]):
        if "options" in item:
            correct = item["options"][0]
            rng = random.Random(zlib.crc32(f"{ex['id']}-{i}".encode()))
            opts = item["options"][:]
            rng.shuffle(opts)
            item["options"] = opts
            letter = "abcd"[opts.index(correct)]
            item["a"] = [letter, correct, f"{letter}) {correct}"]
        elif isinstance(item["a"], str):
            item["a"] = [item["a"]]
    return ex


def _render_ex(ex):
    lines = [f"### Exercise {ex['id']} - {ex['title']}", "", _gap(ex["instructions"]), ""]
    for n, item in enumerate(ex["items"], 1):
        q = _gap(item["q"]).replace("\n", "  \n&nbsp;&nbsp;&nbsp;&nbsp;")
        lines.append(f"{n}. {q}")
        if "options" in item:
            lines.append("   " + " &nbsp; ".join(f"**{l})** {o}" for l, o in zip("abcd", item["options"])))
    md = "\n".join(lines)
    code = ["answers = {"]
    for n, item in enumerate(ex["items"], 1):
        hint = item["q"].split("\n")[-1] if "\n" in item["q"] else item["q"]
        hint = hint.replace('"', "'")
        hint = hint if len(hint) <= 60 else hint[:57] + "..."
        code.append(f'    {n}: "",   # {hint}')
    code.append("}")
    code.append(f'check("{ex["id"]}", answers)')
    return new_markdown_cell(md), new_code_cell("\n".join(code))


def build(module_name):
    mod = importlib.import_module(f"content.{module_name}")
    spec = mod.NOTEBOOK
    nb = new_notebook()
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    cells = [new_markdown_cell(f"# {spec['title']}"), new_code_cell(SETUP)]
    keys = []
    for kind, payload in spec["cells"]:
        if kind == "md":
            cells.append(new_markdown_cell(payload.strip("\n")))
        elif kind == "code":
            cells.append(new_code_cell(payload.strip("\n")))
        elif kind == "ex":
            ex = _prepare(payload)
            keys.append(ex)
            cells.extend(_render_ex(ex))
        else:
            raise ValueError(kind)
    nb.cells = cells
    out = ROOT / "notebooks" / spec["file"]
    out.parent.mkdir(exist_ok=True)
    nbformat.write(nb, str(out))
    if keys:
        key_file = ROOT / "data" / "exercises" / (Path(spec["file"]).stem + ".json")
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_text(json.dumps(keys, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"built {out.name}: {len(cells)} cells, {len(keys)} exercise sets")


if __name__ == "__main__":
    modules = sorted(p.stem for p in (ROOT / "tools" / "content").glob("nb*.py"))
    for m in modules:
        build(m)
