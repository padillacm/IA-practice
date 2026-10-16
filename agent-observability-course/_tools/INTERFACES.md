# INTERFACES · infraestructura compartida (stack + `supportops`)

Lo creó el autor A1 (oleada 0). **Los demás autores lo reutilizan; no lo cambies sin avisar** (si necesitas algo nuevo,
añádelo de forma compatible y documenta aquí). Todo está verificado en una máquina real con Docker 29 (ver «Qué se probó»).

## 1. Stack (Docker Compose) · `agent-observability-course/stack/`

Ejecuta siempre desde `stack/` (o usa `-f`). Sin `--profile` no arranca nada.

| Perfil | Servicios | RAM aprox. | Comando |
|---|---|---|---|
| `core` | `otel-collector`, `tempo`, `loki`, `grafana` | ~0,4 GB en reposo (medido), ≤ ~1 GB con carga | `docker compose --profile core up -d` |
| `metrics` | `prometheus` | +~0,05 GB | `docker compose --profile core --profile metrics up -d` |
| `profiling` | `pyroscope` (vacío; lo usa el módulo 17) | +~0,06 GB | `docker compose --profile profiling up -d` |
| `all` | todos | ~0,5 GB en reposo; disco de imágenes ≈ 3,5 GB | `docker compose --profile all up -d` |

Parar: `docker compose --profile all down` (conserva datos) · borrar datos: `down -v`.

### Servicios, puertos (host) y salud

| Servicio (nombre Compose = hostname en la red) | Imagen (versión fijada y verificada, oct-2026) | Puertos host | Health (usado por `check_stack`) |
|---|---|---|---|
| `otel-collector` | `otel/opentelemetry-collector-contrib:0.162.0` | 4317 (OTLP gRPC), 4318 (OTLP HTTP), 13133 (health), 8888 (métricas internas), 8889 (métricas de apps) | `GET :13133/` → 200 |
| `tempo` | `grafana/tempo:3.1.0` | 3200 (API HTTP). OTLP gRPC 4317 **solo dentro de la red** | `GET :3200/ready` |
| `loki` | `grafana/loki:3.7.8` | 3100 (API HTTP, OTLP en `/otlp`) | `GET :3100/ready` (503 los primeros ~17 s medidos) |
| `grafana` | `grafana/grafana:13.2.4` | 3000 | `GET :3000/api/health` |
| `prometheus` | `prom/prometheus:v3.15.0` | 9090 | `GET :9090/-/ready` |
| `pyroscope` | `grafana/pyroscope:2.1.2` | 4040 | `GET :4040/ready` (503 el primer minuto: ~60 s medidos) |

- Las versiones se sobrescriben con variables: `OTELCOL_VERSION`, `TEMPO_VERSION`, `LOKI_VERSION`, `GRAFANA_VERSION`, `PROMETHEUS_VERSION`, `PYROSCOPE_VERSION`. `TEMPO_CONFIG=tempo-metrics.yaml` activa el metrics-generator (span metrics + service graphs, módulo 07; requiere `metrics`).
- Por qué estas versiones: son las últimas estables al construir el curso (Docker Hub, oct-2026): **Tempo 3.x** cambia la arquitectura (sin ingester/compactor: `live_store` + `backend_scheduler`; monolítico sin Kafka); **Grafana 13**: el acceso anónimo solo puede ser *Viewer*, por eso el laboratorio usa login `admin`/`admin`. El nombre de exporters del Collector contrib **0.162** es `otlp_grpc` / `otlp_http` (ya no `otlp` / `otlphttp`).
- **Cómo enviar telemetría desde un notebook (host):** OTLP/HTTP `http://localhost:4318` (`/v1/traces|metrics|logs`) u OTLP/gRPC `localhost:4317`. Desde otro contenedor de la red: `http://otel-collector:4318`.
- **Pipelines del Collector** (`stack/otel-collector/config.yaml`): `traces` → Tempo; `logs` → Loki (`otlp_http/loki`, endpoint `http://loki:3100/otlp`); `metrics` → exporter `prometheus` en `:8889` (Prometheus lo raspa, perfil `metrics`). Procesadores: `memory_limiter` → `resource/lab` (añade `deployment.environment.name=lab`) → `batch`. Exporter `debug` definido pero no conectado (actívalo para depurar).
- **Datasources aprovisionados** (UIDs fijos): `tempo`, `loki`, `prometheus` (por defecto), `pyroscope`. Correlaciones ya configuradas: Tempo→Loki (`filterByTraceID`), Tempo→Prometheus, Loki `trace_id`→Tempo (derived field), Prometheus exemplars→Tempo (`trace_id`). Grafana: usuario `admin`, contraseña `admin` (API con basic auth).
- **Dashboards como código**: JSON en `stack/grafana/dashboards/` (carpeta «Curso observabilidad de agentes», recarga cada 10 s, editables en la UI). Hay uno: `00-stack-overview.json` (uid `stack-overview`). Los demás módulos añaden los suyos con prefijo `NN-`. Alertas: `stack/grafana/provisioning/alerting/` (vacío, para módulos 10/16).
- **Convenciones de datos en los backends** (verificadas):
  - Loki: labels de índice `service_name`, `deployment_environment_name`, `detected_level`…; `trace_id`/`span_id`/`severity_text` son *structured metadata* → `{service_name="supportops-agent"} | trace_id="<id>"`.
  - Prometheus: un instrumento OTel `foo` (counter) → `foo_total`; atributos de resource → labels con `_` (`service_name`, `deployment_environment_name`), `job`=service.name, `instance`=service.instance.id. Internas del Collector: `otelcol_receiver_accepted_spans`, `otelcol_exporter_sent_spans`, `otelcol_exporter_send_failed_*`…
  - Tempo: TraceQL con `resource.service.name`, `name`, `span.<attr>`; las trazas nuevas tardan de **unos segundos a ~30 s** en ser buscables (live-store + `max_trace_idle: 10s`); haz *polling* con plazo.
- **Ruido esperado (benigno):** Tempo registra `error calling scheduler ... no jobs found` cada ~15 s (el backend worker sondea sin trabajo); Grafana intenta instalar plugins desde grafana.com al arrancar (sin red falla en silencio). Loki/Pyroscope tardan en estar *ready*.
- **No envíes tiempos del pasado lejano** a Tempo/Loki: usa `generate_tickets(..., start_s="live")` (ventana que termina ahora). El tiempo simulado por defecto (2026-09-01) es solo para datos reproducibles/pregrabados.

## 2. Paquete `supportops` · `pip install -e agent-observability-course` (Python ≥ 3.10; núcleo sin dependencias)

Extras: `[viz]` (matplotlib, numpy, pandas), `[nb]`, `[otel]` (opentelemetry-sdk + exportador OTLP/HTTP), `[anthropic]`, `[openai]`.
En un notebook: `%pip install -q -e "..[viz,otel]"` (cada módulo `NN_slug/` está a un nivel de `pyproject.toml`).

