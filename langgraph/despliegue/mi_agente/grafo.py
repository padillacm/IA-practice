"""Construcción del grafo. Este módulo solo EXPORTA; no ejecuta nada al importarse."""

from __future__ import annotations

import os

from langchain.chat_models import init_chat_model
from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.runtime import Runtime

from .estado import ContextoPeticion, EstadoSoporte
from .herramientas import HERRAMIENTAS

MODELO = os.environ.get("MODELO_AGENTE", "openai:gpt-4o-mini")

INSTRUCCIONES = {
    "es": ("Eres un asistente de soporte técnico. Usa las herramientas para dar cifras exactas. "
           "Responde en español, en 3 frases como máximo."),
    "en": ("You are a technical support assistant. Use the tools for exact figures. "
           "Answer in English, 3 sentences maximum."),
}


def _modelo():
    """Una instancia por proceso: crear un cliente por petición abre conexiones de más."""
    global _CACHE
    try:
        return _CACHE
    except NameError:
        _CACHE = init_chat_model(MODELO, temperature=0).bind_tools(HERRAMIENTAS)
        return _CACHE


def pensar(estado: EstadoSoporte, runtime: Runtime[ContextoPeticion]) -> dict:
    idioma = runtime.context.idioma if runtime.context else "es"
    sistema = SystemMessage(INSTRUCCIONES.get(idioma, INSTRUCCIONES["es"]))
    respuesta = _modelo().invoke([sistema, *estado["messages"]])
    n = len(getattr(respuesta, "tool_calls", None) or [])
    return {"messages": [respuesta], "consultas": n,
            "bitacora": [f"modelo: {n} herramienta(s) solicitada(s)"]}


def construir():
    """Devuelve el grafo compilado.

    Sin checkpointer: en LangGraph Platform lo inyecta el servidor con su propia base de
    datos. Ponerlo aquí a mano lo SOBRESCRIBIRÍA y perderías la persistencia real.
    """
    return (
        StateGraph(EstadoSoporte, context_schema=ContextoPeticion)
        .add_node("pensar", pensar)
        .add_node("herramientas", ToolNode(HERRAMIENTAS, handle_tool_errors=True))
        .add_edge(START, "pensar")
        .add_conditional_edges("pensar", tools_condition, {"tools": "herramientas", END: END})
        .add_edge("herramientas", "pensar")
        .compile()
    )


#: Lo que `langgraph.json` apunta. El servidor importa este objeto.
grafo = construir()
