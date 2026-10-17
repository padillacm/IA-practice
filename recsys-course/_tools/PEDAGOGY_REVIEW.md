# Revisión pedagógica del curso (00–19)

Foco: **cómo se enseña** (la corrección técnica la auditaron otros revisores). Alumno: domina ML, MLOps y agentes
LLM; no sabe nada de recsys. Marco: carga cognitiva, andamiaje, ejemplo resuelto → práctica guiada → práctica
independiente, práctica de recuperación, repaso espaciado, alineamiento constructivo y Bloom.

Leyenda: ✅ arreglado en el builder · 📌 recomendación pendiente (cambio grande, no aplicado).

---

## 0. Visión global

### Fortalezas
- **Plantilla muy consistente** en las 20 lecciones (cabecera → objetivos con verbos de Bloom → intuición → teoría →
  desde cero → librería → experimentos → 🏭 → 🧠 → ⚠️ → autoevaluación → referencias). Reduce la carga cognitiva
  extrínseca: el alumno sabe siempre dónde está.
- **Ejemplos en papel** (5×6 películas) al principio de casi todos los módulos clásicos (00, 03, 04, 05, 06, 13): buen
  *worked example* antes de la formalización.
- **CineMatch como hilo conductor** real: el pipeline de datos del 01 y el evaluador del 02 se reutilizan; el 18 integra
  y el 19 depura. Es aprendizaje basado en proyectos auténtico.
- Los objetivos usan verbos medibles (implementar, derivar, medir, comparar, diagnosticar) y suben de nivel de Bloom con
  el curso (00–02: definir/explicar/implementar → 13–19: diseñar/diagnosticar/decidir).
- Las secciones 🧠 están, en general, **argumentadas** (por qué importa + fuente), no son listas de nombres.

### Problemas transversales detectados (y qué se hizo)
| # | Problema | Impacto | Acción |
|---|---|---|---|
| G1 | **Ningún módulo retoma explícitamente conceptos anteriores** (0 cajas de repaso en 20 lecciones). El repaso espaciado depende de que el alumno lo haga solo. | Alto: el curso dura ~150 h; sin recuperación espaciada, lo del bloque I se olvida antes del capstone. | ✅ Caja **«🔁 Conexión con módulos anteriores»** tras los objetivos de cada lección 01–19, con 2–3 preguntas de recuperación (respuesta oculta) sobre los conceptos previos que el módulo necesita. |
| G2 | **Proyectos sin pistas graduadas**: los TODOs traen una pista inline o ninguna; del enunciado se salta a la solución completa (no hay escalón intermedio). | Alto: el alumno o se atasca o mira el SPOILER entero (pierde la práctica guiada). | ✅ Bloques `🪜 Pista 1 / Pista 2` (plegados) en los TODOs más difíciles de cada proyecto: la 1 orienta (qué estructura/idea), la 2 casi da la API. |
| G3 | **Pocos gráficos con lectura explícita** («qué debes observar»): de ~250 figuras, ~60 tienen interpretación justo después. | Medio: un novato no sabe qué mirar en una curva recall–latencia o en un frente de Pareto. | ✅ Cajas **«👀 Qué debes observar»** tras los gráficos clave sin interpretar de cada lección. |
| G4 | **Autoevaluaciones mayoritariamente de recuerdo** («¿qué es X?», «¿por qué Y?»), pocas de cálculo, transferencia o diagnóstico. | Medio: no ejercita los niveles altos de Bloom que piden los objetivos. | ✅ 1–2 preguntas marcadas **(Razonamiento)/(Transferencia)/(Diagnóstico)** por lección: cálculo con números, escenario de producción o depuración. |
| G5 | **Faltan analogías con lo que el alumno ya domina** (RAG, cross-encoders, MLOps, agentes) en módulos donde son evidentes. Solo 08, 12 y 16 las hacían explícitas. | Medio: se pierde el anclaje más barato para este alumno. | ✅ Analogías añadidas donde aportan (00: embudo ≈ RAG bi-encoder + reranker; resto por módulo, ver abajo). |
| G6 | No existía guía de estudio global: ruta, tiempos, qué repasar antes de cada bloque, mapa de dependencias, glosario ES/EN. | Medio. | ✅ `recsys-course/GUIA_DE_ESTUDIO.md` (enlazada desde el README y desde la lección 00). |
| G7 | Niveles del README y de las cabeceras no coinciden en algunos módulos (03, 05, 13, 14). | Bajo. | ✅ README alineado con las cabeceras. |
| G8 | **Módulos sobrecargados**: 12 (7–9 h, 86 celdas, 11 secciones), 19 (7–9 h, 80 celdas) y en menor medida 06 (8 arquitecturas en una lección) y 15 (13 temas). | Medio-alto: carga intrínseca muy alta en una sola sesión. | ✅ Rutas «núcleo vs opcional» señaladas en la lección. 📌 Partir 12 en 12a (LLM como encoder/ranker/LoRA) y 12b (agentes, simulación, evaluación); partir 19 en dos sesiones (§0–4 datos/tablas/tiempo real; §5–8 medición, casebook, rendimiento, cultura). |

