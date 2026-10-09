# Módulo 06 · Ranking como predicción de CTR

**Nivel:** 🟡 Intermedio → 🟠 Avanzado · **Duración:** 5–6 h (lección) + 4–6 h (proyecto) · **GPU:** L4 recomendada (T4 suficiente con `FAST_DEV_RUN=True`; A100 para 5 M+ filas)

La etapa de *ranking* recibe unos cientos de candidatos del retrieval y les pone una nota fina con todas las features (usuario × ítem × contexto). Casi siempre se formula como un **clasificador binario probabilístico** (pCTR), y aquí es donde viven los modelos de interacción de features.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`06_ctr_ranking.ipynb`](06_ctr_ranking.ipynb) | Lección: logloss, **Normalized Entropy**, AUC/GAUC · LR con *hashing trick* · **FM** (derivación O(kn)) · **FFM** · **Wide & Deep** · **DeepFM** · **DCN-v2** · **LightGBM** y **GBDT+LR** (Facebook 2014) · interacciones aprendidas (heatmaps FM y bloques de W en DCN-v2) · colisiones de hashing · **calibración** (reliability diagrams, ECE, corrección por *negative downsampling*, isotónica) · **DIN** sobre MovieLens con visualización de la atención · TorchRec / Merlin / FuxiCTR / DeepCTR-Torch |
| [`06_proyecto_ranker_ctr.ipynb`](06_proyecto_ranker_ctr.ipynb) | Proyecto CineMatch: ranker de la home con MovieLens-1M; features **point-in-time** vs feature con **fuga**; **DCN-v2 vs LightGBM**; calibración y recomendación al *tech lead* |

## Objetivos
1. Formular el ranking como predicción de pCTR y explicar por qué importa la calibración.
2. Construir features categóricas de alta cardinalidad (vocabulario con OOV, bucketización, hashing).
3. Implementar desde cero LR, FM, FFM, Wide & Deep, DeepFM, DCN-v2 y DIN en PyTorch.
4. Comparar con LightGBM y GBDT+LR usando logloss, AUC y NE.
5. Diagnosticar y corregir calibración; medir el efecto de las colisiones de embeddings.

## Datasets
- **Criteo 1TB Click Logs** (Criteo AI Lab, Hugging Face `criteo/CriteoClickLogs`, CC BY-NC-SA 4.0): se leen en *streaming* solo las primeras N filas de `day_0.gz`. Si el dataset pide aceptar la licencia, define `HF_TOKEN`. **Fallback**: Criteo sintético con el mismo esquema (13 enteros + 26 categóricas) e interacciones conocidas.
- Alternativa para comparar con papers: versiones BARS/FuxiCTR (`reczoo/Criteo_x1`, `reczoo/Avazu_x1` en Hugging Face, ver https://github.com/reczoo/Datasets).
- **MovieLens-1M** (GroupLens) para DIN y para el proyecto (fallback sintético incluido).

## Lecturas clave
- He et al. (2014) *Practical Lessons from Predicting Clicks on Ads at Facebook*.
- Rendle (2010) *Factorization Machines* · Juan et al. (2016) *FFM*.
- Cheng et al. (2016) *Wide & Deep* · Guo et al. (2017) *DeepFM*.
- Wang et al. (2021) *DCN V2* · Zhou et al. (2018) *DIN*.
- Zhu et al. (2021) *Open Benchmarking for CTR Prediction* (FuxiCTR/BARS).
- Anil et al. (2022) *On the Factory Floor: ML Engineering for Industrial-Scale Ads Recommendation Models*.

## Conexión con CineMatch
El proyecto produce el **ranker calibrado** de la home que en el módulo 07 se vuelve multi-tarea y en el 16 se despliega detrás del retrieval two-tower + FAISS del módulo 08.

Los notebooks se generan con `python recsys-course/_tools/builders/build_06.py` (desde la raíz del repo).
