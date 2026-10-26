# Revisión de consistencia y lenguaje + celdas Gemini

Pasada final de consistencia (terminología, tono, cabeceras, enlaces/badges) y revisión una por una de las
celdas Gemini (🎨/🎬). Todos los cambios se hicieron en los builders (`_tools/builders/`) y se regeneraron los
notebooks; ningún `.ipynb` se editó a mano. `extras/GEMINI_ASSETS.md` se regenera al final del curso.

## Bloque A (00–08)

### Decisiones de terminología (canónicas en todo el bloque; registradas en el glosario de `GUIA_DE_ESTUDIO.md`)
| Concepto | Forma canónica | Se eliminó / sustituyó |
|---|---|---|
| tokens extra de un idioma frente al inglés | **prima de tokens** (*tokenization premium*; se menciona una vez «token tax» como coloquial, en 04) | «impuesto de tokens», «impuesto de idioma», «impuesto por idioma», «token tax» como título, «prima de tokenización», «prima de paridad» |
| bytes extra de UTF-8 por escritura | **prima de bytes** (01, 06) | «impuesto de bytes», «impuesto de UTF-8» |
| compresión normalizada | **bits por byte (bpb)**; `bpb` en fórmulas y tablas | «bits/byte», «BPB» |
| herramienta que parte el texto | **tokenizer** / **pre-tokenizer** (m.) | «tokenizador», «pre-tokenizador» (salvo la frase de ejemplo en español) |
| cadena de etapas | **pipeline** (m.) | «tubería» |
| regla aprendida de BPE | **merge** (m., pl. *merges*); el verbo es **fusionar** y «fusión» designa el acto de aplicar un merge | — (uso ya coherente; se documenta) |
| coste económico | **coste/costes** | «costo/costos» |
| medio audiovisual | **video** (como en «🎬 GEMINI-VIDEO») | «vídeo» |
| registro | tuteo singular | «entrenasteis», «tenéis» |
| grafías oficiales verificadas | GPT-2, Llama 3 (LLaMA solo en el título del paper de 2023), SentencePiece, `tiktoken`, Hugging Face, ByT5, MegaByte (el paper escribe MEGABYTE: así en la referencia), H-Net, EnCodec, SoundStream, FLORES-200 / FLORES+ | «Flores-200» |

### Cabeceras
- Etiquetas unificadas en lección y proyecto: **Nivel · Duración estimada · GPU recomendada · Prerrequisitos**
  (00–05 usaban «Duración», «GPU», «GPU / coste»).
- Las lecciones 03–08 no llevaban el subtítulo del curso bajo el título: añadido.
- Proyectos 00–02: título «# Proyecto NN · …» como en 03–08.
- Niveles y horas de las 18 cabeceras coinciden con `README.md`, `SYLLABUS.md` y la tabla de `GUIA_DE_ESTUDIO.md`.
- Badges de Colab: los 18 apuntan a `padillacm/IA-practice/blob/master/<ruta real del notebook>`; enlaces internos relativos sin roturas.

