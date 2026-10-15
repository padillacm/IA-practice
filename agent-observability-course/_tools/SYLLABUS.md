# SYLLABUS · Observabilidad de agentes de IA en producción

Cada módulo: README.md + `NN_slug.ipynb` (lección) + `NN_proyecto_slug.ipynb` (proyecto), generados por
`_tools/builders/build_NN.py`. Los autores respetan el **alcance** (qué entra / qué NO) para no solaparse.
Niveles: 🟢 Básico · 🟡 Intermedio · 🟠 Avanzado · 🔴 Experto. ~4,3 h por módulo (≈100 h en total).

## Hilo conductor: «SupportOps»
Empresa ficticia de soporte al cliente (e-commerce de hardware). Un agente atiende tickets: clasifica, consulta una
base de conocimiento (RAG), llama a herramientas (pedidos, reembolsos, envíos), escala a humanos. Crece así:
v0 agente único (01) → instrumentado (03–06) → observado en Tempo/Loki/Prometheus/Grafana (07–10) → multi-agente y
MCP (11–12) → con presupuesto, evaluación y SLOs (13–16) → perfilado, escalado, en K8s y con PII protegida (17–20) →
plataforma completa (22).

## Infraestructura compartida (la crea A1 en el módulo 00–01; el resto la reutiliza)
- `stack/docker-compose.yml`: OTel Collector, Tempo, Loki, Prometheus (o Mimir), Grafana (y Pyroscope más tarde),
  con perfiles de Compose (`--profile core|metrics|profiling`) y datasources aprovisionados. Verificar con WebSearch/WebFetch
  las **versiones estables actuales** de cada imagen antes de fijarlas y explicar por qué.
- `supportops/` (paquete Python, `pip install -e agent-observability-course`): agente base con proveedor LLM
  agnóstico (`LLM_PROVIDER=mock|anthropic|openai|ollama`, `mock` determinista por defecto), herramientas simuladas,
  **simulador de tráfico** (usuarios sintéticos, semilla fija) e **inyector de fallos** (latencia, errores 5xx,
  alucinaciones, bucles de tool calls, fugas de PII). Las API keys solo por variables de entorno, nunca en notebooks.
- Cada notebook empieza con una celda `check_stack()` que verifica qué servicios están arriba y, si no, indica el
  comando exacto para levantarlos (`docker compose --profile ... up -d`) o el modo degradado sin Docker.
- Cadena de resiliencia: stack local → modo degradado (datos de ejemplo pregrabados incluidos en el repo, mismo esquema)
  para que ningún notebook se quede bloqueado.

## Bloque A · Fundamentos 🟢
| Módulo | Alcance (entra) | NO entra | Proyecto |
|---|---|---|---|
| **00_entorno** | Por qué los agentes rompen el monitoreo clásico (no determinismo, cadenas largas, costes, calidad). Mapa del stack. Docker/Compose desde cero para quien nunca lo usó. Levantar el stack, Grafana vacío. | Instrumentar código | Levantar el stack, verificar salud de cada servicio, primer dashboard "hola mundo". |
| **01_agente_base** | Qué es un agente (bucle LLM + tools) con ejemplos mínimos; el paquete `supportops`; proveedor agnóstico; simulador de tráfico y fallos. | OTel | Extender SupportOps v0 con una herramienta nueva y reproducir 3 fallos inyectados. |
| **02_tres_pilares** | Traces, metrics, logs; modelo de datos de OTel (resource, scope, span, contexto); señales correlacionadas; analogía con microservicios y SRE; golden signals aplicadas a agentes. | SDK en profundidad | Clasificar síntomas de 10 incidentes de SupportOps: qué señal los detecta mejor y por qué. |

