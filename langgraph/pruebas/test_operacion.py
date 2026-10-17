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


# ======================================================================================
# Notebook 27 · evaluación de trayectorias
# ======================================================================================
def _traza(*llamadas):
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    mensajes = [HumanMessage("pregunta")]
    for i, (nombre, args) in enumerate(llamadas):
        mensajes.append(AIMessage("", tool_calls=[{"name": nombre, "args": args, "id": f"c{i}"}]))
        mensajes.append(ToolMessage("ok", tool_call_id=f"c{i}", name=nombre))
    mensajes.append(AIMessage("respuesta"))
    return mensajes


_POLITICA = ("buscar_politica", {"tema": "sla"})
_CONTAR = ("contar_tickets", {"categoria": "facturacion", "prioridad": "critica"})
_DETALLE = ("detalle_ticket", {"id_ticket": "TCK-0001"})


@pytest.mark.parametrize("modo,salida,esperado", [
    # el agente hizo exactamente lo mismo
    ("strict",    (_POLITICA, _CONTAR),            True),
    # mismas llamadas, otro orden
    ("strict",    (_CONTAR, _POLITICA),            False),
    ("unordered", (_CONTAR, _POLITICA),            True),
    # se saltó una llamada obligatoria: lo detecta `superset`
    ("superset",  (_CONTAR,),                      False),
    ("subset",    (_CONTAR,),                      True),
    # llamó de más: lo detecta `subset`
    ("subset",    (_POLITICA, _CONTAR, _DETALLE),  False),
    ("superset",  (_POLITICA, _CONTAR, _DETALLE),  True),
])
def test_modos_de_coincidencia_de_trayectoria(modo, salida, esperado):
    """Fija la tabla de verdad del notebook 27.

    Si `agentevals` cambia la semántica de un modo, esta prueba lo dice antes de que el
    material quede desactualizado.
    """
    agentevals = pytest.importorskip("agentevals.trajectory.match")

    evaluar = agentevals.create_trajectory_match_evaluator(trajectory_match_mode=modo)
    resultado = evaluar(outputs=_traza(*salida),
                        reference_outputs=_traza(_POLITICA, _CONTAR))
    assert resultado["score"] is esperado


def test_comparar_argumentos_en_exacto_falla_con_lenguaje_natural():
    """La trampa del notebook 27: `exact` sobre una consulta libre siempre suspende."""
    match = pytest.importorskip("agentevals.trajectory.match")

    ref = _traza(("buscar", {"consulta": "tickets de facturación críticos", "limite": 5}))
    sal = _traza(("buscar", {"consulta": "tickets criticos facturacion", "limite": 5}))

    exacto = match.create_trajectory_match_evaluator(tool_args_match_mode="exact")
    assert exacto(outputs=sal, reference_outputs=ref)["score"] is False

    # El override por lista de claves compara solo lo determinista.
    solo_limite = match.create_trajectory_match_evaluator(
        tool_args_match_overrides={"buscar": ["limite"]})
    assert solo_limite(outputs=sal, reference_outputs=ref)["score"] is True

    # …y sigue detectando el argumento numérico equivocado.
    mal = _traza(("buscar", {"consulta": "tickets criticos facturacion", "limite": 500}))
    assert solo_limite(outputs=mal, reference_outputs=ref)["score"] is False


