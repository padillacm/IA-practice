# Progreso: autor-A3
Agente: Autor A3 · Módulos: 06–08
- [x] Módulo 06_tokenizer_free_bytes_blt: README + lección + proyecto + build_06.py OK + commit/push
- [x] Módulo 07_hnet_tokenizer_transfer: README + lección + proyecto + build_07.py OK + commit/push
- [x] Módulo 08_tokens_multimodales_audio: README + lección + proyecto + build_08.py OK + commit/push
- [x] check_course.py OK + informe final

## Notas para retomar
- Entorno de pruebas: venv /tmp/a3venv (torch CPU+transformers+tokenizers…; HF/openaipublic/zenodo bloqueados; arXiv, raw.githubusercontent, PyPI y torchvision-MNIST funcionan). Runner de prueba: /tmp/a3papers/runnb.py (ejecuta celdas de un .ipynb).
- Código compartido: _tools/builders/a3_common.py (observe/box/details/hint, SETUP_COMMON, corpus_cells() = celdas canónicas de poliglota_utils). Código de celdas de 06/07 en _a3_src06.py/_a3_src07.py; proyectos en _a3_proj06.py/_a3_proj07.py; build_NN.py los ensambla.
- 06 hecho: lección (46 md + 25 código; 3 IMG + 1 VID) y proyecto (18 md + 33 código). Medido (corpus sintético, FAST_DEV): ps val 4.27/4.48, incremental 100 %/92.7 % (BPE), erratas 5 %: frag 1.036 vs 1.005, estabilidad 0.993 vs 1.0, ps para -25 % FLOPs = 6.0. MiniBLT 1.7 bpb vs BPE-512 1.0 vs bytes 2.9 (400 pasos; BPE gana, coherente con el paper a poco cómputo).
- 07: código de celdas y builders escritos (build_07.py, _a3_src07.py, _a3_proj07.py); falta calibrar umbrales del proyecto (T en _a3_proj07.py), probar lección/proyecto completos y commit.
- 08: pendiente (diseño: ViT patches, VQ-VAE/FSQ/RVQ en MNIST, codec toy RVQ audio sintético, imagen real sklearn china/flower; EnCodec/HF con try/except).

- 07 hecho: medido H-Net mini: F≈0.27 (obj 0.25), fronteras vs inicios de palabra P=0.54 R=0.91 (azar 0.16/0.27); bpb pool 3.17 > dc ~2.55 ≈ space ~2.45 (400 pasos). Transfer: bpb0 FVT 3.55, FOCUS 3.59, media 3.86, Hewitt 4.18; final ≈0.23 todas; control A 0.39, scratch B 0.32. Proyecto 7/7 con umbrales calibrados (regresión EN+código +50 %).
- 08: falta _a3_proj08.py (proyecto: foto real china/flower con VQ/RVQ vs JPEG + audio RVQ vs μ-law). FSQ necesitaba ganancia x10 a la entrada (arreglado).
- 08 hecho: MNIST real (torchvision) y fotos reales de scikit-learn ejecutadas; VQ K=64 22.1 dB (ppl 34/64), FSQ [8,6,5] 21.2 dB (ppl 41/240; requiere normalizar entrada y lr 1e-3), RVQ 20.2→23.2 dB con 1→4 niveles; códec toy 7.5→11.9 dB SNR (1→4 kbps; L1 con peso 10). Proyecto: foto no vista 20.45 dB a 0.5 bpp vs JPEG 32.9 dB; 6/6.
