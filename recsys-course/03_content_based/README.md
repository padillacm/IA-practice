# 03 · Recomendación basada en contenido

🟢→🟡 · 3–4 h (lección) + 3–5 h (proyecto) · GPU T4 recomendada (≈ 1–2 unidades de Colab)

Primer recomendador **personalizado** del curso: describimos cada película por su contenido
(géneros, sinopsis, póster) y recomendamos lo que se parece a tu historial.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`03_content_based.ipynb`](03_content_based.ipynb) | TF-IDF y BM25 desde cero · perfiles de usuario (Rocchio centrado) · embeddings BGE/E5/GTE con sentence-transformers · anisotropía y centrado · UMAP del espacio semántico · CLIP (open_clip) para pósters y búsqueda texto→imagen · híbrido contenido+popularidad · cold start de ítems |
| [`03_proyecto_more_like_this.ipynb`](03_proyecto_more_like_this.ipynb) | Fila «Más como esta» de CineMatch: fusión géneros+texto+póster+año evaluada con co-consumo (CoWatch-HR@10) y cold start |

## Objetivos
- Construir y evaluar recomendadores de contenido con métricas top-K en split temporal.
- Usar encoders de texto modernos y CLIP; entender cuándo el contenido gana (cold start) y cuándo pierde (ítems warm).
- Diseñar híbridos simples sin fuga de información (pesos en validación).

## Datasets
- **MovieLens 1M** (GroupLens; espejo en GitHub como fallback).
- **Sinopsis + pósters TMDB** vía [M³L](https://github.com/giuspillo/M3L_10M_20M) (Spillo et al., 2026), commit fijado; fallback: Kaggle *The Movies Dataset* (`rounakbanik/the-movies-dataset`) o solo título+géneros.
- Uso solo educativo/investigación (licencia MovieLens).

## Lecturas clave
- Lops et al. (2011), *Content-based Recommender Systems: State of the Art and Trends*.
- Robertson & Zaragoza (2009), *BM25 and Beyond*.
- Radford et al. (2021), *CLIP*; Wang et al. (2022), *E5*; Xiao et al. (2023), *BGE*.
- van den Oord et al. (2013), *Deep content-based music recommendation*; Volkovs et al. (2017), *DropoutNet*.

## Conexión con CineMatch
Este módulo produce la fila «Más como esta» y la fuente de candidatos para **estrenos**. En 04/05
añadimos la señal colaborativa; en 08 indexaremos estos embeddings en FAISS.

Los notebooks se generan con `python recsys-course/_tools/builders/build_03.py`.
