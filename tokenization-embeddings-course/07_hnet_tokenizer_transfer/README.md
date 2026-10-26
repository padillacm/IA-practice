# Módulo 07 · Tokenizer-free II (H-Net) y *tokenizer transfer*

**Nivel:** 🔴 Experto · **Duración:** ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) · **Cómputo:** CPU en `FAST_DEV_RUN=True` (≈ 12-15 min); **L4 recomendada** (≈ 6-10 unidades) en modo completo con GPT-2 small real

| Archivo | Contenido |
|---|---|
| `07_hnet_tokenizer_transfer.ipynb` | Lección: dynamic chunking de H-Net (routing, smoothing, STE, ratio loss), **MiniHNet** desde cero, debate «¿está muerta la tokenización?», taxonomía de tokenizer transfer (FVT, WECHSEL, FOCUS, Trans-Tokenization, ZeTT), seis inicializaciones implementadas, medición en bpb antes/después de un ajuste corto |
| `07_proyecto_hnet_tokenizer_transfer.ipynb` | Proyecto: **cambiar el tokenizer de un modelo pequeño** (plantilla con TODOs, pistas, rúbrica calibrada, solución tras SPOILER) |
| `assets/` | Imágenes/video de Gemini: `M07-IMG-01.png`, `M07-IMG-02.png`, `M07-IMG-03.png`, `M07-VID-01.mp4` |

## Objetivos
1. Explicar y implementar el chunking dinámico de H-Net (routing, selección, EMA, STE, ratio loss) y verificar su causalidad.
2. Evaluar con evidencia «¿está muerta la tokenización?».
3. Clasificar los métodos de tokenizer transfer y cuándo usar cada uno.
4. Inicializar embeddings de vocabulario nuevo (media, Hewitt, FVT, FOCUS-lite, WECHSEL-lite) y medir bpb cero-shot y tras un ajuste corto.

## Datasets y modelos
Corpus Políglota (`carga_corpus()` del módulo 00). Modelo base: GPT-2 en miniatura entrenado en la propia lección (modo rápido) o **GPT-2 small** (`gpt2`) en modo completo. **Estado de pruebas:** en el entorno de autoría Hugging Face estaba bloqueado: todo se probó con corpus **sintético** (+ código real de la stdlib) y modelos diminutos locales; la ruta con `gpt2` real y Wikipedia real **no pudo ejecutarse**.

## Lecturas
Hwang, Wang y Gu 2025 (H-Net, arXiv:2507.07955) · Minixhofer et al. 2024 (ZeTT, arXiv:2405.07883) · Dobler y de Melo 2023 (FOCUS) · Minixhofer et al. 2022 (WECHSEL) · Remy et al. 2024 (Trans-Tokenization).

## Enlaces
Anterior: [06 · Tokenizer-free I](../06_tokenizer_free_bytes_blt/) · Siguiente: [08 · Tokens multimodales y de audio](../08_tokens_multimodales_audio/)
