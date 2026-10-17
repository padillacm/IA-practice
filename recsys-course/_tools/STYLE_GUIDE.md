# Guía de estilo del curso «Sistemas de Recomendación: de cero a nivel Netflix»

Documento común para todos los autores (humanos o agentes). Lo que dice aquí manda.

## Alumno objetivo
- Sabe **machine learning** (regresión, árboles, gradient boosting, redes neuronales, PyTorch básico), **MLOps** (MLflow, Docker, CI/CD, pipelines) y **agentes LLM** (LangChain/LangGraph).
- **No sabe nada de sistemas de recomendación.** Cada concepto de recsys se explica desde cero, apoyándose en analogías con lo que ya sabe ("esto es como un clasificador binario, pero…").
- Tiene **Google Colab Pro con ~200 unidades de cómputo**: se pueden usar GPUs T4 / L4 / A100. No hay que recortar modelos por miedo al cómputo, pero cada notebook indica al inicio la GPU recomendada y una estimación de unidades.
- Todo el contenido está en **español** (términos técnicos en inglés entre paréntesis o tal cual cuando es la jerga estándar: *embedding*, *retrieval*, *ranking*, *two-tower*…).

## Estructura de cada módulo
```
recsys-course/NN_slug/
├── README.md                     # resumen del módulo, objetivos, lecturas, datasets
├── NN_slug.ipynb                 # LECCIÓN (teoría + código + gráficos)
└── NN_proyecto_slug.ipynb        # PROYECTO de la sesión
```
Se construyen con `recsys-course/_tools/nbbuild.py` desde un script
`recsys-course/_tools/builders/build_NN.py` (un script por módulo que genera ambos notebooks).
Ejecuta el script; `save()` valida JSON y sintaxis Python de cada celda.

## Plantilla de la LECCIÓN (orden de secciones)
1. **Cabecera**: badge de Colab (`nb.badge()`), título, nivel (🟢 Básico / 🟡 Intermedio / 🟠 Avanzado / 🔴 Experto), duración estimada, GPU recomendada y unidades de Colab estimadas, prerrequisitos (módulos anteriores).
2. **Objetivos de aprendizaje** (5–8 bullets, verbos medibles).
3. **Intuición primero**: por qué existe esta técnica, qué problema resuelve, analogía, y un **gráfico/diagrama** que lo explique.
4. **Teoría formal**: matemáticas en LaTeX (`$...$`, `$$...$$`) con cada símbolo explicado. Derivaciones clave paso a paso.
5. **Implementación desde cero** (NumPy/PyTorch) para entender el mecanismo.
6. **Implementación con librerías de industria** (las que realmente se usan) y comparación con la versión desde cero.
7. **Experimentos y gráficos**: curvas de entrenamiento, comparación de métricas, visualización de embeddings (t-SNE/UMAP), etc.
8. **🏭 En producción**: cómo lo usan Netflix / YouTube / Spotify / Pinterest / Meta / Amazon / TikTok / Airbnb / Uber…, con referencias reales (papers, blogs de ingeniería). Latencia, escala, trade-offs.
9. **🧠 Secretos de la élite**: 4–8 puntos que solo saben practicantes expertos (trampas de evaluación, trucos que mueven métricas, por qué lo que funciona en papers falla en producción, etc.). Deben ser concretos y verificables, citando la fuente cuando exista.
10. **⚠️ Errores comunes** (pitfalls).
11. **Autoevaluación**: 5–8 preguntas (con respuestas ocultas en `<details><summary>Respuesta</summary>…</details>`).
12. **Referencias**: papers (autor, año, título, enlace arXiv/ACM), blogs de ingeniería, librerías, videos. Solo referencias que existan de verdad — si no estás seguro de una URL, verifícala con WebSearch/WebFetch o cita solo autor+año+título.

