"""Un servidor MCP mínimo, para el notebook 20 del curso.

Se ejecuta como un proceso aparte que habla por entrada/salida estándar (transporte
`stdio`). El cliente de LangChain lo arranca solo; no hace falta lanzarlo a mano.

Para probarlo por tu cuenta:
    python ejemplos/servidor_mcp_demo.py     # se queda esperando mensajes MCP por stdin
"""

from __future__ import annotations

import csv
import pathlib

from mcp.server.fastmcp import FastMCP

servidor = FastMCP("soporte-demo")

_DATOS = pathlib.Path(__file__).resolve().parent.parent / "data" / "tickets_soporte.csv"
with _DATOS.open(encoding="utf-8") as f:
    TICKETS = list(csv.DictReader(f))


@servidor.tool()
def contar_tickets(categoria: str = "todas", prioridad: str = "todas") -> str:
    """Cuenta tickets de soporte con los filtros indicados.

    Args:
        categoria: la categoría a filtrar, o 'todas'.
        prioridad: baja, media, alta, critica, o 'todas'.
    """
    sel = [t for t in TICKETS
           if (categoria == "todas" or t["categoria"] == categoria)
           and (prioridad == "todas" or t["prioridad"] == prioridad)]
    return f"{len(sel)} tickets (categoría={categoria}, prioridad={prioridad})."


@servidor.tool()
def detalle_ticket(id_ticket: str) -> str:
    """Devuelve el detalle de un ticket concreto.

    Args:
        id_ticket: identificador con formato TCK-0001.
    """
    for t in TICKETS:
        if t["id_ticket"] == id_ticket:
            return f"{t['id_ticket']} [{t['categoria']}/{t['prioridad']}] {t['asunto']}"
    return f"No existe {id_ticket}. El formato correcto es TCK-0001."


@servidor.resource("tickets://categorias")
def categorias() -> str:
    """Las categorías válidas del sistema de tickets."""
    return ", ".join(sorted({t["categoria"] for t in TICKETS}))


@servidor.prompt()
def analizar_cola(foco: str = "prioridad") -> str:
    """Plantilla de análisis de la cola de soporte.

    Args:
        foco: la dimensión sobre la que centrar el análisis.
    """
    return (f"Analiza la cola de tickets de soporte centrándote en {foco}. "
            "Usa las herramientas disponibles para dar cifras exactas y termina con "
            "una recomendación concreta.")


if __name__ == "__main__":
    servidor.run(transport="stdio")
