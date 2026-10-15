"""Genera el módulo 08_loki_logql: README, lección y proyecto (autor A3).
Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_08.py [--no-check]
Capturas en vivo para el modo degradado (stack arriba): SUPPORTOPS_CAPTURE=1 ejecutando la lección con un kernel con las dependencias.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "08_loki_logql"

SETUP = '''
import json, gzip, re, time, collections, inspect, logging, io
from supportops import backends, logql_mini as lq, loki_lab as ll
from supportops.loki_lab import LokiPusher, run_logs_batch, wait_for_logs, loki_range, loki_stats, logfmt
STACK = check_stack("core")
HAVE_LOKI = bool(STACK.up.get("loki")); HAVE_TEMPO = bool(STACK.up.get("tempo")); HAVE_GRAFANA = bool(STACK.up.get("grafana"))
print(f"\\nLoki en vivo: {HAVE_LOKI} · Tempo: {HAVE_TEMPO} · Grafana: {HAVE_GRAFANA}  ->  ",
      "modo COMPLETO" if HAVE_LOKI and HAVE_TEMPO else ("modo parcial (sin Tempo)" if HAVE_LOKI else "MODO DEGRADADO (datos y capturas pregrabados)"))
'''

LOAD = '''
REC = ROOT / "08_loki_logql" / "recorded"
DATA = json.load(gzip.open(REC / "logs_seed42.json.gz", "rt", encoding="utf-8"))     # logs (3 rutas de ingesta) y trazas de un lote pregrabado: 120 tickets, semilla 42
ENTRIES = lq.entries_from_payload(DATA["payload"]); RES = pd.DataFrame(DATA["results"]); SPANS = DATA["spans"]
CAP_FILE = REC / "capture_live.json.gz"
CAP = json.load(gzip.open(CAP_FILE, "rt", encoding="utf-8")) if CAP_FILE.exists() else {}   # salidas reales de Loki/Tempo/Grafana capturadas en vivo
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

print(f"lote pregrabado: {len(ENTRIES)} líneas de log en {len({e.labels['service_name'] for e in ENTRIES})} streams · {len(SPANS)} spans · capturas en vivo: {len(CAP)}")
'''


def readme() -> str:
    return """# Módulo 08 · Loki y LogQL: logs correlacionados con trazas

🟡 Intermedio · ≈ 4 h 30 min · Servicios: `docker compose --profile core up -d` (Collector, Tempo, Loki, Grafana; ≈ 0,4 GB). Funciona en **modo degradado** sin Docker (datos pregrabados + un mini motor de LogQL).

## Qué aprenderás
- **Arquitectura de Loki 3.x**: distributor, ingester, querier, query-frontend, compactor; almacenamiento (TSDB + chunks, esquema v13); modos de despliegue (el laboratorio usa el monolítico) y por qué Loki **no indexa el contenido** de las líneas, solo sus **etiquetas**.
- **Etiquetas frente a *structured metadata* frente a contenido de la línea**: qué va dónde (mapeo por defecto de OTLP a Loki), y un **experimento medido** de cardinalidad (`trace_id` como etiqueta frente a metadato).
- **Logging estructurado en Python**: `logging` con filtro de contexto de traza y formateador JSON; tres rutas de ingesta (OTLP vía Collector, JSON con un cliente de push escrito a mano, logfmt de acceso).
- **LogQL**: selectores, filtros de línea, parsers (`json`, `logfmt`), filtros de etiqueta, structured metadata, consultas de métricas (`rate`, `count_over_time`, `quantile_over_time` con `unwrap`), con un **mini motor** (≈ 200 líneas) validado contra Loki real.
- **Logs ↔ trazas**: de un `trace_id` a **todos** los logs de **todos** los servicios, y de una línea de log a su traza en Tempo (derived fields).
- **Coste de las consultas** (bytes procesados) y tres consultas de investigación sobre un lote con fallos inyectados.

## Archivos
| Archivo | Contenido |
|---|---|
| `08_loki_logql.ipynb` | Lección (teoría + parte a mano + Loki real + 10 gráficos + autoevaluación) |
| `08_proyecto_loki_logql.ipynb` | Proyecto: formateador JSON con `trace_id`, conversión a entradas de Loki (etiquetas bien elegidas), 4 consultas de investigación y 2 de métricas; corrección automática |
| `recorded/logs_seed42.json.gz` | Logs (660 líneas, 4 streams) y trazas del lote pregrabado |
| `recorded/capture_live.json.gz` | Respuestas reales de Loki/Tempo/Grafana capturadas con el stack (modo degradado) |
| `../stack/grafana/dashboards/08-logs-agente.json` | Dashboard aprovisionado (volumen y niveles, errores del gateway, latencia desde logs, logs con salto a traza) |

Código de apoyo (en `supportops/`): `logql_mini.py` (motor), `loki_lab.py` (cliente de push, instrumentores de logs, ayudas de consulta). Documentados en `_tools/INTERFACES.md`.

## Servicios necesarios
```bash
cd agent-observability-course/stack
docker compose --profile core up -d     # (con TEMPO_CONFIG=tempo-metrics.yaml si también quieres span metrics)
```
Loki tarda ~20 s en estar *ready*. Para parar y borrar datos: `docker compose --profile all down -v`.

## Lecturas
- Grafana Labs, documentación de Loki — repo `grafana/loki`, carpeta `docs/sources`: `get-started/architecture.md`, `get-started/labels/` (etiquetas, *structured metadata*, buenas prácticas), `query/log_queries/`, `query/metric_queries.md`, `query/bp-query.md`, `send-data/otel/`, `reference/loki-http-api.md`.
- Grafana Labs, notas de la versión Loki 3.7 — `docs/sources/release-notes/v3-7.md`.
- OpenTelemetry, *Logs Data Model* — <https://opentelemetry.io/docs/specs/otel/logs/data-model/>

