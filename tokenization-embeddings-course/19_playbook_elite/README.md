# Módulo 19 · Playbook de élite: decisiones, trampas y revisión

**Nivel:** 🔴 Experto · **Duración:** ≈ 4 h (lección ≈ 2.5 h + proyecto ≈ 1.5 h) · **Cómputo:** CPU (0 unidades de Colab)

| Archivo | Contenido |
|---|---|
| [`19_playbook_elite.ipynb`](19_playbook_elite.ipynb) | Lección: **árboles de decisión ejecutables** (tokenizer, embedder, índice, híbrido) con el umbral Flat→HNSW **medido** con FAISS · **cuatro trampas de evaluación reproducidas** (tuning en test vs CV, *winner's curse*, dependencia del golden set, sesgo de *pooling*) · **gap offline/online** (mezcla de tráfico, interfaz top-3, modelo de clic) · **calculadora de costes a escala** (1 M–1 B docs, float32/int8/binario) · **fallos reales documentados** + galería de 4 fallos silenciosos reproducidos (truncado, producto punto sin normalizar, tildes índice≠query, caché sin versión) · **linter de PRs** · cultura de equipos top |
| [`19_proyecto_playbook_elite.ipynb`](19_proyecto_playbook_elite.ipynb) | Proyecto: **3 casos de system design** (documentación global, código interno con permisos, PDFs escaneados de salud) con plantilla estructurada, rúbrica automática de 100 puntos (capacidad, restricciones, requisitos, evaluación/operación), revisión de una propuesta con errores, TODOs, pistas 🪜 y soluciones de referencia tras ⛔ SPOILER |
| `assets/` | Recursos de Gemini: `M19-IMG-01.png`, `M19-IMG-02.png`, `M19-IMG-03.png` |

Este módulo produce también [`extras/GUIA_ENTREVISTAS.md`](../extras/GUIA_ENTREVISTAS.md) (preguntas de tokenización, embeddings y system design con respuestas modelo y rúbrica) y [`extras/LECTURA_PAPERS.md`](../extras/LECTURA_PAPERS.md) (lectura guiada por módulo).

## Objetivos
1. Codificar y justificar con mediciones árboles de decisión de tokenizer, embedder, índice e híbrido.
2. Reproducir y cuantificar trampas de evaluación.
3. Explicar y recalcular el gap offline/online.
4. Estimar costes de retrieval a escala con supuestos explícitos.
5. Diagnosticar fallos reales y silenciosos; revisar PRs con una checklist ejecutable.
6. Resolver casos de system design con números y defenderlos frente a una rúbrica.

## Datos
Corpus Políglota canónico (`carga_corpus`, módulo 00; sintético + stdlib sin red), mini golden set de paráfrasis (módulo 13), vectores gaussianos para la medición de índices. El proyecto no usa datos: son especificaciones.

## Estado de pruebas (entorno de autoría, oct-2026)
Lección (≈ 1.5 min) y proyecto (< 10 s) ejecutados completos con `nbclient` en CPU, con corpus **sintético** y embedders **fallback** (Hugging Face bloqueado). Las cifras de la lección (trampas, gap, fallos) salen de esa ejecución; con un embedder neuronal real cambian los valores (en especial T3, donde el fallback es léxico) y la lección lo advierte. Precios de infraestructura del módulo: **supuestos** marcados; precio de API verificado (oct-2026).

## Lecturas
Thakur et al. 2021 (BEIR) · Cormack et al. 2009 (RRF) · Bruch et al. 2022 (fusión) · Nogueira & Cho 2019 · Weller et al. 2025 (LIMIT) · Thomas et al. 2023 / Soboroff 2024 (LLM-as-judge) · Smucker et al. 2007 · Land & Bartolo 2024 · Singh & Strouse 2024 · Petrov et al. 2023 · Boucher & Anderson 2021 · Liu et al. 2023 (*Lost in the Middle*) · Patel et al. 2024 (ACORN) · Chapelle et al. 2012 · Kohavi et al. 2020.

## Enlaces
Anterior: [18 · Producción](../18_produccion/) · Siguiente: [20 · Capstone: Políglota completo](../20_capstone/)

*Notebooks generados con `python tokenization-embeddings-course/_tools/builders/build_19.py` (desde la raíz del repo).*
