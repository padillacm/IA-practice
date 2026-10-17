"""Pruebas del proyecto P1: instrumentar el agente del curso de LangGraph.

Aquí se prueban dos cosas distintas y conviene no mezclarlas:

- Que el **puente entre los dos cursos** sigue funcionando: que el agente se puede
  importar, que sus herramientas leen los tickets y que se traza. Si el curso de
  LangGraph cambia, esto salta.
- Que la **instrumentación** hace lo que el proyecto dice. En particular la sexta
  trampa silenciosa, que es la que más cuesta descubrir sola.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from utils import curso


def _invocar(agente, **config_extra):
    config = {"configurable": {"thread_id": "conv-1"}, **config_extra}
    with curso.traza_local() as traza:
        agente.invoke({"messages": [HumanMessage("¿cuántos tickets hay?")]}, config)
    return traza


# ------------------------------------------------------------------------------------
# El puente con el curso de LangGraph
# ------------------------------------------------------------------------------------


def test_el_agente_del_otro_curso_se_importa_y_se_ejecuta():
    agente, modelo = curso.agente_de_soporte()
    resultado = agente.invoke({"messages": [HumanMessage("¿cuántos?")]})
    assert resultado["messages"][-1].text
    assert modelo.llamadas == 2          # pensar -> herramienta -> pensar


def test_el_agente_ejecuta_sus_herramientas_sobre_los_tickets_de_verdad():
    """No es un agente de juguete: consulta los 400 tickets etiquetados."""
    agente, _ = curso.agente_de_soporte([
        ("contar_tickets", {"categoria": "facturacion"}),
        "Ya está.",
    ])
    traza = _invocar(agente)

    herramientas = [r for _, r in traza.recorrer() if r.run_type == "tool"]
    assert [r.name for r in herramientas] == ["contar_tickets"]
    salida = str(herramientas[0].outputs)
    assert "tickets" in salida and "categoría=facturacion" in salida


def test_el_modelo_guionizado_sabe_pedir_herramientas():
    """Los modelos falsos de serie no implementan `bind_tools`, y sin eso el ToolNode
    nunca se ejecuta y la traza del proyecto sale plana."""
    modelo = curso.ModeloGuionizado([("contar_tickets", {"categoria": "otros"}), "fin"])
    primera = modelo.invoke([HumanMessage("hola")])
    segunda = modelo.invoke([HumanMessage("hola")])

    assert primera.tool_calls[0]["name"] == "contar_tickets"
    assert segunda.text == "fin"
    assert primera.usage_metadata["total_tokens"] > 0     # para las cuentas del nb 04


# ------------------------------------------------------------------------------------
# La instrumentación
# ------------------------------------------------------------------------------------


def test_sin_instrumentar_la_traza_no_tiene_metadatos_de_negocio():
    """El punto de partida del proyecto: lo que sale gratis y lo que falta."""
    agente, _ = curso.agente_de_soporte()
    traza = _invocar(agente)

    raiz = traza.principales[0]
    assert raiz.name == "LangGraph"                      # mil filas iguales en la lista
    assert "cliente" not in raiz.extra["metadata"]       # no se puede filtrar por cliente
    assert raiz.extra["metadata"]["thread_id"] == "conv-1"   # el hilo sí llega solo


def test_el_config_instrumenta_el_grafo_entero():
    agente, _ = curso.agente_de_soporte()
    traza = _invocar(
        agente,
        run_name="soporte:TCK-0001",
        tags=["produccion", "plan-free"],
        metadata={"cliente": "acme", "plan": "free", "version_prompt": "v3"},
    )

    raiz = traza.principales[0]
    assert raiz.name == "soporte:TCK-0001"
    assert set(raiz.tags) >= {"produccion", "plan-free"}
    for _, run in traza.recorrer():
        assert run.extra["metadata"]["cliente"] == "acme", run.name


def test_langsmith_extra_se_ignora_en_un_runnable():
    """La sexta trampa silenciosa, y la peor: el código PARECE el del notebook 02.

    `langsmith_extra` es un mecanismo de `@traceable`. Un grafo es un `Runnable` y se
    instrumenta por callbacks, así que sus metadatos van en el `config`. Pasarlo por el
    otro camino no da ningún error: se ignora y la traza sale sin metadatos.
    """
    agente, _ = curso.agente_de_soporte()
    with curso.traza_local() as traza:
        agente.invoke(
            {"messages": [HumanMessage("hola")]},
            {"configurable": {"thread_id": "conv-1"}},
            langsmith_extra={"name": "NO-SE-APLICA",
                             "metadata": {"cliente": "acme"},
                             "tags": ["produccion"]},
        )

    raiz = traza.principales[0]
    assert raiz.name == "LangGraph"                    # el nombre no se aplicó
    assert "cliente" not in raiz.extra["metadata"]     # los metadatos tampoco
    assert "produccion" not in (raiz.tags or [])       # ni las etiquetas


def test_los_fallos_silenciosos_del_agente_se_detectan_en_la_traza():
    """La pregunta 4 del cuadro de mando, y la que ningún panel trae de serie.

    La herramienta se ejecuta sin error, devuelve un texto educado, el usuario recibe
    una respuesta bien redactada que no le sirve, y la tasa de error marca 0 %.
    """
    agente, _ = curso.agente_de_soporte([
        ("contar_tickets", {"categoria": "categoria-que-no-existe"}),
        "No he encontrado esa categoría.",
    ])
    traza = _invocar(agente)

    herramientas = [r for _, r in traza.recorrer() if r.run_type == "tool"]
    assert all(r.error is None for _, r in traza.recorrer())      # nada marcado como error
    assert any("No existe la categoría" in str(r.outputs) for r in herramientas)


def test_la_politica_de_privacidad_del_proyecto_tapa_lo_que_dice():
    """El agente recibe mensajes de personas. Se comprueba contra lo que llega."""
    import json
    import re

    from langsmith.anonymizer import (DEFAULT_SECRET_RULES, StringNodeRule,
                                      create_anonymizer)

    reglas = list(DEFAULT_SECRET_RULES) + [
        StringNodeRule(pattern=re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), replace="[correo]"),
        StringNodeRule(pattern=re.compile(r"\bES\d{2}[ ]?(?:\d{4}[ ]?){5}\b"), replace="[iban]"),
        StringNodeRule(pattern=re.compile(r"\b(?:\d[ -]*?){13,16}\b"), replace="[tarjeta]"),
        StringNodeRule(pattern=re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b"), replace="[dni]"),
        StringNodeRule(pattern=re.compile(r"\b(?:\+34[ -]?)?[6-9]\d{8}\b"), replace="[telefono]"),
    ]
    agente, _ = curso.agente_de_soporte()
    mensaje = ("Soy Ana Pérez (DNI 12345678Z), tel 611223344, tarjeta "
               "4111 1111 1111 1111, correo ana.perez@acme.com")

    with curso.servicio_simulado(anonymizer=create_anonymizer(reglas)) as servicio:
        with servicio.trazando():
            agente.invoke({"messages": [HumanMessage(mensaje)]},
                          {"configurable": {"thread_id": "conv-1"}})
        servicio.cliente.flush()

    todo = json.dumps(servicio.recibidos, ensure_ascii=False, default=str)
    for dato in ("12345678Z", "611223344", "4111 1111 1111 1111", "ana.perez@acme.com"):
        assert dato not in todo, f"se fue: {dato}"
    # Y lo que la política NO tapa, dicho explícitamente en el proyecto.
    assert "Ana Pérez" in todo
