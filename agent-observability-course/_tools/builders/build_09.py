"""Genera el módulo 09_metricas: README, lección y proyecto (autor A4).  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_09.py
También (re)genera el dashboard aprovisionado stack/grafana/dashboards/09-genai-metrics.json.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, box, boot, details, hint, nb_for, observe  # noqa: E402

sys.path.insert(0, str(COURSE))
MOD = "09_metricas"

# Imports comunes de las dos libretas (A1 trae IMPORTS; aquí añadimos lo propio del módulo)
SETUP = '''
import os
os.environ.setdefault("LLM_PROVIDER", "mock")          # mock = determinista, sin coste, sin API keys
import json, math, time, collections, logging
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from supportops import *                                 # SupportAgent, generate_tickets, check_stack, Incident, ...
from supportops import viz, sample_data, backends
from supportops.telemetry import setup_telemetry, OTelInstrumentor
from supportops.otel_metrics import *                    # MetricsInstrumentor, PriceTable, run_live, prom_instant, prom_range, ...
viz.apply_style()
pd.set_option("display.width", 150); pd.set_option("display.max_colwidth", 90)
SEED = 42
FAST_DEV_RUN = True   # True: tráfico en vivo corto (~100 s) y pocos tickets. False: 4 min de tráfico y más tickets
'''


# =====================================================================================================================
def build_dashboard() -> None:
    """Dashboard aprovisionado 09 (stack/grafana/dashboards/09-genai-metrics.json), generado con supportops.dashkit."""
    from supportops import dashkit as dk
    TIER = 'supportops_customer_tier=~"$tier"'
    d = dk.Dashboard("genai-metrics", "09 · Métricas GenAI de SupportOps", tags=["curso", "metricas", "supportops", "09"],
                     description="RED + GenAI (tokens, coste, pasos) de SupportOps a partir de las métricas de OpenTelemetry (módulo 09). Provisionado desde stack/grafana/dashboards/09-genai-metrics.json.",
                     time_from="now-15m")
    d.variable(dk.var_query("tier", "label_values(supportops_agent_requests_total, supportops_customer_tier)", label="Tier de cliente"))
    d.variable(dk.var_query("model", "label_values(gen_ai_client_inference_duration_seconds_count, gen_ai_request_model)", label="Modelo"))
    d.dash_link("Salud del agente (módulo 10)", "", tags=["salud-agente"], as_dropdown=False)
    d.row("RED · tasa, errores, duración")
    d.add(
        dk.stat("Peticiones/s", f'sum(rate(supportops_agent_requests_total{{{TIER}}}[$__rate_interval]))', unit="reqps", decimals=2, color_mode="value",
                description="Tasa de tickets atendidos. rate() de un Counter con $__rate_interval.", w=4),
        dk.stat("Tasa de error", f'sum(rate(supportops_agent_requests_total{{{TIER},supportops_status=~"error|max_steps"}}[$__rate_interval])) / sum(rate(supportops_agent_requests_total{{{TIER}}}[$__rate_interval]))',
                unit="percentunit", decimals=1, thr=dk.thresholds((None, dk.GREEN), (0.05, dk.ORANGE), (0.15, dk.RED)), w=4,
                description="Fracción de peticiones con estado error o max_steps."),
        dk.stat("p95 del agente", 'histogram_quantile(0.95, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket{supportops_customer_tier=~"$tier"}[$__rate_interval])))',
                unit="s", decimals=2, thr=dk.thresholds((None, dk.GREEN), (4, dk.ORANGE), (8, dk.RED)), w=4,
                description="p95 estimado por interpolación de buckets (histogram_quantile sobre sum by (le))."),
        dk.stat("Coste USD/hora", f'sum(rate(supportops_llm_cost_USD_total[$__rate_interval])) * 3600', unit="currencyUSD", decimals=3, color_mode="value", w=4,
                description="Coste derivado con una tabla de precios ILUSTRATIVA (no son precios reales)."),
        dk.stat("Tokens de entrada/s", 'sum(rate(gen_ai_client_inference_usage_input_tokens_total[$__rate_interval]))', unit="short", decimals=0, color_mode="value", w=4,
                description="Consumo de tokens de entrada (Counter gen_ai.client.inference.usage.input_tokens)."),
        dk.stat("Llamadas LLM por ticket", 'sum(rate(gen_ai_client_inference_duration_seconds_count[$__rate_interval])) / sum(rate(supportops_agent_requests_total[$__rate_interval]))',
                unit="short", decimals=2, thr=dk.thresholds((None, dk.GREEN), (2.6, dk.ORANGE), (4, dk.RED)), w=4,
                description="Un valor que sube indica reintentos o bucles de herramientas."),
    )
    d.add(
        dk.timeseries("Peticiones/s por estado", [dk.prom(f'sum by (supportops_status) (rate(supportops_agent_requests_total{{{TIER}}}[$__rate_interval]))', "{{supportops_status}}")],
                      unit="reqps", stack=True, w=12, description="Descompone la tasa por estado final (ok, escalated, degraded, error, max_steps)."),
        dk.timeseries("Latencia del agente p50 / p95 / p99",
                      [dk.prom(f'histogram_quantile({q}, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket{{{TIER}}}[$__rate_interval])))', f"p{int(q * 100)}", ref=r)
                       for q, r in ((0.5, "A"), (0.95, "B"), (0.99, "C"))], unit="s", w=12,
                      thr=dk.thresholds((None, dk.GREEN), (4, dk.RED)), thr_style="line",
                      description="Percentiles estimados con histogram_quantile. La línea roja marca un umbral orientativo de 4 s."),
    )
    d.add(
        dk.heatmap("Distribución de la latencia y exemplars", f'sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket{{{TIER}}}[$__rate_interval]))', w=24, h=9, exemplar=True,
                   description="Mapa de calor de los buckets del histograma. Los rombos son exemplars: un clic abre la traza concreta en Tempo (requiere tráfico reciente)."),
    )
    d.row("GenAI · modelo, herramientas, coste")
    d.add(
        dk.timeseries("p95 de la llamada al LLM", [dk.prom('histogram_quantile(0.95, sum by (le, gen_ai_request_model) (rate(gen_ai_client_inference_duration_seconds_bucket{gen_ai_request_model=~"$model"}[$__rate_interval])))', "{{gen_ai_request_model}}")],
                      unit="s", w=8, description="Latencia del proveedor LLM aislada de las herramientas (gen_ai.client.inference.duration)."),
        dk.timeseries("Latencia media por herramienta", [dk.prom('sum by (gen_ai_tool_name) (rate(gen_ai_execute_tool_duration_seconds_sum[$__rate_interval])) / sum by (gen_ai_tool_name) (rate(gen_ai_execute_tool_duration_seconds_count[$__rate_interval]))', "{{gen_ai_tool_name}}")],
                      unit="s", w=8, description="Media = sum/count del histograma. Para percentiles por herramienta usa histogram_quantile."),
        dk.timeseries("Tokens/s (entrada y salida)", [dk.prom('sum(rate(gen_ai_client_inference_usage_input_tokens_total[$__rate_interval]))', "entrada", ref="A"),
                                                       dk.prom('sum(rate(gen_ai_client_inference_usage_output_tokens_total[$__rate_interval]))', "salida", ref="B")],
                      unit="short", w=8, description="Counters de uso de tokens; la salida es ≈ 14× menor que la entrada en SupportOps."),
    )
    d.add(
        dk.timeseries("Coste USD/hora por modelo", [dk.prom('sum by (gen_ai_request_model) (rate(supportops_llm_cost_USD_total[$__rate_interval])) * 3600', "{{gen_ai_request_model}}")],
                      unit="currencyUSD", w=8, description="Counter de coste (precios ilustrativos) por modelo."),
        dk.timeseries("Pasos por ticket (p90)", [dk.prom('histogram_quantile(0.9, sum by (le) (rate(gen_ai_invoke_agent_tool_calls_bucket[$__rate_interval])))', "herramientas", ref="A"),
                                                  dk.prom('histogram_quantile(0.9, sum by (le) (rate(gen_ai_invoke_agent_inference_calls_bucket[$__rate_interval])))', "llamadas LLM", ref="B")],
                      unit="short", w=8, description="Cola de pasos del agente: un p90 que sube delata bucles de herramientas."),
        dk.timeseries("Series activas de estas métricas", [dk.prom('count({__name__=~"gen_ai_.*|supportops_.*"})', "series")], unit="short", w=8,
                      description="Presupuesto de cardinalidad: si esta línea crece sin parar, algún atributo tiene valores ilimitados."),
    )
    d.save(COURSE / "stack" / "grafana" / "dashboards" / "09-genai-metrics.json")
    print("OK dashboard 09-genai-metrics.json:", len(d.d["panels"]), "elementos")


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "09_metricas.ipynb", "Módulo 09 · Métricas: Prometheus/Mimir, instrumentos OTel, RED + GenAI y exemplars")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 09 · Métricas: Prometheus/Mimir, instrumentos de OpenTelemetry, RED + GenAI y exemplars

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 3 h + proyecto ≈ 1 h 30 min) |
    | **Servicios de Compose** | `core` + `metrics`: `docker compose --profile core --profile metrics up -d` (≈ 0,45 GB de RAM en reposo). **Funciona sin Docker en modo degradado** (las partes con Prometheus se saltan y se explican) |
    | **Prerrequisitos** | Módulo 02 (contador/histograma a mano, cardinalidad), 03-04 (SDK y GenAI semconv; `setup_telemetry`) y 05 (el pipeline de métricas del Collector) |
    | **Hilo conductor** | SupportOps pasa de «tener trazas» a «tener números»: tasa, errores, latencia, tokens y **coste** por minuto, con *exemplars* que saltan a la traza |

    > 🗺️ **Ruta núcleo vs ampliación.** Núcleo (≈ 2 h): secciones 1, 3, 5, 7 y 8. Ampliación (≈ 1 h): el `rate()`/`histogram_quantile()` a mano (2), nombres (4), exemplars en profundidad (6), histogramas nativos (9) y Mimir (10). El proyecto usa lo del núcleo.
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** el modelo de datos de Prometheus (serie = nombre + etiquetas; contadores, *gauges*, histogramas) y las tres rutas por las que llegan métricas OTel (Collector → *scrape*, OTLP directo, *remote write* a Mimir).
    2. **Implementar a mano** `rate()` (con reinicios y extrapolación) y `histogram_quantile()`, y **comprobar** que coinciden con los de Prometheus.
    3. **Elegir** el instrumento OTel adecuado (*Counter, UpDownCounter, Histogram, Gauge, Observable\\**) y **razonar** sobre la temporalidad *cumulative* frente a *delta*.
    4. **Predecir** el nombre que tendrá una métrica OTel en Prometheus (sufijos de unidad y tipo) y **explicar** por qué `USD` aparece en el nombre.
    5. **Diseñar** las métricas RED + GenAI de un agente (duración, tokens, coste, pasos) con atributos de **cardinalidad acotada**, y **conciliarlas** con la verdad del agente.
    6. **Calcular** el coste desde tokens con una **tabla de precios configurable** y **justificar** si derivarlo al escribir o al consultar.
    7. **Configurar** exemplars de extremo a extremo (SDK → OpenMetrics → Prometheus → traza) y **diagnosticar** por qué faltan.
    8. **Estimar** el error de un percentil según los *buckets*, y **comparar** histogramas clásicos con exponenciales/nativos.
    9. **Cuantificar** la cardinalidad (series = ∏ valores × buckets) y **ponerle presupuesto** a una métrica.
    """)

    md("""
    ## 🔁 Conexión con módulos anteriores
    """)
    md(details("1 · (Módulo 02) Tu p95 por minuto sube a 9 s en una instancia y a 3 s en otra. ¿Cuál es el p95 del conjunto: la media (6 s)?",
               "**No.** Los percentiles no se promedian: hay que combinar las *distribuciones* (sumar los contadores de cada bucket de ambas instancias) y calcular el percentil sobre la suma. Por eso las métricas de latencia se exportan como **histogramas**, no como percentiles pre-calculados."))
    md(details("2 · (Módulo 02) ¿Por qué `customer_id` es una buena etiqueta en un span y una mala etiqueta en una métrica?",
               "Cada valor distinto de una etiqueta crea una **serie temporal nueva** que se guarda y consulta para siempre. En un span, un atributo con muchos valores solo cuesta bytes de esa traza. Con 200 clientes × 5 estados × 15 buckets ya son 15 000 series; con `ticket_id` sería ilimitado."))
    md(details("3 · (Módulo 04) ¿En qué estado de estabilidad están las convenciones semánticas GenAI y qué implica para tus nombres de métrica?",
               "Estado **Development** (inestable): los nombres pueden cambiar (de hecho, las métricas de tokens han pasado de un histograma a *counters* + histogramas por operación). Conviene centralizar los nombres en un único módulo y fijar la versión de la spec que sigues."))

    code(boot("viz,otel"))
    code(SETUP + '''
STACK = check_stack("core+metrics")      # Prometheus es opcional: sin él las celdas «en vivo» se saltan
LIVE = not STACK.degraded
print("\\nModo:", "COMPLETO (stack real)" if LIVE else "DEGRADADO (sin Prometheus: se salta lo que lo necesita)")
''')

    # ------------------------------------------------------------------------------------------ 1 · intuición
    md("""
    ---
    # 1 · Intuición: las métricas son la señal *barata y constante*

    En el módulo 02 viste que una traza describe **una** petición y que una métrica **resume todas**. Aquí construimos las métricas de SupportOps en serio.
    Pensémoslo como el *dashboard de un coche*: no te cuenta cada metro recorrido (eso sería la traza), te da cuatro números —velocidad, revoluciones, combustible, temperatura— **calculados continuamente** y baratos de guardar. Si alguno se sale de rango, sabes *que* algo va mal y entonces abres la caja negra.

    | Si vienes de… | Métricas son… |
    |---|---|
    | **ML** | Las curvas de entrenamiento / métricas de validación por lote: un número por intervalo, no cada predicción |
    | **Backend** | `requests_total`, `latency_seconds`, `errors_total` por endpoint: el *RED* de cada servicio |
    | **SRE** | Los SLIs. Una alerta es una regla sobre una métrica; un SLO es una promesa sobre ella |

    **Coste:** una métrica cuesta **memoria por serie** (una serie = una combinación única de nombre + etiquetas), *no* por evento. Registrar 1 millón de peticiones o 10 cuesta lo mismo si las etiquetas son las mismas. Esa propiedad —y su reverso, que **cada valor nuevo de etiqueta multiplica el coste**— gobierna todo el módulo.

    ## Las tres rutas de OpenTelemetry a un almacén de métricas

    Un SDK OTel produce métricas OTLP; hay tres maneras razonables de llevarlas a un almacén tipo Prometheus:
    """)
    code('''
fig, ax = viz.canvas(15, 5.4, xlim=(0, 150), ylim=(0, 54))
P = viz.PALETTE
app = viz.box(ax, 2, 20, 20, 14, "SupportOps\\n(SDK OTel)\\nMeterProvider", P["traces"], bold=True)
col = viz.box(ax, 40, 38, 22, 11, "OTel Collector\\nexporter prometheus\\n:8889 (/metrics)", P["neutral"])
prom = viz.box(ax, 82, 38, 24, 11, "Prometheus\\n(scrape cada 15 s)", P["metrics"], bold=True)
direct = viz.box(ax, 82, 20, 24, 11, "Prometheus\\nreceptor OTLP\\n/api/v1/otlp/v1/metrics", P["metrics"])
col2 = viz.box(ax, 40, 3, 22, 11, "OTel Collector\\nexporter otlp_http\\no remote_write", P["neutral"])
mimir = viz.box(ax, 82, 3, 24, 11, "Mimir (multi-tenant,\\nlargo plazo)\\n/otlp  ·  remote write", P["metrics"], bold=True)
graf = viz.box(ax, 122, 20, 24, 14, "Grafana\\n(PromQL)\\nmódulo 10", P["logs"], bold=True)
viz.arrow(ax, viz.right(app), viz.left(col), "OTLP :4318", rad=-0.2)
viz.arrow(ax, viz.right(col), viz.left(prom), "scrape (pull)")
viz.arrow(ax, viz.right(app), viz.left(direct), "OTLP directo", P["metrics"])
viz.arrow(ax, viz.right(app), viz.left(col2), "OTLP", rad=0.2)
viz.arrow(ax, viz.right(col2), viz.left(mimir), "push")
for b in (prom, direct, mimir):
    viz.arrow(ax, viz.right(b), viz.left(graf), "", P["logs"], rad=0.0)
ax.text(40, 51.5, "RUTA A (la del curso)", color=P["neutral"], fontsize=9, fontweight="bold")
ax.text(82, 33.5, "RUTA B (histogramas nativos)", color=P["metrics"], fontsize=9, fontweight="bold")
ax.text(40, 15.2, "RUTA C (largo plazo / multi-tenant)", color=P["neutral"], fontsize=9, fontweight="bold")
ax.set_title("Tres rutas de las métricas OpenTelemetry hasta Grafana", loc="left")
plt.show()
''')
    md(observe("""
    - **Ruta A** es la del laboratorio (`stack/otel-collector/config.yaml`): el Collector recibe OTLP y **expone** un endpoint `/metrics` que Prometheus **raspa** (*pull*). Es la más compatible y la que conviene aprender primero.
    - **Ruta B** salta el Collector: Prometheus tiene un receptor OTLP (`--web.enable-otlp-receiver`, ya activo en el stack). Es la única que hoy conserva **histogramas exponenciales como nativos** (lo comprobaremos en la sección 9).
    - **Ruta C** es la de producción a escala: Mimir recibe OTLP o *remote write* con multi-tenencia y retención larga.
    - Las tres terminan igual en Grafana: **PromQL** sobre el mismo modelo de series.
    """))

    md(box("idea", "El mismo número, tres «dialectos»", """
    Un contador de peticiones es `counter` en OTel, `# TYPE ... counter` (con sufijo `_total`) en Prometheus y una *serie* con muestras `(t, v)` en el TSDB. El SDK de OTel **acumula en memoria** y exporta cada N segundos (60 s por defecto; el curso usa 5 s); Prometheus **raspa** cada 15 s. Entre ambos ritmos y el de PromQL (`rate(...[1m])`) aparecen casi todos los «¿por qué mi gráfico está vacío?».
    """))

    # ------------------------------------------------------------------------------------------ 2 · a mano
    md("""
    ---
    # 2 · Prometheus por dentro, a mano

    Antes de usar el SDK y PromQL, implementamos las dos funciones que sostienen casi todos los dashboards de latencia y tráfico: **`rate()`** y **`histogram_quantile()`**. Después las comparamos con las de un Prometheus real.

    ## 2.1 `rate()` a mano

    Un contador solo sube (salvo reinicios). Para saber «cuántas peticiones por segundo» hay que mirar cómo **crece** entre dos instantes. Dos dificultades:

    1. **Reinicios**: si el proceso se reinicia, el contador vuelve a 0. Una resta ingenua daría un valor negativo enorme. Prometheus detecta cada caída y suma el valor previo.
    2. **Bordes de la ventana**: las muestras no caen exactamente en los extremos de `[1m]`, así que Prometheus **extrapola** el crecimiento hasta los bordes (con límites para no inventar demasiado).

    $$\\text{rate}(t) = \\frac{\\text{incremento}}{\\text{rango}}\\cdot \\frac{\\text{intervalo extrapolado}}{\\text{intervalo muestreado}}$$

    donde *incremento* = suma de los saltos positivos (más el valor previo en cada reinicio), *intervalo muestreado* = `t_última − t_primera`, y se extrapola hasta cada borde solo si la distancia es menor que $1{,}1\\times$ el intervalo medio entre muestras (si no, media muestra).
    """)
    code('''
def prom_rate(samples, t_eval, range_s):
    """rate() de PromQL sobre `samples` = [(t, v)] ordenadas. Ventana (t_eval-range, t_eval]. None si hay < 2 muestras."""
    w = [(t, v) for t, v in samples if t_eval - range_s < t <= t_eval]
    if len(w) < 2:
        return None                                   # «rate() necesita ≥ 2 muestras dentro de la ventana»
    inc, prev = 0.0, w[0][1]
    for _, v in w[1:]:
        inc += (v - prev) if v >= prev else v        # tras un reinicio el contador «vuelve a 0 y crece hasta v»
        prev = v
    first_t, first_v, last_t = w[0][0], w[0][1], w[-1][0]
    sampled = last_t - first_t
    avg = sampled / (len(w) - 1)
    d_start, d_end = first_t - (t_eval - range_s), t_eval - last_t
    thr = avg * 1.1
    if d_start >= thr: d_start = avg / 2
    if inc > 0 and first_v >= 0:                      # un contador no pudo valer < 0: no extrapoles más allá del cero
        d_start = min(d_start, sampled * (first_v / inc))
    if d_end >= thr: d_end = avg / 2
    return inc * ((sampled + d_start + d_end) / sampled) / range_s

# Serie sintética: 15 s entre muestras, ≈ 1 petición/s, con un reinicio del proceso en t=150 s
rng = np.random.default_rng(SEED)
ts = np.arange(0, 300, 15.0); inc_per = rng.poisson(15, len(ts))
cnt, tot = [], 0
for t, k in zip(ts, inc_per):
    tot = k if t == 150 else tot + k                  # en t=150 el contador se reinicia
    cnt.append(tot)
samples = list(zip(ts, map(float, cnt)))
naive = [(samples[i][0], (samples[i][1] - samples[i - 1][1]) / 15) for i in range(1, len(samples))]
mine = [(t, prom_rate(samples, t, 60)) for t in ts[4:]]
print("En t=150 s el contador cae a", cnt[10], "(antes valía", cnt[9], ")")
''')
    code('''
fig, axes = plt.subplots(1, 2, figsize=(14, 3.9))
axes[0].step(ts, cnt, where="post", color=viz.PALETTE["metrics"], lw=2); axes[0].axvline(150, color="k", ls=":")
axes[0].set_title("Contador cumulativo con un reinicio (t = 150 s)"); axes[0].set_xlabel("segundos"); axes[0].set_ylabel("valor del contador")
axes[1].plot(*zip(*naive), color=viz.PALETTE["error"], lw=1.6, label="resta ingenua  (v[i] − v[i−1]) / 15 s")
axes[1].plot(*zip(*mine), color=viz.PALETTE["ok"], lw=2.4, label="rate(contador[60 s])  (a mano)")
axes[1].axhline(15 / 15, color="k", ls="--", lw=1, label="verdad ≈ 1 petición/s"); axes[1].set_ylim(-12, 3)
axes[1].set_title("La resta ingenua se va a −10 req/s; rate() es robusta al reinicio"); axes[1].set_xlabel("segundos"); axes[1].set_ylabel("req/s"); axes[1].legend()
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - A la izquierda, la caída del contador en t = 150 s es **un reinicio**, no «negativas peticiones».
    - A la derecha, la resta ingenua da un pico negativo (≈ −10 req/s). La implementación a mano **detecta la caída** y no se inmuta: da ≈ 1 req/s todo el tiempo.
    - Por eso en PromQL **siempre** se usa `rate()`/`increase()` sobre un contador, nunca el valor crudo ni una resta.
    """))

    md("""
    ## 2.2 `histogram_quantile()` a mano

    Un histograma *clásico* de Prometheus son contadores **acumulativos por bucket** (`le` = «menor o igual que»): `bucket{le="1"}` cuenta las observaciones ≤ 1 s, `bucket{le="2"}` las ≤ 2 s, … y `le="+Inf"` el total. No guarda ningún valor individual, así que el percentil es una **estimación por interpolación lineal dentro del bucket** donde cae el rango:

    $$q\\text{-ésimo percentil} \\approx l + (u-l)\\,\\frac{q\\cdot N - C_{<l}}{C_{\\le u}-C_{<l}}$$

    con $l, u$ los límites inferior y superior del bucket que contiene el rango $q\\cdot N$, $N$ el total y $C$ los acumulados. **Consecuencia:** el error depende de *dónde* pones los límites; si el p95 cae en un bucket de 1,6 a 3,2 s, Prometheus **no puede saber** si fueron 1,7 o 3,1 s.
    """)
    code('''
def hist_quantile(q, buckets):
    """histogram_quantile() de Prometheus. buckets = [(le, cuenta_acumulada)], ordenados y con le=inf al final."""
    total = buckets[-1][1]
    if total == 0: return float("nan")
    rank = q * total
    b = next(i for i, (_, c) in enumerate(buckets) if c >= rank)
    if b == len(buckets) - 1:                         # cae en el bucket +Inf: lo mejor que se sabe es «> último límite finito»
        return buckets[-2][0]
    lo = 0.0 if b == 0 else buckets[b - 1][0]
    c_lo = 0.0 if b == 0 else buckets[b - 1][1]
    hi, c_hi = buckets[b]
    return lo + (hi - lo) * (rank - c_lo) / (c_hi - c_lo)

def to_buckets(values, bounds):
    """Observaciones -> buckets acumulativos como los que exporta un histograma clásico."""
    idx = np.searchsorted(bounds, values, side="left")       # side="left" => le (≤): un valor igual al límite cuenta en ese bucket
    counts = np.bincount(idx, minlength=len(bounds) + 1)
    return list(zip([*bounds, float("inf")], np.cumsum(counts)))

tk = generate_tickets(1500, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)
runs_big = pd.DataFrame(to_rows(tk, run_tickets(SupportAgent(), tk)))
lat = runs_big.latency_s.values
print(f"{len(lat)} ejecuciones · latencia p50={np.quantile(lat,.5):.2f}s  p95={np.quantile(lat,.95):.2f}s  p99={np.quantile(lat,.99):.2f}s  máx={lat.max():.1f}s")
''')

    md("""
    ### ¿Cuánto error mete la elección de *buckets*?

    Probamos cinco disposiciones de *buckets* sobre **las mismas 1 500 latencias** de SupportOps y comparamos el percentil estimado con el verdadero (`np.quantile`):

    | Disposición | Qué es |
    |---|---|
    | `sdk_default` | Los límites por defecto del SDK (0, 5, 10, 25, … 10 000), pensados para **milisegundos** |
    | `spec_genai` | Los que **recomienda** la spec GenAI para `gen_ai.invoke_agent.duration` (×2 desde 0,1 s) |
    | `tuned` | Los ajustados a la distribución de SupportOps (los usa `MetricsInstrumentor`) |
    | `lineal_0.5` | Fino y regular: cada 0,5 s hasta 20 s |
    | `fino_x1.15` | Geométrico con razón 1,15 (≈ 7 % de error relativo máximo) |
    """)
    code('''
LAYOUTS = {
    "sdk_default": [0, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000],
    "spec_genai": SPEC_AGENT_DURATION_BOUNDARIES,
    "tuned": TUNED_AGENT_DURATION_BOUNDARIES,
    "lineal_0.5": [round(0.5 * i, 2) for i in range(1, 41)],
    "fino_x1.15": [round(0.1 * 1.15 ** i, 4) for i in range(0, 38)],
}
rows = []
for name, bounds in LAYOUTS.items():
    bk = to_buckets(lat, bounds)
    for q in (0.5, 0.95, 0.99):
        est, true = hist_quantile(q, bk), float(np.quantile(lat, q))
        rows.append({"layout": name, "buckets": len(bounds), "q": q, "estimado": est, "verdadero": true, "error_rel": (est - true) / true})
E = pd.DataFrame(rows)
display(E.pivot(index="layout", columns="q", values="error_rel").mul(100).round(1).add_suffix(" · error %").join(E.groupby("layout").buckets.first()).loc[list(LAYOUTS)])
''')
    code('''
fig, axes = plt.subplots(1, 2, figsize=(14.5, 4.2))
xs = np.sort(lat); axes[0].plot(xs, np.arange(1, len(xs) + 1) / len(xs), color="k", lw=2, label="CDF real de las latencias")
cols = {"sdk_default": viz.PALETTE["error"], "spec_genai": viz.PALETTE["warn"], "tuned": viz.PALETTE["ok"]}
for k, (n, c) in enumerate(cols.items()):
    for bnd in LAYOUTS[n]:
        if bnd <= 16: axes[0].plot([bnd, bnd], [0.02 + 0.045 * k, 0.02 + 0.045 * k + 0.035], color=c, lw=2)
    axes[0].plot([], [], color=c, lw=2, label=f"límites de «{n}»")
axes[0].set_xlim(0, 16); axes[0].set_xlabel("latencia del agente (s)"); axes[0].set_ylabel("fracción acumulada"); axes[0].set_title("Los límites de bucket deben caer donde está la masa"); axes[0].legend(loc="center right", fontsize=8)
piv = E.pivot(index="layout", columns="q", values="error_rel").loc[list(LAYOUTS)] * 100
piv.plot.bar(ax=axes[1], color=[viz.PALETTE["traces"], viz.PALETTE["metrics"], viz.PALETTE["error"]], width=.8)
axes[1].axhline(0, color="k", lw=.8); axes[1].set_ylabel("error relativo del percentil estimado (%)"); axes[1].set_xlabel(""); axes[1].set_title("Error de histogram_quantile() según la disposición"); plt.xticks(rotation=20)
axes[1].legend(title="percentil"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con `sdk_default` la masa de latencias (0,5–4 s) cae **casi entera en un solo bucket** (0–5 s): el p50 estimado interpola una recta y **se equivoca en torno a un 58 %**; el p99 en ≈ 20 %. (El p95 «acierta» solo por casualidad: cae cerca del borde de 5 s.)
    - La disposición recomendada por la spec (factor ×2) mejora (errores del 5 al 10 %), pero **no puedes controlar dónde caerá** tu percentil dentro de un bucket de 1,6 a 3,2 s.
    - `tuned` y los geométricos finos bajan el error del p50/p95 al 0–2 %. El **p99** es el más difícil con pocos puntos en la cola (ver `spec_genai` frente a `tuned`).
    - Regla práctica: pon **un límite justo en tu umbral de SLO** (p. ej. 3 s) y rejilla fina alrededor; o usa histogramas nativos (sección 9).
    """))

    md(box("elite", "Los buckets por defecto del SDK están pensados para milisegundos", """
    El SDK de OpenTelemetry usa por defecto `[0, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000]` (comprobado en la sección 3: lo vemos en el `/metrics`). Si tu unidad es **segundos** o **tokens** y no los cambias, casi todas tus observaciones caen en 1–2 buckets y `histogram_quantile()` devuelve basura **sin avisar** (el cálculo es válido; la resolución no). La spec lo resuelve con la API de *advisory* `explicit_bucket_boundaries_advisory` al crear el histograma (lo usa `MetricsInstrumentor`), o con una *View*.
    """))

    # ------------------------------------------------------------------------------------------ 3 · SDK
    md("""
    ---
    # 3 · Instrumentos, *views* y temporalidad en el SDK de OpenTelemetry

    ## 3.1 Qué instrumento uso para qué

    | Instrumento | Se llama… | Semántica | Ejemplo en SupportOps | Se exporta como |
    |---|---|---|---|---|
    | **Counter** | `add(n≥0)` en el camino de código | Solo suma (monotónico) | peticiones, tokens, coste | `_total` (Prometheus *counter*) |
    | **UpDownCounter** | `add(±n)` | Suma y resta | ejecuciones en curso | *gauge* (no monotónico) |
    | **Histogram** | `record(x)` | Distribución de valores | latencia, tokens por llamada | `_bucket/_sum/_count` |
    | **Gauge** (síncrono) | `set(x)` | Último valor | utilización del contexto | *gauge* |
    | **ObservableCounter / UpDownCounter / Gauge** | *callback* cada vez que se recolecta | Valor que **ya existe** fuera (tamaño de cola, memoria, cuota restante) | profundidad de cola | según el tipo |

    Regla mnemotécnica: **¿se puede sumar entre instancias? → Counter/UpDownCounter. ¿Interesa la distribución? → Histogram. ¿Es el valor de algo que ya existe y solo quieres leerlo? → Observable.** El *gauge* síncrono es el que más se abusa: guarda solo el **último** valor, así que un pico entre dos lecturas es invisible.
    """)
    code('''
fig, ax = viz.canvas(15, 4.6, xlim=(0, 150), ylim=(0, 46))
P = viz.PALETTE
q1 = viz.box(ax, 2, 31, 32, 10, "¿Cuenta algo que SOLO crece?\\n(peticiones, tokens, € )", P["neutral"])
q2 = viz.box(ax, 2, 16, 32, 10, "¿Quieres la DISTRIBUCIÓN?\\n(p95 de latencia, tamaño)", P["neutral"])
q3 = viz.box(ax, 2, 1, 32, 10, "¿Es un valor que YA existe\\ny solo lo lees? (cola, memoria)", P["neutral"])
a1 = viz.box(ax, 62, 31, 34, 10, "Counter\\n(UpDownCounter si también baja)", P["ok"], bold=True)
a2 = viz.box(ax, 62, 16, 34, 10, "Histogram\\n(buckets del SLO / exponencial)", P["metrics"], bold=True)
a3 = viz.box(ax, 62, 1, 34, 10, "Observable Gauge / Counter\\n(con callback)", P["traces"], bold=True)
w = viz.box(ax, 112, 16, 36, 12, "Gauge síncrono: solo si\\nel ÚLTIMO valor basta\\n(¡pierde los picos!)", P["error"])
for q, a in ((q1, a1), (q2, a2), (q3, a3)): viz.arrow(ax, viz.right(q), viz.left(a), "sí")
viz.arrow(ax, viz.bottom(q1), viz.top(q2), "no", rad=0); viz.arrow(ax, viz.bottom(q2), viz.top(q3), "no", rad=0)
viz.arrow(ax, viz.right(a2), viz.left(w), "no hace falta", P["error"], dashed=True)
ax.set_title("Elegir el instrumento", loc="left"); plt.show()
''')

    md("""
    ## 3.2 El SDK con un lector en memoria

    El *pipeline* del SDK es: **Instrumento → View (opcional) → Agregación → MetricReader → Exporter**. Un `InMemoryMetricReader` nos deja ver lo que se exportaría, sin red:
    """)
    code('''
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider as _MP
from opentelemetry.sdk.metrics.export import InMemoryMetricReader as _Mem
from opentelemetry.sdk.resources import Resource as _Res

reader = _Mem()
mp = _MP(metric_readers=[reader], resource=_Res.create({"service.name": "demo"}))
m = mp.get_meter("demo")
requests_c = m.create_counter("demo.requests", unit="{request}", description="peticiones")
active = m.create_up_down_counter("demo.active_runs", unit="{run}")
dur = m.create_histogram("demo.duration", unit="s", description="duración")                      # buckets por defecto del SDK
dur2 = m.create_histogram("demo.duration2", unit="s", explicit_bucket_boundaries_advisory=[0.5, 1, 2, 4])   # buckets «advisory»
util = m.create_gauge("demo.ctx_util", unit="1")
queue = {"depth": 7}
m.create_observable_gauge("demo.queue_depth", callbacks=[lambda opts: [Observation(queue["depth"], {"queue": "tickets"})]], unit="{ticket}")

for v in (0.3, 0.7, 1.2, 3.5):
    requests_c.add(1, {"status": "ok"}); dur.record(v, {"model": "mock-small"}); dur2.record(v, {"model": "mock-small"})
requests_c.add(1, {"status": "error"}); active.add(1); active.add(1); active.add(-1); util.set(0.42)
D = pd.DataFrame(metric_rows(reader))
D["detalle"] = [f"valor={r.value}" if isinstance(r.value, (int, float)) and r.value == r.value else f"count={r['count']} sum={r['sum']:.1f}" for _, r in D.iterrows()]
display(D[["name", "unit", "kind", "attributes", "detalle"]])
print("buckets por defecto del SDK :", D[D.name == "demo.duration"].iloc[0].bounds)
print("buckets con advisory         :", D[D.name == "demo.duration2"].iloc[0].bounds)
''')
    md("""
    Fíjate en que **no hay un valor por evento**: el SDK ha *agregado* (suma, o contadores por bucket) y solo guardará una cifra por combinación de atributos. Eso es lo que hace a las métricas baratas… y lo que impide recuperar un evento concreto (para eso están los *exemplars*, sección 6).

    ## 3.3 *Views*: cambiar la agregación o quitar atributos **sin tocar el código**

    Una *View* se aplica al construir el `MeterProvider`. Sirve para (a) **cambiar buckets**, (b) **quitar atributos** peligrosos (`attribute_keys`) o (c) pasar a **histograma exponencial**. Es la defensa de último recurso contra la cardinalidad: si una librería de terceros etiqueta con `customer_id`, la View lo elimina antes de que cree series.
    """)
    code('''
from opentelemetry.sdk.metrics.view import View, ExplicitBucketHistogramAggregation, ExponentialBucketHistogramAggregation
from opentelemetry.sdk.metrics import Histogram as _H

def n_points(views):
    rd = _Mem(); p = _MP(metric_readers=[rd], views=views); mm = p.get_meter("x")
    c = mm.create_counter("x.requests"); h = mm.create_histogram("x.duration", unit="s")
    for i in range(300):
        at = {"model": "mock-small", "status": "ok" if i % 10 else "error", "customer.id": f"C-{i % 120:04d}"}
        c.add(1, at); h.record(0.5 + (i % 7) * 0.3, at)
    rows = metric_rows(rd); return {n: sum(1 for r in rows if r["name"] == n) for n in ("x.requests", "x.duration")}

print("sin view                              :", n_points([]))
print("View attribute_keys (sin customer.id) :", n_points([View(instrument_name="x.*", attribute_keys={"model", "status"})]))
# ¡Cuidado! Dos views que casan con el MISMO instrumento producen DOS streams con el mismo nombre:
solape = [View(instrument_name="x.*", attribute_keys={"model", "status"}), View(instrument_type=_H, aggregation=ExponentialBucketHistogramAggregation())]
rd = _Mem(); pp = _MP(metric_readers=[rd], views=solape); hh = pp.get_meter("x").create_histogram("x.duration"); hh.record(1.0, {"model": "m", "customer.id": "C-1"})
print("views solapadas ->", sorted((r["name"], r["kind"], len(r["attributes"])) for r in metric_rows(rd)))
# Lo correcto: UNA view por instrumento que combine criterios, atributos y agregación
una = [View(instrument_name="x.duration", attribute_keys={"model", "status"}, aggregation=ExponentialBucketHistogramAggregation())]
print("una sola view (exponencial + sin id)  :", n_points(una))
''')
    md("""
    La primera línea muestra **120 series por instrumento** (una por cada `customer.id`, atributo accidental); con `attribute_keys` caen a 2. **Trampa verificada:** si dos *views* casan con el mismo instrumento, el SDK crea **dos *streams*** con el mismo nombre (una vez como histograma clásico con 2 atributos y otra como exponencial con 3); al exportar a Prometheus chocan. Define **una** View por instrumento que combine criterios, atributos y agregación.

    ## 3.4 Temporalidad: *cumulative* frente a *delta*

    Cuando el SDK exporta cada N segundos puede enviar:

    - **Cumulative** (por defecto): «desde que arranqué llevo 12». Cada punto lleva el total acumulado. Es lo que espera Prometheus.
    - **Delta**: «en este intervalo hubo 7». Cada punto lleva solo lo nuevo. Es lo natural en StatsD/Datadog y reduce memoria en el emisor cuando hay muchas series efímeras.

    Veámoslo con dos lectores sobre el mismo contador (un intervalo sin actividad al final):
    """)
    code('''
from opentelemetry.sdk.metrics.export import AggregationTemporality as AT
from opentelemetry.sdk.metrics import Counter as _C
r_cum, r_del = _Mem(), _Mem(preferred_temporality={_C: AT.DELTA})
p = _MP(metric_readers=[r_cum, r_del]); cc = p.get_meter("t").create_counter("t.events")
hist = []
for cycle, n in enumerate([5, 7, 0, 3], start=1):
    for _ in range(n): cc.add(1)
    vc = [r["value"] for r in metric_rows(r_cum) if r["name"] == "t.events"]
    vd = [r["value"] for r in metric_rows(r_del) if r["name"] == "t.events"]
    hist.append({"intervalo": cycle, "eventos reales": n, "cumulative exporta": vc[0] if vc else "—", "delta exporta": vd[0] if vd else "— (sin punto)"})
display(pd.DataFrame(hist).set_index("intervalo"))
''')
    code('''
# Qué pasa si se PIERDE una exportación (red, Collector caído) y si el proceso se reinicia
true_inc = np.array([5, 9, 6, 8, 7, 10, 4, 8, 9, 6]); lost = 4                       # se pierde el intervalo 5 (índice 4)
cum = np.cumsum(true_inc).astype(float)
delta_seen = np.where(np.arange(10) == lost, 0, true_inc)                                 # el punto delta del intervalo 5 nunca llega
cum_seen = np.where(np.arange(10) == lost, np.nan, cum)                                   # tampoco llega el punto cumulative del intervalo 5...
increase_cum = np.nanmax(cum_seen) - np.nanmin(cum_seen[~np.isnan(cum_seen)][:1])        # ...pero el SIGUIENTE ya trae el total acumulado
fig, axes = plt.subplots(1, 2, figsize=(14, 3.9))
axes[0].bar(range(10), true_inc, color="#cbd5e1", label="eventos reales por intervalo")
axes[0].bar(range(10), delta_seen, color=viz.PALETTE["traces"], label="llegan como DELTA"); axes[0].set_title(f"Delta: el intervalo perdido se pierde para siempre (suma {delta_seen.sum()} de {true_inc.sum()})")
axes[0].legend(); axes[0].set_xlabel("intervalo de exportación")
axes[1].plot(range(10), cum, color="#cbd5e1", lw=6, label="contador real"); axes[1].plot(range(10), cum_seen, "o-", color=viz.PALETTE["metrics"], label="llegan como CUMULATIVE")
axes[1].set_title(f"Cumulative: el siguiente punto repara el hueco (increase = {increase_cum:.0f} + {cum_seen[0]:.0f} inicial)"); axes[1].legend(); axes[1].set_xlabel("intervalo de exportación")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - En la tabla: *cumulative* repite el total aunque no haya actividad (12 en el intervalo 3); *delta* **no exporta nada** si no hubo eventos.
    - Gráfico izquierdo: con *delta* un lote perdido deja un agujero permanente (la suma sale corta). Con *cumulative* (derecha) el punto siguiente ya incluye lo acumulado y **`increase()` se autorrepara**. Es la razón por la que Prometheus es *cumulative-first*.
    - El precio: cumulative obliga al emisor a recordar todas las series que ha visto (memoria), y un reinicio del proceso crea un salto a 0 que `rate()` sabe tratar (sección 2.1).
    """))
    md(box("elite", "Prometheus rechaza *delta* por defecto (y por eso cuesta tan caro un ajuste olvidado)", """
    Si pones `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE=delta` (o `preferred_temporality` en Python) y exportas **directo a Prometheus**, el receptor OTLP responde **HTTP 500** con `invalid temporality and type combination for metric "..."` y descarta el lote: las gráficas quedan vacías sin otro síntoma que un `Failed to export metrics batch` en el log del emisor. Lo verificamos en vivo en la sección 7. Prometheus tiene dos *feature flags* experimentales (`otlp-deltatocumulative`, que convierte delta→cumulative en memoria, y `otlp-native-delta-ingestion`) descritos en su `feature_flags.md`; el Collector, en cambio, **acumula** deltas en su exporter `prometheus`. Regla de oro: **a Prometheus/Mimir, cumulative**.
    """))

    # ------------------------------------------------------------------------------------------ 4 · nombres
    md("""
    ---
    # 4 · De `gen_ai.client.inference.duration` a `gen_ai_client_inference_duration_seconds_bucket`

    Los nombres OTel llevan puntos y unidades (UCUM); Prometheus (hasta 2.x) solo admitía `[a-zA-Z0-9_:]` y por convención añade **sufijos de tipo y de unidad**. La *spec* de compatibilidad (`prometheus_and_openmetrics.md`, estable) fija las reglas y Prometheus 3 las expone como `otlp.translation_strategy` (por defecto `UnderscoreEscapingWithSuffixes`):

    1. Los caracteres no válidos (`.`, `-`) → `_`, y los `_` repetidos se colapsan.
    2. Se **elimina lo que va entre llaves** de la unidad (`{token}`, `{request}` son *anotaciones*, no unidades) y la unidad UCUM restante se traduce a una palabra (`s` → `seconds`, `By` → `bytes`). Se añade como sufijo **antes** del sufijo de tipo, salvo que el nombre ya termine así.
    3. Un contador monotónico recibe `_total`.
    4. Un *gauge* con unidad `1` recibe `_ratio` (comportamiento observado en el exporter del Collector 0.162).
    5. Un histograma genera `_bucket`, `_sum` y `_count`.
    6. Los atributos pasan a etiquetas con las mismas reglas (`gen_ai.request.model` → `gen_ai_request_model`).

    Lo implementamos a mano y lo **verificamos contra el Prometheus real** en la sección 7:
    """)
    code(r"""
import re
UNIT_WORDS = {"s": "seconds", "ms": "milliseconds", "us": "microseconds", "ns": "nanoseconds", "min": "minutes", "h": "hours", "d": "days",
              "By": "bytes", "KiBy": "kibibytes", "MiBy": "mebibytes", "GiBy": "gibibytes", "%": "percent", "Cel": "celsius", "Hz": "hertz"}

def prom_name(name: str, unit: str = "", kind: str = "sum", monotonic: bool = True) -> list[str]:
    '''Nombre(s) de serie en Prometheus de una métrica OTel (estrategia UnderscoreEscapingWithSuffixes).'''
    base = re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9_:]", "_", name))
    u = re.sub(r"\{[^}]*\}", "", unit or "").strip()                       # {token}, {request}... se descartan
    word = UNIT_WORDS.get(u, re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9_]", "_", u))) if u and u != "1" else ""
    if kind == "gauge" and u == "1":
        word = "ratio"
    if word and not base.endswith("_" + word):
        base += "_" + word                                                  # la unidad va ANTES del sufijo de tipo
    if kind == "sum" and monotonic and not base.endswith("_total"):
        base += "_total"
    return [base + sfx for sfx in ("_bucket", "_sum", "_count")] if kind == "histogram" else [base]

casos = [("gen_ai.client.inference.duration", "s", "histogram", True), ("gen_ai.client.inference.usage.input_tokens", "{token}", "sum", True),
         ("supportops.agent.requests", "{request}", "sum", True), ("supportops.agent.active_runs", "{run}", "sum", False),
         ("supportops.llm.cost", "USD", "sum", True), ("supportops.llm.context_utilization", "1", "gauge", False),
         ("supportops.agent.request.cost", "USD", "histogram", True), ("process.memory.usage", "By", "sum", False)]
pd.DataFrame([{"nombre OTel": n, "unidad": u, "tipo": k + ("" if k != "sum" else (" monotónico" if m else " no monotónico")),
               "serie(s) en Prometheus": ", ".join(prom_name(n, u, k, m)[:1]) + (" (+_sum,_count)" if k == "histogram" else "")} for n, u, k, m in casos])
""")
    md("""
    La fila de `supportops.llm.cost` es la «sorpresa» honesta del diseño: `USD` **no es una unidad UCUM conocida por el traductor**, así que se pega tal cual (`..._USD_total`, con mayúsculas). Tienes tres salidas: (1) vivir con ello (es consistente y estable); (2) usar la anotación `{usd}`, que se descarta y deja `supportops_llm_cost_total`; (3) con Prometheus 3, `translation_strategy: NoUTF8EscapingWithSuffixes`, que conserva los puntos (`supportops.llm.cost_USD_total`). Elige **una vez** y documenta: cambiarlo después rompe dashboards y alertas.

    ### Identidad de la serie: `job`, `instance` y `target_info`

    Además del nombre y los atributos, cada serie lleva etiquetas de **recurso**. Hay dos formas de que lleguen, y el curso usa la antigua por simplicidad:

    | Mecanismo | Dónde | Efecto |
    |---|---|---|
    | `resource_to_telemetry_conversion` (Collector) | `stack/otel-collector/config.yaml` | **Copia todos los atributos de recurso a etiquetas** de cada serie. Simple, pero engorda cada serie y mezcla identidad con descripción. En el Collector 0.162 está **marcado como obsoleto** (el log avisa: *«resource_to_telemetry_conversion is deprecated; use resource_constant_labels instead»*) |
    | `target_info` + `promote_resource_attributes` (Prometheus, receptor OTLP) | `prometheus.yml` → `otlp:` | Los recursos van a una serie `target_info{job, instance, ...}` que se une **al consultar**; solo promueves a etiqueta las pocas que quieras (`service.name`, `deployment.environment.name`…). Es la recomendación de la guía OTel de Prometheus |

    En ambos casos `service.name` → `job` y `service.instance.id` → `instance`. **Esto importa:** `service.instance.id` debe ser **único por instancia**; si dos procesos comparten el mismo, sus contadores se mezclan en una sola serie y `rate()` da basura (sección «errores comunes»).
    """)

    # ------------------------------------------------------------------------------------------ 5 · RED + GenAI
    md("""
    ---
    # 5 · RED + métricas GenAI para SupportOps

    **RED** (Tom Wilkie): *Rate, Errors, Duration* por servicio. Para un agente añadimos lo que lo hace distinto: **tokens, coste y pasos**. Estas son las métricas de `MetricsInstrumentor` (el código está en `supportops/otel_metrics.py`):

    | Pregunta | Métrica OTel (tipo · unidad) | Atributos (acotados) |
    |---|---|---|
    | ¿Cuántas peticiones y con qué resultado? (R, E) | `supportops.agent.requests` (Counter `{request}`) | `supportops.status`, `supportops.intent`, `supportops.customer.tier`, `gen_ai.agent.name` |
    | ¿Cuánto tarda el agente? (D) | `gen_ai.invoke_agent.duration` (Histogram `s`) | `gen_ai.agent.name`, `gen_ai.request.model`, `error.type`, tier |
    | ¿Cuánto tarda cada llamada al LLM? | `gen_ai.client.inference.duration` (Histogram `s`) | `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `error.type` |
    | ¿Cuánto tarda cada herramienta? | `gen_ai.execute_tool.duration` (Histogram `s`) | `gen_ai.tool.name`, `error.type` |
    | ¿Cuántos tokens gastamos? | `gen_ai.client.inference.usage.{input,output}_tokens` (Counter `{token}`) | `gen_ai.request.model`, `gen_ai.token.modality`… |
    | ¿Qué tamaño tiene una llamada? (percentiles) | `gen_ai.client.inference.operation.{input,output}_tokens` (Histogram `{token}`) | `gen_ai.request.model`… |
    | ¿Cuántos pasos da el agente? (bucles) | `gen_ai.invoke_agent.{inference_calls,tool_calls}` (Histogram) | agente, tier |
    | ¿Cuánto cuesta? | `supportops.llm.cost` (Counter `USD`), `supportops.agent.request.cost` (Histogram `USD`) | `gen_ai.request.model` |
    | ¿Cuánto contexto usamos? | `supportops.llm.context_utilization` (Gauge `1`) | `gen_ai.request.model` |
    | ¿Cuántas ejecuciones hay en curso? (saturación) | `supportops.agent.active_runs` (UpDownCounter `{run}`) | `gen_ai.agent.name` |

    > ⚠️ **Estado de la spec (verificado contra `open-telemetry/semantic-conventions-genai`, rama `main`, refs a semconv v1.44.0).** Todas las métricas `gen_ai.*` están en estado **Development**. Las de tokens ya **no** son el histograma único `gen_ai.client.token.usage` de versiones anteriores: ahora hay *counters* de uso (`gen_ai.client.inference.usage.*`, para gasto/coste) y *histogramas por operación* (`gen_ai.client.inference.operation.*`, solo para percentiles). La duración de inferencia es `gen_ai.client.inference.duration` y `gen_ai.client.operation.duration` queda para operaciones que **no** son inferencia. Las bibliotecas de auto-instrumentación (módulo 06) pueden seguir emitiendo los nombres antiguos: comprueba la versión de la spec que cumple tu librería.

    **Dos decisiones de diseño que merecen explicación:**

    1. *Se registran DENTRO del span activo.* `MetricsInstrumentor` se compone **después** de `OTelInstrumentor` (`CompositeInstrumentor(OTelInstrumentor(tel, emit_metrics=False), MetricsInstrumentor(...))`), de modo que cuando llama a `record()` ya hay un span sampled activo y el SDK adjunta un *exemplar* con su `trace_id`. `emit_metrics=False` evita que A y B cuenten lo mismo dos veces.
    2. *Las llamadas fallidas también cuentan.* Un error del proveedor registra duración (con `error.type`) y suma **0 tokens** con `modality=unknown`, tal como pide la spec: así el *denominador* de la tasa de error es correcto.

    Ejecutemos 400 tickets (200 en `FAST_DEV_RUN`) **en memoria** y conciliemos las métricas con la verdad del agente:
    """)
    code('''
TRACES = setup_telemetry("supportops-agent", mode="memory", metrics=False, logs=False, deterministic_ids=True)   # solo trazas (para exemplars)
MP, READER = make_meter_provider(otlp_endpoint=None, memory=True)                                              # métricas: lector en memoria
MI = MetricsInstrumentor(MP)
AGENT = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(TRACES, emit_metrics=False), MI))
N = 200 if FAST_DEV_RUN else 400
TK = generate_tickets(N, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)
RES = run_tickets(AGENT, TK)
R = pd.DataFrame(to_rows(TK, RES)); R["steps"] = R.n_llm_calls + R.n_tool_calls
ROWS = metric_rows(READER)        # OJO: cada collect() del lector vacía los exemplars: léelos UNA vez
M = pd.DataFrame(ROWS)
print(f"{len(R)} tickets -> {len(M)} puntos de métricas en {M.name.nunique()} métricas distintas")
display(M.groupby(["name", "kind", "unit"]).agg(series=("attributes", "size")).reset_index().sort_values("name"))
''')
    code('''
def total(name, **attrs):
    sel = M[M.name == name]
    for k, v in attrs.items(): sel = sel[sel.attributes.map(lambda a: a.get(k) == v)]
    return sel["value"].sum() if sel["kind"].iloc[0] in ("sum", "gauge") else sel["count"].sum()

rec = [
    ("peticiones", total("supportops.agent.requests"), len(R)),
    ("  … estado «ok»", total("supportops.agent.requests", **{"supportops.status": "ok"}), (R.status == "ok").sum()),
    ("tokens de entrada", total("gen_ai.client.inference.usage.input_tokens"), R.input_tokens.sum()),
    ("tokens de salida", total("gen_ai.client.inference.usage.output_tokens"), R.output_tokens.sum()),
    ("coste USD (contador)", total("supportops.llm.cost"), R.cost_usd.sum()),
    ("histograma invoke_agent: cuenta", total("gen_ai.invoke_agent.duration"), len(R)),
    ("histograma invoke_agent: suma (s)", M[M.name == "gen_ai.invoke_agent.duration"]["sum"].sum(), R.latency_s.sum()),
    ("llamadas LLM (cuenta de chat)", total("gen_ai.client.inference.duration"), R.n_llm_calls.sum()),
    ("llamadas a herramientas", total("gen_ai.execute_tool.duration"), R.n_tool_calls.sum()),
]
C = pd.DataFrame(rec, columns=["magnitud", "según las MÉTRICAS", "según el AGENTE (verdad)"])
C["coincide"] = np.isclose(C.iloc[:, 1].astype(float), C.iloc[:, 2].astype(float), rtol=1e-3, atol=1e-3).tolist()
C["coincide"] = C.coincide.map({True: "✅", False: "❌"})
display(C.round(4))
''')
    md("""
    Esta tabla es la **prueba de integridad** que deberías automatizar en CI: si las métricas no cuadran con la verdad del agente, ninguna alerta que construyas encima es de fiar (típico: un `return` temprano que se salta el `record()`, o un reintento que cuenta dos veces). Las diferencias de céntimos del coste vienen de que el agente redondea `cost_usd` a 6 decimales por ticket.
    """)
    code('''
fig, axes = plt.subplots(2, 2, figsize=(14.5, 8))
# (a) peticiones por estado e intención
rq = M[M.name == "supportops.agent.requests"].copy(); rq["status"] = rq.attributes.map(lambda a: a["supportops.status"]); rq["intent"] = rq.attributes.map(lambda a: a["supportops.intent"])
pv = rq.pivot_table(index="intent", columns="status", values="value", aggfunc="sum", fill_value=0)
pv.plot.barh(stacked=True, ax=axes[0, 0], width=.75, color=[{"ok": viz.PALETTE["ok"], "escalated": viz.PALETTE["traces"], "degraded": viz.PALETTE["warn"], "error": viz.PALETTE["error"], "max_steps": viz.PALETTE["neutral"]}[c] for c in pv.columns]); axes[0, 0].legend(loc="lower right", fontsize=8); axes[0, 0].set_title("(a) supportops.agent.requests por intención y estado"); axes[0, 0].set_xlabel("peticiones")
# (b) histograma de tokens de entrada: buckets de la spec frente a los ajustados
for lab, bounds, col in (("spec GenAI (×4)", SPEC_TOKEN_BOUNDARIES, viz.PALETTE["warn"]), ("ajustados", TUNED_INPUT_TOKEN_BOUNDARIES, viz.PALETTE["ok"])):
    cnt = np.bincount(np.searchsorted(bounds, R.input_tokens.values, side="left"), minlength=len(bounds) + 1)[:-1]
    axes[0, 1].step(bounds, cnt, where="pre", color=col, lw=2, label=f"{lab}: {int((cnt > 0).sum())} buckets con datos")
axes[0, 1].set_xscale("log"); axes[0, 1].set_title("(b) tokens de entrada por ticket: resolución de los buckets"); axes[0, 1].set_xlabel("tokens (límite superior del bucket, escala log)"); axes[0, 1].set_ylabel("observaciones"); axes[0, 1].legend()
# (c) coste por petición (histograma real exportado)
hh = M[M.name == "supportops.agent.request.cost"].iloc[0]; b = np.array(hh.bounds); c = np.array(hh.buckets)
axes[1, 0].bar(range(len(c)), c, color=viz.PALETTE["metrics"]); axes[1, 0].set_xticks(range(len(c))); axes[1, 0].set_xticklabels([f"≤{x*1e3:.2g}m" for x in b] + ["+Inf"], rotation=60, fontsize=7)
axes[1, 0].set_title("(c) coste por petición (USD, en milésimas: «m») — histograma exportado"); axes[1, 0].set_ylabel("peticiones")
# (d) coste: precios ilustrativos frente a un «what-if» con otra tabla
alt = PriceTable({"mock-small": (0.80, 4.00)}, note="what-if")
base_cost = R.cost_usd.sum(); alt_cost = sum(alt.cost("mock-small", r.input_tokens, r.output_tokens) for r in R.itertuples())
axes[1, 1].bar(["tabla ilustrativa\\n(0,25 / 1,25 USD/Mtok)", "what-if\\n(0,80 / 4,00)"], [base_cost, alt_cost], color=[viz.PALETTE["metrics"], viz.PALETTE["error"]])
for i, v in enumerate((base_cost, alt_cost)): axes[1, 1].text(i, v, f"{v:.4f} USD", ha="center", va="bottom")
axes[1, 1].set_title(f"(d) mismo tráfico ({len(R)} tickets), distinta tabla de precios"); axes[1, 1].set_ylabel("coste total (USD)")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **(a)** Cada barra es una combinación `intención × estado`: 4 intenciones + `unknown` × 5 estados = **≤ 25 series** para el contador de peticiones. Eso es cardinalidad acotada.
    - **(b)** Con los límites de la spec (factor ×4: 256, 1024, …) casi todos los tokens de entrada (≈ 350–850) caen en **un solo bucket** (256–1024): el p95 sería la interpolación de una recta. Los límites ajustados reparten la masa en 6–8 buckets. La spec pretende servir a muchos sistemas; **tú** debes ajustar a tu carga.
    - **(c)** Un coste por petición de décimas de milésima de dólar con una cola larga (los tickets con bucles de herramientas cuestan 5× más): un histograma de coste responde «¿cuál es mi p95 de coste por ticket?» sin guardar cada ticket.
    - **(d)** El coste es **función de la tabla de precios**, no un hecho medido: cambiarla reescala todo. Los precios del curso son **ilustrativos**; los de tu proveedor cambian con frecuencia.
    """))

    md("""
    ## 5.1 Del token al dólar: la tabla de precios

    El coste de una llamada es

    $$C_{\\text{llamada}} = \\frac{n_{\\text{in}}\\,p_{\\text{in}} + n_{\\text{out}}\\,p_{\\text{out}}}{10^{6}}, \\qquad C_{\\text{ticket}}=\\sum_{\\text{llamadas}} C_{\\text{llamada}}$$

    con $n$ = tokens y $p$ = precio en USD por **millón** de tokens. `PriceTable` guarda `{modelo: (p_in, p_out)}`. Se configura por código o por entorno (`SUPPORTOPS_PRICES_JSON='{"mi-modelo": [0.5, 2.0]}'`) y **avisa de modelos desconocidos** (`unknown_models`) en vez de contar 0 en silencio.
    """)
    code('''
print(ILLUSTRATIVE_PRICES.note, "->", dict(ILLUSTRATIVE_PRICES.prices))
t = PriceTable({"mi-modelo-A": (1.0, 4.0)})                       # tu tabla (ficticia)
print("coste de 1 llamada de 2 000 tokens in / 300 out con mi-modelo-A :", f"{t.cost('mi-modelo-A', 2000, 300):.6f} USD")
print("modelo desconocido -> coste", t.cost("otro", 2000, 300), "(¡silencioso!)  · knows('otro') =", t.knows("otro"))
# Un instrumentor con la tabla equivocada: el contador de coste queda a 0 y MI.unknown_models lo delata
mp2, rd2 = make_meter_provider(otlp_endpoint=None); mi2 = MetricsInstrumentor(mp2, prices=t)
run_tickets(SupportAgent(instrumentor=mi2), TK[:20])
print("modelos sin precio detectados:", mi2.unknown_models, "· coste exportado:", sum(r["value"] for r in metric_rows(rd2) if r["name"] == "supportops.llm.cost"))
''')
    md(box("elite", "¿Coste al escribir o al consultar?", """
    **Al escribir** (lo que hacemos): el `Counter` suma dólares con el precio vigente *en ese momento*. Ventajas: el histórico es inmutable (cuadra con la factura de aquel día) y la consulta es trivial (`rate(...)`). Inconveniente: si te equivocas de precio, ya está escrito.
    **Al consultar**: exportas solo tokens y un *gauge* `price_usd_per_mtok{model,direction}`; el dólar sale de multiplicar en PromQL (`sum by (model)(rate(tokens_total[5m])) * on(model) group_left() price`). Ventaja: cambiar un precio re-calcula también el pasado y puedes ensayar tarifas («what-if»). Inconveniente: consultas más complejas y un precio que cambia reescribe la historia.
    **Práctica habitual:** tokens como verdad primaria + coste derivado para dashboards, y **conciliar mensualmente** con la factura del proveedor (módulo 13).
    """))

    # ------------------------------------------------------------------------------------------ 6 · exemplars
    md("""
    ---
    # 6 · Exemplars: del percentil a la traza

    Un histograma te dice «el p99 es 12 s», pero no **qué petición** tardó 12 s. Un *exemplar* es un **ejemplo concreto** guardado junto al dato agregado: `(valor, instante, trace_id, span_id)`. En Grafana se pintan como rombos sobre la gráfica; un clic abre la traza en Tempo.

    **Cómo se produce, paso a paso** (todo debe cumplirse; si falta un eslabón no hay rombos):

    | # | Eslabón | Dónde | Detalle |
    |---|---|---|---|
    | 1 | Hay un **span activo** al llamar a `record()`/`add()` | tu código | por eso componemos el instrumentor de métricas *dentro* del de trazas |
    | 2 | El **filtro** admite la medición | SDK | por defecto `trace_based`: solo si el span está *sampled*. `OTEL_METRICS_EXEMPLAR_FILTER` = `always_on` / `always_off` / `trace_based` |
    | 3 | El **reservorio** elige qué ejemplares conserva | SDK | para histogramas explícitos, `AlignedHistogramBucketExemplarReservoir` (uno por bucket) |
    | 4 | Se exportan en OTLP | SDK → Collector | van dentro del punto de datos |
    | 5 | Se exponen en **OpenMetrics** | Collector | `enable_open_metrics: true` en el exporter `prometheus` (ya está en `config.yaml`) |
    | 6 | Prometheus los **almacena** | Prometheus | `--enable-feature=exemplar-storage` (ya está activo); buffer circular en memoria (≈ 100 bytes por exemplar con solo `trace_id`) |
    | 7 | Grafana los **dibuja y enlaza** | Grafana | datasource con `exemplarTraceIdDestinations` → Tempo (aprovisionado); el panel pide `exemplar: true` |

    La spec de compatibilidad añade tres reglas que explican «misterios»: los exemplars de **gauges y de sumas no monotónicas se descartan** (no hay rombos en `active_runs`), en un **contador** se conserva solo el **último**, y OpenMetrics 1.0 limita las etiquetas de un exemplar a **128 caracteres** (`trace_id` + `span_id` ocupan ≈ 63).

    ### El reservorio a mano: ¿qué ejemplares sobreviven?
    """)
    code('''
def simulate_reservoirs(values, bounds, k_fixed=1, interval=40, seed=0):
    """Dos estrategias sobre un flujo de observaciones, reiniciando cada `interval` mediciones (un intervalo de exportación)."""
    rng = np.random.default_rng(seed); kept_aligned, kept_fixed = [], []
    for start in range(0, len(values), interval):
        chunk = list(enumerate(values[start:start + interval], start))
        slots = {}                                                         # ALIGNED: un hueco por bucket; la última medición lo sobrescribe
        for i, v in chunk: slots[int(np.searchsorted(bounds, v, side="left"))] = (i, v)
        kept_aligned += list(slots.values())
        res, seen = [], 0                                                  # SIMPLE FIXED SIZE: muestreo uniforme de reservorio (Algoritmo R)
        for i, v in chunk:
            seen += 1
            if len(res) < k_fixed: res.append((i, v))
            elif (j := int(rng.integers(0, seen))) < k_fixed: res[j] = (i, v)
        kept_fixed += res
    return kept_aligned, kept_fixed

vals = R.latency_s.values
ka, kf = simulate_reservoirs(vals, TUNED_AGENT_DURATION_BOUNDARIES)
fig, axes = plt.subplots(1, 2, figsize=(14, 3.9), sharey=True)
for ax, kept, ttl, col in ((axes[0], ka, f"Aligned por bucket (el de los histogramas): {len(ka)} ejemplares", viz.PALETTE["ok"]),
                            (axes[1], kf, f"Uniforme de tamaño 1 (el de counters): {len(kf)} ejemplares", viz.PALETTE["warn"])):
    ax.scatter(range(len(vals)), vals, s=6, color="#cbd5e1"); ax.scatter(*zip(*[(i, v) for i, v in kept]), s=26, color=col, zorder=3)
    ax.axhline(np.quantile(vals, .95), color="k", ls=":"); ax.set_yscale("log"); ax.set_title(ttl, fontsize=10); ax.set_xlabel("orden de llegada del ticket")
axes[0].set_ylabel("latencia (s)")
big = lambda kept: sum(v >= np.quantile(vals, .95) for _, v in kept)
plt.tight_layout(); plt.show()
print(f"Ejemplares de la COLA (≥ p95): aligned={big(ka)} · uniforme={big(kf)}  (de {int((vals >= np.quantile(vals, .95)).sum())} observaciones de cola)")
''')
    md(observe("""
    - Cada punto gris es un ticket; los de color son los que **se quedan como exemplar** en su intervalo de exportación (el recuento va en el título).
    - El reservorio **alineado con los buckets** garantiza al menos un ejemplar por cada bucket con datos, **incluidos los de la cola**: siempre hay algo que clicar en «el bucket de 12 s». El uniforme de tamaño 1 elige al azar sobre todo entre peticiones normales (la cola es rara), así que la cola queda casi sin representación.
    - Moraleja: los exemplars de **histogramas** son más útiles que los de contadores precisamente por esta alineación.
    """))
    md("Ahora los exemplars **reales** que produjo el SDK en la ejecución en memoria, y comprobamos que cada uno apunta a una traza que existe:")
    code('''
EX = []
for r in ROWS:
    if r["name"] == "gen_ai.invoke_agent.duration" and r["kind"] == "histogram":
        for e in r["exemplars"]: EX.append({**e, "model": r["attributes"].get("gen_ai.request.model"), "error.type": r["attributes"].get("error.type")})
EX = pd.DataFrame(EX).sort_values("value", ascending=False)
SPANS = pd.DataFrame(TRACES.span_records()); trace_ids = set(SPANS.trace_id)
EX["traza_existe"] = EX.trace_id.isin(trace_ids)
print(f"{len(EX)} exemplars en gen_ai.invoke_agent.duration · con trace_id: {EX.trace_id.notna().sum()} · apuntan a una traza capturada: {EX.traza_existe.mean():.0%}")
display(EX.head(5)[["value", "trace_id", "span_id", "model", "error.type", "traza_existe"]])
worst = EX.iloc[0].trace_id
viz.waterfall([s for s in TRACES.span_records() if s["trace_id"] == worst], title=f"Traza del exemplar más lento ({EX.iloc[0].value:.1f} s): trace_id {worst[:12]}…")
plt.show()
''')
    md(observe("""
    - Cada exemplar lleva el valor medido y el `trace_id` de la petición que lo produjo: el 100 % apunta a una traza capturada (en este experimento en memoria; en producción con *tail sampling* ese porcentaje puede **bajar**: ver 🧠).
    - La cascada del exemplar más lento enseña *por qué* fue lento (reintento del proveedor, herramienta lenta…). Es el flujo «percentil → petición → causa» que en Grafana harás con un clic.
    """))

    # ------------------------------------------------------------------------------------------ 7 · en vivo
    md("""
    ---
    # 7 · En vivo: SupportOps → Collector → Prometheus → PromQL

    Ahora el recorrido completo contra el stack real (si está levantado; si no, verás una versión con datos pregrabados). Plan:

    1. Un experimento corto: **qué pasa si exportas *delta* directamente a Prometheus**.
    2. Tráfico **en tiempo real** de SupportOps durante ≈ 100 s (`FAST_DEV_RUN`) o 4 min, con **dos incidentes** en el último tercio: *proveedor LLM lento* (×5 de latencia en las llamadas) y, dentro de él, una ráfaga de **errores 503**.
    3. Comprobar que los **nombres** que predijimos son los de Prometheus.
    4. Un *playbook* de consultas PromQL, **validado contra la verdad** del agente.

    > ⏱️ Las métricas se estampan con el reloj de pared al exportar (no con el simulado), por eso `run_live()` reparte los tickets en tiempo real. La cadena de latencias: SDK (cada 5 s) → Collector → Prometheus (*scrape* cada 15 s) → tu consulta; espera ≈ 20 s tras terminar para ver el último tramo.
    """)
    code('''
if LIVE:
    from opentelemetry.sdk.metrics import MeterProvider as _MP2, Counter as _Ctr
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader as _PER, AggregationTemporality as _AT
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as _OTLP
    exporter_errors = []
    class _Cap(logging.Handler):
        def emit(self, rec): exporter_errors.append(rec.getMessage())
    logging.getLogger("opentelemetry.exporter.otlp.proto.http.metric_exporter").addHandler(_Cap())

    def push_once(name, temporality):
        kw = {"preferred_temporality": {_Ctr: temporality}} if temporality else {}
        prov = _MP2(metric_readers=[_PER(_OTLP(endpoint=f"{PROM_URL}/api/v1/otlp/v1/metrics", **kw), export_interval_millis=1000)])
        prov.get_meter("lab").create_counter(name).add(5); time.sleep(2.2); prov.shutdown()

    push_once("lab.demo.cumulative.requests", None)
    push_once("lab.demo.delta.requests", _AT.DELTA)
    print("errores del exportador (solo el delta debería provocarlos):", sorted(set(exporter_errors)))
    print("cumulative ->", [r["value"] for r in prom_instant("lab_demo_cumulative_requests_total")], "(visible)")
    print("delta      ->", [r["value"] for r in prom_instant("lab_demo_delta_requests_total")], "(la serie NO existe)")
else:
    print("(sin Prometheus) Resultado esperado: el lote cumulative se acepta; el delta recibe HTTP 500 «invalid temporality and type combination».")
''')
    md("""
    Así se ve un `delta` mal enviado: el exportador solo se queja con un `Failed to export metrics batch code: 500` y la serie nunca aparece. Es el tipo de fallo **silencioso** que hace que «mi dashboard está vacío» consuma horas.

    ## 7.1 Tráfico en tiempo real
    """)
    code('''
SECS = 100 if FAST_DEV_RUN else 240
INCIDENTS = [Incident("llm_lento", "latency_spike", SECS * 0.55, SECS * 0.85, 0.75, {"factor": 5.0, "target": "llm"}),
             Incident("proveedor_caido", "llm_error", SECS * 0.65, SECS * 0.80, 0.5, {"status": 503, "persistent": True})]
if LIVE:
    TEL = setup_telemetry("supportops-agent", metric_interval_s=5)           # trazas + métricas + logs vía OTLP al Collector
    MI_LIVE = MetricsInstrumentor(TEL)                                         # TEL.meter_provider -> métricas con exemplars
    AGENT_LIVE = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(TEL, emit_metrics=False), MI_LIVE))
    TK_LIVE = generate_tickets(SECS * 2, seed=SEED, duration_s=SECS, fault_rates=DEFAULT_FAULT_RATES, incidents=INCIDENTS, start_s=0.0)
    T0 = time.time()
    RES_LIVE = run_live(AGENT_LIVE, TK_LIVE, SECS, progress_every=30)
    T1 = time.time(); TEL.force_flush()
    IID = TEL.resource.attributes["service.instance.id"]; SEL = f'instance="{IID}"'
    print(f"{len(RES_LIVE)} tickets en {T1 - T0:.0f} s · service.instance.id = {IID} · esperando al scrape de Prometheus…"); time.sleep(22)
    LIVE_DF = pd.DataFrame(to_rows(TK_LIVE, RES_LIVE)); print(LIVE_DF.status.value_counts().to_dict())
