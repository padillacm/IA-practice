"""Carga de los conjuntos de datos del curso.

Todos los ficheros viven en `langgraph/data/` y están versionados en el repositorio,
así que los notebooks funcionan sin red. `--descargar` vuelve a traer los originales
públicos por si quieres comprobar la procedencia o actualizarlos.
"""

from __future__ import annotations

import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"

#: fichero local -> URL de origen (todos públicos y de acceso directo)
FUENTES = {
    "ventas_supermercado.csv":
        "https://raw.githubusercontent.com/plotly/datasets/master/supermarket_Sales.csv",
    "titanic.csv":
        "https://raw.githubusercontent.com/datasciencedojo/datasets/master/titanic.csv",
    "clima_seattle.csv":
        "https://raw.githubusercontent.com/vega/vega-datasets/main/data/seattle-weather.csv",
    "propinas.csv":
        "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv",
}

FICHA = {
    "ventas_supermercado.csv": "1.000 líneas de venta de tres supermercados (Myanmar, 2019). Real.",
    "titanic.csv": "891 pasajeros del Titanic con supervivencia. Real, clásico de clasificación.",
    "clima_seattle.csv": "1.461 días de clima en Seattle (2012-2015). Real, serie temporal.",
    "propinas.csv": "244 cuentas de restaurante con propina. Real, clásico de regresión.",
    "tickets_soporte.csv": "400 tickets de soporte en español con categoría y prioridad "
                           "etiquetadas. Sintético y determinista (ver _tools/generar_tickets.py).",
}


def _pandas():
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover
        raise ImportError("Necesitas pandas:  pip install pandas") from exc
    return pd


def ruta(nombre: str) -> pathlib.Path:
    p = DATOS / nombre
    if not p.exists():
        raise FileNotFoundError(f"No encuentro {p}. Ejecuta: python utils/datos.py --descargar")
    return p


def cargar(nombre: str, **kwargs):
    """Carga un CSV del curso como `DataFrame`."""
    return _pandas().read_csv(ruta(nombre), **kwargs)


def tickets():
    """Tickets de soporte etiquetados (Proyecto 1 y Proyecto 3)."""
    df = cargar("tickets_soporte.csv", parse_dates=["fecha"])
    return df


def ventas():
    """Ventas de supermercado, con nombres de columna normalizados a snake_case."""
    df = cargar("ventas_supermercado.csv")
    df.columns = [c.strip().lower().replace(" ", "_").replace("%", "pct") for c in df.columns]
    df["date"] = _pandas().to_datetime(df["date"], format="%m/%d/%Y")
    return df


def clima():
    """Clima diario de Seattle."""
    return cargar("clima_seattle.csv", parse_dates=["date"])


def documentos_kb() -> list[pathlib.Path]:
    """Ficheros markdown del corpus RAG (documentación oficial de LangGraph)."""
    ficheros = sorted((DATOS / "kb").glob("*.md"))
    if not ficheros:
        raise FileNotFoundError(f"El corpus {DATOS / 'kb'} está vacío.")
    return ficheros


def catalogo() -> None:
    """Imprime qué hay disponible y de dónde viene."""
    print(f"Datos del curso en {DATOS}\n")
    for nombre, desc in FICHA.items():
        p = DATOS / nombre
        estado = f"{p.stat().st_size / 1024:.0f} KB" if p.exists() else "AUSENTE"
        print(f"  {nombre:<28} {estado:>9}  {desc}")
    kb = DATOS / "kb"
    n = len(list(kb.glob('*.md'))) if kb.exists() else 0
    print(f"  {'kb/ (corpus RAG)':<28} {n:>6} docs  Documentación oficial de LangGraph (MIT).")


def descargar() -> None:
    import urllib.request

    DATOS.mkdir(parents=True, exist_ok=True)
    for nombre, url in FUENTES.items():
        print(f"  descargando {nombre} ...", end=" ", flush=True)
        with urllib.request.urlopen(url, timeout=60) as r:
            (DATOS / nombre).write_bytes(r.read())
        print(f"{(DATOS / nombre).stat().st_size} bytes")
    print("\nLos datos sintéticos se regeneran con: python _tools/generar_tickets.py")


if __name__ == "__main__":
    if "--descargar" in sys.argv:
        descargar()
    else:
        catalogo()
