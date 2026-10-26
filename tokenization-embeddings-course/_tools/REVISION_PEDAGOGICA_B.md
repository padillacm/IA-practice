# Revisión pedagógica · Bloque B (módulos 09–20)

Revisor pedagógico B (oct-2026). Mismos criterios que la revisión A (`REVISION_PEDAGOGICA_A.md`): progresión y
prerrequisitos, secuencia intuición → ejemplo a mano → fórmula → código desde cero → librería → experimento,
analogías explícitas (compresión, IR/recsys, lingüística), alineamiento objetivos ↔ lección ↔ proyecto ↔
autoevaluación, andamiaje (🪜), repaso espaciado (🔁), 👀 tras gráficos y celdas Gemini, preguntas de
Cálculo/Diagnóstico/Transferencia, carga cognitiva (🧭) y terminología canónica. Todo en los builders
(`_tools/builders/`), notebooks regenerados. Orden de trabajo 18 → 19 → 20 → 09–17 para no coincidir con la
revisión de ejecutabilidad B, que avanzaba en orden ascendente.

Auditoría automática (script de conteo de celdas, gráficos, Gemini, 👀 ausentes, 🔁/🧭/🪜 y preguntas etiquetadas)
como punto de partida en cada módulo.

## Transversal (18–20)
- **Terminología:** «costo/costos» → **coste/costes** (forma canónica del bloque A) en lecciones, proyectos y READMEs
  de 18–20, incluidos títulos de gráficos, encabezados que la rúbrica del capstone exige («Costes y latencia») y la
  plantilla del informe, de forma coherente entre enunciado, comprobación y solución. Identificadores de código
  (`coste_api`, `DECISIONES['tokenizer_costo']`) sin tocar.

## 18 · Producción
- Bien: cada sección con una métrica y 👀 tras los 11 gráficos y las 4 celdas Gemini; analogía two-tower;
  autoevaluación con 6 preguntas etiquetadas; proyecto con 🪜 1/2 en todos los TODO y que solo pide lo enseñado
  (caché §4, adaptador §5, RRF del 13, p50/p99 del 14, bootstrap pareado del 15, filtro dentro de la búsqueda §7).
- **Reestructurado:** Mapa de madurez de la cabecera a justo antes de 🏭, con frase puente (nombraba BCT, interleaving,
  hedged requests… antes de enseñarlos).
- **Arreglado:** la caja 🧭 citaba secciones que no existían o eran otras (§6 migración, §8 vector DB, §11 A/B); ahora
  coincide con la numeración real y marca como núcleo lo que usa el proyecto. Referencias internas «§6»/«§9»
  corregidas a §5 (migración) y §8 (privacidad).
- **Ejemplos a mano añadidos:** punto de equilibrio API vs GPU (584 $/mes → $T^*=2.92\times10^{10}$ frente a una
  capacidad de $3.15\times10^{10}$; analogía coste fijo vs variable), PSI con 2 bins (0.42 → actuar; PSI = KL
  simetrizada, origen en *credit scoring*) y una impresión de team-draft interleaving (paralelo con el test pareado
  del 15).
- **Repaso espaciado:** el 🔁 solo repasaba 12–17. Añadidas R5 (M04 + M00, Cálculo: prima de tokens 1.3 en un corpus
  mitad ES → factura +15 %) y R6 (M01, Diagnóstico: «café» NFC vs NFD en la clave de caché).

## 19 · Playbook de élite
- Bien: no es una lista; las reglas son **código** (árboles `elige_*` con razones y umbral `N_FLAT_MAX` medido),
  las trampas T1–T4 se reproducen con números, los fallos F1–F4 se reproducen y el linter de PRs es ejecutable.
  👀 tras los 7 gráficos y las 3 Gemini. El proyecto ya seguía la escalera ejemplo → guiada (calentamiento:
  revisar la propuesta del becario con la rúbrica) → independiente (C1–C3), con 🪜 1/2 en todos los TODO.
