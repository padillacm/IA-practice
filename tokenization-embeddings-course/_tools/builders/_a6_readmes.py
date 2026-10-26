"""READMEs de los módulos 15–17 (los escriben los build_NN.py)."""

R = "padillacm/IA-practice"
B = "master"
C = "tokenization-embeddings-course"


def badge(mod_dir: str, nb: str) -> str:
    return f"[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/{R}/blob/{B}/{C}/{mod_dir}/{nb})"


README_15 = f"""# 15 · Evaluación de embeddings y retrieval 🟠

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
| [`15_evaluacion_retrieval.ipynb`](15_evaluacion_retrieval.ipynb) | Lección: nDCG/Recall/MRR con tests y verificación contra `ranx`, BEIR/MIRACL/MTEB/MMTEB/RTEB, bootstrap y tests pareados (con Holm), tamaño de golden set, sesgo de pooling, LLM-as-judge (simulación + celda opcional con API), **LIMIT** (cota y embeddings libres), contaminación, drift (PSI), análisis de errores por slices | {badge("15_evaluacion_retrieval", "15_evaluacion_retrieval.ipynb")} |
| [`15_proyecto_evaluacion_retrieval.ipynb`](15_proyecto_evaluacion_retrieval.ipynb) | Proyecto: banco de evaluación de Políglota con TODOs, pistas 🪜, rúbrica calibrada y solución tras ⛔ SPOILER | {badge("15_evaluacion_retrieval", "15_proyecto_evaluacion_retrieval.ipynb")} |
| [`poliglota_eval.py`](poliglota_eval.py) | **Módulo canónico** de métricas/estadística/retrievers de referencia (generado por `_tools/builders/build_15.py`) | — |
| `assets/` | Imágenes/videos de Gemini (ver IDs `M15-*` en `extras/GEMINI_ASSETS.md`) | — |

## 🔌 Contrato de `poliglota_eval.py` (para el resto del curso)
- `ndcg_at_k(ranked_ids, rels, k=10, exp_gain=False)`, `recall_at_k`, `mrr_at_k`, `precision_at_k`: `ranked_ids` = lista ordenada de `doc_id`; `rels` = `dict doc_id -> relevancia` (>0 relevante).
- Convenciones (idénticas a `trec_eval`/`ranx`): ganancia lineal; duplicados cuentan una vez; **sin relevantes → 0.0**; `evaluate_per_query` excluye queries sin relevantes y puntúa 0 a la query sin ranking; empates → orden del corpus (`rank_from_scores`).
- `evaluate(run, qrels, k)` / `evaluate_per_query(...)`: `run = {{qid: [doc_ids]}}`, `qrels = {{qid: {{doc_id: rel}}}}`.
- `bootstrap_ci`, `paired_bootstrap` (IC de la diferencia + p por shift), `paired_permutation`, `holm`.
- Retrievers de CPU para pruebas sin descargas: `BM25`, `LSI`, `rrf_scores`, `build_run`.

Uso desde otro notebook (Colab):
```python
!wget -q https://raw.githubusercontent.com/{R}/{B}/{C}/15_evaluacion_retrieval/poliglota_eval.py
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
"""


README_16 = f"""# 16 · Embeddings multimodales 🟠

> Un solo espacio para texto e imagen (y más). Aquí se construye un **CLIP/SigLIP en miniatura** para *medir* el modality gap, y un **ColPali en miniatura** (patches + MaxSim) para decidir cuándo buscar en capturas y PDFs con embeddings visuales y cuándo basta OCR + texto.

| | |
|---|---|
| **Nivel** | 🟠 Avanzado |
| **Duración** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **GPU** | L4 recomendada solo para las celdas opcionales con modelos reales; todo lo demás corre en CPU (`FAST_DEV_RUN=True`) |
| **Prerrequisitos** | 08, 11, 13, 15 |
| **Estado del arte** | a oct-2026; capacidades de modelos propietarios fechadas y a verificar en documentación oficial |

## 📓 Archivos
| Archivo | Contenido | Colab |
|---|---|---|
| [`16_embeddings_multimodales.ipynb`](16_embeddings_multimodales.ipynb) | Lección: CLIP e InfoNCE simétrica y SigLIP (sigmoide) desde cero, modality gap **medido** (cono, temperatura, índice mixto), SigLIP 2, ColPali/ViDoRe con MaxSim sobre patches (OCR vs visual vs vector medio), coste de almacenamiento, embeddings unificados (Gemini Embedding 2, Jina v4, VLM2Vec), audio y video, árbol de decisión | {badge("16_embeddings_multimodales", "16_embeddings_multimodales.ipynb")} |
| [`16_proyecto_embeddings_multimodales.ipynb`](16_proyecto_embeddings_multimodales.ipynb) | Proyecto «Políglota Visual»: capturas sintéticas de la documentación, estudiante visual destilado del texto, MaxSim, evaluación con IC y coste; plantilla con TODOs, pistas 🪜, rúbrica calibrada y solución tras ⛔ SPOILER | {badge("16_embeddings_multimodales", "16_proyecto_embeddings_multimodales.ipynb")} |
| `assets/` | Imágenes/videos de Gemini (IDs `M16-*` en `extras/GEMINI_ASSETS.md`) | — |

## 🎯 Objetivos
1. Implementar CLIP y SigLIP en miniatura y compararlos.
2. Medir el modality gap y su efecto en un índice mixto.
3. Programar MaxSim sobre patches y compararlo con un único vector por página y con OCR + texto.
4. Estimar el coste de un índice multi-vector y las palancas para reducirlo.
5. Situar los embeddings unificados con capacidades verificadas y fechadas.

## 📦 Datos
Juguete generado en código (figuras de colores con captions ES/EN; páginas renderizadas con la fuente por defecto de Pillow) y corpus Políglota (`carga_corpus`, con fallback sintético). Modelos reales (CLIP/SigLIP, `colpali-engine`) y la API de Gemini son **celdas opcionales protegidas** (no probadas en el entorno de desarrollo: sin acceso a Hugging Face).

## 📚 Lecturas clave (verificadas)
- Radford et al. (2021). *CLIP*. <https://arxiv.org/abs/2103.00020> · Zhai et al. (2023). *SigLIP*. <https://arxiv.org/abs/2303.15343> · Tschannen et al. (2025). *SigLIP 2*. <https://arxiv.org/abs/2502.14786>
- Liang et al. (2022). *Mind the Gap*. <https://arxiv.org/abs/2203.02053>
- Faysse et al. (2024). *ColPali*. <https://arxiv.org/abs/2407.01449> · ViDoRe V2 <https://arxiv.org/abs/2505.17166> · ViDoRe V3 <https://arxiv.org/abs/2601.08620>

## ➡️ Siguiente
[17 · Interpretabilidad y geometría](../17_interpretabilidad_geometria/)

---
*Notebooks generados con [`_tools/builders/build_16.py`](../_tools/builders/build_16.py).*
"""