### Variables de entorno
| Variable | Valor por defecto | Uso |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `mock` \| `anthropic` \| `openai` \| `ollama` |
| `LLM_MODEL` | — | obligatoria para `openai`/`ollama`; `anthropic` usa `claude-sonnet-5-5` por defecto; `mock-small` (def.) o `mock-large` |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OLLAMA_HOST` | — | solo por entorno, **nunca** en notebooks |
| `SUPPORTOPS_SEED` | `42` | semilla del mock y de las latencias de herramientas |
| `SUPPORTOPS_REAL_SLEEP_SCALE` | `0` | si `>0`, el reloj simulado *duerme* `s*escala` de verdad (para que el reloj de pared de un SDK vea duraciones) |
| `SUPPORTOPS_MAX_STEPS` | `6` | pasos máximos del bucle del agente |
| `STACK_HOST`, `SUPPORTOPS_STACK_DIR` | `localhost`, `<curso>/stack` | `check_stack()` y comando de Compose |

### API pública (`from supportops import ...`)
- **Agente**: `SupportAgent(llm=None, tools=None, instrumentor=None, name="supportops-agent", max_steps=None, llm_retries=1, max_tokens=512, temperature=0.0)`; `.run(ticket|str) -> AgentResult` (str → ticket ad-hoc). Bucle LLM+tools con 1 reintento ante 5xx/429 (backoff simulado 0.5 s).
- **Resultado** `AgentResult`: `status` (`ok|degraded|escalated|error|max_steps`), `answer`, `steps: list[StepRecord]` (kind `llm|tool`, start/end simulados, tokens), `latency_s`, `input_tokens`, `output_tokens`, `cost_usd` (precios *simulados*), `n_llm_calls`, `n_tool_calls`, `tools_used`, `error_type`, y **ground truth**: `injected_faults`, `grounded` (False = alucinación), `pii_leaked`, `intent_pred`.
- **Proveedor LLM**: `get_llm(provider=None, model=None)`; `MockLLM(model, seed, rules)` (determinista: reglas por palabras clave → herramientas → plantillas; latencia = TTFT lognormal + tokens·s/token + prefill, 2 % de cola lenta natural ×3; tokens ≈ caracteres/4 sobre el contexto completo, así crecen por paso); `Rule`, `ToolStep` para ampliar el mock; adaptadores `anthropic|openai|ollama` (probados con clientes falsos, **no** con API real). Respuesta normalizada `LLMResponse(content, tool_calls, usage, finish_reason, model, provider, latency_s, response_id, meta)`. Errores: `LLMError(status, error_type, retryable, latency_s)`.
- **Herramientas**: `default_tools()` → `ToolRegistry` con `get_order(order_id)`, `issue_refund(order_id, amount_eur, reason)`, `search_kb(query, k)` (TF-IDF sobre 14 documentos), `escalate_to_human(reason, priority)`; `registry.register(Tool(name, description, parameters, fn, latency_median_s, latency_sigma))`; `ToolError(message, error_type, latency_s)`. Datos: 200 clientes `C-0001..`, 600 pedidos `ORD-00001..`, catálogo `SKU-1001..1010` (`supportops.catalog`).
- **Tráfico**: `generate_tickets(n=200, seed=42, duration_s=3600, fault_rates=None, incidents=(), start_s=SIM_EPOCH_S|"live", intent_mix=None, pii_rate=0.06) -> list[Ticket]`; `run_tickets(agent, tickets)`; `to_rows(tickets, results)` (dicts planos → `pandas.DataFrame`); `Incident(name, kind, start_s, end_s, prob, params)` = ventana con tasa elevada de un fallo; `DEFAULT_FAULT_RATES`. Mezcla: 35 % `order_status`, 20 % `refund`, 35 % `kb_question`, 10 % `escalation`; clientes Zipf; llegadas con pico a mitad de ventana; 6 % de tickets con PII *sintética* en el texto.
- **Fallos** (`ticket.faults`, `FAULT_KINDS`): `latency_spike{factor,target}`, `llm_error{status,at_call,persistent}`, `tool_error{tool,error_type}`, `tool_timeout{tool,timeout_s}`, `hallucination`, `tool_loop`, `pii_leak{victim}`. Se activan por ticket con `FaultSpec(kind, params)`; `AgentResult.injected_faults` dice cuáles se activaron de verdad.
- **Reloj simulado**: `SimClock`; todas las latencias son simuladas (`ctx.clock.now_ns()`), de modo que el notebook corre en milisegundos y las trazas son deterministas. `stable_rng(*keys)`, `stable_hex(n, *keys)` para ids deterministas.
- **Puntos de extensión para instrumentar** (módulo 03 en adelante): `Instrumentor` con tres context managers `agent_run(ctx)`, `llm_call(ctx, info)`, `tool_call(ctx, info)` y `log(ctx, level, msg, fields)`; el agente rellena `info.response/info.error/info.result` dentro del `with` y `ctx.result` al terminar. Además emite logs estándar en el logger `supportops.agent` (campos en `record.supportops`). `CompositeInstrumentor(a, b)` encadena varios. **`RecordingInstrumentor`** (sin dependencias) guarda spans y logs en memoria con el modelo de datos OTel y los nombres `invoke_agent <agent>` / `chat <model>` / `execute_tool <tool>`; sirve de referencia para el instrumentor OTel real (usa `start_time=ctx.clock.now_ns()` y `span.end(end_time=...)`; el contexto padre se guarda en `ctx.state`).
- **Stack/backends**: `check_stack(require="core"|"core+metrics"|["tempo","loki"], timeout=1.5, verbose=True) -> StackStatus` (`.up`, `.degraded`, `.missing`, `.starting`, `.command`; imprime el comando exacto de Compose y avisa del modo degradado; nunca lanza). `supportops.backends`: `tempo_search(traceql, minutes, limit)`, `tempo_trace(id)`, `loki_query(logql, minutes, limit)`, `prom_query(promql)`, `grafana_api(path)`, `grafana_post(path, payload)`.
- **Datos pregrabados (modo degradado)** `supportops.sample_data`: `load_tickets/load_runs/load_spans/load_logs/load_metrics_1m/load_meta()`; semilla 42, 240 tickets en 60 min con fallos de fondo e **incidentes** `llm_provider_degraded` (minutos 20–30, `llm_error` persistente) y `tools_slow` (minutos 40–48, herramientas ×8). Regenerar: `python -m supportops.sample_data`. Esquemas documentados en `supportops.schema` (`TICKET_SCHEMA`, `RUN_RECORD_SCHEMA`, `SPAN_SCHEMA`, `LOG_SCHEMA`, `METRIC_SCHEMA`; `schema.describe(...)`).
- **Gráficos**: `supportops.viz` (`apply_style`, `canvas`, `box`, `arrow`, `right/left/top/bottom`, `waterfall(spans)`, `timeline(result.steps)`, `percentile`; paleta: trazas azul, métricas naranja, logs verde, perfiles morado, error rojo).

### Convenciones de nombres (todos los módulos)
- `service.name`: `supportops-agent` (agente), `supportops-orchestrator` / `supportops-<rol>` (multi-agente, 11), `supportops-orders-mcp` (12), `supportops-traffic` (generador de carga). `deployment.environment.name`: `lab` (lo fija el Collector). `service.version`: `0.1.0` + sufijo por módulo si cambia el comportamiento.
- Atributos GenAI: nombres de la spec **GenAI semconv (estado Development; movida al repo `open-telemetry/semantic-conventions-genai`, antes en `semantic-conventions/docs/gen-ai`)**: `gen_ai.operation.name`, `gen_ai.provider.name` (sustituye a `gen_ai.system`), `gen_ai.agent.name`, `gen_ai.conversation.id`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.response.id`, `gen_ai.response.finish_reasons`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type`; `error.type`. Nombres de span: `invoke_agent {gen_ai.agent.name}` (INTERNAL o CLIENT según sea agente local o remoto), `chat {gen_ai.request.model}` (CLIENT), `execute_tool {gen_ai.tool.name}` (INTERNAL). El módulo 04 es el dueño de la verificación a fondo; no copies atributos de memoria.
- Atributos propios del dominio: prefijo `supportops.` (`supportops.ticket.id`, `supportops.customer.id`, `supportops.customer.tier`, `supportops.channel`, `supportops.intent`, `supportops.status`, `supportops.cost_usd`, `supportops.step`, `supportops.attempt`). Cuidado con la cardinalidad: `ticket.id`/`customer.id` en spans y structured metadata sí; **nunca** como label de métricas.
- Métricas: nombres OTel con punto (`supportops.agent.requests`), unidades UCUM (`s`, `{token}`, `USD`).

### Cómo reutilizarlo en un notebook (plantilla de las dos primeras celdas)
```python
%pip install -q -e "..[viz]"        # desde NN_slug/ la raíz instalable (pyproject.toml) es `..`; añade `otel` si hace falta
import os; os.environ.setdefault("LLM_PROVIDER", "mock")
from supportops import *            # SupportAgent, generate_tickets, run_tickets, check_stack, ...
from supportops import sample_data, viz
STACK = check_stack("core")         # imprime estado y comando de Compose; STACK.degraded -> modo degradado
FAST_DEV_RUN = True                 # pocos tickets al iterar
tickets = generate_tickets(40 if FAST_DEV_RUN else 400, seed=42, fault_rates=DEFAULT_FAULT_RATES,
                           start_s="live" if not STACK.degraded else SIM_EPOCH_S)
