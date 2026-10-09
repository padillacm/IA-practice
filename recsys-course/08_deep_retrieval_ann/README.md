# Módulo 08 · Deep retrieval (two-tower) y búsqueda ANN

**Nivel:** 🟠 Avanzado · **Duración:** 6 h (lección) + 4–6 h (proyecto) · **GPU:** L4 o A100 (T4 suficiente para MovieLens-1M; A100 para ML-25M)

El ranker solo ordena lo que le llega. Este módulo construye la **fuente de candidatos** profunda: un modelo *two-tower* cuyo score es un producto escalar (y por tanto indexable), entrenado con softmax muestreada, y un índice **ANN** que devuelve el top-K entre millones de ítems en milisegundos.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`08_deep_retrieval_ann.ipynb`](08_deep_retrieval_ann.ipynb) | Lección: YouTube DNN (2016) · softmax muestreada · **in-batch negatives** y su sesgo · **corrección logQ** (Yi et al. 2019) · máscara de *accidental hits* · **Mixed Negative Sampling** · **hard negatives** (EBR) · estimador de frecuencia en streaming · temperatura · t-SNE de embeddings · recall por cabeza/torso/cola · **FAISS** Flat / IVF / IVF-PQ / IVF-PQ+refine / HNSW con curvas **recall vs latencia** y memoria · FAISS GPU, hnswlib, ScaNN · servicio top-K con filtrado · bases vectoriales (Milvus, Qdrant, Weaviate, pgvector, Vespa) |
| [`08_proyecto_two_tower_faiss.ipynb`](08_proyecto_two_tower_faiss.ipynb) | Proyecto CineMatch: two-tower en PyTorch con logQ + MNS, ablación cabeza/cola, índice HNSW validado contra búsqueda exacta y servicio `recommend()` con p99 < 10 ms |

## Objetivos
1. Explicar por qué el retrieval necesita scores factorizados.
2. Derivar el sesgo de los in-batch negatives y la corrección logQ.
3. Implementar two-tower con in-batch, logQ, MNS y hard negatives.
4. Construir y comparar índices FAISS con curvas recall–latencia.
5. Servir candidatos con filtrado y presupuestos de latencia.

## Datasets
- **MovieLens-1M** (por defecto) o **MovieLens-25M** (`SCALE="25m"`) de GroupLens, con split temporal global. Fallback sintético si no hay red.
- Corpus ANN aumentado (200 k – 2 M vectores) generado a partir de los embeddings aprendidos para estresar los índices.

## Lecturas clave
- Covington et al. (2016) *Deep Neural Networks for YouTube Recommendations*.
- Yi et al. (2019) *Sampling-Bias-Corrected Neural Modeling for Large Corpus Item Recommendations*.
- Yang et al. (2020) *Mixed Negative Sampling for Learning Two-tower Neural Networks*.
- Huang et al. (2020) *Embedding-based Retrieval in Facebook Search*.
- Johnson et al. (2017) / Douze et al. (2024) *Faiss* · Malkov & Yashunin (2018) *HNSW* · Guo et al. (2020) *ScaNN*.
- Rendle et al. (2020) *Neural Collaborative Filtering vs. Matrix Factorization Revisited*.

## Conexión con CineMatch
El two-tower + FAISS es la fuente principal de candidatos de CineMatch: alimenta el ranker de los módulos 06–07, el agente conversacional del 12 y el microservicio del 16.

Los notebooks se generan con `python recsys-course/_tools/builders/build_08.py` (desde la raíz del repo).
