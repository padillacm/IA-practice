# Módulo 11 · Recomendadores generativos y *foundation models*

**Bloque IV — Estado del arte** · Nivel 🔴 Experto · Lección 5–6 h + proyecto 4 h · GPU **A100** (L4 con menos épocas) · ≈ 8–12 unidades de Colab en modo completo

El cambio de paradigma 2023–2026: de **puntuar** ítems con un producto escalar a **generar** el identificador del siguiente ítem (o la siguiente acción) token a token, como un LLM.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`11_generative_recsys.ipynb`](11_generative_recsys.ipynb) | Lección: paradigmas (two-tower + ANN vs generative retrieval vs Generative Recommenders); memoria de tablas de IDs vs semantic IDs; **RQ-VAE desde cero** (k-means init, reinicio de códigos muertos, colisiones, pureza) vs **RQ-KMeans**; **trie** de semantic IDs; modelo **TIGER-mini** encoder-decoder con **beam search restringido**; comparación honesta con SASRec-CE y análisis por popularidad; **HSTU mini** (atención pointwise SiLU + sesgos relativos de posición/tiempo + puerta U) vs SASRec en ML-1M con mapas de atención; **curvas de escalado** y ajuste de ley de potencias; producción (Meta HSTU, Kuaishou OneRec V1/V2, Netflix, YouTube Semantic IDs y PLUM, Pinterest PinRec). |
| [`11_proyecto_semantic_ids.ipynb`](11_proyecto_semantic_ids.ipynb) | Proyecto: tienda de videojuegos de CineMatch con catálogo cambiante. Tokenizador RQ-VAE → semantic IDs, trie, retrieval generativo, y experimento de **cold start** (ítems nunca vistos por el generador). Plantilla con TODOs + solución. |

## Objetivos
- Construir y diagnosticar semantic IDs; entender colisiones y *codebook collapse*.
- Implementar generative retrieval con decodificación restringida.
- Implementar una capa HSTU y explicar por qué elimina la softmax.
- Leer críticamente las *scaling laws* y los resultados industriales.

## Datasets
- **Amazon Reviews 2023** (McAuley Lab; Hou et al. 2024), Hugging Face `McAuley-Lab/Amazon-Reviews-2023`:
  `benchmark/5core/rating_only/<Categoría>.csv` + `raw/meta_categories/meta_<Categoría>.jsonl`. Por defecto `Video_Games`.
- **MovieLens-1M** para HSTU (necesita *timestamps*) y escalado (opción `ml-20m` en A100).
- Fallbacks automáticos: Amazon → MovieLens-1M (título + géneros) → sintético. Embeddings: Sentence-T5 → TF-IDF + SVD si no hay acceso a modelos.

## Convenciones
- Semantic ID = 3 códigos RQ (K = 256) + token de desambiguación. Tokens con *offset* por nivel; `0` = padding; último token = `BOS`.
- `SemanticIDTrie.allowed_mask(prefijos, nivel, tamaño)` vectorizado en GPU (`searchsorted`) y `lookup(códigos) -> ítem`.
- Modelos secuenciales con interfaz `encode(seq, ts)`; historias como tuplas `(items, timestamps)` para HSTU.
- Métricas: Recall@K/NDCG@K con el mismo protocolo *leave-one-out* que el módulo 09.

## Lecturas clave
- Rajput et al. (NeurIPS 2023) TIGER · Zhai et al. (ICML 2024) HSTU / *Actions Speak Louder than Words* · `meta-recsys/generative-recommenders`
- Singh et al. (RecSys 2024) *Better Generalization with Semantic IDs* · Yang et al. (2024) LIGER
- Deng et al. (2025) OneRec · OneRec Technical Report (2025) · OneRec-V2 (2025)
- Netflix Tech Blog (2025) *Foundation Model for Personalized Recommendation* · Xu, Hsiao & Bhattacharya (2026)
- He et al. (2025) PLUM · Badrinath, Agarwal et al. (2025) PinRec · Ju et al. (CIKM 2025) GRID

**Anterior:** [10_graph](../10_graph/) · **Siguiente:** 12_llm_agents_recsys
