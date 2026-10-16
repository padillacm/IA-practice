"""Genera el módulo 13_costes_finops: README, lección, proyecto y dashboard.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_13.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "13_costes_finops"

IMPORTS_13 = '''
import dataclasses, json, math, time
from supportops.instrument import CompositeInstrumentor
from supportops.telemetry import OTelInstrumentor, setup_telemetry
from supportops.finops import (ILLUSTRATIVE_PRICES, BudgetGuard, BudgetPool, CacheSimulator, CostLedger, DowngradeLLM, FinOpsInstrumentor, LoopGuard,
                               ModelPrice, PriceTable, Usage4, cost_drift_alert, detect_loop_in_result, finops_alert_rule_json, policy_prompt, semconv_usage)
STACK = check_stack("core+metrics")
LIVE = not STACK.degraded                      # True: Collector + Prometheus responden y podemos enviar telemetría de verdad
PP = policy_prompt(2500)                       # prompt de sistema largo (políticas incrustadas): ≈ 2 500 tokens, para que la caché importe
'''

PRICE_BANNER = "⚠️ **Todos los precios de este módulo son ILUSTRATIVOS** (no son de ningún proveedor ni de ninguna fecha): sirven para que las magnitudes sean razonables. Cárgalos de tu proveedor con `PriceTable.from_json(...)` o `SUPPORTOPS_PRICES_FILE`."


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "13_costes_finops.ipynb", "Módulo 13 · Costes y FinOps de agentes de IA")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 13 · Costes y FinOps: de tokens a dinero, con presupuesto y sin sorpresas

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Opcional: `--profile core --profile metrics` (sección 9). Sin Docker todo funciona en **modo degradado** (telemetría en memoria; mismo esquema). Funciona en Colab |
    | **RAM aproximada** | < 500 MB sin stack · ≈ 1,2 GB con `core` + `metrics` |
    | **Prerrequisitos** | Módulos 03-04 (SDK, GenAI semconv), 09 (métricas, cardinalidad), 10 (Grafana) y 11 (contar solo en las hojas) |
    | **Hilo conductor** | A SupportOps le llega la factura del LLM: ¿quién la genera, por qué sube y cómo se frena? |

    > {PRICE_BANNER}
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Calcular** el coste de una llamada y de un ticket desde los tokens con una **tabla de precios configurable**, incluyendo lectura y escritura de caché (y **reconciliarlo** con el coste que calcula el propio agente).
    2. **Normalizar** el `usage` de una API a la semántica de la spec GenAI (la entrada **incluye** la caché) sin contar tokens dos veces.
    3. **Atribuir** el gasto por cliente, *feature*, modelo y agente, eligiendo la señal correcta (métricas, logs o trazas) para no disparar la cardinalidad.
    4. **Medir** el ahorro de la **caché de prompts**, su punto de equilibrio y los tres modos en que se rompe.
    5. **Diseñar presupuestos y topes** (por ticket, cliente y periodo), con **degradación de modelo** y **burn rate** del presupuesto.
    6. **Detectar y cortar bucles caros**, tanto post-hoc como en línea, y cuantificar el coste del *falso positivo*.
    7. **Publicar** el coste como telemetría OpenTelemetry (spans, métricas y logs), construir un panel de FinOps y una **alerta de desvío**.
    8. **Razonar** sobre la *unidad económica* correcta: coste por ticket **resuelto**, no por llamada.
    """)

    md("## 🔁 Conexión con módulos anteriores")
    md(details("1 · (Módulo 09) ¿Por qué `customer_id` no puede ser una etiqueta de una métrica de coste y dónde pones entonces el coste por cliente?",
               "Porque cada valor distinto crea una serie temporal nueva (200 clientes × 4 *features* × 2 modelos × … series) y la cardinalidad explota. El coste por cliente va en **logs** estructurados (Loki, `customer_id` como *structured metadata*) y en **atributos de span**; las métricas llevan solo etiquetas de baja cardinalidad (modelo, *feature*, tier, agente)."))
    md(details("2 · (Módulo 11) Un orquestador y sus subagentes llevan `gen_ai.usage.*` en sus spans `invoke_agent`. ¿Cómo sumas el coste del árbol sin duplicar?",
               "Sumando **solo los spans hoja `chat`**: cada `invoke_agent` repite el total de sus hijos. Es la regla de la spec («cada llamada de inferencia se cuenta una vez»)."))
    md(details("3 · (Módulo 04) ¿Los tokens de caché son un extra o un subconjunto de `gen_ai.usage.input_tokens`?",
               "**Subconjunto**: según la spec GenAI (estado *Development*), `input_tokens` incluye los tokens servidos desde caché y los escritos en caché; `cache_read.input_tokens` y `cache_write.input_tokens` son subconjuntos de la entrada."))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_13 + '''
TEL = setup_telemetry("supportops-agent", mode="otlp" if LIVE else "memory", set_global=False, metric_interval_s=2.0, resource_attrs={"deployment.environment.name": "lab"})
print("Stack:", "arriba (OTLP al Collector)" if LIVE else "no disponible -> modo degradado (telemetría en memoria)")
print(ILLUSTRATIVE_PRICES.describe())
''')

    # ------------------------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · Intuición: el coste de un agente es una distribución con cola larga

    Una llamada a un LLM se factura por **tokens**; un ticket de SupportOps son entre 2 y 6 llamadas (y cada una vuelve a enviar el contexto acumulado); un día son miles de tickets. Tres hechos hacen que el coste de un agente sea **difícil de prever** y **fácil de disparar**:

    - **No es determinista**: el mismo ticket puede costar 1 llamada o 6 (reintentos, bucles de herramientas).
    - **Crece por dentro del ticket**: el contexto se reenvía y se paga en cada paso.
    - **Lo decide una variable de configuración**: cambiar de modelo o de prompt cambia la factura ×10 sin tocar un solo ticket.

    | Si vienes de… | Esto es como… | Lo que cambia |
    |---|---|---|
    | **ML** | El coste de inferencia (GPU-horas, *throughput*) | La unidad es el **token**, y la factura depende del **contenido** de la petición, no solo de su número |
    | **Backend** | La factura de la nube / coste por petición | Hay que **atribuirla** (cliente, *feature*) y vigilar el p99, no la media |
    | **SRE** | El *error budget* | Existe un **presupuesto de coste** con su *burn rate* y su alerta |
    """)
    code('''
N = 240 if FAST_DEV_RUN else 1200
tickets = generate_tickets(N, seed=SEED, fault_rates={**DEFAULT_FAULT_RATES, "tool_loop": 0.04})       # 4 % de bucles de herramientas (el doble que la base) para ver la cola
led = CostLedger()
agent = SupportAgent(system_prompt=PP, instrumentor=FinOpsInstrumentor(ILLUSTRATIVE_PRICES, ledger=led, loop_fn=lambda r: detect_loop_in_result(r)[0]))       # sin caché de momento
results = run_tickets(agent, tickets)
df = led.to_frame()
c = df.cost_usd
srt = np.sort(c.values)[::-1]; top5 = srt[: max(int(0.05 * len(srt)), 1)].sum() / srt.sum()
print(f"{len(df)} tickets · coste total ${c.sum():.4f} · media ${c.mean():.6f} · p50 ${c.median():.6f} · p95 ${c.quantile(.95):.6f} · p99 ${c.quantile(.99):.6f} · máx ${c.max():.6f}")
print(f"el 5 % de los tickets más caros concentra el {top5:.0%} del gasto · p99/media = {c.quantile(.99) / c.mean():.1f}×")
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4))
axes[0].hist(c * 1000, bins=np.geomspace(c[c > 0].min() * 1000, c.max() * 1000, 40), color=viz.PALETTE["metrics"], alpha=0.9); axes[0].set_xscale("log")
for q, col in ((0.5, viz.PALETTE["logs"]), (0.99, viz.PALETTE["error"])): axes[0].axvline(c.quantile(q) * 1000, color=col, ls="--", label=f"p{int(q * 100)}")
axes[0].set_xlabel("coste por ticket (milésimas de USD, log)"); axes[0].set_ylabel("tickets"); axes[0].set_title("Distribución del coste por ticket"); axes[0].legend()
x = np.arange(1, len(srt) + 1) / len(srt) * 100; axes[1].plot(x, np.cumsum(srt) / srt.sum() * 100, color=viz.PALETTE["traces"], lw=2)
axes[1].plot([0, 100], [0, 100], color=viz.PALETTE["neutral"], ls=":"); axes[1].set_xlabel("% de tickets (de más a menos caros)"); axes[1].set_ylabel("% del gasto acumulado"); axes[1].set_title("Concentración del gasto")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La distribución tiene **cola**: el p99 es ≈ 3× la media y unos pocos tickets cuestan varias veces el típico. Los tickets de cola son los que tienen **reintentos y bucles** (más llamadas con contexto creciente).
    - La curva de concentración está por encima de la diagonal: el 5 % de los tickets más caros se lleva más del doble de lo que le tocaría (≈ 13 %). Con precios y tráfico de laboratorio la cola es moderada; en producción, con más fallos y contextos largos, suele ser mucho más pesada. Vigilar solo la **media** es ceguera: el dinero está en la cola.
    - Este panorama es **sin caché**; en la sección 5 veremos cuánto lo cambia. Y los precios son ilustrativos: lo importante son las **proporciones**.
    """))

    # ------------------------------------------------------------------------------------------------------------- 2
    md("""
    ---
    # 2 · Teoría: de tokens a dinero

    @@BANNER@@

    ## 2.1 La fórmula

    Un proveedor cobra por millón de tokens, con precios distintos para la entrada, la salida y —si hay caché de prompts— la lectura y la escritura de caché. Con la semántica de la spec GenAI (la entrada **incluye** los tokens de caché):

    $$C \\;=\\; \\frac{u\\,p_{in} \\;+\\; r\\,p_{cr} \\;+\\; w\\,p_{cw} \\;+\\; o\\,p_{out}}{10^6}, \\qquad u = I - r - w$$

    donde `I` = tokens de entrada **totales** (`gen_ai.usage.input_tokens`), `r` = leídos de caché (`gen_ai.usage.cache_read.input_tokens`), `w` = escritos en caché (`gen_ai.usage.cache_write.input_tokens`), `u` = entrada **no** cacheada, `o` = salida y `p_*` los precios por millón. Los multiplicadores de caché **varían por modelo y proveedor**: la documentación de *prompt caching* de Anthropic indica, por ejemplo, escritura a 1,25× el precio de entrada (TTL de 5 min) o 2× (1 h) y lectura a 0,1× salvo excepciones por modelo (0,05× en algunos), y mínimos cacheables que dependen del modelo (de 512 a 4 096 tokens). Por eso aquí **nada está fijo**: es una tabla.

    ## 2.2 Qué reporta cada API (¡no todas igual!)

    | Estilo | Entrada total |
    |---|---|
    | **Spec GenAI** (`semconv`) | `input_tokens` ya **incluye** caché; `cache_read` y `cache_write` son subconjuntos |
    | **Anthropic** (documentación de *prompt caching*) | `input_tokens` **excluye** caché; total = `cache_read_input_tokens + cache_creation_input_tokens + input_tokens` |

    Si copias a un atributo `gen_ai.usage.input_tokens` el `input_tokens` de Anthropic **sin sumar** la caché, tu instrumentación infravalora la entrada (y rompe el invariante `cache_read + cache_write ≤ input_tokens`).
    """.replace("@@BANNER@@", PRICE_BANNER))
    code('''
raw = {"input_tokens": 300, "output_tokens": 200, "cache_read_input_tokens": 2400, "cache_creation_input_tokens": 100}      # lo que devuelve una API estilo Anthropic
u = semconv_usage("anthropic", **raw)
print("API (Anthropic): input_tokens =", raw["input_tokens"], "(sin caché)  ->  semántica spec: input_total =", u.input_total, "· cache_read =", u.cache_read, "· cache_write =", u.cache_write, "· no cacheada =", u.uncached)
try: Usage4(100, 10, cache_read=80, cache_write=40)
except ValueError as e: print("el invariante protege:", e)
for model in ("mock-small", "mock-large"):
    print(model, ILLUSTRATIVE_PRICES.cost(model, u).as_dict())
''')
    code('''
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4), sharey=False)
scen = {"sin caché": Usage4(3000, 300), "caché FRÍA\\n(se escribe)": Usage4(3000, 300, cache_write=3000), "caché CALIENTE\\n(2800 leídos, 200 nuevos)": Usage4(3000, 300, cache_read=2800, cache_write=200)}
cols = {"input": viz.PALETTE["traces"], "cache_read": viz.PALETTE["logs"], "cache_write": viz.PALETTE["warn"], "output": viz.PALETTE["metrics"]}
for ax, model in zip(axes, ("mock-small", "mock-large")):
    bot = np.zeros(len(scen))
    for comp in ("input", "cache_read", "cache_write", "output"):
        vals = np.array([ILLUSTRATIVE_PRICES.cost(model, uu).as_dict()[comp] for uu in scen.values()]) * 1e3
        ax.bar(range(len(scen)), vals, bottom=bot, color=cols[comp], label=comp.replace("_", " "), width=0.6); bot += vals
    ax.set_xticks(range(len(scen)), list(scen), fontsize=8.5); ax.set_title(f"{model}: una petición de 3 000 tokens de entrada"); ax.set_ylabel("coste (milésimas de USD)")
    for i, t in enumerate(bot): ax.text(i, t, f"{t:.2f}", ha="center", va="bottom", fontsize=9)
axes[0].legend(); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con la caché **caliente** el coste de entrada cae a una fracción: lo que queda es sobre todo la **salida**. Con la caché **fría** pagas la escritura con **recargo**: la primera petición sale *más cara* que sin caché. La caché solo compensa si el prefijo **se reutiliza**.
    - El reparto cambia según el modelo: en el modelo grande la entrada pesa mucho más, así que la caché ahorra más en dinero absoluto.
    - La **salida** cuesta varias veces más por token que la entrada: recortar respuestas largas es la otra palanca (y la más segura para la calidad).
    """))

    # ------------------------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · A mano, y reconciliado con el agente

    Antes de confiar en una tabla de precios, comprueba que **reproduce** lo que ya calcula el agente (`AgentResult.cost_usd`, con los precios del mock de `supportops.pricing`). Si no cuadra, tienes un bug de unidades o de contabilidad de tokens:
    """)
    code('''
PRECIOS = {"mock-small": (0.25, 1.25), "mock-large": (3.00, 15.00)}           # USD por millón de tokens (entrada, salida), a mano
def coste_a_mano(modelo, t_in, t_out):
    p_in, p_out = PRECIOS[modelo]
    return (t_in * p_in + t_out * p_out) / 1_000_000

a_mano = sum(coste_a_mano(r.model, r.input_tokens, r.output_tokens) for r in results)
agente = sum(r.cost_usd for r in results)
tabla = df.cost_usd.sum()
print(f"a mano = ${a_mano:.6f} · AgentResult.cost_usd = ${agente:.6f} · PriceTable/FinOps = ${tabla:.6f}")
print("diferencia máxima por ticket (PriceTable vs agente):", f"{max(abs(r.cost_usd - x) for r, x in zip(results, df.cost_usd)):.2e}", "(el agente redondea a 6 decimales)")
''')
    code('''
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4))
long_t = next(r for r in results if r.n_llm_calls >= 4)
steps = [s for s in long_t.steps if s.kind == "llm"]
axes[0].bar(range(1, len(steps) + 1), [s.input_tokens for s in steps], color=viz.PALETTE["traces"], label="entrada (se reenvía TODO el contexto)")
axes[0].bar(range(1, len(steps) + 1), [s.output_tokens for s in steps], bottom=[s.input_tokens for s in steps], color=viz.PALETTE["metrics"], label="salida")
axes[0].set_xlabel("llamada nº"); axes[0].set_ylabel("tokens"); axes[0].set_title(f"El contexto crece paso a paso (ticket {long_t.ticket_id})"); axes[0].legend(fontsize=8)
by_n = df.assign(n=df.n_llm.clip(upper=7)).groupby("n").cost_usd.agg(["mean", "count"])
axes[1].bar(by_n.index, by_n["mean"] * 1000, color=viz.PALETTE["metrics"])
for n_, (m_, k_) in by_n.iterrows(): axes[1].text(n_, m_ * 1000, f"n={int(k_)}", ha="center", va="bottom", fontsize=8)
axes[1].set_xlabel("llamadas al LLM por ticket"); axes[1].set_ylabel("coste medio (milésimas de USD)"); axes[1].set_title("Cada llamada extra cuesta más que la anterior")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Las tres cifras **coinciden** (salvo el redondeo a 6 decimales del agente): la tabla reproduce el coste del mock. Esa comprobación es tu primera prueba de contrato de FinOps.
    - En un ticket de 4+ llamadas la **entrada de cada llamada incluye todo lo anterior**: el coste es *superlineal* en el nº de pasos. Un bucle de 6 pasos no cuesta 6 veces una llamada, sino bastante más.
    - Por eso el nº de llamadas por ticket (que ya vigilabas en el módulo 09) es también una **métrica de coste**.
    """))

    # ------------------------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · Atribución: ¿quién genera el gasto?

    El `FinOpsInstrumentor` escribe un **libro** (una fila por ticket) con las dimensiones de atribución: cliente, tier, *feature* (la intención detectada), agente y modelo, además del desglose de coste y un indicador de **coste desperdiciado** (tickets en error, `max_steps`, alucinados o en bucle). Con el libro, las preguntas de FinOps son agregaciones:
    """)
    code('''
display(led.by("feature").round(5))
display(led.by("tier").round(5))
resolved = df.status.isin(["ok", "escalated"])
print(f"coste por ticket: ${df.cost_usd.mean():.6f} · coste por ticket RESUELTO: ${df.cost_usd.sum() / resolved.sum():.6f} · gasto desperdiciado: {df.wasted_usd.sum() / df.cost_usd.sum():.1%} ({int((df.wasted_usd > 0).sum())} tickets)")
''')
    code('''
by_c = df.groupby("customer_id").cost_usd.sum().sort_values(ascending=False)
cum = by_c.cumsum() / by_c.sum()
fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
top = by_c.head(25)
axes[0].bar(range(len(top)), top.values * 1000, color=viz.PALETTE["metrics"]); ax2 = axes[0].twinx(); ax2.plot(range(len(top)), cum.head(25).values * 100, color=viz.PALETTE["traces"], marker="o", ms=3)
axes[0].set_xticks(range(0, 25, 4), [top.index[i] for i in range(0, 25, 4)], fontsize=8); axes[0].set_ylabel("coste (milésimas de USD)"); ax2.set_ylabel("% acumulado"); ax2.grid(False)
axes[0].set_title(f"Pareto de clientes: el 10 % de los clientes ({int(len(by_c) * 0.1)}) genera el {cum.iloc[int(len(by_c) * 0.1) - 1]:.0%} del gasto")
pv = df.pivot_table(index="feature", columns="tier", values="cost_usd", aggfunc="sum").fillna(0) * 1000
pv.plot.bar(stacked=True, ax=axes[1], color=[viz.PALETTE["traces"], viz.PALETTE["metrics"]], rot=15); axes[1].set_ylabel("coste (milésimas de USD)"); axes[1].set_xlabel(""); axes[1].set_title("Coste por feature y tier")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Pareto**: pocos clientes concentran mucho gasto (el tráfico sintético sigue una distribución Zipf, como la real). La pregunta de negocio es si esos clientes **también generan** ingresos proporcionales: sin atribución por cliente no puedes ni contestarla.
    - El coste por ticket **resuelto** es mayor que el coste por ticket: lo gastado en tickets fallidos o alucinados «se paga» con los resueltos. Esa es la **unidad económica** que debes seguir (y optimizar): *dinero por problema resuelto*.
    - El reparto por *feature* y *tier* orienta las decisiones (¿qué *feature* optimizar primero? ¿cuánto cuesta atender a un premium?), pero **no** es lo mismo que el reparto del tráfico.
    """))
    md("### Dónde se atribuye: métricas, logs o trazas (y la cuenta de la cardinalidad)")
    code('''
dims = {"clientes": df.customer_id.nunique(), "features": df.feature.nunique(), "modelos": 2, "tiers": df.tier.nunique(), "agentes": 1, "componentes de coste": 4}
naive_series = np.prod(list(dims.values())); good_series = np.prod([v for k, v in dims.items() if k != "clientes"])
print(dims); print(f"series de la métrica supportops.llm.cost: con customer_id como etiqueta = {naive_series:,} · sin él = {good_series:,}  ({naive_series / good_series:.0f}× menos)")
display(pd.DataFrame({"señal": ["Métricas (Prometheus)", "Logs (Loki)", "Trazas (Tempo)"], "dimensiones": ["tier · feature · modelo · agente", "cliente · ticket · coste · tokens (structured metadata)", "ticket · cliente · coste por span chat"],
                      "para qué": ["alertas, tendencias, paneles de coste agregado", "«¿cuánto ha gastado el cliente X hoy?», top-N por cliente", "«¿por qué costó tanto ESTE ticket?» (qué llamadas, qué modelo)"], "cardinalidad": ["baja y acotada", "alta, pero por línea (no por serie)", "alta, por traza (se muestrea)"]}).set_index("señal"))
''')

    # ------------------------------------------------------------------------------------------------------------- 5
    md("""
    ---
    # 5 · Caché de prompts: cuánto ahorra, cuándo no, y cómo se rompe

    Un agente reenvía en **cada** llamada el prompt de sistema (aquí ≈ 2 500 tokens de políticas) y el esquema de herramientas, y dentro de un ticket además toda la conversación previa. La **caché de prefijos** del proveedor permite pagar esa parte repetida a una fracción. El `CacheSimulator` modela las reglas (documentadas por los proveedores) de forma simplificada y determinista: mínimo cacheable, TTL de 5 min renovable con cada lectura, lectura del prefijo ya visto y escritura del resto.
    """)
    code('''
def corre(n, dur=3600.0, cache=True, prefix_fn=None, seed=SEED, faults=None, model="mock-small", ttl=300.0, tk=None):
    tk = tk or generate_tickets(n, seed=seed, duration_s=dur, fault_rates=faults)
    L = CostLedger(); fin = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=CacheSimulator(enabled=cache, min_prefix_tokens=256, ttl_s=ttl), ledger=L, prefix_key_fn=prefix_fn, loop_fn=lambda r: detect_loop_in_result(r)[0])
    run_tickets(SupportAgent(llm=MockLLM(model), system_prompt=PP, instrumentor=fin), tk)
    return L.to_frame()