- **Añadido 💡 Intuición** (faltaba): el playbook como checklist de piloto que se ejecuta, con los tres verbos
  decidir / medir / revisar mapeados a secciones, y la escalera de práctica explícita para el alumno.
- **Reestructurado:** Mapa de madurez de la cabecera a justo antes de 🏭, con frase puente.
- **Ejemplos a mano añadidos:** el árbol del índice aplicado a 10 M × 768 con 64 y 16 GB (33.3 GB → HNSW float32;
  10.2 GB → HNSW + int8), que coincide con la salida de `elige_indice`; y el optimismo esperado del *winner's curse*
  (máximo esperado de 20 normales ≈ 1.87σ → ≈ +0.03 de nDCG ficticio con σ = 0.015; analogía con el CTR de recsys).
- **🧭 corregida:** §4 (costes a escala) pasa a núcleo porque el bloque A de la rúbrica del proyecto usa sus fórmulas;
  §5 (galería de fallos) pasa a ampliación.
- **§7 Cultura** dejaba de ser lista suelta: añadido el cierre que remite cada práctica a dónde se ejecutó en el
  notebook o en el capstone.
- **Repaso espaciado:** añadidas R5 (M00, Diagnóstico: IC pareado que incluye el 0) y R6 (M01 + M02, Transferencia:
  NFC al indexar y queries sin normalizar → ítem «simetría» de la checklist).
- Autoevaluación: la pregunta 6 estaba marcada (Cálculo) sin cálculo; ahora (Diagnóstico).
- Terminología: «impuesto de idioma» y «prima de paridad» → **prima de tokens** (también en la lección 20).

## 20 · Capstone
- Bien: integración real con criterios de aceptación fijados **antes** de construir, cada componente decidido en dev
  con una regla escrita, test ciego usado una vez, informe generado desde las métricas; el proyecto replica el
  procedimiento con 🪜 1/2 en los 6 TODO y una rúbrica que comprueba también las secciones del informe.
- **Añadida la tabla «🧩 Qué integra este capstone (y qué queda como reto)»**: módulo → qué aporta → sección. Deja
  explícito qué módulos no entran en la v1.0 y por qué (06–08 por madurez; 07/09: el embedder trae su tokenizer) y
  sirve de índice de repaso. Para cerrar huecos de integración se añadieron dos retos al proyecto: **robustez**
  (fuzzer del 05 + normalización del 01 sobre las queries de test, con criterio de estabilidad del top-10) y
  **privacidad** (17–18: riesgo de inversión y medidas en *Limitaciones*). El reto 1 ya permitía usar el embedder
  propio del 11.
- **Ejemplo a mano añadido** tras `ACEPTACION`: qué criterios restringen el diseño (coste 80 $, ≈ 92 $ con prima de
  tokens 1.3 → no restringe; RAM ≤ 16 GB → 1 344 B/vector → $d \le 1\,344$ en int8 y $\le 336$ en float32), que
  motiva la decisión dimensión + int8 de §3.
- **Reestructurado:** Mapa de madurez de antes de la Gemini de arquitectura a justo antes de 🏭.
- **🧭 corregida:** el servicio (§6) estaba en ampliación pero el TODO 4 del proyecto lo exige; ahora es núcleo
  (solo la simulación de carga queda como ampliación).
- **Repaso espaciado:** añadidas R5 (M00, Diagnóstico: por qué el listón es el BM25 del 00 y las métricas del 00) y
  R6 (M10 + M12, Cálculo: recortar dimensiones sin renormalizar da 0.36 en vez de coseno 0.6).

## 09 · Capa de embedding en LLMs
- Bien: ejemplo a mano (V = 5, d = 2: lookup = one-hot·E y gradiente solo en filas usadas) antes del código;
  analogías recsys explícitas (tabla de ítems, two-tower, cola larga en la autoevaluación); word2vec/PMI como caja
  histórica; Mapa de madurez ya al final (§8, antes de 🏭); 👀 tras los 8 gráficos y las 3 Gemini; 59 celdas
  (no requiere 🧭).