### Progresión y prerrequisitos (curva 🟢→🔴)
- La curva es coherente: I (🟢) → II (🟢🟡) → III (🟡🟠) → IV (🟠🔴) → V (🟠🔴) → VI (🔴). El salto más brusco es
  **05 → 06** (de un modelo con dos matrices a ocho arquitecturas CTR + calibración + hashing en una lección); se
  amortigua señalando el núcleo (LR → FM → DCN-v2 → calibración) y dejando FFM/DeepFM/DIN como ampliación.
- No se encontraron conceptos usados **antes** de enseñarse que bloqueen la comprensión; sí varias **dependencias
  implícitas** (IPS aparece en 07 y se formaliza de verdad en 14; *softmax muestreada* en 08 se reutiliza en 09 y 11;
  DCG/NDCG del 02 en 07). Las cajas 🔁 las hacen explícitas.
- Bloque V puede estudiarse antes que el IV (13–15 dependen de 01–08, no de 09–12); se indica en la guía de estudio.

---

## Hallazgos por módulo

### 00 · Introducción y panorama
- Secuencia excelente (sobreabundancia → matriz de juguete → formalización → ejemplo a mano de contenido y CF → embudo
  con experimento de coste → ciclo de vida → datos reales → primer recomendador y su crítica).
- ✅ «18 módulos siguientes» → 19, y enlace a la guía de estudio.
- ✅ «👀 Qué observar» en la matriz de juguete (conecta con las dos familias) y en el embudo de señales (conecta con la
  elección del positivo y la multi-tarea del 07).
- ✅ Analogía explícita **embudo ↔ RAG** (bi-encoder + base vectorial = retrieval; cross-encoder = ranking; filtros =
  re-ranking).
- ✅ Autoevaluación: +2 preguntas (cálculo del presupuesto de candidatos; transferencia sobre split aleatorio).
- ✅ Proyecto: pistas graduadas en TODO 2 (Lorenz, semanas), TODO 4 (home sin repetidos) y TODO 5 (split + HitRate).

### 01 · Datos de interacción y baselines
- Muy buena secuencia «log → matriz → sesgos simulados → señales → splits → baselines»; las tres simulaciones de
  sesgos son ejemplos resueltos excelentes. El experimento «el mismo baseline, cuatro verdades» es memorable.
- ✅ Caja 🔁 (exposición ≠ negativo, elección del positivo, «respetar el tiempo» del 00).
- ✅ «👀 Qué observar» tras la long tail (ley de potencias; anticipa el Gini de recomendaciones del 02), MNAR (por qué
  el RMSE no lo detecta) y sesgo de posición (anticipa IPS/PAL del 07 y propensiones del 14). Antes, las dos
  simulaciones de sesgo pasaban a la siguiente sin interpretación.
- ✅ Analogía con *walk-forward validation* / `TimeSeriesSplit` y *target leakage* de ML tabular.
- ✅ Autoevaluación: +1 cálculo (memoria denso vs CSR a escala CineMatch) y +1 diagnóstico (feature con leakage que
  sube offline y no online).
- ⚠️→✅ Prerrequisito: el proyecto pedía implementar NDCG antes del módulo 02. Se añade una nota con la intuición de la
  fórmula y pistas; la derivación queda en el 02.
- ✅ Proyecto: pistas graduadas en TODO 2 (k-core iterativo, cortes por cuantiles), TODO 3 (validaciones) y TODO 5
  (métricas y ventana de popularidad).

### 02 · Evaluación offline rigurosa
- Módulo de muy alto valor y bien argumentado (RMSE vs top-K con experimento, sampled metrics con el contraejemplo
  «francotirador vs bueno en todo», checklist que se reutiliza en todo el curso).
- ⚠️→✅ **Faltaba el ejemplo resuelto a mano** entre la tabla de fórmulas y el código: el alumno pasaba de seis
  fórmulas a la implementación. Se añade una tabla con dos listas con los mismos ítems en distinto orden: muestra en
  un vistazo qué métricas son sensibles a la posición (MRR/AP/NDCG) y cuáles no (P/R/HR).
