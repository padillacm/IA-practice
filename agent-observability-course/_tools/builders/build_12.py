"""Genera el módulo 12_mcp_tools: README, lección, proyecto y dashboard.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_12.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "12_mcp_tools"

PIP_MCP = '''
# El SDK oficial de Python de MCP (v2.x). La versión 1.x tenía otra API (FastMCP); este módulo usa `mcp.server.mcpserver.MCPServer` y `mcp.Client`.
%pip install -q "mcp>=2,<3"
'''

IMPORTS_12 = '''
import asyncio, contextvars, dataclasses, inspect, json, time
from concurrent.futures import ThreadPoolExecutor
from opentelemetry import trace as otel_trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from supportops import catalog
from supportops.instrument import CompositeInstrumentor
from supportops.telemetry import setup_telemetry
from supportops.tools import ToolError
from supportops.mcp_orders import (TOOL_META, McpServerProcess, McpToolBridge, McpToolSpanEnricher, WallClockInstrumentor, build_server, redact_args,
                                   tools_fingerprint, tracking_rule)
from supportops.multiagent import agent_tree_text, attached, extract_manual, inject_manual, parse_traceparent, service_palette, waterfall_services

os.environ["SUPPORTOPS_REAL_SLEEP_SCALE"] = "0.02"      # 1 s simulado del agente = 20 ms de pared (los spans del SDK de MCP usan el reloj REAL)
STACK = check_stack("core")
LIVE = not STACK.degraded                                  # True: el Collector responde y enviamos la telemetría de verdad
TEL = setup_telemetry("supportops-agent", mode="otlp" if LIVE else "memory", resource_attrs={"deployment.environment.name": "lab"})

def run_async(coro):
    """Ejecuta una corrutina desde una celda de Jupyter (que ya tiene un bucle) usando un hilo con su propio bucle."""
    with ThreadPoolExecutor(1) as ex:
        return ex.submit(asyncio.run, coro).result()
'''


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "12_mcp_tools.ipynb", "Módulo 12 · Trazas a través de servidores MCP y herramientas remotas")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 12 · Trazas a través de servidores MCP y herramientas remotas

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 5 h (lección ≈ 3 h 15 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Opcional: `--profile core` + `metrics` (sección 11). Sin Docker funciona en **modo degradado** (telemetría en memoria; los spans del servidor MCP se leen de un fichero JSONL). Necesita lanzar un proceso hijo: en Colab funciona; en entornos muy restringidos puede no ser posible |
    | **RAM aproximada** | < 700 MB sin stack · ≈ 1,3 GB con `core` + `metrics` |
    | **Prerrequisitos** | Módulos 03 (SDK, `OTelInstrumentor`), 04 (GenAI semconv) y 11 (propagación W3C, trazas partidas) |
    | **Hilo conductor** | Las herramientas de pedidos de SupportOps dejan de ser funciones locales: pasan a un **servidor MCP** en otro proceso |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** qué es MCP (clientes, servidores, herramientas, transportes) y por qué una herramienta remota **rompe el tracing** si no se propaga el contexto.
    2. **Construir** un servidor MCP con el SDK oficial de Python y **ejecutarlo como proceso aparte** (stdio).
    3. **Medir** los spans que el SDK emite en cliente y servidor y **compararlos** con las convenciones semánticas de MCP (estado *Development*), listando las desviaciones.
    4. **Unir** la traza del servidor con la del agente; **detectar y corregir** la pérdida de contexto al llamar desde hilos.
    5. **Distinguir y registrar** tres tipos de fallo: error de herramienta (`isError`), *timeout* y error de protocolo/conexión; **medir el trabajo zombi** del servidor.
    6. **Proteger** los reintentos de herramientas destructivas con **claves de idempotencia** y **auditarlas**.
    7. **Aplicar seguridad** a la telemetría de herramientas: no capturar argumentos por defecto, lista blanca y redacción, política de confianza del contexto remoto y **huella** de las herramientas.
    8. **Operar** con la métrica `mcp.*.operation.duration` y consultas TraceQL de «traza partida».
    """)

    md("""
    > 🧭 **Ruta núcleo vs ampliación (75 celdas: dos sesiones).**
    > - **Sesión A (≈ 1 h 40 min):** secciones 1-5 → qué es MCP, la convención de spans, el servidor de pedidos, lo que emite el SDK y cómo el agente usa las herramientas remotas.
    > - **Sesión B (≈ 1 h 35 min):** secciones 6-10 → hilos y contexto, fallos, reintentos idempotentes, seguridad y estado de la spec. Después, el proyecto (usa A y B).
    > - **Ampliación opcional (≈ 20 min, requiere stack):** sección 11 (métricas, dashboard y TraceQL en Grafana).
    """)

    md("## 🔁 Conexión con módulos anteriores")
    md(details("1 · (Módulo 11) Un subagente aparece como una traza suelta en Tempo. ¿Qué dos causas comunes hay y cómo las distingues?",
               "(a) Nadie inyectó `traceparent` en la llamada (propagación `none`) o (b) el contexto se perdió al cambiar de hilo/proceso/cola. Se distinguen mirando si la cabecera/`_meta` llegó al receptor: si no llegó, falla el emisor; si llegó y el receptor abrió traza nueva, falla la extracción. El detector estructural es «raíz `invoke_agent` sin padre fuera del orquestador»; aquí será «span servidor MCP sin padre»."))
    md(details("2 · (Módulo 11) Si el consumidor de una cola enlaza al productor con un *span link* en lugar de ser su hijo, ¿cuántas trazas ves?",
               "Dos: cada lado conserva su `trace_id` y el consumidor lleva un enlace al contexto del productor. Con padre-hijo habría una sola traza."))
    md(details("3 · (Módulo 04) ¿Qué atributos lleva un span `execute_tool` y cuál de ellos es sensible por defecto?",
               "`gen_ai.operation.name=execute_tool`, `gen_ai.tool.name`, `gen_ai.tool.call.id`, `gen_ai.tool.type`. `gen_ai.tool.call.arguments` y `gen_ai.tool.call.result` son **opt-in** y pueden contener datos sensibles (la spec lo avisa)."))

    md(details("4 · (Módulo 11, diagnóstico) Un `ThreadPoolExecutor` ejecuta llamadas a herramientas y sus spans salen como trazas sueltas aunque el padre sí inyecta `traceparent`. ¿Qué pasa y cómo se arregla?",
               "El contexto de OpenTelemetry vive en `contextvars`, y los hilos del *pool* **no lo heredan**: dentro del hilo no hay span activo, así que el span nace como raíz con otro `trace_id`. Arreglo: capturar el contexto al encolar (`ctx = contextvars.copy_context()` y `executor.submit(ctx.run, fn, ...)`) o pasar y adjuntar el contexto explícitamente. Lo verás medido en la sección 6."))

    code(boot("viz,otel"))
    code(PIP_MCP)
    code(IMPORTS + IMPORTS_12 + '''
import mcp, importlib.metadata as _md
print(f"SDK de MCP {_md.version('mcp')} · Stack:", "arriba (OTLP al Collector)" if LIVE else "no disponible -> modo degradado (telemetría en memoria)")
''')

    # ------------------------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · Intuición: una herramienta que vive en otro proceso

    Hasta ahora las herramientas de SupportOps eran funciones de Python en el mismo proceso del agente: `execute_tool get_order` duraba lo que durase la función y, si fallaba, la excepción llegaba al bucle. **MCP** (*Model Context Protocol*) estandariza cómo un agente descubre y llama herramientas que viven en **otro proceso o servicio**: el *servidor MCP* anuncia sus herramientas (nombre, descripción, esquema de argumentos) y el *cliente MCP* (dentro del agente) las invoca con mensajes **JSON-RPC 2.0** sobre un transporte (stdio para procesos hijos locales, HTTP en streaming para servicios remotos).

    | Si vienes de… | MCP es como… | Lo que cambia al observarlo |
    |---|---|---|
    | **ML** | Servir un modelo o un *feature store* detrás de un endpoint | La latencia ya no es CPU local: hay red, serialización, colas y *otro* equipo que escribe el servidor |
    | **Backend** | Una llamada gRPC/REST a un microservicio con contrato (esquema) | Necesitas **tracing distribuido**: un span cliente, un span servidor y el contexto viajando en el mensaje |
    | **SRE** | Una dependencia externa con timeouts, reintentos y SLO propio | Los fallos tienen tres formas distintas (error de herramienta, timeout, conexión) y los reintentos pueden **duplicar efectos** |
    """)
    code('''
fig, ax = viz.canvas(12.5, 5.4, xlim=(0, 125), ylim=(0, 54))
viz.box(ax, 1, 4, 52, 46, "", color=viz.PALETTE["traces"], fc="#2a6fdb12")
viz.box(ax, 70, 4, 53, 46, "", color=viz.PALETTE["logs"], fc="#2f9e6312")
ax.text(27, 47, "PROCESO A · supportops-agent", ha="center", fontsize=9.5, fontweight="bold", color=viz.PALETTE["traces"])
ax.text(96.5, 47, "PROCESO B · supportops-orders-mcp", ha="center", fontsize=9.5, fontweight="bold", color=viz.PALETTE["logs"])
a1 = viz.box(ax, 5, 33, 44, 8, "invoke_agent supportops-agent", color=viz.PALETTE["traces"], fontsize=8.5)
a2 = viz.box(ax, 8, 21, 38, 8, "execute_tool track_shipment", color=viz.PALETTE["traces"], fontsize=8.5)
a3 = viz.box(ax, 11, 9, 38, 8, "MCP send tools/call  [CLIENT]", color=viz.PALETTE["metrics"], fontsize=8.5, bold=True)
b1 = viz.box(ax, 74, 21, 44, 8, "tools/call track_shipment  [SERVER]", color=viz.PALETTE["metrics"], fontsize=8.5, bold=True)
b2 = viz.box(ax, 78, 9, 38, 8, "GET carrier-api  (dependencia)", color=viz.PALETTE["logs"], fontsize=8.5)
viz.arrow(ax, (27, 33), (27, 29.3), color=viz.PALETTE["neutral"])
viz.arrow(ax, (27, 21), (30, 17.3), color=viz.PALETTE["neutral"])
viz.arrow(ax, viz.right(a3), (74, 26), "", color=viz.PALETTE["metrics"], rad=-0.2)
ax.text(62, 32, "JSON-RPC por stdio / HTTP\\nparams._meta.traceparent", ha="center", fontsize=8, color=viz.PALETTE["metrics"])
viz.arrow(ax, (96, 21), (96, 17.3), color=viz.PALETTE["neutral"])
viz.arrow(ax, (74, 22), (49.5, 11), "", color=viz.PALETTE["neutral"], rad=-0.15, dashed=True)
ax.text(61, 12.5, "result (¿isError?)", ha="center", fontsize=7.5, color=viz.PALETTE["neutral"])
ax.text(62, 52, "dos spans por salto: CLIENT (lo que ve el llamador) y SERVER (lo que hizo el servidor)", ha="center", fontsize=8.5, color=viz.PALETTE["neutral"])
ax.set_title("Una herramienta MCP cruza un límite de proceso: el contexto debe viajar DENTRO del mensaje", loc="left")
plt.show()
''')
    md(observe("""
    - La frontera entre procesos (línea vertical) es donde la traza **se puede romper**: solo bytes la cruzan. El estándar MCP reserva `params._meta` para llevar `traceparent` (SEP-414), así que el contexto va **en el mensaje JSON-RPC**, no en una cabecera HTTP: funciona igual con stdio (que no tiene cabeceras) y con HTTP.
    - Cada salto genera **dos spans** con el mismo propósito visto desde cada lado. Si los cuentas los dos como «la llamada a la herramienta» contarás latencias y errores dos veces (hay un tercer span, `execute_tool`, del agente: la sección 6 aclara cuál usar para qué).
    - La caja del servidor tiene **dependencias propias** (BD, API del transportista): ahí se esconde casi siempre la latencia real.
    """))

    # ------------------------------------------------------------------------------------------------------------- 2
    md("""
    ---
    # 2 · Teoría: MCP y su observabilidad

    ## 2.1 MCP en un minuto

    - **Roles:** un *host* (la aplicación del agente) contiene uno o varios *clientes* MCP; cada cliente mantiene una conexión con un *servidor*.
    - **Primitivas del servidor:** *tools* (acciones que el modelo puede pedir), *resources* (datos de lectura) y *prompts* (plantillas). Este módulo trata las **herramientas**.
    - **Transportes:** `stdio` (el cliente lanza el servidor como proceso hijo y habla por stdin/stdout) y *Streamable HTTP* (servicio remoto). Mensajes **JSON-RPC 2.0**.
    - **Anotaciones de herramienta:** pistas `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`: **no** son garantías de seguridad (las declara el servidor), pero son metadatos excelentes para la telemetría (¿audito esta herramienta? ¿puedo reintentarla?).
    - **Dos canales de error distintos:** un fallo de *protocolo* (JSON-RPC `error`: método desconocido, parámetros inválidos, conexión) y un fallo de *herramienta* (`result` con `isError: true`, para que el **modelo** lo lea y se adapte). La telemetría debe distinguirlos.

    ## 2.2 Convenciones semánticas de MCP en OpenTelemetry (estado **Development**)

    Definidas en el repositorio `open-telemetry/semantic-conventions-genai` (`docs/gen-ai/mcp.md`; la página oficial de la web las muestra como «Semantic conventions for Model Context Protocol (MCP)»). **Todo es *Development***: los nombres pueden cambiar.

    | Elemento | Convención |
    |---|---|
    | Nombre de span | `{mcp.method.name} {target}` (p. ej. `tools/call get_order`); el *target* es `gen_ai.tool.name` o `gen_ai.prompt.name`. La URI de un recurso **no** va en el nombre por defecto (alta cardinalidad) |
    | Kind | `CLIENT` en el cliente, `SERVER` en el servidor |
    | Atributos | **Requerido:** `mcp.method.name`. **Condicionalmente:** `error.type`, `gen_ai.tool.name`, `jsonrpc.request.id` (cliente), `rpc.response.status_code`. **Recomendados:** `gen_ai.operation.name=execute_tool` (para `tools/call`), `mcp.protocol.version`, `mcp.session.id`, `network.transport` (`pipe` = stdio; `tcp`/`quic` = HTTP) |
    | Opt-in (sensibles) | `gen_ai.tool.call.arguments`, `gen_ai.tool.call.result`, `gen_ai.prompt.variable.*` |
    | Errores | `isError: true` ⇒ `error.type = "tool_error"`; error JSON-RPC ⇒ `error.type` = código; los códigos `-32602` etc. que indican «el llamador se equivocó» **no** deben contar como error del servidor |
    | Contexto | Se inyecta en `params._meta` con claves **sin prefijo** `traceparent`, `tracestate`, `baggage` (SEP-414); el receptor lo usa como **padre remoto** y *debería* enlazar el contexto ambiente si existe |
    | Métricas | Histogramas en segundos: `mcp.client.operation.duration`, `mcp.server.operation.duration`, `mcp.client.session.duration`, `mcp.server.session.duration` (buckets de 0,01 a 300 s) |

    > 💡 La spec añade que *«los spans de ejecución de herramientas MCP son compatibles con `execute_tool` de GenAI»*, y que el contexto HTTP y el de MCP son **independientes**: una petición HTTP puede servir varios mensajes MCP y viceversa; por eso el padre del span servidor es el span cliente **por mensaje**, no el del transporte.

    ## 2.3 ¿Qué hace ya el SDK de Python?

    El SDK oficial (v2.x) incluye instrumentación OpenTelemetry **de serie**: un span cliente por petición con inyección de `traceparent` en `_meta` y un `OpenTelemetryMiddleware` servidor activado por defecto que extrae ese contexto. Lo comprobaremos midiendo. Lo que **no** trae, como verás, es todo lo que la spec recomienda: por eso este módulo añade lo que falta.
    """)

    # ------------------------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · Un servidor MCP en 10 líneas… y el de pedidos de SupportOps

    La API del SDK v2 es `MCPServer` (en v1 se llamaba `FastMCP`): un decorador `@server.tool()` convierte una función con *type hints* en una herramienta; el esquema de entrada sale de las anotaciones y la descripción del *docstring*.
    """)
    code('''
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp_types import ToolAnnotations

demo = MCPServer("demo")

@demo.tool(annotations=ToolAnnotations(read_only_hint=True, idempotent_hint=True))
def suma(a: int, b: int) -> int:
    """Suma dos enteros."""
    return a + b

async def ejemplo():
    async with Client(demo) as c:                       # Client(servidor) = en proceso, sin transporte (solo para probar)
        tools = (await c.list_tools()).tools
        r = await c.call_tool("suma", {"a": 2, "b": 3})
        return tools[0].name, tools[0].input_schema["properties"], r.structured_content, r.is_error

print(run_async(ejemplo()))
''')
    md("""
    El servidor de pedidos (`supportops/mcp_orders.py`, en `build_server`) expone cinco herramientas con anotaciones coherentes y datos del catálogo de SupportOps. Inspeccionamos lo que **anuncia** (esto es lo que lee el modelo):
    """)
    code('''
async def anuncio():
    async with Client(build_server("normal")) as c:
        return (await c.list_tools()).tools
tl = run_async(anuncio())
df_tools = pd.DataFrame([{"herramienta": t.name, "solo lectura": t.annotations.read_only_hint, "destructiva": t.annotations.destructive_hint,
                          "idempotente": t.annotations.idempotent_hint, "mundo abierto": t.annotations.open_world_hint,
                          "argumentos": ", ".join(t.input_schema.get("properties", {}))} for t in tl])
display(df_tools)
print("huella de las herramientas (SHA-256 corta de nombres+descripciones+esquemas):", tools_fingerprint(tl))
''')
    md(box("idea", "Tres decisiones de diseño del servidor que importan para observar", """
    1. **`ToolError` frente a `RuntimeError`.** Si la herramienta lanza `ToolError("el transportista no responde (503)")` el SDK transmite el mensaje al modelo (`isError`); si lanza una excepción cualquiera, solo envía «Error executing tool …» y **oculta los detalles internos**. Es una buena protección, pero significa que el detalle del fallo **solo está en la telemetría del servidor**.
    2. **Spans de dependencias.** Cada herramienta abre un span hijo para su dependencia (`SELECT orders-db`, `GET carrier-api`, `POST payments-api`): sin ellos el servidor es una caja negra de «271 ms».
    3. **Latencias simuladas y comprimidas.** El transportista tarda 0,30 s *simulados* (×25 para los pedidos múltiplos de 17, y ×6 en modo `slow`); la variable `ORDERS_MCP_TIME_SCALE=0.02` las comprime (1 s simulado = 20 ms reales) para que el notebook sea rápido. Los fallos son **deterministas por pedido** (múltiplos de 13 → 503; de 17 → lento).
    """))

    md("""
    ## 3.1 Middleware del servidor: añadir lo que el SDK no hace

    El `MCPServer` admite **middleware** (`MCPServer(middleware=[...])` o `server.middleware.append(...)`): una corrutina `async (ctx, call_next)` que envuelve cada mensaje entrante. Se ejecuta **dentro** del middleware OpenTelemetry del SDK, de modo que `trace.get_current_span()` es el span servidor `tools/call <tool>`: podemos enriquecerlo, auditar, medir y **clasificar errores** sin tocar las herramientas. (API *provisional* en 2.x: puede cambiar en una versión menor.) Este es el middleware de pedidos:
    """)
    code('''
from supportops.mcp_orders import OrdersTelemetryMiddleware
print(inspect.getsource(OrdersTelemetryMiddleware.__call__))
''')
    md(observe("""
    - Solo actúa en `tools/call`; el resto de mensajes (`tools/list`, `server/discover`…) pasan intactos.
    - Los **atributos de la herramienta** salen de una tabla propia (`TOOL_META`, la misma que las anotaciones): así el span dice si la herramienta es de solo lectura o destructiva **sin** necesidad de consultar el servidor.
    - La clasificación `supportops.error.class = caller | server` aplica la regla de la spec: *herramienta inexistente* o *argumentos inválidos* los causó el llamador y **no** deberían contar contra la disponibilidad del servidor.
    - `try/finally` garantiza **auditoría y métrica incluso si la herramienta falla**; los argumentos solo se capturan si `capture_args` (opt-in).
    """))

    # ------------------------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · Lo que emite el SDK: una llamada, dos procesos

    Lanzamos el servidor como **proceso hijo por stdio** (`McpServerProcess`) y nos conectamos con un puente cliente (`McpToolBridge`: un cliente MCP en su propio hilo/bucle asyncio que expone las herramientas como funciones síncronas, que es lo que espera el bucle del agente). El proceso servidor monta **su propia telemetría** (`service.name = supportops-orders-mcp`) y escribe sus spans en un fichero JSONL (en producción los enviaría por OTLP al Collector).
    """)
    code('''
SP = McpServerProcess(telemetry="otlp" if LIVE else "memory", time_scale=0.02)
try: BR.close()
except NameError: pass
BR = McpToolBridge(SP.params(), read_timeout_s=3.0, meter=TEL.meter())
print("conectado · herramientas:", [t.name for t in BR.tools_list], "· huella:", BR.fingerprint)

def trace_rows(tid, wait=0.4):
    """Spans de la traza `tid` de los DOS procesos (agente: memoria; servidor: fichero JSONL), ordenados por inicio."""
    time.sleep(wait)
    rows = [r for r in TEL.span_records() if r["trace_id"] == tid] + [r for r in SP.spans() if r["trace_id"] == tid]
    return sorted(rows, key=lambda r: (r["start_unix_nano"], -(r["end_unix_nano"] or 0)))

tracer = TEL.tracer()
with tracer.start_as_current_span("execute_tool get_order", kind=SpanKind.INTERNAL) as sp:
    res = BR.call("get_order", {"order_id": "ORD-00001"})
tid = format(sp.get_span_context().trace_id, "032x")
rows = trace_rows(tid)
tab = pd.DataFrame([{"span": r["name"], "kind": r["kind"], "servicio": r["resource"]["service.name"], "pid": r["resource"].get("process.pid"),
                     "id": r["span_id"][:6], "padre": (r["parent_span_id"] or "—")[:6], "ms": round((r["end_unix_nano"] - r["start_unix_nano"]) / 1e6, 1)} for r in rows])
display(tab)
print("¿un único trace_id?", len({r["trace_id"] for r in rows}) == 1)
''')
    code('''
fig, ax = plt.subplots(figsize=(11, 3.4)); fig.subplots_adjust(left=0.30)
waterfall_services(rows, ax=ax, unit="ms", title="Una llamada a get_order cruza dos procesos (tiempo de pared, ms)")
plt.show()
''')
    md(observe("""
    - **Un solo `trace_id` y dos `pid`**: el span `tools/call get_order` (SERVER, proceso B) es **hijo** del span `MCP send tools/call get_order` (CLIENT, proceso A), que a su vez es hijo del `execute_tool` del agente. Nadie escribió código de propagación: lo hizo el SDK.
    - La barra del CLIENT es **más larga** que la del SERVER: la diferencia es el *overhead* de transporte y serialización (stdio + JSON-RPC + el bucle asyncio del puente). Lo medimos con muchas llamadas en la sección 6.
    - Dentro del servidor, más de la mitad del tiempo está en la dependencia (`SELECT orders-db`): sin ese span hijo sería invisible.
    - Fíjate en el **nombre** del span cliente: `MCP send tools/call get_order`. No coincide con el de la spec (`tools/call get_order`). Es la primera de varias desviaciones que cuantificaremos en la sección 10.
    """))
    md("""
    ## 4.1 Continuar una traza que llega de fuera (y una trampa con `meta=`)

    Escenario habitual: el endpoint HTTP del chat de soporte recibe una petición con `traceparent` y tu código debe **continuar esa traza** a través de MCP. El `call_tool` del SDK acepta `meta=` (se copia a `params._meta`), así que parece natural pasarlo ahí. Probamos las dos formas, **sin span activo** en este proceso:
    """)
    code('''
upstream = otel_trace.get_tracer("endpoint-http").start_span("POST /chat", kind=SpanKind.SERVER)
with otel_trace.use_span(upstream, end_on_exit=False):
    header = inject_manual()                           # lo que llegaría en la cabecera HTTP de entrada (módulo 11)
upstream.end()
up_tid, up_sid = format(upstream.get_span_context().trace_id, "032x"), format(upstream.get_span_context().span_id, "016x")

BR.call("get_order", {"order_id": "ORD-00003"}, meta=header)                       # (a) ingenuo: meta= con el traceparent
with attached(extract_manual(header)):                                              # (b) correcto: el contexto remoto pasa a ser el ACTUAL
    BR.call("get_order", {"order_id": "ORD-00004"})
time.sleep(0.5)
cands = [r for r in SP.spans() if r["name"] == "tools/call get_order"][-2:]
cli_by_id = {r["span_id"]: r for r in TEL.span_records()}
display(pd.DataFrame([{"intento": e, "¿misma traza que el endpoint?": c["trace_id"] == up_tid,
                       "el span CLIENTE del SDK cuelga de…": "el endpoint" if cli_by_id[c["parent_span_id"]]["parent_span_id"] == up_sid else "nada (raíz de otra traza)"}
                      for e, c in zip(("(a) meta=header", "(b) attached(extract_manual(header))"), cands)]).set_index("intento"))
''')
    md(observe("""
    - **(a) falla en silencio**: el SDK abre su propio span cliente y **sobrescribe** `traceparent` en `_meta` con el de *ese* span; lo que pasaste en `meta=` se pierde (la traza del servidor empieza en el SDK, no en el endpoint). `meta=` sirve para metadatos propios, no para forzar el padre.
    - **(b) funciona**: hay que hacer **actual** el contexto remoto (`attach`): el span cliente del SDK nace como hijo del endpoint y el servidor hereda su `trace_id`. Es el patrón general: *el contexto se adjunta, no se pasa como argumento*.
    - Si tu cliente **no** es el SDK (otro lenguaje, un *gateway*), tú inyectas `traceparent` en `params._meta` con el propagador: el servidor lo usará como padre remoto (SEP-414).
    """))

    # ------------------------------------------------------------------------------------------------------------- 5
    md("""
    ---
    # 5 · El agente usa las herramientas remotas

    Conectamos el puente al `SupportAgent`: `bridge.register_tools(registry, ...)` crea `Tool`s cuyo `fn` llama al servidor MCP (misma firma y esquema que anuncia el servidor). Dos ajustes de observabilidad:

    - **Reloj de pared.** El `OTelInstrumentor` del módulo 03 usa el reloj *simulado* del agente; los spans del SDK de MCP usan el reloj *real*. Mezclarlos produciría cascadas imposibles (un hijo fuera de su padre). `WallClockInstrumentor` usa el reloj real y `SUPPORTOPS_REAL_SLEEP_SCALE=0.02` hace que las latencias simuladas del agente ocupen tiempo real comprimido.
    - **Marcar las herramientas remotas** (`McpToolSpanEnricher`): `gen_ai.tool.type=extension` (herramienta del lado agente que llama a una API externa), `supportops.mcp.server` y `network.transport=pipe` en el span `execute_tool`.
    """)
    code('''
registry = default_tools()
remote = BR.register_tools(registry, ["get_order", "track_shipment", "issue_refund"])
llm = MockLLM("mock-small"); llm.add_rule(tracking_rule())            # «seguimiento/tracking» -> get_order + track_shipment
agent = SupportAgent(llm=llm, tools=registry, instrumentor=CompositeInstrumentor(WallClockInstrumentor(TEL), McpToolSpanEnricher(remote)))
pool = generate_tickets(120, seed=SEED)
tk = [t for t in pool if t.intent_true in ("order_status", "refund")][: (10 if FAST_DEV_RUN else 40)]
SP.reset_spans(); TEL.reset_local()
t0 = time.time(); results = [agent.run(dataclasses.replace(t, faults=[], created_at=time.time())) for t in tk]
print(f"{len(tk)} tickets en {time.time() - t0:.1f}s de pared · estados: {pd.Series([r.status for r in results]).value_counts().to_dict()}")
time.sleep(0.6)
AG, SV = TEL.span_records(), SP.spans()
agent_tids = {r["trace_id"] for r in AG if r["name"].startswith("invoke_agent")}
calls = [r for r in SV if r["name"].startswith("tools/call")]
print(f"spans del agente: {len(AG)} · spans del servidor MCP: {len(SV)} · llamadas tools/call: {len(calls)} · unidas a una traza del agente: {sum(r['trace_id'] in agent_tids for r in calls)}")
''')
    code('''
slow_tid = next(r["trace_id"] for r in SV if r["name"] == "tools/call track_shipment" and r["trace_id"] in agent_tids)
rows = [r for r in AG + SV if r["trace_id"] == slow_tid]
print(agent_tree_text(rows, ops=("invoke_agent", "execute_tool")))
fig, ax = plt.subplots(figsize=(11.5, 5.2)); fig.subplots_adjust(left=0.33)
waterfall_services(rows, ax=ax, unit="ms", title="Un ticket de seguimiento: agente (A) → cliente MCP → servidor (B) → transportista")
plt.show()
''')
    md(observe("""
    - La traza del ticket contiene **ambos servicios** (`supportops-agent` y `supportops-orders-mcp`) con jerarquía correcta: `execute_tool track_shipment` → `MCP send tools/call` → `tools/call` → `GET carrier-api`. Un ingeniero de guardia puede ir del síntoma («el seguimiento tarda») a la dependencia culpable en un clic.
    - El agente tiene **dos** `execute_tool` (get_order y track_shipment) y el LLM entre ellos; el tiempo de pared del ticket (≈ 0,2 s) refleja la compresión ×50 de las latencias simuladas.
    - Cada span `execute_tool` de una herramienta remota está marcado como `extension` y con el servidor: basta un filtro `span.supportops.tool.remote = true` para aislar el comportamiento de herramientas remotas frente a locales.
    """))
    md("### El coste de cruzar la frontera: *overhead* por herramienta")
    code('''
by_id = {r["span_id"]: r for r in AG + SV}
rec = []
for r in SV:
    if r["name"].startswith("tools/call") and r["parent_span_id"] in by_id:
        c = by_id[r["parent_span_id"]]
        deps = [d for d in SV if d["parent_span_id"] == r["span_id"]]
        rec.append({"tool": r["attributes"]["gen_ai.tool.name"], "cliente_ms": (c["end_unix_nano"] - c["start_unix_nano"]) / 1e6,
                    "servidor_ms": (r["end_unix_nano"] - r["start_unix_nano"]) / 1e6, "dependencia_ms": sum((d["end_unix_nano"] - d["start_unix_nano"]) / 1e6 for d in deps)})
O = pd.DataFrame(rec); O["overhead_ms"] = O.cliente_ms - O.servidor_ms; O["resto_servidor_ms"] = O.servidor_ms - O.dependencia_ms
display(O.groupby("tool")[["cliente_ms", "servidor_ms", "dependencia_ms", "overhead_ms"]].median().round(1))
fig, axes = plt.subplots(1, 2, figsize=(12.5, 3.9))
tools_ = sorted(O.tool.unique())
axes[0].boxplot([O[O.tool == t].overhead_ms for t in tools_], tick_labels=tools_, showfliers=False); axes[0].set_title("Overhead cliente − servidor (ms)")
parts = O.groupby("tool")[["dependencia_ms", "resto_servidor_ms", "overhead_ms"]].median().loc[tools_]
parts.plot.bar(stacked=True, ax=axes[1], color=[viz.PALETTE["logs"], viz.PALETTE["traces"], viz.PALETTE["metrics"]], rot=0); axes[1].set_title("¿Dónde está el tiempo de una llamada? (mediana, ms)"); axes[1].set_xlabel("")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El **overhead** (cliente − servidor) es de unos pocos ms y casi **constante** entre herramientas: es el precio de stdio + JSON-RPC + el puente. Un salto de ese overhead (p. ej. 5 ms → 80 ms) indica problemas de transporte o saturación del bucle del cliente, **no** de la herramienta.
    - En `track_shipment` y `issue_refund` casi todo el tiempo es **dependencia** (transportista, pasarela de pagos): ahí debes buscar cuando la herramienta se enlentece. Un dashboard que solo mida «latencia de la herramienta» no distingue entre ambos casos.
    """))

    # ------------------------------------------------------------------------------------------------------------- 6
    md("""
    ---
    # 6 · Dónde se pierde el contexto: hilos

    Muchos *frameworks* de agentes ejecutan las herramientas en un `ThreadPoolExecutor` para paralelizarlas. En Python, `contextvars` (donde vive el span activo) **no** se hereda al hilo de un *executor*: el cliente MCP no ve el span del agente, no inyecta nada útil y el servidor abre una traza propia. Lo comprobamos con 6 llamadas por cada variante:
    """)
    code('''
def llamadas(n, copiar_contexto):
    with tracer.start_as_current_span(f"agente (copiar_contexto={copiar_contexto})") as sp, ThreadPoolExecutor(2) as ex:
        futs = [ex.submit(*(([contextvars.copy_context().run] if copiar_contexto else []) + [BR.call, "get_order", {"order_id": f"ORD-{100 + i:05d}"}])) for i in range(n)]
        [f.result() for f in futs]
    return format(sp.get_span_context().trace_id, "032x")

SP.reset_spans()
tids_ = {False: llamadas(6, False), True: llamadas(6, True)}
time.sleep(0.5)
sv = [r for r in SP.spans() if r["name"] == "tools/call get_order"]
cont = {k: sum(r["trace_id"] == t for r in sv) for k, t in tids_.items()}
huerf = [r for r in sv if r["trace_id"] not in tids_.values() and r["parent_span_id"] is not None]
print({("con copy_context().run" if k else "SIN copiar el contexto"): f"{v}/6 spans servidor unidos a la traza del agente" for k, v in cont.items()})
fig, ax = plt.subplots(figsize=(7.5, 3.4))
ax.bar(["sin copiar contexto", "con copy_context().run"], [cont[False], cont[True]], color=[viz.PALETTE["error"], viz.PALETTE["logs"]]); ax.set_ylim(0, 6.5)
ax.set_ylabel("spans servidor unidos a la traza del agente (de 6)"); ax.set_title("Llamar a la herramienta desde un hilo de un executor"); plt.show()
''')
    md(observe("""
    - **0/6 frente a 6/6**: la corrección es una línea (`executor.submit(contextvars.copy_context().run, fn, *args)`). Sin ella cada llamada produce una traza de servidor que **nadie sabe a qué ticket pertenece**.
    - La causa **no** es el puente: dentro de él `asyncio.run_coroutine_threadsafe` sí copia las `contextvars` del hilo que llama (lo hemos verificado con la llamada directa de la sección 4). El fallo está en **quién llama al puente**.
    - Detector estructural: spans cliente `MCP send tools/call` que son **raíz** de su traza (`nestedSetParent < 0` en TraceQL): el SDK abrió su span sin ningún `execute_tool` del agente encima. La sección 11 lo convierte en un panel.
    """))

    # ------------------------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Fallos: tres formas de romperse y qué ve cada span

    | Fallo | Cómo llega al cliente | Qué debería verse |
    |---|---|---|
    | **Error de herramienta** (el transportista devuelve 503) | `result.isError = true` con un mensaje para el modelo | `error.type = tool_error` (servidor, spec); el cliente **no** lanza excepción |
    | **Timeout** (el llamador se cansa de esperar) | excepción de *timeout* en el cliente | span cliente `ERROR`; el servidor **sigue trabajando** (¿se cancela?) |
    | **Error de protocolo / conexión** (herramienta desconocida, servidor caído) | error JSON-RPC o conexión cerrada | `rpc.response.status_code`, `error.type`; sin respuesta del servidor |

    Los ejecutamos y comparamos **lo que registra cada span** (cliente, servidor, el `execute_tool` del agente):
    """)
    code('''
def escenario(etiqueta, fn):
    """Emula el span execute_tool del agente alrededor de una llamada y devuelve qué ocurrió."""
    with tracer.start_as_current_span(f"execute_tool {etiqueta}", kind=SpanKind.INTERNAL) as sp:
        t0 = time.perf_counter(); err = None
        try: fn()
        except ToolError as e:
            err = e.error_type; sp.set_attribute("error.type", err); sp.set_status(Status(StatusCode.ERROR, str(e)))
        dt = (time.perf_counter() - t0) * 1000
    return {"etiqueta": etiqueta, "tid": format(sp.get_span_context().trace_id, "032x"), "error_type": err, "espera_ms": dt}

SP.reset_spans()
ESC = [escenario("OK", lambda: BR.call("get_order", {"order_id": "ORD-00001"})),
       escenario("error de herramienta (503)", lambda: BR.call("track_shipment", {"order_id": "ORD-00013"})),
       escenario("timeout (100 ms)", lambda: BR.call("track_shipment", {"order_id": "ORD-00017"}, timeout_s=0.1)),
       escenario("herramienta desconocida", lambda: BR.call("no_existe", {}))]
time.sleep(0.8)
rows_ = []
for e in ESC:
    rs = trace_rows(e["tid"], wait=0)
    cli = next((r for r in rs if r["name"].startswith("MCP send tools/call")), None); srv = next((r for r in rs if r["name"].startswith("tools/call") and r["kind"] == "SERVER"), None)
    rows_.append({"escenario": e["etiqueta"], "execute_tool (agente)": e["error_type"] or "ok", "span CLIENTE": cli["status"] if cli else "—",
                  "span SERVIDOR": srv["status"] if srv else "—", "error.type servidor": srv["attributes"].get("error.type", "—") if srv else "—",
                  "espera del agente (ms)": round(e["espera_ms"], 1), "dur. servidor (ms)": round((srv["end_unix_nano"] - srv["start_unix_nano"]) / 1e6, 1) if srv else None,
                  "zombi (ms)": round(max((srv["end_unix_nano"] - cli["end_unix_nano"]) / 1e6, 0), 1) if srv and cli else None})
FT = pd.DataFrame(rows_).set_index("escenario"); display(FT)
''')
    code('''
fig, axes = plt.subplots(1, 2, figsize=(13, 3.8), gridspec_kw={"width_ratios": [1.1, 1]})
# (a) matriz de «qué span lo marca como error»
M = FT[["execute_tool (agente)", "span CLIENTE", "span SERVIDOR"]].map(lambda v: 0 if v in ("ok", "UNSET", "—") else 1)
axes[0].imshow(M.values, cmap="Reds", vmin=0, vmax=1.4, aspect="auto")
axes[0].set_xticks(range(3), ["execute_tool\\n(agente)", "span CLIENTE\\n(SDK)", "span SERVIDOR\\n(SDK)"]); axes[0].set_yticks(range(len(M)), M.index)
for i in range(M.shape[0]):
    for j in range(M.shape[1]): axes[0].text(j, i, "ERROR" if M.values[i, j] else "—", ha="center", va="center", fontsize=9, color="white" if M.values[i, j] else "#6b7280")
axes[0].set_title("¿Quién marca el error?"); axes[0].grid(False)
# (b) línea de tiempo del timeout
to = trace_rows(ESC[2]["tid"], wait=0); t0_ = min(r["start_unix_nano"] for r in to)
bars = [r for r in to if r["name"].startswith(("MCP send tools/call", "tools/call", "GET carrier"))]
for i, r in enumerate(bars):
    axes[1].barh(i, (r["end_unix_nano"] - r["start_unix_nano"]) / 1e6, left=(r["start_unix_nano"] - t0_) / 1e6, color=viz.PALETTE["error"] if r["status"] == "ERROR" else viz.PALETTE["logs"], height=0.6)
axes[1].set_yticks(range(len(bars)), [r["name"] + ("  (abandona)" if r["name"].startswith("MCP send") else "") for r in bars], fontsize=8); axes[1].invert_yaxis(); axes[1].set_xlabel("ms desde el inicio"); axes[1].set_title("Timeout: el cliente abandona, el servidor sigue")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Error de herramienta:** el span **servidor** sale `ERROR` con `error.type=tool_error`, pero el span **cliente** del SDK queda **sin error** (el mensaje JSON-RPC se entregó con éxito; el fallo viaja en el *resultado*). Solo el `execute_tool` del agente (que traduce `isError` a `ToolError`) lo marca. Si tu alerta mira solo los spans CLIENT de MCP, **no verá los fallos de herramienta**.
    - **Timeout:** el span cliente sale `ERROR`; el servidor termina **más tarde** con éxito: ese intervalo es el **trabajo zombi**. El SDK envía una notificación de cancelación de cortesía, pero la herramienta es una función síncrona en un hilo y **no se interrumpe**.
    - **Herramienta desconocida:** en el SDK v2 se devuelve como `isError` (no como error JSON-RPC `-32602`): en la práctica se comporta como un error de herramienta; no verás `rpc.response.status_code`.
    - El diagnóstico exige **cruzar los tres spans**: ninguno cuenta la historia completa por sí solo.
    """))

    # ------------------------------------------------------------------------------------------------------------- 8
    md("""
    ---
    # 8 · Reintentos de herramientas destructivas: idempotencia y auditoría

    El zombi de la sección anterior se vuelve peligroso con `issue_refund`: si el cliente se rinde y **reintenta**, el servidor puede haber ejecutado ya el primer reembolso. La defensa clásica es una **clave de idempotencia**: el servidor recuerda el resultado de cada clave y no repite el efecto. El servidor de pedidos la soporta (`idempotency_key`) y `register_tools` la añade de forma automática (hash estable de nombre + argumentos).

    Comparamos reintentar un reembolso **sin** y **con** clave, con un primer intento que vence (plazo de 1 ms) y un reintento que funciona:
    """)
    code('''
elig = next(o for o in catalog.orders().values() if o["status"] == "delivered" and (o["delivered_days_ago"] or 99) <= 30)
pay = {"order_id": elig["order_id"], "amount_eur": elig["total_eur"], "reason": "prueba de idempotencia"}
applied = lambda: BR.call("refund_stats")["applied"]

def intento(args, timeout):
    try: return BR.call("issue_refund", args, timeout_s=timeout)
    except ToolError as e: return {"error": e.error_type}

res_ = {}
for etiqueta, key in (("sin clave", None), ("con idempotency_key", "demo-key-1")):
    base = applied(); a = {**pay, **({"idempotency_key": key} if key else {})}
    r1 = intento(a, 0.001); time.sleep(0.4)                    # 1.er intento: el cliente se rinde, el servidor lo ejecuta igualmente
    r2 = intento(a, 3.0)                                       # reintento
    res_[etiqueta] = {"solicitados (1.º + reintento)": 2, "EJECUTADOS en el servidor": applied() - base, "1.er intento": r1.get("error", "ok"), "reintento": "deduplicado" if r2.get("deduplicated") else "ejecutado de nuevo"}
display(pd.DataFrame(res_).T)
fig, ax = plt.subplots(figsize=(6.4, 3.4))
ax.bar(list(res_), [v["EJECUTADOS en el servidor"] for v in res_.values()], color=[viz.PALETTE["error"], viz.PALETTE["logs"]]); ax.axhline(1, color="k", ls=":")
ax.set_ylabel("reembolsos ejecutados (debería ser 1)"); ax.set_title("Un reintento sin idempotencia duplica el reembolso"); plt.show()
''')
    code('''
time.sleep(0.3)
aud = [(r["resource"]["service.name"], e["attributes"]) for r in SP.spans() if r["name"] == "tools/call issue_refund" for e in r["events"] if e["name"] == "supportops.audit"]
display(pd.DataFrame([a for _, a in aud]).tail(6))
''')
    md(observe("""
    - Sin clave: **2 reembolsos** por una sola intención del cliente (el primer intento «falló» para el cliente pero el servidor lo ejecutó). Con clave: **1**, y el reintento se marca `deduplicated`.
    - La **auditoría** es un *evento de span* (`supportops.audit`) en el span servidor de la herramienta destructiva con `outcome`, `order_id` truncado e `idempotency_key` truncada: suficiente para reconstruir quién-hizo-qué sin guardar argumentos sensibles. Nótese que el 1.er intento (que el cliente consideró fallido) aparece como **`ok`** en el servidor: la prueba de que cliente y servidor discrepan.
    - Regla: *toda herramienta con `destructiveHint=true` debe ser idempotente por clave o no reintentarse nunca*; y la clave debe viajar en el span como atributo de baja sensibilidad para poder buscar duplicados.
    """))

    # ------------------------------------------------------------------------------------------------------------- 9
    md("""
    ---
    # 9 · Seguridad de las herramientas observables

    La telemetría de herramientas es un **canal nuevo de fuga** y una **superficie de ataque**. Cuatro controles, todos medibles:

    1. **No capturar argumentos ni resultados por defecto** (la spec los marca *opt-in* y sensibles) y, si se capturan, con **lista blanca por herramienta** y redacción de PII.
    2. **No confiar ciegamente en el `traceparent` entrante**: un cliente hostil puede forzar `sampled=01` en todas sus peticiones (coste de ingesta) o reutilizar `trace_id`s ajenos. Política `link`: la traza del servidor nace sola y **enlaza** al llamador.
    3. **Fijar la huella (*fingerprint*) de las herramientas**: la descripción de una herramienta es **texto que lee el modelo**; si un servidor la cambia entre conexiones (*rug pull*, *tool poisoning*) puede inyectar instrucciones.
    4. **Auditar las herramientas destructivas** (sección 8) y aplicar el mínimo privilegio (`readOnlyHint` coherente).
    """)
    md("### 9.1 Argumentos: lista blanca y redacción")
    code('''
casos = [("get_order", {"order_id": "ORD-00001"}),
         ("get_order", {"order_id": "ORD-00001 (mi correo: ana@example.com)"}),
         ("issue_refund", {"order_id": "ORD-00002", "amount_eur": 19.9, "reason": "tarjeta 4111 1111 1111 1111", "idempotency_key": "k"}),
         ("list_customer_orders", {"customer_id": "C-0001", "limit": 3})]
display(pd.DataFrame([{"herramienta": t, "argumentos reales": json.dumps(a, ensure_ascii=False), "lo que va a la telemetría": json.dumps(redact_args(t, a), ensure_ascii=False)} for t, a in casos]))
sp_c = McpServerProcess(telemetry="memory", capture_args=True)
with McpToolBridge(sp_c.params(), read_timeout_s=3.0) as b2:
    b2.call("issue_refund", {"order_id": "ORD-00002", "amount_eur": 19.9, "reason": "tarjeta 4111 1111 1111 1111", "idempotency_key": "k"})
    time.sleep(0.4)
print("atributo gen_ai.tool.call.arguments en el span SERVIDOR (capture_args=True):",
      [r["attributes"].get("gen_ai.tool.call.arguments") for r in sp_c.spans() if r["name"] == "tools/call issue_refund"])
''')
    md("### 9.2 Contexto remoto: confiar, enlazar o ignorar")
    code('''
sp_l = McpServerProcess(telemetry="memory", context_policy="link")
with McpToolBridge(sp_l.params(), read_timeout_s=3.0) as b3:
    with tracer.start_as_current_span("agente (cliente no confiable)") as sp_a:
        b3.call("get_order", {"order_id": "ORD-00001"})
    time.sleep(0.4)
srv_l = next(r for r in sp_l.spans() if r["name"] == "tools/call get_order")
print("política link -> trace_id del servidor == del llamador:", srv_l["trace_id"] == format(sp_a.get_span_context().trace_id, "032x"),
      "· padre:", srv_l["parent_span_id"], "· enlaces:", [(l["trace_id"][:8], l["attributes"]) for l in srv_l["links"]])
''')
    md("### 9.3 La huella de las herramientas: detectar un *rug pull*")
    code('''
def huella_y_descripcion(mode):
    sp_m = McpServerProcess(mode=mode, telemetry="memory")
    with McpToolBridge(sp_m.params(), read_timeout_s=3.0) as b:
        return b.fingerprint, next(t.description for t in b.tools_list if t.name == "get_order")
(fp_ok, d_ok), (fp_bad, d_bad) = huella_y_descripcion("normal"), huella_y_descripcion("poisoned")
print("huella normal  :", fp_ok, "\\nhuella alterada:", fp_bad, "· ¿iguales?", fp_ok == fp_bad)
print("\\ndescripción añadida por el servidor alterado:", d_bad[len(d_ok):].strip())
''')
    md(observe("""
    - **Argumentos:** solo `order_id`/`amount_eur` pasan a la telemetría; el `reason` (texto libre con una tarjeta) se enmascara **entero** porque no está en la lista blanca. La lista blanca es mejor que la lista negra de patrones: la PII que no previste no se cuela.
    - **Contexto remoto:** con la política `link` el span servidor **no** hereda el `trace_id` del cliente (no se le deja forzar la traza) pero conserva un **enlace** para poder saltar de uno a otro: confianza mínima sin perder correlación.
    - **Huella:** cualquier cambio en una descripción cambia la huella. Guarda la huella aprobada y **alerta** cuando difiera al conectar (`supportops.mcp.tools_hash` como atributo del span de conexión). La descripción alterada de este ejemplo pide enviar la conversación a una URL externa: un modelo ingenuo podría obedecerla; la telemetría no lo evita, pero **sí lo delata**.
    """))

    # ------------------------------------------------------------------------------------------------------------- 10
    md("""
    ---
    # 10 · Estado de las convenciones: spec frente al SDK (medido)

    Lanzamos un servidor **«solo SDK»** (sin nuestro middleware) y comprobamos qué atributos de la spec aparecen en cada span. Es la forma honesta de saber cuánto confiar en la instrumentación incluida, y cuánto añadir tú.
    """)
    code('''
sp_s = McpServerProcess(telemetry="memory", sdk_only=True)
with McpToolBridge(sp_s.params(), read_timeout_s=3.0) as b4:
    with tracer.start_as_current_span("execute_tool get_order") as sp_g:
        b4.call("get_order", {"order_id": "ORD-00001"})
    time.sleep(0.5)
tid_g = format(sp_g.get_span_context().trace_id, "032x")
cli = next(r for r in TEL.span_records() if r["trace_id"] == tid_g and r["kind"] == "CLIENT")
srv_sdk = next(r for r in sp_s.spans() if r["name"].startswith("tools/call"))
srv_ours = next(r for r in SP.spans() if r["name"] == "tools/call get_order")
exec_tool = next(r for r in TEL.span_records() if r["trace_id"] == tid_g and r["name"] == "execute_tool get_order")

SPEC = [("mcp.method.name", "requerido"), ("gen_ai.tool.name", "cond. (tools/call)"), ("gen_ai.operation.name", "recom. (execute_tool)"), ("jsonrpc.request.id", "cond. (cliente)"),
        ("mcp.protocol.version", "recomendado"), ("network.transport", "recomendado"), ("mcp.session.id", "recom. (si hay sesión)")]
cols = {"CLIENTE (SDK)": cli, "SERVIDOR (SDK)": srv_sdk, "SERVIDOR (+ nuestro middleware)": srv_ours}
Mx = pd.DataFrame({c: {a: int(a in s["attributes"]) for a, _ in SPEC} for c, s in cols.items()})
Mx.index = [f"{a}  [{n}]" for a, n in SPEC]
fig, ax = plt.subplots(figsize=(9.5, 4))
ax.imshow(Mx.values, cmap="Greens", vmin=0, vmax=1.3, aspect="auto"); ax.set_xticks(range(3), Mx.columns); ax.set_yticks(range(len(Mx)), Mx.index, fontsize=8.5)
for i in range(Mx.shape[0]):
    for j in range(3): ax.text(j, i, "✔" if Mx.values[i, j] else "✖", ha="center", va="center", color="white" if Mx.values[i, j] else "#d64545", fontsize=12)
ax.set_title("Atributos de la spec MCP presentes en cada span (medido)"); ax.grid(False); plt.tight_layout(); plt.show()
print("nombre del span CLIENTE:", repr(cli["name"]), "· spec: 'tools/call get_order'")
print("nombre del span SERVIDOR:", repr(srv_sdk["name"]), "· kind:", srv_sdk["kind"])
''')
    md(observe("""
    - El SDK ya cubre **lo esencial**: contexto por `_meta` (el span servidor es hijo del cliente), `mcp.method.name`, `gen_ai.tool.name`/`gen_ai.operation.name` en el servidor y `error.type=tool_error`.
    - Faltan, según lo medido: en el **cliente** `gen_ai.tool.name`, `gen_ai.operation.name`, `mcp.protocol.version` y `network.transport`; en el servidor `network.transport` (lo añade nuestro middleware); `mcp.session.id` no aparece con stdio (no hay sesión). El **nombre** del span cliente lleva el prefijo `MCP send` (distinto de la spec). El SDK tampoco emite las **métricas** `mcp.*.operation.duration`.
    - Y una diferencia de **semántica**, no solo de nombres: el SDK marca ERROR en el span servidor para *cualquier* `isError`, mientras que la spec dice que los fallos causados por el llamador (p. ej. herramienta inexistente, `-32602`) **no** deben contarse como errores del servidor. Tu tasa de error puede salir inflada por tráfico malformado.
    - Conclusión práctica: **fija la versión del SDK**, escribe una prueba que compruebe los atributos que tus dashboards usan (como esta celda) y completa lo que falta en tu código (`McpToolSpanEnricher`, middleware, métricas).
    """))
    md(box("warn", "Experimental", """
    Las convenciones MCP de OpenTelemetry están en estado **Development** y el registro de atributos `mcp.*` se ha movido al repositorio de convenciones GenAI. El SDK de Python v2 **evoluciona rápido** (al escribir este módulo había ya versiones 2.2 y 2.3 publicadas, y la API de middleware está marcada como provisional): no hardcodees nombres de span en alertas sin una prueba de contrato como la de arriba.
    """))

    # ------------------------------------------------------------------------------------------------------------- 11
    md("""
    ---
    # 11 · Métricas, dashboard y TraceQL (stack real)

    El servidor registra `mcp.server.operation.duration` (middleware) y el puente `mcp.client.operation.duration` (ambos histogramas en segundos con los *buckets* de la spec, atributos `mcp.method.name`, `gen_ai.tool.name`, `error.type`). El dashboard **«12 · MCP y herramientas remotas»** (`stack/grafana/dashboards/12-mcp-tools.json`, uid `mcp-tools`) reúne:

    | Panel | Consulta |
    |---|---|
    | p95 de la herramienta **cliente vs servidor** (la diferencia = overhead) | `histogram_quantile(0.95, sum by (le, gen_ai_tool_name) (rate(mcp_client_operation_duration_seconds_bucket[$__rate_interval])))` y la equivalente `mcp_server_...` |
    | Tasa de errores por herramienta y tipo | `sum by (gen_ai_tool_name, error_type) (rate(mcp_client_operation_duration_seconds_count{error_type!=""}[$__rate_interval]))` |
    | **Trazas partidas** (llamada MCP cuyo span cliente no cuelga del agente) | TraceQL `{ name =~ "MCP send tools/call.*" && nestedSetParent < 0 }` |
    | Trazas que cruzan agente → servidor | TraceQL `{ resource.service.name = "supportops-agent" } >> { resource.service.name = "supportops-orders-mcp" }` |
    | Llamadas MCP con error | TraceQL `{ resource.service.name = "supportops-orders-mcp" && status = error }` |
    """)
    code('''
if LIVE:
    SPL = McpServerProcess(telemetry="otlp", otlp_endpoint="http://localhost:4318", time_scale=0.02)
    with McpToolBridge(SPL.params(), read_timeout_s=3.0, meter=TEL.meter()) as BL:
        regL = default_tools(); namesL = BL.register_tools(regL, ["get_order", "track_shipment", "issue_refund"])
        llmL = MockLLM("mock-small"); llmL.add_rule(tracking_rule())
        agL = SupportAgent(llm=llmL, tools=regL, instrumentor=CompositeInstrumentor(WallClockInstrumentor(TEL), McpToolSpanEnricher(namesL)))
        for t in [t for t in pool if t.intent_true in ("order_status", "refund")][:30]:
            agL.run(dataclasses.replace(t, faults=[], created_at=time.time()))
        # 4 llamadas desde hilos SIN contexto (traza partida) y 2 timeouts, para que el dashboard tenga rojo
        with ThreadPoolExecutor(2) as ex: [f.result() for f in [ex.submit(BL.call, "get_order", {"order_id": f"ORD-{200 + i:05d}"}) for i in range(4)]]
        for _ in range(2):
            try: BL.call("track_shipment", {"order_id": "ORD-00017"}, timeout_s=0.05)
            except ToolError: pass
        time.sleep(1.0)
    TEL.force_flush(); print("telemetría enviada; espera ~20-30 s a que Tempo y Prometheus la indexen")
else:
    print("Sin stack: arráncalo con `docker compose --profile core --profile metrics up -d` (desde stack/) y vuelve a ejecutar.")
''')
    code('''
if LIVE:
    qs = {"cruzan agente→servidor": '{ resource.service.name = "supportops-agent" } >> { resource.service.name = "supportops-orders-mcp" }',
          "trazas partidas (cliente MCP sin padre)": '{ name =~ "MCP send tools/call.*" && nestedSetParent < 0 }',
          "llamadas MCP con error": '{ resource.service.name = "supportops-orders-mcp" && status = error }'}
    t_end = time.time() + 70; got = {}
    while time.time() < t_end:
        got = {k: backends.tempo_search(q, minutes=30, limit=50).get("traces", []) for k, q in qs.items()}
        if all(got.values()): break
        time.sleep(4)
    print({k: len(v) for k, v in got.items()})
    try:
        r = backends.prom_query('sum by (gen_ai_tool_name) (mcp_client_operation_duration_seconds_count)')
        display(pd.DataFrame([{**x["metric"], "llamadas": float(x["value"][1])} for x in r])[["gen_ai_tool_name", "llamadas"]])
    except Exception as e:
        print("Prometheus no disponible (¿perfil metrics?):", type(e).__name__)
''')
    md(observe("""
    - **Trazas partidas ≈ 4** (las llamadas desde hilos sin contexto) y **cruzan agente → servidor** el resto: la consulta de «partidas» es la prueba de salud permanente de esta integración.
    - `llamadas MCP con error` incluye los 503 (tool_error) y las llamadas lentas **canceladas**; los *timeouts* cuentan en la métrica del **cliente** (`error_type="timeout"`) pero el servidor sigue registrando la llamada como correcta: la discrepancia entre ambas métricas **es** la señal de zombi.
    - Abre Grafana → «12 · MCP y herramientas remotas»: compara el p95 del cliente y del servidor por herramienta; si el cliente sube y el servidor no, mira el transporte o el puente; si suben ambos, mira la dependencia.
    """))
    code('''
try: BR.close()
except Exception: pass
TEL.force_flush()
''')

    # ------------------------------------------------------------------------------------------------------------- prod
    md("""
    ---
    # 🏭 En producción

    - **Dónde viven los servidores MCP**: con *stdio* el servidor es un proceso hijo del host (su vida está atada a la del agente: si el agente muere, mueren sus spans pendientes; vacía el exportador al cerrar). Con *Streamable HTTP* es un servicio remoto con su propio despliegue, autenticación y escalado: aquí los spans del servidor los exporta **él** al Collector y la correlación depende por completo de `_meta`.
    - **Pasarelas (*MCP gateways*) y registros** añaden saltos: cada uno debe propagar `_meta` (o enlazar). Un salto que no lo haga parte la traza justo ahí; la consulta TraceQL de «servidor sin padre» te lo localiza.
    - **Qué miden los equipos que operan agentes con herramientas remotas** (Elastic Observability Labs, entre otros, publica guías de trazado MCP con OpenTelemetry): latencia por herramienta (cliente y servidor), tasa de errores por tipo, tasa de *timeouts*, cardinalidad controlada del nombre de herramienta y trazas completas agente→servidor→dependencia. Compara siempre las guías con la spec: varios blogs usan nombres de span distintos a los de las convenciones oficiales.
    - **Costes:** cada salto añade spans (≈ ×2 por llamada: cliente y servidor) y, si capturas argumentos/resultados, bytes. Con muestreo por cola (módulo 18) decide por traza completa, no por servicio.
    """)

    md(box("elite", "", """
    1. **Dos spans por salto, y un tercero del agente.** `execute_tool` (agente), `MCP send tools/call` (cliente SDK) y `tools/call` (servidor) describen la **misma** llamada. La spec dice que el span MCP es *compatible* con `execute_tool`: elige **uno** como «la herramienta» para latencia y errores y usa los otros para **descomponer** (overhead = cliente − servidor). Si sumas los tres, tus gráficas de latencia de herramientas están inflados ×2–3.
    2. **`isError` no es un error de protocolo.** Un fallo de herramienta viaja como resultado «exitoso» con `isError: true`; el span cliente del SDK sale **sin error**. Mide los fallos en el servidor (`error.type=tool_error`) **y** en el `execute_tool` del agente; una alerta basada solo en spans CLIENT de MCP es ciega a ellos (sección 7, medido).
    3. **El timeout no cancela.** El SDK envía una notificación de cancelación de cortesía, pero una herramienta síncrona (hilo) no se interrumpe: el servidor completa el trabajo (y el efecto) **después** de que el cliente abandonó. La notificación llega además como un span raíz huérfano `notifications/cancelled`: ruido que conviene filtrar o enlazar.
    4. **Idempotencia antes que reintentos.** Para `destructiveHint=true`, reintenta solo con clave de idempotencia y registra la clave en el span del servidor. Sin ella, «reintentar» es duplicar el efecto (sección 8: 2 reembolsos por 1 intención).
    5. **La spec no cuenta como error lo que causó el llamador** (`-32602`, herramienta inexistente…), pero el SDK marca ERROR en el span servidor para todo `isError`. Si quieres una SLI de disponibilidad del servidor honesta, **clasifica** (tool_error del dominio frente a petición inválida) en tu middleware.
    6. **`traceparent` en `_meta` es entrada no confiable.** Un cliente hostil puede forzar el bit `sampled` (coste de ingesta) o reutilizar `trace_id`s. Para servidores expuestos usa la política `link` (traza propia + enlace). Además `baggage` en `_meta` viaja a todos los servicios: lista blanca de claves.
    7. **La descripción de una herramienta es un prompt.** Fija y vigila su huella: un servidor puede cambiarla entre conexiones (*rug pull*) e inyectar instrucciones; el cambio de huella es **una señal observable y barata** (atributo en el span de conexión + alerta). *Fuente del ataque: Invariant Labs, «MCP Security Notification: Tool Poisoning Attacks» (1-abr-2025): una descripción envenenada de una herramienta «calculadora» hizo que el agente leyera una clave SSH y la configuración MCP del usuario, que solo veía un resumen inocuo; el modelo ve la descripción, el humano normalmente no.*
    8. **La spec aún se mueve y el SDK va por delante o por detrás.** Los nombres `mcp.*` están en *Development*; el SDK usa `MCP send …` como nombre de cliente; hay versiones 2.x frecuentes y el middleware es API provisional. Una prueba de contrato (atributos que tus paneles necesitan) es la única defensa fiable.
    9. **Las claves `traceparent`/`tracestate`/`baggage` de `_meta` van SIN prefijo a propósito.** MCP exige prefijos DNS para claves propias de `_meta`, y SEP-414 documenta una excepción deliberada: prefijarlas (`io.modelcontextprotocol.traceparent`) rompería la correlación traza-log de todos los ecosistemas que ya inyectan el nombre estándar. Consecuencia práctica: un propagador «creativo» que prefije la clave produce trazas partidas **sin error alguno** (como la cabecera con otra capitalización, módulo 03); la prueba de contrato debe inyectar y extraer por la misma clave exacta. *Fuente: SEP-414 (estado Final, autor Adrian Cole, 25-abr-2025; la página es registro histórico: manda la especificación vigente).*
    10. **Compara siempre contra la spec de MCP de OpenTelemetry, no contra un blog.** La página oficial recomienda seguir las convenciones MCP en lugar de las de RPC, define `mcp.method.name`/`gen_ai.tool.name`/`error.type` y propone `_meta` para propagar; los nombres de span varían entre blogs y SDK (`MCP send tools/call` frente a `tools/call echo`). Mide tu desviación: un contrato de telemetría que falle la CI cuando falte `mcp.method.name` en un span `tools/call` cuesta una línea y evita paneles vacíos tras actualizar el SDK. *Fuente: opentelemetry.io/docs/specs/semconv/gen-ai/mcp (Development).*
    """))

    md(box("warn", "Errores comunes", """
    - **Mezclar relojes:** instrumentar el agente con el reloj simulado y el SDK de MCP con el de pared ⇒ spans hijos fuera del padre. Usa un solo reloj.
    - **Llamar a herramientas desde `ThreadPoolExecutor` sin `copy_context()`** (sección 6).
    - **Confiar en que «no hay excepción» = «herramienta correcta»:** `isError`.
    - **Capturar `gen_ai.tool.call.arguments`/`result` «para depurar»** y dejarlo activo en producción: PII y datos de negocio en Tempo durante 24 h (o meses).
    - **Un nombre de herramienta con alta cardinalidad** (p. ej. herramientas generadas dinámicamente con un id) como etiqueta de métrica.
    - **No cerrar el servidor/exportador** (los lotes pendientes se pierden) y **no vigilar el arranque**: los spans `server/discover` y `tools/list` de cada conexión crean trazas de un solo span si no hay span activo.
    - **Fiarse de las anotaciones** (`readOnlyHint`…) como control de seguridad: las declara el servidor.
    """))

    # ------------------------------------------------------------------------------------------------------------- autoeval
    md("""
    ---
    # Autoevaluación
    """)
    md(details("1 · (Cálculo) Mides con el span cliente una mediana de 14 ms y con el servidor 9 ms para `get_order`; la dependencia (BD) ocupa 6 ms. ¿Cuánto es el overhead de transporte y qué porcentaje del tiempo del cliente es lógica propia del servidor?",
               "Overhead = 14 − 9 = **5 ms** (36 % del cliente). Lógica propia del servidor = 9 − 6 = **3 ms** (21 %); dependencia 6 ms (43 %). Si el overhead sube a 40 ms mientras el servidor sigue en 9 ms, el problema está en el transporte/puente, no en la herramienta."))
    md(details("2 · (Cálculo) Un agente hace 5 llamadas MCP por ticket y procesa 200 tickets/min. Si cada llamada genera 3 spans (execute_tool, cliente, servidor) y 1 de dependencia, ¿cuántos spans por minuto produce solo la capa MCP? ¿Y si capturas argumentos (+250 B por span servidor) con retención de 24 h?",
               "Spans/min = 200 × 5 × 4 = **4 000**. Si 1 000 de ellos son spans servidor con 250 B extra: 1 000 × 250 B = 250 kB/min ≈ **360 MB/día** extra solo por argumentos (sin contar el coste de cumplimiento por PII). Conclusión: la captura de argumentos es una decisión de presupuesto y de privacidad, no un detalle de depuración."))
    md(details("3 · (Diagnóstico) El panel «llamadas MCP con error» está a cero, pero los agentes devuelven respuestas degradadas («no puedo consultar el transportista»). ¿Qué ocurre y qué miras?",
               "Los fallos son `isError` (503 del transportista): el span cliente del SDK no marca error y, si el panel solo cuenta spans CLIENT, no los ve. Mira el span **servidor** (`error.type=tool_error`, `status=ERROR`), el span `execute_tool` del agente (`error.type`) y la métrica `mcp.server.operation.duration{error_type!=\"\"}`."))
    md(details("4 · (Diagnóstico) En Tempo hay trazas del agente sin spans de servidor y, aparte, trazas de 3 spans (`tools/call`, `SELECT`…) sin padre cuyo número coincide con las llamadas fallidas del agente. ¿Causa y arreglo?",
               "Contexto perdido entre el agente y el cliente MCP (llamadas desde hilos de un *executor* sin copiar `contextvars`, o un cliente no instrumentado): cada lado abre su traza. Arreglo: `executor.submit(contextvars.copy_context().run, ...)` o instrumentar/inyectar `traceparent` en `_meta` (parámetro `meta=` del cliente). Detector: TraceQL de cliente MCP raíz `{ name =~ \"MCP send tools/call.*\" && nestedSetParent < 0 }`."))
    md(details("5 · (Transferencia) Diseñas un servidor MCP de «tickets de Jira» para un agente de ingeniería. ¿Qué herramientas auditarías, qué argumentos permitirías en la telemetría y qué política de contexto pondrías si lo expones a clientes de terceros?",
               "Auditar `create_issue`, `transition_issue`, `delete_comment` (destructivas/escritura) con evento de auditoría + clave de idempotencia; lista blanca de argumentos: `project_key`, `issue_type`, id del issue (nunca título/descripción: texto libre con PII y secretos); política de contexto `link` para terceros (no confiar en su `traceparent`) y `trust` solo para clientes internos autenticados; huella de herramientas y alerta ante cambio."))
    md(details("6 · (Recuerdo) ¿Por qué la spec recomienda propagar el contexto en `params._meta` y no solo con cabeceras HTTP?",
               "Porque MCP es independiente del transporte (stdio no tiene cabeceras) y porque el contexto HTTP solo cubre la petición HTTP, no los mensajes individuales que circulan dentro de ella: una petición HTTP puede llevar varios mensajes MCP. `_meta` garantiza un padre por mensaje con cualquier transporte (SEP-414)."))
    md(details("7 · (Transferencia) Un cliente no cancela las peticiones al vencer su plazo. ¿Qué tres medidas de observabilidad/diseño detectarían o evitarían el trabajo zombi en el servidor?",
               "(1) Medir **cliente vs servidor** (`mcp.client/server.operation.duration`): spans servidor que terminan después del cliente. (2) Propagar un **deadline** (como en el módulo 11) y comprobarlo en el servidor antes de cada dependencia. (3) Herramientas cancelables (asíncronas) y operaciones destructivas **idempotentes**. Opcional: alertar por `servidor_fin − cliente_fin > 0` sostenido."))

    md("""
    ---
    # Referencias

    - Model Context Protocol, *Specification* (transportes, `_meta`, herramientas) y **SEP-414** *Document OpenTelemetry Trace Context Propagation Conventions* — <https://modelcontextprotocol.io/seps/414-request-meta>
    - OpenTelemetry, *Semantic conventions for Model Context Protocol (MCP)* (estado Development) — <https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/> · fuente: <https://github.com/open-telemetry/semantic-conventions-genai> (`docs/gen-ai/mcp.md`).
    - OpenTelemetry, *GenAI semantic conventions: `execute_tool`* (agent spans) — mismo repositorio, `docs/gen-ai/gen-ai-agent-spans.md`.
    - SDK de Python de MCP (`modelcontextprotocol/python-sdk`, v2: `MCPServer`, `Client`, middleware de servidor) — <https://github.com/modelcontextprotocol/python-sdk>
    - W3C, *Trace Context* y *Baggage* — <https://www.w3.org/TR/trace-context/> · <https://www.w3.org/TR/baggage/>
    - Invariant Labs, *MCP Security Notification: Tool Poisoning Attacks* (abril de 2025) — <https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks> (el ataque de envenenamiento de descripciones; la variante *rug pull* se describe en varios análisis posteriores).
    - Rengifo, J. (Elastic Observability Labs), *How to trace MCP server tool calls with OpenTelemetry and Elastic APM* (el enlace conserva el *slug* `mcp-tracing-opentelemetry-elastic-apm`; ejemplo de `tools/call echo` con `mcp.method.name`; el título exacto se confirmó por búsqueda web) — <https://www.elastic.co/observability-labs/blog/mcp-tracing-opentelemetry-elastic-apm>
    - Grafana Labs, *TraceQL* (`nestedSetParent`, selectores y `>>`) — <https://grafana.com/docs/tempo/latest/traceql/>
    """)

    nb.save(out)


# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "12_proyecto_mcp_tools.ipynb", "Proyecto 12 · Instrumentar el servidor MCP de pedidos y unir su traza con la del agente")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 12 · Instrumentar el servidor MCP de pedidos y unir su traza con la del agente

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (todo se evalúa en memoria; lanza un proceso hijo por stdio). Opcional: `core` + `metrics` para el paso final |
    | **RAM aproximada** | < 700 MB |
    | **Prerrequisitos** | Lección `12_mcp_tools` y módulo 11 (propagación de contexto, resiliencia) |
    | **Conexión** | Sustituye las herramientas locales de SupportOps por un servidor MCP **observable y seguro**; el módulo 13 usará estas trazas para atribuir el coste |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. El equipo de pedidos ha expuesto sus herramientas como un **servidor MCP** y el agente ya las usa. Tras una semana en producción hay quejas:

    1. **Hay trazas del servidor que nadie sabe a qué ticket pertenecen** (el *dashboard* de trazas partidas se llena cuando el agente paraleliza herramientas).
    2. **Un reembolso se pagó dos veces** tras un *timeout*.
    3. **Seguridad pide** que la telemetría no guarde datos personales, que el servidor no obedezca contextos ajenos y que se **detecte** si alguien cambia las descripciones de las herramientas.
    4. **Observabilidad pide** un contrato: que los atributos de la spec MCP que usan los paneles estén de verdad en los spans.

    ## Datos

    Todo sintético y determinista (semilla 42, `mock`). El **Paso 0** lanza el servidor MCP de pedidos como proceso hijo y ejecuta 10 tickets reales del agente más 6 llamadas desde hilos sin contexto; te entrega `AGENT_ROWS` y `SERVER_ROWS` (spans de los dos procesos, esquema `SPAN_SCHEMA`). Cadena de datos: stack local (opcional) → memoria + JSONL.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `safe_args` | 8 vectores: lista blanca por herramienta, PII enmascarada en valores permitidos, resto `<redacted>` | 8/8 |
    | R2 | `ToolPolicyMiddleware` | Sobre un servidor en proceso: atributos de herramienta, evento de **auditoría** solo en destructivas, histograma `mcp.server.operation.duration` por herramienta/error, clase de error `caller`/`server`, sin argumentos capturados | 6/6 comprobaciones |
    | R3 | `join_report` | Llamadas de servidor, **unidas** al agente, **huérfanas** y mediana de *overhead* cliente−servidor | contadores exactos · overhead entre 0 y 100 ms |
    | R4 | `safe_call` | 4 escenarios: OK (1 intento), lectura lenta (2 intentos, `timeout`), `tool_error` (1 intento, sin reintento), reembolso con *timeout* (2 intentos, **1** ejecución real) | 4/4 |
    | R5 | `tools_digest`, `detect_drift` | Estable ante reordenación, sensible a cualquier cambio de descripción; detecta el servidor alterado | 5/5 |
    | R6 | `spec_gaps` | Sobre 3 spans sintéticos: lista exacta de atributos de la spec que faltan por nivel; y el span servidor real **no** pierde ninguno requerido | exacto |

    > 📏 Los umbrales salen de la solución de referencia (semilla 42, fija en el notebook; con otra semilla cambian los tickets y, por tanto, los contadores del R3). Las latencias son de pared (compresión ×50), por eso solo se exigen **rangos amplios** y relaciones (cliente ≥ servidor), no valores absolutos.
    """)

    code(boot("viz,otel"))
    code(PIP_MCP)
    code(IMPORTS + IMPORTS_12.replace('TEL = setup_telemetry("supportops-agent", mode="otlp" if LIVE else "memory", resource_attrs={"deployment.environment.name": "lab"})',
                                      'TEL = setup_telemetry("supportops-agent", mode="memory")        # en memoria: la rúbrica no depende del stack') + '''
import hashlib, re
from mcp import Client
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from supportops.mcp_orders import MCP_BUCKETS
''')

    md("""
    ## Paso 0 · El sistema de partida (te lo damos hecho)

    Lanza el servidor MCP de pedidos como proceso hijo (con **nuestra** telemetría de servidor ya activa para que puedas inspeccionarla), conecta el puente, ejecuta 10 tickets del agente y 6 llamadas **desde hilos sin copiar el contexto** (el origen del problema 1).
    """)
    code('''
SP = McpServerProcess(time_scale=0.02)
BR = McpToolBridge(SP.params(), read_timeout_s=3.0, meter=TEL.meter())
registry = default_tools(); remote = BR.register_tools(registry, ["get_order", "track_shipment", "issue_refund"])
llm = MockLLM("mock-small"); llm.add_rule(tracking_rule())
agent = SupportAgent(llm=llm, tools=registry, instrumentor=CompositeInstrumentor(WallClockInstrumentor(TEL), McpToolSpanEnricher(remote)))
pool = [t for t in generate_tickets(120, seed=SEED) if t.intent_true in ("order_status", "refund")][:10]
for t in pool: agent.run(dataclasses.replace(t, faults=[], created_at=time.time()))
with tracer_ctx() if False else TEL.tracer().start_as_current_span("job-batch (hilos sin contexto)") as _sp, ThreadPoolExecutor(2) as ex:
    [f.result() for f in [ex.submit(BR.call, "get_order", {"order_id": f"ORD-{300 + i:05d}"}) for i in range(6)]]
time.sleep(0.8)
AGENT_ROWS, SERVER_ROWS = TEL.span_records(), SP.spans()
print(f"agente: {len(AGENT_ROWS)} spans · servidor MCP: {len(SERVER_ROWS)} spans · tools/call en el servidor: {sum(r['name'].startswith('tools/call') for r in SERVER_ROWS)}")
display(pd.DataFrame([{"span": r["name"], "servicio": r["resource"]["service.name"].replace("supportops-", ""), "kind": r["kind"]} for r in (AGENT_ROWS[:3] + SERVER_ROWS[:3])]))
'''.replace("with tracer_ctx() if False else TEL.tracer()", "with TEL.tracer()"))

    # ---------------------------------------------------------------------------------- paso 1
    md("""
    ## Paso 1 · Telemetría que no filtra datos personales

    **TODO 1.** `safe_args(tool, args)` devuelve los argumentos **aptos para telemetría**:

    - Solo las claves de la **lista blanca** de la herramienta (`ALLOW`) conservan su valor; **cualquier otra** clave pasa a `"<redacted>"` (aunque sea un número).
    - En los valores **de texto permitidos** hay que enmascarar PII con los patrones `PII` (correo → `<email>`, tarjeta de 13-19 dígitos → `<tarjeta>`).
    - Herramientas sin entrada en `ALLOW`: todo `<redacted>`. No debe mutar el diccionario de entrada.
    """)
    md(hint(1, "Recorre `args.items()`: si la clave no está en `ALLOW.get(tool, set())` → `\"<redacted>\"`. Si el valor es `str`, aplica cada `(patrón, sustituto)` de `PII` con `patrón.sub(sustituto, valor)`."))
    code('''
ALLOW = {"get_order": {"order_id"}, "list_customer_orders": {"limit"}, "check_stock": {"sku"}, "track_shipment": {"order_id"}, "issue_refund": {"order_id", "amount_eur"}}
PII = [(re.compile(r"[\\w.+-]+@[\\w-]+\\.[\\w.-]+"), "<email>"), (re.compile(r"\\b(?:\\d[ -]?){13,19}\\b"), "<tarjeta>")]

def safe_args(tool: str, args: dict) -> dict:
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    print(safe_args("issue_refund", {"order_id": "ORD-00002 ana@example.com", "amount_eur": 9.5, "reason": "tarjeta 4111 1111 1111 1111"}))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 2
    md("""
    ## Paso 2 · Middleware de política y auditoría del servidor

    El servidor se construye con `build_server("normal", telemetry=False, meter=...)`: solo trae la instrumentación del SDK. **TODO 2.** Completa `ToolPolicyMiddleware.__call__(ctx, call_next)` para `tools/call` (el resto de mensajes pasan intactos):

    1. Atributos en el **span actual** (`otel_trace.get_current_span()`): `supportops.tool.read_only` y `supportops.tool.destructive` (bool, de `TOOL_META`; si la herramienta no está en la tabla, ambos `False`) y `network.transport="pipe"`.
    2. Tras llamar a `call_next`: el resultado llega al middleware en **forma de cable**, un `dict` (`{"content": [{"text": ...}], "isError": true|ausente, ...}`). Si es de error (`result.get("isError")`), el tipo de error es `"tool_error"` **y** pon el atributo `supportops.error.class`: `"caller"` si el texto del resultado (unión de los `text` de `content`) empieza por `Unknown tool` o contiene `validation error`, si no `"server"`.
    3. **Herramientas destructivas** (`TOOL_META[tool]["destructive"]`): añade **siempre** (también si falla) un evento de span `supportops.audit` con `{"tool", "outcome": "ok"|"error", "order_id": <primeros 16 caracteres del argumento order_id o "">}`.
    4. **Métrica** `mcp.server.operation.duration` (`self.hist.record(segundos, atributos)`) con `mcp.method.name="tools/call"`, `gen_ai.tool.name`, `gen_ai.operation.name="execute_tool"` y `error.type` **solo si hubo error**.
    5. **No** captures argumentos como atributos.
    """)
    md(hint(1, "Estructura: lee `name = ctx.params['name']`, `args = ctx.params.get('arguments') or {}`; marca `t0 = time.perf_counter()`; `err = None`; `try: result = await call_next(ctx) ... finally:` registra evento y métrica. Recuerda `return result` y que una excepción debe **relanzarse**."))
    md(hint(2, "Texto del resultado: `\"\".join(c.get('text', '') for c in result['content'])`. El evento: `span.add_event('supportops.audit', {...})` dentro del `finally` para que se registre aunque haya fallo."))
    code('''
class ToolPolicyMiddleware:
    def __init__(self, meter):
        self.hist = meter.create_histogram("mcp.server.operation.duration", unit="s", explicit_bucket_boundaries_advisory=MCP_BUCKETS)

    async def __call__(self, ctx, call_next):
        # TODO 2
        raise NotImplementedError("TODO 2")

try:
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import InMemoryMetricReader
    _r = InMemoryMetricReader(); _srv = build_server("normal", telemetry=False); _srv.middleware.append(ToolPolicyMiddleware(MeterProvider(metric_readers=[_r]).get_meter("t")))
    async def _go():
        async with Client(_srv) as c: return (await c.call_tool("get_order", {"order_id": "ORD-00001"})).is_error
    print("llamada de prueba, is_error =", run_async(_go()))
except NotImplementedError as e:
    print("Pendiente:", e)
except Exception as e:
    print("Pendiente (aún falla):", type(e).__name__, str(e)[:80])
''')

    # ---------------------------------------------------------------------------------- paso 3
    md("""
    ## Paso 3 · Unir las trazas: informe de cobertura

    **TODO 3.** `join_report(agent_rows, server_rows)` devuelve un `dict`:

    - `tool_calls`: nº de spans del servidor cuyo nombre empieza por `tools/call`.
    - `joined`: cuántos de ellos pertenecen a una traza que **también contiene un span `invoke_agent`** del agente.
    - `orphans`: `tool_calls − joined`.
    - `overhead_ms_median`: mediana (ms, `float`) de `duración del span CLIENTE padre − duración del span servidor` sobre las llamadas **unidas** (el padre del span servidor es el span `MCP send tools/call …` de `agent_rows`). Si no hay ninguna unida, `None`.
    - `by_tool`: `dict` con el nº de llamadas por `gen_ai.tool.name`.
    """)
    md(hint(1, "Conjunto de trazas con agente: `{r['trace_id'] for r in agent_rows if r['name'].startswith('invoke_agent')}`. Índice de spans del agente por `span_id` para buscar el CLIENTE padre."))
    code('''
def join_report(agent_rows: list[dict], server_rows: list[dict]) -> dict:
    # TODO 3
    raise NotImplementedError("TODO 3")

try:
    print(join_report(AGENT_ROWS, SERVER_ROWS))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 4
    md("""
    ## Paso 4 · Llamar con política: timeouts, reintentos e idempotencia

    **TODO 4.** `safe_call(bridge, name, args, timeout_s, retries=1, backoff_s=0.05)` envuelve `bridge.call` y devuelve `{"ok", "value", "error_type", "attempts"}`:

    - `ToolError` con `error_type` **`timeout`** o **`connection_closed`** → se **reintenta** hasta `retries` veces, esperando `backoff_s` antes de cada reintento, **solo si es seguro**: la herramienta es de **solo lectura** (`TOOL_META[name]["read_only"]`) **o** es destructiva y los `args` llevan `idempotency_key` (si falta, **añádela tú** de forma estable: los primeros 16 hex de `sha256` del JSON de `[name, args]` con claves ordenadas, **antes** del primer intento).
    - `tool_error` y `protocol_error` **nunca** se reintentan.
    - `ok=True` y `value` con el resultado si algún intento funciona; si no, `ok=False`, `value=None` y el `error_type` del último fallo.
    """)
    md(hint(1, "Bucle `for attempt in range(1, retries + 2)`: `try: return {..., 'attempts': attempt}` / `except ToolError as e:` decide si reintentar (`e.error_type in ('timeout', 'connection_closed')` y `safe`) con `time.sleep(backoff_s)`."))
    md(hint(2, "Para las destructivas, calcula la clave **una vez antes del bucle**: `hashlib.sha256(json.dumps([name, args], sort_keys=True).encode()).hexdigest()[:16]` y haz `args = {**args, 'idempotency_key': key}` si no estaba."))
    code('''
def safe_call(bridge, name: str, args: dict, timeout_s: float, retries: int = 1, backoff_s: float = 0.05) -> dict:
    # TODO 4
    raise NotImplementedError("TODO 4")

try:
    print(safe_call(BR, "get_order", {"order_id": "ORD-00001"}, 3.0))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 5
    md("""
    ## Paso 5 · Vigilar las herramientas: huella y deriva

    **TODO 5.** (a) `tools_digest(tools)`: SHA-256 (primeros 16 hex) de las herramientas del servidor (`tools` = lista de objetos con `.name`, `.description` y `.input_schema`): debe ser **independiente del orden** y cambiar con **cualquier** cambio de nombre, descripción o esquema. (b) `detect_drift(approved, tools)` devuelve un `dict` `{"drifted": bool, "added": [...], "removed": [...], "changed": [...]}` comparando la lista **aprobada** (`dict` nombre → huella por herramienta, que genera `per_tool_digest`) con la actual; `changed` = herramientas que existen en ambas con huella distinta.
    """)
    md(hint(1, "Serializa cada herramienta como `[name, description or '', input_schema or {}]` con `json.dumps(..., sort_keys=True)`, ordena la lista por nombre y haz el SHA-256 del conjunto. `per_tool_digest` es lo mismo pero por herramienta."))
    code('''
def per_tool_digest(tools) -> dict:
    return {t.name: hashlib.sha256(json.dumps([t.name, t.description or "", getattr(t, "input_schema", None) or {}], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16] for t in tools}

def tools_digest(tools) -> str:
    # TODO 5a
    raise NotImplementedError("TODO 5a")

def detect_drift(approved: dict, tools) -> dict:
    # TODO 5b
    raise NotImplementedError("TODO 5b")

try:
    print(tools_digest(BR.tools_list), detect_drift(per_tool_digest(BR.tools_list), BR.tools_list))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 6
    md("""
    ## Paso 6 · Un contrato de conformidad con la spec

    **TODO 6.** `spec_gaps(span_row, kind)` devuelve `{"required": [...], "conditional": [...], "recommended": [...]}` con los atributos de `SPEC[kind]` (`kind` = `"client"` o `"server"`) que **faltan** en `span_row["attributes"]` (listas ordenadas alfabéticamente). Solo aplica a spans de `tools/call`. Úsala como **prueba de contrato** para un servidor real: `spec_gaps(<span servidor>, "server")["required"]` debe estar vacío.
    """)
    md(hint(1, "Es una **diferencia de conjuntos** por nivel: para cada nivel (`required`, `conditional`, `recommended`), los nombres de `SPEC[kind][nivel]` que **no** están en `span_row[\"attributes\"]`. Devuelve listas ordenadas. Es la misma idea que un test de contrato con un esquema: «¿qué campos esperados faltan?»."))

    code('''
SPEC = {"client": {"required": ["mcp.method.name"], "conditional": ["gen_ai.tool.name", "jsonrpc.request.id"], "recommended": ["gen_ai.operation.name", "mcp.protocol.version", "network.transport"]},
        "server": {"required": ["mcp.method.name"], "conditional": ["gen_ai.tool.name"], "recommended": ["gen_ai.operation.name", "mcp.protocol.version", "network.transport"]}}

def spec_gaps(span_row: dict, kind: str) -> dict:
    # TODO 6
    raise NotImplementedError("TODO 6")

try:
    sv_ = next(r for r in SERVER_ROWS if r["name"].startswith("tools/call"))
    print(spec_gaps(sv_, "server"))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- rúbrica
    md("""
    ## Paso 7 · Rúbrica
    """)
    code('''
REF = {"tool_calls": 20, "joined": 14, "orphans": 6, "by_tool": {"get_order": 16, "issue_refund": 1, "track_shipment": 3}}     # calibrado con la solución (semilla 42)

def run_rubric():
    rows = []
    def add(r, d, ok, det=""): rows.append({"criterio": r, "descripción": d, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": det})
    # R1
    try:
        V = [(("get_order", {"order_id": "ORD-00001"}), {"order_id": "ORD-00001"}),
             (("get_order", {"order_id": "ORD-00001 ana@example.com"}), {"order_id": "ORD-00001 <email>"}),
             (("issue_refund", {"order_id": "ORD-00002", "amount_eur": 9.5, "reason": "x", "idempotency_key": "k"}), {"order_id": "ORD-00002", "amount_eur": 9.5, "reason": "<redacted>", "idempotency_key": "<redacted>"}),
             (("issue_refund", {"order_id": "pago 4111 1111 1111 1111"}), {"order_id": "pago <tarjeta>"}),
             (("check_stock", {"sku": "SKU-1001", "extra": 5}), {"sku": "SKU-1001", "extra": "<redacted>"}),
             (("list_customer_orders", {"customer_id": "C-0001", "limit": 3}), {"customer_id": "<redacted>", "limit": 3}),
             (("desconocida", {"x": 1, "y": "z"}), {"x": "<redacted>", "y": "<redacted>"}),
             (("get_order", {}), {})]
        orig = {"order_id": "ORD-00001 ana@example.com"}; keep = dict(orig); safe_args("get_order", orig)
        n = sum(safe_args(*a) == e for a, e in V) + (0 if orig != keep else 0)
        ok = n == 8 and orig == keep
        add("R1", "safe_args: 8 vectores y sin mutar la entrada", ok, f"{n}/8 · entrada intacta: {orig == keep}")
    except Exception as e: add("R1", "safe_args", False, f"{type(e).__name__}: {e}")
    # R2
    try:
        rd = InMemoryMetricReader(); mp = MeterProvider(metric_readers=[rd]); srv = build_server("normal", telemetry=False); srv.middleware.append(ToolPolicyMiddleware(mp.get_meter("r2")))
        TEL.reset_local()
        async def go():
            async with Client(srv) as c:
                await c.call_tool("get_order", {"order_id": "ORD-00001"})
                await c.call_tool("issue_refund", {"order_id": "ORD-00001", "amount_eur": 1.0, "idempotency_key": "r2"})
                await c.call_tool("no_existe", {})
        run_async(go()); time.sleep(0.2)
        sp = {r["name"]: r for r in TEL.span_records() if r["name"].startswith("tools/call")}
        g, rf, ne = sp.get("tools/call get_order"), sp.get("tools/call issue_refund"), sp.get("tools/call no_existe")
        ev = lambda r: [e for e in r["events"] if e["name"] == "supportops.audit"]
        pts = {(p.attributes["gen_ai.tool.name"], p.attributes.get("error.type")): p.count for rm in rd.get_metrics_data().resource_metrics for sm in rm.scope_metrics for m in sm.metrics
               if m.name == "mcp.server.operation.duration" for p in m.data.data_points}
        checks = {"atributos de la herramienta": bool(g) and g["attributes"].get("supportops.tool.read_only") is True and g["attributes"].get("supportops.tool.destructive") is False and g["attributes"].get("network.transport") == "pipe",
                  "auditoría solo en destructivas": bool(rf) and len(ev(rf)) == 1 and ev(rf)[0]["attributes"].get("tool") == "issue_refund" and ev(rf)[0]["attributes"].get("outcome") == "ok" and not ev(g),
                  "destructiva no marcada como solo lectura": bool(rf) and rf["attributes"].get("supportops.tool.destructive") is True and rf["attributes"].get("supportops.tool.read_only") is False,
                  "métrica por herramienta/error": pts == {("get_order", None): 1, ("issue_refund", None): 1, ("no_existe", "tool_error"): 1},
                  "clase de error caller": bool(ne) and ne["attributes"].get("supportops.error.class") == "caller" and ne["attributes"].get("error.type") == "tool_error",
                  "sin argumentos capturados": all("gen_ai.tool.call.arguments" not in r["attributes"] for r in sp.values())}
        add("R2", "ToolPolicyMiddleware: 6 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R2", "ToolPolicyMiddleware", False, f"{type(e).__name__}: {e}")
    # R3
    try:
        j = join_report(AGENT_ROWS, SERVER_ROWS)
        ok = (j["tool_calls"], j["joined"], j["orphans"]) == (REF["tool_calls"], REF["joined"], REF["orphans"]) and j["by_tool"] == REF["by_tool"] and j["overhead_ms_median"] is not None and 0 < j["overhead_ms_median"] < 100
        add("R3", "join_report: contadores exactos y overhead en (0, 100) ms", ok, f"{j} · ref {REF['tool_calls']}/{REF['joined']}/{REF['orphans']}")
    except Exception as e: add("R3", "join_report", False, f"{type(e).__name__}: {e}")
    # R4
    try:
        pre = BR.call("refund_stats")["applied"]
        sc = {}
        sc["ok"] = safe_call(BR, "get_order", {"order_id": "ORD-00001"}, 3.0)
        sc["lectura_lenta"] = safe_call(BR, "track_shipment", {"order_id": "ORD-00017"}, 0.1)
        sc["tool_error"] = safe_call(BR, "track_shipment", {"order_id": "ORD-00013"}, 3.0)
        o = next(x for x in catalog.orders().values() if x["status"] == "delivered" and (x["delivered_days_ago"] or 99) <= 30)
        sc["reembolso"] = safe_call(BR, "issue_refund", {"order_id": o["order_id"], "amount_eur": o["total_eur"], "reason": "r4"}, 0.001)
        applied = BR.call("refund_stats")["applied"] - pre
        good = {"ok": sc["ok"]["ok"] and sc["ok"]["attempts"] == 1,
                "lectura_lenta": (not sc["lectura_lenta"]["ok"]) and sc["lectura_lenta"]["attempts"] == 2 and sc["lectura_lenta"]["error_type"] == "timeout",
                "tool_error": (not sc["tool_error"]["ok"]) and sc["tool_error"]["attempts"] == 1 and sc["tool_error"]["error_type"] == "tool_error",
                "reembolso": sc["reembolso"]["attempts"] == 2 and applied == 1}
        add("R4", "safe_call: 4 escenarios (incluye 1 sola ejecución del reembolso)", all(good.values()), f"{good} · ejecuciones del reembolso: {applied}")
    except Exception as e: add("R4", "safe_call", False, f"{type(e).__name__}: {e}")
    # R5
    try:
        T = BR.tools_list; swapped = list(reversed(T))
        import copy
        T2 = copy.deepcopy(T); T2[0].description = (T2[0].description or "") + " "
        T3 = copy.deepcopy(T); T3[1].input_schema = {**(T3[1].input_schema or {}), "extra": 1}
        ap = per_tool_digest(T)
        d_same = detect_drift(ap, swapped); d_desc = detect_drift(ap, T2); d_new = detect_drift(ap, T[:-1])
        sp_bad = McpServerProcess(mode="poisoned")
        with McpToolBridge(sp_bad.params(), read_timeout_s=3.0) as bad: d_bad = detect_drift(ap, bad.tools_list)
        checks = {"estable al reordenar": tools_digest(T) == tools_digest(swapped), "cambia con la descripción": tools_digest(T) != tools_digest(T2), "cambia con el esquema": tools_digest(T) != tools_digest(T3),
                  "sin deriva = False": d_same == {"drifted": False, "added": [], "removed": [], "changed": []},
                  "detecta cambio/eliminación y el servidor alterado": d_desc["changed"] == [T[0].name] and d_new["removed"] == [T[-1].name] and d_bad["drifted"] and "get_order" in d_bad["changed"]}
        add("R5", "tools_digest y detect_drift", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R5", "huella de herramientas", False, f"{type(e).__name__}: {e}")
    # R6
    try:
        full = {"name": "tools/call x", "attributes": {"mcp.method.name": "tools/call", "gen_ai.tool.name": "x", "jsonrpc.request.id": "1", "gen_ai.operation.name": "execute_tool", "mcp.protocol.version": "v", "network.transport": "pipe"}}
        bare = {"name": "tools/call x", "attributes": {"mcp.method.name": "tools/call"}}
        part = {"name": "tools/call x", "attributes": {"mcp.method.name": "tools/call", "gen_ai.tool.name": "x", "mcp.protocol.version": "v"}}
        e1, e2, e3 = spec_gaps(full, "client"), spec_gaps(bare, "client"), spec_gaps(part, "server")
        real = spec_gaps(next(r for r in SERVER_ROWS if r["name"].startswith("tools/call")), "server")
        ok = (e1 == {"required": [], "conditional": [], "recommended": []} and e2 == {"required": [], "conditional": ["gen_ai.tool.name", "jsonrpc.request.id"], "recommended": ["gen_ai.operation.name", "mcp.protocol.version", "network.transport"]}
              and e3 == {"required": [], "conditional": [], "recommended": ["gen_ai.operation.name", "network.transport"]} and real["required"] == [])
        add("R6", "spec_gaps exacto y contrato del servidor real", ok, f"cliente vacío={e1 == {'required': [], 'conditional': [], 'recommended': []}} · real={real}")
    except Exception as e: add("R6", "spec_gaps", False, f"{type(e).__name__}: {e}")
    return pd.DataFrame(rows).set_index("criterio")
''')
    code('''
# Ejecuta esta celda cuando hayas terminado los TODO
display(run_rubric())
''')

    md("""
    ---
    ## Paso final (opcional) · Míralo en Grafana

    Con el stack arriba (`docker compose --profile core --profile metrics up -d`) cambia `TEL` a modo `otlp` y el servidor a `McpServerProcess(telemetry="otlp", otlp_endpoint="http://localhost:4318")`, repite el Paso 0 y abre el dashboard **«12 · MCP y herramientas remotas»**: el panel de **trazas partidas** debe mostrar las 6 llamadas desde hilos sin contexto; arregla el origen (usa `contextvars.copy_context().run`) y comprueba que baja a cero.

    ## Retos extra (nivel experto)

    1. **Política `link`:** ejecuta el servidor con `context_policy="link"` y mide cuántas trazas separadas aparecen con tu `join_report`; ¿qué consulta TraceQL recupera «las llamadas enlazadas a una traza del agente»?
    2. **Presupuesto de reintentos:** limita `safe_call` a un máximo del 10 % de reintentos sobre las últimas 50 llamadas y demuestra con el servidor en modo `slow` que evita la tormenta de reintentos.
    3. **Cancelación real:** reescribe `track_shipment` como herramienta **asíncrona** (`async def`) con `anyio.sleep` y comprueba si la notificación de cancelación del SDK **sí** corta el trabajo (¿termina el span servidor antes? ¿qué cambia en el «zombi»?).
    4. **Canal HTTP:** lanza el servidor con `--transport streamable-http` y conecta con `Client("http://127.0.0.1:8000/mcp")`; ¿qué spans HTTP adicionales aparecen y cómo los relacionas (enlace) con los spans MCP?
    5. **Alerta de huella:** emite `supportops.mcp.tools_hash` como atributo del span de conexión y escribe la regla de alerta que dispare cuando cambie.

    ## Reflexión (producción e hilo conductor)

    - ¿Qué parte de lo medido en el `join_report` pondrías en un SLO («% de llamadas MCP unidas a su traza de agente») y qué umbral tendría sentido?
    - `safe_call` reintenta lecturas lentas. ¿Qué pasa con la carga del servidor si **todos** los agentes hacen lo mismo durante un incidente? (módulo 11: amplificación) ¿Dónde pondrías un disyuntor?
    - El módulo 13 atribuirá **coste por herramienta**: las llamadas MCP no tienen tokens, pero sí **tiempo y dinero** (una pasarela de pagos cobra por transacción). ¿Qué atributos de span necesitarías para atribuirlo?
    - Si el servidor MCP lo opera **otra empresa**, ¿qué parte de tu telemetría podrías seguir viendo y qué parte dependería de su colaboración (política `link`, `_meta`)?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine las funciones y vuelve a lanzar la rúbrica).
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
def safe_args(tool, args):
    allowed = ALLOW.get(tool, set()); out = {}
    for k, v in args.items():
        if k not in allowed: out[k] = "<redacted>"; continue
        if isinstance(v, str):
            for pat, repl in PII: v = pat.sub(repl, v)
        out[k] = v
    return out

