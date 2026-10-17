# 00 · Introducción y panorama de los sistemas de recomendación 🟢

> La puerta de entrada del curso: qué es un recomendador, por qué la industria los construye como una cascada *retrieval → ranking → re-ranking*, cómo es su ciclo de vida y qué herramientas se usan en cada etapa.

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración** | ~2,5 h de lección + 2 h de proyecto |
| **GPU** | No necesaria (≈ 0 unidades de Colab) |
| **Prerrequisitos** | Python, pandas y ML general. Ningún conocimiento de recomendación |

## 📓 Notebooks

| Notebook | Contenido | Colab |
|---|---|---|
| [`00_intro.ipynb`](00_intro.ipynb) | Lección: problema, tipos, feedback, arquitectura multi-etapa, ciclo de vida, stack, historia, primer contacto con MovieLens | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/recsys-course/00_intro/00_intro.ipynb) |
| [`00_proyecto_eda_popularidad.ipynb`](00_proyecto_eda_popularidad.ipynb) | Proyecto: EDA de MovieLens-100K, recomendadores de popularidad / nota media / media bayesiana, home por filas, mini-evaluación temporal y crítica | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/recsys-course/00_intro/00_proyecto_eda_popularidad.ipynb) |

## 🎯 Objetivos
1. Formalizar la recomendación como puntuación $s(u, i, c)$ + top-K y distinguirla de la clasificación clásica.
2. Distinguir recomendadores basados en contenido, colaborativos, híbridos y basados en conocimiento (con un ejemplo calculado a mano).
3. Diferenciar feedback explícito e implícito.
4. Dibujar y justificar la arquitectura multi-etapa y las capas offline / nearline / online.
5. Describir el ciclo de vida completo (datos → entrenamiento → evaluación → A/B → serving → monitoreo → reentreno).
6. Situar el stack (FAISS, LightGBM, TorchRec, Feast, Kafka, Triton, MLflow…) en cada etapa.
7. Recorrer la historia: Tapestry (1992) → Amazon (2003) → Netflix Prize → YouTube DNN (2016) → HSTU / TIGER / foundation models (2023-2025).

## 📊 Visualizaciones de la lección
Matriz usuario×ítem de juguete · taxonomía de recomendadores · embudo de señales implícitas · embudo multi-etapa · coste fuerza bruta vs cascada · ciclo de vida · capas offline/nearline/online · línea temporal · distribución de ratings, long tail y actividad de MovieLens.

## 📦 Datos
- **MovieLens-100K** (GroupLens): <https://files.grouplens.org/datasets/movielens/ml-100k.zip>.
- Se carga con `cinematch_data.load_movielens("100k")` (módulo [01](../01_data/)); la celda de utilidades escribe el módulo en la sesión. Sin red, genera datos sintéticos con el mismo esquema.

## 📚 Lecturas clave
- Gomez-Uribe & Hunt (2015). *The Netflix Recommender System: Algorithms, Business Value, and Innovation*. ACM TMIS. <https://doi.org/10.1145/2843948>
- Covington, Adams & Sargin (2016). *Deep Neural Networks for YouTube Recommendations*. RecSys. <https://doi.org/10.1145/2959100.2959190>
- Linden, Smith & York (2003). *Amazon.com Recommendations: Item-to-Item Collaborative Filtering*. IEEE Internet Computing.
- Amatriain & Basilico (2013). *System Architectures for Personalization and Recommendation*. Netflix Tech Blog.
- Ferrari Dacrema, Cremonesi & Jannach (2019). *Are We Really Making Much Progress?* RecSys. <https://arxiv.org/abs/1907.06902>

## ➡️ Siguiente
[01 · Datos de interacción y baselines](../01_data/)

---
*Notebooks generados con [`_tools/builders/build_00.py`](../_tools/builders/build_00.py).*
