"""Valida los notebooks del curso sin ejecutarlos (no hacen falta claves de API).

Comprueba tres cosas, de menor a mayor valor:

1. Estructura del `.ipynb` (JSON, celdas, campos obligatorios).
2. Que **cada celda de código** compila (`ast.parse`), ignorando magias de IPython.
3. Que **cada símbolo importado existe de verdad** en el entorno instalado. Esta es
   la comprobación que importa: detecta APIs inventadas o renombradas entre versiones
   (`from langgraph.types import Foo` cuando `Foo` ya no existe).

Uso:
    python _tools/validar.py                 # todos los notebooks del curso
    python _tools/validar.py 01_fundamentos  # solo una carpeta
"""

from __future__ import annotations

import ast
import importlib
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent

#: Módulos que los notebooks importan a propósito aunque puedan no estar instalados
#: (dependencias opcionales o de despliegue). No se consideran error.
OPCIONALES = {
    "langgraph.checkpoint.postgres", "langgraph_sdk", "langgraph_supervisor",
    "langgraph_swarm", "tavily", "langchain_tavily", "psycopg", "psycopg_pool",
    "matplotlib", "matplotlib.pyplot", "sklearn", "rank_bm25", "IPython",
    "IPython.display", "pytest", "langsmith", "dotenv",
}

MAGIA = re.compile(r"^\s*[!%]")


def limpiar(codigo: str) -> str:
    """Quita magias de IPython (`!pip install`, `%%time`) para poder compilar."""
    return "\n".join("" if MAGIA.match(l) else l for l in codigo.splitlines())


def importable(modulo: str):
    try:
        return importlib.import_module(modulo)
    except Exception:
        return None


def revisar_importaciones(arbol: ast.AST, origen: str, fallos: list[str]) -> None:
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for a in nodo.names:
                if a.name.split(".")[0] in {"utils"} or a.name in OPCIONALES:
                    continue
                if importable(a.name) is None:
                    fallos.append(f"{origen}: no se puede importar el módulo `{a.name}`")

        elif isinstance(nodo, ast.ImportFrom):
            if nodo.level or not nodo.module:
                continue
            if nodo.module.split(".")[0] == "utils" or nodo.module in OPCIONALES:
                continue
            mod = importable(nodo.module)
            if mod is None:
                fallos.append(f"{origen}: no se puede importar el módulo `{nodo.module}`")
                continue
            for a in nodo.names:
                if a.name == "*":
                    continue
                if not hasattr(mod, a.name) and importable(f"{nodo.module}.{a.name}") is None:
                    fallos.append(f"{origen}: `{nodo.module}` no expone `{a.name}`")


def validar(nb: pathlib.Path) -> tuple[int, list[str]]:
    fallos: list[str] = []
    try:
        doc = json.loads(nb.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return 0, [f"{nb.name}: JSON inválido — {exc}"]

    if doc.get("nbformat") != 4:
        fallos.append(f"{nb.name}: nbformat != 4")
    celdas = doc.get("cells", [])
    if not celdas:
        fallos.append(f"{nb.name}: sin celdas")

    n_codigo = 0
    for i, celda in enumerate(celdas):
        tipo = celda.get("cell_type")
        if tipo not in ("code", "markdown", "raw"):
            fallos.append(f"{nb.name}[{i}]: cell_type desconocido {tipo!r}")
            continue
        fuente = "".join(celda.get("source", []))
        if tipo != "code":
            continue
        n_codigo += 1
        if "outputs" not in celda or "execution_count" not in celda:
            fallos.append(f"{nb.name}[{i}]: celda de código sin outputs/execution_count")
        origen = f"{nb.name}[celda {i}]"
        try:
            arbol = ast.parse(limpiar(fuente))
        except SyntaxError as exc:
            fallos.append(f"{origen}: error de sintaxis en la línea {exc.lineno} — {exc.msg}")
            continue
        revisar_importaciones(arbol, origen, fallos)

    return n_codigo, fallos


def main(argv: list[str]) -> int:
    objetivos = [RAIZ / a for a in argv] if argv else [RAIZ]
    notebooks = sorted({p for obj in objetivos for p in obj.rglob("*.ipynb")
                        if ".ipynb_checkpoints" not in p.parts})
    if not notebooks:
        print("No hay notebooks que validar.")
        return 0

    total_fallos: list[str] = []
    for nb in notebooks:
        n, fallos = validar(nb)
        marca = "FALLA" if fallos else "  ok "
        print(f"[{marca}] {nb.relative_to(RAIZ)}  ({n} celdas de código)")
        for f in fallos:
            print(f"          - {f}")
        total_fallos += fallos

    print(f"\n{len(notebooks)} notebooks, {len(total_fallos)} problemas")
    return 1 if total_fallos else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
