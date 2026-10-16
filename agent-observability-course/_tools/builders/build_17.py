"""Genera el módulo 17_profiling_pyroscope: README, lección, proyecto, dashboard 17 y datos pregrabados.

Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_17.py            # notebooks + README + dashboard
    python agent-observability-course/_tools/builders/build_17.py --record   # regenera recorded/capture_seed42.json.gz (necesita Pyroscope en :4040)
"""
from __future__ import annotations

import gzip
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "17_profiling_pyroscope"
RECORDED = COURSE / MOD / "recorded" / "capture_seed42.json.gz"


# =====================================================================================================================
# Datos pregrabados (modo degradado): medidos con el código de supportops.profiling
# =====================================================================================================================
def record() -> None:
    import statistics as S
    import time

    sys.path.insert(0, str(COURSE))
    import supportops.profiling as P

    out: dict = {"meta": {"seed": 42, "n_tickets": 100, "hz": 300, "python": sys.version.split()[0], "note": "medido con supportops.profiling (mock, semilla 42)"}}
    for variant in ("slow", "fast"):
        p = P.SamplingProfiler(hz=300, mode="cpu")
        s = P.run_workload(variant, n=100, profiler=p)
        out[variant] = {"folded": P.folded_text(p.stacks()), "ms_per_ticket": s.ms_per_ticket, "cpu_s": s.cpu_s, "stage_s": s.stage_s,
                        "per_ticket": [[r.n_llm_calls, ms] for r, ms in zip(s.results, s.per_ticket_cpu_ms)], "samples": p.total,
                        "calls": s.calls}
        if variant == "fast":       # la versión rápida gasta tan poca CPU que 100 tickets dan ~15 muestras: una ejecución larga para el flamegraph
            p2 = P.SamplingProfiler(hz=300, mode="cpu")
            P.run_workload("fast", n=800, profiler=p2)
            out["fast"]["folded_big"] = P.folded_text(p2.stacks())
            out["fast"]["samples_big"] = p2.total
    gil = []
    for si in (0.005, 0.0005):
        sys.setswitchinterval(si)
        for hz in (100, 200, 400, 1000):
            p = P.SamplingProfiler(hz=hz, mode="wall")
            P.run_workload("slow", n=30, profiler=p)
            gil.append({"switch_ms": si * 1000, "hz": hz, "effective_hz": p.total / p.duration_s})
    sys.setswitchinterval(0.005)
    out["gil"] = gil
    base = [P.run_workload("slow", n=60).cpu_s for _ in range(3)]
    own = []
    for _ in range(3):
        p = P.SamplingProfiler(hz=100, mode="cpu")
        own.append(P.run_workload("slow", n=60, profiler=p).cpu_s)
    ovh = {"base_cpu_s": S.median(base), "own_100hz_cpu_s": S.median(own)}
    try:
        import pyroscope
        c = P.PyroscopeClient()
        if c.ready():
            pyroscope.configure(application_name="m17-record", server_address="http://localhost:4040", sample_rate=100, upload_interval=5,
                                tags={"variant": "slow"})
            ovh["sdk_100hz_cpu_s"] = S.median([P.run_workload("slow", n=60).cpu_s for _ in range(3)])
            pyroscope.shutdown()
            # perfiles reales en Pyroscope (SDK) y lectura de vuelta
            for variant in ("slow", "fast"):
                pyroscope.configure(application_name="m17-record2", server_address="http://localhost:4040", sample_rate=100, upload_interval=5,
                                    tags={"variant": variant})
                P.run_workload(variant, n=100)
                time.sleep(12)
                pyroscope.shutdown()
            out["pyroscope"] = {v: P.folded_text(c.stacks('{service_name="m17-record2",variant="%s"}' % v)) for v in ("slow", "fast")}
    except Exception as e:  # noqa: BLE001
        print("sin Pyroscope:", e)
    out["overhead"] = ovh
    RECORDED.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(RECORDED, "wt", encoding="utf-8") as f:
        json.dump(out, f)
    print("OK", RECORDED, RECORDED.stat().st_size, "bytes")


# =====================================================================================================================
# Dashboard
# =====================================================================================================================
def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import lint
    from supportops.profiling import profiling_dashboard
    d = profiling_dashboard()
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "17-profiling.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
# Celdas comunes
# =====================================================================================================================
SETUP_17 = '''
import importlib.util, subprocess
if importlib.util.find_spec("pyroscope") is None:       # SDK oficial de Python (pyroscope-io) y su integración con OpenTelemetry
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyroscope-io", "pyroscope-otel"], check=False)
'''

IMPORTS_17 = '''
import collections, gzip, inspect, json, math, time
from IPython.display import Markdown, display
from supportops import profiling as P
from supportops.profiling import PyroscopeClient, SamplingProfiler, run_workload
STACK = check_stack(["pyroscope"])                       # Pyroscope es lo único que NECESITA este módulo; Tempo/Collector solo para la sección de trazas
PYRO = PyroscopeClient()
PYRO_UP = PYRO.ready()
RUN = str(int(time.time()))                               # etiqueta única por ejecución: así el notebook no mezcla perfiles de ejecuciones anteriores
HAVE_SDK = P.have_pyroscope_sdk()
REC = P.load_recorded(str(ROOT / "17_profiling_pyroscope" / "recorded" / "capture_seed42.json.gz"))   # modo degradado: medido con este mismo código
N = 60 if FAST_DEV_RUN else 150                          # tickets por experimento (cada ejecución «lenta» cuesta ≈ 38 ms de CPU por ticket)
print(f"Pyroscope en vivo: {PYRO_UP} · SDK pyroscope-io: {HAVE_SDK} · tickets por experimento: {N}")
'''


def mdj(head: str, *items: str) -> str:
    """Markdown = cabecera (con sangría de código) + bloques <details> sin sangría."""
    import textwrap
    return textwrap.dedent(head).strip("\n") + "\n\n" + "\n\n".join(items)