def test_la_trayectoria_de_grafo_registra_las_interrupciones():
    """Una invariante de negocio comprobada sobre el flujo, no sobre el texto."""
    utils = pytest.importorskip("agentevals.graph_trajectory.utils")
    from langgraph.types import Command, interrupt
    from typing_extensions import TypedDict as TD

    class EstadoGasto(TD):
        importe: float
        decision: str

    def analizar(estado):
        return {}

    def aprobar(estado):
        return {"decision": interrupt({"importe": estado["importe"]})}

    def ejecutar(estado):
        return {}

    flujo = (StateGraph(EstadoGasto)
             .add_node("analizar", analizar)
             .add_node("aprobacion", aprobar)
             .add_node("ejecutar", ejecutar)
             .add_edge(START, "analizar")
             .add_conditional_edges(
                 "analizar",
                 lambda e: "aprobacion" if e["importe"] > 1000 else "ejecutar",
                 ["aprobacion", "ejecutar"])
             .add_edge("aprobacion", "ejecutar")
             .add_edge("ejecutar", END)
             .compile(checkpointer=InMemorySaver()))

    def pasos_de(importe, hilo):
        cfg = {"configurable": {"thread_id": hilo}}
        flujo.invoke({"importe": importe, "decision": ""}, cfg)
        if flujo.get_state(cfg).next:
            flujo.invoke(Command(resume="aprobado"), cfg)
        traza = utils.extract_langgraph_trajectory_from_thread(flujo, cfg)
        return traza["outputs"]["steps"]

    def hubo_aprobacion(pasos):
        return any("__interrupt__" in turno for turno in pasos)

    # Los casos límite, que son los que detectan un `>` escrito donde iba un `>=`.
    assert hubo_aprobacion(pasos_de(1001, "caro"))
    assert hubo_aprobacion(pasos_de(25_000, "carisimo"))
    assert not hubo_aprobacion(pasos_de(999, "justo-debajo"))
    assert not hubo_aprobacion(pasos_de(50, "barato"))


# ======================================================================================
# Notebook 28 · desplegar sobre un sistema vivo
# ======================================================================================
def _flujo_con_aprobacion(almacen, nombre_nodo: str):
    """El mismo flujo; entre versiones solo cambia el nombre del nodo de aprobación."""
    from langgraph.types import interrupt
    from typing_extensions import TypedDict as TD

    class EstadoGasto(TD):
        pasos: Annotated[list[str], operator.add]
        decision: str

    def analizar(estado):
        return {"pasos": ["analizar"]}

    def aprobar(estado):
        return {"decision": interrupt({"p": "?"}), "pasos": ["aprobar"]}

    def ejecutar(estado):
        return {"pasos": ["ejecutar"]}

    return (StateGraph(EstadoGasto)
            .add_node("analizar", analizar)
            .add_node(nombre_nodo, aprobar)
            .add_node("ejecutar", ejecutar)
            .add_edge(START, "analizar")
            .add_edge("analizar", nombre_nodo)
            .add_edge(nombre_nodo, "ejecutar")
            .add_edge("ejecutar", END)
            .compile(checkpointer=almacen))


def test_quitar_un_campo_del_esquema_lo_hace_invisible():
    """El campo no da error ni queda a None: desaparece de `values`."""
    from typing_extensions import TypedDict as TD

    con = sqlite3.connect(":memory:", check_same_thread=False)
    almacen = SqliteSaver(con)

    class V1(TD):
        contador: Annotated[int, operator.add]
        campo_viejo: str

    class V2(TD):
        contador: Annotated[int, operator.add]
        campo_nuevo: str

    def construir(esquema, salida):
        return (StateGraph(esquema).add_node("p", lambda e: salida)
                .add_edge(START, "p").add_edge("p", END).compile(checkpointer=almacen))

    cfg = {"configurable": {"thread_id": "h"}}
    v1 = construir(V1, {"contador": 1, "campo_viejo": "dato"})
    v1.invoke({"contador": 0, "campo_viejo": ""}, cfg)
    assert v1.get_state(cfg).values["campo_viejo"] == "dato"

    v2 = construir(V2, {"contador": 1, "campo_nuevo": "otro"})
    assert "campo_viejo" not in v2.get_state(cfg).values
    v2.invoke({}, cfg)                      # y la ejecución sigue funcionando


def test_renombrar_un_nodo_abandona_los_hilos_parados_en_el():
    """El fallo más grave del módulo 7, fijado como prueba.

    Si algún día LangGraph empieza a lanzar una excepción aquí, es una gran noticia y hay
    que reescribir la sección 3 del notebook 28.
    """
    from langgraph.types import Command

    con = sqlite3.connect(":memory:", check_same_thread=False)
    almacen = SqliteSaver(con)
    cfg = {"configurable": {"thread_id": "gasto"}}

    vieja = _flujo_con_aprobacion(almacen, "aprobar")
    vieja.invoke({"pasos": [], "decision": ""}, cfg)
    assert vieja.get_state(cfg).next == ("aprobar",)

    nueva = _flujo_con_aprobacion(almacen, "aprobacion_humana")
    resultado = nueva.invoke(Command(resume="sí"), cfg)      # no lanza nada

    assert resultado["decision"] == "", "la aprobación debería haberse perdido"
    assert "ejecutar" not in resultado["pasos"], "el flujo no debería haber continuado"
    assert nueva.get_state(cfg).next == (), "el hilo queda marcado como terminado"