class ToolPolicyMiddleware:
    def __init__(self, meter):
        self.hist = meter.create_histogram("mcp.server.operation.duration", unit="s", explicit_bucket_boundaries_advisory=MCP_BUCKETS)

    async def __call__(self, ctx, call_next):
        if ctx.method != "tools/call":
            return await call_next(ctx)
        name = (ctx.params or {}).get("name"); args = (ctx.params or {}).get("arguments") or {}
        span = otel_trace.get_current_span(); meta = TOOL_META.get(name, {})
        span.set_attributes({"supportops.tool.read_only": bool(meta.get("read_only", False)), "supportops.tool.destructive": bool(meta.get("destructive", False)), "network.transport": "pipe"})
        t0 = time.perf_counter(); err = None
        try:
            result = await call_next(ctx)
            if (result or {}).get("isError") if isinstance(result, dict) else getattr(result, "is_error", False):
                err = "tool_error"
                text = "".join(c.get("text", "") for c in result.get("content", []))
                span.set_attribute("supportops.error.class", "caller" if (text.startswith("Unknown tool") or "validation error" in text) else "server")
            return result
        except Exception as e:
            err = type(e).__name__
            raise
        finally:
            if meta.get("destructive"):
                span.add_event("supportops.audit", {"tool": name, "outcome": "error" if err else "ok", "order_id": str(args.get("order_id", ""))[:16]})
            a = {"mcp.method.name": "tools/call", "gen_ai.tool.name": name, "gen_ai.operation.name": "execute_tool"}
            if err: a["error.type"] = err
            self.hist.record(time.perf_counter() - t0, a)

