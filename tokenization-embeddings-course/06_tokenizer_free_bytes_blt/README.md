# Módulo 06 · Tokenizer-free I: bytes y *patches*

**Nivel:** 🔴 Experto · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU en `FAST_DEV_RUN=True` (≈ 6-10 min); T4 opcional en modo completo

| Archivo | Contenido |
|---|---|
| `06_tokenizer_free_bytes_blt.ipynb` | Lección: coste de leer bytes (FLOPs/byte), familia CANINE/ByT5/MegaByte/SpaceByte/MambaByte, entropía del siguiente byte, parches por entropía (umbral global y restricción monótona), parcheo incremental, arquitectura BLT, **MiniBLT** desde cero y comparación con BPE a escala diminuta, resultados publicados, ByT5/CANINE/BLT en Hugging Face |
| `06_proyecto_tokenizer_free_bytes_blt.ipynb` | Proyecto: **mini patcher entrópico vs BPE** (plantilla con TODOs, pistas, rúbrica calibrada y solución tras SPOILER) |
| `assets/` | Imágenes/video de Gemini: `M06-IMG-01.png`, `M06-IMG-02.png`, `M06-IMG-03.png`, `M06-VID-01.mp4` |

## Objetivos
1. Explicar por qué leer bytes es caro y cómo los parches recuperan el coste (FLOPs por byte).
2. Comparar CANINE, ByT5, MegaByte, SpaceByte, MambaByte y BLT.
3. Implementar un modelo de entropía de bytes y derivar parches (umbral global / monótono), calibrando el tamaño medio.
4. Verificar la propiedad de parcheo incremental y la causalidad de un modelo con parches.
5. Construir un MiniBLT y compararlo (con honestidad estadística) con un baseline BPE.
6. Leer críticamente los resultados del paper de BLT y etiquetar la madurez (🟡/🔴).

## Datasets
Corpus Políglota (`carga_corpus()` del módulo 00): Wikipedia ES/EN (HF) + CodeSearchNet; fallback sintético + funciones reales de la stdlib de Python. **Estado de pruebas:** en el entorno de autoría Hugging Face estaba bloqueado, así que se validó con el corpus **sintético** (+ código real de la stdlib). Las conclusiones cualitativas se sostienen; los números absolutos no son comparables con datos reales.

## Lecturas
Pagnoni et al. 2024 (BLT, arXiv:2412.09871) · Yu et al. 2023 (MegaByte, arXiv:2305.07185) · Slagle 2024 (SpaceByte, arXiv:2404.14408) · Xue et al. 2022 (ByT5, arXiv:2105.13626) · Clark et al. 2022 (CANINE, arXiv:2103.06874) · Wang et al. 2024 (MambaByte, arXiv:2401.13660).

## Enlaces
Anterior: [05 · Patologías y robustez](../05_patologias_robustez/) · Siguiente: [07 · Tokenizer-free II y tokenizer transfer](../07_hnet_tokenizer_transfer/)