else:
    print("Sin stack: se omite el tráfico en vivo (usa la sección «datos pregrabados» más abajo).")
''')

    md("""
    ## 7.2 ¿Coinciden los nombres que predijimos con los de Prometheus?
    """)
    code('''
if LIVE:
    rows_live = metric_rows(TEL._metric_mem)                                    # copia en memoria de lo exportado (A2: keep_local)
    expect = {}
    for r in rows_live:
        kind = "histogram" if r["kind"] == "histogram" else ("gauge" if r["kind"] == "gauge" or not r["monotonic"] else "sum")
        for nm in prom_name(r["name"], r["unit"], kind, bool(r["monotonic"])): expect[nm] = r["name"]
    actual = set(prom_api("/api/v1/label/__name__/values")["data"])
    chk = pd.DataFrame([{"serie predicha": n, "métrica OTel": o, "existe en Prometheus": "✅" if n in actual else "❌"} for n, o in sorted(expect.items())])
    print(f"{(chk['existe en Prometheus'] == '✅').sum()}/{len(chk)} nombres predichos existen en Prometheus")
    display(chk[chk["existe en Prometheus"] == "❌"] if (chk["existe en Prometheus"] == "❌").any() else chk.head(8))
else:
    print("Sin Prometheus: la verificación se hace contra /api/v1/label/__name__/values.")
