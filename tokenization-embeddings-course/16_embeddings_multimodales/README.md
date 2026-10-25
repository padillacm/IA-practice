# 16 · Embeddings multimodales 🟠

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
| [`16_embeddings_multimodales.ipynb`](16_embeddings_multimodales.ipynb) | Lección: CLIP e InfoNCE simétrica y SigLIP (sigmoide) desde cero, modality gap **medido** (cono, temperatura, índice mixto), SigLIP 2, ColPali/ViDoRe con MaxSim sobre patches (OCR vs visual vs vector medio), coste de almacenamiento, embeddings unificados (Gemini Embedding 2, Jina v4, VLM2Vec), audio y vídeo, árbol de decisión | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/tokenization-embeddings-course/16_embeddings_multimodales/16_embeddings_multimodales.ipynb) |
| [`16_proyecto_embeddings_multimodales.ipynb`](16_proyecto_embeddings_multimodales.ipynb) | Proyecto «Políglota Visual»: capturas sintéticas de la documentación, estudiante visual destilado del texto, MaxSim, evaluación con IC y coste; plantilla con TODOs, pistas 🪜, rúbrica calibrada y solución tras ⛔ SPOILER | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/tokenization-embeddings-course/16_embeddings_multimodales/16_proyecto_embeddings_multimodales.ipynb) |
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