- ✅ Analogía con la evaluación de RAG/buscadores (Recall@K del retriever, MRR/NDCG@10 de BEIR/MTEB).
- ✅ Caja 🔁 (split temporal y LOO del 01, popularidad del proyecto 00, «cuenta tus usuarios»).
- ✅ «👀 Qué observar» en el gráfico de IC: solapamiento de IC vs test pareado, y la ley 1/√n que reaparece en el
  tamaño muestral del A/B (módulo 15) → puente explícito.
- ✅ Autoevaluación: +1 diagnóstico (HR@10 de paper 0,70 vs 0,09 propio → protocolo) y +1 cálculo (usuarios para un IC
  3× más estrecho).
- ✅ Proyecto: pistas graduadas en TODO 3 (ranx), TODO 5–6 (AUC por rangos, test pareado bootstrap) y miscalibración KL
  (que el proyecto pide y la lección solo menciona: se aclara que la intuición llega en el 13).

### 03 · Basado en contenido
- Excelente honestidad pedagógica: «el contenido pierde contra popularidad en warm y gana en cold start» se demuestra
  con datos y se explica. El ejemplo en papel (6 sinopsis) precede bien a TF-IDF/BM25.
- ✅ Caja 🔁 (perfil centrado del 00, ILD/cobertura del 02, validación dentro de train).
- ✅ «👀 Qué observar» en el histograma de anisotropía (separación vs valor absoluto del coseno) y en el UMAP (qué
  géneros se agrupan y por qué; no interpretar distancias globales). Antes ambos gráficos quedaban sin lectura.
- ✅ Autoevaluación: +1 diagnóstico (cambio de encoder que degrada en silencio) y +1 transferencia (dónde va el
  contenido en el embudo con 200 estrenos/semana).
- ✅ Proyecto: el Paso 5 (cold start) era un `# TODO` vacío que obligaba a reconstruir el protocolo de memoria → dos
  pistas graduadas con la estructura y la puntuación; pista para la penalización por año del Paso 4.
- El cambio de protocolo del Bloque II (80/20, train con todos los ratings) frente a `prepare_cinematch` está bien
  avisado en la celda de utilidades de lección y proyecto (03–05): buen ejemplo de la regla «compara solo dentro del
  mismo protocolo» del 02.

### 04 · Vecindad y modelos lineales
- Buen arco «intuición (co-consumo) → ejemplo 5×6 → similitudes → shrinkage → EASE derivado → implementación →
  librerías → comparativa con coverage». Las lecturas de los barridos (shrinkage/α) son ejemplares.
- ⚠️→✅ La derivación de EASE (Lagrangiano) llegaba sin intuición previa para un alumno de ML. Se añade el puente:
  **EASE = |I| regresiones ridge**, una por película; `diag(B)=0` = prohibir *target leakage*; solución ridge sin
  restricción como referencia.
- ✅ Caja 🔁 (shrinkage como respuesta a la fragilidad del ejemplo del 00, NDCG+coverage del 02, contenido vs
  co-consumo del 03).
- ✅ «👀 Qué observar» en el barrido de β de RP3β (primer frente de Pareto, puente al 13) y en el de λ de EASE.
- ✅ Autoevaluación: +1 diagnóstico (coverage 2 % → α/shrinkage/β) y +1 transferencia (sesión en tiempo real).
- ✅ Proyecto: pistas graduadas para `item_knn`/`ease` (de la fórmula a COO) y para el bootstrap pareado por usuario.

### 05 · Factorización matricial
- Narrativa muy buena (ejes latentes → juguete 5×6 → por qué no SVD → biased MF → SGD → SVD++ → iALS → BPR → iALS
  revisitado) y la analogía «MF = two-tower más simple» está bien colocada.
- ✅ Caja 🔁 (modelo de sesgos del 02, ridge de EASE del 04 → «ALS = alternar ridges», confianza del 01).
- ✅ «👀 Qué observar» en el barrido λ/k (curva sesgo–varianza con ejes de recsys; regla «λ y k se tunean juntos») y
  en la curva de BPR (la pérdida baja y el NDCG se estanca → early stopping por NDCG). Ambas figuras no tenían lectura.
- ✅ Autoevaluación: +1 cálculo (parámetros MF vs EASE a escala CineMatch → cuándo elegir cada uno) y +1 diagnóstico
  (BPR que recomienda lo mismo a todos).
- ✅ Proyecto: los cuatro pasos eran `# TODO` sin andamiaje. Pistas graduadas para BPR (modelo y bucle), Optuna
  (validación sin tocar test) y fold-in (ecuación de ALS con Q fijo y la convención de confianza de `implicit`).

