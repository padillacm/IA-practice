# REVISION_PEDAGOGICA_1 · Módulos 00-07

Revisor: rev-pedagogico-00-07. Alumno de referencia: Python sólido, sin experiencia en agentes LLM, Docker ni observabilidad (COURSE_SPEC). Se leyó cada lección y cada proyecto completos. Todo cambio se hizo en los builders (`_tools/builders/build_00.py` … `build_07.py`) y se regeneraron los notebooks; solo se tocó contenido en markdown, salvo la lectura de verificación con nbclient indicada abajo.

## Resumen (≤ 400 palabras)

**Lo que ya estaba bien.** La secuencia intuición → ejemplo a mano → industria → experimento se cumple en casi todos los módulos (tracer a mano en 03, collector de juguete en 05, mini motor TraceQL en 07, parche a mano en 06). Todas las lecciones tienen analogías ML/backend/SRE, «👀 Qué debes observar» tras cada gráfico clave (9-12 por lección), autoevaluación con Cálculo/Diagnóstico/Transferencia y proyectos con pistas 🪜 y rúbrica calibrada.

**Hallazgos transversales y qué se hizo**
1. **Cajas 🔁 de repaso (módulos 01-07) eran de solo recuerdo** («cita…», «¿qué diferencia hay…?»). Se reescribieron las 3-4 preguntas de cada módulo como **cálculo, diagnóstico, predicción o transferencia** que usan lo previo en un caso nuevo y a veces anticipan el módulo actual.
2. **Prerrequisito no enseñado (alto impacto).** El TODO 3b del proyecto 01 exigía `Rule`/`ToolStep`, que la lección no explica. Se añadió un **ejemplo resuelto comentado** de una regla real y un plan por pasos.
3. **Carga cognitiva del módulo 00.** No había glosario: se usaban «token», «agente», «span», «p95», «SLI/SLO», «OTLP» antes de definirlos. Se añadió **🔤 Glosario mínimo** con analogía en una línea cada término.
4. **Módulos largos sin ruta.** 01, 03, 06 y 07 (73-77 celdas) ahora tienen **🧭 Ruta núcleo vs ampliación** con el mínimo irrenunciable.
5. **Ejemplo a mano antes de la fórmula/regla**: tokens acumulados en 01 (3300 vs 2400) antes de la fórmula; span con 3 desviaciones (verificado con el linter real) antes de las 13 reglas en 04; traza de 4 spans con 3 consultas en 07.
6. **Predicciones** («🤔 Predice antes de ejecutar») en 00, 02, 03, 05, 06, 07 y en los proyectos 02/05/06: retrieval practice y calibración de la intuición.
7. **Alineamiento objetivo ↔ evaluación.** Se añadieron preguntas para objetivos sin práctica evaluada: puntos de extensión y cambio de proveedor (01), correlación y resource/scope/atributo (02), configurar el exportador y coste de CPU (03), localizar la spec vigente (04), conservación de datos del Collector (05), matriz ponderada (06), ajuste de consultas y manual de diagnóstico (07).
8. **Andamiaje de proyectos.** Pistas nuevas o ampliadas en 04 (TODO `migrate`), 05 (plan en 3 iteraciones), 06 (TODO 6a/6b), 07 (ejemplo resuelto «pregunta 0» y TODO de métricas), 02 (descomposición del TODO 3). **👀** añadidos tras gráficos que no tenían interpretación (proyectos 02, 03, 07).
9. Títulos de cajas 🧠 duplicados («Secretos de la élite · Secretos de la élite») corregidos en 00-02.

**Verificación.** Proyecto 02 y 07 reejecutados con nbclient (sin errores, rúbrica OK; consultas TraceQL nuevas probadas con `traceql_mini`); el builder 05 reverificó su solución con Docker; el ejemplo de 04 se probó con el linter del módulo. Ninguna rúbrica, umbral ni celda ejecutable cambió.

## Detalle por módulo

