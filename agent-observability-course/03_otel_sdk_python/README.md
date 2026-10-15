# Módulo 03 · El SDK de OpenTelemetry para Python

🟡 Intermedio · ≈ 4 h 30 min · **Servicios opcionales:** `docker compose --profile core up -d` (Collector + Tempo + Loki, ≈ 0,4 GB en reposo). Sin Docker funciona en **modo degradado** (telemetría en memoria).

## Qué aprenderás
- La separación **API / SDK** y el camino de un span: *Sampler → Span → SpanProcessor → Exporter → OTLP*.
- Un **tracer construido a mano** (ids, `contextvars`, tiempos, estado) y un exportador **OTLP/JSON** casero, para entender qué hace el SDK por debajo.
- `TracerProvider`, `Resource`, spans con atributos, eventos, *links*, estado y excepciones; `SpanKind`; límites del SDK (128 atributos/eventos).
- **Contexto y propagación W3C** (`traceparent`, `inject`/`extract`) entre servicios HTTP reales, y qué se rompe con hilos o cabeceras mal normalizadas.
- `SimpleSpanProcessor` frente a `BatchSpanProcessor`: capacidad, cola, **pérdida de spans** medida; *head sampling* y por qué el sampler solo ve los atributos del momento de crear el span.
- El exportador **OTLP/HTTP** hacia el Collector, variables de entorno `OTEL_*` y verificación de la traza en **Tempo**.
- **SupportOps v1**: instrumentación manual de `invoke_agent` → `chat` → `execute_tool`, logs correlacionados con `trace_id`, y el **coste medido** de instrumentar.

## Archivos
| Archivo | Contenido |
|---|---|
| `03_otel_sdk_python.ipynb` | Lección (teoría + código + 10 gráficos + autoevaluación) |
| `03_proyecto_otel_sdk_python.ipynb` | Proyecto: instrumenta a mano SupportOps v0 (9 TODO), rúbrica de 10 criterios medibles y retos de nivel experto |

## Código de referencia: `supportops.telemetry`
Este módulo enseña a construir la instrumentación a mano; `agent-observability-course/supportops/telemetry.py` es la **versión consolidada** que reutilizan los módulos siguientes:

```python
from supportops.telemetry import setup_telemetry, OTelInstrumentor
tel = setup_telemetry("supportops-agent")                 # OTLP/HTTP a localhost:4318; sin Collector → memoria (aviso)
agent = SupportAgent(instrumentor=OTelInstrumentor(tel))  # spans GenAI + métricas mínimas + logs con trace_id/span_id
...
tel.force_flush(); tel.shutdown()
```
API completa y qué se ve en cada backend: `_tools/INTERFACES.md`, sección 4.

## Servicios necesarios
`core` (Collector, Tempo, Loki) **solo** para los pasos «ver la traza en Tempo/Loki». Todo lo demás (incluida la rúbrica) corre en memoria.

## Lecturas
- OpenTelemetry, *Instrumentation*, *Exporters* y *Propagation* para Python — <https://opentelemetry.io/docs/languages/python/>
- OpenTelemetry Specification, *Trace API* y *Trace SDK* — <https://github.com/open-telemetry/opentelemetry-specification/tree/main/specification/trace>
- W3C, *Trace Context* — <https://www.w3.org/TR/trace-context/>
- OpenTelemetry, *Zero-code Python · Troubleshooting* (servidores pre-fork) — <https://opentelemetry.io/docs/zero-code/python/troubleshooting/>

## Siguiente
`04_genai_semconv`: estandarizar los nombres de atributo de tus spans con las *GenAI semantic conventions* y validarlos con un linter propio.
