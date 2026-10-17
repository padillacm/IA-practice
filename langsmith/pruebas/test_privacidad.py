"""Pruebas del notebook 05: qué sale de verdad hacia el servicio.

Estas pruebas se miran distinto que las demás. Las otras vigilan que el material no
mienta; estas vigilan **una política de privacidad**, y una política de privacidad que
no está probada es una intención. El curso enseña a escribirlas justamente porque una
expresión regular golosa no falla: acierta de menos, en silencio.
"""

from __future__ import annotations

import json
import re

from langsmith import traceable
from langsmith.anonymizer import (DEFAULT_SECRET_RULES, StringNodeRule,
                                  create_anonymizer, create_secret_anonymizer)

from utils import curso


@traceable(run_type="chain", name="ticket")
def _ticket(mensaje: str, correo: str, id_cliente: str) -> str:
    return f"Resuelto tu caso {id_cliente}."


def _enviar(**opciones):
    """Traza una petición con datos reconocibles y devuelve el run tal y como llegó."""
    with curso.servicio_simulado(**opciones) as servicio:
        with servicio.trazando():
            _ticket(mensaje="Soy Ana Pérez, DNI 12345678Z, tarjeta 4111 1111 1111 1111",
                    correo="ana.perez@acme.com", id_cliente="CLI-8891")
        servicio.cliente.flush()
    return servicio.run()


def _todo_el_texto(run: dict) -> str:
    return json.dumps(run, ensure_ascii=False, default=str)


# ------------------------------------------------------------------------------------
# Lo que se manda por defecto
# ------------------------------------------------------------------------------------


def test_por_defecto_se_manda_todo():
    """El punto de partida del notebook 05. Si esto dejara de ser cierto, mejor —pero
    habría que reescribir el notebook, no ignorarlo."""
    run = _enviar()
    assert run["inputs"]["correo"] == "ana.perez@acme.com"
    assert "4111 1111 1111 1111" in run["inputs"]["mensaje"]
    assert "CLI-8891" in str(run["outputs"])


def test_las_variables_de_entorno_del_usuario_viajan_en_los_metadatos(monkeypatch):
    """El hallazgo del apartado 1: el SDK copia TUS variables si las nombraste así."""
    from langsmith.env._runtime_env import get_langchain_env_var_metadata

    monkeypatch.setenv("LANGSMITH_URL_INTERNA", "https://facturacion.interna.local")
    monkeypatch.setenv("LANGCHAIN_CLIENTE", "acme-s-a")
    monkeypatch.setenv("LANGSMITH_MI_API_KEY", "sk-un-secreto")
    get_langchain_env_var_metadata.cache_clear()

    metadatos = get_langchain_env_var_metadata()
    assert metadatos.get("LANGSMITH_URL_INTERNA")   # se va: nombre de máquina interna
    assert metadatos.get("LANGCHAIN_CLIENTE")       # se va: nombre de un cliente
    assert "LANGSMITH_MI_API_KEY" not in metadatos  # la salva la subcadena «key»
    get_langchain_env_var_metadata.cache_clear()


# ------------------------------------------------------------------------------------
# hide_inputs
# ------------------------------------------------------------------------------------


def test_hide_inputs_booleano_no_deja_nada():
    run = _enviar(hide_inputs=True, hide_outputs=True)
    assert run["inputs"] == {}
    assert run["outputs"] == {}


def test_hide_inputs_acepta_una_funcion():
    """Lo que la documentación no destaca y que cambia la pregunta entera."""

    def solo_la_forma(entradas):
        return {k: f"<{type(v).__name__} de {len(str(v))}>" for k, v in entradas.items()}

    run = _enviar(hide_inputs=solo_la_forma)
    assert set(run["inputs"]) == {"mensaje", "correo", "id_cliente"}   # la forma queda
    assert "ana.perez@acme.com" not in _todo_el_texto({"inputs": run["inputs"]})


