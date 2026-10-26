# Revisión élite / industria · Bloque B (módulos 09–20)

Revisor élite B (oct-2026), con la vara «experto de laboratorio/empresa top» (equipos de embeddings, search y retrieval).
Criterio: ¿las secciones 🏭 y 🧠 son concretas, verificables y explican **por qué** importan? ¿Falta algo que todo
experto sabría? Donde la lección solo mencionaba, se añadió **implementación pequeña** (CPU, `FAST_DEV_RUN`, respaldos
existentes). Toda afirmación nueva tiene fuente comprobada en esta revisión o se presenta como práctica habitual sin
cifra. Cambios en los builders; notebooks regenerados y ejecutados con `nbclient` en una copia del scratchpad
(`OMP_NUM_THREADS=1`, CPU). Orden de trabajo descendente (20 → 09) para no coincidir con el verificador de referencias B.
No se deshizo nada de las revisiones técnica, pedagógica y de ejecutabilidad.

## 20 · Capstone
Diagnóstico: integración muy sólida (decisiones solo en dev, test ciego una vez, informe generado). 🧠 #2 «evalúa lo
que despliegas» era un principio sin medición, y el criterio «neighbor recall ≥ 0.95» se presentaba como si fuera
calidad. Faltaba lo que hace un equipo de búsqueda antes de tocar una perilla: **descomponer la pérdida por escalón**.
- **Añadido §6b «Presupuesto de error»** (1 celda + 👀): nDCG@10 en dev por escalón (exacto/d completa/float32 →
  d recortada → int8 → HNSW del servicio → fusión) y, con las copias ruidosas del §5 como distractores casi
  duplicados en un HNSW M = 16, **neighbor recall@10 frente a relevantes conservados y pérdida de nDCG** por
  `efSearch`. Medido (fallback, FAST_DEV_RUN): la fusión aporta +0.141 y los demás escalones ≈ 0; a ef = 10
  neighbor recall 0.565, relevantes 0.774, pérdida de nDCG 0.033; a ef ≥ 64 la «pérdida» es negativa (el exacto se
  llena de casi duplicados): el neighbor recall mide fidelidad al exacto, no calidad. Lección 59 → 62 celdas, 47 s.
- 🧠 #2 reescrito (descomponer + neighbor recall como cota prudente) y **#8 nuevo**: el golden set caduca el día del
  lanzamiento (muestrear queries reales, huérfanas; enlaza 18 §9 y 19 §3).
- 🏭 Contextual Retrieval con cifras verificadas en el post de Anthropic (fallo top-20 5.7 % → 3.7 % / 2.9 % / 1.9 %,
  1.02 $ por millón de tokens de documento) y la lectura «ablación por escalón + coste al lado de la ganancia».

## 19 · Playbook de élite
Diagnóstico: el módulo ya convierte las prácticas en código (árboles, trampas T1–T4, gap offline/online, costes a
escala, galería F1–F4, linter de PRs) y sus 🏭/🧠 son concretos. Hueco claro: **chunking**, la decisión que fija $N$
en la calculadora de costes, no se medía en ningún módulo (13 cubre *late chunking*, no tamaño ni agregación).
- **Añadido §4b «Chunking»** (ampliación, en la 🧭): truncado vs troceado, agregación MaxP/FirstP con la evidencia de
  Dai & Callan (SIGIR 2019, Tabla 2 verificada en el PDF: Robust04 título MaxP 0.469 vs FirstP 0.444; ClueWeb09-B
  descripción FirstP 0.272 vs MaxP 0.262; título añadido a cada pasaje), deduplicación por documento. 🧪 ventanas
  w ∈ {16, 32, 32+solape 16, 64, 128}, denso v2 y BM25 sobre chunks, nDCG@10 a nivel de documento y vectores/doc.
  Medido (respaldo): w = 16 hunde el denso (0.742 vs 0.861, ×7.1 vectores); MaxP gana con w = 16 y FirstP con w = 64
  (0.881 vs 0.863); BM25 con w = 64 supera al documento entero (0.874); el solapamiento no mejora y cuesta ×1.6.
- 🧠 **#8 nuevo**: el tamaño de chunk es un hiperparámetro con factura (se elige en dev). Referencia añadida.
  Lección 61 → 64 celdas.

## 16 · Embeddings multimodales
Diagnóstico: 🧠 ya medido y concreto (gap e intrusos en índices mixtos, τ como geometría, falsos negativos en el
lote, almacenamiento de ColPali, OCR como baseline duro). Faltaba la limitación que todo equipo multimodal conoce:
**la precisión de retrieval no mide composición** (atributos, relaciones, orden).
- **Añadido §3b** (1 celda + 👀): con la torre de texto del CLIP en miniatura, «un círculo rojo un cuadrado azul» y
  «un círculo azul un cuadrado rojo» dan coseno 1.000, igual que un caption con el orden destruido; el control
  (cambiar el color) da 0.482. Conexión con ARO (Yuksekgonul et al., ICLR 2023, verificado en arXiv: > 50 000 casos;
  los VLM reales se comportan casi como bolsas de palabras porque el contraste en lote no necesita el orden; remedio:
  negativos duros composicionales) y con Políglota (slice composicional en el golden set).
