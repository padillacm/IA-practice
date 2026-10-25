# Guía de estilo del curso «Tokenización y Embeddings: de BPE a los modelos modernos»

Documento común para todos los autores (humanos o agentes). Lo que dice aquí manda.

## Alumno objetivo
- Sabe: Python sólido, deep learning / PyTorch, Transformers y atención, álgebra lineal y probabilidad.
- Del tema sabe: «ha leído algo» (conoce BPE y word2vec de nombre, nunca los implementó). Cada concepto nuevo se explica desde cero, apoyándose en analogías explícitas con lo que ya sabe.
- Cómputo: Colab Pro (T4 por defecto; L4/A100 solo en módulos marcados en SYLLABUS). Cada notebook indica al inicio la GPU recomendada y una estimación de unidades/coste.
- Idioma: español con términos técnicos en inglés (jerga técnica estándar en inglés cuando sea lo habitual).

## Estructura de cada módulo
```
tokenization-embeddings-course/NN_slug/
├── README.md                     # resumen del módulo, objetivos, lecturas, datasets
├── NN_slug.ipynb                 # LECCIÓN (teoría + código + gráficos)
└── NN_proyecto_slug.ipynb        # PROYECTO de la sesión
```
Se construyen con `tokenization-embeddings-course/_tools/nbbuild.py` desde un script
`tokenization-embeddings-course/_tools/builders/build_NN.py` (un script por módulo que genera ambos notebooks).
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
8. **🏭 En producción**: cómo lo usan OpenAI, Google DeepMind, Meta FAIR, Anthropic, Cohere, Voyage, Jina, Mistral, Hugging Face, con referencias reales (papers, blogs de ingeniería, docs). Escala, costes, trade-offs.
9. **🧠 Secretos de la élite**: 4–8 puntos que solo saben practicantes expertos (trampas de evaluación, trucos que mueven métricas, por qué lo que funciona en papers falla en producción, etc.). Deben ser concretos y verificables, citando la fuente cuando exista.
10. **⚠️ Errores comunes** (pitfalls).
11. **Autoevaluación**: 5–8 preguntas con respuestas ocultas en `<details>`; al menos 2 marcadas **(Cálculo)/(Diagnóstico)/(Transferencia)**, no solo de recuerdo.
12. **Referencias**: papers (autor, año, título, enlace arXiv/ACM), blogs de ingeniería, librerías, videos. Solo referencias que existan de verdad — si no estás seguro de una URL, verifícala con WebSearch/WebFetch o cita solo autor+año+título.

## Plantilla del PROYECTO
1. Cabecera (badge, nivel, duración, GPU).
2. **Contexto de negocio** realista (ej.: "Eres ML engineer en Políglota Labs…").
3. **Dataset** (real, descargable desde Colab) + descripción.
4. **Entregables y criterios de evaluación** (rúbrica con métricas objetivo y umbrales numéricos, p. ej. "nDCG@10 ≥ el valor medido por la solución de referencia (menos un margen) en el split de test").
5. **Plantilla con TODOs** paso a paso (celdas con `# TODO` y `raise NotImplementedError` envueltas para que «ejecutar todo» no se rompa), con **pistas graduadas plegadas** (🪜 Pista 1 orienta la idea; 🪜 Pista 2 casi da la API) en los TODOs difíciles. No pidas nada que la lección (o una anterior) no haya enseñado.
6. **Solución de referencia** al final, precedida de una celda markdown de aviso «⛔ SPOILER — intenta resolverlo primero». La solución debe ser completa y ejecutable.
7. **Retos extra** (stretch goals) para nivel experto.
8. Reflexión: preguntas que conectan con producción y con el hilo conductor.

Los proyectos van encadenados cuando tenga sentido: el alumno va construyendo **Políglota (buscador semántico multilingüe ES/EN/código)**, que en el capstone se integra entero. Se pueden usar otros dominios cuando la técnica lo pida, pero menciona cómo se conecta con el hilo conductor.

## Código
- **Ejecutable en Colab tal cual**, de arriba a abajo. Primera celda de código: `!pip install -q ...` con versiones razonables (no fijes versiones exactas salvo que sea necesario por compatibilidad conocida; si fijas, explica por qué).
- Fija semillas (`seed = 42`). Detecta GPU: `device = "cuda" if torch.cuda.is_available() else "cpu"`.
- Descarga de datos robusta: URL oficial del dataset (repositorio del autor, Hugging Face Datasets, Kaggle API con instrucciones, Zenodo…). Si un dataset requiere credenciales (Kaggle), explica cómo configurarlas y ofrece un **fallback** (subconjunto público o datos sintéticos) para que el notebook nunca se quede bloqueado.
- Escala: incluye un flag `FAST_DEV_RUN = True/False` o `SCALE = "small" | "full"` para iterar rápido y luego correr a escala completa en GPU.
- Código limpio, con funciones reutilizables, comentarios en español donde aporten, type hints ligeros.
- Celdas de código cortas–medias (≤ ~60 líneas). Mucho texto explicativo entre celdas.
- Nada de pseudo-código en celdas de código: todo debe ser Python válido.

