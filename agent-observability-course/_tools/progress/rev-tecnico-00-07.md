# Progreso: rev-tecnico-00-07
Agente: Revisor técnico R1 · Módulos: 00–07 · Informe: agent-observability-course/_tools/REVISION_TECNICA_1.md
- [x] 00_entorno
- [x] 01_agente_base
- [x] 02_tres_pilares
- [x] 03_otel_sdk_python
- [ ] 04_genai_semconv
- [ ] 05_collector
- [ ] 06_autoinstrumentacion
- [ ] 07_tempo_traceql
- [ ] check_course.py OK + informe final

## Notas para retomar
- (qué archivo/celda, decisiones tomadas, comandos largos lanzados y su resultado)

- 00 revisado: cifras verificadas con ejecución; configs stack validadas (otelcol validate, tempo -config.verify=true, loki -verify-config, promtool, compose config: OK). dockerd arrancado por mí (/tmp/dockerd-r1.log), imágenes en caché.
- 01 revisado sin cambios necesarios (cifras y rúbricas re-ejecutadas OK).
- 02 revisado: cifras re-ejecutadas OK; URL de RED con fecha canónica.
- 03 revisado: corregida autoeval Q4 (fracción de huérfanos); rúbricas y claims SDK verificados con SDK 1.45.1. Snapshot GenAI verificado contra raw repo (registry/spans/metrics/docs): coincide. Fuente: raw.githubusercontent (model/gen-ai/*.yaml, docs/gen-ai/*.md) copiados a /tmp/semconv.