- **Ejemplo a mano añadido** en §6: las tres inicializaciones (`random`, `mean`, `subtoken`) con vectores de 2D para
  « serialización», con la analogía del *cold start* de ítems y por qué `subtoken` en la salida produce masa filtrada.
- **Repaso espaciado:** el 🔁 cubría 02, 05 y 07. Añadidas R4 (M04, Cálculo: 32k → 128k con d = 2048 → ≈ 197 M por
  matriz, ≈ 393 M desatadas) y R5 (M02, Transferencia: criterio voraz «frecuencia × tokens ahorrados» como un merge,
  que es el del TODO 3).
- **Andamiaje del proyecto:** TODO 2 (interpretación) sin pistas → 🪜 1 que remite al 👀 de §3 y a los dos corpus;
  TODO 3 y TODO 5 solo tenían 🪜 1 → añadidas 🪜 2 (Counter + ahorro; congelado + máscara + copia + assert, con el
  detalle del *closure* `m_=mask`), coherentes con la solución.

## 10 · Embeddings contextuales y de oraciones
- Bien: 🔁 con 09 y 00; analogía two-tower explícita; whitening derivado paso a paso con su comprobación; elegir en
  validación y reportar en test (también en el proyecto); Mapa de madurez ya al final; 👀 tras 6 gráficos y 4 Gemini.
- **Ejemplos a mano añadidos:** pooling CLS/media/máximo/último con $T = 4$ y una posición de padding (media con
  máscara $(1, 1.33)$ frente a $(3, 3.25)$ sin ella; analogía bolsa de palabras/TF), y whitening en 2D con
  $\Sigma = \mathrm{diag}(4, 0.25)$ → $W = \mathrm{diag}(0.5, 2)$, enlazado con la anisotropía del 09.
- **Repaso espaciado:** añadida R4 (03–04, Diagnóstico): con mean pooling, una palabra troceada en 4 piezas pesa 4
  veces más; la fertilidad también afecta a la geometría, no solo al coste.
- **Andamiaje del proyecto:** TODO 2/3 solo tenían 🪜 1 → 🪜 2 con la API (SVD de la covarianza, dict de medias);
  la recomendación escrita del TODO 5 no tenía guía → 🪜 1 con estructura de cuatro frases (incluido el riesgo de
  versión de μ/W en producción, puente con el 18).

## 11 · Aprendizaje contrastivo
- Bien: intuición «recuperar = clasificar entre todos los documentos»; derivación de la cota de Oord con sus límites
  (Poole et al.); laboratorio controlado de temperatura/colapso; desde cero → `sentence-transformers`; analogía de
  la softmax muestreada del two-tower (y corrección logQ en la autoevaluación); la nota de calibración del proyecto
  marca con claridad que el efecto de los duros es del corpus de respaldo e inestable. Mapa ya al final.
- **Ejemplo a mano añadido** antes del gradiente: una fila con cosenos (0.8, 0.5, 0.1) a τ = 1 (p = 0.45, pérdida
  0.80) y τ = 0.1 (p = 0.952, pérdida 0.049; el negativo duro recibe 50× más empuje que el fácil), enlazado con la
  cabeza del LM (09) y la softmax muestreada de recsys.
- **Repaso espaciado:** el 🔁 solo repasaba 09–10. Añadida R4 (M00, Diagnóstico): qrels incompletos → falsos
  negativos al minar con BM25 («no visto ≠ no relevante», como los no clics en recsys).
- **Andamiaje del proyecto:** TODO 2 y TODO 3 solo tenían 🪜 1 → añadidas 🪜 2 coherentes con la solución
  (filtro **relativo** TopK-PercPos explicado).

## 12 · Embedders modernos
- Bien: 🔁 con 04, 09, 10 y 11; pooling encoder/decoder desde cero; árbol de decisión; lectura crítica de MTEB;
  autoevaluación con 7 preguntas (6 etiquetadas); proyecto con rúbrica R1–R9 calibrada y 🪜 en los TODO difíciles.