```
Con el stack caído usa `sample_data.load_runs()/load_spans()/load_logs()` (mismo esquema que lo que genera el agente con `RecordingInstrumentor`).

### Utilidades de builders (opcionales)
`_tools/builders/_a1_common.py` (del autor A1) ofrece `boot(extras)` (celda que instala `supportops` en editable también en Colab), `IMPORTS` (imports + `FAST_DEV_RUN`/`SEED`), `box(kind, title, body)`, `observe(text)`, `details(summary, body)`, `hint(n, body)` y `nb_for(dir, file, title)`.
Puedes importarlas (`sys.path.insert(0, <builders>)`; `from _a1_common import ...`) o ignorarlas. Los notebooks de los módulos 00-02 son ejemplos de la plantilla.

## 3. Qué se probó y qué no (autor A1)
- Probado con Docker real (daemon 29.8, imágenes descargadas del registro): `docker compose config`; `otelcol validate`, `promtool check config`, `loki -verify-config`; arranque de los 6 servicios; telemetría OTLP/HTTP real (trazas+logs+métricas) → Tempo (`/api/search` TraceQL), Loki (`query_range`, `trace_id` como structured metadata), Prometheus (`smoke_requests_total` vía `:8889`), salud de los 4 datasources en Grafana, dashboard `stack-overview` aprovisionado, `tempo-metrics.yaml` (aparecen `traces_spanmetrics_calls_total`, `_latency_bucket`…), `check_stack()` y `backends.*` contra el stack vivo.
- **No** probado: adaptadores `anthropic|openai|ollama` contra servidores reales (solo clientes falsos); `tempo-metrics.yaml` en ejecución prolongada (sí se comprobó que genera `traces_spanmetrics_*` en Prometheus); arm64; Windows/WSL; renderizado visual del dashboard en un navegador (se validaron sus consultas contra Prometheus).

## 4. Telemetría OpenTelemetry · `supportops.telemetry` (autor A2, módulos 03–05)

Versión de **referencia consolidada**: el módulo 03 enseña a construirla a mano y el 04 la ajusta a las GenAI semconv. Los demás módulos la **reutilizan** (`git pull`) y **no la editan** salvo cambios compatibles documentados aquí. Requiere el extra `[otel]` (`opentelemetry-sdk>=1.39`; probado con 1.45.1). Importación: `from supportops.telemetry import setup_telemetry, OTelInstrumentor` (no se importa desde `supportops/__init__`, para que el núcleo siga sin dependencias).

```python
tel = setup_telemetry("supportops-agent")                       # OTLP/HTTP a localhost:4318; sin Collector -> degrada a memoria (avisa 1 vez)
agent = SupportAgent(instrumentor=OTelInstrumentor(tel))        # spans GenAI + métricas mínimas + logs con trace_id/span_id
run_tickets(agent, generate_tickets(40, 42, start_s="live"))    # "live": ventana que termina ahora (Tempo/Loki no aceptan el pasado lejano)
tel.force_flush(); tel.shutdown()                               # SIEMPRE al terminar (los lotes pendientes se perderían)
```

### `setup_telemetry(service_name, *, traces=True, metrics=True, logs=True, endpoint=None, resource_attrs=None, mode="auto", keep_local=True, set_global=True, deterministic_ids=False, metric_interval_s=5.0, export_timeout_s=5.0, service_version="0.1.0") -> TelemetryHandle`
- `endpoint`: base OTLP/HTTP (def. `$OTEL_EXPORTER_OTLP_ENDPOINT` o `http://localhost:4318`; añade `/v1/traces|metrics|logs`). Desde un contenedor: `http://otel-collector:4318`.
- `mode`: `"otlp"` (siempre exporta) · `"memory"` (solo memoria, sin red) · `"auto"` (sondea el puerto; si no responde → `memory`, `handle.mode == "memory"` y `handle.reason` lo explica). Con `keep_local=True` también guarda copias en memoria cuando exporta por OTLP.
- Resource: `service.name`, `service.version`, `service.instance.id` (`<servicio>-<8 hex>`), `telemetry.sdk.*` + `resource_attrs`. **No** pone `deployment.environment.name` (lo añade el Collector, `resource/lab`); si exportas sin Collector pásalo en `resource_attrs`.
- Proveedores globales: se registran (`set_global=True`) y se pueden **volver a registrar** al re-ejecutar la celda (truco sobre atributos privados de la API; solo laboratorio). Procesadores: `BatchSpanProcessor` (1 s), `PeriodicExportingMetricReader` (`metric_interval_s`, acumulativo), `BatchLogRecordProcessor` (1 s).
- `deterministic_ids=True`: trace_id = `stable_hex(32, seed, ticket_id)` (= el de `RecordingInstrumentor`) y span_id derivados; **solo tests/datos pregrabados** (re-ejecutar el mismo ticket reutilizaría el trace_id).
- `TelemetryHandle`: `.mode`, `.endpoint`, `.reason`, `.resource`, `.tracer_provider/.meter_provider/.logger_provider`, `.tracer()/.meter()/.logger()`, `.logging_handler()` (stdlib `logging` → OTel, módulo 08), `.force_flush(timeout_s)->bool`, `.shutdown()` (idempotente; también `with setup_telemetry(...) as tel:`), `.span_export_stats` (`{"ok","failed","ok_spans","failed_spans"}`), y las copias en memoria `.span_records()` (esquema `SPAN_SCHEMA`, vale para `viz.waterfall`), `.log_records()` (`LOG_SCHEMA`), `.metric_points()` (`name, unit, type, attributes, value | count/sum/bucket_counts/explicit_bounds`), `.reset_local()`.

### `OTelInstrumentor(handle, *, capture_content=False, redact=None, emit_metrics=True, max_content_chars=2000, extra_attributes=None)`
Implementa `agent_run/llm_call/tool_call/log` de `Instrumentor` (tiempos = reloj simulado `ctx.clock`; los eventos `exception` también). Se compone con `CompositeInstrumentor(OTelInstrumentor(tel), otro)` (el OTel primero para que el span esté activo en los demás). `instr.trace_ids[ticket_id]` → trace_id hex del ticket; `ctx.state["trace_id"]` también.

| Span | Kind | Atributos (spec GenAI, *Development*) |
|---|---|---|
| `invoke_agent supportops-agent` | INTERNAL | `gen_ai.operation.name=invoke_agent`, `gen_ai.agent.name`, `gen_ai.conversation.id` (=ticket id), `gen_ai.request.model`, al cerrar `gen_ai.usage.input_tokens/output_tokens`; dominio `supportops.ticket.id`, `.customer.id`, `.customer.tier`, `.channel`, `.status`, `.cost_usd`, `.llm_calls`, `.tool_calls`, `.intent`; `error.type` + status ERROR si `status ∈ {error, max_steps}` |
| `chat <modelo>` | CLIENT | `gen_ai.operation.name=chat`, `gen_ai.provider.name` (`mock`…), `gen_ai.request.model/max_tokens/temperature`, `gen_ai.conversation.id`, `supportops.step/attempt`; respuesta: `gen_ai.response.model/id`, `gen_ai.response.finish_reasons` (**normalizados al enum de la spec**: `tool_calls`→`tool_call`), `gen_ai.usage.input_tokens/output_tokens`; fallo: `error.type`, `http.response.status_code`, status ERROR, evento `exception` |
| `execute_tool <herramienta>` | INTERNAL | `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type=function`, `gen_ai.agent.name`, `gen_ai.conversation.id`, `supportops.step`; fallo: `error.type` (p. ej. `upstream_500`), ERROR |

- Con `capture_content=True` (APAGADO por defecto): `gen_ai.input.messages` y `gen_ai.output.messages` (JSON string con `role` + `parts` según la spec) en `chat`; `gen_ai.tool.call.arguments`/`.result` en `execute_tool`. `redact(str)->str` se aplica al JSON. No se captura `gen_ai.system_instructions` (el hook no la recibe).
- **Métricas** (solo si `emit_metrics=True`; A4/módulo 09 añade el resto con su `MetricsInstrumentor` y debe usar `emit_metrics=False`): `gen_ai.client.inference.duration` (histograma, `s`, buckets de la spec 0.01…81.92) y `gen_ai.client.inference.usage.input_tokens` / `.output_tokens` (counter, `{token}`, `gen_ai.token.modality=text`; `unknown` y valor 0 si falló sin uso). Atributos: `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model`, `error.type` (solo duración, en caso de fallo).
- **Logs**: un `LogRecord` OTel por `Instrumentor.log` (sin duplicar el logger estándar), `trace_id`/`span_id` del span activo. Atributos: `supportops.ticket.id`, `supportops.channel`, `supportops.customer.tier`, `error.type`, y el resto de campos del agente como `supportops.<campo>` (`supportops.step`, `.attempt`, `.tool`, `.status`, `.latency_s`).
- Funciones públicas útiles: `messages_to_semconv`, `response_to_semconv`, `normalize_finish_reason`, `error_type_of`, `DURATION_BOUNDARIES`, `TOKEN_BOUNDARIES`.

### Cómo se ve en los backends (medido con el stack real, oct-2026)
- **Tempo**: `{ resource.service.name="supportops-agent" && span.gen_ai.operation.name="chat" }`; 30 tickets → 128 spans en un lote OTLP; el trace de un ticket (4 spans) se recupera con `/api/traces/<trace_id>`.
- **Loki**: `{service_name="supportops-agent"} | trace_id="<id>"`; labels de índice incluyen `service_name`, `deployment_environment_name`, `detected_level`; structured metadata: `trace_id`, `span_id`, `severity_text`, `supportops_ticket_id`, `supportops_channel`, `supportops_customer_tier`, `service_instance_id`… (los puntos de los atributos pasan a `_`).
- **Prometheus** (vía Collector `:8889`): `gen_ai_client_inference_duration_seconds_{bucket,count,sum}`, `gen_ai_client_inference_usage_input_tokens_total`, `gen_ai_client_inference_usage_output_tokens_total` (la unidad `{token}` no aparece en el nombre).
- Nota de versiones: las constantes de `opentelemetry.semconv._incubating.attributes.gen_ai_attributes` (paquete Python) **van por detrás de la spec** (p. ej. aún exponen `gen_ai.system` y `gen_ai.usage.cache_creation.input_tokens`; la spec actual usa `gen_ai.provider.name` y `gen_ai.usage.cache_write.input_tokens`): en SupportOps los nombres se escriben como cadenas verificadas contra el registro.
- Qué se probó: `supportops/tests/test_telemetry.py` (16 pruebas: árbol de spans, atributos, logs correlacionados al 100 %, métricas vs `AgentResult`, errores, captura opt-in, ids deterministas, degradación, recarga de globales, ida y vuelta OTLP/HTTP contra un colector falso local con protobuf real) y un ciclo completo contra Collector+Tempo+Loki+Prometheus reales (30 tickets). **No** probado: OTLP/gRPC, TLS/autenticación, `deterministic_ids` con hilos.

