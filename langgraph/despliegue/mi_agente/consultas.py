"""Un segundo grafo, diseñado para que **otros agentes** lo consuman.

`grafo.py` está pensado para una interfaz de chat: recibe `messages` y devuelve `messages`.
Ese contrato es cómodo para una persona y pésimo para exponerlo por MCP o A2A, porque el
esquema que ve el otro modelo es el estado entero — incluidos campos internos como
`bitacora` o `consultas`, que además salen como obligatorios.

Aquí hacemos lo contrario: `input_schema` y `output_schema` explícitos y mínimos. El
resultado es una herramienta con dos campos, uno de entrada y uno de salida, que cualquier
modelo entiende a la primera. Es el mismo grafo por dentro; lo que cambia es el contrato.

**Detalle que cuesta caro descubrir:** en Python < 3.12 hay que importar `TypedDict` de
`typing_extensions`, no de `typing`. Con el de `typing`, Pydantic no puede construir el
JSON Schema, el servidor publica `input_schema: null` y la herramienta MCP aparece **sin
campos**. No hay error en ningún sitio: el grafo funciona y el contrato sale vacío.

Se expone en `langgraph.json` con su propia descripción:

    "graphs": {
      "consultas": {
        "path": "./mi_agente/consultas.py:grafo",
        "description": "Responde preguntas sobre el volumen de tickets de soporte…"
      }
    }
"""

from __future__ import annotations

from typing_extensions import TypedDict   # ¡NO `typing.TypedDict`! Ver la nota de abajo.

from langgraph.graph import END, START, StateGraph

from mi_agente.herramientas import CATEGORIAS, contar_tickets


class EntradaConsulta(TypedDict):
    """Lo único que el otro agente tiene que darnos."""

    categoria: str


class SalidaConsulta(TypedDict):
    """Lo único que devolvemos."""

    resumen: str


class EstadoConsulta(EntradaConsulta, SalidaConsulta):
    """El estado completo: la unión de entrada y salida, más lo interno si hiciera falta."""

    detalle: dict


def consultar(estado: EstadoConsulta) -> dict:
    categoria = estado["categoria"]
    if categoria not in CATEGORIAS and categoria != "todas":
        return {"resumen": f"Categoría desconocida. Las válidas son: {', '.join(CATEGORIAS)}.",
                "detalle": {"error": "categoria_desconocida"}}

    conteo = contar_tickets.invoke({"categoria": categoria, "prioridad": "todas"})
    criticos = contar_tickets.invoke({"categoria": categoria, "prioridad": "critica"})
    return {"resumen": f"{conteo} De esos, {criticos}",
            "detalle": {"categoria": categoria}}


def construir() -> StateGraph:
    return (
        StateGraph(EstadoConsulta,
                   input_schema=EntradaConsulta,      # lo que el mundo puede mandar
                   output_schema=SalidaConsulta)      # lo que el mundo ve al terminar
        .add_node("consultar", consultar)
        .add_edge(START, "consultar")
        .add_edge("consultar", END)
    )


grafo = construir().compile()
