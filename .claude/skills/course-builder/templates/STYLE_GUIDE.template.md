# Guía de estilo del curso «{TÍTULO}»

Documento común para todos los autores (humanos o agentes). Lo que dice aquí manda.

## Alumno objetivo
- Sabe: {PRERREQUISITOS QUE DOMINA (de COURSE_SPEC)}.
- Del tema sabe: {NIVEL INICIAL}. Cada concepto nuevo se explica desde cero, apoyándose en analogías explícitas con lo que ya sabe.
- Cómputo: {RECURSOS}. Cada notebook indica al inicio la GPU recomendada y una estimación de unidades/coste.
- Idioma: {IDIOMA} (jerga técnica estándar en inglés cuando sea lo habitual).

## Estructura de cada módulo
```
{RUTA}/NN_slug/
├── README.md                     # resumen del módulo, objetivos, lecturas, datasets
├── NN_slug.ipynb                 # LECCIÓN (teoría + código + gráficos)
└── NN_proyecto_slug.ipynb        # PROYECTO de la sesión
```
Se construyen con `{RUTA}/_tools/nbbuild.py` desde un script
`{RUTA}/_tools/builders/build_NN.py` (un script por módulo que genera ambos notebooks).
Ejecuta el script; `save()` valida JSON y sintaxis Python de cada celda.

## Plantilla de la LECCIÓN (orden de secciones)
1. **Cabecera**: badge de Colab (`nb.badge()`), título, nivel (🟢 Básico / 🟡 Intermedio / 🟠 Avanzado / 🔴 Experto), duración estimada, GPU recomendada y unidades de Colab estimadas, prerrequisitos (módulos anteriores).
2. **Objetivos de aprendizaje** (5–8 bullets, verbos medibles de Bloom).
2b. **🔁 Conexión con módulos anteriores** (desde el módulo 01): 2–4 preguntas de recuperación con respuesta oculta sobre lo previo que este módulo necesita.
3. **Intuición primero**: por qué existe esta técnica, qué problema resuelve, analogía, y un **gráfico/diagrama** que lo explique.
4. **Teoría formal**: matemáticas en LaTeX (`$...$`, `$$...$$`) con cada símbolo explicado. Derivaciones clave paso a paso.
5. **Implementación desde cero** (NumPy/PyTorch) para entender el mecanismo.
6. **Implementación con librerías de industria** (las que realmente se usan) y comparación con la versión desde cero.
7. **Experimentos y gráficos**: curvas de entrenamiento, comparación de métricas, visualización de embeddings (t-SNE/UMAP), etc.
8. **🏭 En producción**: cómo lo usan {EMPRESAS REFERENTES DEL TEMA}, con referencias reales (papers, blogs de ingeniería, docs). Escala, costes, trade-offs.
9. **🧠 Secretos de la élite**: 4–8 puntos que solo saben practicantes expertos (trampas de evaluación, trucos que mueven métricas, por qué lo que funciona en papers falla en producción, etc.). Deben ser concretos y verificables, citando la fuente cuando exista.
10. **⚠️ Errores comunes** (pitfalls).
11. **Autoevaluación**: 5–8 preguntas con respuestas ocultas en `<details>`; al menos 2 marcadas **(Cálculo)/(Diagnóstico)/(Transferencia)**, no solo de recuerdo.
12. **Referencias**: papers (autor, año, título, enlace arXiv/ACM), blogs de ingeniería, librerías, videos. Solo referencias que existan de verdad — si no estás seguro de una URL, verifícala con WebSearch/WebFetch o cita solo autor+año+título.

## Plantilla del PROYECTO
1. Cabecera (badge, nivel, duración, GPU).
2. **Contexto de negocio** realista (ej.: "Eres {ROL} en {EMPRESA FICTICIA DEL HILO CONDUCTOR}…").
3. **Dataset** (real, descargable desde Colab) + descripción.
4. **Entregables y criterios de evaluación** (rúbrica con métricas objetivo y umbrales numéricos, p. ej. "{MÉTRICA} ≥ {VALOR MEDIDO POR LA SOLUCIÓN} en {SPLIT}").
5. **Plantilla con TODOs** paso a paso (celdas con `# TODO` y `raise NotImplementedError` envueltas para que «ejecutar todo» no se rompa), con **pistas graduadas plegadas** (🪜 Pista 1 orienta la idea; 🪜 Pista 2 casi da la API) en los TODOs difíciles. No pidas nada que la lección (o una anterior) no haya enseñado.
6. **Solución de referencia** al final, precedida de una celda markdown de aviso «⛔ SPOILER — intenta resolverlo primero». La solución debe ser completa y ejecutable.
7. **Retos extra** (stretch goals) para nivel experto.
8. Reflexión: preguntas que conectan con producción y con el hilo conductor.