### Celdas Gemini (revisión una por una)
Criterios comprobados en cada celda (script de auditoría + lectura): generada con `nb.gemini` (marca «⚠️ REEMPLAZAR
ESTA CELDA», ID único con prefijo del módulo), prompt autocontenido con el bloque de estilo común (fondo blanco,
paleta #1F6FEB/#F28E2B/#2CA02C/#6B7280, sans-serif), textos literales entre «», composición explícita, datos exactos,
línea «Evita: …», guion por escenas con tiempos en los videos, formato/alt/instrucción de inserción, placeholder
útil, «👀 Qué debes observar» justo después, sentido pedagógico y sin duplicar un gráfico de código.

| Módulo | Celdas (IMG/VID) | Veredicto y cambios |
|---|---|---|
| 00 | 3 / 0 | Las tres correctas (mapa del curso, pipeline con ids GPT-2 verificados, arquitectura de Políglota). Añadida en la sección 2 la instrucción para videos largos: generar por escenas y concatenar si el generador produce clips cortos. |
| 01 | 4 / 0 | Correctas y con datos exactos (bytes del emoji de familia, € = E2 82 AC, code points de NFC/NFD/NFKC/NFKD, homoglifo). M01-IMG-01: «Evita» prohíbe dibujar personas o cambiar los miembros de la familia; M01-IMG-04: «Evita» prohíbe logotipos/colores de marca (la palabra va en texto plano). |
| 02 | 3 / 1 | Correctas; recuentos de pares del video M02-VID-01 recalculados a mano (desempate lexicográfico e s / s t / t </w>, l o / o w). Arreglado «con música ausente» → «sin música». |
| 03 | 3 / 1 | Datos del video M03-VID-01 (lattice de «hugs») recalculados: 8 segmentaciones, P(X) = 0.1751, posterior de Viterbi 0.857, probabilidades semilla suman 1; offsets de M03-IMG-03 verificados. Añadido pie «segmentaciones ilustrativas» (M03-IMG-01) e «ids ilustrativos» (M03-IMG-03) para que Gemini no las presente como reales. |
| 04 | 3 / 1 | M04-IMG-02: título del prompt «Token tax» → «Prima de tokens» (terminología canónica); placeholder con 11 fichas en español (decía 10). M04-IMG-03: placeholder de ChatML reescrito (los `\n` se convertían en saltos y descuadraban el ASCII). M04-VID-01: escena 2 sin la acción vaga «vuelven a fusionarse», escena 4 con resultado explícito «7 → 5 tokens». |
| 05 | 3 / 1 | M05-VID-01, escena 4 reescrita: el detector mide la distancia coseno de cada fila a los **tokens de referencia** (bytes 0xF5–0xFF), no «del centro del cúmulo azul», como sugería el guion. M05-IMG-01: pie en español («distancia coseno»), id marcado como ilustrativo. M05-IMG-02/03 correctas (ids 496/675/15717 de «strawberry» en cl100k). |
| 06 | 3 / 1 | Recuentos verificados: «El gato duerme.» = 15 bytes en las 4 segmentaciones; «El servidor procesa las peticiones.» = 35 bytes → 5 parches. M06-IMG-03: 40 casillas (decía 41) y placeholder con «␣» coherente; M06-IMG-01: picos de entropía situados en «␣g»/«␣d» (inicio real de parche); M06-VID-01: «sin música» como el resto de videos y sin términos en inglés sueltos que Gemini pudiera rotular. |
| 07 | 3 / 1 | M07-IMG-02: los anchos de los chunks no cuadraban con las fronteras marcadas (bordes en «n», «p», «d» ⇒ chunks «n e w _» / «p r o» / «d u c t !» = 4, 3, 5; prompt y placeholder decían 4, 5, 3). M07-VID-01: «sin música». M07-IMG-01/03 correctas. |
| 08 | 3 / 1 | Cifras verificadas: EnCodec 24 kHz, strides 2·4·5·8 = 320 → 75 frames/s × 8 niveles × 10 bits = 6 kbps; Mimi 12.5 × 8 × 11 bits = 1.1 kbps; Chameleon 1 024 tokens/512×512 con K = 8192; ViT 196 parches; en M08-VID-01 el centroide más cercano a (3.2, 2.1) es (4, 4) (2.06 frente a 2.25). Añadido «sin música». |

**Conclusión del bloque A.** 32 celdas Gemini (25 imágenes, 7 videos): todas cumplen el mínimo por lección
(≥ 3 celdas, ≥ 2 imágenes; video en 02, 06 y 07, y además en 03, 04, 05 y 08). Ninguna duplica un gráfico de
código: las que muestran cifras cualitativas (M04-IMG-02, M06-IMG-03, M07-VID-01) las declaran ilustrativas y su
«👀» remite a la medición real del notebook. Las 32 tienen «👀 Qué debes observar» inmediatamente después.

**Pendiente para la pasada final:** regenerar `extras/GEMINI_ASSETS.md` con `_tools/gen_gemini_index.py` (los
prompts de 01, 03–08 cambiaron en esta revisión).

## Bloque B (09–20)

> Pendiente: la completa el revisor de consistencia del bloque B.