### 06 · CTR y ranking
- Teoría excelente (derivación del truco O(kn), corrección del *negative downsampling* por Bayes, DCN-v2 con
  interpretación de bloques) y ejemplo de 5 impresiones que motiva los cruces.
- ⚠️ **Sobrecarga (G8)**: ocho arquitecturas + hashing + calibración + DIN en 5–6 h; es el mayor salto de carga del
  curso (05 → 06). ✅ Caja **«🧭 Cómo recorrer esta lección»** con núcleo (LR → FM → DCN-v2 → LightGBM → calibración)
  vs ampliación (FFM, W&D/DeepFM, GBDT+LR, interacciones, hashing, DIN), y un hilo conductor explícito («cada modelo es
  una forma de aprender cruces»). 📌 Si se quiere aligerar más: mover FFM y GBDT+LR a «📚 Para profundizar».
- ✅ Caja 🔁 (etapa de ranking del 00, FM ⊃ MF del 05, leakage del 01 → PIT del proyecto y del 16).
- ✅ Analogía DIN = *cross-attention* de una sola query.
- ✅ «👀 Qué observar» en curvas/ROC/barras (one-epoch, diferencias en la 3.ª-4.ª cifra, LightGBM como listón) y en
  los mapas de interacción FM/DCN-v2 (pares plantados; dispersión → bajo rango).
- ✅ Autoevaluación: +1 razonamiento (¿desplegar DCN-v2 por 0,0008?) y +1 transferencia (downsampling sin corregir rompe
  la fusión de objetivos del 07).
- ✅ Proyecto: pistas graduadas para los contadores PIT, DCN-v2 (estructura parallel, logits) y calibración isotónica
  (ajustar en val).

### 07 · Learning to Rank y multi-tarea
- Teoría clara y bien ordenada (pointwise → RankNet → LambdaRank → listwise → sesgo de posición → MTL) con dos
  experimentos controlados excelentes (seesaw sintético y Pareto real).
- ⚠️→✅ **Faltaba el ejemplo resuelto de LambdaRank**: la fórmula de |ΔNDCG| aparecía sin un caso numérico. Se añade
  una consulta de 3 documentos con la tabla de |ΔNDCG| por par y la comprobación (0,64 + 0,34 = 0,98).
- ✅ Analogía **MMoE ↔ MoE de los LLM** (Mixtral/Switch): puerta por tarea, mezcla densa, objetivo distinto.
- ✅ Caja 🔁 (descuentos del DCG del 02 → |ΔNDCG|; simulación de posición del 01 → IPS/PAL; calibración del 06 →
  fusión).
- ✅ «👀 Qué observar» en el seesaw sintético (lectura del eje invertido, *negative transfer*), el frente de Pareto
  (comparar curvas, no puntos; ruido de una semilla) y el heatmap de fusión (la esquina «solo clic»; proxy definida
  por nosotros).
- ✅ Autoevaluación: +1 cálculo (|ΔNDCG| a mano) y +1 diagnóstico (sesgo de posición colado por *features*).
- ✅ Proyecto: pistas graduadas para `MMoE.forward`/`CGCLayer.forward` (formas de tensores), y para LambdaMART
  (`group` contiguo, `label_gain`, `business_ndcg`).

### 08 · Deep retrieval y ANN
- Muy buena conexión con lo previo (MF → two-tower, RAG bi-encoder/cross-encoder ya presente) y una tabla de índices
  FAISS con «cuándo» que es oro para la práctica.
- ⚠️→✅ La corrección logQ (concepto central y contraintuitivo) solo tenía fórmula y gráfico. Se añade un **ejemplo
  numérico** (Titanic 1 % vs película de culto 0,01 % en un batch de 1.024: 10 vs 0,1 apariciones como negativo).
- ✅ Caja 🔁 con 4 preguntas (MF del 05, falsos negativos del 01, Recall@K del 02, InfoNCE del 03).
- ✅ «👀 Qué observar» tras el entrenamiento de variantes (no comparar pérdidas con distinto nº de negativos), el
  análisis cabeza/torso/cola, la temperatura y el t-SNE (comparado con el UMAP de sinopsis del 03: trama vs público).
- ✅ Autoevaluación: +1 diagnóstico (logQ aplicado por error en serving) y +1 transferencia (mapear RAG → CineMatch y
  sus diferencias).
- ✅ Proyecto: el Paso 3 (bucle + MNS + evaluación por grupos) era un `# TODO` de una línea → dos pistas graduadas;
  pista para FAISS (recall vs exacto con consultas reales, p50/p99 con un hilo).

