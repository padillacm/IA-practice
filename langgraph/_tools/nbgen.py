"""Convierte ficheros fuente `.nbsrc` en notebooks Jupyter (.ipynb).

Formato del fichero fuente (sin ambigüedad de escapes, todo texto plano):

    #%%md
    ## Un título en markdown
    #%%py
    print("una celda de código")
    #%%raw
    (celda cruda, poco habitual)

Uso:  python nbgen.py <archivo.nbsrc> [...]   ->  escribe el .ipynb hermano
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

DELIM = re.compile(r"^#%%(md|py|raw)\s*$")


def parsear(texto: str) -> list[tuple[str, str]]:
    celdas: list[tuple[str, str]] = []
    tipo: str | None = None
    buf: list[str] = []

    def cerrar() -> None:
        if tipo is None:
            return
        cuerpo = "\n".join(buf).strip("\n")
        if cuerpo.strip():
            celdas.append((tipo, cuerpo))

    for linea in texto.splitlines():
        m = DELIM.match(linea)
        if m:
            cerrar()
            tipo, buf = m.group(1), []
        else:
            if tipo is None:
                if linea.strip():
                    raise ValueError(f"Contenido antes del primer #%%: {linea!r}")
                continue
            buf.append(linea)
    cerrar()
    return celdas


def a_notebook(celdas: list[tuple[str, str]]) -> dict:
    salida = []
    for i, (tipo, cuerpo) in enumerate(celdas):
        lineas = cuerpo.splitlines(keepends=True)
        base = {"id": f"c{i:03d}", "metadata": {}, "source": lineas}
        if tipo == "md":
            salida.append({"cell_type": "markdown", **base})
        elif tipo == "raw":
            salida.append({"cell_type": "raw", **base})
        else:
            salida.append({"cell_type": "code", "execution_count": None, "outputs": [], **base})
    return {
        "cells": salida,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {
                "name": "python",
                "version": "3.11",
                "mimetype": "text/x-python",
                "file_extension": ".py",
                "pygments_lexer": "ipython3",
                "nbconvert_exporter": "python",
                "codemirror_mode": {"name": "ipython", "version": 3},
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def convertir(origen: pathlib.Path, destino: pathlib.Path) -> int:
    celdas = parsear(origen.read_text(encoding="utf-8"))
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(a_notebook(celdas), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(celdas)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        src = pathlib.Path(arg)
        # _src/01_fundamentos/xxx.nbsrc  ->  01_fundamentos/xxx.ipynb
        rel = src.relative_to(src.parents[len(src.parents) - 1])
        partes = list(src.parts)
        partes = [p for p in partes if p != "_src"]
        dst = pathlib.Path(*partes).with_suffix(".ipynb")
        n = convertir(src, dst)
        print(f"[nbgen] {src} -> {dst}  ({n} celdas)")
