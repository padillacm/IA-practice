"""Genera el módulo 22_capstone: README, lección (guía + plataforma de referencia), proyecto (entrega final), plataforma (Collector, checklist, plantilla de revisión) y dashboard 22.
Ejecutar desde la raíz del repo:  python agent-observability-course/_tools/builders/build_22.py
"""
from __future__ import annotations

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "22_capstone"
DASH_UID = "plataforma-agentes"


# =====================================================================================================================
# Plataforma de referencia: Collector gateway, checklist y plantilla de revisión
# =====================================================================================================================
def gateway_config() -> dict:
    sys.path.insert(0, str(COURSE))
    from supportops import privacy as P
    from supportops import sampling as S
    policies = [S.StatusCode(("ERROR",), name="errors"), S.Latency(8000, name="slow"), S.AttrCompare(key="supportops.tree.cost_usd", op=">", value=0.004, name="costly"), S.Probabilistic(10, name="baseline")]
    return {
        "extensions": {"health_check": {"endpoint": "0.0.0.0:13133"}},
        "receivers": {"otlp": {"protocols": {"grpc": {"endpoint": "0.0.0.0:4317"}, "http": {"endpoint": "0.0.0.0:4318"}}}},
        "processors": {
            "memory_limiter": {"check_interval": "1s", "limit_mib": 400, "spike_limit_mib": 100},
            "resource/lab": {"attributes": [{"key": "deployment.environment.name", "value": "lab", "action": "upsert"}]},
            "redaction": {"allow_all_keys": True, "blocked_values": P.go_blocked_values(), "summary": "info"},
            "tail_sampling": {"decision_wait": "10s", "num_traces": 50000, "expected_new_traces_per_sec": 100, "policies": S.tail_policy_config(policies)},
            "batch": {"timeout": "1s", "send_batch_size": 512},
        },
        "connectors": {"forward": {}, "span_metrics": {"histogram": {"explicit": {"buckets": ["100ms", "500ms", "1s", "2s", "5s", "10s"]}}, "dimensions": [{"name": "supportops.status"}], "metrics_flush_interval": "10s"}},
        "exporters": {"otlp_grpc/tempo": {"endpoint": "tempo:4317", "tls": {"insecure": True}}, "otlp_http/loki": {"endpoint": "http://loki:3100/otlp"},
                      "otlp_http/prometheus": {"endpoint": "http://prometheus:9090/api/v1/otlp"}},
        "service": {"extensions": ["health_check"],
                    "pipelines": {
                        "traces/in": {"receivers": ["otlp"], "processors": ["memory_limiter", "redaction", "resource/lab"], "exporters": ["forward", "span_metrics"]},
                        "traces/sampled": {"receivers": ["forward"], "processors": ["tail_sampling", "batch"], "exporters": ["otlp_grpc/tempo"]},
                        "metrics": {"receivers": ["otlp", "span_metrics"], "processors": ["memory_limiter", "resource/lab", "batch"], "exporters": ["otlp_http/prometheus"]},
                        "logs": {"receivers": ["otlp"], "processors": ["memory_limiter", "redaction", "resource/lab", "batch"], "exporters": ["otlp_http/loki"]}},
                    "telemetry": {"metrics": {"level": "normal", "readers": [{"pull": {"exporter": {"prometheus": {"host": "0.0.0.0", "port": 8888}}}}]}}}}


CHECKLIST = [
    # (id, área, texto, módulo, automática)
    ("I1", "Instrumentación", "Una traza por petición de extremo a extremo (n_trazas == n_tickets en una prueba canario)", "11 · 21", True),
    ("I2", "Instrumentación", "Convenciones GenAI validadas con el linter/instantánea de la spec; versión de la spec fijada", "04", False),
    ("I3", "Instrumentación", "Tokens y coste contados solo en las hojas `chat` (sin doble conteo)", "04 · 11 · 13", True),
    ("I4", "Instrumentación", "`gen_ai.agent.version` y versión de prompt en todos los spans", "15", False),
    ("I5", "Instrumentación", "`ParentBased` en todos los servicios (muestreo coherente)", "11", False),
    ("I6", "Instrumentación", "Logs con `trace_id`/`span_id` al 100 %", "08", True),
    ("I7", "Instrumentación", "Reintentos del SDK desactivados o contados (`max_retries=0` + span por intento)", "06", False),
    ("C1", "Collector", "`memory_limiter` primero; `batch` último; redacción antes de cualquier exportador", "05 · 20", True),
    ("C2", "Collector", "Configuración validada con `otelcol validate` en CI y con el binario real", "05 · 19", True),
    ("C3", "Collector", "Métricas RED calculadas **antes** del muestreo (`span_metrics` en `traces/in`)", "18", True),
    ("C4", "Collector", "Tail sampling con `num_traces` ≥ tráfico × `decision_wait` y vigilancia de `dropped_too_early`", "18", False),
    ("C5", "Collector", "Gateway con afinidad por `traceID` si hay más de una réplica", "19", False),
    ("S1", "SLOs y alertas", "SLIs de disponibilidad, latencia, calidad y coste con objetivos medidos sobre la línea base", "16", True),
    ("S2", "SLOs y alertas", "Alertas por burn rate multiventana, provisionadas como código (intervalo múltiplo de 10 s)", "16", True),
    ("S3", "SLOs y alertas", "Runbook por alerta de página y plantilla de postmortem sin culpa", "16", False),
    ("S4", "SLOs y alertas", "Política de presupuesto de error pactada con producto antes del incidente", "16", False),
    ("Q1", "Calidad", "Evaluación online con muestreo estratificado y corrección por sensibilidad/especificidad del juez", "14", False),
    ("Q2", "Calidad", "Compuerta de regresión apareada y canario con SPRT", "15", False),
    ("Q3", "Calidad", "Estimación de calidad (muestra uniforme) con intervalo y objetivo", "14 · 16", True),
    ("K1", "Coste", "Coste por ticket resuelto con tokens como fuente de verdad y precios versionados", "13", True),
    ("K2", "Coste", "Presupuestos, `BudgetGuard` y `LoopGuard` fuera del instrumentor de coste", "13", False),
    ("K3", "Coste", "Coste del propio stack estimado y retención por clase de dato", "18 · 20", True),
    ("P1", "Privacidad y seguridad", "Captura de contenido apagada por defecto; redacción en la app y en el Collector", "20", True),
    ("P2", "Privacidad y seguridad", "Cero PII en spans y logs tras el Collector (excluyendo nombres), medido", "20", True),
    ("P3", "Privacidad y seguridad", "Detección de inyección (contenido + comportamiento) con alerta y revisión", "20", False),
    ("P4", "Privacidad y seguridad", "Auditoría de accesos a contenido con cadena de hashes; retención por clase", "20", False),
    ("D1", "Despliegue", "Charts y versiones de imagen fijados (sin `latest`); valores como código", "19", True),
    ("D2", "Despliegue", "Dashboards, datasources y alertas aprovisionados desde ficheros (`allowUiUpdates: false`)", "10 · 16", False),
    ("D3", "Despliegue", "Límites por tenant en Loki/Tempo (radio de explosión) y presupuesto de ingesta", "18", False),
    ("R1", "Operación", "Mesa de incidentes superada (los cinco casos en < 15 min con solo telemetría)", "21", False),
    ("R2", "Operación", "Contratos de telemetría en CI y simulacros (game days) trimestrales", "21", False),
]

ADR_TEMPLATE = """# Revisión de arquitectura · plataforma de observabilidad de <sistema>

**Estado:** borrador · **Autores:** <equipo> · **Fecha:** <fecha> · **Revisores:** <nombres/roles>

## 1. Contexto y objetivos
Qué sistema se observa (agentes, tráfico, equipos, usuarios de Grafana), qué decisiones debe permitir tomar la telemetría y qué **no** es objetivo.

## 2. Requisitos y restricciones
| Requisito | Medida | Objetivo |
|---|---|---|
| Disponibilidad del agente | ratio de tickets `ok|escalated` | ≥ 99 % |
| Latencia | p95 de `invoke_workflow` | ≤ 8 s |
| Calidad | groundedness (muestra uniforme) | ≥ 95 % |
| Coste | USD por ticket resuelto | ≤ ... |
| Privacidad | PII en backends | 0 (sin nombres) |
| Retención | por clase de dato | ... |

## 3. Arquitectura propuesta
Diagrama y descripción por capas: instrumentación → Collector (redacción, span metrics, tail sampling) → Tempo/Loki/Prometheus → Grafana/alertas. Despliegue (K8s/Helm) y límites.

## 4. Decisiones clave (ADR) y alternativas descartadas
| Decisión | Alternativas | Por qué | Coste/riesgo |
|---|---|---|---|
| Tail sampling en un gateway | head sampling; todo | ... | memoria ≈ tráfico × decision_wait |

## 5. Riesgos y modos de fallo
Para cada riesgo: probabilidad, impacto, **detección** (qué señal), **mitigación** y dueño. Incluye: pérdida silenciosa de telemetría, cardinalidad, trazas partidas, fuga de PII, regresión silenciosa.

## 6. Coste
Estimación mensual (volumen, retención, precio) con supuestos explícitos y sensibilidad (×2 tráfico, ×2 retención).

## 7. Plan de despliegue y de pruebas
Orden de rollout, pruebas canario, contratos de telemetría, mesa de incidentes y criterios de salida.

## 8. Preguntas abiertas
Lo que no se sabe y cómo se averiguará (con fecha).
"""


