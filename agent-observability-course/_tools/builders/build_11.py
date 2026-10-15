"""Genera el módulo 11_multiagente: README, lección y proyecto.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_11.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "11_multiagente"

IMPORTS_11 = '''
import dataclasses, json, re, threading, contextvars
from concurrent.futures import ThreadPoolExecutor
from opentelemetry import context as otel_context, trace as otel_trace
from opentelemetry.trace import SpanKind
from supportops.multiagent import (ORCH, SPECIALISTS, DelegationPolicy, MultiAgentSupportOps, RemoteAgentProcess, agent_tree_text,
                                   build_mesh, cost_rollup, critical_path, extract_manual, extract_sdk, format_traceparent,
                                   inject_manual, inject_sdk, parse_traceparent, service_palette, span_frame, waterfall_services)
STACK = check_stack("core")
LIVE = not STACK.degraded                      # True: el Collector responde y podemos enviar telemetría de verdad
'''


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "11_multiagente.ipynb", "Módulo 11 · Observabilidad de sistemas multi-agente")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 11 · Observabilidad de sistemas multi-agente: orquestador, handoffs y propagación de contexto

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Opcional: `--profile core` (Collector + Tempo + Loki + Grafana) y `metrics` (Prometheus) para la sección 10. Sin Docker todo funciona igual en **modo degradado** (la telemetría se queda en memoria; mismo esquema) |
    | **RAM aproximada** | < 600 MB sin stack · ≈ 1,2 GB con `core` + `metrics` |
    | **Prerrequisitos** | Módulos 02 (contexto y `traceparent`), 03 (SDK, `OTelInstrumentor`), 04 (GenAI semconv), 07-10 (TraceQL, LogQL, métricas, Grafana) |
    | **Hilo conductor** | SupportOps pasa de **un** agente a un **orquestador + 4 especialistas**; seguiremos un reembolso de extremo a extremo |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Modelar** un sistema multi-agente como un árbol de spans (`invoke_workflow` → `invoke_agent` → `chat` / `execute_tool`) y **distinguir** delegación de *handoff*.
    2. **Implementar a mano** la propagación W3C `traceparent` (formato, validación estricta, inyección y extracción) y **compararla** con el propagador del SDK.
    3. **Demostrar** qué ocurre cuando el contexto se pierde (hilos, colas, procesos) y **detectar** trazas huérfanas.
    4. **Propagar** el contexto por una cola entre **dos procesos reales** y **elegir** entre relación padre-hijo y *span link*.
    5. **Calcular** el camino crítico y el ahorro del *fan-out* paralelo; **atribuir** tokens y coste por agente **sin contar dos veces**.
    6. **Cuantificar** la amplificación de reintentos y el «trabajo zombi» en una **cascada de fallos**, y **comparar** políticas (timeout, reintentos, disyuntor, *deadline*).
    7. **Diagnosticar** la causa raíz de un fallo recorriendo la cadena de spans en error.
    8. **Operar** el sistema en Grafana: panel de agentes, TraceQL de huérfanos y de cascadas.
    """)

    md("## 🔁 Conexión con módulos anteriores")
    md(details("1 · (Módulo 02/03) ¿Qué lleva la cabecera `traceparent` y por qué sin ella un servicio abre una traza nueva?",
               "`versión-trace_id-parent_id-flags` (`00-<32 hex>-<16 hex>-<2 hex>`). El receptor crea su span con ese `trace_id` y como padre ese `parent_id`; si no hay cabecera (o es inválida) no hay contexto remoto y el SDK crea un **span raíz con `trace_id` nuevo**: la petición queda partida en trazas sin relación."))
    md(details("2 · (Módulo 03) ¿Qué hace `OTelInstrumentor.agent_run` y de qué depende que `invoke_agent` sea hijo de otro span?",
               "Abre el span `invoke_agent <nombre>` con el reloj simulado. Su padre es el **contexto OpenTelemetry actual** (contextvars) en ese momento: si hay un span activo, será su hijo; si no, será raíz. En multi-agente eso significa que **quien llama debe dejar su span activo y el contexto remoto debe estar adjunto** antes de ejecutar al subagente."))
    md(details("3 · (Módulo 04) ¿Cuándo es `invoke_agent` de tipo CLIENT y cuándo INTERNAL?",
               "CLIENT cuando el agente es un **servicio remoto** (se le llama por red); INTERNAL cuando corre en el mismo proceso. La spec GenAI (estado *Development*) solo define el lado cliente: el lado servidor de un agente remoto lo decide cada implementación."))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_11 + '''
print("Stack:", "arriba (OTLP al Collector)" if LIVE else "no disponible -> modo degradado (telemetría en memoria)")
''')

    # ------------------------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · Intuición: de un agente a un equipo de agentes

    SupportOps v0 era **un** agente con cuatro herramientas. Funciona, pero a medida que crece (más herramientas, más políticas, más permisos) el *prompt* se hincha, el modelo se confunde y un solo fallo contamina todo. La salida habitual es **dividir**: un **orquestador** que entiende el ticket y reparte el trabajo entre **especialistas** (pedidos, facturación, conocimiento, escalado), cada uno con pocas herramientas, un prompt corto y —si conviene— un modelo distinto.

    | Si vienes de… | Esto es como… | Lo que se rompe al observarlo |
    |---|---|---|
    | **ML** | Un *ensemble*/stacking: un meta-modelo que decide qué modelo base llama y combina sus salidas | El error final no dice **qué modelo base** falló; la métrica agregada oculta al culpable |
    | **Backend** | Un API gateway + microservicios con llamadas síncronas, colas y *fan-out* | Sin **tracing distribuido** ves cada servicio por separado y nunca la petición completa |
    | **SRE** | Dependencias en cascada: un servicio lento hace que el llamador reintente y sature a todos | Timeouts, reintentos y colas **multiplican** la carga: *retry storms* y *cascading failures* |

    Cada especialista es un **servicio** (`service.name = supportops-<agente>`, su propio `TelemetryHandle`). La pregunta de observabilidad cambia de «¿qué hizo el agente?» a «**¿qué agente hizo qué, por orden de quién, cuánto costó y dónde se rompió la cadena?**».
    """)
    code('''
fig, ax = viz.canvas(12.5, 5.6, xlim=(0, 125), ylim=(0, 58))
cli = viz.box(ax, 1, 24, 13, 9, "Cliente\\n(ticket)", color=viz.PALETTE["neutral"], bold=True)
orc = viz.box(ax, 25, 15, 30, 27, "supportops-orchestrator\\n① enrutar  (mock-small)\\n④ sintetizar  (mock-large)\\nno tiene herramientas de negocio", color=viz.PALETTE["traces"], fontsize=8.5, bold=True)
ordr = viz.box(ax, 78, 45, 27, 9, "orders-agent · get_order", color=viz.PALETTE["logs"], fontsize=8.5)
kb = viz.box(ax, 78, 33, 27, 9, "knowledge-agent · search_kb", color=viz.PALETTE["logs"], fontsize=8.5)
bil = viz.box(ax, 78, 17, 27, 9, "billing-agent (mock-large)\\nget_order · issue_refund", color=viz.PALETTE["metrics"], fontsize=8.5)
esc = viz.box(ax, 78, 4, 27, 9, "escalation-agent · escalate_to_human", color=viz.PALETTE["error"], fontsize=8.5)
viz.arrow(ax, viz.right(cli), viz.left(orc), "ticket")
viz.arrow(ax, (56, 38), viz.left(ordr), "② en paralelo\\n(traceparent)", color=viz.PALETTE["traces"], rad=-0.15, fontsize=7.5)
viz.arrow(ax, (56, 33), viz.left(kb), "", color=viz.PALETTE["traces"])
viz.arrow(ax, (56, 21), viz.left(bil), "③ después\\n(con el contexto de ②)", color=viz.PALETTE["traces"], fontsize=7.5)
viz.arrow(ax, (56, 17), viz.left(esc), "fallback si ③ falla", color=viz.PALETTE["error"], rad=0.25, dashed=True, fontsize=7.5)
ax.text(66, 56, "cada caja = un servicio con su propio Resource y su TelemetryHandle", fontsize=8.5, color=viz.PALETTE["neutral"], ha="center")
ax.set_title("SupportOps multi-agente (modo «delegación»: el orquestador conserva el control)", loc="left")
plt.show()
''')
    md(observe("""
    - Hay **tres tipos de aristas**: cliente→orquestador (entrada), orquestador→especialista (**cada flecha cruza un límite de servicio**: ahí se debe propagar el contexto) y el *fallback* discontinuo (camino que solo existe en el fallo).
    - Los pasos ② son **paralelos**: la latencia del reembolso no es la suma de ambos, sino el máximo (lo medimos en la sección 5).
    - El orquestador usa un modelo **pequeño para enrutar** y uno **grande para sintetizar**; facturación usa el grande porque mueve dinero. Esa mezcla de modelos hace que el coste **no se reparta** como el tráfico (sección 6).
    """))
    md(box("warn", "¿Cuándo NO usar multi-agente?", """
    Más agentes = más llamadas, más tokens y más superficie de fallo. Anthropic midió en su sistema de investigación que los agentes usan ≈ **4×** más tokens que un chat y los sistemas multi-agente ≈ **15×** (ver referencias). Un estudio de Google (arXiv 2512.08296) encontró que en tareas **secuenciales** todas las variantes multi-agente *empeoraron* el rendimiento (39-70 %) y que sin orquestador central los errores se amplifican ≈ 17×, frente a ≈ 4× con un orquestador.
    Regla práctica: empieza con **un** agente; divide solo si hay **herramientas/permisos que aislar**, **contextos que no caben** o **trabajo paralelizable**. Y mide el coste (sección 6) antes de aceptar la arquitectura.
    """))

    # ------------------------------------------------------------------------------------------------------------- 2
    md("""
    ---
    # 2 · Teoría: el modelo de datos de un sistema de agentes

    ## 2.1 La jerarquía de spans (GenAI semconv · estado *Development*)

    | Nivel | Span | Kind | Qué representa | Atributos clave |
    |---|---|---|---|---|
    | 0 | `invoke_workflow support_ticket` | INTERNAL | Orquestación a nivel de aplicación de **varios** agentes | `gen_ai.operation.name=invoke_workflow`, `gen_ai.workflow.name`, `gen_ai.conversation.id` |
    | 1 | `invoke_agent <agente>` | **CLIENT** si el agente es un servicio remoto · **INTERNAL** si es del mismo proceso | Una invocación de agente | `gen_ai.agent.name`, `gen_ai.provider.name` (requerido en CLIENT), `gen_ai.conversation.id` |
    | 2 | `chat <modelo>` | CLIENT | Una llamada al LLM | `gen_ai.request.model`, `gen_ai.usage.input_tokens/output_tokens` |
    | 2 | `execute_tool <herramienta>` | INTERNAL | Una herramienta | `gen_ai.tool.name`, `gen_ai.tool.call.id` |

    > ⚠️ Esto está en estado **Development** en la spec (`semantic-conventions-genai`). La spec dice que `invoke_workflow` se usa para orquestación de aplicación (varios agentes) y **no** para una llamada suelta a un agente. Los nombres y atributos pueden cambiar: verifica la versión antes de fijar dashboards.

    ## 2.2 Delegación frente a *handoff*

    | | **Delegación** (agente-como-herramienta) | **Handoff** (transferencia de control) |
    |---|---|---|
    | Quién habla con el usuario | El **orquestador** (sintetiza la respuesta) | El **especialista** (responde directo) |
    | Forma del árbol | Anidado: orquestador → especialistas → LLM/tools | Plano: el orquestador **termina** y el especialista es su *hermano* |
    | Coste | + enrutado + **síntesis** (lee todas las salidas) | + enrutado; sin síntesis |
    | Riesgo | Cuello de botella y cuota del orquestador | Pérdida de contexto; el especialista debe valerse solo |
    | Se parece a | `await service.call()` | Una redirección HTTP / pasar el ticket a otro equipo |

    ## 2.3 Una regla de oro para contar tokens

    La spec es explícita en las métricas por invocación: *las llamadas de un subagente se registran contra **ese** agente «para que cada llamada de inferencia se cuente exactamente una vez a lo largo del árbol»*. Si el span del orquestador acumulase los tokens de sus hijos, **sumar todos los spans contaría el consumo dos veces**. Cuenta siempre en las **hojas** (`chat`) y calcula los totales del árbol agregando hacia arriba.
    """)
    code('''
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2))
for ax, title in zip(axes, ["Delegación (anidado)", "Handoff (plano)"]):
    ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off"); ax.set_title(title, loc="left")
c = viz.PALETTE
# --- delegación
viz.box(axes[0], 2, 52, 44, 6, "invoke_workflow support_ticket", color=c["neutral"], fontsize=8)
viz.box(axes[0], 8, 43, 44, 6, "invoke_agent orchestrator", color=c["traces"], fontsize=8)
for y, t in ((34, "chat (enrutar)"), (26, "invoke_agent billing  [CLIENT]"), (18, "└ invoke_agent billing  [INTERNAL]"), (10, "   └ chat · execute_tool · chat"), (2, "chat (sintetizar)")):
    viz.box(axes[0], 14 + (6 if "└" in t else 0), y, 50, 6, t, color=c["metrics"] if "billing" in t or "execute" in t else c["traces"], fontsize=7.5)
# --- handoff
viz.box(axes[1], 2, 52, 44, 6, "invoke_workflow support_ticket", color=c["neutral"], fontsize=8)
viz.box(axes[1], 8, 43, 36, 6, "invoke_agent orchestrator", color=c["traces"], fontsize=8)
viz.box(axes[1], 14, 34, 36, 6, "chat (enrutar)", color=c["traces"], fontsize=7.5)
viz.box(axes[1], 14, 26, 44, 6, "execute_tool transfer_to_billing", color=c["error"], fontsize=7.5)
viz.box(axes[1], 8, 14, 52, 6, "invoke_agent billing  [CLIENT]  (hermano)", color=c["metrics"], fontsize=8)
viz.box(axes[1], 14, 5, 50, 6, "└ invoke_agent billing · chat · tool · chat", color=c["metrics"], fontsize=7.5)
axes[1].annotate("el orquestador\\nya terminó", xy=(46, 46), xytext=(70, 42), arrowprops=dict(arrowstyle="->", color=c["neutral"]), fontsize=8, color=c["neutral"])
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - En la **delegación** el árbol tiene una profundidad extra y un último `chat` (la síntesis) **después** de los especialistas: el orquestador está en el camino crítico de principio a fin.
    - En el **handoff** el especialista cuelga del workflow, no del orquestador: un *dashboard* que mida «tiempo del orquestador» **no verá** el trabajo del especialista. Elige bien qué span usas como «la petición».
    - Las dos formas comparten la **raíz** `invoke_workflow`: es el span que representa el ticket para el usuario (la SLI de latencia de extremo a extremo vive ahí).
    """))

    # ------------------------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · Propagación de contexto a mano: `traceparent`

    Cuando el orquestador llama a un especialista a través de una frontera (HTTP, cola, otro proceso) solo viajan **bytes**. Para que la traza continúe, el llamador **inyecta** una cabecera y el receptor la **extrae**. El estándar es **W3C Trace Context**:

    ```
    traceparent: 00 - 4bf92f3577b34da6a3ce929d0e0e4736 - 00f067aa0ba902b7 - 01
                 │     └─────────── trace-id ──────────┘ └─ parent-id ──┘  └ flags
                 └ versión                                (span del llamador)  (bit 0 = muestreado)
    ```

    Reglas que importan al implementarlo (spec): hexadecimal **en minúsculas**; la versión `ff` es inválida; `trace-id` y `parent-id` **no pueden ser todo ceros**; en la versión `00` no puede haber campos extra (en versiones futuras se parsean los cuatro primeros y se ignora el resto). Un receptor que recibe una cabecera inválida debe **ignorarla** y abrir una traza nueva —nunca romper la petición—.
    """)
    code('''
fig, ax = viz.canvas(12, 3.4, xlim=(0, 120), ylim=(0, 30))
parts = [("00", "versión", viz.PALETTE["neutral"], 4), ("4bf92f3577b34da6a3ce929d0e0e4736", "trace-id (128 bit)\\nidentifica TODA la petición", viz.PALETTE["traces"], 48),
         ("00f067aa0ba902b7", "parent-id (64 bit)\\nspan del llamador", viz.PALETTE["metrics"], 26), ("01", "flags\\nbit 0 = muestreado", viz.PALETTE["logs"], 6)]
x = 4
for txt, lab, col, w in parts:
    viz.box(ax, x, 14, w, 7, txt, color=col, fontsize=8.5, bold=True)
    ax.text(x + w / 2, 8, lab, ha="center", va="top", fontsize=8, color=col)
    if x > 4: ax.text(x - 1.2, 17.5, "-", fontsize=14, ha="center", va="center")
    x += w + 3.5
ax.text(60, 27, "traceparent  (55 caracteres en la versión 00)", ha="center", fontsize=10, fontweight="bold")
plt.show()
''')
    md(observe("""
    - Solo el **trace-id** es común a toda la traza; el **parent-id** cambia en cada salto (es el span que hace la llamada).
    - El **bit de muestreo** viaja con la cabecera: la decisión de muestrear se toma en la raíz y los demás servicios la **respetan** (sampler `ParentBased`). Si un servicio ignora el bit, aparecen trazas con huecos (módulo 18).
    """))
    md("**Implementación a mano** (en `supportops.multiagent`): `parse_traceparent` valida de forma estricta y devuelve `None` si la cabecera no es válida. Probémosla con vectores de prueba, incluidos los casos hostiles:")
    code('''
OK = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
VECTORS = [
    ("válido, muestreado", OK),
    ("válido, NO muestreado (flags=00)", OK[:-2] + "00"),
    ("versión futura con campos extra (se tolera)", "01-" + OK[3:] + "-campo-extra"),
    ("versión 00 con campo extra (prohibido)", OK + "-extra"),
    ("MAYÚSCULAS", OK.upper()),
    ("versión ff (prohibida)", "ff" + OK[2:]),
    ("trace-id todo ceros", "00-" + "0" * 32 + OK[35:]),
    ("parent-id todo ceros", OK[:36] + "0" * 16 + "-01"),
    ("trace-id corto", "00-4bf92f3577b34da6a3ce929d0e0e47-00f067aa0ba902b7-01"),
    ("basura", "hola"),
]
rows_ = []
for name, h in VECTORS:
    tp = parse_traceparent(h)
    rows_.append({"caso": name, "válido": "✅" if tp else "❌", "sampled": tp.sampled if tp else None, "cabecera": h[:60]})
pd.DataFrame(rows_)
''')
    md("""
    Ahora **inyectar y extraer** con un span real, a mano y con el propagador del SDK. Deben producir **el mismo** `traceparent`:
    """)
    code('''
mesh = build_mesh(mode="memory")                       # 5 servicios, telemetría en memoria
tracer = mesh.handle(ORCH).tracer()
caller = tracer.start_span("invoke_agent orders-agent", kind=SpanKind.CLIENT)
with otel_trace.use_span(caller, end_on_exit=False):
    by_hand, by_sdk = inject_manual(), inject_sdk()    # leen el span ACTIVO
caller.end()
print("a mano :", by_hand)
print("con SDK:", by_sdk)
print("iguales:", by_hand == by_sdk)

remote = otel_trace.get_current_span(extract_manual(by_hand)).get_span_context()
print(f"\\nextraído -> trace_id={format(remote.trace_id, '032x')}  parent_id={format(remote.span_id, '016x')}  remoto={remote.is_remote}")
print("¿coincide con el span que llamó?", format(remote.span_id, "016x") == format(caller.get_span_context().span_id, "016x"))
''')
    md("""
    > 💡 Si ves `-03` al final en lugar de `-01`: el SDK reciente activa también el bit 1 de las *flags* («trace-id aleatorio», añadido en W3C Trace Context nivel 2) además del bit 0 de muestreo. Nuestra versión manual conserva el **byte de flags completo** (`format_traceparent(..., sampled=int(flags))`): reescribirlo siempre como `01` sería una pérdida silenciosa de información.
    """)
    md("""
    ## 3.1 Dónde se pierde el contexto sin que te enteres

    El «contexto actual» de OpenTelemetry vive en `contextvars`. Se hereda en *tareas* de `asyncio`, pero **no** al saltar a un hilo nuevo, a un *executor* ni, por supuesto, a otro proceso o a una cola. Es la causa nº 1 de trazas huérfanas:
    """)
    code('''
seen = {}
def probe(tag, ctx=None):
    token = otel_context.attach(ctx) if ctx is not None else None
    seen[tag] = otel_trace.get_current_span().get_span_context().is_valid
    if token is not None: otel_context.detach(token)

with tracer.start_as_current_span("orquestador") as parent:
    t = threading.Thread(target=probe, args=("Thread sin pasar contexto",)); t.start(); t.join()
    with ThreadPoolExecutor(1) as ex: ex.submit(probe, "ThreadPoolExecutor.submit sin contexto").result()
    ctx_now = otel_context.get_current()
    t = threading.Thread(target=probe, args=("Thread + contexto explícito", ctx_now)); t.start(); t.join()
    c = contextvars.copy_context()
    with ThreadPoolExecutor(1) as ex: ex.submit(c.run, probe, "ThreadPoolExecutor + copy_context().run").result()
pd.Series(seen, name="¿ve el span del orquestador?").map({True: "✅ sí", False: "❌ NO (traza rota)"}).to_frame()
''')
    md(observe("""
    - Los dos primeros casos **pierden** el contexto en silencio: no hay error, solo una traza partida más tarde en Tempo.
    - La corrección es siempre la misma idea: **llevar el contexto explícitamente** (`attach` del contexto capturado o `copy_context().run`) o serializarlo en una cabecera.
    - Los *frameworks* de agentes que ejecutan herramientas en hilos o procesos son los sospechosos habituales: en el proyecto aprenderás a detectar este patrón en las trazas.
    """))

    # ------------------------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · SupportOps multi-agente en acción

    `MultiAgentSupportOps` (en `supportops/multiagent.py`) está construido **encima** de `setup_telemetry`/`OTelInstrumentor` del módulo 03: cada agente es un servicio con su propio handle. El orquestador:

    1. **Enruta** con un LLM pequeño (JSON `{intent, agent}`); si falta el número de pedido, **pregunta** sin llamar a nadie.
    2. **Delega**: en un reembolso lanza en *paralelo* `orders-agent` y `knowledge-agent` (pre-chequeos), y luego `billing-agent` con ese contexto añadido al prompt.
    3. **Sintetiza** la respuesta con un LLM grande.

    Cada delegación abre un span **CLIENT** `invoke_agent <agente>`, **inyecta** `traceparent` y ejecuta el subagente tras **extraer** el contexto: exactamente lo que harían dos procesos, pero en uno solo para que el laboratorio sea determinista.
    """)
    code('''
N = 60 if FAST_DEV_RUN else 240
tickets = generate_tickets(N, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)
# un reembolso que de verdad llega a issue_refund, para tener una traza completa y rica
probe_agent = SupportAgent()
refund = next(t for t in tickets if t.intent_true == "refund" and t.order_id and "issue_refund" in probe_agent.run(t).tools_used)
refund = dataclasses.replace(refund, faults=[])
system = MultiAgentSupportOps(mesh, mode="delegate")
mesh.reset_local()
res = system.run(refund)
rows = mesh.span_records(res.trace_id)
print(f"ticket {res.ticket_id} · {refund.text[:70]}...")
print(f"estado={res.status} · latencia={res.latency_s:.2f}s · coste=${res.cost_usd:.5f} · tokens={res.input_tokens}+{res.output_tokens} · agentes={res.agents_called}")
print(f"{len(rows)} spans en UNA traza ({res.trace_id[:8]}…) repartidos en {len({r['resource']['service.name'] for r in rows})} servicios\\n")
print(agent_tree_text(rows, show_chat=True))
''')
    code('''
fig = plt.figure(figsize=(12.5, 7.2))
ax = fig.add_axes([0.30, 0.08, 0.68, 0.84])
waterfall_services(rows, ax=ax, title=f"Cascada de la petición de reembolso {res.ticket_id} (color = servicio)")
plt.show()
''')
    md(observe("""
    - **Una sola traza** cruza cuatro servicios (cuatro colores; un quinto, `escalation-agent`, aparece si hay *fallback*). Sin la propagación del contexto serían cuatro trazas sueltas y nadie sabría que pertenecen a la misma petición.
    - Los dos pre-chequeos (verde y morado) **empiezan a la vez**; `billing-agent` no arranca hasta que termina el más lento. Fíjate en que cada delegación aparece **dos veces** con el mismo nombre: el CLIENT del orquestador (lo que el llamador ve, incluidos timeouts) y el INTERNAL del servicio (lo que hizo por dentro). Si difieren en duración, la diferencia es red, cola o abandono.
    - El último `chat` (síntesis, modelo grande) es secuencial y está en el camino crítico: es un candidato a optimizar *si* no se necesita (handoff).
    """))
    md("""
    ### Logs y métricas llevan la misma identidad

    El `OTelInstrumentor` de cada servicio emite logs con el `trace_id` y `span_id` activos, así que **un solo filtro** reúne la historia de todos los agentes. Y las métricas llevan el nombre del agente como atributo:
    """)
    code('''
logs = pd.DataFrame(mesh.log_records(res.trace_id))
logs["servicio"] = logs.resource.map(lambda r: r["service.name"].replace("supportops-", ""))
logs["t_rel_s"] = ((logs.time_unix_nano - logs.time_unix_nano.min()) / 1e9).round(2)
display(logs[["t_rel_s", "servicio", "severity_text", "body"]].head(12))
print(f"logs de la petición: {len(logs)} · con trace_id: {logs.trace_id.notna().mean():.0%} · trace_id únicos: {logs.trace_id.nunique()}")
pts = pd.DataFrame(mesh.metric_points())
display(pts[pts.name == "supportops.delegation.attempts"][["name", "attributes", "value"]])
''')

    # ------------------------------------------------------------------------------------------------------------- 5
    md("""
    ---
    # 5 · Camino crítico y fan-out paralelo

    En un árbol de spans la latencia de la petición **no** es la suma de todos los spans, sino la longitud del **camino crítico**: la cadena de spans que, en cada nivel, termina la última y «sostiene» a su padre. Acortar cualquier cosa fuera de esa cadena no cambia la latencia de extremo a extremo.

    Para el reembolso: `latencia ≈ enrutar + max(orders, knowledge) + billing + sintetizar` (pre-chequeos en paralelo). Si fueran secuenciales sería `enrutar + orders + knowledge + billing + sintetizar`.
    """)
    code('''
cp = critical_path(rows)
agents = [r for r in rows if r["kind"] == "CLIENT" and r["attributes"].get("supportops.delegation.role")]
orch_chats = [r for r in rows if r["resource"]["service.name"] == ORCH and r["attributes"].get("gen_ai.operation.name") == "chat"]
t0 = min(r["start_unix_nano"] for r in rows)
dur = lambda r: (r["end_unix_nano"] - r["start_unix_nano"]) / 1e9
pre = [r for r in agents if r["attributes"]["supportops.delegation.role"] == "precheck"]
seq_extra = sum(dur(r) for r in pre) - max(dur(r) for r in pre)
print("camino crítico:", " → ".join(r["name"].replace("invoke_agent ", "") for r in cp))
print(f"latencia real {res.latency_s:.2f}s · si los pre-chequeos fueran secuenciales: {res.latency_s + seq_extra:.2f}s  (el paralelismo ahorra {seq_extra:.2f}s = {seq_extra / (res.latency_s + seq_extra):.0%})")

fig, ax = plt.subplots(figsize=(11, 3.8))
items = sorted(orch_chats + agents, key=lambda r: r["start_unix_nano"])
cp_ids = {r["span_id"] for r in cp}
for i, r in enumerate(items):
    st, du = (r["start_unix_nano"] - t0) / 1e9, dur(r)
    col = viz.PALETTE["traces"] if r["attributes"].get("gen_ai.operation.name") == "chat" else viz.PALETTE["metrics"]
    ax.barh(i, du, left=st, color=col, alpha=0.9, height=0.6)
    lab = ("chat · " + r["attributes"]["gen_ai.request.model"]) if r["kind"] == "CLIENT" and r["resource"]["service.name"] == ORCH and "gen_ai.request.model" in r["attributes"] else r["name"].replace("invoke_agent ", "→ ")
    ax.text(st + du + 0.05, i, f"{lab}  {du:.2f}s", va="center", fontsize=8)
ax.set_yticks([]); ax.invert_yaxis(); ax.set_xlabel("tiempo desde el inicio (s)"); ax.set_title("Línea de tiempo del orquestador (azul = su LLM, naranja = delegaciones)")
ax.axvline(res.latency_s, color=viz.PALETTE["neutral"], ls=":"); plt.show()
''')
    md(observe("""
    - Las dos barras de los **pre-chequeos se solapan**; la siguiente barra (facturación) arranca justo cuando termina la **más larga**: esa es la que está en el camino crítico. Acelerar `orders-agent` (más corta) no mejoraría nada.
    - Con un *fan-out* ancho, la latencia la dicta el **más lento de N** (cola larga). Con 5 ramas independientes y un 2 % de llamadas lentas, P(alguna lenta) = 1 − 0,98⁵ ≈ **9,6 %**: el p95 de un agente que depende de cinco subagentes se parece al p99 de cada uno.
    - Si un *dashboard* suma las duraciones de todos los spans del árbol obtendrá un número mayor que la latencia real: sirve para **coste de cómputo**, no para latencia.
    """))
    md("### Tiempo propio (*exclusive*) frente a tiempo total (*inclusive*) por agente")
    code('''
df = span_frame(rows)
inv = df[(df.op == "invoke_agent") & (df.kind == "INTERNAL") | (df.op == "invoke_workflow")].copy()
children_time = df.groupby("parent").dur_s.sum()                 # suma de hijos (puede superar al padre si hay paralelismo)
inv["inclusive_s"] = inv.dur_s
inv["hijos_s"] = inv.span_id.map(children_time).fillna(0)
inv["propio_s"] = (inv.inclusive_s - inv.hijos_s).clip(lower=0)
display(inv[["name", "service", "inclusive_s", "hijos_s", "propio_s"]].round(2).reset_index(drop=True))
''')
    md(box("idea", "Lectura", """
    Un `propio_s` ≈ 0 en un agente de pasos secuenciales indica que casi todo su tiempo está en llamadas a LLM y herramientas (lo normal). Un `propio_s` grande en el **orquestador** indica trabajo propio no instrumentado (parseo, esperas, serialización) o **paralelismo** (hijos que se solapan hacen que `hijos_s` supere al padre): no lo interpretes como un error.
    """))

    # ------------------------------------------------------------------------------------------------------------- 6
    md("""
    ---
    # 6 · Delegar, transferir o no dividir: latencia, tokens y coste

    Comparamos tres arquitecturas sobre **los mismos tickets** (con los fallos de fondo de siempre): el agente único v0, el multi-agente con **delegación** y con **handoff**.
    """)
    code('''
base_res = run_tickets(SupportAgent(), tickets)
base = pd.DataFrame(to_rows(tickets, base_res)).assign(arq="único (v0)", intent=lambda d: d.intent_true)
frames = [base[["arq", "intent", "latency_s", "cost_usd", "input_tokens", "output_tokens", "n_llm_calls", "status"]]]
for mode in ("delegate", "handoff"):
    m = build_mesh(mode="memory")
    rs = MultiAgentSupportOps(m, mode=mode).run_many(tickets)
    d = pd.DataFrame([r.to_row() for r in rs]).assign(arq=mode, intent=lambda x: x.intent.fillna("unknown"))
    frames.append(d[["arq", "intent", "latency_s", "cost_usd", "input_tokens", "output_tokens", "n_llm_calls", "status"]])
    if mode == "delegate": mesh_delegate, res_delegate = m, rs
ALL = pd.concat(frames, ignore_index=True)
summary = ALL.groupby("arq").agg(latencia_media=("latency_s", "mean"), latencia_p95=("latency_s", lambda s: np.quantile(s, .95)),
                                  coste_medio_usd=("cost_usd", "mean"), llamadas_llm=("n_llm_calls", "mean"), tokens_entrada=("input_tokens", "mean"))
summary["coste_vs_único"] = summary.coste_medio_usd / summary.loc["único (v0)", "coste_medio_usd"]
display(summary.round(4))
''')
    code('''
order = ["único (v0)", "handoff", "delegate"]
cols = {"único (v0)": viz.PALETTE["neutral"], "handoff": viz.PALETTE["logs"], "delegate": viz.PALETTE["traces"]}
fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
axes[0].boxplot([ALL[ALL.arq == a].latency_s for a in order], tick_labels=order, showfliers=False)
axes[0].set_title("Latencia por petición (s)")
by_int = ALL.groupby(["intent", "arq"]).cost_usd.mean().unstack()[order]
by_int.plot.bar(ax=axes[1], color=[cols[a] for a in order], rot=20); axes[1].set_title("Coste medio por intención (USD)"); axes[1].set_xlabel("")
tok = ALL.groupby("arq")[["input_tokens", "output_tokens"]].mean().loc[order]
tok.plot.bar(stacked=True, ax=axes[2], color=[viz.PALETTE["traces"], viz.PALETTE["metrics"]], rot=0); axes[2].set_title("Tokens medios por petición"); axes[2].set_xlabel("")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La **delegación** es la más lenta y la más cara: añade un LLM de enrutado y otro de **síntesis** (modelo grande) y, en reembolsos, tres especialistas. El **handoff** se queda en medio.
    - Aun así el handoff gasta **menos tokens de entrada** que el agente único: cada especialista solo recibe el esquema de **sus** herramientas (un prompt más corto). La especialización *abarata* el prompt; lo que encarece es el modelo grande y las llamadas extra.
    - El coste por intención **no sigue** al tráfico: `refund` es el 20 % de los tickets y concentra una fracción mucho mayor del gasto (modelo grande + contexto de los pre-chequeos). Es la semilla del módulo 13 (atribución).
    """))
    md("### ¿De dónde sale el gasto? Coste por agente y por modelo (contando solo hojas `chat`)")
    code('''
all_rows = mesh_delegate.span_records()
roll = cost_rollup(all_rows)
rdf = pd.DataFrame(roll).T.rename_axis("servicio").reset_index()
rdf["servicio"] = rdf.servicio.str.replace("supportops-", "")
rdf["cuota_coste"] = rdf.cost_usd / rdf.cost_usd.sum()
display(rdf.sort_values("cost_usd", ascending=False).round(5))

# ¡Cuidado con sumar spans de más! Tanto invoke_agent como chat llevan gen_ai.usage.*: sumar todos cuenta el consumo dos veces
fr = span_frame(all_rows)
naive = fr[(fr.in_tok > 0)].in_tok.sum(); leaf = fr[fr.op == "chat"].in_tok.sum()
print(f"tokens de entrada: sumando TODOS los spans con uso = {naive:,} · solo hojas chat = {leaf:,}  ->  error de {naive / leaf - 1:.0%}")
fig, ax = plt.subplots(figsize=(9, 3.4))
ax.barh(rdf.servicio, rdf.cost_usd * 1000, color=viz.PALETTE["metrics"]); ax.set_xlabel("coste acumulado (milésimas de USD, precios SIMULADOS)"); ax.set_title(f"Reparto del coste entre agentes · {len(res_delegate)} tickets")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - `billing-agent` (modelo grande) y el **orquestador** (enrutado + síntesis, también con modelo grande en la síntesis) dominan el gasto, aunque `billing` solo atiende reembolsos.
    - El recuadro de «tokens de entrada» demuestra el error clásico: **sumar todos los spans que traen `gen_ai.usage.*`** infla el total porque `invoke_agent` repite lo que ya contó cada `chat`. Para presupuestos (módulo 13) suma **solo hojas**.
    """))
    md("### El contexto que arrastramos: pasar la salida de un agente al siguiente cuesta tokens")
    code('''
rf = [t for t in tickets if t.intent_true == "refund" and t.order_id][:12]
m_a, m_b = build_mesh(mode="memory"), build_mesh(mode="memory")
with_ctx = MultiAgentSupportOps(m_a, prechecks=True).run_many(rf)
no_ctx = MultiAgentSupportOps(m_b, prechecks=False).run_many(rf)
def bill_in(rs): return np.mean([r.per_agent.get("billing-agent", {}).get("input_tokens", 0) for r in rs])
print(f"tokens de entrada de billing-agent: con contexto de pre-chequeos = {bill_in(with_ctx):.0f} · sin pre-chequeos = {bill_in(no_ctx):.0f}")
print(f"coste medio por reembolso: con = ${np.mean([r.cost_usd for r in with_ctx]):.5f} · sin = ${np.mean([r.cost_usd for r in no_ctx]):.5f} · latencia: {np.mean([r.latency_s for r in with_ctx]):.1f}s vs {np.mean([r.latency_s for r in no_ctx]):.1f}s")
''')
    md(box("idea", "Por qué importa", """
    Cada agente reenvía a su vecino «lo que ha aprendido», y ese texto se **vuelve a cobrar** como entrada en cada llamada posterior. En cadenas largas el coste crece de forma superlineal. Observabilidad útil: `gen_ai.usage.input_tokens` **por agente y por paso**, para ver qué eslabón engorda el contexto.
    """))

    # ------------------------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Cuando la propagación falla: trazas huérfanas

    Repetimos los reembolsos del lote (hasta 20) con tres configuraciones de propagación: `sdk` (propagador W3C del SDK), `manual` (nuestras funciones) y `none` (**nadie inyecta la cabecera**: el bug de «se me olvidó configurar el propagador» o «el cliente HTTP no está instrumentado»).
    """)
    code('''
rf20 = [t for t in tickets if t.intent_true == "refund" and t.order_id][:20]
rep = []
meshes = {}
for prop in ("sdk", "manual", "none"):
    m = build_mesh(mode="memory"); meshes[prop] = m
    rs = MultiAgentSupportOps(m, propagation=prop).run_many(rf20)
    rws = m.span_records()
    n_traces = len({r["trace_id"] for r in rws})
    orphans = [r for r in rws if r["parent_span_id"] is None and r["attributes"].get("gen_ai.operation.name") == "invoke_agent"]
    rep.append({"propagación": prop, "peticiones": len(rf20), "trazas generadas": n_traces, "trazas por petición": n_traces / len(rf20),
                "raíces huérfanas (invoke_agent sin padre)": len(orphans), "spans": len(rws)})
display(pd.DataFrame(rep).set_index("propagación").round(2))
''')
    code('''
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4))
r_ = pd.DataFrame(rep).set_index("propagación")
r_["trazas por petición"].plot.bar(ax=axes[0], color=[viz.PALETTE["logs"], viz.PALETTE["logs"], viz.PALETTE["error"]], rot=0)
axes[0].set_title("Trazas por petición (ideal = 1)"); axes[0].set_xlabel("")
one = meshes["none"].span_records(res_none_tid := [r for r in meshes["none"].span_records() if r["name"] == "invoke_workflow support_ticket"][0]["trace_id"])
waterfall_services(one, ax=axes[1], title="Con propagación=none solo queda el orquestador en la traza del ticket"); axes[1].figure.subplots_adjust(left=0.2)
plt.tight_layout(); plt.show()
n_orph = int(r_.loc["none", "raíces huérfanas (invoke_agent sin padre)"]); n_req = int(r_.loc["none", "peticiones"])
print(f"\\nSi buscaras UN reembolso por trace_id verías solo {len(one)} spans (la parte del orquestador); en total hay {n_orph} raíces huérfanas para {n_req} peticiones (≈ {n_orph / n_req:.1f} por petición), sin unir salvo por el ticket id.")
''')
    md(observe("""
    - Con `sdk` y `manual` hay **exactamente 1 traza por petición**: las dos implementaciones son equivalentes.
    - Con `none` cada subagente abre su propia traza: de 1 petición salen ≈ 4. Nada falla ni emite error: el síntoma es **estructural**.
    - La señal de detección más barata es **«raíces `invoke_agent` que no son el orquestador»** (en TraceQL: `{ span.gen_ai.operation.name = "invoke_agent" && nestedSetParent < 0 && resource.service.name != "supportops-orchestrator" }`). Un valor distinto de cero en un sistema sano es un bug de propagación.
    - Mientras no lo arregles, el único pegamento es un atributo común (`gen_ai.conversation.id` = ticket): úsalo como **segunda línea de correlación**, pero no sustituye al `trace_id` (no da jerarquía ni tiempos).
    """))

    # ------------------------------------------------------------------------------------------------------------- 8
    md("""
    ---
    # 8 · Colas y procesos reales: padre-hijo o *span link*

    Un especialista que consume tareas de una **cola** (Kafka, SQS, Redis…) corre en otro proceso y, a veces, horas después. Ahí hay dos formas de relacionar productor y consumidor, y la spec de mensajería (OpenTelemetry *messaging*) toma partido:

    | Opción | Qué es | Cuándo |
    |---|---|---|
    | **Span link** | El consumidor abre su **propia traza** y enlaza al contexto del productor | **Por defecto en la spec**: obligatorio en lotes (un consumidor procesa N mensajes de N trazas) |
    | **Padre-hijo** | El span `process` cuelga del contexto de creación del mensaje | La spec lo permite **solo para un mensaje por consumidor**; desaconseja usar el contexto de creación como padre del `process` en general |
    | Nada | Se ignoran las cabeceras | El bug de la sección 7 |

    Lo probamos con un especialista en un **proceso del sistema operativo distinto** (`RemoteAgentProcess`, `multiprocessing` con `spawn`): el productor publica un mensaje con las cabeceras, el worker construye **su propio** `TelemetryHandle` y devuelve sus spans.
    """)
    code('''
import os
prod_tracer = mesh.handle(ORCH).tracer()
rt = dataclasses.replace(refund, text=f"Estado del pedido {refund.order_id}", faults=[])      # tarea para orders-agent
modes = {}
try:
    with RemoteAgentProcess("orders-agent") as worker:
        for lm in ("parent", "link", "none"):
            t_pub = rt.created_at
            pub = prod_tracer.start_span("publish supportops.tasks", kind=SpanKind.PRODUCER, start_time=int(t_pub * 1e9), attributes={
                "messaging.system": "supportops-queue", "messaging.destination.name": "supportops.tasks", "messaging.operation.type": "send"})
            with otel_trace.use_span(pub, end_on_exit=False):
                headers = inject_sdk() if lm != "none" else {}
            pub.end(end_time=int((t_pub + 0.01) * 1e9))
            out = worker.call(rt, headers, t_pub + 1.5, link_mode=lm)       # el consumidor arranca 1,5 s (simulados) tras publicar
            modes[lm] = {"pub": pub, "out": out}
    PROC_OK = True
except Exception as e:                                                       # entornos sin multiprocessing (p. ej. algunos sandboxes)
    PROC_OK = False; print("No se pudo lanzar el proceso hijo:", type(e).__name__, e)

if PROC_OK:
    tab = []
    for lm, d in modes.items():
        cons = next(s for s in d["out"]["spans"] if s["kind"] == "CONSUMER")
        ptid = format(d["pub"].get_span_context().trace_id, "032x")
        tab.append({"modo": lm, "PID productor": os.getpid(), "PID consumidor": d["out"]["pid"], "¿misma traza?": cons["trace_id"] == ptid,
                    "¿padre = productor?": cons["parent_span_id"] == format(d["pub"].get_span_context().span_id, "016x"),
                    "enlaces": len(cons["links"]), "spans del worker": len(d["out"]["spans"])})
    display(pd.DataFrame(tab).set_index("modo"))
''')
    code('''
if PROC_OK:
    d = modes["parent"]
    pub_row = {"trace_id": format(d["pub"].get_span_context().trace_id, "032x"), "span_id": format(d["pub"].get_span_context().span_id, "016x"),
               "parent_span_id": None, "name": "publish supportops.tasks", "kind": "PRODUCER", "start_unix_nano": d["pub"].start_time,
               "end_unix_nano": d["pub"].end_time, "status": "UNSET", "attributes": {}, "resource": {"service.name": ORCH}}
    merged = [pub_row] + d["out"]["spans"]
    fig, ax = plt.subplots(figsize=(11, 4.4)); fig.subplots_adjust(left=0.33)
    waterfall_services(merged, ax=ax, title="Productor (proceso A) → cola → consumidor (proceso B): un hueco = tiempo en cola")
    plt.show()
    gap = (next(s for s in d["out"]["spans"] if s["kind"] == "CONSUMER")["start_unix_nano"] - d["pub"].end_time) / 1e9
    print(f"Tiempo en cola visible en la traza: {gap:.2f} s entre el fin de 'publish' y el inicio de 'process'.")
''')
    md(observe("""
    - **PID distintos, misma traza** en el modo `parent`: el contexto cruzó la frontera de proceso porque viajó **en el mensaje** (no en memoria compartida).
    - En `link` el consumidor tiene **otro** `trace_id` y un enlace al productor: Tempo no los dibuja anidados, pero puedes saltar de uno a otro por el enlace. Es lo correcto para lotes y para colas con latencia de horas (una traza que dura horas es difícil de muestrear y de leer).
    - El **hueco** entre `publish` y `process` es la *espera en cola*: invisible en métricas de agente y decisivo para el SLO de extremo a extremo.
    """))
    md(box("elite", "Por qué «padre-hijo» tiene un coste oculto", """
    Una traza se considera completa cuando deja de recibir spans (en Tempo, `max_trace_idle`; en *tail sampling*, el `decision_wait` del Collector). Si el consumidor procesa **horas** después y cuelga del productor, la traza queda abierta durante horas: el muestreo por cola tiene que **retener en memoria** todos esos spans (módulo 18). Los *links* desacoplan los ciclos de vida: cada traza se completa y se muestrea sola.
    """))

    # ------------------------------------------------------------------------------------------------------------- 9
    md("""
    ---
    # 9 · Fallos en cascada: reintentos, timeouts y trabajo zombi

    Un fallo en un nodo del árbol **se propaga hacia arriba** (error o lentitud) y **hacia abajo como carga** (reintentos). Dos mecanismos lo agravan:

    1. **Amplificación por reintentos.** Si cada nivel reintenta `r` veces, el nodo más profundo (nivel `d`) recibe hasta `(r+1)^d` intentos por cada petición original:

    $$A(d, r) = (r + 1)^{d}$$

    donde `d` es el número de niveles que reintentan de forma independiente y `r` los reintentos por nivel. Con 3 niveles y 2 reintentos cada uno: `3³ = 27` intentos contra la herramienta que ya estaba fallando.

    2. **Trabajo zombi.** Cuando el llamador abandona por *timeout*, el llamado **sigue trabajando** (y gastando tokens) salvo que se le cancele o tenga un *deadline*. Pagas dos veces: el intento abandonado y el reintento.
    """)
    code('''
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ds = np.arange(1, 5)
for r, col in zip((0, 1, 2, 3), ("#2f9e63", "#e0a100", "#e8833a", "#d64545")):
    ax.plot(ds, (r + 1) ** ds, marker="o", color=col, label=f"{r} reintentos por nivel")
ax.set_yscale("log"); ax.set_xticks(ds); ax.set_xlabel("niveles que reintentan (d)"); ax.set_ylabel("intentos sobre el nodo más profundo (log)")
ax.set_title("Amplificación de reintentos  A(d, r) = (r+1)^d"); ax.legend(); plt.show()
print("SupportOps (orquestador -> especialista -> herramienta): d = 2 niveles; con r = 2 en ambos, una herramienta caída recibe", (2 + 1) ** 2, "intentos por ticket")
''')
    md("""
    ## 9.1 El incidente

    Simulamos un fallo **persistente** en `issue_refund` (el proveedor de pagos tarda 9 s en vencer), durante una **ventana contigua** de reembolsos (la mitad central del lote), en `billing-agent`. El sub-agente tarda unos 14 s en total: **más** que el timeout del orquestador (12 s). Es el desajuste de plazos clásico: el llamador se rinde antes de que el llamado acabe su propio timeout.

    Comparamos cuatro políticas (`DelegationPolicy`):

    | Política | timeout | reintentos | disyuntor | *deadline* propagado y cancelación en vuelo |
    |---|---|---|---|---|
    | **A · sin límites** | 40 s | 0 | no | no |
    | **B · producción actual** | 12 s | 2 | no | no |
    | **C · plazos coherentes** | 6 s | 1 | no | **sí** |
    | **D · C + disyuntor** | 6 s | 1 | tras 3 fallos seguidos | **sí** |
    """)
    code('''
sa = SupportAgent()
rf_ok = [t for t in tickets if t.intent_true == "refund" and t.order_id and "issue_refund" in sa.run(dataclasses.replace(t, faults=[])).tools_used]
N_INC = 30 if FAST_DEV_RUN else 60
WINDOW = range(N_INC // 4, N_INC * 3 // 4)                    # el proveedor de pagos falla durante una ventana contigua (un incidente real)
BAD = [FaultSpec("tool_timeout", {"tool": "issue_refund", "timeout_s": 9.0, "agent": "billing-agent", "sticky": True})]
rf_inc = [dataclasses.replace(t, ticket_id=f"{t.ticket_id}-i{i}", created_at=SIM_EPOCH_S + i * 20, faults=BAD if i in WINDOW else [])
          for i, t in enumerate((rf_ok * N_INC)[:N_INC])]
POLICIES = {"A · sin límites": DelegationPolicy(timeout_s=40, max_retries=0),
            "B · producción": DelegationPolicy(timeout_s=12, max_retries=2),
            "C · plazos coherentes": DelegationPolicy(timeout_s=6, max_retries=1, propagate_deadline=True, cancel_in_flight=True),
            "D · C + disyuntor": DelegationPolicy(timeout_s=6, max_retries=1, propagate_deadline=True, cancel_in_flight=True, breaker_threshold=3)}
CASC, CASC_MESH = {}, {}
for name, pol in POLICIES.items():
    m = build_mesh(mode="memory"); CASC_MESH[name] = m
    CASC[name] = pd.DataFrame([r.to_row() for r in MultiAgentSupportOps(m, policy=pol).run_many(rf_inc)])
inc_mask = np.array([bool(t.faults) for t in rf_inc])
tab = pd.DataFrame({n: {"p95 latencia (s) · afectados": np.quantile(d.latency_s[inc_mask], .95), "intentos/ticket · afectados": d.attempts[inc_mask].mean(),
                        "coste medio (milésimas USD)": d.cost_usd.mean() * 1000, "trabajo zombi (s/ticket)": d.zombie_s.mean(),
                        "% degradados (sin resolver ni escalar)": (d.status == "degraded")[inc_mask].mean() * 100,
                        "% escalados a persona · afectados": (d.status == "escalated")[inc_mask].mean() * 100,
                        "tickets SANOS escalados (daño colateral)": int(((d.status == "escalated") & ~inc_mask).sum())}
                    for n, d in CASC.items()}).T
display(tab.round(2))
''')
    code('''
fig, axes = plt.subplots(1, 4, figsize=(15, 3.8))
cols = [viz.PALETTE["neutral"], viz.PALETTE["error"], viz.PALETTE["logs"], viz.PALETTE["traces"]]
for ax, (c, t) in zip(axes, [("p95 latencia (s) · afectados", "p95 de latencia (tickets afectados)"), ("intentos/ticket · afectados", "Intentos por ticket afectado"),
                             ("coste medio (milésimas USD)", "Coste medio por ticket"), ("trabajo zombi (s/ticket)", "Trabajo zombi (s por ticket)")]):
    ax.bar([n[:1] for n in tab.index], tab[c], color=cols); ax.set_title(t, fontsize=10)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **B (producción)** es la peor en latencia (p95 ≈ 44 s), intentos (6 por ticket afectado: 3 a facturación + 1 de cada pre-chequeo + el escalado) y coste, y es la única con trabajo zombi: timeout (12 s) < tiempo real del llamado (≈ 14 s) ⇒ *toda* delegación a `billing-agent` vence, se reintenta dos veces y cada intento abandonado **sigue gastando** hasta terminar.
    - **A** parece razonable (sin reintentos, sin zombi, coste bajo) pero deja al cliente esperando ≈ 20 s y termina **degradada** (ni resuelta ni escalada): un coste bajo no es una buena política si el ticket no se atiende. Fíjate en la columna «% degradados».
    - **C** acorta plazos y **cancela en vuelo** al vencer: no hay zombi y el ticket se **escala a una persona** (resuelto), con una latencia similar a A y menos coste que B. Pero reintenta un fallo **persistente**: un reintento es trabajo inútil.
    - **D** añade el disyuntor: tras 3 fallos seguidos deja de llamar a facturación y escala directamente (**fallo rápido**): la mejor latencia y el menor coste. Su precio está en la última columna: mientras el disyuntor sigue abierto (*cooldown*) escala también tickets **sanos** (daño colateral). Es el trade-off clásico: fallo rápido a cambio de falsos positivos.
    """))
    md("""
    ## 9.2 Causa raíz: recorrer la cadena de errores

    En una traza de la política B, ¿dónde nació el fallo? Los errores se propagan hacia arriba como `ERROR` en cada nivel; la **causa** es el span en error **más profundo** y el **síntoma visible** es el más alto. Recorremos el árbol:
    """)
    code('''
def error_chain(rows):
    """Cadena de spans ERROR de la raíz a la hoja más profunda: [(profundidad, nombre, servicio, error.type), ...]."""
    by_id = {r["span_id"]: r for r in rows}
    depth = lambda r: 0 if r["parent_span_id"] not in by_id else 1 + depth(by_id[r["parent_span_id"]])
    errs = sorted([r for r in rows if r["status"] == "ERROR"], key=depth)
    return [(depth(r), r["name"], r["resource"]["service.name"].replace("supportops-", ""), r["attributes"].get("error.type")) for r in errs]

mB = CASC_MESH["B · producción"]
bad_tid = next(r["trace_id"] for r in mB.span_records() if r["attributes"].get("error.type") == "timeout")
chain = error_chain(mB.span_records(bad_tid))
display(pd.DataFrame(chain, columns=["profundidad", "span", "servicio", "error.type"]).head(10))
sym, cause = chain[0], max(chain, key=lambda c: c[0])
print(f"SÍNTOMA (lo más alto): {sym[1]} [{sym[3]}] · CAUSA (lo más profundo): {cause[1]} en {cause[2]} [{cause[3]}]")
print(agent_tree_text(mB.span_records(bad_tid), ops=("invoke_workflow", "invoke_agent", "execute_tool")))
''')
    md(observe("""
    - El **síntoma** (CLIENT `timeout` en el orquestador) y la **causa** (`execute_tool issue_refund` → `timeout` en `billing-agent`) están en servicios distintos: sin la traza unida habría que adivinar. Con ella, el diagnóstico es una lectura del árbol.
    - Fíjate en que el span INTERNAL de `billing-agent` termina **después** del CLIENT: es el trabajo zombi, visible en la propia cascada.
    - Esta cadena de reintentos (tres intentos CLIENT al mismo agente y luego `escalation-agent`) es la **huella** de la tormenta de reintentos; la alerta barata es «`supportops.delegation.attempts` por ticket > 1,5».
    """))

    # ------------------------------------------------------------------------------------------------------------- 10
    md("""
    ---
    # 10 · Operarlo en Grafana (stack real)

    El dashboard **«11 · Multi-agente»** está provisionado como código en `stack/grafana/dashboards/11-multiagente.json` (uid `multiagent`). Contiene: tasa de delegaciones por agente y resultado, *error ratio* por agente, p95 de `gen_ai.invoke_agent.duration`, handoffs, tokens por servicio, una tabla Tempo de **trazas con error**, otra de **raíces huérfanas** y un panel de logs correlacionados.

    Las consultas clave (todas probadas contra el stack):

    | Panel | Fuente | Consulta |
    |---|---|---|
    | Delegaciones/s por agente y resultado | Prometheus | `sum by (gen_ai_agent_name, supportops_outcome) (rate(supportops_delegation_attempts_total[1m]))` |
    | p95 por agente | Prometheus | `histogram_quantile(0.95, sum by (le, gen_ai_agent_name) (rate(gen_ai_invoke_agent_duration_seconds_bucket[5m])))` |
    | Trazas con error por agente | Tempo (TraceQL) | `{ resource.service.name =~ "supportops-.*" && status = error && span.gen_ai.operation.name = "invoke_agent" }` |
    | **Huérfanos** (bug de propagación) | Tempo (TraceQL) | `{ span.gen_ai.operation.name = "invoke_agent" && nestedSetParent < 0 && resource.service.name != "supportops-orchestrator" }` |
    | Logs de una traza | Loki | `{service_name=~"supportops-.*"} \\| trace_id="<id>"` |
    """)
    code('''
if LIVE:
    live_mesh = build_mesh(mode="otlp", metric_interval_s=2.0)
    live_tk = generate_tickets(30 if FAST_DEV_RUN else 120, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, start_s="live", duration_s=300)
    live_sys = MultiAgentSupportOps(live_mesh, mode="delegate")
    live_res = live_sys.run_many(live_tk)
    # un poco de caos para que el dashboard tenga rojo: 6 reembolsos con facturación caída
    bad = [dataclasses.replace(t, faults=[FaultSpec("tool_timeout", {"tool": "issue_refund", "timeout_s": 9.0, "agent": "billing-agent", "sticky": True})]) for t in live_tk if t.intent_true == "refund" and t.order_id][:6]
    MultiAgentSupportOps(live_mesh, policy=DelegationPolicy(timeout_s=12, max_retries=2)).run_many(bad)
    # y 3 peticiones SIN propagación, para ver los huérfanos
    MultiAgentSupportOps(live_mesh, propagation="none").run_many([t for t in live_tk if t.intent_true == "order_status"][:3])
    live_mesh.force_flush(); print("enviadas", len(live_res) + len(bad) + 3, "peticiones al Collector · espera ~20-30 s a que Tempo las indexe")
else:
    print("Sin stack: arráncalo con `docker compose --profile core --profile metrics up -d` (desde stack/) y vuelve a ejecutar.")
''')
    code('''
import time
if LIVE:
    qs = {"trazas del workflow": '{ name = "invoke_workflow support_ticket" }',
          "con error (invoke_agent)": '{ resource.service.name =~ "supportops-.*" && status = error && span.gen_ai.operation.name = "invoke_agent" }',
          "huérfanos": '{ span.gen_ai.operation.name = "invoke_agent" && nestedSetParent < 0 && resource.service.name != "supportops-orchestrator" }'}
    t_end = time.time() + 60
    got = {}
    while time.time() < t_end:
        got = {k: backends.tempo_search(q, minutes=30, limit=50).get("traces", []) for k, q in qs.items()}
        if got["trazas del workflow"] and got["huérfanos"]: break
        time.sleep(4)
    print({k: len(v) for k, v in got.items()})
    if got["huérfanos"]:
        print("raíz de un huérfano:", got["huérfanos"][0].get("rootServiceName"), "·", got["huérfanos"][0].get("rootTraceName"))
''')
    code('''
if LIVE:
    prom = lambda q: backends.prom_query(q)
    try:
        r1 = prom('sum by (gen_ai_agent_name, supportops_outcome) (supportops_delegation_attempts_total)')
        display(pd.DataFrame([{**x["metric"], "valor": float(x["value"][1])} for x in r1])[["gen_ai_agent_name", "supportops_outcome", "valor"]].sort_values(["gen_ai_agent_name", "supportops_outcome"]))
    except Exception as e:
        print("Prometheus no disponible (¿perfil metrics?):", type(e).__name__)
''')
    md(observe("""
    - La tabla de **huérfanos** debe devolver las trazas del tramo `propagation="none"` (3 peticiones × ≈ 3 raíces) y **cero** en el resto: es una prueba de salud permanente de la propagación.
    - En Prometheus, `supportops_outcome="timeout"` solo aparece en `billing-agent`: la métrica ya te dice **qué agente** y la traza te dice **por qué**.
    - Abre Grafana (http://localhost:3000, `admin`/`admin`) → dashboard «11 · Multi-agente». Haz clic en un `trace_id` de la tabla para abrir la cascada: debes ver los 5 servicios.
    """))

    # ------------------------------------------------------------------------------------------------------------- 11
    md("""
    ---
    # 11 · Mapa de servicios (service graph) a partir de las trazas

    Tempo puede generar un *service graph* con el *metrics-generator* (módulo 07). Aquí lo calculamos a mano para entender qué es: cada arista `llamador → llamado` sale de un span CLIENT cuyo hijo está en otro servicio. Contamos llamadas y fallos:
    """)
    code('''
all_ = mesh_delegate.span_records()
by_id = {r["span_id"]: r for r in all_}
edges = {}
for r in all_:
    p = by_id.get(r["parent_span_id"])
    if p and p["kind"] == "CLIENT" and p["resource"]["service.name"] != r["resource"]["service.name"]:
        k = (p["resource"]["service.name"].replace("supportops-", ""), r["resource"]["service.name"].replace("supportops-", ""))
        e = edges.setdefault(k, {"llamadas": 0, "errores": 0, "dur": []})
        e["llamadas"] += 1; e["errores"] += p["status"] == "ERROR"; e["dur"].append((p["end_unix_nano"] - p["start_unix_nano"]) / 1e9)
G = pd.DataFrame([{"origen": a, "destino": b, "llamadas": v["llamadas"], "errores": v["errores"], "p95_s": np.quantile(v["dur"], .95)} for (a, b), v in edges.items()])
names = sorted(set(G.origen) | set(G.destino), key=lambda s: (s != "orchestrator", s))
M = G.pivot(index="origen", columns="destino", values="llamadas").reindex(index=names, columns=names).fillna(0)
fig, ax = plt.subplots(figsize=(6.4, 4.8))
im = ax.imshow(M.values, cmap="Blues"); ax.set_xticks(range(len(names)), names, rotation=35, ha="right"); ax.set_yticks(range(len(names)), names)
for i in range(len(names)):
    for j in range(len(names)):
        if M.values[i, j]: ax.text(j, i, int(M.values[i, j]), ha="center", va="center", color="white" if M.values[i, j] > M.values.max() / 2 else "black")
ax.set_xlabel("llamado"); ax.set_ylabel("llamador"); ax.set_title(f"Llamadas entre agentes · {len(res_delegate)} tickets"); ax.grid(False); plt.colorbar(im, label="llamadas"); plt.show()
display(G.sort_values("llamadas", ascending=False).round(2))
''')
    md(observe("""
    - Toda la actividad parte de la **fila** `orchestrator` (hub-and-spoke): una celda fuera de esa fila sería una dependencia directa entre especialistas que el diseño no prevé (candidata a revisar).
    - `billing` recibe solo los reembolsos; `escalation` recibe las escaladas y los *fallbacks*. La **columna** de un agente es su carga entrante: vigílala como cualquier servicio.
    """))

    # ------------------------------------------------------------------------------------------------------------- baggage
    md("""
    ---
    # 12 · Extra: *baggage* — llevar el «tier del cliente» a todos los saltos

    Además de `traceparent`, W3C define **baggage**: pares clave-valor que viajan con la petición. No se convierten en atributos solos: hace falta un procesador que copie las claves **permitidas** a los spans. Útil para analizar latencia **por tier** en todos los servicios sin pasar el dato como parámetro:
    """)
    code('''
from opentelemetry import baggage
from opentelemetry.sdk.trace import SpanProcessor
ALLOW = {"supportops.customer.tier"}                 # lista blanca: el baggage viaja a TODOS los servicios (y a terceros) -> nada sensible

class BaggageToAttributes(SpanProcessor):
    def on_start(self, span, parent_context=None):
        for k, v in baggage.get_all(parent_context).items():
            if k in ALLOW and k not in (span.attributes or {}):       # nunca pisar un atributo que el servicio ya fijó
                span.set_attribute(k, v)

mb = build_mesh(mode="memory")
for h in mb.handles.values(): h.tracer_provider.add_span_processor(BaggageToAttributes())
ctx = baggage.set_baggage("supportops.customer.tier", refund.tier, otel_context.get_current())
ctx = baggage.set_baggage("customer.email", "ana@example.com", ctx)             # NO permitido: no llegará a los spans... pero SÍ viaja en la cabecera
tok = otel_context.attach(ctx)
print("cabecera baggage que verían TODOS los servicios:", inject_sdk().get("baggage"))
mb_res = MultiAgentSupportOps(mb).run(refund)
otel_context.detach(tok)
sp = pd.DataFrame([{"servicio": r["resource"]["service.name"].replace("supportops-", ""), "op": r["attributes"].get("gen_ai.operation.name"),
                    "tier": r["attributes"].get("supportops.customer.tier")} for r in mb.span_records()])
display(sp.groupby("servicio").tier.agg(spans="size", con_tier=lambda s: s.notna().sum()))
print("¿llegó el email a algún span?", any("customer.email" in r["attributes"] for r in mb.span_records()))
''')
    md(observe("""
    - **Todos los servicios** (los 4 que participan) tienen ahora el atributo `supportops.customer.tier` también en los spans `chat` y `execute_tool` que no lo traían: podrías filtrar latencia **por tier en cualquier servicio** sin tocar su código.
    - El email **no** está en ningún span (lista blanca) pero **sí** viajó en la cabecera `baggage` a todos los saltos: el filtro de atributos no protege la cabecera. Quien reciba la petición (incluido un tercero) lo lee.
    """))
    md(box("warn", "Cuidado", """
    El baggage es **dato propagado, no verificado**: un cliente hostil puede enviar la cabecera con el valor que quiera (por ejemplo `tier=premium`). Úsalo para analítica de baja cardinalidad, nunca para decisiones de seguridad ni de facturación, y **nunca** con PII ni secretos. El procesador de arriba además respeta el atributo que el servicio ya fijó (no pisa la fuente de verdad).
    """))

    # ------------------------------------------------------------------------------------------------------------- prod
    md("""
    ---
    # 🏭 En producción

    - **Frameworks de agentes**: LangGraph, OpenAI Agents SDK, CrewAI, AutoGen, Google ADK… modelan los *handoffs* como herramientas de transferencia (como hicimos con `transfer_to_<agente>`) y varios se integran con OpenTelemetry. Verifica qué spans emiten y **si propagan contexto** al ejecutar herramientas en hilos o procesos.
    - **Anthropic** describe en su ingeniería del sistema de investigación multi-agente que el *tracing* de producción completo fue lo que permitió diagnosticar fallos de agentes, y que monitorizaron los **patrones de decisión y la estructura de interacción sin leer el contenido de las conversaciones** (privacidad): exactamente el enfoque de este módulo (estructura + atributos, no prompts).
    - **Google SRE** (cap. 22, *Addressing Cascading Failures*) trata los reintentos en capas, los plazos y el *load shedding*; **AWS Builders' Library** cubre timeouts, reintentos con *backoff* y *jitter*. Sus recomendaciones aplican tal cual a las delegaciones entre agentes: reintenta en **un solo nivel**, propaga plazos, limita con un presupuesto de reintentos.
    - **Grafana Tempo** correlaciona por `trace_id` y con el *service graph*/TraceQL estructural (`>>`, `>`, `nestedSetParent`) puedes preguntar «¿qué agentes llamó este agente?» sin salir de la UI.
    - **Escala**: en multi-agente el número de spans por petición se multiplica por el nº de agentes; presupuesta cardinalidad y volumen (módulo 18) y **muestrea por traza completa**, nunca por servicio.
    """)

    md(box("elite", "Secretos de la élite", """
    1. **La spec solo define el lado *cliente* de un agente remoto.** `invoke_agent` es CLIENT (remoto) o INTERNAL (en proceso), pero no dice cómo se llama el span del lado servidor. Decide una convención (aquí: el span propio de la ejecución, INTERNAL, hijo del CLIENT) y documéntala; si no, cada equipo dibuja el árbol distinto y las consultas TraceQL no se comparten. *Fuente: spec GenAI de agentes (estado Development).*
    2. **Cada llamada de inferencia se cuenta una sola vez en el árbol.** Si tu orquestador acumula en su span los tokens de sus hijos, sumar spans doblará el coste. La spec lo dice explícitamente al definir `gen_ai.invoke_agent.inference_calls`. Cuenta en las hojas `chat` (sección 6).
    3. **Un timeout del llamador no cancela al llamado.** Sin cancelación o *deadline* propagado el subagente sigue gastando tokens tras el abandono (nuestro `zombie_s`); y el reintento paga de nuevo. La fuga es invisible en la métrica del llamador y se ve en la traza como un hijo que termina **después** que su padre CLIENT.
    4. **Los reintentos multiplican; los plazos deben decrecer.** `A = (r+1)^d` (sección 9) y la regla del *deadline*: el plazo de cada nivel debe ser **menor** que el del nivel superior menos el margen de red; si el llamador espera 12 s a un llamado que puede tardar 14 s, todos los intentos fallan *por diseño*.
    5. **Para mensajería, la spec prefiere *links* a padres.** Padre-hijo solo para un mensaje por consumidor, y con el coste de dejar la traza abierta mientras dure la cola (afecta al muestreo por cola, módulo 18).
    6. **`ParentBased` o trazas rotas.** El bit `sampled` de `traceparent` es la decisión de muestreo de la raíz. Un servicio con `AlwaysOn` o `TraceIdRatio` independiente produce trazas con huecos, y un sistema multi-agente con 5 servicios sampleando al 10 % cada uno completa solo ≈ 0,001 % de las trazas (`0,1^5`).
    7. **El baggage no es un atributo ni un secreto.** Viaja a todos los saltos (también a terceros); copia a los spans solo una lista blanca y trátalo como dato **no verificado** (puede venir de un cliente hostil).
    8. **La alucinación se «lava» al sintetizar.** El orquestador reescribe la respuesta del especialista con tono seguro: el usuario no ve el fallo y, si la calidad se mide solo en el último `chat`, tampoco tu panel. Guarda las señales de calidad **por agente** (módulo 14) y propaga `grounded`/confianza hacia arriba como atributo.
    """))

    md(box("warn", "⚠️ Errores comunes", """
    - **Ejecutar herramientas o subagentes en un `ThreadPool`/`Process` sin llevar el contexto**: no hay error, hay trazas partidas (sección 3.1).
    - **Reintentar en cada capa** (orquestador, agente, SDK del LLM, cliente HTTP): `(r+1)^d`. Decide **un** nivel responsable.
    - **Timeout del llamador ≤ tiempo de peor caso del llamado**: toda llamada «lenta» fallará aunque el llamado funcione.
    - **Medir «la latencia del agente» con el span del orquestador** en una arquitectura de *handoff*: el trabajo real cuelga de otro span.
    - **Sumar todos los spans con `gen_ai.usage.*`** para el coste: doble contabilidad.
    - **Poner `ticket.id`/`customer.id` como etiqueta de métrica** para atribuir coste por cliente: cardinalidad (usa atributos de span/log y métricas con `tier`/`agent`/`model`).
    - **Fiarse del `traceparent` de entrada en un servicio público**: un cliente puede forzar `sampled=01` en todas sus peticiones (coste de ingesta) o reutilizar `trace_id`s. Decide a quién se confía el contexto remoto (módulo 12).
    """))

    # ------------------------------------------------------------------------------------------------------------- autoeval
    md("""
    ---
    # Autoevaluación
    """)
    md(details("1 · (Cálculo) Un orquestador reintenta 3 veces la llamada a un especialista, y el especialista reintenta 2 veces la herramienta. Si la herramienta está caída, ¿cuántos intentos recibe por ticket? ¿Y si solo reintenta el nivel del especialista?",
               "Intentos por nivel: orquestador `3+1 = 4`, especialista `2+1 = 3`. La herramienta recibe `4 × 3 = 12` intentos por ticket. Si solo reintenta el especialista: `3` (la mitad de la carga, mismo efecto de resiliencia para un fallo transitorio de la herramienta). Fórmula: `A = ∏ (r_i + 1)`."))
    md(details("2 · (Cálculo) Un ticket tiene 3 llamadas `chat` de 400 tokens de entrada cada una en `billing-agent` y 2 de 150 en el orquestador. Los spans `invoke_agent` repiten el total de sus hijos. Si sumas todos los spans con `gen_ai.usage.input_tokens` ¿qué total obtienes y qué error cometes?",
               "Hojas: `3·400 + 2·150 = 1500`. Los dos `invoke_agent` (billing: 1200; orquestador: 300) repiten 1500 más ⇒ total ingenuo `3000` (**+100 %**). Y si además el span `invoke_workflow` acumulase el árbol, sería `4500` (+200 %). Regla: contar solo hojas."))
    md(details("3 · (Diagnóstico) En Tempo ves una traza del orquestador que dura 4 s y, aparte, tres trazas de 5 s cuyo único span raíz es `invoke_agent billing-agent` (INTERNAL). No hay errores. ¿Qué ha pasado y cómo lo confirmas?",
               "El contexto no cruzó la frontera: el orquestador no inyectó `traceparent` (o el servicio de facturación no lo extrajo) y el subagente abrió una traza nueva. Se confirma con la consulta de huérfanos `{ span.gen_ai.operation.name = \"invoke_agent\" && nestedSetParent < 0 && resource.service.name != \"supportops-orchestrator\" }`, comprobando que `gen_ai.conversation.id` coincide con el del ticket y mirando las cabeceras de la llamada. Fix: instrumentar el cliente HTTP/cola o inyectar a mano."))
    md(details("4 · (Diagnóstico) El span CLIENT de la delegación a `billing-agent` muestra `error.type=timeout` a los 12,0 s, pero el span INTERNAL de `billing-agent` dura 14,3 s y el coste del ticket es 2× el de un ticket sano. ¿Qué mecanismo explica el coste y qué dos cambios lo reducen?",
               "Trabajo zombi más reintento: el llamador abandonó a los 12 s pero el llamado terminó a los 14,3 s (y gastó sus tokens), y el reintento volvió a pagar el flujo completo. Cambios: (1) **propagar el deadline** para que el subagente deje de iniciar llamadas nuevas al vencer (o cancelar explícitamente), y (2) **alinear plazos**: timeout del llamador > peor caso del llamado, o reducir el timeout interno de la herramienta; opcionalmente disyuntor/presupuesto de reintentos."))
    md(details("5 · (Transferencia) Diseñas un pipeline RAG con `retriever`, `reranker` y `generator` como servicios separados que se llaman por una cola de tareas. ¿Qué eliges: padre-hijo o *links* entre `publish` y `process`? ¿Qué atributos pondrías para correlacionar si usas links?",
               "Si el consumidor procesa de forma casi síncrona (milisegundos) y un mensaje por consumidor, padre-hijo da una cascada legible. Si hay latencia de cola variable, lotes o reintentos, usa **links** (traza propia por `process`) y correlaciona con un atributo común de negocio de baja cardinalidad en span/log (`gen_ai.conversation.id`/id de petición) más `messaging.message.id`. Además mide el tiempo en cola como métrica propia (`process.start − publish.end`)."))
    md(details("6 · (Recuerdo) ¿Por qué en el handoff el span del especialista no cuelga del orquestador y qué consecuencia tiene para el dashboard?",
               "Porque el orquestador transfirió el control y su span ya terminó; el especialista continúa como *hermano* bajo el workflow. Consecuencia: la latencia/errores del «agente de entrada» no incluyen el trabajo real; la SLI de extremo a extremo debe medirse en el span raíz (`invoke_workflow`) o en el último agente, no en el orquestador."))
    md(details("7 · (Transferencia) Tu sistema multi-agente tiene 5 servicios y cada uno muestrea al 20 % de forma independiente. ¿Qué fracción de las trazas queda completa y qué política corrige el problema?",
               "Completa solo si los 5 muestrean: `0,2^5 = 0,032 %`. Corrección: decidir **una vez en la raíz** y propagar el bit `sampled` (`ParentBased` en los demás), o muestrear por cola en el Collector con la traza entera (módulo 18)."))

    md("""
    ---
    # Referencias

    - W3C, *Trace Context* (Recomendación, 2021) — <https://www.w3.org/TR/trace-context/> · W3C, *Baggage* — <https://www.w3.org/TR/baggage/>
    - OpenTelemetry, *GenAI semantic conventions: agent and framework spans* y *GenAI metrics* (estado Development) — <https://github.com/open-telemetry/semantic-conventions-genai> (carpeta `docs/gen-ai/`).
    - OpenTelemetry, *Semantic conventions for messaging spans* (productor/consumidor, links frente a padre-hijo) — <https://github.com/open-telemetry/semantic-conventions/blob/main/docs/messaging/messaging-spans.md>
    - OpenTelemetry, *Context propagation* y *Sampling* (conceptos) — <https://opentelemetry.io/docs/concepts/context-propagation/> · <https://opentelemetry.io/docs/concepts/sampling/>
    - Anthropic Engineering, *How we built our multi-agent research system* (2025) — <https://www.anthropic.com/engineering/multi-agent-research-system>
    - Kim et al., *Towards a Science of Scaling Agent Systems* (2025), arXiv:2512.08296 — <https://arxiv.org/abs/2512.08296>
    - Google SRE Book, cap. 22 *Addressing Cascading Failures* — <https://sre.google/sre-book/addressing-cascading-failures/>
    - Amazon Builders' Library, *Timeouts, retries and backoff with jitter* — <https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/>
    - Grafana Labs, *TraceQL* (selectores, `nestedSetParent` y consultas estructurales) — <https://grafana.com/docs/tempo/latest/traceql/>
    """)

    nb.save(out)


# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "11_proyecto_multiagente.ipynb", "Proyecto 11 · SupportOps multi-agente: trazar de extremo a extremo y contener una cascada")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 11 · SupportOps multi-agente: trazar un reembolso de extremo a extremo y contener una cascada

    | | |
    |---|---|
    | **Nivel** | 🟠 Avanzado |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno obligatorio (todo se evalúa en memoria). Opcional: `--profile core` para mirar tus trazas en Grafana (paso final) |
    | **RAM aproximada** | < 600 MB (sin stack) |
    | **Prerrequisitos** | Lección `11_multiagente` (propagación W3C, orquestador, cascadas) |
    | **Conexión** | Reutiliza `supportops.multiagent` (sobre el `OTelInstrumentor` del módulo 03) y deja listo el sistema que el módulo 12 (MCP) y el 13 (costes) siguen ampliando |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. El equipo migró a multi-agente hace una semana y el on-call reporta tres cosas:

    1. **Reembolsos que tardan más de 40 s** y acaban escalados a una persona, justo cuando el proveedor de pagos tuvo una caída.
    2. **Subagentes que aparecen como trazas sueltas** en Tempo desde que `orders-agent` empezó a consumir de una cola.
    3. **El coste por ticket se ha multiplicado** y nadie sabe si es el modelo grande, los reintentos o el contexto.

    Tu trabajo: **(a)** propagar el contexto por la cola, **(b)** detectar trazas huérfanas, **(c)** atribuir el coste sin contar dos veces, **(d)** encontrar la causa raíz y el **trabajo zombi** del incidente, **(e)** cuantificar el desperdicio y **(f)** elegir una política de delegación que contenga la cascada.

    ## Datos

    Todo es sintético y determinista (semilla 42, modo `mock`, tiempo simulado): el **Paso 0** te entrega tres lotes ya ejecutados con `MultiAgentSupportOps` y la telemetría de **todos** los servicios en memoria (`mesh.span_records()`, esquema `SPAN_SCHEMA` + `links`):

    | Lote | Qué es |
    |---|---|
    | `ROWS_OK`, `RES_OK` | 20 reembolsos sin fallos, propagación correcta |
    | `ROWS_NONE` | los mismos 20 reembolsos con la propagación **rota** (`propagation="none"`) |
    | `ROWS_B`, `RES_B`, `WL` | el **incidente**: 30 reembolsos, ventana de fallos en `issue_refund`, política de **producción** (timeout 12 s, 2 reintentos) |

    Cadena de datos: stack local (opcional) → memoria. No hace falta Docker para obtener la nota.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `publish` / `consume` | En 10 mensajes y los modos `parent` y `link`: trazas, padres, enlaces, tipo de span y **espera en cola** como la spec | 10/10 en ambos modos |
    | R2 | `find_orphans`, `fragmentation` | En `ROWS_NONE`: nº de raíces huérfanas y trazas por petición; en `ROWS_OK`: 0 y 1,0 | coincidencia exacta |
    | R3 | `leaf_totals`, `naive_totals` | Tokens por servicio = los de `RES_OK` (0 de error) y el total ingenuo ≈ 2× (doble contabilidad) | exacto / ratio 2,00 ± 0,02 |
    | R4 | `root_cause`, `zombie_seconds` | La causa raíz y el síntoma de **todas** las trazas con timeout; segundos zombi = los medidos por el sistema | 100 % / ± 0,05 s |
    | R5 | `amplification` | Intentos a facturación por ticket afectado (esperado: los de la política de producción) y fracción del gasto desperdiciada en intentos abandonados | exacto / ± 0,01 |
    | R6 | `MY_POLICY` | Con **tu** política, sobre el mismo incidente: p95 de afectados ≤ 20 s, coste ≤ 7,5 milésimas USD/ticket (la de producción gasta ≈ 10,5), 0 degradados/error, 0 zombi, ≤ 5 tickets sanos escalados | todas a la vez |

    > 📏 Los umbrales salen de la solución de referencia (y de las políticas B/C/D de la lección), medida con las semillas 42, 7 y 99: no dependen de tu máquina (el tiempo es simulado).
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_11 + '''
from opentelemetry.context import Context
from opentelemetry.trace import Link
from supportops.multiagent import span_rows
from supportops.telemetry import setup_telemetry
''')

    md("""
    ## Paso 0 · Los tres lotes (te lo damos hecho)

    El incidente: durante una **ventana contigua** el proveedor de pagos hace que `issue_refund` tarde 9 s en vencer (fallo **persistente** en `billing-agent`). Ejecutamos el mismo lote con la política de producción.
    """)
    code('''
sa = SupportAgent()
pool = generate_tickets(120, seed=SEED, fault_rates=None)
rf_ok = [t for t in pool if t.intent_true == "refund" and t.order_id and "issue_refund" in sa.run(t).tools_used]
def lote(n, t0=SIM_EPOCH_S, window=None):
    bad = [FaultSpec("tool_timeout", {"tool": "issue_refund", "timeout_s": 9.0, "agent": "billing-agent", "sticky": True})]
    return [dataclasses.replace(t, ticket_id=f"{t.ticket_id}-p{i}", created_at=t0 + i * 20, faults=bad if (window and i in window) else [])
            for i, t in enumerate((rf_ok * n)[:n])]

def ejecuta(tickets, policy=None, propagation="sdk"):
    mesh = build_mesh(mode="memory")
    res = MultiAgentSupportOps(mesh, policy=policy, propagation=propagation).run_many(tickets)
    return res, mesh.span_records()

OK_TK = lote(20)
RES_OK, ROWS_OK = ejecuta(OK_TK)
_, ROWS_NONE = ejecuta(OK_TK, propagation="none")
WL = lote(30, window=range(7, 22))
AFFECTED = np.array([bool(t.faults) for t in WL])
POLICY_B = DelegationPolicy(timeout_s=12, max_retries=2)
RES_B, ROWS_B = ejecuta(WL, POLICY_B)
print(f"OK: {len(RES_OK)} tickets · {len(ROWS_OK)} spans | NONE: {len(ROWS_NONE)} spans | INCIDENTE: {len(RES_B)} tickets ({AFFECTED.sum()} afectados) · {len(ROWS_B)} spans")
dfB = pd.DataFrame([r.to_row() for r in RES_B]); display(dfB[AFFECTED].head(3)[["ticket_id", "status", "latency_s", "attempts", "timeouts", "cost_usd", "zombie_s"]].round(3))
''')

    # ---------------------------------------------------------------------------------- paso 1
    md("""
    ## Paso 1 · Propagar el contexto por una cola (productor y consumidor)

    `orders-agent` consume tareas de una cola. Escribe las dos mitades. Reglas (spec de mensajería de OpenTelemetry, estudiadas en la sección 8 de la lección):

    - **`publish(tracer, queue, payload, t_s)`**: abre un span **PRODUCER** de nombre `publish {queue}` (atributos `messaging.system="supportops-queue"`, `messaging.destination.name=queue`, `messaging.operation.type="send"`) que **empieza** en `t_s` y **termina** en `t_s + 0.01`; **inyecta** `traceparent` (`inject_manual`) con ese span activo, y devuelve el mensaje `{"payload", "headers", "queue", "published_at_s": t_s + 0.01, "message_id"}`.
    - **`consume(tracer, msg, mode, start_s, duration_s)`**: abre un span **CONSUMER** `process {queue}` (atributos `messaging.system`, `messaging.destination.name`, `messaging.operation.type="process"`, `messaging.message.id`) entre `start_s` y `start_s + duration_s`. En `mode="parent"` es **hijo** del productor; en `mode="link"` abre una **traza nueva** (raíz) con un **span link** al productor. Si `mode` no es válido, lanza `ValueError`.
    """)
    md(hint(1, "El contexto remoto se obtiene con `extract_manual(msg['headers'])`. Para «traza nueva» usa `context=Context()` (contexto vacío) al crear el span; para el link necesitas el `SpanContext` del productor: `otel_trace.get_current_span(contexto_extraído).get_span_context()`."))
    md(hint(2, "`tracer.start_span(nombre, context=..., kind=SpanKind.CONSUMER, links=[Link(span_context)], start_time=int(t*1e9), attributes={...})`; cierra con `span.end(end_time=int(t_fin*1e9))`. Para inyectar con el productor activo: `with otel_trace.use_span(span, end_on_exit=False): headers = inject_manual()`."))
    code('''
def publish(tracer, queue: str, payload: dict, t_s: float) -> dict:
    # TODO 1a
    raise NotImplementedError("TODO 1a")

def consume(tracer, msg: dict, mode: str, start_s: float, duration_s: float):
    # TODO 1b
    raise NotImplementedError("TODO 1b")

try:
    prod, cons = setup_telemetry("supportops-orchestrator", mode="memory", set_global=False), setup_telemetry("supportops-orders-agent", mode="memory", set_global=False)
    m = publish(prod.tracer(), "supportops.tasks", {"order": "ORD-00001"}, 100.0)
    consume(cons.tracer(), m, "parent", 101.5, 1.0)
    print(m["headers"]); display(pd.DataFrame(span_rows(prod) + span_rows(cons))[["name", "kind", "trace_id", "parent_span_id"]])
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 2
    md("""
    ## Paso 2 · Detectar trazas huérfanas

    **TODO 2.** Escribe:

    - `find_orphans(rows)`: la lista de **spans raíz `invoke_agent`** (sin `parent_span_id`, `gen_ai.operation.name == "invoke_agent"`) cuyo servicio **no** es `supportops-orchestrator`.
    - `fragmentation(rows, n_requests)`: **trazas por petición** (nº de `trace_id` distintos / peticiones). Ideal: 1,0.
    """)
    md(hint(1, "El servicio está en `row['resource']['service.name']` y la operación en `row['attributes']['gen_ai.operation.name']`. Una traza = un `trace_id`."))
    code('''
def find_orphans(rows: list[dict]) -> list[dict]:
    # TODO 2a
    raise NotImplementedError("TODO 2a")

def fragmentation(rows: list[dict], n_requests: int) -> float:
    # TODO 2b
    raise NotImplementedError("TODO 2b")

try:
    for nombre, rws in (("ROWS_OK", ROWS_OK), ("ROWS_NONE", ROWS_NONE)):
        print(f"{nombre}: huérfanos={len(find_orphans(rws))} · trazas/petición={fragmentation(rws, 20):.2f}")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 3
    md("""
    ## Paso 3 · Atribuir el coste sin contar dos veces

    **TODO 3.** Escribe:

    - `leaf_totals(rows)`: por **servicio** (`service.name`), `{"calls", "input_tokens", "output_tokens"}` contando **solo** los spans `chat` (hojas).
    - `naive_totals(rows)`: el total **ingenuo** de tokens de entrada: suma de `gen_ai.usage.input_tokens` de **todos** los spans que lo traen.
    """)
    md(hint(1, "Filtra por `attributes['gen_ai.operation.name'] == 'chat'`. Los atributos de uso pueden faltar (un `chat` que falló no los tiene): usa `.get(..., 0) or 0`."))
    code('''
def leaf_totals(rows: list[dict]) -> dict[str, dict[str, int]]:
    # TODO 3a
    raise NotImplementedError("TODO 3a")

def naive_totals(rows: list[dict]) -> int:
    # TODO 3b
    raise NotImplementedError("TODO 3b")

try:
    LT = leaf_totals(ROWS_OK); print({k.replace("supportops-", ""): v for k, v in LT.items()})
    print("ingenuo / hojas =", round(naive_totals(ROWS_OK) / sum(v["input_tokens"] for v in LT.values()), 2))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 4
    md("""
    ## Paso 4 · Causa raíz y trabajo zombi del incidente

    **TODO 4.** Escribe, sobre las filas de **una** traza del incidente:

    - `error_chain(rows)`: lista de tuplas `(profundidad, nombre, servicio_corto, error.type)` de los spans con `status == "ERROR"`, ordenada por profundidad (el servicio corto es el nombre sin el prefijo `supportops-`).
    - `root_cause(rows)`: devuelve `(sintoma, causa)`; cada uno es `(nombre, servicio_corto, error.type)`. **Síntoma** = el error **más alto** del árbol; **causa** = el **más profundo**. Si no hay errores, `(None, None)`.

    Y sobre las filas de **todo el lote**:

    - `zombie_seconds(rows)`: suma de segundos que los subagentes siguieron trabajando **después** de que su llamador (span CLIENT con `error.type == "timeout"`) abandonara: para cada uno de esos CLIENT, `max(fin_del_hijo − fin_del_CLIENT, 0)` (el hijo es el span cuyo `parent_span_id` es el del CLIENT).
    """)
    md(hint(1, "Profundidad: sube por `parent_span_id` hasta llegar a la raíz (`by_id = {r['span_id']: r for r in rows}`). Las trazas de una lista de filas se separan con `trace_id`."))
    md(hint(2, "Estructura: `errs = sorted([r for r in rows if r['status']=='ERROR'], key=depth)`; síntoma = `errs[0]`, causa = `errs[-1]`. Para el zombi: indexa los hijos por padre y recorre los CLIENT en error `timeout`."))
    code('''
def error_chain(rows: list[dict]) -> list[tuple]:
    # TODO 4a
    raise NotImplementedError("TODO 4a")

def root_cause(rows: list[dict]):
    # TODO 4b
    raise NotImplementedError("TODO 4b")

def zombie_seconds(rows: list[dict]) -> float:
    # TODO 4c
    raise NotImplementedError("TODO 4c")

try:
    tid = next(r["trace_id"] for r in ROWS_B if r["attributes"].get("error.type") == "timeout")
    print(root_cause([r for r in ROWS_B if r["trace_id"] == tid]))
    print(f"zombi total: {zombie_seconds(ROWS_B):.2f} s (el sistema midió {sum(r.zombie_s for r in RES_B):.2f} s)")
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 5
    md("""
    ## Paso 5 · Cuantificar el desperdicio

    **TODO 5.** `amplification(rows, n_affected)` devuelve un `dict` con:

    - `attempts_per_ticket`: nº de spans CLIENT `invoke_agent billing-agent` **de las trazas que contienen algún `timeout`**, dividido por `n_affected` (los tickets afectados por la ventana).
    - `wasted_cost_share`: fracción del coste total de los `chat` que se gastó **dentro de intentos abandonados**, es decir, en el subárbol de un CLIENT con `error.type == "timeout"`. Precio: `supportops.pricing.cost_usd(modelo, tokens_in, tokens_out)` con el modelo de `gen_ai.response.model`.
    - `theoretical`: `(r+1)^d` con `r = 2` reintentos y `d = 1` nivel que reintenta (los intentos que *debería* recibir facturación según la política).
    """)
    md(hint(1, "Un `chat` pertenece a un subárbol abandonado si alguno de sus **ancestros** es un CLIENT con `error.type == 'timeout'`. Calcula el conjunto de `span_id` de esos CLIENT y sube por los padres de cada `chat`."))
    code('''
from supportops.pricing import cost_usd

def amplification(rows: list[dict], n_affected: int) -> dict:
    # TODO 5
    raise NotImplementedError("TODO 5")

try:
    print(amplification(ROWS_B, int(AFFECTED.sum())))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ---------------------------------------------------------------------------------- paso 6
    md("""
    ## Paso 6 · Contener la cascada: tu política

    **TODO 6.** Diseña `MY_POLICY = DelegationPolicy(...)` para el **mismo incidente**. Parámetros: `timeout_s`, `max_retries`, `backoff_s`, `breaker_threshold`, `breaker_cooldown_s`, `propagate_deadline`, `cancel_in_flight`, `fallback_to_human`.
    Objetivos (los comprueba la rúbrica): bajar el **p95 de los tickets afectados**, bajar el **coste**, **no dejar tickets degradados ni en error**, **cero trabajo zombi** y **limitar el daño colateral** (tickets sanos escalados por error).
    Piensa: ¿qué plazo es coherente con un especialista cuyo peor caso son 14 s? ¿Tiene sentido reintentar un fallo **persistente**? ¿Qué cuesta un disyuntor que tarda en cerrarse?
    """)
    md(hint(1, "El plazo del llamador debe poder **cortar** al llamado (no esperar su timeout interno de 9 s): pon un `timeout_s` claramente por debajo de 14 s y activa `propagate_deadline` y `cancel_in_flight` para no dejar trabajo zombi."))
    md(hint(2, "Los reintentos no ayudan en un fallo persistente: `max_retries=0` o 1. Para que el ticket no se quede degradado, deja `fallback_to_human=True`. El disyuntor (`breaker_threshold` ≥ 2) convierte los fallos repetidos en *fallo rápido*; un `breaker_cooldown_s` largo escala tickets sanos."))
    code('''
MY_POLICY = None
# TODO 6: MY_POLICY = DelegationPolicy(...)

if MY_POLICY is None:
    print("Pendiente: define MY_POLICY")
else:
    res_m, _ = ejecuta(WL, MY_POLICY)
    d = pd.DataFrame([r.to_row() for r in res_m])
    print(f"p95 afectados={np.quantile(d.latency_s[AFFECTED], .95):.1f}s · coste medio={d.cost_usd.mean() * 1000:.2f} milésimas USD · estados={d.status.value_counts().to_dict()}")
''')

    # ---------------------------------------------------------------------------------- rúbrica
    md("""
    ## Paso 7 · Rúbrica
    """)
    code('''
REF = {"orphans_none": 60, "frag_none": 4.0, "n_timeout_traces": 15, "attempts_per_ticket": 3.0, "wasted_share": 0.6719,
       "max_p95": 20.0, "max_cost": 7.5, "max_collateral": 5}     # calibrado con la solución (semillas 42, 7, 99)

def run_rubric():
    rows = []
    def add(r, d, ok, det=""): rows.append({"criterio": r, "descripción": d, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": det})
    # R1
    try:
        ok = {"parent": 0, "link": 0}
        for mode in ("parent", "link"):
            for i in range(10):
                p = setup_telemetry("supportops-orchestrator", mode="memory", set_global=False); c = setup_telemetry("supportops-orders-agent", mode="memory", set_global=False)
                t0 = 1000.0 + 10 * i
                m = publish(p.tracer(), "supportops.tasks", {"i": i}, t0)
                consume(c.tracer(), m, mode, t0 + 0.01 + 2.5, 1.0)
                ps, cs = span_rows(p)[0], span_rows(c)[0]
                good = (ps["kind"] == "PRODUCER" and ps["name"] == "publish supportops.tasks" and cs["kind"] == "CONSUMER" and cs["name"] == "process supportops.tasks"
                        and ps["attributes"].get("messaging.operation.type") == "send" and cs["attributes"].get("messaging.operation.type") == "process"
                        and abs((cs["start_unix_nano"] - ps["end_unix_nano"]) / 1e9 - 2.5) < 1e-3 and abs((cs["end_unix_nano"] - cs["start_unix_nano"]) / 1e9 - 1.0) < 1e-3
                        and "traceparent" in m["headers"] and abs(m["published_at_s"] - (t0 + 0.01)) < 1e-9)
                if mode == "parent":
                    good = good and cs["trace_id"] == ps["trace_id"] and cs["parent_span_id"] == ps["span_id"] and not cs["links"]
                else:
                    good = good and cs["trace_id"] != ps["trace_id"] and cs["parent_span_id"] is None and len(cs["links"]) == 1 and cs["links"][0]["span_id"] == ps["span_id"]
                ok[mode] += bool(good)
        try: consume(setup_telemetry("x", mode="memory", set_global=False).tracer(), m, "otro", 0, 1); bad_mode = False
        except ValueError: bad_mode = True
        add("R1", "publish/consume: parent y link correctos en 10/10 y ValueError con modo inválido", ok == {"parent": 10, "link": 10} and bad_mode, f"{ok} · ValueError={bad_mode}")
    except Exception as e: add("R1", "publish/consume", False, f"{type(e).__name__}: {e}")
    # R2
    try:
        o_none, o_ok = find_orphans(ROWS_NONE), find_orphans(ROWS_OK)
        f_none, f_ok = fragmentation(ROWS_NONE, 20), fragmentation(ROWS_OK, 20)
        ok = len(o_none) == REF["orphans_none"] and len(o_ok) == 0 and abs(f_none - REF["frag_none"]) < 1e-6 and abs(f_ok - 1.0) < 1e-6
        add("R2", "huérfanos y trazas por petición (NONE vs OK)", ok, f"huérfanos NONE={len(o_none)} (ref {REF['orphans_none']}) · trazas/pet NONE={f_none:.2f} (ref {REF['frag_none']:.2f}) · OK={len(o_ok)}/{f_ok:.2f}")
    except Exception as e: add("R2", "huérfanos", False, f"{type(e).__name__}: {e}")
    # R3
    try:
        lt = leaf_totals(ROWS_OK)
        tin, tout = sum(v["input_tokens"] for v in lt.values()), sum(v["output_tokens"] for v in lt.values())
        ratio = naive_totals(ROWS_OK) / tin
        ok = tin == sum(r.input_tokens for r in RES_OK) and tout == sum(r.output_tokens for r in RES_OK) and abs(ratio - 2.0) < 0.02 and sum(v["calls"] for v in lt.values()) == sum(r.n_llm_calls for r in RES_OK)
        add("R3", "totales por hojas = totales del sistema; ingenuo ≈ 2×", ok, f"hojas={tin}+{tout} (sistema {sum(r.input_tokens for r in RES_OK)}+{sum(r.output_tokens for r in RES_OK)}) · ratio={ratio:.2f}")
    except Exception as e: add("R3", "totales", False, f"{type(e).__name__}: {e}")
    # R4
    try:
        tids = sorted({r["trace_id"] for r in ROWS_B if r["attributes"].get("error.type") == "timeout"})
        good = 0
        for t in tids:
            sym, cause = root_cause([r for r in ROWS_B if r["trace_id"] == t])
            good += sym == ("invoke_agent billing-agent", "orchestrator", "timeout") and cause == ("execute_tool issue_refund", "billing-agent", "timeout")
        z, zr = zombie_seconds(ROWS_B), sum(r.zombie_s for r in RES_B)
        add("R4", "causa raíz y síntoma en el 100 % de las trazas con timeout; zombi ± 0,05 s", len(tids) == REF["n_timeout_traces"] and good == len(tids) and abs(z - zr) <= 0.05 and zr > 0, f"{good}/{len(tids)} trazas · zombi={z:.2f}s vs {zr:.2f}s")
    except Exception as e: add("R4", "causa raíz y zombi", False, f"{type(e).__name__}: {e}")
    # R5
    try:
        a = amplification(ROWS_B, int(AFFECTED.sum()))
        ok = abs(a["attempts_per_ticket"] - REF["attempts_per_ticket"]) < 1e-9 and abs(a["wasted_cost_share"] - REF["wasted_share"]) <= 0.01 and a["theoretical"] == 3
        add("R5", "amplificación: intentos por ticket, desperdicio y (r+1)^d", ok, f"{a} · ref intentos={REF['attempts_per_ticket']} desperdicio≈{REF['wasted_share']:.3f}")
    except Exception as e: add("R5", "amplificación", False, f"{type(e).__name__}: {e}")
    # R6
    try:
        assert MY_POLICY is not None, "define MY_POLICY"
        res_m, _ = ejecuta(WL, MY_POLICY); d = pd.DataFrame([r.to_row() for r in res_m])
        m = {"p95": np.quantile(d.latency_s[AFFECTED], .95), "coste": d.cost_usd.mean() * 1000, "malos": int(d.status.isin(["degraded", "error"]).sum()),
             "zombi": d.zombie_s.sum(), "colateral": int(((d.status == "escalated") & ~AFFECTED).sum())}
        checks = {f"p95 afectados ≤ {REF['max_p95']} s": m["p95"] <= REF["max_p95"], f"coste ≤ {REF['max_cost']:.2f} milésimas": m["coste"] <= REF["max_cost"],
                  "0 degradados/error": m["malos"] == 0, "zombi = 0": m["zombi"] == 0, f"colateral ≤ {REF['max_collateral']}": m["colateral"] <= REF["max_collateral"]}
        add("R6", "tu política contiene la cascada", all(checks.values()), f"{ {k: bool(v) for k, v in checks.items()} } · medido: p95={m['p95']:.1f}s coste={m['coste']:.2f} malos={m['malos']} zombi={m['zombi']:.1f} colateral={m['colateral']}")
    except Exception as e: add("R6", "política", False, f"{type(e).__name__}: {e}")
    return pd.DataFrame(rows).set_index("criterio")
''')
    code('''
# Ejecuta esta celda cuando hayas terminado los TODO
display(run_rubric())
''')

    md("""
    ---
    ## Paso final (opcional) · Míralo en Grafana

    Con el stack arriba (`docker compose --profile core --profile metrics up -d`), repite el lote del incidente con `build_mesh(mode="otlp")` y `generate_tickets(..., start_s="live")` (los tiempos de `lote()` usan el origen simulado de 2026: Tempo rechazaría esos datos tan antiguos; cambia `t0=` a `time.time() - 600`). Abre el dashboard **«11 · Multi-agente»** y comprueba:

    1. El panel de **huérfanos** está a cero con `propagation="sdk"` y se llena con `"none"`.
    2. `supportops_outcome="timeout"` solo en `billing-agent`.
    3. Pulsa un `trace_id` de la tabla de errores y localiza **a ojo** el síntoma y la causa que tu `root_cause` devolvió.

    ---
    ## Retos extra (nivel experto)

    1. **Handoff:** repite el incidente con `mode="handoff"`. ¿Cambia la causa raíz? ¿Qué span usarías ahora como «latencia de la petición» y por qué?
    2. **Presupuesto de reintentos:** implementa un limitador (cubo de fichas) que permita reintentar como mucho el 10 % de las delegaciones en los últimos 60 s simulados y compáralo con el disyuntor.
    3. **Consulta TraceQL de la cascada:** escribe (y prueba en Tempo) la consulta que devuelve las trazas con ≥ 3 CLIENT `invoke_agent billing-agent` (pista: `count()` sobre un selector con `kind = client`).
    4. **Servicio de grafo:** calcula el *service graph* del incidente (llamadas y errores por arista) y compáralo con el de `ROWS_OK`.
    5. **Detección temprana:** diseña una alerta sobre `supportops.delegation.attempts` por ticket (¿qué umbral y ventana detectan el incidente en < 2 min con ≤ 1 falso positivo en el lote sano?).

    ## Reflexión (producción e hilo conductor)

    - En tu política, ¿qué parte del ahorro viene de **no reintentar** y cuál de **cancelar en vuelo**? ¿Qué dato de la traza te lo demuestra?
    - ¿Cómo cambia el diseño si `billing-agent` **no** soporta cancelación (la operación de pago es no idempotente)? ¿Qué riesgos de duplicar un reembolso aparecen al reintentar y cómo los vigilarías con telemetría?
    - El módulo 12 sustituye las herramientas locales por **servidores MCP remotos**: ¿qué fronteras nuevas de propagación y de timeout se añaden al árbol que acabas de analizar?
    - El módulo 13 atribuirá coste por cliente, feature y modelo: ¿qué atributos faltan hoy en los spans para hacerlo sin cardinalidad explosiva?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine las funciones y vuelve a lanzar la rúbrica).
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
def publish(tracer, queue, payload, t_s):
    span = tracer.start_span(f"publish {queue}", kind=SpanKind.PRODUCER, start_time=int(t_s * 1e9), attributes={
        "messaging.system": "supportops-queue", "messaging.destination.name": queue, "messaging.operation.type": "send", "messaging.operation.name": "publish"})
    with otel_trace.use_span(span, end_on_exit=False):
        headers = inject_manual()
    span.end(end_time=int((t_s + 0.01) * 1e9))
    return {"payload": payload, "headers": headers, "queue": queue, "published_at_s": t_s + 0.01,
            "message_id": "msg-" + format(span.get_span_context().span_id, "016x")[:8]}

def consume(tracer, msg, mode, start_s, duration_s):
    if mode not in ("parent", "link"):
        raise ValueError("mode debe ser 'parent' o 'link'")
    remote = extract_manual(msg["headers"])
    if mode == "parent":
        ctx, links = remote, []
    else:
        ctx, links = Context(), [Link(otel_trace.get_current_span(remote).get_span_context())]
    span = tracer.start_span(f"process {msg['queue']}", context=ctx, kind=SpanKind.CONSUMER, links=links, start_time=int(start_s * 1e9), attributes={
        "messaging.system": "supportops-queue", "messaging.destination.name": msg["queue"], "messaging.operation.type": "process",
        "messaging.message.id": msg["message_id"]})
    span.end(end_time=int((start_s + duration_s) * 1e9))
    return span

def _svc(r): return r["resource"].get("service.name", "?")
def _op(r): return r["attributes"].get("gen_ai.operation.name")

def find_orphans(rows):
    return [r for r in rows if r["parent_span_id"] is None and _op(r) == "invoke_agent" and _svc(r) != "supportops-orchestrator"]

def fragmentation(rows, n_requests):
    return len({r["trace_id"] for r in rows}) / n_requests

def leaf_totals(rows):
    out = {}
    for r in rows:
        if _op(r) != "chat": continue
        d = out.setdefault(_svc(r), {"calls": 0, "input_tokens": 0, "output_tokens": 0})
        d["calls"] += 1
        d["input_tokens"] += r["attributes"].get("gen_ai.usage.input_tokens", 0) or 0
        d["output_tokens"] += r["attributes"].get("gen_ai.usage.output_tokens", 0) or 0
    return out

def naive_totals(rows):
    return sum(r["attributes"].get("gen_ai.usage.input_tokens", 0) or 0 for r in rows)

def error_chain(rows):
    by_id = {r["span_id"]: r for r in rows}
    def depth(r):
        d = 0
        while r["parent_span_id"] in by_id:
            r, d = by_id[r["parent_span_id"]], d + 1
        return d
    errs = sorted([r for r in rows if r["status"] == "ERROR"], key=depth)
    return [(depth(r), r["name"], _svc(r).replace("supportops-", ""), r["attributes"].get("error.type")) for r in errs]

def root_cause(rows):
    ch = error_chain(rows)
    if not ch: return None, None
    return ch[0][1:], ch[-1][1:]

def zombie_seconds(rows):
    kids = {}
    for r in rows: kids.setdefault(r["parent_span_id"], []).append(r)
    total = 0.0
    for r in rows:
        if r["kind"] == "CLIENT" and r["attributes"].get("error.type") == "timeout":
            for k in kids.get(r["span_id"], []):
                total += max(k["end_unix_nano"] - r["end_unix_nano"], 0) / 1e9
    return total

def amplification(rows, n_affected):
    by_id = {r["span_id"]: r for r in rows}
    dead = {r["span_id"] for r in rows if r["kind"] == "CLIENT" and r["attributes"].get("error.type") == "timeout"}
    def abandoned(r):
        while r["parent_span_id"] in by_id:
            r = by_id[r["parent_span_id"]]
            if r["span_id"] in dead: return True
        return False
    total = wasted = 0.0
    for r in rows:
        if _op(r) != "chat": continue
        a = r["attributes"]
        c = cost_usd(a.get("gen_ai.response.model") or a.get("gen_ai.request.model", ""), a.get("gen_ai.usage.input_tokens", 0) or 0, a.get("gen_ai.usage.output_tokens", 0) or 0)
        total += c; wasted += c if abandoned(r) else 0.0
    bad_traces = {r["trace_id"] for r in rows if r["attributes"].get("error.type") == "timeout"}
    n_bill = sum(1 for r in rows if r["kind"] == "CLIENT" and r["name"] == "invoke_agent billing-agent" and r["trace_id"] in bad_traces)
    return {"attempts_per_ticket": n_bill / n_affected, "wasted_cost_share": wasted / total, "theoretical": (2 + 1) ** 1}

MY_POLICY = DelegationPolicy(timeout_s=6, max_retries=0, propagate_deadline=True, cancel_in_flight=True, breaker_threshold=2, breaker_cooldown_s=40)
display(run_rubric())
''')

    nb.save(out)


# =====================================================================================================================
def build_readme() -> None:
    readme = '''# Módulo 11 · Observabilidad de sistemas multi-agente

🟠 **Avanzado** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

SupportOps pasa de **un agente** a un **orquestador + 4 especialistas** (`orders`, `billing`, `knowledge`, `escalation`).
Cada agente es un *servicio* con su propio `service.name` y `TelemetryHandle`; el reto es ver **una petición de extremo a
extremo**, atribuir coste sin contar dos veces y contener fallos en cascada.

## Objetivos
1. Modelar un sistema multi-agente como árbol de spans (`invoke_workflow` → `invoke_agent` → `chat`/`execute_tool`) y distinguir **delegación** de **handoff**.
2. Implementar **a mano** la propagación W3C `traceparent` (validación estricta, inyección, extracción) y compararla con el SDK; entender el **baggage**.
3. Demostrar la pérdida de contexto (hilos, colas, procesos) y detectar **trazas huérfanas**.
4. Propagar contexto por una cola entre **dos procesos reales** y elegir entre padre-hijo y *span link*.
5. Calcular el **camino crítico**, el ahorro del *fan-out* y el coste por agente (**solo hojas**, sin doble contabilidad).
6. Cuantificar la **amplificación de reintentos** y el **trabajo zombi**; comparar políticas (timeout, reintentos, disyuntor, *deadline*).
7. Diagnosticar la **causa raíz** recorriendo la cadena de errores.

## Contenido
| Archivo | Qué es |
|---|---|
| `11_multiagente.ipynb` | Lección (12 secciones, 12 gráficos, TraceQL/PromQL probados, 🧠 de élite, autoevaluación) |
| `11_proyecto_multiagente.ipynb` | Proyecto: propagar por una cola, detectar huérfanos, atribuir coste, causa raíz + zombi, elegir política (rúbrica calibrada, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/multiagent.py` | Código del módulo: `build_mesh`, `MultiAgentSupportOps`, `DelegationPolicy`, `RemoteAgentProcess`, W3C a mano, análisis de trazas |
| `../stack/grafana/dashboards/11-multiagente.json` | Dashboard «11 · Multi-agente» como código (uid `multiagent`) |

## Servicios necesarios
- **Sin Docker** (modo degradado, telemetría en memoria): todo salvo la sección 10 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d` (≈ 1,2 GB de RAM). Grafana: http://localhost:3000 (`admin`/`admin`).

## Lecturas
- W3C *Trace Context* y *Baggage* · OpenTelemetry *GenAI semantic conventions* (agentes, estado Development) y *messaging spans*.
- Anthropic Engineering, *How we built our multi-agent research system* · Kim et al., *Towards a Science of Scaling Agent Systems* (arXiv:2512.08296).
- Google SRE Book, cap. 22 *Addressing Cascading Failures* · Amazon Builders' Library, *Timeouts, retries and backoff with jitter*.

## Cómo se conecta
Antes: módulos 03 (SDK, `OTelInstrumentor`), 04 (GenAI semconv), 07-10 (TraceQL, LogQL, métricas, Grafana). Después: el módulo 12 sustituye herramientas locales
por **servidores MCP remotos** (nuevas fronteras de propagación y timeout) y el 13 usa el desglose por agente/modelo para el **FinOps**.
'''
    (COURSE / MOD / "README.md").write_text(readme, encoding="utf-8")
    print("OK README", MOD)


if __name__ == "__main__":
    build_lesson()
    build_project()
    build_readme()