def build_lesson() -> None:
    nb, out = nb_for(MOD, "17_profiling_pyroscope.ipynb", "Módulo 17 · Profiling continuo con Pyroscope")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 17 · Profiling continuo: el cuarto pilar, de «el span es lento» a «esta línea gasta la CPU»

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 4 h 30 min (ruta núcleo ≈ 3 h: secciones 1-3, 6-8 y 10) |
    | **Servicios de Compose** | `profiling` (Pyroscope). Para la sección 9 (traza ↔ perfil) además `core`: `docker compose --profile core --profile profiling up -d` |
    | **RAM aproximada** | Pyroscope ≈ 0,06 GB en reposo (arranca en ≈ 60-90 s); con `core` ≈ 0,5 GB |
    | **Modo sin Docker** | Las secciones 1-6 (muestreador a mano, pprof, flamegraphs, GIL, CPU vs wall) y los experimentos de CPU corren en cualquier sitio (Colab incluido). Lo que necesita Pyroscope tiene datos pregrabados |
    | **Prerrequisitos** | Módulos 03 (spans), 07 (Tempo), 09 (cardinalidad) y 16 (SLOs) |

    > 🧭 **Ruta núcleo vs ampliación.** Núcleo: intuición, flamegraph a mano, muestreador a mano, Pyroscope, caza del cuello de botella y arreglo (§1-3, §6-8). Ampliación: pprof por dentro (§5), GIL (§4), traza↔perfil con OTel (§9), coste del profiling continuo (§10).
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar el módulo serás capaz de:

    1. **Explicar** qué pregunta responde el perfil que no responden trazas, métricas ni logs, y **decidir** cuándo abrir un flamegraph.
    2. **Construir** un flamegraph a mano desde pilas plegadas («folded stacks») y **leerlo** distinguiendo tiempo propio (*self*) de inclusivo (*total*).
    3. **Implementar** un perfilador por muestreo en Python puro, medir su sesgo (GIL) y su sobrecarga, y compararlo con el SDK real.
    4. **Codificar y decodificar** un perfil en formato **pprof** (protobuf) y empujarlo a **Pyroscope 2.x** (Connect-RPC, `/ingest` y SDK `pyroscope-io`).
    5. **Encontrar** con perfiles el cuello de botella de CPU de SupportOps, **predecir** la ganancia con la ley de Amdahl y **verificarla** con un perfil diferencial.
    6. **Correlacionar** traza y perfil con `span_id` (`PyroscopeSpanProcessor`, `tracesToProfiles` en Grafana) y saltar de un span lento a su flamegraph.
    7. **Dimensionar** el coste del profiling continuo (sobrecarga, ingesta, retención) y diseñar etiquetas sin tormentas de cardinalidad.
    """)

    md(mdj("""
    ## 🔁 Conexión con módulos anteriores

    Antes de empezar, intenta responder (despliega para comprobar):
    """,
           details("1. (Módulo 02/07) Una traza de SupportOps muestra `execute_tool search_kb` con 400 ms y nada dentro. ¿Qué pilar te dice *por qué* tarda?",
                   "Ninguno de los tres clásicos: la traza dice **dónde** (qué span), las métricas **cuánto** y los logs **qué pasó**. Para saber **qué código** del servicio gasta ese tiempo hace falta un perfil (este módulo)."),
           details("2. (Módulo 08) ¿Cómo se correlacionaban logs y trazas? ¿Qué identificador compartían?",
                   "Con `trace_id`/`span_id` en cada log (structured metadata en Loki). Hoy repetimos el truco: el **`span_id` viaja también en cada muestra del perfil**."),
           details("3. (Módulo 09) ¿Por qué `ticket_id` no puede ser una etiqueta de métrica y qué implica para las etiquetas de un perfil?",
                   "Cada combinación de etiquetas es una serie nueva (cardinalidad). En perfiles pasa igual con las etiquetas de servicio: `service_name`, `version`, `region` sí; ids de petición no. El `span_id` es la excepción que Pyroscope trata aparte (§9).")))

    code(boot("viz,otel"))
    code(SETUP_17 + IMPORTS + IMPORTS_17)

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ## 1 · Intuición: la pregunta que le faltaba a la observabilidad

    Piensa en una alerta de SupportOps: *«el p95 de `invoke_agent` subió de 1,2 s a 1,9 s»*. Las métricas te dieron el **síntoma**; la traza te dice que el tiempo se va en un hijo; pero cuando el hijo es **tu propio código**
    (serializar el historial, parsear la salida de una herramienta, calcular un embedding), el span es una caja negra.

    | Pilar | Pregunta que responde | Granularidad | Analogía |
    |---|---|---|---|
    | Métricas | ¿cuánto y con qué tendencia? | agregada | cuadro de mandos del coche |
    | Trazas | ¿en qué paso de ESTA petición? | por petición | recibo detallado |
    | Logs | ¿qué ocurrió exactamente? | por evento | diario de a bordo |
    | **Perfiles** | **¿qué línea de código consume el recurso?** | por función, agregada en el tiempo | `cProfile`/PyTorch profiler, pero **siempre encendido en producción** |

    > 💡 **Intuición (ML).** En entrenamiento usas el *profiler* de PyTorch para ver qué kernel domina la iteración. El profiling continuo es lo mismo, pero en **producción, con tráfico real y sin que nadie lo active**: el cuello de botella real
    > rara vez es el que imaginabas en el portátil.
    """)

    code('''
fig, ax = viz.canvas(11, 4.3, xlim=(0, 110), ylim=(0, 43))
cols = [("Métricas", "¿cuánto?", viz.PALETTE["metrics"], 4), ("Trazas", "¿en qué paso?", viz.PALETTE["traces"], 30), ("Logs", "¿qué ocurrió?", viz.PALETTE["logs"], 56), ("Perfiles", "¿QUÉ LÍNEA\\ngasta CPU?", viz.PALETTE["profiles"], 82)]
bx = {}
for name, q, c, x in cols:
    bx[name] = viz.box(ax, x, 22, 22, 13, f"{name}\\n{q}", c, fontsize=10, bold=True)
ax.text(55, 40.5, "Los cuatro pilares y la pregunta de cada uno", ha="center", fontsize=12, fontweight="bold")
steps_y = 9
for x, txt, col in ((15, "1) alerta SLO:\\np95 de invoke_agent ↑", viz.PALETTE["metrics"]), (41, "2) traza lenta: el span\\n`execute_tool` no tiene hijos", viz.PALETTE["traces"]), (93, "3) flamegraph de ESE span:\\n`scan_pii_slow` = 68 % de la CPU", viz.PALETTE["profiles"])):
    ax.text(x, steps_y, txt, ha="center", va="center", fontsize=9, color=col)
viz.arrow(ax, (27, steps_y), (31, steps_y), "", viz.PALETTE["neutral"])
viz.arrow(ax, (53, steps_y), (77, steps_y), "", viz.PALETTE["neutral"])
ax.text(65, steps_y + 3, "span_id", ha="center", fontsize=9, color=viz.PALETTE["neutral"])
for name, _, c, x in cols:
    if name != "Logs":
        viz.arrow(ax, (x + 11, 21.5), (x + 11, 13.5), "", c)
plt.show()
''')
    md(observe("""
    - El perfil es la **última pregunta** de la cadena de diagnóstico: alerta (métrica) → traza (qué paso) → perfil (qué código). Por eso lo conectamos con `span_id`.
    - Un perfil no sustituye a los otros tres: **no sabe de peticiones** (es una agregación estadística), por eso solo con el `span_id` puedes bajar a una petición concreta.
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ## 2 · Teoría: perfilar es estimar con muestras

    **Dos familias de perfiladores.**

    - **Instrumentación / determinista** (`cProfile`, `sys.setprofile`): engancha cada llamada/retorno. Cuenta exacto, pero añade una sobrecarga *por llamada* (a menudo ×2-×10) y **distorsiona** lo que mide: inaceptable en producción.
    - **Muestreo / estadístico** (py-spy, `perf`, async-profiler, Pyroscope): cada `1/f` segundos mira *dónde está* el programa (su pila de llamadas) y lo apunta. La sobrecarga depende de `f`, no de cuántas funciones se llaman → **se puede dejar encendido siempre**.

    📐 **Matemáticas del muestreo.** Si la función `g` ocupa una fracción verdadera $p$ del tiempo y tomas $N$ muestras independientes, el número de muestras en `g` es binomial y la estimación $\\hat p = k/N$ tiene

    $$\\mathrm{SE}(\\hat p)=\\sqrt{\\frac{p(1-p)}{N}}\\qquad\\text{IC al 95 \\%}\\approx \\hat p\\pm 1{,}96\\,\\mathrm{SE}$$

    ($N$ = nº de muestras; $p$ = fracción real de tiempo; $\\hat p$ = estimación). Con $f=100$ Hz durante 1 s, $N=100$ y si $p=0{,}5$ el error es ±10 puntos: **un perfil corto engaña, uno agregado de miles de muestras no**. De ahí el «continuo»:
    agregar perfiles de muchas réplicas y minutos.
    """)

    code('''
rng = np.random.default_rng(SEED)
p_true = 0.68
Ns = np.unique(np.logspace(1, 4, 24).astype(int))
fig, ax = plt.subplots(figsize=(9, 3.8))
for n in Ns:
    est = rng.binomial(n, p_true, size=40) / n
    ax.scatter([n] * 40, est, s=7, color=viz.PALETTE["profiles"], alpha=0.35)
se = np.sqrt(p_true * (1 - p_true) / Ns)
ax.plot(Ns, p_true + 1.96 * se, color=viz.PALETTE["error"], lw=1.6, label="IC 95 % teórico")
ax.plot(Ns, p_true - 1.96 * se, color=viz.PALETTE["error"], lw=1.6)
ax.axhline(p_true, color=viz.PALETTE["dark"], ls="--", lw=1, label="fracción real p = 0,68")
ax.set_xscale("log"); ax.set_xlabel("muestras N (a 100 Hz: N/100 segundos)"); ax.set_ylabel("estimación de la fracción de CPU")
ax.set_title("El error de un perfil cae como 1/√N"); ax.legend(); plt.show()
print(f"N=100 → ±{1.96*np.sqrt(p_true*(1-p_true)/100):.3f} · N=1000 → ±{1.96*np.sqrt(p_true*(1-p_true)/1000):.3f} · N=10000 → ±{1.96*np.sqrt(p_true*(1-p_true)/10000):.3f}")
''')
    md(observe("""
    - Cada punto es un «perfil» simulado con N muestras: la nube se estrecha **lentamente** (raíz de N). Pasar de 100 a 10 000 muestras reduce el error ×10, no ×100.
    - Conclusión práctica: para decidir «¿es `scan_pii` el 68 % o el 55 %?» necesitas del orden de 1 000 muestras; para «¿está por encima del 5 %?» te bastan 100.
    """))

    md("""
    **Tipos de perfil.** El *recurso* que se muestrea cambia la pregunta:

    | Tipo (ID en Pyroscope) | Qué mide | Cuándo |
    |---|---|---|
    | `process_cpu:cpu:nanoseconds:cpu:nanoseconds` | tiempo **en CPU** | coste, throughput, «¿quién quema cores?» |
    | *wall* (reloj de pared) | tiempo transcurrido, incluida la espera | latencia, I/O, bloqueos |
    | `memory:alloc_space:bytes`, `alloc_objects`, `inuse_space` | asignaciones / memoria viva | fugas, presión del GC |
    | `goroutines`, `mutex:*`, `block:*` | concurrencia (Go) | contención |

    Pyroscope almacena estos tipos como series con **etiquetas** (`service_name`, `version`, `region`…) igual que Prometheus: se filtra con selectores `{service_name="supportops-agent", variant="slow"}`.
    """)

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ## 3 · A mano (1): pilas plegadas y flamegraph

    Un perfilador produce **pilas** («`main;handle;serialize;dumps`») con un contador. El formato *folded* de Brendan Gregg es una línea por pila: `pila;separada;por;puntos N`. Con eso se dibuja un flamegraph:
    **ancho = muestras de ese nodo**, **eje vertical = profundidad** (quien llama debajo, quien es llamado encima); el orden horizontal es alfabético y **no** es temporal.
    """)

    code('''
tiny = P.parse_folded("""main;handle;parse 30
main;handle;serialize;dumps 45
main;handle;serialize;encode 15
main;log 10""")
rows = P.flame_rows(tiny)
tab = pd.DataFrame([{"función": r.name, "profundidad": r.depth, "total (inclusivo)": r.width, "self (propio)": r.self_n} for r in rows if r.name != "all"])
display(tab)
fig, axs = plt.subplots(1, 2, figsize=(12, 3.2))
P.plot_flamegraph(tiny, axs[0], "Flamegraph (raíz abajo)", min_frac=0, short=False)
P.plot_flamegraph(tiny, axs[1], "Icicle (raíz arriba)", min_frac=0, short=False, icicle=True)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - `serialize` es ancho porque *contiene* a `dumps` y `encode` (total = 60), pero su **self es 0**: no hay nada que optimizar «en `serialize`». El tiempo propio está en `dumps` (45).
    - Regla de lectura: busca **mesetas anchas arriba** (funciones hoja con mucho *self*). Una base ancha (`main`, `handle`) solo dice «todo pasa por aquí».
    - `total` de una función = suma de las muestras de sus pilas; `self` = muestras donde ella es la hoja.
    """))

    md("""
    ### 3.1 · El agente de laboratorio: la fontanería de SupportOps con CPU real

    Las latencias del LLM de SupportOps son **simuladas** (no consumen CPU). Pero un agente real dedica CPU a lo que rodea al modelo: **serializar el contexto** para el proveedor, **escanear PII** antes de enviarlo, **contar tokens** y **reordenar resultados con embeddings**.
    `HotPathInstrumentor` implementa esas cuatro etapas en versión *ingenua* (`slow`) y corregida (`fast`). Es código «de verdad» (Python puro): lo que perfilemos es CPU real de tu máquina. Con ratios, no con milisegundos absolutos, las conclusiones son reproducibles.
    """)
    code('''
print(inspect.getsource(P.scan_pii_slow)[:900], "...\\n")
print(inspect.getsource(P.HotPathInstrumentor.llm_call))
base = run_workload("slow", n=N)                      # semilla 42, mock: mismos tickets cada vez
print(f"slow: {base.ms_per_ticket:.1f} ms de CPU por ticket · {base.calls['llm_prepare']} llamadas al LLM preparadas · {base.calls.get('rerank', 0)} búsquedas con rerank")
''')

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ## 4 · A mano (2): un perfilador por muestreo en 40 líneas

    `SamplingProfiler` (en `supportops.profiling`) hace exactamente esto: un hilo despierta cada `1/hz` s, llama a `sys._current_frames()` (la pila de cada hilo), recorre `f_back` hasta la raíz y suma 1 a esa pila.
    Con `mode="cpu"` solo cuenta si el reloj de CPU del hilo avanzó (descarta esperas).
    """)
    code('''
print(inspect.getsource(SamplingProfiler._run))
''')
    code('''
prof = SamplingProfiler(hz=300, mode="cpu")
run_slow = run_workload("slow", n=N, profiler=prof)
st_hand = prof.stacks()
print(f"{prof.total} muestras en {prof.duration_s:.1f} s ({prof.total / prof.duration_s:.0f} muestras/s efectivas, pedidas 300) · CPU medida por el SO: {run_slow.cpu_s:.2f} s")
top = pd.DataFrame([{"función": fn.split(".")[-1], "self": n, "self %": 100 * n / prof.total} for fn, n in P.self_time(st_hand).most_common(8)])
display(top.round(1))
P.plot_flamegraph(st_hand, root="run_workload", title="Flamegraph de SupportOps v-lenta (perfilador a mano, CPU)", highlight=["scan_pii"])
plt.show()
''')
    md(observe("""
    - Una función domina con diferencia: `scan_pii_slow` (el escáner de PII que recorre el texto carácter a carácter), seguida de `count_tokens_slow`. **No** son la serialización ni los embeddings, que es lo que la mayoría adivina.
    - El ancho de la raíz son todas las muestras; cada pila contiene `run_workload → run → llm_call → _prepare_slow → …`: la ruta completa desde el bucle del agente hasta la hoja.
    - Si repites la celda, los porcentajes varían un poco (muestreo) pero el orden no. Eso es lo que significa «estadístico».
    """))

    md("""
    ### 4.1 · Sesgo de un muestreador escrito en Python: el GIL

    ¿Por qué pedimos 300 Hz y recibimos menos? Nuestro hilo muestreador es Python: **necesita el GIL para ejecutarse**. El hilo perfilado lo suelta cada `sys.getswitchinterval()` (5 ms por defecto) o al bloquear. Dos consecuencias: la tasa efectiva está limitada (~200 Hz) y
    **las muestras solo ocurren en puntos donde el intérprete cede el GIL**, lo que puede sesgar qué se ve. Los perfiladores de producción (py-spy, el SDK `pyroscope-io`) leen la memoria del intérprete **desde fuera** (otro hilo nativo/Rust que no necesita el GIL).
    """)
    code('''
rows = []
for si in (0.005, 0.0005):
    sys.setswitchinterval(si)
    for hz in ((100, 400, 1000) if FAST_DEV_RUN else (100, 200, 400, 1000)):
        p = SamplingProfiler(hz=hz, mode="wall"); run_workload("slow", n=25, profiler=p)
        rows.append({"switchinterval_ms": si * 1000, "hz pedidos": hz, "hz efectivos": p.total / p.duration_s})
sys.setswitchinterval(0.005)                            # restaura el valor por defecto
gil = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(7, 3.6))
for si, g in gil.groupby("switchinterval_ms"):
    ax.plot(g["hz pedidos"], g["hz efectivos"], "o-", label=f"switchinterval = {si:g} ms", lw=2)
ax.plot([100, 1000], [100, 1000], "--", color=viz.PALETTE["neutral"], label="ideal")
ax.set_xlabel("frecuencia pedida (Hz)"); ax.set_ylabel("frecuencia efectiva (Hz)"); ax.set_title("El GIL limita a un muestreador escrito en Python"); ax.legend(); plt.show()
''')
    md(observe("""
    - Con el *switch interval* por defecto (5 ms) la curva se **aplana ≈ 250-300 Hz**; bajándolo a 0,5 ms el muestreador alcanza lo pedido, pero a costa de cambios de contexto (¡cambiar el intervalo modifica el programa medido!).
    - Por eso el SDK real usa un hilo **fuera del GIL**: no distorsiona el intervalo de conmutación y puede muestrear a 100 Hz de forma constante.
    """))

    md("""
    ### 4.2 · CPU frente a *wall*: lo que un agente casi nunca hace es calcular

    Un agente pasa la mayor parte del tiempo **esperando** al LLM y a las herramientas. Un perfil de CPU no ve la espera; un perfil *wall* sí. Simulemos un paso típico: 250 ms de espera de red + el trabajo de CPU del escáner.
    """)
    code('''
def llm_network_wait():
    time.sleep(0.25)                                  # espera de red del proveedor LLM: 0 % de CPU

def agent_step():
    llm_network_wait()
    P.scan_pii_slow(P.policy_text() * 24)             # trabajo de CPU real (≈ 60 ms)

w, c = SamplingProfiler(hz=500, mode="wall"), SamplingProfiler(hz=500, mode="cpu")
with w, c:
    for _ in range(4):
        agent_step()
fig, axs = plt.subplots(1, 2, figsize=(11, 3.4), sharex=False)
for ax, prf, ttl, col in ((axs[0], w, "WALL (reloj de pared)", viz.PALETTE["traces"]), (axs[1], c, "CPU", viz.PALETTE["profiles"])):
    top = P.self_time(prf.stacks()).most_common(4)
    ax.barh([fn.split(".")[-1] for fn, _ in top][::-1], [100 * n / prf.total for _, n in top][::-1], color=col)
    ax.set_title(f"{ttl} · {prf.total} muestras"); ax.set_xlabel("% de muestras (self)")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El perfil **wall** dice «más del 90 % del tiempo en `time.sleep`»: es la **latencia** (lo que sufre el usuario). El perfil **CPU** dice «casi todo en `scan_pii_slow`»: es el **coste** (cores que pagas). (Salen pocas muestras de CPU porque nuestro muestreador en Python vive bajo el GIL, §4.1: otra razón para usar el SDK nativo.)
    - Para optimizar latencia de un agente mira el wall y las trazas (la espera es del proveedor); para optimizar **coste e infraestructura** (cuántas réplicas necesitas) mira CPU.
    """))

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ## 5 · pprof por dentro: el idioma común de los perfiladores

    **pprof** (`perftools.profiles.Profile`, un mensaje *protobuf* creado por Google) es el formato que entienden Go, Pyroscope, Parca y las herramientas de Google. Es compacto porque **deduplica**: una tabla de cadenas, una tabla de funciones, una de ubicaciones
    y las muestras solo guardan *ids*. Lo escribimos a mano (sin librería de protobuf) con `encode_pprof` y lo leemos con `decode_pprof`.

    | Campo (nº) | Contenido |
    |---|---|
    | `sample_type` (1) | qué mide cada valor: (`cpu`, `nanoseconds`) |
    | `sample` (2) | una pila: `location_id[]` **de la hoja a la raíz** + `value[]` + `label[]` (etiquetas, p. ej. `span_id`) |
    | `location` (4) / `function` (5) | ubicación → función → nombre (índice en la tabla de cadenas) |
    | `string_table` (6) | todas las cadenas, la 0 es `""` |
    | `time_nanos` (9), `duration_nanos` (10), `period_type` (11), `period` (12) | cuándo, cuánto dura y cada cuántos ns se muestrea |
    """)
    code('''
rows = [(("main", "handle", "parse"), 30, {"span_id": "ab12"}), (("main", "handle", "serialize", "dumps"), 45, {}), (("main", "log"), 10, {})]
raw = P.encode_pprof(rows, period_ns=10_000_000, duration_ns=int(1e9), gzip_it=False)
print(f"{len(rows)} pilas → {len(raw)} bytes de protobuf. Primeros bytes: {raw[:48].hex(' ')}")
print("  08 = campo 1 (sample_type) varint · 12 = campo 2 (sample) longitud-delimitado · ... (cada byte de clave = (campo << 3) | tipo_de_cable)")
dec = P.decode_pprof(raw)
print(dec["sample_type"], "periodo", dec["period"], "ns")
for stack, vals, labels in dec["samples"]:
    print(f"  {';'.join(stack):<28} valor={vals[0]:>3} etiquetas={labels}")
real = prof.to_pprof()
folded = P.folded_text(st_hand)
print(f"\\nPerfil real: {prof.total} muestras · folded {len(folded.encode())} B · pprof+gzip {len(real)} B · ids de función únicos: {len({fn for s in st_hand for fn in s})}")
assert {(s, v[0]) for s, v, _ in P.decode_pprof(real)["samples"]} == {(s, n * prof.sample_period_ns()) for s, n in st_hand.items()}
''')
    md(observe("""
    - La ida y vuelta es exacta: lo que codificamos es lo que decodificamos (la aserción final lo comprueba con el perfil real).
    - El pprof dedup+gzip suele ocupar **del mismo orden o menos** que el texto *folded* y además transporta etiquetas por muestra, que es justo lo que necesitamos para `span_id`.
    - Un SDK de producción hace esto cada `upload_interval` segundos (10 s por defecto en `pyroscope-io`): un `POST` de unos KB por proceso.
    """))

    # ------------------------------------------------------------------------------------------------ 6
    md("""
    ## 6 · Pyroscope 2.x: dónde viven los perfiles

    **Grafana Pyroscope** es el backend de perfiles del stack LGTM+P. Desde la **2.0** la arquitectura por defecto («v2») escribe los perfiles **directamente en almacenamiento de objetos**, sin ingesters en memoria ni discos locales; el camino de escritura enruta por servicio, unos
    *compaction workers* fusionan segmentos pequeños en bloques grandes y el camino de lectura consulta el almacenamiento de objetos (fuente: README de `grafana/pyroscope` y su guía de arquitectura v2). En el laboratorio es un solo contenedor `grafana/pyroscope:2.1.2`
    (modo monolítico) y los mensajes de `/ready` que mediste en el módulo 00 («Metastore not ready», «Segment Writer not ready») son esos componentes arrancando por orden.
    """)
    code('''
fig, ax = viz.canvas(11.5, 4.6, xlim=(0, 115), ylim=(0, 46))
sdk = viz.box(ax, 2, 28, 22, 12, "App Python\\n+ SDK pyroscope-io\\n(hilo nativo, 100 Hz)", viz.PALETTE["profiles"], fontsize=9)
alloy = viz.box(ax, 2, 6, 22, 12, "Grafana Alloy\\n(eBPF / pull)\\nGo, Java, Rust…", viz.PALETTE["neutral"], fontsize=9)
w = viz.box(ax, 36, 17, 20, 14, "Camino de escritura\\nenruta por servicio\\n(segment writer)", viz.PALETTE["profiles"], fontsize=9)
st = viz.box(ax, 66, 28, 20, 12, "Almacenamiento de\\nobjetos (bloques)\\n+ metastore", viz.PALETTE["metrics"], fontsize=9)
cw = viz.box(ax, 66, 6, 20, 12, "compaction workers\\n(fusionan segmentos)", viz.PALETTE["neutral"], fontsize=9)
q = viz.box(ax, 92, 17, 21, 14, "Camino de lectura\\nquery-frontend\\nflamegraph / series", viz.PALETTE["traces"], fontsize=9)
viz.arrow(ax, viz.right(sdk), viz.left(w), "push", viz.PALETTE["profiles"], rad=-0.15)
viz.arrow(ax, viz.right(alloy), viz.left(w), "", viz.PALETTE["neutral"], rad=0.15)
viz.arrow(ax, viz.right(w), viz.left(st), "segmentos", viz.PALETTE["metrics"], rad=-0.1)
viz.arrow(ax, viz.bottom(st), viz.top(cw), "", viz.PALETTE["neutral"])
viz.arrow(ax, viz.left(q), viz.right(st), "lee", viz.PALETTE["traces"], rad=0.2)
ax.text(57, 43, "Pyroscope 2.x: escribe directo a objetos, sin ingesters", ha="center", fontsize=11, fontweight="bold")
ax.text(103, 11, "Grafana\\n(datasource pyroscope,\\npanel flamegraph)", ha="center", fontsize=9, color=viz.PALETTE["traces"])
plt.show()
''')
    md(observe("""
    - El **cliente es tonto y barato**: muestrea y empuja pprof cada 10 s. Toda la inteligencia (agregación, compactación, consulta) está en el servidor, y puede escalar sin tocar las apps.
    - La compactación hace que consultar «los últimos 7 días de CPU de `supportops-agent`» no lea miles de perfiles de 10 s, sino pocos bloques grandes.
    """))

    md("""
    ### 6.1 · Empujar un perfil: tres vías, la misma idea

    1. **Connect-RPC** `push.v1.PusherService/Push` con JSON: `labels` (incluye `__name__=process_cpu`) + `rawProfile` (pprof en base64).
    2. **Ingesta compatible** `POST /ingest?name=app{k=v}&from=&until=&format=pprof`: el cuerpo es el pprof. *(Medido en 2.1.2: un formulario multipart devuelve 422.)*
    3. **SDK** `pyroscope-io` (muestreo por py-spy en Rust + subida periódica): `pyroscope.configure(application_name=..., server_address=..., tags=...)`.

    Las dos primeras las hacemos con el pprof que acabamos de fabricar a mano.
    """)
    code('''
if PYRO_UP:
    tag = f"m17-hand-{int(time.time())}"
    PYRO.push_connect({"service_name": tag, "variant": "slow", "origen": "perfilador-a-mano"}, prof.to_pprof())
    got = PYRO.wait_for('{service_name="%s"}' % tag, timeout_s=90)
    st_pyro = PYRO.stacks('{service_name="%s"}' % tag)
    sel_tag = '{service_name="%s"}' % tag
    print(f"Pyroscope devolvió {got / 1e9:.2f} s de CPU (enviamos {prof.total * prof.sample_period_ns() / 1e9:.2f} s) · etiquetas: {PYRO.label_names(sel_tag)}")
    print("¿Mismo top-3 que nuestro perfilador?", [fn.split('.')[-1] for fn, _ in P.self_time(st_pyro).most_common(3)] == [fn.split('.')[-1] for fn, _ in P.self_time(st_hand).most_common(3)])
else:
    print("Pyroscope no está arriba → modo degradado.", STACK.command if hasattr(STACK, "command") else "")
    print("Comando:  cd stack && docker compose --profile profiling up -d   (espera ≈ 60-90 s a /ready)")
''')

    md("""
    ### 6.2 · El SDK real: `pyroscope-io`

    Verificado contra `pyroscope-io 1.3.0` (PyPI): `pyroscope.configure(application_name, server_address, sample_rate=100, tags, upload_interval=10, oncpu=True, gil_only=True, …)`; `pyroscope.tag_wrapper({...})` etiqueta lo que ocurre dentro del `with`; `pyroscope.shutdown()` vacía lo pendiente.
    El muestreo (`cpu_implementation=PySpy` por defecto) corre en un hilo nativo y existe un perfilador de pila experimental (`ProfilerImplementation.Stack`). **`oncpu=True`** = perfil de CPU; `False` incluye esperas.
    """)
    code('''
if PYRO_UP and HAVE_SDK:
    import pyroscope
    pyroscope.configure(application_name="supportops-agent", server_address="http://localhost:4040", sample_rate=100,
                        tags={"env": "lab", "variant": "slow", "version": "0.1.0-m17", "run": RUN}, upload_interval=5)
    with pyroscope.tag_wrapper({"tarea": "baseline-lenta"}):
        sdk_run = run_workload("slow", n=N)
    time.sleep(12); pyroscope.shutdown()                 # un upload_interval + margen: lo pendiente sale al apagar
    SEL_SLOW = '{service_name="supportops-agent",variant="slow",run="%s"}' % RUN
    print("CPU total vista por Pyroscope:", PYRO.wait_for(SEL_SLOW, timeout_s=90) / 1e9, "s · CPU medida por el SO en el proceso:", round(sdk_run.cpu_s, 2), "s")
    st_slow = PYRO.stacks(SEL_SLOW)
    print("etiquetas:", PYRO.label_values("tarea", SEL_SLOW), PYRO.label_values("version", SEL_SLOW))
else:
    print("SDK o Pyroscope no disponibles: se usa la captura pregrabada (mismo esquema).")
    st_slow = P.parse_folded(REC.get("pyroscope", {}).get("slow") or REC["slow"]["folded"])
top = pd.DataFrame([{"función": fn.split(".")[-1], "self %": 100 * n / sum(st_slow.values())} for fn, n in P.self_time(st_slow).most_common(6)])
display(top.round(1))
''')
    md(observe("""
    - El total que ve Pyroscope coincide, a pocos %, con la CPU que midió el sistema operativo: el perfil **cuenta CPU de verdad**, no una estimación inventada.
    - Los nombres de función del SDK son *sin módulo* (`scan_pii_slow`), los de nuestro perfilador llevan `modulo.función`: otro motivo para comparar por el final del nombre.
    - Mismo ranking que con el perfilador a mano: dos implementaciones independientes (Python con GIL / Rust fuera del GIL) coinciden en **dónde** está el problema.
    """))

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ## 7 · Caza del cuello de botella de SupportOps

    **Hipótesis a priori** (pregunta a tu equipo, casi nadie acierta): ¿qué etapa cuesta más CPU? ¿serializar el contexto con `json.dumps`? ¿los embeddings? Mide: el perfil dice una cosa y los **cronómetros por etapa** (la verdad de referencia) otra que debe coincidir con él.
    """)
    code('''
st_prof = st_slow if PYRO_UP and HAVE_SDK else st_hand
share_prof = P.stage_shares(st_prof)
share_timer = base.stage_share()
stages = ["pii_scan", "tokens", "serialize", "embed_rerank"]
x = np.arange(len(stages))
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.bar(x - 0.2, [100 * share_prof.get(s, 0) for s in stages], 0.4, color=viz.PALETTE["profiles"], label="perfil (muestreo)")
ax.bar(x + 0.2, [100 * share_timer.get(s, 0) for s in stages], 0.4, color=viz.PALETTE["traces"], label="cronómetros (verdad)")
ax.set_xticks(x); ax.set_xticklabels(stages); ax.set_ylabel("% de la CPU de las 4 etapas"); ax.set_title("El perfil atribuye la CPU como los cronómetros"); ax.legend(); plt.show()
print({s: f"perfil {100*share_prof.get(s,0):.0f} % · cronómetro {100*share_timer.get(s,0):.0f} %" for s in stages}, "· resto del agente (otros):", f"{100*share_prof.get('other',0):.0f} %")
''')
    md(observe("""
    - La etapa **ganadora es el escaneo de PII (≈ 2/3 de la CPU)** y la intuición «serializar JSON» es una de las menores (< 10 %). Optimizar lo equivocado no habría movido la aguja.
    - Las barras del perfil y de los cronómetros coinciden con pocos puntos de diferencia: el muestreo estadístico reproduce la medición exhaustiva **sin instrumentar cada función**.
    - El «resto del agente» (el propio bucle, el mock) es pequeño: la fontanería manda.
    """))

    md("""
    ### 7.1 · El arreglo y la predicción con la ley de Amdahl

    Probamos arreglos de menor a mayor ambición, midiendo cada uno:

    1. **Regex precompilada** en lugar del bucle carácter a carácter (optimizar la *constante*).
    2. Regex + contador de tokens sin bucle interno.
    3. **No repetir trabajo**: el prompt de sistema y los ejemplos son idénticos en cada llamada; se escanean/cuentan **por línea con caché** (`scan_pii_cached`).
    4. La variante `fast` completa: además cachea el JSON por mensaje y los embeddings de los documentos.

    📐 **Amdahl.** Si una parte ocupa una fracción $f$ de la CPU total y la aceleras $s$ veces, el programa se acelera
    $$S=\\frac{1}{(1-f)+f/s}$$
    ($f$ = fracción de CPU de esa parte; $s$ = aceleración local; $S$ = aceleración global). Aunque $s\\to\\infty$, el tope es $1/(1-f)$: arreglar el 67 % como mucho da ×3.
    """)
    code('''
fr = base.cpu_fraction()                                    # fracción de la CPU TOTAL por etapa (cronómetros)
steps = {
    "1· regex (solo escaneo)": (dict(scan_fn=P.scan_pii_fast), fr["pii_scan"]),
    "2· regex + tokens": (dict(scan_fn=P.scan_pii_fast, tokens_fn=P.count_tokens_fast), fr["pii_scan"] + fr["tokens"]),
    "3· caché por línea\\n(escaneo + tokens)": (dict(scan_fn=P.scan_pii_cached, tokens_fn=P.count_tokens_cached), fr["pii_scan"] + fr["tokens"]),
}
pred = {k: P.amdahl_speedup(f, 1e9) for k, (_, f) in steps.items()}
meas = {k: base.cpu_s / run_workload("slow", n=N, **kw).cpu_s for k, (kw, _) in steps.items()}
fast = run_workload("fast", n=N)
meas["4· variante fast\\n(todo cacheado)"] = base.cpu_s / fast.cpu_s
fig, ax = plt.subplots(figsize=(9.5, 4))
names = list(meas)
ax.bar(np.arange(len(names)) - 0.2, [pred.get(k, np.nan) for k in names], 0.4, color=viz.PALETTE["neutral"], label="tope de Amdahl (s → ∞) según la fracción arreglada")
ax.bar(np.arange(len(names)) + 0.2, [meas[k] for k in names], 0.4, color=viz.PALETTE["ok"], label="medido")
ax.set_xticks(range(len(names))); ax.set_xticklabels(names, fontsize=8); ax.set_ylabel("aceleración de CPU (×)"); ax.set_title("Cada arreglo, medido contra el tope de Amdahl"); ax.legend(fontsize=8); plt.show()
print({k.replace("\\n", " "): f"×{v:.1f}" for k, v in meas.items()}, "· tope:", {k.replace("\\n", " "): f"×{v:.1f}" for k, v in pred.items()})
same = ([r.status for r in base.results] == [r.status for r in fast.results], [r.input_tokens for r in base.results] == [r.input_tokens for r in fast.results], base.rerank_order == fast.rerank_order)
print("¿Mismo comportamiento? (estados, tokens, ranking de la KB):", same)
''')
    md(observe("""
    - **Optimizar la constante da poco**: la regex acelera el escáner ≈ 3-4× en solitario y solo ≈ ×2 el total. **Eliminar el trabajo repetido** (caché por línea) lo lleva a ≈ ×4-6 y la variante completa a un orden de magnitud más.
    - Cada barra verde queda **por debajo de su tope de Amdahl**: lo que se arregla suma, lo que queda limita; la última supera los topes anteriores porque ataca *todas* las etapas.
    - **Un arreglo sin verificación de equivalencia no es un arreglo**: la última línea comprueba que estados, tokens y ranking de documentos son idénticos antes y después.
    """))

    md("""
    ### 7.2 · Perfil diferencial: la prueba de que el arreglo funcionó

    Un perfil diferencial compara dos perfiles función a función. Hay que **normalizar**: el perfil rápido tiene muchas menos muestras, así que se compara el reparto (%), y se muestra además la CPU absoluta evitada.
    """)
    code('''
if PYRO_UP and HAVE_SDK:
    pyroscope.configure(application_name="supportops-agent", server_address="http://localhost:4040", sample_rate=100,
                        tags={"env": "lab", "variant": "fast", "version": "0.1.0-m17", "run": RUN}, upload_interval=5)
    run_workload("fast", n=max(N * 6, 300)); time.sleep(12); pyroscope.shutdown()
    SEL_FAST = '{service_name="supportops-agent",variant="fast",run="%s"}' % RUN
    PYRO.wait_for(SEL_FAST, timeout_s=90)
    st_fast = PYRO.stacks(SEL_FAST)
else:
    st_fast = P.parse_folded(REC.get("pyroscope", {}).get("fast") or REC["fast"]["folded_big"])
d = pd.DataFrame(P.diff_self(st_slow, st_fast, top=8))
d["función"] = d["function"].str.split(".").str[-1]
d = d.sort_values("before_pct")
fig, axs = plt.subplots(1, 2, figsize=(12, 3.8), sharey=True)
axs[0].barh(d["función"], d["before_pct"], color=viz.PALETTE["error"], label="antes (slow)"); axs[0].set_title("% de la CPU · antes")
axs[1].barh(d["función"], d["after_pct"], color=viz.PALETTE["ok"], label="después (fast)"); axs[1].set_title("% de la CPU · después")
for a in axs: a.set_xlabel("% de muestras (self)")
plt.tight_layout(); plt.show()
print(f"CPU por ticket: slow {base.ms_per_ticket:.1f} ms → fast {fast.ms_per_ticket:.1f} ms (×{base.ms_per_ticket / max(fast.ms_per_ticket, 1e-9):.0f})")
fig, axs = plt.subplots(1, 2, figsize=(12, 3.4))
P.plot_flamegraph(st_slow, axs[0], "ANTES · slow", highlight=["scan_pii"], root="run_workload"); P.plot_flamegraph(st_fast, axs[1], "DESPUÉS · fast", highlight=["scan_pii"], root="run_workload")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Antes**: una barra enorme (`scan_pii_slow`). **Después**: el reparto se aplana; lo que queda es el propio agente. Si tras un arreglo aparece otra función dominante, **vuelve a perfilar**: el cuello de botella migra.
    - En porcentaje el perfil «después» parece tener más peso en otras funciones, pero en absoluto gastan **menos** CPU: por eso el gráfico se complementa con los ms por ticket.
    - El segundo par de flamegraphs usa el mismo eje de % por lado: el rojo de `scan_pii_slow` desaparece.
    """))

    md("""
    ### 7.3 · El coste crece con los pasos del agente

    La ruta caliente se ejecuta **antes de cada llamada al LLM**. Un ticket que da más vueltas (más herramientas, bucles de herramientas del módulo 13) paga más. Veamos CPU por ticket frente a nº de llamadas al LLM.
    """)
    code('''
fig, ax = plt.subplots(figsize=(8, 3.8))
for res, ms, nm, col in ((base.results, base.per_ticket_cpu_ms, "slow", viz.PALETTE["error"]), (fast.results, fast.per_ticket_cpu_ms[:len(base.results)], "fast", viz.PALETTE["ok"])):
    xs = np.array([r.n_llm_calls for r in res][:len(ms)]) + np.random.default_rng(1).uniform(-0.12, 0.12, len(ms))
    ax.scatter(xs, ms, s=16, alpha=0.6, color=col, label=nm)
nl = np.array([r.n_llm_calls for r in base.results]); cm = np.array(base.per_ticket_cpu_ms)
slope = np.polyfit(nl, cm, 1)
ax.plot([nl.min(), nl.max()], np.polyval(slope, [nl.min(), nl.max()]), color=viz.PALETTE["dark"], lw=1, ls="--")
ax.set_xlabel("llamadas al LLM del ticket"); ax.set_ylabel("CPU por ticket (ms)"); ax.set_title(f"slow: ≈ {slope[0]:.0f} ms de CPU extra por cada llamada al LLM"); ax.legend(); plt.show()
''')
    md(observe("""
    - La CPU de la variante lenta crece **linealmente con las llamadas al LLM** (≈ 14-15 ms por llamada: se vuelve a escanear el prompt entero). Los tickets de 3 llamadas cuestan ≈ 3× los de 1.
    - Un bucle de herramientas (6 pasos máximo) multiplica el coste por 6 *además* del gasto en tokens: el perfil da el segundo euro del coste de un bucle.
    - La variante rápida apenas depende de los pasos (cacheo por mensaje).
    """))

    # ------------------------------------------------------------------------------------------------ 8
    md("""
    ## 8 · Etiquetas: perfiles por versión, tenant o tarea

    Las etiquetas convierten un perfil global en preguntas: *«¿la CPU subió con la versión 0.2?»*, *«¿qué tenant cuesta más?»*. Reglas (las mismas que en métricas):

    - **Sí**: `service_name`, `version`, `env`, `region`, `variant`, `endpoint` de baja cardinalidad, `tenant` si son decenas.
    - **No**: ids de ticket/cliente/traza. Cada combinación crea una serie más.
    - **Excepción controlada**: `span_id`, que Pyroscope guarda fuera del índice normal (§9).
    """)
    code('''
if PYRO_UP:
    sel = '{service_name="supportops-agent"}'
    print("etiquetas indexadas:", [n for n in PYRO.label_names(sel) if not n.startswith("__")])
    print("variant =", PYRO.label_values("variant", sel), "· version =", PYRO.label_values("version", sel))
    print("tipos de perfil disponibles:", [t.split(":")[0] + ":" + t.split(":")[1] for t in PYRO.profile_types()][:6], "…")
else:
    print("(sin Pyroscope) etiquetas del SDK en la captura: service_name, variant, env, version, tarea")
''')

    # ------------------------------------------------------------------------------------------------ 9
    md("""
    ## 9 · Traza ↔ perfil: del span lento a su flamegraph

    El mecanismo, idéntico al de logs↔trazas: **cada muestra del perfil lleva el `span_id` del span raíz que estaba activo en ese hilo**. Cuando abres un span en Tempo, Grafana consulta Pyroscope filtrando por ese `span_id` (el campo `spanSelector` de la API, **no** un `{span_id="…"}` en el selector de etiquetas: lo medimos contra Pyroscope 2.1.2 y devuelve 0 muestras) y te muestra solo la CPU de **esa** petición.

    **A mano (funciona sin Docker).** Un instrumentor de 10 líneas pone la etiqueta durante `agent_run`; nuestro muestreador la guarda con cada muestra.
    """)
    code('''
from supportops import Instrumentor
from contextlib import contextmanager

class SpanTagInstrumentor(Instrumentor):
    """Etiqueta las muestras del perfilador con el id del ticket mientras el agente trabaja en él (equivalente a PyroscopeSpanProcessor, a mano)."""
    def __init__(self, profiler): self.p = profiler
    @contextmanager
    def agent_run(self, ctx):
        self.p.set_tag("ticket", ctx.ticket.ticket_id)
        try:
            yield
        finally:
            self.p.clear_tag("ticket")

pp = SamplingProfiler(hz=300, mode="cpu")
tagged = run_workload("slow", n=40, profiler=pp, extra=[SpanTagInstrumentor(pp)])
by_ticket = pp.tag_values("ticket")
worst, n_worst = by_ticket.most_common(1)[0]
print(f"{len(by_ticket)} tickets con muestras · el más caro: {worst} con {n_worst} muestras ({n_worst / pp.total:.0%} de todo el perfil)")
fig, axs = plt.subplots(1, 2, figsize=(12, 3.3))
P.plot_flamegraph(pp.stacks(), axs[0], "Todos los tickets", highlight=["scan_pii"], root="run_workload")
P.plot_flamegraph(pp.stacks(ticket=worst), axs[1], f"Solo el ticket {worst}", highlight=["scan_pii"], root="run_workload")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Filtrando por la etiqueta pasas del **perfil agregado** al de **una petición**. En el ticket más caro `scan_pii_slow` pesa igual: no es un caso raro, es estructural; si el flamegraph del ticket fuera distinto del global habrías encontrado un **caso particular** (un tool-loop, un prompt enorme).
    - Es exactamente lo que automatiza `PyroscopeSpanProcessor` con el `span_id` real de OTel.
    """))

    md("""
    **Con OpenTelemetry real.** El paquete `pyroscope-otel` (verificado, 1.1.0) aporta `PyroscopeSpanProcessor`: en `on_start` de cada **span raíz** (sin padre o con padre remoto) hace dos cosas:
    pone el atributo `pyroscope.profile.id = <span_id>` en el span y añade al hilo las etiquetas `span_id`, `span_name` y `trace_id` que el SDK adjunta a cada muestra; en `on_end` las quita. En Grafana, el datasource de Tempo se configura con `tracesToProfiles`
    (ya provisionado en `stack/grafana/provisioning/datasources/datasources.yaml`):

    ```yaml
    tracesToProfiles:
      datasourceUid: pyroscope
      profileTypeId: "process_cpu:cpu:nanoseconds:cpu:nanoseconds"
      tags: [{ key: service.name, value: service_name }]
    ```
    Sin `customQuery`: Grafana arma `{service_name="…"}` y, como el span lleva `pyroscope.profile.id`, pide el perfil de **ese** span. (Una consulta personalizada con `span_id="…"` dentro del selector de etiquetas no devuelve nada en Pyroscope 2.1.2. ⚠️ El salto con el botón «Profiles for this span» de la interfaz no se pudo probar en el sandbox del curso; la mitad Pyroscope sí está medida con `SelectMergeSpanProfile`.)
    """)
    code('''
TRACES_OK = PYRO_UP and HAVE_SDK and check_stack(["collector", "tempo"], verbose=False).degraded is False
if TRACES_OK:
    import pyroscope
    from pyroscope.otel import PyroscopeSpanProcessor
    from supportops.telemetry import setup_telemetry, OTelInstrumentor
    tel = setup_telemetry("supportops-agent", mode="otlp", resource_attrs={"deployment.environment.name": "lab"})
    tel.tracer_provider.add_span_processor(PyroscopeSpanProcessor())
    pyroscope.configure(application_name="supportops-agent", server_address="http://localhost:4040", sample_rate=100,
                        tags={"env": "lab", "variant": "slow", "version": "0.1.0-m17", "run": RUN}, upload_interval=5)
    instr = OTelInstrumentor(tel)
    tk = generate_tickets(46, seed=SEED, start_s="live")
    live = run_workload("slow", tickets=tk, n=40, extra=[instr])
    tel.force_flush(); time.sleep(12); pyroscope.shutdown()
    roots = {r["attributes"].get("supportops.ticket.id"): r for r in tel.span_records() if r["name"].startswith("invoke_agent")}
    ids = [r.ticket_id for r in live.results]
    k = int(np.argmax(live.per_ticket_cpu_ms))
    root = roots[ids[k]]
    print(f"ticket más caro: {ids[k]} ({live.per_ticket_cpu_ms[k]:.0f} ms de CPU) · trace_id={root['trace_id']} · span_id={root['span_id']}")
    print("atributo del span:", root["attributes"].get("pyroscope.profile.id"))
    fg = PYRO.span_profile([root["span_id"]], '{service_name="supportops-agent"}')
    st_span = P.flamebearer_to_stacks(fg)
    print("perfil de ESE span:", fg["total"] / 1e6, "ms de CPU · top:", [(fn, n // 10**6) for fn, n in P.self_time(st_span).most_common(3)])
    P.plot_flamegraph(st_span, title=f"Flamegraph (Pyroscope) del span {root['span_id']}", highlight=["scan_pii"], root="run_workload"); plt.show()
else:
    print("Sección en vivo omitida (necesita Pyroscope + core). Levántalos con:  cd stack && docker compose --profile core --profile profiling up -d")
''')
    md(observe("""
    - El `span_id` del span raíz de Tempo es el mismo que devuelve `SelectMergeSpanProfile`: **un identificador, dos pilares**. La CPU del span (decenas de ms) coincide con la medida por ticket.
    - En Grafana: abre la traza en Explore → Tempo, pulsa el span raíz → **«Profiles for this span»** te lleva al flamegraph de Pyroscope con ese `span_id`. El dashboard `17 · Profiling continuo` (uid `profiling`) lista las trazas con `pyroscope.profile.id`.
    - Solo se etiquetan los **spans raíz**: los hijos (`chat`, `execute_tool`) no tienen perfil propio. Si necesitas el perfil de un hijo, tendrías que etiquetar también esos spans (más series).
    """))

    code('''
dash = json.load(open(ROOT / "stack" / "grafana" / "dashboards" / "17-profiling.json"))
print("Dashboard provisionado:", dash["title"], f"(uid {dash['uid']})")
for p_ in dash["panels"]:
    if p_["type"] != "row":
        print(f"  [{p_['type']:<10}] {p_['title']}")
if PYRO_UP and check_stack(["grafana"], verbose=False).degraded is False:
    r = backends.grafana_api("/api/dashboards/uid/profiling")
    print("Grafana lo ha cargado:", bool(r) and r.get("dashboard", {}).get("title"))
''')

    # ------------------------------------------------------------------------------------------------ 10
    md("""
    ## 10 · Coste del profiling continuo: sobrecarga, ingesta y retención

    ¿Cuánto cuesta dejarlo siempre encendido? Dos costes distintos: la **sobrecarga en la aplicación** (CPU del muestreador) y la **ingesta/almacenamiento** en el backend. Medimos el primero con la carga del laboratorio y modelamos el segundo.
    """)
    code('''
ov = REC["overhead"]
labels = ["sin perfilador", "perfilador a mano\\n(100 Hz, Python)", "SDK pyroscope-io\\n(100 Hz)"]
vals = [ov["base_cpu_s"], ov["own_100hz_cpu_s"], ov.get("sdk_100hz_cpu_s", np.nan)]
fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
axs[0].bar(labels, vals, color=[viz.PALETTE["neutral"], viz.PALETTE["profiles"], viz.PALETTE["ok"]])
axs[0].set_ylabel("CPU del proceso (s) para 60 tickets"); axs[0].set_title("Sobrecarga medida (mediana de 3 ejecuciones)")
for i, v in enumerate(vals):
    if not np.isnan(v): axs[0].text(i, v, f"{100 * (v / vals[0] - 1):+.1f} %", ha="center", va="bottom")
fleet = [P.profile_cost_model(n, 100, 40_000, 10, 30) for n in (10, 100, 1000)]
axs[1].bar([str(n) for n in (10, 100, 1000)], [f["ingest_mb_per_day"] / 1000 for f in fleet], color=viz.PALETTE["profiles"])
axs[1].set_xlabel("réplicas perfiladas"); axs[1].set_ylabel("ingesta (GB/día)"); axs[1].set_title("Ingesta: pprof de 40 KB cada 10 s por réplica")
plt.tight_layout(); plt.show()
print({n: f"{f['storage_gb']:.0f} GB (30 días, sin compresión adicional)" for n, f in zip((10, 100, 1000), fleet)})
''')
    md(observe("""
    - La sobrecarga está **dentro del ruido** de medida (± pocos %) en este laboratorio: perfilar a 100 Hz es barato. Esa es la razón de que sea viable «siempre encendido».
    - La ingesta crece **linealmente con las réplicas** (1 000 réplicas × un pprof cada 10 s ≈ 346 GB/día antes de compactar). El palanca no es el muestreo sino el **intervalo de subida** y el **nº de series** (etiquetas). Duplicar el intervalo a 20 s casi no pierde información estadística y reduce la ingesta a la mitad.
    - El modelo asume 40 KB por perfil: **mide el tuyo** (en este lab, `len(prof.to_pprof())`); depende de la profundidad de pila y del nº de funciones distintas.
    """))

    # ------------------------------------------------------------------------------------------------ 11
    md("""
    ## 11 · 🏭 En producción

    - **Google-Wide Profiling** (Ren et al., IEEE Micro 2010) fue el primer perfilado continuo a escala de flota: muestreo estadístico de toda la flota con muy poca sobrecarga y agregación por servicio/versión. Todo el diseño de Pyroscope/Parca/Datadog desciende de esa idea.
    - **Flamegraphs** (Brendan Gregg, ACM Queue/CACM 2016) se popularizaron en Netflix; **FlameScope** (Netflix, open source) añadió la dimensión temporal para ver variaciones de subsegundos.
    - **Grafana Pyroscope** (SDK push o Alloy pull/eBPF; v2: escribe directo en almacenamiento de objetos) y **Grafana Cloud Profiles**; alternativas: **Parca** (Polar Signals) y el *continuous profiler* de **Datadog**.
    - **OpenTelemetry Profiles** entró en **alfa pública en marzo de 2026**, con un perfilador eBPF para Linux como camino principal de recolección y correlación con `trace_id`/`span_id`. ⚠️ **Experimental**: formatos y APIs pueden cambiar; hoy Pyroscope sigue usando pprof por su SDK.
    - Cómo se usa en equipos de élite: perfiles **por versión** para validar cada despliegue («¿esta release gasta más CPU?»), **objetivos de CPU por servicio** en el SLO de coste, y **revisiones trimestrales de top-N funciones** en toda la flota (hay empresas que ahorran cores revisando solo el top-10).
    """)

    md("""
    ## 12 · 🧠 Secretos de la élite

    1. **El profiler de Python escrito en Python miente un poco.** Necesita el GIL, así que solo muestrea cuando el programa lo cede: en el laboratorio, 1 000 Hz pedidos dieron ≈ 300 Hz efectivos (§4.1). py-spy y el SDK `pyroscope-io` leen la memoria del intérprete desde un hilo nativo. *Por qué importa:* la tasa efectiva y el sesgo no son los que configuraste.
    2. **Mide antes de optimizar: la intuición falla.** Aquí, serialización y embeddings sumaban < 15 % y el escaneo de PII, 68 %. El perfil te ahorra semanas de optimizar lo equivocado.
    3. **Self ≠ total.** Optimiza donde el *self* es grande (hojas). Una función con total enorme y self cero (`run_workload`) es solo un camino. Y por Amdahl, el beneficio máximo de arreglar una función con fracción $f$ es $1/(1-f)$.
    4. **El perfil de CPU de un agente está casi vacío de espera.** La latencia vive en el *wall* y en las trazas; la CPU es **coste**. No uses un perfil de CPU para explicar un p95 dominado por el proveedor LLM.
    5. **`span_id` no es una etiqueta normal.** Pyroscope lo guarda fuera del índice de etiquetas (no aparece en `LabelNames`: lo medimos) y se consulta con `SelectMergeSpanProfile`; no lo agrupes ni lo uses como dimensión. Y solo existe para spans **raíz** etiquetados.
    6. **Optimizar la constante vs eliminar trabajo.** La regex dio ≈ ×2 en total; la caché por línea (no volver a escanear lo que no cambió) ≈ ×4-6 (§7.1). En agentes casi todo el contexto se repite entre llamadas: la pregunta correcta es «¿por qué estoy recalculando esto?». Y **los cuellos de botella migran**: Tras arreglar el 68 %, el siguiente (tokens) pasa de ≈ 20 % a dominante. Planifica varias rondas «perfilar → arreglar → perfilar» con **perfil diferencial normalizado**.
    7. **Un perfil corto es una opinión; uno agregado es un hecho.** Error ∝ 1/√N (§2): decide con ≥ 1 000 muestras y compara con ventanas iguales.
    8. **Cuidado con el coste oculto de las etiquetas.** Cada valor nuevo de `version`/`tenant` multiplica series y bloques a consultar. Ponlas en la lista de cardinalidad del módulo 18 desde el día uno.
    """)

    md("""
    ## 13 · ⚠️ Errores comunes

    - **Perfilar en el portátil con una carga irreal** y optimizar lo que no importa en producción (el perfil solo vale con tráfico real).
    - **Confundir wall y CPU**: «el perfil de CPU no muestra el LLM» → claro, el LLM no consume tu CPU.
    - **Comparar perfiles de distinta duración sin normalizar**: más muestras ≠ más CPU por petición.
    - **Cambiar `sys.setswitchinterval` o activar `cProfile` en producción**: modificas lo que mides.
    - **Olvidar `shutdown()`**: los últimos `upload_interval` segundos del proceso (el pico final de un batch) se pierden.
    - **Un `span_id` por cada span hijo**: multiplica el coste; etiqueta solo la raíz salvo necesidad.
    - **Dejar `enable_logging` y credenciales de Pyroscope en notebooks**: usa variables de entorno (`PYROSCOPE_URL`).
    """)

    md(mdj("""
    ## 14 · Autoevaluación
    """,
       details("1. (Cálculo) Un servicio se perfila a 100 Hz durante 30 s; la función `g` aparece en 450 de las 3 000 muestras. Estima su fracción y un IC al 95 %.",
                  "$\\hat p=450/3000=0{,}15$; $\\mathrm{SE}=\\sqrt{0{,}15\\cdot0{,}85/3000}=0{,}0065$; IC ≈ $0{,}15\\pm1{,}96\\cdot0{,}0065=[13{,}7\\,\\%,\\,16{,}3\\,\\%]$. Para estrechar a ±0,5 puntos necesitarías ≈ 4× más muestras."),
       details("2. (Cálculo) `scan_pii` ocupa el 68 % de la CPU y la haces 20 veces más rápida. ¿Aceleración global? ¿y el tope?",
               "$S=1/(0{,}32+0{,}68/20)=1/(0{,}32+0{,}034)=2{,}82$. Tope con $s\\to\\infty$: $1/0{,}32=3{,}1$. Moraleja: el 32 % restante manda; hay que atacar la siguiente etapa."),
       details("3. (Diagnóstico) El flamegraph de CPU de tu servicio muestra casi todo el tiempo en `json.dumps`, pero la traza dice que `invoke_agent` tarda 4 s y `dumps` solo 0,05 s. ¿Qué pasa?",
               "El perfil es **agregado de CPU** y las trazas miden **latencia por petición**. Si el 99 % del tiempo de `invoke_agent` es espera del proveedor LLM (no consume CPU), el flamegraph de CPU no la ve. Consulta el perfil **wall** o confía en la traza para esa latencia; `dumps` puede ser el mayor consumidor de CPU y a la vez irrelevante para el p95."),
       details("4. (Diagnóstico) Tu perfil rápido y el lento tienen distinto nº de muestras y `scan_pii` «sube» de 5 % a 9 % tras el arreglo. ¿Hay regresión?",
               "No necesariamente: al normalizar a porcentaje, si el total de CPU bajó mucho, las funciones restantes pesan más. Compara **CPU absoluta por petición** (ms/ticket × fracción) o muestras normalizadas por nº de peticiones, no solo %."),
       details("5. (Transferencia) Tienes 300 pods de un agente en producción. ¿Cómo diseñas el perfilado continuo (etiquetas, frecuencia, retención) sin disparar el coste?",
               "100 Hz de CPU (no más), `upload_interval` 10-30 s, etiquetas `service_name`, `version`, `env`, `region` (nunca ids de petición), `span_id` solo para spans raíz de trazas muestreadas o lentas, retención corta del detalle (días) y agregados largos; estima ingesta = réplicas × tamaño pprof × (86 400/intervalo). Alerta de CPU/ticket por versión y perfil diferencial en cada despliegue."),
       details("6. (Recuerdo) ¿Qué diferencia hay entre *self* y *total* en un flamegraph?",
               "*Self*: muestras en las que la función es la hoja (tiempo propio). *Total*: muestras en las que aparece en la pila (incluye lo que llama). Se optimiza donde el self es grande."),
       details("7. (Recuerdo) ¿Por qué `span_id` no se trata como una etiqueta normal en Pyroscope?",
               "Tendría cardinalidad ilimitada (una serie por petición) y destruiría la agregación; Pyroscope lo almacena aparte y lo expone vía `SelectMergeSpanProfile`, no como etiqueta consultable por agrupación.")))

    md("""
    ## 15 · Referencias

    - Ren, G., Tune, E., Moseley, T., Shi, Y., Rus, S., Hundt, R. (2010). *Google-Wide Profiling: A Continuous Profiling Infrastructure for Data Centers*. IEEE Micro 30(4).
    - Gregg, B. (2016). *The Flame Graph*. Communications of the ACM 59(6) / ACM Queue 14(2). https://queue.acm.org/detail.cfm?id=2927301
    - Grafana Pyroscope: https://github.com/grafana/pyroscope · documentación: https://grafana.com/docs/pyroscope/latest/ (arquitectura v2: `reference-pyroscope-v2-architecture/`; clientes: `configure-client/`).
    - API de consultas de Pyroscope (protobuf): https://github.com/grafana/pyroscope/blob/main/api/querier/v1/querier.proto (`SelectMergeStacktraces`, `SelectMergeSpanProfile`, `SelectSeries`, `LabelNames`).
    - SDK Python: https://pypi.org/project/pyroscope-io/ · integración OTel: https://pypi.org/project/pyroscope-otel/
    - py-spy (muestreador externo al GIL): https://github.com/benfred/py-spy
    - pprof (formato): https://github.com/google/pprof/blob/main/proto/profile.proto
    - OpenTelemetry Profiles, alfa pública (2026): https://opentelemetry.io/blog/2026/profiles-alpha/
    - Netflix FlameScope: https://github.com/Netflix/flamescope · Parca: https://www.parca.dev/
    - Amdahl, G. (1967). *Validity of the single processor approach to achieving large scale computing capabilities*. AFIPS.
    """)

    nb.save(out)


# =====================================================================================================================
# Proyecto
# =====================================================================================================================
SOLUTION_17 = '''
import re
def top_function(stacks):
    fn, n = P.self_time(stacks).most_common(1)[0]
    return fn.split(".")[-1], n / sum(P.self_time(stacks).values())

def stage_report(stacks, stats):
    sp, st = P.stage_shares(stacks), stats.stage_share()
    return pd.DataFrame([{"etapa": s, "perfil": sp.get(s, 0.0), "cronómetro": st.get(s, 0.0)} for s in ("pii_scan", "tokens", "serialize", "embed_rerank")])

import functools
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
_CARD = re.compile(r"\\d(?:[ -]?\\d){12,18}")

@functools.lru_cache(maxsize=65536)
def _scan_line(line):
    cards = sum(1 for m in _CARD.finditer(line) if P.luhn_ok(re.sub(r"\\D", "", m.group())))
    return len(_EMAIL.findall(line)), cards

@functools.lru_cache(maxsize=65536)
def _tok_line(line):
    return sum(-(-len(w) // 4) for w in line.split())

def my_scan(text):                     # un correo o una tarjeta nunca cruzan un salto de línea: se puede cachear POR LÍNEA
    e = c = 0
    for line in text.split("\\n"):
        a, b = _scan_line(line)
        e += a; c += b
    return {"emails": e, "cards": c}

def my_tokens(text):
    return sum(_tok_line(line) for line in text.split("\\n"))

def run_fixed(n):
    return run_workload("slow", n=n, scan_fn=my_scan, tokens_fn=my_tokens)

def predict_speedup(fixed_share):
    return P.amdahl_speedup(fixed_share, 1e9)

def push_profile(prof, service, variant):
    P.PyroscopeClient().push_connect({"service_name": service, "variant": variant}, prof.to_pprof())

def read_top(service, variant):
    sel = '{service_name="%s",variant="%s"}' % (service, variant)
    c = P.PyroscopeClient(); c.wait_for(sel, timeout_s=90)
    return P.self_time(c.stacks(sel)).most_common(1)[0][0].split(".")[-1]

def worst_ticket(prof):
    t, n = prof.tag_values("ticket").most_common(1)[0]
    top = P.self_time(prof.stacks(ticket=t)).most_common(1)[0][0].split(".")[-1]
    return t, top

def cpu_guard(ms_per_ticket, baseline_ms, max_ratio=0.25):
    return ms_per_ticket <= max_ratio * baseline_ms
'''

RUBRIC_17 = '''
import re as _re
def run_rubric(live=PYRO_UP):
    R = {}
    def chk(name, fn):
        try:
            R[name] = bool(fn())
        except NotImplementedError:
            R[name] = None
        except Exception as e:
            R[name] = False; print(f"  {name}: {type(e).__name__}: {e}")
    PAYLOAD = P.serialize_slow(P.policy_text(), [])        # el texto que de verdad se escanea en cada llamada al LLM (≈ 120 KB)
    texts = ["Escribe a ana.lopez@example.com o a x@y.org", "tarjeta 4111 1111 1111 1111 y 4111111111111112", "nada que ver aquí", P.policy_text(), PAYLOAD]
    chk("R1 top_function identifica el cuello de botella (scan_pii_slow, > 50 % del self)", lambda: (lambda r: r[0] == "scan_pii_slow" and r[1] > 0.5)(top_function(ST_SLOW)))
    chk("R2 stage_report: perfil y cronómetros difieren < 0,15 en cada etapa y pii_scan ∈ [0,50; 0,85]",
        lambda: (lambda d: (abs(d["perfil"] - d["cronómetro"]) < 0.15).all() and 0.50 <= d.set_index("etapa").loc["pii_scan", "cronómetro"] <= 0.85)(stage_report(ST_SLOW, BASE)))
    chk("R3 my_scan: mismo resultado que scan_pii_slow en 5 textos y ≥ 5× más rápido sobre el payload real", lambda: all(my_scan(t) == P.scan_pii_slow(t) for t in texts) and
        (lambda a, b: a / b >= 5)(*(lambda f: (min(__import__("timeit").repeat(lambda: P.scan_pii_slow(PAYLOAD), number=3, repeat=3)), min(__import__("timeit").repeat(lambda: f(PAYLOAD), number=3, repeat=3))))(my_scan)))
    chk("R4 my_tokens: igual que count_tokens_slow en 5 textos y ≥ 3× más rápido", lambda: all(my_tokens(t) == P.count_tokens_slow(t) for t in texts) and
        (lambda a, b: a / b >= 3)(*(lambda f: (min(__import__("timeit").repeat(lambda: P.count_tokens_slow(PAYLOAD), number=3, repeat=3)), min(__import__("timeit").repeat(lambda: f(PAYLOAD), number=3, repeat=3))))(my_tokens)))
    def r5():
        fx = run_fixed(N_P)
        same = [r.status for r in fx.results] == [r.status for r in BASE.results] and [r.input_tokens for r in fx.results] == [r.input_tokens for r in BASE.results]
        close = abs(fx.pii_found["emails"] - BASE.pii_found["emails"]) <= 0.01 * BASE.pii_found["emails"]
        return same and close and BASE.cpu_s / fx.cpu_s >= 3
    chk("R5 run_fixed: mismos estados/tokens, correos ±1 % y CPU ≥ 3× menor", r5)
    def r6():
        fx = run_fixed(N_P)
        fr = BASE.cpu_fraction()
        pred = predict_speedup(fr["pii_scan"] + fr["tokens"])
        meas = BASE.cpu_s / fx.cpu_s
        return 0.4 * pred <= meas <= 1.1 * pred
    chk("R6 predict_speedup (Amdahl): lo medido queda entre 0,4× y 1,1× del tope", r6)
    if live:
        chk("R7 Pyroscope: el perfil antes→top scan_pii_slow y el de después ya no", lambda: (read_top(SERVICE, "slow") == "scan_pii_slow") and (read_top(SERVICE, "fixed") != "scan_pii_slow"))
    else:
        R["R7 Pyroscope (sin stack: se omite)"] = None
    chk("R8 worst_ticket: el ticket más caro y su función principal (scan_pii_slow)", lambda: (lambda t, f: f == "scan_pii_slow" and t.startswith("T-"))(*worst_ticket(PP)))
    chk("R9 cpu_guard: suspende la variante lenta y aprueba la corregida", lambda: (not cpu_guard(BASE.ms_per_ticket, BASE.ms_per_ticket)) and cpu_guard(run_fixed(N_P).ms_per_ticket, BASE.ms_per_ticket))
    ok = sum(v is True for v in R.values()); tot = sum(v is not None for v in R.values())
    for k, v in R.items():
        print(("✅" if v else ("⏭️ " if v is None else "❌")), k)
    print(f"\\nPuntuación: {ok}/{tot} comprobaciones superadas" + ("" if live else " (R7 omitida: sin Pyroscope)"))
    return R
'''


def build_project() -> None:
    nb, out = nb_for(MOD, "17_proyecto_profiling_pyroscope.ipynb", "Proyecto 17 · Cuello de botella de CPU en SupportOps")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 17 · Encuentra y arregla el cuello de botella de CPU de SupportOps con perfiles

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 2 h |
    | **Servicios de Compose** | `profiling` (Pyroscope) para los pasos 6-7 (opcionales: sin él se usan datos pregrabados). Nada más |
    | **RAM aproximada** | < 0,5 GB |
    | **Prerrequisitos** | Lección `17_profiling_pyroscope`; módulos 03 y 16 |
    | **Conexión** | Misma ruta caliente de la lección (`HotPathInstrumentor`). Aquí **tú** escribes el diagnóstico y el arreglo; el SLO de coste del módulo 16 es lo que justifica el trabajo |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. El tráfico se ha multiplicado por 8 y la factura de cómputo del agente (no la del LLM: la de **CPU de tus pods**) se ha triplicado.
    Los SLO de latencia siguen verdes porque el proveedor LLM domina el tiempo de petición, y por eso nadie lo había notado. Producto pide: *encuentra qué código quema la CPU, arréglalo sin cambiar el comportamiento,
    demuéstralo con perfiles y deja una guarda para que no vuelva a pasar.*

    ## Datos

    Tráfico sintético de SupportOps (semilla 42, `mock`): `run_workload("slow", n=…)` ejecuta tickets reales con CPU real; no hay datos externos. Con Pyroscope en `:4040` empujarás tus perfiles; sin él, la captura pregrabada cubre los mismos pasos.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `top_function` | función con más *self* del perfil lento | `scan_pii_slow` con > 50 % (la solución mide ≈ 68 %) |
    | R2 | `stage_report` | reparto por etapa del perfil frente a los cronómetros | diferencia < 0,15 por etapa; `pii_scan` ∈ [0,50; 0,85] |
    | R3 | `my_scan` | idéntico a `scan_pii_slow` en 5 textos y rapidez sobre el payload real (≈ 120 KB) | ≥ 5× (la solución: > 15×; una regex sola da ≈ 3-4×) |
    | R4 | `my_tokens` | idéntico a `count_tokens_slow` en 5 textos y rapidez | ≥ 3× (la solución: ≈ 5×) |
    | R5 | `run_fixed` | mismos estados y tokens, correos ± 1 %, CPU total | ≥ 3× menos (la solución: ≈ ×5) |
    | R6 | `predict_speedup` | Amdahl con las fracciones medidas | lo medido ∈ [0,4×; 1,1×] del tope (la solución: ≈ 0,65×) |
    | R7 | `push_profile`/`read_top` (con Pyroscope) | el perfil «antes» tiene `scan_pii_slow` arriba; el «después» ya no | exacto |
    | R8 | `worst_ticket` | ticket más caro y su función principal vía etiquetas | `scan_pii_slow` |
    | R9 | `cpu_guard` | falla la variante lenta y aprueba la corregida (presupuesto = ¼ de la línea base) | exacto |

    > 📏 Las comparaciones usan **ratios** (no ms absolutos), así el resultado no depende de la velocidad de tu máquina.
    """)

    code(boot("viz,otel"))
    code(SETUP_17 + IMPORTS + IMPORTS_17.replace('N = 60 if FAST_DEV_RUN else 150', 'N = 60 if FAST_DEV_RUN else 120'))

    md("""
    ## Paso 0 · Línea base (te la damos hecha)

    Ejecutamos la variante lenta bajo el perfilador a mano (`mode="cpu"`, 300 Hz) con etiquetas por ticket. `BASE` son los cronómetros por etapa; `ST_SLOW` las pilas; `PP` el perfilador con etiquetas.
    """)
    code('''
N_P = N                                                    # tickets por medición
from contextlib import contextmanager
class TicketTag(Instrumentor):
    def __init__(self, p): self.p = p
    @contextmanager
    def agent_run(self, ctx):
        self.p.set_tag("ticket", ctx.ticket.ticket_id)
        try: yield
        finally: self.p.clear_tag("ticket")
PP = SamplingProfiler(hz=300, mode="cpu")
BASE = run_workload("slow", n=N_P, profiler=PP, extra=[TicketTag(PP)])
ST_SLOW = PP.stacks()
SERVICE = f"supportops-p17-{int(time.time())}"
print(f"{BASE.n_tickets} tickets · {BASE.ms_per_ticket:.1f} ms de CPU/ticket · {PP.total} muestras · cronómetros por etapa (s):", {k: round(v, 2) for k, v in BASE.stage_s.items()})
''')

    def todo(n, title, desc, stub, hints=(), sol_hint=""):
        md(f"## Paso {n} · {title}\n\n{desc}" + ("\n\n" + "\n\n".join(hint(i + 1, h) for i, h in enumerate(hints)) if hints else ""))
        code(stub)

    todo(1, "¿Dónde está el cuello de botella? (TODO)",
         "Escribe `top_function(stacks)`: devuelve `(nombre_corto_de_la_función, fracción_de_self)` de la función con más tiempo **propio** (*self*) de un perfil `Counter[pila→muestras]`.",
         '''
def top_function(stacks):
    # TODO: usa P.self_time(stacks) (Counter función→muestras self); nombre corto = parte tras el último "."
    raise NotImplementedError("TODO 1")

try:
    print(top_function(ST_SLOW))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["La función hoja de cada pila es la que gasta el tiempo propio: `P.self_time` ya cuenta muestras por hoja.", "`fn, n = P.self_time(stacks).most_common(1)[0]`; divide `n` por la suma de todos los self."])

    todo(2, "¿Y el reparto por etapa? (TODO)",
         "Escribe `stage_report(stacks, stats)` → `DataFrame` con columnas `etapa`, `perfil` (fracción según el perfil) y `cronómetro` (verdad de referencia) para `pii_scan`, `tokens`, `serialize`, `embed_rerank`. Usa `P.stage_shares` y `stats.stage_share()`.",
         '''
def stage_report(stacks, stats):
    # TODO: P.stage_shares(stacks) -> dict etapa->fracción (incluye 'other'); stats.stage_share() -> fracción entre las 4 etapas cronometradas
    raise NotImplementedError("TODO 2")

try:
    display(stage_report(ST_SLOW, BASE).round(3))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Recorre las cuatro etapas y construye una fila por etapa con `.get(etapa, 0.0)`.", "`pd.DataFrame([{\"etapa\": s, \"perfil\": sp.get(s, 0.0), \"cronómetro\": st.get(s, 0.0)} for s in etapas])`."])

    todo(3, "El arreglo (1/2): escáner de PII (TODO)",
         "Escribe `my_scan(text)` → `{\"emails\": int, \"cards\": int}` con el **mismo resultado** que `P.scan_pii_slow` y **≥ 5× más rápido** sobre el payload real (≈ 120 KB, que se repite casi idéntico en cada llamada al LLM). "
         "Las tarjetas se validan con Luhn (`P.luhn_ok`). **Mide primero** qué te da una regex sola (spoiler: ≈ 3-4× en solitario) y piensa qué trabajo se está repitiendo.",
         '''
def my_scan(text):
    # TODO: regex precompiladas a nivel de módulo; tarjetas: 13-19 dígitos con espacios/guiones opcionales + P.luhn_ok.
    #       Para llegar a 5×: ¿qué parte del texto no cambia entre llamadas?
    raise NotImplementedError("TODO 3")

try:
    print(my_scan("a@b.org y 4111 1111 1111 1111"), P.scan_pii_slow("a@b.org y 4111 1111 1111 1111"))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Recorrer carácter a carácter en Python es lo lento; el motor de regex lo hace en C. Pero con una regex sola sigues re-escaneando 120 KB que casi no cambian: ¿puedes recordar lo ya escaneado?",
      "Un correo o una tarjeta nunca cruzan un salto de línea: divide el texto en líneas (`text.split(\"\\n\")`), escanea cada línea con una función con `@functools.lru_cache` y suma. Correos: `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}` · tarjetas: `\\d(?:[ -]?\\d){12,18}` + `P.luhn_ok(re.sub(r\"\\D\", \"\", m.group()))`."])

    todo(4, "El arreglo (2/2): contador de tokens (TODO)",
         "Escribe `my_tokens(text)` con el mismo resultado que `P.count_tokens_slow` (cada palabra cuenta `ceil(len/4)` trozos) y ≥ 3× más rápido: la misma idea que en el paso 3.",
         '''
def my_tokens(text):
    # TODO: suma de ceil(len(palabra)/4) para cada palabra de text.split(); con caché por línea
    raise NotImplementedError("TODO 4")

try:
    print(my_tokens("hola mundo cruel"), P.count_tokens_slow("hola mundo cruel"))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["El techo de la división entera: `-(-a // b)`; y el truco de caché del paso anterior sirve aquí igual.", "`@functools.lru_cache` sobre `lambda line: sum(-(-len(w) // 4) for w in line.split())` y suma por líneas."])

    todo(5, "Aplica el arreglo y mide (TODO)",
         "Escribe `run_fixed(n)` que ejecute la variante `slow` conectando **tus** funciones con los ganchos `scan_fn`/`tokens_fn` de `run_workload`; y `predict_speedup(fraccion)` con el tope de Amdahl (`s → ∞`).",
         '''
def run_fixed(n):
    # TODO: run_workload("slow", n=n, scan_fn=..., tokens_fn=...)
    raise NotImplementedError("TODO 5a")

def predict_speedup(fixed_share):
    # TODO: tope de Amdahl cuando la parte arreglada (fracción fixed_share) se vuelve gratis: P.amdahl_speedup(f, 1e9)
    raise NotImplementedError("TODO 5b")

try:
    fx = run_fixed(N_P)
    f = BASE.stage_share()["pii_scan"] + BASE.stage_share()["tokens"]
    print(f"CPU: {BASE.ms_per_ticket:.1f} → {fx.ms_per_ticket:.1f} ms/ticket (×{BASE.cpu_s / fx.cpu_s:.1f}) · tope de Amdahl con f={f:.2f}: ×{predict_speedup(f):.1f}")
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["`run_workload` acepta `scan_fn=` y `tokens_fn=`: funciones `texto -> resultado` que sustituyen a las lentas.", "`P.amdahl_speedup(fraccion, 1e9)` te da el tope; compáralo con `BASE.cpu_s / fx.cpu_s`."])

    todo(6, "Perfiles en Pyroscope (TODO; necesita el perfil `profiling`)",
         "Escribe `push_profile(prof, service, variant)` (empuja `prof.to_pprof()` con `PyroscopeClient.push_connect`) y `read_top(service, variant)` (espera a que exista y devuelve el nombre corto de la función con más *self* según **Pyroscope**). Luego empuja el perfil «antes» (`PP`) y el «después».",
         '''
def push_profile(prof, service, variant):
    # TODO: P.PyroscopeClient().push_connect({"service_name": service, "variant": variant}, prof.to_pprof())
    raise NotImplementedError("TODO 6a")

def read_top(service, variant):
    # TODO: selector '{service_name="...",variant="..."}' -> PyroscopeClient().wait_for(sel) -> .stacks(sel) -> P.self_time(...).most_common(1)
    raise NotImplementedError("TODO 6b")

try:
    if PYRO_UP:
        PF = SamplingProfiler(hz=300, mode="cpu"); run_workload("slow", n=N_P, profiler=PF, scan_fn=my_scan, tokens_fn=my_tokens)
        push_profile(PP, SERVICE, "slow"); push_profile(PF, SERVICE, "fixed")
        print("antes →", read_top(SERVICE, "slow"), "· después →", read_top(SERVICE, "fixed"))
    else:
        print("Pyroscope no está arriba: este paso se omite (docker compose --profile profiling up -d). R7 no puntuará.")
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["La API de la lección §6.1: `push_connect(labels, pprof_gz)`; el `__name__` ya lo pone por ti.", "`sel = '{service_name=\"%s\",variant=\"%s\"}' % (service, variant)`; `c.wait_for(sel, timeout_s=90)`; `c.stacks(sel)`."])

    todo(7, "El ticket más caro (TODO)",
         "Escribe `worst_ticket(prof)` → `(ticket_id, función_principal_de_ese_ticket)` usando las etiquetas `ticket` que el paso 0 añadió a cada muestra (`prof.tag_values(\"ticket\")` y `prof.stacks(ticket=...)`).",
         '''
def worst_ticket(prof):
    # TODO: ticket con más muestras y la función con más self de SUS pilas
    raise NotImplementedError("TODO 7")

try:
    print(worst_ticket(PP))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["`prof.tag_values('ticket')` es un `Counter` ticket→muestras.", "`prof.stacks(ticket=t)` filtra las pilas de ese ticket; después `P.self_time(...)`."])

    todo(8, "Una guarda para que no vuelva (TODO)",
         "Escribe `cpu_guard(ms_per_ticket, baseline_ms, max_ratio=0.25)`: `True` si el coste actual cabe en el presupuesto (`max_ratio` × línea base). Es la versión mínima de un test de regresión de rendimiento en CI.",
         '''
def cpu_guard(ms_per_ticket, baseline_ms, max_ratio=0.25):
    # TODO
    raise NotImplementedError("TODO 8")

try:
    print("lenta pasa la guarda:", cpu_guard(BASE.ms_per_ticket, BASE.ms_per_ticket), "· corregida pasa:", cpu_guard(run_fixed(N_P).ms_per_ticket, BASE.ms_per_ticket))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Es una comparación; el presupuesto se expresa como ratio para no depender de la máquina."])

    md("## Rúbrica · ejecútala cuando quieras")
    code(RUBRIC_17 + '''
try:
    run_rubric()
except NameError as e:
    print("Define las funciones de los pasos primero:", e)
''')

    md("""
    ## Retos extra (nivel experto)

    1. **Perfil diferencial de verdad**: sube `slow` y `fixed` con el SDK `pyroscope-io` y compáralos en Grafana (`Pyroscope → Compare`); explica por qué conviene normalizar.
    2. **Mide la regex sola** (sin caché) en `run_fixed` y compárala con tu solución con caché: ¿cuánto vale optimizar la constante frente a no repetir trabajo? **Cambia `tokens` por un contador de tokens real** (p. ej. `tiktoken`, si lo instalas) y mide cómo cambia el reparto: ¿qué etapa pasa a dominar?
    3. **Perfil *wall***: repite el diagnóstico con `mode="wall"` y `SUPPORTOPS_REAL_SLEEP_SCALE=0.02`; ¿qué aparece que el perfil de CPU no ve?
    4. **Etiquetas por intención**: etiqueta las muestras con `supportops.intent` (cardinalidad 4) y responde: ¿qué tipo de ticket cuesta más CPU?
    5. **CI**: escribe un test de `pytest` que falle si `ms_per_ticket` de `fast` supera 2× el valor de referencia medido en tu máquina.
    """)

    md("""
    ## Reflexión

    - ¿Qué habría pasado si optimizas primero lo que creías (serializar JSON)? Cuantifícalo con Amdahl (fracción medida de `serialize`).
    - ¿Cuándo es **suficiente** esta CPU «gratis» frente a gastar el esfuerzo en reducir tokens (módulo 13)? Compara coste de cómputo de pods y coste del LLM por ticket.
    - ¿Qué etiquetas pondrías en producción para detectar una regresión de CPU por **versión del agente** en el módulo 15?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable: redefine las funciones y vuelve a lanzar la rúbrica.
    """)
    code('# ===================== SOLUCIÓN DE REFERENCIA =====================' + SOLUTION_17 + '''
PF = SamplingProfiler(hz=300, mode="cpu"); run_workload("slow", n=N_P, profiler=PF, scan_fn=my_scan, tokens_fn=my_tokens)
if PYRO_UP:
    push_profile(PP, SERVICE, "slow"); push_profile(PF, SERVICE, "fixed")
print(top_function(ST_SLOW), worst_ticket(PP))
display(stage_report(ST_SLOW, BASE).round(3))
R = run_rubric()
''')
    nb.save(out)


# =====================================================================================================================
README_17 = """# Módulo 17 · Profiling continuo con Pyroscope

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 4 h 30 (lección) + ≈ 2 h (proyecto) · **Servicios:** perfil `profiling` (Pyroscope 2.1.2); `core` solo para la sección traza↔perfil.

El **cuarto pilar** de la observabilidad: de «este span es lento» a «esta línea de código gasta la CPU». Aprendes a leer y construir flamegraphs, a escribir un muestreador de pila y el formato **pprof** a mano, a
empujar perfiles a **Pyroscope 2.x** (Connect-RPC, `/ingest` y el SDK `pyroscope-io`), a correlacionar traza y perfil con `span_id` y a encontrar y arreglar un cuello de botella real de SupportOps midiendo el efecto con un perfil diferencial.

## Contenido

| Archivo | Qué es |
|---|---|
| `17_profiling_pyroscope.ipynb` | Lección (15 secciones, 12 gráficos: pilares, error de muestreo, flamegraph a mano, GIL, CPU vs wall, arquitectura de Pyroscope, Amdahl, diferencial, traza↔perfil, coste) |
| `17_proyecto_profiling_pyroscope.ipynb` | Proyecto: diagnóstico con perfiles, arreglo verificable, perfiles en Pyroscope, ticket más caro y guarda de CPU (rúbrica R1-R9, pistas 🪜, solución tras ⛔ SPOILER) |
| `recorded/capture_seed42.json.gz` | Captura pregrabada (modo sin Pyroscope): pilas lentas/rápidas, GIL, sobrecarga, perfiles leídos de Pyroscope |
| `../supportops/profiling.py` | `SamplingProfiler`, pprof a mano, `PyroscopeClient`, `HotPathInstrumentor`, `run_workload`, `plot_flamegraph`, dashboard |
| `../supportops/tests/test_profiling.py` | 14 pruebas (las de Pyroscope se saltan si no está en :4040) |
| `../stack/grafana/dashboards/17-profiling.json` | Dashboard «17 · Profiling continuo» (uid `profiling`) |
| `../stack/grafana/provisioning/datasources/datasources.yaml` | Añade `tracesToProfiles` al datasource de Tempo (salto span → perfil) |

## Servicios necesarios

- **Sin Docker**: las secciones 1-5 y los experimentos de CPU de la lección y el proyecto (modo degradado con captura pregrabada en lo que depende de Pyroscope). Funciona en Colab.
- **Con Pyroscope**: `cd stack && docker compose --profile profiling up -d` (tarda ≈ 60-90 s en estar *ready*; el SDK `pyroscope-io` y `pyroscope-otel` se instalan en la primera celda).
- **Traza ↔ perfil**: `docker compose --profile core --profile profiling up -d`.

## Lecturas

- Gregg, *The Flame Graph* (ACM Queue 2016) · Ren et al., *Google-Wide Profiling* (IEEE Micro 2010).
- Documentación de Grafana Pyroscope (arquitectura v2, clientes) y `api/querier/v1/querier.proto`.
- OpenTelemetry Profiles (alfa pública, marzo 2026): https://opentelemetry.io/blog/2026/profiles-alpha/

## Qué se probó (honestidad)

Probado con Docker real: Pyroscope 2.1.2 (push Connect y `/ingest` con pprof propio, SDK `pyroscope-io 1.3.0`, `SelectMergeStacktraces`, `SelectMergeSpanProfile`, `LabelNames/Values`, `SelectSeries`), `pyroscope-otel 1.1.0` con el Collector+Tempo reales
(el span raíz lleva `pyroscope.profile.id` y su perfil se recupera por `span_id`), el datasource con `tracesToProfiles` y las 3 consultas del dashboard contra `/api/ds/query`. **No** probado: la navegación visual «Profiles for this span» en un navegador, perfiles de memoria (`mem_enabled`), perfilador eBPF/Alloy,
el perfilador de pila experimental del SDK y OTel Profiles.
"""


def build_readme() -> None:
    (COURSE / MOD / "README.md").write_text(README_17, encoding="utf-8")
    print("OK README 17")


if __name__ == "__main__":
    if "--record" in sys.argv:
        record()
    else:
        build_dashboard()
        build_readme()
        build_lesson()
        build_project()
