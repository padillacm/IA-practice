# Revisión pedagógica · Bloque A (módulos 00–08)

Revisor pedagógico A (oct-2026). Criterios: progresión y prerrequisitos, secuencia intuición → ejemplo a mano →
fórmula → código desde cero → librería → experimento, analogías explícitas (compresión, IR/recsys, lingüística),
alineamiento objetivos ↔ lección ↔ proyecto ↔ autoevaluación, andamiaje de proyectos (🪜), repaso espaciado (🔁),
cajas 👀 tras gráficos y celdas Gemini, preguntas de Cálculo/Diagnóstico/Transferencia, carga cognitiva (🧭) y
terminología. Todos los cambios se hicieron en los builders (`_tools/builders/`) y se regeneraron los notebooks.
La ruta de estudio del curso completo y el glosario están en `GUIA_DE_ESTUDIO.md`.

Auditoría automática inicial (lección/proyecto): celdas, gráficos, celdas Gemini, 👀 ausentes, 🔁, 🧭, 🪜 y preguntas
etiquetadas. Puntos de partida: todas las lecciones tenían ≥ 3 Gemini con 👀 detrás y ≥ 3 preguntas etiquetadas; los
huecos estaban en 👀 tras gráficos de proyectos, 🧭 en lecciones largas, repaso espaciado limitado al módulo anterior
y algún ejemplo a mano ausente.

## 00 · Intro
- Bien: secuencia métricas (ejemplo a mano → fórmula → código → tests), BM25 con analogía IR/recsys, autoevaluación
  con 3 preguntas etiquetadas, proyecto con 🪜 en todos los TODO y solo pide lo enseñado (bootstrap en §10.3).
- **Arreglado:** BM25 saltaba de la fórmula al código sin ejemplo numérico. Añadido un **ejemplo resuelto a mano**
  (3 documentos, consulta «gato»: 0.499 / 0.598 / 0) y una celda que lo comprueba con el `BM25` propio.
- **Arreglado:** el gráfico del proyecto (baseline vs `split_ident`) no tenía 👀; añadido.

## 01 · Unicode y bytes
- Bien: ya tenía 🧭 (≈ 75 celdas), 🔁 sobre 00, ejemplo a mano de UTF-8 (`€` → `E2 82 AC`) antes del código,
  analogías explícitas (Huffman/códigos de prefijo, bits por byte, grafema como unidad lingüística), 6 preguntas
  etiquetadas. El proyecto solo pide lo enseñado (mojibake y doble mojibake en §10, homoglifos en §7) con 🪜 1/2.
- **Arreglado:** el gráfico del TODO 7 del proyecto (nDCG limpio/sucio/normalizado) no tenía 👀; añadido con la
  lectura esperada y qué hacer si «normalizado» no alcanza a «limpio».
