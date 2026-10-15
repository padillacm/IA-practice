"""Genera el módulo 07_tempo_traceql: README, lección y proyecto (autor A3).
Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_07.py
Capturar salidas en vivo para el modo degradado (con el stack arriba y Tempo con tempo-metrics.yaml):
    SUPPORTOPS_CAPTURE=1 jupyter nbconvert --to notebook --execute 07_tempo_traceql/07_tempo_traceql.ipynb
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "07_tempo_traceql"

SETUP = '''
import json, gzip, re, time, collections, inspect, textwrap
from supportops import backends, traceql_mini as tq
from supportops.tempo_lab import run_batch, wait_for_traces, INCIDENT_STORY, make_incidents
STACK = check_stack("core+metrics")
HAVE_TEMPO = bool(STACK.up.get("tempo")); HAVE_PROM = bool(STACK.up.get("prometheus")); HAVE_GRAFANA = bool(STACK.up.get("grafana"))
print(f"\\nTempo en vivo: {HAVE_TEMPO} · Prometheus: {HAVE_PROM} · Grafana: {HAVE_GRAFANA}  ->  ",
      "modo COMPLETO" if HAVE_TEMPO and HAVE_PROM else ("modo parcial (sin métricas)" if HAVE_TEMPO else "MODO DEGRADADO (datos pregrabados)"))
'''

LOAD = '''
REC = ROOT / "07_tempo_traceql" / "recorded"
BATCH = json.load(gzip.open(REC / "batch_seed42.json.gz", "rt", encoding="utf-8"))     # lote pregrabado (120 tickets, semilla 42, tiempo simulado)
SPANS = BATCH["spans"]; RES = pd.DataFrame(BATCH["results"])
CAP_FILE = REC / "capture_live.json.gz"
CAP = json.load(gzip.open(CAP_FILE, "rt", encoding="utf-8")) if CAP_FILE.exists() else {}   # salidas de Tempo/Prometheus capturadas en vivo
CAPTURED = {}

def cached(key, live_fn, live=True):
    """Ejecuta ``live_fn`` si hay stack; si falla o no lo hay, usa la captura pregrabada (mismo formato)."""
    if live:
        try:
            v = live_fn(); CAPTURED[key] = v; return v
        except Exception as e:
            print(f"(en vivo falló «{key}»: {str(e)[:110]} · uso la captura pregrabada)")
    if key not in CAP:
        raise KeyError(f"no hay captura pregrabada para «{key}»: levanta el stack o regenera capture_live.json.gz")
    return CAP[key]

print(f"lote pregrabado: {len(SPANS)} spans, {len({s['trace_id'] for s in SPANS})} trazas, {RES.shape[0]} tickets · capturas en vivo disponibles: {len(CAP)}")
'''


def readme() -> str:
    return """# Módulo 07 · Tempo y TraceQL: consultar las trazas

🟡 Intermedio · ≈ 4 h 30 min · Servicios: `docker compose --profile core --profile metrics up -d` con **`TEMPO_CONFIG=tempo-metrics.yaml`** (≈ 0,5 GB de RAM). Funciona en **modo degradado** sin Docker (datos y capturas pregrabadas + un mini motor de TraceQL).

## Qué aprenderás
- **Arquitectura de Tempo 3**: ruta de escritura y de lectura (distributor → live-store / block-builder → almacenamiento de objetos; query-frontend → querier), modo monolítico (el del laboratorio) frente a microservicios con Kafka, bloques Apache Parquet (columnar) y por qué una traza nueva tarda segundos en ser buscable (se mide).
- **TraceQL a mano**: un mini motor (≈ 400 líneas de Python) para entender la semántica —se evalúa **una traza cada vez**, `{A} && {B}` frente a `{A && B}`, estructurales (`>>`, `>`, `~`), agregados— y **contraste con Tempo real** sobre la misma batería de consultas.
- **TraceQL en Tempo**: selectores (intrínsecos vs atributos, ámbitos), estructurales, agregados, `by()`, `select()`, ayudas (`most_recent`), y cómo Tempo ejecuta las consultas (cuántos bytes inspecciona cada variante).
- **Métricas a partir de trazas**: **TraceQL metrics** (`rate()`, `quantile_over_time()`, razones con aritmética) y el **metrics-generator** (span metrics y service graph) con `TEMPO_CONFIG=tempo-metrics.yaml`; cuándo usar cada uno.
- Un **manual de diagnóstico**: consultas que reconstruyen el relato de un lote con fallos inyectados (límite de tasa, proveedor degradado, `orders-api` roto, herramientas lentas, bucles).

## Archivos
| Archivo | Contenido |
|---|---|
| `07_tempo_traceql.ipynb` | Lección (teoría + mini motor + Tempo real + métricas + 10 gráficos + autoevaluación) |
| `07_proyecto_tempo_traceql.ipynb` | Proyecto: 10 preguntas de diagnóstico → escribe las TraceQL (y 2 de métricas) que las responden; corrección automática |
| `recorded/batch_seed42.json.gz` | Lote pregrabado: 120 tickets, 1 077 spans, 4 servicios (`supportops-agent`, `llm-gateway`, `orders-api`, `kb-search`) |
| `recorded/capture_live.json.gz` | Respuestas reales de Tempo/Prometheus capturadas con el stack (modo degradado) |
| `../stack/grafana/dashboards/07-tempo-traceql.json` | Dashboard aprovisionado (TraceQL, TraceQL metrics, span metrics y service graph) |

