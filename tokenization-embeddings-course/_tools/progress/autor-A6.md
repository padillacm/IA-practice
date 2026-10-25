# Progreso: autor-A6
Agente: Autor A6 · Módulos: 15–17
- [x] Módulo 15_evaluacion_retrieval: README + lección + proyecto + build_15.py OK + commit/push
- [x] Módulo 16_embeddings_multimodales: README + lección + proyecto + build_16.py OK + commit/push
- [x] Módulo 17_interpretabilidad_geometria: README + lección + proyecto + build_17.py OK + commit/push
- [ ] check_course.py OK + informe final

## Notas para retomar
- Archivos auxiliares compartidos en `_tools/builders/`: `_a6_common.py` (carga_corpus sintético/real), `_a6_src15.py` (métricas/estadística/retrievers), `_a6_readmes.py`, `_b15_*.py` (partes de la lección/proyecto 15). build_15.py también genera `15_evaluacion_retrieval/poliglota_eval.py` (módulo canónico de métricas).
- Entorno: HF/transformers bloqueados (proxy); arXiv sí. Todo lo de datos reales (HF) NO probado; lo sintético sí (nbclient). Usar el subdirectorio scratchpad/a6 (el scratchpad y /tmp son compartidos con otros agentes).
- M15 medido (FAST_DEV, sintético, semilla 42): nDCG@10 BM25 .531, LSI-48 .589, RRF .519; IC95 BM25 ancho .178; Δ LSI−BM25 +.058 (p Holm .059); code slice BM25 .094 → .253 con tok_code.
- Verificado: LIMIT = Weller et al. arXiv 2508.21038 (ICLR'26), Gemini Embedding 2 (GA 22-abr-2026 según prensa; blog.google no accesible desde el contenedor), ColPali 1030 vectores×128 d (~257.5 KB/página fp16), ViDoRe V3 arXiv 2601.08620.
- M16 (FAST_DEV, CPU, nbclient OK 0 errores): CLIP/SigLIP toy (gap τ=.01→1.06; τ aprendida .21; sin entrenar 1.15), tasa de intrusos 100% solo con τ=.01, MaxSim vs vector medio vs OCR (σ=0/.3/.45), rúbrica proyecto 11/11. Celdas con modelos reales (CLIP/SigLIP, colpali-engine, Gemini API) NO probadas (HF bloqueado, sin GPU).
- M17 (FAST_DEV OK 0 errores): TopK SAE vs ReLU+L1 vs PCA (plantado 64 feat/24 d), pureza SAE .83 vs PCA .72 vs k-means .91, estabilidad entre semillas ≈ .46, inversión LSI .92; rúbrica proyecto 17/17. vec2text / embedder real NO probados.
- Pendiente: revisión final (check_course OK para 15-17) e informe final.
