"""Pruebas de las invariantes que enseña el módulo 1.

No prueban el SDK de LangSmith —eso es trabajo de sus autores— sino **las afirmaciones
que hace el material**. Si una deja de ser cierta al actualizar el SDK, el notebook
pasa a mentir y esto es lo que lo detecta.
"""

from __future__ import annotations

import time

from langsmith import RunTree, traceable

from utils import curso


# ------------------------------------------------------------------------------------
# Notebook 01 · dotted_order
# ------------------------------------------------------------------------------------


def test_la_profundidad_es_contar_puntos():
    @traceable
    def nieto():
        return 1

    @traceable
    def hijo():
        return nieto()

    @traceable
    def padre():
        return hijo()

    with curso.traza_local() as t:
        padre()

    base = min(r.dotted_order.count(".") for _, r in t.recorrer())
    for profundidad, run in t.recorrer():
        assert run.dotted_order.count(".") - base == profundidad


def test_el_arbol_se_reconstruye_desde_una_lista_desordenada():
    """La demostración central del notebook 01, como prueba."""
    import random

    @traceable(run_type="tool")
    def a():
        return 1

    @traceable(run_type="tool")
    def b():
        return 2

    @traceable(run_type="llm")
    def c():
        return a() + b()

    @traceable(run_type="chain")
    def raiz():
        return c()

    with curso.traza_local() as t:
        raiz()

    planos = [r for _, r in t.recorrer()]
    random.Random(7).shuffle(planos)

    orden = [r.name for r in sorted(planos, key=lambda r: r.dotted_order)]
    assert orden == ["raiz", "c", "a", "b"]


def test_el_subarbol_es_una_comparacion_de_prefijos():
    @traceable
    def hoja():
        return 1

    @traceable
    def rama():
        return hoja()

    @traceable
    def otra_rama():
        return 2

    @traceable
    def raiz():
        rama()
        return otra_rama()

    with curso.traza_local() as t:
        raiz()

    planos = [r for _, r in t.recorrer()]
    prefijo = next(r for r in planos if r.name == "rama").dotted_order
    subarbol = {r.name for r in planos if r.dotted_order.startswith(prefijo)}
    assert subarbol == {"rama", "hoja"}      # `otra_rama` queda fuera


# ------------------------------------------------------------------------------------
# Notebook 01 · errores silenciosos
# ------------------------------------------------------------------------------------


def test_una_excepcion_capturada_queda_registrada_en_el_hijo():
    """La afirmación con más valor práctico del notebook 01.

    El padre figura como correcto y el hijo como error. Las dos cosas a la vez, y las
    dos son verdad: la petición se atendió y por dentro algo se rompió.
    """

    @traceable(run_type="tool")
    def falla():
        raise ConnectionError("503")

    @traceable(run_type="chain")
    def con_plan_b():
        try:
            return falla()
        except ConnectionError:
            return "degradado"

    with curso.traza_local() as t:
        assert con_plan_b() == "degradado"

    raiz = t.principales[0]
    hijo = raiz.child_runs[0]
    assert raiz.error is None
    assert raiz.outputs == {"output": "degradado"}
    assert hijo.error is not None
    assert "503" in hijo.error


def test_una_excepcion_que_se_propaga_marca_toda_la_rama():
    @traceable
    def falla():
        raise ValueError("boom")

    @traceable
    def sin_plan_b():
        return falla()

    with curso.traza_local() as t:
        try:
            sin_plan_b()
        except ValueError:
            pass

    assert all(run.error is not None for _, run in t.recorrer())


# ------------------------------------------------------------------------------------
# Notebook 01 · herencia de etiquetas y metadatos
# ------------------------------------------------------------------------------------


def test_las_etiquetas_y_los_metadatos_bajan_a_los_hijos():
    """Por esto se instrumenta el punto de entrada y no cada nodo."""

    @traceable(tags=["herramienta"])
    def hijo():
        return 1

    @traceable(tags=["soporte"], metadata={"version": "v2"})
    def padre():
        return hijo()

    with curso.traza_local() as t:
        padre()

    p = t.principales[0]
    h = p.child_runs[0]
    assert p.tags == ["soporte"]
    assert h.tags == ["soporte", "herramienta"]
    assert h.extra["metadata"]["version"] == "v2"


def test_langsmith_extra_inyecta_metadatos_en_tiempo_de_llamada():
    @traceable
    def hijo():
        return 1

    @traceable
    def padre():
        return hijo()

    with curso.traza_local() as t:
        padre(langsmith_extra={"metadata": {"ticket": "TCK-0001"}, "tags": ["urgente"]})

    for _, run in t.recorrer():
        assert run.extra["metadata"]["ticket"] == "TCK-0001"
        assert "urgente" in run.tags


# ------------------------------------------------------------------------------------
# Notebook 01 · trazado distribuido
# ------------------------------------------------------------------------------------


def test_las_cabeceras_cosen_una_traza_entre_dos_procesos():
    a = RunTree(name="servicio-a", run_type="chain", inputs={})
    b = RunTree.from_headers(a.to_headers(), name="servicio-b", run_type="chain", inputs={})

    assert b is not None
    assert b.trace_id == a.trace_id
    assert b.dotted_order.startswith(a.dotted_order)


# ------------------------------------------------------------------------------------
# Notebook 01 · run_type
# ------------------------------------------------------------------------------------


def test_el_run_type_se_conserva_tal_cual():
    """El SDK no valida el run_type: lo que pongas es lo que llega.

    Es justo la razón de que equivocarlo no dé ningún error, solo un panel de coste
    vacío. La prueba fija ese comportamiento para que el notebook pueda afirmarlo.
    """

    @traceable(run_type="chain")           # una llamada al modelo mal etiquetada
    def modelo_mal():
        return "respuesta"

    @traceable(run_type="llm")
    def modelo_bien():
        return "respuesta"

    with curso.traza_local() as t:
        modelo_mal()
        modelo_bien()

    tipos = {r.name: r.run_type for _, r in t.recorrer()}
    assert tipos == {"modelo_mal": "chain", "modelo_bien": "llm"}


# ------------------------------------------------------------------------------------
# Notebook 01 · tiempos
# ------------------------------------------------------------------------------------


def test_los_tiempos_permiten_repartir_la_latencia():
    @traceable
    def lento():
        time.sleep(0.03)
        return 1

    @traceable
    def rapido():
        return 2

    @traceable
    def raiz():
        lento()
        return rapido()

    with curso.traza_local() as t:
        raiz()

    def duracion(r):
        return (r.end_time - r.start_time).total_seconds()

    total = duracion(t.principales[0])
    parcial = duracion(next(r for _, r in t.recorrer() if r.name == "lento"))
    assert 0.5 < parcial / total <= 1.0
