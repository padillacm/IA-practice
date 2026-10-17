# Módulo 02 · Los tres pilares: traces, metrics y logs

🟢 Básico · ≈ 4 h 30 min · **No necesita servicios de Compose** (datos simulados y pregrabados; funciona en Colab).

## Qué aprenderás
- Qué pregunta responde cada señal (logs: *qué pasó*, métricas: *cuánto*, trazas: *dónde y por qué*) y por qué un agente necesita las tres; analogías con ML, microservicios y SRE.
- Contador, *gauge* e **histograma construidos a mano** (con salida en formato Prometheus) y el error al estimar percentiles desde *buckets*.
- El **modelo de datos de OpenTelemetry**: resource, instrumentation scope, span (kind, status, atributos, eventos, links), log record, temporalidad de métricas; **propagación de contexto** con W3C `traceparent` (implementada a mano) y qué pasa cuando se rompe.
- **Correlación**: métrica → exemplar → traza → logs.
- *Golden signals* (y RED/USE) aplicadas a agentes: latencia, tráfico, errores, saturación **más** tokens/coste, pasos y calidad.
- Percentiles que no se promedian, **cardinalidad** de métricas y la hipótesis de «qué señal detecta qué fallo».

## Archivos
| Archivo | Contenido |
|---|---|
| `02_tres_pilares.ipynb` | Lección (teoría + código + 11 gráficos + autoevaluación) |
| `02_proyecto_tres_pilares.ipynb` | Proyecto: mide y clasifica **10 incidentes** de SupportOps (qué señal salta, qué señal es ciega, diagnóstico) |

## Servicios necesarios
Ninguno.

## Lecturas
- OpenTelemetry, especificación (modelos de datos de trazas, métricas y logs) — <https://github.com/open-telemetry/opentelemetry-specification>
- W3C, *Trace Context* — <https://www.w3.org/TR/trace-context/>
- Google SRE book, cap. 6 *Monitoring Distributed Systems* — <https://sre.google/sre-book/monitoring-distributed-systems/>
- Sigelman et al., *Dapper* (2010) — <https://research.google/pubs/pub36356/>

## Siguiente
`03_otel_sdk_python`: producirás estas señales con el SDK de OpenTelemetry (TracerProvider, spans, contexto y exportador OTLP).
