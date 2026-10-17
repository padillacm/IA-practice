# Módulo 06 · Auto-instrumentación: OpenLIT y OpenLLMetry frente a instrumentación manual

🟡 Intermedio · ≈ 4 h 30 min · **No necesita servicios de Compose** (usa un servidor «compatible con OpenAI» local sobre el LLM simulado y un conjunto pregrabado; las librerías de auto-instrumentación se instalan con `pip`).

## Qué aprenderás
- **Cómo funciona por dentro** la auto-instrumentación (parchear el cliente del proveedor) escribiendo a mano un parche de 15 líneas, y qué **no** puede ver (el bucle del agente, las herramientas, el ticket).
- El **ecosistema real a oct-2026**: instrumentación oficial de OpenTelemetry (`opentelemetry-instrumentation-genai-openai`, repo `opentelemetry-python-genai`), **OpenLLMetry** (`traceloop-sdk`) y **OpenLIT** (`openlit`): versiones, licencias, estado frente a las GenAI semconv (*Development*) y cadencia de versiones medida en PyPI.
- Un **laboratorio reproducible**: SupportOps ejecutado con 9 estrategias (manual, 3 auto, 3 híbridas, 2 con decoradores), 24 tickets y semilla fija, y qué mide cada una: forma de las trazas, cobertura de atributos, atribución de fallos y tokens por ticket, **exposición de PII por defecto**, trampas (doble instrumentación, reintentos ocultos del SDK, *streaming* sin `usage`), huella de dependencias y sobrecoste.
- Cómo **extenderlas**: híbrido (spans manuales de agente/herramienta + `chat` automático), decoradores (`@agent`, `@tool`, `@openlit.trace`) y `SpanProcessor.on_start`; y por qué **no** se puede redactar en `on_end`.
- Una **matriz de decisión** cuantificada con análisis de sensibilidad (pesos aleatorios) y recomendaciones por perfil de equipo.

## Archivos
| Archivo | Contenido |
|---|---|
| `06_autoinstrumentacion.ipynb` | Lección (teoría + parche a mano + laboratorio + 10 gráficos + autoevaluación) |
| `06_proyecto_autoinstrumentacion.ipynb` | Proyecto: mide 4 variantes, escribe un `SpanProcessor` de enriquecimiento y decide con una matriz justificada |
| `recorded/lab_seed42.json.gz` | Datos pregrabados del laboratorio (modo degradado, mismo esquema que `supportops.schema.SPAN_SCHEMA` + `scope`) |

Código de apoyo (en `supportops/`): `openai_compat.py` (servidor falso de OpenAI sobre el mock) y `autoinstr_lab.py` (ejecuta cada variante en un subproceso limpio). Documentados en `_tools/INTERFACES.md`.

## Servicios necesarios
Ninguno. `pip install openai openlit traceloop-sdk opentelemetry-instrumentation-genai-openai` solo para re-ejecutar el laboratorio (≈ 150 MB; sin ellas se usa el dataset pregrabado).

## Lecturas
- OpenTelemetry, *GenAI Semantic Conventions* (estado *Development*) — <https://github.com/open-telemetry/semantic-conventions-genai>
- OpenTelemetry, *Python GenAI instrumentations* (repo de las instrumentaciones oficiales) — <https://github.com/open-telemetry/opentelemetry-python-genai>
- OpenLIT — <https://github.com/openlit/openlit> · OpenLLMetry — <https://github.com/traceloop/openllmetry>
- Grafana Cloud, *AI Observability* (construido sobre el SDK de OpenLIT) — <https://grafana.com/docs/grafana-cloud/monitor-applications/ai-observability/introduction/>
- Datadog, *Datadog LLM Observability natively supports OpenTelemetry GenAI Semantic Conventions* (1-dic-2025) — <https://www.datadoghq.com/blog/llm-otel-semantic-convention>

## Siguiente
`07_tempo_traceql`: lo que acabas de elegir producir se consulta ahora en Tempo con TraceQL.
