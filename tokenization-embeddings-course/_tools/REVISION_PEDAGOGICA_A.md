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

## 02 · BPE desde cero
- Bien: 🔁 con repaso espaciado de 00 y 01, 🧭 (≈ 81 celdas), verificación contra `tiktoken`/HF, analogías con
  compresión (bits por byte, Huffman) bien explotadas en §9.5, proyecto con 🪜 en todos los TODO.
- **Reestructurado:** la teoría formal (§3) iba antes del ejemplo resuelto a mano. Ahora §3 = ejemplo de Sennrich a
  mano (con frase puente y analogía LZW) y §4 = algoritmo formal («acabas de verlo funcionar; ahora en general»),
  como pide la secuencia intuición → ejemplo → fórmula → código.
- **Arreglado:** el placeholder de M02-VID-01 decía `low</w>×5` como estado final; tras 5 fusiones es `low </w>×5`
  (dos tokens), como dicen el texto y el prompt.
- **Arreglado:** 👀 tras el gráfico del TODO 6 del proyecto (barrido de vocabulario e impuesto de idioma).

## 03 · WordPiece, Unigram, SentencePiece
- Bien: derivación de WordPiece seguida de corpus de 5 palabras a mano; ejemplo `hugs` de Unigram a mano antes del
  EM completo; 🔁 con preguntas etiquetadas por módulo (01 y 02); proyecto que reutiliza la tubería de §7.1.
- **Reestructurado:** el **Mapa de madurez** era la §3, antes de la intuición, y nombraba técnicas aún no
  enseñadas (Unigram, BPE-dropout, likelihood de WordPiece). Ahora es la §10 (antes de 🏭), con frase puente; las
  secciones 4–10 se renumeraron (3–9) y se corrigieron las referencias internas («sección 9» → 7.1 / 8).
- **Arreglado:** la caja 🧭 estaba al final de la §9 (Resumen), donde ya no sirve para planificar; se movió al inicio,
  con los números de sección actualizados y la indicación de hacer 8.2 (exportación a `tiktoken`) antes del proyecto,
  porque el paso 4 del proyecto la usa.
- **Andamiaje del proyecto:** el paso 1 ahora remite a `construye_hf` (§7.1) y la 🪜 Pista 2 explicita
  `pre_tokenizers.Sequence` (combinar dos pre-tokenizers no se decía); el paso 5 (decisión escrita) no tenía pistas:
  añadidas 🪜 1 (estructura en cuatro frases) y 🪜 2 (qué métricas pesan para sparse vs embedder).
