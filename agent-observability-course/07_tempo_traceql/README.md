# Módulo 07 · Tempo y TraceQL: consultar las trazas

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
