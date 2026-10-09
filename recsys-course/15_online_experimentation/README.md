# Módulo 15 · Experimentación online para sistemas de recomendación

**Nivel:** 🟠 Avanzado → 🔴 Experto · **Duración:** 5–6 h (lección) + 4 h (proyecto) · **Hardware:** CPU de Colab (sin GPU), < 1 unidad

En Netflix, Spotify o Booking, lo que decide un lanzamiento no es ninguna métrica offline (módulo 02) ni ninguna OPE (módulo 14): es un **experimento controlado online**. Este módulo enseña a diseñarlo (unidad de aleatorización, potencia, MDE), a analizarlo sin engañarse (método delta, SRM, CUPED, peeking) y a resolver los problemas propios de recomendación: comparar rankers con muchos menos usuarios (**interleaving**), efectos que cambian con el tiempo (novelty/primacy), interferencia en marketplaces, efectos a largo plazo (**surrogate index**), heterogeneidad y cuasi-experimentos.

| Notebook | Contenido |
|---|---|
| [`15_online_experimentation.ipynb`](15_online_experimentation.ipynb) | Lección: resultados potenciales y distribuciones reales de engagement; unidad de aleatorización, método delta y SRM con A/A tests; power analysis y MDE (fórmula y `statsmodels`); CUPED/CUPAC; métricas north-star/proxy/guardrail; novelty y primacy; Team Draft Interleaving y su sensibilidad frente a A/B; peeking, O'Brien–Fleming y mSPRT; interferencia en marketplaces (usuario vs clúster); surrogate index; HTE con T-learner; diff-in-diff; herramientas (statsmodels, SciPy, GrowthBook, Eppo, Statsig, Spotify Confidence). Todo con simulaciones y gráficos. |
| [`15_proyecto_ab_interleaving.ipynb`](15_proyecto_ab_interleaving.ipynb) | Proyecto: simulador de A/B + interleaving para la fila "Top 10 para ti" de **CineMatch**, construido sobre MovieLens-100K. Power analysis, asignación por hash y SRM, análisis con método delta, CUPED, Team Draft Interleaving, curvas de sensibilidad por *bootstrap subsampling*, estudio de peeking con mSPRT y memo de decisión. Plantilla con TODOs y solución de referencia. |

## 🎯 Objetivos

1. Diseñar un A/B para un recomendador: unidad, métrica principal, guardrails, n y MDE.
2. Analizar métricas de ratio con el método delta y detectar SRM.
3. Reducir la varianza con CUPED/CUPAC.
4. Implementar Team Draft Interleaving y medir su sensibilidad (Netflix, 2017).
5. Corregir el peeking con tests secuenciales.
6. Diagnosticar novelty/primacy, interferencia y efectos a largo plazo (surrogate index).
7. Estimar HTE y aplicar diff-in-diff.

## 📦 Datos

- **Lección:** simulaciones con verdad conocida (horas vistas con ceros y cola larga, CTR por usuario, marketplaces con oferta limitada, retención…). No hace falta descargar nada.
- **Proyecto:** **MovieLens-100K** (GroupLens, `files.grouplens.org`), del que se extraen factores latentes y actividad para simular una población de usuarios "gemelos". Si no hay red, se usan ratings sintéticos con la misma forma.

## 🔗 Conexión con CineMatch

El proyecto 14 decide con OPE qué política llega al A/B; este módulo diseña y analiza ese A/B. El proceso en dos fases (interleaving para podar y A/B para decidir), la asignación por hash y las alertas de SRM/guardrails se integran en la plataforma de los módulos **16** (serving) y **17** (monitoreo).

## 📚 Lecturas esenciales

- Kohavi, Tang & Xu (2020). *Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing.* Cambridge University Press.
- Deng, Xu, Kohavi & Walker (2013). *Improving the Sensitivity of Online Controlled Experiments by Utilizing Pre-Experiment Data* (CUPED). WSDM.
- Parks, Aurisset & Ramm (2017). *Innovating Faster on Personalization Algorithms at Netflix Using Interleaving.* Netflix TechBlog.
- Johari, Koomen, Pekelis & Walsh (2017). *Peeking at A/B Tests.* KDD · [arXiv:1512.04922](https://arxiv.org/abs/1512.04922) (*Always Valid Inference*).
- Athey, Chetty, Imbens & Kang (2019/2025). *The Surrogate Index.* [arXiv:1603.09326](https://arxiv.org/abs/1603.09326) · Zhang et al. (2023), *200 A/B tests at Netflix*, [arXiv:2311.11922](https://arxiv.org/abs/2311.11922)
- Johari, Li, Liskovich & Weintraub (2022). *Experimental Design in Two-Sided Platforms.* [arXiv:2002.05670](https://arxiv.org/abs/2002.05670)
- Schultzberg & Ankargren (2023). *Choosing a Sequential Testing Framework.* Spotify Engineering.

Prerrequisitos: módulos 02, 13 y 14. Siguiente: **16 · Producción y serving**.
