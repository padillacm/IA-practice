"""Genera `requirements.txt` a partir de `uv.lock`.

El curso usa **uv** y su fuente de verdad es `pyproject.toml` + `uv.lock`. Pero hay dos
sitios donde sigue haciendo falta un `requirements.txt`:

* quien no quiera instalar uv y prefiera `pip install -r requirements.txt`;
* la imagen de despliegue, que instala con pip a partir de lo que declara `langgraph.json`.

Tener las dos listas escritas a mano es la forma clásica de que se desincronicen. Este
script deriva la segunda de la primera, con las versiones **exactas** del lock, para que
`pip` reproduzca lo mismo que `uv sync`.

Uso:
    uv run _tools/exportar_requisitos.py          # reescribe requirements.txt
    uv run _tools/exportar_requisitos.py --check  # falla si está desactualizado (para la CI)
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "requirements.txt"

CABECERA = """\
# ---------------------------------------------------------------------------------------
# FICHERO GENERADO. No lo edites a mano.
#
# La fuente de verdad de las dependencias del curso es `pyproject.toml`, y las versiones
# exactas están en `uv.lock`. Este fichero es la exportación de ese lock para quien
# prefiera pip:
#
#     pip install -r requirements.txt
#
# Para regenerarlo tras tocar `pyproject.toml`:
#
#     uv lock && uv run _tools/exportar_requisitos.py
#
# Instalación recomendada (crea el entorno y resuelve desde el lock):
#
#     uv sync
# ---------------------------------------------------------------------------------------
"""


def exportar() -> str:
    """Exporta el lock a formato requirements, sin hashes y sin el propio proyecto."""
    salida = subprocess.run(
        ["uv", "export", "--no-hashes", "--no-emit-project", "--no-annotate",
         "--group", "dev", "--group", "despliegue"],
        cwd=RAIZ, capture_output=True, text=True, check=True,
    ).stdout
    # `uv export` ya pone su propia cabecera de "autogenerado"; la sustituimos por la
    # nuestra, que además explica cómo regenerarlo.
    cuerpo = "\n".join(l for l in salida.splitlines() if not l.startswith("#"))
    return CABECERA + cuerpo.strip() + "\n"


def main() -> int:
    nuevo = exportar()
    comprobar = "--check" in sys.argv

    if comprobar:
        actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
        if actual != nuevo:
            print("requirements.txt está desactualizado respecto a uv.lock.")
            print("Regenéralo con:  uv run _tools/exportar_requisitos.py")
            return 1
        print("requirements.txt está al día con uv.lock")
        return 0

    DESTINO.write_text(nuevo, encoding="utf-8")
    paquetes = sum(1 for l in nuevo.splitlines() if l and not l.startswith("#"))
    print(f"[exportar] {DESTINO.relative_to(RAIZ)} <- uv.lock  ({paquetes} paquetes fijados)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
