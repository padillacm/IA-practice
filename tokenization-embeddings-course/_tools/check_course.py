"""Revisión automática de todos los notebooks del curso.

    python <curso>/_tools/check_course.py

Ajusta REQUIRED_LESSON / REQUIRED_PROJECT si cambias la plantilla de STYLE_GUIDE.

Comprueba por módulo: que existan README, lección y proyecto; que cada
notebook sea válido y su código parsee; y que la lección tenga las secciones
obligatorias de la guía de estilo.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

import nbformat

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED_LESSON = [
    "Objetivos",
    "En producción",
    "Secretos de la élite",
    "Autoevaluación",
    "Referencias",
    "Qué debes observar",
    "Madurez",
]
REQUIRED_PROJECT = ["SPOILER", "TODO"]


MIN_GEMINI_PER_LESSON = 3
GEMINI_RE = re.compile(r"GEMINI-(IMAGEN|VIDEO) · ID: `([A-Z0-9-]+)`")
seen_gemini_ids: set[str] = set()


def check_gemini(nb_path: pathlib.Path, nb, is_lesson: bool, problems: list[str]) -> None:
    """Valida celdas 🎨/🎬: mínimo por lección, ID único con prefijo del módulo, prompt y placeholder."""
    mod_num = nb_path.parent.name[:2]
    cells = [c for c in nb.cells if c.cell_type == "markdown" and GEMINI_RE.search(c.source)]
    if is_lesson and len(cells) < MIN_GEMINI_PER_LESSON:
        problems.append(f"{nb_path.name}: {len(cells)} celdas Gemini (mínimo {MIN_GEMINI_PER_LESSON})")
    for c in cells:
        kind, gid = GEMINI_RE.search(c.source).groups()
        if gid in seen_gemini_ids:
            problems.append(f"{nb_path.name}: ID Gemini duplicado {gid}")
        seen_gemini_ids.add(gid)
        if not gid.startswith(f"M{mod_num}-"):
            problems.append(f"{nb_path.name}: ID {gid} no empieza por M{mod_num}-")
        if "Prompt para Gemini" not in c.source or "placeholder" not in c.source:
            problems.append(f"{nb_path.name}: celda Gemini {gid} sin prompt o placeholder")


def code_ok(src: str) -> bool:
    lines = ["" if ln.lstrip().startswith(("!", "%")) else ln for ln in src.splitlines()]
    try:
        ast.parse("\n".join(lines))
        return True
    except SyntaxError:
        return False


def main() -> int:
    problems: list[str] = []
    modules = sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name[:2].isdigit())
    if not modules:
        problems.append(f"no hay módulos NN_slug/ en {ROOT}")
    for mod in modules:
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
            low = text.lower()
            missing = [s for s in required if s.lower() not in low]
            if missing:
                problems.append(f"{nb_path.name}: faltan secciones {missing}")
            if "colab.research.google.com" not in text:
                problems.append(f"{nb_path.name}: falta badge de Colab")
            elif "<owner>/<repo>" in text:
                problems.append(f"{nb_path.name}: badge sin configurar (ajusta REPO en nbbuild.py)")
            check_gemini(nb_path, nb, "proyecto" not in nb_path.name, problems)
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
