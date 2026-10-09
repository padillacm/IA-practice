# Módulo 10 · Recomendación con grafos

**Bloque IV — Estado del arte** · Nivel 🟠 Avanzado · Lección 4 h + proyecto 3 h · GPU T4/L4 · ≈ 2–3 unidades de Colab

La matriz usuario×ítem es un **grafo bipartito**. Propagar información por caminos de varios saltos (usuario → película → usuario parecido → película nueva) es otra forma de *collaborative filtering*, y la base de sistemas como PinSage (Pinterest) o TwHIN (Twitter).

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`10_graph.ipynb`](10_graph.ipynb) | Lección: ejemplo en papel 5×6 como grafo y potencias de $\hat A$; **item2vec** con gensim y SGNS desde cero; **DeepWalk/node2vec** con paseos vectorizados (y por qué $q$ apenas importa en grafos bipartitos); de GCN/NGCF a **LightGCN** (derivación); LightGCN **desde cero** con `torch.sparse.mm` y con **PyTorch Geometric**; capas vs *over-smoothing*; rendimiento por actividad del usuario; **PinSage** (vecindarios por importancia); grafos heterogéneos con `HeteroData`; producción (Pinterest, Alibaba EGES, Airbnb, TwHIN, LiGNN, Uber Eats). |
| [`10_proyecto_lightgcn_vs_mf.ipynb`](10_proyecto_lightgcn_vs_mf.ipynb) | Proyecto: generador de candidatos de CineMatch. LightGCN (PyG) vs MF-BPR con selección de capas por validación, análisis por cuartil de actividad y serving con FAISS. Plantilla con TODOs + solución. |

## Objetivos
- Representar interacciones como grafo y razonar en *multi-hop*.
- Entrenar item2vec/DeepWalk/node2vec y entender su relación con la factorización (PMI).
- Derivar e implementar LightGCN y compararlo de forma controlada con MF (LightGCN con $K=0$ ≡ MF).
- Conocer los patrones de despliegue de GNNs a escala (embeddings por lotes + ANN).

## Datasets
- **MovieLens-1M** como feedback implícito; split **temporal por usuario** (último 20 % → test).
- Fallback sintético automático si no hay red.

## Convenciones
- Usuarios `0..n_users-1`, ítems `0..n_items-1`; en grafos homogéneos (PyG) los ítems van desplazados `+ n_users`.
- `evaluate_topk(score_fn, R_train, R_test, k=20)` — Recall@K y NDCG@K con *full ranking*, enmascarando train (utilidad mínima de 02).
- El grafo de propagación se construye **sólo** con train.

## Lecturas clave
- He et al. (SIGIR 2020) LightGCN · Ying et al. (KDD 2018) PinSage · Wang et al. (SIGIR 2019) NGCF
- Barkan & Koenigstein (2016) item2vec · Caselles-Dupré et al. (RecSys 2018) *Hyperparameters Matter*
- Rendle et al. (RecSys 2020) *NCF vs MF Revisited* · Shen et al. (CIKM 2021) GF-CF

**Anterior:** [09_sequential](../09_sequential/) · **Siguiente:** [11_generative_recsys](../11_generative_recsys/)
