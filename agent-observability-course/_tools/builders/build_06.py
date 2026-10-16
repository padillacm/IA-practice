"""Genera el módulo 06_autoinstrumentacion: README, lección y proyecto (autor A3).
Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_06.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "06_autoinstrumentacion"

# ---------------------------------------------------------------------------------------------------------------------
# Código compartido entre lección y proyecto (se inserta tal cual en celdas)
# ---------------------------------------------------------------------------------------------------------------------
PIP_LIBS = '''
# Opcional pero recomendado (≈ 1-2 min, ~150 MB): las tres opciones de auto-instrumentación + el cliente de OpenAI.
# Sin ellas el notebook funciona igual con el dataset pregrabado (mismo esquema), solo que no puedes re-ejecutar el laboratorio.
%pip install -q "openai>=1.50" openlit traceloop-sdk opentelemetry-instrumentation-genai-openai
'''

SETUP = '''
import importlib.util, json, gzip, re, collections, inspect, time
from importlib import metadata
from supportops import autoinstr_lab as lab
from supportops.telemetry import setup_telemetry, OTelInstrumentor
_ = check_stack([])          # este módulo no necesita servicios de Compose

def has(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False

def ver(pkg: str) -> str:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return "no instalado"

LIBS = {"openai": has("openai"), "openlit": has("openlit"), "openllmetry": has("traceloop"),
        "official": has("opentelemetry.instrumentation.genai.openai")}
PACKAGES = ["openai", "openlit", "traceloop-sdk", "opentelemetry-instrumentation-genai-openai", "opentelemetry-sdk"]
print("Versiones instaladas:", {p: ver(p) for p in PACKAGES})
print("Disponible para re-ejecutar el laboratorio:", all(LIBS.values()), LIBS)
'''

LOAD = '''
# Conjunto pregrabado: 24 tickets (semilla 42) por variante, generado con supportops.autoinstr_lab.build_dataset().
REC = ROOT / "06_autoinstrumentacion" / "recorded" / "lab_seed42.json.gz"
LAB = json.load(gzip.open(REC, "rt", encoding="utf-8"))["runs"]
print(len(LAB), "ejecuciones pregrabadas:", ", ".join(LAB)[:300], "...")
print("versiones con las que se grabó:", LAB["openlit"]["meta"]["versions"])
'''

HELPERS = '''
EXPECTED_CHAT = ["gen_ai.operation.name", "gen_ai.provider.name", "gen_ai.request.model", "gen_ai.response.model",
                 "gen_ai.response.id", "gen_ai.response.finish_reasons", "gen_ai.usage.input_tokens",
                 "gen_ai.usage.output_tokens", "gen_ai.conversation.id", "supportops.ticket.id", "supportops.step",
                 "supportops.attempt"]
EMAIL = re.compile(r"[\\w.]+@example\\.com")           # los PII sintéticos de SupportOps son correos @example.com

def is_chat(s: dict) -> bool:
    return s["attributes"].get("gen_ai.operation.name") == "chat"

def traces_of(spans: list[dict]) -> dict[str, list[dict]]:
    out = collections.defaultdict(list)
    for s in spans:
        out[s["trace_id"]].append(s)
    return out

def trace_stats(spans: list[dict]) -> dict:
    """Forma de las trazas: ¿cuántas hay, de qué tamaño y cuántas tienen una raíz «de agente» (no un span de LLM)?"""
    tr = traces_of(spans)
    rooted = 0
    for t in tr.values():
        roots = [s for s in t if s["parent_span_id"] is None]
        rooted += bool(roots) and not is_chat(roots[0])
    return {"n_spans": len(spans), "n_traces": len(tr), "spans_per_trace": len(spans) / max(1, len(tr)),
            "rooted_share": rooted / max(1, len(tr))}

def attr_coverage(spans: list[dict], expected: list[str] = EXPECTED_CHAT, only_ok: bool = True) -> dict[str, float]:
    """Fracción de spans `chat` (sin error) que llevan cada atributo esperado."""
    chats = [s for s in spans if is_chat(s) and (s["status"] != "ERROR" or not only_ok)]
    return {a: sum(a in s["attributes"] for s in chats) / max(1, len(chats)) for a in expected}

def ticket_of_trace(spans: list[dict]) -> dict[str, str]:
    """trace_id -> ticket, si algún span de la traza declara `supportops.ticket.id` o `gen_ai.conversation.id`."""
    m = {}
    for s in spans:
        t = s["attributes"].get("supportops.ticket.id") or s["attributes"].get("gen_ai.conversation.id")
        if t:
            m[s["trace_id"]] = t
    return m

def failure_attribution(run: dict) -> tuple[float, int]:
    """De los tickets que acabaron mal (error / max_steps / degraded), ¿qué fracción tiene una traza atribuible con algún span ERROR?"""
    bad = [r["ticket_id"] for r in run["results"] if r["status"] in ("error", "max_steps", "degraded")]
    t_of, tr = ticket_of_trace(run["spans"]), traces_of(run["spans"])
    with_err = {t_of[tid] for tid, ss in tr.items() if tid in t_of and any(s["status"] == "ERROR" for s in ss)}
    return (sum(t in with_err for t in bad) / len(bad) if bad else float("nan")), len(bad)

def token_attribution(run: dict) -> float:
    """Fracción de tickets cuyos tokens (suma de spans `chat` de su traza) coinciden con los del AgentResult."""
    t_of, tok = ticket_of_trace(run["spans"]), collections.Counter()
    for s in run["spans"]:
        if is_chat(s) and s["trace_id"] in t_of:
            a = s["attributes"]
            tok[t_of[s["trace_id"]]] += int(a.get("gen_ai.usage.input_tokens", 0)) + int(a.get("gen_ai.usage.output_tokens", 0))
    ok = sum(tok.get(r["ticket_id"], 0) == int(r["input_tokens"]) + int(r["output_tokens"]) for r in run["results"])
    return ok / len(run["results"])

def pii_spans(spans: list[dict]) -> int:
    """Nº de spans que contienen un correo (PII sintético) en atributos o eventos."""
    return sum(bool(EMAIL.search(json.dumps([s["attributes"], s["events"]], ensure_ascii=False))) for s in spans)

def kb_per_ticket(run: dict) -> float:
    return sum(len(json.dumps(s["attributes"], ensure_ascii=False)) for s in run["spans"]) / 1024 / len(run["results"])
'''

SOURCES = ["Wrapped"]  # marcador (no se usa)


def readme() -> str:
    return """# Módulo 06 · Auto-instrumentación: OpenLIT y OpenLLMetry frente a instrumentación manual

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
"""


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "06_autoinstrumentacion.ipynb", "Módulo 06 · Auto-instrumentación frente a instrumentación manual")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 06 · Auto-instrumentación: OpenLIT y OpenLLMetry frente a instrumentación manual

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | **Ninguno** (servidor «OpenAI» local sobre el LLM simulado + dataset pregrabado). Las librerías se instalan con `pip` |
    | **RAM aproximada** | < 600 MB (kernel + subprocesos del laboratorio, uno cada vez) |
    | **Prerrequisitos** | Módulos 03-05 (SDK, GenAI semconv, `OTelInstrumentor`) y 01 (los *hooks* `Instrumentor` de SupportOps) |
    | **Hilo conductor** | Decides con datos **cómo** instrumentas SupportOps: a mano, con una librería, o las dos cosas |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** cómo funciona la auto-instrumentación (parcheo del cliente del proveedor) y **escribir a mano** un parche mínimo que genera un span `chat`.
    2. **Distinguir** las tres familias que existen en oct-2026 (instrumentación oficial de OpenTelemetry, OpenLLMetry y OpenLIT) por licencia, alcance, estado frente a las GenAI semconv y cadencia de versiones.
    3. **Medir** —no opinar— qué cubre y qué oculta cada opción sobre el mismo agente: forma de las trazas, cobertura de atributos, atribución de fallos y de tokens por ticket.
    4. **Auditar** la privacidad por defecto de cada librería (qué prompts y datos personales acaban en un atributo) y configurarla.
    5. **Detectar** las trampas típicas: doble instrumentación, reintentos ocultos del SDK, *streaming* sin `usage` y *spans* extra no pedidos.
    6. **Extender** una librería con spans manuales (híbrido), decoradores y un `SpanProcessor.on_start`, y **explicar** por qué la redacción no puede hacerse en `on_end`.
    7. **Cuantificar** la huella (dependencias, tiempo de arranque, sobrecoste por llamada) y el esfuerzo de mantenimiento.
    8. **Decidir** con una matriz ponderada y un análisis de sensibilidad, y defender la recomendación para tres perfiles de equipo.
    """)

    md("""
    ## 🔁 Conexión con módulos anteriores
    """)
    md(details("1 · (Módulo 03) ¿Qué pasa con un span si lo creas con `start_as_current_span` y dentro llamas a otra función que también crea un span?",
               "El segundo span toma como padre el span *actual* del contexto (`contextvars`) y hereda su `trace_id`: forman un árbol dentro de la misma traza. Sin un span actual, cada span nuevo abre **una traza nueva** (lo veremos con las librerías automáticas)."))
    md(details("2 · (Módulo 04) ¿Qué operaciones GenAI modela SupportOps y qué *kind* tiene cada una?",
               "`invoke_agent` (INTERNAL, el ticket), `chat` (CLIENT, cada llamada al LLM) y `execute_tool` (INTERNAL, cada herramienta). Una librería de cliente solo puede conocer `chat`; las otras dos son semántica de **tu** aplicación."))
    md(details("3 · (Módulo 04) ¿Por qué `gen_ai.input.messages` / `gen_ai.output.messages` son un riesgo y qué dice la spec sobre capturarlos por defecto?",
               "Contienen el prompt y la respuesta íntegros (datos personales incluidos). La spec indica que las instrumentaciones **no deberían** capturar contenido por defecto y que debe activarlo el usuario de forma explícita (p. ej. `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`)."))
    md(details("4 · (Módulo 01) ¿Qué tres *context managers* ofrece el `Instrumentor` de SupportOps?",
               "`agent_run(ctx)`, `llm_call(ctx, info)` y `tool_call(ctx, info)` (más `log(...)`). La instrumentación manual es rellenar estos *hooks*."))

    code(boot("viz,otel"))
    code(PIP_LIBS)
    code(IMPORTS + SETUP)
    code(LOAD)

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ---
    # 1 · Intuición: ¿qué significa «auto-instrumentar»?

    Instrumentar es hacer que tu programa emita spans, métricas y logs. Hay dos maneras de insertar esas llamadas:

    | | **Manual** (módulos 03-05) | **Automática** (este módulo) |
    |---|---|---|
    | Dónde se insertan | En **tu** código: *hooks* en el bucle del agente, las herramientas… | En el **cliente de terceros** (`openai`, `anthropic`, `httpx`…): la librería lo *parchea* al arrancar |
    | Qué ve | Todo lo que tú marques: ticket, decisiones, herramientas, reintentos | Solo lo que cruza el **límite del cliente**: una llamada `create(...)` y su respuesta |
    | Esfuerzo | Escribir y mantener los hooks | `pip install` + 1 línea (`init()` / `instrument()`) |
    | Analogía **ML** | Registrar tus propias métricas dentro del bucle de entrenamiento | `wandb.watch(model)`: engancha el framework sin tocar tu bucle… pero no sabe qué significa *tu* experimento |
    | Analogía **backend** | Logs/traces escritos a mano en cada handler | El agente APM (Datadog, New Relic): instrumenta Flask, `requests`, la BBDD solos; no sabe qué es un «pedido» |
    | Analogía **SRE** | Una sonda *blackbox* con tus checks | Un *service mesh*: ve las peticiones, pero no la lógica de negocio |

    Dibujemos **dónde** actúa cada una sobre el agente de SupportOps:
    """)
    code('''
fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 5.2))
for a in (a1, a2):
    a.set_xlim(0, 100); a.set_ylim(0, 44); a.axis("off"); a.grid(False)
C = viz.PALETTE
# ---- MANUAL
a1.set_title("MANUAL · hooks dentro de TU bucle (módulos 03-05)", loc="left")
viz.box(a1, 2, 18, 30, 16, "SupportAgent.run()\\nbucle LLM + herramientas", C["neutral"], fontsize=9, bold=True)
h1 = viz.box(a1, 40, 30, 22, 7, "agent_run  →  invoke_agent", C["traces"], fontsize=8)
h2 = viz.box(a1, 40, 20, 22, 7, "llm_call  →  chat", C["traces"], fontsize=8)
h3 = viz.box(a1, 40, 10, 22, 7, "tool_call  →  execute_tool", C["traces"], fontsize=8)
sdk = viz.box(a1, 72, 18, 25, 16, "SDK de OpenTelemetry\\n→ OTLP → Collector", C["metrics"], fontsize=9, bold=True)
for h in (h1, h2, h3):
    viz.arrow(a1, (32.5, 26), viz.left(h), color=C["traces"], rad=0.0)
    viz.arrow(a1, viz.right(h), (71.5, 26), color=C["traces"])
a1.text(2, 4, "Ve: ticket, pasos, herramientas, reintentos, errores de dominio", fontsize=9, color=C["ok"])
# ---- AUTO
a2.set_title("AUTO · parche en el cliente del proveedor", loc="left")
viz.box(a2, 2, 18, 24, 16, "SupportAgent.run()\\nbucle + herramientas", C["neutral"], fontsize=9, bold=True)
cl = viz.box(a2, 33, 24, 25, 11, "openai ... .create()\\nparcheado (wrapper)", C["traces"], fontsize=9, bold=True)
srv = viz.box(a2, 33, 6, 25, 9, "HTTP → proveedor LLM", C["neutral"], fontsize=9)
sdk2 = viz.box(a2, 70, 18, 27, 16, "SDK de OpenTelemetry\\n→ OTLP → Collector", C["metrics"], fontsize=9, bold=True)
viz.arrow(a2, viz.right((2, 18, 24, 16)), viz.left(cl), "llama", color=C["neutral"])
viz.arrow(a2, viz.bottom(cl), viz.top(srv), color=C["neutral"])
viz.arrow(a2, viz.right(cl), (69.5, 28), "span chat", color=C["traces"])
a2.add_patch(plt.Rectangle((1, 15.5), 26, 21.5, fill=False, ls="--", ec=C["error"], lw=1.4))
a2.text(2, 11.2, "FUERA de su radio:\\nticket, herramientas,\\ndecisiones, reintentos", fontsize=8.5, color=C["error"])
a2.text(30, 1.5, "Ve: cada llamada al modelo (tokens, modelo, errores HTTP)", fontsize=9, color=C["ok"])
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - A la izquierda **tú decides** dónde está cada span; a la derecha la librería decide por ti, pero **solo en la frontera del cliente** (recuadro rojo = lo que queda fuera).
    - Por eso la pregunta del módulo no es «¿cuál es mejor?», sino «¿**qué parte** de mi telemetría puede producir una librería y qué parte debo escribir yo?».
    - Spoiler que mediremos: la parte que falta es justo la que une los spans en **una traza por ticket**.
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ---
    # 2 · Por dentro: un parche a mano

    Todas estas librerías hacen lo mismo que el código de abajo: **sustituyen** un método del cliente por un envoltorio que abre un span, llama al original y copia datos de la respuesta. Usamos el servidor «OpenAI» local de SupportOps (`supportops.openai_compat.FakeOpenAIServer`, determinista y sin red) con el cliente oficial `openai`.
    """)
    code('''
import openai
from opentelemetry.trace import SpanKind

tel = setup_telemetry("demo-parche", mode="memory", set_global=False)       # solo memoria: no necesita Collector
tracer = tel.tracer("demo.parche")
Completions = openai.resources.chat.completions.Completions
_original = Completions.create                                              # guardamos el método original

def create_con_span(self, *args, **kwargs):
    with tracer.start_as_current_span(f"chat {kwargs.get('model')}", kind=SpanKind.CLIENT) as span:   # excepción => span ERROR solo
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.request.model", kwargs.get("model", ""))
        resp = _original(self, *args, **kwargs)                              # la llamada real
        span.set_attribute("gen_ai.usage.input_tokens", resp.usage.prompt_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", resp.usage.completion_tokens)
        span.set_attribute("gen_ai.response.id", resp.id)
        return resp

Completions.create = create_con_span                                        # <- el «parche»
try:
    from supportops.openai_compat import FakeOpenAIServer
    with FakeOpenAIServer() as srv:
        client = openai.OpenAI(base_url=srv.base_url, api_key="sk-fake", max_retries=0)
        client.chat.completions.create(model="mock-small", messages=[{"role": "user", "content": "Hola, ¿dónde está mi pedido ORD-00012?"}])
finally:
    Completions.create = _original                                          # SIEMPRE deshacer (las librerías de verdad lo hacen en uninstrument())
tel.force_flush()
print(json.dumps([{k: s[k] for k in ("name", "kind", "attributes")} for s in tel.span_records()], indent=1, ensure_ascii=False))
tel.shutdown()
''')
    md("""
    Con 15 líneas tenemos un span `chat` con tokens. Lo que **no** hace nuestro parche —y por lo que existen las librerías—:

    | Caso | Qué hay que resolver | ¿Lo hace nuestro parche? |
    |---|---|---|
    | `stream=True` | Envolver el iterador y acumular *chunks*; los tokens solo llegan al final (y solo si se pidió `include_usage`) | No |
    | Versiones del SDK | `create` cambia de firma entre versiones; hay clientes asíncronos, `responses`, `embeddings`… | No |
    | Otros proveedores | Anthropic, Bedrock, Gemini, Cohere… cada uno con su forma | No |
    | Atributos de la spec | Nombres y valores correctos, *finish reasons*, mensajes en el formato de la spec | Parcialmente |
    | Métricas | Duración y tokens como histogramas/contadores | No |
    | Privacidad | Decidir si se captura el contenido | No (no lo captura) |

    > 💡 **Intuición.** Una librería de auto-instrumentación es un *equipo de mantenimiento* que sigue por ti los cambios de ~20 SDKs. Ese es el valor real: no las 15 líneas, sino que alguien las mantenga cuando `openai` cambie.
    """)

    md("""
    ## 2.2 · El ecosistema en oct-2026 (verificado)

    | | **Instrumentación oficial de OpenTelemetry** | **OpenLLMetry** (Traceloop) | **OpenLIT** |
    |---|---|---|---|
    | Paquete(s) | `opentelemetry-instrumentation-genai-openai`, `-genai-anthropic`, `-genai-langchain`, … (todas usan `opentelemetry-util-genai`) | `traceloop-sdk` (+ `opentelemetry-instrumentation-<proveedor>` por cada SDK) | `openlit` |
    | Repo | `open-telemetry/opentelemetry-python-genai` (las copias en `opentelemetry-python-contrib` solo reciben parches de seguridad; `opentelemetry-instrumentation-openai-v2` está **deprecado**) | `traceloop/openllmetry` | `openlit/openlit` |
    | Versión medida (pip, oct-2026) | 1.2b0 (beta) | 0.62.4 | 1.45.0 |
    | Licencia | Apache-2.0 | Apache-2.0 | Apache-2.0 |
    | Filosofía | Solo librería de instrumentación; tú pones SDK y exportador | SDK de arranque (`Traceloop.init()`) + decoradores `@workflow/@task/@agent/@tool` | SDK de arranque (`openlit.init()`) **y** plataforma propia (UI, evals, guardrails) |
    | Contenido de prompts | **No** por defecto (`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`) | Sí por defecto (`TRACELOOP_TRACE_CONTENT`) | Sí por defecto (`capture_message_content`) |
    | Estado frente a semconv | Sigue la spec GenAI (*Development*); «usa siempre las últimas convenciones experimentales» | Atributos `gen_ai.*` de la spec actual (medido); mantiene además su propio paquete de convenciones | Atributos `gen_ai.*` de la spec actual (medido) + atributos propios `openlit.*` |
    | Quién lo usa | Base de referencia del proyecto OpenTelemetry | Documentado como emisor compatible con Datadog, Honeycomb, Grafana, etc. (README) | Grafana Cloud *AI Observability* se construye sobre el SDK de OpenLIT |

    > ⚠️ **Estado experimental.** Las GenAI semantic conventions siguen en estado *Development* (README del repo `semantic-conventions-genai`): los nombres de atributos y su formato han cambiado varias veces en 2025-2026 (p. ej. `gen_ai.system` → `gen_ai.provider.name`, y los mensajes pasaron de eventos a atributos `gen_ai.input.messages`). Fija versiones y revisa los *changelogs* antes de actualizar.
    >
    > Traceloop, la empresa tras OpenLLMetry, anunció en 2026 que se une a ServiceNow (entrada de su blog «Traceloop is joining ServiceNow»); el repositorio sigue bajo Apache-2.0. Comprueba el estado actual del proyecto antes de depender de él: es un riesgo de gobernanza que la matriz del final tiene en cuenta.
    """)

    md("""
    ### La cadencia de versiones es un coste de mantenimiento
    Cada versión nueva puede cambiar atributos. Contamos las publicaciones por mes en PyPI (consulta en vivo si hay red; si no, la instantánea del 15-oct-2026 incluida aquí).
    """)
    code('''
SNAP = {   # versiones publicadas por mes en PyPI (instantánea 15-oct-2026)
    "OpenLIT (openlit)":                  {"2025-10": 5, "2025-11": 2, "2025-12": 2, "2026-01": 2, "2026-02": 6, "2026-03": 6, "2026-04": 6, "2026-05": 1, "2026-06": 0, "2026-07": 2, "2026-08": 1, "2026-09": 0},
    "OpenLLMetry (traceloop-sdk)":        {"2025-10": 2, "2025-11": 9, "2025-12": 4, "2026-01": 2, "2026-02": 7, "2026-03": 9, "2026-04": 6, "2026-05": 1, "2026-06": 1, "2026-07": 0, "2026-08": 1, "2026-09": 1},
    "Oficial (openai-v2 → genai-openai)": {"2025-10": 0, "2025-11": 1, "2025-12": 1, "2026-01": 0, "2026-02": 0, "2026-03": 0, "2026-04": 0, "2026-05": 1, "2026-06": 0, "2026-07": 1, "2026-08": 1, "2026-09": 1},
}
def pypi_monthly(pkgs: list[str], first="2025-10", last="2026-09") -> dict[str, int]:
    import urllib.request
    c = collections.Counter()
    for p in pkgs:
        d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{p}/json", timeout=8))
        for files in d["releases"].values():
            if files:
                c[files[0]["upload_time"][:7]] += 1
    return {m: c[m] for m in sorted(SNAP["OpenLIT (openlit)"]) if first <= m <= last}
try:
    live = {"OpenLIT (openlit)": pypi_monthly(["openlit"]), "OpenLLMetry (traceloop-sdk)": pypi_monthly(["traceloop-sdk"]),
            "Oficial (openai-v2 → genai-openai)": pypi_monthly(["opentelemetry-instrumentation-openai-v2", "opentelemetry-instrumentation-genai-openai"])}
    REL, src = live, "PyPI en vivo"
except Exception as e:                                   # sin red: instantánea
    REL, src = SNAP, "instantánea 15-oct-2026"
months = list(next(iter(REL.values())))
fig, ax = plt.subplots(figsize=(12, 3.8)); w = 0.27
for i, (name, col) in enumerate(zip(REL, [viz.PALETTE["logs"], viz.PALETTE["metrics"], viz.PALETTE["traces"]])):
    ax.bar(np.arange(len(months)) + (i - 1) * w, [REL[name][m] for m in months], w, label=f"{name} · total {sum(REL[name].values())}", color=col)
ax.set_xticks(range(len(months))); ax.set_xticklabels(months, rotation=45); ax.set_ylabel("versiones publicadas / mes")
ax.set_title(f"Cadencia de publicación (oct-2025 → sep-2026) · fuente: {src}"); ax.legend(); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - OpenLIT y OpenLLMetry publican **de 0 a 9 versiones al mes** (según el mes); la oficial publica poco (y es beta). Más versiones = más correcciones **y** más oportunidades de que cambie un nombre de atributo.
    - El patrón no es lineal: el ritmo de ambos bajó de mayo de 2026 en adelante. No lo interpretes como abandono ni como estabilidad: es un dato para **fijar versiones** (`pip install openlit==1.45.0`) y subir de versión a propósito, con una prueba de contrato como la del proyecto.
    - La cadencia se cuenta por *paquete*: OpenLLMetry tiene decenas de paquetes `opentelemetry-instrumentation-*` que versionan juntos.
    """))

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ---
    # 3 · El laboratorio: el mismo agente, nueve estrategias

    Ejecutamos SupportOps con **24 tickets** (semilla 42, `mock`) contra el servidor «OpenAI» local, que además inyecta **errores 503 del proveedor** (≈ 12 %) y los tickets traen fallos de herramientas y un 25 % de PII sintética. Cada estrategia corre en un **subproceso limpio** (estas librerías parchean `openai` globalmente y no se pueden deshacer con limpieza en el mismo intérprete: dos en el mismo proceso se contaminan, y lo demostraremos).

    | Variante | Qué es |
    |---|---|
    | `manual` | Hooks con OpenTelemetry (`invoke_agent` + `chat` + `execute_tool`), reloj de pared |
    | `openlit` · `openllmetry` · `official` | **Solo** la librería (`openlit.init()`, `Traceloop.init()`, `OpenAIInstrumentor().instrument()`) |
    | `hybrid_*` | Spans manuales `invoke_agent` + `execute_tool`, y el span `chat` lo pone la librería |
    | `openlit_decorated` · `openllmetry_decorated` | La librería + sus decoradores sobre `agent.run` y las herramientas |

    Si tienes las librerías instaladas, `lab.run_variant(...)` re-ejecuta cualquiera (≈ 3 s); para no esperar usamos el conjunto pregrabado y **verificamos** que coincide con una ejecución en vivo.
    """)
    code('''
if all(LIBS.values()):
    live_check = {v: lab.run_variant(v, n=24, seed=42) for v in ("official", "hybrid_official")}
    for v, d in live_check.items():
        rec = LAB[v]
        same = (len(d["spans"]) == len(rec["spans"]) and collections.Counter(s["name"] for s in d["spans"]) == collections.Counter(s["name"] for s in rec["spans"]))
        print(f"{v:16s} en vivo: {len(d['spans'])} spans · pregrabado: {len(rec['spans'])} spans · mismos nombres de span: {same}")
else:
    print("Librerías no instaladas: se usa solo el conjunto pregrabado (mismo esquema).")
print()
print("Estados de los 24 tickets (idénticos en todas las variantes):", dict(collections.Counter(r["status"] for r in LAB["manual"]["results"])))
print("Fallos de herramienta/bucle inyectados:", dict(collections.Counter(r["injected_faults"] for r in LAB["manual"]["results"] if r["injected_faults"])))
''')

    md("""
    ## 3.1 · Experimento 1 — ¿qué forma tienen las trazas?

    Definimos unas métricas de análisis (las reutilizarás en el proyecto) y miramos el **mismo ticket** en tres estrategias. Un ticket del agente debería ser **una traza** con `invoke_agent` en la raíz.
    """)
    code(HELPERS)
    code('''
rows = []
for v in ["manual", "openlit", "openllmetry", "official", "hybrid_openlit", "hybrid_openllmetry", "hybrid_official", "openlit_decorated", "openllmetry_decorated"]:
    rows.append({"variante": v, **trace_stats(LAB[v]["spans"])})
TS = pd.DataFrame(rows).set_index("variante")
print("Tickets ejecutados:", len(LAB["manual"]["results"]))
TS.round(2)
''')
    code('''
# Un ticket con herramientas, visto de tres maneras
tk = next(r for r in LAB["manual"]["results"] if r["n_tool_calls"] >= 1 and r["status"] == "ok")["ticket_id"]
def spans_of_ticket(run, tid):
    t_of = ticket_of_trace(run["spans"])
    return [s for s in run["spans"] if t_of.get(s["trace_id"]) == tid]

fig = plt.figure(figsize=(15, 8)); gs = fig.add_gridspec(2, 2, hspace=0.45, wspace=0.28)
ax = fig.add_subplot(gs[0, 0]); viz.waterfall(spans_of_ticket(LAB["manual"], tk), ax=ax, title=f"MANUAL · ticket {tk}: UNA traza")
ax = fig.add_subplot(gs[0, 1]); viz.waterfall(spans_of_ticket(LAB["hybrid_official"], tk), ax=ax, title=f"HÍBRIDO (manual + chat oficial) · ticket {tk}: UNA traza")
# auto-only: los primeros spans de chat en el tiempo; cada uno es su propia traza
ax = fig.add_subplot(gs[1, 0])
chats = sorted([s for s in LAB["official"]["spans"] if is_chat(s)], key=lambda s: s["start_unix_nano"])[:8]
t0 = chats[0]["start_unix_nano"]; cols = plt.cm.tab10.colors
for i, s in enumerate(chats):
    ax.barh(i, (s["end_unix_nano"] - s["start_unix_nano"]) / 1e6, left=(s["start_unix_nano"] - t0) / 1e6, color=cols[i % 10])
    ax.text((s["end_unix_nano"] - t0) / 1e6 + 2, i, f"traza {s['trace_id'][:6]}", va="center", fontsize=8)
ax.invert_yaxis(); ax.set_xlabel("ms desde el primer span"); ax.set_yticks(range(len(chats))); ax.set_yticklabels([f"chat #{i+1}" for i in range(len(chats))])
ax.set_title("SOLO LIBRERÍA (official) · 8 primeras llamadas: cada una en SU traza", loc="left")
ax = fig.add_subplot(gs[1, 1])
order = list(TS.index); ax.barh(order, TS.n_traces, color=[viz.PALETTE["traces"] if v in ("manual",) or v.startswith(("hybrid", "openlit_dec", "openllmetry_dec")) else viz.PALETTE["error"] for v in order])
ax.axvline(len(LAB["manual"]["results"]), color="k", ls="--"); ax.text(len(LAB["manual"]["results"]) + 1, 0.2, "24 tickets", fontsize=9)
ax.invert_yaxis(); ax.set_xlabel("nº de trazas generadas"); ax.set_title("Trazas por estrategia (24 tickets)", loc="left")
plt.show()
''')
    md(observe("""
    - **Manual e híbrido:** 1 traza por ticket (24 trazas) con raíz `invoke_agent`, los `chat` y las herramientas como hijos.
    - **Solo librería:** **66 trazas para 24 tickets** — cada llamada al LLM abre su propia traza, sin ticket ni herramientas. Es el hallazgo central del módulo: *sin un span padre del lado del agente, el auto-instrumentado produce spans huérfanos.*
    - En rojo: el recuento de trazas que no corresponde a ningún ticket. Con `openlit` hay además **66 spans `POST` extra** (instrumentó `httpx` sin que se lo pidieras).
    - Los decoradores (`*_decorated`) recuperan **una traza por ticket (24)**, pero con nombres propios (`run`, `supportops-agent.agent`, `get_order`) en lugar de `invoke_agent`/`execute_tool`, y sin un atributo `ticket.id` (lo veremos en el experimento 3).
    """))

    md("""
    ## 3.2 · Experimento 2 — ¿qué atributos lleva el span `chat`?

    Comparamos la cobertura de 12 atributos esperados (los de la spec que SupportOps usa más los de dominio) en los spans `chat` correctos, incluyendo la **instrumentación de referencia** del módulo 03-05 (`OTelInstrumentor`) ejecutada en este mismo notebook.
    """)
    code('''
# Referencia: OTelInstrumentor (módulos 03-05) en memoria sobre 24 tickets con el LLM mock
tel = setup_telemetry("ref-manual", mode="memory", set_global=False)
ref_agent = SupportAgent(instrumentor=OTelInstrumentor(tel))
run_tickets(ref_agent, generate_tickets(24, 42, duration_s=600))
tel.force_flush(); REF_SPANS = tel.span_records(); tel.shutdown()

cols = {"referencia\\n(OTelInstrumentor)": REF_SPANS, "manual\\n(lab)": LAB["manual"]["spans"], "openlit": LAB["openlit"]["spans"],
        "openllmetry": LAB["openllmetry"]["spans"], "official": LAB["official"]["spans"], "híbrido\\n(official)": LAB["hybrid_official"]["spans"]}
COV = pd.DataFrame({k: attr_coverage(v) for k, v in cols.items()})
fig, ax = plt.subplots(figsize=(11, 5.2))
im = ax.imshow(COV.values, cmap="Greens", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(COV.shape[1])); ax.set_xticklabels(COV.columns, fontsize=9); ax.set_yticks(range(COV.shape[0])); ax.set_yticklabels(COV.index, fontsize=9)
for i in range(COV.shape[0]):
    for j in range(COV.shape[1]):
        ax.text(j, i, f"{COV.values[i, j]:.0%}", ha="center", va="center", fontsize=8.5, color="white" if COV.values[i, j] > 0.6 else "black")
ax.grid(False); ax.set_title("Cobertura de atributos en spans `chat` correctos"); plt.colorbar(im, label="fracción de spans"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Los 8 atributos **de la spec** que una llamada al modelo puede conocer (`gen_ai.*`: operación, proveedor, modelo, respuesta, *finish reasons*, tokens) están al 100 % en las tres librerías: ahí es donde la auto-instrumentación aporta valor sin esfuerzo.
    - Los de **dominio** solo existen donde tú los pones: `supportops.step/attempt` en la referencia y el manual (el índice del paso lo conoce el bucle, no el cliente), `gen_ai.conversation.id` solo en la referencia, y `supportops.ticket.id` **en ninguna columna a nivel de `chat`** (en las manuales vive en el span `invoke_agent`). Para agrupar «tokens por ticket» en Tempo hace falta ese atributo en el propio span: lo arreglaremos en la sección 4 con un `SpanProcessor`.
    - Los atributos *esperados* no son los únicos: la fila de abajo cuenta cuántos atributos propios añade cada librería.
    """))
    code('''
spec_prefix = ("gen_ai.", "error.", "server.", "supportops.")
def own_attrs(spans):
    names = collections.Counter()
    for s in spans:
        if is_chat(s):
            for k in s["attributes"]:
                if not k.startswith(spec_prefix):
                    names[k] += 1
    return sorted(names)
rows = [{"variante": v, "atributos/span chat": np.mean([len(s["attributes"]) for s in LAB[v]["spans"] if is_chat(s)]).round(1),
         "KB atributos / ticket": round(kb_per_ticket(LAB[v]), 1), "propios (fuera de gen_ai./error./server.)": ", ".join(own_attrs(LAB[v]["spans"])) or "—"}
        for v in ("manual", "openlit", "openllmetry", "official")]
pd.set_option("display.max_colwidth", 140); pd.DataFrame(rows).set_index("variante")
''')
    md("""
    Dos detalles que el heatmap no muestra pero afectan a las consultas:

    1. **Valores distintos para el mismo concepto.** `gen_ai.response.finish_reasons` vale `['tool_calls']` en OpenLIT y en la oficial, y `['tool_call']` en OpenLLMetry (y en `OTelInstrumentor`). Una consulta `{ span.gen_ai.response.finish_reasons = "tool_calls" }` dejaría fuera a un servicio con otra librería.
    2. **Ruido que no pediste.** OpenLIT añade `service.name`, `deployment.environment` y `telemetry.sdk.name` como atributos de *span* (ya están en el *resource*), y atributos de valor por defecto como `gen_ai.request.seed = 0` o `gen_ai.request.user = ""`; datos que cuestan almacenamiento en Tempo y no responden preguntas.
    """)

    md("""
    ## 3.3 · Experimento 3 — ¿explican los fallos y el gasto por ticket?

    Dos preguntas operativas: (1) de los tickets que **acabaron mal** (`error`, `max_steps`, `degraded`), ¿en qué fracción puedes llegar a una traza con un span ERROR? (2) ¿puedes calcular los **tokens por ticket** sumando spans `chat`? El resultado verdadero lo conocemos: viene de `AgentResult`.
    """)
    code('''
rows = []
for v in ["manual", "openlit", "openllmetry", "official", "hybrid_openlit", "hybrid_openllmetry", "hybrid_official",
          "openlit_decorated", "openllmetry_decorated", "enrich:openlit", "enrich:openllmetry", "enrich:official"]:
    fa, n_bad = failure_attribution(LAB[v])
    rows.append({"variante": v, "fallos atribuibles": fa, "tokens por ticket correctos": token_attribution(LAB[v])})
ATT = pd.DataFrame(rows).set_index("variante")
fig, ax = plt.subplots(figsize=(12, 4.6)); x = np.arange(len(ATT)); w = 0.38
ax.bar(x - w/2, ATT["fallos atribuibles"] * 100, w, label="fallos del agente atribuibles a un ticket (con span ERROR)", color=viz.PALETTE["error"])
ax.bar(x + w/2, ATT["tokens por ticket correctos"] * 100, w, label="tickets con tokens agregados correctamente desde spans", color=viz.PALETTE["metrics"])
ax.set_xticks(x); ax.set_xticklabels(ATT.index, rotation=35, ha="right"); ax.set_ylabel("%"); ax.set_ylim(0, 110); ax.legend(loc="upper left", fontsize=9)
ax.set_title(f"¿Se puede explicar un ticket con la telemetría? (n_fallos = {failure_attribution(LAB['manual'])[1]})"); plt.tight_layout(); plt.show()
ATT.round(2)
''')
    md(observe("""
    - **Solo librería = 0 %** en ambas: los spans existen y tienen tokens, pero **ningún atributo dice a qué ticket pertenecen**; no se puede ni sumar el coste por ticket ni enlazar un fallo con su causa. Los **decoradores también dan 0 %**: construyen una traza por ticket, pero sin `ticket.id` (habría que añadirlo, p. ej. con `Traceloop.set_association_properties`).
    - Con `enrich:*` (la técnica de la sección 4: un `SpanProcessor` que copia el ticket activo) los tokens por ticket pasan a **100 %**, pero los fallos atribuibles solo suben a **60 %**: ahora se conoce el ticket de cada `chat`, pero los fallos de **herramienta** y de bucle no generan ningún span en una librería de cliente (las 2 de 5 averías restantes).
    - Solo las variantes con spans de **agente y herramienta** con el ticket declarado (manual e híbridos) llegan al 100 % en ambas métricas.
    """))

    md("""
    ## 3.4 · Experimento 4 — privacidad: ¿qué se queda en el atributo?

    El 25 % de los tickets de este lote lleva un **correo y un teléfono sintéticos** en el texto. Contamos en cuántos *spans* aparece un correo en algún atributo o evento, con cada librería en su **configuración por defecto** y con la captura de contenido **desactivada** con el interruptor documentado de cada una.
    """)
    code('''
variants = ["openlit", "openllmetry", "official", "hybrid_openlit", "hybrid_openllmetry", "hybrid_official", "openlit_decorated", "openllmetry_decorated"]
priv = pd.DataFrame({"por defecto": [pii_spans(LAB[v]["spans"]) for v in variants],
                     "contenido desactivado": [pii_spans(LAB["off:" + v]["spans"]) for v in variants],
                     "KB/ticket por defecto": [kb_per_ticket(LAB[v]) for v in variants],
                     "KB/ticket desactivado": [kb_per_ticket(LAB["off:" + v]) for v in variants]}, index=variants)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 4.4))
x = np.arange(len(variants)); w = 0.4
a1.bar(x - w/2, priv["por defecto"], w, color=viz.PALETTE["error"], label="configuración por defecto"); a1.bar(x + w/2, priv["contenido desactivado"], w, color=viz.PALETTE["ok"], label="captura de contenido desactivada")
a1.set_xticks(x); a1.set_xticklabels(variants, rotation=40, ha="right", fontsize=8); a1.set_ylabel("spans con un correo (PII)"); a1.legend(fontsize=8); a1.set_title("Exposición de PII en atributos de span")
a2.bar(x - w/2, priv["KB/ticket por defecto"], w, color=viz.PALETTE["metrics"], label="por defecto"); a2.bar(x + w/2, priv["KB/ticket desactivado"], w, color=viz.PALETTE["logs"], label="desactivado")
a2.set_xticks(x); a2.set_xticklabels(variants, rotation=40, ha="right", fontsize=8); a2.set_ylabel("KB de atributos por ticket"); a2.legend(fontsize=8); a2.set_title("Volumen de atributos")
plt.tight_layout(); plt.show()
print("Con captura activada explícitamente en la oficial:", pii_spans(LAB["on:official"]["spans"]), "spans con PII")
priv.round(1)
''')
    md(observe("""
    - **Por defecto**, OpenLIT y OpenLLMetry guardan el prompt y la respuesta completos en `gen_ai.input.messages` / `gen_ai.output.messages`: el correo del cliente acaba en el atributo de **5 spans**. La instrumentación oficial **no** captura contenido hasta que se lo pides (con `span_only` también expone 5 spans).
    - Al desactivar el contenido (`openlit.init(capture_message_content=False)` o `TRACELOOP_TRACE_CONTENT=false`), el PII desaparece y el volumen de atributos cae entre un 50 % y un 85 %: **el contenido es la mayor parte de los bytes**.
    - **La trampa:** `@openlit.trace` guarda `function.args`/`function.kwargs` *aunque* hayas desactivado el contenido (3 spans con PII en `off:openlit_decorated`), mientras que los decoradores de OpenLLMetry respetan `TRACELOOP_TRACE_CONTENT` (0). Los interruptores globales no cubren todo lo que añadas tú.
    """))
    md("""
    | Librería | Interruptor para desactivar el contenido | Por defecto |
    |---|---|---|
    | Oficial (`genai-openai`) | `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` = `no_content` · `span_only` · `event_only` · `span_and_event` | `no_content` |
    | OpenLLMetry | `TRACELOOP_TRACE_CONTENT=false` (también afecta a los decoradores) | `true` |
    | OpenLIT | `openlit.init(capture_message_content=False)` o `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=false` (el código solo reconoce el valor `false`). **No** afecta a `@openlit.trace` | `True` |

    La redacción real de datos personales (en vez de «todo o nada») se hace en el Collector: módulo 20.
    """)

    md("""
    ## 3.5 · Experimento 5 — trampas de operación

    Tres comportamientos que no se ven en la documentación de inicio rápido y que medimos con el servidor falso (que cuenta cuántas peticiones recibe de verdad):
    """)
    code('''
fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(15, 4.4))
# (a) doble instrumentación
n_req = LAB["both"]["meta"]["server_requests"]
vals = [n_req, sum(is_chat(s) for s in LAB["official"]["spans"]), sum(is_chat(s) for s in LAB["both"]["spans"])]
a1.bar(["peticiones\\nreales", "spans chat\\n(solo official)", "spans chat\\n(openlit + official)"], vals, color=[viz.PALETTE["neutral"], viz.PALETTE["traces"], viz.PALETTE["error"]])
for i, v in enumerate(vals): a1.text(i, v + 1, str(v), ha="center")
a1.set_title("(a) Dos librerías a la vez: cada llamada, 2 spans", loc="left", fontsize=10)
# (b) reintentos ocultos del SDK
r = LAB["retries2:official"]; ro = LAB["retries2:openlit"]
vals = [r["meta"]["server_requests"], sum(is_chat(s) for s in r["spans"]), sum(s["name"] == "POST" for s in ro["spans"])]
a2.bar(["peticiones\\nreales", "spans chat\\n(official)", "spans HTTP POST\\n(openlit, httpx)"], vals, color=[viz.PALETTE["neutral"], viz.PALETTE["traces"], viz.PALETTE["metrics"]])
for i, v in enumerate(vals): a2.text(i, v + 1, str(v), ha="center")
a2.set_title("(b) El SDK reintenta por dentro (max_retries=2)", loc="left", fontsize=10)
# (c) streaming
def stream_out(key):
    sp = [s for s in LAB[key]["spans"] if is_chat(s)][-2:]
    return [s["attributes"].get("gen_ai.usage.output_tokens") for s in sp]   # [sin include_usage, con include_usage]
names = ["openlit", "openllmetry", "official"]; sv = {n: stream_out("stream:" + n) for n in names}
xx = np.arange(3); w = 0.38
a3.bar(xx - w/2, [sv[n][0] if sv[n][0] is not None else 0 for n in names], w, color=viz.PALETTE["error"], label="sin include_usage")
a3.set_ylim(0, 36)
a3.bar(xx + w/2, [sv[n][1] or 0 for n in names], w, color=viz.PALETTE["ok"], label="con include_usage")
for i, n in enumerate(names):
    a3.text(i - w/2, 1, "0 (falso)" if sv[n][0] == 0 else ("ausente" if sv[n][0] is None else str(sv[n][0])), ha="center", fontsize=8.5)
a3.set_xticks(xx); a3.set_xticklabels(names); a3.set_ylabel("gen_ai.usage.output_tokens"); a3.legend(fontsize=8); a3.set_title("(c) Streaming: tokens de salida", loc="left", fontsize=10)
plt.tight_layout(); plt.show()
print("SDK con max_retries=2 y 30 % de 503: peticiones reales", r["meta"]["server_requests"], "· spans chat", sum(is_chat(s) for s in r["spans"]))
''')
    md(observe("""
    - **(a)** Con `openlit` y la oficial instrumentando a la vez, **132 spans `chat` para 66 peticiones**: se duplican las duraciones, los tokens se suman dos veces en cualquier agregado y el coste sale ×2. Una sola librería por proveedor.
    - **(b)** Con el `max_retries=2` por defecto del cliente de OpenAI, el servidor recibió **86 peticiones** pero hay **59 spans `chat`**: los reintentos del SDK ocurren *dentro* de un `create()` y los ve un span HTTP (OpenLIT, porque instrumenta `httpx`), no el span `chat`. En SupportOps ponemos `max_retries=0` y reintentamos en el agente para que cada intento sea un span con su `supportops.attempt`.
    - **(c)** En *streaming*, los tokens de salida solo existen si pides `stream_options={"include_usage": True}`. Sin ello OpenLIT escribe **`0`** (un dato falso que parece verdadero) y las otras dos **omiten** el atributo (un dato ausente que al menos se ve). Un `0` falso es peor que un hueco: contamina medias y costes.
    """))

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ---
    # 4 · Cómo extenderlas

    Hay cuatro técnicas, de la más recomendable a la más peligrosa. Todas funcionan con las tres librerías porque se apoyan en OpenTelemetry, no en la librería.

    ## 4.1 · Híbrido: spans manuales de agente + `chat` automático
    Conserva los *hooks* `agent_run` y `tool_call` del módulo 03-05 y **apaga solo `llm_call`** (el `chat` lo pone la librería, que se cuelga del span `invoke_agent` actual). Este es el código del laboratorio:
    """)
    code('''
print(inspect.getsource(lab.make_wall_instrumentor)[:2400])
''')
    md("""
    En la práctica el cambio respecto a `OTelInstrumentor` es una línea (no abrir span en `llm_call`). El resultado es el de `hybrid_*` arriba: **una traza por ticket (24)**, con herramientas, y spans `chat` con detalle de la librería.

    ## 4.2 · Decoradores de la propia librería
    - **OpenLLMetry:** `@agent(name=...)`, `@workflow`, `@task`, `@tool`; guardan `traceloop.entity.input/output` (respetan `TRACELOOP_TRACE_CONTENT`).
    - **OpenLIT:** `@openlit.trace` y `with openlit.start_trace("nombre")`; el span es `CLIENT` y guarda `function.args` siempre (medido arriba).
    - Ventaja: una línea por función. Inconvenientes: nombres propios (`run`, `get_order`) en vez de `execute_tool get_order`; atributos fuera de la spec; no atribuyen fallos de dominio (`supportops.status`).

    ```python
    from traceloop.sdk.decorators import agent, tool
    tool_fn = tool(name="get_order")(get_order)        # span «get_order.tool» (traceloop.span.kind=tool)
    run = agent(name="supportops-agent")(agent_obj.run)  # span «supportops-agent.agent»
    ```

    ## 4.3 · `SpanProcessor.on_start`: enriquecer **todos** los spans
    Un `SpanProcessor` registrado en el `TracerProvider` recibe **todos** los spans, también los de las librerías. En `on_start` el span todavía es mutable: copiamos el ticket activo (guardado en un `ContextVar` por un *hook* sin spans).
    """)
    code('''
print(inspect.getsource(lab.make_enrich_processor))
print(inspect.getsource(lab.make_context_setter))
''')
    code('''
rows = []
for v in ["openlit", "openllmetry", "official"]:
    for tag, key in (("sin procesador", v), ("con TicketContextProcessor", "enrich:" + v)):
        run = LAB[key]; chats = [s for s in run["spans"] if is_chat(s)]
        rows.append({"librería": v, "configuración": tag, "chat con ticket.id": f"{sum('supportops.ticket.id' in s['attributes'] for s in chats)}/{len(chats)}",
                     "tokens por ticket correctos": f"{token_attribution(run):.0%}", "trazas": trace_stats(run['spans'])['n_traces']})
pd.DataFrame(rows).set_index(["librería", "configuración"])
''')
    md("""
    Con **tres líneas** cualquier librería pasa de 0 % a 100 % en «tokens por ticket». Observa lo que **no** cambia: sigue habiendo 66 trazas; el procesador pone el *atributo* pero no une los spans en un árbol. Para eso hace falta un span padre real (híbrido).

    ## 4.4 · ¿Y la redacción? No en `on_end`
    La tentación: un procesador que, al terminar el span, reemplace el correo por `[email]`. En el SDK de Python **`on_end` recibe un `ReadableSpan` inmutable**:
    """)
    code('''
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

class RedactorIngenuo(SpanProcessor):
    def on_start(self, span, parent_context=None):
        span.set_attribute("añadido.en.on_start", "sí")          # funciona: el span aún está abierto
    def on_end(self, span):
        try:
            span.set_attribute("gen_ai.input.messages", "[redactado]")
        except AttributeError as e:
            print("on_end NO puede modificar el span ->", e)

mem = InMemorySpanExporter(); tp = TracerProvider()
tp.add_span_processor(RedactorIngenuo()); tp.add_span_processor(SimpleSpanProcessor(mem))
with tp.get_tracer("demo").start_as_current_span("chat demo") as sp:
    sp.set_attribute("gen_ai.input.messages", "mi correo es ana@example.com")
print(dict(mem.get_finished_spans()[0].attributes))
''')
    md("""
    El PII sigue en el atributo. Las vías que sí funcionan, de mejor a peor:
    1. **No capturarlo** (interruptores de la sección 3.4).
    2. **Redactar en el Collector** con los procesadores `redaction`/`transform` (módulo 20): una sola política para todos los lenguajes y librerías.
    3. Redactar **antes** de que el atributo se escriba (`OTelInstrumentor(redact=...)`, como en el módulo 04).
    4. Un `SpanExporter` que envuelva al real y reescriba los `ReadableSpan` antes de exportar: posible, pero toca privados del SDK y se rompe en cada actualización.
    """)

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ---
    # 5 · Coste: dependencias, arranque y sobrecoste

    Medimos en entornos virtuales limpios (Python 3.13, Linux x86-64, oct-2026) cuánto añade cada opción sobre la base «SDK de OpenTelemetry + exportador OTLP/HTTP + `openai`»:
    """)
    code('''
FOOT = pd.DataFrame({   # medido el 15-oct-2026 con `pip install` en venvs limpios (paquetes = `pip list`, MB = site-packages)
    "paquetes": {"base (SDK+OTLP+openai)": 29, "+ oficial genai-openai": 34, "+ openlit": 63, "+ traceloop-sdk": 90},
    "MB en disco": {"base (SDK+OTLP+openai)": 67, "+ oficial genai-openai": 71, "+ openlit": 141, "+ traceloop-sdk": 111},
    "init() s": {"base (SDK+OTLP+openai)": 1.0, "+ oficial genai-openai": 1.5, "+ openlit": 3.5, "+ traceloop-sdk": 3.2},
    "mediana ms/llamada": {"base (SDK+OTLP+openai)": 46.9, "+ oficial genai-openai": 47.9, "+ openlit": 48.0, "+ traceloop-sdk": 48.0},
})
RUN_BENCH = all(LIBS.values()) and not FAST_DEV_RUN          # con FAST_DEV_RUN=False se re-mide en tu máquina (~1 min)
if RUN_BENCH:
    for name, lib in zip(FOOT.index, [None, "official", "openlit", "openllmetry"]):
        b = lab.bench_variant(lib, calls=150); FOOT.loc[name, ["init() s", "mediana ms/llamada"]] = [round(b["init_s"], 1), round(b["median_ms"], 1)]
fig, axs = plt.subplots(1, 4, figsize=(16, 3.8))
for ax, col, color in zip(axs, FOOT.columns, [viz.PALETTE["traces"], viz.PALETTE["metrics"], viz.PALETTE["logs"], viz.PALETTE["profiles"]]):
    ax.bar(range(len(FOOT)), FOOT[col], color=color); ax.set_xticks(range(len(FOOT))); ax.set_xticklabels(["base", "oficial", "openlit", "traceloop"], fontsize=9)
    ax.set_title(col, fontsize=10)
    for i, v in enumerate(FOOT[col]): ax.text(i, v, f"{v:g}", ha="center", va="bottom", fontsize=8)
plt.suptitle("Huella de cada opción (" + ("medido ahora" if RUN_BENCH else "instantánea medida el 15-oct-2026") + ")", y=1.02); plt.tight_layout(); plt.show()
FOOT
''')
    md(observe("""
    - **Dependencias:** la oficial añade 5 paquetes; OpenLIT 34 (sobre todo porque trae las instrumentaciones de `httpx`, `requests`, FastAPI… y las activa todas); `traceloop-sdk` 61 (un paquete por proveedor y base de datos vectorial).
    - **Arranque:** `init()` de OpenLIT/OpenLLMetry tarda ≈ 2 s más que la base (importan y parchean decenas de módulos). Relevante en *serverless* y en tests.
    - **Sobrecoste por llamada:** ≈ +1 ms sobre 47 ms contra un servidor local: el coste no es el problema; **el volumen de datos sí** (sección 3.4) y la superficie de dependencias.
    - Nota de seguridad: OpenLIT descarga `pricing.json` de GitHub al hacer `init()` salvo que le pases `pricing_json="ruta/local.json"`; en un entorno sin salida a internet o con *egress* controlado, configúralo.
    """))

    # ------------------------------------------------------------------------------------------------ 6
    md("""
    ---
    # 6 · La decisión: una matriz ponderada y su sensibilidad

    Convertimos lo medido en puntuaciones 1-5 (las cuantitativas se calculan; las cualitativas se justifican) y ponderamos por perfil de equipo. Las opciones: **manual** (módulos 03-05), **OpenLIT**, **OpenLLMetry**, **oficial** (solo librería) e **híbrido** (manual agente/herramientas + `chat` oficial).
    """)
    code('''
OPTS = ["manual", "openlit", "openllmetry", "official", "hybrid_official"]
def scale(values: dict, higher_better=True):
    """Normaliza a 1-5 linealmente entre el peor y el mejor valor."""
    lo, hi = min(values.values()), max(values.values())
    return {k: (5.0 if hi == lo else 1 + 4 * ((v - lo) / (hi - lo) if higher_better else (hi - v) / (hi - lo))) for k, v in values.items()}
extra_pkgs = {"manual": 0, "openlit": 34, "openllmetry": 61, "official": 5, "hybrid_official": 5}      # medido en la sección 5
measured = {
    "Contexto de agente (trazas por ticket + tokens por ticket)": scale({o: (trace_stats(LAB[o]["spans"])["rooted_share"] + token_attribution(LAB[o])) / 2 for o in OPTS}),
    "Privacidad por defecto (spans con PII)": scale({o: pii_spans(LAB[o]["spans"]) for o in OPTS}, higher_better=False),
    "Economía de datos (KB por ticket)": scale({o: kb_per_ticket(LAB[o]) for o in OPTS}, higher_better=False),
    "Huella de dependencias": scale(extra_pkgs, higher_better=False),
}
qualitative = {   # juicio razonado (1-5), con la fuente de cada cifra
    "Amplitud de proveedores/frameworks": {"manual": 1, "openlit": 5, "openllmetry": 4, "official": 3, "hybrid_official": 3},
    "Esfuerzo inicial (menos = mejor)": {"manual": 1, "openlit": 5, "openllmetry": 5, "official": 4, "hybrid_official": 3},
    "Riesgo de gobernanza/estabilidad": {"manual": 5, "openlit": 3, "openllmetry": 3, "official": 4, "hybrid_official": 4},
}
JUSTIF = pd.DataFrame({
    "criterio": list(qualitative),
    "por qué": ["OpenLIT anuncia 70+ integraciones (README); OpenLLMetry instrumenta ≈ 16 proveedores + BBDD vectoriales (README); la oficial publica ≈ 12 paquetes; manual = lo que escribas",
                "1 línea (`init()`) frente a ≈ 80 líneas de hooks propios (módulo 03-05); el híbrido añade los hooks de agente/herramienta",
                "manual = tú controlas el cambio; oficial = proyecto OpenTelemetry (beta, semconv en Development); OpenLIT/OpenLLMetry = proyectos de una empresa, con cadencia irregular y, en el caso de Traceloop, integración en ServiceNow (2026)"]})
SC = pd.DataFrame({**measured, **qualitative}).loc[OPTS]
print("Puntuaciones 1-5 (cuantitativas calculadas de los datos del laboratorio):"); display(SC.round(1)); display(JUSTIF.set_index("criterio"))
''')
    code('''
PROFILES = {   # pesos por criterio, en el orden de SC.columns (se normalizan)
    "SupportOps (agente propio, 1 proveedor, datos sensibles)": [5, 5, 2, 2, 2, 3, 3],
    "Plataforma interna (muchos frameworks y equipos)":          [3, 3, 2, 3, 5, 4, 3],
    "Prototipo de 1 día":                                         [1, 1, 1, 1, 3, 5, 1],
}
rank = {}
for name, w in PROFILES.items():
    w = np.array(w, float); w /= w.sum(); s = SC.values @ w; rank[name] = pd.Series(s, index=OPTS).sort_values(ascending=False)
RANK = pd.DataFrame(rank).round(2)
# sensibilidad: 20 000 vectores de pesos aleatorios (Dirichlet); ¿con qué frecuencia gana cada opción?
rng = np.random.default_rng(42); W = rng.dirichlet(np.ones(SC.shape[1]), 20000); wins = collections.Counter(np.array(OPTS)[(SC.values @ W.T).argmax(axis=0)])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(15, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
im = a1.imshow(SC.values, cmap="RdYlGn", vmin=1, vmax=5, aspect="auto"); a1.set_xticks(range(SC.shape[1])); a1.set_xticklabels([c.split(" (")[0] for c in SC.columns], rotation=25, ha="right", fontsize=8.5)
a1.set_yticks(range(len(OPTS))); a1.set_yticklabels(OPTS)
for i in range(SC.shape[0]):
    for j in range(SC.shape[1]): a1.text(j, i, f"{SC.values[i, j]:.1f}", ha="center", va="center", fontsize=9)
a1.grid(False); a1.set_title("Matriz de puntuaciones (1 = peor, 5 = mejor)")
a2.bar(OPTS, [100 * wins.get(o, 0) / 20000 for o in OPTS], color=viz.PALETTE["traces"]); a2.set_ylabel("% de pesos aleatorios en que gana"); a2.set_title("Sensibilidad: ¿qué tan robusta es la decisión?")
a2.tick_params(axis="x", rotation=25); plt.tight_layout(); plt.show()
display(RANK)
''')
    md(observe("""
    - Para **SupportOps** (agente propio, un proveedor, PII) gana el **híbrido** (4,35) por delante del manual (4,07): ambos tienen el contexto de agente, pero el híbrido mantiene menos código propio. Las dos plataformas pierden por *contexto de agente* y *privacidad por defecto*.
    - Para una **plataforma interna** con muchos frameworks pesa más la amplitud, pero el híbrido sigue ganando (4,02 frente a 3,70 de la oficial): la amplitud de OpenLIT/OpenLLMetry no compensa que sus spans queden huérfanos y con contenido por defecto, **salvo** que añadas el `SpanProcessor` de contexto y apagues el contenido (que es justo el híbrido).
    - Para un **prototipo de un día** gana OpenLIT (3,81), pero por muy poco sobre la oficial (3,74): 1 línea y listo. Con datos reales, apaga el contenido.
    - **Sensibilidad:** con pesos aleatorios el híbrido gana en ≈ 57 % de los casos, la oficial en ≈ 22 %, el manual en ≈ 17 % y OpenLIT en ≈ 4 %. Ninguna opción gana siempre, y que el híbrido gane en una mayoría amplia es la evidencia de que la recomendación no depende de haber acertado con los pesos. OpenLLMetry no gana en ningún caso con estos criterios (la huella de 61 paquetes y la captura de contenido por defecto pesan).
    """))

    md(box("idea", "Recomendación para SupportOps", """
    **Híbrido:** mantener nuestros hooks de **agente y herramienta** (son semántica del dominio: ticket, estado, `execute_tool`) y dejar el span `chat` a la instrumentación oficial *si* llamamos a un SDK con soporte (OpenAI, Anthropic…); si el `chat` ya lo emite nuestro `OTelInstrumentor` (LLM propio o *mock*) no hay nada que automatizar.
    En cualquier caso: contenido **apagado por defecto**, una sola librería por proveedor, `max_retries=0` en el cliente, `include_usage` en *streaming*, versiones fijadas y una prueba de contrato sobre los nombres de atributos (proyecto).
    """))

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ---
    ## 🏭 En producción

    - **Grafana Cloud AI Observability** se construye sobre el SDK de OpenLIT: su documentación indica `pip install openlit` + variables `OTEL_*` + `openlit.init()` y trae cinco *dashboards* (GenAI, Evaluations, VectorDB, MCP, GPU). Es el camino de menor esfuerzo si tu destino es Grafana Cloud; en un stack propio (este curso) la misma telemetría llega vía Collector a Tempo/Loki.
    - **Datadog** anunció (1-dic-2025) soporte nativo de las GenAI semantic conventions (v1.37+): puedes instrumentar **una vez** con OpenTelemetry y enviar a su producto sin SDK propio. La consecuencia estratégica es la misma para cualquier proveedor: **emite semconv estándar y evita atributos propietarios** para no quedar atado.
    - **Patrón de las empresas grandes:** una *librería interna de observabilidad* fina (el equivalente de nuestro `setup_telemetry` + instrumentor) que fija versiones, apaga contenido, añade atributos de dominio y envuelve la instrumentación de terceros. Los equipos de producto no llaman a `openlit.init()` directamente.
    - **Gobernanza del Collector:** como el contenido puede colarse por cualquier librería, la política de redacción y de eliminación de atributos (`transform`/`redaction`/`attributes`) se aplica en el Collector central (módulo 20), no en cada servicio.
    """)

    md("""
    ## 🧠 Secretos de la élite

    1. **Solo-auto = trazas huérfanas.** Medido: 66 trazas para 24 tickets y 0 % de tokens atribuibles. Sin un span padre del lado del agente (o un `SpanProcessor` + `ContextVar`), la telemetría automática no responde a «¿cuánto cuesta este ticket?». *Por qué importa:* es la pregunta de FinOps del módulo 13.
    2. **Los valores por defecto son decisiones de privacidad.** OpenLIT y OpenLLMetry capturan prompts y respuestas por defecto; la spec GenAI indica que las instrumentaciones **no deberían** hacerlo sin opt-in. Verifica el valor por defecto de **cada versión** que fijes: es lo primero que cambia en un *changelog*.
    3. **Los interruptores globales no cubren lo que añades tú.** `@openlit.trace` guarda `function.args` aunque desactives el contenido (medido: 3 spans con PII). Audita con un test que busque PII sintético en los spans exportados (el del proyecto).
    4. **Una librería por proveedor.** Dos instrumentaciones sobre el mismo cliente duplican spans (132 `chat` para 66 llamadas) y, por tanto, tokens y coste; lo hace fácil un `pip install` transitivo. Comprueba el número de spans `chat` frente a las peticiones reales del servidor.
    5. **El `0` falso es peor que el hueco.** En *streaming* sin `include_usage`, OpenLIT escribe `output_tokens = 0`. Una media de tokens o un coste calculado con esos ceros sale sesgado a la baja sin ningún error. Pide siempre `include_usage` y trata los tokens ausentes como `NULL`.
    6. **Reintentos del SDK = tráfico invisible.** Con `max_retries=2` (valor por defecto del cliente de OpenAI) hubo 86 peticiones y 59 spans `chat`: el proveedor te factura/limita por las 86. Pon `max_retries=0` y reintenta tú, con un span por intento (`supportops.attempt`).
    7. **La auto-instrumentación se activa por «lo que hay instalado».** OpenLIT instrumentó `httpx` sin pedírselo (66 spans `POST` extra, +100 % de spans) y descarga `pricing.json` de GitHub en el arranque. Revisa `disabled_instrumentors=[...]` y `pricing_json`, y mide el nº de spans por petición antes de ir a producción.
    8. **Las librerías discrepan en los valores, no solo en los nombres.** `finish_reasons=['tool_calls']` frente a `['tool_call']` rompe consultas cruzadas; define tu normalización en un `SpanProcessor` de `on_start`... o en la capa de consulta/Collector, nunca en `on_end` (inmutable).
    """)

    md("""
    ## ⚠️ Errores comunes

    - Llamar a `openlit.init()` **y** a `OpenAIInstrumentor().instrument()` «por si acaso».
    - Inicializar la librería **después** de importar y crear el cliente en un proceso con *forks* (cada worker debe inicializar).
    - Medir latencias con spans de librería y compararlas con las del agente sin restar los reintentos del SDK.
    - Dejar `capture_message_content` activo «solo en desarrollo» y que la misma imagen llegue a producción. Pon el valor por variable de entorno por entorno.
    - Fijar solo la versión de la librería y no la de la spec/semconv con la que consultas: los *dashboards* dependen de nombres concretos de atributo.
    - Usar un decorador de OpenLIT sobre funciones que reciben texto de clientes.
    """)

    md("""
    ## Autoevaluación
    """)
    md(details("1 · (Diagnóstico) Activas `openlit.init()` en SupportOps y, en Tempo, `{ name =~ \"chat.*\" }` devuelve 66 trazas de 1 span (+66 de `POST`) para 24 tickets. ¿Qué ha pasado y cómo lo arreglas?",
               "La librería solo parchea el cliente de OpenAI; sin un span activo del agente cada `create()` abre una traza nueva (y `httpx` otra hija). Arreglo: abrir `invoke_agent` en `agent_run` (híbrido) para que los `chat` cuelguen de él, y desactivar el instrumentador de `httpx` (`disabled_instrumentors=[\"httpx\"]`) si no lo quieres."))
    md(details("2 · (Cálculo) El servidor recibió 86 peticiones con 30 % de 503 y `max_retries=2` y ves 59 spans `chat`. Si cada petición facturable cuesta 0,002 USD, ¿cuánto se subestima el coste si lo calculas por spans? ¿Y si pusieras `max_retries=0`?",
               "Se subestima 27 peticiones: 27 × 0,002 = **0,054 USD** (el 31 % de lo facturable: 27/86). Con `max_retries=0` cada intento es una petición y un span: 1 petición = 1 span, la subestimación desaparece (cada intento fallido tiene su span ERROR)."))
    md(details("3 · (Cálculo) Con OpenLLMetry, el lote de 24 tickets genera 8,7 KB de atributos por ticket con captura de contenido y 1,3 KB sin ella. Con 1 M tickets/día y retención de 14 días (sin compresión), ¿cuánto almacenamiento de atributos supone cada opción?",
               "Con las cifras medidas en este módulo (OpenLLMetry, 8,7 KB/ticket con contenido frente a 1,3 KB sin él): a 1 M tickets/día son ≈ 8,7 GB/día frente a 1,3 GB/día; en 14 días ≈ **122 GB** frente a **18 GB** (sin compresión; Tempo comprime los bloques, pero la proporción ≈ ×6,7 se conserva y el contenido es lo que más pesa). Cambia las cifras por tu propio `kb_per_ticket`."))
    md(details("4 · (Transferencia) Tu empresa ya usa Datadog APM en 40 servicios Java/Node/Python y quiere observar agentes LLM. ¿Qué criterios de la matriz cambiarían de peso y qué opción sería razonable?",
               "Pesa mucho la **neutralidad (semconv estándar)** y el **esfuerzo/uniformidad entre lenguajes**: la instrumentación oficial de OpenTelemetry (y sus equivalentes en Java/JS) o OpenLLMetry (que existe en JS) con exportación OTLP; Datadog acepta GenAI semconv (v1.37+). Una librería con plataforma propia (OpenLIT) aporta menos si ya tienes plataforma. Sigue valiendo el híbrido: los spans de agente/herramienta son de tu dominio."))
    md(details("5 · (Diagnóstico) Tras actualizar `openlit` de 1.44 a 1.45, un panel de «tokens por modelo» se queda vacío. ¿Qué dos causas son más probables y qué prueba lo habría evitado?",
               "(1) Cambió el nombre/ubicación de un atributo (p. ej. de métrica a atributo de span, o de `gen_ai.usage.*`); (2) cambió un valor por defecto (captura de contenido, instrumentadores activados). Una **prueba de contrato** que ejecute el agente con `mock` y verifique la presencia de los atributos que usan tus paneles (y la ausencia de PII) bloquea la actualización en CI."))
    md(details("6 · ¿Por qué un `SpanProcessor.on_end` no sirve para redactar PII y qué alternativa recomendarías en producción?",
               "Porque en el SDK de Python recibe un `ReadableSpan` inmutable (`set_attribute` no existe). Alternativas: no capturar contenido, redactar al construir el atributo, o —lo más recomendable— `redaction`/`transform` en el Collector (módulo 20), que aplica una política única a todos los servicios."))
    md(details("7 · (Transferencia) Un proveedor LLM sin SDK de Python (HTTP directo con `httpx`) no está soportado por ninguna librería. ¿Qué haces?",
               "Instrumentar a mano: un *hook* `llm_call` (como `OTelInstrumentor`) que abra el span `chat` con los atributos de la spec. Es exactamente la situación en que lo manual gana; además `httpx`/`requests` pueden instrumentarse automáticamente para tener el span HTTP hijo."))
    md(details("8 · ¿Qué ves en la columna «híbrido» del heatmap de atributos que faltaba y cómo lo arreglarías sin tocar la librería?",
               "Faltan `supportops.ticket.id`, `gen_ai.conversation.id`, `supportops.step/attempt` en el span `chat` (están en el padre). Un `SpanProcessor.on_start` que copie el ticket del `ContextVar` (sección 4.3) los añade a todos los spans, incluidos los de la librería."))

    md("""
    ## Referencias

    - OpenTelemetry, *Semantic Conventions for Generative AI* (estado Development): <https://github.com/open-telemetry/semantic-conventions-genai> (`docs/gen-ai/`).
    - OpenTelemetry, *opentelemetry-python-genai* (instrumentaciones GenAI oficiales; `opentelemetry-instrumentation-genai-openai`): <https://github.com/open-telemetry/opentelemetry-python-genai>
    - OpenTelemetry, *opentelemetry-python-contrib / instrumentation-genai* (copias deprecadas, solo parches de seguridad): <https://github.com/open-telemetry/opentelemetry-python-contrib/tree/main/instrumentation-genai>
    - Traceloop, *OpenLLMetry* (Apache-2.0): <https://github.com/traceloop/openllmetry>
    - OpenLIT, *OpenLIT* (Apache-2.0): <https://github.com/openlit/openlit> · documentación <https://docs.openlit.io>
    - Grafana Labs, *AI Observability* (Grafana Cloud): <https://grafana.com/docs/grafana-cloud/monitor-applications/ai-observability/introduction/>
    - Datadog, *Datadog LLM Observability natively supports OpenTelemetry GenAI Semantic Conventions*, 1-dic-2025: <https://www.datadoghq.com/blog/llm-otel-semantic-convention>
    - OpenTelemetry, *Python SDK*, procesadores de span (`SpanProcessor.on_start` / `on_end` con `ReadableSpan`): <https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.html>
    - Código del laboratorio de este módulo: `supportops/openai_compat.py` y `supportops/autoinstr_lab.py`.
    """)

    nb.save(out)


# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "06_proyecto_autoinstrumentacion.ipynb", "Proyecto 06 · Manual frente a auto: medir y decidir")
    md, code = nb.md, nb.code

    md("""
    BADGE_PLACEHOLDER

    # Proyecto 06 · Manual frente a auto en SupportOps: medir, blindar y decidir

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (conjunto pregrabado; funciona en Colab) |
    | **RAM aproximada** | < 500 MB |
    | **Prerrequisitos** | Lección `06_autoinstrumentacion` (laboratorio, helpers de análisis, `SpanProcessor`, matriz) y módulos 03-05 |
    | **Conexión** | Convierte el experimento de la lección en **tres herramientas de ingeniería** que usarías de verdad: un inventario de ruido, un detector de doble instrumentación/fugas de PII y una **prueba de contrato** para actualizar librerías con seguridad. Prepara el módulo 07 (qué consultas podrás escribir en TraceQL) y el 20 (privacidad) |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. El equipo de producto quiere «activar OpenLIT/OpenLLMetry y listo». Tu jefe te pide una **recomendación defendible con datos** y una red de seguridad para que ninguna actualización de librería rompa los *dashboards* ni filtre datos de clientes. Dispones de la telemetría de 7 estrategias sobre los mismos 24 tickets (semilla 42): manual, OpenLIT, OpenLLMetry, oficial de OpenTelemetry, híbrido oficial, híbrido OpenLLMetry y OpenLLMetry con decoradores, además de las pruebas de trampas (doble instrumentación, reintentos del SDK).

    ## Datos

    - **Pregrabados** (`recorded/lab_seed42.json.gz`, generados con OpenLIT 1.45.0, traceloop-sdk 0.62.4, genai-openai 1.2b0, openai 2.54.0, OpenTelemetry SDK 1.45.1): cada ejecución = `{"spans": [...], "results": [...], "meta": {...}}`; los spans siguen `supportops.schema.SPAN_SCHEMA` (+ `scope`); `results` es el `AgentResult` de cada ticket (verdad de campo); `meta["server_requests"]` es el número de peticiones que recibió de verdad el servidor.
    - Todo es **determinista**: los recuentos de spans no dependen de tu máquina ni de las latencias. (Si re-generas el conjunto con otras versiones de las librerías, las cifras pueden cambiar: esa es justo la razón de la prueba de contrato.)
    - Si instalaste las librerías, `lab.run_variant(...)` puede reproducir cualquier ejecución (retos extra).

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución, dataset pregrabado, semilla 42) |
    |---|---|---|---|
    | R1 | `span_inventory` | Recuento por categoría (agent / chat / tool / http / other) en `openlit`, `hybrid_openllmetry` y `openllmetry_decorated` | coincidencia exacta en 3/3 |
    | R2 | `duplicate_ratio` | Spans `chat` / peticiones reales: `both` = 2,0 · `official` = 1,0 · `retries2:official` ≈ 0,686 | tolerancia ±0,005 en 3/3 |
    | R3 | `leak_report` | Spans con PII, correos distintos y **atributos** por los que se filtra (`openllmetry_decorated`, `off:openlit_decorated`, `official`) | coincidencia exacta en 3/3 |
    | R4 | `TicketContextProcessor` | En el banco de pruebas: 48 de 49 spans con `supportops.ticket.id` (el que se creó **fuera** de un ticket no lo lleva) y 49 de 49 con `supportops.instrumented_by` | exacto |
    | R5 | `contract_violations` | Violaciones del contrato en `openlit`, `openllmetry`, `official`, `hybrid_official` | coincidencia exacta en 4/4 |
    | R6 | `weighted_scores` + `win_rates` + `DECISION` | Ganador por perfil, tasa de victorias del híbrido oficial con pesos aleatorios, y justificación escrita con cifras | ganadores coinciden · tasa 0,64 ± 0,03 · 3 justificaciones ≥ 150 caracteres con ≥ 2 cifras |

    > 📏 Calibración: los umbrales son los valores que mide la solución de referencia sobre el conjunto pregrabado. Las clasificaciones y recuentos son estables porque el laboratorio fija semillas y el servidor falso es determinista; las duraciones (que dependen de tu máquina) **no** se usan en ninguna rúbrica.
    """.replace("BADGE_PLACEHOLDER", nb.badge()))

    code(boot("viz,otel"))
    code(IMPORTS + SETUP.replace('print("Versiones instaladas:", {p: ver(p) for p in PACKAGES})\n', "").replace('print("Disponible para re-ejecutar el laboratorio:", all(LIBS.values()), LIBS)', 'print("Librerías para re-ejecutar el laboratorio (opcional):", LIBS)'))
    code(LOAD.replace('print("versiones con las que se grabó:", LAB["openlit"]["meta"]["versions"])', "RUN_KEYS = list(LAB)"))

    md("""
    ## Paso 0 · Herramientas que te damos hechas (de la lección)

    Las funciones de la lección que no vas a tener que reescribir: `trace_stats`, `attr_coverage`, `ticket_of_trace`, `failure_attribution`, `token_attribution`, `pii_spans`, `kb_per_ticket`, `is_chat`, `traces_of`. Los **tickets** y su ground truth están en `LAB[<variante>]["results"]`.
    """)
    code(HELPERS)

    md("""
    ## Paso 1 · Inventario de spans y ruido

    Una forma rápida de ver «qué me ha instalado esta librería» es clasificar los spans por **categoría**.
    **TODO 1.** Implementa `classify(span)` y `span_inventory(spans)`:

    | Categoría | Regla |
    |---|---|
    | `chat` | `is_chat(span)` (operación GenAI `chat`; el nombre de span cambia según la librería: `chat mock-small`, `openai.chat`…) |
    | `agent` | nombre que empieza por `invoke_agent`, o es `run`, o termina en `.agent` (decoradores de OpenLLMetry/OpenLIT) |
    | `tool` | nombre que empieza por `execute_tool`, o termina en `.tool`, o es uno de `TOOL_NAMES` |
    | `http` | nombre `POST` o `GET` (spans de `httpx`) |
    | `other` | el resto |

    `span_inventory` devuelve un `dict` con **las cinco claves** (0 si no hay).
    """)
    md(hint(1, "Evalúa en este orden: primero `chat` (porque `openai.chat` no empieza por `chat`), luego agente, herramienta, http. `collections.Counter(classify(s) for s in spans)` y rellena con `.get(k, 0)` para las 5 claves."))
    md(hint(2, "`def classify(s): n = s['name']; if is_chat(s): return 'chat'; if n.startswith('invoke_agent') or n == 'run' or n.endswith('.agent'): return 'agent'; ...` y después `{k: c.get(k, 0) for k in ('agent','chat','tool','http','other')}`."))
    code('''
TOOL_NAMES = {"get_order", "issue_refund", "search_kb", "escalate_to_human"}

def classify(s: dict) -> str:
    # TODO 1a
    raise NotImplementedError("TODO 1a")

def span_inventory(spans: list[dict]) -> dict:
    # TODO 1b
    raise NotImplementedError("TODO 1b")

try:
    inv = pd.DataFrame({v: span_inventory(LAB[v]["spans"]) for v in ["manual", "openlit", "openllmetry", "official", "hybrid_openllmetry", "openllmetry_decorated"]}).T
    display(inv)
except NotImplementedError as e:
    inv = None; print("Pendiente:", e)
''')

    md("""
    ## Paso 2 · ¿Cuántos spans `chat` por petición real? (doble instrumentación y reintentos)

    Si hay una sola librería por proveedor y el SDK no reintenta por dentro, **un span `chat` = una petición real** (`meta["server_requests"]`).
    **TODO 2.** `duplicate_ratio(run)` = nº de spans `chat` / peticiones reales. Interpreta: > 1 → doble instrumentación; < 1 → peticiones que no ves (reintentos ocultos).
    """)
    code('''
def duplicate_ratio(run: dict) -> float:
    # TODO 2
    raise NotImplementedError("TODO 2")

try:
    for k in ["official", "both", "retries2:official", "retries2:openlit"]:
        print(f"{k:20s} chat/peticiones = {duplicate_ratio(LAB[k]):.3f}")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 3 · ¿Por qué atributo se filtra el PII?

    «Hay PII en 5 spans» no basta para arreglarlo: necesitas saber **en qué atributo** (para saber qué interruptor apagar). **TODO 3.** `leak_report(run)` devuelve `{"spans": n, "emails": n_correos_distintos, "keys": {atributo: nº_de_spans}}`, mirando **todos** los atributos de cada span **y los atributos de sus eventos** (usa la clave `evento:<nombre>.<atributo>` para estos últimos). Usa `EMAIL` y `json.dumps(valor, ensure_ascii=False)` para buscar dentro de valores no-string (listas, dicts).
    """)
    md(hint(1, "Recorre `s['attributes'].items()` y, además, `[(f\"evento:{e['name']}.{k}\", v) for e in s['events'] for k, v in e['attributes'].items()]`. Para cada par, `EMAIL.findall(json.dumps(v, ensure_ascii=False))`: si hay coincidencias, suma 1 a `keys[k]`, añade los correos a un `set` y marca el span como «con fuga» (una sola vez por span)."))
    code('''
def leak_report(run: dict) -> dict:
    # TODO 3
    raise NotImplementedError("TODO 3")

try:
    for k in ["openlit", "off:openlit", "openllmetry_decorated", "off:openlit_decorated", "official"]:
        print(f"{k:24s}", leak_report(LAB[k]))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 4 · Un `SpanProcessor` que enriquece y audita

    En la lección el procesador copiaba el ticket activo. Ahora, además, queremos **saber qué librería creó cada span** (para detectar duplicados en producción).
    **TODO 4.** Escribe `TicketContextProcessor(SpanProcessor)` con `on_start(self, span, parent_context=None)` que:
    1. **siempre** añade `supportops.instrumented_by` = nombre del *instrumentation scope* del span (`span.instrumentation_scope.name`);
    2. **solo si hay un ticket activo** (`lab._TICKET.get()` devuelve un `dict` con `ticket` y `tier`, o `None`), añade `supportops.ticket.id`, `gen_ai.conversation.id` (= ticket) y `supportops.customer.tier`.

    El banco de pruebas `harness(processor)` simula a dos «librerías» (scopes `opentelemetry.instrumentation.genai.openai` y `opentelemetry.instrumentation.httpx`) creando spans dentro de cada ticket de la ejecución `manual` y **un span más fuera de cualquier ticket**.
    """)
    md(hint(1, "`from opentelemetry.sdk.trace import SpanProcessor`; el hook es `on_start`, **no** `on_end` (inmutable). `lab._TICKET` es un `ContextVar`: `lab._TICKET.get()`."))
    md(hint(2, "`span.set_attribute(\"supportops.instrumented_by\", span.instrumentation_scope.name)` y, si `t := lab._TICKET.get()`, `span.set_attributes({\"supportops.ticket.id\": t[\"ticket\"], ...})`."))
    code('''
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

class TicketContextProcessor(SpanProcessor):
    def on_start(self, span, parent_context=None):
        # TODO 4
        raise NotImplementedError("TODO 4")

def harness(proc: SpanProcessor) -> list:
    mem = InMemorySpanExporter(); tp = TracerProvider(); tp.add_span_processor(proc); tp.add_span_processor(SimpleSpanProcessor(mem))
    lib, http = tp.get_tracer("opentelemetry.instrumentation.genai.openai"), tp.get_tracer("opentelemetry.instrumentation.httpx")
    for r in LAB["manual"]["results"]:
        tok = lab._TICKET.set({"ticket": r["ticket_id"], "tier": r["tier"]})
        try:
            with lib.start_as_current_span("chat mock-small", attributes={"gen_ai.operation.name": "chat"}):
                with http.start_as_current_span("POST"):
                    pass
        finally:
            lab._TICKET.reset(tok)
    with lib.start_as_current_span("chat fuera de ticket"):
        pass
    return list(mem.get_finished_spans())

try:
    H = harness(TicketContextProcessor())
    print(len(H), "spans ·", sum("supportops.ticket.id" in s.attributes for s in H), "con ticket.id ·", sum("supportops.instrumented_by" in s.attributes for s in H), "con instrumented_by")
    print("el span fuera de ticket:", dict(H[-1].attributes))
except NotImplementedError as e:
    H = None; print("Pendiente:", e)
''')

    md("""
    ## Paso 5 · Una prueba de contrato para actualizar librerías sin miedo

    Un *dashboard* de «tokens por modelo» depende de **nombres y valores** de atributo concretos. La prueba de contrato (en CI, con el LLM `mock`) ejecuta el agente y comprueba el **contrato** del equipo:

    - **Presencia:** cada span `chat` **sin error** lleva los 8 atributos `SPEC_REQUIRED` (los primeros 8 de `EXPECTED_CHAT`).
    - **Valores:** `gen_ai.response.finish_reasons` ⊆ `ALLOWED_FINISH` (`stop`, `length`, `tool_calls`: el contrato del equipo, para que las consultas funcionen con cualquier servicio).
    - **Privacidad:** ningún span con PII (`pii_spans(...) == 0`).

    **TODO 5.** `contract_violations(run)` devuelve un `dict` `{motivo: nº}`: `falta:<atributo>` por cada ausencia, `finish_reason_fuera_de_contrato` por cada span con algún valor fuera del conjunto, y `pii` (nº de spans con PII) si es > 0. Un dict vacío significa «cumple el contrato».
    """)
    code('''
SPEC_REQUIRED = EXPECTED_CHAT[:8]
ALLOWED_FINISH = {"stop", "length", "tool_calls"}

def contract_violations(run: dict, required=SPEC_REQUIRED, allowed=ALLOWED_FINISH) -> dict:
    # TODO 5
    raise NotImplementedError("TODO 5")

try:
    for k in ["official", "hybrid_official", "openlit", "openllmetry", "hybrid_openllmetry", "openllmetry_decorated"]:
        print(f"{k:24s}", contract_violations(LAB[k]))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 6 · La decisión con tus propias medidas

    Con tus funciones ya puedes puntuar siete opciones. La matriz usa **criterios medidos** (con tus funciones) y **criterios cualitativos** (dados; con su justificación en la lección):

    | Criterio | Origen | Dirección |
    |---|---|---|
    | `contexto` | media de `token_attribution` y de `failure_attribution` | más = mejor |
    | `ruido` | fracción de spans `http` + `other` (`span_inventory`) | menos = mejor |
    | `pii` | spans con PII (`leak_report`) | menos = mejor |
    | `contrato` | nº total de violaciones (`contract_violations`) | menos = mejor |
    | `huella` | paquetes extra medidos en la lección | menos = mejor |
    | `cobertura`, `esfuerzo`, `gobernanza` | cualitativos (1-5) | más = mejor |

    **TODO 6a.** `weighted_scores(SC, w)` → `pd.Series` con la puntuación ponderada (pesos normalizados) ordenada de mayor a menor. **TODO 6b.** `win_rates(SC, n=20000, seed=42)` → `dict` {opción: fracción de vectores de pesos aleatorios `Dirichlet(1,…,1)` en que gana} (usa `np.random.default_rng(seed)`; igual que la lección). **TODO 6c.** Rellena `DECISION[perfil] = (opción, justificación)` con **al menos dos cifras medidas** en cada justificación.
    """)
    code('''
OPTS7 = ["manual", "openlit", "openllmetry", "official", "hybrid_official", "hybrid_openllmetry", "openllmetry_decorated"]
PKGS = {"manual": 0, "openlit": 34, "openllmetry": 61, "official": 5, "hybrid_official": 5, "hybrid_openllmetry": 61, "openllmetry_decorated": 61}

def scale(values: dict, higher_better: bool = True) -> dict:
    lo, hi = min(values.values()), max(values.values())
    return {k: (5.0 if hi == lo else 1 + 4 * ((v - lo) / (hi - lo) if higher_better else (hi - v) / (hi - lo))) for k, v in values.items()}

def build_SC() -> pd.DataFrame:
    noise = lambda spans: (span_inventory(spans)["http"] + span_inventory(spans)["other"]) / max(1, len(spans))
    meas = {"contexto": scale({o: (token_attribution(LAB[o]) + failure_attribution(LAB[o])[0]) / 2 for o in OPTS7}),
            "ruido": scale({o: noise(LAB[o]["spans"]) for o in OPTS7}, False),
            "pii": scale({o: leak_report(LAB[o])["spans"] for o in OPTS7}, False),
            "contrato": scale({o: sum(contract_violations(LAB[o]).values()) for o in OPTS7}, False),
            "huella": scale(PKGS, False)}
    qual = {"cobertura": [1, 5, 4, 3, 3, 4, 4], "esfuerzo": [1, 5, 5, 4, 3, 3, 4], "gobernanza": [5, 3, 3, 4, 4, 3, 3]}
    return pd.DataFrame({**meas, **{k: dict(zip(OPTS7, v)) for k, v in qual.items()}}).loc[OPTS7]

PROFILES = {   # pesos en el orden de las columnas de SC
    "SupportOps (agente propio, 1 proveedor, datos sensibles)": [5, 2, 5, 4, 2, 2, 3, 3],
    "Plataforma interna (muchos frameworks y equipos)":          [3, 2, 3, 4, 2, 5, 4, 3],
    "Prototipo de 1 día":                                         [1, 1, 1, 1, 2, 3, 5, 1],
}

def weighted_scores(SC: pd.DataFrame, w) -> pd.Series:
    # TODO 6a
    raise NotImplementedError("TODO 6a")

def win_rates(SC: pd.DataFrame, n: int = 20000, seed: int = 42) -> dict:
    # TODO 6b
    raise NotImplementedError("TODO 6b")

DECISION: dict[str, tuple[str, str]] = {}      # TODO 6c: perfil -> (opción, justificación con cifras)

try:
    SC = build_SC(); display(SC.round(2))
    for name, w in PROFILES.items():
        print(name, "->", weighted_scores(SC, w).round(2).head(3).to_dict())
    WR = win_rates(SC); print("tasa de victorias con pesos aleatorios:", {k: round(v, 3) for k, v in WR.items()})
except NotImplementedError as e:
    SC = WR = None; print("Pendiente:", e)
''')

    md("""
    ## Autocomprobación (rúbrica)
    Ejecuta esta celda para ver qué entregables pasan. Los valores esperados son los de la solución de referencia.
    """)
    code('''
def check(name, fn):
    try:
        ok, detail = fn()
    except NotImplementedError:
        ok, detail = False, "pendiente"
    except Exception as e:                                  # un error tuyo no debe romper la rúbrica
        ok, detail = False, f"{type(e).__name__}: {e}"
    print(("✅" if ok else "❌"), name, "·", detail); return ok

def r1():
    exp = {"openlit": {"agent": 0, "chat": 66, "tool": 0, "http": 66, "other": 0}, "hybrid_openllmetry": {"agent": 24, "chat": 66, "tool": 36, "http": 0, "other": 0},
           "openllmetry_decorated": {"agent": 24, "chat": 66, "tool": 28, "http": 0, "other": 0}}
    n = sum(span_inventory(LAB[k]["spans"]) == v for k, v in exp.items()); return n == 3, f"{n}/3 inventarios exactos"
def r2():
    exp = {"both": 2.0, "official": 1.0, "retries2:official": 0.686}
    n = sum(abs(duplicate_ratio(LAB[k]) - v) <= 0.005 for k, v in exp.items()); return n == 3, f"{n}/3 ratios dentro de ±0,005"
def r3():
    exp = {"openllmetry_decorated": {"spans": 8, "emails": 3, "keys": {"traceloop.entity.input": 3, "gen_ai.input.messages": 5}},
           "off:openlit_decorated": {"spans": 3, "emails": 3, "keys": {"function.args": 3}}, "official": {"spans": 0, "emails": 0, "keys": {}}}
    n = sum(leak_report(LAB[k]) == v for k, v in exp.items()); return n == 3, f"{n}/3 informes exactos"
def r4():
    H = harness(TicketContextProcessor()); t = sum("supportops.ticket.id" in s.attributes for s in H); b = sum("supportops.instrumented_by" in s.attributes for s in H)
    return (len(H), t, b) == (49, 48, 49) and "supportops.ticket.id" not in H[-1].attributes, f"{t}/{len(H)} con ticket.id, {b}/{len(H)} con instrumented_by"
def r5():
    exp = {"openlit": {"pii": 5}, "openllmetry": {"finish_reason_fuera_de_contrato": 26, "pii": 5}, "official": {}, "hybrid_official": {}}
    n = sum(contract_violations(LAB[k]) == v for k, v in exp.items()); return n == 4, f"{n}/4 contratos exactos"
def r6():
    SC_ = build_SC(); tops = {p: weighted_scores(SC_, w).index[0] for p, w in PROFILES.items()}
    exp_tops = ["hybrid_official", "hybrid_official", "official"]
    wr = win_rates(SC_)
    just = [v[1] for v in DECISION.values() if isinstance(v, tuple) and len(v) == 2]
    ok_text = len(just) >= 3 and all(len(t) >= 150 and len(re.findall(r"\\d+[.,]?\\d*", t)) >= 2 for t in just)
    ok = list(tops.values()) == exp_tops and abs(wr["hybrid_official"] - 0.64) <= 0.03 and abs(sum(wr.values()) - 1) < 1e-9 and ok_text
    return ok, f"ganadores {list(tops.values())} · híbrido gana {wr['hybrid_official']:.2f} · justificaciones con cifras: {ok_text}"

results = [check("R1 span_inventory", r1), check("R2 duplicate_ratio", r2), check("R3 leak_report", r3), check("R4 TicketContextProcessor", r4),
           check("R5 contract_violations", r5), check("R6 decisión", r6)]
print(f"\\n{sum(results)}/6 entregables correctos")
''')

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    Abajo está la solución de referencia completa (con la que se calibró la rúbrica). Si te atascas en un TODO, abre primero las pistas 🪜 del paso correspondiente.
    """)
    md("""
    ## Solución de referencia
    """)
    code('''
# ---- Pasos 1 a 3
def classify(s: dict) -> str:
    n = s["name"]
    if is_chat(s):
        return "chat"
    if n.startswith("invoke_agent") or n == "run" or n.endswith(".agent"):
        return "agent"
    if n.startswith("execute_tool") or n.endswith(".tool") or n in TOOL_NAMES:
        return "tool"
    if n in ("POST", "GET"):
        return "http"
    return "other"

def span_inventory(spans: list[dict]) -> dict:
    c = collections.Counter(classify(s) for s in spans)
    return {k: c.get(k, 0) for k in ("agent", "chat", "tool", "http", "other")}

def duplicate_ratio(run: dict) -> float:
    return sum(is_chat(s) for s in run["spans"]) / run["meta"]["server_requests"]

def leak_report(run: dict) -> dict:
    keys, emails, n = collections.Counter(), set(), 0
    for s in run["spans"]:
        items = list(s["attributes"].items()) + [(f"evento:{e['name']}.{k}", v) for e in s["events"] for k, v in e["attributes"].items()]
        hit = False
        for k, v in items:
            found = EMAIL.findall(json.dumps(v, ensure_ascii=False))
            if found:
                keys[k] += 1; emails.update(found); hit = True
        n += hit
    return {"spans": n, "emails": len(emails), "keys": dict(keys)}
''')
    code('''
# ---- Paso 4: procesador
class TicketContextProcessor(SpanProcessor):
    def on_start(self, span, parent_context=None):
        span.set_attribute("supportops.instrumented_by", span.instrumentation_scope.name)      # siempre: ¿qué librería lo creó?
        t = lab._TICKET.get()
        if t:                                                                                  # solo dentro de un ticket
            span.set_attributes({"supportops.ticket.id": t["ticket"], "gen_ai.conversation.id": t["ticket"], "supportops.customer.tier": t["tier"]})

H = harness(TicketContextProcessor())
print(len(H), "spans ·", sum("supportops.ticket.id" in s.attributes for s in H), "con ticket.id ·", sum("supportops.instrumented_by" in s.attributes for s in H), "con instrumented_by")
''')
    code('''
# ---- Paso 5: contrato
def contract_violations(run: dict, required=SPEC_REQUIRED, allowed=ALLOWED_FINISH) -> dict:
    out = collections.Counter()
    for s in run["spans"]:
        if is_chat(s) and s["status"] != "ERROR":
            for a in required:
                if a not in s["attributes"]:
                    out[f"falta:{a}"] += 1
            fr = s["attributes"].get("gen_ai.response.finish_reasons")
            if fr is not None and any(x not in allowed for x in fr):
                out["finish_reason_fuera_de_contrato"] += 1
    n = pii_spans(run["spans"])
    if n:
        out["pii"] = n
    return dict(out)

# ---- Paso 6: matriz y sensibilidad
def weighted_scores(SC: pd.DataFrame, w) -> pd.Series:
    w = np.asarray(w, float); w = w / w.sum()
    return pd.Series(SC.values @ w, index=SC.index).sort_values(ascending=False)

def win_rates(SC: pd.DataFrame, n: int = 20000, seed: int = 42) -> dict:
    W = np.random.default_rng(seed).dirichlet(np.ones(SC.shape[1]), n)
    c = collections.Counter(SC.index[(SC.values @ W.T).argmax(axis=0)])
    return {o: c.get(o, 0) / n for o in SC.index}

SC = build_SC(); WR = win_rates(SC)
DECISION = {
    "SupportOps (agente propio, 1 proveedor, datos sensibles)": ("hybrid_official",
        "Híbrido oficial: 100 % de los tickets con tokens y fallos atribuibles (como el manual) pero con el span chat mantenido por OpenTelemetry; 0 spans con PII y 0 violaciones de contrato por defecto, solo 5 paquetes extra y gana en el 64 % de los pesos aleatorios."),
    "Plataforma interna (muchos frameworks y equipos)": ("hybrid_official",
        "También híbrido oficial (4,17 frente a 3,86 de la oficial pura): la amplitud de OpenLIT/OpenLLMetry (66 trazas huérfanas para 24 tickets y PII en 5 spans por defecto) no compensa; si hace falta más cobertura se añade OpenLLMetry con contenido apagado y el mismo SpanProcessor."),
    "Prototipo de 1 día": ("official",
        "La oficial pura (3,89) roza a OpenLIT (3,83): 1 línea, 0 PII y 0 violaciones del contrato de atributos; sirve para un prototipo, aceptando que habrá 66 trazas huérfanas y sin atribución por ticket."),
}
for p, (o, j) in DECISION.items():
    print(f"{p}\\n   -> {o}: {j}\\n")
''')
    code("""
