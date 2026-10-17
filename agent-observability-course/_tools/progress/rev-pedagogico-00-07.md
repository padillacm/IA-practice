# Progreso: rev-pedagogico-00-07
Agente: Revisor pedagógico P1 · Módulos: 00–07 · Informe: agent-observability-course/_tools/REVISION_PEDAGOGICA_1.md
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
- (qué archivo/celda, decisiones tomadas)

- 00: añadido glosario mínimo, predicción antes de grieta 4, pregunta 8 (Grafana cae), títulos de cajas élite arreglados (00-02). Aún no regenerados 01/02 (títulos élite editados en builders).
- Herramientas en scratchpad: dump.py (volcado de notebook), commit.sh
- 01: conexión con 00 reescrita (diagnóstico/transferencia), 🧭 ruta núcleo, ejemplo a mano de tokens antes de fórmula, ejemplo resuelto de Rule en proyecto (antes no se enseñaba), autoeval +2 preguntas.
- 02: conexión 00/01 reescrita a diagnóstico/cálculo; predicción §6; autoeval +2 (correlación, resource/scope/atributo); proyecto: plan TODO3, predicción TODO4, 👀 tras viz de la solución. Proyecto ejecutado OK con nbclient (sin errores, rúbrica).
- runnb.py (scratchpad) ejecuta un notebook con nbclient.
- 03: conexión aplicada, 🧭 ruta núcleo, predicción cola Batch, autoeval +2 (endpoint OTLP, coste CPU), 👀 en proyecto tras la cascada. Solo markdown cambiado (sin re-ejecutar).
- 04: conexión aplicada (sampler, kind, doble conteo), ejemplo a mano (span con 3 desviaciones, verificado con el linter real) antes de la tabla de reglas, autoeval +1 (spec vigente), Pista 3 en TODO migrate. Solo markdown.
- 05: conexión Q1 como cálculo, gloss DaemonSet/sidecar, predicción 4.4, autoeval +1 (conservación), plan en 3 iteraciones en TODO 1. Solo markdown (el builder re-verificó la solución con Docker: OK).
- 06: conexión con predicción/transferencia, 🧭 ruta núcleo (74 celdas), predicción antes de exp. 1, autoeval +1 (cálculo matriz) y etiquetas, 2 pistas en TODO 6a/6b. Solo markdown.
- 07: conexión aplicada (4), ejemplo a mano de 4 spans, predicción 2.2, 🧭 ruta núcleo, autoeval +2 (ajuste de consulta, manual de diagnóstico), proyecto: ejemplo resuelto Q0, pistas METRICS, 👀 timeline. Consultas verificadas con traceql_mini; proyecto ejecutado con nbclient OK.
- Pendiente: informe REVISION_PEDAGOGICA_1.md + check_course.py
- Informe escrito: _tools/REVISION_PEDAGOGICA_1.md; check_course.py: Todo OK.
