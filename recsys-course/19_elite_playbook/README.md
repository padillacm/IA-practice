# Módulo 19 · Masterclass: lo que separa a un ingeniero top de recomendación

**Nivel:** 🔴 Experto · **Duración:** 7–9 h (lección) + 6–10 h (proyecto) · **GPU:** opcional (T4 acelera §1 y §7; todo corre en CPU con `FAST_DEV_RUN=True`) · **Unidades Colab:** 1–4

**Prerrequisitos:** 06, 07, 08, 13, 14, 15, 16, 17 y 18.

## Resumen
El módulo 18 reúne un compendio de 38 secretos de élite. Este módulo coge los que allí solo se mencionan y los
**implementa en miniatura**, los **mide** con simulaciones de verdad conocida y enseña a **depurarlos** en producción:

1. **Tablas de embeddings a escala**: memoria y estado del optimizador (Adagrad por filas), colisiones de hashing
   ponderadas por tráfico (cabeza vs cola), IDs estructurados, *double hashing*, **QR embeddings**, **mixed-dimension**,
   **TT-Rec**, híbrido por frecuencia, cuantización **fp16/fp8/int8/int4 por fila vs por tabla**, *one-epoch phenomenon*.
2. **Entrenamiento en tiempo real** (Monolith): tabla sin colisiones con filtro de frecuencia y expiración, estático vs
   diario vs online, **intervalo de sincronización**, *catastrophic forgetting* y *replay*.
3. **Label delay** (modelo de Chapelle ajustado en PyTorch), ventanas de atribución, **fugas de ventana inclusiva** en
   contadores en tiempo real, lag de streaming y **skew report con log-and-wait** (por qué el PSI no lo ve).
4. **Exposure bias** (IPS y positividad), **candidate-set mismatch** y paradoja de Berkson entre etapas, **consistencia
   del funnel** y distilación del ranker final al pre-ranker.
5. **Verdad a largo plazo**: clickbait vs satisfacción con retención simulada, Goodhart y *value models*, encuestas
   como etiquetas (sesgo de respuesta), tamaño de holdouts globales.
6. **Casebook** de 10 incidentes «offline ↑ online ↓», árbol de triaje, *golden queries* para versiones de embeddings y
   análisis de novedad por antigüedad de exposición.
7. **Rendimiento**: presupuesto de latencia, *dynamic batching* (simulación de eventos), *hedged requests*, caché de
   usuario con invalidación por evento, cuantización del ranker, retrieval por fuerza bruta en GPU, *capacity planning*.
8. **Cultura**: experimentación al estilo Netflix, árbol de métricas, linter de *experiment docs*, plantilla de *design
   doc* y señales de seniority.

## Contenido
| Archivo | Qué es |
|---|---|
| `19_elite_playbook.ipynb` | Lección (≥ 25 gráficos, todo ejecutable en CPU con `FAST_DEV_RUN=True`) |
| `19_proyecto_debugging_produccion.ipynb` | Proyecto «pager duty»: CineMatch v2 con 6 bugs plantados (caché stale con versión de embeddings, skew de unidades, fuga en contadores, colisiones de hashing, label delay, candidate mismatch). Herramientas de diagnóstico con TODOs, cuantificación por ablación, *scorecard*, *postmortem* y solución ⛔ SPOILER |

## Datasets
- **Lección**: simulaciones con verdad conocida (no descarga nada).
- **Proyecto**: **MovieLens-100K** (GroupLens) como base de un gemelo digital de usuarios; *fallback* sintético sin red.

## Lecturas clave
- Liu et al. (2022) *Monolith* · Shi et al. (2020) *QR embeddings* · Ginart et al. (2019) *Mixed Dimension Embeddings* · Yin et al. (2021) *TT-Rec* · Guan et al. (2019) *4-bit embedding quantization*.
- Chapelle (2014) *Delayed Feedback* · Ktena et al. (2019) · Zinkevich, *Rules of ML*.
- Schnabel et al. (2016) · Qin et al. (2022) *RankFlow* · Zheng et al. (2024) *Full Stage LTR* · Wang et al. (2023, Meta) *ranking consistency*.
- Hohnhold et al. (2015) *Focusing on the Long-term* · YouTube (2021) *valued watchtime* · Tingley et al. (2021) *Decision Making at Netflix*.
- Dean & Barroso (2013) *The Tail at Scale* · Gupta et al. (2020) *DeepRecSys*.

## Conexión con CineMatch
El proyecto es el «día 2» del capstone (módulo 18): el sistema ya está en producción y falla. Las herramientas que
construyes (cache audit, skew report, time-travel audit, hash audit, curva de maduración, adversarial validation) son
los *gates* que deberías añadir al pipeline de los módulos 16 y 17.

Los notebooks se generan con `python recsys-course/_tools/builders/build_19.py` (desde la raíz del repo).
