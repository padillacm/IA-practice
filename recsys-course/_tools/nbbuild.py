"""Helper para construir los notebooks del curso de forma reproducible.

Uso (desde un script build_XX.py):

    import sys; sys.path.insert(0, "recsys-course/_tools")
    from nbbuild import Notebook
    nb = Notebook("Módulo 05 · Factorización Matricial", colab_path="recsys-course/05_matrix_factorization/05_matrix_factorization.ipynb")
    nb.md("# Título ...")
    nb.code("import numpy as np")
    nb.save("recsys-course/05_matrix_factorization/05_matrix_factorization.ipynb")

`save` valida el notebook con nbformat y comprueba que cada celda de código
sea Python sintácticamente válido (las líneas que empiezan por `!` o `%`
se ignoran en la comprobación).
"""
from __future__ import annotations

import ast
import textwrap

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

REPO = "padillacm/IA-practice"
BRANCH = "master"


def colab_badge(path: str) -> str:
    url = f"https://colab.research.google.com/github/{REPO}/blob/{BRANCH}/{path}"
    return f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)]({url})"


class Notebook:
    def __init__(self, title: str, colab_path: str, gpu: bool = False):
        self.nb = new_notebook()
        self.nb.metadata = {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "colab": {"provenance": [], "name": title},
            "accelerator": "GPU" if gpu else "None",
        }
        if gpu:
            self.nb.metadata["colab"]["gpuType"] = "T4"
        self.colab_path = colab_path

    def md(self, text: str) -> None:
        self.nb.cells.append(new_markdown_cell(textwrap.dedent(text).strip("\n")))

    def code(self, src: str) -> None:
        self.nb.cells.append(new_code_cell(textwrap.dedent(src).strip("\n")))

    def badge(self) -> str:
        return colab_badge(self.colab_path)

    def _check(self) -> None:
        for i, cell in enumerate(self.nb.cells):
            if cell.cell_type != "code":
                continue
            lines = [
                "" if ln.lstrip().startswith(("!", "%")) else ln
                for ln in cell.source.splitlines()
            ]
            try:
                ast.parse("\n".join(lines))
            except SyntaxError as e:
                raise SyntaxError(f"Celda {i} inválida: {e}\n---\n{cell.source[:500]}") from e

    def save(self, path: str) -> None:
        self._check()
        nbformat.validate(self.nb)
        nbformat.write(self.nb, path)
        n_code = sum(c.cell_type == "code" for c in self.nb.cells)
        n_md = len(self.nb.cells) - n_code
        print(f"OK {path}: {n_md} markdown + {n_code} código")