## A5 · Módulos 11–13 (multi-agente, MCP, FinOps) · `supportops.multiagent`, `supportops.mcp_orders`, `supportops.finops`

Compatibles hacia atrás: **no** tocan `agent.py`/`telemetry.py`; se construyen encima de `OTelInstrumentor` (A2). Requieren el extra `[otel]`.

### Módulo 11 · `supportops.multiagent`
```python
from supportops.multiagent import build_mesh, MultiAgentSupportOps, DelegationPolicy, RemoteAgentProcess
mesh = build_mesh(mode="auto")                       # un TelemetryHandle por agente (set_global=False); mode "memory" = sin red
system = MultiAgentSupportOps(mesh, mode="delegate") # "delegate" (orquestador sintetiza) | "handoff" (transfiere al especialista)
res = system.run(ticket)                             # MultiResult: status, trace_id, latency_s, cost_usd (ÁRBOL), tokens, per_agent, retries, timeouts, zombie_s…
rows = mesh.span_records(res.trace_id)               # spans de TODOS los servicios, esquema SPAN_SCHEMA + `links`
```
- **Servicios** (`service.name`, `service.version=0.1.0-m11`): `supportops-orchestrator`, `supportops-orders-agent`, `-billing-agent`, `-knowledge-agent`, `-escalation-agent`. Agentes: `orders-agent` (get_order, mock-small), `billing-agent` (get_order+issue_refund, **mock-large**), `knowledge-agent` (search_kb), `escalation-agent` (escalate_to_human). El orquestador enruta con `mock-small` y sintetiza con `mock-large` (`ScriptedLLM`).
- **Forma de la traza**: raíz `invoke_workflow support_ticket` (INTERNAL, `gen_ai.workflow.name`) → `invoke_agent supportops-orchestrator` → `chat` (enrutar) → por delegación un CLIENT `invoke_agent <agente>` (atributos `supportops.delegation.role=primary|precheck`, `.attempt`, `error.type=timeout|circuit_open|…`) con el `invoke_agent` INTERNAL del servicio como hijo → … → `chat` (síntesis). En *handoff*: `execute_tool transfer_to_<agente>` y el especialista cuelga del workflow (hermano). Atributos de árbol en el workflow: `supportops.tree.cost_usd|input_tokens|output_tokens|agent_calls|retries|timeouts`. **Cuenta tokens/coste solo en las hojas `chat`** (los `invoke_agent` repiten el total de sus hijos).
- **Métricas** (servicio orquestador): `supportops.delegation.attempts` (`gen_ai.agent.name`, `supportops.outcome=ok|error|timeout|circuit_open`, `supportops.mode`), `supportops.handoffs` (`supportops.target_agent`); en cada agente `gen_ai.invoke_agent.duration` (histograma, `s`); las de `OTelInstrumentor` (`gen_ai.client.inference.*`) con `service_name` por agente.
- **Fallos dirigidos**: `FaultSpec(kind, {..., "agent": "billing-agent", "sticky": True})`: sin `agent` afectan al especialista principal; sin `sticky` solo se activan en el primer intento (transitorios).
- **Resiliencia**: `DelegationPolicy(timeout_s, max_retries, backoff_s, breaker_threshold, breaker_cooldown_s, propagate_deadline, cancel_in_flight, fallback_to_human, best_effort_prechecks)`; `DeadlineGuard` (instrumentor que rechaza/cancela llamadas al vencer el plazo; rebobina `SimClock._t`, truco de laboratorio).
- **Propagación**: `format_traceparent`, `parse_traceparent` (estricto), `inject_manual/extract_manual` (solo `traceparent`/`tracestate`; conservan el byte de flags completo: el SDK reciente emite `-03`) y `inject_sdk/extract_sdk` (traceparent + baggage). `propagation="none"` rompe la cadena a propósito.
- **Proceso real**: `RemoteAgentProcess(agent)` (`multiprocessing` *spawn*, cola con cabeceras; `link_mode=parent|link|both|none`; span CONSUMER `process supportops.tasks`).
- **Análisis**: `span_frame`, `agent_tree_text`, `critical_path`, `cost_rollup` (solo hojas), `service_palette`, `waterfall_services`.
- **Dashboard** `stack/grafana/dashboards/11-multiagente.json` (uid `multiagent`).
- Pruebas: `supportops/tests/test_multiagent.py` (25). Nota para otros: el propagador del SDK emite flags `03`; si comparas cabeceras con `-01` fallará.

## A3 · Módulos 06–08 (auto-instrumentación, Tempo/TraceQL, Loki/LogQL) · `supportops.openai_compat`, `supportops.autoinstr_lab`

Módulos nuevos (propios; no tocan `telemetry.py`). Solo librería estándar salvo lo indicado.

- **`supportops.openai_compat`**: `FakeOpenAIServer(llm=None, host="127.0.0.1", port=0, error_rate=0.0, error_status=503, sleep_scale=0.0, seed=None)` — servidor HTTP en un hilo, compatible con `POST /v1/chat/completions` (con y sin `stream`/`include_usage`, `tools`) y `GET /v1/models`, que responde con `MockLLM`. Determinista (clave de llamada = SHA del texto de usuario + nº de turnos; errores con SHA + semilla + nº de intento). `.base_url`, `.requests` (bitácora), context manager. `make_openai_llm(server, model=None, max_retries=0)` → `OpenAILLM` de SupportOps con un cliente `openai.OpenAI` real apuntando al servidor (requiere `pip install openai`). Sirve a cualquier módulo que necesite probar instrumentación de cliente OpenAI sin red.
- **`supportops.autoinstr_lab`**: ejecuta SupportOps con una estrategia de instrumentación **en un subproceso limpio** (`python -m supportops.autoinstr_lab`): `run_variant(variant, n, seed, content="default|on|off", error_rate, stream, extra, enrich, sdk_retries)` → `{"spans","results","meta"}`; `VARIANTS` (manual, openlit, openllmetry, official, hybrid_*, *_decorated); `bench_variant(lib, calls)`; `build_dataset(path)`; `make_wall_instrumentor(tracer, chat=True)` (hooks OTel con reloj de pared; `chat=False` = modo híbrido); `make_enrich_processor()`/`make_context_setter()` (`SpanProcessor.on_start` + `ContextVar` `_TICKET`). Requiere `openai openlit traceloop-sdk opentelemetry-instrumentation-genai-openai` (versiones medidas: 2.54.0 / 1.45.0 / 0.62.4 / 1.2b0 con OTel SDK 1.45.1).
- **Datos pregrabados** del módulo 06: `06_autoinstrumentacion/recorded/lab_seed42.json.gz` (la carpeta `data/` está en `.gitignore`; por eso `recorded/`).
- **Convenciones para otros módulos**: una sola librería de auto-instrumentación por proveedor; `max_retries=0` en el cliente de OpenAI (reintenta el agente); contenido de prompts **apagado** por defecto; los spans de agente/herramienta son manuales (`OTelInstrumentor`).

