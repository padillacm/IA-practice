# COURSE_SPEC · Tokenización y Embeddings: de BPE a los modelos modernos

## Criterios de éxito (palabras literales del usuario)
- "Experto de laboratorio/empresa top" (nivel final; referentes: OpenAI, Google DeepMind, Meta FAIR, Anthropic, Cohere, Voyage, Jina, Mistral).
- "Implementación desde cero + librerías": se construye el mecanismo a mano y luego se usa la librería de industria.
- "Muchos diagramas y prompts que le pasaré a Gemini para que genere imágenes y videos, así que deja bien claro las celdas que tiene que reemplazar Gemini por una imagen o video".
- "Lo último publicado, marcando qué es sólido y qué es incipiente".
- "~100 h, ~18-20 módulos" (el diseño aprobado tiene 21 módulos, 00–20, ≈ 104 h).
- Hilo conductor: "Políglota: buscador semántico multilingüe".
- "Plantilla con TODOs + pistas graduadas + solución oculta" en cada proyecto.
- Contenido de élite: "Ambos: sección por módulo + módulo propio".
- Extras de cierre: "Capstone", "Guía de entrevistas / system design", "Lectura guiada de papers".
- Notebooks de Colab, con cómputo "Colab Pro".
- Un módulo de producción + temas de producción en el playbook.
- Español con términos en inglés.

## Alumno
- Domina: Python sólido, Deep learning / PyTorch, Transformers / atención, Álgebra lineal y probabilidad.
- Del tema sabe: "He leído algo" (conoce BPE y word2vec de nombre; no los ha implementado). Cada concepto se explica desde cero.
- Analogías a usar (a criterio del diseñador, el usuario lo delegó): compresión de datos (BPE ↔ Huffman/LZ, entropía, bits por byte), búsqueda/IR y sistemas de recomendación (BM25, índices invertidos, embeddings de ítems, two-tower, ANN; el repo tiene `recsys-course/`), lingüística (Unicode, morfología, fertilidad por idioma).
- Idioma: español con términos técnicos en inglés (token, embedding, fine-tuning, retrieval…).

## Objetivo
- Nivel final: experto de laboratorio/empresa top (referentes: OpenAI, Google DeepMind, Meta FAIR, Anthropic, Cohere, Voyage, Jina, Mistral).
- Para qué: trabajo actual, cambiar de rol / entrevistas, investigación (leer y reproducir papers recientes).
- Peso: implementación desde cero + librerías de industria (núcleo); teoría justa para entender; producción en un módulo + playbook.

## Formato y recursos
- Formato: notebooks de Colab (lección + proyecto por módulo).
- Cómputo: Colab Pro (T4 por defecto; L4/A100 permitidos en módulos concretos y marcados con unidades estimadas). Todo debe poder correr en `FAST_DEV_RUN` en CPU.
- Duración: ≈ 104 h · ritmo sugerido 8 h/semana · nº de módulos: 21 (00–20).
- Gráficos: ≥ 8 visuales por lección: ≥ 3 celdas Gemini (🎨 imagen / 🎬 video, que el usuario reemplazará) + ≥ 5 gráficos o diagramas generados en código.

## Contenido
- Alcance: tokenización (bytes/Unicode, BPE, WordPiece, Unigram, SentencePiece, tiktoken, diseño de vocabularios, multilingüe, patologías, tokenizer-free: ByT5/MegaByte/BLT/H-Net, tokenizer transfer, tokens multimodales y de audio) y embeddings (capa de embedding de LLMs, contextuales y de oraciones, aprendizaje contrastivo, embedders modernos, Matryoshka y cuantización, dense/sparse/late interaction, ANN, evaluación, multimodal, interpretabilidad, producción). Estado del arte hasta lo último publicado (fecha de referencia: octubre 2026), con etiquetas de madurez 🟢 sólido / 🟡 emergente / 🔴 experimental.
- Fuera de alcance: pretraining completo de LLMs, RLHF, agentes, serving de LLMs generativos, fine-tuning de LLMs (salvo lo necesario para embedders y tokenizer transfer).
- Stack obligatorio: PyTorch + Hugging Face (`transformers`, `tokenizers`, `datasets`); además `tiktoken`, `sentencepiece`, `sentence-transformers`, `faiss`, `mteb`; una vector DB ligera (Qdrant o pgvector) solo en el módulo 18. Ninguna herramienta vetada.
- Ciclo de vida/producción: sí (módulo 18 + playbook).
- Contenido de élite: ambos (🧠 en cada lección + módulo 19 Playbook).

## Proyectos y evaluación
- Hilo conductor: **Políglota**, buscador semántico multilingüe (ES/EN/código) para documentación técnica. El alumno es ML engineer en la startup ficticia «Políglota Labs»; el producto crece módulo a módulo: tokenizer propio → embedder propio → retrieval híbrido (dense + sparse + late interaction) → multimodal → producción.
- Proyectos: plantilla con TODOs, pistas graduadas plegadas, rúbrica con umbrales calibrados con lo medido por la solución y solución oculta tras ⛔ SPOILER.
- Datasets (cadena oficial → espejo → sintético con el mismo esquema; el informe dice qué corrió con datos reales): Wikipedia ES/EN, Flores-200, BEIR (SciFact, FiQA), MIRACL-es, mMARCO, CodeSearchNet, COCO, ViDoRe, LibriSpeech pequeño. Detalle en SYLLABUS.
- Capstone: módulo 20 (Políglota completo) · Guía de entrevistas / system design: `extras/GUIA_ENTREVISTAS.md` · Lectura guiada de papers: `extras/LECTURA_PAPERS.md` · Ruta de carrera: no solicitada.

## Agentes
- Autores (7): A1 {00,01,02} · A2 {03,04,05} · A3 {06,07,08} · A4 {09,10,11} · A5 {12,13,14} · A6 {15,16,17} (ola 1, 6 en paralelo) · A7 {18,19,20} (ola 2, tras A1–A6).
- Revisores: Técnico, Ejecutabilidad, Pedagógico, Verificador de referencias, Élite/industria — por bloque (A: 00–08, B: 09–20), en ese orden; al final una pasada de Consistencia y lenguaje + celdas Gemini sobre los 21 módulos. Alumno simulado: no. Pueden arreglar y reestructurar secciones dentro de un módulo; los cambios mayores se documentan en `_tools/`.

## Repositorio
- Ruta del curso: `tokenization-embeddings-course/` · Rama de trabajo: `claude/tokenization-embeddings-course` · Rama por defecto: `master` · Repo para badges: `padillacm/IA-practice`.
