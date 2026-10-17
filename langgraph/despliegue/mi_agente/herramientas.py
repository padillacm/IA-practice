"""Herramientas del agente.

Se cargan los datos UNA vez al importar el módulo, no en cada llamada: el servidor
importa esto al arrancar y lo reutiliza en todas las peticiones.
"""

from __future__ import annotations

import pathlib

import pandas as pd
from langchain_core.tools import tool

_DATOS = pathlib.Path(__file__).resolve().parent.parent.parent / "data" / "tickets_soporte.csv"
_DF = pd.read_csv(_DATOS)

CATEGORIAS = sorted(_DF["categoria"].unique())


@tool(parse_docstring=True)
def contar_tickets(categoria: str = "todas", prioridad: str = "todas") -> str:
    """Cuenta tickets de soporte con los filtros indicados.

    Args:
        categoria: la categoría a filtrar, o 'todas'.
        prioridad: baja, media, alta, critica, o 'todas'.
    """
    sel = _DF
    if categoria != "todas":
        sel = sel[sel["categoria"] == categoria]
        if sel.empty:
            return f"No existe la categoría '{categoria}'. Válidas: {', '.join(CATEGORIAS)}."
    if prioridad != "todas":
        sel = sel[sel["prioridad"] == prioridad]
    return f"{len(sel)} tickets (categoría={categoria}, prioridad={prioridad})."


@tool(parse_docstring=True)
def detalle_ticket(id_ticket: str) -> str:
    """Devuelve el detalle de un ticket concreto.

    Args:
        id_ticket: identificador con formato TCK-0001.
    """
    fila = _DF[_DF["id_ticket"] == id_ticket]
    if fila.empty:
        return f"No existe {id_ticket}. El formato correcto es TCK-0001."
    r = fila.iloc[0]
    return f"{r['id_ticket']} [{r['categoria']}/{r['prioridad']}] {r['asunto']}"


HERRAMIENTAS = [contar_tickets, detalle_ticket]
