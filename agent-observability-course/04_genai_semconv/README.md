# Módulo 04 · GenAI semantic conventions

🟡 Intermedio · ≈ 4 h 30 min · **No necesita servicios de Compose** (todo en memoria; funciona en Colab).

> ⚠️ **Estado de la spec:** las GenAI semantic conventions están en estado **Development** (inestables). Se contrastaron con la spec oficial el 2026-10-14 (commit `f3c6d0c9` de [`open-telemetry/semantic-conventions-genai`](https://github.com/open-telemetry/semantic-conventions-genai)); el repositorio **se movió** desde `semantic-conventions/docs/gen-ai`.

## Qué aprenderás
- Por qué existen las semantic conventions, **dónde vive la spec hoy**, qué es estable (`error.type`, `server.*`) y qué experimental (todo `gen_ai.*`), y cómo medir la **deriva** entre el paquete Python y la spec.
- Las operaciones `invoke_agent`, `chat`, `execute_tool` (y `create_agent`, `plan`, `invoke_workflow`…): *kind*, nombre y atributos; niveles *Required / Conditionally Required / Recommended / Opt-In*.
- **Tokens sin errores:** entrada total frente a caché de lectura/escritura y razonamiento, normalización por proveedor, y por qué sumar todos los spans cuenta los tokens dos veces.
- Un **linter propio** de atributos (13 reglas) validado contra la **implementación oficial** (`opentelemetry-util-genai`), y un **migrador** de nombres antiguos (`gen_ai.system` → `gen_ai.provider.name`…).
- **Contenido de prompts:** los tres patrones de la spec, su **coste de privacidad y de almacenamiento medidos** con PII sintética, y un almacén con referencias.
- Nombres actuales de las **métricas** GenAI y el evento de evaluación (adelanto de los módulos 09 y 14).

## Archivos
| Archivo | Contenido |
|---|---|
| `04_genai_semconv.ipynb` | Lección (teoría + código + 9 gráficos + autoevaluación) |
| `04_proyecto_genai_semconv.ipynb` | Proyecto: linter por familias de reglas, migrador, normalización de uso/finish por proveedor y política de contenido (7 TODO, rúbrica de 10 criterios) |
| `genai_semconv_snapshot.json` | Instantánea de la spec (atributos, tipos de span con niveles de requisito, métricas, enum de *finish reasons*) extraída de `model/gen-ai/*.yaml`; la usan lección y proyecto. Se regenera con `GENAI_SPEC_DIR=<clon> python _tools/builders/build_04.py` |

## Servicios necesarios
Ninguno.

## Lecturas
- OpenTelemetry, *GenAI semantic conventions* — <https://github.com/open-telemetry/semantic-conventions-genai>
- OpenTelemetry, `opentelemetry-python-genai` (`opentelemetry-util-genai`, instrumentaciones oficiales) — <https://github.com/open-telemetry/opentelemetry-python-genai>
- OpenTelemetry, *Attribute requirement levels* — <https://github.com/open-telemetry/semantic-conventions/blob/main/docs/general/attribute-requirement-level.md>
- Datadog, *OTel GenAI semantic conventions* — <https://www.datadoghq.com/blog/llm-otel-semantic-convention/>

## Siguiente
`05_collector`: el OpenTelemetry Collector recibe estos spans, métricas y logs y los reparte a Tempo, Loki y Prometheus.
