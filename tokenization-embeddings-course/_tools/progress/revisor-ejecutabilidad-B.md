# Progreso: revisor-ejecutabilidad-B
Agente: Revisor de ejecutabilidad · Módulos: 09–20 · Informe: tokenization-embeddings-course/_tools/REVISION_EJECUTABILIDAD_B.md
- [x] 09_capa_embedding_llm (lección + proyecto ejecutados con nbclient)
- [x] 10_embeddings_contextuales_oraciones (lección + proyecto ejecutados con nbclient)
- [x] 11_aprendizaje_contrastivo (lección + proyecto ejecutados con nbclient)
- [x] 12_embedders_modernos (lección + proyecto ejecutados con nbclient)
- [x] 13_dense_sparse_late_interaction (lección + proyecto ejecutados con nbclient)
- [x] 14_indexacion_ann (lección + proyecto ejecutados con nbclient)
- [x] 15_evaluacion_retrieval (lección + proyecto ejecutados con nbclient)
- [x] 16_embeddings_multimodales (lección + proyecto ejecutados con nbclient)
- [x] 17_interpretabilidad_geometria (lección + proyecto ejecutados con nbclient)
- [x] 18_produccion (lección + proyecto ejecutados con nbclient)
- [ ] 19_playbook_elite (lección + proyecto ejecutados con nbclient)
- [ ] 20_capstone (lección + proyecto ejecutados con nbclient)
- [ ] check_course.py OK + informe final

## Notas para retomar
- (comandos lanzados y su resultado)
- Runner: `OMP_NUM_THREADS=2 <scratchpad>/bin/q.sh <nb...>` → `run_nb.py` (copia del módulo en `<scratchpad>/execB/<nb>/`, `!pip install` → `--dry-run`, FAST_DEV_RUN=True, CPU, timeout 600 s/celda, allow_errors; resumen en `execB/summary.log`).
- 09 lección: 233 s, 0 errores. Wikipedia 403 → corpus SINTÉTICO (aviso ⚠️ visible); CodeSearchNet → stdlib real; GPT-2/OPT/Pythia/SmolLM/Qwen del hub no disponibles → mini-GPT-2 fallback (aviso). pip dry-run OK. Proyecto: 33 s, 0 errores, rúbrica 6/6 ✅ (gap 0.93 ≥ 0.5; fert −8.9 % ≥ 5 %; bpb 2.287 ≤ 2.350+0.05). Sin cambios.
- Hallado (para 10/11): `BertWordPieceTokenizer.train_from_iterator` NO es determinista entre procesos (empates vía HashMap de Rust; 5 hashes distintos en 5 ejecuciones); BpeTrainer y UnigramTrainer sí. Builders 10 y 11 ya editados: vocab WordPiece desde Unigram (determinista). Builders 12–14: quitado `-U` del pip (ya regenerados, sin commit hasta su módulo).
- 10 lección: 94 s, 0 errores; proyecto 83 s, 0 errores, 6/6 ✅ (elegida mini-SBERT·mean·whitening: val 0.499 vs 0.380; test 0.523 vs 0.352). Re-ejecutados ambos: salidas IDÉNTICAS (solo cambia el tiempo). Textos de lección/R5/README actualizados. Informe iniciado.
- 11 lección: 1ª ejecución 2 errores (sin `accelerate` → Trainer ImportError; sin `peft`): instalados y `accelerate` añadido al pip. 2ª: 219 s, 0 errores; 3ª idéntica (determinista). Proyecto: 114 s, 0 errores, 6/6 ✅; 2ª ejecución idéntica. Textos 👀 de duros/MNRL recalibrados.
- 12 lección: 43 s, 0 errores (fallback TF-IDF+SVD con aviso; RUN_MTEB=False). Proyecto: 27 s, 0 errores, 8/8 ✅ (plantilla ❌/⏳ sin romper). Cambio: pip sin -U (12–14).
- 13 lección: 31 s, 0 errores. Proyecto: 23 s, 0 errores, 8/8 ✅. Cambio: pip sin -U.
- 14 lección: 114 s, 0 errores. Proyecto: 36 s, 0 errores, 6/6 ✅. Cambio: pip sin -U (numpy).
- 15 lección: 76 s, 0 errores (HF 403 → sintético con aviso; ranx coincide). Proyecto: 7 s, 0 errores, 12/12 ✅. Sin cambios.
- 16 lección: 268 s, 0 errores (mundo de juguete; USE_REAL_MODELS=False). Proyecto: 125 s, 0 errores, 11/11 ✅. Sin cambios.
- 17 lección: 72 s, 0 errores. Proyecto: 19 s, 0 errores, 17/17 ✅. Sin cambios.
- 18 lección: 36 s, 0 errores (Qdrant local OK). Proyecto: 38 s, 0 errores, 5/5 tests ✅. Sin cambios.