Código de apoyo (en `supportops/`): `traceql_mini.py` (motor), `tempo_lab.py` (tráfico multi-servicio con propagación W3C). Documentados en `_tools/INTERFACES.md`.

## Servicios necesarios
`core` (Collector, Tempo, Loki, Grafana) + `metrics` (Prometheus), con el metrics-generator activado:
```bash
cd agent-observability-course/stack
TEMPO_CONFIG=tempo-metrics.yaml docker compose --profile core --profile metrics up -d
```
(Si ya estaba arriba con otra configuración, el comando recrea solo Tempo.) Para parar: `docker compose --profile all down -v`.

## Lecturas
- Grafana Labs, *Tempo documentation*: arquitectura (`introduction/architecture`), TraceQL (`traceql/construct-traceql-queries`), *Tune TraceQL query performance*, *TraceQL metrics*, *Service graphs*, *Span metrics* — en el repo `grafana/tempo`, carpeta `docs/sources/tempo`.
- Grafana Labs, notas de las versiones Tempo 3.0 y 3.1 (`docs/sources/tempo/release-notes/v3-0.md`, `v3-1.md`).
- Grafana Labs, *Tempo 3.0 release* (blog) — <https://grafana.com/blog/tempo-3-0-release-all-the-latest-features/>
- OpenTelemetry, *Trace* (modelo de datos de span) — <https://opentelemetry.io/docs/concepts/signals/traces/>

