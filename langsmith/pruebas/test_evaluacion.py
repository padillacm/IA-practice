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


# ------------------------------------------------------------------------------------
# Notebook 08 · evaluadores
# ------------------------------------------------------------------------------------


def test_un_evaluador_puede_devolver_varios_resultados():
    """Es lo que evita montar cuatro evaluadores para cuatro comprobaciones."""
    def varias(outputs, reference_outputs):
        return [{"key": "a", "score": 1.0},
                {"key": "b", "score": 0.0},
                {"key": "c", "score": 1.0}]

    resultados = curso.experimento_local(lambda e: {"categoria": "otros"}, _conjunto(4),
                                         evaluadores=[varias])
    medias = curso.resumen_del_experimento(resultados)
    assert set(medias) == {"a", "b", "c"}


def test_expect_edit_distance_funciona_sin_red():
    """Necesita `rapidfuzz`, que por eso es dependencia declarada del curso."""
    from langsmith import expect

    igual = expect.edit_distance("cinco días", "cinco días").value
    parecido = expect.edit_distance("cinco dias", "cinco días").value
    distinto = expect.edit_distance("una semana", "cinco días").value

    assert igual == 0.0
    assert 0 < parecido < distinto


def test_openevals_trae_rubricas_escritas():
    """El notebook 08 dice «33». Que envejezca a la vista si cambian."""
    from openevals import prompts

    rubricas = [n for n in dir(prompts) if n.isupper()]
    assert 25 <= len(rubricas) <= 45, f"ahora son {len(rubricas)}: actualiza el nb 08"
    assert "CORRECTNESS_PROMPT" in rubricas
    assert "HALLUCINATION_PROMPT" in rubricas
    # Lo que hace útil una rúbrica es la lista de qué penalizar, no la de virtudes.
    assert "penalize" in prompts.CORRECTNESS_PROMPT.lower()


def test_un_juez_de_openevals_corre_sin_clave():
    """El mecanismo que hace ejecutable el notebook 08.

    `openevals` llama al juez con `with_structured_output(...).invoke(...)`, así que
    basta implementar esos dos métodos. Si eso cambia, el notebook 08 deja de correr.
    """
    from openevals.llm import create_llm_as_judge
    from openevals.prompts import CORRECTNESS_PROMPT

    juez = create_llm_as_judge(
        prompt=CORRECTNESS_PROMPT,
        judge=curso.juez_local(lambda texto: (1.0, "coincide con la referencia")),
        feedback_key="correccion",
    )
    veredicto = juez(inputs={"m": "una consulta"},
                     outputs={"respuesta": "una respuesta"},
                     reference_outputs={"respuesta": "una respuesta"})

    assert veredicto["key"] == "correccion"
    assert veredicto["score"] == 1.0
    assert veredicto["comment"] == "coincide con la referencia"


def test_openevals_escapa_los_acentos_en_el_prompt():
    """Detalle que muerde a cualquiera que evalúe en español.

    Las entradas y salidas se meten en el prompt como JSON con `ensure_ascii`, así que
    `días` llega como `d\\u00edas`. Un modelo lo entiende; una expresión regular tuya
    no encuentra nada y no da ningún error.
    """
    from openevals.llm import create_llm_as_judge

    visto = {}

    def espia(texto):
        visto["prompt"] = texto
        return 1.0, "ok"

    juez = create_llm_as_judge(prompt="{inputs} {outputs} {reference_outputs}",
                               judge=curso.juez_local(espia), feedback_key="x")
    juez(inputs={"m": "¿cuándo?"}, outputs={"r": "en 5 días"}, reference_outputs={"r": "en 5 días"})

    assert "días" not in visto["prompt"]
    assert "d\\u00edas" in visto["prompt"]
    # Y así se recupera, que es lo que hace el notebook.
    assert "días" in visto["prompt"].encode().decode("unicode_escape")


def test_el_juez_sin_rubrica_premia_la_longitud():
    """El sesgo que el notebook 08 mide, como prueba.

    Dos respuestas con el mismo dato y distinta extensión no deberían puntuar distinto.
    Con un juez al que solo le dices «puntúa la calidad», sí lo hacen.
    """
    from openevals.llm import create_llm_as_judge
    from openevals.prompts import CORRECTNESS_PROMPT

    def por_longitud(texto):
        return round(min(1.0, len(texto) / 2600), 2), "más completo"

    juez = create_llm_as_judge(prompt=CORRECTNESS_PROMPT, feedback_key="calidad",
                               judge=curso.juez_local(por_longitud), continuous=True)

    breve = "Tu reembolso llega en 5 días hábiles."
    larga = breve + " " + "Gracias por tu paciencia y quedamos a tu disposición." * 4

    nota_breve = juez(inputs={"m": "x"}, outputs={"r": breve},
                      reference_outputs={"r": breve})["score"]
    nota_larga = juez(inputs={"m": "x"}, outputs={"r": larga},
                      reference_outputs={"r": breve})["score"]

    assert nota_larga > nota_breve      # mismo dato, más nota