''')

    md("""
    ## 7.3 El *playbook* de PromQL de SupportOps

    Cada consulta responde a una pregunta de operación. Dos reglas de oro: **`rate()` siempre sobre contadores y con ventana ≥ 4 × el intervalo de *scrape*** (aquí 15 s → `[1m]`), y **`histogram_quantile()` siempre sobre `sum by (le) (rate(..._bucket[...]))`** (nunca sobre un histograma sin sumar ni promediando percentiles).

    | # | Pregunta | PromQL |
    |---|---|---|
    | 1 | ¿Cuántas peticiones/s? | `sum(rate(supportops_agent_requests_total[1m]))` |
    | 2 | ¿Qué fracción falla? | `sum(rate(supportops_agent_requests_total{supportops_status=~"error\\|max_steps"}[1m])) / sum(rate(supportops_agent_requests_total[1m]))` |
    | 3 | ¿p50 / p95 del agente? | `histogram_quantile(0.95, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket[1m])))` |
    | 4 | ¿Y solo el LLM? | `histogram_quantile(0.95, sum by (le) (rate(gen_ai_client_inference_duration_seconds_bucket[1m])))` |
    | 5 | ¿Tokens/s de entrada y salida? | `sum(rate(gen_ai_client_inference_usage_input_tokens_total[1m]))` (y `output`) |
    | 6 | ¿Coste por hora? | `sum(rate(supportops_llm_cost_USD_total[1m])) * 3600` |
    | 7 | ¿Qué herramienta es lenta? | `sum by (gen_ai_tool_name) (rate(gen_ai_execute_tool_duration_seconds_sum[1m])) / sum by (gen_ai_tool_name) (rate(gen_ai_execute_tool_duration_seconds_count[1m]))` |
    | 8 | ¿Cuántas llamadas al LLM por ticket? (bucles) | `sum(rate(gen_ai_client_inference_duration_seconds_count[1m])) / sum(rate(supportops_agent_requests_total[1m]))` |
    """)
    code('''
