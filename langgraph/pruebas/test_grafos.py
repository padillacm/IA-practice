"""Nivel 2: el grafo completo, con un modelo falso.

Aquí se prueba la TOPOLOGÍA: que las aristas condicionales van donde deben, que los reducers
combinan bien, que el ciclo termina. Nada de esto necesita un modelo de verdad.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict

import pytest
from conftest import con_herramientas, guionizar
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool


# --------------------------------------------------------------------------------------
# Un agente mínimo, el sujeto de las pruebas
# --------------------------------------------------------------------------------------

@tool
def contar(categoria: str) -> str:
    """Cuenta elementos de una categoría."""
    return f"42 elementos de {categoria}"


def construir_agente(modelo):
    return (
        StateGraph(MessagesState)
        .add_node("modelo", lambda e: {"messages": [modelo.bind_tools([contar]).invoke(e["messages"])]})
        .add_node("tools", ToolNode([contar], handle_tool_errors=True))
        .add_edge(START, "modelo")
        .add_conditional_edges("modelo", tools_condition)
        .add_edge("tools", "modelo")
        .compile()
    )


def test_el_agente_llama_a_la_herramienta_y_responde():
    """Guionizamos dos turnos: primero pide la herramienta, después responde."""
    modelo = guionizar(
        con_herramientas("contar", {"categoria": "bugs"}),
        "He encontrado 42 elementos de bugs.",
    )
    salida = construir_agente(modelo).invoke(
        {"messages": [HumanMessage("¿cuántos bugs hay?")]}, {"recursion_limit": 10}
    )
    tipos = [m.type for m in salida["messages"]]
    assert tipos == ["human", "ai", "tool", "ai"], f"secuencia inesperada: {tipos}"
    assert "42" in salida["messages"][-1].text


def test_sin_tool_calls_el_agente_termina_en_un_turno():
    modelo = guionizar("No necesito herramientas para esto.")
    salida = construir_agente(modelo).invoke(
        {"messages": [HumanMessage("hola")]}, {"recursion_limit": 10}
    )
    assert len(salida["messages"]) == 2
    assert not getattr(salida["messages"][-1], "tool_calls", None)


def test_cada_tool_call_recibe_su_tool_message():
    """Invariante del protocolo: un ToolMessage por cada tool_call, con el mismo id."""
    modelo = guionizar(
        AIMessage("", tool_calls=[
            {"name": "contar", "args": {"categoria": "a"}, "id": "c1"},
            {"name": "contar", "args": {"categoria": "b"}, "id": "c2"},
        ]),
        "listo",
    )
    salida = construir_agente(modelo).invoke(
        {"messages": [HumanMessage("cuenta a y b")]}, {"recursion_limit": 10}
    )
    ids_pedidos = {tc["id"] for m in salida["messages"] for tc in (getattr(m, "tool_calls", None) or [])}
    ids_respondidos = {m.tool_call_id for m in salida["messages"] if m.type == "tool"}
    assert ids_pedidos == ids_respondidos


# --------------------------------------------------------------------------------------
# Enrutado: la parte que más se rompe al refactorizar
# --------------------------------------------------------------------------------------

class EstadoRuta(TypedDict):
    prioridad: str
    destino: str


def enrutar(estado: EstadoRuta) -> Literal["guardia", "cola", "auto"]:
    if estado["prioridad"] == "critica":
        return "guardia"
    return "cola" if estado["prioridad"] in ("alta", "media") else "auto"


@pytest.mark.parametrize(("prioridad", "esperado"), [
    ("critica", "guardia"), ("alta", "cola"), ("media", "cola"), ("baja", "auto"),
])
def test_el_router_es_una_funcion_pura(prioridad, esperado):
    """Un router se prueba sin construir el grafo: es una función de estado a nombre."""
    assert enrutar({"prioridad": prioridad, "destino": ""}) == esperado


def test_todos_los_destinos_del_router_existen_en_el_grafo():
    """Esta prueba caza el fallo que compile() NO detecta: una rama a un nodo inexistente."""
    from typing import get_args, get_type_hints

    constructor = StateGraph(EstadoRuta)
    for nombre in ("guardia", "cola", "auto"):
        constructor.add_node(nombre, lambda e, n=nombre: {"destino": n})
    constructor.add_node("clasificar", lambda e: {})
    constructor.add_edge(START, "clasificar")
    constructor.add_conditional_edges("clasificar", enrutar,
                                      {"guardia": "guardia", "cola": "cola", "auto": "auto"})
    grafo = constructor.compile()

    destinos_declarados = set(get_args(get_type_hints(enrutar)["return"]))
    nodos = {n for n in grafo.get_graph().nodes if not n.startswith("__")}
    assert destinos_declarados <= nodos, f"el router puede devolver nodos que no existen: {destinos_declarados - nodos}"


# --------------------------------------------------------------------------------------
# Reducers y concurrencia
# --------------------------------------------------------------------------------------

class EstadoConcurrente(TypedDict):
    hallazgos: Annotated[list[str], operator.add]


def test_las_escrituras_concurrentes_se_acumulan_sin_perderse():
    grafo = (
        StateGraph(EstadoConcurrente)
        .add_node("a", lambda e: {"hallazgos": ["de a"]})
        .add_node("b", lambda e: {"hallazgos": ["de b"]})
        .add_node("c", lambda e: {"hallazgos": ["de c"]})
        .add_edge(START, "a").add_edge(START, "b").add_edge(START, "c")
        .compile()
    )
    salida = grafo.invoke({"hallazgos": []})
    # El ORDEN no está garantizado entre ramas paralelas; el CONTENIDO sí.
    assert sorted(salida["hallazgos"]) == ["de a", "de b", "de c"]


def test_sin_reducer_las_escrituras_concurrentes_dan_error():
    """Comprobamos que la protección existe: es una funcionalidad, no un accidente."""
    from langgraph.errors import InvalidUpdateError

    class SinReducer(TypedDict):
        valor: str

    grafo = (
        StateGraph(SinReducer)
        .add_node("a", lambda e: {"valor": "a"})
        .add_node("b", lambda e: {"valor": "b"})
        .add_edge(START, "a").add_edge(START, "b")
        .compile()
    )
    with pytest.raises(InvalidUpdateError):
        grafo.invoke({"valor": ""})


# --------------------------------------------------------------------------------------
# Ciclos: que terminen
# --------------------------------------------------------------------------------------

def test_el_ciclo_respeta_el_tope_y_no_lanza_excepcion():
    class EstadoBucle(TypedDict):
        turnos: Annotated[int, operator.add]
        resultado: str

    def trabajar(estado):
        return {"turnos": 1}

    def seguir(estado) -> Literal["trabajar", "rendirse"]:
        return "trabajar" if estado["turnos"] < 4 else "rendirse"

    grafo = (
        StateGraph(EstadoBucle)
        .add_node("trabajar", trabajar)
        .add_node("rendirse", lambda e: {"resultado": f"me rindo tras {e['turnos']}"})
        .add_edge(START, "trabajar")
        .add_conditional_edges("trabajar", seguir, {"trabajar": "trabajar", "rendirse": "rendirse"})
        .add_edge("rendirse", END)
        .compile()
    )
    salida = grafo.invoke({"turnos": 0, "resultado": ""}, {"recursion_limit": 20})
    assert salida["turnos"] == 4
    assert "me rindo" in salida["resultado"]
