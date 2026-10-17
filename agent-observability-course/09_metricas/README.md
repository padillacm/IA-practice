# Módulo 09 · Métricas: Prometheus/Mimir, instrumentos OpenTelemetry, RED + GenAI y exemplars

🟡 Intermedio · ≈ 4 h 30 min · Servicios: `core` + `metrics` (`docker compose --profile core --profile metrics up -d`, ≈ 0,45 GB). Funciona **sin Docker en modo degradado** (la parte con Prometheus se salta y se explica).

## Qué aprenderás
- El modelo de Prometheus y las **tres rutas** de las métricas OTel hasta Grafana (Collector → *scrape*, OTLP directo, Mimir).
- `rate()` y `histogram_quantile()` **implementados a mano** y comprobados contra un Prometheus real.
- Los instrumentos OTel (*Counter, UpDownCounter, Histogram, Gauge, Observable\**), las *views*, y **cumulative frente a delta** (y por qué Prometheus rechaza delta).
- **Nombres en Prometheus**: sufijos de unidad y tipo, `target_info`, `job`/`instance`.
- **RED + métricas GenAI** de SupportOps (duración, tokens, coste, pasos) con la spec GenAI actual (estado *Development*), conciliadas con la verdad del agente; **coste con una tabla de precios ilustrativa**.
- **Exemplars** de extremo a extremo: del rombo de Grafana a la traza en Tempo.
- **Cardinalidad** (series = ∏ valores × (B+3)), el SDK de Python **sin límite** y presupuestos de series.
- **Histogramas clásicos frente a exponenciales/nativos** y por qué el Collector del curso no los transporta; qué cambia con Mimir.

## Archivos
| Archivo | Contenido |
|---|---|
| `09_metricas.ipynb` | Lección (≥ 12 gráficos, experimentos en vivo, 🧠 de élite, autoevaluación con cálculo/diagnóstico/transferencia) |
| `09_proyecto_metricas.ipynb` | Proyecto: construyes el `Recorder` de métricas (coste, buckets, instrumentos, cardinalidad, PromQL) con rúbrica R1-R7 (+ L1-L3 en vivo) |
| `img/09_dashboard.png` | Captura real del dashboard provisionado `09-genai-metrics` |
| `../supportops/otel_metrics.py` | `MetricsInstrumentor`, `PriceTable`, `run_live`, clientes de la API de Prometheus (lo reutilizan los módulos 10, 13, 16 y 18) |
| `../stack/grafana/dashboards/09-genai-metrics.json` | Dashboard aprovisionado (generado con `supportops/dashkit.py`) |

## Servicios necesarios
`core` + `metrics`. Sin ellos, los notebooks siguen funcionando en memoria (`InMemoryMetricReader`) y la rúbrica base del proyecto se completa.

## Lecturas
- OpenTelemetry, *Metrics SDK* (cardinality limits, views, exemplars) — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md>
- OpenTelemetry, *Prometheus and OpenMetrics Compatibility* — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/compatibility/prometheus_and_openmetrics.md>
- OpenTelemetry, *Semantic conventions for GenAI* (repo `semantic-conventions-genai`) — <https://github.com/open-telemetry/semantic-conventions-genai>
- Prometheus, *Using Prometheus as your OpenTelemetry backend* — <https://github.com/prometheus/docs/blob/main/docs/guides/opentelemetry.md>
- Prometheus, *Histograms and summaries* — <https://github.com/prometheus/docs/blob/main/docs/practices/histograms.md>
- Grafana Mimir, *Configure native histograms* — <https://github.com/grafana/mimir/blob/main/docs/sources/mimir/configure/configure-native-histograms-ingestion.md>
- Beyer et al., *Site Reliability Engineering*, cap. 6 — <https://sre.google/sre-book/monitoring-distributed-systems/>

## Siguiente
`10_grafana`: llevarás estas métricas a **dashboards como código**, con variables, paneles de trazas/logs/métricas, navegación entre señales (trace → logs → metrics) y alertas aprovisionadas.
