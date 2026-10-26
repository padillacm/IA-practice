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

Mismas reglas y decisiones que el bloque A (prima de tokens, bpb, tokenizer/pre-tokenizer, pipeline, coste, video,
tuteo). Todo se cambió en los builders y se regeneró; ningún `.ipynb` se editó a mano. Coordinado con el revisor
élite B (solo se tocó cada módulo cuando él lo tenía marcado).

### Decisiones añadidas en el bloque B (registradas en `GUIA_DE_ESTUDIO.md`)
| Concepto | Forma canónica | Se sustituyó |
|---|---|---|
| producto de vectores | **producto escalar** | «producto punto» (12, 13, 15, 18, guía de entrevistas) |
| negativos parecidos e irrelevantes | **negativos duros** (*hard negatives*) | «negativos difíciles» (11, 12, guía de entrevistas) |
| segunda etapa | **reranker / reranking / rerankear** | «re-ranker», «re-ranking», «re-rankear» (10, 14) |
| reordenar candidatos | **rescoring** | «re-score» (13) |
| grafías | multi-vector (prosa; `multivector` solo como nombre de opción de Qdrant), video, coste | «costo», «vídeo» (12, 13, 18, extras) |

### Cabeceras y encabezados (pendientes de la revisión pedagógica B, resueltos)
- **Cabecera en tabla** en las 24 cabeceras de 09–20 con las etiquetas del bloque A: **Nivel · Duración estimada · GPU
  recomendada · Prerrequisitos** (12, 13, 14, 18, 19, 20 las tenían en línea con «Duración/GPU/Cómputo»; 09–11
  usaban «Cómputo» y «Requisitos»; 15–20 «Requiere»). Subtítulo del curso añadido bajo el título en las 12 lecciones.
- **Encabezados**: contenido numerado «## N. Título» (12–14 usaban «## N ·»); secciones fijas **sin número y con emoji**
  en las 12 lecciones: 🎯 Objetivos · 🔁 Conexión · 🗺️ Mapa de madurez · 🏭 En producción · 🧠 Secretos de la élite ·
  ⚠️ Errores comunes · 📝 Autoevaluación · 📚 Referencias (09–11 no tenían emoji; 12–17 numeraban las fijas; 15–17 usaban ✅).
- Niveles y horas de las 24 cabeceras coinciden con `README.md`, `SYLLABUS.md` y `GUIA_DE_ESTUDIO.md`; los 42 badges
  apuntan a su ruta real; enlaces relativos (incluidos los de `recsys-course/` y a módulos del bloque A) sin roturas.

### Celdas Gemini (revisión una por una)
IDs unificados a dos dígitos (`M15-IMG-1` → `M15-IMG-01`, 15–17) y numerados por orden de aparición (15, 17, 19).

| Módulo | IMG/VID | Cambios |
|---|---|---|
| 09 | 3 / 0 | IMG-01 con los ids GPT-2 **reales** de «El gato come pescado» (7 tokens: El·Ġg·ato·Ġcome·Ġp·esc·ado = 9527, 308, 5549, 1282, 279, 3798, 4533; antes 4 ids inventados) e IMG-03 con las piezas reales de « serialización» (Ġserial·iz·aci·ón), verificados con `tiktoken` y el vocabulario gpt2. |
| 10 | 4 / 0 | Paleta completa y sans-serif en IMG-03/04; candado decorativo → línea «pesos compartidos». |
| 11 | 3 / 1 | VID-01 recalculado (softmax con τ = 0.05 y 1: pérdidas 0.37/0/0.44/0, medias 0.20 y 1.08: correctas); «sin música»; IMG-03 sin rojo fuera de paleta. |
| 12 | 3 / 1 | IMG-03: los enteros int8 no salían de ninguna regla → recalculados con [lo, hi] = [−0.5, 0.5] como el ✍️ de §5 (0.12 → 30; 0.64 recortado a 127); VID-01 con rankings marcados ilustrativos. |
| 13 | 4 / 1 | MaxSim 0.82 + 0.91 + 0.78 = 2.51 verificado; 👀 añadido tras IMG-04 (faltaba); SPLADE «ilustrativo». |
| 14 | 3 / 1 | Correctas (PQ d = 1024, m = 64 → 64 B, 64× menos que float32); «sin música», reranking. |
| 15 | 3 / 1 | VID-01: el remuestreo de «media 0.61» daba 0.69 → listas nuevas con medias exactas (0.61, 0.49, 0.58) e IC percentil recalculado ≈ [0.35, 0.77] (decía [0.37, 0.74]). LIMIT (pentágono, 5 de 10 pares) correcto. |
| 16 | 3 / 1 | «mapa de calor en 6.2» (decía 6.3); ColPali ≈ 258 KiB/página (1030 × 128 × 2 B). |
| 17 | 3 / 1 | 👀 añadido tras VID-01 (faltaba); SAE de IMG-03 con 96 latentes como §7 (decía 256); colores fuera de paleta sustituidos. Pentágono: cosenos 0.31 / −0.81 verificados. |
| 18 | 3 / 1 | IMG-02: un lote de 2 peticiones no podía cerrarse por `max_batch = 32` → ejemplo con q1–q7 y `max_batch = 4`; IMG-01 sin «p99 ≤ 100 ms» inventado; «sin música». |
| 19 | 3 / 0 | Árbol IMG-01 alineado con `elige_indice` (70 % de la RAM; grafo + vectores en SSD). |
| 20 | 2 / 1 | VID-01 con listas y puntuaciones RRF exactas (doc-5 = 2/63 = 0.0317, doc-2 = 1/62 + 1/65 = 0.0315, doc-7 = 1/61 = 0.0164); IMG-02 con los 7 criterios reales; IMG-01 sin «int8» fijo. |

**Conclusión del bloque B.** 46 celdas Gemini (37 imágenes, 9 videos): todas con ≥ 3 celdas y ≥ 2 imágenes por
lección y video en 11, 13, 14, 18 y 20 (además en 12, 15, 16 y 17). Todas tienen «👀 Qué debes observar»
inmediatamente después, la paleta y el estilo comunes, «Evita: …» y, los videos, guion con tiempos y «sin música».
Las que muestran cifras cualitativas lo declaran (ilustrativas) y ninguna duplica un gráfico de código.

### Extras y global
- `extras/GUIA_ENTREVISTAS.md`: «impuesto de idioma» → prima de tokens; costo → coste; producto punto → producto escalar;
  negativos difíciles → negativos duros. `extras/LECTURA_PAPERS.md`: costo → coste. `GUIA_DE_ESTUDIO.md`: «token tax» → prima de tokens.
- `README.md`: estado «completo», sección «Material de apoyo» con enlaces a la guía de estudio, los extras y `recsys-course/`.
- `REVISION_TECNICA_B.md`: la nota «jina-v5-nano sin resolver» marcada como resuelta (8k/8192, `REVISION_REFERENCIAS_B.md`).
- `extras/GEMINI_ASSETS.md` regenerado (00–20: 81 recursos, 65 imágenes y 16 videos), sin IDs duplicados; `check_course.py`: Todo OK.
- No aplicado: el módulo 00 (bloque A) sigue usando «producto punto» en 3 sitios.
