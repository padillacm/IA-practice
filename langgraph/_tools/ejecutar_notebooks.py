"""Ejecuta los notebooks del curso de principio a fin con un modelo falso.

Es el tercer filtro de verificación del curso: la validación estática (`validar.py`)
comprueba que el código compila y que los símbolos existen, las pruebas (`pruebas/`)
comprueban las invariantes, y esto comprueba lo único que no ven las otras dos — **que
un notebook entero sigue ejecutándose**.

Usa `_tools/modelo_falso.py`, así que no necesita clave de API ni gasta cuota: puede
correr en cada *pull request*.

Uso:
    uv run _tools/ejecutar_notebooks.py                  # todos
    uv run _tools/ejecutar_notebooks.py 07_operacion/    # solo una carpeta
    uv run _tools/ejecutar_notebooks.py 01_fundamentos/01_grafos_estado_y_nodos.ipynb

Salida: una línea por notebook y un resumen. Devuelve 1 si alguno falla.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import textwrap

RAIZ = pathlib.Path(__file__).resolve().parents[1]

#: Guion que ejecuta UN notebook en un proceso limpio. Va en un subproceso a propósito:
#: los notebooks definen clases y variables globales con los mismos nombres, y compartir
#: intérprete entre ellos daría falsos positivos y falsos negativos por igual.
GUION = textwrap.dedent('''
    import json, pathlib, sys, traceback

    sys.path.insert(0, {raiz!r})
    sys.path.insert(0, {tools!r})
    import modelo_falso


    def _conducir(_ruta):
        """Ejecuta las celdas del notebook.

        Todo el estado del ejecutor vive en los LOCALES de esta función, a propósito.
        Las celdas se ejecutan en `__main__.__dict__`, y si el ejecutor guardara ahí sus
        variables, cualquier notebook que use el mismo nombre las machacaría. No es
        hipotético: el notebook 17 define una variable llamada `modelo_falso` y el 09 una
        llamada `espacio`. El fallo resultante —`exec() globals must be a dict`— no dice
        nada sobre su causa, y aparece muchas celdas después de la colisión.

        Se usa `__main__.__dict__` y no un diccionario nuevo porque es lo que hace Jupyter,
        y porque la deserialización de checkpoints resuelve las clases definidas en celdas
        mirando en `sys.modules["__main__"]` (notebook 22).
        """
        _documento = json.loads(_ruta.read_text(encoding="utf-8"))
        _espacio = sys.modules["__main__"].__dict__

        # Atamos lo que necesitamos del módulo a locales. Si dejáramos que el `lambda` de
        # abajo buscara `modelo_falso` como global, el notebook 17 —que define una variable
        # con ese mismo nombre— lo sustituiría por la suya y el fallo aparecería veinte
        # celdas más tarde, sin relación aparente.
        _instalar = modelo_falso.instalar
        _FakeChat = modelo_falso.FakeChat

        for _indice, _celda in enumerate(_documento["cells"]):
            if _celda["cell_type"] != "code":
                continue
            _fuente = "".join(_celda["source"])
            if not _fuente.strip():
                continue
            try:
                exec(compile(_fuente, f"{{_ruta.name}}:celda{{_indice}}", "exec"), _espacio)
            except Exception:
                print(f"celda {{_indice}}", file=sys.stderr)
                traceback.print_exc(limit=4)
                return 1

            # El modelo falso se instala justo después del arranque estándar del curso,
            # que es donde `llm` entra en el espacio de nombres del notebook.
            if "from utils.curso import" in _fuente:
                _instalar()
                _espacio["llm"] = lambda *a, **k: _FakeChat()
        return 0


    sys.exit(_conducir(pathlib.Path(sys.argv[1])))
''')


def notebooks(objetivos: list[str]) -> list[pathlib.Path]:
    if not objetivos:
        return sorted(RAIZ.glob("*/*.ipynb"))

    encontrados: list[pathlib.Path] = []
    for objetivo in objetivos:
        ruta = (RAIZ / objetivo).resolve()
        if ruta.is_dir():
            encontrados.extend(sorted(ruta.glob("*.ipynb")))
        elif ruta.is_file():
            encontrados.append(ruta)
        else:
            print(f"[aviso] no existe: {objetivo}")
    return encontrados


def ejecutar(cuaderno: pathlib.Path) -> tuple[bool, str]:
    guion = GUION.format(raiz=str(RAIZ), tools=str(RAIZ / "_tools"))
    resultado = subprocess.run(
        [sys.executable, "-c", guion, str(cuaderno)],
        cwd=RAIZ, capture_output=True, text=True,
    )
    return resultado.returncode == 0, resultado.stderr


def main() -> int:
    objetivo = notebooks(sys.argv[1:])
    if not objetivo:
        print("no hay notebooks que ejecutar")
        return 1

    fallos: list[pathlib.Path] = []
    for cuaderno in objetivo:
        correcto, error = ejecutar(cuaderno)
        etiqueta = cuaderno.relative_to(RAIZ)
        if correcto:
            print(f"[  ok ] {etiqueta}")
        else:
            fallos.append(cuaderno)
            print(f"[FALLO] {etiqueta}")
            for linea in error.strip().splitlines()[-8:]:
                print(f"        {linea}")

    print(f"\n{len(objetivo)} notebooks, {len(fallos)} con fallo")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
