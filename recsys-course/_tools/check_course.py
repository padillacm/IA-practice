"""Revisión automática de todos los notebooks del curso.

    python recsys-course/_tools/check_course.py

Comprueba por módulo: que existan README, lección y proyecto; que cada
notebook sea válido y su código parsee; y que la lección tenga las secciones
obligatorias de la guía de estilo.
"""
from __future__ import annotations

import ast
import pathlib
import sys

import nbformat

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED_LESSON = ["Objetivos", "En producción", "Secretos de la élite", "Autoevaluación", "Referencias"]
REQUIRED_PROJECT = ["SPOILER", "TODO"]


def code_ok(src: str) -> bool:
    lines = ["" if ln.lstrip().startswith(("!", "%")) else ln for ln in src.splitlines()]
    try:
        ast.parse("\n".join(lines))
        return True
    except SyntaxError:
        return False


def main() -> int:
    problems: list[str] = []
    for mod in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name[:2].isdigit()):
        nbs = sorted(mod.glob("*.ipynb"))
        lesson = [p for p in nbs if "proyecto" not in p.name]
        project = [p for p in nbs if "proyecto" in p.name]
        if not (mod / "README.md").exists():
            problems.append(f"{mod.name}: falta README.md")
        if not lesson or not project:
            problems.append(f"{mod.name}: falta lección o proyecto")
        for nb_path in nbs:
            nb = nbformat.read(nb_path, as_version=4)
            nbformat.validate(nb)
            text = "\n".join(c.source for c in nb.cells)
            bad = [i for i, c in enumerate(nb.cells) if c.cell_type == "code" and not code_ok(c.source)]
            if bad:
                problems.append(f"{nb_path.name}: celdas con sintaxis inválida {bad}")
            required = REQUIRED_PROJECT if "proyecto" in nb_path.name else REQUIRED_LESSON
            missing = [s for s in required if s.lower() not in text.lower()]
            if missing:
                problems.append(f"{nb_path.name}: faltan secciones {missing}")
            if "colab.research.google.com" not in text:
                problems.append(f"{nb_path.name}: falta badge de Colab")
            n_code = sum(c.cell_type == "code" for c in nb.cells)
            print(f"{nb_path.relative_to(ROOT)}: {len(nb.cells)} celdas ({n_code} código)")
    print()
    if problems:
        print("PROBLEMAS:")
        for p in problems:
            print(" -", p)
        return 1
    print("Todo OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