def join_report(agent_rows, server_rows):
    tids = {r["trace_id"] for r in agent_rows if r["name"].startswith("invoke_agent")}
    cli = {r["span_id"]: r for r in agent_rows}
    calls = [r for r in server_rows if r["name"].startswith("tools/call")]
    joined = [r for r in calls if r["trace_id"] in tids]
    ov = [((cli[r["parent_span_id"]]["end_unix_nano"] - cli[r["parent_span_id"]]["start_unix_nano"]) - (r["end_unix_nano"] - r["start_unix_nano"])) / 1e6
          for r in joined if r["parent_span_id"] in cli]
    by_tool = {}
    for r in calls: by_tool[r["attributes"].get("gen_ai.tool.name")] = by_tool.get(r["attributes"].get("gen_ai.tool.name"), 0) + 1
    return {"tool_calls": len(calls), "joined": len(joined), "orphans": len(calls) - len(joined),
            "overhead_ms_median": float(np.median(ov)) if ov else None, "by_tool": by_tool}

def safe_call(bridge, name, args, timeout_s, retries=1, backoff_s=0.05):
    read_only = TOOL_META.get(name, {}).get("read_only", False)
    if not read_only and "idempotency_key" not in args:
        args = {**args, "idempotency_key": hashlib.sha256(json.dumps([name, args], sort_keys=True).encode()).hexdigest()[:16]}
    last = None
    for attempt in range(1, retries + 2):
        try:
            return {"ok": True, "value": bridge.call(name, args, timeout_s=timeout_s), "error_type": None, "attempts": attempt}
        except ToolError as e:
            last = e.error_type
            if e.error_type in ("timeout", "connection_closed") and attempt <= retries:
                time.sleep(backoff_s); timeout_s = max(timeout_s, 3.0) if not read_only else timeout_s; continue
            return {"ok": False, "value": None, "error_type": last, "attempts": attempt}
    return {"ok": False, "value": None, "error_type": last, "attempts": retries + 1}