tasas = [6, 12, 30, 60, 200] if FAST_DEV_RUN else [6, 12, 30, 60, 200, 800]
barrido = []
for n in tasas:
    a, b = corre(n, cache=False), corre(n, cache=True)
    barrido.append({"tickets/hora": n, "coste/ticket sin caché": a.cost_usd.mean(), "coste/ticket con caché": b.cost_usd.mean(), "ahorro": 1 - b.cost_usd.sum() / a.cost_usd.sum(), "hit ratio": b.cache_hit_ratio.mean()})
B = pd.DataFrame(barrido).set_index("tickets/hora"); display(B.round(6))
''')
    code('''
sano = corre(200, cache=True)
rota = corre(200, cache=True, prefix_fn=lambda ctx, info: ctx.ticket.ticket_id)         # el prefijo cambia en CADA petición (p. ej. una marca de tiempo al principio del prompt)
sin = corre(200, cache=False)
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4))
axes[0].plot(B.index, B["ahorro"] * 100, marker="o", color=viz.PALETTE["logs"]); axes[0].set_xscale("log"); axes[0].set_xlabel("tickets por hora (log)"); axes[0].set_ylabel("ahorro por la caché (%)"); axes[0].set_ylim(0, 100)
ax2 = axes[0].twinx(); ax2.plot(B.index, B["hit ratio"] * 100, marker="s", color=viz.PALETTE["traces"], ls="--"); ax2.set_ylabel("hit ratio (%)"); ax2.set_ylim(0, 100); ax2.grid(False); axes[0].set_title("Más tráfico = caché más caliente")
vals = {"sin caché": sin.cost_usd.sum(), "caché sana": sano.cost_usd.sum(), "caché ROTA\\n(prefijo cambiante)": rota.cost_usd.sum()}
axes[1].bar(list(vals), [v * 1000 for v in vals.values()], color=[viz.PALETTE["neutral"], viz.PALETTE["logs"], viz.PALETTE["error"]]); axes[1].set_ylabel("coste de 200 tickets (milésimas de USD)"); axes[1].set_title("Caché rota: se pierde más de la mitad del ahorro")
for i, v in enumerate(vals.values()): axes[1].text(i, v * 1000, f"${v:.4f}", ha="center", va="bottom", fontsize=9)
plt.tight_layout(); plt.show()
print(f"hit ratio sano {sano.cache_hit_ratio.mean():.0%} · roto {rota.cache_hit_ratio.mean():.0%} · coste roto / sano = {rota.cost_usd.sum() / sano.cost_usd.sum():.1f}× · roto / sin caché = {rota.cost_usd.sum() / sin.cost_usd.sum():.2f}×")
''')
    md(observe("""
    - **El ahorro crece con el tráfico y se satura** (≈ 80 %): con poco tráfico el prefijo caduca (TTL de 5 min) entre tickets y solo se aprovecha la reutilización *dentro* de cada ticket; con tráfico denso el prefijo siempre está caliente.
    - **Caché rota:** si algo cambia al principio del prompt en cada petición (una fecha, un identificador de petición, un orden de herramientas distinto), el proveedor ve un prefijo nuevo cada vez: la reutilización *entre* tickets desaparece (solo queda la de dentro de cada ticket) y la primera llamada de cada ticket **se escribe con recargo**. Resultado: el coste se multiplica por ≈ 3-4 respecto a la caché sana y se pierde más de la mitad del ahorro (el gasto vuelve a ≈ 2/3 del que tendrías sin caché, y en peticiones de una sola llamada sale más caro que no usar caché). Es el incidente de coste más traicionero porque **la calidad no cambia**.
    - Síntoma observable y barato: el **hit ratio** (`cache_read / input_total`) cae de golpe tras un despliegue. Lo vigilaremos en el panel.
    """))
    md("""
    ## 5.1 El punto de equilibrio

    Si un prefijo de `L` tokens se escribe una vez (a `p_cw`) y se lee `n − 1` veces (a `p_cr`), frente a pagarlo `n` veces a `p_in`:

    $$\\text{coste con caché} = L\\,[\\,p_{cw} + (n-1)\\,p_{cr}\\,], \\qquad \\text{coste sin caché} = L\\,n\\,p_{in} \\;\\Rightarrow\\; n^{*} = \\frac{p_{cw} - p_{cr}}{p_{in} - p_{cr}}$$

    Con los multiplicadores de laboratorio (escritura 1,25×, lectura 0,1×): `n* = (1,25 − 0,1) / (1 − 0,1) ≈ 1,28`. **Basta con reutilizar el prefijo una sola vez** para que compense; pero si **nunca** se reutiliza (`n = 1`) pagas el 25 % de más.
    """)
    code('''
