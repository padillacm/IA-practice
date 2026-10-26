# Revisión de ejecutabilidad · Bloque B (módulos 09–20)

Revisor de ejecutabilidad B (oct-2026). Cada notebook se ejecutó de arriba abajo con `nbclient` sobre una **copia** en el
scratchpad (sin outputs ni archivos generados dentro del curso), con `FAST_DEV_RUN=True`, CPU (`CUDA_VISIBLE_DEVICES=""`),
`OMP_NUM_THREADS=2` (4 CPUs compartidas), timeout de 600 s por celda, un notebook a la vez y `allow_errors=True` para listar
todos los fallos. La celda `!pip install` se ejecutó como `--dry-run`.

Red del entorno: Hugging Face, openaipublic y Zenodo → 403 del proxy; Wikipedia API → 403; arXiv, raw.githubusercontent.com
y PyPI → OK. En Colab las ramas oficiales deberían funcionar.

| Notebook | Tiempo | Estado | Datos | Rúbrica (solución) | Cambios |
|---|---|---|---|---|---|
| 09 lección | 233 s | OK | Sintético ES/EN (aviso ⚠️) + stdlib real; modelos del hub no disponibles → mini-GPT-2 fallback (aviso) | — | — |
| 09 proyecto | 33 s | OK | Ídem | 6/6 (gap 0.93 ≥ 0.5; fertilidad −8.9 % ≥ 5 %; bpb 2.287 ≤ 2.350 + 0.05) | — |
| 10 lección | 94 s | OK | Sintético + stdlib; mini-encoders fallback (aviso) | — | **vocabulario determinista** |
| 10 proyecto | 83 s | OK | Ídem | 6/6 (elegida 0.523 vs default 0.352 en test) | **vocabulario determinista**; referencia de R5 recalibrada |
| 11 lección | 219 s | OK (tras añadir `accelerate`) | Sintético + stdlib + mundo de juguete; mini-BERT local (aviso) | — | `accelerate` en pip; vocabulario determinista; 👀 recalibrados |
| 11 proyecto | 114 s | OK | Ídem | 6/6 (BM25 0.866 · sin entrenar 0.342 · lote 0.500 · duros 0.533) | nota de calibración con lo medido |
| 12 lección | 43 s | OK | Sintético + stdlib; embedders del hub → TF-IDF+SVD (aviso «NO representa al modelo real»); `RUN_MTEB=False` (registro de mteb sí, local) | — | pip sin `-U` |
| 12 proyecto | 27 s | OK | Ídem | 8/8 automáticas (+R9 manual); plantilla 0/8 sin romper | pip sin `-U` |
| 13 lección | 31 s | OK | Sintético + stdlib; encoders del hub → respaldos locales (aviso) | — | pip sin `-U` |
| 13 proyecto | 23 s | OK | Ídem | 8/8; plantilla 0/8 sin romper | pip sin `-U` |
| 14 lección | 114 s | OK | Sintético + stdlib; embeddings de respaldo (aviso); ScaNN opcional (no instalado, mensaje) | — | pip sin `-U` (incluía `numpy`) |
| 14 proyecto | 36 s | OK | Ídem | 6/6; plantilla 0/6 sin romper | pip sin `-U` |
| 15 lección | 76 s | OK | Sintético (HF `wikimedia/wikipedia` + CodeSearchNet → 403; aviso ⚠️); ranx real: coincide con las métricas propias (≤ 1.1e-16) | — | — |
| 15 proyecto | 7 s | OK | Ídem | 12/12 (umbrales numéricos solo con sintético + FAST_DEV_RUN; con datos reales solo estructurales) | — |
| 16 lección | 268 s | OK | Mundo de juguete de imágenes generadas (por diseño, sin descarga); `USE_REAL_MODELS=False` (CLIP/SigLIP reales opcionales) | — | — |
| 16 proyecto | 125 s | OK | Corpus sintético (HF 403, aviso ⚠️) renderizado como páginas | 11/11 (plantilla 0/11 sin romper) | — |
| 17 lección | 72 s | OK | Sintético (HF 403, aviso ⚠️); `RUN_VEC2TEXT=False` | — | — |
| 17 proyecto | 19 s | OK | Ídem | 17/17 (plantilla 0/17 sin romper) | — |
| 18 lección | 36 s | OK | Sintético + stdlib; v1/v2 = TF-IDF+SVD (aviso ⚠️); Qdrant local real (coincide con fuerza bruta 1.000) | — | — |
| 18 proyecto | 38 s | OK | Ídem | 95/95 pts automáticos (5 tests ✅); plantilla ⏳ sin romper | — |
| 19 lección | 80 s | OK | Sintético + stdlib; TF-IDF+SVD (aviso ⚠️) | — | — |
| 19 proyecto | 2 s | OK | Sin datos (design review con rúbrica en Python puro; no necesita `pip`) | 3/3 casos 100/100 (plantilla 24/100, esperado) | — |
| 20 lección | 28 s | OK | Sintético + stdlib; TF-IDF+SVD (aviso ⚠️) | — | — |
| 20 proyecto | 31 s | OK | Ídem | 95/95 pts automáticos (test nDCG@10 0.887 vs BM25 0.842); plantilla ⬜ sin romper | — |

