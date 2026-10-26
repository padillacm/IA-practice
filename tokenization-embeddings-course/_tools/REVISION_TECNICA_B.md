# Revisión técnica · Bloque B (módulos 09–20 y extras)

Revisor técnico B (oct-2026). Se leyó el código de los builders (`_tools/builders/build_NN.py` y auxiliares) y se
contrastaron fórmulas y cifras con fuentes primarias cuando hizo falta. Cambios aplicados en los builders y notebooks
regenerados; recomendaciones no aplicadas al final de cada módulo. Métricas canónicas: `poliglota_src/metrics.py`
(módulos 00–14) y `15_evaluacion_retrieval/poliglota_eval.py` (15–20) revisadas: ganancia lineal, dedup, convención
trec_eval, bootstrap por queries, test pareado por *shift*, sign-flip y Holm correctos.

## 09 · Capa de embedding en LLMs
- Verificado: one-hot·E, gradiente de salida (p_j − 1[j=y])·h y colapso hacia −h̄, decaimiento AdamW e^{−ηλn},
  rango ≤ d+1 del log-softmax, cifras de GPT-2 small (38 597 376 = 31 % de 124 439 808; 163 037 184 sin tying),
  memoria de logits (8.4 GB), autoevaluación (262 M = 21.8 %; e^{−1}), Godey et al. 2024, nanoGPT 50 304.
- **Arreglado:** R2 del proyecto («colapso de filas no vistas») es un test válido solo con el mini-GPT-2 de fallback
  (allí «no visto en Políglota» = «nunca visto al entrenar»); con GPT-2 real fallaría sin ser un error del alumno.
  Ahora R2 solo se exige en el fallback y la rúbrica lo explica.
- Recomendación: `bpb_y_fuga` trunca a T=64 *tokens*, así que el tokenizer extendido evalúa un trozo de texto algo más
  largo que el base; bpb lo normaliza, pero truncar por bytes haría la comparación exacta.

## 10 · Embeddings contextuales y de oraciones
- Verificado: pooling con máscara (incl. último token con padding a izquierda/derecha), whitening W = UΛ^{−1/2}
  (y su comprobación W^⊤ΣW = I), ABTT, descomposición de L2 con vectores unitarios, cifras de SBERT (Tabla 1: BERT
  media 54.81, CLS 29.19, GloVe 61.32), autoevaluación (√0.4 ≈ 0.632; 5000 s), E5 `query:`/`passage:`.
  El proyecto elige en validación y reporta en test (correcto) y ajusta μ/W con documentos, no con consultas.
- **Arreglado:** la lección imprimía «whitening k=best» con el k elegido sobre las propias consultas de test sin
  avisar (contradice el secreto 4): ahora la salida lo etiqueta como optimista. El comentario del split decía
  «estratificada por idioma» y es un hash del qid (no estratificado).

## 11 · Aprendizaje contrastivo
- Verificado: gradiente (p_ij − 1[i=j])/τ, derivación de la cota de Oord (pasos 1–4, con 1+(K−1)a ≥ Ka para a ≤ 1) y
  la cota rigurosa de Poole et al.; experimento gaussiano (I = −½ log(1−ρ²) = 1.96 nats con crítico óptimo; la
  constante de normalización se cancela en el softmax); saturación en log K; McAllester & Stratos 2020; Tschannen et
  al. 2020; τ de SimCSE (0.05) y E5 (0.01), MNRL `scale=20`; DPR (1 negativo BM25, lotes de 128); TopK-PercPos 95 %;
  CCPairs ≈ 270M; Gradient Cache exacto; autoevaluación (p = 0.599, pérdida 0.51; log 64 = 4.16).
- **Arreglado:** la respuesta del diagnóstico 3 («pérdida muy baja + colapso») daba «temperatura enorme» como causa;
  con negativos reales un modelo colapsado tiene pérdida ≈ log B, así que pérdida baja + colapso implica que los
  negativos no entran en la pérdida. Reescrita.
- Recomendaciones: (a) los negativos duros de un par se comparten como columnas con todo el lote; `grupo` evita
  conceptos repetidos entre consultas, pero un duro del par j puede ser del concepto de i (falso negativo cruzado):
  mencionarlo. (b) Los pares débiles del proyecto incluyen documentos relevantes del test (primera frase → resto):
  es entrenamiento transductivo legítimo (como ICT/GPL), pero conviene decirlo explícitamente.

## 12 · Embedders modernos
- Verificado: pérdida MRL con renormalización por prefijo, ⟨a,b⟩ = d − 2H para ±1, int8 por dimensión calibrado en
  el corpus, binario idéntico a `quantize_embeddings("ubinary")`, overlap@10 contra float32 a igual dimensión (la
  referencia correcta), aritmética de memoria (40.96/10.24/1.28 GB; autoevaluación 76.8/19.2/2.4/6.4 GB y caso de
  50 M), coseno de Hamming (0.805), cifras de familias (Qwen3-Embedding 32k y MRL 32–1024, EmbeddingGemma 308 M/2k,
  gte-multilingual-base 305 M/8192, nomic v2 MoE 475 M/305 M activos, Cohere Embed v4 256–1536/128k, OpenAI
  `dimensions` 25-ene-2024, caída 1–5 % sin instrucción en Qwen3, ≈ 96 % con binario + rescoring).
