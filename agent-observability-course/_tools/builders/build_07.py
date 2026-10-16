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
    - **Por identificador, la traza está casi al instante** (décimas de segundo en la medición): el live-store la tiene en memoria desde que llega. **En una búsqueda TraceQL tarda bastante más** (≈ 15-20 s en la medición, ver las mediciones impresas): el live-store espera `max_trace_idle` (10 s) sin spans nuevos antes de considerar la traza completa y buscable; además el Collector agrupa (`batch`, 1 s).
    - Consecuencia operativa: «tengo el `trace_id` en un log» funciona de inmediato, pero «búscame las trazas con error del último minuto» puede no incluir las más recientes; y en un notebook o un test hay que hacer **polling con plazo** (`wait_for_traces` / reintentos), no un `sleep` fijo.
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
    ("atributo ausente cumple '= nil' (kb-search no tiene db.system)", '{ resource.service.name = "kb-search" && span.db.system = nil }'),
    ("atributo ausente NO cumple '!= mysql'", '{ resource.service.name = "kb-search" && span.db.system != "mysql" }'),
    ("el que sí lo tiene cumple '!= mysql'", '{ resource.service.name = "orders-api" && span.db.system != "mysql" }'),
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
show('{ span:kind = client && resource.service.name = "supportops-agent" } < { name =~ "execute_tool.*" }')   # padre directo (B) de una llamada CLIENT (A)
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
show('{ status = error } | by(resource.service.name) | count() > 1')                        # un servicio con más de un span en error en la misma traza
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
    ax.axvspan(lo / 60, hi / 60, color="#e5e7eb", alpha=.8); ax.text((lo + hi) / 120, -0.62, name, ha="center", fontsize=8, color="#374151")
for i, (lab_, qq) in enumerate(STORY):
    xs = [(h.start_ns - t0) / 6e10 for h in run(qq)]
    ax.scatter(xs, [i] * len(xs), s=48, color=viz.PALETTE["traces"], alpha=.75, edgecolor="white", zorder=3)
