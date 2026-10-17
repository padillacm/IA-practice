# 02 · Evaluación offline rigurosa 🟢🟡

> Media literatura de 2015-2019 no superaba a baselines simples por culpa de la evaluación. Aquí se construye el **evaluador oficial de CineMatch** (`cinematch_eval.py`), con métricas implementadas desde cero y verificadas contra `ranx`, que usan todos los módulos siguientes.

| | |
|---|---|
| **Nivel** | 🟢 Básico → 🟡 Intermedio |
| **Duración** | ~3,5 h de lección + 3 h de proyecto |
| **GPU** | No necesaria (≈ 0 unidades de Colab) |
| **Prerrequisitos** | [00](../00_intro/), [01](../01_data/) (`cinematch_data.py`) |

## 📓 Archivos

| Archivo | Contenido | Colab |
|---|---|---|
| [`02_evaluation.ipynb`](02_evaluation.ipynb) | Lección: protocolo, por qué RMSE no basta (experimento), P/R/HR/MRR/MAP/NDCG (derivación), AUC/GAUC, implementación desde cero verificada contra `ranx`, curvas @K, beyond-accuracy (cobertura, Gini, novedad, ILD, serendipia), bootstrap y tests pareados, **sampled metrics** (Krichene & Rendle 2020) con inversión de ranking, el split cambia la conclusión, crisis de reproducibilidad, *offline-online gap* | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/recsys-course/02_evaluation/02_evaluation.ipynb) |
| [`02_proyecto_libreria_evaluacion.ipynb`](02_proyecto_libreria_evaluacion.ipynb) | Proyecto: construir `cinematch_eval.py` con tests unitarios, validación contra `ranx` (< 1e-9), beyond-accuracy, RMSE/MAE/AUC/GAUC, bootstrap y test pareado, informe de baselines de CineMatch | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/padillacm/IA-practice/blob/master/recsys-course/02_evaluation/02_proyecto_libreria_evaluacion.ipynb) |
| [`cinematch_eval.py`](cinematch_eval.py) | **Módulo canónico** del evaluador (solución de referencia del proyecto) | — |

## 🎯 Objetivos
1. Demostrar por qué RMSE/MAE no bastan para listas top-K.
2. Derivar e implementar P@K, R@K, HR@K, MRR, MAP, NDCG, AUC y GAUC.
3. Verificar las métricas contra `ranx`.
4. Medir cobertura, Gini de exposición, novedad, diversidad y calibración.
5. Cuantificar incertidumbre (bootstrap) y significancia (test pareado).
6. Explicar por qué las *sampled metrics* son inconsistentes.
7. Aplicar una checklist de reproducibilidad y razonar sobre el *offline-online gap*.

## 🔌 Interfaz de `cinematch_eval.py` (contrato para el resto del curso)

**Entradas**: `recs: dict[user_id -> list[item_id]]` ordenada (posición 0 = mejor) · `test: DataFrame` con `user_id, item_id` (+ columna opcional de relevancia graduada vía `rel_col`, p. ej. `"rating"`).

| Función | Qué devuelve |
|---|---|
| `evaluate(recs, test, k=10, metrics=("precision","recall","hit_rate","mrr","map","ndcg"), rel_col=None, train=None, items=None, exp_gain=False, ap_denominator="rel") -> dict` | Medias sobre **todos** los usuarios de `test` con claves `"ndcg@10"`, etc. Con `train` añade `coverage@k`, `gini@k`, `novelty@k`; con `items` también `ild@k` y `miscal_kl@k`. |
| `evaluate_per_user(recs, test, k=10, metrics=..., rel_col=None, exp_gain=False, ap_denominator="rel") -> DataFrame` | Una fila por usuario de test (índice `user_id`); para IC y tests pareados. |
| `precision_at_k, recall_at_k, hit_rate_at_k, mrr_at_k, average_precision_at_k, ndcg_at_k` | Métricas por usuario `(rec, rel, k)`; `rel` = `set` o `dict` (graduada, solo NDCG). |
| `catalog_coverage, gini_index, novelty, intra_list_diversity, miscalibration_kl` | Beyond-accuracy. |
| `rmse, mae, auc_score, gauc` | Métricas de *scoring* (explícito / CTR). |
| `bootstrap_ci(values, n_boot=2000, alpha=0.05, seed=42) -> (media, lo, hi)` | IC percentil sobre usuarios. |
| `paired_bootstrap_test(a, b, n_boot=10000, seed=42) -> {"diff","ci_low","ci_high","p_value"}` | Test pareado (mismos usuarios). |
| `to_ranx(recs, test, rel_col=None) -> (Qrels, Run)` | Puente con `ranx` para verificar o usar `ranx.compare`. |

**Convenciones** (idénticas a `ranx`/`trec_eval`): full ranking (nunca sampled metrics); un usuario sin recomendaciones cuenta 0; `precision@k` divide por `k`; AP divide por \|relevantes\| (`ap_denominator="min"` → min(k, \|rel\|)); NDCG con ganancia lineal (`exp_gain=True` → 2^r − 1, = `ndcg_burges` de ranx).

**Uso estándar desde otro módulo (Colab)**:
```python
!wget -q https://raw.githubusercontent.com/padillacm/IA-practice/master/recsys-course/01_data/cinematch_data.py
!wget -q https://raw.githubusercontent.com/padillacm/IA-practice/master/recsys-course/02_evaluation/cinematch_eval.py
import pandas as pd
import cinematch_data as cd
from cinematch_eval import evaluate, evaluate_per_user, bootstrap_ci, paired_bootstrap_test

data = cd.prepare_cinematch("1m")
train_full = pd.concat([data["train"], data["val"]])
recs = cd.recommend_popular(train_full, data["test"].user_id.unique(), k=10)   # baseline obligatorio
print(evaluate(recs, data["test"], k=10, train=train_full, items=data["items"]))
```

## 📦 Datos
CineMatch (MovieLens-100K por defecto, 1M con `SCALE="full"`) mediante `cinematch_data.prepare_cinematch`.

## 📚 Lecturas clave
- Krichene & Rendle (2020). *On Sampled Metrics for Item Recommendation*. KDD (best paper). <https://research.google/pubs/on-sampled-metrics-for-item-recommendation/>
- Ferrari Dacrema, Cremonesi & Jannach (2019). *Are We Really Making Much Progress?* RecSys. <https://arxiv.org/abs/1907.06902>
- Rendle, Zhang & Koren (2019). *On the Difficulty of Evaluating Baselines*. <https://arxiv.org/abs/1905.01395>
- Järvelin & Kekäläinen (2002). *Cumulated Gain-Based Evaluation of IR Techniques*. ACM TOIS.
- Cremonesi, Koren & Turrin (2010). *Performance of Recommender Algorithms on Top-N Recommendation Tasks*. RecSys.
- Bassani (2022). *ranx*. ECIR. <https://github.com/AmenRa/ranx>

## ➡️ Siguiente
Bloque II: [03 · Basado en contenido y embeddings](../03_content_based/)

---
*Notebooks generados con [`_tools/builders/build_02.py`](../_tools/builders/build_02.py).*
