# 05 · Factorización matricial

🟡→🟠 · 4–5 h (lección) + 4–6 h (proyecto) · GPU T4 recomendada (≈ 1–2 unidades de Colab)

Del Netflix Prize a la recomendación implícita moderna: factores latentes, sesgos, SGD, ALS y BPR.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`05_matrix_factorization.ipynb`](05_matrix_factorization.ipynb) | FunkSVD con SGD (numba) desde cero · escalera μ → sesgos → MF · curvas de convergencia, efecto de λ y k · espacio latente (PCA) · Surprise SVD/SVD++ · iALS desde cero (truco QᵀQ) · fold-in · BPR en PyTorch (GPU) · `implicit` (GPU) iALS/BPR · `cornac` · comparación con EASE |
| [`05_proyecto_ials_bpr.ipynb`](05_proyecto_ials_bpr.ipynb) | «Recomendado para ti» v2: iALS + BPR en GPU tuneados con Optuna, comparación con EASE, fold-in de usuarios nuevos |

## Objetivos
- Derivar e implementar FunkSVD, iALS y BPR; entender el papel de sesgos y regularización.
- Usar `implicit`, `Surprise` y `cornac`; tunear con Optuna sin fuga.
- Conocer la historia del Netflix Prize y qué se llevó a producción.

## Datasets
- **MovieLens 1M** (GroupLens; espejo en GitHub como fallback). Explícito para RMSE; implícito (cualquier rating) para top-K, relevante = rating ≥ 4.

## Lecturas clave
- Koren, Bell & Volinsky (2009), *Matrix Factorization Techniques for Recommender Systems*.
- Hu, Koren & Volinsky (2008), *Collaborative Filtering for Implicit Feedback Datasets*.
- Rendle et al. (2009), *BPR*; Rendle et al. (2022), *Revisiting the Performance of iALS*.
- Amatriain & Basilico (2012), *Netflix Recommendations: Beyond the 5 stars*.

## Conexión con CineMatch
Los vectores de iALS son la primera fuente de candidatos indexable en ANN (módulo 08) y una feature
para el ranker (módulo 06).

Generado con `python recsys-course/_tools/builders/build_05.py`.