def build_platform() -> None:
    d = COURSE / MOD / "platform"
    d.mkdir(parents=True, exist_ok=True)
    cfg = gateway_config()
    header = ("# Gateway de la plataforma de SupportOps (capstone, módulo 22). Integra: memory_limiter (05), redaction (20), span_metrics ANTES del muestreo (18), tail_sampling (18) y exportadores a Tempo/Loki/Prometheus (OTLP).\n"
              "# Generado por _tools/builders/build_22.py; validado con `otelcol-contrib validate` (0.162.0). Pensado para correr en la red de Compose del stack (`agentobs_default`): resuelve tempo, loki y prometheus por nombre.\n"
              "# Prometheus recibe métricas por su receptor OTLP (http://prometheus:9090/api/v1/otlp). `num_traces` ≥ tráfico × decision_wait (módulo 18).\n")
    (d / "collector-gateway.yaml").write_text(header + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    items = [{"id": i, "area": a, "item": t, "modulo": m, "automatica": auto} for i, a, t, m, auto in CHECKLIST]
    (d / "production-checklist.yaml").write_text("# Checklist de producción de la plataforma de observabilidad de agentes (módulo 22). `automatica: true` = lo comprueba el scorecard de la lección con telemetría.\n"
                                                 + yaml.safe_dump({"version": 1, "items": items}, sort_keys=False, allow_unicode=True, width=200), encoding="utf-8")
    (d / "architecture-review-template.md").write_text(ADR_TEMPLATE, encoding="utf-8")
    print("OK platform", [p.name for p in d.iterdir()])


# =====================================================================================================================
# Dashboard 22
# =====================================================================================================================
def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, alertlist, lint, logs, prom, stat, text, thresholds, timeseries, traces_table
    d = Dashboard(DASH_UID, "22 · Plataforma de agentes de SupportOps", tags=["curso", "capstone", "plataforma"], time_from="now-30m",
                  description="Visión integral de la plataforma: SLOs, calidad, coste, privacidad y salud del propio pipeline de observabilidad.")
    d.add(text("Cómo leer la plataforma", "Una fila por **pregunta de negocio**: ¿funciona? (SLOs) · ¿es correcto? (calidad) · ¿cuánto cuesta? (coste) · ¿es seguro? (privacidad) · ¿**ve** bien el sistema que nos vigila? (pipeline). "
               "Cada panel enlaza con el módulo donde se construyó. Si el pipeline está enfermo, **no te fíes del resto**: la ausencia de datos no es salud.", h=3))
    d.row("SLOs (módulo 16)")
    d.add(stat("Disponibilidad (30 min)", 'sum(rate(supportops_agent_requests_total{service_name="supportops-agent",supportops_status=~"ok|escalated"}[30m])) / sum(rate(supportops_agent_requests_total{service_name="supportops-agent"}[30m]))',
               unit="percentunit", w=6, h=4, decimals=3, thr=thresholds((None, "red"), (0.99, "green")), description="SLI de disponibilidad frente al objetivo del 99 %."),
          stat("p95 de invoke_agent (5 min)", 'histogram_quantile(0.95, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket{service_name="supportops-agent"}[5m])))', unit="s", w=6, h=4,
               thr=thresholds((None, "green"), (5, "orange"), (10, "red")), description="Latencia de extremo a extremo del agente."),
          stat("Coste por ticket (5 min)", 'sum(rate(supportops_agent_request_cost_USD_sum{service_name="supportops-agent"}[5m])) / sum(rate(supportops_agent_request_cost_USD_count{service_name="supportops-agent"}[5m]))', unit="currencyUSD", w=6, h=4, decimals=5,
               description="Coste medio por ticket (precios ilustrativos, módulo 13)."),
          stat("Groundedness evaluada (15 min)", 'sum(increase(supportops_eval_results_total{gen_ai_evaluation_name="groundedness",gen_ai_evaluation_score_label="pass"}[15m])) / sum(increase(supportops_eval_results_total{gen_ai_evaluation_name="groundedness"}[15m]))',
               unit="percentunit", w=6, h=4, decimals=3, thr=thresholds((None, "red"), (0.95, "green")), description="Fracción de respuestas fundamentadas según el juez online (módulo 14); objetivo 95 %."))
    d.row("Seguridad y privacidad (módulo 20)")
    d.add(stat("Peticiones sospechosas (15 min)", 'sum(increase(supportops_security_injection_suspected_total[15m]))', unit="short", w=6, h=4, thr=thresholds((None, "green"), (1, "orange"), (5, "red")), description="Señales de prompt injection."),
          stat("PII en la salida (15 min)", 'sum(increase(supportops_privacy_pii_findings_total{direction="output"}[15m]))', unit="short", w=6, h=4, thr=thresholds((None, "green"), (1, "red")), description="PII detectada en respuestas del modelo: objetivo 0."),
          stat("Series activas de Prometheus", 'prometheus_tsdb_head_series', unit="short", w=6, h=4, description="Control de cardinalidad (módulos 18 y 21)."),
          alertlist("Alertas activas", w=6, h=4, description="Reglas de Grafana en firing/pending."))
    d.row("Salud del pipeline de observabilidad (módulos 05, 18, 19)")
    d.add(timeseries("Spans aceptados y enviados por el Collector", [prom('sum by (receiver) (rate(otelcol_receiver_accepted_spans[1m]))', "aceptados · {{receiver}}"),
                                                                       prom('sum by (exporter) (rate(otelcol_exporter_sent_spans[1m]))', "enviados · {{exporter}}", ref="B")], w=12, h=8, unit="ops",
                     description="Si aceptados ≫ enviados hay muestreo o pérdida; si ambos caen a 0 con tráfico, el pipeline está roto."),
          timeseries("Trazas descartadas antes de decidir (tail sampling)", [prom('sum(rate(otelcol_processor_tail_sampling_sampling_trace_dropped_too_early[$__rate_interval]))', "dropped_too_early")], w=12, h=8, unit="ops",
                     description="Debe ser 0: si no, `num_traces` es insuficiente y se pierden trazas sin evaluarlas (módulo 18)."))
    d.add(traces_table("Trazas con error (Tempo)", '{ status = error }', w=12, h=8, description="Trazas con algún span en error: punto de partida de un diagnóstico."),
          logs("Avisos y errores (Loki)", '{service_name=~"supportops.*"} | detected_level=~"warn|error"', w=12, h=8, description="Logs de aviso/error de todos los servicios de SupportOps."))
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "22-plataforma-agentes.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
# Piezas comunes de los notebooks
# =====================================================================================================================
IMPORTS_22 = """
import collections, dataclasses, hashlib, json, math, re, statistics, subprocess, tempfile, time, uuid, pathlib
import yaml
from IPython.display import Markdown
from supportops import incidents as I, privacy as P, sampling as S
from supportops.multiagent import build_mesh, MultiAgentSupportOps, DelegationPolicy, cost_rollup, waterfall_services
from supportops.traffic import Incident
from supportops.pricing import cost_usd
from supportops.quality_eval import wilson_interval
STACK = check_stack("core+metrics")
LIVE = not STACK.degraded
DOCKER = P.docker_available()
PLATFORM = pathlib.Path(ROOT) / "22_capstone" / "platform"
"""

RUN_PLATFORM = '''
def run_platform(n: int = 480, seed: int = SEED, redact: bool = True, content: bool = True, mode: str = "memory", endpoint: str | None = None):
    """La plataforma completa de SupportOps: multi-agente (orquestador + 4 especialistas) con telemetría OTel por servicio, captura de contenido configurable,
    redacción en la app, políticas de resiliencia y una caída parcial (la herramienta `get_order` del billing-agent agota plazos entre los minutos 10 y 20 de una ejecución de 30 min). Devuelve (mesh, tickets, resultados)."""
    mesh = build_mesh(mode=mode, endpoint=endpoint)
    red = P.Redactor("hash", names=True) if redact else None
    for a in mesh.handles:
        mesh.instr(a, capture_content=content, redact=red)
    system = MultiAgentSupportOps(mesh, mode="delegate", policy=DelegationPolicy(timeout_s=6, max_retries=2, backoff_s=0.5))
    inc = Incident("billing-timeouts", "tool_timeout", 10 * 60, 20 * 60, 1.0, {"tool": "get_order", "timeout_s": 8.0, "agent": "billing-agent", "sticky": True})
    tickets = generate_tickets(n, seed, duration_s=1800, fault_rates=DEFAULT_FAULT_RATES, incidents=[inc], pii_rate=0.3)
    results = [system.run(t) for t in tickets]
    mesh.force_flush()
    return mesh, tickets, results
'''

SCORECARD = '''
def pii_after(mesh):
    txt = [json.dumps(s["attributes"], ensure_ascii=False) for s in mesh.span_records()] + [str(l["body"]) + json.dumps(l["attributes"], ensure_ascii=False) for l in mesh.log_records()]
    return P.pii_exposure(txt)

def scorecard(mesh, tickets, results, corpus_cov=None, cfg_ok=None, quality=None):
    """Comprobaciones automáticas de la plataforma con SU PROPIA telemetría. Devuelve una lista de filas (id del checklist, área, medida, umbral, ok)."""
    sp, lg = mesh.span_records(), mesh.log_records()
    rows = []
    def add(cid, area, what, value, thr, ok): rows.append({"id": cid, "área": area, "comprobación": what, "valor": value, "umbral": thr, "ok": bool(ok)})
    tt = I.trace_table(sp, tickets[0].created_at - 1)
    add("I1", "Instrumentación", "trazas por ticket", round(len(tt) / len(tickets), 3), "= 1", len(tt) == len(tickets))
    leaf = collections.defaultdict(int)
    for s in sp:
        if s["name"].startswith("chat"): leaf[s["trace_id"]] += int(s["attributes"].get("gen_ai.usage.input_tokens", 0) or 0)
    tree = sum(r.input_tokens for r in results)
    add("I3", "Instrumentación", "tokens de entrada: hojas chat / árbol del orquestador", round(sum(leaf.values()) / tree, 3), "= 1", sum(leaf.values()) == tree)
    cov = np.mean([bool(l["trace_id"]) for l in lg]); add("I6", "Instrumentación", "logs con trace_id", round(float(cov), 3), "= 1", cov == 1.0)
    good = np.mean([r.status in ("ok", "escalated") for r in results]); add("S1", "SLOs", "disponibilidad (objetivo 99 %: se mide, no se exige cumplirlo en el incidente)", round(float(good), 4), "medida", True)
    p95 = float(np.percentile([r.latency_s for r in results], 95)); add("S1", "SLOs", "p95 de la petición (s)", round(p95, 2), "medida", True)
    c = [r.cost_usd for r in results]; add("K1", "Coste", "coste por ticket (USD, ilustrativo) y p95/media", f"{np.mean(c):.5f} · {np.percentile(c, 95) / np.mean(c):.2f}×", "medida", True)
    ex = pii_after(mesh); no_names = sum(v for k, v in ex.items() if k != "name")
    add("P2", "Privacidad", "PII residual en spans+logs (sin nombres)", no_names, "= 0", no_names == 0)
    if quality is not None: add("Q3", "Calidad", "groundedness (muestra uniforme 25 %): límite inferior del IC 95 %", round(quality["lo"], 3), "≥ 0,85", quality["lo"] >= 0.85)
    if corpus_cov is not None:
        add("C3", "Collector", "recall de errores tras el tail sampling (%)", round(corpus_cov["recall_error_pct"], 1), "= 100", corpus_cov["recall_error_pct"] >= 99.9)
    if cfg_ok is not None: add("C2", "Collector", "configuración del gateway válida (otelcol validate)", cfg_ok, "OK", cfg_ok is True)
    return pd.DataFrame(rows)
'''


# =====================================================================================================================
# LECCIÓN
# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "22_capstone.ipynb", "Módulo 22 · Capstone: plataforma de observabilidad completa para SupportOps")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 22 · Capstone: la plataforma completa de observabilidad de SupportOps

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 4 h 30 min (guía y plataforma de referencia ≈ 2 h 30 min + entrega final ≈ 2 h) |
    | **Servicios de Compose** | Opcional: `--profile core --profile metrics` (sección 11, ≈ 4 min: el Collector del capstone se conecta al stack). Docker para validar el Collector y el *Collector real* efímero. Sin Docker, modo degradado |
    | **RAM aproximada** | < 700 MB sin stack · ≈ 1,3 GB con `core` + `metrics` + el gateway efímero |
    | **Prerrequisitos** | Todo el curso (00-21). **No hay conceptos nuevos**: es integración |
    | **Hilo conductor** | El agente de SupportOps empezó siendo un bucle de 80 líneas. Hoy es un **sistema multi-agente observado, con SLOs, calidad, costes, privacidad, muestreo y despliegue**, con un *scorecard* que lo prueba y una revisión de arquitectura que lo defiende |

    > ⚠️ **Honestidad sobre el laboratorio.** Todo es simulado y determinista (`mock`, semilla 42): el tráfico (≈ 4 tickets/min), el incidente del proveedor y el análisis de muestreo y coste (corpus del módulo 18, de **agente único**; el multi-agente aporta los contratos, el SLO y la privacidad).
    > Los precios son ilustrativos. Kubernetes (módulo 19) no ejecutó pods en este entorno: lo que se verifica del despliegue son los valores y las configuraciones, no un clúster en marcha. Un capstone «de verdad» te pide además probar la plataforma bajo **tu** carga y **tus** datos.
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar este módulo podrás:

    1. **Diseñar** la arquitectura de una plataforma de observabilidad para un sistema multi-agente a partir de **requisitos** (SLOs, privacidad, coste) y justificar cada decisión (ADR).
    2. **Verificar** la instrumentación con **contratos de telemetría** automáticos (una traza por ticket, tokens solo en hojas, logs correlacionados, cero PII).
    3. **Configurar** un gateway del Collector que integre redacción, métricas RED previas al muestreo, tail sampling y exportación, y **validarlo** con el binario real.
    4. **Medir** el efecto del muestreo (cobertura y sesgo) y estimar el coste mensual del propio stack con supuestos explícitos.
    5. **Calcular** SLIs y burn rate de una ejecución con incidente y **estimar** la calidad con intervalo de confianza.
    6. **Evaluar** la plataforma con un *scorecard* automático y un checklist de producción de 31 puntos (los automáticos, medidos; los manuales, declarados con evidencia).
    7. **Defender** una revisión de arquitectura: riesgos, modos de fallo, detección, mitigación, coste y plan de pruebas (incluida la mesa de incidentes).
    """)

    md("## 🔁 Conexión con módulos anteriores")
    md(details("1 · (Módulo 18) ¿Por qué las métricas RED se calculan antes del tail sampling?",
               "Porque el tail sampling conserva sobre todo errores y lentas: cualquier métrica derivada de lo que sobrevive está sesgada (2,6 % → ≈ 12 % de errores en el módulo 18). `span_metrics` en `traces/in` + `forward` calcula sobre el 100 %."))
    md(details("2 · (Módulo 20) ¿Qué dos capas de redacción usa SupportOps y por qué no basta una?",
               "Redacción en la aplicación (HMAC) y en el Collector (`redaction`). Ninguna sola basta: el Collector no ve lo que no pasa por él ni puede detectar nombres; la aplicación puede olvidar un logger. Defensa en profundidad."))
    md(details("3 · (Módulo 16) ¿Qué alertas y por qué ventanas múltiples?",
               "Burn rate multiventana: ventana larga (¿es grave?) y corta (¿sigue ocurriendo?). 14,4× en 1 h/5 min para páginas y 1× en 3 d/6 h para tickets; en el laboratorio, ventanas comprimidas."))
    md(details("4 · (Módulo 11) ¿Cómo se cuenta el coste en un árbol de agentes?",
               "Solo en las hojas `chat`: los `invoke_agent` repiten el total de sus hijos; sumar todos los spans multiplica el coste."))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_22)
    code(RUN_PLATFORM)
    code(SCORECARD)

    # ------------------------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · De requisitos a arquitectura

    Una plataforma se justifica por las **preguntas que debe responder** y los **riesgos que debe cubrir**, no por las herramientas. Esta tabla (la de la revisión de arquitectura) conecta cada requisito con el módulo donde se construyó y la decisión tomada:

    | Requisito de negocio | Medida (SLI) | Decisión de plataforma | Módulos |
    |---|---|---|---|
    | El agente responde | ratio de tickets `ok` o `escalated` ≥ 99 % | SLO + burn rate multiventana provisionado como código | 09, 10, 16 |
    | Responde rápido | p95 de `invoke_workflow` ≤ 8 s | histogramas con buckets en el SLO; plazos propagados y disyuntor entre agentes | 09, 11 |
    | Responde bien | groundedness ≥ 95 % (muestra uniforme) | evaluación online + compuerta de regresión + canario | 14, 15 |
    | Cuesta lo previsto | USD por ticket resuelto; sin bucles | tokens como verdad, `BudgetGuard`/`LoopGuard`, coste solo en hojas | 11, 13 |
    | No filtra datos | 0 PII en backends; inyección detectada | captura apagada, redacción en app y Collector, detector + comportamiento, auditoría | 20 |
    | Es depurable | traza por ticket; versión en spans; runbooks | contratos de telemetría, mesa de incidentes | 03, 15, 21 |
    | Escala sin arruinarnos | coste del stack ≤ presupuesto | tail sampling por valor, métricas antes, retención por clase | 18 |
    | Se despliega con confianza | configuración validada, versiones fijadas | Helm + valores como código + `otelcol validate` en CI | 05, 19 |
    """)
    code('''
fig, ax = viz.canvas(13.5, 6.6, (0, 135), (0, 66))
P_ = viz.PALETTE
ax.text(1, 63, "Arquitectura de la plataforma de SupportOps", fontsize=12, fontweight="bold")
cli = viz.box(ax, 1, 28, 12, 9, "Clientes\\n(tickets)", P_["neutral"], fc="#f3f4f6", fontsize=8)
orch = viz.box(ax, 18, 28, 15, 9, "Orquestador\\nsupportops-\\norchestrator", P_["traces"], fontsize=8, bold=True)
subs = [viz.box(ax, 40, 53.5 - i * 9.5, 15, 7.5, t, P_["traces"], fontsize=7.5) for i, t in enumerate(["orders-agent", "billing-agent", "knowledge-agent", "escalation-agent"])]
tools = viz.box(ax, 61, 26, 15, 18, "Herramientas /\\nKB / MCP\\n(idempotentes)", P_["profiles"], fontsize=8)
llm = viz.box(ax, 61, 49, 15, 8, "Proveedor LLM", P_["warn"], fontsize=8)
viz.arrow(ax, viz.right(cli), viz.left(orch)); [viz.arrow(ax, viz.right(orch), viz.left(b), "", P_["traces"]) for b in subs]
for b in subs[1:]: viz.arrow(ax, viz.right(b), (60.7, b[1] + 3.5), "", P_["profiles"])
viz.arrow(ax, (55.3, 57), (60.7, 52.5), "", P_["warn"])
col = viz.box(ax, 84, 24, 20, 20, "Collector gateway\\n① memory_limiter\\n② redaction\\n③ span_metrics (RED)\\n④ tail_sampling\\n⑤ batch → export", P_["metrics"], fontsize=7.8, bold=True)
viz.arrow(ax, (76.3, 33), (83.7, 33), "OTLP", P_["metrics"])
be = [viz.box(ax, 112, 46, 21, 8, "Tempo · trazas", P_["traces"], fontsize=8), viz.box(ax, 112, 33, 21, 8, "Loki · logs (trace_id)", P_["logs"], fontsize=8), viz.box(ax, 112, 20, 21, 8, "Prometheus · RED/GenAI", P_["metrics"], fontsize=8)]
[viz.arrow(ax, viz.right(col), viz.left(b), "", P_["metrics"]) for b in be]
graf = viz.box(ax, 112, 4, 21, 9, "Grafana · SLOs · alertas\\nrunbooks · dashboards 00-22", P_["ok"], fontsize=7.8, bold=True)
[viz.arrow(ax, viz.bottom(b) if i == 2 else (b[0] + b[2] / 2, b[1] - 0.4), (b[0] + b[2] / 2, 13.6) if i == 2 else (b[0] + b[2] / 2, b[1] - 3.2), "", P_["ok"]) for i, b in enumerate(be)]
ev = viz.box(ax, 84, 4, 20, 9, "Evaluador online\\n(juez) + canario", P_["profiles"], fontsize=7.8); viz.arrow(ax, viz.top(ev), viz.bottom(col), "eventos", P_["profiles"])
sec = viz.box(ax, 2, 3, 74, 7, "Seguridad: captura apagada · HMAC en app · detector de inyección + comportamiento · auditoría", P_["error"], fc="#fdecec", fontsize=7.5)
ops = viz.box(ax, 2, 13, 74, 7, "Despliegue: Helm + valores como código · versiones fijadas · otelcol validate en CI", P_["neutral"], fc="#f3f4f6", fontsize=7.5)
plt.show()
''')
    md(observe("""
    - El Collector es el **punto de control único**: redacción (privacidad), métricas RED (SLO) y muestreo (coste) pasan por él **en ese orden**, y por eso el orden de los procesadores es una decisión de arquitectura, no de estilo.
    - Los agentes solo conocen un endpoint OTLP. Eso permite cambiar muestreo, redacción o destinos **sin redesplegar agentes** (módulo 00).
    - Las franjas inferiores (seguridad, despliegue) **atraviesan** todas las capas: son requisitos transversales, no componentes.
    """))

    # ------------------------------------------------------------------------------------------------------------- 2
    md("""
    ---
    # 2 · Instrumentación y contratos de telemetría

    Ejecutamos la plataforma (multi-agente, contenido capturado pero **redactado en la app**, una caída parcial entre los minutos 10 y 20 de una ejecución de 30 min) y la sometemos a **contratos**: afirmaciones sobre la telemetría que, si dejan de cumplirse, te avisan **antes** que un usuario.
    """)
    code('''
N = 480 if FAST_DEV_RUN else 960
MESH, TICKETS, RES = run_platform(N)
SP, LG = MESH.span_records(), MESH.log_records()
print(f"{len(TICKETS)} tickets · {len(SP)} spans · {len(LG)} logs · servicios: {sorted({s['resource']['service.name'] for s in SP})}")
print("estados:", dict(collections.Counter(r.status for r in RES)), "· reintentos:", sum(r.retries for r in RES), "· timeouts:", sum(r.timeouts for r in RES))
sc = scorecard(MESH, TICKETS, RES)
display(sc.set_index("id"))
''')
    code('''
ok_traces = [r for r in RES if r.n_tool_calls >= 1 and r.agents_called][:1]
tid = ok_traces[0].trace_id
fig, ax = plt.subplots(figsize=(12, 5)); waterfall_services([s for s in SP if s["trace_id"] == tid], ax=ax, title=f"Un ticket de extremo a extremo ({tid[:8]}…): orquestador y especialistas en una sola traza", hide_chat=True)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La tabla es el **contrato** ejecutado: una traza por ticket (`1,0`), tokens de entrada de las hojas = tokens del árbol (`1,0`: nada duplicado), logs con `trace_id` al 100 % y **cero PII** residual (sin nombres) pese a que el 30 % de los tickets trae correo y teléfono y hay fugas inyectadas.
    - Cada contrato es una línea de CI: si mañana un cambio de librería rompe la propagación, `trazas por ticket` deja de ser 1 y el pipeline lo detiene antes de producción (módulo 21, caso E).
    - La cascada de la traza muestra los **saltos entre servicios** (orquestador → especialista) con colores por servicio: es la prueba visual de que el contexto se propaga.
    """))
    code('''
rows = [s for s in SP]
roll = cost_rollup(rows)
naive = collections.defaultdict(float)
for s in rows:
    a = s["attributes"]; i, o = a.get("gen_ai.usage.input_tokens", 0) or 0, a.get("gen_ai.usage.output_tokens", 0) or 0
    if i or o: naive[s["resource"]["service.name"]] += cost_usd(a.get("gen_ai.response.model") or a.get("gen_ai.request.model") or "mock-small", i, o)
names = sorted(roll)
fig, ax = plt.subplots(figsize=(10, 3.8)); x = np.arange(len(names))
ax.bar(x - 0.2, [roll[n]["cost_usd"] * 1000 for n in names], 0.4, label="solo hojas chat (correcto)", color=viz.PALETTE["ok"])
ax.bar(x + 0.2, [naive.get(n, 0) * 1000 for n in names], 0.4, label="sumando todos los spans (doble conteo)", color=viz.PALETTE["error"])
ax.set_xticks(x); ax.set_xticklabels([n.replace("supportops-", "") for n in names], fontsize=8); ax.set_ylabel("coste (milésimas de USD, ilustrativo)"); ax.legend(fontsize=8); ax.set_title("Coste por agente: contarlo mal lo infla")
plt.tight_layout(); plt.show()
print(f"coste total hojas = {sum(r['cost_usd'] for r in roll.values()):.4f} USD · suma ingenua = {sum(naive.values()):.4f} USD · coste del árbol según los resultados = {sum(r.cost_usd for r in RES):.4f} USD")
''')
    md(observe("""
    - El **orquestador** acumula en su `invoke_agent` los tokens de sus hijos: sumar todo cuenta de más (barras rojas por encima de las verdes en el orquestador). El coste por agente correcto sale de las **hojas** y coincide con el coste del árbol de los resultados.
    - La atribución por agente permite decidir dónde optimizar (p. ej. el sintetizador `mock-large` del orquestador y el `billing-agent` concentran el gasto).
    """))

    # ------------------------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · El gateway del Collector: la pieza que integra todo

    El archivo `platform/collector-gateway.yaml` (generado y versionado) integra lo aprendido. **Línea a línea lo importante:**

    - `memory_limiter` primero (módulo 05): protege al proceso; los datos rechazados se devuelven al emisor, que reintenta.
    - `redaction` **antes** de `forward`/`span_metrics` y del tail sampling (módulo 20): nada sin redactar sale de este pipeline ni alimenta métricas ni decisiones de muestreo.
    - `traces/in` → `forward` + `span_metrics` (módulo 18): las métricas RED se calculan sobre el **100 %** de las trazas; `traces/sampled` aplica `tail_sampling` solo a lo que va a Tempo.
    - Políticas de `tail_sampling`: errores, lentas (≥ 8 s), caras (`ottl_condition` sobre un atributo decimal, **no** `numeric_attribute`: SIGSEGV en 0.162.0) y 10 % de base.
    - Exportadores `otlp_grpc`/`otlp_http` (nombres de 0.162) y métricas a Prometheus por su receptor OTLP.
    """)
    code('''
CFG_TEXT = (PLATFORM / "collector-gateway.yaml").read_text()
print(CFG_TEXT)
CFG = yaml.safe_load(CFG_TEXT)
if DOCKER:
    ok, msg = P.validate_collector_config(CFG_TEXT); CFG_OK = True if ok else msg; print("otelcol validate →", "OK" if ok else msg)
else:
    CFG_OK = None; print("(sin Docker: no se pudo ejecutar otelcol validate)")
pl = CFG["service"]["pipelines"]
checks = {"memory_limiter primero en cada pipeline": all(p["processors"][0] == "memory_limiter" for k, p in pl.items() if k != "traces/sampled"),
          "redaction antes de forward y span_metrics": pl["traces/in"]["processors"].index("redaction") < len(pl["traces/in"]["processors"]) and "forward" in pl["traces/in"]["exporters"],
          "span_metrics calculado antes del muestreo": "span_metrics" in pl["traces/in"]["exporters"] and "tail_sampling" in pl["traces/sampled"]["processors"],
          "logs también redactados": "redaction" in pl["logs"]["processors"], "batch al final": all(p["processors"][-1] == "batch" for k, p in pl.items() if k != "traces/in"),
          "sin numeric_attribute sobre decimales": all(p.get("type") != "numeric_attribute" for p in CFG["processors"]["tail_sampling"]["policies"])}
display(pd.Series(checks, name="¿cumple?").to_frame())
''')
    md(observe("""
    - El gateway pasa `otelcol validate` con el binario real (0.162.0) y cumple las seis reglas de diseño que el curso fue acumulando: **cada línea de la tabla es un incidente evitado** (OOM, PII, métricas sesgadas, logs sin redactar, SIGSEGV).
    - La comprobación estructural es la que debe vivir en **CI**: cuesta milisegundos y falla ante el típico «he añadido un procesador y lo he puesto en el sitio equivocado».
    """))

    # ------------------------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · Muestreo y coste: lo que se guarda y lo que cuesta

    Con las políticas del gateway (aquí con el umbral de «lenta» del corpus, 5 s, porque el corpus es de agente único; el gateway usa 8 s para el multi-agente, más lento por construcción) evaluamos, sobre el corpus del módulo 18 (1 200 trazas del agente, con un incidente), qué se conserva y qué sesgo introduce el muestreo en las métricas derivadas **si** se calcularan después (por eso el gateway las calcula antes).
    """)
    code('''
C = S.build_corpus(1200 if FAST_DEV_RUN else 3000, SEED, incidents=[Incident("provider", "llm_error", 300, 420, 0.6, {"status": 503, "at_call": 0, "persistent": True})])
POL = [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"), S.AttrCompare(key="supportops.cost_usd", op=">", value=0.004, name="costly"), S.Probabilistic(10, name="baseline")]
TR = S.TailSampler(POL, decision_wait_s=10, num_traces=50_000).run(C.traces)
COV = S.coverage(TR.kept, C)
W = S.inclusion_weights(TR.kept, lambda t: t.interesting, 0.10)
truth, naive, fixed = S.estimate_metrics(C.traces), S.estimate_metrics(TR.kept), S.estimate_metrics(TR.kept, W)
fig, axes = plt.subplots(1, 2, figsize=(13, 3.8))
keys = ["recall_error_pct", "recall_slow_pct", "recall_costly_pct", "kept_traces_pct", "kept_bytes_pct"]; labels = ["errores", "lentas", "caras", "trazas guardadas", "bytes guardados"]
axes[0].barh(labels, [COV[k] for k in keys], color=[viz.PALETTE["ok"]] * 3 + [viz.PALETTE["traces"]] * 2); axes[0].set_xlim(0, 105); axes[0].set_xlabel("%"); axes[0].set_title("Cobertura del muestreo de la plataforma"); axes[0].invert_yaxis()
vals = [truth["error_rate"] * 100, naive["error_rate"] * 100, fixed["error_rate"] * 100]
axes[1].bar(["verdad\\n(100 % de las trazas)", "tras muestrear\\n(sin pesos)", "tras muestrear\\n(con pesos)"], vals, color=[viz.PALETTE["neutral"], viz.PALETTE["error"], viz.PALETTE["ok"]]); axes[1].set_ylabel("tasa de error (%)"); axes[1].set_title("El sesgo de calcular RED después de muestrear")
for i, v in enumerate(vals): axes[1].text(i, v + 0.2, f"{v:.1f}", ha="center")
plt.tight_layout(); plt.show()
print({k: round(COV[k], 1) for k in keys}, "· error_rate verdad/naive/pesos:", round(truth["error_rate"] * 100, 2), round(naive["error_rate"] * 100, 2), round(fixed["error_rate"] * 100, 2), "· dropped_too_early:", TR.dropped_too_early)
''')
    md(observe("""
    - La política conserva **el 100 % de los errores, las lentas y las caras** con una fracción pequeña del total de trazas y bytes: el muestreo **por valor** es lo que hace asequible la plataforma.
    - Pero la tasa de error calculada *después* del muestreo se infla varias veces (barra roja) frente a la verdad (gris); con pesos de inclusión se corrige (verde). El gateway evita el problema calculando las métricas RED **antes** (`traces/in`).
    - `dropped_too_early` = 0: `num_traces` es suficiente para el tráfico y la espera. Si no lo fuera, perderías trazas **sin error** (módulo 18).
    """))
    code('''
KEEP = COV["kept_traces_pct"] / 100
cm_full = S.StackCostModel.from_corpus(C, 1_000_000, trace_keep=1.0, log_keep=1.0, ingest_price_gb=0.5)      # escenario SaaS ILUSTRATIVO: 0,5 USD por GB ingerido
cm_tail = S.StackCostModel.from_corpus(C, 1_000_000, trace_keep=KEEP, log_keep=KEEP, ingest_price_gb=0.5)
RET = {"traces": 14, "logs": 7, "metrics": 30}
c_full, c_tail = cm_full.monthly_cost(RET), cm_tail.monthly_cost(RET)
fig, ax = plt.subplots(figsize=(8, 3.8)); x = np.arange(3); sig = ["traces", "logs", "metrics"]
ax.bar(x - 0.2, [c_full[s] for s in sig], 0.4, label="guardarlo todo", color=viz.PALETTE["error"]); ax.bar(x + 0.2, [c_tail[s] for s in sig], 0.4, label=f"tail sampling ({KEEP:.0%} de las trazas)", color=viz.PALETTE["ok"])
ax.set_xticks(x); ax.set_xticklabels(sig); ax.set_ylabel("USD/mes (ILUSTRATIVO, 1 M tickets/día)"); ax.legend(); ax.set_title("Coste mensual del propio stack")
plt.tight_layout(); plt.show()
print({k: round(v, 1) for k, v in cm_full.daily_gb().items()}, "GB/día (todo) ·", {k: round(sum(c.values()), 1) for k, c in (("todo", {"t": sum(c_full.values())}), ("tail", {"t": sum(c_tail.values())}))})
''')
    md(observe("""
    - El coste de **trazas y logs** baja en proporción a lo conservado; **las métricas no cambian** (su coste está en las series, no en el volumen de tráfico): otra razón para controlar la cardinalidad.
    - Estos USD son **ilustrativos** (precios configurables del módulo 18): la lección es la **proporción** y la sensibilidad (¿qué pasa si el tráfico se duplica o la retención de logs pasa a 30 días?), que debes incluir en tu revisión de arquitectura.
    """))

    # ------------------------------------------------------------------------------------------------------------- 5
    md("""
    ---
    # 5 · SLOs y alertas sobre la ejecución con incidente

    La caída es **parcial**: solo la ruta de reembolsos (el `billing-agent`, ≈ 20 % del tráfico) agota plazos entre los minutos 10 y 20, y el sistema **degrada bien** (reintentos, escalado a humano). Calculamos dos SLIs —**disponibilidad** (`ok` o `escalated`) y **latencia** (≤ 10 s, el objetivo medido
    sobre la línea base de un multi-agente: más cadena, más latencia que el agente único)— y aplicamos burn rate multiventana de laboratorio (larga 5 min, corta 1 min). Una caída parcial rara vez quema a 14,4×: con el 20 % del tráfico afectado el máximo teórico de la fracción mala es ≈ 20 %, es decir 4× el presupuesto del 5 % de la latencia (y, en disponibilidad, solo una fracción pequeña de esos tickets acaba mal porque el sistema degrada y escala a humano, que cuenta como disponible): por eso aquí usamos la
    política de **ticket (≥ 3×)** y no la de página (módulo 16: dimensiona la política al tipo de incidente).
    """)
    code('''
from supportops.clock import SIM_EPOCH_S as T0
MINS = 30; INC = (10, 20)
def per_minute(pred):
    good = np.zeros(MINS); tot = np.zeros(MINS)
    for r in RES:
        m = int((r.start_s - T0) // 60)
        if 0 <= m < MINS: tot[m] += 1; good[m] += pred(r)
    return good, tot
def burn(g, t, w, obj):
    cg, ct = np.cumsum(np.insert(g, 0, 0)), np.cumsum(np.insert(t, 0, 0)); i = np.arange(len(g)); lo = np.maximum(i + 1 - w, 0)
    gg, tt = cg[i + 1] - cg[lo], ct[i + 1] - ct[lo]
    with np.errstate(divide="ignore", invalid="ignore"): return np.where(tt >= 5, (1 - gg / np.maximum(tt, 1)) / (1 - obj), 0.0)
SLI = {"disponibilidad (ok|escalated)": (lambda r: r.status in ("ok", "escalated"), 0.99), "latencia ≤ 10 s": (lambda r: r.latency_s <= 10, 0.95)}
fig, axes = plt.subplots(1, 2, figsize=(14, 3.8)); FIRES = {}
for ax, (name, (pred, obj)) in zip(axes, SLI.items()):
    g, t = per_minute(pred); bl, bs = burn(g, t, 5, obj), burn(g, t, 1, obj); fire = (bl >= 3) & (bs >= 3); FIRES[name] = fire
    ax.plot(bl, label="burn (5 min)", color=viz.PALETTE["metrics"]); ax.plot(bs, label="burn (1 min)", color=viz.PALETTE["traces"], alpha=0.5); ax.axhline(3, color="k", ls=":"); ax.axvspan(*INC, color="#d64545", alpha=0.12, label="caída real")
    ax.scatter(np.where(fire)[0], bl[fire], color="red", zorder=5, label="alerta"); ax.set_title(f"{name} · objetivo {obj:.0%}"); ax.set_xlabel("minuto"); ax.legend(fontsize=7)
plt.tight_layout(); plt.show()
for name, f in FIRES.items(): print(f"{name:34} primer disparo: {int(np.argmax(f)) if f.any() else None} · falsas alarmas antes del minuto {INC[0]}: {int(f[:INC[0]].sum())} · minutos en alerta: {int(f.sum())}")
''')
    md(observe("""
    - Las **dos** alertas saltan **dentro** de la caída y no antes: la de disponibilidad casi de inmediato (los pocos tickets `degraded` bastan para una quema de ticket) y la de **latencia** unos minutos después (necesita acumular en la ventana larga); la mayor parte del daño está en la latencia, porque el sistema **degrada bien** (reintentos y escalado a humano cuentan como disponibles). Qué SLI es el «de verdad» es una decisión que defenderás en la revisión.
        - Una alerta de **página** (14,4×) no saltaría con un 20 % del tráfico afectado y un sistema que degrada bien: la política (ticket, 3×) debe corresponder al tipo de fallo. Lo contrario es la receta de las alertas que nadie atiende.
    """))
    code('''
UNI = [r for r in RES if int(hashlib.sha256(r.ticket_id.encode()).hexdigest(), 16) % 4 == 0]          # muestra uniforme determinista del 25 %
k, n = sum(r.grounded for r in UNI), len(UNI); lo, hi = wilson_interval(k, n)
QUALITY = {"p": k / n, "lo": lo, "hi": hi, "n": n}
print(f"groundedness (muestra uniforme 25 %): {k}/{n} = {k / n:.3f} · IC 95 % Wilson [{lo:.3f}, {hi:.3f}] · verdad de toda la población: {np.mean([r.grounded for r in RES]):.3f} · objetivo 95 %")
''')

    # ------------------------------------------------------------------------------------------------------------- 6
    md("""
    ---
    # 6 · Privacidad: antes y después

    Misma ejecución con y sin redacción en la aplicación (captura de contenido encendida en ambas), y lo que quedaría si además pasara por el `redaction` del gateway (medido en el módulo 20).
    """)
    code('''
M_RAW, T_RAW, R_RAW = run_platform(N, redact=False, content=True)
M_OFF, T_OFF, R_OFF = run_platform(N, redact=False, content=False)
ex = {"captura apagada (por defecto)": pii_after(M_OFF), "captura + SIN redacción": pii_after(M_RAW), "captura + redacción en la app": pii_after(MESH)}
fig, ax = plt.subplots(figsize=(9, 3.8)); bot = np.zeros(3); names = list(ex)
for kind, col in [("email", viz.PALETTE["error"]), ("phone", viz.PALETTE["warn"]), ("card", viz.PALETTE["profiles"]), ("name", viz.PALETTE["traces"])]:
    v = np.array([ex[n].get(kind, 0) for n in names], float); ax.bar(range(3), v, bottom=bot, label=kind, color=col); bot += v
ax.set_xticks(range(3)); ax.set_xticklabels(names, fontsize=8); ax.set_ylabel("valores de PII en spans + logs"); ax.legend(); ax.set_title("Exposición de PII en la plataforma multi-agente")
plt.tight_layout(); plt.show()
print({k: sum(v.values()) for k, v in ex.items()})
''')
    md(observe("""
    - Con la captura apagada hay **cero** PII, con captura sin redactar hay cientos de valores repartidos por los **cinco servicios** (cada salto del multi-agente vuelve a copiar el texto) y con redacción en la app vuelve a cero.
    - En un multi-agente la PII **se multiplica por el número de saltos** (el orquestador pasa el texto a cada especialista). Por eso la redacción va en **cada** servicio (o en el gateway) y no solo en el primero.
    """))

    # ------------------------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Despliegue: lo verificable

    El módulo 19 desplegó los componentes con Helm. Aquí **comprobamos** lo que el capstone puede afirmar con honestidad: charts y versiones fijados, valores como código presentes y el gateway del capstone coherente con los valores de Kubernetes.
    """)
    code('''
from supportops import k8s as K
rows = [{"release": k, "chart": c.chart, "versión del chart": c.version, "app": c.app_version, "propio": c.own} for k, c in K.CHARTS.items()]
display(pd.DataFrame(rows).set_index("release"))
vals = sorted(p.name for p in (pathlib.Path(ROOT) / "19_kubernetes_helm" / "k8s" / "values").glob("*.yaml"))
print("valores de Helm como código:", vals)
print("imágenes sin 'latest' en el stack:", all("latest" not in l for l in (pathlib.Path(ROOT) / "stack" / "docker-compose.yml").read_text().splitlines() if "image:" in l))
''')
    md(box("warn", "Qué NO se verificó en el despliegue", """
    En el entorno de construcción del curso (sandbox sin red abierta y con *runc* anidado) **ningún pod llegó a ejecutarse** en un clúster: se validaron renderizado, esquemas, configuraciones con los binarios y el flujo de telemetría con laboratorios en Docker (módulo 19).
    Un despliegue real exige además: *probes*, PDB y HPA bajo carga, afinidad por `traceID` con ≥ 2 réplicas del gateway, redes y secretos reales. Márcalo en tu checklist como **manual**.
    """))

    # ------------------------------------------------------------------------------------------------------------- 8
    md("""
    ---
    # 8 · Scorecard integral y checklist de producción

    Reunimos todo en un **scorecard** automático (las comprobaciones que la propia telemetría permite) y lo cruzamos con el **checklist de producción** (`platform/production-checklist.yaml`, 31 puntos, 15 automáticos). Los manuales se declaran con evidencia: aquí
    marcamos cuáles cubre el curso con artefactos entregados (dashboards, runbooks, valores de Helm, plantillas) y cuáles quedan **pendientes** de tu organización.
    """)
    code('''
SC = scorecard(MESH, TICKETS, RES, corpus_cov=COV, cfg_ok=CFG_OK, quality=QUALITY)
display(SC.set_index("id"))
CHK = yaml.safe_load((PLATFORM / "production-checklist.yaml").read_text())["items"]
auto_ok = set(SC[SC["ok"]]["id"]); auto_all = set(SC["id"])
# manuales con evidencia ENTREGADA por el curso (artefactos en el repositorio); el resto: pendiente en TU organización
EVID = {"I2": "instantánea de la spec (04)", "I4": "VersionTagInstrumentor (15)", "I5": "ParentBased (11)", "I7": "max_retries=0 (06)", "C4": "dropped_too_early (18)", "C5": "load_balancing (19)",
        "S3": "runbooks del módulo 16", "Q1": "OnlineEvaluator (14)", "Q2": "ReleaseGate (15)", "K2": "BudgetGuard/LoopGuard (13)", "P3": "InjectionDetector/BehaviorMonitor (20)", "P4": "AuditTrail (20)",
        "D2": "dashboards y alertas aprovisionados (10, 16)", "D3": "límites por tenant (18)"}
PENDING = {"S4": "política pactada con producto", "R1": "mesa de incidentes superada (tú)", "R2": "contratos en CI y game days (tu organización)"}
status = []
for it in CHK:
    cid = it["id"]
    if it["automatica"]: st = "medido" if cid in auto_ok else ("falla" if cid in auto_all else "sin medir aquí")
    else: st = "evidencia entregada" if cid in EVID else "pendiente (tuyo)"
    status.append({**it, "estado": st})
CK = pd.DataFrame(status)
fig, axes = plt.subplots(1, 2, figsize=(14, 4.2))
areas = list(dict.fromkeys(CK["area"])); order = ["medido", "evidencia entregada", "sin medir aquí", "pendiente (tuyo)", "falla"]; colors = [viz.PALETTE["ok"], viz.PALETTE["traces"], viz.PALETTE["warn"], viz.PALETTE["neutral"], viz.PALETTE["error"]]
bot = np.zeros(len(areas))
for st, col in zip(order, colors):
    v = np.array([((CK["area"] == a) & (CK["estado"] == st)).sum() for a in areas], float)
    if v.sum(): axes[0].barh(areas, v, left=bot, label=st, color=col); bot += v
axes[0].invert_yaxis(); axes[0].legend(fontsize=7, loc="lower right"); axes[0].set_title("Checklist de producción por área (31 puntos)")
ca = SC.groupby("área")["ok"].mean(); ang = np.linspace(0, 2 * np.pi, len(ca), endpoint=False); axes[1].remove(); ax2 = fig.add_subplot(122, polar=True)
ax2.plot(np.append(ang, ang[0]), np.append(ca.values, ca.values[0]), color=viz.PALETTE["traces"], lw=2); ax2.fill(ang, ca.values, alpha=0.2, color=viz.PALETTE["traces"]); ax2.set_xticks(ang); ax2.set_xticklabels(ca.index, fontsize=8); ax2.set_ylim(0, 1); ax2.set_title("Scorecard automático por área", pad=18)
plt.tight_layout(); plt.show()
print(CK["estado"].value_counts().to_dict())
''')
    md(observe("""
    - Todo lo **automático** está en verde: la plataforma cumple sus propios contratos en la ejecución de referencia. Eso **no** significa «lista para producción»: de los 31 puntos, los **manuales** son los que de verdad deciden (política de presupuesto pactada, game days, contratos en CI, mesa superada).
    - El valor del checklist es separar lo que **sabes** (medido), lo que **tienes** (artefactos), lo que **no has verificado aquí** (despliegue real) y lo que **te toca** (cultura y proceso). Esa honestidad es la que se defiende en la revisión de arquitectura.
    """))

    # ------------------------------------------------------------------------------------------------------------- 9
    md("""
    ---
    # 9 · Revisión de arquitectura

    La entrega final es una **revisión de arquitectura** (`platform/architecture-review-template.md`): un documento corto que otro ingeniero pueda **atacar**. Estructura: contexto y objetivos, requisitos medibles, arquitectura, **decisiones con alternativas descartadas**, **riesgos con detección y mitigación**, coste con sensibilidad, plan de despliegue y pruebas, y preguntas abiertas.
    Una **tabla de riesgos** buena enlaza cada riesgo con la **señal** que lo detecta (de este mismo curso):
    """)
    code('''
RISKS = pd.DataFrame([
    ("Pérdida silenciosa de telemetría", "media", "alto", "otelcol_exporter_send_failed_*; `dropped_too_early`; traza canario e2e", "Colas con reintento; alertas sobre el pipeline", "05, 18"),
    ("Tormenta de cardinalidad", "media", "alto", "series activas ×N con tráfico plano; valores distintos por etiqueta", "Views del SDK / aggregate_labels; lint de series en CI", "09, 21"),
    ("Trazas partidas", "media", "medio", "trazas por ticket ≠ 1; raíces de subagentes", "Contrato n_traces == n_tickets; ParentBased", "11, 21"),
    ("Fuga de PII", "media", "muy alto", "detector en la salida; contador de PII por tipo; consulta LogQL de control", "Captura apagada; redacción en app y Collector; retención corta", "20"),
    ("Regresión silenciosa de prompt", "alta", "alto", "herramientas por ticket por versión; groundedness; 👎", "Compuerta apareada + canario SPRT + rollback", "15, 21"),
    ("Cascada de reintentos", "media", "alto", "intentos por ticket; timeouts por servicio", "Disyuntor, plazos propagados, degradación", "11, 21"),
    ("Coste desbocado (bucle)", "media", "alto", "coste por ticket p99; trazas con ≥ 5 herramientas idénticas", "LoopGuard, BudgetGuard, max_steps", "13, 21"),
    ("Inyección de prompts", "alta", "alto", "puntuación de inyección; refund sin consulta previa", "Mínimo privilegio, aprobación humana, aislar contenido no fiable", "20"),
], columns=["riesgo", "probabilidad", "impacto", "señal que lo detecta", "mitigación", "módulos"])
display(RISKS)
''')
    md(observe("""
    - Cada riesgo tiene **una señal concreta** y **una mitigación**; ninguno depende de «estar atento». Si no puedes nombrar la señal que lo detecta, no tienes observabilidad de ese riesgo.
    - Los riesgos más probables (regresión silenciosa, inyección) son justo los que **no** disparan alertas clásicas: son los que decide la mesa de incidentes (módulo 21).
    """))

    # ------------------------------------------------------------------------------------------------------------- 10
    md("""
    ---
    # 10 · Plan de pruebas: la mesa de incidentes como examen de aceptación

    La plataforma se acepta cuando un ingeniero que no la construyó resuelve los **cinco incidentes de la mesa** (módulo 21) en menos de 15 minutos **con solo telemetría**. Medimos aquí una versión automática: el *tiempo de cómputo* del diagnóstico de referencia y la puntuación de `I.grade`.
    """)
    code('''
t0 = time.perf_counter(); b = I.build_incident("INC-E"); f = I.reference_facts("INC-E", b)
M = pd.DataFrame(b.metrics); wa, wb, _ = (lambda x: (int(np.argmax(x > 1.5)), 0, 0))(M["traces_per_ticket"].values)
diag = {"cause": "context_propagation_broken", "start_min": wa, "end_min": 59, "culprit": None, "evidence": {"orphan_share_after": f["orphan_share_after"]}, "mitigation": "restore_propagation"}
g = I.grade("INC-E", diag, b); print(f"INC-E · puntuación {g['score']}/{g['of']} · {time.perf_counter() - t0:.2f} s de cómputo · comprobaciones:", g["checks"])
''')

    # ------------------------------------------------------------------------------------------------------------- 11
    md("""
    ---
    # 11 · Con el stack: el gateway del capstone contra Tempo, Loki y Prometheus reales

    Levantamos el **gateway del capstone** (`collector-gateway.yaml`) como contenedor efímero **en la red del stack** (`agentobs_default`, resuelve `tempo`, `loki` y `prometheus`) y le enviamos la telemetría del multi-agente por OTLP/HTTP.
    Comprobamos tres cosas con servicios reales: que Tempo recibe **solo** lo que el muestreo decide (errores y lentas casi completos, base ≈ 10 %), que Loki recibe logs **ya redactados** y que Prometheus recibe métricas **RED de todas las trazas** (span metrics) aunque Tempo no las vea.
    """)
    code('''
class GatewayLab:
    """Collector del capstone en la red del stack (puerto OTLP/HTTP aleatorio en el host; no choca con el Collector del stack)."""
    def __init__(self, cfg_path, network="agentobs_default"):
        self.cfg, self.net, self.name = cfg_path, network, f"capstone-gw-{uuid.uuid4().hex[:6]}"
    def __enter__(self):
        r = subprocess.run(["docker", "run", "-d", "--name", self.name, "--network", self.net, "-p", "127.0.0.1::4318", "-v", f"{self.cfg}:/etc/otelcol-contrib/config.yaml:ro", P.COLLECTOR_IMAGE, "--config=/etc/otelcol-contrib/config.yaml"], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr[:400])
        self.port = int(subprocess.run(["docker", "port", self.name, "4318/tcp"], capture_output=True, text=True).stdout.split(":")[-1])
        for _ in range(60):
            if "Everything is ready" in self.logs(): break
            time.sleep(0.5)
        return self
    def logs(self): r = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True); return r.stdout + r.stderr
    def __exit__(self, *a): subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
LIVE_RUN = None
if LIVE and DOCKER:
    net = subprocess.run(["docker", "network", "ls", "--format", "{{.Name}}"], capture_output=True, text=True).stdout.split()
    net = next((n for n in net if n.endswith("_default") and "agentobs" in n), "agentobs_default")
    with GatewayLab(str(PLATFORM / "collector-gateway.yaml"), net) as gw:
        mesh_l = build_mesh(mode="otlp", endpoint=f"http://127.0.0.1:{gw.port}")
        for a in mesh_l.handles: mesh_l.instr(a, capture_content=True, redact=None)          # SIN redacción en la app: el Collector es la red de seguridad
        system = MultiAgentSupportOps(mesh_l, mode="delegate", policy=DelegationPolicy(timeout_s=6, max_retries=1, breaker_threshold=3, propagate_deadline=True, cancel_in_flight=True))
        inc = Incident("provider", "llm_error", 100, 160, 0.8, {"status": 503, "at_call": 0, "persistent": True})
        lt = generate_tickets(150, SEED + 3, start_s="live", duration_s=240, fault_rates=DEFAULT_FAULT_RATES, incidents=[inc], pii_rate=0.4)
        lres = [system.run(t) for t in lt]; mesh_l.force_flush(); mesh_l.shutdown()
        time.sleep(30)                                        # decision_wait del tail sampling (10 s) + metrics_flush_interval de span_metrics (10 s) + exportación: no pares el gateway antes
        print(gw.logs()[-300:].replace("\\n", " | "))
    LIVE_RUN = (lt, lres)
    print("Enviados", len(lt), "tickets; errores:", sum(r.status in ("error", "degraded") for r in lres), "· lentos (≥ 8 s):", sum(r.latency_s >= 8 for r in lres))
else:
    print("Sin stack o sin Docker: sección omitida (modo degradado). Comando:", STACK.command)
''')
    code('''
if LIVE and LIVE_RUN:
    lt, lres = LIVE_RUN
    def poll(fn, ok, tries=45, wait=2.0):
        v = None
        for _ in range(tries):
            try: v = fn()
            except Exception: v = None
            if v is not None and ok(v): return v
            time.sleep(wait)
        return v
    def stable(fn, checks=3, wait=6.0, tries=25):
        """Espera a que el recuento deje de crecer (Tempo tarda ≈ 15-30 s en hacer buscables las trazas tras el decision_wait)."""
        last, same = -1, 0
        for _ in range(tries):
            try: n = len(fn())
            except Exception: n = -1
            same = same + 1 if (n == last and n > 0) else 0
            last = n
            if same >= checks: break
            time.sleep(wait)
        return last
    n_tempo = stable(lambda: backends.tempo_search('{ name =~ "invoke_workflow.*" }', 10, 500).get("traces", []))
    slow_t = backends.tempo_search('{ trace:duration > 8s }', 10, 500).get("traces", [])
    err_t = backends.tempo_search('{ status = error }', 10, 500).get("traces", [])
    n_slow = sum(r.latency_s > 8 for r in lres)
    print(f"Tempo · trazas de workflow guardadas: {n_tempo} de {len(lt)} enviadas ({n_tempo / len(lt):.0%}) · lentas (> 8 s) guardadas: {len(slow_t)} de {n_slow} enviadas · trazas con algún span en error: {len(err_t)}")
    leak = poll(lambda: backends.loki_query('{service_name=~"supportops.*"} |~ "[A-Za-z0-9._%+-]+@example\\\\\\\\.com"', 10, 200), lambda r: True, tries=3)
    n_logs = backends.loki_query('{service_name=~"supportops.*"}', 10, 500)
    print(f"Loki · líneas recibidas: {len(n_logs)} · líneas con un correo en claro: {len(leak or [])} (esperado 0: el gateway redactó)")
    red_calls = poll(lambda: backends.prom_query('sum(traces_span_metrics_calls_total{span_name="invoke_workflow support_ticket"})'), lambda r: len(r) > 0 and float(r[0]["value"][1]) >= 0.9 * len(lt), tries=45)
    print("Prometheus · span metrics (calls de invoke_workflow, TODAS las trazas):", [m["value"][1] for m in red_calls or []], "· tickets enviados:", len(lt))
''')
    md(observe("""
    - **Tempo** guarda una **fracción** de las trazas (entre un tercio y la mitad en esta ejecución: todas las lentas, las caras y las que tienen algún span en error —durante la caída casi todas—, más el 10 % de base), pero **Prometheus** cuenta **todas** las llamadas a `invoke_workflow` en `traces_span_metrics_calls_total`: las métricas RED salen de `traces/in` (antes del muestreo) y no sufren sesgo.
    - **Loki** recibe los logs **sin correos en claro** aunque la aplicación enviara el contenido sin redactar: el `redaction` del gateway es la red de seguridad (con sus límites: nombres y formatos ofuscados, módulo 20).
    - Si en tu ejecución los números de Tempo difieren, recuerda que tras el *decision wait* hay un retraso de indexación de ≈ 15-20 s (módulo 07): la consulta *polling* lo absorbe.
    """))
    md("Abre el dashboard **22 · Plataforma de agentes de SupportOps** (uid `plataforma-agentes`): SLOs, calidad, coste, privacidad y la **salud del propio pipeline** (spans aceptados/enviados, `dropped_too_early`).")

    # ------------------------------------------------------------------------------------------------------------- 12
    md("""
    ---
    # 12 · 🏭 En producción: cómo se evalúan estas plataformas

    - **Revisiones de arquitectura (*design reviews*)**: los equipos de plataforma de las grandes empresas exigen un documento con requisitos medibles, alternativas descartadas, riesgos con detección y plan de pruebas; es el formato de los ADR (*Architecture Decision Records*, Michael Nygard, 2011) y de las *production readiness reviews* de SRE (*Site Reliability Engineering*, cap. 32 «The Evolving SRE Engagement Model»).
    - **Checklists de preparación para producción** (*Production Readiness*) en la práctica SRE de Google: monitorización, capacidad, respuesta a incidentes y gestión del cambio se revisan **antes** de aceptar un servicio en guardia.
    - **Grafana Labs** promueve OpenTelemetry (convenciones GenAI) con Tempo, Loki y Prometheus/Mimir como base de la observabilidad de aplicaciones de IA; es el patrón que este capstone reproduce con el stack del curso. *(Afirmación general sin cita concreta: contrasta con la documentación actual de Grafana antes de citarla en tu revisión.)*
    - **El coste de observabilidad** es un tema de dirección en las empresas con mucho tráfico: la combinación de *tail sampling*, métricas previas al muestreo y retención por clase es la forma estándar de contenerlo (módulo 18).
    """)

    md("""
    ---
    # 13 · 🧠 Secretos de la élite de la integración

    1. **El orden de los procesadores es arquitectura.** `memory_limiter` → `redaction` → (`forward` → `span_metrics`) → `tail_sampling` → `batch`: invertir dos de ellos produce un incidente distinto cada vez (OOM, PII en métricas, RED sesgada, colas sin sentido).
    2. **Las métricas RED nacen antes del muestreo; las decisiones de muestreo, después de la redacción.** Así ni el muestreo ni la privacidad contaminan los SLOs.
    3. **Un contrato de telemetría vale más que diez dashboards.** «Una traza por ticket», «hojas = árbol», «cero PII» son tres líneas que previenen incidentes enteros.
    4. **En multi-agente, la PII se multiplica por los saltos.** Redacta en cada servicio (o en el gateway), no solo en el primero.
    5. **Los automáticos no sustituyen a los manuales.** El scorecard verde dice que la telemetría cumple sus contratos, no que tu organización responda a un incidente: política de presupuesto, game days y mesa superada deciden.
    6. **Declara lo que NO verificaste.** Un capstone honesto separa *medido*, *entregado*, *no verificado aquí* y *pendiente*: un revisor desconfía de los verdes sin matices.
    7. **El coste de la plataforma también es un SLO.** Series, bytes y retención por clase con presupuesto y alerta de desvío, igual que el coste del agente.
    8. **La plataforma se acepta con un examen de incidentes**, no con una demo de dashboards: si alguien ajeno no resuelve la mesa en 15 minutos, la observabilidad no es suficiente aunque los paneles sean bonitos.
    """)

    md("""
    ---
    # 14 · ⚠️ Errores comunes en un capstone

    - Entregar una arquitectura sin requisitos medibles: nadie puede decir si funciona.
    - Un scorecard que solo mide lo fácil (dashboards creados) y no los contratos (una traza por ticket, PII residual).
    - Olvidar el pipeline como objeto de observación: si el Collector pierde datos, **todo lo demás** miente.
    - Costes sin sensibilidad (¿y si el tráfico se duplica?) y sin supuestos explícitos.
    - Dar por «hecho» el despliegue sin decir qué se probó en un clúster y qué no.
    - Un solo nivel de privacidad (solo app o solo Collector) o contenido capturado «por si acaso».
    """)

    md("""
    ---
    # 15 · Autoevaluación
    """)
    md(details("1 · (Cálculo) Un gateway recibe 150 trazas nuevas/s y espera 10 s antes de decidir. ¿Qué `num_traces` mínimo necesita y qué pasa si pones 1 000?",
               "`num_traces ≥ tráfico × decision_wait = 150 × 10 = 1 500` trazas **simultáneamente** en memoria (con margen: 2-3×). Con 1 000, el Collector descarta las más antiguas **sin evaluarlas** (`sampling_trace_dropped_too_early`) y pierdes trazas —también errores— sin ningún error visible (módulo 18)."))
    md(details("2 · (Diagnóstico) Tempo guarda el 12 % de las trazas pero el panel de «tasa de error» muestra el 14 % cuando tu SLO real es 2,5 %. ¿Qué ocurre y cómo se arregla?",
               "Estás calculando RED con spans **ya muestreados** (el tail sampling conserva errores y lentas): sesgo al alza. Arreglo: calcular `span_metrics` en `traces/in` antes del muestreo (gateway del capstone) o corregir con pesos de inclusión."))
    md(details("3 · (Transferencia) Añaden un tercer nivel de agentes (subagente que delega a otro). ¿Qué cambios mínimos exige la plataforma y qué riesgos aparecen?",
               "Instrumentación: propagación de contexto y `ParentBased` en el nuevo servicio; contratos (`n_traces == n_tickets`, hojas = árbol). SLOs: el plazo debe decrecer con la profundidad y la amplificación crece `(r+1)^d`. Privacidad: redacción en el servicio nuevo (la PII se copia otra vez). Coste/volumen: más spans por traza (revisar `num_traces` y el coste). Riesgo nuevo: cascada de reintentos de profundidad 3."))
    md(details("4 · Explica por qué el scorecard automático no basta para declarar la plataforma «lista para producción».",
               "Porque mide contratos de telemetría sobre una ejecución, no la preparación de la organización: política de presupuesto pactada, runbooks usados, game days, despliegue real en un clúster con carga, límites por tenant. El checklist separa medido / entregado / no verificado / pendiente precisamente para evitarlo."))
    md(details("5 · (Cálculo) Si el 10 % de las trazas base se conserva y el 100 % de las interesantes, ¿qué peso tiene cada traza al corregir la tasa de error?",
               "Interesantes: peso 1 (probabilidad de inclusión 1). Base: peso `1/0,10 = 10`. La tasa corregida es `Σ pesos de trazas con error / Σ pesos totales` (Horvitz-Thompson), que vuelve a la verdad en esperanza."))
    md(details("6 · (Diagnóstico) Tras desplegar la plataforma, Loki muestra correos en claro aunque el gateway tiene `redaction`. Enumera tres causas.",
               "(a) El pipeline de **logs** no incluye el procesador; (b) hay logs que llegan a Loki por otra ruta (envío directo, otro agente); (c) el patrón no cubre el formato (ofuscado) o el dato está en un formato que la regex no ve; (d) la redacción está después de `batch`/exportador o el procesador no se activó en `service.pipelines`."))
    md(details("7 · (Transferencia) Defiende en 5 líneas por qué la mesa de incidentes es mejor criterio de aceptación que una demo.",
               "Una demo muestra el camino feliz; la mesa obliga a **diagnosticar fallos desconocidos** con solo telemetría y mide tiempo y exactitud. Prueba la calidad de los datos (¿están la versión, los intentos, las herramientas?), la capacidad del equipo y la utilidad de los dashboards. Es el único examen que falla si falta una señal que importa."))

    md("""
    ---
    # 16 · Referencias

    - Material del curso: módulos 00-21 y sus referencias (OpenTelemetry, Collector contrib 0.162.0, Tempo 3.1, Loki 3.7, Prometheus 3.15, Grafana 13, Helm).
    - M. Nygard (2011), *Documenting Architecture Decisions* (formato ADR): <https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions>.
    - B. Beyer, C. Jones, J. Petoff, N. R. Murphy (2016), *Site Reliability Engineering*, O'Reilly, cap. 32 «The Evolving SRE Engagement Model» (production readiness reviews).
    - B. Beyer et al. (2018), *The Site Reliability Workbook*, cap. 5 «Alerting on SLOs».
    - C. Majors, L. Fong-Jones, G. Miranker (2022), *Observability Engineering*, O'Reilly.
    - README de `processor/redactionprocessor` y `processor/tailsamplingprocessor` y del conector `spanmetricsconnector` de `opentelemetry-collector-contrib`, v0.162.0.
    """)
    nb.save(out)


# =====================================================================================================================
# PROYECTO · Entrega final
# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "22_proyecto_capstone.ipynb", "Proyecto 22 · Entrega final: tu plataforma de observabilidad")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 22 · Entrega final: la plataforma de SupportOps y su revisión de arquitectura

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 2 h |
    | **Servicios de Compose** | Ninguno. Docker opcional para validar tu Collector con `otelcol validate` (se marca si no hay) |
    | **RAM aproximada** | < 700 MB |
    | **Prerrequisitos** | Lección `22_capstone` y todo el curso |
    | **Conexión** | Integra los proyectos 03-21: lo que construiste por separado, ahora **en una sola plataforma**, medida con su propia telemetría y defendida por escrito |

    ## Contexto de negocio

    SupportOps pasa a producción con el sistema multi-agente. Dirección pide: (1) un **gateway** del Collector que integre redacción, métricas previas al muestreo, tail sampling y exportación; (2) **contratos de telemetría** que corran en CI; (3) un informe de **SLO y calidad** de la ejecución con incidente;
    (4) un **scorecard** y un checklist de producción honestos; (5) una **revisión de arquitectura** que otro ingeniero pueda atacar.

    ## Datos

    El **Paso 0** ejecuta la plataforma completa (multi-agente, `mock`, semilla 42, 480 tickets en 30 min, caída parcial de `get_order` del `billing-agent` entre los minutos 10 y 20) y te da `MESH`, `TICKETS`, `RES`, el corpus de muestreo `C` y los resultados de referencia. Todo en memoria.

    ## Entregables y criterios de evaluación (rúbrica integral)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `gateway_config` | YAML válido; orden correcto de procesadores en los 4 pipelines; span_metrics antes de tail_sampling; `ottl_condition` (no `numeric_attribute`) en la política de coste; `otelcol validate` (si Docker) | 6/6 |
    | R2 | `telemetry_contracts` | Detecta **bien** la plataforma sana (todos OK) y **detecta** una plataforma con propagación rota y otra con PII sin redactar | 5/5 |
    | R3 | `slo_report` | Disponibilidad, p95 y SLI de latencia exactos; alerta multiventana (5 min/1 min, 3×): primer disparo dentro de la caída (min 10-22) y sin falsas alarmas | 5/5 |
    | R4 | `quality_report` | Estimación por muestra uniforme con IC de Wilson: contiene a la verdad y cumple el objetivo | 3/3 |
    | R5 | `sampling_report` | Recall de errores = 100 %, fracción de trazas guardadas ≤ 35 %, y tasa de error corregida a ±15 % de la verdad | 3/3 |
    | R6 | `cost_report` | Coste por agente solo en hojas = coste del árbol (tolerancia relativa 1e-3: cada resultado redondea a 6 decimales) y el doble conteo se detecta | 3/3 |
    | R7 | `checklist_status` | 31 puntos clasificados; los automáticos coinciden con el scorecard; ≥ 12 «evidencia entregada» y 3 «pendiente» | 4/4 |
    | R8 | `architecture_review` | Documento con las 8 secciones, ≥ 6 riesgos con señal y mitigación, coste con sensibilidad (×2) y plan de pruebas con la mesa | 6/6 |

    > 📏 Umbrales calibrados con la solución de referencia en `mock` con la semilla 42 fija; el resto de valores exactos se imprimen en el detalle de la rúbrica.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_22.replace('STACK = check_stack("core+metrics")', 'STACK = check_stack([])').replace("LIVE = not STACK.degraded", "LIVE = False"))
    code(RUN_PLATFORM)
    code(SCORECARD)

    md("## Paso 0 · La plataforma en marcha (te la damos hecha)")
    code('''
N = 480
MESH, TICKETS, RES = run_platform(N)
SP, LG = MESH.span_records(), MESH.log_records()
C = S.build_corpus(1200, SEED, incidents=[Incident("provider", "llm_error", 300, 420, 0.6, {"status": 503, "at_call": 0, "persistent": True})])
T0 = 1_788_253_200.0
print(f"{len(TICKETS)} tickets · {len(SP)} spans · {len(LG)} logs · caída parcial: minutos 10-20 · corpus de muestreo: {len(C)} trazas")
''')

    md("""
    ## Paso 1 · El gateway del Collector

    **TODO 1.** `gateway_config(blocked_values, policies) -> str` devuelve el YAML (con `yaml.safe_dump`) de un Collector con:
    receptor `otlp` (gRPC 4317 y HTTP 4318); procesadores `memory_limiter`, `redaction` (`allow_all_keys: true`, `blocked_values`, `summary: info`), `tail_sampling` (con `policies`) y `batch`; conectores `forward` y `span_metrics`;
    exportadores `otlp_grpc/tempo` (`tempo:4317`, `tls.insecure: true`), `otlp_http/loki` (`http://loki:3100/otlp`) y `otlp_http/prometheus` (`http://prometheus:9090/api/v1/otlp`); y los pipelines `traces/in` (otlp → `memory_limiter`, `redaction` → `forward` y `span_metrics`),
    `traces/sampled` (forward → `tail_sampling`, `batch` → tempo), `metrics` (otlp y span_metrics → `memory_limiter`, `batch` → prometheus) y `logs` (otlp → `memory_limiter`, `redaction`, `batch` → loki).
    """)
    md(hint(1, "Estructura: `receivers`, `processors`, `connectors`, `exporters`, `service.pipelines`. El orden de la lista `processors` de cada pipeline es el orden de ejecución."))
    md(hint(2, "Las políticas se pasan ya hechas (`S.tail_policy_config(policies)` de `supportops.sampling` te da la lista de dicts: úsala tal cual). Para validar: `P.validate_collector_config(cfg)` (Docker)."))
    code('''
POLICIES = [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"), S.AttrCompare(key="supportops.tree.cost_usd", op=">", value=0.004, name="costly"), S.Probabilistic(10, name="baseline")]
BLOCKED = P.go_blocked_values()

def gateway_config(blocked_values, policies) -> str:
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    CFG = gateway_config(BLOCKED, S.tail_policy_config(POLICIES)); print(CFG[:500])
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 2 · Contratos de telemetría

    **TODO 2.** `telemetry_contracts(spans, logs, tickets, results) -> dict[str, bool]` devuelve estas cinco comprobaciones:

    - `una_traza_por_ticket`: nº de `trace_id` distintos de los spans == nº de tickets;
    - `hojas_igual_arbol`: suma de `gen_ai.usage.input_tokens` de los spans `chat` == suma de `input_tokens` de los resultados;
    - `logs_con_trace_id`: todos los logs tienen `trace_id` no vacío;
    - `sin_pii_sin_nombres`: ninguna PII (con `P.pii_exposure`, ignorando `name`) en los atributos de los spans ni en el cuerpo y atributos de los logs;
    - `workflow_raiz`: toda traza tiene exactamente una raíz y se llama `invoke_workflow …`.
    """)
    code('''
def telemetry_contracts(spans, logs, tickets, results) -> dict:
    # TODO 2
    raise NotImplementedError("TODO 2")

try:
    print(telemetry_contracts(SP, LG, TICKETS, RES))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 3 · SLO y alertas

    **TODO 3.** `slo_report(results, t0) -> dict` devuelve `{"availability", "p95_s", "latency_sli", "first_fire", "false_alarms"}`: disponibilidad = fracción de `status` ∈ {`ok`, `escalated`}; `p95_s` = `np.percentile(latency_s, 95)`; `latency_sli` = fracción de `latency_s ≤ 10`.
    La alerta es sobre el **SLI de latencia** (objetivo 95 %): por minuto (`int((r.start_s − t0)//60)`, 30 minutos) cuenta buenos y totales y calcula el burn rate con ventanas de **5 min** (larga) y **1 min** (corta), solo con ≥ 5 eventos en la ventana; dispara si **ambos** ≥ 3,0 (política de ticket: una caída parcial no quema a 14,4×).
    `first_fire` = primer minuto con alerta (o `None`) y `false_alarms` = nº de minutos con alerta **antes del minuto 10**.
    """)
    md(hint(1, "`burn = (1 − buenos/totales)/(1 − objective)` sobre la suma de los últimos `w` minutos (incluido el actual)."))
    code('''
def slo_report(results, t0) -> dict:
    # TODO 3
    raise NotImplementedError("TODO 3")

try:
    print(slo_report(RES, T0))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 4 · Calidad con intervalo

    **TODO 4.** `quality_report(results, every=4) -> dict` toma la **muestra uniforme determinista** de los resultados con `int(sha256(ticket_id).hexdigest(), 16) % every == 0`, y devuelve `{"n", "p", "lo", "hi", "truth", "covers", "meets_target"}`:
    `p = k/n` con `k` = `grounded` verdaderos; `lo, hi` = intervalo de Wilson al 95 % (`wilson_interval(k, n)` de `supportops.quality_eval`); `truth` = fracción de `grounded` en **toda** la población; `covers` = `lo ≤ truth ≤ hi`; `meets_target` = `lo ≥ 0,85`.
    """)
    code('''
def quality_report(results, every=4) -> dict:
    # TODO 4
    raise NotImplementedError("TODO 4")

try:
    print(quality_report(RES))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 5 · Muestreo

    **TODO 5.** `sampling_report(corpus, policies) -> dict` ejecuta `S.TailSampler(policies, decision_wait_s=10, num_traces=50_000)` sobre `corpus.traces`, y devuelve `{"recall_error", "kept_pct", "error_rate_truth", "error_rate_naive", "error_rate_weighted"}`: `recall_error` y `kept_pct` de `S.coverage(kept, corpus)`
    (`recall_error_pct`, `kept_traces_pct`); las tasas con `S.estimate_metrics`: verdad (todas las trazas), ingenua (solo las guardadas) y ponderada con `S.inclusion_weights(kept, lambda t: t.interesting, 0.10)`.
    """)
    code('''
def sampling_report(corpus, policies) -> dict:
    # TODO 5
    raise NotImplementedError("TODO 5")

try:
    print(sampling_report(C, POLICIES))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 6 · Coste

    **TODO 6.** `cost_report(spans) -> dict` devuelve `{"by_service", "total_leaf", "total_naive"}`: `by_service` con `supportops.multiagent.cost_rollup(spans)` (solo hojas `chat`); `total_leaf` = suma de sus `cost_usd`;
    `total_naive` = el coste que saldría de sumar **todos** los spans con `gen_ai.usage.input_tokens/output_tokens` (usa `cost_usd(modelo, in, out)` con `gen_ai.response.model` o `gen_ai.request.model`, y `"mock-small"` si faltan).
    """)
    code('''
def cost_report(spans) -> dict:
    # TODO 6
    raise NotImplementedError("TODO 6")

try:
    r_ = cost_report(SP); print(round(r_["total_leaf"], 4), round(r_["total_naive"], 4))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 7 · Checklist de producción

    **TODO 7.** `checklist_status(items, measured_ok, measured_all, evidence_ids) -> list[dict]` clasifica cada ítem de `platform/production-checklist.yaml`: si `automatica`: `"medido"` si su `id` está en `measured_ok`, `"falla"` si está en `measured_all` pero no en `measured_ok`, `"sin medir"` si no está en `measured_all`;
    si no es automática: `"evidencia"` si su `id` está en `evidence_ids` y `"pendiente"` en otro caso. Devuelve los ítems con una clave `estado` añadida.
    """)
    code('''
CHECKLIST = yaml.safe_load((PLATFORM / "production-checklist.yaml").read_text())["items"]
EVID = {"I2", "I4", "I5", "I7", "C4", "C5", "S3", "Q1", "Q2", "K2", "P3", "P4", "D2", "D3"}      # artefactos entregados por el curso (tuyos al terminar los módulos)

def checklist_status(items, measured_ok, measured_all, evidence_ids) -> list:
    # TODO 7
    raise NotImplementedError("TODO 7")

try:
    sc_ = scorecard(MESH, TICKETS, RES); print(collections.Counter(x["estado"] for x in checklist_status(CHECKLIST, set(sc_[sc_.ok]["id"]), set(sc_["id"]), EVID)))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 8 · Revisión de arquitectura

    **TODO 8.** `architecture_review(facts) -> str` genera el documento **Markdown** de la revisión a partir de los hechos medidos (`facts`: dict con `slo`, `quality`, `sampling`, `cost`, `contracts`, `checklist`). Debe contener, como encabezados `## `, las secciones de la plantilla
    (`platform/architecture-review-template.md`: Contexto y objetivos, Requisitos y restricciones, Arquitectura propuesta, Decisiones clave, Riesgos y modos de fallo, Coste, Plan de despliegue y de pruebas, Preguntas abiertas), una **tabla de riesgos con ≥ 6 filas** (riesgo | señal que lo detecta | mitigación),
    una sección de **coste con sensibilidad** (menciona `×2` de tráfico) con cifras de `facts["cost"]`, y un plan de pruebas que mencione la **mesa de incidentes**. Usa cifras reales de `facts`, no inventadas.
    """)
    code('''
def architecture_review(facts: dict) -> str:
    # TODO 8
    raise NotImplementedError("TODO 8")

try:
    print(architecture_review({"slo": {}, "quality": {}, "sampling": {}, "cost": {}, "contracts": {}, "checklist": {}})[:300])
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ---
    ## Rúbrica automática

    Ejecuta la celda cuando hayas terminado los TODO.
    """)
    code('''
def run_rubric():
    rows = []
    def add(rid, name, ok, detail=""):
        rows.append({"id": rid, "criterio": name, "resultado": "✅" if ok else "❌", "detalle": detail})
    # R1
    try:
        cfg = gateway_config(BLOCKED, S.tail_policy_config(POLICIES)); y = yaml.safe_load(cfg); pl = y["service"]["pipelines"]
        pol = y["processors"]["tail_sampling"]["policies"]
        checks = {"4 pipelines": set(pl) >= {"traces/in", "traces/sampled", "metrics", "logs"},
                  "memory_limiter primero": all(pl[k]["processors"][0] == "memory_limiter" for k in ("traces/in", "metrics", "logs")),
                  "redaction en traces/in y logs, antes de batch": pl["traces/in"]["processors"] == ["memory_limiter", "redaction"] and pl["logs"]["processors"][:2] == ["memory_limiter", "redaction"],
                  "span_metrics antes del muestreo": "span_metrics" in pl["traces/in"]["exporters"] and "forward" in pl["traces/in"]["exporters"] and pl["traces/sampled"]["processors"][0] == "tail_sampling",
                  "ottl_condition y sin numeric_attribute": any(p.get("type") == "ottl_condition" for p in pol) and not any(p.get("type") == "numeric_attribute" for p in pol)}
        if DOCKER:
            ok_v, msg = P.validate_collector_config(cfg); checks["otelcol validate"] = ok_v
        else:
            checks["otelcol validate (omitido sin Docker)"] = True
        add("R1", "gateway_config: 6 comprobaciones", all(checks.values()), str({a: b for a, b in checks.items() if not b} or "todas OK"))
    except Exception as e: add("R1", "gateway_config", False, f"{type(e).__name__}: {e}")
    # R2
    try:
        good = telemetry_contracts(SP, LG, TICKETS, RES)
        broken_mesh, bt, br = run_platform(40, redact=True)
        # plataforma con propagación rota: ejecutamos con propagation=none
        mesh_b = build_mesh(mode="memory"); sysb = MultiAgentSupportOps(mesh_b, mode="delegate", propagation="none"); tb = generate_tickets(30, SEED, duration_s=300, pii_rate=0.0); rb = [sysb.run(t) for t in tb]; mesh_b.force_flush()
        broken = telemetry_contracts(mesh_b.span_records(), mesh_b.log_records(), tb, rb)
        raw_mesh, rt, rr = run_platform(40, redact=False, content=True)
        leaky = telemetry_contracts(raw_mesh.span_records(), raw_mesh.log_records(), rt, rr)
        checks = {"sana: 5/5": all(good.values()) and len(good) == 5, "propagación rota detectada": not broken["una_traza_por_ticket"] and not broken["workflow_raiz"], "PII sin redactar detectada": not leaky["sin_pii_sin_nombres"],
                  "la plataforma rota sigue cumpliendo hojas=árbol": broken["hojas_igual_arbol"], "la que filtra PII sigue con una traza por ticket": leaky["una_traza_por_ticket"]}
        add("R2", "telemetry_contracts: 5 comprobaciones", all(checks.values()), str({a: b for a, b in checks.items() if not b} or "todas OK"))
    except Exception as e: add("R2", "telemetry_contracts", False, f"{type(e).__name__}: {e}")
    # R3
    try:
        r = slo_report(RES, T0)
        av = np.mean([x.status in ("ok", "escalated") for x in RES]); p95 = float(np.percentile([x.latency_s for x in RES], 95)); sli = float(np.mean([x.latency_s <= 10 for x in RES]))
        checks = {"disponibilidad": abs(r["availability"] - av) < 1e-9, "p95": abs(r["p95_s"] - p95) < 1e-6, "SLI de latencia": abs(r["latency_sli"] - sli) < 1e-9,
                  "dispara dentro de la caída (10-22)": r["first_fire"] is not None and 10 <= r["first_fire"] <= 22, "sin falsas alarmas": r["false_alarms"] == 0}
        add("R3", "slo_report: 5 comprobaciones", all(checks.values()), f"{ {a: b for a, b in checks.items() if not b} or 'todas OK'} · disponibilidad={r['availability']:.4f} p95={r['p95_s']:.2f} SLI latencia={r['latency_sli']:.3f} primer disparo={r['first_fire']}")
    except Exception as e: add("R3", "slo_report", False, f"{type(e).__name__}: {e}")
    # R4
    try:
        q = quality_report(RES); truth = np.mean([x.grounded for x in RES])
        checks = {"n ≈ 25 %": 0.15 * len(RES) <= q["n"] <= 0.35 * len(RES), "IC contiene la verdad": q["lo"] <= truth <= q["hi"] and abs(q["truth"] - truth) < 1e-9, "cumple el objetivo": q["meets_target"] is True and q["lo"] >= 0.85}
        add("R4", "quality_report: 3 comprobaciones", all(checks.values()), f"{ {a: b for a, b in checks.items() if not b} or 'todas OK'} · p={q['p']:.3f} IC=[{q['lo']:.3f},{q['hi']:.3f}] verdad={truth:.3f}")
    except Exception as e: add("R4", "quality_report", False, f"{type(e).__name__}: {e}")
    # R5
    try:
        s = sampling_report(C, POLICIES); tr = s["error_rate_truth"]
        checks = {"recall de errores = 100 %": s["recall_error"] >= 99.9, "guarda ≤ 35 % de las trazas": s["kept_pct"] <= 35, "tasa corregida a ±15 % de la verdad": abs(s["error_rate_weighted"] - tr) <= 0.15 * tr}
        add("R5", "sampling_report: 3 comprobaciones", all(checks.values()), f"{ {a: b for a, b in checks.items() if not b} or 'todas OK'} · guardadas={s['kept_pct']:.1f}% · verdad={tr:.4f} naive={s['error_rate_naive']:.4f} ponderada={s['error_rate_weighted']:.4f}")
    except Exception as e: add("R5", "sampling_report", False, f"{type(e).__name__}: {e}")
    # R6
    try:
        c = cost_report(SP)
        checks = {"hojas = árbol": abs(c["total_leaf"] - sum(x.cost_usd for x in RES)) < 1e-3 * c["total_leaf"], "doble conteo detectado": c["total_naive"] > c["total_leaf"] * 1.2, "por servicio": set(c["by_service"]) >= {"supportops-orchestrator", "supportops-billing-agent"}}
        add("R6", "cost_report: 3 comprobaciones", all(checks.values()), f"{ {a: b for a, b in checks.items() if not b} or 'todas OK'} · hojas={c['total_leaf']:.4f} ingenua={c['total_naive']:.4f}")
    except Exception as e: add("R6", "cost_report", False, f"{type(e).__name__}: {e}")
    # R7
    try:
        sc = scorecard(MESH, TICKETS, RES); st = checklist_status(CHECKLIST, set(sc[sc.ok]["id"]), set(sc["id"]), EVID); cnt = collections.Counter(x["estado"] for x in st)
        auto_ids = {x["id"] for x in CHECKLIST if x["automatica"]}
        checks = {"31 puntos": len(st) == 31 and all("estado" in x for x in st), "automáticos = scorecard": {x["id"] for x in st if x["estado"] == "medido"} == (set(sc[sc.ok]["id"]) & auto_ids),
                  "≥ 12 evidencia": cnt["evidencia"] >= 12, "3 pendientes": cnt["pendiente"] == 3}
        add("R7", "checklist_status: 4 comprobaciones", all(checks.values()), f"{ {a: b for a, b in checks.items() if not b} or 'todas OK'} · {dict(cnt)}")
    except Exception as e: add("R7", "checklist_status", False, f"{type(e).__name__}: {e}")
    # R8
    try:
        facts = {"slo": slo_report(RES, T0), "quality": quality_report(RES), "sampling": sampling_report(C, POLICIES), "cost": {"total_usd": float(sum(x.cost_usd for x in RES)), "per_ticket": float(np.mean([x.cost_usd for x in RES])), "monthly_full": 1234.5, "monthly_tail": 456.7},
                 "contracts": telemetry_contracts(SP, LG, TICKETS, RES), "checklist": {"medido": 12}}
        doc = architecture_review(facts)
        heads = [l[3:].strip().lower() for l in doc.splitlines() if l.startswith("## ")]
        need = ["contexto", "requisitos", "arquitectura", "decisiones", "riesgos", "coste", "plan", "preguntas"]
        rows_r = [l for l in doc.splitlines() if l.startswith("|") and not set(l) <= set("|- :")]
        checks = {"8 secciones": all(any(n in h for h in heads) for n in need), "≥ 6 riesgos en tabla": len(rows_r) - 1 >= 6, "riesgos con señal y mitigación": "señal" in doc.lower() and "mitigaci" in doc.lower(),
                  "coste con sensibilidad ×2": "×2" in doc and "456" in doc, "plan con la mesa de incidentes": "mesa de incidentes" in doc.lower(), "usa cifras de facts": f"{facts['slo']['p95_s']:.2f}" in doc or f"{facts['quality']['p']:.3f}" in doc}
        add("R8", "architecture_review: 6 comprobaciones", all(checks.values()), str({a: b for a, b in checks.items() if not b} or "todas OK"))
    except Exception as e: add("R8", "architecture_review", False, f"{type(e).__name__}: {e}")
    return pd.DataFrame(rows).set_index("id")
''')
    code('''
display(run_rubric())
''')

    md("""
    ---
    ## Retos extra (nivel experto)

    1. **Gateway con afinidad**: añade `load_balancing` por `traceID` delante de dos réplicas del gateway (módulo 19) y valida la configuración con `otelcol validate`.
    2. **Detector de incidentes de la mesa sobre la plataforma**: ejecuta `incidents.build_incident` y comprueba que **tus contratos** habrían detectado INC-E (trazas partidas) y INC-D (cardinalidad) antes de que un usuario lo notara.
    3. **Presupuesto de ingesta**: añade una política `rate_limiting` / `bytes_limiting` al gateway para que un incidente masivo no multiplique la factura (módulo 18) y mide su efecto con el simulador.
    4. **Variante de riesgo**: añade un tercer nivel de agentes a tu arquitectura y recalcula amplificación `(r+1)^d`, `num_traces` y el coste de spans.
    5. **Defensa oral**: prepara 5 minutos para explicar a un revisor hostil por qué tu plataforma es suficiente… y qué NO cubre.

    ## Reflexión (producción e hilo conductor)

    - De los 31 puntos del checklist, ¿cuáles dependen de **tu** organización y no de tu código? ¿Cómo los conseguirías en un trimestre?
    - Si solo pudieras instrumentar tres cosas más, ¿cuáles elegirías y qué incidente de la mesa evitaría cada una?
    - ¿Qué parte de este capstone le enseñarías primero a un equipo que empieza (la que da más valor con menos esfuerzo)?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine las funciones y vuelve a lanzar la rúbrica).
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
def gateway_config(blocked_values, policies):
    cfg = {"extensions": {"health_check": {"endpoint": "0.0.0.0:13133"}},
           "receivers": {"otlp": {"protocols": {"grpc": {"endpoint": "0.0.0.0:4317"}, "http": {"endpoint": "0.0.0.0:4318"}}}},
           "processors": {"memory_limiter": {"check_interval": "1s", "limit_mib": 400, "spike_limit_mib": 100},
                          "redaction": {"allow_all_keys": True, "blocked_values": list(blocked_values), "summary": "info"},
                          "tail_sampling": {"decision_wait": "10s", "num_traces": 50000, "expected_new_traces_per_sec": 100, "policies": policies},
                          "batch": {"timeout": "1s", "send_batch_size": 512}},
           "connectors": {"forward": {}, "span_metrics": {"histogram": {"explicit": {"buckets": ["100ms", "500ms", "1s", "2s", "5s", "10s"]}}, "metrics_flush_interval": "10s"}},
           "exporters": {"otlp_grpc/tempo": {"endpoint": "tempo:4317", "tls": {"insecure": True}}, "otlp_http/loki": {"endpoint": "http://loki:3100/otlp"}, "otlp_http/prometheus": {"endpoint": "http://prometheus:9090/api/v1/otlp"}},
           "service": {"extensions": ["health_check"], "pipelines": {
               "traces/in": {"receivers": ["otlp"], "processors": ["memory_limiter", "redaction"], "exporters": ["forward", "span_metrics"]},
               "traces/sampled": {"receivers": ["forward"], "processors": ["tail_sampling", "batch"], "exporters": ["otlp_grpc/tempo"]},
               "metrics": {"receivers": ["otlp", "span_metrics"], "processors": ["memory_limiter", "batch"], "exporters": ["otlp_http/prometheus"]},
               "logs": {"receivers": ["otlp"], "processors": ["memory_limiter", "redaction", "batch"], "exporters": ["otlp_http/loki"]}}}}
    return yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True, width=200)

def telemetry_contracts(spans, logs, tickets, results):
    by = collections.defaultdict(list)
    for s in spans: by[s["trace_id"]].append(s)
    leaf = sum(int(s["attributes"].get("gen_ai.usage.input_tokens", 0) or 0) for s in spans if s["name"].startswith("chat"))
    roots_ok = True
    for ss in by.values():
        ids = {s["span_id"] for s in ss}; roots = [s for s in ss if not s["parent_span_id"] or s["parent_span_id"] not in ids]
        roots_ok &= len(roots) == 1 and roots[0]["name"].startswith("invoke_workflow")
    txt = [json.dumps(s["attributes"], ensure_ascii=False) for s in spans] + [str(l["body"]) + json.dumps(l["attributes"], ensure_ascii=False) for l in logs]
    pii = sum(v for k, v in P.pii_exposure(txt).items() if k != "name")
    return {"una_traza_por_ticket": len(by) == len(tickets), "hojas_igual_arbol": leaf == sum(r.input_tokens for r in results), "logs_con_trace_id": all(bool(l["trace_id"]) for l in logs),
            "sin_pii_sin_nombres": pii == 0, "workflow_raiz": bool(roots_ok)}

def slo_report(results, t0):
    good = np.zeros(30); tot = np.zeros(30)
    for r in results:
        m = int((r.start_s - t0) // 60)
        if 0 <= m < 30: tot[m] += 1; good[m] += r.latency_s <= 10
    def burn(w):
        cg, ct = np.cumsum(np.insert(good, 0, 0)), np.cumsum(np.insert(tot, 0, 0)); i = np.arange(30); lo = np.maximum(i + 1 - w, 0)
        g, t = cg[i + 1] - cg[lo], ct[i + 1] - ct[lo]
        with np.errstate(divide="ignore", invalid="ignore"): return np.where(t >= 5, (1 - g / np.maximum(t, 1)) / 0.05, 0.0)
    fire = (burn(5) >= 3.0) & (burn(1) >= 3.0)
    return {"availability": float(np.mean([r.status in ("ok", "escalated") for r in results])), "p95_s": float(np.percentile([r.latency_s for r in results], 95)),
            "latency_sli": float(np.mean([r.latency_s <= 10 for r in results])), "first_fire": int(np.argmax(fire)) if fire.any() else None, "false_alarms": int(fire[:10].sum())}

def quality_report(results, every=4):
    uni = [r for r in results if int(hashlib.sha256(r.ticket_id.encode()).hexdigest(), 16) % every == 0]
    k, n = sum(r.grounded for r in uni), len(uni); lo, hi = wilson_interval(k, n); truth = float(np.mean([r.grounded for r in results]))
    return {"n": n, "p": k / n, "lo": lo, "hi": hi, "truth": truth, "covers": lo <= truth <= hi, "meets_target": lo >= 0.85}

def sampling_report(corpus, policies):
    kept = S.TailSampler(policies, decision_wait_s=10, num_traces=50_000).run(corpus.traces).kept
    cov = S.coverage(kept, corpus); w = S.inclusion_weights(kept, lambda t: t.interesting, 0.10)
    return {"recall_error": cov["recall_error_pct"], "kept_pct": cov["kept_traces_pct"], "error_rate_truth": S.estimate_metrics(corpus.traces)["error_rate"],
            "error_rate_naive": S.estimate_metrics(kept)["error_rate"], "error_rate_weighted": S.estimate_metrics(kept, w)["error_rate"]}

def cost_report(spans):
    roll = cost_rollup(spans); naive = 0.0
    for s in spans:
        a = s["attributes"]; i, o = a.get("gen_ai.usage.input_tokens", 0) or 0, a.get("gen_ai.usage.output_tokens", 0) or 0
        if i or o: naive += cost_usd(a.get("gen_ai.response.model") or a.get("gen_ai.request.model") or "mock-small", i, o)
    return {"by_service": roll, "total_leaf": sum(v["cost_usd"] for v in roll.values()), "total_naive": naive}

def checklist_status(items, measured_ok, measured_all, evidence_ids):
    out = []
    for it in items:
        cid = it["id"]
        if it["automatica"]: st = "medido" if cid in measured_ok else ("falla" if cid in measured_all else "sin medir")
        else: st = "evidencia" if cid in evidence_ids else "pendiente"
        out.append({**it, "estado": st})
    return out

RISKS = [("Pérdida silenciosa de telemetría", "`otelcol_exporter_send_failed_*`, `dropped_too_early`, traza canario", "colas con reintento y alertas del pipeline"),
         ("Tormenta de cardinalidad", "series activas ×N con tráfico plano", "View del SDK / aggregate_labels y lint de series"),
         ("Trazas partidas", "trazas por ticket ≠ 1", "contrato n_traces == n_tickets y ParentBased"),
         ("Fuga de PII", "contador de PII en la salida y consulta LogQL de control", "captura apagada, redacción en app y Collector, retención corta"),
         ("Regresión silenciosa", "herramientas por ticket por versión y groundedness", "compuerta apareada, canario SPRT y rollback"),
         ("Cascada de reintentos", "intentos por ticket y timeouts por servicio", "disyuntor, plazos propagados y degradación"),
         ("Coste desbocado", "coste p99 por ticket y trazas con bucles", "LoopGuard, BudgetGuard y max_steps")]

def architecture_review(facts):
    slo, q, smp, cost = facts["slo"], facts["quality"], facts["sampling"], facts["cost"]
    L = ["# Revisión de arquitectura · plataforma de observabilidad de SupportOps", "",
         "## 1. Contexto y objetivos", "SupportOps opera un agente multi-agente (orquestador y 4 especialistas). Objetivo: observar disponibilidad, latencia, calidad, coste y privacidad con un presupuesto acotado.", "",
         "## 2. Requisitos y restricciones", f"Disponibilidad ≥ 99 % (medida {slo['availability']:.4f}), p95 ≤ 8 s (medido {slo['p95_s']:.2f} s), groundedness ≥ 95 % (muestra uniforme: {q['p']:.3f}, IC [{q['lo']:.3f}, {q['hi']:.3f}]), 0 PII en backends.", "",
         "## 3. Arquitectura propuesta", "Agentes → gateway del Collector (memory_limiter, redaction, span_metrics antes del muestreo, tail_sampling, batch) → Tempo, Loki y Prometheus → Grafana y alertas por burn rate.", "",
         "## 4. Decisiones clave", "Tail sampling por valor (errores, lentas, caras, 10 % de base) con RED previo al muestreo; redacción en app y Collector; HMAC para seudónimos.", "",
         "## 5. Riesgos y modos de fallo", "", "| Riesgo | Señal que lo detecta | Mitigación |", "|---|---|---|"]
    L += [f"| {a} | {b} | {c} |" for a, b, c in RISKS]
    L += ["", "## 6. Coste", f"Coste del agente: {cost['per_ticket']:.5f} USD por ticket (ilustrativo). Stack a 1 M tickets/día: {cost['monthly_full']:.1f} USD/mes guardándolo todo frente a {cost['monthly_tail']:.1f} USD/mes con tail sampling. Sensibilidad: ×2 de tráfico duplica trazas y logs; las métricas no cambian.", "",
          "## 7. Plan de despliegue y de pruebas", f"Contratos de telemetría en CI ({sum(facts['contracts'].values())}/{len(facts['contracts'])} en la ejecución de referencia), validación del Collector con otelcol validate y aceptación mediante la mesa de incidentes (los cinco casos en < 15 min con solo telemetría).", "",
          "## 8. Preguntas abiertas", "Despliegue real en un clúster con carga; política de presupuesto de error pactada con producto; límites por tenant."]
    return "\\n".join(L)

display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_readme() -> None:
    readme = """# Módulo 22 · Capstone: plataforma de observabilidad completa para SupportOps

🔴 **Experto** · ≈ 4 h 30 min (guía y plataforma de referencia ≈ 2 h 30 min + entrega final ≈ 2 h)

> ⚠️ Todo es **simulado y determinista** (`mock`, semilla 42). El análisis de muestreo y coste usa el corpus del módulo 18 (agente único); el multi-agente aporta contratos, SLO y privacidad. Los precios son ilustrativos.
> Ningún pod llegó a ejecutarse en un clúster en el entorno de construcción (módulo 19): del despliegue se verifican valores y configuraciones, no un clúster en marcha. El README de cada sección lo dice.

**No hay conceptos nuevos: es integración.** El multi-agente de SupportOps con instrumentación OTel por servicio, captura de contenido configurable y redacción; un **gateway del Collector** (`memory_limiter` → `redaction` → `span_metrics` antes del muestreo → `tail_sampling` → `batch`) validado con el binario real y probado contra Tempo/Loki/Prometheus;
**contratos de telemetría**, SLOs con burn rate, calidad con intervalo, coste por agente solo en hojas, sesgo del muestreo; un **scorecard** automático y un **checklist de producción** de 31 puntos (15 automáticos); y una **revisión de arquitectura** que se defiende con riesgos, señales y mitigaciones.

## Objetivos
1. Diseñar la arquitectura a partir de requisitos medibles y justificarla (ADR).
2. Verificar la instrumentación con contratos automáticos.
3. Configurar y validar un gateway del Collector que integre privacidad, RED y muestreo.
4. Medir muestreo, coste, SLO y calidad con su propia telemetría.
5. Evaluar la plataforma (scorecard + checklist) y defenderla en una revisión de arquitectura.

## Contenido
| Archivo | Qué es |
|---|---|
| `22_capstone.ipynb` | Guía y plataforma de referencia (16 secciones, 8 gráficos, gateway real en Docker, scorecard, checklist, revisión de riesgos, 🧠 de élite, autoevaluación) |
| `22_proyecto_capstone.ipynb` | Entrega final: gateway, contratos, SLO, calidad, muestreo, coste, checklist y revisión de arquitectura (rúbrica integral R1-R8, pistas 🪜, solución tras ⛔ SPOILER) |
| `platform/collector-gateway.yaml` | Gateway del Collector de la plataforma (generado por `build_22.py`, validado con `otelcol validate` 0.162.0) |
| `platform/production-checklist.yaml` | Checklist de producción (31 puntos; `automatica: true` = lo mide el scorecard) |
| `platform/architecture-review-template.md` | Plantilla de la revisión de arquitectura (formato ADR) |
| `../stack/grafana/dashboards/22-plataforma-agentes.json` | Dashboard «22 · Plataforma de agentes de SupportOps» (uid `plataforma-agentes`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la validación del Collector y la sección 11 de la lección. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. La sección 11 levanta un gateway efímero en la red `agentobs_default` (≈ 4 min).

## Lecturas
- Módulos 00-21 · Nygard (2011), *Documenting Architecture Decisions* · *SRE* cap. 32 (production readiness reviews) · Majors et al. (2022), *Observability Engineering*.

## Cómo se conecta
Todo lo anterior. La **mesa de incidentes** (módulo 21) es el examen de aceptación y el **compendio de secretos** (`21_elite_playbook/COMPENDIO_SECRETOS.md`) la lista de comprobación de la revisión.
"""
    (COURSE / MOD / "README.md").write_text(readme, encoding="utf-8")
    print("OK README", MOD)


if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    build_platform()
    build_dashboard()
    build_lesson()
    build_project()
    build_readme()