## Siguiente
`08_loki_logql`: lo mismo para los logs, y cómo saltar de una traza a sus logs con `trace_id`.
"""


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "07_tempo_traceql.ipynb", "Módulo 07 · Tempo y TraceQL")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 07 · Tempo y TraceQL: consultar las trazas

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | `core` + `metrics` con **`TEMPO_CONFIG=tempo-metrics.yaml`** (metrics-generator). Modo degradado sin Docker: lote y capturas pregrabadas + mini motor TraceQL (el badge de Colab sirve solo para esa parte) |
    | **RAM aproximada** | ≈ 0,5 GB en reposo (stack) + < 500 MB el kernel |
    | **Prerrequisitos** | Módulos 03-05 (SDK, GenAI semconv, Collector) y 06 (qué spans produce cada estrategia) |
    | **Hilo conductor** | SupportOps pasa a ser **cuatro servicios** (`supportops-agent`, `llm-gateway`, `orders-api`, `kb-search`) y aprendes a hacerle preguntas al lote de trazas |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Describir** la arquitectura de Tempo 3 (ruta de escritura y de lectura, monolítico vs microservicios, Parquet) y **explicar** con una medición por qué una traza nueva tarda segundos en poder buscarse.
    2. **Implementar a mano** la semántica de TraceQL (selección de spans, evaluación *por traza*, operadores estructurales y agregados) con un mini motor y **contrastarla** con Tempo real.
    3. **Escribir** consultas TraceQL con selectores (intrínsecos y atributos con ámbito), operadores lógicos y estructurales, agregados, `by()` y `select()`, evitando las trampas de semántica (`{A} && {B}` frente a `{A && B}`, regex ancladas, `UNSET` frente a `OK`).
    4. **Medir** el coste de una consulta (bytes inspeccionados) y **aplicar** las reglas de ajuste (ámbito, `&&`, atributos mínimos, intrínsecos de traza).
    5. **Derivar métricas de las trazas**: TraceQL metrics (`rate`, `quantile_over_time`, razones) y metrics-generator (span metrics y service graph); **elegir** cuál usar y cuánto cuesta.
    6. **Diagnosticar** un lote con fallos inyectados reconstruyendo el relato de incidentes solo con TraceQL.
    7. **Reconocer** los límites de la consulta de trazas: resultados «los primeros N», no determinismo, frontera live-store/backend, cardinalidad del metrics-generator.
    """)

    md("""
    ## 🔁 Conexión con módulos anteriores
    """)
    md(details("1 · (Módulo 05) ¿Por dónde entran los spans a Tempo en este laboratorio y qué exportador del Collector se usa?",
               "SDK → OTLP/HTTP `:4318` → Collector (`memory_limiter → resource/lab → batch`) → exportador `otlp_grpc/tempo` → Tempo `:4317` (solo dentro de la red de Compose)."))
    md(details("2 · (Módulo 04) ¿Qué *kind* tiene el span `chat` y por qué importa para un *service graph*?",
               "`CLIENT`. El service graph construye aristas emparejando un span CLIENT con el span SERVER que es su hijo en otro servicio; sin pares CLIENT/SERVER no hay aristas."))
    md(details("3 · (Módulo 03) ¿Cómo sabe un servicio remoto a qué traza pertenece una petición?",
               "Por la cabecera W3C `traceparent` (`trace_id` + `parent span_id`), que se inyecta en el cliente y se extrae en el servidor. En este módulo `llm-gateway`, `orders-api` y `kb-search` lo hacen con `propagate.inject/extract`."))
    md(details("4 · (Módulo 06) ¿Por qué `status = ok` no devolverá casi nada en SupportOps?",
               "Por convención de OpenTelemetry los spans correctos quedan en `UNSET`; `OK` solo si el código lo pone explícitamente. Para «no falló» se usa `status != error`."))

    code(boot("viz,otel"))
    code(IMPORTS + SETUP)
    code(LOAD)

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ---
    # 1 · Intuición: preguntarle a un árbol

    Los logs son líneas y las métricas son series: se filtran por valor y por etiqueta. Una **traza es un árbol de spans** y las preguntas útiles son sobre su **forma**:
    *«¿hubo un error **debajo** de la llamada a `orders-api`?»*, *«¿qué traza llamó más de 3 veces a una herramienta?»*, *«¿tardó más el LLM o la base de datos?»*. SQL y los filtros de etiquetas no expresan bien «descendiente de».
    **TraceQL** es el lenguaje de Tempo para eso. Se parece a PromQL/LogQL en la sintaxis, pero su unidad es el **spanset** (un conjunto de spans de **una misma traza**).

    | Si vienes de… | Analogía |
    |---|---|
    | **ML** | Consultar *muestras* de un dataset con condiciones sobre sus *características* (atributos) y sobre las de sus *vecinos* (spans padre/hijo): es filtrar secuencias, no filas sueltas |
    | **Backend** | `SELECT ... WHERE` sobre spans + un `EXISTS` sobre sus descendientes; el equivalente de buscar por tags en Jaeger/Zipkin, pero con estructura y agregados |
    | **SRE** | PromQL para trazas: `{ ... } | rate() by (...)` produce series temporales; la misma consulta que localiza una traza concreta alimenta un panel |

    La misma traza de SupportOps con **tres consultas distintas** (en rojo, los spans que devuelve cada una):
    """)
    code('''
def matched(query, spans):
    """Ids de los spans que devuelve una consulta sobre UNA traza (usa el mini motor que construiremos en la sección 3)."""
    ids = set()
    for ss in tq.evaluate_trace(tq.parse(query), spans):
        ids.update(s["span_id"] for s in ss)
    return ids

def short(s):
    n = s["name"].replace("POST /v1/chat/completions", "POST /v1/chat").replace("invoke_agent supportops-agent", "invoke_agent")
    return n.replace("mock-small", "")

SVC_COLOR = {"supportops-agent": viz.PALETTE["traces"], "llm-gateway": viz.PALETTE["profiles"], "orders-api": viz.PALETTE["metrics"], "kb-search": viz.PALETTE["logs"]}

def draw_tree(ax, spans, hl, title):
    by = {s["span_id"]: s for s in spans}
    kids = collections.defaultdict(list)
    for s in sorted(spans, key=lambda x: x["start_unix_nano"]):
        kids[s["parent_span_id"] if s["parent_span_id"] in by else None].append(s)
    rows = []
    def walk(p, d):
        for s in kids[p]:
            rows.append((d, s)); walk(s["span_id"], d + 1)
    walk(None, 0)
    pos = {s["span_id"]: (d * 9.5, -i * 3.2) for i, (d, s) in enumerate(rows)}
    for d, s in rows:
        if s["parent_span_id"] in pos:
            (x0, y0), (x1, y1) = pos[s["parent_span_id"]], pos[s["span_id"]]
            ax.plot([x0 + 1.5, x0 + 1.5, x1], [y0 - 1.1, y1, y1], color="#9aa3b2", lw=1)
    for d, s in rows:
        x, y = pos[s["span_id"]]; on = s["span_id"] in hl
        col = SVC_COLOR.get(s["resource"]["service.name"], "#888")
        ax.text(x, y, f"{short(s)}\\n{s['resource']['service.name']}" + (" ✗" if s["status"] == "ERROR" else ""), fontsize=7.2, va="center", ha="left",
                bbox=dict(boxstyle="round,pad=0.3", fc="#ffd9d9" if on else "white", ec=viz.PALETTE["error"] if on else col, lw=2.4 if on else 1.2))
    ax.set_xlim(-1, 44); ax.set_ylim(-3.2 * len(rows) + 1, 2); ax.axis("off"); ax.grid(False); ax.set_title(title, loc="left", fontsize=9)

by_trace = collections.defaultdict(list)
for s in SPANS: by_trace[s["trace_id"]].append(s)
hits = tq.search(SPANS, '{ resource.service.name = "orders-api" && status = error } && { span.gen_ai.operation.name = "chat" }')
ONE = by_trace[min(hits, key=lambda h: len(by_trace[h.trace_id])).trace_id]            # la traza más pequeña con ese patrón
QS = ["{ status = error }", '{ name =~ "execute_tool.*" } >> { resource.service.name = "orders-api" }', '{ resource.service.name = "llm-gateway" } && { span.db.system = "postgresql" }']
fig, axs = plt.subplots(1, 3, figsize=(17, 4.8))
for ax, qq in zip(axs, QS):
    draw_tree(ax, ONE, matched(qq, ONE), qq)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **`{ status = error }`** devuelve **todos** los spans con error de la traza (herramienta, llamada HTTP del cliente y servidor remoto): el error se *propaga hacia arriba* por la cadena de llamadas.
    - **`A >> B`** (descendiente) devuelve el lado **derecho**: los spans de `orders-api` que cuelgan de una herramienta. Es la pregunta «¿qué pasó *debajo* de esta herramienta?».
    - **`{A} && {B}`** (dos spansets) devuelve la **unión** de ambos lados *si ambos existen en la misma traza*; aquí `llm-gateway` y `postgresql` están en spans distintos y la consulta funciona. La versión `{ A && B }` (todo dentro de las llaves) habría devuelto **nada**, porque ningún span cumple las dos cosas a la vez (sección 3.1).
    - La traza viaja por **cuatro servicios**; el `trace_id` los une gracias a la cabecera `traceparent`.
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ---
    # 2 · Arquitectura de Tempo 3

    Tempo hace dos cosas: **ingerir** spans (los ordena en columnas Apache Parquet y los guarda en almacenamiento de objetos) y **recuperarlos**, por identificador o con TraceQL. Tempo 3.0 (2026) reorganizó la arquitectura: separó las rutas de escritura y de lectura y eliminó el *ingester* y el *compactor* clásicos.

    | Componente | Qué hace | Modos |
    |---|---|---|
    | **Distributor** | Recibe y valida spans (OTLP recomendado), los reparte por `trace_id` | ambos |
    | **Cola compatible con Kafka** | *Write-ahead log* duradero entre el distributor y los consumidores; permite **RF1** (sin replicar en la ruta de escritura) | solo microservicios |
    | **Block-builder** | Consume de Kafka, construye bloques Parquet y los sube al almacenamiento | solo microservicios |
    | **Live-store** | Sirve los datos **recientes** (memoria + WAL local); los spans son consultables en segundos | ambos |
    | **Query frontend** | Recibe las consultas y las trocea en trabajos paralelos | ambos |
    | **Querier** | Ejecuta los trabajos contra el live-store y el almacenamiento | ambos |
    | **Backend scheduler + worker** | Compactación, retención y mantenimiento de la lista de bloques (sustituyen al *compactor*) | ambos |
    | **Metrics-generator** (opcional) | Deriva métricas RED y *service graphs* de las trazas y las escribe a Prometheus/Mimir (`remote_write`) | ambos |

    El **laboratorio** usa el modo **monolítico** (`-target=all`, el valor por defecto): todo en un proceso, **sin Kafka** (el distributor empuja en proceso al live-store) y con el disco local como almacenamiento. Producción usa microservicios con Kafka y S3/GCS/Azure.
    """)
    code('''
fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 5.6))
for a in (a1, a2):
    a.set_xlim(0, 100); a.set_ylim(0, 50); a.axis("off"); a.grid(False)
C = viz.PALETTE; W, R = C["traces"], C["metrics"]            # azul = ruta de escritura, naranja = ruta de lectura
a1.set_title("MONOLÍTICO · -target=all (nuestro laboratorio)", loc="left")
col = viz.box(a1, 1, 36, 15, 9, "Collector\\n(OTLP gRPC)", C["neutral"], fontsize=8)
dis = viz.box(a1, 21, 36, 16, 9, "Distributor", W, fontsize=8, bold=True)
live = viz.box(a1, 43, 36, 22, 9, "Live-store\\nmemoria + WAL local", W, fontsize=8, bold=True)
blk = viz.box(a1, 71, 36, 27, 9, "Bloques Parquet\\n(disco local /var/tempo)", C["profiles"], fontsize=8)
viz.arrow(a1, viz.right(col), viz.left(dis), color=W); viz.arrow(a1, viz.right(dis), viz.left(live), "en proceso", color=W); viz.arrow(a1, viz.right(live), viz.left(blk), "flush", color=W)
qf = viz.box(a1, 1, 14, 17, 9, "Query frontend", R, fontsize=8, bold=True)
qr = viz.box(a1, 25, 14, 14, 9, "Querier", R, fontsize=8, bold=True)
viz.arrow(a1, viz.right(qf), viz.left(qr), color=R); viz.arrow(a1, viz.top(qr), viz.bottom(live), "recientes", color=R); viz.arrow(a1, (39.5, 18.5), (80, 35.5), "antiguos", color=R, rad=-0.15)
sch = viz.box(a1, 46, 14, 22, 9, "Backend scheduler\\n+ worker (compactación)", C["neutral"], fontsize=8)
viz.arrow(a1, viz.top(sch), (57, 35.5), color=C["neutral"], dashed=True)
mg = viz.box(a1, 73, 14, 25, 9, "Metrics-generator\\n→ remote_write → Prometheus", C["logs"], fontsize=8)
viz.arrow(a1, viz.bottom(dis), (80, 23.5), color=C["logs"], dashed=True, rad=-0.1)
a1.text(1, 4, "Sin Kafka: live-store y metrics-generator reciben del distributor", fontsize=8.5, color=C["neutral"])
a2.set_title("MICROSERVICIOS · producción (recomendado)", loc="left")
col2 = viz.box(a2, 1, 36, 13, 9, "Collector /\\nAlloy", C["neutral"], fontsize=8)
dis2 = viz.box(a2, 18, 36, 14, 9, "Distributor", W, fontsize=8, bold=True)
kaf = viz.box(a2, 36, 36, 13, 9, "Kafka\\n(WAL, RF1)", C["error"], fontsize=8, bold=True)
bb = viz.box(a2, 54, 40, 20, 8, "Block-builder", W, fontsize=8)
ls2 = viz.box(a2, 54, 29, 20, 8, "Live-store (×AZ)", W, fontsize=8)
obj = viz.box(a2, 79, 36, 19, 9, "Object storage\\nS3 / GCS / Azure", C["profiles"], fontsize=8, bold=True)
viz.arrow(a2, viz.right(col2), viz.left(dis2), color=W); viz.arrow(a2, viz.right(dis2), viz.left(kaf), color=W)
viz.arrow(a2, (49.5, 42), (53.5, 43), color=W); viz.arrow(a2, (49.5, 38), (53.5, 33), color=W); viz.arrow(a2, (74.5, 43), (78.5, 42), "bloques", color=W)
qf2 = viz.box(a2, 1, 12, 16, 9, "Query frontend", R, fontsize=8, bold=True)
qr2 = viz.box(a2, 24, 12, 14, 9, "Queriers (×N)", R, fontsize=8, bold=True)
viz.arrow(a2, viz.right(qf2), viz.left(qr2), color=R); viz.arrow(a2, (38.5, 18), (54, 29), "recientes", color=R); viz.arrow(a2, (38.5, 14), (85, 35.5), "antiguos", color=R, rad=-0.1)
mg2 = viz.box(a2, 52, 12, 22, 9, "Metrics-generator\\n(consume de Kafka)", C["logs"], fontsize=8)
viz.arrow(a2, (42.5, 35.5), (60, 21.5), color=C["logs"], dashed=True)
sw = viz.box(a2, 79, 12, 19, 9, "Scheduler + workers", C["neutral"], fontsize=8)
a2.text(1, 3, "Escalan por separado lectura y escritura; Kafka da durabilidad sin replicar", fontsize=8.5, color=C["neutral"])
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Azul = ruta de escritura, naranja = ruta de lectura.** En producción están desacopladas: un pico de consultas no tumba la ingesta y viceversa.
    - La **cola Kafka** es lo que hace posible RF1: la escritura se confirma cuando Kafka la acepta; el live-store y el block-builder consumen *después*. En el laboratorio ese papel lo cumple la llamada en proceso.
    - Las consultas leen **dos sitios**: el live-store (lo reciente) y los bloques (lo antiguo). Esa frontera (por defecto `query_backend_after: 15m` para TraceQL metrics) explica por qué los datos recientes se comportan distinto.
    """))

    md("""
    ## 2.1 · Nuestra configuración, línea a línea

    Es `stack/tempo/tempo-metrics.yaml` (idéntica a `tempo.yaml` más el metrics-generator). Léela con la tabla a la derecha:
    """)
    code('''
print((ROOT / "stack" / "tempo" / "tempo-metrics.yaml").read_text())
''')
    md("""
    | Bloque | Qué controla | Por qué ese valor en el laboratorio |
    |---|---|---|
    | `distributor.receivers.otlp.protocols.grpc` | Puerto OTLP **dentro de la red** de Compose (el host usa el del Collector) | El Collector exporta aquí (`otlp_grpc/tempo`) |
    | `live_store.max_trace_idle: 10s` | Una traza sin spans nuevos durante 10 s se considera completa y se escribe | **Es la razón principal del retraso de búsqueda** (se mide abajo) |
    | `live_store.max_block_duration / max_block_bytes` | Cuándo se cierra un bloque en memoria y se vuelca a disco | Valores pequeños para ver bloques pronto |
    | `backend_scheduler...compaction` | Compactación y retención (`block_retention: 24h`) | 24 h basta para un laboratorio |
    | `storage.trace.backend: local` | Bloques en disco local | Sin S3 ni MinIO; en producción, objeto |
    | `metrics_generator.processor.{span_metrics, service_graphs}` | Qué métricas derivar | Las del módulo (sección 6) |
    | `metrics_generator.registry.collection_interval: 15s` | Cada cuánto escribe a Prometheus | Más corto que el valor por defecto para ver resultados pronto |
    | `metrics_generator.storage.remote_write` | Destino (Prometheus con `--web.enable-remote-write-receiver`) y `send_exemplars: true` | Exemplars: salto de la métrica a una traza |
    | `overrides.defaults.metrics_generator.processors` | Procesadores activos **por tenant** | Sin esto el generador no hace nada |

    Estado de Tempo en vivo (versión y servicios):
    """)
    code('''
def tempo_get(path):
    return backends._get(backends._base("tempo") + path)
info = cached("buildinfo", lambda: tempo_get("/api/status/buildinfo"), live=HAVE_TEMPO)
print({k: info.get(k) for k in ("version", "revision", "branch", "goVersion")})
''')

    md("""
    ## 2.2 · Experimento: ¿cuánto tarda una traza en poder buscarse?
    Enviamos el lote de SupportOps al stack (con `generate_tickets(..., start_s="live")`, ventana que termina ahora) y medimos, para 10 trazas, el tiempo hasta que **(a)** se recupera por identificador (`/api/traces/<id>`) y **(b)** aparece en una búsqueda TraceQL (`{ trace:id = "…" }`).
    """)
    code('''
if HAVE_TEMPO:
    LB = run_batch(120, 42, live=True)                         # genera, instrumenta, exporta por OTLP y hace force_flush
    LSPANS, LIDS, LRES = LB.spans, LB.trace_ids, pd.DataFrame(LB.results)
    print(f"enviados {len(LSPANS)} spans de {len(LIDS)} trazas · modo de exportación: {LB.meta['mode']} · {LB.meta['export_stats']}")
else:
    LB, LSPANS, LIDS, LRES = None, SPANS, BATCH["trace_ids"], RES
    print("Sin Tempo: se usa el lote pregrabado (mismo esquema).")
INV = {v: k for k, v in LIDS.items()}                          # trace_id -> ticket
''')
    code('''
def delay_probe(ids, timeout=75):
    t0 = time.time(); pend_id, pend_s, by_id, by_search = set(ids), set(ids), {}, {}
    while (pend_id or pend_s) and time.time() - t0 < timeout:
        for tid in list(pend_id):
            try:
                backends.tempo_trace(tid); by_id[tid] = time.time() - t0; pend_id.discard(tid)
            except backends.BackendError:
                pass
        for tid in list(pend_s):
            if backends.tempo_search(f'{{ trace:id = "{tid}" }}', minutes=30, limit=5).get("traces"):
                by_search[tid] = time.time() - t0; pend_s.discard(tid)
        time.sleep(1)
    return {"n": len(ids), "by_id": sorted(by_id.values()), "by_search": sorted(by_search.values())}
sample_ids = list(LIDS.values())[:5] + list(LIDS.values())[-5:]
DELAY = cached("delay_probe", lambda: delay_probe(sample_ids), live=HAVE_TEMPO)
fig, ax = plt.subplots(figsize=(9, 3.8))
for k, lab_, col in (("by_id", "por identificador (/api/traces/<id>)", viz.PALETTE["traces"]), ("by_search", "en una búsqueda TraceQL", viz.PALETTE["error"])):
    v = DELAY[k]; ax.step(v, np.arange(1, len(v) + 1) / DELAY["n"], where="post", label=f"{lab_} · mediana {np.median(v):.0f} s" if v else lab_, color=col, lw=2)
ax.axvline(10, color="k", ls="--"); ax.text(10.3, 0.05, "max_trace_idle = 10 s", fontsize=9)
ax.set_xlabel("segundos desde que el notebook terminó de enviar"); ax.set_ylabel("fracción de las 10 trazas visibles"); ax.set_ylim(0, 1.05); ax.legend(loc="lower right"); ax.set_title("Retraso de ingesta → consulta"); plt.tight_layout(); plt.show()
print(DELAY)
''')
    md(observe("""
    - Las trazas **no aparecen al instante**: el Collector agrupa (`batch`, 1 s), el distributor las entrega al live-store y este espera `max_trace_idle` (10 s) sin spans nuevos para considerarlas completas. El orden de magnitud es **decenas de segundos como mucho**, no milisegundos.
    - Consecuencia operativa: en un incidente, la traza del último minuto puede no estar aún; y en un notebook o un test hay que hacer **polling con plazo** (`wait_for_traces`), no un `sleep` fijo.
    - Tempo no tiene noción de «fin de traza»: puede llegar un span más tarde; por eso la traza completa siempre se *reconstruye* al consultar.
    """))

    md("""
    ## 2.3 · Por qué Parquet: lo que no se lee, no se paga

    Tempo guarda los bloques en **Apache Parquet**, un formato **columnar**: cada atributo es una columna. Una consulta lee **solo las columnas que nombra**, no las trazas enteras. Lo comprobamos con una simulación honesta: 20 000 spans sintéticos con 24 atributos, guardados por filas (JSON, como un almacén de documentos) y por columnas, y los bytes que hay que **leer** para responder consultas que citan 1, 2, 4… atributos.
    """)
    code('''
rng = np.random.default_rng(42); N = 20000
cols = {"span:name": rng.choice(["chat", "execute_tool", "GET", "SELECT"], N).tolist(), "span:status": rng.choice(["unset", "error"], N, p=[.93, .07]).tolist(),
        "span:duration": rng.lognormal(5, 1, N).round(1).tolist(), "resource.service.name": rng.choice(["agent", "gateway", "orders", "kb"], N).tolist()}
for i in range(20):                                               # atributos «de relleno» (cadenas largas y números), como los de una app real
    cols[f"span.attr_{i:02d}"] = (rng.integers(0, 10**6, N).tolist() if i % 2 else [f"valor-{v:06d}" for v in rng.integers(0, 10**5, N)])
rows = [{k: v[i] for k, v in cols.items()} for i in range(N)]
row_bytes = len(json.dumps(rows))
col_bytes = {k: len(json.dumps(v)) for k, v in cols.items()}
order = ["span:status", "span:duration", "resource.service.name", "span:name"] + [f"span.attr_{i:02d}" for i in range(20)]
ks = [1, 2, 4, 8, 12, 24]
read_col = [sum(col_bytes[c] for c in order[:k]) for k in ks]
fig, ax = plt.subplots(figsize=(9, 3.9))
ax.plot(ks, [100 * b / row_bytes for b in read_col], "o-", color=viz.PALETTE["traces"], lw=2, label="almacén por columnas (Parquet)")
ax.axhline(100, color=viz.PALETTE["error"], lw=2, label="almacén por filas (hay que leer todo)")
ax.set_xlabel("atributos distintos que cita la consulta"); ax.set_ylabel("% de los bytes que hay que leer"); ax.set_xticks(ks); ax.legend(); ax.set_ylim(0, 110)
ax.set_title(f"Bytes leídos para filtrar {N:,} spans ({row_bytes/1e6:.1f} MB en JSON por filas)"); plt.tight_layout(); plt.show()
print({k: f"{100 * b / row_bytes:.1f} %" for k, b in zip(ks, read_col)})
''')
    md(observe("""
    - Citar **1 o 2 atributos** lee un porcentaje pequeño de los datos; citar los 24 se acerca al almacén por filas: **cada atributo que nombras cuesta**. Por eso la guía de ajuste de Tempo dice «accede a los atributos mínimos».
    - Los atributos de **resource** (p. ej. `service.name`) y los intrínsecos de traza (`trace:duration`, `trace:rootService`) están en columnas **mucho más pequeñas** que las de span: filtrar primero por ellos reduce lo que se escanea.
    - Es una simulación sencilla (no es el formato real: Parquet además comprime y usa *row groups*), pero reproduce el principio. En la sección 4 medimos los bytes que reporta el propio Tempo.
    """))

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ---
    # 3 · TraceQL a mano: un mini motor

    Antes de usar Tempo, construimos el mecanismo. `supportops/traceql_mini.py` (≈ 400 líneas, sin dependencias) evalúa un **subconjunto** de TraceQL sobre spans en memoria. Tiene tres ideas que son *toda* la semántica de TraceQL:

    1. **Una consulta se evalúa sobre una traza cada vez.** Para cada traza se parte de un spanset con *todos* sus spans y se aplica el *pipeline* de izquierda a derecha; si al final queda algún spanset no vacío, la traza es un resultado.
    2. **`{ condición }` filtra spans** (la condición se evalúa sobre **un solo span**). Los operadores entre spansets (`&&`, `||`) combinan **conjuntos de spans de la misma traza**; los estructurales (`>>`, `>`, `~`...) relacionan spans por el árbol y **devuelven el lado derecho**.
    3. **Las etapas `| ...`** (`count()`, `avg()`, `by()`...) operan sobre cada spanset y lo conservan o descartan.

    La parte central es la relación estructural (leer, no memorizar):
    """)
    code('''
print(inspect.getsource(tq._related))
print(inspect.getsource(tq._eval_spanset))
''')
    md("""
    ## 3.1 · Selectores, ámbitos y las tres trampas

    | Qué | Sintaxis | Notas |
    |---|---|---|
    | Intrínsecos (propios del span/traza) | `span:name`, `span:status`, `span:kind`, `span:duration`, `trace:duration`, `trace:rootService`... | Con `:`. `name`, `status`, `kind`, `duration` sin ámbito son alias de los de span |
    | Atributos | `span.http.status_code`, `resource.service.name`, `event.exception.message` | Con `.` y **ámbito** (`span.`, `resource.`, `event.`, `link.`) |
    | Sin ámbito | `.http.route` | Busca en span y en resource: **más lento** |
    | Comparaciones | `= != > >= < <= =~ !~` | Las regex están **ancladas** (`=~ "d"` no encuentra `db`) |
    | Ausencia | `= nil` / `!= nil` | Un atributo que no existe **no** cumple ninguna comparación salvo con `nil` |
    """)
    code('''
def run(query, spans=SPANS):
    hits = tq.search(spans, query)
    return hits

def n(query, spans=SPANS):
    return len(run(query, spans))

rows = [
    ("spans con error", "{ status = error }"),
    ("spans OK explícito (casi ninguno: lo normal es UNSET)", "{ status = ok }"),
    ("no fallaron", "{ status != error }"),
    ("regex anclada: «chat» sin comodín", '{ name =~ "chat" && resource.service.name = "supportops-agent" }'),
    ("regex anclada: con comodín", '{ name =~ "chat.*" && resource.service.name = "supportops-agent" }'),
    ("atributo ausente cumple '= nil'", '{ resource.service.name = "orders-api" && span.db.system = nil }'),
    ("atributo ausente NO cumple '!='", '{ resource.service.name = "orders-api" && span.db.system != "mysql" }'),
]
pd.DataFrame([{"qué compruebo": a, "consulta": q, "trazas": n(q)} for a, q in rows]).set_index("qué compruebo")
''')
    md("""
    **Trampa nº 1: `{A} && {B}` frente a `{A && B}`.** La primera pide que *la traza* contenga un span con A **y** otro (el mismo u otro) con B. La segunda pide que **un solo span** cumpla A y B. La confusión es la causa más frecuente de «mi consulta no devuelve nada».
    """)
    code('''
A, B = 'span.db.system = "postgresql"', "status = error"
res = {f"{{ {A} && {B} }}  (un span cumple ambas)": n("{ %s && %s }" % (A, B)),
       f"{{ {A} }} && {{ {B} }}  (dos spansets, misma traza)": n("{ %s } && { %s }" % (A, B)),
       f"{{ {A} }} || {{ {B} }}  (cualquiera de las dos)": n("{ %s } || { %s }" % (A, B))}
for k, v in res.items():
    print(f"{v:4d} trazas  ←  {k}")
''')
    md("""
    La consulta «error en una SELECT» devuelve 0 en la primera forma porque las `SELECT` de la base de datos **no fallan** en este lote (el error está en el servidor `orders-api` y en la herramienta, no en la consulta SQL): *ningún span* cumple las dos condiciones. La segunda devuelve las trazas que tienen *una* SELECT **y**, en otro span, un error. Elegir la correcta es elegir la pregunta.

    **Trampa nº 2: `UNSET` frente a `OK`.** `status = ok` casi nunca devuelve nada (los spans correctos son `UNSET`, como recomienda OpenTelemetry). Para «no falló» usa `status != error`.
    **Trampa nº 3: regex ancladas.** `name =~ "chat"` no coincide con `chat mock-small`: usa `name =~ "chat.*"`.

    ## 3.2 · Operadores estructurales

    | Operador | Devuelve | Ejemplo en SupportOps |
    |---|---|---|
    | `{A} >> {B}` | spans B **descendientes** de un A | herramienta → ... → consulta SQL lenta |
    | `{A} > {B}` | spans B **hijos directos** de un A | herramienta → su llamada HTTP |
    | `{A} << {B}` · `{A} < {B}` | spans B **ancestros** / **padres** de un A | ¿qué herramienta está por encima de un error SQL? |
    | `{A} ~ {B}` | spans B con un **hermano** A | un `chat` fallido y una herramienta bajo el mismo `invoke_agent` |
    | `&>>`, `&>`... · `!>>`, `!>`... | unión (devuelve ambos lados) · negados (**experimentales**: pueden dar falsos positivos) | no soportados por el mini motor |
    """)
    code('''
def show(query, k=2):
    hs = run(query)
    print(f"{len(hs):3d} trazas · {query}")
    for h in hs[:k]:
        print("      ", ", ".join(f"{s['resource']['service.name']}:{short(s)}" for ss in h.spansets for s in ss[:3]), "…" if h.matched_spans > 3 else "")
show('{ name =~ "execute_tool.*" } >> { span.db.system = "postgresql" && duration > 100ms }')
show('{ name =~ "execute_tool.*" } > { span:kind = client }')
show('{ name =~ "execute_tool.*" } < { span:kind = client }')   # (sintaxis válida; el padre directo de un CLIENT es la herramienta)
show('{ status = error && span.gen_ai.operation.name = "chat" } ~ { span.gen_ai.operation.name = "execute_tool" }')
show('{ name = "invoke_agent supportops-agent" } >> { status = error && resource.service.name = "orders-api" }')
''')
    md("""
    ## 3.3 · Agregados, `by()` y `select()`

    Tras un `|` se opera sobre cada spanset: `count()`, `avg(campo)`, `max()`, `min()`, `sum()` con una comparación; `by(campo)` agrupa; `select(...)` elige qué campos devolver (se recuperan al final: barato). Ejemplos con el relato de SupportOps:
    """)
    code('''
show('{ span.gen_ai.operation.name = "execute_tool" } | count() > 3')                       # bucle de herramientas
show('{ resource.service.name = "kb-search" } | avg(duration) > 200ms')                     # servicio lento de media
show('{ status = error } | by(resource.service.name) | count() > 4')                        # servicios con >4 errores en la misma traza
show('{ trace:rootService = "supportops-agent" && trace:duration > 4s }')                   # intrínseco de traza: el más barato
show('{ resource.service.name = "llm-gateway" } | count() > 3 | select(span.http.response.status_code)')
''')

    md("""
    ## 3.4 · El relato del lote: cinco consultas que cuentan la historia

    El lote se generó con incidentes en una ventana de 10 min: **429 resuelto por el reintento** (0:30-2:00), **proveedor LLM degradado** con 503 persistentes (3:00-4:30), **`orders-api` roto + herramientas lentas** (5:30-7:30) y **bucles de herramientas** (8:00-9:20), sobre un fondo de fallos aleatorios. Si TraceQL es útil, esas cinco consultas deberían **recuperar los incidentes** sin saber nada de ellos de antemano:
    """)
    code('''
t0 = min(s["start_unix_nano"] for s in SPANS)
STORY = [("429 (limitación de tasa)", '{ span.http.response.status_code = 429 }'),
         ("503 del gateway", '{ resource.service.name = "llm-gateway" && span.http.response.status_code >= 500 }'),
         ("orders-api con error", '{ resource.service.name = "orders-api" && status = error }'),
         ("herramienta lenta (> 500 ms)", '{ span.gen_ai.operation.name = "execute_tool" && duration > 500ms }'),
         ("bucle de herramientas", '{ span.gen_ai.operation.name = "execute_tool" } | count() > 3')]
fig, ax = plt.subplots(figsize=(13, 4.4))
for lo, hi, name in [(30, 120, "rate_limited"), (180, 270, "llm_provider_degraded"), (330, 450, "orders_api_broken + tools_slow"), (480, 560, "search_loop")]:
    ax.axvspan(lo / 60, hi / 60, color="#e5e7eb", alpha=.8); ax.text((lo + hi) / 120, len(STORY) - 0.35, name, ha="center", fontsize=8, color="#374151")
for i, (lab_, qq) in enumerate(STORY):
    xs = [(h.start_ns - t0) / 6e10 for h in run(qq)]
    ax.scatter(xs, [i] * len(xs), s=48, color=viz.PALETTE["traces"], alpha=.75, edgecolor="white", zorder=3)
ax.set_yticks(range(len(STORY))); ax.set_yticklabels([f"{l}\\n({n(q)} trazas)" for l, q in STORY], fontsize=8.5); ax.invert_yaxis()
ax.set_xlabel("minuto del lote en que empezó la traza"); ax.set_title("Cada fila es una consulta TraceQL; cada punto, una traza que cumple (sombreado = ventana real del incidente)"); ax.set_xlim(-0.3, 10.2)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Cada consulta **se concentra en su ventana**: el 429 al principio, los 503 en la franja de 3:00-4:30, los errores de `orders-api` y las herramientas lentas a partir del minuto 5:30, los bucles al final. El relato se recupera **solo con TraceQL**.
    - Los puntos *fuera* de las franjas son el **fondo** de fallos aleatorios (`DEFAULT_FAULT_RATES`): las consultas por estructura no distinguen «incidente» de «ruido»; eso lo hace la **densidad temporal**. Esa es la razón de pasar de «buscar trazas» a **métricas derivadas de trazas** (secciones 5 y 6).
    - La consulta de bucle no usa ningún atributo especial: es un **agregado** (`count()` de spans `execute_tool` por traza). Mira la forma, no el contenido.
    """))

    # ---- FIN LECCION 07 ----
    nb.save(out)


def build_project() -> None:
    pass


if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    (COURSE / MOD / "README.md").write_text(readme(), encoding="utf-8")
    print("OK README", COURSE / MOD / "README.md")
    build_lesson()
    build_project()
