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
