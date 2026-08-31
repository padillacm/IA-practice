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
