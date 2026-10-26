# Guía de estudio · Tokenización y Embeddings: de BPE a los modelos modernos

Cómo recorrer el curso, cuánto tiempo dedicar a cada módulo, qué conceptos dependen de cuáles y un glosario
ES/EN. Duración total ≈ 104 h; ritmo sugerido de **8 h/semana**, unas 13 semanas.

## 1. Cómo estudiar cada módulo

1. **Antes de empezar (10 min):** responde de memoria la caja **🔁 Conexión con módulos anteriores** sin desplegar
   las respuestas. Si fallas más de una, repasa esa sección del módulo citado antes de seguir.
2. **Lección:** sigue la caja **🧭 Ruta núcleo vs ampliación** si la hay (módulos 01, 02, 03, 05, 06, 13, 14, 15, 18, 19 y 20). El núcleo
   es lo que necesita el proyecto; la ampliación puede esperar a la semana siguiente (eso ya es repaso espaciado).
3. **Ejemplos a mano:** hazlos con papel *antes* de ejecutar la celda que los comprueba.
4. **👀 Qué debes observar:** léela después de mirar el gráfico, no antes. Primero escribe tu propia conclusión.
5. **Celdas Gemini (🎨/🎬):** si aún no has generado la imagen, el *placeholder* (ASCII) basta para seguir la lección.
6. **Proyecto:** intenta cada TODO al menos 15 min antes de abrir **🪜 Pista 1**, y la Pista 2 solo después. La
   solución tras **⛔ SPOILER** sirve para comparar, no para copiar.
7. **Autoevaluación:** prioriza las preguntas marcadas **(Cálculo)**, **(Diagnóstico)** y **(Transferencia)**.
8. **Repaso espaciado:** al empezar cada semana, vuelve a la autoevaluación del módulo de hace **dos semanas**.

> **Datos sintéticos.** Si no hay red (o Hugging Face está bloqueado), los notebooks usan un corpus de respaldo y lo
> avisan con ⚠️. El código y los conceptos son los mismos; solo cambian los números. Los umbrales de las rúbricas
> están calibrados con el corpus que indica cada proyecto: con datos reales, fíjate en los criterios **relativos**
> (A mejor que B) más que en los absolutos.

## 2. Ruta y tiempos (00–20)

| Semana | Módulo | Nivel | Horas | GPU | Pieza de Políglota | Requiere |
|---|---|---|---|---|---|---|
| 1 | 00 · Intro, entorno e hilo conductor | 🟢 | 2 | CPU | corpus + BM25 + golden set | — |
| 1 | 01 · Unicode, UTF-8, normalización | 🟢 | 4 | CPU | auditoría Unicode + normalizador | 00 |
| 2 | 02 · BPE desde cero | 🟡 | 5 | CPU | BPE propio verificado con tiktoken | 01 |
| 2–3 | 03 · WordPiece, Unigram, SentencePiece | 🟡 | 5 | CPU | comparación de 3 tokenizers | 02 |
| 3 | 04 · Diseño de tokenizers modernos | 🟠 | 5 | CPU | receta de vocabulario (mezcla + V) | 03 |
| 4 | 05 · Patologías y robustez | 🟠 | 5 | CPU/T4 | detector de tokens sub-entrenados + fuzzer | 01, 04 |
| 4–5 | 06 · Tokenizer-free I: bytes y BLT | 🔴 | 5 | T4 (CPU en FAST_DEV) | patcher entrópico vs BPE | 02, 05 |
| 5 | 07 · H-Net y tokenizer transfer | 🔴 | 6 | L4 rec. (CPU en FAST_DEV) | cambiar el tokenizer de un modelo | 05, 06 |
| 6 | 08 · Tokens multimodales y audio | 🟠 | 6 | T4 | tokens VQ de imagen y audio | 02, 06 |
| 7 | 09 · Capa de embedding en LLMs | 🟡 | 5 | CPU/T4 | análisis de embeddings + vocab de dominio | 02, 05, 07 |
| 7 | 10 · Embeddings contextuales y de oraciones | 🟡 | 5 | CPU/T4 | pooling y whitening en retrieval | 09 |
| 8 | 11 · Aprendizaje contrastivo | 🟠 | 6 | L4/A100 rec. (T4 en FAST_DEV) | embedder ES/EN propio | 09, 10 |
| 9 | 12 · Embedders modernos | 🟠 | 5 | T4/L4 | comparativa con Matryoshka y cuantización | 10, 11 |
| 9 | 13 · Dense, sparse y late interaction | 🟠 | 5 | T4 | retrieval híbrido + reranking | 00, 11, 12 |
| 10 | 14 · Indexación y ANN | 🟠 | 5 | CPU/T4 | índice con curvas recall/latencia/memoria | 08, 12, 13 |
| 10–11 | 15 · Evaluación de retrieval | 🟠 | 5 | CPU | banco de evaluación con IC | 00, 13, 14 |
| 11 | 16 · Embeddings multimodales | 🟠 | 5 | L4 rec. (T4 en FAST_DEV) | búsqueda en PDFs con imágenes | 08, 11, 13, 15 |
| 12 | 17 · Interpretabilidad y geometría | 🔴 | 5 | T4/L4 | SAE sobre embeddings | 09–12, 15 |
| 12 | 18 · Producción | 🟠 | 5 | CPU/T4 | servicio con caché y versionado | 12–15, 17 |
| 13 | 19 · Playbook de élite | 🔴 | 4 | CPU | 3 casos de system design | todo (sobre todo 04, 12–15, 18) |
| 13 | 20 · Capstone: Políglota completo | 🔴 | 6 | T4/L4 | Políglota completo | 00–19 |