# ------------------------------------------------------------------------------------
# El anonimizador
# ------------------------------------------------------------------------------------


def test_el_anonimizador_de_fabrica_protege_secretos_y_no_personas():
    """La afirmación más importante del notebook 05.

    Las 24 reglas de fábrica son todas de credenciales. Te protegen a ti, no a tus
    usuarios. Si algún día añaden reglas de datos personales, esta prueba salta y el
    notebook hay que actualizarlo — a mejor.
    """
    anonimizador = create_secret_anonymizer()
    resultado = anonimizador({
        "openai": "sk-proj-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789AbCdEfGh",
        "aws": "AKIAIOSFODNN7EXAMPLE",
        "correo": "ana.perez@acme.com",
        "tarjeta": "4111 1111 1111 1111",
        "dni": "mi DNI es 12345678Z",
    })
    assert resultado["openai"] == "[SECRET_DETECTED]"
    assert resultado["aws"] == "[SECRET_DETECTED]"
    assert resultado["correo"] == "ana.perez@acme.com"      # pasa tal cual
    assert resultado["tarjeta"] == "4111 1111 1111 1111"    # pasa tal cual
    assert "12345678Z" in resultado["dni"]                  # pasa tal cual


def test_el_anonimizador_actua_en_entradas_y_en_salidas():
    anonimizador = create_anonymizer([
        StringNodeRule(pattern=re.compile(r"CLI-\d+"), replace="[cliente]"),
    ])
    run = _enviar(anonymizer=anonimizador)
    assert "CLI-8891" not in _todo_el_texto({"i": run["inputs"], "o": run["outputs"]})


def test_el_orden_de_las_reglas_cambia_el_resultado():
    """La quinta trampa silenciosa: una regla golosa se come lo de la siguiente.

    El resultado del orden malo no es «menos anonimizado»: es un IBAN parcialmente
    visible, que es peor que nada porque parece que la política funcionó.
    """
    iban = StringNodeRule(pattern=re.compile(r"\bES\d{2}[ ]?(?:\d{4}[ ]?){5}\b"),
                          replace="[iban]")
    tarjeta = StringNodeRule(pattern=re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
                             replace="[tarjeta]")
    # Un diccionario nuevo por llamada: el anonimizador MUTA el que recibe (ver la
    # prueba de abajo). Reutilizarlo aquí haría que la segunda llamada trabajara sobre
    # lo ya anonimizado, y la prueba pasaría por el motivo equivocado.
    def texto():
        return {"m": "IBAN ES91 2100 0418 4502 0005 1332"}

    bien = create_anonymizer([iban, tarjeta])(texto())["m"]
    mal = create_anonymizer([tarjeta, iban])(texto())["m"]

    assert bien == "IBAN [iban]"
    assert mal != "IBAN [iban]"
    assert "ES91" in mal              # sobrevive un trozo reconocible del IBAN


def test_el_anonimizador_muta_lo_que_recibe():
    """Detalle con dientes, descubierto porque hizo fallar la prueba de arriba.

    `create_anonymizer(...)` devuelve **el mismo objeto** que se le pasa, ya modificado.
    A través del SDK no importa —el cliente copia antes de anonimizar, y se comprueba
    debajo—, pero sí importa si lo llamas tú: para probarlo, o dentro de un `hide_inputs`
    escrito a mano.
    """
    import copy

    anonimizador = create_anonymizer([
        StringNodeRule(pattern=re.compile(r"\d{8}[A-HJ-NP-TV-Z]"), replace="[dni]"),
    ])
    original = {"m": "DNI 12345678Z", "anidado": {"otro": "DNI 87654321X"}}
    previo = copy.deepcopy(original)

    resultado = anonimizador(original)

    assert resultado is original          # el mismo objeto
    assert original != previo             # y modificado
    assert original["anidado"]["otro"] == "DNI [dni]"