# Verificación final de la solución con la misma rúbrica
results = [check("R1 span_inventory", r1), check("R2 duplicate_ratio", r2), check("R3 leak_report", r3), check("R4 TicketContextProcessor", r4),
           check("R5 contract_violations", r5), check("R6 decisión", r6)]
print(f"\\n{sum(results)}/6 entregables correctos")
""")

    md("""
    ## Retos extra (nivel experto)

    1. **Reproduce en vivo.** Con las librerías instaladas: `d = lab.run_variant("openlit", n=24, content="off", enrich=True)` y pasa tus funciones sobre `d`. ¿Cuántas violaciones de contrato quedan? ¿Qué spans `http` siguen ahí? (Pista: mira `lab.run_variant` y `disabled_instrumentors` en la documentación de OpenLIT.)
    2. **Guardia de doble instrumentación.** Escribe una función de arranque que cuente cuántas capas de *wrapper* tiene `openai.resources.chat.completions.Completions.create` (los parches de `wrapt` exponen `__wrapped__`) y falle si hay más de una librería. Pruébala con `lab.run_variant(..., extra="official")` en un subproceso.
    3. **Prueba de contrato en `pytest`.** Convierte `contract_violations` en un test parametrizado por variante que se ejecute en CI con `mock` y falle si `pii` > 0 o si cambia el conjunto de atributos de `chat`.
    4. **Pesos honestos.** Pide a dos compañeros que puntúen (sin ver tu matriz) los tres criterios cualitativos y recalcula `win_rates`. ¿Cambia el ganador? ¿Cuánto varía la tasa del híbrido?
    5. **Streaming.** Extiende `lab.run_variant` para ejecutar un agente con `stream=True` e `include_usage=True` y comprueba con tu `token_attribution` que se recuperan los tokens.
    """)

    md("""
    ## Reflexión (conexión con producción y con el hilo conductor)

    - Tu prueba de contrato bloquea una actualización de OpenLIT porque cambia un valor de `finish_reasons`. ¿Quién decide si se acepta el cambio y cómo se migran los *dashboards* y las alertas existentes sin romper el histórico? (módulos 10 y 16)
    - ¿Qué parte de lo medido aquí se convierte en **política del Collector** (redacción, eliminación de atributos, normalización) y no en código de cada servicio? (módulos 05 y 20)
    - Un equipo vecino usa OpenLIT con captura de contenido porque sus *evals* lo necesitan (módulo 14). ¿Cómo separas, a nivel de traza, el contenido sensible del resto de la telemetría para que pueda retenerse menos tiempo?
    - ¿Qué consultas de TraceQL (módulo 07) te habría gustado poder escribir y que **no** puedes escribir con la telemetría de solo-librería? Anótalas: son tu lista de atributos obligatorios.
    - Conexión con SupportOps: el híbrido que has elegido es la base de instrumentación que usarán los módulos 07 (Tempo), 08 (Loki) y 13 (costes por ticket).
    """)

    nb.save(out)


if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    (COURSE / MOD / "README.md").write_text(readme(), encoding="utf-8")
    print("OK README", COURSE / MOD / "README.md")
    build_lesson()
    build_project()
