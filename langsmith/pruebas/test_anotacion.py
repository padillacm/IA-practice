"""Pruebas del módulo 3: anotación humana y acuerdo entre anotadores.

Aquí no se prueba el SDK: se prueban las **matemáticas del material**. Las funciones de
kappa que enseña el notebook 11 son código que quien siga el curso va a copiar y usar
para decidir si su rúbrica está lista. Si están mal, el módulo entero da consejos malos.
"""

from __future__ import annotations

import collections
import itertools

import pytest


# ------------------------------------------------------------------------------------
# Las funciones tal y como las enseña el notebook 11
# ------------------------------------------------------------------------------------


def acuerdo_simple(a, b):
    return sum(x == y for x, y in zip(a, b)) / len(a)


def kappa_de_cohen(a, b):
    observado = acuerdo_simple(a, b)
    n = len(a)
    categorias = set(a) | set(b)
    esperado = sum((a.count(c) / n) * (b.count(c) / n) for c in categorias)
    return 1.0 if esperado == 1 else (observado - esperado) / (1 - esperado)


def kappa_de_fleiss(anotaciones):
    n_anotadores = len(anotaciones)
    n_casos = len(anotaciones[0])
    categorias = sorted({v for fila in anotaciones for v in fila})
    conteos = [[sum(fila[i] == c for fila in anotaciones) for c in categorias]
               for i in range(n_casos)]
    p_por_caso = [(sum(n * n for n in fila) - n_anotadores) /
                  (n_anotadores * (n_anotadores - 1)) for fila in conteos]
    p_observado = sum(p_por_caso) / n_casos
    p_categoria = [sum(fila[j] for fila in conteos) / (n_casos * n_anotadores)
                   for j in range(len(categorias))]
    p_esperado = sum(p * p for p in p_categoria)
    return (p_observado - p_esperado) / (1 - p_esperado) if p_esperado != 1 else 1.0


# ------------------------------------------------------------------------------------
# Kappa de Cohen
# ------------------------------------------------------------------------------------


def test_acuerdo_perfecto_da_kappa_uno():
    a = [1, 0, 1, 1, 0, 0, 1, 0]
    assert kappa_de_cohen(a, a) == pytest.approx(1.0)


def test_desacuerdo_total_da_kappa_negativa():
    a = [1, 0, 1, 0, 1, 0]
    b = [0, 1, 0, 1, 0, 1]
    assert kappa_de_cohen(a, b) < 0


def test_el_porcentaje_de_acuerdo_miente_con_una_clase_dominante():
    """La demostración central del notebook 11.

    Dos anotadores sobre un conjunto con el 95 % de «sí»: uno mira y el otro no.
    El acuerdo simple dice 95 %; kappa dice que no hay criterio.
    """
    mira = [1] * 19 + [0]
    no_mira = [1] * 20

    assert acuerdo_simple(mira, no_mira) == pytest.approx(0.95)
    assert kappa_de_cohen(mira, no_mira) == pytest.approx(0.0, abs=0.05)


def test_kappa_contra_el_valor_de_referencia():
    """Un caso con el resultado conocido, para comprobar que la fórmula es la correcta.

    Tabla 2x2 clásica: 20 acuerdos en «sí», 15 en «no», 5 y 10 discrepancias.
    Acuerdo observado = 0.70; esperado = 0.50; kappa = 0.40.
    """
    a = [1] * 20 + [1] * 5 + [0] * 10 + [0] * 15
    b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15

    assert acuerdo_simple(a, b) == pytest.approx(0.70)
    assert kappa_de_cohen(a, b) == pytest.approx(0.40, abs=0.01)


def test_kappa_es_simetrica():
    a = [1, 0, 1, 1, 0, 1, 0, 0]
    b = [1, 1, 1, 0, 0, 1, 0, 1]
    assert kappa_de_cohen(a, b) == pytest.approx(kappa_de_cohen(b, a))


# ------------------------------------------------------------------------------------
# Kappa de Fleiss
# ------------------------------------------------------------------------------------