ax.set_yticks(range(len(STORY))); ax.set_yticklabels([f"{l}\\n({n(q)} trazas)" for l, q in STORY], fontsize=8.5); ax.set_ylim(len(STORY) - 0.4, -0.95)
ax.set_xlabel("minuto del lote en que empezó la traza"); ax.set_title("Cada fila es una consulta TraceQL; cada punto, una traza que cumple (sombreado = ventana real del incidente)"); ax.set_xlim(-0.3, 10.2)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Cada consulta **se concentra en su ventana**: el 429 al principio, los 503 en la franja de 3:00-4:30, los errores de `orders-api` y las herramientas lentas a partir del minuto 5:30, los bucles al final. El relato se recupera **solo con TraceQL**.
    - Los puntos *fuera* de las franjas son el **fondo** de fallos aleatorios (`DEFAULT_FAULT_RATES`): las consultas por estructura no distinguen «incidente» de «ruido»; eso lo hace la **densidad temporal**. Esa es la razón de pasar de «buscar trazas» a **métricas derivadas de trazas** (secciones 5 y 6).
    - La consulta de bucle no usa ningún atributo especial: es un **agregado** (`count()` de spans `execute_tool` por traza). Mira la forma, no el contenido.
    """))

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ---
    # 4 · Tempo de verdad: ¿coincide el mini motor?

    Ejecutamos la **misma batería de consultas** en Tempo (`GET /api/search?q=...`) y en el mini motor, sobre el lote que acabamos de enviar (usamos las copias locales de los spans como verdad), y comparamos **qué tickets** devuelve cada uno. Antes, esperamos a que el lote sea visible en la búsqueda (con plazo).
    """)
    code('''
def wait_visible(ids, frac=0.98, timeout=120):
    t0, ids = time.time(), set(ids)
    while True:
        r = backends.tempo_search("{ }", minutes=30, limit=5000)
        n_vis = len({t["traceID"].zfill(32) for t in r.get("traces", [])} & ids)
        if n_vis >= frac * len(ids) or time.time() - t0 > timeout:
            return n_vis, round(time.time() - t0)
        time.sleep(3)
if HAVE_TEMPO:
    n_vis, secs = wait_visible(LIDS.values())
    print(f"{n_vis}/{len(LIDS)} trazas del lote visibles en la búsqueda tras {secs} s de espera adicional")
''')
    code('''
BATTERY = [
    ("errores", '{ status = error }'),
    ("gateway 5xx", '{ resource.service.name = "llm-gateway" && span.http.response.status_code >= 500 }'),
    ("429 y reintento recuperado", '{ span.http.response.status_code = 429 } && { span.supportops.attempt = 1 && status != error }'),
    ("bucle de herramientas", '{ span.gen_ai.operation.name = "execute_tool" } | count() > 3'),
    ("orders-api con error", '{ resource.service.name = "orders-api" && status = error }'),
    ("&& dentro de las llaves", '{ span.db.system = "postgresql" && status = error }'),
    ("&& entre spansets", '{ span.db.system = "postgresql" } && { status = error }'),
    ("|| entre spansets", '{ span.db.system = "postgresql" } || { status = error }'),
    ("descendiente >>", '{ name =~ "execute_tool.*" } >> { span.db.system = "postgresql" && duration > 100ms }'),
    ("hijo directo >", '{ name =~ "execute_tool.*" } > { span:kind = client }'),
    ("hermano ~", '{ status = error && span.gen_ai.operation.name = "chat" } ~ { span.gen_ai.operation.name = "execute_tool" }'),
    ("traza lenta (raíz)", '{ trace:rootService = "supportops-agent" && trace:duration > 4s }'),
    ("promedio por servicio", '{ resource.service.name = "kb-search" } | avg(duration) > 200ms'),
    ("agrupar by()", '{ status = error } | by(resource.service.name) | count() > 1'),
    ("regex anclada", '{ name =~ "chat.*" && resource.service.name = "supportops-agent" }'),
    ("ausencia nil", '{ resource.service.name = "kb-search" && span.db.system = nil }'),
    ("evento exception", '{ event:name = "exception" }'),
    ("kind + duración", '{ span:kind = server && resource.service.name = "orders-api" && duration > 300ms }'),
]
def tempo_tickets(q):
    r = backends.tempo_search(q, minutes=30, limit=5000)
    ids = [t["traceID"].zfill(32) for t in r.get("traces", [])]
    return sorted(INV[i] for i in ids if i in INV), r["metrics"]

def compare():
    rows = []
    for lab_, q in BATTERY:
        mini = tq.ticket_ids(LSPANS, tq.search(LSPANS, q)); tmp, m = tempo_tickets(q)
        rows.append({"consulta": lab_, "traceql": q, "mini": len(mini), "tempo": len(tmp), "iguales": mini == tmp,
                     "solo_mini": sorted(set(mini) - set(tmp))[:3], "solo_tempo": sorted(set(tmp) - set(mini))[:3], "inspectedBytes": int(m["inspectedBytes"])})
    return rows
EQ = pd.DataFrame(cached("equivalence", compare, live=HAVE_TEMPO))
print(f"coinciden {EQ.iguales.sum()}/{len(EQ)} consultas exactamente (mismo conjunto de tickets)")
EQ[["consulta", "mini", "tempo", "iguales", "solo_mini", "solo_tempo"]].set_index("consulta")
''')
    code('''
fig, ax = plt.subplots(figsize=(13, 4.8)); x = np.arange(len(EQ)); w = 0.4
ax.bar(x - w/2, EQ.mini, w, color=viz.PALETTE["logs"], label="mini motor (Python)"); ax.bar(x + w/2, EQ.tempo, w, color=viz.PALETTE["traces"], label="Tempo 3.1 (real)")
for i, ok in enumerate(EQ.iguales): ax.text(i, max(EQ.mini[i], EQ.tempo[i]) + 1, "✓" if ok else "≠", ha="center", color=viz.PALETTE["ok"] if ok else viz.PALETTE["error"], fontsize=12, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(EQ.consulta, rotation=40, ha="right", fontsize=8.5); ax.set_ylabel("trazas devueltas"); ax.legend(); ax.set_title("La misma consulta, dos motores: nº de trazas del lote que devuelve cada uno"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Las barras coinciden en el **conjunto de tickets** en las 18 consultas de la batería (medido con Tempo 3.1.0 sobre este lote): la semántica que implementamos a mano (evaluación por traza, `{A} && {B}` frente a `{A && B}`, estructurales, agregados, regex ancladas, `nil`) **es** la de TraceQL.
    - Si alguna fila marca `≠`, la tabla de arriba enseña qué tickets difieren: los casos suelen ser **consultas por eventos** o el mini motor no implementa una sutileza; es la forma sana de usar un motor de juguete: como **oráculo de pruebas** (el proyecto lo usa para corregir sin stack).
    - El número de trazas de Tempo es un resultado **de este lote**, no de todo lo que haya en Tempo (se filtra por los trace_id enviados).
    """))

    md("""
    ## 4.1 · Resultados «los primeros N»: la búsqueda no es determinista

    Tempo reparte la consulta en trabajos paralelos y **devuelve los primeros `limit` resultados que llegan**: dos ejecuciones idénticas pueden devolver conjuntos distintos si hay más coincidencias que `limit`. Para ver *lo más reciente* hay que pedirlo (`with (most_recent=true)`, **experimental**).
    """)
    code('''
def first_n(q, n):
    now = int(time.time())
    r = backends._get(backends._base("tempo") + "/api/search", {"q": q, "limit": n, "start": now - 3600, "end": now + 60})
    return [(t["traceID"].zfill(32), int(t["startTimeUnixNano"]) / 1e9) for t in r.get("traces", [])]
def nondet():
    out = {"sin pista": [[tid for tid, _ in first_n("{ }", 5)] for _ in range(3)]}
    mr = first_n("{ } with (most_recent=true)", 5)
    out["most_recent"] = [tid for tid, _ in mr]; out["most_recent_starts"] = [t for _, t in mr]
    now = time.time(); allr = first_n("{ }", 5000)
    out["newest_5_real"] = [tid for tid, _ in sorted(allr, key=lambda x: -x[1])[:5]]
    return out
ND = cached("nondeterminism", nondet, live=HAVE_TEMPO)
runs = ND["sin pista"]
print("tres ejecuciones de { } con limit=5 → solapamiento entre la 1.ª y la 2.ª:", len(set(runs[0]) & set(runs[1])), "/ 5 · entre la 1.ª y la 3.ª:", len(set(runs[0]) & set(runs[2])), "/ 5")
print("most_recent=true devuelve las 5 más recientes de verdad:", ND["most_recent"] == ND["newest_5_real"] or set(ND["most_recent"]) == set(ND["newest_5_real"]))
''')

    md("""
    ## 4.2 · ¿Cuánto cuesta cada consulta? Los bytes que inspecciona Tempo

    La respuesta de búsqueda incluye `metrics.inspectedBytes`: los bytes de columnas que Tempo leyó. Es la métrica práctica para comparar formulaciones equivalentes (mediana de 3 ejecuciones). En un lote pequeño hay un **coste fijo por bloque**, así que las diferencias se ven en porcentaje, no en órdenes de magnitud; con GB de trazas las mismas reglas separan consultas de segundos de consultas de minutos.
    """)
    code('''
VARIANTS_Q = [("sin ámbito `.http.route`", '{ .http.route = "/kb/search" }'), ("con ámbito `span.http.route`", '{ span.http.route = "/kb/search" }'),
              ("solo `resource.service.name`", '{ resource.service.name = "kb-search" }'),
              ("`||` entre dos selectores", '{ resource.service.name = "orders-api" } || { resource.service.name = "kb-search" }'),
              ("regex en un selector", '{ resource.service.name =~ "orders-api|kb-search" }'),
              ("`duration` (span)", '{ duration > 3s }'), ("`trace:duration`", '{ trace:duration > 3s }'),
              ("atributo + `status`", '{ span.http.response.status_code >= 500 && status = error }'), ("solo el atributo", '{ span.http.response.status_code >= 500 }'),
              ("estructural `>>`", '{ name =~ "execute_tool.*" } >> { span.db.system = "postgresql" }'),
              ("`name` + atributo (&&)", '{ name =~ "execute_tool.*" && span.gen_ai.tool.name = "get_order" }')]
def inspected():
    out = {}
    for lab_, q in VARIANTS_Q:
        v = []
        for _ in range(3):
            v.append(int(backends.tempo_search(q, minutes=30, limit=2000)["metrics"]["inspectedBytes"])); time.sleep(0.3)
        out[lab_] = int(np.median(v))
    return out
IB = cached("inspected_bytes", inspected, live=HAVE_TEMPO)
fig, ax = plt.subplots(figsize=(11, 4.6)); labs = list(IB); vals = [IB[k] / 1024 for k in labs]
cols = [viz.PALETTE["error"] if ("sin ámbito" in k or "||" in k or "estructural" in k) else viz.PALETTE["traces"] for k in labs]
ax.barh(labs, vals, color=cols); ax.invert_yaxis(); ax.set_xlabel("KiB inspeccionados (mediana de 3)")
for i, v in enumerate(vals): ax.text(v, i, f" {v:.0f}", va="center", fontsize=8.5)
ax.set_title("Coste de formulaciones de TraceQL (rojo = formulación a evitar si hay alternativa)"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La **base** (≈ 210-230 KiB) es el coste de tocar los bloques; sobre ella, **el número y el tamaño de las columnas** que nombras decide el resto. Las consultas con **`name`** y las **estructurales** leen claramente más (≈ +45 %) porque necesitan columnas de nombre y de relaciones padre/hijo.
    - Quitar el ámbito (`.http.route`) cuesta unos puntos porcentuales **incluso aquí**: Tempo mira en span y en resource. `trace:duration` y `duration` salen parecidos con pocos datos; la diferencia importa con trazas grandes (columnas de traza mucho más pequeñas).
    - Las reglas de la guía de ajuste de Tempo se resumen así: **solo `&&` cuando se pueda; atributos con ámbito; pocos atributos; filtra primero por resource e intrínsecos de traza; usa columnas dedicadas** (`http.method`, `db.system`, `service.name`...).
    """))

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ---
    # 5 · TraceQL metrics: series temporales desde las trazas

    Añadiendo una función de métricas tras el selector, TraceQL devuelve **series** (como PromQL) calculadas **en el momento de la consulta sobre los spans almacenados**: `rate()`, `count_over_time()`, `quantile_over_time()`, `histogram_over_time()`, `min/max/avg/sum_over_time()`, `compare()`, con `by(...)`, `topk()`, comparaciones (`> 10`) y **aritmética** entre consultas (3.1). Son **GA desde Tempo 3.0** (las *alertas* sobre ellas son experimentales). Se consulta con `GET /api/metrics/query_range` (o `/api/metrics/query`, instantánea).
    """)
    code('''
from supportops.tempo_lab import tempo_metrics, metrics_series
def mq(q, since="15m", step="15s"):
    return {k: [list(p) for p in v] for k, v in metrics_series(tempo_metrics(q, since, step)).items()}
M_RATE = cached("m_rate", lambda: mq('{ } | rate() by (resource.service.name)'), live=HAVE_TEMPO)
M_ERR = cached("m_err", lambda: mq('({ status = error } | rate() by (resource.service.name)) / ({ } | rate() by (resource.service.name))'), live=HAVE_TEMPO)
M_LAT = cached("m_lat", lambda: mq('{ span:kind = server } | quantile_over_time(duration, .5, .95) by (resource.service.name)'), live=HAVE_TEMPO)
OURS = ("supportops-agent", "llm-gateway", "orders-api", "kb-search")
def plot_series(ax, ser, title, ylabel, t0=None, keep=None):
    allp = [p for v in ser.values() for p in v]
    t0 = t0 or min(p[0] for p in allp)
    for k, pts in sorted(ser.items()):
        if not any(o in k for o in OURS) or (keep and not keep(k)): continue
        ax.plot([(t - t0) / 60 for t, _ in pts], [v for _, v in pts], label=k.replace("resource.service.name=", ""), lw=1.8)
    ax.set_title(title, fontsize=10, loc="left"); ax.set_xlabel("minutos"); ax.set_ylabel(ylabel); ax.legend(fontsize=7.5)
fig, axs = plt.subplots(1, 3, figsize=(17, 4.2))
plot_series(axs[0], M_RATE, "{ } | rate() by (service): spans/s", "spans por segundo")
plot_series(axs[1], M_ERR, "error rate / rate total por servicio", "fracción de spans con error")
plot_series(axs[2], M_LAT, "quantile_over_time(duration, .5, .95) · spans SERVER", "segundos", keep=lambda k: "p=0.95" in k)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **`rate()`** muestra la **carga de spans** por servicio *en el tiempo de los spans*: el lote de 10 minutos se reparte en la ventana, con el pico a mitad (el generador de tráfico es «diurno»).
    - La **razón con aritmética** (`({status=error}|rate()) / ({}|rate())`, nueva en 3.1) da la **tasa de error por servicio en una sola consulta**: sube donde la historia dice (gateway en 3:00-4:30, `orders-api` desde 5:30).
    - `quantile_over_time(duration, .5, .95)` da p50/p95 de **spans SERVER** por servicio sin ninguna métrica pregenerada: la latencia que ve cada servicio.
    - Coste: estas consultas **leen spans a cada ejecución** (por eso hay `sample=true`, y por eso los dashboards se apoyan mejor en span metrics cuando se repiten mucho; sección 6).
    """))

    # ------------------------------------------------------------------------------------------------ 6
    md("""
    ---
    # 6 · El metrics-generator: span metrics y service graph

    Con `TEMPO_CONFIG=tempo-metrics.yaml` Tempo ejecuta el **metrics-generator**, que procesa los spans **al ingerirlos** y escribe métricas a Prometheus por `remote_write`:

    | Procesador | Métricas (nombres reales) | Para qué |
    |---|---|---|
    | **span-metrics** | `traces_spanmetrics_calls_total` (contador), `traces_spanmetrics_latency` (histograma → `_bucket/_sum/_count`) con etiquetas `service`, `span_name`, `span_kind`, `status_code` | RED por servicio y operación |
    | **service-graphs** | `traces_service_graph_request_total`, `…_failed_total`, `…_request_server_seconds`, `…_request_client_seconds` con `client`, `server`, `connection_type` | Aristas del mapa de servicios: empareja un span CLIENT con su SERVER hijo; los CLIENT con `db.system`/`peer.service` sin par crean **nodos virtuales** (bases de datos…) |

    Una advertencia de operación que **medimos** antes de escribir esta sección: el generador solo cuenta spans que **terminaron hace menos de `metrics_ingestion_time_range_slack`** (30 s por defecto). Nuestro lote lleva tiempos de hace hasta 10 min, así que en `tempo-metrics.yaml` ampliamos la holgura a 15 min (y la del *live-store*, que afecta a la búsqueda): sin ello, solo se contaría la cola del lote.
    """)
    code('''
from supportops.tempo_lab import prom_range
P_CALLS = cached("p_calls", lambda: {k: [list(p) for p in v] for k, v in prom_range('sum by (service) (rate(traces_spanmetrics_calls_total[1m]))', 20, 15).items()}, live=HAVE_PROM)
P_P95 = cached("p_p95", lambda: {k: [list(p) for p in v] for k, v in prom_range('histogram_quantile(0.95, sum by (le, service) (rate(traces_spanmetrics_latency_bucket[2m])))', 20, 15).items()}, live=HAVE_PROM)
P_EDGES = cached("p_edges", lambda: backends.prom_query('sum by (client, server, connection_type) (increase(traces_service_graph_request_total[30m]))'), live=HAVE_PROM)
P_FAILED = cached("p_failed", lambda: backends.prom_query('sum by (client, server, connection_type) (increase(traces_service_graph_request_failed_total[30m]))'), live=HAVE_PROM)
P_CHECK = cached("p_check", lambda: {"spanmetrics_calls": backends.prom_query('sum(traces_spanmetrics_calls_total)'),
                                    "discarded": backends.prom_query('sum by (reason) (tempo_metrics_generator_spans_discarded_total)')}, live=HAVE_PROM)
print(f"spans contados por span-metrics (contador acumulado): {float(P_CHECK['spanmetrics_calls'][0]['value'][1]):.0f} · spans enviados por este notebook: {len(LSPANS)} (si el stack ya tenía tráfico, el contador es mayor)")
print("spans descartados por el generador:", P_CHECK["discarded"])
''')
    code('''
fig = plt.figure(figsize=(16, 5.4)); gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1, 1], wspace=0.28)
ax = fig.add_subplot(gs[0, 0]); ax.set_xlim(-2, 110); ax.set_ylim(0, 60); ax.axis("off"); ax.grid(False)
POS = {"supportops-agent": (15, 30), "llm-gateway": (66, 50), "orders-api": (66, 28), "kb-search": (66, 6), "orders-db": (97, 28), "orders": (97, 28)}
edges = {(m["metric"]["client"], m["metric"]["server"]): float(m["value"][1]) for m in P_EDGES}
failed = {(m["metric"]["client"], m["metric"]["server"]): float(m["value"][1]) for m in P_FAILED}
nodes = sorted({n for e in edges for n in e}); 
for n_ in nodes:
    x, y = POS.get(n_, (50, 30)); db = n_ in ("orders-db", "orders")
    viz.box(ax, x - 11, y - 4, 22, 8, n_, viz.PALETTE["metrics"] if db else viz.PALETTE["traces"], fontsize=7.5, bold=True)