## Siguiente
`09_metricas`: la tercera señal (Prometheus, RED, exemplars), y cómo se enlaza con lo que ya sabes consultar.
"""


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "08_loki_logql.ipynb", "Módulo 08 · Loki y LogQL")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 08 · Loki y LogQL: logs correlacionados con trazas

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | `core` (Collector, Tempo, Loki, Grafana). Modo degradado sin Docker: lote y capturas pregrabadas + mini motor LogQL |
    | **RAM aproximada** | ≈ 0,4 GB en reposo (stack) + < 500 MB el kernel |
    | **Prerrequisitos** | Módulos 02 (los tres pilares), 05 (Collector) y 07 (consultar trazas con TraceQL) |
    | **Hilo conductor** | Los cuatro servicios de SupportOps emiten logs por tres rutas; los unes con las trazas por `trace_id` |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Describir** la arquitectura de Loki 3.x y **explicar** por qué indexa solo etiquetas y qué consecuencia tiene para el coste y las consultas.
    2. **Decidir** qué dato va como **etiqueta**, como ***structured metadata*** o dentro de la **línea**, y **medir** el efecto de una mala elección (cardinalidad de streams).
    3. **Implementar** logging estructurado en Python (filtro de contexto de traza + formateador JSON) y un cliente mínimo de la API de ingesta de Loki.
    4. **Escribir** consultas LogQL de logs (selector, filtros de línea, parsers, filtros de etiqueta, metadatos) y de métricas (`rate`, `count_over_time`, `quantile_over_time` con `unwrap`).
    5. **Correlacionar** logs y trazas en ambos sentidos (`trace_id` → logs de todos los servicios; log → traza) y **componer** una línea de tiempo.
    6. **Estimar** el coste de una consulta (bytes procesados) y **reordenar** el pipeline para abaratarla.
    7. **Investigar** un lote con fallos inyectados con consultas de logs, y **reconocer** los límites de Loki (rechazo de metadatos grandes, series de métricas, timestamps).
    """)

    md("""
    ## 🔁 Conexión con módulos anteriores
    """)
    md(details("1 · (Módulo 02) ¿Qué dos campos de un log lo unen con una traza?",
               "`trace_id` y `span_id` del span activo cuando se emitió el log. En el modelo de datos de logs de OpenTelemetry son campos del *log record*, no atributos."))
    md(details("2 · (Módulo 05) ¿Qué exportador del Collector envía los logs a Loki en este laboratorio y a qué ruta?",
               "`otlp_http/loki` a `http://loki:3100/otlp` (ingesta OTLP nativa de Loki: añade `/v1/logs`). En el Collector 0.162 el nombre es `otlp_http`, no `otlphttp`."))
    md(details("3 · (Módulo 07) ¿Qué ventaja da `GET /api/traces/<id>` frente a una búsqueda TraceQL para un enlace «ver traza» desde un log?",
               "Es **inmediato** (la traza está en el live-store en cuanto llega); la búsqueda tarda ≈ 15-20 s en verla. Un `trace_id` en un log siempre se puede resolver por identificador."))

    code(boot("viz,otel"))
    code(IMPORTS + SETUP)
    code(LOAD)

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ---
    # 1 · Intuición: Prometheus para logs

    Una pila de logs «clásica» (Elasticsearch, Splunk) **indexa el contenido** de cada línea para poder buscar cualquier palabra rápido; el coste es un índice enorme. **Loki** hace la apuesta contraria, inspirada en Prometheus: **solo indexa un conjunto pequeño de etiquetas** por *stream* (p. ej. `service_name`, `deployment_environment_name`) y guarda las líneas comprimidas en *chunks*. Al consultar, el índice localiza los streams y Loki **lee y filtra las líneas por fuerza bruta** (en paralelo).

    | Si vienes de… | Analogía |
    |---|---|
    | **ML** | Un *feature store* indexado solo por la clave de la muestra (el stream) frente a escanear todas las columnas: el índice sirve para *saltar a la partición*, el resto es un scan columnar paralelo |
    | **Backend** | `grep` distribuido sobre ficheros organizados por directorios (`servicio/entorno/`) en lugar de una base de datos de búsqueda de texto |
    | **SRE** | Menos coste por GB almacenado y por línea ingerida a cambio de **disciplina con las etiquetas**: pocas, de baja cardinalidad y estables |

    El modelo de datos tiene tres lugares donde puede vivir un dato, con costes muy distintos:
    """)
    code('''
fig, ax = plt.subplots(figsize=(15, 5.2)); ax.set_xlim(0, 100); ax.set_ylim(0, 44); ax.axis("off"); ax.grid(False)
C = viz.PALETTE
ax.text(1, 41, "UNA LÍNEA DE LOG EN LOKI", fontsize=11, fontweight="bold")
viz.box(ax, 1, 24, 22, 11, "ETIQUETAS (índice)\\nservice_name\\ndeployment_environment_name", C["traces"], fontsize=8.5, bold=True)
viz.box(ax, 27, 24, 24, 11, "STRUCTURED METADATA\\ntrace_id · span_id · ticket_id\\n(no indexado, por línea)", C["profiles"], fontsize=8.5, bold=True)
viz.box(ax, 55, 24, 43, 11, "CONTENIDO DE LA LÍNEA (comprimido en chunks)\\n{\\"level\\":\\"warn\\",\\"msg\\":\\"error del proveedor LLM\\",\\"status\\":503}", C["logs"], fontsize=8.5, bold=True)
ax.text(1, 20, "baja cardinalidad · identifica la FUENTE", fontsize=8.5, color=C["traces"]); ax.text(27, 20, "alta cardinalidad permitida · filtros sin parsear", fontsize=8.5, color=C["profiles"]); ax.text(55, 20, "texto libre / JSON / logfmt · se filtra por fuerza bruta", fontsize=8.5, color=C["logs"])
steps = [("{selector}", "usa el ÍNDICE:\\nelige streams", C["traces"]), ("|= \\"texto\\"", "filtro de línea:\\nbarato, antes de parsear", C["logs"]), ("| json / logfmt", "parser: caro,\\nextrae etiquetas", C["metrics"]), ("| status >= 500", "filtro de etiqueta\\n(parseada o metadato)", C["profiles"]), ("rate(...) / sum by", "agregación:\\nserie temporal", C["error"])]
for i, (t, d, col) in enumerate(steps):
    x = 1 + i * 20
    viz.box(ax, x, 4, 17, 6, t, col, fontsize=8.5, bold=True); ax.text(x + 8.5, 1, d, ha="center", va="center", fontsize=7.8, color="#444")
    if i: viz.arrow(ax, (x - 2.6, 7), (x - 0.4, 7), color="#666")
ax.text(1, 13.5, "PIPELINE DE UNA CONSULTA LogQL (de izquierda a derecha, cada etapa descarta líneas)", fontsize=9.5, fontweight="bold")
plt.show()
''')
    md(observe("""
    - Solo el **selector** (`{...}`) usa el índice. Todo lo demás procesa líneas: por eso **cuanto antes descartes líneas, más barato** (filtros de línea antes de parsear) y por eso un selector ancho es caro.
    - La **structured metadata** (la columna morada) permite filtrar por `trace_id` **sin parsear** y sin crear streams: es el sitio correcto para identificadores de alta cardinalidad.
    - Lo que pongas como **etiqueta** multiplica los streams (cada combinación de valores es un stream y un *chunk* propio): esa es la decisión que más condiciona el coste de Loki (se mide en la sección 3).
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ---
    # 2 · Arquitectura de Loki 3.x

    | Componente | Qué hace |
    |---|---|
    | **Distributor** | Recibe las peticiones de ingesta, las valida y reparte los streams por *hash ring* a los ingesters |
    | **Ingester** | Acumula las líneas de cada stream en *chunks* en memoria (con WAL) y los vuelca al almacenamiento |
    | **Query frontend** | Divide cada consulta en subconsultas por intervalo de tiempo, las paraleliza y cachea resultados |
    | **Querier** | Ejecuta las subconsultas leyendo de ingesters (lo reciente) y del almacenamiento (lo antiguo) |
    | **Compactor** | Compacta el índice y aplica retención |
    | **Ruler** | Evalúa reglas de alerta y de grabación (LogQL) |
    | **Almacenamiento** | **Índice TSDB** (qué chunks contienen qué stream) + **chunks** comprimidos, todo en un único almacén (S3/GCS/Azure o sistema de ficheros en el laboratorio) |

    **Modos:** *monolítico* (un binario con todo; el del laboratorio), *HA monolítico* (varias réplicas del mismo binario) y *microservicios*. El modo *Simple Scalable Deployment* (SSD) está **deprecado** y se eliminará en Loki 4.0 (la documentación recomienda el HA monolítico). Un **esquema v13 + índice TSDB** es requisito de la *structured metadata* y de la ingesta OTLP nativa.
    """)
    code('''
fig, ax = plt.subplots(figsize=(15, 5.4)); ax.set_xlim(0, 100); ax.set_ylim(0, 46); ax.axis("off"); ax.grid(False)
C = viz.PALETTE; W, R = C["traces"], C["metrics"]
ax.set_title("Loki: ruta de escritura (azul) y de lectura (naranja)", loc="left")
col = viz.box(ax, 1, 33, 14, 8, "Collector\\n(OTLP) / push", C["neutral"], fontsize=8)
dis = viz.box(ax, 21, 33, 14, 8, "Distributor", W, fontsize=8.5, bold=True)
ing = viz.box(ax, 41, 33, 18, 8, "Ingester\\nchunks en memoria + WAL", W, fontsize=8, bold=True)
sto = viz.box(ax, 66, 30, 32, 14, "ALMACENAMIENTO ÚNICO\\nchunks comprimidos + índice TSDB\\n(laboratorio: /loki en disco)", C["profiles"], fontsize=8.5, bold=True)
viz.arrow(ax, viz.right(col), viz.left(dis), color=W); viz.arrow(ax, viz.right(dis), viz.left(ing), "hash(stream)", color=W); viz.arrow(ax, viz.right(ing), (65.6, 37), "flush", color=W)
qf = viz.box(ax, 1, 10, 17, 8, "Query frontend\\n(trocea y cachea)", R, fontsize=8, bold=True)
qr = viz.box(ax, 25, 10, 14, 8, "Querier", R, fontsize=8.5, bold=True)
viz.arrow(ax, viz.right(qf), viz.left(qr), color=R); viz.arrow(ax, viz.top(qr), (47, 32.6), "reciente", color=R); viz.arrow(ax, (39.3, 14), (75, 29.6), "antiguo (índice → chunks)", color=R, rad=-0.12)
cmp_ = viz.box(ax, 50, 8, 20, 8, "Compactor\\n(índice + retención)", C["neutral"], fontsize=8)
rul = viz.box(ax, 76, 8, 22, 8, "Ruler\\n(alertas LogQL)", C["logs"], fontsize=8)
viz.arrow(ax, viz.top(cmp_), (72, 29.6), color=C["neutral"], dashed=True); viz.arrow(ax, viz.left(rul), viz.right(qr), color=C["logs"], dashed=True, rad=0.3)
plt.show()
''')
    md("""
    ## 2.1 · Nuestra configuración (`stack/loki/loki.yaml`) línea a línea
    """)
    code('''
print((ROOT / "stack" / "loki" / "loki.yaml").read_text())
''')
    md("""
    | Clave | Qué controla | Por qué |
    |---|---|---|
    | `auth_enabled: false` | Un único tenant (`fake`) | Laboratorio; en producción cada equipo/cliente es un tenant (cabecera `X-Scope-OrgID`) |
    | `common.storage.filesystem` | Chunks y reglas en disco local | Sin S3 ni MinIO |
    | `replication_factor: 1`, `ring.kvstore: inmemory` | Sin réplicas, anillo en memoria | Un solo proceso |
    | `schema_config` (`store: tsdb`, `schema: v13`, `period: 24h`) | Formato de índice y chunk | **v13 es requisito** de structured metadata y OTLP nativo |
    | `limits_config.allow_structured_metadata: true` | Admite metadatos por línea | Sin él, Loki rechaza el payload OTLP |
    | `limits_config.volume_enabled: true` | Endpoints de volumen | Los usa Grafana Logs Drilldown |
    | `limits_config.retention_period: 168h` | 7 días de retención (aplicada por el compactor) | Laboratorio |

    Versión y módulos en ejecución (consulta en vivo a la API de Loki):
    """)
    code('''
def loki_get(path):
    return backends._get(backends._base("loki") + path)
def _build():
    import urllib.request
    b = backends._base("loki")
    bi = loki_get("/loki/api/v1/status/buildinfo")
    svc = urllib.request.build_opener(urllib.request.ProxyHandler({})).open(b + "/services", timeout=5).read().decode().split("\\n")
    return {"buildinfo": bi, "services": [l for l in svc if l.strip()]}
INFO = cached("loki_info", _build, live=HAVE_LOKI)
print({k: INFO["buildinfo"].get(k) for k in ("version", "revision", "goVersion")})
print("módulos del proceso (monolítico):", ", ".join(l.split(" => ")[0] for l in INFO["services"][:14]), "...")
''')

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ---
    # 3 · Etiquetas, *structured metadata* y línea: dónde vive cada dato

    | Lugar | Qué guardar | Cardinalidad | Se filtra con |
    |---|---|---|---|
    | **Etiqueta** (índice) | Qué **fuente** produce el log: entorno, región, servicio, *namespace* | **Baja y acotada** (decenas de valores; < 100 000 streams activos por tenant, según las guías) | `{service_name="..."}` (usa el índice) |
    | ***Structured metadata*** | Identificadores por línea que se consultan a menudo: `trace_id`, `span_id`, pod, `ticket_id` | **Alta** (sin índice) | `\\| trace_id="..."` (sin parsear) |
    | **Línea** | El mensaje y los campos de detalle | Libre | filtros de línea y parsers (`\\| json`, `\\| logfmt`) |

    **Mapeo por defecto de OTLP a Loki** (Loki 3.x): de los atributos de *resource*, **17 se convierten en etiquetas** (los puntos pasan a `_`): `cloud.availability_zone`, `cloud.region`, `container.name`, `deployment.environment.name`, `k8s.cluster.name`, `k8s.container.name`, `k8s.cronjob.name`, `k8s.daemonset.name`, `k8s.deployment.name`, `k8s.job.name`, `k8s.namespace.name`, `k8s.pod.name`, `k8s.replicaset.name`, `k8s.statefulset.name`, `service.instance.id`, `service.name`, `service.namespace`; el resto de atributos de resource, los de *scope* y los del *log record* van a **structured metadata**; el cuerpo es la línea; `trace_id`/`span_id`/`severity_text` también quedan como metadatos. Se puede cambiar con `limits_config.otlp_config`.
    """)

    md("""
    ## 3.1 · Experimento: `trace_id` como etiqueta frente a como metadato

    Enviamos **las mismas 300 líneas** (una por «traza» distinta) de dos maneras con el cliente de push que escribimos a mano (`LokiPusher`): en la primera, `trace_id` es una **etiqueta**; en la segunda, **structured metadata**. Luego miramos cuántos *streams* y *chunks* crea cada una y qué cuesta encontrar una traza concreta.
    """)
    code('''
print(inspect.getsource(LokiPusher.add)); print(inspect.getsource(LokiPusher.payload))
p = LokiPusher("http://localhost:3100"); p.add(1_788_253_200_000_000_000, "hola", {"service_name": "demo"}, {"trace_id": "abc"})
print(json.dumps(p.payload()))
''')
    code('''
def cardinality_experiment(n=300):
    run = int(time.time()) % 100000
    pl, pm = LokiPusher(), LokiPusher(); now = time.time_ns()
    for i in range(n):
        tid = f"{i:032x}"; ts = now - (n - i) * 10**8
        line = f"ticket procesado n={i} status={'error' if i % 10 == 0 else 'ok'}"
        pl.add(ts, line, {"service_name": f"cardlab-label-{run}", "trace_id": tid})
        pm.add(ts, line, {"service_name": f"cardlab-meta-{run}"}, {"trace_id": tid})
    pl.flush(); pm.flush()
    sel_l, sel_m = f'{{service_name="cardlab-label-{run}"}}', f'{{service_name="cardlab-meta-{run}"}}'
    wait_for_logs(sel_m, n, 40, verbose=False); wait_for_logs(sel_l, n, 40, verbose=False)
    now_s = int(time.time())
    def series(sel):
        return len(backends._get(backends._base("loki") + "/loki/api/v1/series", {"match[]": sel, "start": now_s - 3600, "end": now_s + 60}).get("data", []))
    def stats(sel):
        return backends._get(backends._base("loki") + "/loki/api/v1/index/stats", {"query": sel, "start": (now_s - 3600) * 10**9, "end": (now_s + 60) * 10**9})
    needle = f"{n // 2:032x}"
    def timed(q):
        t = []; 
        for _ in range(5):
            t0 = time.perf_counter(); r = loki_stats(q, 30); t.append((time.perf_counter() - t0) * 1000)
        return {"ms": float(np.median(t)), **r}
    return {"n": n, "series": {"etiqueta": series(sel_l), "metadato": series(sel_m)},
            "stats": {"etiqueta": stats(sel_l), "metadato": stats(sel_m)},
            "needle": {"etiqueta": timed(f'{{service_name="cardlab-label-{run}", trace_id="{needle}"}}'),
                       "metadato": timed(f'{{service_name="cardlab-meta-{run}"}} | trace_id="{needle}"')}}
CARD = cached("cardinality", cardinality_experiment, live=HAVE_LOKI)
print("streams creados:", CARD["series"], "· chunks / entradas:", {k: (v.get("chunks"), v.get("entries")) for k, v in CARD["stats"].items()})
print("buscar UNA traza →", {k: {"ms": round(v["ms"], 1), "líneas devueltas": v["lines_returned"], "líneas procesadas": v["lines_processed"]} for k, v in CARD["needle"].items()})
''')
    code('''
fig, axs = plt.subplots(1, 3, figsize=(15, 3.9)); cols = [viz.PALETTE["error"], viz.PALETTE["logs"]]; names = ["trace_id = ETIQUETA", "trace_id = METADATO"]
v = [CARD["series"]["etiqueta"], CARD["series"]["metadato"]]; axs[0].bar(names, v, color=cols); axs[0].set_title("streams creados"); [axs[0].text(i, x, str(x), ha="center", va="bottom") for i, x in enumerate(v)]
v = [int(CARD["stats"]["etiqueta"].get("chunks", 0)), int(CARD["stats"]["metadato"].get("chunks", 0))]; axs[1].bar(names, v, color=cols); axs[1].set_title("chunks (índice/stats)"); [axs[1].text(i, x, str(x), ha="center", va="bottom") for i, x in enumerate(v)]
v = [CARD["needle"]["etiqueta"]["lines_processed"] or 0, CARD["needle"]["metadato"]["lines_processed"] or 0]; axs[2].bar(names, v, color=cols); axs[2].set_title("líneas procesadas al buscar 1 traza"); [axs[2].text(i, x, str(x), ha="center", va="bottom") for i, x in enumerate(v)]
for a in axs: a.tick_params(axis="x", labelsize=8)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Etiqueta:** 300 streams (uno por `trace_id`) y, como mínimo, un chunk por stream: una sola línea por chunk. **Metadato:** **1 stream** con las 300 líneas juntas.
    - **Buscar una traza:** con la etiqueta, el índice localiza el stream y Loki procesa una línea; con el metadato, Loki **recorre las 300 líneas del stream** y filtra por `trace_id` (fuerza bruta). A 300 líneas es irrelevante; a millones de líneas por stream, el recorrido pesa. El *trade-off* es cómo Loki está pensado: **índice pequeño + scan paralelo**, y para identificadores se acepta el scan a cambio de no multiplicar streams.
    - **Por qué la etiqueta es peor en la práctica:** 300 streams son inocuos; **millones** (un `trace_id` por petición) arruinan el índice, el tamaño de los chunks y los límites (por defecto, 15 etiquetas y 100 000 streams activos como referencia por tenant). La documentación de Loki lo dice sin ambages: **no extraigas IDs efímeros como etiqueta**.
    """))

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ---
    # 4 · Logging estructurado en Python

    Un log útil para operar tiene **estructura** (campos con nombre), **contexto de traza** (`trace_id`, `span_id`) y **nivel**. En Python eso son dos piezas de la librería estándar: un **filtro** que añade el contexto del span activo a cada `LogRecord` y un **formateador** que emite una línea JSON.
    """)
    code('''
import datetime
from opentelemetry import trace as otel_trace
from supportops.telemetry import setup_telemetry

class TraceContextFilter(logging.Filter):
    """Añade trace_id y span_id (hex) del span activo a cada registro; vacíos si no hay span."""
    def filter(self, record):
        sc = otel_trace.get_current_span().get_span_context()
        record.trace_id = format(sc.trace_id, "032x") if sc.is_valid else ""
        record.span_id = format(sc.span_id, "016x") if sc.is_valid else ""
        return True

class JsonFormatter(logging.Formatter):
    """Una línea JSON por registro (también las excepciones: el traceback va dentro de UN solo campo)."""
    RESERVED = {"name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName", "processName", "process", "message", "taskName", "trace_id", "span_id"}
    def format(self, record):
        doc = {"ts": datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc).isoformat(timespec="milliseconds"), "level": record.levelname.lower(),
               "logger": record.name, "msg": record.getMessage(), **{k: v for k, v in record.__dict__.items() if k not in self.RESERVED}}
        if record.trace_id:
            doc.update(trace_id=record.trace_id, span_id=record.span_id)
        if record.exc_info:
            doc["exc"] = self.formatException(record.exc_info)
        return json.dumps(doc, ensure_ascii=False, default=str)

