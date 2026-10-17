# Módulo 16 · Recomendadores en producción: arquitectura, feature stores y serving

**Nivel:** 🔴 Experto · **Duración:** 5–6 h (lección) + 4–6 h (proyecto) · **GPU:** no necesaria (CPU basta) · **Unidades Colab:** 2–4

**Prerrequisitos:** 02 (evaluación), 05 (factorización), 06 (ranking CTR), 08 (two-tower + ANN), 13 (re-ranking).

## Resumen
El salto de «modelo en un notebook» a «servicio que responde en milisegundos». Partimos de la arquitectura
**offline / nearline / online** de Netflix, repartimos un **presupuesto de latencia** entre las etapas del funnel
multi-etapa, demostramos con código el *leakage* de un join ingenuo de features y lo corregimos con
**point-in-time joins** (a mano y con **Feast**), simulamos el bus de eventos (**Kafka/Redpanda**) y un consumidor
nearline, usamos **Redis** como caché, y desplegamos un microservicio **FastAPI + FAISS + LightGBM** dentro de Colab
con uvicorn en segundo plano. Exportamos un ranker a **TorchScript/ONNX**, comparamos **Triton, BentoML, Ray Serve y
TorchServe**, entendemos por qué existen **TorchRec / NVIDIA Merlin** (sharding de tablas de embeddings), detectamos
**training-serving skew** y hacemos **tests de carga**.

## Objetivos
1. Justificar qué cómputo va offline, nearline u online.
2. Repartir un presupuesto de latencia p99 y razonar sobre *tail at scale*.
3. Demostrar y corregir leakage temporal con point-in-time joins (Feast).
4. Implementar y medir un servicio de recomendación con caché, fallback e invalidación por evento.
5. Exportar modelos a TorchScript/ONNX con test de paridad.
6. Detectar training-serving skew con un chequeo de paridad de features.
7. Dimensionar réplicas a partir de un test de carga.

## Contenido
| Archivo | Qué es |
|---|---|
| `16_production_serving.ipynb` | Lección: arquitectura, latencia, PIT + Feast, nearline, Redis, FastAPI, load test, ONNX, servidores de modelos, sharding, skew, cold start |
| `16_proyecto_cinematch_microservicio.ipynb` | Proyecto: desplegar CineMatch como microservicio con rúbrica (PIT, LambdaMART, SLO p99, paridad de features) + solución |
| `reference_stack/` | Stack real para correr fuera de Colab: `docker-compose.yml` (API, Redis, Redpanda, consumidor nearline, Prometheus, Grafana, Triton), app FastAPI de producción, Feast con online store Redis, alertas Prometheus, dashboard Grafana, `config.pbtxt` de Triton, BentoML, Ray Serve, locustfile |

### Cómo usar `reference_stack/`
```bash
cd reference_stack
cp -r /ruta/a/artifacts ./artifacts          # artefactos generados por el notebook (celda "publicar artefactos")
docker compose up --build                     # API en :8000, Grafana en :3000 (admin/admin), Prometheus en :9090
locust -f loadtest/locustfile.py --host http://localhost:8000
docker compose --profile gpu up triton        # opcional, con GPU NVIDIA
```

## Datasets
- **MovieLens-100K** (GroupLens): https://files.grouplens.org/datasets/movielens/ml-100k.zip — lección y proyecto.
- **MovieLens-1M** (GroupLens): https://files.grouplens.org/datasets/movielens/ml-1m.zip — proyecto con `SCALE = "full"`.
- Fallback sintético con el mismo esquema si no hay red.

## Lecturas clave
- Amatriain & Basilico (2013). *System Architectures for Personalization and Recommendation*. Netflix Tech Blog.
- Netflix Tech Blog (2025). *Foundation Model for Personalized Recommendation*.
- Sculley et al. (2015). *Hidden Technical Debt in Machine Learning Systems*. NeurIPS.
- Dean & Barroso (2013). *The Tail at Scale*. CACM.
- Sadekar & Jiang (2018). *Time Travel based Feature Generation*. SysML (Netflix).
- Del Balso & Hermann (2017). *Meet Michelangelo: Uber's Machine Learning Platform*.
- Meta Engineering (2023). *Scaling the Instagram Explore recommendations system*.
- Liu et al. (2022). *Monolith: Real Time Recommendation System With Collisionless Embedding Table*. arXiv:2209.07663.
- Ivchenko et al. (2022). *TorchRec*. RecSys · Wang et al. (2022). *Merlin HugeCTR*. RecSys.
- Google. *Rules of Machine Learning* (reglas #29–#37 sobre skew).

## Conexión con CineMatch
El proyecto convierte el retrieval (mód. 08) + ranker (mód. 06–07) + re-ranking (mód. 13) en un servicio con contrato de
SLO. El módulo 17 lo monitoriza y reentrena; el capstone (18) lo integra todo.
