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
FAST_DEV_RUN = True   # True: tráfico en vivo corto (~75 s) y pocos tickets. False: 4 min de tráfico y más tickets
'''


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
axes[0].set_xlim(0, 16); axes[0].set_xlabel("latencia del agente (s)"); axes[0].set_ylabel("fracción acumulada"); axes[0].set_title("Los límites de bucket deben caer donde está la masa"); axes[0].legend(loc="lower right", fontsize=8)
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
    nb.save(out)  # <<END>>


if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    build_lesson()
