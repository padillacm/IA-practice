# CHECKPOINT · estado final del curso

Fecha: 2026-10-26 · Rama: `claude/tokenization-embeddings-course` · Estado del arte a oct-2026.

## Qué hay
- **21 módulos (00–20), 42 notebooks** (lección + proyecto), 2227 celdas (1030 de código), todos generados por
  `_tools/builders/build_NN.py`. Regenerar los 21 builders reproduce exactamente los notebooks commiteados
  (IDs de celda deterministas). `check_course.py` → **Todo OK**.
- **81 celdas Gemini** (65 imágenes, 16 videos), indexadas en `extras/GEMINI_ASSETS.md`; todas con ID, prompt
  autocontenido, formato, alt, instrucción de inserción, placeholder y «👀 Qué debes observar».
- Extras: `GUIA_DE_ESTUDIO.md` (ruta 104 h, rutas abreviadas, mapa de conceptos, glosario ES/EN),
  `extras/GUIA_ENTREVISTAS.md` (50 preguntas, 6 de system design), `extras/LECTURA_PAPERS.md` (lectura guiada 00–20).
- Revisiones: técnica, ejecutabilidad, pedagógica, referencias, élite y consistencia/Gemini en ambos bloques
  (informes `_tools/REVISION_*.md`).

## Qué se probó
- Los 42 notebooks se ejecutaron de arriba abajo con nbclient en CPU con `FAST_DEV_RUN=True` sin errores
  (bloque A ≈ 28 min, bloque B ≈ 31 min). Las soluciones cumplen sus rúbricas con lo medido.
- Datos reales que sí corrieron: Europarl ES/EN (03–05, espejo NLTK en GitHub), vocabulario real de GPT-2
  (espejo GitHub con SHA-256 verificado), ranks de r50k/cl100k/o200k reconstruidos desde js-tiktoken (03–05),
  MNIST, fotos de scikit-learn y voz del Free Spoken Digit Dataset (08), código real de la stdlib de Python,
  FAISS, Qdrant local y FastAPI (14, 18), ranx (15).
- 176 + 105 IDs arXiv verificados contra arxiv.org; ninguna referencia inventada.

## Pendiente de validar en Colab (no se pudo aquí: Hugging Face, Wikipedia API, openaipublic y Zenodo bloqueados)
1. Rama «real» de `carga_corpus` (Wikipedia ES/EN + CodeSearchNet) y recalibrar con ella las rúbricas numéricas
   de 00–02, 06, 07 y 09–20 (hoy calibradas con datos sintéticos; cada proyecto lo avisa).
2. Modelos preentrenados de HF: GPT-2 (05, 07, 09), mDistilBERT/MiniLM/e5 (10–11), E5/BGE-M3/Qwen3/EmbeddingGemma,
   SPLADE y rerankers (12–13), CLIP/SigLIP/ColPali (16), vec2text (17), EnCodec/Mimi con pesos reales (08), BLT.
   Conclusiones que hoy dependen del embedder de respaldo (TF-IDF+SVD, «denso» también léxico) están marcadas
   en 19 y 20.
3. Proyecto 04: los 3 puntos de tiktoken o200k/cl100k (aquí 13/16 por la descarga bloqueada).
4. Ejecución en GPU (modo completo de 07, 11, 16, 17) y los tiempos/unidades de Colab Pro.
5. `mteb.evaluate`, TEI/vLLM, pgvector (solo SQL de referencia) y APIs (Gemini, OpenAI), que son celdas opcionales.
6. Fuentes secundarias marcadas ⚠️ (p. ej. límites de Gemini Embedding 2, filas a cero en Llama 3 base,
   parche de ChatGPT tras SolidGoldMagikarp): confirmar si se quieren como hechos.
7. Los badges de Colab apuntan a `master`: funcionan tras el merge.

## Cómo retomar
Editar `_tools/builders/build_NN.py` (o sus auxiliares) → `python tokenization-embeddings-course/_tools/builders/build_NN.py`
→ `python tokenization-embeddings-course/_tools/check_course.py` → si cambian prompts Gemini,
`python tokenization-embeddings-course/_tools/gen_gemini_index.py`.
