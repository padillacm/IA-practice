# Progreso: revisor-consistencia-B
Agente: Consistencia y lenguaje + celdas Gemini · Módulos: 09–20 + extras · Informe: tokenization-embeddings-course/_tools/REVISION_CONSISTENCIA.md (sección Bloque B)
- [x] 20_capstone
- [x] 19_playbook_elite
- [x] 18_produccion
- [x] 17_interpretabilidad_geometria
- [x] 16_embeddings_multimodales
- [x] 15_evaluacion_retrieval
- [x] 14_indexacion_ann
- [x] 13_dense_sparse_late_interaction
- [x] 12_embedders_modernos
- [x] 11_aprendizaje_contrastivo
- [x] 10_embeddings_contextuales_oraciones
- [ ] 09_capa_embedding_llm
- [ ] extras (GUIA_ENTREVISTAS, LECTURA_PAPERS), README del curso y GUIA_DE_ESTUDIO coherentes
- [ ] regenerar extras/GEMINI_ASSETS.md + check_course.py OK + informe

## Notas para retomar
- Convención B: cabecera en tabla (Nivel · Duración estimada · GPU recomendada · Prerrequisitos) + subtítulo del curso; proyectos con las mismas etiquetas. Encabezados: «## N. Título»; secciones fijas sin número y con emoji (🎯 Objetivos · 🔁 · 🗺️ Mapa de madurez · 🏭 · 🧠 · ⚠️ · 📝 Autoevaluación · 📚 Referencias). IDs Gemini con 2 dígitos (M15-IMG-01).
- M20: cabecera en tabla; VID-01 con listas y puntuaciones RRF exactas + sin música; IMG-01 sin «int8» fijo; IMG-02 con los 7 criterios reales.
- M19: cabecera en tabla; IDs IMG-02/03 renumerados por orden de aparición; árbol M19-IMG-01 alineado con elige_indice (70 % de RAM, grafo + vectores en SSD); T2 sin rojo.
- M16 (adelantado: élite B saltó 18/17 y los dejó para el final): etiquetas canónicas + subtítulo; secciones fijas sin número, ✅→📝; IDs a 2 dígitos; «mapa de calor en 6.2» (decía 6.3); IMG-03 ≈ 258 KiB/página (1030×128×2 B); flecha negra → gris.
- M15: etiquetas canónicas + subtítulo; secciones fijas sin número, ✅→📝; IDs a 2 dígitos y en orden (golden set = IMG-02, LIMIT = IMG-03); VID-01: remuestreos con listas cuyas medias son exactas (el de 0.61 daba 0.69) e IC ≈ [0.35, 0.77] recalculado (decía [0.37, 0.74]); producto punto → producto escalar.
- M14: cabecera inline → tabla canónica (lección y proyecto) + subtítulo; «## N ·» → «## N.»; secciones fijas sin número, 📝/📚; «sin voz en off, sin música»; re-ranking/re-ordenar → reranking/reordenar. Gemini 3 IMG + 1 VID correctas (PQ: 1024/64 → 64 B, 64× menos que float32).
- M18: cabecera inline → tabla canónica + subtítulo; IMG-02: lote 2 no podía cerrarse por max_batch = 32 con 2 peticiones → ejemplo con max_batch = 4 y q1–q7; IMG-01 sin «p99 ≤ 100 ms» inventado; VID-01 sin música; «Costo» → «Coste» en la salida.
- M17: etiquetas canónicas + subtítulo; secciones fijas sin número, 📝; IDs renumerados por orden de aparición (IMG-01 capas de información, VID-01 steering, IMG-02 superposición, IMG-03 SAE); 👀 añadido tras VID-01 (faltaba); SAE de la figura con 96 latentes como §7 (decía 256); colores fuera de paleta (negro, rojo) sustituidos.
- M13: cabecera inline → tabla (lección y proyecto) + subtítulo; «N ·» → «N.»; fijas canónicas; 👀 añadido tras M13-IMG-04 (faltaba); VID-01 MaxSim 0.82+0.91+0.78 = 2.51 verificado, «sin música»; SPLADE con alturas «ilustrativas»; re-score → rescoring; costo → coste; producto punto → producto escalar.
- M12: cabecera inline → tabla (lección y proyecto) + subtítulo; «N ·» → «N.»; fijas canónicas; IMG-03: los enteros int8 no salían de ninguna regla → recalculados con [lo, hi] = [-0.5, 0.5] (mismo esquema que el ✍️ de §5: 0.12 → 30), con el recorte de 0.64; VID-01 rankings marcados ilustrativos, sin música; vídeo → video; producto punto → producto escalar; negativos difíciles → negativos duros.
- M11: etiquetas canónicas (Cómputo → GPU recomendada, Requisitos → Prerrequisitos) + subtítulo; encabezados con emoji (🎯/🗺️/📝/📚); VID-01: softmax, pérdidas y medias recalculadas (0.20 y 1.08 correctas), «sin música»; IMG-03 sin rojo fuera de paleta; negativos difíciles → negativos duros; sans-serif en IMG-02/03.
- M10: etiquetas canónicas + subtítulo; encabezados con emoji; IMG-03/04 con la paleta completa y sans-serif; candado decorativo → línea «pesos compartidos»; re-rankear/re-ranking → rerankear/reranking (también restos en 14).
