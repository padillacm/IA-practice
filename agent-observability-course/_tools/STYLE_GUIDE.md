# Guía de estilo del curso «Observabilidad de agentes de IA en producción»

Documento común para todos los autores (humanos o agentes). Lo que dice aquí manda.

## Alumno objetivo
- Sabe: Python sólido.
- Del tema sabe: nada del stack (OTel, Grafana, Loki, Tempo), ni de agentes LLM, Docker o observabilidad. Cada concepto nuevo se explica desde cero, apoyándose en analogías explícitas con ML/ciencia de datos (métricas offline vs online, drift, evaluación), backend/microservicios (latencia, errores, tracing distribuido) y SRE (SLOs, alertas, on-call, runbooks).
- Cómputo: máquina local con Docker (≈8 GB de RAM libres), sin GPU. Cada notebook indica al inicio los perfiles de Compose que necesita y su consumo aproximado de RAM; no hay estimaciones de GPU ni de unidades de Colab.
- Idioma: español (jerga técnica estándar en inglés cuando sea lo habitual: span, trace, tool call, tail sampling…).

## Estructura de cada módulo
```
agent-observability-course/NN_slug/
├── README.md                     # resumen del módulo, objetivos, lecturas, servicios necesarios
├── NN_slug.ipynb                 # LECCIÓN (teoría + código + gráficos)
└── NN_proyecto_slug.ipynb        # PROYECTO de la sesión
```
Se construyen con `agent-observability-course/_tools/nbbuild.py` desde un script
`agent-observability-course/_tools/builders/build_NN.py` (un script por módulo que genera ambos notebooks).
Ejecuta el script; `save()` valida JSON y sintaxis Python de cada celda.

## Plantilla de la LECCIÓN (orden de secciones)
1. **Cabecera**: badge de Colab (`nb.badge()`, solo útil si el módulo tiene modo sin Docker), título, nivel (🟢 Básico / 🟡 Intermedio / 🟠 Avanzado / 🔴 Experto), duración estimada, servicios de Compose necesarios (perfiles) y RAM aproximada, prerrequisitos (módulos anteriores).
2. **Objetivos de aprendizaje** (5–8 bullets, verbos medibles de Bloom).
2b. **🔁 Conexión con módulos anteriores** (desde el módulo 01): 2–4 preguntas de recuperación con respuesta oculta sobre lo previo que este módulo necesita.
3. **Intuición primero**: por qué existe esta técnica, qué problema resuelve, analogía (ML / backend / SRE) y un **gráfico/diagrama** que lo explique.
4. **Teoría formal**: conceptos y modelo de datos con precisión; matemáticas en LaTeX solo cuando aplique (percentiles, burn-rate, probabilidad de muestreo, coste), con cada símbolo explicado.
5. **Implementación a mano** del mecanismo (p. ej. propagar contexto manualmente, exporter OTLP mínimo, cálculo de burn-rate) para entender qué hace el SDK por debajo.
6. **Implementación con las herramientas de industria** (SDK de OTel, Collector, Tempo/Loki/Grafana…) y comparación con la versión a mano.
7. **Experimentos y gráficos**: trazas, latencias, distribuciones de tokens/coste, comparación antes/después, con tráfico sintético de SupportOps.
8. **🏭 En producción**: cómo lo hacen Grafana Labs, Honeycomb, Datadog, Netflix, Uber u otros, con referencias reales (docs, blogs de ingeniería, specs). Escala, costes, trade-offs.
9. **🧠 Secretos de la élite**: 4–8 puntos que solo saben practicantes expertos (trampas de cardinalidad, por qué el muestreo sesga las métricas, qué no capturar en prompts, anti-patrones de alertas…). Concretos, verificables y con fuente cuando exista; explican POR QUÉ importan.
10. **⚠️ Errores comunes** (pitfalls).
11. **Autoevaluación**: 5–8 preguntas con respuestas ocultas en `<details>`; al menos 2 marcadas **(Cálculo)/(Diagnóstico)/(Transferencia)**, no solo de recuerdo.
12. **Referencias**: specs, docs, blogs de ingeniería, papers (autor, año, título, enlace). Solo referencias que existan de verdad — si no estás seguro de una URL, verifícala con WebSearch/WebFetch o cita solo autor+año+título.

## Plantilla del PROYECTO
1. Cabecera (badge, nivel, duración, servicios y RAM).
2. **Contexto de negocio** realista (ej.: "Eres ingeniero/a de plataforma en SupportOps y el agente de soporte empieza a fallar…").
3. **Datos**: tráfico sintético de SupportOps (semilla fija, esquema documentado), con la cadena stack local → modo degradado con datos pregrabados.
4. **Entregables y criterios de evaluación** (rúbrica con umbrales numéricos calibrados con lo medido por la solución, p. ej. "el 100 % de las trazas contienen `trace_id` en sus logs", "p95 de `invoke_agent` ≤ valor medido en `mock`").
5. **Plantilla con TODOs** paso a paso (celdas con `# TODO` y `raise NotImplementedError` envueltas para que «ejecutar todo» no se rompa), con **pistas graduadas plegadas** (🪜 Pista 1 orienta la idea; 🪜 Pista 2 casi da la API) en los TODOs difíciles. No pidas nada que la lección (o una anterior) no haya enseñado.
6. **Solución de referencia** al final, precedida de una celda markdown de aviso «⛔ SPOILER — intenta resolverlo primero». La solución debe ser completa y ejecutable.
7. **Retos extra** (stretch goals) para nivel experto.
8. Reflexión: preguntas que conectan con producción y con el hilo conductor.

