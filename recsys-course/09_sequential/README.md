# Módulo 09 · Recomendación secuencial y por sesión

**Bloque IV — Estado del arte** · Nivel 🟠 Avanzado · Lección 4–5 h + proyecto 3–4 h · GPU L4 (A100 para el barrido completo) · ≈ 3–5 unidades de Colab

Pasamos de «bolsas de ítems» a **secuencias**: el recomendador predice el siguiente ítem a partir del historial ordenado, igual que un modelo de lenguaje predice la siguiente palabra. Es la base de los recomendadores generativos del módulo 11.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`09_sequential.ipynb`](09_sequential.ipynb) | Lección: Markov/FPMC, GRU4Rec, SASRec y BERT4Rec **desde cero** en PyTorch con una interfaz común; derivación de la **sobreconfianza** de la BCE con negativos y de **gBCE**; comparación *full softmax* vs *sampled softmax* vs BCE vs gBCE; barrido de nº de negativos; mapas de atención causal; t-SNE de embeddings; recomendación **por sesión** en RetailRocket; SASRec con **RecTools**; producción (Alibaba BST/SIM, Kuaishou TWIN, Pinterest PinnerFormer, Meta, Netflix). |
| [`09_proyecto_sasrec_cinematch.ipynb`](09_proyecto_sasrec_cinematch.ipynb) | Proyecto: fila «Porque acabas de ver…» de CineMatch. Baselines, GRU4Rec y SASRec (BCE / gBCE / CE) en GPU, IC *bootstrap* del ΔNDCG y recomendación a producto. Plantilla con TODOs + solución de referencia. |

## Objetivos
- Formular la recomendación secuencial y por sesión y elegir protocolo de evaluación (*leave-one-out*, *full ranking*, split temporal).
- Implementar GRU4Rec, SASRec y BERT4Rec desde cero.
- Explicar con matemáticas por qué **la pérdida importa más que la arquitectura** (Klenitskiy & Vasilev 2023; Petrov & Macdonald 2023).
- Evitar las trampas clásicas: métricas muestreadas, fugas en la máscara causal, *baselines* mal implementados.

## Datasets
- **MovieLens-1M** (GroupLens, `files.grouplens.org/datasets/movielens/ml-1m.zip`) — benchmark estándar secuencial.
- **RetailRocket** (Kaggle `retailrocket/ecommerce-dataset`, requiere `kaggle.json`) — sesiones de e-commerce. Alternativas: Yoochoose (RecSys Challenge 2015), Diginetica (CIKM Cup 2016).
- Si no hay red/credenciales, los notebooks generan datos sintéticos con estructura secuencial (los números no son comparables con papers).

## Convenciones
- Ítems re-indexados a `1..n_items`, **0 = padding**, `n_items + 1` = `[MASK]` (BERT4Rec). Padding a la **izquierda**.
- Interfaz de modelo: `encode(seq) -> [B, L, d]` + `item_emb` compartido como capa de salida.
- `evaluate_next_item(score_fn, histories, targets)` — HR@K y NDCG@K con *full ranking* (utilidad mínima de 02, incluida en cada notebook).
- `FAST_DEV_RUN = True` para iterar rápido en CPU; `False` para el experimento completo en GPU.

## Lecturas clave
- Kang & McAuley (2018) SASRec · Sun et al. (2019) BERT4Rec · Hidasi et al. (2016) GRU4Rec
- Petrov & Macdonald (RecSys 2023) gSASRec · Klenitskiy & Vasilev (RecSys 2023) *Turning Dross Into Gold Loss*
- Krichene & Rendle (KDD 2020) *On Sampled Metrics* · Hidasi & Czapp (RecSys 2023) *third-party implementations*
- Pancha et al. (KDD 2022) PinnerFormer

**Siguiente:** [10_graph](../10_graph/) · [11_generative_recsys](../11_generative_recsys/)