Total bloque B en FAST_DEV_RUN/CPU: ≈ 31 min (24 notebooks). Todas las celdas TODO de los proyectos están envueltas
(`NotImplementedError`/excepción capturada, rúbrica con ⏳/❌/⬜), así que «Ejecutar todo» nunca se rompe.

## Cambios aplicados (en builders; notebooks regenerados)
- **10 · reproducibilidad del whitening** (`build_10.py`): la causa de que el efecto del whitening cambiara de signo entre
  ejecuciones era `BertWordPieceTokenizer.train_from_iterator`: el WordPiece trainer de `tokenizers` rompe empates según el
  orden de un `HashMap` de Rust, distinto en cada proceso (medido: 5 vocabularios distintos en 5 procesos con el mismo
  corpus; `BpeTrainer` con alfabeto byte-level y `UnigramTrainer` sí son deterministas). Ahora `vocab_wordpiece_determinista`
  entrena Unigram y lo convierte a la convención WordPiece (`▁x` → `x`, `x` → `##x`, más todos los caracteres y `##`
  caracteres). Dos ejecuciones completas de lección y proyecto dieron cifras **idénticas**. La rúbrica R5 ya no dependía
  del signo (test ≥ default − 0.03); se actualizaron su referencia, la nota 👀 de la lección, el secreto 4 y el README.
- **11 · reproducibilidad** (`build_11.py`): mismo arreglo del vocabulario en el fallback de sentence-transformers
  (`modelo_st`; además `BertConfig(vocab_size=len(vocab))`). Lección y proyecto re-ejecutados: cifras **idénticas** (el
  resto ya estaba sembrado; el mundo de juguete y el BPE del proyecto eran deterministas).
- **11 lección · `accelerate`**: `SentenceTransformerTrainer` falla sin `accelerate>=1.1` (ImportError) y la celda LoRA sin
  `peft`; ambos vienen en Colab, pero el `pip` solo pedía `peft`: añadido `accelerate`.
- **11 lección · 👀 negativos duros**: el texto afirmaba «duros sin filtrar < solo lote < duros limpios» (prototipo de 300
  pasos: 0.84/0.88/0.92); en `FAST_DEV_RUN` (200 pasos) lo medido es 0.766 · 0.728 · 0.754 (orden distinto, dentro del
  ruido). El texto y el secreto 1 lo dicen ahora; MNRL actualizado a lo medido (0.40 → 0.58).
- **12–14 · `!pip install -q -U …` → sin `-U`** (`build_12.py`, `build_13.py`, `build_14.py`): en Colab `-U` actualizaba
  `transformers`, `sentence-transformers` y (en el 14) **`numpy`** preinstalados; actualizar numpy en caliente rompe
  paquetes compilados contra la versión de Colab y obliga a reiniciar el entorno. Sin `-U` solo se instala lo que falta
  (`mteb`, `rank_bm25`, `faiss-cpu`); resuelven con `--dry-run`.

## Comprobado sin cambios
- `pip install` de todos los notebooks resuelve con `--dry-run`; ninguno usa ya `-U`. Los paquetes que piden (`peft`,
  `accelerate`, `mteb`, `ranx`, `rank_bm25`, `faiss-cpu`, `qdrant-client`) no fuerzan versiones de torch/numpy/transformers.
- Avisos de datos sintéticos y de modelos de respaldo visibles en todos los notebooks que los usan (09–14 y 18–20 vía
  `carga_corpus` con Wikipedia API + CodeSearchNet → stdlib real; 15–17 vía HF `datasets` → sintético).
- Rúbricas de las soluciones: todas en verde con lo medido; no hubo que recalibrar umbrales (la R5 del 10 y la R5 del 11
  ya eran tolerantes al signo; las del 15–17 solo exigen cifras exactas con corpus sintético + `FAST_DEV_RUN`).
- Reproducibilidad: 10 y 11 re-ejecutados dos veces con salidas idénticas tras el arreglo del vocabulario.

## Pendientes
- **Ningún notebook del bloque B corrió con datos reales**: Wikipedia (API y HF) y todos los modelos del hub (GPT-2,
  e5, MiniLM, CLIP/SigLIP, ColPali) están bloqueados aquí; el código real de 09–14/18–20 sí es real (stdlib de Python).
  Verificar en Colab las ramas oficiales y los umbrales relativos con modelos reales.
- 15–17 no tienen espejo automático (solo la indicación manual de `HF_ENDPOINT`); podrían reutilizar el respaldo de
  stdlib para la parte de código como 09–14.
- `16` lección es la más lenta (268 s, 6 entrenamientos CLIP/SigLIP de juguete de ~25 s): aceptable.
