# Módulo 13 · Dense vs sparse vs late interaction

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU:** T4 opcional (CPU en `FAST_DEV_RUN`)

Un solo vector por texto no basta: los identificadores exactos piden **índice invertido**, las paráfrasis piden **semántica** y la precisión fina
pide **interacción por token**. Este módulo construye cada pieza desde cero y las combina en un pipeline **híbrido**: BM25, sparse aprendido (SPLADE),
**MaxSim/ColBERT** (con compresión residual y un PLAID mini), **MUVERA**, BGE-M3 (tres modos), **fusión** (RRF y combinación convexa sin fuga de tuning),
**rerankers cross-encoder** con presupuesto de latencia y **late chunking**.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`13_dense_sparse_late_interaction.ipynb`](13_dense_sparse_late_interaction.ipynb) | Lección: BM25 desde cero (matriz dispersa, verificada contra `rank_bm25`) · SPLADE (fórmula, FLOPS, `SparseEncoder`) · MaxSim vectorizado · compresión residual de ColBERTv2 · PLAID mini · BGE-M3 a mano · MUVERA (FDE) · RRF y combinación lineal con CV · cross-encoder y latencia vs K · late chunking · costes de almacenamiento · 🏭 producción · 🧠 secretos · autoevaluación |
| [`13_proyecto_dense_sparse_late_interaction.ipynb`](13_proyecto_dense_sparse_late_interaction.ipynb) | Proyecto: retrieval híbrido de Políglota con fusión y reranking. Plantilla con TODOs, pistas 🪜, autocomprobación de rúbrica y solución tras ⛔ SPOILER |

## Objetivos
1. Implementar BM25 y MaxSim desde cero y verificarlos contra librerías/fórmula ingenua.
2. Entender SPLADE, ColBERTv2/PLAID y MUVERA y medir sus trade-offs.
3. Fusionar retrievers con RRF y combinación convexa sin fuga de tuning.
4. Montar recuperar → fusionar → reordenar y elegir K desde un presupuesto de latencia.

## Datasets
Banco canónico (`carga_corpus()` del módulo 00: Wikipedia ES/EN + código; sintético con aviso si no hay acceso) y un **mini golden set de paráfrasis ES↔EN↔código**
(29 conceptos, 58 queries) escrito a mano para diagnosticar dónde gana cada retriever.

## Lecturas clave (verificadas)
- Khattab & Zaharia (2020), *ColBERT* (2004.12832) · Santhanam et al. (2021), *ColBERTv2* (2112.01488) · *PLAID* (2205.09707).
- Dhulipala et al. (2024), *MUVERA* (2405.19504).
- Formal et al., *SPLADE* (2107.05720), *SPLADE-v3* (Lassance et al., 2403.06789).
- Chen et al. (2024), *BGE-M3* (2402.03216) · Günther et al. (2024), *Late Chunking* (2409.04701).
- Bruch, Gai, Ingber (2022), *An Analysis of Fusion Functions for Hybrid Retrieval* (2210.11934).

## Conexión con Políglota
El módulo 12 aporta el retriever denso; aquí lo combinas con BM25 y late interaction y añades un reranker. El módulo 14 indexará estos vectores con ANN.

*Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_13.py` (desde la raíz del repo). Estado del arte a octubre de 2026.*
