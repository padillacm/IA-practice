"""Pruebas del LangSmith simulado y de los bugs que destapó.

Este fichero existe por una razón concreta: durante casi todo el curso, las celdas
`@online` estaban escritas contra la firma verificada de cada función pero **nunca se
habían ejecutado**. Al ejecutarlas contra `utils/langsmith_de_mentira.py` aparecieron
cinco errores reales que ninguna validación estática podía ver, porque los símbolos
existían y los argumentos tenían el nombre correcto: lo que estaba mal era el **tipo**
o la **forma del objeto devuelto**.

Cada uno tiene aquí su prueba. No vigilan el material —de eso se encarga la etapa
`--simulado` de la CI— sino la propiedad del SDK que hacía que el material fuese falso.
Si alguna falla, es que el SDK cambió y hay que volver a mirar el notebook.
"""

from __future__ import annotations

import inspect

import pytest


def _cliente_simulado():
    from utils.curso import cliente, servicio_de_mentira

    return cliente(), servicio_de_mentira()


@pytest.fixture
def simulado(monkeypatch):
    """Enciende el modo simulado y lo apaga al terminar."""
    import utils.curso as curso

    monkeypatch.setenv(curso.VARIABLE_DE_SIMULACION, "1")
    monkeypatch.setattr(curso, "_SIMULADO", None)
    yield
    monkeypatch.setattr(curso, "_SIMULADO", None)


# ------------------------------------------------------------------------------------
# El mecanismo
# ------------------------------------------------------------------------------------


def test_en_simulacion_hay_servicio_y_el_cliente_habla_con_el_de_mentira(simulado):
    """El modo simulado tiene que ser indistinguible para el notebook: `hay_servicio()`
    dice que sí y `cliente()` devuelve algo que responde."""
    from utils.curso import hay_servicio, simulando

    assert simulando() and hay_servicio()

    c, servicio = _cliente_simulado()
    d = c.create_dataset("conjunto-de-prueba")
    assert d.name == "conjunto-de-prueba"
    assert ("POST", "/datasets") in servicio.peticiones


def test_en_simulacion_un_fallo_se_propaga(simulado):
    """Es la razón de ser del modo: si `@online` se tragara los errores como en el modo
    en línea, la CI no vería nada y esto no serviría para nada."""
    from utils.curso import online

    with pytest.raises(ZeroDivisionError):
        @online("un bloque que revienta", trazas=0)
        def _():
            return 1 / 0


def test_sin_simulacion_un_fallo_no_tumba_el_notebook(sin_servicio):
    """Y fuera de simulación se mantiene lo de siempre: sin clave, el bloque se salta."""
    from utils.curso import online

    testigo = []

    @online("un bloque que no debería correr", trazas=0)
    def _():
        testigo.append(1)

    assert testigo == []


def test_los_bloques_que_necesitan_un_modelo_se_saltan_y_lo_dicen(simulado, capsys):
    """El simulador simula LangSmith, no a OpenAI. Fingir que cubre esos bloques sería
    peor que declararlos."""
    from utils.curso import online

    @online("un juez de verdad", trazas=3, necesita_modelo=True)
    def _():
        raise AssertionError("no debería ejecutarse")

    salida = capsys.readouterr().out
    assert "NO se comprueba" in salida
    assert "proveedor de modelos" in salida


def test_el_simulador_intercepta_tambien_el_cliente_moderno(simulado):
    """Los accesores nuevos no usan `requests`: van por un cliente generado sobre httpx
    (y sobre un httpx **vendorizado**). Si esto deja de interceptarse, las celdas del
    notebook 14 saldrían a la red de verdad."""
    import asyncio

    c, _ = _cliente_simulado()

    async def listar():
        return [e async for e in c.evaluators.list()]

    assert asyncio.run(listar()) == []


# ------------------------------------------------------------------------------------
# Los cinco bugs que destapó
# ------------------------------------------------------------------------------------


