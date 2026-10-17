"""Pruebas del módulo 5: organización, accesos, retención y borrado.

Casi todo lo que enseña este módulo son **ausencias**: lo que el SDK no tiene, lo que no
se puede borrar, lo que no se puede configurar desde el código. Y una ausencia es
exactamente lo que se rompe en silencio cuando el SDK añade la funcionalidad: el material
pasa de ser cierto a ser mentira sin que falle nada.

De ahí que estas pruebas afirmen las ausencias tanto como las presencias. Si alguna falla
porque LangSmith ha añadido `delete_run` o un recurso de organizaciones, la prueba está
haciendo su trabajo: hay que reescribir el notebook, no relajar la aserción.
"""

from __future__ import annotations

import datetime
import inspect
import os
import time
import uuid
import warnings

import pytest


# ------------------------------------------------------------------------------------
# Notebook 16 · organización y accesos
# ------------------------------------------------------------------------------------


def _cliente_mudo():
    from langsmith import Client

    from utils.curso import _SesionMuda

    return Client(api_key="local", session=_SesionMuda(), auto_batch_tracing=False)


def test_el_sdk_no_tiene_gobierno(sin_servicio):
    """El argumento del apartado 1: ni organizaciones, ni espacios, ni roles, ni
    usuarios, ni claves, ni auditoría. Si algún día aparecen, el notebook miente."""
    api = _cliente_mudo()._get_langsmith_api()
    recursos = {n for n in dir(api) if not n.startswith("_")}

    for concepto in ("organization", "workspace", "role", "member", "audit"):
        assert not [r for r in recursos if concepto in r], concepto

    # Y lo que sí hay, que es de datos y no de gobierno.
    assert {"runs", "traces", "threads", "datasets"} <= recursos


def test_el_espacio_de_trabajo_viaja_como_cabecera(sin_servicio):
    """`LANGSMITH_WORKSPACE_ID` -> `X-Tenant-Id`, y solo si está puesta. Es lo que decide
    a qué datos llega una clave de servicio."""
    import langsmith.utils as lu

    def cabeceras(espacio):
        os.environ.pop("LANGSMITH_WORKSPACE_ID", None)
        if espacio:
            os.environ["LANGSMITH_WORKSPACE_ID"] = espacio
        lu.get_env_var.cache_clear()
        try:
            return dict(_cliente_mudo()._headers)
        finally:
            os.environ.pop("LANGSMITH_WORKSPACE_ID", None)
            lu.get_env_var.cache_clear()

    assert "X-Tenant-Id" not in cabeceras(None)
    assert cabeceras("abc-123")["X-Tenant-Id"] == "abc-123"


def test_la_clave_no_se_ve_en_repr_pero_si_en_las_cabeceras(sin_servicio):
    """El reparto que el notebook mide: el SDK protege lo que se imprime por accidente y
    no protege los dos sitios a los que llegarías depurando."""
    from langsmith import Client

    from utils.curso import _SesionMuda

    secreta = "lsv2_pt_MARCA_UNICA_DE_LA_PRUEBA"
    c = Client(api_key=secreta, session=_SesionMuda(), auto_batch_tracing=False)

    assert secreta not in repr(c)
    assert secreta not in str(c)
    assert c.api_key == secreta                       # sí se ve
    assert secreta in str(dict(c._headers))           # y aquí también


def test_compartir_una_traza_no_pasa_por_ningun_permiso(sin_servicio):
    """La API de compartir existe, devuelve una URL, y no recibe ni usuario ni rol ni
    espacio: por eso el enlace funciona para cualquiera que lo tenga."""
    from langsmith import Client

    firma = inspect.signature(Client.share_run)
    assert set(firma.parameters) == {"self", "run_id", "share_id"}
    assert "str" in str(firma.return_annotation)      # una URL, no un permiso

    # Y la asimetría del notebook: se comparte por run, se retira por traza.
    c = _cliente_mudo()
    assert "run_id" in inspect.signature(c.runs.share.create).parameters
    assert "trace_id" in inspect.signature(c.runs.share.delete).parameters


def test_la_api_vieja_de_compartir_avisa_al_llamarla(sin_servicio):
    """El aviso solo salta al llamar, no al leer la firma — que es justo por lo que se
    cuela en el código de alguien durante dos años."""
    c = _cliente_mudo()

    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        try:
            c.share_run(str(uuid.uuid4()))
        except Exception:
            pass

    mensajes = [str(a.message) for a in avisos if issubclass(a.category, DeprecationWarning)]
    assert any("share_run" in m and "runs.share.create" in m for m in mensajes), mensajes