### 09 · Recomendación secuencial
- Módulo ejemplar en analogías (SASRec = GPT, BERT4Rec = MLM) y en teoría (derivación de la sobreconfianza de la
  BCE y de gBCE paso a paso), con un «truco que no viene en los papers» bien justificado.
- ⚠️→✅ **Inconsistencia de protocolo**: el 01 enseña que LOO tiene *leakage* y aquí se usa LOO sin aviso hasta el
  secreto 4 (al final). Se hace explícito en la caja 🔁 (pregunta 1) para que el alumno lo razone **antes** de los
  experimentos.
- ✅ Caja 🔁 con 4 preguntas (LOO del 01, logQ del 08, DIN del 06, métricas muestreadas del 02).
- ✅ «👀 Qué observar» en la figura de sobreconfianza (saturación en la cabeza = problema de ranking), en la
  comparación final (la pérdida pesa más que la arquitectura; no comparar pérdidas), en el barrido de negativos
  (contrastar con la predicción hecha *antes*) y en el t-SNE (puente con item2vec del 10).
- ✅ Autoevaluación: +1 diagnóstico (colapso a puntuación constante → offset b₀) y +1 transferencia (estado del
  usuario nearline para «Porque acabas de ver»).
- ✅ Proyecto: pistas para baselines (Markov disperso), SASRec (bloques pre-LN y máscara) y pérdidas (CE con índice
  −1, negativos compartidos y el offset b₀, sin el cual el alumno se atascaría como avisa la lección).

### 10 · Grafos
- Buen arranque (la matriz ya es un grafo, con $\hat A^3$ calculado sobre el juguete) y analogías útiles (agregados de
  vecinos en fraude; SGNS = factorización PMI; LightGCN K=0 = MF-BPR como experimento controlado).
- ✅ Caja 🔁 (RP3β del 04 como grafo, BPR/MF del 05, transductivo vs inductivo con la torre de ítem del 08).
- ✅ «👀 Qué observar» en los paseos node2vec (una sola dimensión efectiva en bipartito), capas/over-smoothing (por qué
  K = 2–3), rendimiento por cuartil de actividad (diferencia relativa; resultado nulo legítimo) y vecindario PinSage
  (puente con item-kNN). Cuatro figuras que antes no tenían lectura.
- ✅ Autoevaluación: +1 razonamiento (expandir LightGCN K=1 → híbrido MF + user-kNN + item-kNN) y +1 transferencia
  (nodos actor/director para estrenos: transductivo vs inductivo).
- ✅ Proyecto: pistas para `edge_index` no dirigido y para el bucle BPR con PyG (`recommendation_loss`, `node_id`).

### 11 · Recomendadores generativos
- Contenido de élite **bien dosificado**: analogía del código postal, teoría completa de RQ-VAE/TIGER/HSTU, y sobre todo
  comparaciones honestas (TIGER vs SASRec con CE completa; scaling laws con su «letra pequeña»). Es el mejor ejemplo
  del curso de «por qué importa» frente a «lista de nombres».
- ⚠️→✅ La cuantización residual se presentaba solo en fórmulas. Se añade un **ejemplo resuelto en 2D** (3 ítems, 2
  niveles × 2 códigos) que muestra por qué ítems parecidos comparten prefijo.
- ✅ Caja 🔁 con 4 preguntas (full softmax del 09, colisiones de hashing del 06 vs colisiones semánticas, cold start
  del 03, beam search de LLMs).
- ✅ «👀 Qué observar» en el entrenamiento del RQ-VAE (uso de códigos = diagnóstico de *collapse*) y en la pureza
  (comparar con aleatorio; elegir tokenizador por colisiones/uso/pureza, no por pérdida).
- ✅ Autoevaluación: +1 cálculo (tamaño del espacio de SIDs y del vocabulario vs softmax) y +1 diagnóstico (TIGER débil
  con 40 % de uso del nivel 1).
- ✅ Proyecto: pistas para `quantize` (enlazada al ejemplo 2D), trie/desambiguación y beam search restringido (dos
  niveles).

### 12 · LLMs y agentes
- Muy bien adaptado al alumno («ya conoces LangGraph: aquí lo que cambia al recomendar»), con la regla de oro de costes,
  el patrón «LLM como controlador, recsys como herramientas» y defensas contra alucinación muy concretas.
- ⚠️ **Sobrecarga (G8)**: 86 celdas, 11 secciones, 7–9 h. ✅ Caja **«🧭 Cómo recorrer esta lección»** con dos sesiones
  (A: el LLM dentro del embudo; B: conversación y evaluación) y §4 LoRA marcada como opcional/GPU.
  📌 Recomendación: partir el módulo en **12a** (§1–5, 11) y **12b** (§6–10) con su propia autoevaluación; el proyecto
  ya se apoya sobre todo en 12b.
