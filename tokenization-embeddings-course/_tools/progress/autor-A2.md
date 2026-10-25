# Progreso: autor-A2
Agente: Autor A2 · Módulos: 03–05
- [x] Módulo 03_wordpiece_unigram_sentencepiece: README + lección + proyecto + build_03.py OK + commit/push
- [x] Módulo 04_diseno_tokenizers_modernos: README + lección + proyecto + build_04.py OK + commit/push
- [x] Módulo 05_patologias_robustez: README + lección + proyecto + build_05.py OK + commit/push
- [x] check_course.py OK (sin problemas en 03-05) + informe final

## Notas para retomar
- Entorno: HF/Wikipedia/openaipublic bloqueados por proxy; sí funcionan GitHub raw (nltk_data: Europarl ES/EN, UDHR), PyPI, npm, arxiv. Para probar tiktoken offline: ranks de js-tiktoken (npm) convertidos a .tiktoken en TIKTOKEN_CACHE_DIR (scratchpad/tikcache; hash sha256 verificado).
- Helpers propios: builders/_a2_common.py (celdas corpus/paralelo/métricas, strings). Test local de notebooks: scratchpad/run_nb.py (exec de celdas).
- Módulo 03 hecho: lección 84 celdas (4 Gemini: IMG-01/02/03, VID-01; 7 gráficos), proyecto 31 celdas, rúbrica 17/17 con solución (BM25 nDCG≈0.95, fert_es BPE 1.46, F1 morf ES unigram 0.42).
- Siguiente: 04 (benchmark fertilidad/paridad: carga_paralelo ya en _a2_common; tiktoken r50k/cl100k/o200k offline ok; mini paralelo a mano 12 idiomas), luego 05 (torch+transformers instalados; sin GPT-2 -> modelo mini entrenado local como fallback).

- Módulo 04 hecho: lección 62 celdas (4 Gemini: IMG-01/02/03, VID-01; 7 gráficos), proyecto 29 celdas, rúbrica 16/16 (mejor J 269 vs natural 303; hindi cl100k 4.9x). Paralelo = mini conjunto a mano (HF bloqueado). Siguiente: 05 (patologías; torch+transformers instalados, sin GPT-2 -> mini LM local de fallback).

- Módulo 05 hecho: lección 73 celdas (4 Gemini: IMG-01/02/03, VID-01; 10 gráficos), proyecto 27 celdas, rúbrica 19/19 (precisión@100=1.00, recall intrusos@100=0.42). Banco MiniGPT local (HF bloqueado); ruta GPT-2 real solo verificada con un GPT2 aleatorio (API) -> sin probar con pesos reales.
