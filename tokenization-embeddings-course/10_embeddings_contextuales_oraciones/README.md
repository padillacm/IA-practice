# Módulo 10 · Embeddings contextuales y de oraciones

**Nivel:** 🟡 Intermedio · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU en `FAST_DEV_RUN`; T4 recomendada con modelos reales (≈ 0.5 h)

| Archivo | Contenido |
|---|---|
| [`10_embeddings_contextuales_oraciones.ipynb`](10_embeddings_contextuales_oraciones.ipynb) | Lección: estático vs contextual · pooling CLS/media/máximo/último token desde cero (máscaras, padding) y verificación contra sentence-transformers · contextualidad por capa (self-similarity vs anisotropía, Ethayarajh 2019) · pooling × encoder en Políglota vs BM25 · rogue dimensions · centrado, whitening (derivación) y all-but-the-top; BERT-flow · el idioma como dirección (centrado por idioma) · coseno vs producto vs L2 · prefijos e instrucciones (E5) · bi-encoder vs cross-encoder |
| [`10_proyecto_embeddings_contextuales_oraciones.ipynb`](10_proyecto_embeddings_contextuales_oraciones.ipynb) | Proyecto Políglota: rejilla encoder × pooling × post-procesado elegida en validación y medida en test (nDCG@10), con desglose por idioma y comparación con BM25 |
| `assets/` | Imágenes de Gemini `M10-IMG-01` … `M10-IMG-04` |

## Modelos
`distilbert-base-multilingual-cased` (crudo), `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (SBERT multilingüe) e `intfloat/multilingual-e5-small` (prefijos `query:`/`passage:`).
**Fallback documentado** (sin hub): mini-BERT solo-MLM («crudo») y mini-SBERT (el mismo + 200 pasos contrastivos con pares débiles frase-1 ↔ resto), entrenados en el notebook (~2 min de CPU).

## Datos
Corpus Políglota canónico del módulo 00 (`carga_corpus`), métricas y BM25 canónicos.

## Estado de pruebas (entorno de autoría)
Hugging Face bloqueado por el proxy: lección y proyecto ejecutados completos **solo con el fallback** y el corpus sintético + stdlib. Las celdas con modelos reales no pudieron ejecutarse aquí (protegidas con `try/except`). Umbrales de la rúbrica calibrados con esa ejecución.

## Lecturas clave
Reimers & Gurevych 2019 (SBERT) · Ethayarajh 2019 · Su et al. 2021 (whitening) · Li et al. 2020 (BERT-flow) · Wang et al. 2022 (E5) · Timkey & van Schijndel 2021.

Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_10.py` (desde la raíz del repo).