pin, pcw, pcr = 1.0, 1.25, 0.10
n = np.arange(1, 11)
con = pcw + (n - 1) * pcr; sin_ = n * pin
n_star = (pcw - pcr) / (pin - pcr)
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(n, sin_ / n, marker="o", label="sin caché (coste medio por uso)", color=viz.PALETTE["neutral"]); ax.plot(n, con / n, marker="o", label="con caché (1 escritura + n−1 lecturas)", color=viz.PALETTE["logs"])
ax.axvline(n_star, color=viz.PALETTE["error"], ls=":"); ax.text(n_star + 0.1, 1.15, f"n* ≈ {n_star:.2f}", color=viz.PALETTE["error"])
ax.set_xlabel("veces que se usa el prefijo (n)"); ax.set_ylabel("coste medio por uso (× precio de entrada)"); ax.set_title("Punto de equilibrio de la caché (multiplicadores de laboratorio)"); ax.legend(); plt.show()
frias = pd.Series({"coste sin caché": 1.0, "caché fría, 1 solo uso": pcw, "caché, 2 usos": (pcw + pcr) / 2, "caché, 10 usos": (pcw + 9 * pcr) / 10})
print(frias.round(3).to_string())
''')
    md(observe("""
    - La curva con caché empieza **por encima** de la de sin caché (n = 1: el recargo de escritura) y la cruza enseguida (n* ≈ 1,3) para acabar muy por debajo.
    - La decisión de cachear es una apuesta sobre la **reutilización dentro del TTL**: para prompts que se repiten cientos de veces por hora es obvia; para una consulta rara, no. Mide el `hit ratio`, no lo supongas.
    - Los multiplicadores reales cambian por modelo (lo dice la documentación de los proveedores): recalcula `n*` con **tu** tabla de precios.
    """))

    # ------------------------------------------------------------------------------------------------------------- 6
    md("""
    ---
    # 6 · Presupuestos y topes

    Hay tres niveles de control, de más fino a más grueso:

    | Nivel | Mecanismo | Qué evita |
    |---|---|---|
    | **Ticket** | Tope de gasto por ticket (`BudgetGuard`) y **degradación de modelo** al acercarse (`DowngradeLLM`) | Un ticket que se desboca (bucle, contexto enorme) |
    | **Cliente** | Tope diario por cliente (con multiplicador por tier) | Un cliente (o un abuso) que se come el presupuesto |
    | **Periodo** | Presupuesto mensual con **burn rate** y alerta | Que el mes cierre muy por encima de lo previsto |

    Los topes son **instrumentores que rechazan *antes* de la llamada** (lanzan `LLMError(error_type="budget_exceeded")`): el agente los trata como un fallo del proveedor y no gasta nada más. Se evalúan **entre** llamadas: una llamada ya iniciada no se interrumpe, así que el gasto puede pasarse del tope por *una* llamada.
    """)
    code('''
n_c = 240 if FAST_DEV_RUN else 800
tkc = generate_tickets(n_c, seed=SEED + 1, fault_rates={**DEFAULT_FAULT_RATES, "tool_loop": 0.08})
def corre_cap(guard_fn=None, llm_fn=None, loop_guard=False):
    L = CostLedger(); fin = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, ledger=L, cache=CacheSimulator(min_prefix_tokens=256), loop_fn=lambda r: detect_loop_in_result(r)[0])
    g0 = guard_fn() if guard_fn else None
    guards = ([g0] if g0 else []) + ([LoopGuard(2)] if loop_guard else []) + [fin]          # guards FUERA, FinOps DENTRO (su coste real llega al guard)
    agent = SupportAgent(llm=llm_fn(g0) if llm_fn else None, system_prompt=PP, instrumentor=CompositeInstrumentor(*guards))
    run_tickets(agent, tkc); return L.to_frame(), g0

libre, _ = corre_cap()
normales = libre[~libre["loop"]]
CAP = float(np.quantile(normales.cost_usd, 0.99))
cap_df, g_cap = corre_cap(lambda: BudgetGuard(ILLUSTRATIVE_PRICES, per_ticket_usd=CAP))
bloq = cap_df[cap_df.budget_blocked]
falsos = bloq[~bloq["loop"]]
print(f"tope por ticket = ${CAP:.6f} (p99 de los tickets NORMALES) · tickets bloqueados: {len(bloq)} (de los cuales NO eran bucle: {len(falsos)})")
print(f"gasto total: libre ${libre.cost_usd.sum():.4f} -> con tope ${cap_df.cost_usd.sum():.4f}  ({1 - cap_df.cost_usd.sum() / libre.cost_usd.sum():.1%} menos) · coste máximo por ticket: ${libre.cost_usd.max():.5f} -> ${cap_df.cost_usd.max():.5f}")
''')
    code('''
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4))
for d, lab, col in ((libre, "sin tope", viz.PALETTE["error"]), (cap_df, "con tope", viz.PALETTE["logs"])):
    s = np.sort(d.cost_usd.values); axes[0].plot(s * 1000, 1 - np.arange(1, len(s) + 1) / len(s), label=lab, color=col, lw=2)
