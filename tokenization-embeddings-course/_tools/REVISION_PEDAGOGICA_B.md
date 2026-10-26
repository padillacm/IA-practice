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
