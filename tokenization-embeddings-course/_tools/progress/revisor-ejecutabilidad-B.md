# Progreso: revisor-ejecutabilidad-B
Agente: Revisor de ejecutabilidad · Módulos: 09–20 · Informe: tokenization-embeddings-course/_tools/REVISION_EJECUTABILIDAD_B.md
- [x] 09_capa_embedding_llm (lección + proyecto ejecutados con nbclient)
- [ ] 10_embeddings_contextuales_oraciones (lección + proyecto ejecutados con nbclient)
- [ ] 11_aprendizaje_contrastivo (lección + proyecto ejecutados con nbclient)
- [ ] 12_embedders_modernos (lección + proyecto ejecutados con nbclient)
- [ ] 13_dense_sparse_late_interaction (lección + proyecto ejecutados con nbclient)
- [ ] 14_indexacion_ann (lección + proyecto ejecutados con nbclient)
- [ ] 15_evaluacion_retrieval (lección + proyecto ejecutados con nbclient)
- [ ] 16_embeddings_multimodales (lección + proyecto ejecutados con nbclient)
- [ ] 17_interpretabilidad_geometria (lección + proyecto ejecutados con nbclient)
- [ ] 18_produccion (lección + proyecto ejecutados con nbclient)
- [ ] 19_playbook_elite (lección + proyecto ejecutados con nbclient)
- [ ] 20_capstone (lección + proyecto ejecutados con nbclient)
- [ ] check_course.py OK + informe final

## Notas para retomar
- (comandos lanzados y su resultado)
- Runner: `OMP_NUM_THREADS=2 <scratchpad>/bin/q.sh <nb...>` → `run_nb.py` (copia del módulo en `<scratchpad>/execB/<nb>/`, `!pip install` → `--dry-run`, FAST_DEV_RUN=True, CPU, timeout 600 s/celda, allow_errors; resumen en `execB/summary.log`).
- 09 lección: 233 s, 0 errores. Wikipedia 403 → corpus SINTÉTICO (aviso ⚠️ visible); CodeSearchNet → stdlib real; GPT-2/OPT/Pythia/SmolLM/Qwen del hub no disponibles → mini-GPT-2 fallback (aviso). pip dry-run OK. Proyecto: 33 s, 0 errores, rúbrica 6/6 ✅ (gap 0.93 ≥ 0.5; fert −8.9 % ≥ 5 %; bpb 2.287 ≤ 2.350+0.05). Sin cambios.
- Hallado (para 10/11): `BertWordPieceTokenizer.train_from_iterator` NO es determinista entre procesos (empates vía HashMap de Rust; 5 hashes distintos en 5 ejecuciones); BpeTrainer y UnigramTrainer sí. Builders 10 y 11 ya editados: vocab WordPiece desde Unigram (determinista). Builders 12–14: quitado `-U` del pip (ya regenerados, sin commit hasta su módulo).
