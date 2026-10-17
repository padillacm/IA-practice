# Módulo 05 · El OpenTelemetry Collector

🟡 Intermedio · ≈ 4 h 30 min · **Docker** para los experimentos con el Collector real (contenedores efímeros con puertos aleatorios, **no** necesitan el stack). Sin Docker: modo degradado (resultados pregrabados y linter offline). Opcional `--profile core --profile metrics` para ver el stack real y el control extremo a extremo del proyecto.

> ⚠️ Verificado con `otel/opentelemetry-collector-contrib:0.162.0` (la imagen del stack). El Collector es `0.x`: nombres de componente y de opciones cambian; fija la versión.

## Qué aprenderás
- **Por qué** un Collector (patrones *sin Collector*, *agente*, *gateway*, *dos niveles*) y la anatomía de un *pipeline*: receivers, processors, exporters, connectors, extensions; fan-out síncrono e instancias por pipeline.
- El **orden recomendado de procesadores** (documentación oficial) demostrado con un Collector «de juguete» hecho a mano, y el efecto del fan-out bloqueante.
- La **configuración del stack, línea a línea**; `otelcol validate` frente a un **linter offline propio** (16 reglas) y siete configuraciones rotas a propósito.
- Experimentos con el **Collector real**: efecto de `batch`, PII/ruido/entorno con `attributes`/`filter`/`resource`, **`memory_limiter` (503 al SDK)** y **cola de envío** (llenado y rechazo hacia atrás), con las **métricas internas `otelcol_*`** y la conservación de spans.
- Resiliencia y escalado: colas, reintentos, cola persistente, `GOMEMLIMIT`, cuándo escalar (60-70 % de la cola) y cuándo no.

## Archivos
| Archivo | Contenido |
|---|---|
| `05_collector.ipynb` | Lección (teoría + código + 10 gráficos + autoevaluación) |
| `05_proyecto_collector.ipynb` | Proyecto: escribe tu gateway (PII, ruido, entorno, renombres GenAI, colas) hacia Tempo, Loki y Prometheus; rúbrica de 11 criterios (análisis estático, `validate`, comportamiento real y extremo a extremo) |
| `collector_components_0.162.0.json` | Componentes de la distribución contrib 0.162.0 y su estabilidad por señal (salida de `docker run --rm otel/opentelemetry-collector-contrib:0.162.0 components`); lo usa el linter |
| `lab_results_recorded.json` | Resultados pregrabados de los experimentos (modo degradado sin Docker). Se regeneran con `RECORD_LAB=1` al ejecutar la lección con Docker |

## Servicios necesarios
Docker (imagen del Collector ≈ 0,5 GB en disco). Stack `core` + `metrics` solo para el control R11 del proyecto y la conservación de spans de la lección.

## Lecturas
- OpenTelemetry, *Collector* (arquitectura, configuración, resiliencia, escalado, telemetría interna) — <https://opentelemetry.io/docs/collector/>
- OpenTelemetry Collector, *Processor README* (procesadores recomendados y orden) — <https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/README.md>
- OpenTelemetry Collector, *exporterhelper* (cola de envío, reintentos, batching) — <https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md>
- Prometheus, *Using Prometheus as your OpenTelemetry backend* — <https://prometheus.io/docs/guides/opentelemetry/>

## Siguiente
`06_autoinstrumentacion`: OpenLIT y OpenLLMetry frente a la instrumentación manual de los módulos 03-04.