for (c, s), v in edges.items():
    (x0, y0), (x1, y1) = POS.get(c, (50, 30)), POS.get(s, (50, 30)); fr = failed.get((c, s), 0) / v if v else 0
    ax.annotate("", xy=(x1 - 11.5 if x1 > x0 else x1 + 11.5, y1), xytext=(x0 + 11.5 if x1 > x0 else x0 - 11.5, y0), arrowprops=dict(arrowstyle="-|>", color=viz.PALETTE["error"] if fr > 0.05 else viz.PALETTE["neutral"], lw=1 + 3 * min(1, v / max(edges.values()))))
    ax.text((x0 + x1) / 2 + (4 if y1 < y0 else 0), (y0 + y1) / 2 + 2.5, f"{v:.0f} pet · {fr:.0%} fallo", fontsize=7.5, ha="center", color=viz.PALETTE["error"] if fr > 0.05 else "#444")
ax.set_title("Service graph (Prometheus: traces_service_graph_*)", loc="left", fontsize=10)
ax2 = fig.add_subplot(gs[0, 1]); plot_series(ax2, P_CALLS, "span metrics: llamadas/s por servicio", "llamadas/s")
ax3 = fig.add_subplot(gs[0, 2]); plot_series(ax3, P_P95, "span metrics: p95 de latencia por servicio", "segundos")
plt.show()
''')
    md(observe("""
    - **Service graph:** el agente llama a `llm-gateway`, `orders-api` y `kb-search`; `orders-api` llama a la base de datos, que aparece como **nodo virtual** (no es un servicio instrumentado: lo infiere de los spans CLIENT con `db.system`/`peer.service`). El grosor es la carga; en rojo, las aristas con fallos (el gateway por el 503 persistente, `orders-api` por `upstream_500`).
    - **Span metrics:** RED por servicio. Fíjate en la **forma temporal**: las series del generador se escriben con la hora en que **procesó** los spans, de modo que el lote entero aparece como un **bloque concentrado** en torno al momento del envío, mientras que `rate()` de TraceQL (sección 5) lo repartía en la ventana de 10 min **según el tiempo de cada span**. En producción ambas coinciden (los spans llegan casi en vivo); en un laboratorio con tiempo simulado, no.
    - Si el recuento del generador es menor que el de TraceQL metrics para el mismo periodo, la causa habitual es el **descarte de spans tardíos** (`tempo_metrics_generator_spans_discarded_total`) o los límites de series activas.
    """))
    md("""
    ### ¿TraceQL metrics o span metrics?

    | | **TraceQL metrics** | **Span metrics / service graph (metrics-generator)** |
    |---|---|---|
    | Cuándo se calcula | **Al consultar**, sobre spans almacenados | **Al ingerir**, métricas pregeneradas en Prometheus/Mimir |
    | Flexibilidad | Cualquier atributo, `by()` arbitrario, sin planificar de antemano | Solo las dimensiones configuradas (`dimensions`); añadir una = nuevas series |
    | Coste | CPU/lectura **por consulta** (se paga cada vez que se refresca un panel) | Almacenamiento de series y **cardinalidad** (se paga por serie activa) |
    | Retención | La de las trazas (24 h aquí) | La de Prometheus/Mimir (meses) |
    | Alertas | Experimental | Maduras (Prometheus/Mimir) |
    | Muestreo | `with(extrapolate=true)` (3.1, experimental) | `span multiplier` (3.0) para entornos muestreados |
    | Úsalo para | Exploración, investigación y paneles baratos de baja frecuencia | Paneles RED permanentes, SLOs y alertas |
    """)

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ---
    # 7 · Manual de diagnóstico: del síntoma a la causa solo con TraceQL

    Ejercicio de síntesis: te dicen que «el bot ha ido mal en estos 10 minutos». Sin conocer los incidentes inyectados, ¿qué preguntas haces, en qué orden, y qué responde cada una? El patrón general es **de lo grueso a lo fino**: (1) *¿cuánto y cuándo?* (métricas/densidad), (2) *¿dónde?* (servicio), (3) *¿qué forma tiene?* (estructural/agregado), (4) *¿qué traza concreta lo ilustra?* (abrirla).
    """)
    code('''
