# Módulo 20 · Capstone: Políglota completo

**Nivel:** 🔴 Experto · **Duración:** ≈ 6 h (lección ≈ 2.5 h + proyecto ≈ 3.5 h) · **Cómputo:** CPU en `FAST_DEV_RUN` (≈ 1 min cada notebook); T4/L4 con modelos reales

| Archivo | Contenido |
|---|---|
| [`20_capstone.ipynb`](20_capstone.ipynb) | Lección = **solución de referencia del sistema completo**: criterios de aceptación fijados antes · split dev / test ciego estratificado · tokenizer BPE byte-level (HF `tokenizers`) con fertilidad y bytes/token por idioma y prueba como analizador de BM25 · elección del analizador léxico (palabras + identificadores) · embedder (test pareado v1/v2, dimensión recortada, int8) · fusión RRF vs lineal con CV y la misma normalización que el servicio · índice HNSW vs Flat (recall/latencia con N = 20 000, RAM a 10 M) · `ServicioPoliglota` del módulo 18 con la config elegida (latencia fría/caliente, hit rate Zipf) · evaluación única en test ciego vs BM25 del módulo 00 con IC pareado y slices · **informe técnico generado** (`poliglota_informe.md`, `poliglota_config.json`) con la tabla de criterios · extensión multimodal opcional |
| [`20_proyecto_capstone.ipynb`](20_proyecto_capstone.ipynb) | Proyecto final: 6 TODOs (informe del tokenizer, decisiones solo en dev, verificación del índice, servicio, evaluación en test, informe), pistas 🪜, **rúbrica final de 100 puntos** calibrada con la solución y solución tras ⛔ SPOILER |
| `assets/` | Recursos de Gemini: `M20-IMG-01.png`, `M20-IMG-02.png`, `M20-VID-01.mp4` |

## Objetivos
1. Fijar criterios de aceptación medibles antes de construir.
2. Integrar tokenizer, analizador, embedder, fusión, índice y servicio.
3. Decidir cada componente en dev con reglas explícitas; evaluar una vez en test ciego.
4. Proyectar memoria, coste y latencia a 10 M de chunks.
5. Generar un informe técnico de decisiones desde las métricas.

## Piezas integradas (todas reutilizadas)
`carga_corpus`, métricas y BM25 (módulo 00) · BPE con HF `tokenizers` (02–03) · fertilidad y paridad (04) · embedders con fallback (12) · RRF y combinación lineal (13) · FAISS HNSW/Flat (14) · `bootstrap_ci`/`paired_bootstrap` (15) · ColPali/visual opcional (16) · `ServicioPoliglota`, caché versionada, alias (18) · árboles de decisión y trampas de evaluación (19).

## Estado de pruebas (entorno de autoría, oct-2026)
Lección (≈ 30 s) y proyecto ejecutados completos con `nbclient` en CPU con el corpus **sintético** + stdlib y los **fallbacks** TF-IDF+SVD (Hugging Face bloqueado). Con esa ejecución la regla elige v1 (la diferencia v2−v1 en dev no excluye el 0), d = 48, int8, fusión lineal y HNSW con efSearch = 128, y se cumplen los 7 criterios. **No se pudo probar:** modelos reales del hub, datos reales de Wikipedia/CodeSearchNet, GPU, la extensión multimodal con modelos reales.

## Enlaces
Anterior: [19 · Playbook de élite](../19_playbook_elite/) · Material de cierre: [`extras/GUIA_ENTREVISTAS.md`](../extras/GUIA_ENTREVISTAS.md) · [`extras/LECTURA_PAPERS.md`](../extras/LECTURA_PAPERS.md)

*Notebooks generados con `python tokenization-embeddings-course/_tools/builders/build_20.py` (desde la raíz del repo).*
