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
<!-- TABLA -->

## Cambios aplicados (en builders; notebooks regenerados)
- **10 · reproducibilidad del whitening** (`build_10.py`): la causa de que el efecto del whitening cambiara de signo entre
  ejecuciones era `BertWordPieceTokenizer.train_from_iterator`: el WordPiece trainer de `tokenizers` rompe empates según el
  orden de un `HashMap` de Rust, distinto en cada proceso (medido: 5 vocabularios distintos en 5 procesos con el mismo
  corpus; `BpeTrainer` con alfabeto byte-level y `UnigramTrainer` sí son deterministas). Ahora `vocab_wordpiece_determinista`
  entrena Unigram y lo convierte a la convención WordPiece (`▁x` → `x`, `x` → `##x`, más todos los caracteres y `##`
  caracteres). Dos ejecuciones completas de lección y proyecto dieron cifras **idénticas**. La rúbrica R5 ya no dependía
  del signo (test ≥ default − 0.03); se actualizaron su referencia, la nota 👀 de la lección, el secreto 4 y el README.
<!-- CAMBIOS -->
