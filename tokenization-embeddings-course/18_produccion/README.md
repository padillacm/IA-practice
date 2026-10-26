# Módulo 18 · Embeddings y retrieval en producción

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **Cómputo:** CPU (0 unidades de Colab); T4 opcional para medir throughput real

| Archivo | Contenido |
|---|---|
| [`18_produccion.ipynb`](18_produccion.ipynb) | Lección: costes API vs GPU (fórmulas, precios fechados oct-2026, punto de equilibrio) · batching y padding medidos con un encoder Transformer · micro-batching dinámico (simulación de colas, p50/p99) · *tail at scale* con fan-out y hedged requests · TEI y vLLM (referencia + cliente) · caché LRU con versión en la clave (hit rate con tráfico Zipf, bug de caché sin versión) · **migración v1→v2 medida**: re-embedding vs adaptadores ridge/Procrustes (query-side y doc-side) con test pareado · cuantización int8/binaria + rescoring · **Qdrant en modo local** (named vectors por versión, filtros; respaldo FAISS) · híbrido + filtro por idioma · inversión de embeddings y ruido (privacidad vs utilidad) · drift sin etiquetas (top-1, PSI) · A/B vs team-draft interleaving (potencia) |
| [`18_proyecto_produccion.ipynb`](18_proyecto_produccion.ipynb) | Proyecto **Servicio Políglota**: `ServicioPoliglota` con caché LRU versionada, FAISS por versión, BM25, RRF, filtro por idioma, alias `prod`, adaptador servido como versión, latencias frío/caliente, plan de migración con costes y tests pareados, API FastAPI opcional. TODOs, pistas 🪜, rúbrica de 100 puntos calibrada y solución tras ⛔ SPOILER |
| `assets/` | Recursos de Gemini: `M18-IMG-01.png`, `M18-IMG-02.png`, `M18-IMG-03.png`, `M18-VID-01.mp4` |

## Objetivos
1. Calcular costes de embeber y servir (API vs GPU) con supuestos explícitos y fechados.
2. Medir batching/padding y razonar p50/p99 con colas y fan-out.
3. Implementar caché versionada y medir su hit rate.
4. Implementar y medir la migración de embedder (re-embedding vs adaptador lineal).
5. Operar una vector DB ligera con filtros y versiones; combinarla con BM25.
6. Cuantificar privacidad (inversión), detectar drift y elegir entre A/B e interleaving.

## Piezas reutilizadas (no reescritas)
Corpus, métricas y BM25 canónicos (`_tools/builders/poliglota_utils.py`, módulo 00) · embedders con fallback (`_a5_common.py`, módulo 12) · `bootstrap_ci`/`paired_bootstrap` (`poliglota_eval.py`, módulo 15). El servicio del proyecto (`_tools/builders/_a7_common.py`) se reutiliza en el capstone (módulo 20).

## Datos y modelos
Corpus Políglota (`carga_corpus`, cadena oficial → espejo → sintético). Embedders v1/v2 = `multilingual-e5-small`/`multilingual-e5-base` con hub; sin hub, dos fallbacks TF-IDF+SVD distintos (48 d y 128 d).

## Estado de pruebas (entorno de autoría, oct-2026)
Lección y proyecto ejecutados completos con `nbclient` en CPU (≈ 1 min cada uno) con el corpus **sintético** + stdlib y los **fallbacks** (Hugging Face bloqueado por el proxy). **Sí se ejecutaron:** FAISS, Qdrant en modo local (`qdrant-client`), FastAPI + `TestClient`, el encoder PyTorch de las mediciones de batching. **No se pudo probar:** modelos reales del hub, TEI/vLLM (sin Docker ni hub; el cliente TEI solo corre si defines `TEI_URL`), pgvector (sin Postgres; solo SQL de referencia), throughput en GPU. Precios de API verificados en fuentes públicas (oct-2026); el precio y el throughput de GPU son **supuestos** marcados como tales.

## Lecturas
Dean & Barroso 2013 (*The Tail at Scale*) · Shen et al. 2020 (BCT, arXiv:2003.11942) · Song & Raghunathan 2020 (arXiv:2004.00053) · Morris et al. 2023 (vec2text, arXiv:2310.06816) · Chapelle et al. 2012 (interleaving, ACM TOIS) · Kohavi, Tang, Xu 2020 · Douze et al. 2024 (FAISS, arXiv:2401.08281) · documentación de TEI, vLLM, Qdrant y pgvector.

## Enlaces
Anterior: [17 · Interpretabilidad y geometría](../17_interpretabilidad_geometria/) · Siguiente: [19 · Playbook de élite](../19_playbook_elite/)

*Notebooks generados con `python tokenization-embeddings-course/_tools/builders/build_18.py` (desde la raíz del repo).*