## Bloque B · OpenTelemetry 🟡
| Módulo | Alcance (entra) | NO entra | Proyecto |
|---|---|---|---|
| **03_otel_sdk_python** | TracerProvider, spans, atributos, eventos, status, contexto y propagación W3C, exportador OTLP, `BatchSpanProcessor`. A mano antes de librerías. | Collector | Instrumentar manualmente SupportOps v0 y ver las primeras trazas (en consola/OTLP). |
| **04_genai_semconv** | GenAI semantic conventions: `gen_ai.*`, operaciones `invoke_agent`/`create_agent`/`execute_tool`/`chat`, tokens, finish reasons; estable vs experimental; eventos de prompts/completions y su coste de privacidad. Verificar contra la spec oficial. | Auto-instrumentación | Modelar cada paso del agente con las convenciones y validar atributos con un linter propio. |
| **05_collector** | Receivers, processors (batch, memory_limiter, attributes, resource), exporters; pipelines por señal; despliegue gateway vs agent; `otelcol validate`. | Tail sampling (módulo 18) | Configurar un Collector que reciba OTLP y exporte trazas/métricas/logs a los tres backends. |
| **06_autoinstrumentacion** | OpenLIT y OpenLLMetry frente a instrumentación manual: qué cubren, qué ocultan, cómo extenderlas; trade-offs de mantenimiento. | Backends | Comparar manual vs auto sobre el mismo agente y decidir con una matriz justificada. |

## Bloque C · Backends y Grafana 🟡
| Módulo | Alcance (entra) | NO entra | Proyecto |
|---|---|---|---|
| **07_tempo_traceql** | Arquitectura de Tempo, almacenamiento, TraceQL (selectores, estructurales, agregados), service graph y span metrics. | Muestreo avanzado | Preguntas de diagnóstico sobre un lote de trazas con fallos: escribir las TraceQL que las responden. |
| **08_loki_logql** | Arquitectura de Loki, labels vs structured metadata, LogQL, logs correlacionados con traza (trace_id), logging estructurado en Python. | Pipelines pesados de logs | Pipeline de logs de SupportOps correlacionados con trazas y 4 consultas de investigación. |
| **09_metricas** | Prometheus/Mimir, instrumentos OTel (counter, histogram, gauge), RED + métricas GenAI (latencia, tokens, coste), exemplars, cardinalidad básica. | Escala (18) | Métricas de negocio y de modelo de SupportOps con histogramas y exemplars. |
| **10_grafana** | Dashboards como código, variables, paneles de trazas/logs/métricas, correlaciones (trace→logs→metrics), Explore, alertas básicas. | Alertas por SLO (16) | Dashboard "Salud del agente" con navegación entre señales; provisionado como código. |

## Bloque D · Producción 🟠
| Módulo | Alcance (entra) | NO entra | Proyecto |
|---|---|---|---|
| **11_multiagente** | Orquestador + subagentes, handoffs, propagación de contexto entre procesos/colas, fallos en cascada, vistas de árbol de agentes. | MCP (12) | Convertir SupportOps en multi-agente y rastrear una petición de extremo a extremo. |
| **12_mcp_tools** | Trazas a través de servidores MCP y herramientas remotas, atributos de herramientas, errores y timeouts, seguridad de herramientas observables. Estado de las convenciones MCP (verificar). | Multi-agente | Instrumentar un servidor MCP de pedidos y unir su traza con la del agente. |
| **13_costes_finops** | Tokens → coste, atribución por cliente/feature/modelo, presupuestos y topes, caching de prompts, detección de bucles caros. | Evaluación de calidad | Panel de FinOps con coste por ticket, presupuesto y alerta de desvío. |
| **14_evaluacion_online** | LLM-as-judge como spans/eventos, métricas de calidad online, feedback de usuario, muestreo para evaluar, sesgos del juez, coste de evaluar. | Regresiones offline (15) | Evaluador online sobre tráfico de SupportOps con métricas visibles en Grafana. |
| **15_calidad_regresion** | Datasets desde trazas, regresión de prompts/modelos, drift de calidad y de comportamiento, canarios, comparativas A/B de versiones de agente. | Evaluación en línea (14) | Detectar una regresión introducida en un prompt usando solo telemetría. |
| **16_slos_alertas_incidentes** | SLIs/SLOs específicos de agentes (disponibilidad, latencia, calidad, coste), error budget, burn-rate multiventana, alertas, runbooks, on-call, postmortems sin culpa. | Escala del stack | Definir SLOs, alertas y un runbook; simular un incidente y escribir el postmortem. |
| **17_profiling_pyroscope** | Cuarto pilar: continuous profiling con Pyroscope, flamegraphs, correlación traza↔perfil, hot paths de agentes (serialización, embeddings, parsing). | Optimización de modelos | Encontrar y arreglar un cuello de botella de CPU en SupportOps con perfiles. |