def test_la_revision_de_claves_marca_la_de_servicio_parada():
    """La revisión trimestral del notebook: una clave de servicio olvidada es la peor de
    todas, porque su alcance es la organización entera."""
    hoy = datetime.date(2026, 8, 31)

    def revisar(inventario, *, dias_sin_uso=90, dias_de_vida=180):
        avisos = []
        for clave in inventario:
            sin_usar = (hoy - datetime.date.fromisoformat(clave["ultimo_uso"])).days
            edad = (hoy - datetime.date.fromisoformat(clave["creada"])).days
            if sin_usar > dias_sin_uso:
                avisos.append((clave["nombre"], "sin usar"))
            if edad > dias_de_vida and sin_usar <= dias_sin_uso:
                avisos.append((clave["nombre"], "rotar"))
            if clave["tipo"] == "servicio" and sin_usar > 30:
                avisos.append((clave["nombre"], "servicio parada"))
        return avisos

    inventario = [
        {"nombre": "viva", "tipo": "espacio", "creada": "2026-08-01", "ultimo_uso": "2026-08-30"},
        {"nombre": "vieja", "tipo": "espacio", "creada": "2025-01-01", "ultimo_uso": "2026-08-30"},
        {"nombre": "olvidada", "tipo": "servicio", "creada": "2025-11-08",
         "ultimo_uso": "2025-11-09"},
    ]
    avisos = revisar(inventario)
    assert ("viva", "sin usar") not in avisos and ("viva", "rotar") not in avisos
    assert ("vieja", "rotar") in avisos
    assert ("olvidada", "sin usar") in avisos
    assert ("olvidada", "servicio parada") in avisos


# ------------------------------------------------------------------------------------
# Notebook 17 · retención y cumplimiento
# ------------------------------------------------------------------------------------


def test_la_realimentacion_asciende_la_traza_por_defecto():
    """El hallazgo central del notebook 17: dejar realimentación extiende la retención
    de la traza **como efecto secundario**, y el valor por defecto es True. Afecta a todo
    el módulo 3 y al juez en línea del notebook 14."""
    from langsmith import Client
    from langsmith.schemas import FeedbackCreate

    assert inspect.signature(Client.create_feedback).parameters[
        "extend_trace_retention"].default is True
    assert FeedbackCreate.model_fields["extend_trace_retention"].default is True

    # Y el SDK lo dice con esas palabras, no es una interpretación del curso.
    fuente = inspect.getsource(FeedbackCreate)
    assert "extend trace retention as a side effect" in fuente


def test_el_campo_de_retencion_viaja_en_cada_peticion_de_realimentacion(sin_servicio):
    """No basta con que el parámetro exista: hay que ver que llega al servidor, porque
    el notebook afirma que va en TODAS las realimentaciones."""
    from utils.curso import servicio_simulado

    for valor in (True, False):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with servicio_simulado() as servicio:
                run_id = uuid.uuid4()
                servicio.cliente.create_feedback(
                    run_id, key="correcto", score=1, trace_id=run_id,
                    session_id=uuid.uuid4(), extend_trace_retention=valor)
                time.sleep(0.3)
                assert servicio.recibidos, "no llegó la realimentación"
                assert servicio.recibidos[0]["extend_trace_retention"] is valor


def test_la_variable_con_ttl_no_es_retencion():
    """La trampa del apartado 2: la única variable del SDK con «TTL» en el nombre es la
    memoria del exportador de OTEL, no cuánto se guardan tus datos."""
    from langsmith._internal.otel import _otel_exporter

    documentacion = inspect.getdoc(_otel_exporter.OTELExporter.__init__)
    assert "incomplete traces" in documentacion
    assert "LANGSMITH_OTEL_SPAN_TTL_SECONDS" in documentacion
    assert "3600" in documentacion


def test_no_se_puede_borrar_una_traza():
    """La ausencia que decide el diseño de cumplimiento entero. Si algún día aparece
    `delete_run`, esta prueba falla y hay que reescribir medio notebook 17."""
    from langsmith import Client

    assert not hasattr(Client, "delete_run")
    assert not hasattr(Client, "delete_trace")
    assert not hasattr(Client, "delete_runs")

    # La unidad de borrado es el proyecto, y eso sí existe.
    assert hasattr(Client, "delete_project")

    # Tampoco está en los recursos nuevos: `_delete` es el verbo HTTP, no un método.
    c = _cliente_mudo()
    for recurso in ("runs", "traces", "threads", "public", "datasets"):
        objeto = getattr(c, recurso)
        assert not [n for n in dir(objeto) if "delete" in n and not n.startswith("_")], recurso


def test_borrar_ejemplos_es_blando_por_defecto():
    """Un borrado que no borra es peor que no borrar, si lo haces para cumplir con una
    solicitud de supresión."""
    from langsmith import Client

    parametro = inspect.signature(Client.delete_examples).parameters["hard_delete"]
    assert parametro.default is False
    assert "soft delete" in inspect.getdoc(Client.delete_examples)


def test_el_plan_de_supresion_solo_falla_en_el_caso_habitual():
    """La tabla del apartado 4: hay cuatro maneras de poder borrar y la única que sale
    gratis se decide antes de escribir la primera traza."""

    def plan(*, hay_anonimizador, hay_tabla_de_seudonimos, proyectos_por_cliente,
             dias_de_retencion):
        if hay_anonimizador or hay_tabla_de_seudonimos or proyectos_por_cliente:
            return True
        return dias_de_retencion <= 30

    base = dict(hay_anonimizador=False, hay_tabla_de_seudonimos=False,
                proyectos_por_cliente=False, dias_de_retencion=400)

    assert plan(**{**base, "hay_anonimizador": True})
    assert plan(**{**base, "hay_tabla_de_seudonimos": True})
    assert plan(**{**base, "proyectos_por_cliente": True})
    assert plan(**{**base, "dias_de_retencion": 14})
    assert not plan(**base)          # el caso habitual, y el que no tiene salida