Los proyectos van encadenados cuando tenga sentido: el alumno va construyendo **{HILO CONDUCTOR}**, que en el capstone se integra entero. Se pueden usar otros dominios cuando la técnica lo pida, pero menciona cómo se conecta con el hilo conductor.

## Código
- **Ejecutable en Colab tal cual**, de arriba a abajo. Primera celda de código: `!pip install -q ...` con versiones razonables (no fijes versiones exactas salvo que sea necesario por compatibilidad conocida; si fijas, explica por qué).
- Fija semillas (`seed = 42`). Detecta GPU: `device = "cuda" if torch.cuda.is_available() else "cpu"`.
- Descarga de datos robusta: URL oficial del dataset (repositorio del autor, Hugging Face Datasets, Kaggle API con instrucciones, Zenodo…). Si un dataset requiere credenciales (Kaggle), explica cómo configurarlas y ofrece un **fallback** (subconjunto público o datos sintéticos) para que el notebook nunca se quede bloqueado.
- Escala: incluye un flag `FAST_DEV_RUN = True/False` o `SCALE = "small" | "full"` para iterar rápido y luego correr a escala completa en GPU.
- Código limpio, con funciones reutilizables, comentarios en español donde aporten, type hints ligeros.
- Celdas de código cortas–medias (≤ ~60 líneas). Mucho texto explicativo entre celdas.
- Nada de pseudo-código en celdas de código: todo debe ser Python válido.

## Gráficos (obligatorios)
- Cada lección tiene **al menos {MÍNIMO DE GRÁFICOS} visualizaciones** (6 es un buen default): diagramas conceptuales + gráficos de datos/resultados.
- Diagramas conceptuales (arquitecturas, flujos, matrices) dibujados **en celdas de código** con `matplotlib` (patches, flechas, `annotate`) o `graphviz` (preinstalado en Colab), para que se rendericen en Colab sin imágenes externas. Ejemplos: {DIAGRAMAS CLAVE DEL TEMA: arquitecturas, pipelines, estructuras de datos}.
- Gráficos de datos con `matplotlib`/`seaborn`/`plotly`. Títulos, ejes y leyendas en el idioma del curso.
- Tras cada gráfico clave, una caja **👀 Qué debes observar** que diga qué patrón buscar y qué concluir.
- Además se permiten diagramas ASCII sencillos dentro del markdown.

## Tono pedagógico
- Ir de lo concreto a lo abstracto: ejemplo diminuto resuelto a mano ({EJEMPLO DE JUGUETE DEL TEMA}) → fórmula → código → escala real.
- Explicar el "por qué" y el "cuándo NO usar esto".
- Conectar siempre con lo que el alumno ya sabe ({ANALOGÍAS DE COURSE_SPEC}).
- Cajas destacadas con emojis consistentes: 💡 Intuición · 📐 Matemáticas · 🏭 En producción · 🧠 Secretos de la élite · ⚠️ Cuidado · 🧪 Experimento · 📚 Para profundizar.

## Módulos largos
- Si una lección supera ~7 h o ~70 celdas, marca una caja **🧭 Ruta núcleo vs ampliación** (o dos sesiones).

## Datos y rúbricas
- Cadena de descarga: URL oficial → espejo público → datos sintéticos con el mismo esquema (avisando).
- Umbrales de rúbrica calibrados con lo que **mide** la solución de referencia, nunca con lo deseado.

## Calidad
- Exactitud técnica por encima de todo. Si una cifra o afirmación de industria no la puedes respaldar, no la pongas.
- Investiga (WebSearch/WebFetch) papers y blogs de los últimos 2–3 años para que el contenido de estado del arte sea actual.
- Ejecuta el builder y corrige hasta que `save()` dé OK. Si puedes, prueba localmente los fragmentos críticos (NumPy/pandas/sklearn/matplotlib están instalados en el entorno) — no hay GPU ni hace falta descargar datasets enormes.
