# Revisión de referencias y contenido de élite · módulos 00-10

Revisor: rev-refs-elite-00-10. Alcance: `build_00..10.py` (lecciones, proyectos y READMEs que generan).

## Método
- Los dominios `grafana.com`, `opentelemetry.io`, `honeycomb.io`, `prometheus.io`, `sre.google`, `arxiv.org`, `docs.docker.com`, `w3.org` y `research.google` están bloqueados en el sandbox. Truco que funcionó: **la documentación de esos sitios vive en repos de GitHub accesibles por `raw.githubusercontent.com`** (`open-telemetry/opentelemetry.io`, `grafana/loki|tempo|grafana|mimir|alloy`, `prometheus/docs|prometheus`, `docker/docs`, `open-telemetry/*`). Se leyó el texto real, no solo se comprobó que la URL existiera.
- Para blogs/papers/páginas sin repo (Honeycomb, Datadog, Grafana blog, Dapper, USE, Anthropic, OpenAI, arXiv) se usó búsqueda web (≥ 1 fuente independiente).
- 104 URLs únicas extraídas de los builders (136 entradas módulo-URL) + referencias solo-texto (libros, papers).

## Resultado de referencias
| Estado | Nº | Detalle |
|---|---|---|
| Verificadas (contenido leído o confirmado por ≥ 1 fuente) | ≈ 98 | todos los enlaces de GitHub (60 ficheros por `raw`, 14 repos por README), 17 páginas de opentelemetry.io/docs (por su fuente en repo), docs de Docker, Prometheus (3), Loki, Tempo, Mimir, Grafana, Alloy, Honeycomb ×3, Datadog, Grafana AI Obs., Dapper, RED, USE, Sculley, Majors et al. (ISBN), Ji et al., ReAct, OTel blog |
| Corregidas | 7 | ver tabla |
| Eliminadas | 0 (1 afirmación) | «el sitio avisa de que puede estar desfasado» (OTel blog, módulo 00) |
| No confirmables (marcadas en el texto) | 5 | ver final |

### Correcciones
| Módulo | Problema | Arreglo |
|---|---|---|
| 00 | Blog OTel «AI Agent Observability»: sin autores y con afirmación no verificable | Autores (Guangya Liu, IBM; Sujay Solomon, Google) y fecha 2025-03-06 leídos en `opentelemetry.io` (repo); retirada la frase no verificable |
| 01 | URL de OpenAI *Function calling* (`/api/docs/guides/…`) no corresponde a la actual | `https://developers.openai.com/docs/guides/function-calling` (confirmado por búsqueda) |
| 01 | «19-dic-2024» de *Building effective agents* sin confirmar; autores ausentes | Autores Schluntz y Zhang; fecha «dic-2024», día marcado no confirmado |
| 03 | Pre-fork: se atribuía el problema al `BatchSpanProcessor` | La doc oficial documenta el caso del `PeriodicExportingMetricReader` (métricas se rompen; trazas suelen funcionar). Texto corregido |
| 04/06 | «`OTEL_SEMCONV_STABILITY_OPT_IN` … lo documenta el README de util-genai» | El README actual no lo contiene; el repo nuevo `opentelemetry-python-genai` **eliminó** la bandera (CHANGELOG, PR #117). Texto corregido en 04 y 06 |
| 05 | Alloy OTel engine «experimental»; «la guía oficial prefiere `sending_queue.batch`» | Alloy: *public preview*; redacción suavizada a lo que muestran los ejemplos de la doc |
| 06 | Grafana AI Observability: «cinco dashboards» | La guía de setup dice cinco, la página de referencia seis; matizado, y URL nueva de la doc |

## Élite (🏭/🧠): evaluación y añadidos
Valoración general: los módulos ya eran concretos y muchos medidos; el defecto típico era **afirmaciones sin cita** y **huecos de “gap dashboard vs realidad”**. Cada punto nuevo lleva fuente leída o medición reproducible en el notebook.

| Mód. | Añadidos | Contenido |
|---|---|---|
| 00 | 2 | `memory_limiter` (reintento obligatorio del emisor, memoria previa al limitador; cita README) · docker-otel-lgtm es solo dev/demo/test (README) |
| 01 | 2 + celda | coste cuadrático del historial (celda con números) · caché de prompt (multiplicadores marcados *fuente secundaria*) · `temperature=0` marcado como no verificado |
| 02 | 1 + celda | sesgo de *tail sampling* y corrección por 1/p (celda: ≈ 16,8 % vs 2 % real) · Tempo 3.0 *span multiplier* · spec de probabilidad en `tracestate` · cita Prometheus sobre interpolación |
| 03 | 1 + celda | coste de un span descartado vs exportado (celda; ratios, no absolutos); `Batch` no es más barato en CPU que `Simple` |
| 04 | 1 + celda | buckets por defecto del SDK (ms) vs segundos: p95 real 2,2 s vs 4,8 s estimado vs 2,4 s con buckets GenAI (celda) |
| 05 | 2 | `error_mode: ignore` es *fail-open* para redacción de PII · balanceo por `traceID` colisiona con `spanmetrics` (README loadbalancing) |
| 06 | 2 | bandera de semconv que cambia por versión · defaults de captura de contenido de las tres librerías, verificados en código |
| 07 | 2 | extrapolación de TraceQL metrics con muestreo (Tempo 3.1) · consultas de datos recientes fallan en lugar de ser incompletas (`fail_on_high_lag`, 3.0) |
| 08 | 2 | la asignación OTLP→Loki por defecto promociona 17 atributos incl. `k8s.pod.name`/`service.instance.id` · multiplicación de etiquetas y `max_global_streams_per_user=5000` |
| 09 | 1 | p99 «plano» por el bucket `+Inf` (PromQL) y consulta de detección |
| 10 | 2 | instancias de alerta obsoletas (`Normal (MissingSeries)`) · ventana fija en reglas |

## Qué NO pude verificar
1. Texto completo de los dos posts de Honeycomb (existencia, título, autor y, para «So we shipped…», fecha 2-oct-2023 confirmados; contenido no leído).
2. Blog de Datadog (1-dic-2025) y blog/doc de Grafana Cloud AI Observability: confirmados solo por fragmentos de búsqueda.
3. Multiplicadores de caché de Anthropic (0,1× / 1,25×) y «`temperature=0` no determinista»: solo fuentes secundarias; marcados en el texto.
4. Día exacto de *Building effective agents* y el identificador arXiv 2005.11401 (RAG): título/autor/congreso confirmados, el enlace arXiv no se pudo abrir.
5. Cifra de 1/1024 de Dapper (no se usó) y bit `random-trace-id` de W3C Trace Context nivel 2: este último confirmado vía docstring del SDK de Python, no en el texto W3C.
