"""Nivel 3: persistencia, reanudación y human-in-the-loop.

Son las funcionalidades más difíciles de probar a mano y las más fáciles de probar aquí:
todo ocurre en memoria y en milisegundos.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class EstadoAprobacion(TypedDict):
    importe: float
    decision: str
    efectos: Annotated[list[str], operator.add]


EFECTOS_REALES: list[str] = []


def pedir_aprobacion(estado: EstadoAprobacion) -> dict:
    """El interrupt va PRIMERO: reejecutar este nodo no tiene efectos laterales."""
    respuesta = interrupt({"importe": estado["importe"]})
    return {"decision": respuesta["decision"]}


def ejecutar_pago(estado: EstadoAprobacion) -> dict:
    if estado["decision"] != "aprobar":
        return {"efectos": ["cancelado"]}
    EFECTOS_REALES.append(f"cobro de {estado['importe']}")
    return {"efectos": [f"cobrados {estado['importe']} €"]}


@pytest.fixture
def grafo_pago():
    EFECTOS_REALES.clear()
    return (
        StateGraph(EstadoAprobacion)
        .add_sequence([("pedir", pedir_aprobacion), ("pagar", ejecutar_pago)])
        .add_edge(START, "pedir")
        .compile(checkpointer=InMemorySaver())
    )


def test_el_grafo_se_detiene_y_expone_la_peticion(grafo_pago, hilo):
    salida = grafo_pago.invoke({"importe": 250.0, "decision": "", "efectos": []}, hilo)
    assert "__interrupt__" in salida
    assert salida["__interrupt__"][0].value == {"importe": 250.0}
    assert grafo_pago.get_state(hilo).next == ("pedir",)
    assert EFECTOS_REALES == [], "no debe haber ningún efecto antes de aprobar"


def test_reanudar_con_aprobacion_ejecuta_el_pago_una_sola_vez(grafo_pago, hilo):
    grafo_pago.invoke({"importe": 250.0, "decision": "", "efectos": []}, hilo)
    salida = grafo_pago.invoke(Command(resume={"decision": "aprobar"}), hilo)
    assert salida["efectos"] == ["cobrados 250.0 €"]
    assert len(EFECTOS_REALES) == 1, "el efecto lateral se ha ejecutado más de una vez"


def test_reanudar_con_rechazo_no_ejecuta_nada(grafo_pago, hilo):
    grafo_pago.invoke({"importe": 250.0, "decision": "", "efectos": []}, hilo)
    salida = grafo_pago.invoke(Command(resume={"decision": "rechazar"}), hilo)
    assert salida["efectos"] == ["cancelado"]
    assert EFECTOS_REALES == []


def test_los_hilos_estan_aislados(grafo_pago):
    """El thread_id es la frontera de privacidad: dos hilos no se ven."""
    a = {"configurable": {"thread_id": "cliente-a"}}
    b = {"configurable": {"thread_id": "cliente-b"}}
    grafo_pago.invoke({"importe": 100.0, "decision": "", "efectos": []}, a)
    grafo_pago.invoke({"importe": 900.0, "decision": "", "efectos": []}, b)
    assert grafo_pago.get_state(a).values["importe"] == 100.0
    assert grafo_pago.get_state(b).values["importe"] == 900.0


# --------------------------------------------------------------------------------------
# Tolerancia a fallos
# --------------------------------------------------------------------------------------

def test_al_reanudar_solo_se_reejecuta_el_nodo_que_fallo():
    ejecuciones: dict[str, int] = {}
    fallar = {"activo": True}

    class EstadoT(TypedDict):
        pasos: Annotated[list[str], operator.add]

    def hacer(nombre: str):
        def nodo(estado):
            ejecuciones[nombre] = ejecuciones.get(nombre, 0) + 1
            if nombre == "tercero" and fallar["activo"]:
                fallar["activo"] = False
                raise ConnectionError("fallo transitorio")
            return {"pasos": [nombre]}
        return nodo

    grafo = (
        StateGraph(EstadoT)
        .add_sequence([("primero", hacer("primero")), ("segundo", hacer("segundo")),
                       ("tercero", hacer("tercero"))])
        .add_edge(START, "primero")
        .compile(checkpointer=InMemorySaver())
    )
    conf = {"configurable": {"thread_id": "fallo-1"}}

    with pytest.raises(ConnectionError):
        grafo.invoke({"pasos": []}, conf)

    salida = grafo.invoke(None, conf)          # None = continúa donde te quedaste
    assert salida["pasos"] == ["primero", "segundo", "tercero"]
    assert ejecuciones == {"primero": 1, "segundo": 1, "tercero": 2}


def test_el_historial_permite_volver_a_un_estado_anterior():
    class EstadoH(TypedDict):
        n: Annotated[int, operator.add]

    grafo = (StateGraph(EstadoH).add_node("sumar", lambda e: {"n": 1})
             .add_edge(START, "sumar").compile(checkpointer=InMemorySaver()))
    conf = {"configurable": {"thread_id": "historial-1"}}
    for _ in range(3):
        grafo.invoke({"n": 0}, conf)

    assert grafo.get_state(conf).values["n"] == 3

    historial = list(grafo.get_state_history(conf))
    anterior = next(h for h in historial if h.values.get("n") == 2 and not h.next)
    assert grafo.get_state(anterior.config).values["n"] == 2