- **Arreglado (fechas «verificar»):** Gemini Embedding 2 pasó a GA (`gemini-embedding-2`) el 22-abr-2026 (blog de
  Google; el módulo 16 ya lo decía, el 12 seguía en «preview»); Voyage-4 anunciada el 15-ene-2026 (MongoDB; familia
  large/base/lite/nano abierta), antes «fuentes discrepantes»; jina-embeddings-v5-text: nano 768 / small 1024 con
  MRL hasta 32, 239 M / 677 M (antes «—»); `gemini-embedding-001`: contexto 2048 y la nota «re-normaliza al reducir»
  (falsa: solo la salida de 3072 viene normalizada) corregida; dimensiones de multilingual-e5 y BGE-M3 completadas.
  Añadida la referencia del anuncio de GA.
- **Arreglado:** se atribuía a la documentación de `sentence-transformers` una advertencia explícita contra calibrar
  int8 con queries; lo que dice es que `calibration_embeddings` sea representativo. Matizado (sección 5 y secreto 4).
- Pendiente: el contexto de jina-v5-nano (8k en Elastic/tabla, 32k en el texto de la tarjeta) sigue marcado «verificar».

## 13 · Dense, sparse y late interaction
- Verificado: BM25 con IDF de Lucene (declarado; el BM25 canónico del 00 usa IDF Okapi con suelo ε, como
  `rank_bm25`: son variantes distintas y ambas están etiquetadas), SPLADE (log(1+ReLU), max-pooling desde v2, FLOPS
  = Σ_j ā_j²), MaxSim y su monotonía con la longitud, MUVERA (SimHash, suma en la query, media en el documento,
  relleno de cubetas vacías solo en el documento, dimensión R·2^k·d), RRF (k = 60; autoevaluación 0.03226 ≈ 0.03226),
  fusión convexa con α por validación cruzada de 2 pliegues (sin fuga), Jaccard de top-10, FDE 10 240 d = 40.96 GB.
- **Arreglado:** ColBERTv2 a d = 128 y 2 bits se daba como «33 B/token»; el paper codifica cada vector en 20 B (1 bit)
  o 36 B (2 bits): 32 B de residuo + 4 B de id de centroide. Corregido en el texto y en la tabla de costes (el juguete
  sigue usando 1 B de id porque tiene 256 centroides, y ahora se explica).

## 14 · Indexación ANN
- Verificado: neighbor recall@k contra fuerza bruta del mismo conjunto (incl. el GT filtrado `ok[exacto_topk(X[ok])]`
  en búsqueda filtrada), latencia por query con batch = 1 y un hilo, tamaño serializado real, coste de IVF,
  PQ/ADC (compresión 4d/m, refine exacto), OPQ por Procrustes, MiniHNSW (nivel ⌊−ln U·m_L⌋ con P(ℓ ≥ l) = M^{−l},
  heurística de selección, grado 2M en la capa 0), Vamana con poda α, ejemplo anisótropo de ScaNN (MSE elige c1,
  pérdida con η = 4 elige c2), estimador de RaBitQ ⟨ō,q⟩/⟨ō,o⟩ y su factor de corrección.
- **Arreglado:** la latencia del pre-filtro medía solo el producto matricial y no la selección del top-k, lo que
  favorecía al pre-filtro frente al filtro en grafo; ahora incluye `argpartition`.
- Recomendación: en la tabla de filtrado, el post-filtro usa efSearch = 100 y el filtro en grafo 64 (presupuestos
  distintos); y el filtro en grafo se cronometra en lote, no con batch = 1 como el resto del módulo.

## 15 · Evaluación de retrieval
- `poliglota_eval.py` (generado) coincide con las métricas canónicas del 00 (ganancia lineal por defecto, dedup,
  queries sin relevantes excluidas, query sin ranking = 0) y añade `exp_gain`, precisión/k, bootstrap percentil
  por queries, bootstrap pareado con p por *shift*, sign-flip y Holm (todos correctos). Su BM25 usa IDF de Lucene,
  el canónico del 00 IDF Okapi con suelo ε: es otra variante (las métricas sí coinciden).
- Verificado: ejemplo resuelto (DCG 2.754, IDCG 4.762, nDCG@5 0.578), 9 grupos de tests de bordes, Smucker et al.
  2007, κ de Cohen. **LIMIT contrastado con el PDF v2 (arXiv:2508.21038, ICLR 2026):** Teorema 1 por empaquetamiento
  de esferas d ≥ log C(n,k)/log(1+1/γ), Tabla 1 con γ = 0.1 (n = 10⁶: 12 para k = 2 y 425 para k = 100), ajuste cúbico
  −10.5322 + 4.0309d + 0.0520d² + 0.0037d³, LIMIT 50 K docs / 1000 queries, Tabla 5 (BM25 85.7/93.6, Gemini Embed
  3072-d 1.6/10.0, GTE-ModernColBERT 23.1): todo correcto.
- **Arreglado:** el texto de la doble anotación decía «anotadores 90 % fiables entre sí → κ ≈ 0.64»; la simulación
  hace que cada uno acierte el 90 % frente a la verdad (acuerdo entre ellos ≈ 0.82, κ ≈ 0.64). La caja de empates
  decía que «dos ejecuciones» de `argsort` dan métricas distintas; es determinista para la misma entrada: lo que
  varía es entre implementaciones, órdenes de entrada o versiones.
- Recomendación: el LIMIT en miniatura usa LSI (proyección no optimizada contra las qrels); que «la dimensión limita
  al denso» allí mezcla el límite teórico con la pérdida de información de la SVD. El texto ya avisa de que exagera.
