# Módulo 04 · Diseño de tokenizers modernos

🟠 Avanzado · ≈ 5 h · CPU (0 unidades de Colab) · Hilo conductor: **Políglota**, vocabulario propio (3/3).

## Qué aprenderás
- El vocabulario como **presupuesto**: parámetros de embedding, coste del softmax, longitud de secuencia; leyes de escala con el vocabulario (Tao et al., 2024).
- Vocabularios reales (GPT-2/4/4o, Llama, Qwen, Gemma, Mistral/Tekken) con **cifras verificadas y fechadas**.
- **Token tax**: fertilidad, bytes/token y **prima de paridad** sobre texto paralelo; traducción a dinero y a contexto efectivo.
- Números, espacios e indentación; tokens especiales y **chat templates** (y sus errores clásicos).
- **SuperBPE** (tokens que cruzan palabras) implementado en versión mínima.
- Receta de diseño para Políglota: mezcla del corpus + tamaño de vocabulario con una función de coste.

## Archivos
| Archivo | Contenido |
|---|---|
| `04_diseno_tokenizers_modernos.ipynb` | Lección (4 celdas Gemini: 3 imágenes + 1 video; 7 gráficos en código) |
| `04_proyecto_diseno_tokenizers_modernos.ipynb` | Proyecto: benchmark de paridad + receta de vocabulario (TODOs, pistas 🪜, rúbrica, solución tras ⛔ SPOILER) |
| `assets/` | Imágenes/videos de Gemini (`M04-IMG-01.png`, `M04-VID-01.mp4`, …) |

## Prerrequisitos y conexiones
Módulos 01–03. Continúa en el módulo 05 (patologías) y 07 (tokenizer transfer). El embedder de Políglota (09–11) hereda el vocabulario que decidas aquí.

## Datasets (cadena oficial → espejo → sintético)
Corpus: HF Wikipedia ES/EN + CodeSearchNet → Europarl (nltk_data) + stdlib → sintético. Paralelo: FLORES+ (`openlanguagedata/flores_plus`, puede requerir aceptar términos) → `Helsinki-NLP/opus-100` en-es → mini-conjunto a mano (16 frases × 12 idiomas, orientativo).

## Lecturas
Tao et al. 2024 · Petrov et al. 2023 · Ahia et al. 2023 · Liu et al. 2025 (SuperBPE) · Singh & Strouse 2024 · Dagan et al. 2024. Enlaces verificados en la lección.
