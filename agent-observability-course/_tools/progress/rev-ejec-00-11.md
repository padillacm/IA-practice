# Progreso: rev-ejec-00-11
Agente: Revisor de ejecutabilidad E1 · Módulos: 00–11 · Informe: agent-observability-course/_tools/REVISION_EJECUTABILIDAD_1.md
- [x] 00_entorno
- [x] 01_agente_base
- [x] 02_tres_pilares
- [x] 03_otel_sdk_python
- [x] 04_genai_semconv
- [x] 05_collector
- [x] 06_autoinstrumentacion
- [x] 07_tempo_traceql
- [x] 08_loki_logql
- [x] 09_metricas
- [x] 10_grafana
- [x] 11_multiagente
- [x] check_course.py OK + informe final

## Notas para retomar
- Entorno de trabajo (scratchpad ... /scratchpad/ej): venv (extras completos), venv2 (solo ipykernel+nbclient, "limpio"), repo/ y repo2/ = copias de archivos versionados (sin data/). Scripts: run.sh NN tag, batch_deg.sh, stack_pass.sh (flock+compose core+metrics+TEMPO_CONFIG=tempo-metrics.yaml+down -v), cmp.py, rub.py.
- RESULTADOS (FAST_DEV_RUN=True, 4 CPU): sin stack x2 (deg1/deg2, STACK_HOST=nohost.invalid) módulos 00-11: 0 celdas con error (fuera de TODO), rúbrica de la solución todo OK (00: 4 «no evaluable», 05: 1), salidas idénticas entre las 2 ejecuciones salvo ids aleatorios/tiempos medidos. Con stack (st1 todos; st2 00,03,05,07,08,09,10,11): 0 errores, rúbricas todo OK, nada «no evaluable».
- Tiempos con stack: 00 19+8 s · 03 12+5 · 05 39+50 · 07 41+56 · 08 20+6 · 09 157+88 · 10 202+5 · 11 26+6 (lección+proyecto). RAM stack core+metrics bajo carga: grafana 300, tempo 186, loki 97, prom 70, collector 68 MiB.
- HALLAZGO 1: boot cell (pip install -e) en venv limpio -> `import supportops` falla en la celda siguiente (kernel no ve el editable recién instalado). Arreglo: sys.path.insert(ROOT)+invalidate_caches en BOOT de _a1_common.py (afecta a TODOS los builders; regenerar 00-11 hecho por mí, 12-22 por el otro revisor).

- Venv limpio (venv3, solo ipykernel+nbclient+nbformat): 00-11 ejecutan sin errores tras el arreglo de BOOT (cl2). Pendiente: st3 (core solo + tempo.yaml por defecto: 03,05,07,08), informe, nota al otro revisor.
- st3 (core + tempo.yaml por defecto: 03,05,07,08): sin errores, rúbricas OK. Informe REVISION_EJECUTABILIDAD_1.md escrito. Tarea terminada.
