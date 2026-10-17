# Módulo 18 · Escala, muestreo y coste del propio stack

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
