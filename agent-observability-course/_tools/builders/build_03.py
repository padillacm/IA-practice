"""Genera el módulo 03_otel_sdk_python: README, lección y proyecto.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_03.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "03_otel_sdk_python"

# Imports compartidos por la lección y el proyecto (SDK de OpenTelemetry + utilidades)
OTEL_IMPORTS = '''
import contextvars, json, secrets, threading, time, logging, inspect, urllib.request, http.server
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from opentelemetry import trace, context, propagate
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider, sampling
from opentelemetry.sdk.trace.export import (BatchSpanProcessor, SimpleSpanProcessor, ConsoleSpanExporter, SpanExporter, SpanExportResult)
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from supportops.telemetry import setup_telemetry, OTelInstrumentor
'''


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "03_otel_sdk_python.ipynb", "Módulo 03 · El SDK de OpenTelemetry para Python")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 03 · El SDK de OpenTelemetry para Python: spans, contexto y exportación OTLP

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Opcional: `docker compose --profile core up -d` (Collector + Tempo + Loki). Sin Docker, todo funciona con el **modo degradado** (telemetría en memoria; la parte de «ver la traza en Tempo» se salta) |
    | **RAM aproximada** | ≈ 0,4 GB con el perfil `core` en reposo (≤ 1 GB con carga) + kernel de Python |
    | **Prerrequisitos** | Módulo 02 (modelo de datos de OTel, `traceparent` a mano), módulo 01 (`Instrumentor`, `RecordingInstrumentor`) |
    | **Hilo conductor** | SupportOps pasa de **v0 (sin observabilidad)** a **v1 instrumentado a mano**. Las trazas llegarán a Tempo; el módulo 04 las ajustará a las GenAI semantic conventions y el 05 pondrá un Collector serio en medio |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** la separación API / SDK de OpenTelemetry y recorrer el camino de un span: *Sampler → Span → SpanProcessor → Exporter → OTLP*.
    2. **Construir a mano** un tracer mínimo (ids, contexto con `contextvars`, tiempos, estado) y un exportador OTLP/JSON, para entender qué hace el SDK por debajo.
    3. **Crear** con el SDK un `TracerProvider` con `Resource`, spans con atributos, eventos, *links*, estado y excepciones, y **justificar** cuándo usar `SpanKind` `INTERNAL`, `CLIENT` o `SERVER`.
    4. **Propagar contexto** entre servicios con cabeceras W3C `traceparent` (`inject`/`extract`) y **diagnosticar** una traza rota por un hilo o un servicio sin propagación.
    5. **Elegir y dimensionar** `SimpleSpanProcessor` frente a `BatchSpanProcessor`, **calcular** su capacidad y **medir** qué ocurre cuando la cola se llena.
    6. **Configurar** el exportador OTLP/HTTP (endpoint, compresión, variables de entorno) y **verificar** la traza en Tempo.
    7. **Instrumentar SupportOps** (`invoke_agent` → `chat` → `execute_tool`) con logs correlacionados y **medir el coste** de la instrumentación.
    8. **Evitar** las trampas del SDK (proveedor global de un solo uso, límites de atributos, muestreo y atributos tardíos, fork).
    """)

    md("""
    ## 🔁 Conexión con módulos anteriores
    """)
    md(details("1 · (Módulo 02) ¿Qué cuatro campos tiene la cabecera `traceparent` y cuál de ellos decide si la traza se muestrea?",
               "`versión-trace_id-parent_id-flags` (p. ej. `00-<32 hex>-<16 hex>-01`). El campo `flags`: el bit `0x01` = *sampled* (y, en Trace Context Level 2, `0x02` = *random-trace-id*). El `parent_id` es el span del **emisor**, que se convierte en el padre del primer span del receptor."))
    md(details("2 · (Módulo 02) ¿Qué diferencia hay entre *resource* y *instrumentation scope*?",
               "El *resource* describe **quién** emite (`service.name`, `service.version`, instancia…): es igual para todo el proceso. El *scope* describe **qué librería/código** generó el dato (nombre y versión del tracer) y puede haber varios en el mismo proceso."))
    md(details("3 · (Módulo 01) ¿Por qué las trazas de SupportOps duran milisegundos aunque el agente «tarde» varios segundos?",
               "Porque la latencia es **simulada** (`SimClock`): el agente avanza un reloj virtual en vez de dormir. Por eso usaremos `start_time`/`end_time` simulados para que las trazas sean deterministas (o `SUPPORTOPS_REAL_SLEEP_SCALE` para duraciones de pared)."))

    code(boot("viz,otel"))
    code(IMPORTS + OTEL_IMPORTS + '''
STACK = check_stack(["collector", "tempo", "loki"])     # si falta algo: imprime el comando de Compose y activa el modo degradado
logging.getLogger("opentelemetry").setLevel(logging.ERROR)   # silencia avisos benignos del SDK en los experimentos
''')

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ---
    # 1 · Intuición: API, SDK y el camino de un span

    OpenTelemetry separa dos paquetes a propósito:

    - **API** (`opentelemetry-api`): lo que llama **tu código y las librerías** (`tracer.start_as_current_span(...)`). Si nadie configura nada, es un **no-op** (cero coste, cero efectos).
    - **SDK** (`opentelemetry-sdk`): la implementación que **el dueño de la aplicación** configura una vez, al arrancar: qué se muestrea, cómo se agrupa y adónde se envía.

    | Si vienes de… | Analogía |
    |---|---|
    | **Backend Python** | `logging.getLogger(__name__)` (la API que usan las librerías) frente a `logging.config.dictConfig(...)` (el SDK: *handlers* y formatos que decide la app). Una librería nunca configura *handlers*; con OTel pasa igual. |
    | **ML** | La interfaz `Estimator.fit/predict` (API) frente a la implementación concreta y sus hiperparámetros (SDK): cambias el backend sin tocar el código del modelo. |
    | **SRE** | El *agente de monitoreo* (SDK + exportador) frente al contrato de métricas que expone cada servicio. |

    Dibujemos el camino de un span, de `start_span` a Tempo:
    """)
    code('''
fig, ax = viz.canvas(15, 5.2, xlim=(0, 150), ylim=(0, 52))
ax.text(1, 49, "Tu código y tus librerías", fontsize=10, fontweight="bold", color=viz.PALETTE["dark"])
a = viz.box(ax, 1, 33, 22, 10, "API\\ntracer.start_as_current_span()\\nspan.set_attribute()", viz.PALETTE["neutral"], fontsize=8)
ax.add_patch(plt.Rectangle((29, 8), 82, 40, fill=False, ec=viz.PALETTE["traces"], lw=2, ls="--")); ax.text(30, 49, "SDK (lo configura la aplicación, una vez)", fontsize=10, fontweight="bold", color=viz.PALETTE["traces"])
s = viz.box(ax, 32, 33, 16, 10, "① Sampler\\n¿registrar?\\n(head sampling)", viz.PALETTE["warn"], fontsize=8)
sp = viz.box(ax, 53, 33, 16, 10, "② Span\\n(en memoria, mutable\\nhasta end())", viz.PALETTE["traces"], fontsize=8)
pr = viz.box(ax, 74, 33, 17, 10, "③ SpanProcessor\\nSimple | Batch\\n(cola + hilo)", viz.PALETTE["traces"], fontsize=8)
ex = viz.box(ax, 94, 33, 15, 10, "④ Exporter\\nOTLP/HTTP\\n(protobuf)", viz.PALETTE["traces"], fontsize=8)
viz.box(ax, 32, 12, 37, 10, "TracerProvider\\n= Resource + Sampler + IdGenerator + procesadores", viz.PALETTE["traces"], fontsize=8)
viz.box(ax, 74, 12, 35, 10, "Resource: service.name, service.version,\\nservice.instance.id, telemetry.sdk.*", viz.PALETTE["metrics"], fontsize=8)
col = viz.box(ax, 118, 33, 15, 10, "Collector\\n:4318 /v1/traces", viz.PALETTE["metrics"], fontsize=8)
tp = viz.box(ax, 118, 12, 15, 10, "Tempo\\n(TraceQL)", viz.PALETTE["traces"], fontsize=8)
for p, q, t in ((viz.right(a), viz.left(s), ""), (viz.right(s), viz.left(sp), ""), (viz.right(sp), viz.left(pr), ""), (viz.right(pr), viz.left(ex), ""), (viz.right(ex), viz.left(col), "OTLP")):
    viz.arrow(ax, p, q, t, fontsize=8)
viz.arrow(ax, viz.bottom(col), viz.top(tp), "", dashed=True)
ax.text(1, 3, "Sin SDK configurado, la API es un no-op: instrumentar una librería no cuesta nada ni envía nada.", fontsize=9, style="italic", color=viz.PALETTE["neutral"])
plt.show()
''')
    md(observe("""
    - Hay **cuatro puntos de decisión** donde se pierde o se transforma información: el *sampler* (descarta antes de crear datos), el *processor* (agrupa y puede **descartar si la cola se llena**), el *exporter* (reintenta o falla) y el *Collector* (módulo 05).
    - El `Resource` se adjunta al **proveedor**, no a cada span: por eso `service.name` no se repite en cada `set_attribute`.
    - Todo esto vive en el **proceso de tu aplicación**: el SDK consume CPU/memoria de tu agente (lo mediremos en la sección 7).
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ---
    # 2 · Teoría: el modelo de datos que implementa el SDK

    **Span** = una operación con nombre, intervalo de tiempo y contexto. Campos (spec de trazas):

    | Campo | Qué es | Regla práctica |
    |---|---|---|
    | `name` | Nombre de la operación | **Baja cardinalidad**: `execute_tool get_order`, no `GET /orders/ORD-00017` |
    | `SpanContext` | `trace_id` (16 B), `span_id` (8 B), `trace_flags` (sampled), `trace_state` | Inmutable; es lo que viaja por la red |
    | `parent` | `span_id` del padre (o ninguno = raíz) | Lo fija el contexto activo al crear el span |
    | `kind` | `INTERNAL`, `CLIENT`, `SERVER`, `PRODUCER`, `CONSUMER` | Dice **qué papel** juega en una llamada entre procesos |
    | `start/end time` | Instantes (ns desde epoch) | Se pueden fijar a mano (nosotros usamos el reloj simulado) |
    | `attributes` | Pares clave-valor (str, bool, int, float o arrays homogéneos) | Preferibles al crear el span (¡el sampler solo ve esos!) |
    | `events` | Sucesos con marca de tiempo dentro del span (`exception`, «reintento») | Para hitos, no para spans diminutos |
    | `links` | Referencias a **otros** spans/trazas (sin relación padre-hijo) | Colas, *fan-in*, reintentos que cruzan trazas |
    | `status` | `UNSET` · `OK` · `ERROR` (+ descripción solo en ERROR) | Las librerías **no** deben poner `OK`; solo `ERROR` en fallos |

    **`SpanKind`** (lo que de verdad significa):

    | Kind | Cuándo | Ejemplo en SupportOps |
    |---|---|---|
    | `INTERNAL` | Operación dentro del proceso | `invoke_agent` (agente local), `execute_tool` de una función Python |
    | `CLIENT` | Tu proceso **llama** a otro y espera respuesta | `chat` (llamada al LLM), una llamada HTTP a un MCP |
    | `SERVER` | Tu proceso **atiende** una llamada remota | El orquestador recibiendo una petición (módulo 11) |
    | `PRODUCER` / `CONSUMER` | Mensajería asíncrona (colas) | Cola de tickets (módulo 11) |

    **Contexto.** El «span activo» no es una variable global: vive en un `Context` inmutable guardado en un `contextvars.ContextVar`. Eso hace que funcione bien con `async`, pero **no** se hereda sola en hilos nuevos (lo veremos).
    **Propagación.** Para unir spans de procesos distintos, el emisor **inyecta** el contexto en una cabecera (`traceparent`) y el receptor lo **extrae** antes de crear su span.

    > 📐 **Muestreo por razón de trazas (head sampling).** `TraceIdRatioBased(p)` decide con el propio `trace_id`: se muestrea si
    > $$ \\text{trace\\_id}_{\\text{64 bits bajos}} \\;<\\; \\lfloor p\\cdot 2^{64}\\rfloor $$
    > Como la decisión es función **determinista del `trace_id`**, todos los servicios que lo aplican deciden lo mismo sin hablar entre sí. `ParentBased` respeta además la decisión ya tomada por el padre (bit *sampled* de `traceparent`).
    """)

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ---
    # 3 · A mano primero: un tracer en 40 líneas

    Para que el SDK deje de ser una caja negra, construimos un tracer con lo esencial: **ids aleatorios**, **contexto con `contextvars`**, **tiempos** y **estado de error**. (Es, de forma simplificada, lo que hace `opentelemetry-sdk`.)
    """)
    code('''
_current: contextvars.ContextVar = contextvars.ContextVar("mini_current_span", default=None)

class MiniSpan:
    def __init__(self, name, trace_id, parent_id, attrs=None):
        self.name, self.trace_id, self.parent_id = name, trace_id, parent_id
        self.span_id = secrets.token_hex(8)                      # 8 bytes aleatorios = 16 hex
        self.attrs, self.events, self.status = dict(attrs or {}), [], "UNSET"
        self.start_ns, self.end_ns = time.time_ns(), None
    def set_attribute(self, k, v): self.attrs[k] = v
    def add_event(self, name, **attrs): self.events.append({"name": name, "time_unix_nano": time.time_ns(), "attributes": attrs})

class MiniTracer:
    def __init__(self, service): self.service, self.finished = service, []
    @contextmanager
    def span(self, name, **attrs):
        parent = _current.get()                                   # ← el «contexto activo»
        s = MiniSpan(name, parent.trace_id if parent else secrets.token_hex(16), parent.span_id if parent else None, attrs)
        token = _current.set(s)                                   # este span pasa a ser el activo...
        try:
            yield s
        except BaseException as e:                                # ...y si algo falla lo anotamos y re-lanzamos
            s.status = "ERROR"; s.add_event("exception", **{"exception.type": type(e).__name__, "exception.message": str(e)}); raise
        finally:
            s.end_ns = time.time_ns(); _current.reset(token)      # ...al salir se restaura el anterior
            self.finished.append(s)                               # «exportar» = guardar en una lista

def to_record(s, service):                                        # adaptador al esquema SPAN_SCHEMA del curso (para dibujar con viz.waterfall)
    return {"trace_id": s.trace_id, "span_id": s.span_id, "parent_span_id": s.parent_id, "name": s.name, "kind": "INTERNAL", "start_unix_nano": s.start_ns,
            "end_unix_nano": s.end_ns, "status": s.status, "status_message": None, "attributes": s.attrs, "events": s.events, "resource": {"service.name": service}, "scope": "mini"}

mini = MiniTracer("supportops-agent")
with mini.span("invoke_agent supportops-agent", ticket="T-1") as root:
    time.sleep(0.01)
    with mini.span("chat mock-small", step=0): time.sleep(0.06)
    try:
        with mini.span("execute_tool get_order", step=0):
            time.sleep(0.03); raise TimeoutError("el servicio de pedidos no responde")
    except TimeoutError:
        pass                                                      # el agente se recupera, pero el span quedó en ERROR
    with mini.span("chat mock-small", step=1): time.sleep(0.05)
recs = [to_record(s, mini.service) for s in mini.finished]
print({k: recs[0][k] for k in ("trace_id", "span_id", "parent_span_id", "name")})
fig, ax = plt.subplots(figsize=(10, 2.6)); viz.waterfall(recs, ax=ax, title="Nuestro MiniTracer: 4 spans, 1 error recuperado"); plt.show()
''')
    md(observe("""
    - Los 3 spans hijos comparten el `trace_id` de la raíz y apuntan a ella con `parent_span_id`: el árbol sale **solo** de `contextvars` + `try/finally`.
    - El span rojo (`execute_tool`) tiene `ERROR` pero **la traza sigue**: un error recuperado no rompe al padre. Distinguir «error dentro de la traza» de «petición fallida» es una decisión de instrumentación.
    - Falta todo lo que hace *robusto* al SDK: límites de memoria, muestreo, ids configurables, procesamiento por lotes, hilos, exportadores y reintentos.
    """))

    md("""
    ## 3.1 Exportar a mano: OTLP/JSON

    El Collector acepta OTLP/HTTP también en **JSON** (`POST /v1/traces`, `Content-Type: application/json`; los ids van en hexadecimal y los tiempos como cadenas, como viste en el módulo 00). Convertimos nuestros `MiniSpan` y los enviamos con `urllib`:
    """)
    code('''
def av(v):                                                       # AnyValue de OTLP
    return {"boolValue": v} if isinstance(v, bool) else {"intValue": str(v)} if isinstance(v, int) else {"doubleValue": v} if isinstance(v, float) else {"stringValue": str(v)}

def otlp_json(spans, service):
    return {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": av(service)}]},
        "scopeSpans": [{"scope": {"name": "mini"}, "spans": [{
            "traceId": s.trace_id, "spanId": s.span_id, **({"parentSpanId": s.parent_id} if s.parent_id else {}),
            "name": s.name, "kind": 1, "startTimeUnixNano": str(s.start_ns), "endTimeUnixNano": str(s.end_ns),
            "attributes": [{"key": k, "value": av(v)} for k, v in s.attrs.items()],
            "events": [{"name": e["name"], "timeUnixNano": str(e["time_unix_nano"]), "attributes": [{"key": k, "value": av(v)} for k, v in e["attributes"].items()]} for e in s.events],
            "status": {"code": 2} if s.status == "ERROR" else {}} for s in spans]}]}]}

payload = otlp_json(mini.finished, "mini-demo")
print(json.dumps(payload["resourceSpans"][0]["scopeSpans"][0]["spans"][2], indent=1)[:700])
if not STACK.degraded:
    req = urllib.request.Request("http://localhost:4318/v1/traces", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=5) as r:
        print("\\nCollector respondió:", r.status, r.read().decode())
else:
    print("\\n(modo degradado: no hay Collector; el payload de arriba es lo que se enviaría)")
''')
    md("""
    > 💡 **Lo que ganas con el SDK:** el exportador oficial usa **protobuf** (más compacto que JSON), **gzip**, **reintentos con *backoff*** y un procesador por lotes que **no bloquea tu aplicación**. Nuestro `urllib` hace una llamada de red *en el hilo del agente* por traza: justo lo que no queremos.

    ## 3.2 Propagación a mano: `traceparent`

    Ya la implementaste en el módulo 02; aquí la comparamos con la del SDK para demostrar que **no hay magia**. Un detalle de actualidad: el campo `flags` ya no es solo `01`. El SDK reciente escribe `03`: el bit `0x01` es *sampled* y el bit `0x02` es el **`random-trace-id`** que añade W3C *Trace Context Level 2* («al menos los 7 bytes de la derecha del `trace_id` son aleatorios»), en el que se apoyan los muestreadores por razón de trazas.
    """)
    code('''
def format_traceparent(trace_id: str, span_id: str, flags: int = 1) -> str:
    return f"00-{trace_id}-{span_id}-{flags:02x}"

def parse_traceparent(h: str):
    ver, tid, sid, flags = h.split("-")
    assert ver == "00" and len(tid) == 32 and len(sid) == 16 and tid != "0" * 32 and sid != "0" * 16, "traceparent inválido"
    f = int(flags, 16)
    return tid, sid, {"sampled": bool(f & 1), "random_trace_id": bool(f & 2)}

# La del SDK, sobre un span real
tp_demo = TracerProvider(); t_demo = tp_demo.get_tracer("demo")
with t_demo.start_as_current_span("cliente") as sp:
    hdrs = {}; propagate.inject(hdrs)                              # ← inyecta el contexto ACTIVO en el diccionario (la «cabecera HTTP»)
    ctx = sp.get_span_context()
    flags = int(hdrs["traceparent"][-2:], 16)
    mine = format_traceparent(format(ctx.trace_id, "032x"), format(ctx.span_id, "016x"), flags)
print("SDK  :", hdrs["traceparent"]); print("mano :", mine)
print("idéntica:", hdrs["traceparent"] == mine, "· flags decodificados:", parse_traceparent(hdrs["traceparent"])[2])
''')

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ---
    # 4 · Con las herramientas de industria: el SDK, paso a paso

    ## 4.1 Proveedor, `Resource` y el primer span completo

    Un `TracerProvider` se crea **una vez** con su `Resource` y sus procesadores; de él salen *tracers* (uno por librería/módulo, con nombre y versión = el *instrumentation scope*). Para ver el span «en crudo» lo exportamos a un buffer con `ConsoleSpanExporter`:
    """)
    code('''
import io
buf = io.StringIO()
resource = Resource.create({"service.name": "supportops-agent", "service.version": "0.1.0", "deployment.environment.name": "lab"})
tp = TracerProvider(resource=resource)                                  # sampler por defecto: ParentBased(ALWAYS_ON)
tp.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter(out=buf)))   # Simple: exporta al terminar cada span (solo para depurar)
tracer = tp.get_tracer("supportops.manual", "0.1.0")                    # el instrumentation scope (nombre + versión)

with tracer.start_as_current_span("execute_tool get_order", kind=SpanKind.INTERNAL, attributes={"gen_ai.tool.name": "get_order"}) as span:
    span.set_attribute("supportops.step", 0)
    span.add_event("cache_miss", {"cache": "orders"})                   # un hito dentro del span
    try:
        raise TimeoutError("get_order: timeout tras 8 s")
    except TimeoutError as e:
        span.record_exception(e)                                         # añade un evento «exception» con tipo, mensaje y stacktrace
        span.set_status(Status(StatusCode.ERROR, "timeout"))             # y marca el span como fallido

doc = json.loads(buf.getvalue())
print(json.dumps({k: doc[k] for k in ("name", "kind", "status", "attributes", "resource")}, indent=1, ensure_ascii=False)[:900])
print("eventos:", [e["name"] for e in doc["events"]], "· scope:", doc.get("instrumentation_scope", {}).get("name"))
''')
    md("""
    Fíjate en tres cosas que el SDK añadió solo: `telemetry.sdk.*` en el `Resource`, el `trace_id`/`span_id` y el evento `exception` con el *stacktrace* completo.

    ### Cómo usar la API sin equivocarse

    | Quiero… | Llamada | Notas |
    |---|---|---|
    | Un span que sea el **activo** durante un bloque | `with tracer.start_as_current_span(name, ...)` | El caso normal. Cierra y restaura el contexto al salir; registra excepciones y pone `ERROR` si se propaga |
    | Un span que **no** sea el activo | `span = tracer.start_span(name)` … `span.end()` | Tú gestionas `end()`. Úsalo con `trace.use_span(span, end_on_exit=True)` si quieres activarlo |
    | Fijar tiempos propios | `start_span(..., start_time=ns)` · `span.end(end_time=ns)` | Es lo que hace el instrumentor de SupportOps con el reloj simulado |
    | Un **link** a otro span | `start_span(..., links=[trace.Link(ctx, attrs)])` | Reintentos, colas, *fan-in*: relación sin padre-hijo |
    | Renombrar | `span.update_name(...)` | Evítalo: el sampler vio el nombre original |
    | Saber si merece la pena calcular algo caro | `span.is_recording()` | Evita serializar *prompts* si el span no se graba |
    """)
    code('''
# Links: un reintento que apunta al intento fallido (mismo trace aquí, pero podría ser otra traza)
mem_l = InMemorySpanExporter(); tp_l = TracerProvider(); tp_l.add_span_processor(SimpleSpanProcessor(mem_l)); tr_l = tp_l.get_tracer("links")
with tr_l.start_as_current_span("invoke_agent") as root:
    with tr_l.start_as_current_span("chat attempt-0") as bad:
        bad.set_status(Status(StatusCode.ERROR, "503"))
    failed_ctx = bad.get_span_context()
    with tr_l.start_as_current_span("chat attempt-1", links=[trace.Link(failed_ctx, {"supportops.reason": "retry_after_503"})]) as retry:
        pass
r = [s for s in mem_l.get_finished_spans() if s.name == "chat attempt-1"][0]
print("link ->", format(r.links[0].context.span_id, "016x") == format(failed_ctx.span_id, "016x"), r.links[0].attributes)

# Límites: el SDK acota atributos y eventos por span (spec: 128 por defecto)
mem_b = InMemorySpanExporter(); tp_b = TracerProvider(); tp_b.add_span_processor(SimpleSpanProcessor(mem_b)); tr_b = tp_b.get_tracer("limits")
with tr_b.start_as_current_span("ancho") as s:
    for i in range(200): s.set_attribute(f"k{i:03d}", i)
    for i in range(200): s.add_event(f"e{i}")
big = mem_b.get_finished_spans()[0]
print(f"atributos guardados={len(big.attributes)} descartados={big.dropped_attributes} · eventos guardados={len(big.events)} descartados={big.dropped_events}")
print("claves conservadas:", min(big.attributes), "…", max(big.attributes), "→ se descartan las MÁS ANTIGUAS (k000…k071)")
''')
    md("""
    > 🧠 Un span con cientos de atributos no es «más información»: es información **silenciosamente truncada**. En Python el SDK descarta los atributos **más antiguos** al llegar a 128 y solo deja un aviso en el log del propio SDK (`dropped_attributes`). Si necesitas más, sube `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`; mejor aún, reparte la información entre spans y eventos.

    ## 4.2 Contexto activo, `start_span` vs `start_as_current_span` y los hilos
    """)
    code('''
mem_c = InMemorySpanExporter(); tp_c = TracerProvider(); tp_c.add_span_processor(SimpleSpanProcessor(mem_c)); tr_c = tp_c.get_tracer("ctx")
with tr_c.start_as_current_span("A") as a:
    b = tr_c.start_span("B")                                   # hijo de A (hereda el activo), pero NO pasa a ser el activo
    print("tras start_span, el activo sigue siendo A:", trace.get_current_span() is a)
    with trace.use_span(b, end_on_exit=True):                  # ahora sí: B activo
        c = tr_c.start_span("C"); c.end()                      # C nace hijo de B
by_name = {s.name: s for s in mem_c.get_finished_spans()}
par = lambda n: next((k for k, v in by_name.items() if by_name[n].parent and v.context.span_id == by_name[n].parent.span_id), None)
print({n: par(n) for n in "ABC"})
''')
    md("""
    El contexto activo vive en un `ContextVar`, y los **hilos nuevos empiezan con el contexto vacío**. Un `ThreadPoolExecutor` (muy típico para ejecutar herramientas en paralelo) rompe la traza si no copias el contexto. `asyncio`, en cambio, copia el contexto en cada `create_task`:
    """)
    code('''
import asyncio

def trace_count(runner) -> int:
    m = InMemorySpanExporter(); p = TracerProvider(); p.add_span_processor(SimpleSpanProcessor(m)); t = p.get_tracer("x")
    def work(i):
        with t.start_as_current_span(f"tool-{i}"): time.sleep(0.001)
    with t.start_as_current_span("invoke_agent"):
        runner(work)
    return len({s.context.trace_id for s in m.get_finished_spans()})

def run_threads_naive(work):
    with ThreadPoolExecutor(4) as ex: list(ex.map(work, range(4)))

def run_threads_ctx(work):
    with ThreadPoolExecutor(4) as ex:
        futs = [ex.submit(contextvars.copy_context().run, work, i) for i in range(4)]     # ← copia el contexto actual al hilo
        [f.result() for f in futs]

def run_asyncio(work):
    async def main():
        await asyncio.gather(*[asyncio.create_task(asyncio.to_thread(work, i)) for i in range(4)])      # to_thread copia el contexto
    ctx = contextvars.copy_context()
    th = threading.Thread(target=ctx.run, args=(asyncio.run, main())); th.start(); th.join()           # (Jupyter ya tiene un bucle: usamos otro hilo)

results = {"hilos sin copiar\\ncontexto": trace_count(run_threads_naive), "hilos con\\ncopy_context().run": trace_count(run_threads_ctx), "asyncio.create_task\\n+ to_thread": trace_count(run_asyncio)}
fig, ax = plt.subplots(figsize=(8, 3.2)); bars = ax.bar(list(results), list(results.values()), color=[viz.PALETTE["error"], viz.PALETTE["ok"], viz.PALETTE["ok"]])
ax.bar_label(bars); ax.axhline(1, color="k", ls=":"); ax.set_ylabel("trazas resultantes\\n(debería ser 1)"); ax.set_title("1 petición con 4 herramientas en paralelo"); plt.show()
''')
    md(observe("""
    - Sin copiar el contexto, cada herramienta lanzada en un hilo crea **su propia traza huérfana** (1 + 4 = 5 trazas): en Tempo verías 4 trazas de un solo span y una traza raíz «incompleta». Es el bug de propagación **más frecuente** en agentes con herramientas en paralelo.
    - `contextvars.copy_context().run(fn, ...)` o `asyncio` (que copia el contexto por tarea) lo arreglan. Las librerías de instrumentación (`opentelemetry-instrumentation-threading`) lo automatizan, pero hay que saber que el problema existe.
    - **Síntoma para el on-call:** muchas trazas de 1 span con `parent_span_id` vacío y nombres de herramienta. Lo buscaremos con TraceQL en el módulo 07.
    """))

    md("""
    ## 4.3 Propagación entre servicios por HTTP (de verdad)

    Montamos un mini servidor HTTP en el propio notebook (hilo aparte) que hace de servicio de pedidos con su **propio `TracerProvider`** (otro `service.name`), y un cliente que lo llama como `CLIENT`. Probamos con y sin `inject`:
    """)
    code('''
mem_h = InMemorySpanExporter()
def provider(svc):
    p = TracerProvider(resource=Resource.create({"service.name": svc})); p.add_span_processor(SimpleSpanProcessor(mem_h)); return p
t_orch = provider("supportops-orchestrator").get_tracer("demo"); t_orders = provider("supportops-orders").get_tracer("demo")

class OrdersHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        carrier = {k.lower(): v for k, v in self.headers.items()}       # ¡las cabeceras HTTP no distinguen mayúsculas, el diccionario sí!
        ctx = propagate.extract(carrier)                                # ← extrae traceparent -> Context (vacío si no hay cabecera)
        with t_orders.start_as_current_span("GET /orders/{id}", context=ctx, kind=SpanKind.SERVER):
            time.sleep(0.005); body = b'{"status": "shipped"}'
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *a): pass

srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), OrdersHandler); threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = f"http://127.0.0.1:{srv.server_port}/orders/ORD-00017"
no_proxy = urllib.request.build_opener(urllib.request.ProxyHandler({}))      # el sandbox/empresa puede tener un proxy: evítalo para localhost

def call_orders(do_inject: bool):
    with t_orch.start_as_current_span("execute_tool get_order", kind=SpanKind.CLIENT):
        headers = {}
        if do_inject: propagate.inject(headers)                         # ← escribe traceparent con el span ACTIVO (el CLIENT)
        no_proxy.open(urllib.request.Request(URL, headers=headers), timeout=5).read()
    return headers

h_ok = call_orders(True); n_ok = len(mem_h.get_finished_spans())
h_bad = call_orders(False)
recs = []
for s in mem_h.get_finished_spans():
    c = s.get_span_context()
    recs.append({"trace_id": format(c.trace_id, "032x"), "span_id": format(c.span_id, "016x"), "parent_span_id": format(s.parent.span_id, "016x") if s.parent else None,
                 "name": f"[{s.resource.attributes['service.name'].replace('supportops-', '')}] {s.name}", "kind": s.kind.name, "start_unix_nano": s.start_time, "end_unix_nano": s.end_time, "status": "UNSET"})
good, bad = recs[:n_ok], recs[n_ok:]
fig, axes = plt.subplots(2, 1, figsize=(10, 4.6)); fig.subplots_adjust(left=0.3, hspace=0.9)
viz.waterfall(good, ax=axes[0], title=f"CON inject/extract → {len({r['trace_id'] for r in good})} traza, 2 servicios")
viz.waterfall(bad, ax=axes[1], title=f"SIN inject → {len({r['trace_id'] for r in bad})} trazas rotas (dos raíces)")
plt.show()
print("cabecera enviada:", h_ok)
''')
    md(observe("""
    - **Izquierda:** el span `SERVER` del servicio de pedidos es hijo del span `CLIENT` del orquestador y comparten `trace_id`: Tempo mostrará **una** traza con **dos** servicios. La cabecera `traceparent` (ver impresión) es lo único que cruzó la red.
    - **Derecha:** si el cliente olvida `inject` (o el servidor no hace `extract`), aparecen **dos trazas** independientes. Ninguna da error: la telemetría «funciona» pero ya no puedes seguir una petición de extremo a extremo.
    - Detalle clave que rompe muchas implementaciones caseras: **los nombres de cabecera HTTP no distinguen mayúsculas, pero un `dict` de Python sí** (por eso `k.lower()`).
    - Esto es exactamente lo que necesitarás en el módulo 11 (multi-agente) y el 12 (MCP).
    """))

    md("""
    ## 4.4 `SimpleSpanProcessor` vs `BatchSpanProcessor`

    El procesador decide **cuándo** y **cómo** salen los spans del proceso:

    | | `SimpleSpanProcessor` | `BatchSpanProcessor` |
    |---|---|---|
    | Exporta | **Síncrono**, en el hilo de la aplicación, al terminar cada span | En un **hilo en segundo plano**, por lotes |
    | Latencia añadida a tu código | La del exportador (red) en **cada** span | Casi nula (encolar) |
    | Si el destino va lento | Tu agente va lento | Se llena la cola y se **descartan** spans |
    | Uso | Depuración, tests | **Producción** |

    Parámetros del Batch (valores por defecto de la spec y de las variables `OTEL_BSP_*`): `max_queue_size=2048`, `max_export_batch_size=512`, `schedule_delay=5000 ms`, `export_timeout=30000 ms`.
    Medimos con un exportador artificialmente lento (10 ms por llamada, como una red mediocre):
    """)
    code('''
class SlowExporter(SpanExporter):
    """Exportador de pruebas: tarda `delay` s por lote y registra qué `seq` recibió."""
    def __init__(self, delay): self.delay, self.seq, self.calls = delay, [], 0
    def export(self, spans): time.sleep(self.delay); self.calls += 1; self.seq += [s.attributes.get("seq") for s in spans]; return SpanExportResult.SUCCESS
    def shutdown(self): pass

def bench(make_proc, n=100, delay=0.01):
    exp = SlowExporter(delay); p = TracerProvider(); proc = make_proc(exp); p.add_span_processor(proc); t = p.get_tracer("b")
    t0 = time.perf_counter()
    for i in range(n):
        with t.start_as_current_span("s", attributes={"seq": i}): pass
    app = time.perf_counter() - t0                                # lo que «paga» tu aplicación
    proc.force_flush(30000); total = time.perf_counter() - t0
    return {"app_s": app, "total_s": total, "llamadas": exp.calls, "spans": len(exp.seq)}

R = {"Simple": bench(lambda e: SimpleSpanProcessor(e)), "Batch": bench(lambda e: BatchSpanProcessor(e, schedule_delay_millis=100))}
fig, axes = plt.subplots(1, 2, figsize=(11, 3.2))
axes[0].bar(list(R), [v["app_s"] * 1000 / 100 for v in R.values()], color=[viz.PALETTE["error"], viz.PALETTE["ok"]]); axes[0].set_ylabel("ms añadidos por span\\nen el hilo de la aplicación"); axes[0].set_title("Coste para tu código")
axes[1].bar(list(R), [v["llamadas"] for v in R.values()], color=[viz.PALETTE["error"], viz.PALETTE["ok"]]); axes[1].set_ylabel("llamadas al exportador (100 spans)"); axes[1].set_title("Viajes de red")
plt.tight_layout(); plt.show()
print({k: {a: round(b, 3) for a, b in v.items()} for k, v in R.items()})
''')
    md(observe("""
    - Con `Simple`, cada span paga la latencia del exportador (≈ 10 ms) **dentro de tu agente**: 100 spans ≈ 1 s extra. Con `Batch`, el coste para la aplicación es de microsegundos por span y los 100 spans salen en **una o pocas llamadas**.
    - Los valores absolutos dependen de tu máquina; lo que debe mantenerse es la **proporción** (Simple ≫ Batch en el hilo de la aplicación).
    - El precio del Batch: si el proceso muere sin `force_flush()/shutdown()`, los spans en cola se pierden (por eso `tel.shutdown()` al final).
    """))

    md("""
    ### ¿Qué pasa cuando la cola se llena?

    📐 Un exportador que tarda $d$ segundos por lote de $B$ spans sostiene como máximo $\\;\\lambda_{\\max}=B/d\\;$ spans/s. Si tu aplicación produce $\\lambda>\\lambda_{\\max}$ de forma sostenida, la cola (tamaño $Q$) se llena en $\\;t = Q/(\\lambda-\\lambda_{\\max})\\;$ y **a partir de ahí se descartan spans**.
    Ejemplo: $B=512$, $d=0.2$ s ⇒ $\\lambda_{\\max}=2560$ spans/s; con $\\lambda=3000$ y $Q=2048$ la cola aguanta $2048/440\\approx 4{,}7$ s.

    Lo comprobamos con una cola pequeña ($Q=64$, lotes de 64, 20 ms por lote) frente a una grande ($Q=2048$), enviando 1000 spans numerados de golpe:
    """)
    code('''
def burst(queue, n=1000):
    exp = SlowExporter(0.02); p = TracerProvider(); proc = BatchSpanProcessor(exp, max_queue_size=queue, max_export_batch_size=min(512, queue), schedule_delay_millis=50)
    p.add_span_processor(proc); t = p.get_tracer("b")
    for i in range(n):
        with t.start_as_current_span("s", attributes={"seq": i}): pass
    proc.force_flush(30000)
    return sorted(exp.seq)

fig, axes = plt.subplots(2, 1, figsize=(11, 3.6), sharex=True)
for ax, q in zip(axes, (64, 2048)):
    seq = burst(q); ax.vlines(seq, 0, 1, color=viz.PALETTE["traces"], lw=0.6); ax.set_yticks([]); ax.set_xlim(0, 1000)
    ax.set_title(f"cola = {q}: se exportaron {len(seq)} de 1000 spans ({1 - len(seq)/1000:.0%} perdidos)", loc="left", fontsize=10)
axes[1].set_xlabel("número de secuencia del span (orden de creación)")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con la cola pequeña faltan **grandes tramos contiguos** (el hueco central) y sobreviven sobre todo los **más recientes**: el SDK de Python, al llenarse, descarta los elementos **más antiguos** de la cola.
    - Con la cola grande no se pierde ninguno. En producción el aviso (`Queue full, dropping Span`) sale en el log del SDK: **si nadie mira ese log, pierdes trazas sin enterarte**. Las versiones recientes del SDK exponen métricas internas de la cola; el Collector (módulo 05) también cuenta lo que rechaza.
    - Tras una ráfaga, el «hueco» no está repartido al azar: puedes perder **trazas enteras de un incidente**, justo cuando más las necesitas.
    """))

    md("""
    ## 4.5 Samplers: decidir antes de crear datos (head sampling)

    El `Sampler` se ejecuta al **crear** el span y decide si se graba y se exporta. El módulo 18 trata el muestreo a fondo; aquí lo mínimo para no equivocarte al instrumentar.
    """)
    code('''
def kept_ratio(sampler, n=3000):
    m = InMemorySpanExporter(); p = TracerProvider(sampler=sampler); p.add_span_processor(SimpleSpanProcessor(m)); t = p.get_tracer("s")
    for _ in range(n):
        with t.start_as_current_span("root"):
            with t.start_as_current_span("child"): pass
    spans = m.get_finished_spans()
    roots = sum(s.name == "root" for s in spans); kids = sum(s.name == "child" for s in spans)
    return roots / n, kids / max(roots, 1)

ps = [0.01, 0.1, 0.5, 1.0]
meas = [kept_ratio(sampling.ParentBased(sampling.TraceIdRatioBased(p))) for p in ps]
fig, ax = plt.subplots(figsize=(7.5, 3.2)); x = np.arange(len(ps))
ax.bar(x - 0.2, ps, 0.4, label="configurado", color=viz.PALETTE["neutral"]); ax.bar(x + 0.2, [m[0] for m in meas], 0.4, label="trazas conservadas (medido)", color=viz.PALETTE["traces"])
ax.set_xticks(x, [f"{p:.0%}" for p in ps]); ax.set_ylabel("fracción de trazas"); ax.legend(); ax.set_title("ParentBased(TraceIdRatioBased(p)) sobre 3000 trazas de 2 spans"); plt.show()
print("hijos conservados cuando su raíz se conserva:", [m[1] for m in meas], "(la decisión del padre se hereda: nunca hay trazas a medias)")
''')
    code('''
# ¿Qué ve el sampler? Solo lo que le das AL CREAR el span.
seen = []
class Spy(sampling.Sampler):
    def should_sample(self, parent_context, trace_id, name, kind=None, attributes=None, links=None, trace_state=None):
        seen.append({"name": name, "attributes": dict(attributes or {})})
        return sampling.SamplingResult(sampling.Decision.RECORD_AND_SAMPLE)
    def get_description(self): return "Spy"

tp_spy = TracerProvider(sampler=Spy()); tr_spy = tp_spy.get_tracer("spy")
s = tr_spy.start_span("chat mock-small", attributes={"gen_ai.operation.name": "chat"})   # visible para el sampler
s.set_attribute("supportops.customer.tier", "premium")                                     # tardío: el sampler NUNCA lo verá
s.end()
print(seen)
''')
    md("""
    > 🧠 **Consecuencia directa para agentes:** si algún día quieres muestrear «más los clientes *premium*» o «todas las llamadas `chat` al modelo grande» **con head sampling**, ese atributo tiene que pasarse en `start_span(attributes=...)`. Por eso la spec GenAI marca ciertos atributos como *sampling relevant* y pide darlos **al crear el span** (módulo 04). Para decidir por resultado (error, latencia), necesitarás *tail sampling* (módulo 18).
    """)

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ---
    # 5 · Exportar de verdad: OTLP/HTTP hacia el Collector

    El exportador OTLP envía los spans al **Collector** (que los reenviará a Tempo). Hay dos transportes: **OTLP/HTTP** (`:4318`, protobuf por `POST /v1/traces`) y **OTLP/gRPC** (`:4317`). En el curso usamos HTTP por ser más sencillo de depurar y más robusto con `fork` (ver 🧠). Se configura por **código** o por **variables de entorno estándar** (que ganan si no pasas el argumento):

    | Variable | Para qué | Valor en el curso |
    |---|---|---|
    | `OTEL_SERVICE_NAME` | `service.name` del Resource | `supportops-agent` |
    | `OTEL_RESOURCE_ATTRIBUTES` | Atributos extra del Resource (`k1=v1,k2=v2`) | `service.version=0.1.0` |
    | `OTEL_EXPORTER_OTLP_ENDPOINT` | URL **base** (el SDK añade `/v1/traces`…) | `http://localhost:4318` |
    | `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` o `grpc` | `http/protobuf` |
    | `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | URL **completa** de una señal (no se le añade ruta) | — |
    | `OTEL_EXPORTER_OTLP_COMPRESSION` | `gzip` | opcional |
    | `OTEL_TRACES_SAMPLER` / `_ARG` | Sampler (`parentbased_traceidratio`, `0.1`) | por defecto: todo |
    | `OTEL_BSP_*` | Parámetros del Batch | ver 4.4 |

    Un error clásico: poner `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318/v1/traces` (el SDK añadiría `/v1/traces` otra vez → 404) o la inversa con la variable *específica* de señal.
    """)
    code('''
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http import Compression

ENDPOINT = "http://localhost:4318"
tp_otlp = TracerProvider(resource=Resource.create({"service.name": "lesson03-otlp", "service.version": "0.1.0"}))
exporter = OTLPSpanExporter(endpoint=f"{ENDPOINT}/v1/traces", compression=Compression.Gzip, timeout=5)    # con el argumento endpoint, la URL va COMPLETA
if STACK.degraded:                                                       # sin Collector, el exportador reintentaría con backoff: usamos memoria
    exporter = InMemorySpanExporter(); print("(modo degradado: exportador en memoria en lugar de OTLP)")
tp_otlp.add_span_processor(BatchSpanProcessor(exporter, schedule_delay_millis=500))
tr_otlp = tp_otlp.get_tracer("lesson03")

with tr_otlp.start_as_current_span("hola-tempo", attributes={"curso": "observabilidad-agentes"}) as sp:
    with tr_otlp.start_as_current_span("paso-interno"): time.sleep(0.02)
    HOLA_ID = format(sp.get_span_context().trace_id, "032x")
print("trace_id:", HOLA_ID, "· flush OK:", tp_otlp.force_flush(5000))
''')
    code('''
def wait_for_trace(trace_id, timeout_s=45):
    """Tempo tarda de unos segundos a ~30 s en servir una traza nueva: sondeamos con plazo."""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            d = backends.tempo_trace(trace_id)
            spans = [s for b in d.get("batches", d.get("resourceSpans", [])) for ss in b.get("scopeSpans", []) for s in ss.get("spans", [])]
            if spans: return spans
        except backends.BackendError:
            pass
        time.sleep(2)
    return None

if STACK.degraded:
    print("Modo degradado: sin Collector/Tempo no hay nada que consultar. Levanta el stack con:\\n  ", STACK.command)
else:
    got = wait_for_trace(HOLA_ID)
    print("Tempo devolvió", len(got) if got else 0, "spans:", [s["name"] for s in got] if got else "(aún no indexada: reintenta la celda)")
''')
    md("""
    > ⚠️ **Si no aparece nada:** (1) ¿corre el Collector? `check_stack()` lo dice; (2) ¿flush? sin `force_flush()` el Batch espera hasta 5 s por defecto; (3) ¿URL duplicada o puerto equivocado (4317 es gRPC)?; (4) Tempo tarda hasta ~30 s: es normal (live-store). Sondea con plazo, nunca con `sleep` fijo.

    ---
    # 6 · SupportOps v1: instrumentación manual de verdad

    Ahora aplicamos todo al agente. El punto de extensión `Instrumentor` (módulo 01) nos da tres *context managers* (`agent_run`, `llm_call`, `tool_call`) y un `log`. Escribimos una **versión mínima a mano** sobre el SDK:
    """)
    code('''
class ManualInstrumentor(Instrumentor):
    """Instrumentación mínima: 3 tipos de span con tiempos del reloj simulado. Sin métricas, logs ni captura de contenido."""
    def __init__(self, tracer): self.tracer = tracer

    @contextmanager
    def _span(self, ctx, name, kind, attrs):
        span = self.tracer.start_span(name, kind=kind, attributes=attrs, start_time=ctx.clock.now_ns())      # atributos AL CREAR
        t0 = ctx.clock.now_ns()
        try:
            with trace.use_span(span, end_on_exit=False, record_exception=False, set_status_on_exception=False):
                yield span
        except BaseException as e:
            span.record_exception(e, timestamp=ctx.clock.now_ns())
            span.set_attribute("error.type", str(getattr(e, "error_type", type(e).__name__)))
            span.set_status(Status(StatusCode.ERROR, str(e)[:120])); raise
        finally:
            span.end(end_time=max(ctx.clock.now_ns(), t0))

    @contextmanager
    def agent_run(self, ctx):
        t = ctx.ticket
        with self._span(ctx, f"invoke_agent {ctx.agent_name}", SpanKind.INTERNAL, {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": ctx.agent_name,
                        "supportops.ticket.id": t.ticket_id, "supportops.customer.tier": t.tier}) as span:
            yield
            if ctx.result: span.set_attributes({"supportops.status": ctx.result.status, "gen_ai.usage.input_tokens": ctx.result.input_tokens, "gen_ai.usage.output_tokens": ctx.result.output_tokens})

    @contextmanager
    def llm_call(self, ctx, info):
        with self._span(ctx, f"chat {info.model}", SpanKind.CLIENT, {"gen_ai.operation.name": "chat", "gen_ai.provider.name": info.provider, "gen_ai.request.model": info.model}) as span:
            yield
            if info.response: span.set_attributes({"gen_ai.usage.input_tokens": info.response.usage.input_tokens, "gen_ai.usage.output_tokens": info.response.usage.output_tokens})

    @contextmanager
    def tool_call(self, ctx, info):
        with self._span(ctx, f"execute_tool {info.call.name}", SpanKind.INTERNAL, {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": info.call.name}):
            yield

mem_m = InMemorySpanExporter(); tp_m = TracerProvider(resource=Resource.create({"service.name": "supportops-agent"})); tp_m.add_span_processor(SimpleSpanProcessor(mem_m))
agent_m = SupportAgent(instrumentor=ManualInstrumentor(tp_m.get_tracer("supportops.manual")))
N = 40 if FAST_DEV_RUN else 400
tickets = generate_tickets(N, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, start_s="live" if not STACK.degraded else SIM_EPOCH_S)
results_m = run_tickets(agent_m, tickets)
sp_m = mem_m.get_finished_spans()
print(f"{len(tickets)} tickets → {len(sp_m)} spans · {len({s.context.trace_id for s in sp_m})} trazas · errores: {sum(s.status.status_code == StatusCode.ERROR for s in sp_m)} spans")
''')
    md("""
    Cuatro decisiones de diseño que merece la pena entender:

    1. **Tiempos simulados** (`start_time=ctx.clock.now_ns()`): el notebook corre en ms y las duraciones son las del modelo de latencia. En tu servicio real **no** pasarías tiempos: el SDK usa el reloj de pared.
    2. **Atributos al crear el span** (los de muestreo) y los de resultado **al cerrar** (`tokens`, `status`).
    3. **`CLIENT` para el LLM, `INTERNAL` para el agente y las herramientas locales**; las herramientas remotas (MCP, módulo 12) serían `CLIENT`.
    4. **Un fallo marca el span en `ERROR`** y registra la excepción; pero un fallo *recuperado* por el agente (reintento) deja la raíz sin error.

    ### La versión de referencia: `supportops.telemetry`

    El paquete incluye la versión **consolidada** que reutilizarán los módulos siguientes: `setup_telemetry()` + `OTelInstrumentor`. Añade a lo anterior: **logs con `trace_id`**, métricas mínimas, captura de contenido *opt-in*, ids deterministas para tests y modo degradado.
    """)
    code('''
tel = setup_telemetry("supportops-agent", metric_interval_s=2)          # auto: OTLP si el Collector responde; si no, memoria (con aviso)
print("modo:", tel.mode, "·", tel.endpoint or tel.reason)
instr = OTelInstrumentor(tel)
agent = SupportAgent(instrumentor=instr)
results = run_tickets(agent, tickets)
tel.force_flush()
spans_df = pd.DataFrame(tel.span_records()); spans_df["dur"] = (spans_df.end_unix_nano - spans_df.start_unix_nano) / 1e9
logs_df = pd.DataFrame(tel.log_records())
print(f"{len(spans_df)} spans · {spans_df.trace_id.nunique()} trazas · {len(logs_df)} logs · export: {tel.span_export_stats or '(solo memoria)'}")
spans_df[["name", "kind", "status", "dur"]].head(6)
''')
    code('''
# Una traza concreta: la más lenta con algún error recuperado, si existe
err_traces = spans_df[spans_df.status == "ERROR"].trace_id.unique()
pick = spans_df[spans_df.trace_id.isin(err_traces)].groupby("trace_id").dur.max().idxmax() if len(err_traces) else spans_df.groupby("trace_id").dur.max().idxmax()
one = [s for s in tel.span_records() if s["trace_id"] == pick]
fig, ax = plt.subplots(figsize=(11, 0.45 * len(one) + 1.4)); fig.subplots_adjust(left=0.3)
viz.waterfall(one, ax=ax, title=f"Traza de SupportOps v1 · {pick[:8]}… · {len(one)} spans"); plt.show()
ev = [(s["name"], e["name"]) for s in one for e in s["events"]]
print("eventos:", ev)
''')
    md(observe("""
    - Árbol esperado: `invoke_agent` (raíz, INTERNAL) → varios `chat` (CLIENT) alternados con `execute_tool` (INTERNAL). Las barras **rojas** son spans con `status=ERROR`.
    - Un `chat` rojo seguido de otro `chat` = **reintento tras un 5xx/429** del proveedor: lo verás como dos spans hermanos, el primero con evento `exception`.
    - La suma de las barras hijas ≈ duración del padre: el agente pasa casi todo el tiempo **esperando** al LLM y a las herramientas (no calculando). Ese es el perfil típico de latencia de un agente.
    """))

    md("""
    ### Los logs heredan el contexto: correlación gratis

    El `Instrumentor.log` de SupportOps llega a un `LogRecord` de OpenTelemetry **emitido dentro del span activo**: el SDK toma `trace_id`/`span_id` del contexto, sin que tú los pases. Esa es la correlación que en Loki permitirá saltar de la traza a sus logs (módulo 08).
    """)
    code('''
roots = spans_df[spans_df.parent_span_id.isna()]
cover = logs_df.trace_id.notna().mean()
known = set(spans_df.trace_id)
print(f"logs con trace_id: {cover:.0%} · apuntan a una traza existente: {logs_df.trace_id.isin(known).mean():.0%}")
t_pick = logs_df[logs_df.trace_id == pick]
print(t_pick[["severity_text", "body"]].assign(span=t_pick.span_id.str[:6]).to_string(index=False))
print("\\nmétricas mínimas (lo ampliará el módulo 09):")
print(pd.DataFrame(tel.metric_points())[["name", "unit", "type"]].drop_duplicates().to_string(index=False))
''')
    code('''
# Verificación en los backends reales (solo si el stack está arriba)
if tel.mode == "otlp":
    one_id = instr.trace_ids[tickets[0].ticket_id]
    sp = wait_for_trace(one_id)
    print(f"Tempo: traza {one_id[:8]}… →", len(sp) if sp else "aún no disponible", "spans (esperados:", len([s for s in tel.span_records() if s['trace_id'] == one_id]), ")")
    for _ in range(10):
        lg = backends.loki_query(f'{{service_name="supportops-agent"}} | trace_id="{one_id}"', minutes=180)
        if lg: break
        time.sleep(2)
    print("Loki:", len(lg), "líneas con ese trace_id")
    print("TraceQL en Tempo:", backends.tempo_search('{ resource.service.name = "supportops-agent" && span.gen_ai.operation.name = "chat" }', minutes=180, limit=3).get("traces", [])[:1] and "ok")
else:
    print("Modo degradado: la telemetría se quedó en memoria (tel.mode == 'memory'). Con el stack arriba, esta celda consulta Tempo y Loki.")
''')

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ---
    # 7 · Experimentos: qué cuentan nuestras trazas y cuánto cuesta producirlas
    """)
    code('''
sd = spans_df.assign(tipo=spans_df.name.str.split().str[0]); roots = sd[sd.parent_span_id.isna()].copy()
roots["in_tok"] = roots.attributes.map(lambda a: a.get("gen_ai.usage.input_tokens", 0)); cnt = sd.groupby("trace_id").size()
fig, axes = plt.subplots(1, 3, figsize=(15, 3.7))
order = ["invoke_agent", "chat", "execute_tool"]
axes[0].boxplot([sd[sd.tipo == k].dur for k in order], tick_labels=order); axes[0].set_yscale("log"); axes[0].set_ylabel("duración (s, escala log)"); axes[0].set_title("Duración por tipo de span")
axes[1].hist(cnt, bins=range(1, int(cnt.max()) + 2), color=viz.PALETTE["traces"], align="left", rwidth=.85); axes[1].set_xlabel("spans por traza"); axes[1].set_ylabel("nº de trazas"); axes[1].set_title("Tamaño de las trazas")
ok = roots.status != "ERROR"
axes[2].scatter(roots[ok].in_tok, roots[ok].dur, c=viz.PALETTE["traces"], s=22, alpha=.7, label="OK"); axes[2].scatter(roots[~ok].in_tok, roots[~ok].dur, c=viz.PALETTE["error"], s=26, label="ERROR")
axes[2].set_xlabel("tokens de entrada acumulados (invoke_agent)"); axes[2].set_ylabel("duración (s)"); axes[2].set_title("Coste vs. latencia por petición"); axes[2].legend()
plt.tight_layout(); plt.show()
print("mediana de duración por tipo:", sd.groupby("tipo").dur.median().round(2).to_dict(), "· spans/traza (media):", round(cnt.mean(), 1))
''')
    md(observe("""
    - **Duración (izq.):** `chat` (el LLM) y `execute_tool` están en el rango de cientos de ms; `invoke_agent` es la suma. Los *outliers* altos son el 2 % de cola lenta natural del mock y los fallos inyectados (`latency_spike`, `tool_timeout`).
    - **Tamaño (centro):** la mayoría de trazas tienen pocos spans, pero hay una **cola larga** (reintentos, bucles de herramientas): el número de spans por traza ya es una señal de salud del agente.
    - **Coste vs latencia (dcha.):** los tokens de entrada crecen con cada paso (el contexto se acumula); las peticiones con más pasos son más lentas **y** más caras. Los puntos rojos son peticiones fallidas: no siempre son las más lentas.
    """))

    md("""
    ## 7.1 ¿Cuánto cuesta instrumentar? Un microbenchmark honesto

    Todo span consume CPU y memoria **en el proceso del agente**. Medimos el sobrecoste por span en seis configuraciones, repitiendo cada medida 3 veces y quedándonos con la mínima (la menos ruidosa). El tiempo del agente es simulado, así que lo medido es el coste **real de la instrumentación** más el trabajo propio del agente (que restamos con la línea base).
    """)
    code('''
class NullExporter(SpanExporter):
    def export(self, spans): return SpanExportResult.SUCCESS
    def shutdown(self): pass

def timed(make_instr, n=100, reps=3):
    tk = generate_tickets(n, seed=SEED, fault_rates=DEFAULT_FAULT_RATES); best, n_spans = 1e9, 0
    for _ in range(reps):
        instr = make_instr(); ag = SupportAgent(instrumentor=instr)
        t0 = time.perf_counter(); res = run_tickets(ag, tk); best = min(best, time.perf_counter() - t0)
        n_spans = sum(1 + r.n_llm_calls + r.n_tool_calls for r in res)
        if hasattr(instr, "h"): instr.h.shutdown()
    return best, n_spans

def manual(sampler=None, batch=True):
    p = TracerProvider(sampler=sampler or sampling.ALWAYS_ON)
    p.add_span_processor(BatchSpanProcessor(NullExporter()) if batch else SimpleSpanProcessor(NullExporter()))
    return ManualInstrumentor(p.get_tracer("bench"))

variants = {
    "sin instrumentar": lambda: Instrumentor(),
    "Recording (puro Python)": lambda: RecordingInstrumentor(),
    "SDK · sampler OFF": lambda: manual(sampling.ALWAYS_OFF),
    "SDK · Batch + exp. nulo": lambda: manual(),
    "OTelInstrumentor\\n(spans+logs+métricas)": lambda: OTelInstrumentor(setup_telemetry("bench", mode="memory", set_global=False)),
    "OTelInstrumentor\\n+ captura contenido": lambda: OTelInstrumentor(setup_telemetry("bench", mode="memory", set_global=False), capture_content=True),
}
meas = {k: timed(f) for k, f in variants.items()}; base_t, n_sp = meas["sin instrumentar"]
over = {k: max(0.0, (t - base_t) / n * 1e6) for k, (t, n) in meas.items() if k != "sin instrumentar"}
fig, ax = plt.subplots(figsize=(10, 3.6)); bars = ax.barh(list(over), list(over.values()), color=[viz.PALETTE["neutral"], viz.PALETTE["ok"], viz.PALETTE["traces"], viz.PALETTE["metrics"], viz.PALETTE["error"]])
ax.bar_label(bars, fmt="%.0f µs"); ax.set_xlabel("sobrecoste medio por span (µs)"); ax.set_title(f"Coste de instrumentar (≈ {n_sp / 100:.1f} spans por ticket)"); ax.invert_yaxis(); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con el **sampler en OFF** el coste baja (los spans no se graban ni se encolan, aunque el instrumentor sigue ejecutando su lógica): de ahí el sentido del *head sampling* —descartar antes de pagar.
    - `Batch + exportador nulo` te da el coste del SDK **más** el de nuestro `ManualInstrumentor`; `OTelInstrumentor` suma **logs, métricas** y la copia en memoria del laboratorio; la **captura de contenido** (serializar a JSON todos los mensajes) es lo más caro y crece con el tamaño de la conversación.
    - Interpreta las **proporciones**, no los microsegundos absolutos (dependen de tu CPU; en un portátil actual salen del orden de 0,1-0,4 ms por span en Python). Aun así, ≈ 4 spans por ticket × décimas de milisegundo es despreciable frente a una llamada a un LLM (cientos de ms a segundos): **instrumentar un agente es barato**; lo caro es lo que *envías y almacenas* (módulo 18).
    """))

    # ------------------------------------------------------------------------------------------------ 8
    md("""
    ---
    # 8 · 🏭 En producción

    - **Un SDK por proceso, configurado en el arranque.** Las empresas estandarizan una función `init_telemetry()` (o un *distro* interno) que fija `Resource`, sampler, procesadores y exportador; el código de negocio solo usa la API. Es la misma idea que `supportops.telemetry.setup_telemetry`.
    - **Exporta al Collector local/de la plataforma, no directamente al backend.** El Collector absorbe reintentos, cambia de backend sin redeploy, filtra y añade metadatos (módulo 05). Grafana Labs documenta [Grafana Alloy](https://grafana.com/docs/alloy/latest/introduction/otel_alloy/) como su distribución del OpenTelemetry Collector para este papel.
    - **Los proveedores convergen en el SDK upstream.** Honeycomb, por ejemplo, ya recomienda [el SDK de OpenTelemetry para Python](https://docs.honeycomb.io/send-data/python/opentelemetry-sdk) y declara archivadas sus distribuciones propias: instrumentar con OTel estándar evita el *lock-in*.
    - **Servidores *pre-fork* (Gunicorn, uWSGI):** la documentación oficial de OpenTelemetry advierte de que bifurcar un proceso crea inconsistencias en los hilos y cerrojos de fondo del SDK (el caso documentado es el del `PeriodicExportingMetricReader`: las **métricas** se rompen con varios workers aunque las trazas suelan funcionar); la solución preferida es **inicializar OpenTelemetry después del fork**, en cada worker ([Zero-code Python · Troubleshooting](https://opentelemetry.io/docs/zero-code/python/troubleshooting/)).
    - **Configuración por entorno** (`OTEL_*`) en el despliegue (Compose, Helm): el mismo código en laboratorio y producción cambia solo de variables. Lo veremos en el módulo 19.
    - **Observa tu observabilidad.** El Collector y el SDK exponen métricas internas (spans aceptados/descartados, cola, fallos de envío): una alerta de «`otelcol_exporter_send_failed_spans > 0`» vale más que descubrir el hueco meses después (módulos 05 y 16).
    """)

    md("""
    ---
    # 9 · 🧠 Secretos de la élite

    1. **El proveedor global es de un solo uso (y eso muerde en notebooks y tests).** `set_tracer_provider` solo funciona **una vez** por proceso; la segunda llamada se ignora con un aviso (*«Overriding of current TracerProvider is not allowed»*) y tus spans siguen yendo al proveedor viejo —quizá ya apagado—. Por eso `setup_telemetry` re-registra los globales con un truco de laboratorio, y los instrumentores de SupportOps usan **el tracer del handle de forma explícita**, no el global. *Por qué importa:* un notebook que «deja de exportar» tras re-ejecutar una celda suele ser esto.
    2. **La cola del `BatchSpanProcessor` descarta sin hacer ruido.** Con 2048 de cola y 512 por lote, un exportador lento (Collector saturado) convierte una ráfaga en **pérdida de trazas enteras**, y en Python se pierden las **más antiguas** (lo viste en 4.4). *Verificable:* `max_queue_size`, `Queue full, dropping Span` en el log del SDK. *Contramedida:* Collector local rápido + subir la cola si la ráfaga es corta + alertar sobre descartes.
    3. **El sampler solo ve lo que le das al crear el span.** Un `set_attribute` posterior es invisible para él (lo demostraste con `Spy`). La spec lo dice explícitamente para atributos y links («adding attributes at span creation is preferred … head sampling decisions can only consider information present during span creation»). Para agentes: `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.tool.name` **al crear**.
    4. **128 atributos y 128 eventos por span; el SDK descarta los más antiguos.** Un bucle de herramientas que añade `step_N_result` convierte un incidente en un span **truncado**: justo el dato que buscabas. Los límites se suben con `OTEL_SPAN_ATTRIBUTE_COUNT_LIMIT`/`OTEL_SPAN_EVENT_COUNT_LIMIT` (valor por defecto 128 en la spec); mejor, spans hijos.
    5. **`record_exception` guarda mensaje y *stacktrace*: ahí se cuela PII.** Una excepción de una herramienta con el email del cliente en el mensaje (`"no existe el usuario ana@…"`) acaba en el span y, si exportas logs, en Loki. Registra el **tipo** (`error.type`, baja cardinalidad) y un mensaje saneado; el contenido, solo con política (módulo 20).
    6. **Las cabeceras HTTP no distinguen mayúsculas; los `dict` sí.** Un `extract` sobre `dict(headers)` con `Traceparent` no encuentra `traceparent` y el servidor crea una traza nueva **sin error alguno** (lo vimos en 4.3). Las trazas rotas por esta causa son indistinguibles de las rotas por falta de `inject`.
    7. **El `trace_id` tiene que ser aleatorio de verdad.** `TraceIdRatioBased` decide mirando el `trace_id`, así que un generador de ids no uniforme (con prefijo temporal, como hacen algunos sistemas) **sesga el muestreo**. Por eso W3C Trace Context Level 2 definió el bit `random-trace-id` (`flags & 0x02`) y el SDK de Python lo activa (`traceparent: …-03`): es la promesa de que los 7 bytes de la derecha son aleatorios. Si implementas un `IdGenerator` propio (como el determinista de `supportops.telemetry`, solo para tests), declara `is_trace_id_random()` con honestidad.
    8. **`service.instance.id` es identidad, no adorno.** Cada réplica/worker necesita el suyo (el SDK ≥ 1.44 lo genera y lo regenera tras `fork`, según la documentación oficial): en Prometheus se convierte en la etiqueta `instance`, y compartirlo entre escritores viola el principio de *single-writer* de las métricas. Pero **nunca** lo uses como etiqueta de consulta de negocio.
    9. **«Muestreado a 0 %» no es «coste 0».** Con un sampler que descarta, el SDK sigue creando el objeto de span no-recording y evaluando el sampler; en una medición de referencia (CPython, exportador nulo) un span descartado costó ≈ la mitad que uno exportado (≈ 10 frente a 18-22 µs), no cero. Además, con exportador nulo `BatchSpanProcessor` **no** salió más barato que `SimpleSpanProcessor` en el hilo del llamador: su ventaja es no bloquearte con la **E/S de red** del exportador real (el `SimpleSpanProcessor` exporta en línea), no ahorrar CPU. *Verificable:* la celda siguiente mide microsegundos por span con tres configuraciones (valores absolutos dependen de tu máquina; mira las **proporciones**). Esto decide si instrumentas bucles internos (cada paso de herramienta sí; cada token no).
    """)
    code('''
import time
class _Null(SpanExporter):
    def export(self, spans): return SpanExportResult.SUCCESS
    def shutdown(self): pass

def us_per_span(sampler, processor, n=20_000):
    tp = TracerProvider(sampler=sampler)
    if processor: tp.add_span_processor(processor)
    tr = tp.get_tracer("bench")
    t0 = time.perf_counter()
    for i in range(n):
        with tr.start_as_current_span("execute_tool", attributes={"gen_ai.tool.name": "get_order"}) as sp:
            sp.set_attribute("k", i)
    dt = (time.perf_counter() - t0) / n * 1e6
    tp.shutdown()
    return dt

res = {
  "ALWAYS_OFF (sin procesador)": us_per_span(sampling.ALWAYS_OFF, None),
  "ALWAYS_ON + BatchSpanProcessor": us_per_span(sampling.ALWAYS_ON, BatchSpanProcessor(_Null(), max_queue_size=1_000_000)),
  "ALWAYS_ON + SimpleSpanProcessor": us_per_span(sampling.ALWAYS_ON, SimpleSpanProcessor(_Null())),
}
base = res["ALWAYS_OFF (sin procesador)"]
for k, v in res.items():
    print(f"{k:34s} {v:7.1f} µs/span   ({v / base:4.1f}× el descartado)")
''')

    md("""
    ---
    # 10 · ⚠️ Errores comunes

    | Error | Síntoma | Arreglo |
    |---|---|---|
    | Usar `SimpleSpanProcessor` en producción | El agente va más lento; latencias suben cuando el Collector va lento | `BatchSpanProcessor` |
    | No llamar a `force_flush()`/`shutdown()` en scripts y jobs cortos | Faltan las últimas trazas | `tel.shutdown()` en `finally`/`atexit` |
    | Endpoint con `/v1/traces` en `OTEL_EXPORTER_OTLP_ENDPOINT` | 404 en el Collector; nada llega | URL base en la variable genérica; completa solo en `..._TRACES_ENDPOINT` |
    | Puerto 4317 con exportador HTTP (o 4318 con gRPC) | Errores de conexión/protocolo | HTTP → 4318, gRPC → 4317 |
    | Crear el `TracerProvider` **dentro** de la petición | Memoria y hilos que crecen, spans perdidos | Un proveedor por proceso, creado al arrancar |
    | Nombres de span con ids (`GET /orders/ORD-17`) | Explosión de cardinalidad en Tempo y en span metrics | Nombre de baja cardinalidad + id como atributo |
    | `ThreadPoolExecutor` sin copiar contexto | Trazas de 1 span huérfanas | `copy_context().run(...)` o instrumentación de hilos |
    | Tiempos propios no monótonos (`end < start`) | Duraciones negativas o cero; el SDK no avisa | `max(end, start)` |
    | Poner `StatusCode.OK` «por si acaso» | Oculta errores en agregaciones | Dejar `UNSET`; solo `ERROR` ante fallos |
    | Atributos de alta cardinalidad en **métricas** (`ticket.id`) | Prometheus explota | `ticket.id` solo en spans/logs (módulo 09) |
    | Capturar *prompts* completos «para depurar» | PII, coste de almacenamiento, fugas | Opt-in, redacción, retención corta (módulos 04 y 20) |
    """)

    md("""
    ---
    # 11 · Autoevaluación
    """)
    md(details("1 · (Recuerdo) ¿Por qué una librería (p. ej. un cliente HTTP instrumentado) depende solo de `opentelemetry-api` y no del SDK?",
               "Porque la API es un no-op sin SDK: la librería puede emitir telemetría sin imponer exportador, muestreo ni coste. Quien decide qué se hace con los datos es el **dueño de la aplicación**, configurando el SDK una vez. Es la misma regla que `logging`: las librerías nunca configuran *handlers*."))
    md(details("2 · (Cálculo) SupportOps recibe 50 tickets/s y produce ≈ 4,3 spans por ticket. El exportador envía lotes de 512 y cada envío tarda 0,25 s. ¿Aguanta el `BatchSpanProcessor` por defecto? ¿Qué pasa si el Collector se degrada y cada envío tarda 5 s?",
               """
               $\\lambda = 50\\times 4{,}3 = 215$ spans/s. Capacidad $\\lambda_{max}=B/d = 512/0{,}25 = 2048$ spans/s ⇒ **sobra** casi 10×.
               Con $d=5$ s: $\\lambda_{max}=512/5\\approx 102$ spans/s $<215$ ⇒ la cola crece a $215-102=113$ spans/s y con $Q=2048$ se llena en $2048/113\\approx 18$ s; a partir de ahí se **descartan** spans (en Python, los más antiguos). Lección: dimensiona con el *peor* caso del exportador, no con el normal, y alerta sobre descartes.
               """))
    md(details("3 · (Diagnóstico) En Tempo ves cientos de trazas de **un solo span** llamado `execute_tool search_kb` sin padre, y las trazas `invoke_agent` no tienen esos hijos. El agente ejecuta herramientas en un `ThreadPoolExecutor`. ¿Qué ocurre y cómo lo arreglas?",
               "El contexto activo vive en un `ContextVar` y los hilos del pool empiezan con contexto vacío: cada `start_as_current_span` en el hilo crea una **raíz nueva**. Arreglo: lanzar la tarea con `contextvars.copy_context().run(fn, ...)` (o `opentelemetry-instrumentation-threading`). Comprobación: nº de trazas por petición debe ser 1."))
    md(details("4 · (Diagnóstico) El servicio A usa `ParentBased(TraceIdRatioBased(0.1))` y el servicio B (que A llama) usa solo `TraceIdRatioBased(0.5)`. En Tempo aparecen trazas **con spans de B pero sin los de A**. ¿Por qué?",
               "B no respeta la decisión del padre: aplica su propio 50 % al `trace_id`. De las trazas que A **descartó** (el 90 %), B conserva por su cuenta las que caen entre el 10 % y el 50 % del espacio de `trace_id` (≈ 40 % del total de trazas), y quedan fragmentos huérfanos. (Con el mismo ratio los umbrales coinciden porque la decisión es función del `trace_id`; con ratios distintos no.) Usa `ParentBased` en todos los servicios."))
    md(details("5 · (Cálculo) Con head sampling `p = 5 %` y 40 000 tickets/día, ¿cuántas trazas esperas conservar y con qué dispersión? Si el 0,5 % de los tickets falla, ¿cuántas trazas de fallo verás?",
               """
               Conservadas: $np = 2000$, desviación $\\sqrt{np(1-p)} = \\sqrt{40000\\cdot0{,}05\\cdot0{,}95}\\approx 43{,}6$ ⇒ 2000 ± 87 (95 %).
               Fallos: $40000\\cdot 0{,}005 = 200$ tickets fallidos ⇒ solo **≈ 10** trazas de fallo conservadas (2000·0,005). El head sampling uniforme trata igual lo raro y lo común: por eso para errores y latencias se usa *tail sampling* (módulo 18).
               """))
    md(details("6 · (Transferencia) Despliegas el agente con Gunicorn (8 workers, `--preload`) y `setup_telemetry()` se ejecuta al importar la app. Trazas y métricas se pierden de forma intermitente. Diseña la solución.",
               "Con `--preload` el módulo se importa en el proceso maestro y los hilos de fondo (Batch, lector periódico de métricas) no sobreviven bien al `fork`. Solución: inicializar la telemetría **después del fork**, en el hook `post_fork` de Gunicorn (o en el evento de arranque de cada worker); un `Resource` con `service.instance.id` distinto por worker; exportar por OTLP/HTTP a un Collector local; y `shutdown()` en el hook de salida del worker."))
    md(details("7 · (Transferencia) Tu agente llama a un servidor MCP remoto de pedidos por HTTP. ¿Qué `SpanKind` usarías en cada lado, qué debe hacer cada lado con el contexto y qué verías si el servidor no hiciera `extract`?",
               "Agente: span `CLIENT` (p. ej. `execute_tool get_order`) y `propagate.inject` en las cabeceras de la petición. Servidor: `extract` de las cabeceras y span `SERVER` como hijo. Sin `extract` el servidor crea **otra traza**: dos trazas incompletas, sin errores visibles; el agente vería la latencia de la llamada pero no su desglose interno. (Módulo 12.)"))

    md("""
    ---
    # 12 · Referencias

    - OpenTelemetry. *Instrumentation* (Python) — <https://opentelemetry.io/docs/languages/python/instrumentation/>
    - OpenTelemetry. *Exporters* (Python) — <https://opentelemetry.io/docs/languages/python/exporters/>
    - OpenTelemetry. *Propagation* (Python) — <https://opentelemetry.io/docs/languages/python/propagation/>
    - OpenTelemetry. *Zero-code Python · Troubleshooting* (servidores pre-fork) — <https://opentelemetry.io/docs/zero-code/python/troubleshooting/>
    - OpenTelemetry Specification. *Trace API* y *Trace SDK* (SpanKind, Status, Sampler, BatchSpanProcessor, límites) — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/api.md> · <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/sdk.md>
    - OpenTelemetry Specification. *OTLP Exporter* y *Variables de entorno del SDK* — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/protocol/exporter.md> · <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/configuration/sdk-environment-variables.md>
    - W3C. *Trace Context* (Recommendation) — <https://www.w3.org/TR/trace-context/>
    - Repositorio del SDK — <https://github.com/open-telemetry/opentelemetry-python>
    - Grafana Labs. *OpenTelemetry in Alloy* — <https://grafana.com/docs/alloy/latest/introduction/otel_alloy/>
    - Honeycomb. *Send Data with the OpenTelemetry Python SDK* — <https://docs.honeycomb.io/send-data/python/opentelemetry-sdk>
    - Honeycomb. *Migrate from Honeycomb OTel Distributions to OpenTelemetry* (la distribución Python está archivada y sin mantenimiento; se recomienda el SDK upstream) — <https://docs.honeycomb.io/troubleshoot/product-lifecycle/recommended-migrations/migrate-from-honeycomb-distributions> (confirmado por búsqueda web; el dominio no es accesible desde el entorno de revisión).
    - OpenTelemetry. Valores por defecto `OTEL_BSP_*` (cola 2048, lote 512, retardo 5 s) — *Environment Variables* del SDK, enlace arriba.

    ## Siguiente
    `04_genai_semconv`: tus spans ya existen, pero sus **nombres de atributo** los inventas tú. Las *GenAI semantic conventions* los estandarizan; construirás un linter propio para validarlos.

    **Limpieza (opcional):** `tel.shutdown()` y, si levantaste el stack solo para esta lección, `docker compose --profile all down` desde `stack/`.
    """)
    code('''
tel.shutdown()          # flush final y cierre de los hilos del SDK
''')

    nb.save(out)


# =====================================================================================================================
def _reference_numbers(n: int = 60) -> dict:
    """Mide con el instrumentor de referencia (modo mock, semilla 42) lo que la rúbrica del proyecto va a exigir."""
    sys.path.insert(0, str(COURSE))
    import os
    os.environ.setdefault("LLM_PROVIDER", "mock")
    from supportops import DEFAULT_FAULT_RATES, SIM_EPOCH_S, SupportAgent, generate_tickets, run_tickets
    from supportops.telemetry import OTelInstrumentor, setup_telemetry
    tk = generate_tickets(n, seed=42, fault_rates=DEFAULT_FAULT_RATES, start_s=SIM_EPOCH_S)
    tel = setup_telemetry("ref", mode="memory", set_global=False)
    res = run_tickets(SupportAgent(instrumentor=OTelInstrumentor(tel)), tk)
    sp = tel.span_records()
    steps = [s for r in res for s in r.steps]
    out = {
        "n": n, "spans": len(sp), "traces": len({s["trace_id"] for s in sp}),
        "chat": sum(s["name"].startswith("chat ") for s in sp), "tool": sum(s["name"].startswith("execute_tool ") for s in sp),
        "err_spans": sum(s["status"] == "ERROR" and not s["name"].startswith("invoke_agent") for s in sp),
        "root_err": sum(r.status in ("error", "max_steps") for r in res),
        "retries": sum(1 for s in steps if s.kind == "llm" and s.attributes.get("attempt", 0) >= 1),
        "logs": len(tel.log_records()),
    }
    tel.shutdown()
    return out


def build_project() -> None:
    ref = _reference_numbers()
    nb, out = nb_for(MOD, "03_proyecto_otel_sdk_python.ipynb", "Proyecto 03 · Instrumenta a mano SupportOps v0")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 03 · Instrumenta a mano SupportOps v0 y mira tus primeras trazas

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Opcional (`--profile core`) para el último paso; el resto se verifica en memoria. Sin Docker funciona igual (modo degradado) |
    | **RAM aproximada** | < 0,5 GB (con `core` en reposo ≈ 0,9 GB) |
    | **Prerrequisitos** | Lección `03_otel_sdk_python` (spans, contexto, procesadores, instrumentación manual) y módulo 01 (`Instrumentor`) |
    | **Conexión** | Parte de **SupportOps v0** (módulo 01, sin observabilidad) y entrega **SupportOps v1 instrumentado a mano**. El módulo 04 lo ajustará a las GenAI semantic conventions |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Hoy, cuando un cliente se queja de que «el bot tardó mucho», nadie sabe si fue el modelo, una herramienta o un reintento: el agente v0 es una caja negra.
    Tu primera tarea es instrumentarlo **a mano** con el SDK de OpenTelemetry (sin autoinstrumentación) para que cada ticket produzca **una traza** con el árbol `invoke_agent → chat / execute_tool`, con errores marcados,
    tokens anotados y **logs correlacionados**. Después usarás tus propias trazas para contestar tres preguntas de operación.

    ## Datos

    Tráfico sintético de SupportOps (semilla fija `42`, esquema en `schema.TICKET_SCHEMA`): **{ref['n']} tickets** con fallos de fondo (`DEFAULT_FAULT_RATES`), tiempo **simulado**. Cadena de resiliencia: stack local (último paso) → memoria (toda la verificación) → no hace falta nada pregrabado.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución, `mock`, semilla 42, {ref['n']} tickets) |
    |---|---|---|---|
    | R1 | `init_tracing` | `Resource` con `service.name = supportops-agent`, `service.version` y `service.instance.id` | cumple |
    | R2 | Una traza por ticket | Cada ticket produce **1 traza** con **1 raíz** `invoke_agent <agente>` | {ref['traces']}/{ref['n']} (100 %) |
    | R3 | Spans = pasos | Spans de la traza = `1 + n_llm_calls + n_tool_calls` | {ref['spans']} spans en total ({ref['chat']} `chat` + {ref['tool']} `execute_tool` + {ref['n']} raíces), 100 % de trazas |
    | R4 | Jerarquía y *kinds* | Todo `chat`/`execute_tool` es hijo directo de la raíz; raíz `INTERNAL`, `chat` `CLIENT`, herramienta `INTERNAL` | 100 % |
    | R5 | Tiempos | Duración de la raíz = `AgentResult.latency_s` (±1 ms) | 100 % |
    | R6 | Errores | Nº de spans hijos en `ERROR` = pasos con error ({ref['err_spans']}); raíz en `ERROR` ⇔ estado `error`/`max_steps` ({ref['root_err']} raíces); los spans en error llevan `error.type` y un evento `exception` | 100 % |
    | R7 | Atributos | `chat`: `gen_ai.operation.name`, `gen_ai.request.model`, `supportops.attempt` y tokens; suma de tokens de los `chat` = tokens del `AgentResult` | 100 % |
    | R8 | Logs correlacionados | Cada log del agente ({ref['logs']} en total) lleva el `trace_id` y `span_id` **de su traza** | 100 % |
    | R9 | Paralelismo | 3 herramientas en hilos → **1 traza** (no 4) y 3 hijos de la raíz | cumple |
    | R10 | Operación con trazas | Tus respuestas (reintentos = {ref['retries']}, herramienta más lenta y su p95) coinciden con la verdad de terreno | exacto |

    > 📏 Todo es **estructural y determinista** porque el tiempo es simulado y la semilla fija: no depende de la velocidad de tu máquina. Los umbrales del 100 % son lo que mide la solución de referencia;
    > con tráfico distinto (otra semilla) los totales cambian pero las proporciones deben seguir siendo 100 %.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + OTEL_IMPORTS + '''
STACK = check_stack(["collector", "tempo", "loki"])
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
N = 60
tickets = generate_tickets(N, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, start_s=SIM_EPOCH_S)    # tiempo simulado fijo → rúbrica determinista
print(len(tickets), "tickets ·", sum(bool(t.faults) for t in tickets), "con fallos inyectados")
''')

    # -------------------------------------------------------------------------------------------- paso 1
    md("""
    ## Paso 1 · El proveedor: `init_tracing`

    **TODO 1.** Implementa `init_tracing(service_name, otlp_endpoint=None)` que devuelva `(provider, memory_exporter)`:

    - un `Resource` con `service.name`, `service.version="0.1.0"` y un `service.instance.id` único;
    - un `TracerProvider` con ese resource;
    - una **copia en memoria** (`InMemorySpanExporter` + `SimpleSpanProcessor`) para que podamos verificar (solo para el laboratorio);
    - **si** `otlp_endpoint` no es `None`: además un `BatchSpanProcessor` con `OTLPSpanExporter` (la URL completa es `<endpoint>/v1/traces`).
    """)
    md(hint(1, "Es la celda 4.1 y la sección 5 de la lección: `Resource.create({...})`, `TracerProvider(resource=...)`, `provider.add_span_processor(...)`. Uno de los procesadores es Simple (memoria) y el otro Batch (OTLP)."))
    md(hint(2, "`from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter` y `OTLPSpanExporter(endpoint=f\"{otlp_endpoint.rstrip('/')}/v1/traces\")`. Para el id único: `f\"{service_name}-{secrets.token_hex(4)}\"`."))
    code('''
def init_tracing(service_name: str = "supportops-agent", otlp_endpoint: str | None = None):
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    provider, mem = init_tracing(); print(provider.resource.attributes["service.name"], "·", provider.resource.attributes.get("service.instance.id"))
except NotImplementedError as e:
    provider = mem = None; print("Pendiente:", e)
''')

    # -------------------------------------------------------------------------------------------- paso 2
    md("""
    ## Paso 2 · El instrumentor

    Implementarás `StudentInstrumentor(Instrumentor)`. El agente llama a tus *context managers* alrededor de cada trabajo; **la excepción que ocurra dentro del bloque `with` atraviesa tu `yield`** y el agente la captura fuera (puedes registrarla y volver a lanzarla).
    Usa el **reloj simulado** (`ctx.clock.now_ns()`) como `start_time`/`end_time` para que las trazas sean deterministas.

    **TODO 2 · `_span`.** El ayudante común: abre un span con `start_span(..., start_time=...)`, lo **activa** con `trace.use_span(..., end_on_exit=False, record_exception=False, set_status_on_exception=False)`, y:

    - si el cuerpo lanza una excepción: `record_exception` (con `timestamp` simulado), atributo `error.type` (usa `e.error_type` si existe, si no el nombre de la clase), `set_status(Status(StatusCode.ERROR, ...))` y **relanza**;
    - al final (siempre): `span.end(end_time=...)` con el reloj simulado.
    """)
    md(hint(1, "Es el patrón de `ManualInstrumentor._span` de la lección. Los atributos de **muestreo** (nombre de operación, modelo, herramienta) pásalos en `attributes=` al crear. `try/except BaseException: ...; raise` y `finally: span.end(...)`."))
    md(hint(2, "`end_time=max(ctx.clock.now_ns(), t0)` evita duraciones negativas. `str(getattr(e, 'error_type', type(e).__name__))` da el `error.type` (`ToolError` y `LLMError` tienen `error_type`)."))

    md("""
    **TODO 3 · `agent_run`.** Span raíz `invoke_agent <ctx.agent_name>`, `SpanKind.INTERNAL`, atributos al crear: `gen_ai.operation.name="invoke_agent"`, `gen_ai.agent.name`, `supportops.ticket.id`, `supportops.customer.tier`.
    Al terminar (`ctx.result` ya está disponible tras el `yield`): `supportops.status`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`; y si `ctx.result.status` es `error` o `max_steps`: `error.type` y estado `ERROR` (un fallo **recuperado** con reintento no marca la raíz).

    **TODO 4 · `llm_call`.** Span `chat <info.model>`, `SpanKind.CLIENT`, atributos al crear: `gen_ai.operation.name="chat"`, `gen_ai.provider.name`, `gen_ai.request.model`, `supportops.attempt` (= `info.attempt`) y `supportops.step`. Tras el `yield`, si hay `info.response`: `gen_ai.usage.input_tokens/output_tokens` y `gen_ai.response.model`.
    Si el LLM falla, `info.error` es un `LLMError` con `.status` (HTTP): añade `http.response.status_code`.

    **TODO 5 · `tool_call`.** Span `execute_tool <info.call.name>`, `SpanKind.INTERNAL`, atributos al crear: `gen_ai.operation.name="execute_tool"`, `gen_ai.tool.name`, `gen_ai.tool.call.id`, `supportops.step`.

    **TODO 6 · `log`.** `log(ctx, level, message, fields)` debe **añadir a `self.logs`** un diccionario `{"body", "severity", "trace_id", "span_id", "attributes"}` con el `trace_id` (32 hex) y `span_id` (16 hex) **del span activo en ese instante** (`trace.get_current_span().get_span_context()`).
    """)
    md(hint(1, "`ctx_ = trace.get_current_span().get_span_context()` y `format(ctx_.trace_id, '032x')`, `format(ctx_.span_id, '016x')`. Ojo: si no hay span activo, `trace_id == 0`."))
    code('''
class StudentInstrumentor(Instrumentor):
    def __init__(self, tracer, log_sink: list):
        self.tracer, self.logs = tracer, log_sink

    @contextmanager
    def _span(self, ctx, name, kind, attrs):
        # TODO 2: abre el span, actívalo, gestiona errores y ciérralo con el reloj simulado; haz `yield span`
        raise NotImplementedError("TODO 2")
        yield

    @contextmanager
    def agent_run(self, ctx):
        # TODO 3
        raise NotImplementedError("TODO 3")
        yield

    @contextmanager
    def llm_call(self, ctx, info):
        # TODO 4
        raise NotImplementedError("TODO 4")
        yield

    @contextmanager
    def tool_call(self, ctx, info):
        # TODO 5
        raise NotImplementedError("TODO 5")
        yield

    def log(self, ctx, level, message, fields):
        # TODO 6
        raise NotImplementedError("TODO 6")


def instrument_and_run(tickets_, factory=None):
    """Ejecuta el agente con tu instrumentor sobre un proveedor nuevo. Devuelve (resultados, spans_terminados, logs)."""
    prov, mem_ = init_tracing()
    logs: list = []
    instr = StudentInstrumentor(prov.get_tracer("supportops.student", "0.1.0"), logs)
    res = run_tickets(SupportAgent(instrumentor=instr), tickets_)
    return res, mem_.get_finished_spans(), logs

try:
    results, spans, logs = instrument_and_run(tickets)
    print(f"{len(results)} tickets → {len(spans)} spans · {len({s.context.trace_id for s in spans})} trazas · {len(logs)} logs")
except NotImplementedError as e:
    results, spans, logs = [], [], []; print("Pendiente (completa los TODO 1-6):", e)
''')

    md("""
    ### Mira una traza

    Dibuja la traza del ticket más lento. Si todo va bien verás `invoke_agent` con sus `chat`/`execute_tool` hijos; si ves **barras sueltas sin padre** o un solo span, revisa el TODO 2 (¿activaste el span con `use_span`?).
    """)
    code('''
def to_records(spans_):
    return [{"trace_id": format(s.context.trace_id, "032x"), "span_id": format(s.context.span_id, "016x"), "parent_span_id": format(s.parent.span_id, "016x") if s.parent else None,
             "name": s.name, "kind": s.kind.name, "start_unix_nano": s.start_time, "end_unix_nano": s.end_time, "status": s.status.status_code.name} for s in spans_]

if spans:
    recs = to_records(spans); df = pd.DataFrame(recs); df["dur"] = (df.end_unix_nano - df.start_unix_nano) / 1e9
    tid = df[df.parent_span_id.isna()].sort_values("dur").iloc[-1].trace_id
    fig, ax = plt.subplots(figsize=(11, 0.45 * (df.trace_id == tid).sum() + 1.4)); fig.subplots_adjust(left=0.3)
    viz.waterfall([r for r in recs if r["trace_id"] == tid], ax=ax, title=f"Tu traza más lenta · {tid[:8]}…"); plt.show()
else:
    print("Aún no hay spans: completa los TODO.")
''')

    # -------------------------------------------------------------------------------------------- paso 3
    md("""
    ## Paso 3 · Herramientas en paralelo sin romper la traza

    Algunos agentes ejecutan varias herramientas a la vez. **TODO 7.** Implementa `run_tools_parallel(tracer, tool_names)`: crea un span raíz `invoke_agent parallel-demo` y, **dentro**, lanza **una tarea por herramienta** en un `ThreadPoolExecutor`; cada tarea abre un span `execute_tool <nombre>`.
    El resultado debe ser **una sola traza** con la raíz y tantos hijos como herramientas (en la lección viste qué pasa si no copias el contexto).
    """)
    md(hint(1, "Los hilos nuevos empiezan con el contexto vacío. Hay que ejecutar la tarea **dentro de una copia del contexto actual**: `contextvars.copy_context().run(fn, *args)`."))
    md(hint(2, "`futs = [ex.submit(contextvars.copy_context().run, work, name) for name in tool_names]` y luego `[f.result() for f in futs]`. La copia se hace **en el hilo que llama** (el que tiene el span raíz activo), no dentro de la tarea."))
    code('''
def run_tools_parallel(tracer, tool_names) -> None:
    # TODO 7
    raise NotImplementedError("TODO 7")

try:
    _p, _m = init_tracing("parallel-demo"); run_tools_parallel(_p.get_tracer("demo"), ["get_order", "search_kb", "check_stock"])
    _s = _m.get_finished_spans(); print("trazas:", len({s.context.trace_id for s in _s}), "· spans:", len(_s))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # -------------------------------------------------------------------------------------------- paso 4
    md("""
    ## Paso 4 · Operar con tus propias trazas

    Con la telemetría que acabas de producir, **responde sin mirar los `AgentResult`** (solo los `spans` terminados):

    **TODO 8a.** `retries_from_spans(spans) -> int`: ¿cuántos **reintentos** de llamada al LLM hubo? (spans `chat` con `supportops.attempt >= 1`).
    **TODO 8b.** `slowest_tool(spans) -> (nombre, p95_s)`: de las herramientas (`gen_ai.tool.name`), la de mayor **percentil 95** de duración (usa `viz.percentile` y la duración del span en segundos).
    """)
    md(hint(1, "`s.attributes.get(...)`, `(s.end_time - s.start_time) / 1e9`. Agrupa las duraciones por `s.attributes['gen_ai.tool.name']` con un diccionario de listas."))
    code('''
def retries_from_spans(spans_) -> int:
    # TODO 8a
    raise NotImplementedError("TODO 8a")

def slowest_tool(spans_):
    # TODO 8b
    raise NotImplementedError("TODO 8b")

try:
    print("reintentos:", retries_from_spans(spans), "· herramienta más lenta (p95):", slowest_tool(spans))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # -------------------------------------------------------------------------------------------- rúbrica
    md("""
    ## Paso 5 · Rúbrica

    Ejecuta la celda para puntuar tu trabajo. Las comprobaciones comparan tus spans con la **verdad de terreno** (`AgentResult`).
    """)
    code('''
def run_rubric():
    rows = []
    def add(r, desc, ok, detail=""): rows.append({"criterio": r, "descripción": desc, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": detail})
    try:
        res, sp, lg = instrument_and_run(tickets)
        prov, _ = init_tracing(); a = prov.resource.attributes
        add("R1", "Resource con service.name/version/instance.id", a.get("service.name") == "supportops-agent" and "service.version" in a and "service.instance.id" in a)
    except Exception as e:
        add("R1", "init_tracing + instrumentor", False, repr(e)[:90]); return pd.DataFrame(rows).set_index("criterio")
    by = {}
    for s in sp: by.setdefault(format(s.context.trace_id, "032x"), []).append(s)
    roots = {t: [s for s in v if s.parent is None] for t, v in by.items()}
    ok2 = len(by) == len(res) and all(len(r) == 1 and r[0].name.startswith("invoke_agent ") for r in roots.values())
    add("R2", "1 traza y 1 raíz por ticket", ok2, f"{len(by)} trazas / {len(res)} tickets")
    # Asociamos cada resultado con su traza por el atributo supportops.ticket.id de la raíz
    tr_of = {r[0].attributes.get("supportops.ticket.id"): t for t, r in roots.items() if r}
    def spans_of(r): return by.get(tr_of.get(r.ticket_id), [])
    add("R3", "spans = 1 + n_llm + n_tool en el 100 % de trazas", all(len(spans_of(r)) == 1 + r.n_llm_calls + r.n_tool_calls for r in res), f"{len(sp)} spans")
    def hier_ok(r):
        S = spans_of(r); root = [s for s in S if s.parent is None]
        if len(root) != 1: return False
        rid = root[0].context.span_id
        return (root[0].kind == SpanKind.INTERNAL and all(s.parent.span_id == rid for s in S if s is not root[0] and s.parent is not None)
                and all((s.kind == SpanKind.CLIENT) == s.name.startswith("chat ") for s in S if s is not root[0]) and all(s.parent is not None for s in S if s is not root[0]))
    add("R4", "jerarquía y kinds", all(hier_ok(r) for r in res))
    def dur_ok(r):
        root = [s for s in spans_of(r) if s.parent is None]
        return bool(root) and abs((root[0].end_time - root[0].start_time) / 1e9 - r.latency_s) < 1e-3
    add("R5", "duración de la raíz = latency_s (±1 ms)", all(dur_ok(r) for r in res))
    child_err = sum(s.status.status_code == StatusCode.ERROR for s in sp if s.parent is not None)
    truth_err = sum(st.status == "error" for r in res for st in r.steps)
    root_err_ok = all((([s for s in spans_of(r) if s.parent is None][0].status.status_code == StatusCode.ERROR) == (r.status in ("error", "max_steps"))) for r in res if spans_of(r))
    detail_ok = all("error.type" in s.attributes and any(e.name == "exception" for e in s.events) for s in sp if s.parent is not None and s.status.status_code == StatusCode.ERROR)
    add("R6", "errores: spans ERROR = pasos con error, raíz coherente, error.type + exception", child_err == truth_err and root_err_ok and detail_ok, f"{child_err} vs {truth_err}")
    def attrs_ok(r):
        chats = [s for s in spans_of(r) if s.name.startswith("chat ")]
        need = ("gen_ai.operation.name", "gen_ai.request.model", "supportops.attempt")
        return (all(all(k in s.attributes for k in need) for s in chats)
                and sum(s.attributes.get("gen_ai.usage.input_tokens", 0) for s in chats) == r.input_tokens
                and sum(s.attributes.get("gen_ai.usage.output_tokens", 0) for s in chats) == r.output_tokens)
    add("R7", "atributos de chat y tokens = AgentResult", all(attrs_ok(r) for r in res))
    valid_tr = set(by)
    good_logs = [l for l in lg if l.get("trace_id") in valid_tr and len(l.get("span_id") or "") == 16]
    add("R8", "logs con trace_id/span_id de su traza", len(lg) > 0 and len(good_logs) == len(lg), f"{len(good_logs)}/{len(lg)}")
    try:
        p2, m2 = init_tracing("par"); run_tools_parallel(p2.get_tracer("t"), ["a", "b", "c"]); s2 = m2.get_finished_spans()
        roots2 = [s for s in s2 if s.parent is None]
        add("R9", "3 herramientas en paralelo = 1 traza, 3 hijos de la raíz", len({s.context.trace_id for s in s2}) == 1 and len(roots2) == 1 and sum(s.parent is not None and s.parent.span_id == roots2[0].context.span_id for s in s2) == 3)
    except Exception as e:
        add("R9", "paralelismo", False, repr(e)[:90])
    try:
        steps = [st for r in res for st in r.steps]
        truth_retries = sum(1 for st in steps if st.kind == "llm" and st.attributes.get("attempt", 0) >= 1)
        by_tool: dict = {}
        for st in steps:
            if st.kind == "tool": by_tool.setdefault(st.name, []).append(st.end_s - st.start_s)
        truth_tool = max(((n, viz.percentile(v, .95)) for n, v in by_tool.items()), key=lambda x: x[1])
        got_r, got_t = retries_from_spans(sp), slowest_tool(sp)
        add("R10", "reintentos y herramienta más lenta (p95) = verdad", got_r == truth_retries and got_t[0] == truth_tool[0] and abs(got_t[1] - truth_tool[1]) < 1e-6, f"tú: {got_r}, {got_t[0]} · verdad: {truth_retries}, {truth_tool[0]}")
    except Exception as e:
        add("R10", "operación con trazas", False, repr(e)[:90])
    return pd.DataFrame(rows).set_index("criterio")

display(run_rubric())
''')

    # -------------------------------------------------------------------------------------------- paso 6
    md("""
    ## Paso 6 · (Opcional) Ver tus trazas en Tempo

    Con el stack arriba (`docker compose --profile core up -d` desde `stack/`), exporta por OTLP y busca una traza.
    **TODO 9.** Implementa `export_live(n=20)`: genera `n` tickets con `start_s="live"` (la ventana debe terminar *ahora*, o Tempo rechazará los tiempos), ejecútalos con tu instrumentor sobre `init_tracing(otlp_endpoint="http://localhost:4318")`, haz `force_flush()` y devuelve el `trace_id` (32 hex) de la primera traza. Luego la celda siguiente la busca en Tempo.
    """)
    md(hint(1, "`prov.force_flush()` antes de consultar; el `trace_id` está en `spans[0].context.trace_id` (`format(..., '032x')`). Recuerda `prov.shutdown()` al final."))
    code('''
def export_live(n: int = 20) -> str:
    # TODO 9
    raise NotImplementedError("TODO 9")

try:
    if STACK.degraded:
        print("Modo degradado: levanta el stack para este paso →", STACK.command)
    else:
        TID = export_live(); print("trace_id enviado:", TID)
        for _ in range(20):
            try:
                d = backends.tempo_trace(TID); n_sp = sum(len(ss["spans"]) for b in d.get("batches", []) for ss in b.get("scopeSpans", []))
                if n_sp: print("Tempo devolvió", n_sp, "spans de tu traza ✅"); break
            except backends.BackendError: pass
            time.sleep(2)
        else:
            print("Aún no está en Tempo (puede tardar ~30 s): reintenta la celda.")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ---
    ## Retos extra (nivel experto)

    1. **Muestreo:** monta un proveedor con `ParentBased(TraceIdRatioBased(0.25))`, pasa 400 tickets y mide qué fracción de trazas conserva. ¿Cuántos *fallos* conserva? ¿Y si quieres conservar **todos** los fallos? (pista: no se puede decidir al crear el span → *tail sampling*, módulo 18).
    2. **Links de reintento:** haz que el `chat` del reintento lleve un `trace.Link` al span del intento fallido (guárdalo en `ctx.state`). ¿Cómo se ve en Tempo?
    3. **Límites:** provoca un `tool_loop` (`FaultSpec("tool_loop")`) y comprueba cuántos spans genera. Configura `SpanLimits(max_events=...)` y razona qué se pierde primero si añades un evento por paso.
    4. **Configuración por entorno:** reescribe `init_tracing` para que no reciba argumentos y se configure solo con `OTEL_SERVICE_NAME`, `OTEL_RESOURCE_ATTRIBUTES` y `OTEL_EXPORTER_OTLP_ENDPOINT` (pista: el SDK las lee si no pasas el argumento).
    5. **Fork-safe:** diseña (sin ejecutar Gunicorn) en qué hook inicializarías `init_tracing` y cómo darías un `service.instance.id` distinto a cada worker.

    ## Reflexión (producción e hilo conductor)

    - Tu instrumentor usa **tiempos simulados**. ¿Qué dos cosas cambiarías para un servicio real (pista: `start_time`, `end_time`, y qué procesador)?
    - Un fallo **recuperado** (reintento exitoso) deja la raíz sin `ERROR`. ¿Es lo que quiere el equipo de guardia? ¿Cómo te enterarías de que el proveedor LLM está fallando si todas las raíces salen verdes? (Spoiler: spans hijos `ERROR` y métricas; módulos 09 y 16.)
    - ¿Qué atributos del span `execute_tool` serían **peligrosos** si contuvieran los argumentos completos de `issue_refund`? (módulo 20)
    - En el módulo 04 renombrarás atributos según la spec GenAI. ¿Cuáles de los tuyos (`supportops.*` vs `gen_ai.*`) crees que **no** cambiarán y por qué?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable. Al final vuelve a ejecutar la rúbrica con ella.
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
# TODO 1
def init_tracing(service_name: str = "supportops-agent", otlp_endpoint: str | None = None):
    resource = Resource.create({"service.name": service_name, "service.version": "0.1.0", "service.instance.id": f"{service_name}-{secrets.token_hex(4)}"})
    provider = TracerProvider(resource=resource)
    mem_exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(mem_exporter))                      # copia local solo para verificar (en producción: Batch)
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")))
    return provider, mem_exporter


class StudentInstrumentor(Instrumentor):
    def __init__(self, tracer, log_sink: list):
        self.tracer, self.logs = tracer, log_sink

    # TODO 2
    @contextmanager
    def _span(self, ctx, name, kind, attrs):
        t0 = ctx.clock.now_ns()
        span = self.tracer.start_span(name, kind=kind, attributes=attrs, start_time=t0)           # atributos de muestreo AL CREAR
        try:
            with trace.use_span(span, end_on_exit=False, record_exception=False, set_status_on_exception=False):
                yield span
        except BaseException as e:
            span.record_exception(e, timestamp=ctx.clock.now_ns())
            span.set_attribute("error.type", str(getattr(e, "error_type", type(e).__name__)))
            span.set_status(Status(StatusCode.ERROR, str(e)[:120]))
            raise
        finally:
            span.end(end_time=max(ctx.clock.now_ns(), t0))

    # TODO 3
    @contextmanager
    def agent_run(self, ctx):
        t = ctx.ticket
        attrs = {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": ctx.agent_name, "supportops.ticket.id": t.ticket_id, "supportops.customer.tier": t.tier}
        with self._span(ctx, f"invoke_agent {ctx.agent_name}", SpanKind.INTERNAL, attrs) as span:
            yield
            r = ctx.result
            if r is not None:
                span.set_attributes({"supportops.status": r.status, "gen_ai.usage.input_tokens": r.input_tokens, "gen_ai.usage.output_tokens": r.output_tokens})
                if r.status in ("error", "max_steps"):
                    span.set_attribute("error.type", r.error_type or r.status)
                    span.set_status(Status(StatusCode.ERROR, r.status))

    # TODO 4
    @contextmanager
    def llm_call(self, ctx, info):
        attrs = {"gen_ai.operation.name": "chat", "gen_ai.provider.name": info.provider, "gen_ai.request.model": info.model,
                 "supportops.attempt": info.attempt, "supportops.step": info.step}
        with self._span(ctx, f"chat {info.model}", SpanKind.CLIENT, attrs) as span:
            try:
                yield
            except BaseException as e:
                if getattr(e, "status", None): span.set_attribute("http.response.status_code", int(e.status))
                raise
            if info.response is not None:
                span.set_attributes({"gen_ai.usage.input_tokens": info.response.usage.input_tokens, "gen_ai.usage.output_tokens": info.response.usage.output_tokens,
                                     "gen_ai.response.model": info.response.model})

    # TODO 5
    @contextmanager
    def tool_call(self, ctx, info):
        attrs = {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": info.call.name, "gen_ai.tool.call.id": info.call.id, "supportops.step": info.step}
        with self._span(ctx, f"execute_tool {info.call.name}", SpanKind.INTERNAL, attrs):
            yield

    # TODO 6
    def log(self, ctx, level, message, fields):
        sc = trace.get_current_span().get_span_context()
        self.logs.append({"body": message, "severity": logging.getLevelName(level),
                          "trace_id": format(sc.trace_id, "032x") if sc.trace_id else None, "span_id": format(sc.span_id, "016x") if sc.span_id else None,
                          "attributes": dict(fields)})


# TODO 7
def run_tools_parallel(tracer, tool_names) -> None:
    def work(name):
        with tracer.start_as_current_span(f"execute_tool {name}"):
            time.sleep(0.001)
    with tracer.start_as_current_span("invoke_agent parallel-demo"):
        with ThreadPoolExecutor(max(1, len(tool_names))) as ex:
            futs = [ex.submit(contextvars.copy_context().run, work, n) for n in tool_names]       # la copia se hace AQUÍ, con el raíz activo
            [f.result() for f in futs]


# TODO 8
def retries_from_spans(spans_) -> int:
    return sum(1 for s in spans_ if s.name.startswith("chat ") and s.attributes.get("supportops.attempt", 0) >= 1)

def slowest_tool(spans_):
    d: dict = {}
    for s in spans_:
        if s.attributes.get("gen_ai.tool.name"):
            d.setdefault(s.attributes["gen_ai.tool.name"], []).append((s.end_time - s.start_time) / 1e9)
    return max(((n, viz.percentile(v, 0.95)) for n, v in d.items()), key=lambda x: x[1])


# TODO 9
def export_live(n: int = 20) -> str:
    prov, mem_ = init_tracing(otlp_endpoint="http://localhost:4318")
    instr = StudentInstrumentor(prov.get_tracer("supportops.student"), [])
    run_tickets(SupportAgent(instrumentor=instr), generate_tickets(n, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, start_s="live"))
    prov.force_flush(10000)
    tid = format(mem_.get_finished_spans()[0].context.trace_id, "032x")
    prov.shutdown()
    return tid
''')
    code('''
# Re-ejecuta tu comprobación con la solución de referencia
results, spans, logs = instrument_and_run(tickets)
display(run_rubric())
print("reintentos:", retries_from_spans(spans), "· herramienta más lenta (p95):", slowest_tool(spans))
''')
    nb.save(out)


# =====================================================================================================================
def build_readme() -> None:
    (COURSE / MOD / "README.md").write_text("""# Módulo 03 · El SDK de OpenTelemetry para Python

🟡 Intermedio · ≈ 4 h 30 min · **Servicios opcionales:** `docker compose --profile core up -d` (Collector + Tempo + Loki, ≈ 0,4 GB en reposo). Sin Docker funciona en **modo degradado** (telemetría en memoria).

## Qué aprenderás
- La separación **API / SDK** y el camino de un span: *Sampler → Span → SpanProcessor → Exporter → OTLP*.
- Un **tracer construido a mano** (ids, `contextvars`, tiempos, estado) y un exportador **OTLP/JSON** casero, para entender qué hace el SDK por debajo.
- `TracerProvider`, `Resource`, spans con atributos, eventos, *links*, estado y excepciones; `SpanKind`; límites del SDK (128 atributos/eventos).
- **Contexto y propagación W3C** (`traceparent`, `inject`/`extract`) entre servicios HTTP reales, y qué se rompe con hilos o cabeceras mal normalizadas.
- `SimpleSpanProcessor` frente a `BatchSpanProcessor`: capacidad, cola, **pérdida de spans** medida; *head sampling* y por qué el sampler solo ve los atributos del momento de crear el span.
- El exportador **OTLP/HTTP** hacia el Collector, variables de entorno `OTEL_*` y verificación de la traza en **Tempo**.
- **SupportOps v1**: instrumentación manual de `invoke_agent` → `chat` → `execute_tool`, logs correlacionados con `trace_id`, y el **coste medido** de instrumentar.

## Archivos
| Archivo | Contenido |
|---|---|
| `03_otel_sdk_python.ipynb` | Lección (teoría + código + 10 gráficos + autoevaluación) |
| `03_proyecto_otel_sdk_python.ipynb` | Proyecto: instrumenta a mano SupportOps v0 (9 TODO), rúbrica de 10 criterios medibles y retos de nivel experto |

## Código de referencia: `supportops.telemetry`
Este módulo enseña a construir la instrumentación a mano; `agent-observability-course/supportops/telemetry.py` es la **versión consolidada** que reutilizan los módulos siguientes:

```python
from supportops.telemetry import setup_telemetry, OTelInstrumentor
tel = setup_telemetry("supportops-agent")                 # OTLP/HTTP a localhost:4318; sin Collector → memoria (aviso)
agent = SupportAgent(instrumentor=OTelInstrumentor(tel))  # spans GenAI + métricas mínimas + logs con trace_id/span_id
...
tel.force_flush(); tel.shutdown()
```
API completa y qué se ve en cada backend: `_tools/INTERFACES.md`, sección 4.

## Servicios necesarios
`core` (Collector, Tempo, Loki) **solo** para los pasos «ver la traza en Tempo/Loki». Todo lo demás (incluida la rúbrica) corre en memoria.

## Lecturas
- OpenTelemetry, *Instrumentation*, *Exporters* y *Propagation* para Python — <https://opentelemetry.io/docs/languages/python/>
- OpenTelemetry Specification, *Trace API* y *Trace SDK* — <https://github.com/open-telemetry/opentelemetry-specification/tree/main/specification/trace>
- W3C, *Trace Context* — <https://www.w3.org/TR/trace-context/>
- OpenTelemetry, *Zero-code Python · Troubleshooting* (servidores pre-fork) — <https://opentelemetry.io/docs/zero-code/python/troubleshooting/>

## Siguiente
`04_genai_semconv`: estandarizar los nombres de atributo de tus spans con las *GenAI semantic conventions* y validarlos con un linter propio.
""", encoding="utf-8")
    print("OK README 03")


if __name__ == "__main__":
    build_lesson()
    build_project()
    build_readme()
