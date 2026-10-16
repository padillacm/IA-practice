# Progreso: rev-tecnico-00-07
Agente: Revisor técnico R1 · Módulos: 00–07 · Informe: agent-observability-course/_tools/REVISION_TECNICA_1.md
- [x] 00_entorno
- [x] 01_agente_base
- [x] 02_tres_pilares
- [x] 03_otel_sdk_python
- [x] 04_genai_semconv
- [x] 05_collector
- [x] 06_autoinstrumentacion
- [x] 07_tempo_traceql
- [x] check_course.py OK + informe final

## Notas para retomar
- (qué archivo/celda, decisiones tomadas, comandos largos lanzados y su resultado)

- 00 revisado: cifras verificadas con ejecución; configs stack validadas (otelcol validate, tempo -config.verify=true, loki -verify-config, promtool, compose config: OK). dockerd arrancado por mí (/tmp/dockerd-r1.log), imágenes en caché.
- 01 revisado sin cambios necesarios (cifras y rúbricas re-ejecutadas OK).
- 02 revisado: cifras re-ejecutadas OK; URL de RED con fecha canónica.
- 03 revisado: corregida autoeval Q4 (fracción de huérfanos); rúbricas y claims SDK verificados con SDK 1.45.1. Snapshot GenAI verificado contra raw repo (registry/spans/metrics/docs): coincide. Fuente: raw.githubusercontent (model/gen-ai/*.yaml, docs/gen-ai/*.md) copiados a /tmp/semconv.
- 04 revisado: snapshot verificado 100% contra registry/spans/docs del repo oficial (79 atributos, 11 spans, 19 métricas); corregido 58%->50% ahorro caché; 'prohíbe'->'desaconseja (SHOULD NOT)' para conversation.id.
- 05 revisado: snapshot de componentes == 'otelcol components' 0.162 (exacto); labs reales ejecutados con docker (puertos aleatorios) OK; solución verificada con validate+funcional; corregida afirmación falsa de sufijo _total en métricas internas (en 0.162 sin _total). Pendiente: R11 (extremo a extremo con stack vivo) no ejecutado.
- 06 revisado: versiones/licencias/cadencia verificadas contra PyPI (exacto); Traceloop->ServiceNow y Datadog verificados por búsqueda web; cifras del dataset pregrabado re-calculadas; corregidos 3 números de la matriz (3,81/3,74; 57%) y 'de 0 a 9'. No verificado: comportamiento interno de openlit/traceloop (no instalados).
- 07 revisado: validado en vivo contra Tempo 3.1 (18/18 consultas == mini motor; proyecto R1-R6 OK con stack; dashboard 07 query_check OK); retirada cifra 2-2,5x no verificable. Informe en _tools/REVISION_TECNICA_1.md