README_17 = f"""# 17 · Interpretabilidad y geometría de los embeddings 🔴

> ¿Qué hay dentro de un vector de embedding y qué revela? Aquí se **implementa desde cero** un sparse autoencoder TopK (con AuxK) y uno ReLU+L1, se miden sondas con *control tasks*, direcciones de concepto, dimensiones dominantes e inversión de embeddings, y se aplica todo a los embeddings de Políglota. Con etiquetas de madurez honestas (🟡/🔴).

| | |
|---|---|
| **Nivel** | 🔴 Experto |
| **Duración** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **GPU** | No necesaria con `FAST_DEV_RUN=True`; T4/L4 solo con el embedder real opcional |
| **Prerrequisitos** | 09–12, 15 |
| **Estado del arte** | a oct-2026; SAE sobre embeddings de retrieval = 🔴 experimental |

## 📓 Archivos
| Archivo | Contenido | Colab |
|---|---|---|
| [`17_interpretabilidad_geometria.ipynb`](17_interpretabilidad_geometria.ipynb) | Lección: probing y control tasks (Hewitt), representación lineal (steering por diferencia de medias, borrado lineal), dimensiones dominantes (Timkey; Kovaleva), superposición (Toy Models), **TopK SAE y ReLU+L1 desde cero** con recuperación de características plantadas, features de Políglota (pureza vs k-means/PCA, estabilidad entre semillas), steering con SAE vs baseline, qué codifica un embedding, inversión (vec2text) y trade-off privacidad–utilidad | {badge("17_interpretabilidad_geometria", "17_interpretabilidad_geometria.ipynb")} |
| [`17_proyecto_interpretabilidad_geometria.ipynb`](17_proyecto_interpretabilidad_geometria.ipynb) | Proyecto: SAE sobre embeddings de `carga_corpus` y análisis de features interpretables; plantilla con TODOs, pistas 🪜, rúbrica calibrada y solución tras ⛔ SPOILER | {badge("17_interpretabilidad_geometria", "17_proyecto_interpretabilidad_geometria.ipynb")} |
| `assets/` | Imágenes/videos de Gemini (IDs `M17-*`) | — |

## 🎯 Objetivos
1. Diseñar sondas con control tasks y selectividad.
2. Probar la hipótesis de representación lineal con steering y borrado, y ver sus límites.
3. Diagnosticar dimensiones dominantes y anisotropía.
4. Implementar TopK SAE y evaluarlo con verdad terreno, semillas y baselines (k-means, PCA, diferencia de medias).
5. Medir qué se puede reconstruir desde un embedding y su coste de defensa.

## 📚 Lecturas clave (verificadas)
- Hewitt & Manning (2019) <https://aclanthology.org/N19-1419/> · Hewitt & Liang (2019) <https://arxiv.org/abs/1909.03368>
- Park, Choe, Veitch (2023) <https://arxiv.org/abs/2311.03658> · Elhage et al. (2022) <https://arxiv.org/abs/2209.10652>
- Gao et al. (2024) <https://arxiv.org/abs/2406.04093> · Wu et al. (2025) <https://arxiv.org/abs/2501.17148> · Paulo & Belrose (2025) <https://arxiv.org/abs/2501.16615>
- Morris et al. (2023) <https://arxiv.org/abs/2310.06816>

## ➡️ Siguiente
[18 · Producción](../18_produccion/) (privacidad, versionado y monitorización).

---
*Notebooks generados con [`_tools/builders/build_17.py`](../_tools/builders/build_17.py).*
"""