## Visuales (obligatorios) y celdas Gemini

Cada lección tiene **al menos 8 visuales**:
- **≥ 3 celdas Gemini** (🎨 imagen / 🎬 video) que el usuario reemplazará por un recurso generado con Gemini. Úsalas para lo que gana como imagen o animación: diagramas conceptuales de arquitectura, metáforas visuales, procesos paso a paso (merges de BPE, patching por entropía, recorrido HNSW, MaxSim de ColBERT, estructura de un embedder contrastivo…). Mínimo **2 imágenes**, y **≥ 1 video** en los módulos donde hay un proceso dinámico (02, 06, 07, 11, 13, 14 como mínimo; en el resto, si aporta).
- **≥ 5 gráficos generados en código** (matplotlib/seaborn/plotly/graphviz): datos reales, curvas, heatmaps, distribuciones, proyecciones UMAP/t-SNE, comparativas. Los resultados con datos NUNCA van en celdas Gemini.
- Además se permiten diagramas ASCII sencillos dentro del markdown.
- Tras cada gráfico clave (de código o Gemini), una caja **👀 Qué debes observar** que diga qué patrón buscar y qué concluir.
- Títulos, ejes y leyendas de los gráficos en español.

### Cómo se escribe una celda Gemini (OBLIGATORIO: usa `nb.gemini(...)` de `nbbuild.py`)
```python
nb.gemini(
    "imagen",                       # "imagen" | "video"
    "M02-IMG-01",                   # ID único: M<NN>-IMG-<k> / M<NN>-VID-<k> (NN = número de tu módulo)
    "Cómo BPE fusiona pares",       # título corto
    "Qué muestra y por qué está en la lección",
    """Prompt COMPLETO y autocontenido para Gemini ...""",   # ver reglas abajo
    "Texto alternativo descriptivo",
    "placeholder ASCII/texto visible mientras no se reemplace",
    fmt="PNG 16:9, 1920x1080",     # opcional
    duration="20-30 s",             # solo video
)
```
Reglas del **prompt** (el usuario lo copia y pega en Gemini sin editar):
1. Autocontenido: no referencies «el notebook» ni «la figura anterior»; Gemini no tiene tu contexto.
2. Estilo visual consistente en todo el curso: *diagrama técnico limpio, fondo blanco/claro, paleta sobria (azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280), tipografía sans-serif legible, flechas claras, sin ilustraciones decorativas ni texto inventado*.
3. Escribe **literalmente** todos los textos/etiquetas que deben aparecer en la imagen (en español, términos técnicos en inglés) y la composición (izquierda→derecha, capas, colores por rol).
4. Para video: guion **por escenas** con duración aproximada de cada una (p. ej. «0–5 s: …»), qué entra/sale, texto en pantalla, sin voz en off salvo que se pida, 16:9, ritmo calmado.
5. Si el contenido tiene datos numéricos, dalos exactos (Gemini no debe inventarlos).
6. Termina con una línea «Evita: …» con los errores típicos a evitar (texto ilegible, flechas ambiguas, elementos decorativos).

El **placeholder** debe ser útil por sí solo (diagrama ASCII o descripción) para que la lección se entienda aunque el usuario aún no haya generado la imagen. La caja «👀 Qué debes observar» va **después** de la celda Gemini y debe tener sentido con el recurso ya insertado.
Los IDs se indexan con `python tokenization-embeddings-course/_tools/gen_gemini_index.py` (genera `extras/GEMINI_ASSETS.md`).
Crea (vacía, con `.gitkeep`) la carpeta `NN_slug/assets/` del módulo.

## Etiquetas de madurez (obligatorio en cada lección)
Estado del arte hasta **octubre 2026**. Cada lección incluye una tabla **Mapa de madurez**: técnica → 🟢 sólido / 🟡 emergente / 🔴 experimental → quién la usa (modelo/empresa, solo si lo puedes respaldar) → fuente. Fecha toda cifra sujeta a cambio ("a oct-2026") y no pongas ninguna que no hayas verificado.

## Tono pedagógico
- Ir de lo concreto a lo abstracto: ejemplo diminuto resuelto a mano (un corpus de 5 palabras tokenizado a mano, un espacio de 2 dimensiones con 4 vectores) → fórmula → código → escala real.
- Explicar el "por qué" y el "cuándo NO usar esto".
- Conectar siempre con lo que el alumno ya sabe (compresión de datos, búsqueda/IR y recsys, lingüística).
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