Los proyectos están encadenados: el alumno va construyendo **SupportOps** (agente de soporte con observabilidad completa), que en el capstone se integra entero. Menciona siempre cómo se conecta el proyecto con lo hecho antes.

## Código
- **Ejecutable en Jupyter/VS Code con el kernel local**, de arriba a abajo. Primera celda de código: `%pip install -q ...` con versiones razonables (no fijes versiones exactas salvo compatibilidad conocida; si fijas, explica por qué).
- Segunda celda: `check_stack()` — comprueba qué servicios están arriba (Collector, Tempo, Loki, Prometheus, Grafana, Pyroscope según el módulo) y, si no, imprime el comando exacto de `docker compose --profile … up -d` y avisa del **modo degradado** (datos pregrabados, mismo esquema) para que el notebook nunca se quede bloqueado.
- Fija semillas (`seed = 42`). Proveedor LLM por `LLM_PROVIDER` (`mock` por defecto). **Nunca** pongas API keys en notebooks: solo variables de entorno, con instrucciones.
- Escala: incluye un flag `FAST_DEV_RUN = True/False` o `SCALE = "small" | "full"` (poco tráfico y pocas peticiones para iterar rápido).
- Configs (Collector, Tempo, Loki, Compose, Helm values): en archivos reales bajo `stack/` o dentro del módulo; el notebook los muestra y explica línea a línea. Valida con las herramientas oficiales cuando sea posible (`docker compose config`, `otelcol validate`…).
- Código limpio, funciones reutilizables, comentarios en español donde aporten, type hints ligeros.
- Celdas de código cortas–medias (≤ ~60 líneas). Mucho texto explicativo entre celdas.
- Nada de pseudo-código en celdas de código: todo debe ser Python (o YAML/shell correctamente marcado) válido.

## Gráficos (obligatorios)
- Cada lección tiene **al menos 6 visualizaciones**: diagramas conceptuales (arquitecturas, flujos de señales, pipelines del Collector, árboles de spans) + gráficos de datos/resultados (latencias, tokens, coste, tasas de error, flamegraphs simplificados).
- Los diagramas se dibujan **en celdas de código** con `matplotlib` (patches, flechas, `annotate`) o `graphviz` para que se rendericen sin imágenes externas. También se permite `mermaid` en markdown y diagramas ASCII sencillos.
- Gráficos de datos con `matplotlib`/`seaborn`/`plotly`. Títulos, ejes y leyendas en español.
- Tras cada gráfico clave, una caja **👀 Qué debes observar** que diga qué patrón buscar y qué concluir.
- Cuando el resultado esté en Grafana, describe qué debe ver el alumno (y muestra el JSON del dashboard provisionado).

## Tono pedagógico
- Ir de lo concreto a lo abstracto: una traza diminuta de 3 spans dibujada a mano → modelo de datos → código → escala real.
- Explicar el "por qué" y el "cuándo NO usar esto" (p. ej. cuándo no capturar prompts, cuándo no usar tail sampling).
- Conectar siempre con lo que el alumno ya sabe (ML/ciencia de datos, backend, SRE).
- Cajas destacadas con emojis consistentes: 💡 Intuición · 📐 Matemáticas · 🏭 En producción · 🧠 Secretos de la élite · ⚠️ Cuidado · 🧪 Experimento · 📚 Para profundizar.

## Módulos largos
- Si una lección supera ~7 h o ~70 celdas, marca una caja **🧭 Ruta núcleo vs ampliación** (o dos sesiones).

## Datos y rúbricas
- Cadena de datos: stack local → modo degradado con datos pregrabados (mismo esquema, incluidos en el repo) → datos sintéticos regenerables.
- Umbrales de rúbrica calibrados con lo que **mide** la solución de referencia en modo `mock` y semilla fija, nunca con lo deseado.
- Evita rúbricas que dependan de latencias reales de la máquina del alumno: usa proporciones, rangos amplios o latencias simuladas deterministas.

## Calidad
- Exactitud técnica por encima de todo. Si una cifra o afirmación de industria no la puedes respaldar, no la pongas.
- No inventes atributos de semantic conventions, claves de configuración, flags, TraceQL/LogQL ni imágenes/charts: verifica en la documentación oficial (WebSearch/WebFetch) y marca lo experimental o cambiante (GenAI semconv, MCP, nuevas funciones de Tempo/Loki).
- Investiga la documentación y blogs más recientes para que el estado del arte sea actual (hasta 2026).
- Ejecuta el builder y corrige hasta que `save()` dé OK. Prueba localmente lo crítico (el entorno puede no tener Docker ni red abierta: documenta qué se probó y qué no).
