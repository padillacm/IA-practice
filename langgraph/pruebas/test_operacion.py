"""Nivel 4: las invariantes de operación del módulo 7.

Estas pruebas no comprueban tu lógica de negocio: comprueban las **garantías del entorno**
sobre las que se apoya el material. Si una de ellas empieza a fallar, es que una versión
nueva de LangGraph ha cambiado un comportamiento que el curso documenta, y hay que
revisar los notebooks 22-25.

Es también el patrón que merece la pena copiar a tu propio proyecto: las suposiciones que
tu diseño da por buenas se escriben como pruebas, no como comentarios.
"""

from __future__ import annotations

import collections
import operator
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, TypedDict

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

SERDE = JsonPlusSerializer()


def ida_y_vuelta(valor):
    """Lo que le pasa a un valor al guardarse en un checkpoint y volver a leerse."""
    return SERDE.loads_typed(SERDE.dumps_typed({"v": valor}))["v"]


# ======================================================================================
# Notebook 22 · serialización del estado
# ======================================================================================
@pytest.mark.parametrize("valor", [
    "texto", 42, 3.5, True, None,
    [1, 2, 3], {"a": 1},
    {1, 2, 3},                       # set
    b"bytes",
    datetime(2026, 1, 1),
])
def test_tipos_que_sobreviven_al_checkpoint(valor):
    """Estos tipos vuelven idénticos. El material los da por buenos."""
    vuelta = ida_y_vuelta(valor)
    assert type(vuelta) is type(valor)
    assert vuelta == valor


def test_la_tupla_vuelve_como_lista():
    """La sorpresa del notebook 22, escrita como prueba.

    Si algún día esto empieza a fallar porque las tuplas se conservan, es una buena
    noticia — y hay que actualizar el notebook.
    """
    assert type(ida_y_vuelta((1, 2, 3))) is list


def test_una_clase_normal_no_es_serializable():
    """Falla ruidosamente, que es lo correcto: mejor un TypeError que un dato corrupto."""

    class Opaco:
        pass

    with pytest.raises(TypeError):
        SERDE.dumps_typed({"v": Opaco()})


def test_el_estado_no_deberia_contener_tuplas():
    """El detector que conviene tener sobre TU esquema de estado.

    Aquí se aplica a un esquema de ejemplo; en tu proyecto, apúntalo al de verdad.
    """

    class EstadoBueno(TypedDict):
        coordenadas: list[float]
        etiquetas: set[str]
        momento: datetime

    ejemplo = {"coordenadas": [1.0, 2.0], "etiquetas": {"a"}, "momento": datetime(2026, 1, 1)}
    problemas = [c for c, v in ejemplo.items() if type(ida_y_vuelta(v)) is not type(v)]
    assert problemas == []


# ======================================================================================
# Notebook 23 · persistencia a escala
# ======================================================================================
class EstadoPasos(TypedDict):
    pasos: Annotated[list[str], operator.add]


def _cadena(n_nodos: int) -> StateGraph:
    g = StateGraph(EstadoPasos)
    for i in range(n_nodos):
        g.add_node(f"n{i}", lambda estado, i=i: {"pasos": [f"n{i}"]})
    g.add_edge(START, "n0")
    for i in range(n_nodos - 1):
        g.add_edge(f"n{i}", f"n{i + 1}")
    g.add_edge(f"n{n_nodos - 1}", END)
    return g


def _contar(con: sqlite3.Connection) -> tuple[int, int]:
    return (con.execute("SELECT count(*) FROM checkpoints").fetchone()[0],
            con.execute("SELECT count(*) FROM writes").fetchone()[0])


@pytest.mark.parametrize("n_nodos", [1, 2, 3, 4, 6])
def test_checkpoints_por_turno_son_superpasos_mas_dos(n_nodos):
    con = sqlite3.connect(":memory:", check_same_thread=False)
    app = _cadena(n_nodos).compile(checkpointer=SqliteSaver(con))
    app.invoke({"pasos": []}, {"configurable": {"thread_id": "h"}})
    checkpoints, _ = _contar(con)
    assert checkpoints == n_nodos + 2


def test_durability_exit_escribe_un_solo_checkpoint():
    con = sqlite3.connect(":memory:", check_same_thread=False)
    app = _cadena(4).compile(checkpointer=SqliteSaver(con))
    app.invoke({"pasos": []}, {"configurable": {"thread_id": "h"}}, durability="exit")
    assert _contar(con) == (1, 0)