Bloque A (00–08) ≈ 43 h · Bloque B (09–17) ≈ 46 h · Producción y cierre (18–20) ≈ 15 h.

**Rutas abreviadas** (si tienes un objetivo concreto):
- *Solo tokenización para LLMs:* 00 → 01 → 02 → 03 → 04 → 05 → 07 (§tokenizer transfer) → 09.
- *Solo búsqueda semántica:* 00 → 01 (núcleo) → 02 (núcleo) → 10 → 11 → 12 → 13 → 14 → 15 → 18.
- *Entrevistas:* autoevaluaciones de todos los módulos + 19 + `extras/GUIA_ENTREVISTAS.md`.

## 3. Mapa de conceptos

```mermaid
flowchart LR
  subgraph A["Bloque A · Texto y tokenización"]
    U["Unicode / UTF-8<br/>normalización (01)"] --> BPE["BPE byte-level<br/>regex de pre-tokenización (02)"]
    BPE --> ALG["WordPiece · Unigram<br/>SentencePiece (03)"]
    BPE --> VOC["Diseño de vocabulario<br/>fertilidad · paridad (04)"]
    ALG --> VOC
    VOC --> PAT["Patologías<br/>tokens sub-entrenados (05)"]
    U --> PAT
    BPE --> BYTES["Modelos de bytes<br/>parcheo por entropía · BLT (06)"]
    BYTES --> HNET["H-Net<br/>dynamic chunking (07)"]
    PAT --> TT["Tokenizer transfer<br/>inicializar embeddings (07)"]
    BPE --> VQ["Tokens de imagen/audio<br/>VQ · FSQ · RVQ (08)"]
  end
  subgraph B["Bloque B · Embeddings"]
    EMB["Capa de embedding (09)"] --> CTX["Embeddings de oraciones (10)"]
    CTX --> CON["Contrastivo (11)"] --> MOD["Embedders modernos (12)"]
    MOD --> HYB["Dense · sparse · late (13)"] --> ANN["ANN (14)"]
    HYB --> EVAL["Evaluación (15)"]
    MOD --> MM["Multimodal (16)"]
    MOD --> INT["Interpretabilidad (17)"]
  end
  M00["Métricas y BM25 (00)"] --> HYB
  M00 --> EVAL
  TT --> EMB
  PAT --> EMB
  VQ --> MM
  VQ -. "k-means ↔ PQ" .-> ANN
  ANN --> PROD["Producción (18)"]
  EVAL --> PROD
  INT -. "inversión de embeddings" .-> PROD
  U -. "NFC en la clave de caché" .-> PROD
  VOC -. "prima de tokens = coste" .-> PROD
  PROD --> PB["Playbook (19)"]
  EVAL --> PB
  PB --> CAP["Capstone Políglota (20)"]
  PROD --> CAP
```

