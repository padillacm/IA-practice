"""Pruebas del módulo 4: monitorización, reglas y prompts.

Como en el módulo 3, aquí se prueban sobre todo las decisiones del material —qué se mide
y cómo se compara— porque son código que quien siga el curso va a copiar a su panel.
"""

from __future__ import annotations

import collections
import inspect
import random
import statistics

import pytest


# ------------------------------------------------------------------------------------
# Notebook 13 · monitorizar
# ------------------------------------------------------------------------------------


def _semana(semilla: int = 3) -> list[dict]:
    """La misma semana simulada del notebook 13: un cambio el día 4 que degrada el
    comportamiento sin tocar la disponibilidad."""
    aleatorio = random.Random(semilla)
    peticiones = []
    for dia in range(7):
        degradado = dia >= 4
        for _ in range(200):
            vueltas = aleatorio.choice([1, 1, 1, 2] if not degradado else [1, 2, 3, 3])
            peticiones.append({
                "dia": dia,
                "error": aleatorio.random() < 0.01,
                "latencia_ms": aleatorio.gauss(900, 200),
                "tokens": 400 * vueltas + aleatorio.randint(-50, 50),
                "vueltas": vueltas,
                "escalado": aleatorio.random() < (0.22 if degradado else 0.06),
            })
    return peticiones


def test_las_metricas_de_salud_no_ven_la_degradacion():
    """El argumento del notebook 13, medido.

    El agente pasa a dar el doble de vueltas y a escalar cuatro veces más, y la tasa de
    error y la latencia por llamada no se mueven.
    """
    trafico = _semana()
    antes = [p for p in trafico if p["dia"] < 4]
    despues = [p for p in trafico if p["dia"] >= 4]

    def media(peticiones, clave):
        return statistics.mean(p[clave] for p in peticiones)

    # Salud: quieta.
    assert abs(media(antes, "latencia_ms") - media(despues, "latencia_ms")) < 60
    assert abs(media(antes, "error") - media(despues, "error")) < 0.02

    # Comportamiento: movida, y mucho.
    assert media(despues, "vueltas") > media(antes, "vueltas") * 1.5
    assert media(despues, "escalado") > media(antes, "escalado") * 2


def test_la_media_del_juez_baja_sin_que_el_sistema_cambie():
    """La primera métrica trampa: una media sobre tráfico que cambia de composición.

    El mismo sistema puntúa peor porque entraron clientes con consultas más difíciles.
    Partida por segmento, cada uno queda estable.
    """
    aleatorio = random.Random(1)
    def calidad(p):
        return 0.9 if p["plan"] == "free" else 0.6

    mes_1 = [{"plan": aleatorio.choice(["free"] * 8 + ["pro", "business"])}
             for _ in range(500)]
    mes_2 = [{"plan": aleatorio.choice(["free"] * 3 + ["pro"] * 4 + ["business"] * 3)}
             for _ in range(500)]

    global_1 = statistics.mean(calidad(p) for p in mes_1)
    global_2 = statistics.mean(calidad(p) for p in mes_2)
    assert global_2 < global_1 - 0.08          # «cae» la calidad

    def por_plan(mes):
        grupos = collections.defaultdict(list)
        for p in mes:
            grupos[p["plan"]].append(calidad(p))
        return {k: statistics.mean(v) for k, v in grupos.items()}

    # Y sin embargo cada segmento es idéntico: no hubo regresión.
    assert por_plan(mes_1) == por_plan(mes_2)


def test_la_alerta_del_silencio_va_primero():
    """Detalle de orden con consecuencias: si la comprobación de «no hay datos» va al
    final, el cálculo de las métricas revienta con una lista vacía y la alerta que más
    falta hace nunca se emite."""
    def alertas(hoy, referencia):
        if not hoy:
            return ["NO HAY DATOS"]
        return [f"escalados {statistics.mean(p['escalado'] for p in hoy):.2f}"]

    assert alertas([], _semana()) == ["NO HAY DATOS"]   # no lanza ZeroDivisionError


def test_una_linea_base_de_cero_no_se_esconde_como_cero_por_ciento():
    """`peticiones_largas` pasa de 0 a la mitad del tráfico. Dividir entre cero daría
    0 % y escondería el cambio más brutal de la tabla."""
    def comparar(antes, ahora, *, umbral=0.3):
        if antes:
            return abs((ahora - antes) / antes) > umbral
        return bool(ahora)

    assert comparar(0.0, 0.508) is True
    assert comparar(0.0, 0.0) is False
    assert comparar(0.10, 0.11) is False


def test_get_run_stats_acepta_los_filtros_que_ensena_el_notebook():
    """Los tres parámetros con los que se construyen las consultas del panel."""
    from langsmith import Client

    parametros = inspect.signature(Client.get_run_stats).parameters
    for necesario in ("filter", "trace_filter", "is_root", "project_names", "start_time"):
        assert necesario in parametros


