# 04 · Vecindarios y modelos lineales

🟡 · 3–4 h (lección) + 3–4 h (proyecto) · GPU opcional (T4 acelera EASE/SLIM, ≈ 1 unidad)

Filtrado colaborativo **basado en memoria** y **modelos lineales ítem-ítem**: los baselines que todo
modelo deep debe batir — y que muchas veces no bate.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`04_neighborhood_linear.ipynb`](04_neighborhood_linear.ipynb) | user-kNN e item-kNN desde cero con `scipy.sparse` · coseno, coseno asimétrico, Jaccard, coseno ajustado · shrinkage · RP3β · SLIM (ADMM) · **EASE** con derivación · `implicit` (Cosine/BM25) · `Surprise` (KNNBaseline, RMSE) · sesgo de popularidad |
| [`04_proyecto_knn_vs_ease.ipynb`](04_proyecto_knn_vs_ease.ipynb) | Informe «¿cambiamos a EASE?»: tuning con Optuna en validación, IC por bootstrap pareado, coste de memoria/latencia |

## Objetivos
- Implementar y tunear item-kNN, user-kNN, RP3β, SLIM y EASE.
- Entender shrinkage y normalización por popularidad como palancas precisión ↔ cobertura.
- Evaluar con rigor (split temporal, validación, IC) y razonar costes de producción.

## Datasets
- **MovieLens 1M** (GroupLens; espejo en GitHub como fallback). Implícito = cualquier rating; relevante en test = rating ≥ 4.

## Lecturas clave
- Linden, Smith & York (2003), *Amazon.com Recommendations: Item-to-Item CF*.
- Steck (2019), *Embarrassingly Shallow Autoencoders for Sparse Data* (EASE).
- Dacrema, Cremonesi & Jannach (2019), *Are We Really Making Much Progress?*
- Anelli et al. (2022), *Top-N Recommendation Algorithms: A Quest for the State-of-the-Art*.

## Conexión con CineMatch
Fila «Recomendado para ti» v1 y fuente de candidatos en tiempo real («Porque viste…»). En 05 lo
compararemos con factorización matricial (iALS/BPR).

Generado con `python recsys-course/_tools/builders/build_04.py`.
