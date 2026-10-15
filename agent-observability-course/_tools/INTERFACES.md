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