buf = io.StringIO(); h = logging.StreamHandler(buf); h.setFormatter(JsonFormatter()); h.addFilter(TraceContextFilter())
log = logging.getLogger("demo.soporte"); log.handlers[:] = [h]; log.setLevel(logging.INFO); log.propagate = False
tel = setup_telemetry("demo-logs", mode="memory", set_global=False); tracer = tel.tracer("demo")
log.info("fuera de cualquier span", extra={"ticket_id": "T-1"})
with tracer.start_as_current_span("invoke_agent demo") as sp:
    log.warning("error del proveedor LLM", extra={"ticket_id": "T-1", "status": 503, "attempt": 0})
    try:
        1 / 0
    except ZeroDivisionError:
        log.exception("fallo inesperado", extra={"ticket_id": "T-1"})
    esperado = format(sp.get_span_context().trace_id, "032x")
lines = buf.getvalue().strip().splitlines(); tel.shutdown()
for l in lines: print(l[:230])
print("\\n¿trace_id del log == trace_id del span?", json.loads(lines[1])["trace_id"] == esperado, "· sin span, sin trace_id:", "trace_id" not in json.loads(lines[0]))
''')
    md("""
    Reglas que separan un log útil de uno que molesta: **una línea por evento** (el *traceback* dentro de un campo, no varias líneas: Loki ve cada línea como una entrada), **nombres de campo estables** (`ticket_id`, `status`, `attempt`), **nivel** coherente con OpenTelemetry, **nunca datos personales** en el mensaje (ver módulo 20) y **cardinalidad en el contenido, no en las etiquetas**.

    ## 4.1 · Tres rutas de ingesta de los logs de SupportOps
    Ejecutamos un lote con trazas y logs por **tres rutas a la vez** (cada una con su `service_name`):

    | Ruta | `service_name` | Cómo llega | Cuerpo de la línea | Metadatos |
    |---|---|---|---|---|
    | **OTLP** (producción moderna) | `supportops-agent` | `OTelInstrumentor` → SDK → Collector → `/otlp` de Loki | el mensaje (`ticket recibido`...) | `trace_id`, `span_id`, `supportops_ticket_id`... (todos los atributos) |
    | **JSON clásico** | `supportops-agent-json` | `JsonLogInstrumentor` → `LokiPusher` (`/loki/api/v1/push`) | **JSON** con los campos | `trace_id`, `span_id`, `ticket_id` |
    | **logfmt de acceso** | `llm-gateway-access`, `orders-api-access`, `kb-search-access` | `AccessLogInstrumentor` → `LokiPusher` | **logfmt** (`method=POST route=... status=503 duration_ms=...`) | `trace_id` |
    """)
    code('''
if HAVE_LOKI:
    LB, PUSH = run_logs_batch(120, 42, live=True)
    LSPANS, LRES = LB.spans, pd.DataFrame(LB.results); LIDS = LB.trace_ids; LENTRIES = lq.entries_from_payload(PUSH.full_payload())
    n_json = sum(1 for e in LENTRIES if e.labels["service_name"] == "supportops-agent-json")
    wait_for_logs('{service_name="supportops-agent-json"}', int(0.98 * n_json), 60)
    wait_for_logs('{service_name="supportops-agent"}', 1, 60)
    print("enviado:", {s["stream"]["service_name"]: len(s["values"]) for s in PUSH.full_payload()["streams"]}, "· logs OTLP en Loki:", len(backends.loki_query('{service_name="supportops-agent"}', minutes=30, limit=5000)))
else:
    LB, LSPANS, LRES, LIDS, LENTRIES = None, SPANS, RES, DATA["trace_ids"], ENTRIES
    print("Sin Loki: se usa el lote pregrabado (las 3 rutas de ingesta, salvo las líneas OTLP que solo existen en vivo).")
''')
    code('''
def show(stream, k=2):
    es = [e for e in LENTRIES if e.labels["service_name"] == stream][:k]
    for e in es: print(f"  {stream:22s} labels={e.labels}  metadata={e.metadata}\\n     línea: {e.line[:170]}")
for s_ in ("supportops-agent-json", "llm-gateway-access"): show(s_, 1)
def otlp_sample():
    r = backends.loki_query('{service_name="supportops-agent"}', minutes=30, limit=2)
    return [{"labels": x["labels"], "line": x["line"]} for x in r[:2]]
