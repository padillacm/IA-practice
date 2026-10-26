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