def shade(ax):
    ax.axvspan(SECS * 0.55, SECS * 0.85, color=viz.PALETTE["warn"], alpha=.13); ax.axvspan(SECS * 0.65, SECS * 0.80, color=viz.PALETTE["error"], alpha=.13)

if LIVE:
    W = "1m"; mins = (time.time() - T0) / 60 + 0.4
    PQ = {
        "Peticiones/s": f'sum(rate(supportops_agent_requests_total{{{SEL}}}[{W}]))',
        "Tasa de error": f'sum(rate(supportops_agent_requests_total{{{SEL},supportops_status=~"error|max_steps"}}[{W}])) / sum(rate(supportops_agent_requests_total{{{SEL}}}[{W}]))',
        "p95 agente (s)": f'histogram_quantile(0.95, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket{{{SEL}}}[{W}])))',
        "p95 llamada LLM (s)": f'histogram_quantile(0.95, sum by (le) (rate(gen_ai_client_inference_duration_seconds_bucket{{{SEL}}}[{W}])))',
        "Tokens entrada/s": f'sum(rate(gen_ai_client_inference_usage_input_tokens_total{{{SEL}}}[{W}]))',
        "Coste USD/hora": f'sum(rate(supportops_llm_cost_USD_total{{{SEL}}}[{W}])) * 3600',
    }
    fig, axes = plt.subplots(2, 3, figsize=(15.5, 7))
    for ax, (ttl, q) in zip(axes.ravel(), PQ.items()):
        for s in prom_range(q, minutes=mins, step_s=5):
            ax.plot(np.array(s["t"]) - T0, s["v"], lw=2.2, color=viz.PALETTE["metrics"])
        shade(ax); ax.set_title(ttl); ax.set_xlabel("segundos desde el inicio"); ax.set_xlim(0, SECS + 20)
    plt.suptitle("Las 6 consultas del playbook sobre el tráfico real (amarillo = proveedor lento · rojo = errores 503)", y=1.01); plt.tight_layout(); plt.show()