ORDER = ["rate_limited", "llm_provider_degraded", "orders_api_broken", "tools_slow", "search_loop"]
STEPS = [
    ("1 ¿Qué tickets fallaron?", '{ trace:rootService = "supportops-agent" && span.supportops.status = "error" }'),
    ("2 ¿Dónde está el error? (servicio)", '{ status = error } | by(resource.service.name) | count() > 0'),
    ("3 ¿El gateway devuelve 5xx?", '{ resource.service.name = "llm-gateway" && span.http.response.status_code >= 500 }'),
    ("4 ¿Reintentos que SÍ funcionaron?", '{ span.http.response.status_code = 429 } && { span.supportops.attempt = 1 && status != error }'),
    ("5 ¿orders-api roto y el agente degradó?", '{ resource.service.name = "orders-api" && status = error } && { span.supportops.status = "degraded" }'),
    ("6 ¿Herramientas lentas por la BBDD?", '{ name =~ "execute_tool.*" } >> { span.db.system = "postgresql" && duration > 100ms }'),
    ("7 ¿Bucles de herramientas?", '{ span.gen_ai.operation.name = "execute_tool" } | count() > 3'),
]
t0s = min(s["start_unix_nano"] for s in LSPANS)
rows = []
for lab_, qq in STEPS:
    hs = tq.search(LSPANS, qq); tk = tq.ticket_ids(LSPANS, hs)
    st = LRES[LRES.ticket_id.isin(tk)].status.value_counts().to_dict()
    mins = [(h.start_ns - t0s) / 6e10 for h in hs]
    rows.append({"pregunta": lab_, "trazas": len(hs), "ventana (min)": f"{min(mins):.1f}-{max(mins):.1f}" if mins else "—", "estado de los tickets": st})
pd.set_option("display.max_colwidth", 80); pd.DataFrame(rows).set_index("pregunta")
''')
    code('''
# La verdad de campo (ground truth) del generador: ¿qué tickets sufrieron de verdad cada incidente?
truth = LRES.groupby("incident", dropna=True).agg(tickets=("ticket_id", "size"), errores=("status", lambda s: int((s == "error").sum())),
                                                    degradados=("status", lambda s: int((s == "degraded").sum())), max_steps=("status", lambda s: int((s == "max_steps").sum())))