def test_el_sdk_copia_antes_de_anonimizar():
    """El control del anterior: tus datos vivos NO se te modifican por trazar."""
    anonimizador = create_anonymizer([
        StringNodeRule(pattern=re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), replace="[correo]"),
    ])

    @traceable(run_type="chain", name="atender")
    def atender(cliente: dict) -> str:
        return "ok"

    mi_dato = {"correo": "ana@acme.com", "nombre": "Ana"}
    with curso.servicio_simulado(anonymizer=anonimizador) as servicio:
        with servicio.trazando():
            atender(mi_dato)
        servicio.cliente.flush()

    assert mi_dato["correo"] == "ana@acme.com"                       # intacto
    assert servicio.run()["inputs"]["cliente"]["correo"] == "[correo]"  # y anonimizado


def test_las_reglas_personales_del_notebook_hacen_lo_que_dicen():
    """Una prueba por regla, con un caso que debe cambiar. Es lo que el notebook pide
    que hagas con las tuyas."""
    reglas = {
        "correo": (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "ana.perez@acme.com"),
        "iban": (re.compile(r"\bES\d{2}[ ]?(?:\d{4}[ ]?){5}\b"), "ES91 2100 0418 4502 0005 1332"),
        "tarjeta": (re.compile(r"\b(?:\d[ -]*?){13,16}\b"), "4111 1111 1111 1111"),
        "dni": (re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b"), "12345678Z"),
        "telefono": (re.compile(r"\b(?:\+34[ -]?)?[6-9]\d{8}\b"), "611223344"),
    }
    for etiqueta, (patron, ejemplo) in reglas.items():
        anonimizador = create_anonymizer([StringNodeRule(pattern=patron,
                                                         replace=f"[{etiqueta}]")])
        resultado = anonimizador({"t": f"el dato es {ejemplo} y ya"})["t"]
        assert ejemplo not in resultado, f"la regla «{etiqueta}» no cazó su propio ejemplo"


# ------------------------------------------------------------------------------------
# No trazar
# ------------------------------------------------------------------------------------


def test_no_trazar_es_la_unica_garantia():
    """De las tres herramientas, la única que no depende de que tus reglas estén
    completas —y las reglas nunca están completas."""
    from langsmith.run_helpers import tracing_context

    tickets = [
        {"id": "CLI-1", "sensible": False},
        {"id": "CLI-2", "sensible": True},
        {"id": "CLI-3", "sensible": False},
    ]
    with curso.servicio_simulado() as servicio:
        for t in tickets:
            with tracing_context(enabled=not t["sensible"], client=servicio.cliente):
                _ticket("mensaje", "correo@x.com", t["id"])
        servicio.cliente.flush()

    llegaron = [r["inputs"]["id_cliente"] for r in servicio.recibidos]
    assert llegaron == ["CLI-1", "CLI-3"]
    assert "CLI-2" not in json.dumps(servicio.recibidos, default=str)


# ------------------------------------------------------------------------------------
# El auditor del ejercicio 1
# ------------------------------------------------------------------------------------


def test_auditar_solo_las_entradas_no_basta():
    """La lección del ejercicio 1: lo que el modelo escribe también es un canal de fuga.

    `CLI-8891` no estaba en el mensaje. Lo puso la salida, que lo compone a partir de
    un argumento.
    """
    anonimizador = create_anonymizer(list(DEFAULT_SECRET_RULES) + [
        StringNodeRule(pattern=re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), replace="[correo]"),
        StringNodeRule(pattern=re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b"), replace="[dni]"),
        StringNodeRule(pattern=re.compile(r"\b(?:\d[ -]*?){13,16}\b"), replace="[tarjeta]"),
    ])
    run = _enviar(anonymizer=anonimizador)

    assert "ana.perez@acme.com" not in _todo_el_texto(run)      # esas sí se taparon
    assert "12345678Z" not in _todo_el_texto(run)
    assert "Ana Pérez" in run["inputs"]["mensaje"]              # un nombre no tiene forma
    assert "CLI-8891" in str(run["outputs"])                    # y salió por la salida
