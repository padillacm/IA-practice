# Módulo 18 · Capstone: CineMatch end-to-end + lo que solo sabe la élite

**Nivel:** 🔴 Experto · **Duración:** 6–8 h (lección) + 15–25 h (proyecto) · **GPU:** opcional (T4 para el two-tower con ML-1M) · **Unidades Colab:** 2–10

**Prerrequisitos:** todo el curso (00–17).

## Resumen
La lección integra el sistema en un ***walking skeleton*** ejecutable (retrieval multi-fuente → LambdaMART con features
point-in-time → MMR → función de serving con perfil de latencia → chequeo de drift), y luego reúne lo que no está en
los tutoriales:
- **🧠 Lo que solo sabe la élite**: 38 lecciones concretas, cada una con su paper o blog de origen.
- **Guía de entrevistas de system design**: marco de 10 pasos, cálculos *back-of-the-envelope* y 3 casos resueltos con
  diagramas — **home de Netflix**, **feed de YouTube/TikTok** y **People You May Know**.
- **Mapa de lectura** de 45 papers canónicos ordenados por etapa (con gráfico), **conferencias**, **blogs** de ingeniería
  y **ruta de carrera**.

El **proyecto capstone** construye CineMatch completo con rúbrica exigente (100 + 10 puntos): two-tower PyTorch con
corrección logQ + FAISS, fuentes PureSVD/co-ocurrencia/popularidad, LambdaMART con ablación, MMR, motor de serving
compartido por notebook y API (paridad por construcción), FastAPI con caché/fallback/métricas y test de carga, MLflow
(registry + alias champion), informe de drift con decisión de reentreno basada en «stale vs fresh», *scorecard*
automático, *design doc* y bonus de agente conversacional (Claude API con tool use, con fallback sin LLM).

## Contenido
| Archivo | Qué es |
|---|---|
| `18_capstone.ipynb` | Lección: mapa del sistema, walking skeleton, compendio de élite, system design (3 casos), papers, conferencias, blogs, carrera |
| `18_proyecto_capstone_cinematch.ipynb` | Proyecto capstone con TODOs por etapa, rúbrica y solución de referencia completa |
| `reference_stack/` | `docker-compose.yml` que incluye los stacks de los módulos 16 y 17 + imagen de la API del capstone |

## Datasets
- **MovieLens-100K** (iteración) y **MovieLens-1M** (entrega, `SCALE="full"`) — GroupLens. Fallback sintético sin red.

## Variables opcionales
- `ANTHROPIC_API_KEY` (bonus del agente; sin ella se usa el fallback determinista). `CINEMATCH_LLM_MODEL` para elegir modelo (por defecto `claude-opus-5-5`).

## Lecturas clave
Ver el mapa de lectura (§5 de la lección). Imprescindibles: Covington et al. 2016; Yi et al. 2019; He et al. 2014;
Krichene & Rendle 2020; Ferrari Dacrema et al. 2019; Zhao et al. 2019; Sculley et al. 2015; Zhai et al. 2024 (HSTU).
