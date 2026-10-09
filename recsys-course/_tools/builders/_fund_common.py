"""Utilidades compartidas por los builders del Bloque I (módulos 00, 01, 02)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # recsys-course/
sys.path.insert(0, str(ROOT / "_tools"))
from nbbuild import Notebook  # noqa: E402

RAW = "https://raw.githubusercontent.com/padillacm/IA-practice/master/recsys-course"
MODULE_FILES = {
    "cinematch_data.py": "01_data/cinematch_data.py",
    "cinematch_eval.py": "02_evaluation/cinematch_eval.py",
}


def module_source(fname: str) -> str:
    return (ROOT / MODULE_FILES[fname]).read_text(encoding="utf-8")


def utils_cell(nb: Notebook, fnames: list[str]) -> None:
    """Celda (oculta como formulario en Colab) que escribe los módulos del curso
    en el directorio de trabajo. Lleva una copia embebida para no depender de la
    red; si prefieres la última versión del repo, descarga desde RAW."""
    lines = [
        '#@title 🔧 Utilidades del curso: ' + ", ".join(fnames) + ' { display-mode: "form" }',
        "# Escribe los módulos reutilizables del curso en el directorio actual.",
        "# Última versión en GitHub (alternativa):",
    ]
    for f in fnames:
        lines.append(f"#   !wget -q {RAW}/{MODULE_FILES[f]}")
    lines.append("_SOURCES = {}")
    for f in fnames:
        lines.append(f"_SOURCES[{f!r}] = {module_source(f)!r}")
    lines += [
        "for _name, _src in _SOURCES.items():",
        "    with open(_name, 'w', encoding='utf-8') as _fh:",
        "        _fh.write(_src)",
        "    print('✔ escrito', _name)",
    ]
    nb.code("\n".join(lines))


def writefile_chunks(nb: Notebook, fname: str, max_lines: int = 70) -> int:
    """Escribe el módulo canónico con celdas %%writefile / %%writefile -a,
    troceado en fronteras de sección (líneas '# ----') o de funciones top-level."""
    src = module_source(fname).rstrip("\n").split("\n")
    # puntos de corte candidatos: inicio de función/clase top-level o separador
    cuts = [i for i, ln in enumerate(src) if re.match(r"^(def |class |# -{10,})", ln)]
    chunks, start = [], 0
    while start < len(src):
        end = len(src)
        if end - start > max_lines:
            cands = [c for c in cuts if start < c <= start + max_lines]
            if cands:
                end = cands[-1]
                # no separar el separador '# ----' de su título
                while end - 1 > start and src[end - 1].startswith("# "):
                    end -= 1
        chunks.append(src[start:end])
        start = end
    for j, ch in enumerate(chunks):
        magic = f"%%writefile {fname}" if j == 0 else f"%%writefile -a {fname}"
        body = "\n".join(ch).strip("\n")
        if j > 0:
            body = "\n\n" + body
        nb.nb.cells.append(__import__("nbformat").v4.new_code_cell(magic + "\n" + body))
    return len(chunks)