else:
    mm = pd.DataFrame(sample_data.load_metrics_1m()); fig, axes = plt.subplots(1, 4, figsize=(15.5, 3.4))
    for ax, (col, ttl) in zip(axes, (("requests", "Peticiones/min"), ("errors", "Errores/min"), ("p95_latency_s", "p95 (s)"), ("cost_usd", "Coste USD/min"))):
        ax.plot(mm.minute, mm[col], color=viz.PALETTE["metrics"], lw=2); ax.set_title(ttl + " (pregrabado)"); ax.set_xlabel("minuto")
    plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Tasa de error** y **p95**: durante el incidente (franja amarilla) el p95 del agente y de la llamada LLM se disparan (×5 en las llamadas); en la franja roja suben los errores 503 (con reintento, algunos tickets se salvan, otros acaban en `error`).
    - **Peticiones/s** sigue siendo ≈ 1–2 req/s: el tráfico no cambia, **la calidad del servicio sí**. Un dashboard de solo tráfico no vería el incidente.
    - **Tokens/s y coste/hora** *suben* durante el incidente aunque haya menos respuestas útiles: los reintentos y las respuestas degradadas consumen igual. Es el patrón «el incidente también cuesta dinero».
    - Las curvas **empiezan ≈ 35 s después del inicio**: la primera exportación tarda 5 s, Prometheus necesita al menos dos *scrapes* (15 s) dentro de la ventana de `rate()` y por eso antes no hay nada. Los tramos rectos son la interpolación entre dos raspados.
    """))

    md("""
    ## 7.4 Validación contra la verdad del agente

    Una consulta PromQL que «se ve bien» no está validada. Contrastamos con lo que sabemos del agente:
    """)
    code('''
if LIVE:
    at = T1 + 25                                                       # cuando ya se ha raspado todo
    pq = lambda q: prom_instant(f'histogram_quantile({q}, sum by (le) (gen_ai_invoke_agent_duration_seconds_bucket{{{SEL}}}))', at=at)[0]["value"]
    lats = [r.latency_s for r in RES_LIVE]
    V = pd.DataFrame([
        ("Σ peticiones", prom_instant(f"sum(supportops_agent_requests_total{{{SEL}}})")[0]["value"], len(RES_LIVE)),
        ("Σ tokens de entrada", prom_instant(f"sum(gen_ai_client_inference_usage_input_tokens_total{{{SEL}}})")[0]["value"], sum(r.input_tokens for r in RES_LIVE)),
        ("Σ coste USD", prom_instant(f"sum(supportops_llm_cost_USD_total{{{SEL}}})")[0]["value"], sum(r.cost_usd for r in RES_LIVE)),
        ("Σ errores (error+max_steps)", prom_instant(f'sum(supportops_agent_requests_total{{{SEL},supportops_status=~"error|max_steps"}})')[0]["value"], sum(r.status in ("error", "max_steps") for r in RES_LIVE)),
        ("p50 del agente (s)", pq(0.5), float(np.quantile(lats, .5))),
        ("p95 del agente (s)", pq(0.95), float(np.quantile(lats, .95))),
        ("p99 del agente (s)", pq(0.99), float(np.quantile(lats, .99))),
    ], columns=["magnitud", "PromQL (Prometheus)", "verdad (agente)"])
    V["error rel."] = ((V.iloc[:, 1] - V.iloc[:, 2]).abs() / V.iloc[:, 2].abs()).round(4)
    V["ok"] = np.where(V["error rel."] <= [0.001, 0.001, 0.01, 0.001, 0.15, 0.15, 0.15], "✅", "❌")
    display(V)
else:
    print("Sin Prometheus: aquí compararías Σ contadores y percentiles con la verdad del agente (error < 0,1 % en sumas; < 15 % en percentiles con buckets ajustados).")
''')
    md("""
    Las **sumas** (peticiones, tokens, coste, errores) deben coincidir **exactamente** (error < 0,1 %): son contadores. Los **percentiles** son estimaciones por interpolación (sección 2.2): con los buckets ajustados y 150 tickets el error queda en el 0–10 % (aceptamos hasta el 15 %; el p99 con tan pocas observaciones en la cola es el más ruidoso). Fíjate en que consultamos los buckets **acumulados** (sin `rate`/`increase`): así el percentil cubre *toda* la ejecución, que es lo que conocemos con exactitud. Con `increase()` sobre una ventana arbitraria el resultado depende de **cuándo** cayó cada *scrape* respecto al borde de la ventana (±15 s).

    ## 7.5 Dos trampas clásicas, reproducidas
    """)
    code('''
if LIVE:
    at = T1 + 25
    one = prom_instant(f'rate(supportops_agent_requests_total{{{SEL}}}[15s])', at=T0 + 40)
    ok_ = prom_instant(f'sum(rate(supportops_agent_requests_total{{{SEL}}}[1m]))', at=T0 + 40)
    print(f"TRAMPA 1 · ventana demasiado corta  rate(...[15s]) con scrape de 15 s -> {len(one)} series (VACÍO: ¡solo hay 1 muestra por ventana!)  ·  rate(...[1m]) -> {ok_[0]['value']:.2f} req/s")
    B = f'gen_ai_invoke_agent_duration_seconds_bucket{{{SEL}}}'
    per_grp = prom_instant(f'histogram_quantile(0.95, sum by (le, error_type) ({B}))', at=at)
    avg_of_p95 = float(np.mean([r["value"] for r in per_grp]))
    right = prom_instant(f'histogram_quantile(0.95, sum by (le) ({B}))', at=at)[0]["value"]
    truth = float(np.quantile([r.latency_s for r in RES_LIVE], .95))
    print(f"TRAMPA 2 · promediar percentiles    avg(p95 por error.type) = {avg_of_p95:.2f} s  ·  p95 correcto (sumando buckets) = {right:.2f} s  ·  verdad = {truth:.2f} s")
    print("   p95 por grupo:", {(r["metric"].get("error_type") or "sin error"): round(r["value"], 2) for r in per_grp})
else:
    print("Sin Prometheus: reproduce (1) rate(x[15s]) vacío con scrape de 15 s y (2) avg(p95 por tier) ≠ p95 global.")
''')
    md("""
    La segunda trampa no es un error de Prometheus sino de **estadística**: el p95 global no es la media de los p95 de los subgrupos (módulo 02); aquí los grupos «sin error» (la inmensa mayoría) y `server_error` (rápido: falla enseguida) pesan muy distinto. La forma correcta es sumar **antes** los contadores de bucket (`sum by (le)`) y calcular el percentil sobre la suma.

    ## 7.6 Exemplars reales: del rombo a la traza
    """)
    code('''
if LIVE:
    ex = prom_exemplars("gen_ai_invoke_agent_duration_seconds_bucket", minutes=(time.time() - T0) / 60 + 1)
    ex = [e for e in ex if e["series"].get("instance") == IID]; ex.sort(key=lambda e: -e["value"])
    print(f"{len(ex)} exemplars almacenados en Prometheus para esta ejecución · el más lento: {ex[0]['value']:.1f} s · trace_id {ex[0]['trace_id']}")
    top = ex[0]["trace_id"]; sp = []
    for _ in range(12):                                                         # Tempo tarda unos segundos en poder devolver la traza
        try:
            sp = tempo_spans(backends.tempo_trace(top))
            if sp: break
        except Exception: pass
        time.sleep(4)
    if sp:
        viz.waterfall(sp, title=f"Traza en TEMPO del exemplar más lento ({ex[0]['value']:.1f} s)"); plt.show()
        print("spans:", [s["name"] for s in sp])
    else:
        print("Tempo aún no devuelve la traza (espera unos segundos y repite).")
else:
    print("Sin stack: el flujo es  Prometheus /api/v1/query_exemplars -> trace_id -> Tempo /api/traces/<id>.")
''')
    md(observe("""
    - Los exemplars almacenados en Prometheus llevan **`trace_id` y `span_id`** y el valor medido. El de mayor valor es la petición más lenta del bucket más alto.
    - La cascada viene **de Tempo**, no de la memoria del proceso: el ciclo completo SDK → Collector → Prometheus *y* SDK → Collector → Tempo funciona, y ambos están unidos por el `trace_id`.
    - En Grafana (módulo 10) este salto es un clic en el rombo; aquí lo hemos hecho con dos llamadas HTTP para que entiendas qué hay debajo.
    """))
    md("""
    ## 7.7 El dashboard provisionado «09 · Métricas GenAI de SupportOps»

    El repo trae `stack/grafana/dashboards/09-genai-metrics.json` (generado con `supportops.dashkit` por `build_09.py`; en el módulo 10 aprendes a construirlos). Grafana lo recarga cada 10 s. Comprobamos por la API que está cargado:
    """)
    code('''
if LIVE:
    try:
        d = backends.grafana_api("/api/dashboards/uid/genai-metrics")
        print("Dashboard:", d["dashboard"]["title"], "· paneles:", len([p for p in d["dashboard"]["panels"] if p["type"] != "row"]), "· carpeta:", d["meta"]["folderTitle"])
        print("Ábrelo en  http://localhost:3000/d/genai-metrics  (usuario admin / contraseña admin)")
    except Exception as e:
        print("Aún no está cargado (Grafana recarga los dashboards cada 10 s):", str(e)[:120])
else:
    print("Sin Grafana: el dashboard está en stack/grafana/dashboards/09-genai-metrics.json")
''')

    md("""
    ![Dashboard 09 · Métricas GenAI de SupportOps en Grafana: fila de stats (peticiones/s, error, p95, coste, tokens, llamadas por ticket), tasa por estado, percentiles, mapa de calor con exemplars y paneles de herramientas, tokens y coste](img/09_dashboard.png)

    *Captura real del dashboard aprovisionado (Grafana 13.2.4, Chromium sin interfaz) tras ejecutar esta lección.* **Qué debe ver el alumno:** (1) arriba, seis *stats* con umbrales de color (la tasa de error en verde/naranja/rojo, el p95 en rojo durante el incidente); (2) a la izquierda, la tasa por estado apilada: `ok` domina, con `error` y `escalated` visibles durante el incidente; (3) a la derecha, p50/p95/p99 con la línea roja del umbral; (4) el **mapa de calor** de la latencia con **cuadrados magenta = exemplars**: un clic abre la traza en Tempo; (5) abajo, el p95 de la llamada al LLM, la latencia media por herramienta (`escalate_to_human` y `issue_refund` son las más lentas) y los tokens/s. Los huecos entre ráfagas son tiempo sin tráfico: `rate()` no devuelve nada si no hay muestras nuevas.
    """)

    # ------------------------------------------------------------------------------------------ 8 · cardinalidad
    md("""
    ---
    # 8 · Cardinalidad: el coste real de una etiqueta

    Una métrica de Prometheus ocupa memoria y disco **por serie**, y el número de series es

    $$\\#\\text{series} \\;=\\; \\prod_{a\\in\\text{atributos}} |a| \\;\\times\\; \\underbrace{(B+3)}_{\\text{solo histogramas clásicos}}$$

    donde $|a|$ es el nº de valores distintos de cada atributo y $B$ el nº de límites finitos de bucket (`B` buckets finitos + `+Inf` + `_sum` + `_count`). Un histograma con 15 límites y 5 combinaciones de etiquetas ya son **90 series**; si añades `customer_id` (200 clientes), **18 000**.

    ### Experimento: ¿qué pasa en el SDK cuando un atributo tiene muchos valores?
    """)
    code('''
import tracemalloc
def cardinality_run(n_unique: int, n_events: int = 20000):
    rd = InMemoryMetricReader(); p = MeterProvider(metric_readers=[rd]); m = p.get_meter("c")
    c = m.create_counter("c.req"); h = m.create_histogram("c.dur", unit="s", explicit_bucket_boundaries_advisory=TUNED_AGENT_DURATION_BOUNDARIES)
    tracemalloc.start(); t0 = time.perf_counter()
    for i in range(n_events):
        at = {"model": "mock-small", "status": "ok", "id": f"X-{i % n_unique:06d}"}
        c.add(1, at); h.record(0.5 + (i % 9) * 0.3, at)
    dt = time.perf_counter() - t0; _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    rows = metric_rows(rd); pc = sum(r["name"] == "c.req" for r in rows); ph = sum(r["name"] == "c.dur" for r in rows)
    return {"valores distintos del atributo": n_unique, "puntos Counter": pc, "puntos Histogram": ph,
            "series en Prometheus": pc + ph * (len(TUNED_AGENT_DURATION_BOUNDARIES) + 3), "memoria SDK (MB)": round(peak / 1e6, 1), "µs por evento": round(dt / n_events * 1e6, 1)}

from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics import MeterProvider
CARD = pd.DataFrame([cardinality_run(n) for n in (1, 10, 100, 1000, 5000, 20000)])
CARD["con límite de la spec (2000)"] = CARD["puntos Counter"].clip(upper=2001)
display(CARD)
''')
    code('''
fig, axes = plt.subplots(1, 2, figsize=(14, 4.1))
axes[0].loglog(CARD["valores distintos del atributo"], CARD["series en Prometheus"], "o-", color=viz.PALETTE["error"], lw=2.4, label="series en Prometheus (counter + histograma clásico)")
axes[0].loglog(CARD["valores distintos del atributo"], CARD["puntos Counter"], "s--", color=viz.PALETTE["metrics"], label="puntos de un Counter")
axes[0].axhline(150000, color="k", ls=":"); axes[0].text(1.2, 110000, "límite por defecto de Mimir por tenant: 150 000 series activas", fontsize=8, va="top")
axes[0].set_xlabel("valores distintos de UN atributo (p. ej. customer_id)"); axes[0].set_ylabel("series"); axes[0].set_title("Series vs. cardinalidad de un atributo"); axes[0].legend(fontsize=8)
axes[1].bar(range(len(CARD)), CARD["memoria SDK (MB)"], color=viz.PALETTE["traces"]); axes[1].set_xticks(range(len(CARD))); axes[1].set_xticklabels(CARD["valores distintos del atributo"])
axes[1].set_xlabel("valores distintos del atributo"); axes[1].set_ylabel("pico de memoria del SDK (MB)"); axes[1].set_title("…y la memoria del PROCESO de la aplicación crece con ellas")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Una sola etiqueta con 20 000 valores genera **20 000 puntos por instrumento**, y como el histograma clásico las multiplica por $B+3 = 18$, ~**360 000 series** en Prometheus: **más del doble del límite por defecto de Mimir** por tenant (150 000 series activas, `max_global_series_per_user` en `limits.go`).
    - La memoria **del propio proceso Python crece con la cardinalidad**: el SDK mantiene un acumulador por combinación. La última columna de la tabla muestra que el SDK de Python 1.45.1 **no corta**: con 20 000 valores distintos exporta 20 000 puntos. La *spec* (estable) pide un límite por defecto de 2 000 con un punto de desbordamiento `otel.metric.overflow=true`; otros SDK lo implementan, **el de Python aún no** (comprobado: no hay ningún `cardinality_limit` en `opentelemetry/sdk/metrics`). Tu defensa es el diseño (atributos acotados) y las *views* con `attribute_keys`.
    """))
    md("""
    ### La cardinalidad de SupportOps, medida
    Comparamos las series que *predice* la fórmula para cada métrica de `MetricsInstrumentor` con las que **hay realmente** en Prometheus tras el tráfico en vivo:
    """)
    code('''
if LIVE:
    fam = collections.defaultdict(lambda: {"puntos": 0, "pred": 0, "names": []})
    for r in rows_live:
        f = fam[r["name"]]; kind = "histogram" if r["kind"] == "histogram" else ("gauge" if r["kind"] == "gauge" or not r["monotonic"] else "sum")
        f["puntos"] += 1; f["pred"] += (len(r["bounds"]) + 3) if kind == "histogram" else 1
        f["names"] = prom_name(r["name"], r["unit"], kind, bool(r["monotonic"]))
    out = []
    for name, f in fam.items():
        rgx = "|".join(f["names"]); got = prom_instant(f'count({{__name__=~"{rgx}", {SEL}}})')
        out.append({"métrica OTel": name, "puntos (combinaciones)": f["puntos"], "series predichas": f["pred"], "series en Prometheus": int(got[0]["value"]) if got else 0})
    CT = pd.DataFrame(out).sort_values("series en Prometheus", ascending=False); CT["coincide"] = np.where(CT["series predichas"] == CT["series en Prometheus"], "✅", "❌")
    display(CT); print("TOTAL: predichas", CT["series predichas"].sum(), "· en Prometheus", CT["series en Prometheus"].sum(), "· head de Prometheus:", prom_instant("prometheus_tsdb_head_series")[0]["value"])
    top = prom_api("/api/v1/status/tsdb")["data"]["seriesCountByMetricName"][:10]
    print("\\nTop-10 métricas por nº de series en TODO el Prometheus (API /api/v1/status/tsdb):"); display(pd.DataFrame(top))
else:
    print("Sin Prometheus: usa /api/v1/status/tsdb para ver las métricas con más series.")
''')
    md(box("elite", "Presupuesta las series antes de desplegar", """
    Antes de añadir una etiqueta, multiplica: `series = ∏|a| × (B+3)`. Para `gen_ai.execute_tool.duration` con 4 herramientas × 3 `error.type` posibles × 1 agente y 11 límites, el techo es 4×3×14 = **168 series**. Si mañana alguien añade `gen_ai.tool.call.id` (único por llamada), no hay techo. Tres defensas, de más a menos barata: (1) **diseño**: atributos de dominio acotado (enums), nunca ids; (2) **View con `attribute_keys`** en el SDK; (3) **límites del backend** (Mimir/Cardinality Explorer, `series_limit` por scrape en Prometheus), que *rechazan* en vez de proteger. Y recuerda: los ids van en **spans y logs** (módulos 07-08), donde su coste es por evento, no por serie.
    """))

    # ------------------------------------------------------------------------------------------ 9 · nativos
    md("""
    ---
    # 9 · Histogramas exponenciales (OTel) y nativos (Prometheus)

    El problema de los histogramas clásicos: **tú** eliges los límites (y acabamos de ver lo que cuesta equivocarse) y cada límite es **una serie**. Los *histogramas exponenciales* de OTel (y sus equivalentes nativos en Prometheus) fijan los buckets con una **fórmula** a partir de un parámetro `scale`:

    $$\\text{base}=2^{2^{-\\text{scale}}},\\qquad \\text{bucket } i = \\big(\\text{base}^{\\,i},\\ \\text{base}^{\\,i+1}\\big],\\qquad i=\\left\\lceil \\log_{\\text{base}}(v)\\right\\rceil-1$$

    Cada incremento de `scale` **divide por dos** el ancho relativo del bucket (más resolución, más buckets). El SDK reduce el `scale` solo si supera el máximo de buckets (160 por defecto), así que **no hay que elegir límites**. En Prometheus un histograma nativo es **una sola serie** con todos los buckets dentro.
    """)
    code('''
class ExpHist:
    """Histograma exponencial a mano (solo valores > 0): bucket i = (base^i, base^(i+1)]."""
    def __init__(self, scale: int = 3):
        self.scale, self.base = scale, 2 ** (2 ** -scale); self.buckets = collections.Counter(); self.n = 0
    def add(self, v: float):
        self.buckets[math.ceil(math.log(v, self.base)) - 1] += 1; self.n += 1
    def quantile(self, q: float) -> float:
        rank, cum = q * self.n, 0
        for i in sorted(self.buckets):
            c = self.buckets[i]
            if cum + c >= rank:
                lo, hi = self.base ** i, self.base ** (i + 1)
                return lo * (hi / lo) ** ((rank - cum) / c)          # interpolación GEOMÉTRICA dentro del bucket
            cum += c

rows = []
for sc in range(0, 7):
    h = ExpHist(sc)
    for v in lat: h.add(float(v))
    rows.append({"scale": sc, "base": round(h.base, 4), "buckets usados": len(h.buckets), **{f"error p{int(q*100)} %": round(100 * (h.quantile(q) - np.quantile(lat, q)) / np.quantile(lat, q), 2) for q in (.5, .95, .99)}})
EH = pd.DataFrame(rows); display(EH)
''')
    code('''
fig, ax = plt.subplots(figsize=(8.5, 3.9))
for q, col in ((.5, viz.PALETTE["traces"]), (.95, viz.PALETTE["metrics"]), (.99, viz.PALETTE["error"])):
    ax.plot(EH.scale, EH[f"error p{int(q*100)} %"].abs(), "o-", color=col, lw=2, label=f"|error| p{int(q*100)}")
ax.set_xlabel("scale (resolución)"); ax.set_ylabel("|error relativo| del percentil (%)"); ax.set_yscale("log")
ax2 = ax.twinx(); ax2.plot(EH.scale, EH["buckets usados"], "k--", label="buckets usados"); ax2.set_ylabel("buckets no vacíos"); ax2.grid(False)
ax.set_title("Más scale = menos error y más buckets (todos dentro de UNA serie nativa)"); ax.legend(loc="upper right"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con `scale = 3` (base ≈ 1,09: cada bucket es un 9 % más ancho que el anterior, error relativo máximo ≈ ±4,5 %) el error del p95/p99 ya es **< 1 %** sin elegir ni un límite, usando ≈ 50 buckets no vacíos para el rango 0,3–50 s.
    - Cada +1 de `scale` reduce el error de forma aproximadamente geométrica; el coste son más buckets, pero **dentro de una misma serie**: no multiplican series.
    - Compáralo con la sección 2.2: los clásicos necesitaban buscar los límites correctos para llegar al mismo error.
    """))
    md("""
    ## 9.1 En vivo: clásico (spec), clásico (ajustado) y nativo, sobre las mismas 1 500 latencias

    Enviamos las **mismas observaciones** a Prometheus por la **ruta B** (OTLP directo): un histograma con los límites de la spec, otro con los ajustados y uno **exponencial** (que Prometheus ingiere como nativo, sin ningún *flag*: son estables desde la v3.8).
    """)
    code('''
if LIVE:
    from opentelemetry.sdk.metrics.view import View, ExponentialBucketHistogramAggregation
    from opentelemetry.sdk.resources import Resource
    LAB_ID = f"lab-{int(time.time())}"
    prov = MeterProvider(resource=Resource.create({"service.name": "lab-hist", "service.instance.id": LAB_ID}),
                         metric_readers=[_PER(_OTLP(endpoint=f"{PROM_URL}/api/v1/otlp/v1/metrics"), export_interval_millis=1500)],
                         views=[View(instrument_name="lab.latency.native", aggregation=ExponentialBucketHistogramAggregation(max_size=160))])
    mm = prov.get_meter("lab")
    hs = {"spec": mm.create_histogram("lab.latency.spec", unit="s", explicit_bucket_boundaries_advisory=SPEC_AGENT_DURATION_BOUNDARIES),
          "tuned": mm.create_histogram("lab.latency.tuned", unit="s", explicit_bucket_boundaries_advisory=TUNED_AGENT_DURATION_BOUNDARIES),
          "native": mm.create_histogram("lab.latency.native", unit="s")}
    for v in lat:
        for h in hs.values(): h.record(float(v))
    time.sleep(3.5)
    qs = {"spec": 'histogram_quantile({q}, sum by (le) (lab_latency_spec_seconds_bucket{{instance="{lab}"}}))',
          "tuned": 'histogram_quantile({q}, sum by (le) (lab_latency_tuned_seconds_bucket{{instance="{lab}"}}))',
          "native": 'histogram_quantile({q}, lab_latency_native_seconds{{instance="{lab}"}})'}
    NT = []
    for q in (.5, .95, .99):
        row = {"percentil": f"p{int(q*100)}", "verdad": float(np.quantile(lat, q))}
        for k, tpl in qs.items():
            got = prom_instant(tpl.format(q=q, lab=LAB_ID)); row[k] = got[0]["value"] if got else float("nan")
        NT.append(row)
    NT = pd.DataFrame(NT)
    for k in qs: NT[f"error {k} %"] = (100 * (NT[k] - NT.verdad) / NT.verdad).round(1)
    display(NT.round(3))
    ser = {k: prom_series_count(f'{{__name__=~"lab_latency_{k}_seconds.*",instance="{LAB_ID}"}}') for k in qs}
    print("series en Prometheus por histograma:", ser)
    prov.shutdown()
else:
    print("Sin Prometheus. Resultado medido en el curso: p99 spec +5 %, ajustado +5,5 %, nativo +0,2 %; series 16 / 18 / 1.")
''')
    md(observe("""
    - El histograma **nativo** da el percentil más cercano a la verdad (error ≲ 1 %) **sin que hayas elegido límites**, y ocupa **1 serie** frente a 16-18 de los clásicos.
    - Los clásicos están bien en el centro y peor en la cola (p99), donde sus buckets son anchos.
    - En consultas, el nativo se escribe `histogram_quantile(0.95, sum(rate(metrica[5m])))` **sin** `by (le)` y sin sufijo `_bucket`.
    """))
    md("""
    ### Pero ojo con la ruta: el Collector del curso **no** transporta histogramas exponenciales
    """)
    code('''
if LIVE:
    prov = MeterProvider(resource=Resource.create({"service.name": "lab-hist-collector", "service.instance.id": "lab-c1"}),
                         metric_readers=[_PER(_OTLP(endpoint="http://localhost:4318/v1/metrics"), export_interval_millis=1500)],
                         views=[View(instrument_name="lab.collector.native", aggregation=ExponentialBucketHistogramAggregation())])
    hx = prov.get_meter("lab").create_histogram("lab.collector.native", unit="s")
    for v in lat[:500]: hx.record(float(v))
    time.sleep(3.5); prov.shutdown()
    import urllib.request
    body = urllib.request.build_opener(urllib.request.ProxyHandler({})).open("http://localhost:8889/metrics", timeout=5).read().decode()
    lines = [ln.split("{")[0] + "{…le=" + ln.split('le="')[1] if "_bucket" in ln else ln.split("{")[0] for ln in body.splitlines() if ln.startswith("lab_collector_native")]
    print("\\n".join(lines))
else:
    print("Sin Collector. Resultado medido (Collector 0.162): solo aparece  lab_collector_native_seconds_bucket{…le=\\"+Inf\\"}  más _sum y _count.")
''')
    md("""
    El exporter `prometheus` del Collector (v0.162.0) convierte el histograma exponencial en **clásico con un único bucket `+Inf`**: conserva `_sum` y `_count` (¡la media sí!) pero **pierde la distribución**, así que `histogram_quantile()` es imposible. Para tener nativos hay que usar la **ruta B** (OTLP directo a Prometheus, o `otlphttp` del Collector hacia Prometheus/Mimir) o `prometheusremotewrite`. En **Mimir**, además, los exponenciales **no se aceptan por defecto**: hay que habilitar la ingesta de nativos (`-ingester.native-histograms-ingestion-enabled=true`, o por tenant `native_histograms_ingestion_enabled`) y se recomienda limitar los buckets a 160 (`-validation.max-native-histogram-buckets`).

    | | Clásico (explícito) | Exponencial/Nativo |
    |---|---|---|
    | Límites de bucket | Los eliges tú (y los pagas en series) | Fórmula (`scale`), automáticos |
    | Series por histograma | $B+3$ | 1 |
    | Error de percentil | Depende de tus límites | Acotado por el `scale` (con scale 3, buckets un 9 % más anchos que el anterior: ≈ ±4,5 %) |
    | Agregar instancias | Sí, si **mismos** límites | Sí (ajusta `scale` al fusionar) |
    | Soporte | Universal | Prometheus ≥ 3.8 (estable), Mimir con flags, Grafana (heatmap). El exporter `prometheus` del Collector **no** los transporta |
    | Estado | Estable | OTel: estable; Prometheus: estable pero *opt-in* (`scrape_native_histograms`); la ruta Collector→Prometheus requiere OTLP/remote write |
    """)

    # ------------------------------------------------------------------------------------------ 10 · Mimir
    md("""
    ---
    # 10 · Cuando Prometheus no basta: Mimir

    Un Prometheus único es perfecto para el laboratorio y para muchos equipos. Se queda corto cuando necesitas **retención larga**, **alta disponibilidad**, **muchos equipos/entornos aislados** o **más series de las que caben en una máquina**. **Grafana Mimir** es el almacén de métricas horizontalmente escalable de Grafana Labs, compatible con PromQL y con la ingesta de Prometheus/OTLP. Lo que cambia para ti como autor de instrumentación (verificado en la documentación de Mimir):

    | Tema | Prometheus (curso) | Mimir |
    |---|---|---|
    | Entrada de OTLP | `/api/v1/otlp/v1/metrics` (con `--web.enable-otlp-receiver`) | endpoint nativo `/otlp` (exporter `otlphttp` del Collector); alternativa `prometheusremotewrite` → `/api/v1/push` |
    | Multi-tenencia | No (un solo espacio) | Cada petición lleva la cabecera **`X-Scope-OrgID: <tenant>`** (≤ 150 caracteres); un proxy debe inyectarla |
    | Límite de series | Sin límite duro (te quedas sin memoria) | `max_global_series_per_user` (**150 000 por defecto**) por tenant: **rechaza** las series nuevas al superarlo |
    | Histogramas exponenciales | Se ingieren como nativos | **No se aceptan por defecto**: `-ingester.native-histograms-ingestion-enabled=true` (global) o `native_histograms_ingestion_enabled` por tenant; limitar buckets a 160 con `-validation.max-native-histogram-buckets` |
    | Atributos de recurso | `promote_resource_attributes` en `prometheus.yml` | `-distributor.otel-promote-resource-attributes` (**experimental**); el resto va a `target_info` |

    Un fragmento de Collector para enviar OTLP a Mimir con un tenant (basado en la documentación de Mimir; **no lo hemos ejecutado** en el laboratorio porque el stack del curso no incluye Mimir):
    """)
    code('''
MIMIR_EXPORTER = """
exporters:
  otlp_http/mimir:                     # el nombre del exporter en el Collector 0.162 es otlp_http (antes «otlphttp»)
    endpoint: http://mimir:8080/otlp   # ejemplo; el exporter añade /v1/metrics
    headers:
      X-Scope-OrgID: supportops        # tenant (multi-tenencia)
service:
  pipelines:
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource/lab, batch]
      exporters: [otlp_http/mimir]
"""
import yaml
cfg = yaml.safe_load(MIMIR_EXPORTER); print("YAML válido · exporters:", list(cfg["exporters"]), "· tenant:", cfg["exporters"]["otlp_http/mimir"]["headers"])
''')
    md(box("warn", "No lo olvides", """
    Mimir/Prometheus **no arreglan** una mala cardinalidad: la **cobran**. Un Mimir con 150 000 series por tenant rechaza las nuevas (los datos *nuevos* desaparecen en silencio salvo que mires las métricas de descartes). La disciplina de la sección 8 es el 90 % del trabajo; el escalado (muestreo, límites por tenant, tiering) es el módulo 18.
    """))

    # ------------------------------------------------------------------------------------------ prod / élite
    md("""
    ---
    # 🏭 En producción

    - **Alerta sobre síntomas, no sobre causas.** La guía de dashboards de Grafana lo resume así: *USE* (utilización, saturación, errores) informa de las **causas** en recursos; *RED* (tasa, errores, duración) informa de la **experiencia de usuario**; «alerta sobre síntomas»: las alertas van sobre el RED. Las *cuatro señales de oro* del libro SRE de Google añaden **saturación**. Para un agente: RED + tokens/coste/pasos (esta lección) y saturación = cola, ejecuciones concurrentes y uso de contexto.
    - **Una métrica de latencia = un histograma + un SLO.** Pon un límite de bucket justo en el umbral del SLO: así «% de peticiones bajo 3 s» se calcula **exacto** (`sum(rate(bucket{le="3"}))/sum(rate(count))`) y no por interpolación. Es la base de las alertas por *burn rate* del módulo 16.
    - **Receptor OTLP de Prometheus en producción:** la guía oficial de OpenTelemetry de Prometheus recomienda `out_of_order_time_window: 30m` (varias réplicas del Collector pueden enviar fuera de orden), promover solo un conjunto corto de atributos de recurso (`service.name`, `service.instance.id`, `deployment.environment.name`, `k8s.*`…) y unir el resto con `target_info` en la consulta (función experimental `info()`).
    - **Intervalo de exportación y de *scrape* son una decisión de coste:** el SDK exporta cada 60 s por defecto (el curso usa 5 s para iterar); a 15 s de *scrape* necesitas ventanas de `rate()` ≥ 1 min. Menos resolución = menos muestras = menos disco, pero alertas más lentas.
    - **Coste del propio stack de métricas** (módulo 18): ∝ series × resolución × retención. Los histogramas clásicos son lo más caro: revisa `topk(10, count by (__name__)({__name__=~".+"}))` cada trimestre.
    - **Conciliación:** una métrica de coste debe cuadrar con la factura del proveedor; una de peticiones, con los logs del balanceador. Automatiza la conciliación de la sección 5 en CI.
    """)

    md("""
    ---
    # 🧠 Secretos de la élite

    1. **El SDK de Python no limita la cardinalidad (y el de la spec sí debería).** La spec de OTel (estable) pide un límite de 2 000 puntos por métrica con un punto de desbordamiento `otel.metric.overflow=true`. En `opentelemetry-sdk` 1.45.1 **no existe** (no hay rastro de `cardinality_limit` en `sdk/metrics`) y el experimento de la sección 8 exporta 20 000 puntos y ≈ 60 MB de memoria del proceso. Un atributo mal puesto (un id, una URL con parámetros) **tumba tu aplicación**, no solo el backend. Defensa: atributos de dominio acotado, revisión de código con la pregunta «¿cuántos valores distintos puede tomar esto?» y *views* con `attribute_keys`.
    2. **Los buckets por defecto mienten sin avisar.** Los del SDK están pensados para milisegundos; con segundos o tokens, casi todo cae en 1–2 buckets (medido: p50 con +58 % de error). Los de la spec GenAI (×2 o ×4) son un compromiso genérico: errores del 5–10 % en la latencia y casi todos los tokens de entrada en un solo bucket. Pon **un límite en tu SLO** y rejilla fina donde está la masa, o usa histogramas exponenciales.
    3. **Nunca promedies percentiles.** `avg(histogram_quantile(0.95, sum by (le, error_type)(…)))` dio ≈ 5 s frente a ≈ 9 s del p95 correcto (sección 7.5). Agrega **buckets** (`sum by (le)`), luego el percentil. Es el error nº 1 en dashboards de latencia (lo advierte la propia guía de histogramas de Prometheus: los cuantiles no se pueden agregar).
    4. **Dos *views* sobre el mismo instrumento crean dos *streams* con el mismo nombre** (verificado en 3.3): al exportar a Prometheus colisionan o duplican series. Una View por instrumento que combine criterios, atributos y agregación.
    5. **El Collector no transporta histogramas exponenciales a Prometheus** por la ruta `prometheus`-exporter: solo queda `+Inf`, `_sum` y `_count` (medido con 0.162.0). Y Mimir **rechaza** exponenciales por defecto. La tabla de decisión: ruta B (OTLP directo) o `prometheusremotewrite`/OTLP a Mimir con los flags activados; si no, clásicos con buckets ajustados.
    6. **La temporalidad se decide en el emisor y Prometheus no perdona:** *delta* directo a Prometheus = HTTP 500 y serie ausente (sección 7); con el exporter del Collector, en cambio, se acumula. Si cambias `OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE` por un requisito de otro backend, revisa **todas** las rutas.
    7. **Los exemplars tienen condiciones y fecha de caducidad.** Se producen solo con un span *sampled* activo (filtro `trace_based`), en un histograma se conserva uno por bucket y por intervalo de exportación (último gana), en gauges/UpDownCounter **se descartan** y en counters queda el último. El endpoint del Collector solo expone los del **último punto acumulado**: sin tráfico reciente no hay rombos (lo vimos en el laboratorio). Y con *tail sampling* (módulo 18) un exemplar puede apuntar a una traza **descartada**: decide qué trazas conservar *sabiendo* qué exemplars has publicado (p. ej., conserva siempre las de error/lentas).
    8. **Los nombres son una API pública.** `USD` acaba en el nombre (`..._USD_total`), un gauge con unidad `1` recibe `_ratio`, `{token}` desaparece. Con Prometheus 3 puedes conservar los puntos (`NoUTF8EscapingWithSuffixes`), y entonces las consultas llevan el nombre entre comillas (`{"gen_ai.client.inference.duration_seconds_bucket"}`), como hace la propia spec GenAI en sus ejemplos. Elige una vez, documenta y no lo cambies sin migración.
    9. **`service.instance.id` único… y estable por proceso.** Dos procesos con el mismo id escribirían en la **misma serie** (contadores a saltos, `rate()` sin sentido). Al revés, un id nuevo en cada arranque (como hace `setup_telemetry`, y como pasa al relanzar una celda de notebook) deja series muertas durante el *lookback* de 5 min: en dashboards usa `sum without (instance)` y no compares `instance`.
    10. **`resource_to_telemetry_conversion` está obsoleto en el Collector 0.162** (el log lo avisa): copiar todos los atributos de recurso a cada serie mezcla identidad con descripción. La vía recomendada es `target_info` + promover unos pocos atributos.
    """)

    md("""
    ---
    # ⚠️ Errores comunes

    | Error | Síntoma | Arreglo |
    |---|---|---|
    | `rate()` con ventana < 2 × *scrape* | Panel vacío o a saltos | Ventana ≥ 4 × intervalo (`[1m]` con 15 s) o `$__rate_interval` en Grafana |
    | `histogram_quantile()` sin `sum by (le)` | Percentiles por serie, valores raros o `NaN` | `histogram_quantile(q, sum by (le) (rate(x_bucket[..])))` |
    | `rate()` sobre un *gauge* | Resultado sin sentido | `rate`/`increase` solo con contadores; para gauges `avg_over_time`, `max_over_time` |
    | Medir tiempos con un *gauge* | Picos invisibles | Histogram |
    | `customer_id` / `ticket_id` como atributo | Explosión de series, memoria, 429 en Mimir | Spans/logs; agrupa por tier |
    | Cambiar los límites de bucket «en caliente» | Saltos en p95; `sum by (le)` mezcla límites distintos | Versiona la métrica (nombre nuevo) o migra con ventana de solape |
    | Registrar la métrica fuera del span | Sin exemplars | Compón el instrumentor de métricas **dentro** del de trazas |
    | Contar dos veces (dos instrumentores) | Totales ×2 | `emit_metrics=False` en uno de ellos y conciliar con la verdad |
    | Unidad equivocada (ms en lugar de s) | Gráficos ×1000 | Unidades UCUM base (`s`, `By`); la spec GenAI usa segundos |
    | Olvidar el modo *degradado* | Notebook bloqueado sin stack | `check_stack()` y rama sin servicios |
    """)

    # ------------------------------------------------------------------------------------------ autoevaluación
    md("""
    ---
    # Autoevaluación
    """)
    md(details("1 · **(Cálculo)** Un contador se raspa cada 15 s con los valores 100, 115, 130, 145, 160 (ventana de 60 s alineada). ¿Cuánto vale `rate(x[1m])`? ¿Y si en la 4.ª muestra el valor fuera 5 (reinicio) y la 5.ª 20?",
               "Sin reinicio: incremento 60 en 60 s → **1 req/s**. Con reinicio: saltos +15, +15, y al caer a 5 se suma el valor tras el reinicio (5), luego +15 → incremento = 15 + 15 + 5 + 15 = **50** → ≈ **0,83 req/s** (la resta ingenua `20 − 100` daría −80)."))
    md(details("2 · **(Cálculo)** Buckets acumulados `le=1:50, le=2:80, le=4:95, le=8:100, +Inf:100`. ¿Cuánto da `histogram_quantile(0.90, …)` y `histogram_quantile(0.99, …)`?",
               "N = 100. **p90**: rango 90 → bucket (2, 4]: acumulado previo 80, cuenta 15 → 2 + 2·(10/15) = **3,33 s**. **p99**: rango 99 → bucket (4, 8]: previo 95, cuenta 5 → 4 + 4·(4/5) = **7,2 s**. El valor real no se conoce; es interpolación lineal."))
    md(details("3 · **(Cálculo)** `gen_ai.execute_tool.duration` con 4 herramientas × 3 `error.type` × 2 agentes y 11 límites de bucket. ¿Cuántas series? ¿Y si añades `gen_ai.request.model` con 3 modelos?",
               "4·3·2 = 24 combinaciones × (11 + 3) = **336 series**. Con 3 modelos: 24·3 = 72 × 14 = **1 008**. (Los ids únicos, en cambio, no tienen techo.)"))
    md(details("4 · **(Diagnóstico)** Cambias el SDK a temporalidad *delta* «para ahorrar memoria» y exportas directo a Prometheus. Los paneles se quedan vacíos y no hay errores en tu app. ¿Por qué y cómo lo confirmas?",
               "Prometheus rechaza delta por defecto (HTTP 500, `invalid temporality and type combination`); el exportador solo registra `Failed to export metrics batch code: 500`. Se confirma en el log del exportador/Prometheus y consultando que la serie no existe. Arreglo: *cumulative* (o, de forma experimental, `--enable-feature=otlp-deltatocumulative`)."))
    md(details("5 · **(Diagnóstico)** En Grafana no aparecen rombos de exemplars. Enumera, en orden, las comprobaciones.",
               "(1) ¿Hay tráfico reciente? (2) ¿Se registra dentro de un span *sampled*? (filtro `trace_based`). (3) ¿`curl :8889/metrics -H 'Accept: application/openmetrics-text'` muestra `# {trace_id=…}`? (`enable_open_metrics`). (4) ¿`/api/v1/query_exemplars` en Prometheus devuelve datos? (`exemplar-storage`). (5) ¿El datasource tiene `exemplarTraceIdDestinations` y el panel `exemplar: true`? (6) ¿El tipo es histograma/counter (no gauge)? (7) ¿Existe la traza en Tempo (tail sampling)?"))
    md(details("6 · **(Diagnóstico)** Despliegas un cambio que solo modifica los límites de bucket de la latencia y el p95 «mejora» un 20 % sin cambiar nada real. ¿Qué ha pasado y cómo se evita?",
               "`histogram_quantile` interpola dentro del bucket: otros límites → otra estimación (error de resolución, no de rendimiento). Peor: durante el solape `sum by (le)` mezcla series con `le` distintos. Evítalo versionando la métrica, mejorando la resolución una sola vez y anotando el cambio en el dashboard."))
    md(details("7 · **(Transferencia, producto)** Quieres facturar por cliente según tokens. ¿Por qué no `customer_id` en la métrica y qué haces?",
               "Cardinalidad ilimitada. Alternativas: (a) atribuir en **spans/logs** (`supportops.customer.id`) y agregar en un almacén analítico; (b) métricas con etiqueta de **segmento** acotado (tier, plan) y un top-N de clientes grandes; (c) *recording rules* sobre un pipeline de eventos; (d) consultar Loki/Tempo para el detalle. Las métricas dan el total y la tendencia; el detalle fino va en eventos."))
    md(details("8 · **(Transferencia, ML)** Quieres vigilar la deriva (*drift*) de la longitud del prompt como se vigila una *feature* en un modelo. ¿Qué instrumento y qué consulta?",
               "Un **histograma** (`gen_ai.client.inference.operation.input_tokens`) con buckets ajustados o exponencial, y comparar `histogram_quantile(0.5/0.95, …)` hoy frente a hace una semana (`offset 7d`). Es el equivalente a monitorizar la distribución de una *feature* (PSI/KS) con percentiles; para una prueba formal exporta los buckets y calcula la divergencia fuera de PromQL."))

    md("""
    ---
    # Referencias

    **Especificaciones (OpenTelemetry)**
    - OpenTelemetry, *Metrics SDK* — incluye *Cardinality limits* (estable), *Views*, *Exemplar* y temporalidad: <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md>
    - OpenTelemetry, *Prometheus and OpenMetrics Compatibility* (traducción de nombres, unidades, exemplars, `target_info`): <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/compatibility/prometheus_and_openmetrics.md>
    - OpenTelemetry, *Semantic conventions for GenAI* (repositorio `semantic-conventions-genai`; estado Development): `docs/gen-ai/gen-ai-metrics.md`, `gen-ai-token-metrics.md`, `client-inference.md` y `non-normative/token-metrics-design.md` en <https://github.com/open-telemetry/semantic-conventions-genai>

    **Prometheus**
    - Prometheus, *Using Prometheus as your OpenTelemetry backend* (receptor OTLP, `promote_resource_attributes`, `target_info`, UTF-8, delta): <https://github.com/prometheus/docs/blob/main/docs/guides/opentelemetry.md>
    - Prometheus, *Histograms and summaries* (por qué no se agregan los cuantiles): <https://github.com/prometheus/docs/blob/main/docs/practices/histograms.md> · *Metric and label naming*: <https://github.com/prometheus/docs/blob/main/docs/practices/naming.md>
    - Prometheus, *Feature flags* (`exemplar-storage`, `otlp-deltatocumulative`, `otlp-native-delta-ingestion`) y *Configuration* (`otlp:`, `scrape_native_histograms`): <https://github.com/prometheus/prometheus/blob/v3.15.0/docs/feature_flags.md>, <https://github.com/prometheus/prometheus/blob/v3.15.0/docs/configuration/configuration.md>
    - Prometheus, *CHANGELOG* (3.8.0: histogramas nativos estables; 3.9.0: el flag `native-histograms` pasa a no-op): <https://github.com/prometheus/prometheus/blob/v3.15.0/CHANGELOG.md>

    **Grafana**
    - Grafana Mimir, *Configure the OpenTelemetry Collector to write metrics into Mimir* y *Configure native histograms*: <https://github.com/grafana/mimir/tree/main/docs/sources/mimir/configure> · *Authentication and authorization* (`X-Scope-OrgID`): <https://github.com/grafana/mimir/blob/main/docs/sources/mimir/manage/secure/authentication-and-authorization.md>
    - Grafana, *Dashboard best practices* (RED, USE, golden signals): <https://github.com/grafana/grafana/blob/main/docs/sources/visualizations/dashboards/build-dashboards/best-practices/index.md>
    - Tom Wilkie, *The RED Method: How to instrument your services* (2018): <https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services>

    **SRE**
    - Beyer et al., *Site Reliability Engineering*, cap. 6 «Monitoring Distributed Systems» (cuatro señales de oro): <https://sre.google/sre-book/monitoring-distributed-systems/>

    > ℹ️ Las versiones usadas y verificadas en el laboratorio: Prometheus v3.15.0, OTel Collector contrib 0.162.0, Grafana 13.2.4, `opentelemetry-sdk` 1.45.1. La spec GenAI es *Development*: revisa los nombres antes de fijarlos en producción.
    """)
    nb.save(out)


# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "09_proyecto_metricas.ipynb", "Proyecto 09 · Métricas de negocio y de modelo de SupportOps (histogramas y exemplars)")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 09 · Métricas de negocio y de modelo de SupportOps: histogramas, coste y exemplars

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 1 h 30 min |
    | **Servicios de Compose** | **Opcionales**: `core` + `metrics` (`docker compose --profile core --profile metrics up -d`, ≈ 0,45 GB). La rúbrica base corre **sin Docker**; con stack se añaden comprobaciones en vivo contra Prometheus |
    | **Prerrequisitos** | Lección `09_metricas` (instrumentos, buckets, cardinalidad, exemplars, PromQL) y `setup_telemetry`/`OTelInstrumentor` del módulo 03 |
    | **Conexión** | Construyes tú la capa de métricas que en la lección te dimos hecha (`MetricsInstrumentor`). Es la base de los paneles del módulo 10 y del FinOps del 13 |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. El equipo de finanzas pregunta *«¿cuánto nos cuesta cada ticket y qué modelo lo gasta?»*; el on-call, *«¿cuál es el p95 de hoy y qué herramienta lo está empeorando?»*; y el responsable de plataforma, *«¿cuántas series va a añadir esto a Prometheus?»*. Las trazas no responden a ninguna de las tres a escala: necesitas **métricas** bien diseñadas: coste y tokens como contadores, latencias como histogramas con buckets que midan **de verdad**, atributos acotados y *exemplars* para saltar a la traza.

    ## Datos

    Tráfico sintético de SupportOps con **semilla fija** (`generate_tickets(…, seed=42)`, `LLM_PROVIDER=mock`, tiempos simulados deterministas): sin descargas ni licencias. Cadena de datos: **stack local** (opcional, para la parte en vivo) → **modo degradado** (todo en memoria con `InMemoryMetricReader`, mismo esquema) → datos regenerables por semilla. No hay datasets externos.

    ## Qué vas a construir (los 6 TODOs)

    | TODO | Entregable |
    |---|---|
    | 1 | `PRICES` y `cost()`: tabla de precios **ilustrativa** y función de coste (error claro con modelos desconocidos) |
    | 2 | `LATENCY_BOUNDS` y `TOKEN_BOUNDS`: límites de bucket que midan p50/p95/p99 con poco error (se evalúa con **otras semillas**) |
    | 3 | `build_metrics(meter)`: los 8 instrumentos con nombre, tipo y unidad exactos |
    | 4 | `Recorder`: un `Instrumentor` que registra las métricas (RED + tokens + coste) con atributos **acotados** |
    | 5 | `series_budget()`: presupuesto de series (∏ valores × (B+3) en histogramas) |
    | 6 | `PROMQL`: seis consultas del *playbook* (con los nombres que producirá Prometheus) |

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución, `mock`, semillas 7 y 99) |
    |---|---|---|---|
    | R1 | `cost()` | 5 casos exactos (tolerancia 1e-9) y `KeyError` en modelo desconocido | 5/5 + error |
    | R2 | Buckets | ≤ 20 límites crecientes, con **3,0 s** (umbral de SLO) entre ellos; error de p50/p95/p99 de latencia ≤ 3 % / 10 % / 20 % y de p50/p95 de tokens ≤ 3 % / 10 % en las semillas **7 y 99** (1 000 tickets) | La solución mide ≤ 1 % / 7 % / 16 % y ≤ 0,3 % / 7,1 %; los límites de la spec dan 6-7 % (p50) y 59 % (tokens) |
    | R3 | Instrumentos | Nombres, tipos y unidades exactos; los histogramas usan **tus** límites | 8/8 |
    | R4 | Conciliación | Peticiones = 200 y por estado; tokens y coste = verdad del agente (rtol 1e-4; el coste 2e-3 porque el agente redondea `cost_usd` a 6 decimales); cuenta y suma de duraciones; nº de llamadas LLM y de herramientas | 8 magnitudes |
    | R5 | Cardinalidad | Atributos **exactamente** los pedidos; sin ids; series totales ≤ presupuesto declarado y ≤ 700; `series_budget` correcto | ver celda |
    | R6 | Exemplars | ≥ 1 exemplar en la duración y el 100 % apunta a una traza capturada | 100 % |
    | R7 | PromQL (estático) | 6 consultas con la forma correcta (`sum by (le)`, ventana ≥ 1 m, nombres válidos…) | 6/6 |
    | L1-L3 | *(con stack)* | Las consultas devuelven datos y se parecen a la verdad (tolerancias amplias por el desfase del *scrape*) | informativo |

    > 📏 Los umbrales salen de la solución de referencia (abajo), probada con semillas 42, 7, 99 y 123. No dependen de tu máquina: los tiempos son simulados.
    """)

    code(boot("viz,otel"))
    code(SETUP + '''
from contextlib import contextmanager
STACK = check_stack("core+metrics")
LIVE = not STACK.degraded
print("Modo:", "COMPLETO (con Prometheus)" if LIVE else "DEGRADADO (rúbrica base en memoria; sin comprobaciones en vivo)")
''')

    md("""
    ## Paso 0 · Herramientas que te damos hechas

    Son las del lección: la traducción de nombres a Prometheus, `histogram_quantile` y una forma de medir el error de un percentil con unos límites.
    """)
    code(r'''
import re
UNIT_WORDS = {"s": "seconds", "ms": "milliseconds", "By": "bytes", "%": "percent"}
def prom_name(name, unit="", kind="sum", monotonic=True):
    """Serie(s) de Prometheus de una métrica OTel (misma función que en la lección)."""
    base = re.sub(r"_+", "_", re.sub(r"[^a-zA-Z0-9_:]", "_", name))
    u = re.sub(r"\{[^}]*\}", "", unit or "").strip()
    word = UNIT_WORDS.get(u, re.sub(r"[^a-zA-Z0-9_]", "_", u)) if u and u != "1" else ""
    if kind == "gauge" and u == "1": word = "ratio"
    if word and not base.endswith("_" + word): base += "_" + word
    if kind == "sum" and monotonic and not base.endswith("_total"): base += "_total"
    return [base + s for s in ("_bucket", "_sum", "_count")] if kind == "histogram" else [base]

def to_buckets(values, bounds):
    idx = np.searchsorted(bounds, np.asarray(values), side="left"); counts = np.bincount(idx, minlength=len(bounds) + 1)
    return list(zip([*bounds, float("inf")], np.cumsum(counts)))

def hist_quantile(q, buckets):
    total = buckets[-1][1]; rank = q * total
    b = next(i for i, (_, c) in enumerate(buckets) if c >= rank)
    if b == len(buckets) - 1: return buckets[-2][0]
    lo, c_lo = (0.0, 0.0) if b == 0 else buckets[b - 1]; hi, c_hi = buckets[b]
    return lo + (hi - lo) * (rank - c_lo) / (c_hi - c_lo)

def bucket_quantile(values, bounds, q): return hist_quantile(q, to_buckets(values, bounds))

def sample_runs(seed, n=1000):
    """Latencias del agente y tokens de entrada por llamada de n tickets (para evaluar buckets)."""
    tk = generate_tickets(n, seed=seed, fault_rates=DEFAULT_FAULT_RATES); res = run_tickets(SupportAgent(), tk)
    return (np.array([r.latency_s for r in res]), np.array([s.input_tokens for r in res for s in r.steps if s.kind == "llm" and s.status == "ok"]))

def quantile_errors(values, bounds, qs=(0.5, 0.95, 0.99)):
    """Error relativo (%) de histogram_quantile con esos límites frente al percentil verdadero."""
    return {f"p{int(q*100)}": round(100 * (bucket_quantile(values, bounds, q) - np.quantile(values, q)) / np.quantile(values, q), 1) for q in qs}

TRAIN_LAT, TRAIN_TOK = sample_runs(42, 600)                 # muestra de «entrenamiento» (la rúbrica evalúa con OTRAS semillas)
print(f"Muestra de entrenamiento: latencia p50={np.quantile(TRAIN_LAT, .5):.2f}s p95={np.quantile(TRAIN_LAT, .95):.2f}s p99={np.quantile(TRAIN_LAT, .99):.2f}s · tokens de entrada p50={np.quantile(TRAIN_TOK, .5):.0f} p95={np.quantile(TRAIN_TOK, .95):.0f}")
print("Con los límites de la spec GenAI (para comparar):", quantile_errors(TRAIN_LAT, SPEC_AGENT_DURATION_BOUNDARIES), quantile_errors(TRAIN_TOK, SPEC_TOKEN_BOUNDARIES, (0.5, 0.95)))
''')

    # ------------------------------------------------------------------------------------------------ TODO 1
    md("""
    ## Paso 1 · Del token al dólar (TODO 1)

    Define `PRICES` con los precios **ilustrativos** del curso (**no son precios reales**): `mock-small` = 0,25 USD de entrada y 1,25 de salida por millón de tokens; `mock-large` = 3,00 y 15,00. Implementa `cost(model, input_tokens, output_tokens)` en USD. Un modelo desconocido debe lanzar `KeyError` (mejor un error claro que un coste 0 en silencio).
    """)
    md(hint(1, "$C = (n_{in}\\,p_{in} + n_{out}\\,p_{out})/10^6$. Guarda `{modelo: (p_in, p_out)}` y desempaqueta con `pin, pout = PRICES[model]` (el `KeyError` sale solo)."))
    code('''
PRICES = {}   # TODO 1a: {"mock-small": (0.25, 1.25), "mock-large": (3.00, 15.00)}  (USD por millón de tokens: entrada, salida)

def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    # TODO 1b
    raise NotImplementedError("TODO 1")

try:
    print(f"{cost('mock-small', 1000, 100):.6f} USD (esperado 0.000375)")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------------ TODO 2
    md("""
    ## Paso 2 · Buckets que midan de verdad (TODO 2)

    Elige `LATENCY_BOUNDS` (segundos) y `TOKEN_BOUNDS` (tokens de entrada por llamada). Restricciones: **≤ 20 límites**, estrictamente crecientes, y `LATENCY_BOUNDS` debe incluir **3.0** (tu umbral de SLO). Mira la distribución de la muestra de entrenamiento y pon los límites **donde está la masa**. La rúbrica los evalúa con **otras semillas** (7 y 99): no sobreajustes a la 42.
    """)
    md(hint(1, "Mira `np.quantile(TRAIN_LAT, [.05,.25,.5,.75,.9,.95,.99])`. Quieres rejilla fina (cada 0,25–0,5 s) entre ≈ 0,25 s y 5 s y pocos límites en la cola (7,5; 10; 20; 40). Para los tokens, la masa está entre ≈ 300 y 900: límites cada 50-100 ahí."))
    md(hint(2, "Una disposición que funciona: latencia `[0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10, 20, 40]`; tokens `[100, 200, 300, 350, 400, 450, 500, 600, 800, 1000, 1500, 2000, 4000, 8000]`. Pero entiende *por qué*: comprueba tú el error con `quantile_errors`."))
    code('''
LATENCY_BOUNDS = []   # TODO 2a (segundos)
TOKEN_BOUNDS = []     # TODO 2b (tokens)

if LATENCY_BOUNDS and TOKEN_BOUNDS:
    print("latencia:", quantile_errors(TRAIN_LAT, LATENCY_BOUNDS), "· tokens:", quantile_errors(TRAIN_TOK, TOKEN_BOUNDS, (0.5, 0.95)))
else:
    print("Pendiente: rellena LATENCY_BOUNDS y TOKEN_BOUNDS")
''')

    # ------------------------------------------------------------------------------------------------ TODO 3
    md("""
    ## Paso 3 · Los instrumentos (TODO 3)

    `build_metrics(meter)` devuelve un `dict` con **estos ocho instrumentos exactamente** (nombre OTel, tipo, unidad). Los histogramas llevan sus límites como *advisory* (`explicit_bucket_boundaries_advisory=`):

    | clave | nombre OTel | tipo | unidad | límites |
    |---|---|---|---|---|
    | `requests` | `proj09.agent.requests` | Counter | `{request}` | — |
    | `duration` | `proj09.agent.duration` | Histogram | `s` | `LATENCY_BOUNDS` |
    | `in_tokens` | `proj09.llm.input_tokens` | Counter | `{token}` | — |
    | `out_tokens` | `proj09.llm.output_tokens` | Counter | `{token}` | — |
    | `cost` | `proj09.llm.cost` | Counter | `USD` | — |
    | `llm_duration` | `proj09.llm.call.duration` | Histogram | `s` | `LATENCY_BOUNDS` |
    | `tool_duration` | `proj09.tool.duration` | Histogram | `s` | `LATENCY_BOUNDS` |
    | `tokens_per_call` | `proj09.llm.input_tokens_per_call` | Histogram | `{token}` | `TOKEN_BOUNDS` |
    """)
    md(hint(1, "`meter.create_counter(name, unit=..., description=...)` y `meter.create_histogram(name, unit=..., description=..., explicit_bucket_boundaries_advisory=[...])`. Devuelve un diccionario `{\"requests\": ..., ...}`."))
    code('''
def build_metrics(meter) -> dict:
    # TODO 3
    raise NotImplementedError("TODO 3")

try:
    _mp, _rd = make_meter_provider(otlp_endpoint=None); print(sorted(build_metrics(_mp.get_meter("t"))))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------------ TODO 4
    md("""
    ## Paso 4 · El instrumentor de métricas (TODO 4)

    `Recorder` es un `Instrumentor` (módulo 01-03). Registra:

    - **al terminar cada ticket** (`agent_run`, leyendo `ctx.result`): `requests` con atributos **`status`, `intent`, `tier`** (`intent` = `r.intent_pred` o `"unknown"`; `tier` = `ctx.ticket.tier`) y `duration` (`r.latency_s`) con atributos **`model`, `status`**;
    - **en cada llamada al LLM** (`llm_call`): `llm_duration` (duración con el reloj simulado `ctx.clock.now_s()`) con **`model`, `outcome`** (`ok`/`error`); si hubo respuesta: `in_tokens`, `out_tokens`, `cost` (con `cost()`) y `tokens_per_call` (tokens de entrada), todos con **`model`**;
    - **en cada herramienta** (`tool_call`): `tool_duration` con **`tool`** (`info.call.name`) y **`outcome`**.

    Las llamadas **fallidas también cuentan** (duración con `outcome="error"`, sin tokens). **Ningún** atributo puede ser un id (`ticket_id`, `customer_id`…).
    """)
    md(hint(1, "Sigue el patrón de la lección: `try: yield / except BaseException: outcome = \"error\"; raise / finally: <registrar>`. En `llm_call` la respuesta está en `info.response` (puede ser `None` si hubo error): `info.response.usage.input_tokens`."))
    md(hint(2, "Dentro de `finally` de `llm_call`: `dur = ctx.clock.now_s() - t0`; `self.m[\"llm_duration\"].record(dur, {\"model\": info.model, \"outcome\": outcome})`; `r = info.response`; `if r is not None:` suma tokens y coste con `{\"model\": info.model}`."))
    code('''
class Recorder(Instrumentor):
    def __init__(self, meter_provider):
        self.m = build_metrics(meter_provider.get_meter("proj09"))

    @contextmanager
    def agent_run(self, ctx):
        try:
            yield
        finally:
            r = ctx.result
            if r is not None:
                pass   # TODO 4a: requests y duration

    @contextmanager
    def llm_call(self, ctx, info):
        t0 = ctx.clock.now_s(); outcome = "ok"
        try:
            yield
        except BaseException:
            outcome = "error"; raise
        finally:
            pass       # TODO 4b: llm_duration (+ tokens, coste y tokens_per_call si hay respuesta)

    @contextmanager
    def tool_call(self, ctx, info):
        t0 = ctx.clock.now_s(); outcome = "ok"
        try:
            yield
        except BaseException:
            outcome = "error"; raise
        finally:
            pass       # TODO 4c: tool_duration
''')
    code('''
def run_inmemory(n=200, seed=SEED):
    """Ejecuta n tickets con trazas (para exemplars) + tu Recorder; devuelve filas de métricas, resultados y trazas capturadas."""
    tr = setup_telemetry("proj09-lab", mode="memory", metrics=False, logs=False)
    mp, rd = make_meter_provider(otlp_endpoint=None)
    ag = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(tr, emit_metrics=False), Recorder(mp)))
    tk = generate_tickets(n, seed=seed, fault_rates=DEFAULT_FAULT_RATES); res = run_tickets(ag, tk)
    return pd.DataFrame(metric_rows(rd)), res, {s["trace_id"] for s in tr.span_records()}

