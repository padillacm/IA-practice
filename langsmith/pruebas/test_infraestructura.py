"""Pruebas del aparato del curso: los dos modos, el presupuesto y la traza local.

Estas pruebas valen más que las de un curso normal. El material se escribió sin poder
alcanzar el servicio, así que el mecanismo que separa «lo que ejecuto» de «lo que solo
escribo» es lo único que sostiene la honestidad del curso. Si `@online` se equivocara
de rama, el curso mentiría sin que nadie se enterase.
"""

from __future__ import annotations

import pytest

from utils import curso


# ------------------------------------------------------------------------------------
# El mecanismo de los dos modos
# ------------------------------------------------------------------------------------


def test_sin_clave_estamos_en_modo_local():
    assert curso.hay_servicio() is False
    info = curso.init(silencioso=True)
    assert info["modo"] == "local"
    assert info["conectado"] is False


def test_con_clave_estamos_en_modo_en_linea(con_servicio):
    assert curso.hay_servicio() is True
    info = curso.init(silencioso=True)
    assert info["modo"] == "en línea"
    assert info["proyecto"] is not None


def test_init_apaga_el_trazado_explicitamente_si_no_hay_clave(monkeypatch):
    """No basta con no encenderlo: hay que apagarlo.

    Si `LANGSMITH_TRACING` se quedara a `true` de una sesión anterior, el SDK intentaría
    salir a la red en cada celda y llenaría la salida de avisos de conexión.
    """
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    curso.init(silencioso=True)
    import os

    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_online_no_ejecuta_el_cuerpo_sin_clave():
    ejecutado = []

    @curso.online("no debería pasar")
    def _():
        ejecutado.append(True)
        return "valor"

    assert ejecutado == []
    assert _ is None


def test_online_si_ejecuta_el_cuerpo_con_clave(con_servicio):
    @curso.online("sí debería pasar", trazas=0)
    def resultado():
        return "valor"

    assert resultado == "valor"


def test_online_captura_los_errores_y_no_los_propaga(con_servicio, capsys):
    """Decisión deliberada: una celda en línea rota no debe tumbar el notebook.

    El material en línea está escrito sin poder ejecutarse. Si tiene un fallo, lo mejor
    que puede pasar es que se vea señalado y el resto del notebook siga.
    """

    @curso.online("una llamada con un fallo", trazas=0)
    def _():
        raise ValueError("la API ha cambiado")

    assert _ is None
    salida = capsys.readouterr().out
    assert "FALLO" in salida
    assert "la API ha cambiado" in salida


def test_online_solo_cuenta_las_trazas_que_de_verdad_se_gastan(con_servicio):
    antes = curso.trazas_consumidas()

    @curso.online("esta falla", trazas=10)
    def _():
        raise RuntimeError("no llega a gastar nada")

    assert curso.trazas_consumidas() == antes

    @curso.online("esta funciona", trazas=7)
    def _ok():
        return None

    assert curso.trazas_consumidas() == antes + 7


# ------------------------------------------------------------------------------------
# El presupuesto de trazas
# ------------------------------------------------------------------------------------


def test_los_jueces_llm_tambien_cuentan():
    """La cuenta que sorprende a todo el mundo la primera vez."""
    solo_target = curso.presupuesto_de_trazas(ejemplos=50, repeticiones=3)
    con_jueces = curso.presupuesto_de_trazas(ejemplos=50, repeticiones=3, evaluadores_llm=2)
    assert solo_target == 150
    assert con_jueces == 450  # y no 150: cada juez es otra llamada trazada


def test_el_tope_impide_lanzar_el_experimento():
    with pytest.raises(ValueError, match="tope"):
        curso.presupuesto_de_trazas(ejemplos=200, repeticiones=5, tope=100)


def test_el_tope_deja_pasar_lo_que_cabe():
    assert curso.presupuesto_de_trazas(ejemplos=10, repeticiones=2, tope=100) == 20


# ------------------------------------------------------------------------------------
# La traza local
# ------------------------------------------------------------------------------------