### Módulo 12 · `supportops.mcp_orders` (requiere `pip install "mcp>=2,<3"` además de `[otel]`; probado con mcp 2.2.0 y 2.3.0)
```python
from supportops.mcp_orders import McpServerProcess, McpToolBridge, WallClockInstrumentor, McpToolSpanEnricher, build_server, tracking_rule
SP = McpServerProcess(telemetry="memory"|"otlp", otlp_endpoint=None, mode="normal|slow|flaky|down|poisoned", capture_args=False, context_policy="trust|link|ignore", sdk_only=False)
BR = McpToolBridge(SP.params(), read_timeout_s=3.0, meter=tel.meter())   # cliente MCP en un hilo; BR.call(name, args, timeout_s=, meta=); BR.register_tools(registry, ["get_order", ...])
SP.spans()   # spans del PROCESO SERVIDOR (JSONL, esquema SPAN_SCHEMA + links); el agente usa tel.span_records()
```
- **Servidor** `python -m supportops.mcp_orders --transport stdio|streamable-http` (`service.name=supportops-orders-mcp`, `0.1.0-m12`): herramientas `get_order`, `list_customer_orders`, `check_stock`, `track_shipment` (API de transportista lenta/fallida: múltiplos de 13 → 503, de 17 → ×25), `issue_refund` (idempotency_key; destructiva), `refund_stats` (diagnóstico). Latencia simulada **comprimida** con `ORDERS_MCP_TIME_SCALE` (def. 0,02). Spans hijos de dependencias (`SELECT orders-db`, `GET carrier-api`, `POST payments-api`), middleware `OrdersTelemetryMiddleware` (atributos `supportops.tool.read_only|destructive`, `network.transport`, `supportops.error.class=caller|server`, evento `supportops.audit` en destructivas, métrica `mcp.server.operation.duration`, argumentos opt-in con `redact_args`) y `RemoteContextPolicy` (`link`: traza propia + span link al llamador).
- **Agente en tiempo de pared**: los spans del SDK de MCP usan el reloj REAL; `WallClockInstrumentor` (subclase de `OTelInstrumentor`, sobreescribe `_span/_fail/log`) + `SUPPORTOPS_REAL_SLEEP_SCALE=0.02` evita mezclar relojes. `McpToolSpanEnricher` marca `execute_tool` de herramientas MCP (`gen_ai.tool.type=extension`, `supportops.mcp.server`, `network.transport=pipe`). **Si cambias `OTelInstrumentor._span/_fail` hay que revisar `WallClockInstrumentor`** (hay una prueba).
- **Errores del puente** → `ToolError.error_type`: `timeout` | `tool_error` (`isError`) | `protocol_error` | `connection_closed`. `register_tools` añade `idempotency_key` estable a `issue_refund`.
- **Hallazgos medidos del SDK v2 (ver lección §10)**: el SDK ya instrumenta cliente (`MCP send tools/call <tool>`, CLIENT; solo `mcp.method.name` y `jsonrpc.request.id`) y servidor (`tools/call <tool>`, SERVER, con `gen_ai.tool.name`, `gen_ai.operation.name`, `mcp.protocol.version`, `error.type=tool_error`); propaga `traceparent` en `params._meta` y **sobrescribe** el `traceparent` que pases en `meta=` con el de su propio span cliente; `isError` no marca el span cliente; herramienta desconocida y argumentos inválidos llegan como `isError` (no como JSON-RPC -32602); un timeout del cliente envía `notifications/cancelled` pero una herramienta síncrona no se interrumpe (trabajo zombi). `asyncio.run_coroutine_threadsafe` copia las contextvars del hilo que llama.
- **Dashboard** `12-mcp-tools.json` (uid `mcp-tools`). Pruebas: `supportops/tests/test_mcp.py` (14, ~15 s: lanzan servidores por stdio).

## A4 · Módulos 09–10 (métricas, Grafana) · `supportops.otel_metrics`, `supportops.dashkit`

Módulos nuevos y propios (no tocan `telemetry.py`). Requieren `[otel]`; `dashkit` solo usa la librería estándar.

### `supportops.otel_metrics` (módulo 09; lo reutilizan 10, 13, 16, 18)
```python
from supportops.telemetry import setup_telemetry, OTelInstrumentor
from supportops.otel_metrics import MetricsInstrumentor, PriceTable, run_live, make_meter_provider, metric_rows, prom_instant, prom_range, prom_exemplars
tel = setup_telemetry("supportops-agent", metric_interval_s=5)
agent = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(tel, emit_metrics=False), MetricsInstrumentor(tel)))  # el de trazas PRIMERO
```
- **`MetricsInstrumentor(provider, prices=ILLUSTRATIVE_PRICES, boundaries="tuned"|"spec", include_tier=True)`**: RED + GenAI + coste. Métricas OTel → Prometheus (vía Collector): `supportops.agent.requests` → `supportops_agent_requests_total{supportops_status,supportops_intent,supportops_customer_tier,gen_ai_agent_name}`; `gen_ai.invoke_agent.duration` → `gen_ai_invoke_agent_duration_seconds_bucket`; `gen_ai.client.inference.duration` (`..._seconds_bucket`), `gen_ai.client.inference.usage.{input,output}_tokens` (`..._tokens_total`), `gen_ai.client.inference.operation.{input,output}_tokens` (histogramas), `gen_ai.execute_tool.duration` (`gen_ai_tool_name`), `gen_ai.invoke_agent.{inference_calls,tool_calls}`, `supportops.llm.cost` → `supportops_llm_cost_USD_total{gen_ai_request_model}` (**`USD` se pega al nombre**), `supportops.agent.request.cost`, `supportops.llm.context_utilization` → `..._ratio`, `supportops.agent.active_runs`. Atributos SIEMPRE acotados (nunca `ticket_id`/`customer_id`). Spec GenAI: estado *Development*.
- **A2 ya emite** `gen_ai.client.inference.duration` y `usage.*` con `OTelInstrumentor(emit_metrics=True)`: si compones con `MetricsInstrumentor` pasa **`emit_metrics=False`** al de A2 (si no, doble conteo). Registrar métricas **dentro** del span activo es lo que genera los *exemplars*.
- **`PriceTable({modelo: (usd_in_Mtok, usd_out_Mtok)})`** · `ILLUSTRATIVE_PRICES` (**ilustrativos, no reales**; `SUPPORTOPS_PRICES_JSON` los sobreescribe). Modelo desconocido → coste 0 y `MetricsInstrumentor.unknown_models`.
- **`run_live(agent, tickets, seconds)`**: reparte los tickets en tiempo REAL (las métricas se estampan con el reloj de pared) y reancla `created_at`. Los `Incident(start_s, end_s)` de `generate_tickets(..., start_s=0.0, duration_s=seconds)` están en segundos reales.
- **Prometheus HTTP**: `prom_instant(q, at=None)` (lanza `ValueError` si PromQL inválido), `prom_range(q, minutes, step_s)`, `prom_raw('x[2m]')`, `prom_exemplars(selector, minutes)`, `prom_series_count(match)`, `prom_api(path, **params)`, `PROM_URL`; `tempo_spans(backends.tempo_trace(id))` convierte la traza de Tempo (ids base64) al esquema `SPAN_SCHEMA`.
- **Sin Docker**: `make_meter_provider(otlp_endpoint=None)` + `metric_rows(reader)` (incluye exemplars; ¡cada `collect()` los vacía: léelos una vez!).
- **Hechos medidos (Prometheus v3.15.0, Collector 0.162.0, SDK 1.45.1)**: el exporter `prometheus` del Collector exporta histogramas **exponenciales solo como `+Inf`**; Prometheus (receptor OTLP) **rechaza delta** (HTTP 500) y guarda exponenciales como **nativos sin flags**; el SDK de Python **no tiene cardinality limit**; `rate(x[15s])` con *scrape* de 15 s da vacío; dos *views* sobre el mismo instrumento crean dos *streams*; `service.instance.id` cambia en cada `setup_telemetry` (series huérfanas ~5 min).

### `supportops.dashkit` (módulos 09–10): dashboards de Grafana como código (esquema clásico, `schemaVersion` 39)
- `Dashboard(uid, title, tags=, refresh=, time_from=)` → `.variable(var_query/var_custom/var_interval/var_datasource)`, `.row(titulo)`, `.add(*paneles)` (rejilla de 24 columnas automática), `.dash_link(...)`, `.save(ruta)`; paneles `timeseries, stat, gauge, bargauge, heatmap, table, logs, traces_table, text`; consultas `prom(expr, legend, exemplar=)`, `loki(...)`, `tempo(traceql)`; `link`, `explore_url`, `thresholds`.
- **`lint(d)`** (higiene: uid, tags, títulos, `description`, datasource en cada target, ventanas de `rate`) y **`query_check(d)`** (ejecuta cada consulta contra Grafana con `/api/ds/query`; variables → `.*`).
- Dashboards del curso por NN: `09-genai-metrics.json` (uid `genai-metrics`), `10-salud-del-agente.json` (uid `salud-agente`).

### 4.1 Utilidades de los módulos 04 y 05 (autor A2)
- **Instantánea de la spec GenAI** (`04_genai_semconv/genai_semconv_snapshot.json`; commit `f3c6d0c9`, 2026-10-14 de `open-telemetry/semantic-conventions-genai`): atributos con tipo/enum, tipos de span con nivel de requisito por atributo, métricas y enum de *finish reasons*. Úsala (en vez de copiar nombres de memoria o del paquete `opentelemetry-semantic-conventions`, que va por detrás) para validar atributos; se regenera con `GENAI_SPEC_DIR=<clon> python _tools/builders/build_04.py`. Reglas de nombre ya verificadas: `gen_ai.provider.name` (no `gen_ai.system`), `gen_ai.usage.cache_write.input_tokens`, `input_tokens` **incluye** caché, `finish_reasons` normalizados (`stop|length|content_filter|tool_call|error`), `invoke_agent` en proceso = INTERNAL y **sin** `gen_ai.provider.name`.
- **Collector de laboratorio** (`05_collector`, clase `LabCollector` en las celdas de lección/proyecto): `docker run` de la imagen contrib 0.162.0 con **puertos de host aleatorios** (no choca con el stack ni exige el candado), exportador `file` en `/out` para leer lo que sale y métricas internas `otelcol_*` en el puerto mapeado de 8888. Conectado a la red `agentobs_default` resuelve `tempo`, `loki`, `prometheus`. Receptor OTLP de Prometheus activado en el stack: `http://prometheus:9090/api/v1/otlp` (exportador `otlp_http`); Prometheus **no promociona** atributos de resource a etiquetas salvo `job`/`instance` (el resto va a `target_info`).
- `05_collector/collector_components_0.162.0.json`: componentes de `otelcol-contrib` 0.162.0 y su estabilidad por señal (`otelcol components`). En 0.162 los nombres canónicos son `otlp_grpc`, `otlp_http`, `prometheus_remote_write`, `span_metrics`, `file_log`, `k8s_attributes`…; los antiguos se aceptan como alias en `validate` pero no aparecen en `components`.
- Qué se probó: lección y proyecto de 05 ejecutados con nbclient con Docker real (y en modo sin Docker); la solución del proyecto pasa linter, `otelcol validate`, el control funcional con exportadores `file` y el extremo a extremo contra Tempo/Loki/Prometheus reales. **No** probado: Collector en Kubernetes, cola persistente (`file_storage`) ni el conector `span_metrics` (solo se proponen como retos).