try:
    ROWS, RES, TRACE_IDS = run_inmemory()
    display(ROWS.groupby("name").agg(kind=("kind", "first"), unit=("unit", "first"), series=("name", "size")))
except NotImplementedError as e:
    ROWS = None; print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------------ TODO 5
    md("""
    ## Paso 5 · Presupuesto de series (TODO 5)

    Implementa `series_budget(attrs, n_bounds=None)`: `attrs` es `{atributo: nº máximo de valores}`; devuelve el nº **máximo** de series que generaría el instrumento en Prometheus: el producto de los valores y, si es un histograma clásico (`n_bounds` = nº de límites finitos), por **`n_bounds + 3`** (`n_bounds+1` buckets incluido `+Inf`, más `_sum` y `_count`). Sin atributos → 1 serie.
    Después rellena `DECLARED` con el presupuesto de **tus 8 instrumentos** según el diseño de arriba (valores máximos razonables: 5 estados, 5 intenciones, 2 tiers, 2 modelos, 4 herramientas, 2 *outcomes*) y calcula `TOTAL_BUDGET`.
    """)
    md(hint(1, "`math.prod(attrs.values()) * (n_bounds + 3 if n_bounds is not None else 1)`. Ejemplo: `requests` = 5·5·2 = 50 series; `duration` = (2 modelos · 5 estados) · (B+3)."))
    code('''
import math
def series_budget(attrs: dict, n_bounds: int | None = None) -> int:
    # TODO 5a
    raise NotImplementedError("TODO 5")

DECLARED = {}      # TODO 5b: {"requests": ..., "duration": ..., "in_tokens": ..., "out_tokens": ..., "cost": ..., "llm_duration": ..., "tool_duration": ..., "tokens_per_call": ...}
TOTAL_BUDGET = 0   # TODO 5c: suma de DECLARED
''')

    # ------------------------------------------------------------------------------------------------ TODO 6
    md("""
    ## Paso 6 · El *playbook* de PromQL (TODO 6)

    Escribe en `PROMQL` seis consultas (cadenas). Los nombres de serie de Prometheus los produce la traducción de la lección (`prom_name`): **no los adivines, calcúlalos**. Usa ventanas de **`[1m]`** (el *scrape* es de 15 s) y `sum by (le)` en los percentiles.

    | clave | pregunta |
    |---|---|
    | `rate` | peticiones por segundo |
    | `error_ratio` | fracción de peticiones con `status` `error` o `max_steps` |
    | `p95` | p95 de la duración del agente |
    | `cost_per_hour` | USD por hora |
    | `tokens_per_request` | tokens de entrada por petición (cociente de dos tasas) |
    | `slowest_tool` | herramienta con mayor duración **media** (`topk(1, …)` de `sum/count` por `tool`) |
    """)
    code('''
VALID = set()
for _n, _u, _k, _m in [("proj09.agent.requests", "{request}", "sum", True), ("proj09.agent.duration", "s", "histogram", True), ("proj09.llm.input_tokens", "{token}", "sum", True),
                       ("proj09.llm.output_tokens", "{token}", "sum", True), ("proj09.llm.cost", "USD", "sum", True), ("proj09.llm.call.duration", "s", "histogram", True),
                       ("proj09.tool.duration", "s", "histogram", True), ("proj09.llm.input_tokens_per_call", "{token}", "histogram", True)]:
    VALID.update(prom_name(_n, _u, _k, _m))
print(len(VALID), "series válidas, p. ej.:", sorted(VALID)[:3])

PROMQL = {   # TODO 6: rellena las seis claves: rate, error_ratio, p95, cost_per_hour, tokens_per_request, slowest_tool
}
''')

    md("""
    ## Paso 7 (opcional, con stack) · Tráfico en vivo y validación en Prometheus

    Si el stack está arriba, enviamos 60 s de tráfico con **tu** `Recorder` por el Collector y evaluamos **tus** consultas contra Prometheus. Es lo que hará la rúbrica en las filas `L1-L3`.
    """)
    code('''
def run_live_project(secs=60):
    tr = setup_telemetry("proj09-lab", metrics=False, logs=False)                    # trazas por OTLP (para exemplars)
    mp, rd = make_meter_provider("proj09-lab", otlp_endpoint="http://localhost:4318/v1/metrics", interval_s=5)
    ag = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(tr, emit_metrics=False), Recorder(mp)))
    tk = generate_tickets(secs * 2, seed=SEED, duration_s=secs, fault_rates=DEFAULT_FAULT_RATES, start_s=0.0)
    t0 = time.time(); res = run_live(ag, tk, secs); t1 = time.time()
    tr.force_flush(); mp.force_flush(); time.sleep(22)
    return res, t0, t1

LIVE_RUN = None
if LIVE and PROMQL and ROWS is not None:
    try: LIVE_RUN = run_live_project(60)
    except Exception as e: print("No se pudo ejecutar el tráfico en vivo:", type(e).__name__, str(e)[:100])
else:
    print("Se omite (sin stack, o aún faltan TODOs).")
''')

    md("""
    ## Paso 8 · Rúbrica
    """)
    code(r'''
def run_rubric():
    rows = []
    def add(r, d, ok, det=""): rows.append({"criterio": r, "descripción": d, "resultado": ("✅ OK" if ok else "❌ FALLA") if ok is not None else "⏭ n/a", "detalle": det})
    # R1 ---------------------------------------------------------------------------------------------------
    try:
        cases = [("mock-small", 1000, 100, 0.000375), ("mock-small", 0, 0, 0.0), ("mock-large", 2000, 300, 0.0105), ("mock-large", 1, 1, 0.000018), ("mock-small", 354, 19, 0.00011225)]
        good = sum(abs(cost(m, a, b) - e) < 1e-9 for m, a, b, e in cases)
        try: cost("gpt-desconocido", 1, 1); raised = False
        except KeyError: raised = True
        add("R1", "cost(): 5 casos exactos y KeyError en modelo desconocido", good == 5 and raised, f"{good}/5 · KeyError={raised}")
    except Exception as e: add("R1", "cost()", False, type(e).__name__)
    # R2 ---------------------------------------------------------------------------------------------------
    try:
        ok_shape = (0 < len(LATENCY_BOUNDS) <= 20 and 0 < len(TOKEN_BOUNDS) <= 20 and all(b > a for a, b in zip(LATENCY_BOUNDS, LATENCY_BOUNDS[1:]))
                    and all(b > a for a, b in zip(TOKEN_BOUNDS, TOKEN_BOUNDS[1:])) and 3.0 in LATENCY_BOUNDS)
        worst = {"p50": 0, "p95": 0, "p99": 0, "t50": 0, "t95": 0}
        for sd in (7, 99):
            lat, tok = sample_runs(sd, 1000); e = quantile_errors(lat, LATENCY_BOUNDS); t = quantile_errors(tok, TOKEN_BOUNDS, (.5, .95))
            for k in ("p50", "p95", "p99"): worst[k] = max(worst[k], abs(e[k]))
            worst["t50"], worst["t95"] = max(worst["t50"], abs(t["p50"])), max(worst["t95"], abs(t["p95"]))
        ok = ok_shape and worst["p50"] <= 3 and worst["p95"] <= 10 and worst["p99"] <= 20 and worst["t50"] <= 3 and worst["t95"] <= 10
        add("R2", "Buckets: forma válida, incluye 3.0 y errores de percentil acotados (semillas 7 y 99)", ok, f"forma={ok_shape} · peor error lat p50/p95/p99 = {worst['p50']}/{worst['p95']}/{worst['p99']} % · tokens p50/p95 = {worst['t50']}/{worst['t95']} %")
    except Exception as e: add("R2", "Buckets", False, type(e).__name__ + ": " + str(e)[:60])
    # R3 ---------------------------------------------------------------------------------------------------
    SPEC = {"requests": ("proj09.agent.requests", "{request}", "sum", None), "duration": ("proj09.agent.duration", "s", "histogram", "lat"),
            "in_tokens": ("proj09.llm.input_tokens", "{token}", "sum", None), "out_tokens": ("proj09.llm.output_tokens", "{token}", "sum", None),
            "cost": ("proj09.llm.cost", "USD", "sum", None), "llm_duration": ("proj09.llm.call.duration", "s", "histogram", "lat"),
            "tool_duration": ("proj09.tool.duration", "s", "histogram", "lat"), "tokens_per_call": ("proj09.llm.input_tokens_per_call", "{token}", "histogram", "tok")}
    try:
        mp, rd = make_meter_provider(otlp_endpoint=None); ins = build_metrics(mp.get_meter("r3")); good = []
        for k, (name, unit, kind, b) in SPEC.items():
            i = ins[k]; (i.record if kind == "histogram" else i.add)(1)
        got = {r["name"]: r for r in metric_rows(rd)}
        for k, (name, unit, kind, b) in SPEC.items():
            r = got.get(name); ok = r is not None and r["unit"] == unit and r["kind"] == ("histogram" if kind == "histogram" else "sum")
            if ok and b: ok = r["bounds"] == [float(x) for x in (LATENCY_BOUNDS if b == "lat" else TOKEN_BOUNDS)]
            good.append(ok)
        add("R3", "build_metrics(): 8 instrumentos con nombre, tipo, unidad y límites exactos", all(good), f"{sum(good)}/8")
    except Exception as e: add("R3", "build_metrics", False, type(e).__name__ + ": " + str(e)[:60])
    # R4 ---------------------------------------------------------------------------------------------------
    try:
        R, res, trace_ids = run_inmemory(200, SEED)
        def tot(name, **at):
            s = R[R.name == name]
            for k, v in at.items(): s = s[s.attributes.map(lambda a: a.get(k) == v)]
            return float(s["value"].sum()) if len(s) and s["kind"].iloc[0] == "sum" else float(s["count"].sum())
        truth = pd.DataFrame([(r.status, r.input_tokens, r.output_tokens, r.cost_usd, r.latency_s, r.n_llm_calls, r.n_tool_calls) for r in res], columns="status tin tout cost lat nl nt".split())
        checks = {"peticiones": (tot("proj09.agent.requests"), 200),
                  "peticiones «ok»": (tot("proj09.agent.requests", status="ok"), (truth.status == "ok").sum()),
                  "tokens entrada": (tot("proj09.llm.input_tokens"), truth.tin.sum()), "tokens salida": (tot("proj09.llm.output_tokens"), truth.tout.sum()),
                  "coste": (tot("proj09.llm.cost"), truth.cost.sum()), "Σ duración": (float(R[R.name == "proj09.agent.duration"]["sum"].sum()), truth.lat.sum()),
                  "llamadas LLM": (tot("proj09.llm.call.duration"), truth.nl.sum()), "herramientas": (tot("proj09.tool.duration"), truth.nt.sum())}
        bad = [k for k, (a, b) in checks.items() if not np.isclose(a, b, rtol=(2e-3 if k == "coste" else 1e-4), atol=1e-6)]
        add("R4", "Conciliación con la verdad del agente (8 magnitudes)", not bad, "todas coinciden" if not bad else f"no cuadran: {bad}")
    except Exception as e: R = None; add("R4", "Conciliación", False, type(e).__name__ + ": " + str(e)[:60])
    # R5 ---------------------------------------------------------------------------------------------------
    try:
        want = {"proj09.agent.requests": {"status", "intent", "tier"}, "proj09.agent.duration": {"model", "status"}, "proj09.llm.input_tokens": {"model"},
                "proj09.llm.output_tokens": {"model"}, "proj09.llm.cost": {"model"}, "proj09.llm.call.duration": {"model", "outcome"},
                "proj09.tool.duration": {"tool", "outcome"}, "proj09.llm.input_tokens_per_call": {"model"}}
        keys_ok = all({frozenset(a) for a in R[R.name == n].attributes} == {frozenset(w)} for n, w in want.items())
        pts = {n: len(R[R.name == n]) for n in want}
        def per_point(n):
            if R[R.name == n].iloc[0]["kind"] != "histogram": return 1
            return (len(TOKEN_BOUNDS) if "per_call" in n else len(LATENCY_BOUNDS)) + 3
        actual = sum(p * per_point(n) for n, p in pts.items())
        formula = (series_budget({"a": 2, "b": 3}) == 6 and series_budget({"a": 2, "b": 3}, 10) == 78 and series_budget({}) == 1)
        ok = keys_ok and formula and actual <= TOTAL_BUDGET <= 700 and TOTAL_BUDGET > 0 and len(DECLARED) == 8
        add("R5", "Cardinalidad: atributos exactos, series reales ≤ presupuesto declarado ≤ 700, series_budget correcto", ok, f"atributos={keys_ok} · fórmula={formula} · series reales={actual} · presupuesto declarado={TOTAL_BUDGET}")
    except Exception as e: add("R5", "Cardinalidad", False, type(e).__name__ + ": " + str(e)[:60])
    # R6 ---------------------------------------------------------------------------------------------------
    try:
        ex = [e for _, r in R[R.name == "proj09.agent.duration"].iterrows() for e in r["exemplars"]]
        ok = len(ex) >= 1 and all(e["trace_id"] in trace_ids for e in ex)
        add("R6", "Exemplars: ≥ 1 en la duración y todos apuntan a una traza capturada", ok, f"{len(ex)} exemplars · {sum(e['trace_id'] in trace_ids for e in ex)} con traza")
    except Exception as e: add("R6", "Exemplars", False, type(e).__name__)
    # R7 ---------------------------------------------------------------------------------------------------
    def window_ok(q):
        ws = re.findall(r"\[(\d+)([smh])\]", q); return bool(ws) and all((int(n) * {"s": 1, "m": 60, "h": 3600}[u]) >= 60 for n, u in ws) or "$__rate_interval" in q
    def names_ok(q):
        toks = set(re.findall(r"proj09_\w+", q)); return bool(toks) and toks <= VALID
    try:
        q = PROMQL
        chk = {"rate": names_ok(q["rate"]) and "rate(" in q["rate"] and window_ok(q["rate"]) and "proj09_agent_requests_total" in q["rate"],
               "error_ratio": names_ok(q["error_ratio"]) and "/" in q["error_ratio"] and "error" in q["error_ratio"] and window_ok(q["error_ratio"]),
               "p95": names_ok(q["p95"]) and "histogram_quantile(0.95" in q["p95"].replace(" ", "") and "sum by (le)" in q["p95"].replace("sum by(le)", "sum by (le)") and "_bucket" in q["p95"] and "rate(" in q["p95"] and window_ok(q["p95"]),
               "cost_per_hour": names_ok(q["cost_per_hour"]) and "proj09_llm_cost_USD_total" in q["cost_per_hour"] and "3600" in q["cost_per_hour"] and "rate(" in q["cost_per_hour"],
               "tokens_per_request": names_ok(q["tokens_per_request"]) and "proj09_llm_input_tokens_total" in q["tokens_per_request"] and "proj09_agent_requests_total" in q["tokens_per_request"] and "/" in q["tokens_per_request"] and window_ok(q["tokens_per_request"]),
               "slowest_tool": names_ok(q["slowest_tool"]) and "topk(1" in q["slowest_tool"].replace(" ", "") and "_sum" in q["slowest_tool"] and "_count" in q["slowest_tool"] and "tool" in q["slowest_tool"]}
        add("R7", "PromQL (estático): 6 consultas con forma, nombres y ventanas válidos", all(chk.values()), "fallan: " + ", ".join(k for k, v in chk.items() if not v) if not all(chk.values()) else "6/6")
    except Exception as e: add("R7", "PromQL", False, type(e).__name__ + ": " + str(e)[:60])
    # L1-L3 (informativas) ---------------------------------------------------------------------------------
    if LIVE_RUN is None:
        for r_, d_ in (("L1", "Consultas devuelven datos en Prometheus"), ("L2", "Valores cercanos a la verdad"), ("L3", "Exemplars en Prometheus")): add(r_, d_ + " (con stack)", None, "sin stack o sin ejecutar el Paso 7")
    else:
        try:
            res_l, t0, t1 = LIVE_RUN; at = t1 + 20; got = {k: prom_instant(v, at=at) for k, v in PROMQL.items()}
            nonempty = {k: bool(v) and v[0]["value"] is not None for k, v in got.items()}
            add("L1", "Las 6 consultas devuelven datos en Prometheus", all(nonempty.values()), str({k: (round(v[0]["value"], 3) if nonempty[k] else None) for k, v in got.items() if k != "slowest_tool"}))
            win = [r for r in res_l if t1 - 40 <= r.start_s <= t1]; n = len(win)
            tr_ = {"rate": n / 60, "error_ratio": np.mean([r.status in ("error", "max_steps") for r in win]), "cost_per_hour": sum(r.cost_usd for r in win) / 60 * 3600,
                   "tokens_per_request": sum(r.input_tokens for r in win) / n}
            rel = {k: abs(got[k][0]["value"] - tr_[k]) / max(abs(tr_[k]), 1e-9) for k in ("rate", "cost_per_hour", "tokens_per_request") if nonempty[k]}
            ok2 = all(v <= 0.45 for v in rel.values()) and nonempty["error_ratio"] and abs(got["error_ratio"][0]["value"] - tr_["error_ratio"]) <= 0.10
            add("L2", "Valores cercanos a la verdad (tolerancias amplias por el desfase del scrape)", ok2, str({k: round(v, 2) for k, v in rel.items()}))
            ex = prom_exemplars("proj09_agent_duration_seconds_bucket", minutes=4)
            add("L3", "Hay exemplars de tu métrica en Prometheus", len(ex) > 0, f"{len(ex)} exemplars")
        except Exception as e:
            for r_ in ("L1", "L2", "L3"): add(r_, "(en vivo)", False, type(e).__name__ + ": " + str(e)[:70])
    return pd.DataFrame(rows).set_index("criterio")
''')
    code('''
# Ejecuta esta celda cuando hayas terminado los TODO
display(run_rubric())
''')

    md("""
    ---
    ## Retos extra (nivel experto)

    1. **Exponencial:** añade una *View* que convierta `proj09.llm.call.duration` en histograma exponencial y envíalo por la **ruta B** (OTLP directo a Prometheus). Compara series y error de p99 con la versión clásica (sección 9 de la lección).
    2. **Guardia de cardinalidad:** haz que `Recorder` cuente los valores distintos de `intent` y, si pasan de 8, los agrupe en `"other"`. ¿Cómo lo probarías con una intención nueva inyectada?
    3. **Coste «al consultar»:** exporta un *gauge* observable `proj09.price` con atributos `model` y `direction` (`input`/`output`) y reescribe `cost_per_hour` en PromQL multiplicando tokens por precio con `on(model) group_left`. ¿Qué pasa al cambiar un precio?
    4. **Presupuesto en CI:** escribe un test que falle si el número real de series de `Recorder` supera `TOTAL_BUDGET` (por ejemplo tras añadir un atributo).
    5. **Detector de buckets malos:** dado un histograma exportado (`metric_rows`), calcula qué fracción de observaciones cae en el bucket de mayor masa y alerta si supera el 60 %.

    ## Reflexión (producción e hilo conductor)

    - Tu `cost()` lanza `KeyError` en un modelo desconocido, pero `MetricsInstrumentor` de la lección **no**: cuenta 0 y anota `unknown_models`. ¿Qué es mejor para un sistema en producción que no debe romper el agente por un fallo de telemetría? ¿Cómo **avisarías** sin romper?
    - ¿Qué cambia en tu diseño si mañana el agente usa 5 modelos y 12 herramientas? Recalcula el presupuesto de `tool_duration` y `duration`.
    - ¿Qué pregunta de finanzas **no** puedes responder con estas métricas (p. ej. «¿cuánto costó el cliente C-0007?»)? ¿Dónde vive esa respuesta (módulos 07-08, 13)?
    - En el módulo 10 construirás con estas consultas el dashboard «Salud del agente»: ¿cuáles pondrías en la fila superior y por qué?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine los TODO y vuelve a pasar la rúbrica).
    """)
    code(r'''
# ===================== SOLUCIÓN DE REFERENCIA =====================
# TODO 1
PRICES = {"mock-small": (0.25, 1.25), "mock-large": (3.00, 15.00)}      # USD por millón de tokens (ILUSTRATIVOS)
def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = PRICES[model]                                           # KeyError si el modelo no está en la tabla
    return (input_tokens * pin + output_tokens * pout) / 1_000_000

# TODO 2
LATENCY_BOUNDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10, 20, 40]
TOKEN_BOUNDS = [100, 200, 300, 350, 400, 450, 500, 600, 800, 1000, 1500, 2000, 4000, 8000]

# TODO 3
def build_metrics(meter) -> dict:
    return {
        "requests": meter.create_counter("proj09.agent.requests", unit="{request}", description="Peticiones por estado final"),
        "duration": meter.create_histogram("proj09.agent.duration", unit="s", description="Duración del agente", explicit_bucket_boundaries_advisory=LATENCY_BOUNDS),
        "in_tokens": meter.create_counter("proj09.llm.input_tokens", unit="{token}", description="Tokens de entrada"),
        "out_tokens": meter.create_counter("proj09.llm.output_tokens", unit="{token}", description="Tokens de salida"),
        "cost": meter.create_counter("proj09.llm.cost", unit="USD", description="Coste (precios ilustrativos)"),
        "llm_duration": meter.create_histogram("proj09.llm.call.duration", unit="s", description="Duración de la llamada al LLM", explicit_bucket_boundaries_advisory=LATENCY_BOUNDS),
        "tool_duration": meter.create_histogram("proj09.tool.duration", unit="s", description="Duración de una herramienta", explicit_bucket_boundaries_advisory=LATENCY_BOUNDS),
        "tokens_per_call": meter.create_histogram("proj09.llm.input_tokens_per_call", unit="{token}", description="Tokens de entrada por llamada", explicit_bucket_boundaries_advisory=TOKEN_BOUNDS),
    }

# TODO 4
class Recorder(Instrumentor):
    def __init__(self, meter_provider):
        self.m = build_metrics(meter_provider.get_meter("proj09"))

    @contextmanager
    def agent_run(self, ctx):
        try:
            yield
        finally:
            r = ctx.result
            if r is not None:
                self.m["requests"].add(1, {"status": r.status, "intent": r.intent_pred or "unknown", "tier": ctx.ticket.tier})
                self.m["duration"].record(r.latency_s, {"model": r.model, "status": r.status})

    @contextmanager
    def llm_call(self, ctx, info):
        t0 = ctx.clock.now_s(); outcome = "ok"
        try:
            yield
        except BaseException:
            outcome = "error"; raise
        finally:
            self.m["llm_duration"].record(max(ctx.clock.now_s() - t0, 0.0), {"model": info.model, "outcome": outcome})
            r = info.response
            if r is not None:
                at = {"model": info.model}
                self.m["in_tokens"].add(r.usage.input_tokens, at); self.m["out_tokens"].add(r.usage.output_tokens, at)
                self.m["cost"].add(cost(info.model, r.usage.input_tokens, r.usage.output_tokens), at)
                self.m["tokens_per_call"].record(r.usage.input_tokens, at)

    @contextmanager
    def tool_call(self, ctx, info):
        t0 = ctx.clock.now_s(); outcome = "ok"
        try:
            yield
        except BaseException:
            outcome = "error"; raise
        finally:
            self.m["tool_duration"].record(max(ctx.clock.now_s() - t0, 0.0), {"tool": info.call.name, "outcome": outcome})

# TODO 5
def series_budget(attrs: dict, n_bounds: int | None = None) -> int:
    return math.prod(attrs.values()) * (n_bounds + 3 if n_bounds is not None else 1)

DECLARED = {
    "requests": series_budget({"status": 5, "intent": 5, "tier": 2}),
    "duration": series_budget({"model": 2, "status": 5}, len(LATENCY_BOUNDS)),
    "in_tokens": series_budget({"model": 2}), "out_tokens": series_budget({"model": 2}), "cost": series_budget({"model": 2}),
    "llm_duration": series_budget({"model": 2, "outcome": 2}, len(LATENCY_BOUNDS)),
    "tool_duration": series_budget({"tool": 4, "outcome": 2}, len(LATENCY_BOUNDS)),
    "tokens_per_call": series_budget({"model": 2}, len(TOKEN_BOUNDS)),
}
TOTAL_BUDGET = sum(DECLARED.values())

# TODO 6
PROMQL = {
    "rate": "sum(rate(proj09_agent_requests_total[1m]))",
    "error_ratio": 'sum(rate(proj09_agent_requests_total{status=~"error|max_steps"}[1m])) / sum(rate(proj09_agent_requests_total[1m]))',
    "p95": "histogram_quantile(0.95, sum by (le) (rate(proj09_agent_duration_seconds_bucket[1m])))",
    "cost_per_hour": "sum(rate(proj09_llm_cost_USD_total[1m])) * 3600",
    "tokens_per_request": "sum(rate(proj09_llm_input_tokens_total[1m])) / sum(rate(proj09_agent_requests_total[1m]))",
    "slowest_tool": "topk(1, sum by (tool) (rate(proj09_tool_duration_seconds_sum[1m])) / sum by (tool) (rate(proj09_tool_duration_seconds_count[1m])))",
}
print("Presupuesto declarado por instrumento:", DECLARED, "· total", TOTAL_BUDGET)
ROWS, RES, TRACE_IDS = run_inmemory()
if LIVE and LIVE_RUN is None:
    LIVE_RUN = run_live_project(60)
display(run_rubric())
''')

    code(r'''
# Visualización de la solución: error de percentil con los límites de la spec frente a los tuyos, y series por instrumento
fig, axes = plt.subplots(1, 3, figsize=(16, 4.1))
lat7, tok7 = sample_runs(7, 1000)
labels = ["p50", "p95", "p99"]; spec = quantile_errors(lat7, SPEC_AGENT_DURATION_BOUNDARIES); mine = quantile_errors(lat7, LATENCY_BOUNDS)
x = np.arange(3); axes[0].bar(x - .2, [abs(spec[k]) for k in labels], .4, color=viz.PALETTE["warn"], label="límites de la spec"); axes[0].bar(x + .2, [abs(mine[k]) for k in labels], .4, color=viz.PALETTE["ok"], label="tus límites")
axes[0].set_xticks(x); axes[0].set_xticklabels(labels); axes[0].set_ylabel("|error| %"); axes[0].set_title("Latencia: error de percentil (semilla 7)"); axes[0].legend()
specT = quantile_errors(tok7, SPEC_TOKEN_BOUNDARIES, (.5, .95)); mineT = quantile_errors(tok7, TOKEN_BOUNDS, (.5, .95))
axes[1].bar([-.2, .8], [abs(specT["p50"]), abs(specT["p95"])], .4, color=viz.PALETTE["warn"]); axes[1].bar([.2, 1.2], [abs(mineT["p50"]), abs(mineT["p95"])], .4, color=viz.PALETTE["ok"])
axes[1].set_xticks([0, 1]); axes[1].set_xticklabels(["p50", "p95"]); axes[1].set_title("Tokens de entrada: error de percentil (semilla 7)")
axes[2].barh(list(DECLARED), list(DECLARED.values()), color=viz.PALETTE["metrics"]); axes[2].set_title(f"Presupuesto de series ({TOTAL_BUDGET} en total)"); axes[2].set_xlabel("series máx. en Prometheus")
plt.tight_layout(); plt.show()
''')
    nb.save(out)


