"""Pruebas del módulo 2: datasets y experimentos.

Dos de estas pruebas son distintas de todas las demás del curso, y conviene señalarlo:
`test_upload_results_sigue_permitiendo_evaluar_sin_subir` y
`test_evaluate_acepta_ejemplos_en_memoria` no vigilan una afirmación del material —
vigilan **el mecanismo del que depende que el módulo 2 se pueda ejecutar**. El SDK marca
`upload_results` como beta. Si desaparece, este módulo deja de ser verificable y hay que
enterarse aquí.
"""

from __future__ import annotations

import contextlib
import io

from utils import curso


def _conjunto(n: int = 16):
    return curso.ejemplos_locales(curso.tickets(n), entradas=("asunto", "mensaje"),
                                  salidas=("categoria",))


def _acierto(outputs, reference_outputs):
    return {"key": "acierto",
            "score": float((outputs or {}).get("categoria") == reference_outputs["categoria"])}


# ------------------------------------------------------------------------------------
# El mecanismo del que depende el módulo
# ------------------------------------------------------------------------------------


def test_evaluate_acepta_ejemplos_en_memoria():
    ejemplos = _conjunto(8)
    resultados = curso.experimento_local(lambda e: {"categoria": "otros"}, ejemplos,
                                         evaluadores=[_acierto])
    assert len(list(resultados)) == 8


def test_upload_results_sigue_permitiendo_evaluar_sin_subir(monkeypatch):
    """Si esto deja de funcionar, el módulo 2 deja de ser ejecutable en local."""
    import socket

    intentos = []
    original = socket.getaddrinfo
    monkeypatch.setattr(socket, "getaddrinfo",
                        lambda h, p, *a, **k: (intentos.append(str(h)), original(h, p, *a, **k))[1])

    list(curso.experimento_local(lambda e: {"categoria": "otros"}, _conjunto(4),
                                 evaluadores=[_acierto]))
    assert [h for h in intentos if "langchain.com" in h] == []


# ------------------------------------------------------------------------------------
# Notebook 06 · datasets
# ------------------------------------------------------------------------------------


def test_la_muestra_estratificada_equilibra_las_categorias():
    """Las primeras N filas miden lo que hubo en enero; la estratificada, tu sistema."""
    import collections

    ingenuo = collections.Counter(t["categoria"] for t in curso.tickets()[:40])
    equilibrado = collections.Counter(t["categoria"] for t in curso.tickets(40))

    assert max(equilibrado.values()) - min(equilibrado.values()) <= 1
    assert max(ingenuo.values()) - min(ingenuo.values()) > 5      # muy desequilibrado


def test_el_perezoso_saca_mejor_nota_sobre_la_muestra_desequilibrada():
    """El número que justifica el apartado 3 del notebook 06."""
    import collections

    def nota_del_perezoso(muestra):
        mayoritaria = collections.Counter(t["categoria"] for t in muestra).most_common(1)[0][0]
        ejemplos = curso.ejemplos_locales(muestra, entradas=("asunto", "mensaje"),
                                          salidas=("categoria",))
        resultados = curso.experimento_local(lambda e: {"categoria": mayoritaria},
                                             ejemplos, evaluadores=[_acierto])
        return curso.resumen_del_experimento(resultados)["acierto"]

    desequilibrada = nota_del_perezoso(curso.tickets()[:40])
    estratificada = nota_del_perezoso(curso.tickets(40))
    assert desequilibrada > estratificada * 1.5


def test_los_ejemplos_separan_entradas_salidas_y_metadatos():
    ejemplo = _conjunto(4)[0]
    assert set(ejemplo.inputs) == {"asunto", "mensaje"}
    assert set(ejemplo.outputs) == {"categoria"}
    # Lo que sirve para filtrar y no para comparar.
    assert "plan_cliente" in (ejemplo.metadata or {})
    assert "categoria" not in (ejemplo.metadata or {})


# ------------------------------------------------------------------------------------
# Notebook 07 · experimentos
# ------------------------------------------------------------------------------------


def test_un_objetivo_que_revienta_no_detiene_el_experimento():
    ejemplos = _conjunto(10)

    def objetivo(entradas):
        if len(entradas["mensaje"]) > 120:
            raise ValueError("boom")
        return {"categoria": "otros"}

    with contextlib.redirect_stderr(io.StringIO()):
        filas = list(curso.experimento_local(objetivo, ejemplos, evaluadores=[_acierto]))

    assert len(filas) == 10
    assert any(f["run"].error for f in filas)