### Módulo 13 · `supportops.finops` (⚠️ precios ILUSTRATIVOS y configurables; requiere `[otel]`)
```python
from supportops.finops import ILLUSTRATIVE_PRICES, PriceTable, ModelPrice, Usage4, semconv_usage, CacheSimulator, CostLedger, FinOpsInstrumentor, BudgetGuard, BudgetPool, DowngradeLLM, LoopGuard
ledger, cache = CostLedger(), CacheSimulator(min_prefix_tokens=256)                       # TTL 5 min; el mínimo cacheable es un parámetro de laboratorio
fin = FinOpsInstrumentor(ILLUSTRATIVE_PRICES, cache=cache, ledger=ledger, handle=tel)    # handle=None: solo libro; con handle: spans + métricas + logs
agent = SupportAgent(system_prompt=policy_prompt(2500), instrumentor=CompositeInstrumentor(OTelInstrumentor(tel), BudgetGuard(ILLUSTRATIVE_PRICES, per_ticket_usd=...), fin))   # ¡guards FUERA, FinOps DENTRO!
ledger.to_frame()   # una fila por ticket: customer_id, tier, feature, model, status, input_total/cache_read/cache_write/output, cost_usd(+desglose), wasted_usd, loop, cache_hit_ratio…
```
- **Precios**: `PriceTable.from_json/from_env` (`SUPPORTOPS_PRICES_FILE`); `ILLUSTRATIVE_PRICES` = mock-small 0,25/1,25 y mock-large 3/15 USD/M + caché de laboratorio (lectura 0,1×, escritura 1,25×); `describe()` imprime el aviso «ILUSTRATIVOS». **Semántica de tokens (spec GenAI)**: `input_total` INCLUYE `cache_read` y `cache_write` (subconjuntos; `Usage4` lo valida); `semconv_usage("anthropic", ...)` normaliza el estilo Anthropic (input sin caché).
- **Telemetría de `FinOpsInstrumentor`**: span `chat`: `gen_ai.usage.cache_read.input_tokens`, `gen_ai.usage.cache_write.input_tokens`, `supportops.finops.cost_usd`; span raíz: `supportops.finops.cost_usd|cache_hit_ratio|wasted|feature` (NO pisa `supportops.cost_usd` del OTelInstrumentor); métricas por EJECUCIÓN (sin customer/ticket como etiqueta): `supportops.llm.cost` (USD; `supportops.cost.component=input|cache_read|cache_write|output`), `supportops.llm.tokens` (`gen_ai.token.type`), `supportops.ticket.cost` (histograma USD), `supportops.ticket.cost.wasted`, `supportops.tickets`; presupuesto: `BudgetPool.register_metrics(meter, elapsed_fn)` → `supportops.budget.spent|limit` (USD) y `.burn_rate`; log `ticket costed` con `supportops.customer.id` y `supportops.finops.cost_usd` (atribución por cliente en Loki).
- **Guards como Instrumentor** (rechazan ANTES de la llamada): `BudgetGuard` (`LLMError(error_type="budget_exceeded", status=429)`; tope por ticket/cliente-día/pool, `tier_multiplier`), `LoopGuard` (`ToolError("loop_detected")` y aborta la siguiente llamada al LLM con `LLMError("loop_detected")`), `DowngradeLLM` (envoltorio del LLM). Se evalúan ENTRE llamadas: se puede pasar del tope por una llamada.
- `cost_drift_alert(series, baseline_n, ratio, persist)` y `finops_alert_rule_json(folder_uid)` (regla de Grafana vía `/api/v1/provisioning/alert-rules`). Dashboard `13-finops.json` (uid `finops`). Pruebas: `supportops/tests/test_finops.py` (9).

### A3 · módulos 07–08: `traceql_mini`, `tempo_lab`, `loki_lab`
- **`supportops.traceql_mini`**: mini motor de TraceQL en Python (subconjunto: selectores con intrínsecos/atributos con ámbito, `&& || !`, `>> > << < ~`, `count/avg/max/min/sum`, `by()`, `select()`). `search(spans, query)` → `TraceHit`s; `ticket_ids(spans, hits)`; `evaluate_trace`, `parse`. Validado contra Tempo 3.1.0: 18/18 consultas con el mismo conjunto de tickets (lección 07). Pruebas: `supportops/tests/test_traceql_mini.py`.
- **`supportops.tempo_lab`**: `run_batch(n, seed, live=True, duration_s=600, export=None, extra=[...])` → `Batch(spans, results, trace_ids)`: SupportOps como **4 servicios** (`supportops-agent`, `llm-gateway`, `orders-api`, `kb-search`; `orders-api` con SELECT `db.system=postgresql`) con propagación W3C y un relato de incidentes (`INCIDENT_STORY`). `wait_for_traces`, `tempo_metrics` (`/api/metrics/query_range`), `metrics_series`, `prom_range`. Usa `OTelInstrumentor` de A2 sin modificarlo; `extra` admite instrumentores adicionales (p. ej. los de logs).
- **`supportops.loki_lab`**: `LokiPusher` (push JSON a `/loki/api/v1/push` con structured metadata), `JsonLogInstrumentor` (logs JSON, `service_name=supportops-agent-json`), `AccessLogInstrumentor` (logfmt de `llm-gateway/orders-api/kb-search`, `service_name=<svc>-access`), `wait_for_logs`, `logfmt`.
- **Configuración de Tempo (compatible):** `stack/tempo/tempo.yaml` y `tempo-metrics.yaml` llevan `live_store.wal.ingestion_time_range_slack: 15m` (y el metrics-generator, `metrics_ingestion_time_range_slack` y la sobreescritura por tenant a 15m). **Motivo medido:** con la holgura por defecto (2 min) Tempo no encuentra por búsqueda con rango las trazas con spans de hace más de ~2 min (el lote «live» de 10 min: solo 12-14 de 30 trazas visibles, aunque `/api/traces/<id>` las devuelve); con 15 m, 30/30 en 20-30 s. El metrics-generator descarta spans de más de 30 s por defecto. Tras cambiar el YAML hay que **reiniciar** Tempo (`docker compose restart tempo`).
- Datos: `07_tempo_traceql/recorded/{batch_seed42,capture_live}.json.gz`. Dashboard `07-tempo-traceql.json` (uid `tempo-traceql`).
- Hallazgos operativos para otros módulos: por identificador una traza es consultable al instante; por búsqueda tarda ≈ 15-20 s. Los spans correctos son `UNSET` (no `OK`). Los CLIENT con `db.system`/`peer.service` crean nodos virtuales en el service graph.
- **`supportops.logql_mini`** (módulo 08): mini motor de LogQL de **logs** (selectores, `|= != |~ !~`, `| json`, `| logfmt`, filtros de etiqueta con `and/or`, structured metadata como etiquetas); `query(entries, logql)`, `entries_from_payload`, `parse_logfmt`. Validado contra Loki 3.7.8: 11/11 consultas con el mismo nº de líneas. No hace métricas ni `line_format`.
- **`supportops.loki_lab`** (ampliado): `run_logs_batch(n, seed, live, export)` → `(Batch, LokiPusher)` con trazas + logs por 3 rutas (OTLP vía `OTelInstrumentor`; JSON `supportops-agent-json`; logfmt `<svc>-access`); `LokiPusher.full_payload()`, `loki_range` (consultas de métricas), `loki_stats` (bytes procesados). Datos: `08_loki_logql/recorded/{logs_seed42,capture_live}.json.gz`; dashboard `08-logs-agente.json` (uid `logs-agente`).
- Hallazgos de Loki 3.7.8 medidos: la ruta OTLP tarda más en ser visible que el push directo (esperar a que el recuento se estabilice); `/loki/api/v1/index/stats` devuelve 0 para datos aún en memoria del ingester; los filtros de línea no reducen bytes procesados (sí CPU del parser); selector ancho ≈ 3,4× bytes que el estrecho en el lote del módulo.

## A6 · Módulos 14–16 (evaluación online, calidad/regresión, SLOs) · `supportops.quality_eval`, `supportops.regression`, `supportops.slo`

Módulos nuevos y propios (no tocan `telemetry.py`/`agent.py`). `quality_eval` y `regression` requieren `[otel]` solo para emitir telemetría; `slo` requiere numpy. Los tres tienen pruebas (`tests/test_quality_eval.py`, `test_regression.py`, `test_slo.py`).