def test_un_umbral_bajo_produce_demasiadas_falsas_alarmas():
    """La forma de elegir el umbral: midiendo sobre el propio ruido, no a ojo.

    Un umbral que salta veinticinco veces al mes sobre tráfico sano se silencia, y una
    alerta silenciada no vuelve.
    """
    def falsas_alarmas(umbral, *, semanas=10):
        saltos = dias = 0
        for semilla in range(semanas):
            aleatorio = random.Random(1000 + semilla)
            sana = [{"dia": d, "escalado": aleatorio.random() < 0.06}
                    for d in range(7) for _ in range(200)]
            for dia in range(1, 7):
                hoy = [p for p in sana if p["dia"] == dia]
                ayer = [p for p in sana if p["dia"] == dia - 1]
                a = sum(p["escalado"] for p in hoy) / len(hoy)
                b = sum(p["escalado"] for p in ayer) / len(ayer)
                dias += 1
                if b and abs((a - b) / b) > umbral:
                    saltos += 1
        return 30 * saltos / dias

    con_umbral_bajo = falsas_alarmas(0.10)
    con_umbral_alto = falsas_alarmas(0.80)
    assert con_umbral_bajo > 10          # se silenciaría en dos semanas
    assert con_umbral_alto < 5           # este sí se puede mantener


# ------------------------------------------------------------------------------------
# Notebook 14 · reglas y evaluación en línea
# ------------------------------------------------------------------------------------


def test_el_sdk_no_expone_reglas_paneles_ni_alertas():
    """Afirmación fuerte del notebook 14, que condiciona cómo se trabaja.

    Si algún día aparecen, esta prueba salta y el notebook hay que actualizarlo —a
    mejor, porque entonces se podrían versionar.
    """
    from langsmith import Client

    publicos = {m for m in dir(Client) if not m.startswith("_")}
    for ausente in ("rules", "dashboards", "alerts", "monitors"):
        assert ausente not in publicos


def test_los_evaluadores_en_linea_si_tienen_api_publica():
    from langsmith import Client

    assert isinstance(vars(Client).get("evaluators"), property)
    assert isinstance(vars(Client).get("annotation_queues"), property)


def test_los_issues_solo_se_alcanzan_por_un_accesor_privado():
    """El matiz que el notebook 14 deja escrito: el recurso existe en el cliente
    generado y `Client` no lo publica, así que llegar a él es usar API privada."""
    from langsmith import Client
    from langsmith._openapi_client import _client as generado

    assert not hasattr(Client, "issues")
    assert "issues" in dir(generado.Langsmith)
    assert hasattr(Client, "_get_langsmith_api")


def test_el_evaluador_de_codigo_se_define_con_codigo_y_lenguaje():
    """El hallazgo del notebook 14: se sube Python que corre en el lado de LangSmith,
    sobre el 100 % del tráfico y sin gastar una traza de juez."""
    from langsmith._openapi_client.types import online_evaluator_create_params as p

    assert set(p.CreateOnlineCodeEvaluatorRequestParam.__annotations__) == {"code", "language"}
    assert "llm" in p.OnlineEvaluatorType.__args__
    assert "code" in p.OnlineEvaluatorType.__args__


def test_el_juez_en_linea_referencia_un_prompt_del_hub():
    """No lleva el prompt dentro: lleva un handle y un commit. O sea que el prompt del
    juez de producción está versionado quieras o no. Es el puente con el notebook 15."""
    from langsmith._openapi_client.types import online_evaluator_create_params as p

    campos = set(p.CreateOnlineLlmEvaluatorRequestParam.__annotations__)
    assert {"prompt_repo_handle", "commit_hash_or_tag"} <= campos


def test_el_muestreo_estratificado_ve_todos_los_problemas():
    """La comparación que decide cómo gastar el presupuesto de evaluación en línea.

    Al mismo coste, el estratificado ve el 100 % de lo problemático y el uniforme
    una fracción.
    """
    import hashlib

    aleatorio = random.Random(4)
    trafico = [{"id": f"pet-{i}",
                "escalado": aleatorio.random() < 0.04,
                "feedback_negativo": aleatorio.random() < 0.01,
                "vueltas": 4 if aleatorio.random() < 0.02 else aleatorio.choice([1, 1, 1, 2]),
                "plan": aleatorio.choice(["free"] * 20 + ["pro"] * 8 + ["enterprise"])}
               for i in range(10_000)]

    def problematica(p):
        return p["escalado"] or p["feedback_negativo"] or p["vueltas"] > 3

    def estratificado(p, *, tasa=0.02):
        if problematica(p) or p["plan"] == "enterprise":
            return True
        digito = int(hashlib.blake2b(p["id"].encode(), digest_size=4).hexdigest(), 16)
        return (digito % 10_000) < tasa * 10_000

    elegidas = [p for p in trafico if estratificado(p)]
    problemas = [p for p in trafico if problematica(p)]
    vistos = [p for p in problemas if estratificado(p)]

    # Mismo coste, muestreo uniforme.
    tasa = len(elegidas) / len(trafico)
    otro = random.Random(9)
    uniformes = [p for p in trafico if otro.random() < tasa]
    vistos_uniforme = [p for p in uniformes if problematica(p)]

    assert len(vistos) == len(problemas)                       # el 100 %
    assert len(vistos_uniforme) < len(problemas) * 0.3         # una fracción
    assert len(elegidas) < len(trafico) * 0.25                 # y cuesta poco


