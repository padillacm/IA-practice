"""Genera el módulo 15_calidad_regresion: README, lección, proyecto y dashboard.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_15.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "15_calidad_regresion"

IMPORTS_15 = '''
import collections, dataclasses, json, math, re, time
from supportops.instrument import CompositeInstrumentor
from supportops.telemetry import OTelInstrumentor, setup_telemetry
from supportops.quality_eval import (CaseCollector, MockJudge, OnlineEvaluator, RateSampler, StratifiedSampler, VersionTagInstrumentor, confusion, simulate_feedback,
                                     wilson_interval)
from supportops.regression import (PROMPT_VERSIONS, Cusum, GoldenCase, LivePipeline, ReleaseGate, behavior_fingerprint, bootstrap_diff, canary_route, event_records,
                                   golden_to_tickets, js_divergence, ks_2samp, make_agent, mcnemar_exact, min_detectable_drop, novel_topic_tickets,
                                   peeking_false_positive_rate, psi, psi_categorical, replay, required_n_per_arm, run_version, select_golden, sprt_bernoulli,
                                   trace_shapes, trajectory_match, two_proportion_test, version_report)
STACK = check_stack("core+metrics")
LIVE = not STACK.degraded
'''

DATA_15 = '''
N = 800 if FAST_DEV_RUN else 3000
TK = generate_tickets(N, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)         # MISMO tráfico para todas las versiones (comparación apareada)
J = MockJudge(SEED)
RUN = {}
for v in ("v1", "v2", "v2.1"):
    res, cases = run_version(v, TK)
    RUN[v] = {"res": res, "cases": cases, "verd": [J.evaluate(c) for c in cases]}
q = lambda v: float(np.mean([x.scores["groundedness"].label == "pass" for x in RUN[v]["verd"]]))
print({v: f"groundedness OK {q(v):.1%}" for v in RUN})
'''


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "15_calidad_regresion.ipynb", "Módulo 15 · Calidad y regresión de agentes")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 15 · Calidad y regresión: cazar el cambio que empeora al agente sin que ningún dashboard lo vea

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Opcional: `--profile core --profile metrics` (sección 9). Sin Docker todo funciona en **modo degradado** (telemetría en memoria, mismo esquema). Funciona en Colab |
    | **RAM aproximada** | < 500 MB sin stack · ≈ 1,2 GB con `core` + `metrics` |
    | **Prerrequisitos** | Módulo 14 (evaluación online: juez, muestreo, sesgos), 09 (métricas), 07 (TraceQL) y 13 (coste) |
    | **Hilo conductor** | Alguien «mejora» el prompt de SupportOps para que sea más conciso. La latencia baja, el coste baja, los errores no se mueven… y el agente empieza a inventarse datos |

    > ⚠️ **Honestidad sobre el laboratorio.** Las versiones de prompt son **simuladas** sobre el `mock` (`PromptVariantLLM`): `v2` hace que, en una fracción de los tickets que
    > necesitan una herramienta, el modelo conteste directamente y se invente el dato. No es un modelo real, pero reproduce con exactitud el **patrón** de una regresión silenciosa
    > y deja el *ground truth* en los datos para medir tus detectores. Las cifras cambian con modelos reales; el método no.
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** por qué una regresión de prompt/modelo es silenciosa y qué señales de telemetría la delatan (calidad, trayectoria, mezcla de herramientas).
    2. **Construir** un dataset de regresión *desde trazas* (casos que fallaron, 👎, escalados y una muestra de los buenos), sin duplicados ni PII.
    3. **Reproducir** (replay) el dataset contra dos versiones del agente y decidir con una **compuerta de release** con estadística apareada (McNemar, IC de la diferencia).
    4. **Calcular** el poder estadístico: el tamaño de muestra necesario y la caída mínima detectable; entender el problema de «mirar los resultados antes de tiempo».
    5. **Medir** el *drift* de entrada (PSI, KS) y de comportamiento (Jensen–Shannon sobre la mezcla de herramientas, huella de comportamiento) y detectar caídas con CUSUM.
    6. **Diseñar** un despliegue en canario con decisión secuencial (SPRT) y calcular cuándo puedes promover o revertir.
    7. **Detectar** una regresión de prompt **usando solo telemetría** (spans, eventos de evaluación) y localizar las trazas culpables con TraceQL.
    8. **Comparar** versiones A/B del agente con guardarraíles de coste y latencia.
    """)

    md("## 🔁 Conexión con módulos anteriores")
    md(details("1 · (Módulo 14) ¿Por qué la media de la muestra evaluada no es la calidad real y cómo se corrige?",
               "Porque el muestreo es estratificado (más peso a errores y escalados). Se corrige con la **post-estratificación**: ponderar cada estrato por su tamaño en la población (`supportops_eval_population_total`)."))
    md(details("2 · (Módulo 14) Un juez con sensibilidad 0,90 y especificidad 0,98 marca el 11 % de respuestas como malas. ¿Qué tasa real hay?",
               "Rogan–Gladen: (0,11 + 0,98 − 1)/(0,90 + 0,98 − 1) ≈ 10,2 %. Al comparar versiones, el **mismo juez** sesga las dos igual: por eso las comparativas pareadas son más fiables que los valores absolutos."))
    md(details("3 · (Módulo 07) ¿Qué selector de TraceQL devuelve los `invoke_agent` sin ninguna llamada a herramienta?",
               "Por atributos del span raíz: `{ name =~ \"invoke_agent.*\" && span.supportops.tool_calls = 0 }`. O estructural: trazas con `chat` pero sin hijos `execute_tool` (con `!>`/`count()` según versión de Tempo). Hoy lo usaremos para localizar la regresión."))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_15)
    code(DATA_15)

    # ------------------------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · Intuición: la regresión silenciosa

    La historia es real en forma, no en detalle: un martes se despliega un prompt «más conciso». Se revisan los paneles del módulo 10: latencia ↓, coste ↓, errores = igual. ¡Éxito! Tres semanas
    después soporte humano nota que los clientes llaman por números de seguimiento que no existen. **La regresión llevaba tres semanas viva** porque ninguna señal clásica la veía.

    | Si vienes de… | Esto es como… | Lo que cambia |
    |---|---|---|
    | **ML** | *Model drift* / regresión de un modelo reentrenado | El «modelo» es un prompt + un LLM de terceros que puede cambiar **sin avisar**; el conjunto de test hay que **construirlo desde producción** |
    | **Backend** | Una migración que cambia el comportamiento sin tocar el contrato | Necesitas tests de **comportamiento** (qué herramientas llama, qué dice) además de tests de contrato |
    | **SRE** | Despliegue canario + análisis automático (p. ej. Kayenta) | La métrica de decisión es la **calidad**, que es ruidosa y cara: hay que decidir con pocas muestras |
    """)
    code('''
fig, ax = viz.canvas(12.5, 4.6, (0, 125), (0, 46))
P = viz.PALETTE
b1 = viz.box(ax, 1, 28, 18, 9, "Producción\\n(trazas + eventos\\nde evaluación)", P["traces"])
b2 = viz.box(ax, 26, 28, 18, 9, "Dataset de oro\\n(fallos, −, escalados,\\nmuestra de buenos)", P["logs"], fontsize=8)
b3 = viz.box(ax, 51, 28, 17, 9, "Replay offline\\nversión candidata", P["profiles"])
b4 = viz.box(ax, 75, 28, 17, 9, "Compuerta\\n(estadística apareada)", P["warn"])
b5 = viz.box(ax, 99, 28, 17, 9, "Canario 5-10 %\\n(SPRT)", P["metrics"])
b6 = viz.box(ax, 99, 8, 17, 9, "100 % + vigilancia\\n(drift, SLO calidad)", P["ok"])
b7 = viz.box(ax, 51, 8, 41, 9, "Nuevos fallos en producción → vuelven al dataset de oro", P["neutral"], fc="#f3f4f6")
for a, b in ((b1, b2), (b2, b3), (b3, b4), (b4, b5)): viz.arrow(ax, viz.right(a), viz.left(b))
viz.arrow(ax, viz.bottom(b5), viz.top(b6)); viz.arrow(ax, viz.left(b6), viz.right(b7)); viz.arrow(ax, viz.top(b7), viz.bottom(b2), "", P["neutral"], rad=-0.25, dashed=True)
ax.text(1, 43, "El ciclo de regresión: offline barato antes, online prudente después, y producción alimenta el dataset", fontsize=10, fontweight="bold")
ax.text(75, 23.5, "bloquea o pasa", fontsize=8, color=P["warn"]); ax.text(99, 23.5, "promueve o revierte", fontsize=8, color=P["metrics"])
plt.show()
''')
    md(observe("""
    - Hay **dos puertas** antes del 100 %: una barata y *offline* (replay del dataset de oro) y una prudente y *online* (canario con decisión secuencial). Ninguna sustituye a la otra: el replay no ve el tráfico nuevo; el canario es caro y expone a clientes reales.
    - La flecha discontinua es el motor del sistema: **cada fallo en producción alimenta el dataset de oro**. Sin ella, el dataset envejece y deja de representar el tráfico.
    """))
    md("## 1.1 Los paneles clásicos mejoran; la calidad empeora")
    code('''
def fp(v):
    r = RUN[v]["res"]
    return {"latencia media (s)": np.mean([x.latency_s for x in r]), "coste medio (USD)": np.mean([x.cost_usd for x in r]) * 1e3, "% errores": 100 * np.mean([x.status in ("error", "max_steps") for x in r]),
            "herramientas/ticket": np.mean([x.n_tool_calls for x in r]), "groundedness OK (%)": 100 * q(v)}
T = pd.DataFrame({v: fp(v) for v in RUN}).T
display(T.round(3))
fig, axes = plt.subplots(1, 5, figsize=(14, 3.2))
for ax, col_ in zip(axes, T.columns):
    ax.bar(T.index, T[col_], color=[viz.PALETTE["ok"], viz.PALETTE["error"], viz.PALETTE["warn"]]); ax.set_title(col_, fontsize=9); ax.tick_params(axis="x", labelsize=8)
    ax.set_ylim(0, T[col_].max() * 1.25)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **v2** tiene mejor latencia, menos coste y **los mismos errores** que v1: un revisor que mire los paneles de los módulos 09/10 la aprobaría. Solo dos columnas delatan el cambio: **menos herramientas por ticket** (el agente ya no consulta) y **menos groundedness**.
    - El «ahorro» de coste y latencia es **el síntoma de la regresión**, no un beneficio: son las llamadas a herramientas que ya no se hacen. Cualquier optimización de coste necesita **guardarraíl de calidad** (conexión con el módulo 13).
    - **v2.1** (el hotfix) recupera casi todo, pero no del todo: más adelante veremos cuántos datos hacen falta para saberlo.
    """))

    # ------------------------------------------------------------------------------------------------------------- 2
    md("""
    ---
    # 2 · Teoría: qué cambia, qué se rompe, cómo se detecta

    ## 2.1 Qué puede regresar (y quién lo cambia)

    | Cambio | Quién lo decide | Cómo se ve | Detector principal |
    |---|---|---|---|
    | Prompt de sistema / plantillas | Tu equipo | Calidad ↓, trayectoria distinta | Replay del dataset + canario |
    | Modelo (versión del proveedor) | **El proveedor, a veces sin avisar** (alias `latest`) | Cambio en estilo, tokens, tool use | Canarios sintéticos continuos + huella de comportamiento |
    | Herramientas / APIs | Otros equipos | Errores o resultados distintos | Métricas de herramienta (módulo 12), contratos |
    | Base de conocimiento / RAG | Contenido | Respuestas desactualizadas, «no encuentro» | Tasa de «sin resultados», groundedness |
    | Distribución de entrada (*data drift*) | Los clientes | Temas nuevos, picos estacionales | PSI/KS de la entrada, cobertura del KB |
    | Juez / rúbrica | Tu equipo | La «calidad» cambia sin cambiar el agente | Calibración (módulo 14) |

    ## 2.2 Offline vs online (y por qué hacen falta los dos)

    | | Offline (dataset de oro, replay) | Online (canario, A/B, monitorización) |
    |---|---|---|
    | Tráfico | Fijo, curado | Real, cambiante |
    | Coste/riesgo | Barato, sin clientes | Caro, expone clientes |
    | Detecta | Regresiones conocidas, cambios deliberados | Efectos de distribución real, fallos nuevos |
    | Ciega a | Casos nuevos, interacción con el entorno (herramientas lentas, KB viva) | Lo que no ocurre en la ventana observada |

    ## 2.3 Tipos de *drift*

    | Tipo | Qué cambia | Cómo se mide sin etiquetas |
    |---|---|---|
    | **Entrada** (covariate shift) | \\( P(x) \\) | PSI/KS de longitud, tokens, mezcla de intenciones |
    | **Concepto** | \\( P(y \\mid x) \\): lo que es «correcto» | Cambios en KB/políticas; requiere etiquetas o juez |
    | **Comportamiento** | Qué hace el agente con la misma entrada | Mezcla de herramientas, nº de llamadas, tokens de salida (JS/PSI) |
    | **Calidad** | La nota del juez | CUSUM/EWMA sobre la tasa de aprobados |

    El **drift de comportamiento** es el más barato de vigilar (no necesita juez) y el que primero delata un cambio de prompt o de modelo.
    """)

    # ------------------------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · Dataset de regresión *desde trazas*

    La mejor fuente de casos de test es producción. Con la telemetría del módulo 14 sabemos **qué traza falló** (evaluación), **qué traza disgustó** (feedback −) y **cuál escaló**. El algoritmo:

    1. Prioriza: `thumbs_down` → `judge_fail` → `error` → `escalated` → `random_pass` (una muestra de los buenos: **sin ellos solo pruebas lo que ya sabes que falla**).
    2. **Deduplica** por texto (mismo texto y pedido = mismo caso; se acumula el *peso* = a cuántos tickets representa).
    3. **Redacta PII** (`scrub_pii`) y quita el cuerpo con datos personales.
    4. Guarda la **trayectoria aceptada** (herramientas usadas en la traza buena) para evaluar el *comportamiento*, no solo el texto.
    5. Guarda `source_trace_id`: de cada caso puedes volver a la traza de origen.
    """)
    code('''
v1 = RUN["v1"]
verdicts = {c.ticket_id: v for c, v in zip(v1["cases"], v1["verd"])}
FB = {f.ticket_id: f.rating for f in simulate_feedback(v1["cases"], seed=SEED)}
tools = {r.ticket_id: r.tools_used for r in v1["res"]}
GOLD = select_golden(v1["cases"], verdicts, FB, n_total=120, tools_by_ticket=tools)
SRC = {t.ticket_id: t for t in TK}; GT = golden_to_tickets(GOLD, SRC)
comp = collections.Counter(g.reason for g in GOLD)
print(f"{len(GOLD)} casos de oro · composición: {dict(comp)} · pesos: representan {sum(g.weight for g in GOLD):.0f} tickets de producción")
display(pd.DataFrame([dataclasses.asdict(g) for g in GOLD[:5]])[["case_id", "reason", "question", "expected_tools", "weight", "source_trace_id"]])
fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
axes[0].bar(comp.keys(), comp.values(), color=viz.PALETTE["logs"]); axes[0].set_title("Por qué entró cada caso"); axes[0].tick_params(axis="x", labelsize=8)
iv = collections.Counter(SRC[g.source_ticket_id].intent_true for g in GOLD); ip = collections.Counter(t.intent_true for t in TK)
axes[1].bar(np.arange(4) - 0.2, [iv[k] / len(GOLD) for k in sorted(ip)], 0.4, label="dataset", color=viz.PALETTE["logs"]); axes[1].bar(np.arange(4) + 0.2, [ip[k] / len(TK) for k in sorted(ip)], 0.4, label="producción", color=viz.PALETTE["neutral"])
axes[1].set_xticks(range(4), sorted(ip), fontsize=8); axes[1].legend(); axes[1].set_title("Intenciones: dataset vs producción")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El dataset está **sesgado a propósito** hacia los fallos (judge_fail, −): es lo que queremos probar. Pero la mezcla de intenciones se desvía de la de producción (más escalados y reembolsos). Por eso cada caso lleva un **peso** y por eso conservamos una muestra de buenos: para poder reponderar a la distribución real y para detectar regresiones en lo que *hoy* funciona.
    - **Privacidad**: el dataset contiene preguntas de clientes. Se redacta PII con `scrub_pii` (módulo 20 amplía a nombres y direcciones) y **no se captura el contenido en las trazas por defecto** (`capture_content=False`): el dataset se construye con una captura *dirigida* (solo los tickets elegidos) y con retención corta.
    - Cada caso guarda `source_trace_id`: si un test falla mañana, abres la traza de producción de la que nació.
    """))
    md(box("warn", "Cuidado: el replay NO reproduce el entorno", """
    El replay vuelve a ejecutar **la entrada**, no las condiciones de aquel momento: un caso que falló por un 503 del proveedor *no falla* al repetirlo. Por eso (a) los casos de `error` tienen poco valor como test de regresión de *calidad*
    (sirven para pruebas de resiliencia) y (b) los fallos intermitentes se tratan con **repeticiones** o con tolerancia estadística, nunca con un `assert` sobre una sola ejecución.
    """))

    # ------------------------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · Replay y compuerta de release

    Repetimos el dataset con cada versión y comparamos. Como las dos versiones ven **los mismos casos**, la comparación es **apareada**: la prueba de McNemar solo mira los casos en los que las versiones discrepan
    (\\( b \\): pasaba con v1 y falla con v2; \\( c \\): al revés), con p-valor exacto binomial \\( 2\\cdot P(X \\le \\min(b,c)),\\; X\\sim\\mathrm{Bin}(b+c,\\tfrac12) \\).
    """)
    code('''
REP = {v: replay(GOLD, GT, v, J) for v in ("v1", "v2", "v2.1")}
rows = []
for v, rr in REP.items():
    k = sum(r["passed"] for r in rr); lo, hi = wilson_interval(k, len(rr))
    rows.append({"versión": v, "calidad OK": k / len(rr), "IC95 bajo": lo, "IC95 alto": hi, "trayectoria OK": np.mean([r["trajectory_ok"] for r in rr]), "coste medio": np.mean([r["cost_usd"] for r in rr]), "latencia": np.mean([r["latency_s"] for r in rr])})
R = pd.DataFrame(rows).set_index("versión"); display(R.round(4))
gate = ReleaseGate()
for cand in ("v2", "v2.1"):
    dec, why = gate.decide(REP["v1"], REP[cand])
    b = sum(a["passed"] and not c["passed"] for a, c in zip(REP["v1"], REP[cand])); c_ = sum((not a["passed"]) and c["passed"] for a, c in zip(REP["v1"], REP[cand]))
    print(f"v1 → {cand}: {dec.upper():5s} · McNemar b={b} c={c_} p={mcnemar_exact(b, c_):.4f} · {why or 'sin motivos'}")
fig, ax = plt.subplots(figsize=(7.5, 3.6))
x = np.arange(len(R)); ax.errorbar(x, R["calidad OK"], yerr=[R["calidad OK"] - R["IC95 bajo"], R["IC95 alto"] - R["calidad OK"]], fmt="o", capsize=6, color=viz.PALETTE["traces"], label="calidad OK (IC95 Wilson)")
ax.plot(x, R["trayectoria OK"], "s--", color=viz.PALETTE["profiles"], label="trayectoria correcta"); ax.set_xticks(x, R.index); ax.set_ylim(0.6, 1.02); ax.legend(); ax.set_title("Replay del dataset de oro por versión")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La compuerta **bloquea v2** por dos motivos independientes: la calidad cae ≈ 17 puntos (McNemar: ≈ 20 casos empeoran, ninguno mejora, p ≈ 1e-6) y la **trayectoria** (qué herramientas llama) se desvía de la aceptada. La segunda señal no necesita juez.
    - **v2.1 (el hotfix) queda en el filo**: pierde ≈ 4-5 puntos, 5-6 casos empeoran y ninguno mejora (p ≈ 0,03-0,06). Según cuál sea la muestra de 120 casos la compuerta lo bloquea o lo deja pasar: **esa fragilidad es lo que significa «poco poder estadístico»** (sección 5). Los intervalos de Wilson de v1 y v2.1 se solapan: una comparación *no apareada* ni se acercaría a detectarlo.
    - Aparear —que cada caso sea su propio control— multiplica el poder. Por eso `ReleaseGate` usa McNemar cuando las dos ejecuciones son de los mismos casos y el IC de la diferencia de proporciones solo cuando no lo son.
    """))

    # ------------------------------------------------------------------------------------------------------------- 5
    md(r"""
    ---
    # 5 · Poder estadístico: ¿cuántos datos hacen falta?

    Para decidir «v2.1 no es peor que v1» hay que fijar de antemano qué diferencia te importa. Con dos proporciones \(p_0\) (base) y \(p_1\) (candidata), nivel \(\alpha\) y poder \(1-\beta\):
    $$ n \;=\; \frac{\Big(z_{1-\alpha/2}\sqrt{2\bar p(1-\bar p)} + z_{1-\beta}\sqrt{p_0(1-p_0)+p_1(1-p_1)}\Big)^2}{(p_0-p_1)^2}, \qquad \bar p = \tfrac{p_0+p_1}{2}$$
    por grupo. Dicho al revés: con \(n\) por grupo, la **caída mínima detectable** es \(\approx (z_{1-\alpha/2}+z_{1-\beta})\sqrt{2p_0(1-p_0)/n}\).
    """)
    code('''
drops = np.array([0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15])
fig, axes = plt.subplots(1, 2, figsize=(12.5, 3.8))
for p0, col_ in ((0.97, viz.PALETTE["traces"]), (0.90, viz.PALETTE["metrics"]), (0.80, viz.PALETTE["profiles"])):
    axes[0].plot(drops * 100, [required_n_per_arm(p0, p0 - d) for d in drops], "o-", label=f"calidad base {p0:.0%}", color=col_)
axes[0].set_yscale("log"); axes[0].set_xlabel("caída de calidad a detectar (puntos)"); axes[0].set_ylabel("n por grupo (α=5 %, potencia 80 %)"); axes[0].legend(); axes[0].set_title("Casos necesarios")
ns = np.array([30, 60, 120, 250, 500, 1000, 3000])
axes[1].plot(ns, [min_detectable_drop(int(n), 0.97) * 100 for n in ns], "o-", color=viz.PALETTE["traces"], label="base 97 %")
axes[1].plot(ns, [min_detectable_drop(int(n), 0.85) * 100 for n in ns], "o-", color=viz.PALETTE["metrics"], label="base 85 %")
axes[1].axvline(120, color=viz.PALETTE["neutral"], ls=":"); axes[1].text(125, axes[1].get_ylim()[1] * 0.85, "nuestro dataset (120)", fontsize=8)
axes[1].set_xscale("log"); axes[1].set_xlabel("n por grupo"); axes[1].set_ylabel("caída mínima detectable (puntos)"); axes[1].legend(); axes[1].set_title("Sensibilidad según el tamaño del dataset")
plt.tight_layout(); plt.show()
print("n por grupo para detectar 97% → 92%:", required_n_per_arm(0.97, 0.92), "· 90% → 85%:", required_n_per_arm(0.90, 0.85), "· caída mínima con 120 casos y base 97%:", f"{min_detectable_drop(120, 0.97):.1%}")
''')
    md(observe("""
    - Detectar una caída pequeña es **caro**: 5 puntos desde 90 % requieren unos 700 casos *por grupo*; desde 97 %, menos (la varianza es menor cerca del techo) pero aun así cientos. Con 120 casos *independientes* solo ves caídas de ≥ 6 puntos si la base es ≈ 97 % (≈ 13 si es ≈ 85 %): v2 (−16) sí, v2.1 (−5) no… salvo que compares de forma **apareada**, como en la sección 4, donde v2.1 queda al límite de la significación (p ≈ 0,03-0,06).
    - Dos formas de ganar poder sin más datos: **comparación apareada** (cada caso es su propio control) y **métricas continuas/más finas** (puntuaciones del juez, no pass/fail).
    - Conclusión práctica: el dataset de oro es una **red de seguridad para regresiones grandes**; las pequeñas se vigilan online con volumen (canario + SLO de calidad, módulo 16).
    """))
    md("## 5.1 El problema de «mirar antes de tiempo» (*peeking*)")
    code('''
pk = peeking_false_positive_rate(p=0.06, n_max=600, looks=20, trials=300, seed=SEED)
print(pk)
fig, ax = plt.subplots(figsize=(5.8, 3.4))
ax.bar(["nominal", "prueba z repetida\\n20 veces", "SPRT"], [pk["nominal"], pk["fixed_sample_peeking"], pk["sprt"]], color=[viz.PALETTE["neutral"], viz.PALETTE["error"], viz.PALETTE["ok"]])
ax.set_ylabel("falsos positivos (dos versiones IDÉNTICAS)"); ax.set_title("Mirar sin corregir infla el error")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con dos grupos **idénticos**, repetir una prueba de tamaño fijo cada 30 peticiones y parar en el primer «significativo» declara regresión en ≈ 20–25 % de los casos en lugar del 5 % prometido: cada mirada es una nueva oportunidad de error (Johari et al., 2017).
    - El **SPRT** de Wald está diseñado para mirar tras cada observación y mantiene el error cerca del nominal. Es lo que usamos en el canario (sección 7).
    """))

    # ------------------------------------------------------------------------------------------------------------- 6
    md("""
    ---
    # 6 · Drift: de entrada, de comportamiento y de calidad

    ## 6.1 Drift de entrada: temas nuevos
    Inyectamos tickets sobre temas que la base de conocimiento no cubre (reciclaje, facturación en otro país…). Sin etiquetas, ¿qué se ve?
    """)
    code('''
NOV = novel_topic_tickets(len(TK) // 4, seed=7)
res_n, cases_n = run_version("v1", NOV)
mix = lambda r: collections.Counter(t for x in r for t in x.tools_used)
len_ref = [len(t.text) for t in TK]; len_nov = [len(t.text) for t in NOV]
rows = [
    {"magnitud": "longitud de la pregunta (PSI)", "valor": psi(len_ref, len_nov), "umbral": 0.25},
    {"magnitud": "longitud de la pregunta (KS p-valor)", "valor": ks_2samp(len_ref, len_nov)[1], "umbral": 0.01},
    {"magnitud": "mezcla de herramientas (JS)", "valor": js_divergence(mix(RUN["v1"]["res"]), mix(res_n)), "umbral": 0.10},
    {"magnitud": "tasa de «no encuentro» en las respuestas", "valor": np.mean([("No he encontrado" in x.answer) for x in res_n]), "umbral": 0.10},
    {"magnitud": "groundedness OK (juez)", "valor": np.mean([J.evaluate(c).scores["groundedness"].label == "pass" for c in cases_n]), "umbral": 0.90},
    {"magnitud": "calidad global OK (juez)", "valor": np.mean([J.evaluate(c).passed for c in cases_n]), "umbral": 0.80},
]
display(pd.DataFrame(rows).set_index("magnitud").round(4))
''')
    md(observe("""
    - La entrada derivó (PSI de longitud muy por encima de 0,25) y la **mezcla de herramientas** cambió (casi todo `search_kb`): ambas señales aparecen **sin juez**.
    - Un hallazgo contraintuitivo: la **groundedness** sigue alta (el agente no inventa: dice «no he encontrado información») mientras la **calidad global** cae por relevancia/resolución. Un agente «honesto pero inútil» no es una alucinación: necesitas varios criterios, no uno.
    - Qué hacer con este drift no es revertir una versión, sino **ampliar la base de conocimiento** o la cobertura: la señal es para el producto, no para el despliegue.
    """))
    md("## 6.2 Drift de comportamiento: la huella de una versión")
    code('''
fps = pd.DataFrame({v: behavior_fingerprint([dict(r.to_dict(), n_tool_calls=r.n_tool_calls) for r in RUN[v]["res"]]) for v in RUN}).T.drop(columns="n")
display(fps.round(4))
base_mix = mix(RUN["v1"]["res"])
js = {v: js_divergence(base_mix, mix(RUN[v]["res"])) for v in ("v2", "v2.1")}
psi_tok = {v: psi([x.output_tokens for x in RUN["v1"]["res"]], [x.output_tokens for x in RUN[v]["res"]]) for v in ("v2", "v2.1")}
print("JS de la mezcla de herramientas frente a v1:", {k: round(x, 4) for k, x in js.items()}, "· PSI de tokens de salida:", {k: round(x, 3) for k, x in psi_tok.items()})
fig, axes = plt.subplots(1, 2, figsize=(11.5, 3.5))
for v, col_ in (("v1", viz.PALETTE["ok"]), ("v2", viz.PALETTE["error"]), ("v2.1", viz.PALETTE["warn"])):
    nt = collections.Counter(x.n_tool_calls for x in RUN[v]["res"]); ks = sorted(nt)
    axes[0].plot(ks, [nt[k] / N for k in ks], "o-", label=v, color=col_)
axes[0].set_xlabel("llamadas a herramientas por ticket"); axes[0].set_ylabel("fracción de tickets"); axes[0].legend(); axes[0].set_title("Distribución del nº de herramientas")
axes[1].bar(["no_tool_rate v1", "v2", "v2.1"], [fps.loc[v, "no_tool_rate"] for v in ("v1", "v2", "v2.1")], color=[viz.PALETTE["ok"], viz.PALETTE["error"], viz.PALETTE["warn"]]); axes[1].set_title("Tickets sin ninguna herramienta")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La **huella de comportamiento** separa a v2 de v1 sin mirar ni una respuesta: el porcentaje de tickets *sin ninguna herramienta* se triplica y la distribución del nº de llamadas se desplaza hacia 0.
    - v2.1 casi restaura la huella (`no_tool_rate` ≈ 11,5 % frente a ≈ 8,4 % de v1) pero **no del todo**: sigue habiendo tickets sin herramienta que antes no los había. Es la ventaja del monitor de comportamiento: usa **todo el tráfico**, no un dataset pequeño.
    - La divergencia JS de la mezcla *global* de herramientas es ≈ 0 en las dos versiones (la mezcla casi no cambia: lo que cambia es **cuántos tickets no llaman a nada**); el PSI de los tokens de salida de v2 (≈ 0,24, cerca del umbral habitual de 0,25) sí lo capta. **Elige la magnitud que corresponde al fallo**, no una distancia genérica: una divergencia sobre la mezcla de herramientas no ve un agente que deja de usarlas todas por igual.
    """))
    md("## 6.3 Drift de calidad en el tiempo: CUSUM")
    code('''
# Serie temporal: despliegue de v2 en el minuto 40; cada punto = pass-rate de groundedness del minuto sobre ≈ 10 evaluaciones (calidad 93 % → 82 %)
def serie(seed, minutes=100, onset=40, n=10, p0=0.93, p1=0.82):
    rng = np.random.default_rng(seed); return np.array([rng.binomial(n, p0 if m < onset else p1) / n for m in range(minutes)])
ser = serie(SEED)
K, H = 0.05, 0.6
cus = Cusum(target=0.93, k=K, h=H); alarm = cus.first_alarm(ser)
S, s_ = [], 0.0
for x in ser: s_ = max(0.0, s_ + (0.93 - x) - K); S.append(s_)
fig, axes = plt.subplots(2, 1, figsize=(10, 5), sharex=True)
axes[0].plot(ser, color=viz.PALETTE["traces"], lw=1); axes[0].axvline(40, color=viz.PALETTE["error"], ls="--"); axes[0].set_ylabel("pass-rate por minuto"); axes[0].set_title("Calidad muestreada por minuto (n≈10 por punto)")
axes[1].plot(S, color=viz.PALETTE["metrics"]); axes[1].axhline(H, color=viz.PALETTE["error"], ls=":"); axes[1].set_ylabel("CUSUM"); axes[1].set_xlabel("minuto")
if alarm is not None: axes[1].axvline(alarm, color=viz.PALETTE["ok"], ls="--"); axes[1].text(alarm + 1, H * 1.1, f"alarma min {alarm}", fontsize=9)
plt.tight_layout(); plt.show()
# Monte Carlo (200 repeticiones): falsas alarmas ANTES del despliegue y retraso de detección DESPUÉS
def mc(detector):
    fa, dl = 0, []
    for sd in range(200):
        t = detector(serie(sd))
        if t is not None and t < 40: fa += 1
        elif t is not None: dl.append(t - 40)
    return {"falsas alarmas": fa / 200, "retraso mediano (min)": float(np.median(dl)) if dl else None, "no detectado": 1 - (fa + len(dl)) / 200}
ma = lambda thr: (lambda x: next((i for i in range(4, len(x)) if x[i - 4:i + 1].mean() < thr), None))
table = pd.DataFrame({"media móvil 5 min < 0,85": mc(ma(0.85)), "media móvil 5 min < 0,80": mc(ma(0.80)), f"CUSUM (k={K}, h={H})": mc(lambda x: Cusum(0.93, K, H).first_alarm(x))}).T
display(table.round(3))
''')
    md(observe("""
    - Cada punto de la serie es muy ruidoso (n≈10 evaluaciones por minuto). La tabla Monte Carlo muestra la disyuntiva de siempre: un umbral sensible (< 0,85) detecta en ≈ 3 min pero **da falsa alarma en más de un tercio de las series sanas**; endurecerlo (< 0,80) baja las falsas alarmas al ≈ 5 % a costa de tardar ≈ 8 min.
    - **CUSUM acumula la evidencia** (\\( S_t=\\max(0,S_{t-1}+(\\mu_0-x_t)-k) \\)): con un retraso mediano parecido (≈ 7-8 min) tiene una tasa de falsas alarmas menor (≈ 2-3 %). No es magia: es mejor uso de los mismos datos.
    - Los parámetros \\(k\\) (≈ la mitad de la caída que quieres detectar) y \\(h\\) (cuánta evidencia acumulada) se calibran con la serie histórica *sana*. Es la misma disyuntiva que la alerta por *burn rate* del módulo 16.
    """))

    # ------------------------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Canarios: decidir con pocos datos

    Un **canario** manda una fracción pequeña (5–10 %) del tráfico a la versión nueva, **enrutada de forma determinista** por hash del ticket (mismo cliente, misma versión: sin parpadeos y sin mezclar conversaciones).
    La decisión se toma con una prueba **secuencial**: tras cada petición se actualiza el log-cociente de verosimilitud del contraste *tasa sana \\( p_0 \\)* frente a *tasa mala \\( p_1 \\)*:
    $$ \\Lambda_n = k\\,\\ln\\frac{p_1}{p_0} + (n-k)\\,\\ln\\frac{1-p_1}{1-p_0}, \\qquad \\text{revertir si } \\Lambda_n \\ge \\ln\\frac{1-\\beta}{\\alpha},\\quad \\text{promover si } \\Lambda_n \\le \\ln\\frac{\\beta}{1-\\alpha}$$
    con \\( k \\) fallos de calidad en \\( n \\) peticiones evaluadas.
    """)
    code('''
share = np.mean([canary_route(t.ticket_id, 0.10) == "canary" for t in TK]); print(f"fracción enrutada al canario: {share:.1%} (objetivo 10 %) · determinista:", canary_route("T-4200001") == canary_route("T-4200001"))
P0, P1 = 0.07, 0.15                    # tasa sana de fallos de groundedness (≈ 7 %) vs la que consideramos regresión (15 %)
traj = {}
for v in ("v1", "v2", "v2.1"):
    fails = [x.scores["groundedness"].label != "pass" for x in RUN[v]["verd"]]
    k, path, dec = 0, [], None
    for i, f in enumerate(fails, 1):
        k += f; d, llr = sprt_bernoulli(k, i, P0, P1, alpha=0.05, beta=0.2); path.append(llr)
        if d != "continue" and dec is None: dec = (d, i)
    traj[v] = (path, dec)
up, lo = math.log(0.8 / 0.05), math.log(0.2 / 0.95)
fig, ax = plt.subplots(figsize=(9, 4))
for v, col_ in (("v1", viz.PALETTE["ok"]), ("v2", viz.PALETTE["error"]), ("v2.1", viz.PALETTE["warn"])):
    ax.plot(range(1, 301), traj[v][0][:300], label=f"{v}: {traj[v][1]}", color=col_)
ax.axhline(up, color=viz.PALETTE["error"], ls=":"); ax.axhline(lo, color=viz.PALETTE["ok"], ls=":"); ax.text(200, up + 0.15, "revertir", fontsize=9); ax.text(200, lo - 0.6, "promover", fontsize=9)
ax.set_xlabel("evaluaciones del canario (n)"); ax.set_ylabel("log-cociente de verosimilitud Λ"); ax.set_ylim(lo - 2, up + 2); ax.legend(); ax.set_title("SPRT: cuántos datos hacen falta para decidir")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **v2 se revierte con muy pocas evaluaciones** (decenas): su tasa de fallo es 3-4× la sana y el SPRT lo ve rápido. **v1** (sana) se promueve con unos cientos. La asimetría es la gracia: lo claramente malo se corta pronto, lo bueno requiere más pruebas.
    - **v2.1** (≈ 10 % de fallos frente al 7 % sano) es la zona gris: depende de qué \\(p_1\\) hayas declarado «inaceptable». Con \\(p_1=15\\\\%\\) tarda más en decidir o se promueve; con \\(p_1=10\\\\%\\) se revertiría. **Declarar \\(p_0\\) y \\(p_1\\) de antemano es una decisión de producto**, no de estadística.
    - Para el 5-10 % de tráfico a una cadencia de 1 000 tickets/hora y evaluando el 25 %, 100 evaluaciones llegan en unas 4 horas: el canario cuesta **tiempo**; por eso se acompaña de la compuerta offline.
    """))

    # ------------------------------------------------------------------------------------------------------------- 8
    md("""
    ---
    # 8 · Detectar la regresión usando solo telemetría

    Situación realista: no tienes acceso al código ni al prompt; solo a **spans y eventos de evaluación** en Tempo/Loki. Se han desplegado dos versiones de forma consecutiva (tráfico distinto). ¿Cuál regresó y qué trazas lo prueban?
    Generamos la telemetría con el `OTelInstrumentor` (etiquetas de versión `gen_ai.agent.version`) y el evaluador del módulo 14 (muestra del 30 %).
    """)
    code('''
def run_telemetry(version, tickets, rate=0.3):
    ta = setup_telemetry("supportops-agent", mode="memory", set_global=False)
    te = setup_telemetry("supportops-evaluator", mode="memory", set_global=False)
    ev = OnlineEvaluator(J, RateSampler(rate, "tel"), te)
    agent, col = make_agent(version, instrumentors=[OTelInstrumentor(ta), VersionTagInstrumentor(version)], collector=CaseCollector(version, on_case=ev.submit))
    res = [agent.run(t) for t in tickets]; ev.run_pending(); ta.force_flush(); te.force_flush()
    return ta.span_records(), event_records(te), res, col.cases

TA, TB = generate_tickets(500, seed=11, fault_rates=DEFAULT_FAULT_RATES), generate_tickets(500, seed=12, fault_rates=DEFAULT_FAULT_RATES)
sp1, ev1, r1, c1 = run_telemetry("v1", TA); sp2, ev2, r2, c2 = run_telemetry("v2", TB)
SPANS, EVENTS = sp1 + sp2, ev1 + ev2
SHAPES = trace_shapes(SPANS)
REP_V = pd.DataFrame(version_report(SHAPES, EVENTS)).set_index("version")
display(REP_V[["n", "p50_s", "p95_s", "error_rate", "tools_per_ticket", "no_tool_rate", "tokens_per_ticket", "groundedness_pass", "groundedness_n", "relevance_pass", "resolution_pass"]].round(3))
''')
    md(observe("""
    - Mirando **solo lo clásico** (p50/p95, error_rate, tokens) v2 parece igual o mejor. Las dos columnas que lo delatan son `tools_per_ticket`/`no_tool_rate` (estructura de la traza, **sin juez**) y `groundedness_pass` (evento de evaluación).
    - La calidad se mide solo en la **muestra** evaluada (`groundedness_n` ≈ 150 por versión): es suficiente para ver una caída de ≥ 10 puntos, no una de 2.
    - Todo esto sale de `gen_ai.agent.version` en los spans y en los eventos: **etiquetar la versión en toda la telemetría** es lo que hace posible comparar. Sin la etiqueta habría que inferir el despliegue por la fecha.
    """))
    code('''
t = two_proportion_test(int(round(REP_V.loc["v1", "groundedness_pass"] * REP_V.loc["v1", "groundedness_n"])), int(REP_V.loc["v1", "groundedness_n"]),
                        int(round(REP_V.loc["v2", "groundedness_pass"] * REP_V.loc["v2", "groundedness_n"])), int(REP_V.loc["v2", "groundedness_n"]))
print(f"groundedness v1 {t['p1']:.1%} → v2 {t['p2']:.1%} · diferencia {t['diff']:+.1%} IC95 [{t['ci_low']:+.1%}, {t['ci_high']:+.1%}] · p = {t['p_value']:.2g}")
# ¿Qué trazas lo explican? Tickets de intención que necesita herramienta, sin ninguna llamada a herramienta, en v2
suspects = [s for s in SHAPES.values() if s["version"] == "v2" and s["n_tool"] == 0 and s["status"] == "ok" and s["intent"] in ("order_status", "refund", "kb_question")]
suspects_v1 = [s for s in SHAPES.values() if s["version"] == "v1" and s["n_tool"] == 0 and s["status"] == "ok" and s["intent"] in ("order_status", "refund", "kb_question")]
truth_reg = {c.ticket_id for c in c2 if "prompt_regression" in c.truth["faults"]}
prec = np.mean([s["ticket"] in truth_reg for s in suspects]); rec = np.mean([any(s["ticket"] == t_ for s in suspects) for t_ in truth_reg])
print(f"trazas sospechosas (v2, status ok, 0 herramientas, intención que las necesita): {len(suspects)} (en v1 con el mismo filtro: {len(suspects_v1)}) · precisión frente a la verdad {prec:.0%} · exhaustividad {rec:.0%}")
sample_trace = suspects[0]["trace_id"]; ok_trace = next(s["trace_id"] for s in SHAPES.values() if s["version"] == "v1" and s["n_tool"] >= 1)
fig, axes = plt.subplots(1, 2, figsize=(13, 2.7))
for ax, tid, ttl in ((axes[0], ok_trace, "v1: traza normal (consulta herramienta)"), (axes[1], sample_trace, "v2: traza sospechosa (contesta sin consultar)")):
    viz.waterfall([s for s in SPANS if s["trace_id"] == tid], ax=ax, title=ttl)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La comparación de calidad es significativa (el IC de la diferencia no contiene 0). Las trazas con **cero herramientas en intenciones que las necesitan** localizan la regresión: ≈ 22 % de los tickets de v2 frente a ≈ 7 % de v1 con el mismo filtro (la diferencia, ≈ 15 puntos, coincide con la caída de groundedness). La causa raíz queda a la vista **sin leer el prompt**: la cascada de v2 se queda en un único span `chat`.
    - El detector estructural es un **proxy**, no una prueba: su precisión frente a la verdad ronda el 70 % (el resto son peticiones legítimas sin herramienta, como pedir al cliente su nº de pedido, y alucinaciones de fondo que también existen en v1) y no cubre regresiones que no cambian la trayectoria. Se usa para *localizar* y *priorizar*; la calidad la confirma el evento de evaluación.
    """))
    md("""
    ### Las consultas de Tempo y Loki que usarías

    ```text
    # Tempo (TraceQL): tickets de v2 que debían usar una herramienta y no la usaron
    { name =~ "invoke_agent.*" && span.gen_ai.agent.version = "v2" && span.supportops.tool_calls = 0 && span.supportops.intent =~ "order_status|refund" }

    # Loki (LogQL): evaluaciones fallidas de groundedness por versión
    sum by (gen_ai_agent_version) (count_over_time({service_name="supportops-evaluator"} | gen_ai_evaluation_name="groundedness" | gen_ai_evaluation_score_label="fail" [5m]))

    # Prometheus (PromQL): calidad por versión
    sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m]))
      / sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))
    ```
    """)

    # ------------------------------------------------------------------------------------------------------------- 9
    md("""
    ---
    # 9 · Con el stack real: un despliegue en canario, en vivo

    `LivePipeline` envía ≈ 60 s de tráfico al Collector con el flujo: los primeros ≈ 20 s todo es v1; después **v2 recibe el 40 % del tráfico (canario)**. Veremos la regresión en tres backends distintos.
    """)
    code('''
LIVE_S = 60 if FAST_DEV_RUN else 150
if LIVE:
    from supportops.slo import BASELINE_FAULTS
    lp = LivePipeline(("v1", "v2"), mode="otlp", sampler=RateSampler(0.6), metric_interval_s=5)
    tk_live = generate_tickets(int(LIVE_S * 4.5), seed=SEED, duration_s=LIVE_S, fault_rates=BASELINE_FAULTS, start_s=0.0)
    t0 = time.time(); lp.run_live(tk_live, LIVE_S, lambda t, el: "v2" if el > LIVE_S / 3 and canary_route(t.ticket_id, 0.40) == "canary" else "v1"); lp.close()
    print(f"enviados {len(tk_live)} tickets en {time.time() - t0:.0f}s · tráfico por versión: {collections.Counter(c.version for c in lp.cases)}")
    time.sleep(14)
else:
    print("Modo degradado: levanta el stack con:", STACK.command)
''')
    code('''
if LIVE:
    from supportops.otel_metrics import prom_instant
    qv = 'sum by (gen_ai_agent_version) (increase(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[10m])) / sum by (gen_ai_agent_version) (increase(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[10m]))'
    print("Prometheus · calidad por versión:", {r["metric"].get("gen_ai_agent_version"): round(r["value"], 3) for r in prom_instant(qv)})
    q_tools = 'sum by (gen_ai_agent_version) (increase(supportops_eval_population_total[10m]))'
    print("Prometheus · peticiones por versión:", {r["metric"].get("gen_ai_agent_version"): round(r["value"]) for r in prom_instant(q_tools)})
    tq = '{ name =~ "invoke_agent.*" && span.gen_ai.agent.version = "v2" && span.supportops.tool_calls = 0 && span.supportops.intent =~ "order_status|refund" }'
    ts = backends.tempo_search(tq, minutes=15, limit=20)
    print("Tempo · trazas v2 sin herramientas en pedidos/reembolsos:", len(ts.get("traces", [])))
    lg = backends.loki_query('{service_name="supportops-evaluator"} | gen_ai_evaluation_name="groundedness" | gen_ai_evaluation_score_label="fail" | gen_ai_agent_version="v2"', minutes=15, limit=50)
    print("Loki · evaluaciones fallidas de groundedness en v2:", len(lg))
''')
    md("""
    ### El dashboard `15-regresion-versiones`

    `stack/grafana/dashboards/15-regresion-versiones.json` (uid `regresion-versiones`) junta las tres lecturas: **calidad por versión** (PromQL sobre los eventos agregados), **comportamiento** (herramientas por ticket, latencia y coste *clásicos*, sin etiqueta de versión pero con el escalón del despliegue) y las **trazas sospechosas** (TraceQL).
    **Qué debes ver:** al entrar v2, la línea de v2 en «Calidad por versión» cae por debajo de v1 mientras los paneles de latencia y coste muestran una ligera **mejora**; la tabla de Tempo se llena de trazas de un solo span `chat`.
    """)

    # ------------------------------------------------------------------------------------------------------------- 10
    md("""
    ---
    # 10 · 🏭 En producción

    - **Evals en CI/CD.** El dataset de oro se ejecuta en cada cambio de prompt, modelo o herramienta como una suite de pruebas (la «compuerta»), con resultados guardados por versión. Las plataformas de evaluación comerciales y abiertas (Langfuse, LangSmith, Braintrust, Arize Phoenix, promptfoo, OpenAI Evals…) implementan variantes de este ciclo: datasets versionados, ejecuciones comparables y gating; lo que aporta OTel es que la **misma telemetría** sirve para observar y para construir los datasets.
    - **Versionado de prompts.** El prompt es código: versión semántica o hash, registro de cambios y etiquetado en la telemetría (`gen_ai.prompt.name`/`gen_ai.prompt.version`, spec GenAI *Development*; `gen_ai.agent.version`). Sin etiqueta no hay comparativa.
    - **Fijar el modelo.** Evita alias flotantes (`latest`) en producción: el proveedor puede cambiar el modelo por debajo. Si no puedes fijarlo, ejecuta **canarios sintéticos** cada pocos minutos (un conjunto fijo de prompts con aserciones) y alerta si cambia la huella.
    - **Canarios y progresivos.** Despliegue progresivo (5 → 25 → 50 → 100 %) con análisis automático en cada escalón; el análisis compara canario y línea base *al mismo tiempo* (no contra «ayer») para neutralizar la estacionalidad.
    - **Coste de las evals.** Las regresiones se ejecutan sobre dataset pequeño con juez pequeño/reglas y se escalan solo si la señal es ambigua (módulos 13, 14 y 18).
    """)

    md("""
    ---
    # 11 · 🧠 Secretos de la élite

    1. **Las mejoras de latencia y coste tras un cambio de prompt son sospechosas hasta que se demuestre lo contrario**: suelen ser llamadas a herramientas o razonamiento que dejó de ocurrir. Todo cambio «de eficiencia» necesita guardarraíl de calidad y de trayectoria.
    2. **Evalúa la trayectoria, no solo la respuesta.** Comparar el conjunto/orden de herramientas llamadas con el de la traza aceptada detecta regresiones sin juez, baratas y deterministas (`trajectory_match`). El texto puede cambiar sin ser peor; la trayectoria cambia cuando cambia el comportamiento.
    3. **Compara apareado y al mismo tiempo.** Mismo conjunto de casos (replay) o mismo periodo (canario simultáneo). Comparar «esta semana» con «la semana pasada» mezcla la regresión con la estacionalidad y los cambios de tráfico.
    4. **Fija el tamaño de muestra y la diferencia relevante antes de mirar**, o usa una prueba secuencial. Mirar repetidamente y parar al primer p < 0,05 infla el error de tipo I muy por encima del 5 % (en nuestra simulación de 20 miradas, ≈ 1 de cada 4; el efecto crece con el nº de miradas, ver Johari et al., 2017).
    5. **Un dataset de oro envejece**: pesa los casos por su frecuencia real, retira los obsoletos, añade cada incidente nuevo y vigila la distancia entre su distribución y la de producción (PSI). Un dataset que ya no se parece a producción da luz verde a regresiones reales.
    6. **Los casos de `error` no son tests de calidad.** Un 503 del proveedor no se reproduce en un replay; mezclarlos infla la varianza. Sepáralos en una suite de resiliencia.
    7. **Etiqueta la versión en TODAS las señales** (spans, logs, métricas, eventos de evaluación) y mantén la cardinalidad acotada (versión ≈ decenas de valores, no un hash por despliegue de CI). Sin esa etiqueta, la regresión se descubre por correlación temporal con el calendario de despliegues.
    8. **Rollback automático solo con datos suficientes.** Un SPRT con \\(p_0,p_1\\) declarados evita revertir por ruido y evita esperar 3 semanas; pero necesita una definición de «fallo» estable (juez versionado, módulo 14).
    9. **Cuenta el coste del hotfix.** v2.1 recuperó casi todo… pero «casi» sobre millones de tickets son miles de respuestas malas: calcula el impacto (tasa residual × volumen) antes de dar un incidente por cerrado.
    10. **Haz primero un A/A: la versión idéntica contra sí misma.** Antes de creer una diferencia v1-v2, enruta el tráfico a dos réplicas de la **misma** versión y comprueba que el reparto real coincide con el planificado (*sample ratio mismatch*, SRM) y que la métrica no «detecta» diferencias. Con LLM la salida varía entre ejecuciones incluso con el mismo prompt (Anthropic: los agentes son «non-deterministic between runs, even with identical prompts»), así que la varianza intra-versión es parte de tu ruido. Un A/A que dispara falsos positivos > 5 % invalida el juez, el reparto o el etiquetado. *Fuente: Kohavi, Tang, Xu (2020), capítulos sobre SRM y pruebas A/A; Anthropic Engineering (2025) para el no determinismo.*
    11. **Si vas a mirar siempre, usa inferencia válida en cualquier momento, no un p-valor cada hora.** Johari et al. no solo documentan el problema: proponen *p-valores e intervalos siempre válidos* basados en una prueba secuencial de razón de probabilidades por mezcla (mSPRT), que mantienen el error de tipo I bajo control con mirada continua a cambio de algo de potencia; versión extendida en *Operations Research* (2022). El SPRT de Wald de este módulo es el caso de hipótesis simples. *Fuente: Johari, Koomen, Pekelis, Walsh (KDD '17, pp. 1517-1525; confirmado en DBLP); la versión de* Operations Research *se confirmó solo por el listado de DBLP.*
    12. **Un canario necesita un grupo de control concurrente y tres decisiones que se compensan.** El Workbook define el canario como un despliegue parcial y limitado en el tiempo, evaluado contra el resto (el «control»). La charla de SREcon18 de Štěpán Davidovič (Google SRE) lo resume en un triángulo: **duración** (más datos, menos velocidad), **tamaño de la población** (más representativo, pero más daño si es malo) y **selección de métricas** (más métricas, más ruido y falsas alarmas). Aquí: reparto del canario (módulo 15 §9), ventana de decisión y qué señales cuentan (calidad con intervalo, trayectoria, coste por ticket). *Fuente: SRE Workbook cap. 16 «Canarying Releases» (definición leída en el extracto de O'Reilly); el triángulo, vía el resumen de New Relic de la charla (fuente secundaria, no verificada en el original).*
    """)

    md("""
    ---
    # 12 · ⚠️ Errores comunes

    - Probar solo con el dataset de **fallos pasados** (sin una muestra de lo que funciona): no ves regresiones en lo que hoy va bien.
    - Mezclar fallos de infraestructura con fallos de calidad en el mismo dataset.
    - Comparar versiones con **tráfico distinto** (otro día, otro mix) y atribuir la diferencia al prompt.
    - Declarar «no hay regresión» porque *p* > 0,05 con 50 casos (ausencia de evidencia ≠ evidencia de ausencia): calcula la caída mínima detectable.
    - Cambiar el juez a la vez que el agente (no sabrás cuál causó el cambio).
    - Guardar contenido de clientes en el dataset sin redactar ni caducidad.
    - Canario sin enrutamiento determinista: el mismo cliente ve una versión u otra a mitad de una conversación.
    """)

    md("""
    ---
    # 13 · Autoevaluación
    """)
    md(details("1 · (Cálculo) Quieres detectar una caída de calidad de 0,90 a 0,85 con α = 5 % y potencia 80 %. ¿Cuántos casos por versión? ¿Cuántos si la base fuera 0,97 y la caída 0,92?",
               "Con la fórmula de dos proporciones: ≈ 686 por grupo (90 → 85) y ≈ 326 por grupo (97 → 92) con esta aproximación. La varianza \\( p(1-p) \\) es menor cerca de 1, así que la misma caída de 5 puntos requiere menos casos cerca del techo. Con un dataset de 120 casos solo detectas caídas de ≥ 6 puntos (base 97 %) o ≈ 13 (base 85 %)."))
    md(details("2 · (Cálculo) Tras el replay, 14 casos pasaban con v1 y fallan con v2, y 1 caso al revés. ¿Es significativa la regresión?",
               "McNemar exacto: b = 14, c = 1 → n = 15, min = 1. p = 2·P(Bin(15, ½) ≤ 1) = 2·(1 + 15)/32768 ≈ 0,001. Sí: significativa. Solo cuentan los casos discordantes; los que pasan o fallan en ambas versiones no aportan información sobre la diferencia."))
    md(details("3 · (Diagnóstico) Tras un despliegue el coste por ticket baja un 12 %, el p95 baja un 8 % y los errores no cambian. El equipo celebra. ¿Qué miras antes de aceptar?",
               "Calidad (groundedness/relevancia por versión) y trayectoria: herramientas por ticket, `no_tool_rate`, tokens de salida. Un ahorro sin cambio de modelo suele ser trabajo que se dejó de hacer. Comprueba también la mezcla de intenciones (¿cambió el tráfico?) para descartar un efecto de composición."))
    md(details("4 · (Diagnóstico) El replay de tu dataset de oro pasa al 100 % con la versión nueva, pero en producción los clientes se quejan. Da tres causas.",
               "(1) El dataset no representa el tráfico actual (drift de entrada, falta de casos nuevos). (2) Los fallos dependen del entorno que el replay no reproduce (herramientas lentas, KB viva, límites de tasa). (3) Poco poder estadístico: una caída pequeña no es detectable con tu n. Y quizá (4) la regresión está en lo que el juez no mide (otro criterio)."))
    md(details("5 · (Transferencia) Tu proveedor anuncia que retirará el modelo X y migrará el alias `default` a Y. ¿Qué plan de pruebas montas?",
               "Replay del dataset de oro con X e Y (apareado) + huella de comportamiento sobre una muestra de tráfico real redactado; canario con enrutamiento determinista y SPRT con \\(p_0,p_1\\) acordados; guardarraíles de coste/latencia/tokens (Y puede ser más verboso); recalibrar el juez si usa Y; fijar la versión del modelo en la configuración y monitorizar `gen_ai.response.model` por si el proveedor cambia el modelo por debajo."))
    md(details("6 · (Transferencia) ¿Cómo aplicarías la huella de comportamiento a un agente de código que edita ficheros?",
               "Con métricas del mismo estilo: nº de ficheros tocados, herramientas usadas (leer/editar/ejecutar tests), proporción de ejecuciones que corren tests antes de terminar, longitud de los diffs y tokens. Un cambio de prompt que reduce «ejecutar tests» es el equivalente a nuestro `no_tool_rate`. Todo ello sin juez y desde los spans `execute_tool`."))

    md("""
    ---
    # 14 · Referencias

    - OpenTelemetry, *Semantic conventions for generative AI* (repo `open-telemetry/semantic-conventions-genai`, estado *Development*): `gen_ai.agent.version`, `gen_ai.prompt.name`/`gen_ai.prompt.version`, evento `gen_ai.evaluation.result`.
    - Wald, A. (1945). *Sequential Tests of Statistical Hypotheses.* Annals of Mathematical Statistics 16(2):117–186 — origen del SPRT.
    - Johari, R., Koomen, P., Pekelis, L., Walsh, D. (2017). *Peeking at A/B Tests: Why It Matters, and What To Do About It.* KDD '17, pp. 1517–1525.
    - Page, E. S. (1954). *Continuous Inspection Schemes.* Biometrika 41(1/2):100–115 — origen de CUSUM.
    - McNemar, Q. (1947). *Note on the sampling error of the difference between correlated proportions or percentages.* Psychometrika 12(2):153–157.
    - Kohavi, R., Tang, D., Xu, Y. (2020). *Trustworthy Online Controlled Experiments.* Cambridge University Press — experimentación online, poder, SRM, guardarraíles.
    - Husain, H. (2024). *Your AI Product Needs Evals.* https://hamel.dev/blog/posts/evals/ — evals desde datos de producción.
    - Zheng, L. et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* arXiv:2306.05685.
    - Beyer, B. et al. (2018). *The Site Reliability Workbook*, cap. 16 «Canarying Releases» — despliegues canario y su análisis. https://sre.google/workbook/canarying-releases/
    """)
    nb.save(out)


# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "15_proyecto_calidad_regresion.ipynb", "Proyecto 15 · Detectar una regresión de prompt usando solo telemetría")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 15 · Detectar una regresión de prompt usando solo telemetría

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (todo en memoria). Opcional: `core` + `metrics` para ver tu panel (paso final) |
    | **RAM aproximada** | < 500 MB |
    | **Prerrequisitos** | Lección `15_calidad_regresion`, proyecto 14 (tu evaluador) y módulos 07 y 10 |
    | **Conexión** | Usas el evaluador del 14 como detector. El 16 convertirá esta señal en un SLO de calidad con alertas |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. El jueves se desplegó «prompt v2». Soporte humano dice que «algo raro pasa con los números de seguimiento», pero **no tienes acceso al repositorio de prompts**
    (es de otro equipo) y los paneles de latencia y errores están verdes. Solo tienes **telemetría**: spans del agente (con `gen_ai.agent.version`) y eventos de evaluación. Tu misión:

    1. **Demostrar con estadística** si hubo regresión y en qué versión.
    2. **Localizar las trazas culpables** y describir la causa sin leer el prompt.
    3. **Montar la red de seguridad**: dataset de oro desde producción, compuerta de release, vigilancia del comportamiento y un canario con decisión secuencial.

    ## Datos

    Sintéticos y deterministas (semilla 42, `mock`). El **Paso 0** genera (a) 800 tickets de «producción» con la versión v1 (evaluados por el juez, con feedback sintético) para construir el dataset de oro y (b) un **A/B consecutivo** de 500 tickets con v1 y 500 con v2
    exportados como spans y eventos (`SPANS`, `EVENTS`) — **de ahí sale la detección «solo telemetría»**. Cadena de datos: stack local (opcional) → memoria.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `build_golden` | Mismos casos y razones que la referencia, sin duplicados ni PII, pesos ≥ 1 | exacto |
    | R2 | `compare_versions` | Prueba apareada McNemar: v2 se bloquea, v1 vs v1 pasa, listas distintas lanzan `ValueError` | 4/4 |
    | R3 | `fingerprint` y `drift_flags` | Huella exacta y banderas correctas (v2 marcada, v2.1 no marcada en `no_tool_rate`) | exacto / 3/3 |
    | R4 | `find_regression` | Versión culpable, tasas de groundedness exactas y p < 0,01; sospechosas con precisión ≥ 0,65 y exhaustividad ≥ 0,85 | 4/4 |
    | R5 | `canary_decision` | Decisión y nº de evaluaciones exactos en 3 flujos (sana, regresión grave, sin evidencia) | 3/3 |
    | R6 | `build_regression_dashboard` | `lint` limpio y 8 consultas clave | 8/8 |

    > 📏 Los umbrales salen de la solución de referencia con la semilla 42 fija en el notebook (R1, R3 y R5 se comparan con las funciones del paquete `supportops.regression` ejecutadas en vivo, así que no dependen de constantes).
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_15.replace('STACK = check_stack("core+metrics")', 'STACK = check_stack([])').replace("LIVE = not STACK.degraded", "LIVE = False") + '''
from supportops.dashkit import Dashboard, lint, prom, loki, tempo, timeseries, stat, bargauge, traces_table, logs, table, heatmap, thresholds
from supportops.clock import stable_hex
from supportops.quality_eval import scrub_pii
''')

    md("""
    ## Paso 0 · Los datos (te lo damos hecho)
    """)
    code('''
J = MockJudge(SEED)
TK = generate_tickets(800, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)
RES1, CASES1 = run_version("v1", TK)                                       # «producción» con v1
VERD1 = {c.ticket_id: J.evaluate(c) for c in CASES1}
FB1 = {f.ticket_id: f.rating for f in simulate_feedback(CASES1, seed=SEED)}
TOOLS1 = {r.ticket_id: r.tools_used for r in RES1}
SRC = {t.ticket_id: t for t in TK}

def run_telemetry(version, tickets, rate=0.3):
    ta = setup_telemetry("supportops-agent", mode="memory", set_global=False)
    te = setup_telemetry("supportops-evaluator", mode="memory", set_global=False)
    ev = OnlineEvaluator(J, RateSampler(rate, "tel"), te)
    agent, col = make_agent(version, instrumentors=[OTelInstrumentor(ta), VersionTagInstrumentor(version)], collector=CaseCollector(version, on_case=ev.submit))
    res = [agent.run(t) for t in tickets]; ev.run_pending(); ta.force_flush(); te.force_flush()
    return ta.span_records(), event_records(te), col.cases

sp1, ev1, _ = run_telemetry("v1", generate_tickets(500, seed=11, fault_rates=DEFAULT_FAULT_RATES))
sp2, ev2, cases_v2 = run_telemetry("v2", generate_tickets(500, seed=12, fault_rates=DEFAULT_FAULT_RATES))
SPANS, EVENTS = sp1 + sp2, ev1 + ev2                                       # LO ÚNICO que tienes para el Paso 4 (la verdad queda oculta en TRUTH_REG)
TRUTH_REG = {c.ticket_id for c in cases_v2 if "prompt_regression" in c.truth["faults"]}
print(f"producción v1: {len(CASES1)} casos, {sum(not v.passed for v in VERD1.values())} fallos del juez, {len(FB1)} valoraciones · telemetría A/B: {len(SPANS)} spans, {len(EVENTS)} eventos de evaluación")
print("un span invoke_agent:", {k: v for k, v in next(s for s in SPANS if s["name"].startswith("invoke_agent"))["attributes"].items() if k.startswith(("gen_ai.agent", "supportops.tool", "supportops.intent", "supportops.status"))})
''')

    # ---------------------------------------------------------------------------------- 1
    md("""
    ## Paso 1 · El dataset de oro desde trazas

    **TODO 1.** `build_golden(cases, verdicts, feedback, n_total, tools_by_ticket)` devuelve una lista de `dict` `{"case_id", "question", "reason", "source_ticket_id", "expected_tools", "weight"}` con estas reglas (las mismas que la lección, §3):

    1. Reparte cada `EvalCase` en **un** cubo, por este orden de prioridad: `thumbs_down` (`feedback[ticket] < 0`), `judge_fail` (`not verdicts[ticket].passed`), `error` (`status` ∈ {error, max_steps, degraded}), `escalated`, `random_pass` (el resto con veredicto).
    2. Recorre los cubos en ese orden; dentro de cada uno ordena por `stable_hex(8, "golden", 42, c.ticket_id)`. Cuotas: `thumbs_down`, `judge_fail` y `random_pass` hasta `n_total`; `error` y `escalated` hasta `max(n_total // 6, 4)`. Para al llegar a `n_total` casos.
    3. **Deduplica** por `c.question.lower()` sin el sufijo « mi correo es…»: un duplicado **suma 1 al `weight`** del caso ya existente y no cuenta para la cuota. `weight` empieza en 1.
    4. `question` = la pregunta **sin** el sufijo «Mi correo es…» y pasada por `scrub_pii`. `case_id` = `G-001`, `G-002`…
    5. `expected_tools`: las herramientas usadas por el ticket (`tools_by_ticket`) **solo si** su veredicto aprobó y `status == "ok"`; si no, `[]` (la función del paquete, `select_golden`, rellena además esos huecos con la trayectoria más frecuente de la misma intención; aquí basta con `[]`).
    """)
    md(hint(1, "Un `dict` de cubos `{razón: []}`; clasifica con un `if/elif` en el orden de prioridad. La clave de deduplicación es `re.sub(r'\\s*mi correo es.*$', '', c.question.lower()).strip()`."))
    md(hint(2, "Recorre `for reason, quota in cuotas:` ; `pool = sorted(buckets[reason], key=lambda c: stable_hex(8, 'golden', 42, c.ticket_id))`; para cada `c`: si la clave ya está en `seen`, `seen[key]['weight'] += 1` y `continue`; si no, comprueba `quota > 0` y `len(out) < n_total`."))
    code('''
def build_golden(cases, verdicts, feedback, n_total, tools_by_ticket) -> list:
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    G = build_golden(CASES1, VERD1, FB1, 120, TOOLS1)
    print(len(G), collections.Counter(g["reason"] for g in G), G[0])
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 2
    md("""
    ## Paso 2 · La compuerta: comparación apareada

    **TODO 2.** `compare_versions(base, cand, margin=0.03)` recibe dos listas de filas de `replay(...)` (dicts con `case_id`, `passed`, …) de **los mismos casos** y devuelve `{"b", "c", "diff", "p_value", "decision"}`:
    `b` = casos que pasan con la base y fallan con la candidata, `c` = al revés, `diff` = calidad candidata − calidad base, `p_value` = `mcnemar_exact(b, c)` y `decision` = `"block"` si `diff < -margin` **y** `p_value < 0,05` (si no, `"ship"`). Lanza `ValueError` si las listas no tienen los mismos `case_id` en el mismo orden.
    """)
    code('''
GOLD = select_golden(CASES1, VERD1, FB1, n_total=120, tools_by_ticket=TOOLS1)        # (lo da el paquete: úsalo en los pasos 2 y 3 aunque tu build_golden aún no esté)
GT = golden_to_tickets(GOLD, SRC)
REP = {v: replay(GOLD, GT, v, J) for v in ("v1", "v2", "v2.1")}

def compare_versions(base: list, cand: list, margin: float = 0.03) -> dict:
    # TODO 2
    raise NotImplementedError("TODO 2")

try:
    for v in ("v2", "v2.1"): print(v, compare_versions(REP["v1"], REP[v]))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 3
    md("""
    ## Paso 3 · Vigilar el comportamiento sin juez

    **TODO 3a.** `fingerprint(rows)` recibe filas por ticket (dicts con `n_llm_calls`, `n_tool_calls`, `input_tokens`, `output_tokens`, `cost_usd`, `latency_s`, `status`) y devuelve `{"llm_calls", "tool_calls", "no_tool_rate", "output_tokens", "input_tokens", "cost_usd", "latency_s", "error_rate"}`: las **medias** (y `no_tool_rate` = fracción con 0 herramientas, `error_rate` = fracción con `status` ∈ {error, max_steps}).

    **TODO 3b.** `drift_flags(ref, cur)` recibe dos huellas y devuelve la **lista ordenada alfabéticamente** de métricas «marcadas»: `no_tool_rate` si sube más de **0,05** (absoluto); `error_rate` si sube más de **0,02**; y cualquier otra si cambia más de un **15 %** en relativo (`abs(cur-ref)/ref > 0,15`, ignorando `ref == 0`).
    """)
    code('''
def fingerprint(rows: list) -> dict:
    # TODO 3a
    raise NotImplementedError("TODO 3a")

def drift_flags(ref: dict, cur: dict) -> list:
    # TODO 3b
    raise NotImplementedError("TODO 3b")

ROWS = {v: [dict(r.to_dict(), n_tool_calls=r.n_tool_calls) for r in run_version(v, TK)[0]] for v in ("v1", "v2", "v2.1")}
try:
    FP = {v: fingerprint(ROWS[v]) for v in ROWS}
    print({v: {k: round(x, 3) for k, x in f.items()} for v, f in FP.items()})
    print({v: drift_flags(FP["v1"], FP[v]) for v in ("v2", "v2.1")})
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 4
    md("""
    ## Paso 4 · Cazar la regresión solo con telemetría

    **TODO 4.** `find_regression(spans, events)` recibe la lista de spans (`SPAN_SCHEMA`) y los eventos de evaluación (`{"attributes": {...}}`) y devuelve `{"culprit", "groundedness", "p_value", "suspects"}`:

    - `groundedness`: `dict` versión → fracción de eventos `gen_ai.evaluation.name == "groundedness"` con `score.label == "pass"` (agrupa por `gen_ai.agent.version` del evento).
    - `culprit`: la versión con **menor** groundedness si la diferencia con la otra es significativa (`two_proportion_test(...)["p_value"] < 0,01`), si no `None`.
    - `suspects`: `trace_id` de los spans `invoke_agent` de la versión culpable con `supportops.tool_calls == 0`, `supportops.status == "ok"` e `supportops.intent` ∈ {`order_status`, `refund`, `kb_question`}.
    """)
    md(hint(1, "Los spans `invoke_agent` tienen `attributes['gen_ai.operation.name'] == 'invoke_agent'`, `gen_ai.agent.version`, `supportops.tool_calls`, `supportops.status` y `supportops.intent`. Cada evento lleva `gen_ai.agent.version`, `gen_ai.evaluation.name` y `gen_ai.evaluation.score.label`."))
    code('''
def find_regression(spans: list, events: list) -> dict:
    # TODO 4
    raise NotImplementedError("TODO 4")

try:
    FR = find_regression(SPANS, EVENTS)
    print(FR["culprit"], {k: round(v, 3) for k, v in FR["groundedness"].items()}, f"p={FR['p_value']:.2g}", len(FR["suspects"]), "trazas sospechosas")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 5
    md("""
    ## Paso 5 · Canario con decisión secuencial

    **TODO 5.** `canary_decision(fails, p0, p1, alpha=0.05, beta=0.2)` recibe una lista de booleanos (`True` = fallo de calidad en cada evaluación del canario, en orden) y devuelve `(decisión, n)`: tras cada observación `i` (1-based) calcula
    \\( \\Lambda_i = k\\ln\\frac{p_1}{p_0} + (i-k)\\ln\\frac{1-p_1}{1-p_0} \\) y devuelve `("rollback", i)` si \\( \\Lambda_i \\ge \\ln\\frac{1-\\beta}{\\alpha} \\), `("promote", i)` si \\( \\Lambda_i \\le \\ln\\frac{\\beta}{1-\\alpha} \\); si termina sin cruzar ninguna cota, `("continue", len(fails))`.
    """)
    code('''
def canary_decision(fails: list, p0: float, p1: float, alpha: float = 0.05, beta: float = 0.2) -> tuple:
    # TODO 5
    raise NotImplementedError("TODO 5")

FAILS = {v: [not x.scores["groundedness"].label == "pass" for x in [J.evaluate(c) for c in run_version(v, TK[:400])[1]]] for v in ("v1", "v2")}
try:
    print({v: canary_decision(f, 0.07, 0.15) for v, f in FAILS.items()}, canary_decision(FAILS["v1"][:15], 0.07, 0.15))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 6
    md("""
    ## Paso 6 · El panel de regresión como código

    **TODO 6.** `build_regression_dashboard()` devuelve el `dict` de un dashboard con **uid** `regresion-versiones`, título «15 · Regresión por versión (proyecto)» y **al menos 8 paneles con `description`** que incluyan estas consultas:

    1. **Calidad por versión**: `sum by (gen_ai_agent_version)` sobre `supportops_eval_results_total` con `gen_ai_evaluation_score_label="pass"`.
    2. **Tráfico por versión**: `supportops_eval_population_total` agrupado por `gen_ai_agent_version`.
    3. **Herramientas por ticket**: `gen_ai_invoke_agent_tool_calls_sum` / `gen_ai_invoke_agent_tool_calls_count`.
    4. **Latencia p95 clásica**: `histogram_quantile(0.95, …gen_ai_invoke_agent_duration_seconds_bucket…)`.
    5. **Coste por ticket**: `supportops_agent_request_cost_USD_sum` / `_count`.
    6. **Errores**: `supportops_agent_requests_total` con `supportops_status=~"error|max_steps"`.
    7. **Trazas sospechosas (Tempo)**: contiene `span.gen_ai.agent.version` y `span.supportops.tool_calls = 0`.
    8. **Evaluaciones fallidas por versión (Loki)**: contiene `gen_ai_evaluation_score_label="fail"` y `gen_ai_agent_version`.
    """)
    code('''
def build_regression_dashboard() -> dict:
    # TODO 6
    raise NotImplementedError("TODO 6")

try:
    D = build_regression_dashboard(); print(len(D["panels"]), "paneles · lint:", lint(D) or "OK")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- rúbrica
    md("""
    ## Paso 7 · Rúbrica
    """)
    code('''
def run_rubric():
    rows = []
    def add(r, d, ok, det=""): rows.append({"criterio": r, "descripción": d, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": det})
    # R1
    try:
        G = build_golden(CASES1, VERD1, FB1, 120, TOOLS1); ref = select_golden(CASES1, VERD1, FB1, n_total=120, tools_by_ticket=TOOLS1)
        sig = lambda x: [(g["source_ticket_id"], g["reason"], g["weight"]) for g in x] if isinstance(x[0], dict) else [(g.source_ticket_id, g.reason, g.weight) for g in x]
        keys = [re.sub(r"\\s*mi correo es.*$", "", g["question"].lower()).strip() for g in G]
        checks = {"mismos casos, razones y pesos": sig(G) == sig(ref), "sin duplicados": len(set(keys)) == len(keys), "sin PII": all("@" not in g["question"] and "correo es" not in g["question"].lower() for g in G),
                  "ids y pesos": [g["case_id"] for g in G] == [f"G-{i + 1:03d}" for i in range(len(G))] and all(g["weight"] >= 1 for g in G), "trayectorias": all(g["expected_tools"] == (r.expected_tools if (VERD1[g["source_ticket_id"]].passed and next(c for c in CASES1 if c.ticket_id == g["source_ticket_id"]).status == "ok") else []) for g, r in zip(G, ref))}
        add("R1", "build_golden: 5 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or f"todas OK · {len(G)} casos"))
    except Exception as e: add("R1", "build_golden", False, f"{type(e).__name__}: {e}")
    # R2
    try:
        a, b = compare_versions(REP["v1"], REP["v2"]), compare_versions(REP["v1"], REP["v1"])
        bb = sum(x["passed"] and not y["passed"] for x, y in zip(REP["v1"], REP["v2"])); cc = sum((not x["passed"]) and y["passed"] for x, y in zip(REP["v1"], REP["v2"]))
        def raises(): 
            try: compare_versions(REP["v1"], REP["v2"][:-1])
            except ValueError: return True
            except Exception: return False
            return False
        checks = {"v2 bloqueada": a["decision"] == "block", "v1 vs v1 pasa": b["decision"] == "ship" and b["p_value"] == 1.0, "b, c y p exactos": (a["b"], a["c"]) == (bb, cc) and abs(a["p_value"] - mcnemar_exact(bb, cc)) < 1e-12, "ValueError si no son los mismos casos": raises()}
        add("R2", "compare_versions: 4 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or f"todas OK · v1→v2: {a}"))
    except Exception as e: add("R2", "compare_versions", False, f"{type(e).__name__}: {e}")
    # R3
    try:
        FPs = {v: fingerprint(ROWS[v]) for v in ROWS}
        ref = {v: behavior_fingerprint(ROWS[v]) for v in ROWS}
        same = all(abs(FPs[v][k] - ref[v][k]) < 1e-9 for v in ROWS for k in ("llm_calls", "tool_calls", "no_tool_rate", "output_tokens", "input_tokens", "cost_usd", "latency_s", "error_rate"))
        f2, f21 = drift_flags(FPs["v1"], FPs["v2"]), drift_flags(FPs["v1"], FPs["v2.1"])
        checks = {"huella exacta": same, "v2 marca no_tool_rate y tool_calls": "no_tool_rate" in f2 and "tool_calls" in f2, "v2.1 no marca no_tool_rate (sube < 0,05)": "no_tool_rate" not in f21, "orden alfabético": f2 == sorted(f2)}
        add("R3", "fingerprint y drift_flags: 4 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or f"v2: {f2} · v2.1: {f21}"))
    except Exception as e: add("R3", "fingerprint/drift_flags", False, f"{type(e).__name__}: {e}")
    # R4
    try:
        FR = find_regression(SPANS, EVENTS); sus = set(FR["suspects"])
        tid2ticket = {s["trace_id"]: s["attributes"].get("supportops.ticket.id") for s in SPANS if s["name"].startswith("invoke_agent")}
        got = {tid2ticket[t] for t in sus}
        prec = len(got & TRUTH_REG) / max(len(got), 1); rec = len(got & TRUTH_REG) / len(TRUTH_REG)
        ok_ev = {}
        for e in EVENTS:
            a_ = e["attributes"]
            if a_.get("gen_ai.evaluation.name") == "groundedness": ok_ev.setdefault(a_["gen_ai.agent.version"], []).append(a_["gen_ai.evaluation.score.label"] == "pass")
        ref_g = {v: sum(x) / len(x) for v, x in ok_ev.items()}
        checks = {"culpable = v2": FR["culprit"] == "v2", "groundedness exacta": all(abs(FR["groundedness"][v] - ref_g[v]) < 1e-9 for v in ref_g), "p < 0,01": FR["p_value"] < 0.01, "precisión ≥ 0,65 y exhaustividad ≥ 0,85": prec >= 0.65 and rec >= 0.85}
        add("R4", "find_regression: 4 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK") + f" · precisión={prec:.2f} exhaustividad={rec:.2f}")
    except Exception as e: add("R4", "find_regression", False, f"{type(e).__name__}: {e}")
    # R5
    try:
        outs = [canary_decision(FAILS["v1"], 0.07, 0.15), canary_decision(FAILS["v2"], 0.07, 0.15), canary_decision(FAILS["v1"][:15], 0.07, 0.15)]
        def ref_dec(f, p0, p1):
            k = 0
            for i, x in enumerate(f, 1):
                k += x; d, _ = sprt_bernoulli(k, i, p0, p1)
                if d != "continue": return (d, i)
            return ("continue", len(f))
        refs = [ref_dec(FAILS["v1"], 0.07, 0.15), ref_dec(FAILS["v2"], 0.07, 0.15), ref_dec(FAILS["v1"][:15], 0.07, 0.15)]
        add("R5", "canary_decision: 3 flujos", outs == refs and outs[1][0] == "rollback" and outs[2][0] == "continue", f"{outs} (ref {refs})")
    except Exception as e: add("R5", "canary_decision", False, f"{type(e).__name__}: {e}")
    # R6
    try:
        D = build_regression_dashboard()
        exprs = []
        for p in D["panels"]:
            for t in p.get("targets", []): exprs.append(t.get("expr") or t.get("query") or "")
        has = lambda *pats: any(all(re.search(p, e) for p in pats) for e in exprs)
        checks = {"lint limpio, uid y ≥ 8 paneles": not lint(D) and D["uid"] == "regresion-versiones" and len(D["panels"]) >= 8,
                  "calidad por versión": has(r"sum by \\(gen_ai_agent_version\\)", r"supportops_eval_results_total", r'score_label="pass"'), "tráfico por versión": has(r"supportops_eval_population_total", r"gen_ai_agent_version"),
                  "herramientas por ticket": has(r"gen_ai_invoke_agent_tool_calls_sum", r"gen_ai_invoke_agent_tool_calls_count"), "latencia p95": has(r"histogram_quantile\\(0\\.95", r"gen_ai_invoke_agent_duration_seconds_bucket"),
                  "coste por ticket": has(r"supportops_agent_request_cost_USD_sum", r"supportops_agent_request_cost_USD_count"), "errores": has(r"supportops_agent_requests_total", r"error\\|max_steps"),
                  "Tempo sospechosas": has(r"span\\.gen_ai\\.agent\\.version", r"span\\.supportops\\.tool_calls = 0"), "Loki fallidas": has(r'gen_ai_evaluation_score_label="fail"', r"gen_ai_agent_version")}
        add("R6", "build_regression_dashboard: lint + 8 consultas", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R6", "build_regression_dashboard", False, f"{type(e).__name__}: {e}")
    return pd.DataFrame(rows).set_index("criterio")
''')
    code('''
# Ejecuta esta celda cuando hayas terminado los TODO
display(run_rubric())
''')

    md("""
    ---
    ## Paso final (opcional) · Míralo funcionar

    Con el stack: guarda tu dashboard (`Dashboard.save(...)` en `stack/grafana/dashboards/`) y ejecuta un despliegue en canario en vivo con `LivePipeline(("v1", "v2"), mode="otlp", sampler=RateSampler(0.6))`
    (ver la sección 9 de la lección). Espera ≈ 20 s: «Calidad por versión» debe separar v1 y v2 mientras latencia y coste de v2 parecen mejores.

    ## Retos extra (nivel experto)

    1. **Detector sin versión**: si los spans NO llevaran `gen_ai.agent.version`, ¿podrías inferir el despliegue? Detecta el punto de cambio con CUSUM sobre `tool_calls` por ticket en una serie temporal y compáralo con el momento del despliegue.
    2. **Potencia del dataset**: calcula con simulación (bootstrap sobre `REP`) la probabilidad de bloquear v2.1 con 60, 120 y 240 casos de oro. ¿Dónde se cruza el 80 %?
    3. **Estratificación del dataset**: reponde los casos por `weight` y por intención para que la métrica del replay refleje la producción; ¿cambia la decisión sobre v2.1?
    4. **Canario multi-criterio**: extiende `canary_decision` para vigilar a la vez calidad, `no_tool_rate` y latencia (corrección de Bonferroni o *alpha spending*).
    5. **Reversión automática**: conecta `canary_decision` con `LivePipeline` y revierte el enrutamiento cuando decida `rollback`; mide cuántos clientes vieron v2 antes de la reversión.

    ## Reflexión (producción e hilo conductor)

    - Tu detector estructural tiene falsos positivos (peticiones legítimas sin herramienta). ¿Cómo evitarías que una alerta basada en él despierte a alguien por una campaña que pregunta cosas nuevas? (módulo 16).
    - ¿Qué metadatos de la traza necesitas conservar para reconstruir el dataset de oro dentro de 3 meses? ¿Y cuáles deberías **borrar** por privacidad (módulo 20)?
    - Con v2.1 la compuerta bloquea por poco: ¿qué decisión de negocio tomas (coste de una regresión residual del 5 % frente al de retrasar el release)?
    - En el capstone el agente es multi-agente (módulo 11): ¿qué cambia en la huella de comportamiento cuando hay handoffs?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine las funciones y vuelve a lanzar la rúbrica).
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
def build_golden(cases, verdicts, feedback, n_total, tools_by_ticket):
    buckets = {"thumbs_down": [], "judge_fail": [], "error": [], "escalated": [], "random_pass": []}
    for c in cases:
        v = verdicts.get(c.ticket_id)
        if feedback.get(c.ticket_id, 0) < 0: buckets["thumbs_down"].append(c)
        elif v is not None and not v.passed: buckets["judge_fail"].append(c)
        elif c.status in ("error", "max_steps", "degraded"): buckets["error"].append(c)
        elif c.status == "escalated": buckets["escalated"].append(c)
        elif v is not None: buckets["random_pass"].append(c)
    quota = {"thumbs_down": n_total, "judge_fail": n_total, "error": max(n_total // 6, 4), "escalated": max(n_total // 6, 4), "random_pass": n_total}
    out, seen = [], {}
    for reason in ("thumbs_down", "judge_fail", "error", "escalated", "random_pass"):
        for c in sorted(buckets[reason], key=lambda c: stable_hex(8, "golden", 42, c.ticket_id)):
            if len(out) >= n_total or quota[reason] <= 0: break
            key = re.sub(r"\\s*mi correo es.*$", "", c.question.lower()).strip()
            if key in seen:
                seen[key]["weight"] += 1; continue
            quota[reason] -= 1
            v = verdicts.get(c.ticket_id)
            tools = list(tools_by_ticket.get(c.ticket_id, [])) if (v is not None and v.passed and c.status == "ok") else []
            g = {"case_id": f"G-{len(out) + 1:03d}", "question": re.sub(r"\\s*Mi correo es.*$", "", scrub_pii(c.question)), "reason": reason, "source_ticket_id": c.ticket_id, "expected_tools": tools, "weight": 1.0}
            seen[key] = g; out.append(g)
    return out

def compare_versions(base, cand, margin=0.03):
    if [r["case_id"] for r in base] != [r["case_id"] for r in cand]: raise ValueError("las listas deben ser de los mismos casos")
    b = sum(bool(x["passed"]) and not bool(y["passed"]) for x, y in zip(base, cand)); c = sum((not bool(x["passed"])) and bool(y["passed"]) for x, y in zip(base, cand))
    diff = np.mean([bool(y["passed"]) for y in cand]) - np.mean([bool(x["passed"]) for x in base]); p = mcnemar_exact(b, c)
    return {"b": b, "c": c, "diff": float(diff), "p_value": p, "decision": "block" if diff < -margin and p < 0.05 else "ship"}

def fingerprint(rows):
    n = len(rows); m = lambda k: sum(float(r[k]) for r in rows) / n
    return {"llm_calls": m("n_llm_calls"), "tool_calls": m("n_tool_calls"), "no_tool_rate": sum(int(r["n_tool_calls"]) == 0 for r in rows) / n, "output_tokens": m("output_tokens"),
            "input_tokens": m("input_tokens"), "cost_usd": m("cost_usd"), "latency_s": m("latency_s"), "error_rate": sum(r["status"] in ("error", "max_steps") for r in rows) / n}

def drift_flags(ref, cur):
    flags = []
    for k in ref:
        if k == "no_tool_rate": hit = cur[k] - ref[k] > 0.05
        elif k == "error_rate": hit = cur[k] - ref[k] > 0.02
        else: hit = ref[k] != 0 and abs(cur[k] - ref[k]) / ref[k] > 0.15
        if hit: flags.append(k)
    return sorted(flags)

def find_regression(spans, events):
    cnt = {}
    for e in events:
        a = e["attributes"]
        if a.get("gen_ai.evaluation.name") == "groundedness":
            k = cnt.setdefault(a["gen_ai.agent.version"], [0, 0]); k[1] += 1; k[0] += a["gen_ai.evaluation.score.label"] == "pass"
    g = {v: k / n for v, (k, n) in cnt.items()}
    (va, (ka, na)), (vb, (kb, nb)) = sorted(cnt.items())[:2]
    p = two_proportion_test(ka, na, kb, nb)["p_value"]
    worst = min(g, key=g.get)
    culprit = worst if p < 0.01 else None
    sus = [s["trace_id"] for s in spans if s["attributes"].get("gen_ai.operation.name") == "invoke_agent" and s["attributes"].get("gen_ai.agent.version") == culprit
           and s["attributes"].get("supportops.tool_calls") == 0 and s["attributes"].get("supportops.status") == "ok" and s["attributes"].get("supportops.intent") in ("order_status", "refund", "kb_question")]
    return {"culprit": culprit, "groundedness": g, "p_value": p, "suspects": sus}

def canary_decision(fails, p0, p1, alpha=0.05, beta=0.2):
    up, lo = math.log((1 - beta) / alpha), math.log(beta / (1 - alpha)); k = 0
    for i, f in enumerate(fails, 1):
        k += bool(f); llr = k * math.log(p1 / p0) + (i - k) * math.log((1 - p1) / (1 - p0))
        if llr >= up: return ("rollback", i)
        if llr <= lo: return ("promote", i)
    return ("continue", len(fails))

def build_regression_dashboard():
    d = Dashboard("regresion-versiones", "15 · Regresión por versión (proyecto)", tags=["curso", "regresion"], description="Calidad, comportamiento y señales clásicas por versión del agente.")
    d.add(
        timeseries("Calidad por versión", [prom('sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m])) / sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))', "{{gen_ai_agent_version}}")], unit="percentunit", w=12, description="Groundedness por versión."),
        timeseries("Tráfico por versión", [prom("sum by (gen_ai_agent_version) (rate(supportops_eval_population_total[5m]))", "{{gen_ai_agent_version}}")], w=12, description="Peticiones por segundo por versión (reparto del canario)."),
        timeseries("Herramientas por ticket", [prom("sum(rate(gen_ai_invoke_agent_tool_calls_sum[5m])) / sum(rate(gen_ai_invoke_agent_tool_calls_count[5m]))", "herramientas/ticket")], w=8, description="Baja cuando el agente deja de consultar."),
        timeseries("Latencia p95 (clásica)", [prom("histogram_quantile(0.95, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket[5m])))", "p95")], unit="s", w=8, description="La señal clásica mejora con la regresión."),
        timeseries("Coste por ticket", [prom("sum(rate(supportops_agent_request_cost_USD_sum[5m])) / sum(rate(supportops_agent_request_cost_USD_count[5m]))", "USD/ticket")], unit="currencyUSD", w=8, description="Coste medio por ticket (ilustrativo)."),
        timeseries("Errores", [prom('sum(rate(supportops_agent_requests_total{supportops_status=~"error|max_steps"}[5m])) / sum(rate(supportops_agent_requests_total[5m]))', "error ratio")], unit="percentunit", w=8, description="Tasa de error: no cambia con la regresión."),
        traces_table("Trazas sospechosas (Tempo)", '{ name =~ "invoke_agent.*" && span.gen_ai.agent.version = "v2" && span.supportops.tool_calls = 0 && span.supportops.intent =~ "order_status|refund" }', w=8, description="Tickets de v2 que debían usar una herramienta y no la usaron."),
        logs("Evaluaciones fallidas por versión (Loki)", '{service_name="supportops-evaluator"} | gen_ai_evaluation_score_label="fail" | gen_ai_agent_version="v2"', w=8, description="Eventos de evaluación fallidos de la versión v2."),
    )
    return d.to_dict()

display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, lint, logs, prom, stat, table, text, thresholds, timeseries, traces_table
    d = Dashboard("regresion-versiones", "15 · Regresión por versión", tags=["curso", "calidad", "regresion"], time_from="now-30m",
                  description="Comparativa de versiones del agente (canario/despliegue): calidad medida por el juez frente a las señales clásicas (latencia, coste, errores) y a la huella de comportamiento.")
    d.add(text("Cómo leer este dashboard", "Una **regresión silenciosa** empeora la calidad mientras las señales clásicas parecen **iguales o mejores**. Fila 1: lo que dice el juez, por versión (`gen_ai.agent.version`). "
               "Fila 2: lo que dicen los paneles de siempre (módulo 10) — fíjate en que NO tienen etiqueta de versión pero muestran el escalón del despliegue. "
               "Fila 3: la huella de comportamiento (herramientas por ticket) y las trazas sospechosas (v2 sin ninguna herramienta en pedidos/reembolsos).", h=3))
    gp = 'sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m])) / sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))'
    d.row("Lo que dice el juez, por versión")
    d.add(
        timeseries("Calidad por versión (groundedness)", [prom(gp, "{{gen_ai_agent_version}}")], unit="percentunit", w=12, description="Tasa de respuestas fundamentadas por versión. Una versión por debajo de otra durante un canario = regresión."),
        timeseries("Calidad por criterio y versión", [prom('sum by (gen_ai_evaluation_name, gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_score_label="pass"}[5m])) / sum by (gen_ai_evaluation_name, gen_ai_agent_version) (rate(supportops_eval_results_total[5m]))',
                                                       "{{gen_ai_evaluation_name}} · {{gen_ai_agent_version}}")], unit="percentunit", w=12, description="Pass-rate de cada criterio por versión: solo groundedness (y relevancia) caen con v2."),
        timeseries("Tráfico por versión", [prom("sum by (gen_ai_agent_version) (rate(supportops_eval_population_total[5m]))", "{{gen_ai_agent_version}}")], w=8, description="Peticiones/s por versión: el reparto real del canario."),
        timeseries("Evaluaciones por versión", [prom("sum by (gen_ai_agent_version) (rate(supportops_eval_sampled_total[5m]))", "{{gen_ai_agent_version}}")], w=8, description="Evaluaciones/s por versión: poca muestra = decisión poco fiable."),
        stat("Diferencia de calidad v2 − v1", f'(sum(rate(supportops_eval_results_total{{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass",gen_ai_agent_version="v2"}}[5m])) / sum(rate(supportops_eval_results_total{{gen_ai_evaluation_name="groundedness",gen_ai_agent_version="v2"}}[5m]))) - (sum(rate(supportops_eval_results_total{{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass",gen_ai_agent_version="v1"}}[5m])) / sum(rate(supportops_eval_results_total{{gen_ai_evaluation_name="groundedness",gen_ai_agent_version="v1"}}[5m])))',
             unit="percentunit", w=8, h=8, decimals=3, thr=thresholds((None, "red"), (-0.03, "orange"), (0, "green")), description="Diferencia de groundedness del canario (v2) frente a la versión estable (v1): negativa = regresión."),
    )
    d.row("Lo que dicen los paneles clásicos")
    d.add(
        timeseries("Latencia p95 del agente", [prom("histogram_quantile(0.95, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket{service_name=\"supportops-agent\"}[5m])))", "p95")], unit="s", w=8, description="Mejora (o no cambia) con la regresión."),
        timeseries("Coste por ticket", [prom('sum(rate(supportops_agent_request_cost_USD_sum{service_name="supportops-agent"}[5m])) / sum(rate(supportops_agent_request_cost_USD_count{service_name="supportops-agent"}[5m]))', "USD/ticket")], unit="currencyUSD", w=8, description="Coste medio por ticket (precios ilustrativos): baja cuando se dejan de llamar herramientas."),
        timeseries("Tasa de error", [prom('sum(rate(supportops_agent_requests_total{service_name="supportops-agent",supportops_status=~"error|max_steps"}[5m])) / sum(rate(supportops_agent_requests_total{service_name="supportops-agent"}[5m]))', "error ratio")], unit="percentunit", w=8, description="No cambia: la petición termina bien aunque la respuesta sea inventada."),
    )
    d.row("Huella de comportamiento y trazas sospechosas")
    d.add(
        timeseries("Herramientas por ticket", [prom('sum(rate(gen_ai_invoke_agent_tool_calls_sum{service_name="supportops-agent"}[5m])) / sum(rate(gen_ai_invoke_agent_tool_calls_count{service_name="supportops-agent"}[5m]))', "herramientas/ticket")], w=8, description="Desciende cuando una versión deja de consultar herramientas: detecta la regresión SIN juez."),
        traces_table("Trazas sospechosas de v2 (Tempo)", '{ name =~ "invoke_agent.*" && span.gen_ai.agent.version = "v2" && span.supportops.tool_calls = 0 && span.supportops.intent =~ "order_status|refund" }', w=8, h=8,
                     description="Tickets de v2 sobre pedidos/reembolsos sin ninguna herramienta: la huella estructural de la regresión."),
        logs("Evaluaciones fallidas de v2 (Loki)", '{service_name="supportops-evaluator"} | gen_ai_evaluation_name="groundedness" | gen_ai_evaluation_score_label="fail" | gen_ai_agent_version="v2"', w=8, h=8,
             description="Eventos gen_ai.evaluation.result fallidos de la versión v2; el trace_id es el de la traza del agente evaluada."),
    )
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "15-regresion-versiones.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
def build_readme() -> None:
    readme = """# Módulo 15 · Calidad y regresión de agentes

🔴 **Experto** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ Las versiones de prompt (`v1`, `v2` «regresión silenciosa», `v2.1` hotfix) son **simuladas** sobre el `mock` (`PromptVariantLLM`): reproducen el patrón de una regresión real con el *ground truth* en los datos.
> Las cifras cambian con modelos reales; el método no.

Un prompt «más conciso» baja la latencia y el coste… y hace que el agente se invente datos. Ningún panel clásico lo ve. Este módulo construye la red de seguridad: **dataset de oro desde trazas**, **replay y compuerta de release** con estadística apareada,
**poder estadístico**, **drift** de entrada/comportamiento/calidad (PSI, JS, CUSUM), **canarios con SPRT** y la detección **usando solo telemetría**.

## Objetivos
1. Explicar por qué una regresión de prompt/modelo es silenciosa y qué señales la delatan.
2. Construir un dataset de regresión desde trazas (fallos, feedback negativo, escalados y muestra de buenos), sin duplicados ni PII.
3. Decidir con una compuerta de release (McNemar apareado) y calcular su poder estadístico y el problema del *peeking*.
4. Medir drift de entrada y de comportamiento y detectar caídas de calidad con CUSUM.
5. Diseñar un canario con decisión secuencial (SPRT) y enrutamiento determinista.
6. Localizar una regresión solo con spans y eventos de evaluación (TraceQL/PromQL/LogQL).

## Contenido
| Archivo | Qué es |
|---|---|
| `15_calidad_regresion.ipynb` | Lección (14 secciones, 11 gráficos, canario en vivo con el stack real, 🧠 de élite, autoevaluación) |
| `15_proyecto_calidad_regresion.ipynb` | Proyecto: dataset de oro, compuerta apareada, huella de comportamiento, detección solo con telemetría, canario SPRT y panel como código (rúbrica, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/regression.py` | `PromptVariantLLM`, `select_golden`/`replay`/`ReleaseGate`, estadística (McNemar, potencia, bootstrap), drift (`psi`, `js_divergence`, `ks_2samp`, `Cusum`), canarios (`canary_route`, `sprt_bernoulli`), `trace_shapes`/`version_report`, `LivePipeline` |
| `../supportops/tests/test_regression.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/15-regresion-versiones.json` | Dashboard «15 · Regresión por versión» (uid `regresion-versiones`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 9 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`).

## Lecturas
- OpenTelemetry GenAI semantic conventions: `gen_ai.agent.version`, `gen_ai.prompt.name`/`gen_ai.prompt.version`, evento `gen_ai.evaluation.result`.
- Wald (1945), SPRT · Johari et al. (2017), *Peeking at A/B Tests* · Page (1954), CUSUM · Kohavi et al. (2020), *Trustworthy Online Controlled Experiments* · SRE Workbook, cap. «Canarying Releases».

## Cómo se conecta
Antes: módulo 14 (juez, muestreo, sesgos, eventos de evaluación), 09 (métricas), 07 (TraceQL). Después: el 16 convierte la calidad en un SLO con *burn rate* y alertas; el 18 decide cuánto muestrear y evaluar con un presupuesto; el 21 reutiliza la regresión silenciosa en la «mesa de incidentes».
"""
    (COURSE / MOD / "README.md").write_text(readme, encoding="utf-8")
    print("OK README", MOD)


if __name__ == "__main__":
    build_lesson()
    build_project()
    build_readme()
    build_dashboard()