truth.loc[[i for i in ORDER if i in truth.index]]
''')
    md("""
    La tabla de arriba reconstruye la historia (429 que se resuelve, 503 persistentes, `orders-api` roto con herramientas lentas, bucles) y la de abajo es la **verdad de campo** del generador: coinciden en el orden de magnitud y la ventana. Con trazas reales no tienes verdad de campo, y por eso el último paso siempre es **abrir una traza concreta** (`GET /api/traces/<id>` o el visor de Grafana) para confirmar la causa.

    ### El dashboard provisionado
    `stack/grafana/dashboards/07-tempo-traceql.json` (uid `tempo-traceql`, carpeta «Curso observabilidad de agentes») reúne este manual: tablas de trazas con TraceQL (errores y bucles), series de TraceQL metrics, RED de span metrics, tasa de fallos por arista del service graph y el mapa de servicios. Se genera con `supportops.dashkit` desde `build_07.py` (dashboards como código, módulo 10) y se valida contra Grafana real en el build.
    """)

    # ------------------------------------------------------------------------------------------------ 8
    md("""
    ---
    ## 🏭 En producción

    - **Grafana Labs (Tempo 3.0, 2026).** La nueva arquitectura separa lectura y escritura, usa Kafka como WAL duradero y **RF1** (en 2.x había que replicar ×3: el objetivo declarado del rediseño es almacenar una copia de las trazas en lugar de tres; fuente: blog y notas de la versión 3.0). Además: TraceQL metrics GA, límite de cardinalidad por etiqueta en el metrics-generator, *span name sanitization* (experimental) y **Redaction** de trazas con datos sensibles (3.1: por consulta TraceQL en vez de lista de IDs, relevante para el módulo 20).
    - **Formato:** vParquet5 es el formato por defecto desde Tempo 3.1 (los bloques vParquet4 siguen siendo legibles) y 3.0 duplicó las *dedicated columns* (atributos frecuentes con columna propia, más baratos de filtrar).
    - **Patrones que verás en equipos de plataforma:** una *regla de atributos obligatorios* (`service.name`, `deployment.environment.name`, `service.version`, y en agentes `gen_ai.agent.name`, `supportops.ticket.id`), TraceQL guardado como consultas de runbook, y **métricas RED con el metrics-generator para los paneles permanentes** y TraceQL metrics para investigar.
    - **Coste:** el almacenamiento de trazas es barato (objeto + Parquet); lo caro es **leer**: una consulta sin filtros sobre días de datos. Las guías de ajuste (ámbito, `&&`, atributos mínimos) y los límites de duración de búsqueda (`max_duration` 168 h, y 24 h por defecto en TraceQL metrics) existen por eso.
    """)

    md("""
    ## 🧠 Secretos de la élite

    1. **El punto ciego de la «hora del span».** Tempo usa la hora de los spans para decidir en qué bloque buscar. Por defecto el live-store solo deja que un span **dentro de ±2 min** modifique el rango temporal de su bloque (`live_store.wal.ingestion_time_range_slack`); la documentación avisa de que *«esto puede hacer que una traza no se encuentre»*. Lo medimos: lotes con spans de hasta 10 min de antigüedad → **solo 12-14 de 30 trazas** aparecían en búsquedas con rango (y se *iban* según pasaba el tiempo), aunque `GET /api/traces/<id>` las devolvía siempre; con la holgura en 15 min, **30 de 30 a los 20-30 s**. Si tu pipeline reenvía datos retrasados (colas, reintentos, *batch jobs*), esto te afecta en producción.
    2. **El generador de métricas descarta los spans tardíos** (`metrics_ingestion_time_range_slack`, 30 s por defecto): se guardan y se pueden buscar, pero **nunca** entran en span metrics ni en el service graph. Compara `traces_spanmetrics_calls_total` con un `count_over_time()` de TraceQL y mira `tempo_metrics_generator_spans_discarded_total{reason="outside_metrics_ingestion_slack"}`.
    3. **La búsqueda devuelve «los primeros N», no «todos» ni «los últimos».** Dos ejecuciones iguales de `{ }` con `limit=5` solaparon **entre 0 y 4 de 5** según la ejecución (nuestras mediciones: 0/5 con el stack cargado de lotes, 4/5 con un único lote). Para el más reciente, `with (most_recent=true)` (experimental); para contar, usa TraceQL metrics (`count_over_time`) en lugar de contar resultados de búsqueda.
    4. **`{A} && {B}` y `{A && B}` son preguntas distintas** (sección 3.1) y además cuestan distinto: solo `&&` dentro de un selector permite empujar el filtro a Parquet (*predicate pushdown*); `||` y los estructurales no.
    5. **`duration` es la del *span*, no la de la traza.** El alias sin ámbito `duration` = `span:duration`; para «traces lentas» usa `trace:duration` (y `trace:rootService`/`trace:rootName`, que además son los filtros más baratos).
    6. **Las métricas del generador tienen «hora de procesamiento»; TraceQL metrics, «hora del span».** Con datos en vivo coinciden; con reenvíos o *backfill*, una muestra un bloque y la otra un reparto. Elige la fuente según la pregunta.
    7. **Cardinalidad del generador:** cada `dimension` (y cada nombre de span con IDs: `GET /orders/123`) multiplica las series. Nunca `ticket.id` como dimensión; normaliza rutas en el instrumento (`/orders/{id}`, como hace `orders-api`) o activa `span_name_sanitization` (3.0, experimental).
    8. **Por identificador, inmediato; por búsqueda, con retraso.** Medimos décimas de segundo frente a ≈ 15-20 s. Un enlace «ver traza» desde un log o una alerta funciona al instante; una búsqueda «las trazas con error del último minuto» debe tolerar ese retraso.
    9. **El service graph necesita pares CLIENT/SERVER.** Sin ellos las aristas no existen (se cuenta como `traces_service_graph_unpaired_spans_total`); los CLIENT con `db.system`/`peer.service` crean nodos virtuales. Por eso instrumentar `chat` como CLIENT (módulo 04) tiene consecuencias aguas arriba.
    """)

    md("""
    ## ⚠️ Errores comunes

    - Buscar `status = ok` y concluir «nada funciona»: lo normal es `UNSET`.
    - Olvidar que las regex están **ancladas** (`name =~ "chat"` no encuentra `chat mock-small`).
    - Atributos sin ámbito (`.http.route`) en consultas de dashboard que se ejecutan cada 10 s.
    - Usar la **búsqueda** para contar (límite, no determinista); usa TraceQL metrics o span metrics.
    - Ejecutar `rate()` de TraceQL metrics en un panel con refresco de 5 s sobre 24 h: cada refresco lee spans.
    - `ticket.id` como dimensión del metrics-generator.
    - Enviar datos con hora muy atrasada y esperar verlos en span metrics (30 s) o en la búsqueda (2 min de holgura).
    - Pensar que el mini motor es Tempo: no soporta métricas, `with(...)` ni operadores `&>>`/`!>>`.
    """)

    md("""
    ## Autoevaluación
    """)
    md(details("1 · (Diagnóstico) Tu consulta `{ span.db.system = \"postgresql\" && status = error }` devuelve 0 trazas, pero sabes que hay errores en la ruta de la base de datos. ¿Qué cambia y por qué?",
               "Pide que **un mismo span** sea de PostgreSQL **y** esté en error. En SupportOps el error está en el servidor `orders-api` y en la herramienta, no en la SELECT. La pregunta correcta es *dos spansets en la misma traza*: `{ span.db.system = \"postgresql\" } && { status = error }` (13 trazas en el lote) o, si importa la estructura, `{ status = error && resource.service.name = \"orders-api\" } >> { span.db.system = \"postgresql\" }`."))
    md(details("2 · (Cálculo) Un servicio genera 2 000 trazas/s de 30 spans y guardas 14 días. Con ≈ 1 KB por span comprimido (supuesto), ¿cuánto almacenamiento de trazas es? ¿Y con RF3 frente a RF1?",
               "2 000 × 30 = 60 000 spans/s ≈ 60 MB/s; × 86 400 s ≈ 5,2 TB/día; × 14 ≈ **72,6 TB**. Con **RF3** (Tempo 2.x) serían ≈ 218 TB; con **RF1** (Tempo 3.0 con Kafka como WAL), 72,6 TB: el objetivo declarado del rediseño 3.0 es quedarse con una copia en vez de tres. (Las cifras absolutas dependen del supuesto de 1 KB/span; el cociente 3/1 no.) Esto es lo que justifica el **muestreo** del módulo 18."))
    md(details("3 · (Diagnóstico) Envías un lote de pruebas con la hora de hace 8 minutos. `GET /api/traces/<id>` funciona, pero la búsqueda TraceQL con rango solo encuentra la mitad y, con el paso de los minutos, aún menos. ¿Cuál es la causa y la solución en laboratorio y en producción?",
               "Es la holgura de ingesta del **live-store** (`live_store.wal.ingestion_time_range_slack`, 2 min por defecto): los spans más antiguos que eso no actualizan el rango temporal del bloque, y la búsqueda con rango lo descarta. En laboratorio se amplía (aquí 15 min). En producción lo correcto es **no enviar datos con horas tan atrasadas** (o aceptar que no son buscables por rango) y vigilar el retraso de la cola/Collector; ampliar la holgura tiene coste (bloques con rangos más anchos → más bloques por consulta)."))
    md(details("4 · (Cálculo) `traces_spanmetrics_calls_total` suma 4 800 spans en una hora, pero `{ resource.service.name = \"orders-api\" } | count_over_time()` da 5 600 en el mismo periodo. ¿Cuál es la hipótesis principal y cómo la compruebas?",
               "800 spans (14 %) no llegaron a las métricas pregeneradas: lo más probable es **descarte de spans tardíos** (`outside_metrics_ingestion_slack`) o series limitadas. Se comprueba con `tempo_metrics_generator_spans_discarded_total` por `reason` y `tempo_metrics_generator_registry_series_limited_total`. TraceQL metrics lee los spans almacenados, que incluyen los tardíos."))
    md(details("5 · (Transferencia) Quieres un panel «p95 de latencia de la herramienta `get_order`» que se refresque cada 10 s para 30 personas durante meses. ¿TraceQL metrics o span metrics?",
               "**Span metrics** (metrics-generator): el cálculo se hace una vez al ingerir y Prometheus/Mimir sirve las consultas baratas y con retención larga; añade `span_name` o una dimensión `gen_ai.tool.name` controlada. TraceQL metrics releería spans en cada refresco de cada usuario. Dejas TraceQL metrics para investigaciones puntuales y para atributos que no merece la pena convertir en dimensión."))
    md(details("6 · ¿Qué devuelve `{ name =~ \"execute_tool.*\" } >> { span.db.system = \"postgresql\" }`: spans `execute_tool`, spans `SELECT` o ambos? ¿Y con `&>>`?",
               "Los spans de la **derecha** (las SELECT descendientes de una herramienta). Con el operador de unión `&>>` devolvería **ambos lados** (herramienta y SELECT). `&>>` y los negados `!>>` no están en el mini motor; los negados son experimentales y pueden dar falsos positivos."))
    md(details("7 · (Diagnóstico) Un compañero cuenta incidentes con `limit=20` en la búsqueda y dice que «siempre hay 20». ¿Qué le explicas?",
               "Que `limit` es un **tope de resultados devueltos, no el número de coincidencias**, y la búsqueda toma los primeros que llegan de varios trabajos en paralelo (no determinista). Para contar o ver la tasa: `{ ... } | count_over_time()` / `rate()` con TraceQL metrics, o span metrics."))
    md(details("8 · (Transferencia) ¿Qué atributos de SupportOps declararías «obligatorios» para poder hacer todas las preguntas de este módulo, y cuáles NO convertirías en dimensión de span metrics?",
               "Obligatorios: `service.name`, `deployment.environment.name`, `service.version` (resource); `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.tool.name`, `gen_ai.request.model`, `error.type`, `supportops.status`, `supportops.attempt` (span). **No** dimensión: `supportops.ticket.id`, `supportops.customer.id`, `trace_id`, rutas con IDs (cardinalidad ilimitada); sí `gen_ai.tool.name` y `gen_ai.request.model` (valores acotados)."))

    md("""
    ## Referencias

    - Grafana Labs, *Tempo architecture* y *Tempo architecture reference* — repo `grafana/tempo`, `docs/sources/tempo/introduction/architecture.md` y `reference-tempo-architecture/` (<https://github.com/grafana/tempo/tree/main/docs/sources/tempo>).
    - Grafana Labs, *Construct a TraceQL query* y *Tune TraceQL query performance* — `docs/sources/tempo/traceql/construct-traceql-queries.md` y `tune-traceql-queries.md` (mismo repo).
    - Grafana Labs, *TraceQL metrics* (`metrics-from-traces/metrics-queries/`), *Span metrics* y *Service graphs* (`metrics-from-traces/span-metrics/`, `service_graphs/`) — mismo repo.
    - Grafana Labs, *Tempo HTTP API* (`/api/search`, `/api/traces/<id>`, `/api/metrics/query_range`) — `docs/sources/tempo/api_docs/_index.md`.
    - Grafana Labs, *Tempo configuration* (`live_store`, `metrics_generator`, `query_frontend`, `ingestion_time_range_slack`) — `docs/sources/tempo/configuration/_index.md`.
    - Grafana Labs, notas de la versión *Tempo 3.0* y *Tempo 3.1* — `docs/sources/tempo/release-notes/v3-0.md` y `v3-1.md`; blog *Tempo 3.0 release* — <https://grafana.com/blog/tempo-3-0-release-all-the-latest-features/>.
    - OpenTelemetry, *Traces* (modelo de span, estado `UNSET`/`OK`/`ERROR`, tipos de span) — <https://opentelemetry.io/docs/concepts/signals/traces/>.
    - W3C, *Trace Context* (`traceparent`) — <https://www.w3.org/TR/trace-context/>.
    - Código del módulo: `supportops/traceql_mini.py`, `supportops/tempo_lab.py`, `supportops/tests/test_traceql_mini.py`.
    """)

    code('''