axes[0].set_xscale("log"); axes[0].set_yscale("log"); axes[0].set_xlabel("coste por ticket (milésimas de USD)"); axes[0].set_ylabel("fracción de tickets más caros que x"); axes[0].axvline(CAP * 1000, color=viz.PALETTE["neutral"], ls=":")
axes[0].set_title("Cola de costes (CCDF): el tope corta la cola"); axes[0].legend()
pesos = pd.Series({"bucles": libre[libre["loop"]].cost_usd.sum(), "resto desperdiciado": libre[(libre.wasted_usd > 0) & ~libre["loop"]].cost_usd.sum(), "resueltos": libre[libre.wasted_usd == 0].cost_usd.sum()})
axes[1].pie(pesos.values, labels=[f"{k}\\n${v:.4f}" for k, v in pesos.items()], colors=[viz.PALETTE["error"], viz.PALETTE["warn"], viz.PALETTE["logs"]], startangle=90, wedgeprops={"width": 0.45}); axes[1].set_title("¿En qué se gasta (sin tope)?")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El tope fijado en el **p99 de los tickets normales** recorta la cola sin tocar a casi nadie más: los bloqueados son casi todos **bucles** (los falsos positivos se cuentan aparte). Elegir el tope con datos —no «a ojo»— es lo que evita bloquear tickets legítimos.
    - Aun así el gasto de los bloqueados no es cero: el tope se evalúa **entre** llamadas, así que cada bloqueado gasta hasta el tope más una llamada.
    - Un bloqueo no es gratis: es un ticket **sin resolver** (se escala o se pide reintentar). Cuenta su coste de calidad, no solo el ahorro.
    """))
    code('''
gr_df, _ = corre_cap(None, lambda g: MockLLM("mock-large"))                                 # siempre el modelo grande
CAP_L = float(np.quantile(gr_df[~gr_df["loop"]].cost_usd, 0.99))                            # tope del modelo grande: p99 de sus tickets normales
dg_df, g_dg = corre_cap(lambda: BudgetGuard(ILLUSTRATIVE_PRICES, per_ticket_usd=CAP_L), lambda g: DowngradeLLM(MockLLM("mock-large"), MockLLM("mock-small"), g, soft_ratio=0.25))
res_ = pd.DataFrame({"modelo grande siempre": gr_df.cost_usd, "grande + degradación al pequeño al 25 % del tope": dg_df.cost_usd})
ok_ = lambda d: d.status.isin(["ok", "escalated"]).mean()
print(res_.sum().round(4).to_string(), "\\nahorro:", f"{1 - res_.iloc[:, 1].sum() / res_.iloc[:, 0].sum():.0%}", "· tickets resueltos:", f"{ok_(gr_df):.1%} -> {ok_(dg_df):.1%}", "· tickets bloqueados:", int(dg_df.budget_blocked.sum()))
''')
    md("""
    ### 6.1 El presupuesto del periodo: *burn rate*

    Como en un SLO, el presupuesto de un periodo se vigila con su **burn rate**: gasto relativo / tiempo relativo transcurrido.

    $$\\text{burn} = \\frac{S / B}{t / T}, \\qquad \\text{previsión a fin de periodo} = S \\cdot \\frac{T}{t}$$

    con `S` gasto acumulado, `B` presupuesto, `t` tiempo transcurrido y `T` duración del periodo. Un `burn = 1` es «justo en presupuesto»; `burn = 2` agota el presupuesto a mitad de periodo. Simulamos un mes (30 días, 100 tickets/día): el día 7-8 hay una oleada de bucles, el día 14 alguien cambia el modelo por defecto a uno grande y los días 19-21 se rompe la caché.
    """)
    code('''
DIAS, POR_DIA = 30, (100 if FAST_DEV_RUN else 200)
Lm, cache_m = CostLedger(), CacheSimulator(min_prefix_tokens=256)
for d in range(DIAS):
    fr = dict(DEFAULT_FAULT_RATES); fr["tool_loop"] = 0.35 if 7 <= d <= 8 else fr["tool_loop"]
    pf = (lambda ctx, info: ctx.ticket.ticket_id) if 19 <= d <= 21 else None
    fin = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=cache_m, ledger=Lm, prefix_key_fn=pf, loop_fn=lambda r: detect_loop_in_result(r)[0])
    ag = SupportAgent(llm=MockLLM("mock-large" if d >= 14 else "mock-small"), system_prompt=PP, instrumentor=fin)
    run_tickets(ag, generate_tickets(POR_DIA, seed=100 + d, duration_s=86400, fault_rates=fr, start_s=SIM_EPOCH_S + d * 86400))
dm = Lm.to_frame(); dm["dia"] = ((dm.t_start - SIM_EPOCH_S) // 86400).astype(int)
g = dm.groupby("dia").agg(coste=("cost_usd", "sum"), tickets=("ticket_id", "count"), hit=("cache_hit_ratio", "mean")); g["cpt"] = g.coste / g.tickets
esperado_mes = g.coste.iloc[:7].mean() * DIAS
POOL = BudgetPool(limit_usd=round(esperado_mes * 1.3, 4), period_s=DIAS * 86400.0)          # presupuesto = 130 % del gasto esperado
cum, burn, fore = [], [], []
for d in range(DIAS):
    POOL.add(g.coste.iloc[d]); el = (d + 1) * 86400.0
    cum.append(POOL.spent_usd); burn.append(POOL.burn_rate(el)); fore.append(POOL.forecast_usd(el))
dia_alerta = cost_drift_alert(list(g.cpt), baseline_n=7, ratio=1.6, persist=2)
dia_burn2 = next((d for d, b in enumerate(burn) if b >= 2.0), None)
print(f"presupuesto mensual ${POOL.limit_usd} · gasto del mes ${POOL.spent_usd:.2f} · alerta de desvío (coste/ticket ≥ 1,6× la base, 2 días seguidos) el día {dia_alerta} · burn rate ≥ 2 el día {dia_burn2}")
''')
    code('''
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
axes[0].semilogy(g.index, g.cpt * 1000, marker="o", ms=3, color=viz.PALETTE["metrics"]); axes[0].set_xlabel("día"); axes[0].set_ylabel("coste por ticket (milésimas de USD, log)")
for d0, d1, txt, col in ((7, 8, "bucles", viz.PALETTE["warn"]), (14, 29, "modelo grande", viz.PALETTE["error"]), (19, 21, "caché rota", viz.PALETTE["traces"])):
    axes[0].axvspan(d0 - 0.4, d1 + 0.4, color=col, alpha=0.12)
axes[0].axvline(dia_alerta, color="k", ls="--"); axes[0].text(dia_alerta + 0.3, g.cpt.min() * 1000 * 1.1, "alerta de desvío", fontsize=8); axes[0].set_title("Coste por ticket: tres incidentes")
axes[1].plot(range(DIAS), cum, color=viz.PALETTE["metrics"], lw=2, label="gasto acumulado"); axes[1].plot(range(DIAS), [POOL.limit_usd * (d + 1) / DIAS for d in range(DIAS)], color=viz.PALETTE["neutral"], ls=":", label="ritmo lineal permitido")
axes[1].axhline(POOL.limit_usd, color=viz.PALETTE["error"], ls="--", label="presupuesto"); axes[1].set_xlabel("día"); axes[1].set_ylabel("USD"); axes[1].legend(fontsize=8); axes[1].set_title("Presupuesto mensual")
axes[2].plot(range(DIAS), burn, color=viz.PALETTE["traces"], lw=2, label="burn rate"); axes[2].axhline(1, color=viz.PALETTE["neutral"], ls=":"); axes[2].axhline(2, color=viz.PALETTE["error"], ls="--")
axes[2].set_xlabel("día"); axes[2].set_ylabel("burn rate (1 = justo en presupuesto)"); ax3 = axes[2].twinx(); ax3.plot(range(DIAS), np.array(fore) / POOL.limit_usd * 100, color=viz.PALETTE["metrics"], ls="--"); ax3.set_ylabel("previsión a fin de mes (% del presupuesto)"); ax3.grid(False); axes[2].set_title("Burn rate y previsión")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La **oleada de bucles** (días 7-8) sube el coste por ticket un ~30 %: **no** supera el umbral de 1,6× y la alerta de desvío no salta. Es un desvío real pero pequeño: lo cazarías con la métrica de **coste desperdiciado**, no con la de coste por ticket.
    - El **cambio de modelo** (día 14) multiplica el coste por ~12: la alerta salta al segundo día (con `persist=2`) y el *burn rate* se dispara. La **previsión a fin de mes** supera varias veces el presupuesto *antes* de que acabe el mes: ese es el valor de vigilar el ritmo, no solo el total.
    - La **caché rota** (días 19-21) añade un escalón encima del anterior: el coste por ticket sube otro ~30 % y el *hit ratio* cae. Sin ese panel, quedaría oculto tras el incidente mayor.
    - Los umbrales son una decisión: `ratio` alto = pocos falsos positivos pero más retraso; `persist` largo = lo mismo. Calíbralos con tu línea base (el proyecto lo hace).
    """))

    # ------------------------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Bucles caros: detectarlos y cortarlos

    Un **bucle de herramientas** es el caso extremo de la cola: el modelo repite la misma llamada sin converger hasta `max_steps`, con el contexto creciendo en cada vuelta. Dos enfoques complementarios:

    - **Post-hoc**: mirar la ejecución terminada y buscar ≥ 3 llamadas **idénticas** (herramienta + argumentos). Barato y preciso, pero el dinero ya se gastó.
    - **En línea** (`LoopGuard`): rechazar la llamada idéntica nº `max_repeats + 1` antes de ejecutarla **y abortar la siguiente llamada al LLM** (cortar solo la herramienta no basta: el modelo seguiría pidiéndola y gastando tokens).

    Sin capturar argumentos (privacidad), en trazas solo ves el **nombre** de la herramienta repetido: TraceQL `{ span.gen_ai.operation.name = "execute_tool" } | count() >= 4` encuentra trazas con 4 o más herramientas (un proxy más grosero).
    """)
    code('''
flags = [detect_loop_in_result(r) for r in results]
real = np.array(["tool_loop" in r.injected_faults for r in results]); det = np.array([f[0] for f in flags])
tp, fp, fn = (real & det).sum(), (~real & det).sum(), (real & ~det).sum()
print(f"post-hoc (≥3 llamadas idénticas): verdaderos positivos {tp} · falsos positivos {fp} · falsos negativos {fn} · precisión {tp / max(tp + fp, 1):.0%} · exhaustividad {tp / max(tp + fn, 1):.0%}")
cw = pd.DataFrame({"loop": real, "cost": df.cost_usd.values, "n_llm": df.n_llm.values})
print(f"coste medio: ticket en bucle ${cw[cw['loop']].cost.mean():.5f} vs normal ${cw[~cw['loop']].cost.mean():.5f}  ({cw[cw['loop']].cost.mean() / cw[~cw['loop']].cost.mean():.1f}×) · los bucles son el {real.mean():.1%} de los tickets y el {cw[cw['loop']].cost.sum() / cw.cost.sum():.1%} del gasto")

Lg, Lf = CostLedger(), CostLedger()
lg = LoopGuard(max_repeats=2)
run_tickets(SupportAgent(system_prompt=PP, instrumentor=CompositeInstrumentor(FinOpsInstrumentor(ILLUSTRATIVE_PRICES, ledger=Lg, loop_fn=lambda r: detect_loop_in_result(r)[0]), lg)), tickets)
g_df = Lg.to_frame()
print(f"con LoopGuard(2): gasto ${df.cost_usd.sum():.4f} -> ${g_df.cost_usd.sum():.4f} ({1 - g_df.cost_usd.sum() / df.cost_usd.sum():.1%} menos) · cortes: {len(lg.tripped)} · cortes en tickets que NO eran bucle: {sum(1 for t in lg.tripped if 'tool_loop' not in next(r for r, tk_ in zip(results, tickets) if tk_.ticket_id == t).injected_faults)}")
''')
    code('''
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
axes[0].bar(["normal", "en bucle"], [cw[~cw["loop"]].cost.mean() * 1000, cw[cw["loop"]].cost.mean() * 1000], color=[viz.PALETTE["logs"], viz.PALETTE["error"]]); axes[0].set_ylabel("coste medio (milésimas de USD)"); axes[0].set_title("Un ticket en bucle cuesta…")
axes[1].bar(["post-hoc\\nprecisión", "post-hoc\\nexhaustividad"], [tp / max(tp + fp, 1) * 100, tp / max(tp + fn, 1) * 100], color=viz.PALETTE["traces"]); axes[1].set_ylim(0, 105); axes[1].set_ylabel("%"); axes[1].set_title("Detección post-hoc")
axes[2].bar(["sin guarda", "LoopGuard(2)"], [df.cost_usd.sum() * 1000, g_df.cost_usd.sum() * 1000], color=[viz.PALETTE["error"], viz.PALETTE["logs"]]); axes[2].set_ylabel("gasto del lote (milésimas de USD)"); axes[2].set_title("Efecto de cortar en línea")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Una pequeña fracción de los tickets (los bucles: ≈ 4 % aquí) tiene un coste **medio varias veces mayor** y pesa claramente más que su proporción en el gasto: un FinOps que mire solo la media nunca lo verá.
    - La detección post-hoc por llamadas idénticas es muy precisa; **el falso positivo** de las guardas en línea aparece cuando una herramienta se repite **legítimamente** con los mismos argumentos (p. ej. consultar el estado de un pedido tras un reintento): por eso `max_repeats` no debe ser 1 y conviene registrar cada corte (`loop_detected`) para auditarlo.
    - Cortar en línea evita el gasto restante del bucle; el ticket queda **sin resolver** (se escala). Es el mismo trade-off de la sección 6: dinero frente a calidad.
    """))

    # ------------------------------------------------------------------------------------------------------------- 8
    md("""
    ---
    # 8 · El coste como telemetría OpenTelemetry

    El `FinOpsInstrumentor` publica el coste en las tres señales (todos los nombres propios llevan prefijo `supportops.`; **no** hay un atributo de coste en la spec GenAI):

    | Señal | Qué | Notas |
    |---|---|---|
    | **Span `chat`** | `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens` (spec, *Development*) y `supportops.finops.cost_usd` | Explica «por qué costó tanto ESTE ticket» |
    | **Span raíz** `invoke_agent` | `supportops.finops.cost_usd`, `.cache_hit_ratio`, `.wasted`, `.feature` | Suma de sus hojas `chat` (comprobado en las pruebas) |
    | **Métricas** (baja cardinalidad) | `supportops.llm.cost` (USD, por componente), `supportops.llm.tokens` (por tipo de token), `supportops.ticket.cost` (histograma), `supportops.ticket.cost.wasted`, `supportops.tickets`; presupuesto: `supportops.budget.spent/limit/burn_rate` | Etiquetas: modelo, *feature*, tier, agente |
    | **Log** `ticket costed` | `supportops.customer.id`, `supportops.ticket.id`, `supportops.finops.cost_usd` + `trace_id` | Atribución por cliente en Loki |

    > 💡 **El coste se deriva, los tokens son la verdad.** Guarda siempre los tokens (y la versión de la tabla de precios): si cambian los precios puedes **reponderar** el histórico. Lo demostramos con el libro: el mismo gasto con otra tabla.
    """)
    code('''
alt = PriceTable({"mock-small": ModelPrice(0.50, 2.00, 0.05, 0.625), "mock-large": ModelPrice(2.00, 10.00, 0.20, 2.50)}, label="ILUSTRATIVA B")
def repondera(d, tabla):
    return sum(tabla.cost(r.model, Usage4(int(r.input_total), int(r.output), int(r.cache_read), int(r.cache_write))).total for r in d.itertuples())
print(f"el mismo lote ({len(dm):,} tickets): tabla A ${repondera(dm, ILLUSTRATIVE_PRICES):.2f} · tabla B ${repondera(dm, alt):.2f}   (misma telemetría de tokens, otros precios)")
with_trace = setup_telemetry("supportops-agent", mode="memory", set_global=False)
fin_t = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=CacheSimulator(min_prefix_tokens=256), handle=with_trace, loop_fn=lambda r: detect_loop_in_result(r)[0])
run_tickets(SupportAgent(system_prompt=PP, instrumentor=CompositeInstrumentor(OTelInstrumentor(with_trace, emit_metrics=False), fin_t)), tickets[:30])
sp = with_trace.span_records(); ch = [s for s in sp if s["name"].startswith("chat")]; roots = [s for s in sp if s["name"].startswith("invoke_agent")]
print(f"spans: {len(sp)} · suma de cost_usd en hojas chat = ${sum(s['attributes'].get('supportops.finops.cost_usd', 0) for s in ch):.6f} · en raíces invoke_agent = ${sum(s['attributes'].get('supportops.finops.cost_usd', 0) for s in roots):.6f}  (iguales: SOLO se cuenta una vez)")
pts = pd.DataFrame(with_trace.metric_points()); display(pts[pts.name.str.startswith("supportops")].groupby("name").agg(series=("name", "size")).T)
print("¿alguna serie lleva customer.id como etiqueta?", any("supportops.customer.id" in p["attributes"] for p in with_trace.metric_points()))
''')

    # ------------------------------------------------------------------------------------------------------------- 9
    md("""
    ---
    # 9 · Panel de FinOps y alerta de desvío (stack real)

    El dashboard **«13 · FinOps»** (`stack/grafana/dashboards/13-finops.json`, uid `finops`, generado con `supportops.dashkit`) tiene:

    | Panel | Consulta |
    |---|---|
    | Coste por hora y por ticket | `sum(increase(supportops_llm_cost_USD_total[1h]))` · `sum(rate(supportops_ticket_cost_USD_sum[10m])) / sum(rate(supportops_ticket_cost_USD_count[10m]))` |
    | Coste por modelo / *feature* / tier | `sum by (gen_ai_request_model) (rate(supportops_llm_cost_USD_total[$__rate_interval]))` |
    | **Hit ratio de la caché** | `sum(rate(supportops_llm_tokens_total{gen_ai_token_type="cache_read"}[...])) / sum(rate(supportops_llm_tokens_total{gen_ai_token_type=~"input\\|cache_read\\|cache_write"}[...]))` |
    | Gasto desperdiciado | `sum(rate(supportops_ticket_cost_wasted_USD_total[...])) / sum(rate(supportops_llm_cost_USD_total[...]))` |
    | Presupuesto y *burn rate* | `supportops_budget_burn_rate_ratio`, `supportops_budget_spent_USD` / `supportops_budget_limit_USD` |
    | **Desvío** (la alerta) | coste por ticket (10 min) / el de hace 1 h, con umbral 1,6 |
    | Top clientes (Loki) | `topk(10, sum by (supportops_customer_id) (sum_over_time({service_name="supportops-agent"} \\|= "ticket costed" \\| unwrap supportops_finops_cost_usd [$__range])))` |
    | Tickets caros / bucles (Tempo) | `{ name =~ "invoke_agent.*" && span.supportops.finops.cost_usd > 0.002 }` · `{ span.gen_ai.operation.name = "execute_tool" } \\| count() >= 4` |
    """)
    code('''
if LIVE:
    live_ledger = CostLedger(); cache_l = CacheSimulator(min_prefix_tokens=256)
    pool_l = BudgetPool(limit_usd=0.5, period_s=3600.0); t_start = time.time()
    pool_l.register_metrics(TEL.meter(), lambda: time.time() - t_start + 60)
    n_l = 60 if FAST_DEV_RUN else 240
    sano = generate_tickets(n_l, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, start_s="live", duration_s=600)
    def corre_live(tk, model, pf=None):
        fin = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=cache_l, ledger=live_ledger, handle=TEL, prefix_key_fn=pf, loop_fn=lambda r: detect_loop_in_result(r)[0])
        run_tickets(SupportAgent(llm=MockLLM(model), system_prompt=PP, instrumentor=CompositeInstrumentor(OTelInstrumentor(TEL, emit_metrics=False), BudgetGuard(ILLUSTRATIVE_PRICES, pool=pool_l), fin)), tk)
    corre_live(sano[: n_l // 2], "mock-small")                                              # primera mitad: normal
    corre_live(sano[n_l // 2:], "mock-large")                                               # segunda mitad: alguien cambia el modelo por defecto
    TEL.force_flush(); print(f"enviados {len(live_ledger.rows)} tickets · gasto ${pool_l.spent_usd:.4f} de ${pool_l.limit_usd} · espera ~20-30 s a que Tempo/Prometheus lo indexen")
else:
    print("Sin stack: arráncalo con `docker compose --profile core --profile metrics up -d` (desde stack/) y vuelve a ejecutar.")
''')
    code('''
if LIVE:
    time.sleep(25)
    def prom(q):
        try: return backends.prom_query(q)
        except Exception as e: return [{"metric": {"error": type(e).__name__}, "value": [0, "nan"]}]
    por_modelo = prom('sum by (gen_ai_request_model) (supportops_llm_cost_USD_total)')
    display(pd.DataFrame([{**x["metric"], "USD": float(x["value"][1])} for x in por_modelo]))
    cpt = prom("sum(rate(supportops_ticket_cost_USD_sum[10m])) / sum(rate(supportops_ticket_cost_USD_count[10m]))")
    print("coste por ticket (10 min):", [float(x["value"][1]) for x in cpt][:1])
    try:
        top = backends._get(backends._base("loki") + "/loki/api/v1/query", {"query": 'topk(5, sum by (supportops_customer_id) (sum_over_time({service_name="supportops-agent"} |= "ticket costed" | unwrap supportops_finops_cost_usd [30m])))'})
        display(pd.DataFrame([{**x["metric"], "USD": float(x["value"][1])} for x in top["data"]["result"]]))
    except Exception as e:
        print("Loki no disponible:", type(e).__name__)
    t_ = backends.tempo_search('{ name =~ "invoke_agent.*" && span.supportops.finops.cost_usd > 0.002 }', minutes=30, limit=20).get("traces", [])
    print("trazas de tickets caros (> $0,002):", len(t_))
''')
    md("""
    ## 9.1 La alerta de desvío

    La regla compara el coste por ticket de los últimos 10 min con el de **hace 1 hora** y dispara si lo supera ×1,6 durante 5 min (`finops_alert_rule_json`). Es la versión de producción de `cost_drift_alert` (que usamos sobre series ya agregadas): misma idea (razón frente a línea base + persistencia), ahora evaluada por Grafana sobre Prometheus.
    """)
    code('''
rule = finops_alert_rule_json(folder_uid="<uid-de-la-carpeta>", ratio=1.6, for_="5m")
print(json.dumps({k: rule[k] for k in ("title", "ruleGroup", "for", "condition")}, ensure_ascii=False))
print("consulta:", rule["data"][0]["model"]["expr"][:140], "…")
if LIVE:
    try:
        folders = backends.grafana_api("/api/folders"); fuid = next((f["uid"] for f in folders if "Curso" in f["title"]), folders[0]["uid"])
        r = backends.grafana_post("/api/v1/provisioning/alert-rules", finops_alert_rule_json(fuid))
        print("regla creada en Grafana:", r.get("uid"), r.get("title"))
    except Exception as e:
        print("no se pudo crear la regla (¿ya existe o la API cambió?):", str(e)[:140])
''')
    md(observe("""
    - En el panel de **coste por modelo** aparece `mock-large` solo en la segunda mitad: el cambio de modelo es visible **a primera vista**; el panel de desvío cruza el umbral 1,6 y, tras 5 min, la regla pasa a *Firing*.
    - El libro (logs) permite contestar la pregunta de negocio «¿quién ha gastado más?» sin tocar la cardinalidad de las métricas; los tickets caros salen en Tempo con su cascada.
    - Recuerda que **todo está en precios ilustrativos**: los valores absolutos del panel no significan nada; sí las **proporciones** y la **forma** de las curvas.
    """))

    # ------------------------------------------------------------------------------------------------------------- prod
    md("""
    ---
    # 🏭 En producción

    - **La disciplina FinOps aplicada a IA** (FinOps Foundation, *Optimizing GenAI Usage: A FinOps Perspective on Cost, Performance, and Efficiency*) aplica a la IA el ciclo FinOps habitual de la nube (informar, optimizar y operar): **visibilidad y asignación** del gasto (¿quién lo genera?), **optimización** (caché, modelo adecuado, límites) y **operación continua** (presupuestos, alertas). Este módulo implementa esas tres cosas con telemetría.
    - **Las plataformas de observabilidad de LLM** (Datadog, Langfuse, Helicone, LangSmith…) calculan coste a partir de tokens y tablas de precios del modelo, igual que aquí; la diferencia es quién mantiene la tabla. Verifica siempre contra tu factura real: la **reconciliación** mensual (telemetría vs factura del proveedor) es la prueba definitiva.
    - **Quién paga qué**: en SaaS multi-tenant el coste de IA se imputa por tenant (*showback/chargeback*): necesitas el identificador de tenant en spans y logs y una política de retención acorde (módulo 18/20).
    - **Prompt caching en la práctica**: la documentación de los proveedores insiste en poner el contenido **estable al principio** (herramientas, sistema, documentos) y lo **variable al final**; cambiar una definición de herramienta o el orden invalida la caché de ese nivel y de los siguientes.
    - **Costes del propio stack**: la telemetría de coste también cuesta (cada span extra, cada serie). El módulo 18 trata el presupuesto de observabilidad.
    """)

    md(box("elite", "Secretos de la élite", """
    1. **La entrada incluye la caché… según quién.** La spec GenAI define `gen_ai.usage.input_tokens` como el total (con caché); la API de Anthropic devuelve `input_tokens` **sin** caché y suma aparte `cache_read`/`cache_creation`. Copiar el campo sin normalizar infravalora la entrada y rompe el invariante `cache_read + cache_write ≤ input`. Valida ese invariante en una prueba de contrato (`Usage4` lo exige).
    2. **Los multiplicadores de caché no son constantes.** Escritura 1,25× o 2× según el TTL, lectura 0,1× o menos según el modelo y mínimos cacheables de 512 a 4 096 tokens según el modelo (documentación de *prompt caching* de Anthropic). Hardcodear «0,1×» es un bug latente: pon los multiplicadores **en la tabla** y versiona la tabla.
    3. **La caché rota no cambia la calidad y multiplica el coste.** Una marca de tiempo, un id de petición o un orden de herramientas no determinista al principio del prompt hace que cada petición escriba un prefijo nuevo (con recargo) y nadie lo lea: en la simulación, 3-4× el coste sano, y más caro que no usar caché en las peticiones de una sola llamada. Vigila el **hit ratio** como una SLI: una caída brusca tras un despliegue es un incidente de coste.
    4. **La unidad económica es el ticket resuelto.** Coste por llamada o por ticket oculta el desperdicio (errores, alucinaciones, bucles). Sigue `coste / ticket resuelto` y la fracción desperdiciada.
    5. **Vigila el p99 y la concentración, no la media.** Los bucles y los reintentos forman la cola larga; una pequeña fracción de tickets concentra una fracción desproporcionada del gasto (curva de concentración).
    6. **El presupuesto se vigila como un SLO.** `burn = (S/B)/(t/T)`; la previsión a fin de periodo avisa **antes** de gastar. Un tope por ticket evita el desastre local pero **se evalúa entre llamadas**: se paga hasta el tope más una llamada; y un bloqueo es un ticket sin resolver (calidad), así que degrada de modelo antes de bloquear.
    7. **Los tokens son la fuente de verdad; el coste, un derivado.** Guarda tokens (y la versión de la tabla de precios en un atributo) y reprecia a posteriori; si guardas solo dólares, no puedes corregir una tabla errónea ni simular otro proveedor.
    8. **Cardinalidad:** `customer_id` como etiqueta de métrica multiplica las series ×N clientes (en la sección 4: 69 clientes → 69× más series). Atribuye por cliente con **logs/atributos de span** y usa las métricas para agregados (modelo, *feature*, tier). Y cuenta el coste **solo en las hojas** (módulo 11) para no duplicar.
    9. **El punto de equilibrio de la caché depende del TTL: con 1 h necesitas ≥ 3 usos.** Con escritura `w`, lectura `r` y precio de entrada 1, cachear `n` usos cuesta `w + (n−1)·r` frente a `n` sin caché ⇒ `n* = (w−r)/(1−r)`. Con los multiplicadores documentados por Anthropic: TTL 5 min (`w=1,25`, `r=0,1`) ⇒ `n* ≈ 1,28`; TTL 1 h (`w=2`) ⇒ `n* ≈ 2,11`, es decir, con 2 usos pagas `2,1` frente a `2` (≈ 5 % más caro) y con 3 usos `2,3` frente a `3` (−23 %). Elegir el TTL de 1 h «por si acaso» en un prefijo que se reutiliza poco es dinero perdido. *Fuente: multiplicadores de la documentación de* prompt caching *(consultada el 16-oct-2026); el cálculo es reproducible con la fórmula de la sección 4.*
    10. **Las escrituras de caché se cobran distinto según el TTL y la API las desglosa.** La respuesta incluye `cache_creation` con `ephemeral_5m_input_tokens` y `ephemeral_1h_input_tokens` además del total `cache_creation_input_tokens`, y la entrada total es `cache_read + cache_creation + input_tokens`. Si tu libro guarda un único `cache_write`, no puedes reconciliar la factura cuando mezclas TTLs: guarda los dos campos y valida que suman el total. *Fuente: documentación de* prompt caching *de Anthropic.*
    11. **Más gasto compra calidad, y por eso el coste solo no es una métrica de salud.** Anthropic midió que los agentes consumen ≈ 4× los tokens de un chat y los sistemas multi-agente ≈ 15×, y que el uso de tokens por sí solo explicaba el 80 % de la varianza de rendimiento en su evaluación BrowseComp. Un coste por ticket que sube con la calidad que sube puede ser sano; uno que sube con la calidad plana es el desperdicio de los bucles. Grafica **coste frente a calidad** (módulos 14-15), no el coste a solas. *Fuente: Anthropic Engineering, «How we built our multi-agent research system» (2025).*
    """))

    md(box("warn", "⚠️ Errores comunes", """
    - **Presentar los precios de ejemplo como reales.** Una tabla ilustrativa en un panel de dirección se convierte en «la factura»: etiquétala, versiona y reconcilia con la factura del proveedor.
    - **Sumar `gen_ai.usage.*` de todos los spans** (raíz + hojas): doble contabilidad (módulos 11 y 13).
    - **Etiquetar métricas con `customer_id`/`ticket_id`.**
    - **Fijar el tope por ticket «a ojo»**: demasiado bajo bloquea tickets legítimos; elígelo con datos (p. ej. p99 de los normales) y mide los falsos bloqueos.
    - **Cortar solo la herramienta en un bucle** y dejar que el LLM siga llamando: el gasto de tokens continúa.
    - **Medir el ahorro de la caché con tráfico de laboratorio denso** y esperarlo en producción con poco tráfico (TTL de 5 min).
    - **Cambiar el modelo o el prompt sin vigilar el coste por ticket** durante las primeras horas.
    - **Olvidar la caché en las previsiones**: un prompt largo sin caché es la partida de coste dominante.
    """))

    # ------------------------------------------------------------------------------------------------------------- autoeval
    md("""
    ---
    # Autoevaluación
    """)
    md(details("1 · (Cálculo) Una llamada tiene `input_tokens = 400` (API estilo Anthropic), `cache_read_input_tokens = 2 400` y `cache_creation_input_tokens = 100`, y 200 tokens de salida. Con precios de entrada 3, salida 15, lectura 0,3 y escritura 3,75 (USD/M), ¿cuál es el total de entrada según la spec y cuánto cuesta?",
               "Total de entrada (spec) = 400 + 2 400 + 100 = **2 900**; no cacheada `u = 400`. Coste = (400·3 + 2 400·0,3 + 100·3,75 + 200·15) / 10⁶ = (1 200 + 720 + 375 + 3 000) / 10⁶ = **0,005295 USD**. Si se copiase `input_tokens = 400` como entrada total y se calculase `u = 400 − 2 400 − 100`, saldría un valor negativo: el invariante lo detecta."))
    md(details("2 · (Cálculo) Prefijo de 2 000 tokens, precio de entrada 1, escritura 1,25 y lectura 0,1 (unidades relativas). ¿Cuánto cuesta usarlo 1, 2 y 10 veces con caché frente a sin caché?",
               "Con caché: n=1 → 2 000·1,25 = **2 500** (sin caché 2 000: +25 %); n=2 → 2 000·(1,25+0,1) = **2 700** (sin caché 4 000: −32,5 %); n=10 → 2 000·(1,25+9·0,1) = **4 300** (sin caché 20 000: −78,5 %). Equilibrio `n* = (1,25 − 0,1)/(1 − 0,1) ≈ 1,28`."))
    md(details("3 · (Cálculo) Presupuesto mensual 3 000 USD. A los 6 días has gastado 900 USD. ¿Burn rate y previsión a fin de mes? ¿Alertarías?",
               "`burn = (900/3 000)/(6/30) = 0,30/0,20 = 1,5`; previsión = 900·30/6 = **4 500 USD (150 % del presupuesto)**. Sí: aunque aún no se ha superado el presupuesto, a este ritmo se agota hacia el día 20. Un `burn` sostenido ≥ 1 ya merece aviso; ≥ 2 (agota a mitad de periodo) merece *page*."))
    md(details("4 · (Diagnóstico) El coste por ticket se duplica de un día para otro, pero los tokens por ticket no cambian. ¿Qué miras y qué hipótesis tienes?",
               "Si los tokens no cambian y el coste sí, cambió el **precio efectivo**: (a) se cambió el modelo (mira `gen_ai.response.model` y el coste por modelo; nuestro `mock-large` es ~12× más caro), (b) cambió la tabla de precios o los multiplicadores, o (c) bajó el hit ratio (misma entrada, pero ahora se paga a precio normal o con recargo de escritura). Compara el desglose de coste por componente y el *hit ratio*."))
    md(details("5 · (Diagnóstico) Tras un despliegue el hit ratio pasa del 95 % al 12 % y el coste sube ×3, sin errores ni cambios de calidad. ¿Causa más probable y cómo la confirmas?",
               "Se ha invalidado el prefijo cacheable: algo variable (marca de tiempo, id, orden de herramientas, un campo nuevo) está **al principio** del prompt o de las definiciones de herramientas. Confirmas comparando el prompt/definiciones entre versiones (¿difieren entre peticiones?) y mirando `cache_write` alto con `cache_read` ≈ 0 en los spans `chat`. Arreglo: mover lo variable al final del prompt."))
    md(details("6 · (Transferencia) Diseñas el FinOps de un asistente RAG multi-tenant (recuperación + reranker + generador). ¿Qué dimensiones usarías en métricas, cuáles en logs/spans y qué unidad económica seguirías?",
               "Métricas: modelo, componente (retriever/reranker/generator), tier del tenant, *feature*, tipo de token; coste por componente. Logs/spans: `tenant_id`, `request_id`, tokens y coste por llamada (para *showback* por tenant y depurar tickets caros). Unidad económica: coste por **consulta respondida con éxito** (con fundamentación), no por llamada; añade tokens de recuperación y el coste de la base vectorial si es relevante."))
    md(details("7 · (Transferencia) ¿Cómo adaptarías `LoopGuard` si una herramienta se llama legítimamente varias veces con los mismos argumentos (p. ej. sondeo del estado de un trabajo asíncrono)?",
               "Que la clave de repetición incluya algo que **cambie** entre llamadas legítimas (un contador o el estado devuelto) o excluir esa herramienta; subir `max_repeats`; o medir progreso en lugar de repetición (¿el resultado cambia?). Siempre registrar cada corte como `loop_detected` para medir los falsos positivos."))

    md("""
    ---
    # Referencias

    - Anthropic, *Prompt caching* (documentación de la plataforma): campos `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`; multiplicadores de escritura/lectura; TTL; mínimos cacheables por modelo; qué invalida la caché — <https://platform.claude.com/docs/en/build-with-claude/prompt-caching> (y su página de precios, que **cambia**: consúltala siempre).
    - OpenTelemetry, *GenAI semantic conventions* (estado Development): `gen_ai.usage.input_tokens` (incluye caché), `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens` y métricas `gen_ai.client.inference.usage.*` — <https://github.com/open-telemetry/semantic-conventions-genai> (`docs/gen-ai/`).
    - FinOps Foundation, *Optimizing GenAI Usage: A FinOps Perspective on Cost, Performance, and Efficiency* — grupo de trabajo FinOps for AI, licencia CC BY 4.0; <https://www.finops.org/wg/optimizing-genai-usage/> (confirmada su existencia y título por búsqueda web; **no** se leyó el texto completo: no atribuimos cifras suyas al curso).
    - Google, *The Site Reliability Workbook*, cap. «Alerting on SLOs» (burn rate y alertas de múltiples ventanas, base de nuestra analogía) — <https://sre.google/workbook/alerting-on-slos/>
    - Anthropic Engineering, *How we built our multi-agent research system* (consumo de tokens de agentes y sistemas multi-agente) — <https://www.anthropic.com/engineering/multi-agent-research-system>
    - Grafana Labs, *LogQL* (`unwrap`, `sum_over_time`, `topk`) y *TraceQL* (`count()`) — <https://grafana.com/docs/loki/latest/query/> · <https://grafana.com/docs/tempo/latest/traceql/>
    """)

    nb.save(out)



# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "13_proyecto_costes_finops.ipynb", "Proyecto 13 · Panel de FinOps: coste por ticket, presupuesto y alerta de desvío")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 13 · Panel de FinOps con coste por ticket, presupuesto y alerta de desvío

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (todo se evalúa en memoria). Opcional: `core` + `metrics` para ver tu panel funcionando (paso final) |
    | **RAM aproximada** | < 500 MB |
    | **Prerrequisitos** | Lección `13_costes_finops`, módulo 10 (dashboards como código con `supportops.dashkit`) y proyecto 11 (cascadas y costes por agente) |
    | **Conexión** | Convierte la telemetría de SupportOps en **control financiero**: cuánto cuesta cada ticket, quién lo genera, cuándo nos pasamos y cómo nos enteramos antes de que llegue la factura |

    > {PRICE_BANNER}

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Dirección pide tres cosas antes de aprobar el presupuesto de IA del trimestre:

    1. **Un número fiable de coste por ticket resuelto**, con quién lo genera (cliente, tier, *feature*).
    2. **Un tope** que evite que un solo ticket (un bucle) gaste una barbaridad, sin bloquear a los tickets normales.
    3. **Una alerta de desvío** que salte en minutos —no a fin de mes— si el coste por ticket se dispara (alguien cambió el modelo, se rompió la caché…), y un **panel** que lo muestre.

    ## Datos

    Todo sintético y determinista (semilla 42, `mock`, tiempo simulado, **precios ilustrativos**): el **Paso 0** ejecuta 240 tickets con un 6 % de bucles de herramientas y un prompt de sistema largo (≈ 2 500 tokens), y construye el **libro de costes** (`LEDGER`: una fila por ticket) con el `FinOpsInstrumentor` de la lección. También genera una **serie de coste por ticket** por minuto de un incidente de 90 min (a partir del minuto 60 alguien cambia el modelo por defecto). Cadena de datos: stack local (opcional) → memoria.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `cost_breakdown` | 7 vectores: semántica de subconjuntos de caché, estilo Anthropic, sin multiplicadores, invariantes y modelo desconocido | 7/7 |
    | R2 | `attribution` | % del gasto del 5 % de clientes con más coste, coste por ticket por tier, coste por ticket **resuelto**, gasto desperdiciado y reparto por *feature* | exacto (tol. 1e-9) |
    | R3 | `PerTicketCap` | Con `CAP_USD`: 0 falsos bloqueos, bloquea todos los bucles que lo superan, coste máximo ≤ tope + 1 llamada | 3/3 |
    | R4 | `loop_report` | Detecta los bucles inyectados con precisión y exhaustividad ≥ 0,95 y calcula el coste desperdiciado | ≥ 0,95 / ± 2 % |
    | R5 | `drift_alert` | Sin falsa alarma en la línea base, detecta el incidente en ≤ 4 min, ignora picos de 2 puntos y rachas rotas por huecos | 4/4 |
    | R6 | `build_finops_dashboard` | `lint` limpio y las 8 consultas clave (coste por ticket p95, coste por modelo, caché, desperdicio, burn rate, desvío, Loki por cliente, Tempo de tickets caros) | 8/8 |

    > 📏 Los umbrales salen de la solución de referencia y se comprobaron con las semillas 42, 7 y 99 (las cifras exactas del R2 son las de la semilla 42, fija en el notebook). El tiempo es simulado: nada depende de tu máquina.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_13.replace("STACK = check_stack(\"core+metrics\")", "STACK = check_stack([])").replace("LIVE = not STACK.degraded", "LIVE = False") + '''
from supportops.dashkit import Dashboard, lint, prom, loki, tempo, timeseries, stat, bargauge, traces_table, logs, table, thresholds
from supportops.pricing import cost_usd
''')

    md("""
    ## Paso 0 · Los datos (te lo damos hecho)

    El sistema de partida ejecuta 240 tickets con el agente de SupportOps **sin guardas** (para medir el coste «libre», incluidos los bucles) y a la vez construye el libro de costes con caché (`CacheSimulator`) y los precios ilustrativos.
    """)
    code('''
TK = generate_tickets(240, seed=SEED, fault_rates={**DEFAULT_FAULT_RATES, "tool_loop": 0.06})
_led = CostLedger()
_fin = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=CacheSimulator(min_prefix_tokens=256), ledger=_led, loop_fn=lambda r: detect_loop_in_result(r)[0])
RES_FREE = run_tickets(SupportAgent(system_prompt=PP, instrumentor=_fin), TK)           # agente libre: cada AgentResult.cost_usd usa los precios del mock (sin caché)
LEDGER = _led.to_frame()
print(f"{len(LEDGER)} tickets · coste con caché ${LEDGER.cost_usd.sum():.4f} · sin caché ${sum(r.cost_usd for r in RES_FREE):.4f} · bucles inyectados: {sum('tool_loop' in r.injected_faults for r in RES_FREE)}")
display(LEDGER[["ticket_id", "customer_id", "tier", "feature", "model", "status", "input_total", "cache_read", "output", "cost_usd", "wasted_usd"]].head(4).round(6))

# Serie de un incidente de 90 min: coste por ticket y minuto (NaN en los minutos sin tráfico). A partir del minuto 60 alguien pone el modelo grande por defecto.
def serie_incidente(seed=SEED, minutos=90, onset=60, por_min=3):
    L = CostLedger(); cache = CacheSimulator(min_prefix_tokens=256)
    for m in range(minutos):
        tk = generate_tickets(por_min, seed=seed * 1000 + m, duration_s=60, fault_rates=DEFAULT_FAULT_RATES, start_s=SIM_EPOCH_S + m * 60)
        run_tickets(SupportAgent(llm=MockLLM("mock-large" if m >= onset else "mock-small"), system_prompt=PP, instrumentor=FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=cache, ledger=L)), tk)
    d = L.to_frame(); d["minuto"] = ((d.t_start - SIM_EPOCH_S) // 60).astype(int)
    g = d.groupby("minuto").cost_usd.mean().reindex(range(minutos))
    return [float(x) for x in g.values]
SERIE = serie_incidente()
print(f"serie: {len(SERIE)} minutos · mediana de los 60 primeros ${np.nanmedian(SERIE[:60]):.6f} · mediana del incidente ${np.nanmedian(SERIE[60:]):.6f} · ratio {np.nanmedian(SERIE[60:]) / np.nanmedian(SERIE[:60]):.1f}×")
''')

    # ------------------------------------------------------------------------------------------ 1
    md("""
    ## Paso 1 · De tokens a dinero

    **TODO 1.** `cost_breakdown(prices, model, usage, style="semconv")` devuelve un `dict` `{"input", "cache_read", "cache_write", "output", "total"}` en USD.

    - `prices`: `dict` modelo → `{"input", "output", "cache_read"?, "cache_write"?}` en USD por **millón** de tokens. Si faltan `cache_read`/`cache_write`, se cobran como `input` (sin descuento ni recargo).
    - `usage`: `dict` con `input_tokens`, `output_tokens` y, opcionalmente, `cache_read_input_tokens` y `cache_write_input_tokens` (estilo spec) **o** `cache_creation_input_tokens` (estilo Anthropic).
    - `style="semconv"`: `input_tokens` **incluye** la caché. `style="anthropic"`: `input_tokens` **excluye** la caché (el total es `input + lectura + creación`).
    - Lanza `ValueError` si `cache_read + cache_write > input_total` (invariante de subconjuntos) o si algún token es negativo, y `KeyError` si el modelo no está en `prices`.
    """)
    md(hint(1, "Primero normaliza a `(input_total, cache_read, cache_write, output)`: para `anthropic`, `input_total = input_tokens + cache_read_input_tokens + cache_creation_input_tokens`. Después valida el invariante y calcula `u = input_total - r - w`."))
    md(hint(2, "`p = prices[model]` (da `KeyError` solo); `p_cr = p.get('cache_read', p['input'])`, `p_cw = p.get('cache_write', p['input'])`; `input = u * p['input'] / 1e6`, etc., y `total` = suma de los cuatro."))
    code('''
PRICES = {"m": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75}, "n": {"input": 1.0, "output": 2.0}}

def cost_breakdown(prices: dict, model: str, usage: dict, style: str = "semconv") -> dict:
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    print(cost_breakdown(PRICES, "m", {"input_tokens": 1000, "output_tokens": 100, "cache_read_input_tokens": 600, "cache_write_input_tokens": 100}))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------ 2
    md("""
    ## Paso 2 · Atribución y unidad económica

    **TODO 2.** `attribution(ledger)` (un `DataFrame` con las columnas `customer_id`, `tier`, `feature`, `status`, `cost_usd`, `wasted_usd`) devuelve un `dict`:

    - `top5_share`: fracción del gasto total que generan el **5 % de los clientes con más coste** (nº de clientes = `max(1, round(0.05 · nº de clientes distintos))`).
    - `cost_per_ticket_by_tier`: `dict` tier → coste medio por ticket.
    - `cost_per_resolved`: gasto **total** dividido por el nº de tickets **resueltos** (`status` ∈ {`ok`, `escalated`}).
    - `wasted_share`: `wasted_usd.sum() / cost_usd.sum()`.
    - `feature_share`: `dict` *feature* → fracción del gasto total.
    """)
    md(hint(1, "`by_c = ledger.groupby('customer_id').cost_usd.sum().sort_values(ascending=False)`; `k = max(1, round(0.05 * len(by_c)))`; `top5_share = by_c.head(k).sum() / by_c.sum()`."))
    code('''
def attribution(ledger: pd.DataFrame) -> dict:
    # TODO 2
    raise NotImplementedError("TODO 2")

try:
    A = attribution(LEDGER); print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in A.items()})
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------ 3
    md("""
    ## Paso 3 · Un tope por ticket que no bloquee a los normales

    **TODO 3.** Completa `PerTicketCap(cap_usd)`, un `Instrumentor` que **rechaza la siguiente llamada al LLM** cuando el gasto acumulado del ticket ya alcanzó `cap_usd`, lanzando `LLMError("presupuesto agotado", status=429, error_type="budget_exceeded", retryable=False, latency_s=0.0)` **antes** de la llamada. El gasto de cada llamada es el de **tu** `cost_breakdown` con `PRICES_MOCK` (sin caché; usa `style="semconv"`). Guarda el gasto acumulado en `ctx.state["cap_spent"]` y apunta cada rechazo en `self.blocked` (ids de ticket).

    El tope `CAP_USD` está calibrado para los tickets normales (≈ p99,9 de su coste **sin caché**): la rúbrica comprueba que **no bloquea ninguno** y que **sí** bloquea los bucles que lo superan.
    """)
    md(hint(1, "`llm_call` es un *context manager*: `@contextmanager def llm_call(self, ctx, info):` con la comprobación **antes** del `yield` (lanza el error) y la acumulación **después** (usa `info.response.usage.input_tokens/output_tokens` y `info.response.model`)."))
    code('''
from contextlib import contextmanager
from supportops.llm import LLMError
PRICES_MOCK = {"mock-small": {"input": 0.25, "output": 1.25}, "mock-large": {"input": 3.0, "output": 15.0}}
CAP_USD = 0.0030

class PerTicketCap(Instrumentor):
    def __init__(self, cap_usd: float):
        self.cap_usd, self.blocked = cap_usd, []

    @contextmanager
    def llm_call(self, ctx, info):
        # TODO 3
        raise NotImplementedError("TODO 3")
        yield

try:
    _cap = PerTicketCap(CAP_USD)
    _r = run_tickets(SupportAgent(system_prompt=PP, instrumentor=_cap), TK[:60])
    print("bloqueados en los 60 primeros:", len(_cap.blocked))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------ 4
    md("""
    ## Paso 4 · Cuantificar el coste de los bucles

    **TODO 4.** `loop_report(results, truth=None)` recibe una lista de `AgentResult` y devuelve `{"flagged": [ticket_id…], "precision", "recall", "wasted_usd"}`:

    - Un ticket es un **bucle** si contiene **3 o más llamadas idénticas** a herramientas (mismo nombre y mismos argumentos, en `step.attributes["arguments"]` de los `StepRecord` con `kind == "tool"`).
    - `precision`/`recall` frente a la verdad de terreno: `"tool_loop" in r.injected_faults`.
    - `wasted_usd`: suma, sobre los tickets marcados, del coste (`supportops.pricing.cost_usd(modelo, entrada, salida)`, precios del mock) de **todos los pasos `llm` posteriores a la 2.ª llamada idéntica** (lo que un `LoopGuard(2)` habría ahorrado). Un paso `llm` es posterior si su `index` es mayor que el de la 2.ª herramienta repetida.
    """)
    md(hint(1, "Para cada resultado cuenta repeticiones con un `dict` clave `(nombre, json.dumps(argumentos, sort_keys=True))`; marca como bucle si el máximo ≥ 3. Para el desperdicio localiza el `index` del paso de herramienta donde esa clave llega a 2."))
    code('''
def loop_report(results: list, truth=None) -> dict:
    # TODO 4
    raise NotImplementedError("TODO 4")

try:
    LR = loop_report(RES_FREE); print({k: (round(v, 4) if isinstance(v, float) else (v[:3] if isinstance(v, list) else v)) for k, v in LR.items()})
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------ 5
    md("""
    ## Paso 5 · La alerta de desvío

    **TODO 5.** `drift_alert(series, baseline_n=30, ratio=1.6, persist=3)` devuelve el **índice** del primer punto en que salta la alerta, o `None`. Regla: la **línea base** es la mediana de los primeros `baseline_n` puntos (ignora `NaN`); salta cuando hay `persist` puntos **consecutivos** con valor ≥ `ratio` × línea base. Un `NaN` (minuto sin tráfico) **rompe** la racha. Empieza a evaluar en el índice `baseline_n`. Si la línea base tiene menos de `max(3, baseline_n // 2)` puntos válidos (no `NaN`), devuelve `None`.
    """)
    md(hint(1, "`import statistics`; `base = [x for x in series[:baseline_n] if x == x]` (el `NaN` no es igual a sí mismo); `umbral = ratio * statistics.median(base)`; recorre con un contador `racha` que se reinicia a 0 con un valor menor o con `NaN`."))
    code('''
def drift_alert(series, baseline_n: int = 30, ratio: float = 1.6, persist: int = 3):
    # TODO 5
    raise NotImplementedError("TODO 5")

try:
    print("alerta en el minuto:", drift_alert(SERIE))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------ 6
    md("""
    ## Paso 6 · El panel de FinOps como código

    **TODO 6.** `build_finops_dashboard()` devuelve el `dict` de un dashboard (`Dashboard(...).to_dict()` de `supportops.dashkit`, módulo 10) con **uid** `finops`, título «13 · FinOps (proyecto)» y al menos **8 paneles**, cada uno con `description`. Debe pasar `lint(...)` y contener estas **consultas** (las métricas las publica `FinOpsInstrumentor`: ver la lección, sección 8-9):

    1. **Coste por ticket, p95**: `histogram_quantile(0.95, …supportops_ticket_cost_USD_bucket…)`.
    2. **Coste por modelo**: `sum by (gen_ai_request_model) (rate(supportops_llm_cost_USD_total[…]))`.
    3. **Hit ratio de la caché**: una expresión con `supportops_llm_tokens_total` y `cache_read`.
    4. **Gasto desperdiciado**: una expresión con `supportops_ticket_cost_wasted_USD_total`.
    5. **Burn rate del presupuesto**: `supportops_budget_burn_rate_ratio`.
    6. **Desvío**: coste por ticket actual / el de **hace 1 h** (`offset 1h`).
    7. **Top clientes** (Loki): una consulta que contenga `ticket costed` y `supportops_finops_cost_usd`.
    8. **Tickets caros** (Tempo, TraceQL): una consulta que contenga `span.supportops.finops.cost_usd`.
    """)
    md(hint(1, "Estructura (módulo 10): `d = Dashboard('finops', '13 · FinOps (proyecto)', tags=['curso', 'finops'])`; `d.add(stat('…', 'promql', description='…'), timeseries('…', [prom('promql', '{{leyenda}}')], description='…'))`; `d.add(traces_table('…', '{ … }', description='…'))`; `table('…', [loki('…', query_type='instant')], description='…')` para Loki; `return d.to_dict()`."))
    code('''
def build_finops_dashboard() -> dict:
    # TODO 6
    raise NotImplementedError("TODO 6")

try:
    D = build_finops_dashboard(); print(len(D["panels"]), "paneles · lint:", lint(D) or "OK")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------ rúbrica
    md("""
    ## Paso 7 · Rúbrica
    """)
    code('''
REF = {"top5_share": 0.43434498924459763, "cost_per_resolved": 0.00031152420454545456, "wasted_share": 0.1657263972994948,
       "by_tier": {"premium": 0.0003021250954198473, "standard": 0.0002656599770642202},
       "feature_share": {"escalation": 0.14457398429204207, "kb_question": 0.3411003741501189, "order_status": 0.3418857355677528, "refund": 0.1724399059900861, "unknown": 0.0},
       "loop_wasted": 0.038409, "n_loops": 12}      # calibrado con la solución (semilla 42)

def run_rubric():
    rows = []
    def add(r, d, ok, det=""): rows.append({"criterio": r, "descripción": d, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": det})
    ap = lambda a, b, t=1e-12: abs(a - b) <= t * max(1.0, abs(b))
    # R1
    try:
        U = {"input_tokens": 1000, "output_tokens": 100, "cache_read_input_tokens": 600, "cache_write_input_tokens": 100}
        c1 = cost_breakdown(PRICES, "m", U)
        c2 = cost_breakdown(PRICES, "m", {"input_tokens": 300, "output_tokens": 100, "cache_read_input_tokens": 600, "cache_creation_input_tokens": 100}, style="anthropic")
        c3 = cost_breakdown(PRICES, "n", {"input_tokens": 1_000_000, "output_tokens": 0, "cache_read_input_tokens": 500_000})
        def raises(exc, fn):
            try: fn()
            except exc: return True
            except Exception: return False
            return False
        checks = {"subconjuntos": ap(c1["input"], 300 * 3 / 1e6) and ap(c1["cache_read"], 600 * 0.3 / 1e6) and ap(c1["cache_write"], 100 * 3.75 / 1e6) and ap(c1["output"], 100 * 15 / 1e6) and ap(c1["total"], sum(c1[k] for k in ("input", "cache_read", "cache_write", "output"))),
                  "estilo Anthropic = spec": all(ap(c2[k], c1[k]) for k in c1),
                  "sin multiplicadores": ap(c3["total"], 1.0) and ap(c3["cache_read"], 0.5),
                  "invariante": raises(ValueError, lambda: cost_breakdown(PRICES, "m", {"input_tokens": 100, "output_tokens": 1, "cache_read_input_tokens": 80, "cache_write_input_tokens": 40})),
                  "negativos": raises(ValueError, lambda: cost_breakdown(PRICES, "m", {"input_tokens": -1, "output_tokens": 1})),
                  "modelo desconocido": raises(KeyError, lambda: cost_breakdown(PRICES, "zzz", U)),
                  "anthropic invariante": ap(cost_breakdown(PRICES, "n", {"input_tokens": 10, "output_tokens": 0, "cache_read_input_tokens": 90}, style="anthropic")["total"], 100 * 1.0 / 1e6)}
        add("R1", "cost_breakdown: 7 vectores", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R1", "cost_breakdown", False, f"{type(e).__name__}: {e}")
    # R2
    try:
        a = attribution(LEDGER)
        ok = ap(a["top5_share"], REF["top5_share"], 1e-9) and ap(a["cost_per_resolved"], REF["cost_per_resolved"], 1e-9) and ap(a["wasted_share"], REF["wasted_share"], 1e-9) \\
            and all(ap(a["cost_per_ticket_by_tier"][k], v, 1e-9) for k, v in REF["by_tier"].items()) and all(ap(a["feature_share"].get(k, -1), v, 1e-9) for k, v in REF["feature_share"].items())
        add("R2", "attribution: top-5 %, tier, resuelto, desperdicio y features", ok, f"top5={a['top5_share']:.4f} (ref {REF['top5_share']:.4f}) · USD/resuelto={a['cost_per_resolved']:.6f} (ref {REF['cost_per_resolved']:.6f}) · desperdicio={a['wasted_share']:.4f} (ref {REF['wasted_share']:.4f})")
    except Exception as e: add("R2", "attribution", False, f"{type(e).__name__}: {e}")
    # R3
    try:
        cap = PerTicketCap(CAP_USD)
        res_c = run_tickets(SupportAgent(system_prompt=PP, instrumentor=cap), TK)
        free = {r.ticket_id: r for r in RES_FREE}; blocked = set(cap.blocked)
        normal_blocked = [t for t in blocked if "tool_loop" not in free[t].injected_faults]
        expected = {t for t, r in free.items() if "tool_loop" in r.injected_faults and r.cost_usd > CAP_USD}
        max_one_call = max(max(cost_usd(s.name, s.input_tokens, s.output_tokens) for s in r.steps if s.kind == "llm") for r in RES_FREE if any(s.kind == "llm" for s in r.steps))
        checks = {"0 falsos bloqueos": len(normal_blocked) == 0, "bloquea los bucles que superan el tope": blocked == expected and len(expected) > 0,
                  "coste ≤ tope + 1 llamada": max(r.cost_usd for r in res_c) <= CAP_USD + max_one_call + 1e-9,
                  "estado de los bloqueados": all(r.status == "error" and r.error_type == "budget_exceeded" for r in res_c if r.ticket_id in blocked)}
        add("R3", "PerTicketCap: 3 comprobaciones + estado", all(checks.values()), f"{ {k: v for k, v in checks.items() if not v} or 'todas OK'} · bloqueados={len(blocked)} (esperados {len(expected)})")
    except Exception as e: add("R3", "PerTicketCap", False, f"{type(e).__name__}: {e}")
    # R4
    try:
        lr = loop_report(RES_FREE)
        ok = lr["precision"] >= 0.95 and lr["recall"] >= 0.95 and abs(lr["wasted_usd"] - REF["loop_wasted"]) <= 0.02 * REF["loop_wasted"] and len(lr["flagged"]) == REF["n_loops"]
        add("R4", "loop_report: precisión/exhaustividad ≥ 0,95 y desperdicio ± 2 %", ok, f"precisión={lr['precision']:.2f} exhaustividad={lr['recall']:.2f} desperdicio=${lr['wasted_usd']:.5f} (ref ${REF['loop_wasted']:.5f}) · marcados={len(lr['flagged'])} (ref {REF['n_loops']})")
    except Exception as e: add("R4", "loop_report", False, f"{type(e).__name__}: {e}")
    # R5
    try:
        rng = np.random.default_rng(1); base = list(1.0 + 0.1 * rng.standard_normal(60))
        checks = {"sin falsa alarma en la base": drift_alert(base + [1.0] * 30) is None,
                  "detecta el incidente real en ≤ 4 min": (lambda i: i is not None and 60 <= i <= 64)(drift_alert(SERIE)),
                  "picos de 2 puntos no alertan": drift_alert(base + [3.0, 3.0, 1.0, 3.0, 3.0, 1.0] + [1.0] * 10) is None,
                  "los huecos (NaN) rompen la racha y el índice es correcto": drift_alert(base + [3.0, 3.0, float("nan"), 3.0, 3.0, 3.0]) == 60 + 5 and drift_alert(base[:10] + [float("nan")] * 20 + [5.0] * 5, baseline_n=30) is None}
        add("R5", "drift_alert: 4 escenarios", all(checks.values()), str({k: v for k, v in checks.items() if not v} or f"todas OK · alerta en el minuto {drift_alert(SERIE)}"))
    except Exception as e: add("R5", "drift_alert", False, f"{type(e).__name__}: {e}")
    # R6
    try:
        import re as _re
        D = build_finops_dashboard()
        exprs = []
        for p in D["panels"]:
            for t in p.get("targets", []): exprs.append(t.get("expr") or t.get("query") or "")
        has = lambda *pats: any(all(_re.search(p, e) for p in pats) for e in exprs)
        checks = {"lint limpio y uid": not lint(D) and D["uid"] == "finops" and len(D["panels"]) >= 8,
                  "p95 coste por ticket": has(r"histogram_quantile\\(0\\.95", r"supportops_ticket_cost_USD_bucket"), "coste por modelo": has(r"sum by \\(gen_ai_request_model\\)", r"supportops_llm_cost_USD_total"),
                  "hit ratio": has(r"supportops_llm_tokens_total", r"cache_read"), "desperdicio": has(r"supportops_ticket_cost_wasted_USD_total"), "burn rate": has(r"supportops_budget_burn_rate_ratio"),
                  "desvío (offset 1h)": has(r"offset 1h", r"supportops_ticket_cost_USD"), "Loki por cliente": has(r"ticket costed", r"supportops_finops_cost_usd"),
                  "Tempo tickets caros": has(r"span\\.supportops\\.finops\\.cost_usd")}
        add("R6", "build_finops_dashboard: lint + 8 consultas", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R6", "build_finops_dashboard", False, f"{type(e).__name__}: {e}")
    return pd.DataFrame(rows).set_index("criterio")
''')
    code('''
# Ejecuta esta celda cuando hayas terminado los TODO
display(run_rubric())
''')

    md("""
    ---
    ## Paso final (opcional) · Míralo funcionar

    Con el stack (`docker compose --profile core --profile metrics up -d`): guarda tu dashboard con `Dashboard.save(...)` en `stack/grafana/dashboards/`, envía telemetría con `FinOpsInstrumentor(..., handle=setup_telemetry("supportops-agent"))` y `generate_tickets(..., start_s="live")`, provoca un cambio de modelo a mitad y comprueba que tu panel de desvío cruza el umbral y que `finops_alert_rule_json(...)` (lección, sección 9.1) dispara.

    ## Retos extra (nivel experto)

    1. **Presupuesto por cliente y día** con multiplicador por tier (`BudgetGuard(per_customer_day_usd=…, tier_multiplier={"premium": 2})`): ¿cuántos clientes se bloquean con un tope del p95 diario y cuánto gasto evitas? ¿Qué pasa con los premium?
    2. **Degradación inteligente:** `DowngradeLLM` al 25 % del tope frente a bloqueo: mide coste, tickets resueltos y `grounded` (¿baja la calidad del modelo pequeño?).
    3. **Reponderación:** vuelve a calcular el gasto del libro con una segunda tabla de precios y explica por qué guardar **tokens** es mejor que guardar dólares.
    4. **Alerta multiventana:** combina una ventana corta (5 min) y una larga (1 h) como el *burn rate* de un SLO para reducir falsos positivos; calibra con la línea base de `SERIE` y mide el retraso de detección.
    5. **Multi-agente:** reutiliza `MultiAgentSupportOps` (módulo 11), reprecia `per_agent` con `PriceTable` y atribuye el coste por agente y modelo; ¿qué agente domina?

    ## Reflexión (producción e hilo conductor)

    - Tu `CAP_USD` bloqueó bucles pero un bloqueo es un ticket **sin resolver**: ¿qué ocurre con el cliente? ¿Dónde pondrías la **degradación a humano** y cómo medirías su coste (módulo 11, fallback)?
    - `drift_alert` salta en 1-3 min con un cambio ×12 y **no** vería un +30 %: ¿qué métrica añadirías (coste desperdiciado, hit ratio, tokens por ticket) para el desvío lento?
    - La unidad económica es el **ticket resuelto**: ¿cómo la combinarías con la calidad del módulo 14 (juez) para no «ahorrar» empeorando las respuestas?
    - El módulo 18 trata el **coste del propio stack de observabilidad**: ¿cuánto gasta tu telemetría de FinOps (spans, series, logs por ticket) comparado con lo que ahorra?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine las funciones y vuelve a lanzar la rúbrica).
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
def cost_breakdown(prices, model, usage, style="semconv"):
    p = prices[model]
    cr, cw = int(usage.get("cache_read_input_tokens", 0)), int(usage.get("cache_write_input_tokens", usage.get("cache_creation_input_tokens", 0)))
    inp, out = int(usage["input_tokens"]), int(usage["output_tokens"])
    total_in = inp + cr + cw if style == "anthropic" else inp
    if min(total_in, out, cr, cw) < 0: raise ValueError("tokens negativos")
    if cr + cw > total_in: raise ValueError("cache_read + cache_write > input_total")
    u = total_in - cr - cw
    d = {"input": u * p["input"] / 1e6, "cache_read": cr * p.get("cache_read", p["input"]) / 1e6, "cache_write": cw * p.get("cache_write", p["input"]) / 1e6, "output": out * p["output"] / 1e6}
    d["total"] = sum(d.values())
    return d

def attribution(ledger):
    by_c = ledger.groupby("customer_id").cost_usd.sum().sort_values(ascending=False)
    k = max(1, round(0.05 * len(by_c)))
    resolved = ledger.status.isin(["ok", "escalated"]).sum()
    return {"top5_share": float(by_c.head(k).sum() / by_c.sum()), "cost_per_ticket_by_tier": ledger.groupby("tier").cost_usd.mean().to_dict(),
            "cost_per_resolved": float(ledger.cost_usd.sum() / resolved), "wasted_share": float(ledger.wasted_usd.sum() / ledger.cost_usd.sum()),
            "feature_share": (ledger.groupby("feature").cost_usd.sum() / ledger.cost_usd.sum()).to_dict()}

class PerTicketCap(Instrumentor):
    def __init__(self, cap_usd):
        self.cap_usd, self.blocked = cap_usd, []

    @contextmanager
    def llm_call(self, ctx, info):
        spent = ctx.state.get("cap_spent", 0.0)
        if spent >= self.cap_usd:
            self.blocked.append(ctx.ticket.ticket_id)
            raise LLMError("presupuesto agotado", status=429, error_type="budget_exceeded", retryable=False, latency_s=0.0)
        yield
        r = info.response
        if r is not None:
            usage = {"input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens}
            ctx.state["cap_spent"] = spent + cost_breakdown(PRICES_MOCK, r.model, usage)["total"]

def loop_report(results, truth=None):
    flagged, wasted = [], 0.0
    for r in results:
        seen, second_idx = {}, None
        for s in r.steps:
            if s.kind != "tool": continue
            k = (s.name, json.dumps(s.attributes.get("arguments", {}), sort_keys=True, default=str))
            seen[k] = seen.get(k, 0) + 1
            if seen[k] == 2 and second_idx is None: second_idx = s.index
        if max(seen.values(), default=0) >= 3:
            flagged.append(r.ticket_id)
            wasted += sum(cost_usd(s.name, s.input_tokens, s.output_tokens) for s in r.steps if s.kind == "llm" and second_idx is not None and s.index > second_idx)
    real = {r.ticket_id for r in results if "tool_loop" in r.injected_faults}
    tp = len(real & set(flagged))
    return {"flagged": flagged, "precision": tp / len(flagged) if flagged else 1.0, "recall": tp / len(real) if real else 1.0, "wasted_usd": wasted}

def drift_alert(series, baseline_n=30, ratio=1.6, persist=3):
    import statistics
    base = [x for x in series[:baseline_n] if x == x]
    if len(base) < max(3, baseline_n // 2): return None
    thr, racha = ratio * statistics.median(base), 0
    for i in range(baseline_n, len(series)):
        v = series[i]
        racha = racha + 1 if (v == v and v >= thr) else 0
        if racha >= persist: return i
    return None

def build_finops_dashboard():
    d = Dashboard("finops", "13 · FinOps (proyecto)", tags=["curso", "finops"], description="Coste por ticket, por modelo, caché, desperdicio, presupuesto y desvío.")
    cur = "sum(rate(supportops_ticket_cost_USD_sum[10m])) / sum(rate(supportops_ticket_cost_USD_count[10m]))"
    off = "sum(rate(supportops_ticket_cost_USD_sum[10m] offset 1h)) / sum(rate(supportops_ticket_cost_USD_count[10m] offset 1h))"
    d.add(
        timeseries("Coste por ticket · p95", [prom("histogram_quantile(0.95, sum by (le) (rate(supportops_ticket_cost_USD_bucket[$__rate_interval])))", "p95")], unit="currencyUSD", w=12, description="p95 del coste por ticket (precios de la tabla configurada)."),
        timeseries("Coste por modelo", [prom("sum by (gen_ai_request_model) (rate(supportops_llm_cost_USD_total[$__rate_interval]))", "{{gen_ai_request_model}}")], unit="currencyUSD", stack=True, w=12, description="Dinero por segundo y modelo: un cambio de modelo se ve aquí primero."),
        stat("Hit ratio de la caché", 'sum(rate(supportops_llm_tokens_total{gen_ai_token_type="cache_read"}[10m])) / sum(rate(supportops_llm_tokens_total{gen_ai_token_type=~"input|cache_read|cache_write"}[10m]))', unit="percentunit", w=6, description="Fracción de la entrada servida desde caché. Una caída brusca = caché rota."),
        stat("Gasto desperdiciado", "sum(rate(supportops_ticket_cost_wasted_USD_total[10m])) / sum(rate(supportops_llm_cost_USD_total[10m]))", unit="percentunit", w=6, description="Fracción del gasto en tickets no resueltos, alucinados o en bucle."),
        stat("Burn rate del presupuesto", "max(supportops_budget_burn_rate_ratio)", w=6, thr=thresholds((None, "green"), (1, "orange"), (2, "red")), description="1 = justo en presupuesto; 2 = agota el presupuesto a mitad de periodo."),
        timeseries("Desvío del coste por ticket (actual / hace 1 h)", [prom(f"({cur}) / ({off})", "ratio")], w=6, thr=thresholds((None, "green"), (1.6, "red")), description="Cruzar 1,6 durante 5 min dispara la alerta de desvío."),
        table("Top clientes por coste (Loki)", [loki('topk(10, sum by (supportops_customer_id) (sum_over_time({service_name="supportops-agent"} |= "ticket costed" | unwrap supportops_finops_cost_usd [$__range])))', "{{supportops_customer_id}}", query_type="instant")], w=12, description="Atribución por cliente desde los logs (alta cardinalidad fuera de Prometheus)."),
        traces_table("Tickets caros (Tempo)", '{ name =~ "invoke_agent.*" && span.supportops.finops.cost_usd > 0.002 }', w=12, description="Trazas de tickets con coste superior a 0,002 USD: abre la cascada para ver qué llamadas lo causaron."),
    )
    return d.to_dict()

display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, bargauge, gauge, lint, logs, prom, stat, table, text, thresholds, timeseries, traces_table, loki
    d = Dashboard("finops", "13 · FinOps", tags=["curso", "finops"], time_from="now-1h",
                  description="Coste de SupportOps: por ticket, modelo, feature y tier, caché, desperdicio, presupuesto y alerta de desvío. PRECIOS ILUSTRATIVOS.")
    d.add(text("Cómo leer este dashboard", "⚠️ **Precios ilustrativos** (tabla configurable del módulo 13; no son de ningún proveedor). Importan las **proporciones** y la **forma** de las curvas. "
               "Métricas: `supportops_llm_cost_USD_total` (por modelo/feature/tier/componente), `supportops_ticket_cost_USD` (histograma por ticket), "
               "`supportops_llm_tokens_total` (por tipo de token) y el presupuesto (`supportops_budget_*`). El coste **por cliente** sale de los logs (Loki): "
               "`customer_id` nunca es etiqueta de métrica.", h=3))
    cost, tk_sum, tk_cnt = "supportops_llm_cost_USD_total", "supportops_ticket_cost_USD_sum", "supportops_ticket_cost_USD_count"
    cur = f"sum(rate({tk_sum}[10m])) / sum(rate({tk_cnt}[10m]))"
    off = f"sum(rate({tk_sum}[10m] offset 1h)) / sum(rate({tk_cnt}[10m] offset 1h))"
    d.row("Resumen")
    d.add(
        stat("Coste en el rango", f"sum(increase({cost}[$__range]))", unit="currencyUSD", w=4, h=4, color_mode="value", decimals=4, description="Gasto total (USD ilustrativos) en el rango seleccionado."),
        stat("Coste por ticket (10 min)", cur, unit="currencyUSD", w=4, h=4, color_mode="value", decimals=5, description="Coste medio por ticket en los últimos 10 minutos."),
        stat("Hit ratio de la caché", 'sum(rate(supportops_llm_tokens_total{gen_ai_token_type="cache_read"}[10m])) / sum(rate(supportops_llm_tokens_total{gen_ai_token_type=~"input|cache_read|cache_write"}[10m]))',
             unit="percentunit", w=4, h=4, thr=thresholds((None, "red"), (0.5, "orange"), (0.8, "green")), description="Fracción de la entrada servida desde la caché del proveedor. Una caída brusca tras un despliegue = caché rota."),
        stat("Gasto desperdiciado", f"sum(rate(supportops_ticket_cost_wasted_USD_total[10m])) / sum(rate({cost}[10m]))", unit="percentunit", w=4, h=4, thr=thresholds((None, "green"), (0.05, "orange"), (0.15, "red")),
             description="Fracción del gasto en tickets no resueltos, alucinados o en bucle."),
        stat("Burn rate del presupuesto", "max(supportops_budget_burn_rate_ratio)", w=4, h=4, thr=thresholds((None, "green"), (1, "orange"), (2, "red")), decimals=2,
             description="Ritmo de gasto relativo al lineal permitido: 1 = justo en presupuesto; 2 = agota el presupuesto a mitad de periodo."),
        gauge("Presupuesto gastado", "max(supportops_budget_spent_USD) / max(supportops_budget_limit_USD)", w=4, h=4, description="Fracción del presupuesto del periodo ya gastada."),
    )
    d.row("Coste por ticket y desvío")
    d.add(
        timeseries("Coste por ticket · p50 y p95", [prom(f"histogram_quantile(0.50, sum by (le) (rate(supportops_ticket_cost_USD_bucket[$__rate_interval])))", "p50"),
                                                    prom(f"histogram_quantile(0.95, sum by (le) (rate(supportops_ticket_cost_USD_bucket[$__rate_interval])))", "p95", ref="B")], unit="currencyUSD", w=12,
                   description="Percentiles del coste por ticket: el p95 revela la cola (bucles, reintentos) que la media oculta."),
        timeseries("Desvío: coste por ticket actual / hace 1 h", [prom(f"({cur}) / ({off})", "ratio")], w=12, thr=thresholds((None, "green"), (1.6, "red")), thr_style="line", description="La alerta de desvío salta si supera 1,6 durante 5 minutos (misma consulta que la regla de Grafana)."),
    )
    d.row("Atribución")
    d.add(
        timeseries("Coste por modelo", [prom(f"sum by (gen_ai_request_model) (rate({cost}[$__rate_interval]))", "{{gen_ai_request_model}}")], unit="currencyUSD", stack=True, w=8, description="Dinero por segundo y modelo."),
        timeseries("Coste por feature", [prom(f"sum by (supportops_feature) (rate({cost}[$__rate_interval]))", "{{supportops_feature}}")], unit="currencyUSD", stack=True, w=8, description="Dinero por segundo y *feature* (intención detectada)."),
        timeseries("Coste por tier", [prom(f"sum by (supportops_customer_tier) (rate({cost}[$__rate_interval]))", "{{supportops_customer_tier}}")], unit="currencyUSD", stack=True, w=8, description="Dinero por segundo y tier de cliente."),
        timeseries("Coste por componente", [prom(f"sum by (supportops_cost_component) (rate({cost}[$__rate_interval]))", "{{supportops_cost_component}}")], unit="currencyUSD", stack=True, w=12,
                   description="Entrada no cacheada, lectura de caché, escritura de caché y salida: cómo se reparte el gasto."),
        timeseries("Tokens por tipo", [prom("sum by (gen_ai_token_type) (rate(supportops_llm_tokens_total[$__rate_interval]))", "{{gen_ai_token_type}}")], unit="short", stack=True, w=12,
                   description="Tokens/s por tipo: `cache_read` alto y `cache_write` bajo = caché sana."),
    )
    d.row("Por cliente, tickets caros y bucles")
    d.add(
        table("Top clientes por coste (Loki)", [loki('topk(10, sum by (supportops_customer_id) (sum_over_time({service_name="supportops-agent"} |= "ticket costed" | unwrap supportops_finops_cost_usd [$__range])))', "{{supportops_customer_id}}", query_type="instant")], w=12, h=9,
              description="Atribución por cliente desde los logs `ticket costed` (el `customer_id` es *structured metadata*, no etiqueta de métrica). Consulta de métrica de Loki, instantánea."),
        traces_table("Tickets caros (> 0,002 USD)", '{ name =~ "invoke_agent.*" && span.supportops.finops.cost_usd > 0.002 }', w=12, h=9, description="Trazas de tickets caros: abre la cascada para ver qué llamadas (y qué modelo) lo causaron."),
        traces_table("Posibles bucles (≥ 4 herramientas en la traza)", '{ span.gen_ai.operation.name = "execute_tool" } | count() >= 4', w=24, h=7, description="Trazas con 4 o más ejecuciones de herramienta: candidatas a bucle (sin capturar argumentos solo se ve el recuento)."),
    )
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "13-finops.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
def build_readme() -> None:
    readme = """# Módulo 13 · Costes y FinOps de agentes de IA

🟠 **Avanzado** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ **Todos los precios del módulo son ILUSTRATIVOS** (tabla configurable, no de ningún proveedor ni fecha). Cárgalos de tu proveedor con
> `PriceTable.from_json(...)` o `SUPPORTOPS_PRICES_FILE`; cambian con frecuencia y por modelo (incluidos los multiplicadores de caché).

De tokens a dinero: una tabla de precios configurable, **atribución** por cliente/*feature*/modelo/agente sin disparar la cardinalidad, **caché de prompts**
(ahorro, punto de equilibrio y cómo se rompe), **presupuestos y topes** (por ticket, cliente y periodo, con degradación de modelo y *burn rate*),
**detección de bucles caros** y un **panel de FinOps con alerta de desvío**.

## Objetivos
1. Calcular el coste de una llamada/ticket con una tabla de precios (con lectura/escritura de caché) y reconciliarlo con el agente.
2. Normalizar el `usage` de una API a la semántica de la spec GenAI (la entrada **incluye** la caché).
3. Atribuir el gasto eligiendo la señal correcta (métricas, logs o trazas) y medir la unidad económica (coste por ticket **resuelto**).
4. Medir el ahorro de la caché, su punto de equilibrio y los modos en que se rompe.
5. Diseñar topes y presupuestos (burn rate, previsión) y degradación de modelo.
6. Detectar y cortar bucles de herramientas (post-hoc y en línea).
7. Publicar el coste como telemetría OpenTelemetry y construir panel + alerta de desvío.

## Contenido
| Archivo | Qué es |
|---|---|
| `13_costes_finops.ipynb` | Lección (9 secciones, 10+ gráficos, simulación de un mes, 🧠 de élite, autoevaluación) |
| `13_proyecto_costes_finops.ipynb` | Proyecto: `cost_breakdown`, atribución, tope por ticket, informe de bucles, alerta de desvío y panel como código (rúbrica calibrada, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/finops.py` | `PriceTable` (ilustrativa/configurable), `CacheSimulator`, `FinOpsInstrumentor`, `CostLedger`, `BudgetGuard`/`BudgetPool`, `DowngradeLLM`, `LoopGuard`, `cost_drift_alert`, regla de alerta de Grafana |
| `../stack/grafana/dashboards/13-finops.json` | Dashboard «13 · FinOps» (uid `finops`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 9 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`).

## Lecturas
- Anthropic, documentación de *prompt caching* (campos de uso, multiplicadores, TTL, mínimos, invalidación) · OpenTelemetry GenAI semconv (`cache_read`/`cache_write`).
- FinOps Foundation, *Optimizing GenAI Usage* · Google SRE Workbook, *Alerting on SLOs* (burn rate).

## Cómo se conecta
Antes: módulo 09 (cardinalidad, métricas), 11 (coste por agente, contar solo hojas), 12 (herramientas con coste propio). Después: el 14 combina coste y calidad (¿ahorrar sin empeorar?),
el 16 convierte el coste en un SLO con *burn rate* y el 18 mide el coste del propio stack de observabilidad.
"""
    (COURSE / MOD / "README.md").write_text(readme, encoding="utf-8")
    print("OK README", MOD)


if __name__ == "__main__":
    build_lesson()
    build_project()
    build_readme()
    build_dashboard()
