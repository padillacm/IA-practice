"""Servidor MCP de ventas — solución del ejercicio 20.1."""

import csv
import pathlib
from typing import Literal

from mcp.server.fastmcp import FastMCP

servidor = FastMCP("ventas-demo")

_RUTA = pathlib.Path(__file__).resolve().parent.parent / "data" / "ventas_supermercado.csv"
with _RUTA.open(encoding="utf-8") as f:
    VENTAS = list(csv.DictReader(f))

COLUMNA = {"ingresos": "Total", "unidades": "Quantity", "margen": "Gross income"}
DIMENSION = {"ciudad": "City", "linea_producto": "Product line",
             "tipo_cliente": "Customer type", "metodo_pago": "Payment"}


@servidor.tool()
def agregar_ventas(
    metrica: Literal["ingresos", "unidades", "margen"],
    dimension: Literal["ciudad", "linea_producto", "tipo_cliente", "metodo_pago", "ninguna"] = "ninguna",
) -> str:
    """Suma una métrica de ventas, opcionalmente agrupada por una dimensión.

    Args:
        metrica: qué se mide.
        dimension: por qué columna agrupar, o 'ninguna' para el total.
    """
    col = COLUMNA[metrica]
    if dimension == "ninguna":
        total = sum(float(v[col]) for v in VENTAS)
        return f"{metrica} total: {total:,.2f}"

    dim = DIMENSION[dimension]
    grupos: dict[str, float] = {}
    for v in VENTAS:
        grupos[v[dim]] = grupos.get(v[dim], 0.0) + float(v[col])
    filas = sorted(grupos.items(), key=lambda kv: -kv[1])
    return f"{metrica} por {dimension}:\n" + "\n".join(f"  {k}: {v:,.2f}" for k, v in filas)


@servidor.resource("ventas://dimensiones")
def dimensiones() -> str:
    """Valores válidos de cada dimensión, para poder construir consultas correctas."""
    lineas = []
    for nombre, columna in DIMENSION.items():
        valores = sorted({v[columna] for v in VENTAS})
        lineas.append(f"{nombre}: {', '.join(valores)}")
    return "\n".join(lineas)


@servidor.prompt()
def informe_ventas(periodo: str = "el periodo completo") -> str:
    """Plantilla para pedir un informe de ventas.

    Args:
        periodo: el periodo del que informar.
    """
    return (f"Elabora un informe de ventas de {periodo}. Usa las herramientas para obtener "
            "cifras exactas, compara al menos dos dimensiones y termina con una recomendación.")


if __name__ == "__main__":
    servidor.run(transport="stdio")
