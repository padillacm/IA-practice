# Módulo 12 · Embedders modernos

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU:** T4 recomendada (CPU en `FAST_DEV_RUN`)

Ya sabes entrenar un embedder (módulo 11). Aquí aprendes qué hay **en el mercado** a oct-2026, cómo funcionan por dentro sus piezas
(pooling last-token y latent attention, prefijos e instrucciones, **Matryoshka**, **cuantización int8 y binaria con rescoring**),
cómo leer MTEB/MMTEB con ojo crítico y cómo **elegir** un embedder con datos de tu propio corpus.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`12_embedders_modernos.ipynb`](12_embedders_modernos.ipynb) | Lección: las tres olas de embedders · pooling desde cero (CLS/mean/max/last-token/latent attention) · LLM2Vec y NV-Embed · prefijos e instrucciones (E5, Qwen3, EmbeddingGemma, Nomic) · pérdida **Matryoshka** y experimento de juguete · truncado + renormalización vs PCA · **int8 y binaria desde cero** + rescoring · comparación de modelos con `sentence-transformers` · bootstrap pareado · MTEB/MMTEB y sus límites · árbol de decisión · 🏭 producción · 🧠 secretos · autoevaluación |
| [`12_proyecto_embedders_modernos.ipynb`](12_proyecto_embedders_modernos.ipynb) | Proyecto: comparativa de 4–6 embedders × escalas Matryoshka × 4 precisiones en Políglota; frontera de Pareto (calidad vs memoria vs latencia) y recomendación para 10 M de documentos en 20 GB. Plantilla con TODOs, pistas 🪜, autocomprobación de la rúbrica y solución tras ⛔ SPOILER |

## Objetivos
1. Explicar la receta de un embedder moderno y la diferencia entre encoder y decoder-as-embedder.
2. Implementar los pooling y el bug del *padding side* en last-token.
3. Aplicar prefijos/instrucciones y medir su efecto.
4. Derivar e implementar Matryoshka (truncar + renormalizar) y saber cuándo falla.
5. Implementar cuantización int8 y binaria + rescoring, y compararla con `sentence-transformers`.
6. Comparar embedders con intervalos de confianza y decidir con un árbol de decisión.

## Datasets
Corpus Políglota vía `carga_corpus()` (cadena oficial → espejo → sintético): Wikipedia ES/EN y CodeSearchNet si hay acceso (o el espejo de la API de Wikipedia); si no, el
corpus sintético del módulo 00 (texto ES/EN de plantillas + código de la stdlib) con el mismo esquema. Los modelos se descargan de Hugging Face; sin red se usa un fallback TF-IDF+SVD
(el notebook avisa con `⚠️`).

## Lecturas clave (verificadas)
- Kusupati et al. (2022), *Matryoshka Representation Learning* (arXiv 2205.13147).
- Wang et al. (2024), *Multilingual E5 Text Embeddings* (2402.05672) · Chen et al. (2024), *M3-Embedding / BGE-M3* (2402.03216).
- Lee et al. (2024), *NV-Embed* (2405.17428) · BehnamGhader et al. (2024), *LLM2Vec* (2404.05961).
- Zhang et al. (2025), *Qwen3 Embedding* (2506.05176) · Vera et al. (2025), *EmbeddingGemma* (2509.20354) · Lee et al. (2025), *Gemini Embedding* (2503.07891).
- Muennighoff et al. (2022), *MTEB* (2210.07316) · Enevoldsen et al. (2025), *MMTEB* (2502.13595).
- Shakir, Aarsen, Lee (2024), *Binary and Scalar Embedding Quantization* (blog de Hugging Face).

## Conexión con Políglota
El embedder y la configuración (dimensión, precisión) que elijas aquí serán el **retriever denso** del módulo 13 y fijarán el tamaño del índice del módulo 14.

*Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_12.py` (desde la raíz del repo). Estado del arte a octubre de 2026: re-verifica IDs de modelos y cifras antes de usarlas.*