def test_el_muestreo_por_hash_es_reproducible():
    """Con `random()` la decisión cambia según cuándo mires; con un hash es una función
    pura de la petición, así que dos servicios coinciden sin coordinarse."""
    import hashlib

    def decide(identificador, *, tasa=0.02):
        digito = int(hashlib.blake2b(identificador.encode(), digest_size=4).hexdigest(), 16)
        return (digito % 10_000) < tasa * 10_000

    ids = [f"pet-{i}" for i in range(500)]
    assert [decide(i) for i in ids] == [decide(i) for i in ids]
    # Y la tasa sale donde debe.
    assert 0 < sum(decide(i) for i in ids) / len(ids) < 0.08


def test_la_regla_sin_cortafuegos_se_come_el_conjunto():
    """«Todo lo que falla va al dataset» pasa de 40 casos a cientos en un año, y un
    conjunto que tarda media hora deja de ejecutarse."""
    tipos = ["no da el plazo", "herramienta equivocada", "se inventa una cifra",
             "responde en otro idioma", "cita una fuente que no existe"]
    categorias = [f"cat{i}" for i in range(8)]

    def un_ano(con_filtro):
        aleatorio = random.Random(2)
        dataset = []
        for _ in range(12):
            for _ in range(40):
                caso = {"categoria": aleatorio.choice(categorias),
                        "tipo": aleatorio.choice(tipos)}
                firma = (caso["categoria"], caso["tipo"])
                if con_filtro and any((c["categoria"], c["tipo"]) == firma for c in dataset):
                    continue
                dataset.append(caso)
        return len(dataset)

    sin_filtro, con_filtro = un_ano(False), un_ano(True)
    assert sin_filtro > 400
    assert con_filtro <= len(categorias) * len(tipos)      # como mucho, uno de cada tipo
    assert con_filtro < sin_filtro / 5


# ------------------------------------------------------------------------------------
# Notebook 15 · prompts versionados
# ------------------------------------------------------------------------------------


def test_la_cache_de_prompts_caduca_a_los_cinco_minutos():
    """El notebook enseña «he cambiado el prompt y no pasa nada» como consecuencia de
    unos valores por defecto concretos. Si el SDK los cambia, la explicación deja de
    ser cierta y hay que reescribirla, no descubrirlo en producción."""
    from langsmith import prompt_cache

    assert prompt_cache.DEFAULT_PROMPT_CACHE_MAX_SIZE == 100
    assert prompt_cache.DEFAULT_PROMPT_CACHE_TTL_SECONDS == 300        # cinco minutos
    assert prompt_cache.DEFAULT_PROMPT_CACHE_REFRESH_INTERVAL_SECONDS == 60

    # Y los defaults de la clase son los mismos que las constantes: el notebook imprime
    # las constantes y habla del objeto.
    parametros = inspect.signature(prompt_cache.PromptCache.__init__).parameters
    assert parametros["max_size"].default == prompt_cache.DEFAULT_PROMPT_CACHE_MAX_SIZE
    assert parametros["ttl_seconds"].default == prompt_cache.DEFAULT_PROMPT_CACHE_TTL_SECONDS


def test_las_tres_formas_de_gobernar_la_cache_existen():
    """Global, por cliente y por llamada. El notebook las presenta como una tabla de
    decisión, así que las tres tienen que ser reales."""
    import langsmith
    from langsmith import Client

    assert callable(langsmith.configure_global_prompt_cache)
    assert "disable_prompt_cache" in inspect.signature(Client.__init__).parameters
    assert "skip_cache" in inspect.signature(Client.pull_prompt).parameters