def tools_digest(tools):
    items = sorted([[t.name, t.description or "", getattr(t, "input_schema", None) or {}] for t in tools], key=lambda x: x[0])
    return hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]

def detect_drift(approved, tools):
    cur = per_tool_digest(tools)
    added, removed = sorted(set(cur) - set(approved)), sorted(set(approved) - set(cur))
    changed = sorted(n for n in set(cur) & set(approved) if cur[n] != approved[n])
    return {"drifted": bool(added or removed or changed), "added": added, "removed": removed, "changed": changed}

def spec_gaps(span_row, kind):
    present = span_row["attributes"]
    return {lvl: sorted(a for a in attrs if a not in present) for lvl, attrs in SPEC[kind].items()}

display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, bargauge, lint, stat, text, thresholds, timeseries, traces_table, prom
    d = Dashboard("mcp-tools", "12 · MCP y herramientas remotas", tags=["curso", "mcp"], time_from="now-30m",
                  description="Herramientas MCP de pedidos: latencia cliente vs servidor, errores por herramienta/tipo, trazas partidas y cruzadas.")
    d.add(text("Cómo leer este dashboard", "**Cliente** = lo que el agente espera (`mcp.client.operation.duration`); **servidor** = lo que tardó el servidor (`mcp.server.operation.duration`). "
               "La diferencia es el *overhead* de transporte. Un **timeout** cuenta en el cliente pero el servidor sigue y termina bien (trabajo zombi). "
               "La tabla de **trazas partidas** debe estar vacía: si no, algún llamador pierde el contexto (hilos, gateway…).", h=3))
    d.row("Llamadas")
    cli, srv = "mcp_client_operation_duration_seconds", "mcp_server_operation_duration_seconds"
    d.add(
        stat("Llamadas MCP por minuto", f"sum(rate({cli}_count[$__rate_interval])) * 60", w=6, h=4, color_mode="value",
             description="Llamadas a herramientas medidas en el cliente (agente), por minuto."),
        stat("% con error (cliente)", f'sum(rate({cli}_count{{error_type!=""}}[$__rate_interval])) / sum(rate({cli}_count[$__rate_interval]))', unit="percentunit", w=6, h=4,
             thr=thresholds((None, "green"), (0.05, "orange"), (0.2, "red")), description="Fracción de llamadas con `error.type` (tool_error, timeout, connection_closed)."),
        stat("Timeouts (rango)", f'sum(increase({cli}_count{{error_type="timeout"}}[$__range]))', w=6, h=4, thr=thresholds((None, "green"), (1, "orange"), (10, "red")),
             description="Llamadas que agotaron el plazo del cliente: cada una es potencial trabajo zombi en el servidor."),
        stat("Errores de herramienta en el servidor", f'sum(increase({srv}_count{{error_type="tool_error"}}[$__range]))', w=6, h=4, thr=thresholds((None, "green"), (1, "orange"), (20, "red")),
             description="`isError` observados en el servidor. Si es mayor que los del cliente, hay llamadores que no los cuentan."),
    )
    d.add(
        timeseries("Llamadas por herramienta", [prom(f"sum by (gen_ai_tool_name) (rate({cli}_count[$__rate_interval]))", "{{gen_ai_tool_name}}")], unit="reqps", stack=True, w=12,
                   description="Tasa de llamadas por herramienta (cardinalidad acotada: 6 herramientas)."),
        timeseries("Errores por herramienta y tipo (cliente)", [prom(f'sum by (gen_ai_tool_name, error_type) (rate({cli}_count{{error_type!=""}}[$__rate_interval]))', "{{gen_ai_tool_name}} · {{error_type}}")],
                   unit="reqps", w=12, description="Qué herramienta falla y cómo: `tool_error` (dominio), `timeout` (plazo), `connection_closed` (transporte)."),
    )
    d.row("Latencia: cliente frente a servidor")
    d.add(
        timeseries("p95 por herramienta · CLIENTE", [prom(f"histogram_quantile(0.95, sum by (le, gen_ai_tool_name) (rate({cli}_bucket[$__rate_interval])))", "{{gen_ai_tool_name}}")], unit="s", w=12,
                   description="p95 que ve el agente (incluye transporte y espera)."),
        timeseries("p95 por herramienta · SERVIDOR", [prom(f"histogram_quantile(0.95, sum by (le, gen_ai_tool_name) (rate({srv}_bucket[$__rate_interval])))", "{{gen_ai_tool_name}}")], unit="s", w=12,
                   description="p95 que mide el servidor. Si el cliente sube y el servidor no, mira transporte o puente; si suben ambos, mira la dependencia."),
        bargauge("Overhead medio cliente − servidor", [prom(f"sum by (gen_ai_tool_name) (increase({cli}_sum[$__range])) / sum by (gen_ai_tool_name) (increase({cli}_count[$__range])) - "
                                                          f"on(gen_ai_tool_name) sum by (gen_ai_tool_name) (increase({srv}_sum[$__range])) / sum by (gen_ai_tool_name) (increase({srv}_count[$__range]))",
                                                          "{{gen_ai_tool_name}}", instant=True)], unit="s", w=24, h=6, thr=thresholds((None, "green"), (0.02, "orange"), (0.1, "red")),
                 description="Diferencia de duración media entre el cliente y el servidor por herramienta (≈ coste de transporte y serialización)."),
    )
    d.row("Trazas")
    d.add(
        traces_table("🚨 Trazas partidas (cliente MCP sin padre)", '{ name =~ "MCP send tools/call.*" && nestedSetParent < 0 }', w=12,
                     description="Spans cliente `MCP send tools/call` raíz (sin span del agente como padre): el llamador perdió el contexto antes de llegar al cliente MCP; su traza arrastra al servidor. En un sistema sano esta tabla está vacía."),
        traces_table("Trazas que cruzan agente → servidor MCP", '{ resource.service.name = "supportops-agent" } >> { resource.service.name = "supportops-orders-mcp" }', w=12,
                     description="Una fila por traza que contiene spans de los dos servicios: la unión funciona."),
        traces_table("Llamadas MCP con error (servidor)", '{ resource.service.name = "supportops-orders-mcp" && status = error }', w=12,
                     description="Spans del servidor en error (tool_error). Abre la traza para ver la dependencia que falló (p. ej. `GET carrier-api`)."),
        traces_table("Llamadas lentas (> 100 ms)", '{ resource.service.name = "supportops-orders-mcp" && span.mcp.method.name = "tools/call" && duration > 100ms }', w=12,
                     description="Llamadas a herramientas con más de 100 ms en el servidor: candidatas a dependencia lenta."),
    )
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "12-mcp-tools.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
def build_readme() -> None:
    readme = """# Módulo 12 · Trazas a través de servidores MCP y herramientas remotas

🟠 **Avanzado** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

Las herramientas de pedidos de SupportOps pasan de funciones locales a un **servidor MCP** (SDK oficial de Python, `mcp` 2.x) que corre
como **proceso aparte**. El reto: seguir una llamada a través de la frontera de proceso, entender qué emite ya el SDK, distinguir los
tres tipos de fallo, proteger los reintentos de herramientas destructivas y aplicar seguridad a la telemetría.

## Objetivos
1. Explicar MCP (clientes, servidores, herramientas, transportes) y por qué una herramienta remota rompe el tracing si no se propaga el contexto.
2. Construir un servidor MCP con el SDK y ejecutarlo como proceso hijo por stdio, con su propia telemetría.
3. Medir los spans del SDK en cliente y servidor y compararlos con las convenciones semánticas de MCP (estado **Development**).
4. Unir la traza del servidor con la del agente; detectar y corregir la pérdida de contexto en hilos.
5. Distinguir error de herramienta (`isError`), *timeout* y error de protocolo; medir el **trabajo zombi**.
6. Idempotencia y auditoría de herramientas destructivas.
7. Seguridad: lista blanca/redacción de argumentos, política de confianza del contexto remoto, huella de herramientas (*rug pull*).
8. Métrica `mcp.*.operation.duration`, dashboard y TraceQL de «traza partida».

## Contenido
| Archivo | Qué es |
|---|---|
| `12_mcp_tools.ipynb` | Lección (11 secciones, 8+ gráficos, medidas reales spec-vs-SDK, 🧠 de élite, autoevaluación) |
| `12_proyecto_mcp_tools.ipynb` | Proyecto: redacción de argumentos, middleware de política/auditoría, informe de unión de trazas, `safe_call` con idempotencia, huella de herramientas, contrato con la spec (rúbrica calibrada, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/mcp_orders.py` | Servidor MCP de pedidos, `McpServerProcess`, `McpToolBridge`, `WallClockInstrumentor`, middleware, política de contexto |
| `../stack/grafana/dashboards/12-mcp-tools.json` | Dashboard «12 · MCP y herramientas remotas» (uid `mcp-tools`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 11 y el paso final del proyecto. Lanza un proceso hijo por stdio (funciona en Colab).
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`).
- Dependencia extra: `pip install "mcp>=2,<3"` (la 1.x tiene otra API). El notebook lo instala.

## Lecturas
- MCP: especificación y **SEP-414** (contexto de traza en `_meta`) · OpenTelemetry: convenciones semánticas de MCP (Development) y spans de agentes (`execute_tool`).
- SDK de Python de MCP v2 · Invariant Labs, *Tool Poisoning Attacks* · W3C *Trace Context*.

## Cómo se conecta
Antes: módulo 11 (propagación W3C, trazas partidas, resiliencia). Después: el módulo 13 atribuye coste por agente/herramienta/modelo y el 20 trata la inyección
de instrucciones y la PII con más profundidad.
"""
    (COURSE / MOD / "README.md").write_text(readme, encoding="utf-8")
    print("OK README", MOD)


if __name__ == "__main__":
    build_lesson()
    build_project()
    build_readme()
    build_dashboard()