- ✅ Caja 🔁 (contenido warm vs cold del 03, techo Recall@K del 00/08, sesgo de posición del 07 vs del LLM, protocolo
  1+N del 02).
- ✅ «👀 Qué observar» en sesgo de posición + bootstrapping (aviso del backend mock), cold start (suelo/techo; hablar el
  idioma del CF), auditoría de explicaciones (tres fallos distintos → guardrail) y fidelidad del simulador (condición
  previa para creer la evaluación en bucle).
- ✅ Autoevaluación: +1 diagnóstico (exclusión perdida en el agente: reducer, relax, Store) y +1 transferencia
  («pon un LLM en la home»: dos usos rentables y uno a rechazar).
- ✅ Proyecto: pistas para el parser/Borda, el cableado del grafo (aristas condicionales y ciclo relax) y los
  guardrails por construcción.

### 13 · Más allá de la precisión
- Teoría excelente y muy completa (MMR, DPP con intuición geométrica, Steck, feedback loop con simulación, fairness de
  Singh & Joachims, Pareto, página de Netflix, reglas), con analogías potentes (cartera de inversión).
- ⚠️→✅ **18 gráficos con solo 2 lecturas**: casi todas las secciones encadenaban código → gráfico → siguiente sección.
  Se añaden siete cajas «👀 Qué observar» (DPP: área/ángulo, coste y fronteras; calibración por usuario y su
  distribución; novedad y el sesgo del NDCG offline hacia lo popular; fairness exposición vs mérito y por actividad;
  Pareto y ε-restricción como lenguaje de negocio; página deduplicada; heatmap de lanzamiento).
- ✅ Caja 🔁 con 4 preguntas (ILD/cobertura del 02 lista vs catálogo, feedback loop del 01, Pareto del 04/07, etapa de
  re-ranking del 00). Es el módulo que más reutiliza conceptos previos: el repaso aquí es especialmente rentable.
- ✅ Proyecto: pistas para la KL vectorizada del re-ranker greedy y para el orden filtros → deduplicación → cuotas.
- (La autoevaluación ya tenía preguntas de razonamiento de calidad; no se amplía.)

### 14 · Bandits, RL y OPE
- Uno de los módulos mejor construidos pedagógicamente: muchas lecturas («Lectura.», «Lectura honesta.»), estudio
  Monte Carlo de sesgo/varianza en vez de una sola estimación, caso Netflix bien explicado y una autoevaluación con
  derivaciones (Hoeffding → UCB) y transferencia.
- ✅ Caja 🔁 (IPS del 07 → propensiones; huecos de exploración del 13 → soporte común; «offline premia imitar» del 02;
  media bayesiana del proyecto 00 → prior Beta de Thompson).
- ✅ «👀 Qué observar» en cuatro figuras sin lectura: α de LinUCB, MSE vs n (pendiente −1 vs sesgo de DM), SlateQ vs
  miope y varianza de trayectoria vs horizonte (por qué la industria usa horizontes cortos).
- ✅ Autoevaluación: +1 cálculo (peso IPS 16× de una acción rara) y +1 diagnóstico (IPS +40 % con ESS 3 % vs DR +4 %).
- ✅ Proyecto: pistas para los cinco estimadores (fórmulas vectorizadas), LinUCB/TS con Sherman–Morrison y
  cross-fitting de q̂.

### 15 · Experimentación online
- Rigor estadístico alto y muy orientado a recsys (unidad de aleatorización, método delta, interleaving replicando el
  razonamiento de Netflix, mSPRT, interferencia con simulación de marketplace, surrogate index). Buenas lecturas en
  §2, §10 y §11 y prints interpretativos en novelty/HTE.
- ⚠️ **Sobrecarga (G8)**: 13 temas. ✅ Caja «🧭 Cómo recorrer esta lección» (núcleo §1–9 vs ampliación §10–13, con
  aviso de que el 19 da la ampliación por sabida).
- ✅ Caja 🔁 (test pareado del 02 → interleaving; ley 1/√n del 02 → 1/δ²; OPE del 14 vs A/B; guardrail para la
  diversidad del 13).
- ✅ «👀 Qué observar» en el A/A con método delta (p-valores uniformes), MDE vs días (semanas completas; qué hacer si no
  llega), CUPED vs ρ² (analogía ANCOVA/CUPAC con ML) y diff-in-diff (tendencias paralelas).
- ✅ Autoevaluación: +1 diagnóstico (SRM con cálculo del χ²) y +1 transferencia (plan interleaving → A/B con poco
  tráfico).
