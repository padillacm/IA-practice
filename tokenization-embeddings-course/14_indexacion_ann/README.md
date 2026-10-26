# Módulo 14 · Indexación y búsqueda aproximada de vecinos (ANN)

**Nivel:** 🟠 Avanzado · **Duración:** ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) · **GPU:** no necesaria (CPU)

Con 10 M de fragmentos la búsqueda exacta cuesta decenas de GB de lecturas por consulta. Este módulo enseña a **medir** un índice (neighbor recall,
latencia p50/p99 con batch=1, memoria real) y construye desde cero los algoritmos que lo hacen posible: **IVF**, **PQ/OPQ**, un **mini-HNSW**
(con visualización de capas), **Vamana/DiskANN**, la idea de **ScaNN**, **RaBitQ** (estimador insesgado, error ∝ 1/√D) y **búsqueda filtrada**; después
usa **FAISS** en serio (barrido, frontera de Pareto y elección con un SLA).

> Puente con recsys: [`recsys-course/08_deep_retrieval_ann`](../../recsys-course/08_deep_retrieval_ann/README.md) cubre el uso de FAISS con un *two-tower*; aquí se construyen los algoritmos y se añaden grafos en disco, cuantización con garantías y filtros. La operación de bases vectoriales va en el módulo 18.

## Contenido
| Notebook | Qué hay dentro |
|---|---|
| [`14_indexacion_ann.ipynb`](14_indexacion_ann.ipynb) | Lección: fuerza bruta y protocolo de medición · IVF desde cero · PQ/OPQ desde cero (ADC, refine) · mini-HNSW + capas en 2D · Vamana (RobustPrune) y modelo de I/O de DiskANN · ScaNN (pérdida anisótropa) · mini-RaBitQ · filtros (pre/post/en grafo) · barrido FAISS con SLA · sensibilidad al dataset · 🏭 producción · 🧠 secretos · autoevaluación |
| [`14_proyecto_indexacion_ann.ipynb`](14_proyecto_indexacion_ann.ipynb) | Proyecto: índice de Políglota con curvas recall@10 vs latencia vs memoria; frontera de Pareto en 3 objetivos y elección bajo un SLA. Plantilla con TODOs, pistas 🪜, autocomprobación y solución tras ⛔ SPOILER |

## Objetivos
1. Medir ANN con el protocolo correcto y reconocer cuándo la fuerza bruta basta.
2. Implementar IVF, PQ/OPQ, HNSW, Vamana y RaBitQ (mini) y relacionarlos con FAISS.
3. Resolver búsqueda filtrada y razonar sobre el trade-off recall/latencia/memoria.
4. Elegir una configuración de índice que cumpla un SLA con datos propios.

## Datasets
Vectores sintéticos «tipo embedding» (mezcla de clusters con espectro decreciente) para la lección y **embeddings de Políglota** (corpus del módulo 00 con el embedder del módulo 12, ampliado con copias ruidosas) para el proyecto. Sin acceso a Hugging Face se usa el corpus sintético y un embedder de respaldo (el notebook avisa con `⚠️`).

## Lecturas clave (verificadas)
- Malkov & Yashunin, *HNSW* (1603.09320) · Guo et al., *ScaNN* (1908.10396) · Gao & Long, *RaBitQ* (2405.12497) · Douze et al., *The Faiss library* (2401.08281).
- Subramanya et al., *DiskANN* (NeurIPS 2019) · Singh et al., *FreshDiskANN* (2105.09613) · Patel et al., *ACORN* (2403.04871) · Aumüller et al., *ANN-Benchmarks* (1807.05614).

## Conexión con Políglota
Los vectores y la configuración (dimensión, precisión) vienen de los módulos 12–13; el índice elegido aquí se opera en el módulo 18 y se evalúa de extremo a extremo en el 15.

*Los notebooks se generan con `python tokenization-embeddings-course/_tools/builders/build_14.py` (desde la raíz del repo). Estado del arte a octubre de 2026.*