import os
if os.environ.get("SUPPORTOPS_CAPTURE") == "1" and CAPTURED:                 # solo al regenerar las capturas del modo degradado (ver build_07.py)
    with gzip.open(CAP_FILE, "wt", encoding="utf-8") as f:
        json.dump({**CAP, **CAPTURED}, f)
    print("capturas guardadas:", sorted(CAPTURED))
''')

    # ---- FIN LECCION 07 ----
    nb.save(out)


# =====================================================================================================================
def build_dashboard(check: bool = True) -> None:
    """Dashboard 07 como código (con supportops.dashkit, módulo 10) y, si Grafana responde, validación de cada consulta."""
    sys.path.insert(0, str(COURSE))
    from supportops import dashkit as dk  # noqa: PLC0415

    d = dk.Dashboard("tempo-traceql", "07 · Tempo y TraceQL", tags=["curso", "tempo", "traceql"], refresh="10s",
                     description="Manual de diagnóstico del módulo 07: TraceQL, TraceQL metrics, span metrics y service graph de SupportOps.")
    d.add(dk.text("Cómo leerlo", "Lote de SupportOps: **agente → gateway LLM, orders-api, kb-search**. Arriba, **trazas** (TraceQL); en medio, **series calculadas "
                  "al consultar** (TraceQL metrics); abajo, **métricas pregeneradas** (metrics-generator, requieren `TEMPO_CONFIG=tempo-metrics.yaml`).", w=24, h=3))
    d.row("Trazas (TraceQL)")
    d.add(dk.traces_table("Tickets con error (raíz = agente)", '{ trace:rootService = "supportops-agent" && span.supportops.status = "error" }', w=12, h=9, description="Trazas cuyo span raíz es del agente y terminó en error. Pulsa el traceID para abrir la traza. Filtra primero por trace:rootService (intrínseco barato)."),
          dk.traces_table("Bucles de herramientas (> 3 execute_tool por traza)", '{ span.gen_ai.operation.name = "execute_tool" } | count() > 3', w=12, h=9, description="Agregado de TraceQL: trazas con más de 3 spans execute_tool. Detecta bucles sin atributos especiales."))
    d.row("TraceQL metrics (se calculan al consultar)")
    rate = {**dk.tempo('{ } | rate() by (resource.service.name)', table_type="spans"), "metricsQueryType": "range", "step": ""}
    err = {**dk.tempo('({ status = error } | rate() by (resource.service.name)) / ({ } | rate() by (resource.service.name))', table_type="spans"), "metricsQueryType": "range", "step": ""}
    d.add(dk.timeseries("spans/s por servicio", [rate], unit="short", w=12, h=8, description="TraceQL metrics: rate() por servicio, calculado al consultar sobre los spans almacenados (hora del span)."), dk.timeseries("fracción de spans con error por servicio", [err], unit="percentunit", w=12, h=8, description="Razón de dos consultas TraceQL metrics (aritmética, Tempo 3.1): spans en error / spans totales por servicio."))
    d.row("Span metrics y service graph (metrics-generator)")
    d.add(dk.timeseries("llamadas/s por servicio (span metrics)", [dk.prom('sum by (service) (rate(traces_spanmetrics_calls_total[$__rate_interval]))', "{{service}}")], unit="reqps", w=8, h=8, description="Span metrics (metrics-generator): traces_spanmetrics_calls_total. Hora de procesamiento, no del span."),
          dk.timeseries("p95 de latencia por servicio", [dk.prom('histogram_quantile(0.95, sum by (le, service) (rate(traces_spanmetrics_latency_bucket[$__rate_interval])))', "{{service}}")], unit="s", w=8, h=8, description="histogram_quantile sobre traces_spanmetrics_latency_bucket (span metrics)."),
          dk.bargauge("fallos por arista del service graph", [dk.prom('sum by (client, server) (rate(traces_service_graph_request_failed_total[5m])) / sum by (client, server) (rate(traces_service_graph_request_total[5m]))', "{{client}} → {{server}}", instant=True)], unit="percentunit", w=8, h=8, description="Fracción de peticiones fallidas por arista cliente→servidor (traces_service_graph_request_failed_total / request_total)."))
    nodegraph = {"type": "nodeGraph", "title": "Mapa de servicios (service graph)", "description": "Service graph del datasource Tempo (se resuelve en el navegador con las métricas traces_service_graph_* de Prometheus; no se valida por /api/ds/query).", "gridPos": {"x": 0, "y": 0, "w": 24, "h": 10},
                 "datasource": dk.DS_TEMPO, "options": {}, "fieldConfig": {"defaults": {}, "overrides": []},
                 "targets": [{"datasource": dk.DS_TEMPO, "queryType": "serviceMap", "serviceMapQuery": "", "refId": "A"}]}
    d.add(nodegraph)
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "07-tempo-traceql.json")
    print("OK dashboard", path, "· lint:", dk.lint(d.to_dict()) or "sin avisos")
    if check:
        try:
            res = dk.query_check(d.to_dict())
            for r in res:
                print(("  ok " if r["ok"] else "  ERR"), r["panel"], "| filas:", r["rows"], r["error"][:120])
        except Exception as e:  # noqa: BLE001 (sin Grafana: no se valida)
            print("  (Grafana no disponible: dashboard sin validar)", str(e)[:80])


def build_project() -> None:
    nb, out = nb_for(MOD, "07_proyecto_tempo_traceql.ipynb", "Proyecto 07 · Preguntas de diagnóstico con TraceQL")
    md, code = nb.md, nb.code
    H = {"Q1": [16, "72189d8ad8"], "Q2": [3, "af27feed05"], "Q3": [4, "8320d750b3"], "Q4": [8, "1703f40404"], "Q5": [2, "0a1b65e94c"], "Q6": [20, "39a83d88f9"],
         "Q7": [3, "af27feed05"], "Q8": [9, "fc2e3c5db5"], "P1": [13, "4a75247585"], "P2": [53, "b618fe8df7"], "P3": [120, "2caa8746a4"]}
    md("""
    BADGE_PLACEHOLDER

    # Proyecto 07 · Diez preguntas de diagnóstico: escribe la TraceQL que las responde

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Opcionales (`core` + `metrics`, con `TEMPO_CONFIG=tempo-metrics.yaml`) para la verificación contra Tempo; la corrección usa el mini motor y funciona **sin Docker** (Colab) |
    | **RAM aproximada** | < 500 MB (+ ≈ 0,5 GB si usas el stack) |
    | **Prerrequisitos** | Lección `07_tempo_traceql` y proyecto 06 (qué atributos lleva cada span) |
    | **Conexión** | Aplica el manual de diagnóstico de la lección a un lote nuevo de la misma historia; las consultas que escribas son las que usarás como runbook en el módulo 16 y como paneles en el 10 |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Soporte te escala ocho preguntas sobre las últimas horas del agente («¿qué clientes premium se quedaron sin respuesta por el gateway?», «¿qué tickets entraron en bucle?»...). Tienes el lote de trazas (120 tickets, 4 servicios) y debes **responder cada pregunta con una consulta TraceQL** (no con pandas). Además, para el *dashboard*, escribes dos consultas de **TraceQL metrics** y una de **span metrics**.

    ## Datos

    El lote pregrabado `recorded/batch_seed42.json.gz` (1 077 spans, `supportops-agent`, `llm-gateway`, `orders-api`, `kb-search`; semilla 42) y su verdad de campo en `RES`. Los atributos relevantes: `span.gen_ai.operation.name` (`invoke_agent|chat|execute_tool`), `span.gen_ai.tool.name`, `span.supportops.{ticket.id,status,attempt,customer.tier}`, `span.http.response.status_code`, `span.db.system`, `resource.service.name`. Los spans correctos están en `UNSET` (no `OK`).
    La corrección usa `traceql_mini` (el mini motor validado contra Tempo 3.1 en la lección: 18/18 consultas idénticas). Si tienes el stack, una celda final **verifica tus consultas contra Tempo real**.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución, lote pregrabado) |
    |---|---|---|---|
    | R1 | `QUERIES` Q1-Q8 | El conjunto de tickets que devuelve cada consulta coincide con el de la solución (nº y huella) | ≥ 7 de 8 exactas |
    | R2 | Buenas prácticas | Ninguna consulta usa atributos sin ámbito (`.attr`), `||` donde basta un selector, ni `status = ok` | 0 infracciones |
    | R3 | `FIXES` | Corrige 3 consultas con trampa (P1 `&&` dentro de llaves, P2 `status = ok`, P3 regex anclada): cada una devuelve lo que pide el enunciado | 3/3 |
    | R4 | `incident_timeline` | Recuento de trazas por intervalo de 60 s de Q1: `[0, 0, 3, 10, 2, 0, 0, 1, 0, 0]` y Q3 | exacto |
    | R5 | `METRICS` | 2 consultas TraceQL metrics (tasa de error por servicio con aritmética; p95 de `execute_tool` por herramienta) y 1 PromQL de span metrics (p95 por servicio) con la sintaxis esperada | 3/3 |
    | R6 | Verificación en vivo (opcional) | Con Tempo: tus Q1-Q8 devuelven los mismos tickets que en el mini motor | 8/8 (se omite sin stack) |

    > 📏 Calibración: los umbrales son lo que mide la solución sobre el lote pregrabado (semilla 42, tiempo simulado, sin dependencia de tu máquina). La huella de cada conjunto de tickets es `sha1(",".join(tickets ordenados))[:10]`.
    """.replace("BADGE_PLACEHOLDER", nb.badge()))
    code(boot("viz,otel"))
    code(IMPORTS + SETUP)
    code(LOAD.replace('CAP_FILE = REC / "capture_live.json.gz"\nCAP = json.load(gzip.open(CAP_FILE, "rt", encoding="utf-8")) if CAP_FILE.exists() else {}   # salidas de Tempo/Prometheus capturadas en vivo\nCAPTURED = {}\n', "").split("def cached")[0] + 'print(f"lote: {len(SPANS)} spans, {len({s[\'trace_id\'] for s in SPANS})} trazas, {RES.shape[0]} tickets")\n')
    md("""
    ## Paso 0 · Cómo se corrige y atributos disponibles
    `answer(query)` devuelve los tickets de las trazas que cumplen la consulta (con el mini motor); `fingerprint(tickets)` la huella de la rúbrica. Explora el lote antes de escribir nada.
    """)
    code('''
