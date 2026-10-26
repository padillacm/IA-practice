# Progreso: autor-A4
Agente: Autor A4 · Módulos: 09–11
- [x] Módulo 09_capa_embedding_llm: README + lección + proyecto + build_09.py OK + commit/push
- [x] Módulo 10_embeddings_contextuales_oraciones: README + lección + proyecto + build_10.py OK + commit/push
- [x] Módulo 11_aprendizaje_contrastivo: README + lección + proyecto + build_11.py OK + commit/push
- [x] check_course.py OK + informe final

## Notas para retomar
- Entorno: HF/Kaggle/Wikipedia BLOQUEADOS por el proxy (403); PyPI y arxiv.org sí. Sin modelos preentrenados: todo se prueba con el FALLBACK (corpus sintético + mini-modelos entrenados in situ). Los datos reales/modelos reales NO se pudieron probar aquí.
- Venv de pruebas: `/tmp/a4venv` (system-site-packages + transformers 5.20, sentence-transformers 6.2, peft 0.21). Ejecutar con `OMP_NUM_THREADS=1`.
- Celdas compartidas (corpus sintético/real, métricas, evaluación): `_tools/builders/a4_common.py` (se copian dentro de cada notebook).
- Runner de pruebas de notebooks: `runnb.py` en el scratchpad (ejecuta celdas de código en un namespace; no es parte del repo).
- Referencias ya verificadas en arxiv.org (ids): 1608.05859 1611.01462 1301.3781 1711.03953 1907.12009 2405.05417 2305.18294 2109.04404 2312.16903 2403.08295 2408.00118 2010.12821 1702.01417 1810.04805 1908.10084 2011.05864 2103.15316 2004.09813 2202.08904 2212.09741 2212.03533 2401.00368 2106.01183 2210.07316 2403.05440 2201.10005 2104.08663 2401.12143 2311.05928 1909.00512 1807.03748 2002.05709 2104.08821 2004.04906 2005.10242 2007.00808 2104.06967 2010.08191 1705.00652 2101.06983 2106.09685 1905.06922 1811.04251 1907.13625 2012.09740 2308.03281 2309.07597 2402.01613 2402.03216 2402.09906 2405.17428 2506.05176 2010.04592 2007.00224 2004.11362 2407.15831 2403.20327 2112.09118 2508.21038 2404.07647 2111.09543 1911.03310 1901.07291 2410.10989.
- 09 HECHO: build_09.py (lección 59 celdas/23 código, 3 Gemini IMG; proyecto 18/11). Corpus = canónico de A1 (poliglota_utils). Probado completo con fallback (mini-GPT-2 + sintético). a4_common.py ahora solo tiene el "mundo de juguete" para el 11.
- 10 HECHO: build_10.py (lección 60 celdas/21 código, 4 Gemini IMG; proyecto 25/17). Fallback mini-BERT/mini-SBERT; no determinista bit a bit (texto lo explica).
- 11 HECHO: build_11.py (lección 66 celdas/29 código, 3 IMG + 1 VID; proyecto 25/16). Lección ≈ 5.3 min y proyecto ≈ 2.7 min en CPU con fallback; rúbrica 6/6.