- ✅ Proyecto: pistas para el power analysis (fórmula y `NormalIndPower`) y Team Draft.

### 16 · Producción y serving
- Excelente puente desde MLOps («offline = Airflow, online = endpoint, nearline = la pieza que casi nadie tiene») y el
  «bug más caro de la industria en 20 líneas» (leakage del join ingenuo) es un ejemplo resuelto memorable.
- ✅ Caja 🔁 (capas del 00, contadores PIT del proyecto 06 → feature store, K' > K del 08, one-epoch del 06 → reentreno).
- ✅ «👀 Qué observar» en *tail at scale* (F(t)ⁿ; SLO en p99), caché TTL/invalidación (frescura como decisión de
  producto), paridad/skew (qué feature; no lo detecta un monitor de drift) y torre de contenido para estrenos (puente
  con el 12).
- ✅ Autoevaluación: +1 diagnóstico (skew vs drift con AUC 0,81 → 0,74) y +1 cálculo (presupuesto de latencia →
  nº máximo de candidatos).
- ✅ Proyecto: pistas para el servicio (artefactos al arrancar, flujo de caché, log de features antes del ranker) y
  para `load_test`/`parity_check`.

### 17 · MLOps: monitoreo y reentreno
- Bien enfocado para un alumno que ya sabe MLOps: el experimento central (cuánto se degrada un modelo estático con 20
  años de MovieLens) es auténtico y la sección «Qué deberías ver» es un buen ejemplo de lectura guiada.
- ✅ Caja 🔁 que explicita «lo que este módulo añade sobre tu MLOps» (feedback loop + propensiones del 01/13/14, skew
  vs drift del 16, fold-in del 05, SRM del 15).
- ✅ «👀 Qué observar» en seis figuras sin lectura: EDA temporal (tres drifts antes de entrenar), señales sin
  etiquetas y OOV como trigger específico de recsys, mapa de Evidently «todo rojo» (tests con n grande), embedding
  drift (AUC de dominio vs PCA), alertas con estacionalidad y canary por escalones.
- ✅ Autoevaluación: +1 diagnóstico (challenger +4 % offline, −3 % online tras reentreno automático) y +1
  transferencia (traducir el flow a tu orquestador; qué es específico de recsys).
- ✅ Proyecto: pistas para el esquema Pandera (check a nivel de DataFrame) y para el flow (tags de línea base en
  MLflow, aliases).
- El *feedback loop* aparece en 01, 13, 14 y 17: es **espiral deliberada** (cada vez con una lente distinta: datos,
  re-ranking, exploración, operación); las cajas 🔁 ahora lo hacen explícito.

### 18 · Capstone
- Buen cierre: *walking skeleton* ejecutable que mapea cada etapa a su módulo, marco de 10 pasos para *system design*
  con *back-of-the-envelope*, mapa de lectura y ruta de carrera.
- ⚠️ El compendio de 38 secretos es una **lista** larga (contenido de élite con riesgo de lectura pasiva). ✅ Se
  convierte en **ejercicio de recuperación**: instrucción de «tapar y explicar en 1 minuto» + tabla secreto → módulo
  donde se practicó (la tabla también es un índice de repaso para entrevistas).
- ✅ Autoevaluación: +1 pregunta de **integración** (una petición de punta a punta: métrica y módulo por etapa).
- ✅ Proyecto: «🧭 Plan de sprint y mapa de reutilización» (qué proyecto anterior reutilizar en cada etapa, orden en
  ~2 semanas, regla del walking skeleton). Es el andamiaje adecuado para práctica independiente: pistas por
  referencia en vez de huecos rellenables. Se señala la referencia adelantada al design doc del 19 como lectura
  independiente.
- 📌 Considerar que la rúbrica del capstone pida también 3–5 respuestas cortas del marco de entrevista sobre el propio
  sistema (convertir el §4 en evaluación).

### 19 · Masterclass élite
- El módulo que mejor convierte «secretos de élite» en **práctica**: cada idea del compendio del 18 se implementa con
  una simulación de verdad conocida, con lecturas («Cómo leerlo», «Lecturas») y un *casebook* con árbol de triaje.
  La autoevaluación ya es de nivel alto (cálculos de capacidad, verosimilitud de Chapelle, Berkson).
- ⚠️ **Sobrecarga (G8)**: 80 celdas, 7–9 h. ✅ Caja «🧭 Cómo recorrer esta lección» (sesión A §0–4 datos/modelos a
  escala; sesión B §5–8 medir/depurar/operar; el casebook como prioridad para entrevistas). 📌 Recomendación: partir en
  dos notebooks si se rehace.
- ✅ Caja 🔁 en forma de **tabla «antes de… → pregunta → módulo»** (06, 14, 15, 16, 17), coherente con que el 19 da
  muchas piezas por sabidas.
- ✅ «👀 Qué observar» en memoria de tablas + estado del optimizador (Adagrad por filas), *one-epoch* explicado por
  tablas dispersas (puente con el 06), encuestas con IPS (puente con el 14), *golden queries* y novelty por antigüedad
  (puente con el 15). Las figuras de §7 ya se interpretaban en el texto previo.
- ✅ Proyecto (ya muy bien andamiado con una pista por bug): nota «si una herramienta no te sale, vuelve a la lección
  §…» y pista de `soft_labels` (estimar p y μ solo con clics maduros).

---

## Artefactos transversales
- ✅ `recsys-course/GUIA_DE_ESTUDIO.md`: cómo usar cada módulo (🔁, 👀, preguntas marcadas, 🪜 pistas), ruta y tiempos
  por bloque (≈ 190–220 h), órdenes alternativos sin romper prerrequisitos (V antes que IV; ruta exprés de ≈ 90 h
  para entrevistas), qué repasar antes de cada bloque, **mapa de dependencias en mermaid**, hilos transversales
  (feedback loop, leakage/PIT, negativos, recall como techo, offline ≠ online), **glosario ES/EN de ~70 términos** con
  módulo, y checklist de fin de curso.
- ✅ README: enlace a la guía (arriba y en «Cómo estudiar»), niveles alineados con las cabeceras (03, 05, 13, 14),
  presupuesto de Colab VI = 16–19, y explicación de las cajas 🔁/👀/🪜.
- ✅ Lección 00 enlaza la guía.

## Resumen cuantitativo de cambios
| Intervención | Cantidad |
|---|---|
| Cajas «🔁 Conexión con módulos anteriores» (01–17, 19; en el 18 el compendio se convierte en repaso) | 18 + 1 |
| Cajas/prints «👀 Qué debes observar» tras gráficos | ~68 |
| Pistas graduadas «🪜» en proyectos | ~60 |
| Preguntas nuevas de Cálculo / Razonamiento / Diagnóstico / Transferencia / Integración | ~35 |
| Ejemplos resueltos a mano añadidos (métricas 02, LambdaRank 07, logQ 08, RQ 11) | 4 |
| Rutas «🧭 núcleo vs ampliación» en módulos sobrecargados (06, 12, 15, 19) + plan de sprint del capstone | 5 |
| Puentes/analogías nuevas (RAG ↔ embudo, BEIR ↔ NDCG, walk-forward ↔ split temporal, EASE ↔ ridge, DIN ↔ cross-attention, MMoE ↔ MoE de LLMs, CUPED ↔ ANCOVA…) | ~12 |

## 📌 Recomendaciones pendientes (cambios grandes, no aplicados)
1. **Partir 12 y 19** en dos notebooks cada uno (12a/12b; 19a §0–4 / 19b §5–8) con autoevaluación propia. Las cajas 🧭
   mitigan, pero 80–86 celdas por sesión superan una carga cognitiva razonable.
2. **Aligerar 06**: mover FFM y GBDT+LR a «📚 Para profundizar» (o a un notebook opcional) para suavizar el salto 05 → 06.
3. **Autoevaluaciones con feedback ejecutable**: convertir 2–3 preguntas de cálculo por módulo en celdas `assert`
   (p. ej. «calcula NDCG@5 de esta lista» con comprobación), como ya hacen los tests de los proyectos 02 y 04.
4. **Repaso acumulativo por bloque**: un mini-notebook de 30 min al final de cada bloque (I–VI) con 8–10 preguntas
   mezcladas de todos sus módulos (interleaved practice), en vez de solo repasos por módulo.
5. **Rúbrica del capstone**: añadir 3–5 respuestas cortas del marco de *system design* (§4 del 18) aplicadas al propio
   CineMatch del alumno, para evaluar también el objetivo 4 del módulo.
6. **Protocolos de evaluación**: el curso usa tres protocolos (prepare_cinematch 01–02, 80/20 del bloque II, LOO en
   09–11). Están avisados, pero una tabla única en la guía o en el 02 («qué protocolo usa cada módulo y por qué»)
   evitaría comparaciones indebidas entre módulos.
7. **Terminología**: el curso es consistente en lo esencial (*retrieval*, *re-ranking*, reentreno, cold start); quedan
   variantes menores («re-entrenar»/«reentrenar», «split»/«partición»). El glosario fija la forma preferida; un pase
   de búsqueda/reemplazo en los builders las unificaría.