def test_los_hilos_parados_solo_se_ven_con_el_grafo_desplegado():
    """La trampa de la comprobación previa: con el candidato salen cero."""
    con = sqlite3.connect(":memory:", check_same_thread=False)
    almacen = SqliteSaver(con)

    produccion = _flujo_con_aprobacion(almacen, "aprobar")
    for i in range(3):
        produccion.invoke({"pasos": [], "decision": ""},
                          {"configurable": {"thread_id": f"g{i}"}})
    candidata = _flujo_con_aprobacion(almacen, "aprobacion_humana")

    def parados(app):
        return {t for (t,) in con.execute("SELECT DISTINCT thread_id FROM checkpoints")
                if app.get_state({"configurable": {"thread_id": t}}).next}

    assert len(parados(produccion)) == 3, "con el grafo desplegado se ven los 3"
    assert parados(candidata) == set(), "con el candidato no se ve ninguno"


def test_un_alias_del_nodo_viejo_salva_los_hilos_parados():
    """La solución barata: conservar el nombre antiguo durante un despliegue."""
    from langgraph.types import Command, interrupt
    from typing_extensions import TypedDict as TD

    class EstadoGasto(TD):
        pasos: Annotated[list[str], operator.add]
        decision: str

    def analizar(estado):
        return {"pasos": ["analizar"]}

    def aprobar(estado):
        return {"decision": interrupt({"p": "?"}), "pasos": ["aprobar"]}

    def ejecutar(estado):
        return {"pasos": ["ejecutar"]}

    con = sqlite3.connect(":memory:", check_same_thread=False)
    almacen = SqliteSaver(con)
    cfg = {"configurable": {"thread_id": "con-alias"}}

    _flujo_con_aprobacion(almacen, "aprobar").invoke({"pasos": [], "decision": ""}, cfg)

    con_alias = (StateGraph(EstadoGasto)
                 .add_node("analizar", analizar)
                 .add_node("aprobacion_humana", aprobar)
                 .add_node("aprobar", aprobar)          # alias para los hilos vivos
                 .add_node("ejecutar", ejecutar)
                 .add_edge(START, "analizar")
                 .add_edge("analizar", "aprobacion_humana")
                 .add_edge("aprobacion_humana", "ejecutar")
                 .add_edge("aprobar", "ejecutar")
                 .add_edge("ejecutar", END)
                 .compile(checkpointer=almacen))

    resultado = con_alias.invoke(Command(resume="sí, apruebo"), cfg)
    assert resultado["decision"] == "sí, apruebo"
    assert "ejecutar" in resultado["pasos"]


def test_update_state_as_node_rescata_un_hilo_abandonado():
    from langgraph.types import Command

    con = sqlite3.connect(":memory:", check_same_thread=False)
    almacen = SqliteSaver(con)
    cfg = {"configurable": {"thread_id": "rescate"}}

    _flujo_con_aprobacion(almacen, "aprobar").invoke({"pasos": [], "decision": ""}, cfg)
    nueva = _flujo_con_aprobacion(almacen, "aprobacion_humana")

    nueva.update_state(cfg, {"decision": "migrado", "pasos": ["aprobar"]},
                       as_node="aprobacion_humana")
    assert nueva.get_state(cfg).next == ("ejecutar",)
    assert "ejecutar" in nueva.invoke(None, cfg)["pasos"]


# ======================================================================================
# Notebook 29 · límites, colas e incidentes
# ======================================================================================
def test_el_limitador_arranca_con_el_cubo_vacio():
    """`max_bucket_size` gobierna la ráfaga tras un reposo, no al arrancar.

    Es lo contrario de lo que sugiere el nombre, y explica por qué un pod recién arrancado
    está limitado desde la primera petición.
    """
    from langchain_core.rate_limiters import InMemoryRateLimiter

    limitador = InMemoryRateLimiter(requests_per_second=20, check_every_n_seconds=0.005,
                                    max_bucket_size=5)
    assert limitador.available_tokens == 0.0

    inicio = time.monotonic()
    for _ in range(3):
        limitador.acquire()
    transcurrido = time.monotonic() - inicio

    # Si el cubo arrancara lleno, las 3 saldrían instantáneas (< 0,01 s).
    assert transcurrido > 0.10, "el cubo parece arrancar lleno; revisar el notebook 29"


