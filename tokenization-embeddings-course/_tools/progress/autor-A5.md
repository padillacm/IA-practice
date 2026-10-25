# Progreso: autor-A5
Agente: Autor A5 · Módulos: 12–14
- [x] Módulo 12_embedders_modernos: README + lección + proyecto + build_12.py OK + commit/push
- [x] Módulo 13_dense_sparse_late_interaction: README + lección + proyecto + build_13.py OK + commit/push
- [x] Módulo 14_indexacion_ann: README + lección + proyecto + build_14.py OK + commit/push
- [x] check_course.py OK (sin problemas en 12–14) + informe final

## Notas para retomar
- Entorno: HF/Zenodo/openai.com bloqueados (proxy); PyPI y arXiv OK. Instalados en el contenedor: torch, transformers 5.x, sentence-transformers 6.x, mteb 2.26, faiss-cpu 1.15, sklearn.
- Pruebas locales: /tmp/claude-0/.../scratch/runnb.py ejecuta las celdas; modelos diminutos locales (BERT aleatorio) para ejercitar la ruta sentence-transformers.
- Decisión: usar el carga_corpus CANÓNICO de A1 (builders/poliglota_utils.py: src_corpus_cells(), SRC_METRICS) y mis utilidades en builders/_a5_common.py (setup, ndcgs_por_query).
- Módulo 12 hecho (lección 68 celdas, proyecto 33). Rúbrica del proyecto calibrada con fallbacks TF-IDF+SVD y modelo aleatorio diminuto (SIN modelos reales: no se pudo descargar).
- Módulo 13 hecho (lección 69 celdas, 5 Gemini: 4 img + 1 video; proyecto 35). Dos bancos: canónico + mini golden de paráfrasis (en _a5_common). Probado con modelos diminutos aleatorios (rutas ST/SparseEncoder/CrossEncoder/BGE-M3 manual) y fallbacks; sin modelos reales.
- Módulo 14 hecho (lección 55 celdas: 3 imágenes + 1 vídeo Gemini; proyecto 27). Probado con FAISS real (CPU, 1 hilo) y vectores sintéticos/Políglota-fallback.
- Pendiente: check_course global + informe final.
