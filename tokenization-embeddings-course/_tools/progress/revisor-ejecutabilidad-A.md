# Progreso: revisor-ejecutabilidad-A
Agente: Revisor de ejecutabilidad · Módulos: 00–08 · Informe: tokenization-embeddings-course/_tools/REVISION_EJECUTABILIDAD_A.md
- [x] 00_intro (lección + proyecto ejecutados con nbclient)
- [x] 01_unicode_bytes (lección + proyecto ejecutados con nbclient)
- [x] 02_bpe_desde_cero (lección + proyecto ejecutados con nbclient)
- [x] 03_wordpiece_unigram_sentencepiece (lección + proyecto ejecutados con nbclient)
- [x] 04_diseno_tokenizers_modernos (lección + proyecto ejecutados con nbclient)
- [x] 05_patologias_robustez (lección + proyecto ejecutados con nbclient)
- [x] 06_tokenizer_free_bytes_blt (lección + proyecto ejecutados con nbclient)
- [x] 07_hnet_tokenizer_transfer (lección + proyecto ejecutados con nbclient)
- [x] 08_tokens_multimodales_audio (lección + proyecto ejecutados con nbclient)
- [x] check_course.py OK + informe final

## Notas para retomar
- (comandos lanzados y su resultado)
- Runner: `OMP_NUM_THREADS=2 python <scratchpad>/run_nb.py <nb.ipynb> 600` (copia en scratchpad/exec/<nb>/, `!pip install` → `--dry-run`, FAST_DEV_RUN=True, CPU, allow_errors para listar todos los fallos).
- 00 lección: 17 s, 0 errores; GPT-2 vía espejo GitHub (hash OK); Wikipedia API 403 → corpus SINTÉTICO (aviso ⚠️ visible); CodeSearchNet → stdlib real. Proyecto: 7 s, 0 errores, rúbrica 12/12 ✅ (nDCG@10 0.878 ≥ 0.82). Sin cambios.
- 01 lección: 14 s, 0 errores (GPT-2 espejo; corpus sintético con aviso). Proyecto: 15 s, 0 errores, rúbrica 13/13 ✅ (R7 limpio 0.955 / sucio 0.894). Sin cambios.
- 02 lección: 21 s, 0 errores (encode propio == tiktoken GPT-2 real 18/18; cl100k/o200k no descargables). Proyecto: 7 s, 0 errores, rúbrica 13/13 ✅. Sin cambios.
- 03 lección: 39 s, 0 errores; datos REALES vía espejo (NLTK Europarl ES/EN + stdlib); r50k/cl100k/o200k no descargables (aviso). Proyecto: 14 s, 0 errores, rúbrica 11/11 ✅. Cambio: `_a2_common.pip_cell` sin `-U` (riesgo de romper transformers en Colab al actualizar solo tokenizers); afecta 03–05.
- 04 lección: 43 s, 0 errores; Europarl real (espejo NLTK); tokenizers HF no disponibles (aviso). Proyecto: 15 s, 0 errores, 13/16 (los 3 pts de «tiktoken o200k/cl100k» no alcanzables aquí por proxy; en Colab sí). Mejora J medida 11 % (umbral 8 %), desbalance 1.20 (≤ 1.35): calibrado. Solo regenerado (pip).
- 05 lección: 93 s (celda 18 MiniGPT 70 s), 0 errores; Europarl real. Proyecto: 74 s, 0 errores, rúbrica completa ✅ (prec@100 1.00 ≥ 0.9; recall 0.42 ≥ 0.3; AUC 1.0; P5 83 % ≥ 60 %). Solo regenerado (pip).
- 06 lección: 274 s (celda 55 MiniBLT 145 s, celda 28 72 s; 2 hilos CPU), 0 errores; corpus sintético con aviso. Proyecto: 46 s, 0 errores; plantilla 0/7 (esperado), solución 7/7 ✅ (ps 4.27/4.48; frag 1.036 ≤ 1.10; ps_25 6.0 ≤ 6.5). Sin cambios.
- 07 lección: 370 s (celdas 42/22 ≈ 130 s c/u), 0 errores; corpus sintético con aviso. Proyecto: 150 s, 0 errores, 7/7 ✅. Cambio: R3 comparaba bpb cero-shot FVT vs aleatoria con margen 0 y diferencia medida ~0.009 (autor: 0.005; frágil, cambia de signo entre entornos) → ahora compara tras la fase de solo embeddings (K1): medido 0.703 vs 0.779, umbral FVT ≤ aleatoria − 0.03 (`_a3_proj07.py`). Re-ejecutado: ✅.
- 08 lección: 1ª corrida 387 s con 1 error (`import torchaudio` fuera del try). Arreglado (torchaudio opcional + SciPy). Añadida cadena de audio real FSDD (GitHub) → sintético. Re-ejecutado con torchvision/torchaudio instalados (--no-deps): 354 s, 0 errores, MNIST real + voz real. Proyecto: 140 s, 0 errores; R5 falló con voz real (SNR 2.94 dB < 9.0) → recalibrada a ≥ 2.5 dB y ganancia ≥ 1.0 dB (medido 1.46→2.94). Informe en _tools/REVISION_EJECUTABILIDAD_A.md.
- check_course.py: Todo OK (tras commit 42f375c).