OTLP = cached("otlp_sample", otlp_sample, live=HAVE_LOKI)
for x in OTLP[:1]: print("  OTLP (ruta nativa)    labels (índice + metadatos que Loki devuelve):", x["labels"], "\\n     línea:", x["line"])
''')
    md("""
    Fíjate en la línea OTLP: Loki devuelve **juntas** las etiquetas de índice y la *structured metadata* (en la consulta se comportan igual); el cuerpo es solo el mensaje. En las rutas JSON y logfmt los campos están **dentro de la línea** y hay que parsearlos con `| json` / `| logfmt`: más flexibles pero más caros que un metadato.
    """)

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ---
    # 5 · LogQL

    Una consulta de **logs** devuelve líneas: `{selector} | etapa | etapa ...`. Una consulta de **métricas** envuelve una de logs en una función de rango y devuelve series: `rate({...} | ... [1m])`. Para entender el pipeline construimos (`supportops/logql_mini.py`, ≈ 200 líneas) un motor de un **subconjunto** de las consultas de *logs* —selectores, filtros de línea, `json`/`logfmt`, filtros de etiqueta, metadatos— y lo contrastamos con Loki.

    ## 5.1 · Selectores, filtros de línea, parsers y filtros de etiqueta

    | Etapa | Sintaxis | Notas |
    |---|---|---|
    | Selector | `{service_name="x", env=~"a.*"}` | Operadores `= != =~ !~`; **obligatorio**, usa el índice; las regex están ancladas |
    | Filtro de línea | `\\|= "txt"` · `!= "txt"` · `\\|~ "re"` · `!~ "re"` | Contienen/no contienen texto o regex; los más baratos: ponlos **antes** de parsear |
    | Parser | `\\| json` · `\\| logfmt` · `\\| pattern "<ip> - <m>"` · `\\| regexp` · `\\| unpack` | Extraen etiquetas de la línea (`json` aplana objetos con `_`) |
    | Filtro de etiqueta | `\\| status >= 500` · `\\| level="error"` · `\\| a="x" and b>3` | Compara etiquetas de **stream, metadatos o parseadas**; números sin comillas |
    | Formato | `\\| line_format "{{.msg}}"` · `\\| label_format` · `\\| drop a` · `\\| keep a` | Reescritura (el mini motor no las implementa) |

    Estas son las consultas de la lección sobre los logs de SupportOps, evaluadas **en Loki** (o, sin stack, en el mini motor) y comparadas con el mini motor:
    """)
    code('''
fail = LRES[LRES.status.isin(["degraded", "error"])].ticket_id.tolist()
TID = LIDS[next(t for t in fail if t in LIDS)]                    # trace_id de un ticket que falló
JSON_ACC = 'service_name=~"supportops-agent-json|.+-access"'
BATTERY = [
    ("stream JSON completo", '{service_name="supportops-agent-json"}'),
    ("filtro de línea |=", '{service_name="supportops-agent-json"} |= "error del proveedor"'),
    ("excluir !=", '{service_name="orders-api-access"} != "status=200"'),
    ("regex |~", '{service_name=~".+-access"} |~ "status=(429|503)"'),
    ("json + etiqueta", '{service_name="supportops-agent-json"} | json | level="warn"'),
    ("json + numérico", '{service_name="supportops-agent-json"} | json | attempt >= 1'),
    ("logfmt + numérico", '{service_name="llm-gateway-access"} | logfmt | status >= 500'),
    ("logfmt + and", '{service_name="llm-gateway-access"} | logfmt | status >= 400 and route="/v1/chat/completions"'),
    ("logfmt duración", '{service_name=~".+-access"} | logfmt | duration_ms > 500'),
    ("metadato trace_id", '{' + JSON_ACC + '} | trace_id="' + TID + '"'),
    ("metadato + parser", '{' + JSON_ACC + '} | trace_id="' + TID + '" | logfmt | status >= 500'),
]
def loki_count(q):
    lines = backends.loki_query(q, minutes=30, limit=5000)
    mine = set(LIDS.values())
    return sum(1 for x in lines if x["labels"].get("trace_id") in mine)
def compare_logs():
    rows = []
    for lab_, q in BATTERY:
        mini = len(lq.query(LENTRIES, q)); live = loki_count(q)
        rows.append({"consulta": lab_, "logql": q, "mini": mini, "loki": live, "iguales": mini == live})
    return rows
EQ = pd.DataFrame(cached("equivalence_logs", compare_logs, live=HAVE_LOKI))
print(f"coinciden {EQ.iguales.sum()}/{len(EQ)} consultas (nº de líneas de ESTE lote)")
EQ[["consulta", "mini", "loki", "iguales"]].set_index("consulta")
''')
    code('''