Ideas que atraviesan el curso (vuelve a ellas en cada módulo):
- **Compresión:** BPE (02) es un compresor voraz; bits por byte (01, 02, 06) mide la tasa; BLT (06) reparte el
  cómputo según la entropía; VQ (08) es compresión con pérdida; PQ (14) comprime vectores.
- **IR/recsys:** índice invertido y BM25 (00) → sparse aprendido (13); *cold start* de ítems ↔ inicializar tokens
  nuevos (07, 09); two-tower ↔ bi-encoder (10–11); k-means ↔ VQ (08) ↔ IVF/PQ (14).
- **Lingüística:** grafemas y escrituras (01), morfología y fronteras (03), fertilidad y «token tax» por idioma (04).
- **Medir bien:** nDCG con convenciones fijas e IC bootstrap (00) → evaluación a fondo (15).

## 4. Glosario ES/EN · Bloque A (00–08)

| Español (como se usa en el curso) | Inglés | Definición breve | Módulo |
|---|---|---|---|
| token | token | unidad discreta de un vocabulario, con un id entero | 00 |
| tokenizer (m.) | tokenizer | componente que convierte texto en ids y de vuelta; no se usa «tokenizador» | 00 |
| embedding | embedding | vector denso aprendido asociado a una unidad o a un texto | 00 |
| índice invertido | inverted index | término → lista de (documento, frecuencia) | 00 |
| BM25 | BM25 (Okapi BM25) | puntuación léxica con IDF, saturación ($k_1$) y normalización por longitud ($b$) | 00 |
| ganancia acumulada descontada normalizada | nDCG@k | calidad de un ranking con descuento logarítmico por posición | 00 |
| exhaustividad en k | Recall@k | fracción de relevantes recuperados en el top-k | 00 |
| rango recíproco medio | MRR@k | media de 1/posición del primer relevante | 00 |
| conjunto de referencia | golden set / qrels | consultas con sus documentos relevantes anotados | 00 |
| intervalo de confianza bootstrap | bootstrap CI | IC obtenido remuestreando consultas con reemplazo | 00 |
| punto de código | code point | número que Unicode asigna a un carácter (U+00F1) | 01 |
| grafema | grapheme cluster | lo que el lector percibe como «un carácter» | 01 |
| normalización (NFC/NFD/NFKC/NFKD) | Unicode normalization | formas canónicas o de compatibilidad del mismo texto | 01 |
| homoglifo | homoglyph / confusable | carácter visualmente igual a otro de otra escritura | 01 |
| mojibake | mojibake | texto corrompido por decodificar con la codificación equivocada | 01 |
| codificación por pares de bytes | Byte Pair Encoding (BPE) | fusiona iterativamente el par adyacente más frecuente | 02 |
| merge (sust. m., pl. *merges*); verbo «fusionar» | merge | regla aprendida (a, b) → ab; su orden forma parte del tokenizer. «Fusión» = el acto de aplicar un merge | 02 |
| pre-tokenización; el componente es el **pre-tokenizer** (m.) | pre-tokenization / pre-tokenizer | partición previa (regex) dentro de la cual se aplican los merges | 02 |
| BPE a nivel de byte | byte-level BPE | BPE con alfabeto inicial de 256 bytes: sin `[UNK]` | 02 |
| tokens especiales | special tokens | tokens de control (`<|endoftext|>`, roles de chat) | 02, 04 |
| WordPiece | WordPiece | fusiona por ganancia de verosimilitud; inferencia *longest-match-first* (`##`) | 03 |
| modelo de lenguaje unigrama | Unigram LM | vocabulario grande que se poda con EM; segmentación por Viterbi | 03 |
| regularización de subpalabras | subword regularization / BPE-dropout | muestrear segmentaciones distintas al entrenar | 03 |
| pipeline del tokenizer (m.) | tokenizer pipeline | normalizer → pre-tokenizer → model → post-processor → decoder | 03 |
| fertilidad | fertility | tokens por palabra | 03, 04 |
| bytes por token | bytes per token | bytes UTF-8 cubiertos por cada token (compresión) | 02–04 |
| **prima de tokens** (por idioma); paridad = prima ≈ 1 | tokenization premium / parity (coloquial: «token tax») | tokens de un idioma ÷ tokens del inglés para el mismo contenido. Forma canónica del curso: no se usa «impuesto» | 00, 02, 04 |
| prima de bytes | — | bytes UTF-8 extra que paga una escritura frente al ASCII por la misma información | 01, 06 |
| plantilla de chat | chat template | formato con roles y tokens especiales que se tokeniza | 04 |
| tokens que cruzan palabras | superword tokens (SuperBPE) | merges que atraviesan espacios | 04 |
| token sub-entrenado / glitch | under-trained / glitch token | token del vocabulario que el modelo casi no vio al entrenar | 05 |
| curación de la frontera del prompt | token healing | retroceder un token y restringir la generación al prefijo | 05 |
| inyección de tokens | token injection / smuggling | colar tokens de control o texto invisible en la entrada | 05 |
| fuzzing por propiedades | property-based fuzzing | generar entradas y comprobar invariantes | 05 |
| bits por byte (abrev. **bpb**, en minúscula) | bits per byte (bpb) | entropía cruzada normalizada por bytes: compara tokenizaciones distintas | 06, 07 |
| parche | patch | grupo de bytes que procesa un paso del transformer global | 06 |
| parcheo por entropía | entropy-based patching | abrir parche cuando $H(x_i)$ supera un umbral | 06 |
| parcheo incremental | incremental patching | la segmentación del prefijo no depende del futuro | 06 |
| troceado dinámico | dynamic chunking (H-Net) | fronteras aprendidas de extremo a extremo con un *router* | 07 |
| estimador de paso directo | straight-through estimator (STE) | forward discreto, backward como identidad | 07, 08 |
| transferencia de tokenizer | tokenizer transfer | cambiar el vocabulario de un modelo ya entrenado | 07 |
| FVT / FOCUS / WECHSEL / ZeTT | (igual) | métodos para inicializar los embeddings del vocabulario nuevo | 07 |
| cuantización vectorial | vector quantization (VQ) | sustituir un vector por su centroide más cercano del codebook | 08 |
| libro de códigos | codebook | conjunto de K vectores (centroides) del cuantizador | 08 |
| pérdida de compromiso | commitment loss | término que ancla el encoder a su código elegido | 08 |
| cuantización escalar finita | finite scalar quantization (FSQ) | redondear cada dimensión a pocos niveles: sin codebook aprendido | 08 |
| cuantización vectorial residual | residual VQ (RVQ) | cuantizadores en cascada sobre el residuo | 08 |
| códec neuronal | neural audio codec | SoundStream, EnCodec, Mimi: audio → tokens discretos | 08 |
| tasa-distorsión | rate-distortion | compromiso entre bits (bpp, kbps) y calidad (PSNR, SNR) | 08 |