import hashlib
def answer(query, spans=SPANS):
    return tq.ticket_ids(spans, tq.search(spans, query))
def fingerprint(tickets):
    return [len(tickets), hashlib.sha1(",".join(sorted(tickets)).encode()).hexdigest()[:10]]
print("atributos de span más frecuentes:", collections.Counter(k for s in SPANS for k in s["attributes"]).most_common(14))
print("servicios:", collections.Counter(s["resource"]["service.name"] for s in SPANS))
answer('{ status = error }')[:5]
''')
    md("""
    ## Paso 1 · Las ocho preguntas
    **TODO 1.** Rellena `QUERIES` (cada valor es una consulta TraceQL **completa**; se evalúa por traza y se compara el conjunto de tickets):

    | # | Pregunta |
    |---|---|
    | Q1 | ¿Qué tickets tuvieron una llamada al **gateway LLM** con HTTP **5xx**? (span del servicio `llm-gateway`) |
    | Q2 | ¿Qué tickets recibieron un **429** y se **recuperaron con el reintento** (un `chat` con `attempt = 1` que no falló)? |
    | Q3 | ¿Qué tickets entraron en un **bucle de herramientas** (más de 3 spans `execute_tool`)? |
    | Q4 | ¿En qué tickets falló **`orders-api`** (span en error) y el agente terminó **`degraded`** (`supportops.status`)? |
    | Q5 | ¿Qué trazas **de más de 4 s** (raíz del agente) contienen una herramienta que tardó **más de 500 ms**? |
    | Q6 | ¿Qué tickets tienen una herramienta con una **consulta SQL de más de 100 ms** (PostgreSQL) como **descendiente**? |
    | Q7 | ¿En qué tickets un `chat` **falló** y tiene como **hermano** un `execute_tool` (mismo padre)? |
    | Q8 | ¿Qué tickets de clientes **premium** (`supportops.customer.tier`) tuvieron un span **en error** del servicio `llm-gateway`? |
    """)
    md(hint(1, "Q1: ámbito de recurso + atributo del span en el **mismo** selector (`&&` dentro de las llaves). Q2/Q4/Q5/Q8: son condiciones sobre **spans distintos** de la misma traza → dos selectores unidos con `&&` entre spansets."))
    md(hint(2, "Q3: agregado `| count() > 3` sobre `{ span.gen_ai.operation.name = \"execute_tool\" }`. Q6: `{ A } >> { B }` (descendiente: devuelve la derecha). Q7: `{ A } ~ { B }` (hermano). `status != error` incluye `UNSET`."))
    code('''
QUERIES: dict[str, str] = {
    # "Q1": '{ ... }',
}
def check_queries():
    for k, q in QUERIES.items():
        try:
            t = answer(q); print(f"{k}: {len(t)} tickets · {fingerprint(t)} · {q}")
        except Exception as e:
            print(f"{k}: ERROR {type(e).__name__}: {e}")
check_queries()
''')
    md("""
    ## Paso 2 · Tres trampas a corregir
    Cada consulta de `BROKEN` no responde a su enunciado. **TODO 2.** Escribe en `FIXES` la versión correcta de cada una.
    - **P1** «tickets con una SELECT de PostgreSQL **y** algún error en la traza» (devuelve 0).
    - **P2** «tickets con spans de `orders-api` que **no fallaron**» (casi no devuelve nada).
    - **P3** «todos los tickets con algún `chat`» (no devuelve nada).
    """)
    code('''
BROKEN = {"P1": '{ span.db.system = "postgresql" && status = error }',
          "P2": '{ status = ok && resource.service.name = "orders-api" }',
          "P3": '{ name =~ "chat" }'}
FIXES: dict[str, str] = {
    # "P1": '{ ... }',
}
for k, q in BROKEN.items():
    print(f"{k} (rota): {len(answer(q))} tickets · {q}")
for k, q in FIXES.items():
    print(f"{k} (arreglada): {len(answer(q))} tickets · {q}")
''')
    md("""
    ## Paso 3 · La forma temporal de un incidente
    La lección superpuso consultas y ventanas de incidente. **TODO 3.** Implementa `incident_timeline(spans, query, bin_s=60, n_bins=10)`: lista de **n_bins** enteros con el nº de **trazas** que cumplen `query`, agrupadas por el instante de inicio de la traza (`TraceHit.start_ns`) en intervalos de `bin_s` segundos desde `t0` = inicio del span más antiguo del lote. Una traza que empiece después del último intervalo se cuenta en el último.
    """)
    md(hint(1, "`hits = tq.search(spans, query)`; `t0 = min(s['start_unix_nano'] for s in spans)`; el índice es `int((h.start_ns - t0) / (bin_s * 1e9))` limitado a `n_bins - 1`."))
    code('''
def incident_timeline(spans, query, bin_s=60, n_bins=10):
    # TODO 3
    raise NotImplementedError("TODO 3")

try:
    q1 = QUERIES.get("Q1", '{ resource.service.name = "llm-gateway" && span.http.response.status_code >= 500 }')
    TL = incident_timeline(SPANS, q1); print(TL)
    fig, ax = plt.subplots(figsize=(8, 3)); ax.bar(range(len(TL)), TL, color=viz.PALETTE["traces"]); ax.set_xlabel("minuto"); ax.set_ylabel("trazas"); ax.set_title("Q1 en el tiempo"); plt.show()
except NotImplementedError as e:
    TL = None; print("Pendiente:", e)
''')
    md("""
    ## Paso 4 · Consultas para el dashboard
    **TODO 4.** Escribe en `METRICS`:
    - `"error_rate"`: TraceQL metrics, **tasa de spans con error por servicio** como razón de dos `rate()` agrupados `by (resource.service.name)` (aritmética, Tempo 3.1).
    - `"tool_p95"`: TraceQL metrics, **p95 de la duración de los spans `execute_tool`** por herramienta (`span.gen_ai.tool.name`) con `quantile_over_time`.
    - `"promql_p95"`: PromQL de **span metrics**: p95 de latencia por `service` con `histogram_quantile` sobre `traces_spanmetrics_latency_bucket`.
    """)
    code('''
METRICS: dict[str, str] = {
    # "error_rate": '...',
}
for k, q in METRICS.items(): print(k, "→", q)
''')
    md("""
    ## Autocomprobación (rúbrica)
    """)
    code(f'''
