# Módulo 08 · Loki y LogQL: logs correlacionados con trazas

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
