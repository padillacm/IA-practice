# Progreso: autor-A2
Agente: Autor A2 · Módulos: 03–05
- [x] Módulo 03_wordpiece_unigram_sentencepiece: README + lección + proyecto + build_03.py OK + commit/push
- [ ] Módulo 04_diseno_tokenizers_modernos: README + lección + proyecto + build_04.py OK + commit/push
- [ ] Módulo 05_patologias_robustez: README + lección + proyecto + build_05.py OK + commit/push
- [ ] check_course.py OK + informe final

## Notas para retomar
- Entorno: HF/Wikipedia/openaipublic bloqueados por proxy; sí funcionan GitHub raw (nltk_data: Europarl ES/EN, UDHR), PyPI, npm, arxiv. Para probar tiktoken offline: ranks de js-tiktoken (npm) convertidos a .tiktoken en TIKTOKEN_CACHE_DIR (scratchpad/tikcache; hash sha256 verificado).
- Helpers propios: builders/_a2_common.py (celdas corpus/paralelo/métricas, strings). Test local de notebooks: scratchpad/run_nb.py (exec de celdas).
- Módulo 03 hecho: lección 84 celdas (4 Gemini: IMG-01/02/03, VID-01; 7 gráficos), proyecto 31 celdas, rúbrica 17/17 con solución (BM25 nDCG≈0.95, fert_es BPE 1.46, F1 morf ES unigram 0.42).
- Siguiente: 04 (benchmark fertilidad/paridad: carga_paralelo ya en _a2_common; tiktoken r50k/cl100k/o200k offline ok; mini paralelo a mano 12 idiomas), luego 05 (torch+transformers instalados; sin GPT-2 -> modelo mini entrenado local como fallback).
