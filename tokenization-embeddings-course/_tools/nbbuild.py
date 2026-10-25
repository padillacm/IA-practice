"""Helper para construir los notebooks del curso de forma reproducible.

Uso (desde un script build_XX.py):

    # ejecutar desde la raíz del repo: python <curso>/_tools/builders/build_05.py
    import sys; sys.path.insert(0, "<curso>/_tools")
    from nbbuild import Notebook
    path = "<curso>/05_slug/05_slug.ipynb"
    nb = Notebook("Módulo 05 · Título", colab_path=path)
    nb.md(nb.badge() + "\n# Módulo 05 · Título ...")
    nb.code("import numpy as np")
    nb.save(path)

`save` valida el notebook con nbformat y comprueba que cada celda de código
sea Python sintácticamente válido (las líneas que empiezan por `!` o `%`
se ignoran en la comprobación).
"""
from __future__ import annotations

import ast
import textwrap

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

REPO = "padillacm/IA-practice"  # ajustar al crear el curso
BRANCH = "master"  # rama POR DEFECTO del remoto (main/master): el badge funciona tras el merge


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

    def gemini(
        self,
        kind: str,
        asset_id: str,
        title: str,
        shows: str,
        prompt: str,
        alt: str,
        placeholder: str,
        fmt: str | None = None,
        duration: str | None = None,
    ) -> None:
        """Celda markdown que el usuario reemplazará por una imagen/video generado con Gemini.

        kind: "imagen" | "video". asset_id: "M04-IMG-02" / "M04-VID-01" (único en el curso).
        shows: qué debe mostrar el recurso y por qué está en la lección.
        prompt: prompt COMPLETO y autocontenido (estilo visual, composición, textos exactos
            que deben aparecer, idioma de las etiquetas). Se copia tal cual en Gemini.
        placeholder: diagrama ASCII/texto que se ve mientras no se reemplace.
        fmt: formato (p. ej. "PNG 16:9, 1920x1080"); por defecto según el tipo.
        duration: solo video (p. ej. "20-30 s"), con el guion por escenas dentro del prompt.
        """
        if kind not in ("imagen", "video"):
            raise ValueError("kind debe ser 'imagen' o 'video'")
        want = "VID" if kind == "video" else "IMG"
        if f"-{want}-" not in asset_id:
            raise ValueError(f"asset_id {asset_id!r} no corresponde a kind={kind!r}")
        tag = "🎬 GEMINI-VIDEO" if kind == "video" else "🎨 GEMINI-IMAGEN"
        fmt = fmt or ("MP4 16:9, 1080p" if kind == "video" else "PNG 16:9, 1920x1080")
        ext = "mp4" if kind == "video" else "png"
        dur = f" | Duración: {duration}" if duration else ""
        ins = (
            f"![{alt}](assets/{asset_id}.{ext})"
            if kind == "imagen"
            else f'<video src="assets/{asset_id}.{ext}" controls width="100%"></video>'
        )
        lines = [
            f"> ### {tag} · ID: `{asset_id}` · ⚠️ REEMPLAZAR ESTA CELDA",
            f"> **{title}**",
            ">",
            f"> **Qué muestra:** {shows}",
            f"> **Formato:** {fmt}{dur} | **Texto alternativo:** {alt}",
            ">",
            "> **Prompt para Gemini (copiar y pegar):**",
            "> ```text",
            *[f"> {ln}" for ln in textwrap.dedent(prompt).strip().splitlines()],
            "> ```",
            ">",
            f"> **Cómo insertarlo:** guarda el archivo como `assets/{asset_id}.{ext}` en la carpeta del "
            f"módulo y reemplaza esta celda por: `{ins}`",
            ">",
            "> **Mientras tanto (placeholder):**",
            "> ```text",
            *[f"> {ln}" for ln in textwrap.dedent(placeholder).strip("\n").splitlines()],
            "> ```",
        ]
        self.md("\n".join(lines))

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
