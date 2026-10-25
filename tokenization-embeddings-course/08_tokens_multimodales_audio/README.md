# Módulo 08 · Tokens multimodales y de audio

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) · **Cómputo:** CPU en `FAST_DEV_RUN=True` (≈ 6-10 min); T4 en modo completo

| Archivo | Contenido |
|---|---|
| `08_tokens_multimodales_audio.ipynb` | Lección: presupuesto de tokens por modalidad, parches ViT (continuo), VQ-VAE/FSQ/RVQ desde cero en MNIST, colapso del codebook, un LM sobre tokens de imagen (mini-Chameleon), códec de audio de juguete con RVQ y *quantizer dropout* (SNR/LSD vs μ-law), EnCodec en `transformers`, tokenizers de vídeo, tokens discretos vs continuos |
| `08_proyecto_tokens_multimodales_audio.ipynb` | Proyecto: **tokenizar una foto real (VQ) y un clip de audio (RVQ)** y medir reconstrucción y compresión vs JPEG y μ-law (plantilla con TODOs, pistas, rúbrica calibrada, solución tras SPOILER) |
| `assets/` | Imágenes/video de Gemini: `M08-IMG-01.png`, `M08-IMG-02.png`, `M08-IMG-03.png`, `M08-VID-01.mp4` |

## Objetivos
1. Distinguir tokens continuos (parches) y discretos (códigos) y calcular su coste de contexto.
2. Implementar VQ-VAE, FSQ y RVQ; medir PSNR, bits por imagen y perplejidad de uso del codebook.
3. Entrenar un LM sobre tokens de imagen y generar muestras.
4. Construir un códec de audio de juguete y medir kbps, SNR y distancia log-espectral.
5. Conectar con embeddings multimodales (módulo 16) sin adelantarlo.

## Datasets
**MNIST** real (`torchvision`, descarga desde el espejo de PyTorch; respaldo: figuras sintéticas), **foto real** empaquetada con scikit-learn (`china.jpg`, `flower.jpg`; sin descargas) y **voz real** del *Free Spoken Digit Dataset* (GitHub; respaldo: audio sintético «tipo voz»). Opcional: LibriSpeech pequeño / pesos de EnCodec desde el hub (no disponibles en el entorno de autoría; con fallback documentado). **Estado de pruebas:** MNIST real, fotos reales de scikit-learn, voz real FSDD y el respaldo sintético se ejecutaron; EnCodec/Mimi **con pesos reales** y LibriSpeech **no pudieron probarse** (hub bloqueado): la celda de EnCodec se probó con pesos aleatorios (solo formas y tasas).

## Lecturas
Oord et al. 2017 (VQ-VAE) · Esser et al. 2020 (VQGAN) · Mentzer et al. 2023 (FSQ) · Chameleon 2024 · Zeghidour et al. 2021 (SoundStream) · Défossez et al. 2022 (EnCodec) · Défossez et al. 2024 (Moshi/Mimi) · NVIDIA 2025 (Cosmos).

## Enlaces
Anterior: [07 · Tokenizer-free II y tokenizer transfer](../07_hnet_tokenizer_transfer/) · Siguiente: [09 · La capa de embedding en LLMs](../09_capa_embedding_llm/)