def test_traerse_un_prompt_publico_ajeno_esta_bloqueado(sin_servicio):
    """El bloqueo es el argumento entero del apartado 4: un prompt del Hub es un objeto
    de LangChain serializado, y deserializar el de otra persona es superficie de ataque.
    Se comprueba sin red, con la sesión muda del curso."""
    from langsmith import Client

    from utils.curso import _SesionMuda

    c = Client(api_key="local", session=_SesionMuda(), auto_batch_tracing=False)

    with pytest.raises(ValueError) as fallo:
        c.pull_prompt("otra-persona/su-prompt-genial")

    mensaje = str(fallo.value)
    assert "dangerously_pull_public_prompt" in mensaje
    assert "untrusted" in mensaje

    # Y el escape es explícito y está donde el notebook dice.
    assert "dangerously_pull_public_prompt" in inspect.signature(Client.pull_prompt).parameters


def test_el_hub_expone_etiquetas_por_commit():
    """«En producción, nunca sin etiqueta» solo se sostiene si se puede etiquetar un
    commit al publicarlo y listar después qué etiquetas tiene."""
    from langsmith import Client

    publicar = inspect.signature(Client.push_prompt).parameters
    assert "commit_tags" in publicar          # etiquetas de ESTA versión
    assert "tags" in publicar                 # etiquetas del prompt entero
    assert "parent_commit_hash" in publicar

    assert "prompt_identifier" in inspect.signature(Client.list_prompt_commits).parameters


def test_la_huella_del_prompt_distingue_versiones_y_no_commits():
    """La huella del notebook es del texto, no del objeto: dos commits con el mismo
    texto dan la misma huella. Eso es lo que detecta un reetiquetado que no cambia nada
    y, al revés, un cambio de texto colado bajo el mismo nombre."""
    import hashlib

    from langchain_core.prompts import ChatPromptTemplate

    def huella(plantilla) -> str:
        texto = "\n".join(str(m) for m in plantilla.messages)
        return hashlib.blake2b(texto.encode(), digest_size=6).hexdigest()

    v1 = ChatPromptTemplate.from_messages([("system", "Clasifica: {categorias}.")])
    v1_otra_vez = ChatPromptTemplate.from_messages([("system", "Clasifica: {categorias}.")])
    v2 = ChatPromptTemplate.from_messages([("system", "Clasifica: {categorias}. Minúsculas.")])

    assert huella(v1) == huella(v1_otra_vez)      # mismo texto, misma huella
    assert huella(v1) != huella(v2)


def test_la_puerta_del_prompt_bloquea_la_etiqueta_movida_a_mano():
    """La guarda del apartado 5. Los tres escenarios del notebook, más el que no sale:
    dos commits con la etiqueta «produccion» a la vez."""

    def puerta(historial):
        problemas = []
        en_produccion = [c for c in historial if "produccion" in c["tags"]]
        if len(en_produccion) != 1:
            problemas.append(f"la etiqueta «produccion» apunta a {len(en_produccion)} commits")
        for commit in en_produccion:
            if not commit.get("experimento"):
                problemas.append(f"{commit['hash'][:8]} sin experimento")
            elif not commit.get("aprobado"):
                problemas.append(f"{commit['hash'][:8]} no pasó la puerta")
        return problemas

    aprobado = {"hash": "a1b2c3d4", "tags": ["produccion"],
                "experimento": "ci-482", "aprobado": True}
    candidata = {"hash": "e5f6a7b8", "tags": ["candidata"],
                 "experimento": "ci-491", "aprobado": False}

    assert puerta([aprobado, candidata]) == []
    assert puerta([{"hash": "e5f6a7b8", "tags": ["produccion", "candidata"],
                    "experimento": None}])
    assert puerta([{"hash": "c9d0e1f2", "tags": ["produccion"],
                    "experimento": "ci-500", "aprobado": False}])
    # Ninguno en producción, y dos a la vez: los dos casos que una interfaz no impide.
    assert puerta([candidata])
    assert puerta([aprobado, dict(candidata, tags=["produccion"])])


def test_el_rollback_por_cache_es_mas_lento_que_reiniciar_es_falso():
    """La fila que sorprende del ejercicio 2: con la caché por defecto el rollback tarda
    cinco minutos, MENOS que rotar los procesos, y durante ese rato conviven las dos
    versiones. El material afirma las dos cosas; aquí se comprueban."""
    from langsmith import prompt_cache

    ttl = prompt_cache.DEFAULT_PROMPT_CACHE_TTL_SECONDS
    por_reinicio = 12 * 40                      # 12 procesos, 40 s de arranque

    assert ttl < por_reinicio                   # la caché es más rápida que reiniciar
    assert ttl > 60                             # y aun así, más de un minuto conviviendo

    # Durante la ventana, un proceso que cacheó antes del cambio sirve lo viejo.
    cacheado_en = {"proceso-a": 0, "proceso-b": 290}
    cambio_en = 100
    sirven_lo_viejo = [p for p, t in cacheado_en.items() if t < cambio_en < t + ttl]
    assert sirven_lo_viejo == ["proceso-a"]