### Módulo 14 · `supportops.quality_eval`
```python
from supportops.quality_eval import CaseCollector, MockJudge, RuleJudge, LLMJudge, get_judge, StratifiedSampler, RateSampler, OnlineEvaluator, simulate_feedback
col = CaseCollector(version="v1", on_case=evaluator.submit)       # Instrumentor: componlo DESPUÉS del OTelInstrumentor (necesita el span activo)
agent = SupportAgent(instrumentor=CompositeInstrumentor(OTelInstrumentor(tel_agent), col))
ev = OnlineEvaluator(MockJudge(42), StratifiedSampler(), tel_evaluator)   # tel_evaluator = setup_telemetry("supportops-evaluator")
ev.run_pending(); ev.estimate_quality()   # {"estimate" (post-estratificada), "se", "naive", ...}
```
- **`EvalCase`**: lo que ve el juez (`question`, `answer`, `context` = JSON de resultados de herramientas) + ids (`trace_id`, `span_id` del `chat` final, `response_id`) + `truth` (ground truth: `grounded`, `pii_leaked`, `faults`; **el juez nunca lo ve**). `truth_bad` = alucinación | PII | sin resolver. El colector lee `resp.meta["fault"]` (`hallucination`, `prompt_regression`) para el ground truth.
- **Jueces**: `RuleJudge` (exacto en groundedness/PII), `MockJudge(seed, miss_rate=.10, false_alarm_rate=.02, noise, verbosity_bias, position_bias)` (con errores deterministas; `compare(q, a, b, key=)` por pares), `LLMJudge(llm)` (JSON; `error="parse_error"` si no parsea), `get_judge()` (`JUDGE_PROVIDER`, `JUDGE_MODEL`). Criterios: `groundedness`, `relevance`, `resolution`, `pii_safety`; `Verdict.passed` = los críticos aprueban. Coste del juez con precios del mock (`mock-large`), **≈ 9× el de atender el ticket**.
- **Telemetría emitida por `OnlineEvaluator`** (servicio `supportops-evaluator`): span `supportops.evaluate` (INTERNAL, traza propia con *link* al span evaluado; atributos `supportops.eval.*`) con hijo `chat <juez>` (tokens); **evento** `gen_ai.evaluation.result` (log OTel con `event_name`, `trace_id`/`span_id` del span `chat` evaluado, cuerpo `<criterio>=<pass|fail>`); métricas → Prometheus: `supportops_eval_population_total` (TODAS las peticiones por estrato), `_sampled_total`, `_results_total{gen_ai_evaluation_name,gen_ai_evaluation_score_label,supportops_eval_stratum,gen_ai_agent_version}`, `supportops_eval_score_bucket` (unidad `1`, sin sufijo), `_cost_USD_total`, `_tokens_total`, `_duration_seconds_*`, `supportops_feedback_total{supportops_feedback_rating}`, `_errors_total`. Estratos: `error` (1,0) · `escalated` (0,5) · `premium` (0,25) · `base` (0,10). `event_records(tel)` (en `regression`) lee los eventos de un handle en memoria.
- **Hallazgos medidos (Loki 3.7.8, Prometheus v3.15)**: el `event_name` del log **no llega** a Loki (ni etiqueta ni metadato): filtra por `gen_ai_evaluation_name`/`..._score_label` y pon cuerpo legible; los `le` de Prometheus son `"5.0"`, `"0.0005"` (floats), no `"5"`.
- Estadística: `wilson_interval`, `required_sample_size`, `post_stratified_rate`, `rogan_gladen`, `confusion`. Feedback **sintético** con sesgo de respuesta (`simulate_feedback`). Atributos de versión: `VersionTagInstrumentor(version)` pone `gen_ai.agent.version` en `invoke_agent` y `gen_ai.prompt.name/version` en `chat` (atributos de la spec GenAI, *Development*).
- Dashboard `14-calidad-online.json` (uid `calidad-online`; 14 consultas validadas contra Grafana). Eventos de evaluación: **semconv GenAI, estado Development**, verificado contra `open-telemetry/semantic-conventions-genai` (commit `f3c6d0c9`, 2026-10-14).

### Módulo 15 · `supportops.regression`
```python
from supportops.regression import run_version, make_agent, select_golden, golden_to_tickets, replay, ReleaseGate, canary_route, sprt_bernoulli, LivePipeline
res, cases = run_version("v2", tickets)                 # versiones de prompt SIMULADAS: "v1" (base), "v2" (regresión silenciosa), "v2.1" (hotfix)
agent, col = make_agent("v2", instrumentors=[OTelInstrumentor(tel), VersionTagInstrumentor("v2")], collector=CaseCollector("v2", on_case=ev.submit))
lp = LivePipeline(("v1", "v2"), mode="otlp", sampler=RateSampler(0.6)); lp.run_live(tickets, 60, lambda t, el: "v2" if ... else "v1"); lp.close()   # agente + MetricsInstrumentor (09) + evaluador (14) en vivo
```
- **`PromptVariantLLM`**: envuelve el mock; en `v2` el 22 % de los tickets que usarían una herramienta reciben una respuesta inventada inmediata (`meta["fault"]="prompt_regression"`, que el `CaseCollector` guarda en `truth`). Efecto medido: latencia −15 %, coste −12 %, errores iguales, herramientas/ticket 1,08→0,86, groundedness 92,8→75,2 %. `v2.1` (4 %) recupera casi todo. Es una SIMULACIÓN determinista, no un modelo real.
- **Dataset desde trazas**: `select_golden(cases, verdicts, feedback, n_total, tools_by_ticket)` (cubos `thumbs_down > judge_fail > error > escalated > random_pass`, orden por `stable_hex(8,"golden",seed,ticket)`, deduplicación con pesos, `scrub_pii`, trayectoria propia o la más frecuente de la intención); `replay`, `trajectory_match`, `ReleaseGate` (McNemar apareado o z de dos proporciones + caída de trayectoria + guardarraíles).
- **Estadística**: `two_proportion_test`, `mcnemar_exact`, `required_n_per_arm`, `min_detectable_drop`, `bootstrap_diff`; drift: `psi`, `psi_categorical`, `js_divergence`, `ks_2samp`, `Cusum`, `behavior_fingerprint`; canarios: `canary_route` (hash determinista), `sprt_bernoulli`, `peeking_false_positive_rate` (mirar 20 veces: ≈ 24 % de falsos positivos frente al 5 % nominal; SPRT ≈ 3 %).
- **Solo telemetría**: `trace_shapes(spans)` (una fila por traza: versión, nº `chat`/`execute_tool`, tokens de las hojas `chat`), `version_report(shapes, eval_events)`, `event_records(tel)`.
- Etiquetado: `gen_ai.agent.version` (invoke_agent), `gen_ai.prompt.name/version` (chat) con `VersionTagInstrumentor`. Dashboard `15-regresion-versiones.json` (uid `regresion-versiones`). Medido en vivo: calidad por versión en Prometheus v1 ≈ 0,98 / v2 ≈ 0,83 y la consulta TraceQL `span.gen_ai.agent.version = "v2" && span.supportops.tool_calls = 0` devuelve las trazas culpables.

### Módulo 16 · `supportops.slo` (numpy)
```python
from supportops.slo import DEFAULT_SLOS, GOOGLE_POLICIES, LAB_POLICIES, simulate_day, simulate_month, bin_events, burn_series, fire_series, alert_quality, grafana_burn_rule, rules_yaml, render_postmortem
day = simulate_day(42)            # 24 h de tráfico REAL del agente (≈ 1 s): rows por ticket, outage 10:00-10:45 (llm_error persistente) y regresión de prompt v2 6:00-14:00; day["truth"] = ventanas reales en minutos
g, t = bin_events(day["rows"], DEFAULT_SLOS["availability"], t0=day["t0"], n_bins=day["n_bins"])   # (buenos, totales) por minuto
fire = fire_series(g, t, 0.99, GOOGLE_POLICIES[0])      # burn(1 h) y burn(5 min) ≥ 14,4
```
- **SLOs de laboratorio** (`DEFAULT_SLOS`, medidos con `BASELINE_FAULTS`): disponibilidad 99 % (`ok|escalated`), latencia ≤ 5 s 97 %, calidad (groundedness, muestra uniforme 25 %) 95 %, coste ≤ 0,0005 USD 98 %. Políticas: `GOOGLE_POLICIES` = 14,4× (1 h/5 min, página), 6× (6 h/30 min, página), 1× (3 d/6 h, ticket) (SRE Workbook cap. 5); `LAB_POLICIES` = 14,4× (5 m/1 m) y 3× (15 m/3 m) para el stack en vivo.
- **PromQL** (`sli_promql`, `burn_promql`): `le` de Prometheus es `"5.0"`/`"0.0005"` (float repr). **Alertas provisionadas**: `stack/grafana/provisioning/alerting/16-slo-alerts.yaml` (8 reglas, grupo `supportops-slo`, `interval: 30s` —múltiplo de 10 s, `rules_yaml` lo exige—, `annotations.__dashboardUid__=slo-agente`, `__panelId__` = panel «Burn rate · <slo>» (ids 12-15), `runbook_url` a `16_slos_alertas_incidentes/runbooks/`), generado por `build_16.py`. Recarga: `POST /api/admin/provisioning/alerting/reload`; estado: `/api/prometheus/grafana/api/v1/rules` (estados `inactive|pending|firing`).
- **Medido con el stack real**: incidente de proveedor de 35 s a 5 tickets/s → `SLO availability · fast-burn` pasa a *firing* ≈ 55 s después del inicio y se apaga ≈ 80 s tras el fin; la de ticket (15 m) sigue activa más tiempo. Dashboard `16-slos.json` (uid `slo-agente`).
- Hallazgos de simulación: con 40 meses simulados el umbral fijo (5 min > 5 %) da ≈ 66 páginas/semana (≈ 99 % falsas); 1 h solo y multiventana ≈ 0,6/semana sin falsas, pero la multiventana queda disparada ≈ 10× menos minutos tras acabar el incidente. La regresión de calidad quema ≈ 4× (solo la política de ticket la ve).