**Convenciones de escritura del bloque A** (pasada de consistencia): *coste/costes* (no «costo»), *video* (no «vídeo»), tuteo singular; grafías oficiales: GPT-2, Llama 3, SentencePiece, `tiktoken`, Hugging Face, ByT5, MegaByte (MEGABYTE en el título del paper), H-Net, EnCodec, SoundStream, FLORES-200/FLORES+. Detalle en `_tools/REVISION_CONSISTENCIA.md`.

## 5. Bloque B (09–20)

**Columna «Requiere» confirmada** (revisión pedagógica B) contra los prerrequisitos de cada lección y lo que usan
sus proyectos; se corrigieron 09, 11–18 en la tabla de la sección 2. Los tiempos no cambian.

**Cómo estudiar el bloque B.** Además de lo de la sección 1:
- Las cajas **🧭** del bloque están en 13, 14, 15, 18, 19 y 20 (y 16–17 si la tienen): el núcleo es siempre lo que usa
  el proyecto.
- Cada lección tiene ejemplos **✍️ a mano** antes del código (pooling, whitening, InfoNCE, int8/binaria, MaxSim, PQ,
  bootstrap pareado, punto de equilibrio API/GPU, PSI, team-draft, árbol del índice, criterios de aceptación):
  hazlos en papel.
