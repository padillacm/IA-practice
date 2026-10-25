# SYLLABUS · Tokenización y Embeddings: de BPE a los modelos modernos

Fecha de referencia del estado del arte: **octubre 2026**. Niveles: 🟢 básico · 🟡 intermedio · 🟠 avanzado · 🔴 experto.
Madurez de técnicas (se etiqueta dentro de cada lección): 🟢 sólido (estándar de industria) · 🟡 emergente (resultados
publicados, adopción parcial) · 🔴 experimental (investigación temprana).

> **Las "lecturas candidatas" de cada módulo son punto de partida, NO citas verificadas.** Cada autor debe confirmar
> autor, año, título y URL con WebSearch/WebFetch antes de citar; si no se puede confirmar, cita solo lo que sí sepa
> o márcalo como fuente secundaria. IDs de modelos, cifras de leaderboards y tamaños de vocabulario: verificarlos y
> fecharlos ("a oct-2026").

## Hilo conductor · Políglota
Eres ML engineer en **Políglota Labs**, startup que construye un buscador semántico para documentación técnica en
español, inglés y código. En cada módulo el alumno añade una pieza: corpus y baseline BM25 (00) → tokenizer propio
(01–05) → alternativas a tokenizar (06–08) → embeddings propios y modernos (09–12) → retrieval híbrido e índice
(13–14) → evaluación (15) → multimodal (16) → interpretabilidad (17) → servicio en producción (18) → decisiones de
diseño (19) → Políglota completo (20). Cada proyecto debe mencionar cómo se conecta con el módulo anterior y siguiente.

**Corpus Políglota** (definido en el módulo 00, reutilizado por todos): subconjunto de Wikipedia ES+EN (≈ 20–50 MB de
texto), documentación técnica (Markdown de proyectos open source con licencia permisiva) y código (CodeSearchNet,
Python). El módulo 00 publica la celda de utilidades `carga_corpus()`; los demás la copian (cada notebook es
autocontenido) y documentan cualquier diferencia.

## Datasets (cadena: oficial → espejo → sintético con el mismo esquema; verificar disponibilidad)
| Uso | Dataset (candidato) | Notas |
|---|---|---|
| Corpus ES/EN | HF `wikimedia/wikipedia` (`20231101.es`, `20231101.en`) | CC BY-SA; usar streaming y subconjunto |
| Paridad multilingüe | FLORES-200 / `openlanguagedata/flores_plus` | puede requerir aceptar términos; fallback: `Helsinki-NLP/opus-100` en-es o frases sintéticas paralelas |
| Retrieval | BEIR (`BeIR/scifact`, `BeIR/fiqa`), MIRACL-es (`miracl/miracl`), mMARCO (`unicamp-dlc/mmarco`) | usar subconjuntos pequeños con `FAST_DEV_RUN` |
| Código | CodeSearchNet (`code_search_net` / `code-search-net/code_search_net`) | Python |
| Multimodal | COCO (subconjunto de captions), ViDoRe (`vidore/*`) | pocas imágenes en FAST_DEV_RUN |
| Audio | LibriSpeech pequeño (`openslr/librispeech_asr` o split dummy de HF) | segundos de audio |
En entornos con proxy restrictivo, HF/Kaggle pueden estar bloqueados: el builder debe seguir funcionando con el
fallback sintético, avisando claramente.

## Convenciones técnicas comunes
- Semilla 42; `device` detectado; `FAST_DEV_RUN = True` por defecto en las celdas pesadas (CPU en minutos).
- Métricas de retrieval: nDCG@10, Recall@k, MRR@10 (misma implementación en todos los módulos; 15 la formaliza).
- Tokenizers: reportar siempre **fertilidad** (tokens/palabra) y **bytes por token**; paridad ES/EN con Flores.
- Cada lección incluye la tabla **Mapa de madurez** (técnica → 🟢/🟡/🔴 → quién la usa → fuente).

## Bloque A · Texto y tokenización

### 00 · Intro, entorno e hilo conductor 🟢 · ≈ 2 h · CPU
- Entra: mapa del curso, qué es un token y qué es un embedding (visión global), entorno Colab, corpus Políglota, baseline BM25 (`rank_bm25`) con nDCG@10 sobre un mini-benchmark ES/EN. Cómo usar las celdas Gemini y la carpeta `assets/`.
- No entra: BPE, entrenamiento de embeddings.
- Proyecto: Políglota v0 (corpus + BM25 + mini golden set).