## Plantilla del PROYECTO
1. Cabecera (badge, nivel, duración, GPU).
2. **Contexto de negocio** realista (ej.: "Eres ML engineer en una plataforma de streaming…").
3. **Dataset** (real, descargable desde Colab) + descripción.
4. **Entregables y criterios de evaluación** (rúbrica con métricas objetivo, p. ej. "NDCG@10 ≥ 0,30 en el split temporal").
5. **Plantilla con TODOs** paso a paso (celdas con `# TODO` y `raise NotImplementedError` o `...`), con pistas.
6. **Solución de referencia** al final, precedida de una celda markdown de aviso «⛔ SPOILER — intenta resolverlo primero». La solución debe ser completa y ejecutable.
7. **Retos extra** (stretch goals) para nivel experto.
8. Reflexión: preguntas que conectan con producción/MLOps.

Los proyectos van encadenados cuando tenga sentido: el alumno va construyendo una plataforma ("**CineMatch**", recomendador de películas/series estilo Netflix) que en el capstone se integra entera. Se pueden usar otros dominios (e-commerce, noticias, música, ads) cuando la técnica lo pida, pero menciona cómo se conecta con CineMatch.

## Código
- **Ejecutable en Colab tal cual**, de arriba a abajo. Primera celda de código: `!pip install -q ...` con versiones razonables (no fijes versiones exactas salvo que sea necesario por compatibilidad conocida; si fijas, explica por qué).
- Fija semillas (`seed = 42`). Detecta GPU: `device = "cuda" if torch.cuda.is_available() else "cpu"`.
- Descarga de datos robusta: URL oficial (GroupLens, HuggingFace Datasets, Kaggle API con instrucciones, RecBole, Zenodo…). Si un dataset requiere credenciales (Kaggle), explica cómo configurarlas y ofrece un **fallback** (subconjunto público o datos sintéticos) para que el notebook nunca se quede bloqueado.
- Escala: incluye un flag `FAST_DEV_RUN = True/False` o `SCALE = "small" | "full"` para iterar rápido y luego correr a escala completa en GPU.
- Código limpio, con funciones reutilizables, comentarios en español donde aporten, type hints ligeros.
- Celdas de código cortas–medias (≤ ~60 líneas). Mucho texto explicativo entre celdas.
- Nada de pseudo-código en celdas de código: todo debe ser Python válido.

## Gráficos (obligatorios)
- Cada lección tiene **al menos 6 visualizaciones**: diagramas conceptuales + gráficos de datos/resultados.
- Diagramas conceptuales (arquitecturas, flujos, matrices) dibujados **en celdas de código** con `matplotlib` (patches, flechas, `annotate`) o `graphviz` (preinstalado en Colab), para que se rendericen en Colab sin imágenes externas. Ejemplo: matriz usuario×ítem dispersa, pipeline retrieval→ranking→re-ranking, arquitectura two-tower, atención causal de SASRec.
- Gráficos de datos con `matplotlib`/`seaborn`/`plotly`. Títulos, ejes y leyendas en español.
- Además se permiten diagramas ASCII sencillos dentro del markdown.

## Tono pedagógico
- Ir de lo concreto a lo abstracto: ejemplo con 5 usuarios × 6 películas en papel → fórmula → código → escala real.
- Explicar el "por qué" y el "cuándo NO usar esto".
- Conectar siempre con lo que el alumno ya sabe de ML, MLOps y agentes.
- Cajas destacadas con emojis consistentes: 💡 Intuición · 📐 Matemáticas · 🏭 En producción · 🧠 Secretos de la élite · ⚠️ Cuidado · 🧪 Experimento · 📚 Para profundizar.

## Calidad
- Exactitud técnica por encima de todo. Si una cifra o afirmación de industria no la puedes respaldar, no la pongas.
- Investiga (WebSearch/WebFetch) papers y blogs recientes (2023–2026) para que el contenido de estado del arte sea actual.
- Ejecuta el builder y corrige hasta que `save()` dé OK. Si puedes, prueba localmente los fragmentos críticos (NumPy/pandas/sklearn/matplotlib están instalados en el entorno) — no hay GPU ni hace falta descargar datasets enormes.