- Los **🔁** del bloque B repasan a propósito módulos lejanos: métricas e IC del 00 (en 11, 13, 19, 20), Unicode del
  01 (18, 19), prima de tokens del 04 (09, 10, 15, 18), VQ del 08 (12, 14). Si fallas una, vuelve a ese módulo.
- Las conclusiones de las 👀 y las notas de calibración que dependen del **corpus o modelo de respaldo** lo dicen
  explícitamente; con datos y modelos reales, defiende la **forma** de las curvas, no los números.
- En 20 hay una tabla **«🧩 Qué integra este capstone»**: úsala como índice de repaso final del curso.

**Rutas abreviadas adicionales:**
- *Solo embeddings para RAG (≈ 30 h):* 00 → 10 → 11 → 12 → 13 → 14 → 15 → 18 → 20 (núcleo de cada 🧭).
- *Evaluación y decisiones (≈ 15 h):* 00 → 15 → 19 → 20 §1, §7 y §8.
- *Entrevistas de system design:* 12 (§5) → 14 (§1, §10) → 18 → 19 (lección + proyecto) → `extras/GUIA_ENTREVISTAS.md`.

### Glosario ES/EN · Bloque B (09–20)

Misma convención que el bloque A: término técnico en inglés cuando es el habitual, **coste/costes**, **prima de
tokens**, **tokenizer**, **pipeline** (m.).

