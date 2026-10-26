# 17 · Interpretabilidad y geometría de los embeddings 🔴

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
| [`17_interpretabilidad_geometria.ipynb`](17_interpretabilidad_geometria.ipynb) | Lección: probing y control tasks (Hewitt), representación lineal (steering por diferencia de medias, borrado lineal), dimensiones dominantes (Timkey; Kovaleva), superposición (Toy Models), **TopK SAE y ReLU+L1 desde cero** con recuperación de características plantadas, features de Políglota (pureza vs k-means/PCA, estabilidad entre semillas), steering con SAE vs baseline, qué codifica un embedding, inversión (vec2text) y trade-off privacidad–utilidad | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/tokenization-embeddings-course/17_interpretabilidad_geometria/17_interpretabilidad_geometria.ipynb) |
| [`17_proyecto_interpretabilidad_geometria.ipynb`](17_proyecto_interpretabilidad_geometria.ipynb) | Proyecto: SAE sobre embeddings de `carga_corpus` y análisis de features interpretables; plantilla con TODOs, pistas 🪜, rúbrica calibrada y solución tras ⛔ SPOILER | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/tokenization-embeddings-course/17_interpretabilidad_geometria/17_proyecto_interpretabilidad_geometria.ipynb) |
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
