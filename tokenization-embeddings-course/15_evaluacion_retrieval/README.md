# 15 · Evaluación de embeddings y retrieval 🟠

> Entrenar un embedder es fácil; saber si es **mejor** es lo difícil. Aquí se construye el **banco de evaluación de Políglota** (`poliglota_eval.py`): métricas con tests, golden sets, intervalos de confianza, tests pareados, LLM-as-judge con sus sesgos, el límite teórico de la dimensión del embedding, contaminación, drift y análisis de errores.

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **GPU** | No necesaria (CPU, ≈ 0 unidades de Colab) |
| **Prerrequisitos** | 00 (BM25 + mini golden set), 10, 12, 13, 14 |
| **Estado del arte** | a oct-2026; cifras de leaderboards, modelos y papers fechados |

## 📓 Archivos
| Archivo | Contenido | Colab |
|---|---|---|
| [`15_evaluacion_retrieval.ipynb`](15_evaluacion_retrieval.ipynb) | Lección: nDCG/Recall/MRR con tests y verificación contra `ranx`, BEIR/MIRACL/MTEB/MMTEB/RTEB, bootstrap y tests pareados (con Holm), tamaño de golden set, sesgo de pooling, LLM-as-judge (simulación + celda opcional con API), **LIMIT** (cota y embeddings libres), contaminación, drift (PSI), análisis de errores por slices | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/tokenization-embeddings-course/15_evaluacion_retrieval/15_evaluacion_retrieval.ipynb) |
| [`15_proyecto_evaluacion_retrieval.ipynb`](15_proyecto_evaluacion_retrieval.ipynb) | Proyecto: banco de evaluación de Políglota con TODOs, pistas 🪜, rúbrica calibrada y solución tras ⛔ SPOILER | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/tokenization-embeddings-course/15_evaluacion_retrieval/15_proyecto_evaluacion_retrieval.ipynb) |
| [`poliglota_eval.py`](poliglota_eval.py) | **Módulo canónico** de métricas/estadística/retrievers de referencia (generado por `_tools/builders/build_15.py`) | — |
| `assets/` | Imágenes/videos de Gemini (ver IDs `M15-*` en `extras/GEMINI_ASSETS.md`) | — |

## 🔌 Contrato de `poliglota_eval.py` (para el resto del curso)
- `ndcg_at_k(ranked_ids, rels, k=10, exp_gain=False)`, `recall_at_k`, `mrr_at_k`, `precision_at_k`: `ranked_ids` = lista ordenada de `doc_id`; `rels` = `dict doc_id -> relevancia` (>0 relevante).
- Convenciones (idénticas a `trec_eval`/`ranx`): ganancia lineal; duplicados cuentan una vez; **sin relevantes → 0.0**; `evaluate_per_query` excluye queries sin relevantes y puntúa 0 a la query sin ranking; empates → orden del corpus (`rank_from_scores`).
- `evaluate(run, qrels, k)` / `evaluate_per_query(...)`: `run = {qid: [doc_ids]}`, `qrels = {qid: {doc_id: rel}}`.
- `bootstrap_ci`, `paired_bootstrap` (IC de la diferencia + p por shift), `paired_permutation`, `holm`.
- Retrievers de CPU para pruebas sin descargas: `BM25`, `LSI`, `rrf_scores`, `build_run`.

Uso desde otro notebook (Colab):
```python
!wget -q https://raw.githubusercontent.com/padillacm/IA-practice/master/tokenization-embeddings-course/15_evaluacion_retrieval/poliglota_eval.py
from poliglota_eval import ndcg_at_k, recall_at_k, mrr_at_k, evaluate_per_query, bootstrap_ci, paired_bootstrap
```

## 🎯 Objetivos
1. Implementar y **testear** nDCG, Recall y MRR (empates, duplicados, graduadas, sin relevantes) y verificarlas contra `ranx`.
2. Construir golden sets (estratificación, pooling, κ) y **dimensionarlos** con bootstrap.
3. Comparar sistemas con **IC y tests pareados** corrigiendo comparaciones múltiples.
4. Entender y **medir** los sesgos de pooling y de LLM-as-judge.
5. Explicar y **reproducir** el límite de dimensión de Weller et al. (LIMIT).
6. Detectar contaminación y drift; hacer análisis de errores que lleve a acciones.

## 📦 Datos
Corpus Políglota (`carga_corpus`: Wikipedia ES/EN + CodeSearchNet vía Hugging Face) con **fallback sintético** (huecos léxicos a propósito) cuando no hay red. BEIR (`BeIR/scifact`, `BeIR/fiqa`) y MIRACL-es se cargan en celdas opcionales (`FAST_DEV_RUN=False`).

## 📚 Lecturas clave (verificadas)
- Thakur et al. (2021). *BEIR*. <https://arxiv.org/abs/2104.08663>
- Muennighoff et al. (2022). *MTEB*. <https://arxiv.org/abs/2210.07316> · Enevoldsen et al. (2025). *MMTEB*. <https://arxiv.org/abs/2502.13595>
- Weller, Boratko, Naim, Lee (2025). *On the Theoretical Limitations of Embedding-Based Retrieval*. <https://arxiv.org/abs/2508.21038>
- Smucker, Allan, Carterette (2007). *A Comparison of Statistical Significance Tests for IR Evaluation*. CIKM.
- Thomas et al. (2023) <https://arxiv.org/abs/2309.10621> vs Soboroff (2024) <https://arxiv.org/abs/2409.15133> (LLM-as-judge).
- Material del repo: [`recsys-course/02_evaluation`](../../recsys-course/02_evaluation/README.md) (métricas de ranking, sampled metrics, bootstrap) — aquí **no se repite**.

## ➡️ Siguiente
[16 · Embeddings multimodales](../16_embeddings_multimodales/)

---
*Notebooks generados con [`_tools/builders/build_15.py`](../_tools/builders/build_15.py).*
