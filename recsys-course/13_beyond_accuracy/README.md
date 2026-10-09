# Módulo 13 · Más allá de la precisión

**Nivel:** 🟠 Avanzado → 🔴 Experto · **Duración:** 6–7 h (lección) + 4–6 h (proyecto) · **GPU:** no necesaria (NumPy en CPU) · **Unidades de Colab:** ~0–1.

| Notebook | Contenido |
|---|---|
| [`13_beyond_accuracy.ipynb`](13_beyond_accuracy.ipynb) | Lección: métricas *beyond-accuracy*, MMR, DPP (greedy rápido de Chen et al. 2018 y kernel de YouTube), calibración de Steck con KL, novedad/serendipia, popularidad y simulación de *feedback loops*, fairness de exposición, multi-objetivo y frente de Pareto, optimización de página estilo Netflix, reglas de negocio |
| [`13_proyecto_reranker_home.ipynb`](13_proyecto_reranker_home.ipynb) | Proyecto: re-ranker de la home de CineMatch que optimiza relevancia + diversidad + calibración, con barrido de Pareto en validación, página deduplicada con reglas y simulación de feedback loop |

## Objetivos
1. Medir ILD, cobertura, Gini de exposición, novedad, serendipia y miscalibración (KL), e interpretar sus *trade-offs* con NDCG.
2. Implementar desde cero **MMR**, **DPP** (Cholesky incremental, O(NK²)) y **calibración** (Steck 2018).
3. **Simular feedback loops** y cuantificar la concentración de la exposición por política (curvas de Gini, cuota del top-1 %, Lorenz).
4. Evaluar y corregir la **fairness de exposición** (Singh & Joachims 2018; cuotas por prefijo estilo FA*IR; amortizada estilo Biega 2018) y la equidad entre usuarios.
5. Calcular **frentes de Pareto**, hipervolumen y elegir puntos operativos por **ε-restricción**.
6. Construir una **home 2D** (filas × columnas) con modelo de atención y greedy de página con deduplicación.
7. Diseñar un **motor de reglas de negocio** auditable (filtros duros, cuotas, boosts, pins).

## Dataset
**MovieLens latest-small** (GroupLens; `ml-1m` con `FAST_DEV_RUN=False`). Los géneros sirven como espacio interpretable de diversidad/calibración. Candidatos: top-100 de un retriever PureSVD + FAISS. *Fallback* sintético si no hay red.

## Utilidades de módulos anteriores
Carga de MovieLens y split temporal (01), `Recall/NDCG@K` (02) y retriever PureSVD + FAISS (08), incluidos en versión mínima en cada notebook.

## Lecturas clave
- Carbonell & Goldstein (1998). *MMR*. SIGIR.
- Chen, Zhang & Zhou (2018). *Fast Greedy MAP Inference for DPP*. NeurIPS. [arXiv:1709.05135](https://arxiv.org/abs/1709.05135)
- Wilhelm et al. (2018). *Practical Diversified Recommendations on YouTube with DPPs*. CIKM. [doi](https://doi.org/10.1145/3269206.3272018)
- Steck (2018). *Calibrated Recommendations*. RecSys. [doi](https://doi.org/10.1145/3240323.3240372)
- Chaney et al. (2018). *How Algorithmic Confounding in Recommendation Systems Increases Homogeneity and Decreases Utility*. [arXiv:1710.11214](https://arxiv.org/abs/1710.11214)
- Singh & Joachims (2018). *Fairness of Exposure in Rankings*. KDD. [arXiv:1802.07281](https://arxiv.org/abs/1802.07281)
- Alvino & Basilico (2015). *Learning a Personalized Homepage*. Netflix TechBlog.
- Anderson et al. (2020). *Algorithmic Effects on the Diversity of Consumption on Spotify*. WWW.

## Conexión con CineMatch
El re-ranker del proyecto es la etapa final de la home de CineMatch: recibe los candidatos del módulo 08 (o el ranker multi-objetivo del 07), y sus métricas *beyond-accuracy* serán *guardrails* en el A/B test del módulo 15. La simulación de feedback loop motiva la exploración del módulo 14.

## Regenerar los notebooks
```bash
python recsys-course/_tools/builders/build_13.py
```