| Español (como se usa en el curso) | Inglés | Definición breve | Módulo |
|---|---|---|---|
| matriz de embeddings (de entrada) | embedding matrix / input embeddings | tabla $V\times d$: fila = vector de un token; lookup = one-hot·E | 09 |
| matriz de salida (*unembedding*) | unembedding / LM head | $W_U$: los logits son productos escalares con el estado oculto | 09 |
| pesos atados | weight tying | la misma matriz como entrada y salida | 09 |
| cuello de botella del softmax | softmax bottleneck | rango ≤ d+1 de los log-probs de un LM | 09 |
| inicialización por subtokens | subtoken (mean) initialization | fila nueva = media de las filas de sus piezas | 09, 07 |
| pooling (media, CLS, máximo, último token) | pooling | cómo se resume una secuencia de estados en un vector | 10, 12 |
| anisotropía | anisotropy | los vectores comparten una dirección dominante; el coseno medio es > 0 | 09, 10 |
| blanqueado | whitening | $(x-\mu)U\Lambda^{-1/2}$: media 0 y covarianza identidad | 10 |
| bi-encoder / cross-encoder | bi-encoder / cross-encoder | codificar por separado (indexable) / el par junto (reranker) | 10, 13 |
| prefijos e instrucciones | query/passage prefixes, instructions | texto fijo que indica el papel (`query:`) o la tarea | 10, 12 |
| aprendizaje contrastivo | contrastive learning | acercar pares positivos y alejar negativos | 11 |
| InfoNCE | InfoNCE (MNRL en sentence-transformers) | entropía cruzada sobre la matriz de similitudes del lote | 11 |
| temperatura | temperature ($\tau$) | escala de los logits; pequeña = se concentra en los negativos duros | 11 |
| negativos del lote | in-batch negatives | los positivos de otros pares hacen de negativos | 11 |
| negativos duros / falsos negativos | hard negatives / false negatives | parecidos pero irrelevantes / relevantes sin juicio | 11 |
| alineación y uniformidad | alignment / uniformity | dos propiedades del espacio contrastivo (Wang & Isola) | 11 |
| Gradient Cache | Gradient Cache | lotes grandes con memoria constante, gradiente exacto | 11 |
| Matryoshka (MRL) | Matryoshka Representation Learning | prefijos del vector útiles por sí solos; se renormaliza al recortar | 12 |
| cuantización int8 / binaria | scalar (int8) / binary quantization | 1 byte o 1 bit por dimensión; binaria + rescoring | 12, 18 |
| reordenado con mayor precisión | rescoring | recuperar candidatos con binaria y reordenar con float/int8 | 12 |
| MTEB / MMTEB | Massive (Multilingual) Text Embedding Benchmark | banco público de tareas de embeddings | 12, 15 |
| sparse aprendido | learned sparse retrieval (SPLADE) | pesos por término del vocabulario aprendidos por un MLM | 13 |
| interacción tardía | late interaction (ColBERT) | un vector por token y puntuación MaxSim | 13 |
| MaxSim | MaxSim | suma, por token de la query, de su máxima similitud en el documento | 13 |
| MUVERA | MUVERA (fixed dimensional encodings) | multi-vector → un vector de dimensión fija | 13 |
| fusión por rango recíproco | Reciprocal Rank Fusion (RRF) | $\sum 1/(k+\text{rango})$; $k=60$ por convención | 13, 20 |
| combinación lineal (convexa) | convex/linear combination | $\alpha$·denso + (1−α)·BM25 normalizados; α sin fuga (CV) | 13, 19 |
| troceado tardío | late chunking | embeber el documento entero y trocear después | 13 |
| búsqueda aproximada de vecinos | approximate nearest neighbor (ANN) | top-k con error controlado a cambio de latencia/memoria | 14 |
| exhaustividad de vecinos | neighbor recall@k | fracción del top-k exacto que devuelve el índice (≠ Recall@k de relevancia) | 14 |
| fichero invertido | IVF (inverted file) | listas por centroide; se recorren `nprobe` listas | 14 |
| cuantización por producto | product quantization (PQ), OPQ | VQ por subespacios; distancias con tablas (ADC) | 14 |
| HNSW | Hierarchical Navigable Small World | grafo por capas; `M`, `efConstruction`, `efSearch` | 14 |
| Vamana / DiskANN | Vamana / DiskANN | grafo pensado para SSD con PQ en RAM | 14 |
| RaBitQ / ScaNN | RaBitQ / ScaNN (anisotropic quantization) | cuantizaciones con garantías / orientadas al producto escalar | 14 |
| búsqueda filtrada | filtered search (pre/post-filtering, ACORN) | top-k restringido por metadatos | 14, 18 |
| test ciego | held-out / blind test | split que se usa una sola vez, al final | 15, 20 |
| bootstrap pareado / permutación de signos | paired bootstrap / sign-flip test | IC y p-valor de la diferencia por query | 15 |
| comparaciones múltiples (Holm) | multiple comparisons (Holm–Bonferroni) | corregir p-valores al comparar muchos sistemas | 15 |
| acuerdo entre anotadores | inter-annotator agreement (Cohen's κ) | fiabilidad de los juicios | 15 |
| LLM como juez | LLM-as-judge | etiquetar relevancia con un LLM (🟡, validar con humanos) | 15 |
| sesgo de *pooling* | pooling bias | los qrels favorecen a los sistemas que los generaron | 15, 19 |
| límite de dimensión | LIMIT (Weller et al. 2025) | conjuntos top-k que un embedding de dimensión d no representa | 15 |
| deriva | drift (PSI) | cambio de la distribución de queries o documentos; PSI sin etiquetas | 15, 18 |
| brecha de modalidad | modality gap | imágenes y textos ocupan conos separados en CLIP | 16 |
| SigLIP / ColPali | SigLIP / ColPali | contrastivo con sigmoide / late interaction sobre páginas | 16 |
| autoencoder disperso | sparse autoencoder (SAE) | descompone un embedding en rasgos dispersos interpretables | 17 |
| inversión de embeddings | embedding inversion (vec2text) | reconstruir el texto a partir del vector | 17, 18 |
| micro-batching dinámico | dynamic micro-batching | agrupar peticiones con `max_wait` para ganar throughput | 18 |
| latencia de cola | tail latency (p99), hedged requests | lo que ve 1 de cada 100 usuarios; se amplifica con *fan-out* | 14, 18 |
| despliegue azul/verde con alias | blue/green, collection alias | índice nuevo en paralelo y cambio atómico de puntero | 18 |
| adaptador entre versiones | embedding adapter (ridge / Procrustes), BCT | puente lineal v2 → v1 sin re-embeber | 18 |
| intercalado | interleaving (team-draft) | evaluación online pareada dentro de la misma impresión | 18 |
| maldición del ganador | winner's curse | el mejor de muchos está sesgado al alza | 19 |
| criterios de aceptación | acceptance criteria | umbrales fijados antes de construir | 20 |
| registro de decisiones | ADR (architecture decision record) | informe de decisiones con alternativas y evidencia | 20 |