| Mód. | Cambios | Pendiente / recomendación |
|---|---|---|
| 00 | Glosario mínimo; predicción antes de «grieta 4»; autoeval +1 (qué se pierde si cae Grafana/Collector); texto clarificado en el gráfico del `trace_id`; título 🧠. | El proyecto no tiene 👀 (solo hay gráficos en la solución). Un resumen visual de 1 página «un ticket de punta a punta» ayudaría. |
| 01 | Conexión 00 en diagnóstico/transferencia; 🧭 ruta núcleo; tokens a mano antes de la fórmula; ejemplo resuelto de `Rule` (proyecto); autoeval +2 (reintentos/extensión, proveedor), relabel. | Los adaptadores reales siguen sin probarse en vivo (honestidad ya declarada). |
| 02 | Conexión 00/01/01 aplicada; predicción de percentiles; autoeval +2; proyecto: plan TODO 3, predicción TODO 4, 👀 de la matriz de señales. | Los umbrales de `fires` (TODO 4) se dan hechos: es un andamiaje fuerte; en una reedición se podría pedir derivarlos. |
| 03 | Conexión aplicada (cálculo traceparent, diagnóstico trazas partidas, por qué `Instrumentor`); 🧭 ruta núcleo; predicción cola Batch; autoeval +2; 👀 de la cascada en el proyecto. | Es el módulo más difícil de la parte B para un recién llegado a `contextvars`; considerar dividir §3-4 en dos sesiones. |
| 04 | Ejemplo a mano antes del linter; conexión aplicada; autoeval +1; Pista 3 en `migrate`. | La instantánea de la spec caduca rápido: revisar fecha antes de cada tanda de alumnos. |
| 05 | Conexión Q1 con cálculo; glosa de sidecar/DaemonSet; predicción de la cola; autoeval +1; plan en 3 iteraciones. | El TODO 1 (todo el YAML) sigue siendo grande aunque tiene 4 pistas; opción: dividirlo en 3 celdas evaluables por separado. |
| 06 | Conexión con predicción/transferencia; 🧭 ruta núcleo; predicción antes del exp. 1; autoeval +1 y etiquetas; pistas 6a/6b. | Las cifras dependen de versiones fijadas de OpenLIT/OpenLLMetry (dataset pregrabado): avisar al alumno de que re-ejecutar en vivo puede variar. |
| 07 | Ejemplo a mano de 4 spans; conexión aplicada; predicción del retraso; 🧭 ruta núcleo; autoeval +2; proyecto: ejemplo resuelto Q0, pistas METRICS, 👀 de la línea temporal. | Muy denso (arquitectura Tempo 3, Parquet, metrics-generator): marcar §2 y §6 como lectura de contexto si hay poco tiempo. |

## Tabla para el mapa de conceptos y el glosario (módulo → horas reales, nivel, prerrequisitos, conceptos clave)

Horas = estimación del revisor para un alumno que parte de cero (incluye primeras descargas de Docker y fallos normales), frente a las ≈ 4-4,5 h anunciadas. «Núcleo» = ruta mínima (lección + proyecto).

| Módulo | Horas reales (núcleo / completo) | Nivel | Prerrequisitos | Conceptos clave |
|---|---|---|---|---|
| 00 Entorno | 3,5 / 4,5 | 🟢 | Python | cinco grietas del monitoreo clásico, mapa del stack (app → Collector → Tempo/Loki/Prometheus → Grafana), imagen/contenedor/volumen/red/puerto/perfil, readiness ≠ arrancado, OTLP/JSON, `trace_id` como hilo común |
| 01 Agente base | 3,5 / 5 | 🟢 | 00 | agente = bucle LLM + herramientas, workflow vs agente, `max_steps`, coste cuadrático del contexto, proveedor agnóstico, error de negocio ≠ de infraestructura, RAG TF-IDF, tráfico/fallos sintéticos, puntos de extensión |
| 02 Tres pilares | 3,5 / 5 | 🟢 | 00-01 | logs/métricas/trazas, counter/gauge/histogram, percentiles desde buckets y por qué no se promedian, resource/scope/span, `traceparent`, exemplars, golden signals + tokens/pasos/calidad, cardinalidad |
| 03 SDK de OTel | 4 / 5,5 | 🟡 | 01-02 | API vs SDK, `TracerProvider`/`Resource`, `contextvars` y trazas huérfanas en hilos, inject/extract, Simple vs Batch (cola y pérdida), samplers (head), OTLP exporter y variables `OTEL_*`, instrumentor manual de SupportOps |
| 04 Convenciones GenAI | 3,5 / 5 | 🟡 | 03 | `gen_ai.*`, `invoke_agent`/`chat`/`execute_tool`, niveles de requisito, tokens con caché, contenido opt-in (3 patrones), estado *Development*, linter y migración de nombres |
| 05 Collector | 4 / 5,5 | 🟡 | 00, 03-04 | receivers/processors/exporters/pipelines, orden recomendado, fan-out síncrono, `memory_limiter`, `batch`, `sending_queue`/reintentos, agente vs gateway, `otelcol validate`, métricas `otelcol_*`, OTTL |
| 06 Auto-instrumentación | 3,5 / 5 | 🟡 | 03-05 | parcheo del cliente, OpenLIT/OpenLLMetry/oficial, trazas huérfanas, híbrido, `SpanProcessor.on_start`, privacidad por defecto, doble instrumentación y reintentos ocultos, matriz ponderada y sensibilidad |
| 07 Tempo y TraceQL | 4,5 / 6 | 🟡 | 03-06 | spanset y evaluación por traza, `{A} && {B}` ≠ `{A && B}`, UNSET ≠ OK, estructurales, agregados, bytes inspeccionados, TraceQL metrics vs span metrics, service graph, búsqueda «primeros N» y retraso del live-store |

Total real estimado: ≈ 30 h de ruta núcleo y ≈ 42 h completo (frente a ≈ 35 h anunciadas para 00-07).

## Qué no se pudo evaluar

- No hubo alumnos reales: los tiempos son estimaciones; conviene medirlos con 2-3 personas.
- No se re-ejecutaron los notebooks 03, 04, 05, 06 (solo cambió markdown; el builder de 05 reverificó con Docker). No se levantó el stack (Grafana/Tempo): las comprobaciones contra servicios vivos de 00 y 07 siguen siendo las de la revisión de ejecutabilidad.
- Módulos fuera de rango (08-22) no revisados.