fig, ax = plt.subplots(figsize=(12, 4.4)); x = np.arange(len(EQ)); w = 0.4
ax.bar(x - w/2, EQ.mini, w, color=viz.PALETTE["logs"], label="mini motor (Python)"); ax.bar(x + w/2, EQ.loki, w, color=viz.PALETTE["traces"], label="Loki 3.7 (real)")
for i, ok in enumerate(EQ.iguales): ax.text(i, max(EQ.mini[i], EQ.loki[i]) + 3, "✓" if ok else "≠", ha="center", color=viz.PALETTE["ok"] if ok else viz.PALETTE["error"], fontsize=12, fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(EQ.consulta, rotation=35, ha="right", fontsize=8.5); ax.set_ylabel("líneas devueltas"); ax.legend(); ax.set_title("La misma consulta LogQL, dos motores")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Las barras coinciden: el pipeline **selector → filtro de línea → parser → filtro de etiqueta** funciona como lo implementamos. Si alguna marca `≠`, es una sutileza que el mini motor no cubre (la tabla dice cuál): su función es **oráculo de pruebas** (el proyecto lo usa sin stack).
    - `| trace_id="..."` encuentra la línea **sin parsear nada** porque es metadato; combinado con `| logfmt | status >= 500` se filtra primero por traza (barato) y después se parsea.
    - Cada parser añade etiquetas **solo para esa consulta**; no cambian lo almacenado.
    """))

    md("""
    ## 5.2 · Consultas de métricas: de logs a series

    Envolviendo una consulta de logs en `rate(... [1m])`, `count_over_time(... [1m])`, `bytes_over_time` o `quantile_over_time(0.95, ... | unwrap campo [2m])` se obtienen series. `unwrap` convierte una etiqueta numérica (p. ej. `duration_ms`) en el valor a agregar. Después se agrega con `sum by (...)`, `topk`, etc., igual que en PromQL.
    """)
    code('''
Q_ERR = 'sum by (route) (rate({service_name=~".+-access"} | logfmt | status >= 500 [1m]))'
Q_P95 = 'quantile_over_time(0.95, {service_name=~".+-access"} | logfmt | unwrap duration_ms [2m]) by (service_name)'
Q_LVL = 'sum by (level) (count_over_time({service_name="supportops-agent-json"} | json [1m]))'
def ser(q, step=15):
    return {k: [list(p) for p in v] for k, v in loki_range(q, 15, step).items()}
M_ERR = cached("m_err", lambda: ser(Q_ERR), live=HAVE_LOKI); M_P95 = cached("m_p95", lambda: ser(Q_P95), live=HAVE_LOKI); M_LVL = cached("m_lvl", lambda: ser(Q_LVL), live=HAVE_LOKI)
def plot_series(ax, s, title, ylabel, only=None):
    allp = [p for v in s.values() for p in v]
    if not allp:
        ax.set_title(title + " (sin datos)", fontsize=10, loc="left"); return
    t0 = min(p[0] for p in allp)
    for k, pts in sorted(s.items()):
        if only and not only(k): continue
        ax.plot([(t - t0) / 60 for t, _ in pts], [v for _, v in pts], label=k.replace("route=", "").replace("service_name=", "").replace("level=", ""), lw=1.8)
    ax.set_title(title, fontsize=10, loc="left"); ax.set_xlabel("minutos"); ax.set_ylabel(ylabel); ax.legend(fontsize=7.5)
fig, axs = plt.subplots(1, 3, figsize=(17, 4.2))
plot_series(axs[0], M_ERR, "errores 5xx/s por ruta (logfmt)", "eventos/s"); plot_series(axs[1], M_P95, "p95 de duration_ms por servicio (unwrap)", "ms"); plot_series(axs[2], M_LVL, "líneas por nivel (json)", "líneas/min")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Errores 5xx/s por ruta:** aparecen los 503 de `/v1/chat/completions` (proveedor degradado) y los de `/orders/{id}` (`orders-api` roto): la misma historia que contaron las trazas en el módulo 07, ahora **desde logs** (y con la hora del evento: los logs se enviaron con el reloj simulado del agente).
    - **p95 por servicio** (`unwrap duration_ms`): latencia desde logs de acceso; es una estimación con muy pocos eventos por ventana, ruidosa (en producción, con miles de eventos, es una buena métrica de apoyo, pero el histograma de métricas del módulo 09 es la fuente correcta para SLOs).
    - **Líneas por nivel:** `warn` (reintentos, errores del proveedor) frente a `info`. Un cambio brusco en la proporción es una señal barata de que algo ha cambiado.
    """))
    code('''
# Validación a mano: ¿coincide count_over_time de Loki con contar las líneas con pandas? (5xx por ruta, intervalos de 1 min sin solaparse)
HAND = collections.Counter()
for e in LENTRIES:
    if e.labels["service_name"].endswith("-access"):
        f = lq.parse_logfmt(e.line)
        if int(f["status"]) >= 500: HAND[f["route"]] += 1
def loki_total():
    s = loki_range('sum by (route) (count_over_time({service_name=~".+-access"} | logfmt | status >= 500 [1m]))', 15, 60)
    return {k.replace("route=", ""): sum(v for _, v in pts) for k, pts in s.items()}
LT = cached("count_validation", loki_total, live=HAVE_LOKI)
print(pd.DataFrame({"a mano (pandas/Python)": dict(HAND), "Loki count_over_time (1 min, paso 1 min)": LT}).fillna(0).astype(int))
''')

    # ------------------------------------------------------------------------------------------------ 6
    md("""
    ---
    # 6 · Logs ↔ trazas

    El motivo de todo el trabajo anterior: partiendo de **una traza lenta o fallida** (módulo 07) quieres **todos los logs de esa petición, de todos los servicios**; y partiendo de **una línea de log** quieres su traza. Ambos saltos usan el mismo `trace_id`:
    - **Traza → logs:** `{deployment_environment_name="lab"} | trace_id="<id>"` (sin parsear, sobre todos los streams del entorno). Grafana lo hace con `tracesToLogsV2` (aprovisionado en el datasource de Tempo).
    - **Log → traza:** el *derived field* del datasource de Loki convierte el metadato `trace_id` en un enlace a Tempo; y `GET /api/traces/<id>` funciona **al instante**.
    """)
    code('''
def correlate():
    t = backends.tempo_trace(TID)
    n_sp = sum(len(ss["spans"]) for b in (t.get("batches") or t.get("resourceSpans") or []) for ss in b.get("scopeSpans", b.get("instrumentationLibrarySpans", [])))
    lines = backends.loki_query('{deployment_environment_name="lab"} | trace_id="%s"' % TID, minutes=30, limit=500)
    return {"spans_en_tempo": n_sp, "logs": [{"ts": x["timestamp_ns"], "service": x["labels"].get("service_name"), "line": x["line"][:140]} for x in lines]}
COR = cached("correlation", correlate, live=HAVE_LOKI and HAVE_TEMPO)
print(f"trace_id {TID}: {COR['spans_en_tempo']} spans en Tempo y {len(COR['logs'])} líneas de log en {len({l['service'] for l in COR['logs']})} streams")
for l in COR["logs"][:12]: print(f"  {l['service']:24s} {l['line']}")
''')
    code('''
tr_spans = [s for s in LSPANS if s["trace_id"] == TID] if HAVE_LOKI else [s for s in SPANS if s["trace_id"] == TID]
t0 = min(s["start_unix_nano"] for s in tr_spans)
fig = plt.figure(figsize=(15, 6.4)); gs = fig.add_gridspec(2, 1, height_ratios=[1.5, 1], hspace=0.35)
ax1 = fig.add_subplot(gs[0]); viz.waterfall(tr_spans, ax=ax1, title="TRAZA (Tempo): spans de los 4 servicios")
ax2 = fig.add_subplot(gs[1], sharex=None)
streams = sorted({l["service"] for l in COR["logs"]}); col = {s_: c for s_, c in zip(streams, plt.cm.tab10.colors)}
for l in COR["logs"]:
    ax2.scatter((l["ts"] - t0) / 1e9, streams.index(l["service"]), s=70, color=col[l["service"]], edgecolor="white", zorder=3)
    ax2.text((l["ts"] - t0) / 1e9, streams.index(l["service"]) + 0.18, l["line"][:44], fontsize=6.3, rotation=18, va="bottom")
ax2.set_yticks(range(len(streams))); ax2.set_yticklabels(streams, fontsize=8); ax2.set_ylim(-0.6, len(streams) - 0.1); ax2.set_xlabel("segundos desde el inicio de la traza"); ax2.set_title("LOGS (Loki): `| trace_id=...` en todos los streams", loc="left")
plt.show()
''')
    md(observe("""
    - Una **sola consulta** reúne los logs de la petición de los cuatro servicios; ordenados por tiempo cuentan la misma historia que la cascada: dónde se reintentó, qué devolvió el gateway, qué falló en `orders-api`.
    - Cada línea de log cae **dentro** del intervalo del span que la emitió (mismo reloj simulado y `span_id` en el metadato): la traza da la **estructura y los tiempos**, el log da el **detalle en palabras**.
    - El mismo `trace_id` aparece en las **tres rutas** de ingesta (OTLP, JSON, logfmt): por eso conviene normalizarlo en un único nombre de metadato.
    """))
    code('''
def ds_cfg():
    lk = backends.grafana_api("/api/datasources/uid/loki")["jsonData"]; tp = backends.grafana_api("/api/datasources/uid/tempo")["jsonData"]
    return {"derivedFields": lk.get("derivedFields"), "tracesToLogsV2": tp.get("tracesToLogsV2")}
DS = cached("grafana_correlation", ds_cfg, live=HAVE_GRAFANA)
print("Loki → Tempo (derived field):", json.dumps(DS["derivedFields"], ensure_ascii=False)[:330])
print("Tempo → Loki (tracesToLogsV2):", json.dumps({k: DS["tracesToLogsV2"][k] for k in ("datasourceUid", "filterByTraceID", "customQuery", "query")}, ensure_ascii=False))
''')

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ---
    # 7 · Cuánto cuesta una consulta

    Loki devuelve en cada respuesta las **estadísticas de ejecución** (`data.stats.summary`: bytes y líneas procesados). Comparamos formulaciones equivalentes de «líneas de error del agente»: **selector ancho frente a estrecho** y **filtro de línea antes del parser**.
    """)
    code('''
VQ = [("selector ancho · | json", '{service_name=~".+"} | json | level="warn"'),
      ("selector estrecho · | json", '{service_name="supportops-agent-json"} | json | level="warn"'),
      ("estrecho · |= antes de json", '{service_name="supportops-agent-json"} |= "warn" | json | level="warn"'),
      ("estrecho · |= \\"error del\\" (sin parser)", '{service_name="supportops-agent-json"} |= "error del proveedor"'),
      ("estrecho · metadato trace_id", '{service_name="supportops-agent-json"} | trace_id="' + TID + '"')]
def costs():
    return {lab_: loki_stats(q, 30) for lab_, q in VQ}
CO = cached("costs", costs, live=HAVE_LOKI)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 3.8)); labs = list(CO)
a1.barh(labs, [CO[k]["bytes_processed"] / 1024 for k in labs], color=viz.PALETTE["logs"]); a1.invert_yaxis(); a1.set_xlabel("KiB procesados"); a1.set_title("bytes procesados por la consulta")
a2.barh(labs, [CO[k]["lines_returned"] for k in labs], color=viz.PALETTE["traces"]); a2.invert_yaxis(); a2.set_xlabel("líneas devueltas"); a2.set_title("resultado (lo que sí quieres)"); a2.set_yticklabels([])
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Selector ancho (`{service_name=~".+"}`)** procesa muchos más bytes que el estrecho **para el mismo resultado útil**: cada stream extra se lee entero. La regla de oro es la de siempre: **estrecha primero con etiquetas**.
    - Un **filtro de línea** (`|= "warn"`) antes del parser descarta líneas **antes** de parsear JSON: los *bytes* procesados son los mismos (Loki lee los chunks), pero se ahorra CPU del parser; en volúmenes grandes esa diferencia es la que separa segundos de minutos (guía de la documentación: filtros de línea primero).
    - Con pocas líneas las diferencias son pequeñas; los **bytes procesados** son el indicador que debes mirar (Grafana Explore lo muestra en «Query inspector»).
    """))

    # ------------------------------------------------------------------------------------------------ 8
    md("""
    ---
    ## 🏭 En producción

    - **Grafana Labs** diseña Loki alrededor de la apuesta «índice pequeño + chunks en almacenamiento de objetos»: la documentación apunta como referencia a **menos de 100 000 streams activos por tenant** (y menos de un millón en 24 h) incluso para tenants enormes (> 10 TB/día) y a **etiquetas de decenas de valores** como mucho. El coste de Loki es, sobre todo, **disciplina de etiquetas**.
    - **OTLP nativo:** desde Loki 3.0 se ingiere OpenTelemetry directamente (`/otlp`); los atributos de *resource* mapean bien a etiquetas y el resto a *structured metadata* (por eso el Collector necesita solo `otlphttp` y no un exportador específico de Loki).
    - **Despliegue:** el modo *Simple Scalable* está deprecado (se elimina en 4.0); la recomendación es el **HA monolítico** para la mayoría y microservicios para los muy grandes. Los charts de Helm de Loki los mantiene desde 2026 la comunidad (`grafana-community/helm-charts`, según las notas de la 3.7).
    - **Bloom filters** (experimentales, a partir de Loki 3.3, para grandes clientes de > 75 TB/mes) usan *structured metadata*: otra razón para guardar ahí los identificadores.
    - **Patrón de equipo:** logs estructurados (JSON/logfmt) o OTLP, **un esquema de campos acordado** (`trace_id`, `span_id`, `service.name`, `ticket_id`...), derived fields hacia Tempo y trazas con `tracesToLogs` hacia Loki; alertas desde el *ruler* sobre `rate(... | json | level="error")` solo para señales que no existan como métrica.
    """)

    md("""
    ## 🧠 Secretos de la élite

    1. **`trace_id` como etiqueta es el error nº 1.** Medido: 300 trazas → 300 streams (y ≥ 300 chunks de una línea) frente a 1 stream con metadato. A escala crea millones de streams, chunks diminutos y un índice inservible; la guía oficial: *no extraigas IDs efímeros (trace ID, order ID) como etiqueta*.
    2. **La structured metadata se mezcla con las etiquetas en el resultado**, y eso rompe consultas de métricas: `maximum of series (50000) reached` si agregas sin `by (...)`. Usa `by`, o `| keep service_name` / `| drop trace_id` antes de la función de rango (documentación de *structured metadata*).
    3. **Un atributo grande puede hacer que Loki rechace TODA la línea.** Por defecto cada línea admite hasta **64 KB** y **128 entradas** de metadatos; `exception.stacktrace` como atributo de un log OTLP suele pasarse: HTTP 400 no reintentable y `loki_discarded_samples_total{reason="structured_metadata_too_large"}`. Mitiga moviendo el stacktrace al cuerpo con el procesador `transform` del Collector (receta en la documentación) o descartándolo con `limits_config.otlp_config`.
    4. **No hagas del nivel una etiqueta dinámica.** La guía oficial: `{app="loki"} |= "level=error"` suele ir igual de rápido que `{app="loki", level="error"}`, y la etiqueta parte un stream en hasta 5, con 5× más chunks. En Loki 3.x hay además `detected_level` (descubrimiento automático, `discover_log_levels`) que usa Logs Drilldown.
    5. **Filtros de línea antes que parsers; selector estrecho antes que filtros.** Cada etapa procesa líneas; un `| json` sobre millones de líneas es caro, un `|= "error"` previo lo evita casi todo.
    6. **El push JSON exige marcas de tiempo como cadenas** (nanosegundos en `string`); con un número, 400. El tercer elemento del par `[ts, línea, {metadatos}]` solo admite cadenas y no admite objetos anidados. Es lo que hace nuestro `LokiPusher` y lo que se tuerce al escribir un cliente propio.
    7. **Loki rechaza muestras muy antiguas** (`reject_old_samples`, una semana por defecto) y **muy futuras**; los desfases del reloj del emisor se pagan en logs perdidos. Nuestro laboratorio envía el tiempo simulado de «ahora - 10 min»: válido; el de 2026-09-01 de las muestras pregrabadas, no.
    8. **`service_name` se deduce si no lo pones:** Loki toma el primero no vacío de una lista (`service`, `app`, `application`, `app_name`, `name`, `container`, `job`...) o `unknown_service`; relevante para Logs Drilldown. Acuerda el nombre en el Collector, no lo dejes a la deducción.
    9. **Los logs no sustituyen a las métricas.** `quantile_over_time ... unwrap` sirve para investigar y para una alerta puntual, pero cuesta una lectura de logs en cada evaluación; las señales permanentes (tasa de error, latencia) deben ser métricas (módulo 09).
    """)

    md("""
    ## ⚠️ Errores comunes

    - Meter `ticket_id`, `trace_id`, `customer_id` o rutas con IDs como etiquetas.
    - Selectores del tipo `{service_name=~".+"}` en paneles que se refrescan cada 10 s.
    - `| json` sobre todo el stream sin un filtro de línea previo.
    - Logs multilínea (un *traceback* en 30 líneas = 30 entradas): serializa en una línea.
    - Mensajes con texto del cliente (PII) en el cuerpo: lo veremos en el módulo 20.
    - Confundir el **tiempo del log** (el del evento) con el **tiempo de ingesta**: las consultas de rango usan el primero.
    - Esperar que `rate()` de Loki sea una métrica «gratis»: es una consulta sobre logs en cada evaluación.
    """)

    md("""
    ## Autoevaluación
    """)
    md(details("1 · (Cálculo) Un servicio emite 2 000 líneas/s de 300 bytes y se guardan 14 días. ¿Cuántos GB de logs sin comprimir? Si la compresión media de chunks es ≈ 8×, ¿cuánto ocupa? (supuestos)",
               "2 000 × 300 B = 600 KB/s ≈ 51,8 GB/día; × 14 ≈ **725 GB**. Con compresión 8× (supuesto, depende del contenido) ≈ **91 GB**. La lección: el coste de Loki sigue al volumen de **líneas**, no al número de etiquetas; pero etiquetas mal elegidas fragmentan los chunks y empeoran esa compresión."))
    md(details("2 · (Diagnóstico) Tu consulta de métricas `sum(rate({service_name=\"agente\"} | json [1m]))` funciona, pero `rate({service_name=\"agente\"} | json [1m])` (sin `sum`) falla con «maximum of series reached». ¿Por qué?",
               "Sin agregación, cada combinación de etiquetas **resultante** es una serie; tras `| json` hay una etiqueta por campo del JSON y, además, la *structured metadata* (`trace_id`, `ticket_id`...) se une a las etiquetas: miles de series. Con `sum` (o `sum by (level)`) se colapsan; también valen `| keep level` / `| drop trace_id`."))
    md(details("3 · (Diagnóstico) Alguien añade `request_id` como etiqueta «para buscar rápido». A las dos semanas, las consultas son lentas y Loki rechaza peticiones. ¿Qué ha pasado y cuál es la alternativa?",
               "Cada `request_id` crea un stream y un chunk propios (millones): índice enorme, chunks de una línea, límites de streams activos superados. Alternativa: **structured metadata** (`| request_id=\"...\"`, sin índice, busca por fuerza bruta dentro del stream) o dejarlo en la línea y filtrar con `|= \"request_id=abc\"`."))
    md(details("4 · (Transferencia) Tu aplicación Java ya escribe logs JSON a stdout en Kubernetes. ¿Qué cambias para que Loki los correlacione con trazas sin tocar el código?",
               "Añadir el **`trace_id`/`span_id`** al log desde el contexto de OpenTelemetry (agente de Java con el *log correlation* de OTel/MDC) y recogerlos con Alloy/Collector: etiquetas del pod como índice (`k8s_namespace_name`, `service_name`), `trace_id` como **structured metadata** (`stage.structured_metadata`) y derived field hacia Tempo en Grafana."))
    md(details("5 · (Cálculo) El compañero propone `level` como etiqueta (5 valores) sobre 400 servicios. ¿Cuántos streams como máximo y por qué se desaconseja con volumen bajo?",
               "400 × 5 = **2 000 streams** (más los demás ejes). Con poco volumen cada stream produce chunks muy pequeños (se cierran por inactividad antes de llenarse), con más sobrecarga de lectura que beneficio: la guía recomienda filtros de línea (`|= \"level=error\"`) y, si hace falta, `detected_level`."))
    md(details("6 · ¿Qué diferencia hay entre `{...} | trace_id=\"x\"` y `{..., trace_id=\"x\"}`? ¿Cuándo funcionaría la segunda?",
               "La primera filtra por **metadato** (sin índice; Loki recorre las líneas del stream). La segunda exige que `trace_id` sea una **etiqueta de índice**: solo funciona si se ingirió así (la mala práctica del experimento). Con metadato, la segunda forma no devuelve nada."))
    md(details("7 · (Transferencia) Quieres una alerta «tasa de errores 5xx del gateway > 2 %». ¿Con LogQL o con métricas? ¿Qué cambia si no existe aún la métrica?",
               "Lo correcto es una **métrica** (contador de peticiones con `status`, módulo 09; barata de evaluar y con histórico). Si aún no existe, una regla del *ruler* con `sum(rate({...} | logfmt | status >= 500 [5m])) / sum(rate({...}[5m]))` sirve como puente, sabiendo que lee logs en cada evaluación."))
    md(details("8 · ¿Por qué el `trace_id` de un log se resuelve al instante en Tempo (`/api/traces/<id>`) pero «las trazas con error del último minuto» tardan más en aparecer?",
               "El live-store de Tempo sirve por identificador lo que acaba de llegar; la **búsqueda** espera a que la traza se considere completa (`max_trace_idle`) y esté indexada (≈ 15-20 s medidos en el módulo 07)."))

    md("""
    ## Referencias

    - Grafana Labs, documentación de Loki (repo `grafana/loki`, `docs/sources`): *Loki overview*, *Loki architecture* (`get-started/`), *Understand labels*, *What is structured metadata*, *Label best practices*, *Cardinality* (`get-started/labels/`).
    - Grafana Labs, *Log queries* (`query/log_queries/_index.md`), *Metric queries* (`query/metric_queries.md`), *Query best practices* (`query/bp-query.md`) — mismo repo.
    - Grafana Labs, *Ingesting logs to Loki using OpenTelemetry Collector* (`send-data/otel/`, incluida la sección *Handle large attributes such as stack traces*) — mismo repo.
    - Grafana Labs, *Loki HTTP API* (`/loki/api/v1/push`, `/otlp/v1/logs`, `query_range`, `series`, `index/stats`) — `docs/sources/reference/loki-http-api.md`.
    - Grafana Labs, notas de la versión *Loki 3.7* — `docs/sources/release-notes/v3-7.md`.
    - OpenTelemetry, *Logs Data Model* — <https://opentelemetry.io/docs/specs/otel/logs/data-model/>.
    - Código del módulo: `supportops/logql_mini.py`, `supportops/loki_lab.py`, `supportops/tests/test_logql_mini.py`.
    """)

    code('''
import os
if os.environ.get("SUPPORTOPS_CAPTURE") == "1" and CAPTURED:                 # solo al regenerar las capturas del modo degradado (ver build_08.py)
    with gzip.open(CAP_FILE, "wt", encoding="utf-8") as f:
        json.dump({**CAP, **CAPTURED}, f)
    print("capturas guardadas:", sorted(CAPTURED))
''')
    nb.save(out)


