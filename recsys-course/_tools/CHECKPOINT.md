# Checkpoint del curso (estado de construcción)

Última actualización: 2026-10-09. Rama: `claude/recommendation-systems-course-s08zlj`.

## Hecho
- Módulos **00–18**: lección + proyecto + README cada uno, generados por `_tools/builders/build_NN.py`. `check_course.py` → Todo OK.
- Módulo **19_elite_playbook** (masterclass de élite): lección (80 celdas) + proyecto *pager duty* (41 celdas). Borrador casi terminado; faltaba cerrar la sección 8 y las secciones finales de la lección, y probarlo con nbclient.
- `reference_stack/` reales en 16, 17 y 18 (docker-compose, FastAPI, Feast, Triton, Prometheus/Grafana, MLflow, Prefect/Airflow/Metaflow/KFP, Evidently, GitHub Actions).
- README del curso con mapa, temario, stack, datasets y presupuesto de Colab.

## En curso en el momento del checkpoint (agentes revisores)
- **Auditoría 00–09**: revisados y corregidos 00–06; pendientes **07, 08, 09**.
- **Auditoría 10–18**: casi terminada. Último paso: co-ocurrencia dispersa top-k en el capstone (18) para arreglar el OOM con ml-latest-small. Pendiente: añadir referencias con URL verificadas a las lecciones 16, 17 y 18.

## Pendiente para cerrar el curso
1. Terminar la auditoría de 07–09 y lo que quede de 10–18 (ver arriba).
2. Cerrar y probar el módulo 19.
3. Volver a ejecutar `python recsys-course/_tools/check_course.py` y regenerar todos los builders (`for f in recsys-course/_tools/builders/build_*.py; do python $f; done`).
4. Informe final al alumno, criterio por criterio (básico→experto, técnicas recientes, producción/monitoreo/reentreno, stack, gráficos, proyecto por sesión, datasets, contenido de élite).

## Limitaciones conocidas (validar en Colab)
- Desde el entorno de construcción, GroupLens y Hugging Face estaban bloqueados por el proxy. La mayoría de notebooks se probaron con *fallback* sintético; 03–05 sí se probaron con MovieLens-1M real (espejo de GitHub).
- No se han ejecutado los caminos con GPU (implicit-GPU, LLMs 7B/QLoRA, vLLM, TorchRec) ni llamadas reales a APIs de LLM.
- Umbrales de rúbricas ajustados en datos sintéticos en 07, 08, 12, 13, 16 y 18: pueden necesitar retoque con datos reales.
- Latencias p99 medidas en una máquina saturada: comprobar los SLO en Colab.
- Proyecto 05: objetivo BPR ≥ 0,17 sin verificar (con 3 trials de Optuna dio 0,13).
