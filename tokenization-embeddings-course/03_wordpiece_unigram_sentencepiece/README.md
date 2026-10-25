# Módulo 03 · WordPiece, Unigram, SentencePiece, tiktoken y HF `tokenizers`

🟡 Intermedio · ≈ 5 h · CPU (0 unidades de Colab) · Hilo conductor: **Políglota**, tokenizer propio (2/3).

## Qué aprenderás
- Que todo tokenizer de subpalabras decide dos cosas: **cómo se construye el vocabulario** y **cómo se segmenta** con él.
- WordPiece como ganancia de log-verosimilitud (derivación + comparación con BPE y con la fórmula «score» de los tutoriales).
- Unigram LM desde cero: lattice, EM con forward-backward, poda por pérdida, Viterbi y muestreo (subword regularization).
- SentencePiece: `▁`, tokenización reversible, `byte_fallback`, normalización y sus trampas.
- Pipeline de HF `tokenizers` (normalizer → pre-tokenizer → model → post-processor → decoder) y entrenamiento de las tres familias con la misma tubería.
- `tiktoken`: tu BPE en 12 líneas, BPE-dropout y exportación HF → `tiktoken.Encoding` con igualdad exacta.

## Archivos
| Archivo | Contenido |
|---|---|
| `03_wordpiece_unigram_sentencepiece.ipynb` | Lección (4 celdas Gemini: 3 imágenes + 1 video, 7 gráficos en código) |
| `03_proyecto_wordpiece_unigram_sentencepiece.ipynb` | Proyecto: entrenar y comparar BPE/WordPiece/Unigram (TODOs, pistas 🪜, rúbrica, solución tras ⛔ SPOILER) |
| `assets/` | Aquí van las imágenes/videos de Gemini (`M03-IMG-01.png`, `M03-VID-01.mp4`, …) |

## Prerrequisitos y conexiones
Módulos 01 (Unicode/normalización) y 02 (BPE desde cero). Continúa en el módulo 04 (diseño de vocabulario, paridad multilingüe) y 05 (patologías).

## Datasets (cadena oficial → espejo → sintético)
HF `wikimedia/wikipedia` ES/EN + CodeSearchNet (Python) → muestra Europarl ES/EN de `nltk_data` (GitHub) + código de la stdlib → texto sintético. El notebook avisa cuál usó.

## Lecturas
Schuster & Nakajima 2012 · Kudo 2018 · Kudo & Richardson 2018 · Provilkov et al. 2020 · Bostrom & Durrett 2020 · Uzan et al. 2024 · Schmidt et al. 2024. Enlaces verificados en la sección «Referencias» de la lección.
