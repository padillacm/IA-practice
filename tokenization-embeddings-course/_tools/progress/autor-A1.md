# Progreso: autor-A1
Agente: Autor A1 · Módulos: 00–02
- [x] Módulo 00_intro: README + lección + proyecto + build_00.py OK + commit/push
- [ ] Módulo 01_unicode_bytes: README + lección + proyecto + build_01.py OK + commit/push
- [ ] Módulo 02_bpe_desde_cero: README + lección + proyecto + build_02.py OK + commit/push
- [ ] check_course.py OK + informe final

## Notas para retomar
- Entorno: HF, Wikipedia, unicode.org, openaipublic (vocabularios tiktoken) BLOQUEADOS; arXiv, raw.githubusercontent.com, PyPI funcionan. GPT-2 vocab verificado por SHA-256 desde github graykode/gpt-2-Pytorch (fallback en a1_common.SRC_GPT2).
- 00 hecho: utilidades canónicas en `_tools/builders/poliglota_utils.py` (+ `poliglota_src/`): src_corpus_cells(), SRC_METRICS, SRC_BM25. Ejecutado con nbclient (/tmp/runnb.py): lección y proyecto OK con datos sintéticos.
- Umbrales 00 (sintético, fast_dev, n=110): all 0.878, es 0.982, en 0.932, code 0.668 (0.606 base).
- Siguiente: 01 (build_01.py), helpers de texto en `_tools/builders/a1_common.py`.