def test_los_outputs_de_una_fila_reventada_no_son_none():
    """El detalle del que depende todo lo demás, y que corrige el reflejo defensivo.

    Cuando el objetivo lanza, `outputs` no queda a `None` sino a `{"output": None}`.
    Es un diccionario, o sea **verdadero**, así que la guarda `(outputs or {})` que
    escribe todo el mundo no protege absolutamente de nada.
    """
    vistos = []

    def revienta(entradas):
        raise ValueError("boom")

    def espia(outputs, reference_outputs):
        vistos.append(outputs)
        return {"key": "x", "score": 0.0}

    with contextlib.redirect_stderr(io.StringIO()):
        list(curso.experimento_local(revienta, _conjunto(4), evaluadores=[espia]))

    assert vistos == [{"output": None}] * 4
    assert all(bool(v) for v in vistos)          # verdaderos: `or {}` no salta


def test_solo_el_get_salva_al_evaluador_de_un_sistema_fragil():
    """El hallazgo central del notebook 07, y el fallo más caro del módulo.

    Las tres formas de leer `outputs`, sobre el mismo sistema frágil y el mismo
    conjunto. Las dos primeras dejan sin puntuar los casos que reventaron, así que
    esos casos desaparecen del promedio y la nota sube: cuanto más frágil es el
    sistema, mejor sale.
    """
    ejemplos = _conjunto(32)

    def fragil(entradas):
        if len(entradas["mensaje"]) > 155:
            raise ValueError("mensaje demasiado largo")
        return {"categoria": "facturacion"}

    def indexa(outputs, reference_outputs):
        return {"key": "acierto",
                "score": float(outputs["categoria"] == reference_outputs["categoria"])}

    def con_or(outputs, reference_outputs):
        return {"key": "acierto",
                "score": float((outputs or {})["categoria"] == reference_outputs["categoria"])}

    def medir(evaluador):
        """Cuenta las filas con puntuación DE LA MÉTRICA, no los resultados a secas.

        Cuando un evaluador lanza, el SDK igualmente registra un resultado para esa
        fila —sin `score` y con otra clave—, así que contar resultados da 32 siempre y
        no distingue nada. Es la misma cuenta por métrica que hace `informe()` en el
        notebook 07, y la razón de que allí esté escrita así.
        """
        with contextlib.redirect_stderr(io.StringIO()):
            resultados = curso.experimento_local(fragil, ejemplos, evaluadores=[evaluador])
            filas = list(resultados)
            puntuadas = sum(1 for f in filas
                            for r in f["evaluation_results"]["results"]
                            if r.key == "acierto" and r.score is not None)
            return puntuadas, len(filas), curso.resumen_del_experimento(resultados)["acierto"]

    p_indexa, total, nota_indexa = medir(indexa)
    p_or, _, nota_or = medir(con_or)
    p_get, _, nota_get = medir(_acierto)          # `_acierto` usa .get()

    assert p_indexa < total                        # se caen del promedio
    assert (p_or, nota_or) == (p_indexa, nota_indexa)   # `or {}` no cambia NADA
    assert p_get == total                          # solo `.get()` los puntúa
    assert nota_indexa > nota_get                  # y la nota inflada es la de antes


def test_un_evaluador_que_se_cae_desaparece_sin_dejar_rastro():
    """Ni un cero, ni un aviso: la métrica simplemente no está en la lista."""
    ejemplos = _conjunto(8)

    def juez_roto(outputs, reference_outputs):
        raise RuntimeError("el juez devolvió 500")

    with contextlib.redirect_stderr(io.StringIO()):
        resultados = curso.experimento_local(lambda e: {"categoria": "otros"}, ejemplos,
                                             evaluadores=[_acierto, juez_roto])
        medias = curso.resumen_del_experimento(resultados)

    assert "acierto" in medias
    assert not any("juez" in k for k in medias)


def test_los_evaluadores_de_resumen_ven_todo_el_conjunto():
    """Es lo que hace posible el F1: la media de F1 por caso no es el F1."""
    vistos = {}

    def resumen(outputs, reference_outputs):
        vistos["n"] = len(outputs)
        return {"key": "cobertura_total", "score": 1.0}

    ejemplos = _conjunto(12)
    resultados = curso.experimento_local(lambda e: {"categoria": "otros"}, ejemplos,
                                         evaluadores=[_acierto],
                                         evaluadores_de_resumen=[resumen])
    medias = curso.resumen_del_experimento(resultados)

    assert vistos["n"] == 12
    assert "cobertura_total (resumen)" in medias


def test_las_repeticiones_multiplican_las_filas():
    ejemplos = _conjunto(5)
    filas = list(curso.experimento_local(lambda e: {"categoria": "otros"}, ejemplos,
                                         evaluadores=[_acierto], repeticiones=3))
    assert len(filas) == 15


def test_en_local_el_prefijo_del_experimento_se_ignora():
    """Rareza del modo local que el notebook 07 avisa: sin subida no hay experimento
    que nombrar, así que `experiment_name` devuelve un nombre aleatorio."""
    resultados = curso.experimento_local(lambda e: {"categoria": "otros"}, _conjunto(4),
                                         evaluadores=[_acierto], prefijo="mi-prefijo")
    list(resultados)
    assert not resultados.experiment_name.startswith("mi-prefijo")
