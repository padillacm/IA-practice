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
    - **Una sola traza** cruza cinco servicios (cinco colores). Sin la propagación del contexto serían cinco trazas sueltas y nadie sabría que pertenecen a la misma petición.
    - Los dos pre-chequeos (naranja claro y verde) **empiezan a la vez**; `billing-agent` no arranca hasta que termina el más lento. Fíjate en que cada delegación aparece **dos veces** con el mismo nombre: el CLIENT del orquestador (lo que el llamador ve, incluidos timeouts) y el INTERNAL del servicio (lo que hizo por dentro). Si difieren en duración, la diferencia es red, cola o abandono.
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
    col = viz.PALETTE["metrics"] if r["kind"] == "CLIENT" else viz.PALETTE["traces"]
    ax.barh(i, du, left=st, color=col, alpha=0.9, height=0.6)
    lab = ("chat · " + r["attributes"]["gen_ai.request.model"]) if r["kind"] == "CLIENT" and r["resource"]["service.name"] == ORCH and "gen_ai.request.model" in r["attributes"] else r["name"].replace("invoke_agent ", "→ ")
    ax.text(st + du + 0.05, i, f"{lab}  {du:.2f}s", va="center", fontsize=8)
ax.set_yticks([]); ax.invert_yaxis(); ax.set_xlabel("tiempo desde el inicio (s)"); ax.set_title("Línea de tiempo del orquestador: pre-chequeos en paralelo, luego facturación, luego síntesis")
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

    Repetimos 20 reembolsos con tres configuraciones de propagación: `sdk` (propagador W3C del SDK), `manual` (nuestras funciones) y `none` (**nadie inyecta la cabecera**: el bug de «se me olvidó configurar el propagador» o «el cliente HTTP no está instrumentado»).
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
print("\\nSi buscaras el reembolso por trace_id verías esto (", len(one), "spans ) y los subagentes aparecerían como", len(r_) and int(r_.loc['none', 'raíces huérfanas (invoke_agent sin padre)']), "trazas sueltas, sin forma de unirlas salvo por el ticket id.")
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
rt = refund
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

    Simulamos un fallo **persistente** en `issue_refund` (el proveedor de pagos tarda 9 s en vencer), solo para el 50 % de los reembolsos, en `billing-agent`. El sub-agente tarda unos 14 s en total: **más** que el timeout del orquestador (12 s). Es el desajuste de plazos clásico: el llamador se rinde antes de que el llamado acabe su propio timeout.

    Comparamos cuatro políticas (`DelegationPolicy`):

    | Política | timeout | reintentos | disyuntor | propagar *deadline* |
    |---|---|---|---|---|
    | **A · sin límites** | 40 s | 0 | no | no |
    | **B · producción actual** | 12 s | 2 | no | no |
    | **C · plazos coherentes** | 6 s | 1 | no | **sí** |
    | **D · C + disyuntor** | 6 s | 1 | tras 3 fallos | **sí** |
    """)
    code('''
rf_inc = [t for t in tickets if t.intent_true == "refund" and t.order_id and "issue_refund" in SupportAgent().run(dataclasses.replace(t, faults=[])).tools_used]
rf_inc = (rf_inc * 4)[: (16 if FAST_DEV_RUN else 40)]
rf_inc = [dataclasses.replace(t, ticket_id=f"{t.ticket_id}-i{i}", created_at=t.created_at + i * 20, faults=(
    [FaultSpec("tool_timeout", {"tool": "issue_refund", "timeout_s": 9.0, "agent": "billing-agent", "sticky": True})] if i % 2 == 0 else [])) for i, t in enumerate(rf_inc)]
POLICIES = {"A · sin límites": DelegationPolicy(timeout_s=40, max_retries=0),
            "B · producción": DelegationPolicy(timeout_s=12, max_retries=2),
            "C · plazos coherentes": DelegationPolicy(timeout_s=6, max_retries=1, propagate_deadline=True),
            "D · C + disyuntor": DelegationPolicy(timeout_s=6, max_retries=1, propagate_deadline=True, breaker_threshold=3)}
CASC, CASC_MESH = {}, {}
for name, pol in POLICIES.items():
    m = build_mesh(mode="memory"); CASC_MESH[name] = m
    CASC[name] = pd.DataFrame([r.to_row() for r in MultiAgentSupportOps(m, policy=pol).run_many(rf_inc)])
inc_mask = np.array([bool(t.faults) for t in rf_inc])
tab = pd.DataFrame({n: {"p95 latencia (s)": np.quantile(d.latency_s[inc_mask], .95), "intentos/ticket (afectados)": d.attempts[inc_mask].mean(),
                        "coste medio (milésimas USD)": d.cost_usd.mean() * 1000, "trabajo zombi (s/ticket)": d.zombie_s.mean(),
                        "% escalados": (d.status == "escalated").mean() * 100, "% error": (d.status == "error").mean() * 100}
                    for n, d in CASC.items()}).T
display(tab.round(2))
''')
    code('''
fig, axes = plt.subplots(1, 4, figsize=(15, 3.8))
cols = [viz.PALETTE["neutral"], viz.PALETTE["error"], viz.PALETTE["logs"], viz.PALETTE["traces"]]
for ax, (c, t) in zip(axes, [("p95 latencia (s)", "p95 de latencia (tickets afectados)"), ("intentos/ticket (afectados)", "Intentos por ticket afectado"),
                             ("coste medio (milésimas USD)", "Coste medio por ticket"), ("trabajo zombi (s/ticket)", "Trabajo zombi (s por ticket)")]):
    ax.bar([n[:1] for n in tab.index], tab[c], color=cols); ax.set_title(t, fontsize=10)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **B (producción)** es la peor en intentos, coste y zombi: timeout (12 s) < tiempo real del llamado (≈ 14 s) ⇒ *toda* delegación a `billing-agent` vence, se reintenta dos veces y cada intento abandonado **sigue gastando**. Además la latencia sube a ≈ 30 s antes de escalar a un humano.
    - **A** parece «mejor» (no hay reintentos ni zombi) pero deja al cliente esperando ≈ 18 s con una respuesta **degradada** sin escalar: lo barato aquí es lo peor para el usuario. Una política no se juzga solo por coste.
    - **C** acorta plazos y **propaga el deadline**: los subagentes dejan de iniciar llamadas nuevas al vencer (se ven como spans `deadline_exceeded` de duración ≈ 0) y el zombi baja.
    - **D** añade el disyuntor: tras 3 fallos seguidos deja de intentar facturación y escala directamente (**fallo rápido**). Es la mejor en latencia y coste para el incidente, a cambio de no probar un servicio que quizá ya se recuperó (mitigado por el *cooldown*).
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
            if k in ALLOW: span.set_attribute(k, v)

mb = build_mesh(mode="memory")
for h in mb.handles.values(): h.tracer_provider.add_span_processor(BaggageToAttributes())
ctx = baggage.set_baggage("supportops.customer.tier", "premium", otel_context.get_current())
ctx = baggage.set_baggage("customer.email", "ana@example.com", ctx)             # NO permitido: no debe llegar a los spans
tok = otel_context.attach(ctx)
mb_res = MultiAgentSupportOps(mb).run(dataclasses.replace(refund, tier="standard"))
otel_context.detach(tok)
tiers = pd.Series([r["attributes"].get("supportops.customer.tier") for r in mb.span_records()]).value_counts(dropna=False)
print("valores de supportops.customer.tier en los spans:\\n", tiers.to_string())
print("¿filtró el email?", any("customer.email" in r["attributes"] for r in mb.span_records()))
''')
    md(box("warn", "Cuidado", """
    El baggage de este ejemplo solo vive dentro del proceso; en una frontera real se serializa en la cabecera `baggage` y la reciben **todos** los servicios aguas abajo, incluidos terceros (un LLM proveedor, un CDN). Nunca metas PII ni secretos. Y observa que el `tier` del ticket («standard») y el del baggage («premium») pueden discrepar: el baggage es **dato propagado, no verificado**.
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
