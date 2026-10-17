# Checkpoint del curso (estado de construcción)

Última actualización: 2026-10-09. Rama: `claude/recommendation-systems-course-s08zlj`.

## Estado: COMPLETO (v1)
- Módulos **00–19**: lección + proyecto + README, generados por `_tools/builders/build_NN.py`; `check_course.py` → Todo OK.
- Auditoría técnica y pedagógica de 00–18 terminada (ver `_tools/progress/audit_00_09.md` y `audit_10_18.md`); módulo 19 terminado (`_tools/progress/module_19.md`).
- Cargadores de MovieLens con cadena GroupLens → espejo GitHub → sintético.

## Pendiente (validación en Colab, no bloqueante)
- Ejecutar en Colab con GPU y datos reales: caminos GPU (implicit-GPU, LLMs 7B/QLoRA, vLLM), datasets HF/Kaggle/Zenodo (Criteo, KuaiRand, Amazon 2023, RetailRocket).
- Re-ejecutar con nbclient: lección 03, notebooks 07–09, lecciones/proyectos 10–13 y proyecto 15.
- Proyecto 08: medir Recall@100 vs popularidad con ML-1M real y fijar el umbral.
- Proyecto 05: confirmar BPR ≥ 0,17 con 8+ trials de Optuna en GPU.
- Levantar los `docker-compose` de 16–18 con Docker real (solo se validó el YAML).
- Latencias p99: comprobar SLO en Colab (medidas locales en máquina saturada).
