# Módulo 07 · Learning to Rank y ranking multi-tarea

**Nivel:** 🟠 Avanzado · **Duración:** 6 h (lección) + 5–6 h (proyecto) · **GPU:** L4 recomendada (T4 suficiente con `FAST_DEV_RUN=True`)

El usuario no ve impresiones sueltas: ve **listas**, y el negocio no optimiza un único objetivo. Este módulo cubre cómo optimizar el **orden** (pointwise → pairwise → listwise, LambdaMART), cómo aprender de clics con **sesgo de posición**, y cómo entrenar un ranker **multi-tarea** (clic, visionado largo, like) y fusionar sus salidas.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`07_learning_to_rank_multitask.ipynb`](07_learning_to_rank_multitask.ipynb) | Lección: NDCG y su no-diferenciabilidad · **RankNet**, **LambdaRank** (derivación de λ con \|ΔNDCG\|), **ListNet**, **ListMLE** desde cero en PyTorch · **LambdaMART** con LightGBM · simulación de **position bias** (PBM), estimación de propensiones con tráfico aleatorizado, **IPS** y **PAL** · **Shared-Bottom, MMoE, PLE** desde cero · experimento sintético de correlación entre tareas (*seesaw*) · **frente de Pareto** · utilización de expertos · **ESMM** · fusión de objetivos |
| [`07_proyecto_ranker_multiobjetivo.ipynb`](07_proyecto_ranker_multiobjetivo.ipynb) | Proyecto CineMatch Clips: MMoE/PLE vs Shared-Bottom vs single-task en KuaiRand, frente de Pareto, baseline LambdaMART con etiqueta de negocio y fusión tuneada en validación |

## Objetivos
1. Elegir entre pointwise, pairwise y listwise según la métrica.
2. Derivar RankNet/LambdaRank y usar LambdaMART en LightGBM.
3. Corregir el sesgo de posición (IPS, PAL / shallow tower).
4. Implementar MMoE, PLE y ESMM y diagnosticar el *seesaw*.
5. Diseñar y evaluar una fórmula de fusión multi-objetivo.

## Datasets
- **MovieLens-1M** (GroupLens) convertido en un problema LTR temporal (consultas = usuarios, candidatos = vistos + negativos por popularidad, features solo del pasado). Fallback sintético.
- **KuaiRand-Pure** (Gao et al., CIKM 2022): logs de Kuaishou con `is_click`, `long_view`, `is_like`… Descarga: `https://zenodo.org/records/10439422/files/KuaiRand-Pure.tar.gz` (según el README de https://github.com/chongminggao/KuaiRand). Fallback sintético con el mismo esquema.

## Lecturas clave
- Burges (2010) *From RankNet to LambdaRank to LambdaMART: An Overview*.
- Joachims et al. (2017) *Unbiased Learning-to-Rank with Biased Feedback* · Guo et al. (2019) *PAL*.
- Ma et al. (2018) *MMoE* · Tang et al. (2020) *PLE* · Ma et al. (2018) *ESMM*.
- Zhao et al. (2019) *Recommending What Video to Watch Next: A Multitask Ranking System* (YouTube).
- Qin et al. (2021) *Are Neural Rankers still Outperformed by GBDT?*

## Conexión con CineMatch
Convierte el ranker del módulo 06 en el ranker multi-objetivo de la home; la fusión de scores se re-ranquea por diversidad/calibración en el módulo 13 y se valida con A/B en el 15.

Los notebooks se generan con `python recsys-course/_tools/builders/build_07.py` (desde la raíz del repo).