# =====================================================================================================================
def build_dashboard(check: bool = True) -> None:
    sys.path.insert(0, str(COURSE))
    from supportops import dashkit as dk  # noqa: PLC0415

    d = dk.Dashboard("logs-agente", "08 · Logs del agente (Loki)", tags=["curso", "loki", "logql"], refresh="10s",
                     description="Logs de SupportOps por tres rutas de ingesta (OTLP, JSON, logfmt) y su correlación con trazas.")
    d.add(dk.text("Cómo leerlo", "Streams: `supportops-agent` (OTLP), `supportops-agent-json` (JSON) y `*-access` (logfmt de `llm-gateway`, `orders-api`, `kb-search`). "
                  "En las líneas, el metadato **trace_id** abre la traza en Tempo (derived field). Variable `trace_id` para ver los logs de una petición.", w=24, h=3))
    d.variable(dk.var_textbox("trace_id", label="trace_id", default=""))
    d.row("Volumen y niveles")
    d.add(dk.timeseries("líneas por servicio", [dk.loki('sum by (service_name) (count_over_time({deployment_environment_name="lab"}[$__auto]))', "{{service_name}}")], unit="short", w=12, h=8,
                        description="Volumen de logs por stream (índice: service_name). Una subida brusca suele ser un bucle de errores."),
          dk.timeseries("líneas por nivel (agente JSON)", [dk.loki('sum by (level) (count_over_time({service_name="supportops-agent-json"} | json [$__auto]))', "{{level}}")], unit="short", w=12, h=8,
                        description="Proporción info/warn/error del agente (parser json)."))
    d.row("Errores y latencia desde logs de acceso (logfmt)")
    d.add(dk.timeseries("5xx por ruta", [dk.loki('sum by (route) (rate({service_name=~".+-access"} | logfmt | status >= 500 [5m]))', "{{route}}")], unit="ops", w=12, h=8,
                        description="Errores 5xx/s por ruta a partir de logs de acceso. Las señales permanentes deberían ser métricas (módulo 09)."),
          dk.timeseries("p95 de duration_ms por servicio", [dk.loki('quantile_over_time(0.95, {service_name=~".+-access"} | logfmt | unwrap duration_ms [$__auto]) by (service_name)', "{{service_name}}")], unit="ms", w=12, h=8,
                        description="Latencia p95 desde logs (unwrap de duration_ms). Estimación; la fuente correcta para SLOs son los histogramas."))
    d.row("Logs")
    d.add(dk.logs("Errores y avisos del agente", '{service_name="supportops-agent-json"} | json | level=~"warn|error"', w=24, h=9,
                  description="Líneas JSON con nivel warn/error. Abre una línea y pulsa «Ver traza en Tempo»."),
          dk.logs("Todos los logs de una petición (variable trace_id)", '{deployment_environment_name="lab"} | trace_id="$trace_id"', w=24, h=9,
                  description="Rellena la variable trace_id con el de una traza (módulo 07): reúne los logs de todos los servicios."))
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "08-logs-agente.json")
    print("OK dashboard", path, "· lint:", dk.lint(d.to_dict()) or "sin avisos")
    if check:
        try:
            for r in dk.query_check(d.to_dict(), overrides={"trace_id": "00000000000000000000000000000000"}):
                print(("  ok " if r["ok"] else "  ERR"), r["panel"], "| filas:", r["rows"], r["error"][:120])
        except Exception as e:  # noqa: BLE001
            print("  (Grafana no disponible: dashboard sin validar)", str(e)[:80])


