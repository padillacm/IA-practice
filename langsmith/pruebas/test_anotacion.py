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


# ------------------------------------------------------------------------------------
# Notebook 12 · alinear el juez
# ------------------------------------------------------------------------------------


def test_los_ejemplos_del_juez_llegan_a_su_prompt():
    """El mecanismo del que depende la palanca 2, que es la más potente del notebook 12.

    `openevals` inyecta cada ejemplo como un bloque <example> con entrada, salida,
    razonamiento y puntuación. Si eso cambiara, la técnica del notebook deja de funcionar.
    """
    from openevals.llm import create_llm_as_judge

    from utils import curso

    capturado = {}

    def espia(texto):
        capturado["prompt"] = texto
        return 1.0, "ok"

    juez = create_llm_as_judge(
        prompt="RUBRICA\n{inputs}\n{outputs}",
        judge=curso.juez_local(espia),
        feedback_key="x",
        few_shot_examples=[
            {"inputs": {"m": "¿cuándo?"}, "outputs": {"r": "En 5 días."},
             "score": 1.0, "reasoning": "contiene el dato"},
            {"inputs": {"m": "¿cuándo?"}, "outputs": {"r": "Lo revisamos."},
             "score": 0.0, "reasoning": "no contiene el dato"},
        ],
    )
    juez(inputs={"m": "hola"}, outputs={"r": "adios"})

    prompt = capturado["prompt"]
    assert prompt.count("<example>") == 2
    assert "<score>1.0</score>" in prompt
    assert "<score>0.0</score>" in prompt
    assert "contiene el dato" in prompt


def test_la_matriz_de_confusion_distingue_indulgente_de_severo():
    """Dónde se equivoca el juez importa más que cuánto, y los dos errores no cuestan
    lo mismo: el indulgente produce confianza."""
    humano = [1, 1, 0, 0, 1, 0]
    indulgente = [1, 1, 1, 1, 1, 1]      # aprueba todo
    severo = [0, 0, 0, 0, 0, 0]          # suspende todo

    def matriz(h, j):
        return (sum(x == 0 and y == 1 for x, y in zip(h, j)),
                sum(x == 1 and y == 0 for x, y in zip(h, j)))

    assert matriz(humano, indulgente) == (3, 0)
    assert matriz(humano, severo) == (0, 3)


def test_los_ejemplos_se_cogen_de_los_dos_tipos_de_error():
    """Solo indulgentes y el juez se vuelve severo; solo severos y al revés."""
    respuestas = [f"r{i}" for i in range(8)]
    humano = [1, 1, 1, 1, 0, 0, 0, 0]
    juez = [0, 0, 1, 1, 1, 1, 0, 0]      # 2 severos y 2 indulgentes

    indulgentes = [(r, h) for r, h, j in zip(respuestas, humano, juez) if h == 0 and j == 1]
    severos = [(r, h) for r, h, j in zip(respuestas, humano, juez) if h == 1 and j == 0]

    mitad = 4 // 2
    elegidos = indulgentes[:mitad] + severos[:mitad]

    assert len(elegidos) == 4
    assert sum(1 for _, h in elegidos if h == 0) == 2
    assert sum(1 for _, h in elegidos if h == 1) == 2


def test_un_juez_que_memoriza_se_hunde_fuera_de_su_conjunto():
    """El ejercicio 2 del notebook 12, y la razón de reservar parte del conjunto.

    Un juez que solo reconoce las frases que vio saca una kappa decente sobre ellas y
    se derrumba en cuanto ve una nueva. Por dentro no se distingue de uno alineado.
    """
    vistas = {"tiene el dato: 5 días": 1, "solo cortesía": 0}

    def juez_que_memoriza(respuesta):
        return vistas.get(respuesta, 1)      # lo que no conoce, lo aprueba

    dentro = list(vistas)
    humano_dentro = [vistas[r] for r in dentro]
    juez_dentro = [juez_que_memoriza(r) for r in dentro]

    fuera = ["otra con dato: 3 días", "otra de cortesía", "más cortesía", "dato: 7 euros"]
    humano_fuera = [1, 0, 0, 1]
    juez_fuera = [juez_que_memoriza(r) for r in fuera]

    assert kappa_de_cohen(humano_dentro, juez_dentro) == pytest.approx(1.0)
    assert kappa_de_cohen(humano_fuera, juez_fuera) <= 0.0