## Bloque E · Élite 🔴
| Módulo | Alcance (entra) | NO entra | Proyecto |
|---|---|---|---|
| **18_escala_muestreo_coste** | Head vs tail sampling, muestreo por errores/latencia/coste, cardinalidad, multi-tenant, retención y tiering, coste del propio stack, límites de ingesta. | K8s (19) | Diseñar la política de muestreo y retención de SupportOps con presupuesto y medir su impacto. |
| **19_kubernetes_helm** | Desplegar Collector, backends y agentes en K8s con Helm (kind/k3d local), Operator del Collector, autoscaling, configuración como código. Verificar charts y versiones actuales. | Administración avanzada de K8s | Desplegar el stack y SupportOps en un clúster local y verificar el flujo de telemetría. |
| **20_privacidad_seguridad** | PII en prompts/logs, redacción en el Collector, captura configurable de contenido, prompt injection y su detección vía telemetría, auditoría y retención por cumplimiento. | Legislación detallada | Pipeline de redacción de PII y alertas de posible inyección con casos inyectados. |
| **21_elite_playbook** | Masterclass: debugging de producción con casos de fallo reales (cascadas, bucles, regresiones silenciosas, tormentas de cardinalidad), patrones y antipatrones, cultura de observabilidad, compendio de secretos con fuentes. | Contenido nuevo del stack | "Mesa de incidentes": diagnosticar 5 incidentes sin pistas directas. |
| **22_capstone** | Integración: plataforma completa para SupportOps multi-agente (instrumentación, backends, SLOs, calidad, costes, privacidad, despliegue) + checklist de producción. | Conceptos nuevos | Entrega final con rúbrica integral y revisión de arquitectura. |

## Documentos extra (A8)
- `GUIA_DE_ESTUDIO.md` (ruta, tiempos, mapa de conceptos mermaid, glosario ES/EN) — lo crea el revisor pedagógico.
- `extras/ENTREVISTAS_SYSTEM_DESIGN.md`: preguntas típicas de observabilidad de IA y 3 diseños de referencia.
- `extras/RUTA_DE_CARRERA.md`: roles (AI platform, SRE de IA, observability engineer), certificaciones y comunidad (verificar cada enlace y certificación).

## Notas transversales para los autores
- Verifica con WebSearch/WebFetch la **spec oficial** de OpenTelemetry (GenAI semconv: qué es estable y qué experimental), las
  docs de Tempo, Loki, Grafana, Pyroscope y los charts de Helm. No inventes atributos, flags ni claves de configuración.
- Validar configs (YAML del Collector, Tempo, Loki, Compose) con las herramientas oficiales cuando sea posible
  (`docker compose config`, `otelcol validate`, etc.) y documentar si no se pudo ejecutar.
- Las rúbricas se calibran con lo que **mide** la solución en modo `mock` y con semillas fijas.
- En la lección, "desde cero" significa implementar a mano el mecanismo (p. ej. propagar contexto manualmente, escribir
  un exporter OTLP mínimo, calcular burn-rate) antes de usar el SDK/Collector.