- 🧠 #6 reescrito en ese sentido (antes solo «el vector medio es invariante al orden»). Referencia añadida.
  Lección 64 → 67 celdas; ejecución completa 394 s en CPU.

## 15 · Evaluación de retrieval
Revisado sin cambios. Es el módulo más completo del bloque en lo que pide el encargo: gap offline/online y MTEB como
filtro (🏭), qrels incompletos y falsos negativos (🧠 #4, Arabzadeh et al.), LLM-as-judge con sus sesgos y una
simulación del sesgo léxico (§7), contaminación y brecha público–privado (§9, RTEB), drift (§10), potencia y
tamaño del golden set (§5). Con 93 celdas no se añadió nada. Recomendación no aplicada: una simulación de
presupuesto de anotación fijo (muchas queries con juicios someros frente a pocas con juicios profundos); no se
encontró en esta revisión una fuente primaria accesible para citar su conclusión clásica.

## 14 · Indexación ANN
Diagnóstico: 🧠 de alto nivel (10 puntos, protocolo de medición, refine, filtros por selectividad, tombstones,
RaBitQ), con el matiz de que el #1 pedía medir «sobre queries reales» sin mostrar por qué. Es un hueco de experto:
**los índices se adaptan a la distribución de los documentos y las queries de retrieval asimétrico viven en otra
región**.
- **Añadido en §10 «Las queries no son documentos»** (1 celda + 👀): las queries se desplazan con una dirección fija
  $g\,u$ (el modelo más simple del *modality gap* o de un prefijo) y se recalcula el exacto para cada $g$. Medido
  (FAST_DEV_RUN, N = 20 000, d = 64): HNSW ef = 32 0.841 → 0.624 de g = 0 a g = 2; IVF nprobe = 4 0.696 → 0.282; a
  ef = 64 con g = 2 (0.792) queda por debajo de ef = 32 sin desplazar. Fuente: OOD-DiskANN (Jaiswal et al. 2022,
  abstract verificado en arXiv: latencia «un orden de magnitud o más» peor a recall fijo con queries OOD; muestra de
  queries ≈ 1 % del índice en la construcción). Consecuencias: ajustar con queries reales con su prefijo, reajustar
  al cambiar prefijo/instrucción, más `efSearch` en búsqueda cruzada.
- 🧠 #1 ampliado con el porqué; referencia añadida. Lección 56 → 59 celdas; ejecución completa 203 s.

## 18 · Producción
Diagnóstico: el módulo cubre con medición casi toda la lista del encargo (coste API/GPU, batching y padding, p99 y
*tail at scale*, caché versionada, migración con adaptadores y alias, cuantización en RAM/disco, filtros y
multi-tenant en Qdrant, privacidad e inversión, drift sin etiquetas, interleaving vs A/B), con 🧠 concretos. Con 76
celdas no se añadió sección nueva. Hueco puntual: la **reproducibilidad numérica** de los vectores servidos.
- 🧠 #1 ampliado: no hay reproducibilidad bit a bit fuera del contrato de versión (no asociatividad + kernels que
  cambian según el tamaño de lote, que depende de la carga; He / Thinking Machines Lab, 10-sep-2025, verificado por
  búsqueda: el blog no resolvía desde el proxy, se citan solo su tesis central y la fecha). Consecuencias: tolerancia
  en CI, nunca hash del vector como identidad, clave = texto normalizado + versión. Medido en esta revisión con el
  `MiniEncoder` del §2 (CPU, 1 hilo): el mismo texto solo o en un lote de 32 con padding sale idéntico bit a bit en
  float32 y bf16 (se dice explícitamente que el efecto aparece con kernels sensibles al lote). Referencia añadida.

## 17 · Interpretabilidad y geometría
Diagnóstico: 🧠 excelente y medido (control tasks, leer ≠ usar, diferencia de medias frente a SAE, estabilidad entre
semillas, rogue dimensions, vec2text). Faltaba la patología geométrica con más impacto directo en un buscador:
**hubness** (no aparecía en ningún módulo).
- **Añadido §5b** (1 celda + 👀): k-ocurrencia $N_{10}$, asimetría, máximo y % de anti-hubs; mecanismo con gaussianas
  con una dirección común a d = 20/100/500 (crudo, centrado, CSLS) y medición en LSI-64 de Políglota. Medido:
  asimetría 1.46 → 4.68 → 5.53 al subir d (máx N10 hasta 317 de 2000 listas, hasta 18.6 % de anti-hubs); centrar la
  baja a 0.1–0.4 y CSLS a ≈ 0.6–0.8; LSI-64 de Políglota apenas tiene hubness (0.38), y se explica por qué (casi
  centrado, clusters compactos) y que un Transformer anisótropo hay que medirlo. Enlace con el monitor sin etiquetas
  de 18 §9. Fuentes: Radovanović et al. (JMLR 2010) y CSLS de Conneau et al. (ICLR 2018).
- 🧠 #6 ampliado (hubness como primo de las dimensiones dominantes). Referencias añadidas. Lección 66 → 69 celdas, 104 s.
