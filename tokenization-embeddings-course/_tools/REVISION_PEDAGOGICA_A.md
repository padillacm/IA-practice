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

## 04 · Diseño de tokenizers modernos
- Bien: intuición del vocabulario como presupuesto → teoría de parámetros con cifras → mediciones reales; analogía
  con coste económico (USD por idioma) y ventana de contexto; 6 preguntas etiquetadas; 62 celdas (no necesita 🧭).
- **Reestructurado:** igual que en 03, el Mapa de madurez era la §3 (antes de la intuición); ahora es la §13 (tras el
  resumen de decisiones, antes de 🏭). Secciones 4–13 renumeradas (3–12) y referencias internas actualizadas
  («medido abajo» → «medido en la sección 5/8»).
- **Repaso espaciado:** el 🔁 solo preguntaba por 02–03. Añadidas R4 (módulo 01, Cálculo: bytes y tokens máximos de
  «Привет, мир») y R5 (módulo 00, Diagnóstico: ¿una mejora de nDCG de 0.02 en 40 consultas es real? → IC pareado).
- **Andamiaje del proyecto:** paso 2 sin 🪜 Pista 2 y paso 4 (receta + justificación) sin pistas: añadidas.

## 05 · Patologías y robustez
- Bien: 🔁 con repaso espaciado de 01, 02/04 y 03/04; intuición («dos entrenamientos que nunca se hablaron») antes de
  la derivación del gradiente; banco MiniGPT con verdad de referencia que permite **medir** el detector; enfoque
  defensivo explícito; 👀 en todos los gráficos.
- **Carga cognitiva:** ≈ 74 celdas sin 🧭. Añadida la ruta núcleo (secciones 3–5, 10–12, lo que usa el proyecto) vs
  ampliación (6–9: letras, aritmética, espacios, *token healing*).
- **Reestructurado:** Mapa de madurez movido de §3 a §13 (antes de 🏭), como en 03–04; secciones renumeradas y
  referencias internas («sección 6/11») actualizadas.
- **Alineamiento proyecto ↔ solución:** el enunciado del paso 2 listaba U+200B, U+2060, U+FEFF pero la pista y la
  solución también eliminan U+200C y U+2061–U+2064; enunciado corregido. Añadida una caja 🔁 que contrasta con el
  `normalizar` del módulo 01 (que conservaba el ZWNJ en persa/índicas): decisión de diseño explícita.
- **Andamiaje:** el paso 3 (fuzzing + informe de hallazgos) solo tenía 🪜 1; añadida 🪜 2 (cómo convertir la tabla de
  fallos por clase en hallazgos con evidencia, severidad y mitigación).

## 06 · Tokenizer-free I (bytes, BLT)
- Bien: 🔁 con repaso espaciado de 01, 02 y 05; intuición «la tokenización es una heurística de compresión»;
  experimento propio (n-grama Witten-Bell + TinyGPT + MiniBLT) separado con claridad de las cifras **reportadas**
  por el paper; honestidad sobre madurez 🟡/🔴.
- **Carga cognitiva:** ≈ 72 celdas sin 🧭; añadida ruta núcleo (lo que usa el proyecto) vs ampliación (familia de
  modelos, parcheo incremental, MiniBLT, librerías), con la sugerencia de ejecutar MiniBLT sin estudiarlo si falta
  tiempo.
- **Ejemplo a mano:** la teoría del parcheo por entropía (§6) pasaba de la fórmula al código; añadido cálculo
  de $H$ tras «el servid» (0.80 bits) y tras «el␣» (4 bits) con $\theta_g=2$, enlazado con la analogía del compresor
  aritmético del módulo 02.
- **Reestructurado:** Mapa de madurez de §4 a §12 (antes de 🏭); secciones 5–12 renumeradas (4–11), incluidas las
  subsecciones en `nb.md("### …")` y la referencia interna «sección 8» → 7.
- **👀 añadidas:** tras la figura «La misma frase agrupada de cuatro maneras» (lección) y tras la figura de resumen
  del proyecto (incremental / estabilidad / inflación con erratas), con qué hacer si contradice la lección.

## 07 · H-Net y tokenizer transfer
- Bien: 🔁 con repaso espaciado de 06, 02/04 y 05 (tokens sub-entrenados ↔ inicializar tokens nuevos); intuición
  antes de la teoría; cifras reportadas separadas de las medidas; checklist de cambio de tokenizer; 57 celdas.