def test_fleiss_coincide_con_cohen_para_dos_anotadores():
    """Fleiss generaliza a Cohen: con dos anotadores deben dar prácticamente lo mismo."""
    a = [1, 0, 1, 1, 0, 1, 0, 0, 1, 0]
    b = [1, 1, 1, 0, 0, 1, 0, 1, 1, 0]
    assert kappa_de_fleiss([a, b]) == pytest.approx(kappa_de_cohen(a, b), abs=0.1)


def test_fleiss_con_acuerdo_perfecto():
    a = [1, 0, 1, 1, 0, 0]
    assert kappa_de_fleiss([a, a, a]) == pytest.approx(1.0)


# ------------------------------------------------------------------------------------
# El diagnóstico de una ronda de anotación
# ------------------------------------------------------------------------------------


def _interpretar(k):
    return "listo" if k >= 0.6 else "no listo"


def diagnosticar(anotaciones: dict[str, list[int]]) -> list[str]:
    """La función del ejercicio 1 del notebook 11."""
    nombres = list(anotaciones)
    avisos = []

    for nombre in nombres:
        valores = anotaciones[nombre]
        frecuente = collections.Counter(valores).most_common(1)[0][1] / len(valores)
        if frecuente > 0.9:
            avisos.append(f"{nombre}:no-mira")

    for nombre in nombres:
        otros = [n for n in nombres if n != nombre]
        if len(otros) < 2:
            continue
        contra_el = [kappa_de_cohen(anotaciones[nombre], anotaciones[o]) for o in otros]
        entre_ellos = [kappa_de_cohen(anotaciones[x], anotaciones[y])
                       for x, y in itertools.combinations(otros, 2)]
        if max(contra_el) < 0.3 and min(entre_ellos) > 0.6:
            avisos.append(f"{nombre}:desalineado")

    global_ = (kappa_de_fleiss(list(anotaciones.values())) if len(nombres) > 2
               else kappa_de_cohen(*anotaciones.values()))
    if global_ < 0.6:
        avisos.append("rubrica:no-lista")
    return avisos


def test_se_detecta_a_quien_no_esta_mirando():
    bueno = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    avisos = diagnosticar({"ana": bueno, "luis": bueno, "marta": [1] * 10})
    assert "marta:no-mira" in avisos
    assert "marta:desalineado" in avisos


def test_cuando_nadie_se_entiende_no_se_señala_a_nadie():
    """La condición doble del notebook: para acusar a alguien, los demás tienen que
    entenderse entre sí. Si nadie coincide con nadie, el problema es la rúbrica."""
    uno = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    dos = [1, 1, 0, 0, 1, 1, 0, 0, 1, 1]
    tres = [0, 0, 1, 1, 1, 0, 0, 1, 0, 1]

    avisos = diagnosticar({"ana": uno, "luis": dos, "sara": tres})
    assert "rubrica:no-lista" in avisos
    assert not any("desalineado" in a for a in avisos)


def test_una_ronda_sana_no_produce_avisos():
    bueno = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]
    casi = [1, 0, 1, 0, 1, 0, 1, 1, 1, 0]      # una discrepancia
    assert diagnosticar({"ana": bueno, "luis": casi}) == []


# ------------------------------------------------------------------------------------
# El consenso
# ------------------------------------------------------------------------------------


def test_un_numero_par_de_anotadores_no_mejora_al_impar_anterior():
    """El resultado poco intuitivo del ejercicio 2: dos anotadores no son mejores que
    uno, porque los empates son casos que no sabes resolver."""
    import random
    import statistics

    def consenso(n_anotadores, *, error=0.15, casos=200, semilla=0):
        aleatorio = random.Random(semilla)
        aciertos = 0
        for _ in range(casos):
            real = aleatorio.randint(0, 1)
            votos = [real if aleatorio.random() > error else 1 - real
                     for _ in range(n_anotadores)]
            favor = sum(votos)
            elegido = (aleatorio.randint(0, 1) if favor * 2 == len(votos)
                       else int(favor * 2 > len(votos)))
            aciertos += int(elegido == real)
        return aciertos / casos

    def media(n):
        return statistics.mean(consenso(n, semilla=s) for s in range(20))

    uno, dos, tres = media(1), media(2), media(3)
    assert abs(dos - uno) < 0.03        # el segundo anotador no aporta
    assert tres > uno + 0.05            # el tercero sí
