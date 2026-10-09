# 01 · Datos de interacción, sesgos, splits y baselines 🟢

> Los errores más graves en recomendación están en los datos y en cómo se parten. Aquí se construye el **pipeline de datos de CineMatch** (`cinematch_data.py`) que reutiliza todo el curso.

| | |
|---|---|
| **Nivel** | 🟢 Básico |
| **Duración** | ~3 h de lección + 2,5 h de proyecto |
| **GPU** | No necesaria (≈ 0 unidades de Colab) |
| **Prerrequisitos** | [00](../00_intro/) |

## 📓 Archivos

| Archivo | Contenido | Colab |
|---|---|---|
| [`01_data.ipynb`](01_data.ipynb) | Lección: log → matriz, scipy.sparse (COO/CSR/CSC), long tail (Lorenz, Gini), sesgos (MNAR, exposición, posición, popularidad y *feedback loop*) con simulaciones, señales implícitas y confianza, k-core, splits aleatorio / leave-one-out / temporal global y *leakage*, baselines (global, reciente, decaída, por segmento), negativos y falsos negativos, catálogo de 17 datasets | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/recsys-course/01_data/01_data.ipynb) |
| [`01_proyecto_pipeline_datos.ipynb`](01_proyecto_pipeline_datos.ipynb) | Proyecto: pipeline reproducible (config con hash, split temporal, k-core solo en train, validaciones, parquet + `metadata.json` con sha256, baselines ajustados en val, informe de leakage) y comprobación contra el módulo canónico | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/recsys-course/01_data/01_proyecto_pipeline_datos.ipynb) |
| [`cinematch_data.py`](cinematch_data.py) | **Módulo canónico** del pipeline de datos (lo usan los módulos 02 en adelante) | — |

## 🎯 Objetivos
1. Representar interacciones con matrices dispersas y estimar su memoria.
2. Cuantificar la long tail.
3. Explicar y simular los sesgos de selección (MNAR), exposición, posición y popularidad.
4. Construir señales implícitas (play, % visto, confianza de Hu et al.).
5. Medir falsos negativos según la estrategia de muestreo.
6. Implementar splits y demostrar el leakage temporal.
7. Construir y ajustar baselines fuertes.
8. Elegir datasets públicos por dominio.

## 🔌 Interfaz de `cinematch_data.py` (contrato para el resto del curso)

**Esquema**: `ratings`/interacciones con columnas `user_id` (int64), `item_id` (int64), `rating` (float32), `timestamp` (int64, segundos Unix), ordenadas por tiempo. `items`: `item_id`, `title`, `year`, `genres` (`"Action|Comedy"`). **Recomendaciones**: `dict[user_id -> list[item_id]]` ordenada (posición 0 = mejor).

| Función | Qué hace |
|---|---|
| `load_movielens(size="100k", data_dir="data", synthetic_fallback=True) -> (ratings, items)` | Descarga de GroupLens (`"100k"`, `"1m"`, `"latest-small"`, `"25m"`, `"32m"`). Si GroupLens no responde, 100k y 1m se bajan de un espejo público en GitHub; sin red → datos sintéticos con el mismo esquema (y un aviso). |
| `load_users(size)` | Demografía (`user_id, age, gender, occupation, zip`) para 100k/1m; si no, `None`. |
| `make_synthetic_movielens(n_users, n_items, n_ratings, seed)` | Generador sintético (long tail, gustos por género, sesgos, estrenos). |
| `dedup_interactions(df, keep="last")` | Un evento por (usuario, ítem). |
| `to_implicit(ratings, threshold=4.0)` | Positivos implícitos: `rating >= threshold` (convención del curso). |
| `filter_k_core(df, min_user=5, min_item=5)` | k-core iterativo. |
| `random_split(df, test_frac=0.2, seed=42)` | Split aleatorio (solo como contraejemplo). |
| `leave_one_out_split(df, n_test=1)` | Últimas `n_test` interacciones de cada usuario a test. |
| `temporal_split(df, val_frac=0.1, test_frac=0.1, drop_cold_users=True, drop_cold_items=True) -> (train, val, test)` | **Split temporal global** por cuantiles de `timestamp`. |
| `prepare_cinematch(size="100k", threshold=4.0, min_user=5, min_item=5, val_frac=0.1, test_frac=0.1, out_dir=None) -> dict` | **Pipeline estándar en una llamada**: carga → dedup → implícito → split temporal → k-core *solo en train* → val/test restringidos a usuarios e ítems de train. Devuelve `{"train", "val", "test", "items", "ratings"}`. |
| `build_mappings(df)` / `to_csr(df, user2idx=None, item2idx=None, value_col=None) -> (X, user2idx, item2idx)` | Matriz usuario×ítem CSR (1.0 por interacción si `value_col=None`). |
| `popularity_ranking(train, window_days=None, half_life_days=None)` | Ítems ordenados por popularidad (global, ventana o decaimiento). |
| `recommend_popular(train, users, k=10, exclude_seen=True, window_days=None, half_life_days=None)` | Baseline de popularidad (global / reciente). |
| `recommend_popular_by_segment(train, users, segment_of, k=10)` | Popularidad por segmento (`segment_of`: dict `user_id -> segmento`). |
| `recommend_random(train, users, k=10, seed=42)` | Suelo absoluto. |
| `save_splits(out_dir, **frames)` / `load_splits(out_dir)` | Persistencia en parquet. |

**Convención de evaluación**: ajusta hiperparámetros con `train` → `val`; para la evaluación final, entrena con `train + val` y evalúa en `test`, excluyendo los ítems ya vistos.

**Cómo usarlo desde otro módulo (Colab)**:
```python
!wget -q https://raw.githubusercontent.com/padillacm/IA-practice/master/recsys-course/01_data/cinematch_data.py
import cinematch_data as cd
data = cd.prepare_cinematch("1m")
```
(Los notebooks del Bloque I llevan además una copia embebida del módulo para funcionar sin red.)

## 📦 Datasets
- **MovieLens-100K / 1M** (<https://files.grouplens.org/datasets/movielens/>), `SCALE="small" | "full"`.
- Catálogo comentado en la lección: MovieLens, Netflix Prize, Amazon Reviews 2023, Yelp, MIND, KuaiRec, KuaiRand, RetailRocket, Yoochoose, H&M, OTTO, Last.fm, LFM-2b (retirado), Goodbooks-10k, Criteo, Avazu, Open Bandit Dataset.

## 📚 Lecturas clave
- Ji, Sun, Zhang & Li (2023). *A Critical Study on Data Leakage in Recommender System Offline Evaluation*. ACM TOIS. <https://arxiv.org/abs/2010.11060>
- Chen et al. (2023). *Bias and Debias in Recommender System: A Survey and Future Directions*. ACM TOIS. <https://arxiv.org/abs/2010.03240>
- Hu, Koren & Volinsky (2008). *Collaborative Filtering for Implicit Feedback Datasets*. ICDM.
- Marlin & Zemel (2009). *Collaborative Prediction and Ranking with Non-Random Missing Data*. RecSys.
- Harper & Konstan (2015). *The MovieLens Datasets: History and Context*. ACM TiiS.

## ➡️ Siguiente
[02 · Evaluación offline rigurosa](../02_evaluation/)

---
*Notebooks generados con [`_tools/builders/build_01.py`](../_tools/builders/build_01.py).*