## A7 · Módulos 17–19 (profiling, escala/muestreo/coste, Kubernetes/Helm) · `supportops.profiling`, `supportops.sampling`, `supportops.k8s`

Módulos nuevos y propios (no tocan `telemetry.py`/`agent.py`). Solo librería estándar (+ numpy opcional) salvo lo indicado. Para las secciones con el SDK de Pyroscope: `pip install pyroscope-io pyroscope-otel` (no están en los extras de `pyproject.toml`; los notebooks los instalan en su primera celda).

### Módulo 17 · `supportops.profiling` (Pyroscope 2.1.2; ver `17_profiling_pyroscope/README.md`)
```python
from supportops import profiling as P
prof = P.SamplingProfiler(hz=300, mode="cpu")                  # muestreador de pila a mano (wall|cpu), etiquetas por hilo: prof.set_tag/ prof.tag(k=v)
stats = P.run_workload("slow", n=60, profiler=prof)             # SupportOps con CPU real (HotPathInstrumentor): "slow" ≈ 38 ms CPU/ticket, "fast" ≈ 2 ms; extra=[OTelInstrumentor(tel)], scan_fn=/tokens_fn= (ganchos)
c = P.PyroscopeClient()                                         # PYROSCOPE_URL (def. http://localhost:4040)
c.push_connect({"service_name": "x", "variant": "slow"}, prof.to_pprof()); c.wait_for('{service_name="x"}'); P.self_time(c.stacks('{service_name="x"}'))
```
- **Medido con Pyroscope 2.1.2 real**: `push.v1.PusherService/Push` (JSON, `__name__=process_cpu`, `rawProfile` = pprof base64) y `POST /ingest?name=app{k=v}&format=pprof` con el pprof como cuerpo **crudo** (multipart → 422) funcionan; el pprof de `encode_pprof` (escrito a mano, sin protobuf) se acepta. Consultas Connect-RPC JSON: `SelectMergeStacktraces` (flamebearer → `flamebearer_to_stacks`), `SelectMergeSpanProfile` (`spanSelector`=span_ids), `SelectSeries`, `LabelNames/LabelValues`, `ProfileTypes`. Perfil de CPU: `process_cpu:cpu:nanoseconds:cpu:nanoseconds`. **`span_id` no aparece en `LabelNames`**: se consulta solo con `SelectMergeSpanProfile`. El SDK `pyroscope-io 1.3.0` nombra las funciones **sin módulo** (`scan_pii_slow`). Pyroscope tarda ≈ 60-90 s en estar *ready* (mensajes «Metastore/Segment Writer not ready») y unos segundos en hacer visible lo empujado (`wait_for`).
- **Traza ↔ perfil**: `pyroscope.otel.PyroscopeSpanProcessor` (paquete `pyroscope-otel 1.1.0`; añadir con `tel.tracer_provider.add_span_processor(...)`): en el span RAÍZ pone `pyroscope.profile.id=<span_id>` y etiquetas `span_id`, `span_name`, `trace_id` en las muestras. Datasource Tempo (`stack/grafana/provisioning/datasources/datasources.yaml`) ampliado con `tracesToProfiles` (cambio compatible). Dashboard `17-profiling.json` (uid `profiling`; paneles `flamegraph` y `timeseries` con datasource Pyroscope; consultas comprobadas con `/api/ds/query`).
- **GIL**: un muestreador en Python rinde ≈ 250-300 Hz efectivos con `switchinterval` 5 ms aunque pidas 1 000 Hz (0,5 ms → ≈ 950 Hz); sobrecarga medida dentro del ruido (≈ 0-6 %). Datos pregrabados: `17_profiling_pyroscope/recorded/capture_seed42.json.gz` (`P.load_recorded`). Pruebas: `supportops/tests/test_profiling.py` (14; las de Pyroscope se saltan si no está en :4040).
- **Hallazgo clave de la ruta caliente**: escaneo de PII 67 %, tokens ≈ 20 %, serialización ≈ 7 %, embeddings ≈ 5 %. Regex sola ≈ ×1,5-2 en total; caché por línea ≈ ×5-6; variante `fast` ≥ ×20. Convención para otros módulos: **etiqueta `run=<timestamp>` en los perfiles de un notebook** para no mezclar ejecuciones en Pyroscope.

### Módulo 18 · `supportops.sampling` (ver `18_escala_muestreo_coste/README.md`)
```python
from supportops import sampling as S
C = S.build_corpus(1500)                                         # trazas de SupportOps (mock, seed 42) con tamaño OTLP real; C.summary(), C.by_id()
pol = [S.StatusCode(("ERROR",), name="errors"), S.Latency(5000, name="slow"), S.AttrCompare(name="costly"), S.Probabilistic(10, name="baseline")]
res = S.TailSampler(pol, decision_wait_s=30, num_traces=50_000).run(C.traces)     # .kept, .dropped_too_early, .peak_traces, .peak_bytes, .by_policy
S.coverage(res.kept, C); S.head_sample(C.traces, 0.1); S.estimate_metrics(res.kept, S.inclusion_weights(res.kept, lambda t: t.interesting, 0.10))
cfg = S.collector_config(pol, decision_wait="30s", num_traces=50_000); S.validate_collector_config(cfg)     # otelcol-contrib validate (Docker)
with S.SamplingLab(cfg) as lab: lab.send(spans); lab.wait_settled(); lab.kept_trace_ids(); lab.internal(); lab.red_metrics()   # Collector real efímero
```
- **Políticas** (`Latency`, `StatusCode`, `NumericAttribute`, `AttrCompare` (ottl_condition), `StringAttribute`, `Probabilistic`, `SpanCount`, `RateLimiting`, `And`, `Drop`): mismas claves que el `tail_sampling` del Collector contrib 0.162.0 (`.to_config()`). Medido con el binario real: las políticas errors/slow/costly votan **igual** que el simulador (119/69/24 sobre 1 500 trazas); con `num_traces` insuficiente el Collector descarta sin decidir (1 300 de 1 500, igual que `TailSampler`).
- **Trampa verificada**: `numeric_attribute` es **int64**; un atributo *double* (`supportops.cost_usd`) con solo `min_value` hace caer el Collector 0.162.0 con SIGSEGV (`EvaluateWithThreshold`). `NumericAttribute.to_config()` rechaza decimales; usa `AttrCompare`.
- **Laboratorio de backends** (`BackendLab('loki'|'tempo'|'prometheus', config)`, `loki_lab_config(limits)`, `tempo_lab_config(overrides)`, `backends_experiment()`, `storm_experiment(n, bounded=)`): contenedores efímeros con puertos aleatorios (no necesitan el candado del stack). Medido: Loki `auth_enabled: true` → 401 sin `X-Scope-OrgID`, 429 «maximum active stream limit exceeded», 400 por etiquetas; Tempo `multitenancy_enabled: true`, `trace_too_large` descartado en silencio (`tempo_discarded_spans_total`); Loki `retention_enabled` exige `compactor.delete_request_store`; Prometheus v3.15 OTLP: ≈ 1-3 KB de RSS por serie (30 000 series → +84 MB).
- **Costes**: `StackCostModel.from_corpus(C, tickets_per_day, **supuestos)` y `retention_cost` (precios ILUSTRATIVOS). `rescale_rate(traces, factor)` comprime el tiempo (más tráfico, misma duración por traza). Datos pregrabados: `18_escala_muestreo_coste/recorded/capture_seed42.json.gz`; configuraciones validadas en `18_escala_muestreo_coste/configs/`; dashboard `18-escala-coste.json` (uid `escala-coste`). Pruebas: `supportops/tests/test_sampling.py` (17; las de Docker se saltan sin daemon).
- **Convención**: las métricas RED se calculan ANTES del muestreo (`span_metrics` en `traces/in` + `forward`); sin pesos el tail sampling infla la tasa de error ≈ 5× (2,6 % → 12 %).