EXPECTED = {H!r}
BAD_STYLE = [re.compile(r"[{{&|(]\\s*\\.[a-zA-Z]"), re.compile(r"status\\s*=\\s*ok"), re.compile(r"\\}}\\s*\\|\\|\\s*\\{{")]
def check(name, fn):
    try:
        ok, detail = fn()
    except NotImplementedError:
        ok, detail = False, "pendiente"
    except Exception as e:
        ok, detail = False, f"{{type(e).__name__}}: {{e}}"
    print(("✅" if ok else "❌"), name, "·", detail); return ok
def r1():
    good = [k for k in [f"Q{{i}}" for i in range(1, 9)] if k in QUERIES and fingerprint(answer(QUERIES[k])) == EXPECTED[k]]
    return len(good) >= 7, f"{{len(good)}}/8 exactas: {{good}}"
def r2():
    bad = [(k, p.pattern) for k, q in QUERIES.items() for p in BAD_STYLE if p.search(q)]
    return bool(QUERIES) and not bad, f"{{len(bad)}} infracciones {{bad[:2]}}"
def r3():
    good = [k for k in ("P1", "P2", "P3") if k in FIXES and fingerprint(answer(FIXES[k])) == EXPECTED[k]]
    return len(good) == 3, f"{{len(good)}}/3 corregidas: {{good}}"
def r4():
    ok1 = incident_timeline(SPANS, '{{ resource.service.name = "llm-gateway" && span.http.response.status_code >= 500 }}') == [0, 0, 3, 10, 2, 0, 0, 1, 0, 0]
    ok2 = sum(incident_timeline(SPANS, '{{ span.gen_ai.operation.name = "execute_tool" }} | count() > 3')) == 4
    return ok1 and ok2, f"Q1 {{ok1}} · Q3 {{ok2}}"
def r5():
    m = METRICS; a = m.get("error_rate", ""); b = m.get("tool_p95", ""); c = m.get("promql_p95", "")
    ok_a = a.count("rate()") >= 2 and "by (resource.service.name)" in a and "status = error" in a and "/" in a
    ok_b = "quantile_over_time" in b and "execute_tool" in b and ".95" in b and "span.gen_ai.tool.name" in b
    ok_c = "histogram_quantile(0.95" in c and "traces_spanmetrics_latency_bucket" in c and "by (le, service)" in c
    return ok_a and ok_b and ok_c, f"error_rate {{ok_a}} · tool_p95 {{ok_b}} · promql_p95 {{ok_c}}"
def r6():
    if not HAVE_TEMPO:
        return True, "omitido (sin Tempo)"
    return live_check()
def live_check():
    b = run_batch(120, 42, live=True); inv = {{v: k for k, v in b.trace_ids.items()}}; time.sleep(25)
    same = 0
    for k, q in QUERIES.items():
        r = backends.tempo_search(q, minutes=30, limit=5000)
        tk = sorted(inv[t["traceID"].zfill(32)] for t in r.get("traces", []) if t["traceID"].zfill(32) in inv)
        same += tk == answer(q, b.spans)
    return same == len(QUERIES) == 8, f"{{same}}/8 consultas devuelven los mismos tickets en Tempo y en el mini motor"
results = [check("R1 Q1-Q8", r1), check("R2 buenas prácticas", r2), check("R3 FIXES", r3), check("R4 incident_timeline", r4), check("R5 METRICS", r5), check("R6 verificación en vivo", r6)]
print(f"\\n{{sum(results)}}/6 entregables correctos")
''')
    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    Solución de referencia completa (con ella se calibró la rúbrica). Si te atascas, abre antes las pistas 🪜.
    """)
    code('''
QUERIES = {
    "Q1": '{ resource.service.name = "llm-gateway" && span.http.response.status_code >= 500 }',
    "Q2": '{ span.http.response.status_code = 429 } && { span.supportops.attempt = 1 && status != error }',
    "Q3": '{ span.gen_ai.operation.name = "execute_tool" } | count() > 3',
    "Q4": '{ resource.service.name = "orders-api" && status = error } && { span.supportops.status = "degraded" }',
    "Q5": '{ trace:rootService = "supportops-agent" && trace:duration > 4s } && { span.gen_ai.operation.name = "execute_tool" && duration > 500ms }',
    "Q6": '{ name =~ "execute_tool.*" } >> { span.db.system = "postgresql" && duration > 100ms }',
    "Q7": '{ status = error && span.gen_ai.operation.name = "chat" } ~ { span.gen_ai.operation.name = "execute_tool" }',
    "Q8": '{ span.supportops.customer.tier = "premium" } && { resource.service.name = "llm-gateway" && status = error }',
}
FIXES = {
    "P1": '{ span.db.system = "postgresql" } && { status = error }',     # dos spansets de la misma traza, no un solo span con ambas cosas
    "P2": '{ status != error && resource.service.name = "orders-api" }',  # los spans correctos son UNSET, no OK
    "P3": '{ name =~ "chat.*" }',                                          # las regex están ancladas
}
def incident_timeline(spans, query, bin_s=60, n_bins=10):
    t0 = min(s["start_unix_nano"] for s in spans); out = [0] * n_bins
    for h in tq.search(spans, query):
        out[min(n_bins - 1, int((h.start_ns - t0) / (bin_s * 1e9)))] += 1
    return out
METRICS = {
    "error_rate": '({ status = error } | rate() by (resource.service.name)) / ({ } | rate() by (resource.service.name))',
    "tool_p95": '{ span.gen_ai.operation.name = "execute_tool" } | quantile_over_time(duration, .95) by (span.gen_ai.tool.name)',
    "promql_p95": 'histogram_quantile(0.95, sum by (le, service) (rate(traces_spanmetrics_latency_bucket[5m])))',
}
check_queries(); print(incident_timeline(SPANS, QUERIES["Q1"]))
''')
    code('''
results = [check("R1 Q1-Q8", r1), check("R2 buenas prácticas", r2), check("R3 FIXES", r3), check("R4 incident_timeline", r4), check("R5 METRICS", r5), check("R6 verificación en vivo", r6)]
print(f"\\n{sum(results)}/6 entregables correctos")
''')
    md("""
    ## Retos extra (nivel experto)

    1. **Estructurales avanzados (Tempo real):** reescribe Q6 con el operador de unión `&>>` para obtener herramienta **y** SELECT en un solo resultado y compara los dos resultados con `select(span.gen_ai.tool.name, duration)`.
    2. **Más barato:** para Q5 mide `inspectedBytes` de tres formulaciones equivalentes (con `trace:duration`, con `duration`, con agregado) usando la sección 4.2 de la lección y razona cuál usarías en un dashboard.
    3. **Cardinalidad:** estima con el generador de tráfico cuántas series crearía añadir `gen_ai.tool.name` como `dimension` del span-metrics y cuántas con `supportops.ticket.id`. ¿A partir de qué volumen de tickets/día te limitaría el `max_active_series`?
    4. **Extrapolación:** simula un muestreo de cabeza del 10 % (descarta el 90 % de las trazas del lote) y calcula cuánto subestima `rate()` frente al lote completo; relaciónalo con `with(extrapolate=true)` (Tempo 3.1, experimental).
    5. **Ampliar el mini motor:** añade el operador `!>>` (no descendiente) y valida contra Tempo en la batería de la lección; documenta los falsos positivos que la documentación advierte.
    """)
    md("""
    ## Reflexión

    - De tus ocho consultas, ¿cuáles migrarías a **span metrics + alertas** (módulo 16) y cuáles dejarías como **TraceQL de investigación**? ¿Por qué (coste por refresco, retención, cardinalidad)?
    - El punto ciego de la «hora del span»: ¿qué pasaría con tus consultas si el Collector reenviara spans con 10 minutos de retraso tras una caída? ¿Cómo lo detectarías?
    - ¿Qué atributos faltan en SupportOps para responder preguntas de **costes por cliente** (módulo 13) con TraceQL, sin tocar el generador de métricas?
    - Conexión con SupportOps: estas consultas son el *runbook* del incidente «proveedor LLM degradado» que escribirás en el módulo 16.
    """)
    nb.save(out)


if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    (COURSE / MOD / "README.md").write_text(readme(), encoding="utf-8")
    print("OK README", COURSE / MOD / "README.md")
    build_lesson()
    build_dashboard(check="--no-check" not in sys.argv)
    build_project()
