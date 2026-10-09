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