def test_create_dataset_exige_el_enum_no_la_cadena():
    """Bug 1 (nb 06 y P2): `data_type="kv"` revienta con «'str' object has no attribute
    'value'» porque el SDK le pide `.value`. Va el enum."""
    from langsmith.schemas import DataType

    assert DataType.kv.value == "kv"
    defecto = inspect.signature(
        __import__("langsmith").Client.create_dataset).parameters["data_type"].default
    assert defecto is DataType.kv


def test_update_dataset_tag_no_admite_latest():
    """Bug 2 (nb 06 y P2): `as_of` es un `datetime`, no la cadena "latest". La
    documentación del método dice además que tiene que ser una versión EXACTA."""
    from langsmith import Client

    parametro = inspect.signature(Client.update_dataset_tag).parameters["as_of"]
    assert "datetime" in str(parametro.annotation)
    assert parametro.default is inspect.Parameter.empty        # es obligatorio
    assert "exact version" in inspect.getdoc(Client.update_dataset_tag)


def test_los_commits_listados_no_traen_etiquetas():
    """Bug 3 (nb 15): `list_prompt_commits` devuelve `ListedPromptCommit`, que **no
    tiene `tags`**. Las etiquetas viven en el repo. Por eso saber qué commit está en
    producción es `pull_prompt_commit("nombre:etiqueta")`, no filtrar una lista."""
    from langsmith.schemas import ListedPromptCommit, Prompt, PromptCommit

    assert "tags" not in ListedPromptCommit.model_fields
    assert "tags" not in PromptCommit.model_fields
    assert "tags" in Prompt.model_fields                       # aquí sí

    # Y la vía que sí funciona existe y devuelve el commit.
    from langsmith import Client

    assert "commit_hash" in PromptCommit.model_fields
    assert "prompt_identifier" in inspect.signature(Client.pull_prompt_commit).parameters


def test_los_accesores_nuevos_son_asincronos():
    """Bug 4 (nb 14): `client.evaluators.list()` no devuelve una lista con `.evaluators`
    dentro: devuelve un paginador asíncrono que se recorre con `async for`."""
    from langsmith import Client

    from utils.curso import _SesionMuda

    c = Client(api_key="local", session=_SesionMuda(), auto_batch_tracing=False)
    paginador = c.evaluators.list()
    assert hasattr(paginador, "__aiter__")
    assert not hasattr(paginador, "evaluators")


def test_un_uuid_de_mentira_no_cuela():
    """Bug 5 (nb 04): había dos huecos de texto —"<el uuid del run>"— donde iba un UUID.
    El SDK los valida, así que esas celdas no eran ejemplos: eran llamadas rotas."""
    from langsmith import Client

    from utils.curso import _SesionMuda

    c = Client(api_key="local", session=_SesionMuda(), auto_batch_tracing=False)
    with pytest.raises(Exception) as fallo:
        c.create_feedback(run_id="<el uuid del run>", key="x", score=1)
    assert "UUID" in str(fallo.value)


def test_el_recuento_de_bloques_online_del_readme_es_cierto():
    """El README dice cuántos bloques se comprueban contra el simulador y cuántos no.
    Es la afirmación más importante del documento —de ella depende cuánta fe hay que
    tenerle al curso— así que se mide en vez de mantenerse a mano."""
    import json
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parents[1]
    total = con_modelo = 0
    for cuaderno in sorted(raiz.glob("0*/*.ipynb")):
        for celda in json.load(open(cuaderno))["cells"]:
            if celda["cell_type"] != "code":
                continue
            fuente = "".join(celda["source"])
            total += fuente.count("@online")
            con_modelo += fuente.count("necesita_modelo=True")

    readme = (raiz / "README.md").read_text()
    assert f"{total - con_modelo} de {total}" in readme, (total, con_modelo)
    assert f"{con_modelo}, marcados `necesita_modelo=True`" in readme