- **Ejemplos a mano:** §4 (dynamic chunking) era solo fórmulas; añadido cálculo de $p_t$ para dos cosenos y de la
  ratio loss con $N=4$ en el óptimo (1) y en los dos colapsos (4 y 1.33), con la analogía del balanceo de carga MoE.
  En tokenizer transfer, ejemplo FVT con vectores de juguete y analogía con el *cold start* de ítems en recsys.
- **Reestructurado:** Mapa de madurez de §4 a §8 (antes de 🏭); secciones 5–8 renumeradas (4–7).
- **👀 añadida** tras las curvas de adaptación del proyecto, coherente con lo medido por la revisión de
  ejecutabilidad (en cero-shot las inits apenas difieren; tras la fase 1, FVT ≈ 0.70 vs aleatoria ≈ 0.78 bpb).

## 08 · Tokens multimodales y de audio
- Bien: 🔁 que conecta VQ con BPE (diccionario con/sin pérdida), bits por byte ↔ bpp/kbps y presupuesto de contexto
  (04); intuición «tokenizar = cuantizar»; datos reales (MNIST, fotos de scikit-learn, voz FSDD); 59 celdas.
- **Ejemplo a mano:** VQ-VAE pasaba de la pérdida al código; añadido un codebook de 3 vectores en 2D (distancias,
  token elegido, commitment, 1.58 bits) con la analogía explícita k-means ↔ PQ de los índices ANN (módulo 14).
- **Reestructurado:** Mapa de madurez de §4 a §12 (antes de 🏭); secciones 5–12 renumeradas (4–11), incluida la
  referencia «parches ViT (sección 6)» → 5.
- **👀 añadida** tras la figura de tasa-distorsión del proyecto (imagen y audio), formulada sin presuponer el
  resultado frente a JPEG y con la conclusión que el alumno debe poder defender.

## Transversal
- **Patrón corregido en 03–08:** el Mapa de madurez iba al principio (antes de la intuición) en seis lecciones y
  nombraba técnicas aún no enseñadas. Ahora va siempre al final, justo antes de 🏭, como en 00–02. Si el bloque B
  tiene el mismo patrón, conviene aplicarle el mismo cambio.
- **Ejemplos a mano añadidos** donde la secuencia saltaba de la fórmula al código: BM25 (00), entropía del parcheo
  (06), routing/ratio loss/FVT (07), VQ (08); y en 02 el ejemplo se movió delante de la formalización.
- **🧭** ahora en 01, 02, 03 (movida al inicio), 05 y 06 (nuevas): todas las lecciones de más de ~70 celdas.
- **👀 tras todos los gráficos de proyectos** (00, 01, 02, 06, 07, 08), que no tenían ninguna.
- `GUIA_DE_ESTUDIO.md` creada (ruta y tiempos 00–20, rutas abreviadas, mapa mermaid, glosario ES/EN del bloque A
  y sección vacía para el revisor pedagógico B); enlazada desde el README del curso.
- `check_course.py`: Todo OK.

## Pendientes y recomendaciones (no aplicadas)
- **Duraciones:** la lección 00 se estima en ≈ 1 h con 65 celdas (métricas, BM25 propio, bootstrap); 1.5 h es más
  realista. No se cambió para no descuadrar las 104 h del SYLLABUS.
- **Repaso espaciado:** los 🔁 de 06–08 repasan 01–06, pero ninguno vuelve a las métricas del módulo 00 salvo el 04;
  conviene que el 🔁 del 09 o del 13 retome nDCG/IC bootstrap antes de la evaluación de retrieval.
- **Terminología:** se alterna «prima», «token tax» e «impuesto de idioma» (02, 04); la guía de estudio los
  recoge como sinónimos. Unificar en la pasada final de consistencia.
- **Celdas Gemini:** todas tienen placeholder ASCII útil y 👀 detrás; `extras/GEMINI_ASSETS.md` sigue pendiente de
  regenerar (lo dejó anotado la revisión técnica): los prompts no cambiaron en esta revisión, solo el placeholder
  de M02-VID-01.
- **Avisos de datos sintéticos:** claros en todos los notebooks; la guía de estudio añade cómo leer las rúbricas
  con datos reales (criterios relativos frente a absolutos).
