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
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, TypedDict

import json
import pathlib

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

RAIZ = pathlib.Path(__file__).resolve().parents[1]
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


# ======================================================================================
# Notebook 26 · el contrato que ve quien te consume
# ======================================================================================
def test_sin_input_schema_se_expone_el_estado_entero():
    """Un grafo sin `input_schema` publica sus campos internos como obligatorios.

    Es la razón de ser del notebook 26: el estado es tu estructura interna, el
    `input_schema` es tu API pública.
    """
    from typing_extensions import TypedDict as TD

    class Estado(TD):
        pregunta: str
        bitacora: list
        contador: int

    grafo = (StateGraph(Estado).add_node("n", lambda e: {})
             .add_edge(START, "n").add_edge("n", END).compile())

    campos = set(grafo.get_input_jsonschema().get("properties", {}))
    assert campos == {"pregunta", "bitacora", "contador"}


def test_con_input_schema_solo_se_expone_lo_declarado():
    from typing_extensions import TypedDict as TD

    class Entrada(TD):
        pregunta: str

    class Salida(TD):
        respuesta: str

    class Estado(Entrada, Salida):
        bitacora: list

    grafo = (StateGraph(Estado, input_schema=Entrada, output_schema=Salida)
             .add_node("n", lambda e: {"respuesta": "x"})
             .add_edge(START, "n").add_edge("n", END).compile())

    assert set(grafo.get_input_jsonschema()["properties"]) == {"pregunta"}
    assert set(grafo.get_output_jsonschema()["properties"]) == {"respuesta"}


@pytest.mark.skipif(sys.version_info >= (3, 12),
                    reason="en Python 3.12+ Pydantic ya introspecciona typing.TypedDict")
def test_typing_typeddict_impide_publicar_el_esquema():
    """El fallo silencioso del notebook 26.

    En Python < 3.12, un `typing.TypedDict` hace que el esquema no se pueda generar; el
    servidor lo publica como `null` y la herramienta MCP sale sin campos. Aquí lo fijamos
    como prueba para que, si algún día deja de pasar, nos enteremos.
    """
    import typing

    Entrada = typing.TypedDict("Entrada", {"categoria": str})
    Estado = typing.TypedDict("Estado", {"categoria": str, "resumen": str})

    grafo = (StateGraph(Estado, input_schema=Entrada)
             .add_node("n", lambda e: {"resumen": "x"})
             .add_edge(START, "n").add_edge("n", END).compile())

    with pytest.raises(Exception, match="typing_extensions"):
        grafo.get_input_jsonschema()


def test_typing_extensions_typeddict_si_publica_el_esquema():
    import typing_extensions

    Entrada = typing_extensions.TypedDict("Entrada", {"categoria": str})
    Estado = typing_extensions.TypedDict("Estado", {"categoria": str, "resumen": str})

    grafo = (StateGraph(Estado, input_schema=Entrada)
             .add_node("n", lambda e: {"resumen": "x"})
             .add_edge(START, "n").add_edge("n", END).compile())

    assert set(grafo.get_input_jsonschema()["properties"]) == {"categoria"}


def test_los_grafos_expuestos_de_la_app_tienen_contrato():
    """Los grafos con `description` en langgraph.json se consideran expuestos.

    De uno expuesto exigimos las dos cosas que hacen que otro modelo pueda usarlo:
    esquema publicable y distinto del estado entero.
    """
    import importlib.util
    from typing import get_type_hints

    ruta_app = RAIZ / "despliegue"
    cfg = json.loads((ruta_app / "langgraph.json").read_text(encoding="utf-8"))
    sys.path.insert(0, str(ruta_app))

    expuestos = {n: e for n, e in cfg["graphs"].items()
                 if isinstance(e, dict) and e.get("description")}
    assert expuestos, "la app debería exponer al menos un grafo con descripción"

    for nombre, entrada in expuestos.items():
        fichero = (ruta_app / entrada["path"].rsplit(":", 1)[0]).resolve()
        spec = importlib.util.spec_from_file_location(fichero.stem, fichero)
        modulo = importlib.util.module_from_spec(spec)
        sys.modules[fichero.stem] = modulo
        spec.loader.exec_module(modulo)
        grafo = getattr(modulo, entrada["path"].rsplit(":", 1)[1])

        entrada_esq = set(grafo.get_input_jsonschema().get("properties", {}))
        estado_esq = set(get_type_hints(grafo.builder.state_schema, include_extras=False))
        assert entrada_esq, f"{nombre}: esquema de entrada vacío"
        assert entrada_esq != estado_esq, f"{nombre}: expone el estado entero"


# ======================================================================================
# Consistencia del proyecto (uv)
# ======================================================================================
def test_requirements_esta_al_dia_con_el_lock():
    """`requirements.txt` es un fichero DERIVADO de uv.lock.

    Si alguien toca `pyproject.toml` y no reexporta, las dos vías de instalación divergen
    en silencio. Esta prueba es la que lo impide.
    """
    import subprocess

    if not (RAIZ / "uv.lock").exists():
        pytest.skip("sin uv.lock")

    salida = subprocess.run([sys.executable, str(RAIZ / "_tools" / "exportar_requisitos.py"),
                             "--check"], capture_output=True, text=True)
    if "uv" in salida.stderr and salida.returncode == 2:
        pytest.skip("uv no está en el PATH de este entorno")
    assert salida.returncode == 0, salida.stdout + salida.stderr


def test_las_dependencias_del_curso_declaran_lo_que_importan_los_notebooks():
    """Nada de dependerse de paquetes transitivos por accidente.

    starlette, httpx y mcp los usan los notebooks 24 y 26; si llegaran solo como
    dependencia indirecta de otro paquete, una actualización podría quitarlos.
    """
    import tomllib

    pyproject = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    declaradas = {d.split(">")[0].split("[")[0].split("=")[0].strip().lower()
                  for d in pyproject["project"]["dependencies"]}

    for paquete in ("starlette", "httpx", "langgraph-sdk", "langchain-mcp-adapters"):
        assert paquete in declaradas, f"{paquete} se usa en los notebooks y no está declarado"