def test_traza_local_construye_el_arbol_sin_clave():
    from langsmith import traceable

    @traceable(run_type="tool")
    def buscar(consulta: str) -> list[str]:
        return [consulta]

    @traceable(run_type="chain", name="raiz")
    def responder(pregunta: str) -> str:
        buscar(pregunta)
        return "listo"

    with curso.traza_local() as t:
        assert responder("hola") == "listo"

    assert len(t.principales) == 1
    raiz = t.principales[0]
    assert raiz.name == "raiz"
    assert raiz.run_type == "chain"
    assert [h.name for h in raiz.child_runs] == ["buscar"]
    assert len(t) == 2


def test_traza_local_captura_entradas_y_salidas():
    """Y por eso el notebook 05 existe: lo que entra en la función entra en la traza."""
    from langsmith import traceable

    @traceable
    def saludar(nombre: str, secreto: str) -> str:
        return f"hola {nombre}"

    with curso.traza_local() as t:
        saludar("ana", secreto="sk-no-deberia-estar-aqui")

    run = t.principales[0]
    assert run.inputs == {"nombre": "ana", "secreto": "sk-no-deberia-estar-aqui"}
    assert run.outputs == {"output": "hola ana"}


def test_el_dotted_order_del_hijo_empieza_por_el_del_padre():
    """La propiedad que permite reconstruir el árbol desde una lista plana."""
    from langsmith import traceable

    @traceable
    def hijo():
        return 1

    @traceable
    def padre():
        return hijo()

    with curso.traza_local() as t:
        padre()

    p = t.principales[0]
    h = p.child_runs[0]
    assert h.dotted_order.startswith(p.dotted_order)
    assert p.trace_id == h.trace_id
    assert p.id != h.id


def test_traza_local_no_envia_nada(monkeypatch):
    """El punto entero del modo local: que no salga.

    Se comprueba cortando la resolución de nombres. Si `traza_local` intentara subir
    algo —o siquiera sondear `/info`— se anotaría aquí.
    """
    import socket

    intentos = []
    original = socket.getaddrinfo

    def espia(host, port, *args, **kwargs):
        intentos.append(str(host))
        return original(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", espia)

    from langsmith import traceable

    @traceable
    def algo():
        return 42

    with curso.traza_local() as t:
        algo()

    assert t.principales[0].outputs == {"output": 42}
    assert [h for h in intentos if "langchain.com" in h] == []


def test_traza_local_vacia_no_revienta():
    with curso.traza_local() as t:
        pass
    assert t.principales == []
    assert len(t) == 0


# ------------------------------------------------------------------------------------
# Datos compartidos con el curso de LangGraph
# ------------------------------------------------------------------------------------


def test_los_tickets_del_otro_curso_se_encuentran():
    ruta = curso.ruta_datos("tickets_soporte.csv")
    assert ruta.exists()


def test_un_fichero_que_no_existe_da_un_error_util():
    with pytest.raises(FileNotFoundError, match="langgraph"):
        curso.ruta_datos("no_existe.csv")


def test_el_mapa_de_la_superficie_del_readme_sigue_siendo_cierto():
    """El README reparte la superficie del SDK en tres montones y da dos números. Si el
    SDK cambia y los números dejan de cuadrar, el mapa deja de servir para orientarse,
    que es lo único para lo que existe."""
    import ast
    import pathlib
    import re

    import langsmith.client as lc

    fuente = pathlib.Path(lc.__file__).read_text()
    arbol = ast.parse(fuente)
    clase = next(n for n in arbol.body
                 if isinstance(n, ast.ClassDef) and n.name == "Client")

    publicos = [n for n in dir(lc.Client) if not n.startswith("_")]
    obsoletos, fechas = [], set()
    for nodo in clase.body:
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cuerpo = ast.get_source_segment(fuente, nodo) or ""
            if "deprecated" in cuerpo[:600].lower():
                obsoletos.append(nodo.name)
                fechas |= set(re.findall(r"Will be removed after ([A-Z][a-z]+ \d+, \d{4})",
                                         cuerpo))

    readme = (pathlib.Path(__file__).resolve().parents[1] / "README.md").read_text()
    assert f"{len(publicos)} miembros públicos" in readme, len(publicos)
    assert f"{len(obsoletos)} de ellos" in readme, len(obsoletos)
    assert fechas == {"Jan 31, 2027"}, fechas
    assert "31 de enero de 2027" in readme
