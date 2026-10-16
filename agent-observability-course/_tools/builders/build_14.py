"""Genera el módulo 14_evaluacion_online: README, lección, proyecto y dashboard.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_14.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "14_evaluacion_online"

IMPORTS_14 = '''
import dataclasses, json, math, re, time
from supportops.instrument import CompositeInstrumentor
from supportops.telemetry import OTelInstrumentor, setup_telemetry
from supportops.quality_eval import (EVALUATORS, EVENT_NAME, CaseCollector, EvalCase, EvalScore, LLMJudge, MockJudge, OnlineEvaluator, RateSampler, RuleJudge,
                                     StratifiedSampler, build_eval_event, confusion, extract_claims, find_pii, post_stratified_rate, render_judge_prompt,
                                     required_sample_size, rogan_gladen, scrub_pii, simulate_feedback, unsupported_claims, wilson_interval)
STACK = check_stack("core+metrics")
LIVE = not STACK.degraded                      # True: Collector + Prometheus responden y la sección 8 envía telemetría de verdad
'''

DATA_14 = '''
N = 600 if FAST_DEV_RUN else 3000
FAULTS = {**DEFAULT_FAULT_RATES, "hallucination": 0.06}            # alucinaciones al 6 % (el doble que la base) para tener qué detectar
TICKETS = generate_tickets(N, seed=SEED, fault_rates=FAULTS)
col = CaseCollector()                                                 # un EvalCase por ticket: lo que verá el juez + ground truth APARTE
RESULTS = run_tickets(SupportAgent(instrumentor=col), TICKETS)
CASES = col.cases
RULE, JUDGE = RuleJudge(), MockJudge(SEED)
print(f"{len(CASES)} casos · alucinaciones reales: {sum(not c.truth['grounded'] for c in CASES)} · fugas de PII: {sum(c.truth['pii_leaked'] for c in CASES)} · "
      f"tickets sin resolver: {sum(c.status in ('error', 'max_steps', 'degraded') for c in CASES)}")
'''


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "14_evaluacion_online.ipynb", "Módulo 14 · Evaluación online de agentes de IA")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 14 · Evaluación online: ¿las respuestas son buenas?, medido en producción

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Opcional: `--profile core --profile metrics` (sección 8 y paso final). Sin Docker todo funciona en **modo degradado** (telemetría en memoria, mismo esquema). Funciona en Colab |
    | **RAM aproximada** | < 500 MB sin stack · ≈ 1,2 GB con `core` + `metrics` |
    | **Prerrequisitos** | Módulos 04 (GenAI semconv), 08 (Loki), 09 (métricas), 10 (Grafana) y 13 (coste por ticket) |
    | **Hilo conductor** | SupportOps responde rápido y barato… pero ¿responde **bien**? Ningún dashboard de latencia ni de errores lo sabe |

    > ⚠️ **Honestidad sobre el laboratorio.** El agente y el «juez» de este módulo son **simulados y deterministas** (`mock`): el juez es un conjunto de reglas con errores
    > realistas (falsos negativos, falsos positivos, sesgo de verbosidad y de posición) para que **puedas medir sus defectos contra la verdad de terreno**, cosa que con un
    > LLM real hay que hacer con etiquetas humanas. Las cifras cambian con un juez real; el **método** no.
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Distinguir** evaluación *offline* y *online*, y elegir el tipo de evaluador (reglas, juez LLM, humano, feedback) según coste, latencia y fiabilidad.
    2. **Implementar a mano** un evaluador de *groundedness* (afirmaciones respaldadas por el contexto) y medir su sensibilidad y especificidad contra la verdad.
    3. **Emitir** una evaluación como telemetría OpenTelemetry: evento `gen_ai.evaluation.result` (spec GenAI, estado *Development*) asociado al span evaluado, span del juez enlazado a la traza original y métricas.
    4. **Diseñar** un muestreo estratificado para evaluar y **estimar** la calidad poblacional sin sesgo (post-estratificación) con su intervalo de confianza.
    5. **Detectar y cuantificar** los sesgos del juez (verbosidad, posición) y **corregir** una tasa observada con la sensibilidad/especificidad del juez (Rogan–Gladen).
    6. **Interpretar** el feedback de usuario como señal sesgada por la tasa de respuesta, y combinarlo con el juez.
    7. **Calcular** el coste de evaluar y elegir una tasa de muestreo que cumpla un presupuesto y una precisión.
    8. **Construir** un panel de Grafana de calidad online con sus consultas (PromQL, LogQL, TraceQL).
    """)

    md("## 🔁 Conexión con módulos anteriores")
    md(details("1 · (Módulo 04) ¿En qué estado está la spec GenAI y por qué importa para los nombres que usaremos hoy?",
               "Está en estado *Development* (inestable): los nombres pueden cambiar. Por eso en SupportOps los atributos se escriben como cadenas verificadas contra una instantánea de la spec y no se importan de librerías que van por detrás."))
    md(details("2 · (Módulo 13) ¿Dónde se suman los tokens y el coste de un ticket sin duplicar?",
               "Solo en los spans hoja `chat`. Hoy esto tiene una consecuencia: el **juez** también hace llamadas `chat`; por eso vive en **otro servicio** (`supportops-evaluator`) y su coste no se mezcla con el del agente."))
    md(details("3 · (Módulo 09) ¿Por qué `ticket_id` no puede ser una etiqueta de una métrica?",
               "Cada valor distinto crea una serie temporal nueva: cardinalidad ilimitada. Los identificadores van en spans/logs; las métricas llevan etiquetas acotadas (estrato, criterio, etiqueta pass/fail, versión)."))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_14)
    code(DATA_14)

    # ------------------------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · Intuición: el dashboard verde que miente

    Imagina el panel de salud de SupportOps (módulo 10): latencia p95 estable, 0,8 % de errores, coste por ticket normal… y el agente lleva una hora **inventándose el número de
    seguimiento de los pedidos**. Ninguna señal clásica lo ve: la petición *terminó bien* (HTTP 200, `status=ok`) y rápido. **La calidad es una propiedad del contenido**, no de la ejecución.

    | Si vienes de… | Esto es como… | Lo que cambia |
    |---|---|---|
    | **ML / ciencia de datos** | Evaluación *offline* con un conjunto de test vs monitorizar el modelo en producción | No hay etiqueta de verdad por petición: hay que **estimarla** (reglas, juez, humanos, feedback) y **muestrear** porque evaluar cuesta |
    | **Backend** | Un *health check* que devuelve 200 pero la base de datos devuelve datos corruptos | El «200» no prueba que el resultado sea correcto: necesitas una **comprobación semántica** (un *canary* funcional) |
    | **SRE** | SLI de calidad de servicio: no solo «¿responde?» sino «¿responde bien?» | La calidad se convierte en un SLI con su SLO y su presupuesto (módulo 16) |

    El patrón de la industria: **la evaluación online es otro consumidor de la telemetría**. La traza ya contiene la pregunta, el contexto recuperado y la respuesta; un evaluador asíncrono
    (fuera del camino crítico de la petición) lee una **muestra**, la puntúa y publica el resultado **asociado al span evaluado**, de modo que desde una puntuación mala saltas a la traza que la causó.
    """)
    code('''
fig, ax = viz.canvas(12.5, 4.9, (0, 125), (0, 48))
P = viz.PALETTE
b_u = viz.box(ax, 1, 20, 13, 9, "Cliente\\n(ticket)", P["neutral"])
b_a = viz.box(ax, 20, 20, 17, 9, "Agente SupportOps\\n(invoke_agent)", P["traces"], bold=True)
b_r = viz.box(ax, 43, 20, 15, 9, "Respuesta\\n(span chat)", P["traces"])
b_t = viz.box(ax, 43, 36, 15, 8, "Trazas · logs\\n(Tempo / Loki)", P["logs"])
b_s = viz.box(ax, 64, 36, 17, 8, "Muestreo\\npor estratos", P["warn"])
b_j = viz.box(ax, 64, 20, 17, 9, "Juez\\n(reglas / LLM)", P["profiles"], bold=True)
b_e = viz.box(ax, 88, 33, 17, 9, "Evento\\ngen_ai.evaluation.result", P["logs"], fontsize=8)
b_m = viz.box(ax, 88, 20, 17, 9, "Métricas\\nsupportops.eval.*", P["metrics"])
b_v = viz.box(ax, 88, 7, 17, 9, "Span\\nsupportops.evaluate", P["traces"], fontsize=8)
b_g = viz.box(ax, 110, 20, 14, 9, "Grafana\\n+ alertas / SLO", P["dark"], fc="#e5e7eb")
b_f = viz.box(ax, 20, 4, 17, 8, "Feedback del usuario\\n(pulgar ↑/↓, sesgado)", P["warn"], fontsize=8)
for a, b in ((b_u, b_a), (b_a, b_r), (b_s, b_j)):
    viz.arrow(ax, viz.right(a), viz.left(b))
viz.arrow(ax, viz.right(b_r), viz.left(b_j), "", P["neutral"], dashed=True)
viz.arrow(ax, viz.top(b_r), viz.bottom(b_t), "", P["logs"])
viz.arrow(ax, viz.right(b_t), viz.left(b_s))
viz.arrow(ax, viz.right(b_j), viz.left(b_m)); viz.arrow(ax, viz.top(b_j), (88 - 0.3, 36), "", P["logs"], rad=-0.2)
viz.arrow(ax, (b_j[0] + b_j[2], 20), (88 - 0.3, 11.5), "", P["traces"], rad=0.25)
viz.arrow(ax, viz.right(b_m), viz.left(b_g)); viz.arrow(ax, viz.right(b_e), (118, 29.5), "", P["logs"], rad=-0.2)
viz.arrow(ax, viz.right(b_f), (60, 8), "", P["warn"], dashed=True)
ax.text(62, 4.2, "→ feedback_total", fontsize=8, color=P["warn"])
ax.text(1, 45, "La evaluación online NO está en el camino crítico: ocurre DESPUÉS, sobre una muestra", fontsize=10, fontweight="bold")
plt.show()
''')
    md(observe("""
    - El juez **no** está entre el cliente y la respuesta: no añade latencia al usuario. Lee la traza ya terminada (flecha discontinua) y publica **tres señales**: un evento por criterio (logs), una métrica y un span propio.
    - El **muestreo** está antes del juez porque evaluar cuesta dinero (sección 9). La pregunta de diseño central es *qué evaluar*, no *cómo puntuar*.
    - El feedback del usuario es una señal **distinta y barata** (sección 8), pero tiene un sesgo de respuesta: lo miraremos con números.
    """))

    md("""
    ## 1.1 La demostración: calidad invisible para las señales clásicas

    Comparamos, ticket a ticket, lo que ven los paneles clásicos (estado, latencia, coste) con la verdad que conocemos por construcción (el inyector sabe qué respuestas son inventadas).
    """)
    code('''
df = pd.DataFrame(to_rows(TICKETS, RESULTS))
df["bad_truth"] = [c.truth_bad for c in CASES]
df["halluc"] = [not c.truth["grounded"] for c in CASES]
h = df[df.halluc]; ok = df[(~df.halluc) & (df.status == "ok")]
fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
for ax, col_, ttl, unit in ((axes[0], "latency_s", "Latencia por ticket (s)", "s"), (axes[1], "cost_usd", "Coste por ticket (USD mock)", "$"), (axes[2], "output_tokens", "Tokens de salida", "tok")):
    ax.boxplot([ok[col_], h[col_]], tick_labels=["correctas (ok)", "alucinadas"], showfliers=False, patch_artist=True,
               boxprops={"facecolor": viz.PALETTE["light"]}, medianprops={"color": viz.PALETTE["error"]})
    ax.set_title(ttl)
plt.tight_layout(); plt.show()
print("estado de las alucinadas:", h.status.value_counts().to_dict(), "· tickets 'error' entre las alucinadas:", int((h.status == "error").sum()))
print("medianas (correctas vs alucinadas): latencia %.2f vs %.2f s · coste %.6f vs %.6f USD · tokens de salida %d vs %d" % (ok.latency_s.median(), h.latency_s.median(), ok.cost_usd.median(), h.cost_usd.median(), ok.output_tokens.median(), h.output_tokens.median()))
''')
    md(observe("""
    - Las respuestas alucinadas son **más rápidas y baratas** que las correctas (no llaman a ninguna herramienta, contestan al primer intento) y su estado es `ok`. Si optimizas latencia y coste, **premias** al agente que se inventa los datos.
    - Es el patrón de las *regresiones silenciosas* del módulo 15: mejoran los números que miramos y empeoran los que no medimos.
    - Conclusión: hay que **medir el contenido**. El resto del módulo es cómo hacerlo barato, sin sesgo y observable.
    """))

    # ------------------------------------------------------------------------------------------------------------- 2
    md("""
    ---
    # 2 · Teoría: qué evaluar y con qué

    ## 2.1 Criterios (qué significa «bien»)

    | Criterio | Pregunta | Necesita… | En SupportOps |
    |---|---|---|---|
    | **Groundedness / fidelidad** | ¿Cada dato de la respuesta está respaldado por el contexto (resultados de herramientas)? | la respuesta + el contexto | Detecta alucinaciones (importes, referencias, plazos inventados) |
    | **Relevancia** | ¿Responde a lo que se preguntó? | pregunta + respuesta | Pide un dato que ya dio el cliente → falla |
    | **Resolución** | ¿Resuelve o encamina bien el caso? | respuesta + estado | Mensajes de *fallback* no resuelven |
    | **Seguridad / PII** | ¿Revela datos personales ajenos? | respuesta | Regex deterministas: **no** se delega en un LLM |

    «Sin referencia» (*reference-free*): en producción no hay respuesta de oro; se evalúa la respuesta frente a **su contexto y su pregunta**. Las etiquetas de oro viven en el dataset *offline* (módulo 15).

    ## 2.2 Tipos de evaluador

    | Tipo | Coste | Latencia | Fiabilidad | Úsalo para… |
    |---|---|---|---|---|
    | **Reglas / código** (regex, esquemas, comprobaciones numéricas) | ≈ 0 | µs–ms | Exacta en lo que cubre | PII, formato, ids inventados, *todo lo verificable por código* |
    | **Juez LLM** | alto (1 llamada por criterio o por caso) | s | Buena pero **sesgada** (verbosidad, posición, autopreferencia) | Criterios semánticos que el código no ve (tono, relevancia, razonamiento) |
    | **Humano** | muy alto | horas–días | La referencia, con desacuerdo entre anotadores | Calibrar al juez y construir el dataset de oro |
    | **Feedback de usuario** | ≈ 0 | inmediata | Escasa y **sesgada** por quién responde | Señal de alarma y fuente de casos difíciles |

    Regla práctica: **código primero, LLM para lo que el código no puede, humanos para calibrar** (Husain, *Your AI Product Needs Evals*; Yan, *Evaluating the Effectiveness of LLM-Evaluators*).

    ## 2.3 Qué dice la spec de OpenTelemetry (estado real, oct-2026)

    La spec **GenAI semantic conventions** (estado *Development*, repo `open-telemetry/semantic-conventions-genai`) define un **evento** `gen_ai.evaluation.result`:
    «captura el resultado de evaluar la salida de GenAI en calidad, exactitud u otras características; **DEBERÍA** tener como padre el span de la operación evaluada o, si no hay id de span, llevar `gen_ai.response.id`». Atributos:
    `gen_ai.evaluation.name` (*Required*), `gen_ai.evaluation.score.value` (double) y `gen_ai.evaluation.score.label` (*Conditionally Required*), `gen_ai.evaluation.explanation` y `gen_ai.response.id` (*Recommended*), `error.type` (si la evaluación falló).

    **Lo que la spec NO define** (por tanto es convención propia, y así lo marcamos con el prefijo `supportops.`): un span para el evaluador, métricas de calidad, el estrato de muestreo, el feedback del usuario.
    """)
    code('''
snap = json.load(open(ROOT / "04_genai_semconv" / "genai_semconv_snapshot.json"))
print("Instantánea de la spec:", snap["source"]["repo"].split("/")[-1], "· commit", snap["source"]["commit"][:8], "·", snap["source"]["date"], "·", snap["source"]["status"])
rows = [{"atributo": k, "tipo": snap["attributes"][k]["type"], "estabilidad": snap["attributes"][k]["stability"], "descripción": snap["attributes"][k]["brief"][:80]}
        for k in ("gen_ai.evaluation.name", "gen_ai.evaluation.score.value", "gen_ai.evaluation.score.label", "gen_ai.evaluation.explanation", "gen_ai.prompt.name", "gen_ai.prompt.version", "gen_ai.agent.version")]
display(pd.DataFrame(rows).set_index("atributo"))
''')
    md(box("warn", "Cuidado", """
    Todo lo de `gen_ai.evaluation.*` es **Development**: puede cambiar de nombre o forma (hasta hace poco la evaluación se modelaba de otra manera en algunas herramientas). Aísla los nombres
    en **una** función (`build_eval_event`) y valida contra la instantánea de la spec en CI, como hicimos con el linter del módulo 04.
    """))

    # ------------------------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · A mano: un evaluador de groundedness con reglas

    Antes de usar un LLM como juez, veamos hasta dónde llega **el código**. Una alucinación típica de SupportOps es un dato concreto (referencia de reembolso, importe, tracking, plazo) que **no aparece** en lo que devolvieron las herramientas. Eso se puede comprobar con expresiones regulares:

    1. **Extraer afirmaciones** verificables de la respuesta: identificadores (`ORD-…`, `TRK…`, `RF-…`), importes en € y «número + unidad» (años, días, unidades).
    2. **Comprobar** cada una contra el contexto (JSON de las herramientas) y contra lo que dijo el propio cliente.
    3. Si alguna no está respaldada → `groundedness = 0`.
    """)
    code('''
ej = [c for c in CASES if not c.truth["grounded"]][:2] + [c for c in CASES if c.truth["grounded"] and c.n_tool_calls >= 1][:2]
for c in ej:
    print(f"[{'ALUCINADA' if not c.truth['grounded'] else 'correcta  '}] {c.answer[:110]}")
    print("    afirmaciones:", extract_claims(c.answer), "· sin respaldo:", unsupported_claims(c.answer, c.context, c.question))
''')
    code('''
def groundedness_by_hand(case: EvalCase) -> float:
    """1.0 si toda afirmación verificable de la respuesta está respaldada por el contexto o la pregunta; 0.0 si no."""
    return 0.0 if unsupported_claims(case.answer, case.context, case.question) else 1.0

pred_bad = [groundedness_by_hand(c) == 0.0 for c in CASES]
truth_bad = [not c.truth["grounded"] for c in CASES]
cm = confusion(pred_bad, truth_bad)
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in cm.items()})
''')
    md(observe("""
    - Con **cero** llamadas a un LLM el evaluador de reglas encuentra **todas** las alucinaciones (sensibilidad 1,0) y no acusa a ninguna respuesta correcta (especificidad 1,0). En este laboratorio las alucinaciones son datos inventados *comprobables*.
    - **Cuidado con extrapolar**: en la vida real hay alucinaciones que el código no ve (un razonamiento falso sin cifras, una paráfrasis que cambia el significado). Para esas hace falta un juez semántico — y ahí empiezan los errores de medición.
    - Las reglas también se equivocan si olvidas casos: una primera versión ingenua de este evaluador marcaba como inventado el ejemplo de formato `ORD-00000` y el plazo de política «5 días» — los **falsos positivos** de una regla se corrigen añadiendo excepciones, y por eso se mide.
    """))

    # ------------------------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · El juez: anatomía, protocolo y proveedores

    Un **LLM-as-judge** es un LLM al que le pasas la rúbrica, la pregunta, el contexto y la respuesta, y te devuelve puntuaciones estructuradas. Lo importante para observabilidad:

    - Es una **llamada `chat` más**: tiene tokens, latencia, coste, fallos y *rate limits*. Hay que instrumentarla.
    - Su salida es **texto**: puede no ser JSON válido. Un juez que falla en silencio sesga la métrica hacia «todo bien» → se cuenta `supportops.eval.errors`.
    - Es **agnóstico de proveedor**: usa la misma capa `supportops.llm` (`JUDGE_PROVIDER=mock|anthropic|openai|ollama` y `JUDGE_MODEL`); aquí corre el `MockJudge` determinista.
    """)
    code('''
case = next(c for c in CASES if not c.truth["grounded"] and c.n_tool_calls == 0)
prompt = render_judge_prompt(case)
print(prompt)
print("-" * 80, "\\ntokens del prompt del juez ≈", len(prompt) // 4, "· tokens del agente en ese ticket =", next(r.input_tokens for r in RESULTS if r.ticket_id == case.ticket_id))
v = JUDGE.evaluate(case)
for name, s in v.scores.items():
    print(f"{name:13s} {s.value:5.2f} {s.label:5s} {s.explanation}")
print(f"juez: {v.judge_model} · {v.input_tokens} tok in / {v.output_tokens} tok out · latencia simulada {v.latency_s:.2f}s · coste ${v.cost_usd:.5f} (ilustrativo)")
''')
    md("""
    **Contrato de implementación** (`LLMJudge`): enviamos el prompt con `temperature=0`, pedimos solo JSON y lo parseamos de forma tolerante; si no se puede parsear devolvemos un veredicto con `error="parse_error"` en lugar de inventar una nota.
    """)
    code('''
stub = type("StubLLM", (), {"model": "mock-large"})()          # cualquier cliente de supportops.llm vale; aquí solo probamos el parseo
lj = LLMJudge(stub)
good = lj.parse("T-1", 'Claro: {"groundedness": {"score": 0.9, "explanation": "ok"}, "relevance": {"score": 1}, "resolution": {"score": 1}, "pii_safety": {"score": 1}}')
bad = lj.parse("T-2", "Lo siento, no puedo evaluar esto.")
print("válido  ->", good.error, good.passed, {k: v.value for k, v in good.scores.items()})
print("inválido->", bad.error, bad.passed, bad.scores)
''')
    md(observe("""
    - El prompt del juez es **más largo que la conversación del agente** (lleva rúbrica + contexto + respuesta): el juez cuesta más por caso que el agente. Lo cuantificamos en la sección 9.
    - El parseo defensivo es parte de la observabilidad del juez: sin él, un cambio de formato del modelo juez parece «de repente todo va perfecto».
    - **Privacidad**: lo que mandas al juez (a menudo un tercero) incluye pregunta, contexto y respuesta, con su PII. `scrub_pii()` redacta emails, teléfonos y tarjetas antes de enviar; y la detección de PII se hace con regex locales, no con el LLM.
    """))

    # ------------------------------------------------------------------------------------------------------------- 5
    md("""
    ---
    # 5 · Los errores del juez: medirlos, no ignorarlos

    El `MockJudge` se equivoca a propósito de cuatro maneras (las que documenta la literatura sobre jueces LLM; Zheng et al., 2023): **falsos negativos** (deja pasar una alucinación), **falsos positivos** (acusa a una respuesta correcta),
    **sesgo de verbosidad** (puntúa mejor lo largo) y **sesgo de posición** (en comparaciones por pares prefiere la primera respuesta). Con un juez real hay que *medir* estos errores con un conjunto de calibración etiquetado por humanos; aquí lo etiquetamos con la verdad del inyector.

    ## 5.1 Sensibilidad, especificidad y qué le pasa a tu métrica
    """)
    code('''
vs_rule = [RULE.evaluate(c) for c in CASES]; vs_mock = [JUDGE.evaluate(c) for c in CASES]
fail = lambda vs: [v.scores["groundedness"].label == "fail" for v in vs]
cm_r, cm_m = confusion(fail(vs_rule), truth_bad), confusion(fail(vs_mock), truth_bad)
obs_rate = sum(fail(vs_mock)) / len(CASES); true_rate = sum(truth_bad) / len(CASES)
fixed = rogan_gladen(obs_rate, cm_m["sensitivity"], cm_m["specificity"])
print(f"verdad: {true_rate:.2%} alucinadas · observado con el juez: {obs_rate:.2%} · corregido (Rogan–Gladen): {fixed:.2%}")
print(f"juez imperfecto -> sensibilidad {cm_m['sensitivity']:.2f} · especificidad {cm_m['specificity']:.3f} · precisión {cm_m['precision']:.2f}")
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
for ax, cm_, ttl in ((axes[0], cm_r, "Juez de reglas"), (axes[1], cm_m, "Juez imperfecto (mock)")):
    M = np.array([[cm_["tn"], cm_["fp"]], [cm_["fn"], cm_["tp"]]])
    ax.imshow(M, cmap="Blues"); ax.set_xticks([0, 1], ["dice OK", "dice FALLA"]); ax.set_yticks([0, 1], ["era buena", "era alucinada"]); ax.set_title(ttl); ax.grid(False)
    for (i, j), val in np.ndenumerate(M): ax.text(j, i, int(val), ha="center", va="center", color="white" if val > M.max() / 2 else "black", fontsize=13)
axes[2].bar(["verdad", "observado\\n(juez)", "corregido\\n(Rogan–Gladen)"], [true_rate, obs_rate, fixed], color=[viz.PALETTE["ok"], viz.PALETTE["warn"], viz.PALETTE["traces"]])
axes[2].set_ylabel("tasa de alucinación"); axes[2].set_title("Tasa de alucinación")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El juez imperfecto **deja pasar ~10 %** de las alucinaciones y **acusa ~1–2 %** de respuestas correctas. Como las alucinaciones son raras (~7 %), esos falsos positivos son una fracción grande de las alarmas: la **precisión** del juez es mucho menor que su especificidad (la paradoja de la prevalencia baja).
    - La tasa observada **no es** la tasa real. Con sensibilidad *Se* y especificidad *Sp* medidas en un conjunto de calibración, la corrección de Rogan–Gladen recupera la prevalencia: \\( \\hat\\pi = \\frac{p_{obs} + Sp - 1}{Se + Sp - 1} \\).
    - Esto exige una **muestra etiquetada por humanos** (aquí, la verdad del inyector). Con 100–200 casos etiquetados ya puedes estimar *Se* y *Sp* con intervalo de confianza (`wilson_interval`).
    """))
    md("## 5.2 Sesgo de verbosidad: ¿premia el juez lo largo?")
    code('''
PAD = " Gracias por contactar con SupportOps; estamos encantados de ayudarle con todo lo que necesite y quedamos a su entera disposición para cualquier otra consulta."
sample = [c for c in CASES if c.truth["grounded"] and c.status == "ok" and RULE.relevance(c).value <= 0.7][:200]       # respuestas con margen de mejora (sin techo de 1,0)
print(len(sample), "respuestas correctas pero con relevancia mejorable")
d = []
for k in (0, 1, 2, 3):
    vals = [JUDGE.evaluate(dataclasses.replace(c, answer=c.answer + PAD * k)).scores["relevance"].value for c in sample]
    d.append((k, float(np.mean(vals)), float(np.std(vals) / math.sqrt(len(vals)))))
base = d[0][1]
fig, ax = plt.subplots(figsize=(6.5, 3.6))
ax.errorbar([x[0] * len(PAD) for x in d], [x[1] for x in d], yerr=[1.96 * x[2] for x in d], marker="o", color=viz.PALETTE["profiles"], capsize=4)
ax.set_xlabel("caracteres de relleno añadidos (sin información nueva)"); ax.set_ylabel("puntuación media de relevancia"); ax.set_title("El juez premia el relleno")
plt.tight_layout(); plt.show()
print({k: round(m, 3) for k, m, _ in d})
''')
    md(observe("""
    - Con relleno sin información nueva, la puntuación de relevancia **sube** con cada bloque de relleno (con la muestra rápida de `FAST_DEV_RUN`, solo ≈ 14 casos, de ≈ 0,6 a ≈ 0,8; con `FAST_DEV_RUN=False` la muestra llega a 200 casos y el intervalo de error es mucho más estrecho): el juez confunde longitud con calidad. Es el sesgo de verbosidad descrito por Zheng et al. (2023) para jueces LLM.
    - Consecuencia operativa: si un cambio de prompt hace al agente más hablador, tu «calidad» sube **sin que el cliente esté mejor atendido**. Defensas: rúbricas que penalicen el relleno, normalizar por longitud, y — sobre todo — **sondas de sesgo** como esta, ejecutadas cada vez que cambias de juez.
    """))
    md("## 5.3 Sesgo de posición en comparaciones por pares")
    code('''
pairs = [(c.question, c.answer) for c in CASES if c.truth["grounded"] and c.status == "ok" and c.n_tool_calls][:120]
same = sum(JUDGE.compare(q, a, a + ".", key=str(i)) == "A" for i, (q, a) in enumerate(pairs))                       # dos respuestas prácticamente IGUALES
swap_consistent = sum((JUDGE.compare(q, a, a + ".", key=str(i)) == "A") != (JUDGE.compare(q, a + ".", a, key=str(i)) == "A") for i, (q, a) in enumerate(pairs))
print(f"con respuestas equivalentes elige A en {same / len(pairs):.0%} de los casos · elige la MISMA respuesta en ambos órdenes: {swap_consistent / len(pairs):.0%} (eligiendo al azar entre equivalentes saldría ≈ 50 %)")
''')
    md(observe("""
    - Ante dos respuestas equivalentes un juez sin sesgo diría «empate» o elegiría al azar (≈ 50 % de «A» en cada orden). Este elige «A» en torno al 60 % de las veces **en ambos órdenes**, así que su veredicto casi nunca es consistente al permutar. La mitigación estándar: evaluar **ambos órdenes** y contar solo los veredictos consistentes (empate si discrepan).
    - Para criterios con respuesta objetiva (¿está respaldado el dato?) prefiere **puntuación directa** a comparación por pares: elimina este sesgo de raíz.
    """))

    # ------------------------------------------------------------------------------------------------------------- 6
    md(r"""
    ---
    # 6 · Muestreo para evaluar: qué evaluar y cómo no sesgar la métrica

    Evaluar todo es caro (sección 9). Muestrear es inevitable, pero **un muestreo inteligente sesga la métrica** si no lo corriges:

    - **Uniforme** (`RateSampler`): sin sesgo, pero desperdicia presupuesto en tickets aburridos y casi no ve los raros (errores, escalados).
    - **Estratificado** (`StratifiedSampler`): evalúa casi todo lo raro e importante (errores 100 %, escalados 50 %, premium 25 %, resto 10 %). Mucho más informativo… y la tasa de «bien» de la **muestra** es engañosa porque sobrerrepresenta los tickets difíciles.

    📐 **Estimador post-estratificado.** Con estratos \(s\), población \(N_s\), evaluados \(n_s\) y buenos \(k_s\):
    $$\hat p = \sum_s \frac{N_s}{N}\,\frac{k_s}{n_s}, \qquad \widehat{\mathrm{Var}}(\hat p)=\sum_s \Big(\frac{N_s}{N}\Big)^2\frac{\hat p_s(1-\hat p_s)}{n_s-1}\Big(1-\frac{n_s}{N_s}\Big)$$
    Cada estrato se pondera por su **tamaño en la población** (`supportops.eval.population` cuenta *todas* las peticiones, evaluadas o no), no por cuántos se evaluaron. Es lo que hace la consulta de PromQL del panel.
    """)
    code('''
def run_sampler(sampler, judge=RULE):
    ev = OnlineEvaluator(judge, sampler)
    for c in CASES: ev.submit(c)
    ev.run_pending()
    return ev
true_full = float(np.mean([RULE.evaluate(c).passed for c in CASES]))          # lo que daría evaluar TODO con el juez de reglas
rows = []
for s in range(40):
    e1 = run_sampler(StratifiedSampler(salt=f"s{s}")).estimate_quality()
    e2 = run_sampler(RateSampler(0.15, salt=f"s{s}")).estimate_quality()
    rows.append({"estratificado ingenuo": e1["naive"], "estratificado post-estrat.": e1["estimate"], "uniforme 15 %": e2["naive"], "n_estrat": e1["n_evaluated"], "n_unif": e2["n_evaluated"]})
R = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(8, 4))
ax.boxplot([R[c] for c in ("estratificado ingenuo", "estratificado post-estrat.", "uniforme 15 %")], tick_labels=["estratificado\\n(media de la muestra)", "estratificado\\n(post-estratificado)", "uniforme 15 %"], patch_artist=True,
           boxprops={"facecolor": viz.PALETTE["light"]}, medianprops={"color": viz.PALETTE["error"]})
ax.axhline(true_full, color=viz.PALETTE["ok"], ls="--", label=f"verdad (evaluando todo) = {true_full:.3f}"); ax.set_ylabel("tasa de calidad OK estimada"); ax.legend(); ax.set_title("40 repeticiones del muestreo con semillas distintas")
plt.tight_layout(); plt.show()
print(R.mean().round(3).to_dict(), "· desviación típica:", R.std().round(3).to_dict())
''')
    md(observe("""
    - La media **ingenua** del muestreo estratificado queda muy por debajo de la verdad: sobrerrepresenta errores y escalados. Si alertaras sobre ella verías una «calidad baja» permanente que es un artefacto del muestreo.
    - El estimador **post-estratificado** cae sobre la verdad (caja centrada en la línea verde) con una dispersión similar a la del muestreo uniforme (≈ 3 puntos), y además **ve los estratos raros**: los errores se evalúan todos (100 %), cosa que un 15 % uniforme no garantiza. Cuesta más evaluaciones (≈ 150 frente a ≈ 90 en el laboratorio), por eso la sección 9.2 pone precio.
    - Regla de oro: **cada muestra lleva su probabilidad de inclusión** (aquí, el estrato). Si no la guardas en la telemetría no podrás corregir después.
    """))
    code('''
n_pop = {s: v for s, v in run_sampler(StratifiedSampler()).population.items()}
print("población por estrato:", n_pop)
est = run_sampler(StratifiedSampler()).estimate_quality()
lo, hi = est["estimate"] - 1.96 * est["se"], est["estimate"] + 1.96 * est["se"]
print(f"calidad estimada {est['estimate']:.3f}  IC95 [{lo:.3f}, {hi:.3f}]  (n evaluados = {est['n_evaluated']} de {est['n_population']})")
print("n necesario para ±3 puntos con p≈0,85:", required_sample_size(0.85, 0.03), "· para ±1 punto:", required_sample_size(0.85, 0.01))
''')

    # ------------------------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Hacerlo observable: evaluación como telemetría OpenTelemetry

    Diseño (todo verificado en la sección 8 con el stack real):

    | Señal | Qué | Por qué así |
    |---|---|---|
    | **Evento** `gen_ai.evaluation.result` (log OTel con `event_name`) | uno por criterio, con `name`, `score.value`, `score.label`, `explanation`, `gen_ai.response.id` | La spec pide que cuelgue del **span evaluado** (`trace_id`/`span_id` de la llamada `chat` que produjo la respuesta) |
    | **Span** `supportops.evaluate` + hijo `chat <juez>` | el trabajo del juez, con tokens y duración | Es **otra traza** (la evaluación es asíncrona, no es hija de la petición) **enlazada** (*span link*) al span evaluado |
    | **Métricas** `supportops.eval.*` | `population`, `sampled`, `results{criterio, etiqueta, estrato, versión}`, `score`, `cost`, `duration` | SLIs y paneles baratos; etiquetas acotadas (nunca `ticket_id`) |
    | **Servicio propio** `supportops-evaluator` | evaluador y agente separados | El coste y los tokens del juez no se cuelan en el coste del agente (regla de las hojas `chat`) |
    """)
    code('''
tel_a = setup_telemetry("supportops-agent", mode="memory", set_global=False)
tel_e = setup_telemetry("supportops-evaluator", mode="memory", set_global=False)
ev = OnlineEvaluator(JUDGE, StratifiedSampler(), tel_e)
col2 = CaseCollector(on_case=ev.submit)                         # al terminar cada ticket, el evaluador decide si lo muestrea
agent2 = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(tel_a), col2))      # el de trazas PRIMERO: así el span está activo cuando col2 lee los ids
res2 = run_tickets(agent2, generate_tickets(120, seed=SEED, fault_rates=FAULTS))
ev.run_pending(); tel_a.force_flush(); tel_e.force_flush()
print(f"{len(res2)} tickets · {len(ev.records)} evaluados · spans del agente {len(tel_a.span_records())} · spans del evaluador {len(tel_e.span_records())}")
''')
    code('''
from supportops.regression import event_records
EVENTS = event_records(tel_e)
agent_spans = {s["span_id"]: s for s in tel_a.span_records()}
e = EVENTS[0]
print("evento:", json.dumps({k: v for k, v in e["attributes"].items()}, ensure_ascii=False, indent=1))
tgt = agent_spans[e["span_id"]]
print("\\nel evento cuelga del span:", tgt["name"], "· trace_id coincide:", tgt["trace_id"] == e["trace_id"])
''')
    md("""
    ### Validación contra la spec

    Escribimos el validador una vez y lo ejecutamos sobre **todos** los eventos: ¿existen los atributos en la instantánea?, ¿son del tipo correcto?, ¿están los *Required*?
    """)
    code('''
def validate_eval_event(attrs: dict) -> list[str]:
    """Problemas de un evento gen_ai.evaluation.result frente a la instantánea de la spec."""
    probs = []
    if "gen_ai.evaluation.name" not in attrs: probs.append("falta gen_ai.evaluation.name (Required)")
    if "gen_ai.evaluation.score.value" not in attrs and "gen_ai.evaluation.score.label" not in attrs: probs.append("falta score.value o score.label")
    for k, v in attrs.items():
        if k.startswith("gen_ai."):
            if k not in snap["attributes"]: probs.append(f"{k} no existe en la spec")
            elif snap["attributes"][k]["type"] == "double" and not isinstance(v, float): probs.append(f"{k} debe ser double")
            elif snap["attributes"][k]["type"] == "string" and not isinstance(v, str): probs.append(f"{k} debe ser string")
    return probs
bad = [(i, validate_eval_event(x["attributes"])) for i, x in enumerate(EVENTS) if validate_eval_event(x["attributes"])]
print(f"{len(EVENTS)} eventos validados · con problemas: {len(bad)}")
print("un evento sin name ->", validate_eval_event({"gen_ai.evaluation.score.value": 1.0}), "· con un atributo inventado ->", validate_eval_event({"gen_ai.evaluation.name": "x", "gen_ai.evaluation.score": 1.0, "gen_ai.evaluation.score.value": 1.0}))
''')
    code('''
ev_spans = [s for s in tel_e.span_records() if s["name"] == "supportops.evaluate"]
one = ev_spans[0]
trace_spans = [s for s in tel_e.span_records() if s["trace_id"] == one["trace_id"]]
fig, ax = plt.subplots(figsize=(10, 2.4)); viz.waterfall(trace_spans, ax=ax, title="Traza de UNA evaluación (servicio supportops-evaluator)"); plt.tight_layout(); plt.show()
print("atributos del span evaluate:", {k: v for k, v in one["attributes"].items() if k.startswith("supportops.eval")})
''')
    md(observe("""
    - La cascada tiene dos spans: `supportops.evaluate` (el trabajo de evaluar) y su hijo `chat mock-large` (la llamada al juez, con tokens). Su duración es la **latencia del juez**, no la del usuario: la evaluación no está en el camino crítico.
    - Cada evento apunta (`trace_id`, `span_id`) al span `chat` del **agente** que produjo la respuesta evaluada: en Grafana, desde una puntuación mala abres la traza original con un clic.
    - En el span `supportops.evaluate` hay un *link* al span evaluado (no es su hijo: se evalúa minutos después). Un trace con la evaluación como hijo alargaría artificialmente la duración de la petición.
    """))

    # ------------------------------------------------------------------------------------------------------------- 8
    md("""
    ---
    # 8 · Con el stack real: Tempo, Loki, Prometheus y Grafana

    Con el stack (`docker compose --profile core --profile metrics up -d`) enviamos **60 s de tráfico en tiempo real** por `LivePipeline` (agente con métricas del módulo 09 + evaluador) y consultamos cada backend.
    Sin stack esta celda se salta (modo degradado) y las explicaciones siguen valiendo.
    """)
    code('''
from supportops.regression import LivePipeline
from supportops.slo import BASELINE_FAULTS
LIVE_S = 45 if FAST_DEV_RUN else 120
if LIVE:
    lp = LivePipeline(("v1",), mode="otlp", sampler=StratifiedSampler(), metric_interval_s=5)
    live_tk = generate_tickets(int(LIVE_S * 3), seed=SEED, duration_s=LIVE_S, fault_rates={**BASELINE_FAULTS, "hallucination": 0.08}, start_s=0.0)
    t0 = time.time(); lp.run_live(live_tk, LIVE_S); lp.close()
    print(f"enviados {len(live_tk)} tickets en {time.time() - t0:.0f}s · evaluados {len(lp.ev.records)} · estimación de calidad {lp.ev.estimate_quality()['estimate']:.3f}")
    time.sleep(12)                       # métricas: scrape de 15 s; trazas: ≈ 15-20 s hasta ser buscables
else:
    print("Modo degradado: sin Collector no se envía nada. Levanta el stack con:", STACK.command)
''')
    code('''
if LIVE:
    from supportops.otel_metrics import prom_instant
    qs = {"calidad groundedness (5 m)": 'sum(rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m])) / sum(rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))',
          "cobertura: evaluadas/pobl.": "sum(increase(supportops_eval_sampled_total[5m])) / sum(increase(supportops_eval_population_total[5m]))",
          "coste del juez (USD, 5 m)": "sum(increase(supportops_eval_cost_USD_total[5m]))"}
    for k, q in qs.items():
        r = prom_instant(q); print(f"{k:32s}", [round(x['value'], 4) for x in r if x['value'] is not None] if r else "sin datos aún")
    ta = backends.tempo_search('{ resource.service.name = "supportops-evaluator" && name = "supportops.evaluate" }', minutes=10, limit=5)
    print("Tempo · trazas de evaluación:", len(ta.get("traces", [])) if isinstance(ta, dict) else ta)
    lg = backends.loki_query('{service_name="supportops-evaluator"} | gen_ai_evaluation_name="groundedness" | gen_ai_evaluation_score_label="fail"', minutes=10, limit=3)
    print("Loki · evaluaciones fallidas de groundedness:", len(lg), "líneas · primera:", str(lg[0])[:260] if lg else "(aún ninguna)")
''')
    md(box("exp", "Experimento medido (oct-2026, Loki 3.7.8)", """
    El **nombre del evento** (`event_name`) **no llega** a Loki como etiqueta ni como metadato estructurado en la ruta OTLP: el cuerpo (`groundedness=fail`) y los atributos `gen_ai_evaluation_*`
    sí. Por eso las consultas filtran por `gen_ai_evaluation_name` y no por el nombre del evento, y por eso conviene poner un **cuerpo legible** en el evento. Los puntos de los atributos se convierten en `_`.
    El `trace_id`/`span_id` del evento son los del **span evaluado** (comprobado).
    """))
    md("""
    ### El dashboard `14-calidad-online` (provisionado como código)

    `stack/grafana/dashboards/14-calidad-online.json` (uid `calidad-online`) lo genera este mismo builder con `supportops.dashkit`. Paneles y consultas clave:

    | Panel | Consulta |
    |---|---|
    | Calidad estimada (post-estratificada) | `sum(rate(population)·pass/evaluados por estrato)/sum(rate(population))` — la fórmula de la sección 6 en PromQL |
    | Calidad por versión | `sum by (gen_ai_agent_version)(rate(results{pass}))/sum by (...)(rate(results))` |
    | Cobertura de la evaluación | `increase(sampled)/increase(population)` por estrato |
    | Distribución de puntuaciones | heatmap de `supportops_eval_score_bucket` |
    | Feedback +/− | `supportops_feedback_total` por valoración |
    | Coste del juez frente al del agente | `eval_cost / llm_cost` |
    | Evaluaciones fallidas | LogQL `{service_name="supportops-evaluator"} \\| gen_ai_evaluation_score_label="fail"` |
    | Trazas evaluadas con fallo | TraceQL `{ name="supportops.evaluate" && span.supportops.eval.passed=false }` |

    **Qué debes ver en Grafana:** un panel «Calidad estimada» estable alrededor del 0,85–0,95, que baja cuando inyectas alucinaciones; la tabla de logs lista las evaluaciones fallidas y un clic en `trace_id` abre la traza del agente.
    """)

    # ------------------------------------------------------------------------------------------------------------- 9
    md("""
    ---
    # 9 · Feedback de usuario y coste de evaluar

    ## 9.1 El feedback explícito (+/−) es barato… y sesgado

    En SupportOps el widget de chat permite valorar la respuesta. **No hay convención OTel** para feedback de usuario (a fecha de hoy): se modela como métrica de baja cardinalidad (`supportops.feedback{rating}`) y, si se guarda el texto, como log con el `trace_id` de la traza valorada.
    Aquí lo **simulamos** (sintético): quien tuvo una mala experiencia responde ~5× más que quien no.
    """)
    code('''
FB = simulate_feedback(CASES, seed=SEED)
by = {f.ticket_id: f.rating for f in FB}
bad_t = [c for c in CASES if c.truth_bad]; good_t = [c for c in CASES if not c.truth_bad]
resp_bad = np.mean([c.ticket_id in by for c in bad_t]); resp_good = np.mean([c.ticket_id in by for c in good_t])
down_share = np.mean([f.rating < 0 for f in FB])
print(f"{len(FB)} valoraciones de {len(CASES)} tickets ({len(FB) / len(CASES):.1%}) · responden el {resp_bad:.0%} de los malos y el {resp_good:.1%} de los buenos")
print(f"− entre las valoraciones: {down_share:.0%}  ·  tickets realmente malos: {len(bad_t) / len(CASES):.0%}  ->  el feedback SOBRESTIMA el problema {down_share / (len(bad_t) / len(CASES)):.1f}×")
# ¿cuánta de la alucinación real captura el feedback frente al juez?
hall = [c for c in CASES if not c.truth["grounded"]]
print(f"alucinaciones con −: {np.mean([by.get(c.ticket_id) == -1 for c in hall]):.0%} · detectadas por el juez imperfecto: {np.mean([JUDGE.evaluate(c).scores['groundedness'].label == 'fail' for c in hall]):.0%}")
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.bar(["tickets malos\\n(verdad)", "− entre\\nvaloraciones", "alucinaciones\\ncon −", "alucinaciones\\ndetectadas (juez)"], [len(bad_t) / len(CASES), down_share, np.mean([by.get(c.ticket_id) == -1 for c in hall]), np.mean([JUDGE.evaluate(c).scores['groundedness'].label == 'fail' for c in hall])],
       color=[viz.PALETTE["ok"], viz.PALETTE["warn"], viz.PALETTE["warn"], viz.PALETTE["profiles"]]); ax.set_ylim(0, 1); ax.set_title("Feedback vs juez frente a la verdad")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Solo ≈ 8 % de los tickets recibe valoración y el porcentaje de valoraciones negativas **sobrestima** la tasa real de problemas ≈ 3×: responden los enfadados (sesgo de autoselección).
    - Y lo importante: el feedback **no ve** casi ninguna alucinación (≈ 12 % reciben un negativo; el cliente que recibe un dato falso verosímil no protesta hasta que le falla). El juez imperfecto ve ≈ 90 %.
    - Uso correcto del feedback: **disparador** (un − fuerza la evaluación del ticket y entra en el dataset de regresión, módulo 15) y señal de tendencia, **no** estimador de la calidad poblacional.
    """))

    md("""
    ## 9.2 El coste de evaluar: ¿cuánto muestrear?

    Cada evaluación es una llamada a un modelo (el prompt incluye rúbrica + contexto + respuesta). Con los precios **ilustrativos** del mock (juez `mock-large`, agente `mock-small`):
    """)
    code('''
ev_all = run_sampler(RateSampler(1.0), judge=JUDGE)
judge_per = np.mean([r.verdict.cost_usd for r in ev_all.records]); agent_per = np.mean([r.case.cost_usd for r in ev_all.records])
print(f"coste medio por ticket: agente ${agent_per:.6f} · juez ${judge_per:.6f} -> evaluar UN ticket cuesta {judge_per / agent_per:.1f}× lo que cuesta atenderlo")
rates = np.array([0.01, 0.02, 0.05, 0.10, 0.20, 0.50, 1.0]); p = 0.85; N_DAY = 20000
n_eval = rates * N_DAY
cost_day = n_eval * judge_per; width = 1.96 * np.sqrt(p * (1 - p) / n_eval)
fig, ax = plt.subplots(figsize=(8, 4)); ax2 = ax.twinx()
ax.plot(rates * 100, cost_day / (N_DAY * agent_per) * 100, "o-", color=viz.PALETTE["metrics"], label="coste del juez / coste del agente (%)"); ax.set_xlabel("% de tickets evaluados"); ax.set_ylabel("sobrecoste sobre el agente (%)", color=viz.PALETTE["metrics"])
ax2.plot(rates * 100, width * 100, "s--", color=viz.PALETTE["traces"], label="± puntos de error (IC95) de la calidad"); ax2.set_ylabel("± puntos de error del IC95", color=viz.PALETTE["traces"]); ax2.grid(False)
ax.set_xscale("log"); ax.set_title("Coste vs precisión según la tasa de muestreo (20 000 tickets/día)")
plt.tight_layout(); plt.show()
print({f"{r:.0%}": f"{c / (N_DAY * agent_per):.0%} de sobrecoste, ±{w * 100:.1f} pt" for r, c, w in zip(rates, cost_day, width)})
''')
    md(observe("""
    - Evaluar un ticket con un juez grande cuesta **~9× más** que atenderlo con el modelo pequeño. Evaluarlo todo multiplicaría la factura de IA por ≈ 10: inviable.
    - La precisión mejora con la **raíz** de n: del 1 % al 10 % de muestreo el error baja de ±~5 a ±~1,6 puntos; pasar del 10 % al 100 % solo lo baja de ±1,6 a ±0,5 por 10× el dinero. **El codo de la curva está en torno al 5–10 %.**
    - Palancas para abaratar sin perder señal: (1) **cascada** (reglas primero, LLM solo en lo dudoso), (2) juez **más pequeño** calibrado contra el grande, (3) un solo prompt con **todos los criterios**, (4) muestrear por estratos de valor, (5) *caching* de la rúbrica (módulo 13).
    """))

    # ------------------------------------------------------------------------------------------------------------- 10
    md("""
    ---
    # 10 · 🏭 En producción

    - **Evaluación como consumidor de trazas.** Las plataformas de observabilidad de LLMs (Langfuse, LangSmith, Arize Phoenix y otras) comparten el patrón: puntuaciones ligadas a una traza/span, evaluadores asíncronos sobre una muestra y datasets creados desde producción. El valor del enfoque OTel es que las puntuaciones viven en **los mismos backends** que el resto de señales y se correlacionan con ellas.
    - **Dónde se ejecuta el juez.** Servicio independiente con su propia cuota, cola y escalado; si el proveedor del juez cae, la *evaluación* se retrasa, el usuario no se entera. Backpressure: descarta evaluaciones antiguas antes que bloquear.
    - **Versiona todo lo que influye en la nota**: versión del prompt del juez, del modelo juez y de la rúbrica (`supportops.eval.judge`). Cambiar el juez rompe la comparabilidad histórica de la serie.
    - **Calibración continua.** Muestra semanalmente casos para revisión humana, recalcula sensibilidad/especificidad y detecta *drift del juez* (un proveedor cambia el modelo por debajo).
    - **Cardinalidad.** `criterio × etiqueta × estrato × versión` son unas decenas de series: seguro. `ticket_id`, `customer_id`, el texto de la explicación **nunca** como etiqueta (van en el log/span).
    """)

    md("""
    ---
    # 11 · 🧠 Secretos de la élite

    1. **La métrica de la muestra no es la métrica de la población.** Cualquier muestreo no uniforme (errores, premium, −) exige guardar la probabilidad de inclusión y **post-estratificar** (sección 6); alertar sobre la media ingenua crea una «calidad baja» permanente que es un artefacto. Mide `population` para *todas* las peticiones, no solo las evaluadas.
    2. **Corrige la tasa con la sensibilidad y la especificidad del juez** (Rogan & Gladen, 1978): con prevalencia baja, un 2 % de falsos positivos puede ser la mayoría de las alarmas. Una nota sin el error del juez no es una medida, es una opinión.
    3. **Sondas de sesgo por cada cambio de juez.** Relleno (verbosidad), permutación de orden (posición) y, si juez y agente son de la misma familia, autopreferencia (Panickssery et al., 2024). Es un test de regresión *del evaluador*, con la misma disciplina que el del agente.
    4. **Código antes que LLM para todo lo verificable.** PII, ids, importes y formatos se comprueban con regex/esquemas: coste ≈ 0, reproducibles y sin enviar datos personales a un tercero. El juez LLM se reserva para lo semántico.
    5. **El evaluador es otro servicio y su traza va enlazada, no anidada.** Así la duración de la petición no incluye la evaluación, el coste del juez no contamina el coste del agente (la regla de «solo hojas `chat`» se aplica *por servicio*) y se puede escalar/limitar por separado.
    6. **Muestreo determinista por hash del id**, no `random()`: la decisión es reproducible, idéntica en todas las réplicas y estable ante reintentos; puedes re-evaluar *exactamente* la misma muestra con un juez nuevo.
    7. **Cuenta los fallos del juez.** `parse_error`, timeouts y *rate limits* del juez deben ser una métrica y una alerta: si no, la calidad «mejora» el día que el juez se rompe porque solo puntúas lo que sí parsea.
    8. **No alertes sobre una nota individual ni sobre una media sin intervalo.** Alerta sobre una **tasa** en una ventana con suficiente n (módulo 16: `min_events`) y comprueba que el IC no solape el umbral.
    9. **El feedback de usuario es un disparador, no un estimador**: sesgo de autoselección (responden los enfadados) y ceguera ante errores verosímiles.
    """)

    md("""
    ---
    # 12 · ⚠️ Errores comunes

    - Evaluar con el **mismo modelo** (o familia) que genera la respuesta y no medir la autopreferencia.
    - Poner la nota del juez como etiqueta de una métrica (alta cardinalidad) en lugar de histograma + etiqueta pass/fail.
    - Usar el **puntaje medio** de una escala de 1–10: poco fiable e inestable; prefiere pass/fail por criterio con rúbrica concreta, o escalas pequeñas con ejemplos.
    - Mandar la conversación completa (con PII) al juez de un tercero sin redactar.
    - Cambiar el prompt del juez sin versionarlo ni recalibrar: la serie histórica pierde sentido.
    - Evaluar *dentro* del camino de la petición (latencia para el usuario) cuando no hace falta bloquear la respuesta.
    - Confundir **correlación con la satisfacción** con **corrección**: una respuesta amable y falsa puede puntuar bien.
    """)

    md("""
    ---
    # 13 · Autoevaluación
    """)
    md(details("1 · (Cálculo) Con una sensibilidad de 0,90 y una especificidad de 0,98, el juez marca el 11 % de las respuestas como alucinadas. ¿Cuál es la tasa real de alucinación?",
               "Rogan–Gladen: \\( (0{,}11 + 0{,}98 - 1)/(0{,}90 + 0{,}98 - 1) = 0{,}09/0{,}88 \\approx 0{,}102 \\). La tasa real es ≈ **10,2 %**, no 11 %: parte de las alarmas son falsos positivos y se escapan alucinaciones, y el efecto neto depende de la prevalencia."))
    md(details("2 · (Cálculo) Población: base 8 000 (evaluados 400, 360 buenos), error 200 (evaluados 200, 100 buenos). Estima la tasa de calidad OK poblacional y compárala con la media de la muestra.",
               "Post-estratificado: \\( (8000/8200)\\cdot 0{,}9 + (200/8200)\\cdot 0{,}5 = 0{,}878 + 0{,}0122 \\approx 0{,}890 \\). La media ingenua de la muestra es \\( (360+100)/600 = 0{,}767 \\): subestima 12 puntos porque el estrato «error» está sobrerrepresentado (200 de 600 evaluados, pero solo 2,4 % de la población)."))
    md(details("3 · (Diagnóstico) Tras cambiar el modelo juez, la «calidad» de SupportOps sube 4 puntos de un día para otro sin ningún despliegue del agente. ¿Qué sospechas y cómo lo compruebas?",
               "Cambió la **vara de medir**, no el agente: otro juez con distinta sensibilidad/especificidad o sesgo (p. ej. más indulgente con respuestas largas). Comprueba (a) `supportops.eval.judge`/versión en las métricas, (b) re-evalúa una muestra congelada con ambos jueces (comparación pareada), (c) recalcula sensibilidad/especificidad con la muestra etiquetada, (d) mira `parse_error`. Nunca compares series de jueces distintos sin calibrar."))
    md(details("4 · (Diagnóstico) El panel de calidad muestra 100 % durante una hora; luego se recupera «de golpe» a 94 %. ¿Qué mirarías antes de celebrar?",
               "Que el juez no estuviera caído: `supportops.eval.errors`/`parse_error`, la métrica `sampled` frente a `results` (¿se evaluó algo?), la cobertura y el volumen `n` por ventana. Un 100 % con n≈0 o con el juez fallando es un **falso verde**. Por eso el panel de calidad lleva siempre al lado la cobertura y el nº de evaluaciones."))
    md(details("5 · (Transferencia) Tu equipo de soporte humano ya etiqueta 50 tickets a la semana. ¿Cómo los usas para mantener sano el sistema de evaluación?",
               "Como **conjunto de calibración**: cada semana, el juez evalúa esos 50 y se recalculan sensibilidad/especificidad con su IC (Wilson); si caen por debajo de un umbral se bloquea el uso del juez para decisiones. También como semilla del dataset de oro del módulo 15, y para medir el desacuerdo entre anotadores (el techo de fiabilidad del juez)."))
    md(details("6 · (Transferencia) ¿Cómo adaptarías este diseño a un agente que genera código o consultas SQL?",
               "Priorizando evaluadores **ejecutables**: compilar/ejecutar en un sandbox, comprobar el plan, comparar resultados con una consulta de referencia. El juez LLM queda para estilo y seguridad. El mismo esqueleto: evento de evaluación ligado al span, muestreo por estratos (consultas lentas, que tocan tablas sensibles) y métricas de pass-rate."))
    md(details("7 · ¿Por qué el evento de evaluación lleva el `trace_id`/`span_id` del span evaluado y no los del span `supportops.evaluate`?",
               "Porque la spec pide que el evento cuelgue del span de la operación **evaluada**: así una consulta por `trace_id` en Loki devuelve, junto a los logs del agente, sus puntuaciones, y desde la traza del agente se llega a ellas. El span del evaluador tiene su propia traza y un *link* al evaluado."))

    md("""
    ---
    # 14 · Referencias

    - OpenTelemetry, *Semantic conventions for generative AI* (repo `open-telemetry/semantic-conventions-genai`, estado *Development*): evento `gen_ai.evaluation.result` — https://github.com/open-telemetry/semantic-conventions-genai (`docs/gen-ai/gen-ai-events.md`).
    - Zheng, L. et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* arXiv:2306.05685 — sesgos de posición, verbosidad y autopreferencia.
    - Panickssery, A., Bowman, S. R., Feng, S. (2024). *LLM Evaluators Recognize and Favor Their Own Generations.* arXiv:2404.13076 (NeurIPS 2024).
    - Rogan, W. J., Gladen, B. (1978). *Estimating prevalence from the results of a screening test.* American Journal of Epidemiology 107(1):71–76.
    - Husain, H. (2024). *Your AI Product Needs Evals.* https://hamel.dev/blog/posts/evals/
    - Yan, E. (2024). *Evaluating the Effectiveness of LLM-Evaluators (aka LLM-as-Judge).* https://eugeneyan.com/writing/llm-evaluators/
    - Es, S. et al. (2023). *RAGAS: Automated Evaluation of Retrieval Augmented Generation.* arXiv:2309.15217 — fidelidad (*faithfulness*) y relevancia sin referencia.
    - Cochran, W. G. (1977). *Sampling Techniques* (3.ª ed.), Wiley — muestreo estratificado y estimadores post-estratificados.
    - Grafana Labs, documentación de *Alerting* y *Dashboards* (provisioning como código) — https://grafana.com/docs/grafana/latest/
    """)
    nb.save(out)


# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "14_proyecto_evaluacion_online.ipynb", "Proyecto 14 · Evaluador online de SupportOps con métricas en Grafana")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 14 · Evaluador online de SupportOps (y su panel en Grafana)

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (se evalúa en memoria). Opcional: `core` + `metrics` para ver tu panel (paso final) |
    | **RAM aproximada** | < 500 MB |
    | **Prerrequisitos** | Lección `14_evaluacion_online`, módulo 10 (dashboards como código) y proyecto 13 |
    | **Conexión** | Hasta ahora SupportOps medía *si responde*; hoy mide *si responde bien*. El 15 usará tu evaluador para cazar regresiones y el 16 lo convertirá en un SLO |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Producto sospecha que el agente «se inventa cosas» y no hay forma de saberlo: todos los paneles están en verde. Te piden un
    **evaluador online** con cuatro garantías: (1) detecta respuestas sin respaldo, (2) cuesta poco porque **muestrea**, (3) su número poblacional **no está sesgado** y (4) se ve en Grafana y es
    auditable (cada nota cuelga de la traza evaluada). Además, tu jefe quiere saber **cuánto se puede fiar del juez**.

    ## Datos

    Sintéticos y deterministas (semilla 42, `mock`): el **Paso 0** ejecuta 600 tickets con alucinaciones al 6 % y construye un `EvalCase` por ticket. Los primeros 200 forman el **conjunto de calibración**
    (etiquetado por «humanos» = la verdad del inyector); los 400 restantes son «producción» sin etiquetas. Cadena de datos: stack local (opcional) → memoria.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `check_groundedness` | Sensibilidad y especificidad frente a la verdad de los 600 casos | ≥ 0,98 ambas |
    | R2 | `stratified_estimate` | Estimador post-estratificado y error estándar sobre una muestra dada | exacto (tol. 1e-9) |
    | R3 | `eval_telemetry` | Evento válido contra la spec (instantánea) + etiquetas de métrica acotadas | 5/5 comprobaciones |
    | R4 | `bias_probe` | Ganancia por verbosidad y consistencia de posición del juez | ± 0,02 / ± 0,05 de la referencia |
    | R5 | `calibrate` | Sensibilidad/especificidad con IC de Wilson y corrección de la tasa en producción | error ≤ 0,01 frente a la verdad |
    | R6 | `choose_rate` | Mayor tasa de muestreo que cumple el presupuesto de coste y su error de estimación | exacto |
    | R7 | `build_quality_dashboard` | `lint` limpio y 8 consultas clave | 8/8 |

    > 📏 Los umbrales salen de la solución de referencia: R1 se comprobó con las semillas 42, 7 y 99 (sensibilidad y especificidad = 1,0 en las tres); R2, R4 y R5 son cifras exactas de la semilla 42, fija en el notebook. Ojo con R5: la calibración tiene solo ≈ 15 alucinaciones positivas, así que el IC de la sensibilidad es **ancho** (la corrección de Rogan–Gladen con otra semilla puede quedar peor que la tasa observada: justo la lección). El tiempo es simulado: nada depende de tu máquina.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_14.replace('STACK = check_stack("core+metrics")', 'STACK = check_stack([])').replace("LIVE = not STACK.degraded", "LIVE = False") + '''
from supportops.dashkit import Dashboard, lint, prom, loki, tempo, timeseries, stat, bargauge, traces_table, logs, table, heatmap, thresholds
''')

    md("""
    ## Paso 0 · Los datos (te lo damos hecho)
    """)
    code('''
N = 600
FAULTS = {**DEFAULT_FAULT_RATES, "hallucination": 0.06}
TK = generate_tickets(N, seed=SEED, fault_rates=FAULTS)
_col = CaseCollector()
RES = run_tickets(SupportAgent(instrumentor=_col), TK)
CASES = _col.cases
JUDGE, RULE = MockJudge(SEED), RuleJudge()
CALIB, PROD = CASES[:200], CASES[200:]                              # calibración (etiquetada por humanos) / producción (sin etiquetas)
TRUTH = [not c.truth["grounded"] for c in CASES]                    # verdad: ¿alucinada?

# muestra estratificada ya evaluada (por el juez de reglas) para el Paso 2
_ev = OnlineEvaluator(RULE, StratifiedSampler(salt="proyecto"))
for c in CASES: _ev.submit(c)
_ev.run_pending()
EVALS = [{"stratum": r.stratum, "passed": bool(r.verdict.passed)} for r in _ev.records]
POP = dict(_ev.population)
FULL_PASS = float(np.mean([RULE.evaluate(c).passed for c in CASES]))      # lo que daría evaluar TODO
print(f"{len(CASES)} casos · alucinadas: {sum(TRUTH)} · muestra evaluada: {len(EVALS)} · población por estrato: {POP}")
print(f"calidad OK real (evaluando todo): {FULL_PASS:.3f} · media ingenua de la muestra: {np.mean([e['passed'] for e in EVALS]):.3f}")
''')

    # ---------------------------------------------------------------------------------- 1
    md("""
    ## Paso 1 · Un evaluador de groundedness hecho por ti

    **TODO 1.** `check_groundedness(answer, context, question)` devuelve `{"score": 0.0 | 1.0, "unsupported": [(tipo, valor), …]}`. La respuesta está **fundamentada** (`score=1.0`) si toda afirmación verificable está respaldada:

    - **Afirmaciones**: identificadores `ORD-\\d{5}`, `TRK\\d{6,}`, `RF-\\d+`, `HO-\\d+`, `KB-\\d+`; importes `NN,NN €`; y «número + unidad» con unidad ∈ {años, unidades, horas, meses, días}.
    - **Respaldo**: un identificador está respaldado si aparece literalmente en `context` o en `question`; un importe o «número + unidad», si su **número** (con `,` o `.` decimal) aparece entre los números del `context`.
    - **Excepciones** (no son afirmaciones): el ejemplo de formato `ORD-00000` y los hechos de política **«30 días»** y **«5 días»**.
    """)
    md(hint(1, "Usa `re.findall` para cada familia de afirmaciones y normaliza los números con `float(x.replace(',', '.'))`. Para «número + unidad» captura `(\\d+)\\s+(años|unidades|horas|meses|días|dias)`."))
    md(hint(2, "`nums = {round(float(x.replace(',', '.')), 2) for x in re.findall(r'\\d+(?:[.,]\\d+)?', context)}`; un importe/num está respaldado si `round(valor, 2) in nums`. Descarta primero `ORD-00000` y los textos de política (`'30 días'`, `'5 días'`)."))
    code('''
def check_groundedness(answer: str, context: str, question: str = "") -> dict:
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    print(check_groundedness("Reembolso aprobado de 1299,00 € (ref. RF-99999).", '{"order_id": "ORD-00001", "total_eur": 129.0}', "quiero un reembolso de ORD-00001"))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 2
    md("""
    ## Paso 2 · Estimar la calidad poblacional sin sesgo

    **TODO 2.** `stratified_estimate(evals, population)` recibe la lista `EVALS` (dicts `stratum`, `passed`) y la población por estrato `POP`, y devuelve `(estimación, error_estándar)` con el estimador **post-estratificado** de la lección (sección 6):
    estimación \\( \\sum_s \\frac{N_s}{N}\\hat p_s \\), varianza \\( \\sum_s (N_s/N)^2\\,\\hat p_s(1-\\hat p_s)/(n_s-1)\\,(1-n_s/N_s) \\). Ignora los estratos sin evaluaciones y usa `max(n_s - 1, 1)` en el denominador.
    """)
    md(hint(1, "Agrupa `evals` por estrato: `n_s` = nº de evaluaciones, `k_s` = nº de `passed`. Después recorre `population.items()`."))
    code('''
def stratified_estimate(evals: list, population: dict) -> tuple:
    # TODO 2
    raise NotImplementedError("TODO 2")

try:
    est, se = stratified_estimate(EVALS, POP)
    print(f"estimación {est:.4f} ± {1.96 * se:.4f} · media ingenua {np.mean([e['passed'] for e in EVALS]):.4f} · verdad {FULL_PASS:.4f}")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 3
    md("""
    ## Paso 3 · Publicar la evaluación como telemetría

    **TODO 3.** `eval_telemetry(case, name, score, label, explanation, stratum, sample_rate)` devuelve `(event_attrs, metric_attrs)`:

    - `event_attrs`: atributos del evento `gen_ai.evaluation.result`: `gen_ai.evaluation.name`, `gen_ai.evaluation.score.value` (**float**), `gen_ai.evaluation.score.label`, `gen_ai.evaluation.explanation` (recortada a **300** caracteres, solo si hay), `gen_ai.response.id` (solo si el caso lo tiene) y los propios `supportops.ticket.id`, `supportops.eval.stratum`, `supportops.eval.sample_rate`, `gen_ai.agent.version`.
    - `metric_attrs`: etiquetas **acotadas** para la métrica `supportops.eval.results`: exactamente `gen_ai.evaluation.name`, `gen_ai.evaluation.score.label`, `supportops.eval.stratum`, `gen_ai.agent.version`. **Nunca** ids, explicación ni puntuación.
    """)
    code('''
def validate_eval_event(attrs: dict) -> list:
    snap = json.load(open(ROOT / "04_genai_semconv" / "genai_semconv_snapshot.json"))
    probs = []
    if "gen_ai.evaluation.name" not in attrs: probs.append("falta gen_ai.evaluation.name")
    if "gen_ai.evaluation.score.value" not in attrs and "gen_ai.evaluation.score.label" not in attrs: probs.append("falta score.value o score.label")
    for k, v in attrs.items():
        if k.startswith("gen_ai."):
            if k not in snap["attributes"]: probs.append(f"{k} no existe en la spec")
            elif snap["attributes"][k]["type"] == "double" and not isinstance(v, float): probs.append(f"{k} debe ser double")
            elif snap["attributes"][k]["type"] == "string" and not isinstance(v, str): probs.append(f"{k} debe ser string")
    return probs

def eval_telemetry(case, name: str, score: float, label: str, explanation: str, stratum: str, sample_rate: float) -> tuple:
    # TODO 3
    raise NotImplementedError("TODO 3")

try:
    ea, ma = eval_telemetry(CASES[0], "groundedness", 1, "pass", "ok", "base", 0.1)
    print(validate_eval_event(ea) or "evento válido", ma)
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 4
    md("""
    ## Paso 4 · Sondas de sesgo del juez

    **TODO 4.** `bias_probe(judge, cases, pad)` devuelve `{"verbosity_gain": …, "position_consistency": …}` usando **solo la API pública** del juez (`judge.evaluate(case)`, `judge.compare(question, a, b, key=…)`):

    - `verbosity_gain`: sobre los **100 primeros** casos con `truth["grounded"]`, `status == "ok"` y puntuación de relevancia del **juez de reglas** `RULE.evaluate(c).scores["relevance"].value ≤ 0,7`, la media de `relevance` del juez tras añadir `pad * 3` a la respuesta **menos** la media original.
    - `position_consistency`: sobre los **100 primeros** casos con `truth["grounded"]`, `status == "ok"` y `n_tool_calls ≥ 1`, la fracción en que el juez elige **la misma respuesta** en ambos órdenes al comparar `a = c.answer` frente a `b = c.answer + "."` con `key=str(i)` (`i` = posición en esa lista). Elegir la misma respuesta significa `(compare(q, a, b) == "A") != (compare(q, b, a) == "A")`.
    """)
    code('''
PAD = " Gracias por contactar con SupportOps; estamos encantados de ayudarle con todo lo que necesite y quedamos a su entera disposición para cualquier otra consulta."

def bias_probe(judge, cases, pad) -> dict:
    # TODO 4
    raise NotImplementedError("TODO 4")

try:
    print(bias_probe(JUDGE, CASES, PAD))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 5
    md("""
    ## Paso 5 · ¿Cuánto me puedo fiar del juez?

    **TODO 5.** `calibrate(judge, calib, prod)` devuelve un `dict`:

    - `sens`, `spec`: sensibilidad y especificidad del juez para detectar **alucinaciones** (positivo = `groundedness` con etiqueta `fail`; verdad = `not c.truth["grounded"]`) sobre `calib`.
    - `sens_ci`, `spec_ci`: intervalos de Wilson 95 % (`wilson_interval(k, n)`) de ambas.
    - `observed`: tasa de `fail` de `groundedness` del juez sobre `prod`.
    - `corrected`: `observed` corregida con Rogan–Gladen usando `sens` y `spec`.
    """)
    code('''
def calibrate(judge, calib, prod) -> dict:
    # TODO 5
    raise NotImplementedError("TODO 5")

try:
    CAL = calibrate(JUDGE, CALIB, PROD)
    print({k: (tuple(round(x, 3) for x in v) if isinstance(v, tuple) else round(v, 4)) for k, v in CAL.items()}, "· verdad en producción:", round(float(np.mean(TRUTH[200:])), 4))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 6
    md("""
    ## Paso 6 · Elegir la tasa de muestreo

    **TODO 6.** `choose_rate(rates, judge_cost, agent_cost, n_day, max_overhead, p=0.85)` devuelve `{"rate", "overhead", "margin"}`: la **mayor** tasa de `rates` cuyo sobrecoste (coste diario del juez / coste diario del agente) no supera `max_overhead`, su sobrecoste y el margen de error del IC 95 % de la calidad
    (`1,96·√(p(1−p)/n)` con `n = rate · n_day`). Si ninguna cumple, devuelve `{"rate": None, …}` con la menor tasa evaluada.
    """)
    code('''
def choose_rate(rates, judge_cost, agent_cost, n_day, max_overhead, p=0.85) -> dict:
    # TODO 6
    raise NotImplementedError("TODO 6")

try:
    _jc = float(np.mean([RULE.evaluate(c).cost_usd for c in CASES])); _ac = float(np.mean([c.cost_usd for c in CASES]))
    print("coste juez/agente por ticket:", round(_jc, 6), round(_ac, 6), "->", choose_rate([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0], _jc, _ac, 20000, 0.5))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- 7
    md("""
    ## Paso 7 · El panel de calidad como código

    **TODO 7.** `build_quality_dashboard()` devuelve el `dict` de un dashboard (`Dashboard(...).to_dict()`, módulo 10) con **uid** `calidad-online`, título «14 · Calidad online (proyecto)» y **al menos 8 paneles con `description`**. Debe incluir estas consultas:

    1. **Calidad estimada (post-estratificada)**: usa `supportops_eval_population_total` y `supportops_eval_results_total` con `by (supportops_eval_stratum)`.
    2. **Calidad por versión**: `sum by (gen_ai_agent_version)` sobre `supportops_eval_results_total` con `gen_ai_evaluation_score_label="pass"`.
    3. **Cobertura**: `supportops_eval_sampled_total` / `supportops_eval_population_total`.
    4. **Distribución de puntuaciones**: heatmap de `supportops_eval_score_bucket`.
    5. **Feedback**: `supportops_feedback_total`.
    6. **Coste del juez**: `supportops_eval_cost_USD_total`.
    7. **Evaluaciones fallidas (Loki)**: contiene `service_name="supportops-evaluator"` y `gen_ai_evaluation_score_label="fail"`.
    8. **Trazas con fallo (Tempo)**: contiene `supportops.evaluate` y `span.supportops.eval.passed`.
    """)
    md(hint(1, "Estructura (módulo 10): `d = Dashboard('calidad-online', '14 · Calidad online (proyecto)', tags=['curso', 'calidad'])`; `d.add(stat('…', 'promql', description='…'), timeseries('…', [prom('promql', '{{leyenda}}')], description='…'), heatmap('…', 'promql', description='…'), table('…', [loki('logql', '')], description='…'), traces_table('…', 'traceql', description='…'))`; devuelve `d.to_dict()`."))
    code('''
def build_quality_dashboard() -> dict:
    # TODO 7
    raise NotImplementedError("TODO 7")

try:
    D = build_quality_dashboard(); print(len(D["panels"]), "paneles · lint:", lint(D) or "OK")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- rúbrica
    md("""
    ## Paso 8 · Rúbrica
    """)
    code('''
REF = {"est": 0.845256794955425, "se": 0.027401340101016983, "gain": 0.21557142857142855, "pos": 0.2, "sens": 0.9333333333333333, "spec": 0.9891891891891892}   # calibrado con la solución (semilla 42)

def run_rubric():
    rows = []
    def add(r, d, ok, det=""): rows.append({"criterio": r, "descripción": d, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": det})
    # R1
    try:
        pred = [check_groundedness(c.answer, c.context, c.question)["score"] == 0.0 for c in CASES]
        cm = confusion(pred, TRUTH)
        ok = cm["sensitivity"] >= 0.98 and cm["specificity"] >= 0.98
        add("R1", "check_groundedness: sens. y espec. ≥ 0,98", ok, f"sens={cm['sensitivity']:.3f} espec={cm['specificity']:.3f} (tp={cm['tp']} fp={cm['fp']} fn={cm['fn']})")
    except Exception as e: add("R1", "check_groundedness", False, f"{type(e).__name__}: {e}")
    # R2
    try:
        est, se = stratified_estimate(EVALS, POP)
        ok = abs(est - REF["est"]) < 1e-9 and abs(se - REF["se"]) < 1e-9 and abs(est - FULL_PASS) < 0.03
        add("R2", "stratified_estimate: exacto y cerca de la verdad", ok, f"est={est:.6f} (ref {REF['est']:.6f}) se={se:.6f} (ref {REF['se']:.6f}) · verdad={FULL_PASS:.4f}")
    except Exception as e: add("R2", "stratified_estimate", False, f"{type(e).__name__}: {e}")
    # R3
    try:
        c0 = next(c for c in CASES if c.response_id)
        ea, ma = eval_telemetry(c0, "groundedness", 0.0, "fail", "x" * 500, "error", 1.0)
        ea2, _ = eval_telemetry(dataclasses.replace(c0, response_id=""), "relevance", 1, "pass", "", "base", 0.1)
        checks = {"evento válido": not validate_eval_event(ea) and not validate_eval_event(ea2), "score.value es float": isinstance(ea["gen_ai.evaluation.score.value"], float) and isinstance(ea2["gen_ai.evaluation.score.value"], float),
                  "explicación ≤ 300 y ausente si vacía": len(ea["gen_ai.evaluation.explanation"]) == 300 and "gen_ai.evaluation.explanation" not in ea2,
                  "response.id solo si existe": ea["gen_ai.response.id"] == c0.response_id and "gen_ai.response.id" not in ea2,
                  "etiquetas de métrica acotadas": set(ma) == {"gen_ai.evaluation.name", "gen_ai.evaluation.score.label", "supportops.eval.stratum", "gen_ai.agent.version"} and ea["supportops.ticket.id"] == c0.ticket_id}
        add("R3", "eval_telemetry: 5 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R3", "eval_telemetry", False, f"{type(e).__name__}: {e}")
    # R4
    try:
        b = bias_probe(JUDGE, CASES, PAD)
        ok = abs(b["verbosity_gain"] - REF["gain"]) <= 0.02 and abs(b["position_consistency"] - REF["pos"]) <= 0.05
        add("R4", "bias_probe: ganancia por verbosidad y consistencia de posición", ok, f"ganancia={b['verbosity_gain']:.3f} (ref {REF['gain']:.3f}) · consistencia={b['position_consistency']:.2f} (ref {REF['pos']:.2f})")
    except Exception as e: add("R4", "bias_probe", False, f"{type(e).__name__}: {e}")
    # R5
    try:
        cal = calibrate(JUDGE, CALIB, PROD); truth_prod = float(np.mean(TRUTH[200:]))
        ok = abs(cal["sens"] - REF["sens"]) < 1e-9 and abs(cal["spec"] - REF["spec"]) < 1e-9 and cal["sens_ci"][0] < cal["sens"] < cal["sens_ci"][1] and abs(cal["corrected"] - truth_prod) <= 0.01 and abs(cal["corrected"] - truth_prod) < abs(cal["observed"] - truth_prod)
        add("R5", "calibrate: sens/espec exactas, IC y tasa corregida", ok, f"sens={cal['sens']:.3f} spec={cal['spec']:.3f} · observada={cal['observed']:.4f} corregida={cal['corrected']:.4f} verdad={truth_prod:.4f}")
    except Exception as e: add("R5", "calibrate", False, f"{type(e).__name__}: {e}")
    # R6
    try:
        r1 = choose_rate([0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0], 0.0027, 0.0003, 20000, 0.5)
        r2 = choose_rate([0.5, 1.0], 0.0027, 0.0003, 20000, 0.5)
        ok = r1["rate"] == 0.05 and abs(r1["overhead"] - 0.45) < 1e-9 and abs(r1["margin"] - 1.96 * math.sqrt(0.85 * 0.15 / 1000)) < 1e-9 and r2["rate"] is None
        add("R6", "choose_rate: presupuesto y margen", ok, f"{r1} · sin solución -> {r2}")
    except Exception as e: add("R6", "choose_rate", False, f"{type(e).__name__}: {e}")
    # R7
    try:
        import re as _re
        D = build_quality_dashboard()
        exprs = []
        for p in D["panels"]:
            for t in p.get("targets", []): exprs.append(t.get("expr") or t.get("query") or "")
        has = lambda *pats: any(all(_re.search(p, e) for p in pats) for e in exprs)
        checks = {"lint limpio, uid y ≥ 8 paneles": not lint(D) and D["uid"] == "calidad-online" and len(D["panels"]) >= 8,
                  "calidad post-estratificada": has(r"supportops_eval_population_total", r"supportops_eval_results_total", r"by \\(supportops_eval_stratum\\)"),
                  "calidad por versión": has(r"sum by \\(gen_ai_agent_version\\)", r"supportops_eval_results_total", r'score_label="pass"'), "cobertura": has(r"supportops_eval_sampled_total", r"supportops_eval_population_total"),
                  "distribución": has(r"supportops_eval_score_bucket"), "feedback": has(r"supportops_feedback_total"), "coste del juez": has(r"supportops_eval_cost_USD_total"),
                  "Loki fallidas": has(r'service_name="supportops-evaluator"', r'gen_ai_evaluation_score_label="fail"'), "Tempo": has(r"supportops\\.evaluate", r"span\\.supportops\\.eval\\.passed")}
        add("R7", "build_quality_dashboard: lint + 8 consultas", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R7", "build_quality_dashboard", False, f"{type(e).__name__}: {e}")
    return pd.DataFrame(rows).set_index("criterio")
''')
    code('''
# Ejecuta esta celda cuando hayas terminado los TODO
display(run_rubric())
''')

    md("""
    ---
    ## Paso final (opcional) · Míralo funcionar

    Con el stack (`docker compose --profile core --profile metrics up -d`): guarda tu dashboard con `Dashboard.save(...)` en `stack/grafana/dashboards/`, y ejecuta `LivePipeline(("v1",), mode="otlp", sampler=StratifiedSampler()).run_live(generate_tickets(150, seed=42, duration_s=60, fault_rates=FAULTS, start_s=0.0), 60)`
    (de `supportops.regression`). Espera ≈ 20 s y abre http://localhost:3000 (`admin`/`admin`): el panel «Calidad estimada» debe moverse y los logs de evaluaciones fallidas deben enlazar con la traza del agente.

    ## Retos extra (nivel experto)

    1. **Cascada de evaluadores**: ejecuta primero las reglas y envía al juez solo los casos con `groundedness` incierto (0,3–0,7). ¿Cuánto coste ahorras y cuánta sensibilidad pierdes? Mídelo con la verdad.
    2. **Juez por pares con ambos órdenes**: implementa `compare_both(judge, q, a, b)` que devuelve `"A"`, `"B"` o `"tie"` y mide cómo cambia la consistencia.
    3. **IC de la calidad por versión**: con dos versiones del agente (módulo 15) calcula la diferencia de calidad con intervalo y decide si es significativa con el n evaluado.
    4. **Calibración con deriva**: cambia el `MockJudge` a `miss_rate=0.25` y comprueba que `calibrate` lo detecta y que la tasa corregida se mantiene cerca de la verdad.
    5. **Evaluación del feedback**: usa `simulate_feedback` para forzar la evaluación de todos los tickets con valoración negativa (se suman al estrato `error`); ¿sesga el estimador? ¿cómo lo corriges?

    ## Reflexión (producción e hilo conductor)

    - Tu juez cuesta ~9× un ticket: ¿qué tasa de muestreo defenderías ante finanzas (módulo 13) y qué margen de error aceptas? ¿Cómo cambia la respuesta para un cliente premium?
    - ¿Dónde pondrías el **umbral de alerta** de calidad para que no despierte a nadie por ruido del juez? (módulo 16: SLO de calidad y *min events*).
    - ¿Qué parte de tu evaluador deberías poder **auditar** si un cliente reclama que su ticket fue evaluado con sus datos personales? (módulo 20).
    - El módulo 15 usará los casos con evaluación fallida para construir el dataset de regresión: ¿qué campos de la telemetría necesitarías conservar?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine las funciones y vuelve a lanzar la rúbrica).
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
def check_groundedness(answer, context, question=""):
    claims = [("id", m) for m in re.findall(r"\\b(?:ORD-\\d{5}|TRK\\d{6,}|RF-\\d+|HO-\\d+|KB-\\d+)\\b", answer) if m != "ORD-00000"]
    claims += [("eur", m) for m in re.findall(r"(\\d+(?:[.,]\\d+)?)\\s?€", answer)]
    claims += [("num", f"{n} {u}") for n, u in re.findall(r"(\\d+)\\s+(años|unidades|horas|meses|días|dias)\\b", answer)]
    nums = {round(float(x.replace(",", ".")), 2) for x in re.findall(r"\\d+(?:[.,]\\d+)?", context)}
    bad = []
    for kind, val in claims:
        if kind == "id": ok = val in context or val in question
        elif val in ("30 días", "5 días"): ok = True
        else: ok = round(float(val.split()[0].replace(",", ".")), 2) in nums
        if not ok: bad.append((kind, val))
    return {"score": 0.0 if bad else 1.0, "unsupported": bad}

def stratified_estimate(evals, population):
    N = sum(population.values()); est = var = 0.0
    for s, Ns in population.items():
        xs = [e["passed"] for e in evals if e["stratum"] == s]
        n = len(xs)
        if n == 0: continue
        p, w = sum(xs) / n, Ns / N
        est += w * p
        var += w * w * p * (1 - p) / max(n - 1, 1) * max(0.0, 1 - n / Ns)
    return est, math.sqrt(var)

def eval_telemetry(case, name, score, label, explanation, stratum, sample_rate):
    ev = {"gen_ai.evaluation.name": name, "gen_ai.evaluation.score.value": float(score), "gen_ai.evaluation.score.label": label}
    if explanation: ev["gen_ai.evaluation.explanation"] = explanation[:300]
    if case.response_id: ev["gen_ai.response.id"] = case.response_id
    ev.update({"supportops.ticket.id": case.ticket_id, "supportops.eval.stratum": stratum, "supportops.eval.sample_rate": float(sample_rate), "gen_ai.agent.version": case.version})
    mt = {"gen_ai.evaluation.name": name, "gen_ai.evaluation.score.label": label, "supportops.eval.stratum": stratum, "gen_ai.agent.version": case.version}
    return ev, mt

def bias_probe(judge, cases, pad):
    low = [c for c in cases if c.truth["grounded"] and c.status == "ok" and RULE.evaluate(c).scores["relevance"].value <= 0.7][:100]
    gain = float(np.mean([judge.evaluate(dataclasses.replace(c, answer=c.answer + pad * 3)).scores["relevance"].value - judge.evaluate(c).scores["relevance"].value for c in low]))
    pairs = [c for c in cases if c.truth["grounded"] and c.status == "ok" and c.n_tool_calls >= 1][:100]
    same = 0
    for i, c in enumerate(pairs):
        a, b = c.answer, c.answer + "."
        same += (judge.compare(c.question, a, b, key=str(i)) == "A") != (judge.compare(c.question, b, a, key=str(i)) == "A")
    return {"verbosity_gain": gain, "position_consistency": same / len(pairs)}

def calibrate(judge, calib, prod):
    fails = lambda cs: [judge.evaluate(c).scores["groundedness"].label == "fail" for c in cs]
    pred, truth = fails(calib), [not c.truth["grounded"] for c in calib]
    cm = confusion(pred, truth)
    sens, spec = cm["sensitivity"], cm["specificity"]
    observed = float(np.mean(fails(prod)))
    return {"sens": sens, "spec": spec, "sens_ci": wilson_interval(cm["tp"], cm["tp"] + cm["fn"]), "spec_ci": wilson_interval(cm["tn"], cm["tn"] + cm["fp"]),
            "observed": observed, "corrected": rogan_gladen(observed, sens, spec)}

def choose_rate(rates, judge_cost, agent_cost, n_day, max_overhead, p=0.85):
    best = None
    for r in sorted(rates):
        over = r * n_day * judge_cost / (n_day * agent_cost)
        if over <= max_overhead + 1e-12: best = (r, over)
    if best is None:
        r = min(rates); return {"rate": None, "overhead": r * judge_cost / agent_cost, "margin": 1.96 * math.sqrt(p * (1 - p) / (r * n_day))}
    r, over = best
    return {"rate": r, "overhead": over, "margin": 1.96 * math.sqrt(p * (1 - p) / (r * n_day))}

def build_quality_dashboard():
    d = Dashboard("calidad-online", "14 · Calidad online (proyecto)", tags=["curso", "calidad"], description="Calidad de las respuestas de SupportOps medida online.")
    pop = "sum by (supportops_eval_stratum) (rate(supportops_eval_population_total[5m]))"
    ok_ = 'sum by (supportops_eval_stratum) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m]))'
    all_ = 'sum by (supportops_eval_stratum) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))'
    d.add(
        stat("Calidad estimada (post-estratificada)", f"sum({pop} * ({ok_} / {all_})) / sum(rate(supportops_eval_population_total[5m]))", unit="percentunit", w=6, description="Tasa de respuestas fundamentadas, ponderada por el tamaño real de cada estrato."),
        timeseries("Calidad por versión", [prom('sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m])) / sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))', "{{gen_ai_agent_version}}")], unit="percentunit", w=9, description="Groundedness por versión del agente."),
        timeseries("Cobertura de la evaluación", [prom("sum(rate(supportops_eval_sampled_total[5m])) / sum(rate(supportops_eval_population_total[5m]))", "evaluadas / total")], unit="percentunit", w=9, description="Fracción de peticiones evaluadas."),
        heatmap("Distribución de puntuaciones", "sum by (le) (increase(supportops_eval_score_bucket[$__rate_interval]))", unit="short", w=12, description="Histograma de puntuaciones 0..1 de los jueces."),
        timeseries("Feedback de usuarios", [prom("sum by (supportops_feedback_rating) (rate(supportops_feedback_total[5m]))", "{{supportops_feedback_rating}}")], w=12, description="Valoraciones explícitas (sintéticas)."),
        timeseries("Coste del juez", [prom("sum(rate(supportops_eval_cost_USD_total[5m]))", "juez")], unit="currencyUSD", w=8, description="Gasto del juez (precios ilustrativos)."),
        logs("Evaluaciones fallidas (Loki)", '{service_name="supportops-evaluator"} | gen_ai_evaluation_score_label="fail"', w=8, description="Evaluaciones con etiqueta fail."),
        traces_table("Trazas de evaluación con fallo (Tempo)", '{ name = "supportops.evaluate" && span.supportops.eval.passed = false }', w=8, description="Evaluaciones que no pasaron."),
    )
    return d.to_dict()

display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, gauge, heatmap, lint, logs, prom, stat, table, text, thresholds, timeseries, traces_table
    d = Dashboard("calidad-online", "14 · Calidad online", tags=["curso", "calidad", "evaluacion"], time_from="now-30m",
                  description="Calidad de las respuestas de SupportOps medida online: evaluaciones del juez (muestreadas por estratos), cobertura, feedback y coste de evaluar.")
    pop = "sum by (supportops_eval_stratum) (rate(supportops_eval_population_total[5m]))"
    ok_ = 'sum by (supportops_eval_stratum) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m]))'
    all_ = 'sum by (supportops_eval_stratum) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))'
    strat = f"sum({pop} * ({ok_} / {all_})) / sum(rate(supportops_eval_population_total[5m]))"
    d.add(text("Cómo leer este dashboard", "La evaluación es **asíncrona y muestreada por estratos** (error 100 %, escalado 50 %, premium 25 %, base 10 %). La media de la muestra está **sesgada**: el panel «Calidad estimada» "
               "la re-pondera por el tamaño real de cada estrato (`supportops_eval_population_total`, que cuenta TODAS las peticiones). Las notas son del juez simulado (`mock`) del módulo 14. "
               "Cada evaluación fallida cuelga del `trace_id` del span evaluado: haz clic en el log para abrir la traza del agente.", h=3))
    d.row("Resumen")
    d.add(
        stat("Calidad estimada (groundedness, post-estratificada)", strat, unit="percentunit", w=6, h=5, decimals=3, thr=thresholds((None, "red"), (0.8, "orange"), (0.9, "green")),
             description="Tasa de respuestas fundamentadas en los últimos 5 min, ponderada por el tamaño real de cada estrato."),
        stat("Media ingenua de la muestra", 'sum(rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m])) / sum(rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))',
             unit="percentunit", w=6, h=5, decimals=3, description="Lo que daría promediar solo lo evaluado: sesgada por el muestreo estratificado. Compárala con el panel de la izquierda."),
        stat("Cobertura (evaluadas / total)", "sum(increase(supportops_eval_sampled_total[5m])) / sum(increase(supportops_eval_population_total[5m]))", unit="percentunit", w=6, h=5, decimals=3,
             description="Fracción de peticiones evaluadas. Si cae a 0 el juez está caído: la calidad «perfecta» sería un falso verde."),
        stat("Coste del juez / coste del agente", "sum(increase(supportops_eval_cost_USD_total[5m])) / sum(increase(supportops_llm_cost_USD_total{service_name=\"supportops-agent\"}[5m]))", w=6, h=5, decimals=2,
             description="Cuántas veces cuesta evaluar lo que cuesta atender (precios ilustrativos). Requiere el MetricsInstrumentor del módulo 09 en el agente."),
    )
    d.row("Calidad en el tiempo")
    d.add(
        timeseries("Calidad por criterio (pass-rate)", [prom('sum by (gen_ai_evaluation_name) (rate(supportops_eval_results_total{gen_ai_evaluation_score_label="pass"}[5m])) / sum by (gen_ai_evaluation_name) (rate(supportops_eval_results_total[5m]))', "{{gen_ai_evaluation_name}}")],
                   unit="percentunit", w=12, description="Tasa de aprobados de cada criterio (muestra, sin re-ponderar). Una caída de groundedness sin cambios en resolución = alucinaciones."),
        timeseries("Calidad por versión del agente (groundedness)", [prom('sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[5m])) / sum by (gen_ai_agent_version) (rate(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[5m]))', "{{gen_ai_agent_version}}")],
                   unit="percentunit", w=12, description="Comparativa entre versiones desplegadas a la vez (canario) o consecutivas: base del módulo 15."),
        timeseries("Muestreo por estrato", [prom("sum by (supportops_eval_stratum) (rate(supportops_eval_sampled_total[5m]))", "evaluadas · {{supportops_eval_stratum}}"),
                                            prom("sum by (supportops_eval_stratum) (rate(supportops_eval_population_total[5m]))", "población · {{supportops_eval_stratum}}", ref="B")], w=12,
                   description="Peticiones por segundo evaluadas y totales por estrato: los errores se evalúan todos, la base muy poco."),
        heatmap("Distribución de puntuaciones (todos los criterios)", "sum by (le) (increase(supportops_eval_score_bucket[$__rate_interval]))", unit="short", w=12,
                description="Histograma de las puntuaciones 0..1. Bimodal (0 y 1) = juez con rúbrica binaria; masa en el medio = juez indeciso."),
    )
    d.row("Feedback y coste de evaluar")
    d.add(
        timeseries("Feedback de usuarios (sintético)", [prom("sum by (supportops_feedback_rating) (rate(supportops_feedback_total[5m]))", "{{supportops_feedback_rating}}")], w=8,
                   description="Valoraciones explícitas por segundo: SESGADAS (responden más los descontentos). Úsalas como disparador, no como estimador."),
        timeseries("Coste del juez (USD/s)", [prom("sum(rate(supportops_eval_cost_USD_total[5m]))", "juez")], unit="currencyUSD", w=8, description="Gasto en evaluar (precios ilustrativos)."),
        timeseries("Latencia del juez p95 (s)", [prom("histogram_quantile(0.95, sum by (le) (rate(supportops_eval_duration_seconds_bucket[5m])))", "p95")], unit="s", w=8,
                   description="Latencia (simulada) de una llamada al juez. No afecta al usuario: la evaluación es asíncrona."),
    )
    d.row("Evaluaciones fallidas: de la nota a la traza")
    d.add(
        logs("Evaluaciones fallidas (Loki)", '{service_name="supportops-evaluator"} | gen_ai_evaluation_score_label="fail"', w=14, h=10,
             description="Eventos gen_ai.evaluation.result con etiqueta fail. `trace_id` es el del span evaluado del agente (Loki guarda el nombre del evento solo en el cuerpo)."),
        traces_table("Trazas de evaluación con fallo (Tempo)", '{ name = "supportops.evaluate" && span.supportops.eval.passed = false }', w=10, h=10,
                     description="Trazas del evaluador cuyo veredicto global fue «no pasa». Cada una lleva un span link a la traza del agente evaluada."),
    )
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "14-calidad-online.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
def build_readme() -> None:
    readme = """# Módulo 14 · Evaluación online de agentes de IA

🔴 **Experto** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ El agente y el «juez» son **simulados y deterministas** (`mock`, semilla 42): el juez es un conjunto de reglas con errores realistas
> (falsos negativos/positivos, sesgo de verbosidad y de posición) para poder **medirlos contra la verdad**. Las cifras cambian con un juez real; el método no.

Las señales clásicas (latencia, errores, coste) no ven la **calidad**: una respuesta inventada es `ok`, rápida y barata. Este módulo mide la calidad **en producción** y la convierte en telemetría:
un evaluador asíncrono sobre una **muestra**, el evento `gen_ai.evaluation.result` de la spec GenAI (estado *Development*) asociado al span evaluado, métricas de calidad y un panel en Grafana.

## Objetivos
1. Elegir el tipo de evaluador (reglas, juez LLM, humano, feedback) según coste, latencia y fiabilidad.
2. Implementar a mano un evaluador de *groundedness* y medir su sensibilidad y especificidad.
3. Emitir evaluaciones como telemetría OTel (evento ligado al span evaluado, span enlazado del juez, métricas `supportops.eval.*`).
4. Diseñar un muestreo estratificado y estimar la calidad poblacional sin sesgo (post-estratificación).
5. Medir y corregir los sesgos del juez (verbosidad, posición; corrección de Rogan–Gladen).
6. Interpretar el feedback de usuario (sesgo de respuesta) y calcular el coste de evaluar.

## Contenido
| Archivo | Qué es |
|---|---|
| `14_evaluacion_online.ipynb` | Lección (14 secciones, 10 gráficos, stack real opcional, 🧠 de élite, autoevaluación) |
| `14_proyecto_evaluacion_online.ipynb` | Proyecto: groundedness a mano, estimador post-estratificado, evento validado contra la spec, sondas de sesgo, calibración del juez, tasa de muestreo y panel como código (rúbrica calibrada, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/quality_eval.py` | `CaseCollector`, `RuleJudge`/`MockJudge`/`LLMJudge`, `RateSampler`/`StratifiedSampler`, `OnlineEvaluator`, estadística (Wilson, post-estratificación, Rogan–Gladen), `simulate_feedback` |
| `../supportops/tests/test_quality_eval.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/14-calidad-online.json` | Dashboard «14 · Calidad online» (uid `calidad-online`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 8 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`).
- **Juez real** (opcional): `JUDGE_PROVIDER=anthropic|openai|ollama` + `JUDGE_MODEL` (claves solo por variables de entorno).

## Lecturas
- OpenTelemetry GenAI semantic conventions, evento `gen_ai.evaluation.result` (repo `open-telemetry/semantic-conventions-genai`).
- Zheng et al. (2023), *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* · Panickssery et al. (2024), *LLM Evaluators Recognize and Favor Their Own Generations* · Rogan y Gladen (1978).

## Cómo se conecta
Antes: módulos 04 (GenAI semconv), 09 (métricas), 13 (coste por ticket). Después: el 15 usa el evaluador para detectar regresiones de prompt y construir datasets desde trazas; el 16 convierte la calidad en un SLO con *burn rate*; el 18 decide cuánto evaluar con un presupuesto; el 20 revisa la privacidad de lo que se envía al juez.
"""
    (COURSE / MOD / "README.md").write_text(readme, encoding="utf-8")
    print("OK README", MOD)


if __name__ == "__main__":
    build_lesson()
    build_project()
    build_readme()
    build_dashboard()
