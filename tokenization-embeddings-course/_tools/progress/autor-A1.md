# Progreso: autor-A1
Agente: Autor A1 · Módulos: 00–02
- [x] Módulo 00_intro: README + lección + proyecto + build_00.py OK + commit/push
- [x] Módulo 01_unicode_bytes: README + lección + proyecto + build_01.py OK + commit/push
- [ ] Módulo 02_bpe_desde_cero: README + lección + proyecto + build_02.py OK + commit/push
- [ ] check_course.py OK + informe final

## Notas para retomar
- Entorno: HF, Wikipedia, unicode.org, openaipublic (vocabularios tiktoken) BLOQUEADOS; arXiv, raw.githubusercontent.com, PyPI funcionan. GPT-2 vocab verificado por SHA-256 desde github graykode/gpt-2-Pytorch (fallback en a1_common.SRC_GPT2).
- 00 hecho: utilidades canónicas en `_tools/builders/poliglota_utils.py` (+ `poliglota_src/`): src_corpus_cells(), SRC_METRICS, SRC_BM25. Ejecutado con nbclient (/tmp/runnb.py): lección y proyecto OK con datos sintéticos.
- Umbrales 00 (sintético, fast_dev, n=110): all 0.878, es 0.982, en 0.932, code 0.668 (0.606 base).
- 01 hecho (74 celdas lección con caja Ruta núcleo; 4 Gemini IMG; proyecto con inyector `contaminar` + normalizar). Umbrales 01 (sintético): recall/prec 1.0 → umbral 0.95/0.90; nDCG limpio .955/sucio .894/norm .955; tokens ratio 1.049.
- Ejecutar notebooks para probar: `/tmp/runnb.py <nb> <timeout>` (nbclient, cwd = scratchpad/run para no ensuciar el repo con json de salida).
- Siguiente: 02 (build_02.py). Plan 02: BPE a mano (Sennrich toy low/lower/newest/widest), byte-level, regex GPT-2/cl100k/o200k (patrones de tiktoken 0.14 openai_public.py), entrenamiento incremental (pair counts + índice invertido pair→words), encode por rank, verificación vs tiktoken (Encoding con mis merges) y HF tokenizers; GPT-2 real vía get_gpt2_encoding + merges de vocab.bpe; VID-01 merges.
