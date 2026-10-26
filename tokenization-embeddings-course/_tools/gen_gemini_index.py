"""Genera extras/GEMINI_ASSETS.md escaneando las celdas 🎨/🎬 de todos los notebooks.

    python tokenization-embeddings-course/_tools/gen_gemini_index.py

Estado: una celda sigue "pendiente" mientras contenga la marca "REEMPLAZAR ESTA CELDA"; si el
usuario la reemplazó por la imagen/video, aparece como "hecho" (el ID ya no está en la lección
como celda Gemini pero sí existe assets/<ID>.png|mp4).
"""
from __future__ import annotations

import pathlib
import re
import sys

import nbformat

ROOT = pathlib.Path(__file__).resolve().parents[1]
CELL_RE = re.compile(r"GEMINI-(IMAGEN|VIDEO) · ID: `([A-Z0-9-]+)`")
TITLE_RE = re.compile(r"^> \*\*(.+?)\*\*$", re.M)
FMT_RE = re.compile(r"\*\*Formato:\*\* (.+?) \| \*\*Texto alternativo")
PROMPT_RE = re.compile(r"\*\*Prompt para Gemini \(copiar y pegar\):\*\*\n> ```text\n(.*?)\n> ```", re.S)


def scan() -> list[dict]:
    rows = []
    for nb_path in sorted(ROOT.glob("[0-9][0-9]_*/*.ipynb")):
        nb = nbformat.read(nb_path, as_version=4)
        for cell in nb.cells:
            if cell.cell_type != "markdown":
                continue
            m = CELL_RE.search(cell.source)
            if not m:
                continue
            title = TITLE_RE.search(cell.source)
            fmt = FMT_RE.search(cell.source)
            prompt = PROMPT_RE.search(cell.source)
            rows.append(
                {
                    "id": m.group(2),
                    "kind": m.group(1).lower(),
                    "module": nb_path.parent.name,
                    "notebook": nb_path.name,
                    "title": title.group(1) if title else "",
                    "fmt": fmt.group(1) if fmt else "",
                    "prompt": "\n".join(ln[2:] for ln in prompt.group(1).splitlines()) if prompt else "",
                    "pending": "REEMPLAZAR ESTA CELDA" in cell.source,
                }
            )
    return rows


def main() -> int:
    rows = scan()
    ids = [r["id"] for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    out = ["# Recursos para Gemini (imágenes y videos)", ""]
    out.append(
        "Índice generado por `_tools/gen_gemini_index.py`. Cada recurso es una celda 🎨/🎬 de una lección que "
        "debes **reemplazar** por la imagen/video generado con Gemini. Guarda el archivo como "
        "`<módulo>/assets/<ID>.png|mp4` y sustituye la celda por la línea indicada en ella."
    )
    out.append("")
    if dup:
        out.append(f"> ⚠️ IDs duplicados: {', '.join(dup)}")
        out.append("")
    n_img = sum(r["kind"] == "imagen" for r in rows)
    n_vid = sum(r["kind"] == "video" for r in rows)
    out.append(f"**Total:** {len(rows)} recursos ({n_img} imágenes, {n_vid} videos).")
    out.append("")
    out.append("| ID | Tipo | Módulo | Título | Formato | Estado |")
    out.append("|---|---|---|---|---|---|")
    for r in rows:
        estado = "⏳ pendiente" if r["pending"] else "✅ hecho"
        out.append(f"| `{r['id']}` | {r['kind']} | {r['module']} | {r['title']} | {r['fmt']} | {estado} |")
    out.append("")
    cur = None
    for r in rows:
        if r["module"] != cur:
            cur = r["module"]
            out += [f"## {cur}", ""]
        out += [
            f"### `{r['id']}` · {r['title']}",
            f"*{r['notebook']}* · {r['kind']} · {r['fmt']}",
            "",
            "```text",
            r["prompt"],
            "```",
            "",
        ]
    dest = ROOT / "extras" / "GEMINI_ASSETS.md"
    dest.parent.mkdir(exist_ok=True)
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"OK {dest.relative_to(ROOT.parent)}: {len(rows)} recursos ({n_img} imágenes, {n_vid} videos)")
    return 1 if dup else 0


if __name__ == "__main__":
    sys.exit(main())
