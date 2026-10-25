# Progreso: revisor-ejecutabilidad-A
Agente: Revisor de ejecutabilidad · Módulos: 00–08 · Informe: tokenization-embeddings-course/_tools/REVISION_EJECUTABILIDAD_A.md
- [x] 00_intro (lección + proyecto ejecutados con nbclient)
- [x] 01_unicode_bytes (lección + proyecto ejecutados con nbclient)
- [ ] 02_bpe_desde_cero (lección + proyecto ejecutados con nbclient)
- [ ] 03_wordpiece_unigram_sentencepiece (lección + proyecto ejecutados con nbclient)
- [ ] 04_diseno_tokenizers_modernos (lección + proyecto ejecutados con nbclient)
- [ ] 05_patologias_robustez (lección + proyecto ejecutados con nbclient)
- [ ] 06_tokenizer_free_bytes_blt (lección + proyecto ejecutados con nbclient)
- [ ] 07_hnet_tokenizer_transfer (lección + proyecto ejecutados con nbclient)
- [ ] 08_tokens_multimodales_audio (lección + proyecto ejecutados con nbclient)
- [ ] check_course.py OK + informe final

## Notas para retomar
- (comandos lanzados y su resultado)
- Runner: `OMP_NUM_THREADS=2 python <scratchpad>/run_nb.py <nb.ipynb> 600` (copia en scratchpad/exec/<nb>/, `!pip install` → `--dry-run`, FAST_DEV_RUN=True, CPU, allow_errors para listar todos los fallos).
- 00 lección: 17 s, 0 errores; GPT-2 vía espejo GitHub (hash OK); Wikipedia API 403 → corpus SINTÉTICO (aviso ⚠️ visible); CodeSearchNet → stdlib real. Proyecto: 7 s, 0 errores, rúbrica 12/12 ✅ (nDCG@10 0.878 ≥ 0.82). Sin cambios.
- 01 lección: 14 s, 0 errores (GPT-2 espejo; corpus sintético con aviso). Proyecto: 15 s, 0 errores, rúbrica 13/13 ✅ (R7 limpio 0.955 / sucio 0.894). Sin cambios.
