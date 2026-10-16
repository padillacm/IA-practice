"""Genera el módulo 18_escala_muestreo_coste: README, lección, proyecto, dashboard 18, configuraciones validables y datos pregrabados.

Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_18.py            # notebooks + README + dashboard + configs
    python agent-observability-course/_tools/builders/build_18.py --record   # regenera recorded/capture_seed42.json.gz (necesita Docker)
"""
from __future__ import annotations

import gzip
import json
import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "18_escala_muestreo_coste"
RECORDED = COURSE / MOD / "recorded" / "capture_seed42.json.gz"
N_TICKETS = 1500


def mdj(head: str, *items: str) -> str:
    return textwrap.dedent(head).strip("\n") + "\n\n" + "\n\n".join(items)


# =====================================================================================================================
# Datos pregrabados: medidos con Docker real (Collector contrib 0.162, Loki 3.7.8, Tempo 3.1.0, Prometheus v3.15.0)
# =====================================================================================================================
def policies_reference():
    sys.path.insert(0, str(COURSE))
    from supportops import sampling as S
    return [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"), S.AttrCompare(name="costly"), S.Probabilistic(10, name="baseline")]


def record() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops import sampling as S
    if not S.docker_ok():
        raise SystemExit("hace falta Docker para grabar los datos")
    C = S.build_corpus(N_TICKETS)
    pol = policies_reference()
    out: dict = {"meta": {"seed": 42, "n_tickets": N_TICKETS, "collector": S.COLLECTOR_IMAGE, "loki": S.LOKI_IMAGE, "tempo": S.TEMPO_IMAGE, "prometheus": S.PROM_IMAGE}}
    r = S.run_collector_experiment(C, pol, decision_wait="2s")
    r.pop("kept_ids")
    out["collector"] = r
    sim = S.TailSampler(pol, decision_wait_s=2).run(C.traces)
    out["collector_sim"] = {"n_kept": len(sim.kept), "by_policy": dict(sim.by_policy), "coverage": S.coverage(sim.kept, C)}
    small = []
    for nt in (200, 50_000):
        rr = S.run_collector_experiment(C, [S.StatusCode(("ERROR",), name="errors"), S.Probabilistic(10, name="baseline")], decision_wait="5s", num_traces=nt)
        small.append({"num_traces": nt, "n_kept": rr["n_kept"], "recall_error_pct": rr["coverage"].get("recall_error_pct"),
                      "dropped_too_early": rr["internal"].get("otelcol_processor_tail_sampling_sampling_trace_dropped_too_early"),
                      "on_memory": rr["internal"].get("otelcol_processor_tail_sampling_sampling_traces_on_memory")})
    out["num_traces"] = small
    out["numeric_probe"] = S.numeric_attribute_probe(C)
    out["backends"] = S.backends_experiment()
    out["storm"] = [dict(n=n, bounded=b, **S.storm_experiment(n, bounded=b, interval_s=3, settle_s=10)) for n, b in ((2000, False), (10000, False), (30000, False), (10000, True))]
    RECORDED.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(RECORDED, "wt", encoding="utf-8") as f:
        json.dump(out, f)
    print("OK", RECORDED, RECORDED.stat().st_size, "bytes")


# =====================================================================================================================
# Configuraciones como archivos reales del módulo (se validan con las herramientas oficiales en la lección)
# =====================================================================================================================
LOKI_MT_YAML_NOTE = "# Loki multi-tenant con límites bajos (laboratorio de la lección 18). Verificado con `loki -verify-config`.\n"
RETENTION_LOKI = """# Loki: retención por compactor (verificado con `loki -verify-config` en 3.7.8).
# ⚠️ Con retention_enabled: true Loki EXIGE compactor.delete_request_store (sin él: «CONFIG ERROR … should be configured when retention is enabled»).
auth_enabled: false
server:
  http_listen_port: 3100
common:
  instance_addr: 127.0.0.1
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
schema_config:
  configs:
    - from: 2024-04-01
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h
compactor:
  working_directory: /loki/compactor
  retention_enabled: true
  retention_delete_delay: 2h
  delete_request_store: filesystem
limits_config:
  allow_structured_metadata: true
  retention_period: 336h            # 14 días por defecto
  retention_stream:                 # más tiempo para lo que importa en un incidente; menos para el ruido
    - selector: '{detected_level="debug"}'
      priority: 1
      period: 24h
    - selector: '{detected_level=~"warn|error"}'
      priority: 2
      period: 720h
"""
RETENTION_TEMPO = """# Tempo 3.x: retención de bloques (verificado con `tempo -config.verify=true` en 3.1.0). En Tempo 3 el compactor pasó al `backend_scheduler`.
stream_over_http_enabled: true
server:
  http_listen_port: 3200
distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
backend_scheduler:
  provider:
    compaction:
      compaction:
        compaction_window: 1h
        block_retention: 168h           # 7 días por defecto
        compacted_block_retention: 10m
storage:
  trace:
    backend: local
    wal:
      path: /var/tempo/wal
    local:
      path: /var/tempo/blocks
overrides:
  defaults:
    compaction:
      block_retention: 72h              # un tenant concreto puede tener menos (o más) que el valor global
"""
PROM_SCRAPE_LIMITS = """# Prometheus: límites por trabajo de scrape (verificado con `promtool check config`). Una tormenta de cardinalidad ENTERA se rechaza en el scrape
# (el objetivo pasa a up=0) en vez de reventar la memoria. La retención se fija con FLAGS: --storage.tsdb.retention.time=15d --storage.tsdb.retention.size=20GB
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: otel-collector-apps
    honor_labels: true
    sample_limit: 20000           # máx. muestras por scrape tras relabeling (si se supera, se descarta TODO el scrape)
    label_limit: 30               # máx. nº de etiquetas por muestra
    label_name_length_limit: 64
    label_value_length_limit: 200
    static_configs:
      - targets: ["otel-collector:8889"]
"""


def build_configs() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops import sampling as S
    d = COURSE / MOD / "configs"
    d.mkdir(parents=True, exist_ok=True)
    pol = policies_reference()
    header = ("# Collector con TAIL SAMPLING (módulo 18). Verificado con `otelcol-contrib validate` 0.162.0.\n"
              "# RED (span_metrics) se calcula ANTES del muestreo (pipeline traces/in); lo conservado sale por traces/sampled.\n"
              "# ⚠️ numeric_attribute usa int64 en 0.162.0 (un decimal trunca y, con atributos double, el procesador cae): el coste va con ottl_condition.\n")
    (d / "collector-tail-sampling.yaml").write_text(header + S.collector_config(pol, decision_wait="30s", num_traces=50_000, expected_new_traces_per_sec=50,
                                                                              decision_cache=(100_000, 100_000)), encoding="utf-8")
    (d / "loki-multitenant-limits.yaml").write_text(LOKI_MT_YAML_NOTE + S.loki_lab_config({"ingestion_rate_mb": 4, "ingestion_burst_size_mb": 6, "per_stream_rate_limit": "3MB",
                                                                                           "max_label_names_per_series": 15, "max_streams_per_user": 5000, "retention_period": "336h"}, auth=True), encoding="utf-8")
    (d / "tempo-multitenant-limits.yaml").write_text("# Tempo multi-tenant con límites (verificado con `tempo -config.verify=true`).\n" + S.tempo_lab_config(
        {"global": {"max_bytes_per_trace": 5_000_000}, "ingestion": {"rate_limit_bytes": 15_000_000, "burst_size_bytes": 20_000_000}}, multitenancy=True), encoding="utf-8")
    (d / "loki-retention.yaml").write_text(RETENTION_LOKI, encoding="utf-8")
    (d / "tempo-retention.yaml").write_text(RETENTION_TEMPO, encoding="utf-8")
    (d / "prometheus-scrape-limits.yaml").write_text(PROM_SCRAPE_LIMITS, encoding="utf-8")
    print("OK configs", sorted(p.name for p in d.iterdir()))


def validate_configs() -> dict[str, bool]:
    """Validación con los binarios oficiales (si hay Docker): se usa en la lección y se puede lanzar desde aquí."""
    import subprocess
    sys.path.insert(0, str(COURSE))
    from supportops import sampling as S
    d = COURSE / MOD / "configs"
    res = {}
    ok, _ = S.validate_collector_config((d / "collector-tail-sampling.yaml").read_text())
    res["collector-tail-sampling"] = ok
    for f, img, args in (("loki-multitenant-limits.yaml", S.LOKI_IMAGE, ["-verify-config"]), ("loki-retention.yaml", S.LOKI_IMAGE, ["-verify-config"]),
                         ("tempo-multitenant-limits.yaml", S.TEMPO_IMAGE, ["-config.verify=true"]), ("tempo-retention.yaml", S.TEMPO_IMAGE, ["-config.verify=true"])):
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{d / f}:/c.yaml:ro", img, "-config.file=/c.yaml", *args], capture_output=True, text=True)
        res[f] = r.returncode == 0 and "CONFIG ERROR" not in (r.stdout + r.stderr)
    r = subprocess.run(["docker", "run", "--rm", "--entrypoint", "promtool", "-v", f"{d / 'prometheus-scrape-limits.yaml'}:/p.yml:ro", S.PROM_IMAGE, "check", "config", "/p.yml"],
                       capture_output=True, text=True)
    res["prometheus-scrape-limits"] = r.returncode == 0
    return res


# =====================================================================================================================
# Dashboard
# =====================================================================================================================
DASH_UID = "escala-coste"


def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, lint, prom, stat, text, thresholds, timeseries
    d = Dashboard(DASH_UID, "18 · Escala y coste del propio stack", tags=["curso", "escala", "muestreo", "coste"], time_from="now-1h",
                  description="Salud y coste del pipeline de telemetría: volumen de spans que entran/salen del Collector, cola y reintentos, series activas en Prometheus y descartes de Tempo/Loki por límites.")
    d.add(text("Cómo leer este dashboard", "El stack de observabilidad **también se monitoriza**. Primero, ¿cuánto entra y cuánto sale? (`accepted` − `sent` = lo muestreado o perdido). Después, ¿hay presión (cola, reintentos, `refused`)? "
               "Por último, el coste real: **series activas** de Prometheus (memoria ∝ series) y **descartes por límites** en Tempo y Loki (señal de tenants o aplicaciones que se pasan). "
               "Las métricas `otelcol_processor_tail_sampling_*` aparecen cuando el Collector del stack usa `tail_sampling` (ver `configs/collector-tail-sampling.yaml`).", h=3))
    d.row("Volumen y pérdidas en el Collector")
    d.add(timeseries("Spans aceptados vs enviados (por segundo)", [prom("sum(rate(otelcol_receiver_accepted_spans[$__rate_interval]))", "aceptados"),
                                                                     prom("sum(rate(otelcol_exporter_sent_spans[$__rate_interval]))", "enviados", ref="B")], unit="ops", w=12, h=7,
                     description="Diferencia entre lo que entra y lo que sale: con tail sampling activo es la fracción muestreada; sin él, cualquier hueco es una pérdida."),
          timeseries("Spans rechazados o con fallo de envío (por segundo)", [prom("sum(rate(otelcol_receiver_refused_spans[$__rate_interval]))", "rechazados por el receptor"),
                                                                              prom("sum(rate(otelcol_exporter_send_failed_spans[$__rate_interval]))", "fallo al exportar", ref="B")], unit="ops", w=12, h=7,
                     description="Presión hacia atrás: el memory_limiter rechaza (refused) y los exportadores fallan cuando un backend aplica límites."))
    d.row("Tail sampling (si está activo)")
    d.add(timeseries("Decisiones de muestreo por política", [prom('sum by (policy) (rate(otelcol_processor_tail_sampling_count_traces_sampled{sampled="true"}[$__rate_interval]))', "{{policy}}")], unit="ops", w=12, h=7,
                     description="Trazas por segundo que cada política votó conservar. Una política «baseline» muy por encima de errors/slow indica que el muestreo base domina el presupuesto."),
          timeseries("Trazas descartadas antes de decidir", [prom("sum(rate(otelcol_processor_tail_sampling_sampling_trace_dropped_too_early[$__rate_interval]))", "dropped_too_early")], unit="ops", w=12, h=7,
                     description="Debe ser 0. Si crece, num_traces es insuficiente para (tráfico × decision_wait): se pierden trazas sin evaluar sus políticas."))
    d.row("Coste: series y límites")
    d.add(stat("Series activas en Prometheus", "prometheus_tsdb_head_series", w=6, h=5, thr=thresholds((None, "green"), (50000, "orange"), (200000, "red")),
               description="Memoria de Prometheus ∝ series activas (≈ 1-3 KB por serie medido). Umbrales de laboratorio."),
          timeseries("Crecimiento de series activas", [prom("prometheus_tsdb_head_series", "series")], w=9, h=5, description="Una pendiente brusca = tormenta de cardinalidad (una etiqueta nueva con valores casi únicos)."),
          timeseries("Descartes de Tempo por motivo", [prom("sum by (reason) (rate(tempo_discarded_spans_total[$__rate_interval]))", "{{reason}}")], unit="ops", w=9, h=5,
                     description="Motivos típicos: trace_too_large, rate_limited, max_live_traces. Cada uno es un límite por tenant que se está alcanzando."))
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "18-escala-coste.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
# Celdas comunes
# =====================================================================================================================
IMPORTS_18 = '''
import copy, collections, gzip, json, math, re, subprocess, time
from IPython.display import Markdown, display
from supportops import sampling as S
DOCKER = S.docker_ok()
REC = json.load(gzip.open(ROOT / "18_escala_muestreo_coste" / "recorded" / "capture_seed42.json.gz", "rt", encoding="utf-8"))   # modo degradado: medido con Docker real
CORPUS = S.build_corpus(1500, seed=SEED)                  # 1 500 tickets de SupportOps (mock, semilla 42) con su tamaño OTLP real
SM = CORPUS.summary()
print(f"Docker disponible: {DOCKER} (si es False, las secciones con contenedores usan la captura pregrabada) · {int(SM['traces'])} trazas, {int(SM['spans'])} spans, {SM['bytes_per_span']:.0f} B/span")
'''


def build_lesson() -> None:
    nb, out = nb_for(MOD, "18_escala_muestreo_coste.ipynb", "Módulo 18 · Escala, muestreo y coste del propio stack")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 18 · Escala, muestreo y coste: observar el agente sin arruinar la factura de observar

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 5 h (ruta núcleo ≈ 3 h 30: §1-6, §8 y §11) |
    | **Servicios de Compose** | Ninguno del stack del curso. Con **Docker** el notebook lanza contenedores efímeros (Collector contrib 0.162, Loki, Tempo, Prometheus) en puertos aleatorios: no choca con `docker compose` |
    | **RAM aproximada** | ≈ 1 GB mientras corre un contenedor de laboratorio (se destruyen al terminar cada experimento) |
    | **Modo sin Docker** | Todo el muestreo (simulador, sesgo, costes, cardinalidad analítica) corre en cualquier sitio, Colab incluido; lo medido con contenedores reales viene **pregrabado** |
    | **Prerrequisitos** | Módulos 05 (Collector), 07-09 (backends y métricas), 13 (coste del agente) y 16 (SLOs) |

    > 🧭 **Ruta núcleo vs ampliación.** Núcleo: volumen y presupuesto (§1), head vs tail (§2-5), Collector real (§6), sesgo (§7) y política final (§12). Ampliación: cardinalidad (§8), multi-tenant y límites (§9), retención/tiering (§10), coste (§11).
    """)

    md("""
    ## Objetivos de aprendizaje

    1. **Calcular** el volumen y el coste de la telemetría de un agente a partir de tamaños **medidos** (bytes por span, spans por traza) y proyectarlo a producción.
    2. **Comparar** muestreo *head* y *tail*, y **diseñar** una política que conserve el 100 % de errores, lentas y caras con una fracción del volumen.
    3. **Configurar y verificar** el procesador `tail_sampling` del Collector contrib 0.162 (políticas, `decision_wait`, `num_traces`), y **dimensionar** su memoria.
    4. **Demostrar** que el muestreo sesga las métricas derivadas y **corregirlas** (pesos de inclusión o métricas calculadas *antes* de muestrear).
    5. **Provocar y contener** una tormenta de cardinalidad en Prometheus real; **explicar** por qué el coste depende de las series y no de los puntos.
    6. **Aislar** tenants en Tempo y Loki y **hacer cumplir** límites de ingesta con contenedores reales, interpretando los errores.
    7. **Diseñar** retención y niveles (caliente/frío) con un presupuesto y **medir** el impacto de la política completa.
    """)

    md(mdj("""
    ## 🔁 Conexión con módulos anteriores
    """,
           details("1. (Módulo 05) ¿En qué punto de un pipeline de Collector se coloca un procesador que mantiene estado, como `tail_sampling`, y qué exige a la red?",
                   "Después de procesadores que dependen del contexto (p. ej. `k8s_attributes`), y **todos los spans de una traza deben llegar a la misma instancia**: con varias réplicas hace falta una capa delante con el exportador `load_balancing` por `traceID`."),
           details("2. (Módulo 09) ¿Por qué `ticket_id` no puede ser una etiqueta de métrica?",
                   "Cada valor distinto crea una serie nueva: la memoria de Prometheus crece con el nº de series activas. En este módulo lo **medimos** con un Prometheus real."),
           details("3. (Módulo 13/16) ¿Qué condiciones del SLO de coste y de latencia usamos para decir que un ticket es «interesante»?",
                   "Coste por ticket > 0,0005 USD y latencia > 5 s (más los errores). Son exactamente los criterios de las políticas `latency` y `ottl_condition` de este módulo.")))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_18)

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ## 1 · Intuición: la telemetría también tiene factura

    Un agente de IA genera mucho más dato por petición que un servicio web clásico: varios *spans* por ticket (LLM, herramientas), logs por paso y, si capturas contenido, **kilobytes por span**.
    Observarlo todo, siempre, es caro de tres formas distintas:

    | Coste | Qué lo dispara | Dónde se paga |
    |---|---|---|
    | **Volumen** (bytes/s) | spans y logs por petición × peticiones | red, CPU del Collector, ingesta/almacenamiento (y, en SaaS, la factura) |
    | **Cardinalidad** (series) | etiquetas con muchos valores distintos | **memoria** de Prometheus/Mimir, índice de Loki |
    | **Retención** (días) | cuánto se conserva y en qué disco | almacenamiento caliente vs. frío |

    > 💡 **Intuición (ML).** Es el equilibrio sesgo/varianza de la observabilidad: guardas una *muestra* de la población de trazas. Si la muestra es aleatoria, es insesgada pero pierde lo raro (los errores);
    > si la eliges con criterio (errores, lentas, caras) conservas lo valioso, pero **estás sesgando** cualquier estadística calculada sobre ella (lo vemos en §7).
    """)

    code('''
sm = SM
tickets_day = 1_000_000
scen = {"SupportOps medido\\n(mock: 4 spans, sin contenido)": S.StackCostModel.from_corpus(CORPUS, tickets_day),
        "Agente de producción\\n(supuesto: 40 spans, contenido ≈ 2,5 KB/span)": S.StackCostModel(tickets_per_day=tickets_day, spans_per_trace=40, bytes_per_span=2500, log_lines_per_ticket=12, bytes_per_log_line=600)}
fig, ax = plt.subplots(figsize=(9.5, 4))
bottom = np.zeros(len(scen)); names = list(scen)
for key, col, lab in (("traces_ingest", viz.PALETTE["traces"], "trazas"), ("logs_ingest", viz.PALETTE["logs"], "logs"), ("metrics_stored", viz.PALETTE["metrics"], "métricas")):
    vals = np.array([scen[n].daily_gb()[key] for n in names])
    ax.bar(names, vals, bottom=bottom, color=col, label=lab); bottom += vals
ax.set_ylabel("GB/día ingeridos (sin comprimir) a 1 M tickets/día"); ax.set_title("El volumen por señal depende del tamaño del span, no solo del nº de tickets"); ax.legend(); plt.show()
print({n.replace("\\n", " "): {k: round(v, 2) for k, v in m.daily_gb().items()} for n, m in scen.items()})
''')
    md(observe("""
    - Con los números **medidos** en SupportOps (≈ 500 B por span, 4 spans por traza) un millón de tickets al día son solo ≈ 2 GB de trazas; con un agente «real» (decenas de spans con contenido de prompts) pasan a **cientos de GB/día**. El orden de magnitud lo decide el contenido, por eso la lección del módulo 20 sobre qué capturar importa también para el coste.
    - Las métricas ocupan **muy poco** en bytes pero son lo más peligroso en memoria si crecen las series (§8).
    - Los parámetros del escenario de producción son **supuestos** marcados como tales; sustitúyelos por los medidos en tu sistema (`CORPUS.summary()`).
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ## 2 · Teoría: head frente a tail

    **Head sampling**: la decisión se toma **al empezar** la traza (en el SDK o en el primer Collector), solo con lo que se sabe entonces: el `trace_id`. Es barata (cero memoria), consistente (todos los servicios deciden igual si usan el mismo `trace_id`) y **ciega** al desenlace.

    **Tail sampling**: la decisión se toma **cuando la traza está completa** (tras `decision_wait`), así que puede mirar errores, latencia total, coste… Es potente, pero tiene **estado** (guarda todos los spans en memoria hasta decidir), exige afinidad por `trace_id` y es una pieza más que operar.

    📐 **Matemáticas.** Con probabilidad de muestreo $p$ uniforme, cada traza se conserva con probabilidad $p$. Un suceso raro con $m$ trazas en el periodo se pierde **del todo** con probabilidad $(1-p)^m$; con $p=0{,}1$ y $m=20$ errores:
    $(1-0{,}1)^{20}\\approx 12\\,\\%$ de no ver **ninguno**, y se ven de media solo $mp=2$. Si cada traza conservada tiene probabilidad de inclusión $\\pi_i$, un estimador insesgado del total usa **pesos** $w_i=1/\\pi_i$ (Horvitz–Thompson):
    $\\hat N=\\sum_{i\\in\\text{muestra}} 1/\\pi_i$ ($\\pi_i$ = probabilidad de inclusión; $\\hat N$ = nº estimado de trazas reales).
    """)
    code('''
fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
ax = axs[0]
ps = np.linspace(0.01, 0.5, 100)
for m, col in ((5, viz.PALETTE["error"]), (20, viz.PALETTE["warn"]), (100, viz.PALETTE["ok"])):
    ax.plot(ps * 100, 100 * (1 - ps) ** m, color=col, lw=2, label=f"{m} errores en el periodo")
ax.set_xlabel("probabilidad de muestreo head p (%)"); ax.set_ylabel("% de veces que NO se ve ningún error"); ax.set_title("Un head sampling pierde lo raro"); ax.legend()
ax = axs[1]
ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
for i, (ttl, rows, c) in enumerate((("HEAD", ["trace_id → ¿conservar?", "sin memoria, sin espera", "decide ANTES de saber el desenlace", "consistente entre servicios"], viz.PALETTE["traces"]),
                                  ("TAIL", ["traza completa → políticas", "memoria ∝ tráfico × decision_wait", "ve errores, latencia y coste", "afinidad por trace_id obligatoria"], viz.PALETTE["profiles"]))):
    x = 0.2 + i * 5
    ax.add_patch(plt.Rectangle((x, 0.3), 4.5, 5.2, fc=c + "22", ec=c, lw=2))
    ax.text(x + 2.25, 5.0, ttl, ha="center", fontsize=12, fontweight="bold", color=c)
    for j, r in enumerate(rows): ax.text(x + 0.2, 4.1 - j * 0.9, "• " + r, fontsize=8.5, va="center")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Izquierda: con p = 10 % y 20 errores todavía hay ≈ 12 % de probabilidad de **no ver ni uno**, y la curva solo mejora subiendo el muestreo (más coste). Para lo raro, el head sampling es una mala herramienta.
    - Derecha: el tail sampling compra **información** (el desenlace) a cambio de **estado** (memoria y afinidad). La decisión de ingeniería es qué pagar.
    """))

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ## 3 · Los datos: un corpus de trazas de SupportOps

    `build_corpus` ejecuta el agente (mock, semilla 42) sobre 1 500 tickets con los fallos habituales y guarda cada traza con su tamaño OTLP/protobuf **real** (`spans_to_otlp(...).ByteSize()`). «**Interesante**» = lo que querrías ver siempre: algún span en error (un fallo recuperado por un reintento también cuenta), lenta (≥ 5 s) o cara (> 0,0005 USD). `error` = ticket fallido (raíz en ERROR).
    """)
    code('''
rows = pd.DataFrame([{"duración (s)": t.duration_s, "coste (USD)": t.cost_usd, "spans": t.n_spans, "bytes": t.bytes, "error": t.error, "span_error": t.has_error_span, "lenta": t.slow, "cara": t.costly, "interesante": t.interesting} for t in CORPUS.traces])
display(pd.Series({k: (round(v, 4) if isinstance(v, float) else v) for k, v in SM.items()}, name="corpus").to_frame().T)
fig, axs = plt.subplots(1, 3, figsize=(13, 3.5))
axs[0].hist(rows["duración (s)"].clip(upper=20), bins=40, color=viz.PALETTE["traces"]); axs[0].axvline(S.SLOW_S, color=viz.PALETTE["error"], ls="--"); axs[0].set_title("Duración de la traza (s)"); axs[0].set_xlabel("s (recortado a 20)")
axs[1].hist(rows["coste (USD)"] * 1e3, bins=40, color=viz.PALETTE["metrics"]); axs[1].axvline(S.COSTLY_USD * 1e3, color=viz.PALETTE["error"], ls="--"); axs[1].set_title("Coste por ticket (milésimas de USD)"); axs[1].set_xlabel("m USD")
cnt = rows[["error", "span_error", "lenta", "cara", "interesante"]].mean() * 100
axs[2].bar(cnt.index, cnt.values, color=[viz.PALETTE["error"], viz.PALETTE["error"], viz.PALETTE["warn"], viz.PALETTE["metrics"], viz.PALETTE["profiles"]]); axs[2].tick_params(axis="x", labelsize=8); axs[2].set_ylabel("% de las trazas"); axs[2].set_title("Lo «interesante» es raro")
for i, v in enumerate(cnt.values): axs[2].text(i, v, f"{v:.1f} %", ha="center", va="bottom")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Solo ≈ 11 %** de las trazas son interesantes (tickets fallidos 2,6 %, con algún span en error 7,9 %, lentas 4,6 %, caras 1,6 %, con solapes): ese es el margen que explota el tail sampling. El ≈ 89 % restante es el «cuerpo» de la distribución.
    - Las colas (duración > 5 s, coste > 0,0005) son largas y finas: justo lo que un muestreo aleatorio pierde.
    """))

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ## 4 · Head sampling a mano: `trace_id` → decisión

    El muestreo basado en el id compara la **aleatoriedad del `trace_id`** (sus 56 bits menos significativos, como en el muestreo consistente de OpenTelemetry) con un umbral. Todos los servicios que vean el mismo `trace_id` toman la misma decisión sin hablar entre sí.
    """)
    code('''
ratio = 0.10
dec = [S.head_keep(t.trace_id, ratio) for t in CORPUS.traces]
print(f"conservadas con p={ratio}: {sum(dec)} de {len(dec)} ({100*sum(dec)/len(dec):.1f} %)")
t0 = CORPUS.traces[0]
print("decisión del servicio A y del servicio B para la misma traza:", S.head_keep(t0.trace_id, ratio), S.head_keep(t0.trace_id, ratio), "(determinista: no necesitan coordinarse)")
fig, ax = plt.subplots(figsize=(9, 3.8))
for p, col in zip((0.01, 0.05, 0.10, 0.25, 0.5), plt.cm.Blues(np.linspace(0.35, 0.95, 5))):
    cov = S.coverage(S.head_sample(CORPUS.traces, p), CORPUS)
    ax.scatter(cov["kept_bytes_pct"], cov["recall_interesting_pct"], s=70, color=col, edgecolor="k", zorder=3)
    ax.annotate(f"p={p:g}", (cov["kept_bytes_pct"], cov["recall_interesting_pct"]), textcoords="offset points", xytext=(6, -10), fontsize=8)
ax.plot([0, 100], [0, 100], "--", color=viz.PALETTE["neutral"], label="recall = fracción conservada (azar)")
ax.set_xlabel("% de bytes conservados (coste)"); ax.set_ylabel("% de trazas interesantes conservadas (recall)"); ax.set_title("Head sampling: el recall es igual al coste"); ax.legend(); plt.show()
''')
    md(observe("""
    - Todos los puntos del head sampling caen **sobre la diagonal**: para ver el 25 % de los errores pagas el 25 % del volumen. No hay forma de «ser listo» sin conocer el desenlace.
    - La decisión es **determinista por `trace_id`**: reconstruir qué se conservó no necesita estado compartido. Por eso el head sampling escala sin coordinación.
    """))

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ## 5 · Tail sampling a mano: políticas como código

    El procesador `tail_sampling` agrupa los spans por `trace_id`, espera `decision_wait` (30 s por defecto) desde el primero y evalúa **políticas** (`latency`, `status_code`, `ottl_condition`, `probabilistic`, `rate_limiting`, `and`, `drop`…).
    Regla de decisión: **conserva si alguna política dice «sí» y ninguna dice «drop»**. `TailSampler` implementa esa semántica, con la memoria acotada por `num_traces`, para poder razonar y dimensionar antes de tocar un Collector.
    """)
    code('''
policies = [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"), S.AttrCompare("supportops.cost_usd", ">", 0.0005, name="costly"), S.Probabilistic(10, name="baseline")]
res = S.TailSampler(policies, decision_wait_s=30).run(CORPUS.traces)
cov = S.coverage(res.kept, CORPUS)
print("políticas que votaron «conservar» (una traza puede tener varios votos):", dict(res.by_policy))
print({k: round(v, 1) for k, v in cov.items()})
fig, axs = plt.subplots(1, 2, figsize=(12.5, 3.8))
names = ["Head 10 %", "Tail: errores+lentas+caras\\n+ 10 % base", "Tail: solo errores"]
sets = {names[0]: S.head_sample(CORPUS.traces, 0.10), names[1]: res.kept, names[2]: S.TailSampler([S.StatusCode(("ERROR",), name="e")], 30).run(CORPUS.traces).kept}
x = np.arange(3)
axs[0].bar(x - 0.2, [S.coverage(sets[n], CORPUS)["kept_bytes_pct"] for n in names], 0.4, color=viz.PALETTE["metrics"], label="% de bytes (coste)")
axs[0].bar(x + 0.2, [S.coverage(sets[n], CORPUS)["recall_interesting_pct"] for n in names], 0.4, color=viz.PALETTE["ok"], label="% de interesantes conservadas")
axs[0].set_xticks(x); axs[0].set_xticklabels(names, fontsize=8); axs[0].set_title("Coste vs cobertura"); axs[0].legend(fontsize=8)
comp = collections.Counter()
for t in res.kept:
    comp["error" if t.error else "lenta" if t.slow else "cara" if t.costly else "base (10 %)"] += 1
axs[1].pie(comp.values(), labels=[f"{k} · {v}" for k, v in comp.items()], colors=[viz.PALETTE["error"], viz.PALETTE["warn"], viz.PALETTE["metrics"], viz.PALETTE["neutral"]], startangle=90)
axs[1].set_title("¿Qué hay dentro de lo conservado?")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La política compuesta conserva **el 100 % de lo interesante** con ≈ 23 % de los bytes; el head al 10 % guarda ≈ 10 % del volumen y **solo ≈ 10 %** de lo interesante.
    - Casi la mitad de lo conservado (≈ 48 %) no es interesante: es el **10 % base** del resto. Ese muestreo base es el que permite estimar el comportamiento «normal»; su porcentaje es tu mando de presupuesto.
    - Una política solo de errores sale barata, pero no ve la lentitud ni el coste (los «fallos silenciosos» del módulo 15).
    """))

    md("""
    ### 5.1 · La memoria del tail sampling: $\\text{traces en memoria}\\approx \\text{tráfico}\\times\\text{decision\\_wait}$

    El procesador guarda **todos los spans** de las trazas hasta decidir. Con `num_traces` demasiado pequeño, la traza más antigua se descarta **sin decisión** (`sampling_trace_dropped_too_early`). Comprimimos la línea de tiempo del corpus para simular más tráfico.
    """)
    code('''
fig, axs = plt.subplots(1, 2, figsize=(12.5, 3.8))
base_rate = len(CORPUS) / CORPUS.duration_s
rates = [base_rate * f for f in (1, 4, 16, 64)]
waits = [5, 10, 30, 60]
for f, col in zip((1, 4, 16, 64), plt.cm.Purples(np.linspace(0.35, 0.95, 4))):
    r = S.rescale_rate(CORPUS.traces, f)
    peaks = [S.TailSampler(policies, decision_wait_s=w, num_traces=10**9).run(r).peak_traces for w in waits]
    axs[0].plot(waits, peaks, "o-", color=col, lw=2, label=f"{base_rate * f:.0f} trazas/s")
axs[0].set_xlabel("decision_wait (s)"); axs[0].set_ylabel("trazas en memoria (pico)"); axs[0].set_title("Memoria ≈ tráfico × decision_wait"); axs[0].legend(fontsize=8)
r = S.rescale_rate(CORPUS.traces, 16)
nts = [100, 300, 1000, 3000]
lost = [len(S.TailSampler(policies, decision_wait_s=30, num_traces=n).run(r).dropped_too_early) / len(r) * 100 for n in nts]
rec = [S.coverage(S.TailSampler(policies, 30, n).run(r).kept, CORPUS)["recall_interesting_pct"] for n in nts]
axs[1].bar([str(n) for n in nts], lost, color=viz.PALETTE["error"], label="% de trazas perdidas sin decidir"); axs[1].set_xlabel("num_traces"); axs[1].set_ylabel("% perdidas"); axs[1].set_title("num_traces insuficiente a 16× el tráfico y 30 s")
ax2 = axs[1].twinx(); ax2.plot([str(n) for n in nts], rec, "o-", color=viz.PALETTE["ok"], lw=2); ax2.set_ylabel("% interesantes conservadas", color=viz.PALETTE["ok"]); ax2.grid(False)
plt.tight_layout(); plt.show()
print(f"pico de memoria a {base_rate*16:.0f} trazas/s con 30 s: {S.fmt_bytes(S.TailSampler(policies, 30, 10**9).run(r).peak_bytes)} de spans (solo datos, sin sobrecoste del procesador)")
''')
    md(observe("""
    - Cada línea es lineal en `decision_wait`, y sube con el tráfico: **doblar la espera o el tráfico dobla la memoria**. No es un coste fijo: crece con el éxito del producto.
    - A la derecha, con `num_traces` pequeño se pierden trazas **antes de evaluar sus políticas** y el recall de lo interesante se desploma: un tail sampling mal dimensionado es peor que un head sampling.
    - Regla de dimensionado: `num_traces` ≥ (trazas nuevas/s) × `decision_wait` × margen de 1,5-2, y vigila `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early` (debe ser 0).
    """))

    # ------------------------------------------------------------------------------------------------ 6
    md("""
    ## 6 · Con el Collector real: configuración verificada

    Configuración (claves comprobadas con el README del procesador, v0.162.0, estabilidad *beta* para trazas). Dos canalizaciones unidas por el conector `forward`: **`traces/in`** calcula las métricas RED (`span_metrics`) **antes** de muestrear y reenvía; **`traces/sampled`** aplica `tail_sampling`.
    """)
    code('''
cfg = S.collector_config(policies, decision_wait="2s")
print(cfg)
if DOCKER:
    ok, msg = S.validate_collector_config(cfg)
    print("otelcol-contrib validate →", "✅ válida" if ok else "❌\\n" + msg)
else:
    print("(sin Docker: no se valida; en la captura pregrabada la configuración fue válida con otelcol-contrib 0.162.0)")
''')
    md("""
    > ⚠️ **Trampa verificada (0.162.0).** `numeric_attribute` usa **enteros** (`min_value`/`max_value` son `int64`). Con un atributo decimal como `supportops.cost_usd` el valor se trunca y, medido con el binario real, **el procesador cae con un SIGSEGV**
    > (`nil pointer` en `EvaluateWithThreshold`) en cuanto aparece una traza con ese atributo. Para costes fraccionarios usa **`ottl_condition`** (admite decimales: `attributes["supportops.cost_usd"] > 0.0005`) o un atributo entero (micro-USD).
    """)
    code('''
if DOCKER:
    probe = S.numeric_attribute_probe(CORPUS)
else:
    probe = REC["numeric_probe"]
display(pd.Series(probe, name="resultado con el Collector 0.162.0 real").to_frame())
''')
    code('''
if DOCKER:
    real = S.run_collector_experiment(CORPUS, policies, decision_wait="2s")
else:
    real = REC["collector"]
sim = S.TailSampler(policies, decision_wait_s=2).run(CORPUS.traces)
pol_names = ["errors", "slow", "costly", "baseline"]
fig, axs = plt.subplots(1, 2, figsize=(12.5, 3.8))
x = np.arange(len(pol_names))
axs[0].bar(x - 0.2, [sim.by_policy.get(n, 0) for n in pol_names], 0.4, color=viz.PALETTE["neutral"], label="simulador (Python)")
axs[0].bar(x + 0.2, [real["per_policy"].get(n, 0) for n in pol_names], 0.4, color=viz.PALETTE["profiles"], label="Collector real")
axs[0].set_xticks(x); axs[0].set_xticklabels(pol_names); axs[0].set_ylabel("trazas con voto «conservar»"); axs[0].set_title("Votos por política: simulador vs real"); axs[0].legend()
covr = real["coverage"]
keys = ["recall_error_pct", "recall_slow_pct", "recall_costly_pct", "kept_bytes_pct"]
axs[1].bar(keys, [covr[k] for k in keys], color=[viz.PALETTE["error"], viz.PALETTE["warn"], viz.PALETTE["metrics"], viz.PALETTE["neutral"]])
axs[1].set_title("Lo que SALIÓ del Collector real"); axs[1].set_ylabel("%"); axs[1].tick_params(axis="x", labelsize=8)
plt.tight_layout(); plt.show()
print(f"conservadas: real {real['n_kept']} · simulador {len(sim.kept)} (la diferencia está solo en la política «baseline»: el Collector hace su propio hash FNV, nosotros SHA-256, y ambas dan ≈ 10 %)")
print({k.replace("otelcol_processor_tail_sampling_", ""): v for k, v in real["internal"].items() if "dropped" in k or "on_memory" in k})
''')
    md(observe("""
    - Las políticas **errors, slow y costly votan exactamente igual** en el simulador y en el Collector real (119, 69 y 24 trazas con voto): el simulador es una herramienta fiable para diseñar la política **antes** de desplegarla. Solo difiere el 10 % base (distinta función hash → mismo ratio estadístico).
    - Del Collector sale el **100 % de lo interesante** con ≈ 22-23 % de los bytes. `sampling_trace_dropped_too_early = 0` confirma que `num_traces` fue suficiente.
    - El estado vive en el procesador: reiniciar el Collector pierde las trazas pendientes (de ahí `decision_cache` y, en el futuro, `tail_storage`, experimental).
    """))

    code('''
nt = REC["num_traces"] if not DOCKER else None
if DOCKER:
    pols2 = [S.StatusCode(("ERROR",), name="errors"), S.Probabilistic(10, name="baseline")]
    nt = []
    for n in (200, 50_000):
        rr = S.run_collector_experiment(CORPUS, pols2, decision_wait="5s", num_traces=n)
        nt.append({"num_traces": n, "n_kept": rr["n_kept"], "recall_error_pct": rr["coverage"].get("recall_error_pct"),
                   "dropped_too_early": rr["internal"].get("otelcol_processor_tail_sampling_sampling_trace_dropped_too_early"), "on_memory": rr["internal"].get("otelcol_processor_tail_sampling_sampling_traces_on_memory")})
display(pd.DataFrame(nt).rename(columns={"n_kept": "trazas conservadas", "recall_error_pct": "% errores conservados", "dropped_too_early": "descartadas antes de decidir", "on_memory": "en memoria al final"}).round(1))
''')
    md(observe("""
    - Con `num_traces: 200` y una ráfaga de 1 500 trazas el Collector real **descartó 1 300 sin decidir** (el simulador predijo exactamente 1 300) y solo conservó ≈ 13 % de los errores. Con `num_traces` suficiente, el 100 %.
    - Es el modo de fallo más traicionero del tail sampling: **no hay error visible**, solo una métrica interna. Alerta sobre ella.
    """))

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ## 7 · El muestreo sesga las métricas derivadas

    Si construyes métricas RED **a partir de los spans que sobreviven** (un `span_metrics` *después* del muestreo, o contando trazas en Tempo), lo que ves es la **muestra**, no la población. Con tail sampling por errores la tasa de errores sale inflada; con head sampling, las latencias son insesgadas pero ruidosas.
    Dos remedios: **(a)** calcular las métricas **antes** de muestrear (el conector `span_metrics` en `traces/in`, como en §6) o **(b)** ponderar cada traza por `1/π`.
    """)
    code('''
truth = S.estimate_metrics(CORPUS.traces)
tail_kept = S.TailSampler(policies, 30).run(CORPUS.traces).kept
naive_tail = S.estimate_metrics(tail_kept)
keep_all = lambda t: t.interesting                                 # lo que las políticas conservan SIEMPRE (π = 1)
w = S.inclusion_weights(tail_kept, keep_all, base_ratio=0.10)     # π = 1 para lo interesante, π = 0,10 para el resto
weighted_tail = S.estimate_metrics(tail_kept, w)
head_kept = S.head_sample(CORPUS.traces, 0.10)
head_est = S.estimate_metrics(head_kept)                          # head uniforme: sin pesos ya es insesgado (π constante)
red_before = {"error_rate": (real["red"].get("STATUS_CODE_ERROR", 0) / sum(real["red"].values())) if real.get("red") else float("nan")}
rows = {"verdad (población)": truth, "tail SIN pesos (sesgado)": naive_tail, "tail con pesos 1/π": weighted_tail, "head 10 % (uniforme)": head_est}
df = pd.DataFrame(rows).T[["requests", "error_rate", "mean_cost_usd", "p50_s", "p95_s"]]
display(df.round(4))
fig, axs = plt.subplots(1, 3, figsize=(13.5, 3.8))
cols = [viz.PALETTE["dark"], viz.PALETTE["error"], viz.PALETTE["ok"], viz.PALETTE["traces"]]
for ax, key, ttl in zip(axs, ("error_rate", "p50_s", "p95_s"), ("tasa de error", "latencia p50 (s)", "latencia p95 (s)")):
    ax.bar(range(4), df[key].values, color=cols); ax.set_xticks(range(4)); ax.set_xticklabels(["verdad", "tail\\nsin pesos", "tail\\ncon pesos", "head\\n10 %"], fontsize=8); ax.set_title(ttl)
axs[0].axhline(red_before["error_rate"], color=viz.PALETTE["metrics"], ls="--", lw=2); axs[0].text(3.4, red_before["error_rate"], "span_metrics\\nANTES de muestrear", fontsize=7.5, color=viz.PALETTE["metrics"], ha="right", va="bottom")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Tail sin pesos**: la tasa de error pasa de ≈ 2,6 % real a ≈ **12 %** (casi 5×) y la p95 de la latencia de ≈ 4,7 s a ≈ 14,6 s, porque conservamos *todo* lo malo y solo el 10 % de lo normal. Un panel construido sobre esas trazas «dice» que el sistema está roto.
    - **Con pesos 1/π** (1 para lo interesante, 10 para la base) las estimaciones vuelven a la verdad (error ≈ 2,3 % frente a 2,6 %: la diferencia es el ruido del 10 % base). **Head uniforme** ya es insesgado sin pesos (π constante) pero con ruido.
    - La línea naranja es la tasa de error del conector `span_metrics` **del Collector real, calculada antes del muestreo**: coincide con la verdad (≈ 2,6 %) con cero matemáticas. Es la solución de producción: **métricas antes, trazas después**.
    """))

    # ------------------------------------------------------------------------------------------------ 8
    md("""
    ## 8 · Cardinalidad: el coste se paga en series, no en puntos

    En Prometheus, la memoria depende del nº de **series activas** (combinaciones únicas de etiquetas), no de cuántas muestras tiene cada una. La cota de series de una métrica es el **producto** de las cardinalidades de sus etiquetas.
    """)
    code('''
dims_ok = {"intent": 4, "status": 5, "tier": 3, "model": 2}
dims_storm = {**dims_ok, "ticket_id": 2_000_000}
tab = pd.DataFrame([{"etiquetas": ", ".join(d), "series (cota)": S.series_estimate(d)} for d in (dims_ok, {**dims_ok, "customer_id": 10_000}, dims_storm)])
display(tab)
''')
    code('''
sizes = (2000, 10000, 30000)                               # ≈ 1 min en total con Docker
if DOCKER:
    storm = [dict(n=n, bounded=False, **S.storm_experiment(n, bounded=False, interval_s=3, settle_s=10)) for n in sizes] + [dict(n=sizes[-1], bounded=True, **S.storm_experiment(sizes[-1], bounded=True, interval_s=3, settle_s=10))]
else:
    storm = [r for r in REC["storm"] if r["n"] in sizes or r["bounded"]]
st = pd.DataFrame(storm)
unb = st[~st["bounded"]]; bnd = st[st["bounded"]]
fig, axs = plt.subplots(1, 2, figsize=(12, 3.8))
axs[0].plot(unb["series_added"], unb["rss_mb_after"] - unb["rss_mb_before"], "o-", color=viz.PALETTE["error"], lw=2, label="con la etiqueta ticket_id")
axs[0].scatter(bnd["series_added"], bnd["rss_mb_after"] - bnd["rss_mb_before"], s=90, color=viz.PALETTE["ok"], zorder=3, label="acotado con un View del SDK")
axs[0].set_xlabel("series activas añadidas (Prometheus real)"); axs[0].set_ylabel("memoria RSS añadida (MB)"); axs[0].set_title("Memoria de Prometheus ∝ series"); axs[0].legend(fontsize=8)
per = (unb["rss_mb_after"] - unb["rss_mb_before"]) / unb["series_added"] * 1000
axs[1].bar([f"{int(n):,}" for n in unb["series_added"]], per, color=viz.PALETTE["metrics"]); axs[1].set_xlabel("series"); axs[1].set_ylabel("KB de RSS por serie"); axs[1].set_title("Coste unitario ≈ 1-3 KB por serie")
plt.tight_layout(); plt.show()
print(st[["n", "bounded", "series_added", "rss_mb_before", "rss_mb_after"]].round(1).to_string(index=False))
''')
    md(observe("""
    - Con 30 000 valores distintos de `ticket_id` Prometheus añadió ≈ 30 000 series y **≈ 80 MB de RSS** (≈ 1-3 KB por serie; con pocas series el GC enmascara la cifra). Extrapola: 2 millones de tickets/día con ese label ⇒ **gigabytes de memoria**, y OOM del Prometheus.
    - Con un **View del SDK** que solo permite la etiqueta `intent`, las mismas 30 000 peticiones producen **5 series**. El arreglo está en el origen: el id va en el **span** (alta cardinalidad barata) y, si hace falta, en un **exemplar**, nunca como etiqueta.
    - Defensas por capas: (1) revisión de etiquetas en el código (módulo 09), (2) *Views* en el SDK, (3) `sample_limit`/`label_limit` por trabajo de scrape en Prometheus (`configs/prometheus-scrape-limits.yaml`: una tormenta ⇒ el scrape falla, no se acumula), (4) alerta sobre `prometheus_tsdb_head_series`.
    """))

    # ------------------------------------------------------------------------------------------------ 9
    md("""
    ## 9 · Multi-tenant y límites de ingesta (Tempo y Loki reales)

    Un **tenant** es una frontera de aislamiento y de límites: equipos, entornos o clientes. En Loki se activa con `auth_enabled: true` y en Tempo con `multitenancy_enabled: true`; cada petición lleva la cabecera `X-Scope-OrgID`.
    Prometheus **no** tiene multi-tenant nativo (Mimir sí). Los límites (`limits_config` en Loki, `overrides` en Tempo) convierten un tenant ruidoso en errores **para él**, no en una caída para todos.
    """)
    code('''
if DOCKER:
    BK = S.backends_experiment(CORPUS)
else:
    BK = REC["backends"]
rows = []
for backend in ("loki", "tempo"):
    for k, v in BK[backend].items():
        if not k.startswith("_") and k != "descartes":
            rows.append({"backend": backend, "prueba": k, "resultado": v})
display(pd.DataFrame(rows))
print("Descartes de Tempo:", BK["tempo"].get("descartes"))
print("Loki dijo (límite de streams):", BK["loki"]["_msg_streams"][:150])
print("Loki dijo (etiquetas):", BK["loki"]["_msg_labels"][:150])
''')
    code('''
fig, axs = plt.subplots(1, 2, figsize=(12.5, 3.6))
l = BK["loki"]
axs[0].bar(["A", "B", "otro\\ntenant"], [l["líneas visibles para A"], l["líneas visibles para B"], l["líneas visibles para tenant desconocido"]], color=[viz.PALETTE["traces"], viz.PALETTE["logs"], viz.PALETTE["neutral"]])
axs[0].set_title("Loki: líneas visibles por tenant (A intentó 40, límite 20 streams)"); axs[0].set_ylabel("líneas")
tp = BK["tempo"]
axs[1].bar(["A", "B"], [tp["trazas visibles para A"], tp["trazas visibles para B"]], color=[viz.PALETTE["traces"], viz.PALETTE["logs"]]); axs[1].set_title("Tempo: trazas visibles por tenant"); axs[1].set_ylabel("trazas")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Aislamiento**: cada tenant solo ve lo suyo, un tenant desconocido ve 0 y **sin cabecera la petición se rechaza** (Loki 401 «no org id»; Tempo 401 en consulta).
    - **Límites con mensajes accionables**: Loki devolvió **429** («maximum active stream limit exceeded», streams > 20), **400** («has 11 label names; limit 8») y **429** por tasa; Tempo aceptó la traza pero **descartó sus spans** con `reason="trace_too_large"` (`tempo_discarded_spans_total`).
    - Un límite de Tempo **no siempre rechaza la petición**: descarta en silencio y solo lo ves en la métrica. El dashboard 18 incluye ese panel.
    """))
    md("""
    Configuraciones de referencia del módulo (archivos reales en `configs/`, verificados con las herramientas oficiales):
    """)
    code('''
CONF = ROOT / "18_escala_muestreo_coste" / "configs"
for f in sorted(CONF.iterdir()):
    print(f"── {f.name} ({len(f.read_text().splitlines())} líneas)")
if DOCKER:
    ok = {}
    okc, _ = S.validate_collector_config((CONF / "collector-tail-sampling.yaml").read_text()); ok["collector-tail-sampling.yaml (otelcol validate)"] = okc
    for f, img, args in (("loki-multitenant-limits.yaml", S.LOKI_IMAGE, ["-verify-config"]), ("loki-retention.yaml", S.LOKI_IMAGE, ["-verify-config"]),
                         ("tempo-multitenant-limits.yaml", S.TEMPO_IMAGE, ["-config.verify=true"]), ("tempo-retention.yaml", S.TEMPO_IMAGE, ["-config.verify=true"])):
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{CONF / f}:/c.yaml:ro", img, "-config.file=/c.yaml", *args], capture_output=True, text=True)
        ok[f] = r.returncode == 0 and "CONFIG ERROR" not in r.stdout + r.stderr
    r = subprocess.run(["docker", "run", "--rm", "--entrypoint", "promtool", "-v", f"{CONF / 'prometheus-scrape-limits.yaml'}:/p.yml:ro", S.PROM_IMAGE, "check", "config", "/p.yml"], capture_output=True, text=True)
    ok["prometheus-scrape-limits.yaml (promtool)"] = r.returncode == 0
    print({k: "✅" if v else "❌" for k, v in ok.items()})
else:
    print("(sin Docker) todas pasaron la validación oficial al construir el módulo")
print((CONF / "tempo-multitenant-limits.yaml").read_text()[:900])
''')

    # ------------------------------------------------------------------------------------------------ 10
    md("""
    ## 10 · Retención y niveles (*tiering*)

    La retención es el tercer mando. Cada backend la configura de forma distinta (los tres están en `configs/`):

    | Backend | Cómo | Matiz verificado |
    |---|---|---|
    | **Loki** | `limits_config.retention_period` + `retention_stream` (por selector y prioridad) + `compactor.retention_enabled: true` | **Exige** `compactor.delete_request_store` (si falta: «CONFIG ERROR»). Borrado diferido (`retention_delete_delay`) |
    | **Tempo 3.x** | `backend_scheduler…compaction.block_retention` y `overrides.defaults.compaction.block_retention` (por tenant) | el compactor pasó al `backend_scheduler` en Tempo 3 |
    | **Prometheus** | *flags* `--storage.tsdb.retention.time` y `--storage.tsdb.retention.size` | tamaño o tiempo: lo que se cumpla primero |

    **Niveles**: lo reciente y consultado a menudo va en almacenamiento *caliente* (SSD, caro); lo antiguo, en almacenamiento de objetos (barato, más lento). El tail sampling y la retención se **multiplican**: conservar solo lo interesante y durante más tiempo cuesta menos que conservarlo todo poco tiempo.
    """)
    code('''
daily = S.StackCostModel.from_corpus(CORPUS, 1_000_000, spans_per_trace=40, bytes_per_span=2500)   # escenario de producción (supuesto marcado)
traces_gb = daily.daily_gb()["traces_stored"]
fig, axs = plt.subplots(1, 2, figsize=(12.5, 3.9))
days = np.arange(1, 91)
flat = traces_gb * days * 0.10
tiered = np.array([traces_gb * min(d, 7) * 0.10 + traces_gb * max(0, d - 7) * 0.023 for d in days])
sampled = tiered * 0.23
axs[0].plot(days, flat, color=viz.PALETTE["error"], lw=2, label="todo en caliente")
axs[0].plot(days, tiered, color=viz.PALETTE["warn"], lw=2, label="7 d caliente + resto frío")
axs[0].plot(days, sampled, color=viz.PALETTE["ok"], lw=2, label="… y solo el 23 % (tail sampling)")
axs[0].set_xlabel("días de retención"); axs[0].set_ylabel("USD/mes en régimen estacionario (ilustrativo)"); axs[0].set_title("Retención × nivel × muestreo"); axs[0].legend(fontsize=8)
tiers = [("caliente 7 d", 7, 0.10), ("frío 23 d", 23, 0.023), ("archivo 60 d", 60, 0.004)]
rc = pd.DataFrame(S.retention_cost(traces_gb * 0.23, tiers))
axs[1].bar(rc["tier"], rc["usd_per_month"], color=[viz.PALETTE["error"], viz.PALETTE["warn"], viz.PALETTE["ok"]]); axs[1].set_ylabel("USD/mes (ilustrativo)"); axs[1].set_title("Reparto por nivel de lo conservado (90 días)")
for i, (g, c) in enumerate(zip(rc["resident_gb"], rc["usd_per_month"])): axs[1].text(i, c, f"{g:,.0f} GB", ha="center", va="bottom", fontsize=8)
plt.tight_layout(); plt.show()
print(f"trazas guardadas al día (escenario de producción): {traces_gb:,.0f} GB → con el 23 % del tail sampling: {traces_gb*0.23:,.0f} GB/día. PRECIOS ILUSTRATIVOS (parámetros): sustitúyelos por los de tu proveedor.")
''')
    md(observe("""
    - La retención es **lineal** en días, pero el nivel frío cuesta ≈ 4× menos por GB: la curva «7 d caliente + resto frío» sube mucho más despacio. Combinada con el tail sampling (solo ≈ 23 % de los bytes), la política completa es ≈ **10× más barata** que «todo en caliente».
    - El 90 % del coste cae en el **primer nivel** si su retención es corta pero su precio alto: ajusta la ventana caliente a lo que de verdad consultan tus on-calls (normalmente 3-7 días).
    - Todos los precios son **ilustrativos** (parámetros de `StackCostModel`); el método (volumen medido × días × precio por nivel) es lo que se traslada.
    """))

    # ------------------------------------------------------------------------------------------------ 11
    md("""
    ## 11 · El coste del stack con y sin política

    Juntamos todo: volumen medido → coste mensual del stack con la **política completa** (tail sampling, logs correlacionados, retención por señal, métricas acotadas). Escenario de producción **supuesto** (40 spans, contenido capturado) para ver la escala; SupportOps medido queda como referencia.
    """)
    code('''
before = S.StackCostModel.from_corpus(CORPUS, 2_000_000, spans_per_trace=40, bytes_per_span=2500, log_lines_per_ticket=12, bytes_per_log_line=600, ingest_price_gb=0.0)
kept_bytes = S.coverage(res.kept, CORPUS)["kept_bytes_pct"] / 100
after = S.StackCostModel.from_corpus(CORPUS, 2_000_000, spans_per_trace=40, bytes_per_span=2500, log_lines_per_ticket=12, bytes_per_log_line=600, trace_keep=kept_bytes, log_keep=0.35)
ret = {"traces": 30, "logs": 14, "metrics": 90}; hot = {"traces": 7, "logs": 7, "metrics": 15}
rows = []
for name, m, r_, h_ in (("sin política (todo, 7 d caliente)", before, {"traces": 7, "logs": 7, "metrics": 15}, {"traces": 7, "logs": 7, "metrics": 15}), ("con política (tail + logs 35 %, retención por señal)", after, ret, hot)):
    c = m.monthly_cost(r_, h_)
    rows.append({"escenario": name, **{k: round(v, 0) for k, v in c.items()}, "GB/día de trazas ingeridas": round(m.daily_gb()["traces_ingest"], 1)})
df = pd.DataFrame(rows); display(df)
fig, ax = plt.subplots(figsize=(8.5, 3.6))
bot = np.zeros(2)
for k, col in (("traces", viz.PALETTE["traces"]), ("logs", viz.PALETTE["logs"]), ("metrics", viz.PALETTE["metrics"])):
    ax.bar(["sin política", "con política"], df[k].values, bottom=bot, color=col, label=k); bot += df[k].values
ax.set_ylabel("USD/mes (ilustrativo, autoalojado)"); ax.set_title("Coste mensual del almacenamiento: 2 M tickets/día (escenario supuesto)"); ax.legend(); plt.show()
''')
    md(observe("""
    - El grueso del coste de almacenamiento son las **trazas** (por el contenido) y los **logs**; las métricas, aun con 90 días, cuestan poco **si las series están acotadas**.
    - La política (tail sampling + menos logs + retención por señal) reduce el coste de forma **multiplicativa**, y además **alarga** la retención de lo valioso (30 días de trazas interesantes frente a 7 de todo).
    - En un SaaS el término dominante es el **precio por GB ingerido**: `StackCostModel(ingest_price_gb=…)` lo incorpora; ahí el muestreo antes de salir de tu red (Collector) es lo que más ahorra.
    """))

    # ------------------------------------------------------------------------------------------------ 12
    md("""
    ## 12 · Diseño de la política de SupportOps y su impacto

    Resumen de decisiones, cada una respaldada por una medida de este módulo:

    | Decisión | Valor | Evidencia |
    |---|---|---|
    | Muestreo | **Tail** con `errors` + `slow` (≥ 5 s) + `costly` (> 0,0005 USD, OTTL) + 10 % base | recall 100 % de lo interesante con ≈ 23 % de los bytes (§5-6) |
    | Métricas RED | **Antes** del muestreo (`span_metrics` en `traces/in`) | error 2,6 % exacto (§7) |
    | Memoria | `num_traces` ≥ tráfico × `decision_wait` × 1,5; alerta si `dropped_too_early` > 0 | §5.1 y §6 |
    | Cardinalidad | `intent`, `status`, `tier`, `model` en métricas; ids solo en spans/logs; `sample_limit` en el scrape | §8 |
    | Tenants | un tenant por entorno/equipo, límites explícitos y alertas sobre descartes | §9 |
    | Retención | trazas interesantes 30 d (7 d caliente), base 7 d; logs 14 d (errores 30 d); métricas 90 d | §10 |
    """)
    code('''
final = S.TailSampler(policies, decision_wait_s=30).run(CORPUS.traces)
c = S.coverage(final.kept, CORPUS)
summary = pd.Series({"trazas conservadas (%)": c["kept_traces_pct"], "spans conservados (%)": c["kept_spans_pct"], "bytes conservados (%)": c["kept_bytes_pct"], "recall errores (%)": c["recall_error_pct"],
                     "recall lentas (%)": c["recall_slow_pct"], "recall caras (%)": c["recall_costly_pct"], "reducción de volumen (×)": 100 / c["kept_bytes_pct"]}, name="impacto de la política").round(1)
display(summary.to_frame())
fig, ax = plt.subplots(figsize=(9, 3.4))
labels = ["volumen", "bytes de trazas", "memoria del Collector\\n(pico, trazas)"]
ax.bar(["sin política", "con política"], [100, c["kept_bytes_pct"]], color=[viz.PALETTE["neutral"], viz.PALETTE["ok"]]); ax.set_ylabel("% del volumen ingerido en el backend de trazas"); ax.set_title("Impacto de la política en el volumen de trazas (lo interesante: 100 % conservado)")
plt.show()
''')
    md(observe("""
    - La política reduce el volumen de trazas a **≈ ¼** sin perder ni una traza interesante del corpus, con métricas exactas y memoria acotada. Es el patrón que se despliega en el módulo 19 (Collector de dos capas en Kubernetes).
    - El proyecto te pide diseñar esta política con **presupuesto** (bytes, recall, memoria) y medir su impacto.
    """))

    md("""
    ## 13 · 🏭 En producción

    - **Dapper** (Google, 2010) muestreaba una traza de cada 1 024 por defecto y lo hacía **adaptativo** según la carga; es el origen del muestreo *head* de baja probabilidad.
    - **Honeycomb Refinery** es un proxy de *tail sampling* (código abierto) con **muestreo dinámico**: mantiene tasas distintas según claves (endpoint, código de estado) para conservar la diversidad y pondera las trazas (`SampleRate`) para que los agregados se corrijan: exactamente la idea de los pesos 1/π de §7.
    - En el **Collector contrib** la arquitectura recomendada es de **dos capas**: una de Collectors con el exportador `load_balancing` (por `traceID`) y otra con `tail_sampling`, para garantizar que todos los spans de una traza lleguen al mismo nodo.
    - **Grafana Cloud** ofrece *Adaptive Metrics* (agregación automática de series poco usadas) y límites por tenant en Mimir/Loki/Tempo; en OSS se logra con `limits_config`/`overrides` (§9) y revisión de series.
    - **OpenTelemetry** trabaja en muestreo por **umbral consistente** (`th`/`rv` en `tracestate`): cada decisión anota su probabilidad, de modo que se pueden **recomponer los pesos** aguas abajo. El procesador `tail_sampling` lo soporta tras una *feature gate* (`processor.tailsamplingprocessor.usetracestate`). ⚠️ Estado: en evolución, verifica antes de depender de ello.
    """)
    md("""
    ## 14 · 🧠 Secretos de la élite

    1. **Métricas antes, trazas después.** Cualquier métrica derivada de spans que ya fueron muestreados está sesgada (§7: 2,6 % → ≈ 12 %). Calcula RED en `traces/in` con `span_metrics` y muestrea solo lo que va a almacenarse.
    2. **El modo de fallo del tail sampling es silencioso.** Si `num_traces` < tráfico × `decision_wait`, el Collector descarta trazas **sin evaluarlas** y sin error (medido: 1 300 de 1 500 perdidas; recall de errores 13 %). Vigila `sampling_trace_dropped_too_early`.
    3. **`numeric_attribute` es de enteros.** Con un atributo decimal y solo `min_value` el Collector 0.162.0 **cae con SIGSEGV** (medido). Usa `ottl_condition` para decimales. Moraleja general: prueba cada política con el binario real y datos reales.
    4. **Cuidado con la composición de probabilidades.** Un head sampling del 10 % *delante* de un tail con baseline del 10 % deja ≈ 1 % de la base… y **solo el 10 % de los errores** (el head ya los tiró). El tail solo ve lo que le llega.
    5. **El coste de las métricas está en las series, no en las muestras.** ≈ 1-3 KB de RAM por serie (medido). Un `ticket_id` en una etiqueta convierte tu Prometheus en un contador de tickets.
    6. **Los logs dependen de las trazas.** Si descartas una traza pero conservas sus logs, el `trace_id` queda **colgando** (el salto de Grafana no encuentra nada). Decide la retención de logs y trazas **juntas**, o muestrea los logs con la misma decisión.
    7. **Los límites por tenant son tu radio de explosión.** Sin ellos, un solo servicio con un bucle de logs consume la ingesta de todos. Con ellos, el error es 429 para él y se ve en una métrica.
    8. **Una política sin presupuesto es una opinión.** Fija límite de bytes/s (`bytes_limiting`/`rate_limiting`) como red de seguridad para que un incidente masivo (todo falla ⇒ todo es «interesante») no multiplique tu factura justo cuando más telemetría se emite.
    """)
    md("""
    ## 15 · ⚠️ Errores comunes

    - Muestrear en el SDK **y** en el Collector sin coordinar: las probabilidades se **multiplican** y pierdes los errores.
    - Poner `tail_sampling` en un Collector con varias réplicas sin balanceo por `trace_id`: decisiones parciales y trazas rotas.
    - Calcular la tasa de error sobre trazas muestreadas (en el corpus: 2,6 % real frente a ≈ 12 % medido).
    - Etiquetas con ids, e-mails o rutas con parámetros en métricas.
    - Activar `retention_enabled` en Loki sin `delete_request_store` (no arranca) o creer que Tempo/Loki **rechazan** siempre al superar un límite (Tempo descarta en silencio).
    - Fijar `decision_wait` demasiado corto: las trazas lentas llegan incompletas y la política `latency` no las ve enteras.
    - Olvidar que los precios y ratios de compresión de los modelos de coste son **supuestos**: mide los tuyos.
    """)
    md(mdj("""
    ## 16 · Autoevaluación
    """,
           details("1. (Cálculo) Con head sampling p = 5 % y 40 errores en la hora, ¿cuántos errores esperas ver y con qué probabilidad no ves ninguno?",
                   "Esperados: $40\\cdot0{,}05=2$. Probabilidad de ninguno: $(1-0{,}05)^{40}=0{,}95^{40}\\approx 12,9\\,\\%$. Con tail sampling por `status_code` verías los 40."),
           details("2. (Cálculo) Tráfico de 200 trazas nuevas/s y `decision_wait` de 30 s. ¿Qué `num_traces` mínimo pones y cuánta memoria de spans (traza de 40 spans × 2,5 KB)?",
                   "Trazas en memoria ≈ 200·30 = 6 000; con margen ×1,5 → `num_traces` ≈ 9 000. Memoria de datos ≈ 6 000 · 40 · 2,5 KB = **600 MB** (solo spans; el procesador añade estructuras: deja margen y comprueba `otelcol_processor_tail_sampling_sampling_traces_on_memory`)."),
           details("3. (Cálculo) Tras un tail sampling que conserva todo lo interesante (π = 1) y el 10 % del resto, conservas 120 trazas interesantes y 90 normales. ¿Cuántas trazas había en la población y qué tasa de error real si 100 de las interesantes son errores?",
                   "Población estimada $\\hat N=120\\cdot1+90\\cdot10=1\\,020$. Errores estimados: $100\\cdot1=100$ → tasa ≈ $100/1020=9,8\\,\\%$ (sin pesos saldría $100/210=47,6\\,\\%$)."),
           details("4. (Diagnóstico) Tu panel «tasa de error del agente» construido con span metrics sobre trazas conservadas sube de 3 % a 45 % tras activar tail sampling, pero los tickets fallidos no han cambiado. ¿Qué pasó y cómo lo arreglas?",
                   "El muestreo conserva casi todos los errores y poco de lo normal ⇒ la **muestra** tiene más errores que la **población**. Mueve el cálculo de RED **antes** del muestreo (`span_metrics` en la canalización previa), o pondera por 1/π."),
           details("5. (Diagnóstico) Tras reiniciar los Collectors con tail sampling, durante 5 minutos faltan trazas de errores conocidos y no hay ningún error en los logs del Collector. ¿Qué miras?",
                   "`sampling_trace_dropped_too_early` (¿`num_traces` insuficiente en el arranque/ráfaga?), `sampling_traces_on_memory`, y la pérdida de estado del procesador al reiniciar (las trazas pendientes se pierden salvo `decision_cache`/`drop_pending_traces_on_shutdown`). También la afinidad por `traceID` del balanceador."),
           details("6. (Transferencia) Debes dar a 12 equipos acceso a Tempo y Loki con presupuestos distintos. Diseña tenants, límites y alertas.",
                   "Un tenant por equipo/entorno (`X-Scope-OrgID`), `limits_config` (Loki: `ingestion_rate_mb`, `max_streams_per_user`, `max_label_names_per_series`) y `overrides` por tenant (Tempo: `max_bytes_per_trace`, `rate_limit_bytes`), retención por tenant, y alertas sobre `tempo_discarded_spans_total` por motivo y 429 de Loki por tenant. Un panel de coste por tenant (bytes ingeridos × precio) para que cada equipo vea su factura."),
           details("7. (Transferencia) ¿Cómo adaptarías la política si el producto añade un agente de ventas con 100× más tráfico y ningún criterio de «interesante» más allá de errores?",
                   "Separar por servicio/tenant con políticas propias; para el agente de alto volumen, `rate_limiting`/`bytes_limiting` como techo, baseline más bajo (1 %), y `and` de `service.name` con `probabilistic`; métricas RED antes del muestreo; reevaluar el dimensionado de `num_traces` con el nuevo tráfico.")))

    md("""
    ## 17 · Referencias

    - OpenTelemetry Collector contrib, `tailsamplingprocessor` (README, v0.162.0): https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/v0.162.0/processor/tailsamplingprocessor (políticas, `decision_wait`, `num_traces`, métricas internas, estabilidad *beta*).
    - OpenTelemetry, *Tracestate probability sampling* (muestreo consistente por umbral): https://opentelemetry.io/docs/specs/otel/trace/tracestate-probability-sampling/
    - Sigelman, B. H. et al. (2010). *Dapper, a Large-Scale Distributed Systems Tracing Infrastructure*. Google Technical Report.
    - Honeycomb Refinery (tail sampling dinámico): https://github.com/honeycombio/refinery
    - Grafana Loki, configuración (`limits_config`, `compactor`): https://grafana.com/docs/loki/latest/configure/ · Grafana Tempo, configuración (`overrides`, `multitenancy_enabled`): https://grafana.com/docs/tempo/latest/configuration/
    - Prometheus, configuración de scrape (`sample_limit`, `label_limit`) y almacenamiento (retención): https://prometheus.io/docs/prometheus/latest/configuration/configuration/ · https://prometheus.io/docs/prometheus/latest/storage/
    - Horvitz, D. G. y Thompson, D. J. (1952). *A generalization of sampling without replacement from a finite universe*. JASA 47(260).
    """)
    nb.save(out)


# =====================================================================================================================
# Proyecto
# =====================================================================================================================
SOLUTION_18 = '''
def volume_report(corpus, tickets_per_day):
    sm = corpus.summary()
    inter = [t for t in corpus.traces if t.interesting]
    return {"spans_per_trace": sm["spans_per_trace"], "bytes_per_span": sm["bytes_per_span"], "interesting_rate": sm["interesting_rate"],
            "interesting_bytes_frac": sum(t.bytes for t in inter) / corpus.total_bytes,
            "gb_per_day_traces": tickets_per_day * sm["spans_per_trace"] * sm["bytes_per_span"] / 1e9}

def baseline_for_budget(corpus, budget_bytes_pct):
    vr = volume_report(corpus, 1)
    i = vr["interesting_bytes_frac"]
    b = (budget_bytes_pct / 100 - i) / (1 - i)
    return max(0.0, math.floor(b * 1000) / 10)          # en % con un decimal, hacia abajo

def build_policies(baseline_pct):
    return [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"),
            S.AttrCompare("supportops.cost_usd", ">", 0.0005, name="costly"), S.Probabilistic(baseline_pct, name="baseline")]

def num_traces_for(traces_per_s, decision_wait_s, margin=1.5):
    return int(math.ceil(traces_per_s * decision_wait_s * margin))

def evaluate(policies, corpus, decision_wait_s=30.0, rate_factor=16):
    rescaled = S.rescale_rate(corpus.traces, rate_factor)
    peak = S.TailSampler(policies, decision_wait_s, num_traces=10**9).run(rescaled).peak_traces
    nt = num_traces_for(rate_factor * len(corpus) / corpus.duration_s, decision_wait_s)
    r = S.TailSampler(policies, decision_wait_s, num_traces=nt).run(rescaled)
    return {**S.coverage(r.kept, corpus), "peak_traces": peak, "num_traces": nt, "dropped_too_early": len(r.dropped_too_early), "kept": r.kept}

def corrected_error_rate(kept, baseline_pct):
    keep_all = lambda t: t.interesting
    w = S.inclusion_weights(kept, keep_all, baseline_pct / 100)
    return S.estimate_metrics(kept, w)["error_rate"]

def collector_yaml(policies, num_traces):
    return S.collector_config(policies, decision_wait="30s", num_traces=num_traces)

def cardinality_check(dims, max_series):
    total = S.series_estimate(dims)
    if total <= max_series:
        return True, None
    return False, max(dims, key=dims.get)

def retention_plan(traces_gb_day, budget_usd_month, hot_price=0.10, cold_price=0.023, hot_days=7):
    best = 0
    for d in range(1, 366):
        cost = traces_gb_day * (min(d, hot_days) * hot_price + max(0, d - hot_days) * cold_price)
        if cost <= budget_usd_month:
            best = d
    return best

def tenant_limits():
    loki = {"max_streams_per_user": 20, "max_label_names_per_series": 8, "ingestion_rate_mb": 1, "ingestion_burst_size_mb": 1, "per_stream_rate_limit": "512KB"}
    tempo = {"global": {"max_bytes_per_trace": 3000}, "ingestion": {"rate_limit_bytes": 200000, "burst_size_bytes": 200000}}
    return loki, tempo
'''

RUBRIC_18 = '''
def run_rubric(docker=DOCKER):
    R = {}
    def chk(name, fn):
        try:
            R[name] = bool(fn())
        except NotImplementedError:
            R[name] = None
        except Exception as e:
            R[name] = False; print(f"  {name}: {type(e).__name__}: {e}")
    ref_vr = {"spans_per_trace": CORPUS.summary()["spans_per_trace"], "bytes_per_span": CORPUS.summary()["bytes_per_span"]}
    chk("R1 volume_report: spans/traza, bytes/span, fracción interesante y GB/día correctos (±1 %)", lambda: (lambda v: abs(v["spans_per_trace"] / ref_vr["spans_per_trace"] - 1) < .01 and abs(v["bytes_per_span"] / ref_vr["bytes_per_span"] - 1) < .01
        and abs(v["interesting_rate"] - CORPUS.summary()["interesting_rate"]) < 1e-9 and 0.10 < v["interesting_bytes_frac"] < 0.18 and abs(v["gb_per_day_traces"] / (1e6 * ref_vr["spans_per_trace"] * ref_vr["bytes_per_span"] / 1e9) - 1) < .01)(volume_report(CORPUS, 1e6)))
    chk("R2 baseline_for_budget: presupuesto del 25 % de los bytes → base entre 11 % y 15 %", lambda: 11.0 <= baseline_for_budget(CORPUS, 25) <= 15.0 and baseline_for_budget(CORPUS, 5) <= 0)
    def r3():
        pols = build_policies(baseline_for_budget(CORPUS, 25))
        names = [p.name for p in pols]
        res = S.TailSampler(pols, 30).run(CORPUS.traces)
        c = S.coverage(res.kept, CORPUS)
        return {"errors", "slow", "costly", "baseline"} <= set(names) and c["recall_interesting_pct"] == 100.0 and c["kept_bytes_pct"] <= 27.0
    chk("R3 build_policies: 100 % de lo interesante y ≤ 27 % de los bytes (presupuesto 25 % + ruido del hash)", r3)
    def r4():
        pols = build_policies(12.0)
        ev = evaluate(pols, CORPUS, 30.0, 16)
        return ev["dropped_too_early"] == 0 and ev["peak_traces"] <= ev["num_traces"] <= 2.2 * ev["peak_traces"] and num_traces_for(200, 30) == 9000
    chk("R4 evaluate/num_traces_for: sin descartes tempranos, num_traces entre 1× y 2,2× el pico y num_traces_for(200, 30) = 9 000", r4)
    def r5():
        b = 12.0
        kept = S.TailSampler(build_policies(b), 30).run(CORPUS.traces).kept
        truth = S.estimate_metrics(CORPUS.traces)["error_rate"]
        naive = S.estimate_metrics(kept)["error_rate"]
        est = corrected_error_rate(kept, b)
        return abs(est / truth - 1) < 0.15 and naive > 3 * truth
    chk("R5 corrected_error_rate: error relativo < 15 % frente a la verdad (el crudo está > 3× por encima)", r5)
    def r6():
        y = collector_yaml(build_policies(12.0), 9000)
        ok_text = all(k in y for k in ("tail_sampling", "span_metrics", "forward", "decision_wait", "ottl_condition")) and "numeric_attribute" not in y
        if not docker:
            return ok_text
        return ok_text and S.validate_collector_config(y)[0]
    chk("R6 collector_yaml: contiene tail_sampling + span_metrics antes del muestreo, sin numeric_attribute con decimales" + ("" if docker else " (sin Docker: solo texto)") + " y pasa `otelcol validate`", r6)
    chk("R7 cardinality_check: acepta 120 series, rechaza la tormenta y señala ticket_id", lambda: cardinality_check({"intent": 4, "tier": 3, "model": 10}, 1000) == (True, None) and cardinality_check({"intent": 4, "tier": 3, "ticket_id": 2_000_000}, 100_000) == (False, "ticket_id"))
    chk("R8 retention_plan: coincide con la referencia en 4 casos (días máximos dentro del presupuesto)", lambda: [retention_plan(g, b) for g, b in ((100, 300), (100, 1200), (20, 200), (500, 100))] == [REF_RET[(100, 300)], REF_RET[(100, 1200)], REF_RET[(20, 200)], REF_RET[(500, 100)]])
    def r9():
        if not docker:
            return None
        loki, tempo = tenant_limits()
        with S.BackendLab("loki", S.loki_lab_config(loki, auth=True)) as lk:
            now = time.time_ns()
            st = lambda n: [{"stream": {"service_name": "s", "t": f"{i}"}, "values": [[str(now + i), "x"]]} for i in range(n)]
            c_ok = lk.loki_push("a", st(10))[0]; c_bad = lk.loki_push("a", st(40))[0]
        return c_ok == 204 and c_bad == 429 and tempo["global"]["max_bytes_per_trace"] <= 5000
    chk("R9 tenant_limits (con Docker): Loki acepta 10 streams y rechaza 40 con 429; Tempo con tope de bytes por traza ≤ 5 000", r9)
    ok = sum(v is True for v in R.values()); tot = sum(v is not None for v in R.values())
    for k, v in R.items():
        print(("✅" if v else ("⏭️ " if v is None else "❌")), k)
    print(f"\\nPuntuación: {ok}/{tot} comprobaciones superadas")
    return R
'''


def build_project() -> None:
    nb, out = nb_for(MOD, "18_proyecto_escala_muestreo_coste.ipynb", "Proyecto 18 · Política de muestreo y retención de SupportOps")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 18 · Diseña la política de muestreo, cardinalidad y retención de SupportOps (con presupuesto) y mide su impacto

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 2 h 30 min |
    | **Servicios de Compose** | Ninguno. Con Docker, los pasos 6 y 9 lanzan contenedores efímeros (Collector, Loki); sin Docker se evalúan solo por texto |
    | **RAM aproximada** | < 1 GB |
    | **Prerrequisitos** | Lección `18_escala_muestreo_coste`; proyectos 05 y 16 |
    | **Conexión** | Aplica el tail sampling que el módulo 05 dejó fuera y protege los SLO del 16 (nada interesante se pierde); el resultado es el Collector de dos capas que se despliega en el módulo 19 |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. El agente pasa de piloto a producción (2 M tickets/día) y finanzas pone un tope: **las trazas conservadas no pueden pasar del 25 % de los bytes generados**, sin perder ninguna traza con error, lenta o cara,
    sin falsear la tasa de error de los paneles, con el Collector dimensionado para que no descarte trazas y con un presupuesto mensual de almacenamiento. Además, debes impedir que un servicio ruidoso (etiquetas con ids, bucles de logs, trazas gigantes) tumbe a los demás.

    ## Datos

    Corpus de 1 500 tickets (mock, semilla 42) generado en el notebook; cada traza lleva su tamaño OTLP real. Sin descargas. Con Docker puedes validar tu configuración con el Collector y Loki reales.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `volume_report` | spans/traza, bytes/span, fracción interesante y GB/día | ±1 % de lo medido; fracción de bytes interesante ∈ (10 %; 18 %) |
    | R2 | `baseline_for_budget` | porcentaje base que cumple el 25 % de bytes | 11-15 % (la solución: 13,x %); con presupuesto del 5 % → 0 |
    | R3 | `build_policies` | recall de interesantes y bytes conservados | 100 % y ≤ 27 % |
    | R4 | `num_traces_for`, `evaluate` | dimensionado sin descartes (16× tráfico, 30 s) | `dropped_too_early` = 0; pico ≤ `num_traces` ≤ 2,2 × pico; `num_traces_for(200, 30)` = 9 000 |
    | R5 | `corrected_error_rate` | tasa de error con pesos 1/π | error relativo < 15 %; la cruda > 3× la real (≈ 4,5×) |
    | R6 | `collector_yaml` | `tail_sampling` + `span_metrics` + `forward`, OTTL para el coste, sin `numeric_attribute` | texto correcto y `otelcol validate` OK (con Docker) |
    | R7 | `cardinality_check` | acepta lo sano y rechaza la tormenta señalando la etiqueta | exacto |
    | R8 | `retention_plan` | días máximos dentro de un presupuesto (4 casos) | exacto |
    | R9 | `tenant_limits` (con Docker) | Loki acepta 10 streams y rechaza 40 (429); Tempo con tope de bytes por traza ≤ 5 000 | exacto |

    > 📏 Los umbrales salen de la solución de referencia con la semilla 42 fija; las comparaciones usan ratios y rangos, no tiempos absolutos.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_18.replace("print(f\"Docker disponible", "print(f\"Docker disponible"))

    def todo(n, title, desc, stub, hints=()):
        md(f"## Paso {n} · {title}\n\n{desc}" + ("\n\n" + "\n\n".join(hint(i + 1, h) for i, h in enumerate(hints)) if hints else ""))
        code(stub)

    md("""
    ## Paso 0 · El presupuesto (te lo damos hecho)

    El corpus, el tráfico objetivo (2 M tickets/día) y el presupuesto. `REF_RET` son las respuestas de referencia del paso 8 (para la rúbrica).
    """)
    code('''
TICKETS_DAY = 2_000_000
BUDGET_BYTES_PCT = 25.0
BUDGET_USD_MONTH = 40.0
REF_RET = {}
for g, b in ((100, 300), (100, 1200), (20, 200), (500, 100)):
    REF_RET[(g, b)] = max([d for d in range(1, 366) if g * (min(d, 7) * 0.10 + max(0, d - 7) * 0.023) <= b] or [0])
print(f"{len(CORPUS)} trazas · interesantes: {SM['interesting_rate']:.1%} · bytes por traza: {SM['bytes_per_trace']:.0f} · presupuesto: ≤ {BUDGET_BYTES_PCT} % de los bytes y {BUDGET_USD_MONTH} USD/mes")
''')

    todo(1, "El volumen (TODO)",
         "Escribe `volume_report(corpus, tickets_per_day)` → dict con `spans_per_trace`, `bytes_per_span`, `interesting_rate`, `interesting_bytes_frac` (fracción de los **bytes** que pertenecen a trazas interesantes) y `gb_per_day_traces` (spans × bytes sin muestrear). Usa `corpus.summary()` y `Trace.interesting`.",
         '''
def volume_report(corpus, tickets_per_day):
    # TODO
    raise NotImplementedError("TODO 1")

try:
    print(volume_report(CORPUS, TICKETS_DAY))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["`corpus.summary()` ya trae spans por traza y bytes por span; la fracción de bytes interesantes es `sum(t.bytes for t in corpus.traces if t.interesting) / corpus.total_bytes`.", "GB/día = tickets_por_día × spans_por_traza × bytes_por_span / 1e9."])

    todo(2, "El mando del presupuesto (TODO)",
         "Escribe `baseline_for_budget(corpus, budget_bytes_pct)`: el porcentaje de muestreo base (`probabilistic`) tal que **lo interesante (siempre conservado) + base × resto** no supere el presupuesto. Redondea hacia abajo a 1 decimal; si el presupuesto no alcanza ni para lo interesante, devuelve 0.",
         '''
def baseline_for_budget(corpus, budget_bytes_pct):
    # TODO: i + b·(1 − i) ≤ presupuesto, con i = fracción de bytes interesantes
    raise NotImplementedError("TODO 2")

try:
    print(baseline_for_budget(CORPUS, BUDGET_BYTES_PCT), baseline_for_budget(CORPUS, 5))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Es una ecuación lineal: despeja b de $i + b(1-i) \\le B$.", "`b = (B/100 - i) / (1 - i)`; el resultado en % con `math.floor(b*1000)/10`; `max(0, ...)`."])

    todo(3, "Las políticas (TODO)",
         "Escribe `build_policies(baseline_pct)` → lista de políticas con **esos nombres**: `errors` (`StatusCode`), `slow` (`Latency` ≥ 5 000 ms), `costly` (`AttrCompare` sobre `supportops.cost_usd` > 0,0005; **no** `NumericAttribute`: recuerda la trampa del int64) y `baseline` (`Probabilistic`).",
         '''
def build_policies(baseline_pct):
    # TODO: S.StatusCode, S.Latency, S.AttrCompare, S.Probabilistic (con name=...)
    raise NotImplementedError("TODO 3")

try:
    pols = build_policies(baseline_for_budget(CORPUS, BUDGET_BYTES_PCT))
    c = S.coverage(S.TailSampler(pols, 30).run(CORPUS.traces).kept, CORPUS)
    print({k: round(v, 1) for k, v in c.items()})
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Cada clase de `S` tiene los mismos parámetros que la clave del Collector (`threshold_ms`, `status_codes`, `sampling_percentage`).", "`S.StatusCode((\"ERROR\",), name=\"errors\")`, `S.Latency(5000, name=\"slow\")`, `S.AttrCompare(\"supportops.cost_usd\", \">\", 0.0005, name=\"costly\")`, `S.Probabilistic(pct, name=\"baseline\")`."])

    todo(4, "El dimensionado (TODO)",
         "Escribe `num_traces_for(traces_per_s, decision_wait_s, margin=1.5)` y `evaluate(policies, corpus, decision_wait_s, rate_factor)`, que simula el tráfico ×`rate_factor` (`S.rescale_rate`), mide el pico de trazas en memoria con memoria ilimitada y vuelve a ejecutar con tu `num_traces`. "
         "Devuelve `S.coverage(...)` más `peak_traces`, `num_traces`, `dropped_too_early` y `kept`.",
         '''
def num_traces_for(traces_per_s, decision_wait_s, margin=1.5):
    # TODO: trazas en memoria ≈ tráfico × espera; añade margen y redondea hacia arriba
    raise NotImplementedError("TODO 4a")

def evaluate(policies, corpus, decision_wait_s=30.0, rate_factor=16):
    # TODO: rescaled = S.rescale_rate(corpus.traces, rate_factor); S.TailSampler(...).run(...) -> .peak_traces, .kept, .dropped_too_early
    raise NotImplementedError("TODO 4b")

try:
    ev = evaluate(build_policies(12.0), CORPUS)
    print({k: v for k, v in ev.items() if k != "kept"})
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["`traces_per_s` del corpus reescalado = `rate_factor × len(corpus) / corpus.duration_s`.", "`S.TailSampler(policies, decision_wait_s, num_traces=10**9).run(rescaled).peak_traces` da el pico sin límite; `num_traces_for(...)` ≥ pico."])

    todo(5, "No falsees las métricas (TODO)",
         "Escribe `corrected_error_rate(kept, baseline_pct)`: la tasa de error estimada sobre las trazas conservadas **con pesos de inclusión** (lo interesante pesa 1; el resto, 1/baseline). Usa `S.inclusion_weights` y `S.estimate_metrics(kept, pesos)`.",
         '''
def corrected_error_rate(kept, baseline_pct):
    # TODO
    raise NotImplementedError("TODO 5")

try:
    kept = S.TailSampler(build_policies(12.0), 30).run(CORPUS.traces).kept
    print("verdad:", round(S.estimate_metrics(CORPUS.traces)["error_rate"], 4), "· cruda:", round(S.estimate_metrics(kept)["error_rate"], 4), "· corregida:", round(corrected_error_rate(kept, 12.0), 4))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Una traza «interesante» (error, lenta o cara) se conserva siempre (π = 1); las demás con probabilidad `baseline_pct/100`.", "`keep_all = lambda t: t.error or t.slow or t.costly`; `w = S.inclusion_weights(kept, keep_all, baseline_pct/100)`."])

    todo(6, "La configuración del Collector (TODO)",
         "Escribe `collector_yaml(policies, num_traces)`: la configuración completa (con `span_metrics` **antes** del muestreo, `forward`, `tail_sampling` con `decision_wait: 30s`). Con Docker, la rúbrica la valida con `otelcol-contrib validate`.",
         '''
def collector_yaml(policies, num_traces):
    # TODO: S.collector_config(policies, decision_wait="30s", num_traces=num_traces)
    raise NotImplementedError("TODO 6")

try:
    Y = collector_yaml(build_policies(12.0), 9000)
    print(Y[:700])
    if DOCKER:
        print("otelcol validate →", S.validate_collector_config(Y)[0])
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["`supportops.sampling.collector_config` genera exactamente la estructura de la lección §6.", "`S.collector_config(policies, decision_wait=\"30s\", num_traces=num_traces)`."])

    todo(7, "Cardinalidad (TODO)",
         "Escribe `cardinality_check(dims, max_series)` → `(True, None)` si el producto de cardinalidades no supera `max_series`; si lo supera, `(False, etiqueta_con_mayor_cardinalidad)` (la que hay que quitar).",
         '''
def cardinality_check(dims, max_series):
    # TODO: S.series_estimate(dims) y max(dims, key=dims.get)
    raise NotImplementedError("TODO 7")

try:
    print(cardinality_check({"intent": 4, "tier": 3, "model": 10}, 1000), cardinality_check({"intent": 4, "tier": 3, "ticket_id": 2_000_000}, 100_000))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["El nº de series es el producto de las cardinalidades.", "`max(dims, key=dims.get)` devuelve la clave con el valor más alto."])

    todo(8, "Retención dentro del presupuesto (TODO)",
         "Escribe `retention_plan(traces_gb_day, budget_usd_month, hot_price=0.10, cold_price=0.023, hot_days=7)` → el **máximo de días** de retención (1-365) cuyo coste mensual en régimen estacionario no supera el presupuesto: `gb × (min(d, hot_days)·hot_price + max(0, d − hot_days)·cold_price)`.",
         '''
def retention_plan(traces_gb_day, budget_usd_month, hot_price=0.10, cold_price=0.023, hot_days=7):
    # TODO
    raise NotImplementedError("TODO 8")

try:
    print([retention_plan(g, b) for g, b in ((100, 300), (100, 1200), (20, 200), (500, 100))])
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Prueba cada d de 1 a 365 y quédate con el mayor que cumple (el coste crece con d).", "`best = max([d for d in range(1, 366) if coste(d) <= budget] or [0])`."])

    todo(9, "Límites por tenant (TODO; con Docker se comprueba en vivo)",
         "Escribe `tenant_limits()` → `(loki_limits, tempo_overrides)`: dicts con las claves de `limits_config` de Loki (máx. **20** streams activos, 8 etiquetas por serie, 1 MB/s de ingesta con ráfaga de 1 MB, 512 KB/s por stream) y de `overrides.defaults` de Tempo (**3 000** bytes por traza máx., 200 000 B/s de ingesta con ráfaga de 200 000).",
         '''
def tenant_limits():
    # TODO: claves de Loki: max_streams_per_user, max_label_names_per_series, ingestion_rate_mb, ingestion_burst_size_mb, per_stream_rate_limit
    #       claves de Tempo: {"global": {"max_bytes_per_trace": ...}, "ingestion": {"rate_limit_bytes": ..., "burst_size_bytes": ...}}
    raise NotImplementedError("TODO 9")

try:
    print(tenant_limits())
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Las claves están en la lección §9 y en `configs/loki-multitenant-limits.yaml` y `configs/tempo-multitenant-limits.yaml`.", "Loki: `{\"max_streams_per_user\": 20, \"max_label_names_per_series\": 8, \"ingestion_rate_mb\": 1, \"ingestion_burst_size_mb\": 1, \"per_stream_rate_limit\": \"512KB\"}`."])

    md("## Rúbrica · ejecútala cuando quieras")
    code(RUBRIC_18 + '''
try:
    run_rubric()
except NameError as e:
    print("Define las funciones de los pasos primero:", e)
''')

    md("""
    ## Retos extra (nivel experto)

    1. **Dos capas**: escribe la configuración de la capa 1 (`load_balancing` por `traceID` hacia 3 Collectors con `tail_sampling`) y valídala con `otelcol validate`.
    2. **`bytes_limiting` como red de seguridad**: añade la política y simula un incidente donde el 100 % de las trazas es error: ¿cuántos bytes/s dejas pasar y cuántos errores pierdes?
    3. **Muestreo por intención**: baja el baseline al 2 % para `kb_question` (la más barata de observar) y mantén el 20 % para `refund`; corrige las métricas con pesos por estrato.
    4. **Logs coherentes con las trazas**: calcula qué fracción de los logs quedaría con un `trace_id` colgante si descartas la traza pero conservas los logs, y diseña la política de logs.
    5. **Alerta de descartes**: escribe la regla de Grafana (módulo 16) sobre `otelcol_processor_tail_sampling_sampling_trace_dropped_too_early` > 0 durante 5 min.
    """)
    md("""
    ## Reflexión

    - ¿Qué pasaría con tu política en un **incidente** donde casi todas las trazas fueran error? ¿Quién protege tu presupuesto?
    - ¿Cómo repartirías el 15 % entre equipos con tráficos 100× distintos? (tenants, cuotas, `rate_limiting`).
    - ¿Qué dato necesitarías **medir** en tu sistema real antes de fiarte de las cifras de coste del notebook?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable: redefine las funciones y vuelve a lanzar la rúbrica.
    """)
    code('# ===================== SOLUCIÓN DE REFERENCIA =====================' + SOLUTION_18 + '''
VR = volume_report(CORPUS, TICKETS_DAY)
b = baseline_for_budget(CORPUS, BUDGET_BYTES_PCT)
print({k: round(v, 4) for k, v in VR.items()}, "· baseline:", b)
ev = evaluate(build_policies(b), CORPUS)
print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in ev.items() if k != "kept"})
kept = ev["kept"]
print("tasa de error: verdad", round(S.estimate_metrics(CORPUS.traces)["error_rate"], 4), "· cruda", round(S.estimate_metrics(kept)["error_rate"], 4), "· corregida", round(corrected_error_rate(kept, b), 4))
cm = S.StackCostModel.from_corpus(CORPUS, TICKETS_DAY, spans_per_trace=40, bytes_per_span=2500, trace_keep=ev["kept_bytes_pct"] / 100)
print("días de retención de trazas dentro de", BUDGET_USD_MONTH, "USD/mes (escenario supuesto de 40 spans):", retention_plan(cm.daily_gb()["traces_stored"], BUDGET_USD_MONTH))
R = run_rubric()
''')
    nb.save(out)


README_18 = """# Módulo 18 · Escala, muestreo y coste del propio stack

**Nivel:** 🔴 Experto · **Duración:** ≈ 5 h (lección) + ≈ 2 h 30 (proyecto) · **Servicios:** ninguno del stack del curso; con Docker, contenedores efímeros (Collector contrib 0.162, Loki, Tempo, Prometheus) en puertos aleatorios.

Cómo observar un agente sin arruinar la factura de observar: **head vs tail sampling**, políticas por errores/latencia/coste con el procesador `tail_sampling` del Collector contrib 0.162 (verificado con el binario real), por qué el muestreo **sesga las métricas** y cómo corregirlo,
**cardinalidad** y tormentas (medidas con Prometheus real), **multi-tenant y límites** en Tempo y Loki, **retención y niveles**, y el **coste del propio stack** con presupuesto.

## Contenido

| Archivo | Qué es |
|---|---|
| `18_escala_muestreo_coste.ipynb` | Lección (17 secciones, 13 gráficos, experimentos con contenedores reales, 🧠 de élite, autoevaluación con cálculo/diagnóstico/transferencia) |
| `18_proyecto_escala_muestreo_coste.ipynb` | Proyecto: política con presupuesto (bytes, recall, memoria, métricas sin sesgo, cardinalidad, retención, límites por tenant); rúbrica R1-R9, pistas 🪜 y solución tras ⛔ SPOILER |
| `configs/` | `collector-tail-sampling.yaml`, `loki-multitenant-limits.yaml`, `tempo-multitenant-limits.yaml`, `loki-retention.yaml`, `tempo-retention.yaml`, `prometheus-scrape-limits.yaml` (todos validados con las herramientas oficiales) |
| `recorded/capture_seed42.json.gz` | Captura pregrabada de los experimentos con Docker (modo sin Docker) |
| `../supportops/sampling.py` | Corpus de trazas, head/tail sampling (simulador con las claves del Collector), sesgo y pesos, cardinalidad, modelo de coste/retención, generadores de configuración, laboratorios Docker (`SamplingLab`, `BackendLab`, `storm_experiment`) |
| `../supportops/tests/test_sampling.py` | Pruebas del módulo (las de Docker se saltan si no hay daemon) |
| `../stack/grafana/dashboards/18-escala-coste.json` | Dashboard «18 · Escala y coste del propio stack» (uid `escala-coste`) |

## Servicios necesarios

- **Sin Docker**: todo el muestreo, el sesgo, la cardinalidad analítica y los modelos de coste; lo medido con contenedores va pregrabado. Funciona en Colab.
- **Con Docker**: los experimentos de §6, §8 y §9 descargan/usan `otel/opentelemetry-collector-contrib:0.162.0`, `grafana/loki:3.7.8`, `grafana/tempo:3.1.0` y `prom/prometheus:v3.15.0` (las mismas del stack).

## Hallazgos verificados con los binarios reales (oct-2026)

- `tail_sampling` (contrib 0.162.0): `numeric_attribute` usa `int64`; con un atributo *double* y solo `min_value` el Collector **cae con SIGSEGV** (`EvaluateWithThreshold`). Usa `ottl_condition` para decimales.
- Con `num_traces` insuficiente el Collector descarta trazas **sin decidir** y sin error (solo la métrica `sampling_trace_dropped_too_early`).
- Loki: `retention_enabled` exige `compactor.delete_request_store`; límites devuelven 429/400 con mensajes accionables; sin cabecera de tenant, 401. Tempo descarta en silencio por `trace_too_large` (`tempo_discarded_spans_total`).
- Prometheus v3.15 (OTLP): ≈ 1-3 KB de RSS por serie en una tormenta de `ticket_id` (30 000 series → +84 MB); un *View* del SDK las reduce a 5.

## Lecturas

README del procesador `tailsamplingprocessor` (v0.162.0) · especificación de muestreo por umbral consistente de OpenTelemetry · Dapper (Google, 2010) · Honeycomb Refinery · documentación de Loki, Tempo y Prometheus (límites, retención).
"""


def build_readme() -> None:
    (COURSE / MOD / "README.md").write_text(README_18, encoding="utf-8")
    print("OK README 18")


if __name__ == "__main__":
    if "--record" in sys.argv:
        record()
    else:
        build_dashboard()
        build_configs()
        build_readme()
        build_lesson()
        build_project()
