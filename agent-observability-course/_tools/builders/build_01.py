"""Genera el módulo 01_agente_base: README, lección y proyecto.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_01.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "01_agente_base"


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "01_agente_base.ipynb", "Módulo 01 · El agente base: SupportOps v0, proveedor agnóstico, tráfico y fallos")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 01 · El agente base: SupportOps v0, proveedor agnóstico, tráfico y fallos

    | | |
    |---|---|
    | **Nivel** | 🟢 Básico |
    | **Duración estimada** | ≈ 4 h 20 min (lección ≈ 2 h 30 min + proyecto ≈ 1 h 50 min) |
    | **Servicios de Compose** | **Ninguno** (todo es simulado y corre en Python). Funciona igual en Colab |
    | **RAM aproximada** | < 300 MB (solo el kernel de Python) |
    | **Prerrequisitos** | Módulo 00 (mapa del stack, «Docker listo ≠ arrancado», las cinco grietas del monitoreo clásico) |
    | **Hilo conductor** | Aquí nace **SupportOps v0**: el agente de soporte que instrumentarás a partir del módulo 03 |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Definir** qué es un agente (bucle LLM + herramientas) y distinguirlo de una llamada simple y de un *workflow*.
    2. **Implementar a mano** el bucle de un agente en ≈ 25 líneas y **leer** el de `SupportAgent`.
    3. **Calcular** cómo crecen los tokens de entrada y el coste con el número de pasos (efecto cuadrático del contexto).
    4. **Cambiar de proveedor LLM** (`mock | anthropic | openai | ollama`) solo con variables de entorno, sin tocar el agente.
    5. **Describir** la base de conocimiento (RAG con TF-IDF) y las herramientas de SupportOps, y **distinguir** error de negocio de error de infraestructura.
    6. **Generar** tráfico sintético reproducible (semilla, esquema, ventanas de incidente) y **ejecutarlo** a través del agente.
    7. **Inyectar** siete tipos de fallo y **explicar** qué huella deja cada uno en latencia, tokens, estado y calidad.
    8. **Identificar** los puntos de extensión donde se instrumentará el agente (módulo 03).
    """)

    md("""
    ## 🔁 Conexión con el módulo anterior

    Responde de memoria; luego abre la respuesta.
    """)
    md(details("1 · ¿Por qué «Up» en `docker compose ps` no basta para saber si Loki puede recibir logs?",
               "Porque *arrancado* ≠ *listo*: Loki tardó ≈ 17 s en responder `200` en `/ready` (y Pyroscope ≈ 1 minuto). Se verifica con el *readiness*, idealmente con una señal canario de extremo a extremo."))
    md(details("2 · Cita dos de las cinco «grietas» del monitoreo clásico con agentes.",
               "Por ejemplo: la longitud de la cadena es variable (bucles de herramientas) y «200 OK» ya no significa éxito (respuestas inventadas con estado `ok`). Las otras: latencia de cola pesada, coste ∝ tokens y fallos parciales silenciosos."))
    md(details("3 · ¿Quién habla con los backends (Tempo, Loki, Prometheus): la app o el Collector?",
               "El **Collector**: la app solo envía OTLP al Collector (`:4317` gRPC / `:4318` HTTP) y este reparte cada señal a su backend."))

    code(boot("viz"))
    code(IMPORTS + '''
_ = check_stack([])   # este módulo NO necesita servicios: solo muestra el estado por si quieres tenerlos levantados
''')

    # ---------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · ¿Qué es un agente?

    ## 1.1 Intuición: quién decide el siguiente paso

    Anthropic, en su guía [«Building effective agents»](https://www.anthropic.com/engineering/building-effective-agents) (dic. 2024), distingue dos tipos de «sistemas agénticos»:

    - **Workflows**: *LLMs y herramientas orquestados por caminos de código predefinidos* — el programador decide el orden.
    - **Agentes**: *sistemas donde el LLM dirige dinámicamente su propio proceso y el uso de herramientas* — el modelo decide el orden.

    Y resume su implementación así: suelen ser **«LLMs usando herramientas según el feedback del entorno, en un bucle»**; además es habitual incluir **condiciones de parada** (p. ej. un número máximo de iteraciones).
    La misma guía avisa de que la autonomía implica **mayor coste y posibilidad de errores acumulados**. Esas dos frases son, literalmente, el motivo de este curso.

    | Si vienes de… | Analogía |
    |---|---|
    | **ML** | Un *pipeline* (workflow) es un `Pipeline.fit/predict` de sklearn con pasos fijos; un agente es una **política** que, en cada estado, elige la siguiente acción (como en aprendizaje por refuerzo, pero con un LLM como política y sin entrenamiento) |
    | **Backend** | Un workflow es un orquestador con un DAG fijo; un agente es un *servicio que decide a quién llamar en tiempo de ejecución* |
    | **SRE** | El grafo de dependencias del servicio **no está en el código**: cambia con cada petición, así que el *runbook* clásico («si cae X, mira Y») no basta |
    """)

    code('''
fig, ax = viz.canvas(12, 4.6, (0, 100), (0, 40))
cols = [(2, "1 · Llamada al LLM", viz.PALETTE["neutral"]), (35, "2 · Workflow\\n(el código decide)", viz.PALETTE["logs"]), (68, "3 · Agente\\n(el LLM decide)", viz.PALETTE["traces"])]
for x, title, c in cols:
    ax.text(x + 14, 37, title, ha="center", va="top", fontsize=11, fontweight="bold", color=c)
# 1
a = viz.box(ax, 4, 16, 10, 6, "Entrada", c := viz.PALETTE["neutral"]); b = viz.box(ax, 18, 16, 10, 6, "LLM", c, bold=True)
viz.arrow(ax, viz.right(a), viz.left(b)); ax.text(16, 10, "una sola llamada;\\nsin herramientas", ha="center", fontsize=9)
# 2
c = viz.PALETTE["logs"]; w1 = viz.box(ax, 36, 17, 10, 6, "LLM:\\nclasifica", c); w2 = viz.box(ax, 52, 24, 12, 5, "if pedido:", c, fontsize=8)
w3 = viz.box(ax, 52, 16, 12, 5, "get_order()", c, fontsize=8); w4 = viz.box(ax, 52, 8, 12, 5, "search_kb()", c, fontsize=8)
viz.arrow(ax, viz.right(w1), viz.left(w2)); viz.arrow(ax, viz.right(w1), viz.left(w3)); viz.arrow(ax, viz.right(w1), viz.left(w4))
ax.text(49, 1.5, "caminos fijos en el código;\\nel LLM rellena huecos", ha="center", fontsize=9)
# 3
c = viz.PALETTE["traces"]; g1 = viz.box(ax, 70, 20, 11, 8, "LLM", c, bold=True); g2 = viz.box(ax, 87, 26, 11, 5, "tool A", c, fontsize=8); g3 = viz.box(ax, 87, 18, 11, 5, "tool B", c, fontsize=8)
g4 = viz.box(ax, 87, 10, 11, 5, "respuesta", c, fontsize=8)
viz.arrow(ax, viz.right(g1), viz.left(g2)); viz.arrow(ax, viz.right(g1), viz.left(g3)); viz.arrow(ax, viz.right(g1), viz.left(g4))
viz.arrow(ax, (g2[0] + 5, g2[1] + 6), (g1[0] + 5, g1[1] + 8.6), "", c, rad=0.5, dashed=True); viz.arrow(ax, (g3[0], g3[1] + 5.2), (g1[0] + 11.4, g1[1] + 1), "", c, rad=-0.3, dashed=True)
ax.text(83, 1.5, "el LLM elige qué herramienta y\\ncuántas veces: bucle", ha="center", fontsize=9)
plt.show()
''')
    md(observe("""
    - De izquierda a derecha **aumenta la autonomía… y la incertidumbre**: en 1 hay un único punto de fallo; en 2 el grafo de llamadas es *conocido* (puedes dibujarlo en tiempo de diseño); en 3 el grafo **se decide en ejecución**.
    - La observabilidad de un agente (3) tiene que *reconstruir* ese grafo a partir de lo que ocurrió — por eso necesitaremos trazas. Para (1) y (2) bastaban métricas y logs clásicos.
    - Regla práctica de la guía de Anthropic: usa la solución **más simple** que funcione; los agentes intercambian latencia y coste por mejor rendimiento en la tarea.
    """))

    md("""
    ## 1.2 Una llamada simple al LLM (nivel 1)

    Usamos la capa de proveedor del curso. Por defecto es el **modo `mock`**: un LLM simulado, determinista y sin coste (lo estudiamos en la sección 2).
    Una llamada recibe mensajes y devuelve una respuesta **normalizada**.
    """)
    code('''
llm = get_llm()                                   # LLM_PROVIDER=mock → MockLLM("mock-small")
resp = llm.chat([Message("user", "¿Cuántos años de garantía tienen los productos?")], system="Eres un asistente de soporte.",
                call_key=("demo", 0))
print("proveedor/modelo :", resp.provider, "/", resp.model)
print("finish_reason     :", resp.finish_reason, "(¿pide herramientas?:", bool(resp.tool_calls), ")")
print("tokens (in/out)   :", resp.usage.input_tokens, "/", resp.usage.output_tokens)
print("latencia simulada :", resp.latency_s, "s")
print("contenido         :", repr(resp.content[:80]))
print("tool_calls        :", [(c.name, c.arguments) for c in resp.tool_calls])
''')
    md("""
    Sin herramientas, el modelo **no puede consultar la base de conocimiento**: aquí el mock decide que necesita `search_kb`, así que `finish_reason="tool_calls"` y no hay texto. Eso es el germen del agente: la respuesta **no es el final**, es una *petición de acción*.

    ## 1.3 El bucle del agente, a mano (≈ 25 líneas)

    Antes de usar `SupportAgent`, escribamos el bucle desde cero con un «modelo de juguete» (un guion) y una calculadora segura. Fíjate en la **lista de mensajes**: es la única memoria del agente.
    """)
    code('''
import ast, operator

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
def calculadora(expr: str) -> float:
    """Evalúa aritmética básica SIN usar eval() (nunca evalúes texto que viene de un LLM)."""
    def ev(n):
        if isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in OPS: return OPS[type(n.op)](ev(n.left), ev(n.right))
        raise ValueError("expresión no permitida")
    return ev(ast.parse(expr, mode="eval").body)

def modelo_de_juguete(mensajes):
    """Sustituye al LLM: guion fijo «17*23 + 5». Devuelve ('tool', nombre, args) o ('final', texto)."""
    herramientas_usadas = [m for m in mensajes if m["role"] == "tool"]
    if len(herramientas_usadas) == 0: return ("tool", "calculadora", {"expr": "17*23"})
    if len(herramientas_usadas) == 1: return ("tool", "calculadora", {"expr": f"{herramientas_usadas[0]['content']}+5"})
    return ("final", f"El resultado es {herramientas_usadas[-1]['content']}.")

def agente_minimo(pregunta: str, max_pasos: int = 5):
    mensajes = [{"role": "user", "content": pregunta}]              # 1) memoria = lista de mensajes
    for paso in range(max_pasos):                                   # 2) condición de parada: máximo de iteraciones
        accion = modelo_de_juguete(mensajes)                        # 3) el «LLM» decide
        if accion[0] == "final":                                    # 4a) si no pide herramientas → terminamos
            return accion[1], mensajes
        _, nombre, args = accion                                    # 4b) si pide una herramienta → la ejecutamos
        resultado = calculadora(**args)
        mensajes.append({"role": "assistant", "content": f"{nombre}({args})"})
        mensajes.append({"role": "tool", "content": str(resultado)})   # 5) el resultado vuelve a la memoria
    return "No he podido terminar (máximo de pasos)", mensajes

respuesta, hist = agente_minimo("¿Cuánto es 17*23 + 5?")
for m in hist: print(f"{m['role']:>9}: {m['content']}")
print("\\nRESPUESTA FINAL:", respuesta)
''')
    code('''
fig, ax = viz.canvas(12, 4.2, (0, 100), (0, 38))
mem = viz.box(ax, 3, 14, 17, 10, "Mensajes\\n(la memoria del\\nagente)", viz.PALETTE["neutral"], bold=True)
llm_ = viz.box(ax, 29, 14, 14, 10, "LLM", viz.PALETTE["traces"], bold=True)
dec = viz.box(ax, 51, 14, 16, 10, "¿pide\\nherramientas?", viz.PALETTE["warn"])
tool = viz.box(ax, 51, 1, 16, 8, "Ejecutar\\nherramienta", viz.PALETTE["logs"], bold=True)
fin = viz.box(ax, 78, 14, 17, 10, "Respuesta\\nfinal", viz.PALETTE["ok"], bold=True)
guard = viz.box(ax, 36, 28, 28, 7, "guarda: max_steps (condición de parada)", viz.PALETTE["error"], fontsize=8)
viz.arrow(ax, viz.right(mem), viz.left(llm_), "prompt")
viz.arrow(ax, viz.right(llm_), viz.left(dec), "respuesta"); viz.arrow(ax, viz.right(dec), viz.left(fin), "no")
viz.arrow(ax, viz.bottom(dec), viz.top(tool), "sí", viz.PALETTE["logs"])
viz.arrow(ax, (tool[0] - 0.3, tool[1] + 4), (mem[0] + 8.5, mem[1] - 0.4), "", viz.PALETTE["logs"], rad=-0.3)
ax.text(30, 4.2, "el resultado de la herramienta\\nse añade a los mensajes", color=viz.PALETTE["logs"], fontsize=8, ha="center")
viz.arrow(ax, (guard[0] + 3, guard[1] - 0.3), (dec[0] + 3, dec[1] + 10.4), "", viz.PALETTE["error"], dashed=True)
plt.show()
''')
    md(observe("""
    - El agente es un `for` con una condición de parada: **no hay magia**, solo un LLM dentro de un bucle y una lista que crece.
    - Cada vuelta del ciclo *Mensajes → LLM → herramienta → Mensajes* es **un paso**. Cada paso = una llamada al modelo (latencia + tokens + dinero) y, a menudo, una llamada a un sistema externo (que puede fallar).
    - Sin la guarda `max_steps`, un modelo que nunca emite una respuesta final **gastaría tokens para siempre**. Esa guarda es tu primer control de coste (y su activación es una señal que querremos observar).
    """))

    md("""
    ## 1.4 SupportOps v0: el mismo bucle, con proveedor, herramientas y reintentos

    `SupportAgent` (en `supportops/agent.py`) es el mismo bucle más lo necesario para producción: proveedor LLM intercambiable, registro de herramientas con esquema, **reintentos** ante errores 5xx/429,
    control de pasos, cálculo de tokens y coste, y *ganchos* para instrumentación (que de momento no hacen nada). Veamos el núcleo del código real:
    """)
    code('''
import inspect
src = inspect.getsource(SupportAgent.run).splitlines()
a = next(i for i, l in enumerate(src) if "for step in range" in l)
print("\\n".join(src[a:a + 26]))
print("   ...")
''')
    md("""
    Probemos las cuatro intenciones del negocio. Observa las columnas: **pasos**, **tokens** y **latencia simulada** de cada petición.
    """)
    code('''
agent = SupportAgent()
preguntas = [
    "¿Dónde está mi pedido ORD-00012?",
    "Quiero devolver el pedido ORD-00020 y que me devuelvan el dinero.",
    "¿Cuántos años de garantía tienen los productos?",
    "Quiero hablar con una persona real, esto es inaceptable.",
]
filas = []
for q in preguntas:
    r = agent.run(q)
    filas.append({"pregunta": q[:46] + "…", "estado": r.status, "herramientas": ",".join(r.tools_used), "pasos": len(r.steps),
                  "tokens_in": r.input_tokens, "tokens_out": r.output_tokens, "latencia_s": round(r.latency_s, 2), "respuesta": r.answer[:60] + "…"})
pd.DataFrame(filas)
''')
    code('''
def explicar(r):
    """Cuenta la historia de una ejecución paso a paso (útil para depurar sin trazas… todavía)."""
    print(f"ticket {r.ticket_id}: estado={r.status} · {len(r.steps)} pasos · {r.latency_s:.2f}s simulados · {r.input_tokens}+{r.output_tokens} tokens · {r.cost_usd*1000:.3f} milésimas de USD")
    for s in r.steps:
        extra = f" tokens={s.input_tokens}/{s.output_tokens} finish={s.finish_reason}" if s.kind == "llm" else f" args={s.attributes.get('arguments')}"
        print(f"  {s.index}. {s.kind:4s} {s.name:18s} {s.latency_s:5.2f}s [{s.status}]{extra}")
    print("  →", r.answer)

r_ref = agent.run(Ticket("T-demo", "C-0001", "standard", "chat", "Quiero un reembolso del pedido ORD-00020, no me gustó.", "refund", SIM_EPOCH_S))
explicar(r_ref)
fig, ax = plt.subplots(figsize=(9, 3)); fig.subplots_adjust(left=0.22)
viz.timeline(r_ref.steps, ax, "Una petición de reembolso: 3 llamadas al LLM y 2 herramientas"); plt.show()
''')
    md(observe("""
    - El patrón **LLM → herramienta → LLM → herramienta → LLM** es la firma del agente: tres llamadas al modelo para dos herramientas.
    - El tiempo se reparte entre **espera del modelo** (barras azules, la mayor parte) y herramientas (verdes, mucho más cortas). Para optimizar latencia en agentes normalmente optimizas *llamadas al LLM* (menos pasos, prompts más cortos, modelos más rápidos), no tus APIs internas.
    - Esta gráfica la hemos dibujado nosotros con datos que el agente **devuelve**. En producción no tendrás un `AgentResult`: tendrás una **traza**, que es exactamente esta misma cascada pero capturada por instrumentación (módulo 03).
    """))

    # --------------------------------------------------------------------------- 1.5 teoría
    md("""
    ## 1.5 Teoría: mensajes, herramientas, parada y coste

    **Mensajes.** Cada mensaje tiene un `role`: `system` (instrucciones permanentes), `user` (el cliente), `assistant` (el modelo; puede incluir `tool_calls`) y `tool` (el resultado de una herramienta, con el `tool_call_id` que lo enlaza).
    El modelo **no tiene memoria entre llamadas**: en cada paso se le reenvía *toda* la conversación.

    **Herramientas.** Se declaran con un nombre, una descripción y un **JSON Schema** de argumentos; el modelo devuelve `tool_calls` con el nombre y los argumentos, y **tu código** ejecuta la función. Las de SupportOps:
    """)
    code('''
import json
tools = default_tools()
print(json.dumps(tools.get("issue_refund").schema(), indent=1, ensure_ascii=False))
pd.DataFrame([{"herramienta": t, "descripción": tools.get(t).description[:70], "latencia mediana (s)": tools.get(t).latency_median_s} for t in tools.names()]).set_index("herramienta")
''')
    md("""
    **Parada.** El bucle termina cuando el modelo responde **sin** `tool_calls` (`finish_reason="stop"`), cuando se agotan los pasos (`max_steps`) o ante un error no recuperable.

    **Tokens y coste.** Sea $S$ el tamaño del contexto inicial (instrucciones del sistema + definición de herramientas + mensaje del cliente), $u_j$ los tokens de los resultados de herramienta añadidos tras el paso $j$ y $o_j$ los tokens que el modelo generó en ese paso.
    En la llamada $k$ el modelo recibe:

    $$ I_k \\;=\\; S \\;+\\; \\sum_{j<k} (o_j + u_j) $$

    y el coste de una petición de $K$ llamadas es

    $$ \\text{coste} \\;=\\; \\frac{1}{10^6}\\sum_{k=1}^{K} \\big( I_k \\cdot p_{in} \\;+\\; O_k \\cdot p_{out} \\big) $$

    con $p_{in}, p_{out}$ los precios por millón de tokens de entrada y salida. Como $I_k$ crece con $k$, la **suma de tokens de entrada crece ~ cuadráticamente con el número de pasos**: duplicar los pasos puede *más que duplicar* el coste.

    > 📐 Los precios del modo `mock` son **simulados** (`supportops/pricing.py`: 0,25 / 1,25 USD por millón para `mock-small`; 3 / 15 para `mock-large`). Para costes reales consulta la página de precios de tu proveedor.
    """)
    code('''
# Tokens de entrada por llamada al LLM: petición normal vs petición con bucle de herramientas (fallo inyectado)
base = Ticket("T-demo", "C-0001", "standard", "chat", "Quiero un reembolso del pedido ORD-00020, no me gustó.", "refund", SIM_EPOCH_S)
loop = Ticket("T-demo", "C-0001", "standard", "chat", base.text, "refund", SIM_EPOCH_S, faults=[FaultSpec("tool_loop")])
r_ok, r_loop = agent.run(base), agent.run(loop)
tok = lambda r: [s.input_tokens for s in r.steps if s.kind == "llm"]
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
ax[0].bar(np.arange(len(tok(r_ok))) - 0.2, tok(r_ok), 0.4, label=f"normal ({r_ok.n_llm_calls} llamadas)", color=viz.PALETTE["ok"])
ax[0].bar(np.arange(len(tok(r_loop))) + 0.2, tok(r_loop), 0.4, label=f"con bucle ({r_loop.n_llm_calls} llamadas)", color=viz.PALETTE["error"])
ax[0].set_xlabel("nº de llamada al LLM"); ax[0].set_ylabel("tokens de ENTRADA de esa llamada"); ax[0].set_title("Cada vuelta reenvía todo el contexto"); ax[0].legend()
ks = np.arange(1, 13); S, per = 350, 120
ax[1].plot(ks, S * ks + per * ks * (ks - 1) / 2, "o-", color=viz.PALETTE["metrics"]); ax[1].plot(ks, S * ks, "k:", label="si el contexto no creciera (lineal)")
ax[1].set_xlabel("nº de llamadas al LLM (K)"); ax[1].set_ylabel("tokens de entrada acumulados"); ax[1].set_title("Modelo: suma de I_k (S=350, +120 por paso)"); ax[1].legend()
plt.tight_layout(); plt.show()
print(f"normal: {r_ok.input_tokens} tokens in, {r_ok.cost_usd*1000:.3f} m$ · con bucle: {r_loop.input_tokens} tokens in, {r_loop.cost_usd*1000:.3f} m$ → {r_loop.cost_usd/r_ok.cost_usd:.1f}× el coste")
''')
    md(observe("""
    - A la izquierda, cada barra es **más alta que la anterior**: el agente reenvía el historial completo. El bucle (rojo) hace 6 llamadas y la última recibe ≈ 2,5× los tokens de la primera.
    - A la derecha, el modelo teórico: la curva naranja se separa de la línea recta, que sería el coste si cada llamada fuera independiente. Esto explica por qué **un bucle largo es tan caro** y por qué *recortar contexto* (resúmenes, no repetir herramientas) es una palanca de coste de primer orden (módulo 13).
    - El coste de la petición con bucle no es 2×: es varias veces el de la normal.
    """))

    code('''
# Determinismo: misma semilla → mismos resultados (por eso las rúbricas del curso son reproducibles)
t = generate_tickets(5, seed=SEED)[0]
a = SupportAgent(llm=MockLLM(seed=SEED)).run(t)
b = SupportAgent(llm=MockLLM(seed=SEED)).run(t)
c = SupportAgent(llm=MockLLM(seed=7)).run(t)
print("misma semilla  → latencia idéntica:", a.latency_s == b.latency_s, f"({a.latency_s:.4f} s)")
print("otra semilla   → latencia distinta:", c.latency_s != a.latency_s, f"({c.latency_s:.4f} s)")
''')
    md(box("elite", "Secretos de la élite · determinismo por llamada", """
    El mock **no usa un generador aleatorio global**: cada llamada deriva su propio RNG de `SHA-256(seed, ticket_id, nº de llamada)`. Así la latencia de la llamada 3 del ticket T-17 es la misma
    se ejecute el notebook entero, solo esa celda o en otro orden. Un `random.seed(42)` global *no* da esa garantía (cualquier llamada extra desplaza toda la secuencia). Es el mismo principio que usan los sistemas de *record/replay* para depurar agentes reales.
    """))

    # ---------------------------------------------------------------------------------------------- 2
    md("""
    ---
    # 2 · Proveedor LLM agnóstico

    El agente no depende de ningún proveedor: habla con un `LLMClient` (un *Protocol*: cualquier objeto con `.chat(messages, tools, ...)` que devuelva `LLMResponse`). La fábrica `get_llm()` lee el entorno:

    | `LLM_PROVIDER` | Qué usa | Variables |
    |---|---|---|
    | `mock` (por defecto) | `MockLLM`: determinista, sin red, sin coste | `LLM_MODEL=mock-small \\| mock-large`, `SUPPORTOPS_SEED` |
    | `anthropic` | SDK oficial `anthropic` (API Messages con `tools`) | `ANTHROPIC_API_KEY`; `LLM_MODEL` (por defecto `claude-sonnet-5-5`; verifica los modelos disponibles hoy) |
    | `openai` | SDK `openai` (Chat Completions con `tools`) | `OPENAI_API_KEY`, `LLM_MODEL` **obligatoria**, opcional `OPENAI_BASE_URL` |
    | `ollama` | API HTTP local `/api/chat` (sin dependencias) | `LLM_MODEL` **obligatoria** (un modelo con soporte de herramientas), `OLLAMA_HOST` |

    > ⚠️ **Las API keys solo por variables de entorno** (`export ANTHROPIC_API_KEY=...` antes de lanzar Jupyter). Nunca en un notebook: acabaría en git. Las rúbricas del curso se calibran **solo con `mock`**.
    > Los adaptadores reales están probados con clientes de prueba (sin red) y *no* contra las APIs en vivo durante la construcción del curso.

    Cada adaptador traduce el formato interno a la API de su proveedor (por ejemplo, `tool_result` como bloque dentro de un mensaje `user` en Anthropic, o `role="tool"` en OpenAI) y **normaliza la respuesta** a `LLMResponse`. Mismo agente, distinto motor:
    """)
    code('''
from supportops.llm.anthropic_provider import to_anthropic_messages
from supportops.llm.openai_provider import to_openai_messages

conv = [Message("user", "¿Dónde está ORD-00012?"),
        Message("assistant", "", [ToolCall("call_1", "get_order", {"order_id": "ORD-00012"})]),
        Message("tool", \'{"status": "processing"}\', tool_call_id="call_1", name="get_order")]
print("— formato Anthropic —");  print(json.dumps(to_anthropic_messages(conv), indent=1, ensure_ascii=False)[:520], "...")
print("— formato OpenAI —");     print(json.dumps(to_openai_messages(conv, "sistema"), indent=1, ensure_ascii=False)[:420], "...")
''')
    code('''
# Prueba OPT-IN con un proveedor real: solo si TÚ has exportado la clave y quieres gastar unos tokens.
provider = os.environ.get("LLM_PROVIDER", "mock")
if provider != "mock" and (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY") or provider == "ollama"):
    real = SupportAgent(llm=get_llm(provider))
    explicar(real.run("¿Cuántos años de garantía tienen los productos?"))
else:
    print("LLM_PROVIDER=mock → no se llama a ningún servicio externo. Para probar uno real:\\n  export LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=...  (antes de lanzar Jupyter)")
''')

    md("""
    ## 2.1 El modelo de latencia del mock

    Para que las trazas y los dashboards se parezcan a los de producción, la latencia simulada de cada llamada es:

    $$ \\text{latencia} \\;=\\; \\underbrace{T_{ttft}\\, e^{\\epsilon_1}}_{\\text{tiempo hasta el primer token}} \\;+\\; \\underbrace{o\\cdot c_{out}\\, e^{\\epsilon_2}}_{\\text{generación}} \\;+\\; \\underbrace{I\\cdot c_{in}}_{\\text{prefill}} ,\\qquad \\epsilon_i\\sim\\mathcal N(0,\\sigma_i^2) $$

    con $o$ = tokens de salida, $I$ = tokens de entrada, y (para `mock-small`) $T_{ttft}=0{,}35$ s, $c_{out}=12$ ms/token, $c_{in}=0{,}04$ ms/token. Además, un 2 % de las llamadas son «lentas por naturaleza» (×3): la cola pesada típica.
    Los ruidos son *lognormales* (multiplicativos), que es lo que se observa en latencias reales. Lo comprobamos con tráfico:
    """)
    code('''
N = 150 if FAST_DEV_RUN else 400
tk = generate_tickets(N, seed=SEED)                                   # tráfico SIN fallos: aislamos el modelo de latencia
res_s = run_tickets(SupportAgent(llm=MockLLM("mock-small", seed=SEED)), tk)
res_l = run_tickets(SupportAgent(llm=MockLLM("mock-large", seed=SEED)), tk)
llm_steps = lambda rs: pd.DataFrame([{"out": s.output_tokens, "inp": s.input_tokens, "lat": s.latency_s} for r in rs for s in r.steps if s.kind == "llm"])
Ds, Dl = llm_steps(res_s), llm_steps(res_l)
fig, ax = plt.subplots(figsize=(8.5, 4.2))
ax.scatter(Ds.out, Ds.lat, s=10, alpha=.45, label="mock-small", color=viz.PALETTE["traces"]); ax.scatter(Dl.out, Dl.lat, s=10, alpha=.45, label="mock-large", color=viz.PALETTE["metrics"])
xs = np.linspace(0, max(Ds.out.max(), Dl.out.max()), 50)
ax.plot(xs, 0.35 + 0.012 * xs + 0.00004 * Ds.inp.median(), color=viz.PALETTE["traces"], lw=2); ax.plot(xs, 0.70 + 0.030 * xs + 0.00008 * Dl.inp.median(), color=viz.PALETTE["metrics"], lw=2)
ax.set_xlabel("tokens de salida de la llamada"); ax.set_ylabel("latencia de la llamada al LLM (s, simulada)"); ax.set_title("Latencia ≈ TTFT + tokens·s/token (+ cola lenta natural)"); ax.legend()
plt.show()
print(f"mock-small: mediana {Ds.lat.median():.2f}s · p99 {Ds.lat.quantile(.99):.2f}s | mock-large: mediana {Dl.lat.median():.2f}s · p99 {Dl.lat.quantile(.99):.2f}s")
''')
    md(observe("""
    - Los puntos siguen una **recta** (TTFT + pendiente por token). `mock-large` tiene mayor ordenada (TTFT) y mayor pendiente: es más lento en ambos conceptos.
    - Los puntos muy por encima de la recta son la **cola lenta natural** (×3). No son un fallo inyectado: así es la latencia de un proveedor real. Un SLO de latencia debe vivir con esa cola.
    - Observa también que las llamadas con **pocos tokens de salida** (las que piden herramienta) son rápidas: el tiempo dominante es el TTFT, no la generación.
    """))

    code('''
# Mismo tráfico, dos modelos: ¿qué compras con un modelo «grande»? (en el mock: más latencia y 12× el precio)
def resumen(rs):
    d = pd.DataFrame([r.to_dict() for r in rs])
    return {"latencia media (s)": d.latency_s.mean(), "p95 latencia (s)": d.latency_s.quantile(.95), "coste medio / ticket (m$)": d.cost_usd.mean() * 1000, "tokens in / ticket": d.input_tokens.mean()}
cmp = pd.DataFrame({"mock-small": resumen(res_s), "mock-large": resumen(res_l)}).T
display(cmp.round(2))
fig, ax = plt.subplots(1, 3, figsize=(11, 3.3))
for a_, col, lab in zip(ax, ["latencia media (s)", "p95 latencia (s)", "coste medio / ticket (m$)"], ["segundos", "segundos", "milésimas de USD"]):
    a_.bar(cmp.index, cmp[col], color=[viz.PALETTE["traces"], viz.PALETTE["metrics"]]); a_.set_title(col); a_.set_ylabel(lab)
plt.tight_layout(); plt.show()
print(f"coste ×{cmp.loc['mock-large', 'coste medio / ticket (m$)'] / cmp.loc['mock-small', 'coste medio / ticket (m$)']:.1f} · latencia ×{cmp.loc['mock-large', 'latencia media (s)'] / cmp.loc['mock-small', 'latencia media (s)']:.1f}")
''')
    md(observe("""
    - El coste por ticket se multiplica por el cociente de precios (12×) mientras la latencia «solo» se duplica aproximadamente. En la práctica **la decisión de modelo es una decisión de coste y de latencia a la vez**, y tiene que verse en los dashboards (módulos 09 y 13).
    - Las gráficas son **comparables** porque el tráfico es idéntico (misma semilla): ése es el valor de un generador reproducible.
    """))

    # ---------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · Herramientas y base de conocimiento (RAG)

    ## 3.1 Las herramientas simuladas

    | Herramienta | Qué hace | Regla de negocio / fallo posible |
    |---|---|---|
    | `get_order(order_id)` | Estado de un pedido (de 600 sintéticos `ORD-00001…`) | `found: false` si no existe |
    | `issue_refund(order_id, amount_eur, reason)` | Reembolsa | Solo pedidos **entregados hace ≤ 30 días** y por importe ≤ total. Si no: `approved: false` con `reason` |
    | `search_kb(query, k)` | Busca en 14 documentos (devoluciones, garantía, envíos, drivers…) | Devuelve `score` por documento |
    | `escalate_to_human(reason, priority)` | Deriva a una persona | — |

    **Error de negocio ≠ error de infraestructura.** Que `issue_refund` devuelva `approved: false` es un **resultado normal** (el cliente no cumple la política) y *no* debe contar como error del sistema.
    Una excepción `ToolError` (timeout, 5xx del servicio de pedidos) sí lo es. Confundirlos infla la tasa de error y despierta a on-call por nada — o peor, oculta fallos reales.
    """)
    code('''
from supportops.tools import issue_refund, get_order, ToolError
from supportops import catalog
orders = catalog.orders()
elegible = next(o for o in orders.values() if o["status"] == "delivered" and o["delivered_days_ago"] <= 30)
antiguo = next(o for o in orders.values() if o["status"] == "delivered" and o["delivered_days_ago"] > 30)
enviado = next(o for o in orders.values() if o["status"] == "shipped")
for o in (elegible, antiguo, enviado):
    print(f"{o['order_id']} ({o['status']}, entregado hace {o['delivered_days_ago']} d) →", issue_refund(o["order_id"], o["total_eur"]))
print("\\nError de infraestructura (distinto):")
try:
    raise ToolError("el servicio de pedidos devolvió 503", "upstream_503")
except ToolError as e:
    print(" ToolError:", e, "| error_type =", e.error_type)
''')

    md("""
    ## 3.2 RAG sencillo: TF-IDF + coseno

    **RAG** (*retrieval-augmented generation*, Lewis et al., 2020) = antes de responder, **recuperar** documentos relevantes y dárselos al modelo. Aquí la recuperación es TF-IDF, sin dependencias:

    $$ \\text{idf}(t)=\\ln\\frac{1+n}{1+\\text{df}(t)}+1,\\qquad \\vec d_t=\\text{tf}(t,d)\\cdot\\text{idf}(t),\\qquad \\text{score}(q,d)=\\cos(\\vec q,\\vec d)=\\frac{\\vec q\\cdot\\vec d}{\\lVert\\vec q\\rVert\\,\\lVert\\vec d\\rVert} $$

    con $n$ documentos y $\\text{df}(t)$ cuántos contienen el término $t$. Un término raro (alto idf) pesa más que uno frecuente. Veamos qué recupera para tres consultas, incluida una que **no encaja bien**:
    """)
    code('''
from supportops.kb import KnowledgeBase
kb = KnowledgeBase()
consultas = ["¿cuántos años de garantía tienen?", "mi tarjeta gráfica parpadea tras instalarla", "¿cuánto tarda el correo en llegar a casa?"]
fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), sharex=True)
for ax, q in zip(axes, consultas):
    res = kb.search(q, k=4)
    ax.barh([f"{r['doc_id']}\\n{r['title'][:24]}" for r in res][::-1], [r["score"] for r in res][::-1], color=viz.PALETTE["logs"] if res and res[0]["score"] > 0.2 else viz.PALETTE["warn"])
    ax.set_title(q if len(q) < 40 else q[:38] + "…", fontsize=9); ax.set_xlabel("similitud coseno")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con vocabulario compartido («garantía», «tarjeta gráfica», «parpadea») el documento correcto sale **primero con una puntuación clara**.
    - La tercera consulta usa sinónimos («correo», «a casa») que el TF-IDF no entiende: las puntuaciones son bajas y **parecidas entre sí** (barras amarillas). Si el agente aun así responde con el primer documento, **inventa con apariencia de fundamento**. Una puntuación de recuperación baja es una *señal de calidad* que merece ser un atributo de la traza (módulo 04) y una métrica (módulo 14).
    - Los embeddings densos resuelven sinónimos, pero introducen otro coste (cómputo, índice, deriva) — y otros fallos que observar.
    """))

    # ---------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · Tráfico sintético con semilla

    ## 4.1 El generador

    `generate_tickets(n, seed, duration_s, fault_rates, incidents, start_s, ...)` crea **tickets** de clientes ficticios. Es determinista: misma semilla → mismos tickets. Esquema:
    """)
    code('''
print(schema.describe(schema.TICKET_SCHEMA))
tk = generate_tickets(400 if not FAST_DEV_RUN else 200, seed=SEED, fault_rates=DEFAULT_FAULT_RATES,
                      incidents=[Incident("llm_provider_degraded", "llm_error", 1200, 1800, prob=0.7, params={"status": 503, "persistent": True})])
print("\\nejemplo:", tk[0].to_dict()["text"], "| intent:", tk[0].intent_true, "| faults:", [f.kind for f in tk[0].faults])
''')
    code('''
T = pd.DataFrame([t.to_dict() | {"minute": (t.created_at - SIM_EPOCH_S) / 60, "n_faults": len(t.faults)} for t in tk])
fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
ax[0].hist(T.minute, bins=np.arange(0, 61, 2), color=viz.PALETTE["traces"]); ax[0].axvspan(20, 30, color=viz.PALETTE["error"], alpha=.15, label="incidente (min 20–30)")
ax[0].set_xlabel("minuto"); ax[0].set_ylabel("tickets cada 2 min"); ax[0].set_title("Llegadas: pico a mitad de ventana"); ax[0].legend()
mix = T.intent_true.value_counts(normalize=True); ax[1].bar(mix.index, mix.values * 100, color=viz.PALETTE["logs"]); ax[1].set_ylabel("% de tickets"); ax[1].set_title("Mezcla de intenciones"); ax[1].tick_params(axis="x", rotation=20)
cnt = T.customer_id.value_counts().values; ax[2].loglog(np.arange(1, len(cnt) + 1), cnt, "o", color=viz.PALETTE["metrics"], ms=4); ax[2].set_xlabel("ranking del cliente (log)"); ax[2].set_ylabel("nº de tickets (log)"); ax[2].set_title("Cola larga de clientes (Zipf)")
plt.tight_layout(); plt.show()
print(f"{(T.customer_id.value_counts().head(10).sum() / len(T)):.0%} de los tickets vienen de los 10 clientes más activos de {T.customer_id.nunique()} distintos")
''')
    md(observe("""
    - **Izquierda:** llegadas con un pico central (patrón diario comprimido a 1 hora). La franja roja es una **ventana de incidente** que programamos: dentro de ella los tickets tienen un 70 % de probabilidad de sufrir un fallo del proveedor LLM.
    - **Centro:** la mezcla pedida (35 / 20 / 35 / 10 %).
    - **Derecha:** distribución de cola larga: unos pocos clientes generan muchísimo tráfico. Esto importa para observabilidad: **atribuir coste o errores por cliente** (alta cardinalidad) es útil en trazas y logs, pero peligroso como *label* de métricas (módulo 02 y 09).
    - Para enviar tráfico a un stack **vivo** usa `start_s="live"`: así los timestamps caen en la última hora y Tempo/Loki los aceptan.
    """))

    # ---------------------------------------------------------------------------------------------- 5
    md("""
    ---
    # 5 · Fallos inyectados: el *ground truth* de la observabilidad

    Siete tipos de fallo, activables **por ticket** (van dentro de `ticket.faults`). Como los inyectamos nosotros, sabemos la verdad y podremos medir si nuestra observabilidad los detecta.
    """)
    code('''
pd.DataFrame([{"fallo": k, "qué hace": v} for k, v in FAULT_KINDS.items()]).set_index("fallo")
''')
    md("""
    Ejecutemos **el mismo ticket** (un reembolso) sin fallo y con cada fallo. Compara la fila «ninguno» con el resto:
    """)
    code('''
base = Ticket("T-demo", "C-0001", "standard", "chat", "Quiero un reembolso del pedido ORD-00020, no me gustó.", "refund", SIM_EPOCH_S)
casos = [("ninguno", None, {}), ("latency_spike ×8", "latency_spike", {"factor": 8.0, "target": "both"}), ("llm_error (transitorio)", "llm_error", {"persistent": False}),
         ("llm_error (persistente)", "llm_error", {"persistent": True}), ("tool_error", "tool_error", {}), ("tool_timeout", "tool_timeout", {}),
         ("hallucination", "hallucination", {}), ("tool_loop", "tool_loop", {}), ("pii_leak", "pii_leak", {"victim": "C-0042"})]
filas = []
for nombre, kind, params in casos:
    t = Ticket(base.ticket_id, base.customer_id, base.tier, base.channel, base.text, base.intent_true, base.created_at, faults=[FaultSpec(kind, params)] if kind else [])
    r = SupportAgent().run(t)
    filas.append({"caso": nombre, "estado": r.status, "latencia_s": round(r.latency_s, 2), "pasos": len(r.steps), "tokens_in": r.input_tokens,
                  "¿fundamentada?": r.grounded, "¿PII ajena?": r.pii_leaked, "error_type": r.error_type or "", "respuesta": r.answer[:55] + "…"})
F = pd.DataFrame(filas).set_index("caso")
F
''')
    code('''
fig, ax = plt.subplots(1, 3, figsize=(14, 3.9), sharey=True)
y = np.arange(len(F))
col = lambda v: viz.PALETTE["error"] if v in ("error", "max_steps") else viz.PALETTE["warn"] if v == "degraded" else viz.PALETTE["ok"]
ax[0].barh(y, F.latencia_s, color=[col(s) for s in F.estado]); ax[0].set_yticks(y); ax[0].set_yticklabels(F.index); ax[0].invert_yaxis(); ax[0].set_xlabel("latencia (s)"); ax[0].set_title("Latencia (color = estado)")
ax[1].barh(y, F.tokens_in, color=[col(s) for s in F.estado]); ax[1].set_xlabel("tokens de entrada"); ax[1].set_title("Tokens de entrada")
ax[2].barh(y, F.pasos, color=[col(s) for s in F.estado]); ax[2].set_xlabel("pasos"); ax[2].set_title("Pasos del agente")
for i, (g, p) in enumerate(zip(F["¿fundamentada?"], F["¿PII ajena?"])):
    if not g or p: ax[2].text(F.pasos.iloc[i] + 0.2, i, "respuesta MALA con estado «ok»" if F.estado.iloc[i] == "ok" else "", va="center", fontsize=8, color=viz.PALETTE["error"])
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **`hallucination` es el caso más barato y rápido** (0,6 s, 1 paso, ≈ 350 tokens) frente al reembolso correcto (≈ 2,5 s, 5 pasos, ≈ 1300 tokens). Una «mejora de latencia y coste» puede ser un **síntoma de que el agente dejó de usar sus herramientas**. Un dashboard que celebre ese descenso estaría celebrando una regresión.
    - **`pii_leak` es idéntico al caso sano** en latencia, pasos y tokens (la fuga añade unos pocos tokens a la respuesta): ninguna métrica de infraestructura lo ve. Solo se detecta **mirando el contenido** (módulo 20).
    - **`tool_loop`** dispara pasos y tokens (≈ 2,8× los de entrada) y termina en `max_steps`: sí se ve en métricas de coste/pasos y, mejor aún, en la traza (la misma herramienta repetida).
    - **`tool_timeout` y `tool_error`** terminan en estado `degraded` (el agente se disculpa pero *responde*): el error está **dentro** de la traza, no en el estado de la petición raíz. Mira el span de la herramienta, no solo el raíz.
    - **`llm_error` transitorio** *no* acaba en error: el reintento lo absorbe y solo se nota como +1 llamada y más latencia. **Persistente** sí falla (estado `error`). Los reintentos *enmascaran* problemas: hay que contarlos aparte.
    """))

    code('''
# ¿Cómo se ve cada fallo en la línea de tiempo? (latencia de los pasos)
fig, axes = plt.subplots(1, 3, figsize=(15, 3.4)); fig.subplots_adjust(left=0.08, wspace=0.55)
for ax, (nombre, kind, params) in zip(axes, [casos[0], casos[5], casos[7]]):
    t = Ticket(base.ticket_id, base.customer_id, base.tier, base.channel, base.text, base.intent_true, base.created_at, faults=[FaultSpec(kind, params)] if kind else [])
    r = SupportAgent().run(t); viz.timeline(r.steps[:12], ax, f"{nombre}  ({r.status})")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    Tres «huellas» distintas en la línea de tiempo: la **sana** (5 pasos cortos), el **timeout** (una barra roja de 5 s en la herramienta y un LLM que responde con disculpa) y el **bucle** (la misma herramienta repetida 6 veces, cada LLM más lenta por el contexto acumulado).
    Este tipo de vistas es lo que vas a obtener automáticamente de Tempo; hoy la dibujamos a mano para saber qué buscar.
    """))

    # ---------------------------------------------------------------------------------------------- 6
    md("""
    ---
    # 6 · Experimento: tráfico sano vs tráfico con fallos de fondo

    Ejecutamos el mismo tráfico dos veces: sin fallos y con las tasas por defecto (`DEFAULT_FAULT_RATES`). ¿Qué cambia en las métricas agregadas que un dashboard clásico mostraría?
    """)
    code('''
N = 300 if FAST_DEV_RUN else 1000
tk_ok = generate_tickets(N, seed=SEED)
tk_bad = generate_tickets(N, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)
d_ok = pd.DataFrame(to_rows(tk_ok, run_tickets(SupportAgent(), tk_ok)))
d_bad = pd.DataFrame(to_rows(tk_bad, run_tickets(SupportAgent(), tk_bad)))
def kpis(d):
    bad = (~d.grounded) | d.pii_leaked
    return {"error rate (error+max_steps)": d.status.isin(["error", "max_steps"]).mean() * 100, "degraded %": d.status.eq("degraded").mean() * 100,
            "respuestas malas con estado ok %": (bad & d.status.eq("ok")).mean() * 100, "p50 latencia (s)": d.latency_s.quantile(.5), "p99 latencia (s)": d.latency_s.quantile(.99),
            "coste total (m$)": d.cost_usd.sum() * 1000, "tokens in / ticket": d.input_tokens.mean()}
K = pd.DataFrame({"sano": kpis(d_ok), "con fallos": kpis(d_bad)}); K["Δ"] = K["con fallos"] - K["sano"]
display(K.round(2))
fig, ax = plt.subplots(1, 3, figsize=(14, 3.7))
for d, lab, c in [(d_ok, "sano", viz.PALETTE["ok"]), (d_bad, "con fallos", viz.PALETTE["error"])]:
    l = np.sort(d.latency_s.values); ax[0].plot(l, np.arange(1, len(l) + 1) / len(l), label=lab, color=c, lw=2)
ax[0].set_xscale("log"); ax[0].set_xlabel("latencia (s)"); ax[0].set_ylabel("ECDF"); ax[0].set_title("Latencia: la cola engorda"); ax[0].legend()
st = pd.DataFrame({"sano": d_ok.status.value_counts(normalize=True), "con fallos": d_bad.status.value_counts(normalize=True)}).fillna(0) * 100
SC = {"ok": viz.PALETTE["ok"], "escalated": viz.PALETTE["traces"], "degraded": viz.PALETTE["warn"], "error": viz.PALETTE["error"], "max_steps": viz.PALETTE["dark"]}
st.T.plot(kind="bar", stacked=True, ax=ax[1], color=[SC[c] for c in st.index], legend=True); ax[1].set_ylabel("% de tickets"); ax[1].set_title("Estados"); ax[1].tick_params(axis="x", rotation=0)
ax[2].boxplot([d_ok.cost_usd * 1000, d_bad.cost_usd * 1000], tick_labels=["sano", "con fallos"], flierprops=dict(marker=".", alpha=.5)); ax[2].set_ylabel("coste por ticket (m$)"); ax[2].set_title("Coste por ticket")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - La mediana casi no se mueve (los fallos son **minoría**), pero **p99 y máximo** sí: la cola es donde viven los problemas. Un SLO sobre la mediana no detectaría nada.
    - En «Estados», la barra de «con fallos» muestra errores y `degraded`, pero **la fila «respuestas malas con estado ok» de la tabla** es la que no aparece en ningún gráfico de estados: un SLI de éxito basado en estado la ignora.
    - El **coste total no sube; incluso baja un poco**: las alucinaciones (que no llaman herramientas) y las peticiones fallidas son *baratas*. Un dashboard de gasto vería un «ahorro» justo cuando la calidad empeora. Mientras tanto, el `coste por ticket` muestra extremos (bucles): el gasto está **concentrado**, como vimos en el módulo 00.
    """))

    # ---------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Puntos de extensión: dónde se instrumentará (adelanto del módulo 03)

    El agente v0 **no está instrumentado**, pero llama a un `Instrumentor` (por defecto no hace nada) en tres sitios, con *context managers*:

    ```python
    with instr.agent_run(ctx):                  # 1 por ticket          → span raíz   «invoke_agent supportops-agent»
        with instr.llm_call(ctx, info): ...     # 1 por llamada al LLM → span        «chat <modelo>»
        with instr.tool_call(ctx, info): ...    # 1 por herramienta    → span        «execute_tool <herramienta>»
    ```

    Para enseñarte el **modelo de datos** sin depender aún de OpenTelemetry, el paquete trae `RecordingInstrumentor`: guarda *spans* y *logs* en memoria con identificadores, padre/hijo, atributos y estado.
    No es OpenTelemetry (eso es el módulo 03), pero tiene su misma forma. Veamos qué captura de una ejecución:
    """)
    code('''
rec = RecordingInstrumentor()
r = SupportAgent(instrumentor=rec).run(Ticket("T-demo", "C-0001", "premium", "chat", "Quiero un reembolso del pedido ORD-00020, no me gustó.", "refund", SIM_EPOCH_S,
                                            faults=[FaultSpec("tool_timeout")]))
sp = pd.DataFrame(rec.spans)
sp["dur_s"] = (sp.end_unix_nano - sp.start_unix_nano) / 1e9
sp["padre"] = sp.parent_span_id.fillna("—").str[:6]
display(sp[["span_id", "padre", "name", "kind", "status", "dur_s"]].assign(span_id=sp.span_id.str[:6]).round(2))
print("atributos del span raíz:", {k: v for k, v in rec.spans[0]["attributes"].items() if k.startswith(("gen_ai", "supportops"))})
''')
    code('''
fig, ax = plt.subplots(1, 2, figsize=(15, 3.6), gridspec_kw={"width_ratios": [1.5, 1]})
fig.subplots_adjust(left=0.26, wspace=0.08)
viz.waterfall(rec.spans, ax=ax[0], title="Cascada de la traza (spans registrados)")
lg = pd.DataFrame(rec.logs); lg["t_s"] = (lg.time_unix_nano - rec.spans[0]["start_unix_nano"]) / 1e9
ax[1].axis("off"); ax[1].set_title("Logs correlacionados (mismo trace_id)")
txt = "\\n".join(f"{x.t_s:5.2f}s  {x.severity_text:5s} {x.body}   [span {x.span_id[:4]}]" for x in lg.itertuples())
ax[1].text(0, 0.95, txt, va="top", family="monospace", fontsize=8)
plt.show()
print("¿todos los logs comparten el trace_id de la traza?", set(lg.trace_id) == {rec.spans[0]["trace_id"]})
''')
    md(observe("""
    - La cascada muestra el **árbol**: raíz `invoke_agent`, y debajo `chat` y `execute_tool` (en rojo, el timeout de 5 s). El padre se identifica por `parent_span_id`.
    - Los **logs** del agente llevan el mismo `trace_id` y el `span_id` del span activo: así, desde una traza lenta saltarás a *sus* logs y viceversa. Esa correlación —que no es magia, es copiar dos identificadores— es la base del módulo 08.
    - Los nombres `invoke_agent`, `chat` y `execute_tool` y los atributos `gen_ai.*` siguen las **GenAI semantic conventions** de OpenTelemetry, que están en estado **Development** (inestables); las estudiaremos y validaremos en el módulo 04.
    """))

    # ---------------------------------------------------------------------------------------------- prod / elite
    md("""
    ---
    # 8 · 🏭 En producción

    - **Anthropic** ([«Building effective agents»](https://www.anthropic.com/engineering/building-effective-agents), 2024) recomienda empezar por la solución más simple, observa que los agentes **intercambian latencia y coste por rendimiento**, que su autonomía implica **más coste y errores acumulados**, y que conviene incluir **condiciones de parada** (máximo de iteraciones) y pruebas extensas en entornos aislados. Cada una de esas recomendaciones se traduce en algo que observar: pasos por petición, coste por petición, activaciones de `max_steps`.
    - **ReAct** (Yao et al., 2022) popularizó el patrón de intercalar *razonamiento y acciones* con herramientas, base de casi todos los agentes actuales; **RAG** (Lewis et al., 2020) el de recuperar documentos antes de generar. Ambos son fuentes de latencia (más pasos) y de fallos nuevos (recuperación irrelevante).
    - **Documentación de proveedores:** el bucle `tool_use`/`tool_result` de Anthropic y las `tools` de OpenAI son el contrato que implementan nuestros adaptadores; ambos exigen que **tu código** ejecute la herramienta y devuelva el resultado en el siguiente mensaje (por eso el coste de contexto crece con cada paso).
    - **Honeycomb** insiste (en sus artículos sobre su *Query Assistant*) en medir el éxito de las funciones con LLM con datos de uso reales y no solo con pruebas previas; es el motivo de que SupportOps nazca con *ground truth* de fallos para validar la observabilidad.
    """)
    md(box("elite", "Secretos de la élite · agentes en producción", """
    1. **La unidad de coste y de fallo es el *paso*, no la petición.** Dos peticiones idénticas pueden costar 1× y 6×. Todo presupuesto razonable tiene `max_steps` *y* un tope de tokens/coste por petición (módulo 13).
    2. **Los reintentos enmascaran fallos.** Un `llm_error` transitorio acaba en estado `ok`; si solo mides errores finales, no verás que el proveedor se degrada hasta que los reintentos se agotan. Cuenta **intentos**, no solo resultados.
    3. **Herramientas con efectos (reembolsos, escrituras) deben ser idempotentes.** Un reintento tras un timeout puede ejecutar la acción dos veces. Usa claves de idempotencia; es un riesgo que ninguna métrica te mostrará hasta que haya un cliente reembolsado dos veces.
    4. **Distingue error de negocio de error de infraestructura** (`approved:false` vs `ToolError`). Los SLOs de fiabilidad se calculan sobre lo segundo.
    5. **«Más rápido y más barato» puede ser peor**: una alucinación no llama herramientas. Vigila `tool_calls por petición` como señal de salud, no solo latencia y coste.
    6. **El contexto crece cuadráticamente en coste**: resumir o podar el historial suele ahorrar más que cambiar de modelo.
    7. **Determinismo reproducible = capacidad de depuración.** Si puedes re-ejecutar un incidente con la misma semilla/entrada, conviertes un fallo «no determinista» en un *test*. En producción real, graba entradas y respuestas de herramientas para *replay*.
    8. **`temperature=0` no garantiza determinismo** en proveedores reales (paralelismo, versiones del modelo, enrutado): no diseñes tests que lo asuman. *(Fuente secundaria / no verificada contra la página oficial de la API: varias guías de terceros lo indican; la documentación de cada proveedor lo matiza, compruébalo en la tuya.)*
    9. **Mide el coste cuadrático, no lo supongas.** Si cada paso reenvía el historial completo, los tokens de *entrada* acumulados de una petición de $n$ pasos son $n\\,c_0 + d\\,n(n-1)/2$ ($c_0$ = prompt fijo, $d$ = tokens que añade cada paso): con los valores de la celda, pasar de 3 a 6 pasos multiplica el coste de entrada por ≈ 2,9, **no** por 2. La celda siguiente lo calcula.
    10. **La caché de prompt es la palanca del coste cuadrático**, pero cambia lo que ves: en las APIs con caché explícita los tokens leídos de caché se facturan a una fracción del precio de entrada (cifras habituales: lectura ≈ 0,1× y escritura ≈ 1,25× el precio base en Anthropic; *fuente secundaria / no verificada: consulta la página de precios vigente*). Por eso el módulo 04 separa los tokens de caché en atributos propios: sin ellos, tu coste calculado no cuadra con la factura.
    """))
    code('''
# Coste de entrada acumulado de una petición con n pasos, reenviando todo el historial en cada paso
C0, D = 600, 250        # tokens del prompt fijo y tokens que añade cada paso (hipótesis ilustrativas)
def input_tokens(n: int) -> int:
    return sum(C0 + D * k for k in range(n))      # paso k reenvía C0 + k*D
for n in (1, 3, 6, 12):
    print(f"n={n:2d} pasos → {input_tokens(n):6d} tokens de entrada  ({input_tokens(n) / input_tokens(1):4.1f}× el de 1 paso)")
''')
    md(box("warn", "Errores comunes (pitfalls)", """
    - **Escribir tests de «la respuesta debe ser exactamente X»** contra un LLM real: usa propiedades (llamó a la herramienta correcta, citó el documento, no incluyó PII).
    - **Medir solo el estado final**: un agente puede responder `ok` tras tres herramientas fallidas.
    - **Olvidar `max_steps`** (o ponerlo muy alto): el primer bucle te cuesta dinero real.
    - **Evaluar con `eval()`** el texto que genera un LLM: ejecución de código arbitrario. Usa parsers o herramientas con argumentos tipados.
    - **Mezclar API keys en notebooks o repos**: siempre variables de entorno / gestor de secretos.
    - **Usar un RNG global** para simular: los resultados dependen del orden de ejecución y no son reproducibles.
    - **Suponer que el mock = realidad**: es un simulador con latencias y tokens plausibles, útil para aprender y para pruebas deterministas, no un sustituto de medir tu proveedor real.
    """))

    # ---------------------------------------------------------------------------------------------- autoevaluación
    md("""
    ---
    # 9 · Autoevaluación
    """)
    qs = [
        ("1 · (Cálculo) Coste de una petición",
         """Una petición hace 3 llamadas al LLM con 800, 1100 y 1400 tokens de entrada y 40, 40 y 90 de salida. Con 0,25 USD/M de entrada y 1,25 USD/M de salida, ¿cuál es el coste? ¿Y si el agente hiciera 6 llamadas añadiendo ≈ 300 tokens de entrada por paso desde 800?""",
         """3 llamadas: entrada 800+1100+1400 = 3300 → 3300·0,25/10⁶ = 0,000825 USD; salida 170·1,25/10⁶ = 0,0002125 USD; **total ≈ 0,00104 USD (≈ 1,04 milésimas)**.
        6 llamadas: entrada 800, 1100, 1400, 1700, 2000, 2300 = 9300 tokens → 0,0023 USD solo de entrada: **más del doble** con el doble de llamadas, por el crecimiento del contexto (efecto cuadrático)."""),
        ("2 · (Cálculo) Latencia esperada",
         """Con `mock-small` (TTFT 0,35 s; 12 ms/token de salida; 0,04 ms/token de entrada), ¿qué latencia *media* (sin ruido) tiene una llamada con 900 tokens de entrada y 60 de salida? ¿Y una que solo pide una herramienta (≈ 25 tokens de salida)?""",
         """Con 60 de salida: 0,35 + 60·0,012 + 900·0,00004 = 0,35 + 0,72 + 0,036 = **≈ 1,11 s**. Con 25 de salida: 0,35 + 0,30 + 0,036 = **≈ 0,69 s**. Dominan TTFT y generación; el prefill apenas cuenta aquí."""),
        ("3 · (Diagnóstico) «El agente va mejor»",
         """Tras un cambio de prompt, la latencia media baja un 40 %, el coste un 60 % y el error rate no cambia. ¿Celebras? ¿Qué miras antes?""",
         """No celebres todavía. Una caída conjunta de latencia y coste con error rate estable es la huella de **menos pasos/herramientas**: quizá el agente ahora responde sin consultar (alucinaciones). Mira `tool_calls` por petición, la tasa de respuestas *fundamentadas* (evaluación online) y una muestra de trazas antes/después."""),
        ("4 · (Diagnóstico) Reembolsos duplicados",
         """Aparecen reembolsos duplicados en contabilidad, pero tus dashboards muestran 0 errores. Da una hipótesis basada en lo visto y cómo la confirmas con telemetría.""",
         """Hipótesis: un **timeout** en `issue_refund` seguido de un reintento (del LLM o de la herramienta) ejecutó la acción dos veces; la herramienta no es idempotente. Confirmación: en las trazas, peticiones con **dos spans `execute_tool issue_refund`** (el primero con error/timeout) para el mismo `order_id`; en logs, mismo `order_id` aprobado dos veces."""),
        ("5 · (Cálculo) Semillas",
         """Corres 1000 tickets con `seed=42` y obtienes p99 = 12,0 s. Un compañero obtiene 12,3 s con el mismo código. ¿Qué dos explicaciones razonables hay?""",
         """(1) **Distinto `SUPPORTOPS_SEED` o versión del paquete/mock** (el RNG deriva de la semilla y del código). (2) Usó otro `LLM_MODEL`/otras `fault_rates`. Si todo coincide, el resultado **debe** ser idéntico (el RNG es por llamada): una diferencia indicaría estado oculto o dependencia del orden — un bug."""),
        ("6 · (Transferencia) De tu bot actual",
         """Piensa en un chatbot o asistente que conozcas. ¿Es workflow o agente según la definición de Anthropic? ¿Qué *condición de parada* tiene y qué métrica te avisaría de que falla?""",
         """Si el orden de pasos está fijado por código (p. ej. «clasifica → busca → responde») es un *workflow*; si el modelo decide qué herramienta usar y cuándo parar, es un *agente*. La condición de parada típica es `max_steps`/tiempo máximo; la métrica: tasa de peticiones que terminan por esa condición (en SupportOps, estado `max_steps`)."""),
        ("7 · (Transferencia) RAG en tu dominio",
         """Tu empresa tiene un RAG sobre documentación interna. ¿Qué dos señales de la recuperación incluirías como atributos de traza para detectar respuestas «con apariencia de fundamento»?""",
         """La **puntuación del mejor documento** (y la diferencia con el segundo) y el **número de documentos recuperados por encima de un umbral**; opcionalmente los *ids* de documentos. Una puntuación baja o plana indica recuperación débil: la respuesta probablemente no esté fundamentada."""),
        ("8 · (Recuerdo) Roles y parada",
         """¿Qué roles tienen los mensajes de la conversación y qué tres condiciones terminan el bucle?""",
         """Roles: `system`, `user`, `assistant` (con `tool_calls`), `tool` (resultado). Terminan el bucle: respuesta sin `tool_calls` (`finish_reason=stop`), agotar `max_steps`, o error no recuperable (p. ej. `llm_error` persistente)."""),
    ]
    for title, q, a in qs:
        md(f"**Pregunta {title}**\n\n{q}\n\n" + details("Ver respuesta", a))

    md("""
    ---
    # 10 · Referencias

    - Anthropic Engineering, *Building effective agents* (19-dic-2024) — <https://www.anthropic.com/engineering/building-effective-agents> (definiciones de *workflow* vs *agent*, condiciones de parada, coste y errores acumulados).
    - Yao, Zhao, Yu, Du, Shafran, Narasimhan, Cao, *ReAct: Synergizing Reasoning and Acting in Language Models*, 2022 — <https://arxiv.org/abs/2210.03629>.
    - Lewis et al., *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, NeurIPS 2020 — <https://arxiv.org/abs/2005.11401>.
    - Ji et al., *Survey of Hallucination in Natural Language Generation*, 2022 (arXiv; revisiones posteriores) — <https://arxiv.org/abs/2202.03629>.
    - Anthropic, *Tool use with Claude* (documentación) — <https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview> (flujo `tool_use` → `tool_result`, `stop_reason`).
    - OpenAI, *Function calling* (guía) — <https://developers.openai.com/api/docs/guides/function-calling>. (Nuestro adaptador usa Chat Completions con `tools`; la guía actual puede centrarse en otra API: revisa la documentación vigente.)
    - Honeycomb, *So We Shipped an AI Product. Did it Work?* (2 de octubre de 2023) — <https://www.honeycomb.io/blog/we-shipped-ai-product>.
    - Anthropic, *Pricing / Prompt caching* (multiplicadores de lectura y escritura de caché citados en 🧠 #10: **fuente secundaria, no verificada** contra la página oficial desde este entorno).
    - OpenTelemetry, *GenAI semantic conventions* (estado Development; repositorio actual) — <https://github.com/open-telemetry/semantic-conventions-genai>.

    **Siguiente:** `02_tres_pilares` — traces, metrics y logs, el modelo de datos de OpenTelemetry y las *golden signals* aplicadas a agentes. Haz primero el **proyecto** de este módulo: `01_proyecto_agente_base.ipynb`.
    """)
    nb.save(out)


# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "01_proyecto_agente_base.ipynb", "Proyecto 01 · Extiende SupportOps v0 y reproduce tres fallos")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 01 · Extiende SupportOps v0 con una herramienta nueva y reproduce 3 fallos

    | | |
    |---|---|
    | **Nivel** | 🟢 Básico |
    | **Duración estimada** | ≈ 1 h 50 min |
    | **Servicios de Compose** | Ninguno (todo simulado) |
    | **RAM aproximada** | < 300 MB |
    | **Prerrequisitos** | Lección `01_agente_base` (bucle del agente, herramientas, mock, fallos). Módulo 00 (proyecto: `check_stack`) |
    | **Conexión** | Parte de **SupportOps v0** y te deja un agente con `check_stock` y un detector de síntomas que usarás como punto de partida en el módulo 03 (instrumentación) |

    ## Contexto de negocio

    Eres ingeniero/a de IA en **SupportOps**. Marketing quiere que el agente conteste «¿hay stock del teclado K87?» sin escalar a una persona.
    Antes de lanzarlo, Calidad te pide dos cosas: (1) **la herramienta nueva sin romper nada** (el resto de tickets debe comportarse exactamente igual) y (2) **un catálogo de síntomas**: para tres fallos que ya conocéis (bucle de herramientas, alucinación, timeout), qué «huella» dejan en el resultado del agente, y un detector que *solo mire el resultado* (sin conocer la verdad) para ver cuánto se puede detectar sin observabilidad especializada.

    ## Datos

    Tráfico sintético de SupportOps (semilla fija `42`, esquema en `schema.TICKET_SCHEMA`) generado con `generate_tickets`; no hay descargas. **Este proyecto no usa servicios**, así que no hay modo degradado: funciona siempre.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución en `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `check_stock(sku)` | Coincide con `catalog.stock()` para los 10 SKU y gestiona un SKU desconocido sin excepción | 10/10 SKU + 1 caso desconocido |
    | R2 | Herramienta registrada | Esquema JSON válido: `sku` en `properties` y en `required` | cumple |
    | R3 | El agente la usa | De 8 preguntas de stock: la usa **exactamente una vez** y el número que cita coincide con el stock real | ≥ 7/8 |
    | R4 | Sin regresiones | En 150 tickets del tráfico normal, `tools_used` idéntico al agente sin la regla nueva | 100 % idénticos |
    | R5 | Tres huellas reproducibles | Tus `SIGNATURES` son verdaderas para su fallo en los 20 tickets de prueba y **falsas** en los 20 tickets sanos | 3/3 fallos con 100 % sensibilidad y 0 falsos positivos |
    | R6 | Detector ciego | `detect(result)` (sin leer `injected_faults`/`grounded`/`pii_leaked`) sobre 400 tickets con fallos: precisión global ≥ 0,90 y recall de `tool_loop`, `tool_timeout`, `tool_error`, `pii_leak` ≥ 0,90 | ver celda de la rúbrica |

    > 📏 Los umbrales salen de lo que mide la solución de referencia en `mock` con semilla fija; no dependen de la velocidad de tu máquina porque el tiempo es **simulado**. La solución obtiene: R3 = 8/8, R4 = 150/150, R5 = 3/3 con 0 falsos positivos y,
    > en R6 sobre 400 tickets, precisión 1,00 y recall 1,00 en `tool_loop` (2 casos), `tool_timeout` (5), `tool_error` (14) y `pii_leak` (6); el umbral de 0,90 deja margen y los conteos son pequeños (no extraigas conclusiones estadísticas de ellos).
    """)
    code(boot("viz"))
    code(IMPORTS + '''
import json, re
from supportops import catalog
from supportops.llm.mock import ORDER_RE, SKU_RE
_ = check_stack([])      # este proyecto no necesita servicios
''')

    md("""
    ## Paso 1 · La herramienta `check_stock`

    **TODO 1.** Implementa `check_stock(sku: str) -> dict` que devuelva `{"found": True, "sku": ..., "name": ..., "units": int, "available": bool}` usando `catalog.stock()` (diccionario `sku → unidades`) y `catalog.PRODUCTS` (lista de `(sku, nombre, precio)`).
    Para un SKU desconocido devuelve `{"found": False, "sku": sku}` (**no** lances una excepción: es un resultado de negocio, no un fallo de infraestructura).
    """)
    md(hint(1, "Construye un diccionario `nombres = {sku: nombre for sku, nombre, _ in catalog.PRODUCTS}` y consulta `catalog.stock().get(sku)`. Ten cuidado: `0` unidades es un valor válido (no uses `if not units`)."))
    code('''
def check_stock(sku: str) -> dict:
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    print(check_stock("SKU-1001"), check_stock("SKU-9999"))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 2 · Registrarla con su esquema

    **TODO 2.** Crea un `ToolRegistry` con las herramientas por defecto (`default_tools()`) y **registra** `check_stock` como `Tool(name, description, parameters, fn, latency_median_s)`.
    `parameters` es un JSON Schema de objeto con la propiedad `sku` (string) **obligatoria**. Usa `latency_median_s=0.06`.
    """)
    md(hint(1, "`reg = default_tools()` y `reg.register(Tool(name=\"check_stock\", description=\"...\", parameters={...}, fn=check_stock, latency_median_s=0.06))`. Revisa cómo se ve el esquema de `issue_refund` con `reg.get('issue_refund').schema()`."))
    md(hint(2, "Esquema: `{\"type\": \"object\", \"properties\": {\"sku\": {\"type\": \"string\", \"description\": \"...\"}}, \"required\": [\"sku\"]}`."))
    code('''
def build_registry() -> ToolRegistry:
    # TODO 2: devuelve un registro con las herramientas por defecto + check_stock
    raise NotImplementedError("TODO 2")

try:
    REG = build_registry(); print(REG.names())
except NotImplementedError as e:
    REG = None; print("Pendiente:", e)
''')

    md("""
    ## Paso 3 · Enseñar al agente (mock) cuándo usarla

    El mock decide con **reglas** (`Rule`): palabras clave → pasos de herramienta → plantilla de respuesta. Observa las reglas por defecto con `default_rules()` y añade la tuya.

    **TODO 3a.** Implementa `sku_from_text(text)`: devuelve el SKU mencionado (`SKU-####`, usa `SKU_RE`) **o** el SKU del producto cuyo nombre aparece en el texto (ignora mayúsculas; compara con `catalog.PRODUCTS`, p. ej. «teclado mecánico K87» → `SKU-1001`; basta con que aparezca el nombre completo o su última palabra, p. ej. «K87», «M3»). Si no hay, `""`.

    **TODO 3b.** Implementa `build_llm()` que devuelva un `MockLLM(seed=SEED)` con una `Rule("stock", keywords=(...), steps=[ToolStep("check_stock", args=...)], answer=..., needs=..., missing_answer=..., clarify=True, priority=25)`.
    La respuesta debe decir cuántas unidades quedan (o que no hay stock / que el SKU no existe). Palabras clave sugeridas: `"stock"`, `"disponib"`, `"quedan"`, `"unidades"`.
    """)
    md(hint(1, "Mira `default_rules()` en `supportops/llm/mock.py` (puedes imprimirlo con `inspect.getsource`). Una `Rule` necesita: `intent`, `keywords` (tupla de *subcadenas* en minúsculas), `steps` (lista de `ToolStep(tool, args)` donde `args(text, results)` devuelve el dict de argumentos), `answer(text, results)` (devuelve el texto final; `results['check_stock']` es el resultado de tu herramienta), y opcionalmente `needs(text)` + `missing_answer` + `clarify=True` para pedir el dato que falta."))
    md(hint(2, "`ToolStep(\"check_stock\", lambda t, r: {\"sku\": sku_from_text(t)})`. `answer=lambda t, r: ...` con tres casos: `not r['check_stock']['found']`, `units == 0`, y el caso normal («Quedan {units} unidades de {name}»). `priority=25` hace que gane a las reglas por defecto cuando el ticket habla de stock."))
    code('''
def sku_from_text(text: str) -> str:
    # TODO 3a
    raise NotImplementedError("TODO 3a")

def build_llm() -> MockLLM:
    # TODO 3b
    raise NotImplementedError("TODO 3b")

try:
    print(sku_from_text("¿Hay stock del teclado mecánico K87?"), sku_from_text("¿Quedan unidades del SKU-1005?"), repr(sku_from_text("hola")))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 4 · Prueba funcional y *test de regresión*

    Con las piezas anteriores montamos el agente nuevo. Dos pruebas: (a) **8 preguntas de stock** y (b) **regresión**: los 150 tickets normales deben usar *exactamente las mismas herramientas* que con el agente original (una regla nueva no puede «robar» tickets de otras intenciones).

    **TODO 4.** Implementa `build_agent()` que devuelva `SupportAgent(llm=build_llm(), tools=build_registry())`. Después ejecuta la celda de pruebas (ya escrita).
    """)
    code('''
def build_agent() -> SupportAgent:
    # TODO 4
    raise NotImplementedError("TODO 4")

STOCK_Q = ["¿Hay stock del teclado mecánico K87?", "¿Quedan unidades del SKU-1005?", "¿Está disponible el ratón inalámbrico M3?", "¿Tenéis stock del SKU-1010?",
           "¿Cuántas unidades quedan de la webcam 4K?", "¿Hay disponibilidad del SSD NVMe 1 TB?", "¿Queda stock de los auriculares ANC H5?", "¿Hay stock del SKU-1003?"]

def run_stock_tests(agent) -> list[dict]:
    out = []
    for i, q in enumerate(STOCK_Q):
        r = agent.run(Ticket(f"T-stock{i}", "C-0001", "standard", "chat", q, "stock", SIM_EPOCH_S))
        sku = sku_from_text(q); real = catalog.stock().get(sku)
        out.append({"pregunta": q, "tools": r.tools_used, "units_reales": real, "usa_1_vez": r.tools_used == ["check_stock"],
                    "cita_numero": bool(re.search(rf"\\b{real}\\b", r.answer)) if real else ("no hay stock" in r.answer.lower() or "no encuentro" in r.answer.lower()), "respuesta": r.answer[:70]})
    return out

try:
    NEW_AGENT = build_agent()
    ST = pd.DataFrame(run_stock_tests(NEW_AGENT)); display(ST)
except NotImplementedError as e:
    NEW_AGENT = None; print("Pendiente:", e)
''')

    md("""
    ## Paso 5 · Reproducir tres fallos y definir su «huella»

    Ahora la parte de observabilidad. Para cada fallo (**`tool_loop`**, **`hallucination`**, **`tool_timeout`**) sobre una pregunta de stock:

    1. **TODO 5a.** `inject(kind, text)` devuelve un `Ticket` con ese fallo (`FaultSpec(kind)`), y ejecútalo con tu agente.
    2. Mira la tabla de resultados que imprime la celda siguiente (estado, pasos, latencia, tokens, `grounded`…) y **escribe tus `SIGNATURES`**: una función `lambda r: bool` por fallo basada **solo en lo observable**
       (`r.status`, `r.n_tool_calls`, `r.latency_s`, `r.steps`…). Debe ser verdadera para su fallo y **falsa** para tickets sanos (sin falsos positivos).

    **TODO 5b.** Completa el diccionario `SIGNATURES`.
    """)
    md(hint(1, "Tabla de huellas esperada (compruébala con tus datos): `tool_loop` → estado `max_steps` y tantas herramientas como `max_steps`; `hallucination` → **0 herramientas** en una pregunta que necesita una; `tool_timeout` → algún paso `tool` con `error_type == 'timeout'` (o latencia > 5 s)."))
    md(hint(2, "Ejemplos de predicados: `lambda r: r.status == 'max_steps'`; `lambda r: r.n_tool_calls == 0 and r.status == 'ok'`; `lambda r: any(s.kind == 'tool' and s.error_type == 'timeout' for s in r.steps)`. Cuidado: «0 herramientas» también ocurre en la pregunta de aclaración (sin SKU): usa solo preguntas con SKU para esta prueba."))
    code('''
def inject(kind: str, text: str, i: int = 0) -> Ticket:
    # TODO 5a: ticket con el fallo `kind` (FaultSpec(kind)) y el texto dado
    raise NotImplementedError("TODO 5a")

SIGNATURES = {
    # TODO 5b: predicado r -> bool por fallo, basado solo en lo observable
    "tool_loop": None,
    "hallucination": None,
    "tool_timeout": None,
}

try:
    rows = []
    for kind in ["tool_loop", "hallucination", "tool_timeout"]:
        r = NEW_AGENT.run(inject(kind, "¿Hay stock del teclado mecánico K87?"))
        rows.append({"fallo": kind, "estado": r.status, "pasos": len(r.steps), "herramientas": r.n_tool_calls, "latencia_s": round(r.latency_s, 2), "tokens_in": r.input_tokens,
                     "errores_de_paso": [s.error_type for s in r.steps if s.error_type], "fundamentada": r.grounded})
    display(pd.DataFrame(rows).set_index("fallo"))
except (NotImplementedError, AttributeError, TypeError) as e:
    print("Pendiente (completa los TODO anteriores):", type(e).__name__, e)
''')

    md("""
    ## Paso 6 · Un detector ciego

    **TODO 6.** Implementa `detect(r) -> set[str]`: dado **solo** el `AgentResult` (sin `injected_faults`, `grounded` ni `pii_leaked`, que son la verdad de terreno), devuelve el conjunto de fallos que sospechas de entre
    `{"tool_loop", "tool_timeout", "tool_error", "llm_error", "pii_leak", "hallucination", "latency_spike"}`.
    Pistas de dónde mirar: el **estado**, los **pasos con error** (`s.error_type`), el **número de herramientas**, la **latencia** y el **texto de la respuesta** (¿contiene un correo o una tarjeta?).
    Luego evalúa precisión y recall frente a la verdad de terreno en 400 tickets con fallos de fondo.
    """)
    md(hint(1, "Reglas sencillas: `status=='max_steps'` → `tool_loop`; paso `tool` con `error_type=='timeout'` → `tool_timeout`; otro `error_type` en paso `tool` → `tool_error`; `status=='error'` → `llm_error`; regex de correo (`[\\\\w.]+@[\\\\w.]+`) o de tarjeta (`\\\\d{4} \\\\d{4} \\\\d{4} \\\\d{4}`) en la respuesta → `pii_leak`."))
    md(hint(2, "`hallucination`: la respuesta afirma datos concretos (un número de pedido `ORD-`, un seguimiento `TRK`, «aprobado», «unidades») pero `n_tool_calls == 0`. `latency_spike`: latencia por encima de un umbral robusto (p. ej. mediana de sanos × 3), pero ojo con los falsos positivos de la cola natural."))
    code('''
import re

def detect(r) -> set[str]:
    # TODO 6
    raise NotImplementedError("TODO 6")

def evaluate_detector(detect_fn, n=400):
    tk = generate_tickets(n, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)
    res = run_tickets(NEW_AGENT or SupportAgent(), tk)
    kinds = list(FAULT_KINDS)
    tp = dict.fromkeys(kinds, 0); fp = dict.fromkeys(kinds, 0); fn = dict.fromkeys(kinds, 0)
    for r in res:
        truth, pred = set(r.injected_faults), detect_fn(r)
        for k in kinds:
            tp[k] += (k in truth) and (k in pred); fp[k] += (k not in truth) and (k in pred); fn[k] += (k in truth) and (k not in pred)
    T = pd.DataFrame({"verdad": {k: tp[k] + fn[k] for k in kinds}, "TP": tp, "FP": fp, "FN": fn})
    T["recall"] = (T.TP / T.verdad.replace(0, np.nan)).round(2); T["precisión"] = (T.TP / (T.TP + T.FP).replace(0, np.nan)).round(2)
    return T, (sum(tp.values()) / max(1, sum(tp.values()) + sum(fp.values())))

try:
    TABLE, PREC = evaluate_detector(detect)
    display(TABLE); print(f"precisión global = {PREC:.2f}")
except NotImplementedError as e:
    TABLE, PREC = None, None; print("Pendiente:", e)
''')

    md("""
    ## Paso 7 · Rúbrica

    Ejecuta la celda para puntuar tu trabajo. Los umbrales provienen de la solución de referencia.
    """)
    code('''
def run_rubric():
    rows = []
    def add(r, desc, ok, detail=""): rows.append({"criterio": r, "descripción": desc, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": detail})
    # R1
    try:
        ok1 = all((lambda d, s: d.get("found") and d["units"] == s and d["available"] == (s > 0))(check_stock(k), v) for k, v in catalog.stock().items()) and check_stock("SKU-9999") == {"found": False, "sku": "SKU-9999"}
        add("R1", "check_stock correcta (10 SKU + desconocido)", ok1)
    except Exception as e: add("R1", "check_stock correcta", False, repr(e)[:80])
    # R2
    try:
        sch = REG.get("check_stock").schema()["parameters"]
        add("R2", "esquema válido (sku requerido)", "sku" in sch["properties"] and "sku" in sch.get("required", []))
    except Exception as e: add("R2", "esquema válido", False, repr(e)[:80])
    # R3
    try:
        ST = pd.DataFrame(run_stock_tests(NEW_AGENT)); n = int((ST.usa_1_vez & ST.cita_numero).sum())
        add("R3", "≥ 7/8 preguntas de stock bien resueltas", n >= 7, f"{n}/8")
    except Exception as e: add("R3", "preguntas de stock", False, repr(e)[:80])
    # R4
    try:
        tk = generate_tickets(150, seed=SEED); base = run_tickets(SupportAgent(), tk); new = run_tickets(NEW_AGENT, tk)
        same = sum(a.tools_used == b.tools_used for a, b in zip(base, new))
        add("R4", "sin regresiones (100 % idénticos)", same == len(tk), f"{same}/{len(tk)}")
    except Exception as e: add("R4", "regresión", False, repr(e)[:80])
    # R5
    try:
        det = {}
        for kind, pred in SIGNATURES.items():
            sick = [NEW_AGENT.run(inject(kind, STOCK_Q[i % 8] if i % 8 != 1 else "¿Hay stock del SKU-1003?", i)) for i in range(20)]
            healthy = [NEW_AGENT.run(Ticket(f"T-h{i}", "C-0001", "standard", "chat", STOCK_Q[i % 8], "stock", SIM_EPOCH_S + i)) for i in range(20)]
            det[kind] = (sum(map(pred, sick)) / 20, sum(map(pred, healthy)))
        add("R5", "huellas: sensibilidad 100 % y 0 falsos positivos", all(s == 1.0 and f == 0 for s, f in det.values()), str(det))
    except Exception as e: add("R5", "huellas", False, repr(e)[:80])
    # R6
    try:
        T, prec = evaluate_detector(detect)
        rec = {k: float(T.loc[k, "recall"]) for k in ["tool_loop", "tool_timeout", "tool_error", "pii_leak"]}
        add("R6", "detector: precisión ≥ 0,90 y recall ≥ 0,90", prec >= 0.90 and all(v >= 0.90 for v in rec.values()), f"precisión={prec:.2f} recall={rec}")
    except Exception as e: add("R6", "detector ciego", False, repr(e)[:80])
    return pd.DataFrame(rows).set_index("criterio")

display(run_rubric())
''')

    md("""
    ---
    ## Retos extra (nivel experto)

    1. **Guarda de bucles en el agente:** crea `class GuardedAgent(SupportAgent)` que detecte la *misma herramienta con los mismos argumentos* repetida ≥ 3 veces y corte con una respuesta de escalado. Mide el ahorro de tokens/coste en el tráfico con `tool_loop` y los falsos positivos en tráfico sano.
    2. **Idempotencia del reembolso:** protege `issue_refund` con una *clave de idempotencia* (`order_id`) para que un reintento tras un timeout no duplique el reembolso. Demuéstralo con `tool_timeout` + reintento.
    3. **Presupuesto de pasos por intención:** calcula con 1000 tickets el percentil 99 de pasos por intención y propón un `max_steps` distinto por intención. ¿Cuántos falsos cortes provoca?
    4. **Cambia de proveedor:** con una clave propia (solo por variables de entorno), ejecuta las 8 preguntas de stock con `LLM_PROVIDER=anthropic|openai|ollama`. ¿Qué diferencias de pasos, tokens y latencia ves frente al mock? (No es parte de la rúbrica.)

    ## Reflexión (producción e hilo conductor)

    - ⚠️ **Validez:** en el mock la alucinación usa frases fijas, por eso un *regex* la detecta al 100 %. Con un LLM real no existe esa regularidad: una alucinación solo se detecta comparando la respuesta con las fuentes (evaluación online, módulo 14). ¿Qué parte de tu detector **sí** generalizaría a producción (pista: PII por patrones, bucles por repetición, errores por estado de los pasos) y cuál no?
    - Tu detector ciego, ¿qué fallos **no puede** detectar con datos reales y qué dato adicional necesitaría?
    - Si el 100 % de tus herramientas fallara a la vez, ¿cuántos de los *síntomas* que has definido se activarían? ¿Cuál sería la primera alerta útil?
    - Has añadido una herramienta y un test de regresión: ¿qué parte de la telemetría del módulo 03 te habría avisado *en producción* de que la regla nueva robaba tickets?
    - En el módulo 03 instrumentarás este mismo agente. ¿Qué atributos pondrías en el span de `check_stock` para depurar discrepancias de inventario?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable.
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
NAMES = {sku: nombre for sku, nombre, _ in catalog.PRODUCTS}

# TODO 1
def check_stock(sku: str) -> dict:
    units = catalog.stock().get(sku)
    if units is None:
        return {"found": False, "sku": sku}
    return {"found": True, "sku": sku, "name": NAMES[sku], "units": units, "available": units > 0}

# TODO 2
def build_registry() -> ToolRegistry:
    reg = default_tools()
    reg.register(Tool(name="check_stock", description="Consulta las unidades en stock de un producto por su SKU (SKU-####).",
                      parameters={"type": "object", "properties": {"sku": {"type": "string", "description": "SKU del producto"}}, "required": ["sku"]},
                      fn=check_stock, latency_median_s=0.06))
    return reg

# TODO 3a
def sku_from_text(text: str) -> str:
    m = SKU_RE.search(text)
    if m:
        return m.group(0)
    low = text.lower()
    for sku, nombre, _ in catalog.PRODUCTS:
        if nombre.lower() in low or nombre.lower().split()[-1] in low.replace("?", " ").replace(",", " ").split():
            return sku
    return ""

# TODO 3b
def build_llm() -> MockLLM:
    def answer(t, r):
        s = r["check_stock"]
        if not s.get("found"):
            return f"No encuentro el producto {s['sku']} en el catálogo."
        if s["units"] == 0:
            return f"Ahora mismo no hay stock de {s['name']} ({s['sku']}). ¿Quiere que le avisemos cuando vuelva a estar disponible?"
        return f"Quedan {s['units']} unidades de {s['name']} ({s['sku']})."
    llm = MockLLM(seed=SEED)
    llm.add_rule(Rule("stock", keywords=("stock", "disponib", "quedan", "unidades"),
                      steps=[ToolStep("check_stock", lambda t, r: {"sku": sku_from_text(t)})], answer=answer,
                      needs=lambda t: bool(sku_from_text(t)), missing_answer="¿De qué producto quiere consultar el stock? Indíqueme su nombre o su SKU.",
                      clarify=True, priority=25))
    return llm

# TODO 4
def build_agent() -> SupportAgent:
    return SupportAgent(llm=build_llm(), tools=build_registry())

# TODO 5a / 5b
def inject(kind: str, text: str, i: int = 0) -> Ticket:
    return Ticket(f"T-{kind}-{i}", "C-0001", "standard", "chat", text, "stock", SIM_EPOCH_S + i, faults=[FaultSpec(kind)])

SIGNATURES = {
    "tool_loop": lambda r: r.status == "max_steps" and r.n_tool_calls >= 5,
    "hallucination": lambda r: r.status == "ok" and r.n_tool_calls == 0 and r.n_llm_calls == 1,
    "tool_timeout": lambda r: any(s.kind == "tool" and s.error_type == "timeout" for s in r.steps),
}

# TODO 6: detector ciego
EMAIL, CARD = re.compile(r"[\\w.+-]+@[\\w-]+\\.\\w+"), re.compile(r"\\b\\d{4} \\d{4} \\d{4} \\d{4}\\b")
CLAIMS = re.compile(r"TRK\\d+|aprobado|unidades|garantía|días")   # afirmaciones concretas (sin «ORD-»: lo usa también la pregunta de aclaración)

def detect(r) -> set[str]:
    found: set[str] = set()
    errs = [s.error_type for s in r.steps if s.kind == "tool" and s.error_type]
    if r.status == "max_steps": found.add("tool_loop")
    if "timeout" in errs: found.add("tool_timeout")
    if any(e and e != "timeout" for e in errs): found.add("tool_error")
    if any(s.kind == "llm" and s.status == "error" for s in r.steps): found.add("llm_error")   # también los transitorios (el reintento los oculta en el estado)
    if EMAIL.search(r.answer) or CARD.search(r.answer): found.add("pii_leak")
    if r.status == "ok" and r.n_tool_calls == 0 and CLAIMS.search(r.answer): found.add("hallucination")
    if r.latency_s > 8 and not (found & {"tool_loop", "tool_timeout", "llm_error"}): found.add("latency_spike")
    return found

NEW_AGENT = build_agent()
REG = build_registry()
display(pd.DataFrame(run_stock_tests(NEW_AGENT)))
TABLE, PREC = evaluate_detector(detect); display(TABLE); print(f"precisión global = {PREC:.2f}")
display(run_rubric())
''')
    nb.save(out)


README = """# Módulo 01 · El agente base: SupportOps v0

🟢 Básico · ≈ 4 h 20 min · **No necesita servicios de Compose** (todo simulado; funciona en Colab).

## Qué aprenderás
- Qué es un agente (bucle LLM + herramientas) frente a una llamada simple y a un workflow; el bucle escrito a mano en ≈ 25 líneas.
- **SupportOps v0**: el agente de soporte del curso (`supportops/`), sin instrumentar, con reintentos, herramientas simuladas y RAG (TF-IDF).
- Proveedor LLM agnóstico: `LLM_PROVIDER=mock|anthropic|openai|ollama` (el `mock` determinista es el valor por defecto y el de las rúbricas).
- Tokens y coste de un agente: por qué el contexto crece y el coste se dispara con los pasos.
- **Tráfico sintético** reproducible (semilla, esquema, ventanas de incidente) y **siete fallos inyectados** (latencia, errores del proveedor, errores y timeouts de herramientas, alucinación, bucle de herramientas, fuga de PII).
- Los **puntos de extensión** donde se instrumentará el agente (módulo 03) y un `RecordingInstrumentor` para ver el modelo de datos.

## Archivos
| Archivo | Contenido |
|---|---|
| `01_agente_base.ipynb` | Lección (teoría + código + 12 gráficos + autoevaluación) |
| `01_proyecto_agente_base.ipynb` | Proyecto: añadir la herramienta `check_stock` sin regresiones, definir la «huella» de 3 fallos y construir un detector ciego |

## Servicios necesarios
Ninguno. (`pip install -e agent-observability-course[viz]` lo hace el primer bloque de cada notebook.)

## Variables de entorno (opcionales)
`LLM_PROVIDER`, `LLM_MODEL`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `OLLAMA_HOST`, `SUPPORTOPS_SEED` (ver `_tools/INTERFACES.md`). **Nunca** pongas claves en un notebook.

## Lecturas
- Anthropic, *Building effective agents* — <https://www.anthropic.com/engineering/building-effective-agents>
- Yao et al., *ReAct* — <https://arxiv.org/abs/2210.03629> · Lewis et al., *RAG* — <https://arxiv.org/abs/2005.11401>
- Anthropic, *Tool use with Claude* — <https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview>

## Siguiente
`02_tres_pilares`: traces, metrics y logs, el modelo de datos de OpenTelemetry y las *golden signals* aplicadas a agentes.
"""

if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    (COURSE / MOD / "README.md").write_text(README, encoding="utf-8")
    build_lesson()
    build_project()