def build_project() -> None:
    nb, out = nb_for(MOD, "08_proyecto_loki_logql.ipynb", "Proyecto 08 · Pipeline de logs correlacionados con trazas")
    md, code = nb.md, nb.code
    EXP = {"I1": [73, "ae65d50444"], "I2": [32, "4a85a07b13"], "I3": [8, "5e7147de48"], "I4": [13, "35c3a13bf8"]}
    BINS = [1, 0, 6, 17, 7, 4, 2, 4, 0, 0]
    md("""
    BADGE_PLACEHOLDER

    # Proyecto 08 · Logs de SupportOps correlacionados con trazas: del formato a la investigación

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Opcionales (`core`) para la verificación contra Loki; la corrección usa el mini motor LogQL y funciona **sin Docker** (Colab) |
    | **RAM aproximada** | < 500 MB (+ ≈ 0,4 GB con el stack) |
    | **Prerrequisitos** | Lección `08_loki_logql` y proyecto 07 (el `trace_id` que enlaza ambos mundos) |
    | **Conexión** | Cierra el ciclo «traza → logs → causa» del hilo conductor. El formato de log que diseñes es el que usarán el módulo 20 (redacción de PII) y el 21 (mesa de incidentes) |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Los logs actuales son texto suelto y nadie puede saltar de una queja de cliente a la traza. Debes (1) **definir el formato de log** del agente (JSON con el modelo de datos de logs de OpenTelemetry, contexto de traza y **sin correos** en el mensaje), (2) **convertir** cada log a una entrada de Loki con **etiquetas bien elegidas**, (3) responder **cuatro preguntas de investigación** con LogQL y (4) preparar dos consultas de métricas y un recuento por minuto.

    ## Datos

    El lote pregrabado `recorded/logs_seed42.json.gz`: **660 líneas** en 4 streams (`supportops-agent-json`, `llm-gateway-access`, `orders-api-access`, `kb-search-access`) del mismo lote que usaste en el módulo 07, con `trace_id` como *structured metadata*, y la verdad de campo `RES`. La corrección usa `logql_mini` (validado contra Loki 3.7 en la lección). Con el stack, una celda final verifica tus consultas en Loki real.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución, lote pregrabado) |
    |---|---|---|---|
    | R1 | `OtelJsonFormatter` | 5 casos: INFO sin span (sin `trace_id`); WARNING dentro de un span (`WARN`, `trace_id`/`span_id` correctos, extras en `attributes`); correo en el mensaje → `[email]`; excepción en **una sola línea** con `exception.stacktrace`; CRITICAL → `FATAL` | 5/5 |
    | R2 | `to_loki_entry` | Etiquetas **exactamente** `service_name` y `deployment_environment_name`; metadatos con `trace_id`/`span_id`/`ticket_id`; marca de tiempo en ns correcta; línea = JSON | 4/4 comprobaciones |
    | R3 | `INVESTIGATION` I1-I4 | Nº de líneas y huella (sha1 de las marcas de tiempo) de cada consulta | 4/4 exactas |
    | R4 | `errors_per_minute` | Lista de 10 enteros: logs de acceso con `status >= 500` por minuto desde la primera línea: `[1, 0, 6, 17, 7, 4, 2, 4, 0, 0]` | exacto |
    | R5 | `METRICS` | 2 consultas de métricas (tasa de 5xx por ruta; p95 de `duration_ms` por servicio con `unwrap`) con la sintaxis esperada | 2/2 |
    | R6 | Verificación en vivo (opcional) | Con Loki: I1, I2 y I4 devuelven el mismo nº de líneas que el mini motor sobre un lote nuevo | 3/3 (se omite sin stack) |

    > 📏 Calibración: los umbrales son lo que mide la solución sobre el lote pregrabado (semilla 42, tiempo simulado); nada depende de tu máquina.
    """.replace("BADGE_PLACEHOLDER", nb.badge()))
    code(boot("viz,otel"))
    code(IMPORTS + SETUP)
    code(LOAD.split("CAP_FILE = ")[0] + 'print(f"{len(ENTRIES)} líneas en {len({e.labels[\'service_name\'] for e in ENTRIES})} streams · {RES.shape[0]} tickets")\n')
    md("""
    ## Paso 0 · El material

    Cada `Entry` de `ENTRIES` tiene `ts_ns`, `line`, `labels` (índice) y `metadata` (structured metadata). `logql.query(ENTRIES, '...')` evalúa una consulta de logs (mini motor). Explora antes de escribir nada.
    """)
    code('''
import hashlib, datetime
from opentelemetry import trace as otel_trace
from supportops.telemetry import setup_telemetry
def run_q(q, entries=ENTRIES):
    return lq.query(entries, q)
def fp(hits):
    return [len(hits), hashlib.sha1(",".join(str(e.ts_ns) for e in sorted(hits, key=lambda e: e.ts_ns)).encode()).hexdigest()[:10]]
for s_ in sorted({e.labels["service_name"] for e in ENTRIES}):
    e = next(e for e in ENTRIES if e.labels["service_name"] == s_); print(f"{s_:24s} {sum(1 for x in ENTRIES if x.labels['service_name']==s_):4d} líneas · ejemplo: {e.line[:105]}")
''')
    md("""
    ## Paso 1 · El formato de log (logging estructurado)

    **TODO 1.** Implementa `OtelJsonFormatter(logging.Formatter)`: `format(record)` devuelve **una línea JSON** con las claves del modelo de logs de OpenTelemetry:

    | Clave | Valor |
    |---|---|
    | `ts` | instante de `record.created` en ISO-8601 UTC con milisegundos |
    | `severity_text` | `DEBUG`, `INFO`, `WARN`, `ERROR` o `FATAL` (nombres de OpenTelemetry: `WARNING→WARN`, `CRITICAL→FATAL`) |
    | `body` | el mensaje (`record.getMessage()`) con **cualquier correo sustituido por `[email]`** (regex `[\\w.+-]+@[\\w-]+\\.[\\w.]+`) |
    | `attributes` | dict con los campos extra pasados con `extra={...}` (`ticket_id`, `status`...) y, si hay excepción, `exception.stacktrace` con el *traceback* en el propio valor |
    | `trace_id`, `span_id` | del **span activo** (hex de 32 y de 16 caracteres) **solo si hay uno** |
    """)
    md(hint(1, "Los atributos «de serie» de `LogRecord` (`name`, `msg`, `args`, `levelname`, `levelno`, `pathname`, `filename`, `module`, `exc_info`, `exc_text`, `stack_info`, `lineno`, `funcName`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`, `processName`, `process`, `message`, `taskName`) no son extras: los extras son el resto de `record.__dict__`."))
    md(hint(2, "`sc = otel_trace.get_current_span().get_span_context()`; `sc.is_valid`; `format(sc.trace_id, '032x')`, `format(sc.span_id, '016x')`. El traceback: `self.formatException(record.exc_info)`; al ir dentro de JSON los saltos de línea se escapan, así que la línea sigue siendo única."))
    code('''
EMAIL_RE = re.compile(r"[\\w.+-]+@[\\w-]+\\.[\\w.]+")
SEVERITY = {"DEBUG": "DEBUG", "INFO": "INFO", "WARNING": "WARN", "ERROR": "ERROR", "CRITICAL": "FATAL"}

class OtelJsonFormatter(logging.Formatter):
    def format(self, record):
        # TODO 1
        raise NotImplementedError("TODO 1")

def demo_logger(fmt):
    buf = io.StringIO(); h = logging.StreamHandler(buf); h.setFormatter(fmt)
    lg = logging.getLogger(f"demo.p08.{id(buf)}"); lg.handlers[:] = [h]; lg.setLevel(logging.DEBUG); lg.propagate = False
    return lg, buf

try:
    lg, buf = demo_logger(OtelJsonFormatter())
    tel = setup_telemetry("demo", mode="memory", set_global=False)
    with tel.tracer("demo").start_as_current_span("invoke_agent") as sp:
        lg.warning("el cliente ana@example.com pregunta por su pedido", extra={"ticket_id": "T-1", "status": 429})
    tel.shutdown(); print(buf.getvalue().strip())
except NotImplementedError as e:
    print("Pendiente:", e)
''')
    md("""
    ## Paso 2 · De log a entrada de Loki

    **TODO 2.** `to_loki_entry(doc, service="supportops-agent-json", env="lab")` recibe el **dict** que produce tu formateador y devuelve la tupla `(ts_ns, line, labels, metadata)` que espera `LokiPusher.add`:
    - `ts_ns`: `int` de nanosegundos del campo `ts` (ISO);
    - `line`: `json.dumps(doc, ensure_ascii=False)`;
    - `labels`: **exactamente** `{"service_name": service, "deployment_environment_name": env}` — nada de `trace_id`, `ticket_id` ni nivel como etiquetas (cardinalidad);
    - `metadata`: `trace_id`, `span_id` (si existen en `doc`) y `ticket_id` (si está en `doc["attributes"]`), todo `str`.
    """)
    md(hint(1, "`datetime.datetime.fromisoformat(doc['ts'])` devuelve un `datetime` con zona; `int(dt.timestamp() * 1e9)` pierde precisión de nanosegundos por el `float`: usa `int(dt.timestamp()) * 10**9 + dt.microsecond * 1000`."))
    code('''
def to_loki_entry(doc: dict, service: str = "supportops-agent-json", env: str = "lab"):
    # TODO 2
    raise NotImplementedError("TODO 2")
try:
    d = {"ts": "2026-10-15T12:00:00.123+00:00", "severity_text": "WARN", "body": "x", "attributes": {"ticket_id": "T-9"}, "trace_id": "a" * 32, "span_id": "b" * 16}
    print(to_loki_entry(d))
except NotImplementedError as e:
    print("Pendiente:", e)
''')
    md("""
    ## Paso 3 · Cuatro preguntas de investigación (LogQL)

    **TODO 3.** Rellena `INVESTIGATION` con consultas de **logs** (evaluadas con `logql_mini`):

    | # | Pregunta |
    |---|---|
    | I1 | Avisos (`warn`) del **agente** (stream JSON) — usa el parser `json` y un filtro de etiqueta |
    | I2 | Peticiones al **gateway LLM** (`llm-gateway-access`) con HTTP **5xx** — `logfmt` y filtro numérico |
    | I3 | **Todos los logs** (agente y servicios, sin los de OTLP) de la petición del ticket **`T-4200004`**, a partir de su `trace_id` (`TRACE_ID` ya calculado) — structured metadata, sin parsear |
    | I4 | Llamadas a **`orders-api`** **correctas** (`status = 200`) que tardaron **más de 300 ms** |
    """)
    code('''
TRACE_ID = DATA["trace_ids"]["T-4200004"]
INVESTIGATION: dict[str, str] = {
    # "I1": '{service_name="..."} | ...',
}
for k, q in INVESTIGATION.items():
    try:
        print(k, fp(run_q(q)), q)
    except Exception as e:
        print(k, "ERROR", type(e).__name__, e)
''')
    md("""
    ## Paso 4 · La forma temporal y las métricas

    **TODO 4a.** `errors_per_minute(entries, n_bins=10)`: lista de `n_bins` enteros con el nº de líneas de los streams `*-access` con **`status >= 500`** por intervalo de 60 s desde la marca de tiempo de la **primera línea del lote** (`t0 = min(e.ts_ns)`); lo posterior al último intervalo cuenta en el último. Parsea con `lq.parse_logfmt(e.line)`.

    **TODO 4b.** Escribe en `METRICS` dos consultas de **métricas LogQL**: `"err_rate"`: tasa de 5xx **por ruta** (`sum by (route)`, `rate`, ventana de 1 m) y `"p95"`: p95 de `duration_ms` **por servicio** (`quantile_over_time(0.95, ... | unwrap duration_ms [2m]) by (service_name)`), ambas sobre los logs `*-access` con `logfmt`.
    """)
    code('''
def errors_per_minute(entries, n_bins=10):
    # TODO 4a
    raise NotImplementedError("TODO 4a")
METRICS: dict[str, str] = {
    # "err_rate": '...',
}
try:
    EPM = errors_per_minute(ENTRIES); print(EPM)
    fig, ax = plt.subplots(figsize=(8, 3)); ax.bar(range(len(EPM)), EPM, color=viz.PALETTE["error"]); ax.set_xlabel("minuto"); ax.set_ylabel("5xx"); ax.set_title("5xx en los logs de acceso"); plt.show()
except NotImplementedError as e:
    print("Pendiente:", e)
for k, q in METRICS.items(): print(k, "→", q)
''')
    md("""
    ## Autocomprobación (rúbrica)
    """)
    code(f'''
EXPECTED = {EXP!r}
def check(name, fn):
    try:
        ok, detail = fn()
    except NotImplementedError:
        ok, detail = False, "pendiente"
    except Exception as e:
        ok, detail = False, f"{{type(e).__name__}}: {{e}}"
    print(("✅" if ok else "❌"), name, "·", detail); return ok
def r1():
    tel = setup_telemetry("p08", mode="memory", set_global=False); tr = tel.tracer("p08"); res = []
    try:
        lg, buf = demo_logger(OtelJsonFormatter())
        lg.info("fuera de span", extra={{"ticket_id": "T-1"}}); a = json.loads(buf.getvalue().strip().splitlines()[-1])
        res.append(a["severity_text"] == "INFO" and "trace_id" not in a and a["attributes"].get("ticket_id") == "T-1")
        with tr.start_as_current_span("s") as sp:
            lg.warning("aviso", extra={{"ticket_id": "T-2", "status": 429}}); b = json.loads(buf.getvalue().strip().splitlines()[-1])
            sc = sp.get_span_context()
            res.append(b["severity_text"] == "WARN" and b["trace_id"] == format(sc.trace_id, "032x") and b["span_id"] == format(sc.span_id, "016x") and b["attributes"].get("status") == 429)
            lg.error("el cliente ana@example.com escribió", extra={{"ticket_id": "T-3"}}); c = json.loads(buf.getvalue().strip().splitlines()[-1])
            res.append(c["body"] == "el cliente [email] escribió")
            try:
                1 / 0
            except ZeroDivisionError:
                lg.exception("fallo"); raw = buf.getvalue().strip().splitlines()[-1]
            d = json.loads(raw); res.append("ZeroDivisionError" in d["attributes"]["exception.stacktrace"] and "\\n" not in raw and d["severity_text"] == "ERROR")
        lg.critical("fin"); res.append(json.loads(buf.getvalue().strip().splitlines()[-1])["severity_text"] == "FATAL")
    finally:
        tel.shutdown()
    return sum(res) == 5, f"{{sum(res)}}/5 casos"
def r2():
    doc = {{"ts": "2026-10-15T12:00:00.123456+00:00", "severity_text": "WARN", "body": "x", "attributes": {{"ticket_id": "T-9", "status": 429}}, "trace_id": "a" * 32, "span_id": "b" * 16}}
    ts, line, labels, meta = to_loki_entry(doc)
    ok = [labels == {{"service_name": "supportops-agent-json", "deployment_environment_name": "lab"}}, meta == {{"trace_id": "a" * 32, "span_id": "b" * 16, "ticket_id": "T-9"}},
          ts == 1792065600123456000, json.loads(line) == doc]
    return all(ok), f"{{sum(ok)}}/4 comprobaciones {{ok}}"
def r3():
    good = [k for k in EXPECTED if k in INVESTIGATION and fp(run_q(INVESTIGATION[k])) == EXPECTED[k]]
    return len(good) == 4, f"{{len(good)}}/4 exactas: {{good}}"
def r4():
    return errors_per_minute(ENTRIES) == {BINS!r}, f"{{errors_per_minute(ENTRIES)}}"
def r5():
    a, b = METRICS.get("err_rate", ""), METRICS.get("p95", "")
    ok_a = "sum by (route)" in a and "rate(" in a and "logfmt" in a and "status >= 500" in a and "[1m]" in a and "-access" in a
    ok_b = "quantile_over_time(0.95" in b and "unwrap duration_ms" in b and "[2m]" in b and "by (service_name)" in b and "logfmt" in b
    return ok_a and ok_b, f"err_rate {{ok_a}} · p95 {{ok_b}}"
def r6():
    if not HAVE_LOKI:
        return True, "omitido (sin Loki)"
    B, P = run_logs_batch(120, 42, live=True); mine = set(B.trace_ids.values()); es = lq.entries_from_payload(P.full_payload())
    n_json = sum(1 for e in es if e.labels["service_name"] == "supportops-agent-json"); wait_for_logs('{{service_name="supportops-agent-json"}}', int(0.98 * n_json), 60, verbose=False)
    same = 0
    for k in ("I1", "I2", "I4"):
        live = sum(1 for x in backends.loki_query(INVESTIGATION[k], minutes=30, limit=5000) if x["labels"].get("trace_id") in mine)
        same += live == len(lq.query(es, INVESTIGATION[k]))
    return same == 3, f"{{same}}/3 consultas devuelven el mismo nº de líneas en Loki y en el mini motor"
results = [check("R1 formateador", r1), check("R2 to_loki_entry", r2), check("R3 investigación", r3), check("R4 errors_per_minute", r4), check("R5 métricas", r5), check("R6 verificación en vivo", r6)]
print(f"\\n{{sum(results)}}/6 entregables correctos")
''')
    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    Solución de referencia completa (con la que se calibró la rúbrica). Si te atascas, abre antes las pistas 🪜.
    """)
    code('''
class OtelJsonFormatter(logging.Formatter):
    RESERVED = {"name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "created", "msecs", "relativeCreated", "thread", "threadName", "processName", "process", "message", "taskName"}
    def format(self, record):
        attrs = {k: v for k, v in record.__dict__.items() if k not in self.RESERVED}
        if record.exc_info:
            attrs["exception.stacktrace"] = self.formatException(record.exc_info)
        doc = {"ts": datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc).isoformat(timespec="milliseconds"),
               "severity_text": SEVERITY.get(record.levelname, "INFO"), "body": EMAIL_RE.sub("[email]", record.getMessage()), "attributes": attrs}
        sc = otel_trace.get_current_span().get_span_context()
        if sc.is_valid:
            doc["trace_id"], doc["span_id"] = format(sc.trace_id, "032x"), format(sc.span_id, "016x")
        return json.dumps(doc, ensure_ascii=False, default=str)

def to_loki_entry(doc: dict, service: str = "supportops-agent-json", env: str = "lab"):
    dt = datetime.datetime.fromisoformat(doc["ts"])
    ts_ns = int(dt.timestamp()) * 10**9 + dt.microsecond * 1000
    meta = {k: str(doc[k]) for k in ("trace_id", "span_id") if doc.get(k)}
    if doc.get("attributes", {}).get("ticket_id"):
        meta["ticket_id"] = str(doc["attributes"]["ticket_id"])
    return ts_ns, json.dumps(doc, ensure_ascii=False), {"service_name": service, "deployment_environment_name": env}, meta

INVESTIGATION = {
    "I1": '{service_name="supportops-agent-json"} | json | level="warn"',
    "I2": '{service_name="llm-gateway-access"} | logfmt | status >= 500',
    "I3": '{service_name=~"supportops-agent-json|.+-access"} | trace_id="%s"' % TRACE_ID,
    "I4": '{service_name="orders-api-access"} | logfmt | duration_ms > 300 and status = 200',
}
def errors_per_minute(entries, n_bins=10):
    t0 = min(e.ts_ns for e in entries); out = [0] * n_bins
    for e in entries:
        if e.labels["service_name"].endswith("-access") and int(lq.parse_logfmt(e.line)["status"]) >= 500:
            out[min(n_bins - 1, int((e.ts_ns - t0) / 60e9))] += 1
    return out
METRICS = {
    "err_rate": 'sum by (route) (rate({service_name=~".+-access"} | logfmt | status >= 500 [1m]))',
    "p95": 'quantile_over_time(0.95, {service_name=~".+-access"} | logfmt | unwrap duration_ms [2m]) by (service_name)',
}
print(fp(run_q(INVESTIGATION["I3"])), errors_per_minute(ENTRIES))
''')
    code('''
results = [check("R1 formateador", r1), check("R2 to_loki_entry", r2), check("R3 investigación", r3), check("R4 errors_per_minute", r4), check("R5 métricas", r5), check("R6 verificación en vivo", r6)]
print(f"\\n{sum(results)}/6 entregables correctos")
''')
    md("""
    ## Retos extra (nivel experto)

    1. **Envíalo de verdad:** con el stack, genera un lote con `OtelJsonFormatter` + `to_loki_entry` + `LokiPusher` (un `Instrumentor` propio sobre `log(...)`) y verifica con `loki_stats` que tu pipeline procesa los mismos bytes que `JsonLogInstrumentor`.
    2. **Presupuesto de etiquetas:** calcula el nº de streams si añadieras `level` y `tier` como etiquetas a los 4 servicios; ¿cuánto crece el nº de chunks con el volumen de este lote?
    3. **Alerta puente:** escribe una regla del *ruler* (YAML) con `sum(rate({service_name=~".+-access"} | logfmt | status >= 500 [5m])) > 0.05` y explica cuándo la sustituirías por una métrica.
    4. **Redacción mejor:** amplía el formateador para ocultar también teléfonos (`+34 6xx xxx xxx`); luego mueve la redacción al Collector (procesador `transform`, módulo 20) y razona qué política es más robusta.
    5. **Línea de tiempo:** reproduce el gráfico de la sección 6 para el ticket con más reintentos del lote.
    """)
    md("""
    ## Reflexión

    - ¿Qué campos de tus logs deberían ser etiquetas, cuáles metadatos y cuáles contenido, y qué cambiaría si SupportOps pasara de 4 a 400 servicios?
    - Un auditor te pide «todos los logs de este cliente en los últimos 30 días». ¿Qué atributo falta como metadato para poder responder sin parsear todo? (módulo 20)
    - ¿Qué señales que hoy salen de logs (`rate` de 5xx, p95 con `unwrap`) migrarías a métricas en el módulo 09 y por qué?
    - Conexión con SupportOps: el `trace_id` en cada línea es la base de los paneles de correlación del módulo 10 y de las alertas con enlace a traza del 16.
    """)
    nb.save(out)


if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    (COURSE / MOD / "README.md").write_text(readme(), encoding="utf-8")
    print("OK README", COURSE / MOD / "README.md")
    build_lesson()
    build_dashboard(check="--no-check" not in sys.argv)
    build_project()