- **Reestructurado:** Mapa de madurez de la cabecera (§0, antes de la intuición) a justo antes de 🏭, con frase puente.
- **Ejemplo a mano añadido** en §5: cuantización int8 de un valor (0.12 → 30 → 0.1196) y binaria de dos vectores de 4
  dimensiones (H = 2 → producto ±1 = 0), con la observación de que la binaria tira la magnitud (motivo del rescoring).
- **Repaso espaciado:** añadida R5 (M08 + M02, Cálculo): 24 576 bits (float32) vs 768 (binario) vs 13 (token VQ de
  8 192) como puntos de una curva tasa-distorsión; puente con PQ (14).
- **Proyecto:** el TODO 7 (frontera de Pareto + recomendación + gráfico) no tenía pistas → 🪜 1 (skyline de dos
  objetivos, analogía tasa-distorsión del 08) y 🪜 2 (API). Añadidas 👀 tras el gráfico de la frontera (plantilla y
  solución), formuladas sin presuponer el resultado con datos reales.

## 13 · Dense, sparse y late interaction
- Bien: 🔁 con 00 (BM25), 04/05, 10/12 y 11/12; BM25 desde cero verificado contra `rank_bm25`; mini golden set de
  paráfrasis para diagnosticar dónde gana cada retriever; ejemplo RRF a mano (autoevaluación) que la rúbrica R3
  comprueba; tuning de α sin fuga (CV); 👀 tras 10 gráficos y 5 Gemini; proyecto con 🪜 1/2 en todos los pasos.
- **Reestructurado:** Mapa de madurez de la cabecera a justo antes de 🏭.
- **🧭 corregida:** el núcleo decía «secciones 1–4» e incluía SPLADE (3), que también figuraba en ampliación; ahora
  núcleo = 1, 2, 4, 7, 8 (lo que usa el proyecto) y ampliación = 3, 5–6, 9, 10.
- **Ejemplo a mano añadido** en §4: MaxSim con una matriz 2×3 (0.9 + 0.8 = 1.7; 1.3 si falta el token), con la
  analogía «cada término exige su evidencia» de BM25 y el contraste con el bi-encoder.
- **Repaso espaciado:** añadida R5 (M00, Diagnóstico: +0.02 en 58 queries sin IC pareado, y α elegido sobre las
  mismas queries), como recomendaba la revisión pedagógica A para retomar nDCG/IC antes del 15.

## 14 · Indexación y ANN
- Bien: «cuándo NO usar ANN» en la intuición; protocolo de medición (batch = 1, p50/p99, neighbor recall) antes de
  los índices; IVF, PQ/OPQ y un HNSW mínimo desde cero → FAISS con barrido y SLA; puente explícito con
  `recsys-course/08`; 🧭 coherente con el proyecto; 👀 tras 12 gráficos y 4 Gemini.
- **Reestructurado:** Mapa de madurez de la cabecera a justo antes de 🏭.
- **Ejemplo a mano añadido** en §4: PQ con $d = 4$, $m = 2$, $K = 2$ (código `[0, 0]`, tablas ADC, score aproximado 1
  frente a 0.9 exacto), enlazado con la VQ del 08 y la idea de diccionario de compresión; 3 072 B → 96 B a escala.
- **Repaso espaciado:** añadidas R5 (M08, Cálculo: codebook de 256 = 1 byte; 96 trozos = 96 B → PQ) y R6 (M00,
  Transferencia: IVF como índice invertido cuyo «término» es un centroide).
- **Proyecto:** TODO 5 tenía 🪜 2 sin 🪜 1 → añadida; TODO 6–7 (no dominados con 3 objetivos, elección con SLA) sin
  pistas → 🪜 1/2 coherentes con la solución. 👀 añadidas tras las curvas recall/latencia/memoria (plantilla y
  solución), incluida la lectura «si Flat cumple el SLA, no hace falta ANN».
