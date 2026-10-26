# Módulo 11 · Aprendizaje contrastivo para embeddings

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 6 h (lección ≈ 3.5 h + proyecto ≈ 2.5 h) · **Cómputo:** `FAST_DEV_RUN` en CPU/T4 (≈ 10–12 min la lección); modo completo con L4/A100 (unidades ≈ horas reales × tarifa de tu sesión de Colab; la lección incluye un estimador de horas por FLOPs)

| Archivo | Contenido |
|---|---|
| [`11_aprendizaje_contrastivo.ipynb`](11_aprendizaje_contrastivo.ipynb) | Lección: InfoNCE y temperatura (gradiente) · derivación de la cota de información mutua y comprobación numérica con gaussianas (saturación en log K) · bi-encoder e InfoNCE desde cero (negativos en el lote, duros, simétrica) · laboratorio controlado (mundo de juguete ES/EN/código): barrido de τ, colapso, alineación/uniformidad, negativos duros limpios vs falsos negativos, tamaño de lote · SimCSE, DPR, débil → supervisado (E5/GTE/BGE) · Gradient Cache desde cero con verificación del gradiente · embedder propio de Políglota · sentence-transformers con MNRL y NO_DUPLICATES · LoRA con PEFT · estimación de cómputo |
| [`11_proyecto_aprendizaje_contrastivo.ipynb`](11_proyecto_aprendizaje_contrastivo.ipynb) | Proyecto Políglota: embedder propio entrenado con pares débiles + etiquetados y negativos duros BM25 filtrados (TopK-PercPos), comparado con BM25 y con la torre sin entrenar |
| `assets/` | Recursos de Gemini: `M11-IMG-01`, `M11-IMG-02`, `M11-IMG-03` y el video `M11-VID-01` |

## Datos y modelos
Corpus Políglota canónico (módulo 00) + «mundo de juguete» sintético con verdad conocida para los experimentos controlados (`_tools/builders/a4_common.py`). sentence-transformers sobre `paraphrase-multilingual-MiniLM-L12-v2` si hay hub; si no, un mini-BERT local sin preentrenar (fallback).

## Estado de pruebas (entorno de autoría)
Hugging Face bloqueado: lección y proyecto ejecutados completos con el corpus sintético + stdlib, el mundo de juguete y el fallback local de sentence-transformers. No se probó con modelos ni datos reales, ni en GPU. Umbrales de la rúbrica calibrados con esa ejecución. Revisión de ejecutabilidad (oct-2026, CPU, `FAST_DEV_RUN`): lección 219 s y proyecto 114 s, sin errores y reproducibles (dos ejecuciones con cifras idénticas; el vocabulario WordPiece del fallback de sentence-transformers se construye ahora de forma determinista). El `Trainer` de sentence-transformers necesita `accelerate` (añadido al `pip`).

## Lecturas clave
Oord et al. 2018 · Poole et al. 2019 · Wang & Isola 2020 · Gao, Yao & Chen 2021 (SimCSE) · Karpukhin et al. 2020 (DPR) · Wang et al. 2022 (E5) · Moreira et al. 2024 (NV-Retriever) · Gao et al. 2021 (Gradient Cache).

Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_11.py` (desde la raíz del repo).
