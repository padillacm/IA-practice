# Módulo 17 · MLOps para recomendadores: tracking, orquestación, monitoreo y reentreno

**Nivel:** 🔴 Experto · **Duración:** 5–6 h (lección) + 4–6 h (proyecto) · **GPU:** no necesaria · **Unidades Colab:** 1–3 (`SCALE="full"` con ML-25M ≈ 3–5)

**Prerrequisitos:** 02 (evaluación), 05 (ALS), 13 (feedback loops), 15 (A/B), 16 (serving).

## Resumen
Un recomendador se degrada solo: entran títulos que el modelo no conoce (*catalog drift*), cambian los gustos y el
propio sistema sesga sus datos (*feedback loops*). Usando 20+ años de MovieLens como «producción» simulada, medimos
**cuánto cae el NDCG@10 sin reentreno** y comparamos estrategias (estático, programado, ventana deslizante, warm-start,
por trigger de drift). Montamos el ciclo completo: **MLflow** (tracking, registry, aliases `champion`/`challenger`,
rollback), **Pandera** (validación de lotes), **Evidently** (data/prediction drift) + embedding drift propio
(clasificador de dominio, MMD), **Prefect** (flow de entrenamiento continuo ejecutable en Colab), alertas de negocio con
estacionalidad, simulación de feedback loops, canary con guardrails y tests de modelo para CI/CD/CT.

## Objetivos
1. MLflow: tracking, registry y despliegue por alias (champion/challenger, rollback).
2. Orquestar CT con Prefect y saber traducirlo a Airflow / Kubeflow / Metaflow.
3. Validar datos con Pandera / Great Expectations.
4. Medir data, prediction, catalog y embedding drift (Evidently + implementaciones propias).
5. Cuantificar la degradación temporal y elegir una política de reentreno con evidencia.
6. Diseñar alertas de negocio, simular feedback loops y desplegar con shadow/canary/rollback.

## Contenido
| Archivo | Qué es |
|---|---|
| `17_mlops_monitoring.ipynb` | Lección completa (≥ 10 gráficos: degradación de NDCG con/sin reentreno, drift por año, Evidently, embedding drift, alertas, feedback loop, canary, registry) |
| `17_proyecto_pipeline_ct.ipynb` | Proyecto: pipeline CT con MLflow + Prefect + Evidently, trigger por drift relativo a la línea base, simulacro de incidente y rollback (rúbrica + solución) |
| `reference_stack/` | Stack real: `docker-compose.yml` (MLflow + Postgres + MinIO, Prefect server/runner, Evidently UI, Prometheus + Pushgateway + Alertmanager, Grafana), flow de Prefect con cron, DAG de Airflow, flow de Metaflow, pipeline de Kubeflow (KFP v2), esquemas Pandera/GX, job de drift → Pushgateway, alertas de modelo y negocio, dashboard Grafana, workflow de GitHub Actions CI/CD/CT |

### Cómo usar `reference_stack/`
```bash
cd reference_stack
docker compose up -d --build        # MLflow :5000 · Prefect :4200 · Evidently :8085 · Grafana :3000 · Prometheus :9090
# Los flows esperan particiones diarias en ./data/events/date=YYYY-MM-DD (parquet)
```

## Datasets
- **MovieLens latest-small** (100 836 valoraciones, 1996–2018): https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
- **MovieLens-25M** (`SCALE="full"`): https://files.grouplens.org/datasets/movielens/ml-25m.zip
- Fallback sintético con drift (catálogo creciente + desplazamiento de gustos) si no hay red.

## Lecturas clave
- Sculley et al. (2015). *Hidden Technical Debt in Machine Learning Systems*. NeurIPS.
- Breck et al. (2017). *The ML Test Score*. IEEE Big Data.
- Shankar et al. (2022). *Operationalizing Machine Learning: An Interview Study*. arXiv:2209.09125.
- Bernardi et al. (2019). *150 Successful Machine Learning Models: 6 Lessons Learned at Booking.com*. KDD.
- Chaney et al. (2018). *How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility*. RecSys.
- Rabanser et al. (2019). *Failing Loudly: An Empirical Study of Methods for Detecting Dataset Shift*. NeurIPS.
- Google Cloud. *MLOps: Continuous delivery and automation pipelines in machine learning*.
- Evidently AI (2023). *Shift happens: we compared 5 methods to detect drift in ML embeddings*.

## Conexión con CineMatch
Mantiene vivo el servicio del módulo 16: el flow de CT registra challengers, el servicio carga `@champion` y el rollback
es mover un alias. El capstone (18) usa el registry y el informe de drift como parte de la rúbrica.