def test_el_limitador_permite_rafaga_tras_un_reposo():
    from langchain_core.rate_limiters import InMemoryRateLimiter

    limitador = InMemoryRateLimiter(requests_per_second=50, check_every_n_seconds=0.005,
                                    max_bucket_size=5)
    limitador.acquire()
    time.sleep(0.3)                       # a 50 rps, de sobra para llenar el cubo

    inicio = time.monotonic()
    for _ in range(5):
        limitador.acquire()
    assert time.monotonic() - inicio < 0.05, "tras el reposo debería haber ráfaga"


def test_el_limitador_se_comparte_entre_hilos_del_proceso():
    """Es por proceso: protege de tu propio paralelismo, no del de tus réplicas."""
    from langchain_core.rate_limiters import InMemoryRateLimiter

    limitador = InMemoryRateLimiter(requests_per_second=20, check_every_n_seconds=0.005,
                                    max_bucket_size=1)
    inicio = time.monotonic()

    def pedir():
        for _ in range(3):
            limitador.acquire()

    hilos = [threading.Thread(target=pedir) for _ in range(3)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    # 9 peticiones a 20 rps ≈ 0,45 s. Si cada hilo tuviera su cubo, sería ~0,15 s.
    assert time.monotonic() - inicio > 0.30


def test_sin_jitter_los_reintentos_se_sincronizan():
    """El rebaño atronador, fijado como prueba."""
    import collections
    import random

    def simular(jitter: str) -> collections.Counter:
        azar = random.Random(42)
        franjas: collections.Counter = collections.Counter()
        for _ in range(200):
            instante = 0.0
            for intento in range(4):
                espera = 0.5 * (2 ** intento)
                if jitter == "mitad":
                    espera = espera / 2 + azar.uniform(0, espera / 2)
                instante += espera
                franjas[round(instante / 0.25)] += 1
        return franjas

    sin_jitter = simular("no")
    con_jitter = simular("mitad")

    assert max(sin_jitter.values()) == 200, "sin jitter deberían coincidir los 200"
    assert len(sin_jitter) == 4, "sin jitter solo hay 4 momentos distintos"
    assert max(con_jitter.values()) < 200 / 1.5, "el jitter debería repartir el pico"
    assert len(con_jitter) > 4 * 3, "el jitter debería multiplicar los momentos distintos"


def test_el_semaforo_evita_los_rechazos_por_concurrencia():
    import asyncio

    class Proveedor:
        def __init__(self, maximo):
            self.maximo, self.en_vuelo, self.rechazos = maximo, 0, 0

        async def llamar(self):
            self.en_vuelo += 1
            try:
                if self.en_vuelo > self.maximo:
                    self.rechazos += 1
                    raise RuntimeError("429")
                await asyncio.sleep(0.01)
            finally:
                self.en_vuelo -= 1

    async def correr(permitidas: int | None) -> int:
        proveedor = Proveedor(maximo=8)
        sem = asyncio.Semaphore(permitidas) if permitidas else None

        async def una():
            if sem is None:
                try:
                    await proveedor.llamar()
                except RuntimeError:
                    pass
                return
            async with sem:
                try:
                    await proveedor.llamar()
                except RuntimeError:
                    pass

        await asyncio.gather(*(una() for _ in range(40)))
        return proveedor.rechazos

    assert asyncio.run(correr(None)) > 20, "sin semáforo deberían llover los 429"
    assert asyncio.run(correr(8)) == 0, "con semáforo no debería haber ninguno"


def test_el_barredor_no_toca_los_hilos_que_esperan_a_un_humano():
    """La precaución que hace seguro al barredor del notebook 29."""
    from langgraph.types import Command, interrupt
    from typing_extensions import TypedDict as TD

    class E(TD):
        pasos: Annotated[list[str], operator.add]
        decision: str

    def clasificar(estado):
        return {"pasos": ["clasificar"]}

    def aprobar(estado):
        return {"decision": interrupt({"p": "?"}), "pasos": ["aprobar"]}

    def resolver(estado):
        return {"pasos": ["resolver"]}

    con = sqlite3.connect(":memory:", check_same_thread=False)
    app = (StateGraph(E).add_node("clasificar", clasificar).add_node("aprobar", aprobar)
           .add_node("resolver", resolver).add_edge(START, "clasificar")
           .add_edge("clasificar", "aprobar").add_edge("aprobar", "resolver")
           .add_edge("resolver", END).compile(checkpointer=SqliteSaver(con)))

    # Uno esperando a un humano y otro cortado tras la aprobación.
    esperando = {"configurable": {"thread_id": "espera"}}
    app.invoke({"pasos": [], "decision": ""}, esperando)

    cortado = {"configurable": {"thread_id": "cortado"}}
    app.invoke({"pasos": [], "decision": ""}, cortado)
    app.update_state(cortado, {"decision": "sí", "pasos": ["aprobar"]}, as_node="aprobar")

    def barrer(limite=50):
        reanudados = []
        for (tid,) in con.execute("SELECT DISTINCT thread_id FROM checkpoints"):
            if len(reanudados) >= limite:
                break
            cfg = {"configurable": {"thread_id": tid}}
            snap = app.get_state(cfg)
            if snap.next and not snap.interrupts:
                app.invoke(None, cfg)
                reanudados.append(tid)
        return reanudados

    assert barrer() == ["cortado"], "solo debería reanudar el huérfano"
    assert app.get_state(esperando).next == ("aprobar",), "el que espera no se toca"
    assert "resolver" in app.get_state(cortado).values["pasos"]


# ======================================================================================
# Notebook 30 · datos, dinero y cambio
# ======================================================================================
def _bytes_del_almacen(conexion: sqlite3.Connection) -> bytes:
    trozos = []
    for consulta in ("SELECT checkpoint FROM checkpoints", "SELECT value FROM writes"):
        for (valor,) in conexion.execute(consulta):
            trozos.append(valor if isinstance(valor, bytes) else str(valor).encode())
    return b"".join(trozos)


def test_pii_middleware_no_protege_el_checkpoint():
    """El hallazgo del notebook 30: redacta hacia el modelo, no hacia el disco.

    Si algún día el dato original deja de persistirse, es una gran noticia y hay que
    reescribir la sección 1 del notebook 30.
    """
    pytest.importorskip("langchain.agents.middleware")
    from langchain.agents import create_agent
    from langchain.agents.middleware import PIIMiddleware

    sys.path.insert(0, str(RAIZ / "_tools"))
    import modelo_falso

    correo = b"ana@ejemplo.com"
    con = sqlite3.connect(":memory:", check_same_thread=False)
    agente = create_agent(
        model=modelo_falso.FakeChat(),
        tools=[],
        middleware=[PIIMiddleware("email", strategy="redact", apply_to_input=True)],
        checkpointer=SqliteSaver(con),
    )
    resultado = agente.invoke(
        {"messages": [{"role": "user", "content": "mi correo es ana@ejemplo.com"}]},
        {"configurable": {"thread_id": "t"}})

    assert "[REDACTED_EMAIL]" in resultado["messages"][0].content, "el estado sí se redacta"
    assert correo in _bytes_del_almacen(con), "pero el original sigue en el checkpoint"


def test_redactar_en_el_borde_si_protege_el_checkpoint():
    import re

    from langchain.agents import create_agent

    sys.path.insert(0, str(RAIZ / "_tools"))
    import modelo_falso

    con = sqlite3.connect(":memory:", check_same_thread=False)
    agente = create_agent(model=modelo_falso.FakeChat(), tools=[],
                          checkpointer=SqliteSaver(con))
    limpio = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[correo]", "mi correo es ana@ejemplo.com")
    agente.invoke({"messages": [{"role": "user", "content": limpio}]},
                  {"configurable": {"thread_id": "t"}})

    assert b"ana@ejemplo.com" not in _bytes_del_almacen(con)


def _grafo_con_metadata(almacen):
    from typing_extensions import TypedDict as TD

    class E(TD):
        pasos: Annotated[list[str], operator.add]

    return (StateGraph(E).add_node("n", lambda e: {"pasos": ["x"]})
            .add_edge(START, "n").add_edge("n", END).compile(checkpointer=almacen))


def test_la_metadata_del_config_se_persiste_y_es_filtrable():
    """Sin esto no hay borrado por usuario posible."""
    con = sqlite3.connect(":memory:", check_same_thread=False)
    almacen = SqliteSaver(con)
    app = _grafo_con_metadata(almacen)

    for usuario, hilos in {"u-ana": ["h1", "h2"], "u-luis": ["h3"]}.items():
        for h in hilos:
            app.invoke({"pasos": []},
                       {"configurable": {"thread_id": h}, "metadata": {"id_usuario": usuario}})

    def hilos_de(usuario):
        return sorted({t.config["configurable"]["thread_id"]
                       for t in almacen.list(None, filter={"id_usuario": usuario})})

    assert hilos_de("u-ana") == ["h1", "h2"]
    assert hilos_de("u-luis") == ["h3"]

    # Y la trampa: en SQLite la metadata NO es texto plano, así que `LIKE` no la encuentra.
    por_like = con.execute(
        "SELECT DISTINCT thread_id FROM checkpoints WHERE metadata LIKE ?",
        ("%u-ana%",)).fetchall()
    assert por_like == [], "si esto deja de estar vacío, revisar la sección 2 del nb 30"


def test_delete_thread_limpia_checkpoints_y_writes():
    con = sqlite3.connect(":memory:", check_same_thread=False)
    almacen = SqliteSaver(con)
    app = _grafo_con_metadata(almacen)

    for h in ("h1", "h2"):
        app.invoke({"pasos": []},
                   {"configurable": {"thread_id": h}, "metadata": {"id_usuario": "u-ana"}})
    app.invoke({"pasos": []},
               {"configurable": {"thread_id": "h3"}, "metadata": {"id_usuario": "u-luis"}})

    almacen.delete_thread("h1")
    almacen.delete_thread("h2")

    quedan_cp = {t for (t,) in con.execute("SELECT DISTINCT thread_id FROM checkpoints")}
    quedan_w = {t for (t,) in con.execute("SELECT DISTINCT thread_id FROM writes")}
    assert quedan_cp == {"h3"}, "no debe quedar ningún checkpoint del usuario borrado"
    assert quedan_w == {"h3"}, "tampoco writes: por eso no se borra con SQL a mano"


def test_el_reparto_del_canario_es_estable_y_monotono():
    """Con `random()` el mismo usuario alternaría de versión en cada petición."""
    import hashlib

    def reparto(id_usuario: str, porcentaje: int) -> bool:
        posicion = int(hashlib.sha256(id_usuario.encode()).hexdigest()[:8], 16) % 100
        return posicion < porcentaje

    usuarios = [f"u-{i}" for i in range(1000)]

    # Estable: la misma entrada da siempre lo mismo.
    assert all(reparto(u, 10) == reparto(u, 10) for u in usuarios)

    # Monótono: quien entra al 1 % sigue dentro al 10 % y al 50 %.
    en_el_uno = [u for u in usuarios if reparto(u, 1)]
    assert en_el_uno, "con 1000 usuarios debería haber alguno en el 1 %"
    assert all(reparto(u, 10) and reparto(u, 50) for u in en_el_uno)

    # Y el reparto se acerca al porcentaje pedido.
    assert 5 <= sum(reparto(u, 10) for u in usuarios) / 10 <= 15


def test_el_coste_separa_los_tokens_cacheados():
    """Sin separarlos, la contabilidad y la factura no cuadran."""
    precios = {"entrada": 0.15, "entrada_cacheada": 0.075, "salida": 0.60}

    def coste(uso: dict) -> float:
        cacheados = (uso.get("input_token_details") or {}).get("cache_read", 0)
        entrada = uso["input_tokens"] - cacheados
        return (entrada * precios["entrada"] + cacheados * precios["entrada_cacheada"]
                + uso["output_tokens"] * precios["salida"]) / 1e6

    con_cache = {"input_tokens": 120_000, "output_tokens": 2_000,
                 "input_token_details": {"cache_read": 100_000}}
    sin_cache = {"input_tokens": 120_000, "output_tokens": 2_000, "input_token_details": {}}

    assert coste(con_cache) < coste(sin_cache)
    assert coste(sin_cache) / coste(con_cache) > 1.5
