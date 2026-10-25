# Módulo 05 · Patologías y robustez de la tokenización

🟠 Avanzado · ≈ 5 h · CPU (GPT-2 real opcional) · Hilo conductor: **Políglota**, informe de robustez antes de congelar el vocabulario del embedder.

## Qué aprenderás
- **Glitch tokens / tokens sub-entrenados** (SolidGoldMagikarp; Land & Bartolo 2024): por qué ocurren (tokenizer y modelo entrenados con datos distintos), derivación del colapso a una dirección común y **detectores** (distancia coseno a bytes imposibles, norma, frecuencia, verificación por comportamiento).
- **Auditoría sin modelo** de tokenizers reales: tokens parciales UTF-8 e inalcanzables (`tiktoken`).
- Fallos de **conteo de letras** («strawberry») y de **aritmética** (alineación de tokens L2R vs R2L).
- Sensibilidad a **espacios, mayúsculas y typos** (deriva de tokens) y **prompt boundary / token healing** (medido con un modelo pequeño).
- **Unicode invisible** (bloque Tags, ancho cero, bidi), homoglifos e **inyección de tokens de control**: `inspecciona`, `sanitiza` y defensas (enfoque defensivo, sin payloads dañinos).
- **Fuzzing** de tokenizer + modelo por clases de entrada y propiedades.

## Archivos
| Archivo | Contenido |
|---|---|
| `05_patologias_robustez.ipynb` | Lección (4 celdas Gemini: 3 imágenes + 1 video; 10 gráficos en código) |
| `05_proyecto_patologias_robustez.ipynb` | Proyecto: detector de tokens sub-entrenados + sanitizador + fuzzer (TODOs, pistas 🪜, rúbrica, solución tras ⛔ SPOILER) |
| `assets/` | Imágenes/videos de Gemini (`M05-IMG-01.png`, `M05-VID-01.mp4`, …) |

## Banco de pruebas
`cargar_banco()` usa **GPT-2 real** (HF) con `FAST_DEV_RUN=False` y red; si no, un **MiniGPT local** (≈ 1 min en CPU) cuyo tokenizer vio un hilo de nombres de usuario que el modelo nunca ve: así hay verdad de referencia (frecuencia 0) para medir los detectores. Es un modelo de juguete: sirve para el mecanismo, no para cifras de GPT-2.

## Prerrequisitos y conexiones
Módulos 01 (Unicode), 02–04 (BPE, vocabularios, especiales y plantillas). Continúa en el módulo 06 (modelos sin tokenizer, que evitan varias de estas patologías).

## Datasets
Corpus Políglota (HF Wikipedia + CodeSearchNet → Europarl + stdlib → sintético). Sin datasets adicionales.

## Lecturas
Rumbelow & Watkins 2023 · Land & Bartolo 2024 · Li et al. 2024 · Jang et al. 2024 · Edman et al. 2024 · Singh & Strouse 2024 · Chai et al. 2024 · Phan et al. 2024. Enlaces verificados en la lección.