### 01 · Texto como bytes: Unicode, UTF-8, normalización 🟢 · ≈ 4 h · CPU
- Entra: code points vs bytes vs grafemas, UTF-8 a mano, NFC/NFD/NFKC/NFKD, homoglifos, emojis y secuencias ZWJ, costo en bytes por idioma, por qué la normalización importa en tokenización, mojibake.
- No entra: algoritmos de tokenización.
- Lecturas candidatas: Unicode Standard (UAX #15, UAX #29), "Unicode Explained"-tipo docs.
- Proyecto: auditoría Unicode del corpus Políglota + normalizador.

### 02 · BPE desde cero 🟡 · ≈ 5 h · CPU
- Entra: BPE (Gage 1994; Sennrich et al. 2016), byte-level BPE (GPT-2), regex de pre-tokenización (GPT-2, cl100k, o200k), entrenamiento eficiente (conteo incremental), codificación/decodificación, reglas de merge y orden, complejidad, ejemplo resuelto a mano. Analogía con Huffman/LZ y bits por byte.
- No entra: WordPiece/Unigram (03), diseño de vocabularios (04).
- Lecturas candidatas: Sennrich, Haddow, Birch 2016; Radford et al. 2019 (GPT-2); Karpathy `minbpe`.
- Proyecto: BPE propio entrenado en el corpus Políglota, verificado contra `tiktoken`/HF.

### 03 · WordPiece, Unigram, SentencePiece, tiktoken, HF tokenizers 🟡 · ≈ 5 h · CPU
- Entra: WordPiece, Unigram LM (Kudo 2018), SentencePiece (Kudo & Richardson 2018), BPE-dropout/subword regularization, pipeline de HF `tokenizers` (normalizer → pre-tokenizer → model → post-processor → decoder), entrenar un tokenizer con HF y SentencePiece, `tiktoken`, comparar algoritmos.
- No entra: criterios de diseño de vocabulario (04).
- Proyecto: entrenar y comparar 3 tokenizers (BPE/Unigram/WordPiece) sobre Políglota.

### 04 · Diseño de tokenizers modernos 🟠 · ≈ 5 h · CPU
- Entra: tamaño de vocabulario (trade-offs, leyes de escala con el vocabulario), vocabularios reales de modelos recientes (familia Llama, Gemma, Qwen, Mistral/Tekken, GPT/o200k: **verificar cifras**), multilingüe y "token tax", fertilidad y paridad, tokenización de números y código (espacios/indentación), tokens especiales, chat templates, tokenizers que cruzan límites de palabra (p. ej. SuperBPE, verificar), costos en $ por idioma.
- No entra: patologías (05), tokenizer-free (06–07).
- Proyecto: benchmark de fertilidad/paridad ES/EN/código con Flores y diseño de un vocabulario óptimo para Políglota.

### 05 · Patologías y robustez 🟠 · ≈ 5 h · CPU/T4
- Entra: glitch tokens ("SolidGoldMagikarp" y trabajo posterior), conteo de letras ("strawberry"), aritmética y números, sensibilidad a espacios/mayúsculas, prompt boundary / token healing, token smuggling / inyección vía Unicode, tokens sub-entrenados, detectar tokens de bajo uso, por qué ocurre (conexión con el vocabulario entrenado en datos distintos al modelo).
- No entra: soluciones arquitectónicas (06–07).
- Proyecto: detector de glitch/under-trained tokens y fuzzing de un tokenizer + modelo pequeño.

### 06 · Tokenizer-free I: bytes y patches 🔴 · ≈ 5 h · T4 (CPU en FAST_DEV)
- Entra: modelos a nivel de byte/carácter (CANINE, ByT5, MegaByte, SpaceByte, MambaByte), Byte Latent Transformer (BLT: patching por entropía del siguiente byte, encoder/decoder locales, latent transformer global), FLOPs por byte vs por token, resultados y límites (benchmarks de caracteres, costos). Etiquetar madurez con honestidad (🟡/🔴).
- No entra: H-Net y tokenizer transfer (07).
- Proyecto: mini patcher entrópico (modelo de bytes pequeño) y comparación con BPE a escala diminuta.

### 07 · Tokenizer-free II y tokenizer transfer 🔴 · ≈ 6 h · L4 recomendada (T4/CPU en FAST_DEV)
- Entra: H-Net / dynamic chunking (Hwang, Wang, Gu 2025: chunking aprendido, routing, smoothing, jerarquías), ¿está muerta la tokenización? (visión crítica con evidencia), tokenizer transfer (Zero-Shot Tokenizer Transfer, FOCUS, WECHSEL, Trans-Tokenization: verificar), inicialización de embeddings de vocabulario nuevo, adaptación de vocabulario a idioma/dominio.
- No entra: pretraining desde cero a escala.
- Proyecto: cambiar el tokenizer de un modelo pequeño y medir pérdida de calidad antes/después del ajuste.

### 08 · Tokens multimodales y de audio 🟠 · ≈ 6 h · T4
- Entra: patches ViT, VQ-VAE, VQGAN, FSQ, tokens de imagen en LLMs (Chameleon-style), codecs de audio (SoundStream, EnCodec, Mimi: verificar), tokenizers de video, tokens discretos vs continuos, tasa de tokens por segundo/imagen y costo de contexto.
- No entra: modelos de generación completos; embeddings multimodales de retrieval (16).
- Proyecto: tokenizar una imagen (VQ) y un clip de audio (codec) pequeños y medir reconstrucción y compresión.

## Bloque B · Embeddings

### 09 · La capa de embedding en LLMs 🟡 · ≈ 5 h · CPU/T4
- Entra: de token id a vector, matriz de embeddings y unembedding, weight tying (Press & Wolf 2017), geometría y normas, frecuencia de tokens y embeddings, extensión de vocabulario e inicialización, cuello de botella softmax. Caja histórica corta (≤ 1 sección) sobre word2vec/GloVe/PMI solo como contexto, sin módulo propio.
- No entra: embeddings de oraciones (10).
- Proyecto: análisis de la capa de embedding de un LLM pequeño (normas, vecinos, tokens raros) y extender el vocabulario con tokens de dominio.

### 10 · Embeddings contextuales y de oraciones 🟡 · ≈ 5 h · CPU/T4
- Entra: BERT y representaciones contextuales, pooling (CLS, mean, max, last-token), SBERT y bi-encoders, anisotropía y soluciones (whitening, BERT-flow, normalización), similitud (coseno, producto punto, L2), baselines de oraciones; prompts e instrucciones.
- No entra: entrenamiento contrastivo (11).
- Proyecto: comparar estrategias de pooling/whitening en retrieval Políglota.

### 11 · Aprendizaje contrastivo para embeddings 🟠 · ≈ 6 h · L4/A100 recomendada (T4 en FAST_DEV)
- Entra: InfoNCE y temperatura, in-batch negatives, hard negative mining, SimCSE, DPR, pretraining débilmente supervisado → fine-tuning, MultipleNegativesRankingLoss, Gradient Cache / batch grande, LoRA para embedders, derivaciones (InfoNCE como cota de información mutua), colapso y uniformidad/alineación.
- No entra: LLM-as-embedder (12).
- Proyecto: entrenar tu embedder ES/EN con hard negatives y medir contra baselines.

### 12 · Embedders modernos 🟠 · ≈ 5 h · T4/L4
- Entra: familias E5, BGE, GTE, Nomic, NV-Embed, Qwen3-Embedding, Gemini Embedding, EmbeddingGemma, Jina (verificar vigentes), LLM-as-embedder (LLM2Vec, e5-mistral, last-token/latent attention pooling), embeddings con instrucciones, Matryoshka (Kusupati 2022) y truncado, cuantización (int8/binaria), MTEB/MMTEB y sus límites, cómo elegir un embedder.
- No entra: sparse/late interaction (13), evaluación a fondo (15).
- Proyecto: comparativa de 4–6 embedders con Matryoshka y cuantización en Políglota (calidad vs memoria vs latencia).

### 13 · Dense vs sparse vs late interaction 🟠 · ≈ 5 h · T4
- Entra: BM25, SPLADE y sparse aprendido, ColBERT/ColBERTv2 y MaxSim, PLAID, representaciones multi-vector fijas (MUVERA, verificar), BGE-M3 (dense+sparse+multi-vector), fusión (RRF, combinación lineal), rerankers cross-encoder, late chunking (verificar).
- No entra: indexación ANN (14).
- Proyecto: retrieval híbrido de Políglota con fusión y reranking.

### 14 · Indexación y ANN 🟠 · ≈ 5 h · CPU/T4
- Entra: fuerza bruta, HNSW, IVF, PQ/OPQ, ScaNN, DiskANN/Vamana, RaBitQ y cuantización binaria (verificar), filtros y búsqueda híbrida, trade-off recall/latencia/memoria, FAISS, construir HNSW desde cero (mini), analogía con recsys-course (módulo `08_deep_retrieval_ann`).
- No entra: operación de vector DBs (18).
- Proyecto: índice de Políglota con curvas recall@10 vs latencia vs memoria.

### 15 · Evaluación de embeddings y retrieval 🟠 · ≈ 5 h · CPU
- Entra: nDCG/Recall/MRR bien implementados, BEIR, MIRACL, MTEB/MMTEB, construcción de golden sets propios, LLM-as-judge para relevancia (sesgos), intervalos de confianza por bootstrap, contaminación y overfitting al leaderboard, límites teóricos de retrieval con embeddings de dimensión fija (trabajo reciente, verificar), drift.
- No entra: A/B en producción (18).
- Proyecto: banco de evaluación de Políglota con CIs y análisis de errores.

### 16 · Embeddings multimodales 🟠 · ≈ 5 h · L4 recomendada (T4 en FAST_DEV)
- Entra: CLIP, SigLIP/SigLIP 2, modality gap, ColPali / ViDoRe (retrieval visual de documentos), embeddings unificados multimodales (Gemini Embedding 2 y similares: **verificar fecha y capacidades**), audio y video en embeddings, cuándo OCR+texto vs embedding visual.
- No entra: generación multimodal.
- Proyecto: extender Políglota para buscar en PDFs con capturas/diagramas usando ColPali o equivalente.

### 17 · Interpretabilidad y geometría 🔴 · ≈ 5 h · T4/L4
- Entra: probing (Hewitt & Manning), hipótesis de representación lineal, sparse autoencoders (Anthropic, OpenAI TopK SAE) aplicados a embeddings, steering/dirección de conceptos, dimensiones dominantes y outliers, qué codifica un embedding de texto, vec2text y qué revela un embedding (puente a privacidad en 18).
- No entra: interpretabilidad mecanicista de circuitos completos.
- Proyecto: SAE sobre embeddings de Políglota y análisis de features interpretables.

### 18 · Producción 🟠 · ≈ 5 h · CPU/T4
- Entra: costos ($/1M tokens, GPU vs API), batching, TEI/vLLM para embeddings, caché, latencia p50/p99, versionado y migración de embedders (re-embedding vs adaptadores lineales), cuantización en producción, vector DB ligera (Qdrant o pgvector), búsqueda híbrida con filtros, embedding inversion y privacidad, monitoreo de drift, A/B de retrieval.
- No entra: MLOps general.
- Proyecto: servicio de Políglota con caché, versionado y plan de migración de modelo.

### 19 · Playbook de élite 🔴 · ≈ 4 h · CPU
- Entra: masterclass con implementación de lo que las lecciones solo enumeran: árbol de decisión "qué tokenizer/embedder/índice elegir", trampas de evaluación, gap offline/online, costos a escala, casos reales de fallos, checklist de revisión de PRs de tokenización/embeddings, cultura de laboratorios top. Debe producir además `extras/GUIA_ENTREVISTAS.md` (preguntas de tokenización/embeddings/system design con respuestas modelo y rúbrica) y `extras/LECTURA_PAPERS.md` (lectura guiada priorizada por módulo, con preguntas de lectura; solo papers verificados).
- Proyecto: casos de system design (3) resueltos y revisados contra rúbrica.

### 20 · Capstone: Políglota completo 🔴 · ≈ 6 h · T4/L4
- Entra: integrar tokenizer + embedder + híbrido + índice + evaluación + (opcional) multimodal + servicio; informe técnico de decisiones con métricas y costos; criterios de aceptación.
- Proyecto: Políglota completo con rúbrica final.

## Horas (≈ 104 h)
00:2 · 01:4 · 02:5 · 03:5 · 04:5 · 05:5 · 06:5 · 07:6 · 08:6 · 09:5 · 10:5 · 11:6 · 12:5 · 13:5 · 14:5 · 15:5 · 16:5 · 17:5 · 18:5 · 19:4 · 20:6.

## Plan de agentes
**Ola 1 (en paralelo):** A1 {00,01,02} · A2 {03,04,05} · A3 {06,07,08} · A4 {09,10,11} · A5 {12,13,14} · A6 {15,16,17}.
**Ola 2:** A7 {18,19,20} (integra y requiere ver lo ya escrito; escribe también `extras/GUIA_ENTREVISTAS.md` y `extras/LECTURA_PAPERS.md`).
**Revisores por bloque:** A = módulos 00–08, B = módulos 09–20. Orden: Técnico → Ejecutabilidad → Pedagógico → Verificador de referencias → Élite. Final: Consistencia y lenguaje + celdas Gemini (00–20).

## Slugs de carpeta (fijos; los builders se llaman `build_NN.py`)
| NN | Carpeta | Lección | Proyecto |
|---|---|---|---|
| 00 | `00_intro` | `00_intro.ipynb` | `00_proyecto_intro.ipynb` |
| 01 | `01_unicode_bytes` | `01_unicode_bytes.ipynb` | `01_proyecto_unicode_bytes.ipynb` |
| 02 | `02_bpe_desde_cero` | `02_bpe_desde_cero.ipynb` | `02_proyecto_bpe_desde_cero.ipynb` |
| 03 | `03_wordpiece_unigram_sentencepiece` | `03_wordpiece_unigram_sentencepiece.ipynb` | `03_proyecto_wordpiece_unigram_sentencepiece.ipynb` |
| 04 | `04_diseno_tokenizers_modernos` | `04_diseno_tokenizers_modernos.ipynb` | `04_proyecto_diseno_tokenizers_modernos.ipynb` |
| 05 | `05_patologias_robustez` | `05_patologias_robustez.ipynb` | `05_proyecto_patologias_robustez.ipynb` |
| 06 | `06_tokenizer_free_bytes_blt` | `06_tokenizer_free_bytes_blt.ipynb` | `06_proyecto_tokenizer_free_bytes_blt.ipynb` |
| 07 | `07_hnet_tokenizer_transfer` | `07_hnet_tokenizer_transfer.ipynb` | `07_proyecto_hnet_tokenizer_transfer.ipynb` |
| 08 | `08_tokens_multimodales_audio` | `08_tokens_multimodales_audio.ipynb` | `08_proyecto_tokens_multimodales_audio.ipynb` |
| 09 | `09_capa_embedding_llm` | `09_capa_embedding_llm.ipynb` | `09_proyecto_capa_embedding_llm.ipynb` |
| 10 | `10_embeddings_contextuales_oraciones` | `10_embeddings_contextuales_oraciones.ipynb` | `10_proyecto_embeddings_contextuales_oraciones.ipynb` |
| 11 | `11_aprendizaje_contrastivo` | `11_aprendizaje_contrastivo.ipynb` | `11_proyecto_aprendizaje_contrastivo.ipynb` |
| 12 | `12_embedders_modernos` | `12_embedders_modernos.ipynb` | `12_proyecto_embedders_modernos.ipynb` |
| 13 | `13_dense_sparse_late_interaction` | `13_dense_sparse_late_interaction.ipynb` | `13_proyecto_dense_sparse_late_interaction.ipynb` |
| 14 | `14_indexacion_ann` | `14_indexacion_ann.ipynb` | `14_proyecto_indexacion_ann.ipynb` |
| 15 | `15_evaluacion_retrieval` | `15_evaluacion_retrieval.ipynb` | `15_proyecto_evaluacion_retrieval.ipynb` |
| 16 | `16_embeddings_multimodales` | `16_embeddings_multimodales.ipynb` | `16_proyecto_embeddings_multimodales.ipynb` |
| 17 | `17_interpretabilidad_geometria` | `17_interpretabilidad_geometria.ipynb` | `17_proyecto_interpretabilidad_geometria.ipynb` |
| 18 | `18_produccion` | `18_produccion.ipynb` | `18_proyecto_produccion.ipynb` |
| 19 | `19_playbook_elite` | `19_playbook_elite.ipynb` | `19_proyecto_playbook_elite.ipynb` |
| 20 | `20_capstone` | `20_capstone.ipynb` | `20_proyecto_capstone.ipynb` |

Los nombres de proyecto contienen «proyecto» (lo exige `check_course.py`). Cada módulo tiene también `README.md`
y una carpeta `assets/` (con `.gitkeep`) para las imágenes/videos de Gemini.
