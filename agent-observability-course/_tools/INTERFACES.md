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

## 3. Qué se probó y qué no (autor A1)
- Probado con Docker real (daemon 29.8, imágenes descargadas del registro): `docker compose config`; `otelcol validate`, `promtool check config`, `loki -verify-config`; arranque de los 6 servicios; telemetría OTLP/HTTP real (trazas+logs+métricas) → Tempo (`/api/search` TraceQL), Loki (`query_range`, `trace_id` como structured metadata), Prometheus (`smoke_requests_total` vía `:8889`), salud de los 4 datasources en Grafana, dashboard `stack-overview` aprovisionado, `tempo-metrics.yaml` (aparecen `traces_spanmetrics_calls_total`, `_latency_bucket`…), `check_stack()` y `backends.*` contra el stack vivo.
- **No** probado: adaptadores `anthropic|openai|ollama` contra servidores reales (solo clientes falsos); `tempo-metrics.yaml` en ejecución prolongada (sí se comprobó que genera `traces_spanmetrics_*` en Prometheus); arm64; Windows/WSL; renderizado visual del dashboard en un navegador (se validaron sus consultas contra Prometheus).