def test_los_evaluadores_de_trayectoria_del_otro_curso_se_integran():
    """El puente con el notebook 27 del curso de LangGraph."""
    from agentevals.trajectory.match import create_trajectory_match_evaluator
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

    evaluador = create_trajectory_match_evaluator(trajectory_match_mode="unordered")

    def con(nombre):
        return [
            HumanMessage("¿cuántos tickets hay?"),
            AIMessage("", tool_calls=[{"name": nombre, "args": {}, "id": "1",
                                       "type": "tool_call"}]),
            ToolMessage("87", tool_call_id="1"),
            AIMessage("Hay 87."),
        ]

    esperada = con("contar_tickets")
    assert evaluador(outputs=con("contar_tickets"), reference_outputs=esperada)["score"]
    assert not evaluador(outputs=con("detalle_ticket"), reference_outputs=esperada)["score"]


# ------------------------------------------------------------------------------------
# Notebook 09 · varianza y regresión
# ------------------------------------------------------------------------------------


def test_el_mismo_sistema_da_notas_distintas():
    """El punto de partida del notebook 09, medido.

    Quince ejecuciones idénticas sobre el mismo conjunto y notas que se separan
    decenas de puntos. Si esto dejara de ser cierto, el notebook sobra.
    """
    import random
    import statistics

    ejemplos = _conjunto(30)

    def sistema(semilla):
        aleatorio = random.Random(semilla)
        return lambda entradas: {"acierta": aleatorio.random() < 0.70}

    def acierto(outputs, reference_outputs):
        return {"key": "acierto", "score": float((outputs or {}).get("acierta", False))}

    notas = [curso.resumen_del_experimento(
                curso.experimento_local(sistema(s), ejemplos, evaluadores=[acierto]))["acierto"]
             for s in range(15)]

    assert 0.6 < statistics.mean(notas) < 0.8      # la media sí converge al valor real
    assert max(notas) - min(notas) > 0.15          # pero cada medida suelta baila mucho


def test_el_ruido_sigue_la_ley_de_la_raiz():
    """`σ = √(p(1−p)/n)`, comprobado contra la medida y no contra el libro.

    Con más casos, menos ruido — y la reducción no es lineal.
    """
    import math
    import random
    import statistics

    def medir_ruido(n):
        ejemplos = _conjunto(n)

        def sistema(semilla):
            aleatorio = random.Random(semilla)
            return lambda entradas: {"acierta": aleatorio.random() < 0.70}

        def acierto(outputs, reference_outputs):
            return {"key": "acierto", "score": float((outputs or {}).get("acierta", False))}

        notas = [curso.resumen_del_experimento(
                    curso.experimento_local(sistema(s), ejemplos,
                                            evaluadores=[acierto]))["acierto"]
                 for s in range(15)]
        return statistics.stdev(notas), math.sqrt(0.70 * 0.30 / n)

    ruido_10, teorico_10 = medir_ruido(10)
    ruido_200, teorico_200 = medir_ruido(200)

    assert ruido_200 < ruido_10 / 2               # más casos, mucho menos ruido
    for medido, teorico in ((ruido_10, teorico_10), (ruido_200, teorico_200)):
        assert 0.4 < medido / teorico < 2.2, f"medido {medido} frente a teórico {teorico}"


def test_repetir_no_aporta_nada_sobre_un_sistema_determinista():
    """Comprobación que ahorra dinero: si el sistema es determinista, N repeticiones
    son N veces el coste y cero información."""
    ejemplos = _conjunto(20)

    def determinista(entradas):
        texto = f"{entradas.get('asunto', '')} {entradas.get('mensaje', '')}".lower()
        return {"acierta": "factur" in texto}

    def acierto(outputs, reference_outputs):
        return {"key": "acierto", "score": float((outputs or {}).get("acierta", False))}

    por_caso: dict[str, set] = {}
    for fila in curso.experimento_local(determinista, ejemplos, evaluadores=[acierto],
                                        repeticiones=5):
        clave = str(fila["example"].id)
        for resultado in fila["evaluation_results"]["results"]:
            por_caso.setdefault(clave, set()).add(resultado.score)

    assert all(len(puntuaciones) == 1 for puntuaciones in por_caso.values())


def test_la_banda_de_ruido_depende_del_tamano_del_conjunto():
    """La tabla que resume el notebook 09: la MISMA diferencia es ruido o mejora
    según cuántos casos la respalden."""
    import math

    def decidir(nueva, anterior, *, n, sigmas=2.0):
        p = (nueva + anterior) / 2
        banda = sigmas * math.sqrt(2 * p * (1 - p) / n)
        if nueva - anterior < -banda:
            return "BLOQUEA"
        if nueva - anterior > banda:
            return "MEJORA"
        return "RUIDO"

    assert decidir(0.78, 0.72, n=20) == "RUIDO"
    assert decidir(0.78, 0.72, n=1000) == "MEJORA"
    assert decidir(0.40, 0.72, n=30) == "BLOQUEA"


def test_evaluate_comparative_permite_desordenar_las_posiciones():
    """`randomize_order` es el arreglo directo del sesgo de posición del notebook 08."""
    import inspect

    from langsmith.evaluation import evaluate_comparative

    parametros = inspect.signature(evaluate_comparative).parameters
    assert "randomize_order" in parametros
    assert parametros["randomize_order"].default is False     # hay que pedirlo
