# Revisión técnica R1 · módulos 00-07

Revisor: rev-tecnico-00-07. Alcance: builders `build_00..07.py` y sus notebooks, más lectura de `stack/` y `supportops/` compartidos (sin cambios en ellos).

## Método
- Re-ejecución de las lecciones y proyectos con `nbclient` (modo degradado) y, para 00, 03, 05 y 07, también con el stack vivo (Collector 0.162.0, Tempo 3.1.0 con `tempo-metrics.yaml`, Loki 3.7.8, Prometheus 3.15.0, Grafana 13.2.4) bajo el candado `/tmp/obs-stack.lock`.
- Configuraciones del stack validadas con las herramientas oficiales: `docker compose config`, `otelcol validate`, `tempo -config.verify=true` (estricto: rechaza claves desconocidas), `loki -verify-config`, `promtool check config`. Todas OK.
- Snapshot GenAI (`04_genai_semconv/genai_semconv_snapshot.json`) contrastado de forma automática con `model/gen-ai/{registry,spans,metrics}.yaml` y `docs/gen-ai/*.md` de `open-telemetry/semantic-conventions-genai` (raw.githubusercontent): 79/79 atributos (tipo y estabilidad), 11 tipos de span, 19 métricas y enum de `finish_reason` coinciden.
- Snapshot de componentes del Collector (`05_collector/collector_components_0.162.0.json`) == `otelcol-contrib components` de la imagen 0.162.0 (107/33/48/13/41 componentes).
- Versiones, licencias y cadencia de publicación del módulo 06 contrastadas con la API JSON de PyPI (exactas). Traceloop→ServiceNow y soporte GenAI de Datadog verificados con búsqueda web. Notas de Tempo 3.0/3.1 (RF1, TraceQL metrics GA, vParquet5, redaction por consulta) verificadas con búsqueda web; `query_backend_after: 15m` y `vParquet5` verificados en `/status/config?mode=defaults` de Tempo 3.1.

## Problemas encontrados y corregidos (builders regenerados)
| Módulo | Problema | Arreglo |
|---|---|---|
| 00 | Afirmación sin respaldo: «Grafana 13 solo permite acceso anónimo como Viewer» | Reformulada: el acceso anónimo está desactivado en el compose |
| 02 | URL de Grafana (RED method) sin fecha canónica | Se usa la URL con fecha |
| 03 | Autoevaluación Q4: «B conserva el 50 % de lo que A descartó» (incorrecto: es ≈ 40 % del total, umbrales anidados) | Corregida |
| 04 | Cálculo erróneo: la caché «rebaja ≈ 58 %» (el ejemplo da 85/170 = 50 %) | Corregido |
| 04 | «La spec prohíbe» inventar `gen_ai.conversation.id`: el texto de la spec es SHOULD NOT | Reformulado (4 sitios) |
| 05 | Afirmación falsa: «los contadores internos llevan sufijo `_total`» (en 0.162 con el lector `pull` del stack NO lo llevan; los dashboards ya usan los nombres sin sufijo) | Corregida en 2 sitios |
| 06 | Cifras de la matriz: 3,82/3,75 → 3,81/3,74; «≈ 58 %» → «≈ 57 %»; «de 1 a 9 versiones/mes» → «de 0 a 9» | Corregidas con los valores recalculados |
| 07 | «2-2,5× de datos duplicados» atribuido a las notas de 3.0 (no verificable) | Sustituido por lo verificado (una copia en vez de tres) |

Sin hallazgos en 01 (cifras y rúbricas re-ejecutadas OK).

## Recomendaciones / pendientes (no aplicadas)
1. `supportops/otel_metrics.py` y `telemetry.py` emiten `gen_ai.client.inference.usage.*` (correcto con la spec actual en `gen-ai-token-metrics.md`), pero el módulo 04 lo presenta como "tres cambios de nombre" sin enlazar ese documento; añadir el enlace.
2. Los datos pregrabados de `sample_data` (módulo 01-02) llevan `gen_ai.provider.name` en `invoke_agent` y `finish_reasons=['tool_calls']`; el linter del módulo 04 los marca (SCOPE/FINISH) y la lección lo usa pedagógicamente. Conviene regenerarlos con el instrumentor actual si se quiere un ejemplo "limpio".
3. Rúbrica 06 R6 y matriz: los pesos y las puntuaciones cualitativas son juicios del autor (documentado); no hay riesgo técnico pero no son mediciones.
4. `00_entorno` usa mediciones de RAM/imagen/arranque "de una máquina de referencia" que no se pueden verificar aquí (sí son coherentes: 437 MiB en reposo, 3,4 GB de imágenes).
5. Si Tempo cambia los nombres de métricas o `most_recent` deja de ser experimental, revisar 07 §4.1 y §5.

## No verificado
- Comportamiento interno de `openlit` y `traceloop-sdk` (no instalados; se confía en el dataset pregrabado y en las cifras re-calculadas).
- Páginas de grafana.com, opentelemetry.io, honeycomb.io, docs.honeycomb.io (no accesibles); URLs de esos dominios sin comprobar una a una.
- Adaptadores LLM reales (anthropic/openai/ollama) del módulo 01: solo formato de mensajes.
- Pyroscope y paneles de dashboards 08-22 (fuera de rango).