def test_podar_conserva_el_hilo_vivo():
    """Borrar historial antiguo no debe romper la continuidad de la conversación."""
    con = sqlite3.connect(":memory:", check_same_thread=False)
    app = _cadena(2).compile(checkpointer=SqliteSaver(con))
    cfg = {"configurable": {"thread_id": "h"}}
    for turno in range(5):
        app.invoke({"pasos": [f"t{turno}"]}, cfg)

    antes = app.get_state(cfg).values["pasos"]
    con.execute(
        """DELETE FROM checkpoints WHERE (thread_id, checkpoint_id) NOT IN (
               SELECT thread_id, checkpoint_id FROM (
                   SELECT thread_id, checkpoint_id,
                          ROW_NUMBER() OVER (PARTITION BY thread_id
                                             ORDER BY checkpoint_id DESC) AS pos
                     FROM checkpoints) WHERE pos <= 2)""")
    con.execute("""DELETE FROM writes WHERE (thread_id, checkpoint_id) NOT IN
                   (SELECT thread_id, checkpoint_id FROM checkpoints)""")
    con.commit()

    assert app.get_state(cfg).values["pasos"] == antes        # el presente intacto
    despues = app.invoke({"pasos": ["nuevo"]}, cfg)           # y sigue avanzando
    assert despues["pasos"][:len(antes)] == antes


# ======================================================================================
# Notebook 24 · concurrencia
# ======================================================================================
def _grafo_lento(retardo: float = 0.3):
    def lento(estado):
        time.sleep(retardo)
        return {"pasos": ["LENTO"]}

    return (StateGraph(EstadoPasos).add_node("lento", lento)
            .add_edge(START, "lento").add_edge("lento", END)
            .compile(checkpointer=InMemorySaver()))


def _dos_ejecuciones(enviar, separacion: float = 0.1) -> None:
    hilos = [threading.Thread(target=enviar, args=(f"m{i}",)) for i in (1, 2)]
    hilos[0].start()
    time.sleep(separacion)
    hilos[1].start()
    for h in hilos:
        h.join()


def test_dos_ejecuciones_en_el_mismo_hilo_pierden_escrituras():
    """Documenta la anomalía del notebook 24. NO es un bug del curso: es la garantía
    que LangGraph no da y que tu servidor tiene que añadir."""
    app = _grafo_lento()
    cfg = {"configurable": {"thread_id": "compartido"}}
    _dos_ejecuciones(lambda m: app.invoke({"pasos": [m]}, cfg))

    pasos = app.get_state(cfg).values["pasos"]
    assert pasos.count("LENTO") == 1, "si esto pasa a 2, LangGraph ya serializa por hilo"


def test_el_cerrojo_por_hilo_evita_la_perdida():
    app = _grafo_lento()
    cerrojos: dict[str, threading.Lock] = collections.defaultdict(threading.Lock)
    maestro = threading.Lock()

    def enviar(mensaje: str) -> None:
        with maestro:
            cerrojo = cerrojos["seguro"]
        with cerrojo:
            app.invoke({"pasos": [mensaje]}, {"configurable": {"thread_id": "seguro"}})

    _dos_ejecuciones(enviar)
    pasos = app.get_state({"configurable": {"thread_id": "seguro"}}).values["pasos"]
    assert pasos.count("LENTO") == 2


def test_el_grafo_compilado_se_puede_compartir_entre_hilos():
    """Hilos distintos con thread_id distintos no se contaminan."""
    app = _grafo_lento(retardo=0.01)
    resultados: dict[int, list[str]] = {}

    def peticion(n: int) -> None:
        resultados[n] = app.invoke(
            {"pasos": [f"u{n}"]}, {"configurable": {"thread_id": f"u-{n}"}})["pasos"]

    hilos = [threading.Thread(target=peticion, args=(n,)) for n in range(8)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert all(r == [f"u{n}", "LENTO"] for n, r in resultados.items())


# ======================================================================================
# Notebook 25 · configuración de despliegue
# ======================================================================================
import json
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parents[1]


def test_la_configuracion_de_produccion_esta_endurecida():
    cfg = json.loads((RAIZ / "despliegue" / "langgraph.produccion.json").read_text())

    assert "auth" in cfg, "sin auth, la API está abierta"
    assert "ttl" in cfg.get("checkpointer", {}), "sin TTL la base de datos crece sin límite"
    cors = cfg["http"]["cors"]
    assert cors["allow_origins"] != ["*"] or not cors.get("allow_credentials"), \
        "CORS con comodín y credenciales a la vez es un fallo de seguridad"
    assert cfg["http"]["disable_meta"] is True, "/docs publica la API entera"


def test_las_reglas_de_acceso_cubren_todos_los_recursos():
    """Ninguna combinación (recurso, acción) debe caer en un permiso por omisión."""
    import sys

    sys.path.insert(0, str(RAIZ / "despliegue"))
    from mi_agente.auth import auth

    assert auth._authenticate_handler is not None, "falta @auth.authenticate"
    assert auth._global_handlers, "falta un manejador global que deniegue lo no contemplado"

    def hay_regla(recurso: str, accion: str) -> bool:
        return ((recurso, accion) in auth._handlers
                or (recurso, "*") in auth._handlers
                or bool(auth._global_handlers))

    for recurso, accion in [("threads", "create"), ("threads", "read"), ("threads", "search"),
                            ("threads", "delete"), ("assistants", "create"),
                            ("crons", "create"), ("store", "put")]:
        assert hay_regla(recurso, accion), f"{recurso}.{accion} sin regla"