def test_un_evaluador_de_codigo_puede_bastar():
    """El número que hay que mirar antes de meter un juez en producción.

    En tareas donde «bueno» tiene una marca formal, dos líneas de expresión regular
    sacan una kappa comparable a la del juez, gratis y sin no-determinismo.
    """
    import re

    respuestas = [
        ("Tu reembolso llega en 5 días hábiles.", 1),
        ("El cargo del 12/09 se devuelve el 17/09.", 1),
        ("Puedes cambiarlo desde Ajustes > Suscripción.", 1),
        ("Son 87 tickets abiertos.", 1),
        ("Gracias por escribirnos, lo revisamos.", 0),
        ("Lamentamos las molestias, te contactaremos.", 0),
        ("Estamos en ello.", 0),
        ("Entendemos tu frustración y lo solucionaremos.", 0),
    ]
    humano = [e for _, e in respuestas]
    codigo = [int(bool(re.search(r"\d", r)) or ">" in r) for r, _ in respuestas]

    assert kappa_de_cohen(humano, codigo) >= 0.7


# ------------------------------------------------------------------------------------
# Proyecto P3 · la decisión de si el juez entra
# ------------------------------------------------------------------------------------


def _decidir(resultados, *, minimo_kappa=0.6, margen_sobre_codigo=0.10):
    """El criterio del proyecto P3, con sus tres condiciones."""
    codigo = resultados["codigo"]["kappa"]
    nombres = [n for n in resultados if n != "codigo"]
    mejor_nombre = max(nombres, key=lambda n: (resultados[n]["kappa"], -nombres.index(n)))
    mejor = resultados[mejor_nombre]

    razones = []
    if mejor["kappa"] < minimo_kappa:
        razones.append("por debajo del umbral")
    if mejor["kappa"] < codigo + margen_sobre_codigo:
        razones.append("no supera al código")
    if mejor["indulgente"] > mejor["severo"]:
        razones.append("indulgente")
    return ("NO" if razones else "SI"), razones


def test_un_juez_que_empata_con_el_codigo_no_entra():
    """El desenlace del proyecto P3, y la razón de que sea un proyecto y no un tutorial.

    El juez no es malo —saca una kappa estupenda—: es que una expresión regular saca la
    misma, y esa no cuesta trazas ni mete no-determinismo.
    """
    decision, razones = _decidir({
        "codigo": {"kappa": 0.90, "indulgente": 0, "severo": 1},
        "juez": {"kappa": 0.90, "indulgente": 0, "severo": 1},
    })
    assert decision == "NO"
    assert "no supera al código" in razones


def test_un_juez_claramente_mejor_si_entra():
    decision, razones = _decidir({
        "codigo": {"kappa": 0.55, "indulgente": 4, "severo": 5},
        "juez": {"kappa": 0.85, "indulgente": 1, "severo": 3},
    })
    assert decision == "SI"
    assert razones == []


def test_un_juez_bueno_pero_indulgente_no_entra():
    """La condición que más gente omite: entre dos con la misma kappa, prefiere el
    severo. Los errores del severo generan alarmas; los del indulgente, silencio."""
    decision, razones = _decidir({
        "codigo": {"kappa": 0.50, "indulgente": 5, "severo": 4},
        "juez": {"kappa": 0.75, "indulgente": 6, "severo": 1},
    })
    assert decision == "NO"
    assert "indulgente" in razones


def test_a_igualdad_de_kappa_gana_el_juez_mas_simple():
    """Menos piezas que mantener y menos cosas que se desalineen."""
    resultados = {
        "codigo": {"kappa": 0.40, "indulgente": 3, "severo": 3},
        "juez simple": {"kappa": 0.80, "indulgente": 1, "severo": 3},
        "juez complejo": {"kappa": 0.80, "indulgente": 1, "severo": 3},
    }
    nombres = [n for n in resultados if n != "codigo"]
    mejor = max(nombres, key=lambda n: (resultados[n]["kappa"], -nombres.index(n)))
    assert mejor == "juez simple"


def test_la_revision_mensual_detecta_la_desalineacion():
    """Un juez alineado se desalinea solo: el proveedor cambia el modelo, tus datos
    cambian, tu criterio cambia. Veinte casos ya anotados, una vez al mes."""
    def revision(kappa_ahora, kappa_referencia, *, caida_maxima=0.15):
        return (kappa_referencia - kappa_ahora) <= caida_maxima

    assert revision(0.88, 0.90)          # variación normal
    assert not revision(0.60, 0.90)      # caída de 0,30: alerta
    assert not revision(-0.33, 0.90)     # el modelo cambió bajo el mismo nombre


def test_la_particion_se_hace_antes_y_las_mitades_se_parecen():
    """Si el corte deja casi todos los «sí» en una mitad, la kappa de la reserva mide
    otra cosa. Hay que comprobarlo antes de fiarse del número."""
    import random

    anotado = [(f"con dato {i}", 1) for i in range(25)] + \
              [(f"sin dato {i}", 0) for i in range(25)]
    random.Random(5).shuffle(anotado)

    corte = int(len(anotado) * 0.6)
    alinear, reserva = anotado[:corte], anotado[corte:]

    proporcion_a = sum(e for _, e in alinear) / len(alinear)
    proporcion_r = sum(e for _, e in reserva) / len(reserva)
    assert abs(proporcion_a - proporcion_r) < 0.15
