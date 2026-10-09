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
- 📌 La lección usa su propio protocolo del Bloque II (80/20, train con todos los ratings) distinto de
  `prepare_cinematch`; está bien avisado en el proyecto, pero convendría repetir el aviso en la lección (sección 3).