README = """# Módulo 09 · Métricas: Prometheus/Mimir, instrumentos OpenTelemetry, RED + GenAI y exemplars

🟡 Intermedio · ≈ 4 h 30 min · Servicios: `core` + `metrics` (`docker compose --profile core --profile metrics up -d`, ≈ 0,45 GB). Funciona **sin Docker en modo degradado** (la parte con Prometheus se salta y se explica).

## Qué aprenderás
- El modelo de Prometheus y las **tres rutas** de las métricas OTel hasta Grafana (Collector → *scrape*, OTLP directo, Mimir).
- `rate()` y `histogram_quantile()` **implementados a mano** y comprobados contra un Prometheus real.
- Los instrumentos OTel (*Counter, UpDownCounter, Histogram, Gauge, Observable\\**), las *views*, y **cumulative frente a delta** (y por qué Prometheus rechaza delta).
- **Nombres en Prometheus**: sufijos de unidad y tipo, `target_info`, `job`/`instance`.
- **RED + métricas GenAI** de SupportOps (duración, tokens, coste, pasos) con la spec GenAI actual (estado *Development*), conciliadas con la verdad del agente; **coste con una tabla de precios ilustrativa**.
- **Exemplars** de extremo a extremo: del rombo de Grafana a la traza en Tempo.
- **Cardinalidad** (series = ∏ valores × (B+3)), el SDK de Python **sin límite** y presupuestos de series.
- **Histogramas clásicos frente a exponenciales/nativos** y por qué el Collector del curso no los transporta; qué cambia con Mimir.

## Archivos
| Archivo | Contenido |
|---|---|
| `09_metricas.ipynb` | Lección (≥ 12 gráficos, experimentos en vivo, 🧠 de élite, autoevaluación con cálculo/diagnóstico/transferencia) |
| `09_proyecto_metricas.ipynb` | Proyecto: construyes el `Recorder` de métricas (coste, buckets, instrumentos, cardinalidad, PromQL) con rúbrica R1-R7 (+ L1-L3 en vivo) |
| `img/09_dashboard.png` | Captura real del dashboard provisionado `09-genai-metrics` |
| `../supportops/otel_metrics.py` | `MetricsInstrumentor`, `PriceTable`, `run_live`, clientes de la API de Prometheus (lo reutilizan los módulos 10, 13, 16 y 18) |
| `../stack/grafana/dashboards/09-genai-metrics.json` | Dashboard aprovisionado (generado con `supportops/dashkit.py`) |

## Servicios necesarios
`core` + `metrics`. Sin ellos, los notebooks siguen funcionando en memoria (`InMemoryMetricReader`) y la rúbrica base del proyecto se completa.

## Lecturas
- OpenTelemetry, *Metrics SDK* (cardinality limits, views, exemplars) — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md>
- OpenTelemetry, *Prometheus and OpenMetrics Compatibility* — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/compatibility/prometheus_and_openmetrics.md>
- OpenTelemetry, *Semantic conventions for GenAI* (repo `semantic-conventions-genai`) — <https://github.com/open-telemetry/semantic-conventions-genai>
- Prometheus, *Using Prometheus as your OpenTelemetry backend* — <https://github.com/prometheus/docs/blob/main/docs/guides/opentelemetry.md>
- Prometheus, *Histograms and summaries* — <https://github.com/prometheus/docs/blob/main/docs/practices/histograms.md>
- Grafana Mimir, *Configure native histograms* — <https://github.com/grafana/mimir/blob/main/docs/sources/mimir/configure/configure-native-histograms-ingestion.md>
- Beyer et al., *Site Reliability Engineering*, cap. 6 — <https://sre.google/sre-book/monitoring-distributed-systems/>

## Siguiente
`10_grafana`: llevarás estas métricas a **dashboards como código**, con variables, paneles de trazas/logs/métricas, navegación entre señales (trace → logs → metrics) y alertas aprovisionadas.
"""

if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    (COURSE / MOD / "README.md").write_text(README, encoding="utf-8")
    build_dashboard()
    build_lesson()
    build_project()
