"""Genera el módulo 00_entorno: README, lección y proyecto.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_00.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import BOOT, COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "00_entorno"


# =====================================================================================================================
# LECCIÓN
# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "00_entorno.ipynb", "Módulo 00 · Entorno: por qué los agentes rompen el monitoreo y cómo levantar el stack")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 00 · Entorno: por qué los agentes rompen el monitoreo clásico y cómo levantar el stack

    | | |
    |---|---|
    | **Nivel** | 🟢 Básico |
    | **Duración estimada** | ≈ 4 h (lección ≈ 2 h 15 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Lectura y gráficos: ninguno (modo degradado con datos pregrabados). Parte práctica: perfil `core` (+ `metrics`) |
    | **RAM aproximada** | `core` ≈ 0,4 GB en reposo (≈ 1 GB con carga); `core`+`metrics` ≈ +0,05 GB; imágenes ≈ 3,5 GB de disco |
    | **Prerrequisitos** | Python sólido. Nada más: ni Docker, ni agentes, ni observabilidad |
    | **Colab** | El badge sirve para las partes conceptuales y los gráficos (modo degradado). El stack con Docker corre en **tu máquina** |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** con datos por qué un agente LLM en producción rompe cuatro supuestos del monitoreo clásico (determinismo, longitud de la cadena, coste por petición y significado de «éxito»).
    2. **Dibujar** el mapa del stack del curso (aplicación → Collector → Tempo/Loki/Prometheus → Grafana) y justificar el papel de cada pieza.
    3. **Distinguir** imagen, contenedor, volumen, red, puerto y perfil de Compose, y **leer** un `docker-compose.yml` línea a línea.
    4. **Levantar** el stack con perfiles de Compose y **verificar** su salud (listo ≠ arrancado).
    5. **Enviar a mano** una traza, un log y una métrica en formato OTLP/JSON y **encontrarlos** en Tempo, Loki y Prometheus.
    6. **Diagnosticar** los fallos típicos de arranque (puertos, volúmenes, orden de arranque, URLs dentro de la red de Compose).
    7. **Calcular** un presupuesto de RAM del stack para tu máquina.
    """)

    md("""
    ## Cómo usar este notebook

    - Se ejecuta **de arriba abajo** con el kernel local de Jupyter o VS Code, junto al stack de Docker Compose del curso.
    - Si el stack no está arriba, las celdas que lo necesitan **no se rompen**: usan *modo degradado* (datos pregrabados del repo, con el mismo esquema) y te avisan.
    - `FAST_DEV_RUN = True` usa pocos tickets sintéticos para iterar rápido; ponlo en `False` para los tamaños del texto.
    - Verás tres tipos de cajas: **👀 Qué debes observar** (tras cada gráfico), **🧠 Secretos de la élite** y **⚠️ Cuidado**.
    - **Nunca** pongas API keys en un notebook. Este curso usa por defecto un LLM *simulado* (`LLM_PROVIDER=mock`): determinista, gratis y sin red.
    """)

    md("""
    ## 🔤 Glosario mínimo (para empezar sin saber nada del tema)

    Estas palabras aparecerán en la primera sección; no hace falta memorizarlas, vuelve aquí si alguna te frena. Todas se desarrollan después (entre paréntesis, dónde).

    | Palabra | En una frase | Analogía |
    |---|---|---|
    | **LLM** | Modelo de lenguaje: recibe texto y devuelve texto (lo llamas por API) | Una función `texto -> texto` cara y no determinista |
    | **Token** | Trozo de texto (≈ ¾ de palabra) que el LLM lee/escribe; **se factura por token** | Los «bytes» de una llamada a un LLM |
    | **Agente** | Programa que repite «el LLM decide → se ejecuta una *herramienta* (*tool call*) → se vuelve a preguntar al LLM» hasta terminar (módulo 01) | Un `while` cuyo cuerpo lo decide el modelo |
    | **Telemetría** | Los datos que tu programa emite sobre sí mismo mientras corre (trazas, métricas, logs) | `print`/`logging` con estructura y estándar |
    | **Span / traza (*trace*)** | Un *span* es un paso con inicio y duración; una *traza* es el árbol de spans de una petición (módulo 02-03) | El resultado de `cProfile` de **una** petición, como árbol |
    | **Percentil (p50, p95, p99)** | «El 95 % de las peticiones tarda *menos* que esto». p50 = mediana | `np.percentile(lat, 95)` |
    | **SLI / SLO** | Indicador que mides (p. ej. % de peticiones correctas) / objetivo que te comprometes a cumplir (≥ 99 %) (módulo 16) | Métrica de validación / umbral de aceptación de un modelo |
    | **OTLP** | Formato y protocolo estándar de OpenTelemetry para enviar telemetría | «El JSON/gRPC común» entre tu app y el Collector |
    | **Backend** (de observabilidad) | Base de datos donde se guarda y consulta la telemetría (Tempo, Loki, Prometheus) | El almacén de features de tu pipeline |
    | **Dashboard** | Pantalla de gráficos sobre esos datos (Grafana) | Un notebook de exploración siempre encendido |
    """)

    code(boot("viz"))
    code(IMPORTS + '''
STACK = check_stack("core")        # ¿qué servicios están arriba? si no: comando exacto de Compose y modo degradado
''')

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ---
    # 1 · Por qué los agentes rompen el monitoreo clásico

    ## 1.1 Intuición: de «un endpoint» a «un empleado que improvisa»

    Un servicio web clásico se parece a una **función pura con efectos secundarios conocidos**: misma entrada, mismo camino de código,
    latencia casi constante, coste fijo por petición y un fallo es casi siempre un código `5xx` o una excepción.

    Un **agente LLM** se parece más a un *empleado nuevo al que le das una tarea en lenguaje natural*: decide qué consultar, en qué orden y
    cuántas veces; puede equivocarse con total seguridad en sí mismo, y cada decisión te cuesta dinero (tokens). Tres analogías que usaremos todo el curso:

    | Si vienes de… | Lo que ya sabes | Lo que cambia con un agente |
    |---|---|---|
    | **Ciencia de datos / ML** | Evalúas un modelo *offline* con un dataset y métricas (accuracy, F1…); vigilas *drift* | En producción no hay etiqueta inmediata: la «métrica de calidad» hay que **inferirla online** (módulo 14) y el comportamiento depende de prompts, herramientas y contexto, no solo de pesos |
    | **Backend / microservicios** | Latencia p95, tasa de errores, *tracing* distribuido entre servicios | Los «servicios» ahora son **llamadas a LLM y herramientas elegidas en tiempo de ejecución**; el grafo de llamadas no está fijado en el código |
    | **DevOps / SRE** | SLOs, alertas, on-call, *runbooks* | El SLI «HTTP 200» deja de significar «el cliente quedó bien atendido»; aparecen SLIs de calidad y de coste |

    Vamos a **medirlo** en lugar de creerlo. Usaremos el agente de soporte del curso (**SupportOps**) como *caja negra* (en el módulo 01 lo abrimos por dentro) con tráfico sintético
    de semilla fija: 35 % consultas de pedido, 20 % reembolsos, 35 % preguntas a la base de conocimiento y 10 % escalados, con fallos de fondo realistas
    (latencia, errores del proveedor, alucinaciones, bucles de herramientas, fugas de datos personales).
    """)

    code('''
N = 300 if FAST_DEV_RUN else 800
tickets = generate_tickets(N, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)      # tráfico sintético con fallos de fondo
agent = SupportAgent()                                                          # LLM_PROVIDER=mock por defecto
results = run_tickets(agent, tickets)                                           # tiempo SIMULADO: tarda milisegundos
df = pd.DataFrame(to_rows(tickets, results))
df["steps"] = df.n_llm_calls + df.n_tool_calls                                  # pasos = llamadas al LLM + herramientas
print(f"{len(df)} tickets simulados · columnas: {list(df.columns)}")
df[["ticket_id", "intent_true", "status", "latency_s", "steps", "input_tokens", "cost_usd", "injected_faults"]].head(8)
''')

    md("""
    ### Grieta 1 · No determinismo: la misma tarea no siempre cuesta lo mismo

    En un endpoint clásico, el histograma de latencia de una ruta tiene una «joroba» estrecha. Veamos el del agente, separado por intención del cliente.
    """)

    code('''
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
order = ["order_status", "kb_question", "refund", "escalation"]
data = [df.loc[df.intent_true == k, "latency_s"] for k in order]
axes[0].boxplot(data, tick_labels=order, showfliers=True, flierprops=dict(marker=".", alpha=.5))
axes[0].set_yscale("log"); axes[0].set_ylabel("latencia de extremo a extremo (s, escala log)")
axes[0].set_title("Latencia por intención del cliente")
lat = np.sort(df.latency_s.values)
axes[1].plot(lat, np.arange(1, len(lat) + 1) / len(lat), color=viz.PALETTE["traces"], lw=2)
for q, c in [(0.5, "ok"), (0.95, "warn"), (0.99, "error")]:
    v = np.quantile(lat, q); axes[1].axvline(v, color=viz.PALETTE[c], ls="--"); axes[1].text(v, 0.05 + 0.1 * q, f" p{int(q*100)}={v:.1f}s", color=viz.PALETTE[c])
axes[1].axvline(lat.mean(), color="gray", ls=":"); axes[1].text(lat.mean(), 0.5, f" media={lat.mean():.1f}s", color="gray")
axes[1].set_xscale("log"); axes[1].set_xlabel("latencia (s, escala log)"); axes[1].set_ylabel("fracción de peticiones ≤ x"); axes[1].set_title("ECDF de latencia")
plt.tight_layout(); plt.show()
print(f"p50={np.quantile(lat,.5):.2f}s  p99={np.quantile(lat,.99):.2f}s  máx={lat.max():.1f}s  →  el máximo es {lat.max()/np.quantile(lat,.5):.0f}× la mediana")
''')
    md(observe("""
    - Las cajas (percentiles 25-75) son relativamente compactas, pero **los puntos sueltos** llegan a más de 10× la mediana: son peticiones con herramientas lentas, reintentos o bucles.
    - La **media** (línea gris) queda a la derecha de la mediana: la cola pesada la arrastra. Una alerta sobre «latencia media» tardaría en saltar y escondería a los usuarios peor atendidos.
    - Conclusión: para un agente hay que vigilar **percentiles altos** (p95/p99) *y* mirar los casos extremos individuales (trazas), no solo promedios.
    """))

    md("""
    ### Grieta 2 · La longitud de la cadena es variable

    Un endpoint hace *una* consulta a la base de datos y devuelve. Un agente decide *en tiempo de ejecución* cuántos pasos da (cada paso = una llamada al LLM o a una herramienta).
    """)
    code('''
steps_count = df.steps.value_counts().sort_index()
fig, ax = plt.subplots(figsize=(8, 3.6))
colors = [viz.PALETTE["error"] if k >= 10 else viz.PALETTE["traces"] for k in steps_count.index]
ax.bar(steps_count.index.astype(str), steps_count.values, color=colors)
for x, v in zip(steps_count.index.astype(str), steps_count.values):
    ax.text(x, v, str(v), ha="center", va="bottom", fontsize=9)
ax.set_xlabel("pasos por petición (llamadas al LLM + herramientas)"); ax.set_ylabel("nº de peticiones")
ax.set_title("La longitud de la cadena NO es constante"); plt.show()
loops = df[df.steps >= 10]
print(f"{len(loops)} peticiones con ≥10 pasos (bucles de herramientas): gastan {loops.input_tokens.mean()/df.input_tokens.median():.1f}× los tokens de entrada de una petición mediana")
''')
    md(observe("""
    - La mayoría de peticiones tiene **3 pasos** (LLM → herramienta → LLM). Pero hay una barra roja con **12 pasos**: el agente se quedó dando vueltas hasta agotar su presupuesto de pasos.
    - Esas pocas peticiones cuestan *muchísimos más tokens* (cada vuelta reenvía todo el contexto). Un monitor de «peticiones por segundo» no las distingue de las normales.
    - Idea clave: en un agente, **la unidad de trabajo es el paso, no la petición**. Los trazas (módulo 03) existen precisamente para ver esa cadena.
    """))

    md("""
    ### Grieta 3 · El coste por petición es variable y de cola pesada

    En un servicio clásico el coste por petición es prácticamente constante (CPU/memoria); en un agente es **proporcional a los tokens**, y estos dependen de lo que el agente decida hacer.
    """)
    code('''
c = np.sort(df.cost_usd.values)[::-1]
share = np.cumsum(c) / c.sum()
x = np.arange(1, len(c) + 1) / len(c)
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
ax[0].hist(df.cost_usd * 1000, bins=40, color=viz.PALETTE["metrics"]); ax[0].set_yscale("log")
ax[0].set_xlabel("coste de la petición (milésimas de USD, precios simulados)"); ax[0].set_ylabel("nº de peticiones (log)"); ax[0].set_title("Distribución del coste por petición")
ax[1].plot(x * 100, share * 100, color=viz.PALETTE["metrics"], lw=2); ax[1].plot([0, 100], [0, 100], "k:", lw=1)
top5 = share[int(0.05 * len(c)) - 1] * 100
ax[1].scatter([5], [top5], color=viz.PALETTE["error"], zorder=3); ax[1].annotate(f"el 5 % más caro\\n= {top5:.0f} % del gasto", (5, top5), (28, top5 + 8), arrowprops=dict(arrowstyle="->"))
ax[1].set_xlabel("% de peticiones (de más a menos caras)"); ax[1].set_ylabel("% acumulado del coste"); ax[1].set_title("Concentración del gasto")
plt.tight_layout(); plt.show()
print(f"coste máx / mediana = {c.max()/np.median(c):.1f}×")
''')
    md(observe("""
    - La distribución tiene cola derecha: unas pocas peticiones cuestan **varias veces** la mediana.
    - La curva de concentración queda **por encima de la diagonal**: el 5 % más caro se lleva ≈ el doble de lo que le «tocaría» (≈ 10 % del gasto). Con un modelo caro o prompts largos esa desigualdad crece; por eso el módulo 13 (FinOps) atribuye coste *por petición, cliente y función*.
    - Una métrica agregada de «coste total diario» te avisa tarde y no dice **quién** lo causa.
    """))

    md("""
    ### Grieta 4 · «200 OK» ya no significa «éxito»

        > 🤔 **Predice antes de ejecutar.** Del tráfico sintético, ¿qué porcentaje de peticiones crees que acaba con una respuesta incorrecta o insegura **sin** dar ningún error (1 %, 5 %, 15 %)? Anota tu número y compáralo con el gráfico: calibrar tu intuición es parte del oficio.

Un monitor clásico cuenta como fallo lo que termina en error (excepción, `5xx`, *timeout*). Pero un agente puede devolver una respuesta **fluida, rápida y completamente inventada**,
    o filtrar datos personales de otro cliente… con estado `ok`. Comparemos lo que ve el monitoreo clásico con la realidad (en SupportOps conocemos la verdad de terreno porque *nosotros* inyectamos los fallos).
    """)
    code('''
classic_fail = df.status.isin(["error", "max_steps"])
quality_fail = (~df.grounded) | df.pii_leaked              # respuesta inventada o con datos personales ajenos
degraded = df.status.eq("degraded")                          # una herramienta falló pero hubo respuesta (fallo parcial)
silent = quality_fail & ~classic_fail
labels = ["Lo que ve el monitoreo clásico\\n(tasa de error)", "Lo que realmente falla\\n(misma ventana de tráfico)"]
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.barh(0, classic_fail.mean() * 100, color=viz.PALETTE["error"], label="errores visibles (error / max_steps)")
ax.barh(1, classic_fail.mean() * 100, color=viz.PALETTE["error"])
ax.barh(1, silent.mean() * 100, left=classic_fail.mean() * 100, color=viz.PALETTE["warn"], label="«OK» pero con respuesta inventada o con PII ajena (invisible)")
ax.barh(1, degraded.mean() * 100, left=(classic_fail.mean() + silent.mean()) * 100, color=viz.PALETTE["neutral"], alpha=.55, label="fallo parcial de herramienta (estado «degraded»)")
ax.set_yticks([0, 1]); ax.set_yticklabels(labels); ax.set_xlabel("% de peticiones"); ax.invert_yaxis()
ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.22), fontsize=8, ncol=1)
ax.set_title("Un dashboard de HTTP/errores subestima los problemas reales"); plt.tight_layout(); plt.show()
print(f"tasa de error clásica: {classic_fail.mean():.1%} · respuestas malas con estado OK: {silent.mean():.1%} · fallos parciales: {degraded.mean():.1%}")
print(f"SLI «sin errores» = {1-classic_fail.mean():.1%}  vs  SLI «respuesta correcta y segura» = {1-quality_fail.mean():.1%}")
''')
    md(observe("""
    - La barra superior (lo que alerta hoy en casi cualquier empresa) es **mucho más corta** que la inferior. La diferencia amarilla son respuestas que *parecen* correctas.
    - Dos SLIs distintos cuentan historias distintas: «sin errores» puede estar en verde mientras «correcto y seguro» está en rojo. Esto motiva la **calidad online** (módulos 14-15) y la **privacidad** (módulo 20).
    - En producción real no tienes la columna `grounded`: tendrás que *estimarla* con evaluadores, feedback de usuarios o reglas. Aquí la usamos para enseñarte qué buscar.
    """))

    md("""
    ### Resumen: las cinco grietas

    | # | Supuesto clásico | En un agente | Lo que necesitas | Módulos |
    |---|---|---|---|---|
    | 1 | Latencia estable | Cola pesada, depende del camino elegido | Percentiles + trazas de casos extremos | 02, 03, 07 |
    | 2 | Camino de código fijo | Cadena de longitud variable, bucles posibles | Trazas con un span por paso | 03, 04 |
    | 3 | Coste ≈ constante | Coste ∝ tokens (variable y concentrado) | Métricas de tokens/coste con atribución | 09, 13 |
    | 4 | Éxito = sin error | Respuestas fluidas pero erróneas o inseguras | Evaluación online, señales de calidad | 14, 15 |
    | 5 | Fallo = excepción | Fallos parciales silenciosos (herramienta caída + respuesta de cortesía) | Errores por span y logs correlacionados | 02, 08 |

    Para ver todo eso necesitamos un **laboratorio de observabilidad** de verdad. Lo construimos ahora.
    """)

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ---
    # 2 · Mapa del stack del curso

    ## 2.1 Las tres señales en una línea (las estudiamos a fondo en el módulo 02)

    - **Trazas (traces)**: *«¿qué camino siguió esta petición y dónde tardó?»* — un árbol de *spans* con tiempos.
    - **Métricas (metrics)**: *«¿cuántas, con qué frecuencia, qué tan lentas en agregado?»* — series numéricas baratas, ideales para alertas.
    - **Logs**: *«¿qué ocurrió exactamente en este instante?»* — eventos con texto y campos.

    ## 2.2 El stack

    | Pieza | Rol | Analogía que ya conoces |
    |---|---|---|
    | **OpenTelemetry (SDK)** | Estándar abierto (API, SDK, protocolo OTLP) para **generar** telemetría desde tu código | El `logging` de Python, pero para las tres señales y con formato común |
    | **OTel Collector** | Proceso que **recibe, transforma y reenvía** telemetría | Un *router/ETL* de telemetría; como el *feature pipeline* entre la fuente y el almacén |
    | **Tempo** | Base de datos de **trazas** (consulta con TraceQL) | Jaeger/Zipkin, con almacenamiento barato en objetos |
    | **Loki** | Base de datos de **logs** (consulta con LogQL) | Un «grep distribuido» indexado solo por etiquetas, no por el texto |
    | **Prometheus** (o Mimir) | Base de datos de **métricas** (PromQL) | El almacén de series temporales del SRE clásico |
    | **Grafana** | **Visualización**, exploración y alertas sobre todos los anteriores | El *notebook* de la operación: paneles + exploración ad hoc |
    | **Pyroscope** (opcional) | **Profiling continuo**: dónde gasta CPU tu código (módulo 17) | `cProfile` siempre encendido y consultable |
    """)

    code('''
fig, ax = viz.canvas(12, 5.2, (0, 100), (0, 46))
app = viz.box(ax, 1, 18, 17, 11, "App SupportOps\\n(SDK OpenTelemetry)", viz.PALETTE["neutral"], bold=True)
col = viz.box(ax, 28, 18, 17, 11, "OTel Collector\\nreceivers → processors\\n→ exporters", viz.PALETTE["neutral"], bold=True)
tempo = viz.box(ax, 58, 34, 16, 8, "Tempo\\n(trazas)", viz.PALETTE["traces"], bold=True)
loki = viz.box(ax, 58, 22, 16, 8, "Loki\\n(logs)", viz.PALETTE["logs"], bold=True)
prom = viz.box(ax, 58, 10, 16, 8, "Prometheus\\n(métricas)", viz.PALETTE["metrics"], bold=True)
pyro = viz.box(ax, 58, -1, 16, 8, "Pyroscope\\n(perfiles)", viz.PALETTE["profiles"], bold=True)
graf = viz.box(ax, 84, 16, 15, 14, "Grafana\\nExplore · dashboards\\n· alertas", viz.PALETTE["dark"], bold=True)
viz.arrow(ax, viz.right(app), viz.left(col), "OTLP\\n:4317 gRPC · :4318 HTTP", fontsize=8)
for b, c, lab in [(tempo, "traces", "trazas"), (loki, "logs", "logs OTLP"), (prom, "metrics", "métricas :8889")]:
    viz.arrow(ax, (col[0] + col[2] + 0.3, col[1] + col[3] / 2), viz.left(b), "", viz.PALETTE[c], rad=0.0)
    viz.arrow(ax, viz.right(b), (graf[0] - 0.3, graf[1] + graf[3] / 2 + (b[1] - 20) * 0.1), "", viz.PALETTE[c], rad=0.0, dashed=True)
viz.arrow(ax, viz.right(app), viz.left(pyro), "", viz.PALETTE["profiles"], rad=0.25, dashed=True)
viz.arrow(ax, viz.right(pyro), (graf[0] - 0.3, graf[1] + 1), "", viz.PALETTE["profiles"], rad=-0.15, dashed=True)
ax.text(66, 43.2, "[perfil core] :3200", ha="center", fontsize=8); ax.text(66, 31.2, "[perfil core] :3100", ha="center", fontsize=8)
ax.text(66, 19.2, "[perfil metrics] :9090", ha="center", fontsize=8); ax.text(66, 7.2, "[perfil profiling] :4040", ha="center", fontsize=8)
ax.text(91.5, 13.3, "[perfil core] :3000", ha="center", fontsize=8); ax.text(36.5, 15.3, "[perfil core]", ha="center", fontsize=8)
ax.text(50, 45, "Flujo de datos (continuo) y de consulta (discontinuo)", ha="center", fontsize=11, fontweight="bold")
plt.show()
''')
    md(observe("""
    - Las flechas **continuas** son *escritura* de telemetría: la app habla **solo con el Collector**; el Collector reparte cada señal a su base de datos.
    - Las flechas **discontinuas** son *lectura*: Grafana consulta a cada base de datos. Grafana nunca recibe telemetría directamente.
    - La app no sabe qué backend hay detrás: puedes cambiar Tempo por otra cosa **tocando solo el Collector**. Ese desacoplamiento es la razón de ser de OpenTelemetry.
    """))

    md("""
    ### ¿Por qué un Collector en medio?  *(detalle en el módulo 05)*

    Enviar directo de la app al backend funciona en un tutorial, pero en producción el Collector te da: **reintentos y *buffering*** si el backend cae, **un único punto de salida** de red,
    **procesado central** (quitar datos personales, añadir etiquetas de entorno, muestrear) sin redesplegar apps, y **cambiar de backend** sin tocar el código. Es como poner un *API gateway* delante de tus servicios.

    Veamos los **servicios y versiones reales** de nuestro `docker-compose.yml` (leídos del fichero, no copiados a mano):
    """)
    code('''
import yaml
STACK_DIR = ROOT / "stack"
compose = yaml.safe_load((STACK_DIR / "docker-compose.yml").read_text())
ROLE = {"otel-collector": "recibe/transforma/reenvía OTLP", "tempo": "trazas (TraceQL)", "loki": "logs (LogQL)",
        "grafana": "dashboards y Explore", "prometheus": "métricas (PromQL)", "pyroscope": "profiling continuo"}
rows = []
for name, s in compose["services"].items():
    rows.append({"servicio": name, "rol": ROLE[name], "imagen": s["image"].replace("${", "").split(":")[0],
                 "versión por defecto": s["image"].split(":-")[1].rstrip("}"), "perfiles": ", ".join(s["profiles"]),
                 "puertos host": " ".join(p.split(":")[0] for p in s["ports"])})
pd.DataFrame(rows).set_index("servicio")
''')

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ---
    # 3 · Docker y Compose desde cero

    Si nunca has usado Docker, esta sección es todo lo que necesitas (y nada más) para el curso.

    ## 3.1 Seis palabras

    | Concepto | Qué es | Analogía Python/ML |
    |---|---|---|
    | **Imagen** | Paquete inmutable con un programa y todo lo que necesita (SO mínimo, librerías, binario) | Una *wheel* o un `conda-pack`: se descarga y no cambia |
    | **Contenedor** | Una imagen *en ejecución*: un proceso aislado con su propio sistema de ficheros y red | Una *instancia* de una clase / un proceso con su propio entorno virtual |
    | **Volumen** | Disco persistente que sobrevive al contenedor | Una carpeta de datos fuera del `venv`: borrar el entorno no borra los datos |
    | **Red** | Red virtual privada donde los contenedores se ven por **nombre de servicio** | Un `localhost` compartido con DNS: `http://loki:3100` |
    | **Puerto publicado** (`"3000:3000"`) | `puerto_host:puerto_contenedor`: abre una puerta desde tu máquina al contenedor | Un `port-forward` |
    | **Compose** | Fichero YAML que describe *varios* servicios, redes y volúmenes y los levanta juntos | `requirements.txt` + `Makefile` para infraestructura |

    ## 3.2 Una imagen que se parece a lo que ya haces

    ```text
    docker pull grafana/grafana:13.2.4      # descarga la imagen (una vez)
    docker run -p 3000:3000 grafana/grafana:13.2.4   # crea un contenedor y publica el puerto 3000
    ```
    Con Compose **no ejecutas eso a mano**: describes el estado deseado en YAML y `docker compose up` lo reconcilia.
    """)

    code('''
fig, ax = viz.canvas(12, 5.6, (0, 100), (0, 50))
viz.box(ax, 0.5, 0.5, 99, 48, "", viz.PALETTE["neutral"], fc="#00000005")
ax.text(2, 46, "TU MÁQUINA (host)", fontsize=10, fontweight="bold", color=viz.PALETTE["neutral"])
viz.box(ax, 2, 6, 13, 34, "Tu navegador\\ny tu notebook\\n\\n(localhost)", viz.PALETTE["dark"], bold=True)
viz.box(ax, 33, 2, 65, 40, "", viz.PALETTE["traces"], fc="#2a6fdb0d")
ax.text(35, 38.5, "Red virtual de Compose «agentobs_default»: los contenedores se ven por NOMBRE (tempo:3200)", fontsize=9, color=viz.PALETTE["traces"])
rows = [("otel-collector", "4317 · 4318", "(ninguno)", ":4318"), ("tempo", "3200", "tempo-data", ":3200"),
        ("loki", "3100", "loki-data", ":3100"), ("grafana", "3000", "grafana-data", ":3000")]
for i, (name, port, vol, hostport) in enumerate(rows):
    y = 30 - i * 9
    viz.box(ax, 20, y, 8, 5, f"localhost{hostport}", viz.PALETTE["dark"], fontsize=7)                      # puerto publicado en el host
    viz.arrow(ax, (15.4, y + 2.5), (19.6, y + 2.5), "", viz.PALETTE["dark"])
    c = viz.box(ax, 38, y, 25, 5, f"{name} · puerto {port}", viz.PALETTE["neutral"], fontsize=8)
    viz.arrow(ax, (28.4, y + 2.5), (37.6, y + 2.5), "publicado", viz.PALETTE["dark"], fontsize=7)
    viz.box(ax, 72, y, 22, 5, f"volumen: {vol}", viz.PALETTE["metrics"], fontsize=8)
    viz.arrow(ax, (63.4, y + 2.5), (71.6, y + 2.5), "", viz.PALETTE["metrics"], style="-")
plt.show()
''')
    md(observe("""
    - Dentro de la red de Compose el Collector habla con Tempo como `tempo:4317` (nombre del servicio), **no** `localhost`. `localhost` dentro de un contenedor es *ese mismo contenedor*.
    - Desde *tu* máquina entras por los **puertos publicados** (`localhost:3000` → Grafana).
    - Los volúmenes (naranja) guardan los datos: `docker compose down` los conserva; `docker compose down -v` los **borra**.
    """))

    md("""
    ## 3.3 Comprueba tu Docker

    Necesitas Docker Engine (Linux) o Docker Desktop (macOS/Windows) con **Compose v2** (el comando es `docker compose`, con espacio, no `docker-compose`).
    En macOS/Windows, Docker Desktop reserva su propia memoria para la máquina virtual: **Settings → Resources → Memory ≥ 4 GB** (el stack usa ≈ 1 GB).
    """)
    code('''
import shutil, subprocess

def sh(cmd: list[str], timeout: int = 20) -> str:
    """Ejecuta un comando y devuelve su salida (o un mensaje claro si falla). Nunca lanza."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (r.stdout or r.stderr).strip()
    except FileNotFoundError:
        return f"(no encuentro `{cmd[0]}` en el PATH)"
    except subprocess.TimeoutExpired:
        return "(tiempo agotado)"

HAS_DOCKER = shutil.which("docker") is not None
print("docker en PATH:", HAS_DOCKER)
if HAS_DOCKER:
    print("compose:", sh(["docker", "compose", "version"]))
    print("daemon :", sh(["docker", "version", "--format", "{{.Server.Version}}"]) or "—")
else:
    print("→ Instala Docker (https://docs.docker.com/get-docker/). Mientras tanto, el notebook sigue en modo degradado.")
''')

    md("""
    ## 3.4 Seis comandos que usarás el 95 % del tiempo

    | Comando (desde `stack/`) | Qué hace |
    |---|---|
    | `docker compose --profile core up -d` | Crea y arranca los servicios del perfil `core` **en segundo plano** (`-d`) |
    | `docker compose --profile all ps` | Lista los contenedores y su estado (`Up`, `healthy`, `Exited`…) |
    | `docker compose logs -f tempo` | Sigue los logs de un servicio (Ctrl-C para salir) |
    | `docker compose --profile all down` | Para y elimina contenedores y red (**conserva** volúmenes) |
    | `docker compose --profile all down -v` | Igual, y **borra volúmenes** (empezar de cero) |
    | `docker compose config` | Valida el YAML y muestra el fichero ya interpolado (variables, perfiles) |

    ## 3.5 Leer el `docker-compose.yml` línea a línea

    Mostramos el servicio `grafana` del fichero real, con los números de línea:
    """)
    code('''
def show(path, start, end):
    lines = pathlib.Path(path).read_text().splitlines()
    for i in range(start - 1, min(end, len(lines))):
        print(f"{i+1:>3} │ {lines[i]}")

text = (STACK_DIR / "docker-compose.yml").read_text().splitlines()
g0 = next(i for i, l in enumerate(text) if l.startswith("  grafana:")) + 1
show(STACK_DIR / "docker-compose.yml", g0, g0 + 28)
''')
    md("""
    | Línea (relativa) | Qué significa |
    |---|---|
    | `image: grafana/grafana:${GRAFANA_VERSION:-13.2.4}` | Imagen y **versión fijada** (`${VAR:-valor}` = «usa la variable de entorno o, si no existe, este valor»). Fijar versión = reproducibilidad |
    | `profiles: ["core", "all"]` | El servicio **solo** arranca si activas `--profile core` o `--profile all` |
    | `environment:` | Variables de entorno de Grafana (`GF_*`): usuario/contraseña del laboratorio, sin telemetría de uso |
    | `volumes: ./grafana/provisioning:/etc/grafana/provisioning:ro` | **Monta una carpeta tuya dentro del contenedor** (`:ro` = solo lectura): así los datasources llegan como código |
    | `volumes: grafana-data:/var/lib/grafana` | Volumen **con nombre**: la base de datos de Grafana persiste entre reinicios |
    | `ports: "3000:3000"` | Publica `host:contenedor` |
    | `depends_on:` | Orden de arranque (arranca tras `tempo` y `loki`; **no** espera a que estén *listos*) |
    | `healthcheck:` | Cómo saber si el servicio está **sano** (aquí, `curl /api/health`) |
    | `restart: unless-stopped` | Se reinicia solo si cae |

    ## 3.6 Perfiles de Compose y presupuesto de RAM

    Un **perfil** es una etiqueta que activas con `--profile`. Sirve para que cada módulo arranque *solo* lo que necesita. Medimos el consumo en reposo de cada contenedor
    (`docker stats`) en una máquina de referencia con el stack recién arrancado:
    """)
    code('''
# Medido con `docker stats --no-stream` en una máquina de referencia (stack recién arrancado, sin carga). MiB.
REF_RAM_MIB = {"otel-collector": 38, "tempo": 35, "loki": 40, "grafana": 228, "prometheus": 42, "pyroscope": 54}
REF_IMG_MB = {"otel-collector": 520, "tempo": 178, "loki": 211, "grafana": 1940, "prometheus": 381, "pyroscope": 240}
profile_of = {n: s["profiles"][0] for n, s in compose["services"].items()}
colors = {"core": viz.PALETTE["traces"], "metrics": viz.PALETTE["metrics"], "profiling": viz.PALETTE["profiles"]}

fig, ax = plt.subplots(1, 2, figsize=(12, 3.9), gridspec_kw={"width_ratios": [1.1, 1]})
names = list(REF_RAM_MIB)
ax[0].barh(names, [REF_RAM_MIB[n] for n in names], color=[colors[profile_of[n]] for n in names])
for i, n in enumerate(names):
    ax[0].text(REF_RAM_MIB[n] + 3, i, f"{REF_RAM_MIB[n]} MiB", va="center", fontsize=9)
ax[0].invert_yaxis(); ax[0].set_xlabel("RAM en reposo (MiB)"); ax[0].set_title("Consumo por servicio (color = perfil)")
combos = {"core": ["core"], "core+metrics": ["core", "metrics"], "todo": ["core", "metrics", "profiling"]}
tot = {k: sum(REF_RAM_MIB[n] for n in names if profile_of[n] in v) / 1024 for k, v in combos.items()}
LOAD_FACTOR = 3.0   # margen razonable para tráfico real (Tempo/Loki/Prometheus crecen con la carga)
x = np.arange(len(tot)); ax[1].bar(x - 0.2, list(tot.values()), 0.4, label="reposo (medido)", color=viz.PALETTE["ok"])
ax[1].bar(x + 0.2, [v * LOAD_FACTOR for v in tot.values()], 0.4, label=f"con carga (×{LOAD_FACTOR:g}, estimación)", color=viz.PALETTE["warn"])
ax[1].axhline(8, color=viz.PALETTE["error"], ls="--"); ax[1].text(0, 7.4, "8 GB libres recomendados", color=viz.PALETTE["error"], fontsize=9)
ax[1].set_xticks(x); ax[1].set_xticklabels(list(tot)); ax[1].set_ylabel("GB"); ax[1].set_ylim(0, 9); ax[1].legend(fontsize=8, loc="center right"); ax[1].set_title("Presupuesto por perfiles")
plt.tight_layout(); plt.show()
print({k: round(v, 2) for k, v in tot.items()}, "GB en reposo ·", f"imágenes ≈ {sum(REF_IMG_MB.values())/1024:.1f} GB de disco")
''')
    md(observe("""
    - **Grafana** domina el consumo (≈ 230 MiB); el Collector, Tempo y Loki son ligeros en reposo. Con el perfil `all` estamos en torno a medio gigabyte.
    - El factor de carga es una **estimación prudente** (no una medición): Tempo/Loki/Prometheus guardan datos en memoria antes de volcarlos a disco, así que crecen con el tráfico. Por eso recomendamos 8 GB libres aunque en reposo uses mucho menos.
    - Las **imágenes** ocupan ≈ 3,5 GB de disco la primera vez que haces `up` (descarga única; Grafana pesa casi 2 GB).
    """))

    md("""
    ## 3.7 Las configuraciones también son código

    El Collector se configura con un YAML de **receivers → processors → exporters** unidos por **pipelines**. Este es el de nuestro stack (lo estudiamos en profundidad en el módulo 05):
    """)
    code('''
cfg = (STACK_DIR / "otel-collector" / "config.yaml").read_text().splitlines()
start = next(i for i, l in enumerate(cfg) if l.startswith("service:"))
print("\\n".join(f"{i+1:>3} │ {l}" for i, l in enumerate(cfg) if i >= start))
''')
    md("""
    Lectura: hay **tres pipelines independientes** (`traces`, `logs`, `metrics`); cada uno recibe por OTLP, pasa por `memory_limiter` (siempre primero), `resource/lab` (añade `deployment.environment.name=lab`) y `batch`,
    y sale hacia su backend: Tempo por OTLP/gRPC, Loki por OTLP/HTTP (Loki 3 acepta OTLP de forma nativa) y Prometheus por un endpoint que *él* raspa (`:8889`).

    > 💡 **Aprovisionamiento como código.** Los *datasources* de Grafana (`stack/grafana/provisioning/datasources/datasources.yaml`) también son un fichero versionado: al arrancar, Grafana ya conoce Tempo, Loki y Prometheus,
    > con las **correlaciones** configuradas (de una traza a sus logs, de un log a su traza). Nadie hace clic en la UI para configurar nada: es reproducible.
    """)

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ---
    # 4 · Levantar el stack y verificar su salud

    ## 4.1 Arranque

    Desde una terminal, en la carpeta `agent-observability-course/stack/`:

    ```bash
    docker compose --profile core --profile metrics up -d
    ```

    La primera vez descarga ≈ 3,5 GB de imágenes (varios minutos). También puedes hacerlo desde el notebook cambiando `START_STACK = True` en la celda siguiente
    (usa `docker compose up -d`, y mide cuánto tarda cada servicio en estar **listo**).
    """)
    code('''
START_STACK = False   # True: este notebook ejecuta `docker compose up -d` por ti (necesita Docker y red para descargar imágenes)
COMPOSE = ["docker", "compose", "-f", str(STACK_DIR / "docker-compose.yml")]
READY_S = None        # se rellena si medimos un arranque real

if START_STACK and HAS_DOCKER:
    import time
    t0 = time.time()
    print(sh(COMPOSE + ["--profile", "core", "--profile", "metrics", "up", "-d"], timeout=900))
    READY_S, pending = {}, {"collector", "tempo", "loki", "grafana", "prometheus"}
    while pending and time.time() - t0 < 150:
        st = check_stack(["core", "metrics"], verbose=False)
        for s in list(pending):
            if st.up.get(s):
                READY_S[s] = round(time.time() - t0, 1); pending.discard(s)
        time.sleep(1)
    print("tiempo hasta READY (s):", READY_S)
else:
    print("No arrancamos nada desde aquí (START_STACK=False). Usa la terminal o cambia la bandera.")
STACK = check_stack(["core", "metrics"])
''')

    code('''
# Tiempo hasta READY (s). Si arrancaste el stack desde el notebook usamos tu medición; si no, una medición de referencia.
REF_READY_S = {"collector": 2.1, "tempo": 2.1, "prometheus": 2.1, "grafana": 6.7, "loki": 17.3, "pyroscope": 63.2}
ready = READY_S or REF_READY_S
src = "tu máquina (medido arriba)" if READY_S else "máquina de referencia (medición previa)"
order = sorted(ready, key=ready.get)
fig, ax = plt.subplots(figsize=(8.5, 3.6))
prof_of_ready = lambda s: profile_of["otel-collector" if s == "collector" else s]
ax.barh(order, [ready[s] for s in order], color=[colors[prof_of_ready(s)] for s in order])
for i, s in enumerate(order):
    ax.text(ready[s] + 0.8, i, f"{ready[s]:.0f} s", va="center")
ax.invert_yaxis(); ax.set_xlabel("segundos desde `docker compose up -d` hasta responder «listo»"); ax.set_title(f"Arrancado ≠ listo · {src}")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Docker devuelve el control en ≈ 2 s, pero **Loki tarda ≈ 17 s y Pyroscope ≈ 1 minuto** en estar listos (anillos internos, replay del WAL, esperas deliberadas antes de aceptar escrituras).
    - Por eso un mismo `docker compose ps` que dice «Up» *no* garantiza que puedas escribir. En producción la señal buena es el **readiness** (`/ready`), no el estado del contenedor.
    - `check_stack()` distingue tres estados: `OK` (listo), `....` (responde pero aún arrancando) y `----` (no responde).
    """))

    md("""
    ## 4.2 Un recorrido por Grafana

    Abre <http://localhost:3000> → usuario `admin`, contraseña `admin` (solo laboratorio; el acceso anónimo está desactivado en `docker-compose.yml`, por eso usamos login).

    1. **Connections → Data sources**: deben aparecer **Tempo, Loki, Prometheus y Pyroscope** (provisionados; Pyroscope saldrá en rojo si no arrancaste el perfil `profiling`).
    2. **Dashboards → «Curso observabilidad de agentes» → «00 · Stack overview»**: vacío hasta que llegue telemetría.
    3. **Explore**: elige un datasource y lanza consultas ad hoc (en los módulos 07-09 aprenderás TraceQL, LogQL y PromQL).

    Lo mismo, por API (así podemos comprobarlo desde Python):
    """)
    code('''
def datasource_health() -> pd.DataFrame:
    """Salud de cada datasource provisionado, consultando la API de Grafana."""
    rows = []
    for uid in ["tempo", "loki", "prometheus", "pyroscope"]:
        try:
            h = backends.grafana_api(f"/api/datasources/uid/{uid}/health")
            rows.append({"uid": uid, "estado": h.get("status"), "mensaje": h.get("message", "")[:70]})
        except backends.BackendError as e:
            rows.append({"uid": uid, "estado": "SIN CONEXIÓN", "mensaje": str(e)[:70]})
    return pd.DataFrame(rows).set_index("uid")

if STACK.up.get("grafana"):
    display(datasource_health())
else:
    print("Grafana no está arriba (modo degradado). Resultado típico con core+metrics (Pyroscope parado):")
    display(pd.DataFrame({"estado": ["OK", "OK", "OK", "ERROR"], "mensaje": ["Data source is working. Streaming test succeeded.", "Data source successfully connected.", "Successfully queried the Prometheus API.", "received error from client ... no such host"]},
                         index=pd.Index(["tempo", "loki", "prometheus", "pyroscope"], name="uid")))
''')

    md("""
    ## 4.3 «Hola mundo» a nivel de cable: tu primera traza, log y métrica

    En el módulo 03 usarás el SDK de OpenTelemetry. Antes, para **ver qué viaja realmente**, enviaremos telemetría *a mano* como JSON por HTTP al Collector (`POST :4318/v1/traces|logs|metrics`).
    Reglas de OTLP/JSON que conviene saber:

    - Los **identificadores** `traceId` (16 bytes) y `spanId` (8 bytes) se escriben en **hexadecimal** (32 y 16 caracteres).
    - Los **tiempos** son nanosegundos desde la época Unix, como **cadenas** (`"1792041396307640080"`), porque no caben en un número JSON seguro.
    - Los atributos son listas de `{"key": ..., "value": {"stringValue" | "intValue" | "boolValue"...: ...}}`.
    - La jerarquía es `resource → scope → (spans | logRecords | metrics)`. El **resource** dice *quién* emite (`service.name`); el **scope** dice *qué librería* lo instrumentó.
    """)
    code('''
import json, secrets, time, urllib.request

OTLP = "http://localhost:4318"

def attrs(**kv):
    """{'a': 1, 'b': 'x'} -> formato de atributos OTLP/JSON."""
    def val(v):
        return {"intValue": str(v)} if isinstance(v, int) and not isinstance(v, bool) else {"boolValue": v} if isinstance(v, bool) else {"stringValue": str(v)}
    return [{"key": k, "value": val(v)} for k, v in kv.items()]

def hello_payloads(service="hola-mundo"):
    now = time.time_ns()
    trace_id, root, child = secrets.token_hex(16), secrets.token_hex(8), secrets.token_hex(8)
    resource, scope = {"attributes": attrs(**{"service.name": service})}, {"name": "curso.manual", "version": "0"}
    traces = {"resourceSpans": [{"resource": resource, "scopeSpans": [{"scope": scope, "spans": [
        {"traceId": trace_id, "spanId": root, "name": "invoke_agent hola", "kind": 1, "startTimeUnixNano": str(now - 300_000_000),
         "endTimeUnixNano": str(now), "attributes": attrs(**{"gen_ai.operation.name": "invoke_agent"}), "status": {"code": 1}},
        {"traceId": trace_id, "spanId": child, "parentSpanId": root, "name": "chat mock-small", "kind": 3, "startTimeUnixNano": str(now - 250_000_000),
         "endTimeUnixNano": str(now - 50_000_000), "attributes": attrs(**{"gen_ai.usage.input_tokens": 120}), "status": {"code": 0}}]}]}]}
    logs = {"resourceLogs": [{"resource": resource, "scopeLogs": [{"scope": scope, "logRecords": [
        {"timeUnixNano": str(now), "severityNumber": 9, "severityText": "INFO", "body": {"stringValue": "hola mundo"},
         "traceId": trace_id, "spanId": root, "attributes": attrs(**{"ticket.id": "T-1"})}]}]}]}
    metrics = {"resourceMetrics": [{"resource": resource, "scopeMetrics": [{"scope": scope, "metrics": [
        {"name": "hello_requests", "unit": "{request}", "sum": {"aggregationTemporality": 2, "isMonotonic": True,
         "dataPoints": [{"startTimeUnixNano": str(now - 60_000_000_000), "timeUnixNano": str(now), "asInt": "5"}]}}]}]}]}
    return trace_id, {"/v1/traces": traces, "/v1/logs": logs, "/v1/metrics": metrics}

def post(path, payload):
    req = urllib.request.Request(OTLP + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.read().decode()

HELLO_TRACE_ID, payloads = hello_payloads()
print("trace_id:", HELLO_TRACE_ID, "(32 hex)")
print(json.dumps(payloads["/v1/traces"]["resourceSpans"][0]["scopeSpans"][0]["spans"][1], indent=1)[:600], "...")
''')
    code('''
SENT = False
if STACK.up.get("collector"):
    for path, payload in payloads.items():
        print(path, "→", post(path, payload))          # el Collector responde 200 {"partialSuccess":{}} si aceptó los datos
    SENT = True
else:
    print("Collector no disponible: modo degradado. Se habrían enviado los 3 payloads de arriba.")
''')
    md("""
    **200 no significa «ya puedes verlo»**: el Collector confirma que *aceptó* el dato; luego lo agrupa (`batch`, 1 s), lo reenvía y el backend lo indexa. Tempo tarda de unos segundos a ≈ 30 s en volverlo buscable
    (el *live-store* espera `max_trace_idle: 10s` antes de dar una traza por completa). Hacemos un *polling* con límite de tiempo, como harías en una prueba de humo en CI:
    """)
    code('''
def wait_for(fn, timeout=90, every=2.0):
    """Reintenta fn() hasta que devuelva algo «truthy» o venza el plazo. Devuelve (resultado, segundos)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = fn()
            if r:
                return r, time.time() - t0
        except backends.BackendError:
            pass
        time.sleep(every)
    return None, time.time() - t0

found = {}
if SENT:
    found["traza"] = wait_for(lambda: backends.tempo_trace(HELLO_TRACE_ID))
    found["log"] = wait_for(lambda: backends.loki_query(f'{{service_name="hola-mundo"}} | trace_id="{HELLO_TRACE_ID}"', minutes=15))
    if STACK.up.get("prometheus"):
        found["métrica"] = wait_for(lambda: backends.prom_query("hello_requests_total"))
    for k, (v, t) in found.items():
        print(f"{k:8s}: {'ENCONTRADO' if v else 'no encontrado'} tras {t:.0f} s")
else:
    print("(sin stack: nada que buscar)")
''')

    code('''
def otlp_to_spans(doc: dict) -> list[dict]:
    """Aplana un documento OTLP/JSON (el de Tempo usa 'batches', el que enviamos usa 'resourceSpans') al formato SPAN_SCHEMA del curso."""
    out = []
    for rs in doc.get("batches") or doc.get("resourceSpans") or []:
        for ss in rs.get("scopeSpans") or rs.get("instrumentationLibrarySpans") or []:
            for s in ss["spans"]:
                code_ = (s.get("status") or {}).get("code", 0)
                out.append({"trace_id": s["traceId"], "span_id": s["spanId"], "parent_span_id": s.get("parentSpanId") or None,
                            "name": s["name"], "start_unix_nano": int(s["startTimeUnixNano"]), "end_unix_nano": int(s["endTimeUnixNano"]),
                            "status": "ERROR" if code_ in (2, "STATUS_CODE_ERROR") else "OK"})
    return out

doc = found["traza"][0] if found.get("traza") and found["traza"][0] else payloads["/v1/traces"]
origin = "leída de Tempo" if found.get("traza") and found["traza"][0] else "el payload que habríamos enviado (modo degradado)"
viz.waterfall(otlp_to_spans(doc), title=f"Tu primera traza ({origin})")
plt.show()
''')
    md(observe("""
    - La barra larga es el span **raíz** (`invoke_agent hola`, 300 ms); el span hijo (`chat mock-small`, 200 ms) está **anidado** dentro: empieza después y termina antes. La relación padre→hijo viaja en `parentSpanId`.
    - Esta cascada (*waterfall*) es la vista principal de Tempo/Grafana: de un vistazo ves *dónde se fue el tiempo*.
    - El mismo `trace_id` está también en el **log**; la métrica no lo lleva (un contador agrega muchas peticiones; luego veremos *exemplars*, módulo 09). Ese identificador común es el hilo que une las señales: sin él, tres sistemas separados no se pueden cruzar.
    """))

    code('''
def collector_counters() -> dict[str, float]:
    """Lee los contadores internos del Collector (endpoint :8888/metrics, formato texto de Prometheus). No necesita Prometheus."""
    import re
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))      # localhost: sin proxy
    with opener.open("http://localhost:8888/metrics", timeout=3) as r:
        txt = r.read().decode()
    out = {}
    for line in txt.splitlines():
        m = re.match(r"otelcol_(receiver_accepted|exporter_sent)_(spans|log_records|metric_points)(?:_total)?\\{([^}]*)\\} (\\S+)", line)
        if m:
            kind, sig, labels, val = m.groups()
            who = re.search(r'(?:receiver|exporter)="([^"]+)"', labels).group(1)
            key = f"{kind.split('_')[0]}:{who}:{sig}"
            out[key] = out.get(key, 0) + float(val)
    return out

REF_COUNTERS = {"receiver:otlp:spans": 34, "exporter:otlp_grpc/tempo:spans": 34, "receiver:otlp:log_records": 2, "exporter:otlp_http/loki:log_records": 2,
                "receiver:otlp:metric_points": 3, "exporter:prometheus:metric_points": 3}
try:
    counters = collector_counters(); src = "contadores reales de tu Collector (:8888)"
    if not counters: raise RuntimeError
except Exception:
    counters, src = REF_COUNTERS, "valores de referencia (modo degradado)"
sig_names = {"spans": "trazas (spans)", "log_records": "logs", "metric_points": "métricas (puntos)"}
rec = {s: sum(v for k, v in counters.items() if k.startswith("receiver") and k.endswith(s)) for s in sig_names}
sent = {s: sum(v for k, v in counters.items() if k.startswith("exporter") and k.endswith(s)) for s in sig_names}
fig, ax = plt.subplots(figsize=(8, 3.6)); x = np.arange(3)
ax.bar(x - 0.2, [rec[s] for s in sig_names], 0.4, label="aceptado por el receiver OTLP", color=viz.PALETTE["neutral"])
ax.bar(x + 0.2, [sent[s] for s in sig_names], 0.4, label="enviado por el exporter al backend", color=viz.PALETTE["ok"])
ax.set_xticks(x); ax.set_xticklabels(list(sig_names.values())); ax.legend(); ax.set_title(f"Lo que ha pasado por el Collector · {src}")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Si **aceptado ≈ enviado** para cada señal, el Collector no está perdiendo datos. Si el naranja/verde de «enviado» queda por debajo (o aparece `otelcol_exporter_send_failed_*` en `:8888/metrics`), el problema está *entre el Collector y el backend*.
    - Es el primer ejemplo de **observar la propia observabilidad**: tu pipeline de telemetría también falla, y hay que medirlo.
    - Si ves los valores de referencia, no tenías el stack arriba: no pasa nada, el resto del módulo funciona igual.
    """))

    # ------------------------------------------------------------------------------------------------ prod / elite
    md("""
    ---
    # 5 · 🏭 En producción

    - **Grafana Labs** empaqueta exactamente esta combinación (OpenTelemetry Collector + Prometheus + Tempo + Loki + Pyroscope + Grafana) en una imagen *todo en uno para desarrollo*,
      [`grafana/docker-otel-lgtm`](https://github.com/grafana/docker-otel-lgtm). En este curso los servicios están **separados** a propósito: así ves cada pieza, sus puertos y sus configuraciones, que es lo que operarás en producción.
    - **Honeycomb** publicó cómo construyó una función con LLM (*Query Assistant*) y cómo midió si funcionaba: [«All the Hard Stuff Nobody Talks About when Building Products with LLMs»](https://www.honeycomb.io/blog/hard-stuff-nobody-talks-about-llm) (2023)
      y [«So We Shipped an AI Product. Did it Work?»](https://www.honeycomb.io/blog/we-shipped-ai-product) (2023). La lección común: con LLMs el éxito se mide con **datos de producción**, no con pruebas unitarias.
    - **OpenTelemetry** documenta el estado de la observabilidad de agentes y la necesidad de convenciones comunes: [«AI Agent Observability — Evolving Standards and Best Practices»](https://opentelemetry.io/blog/2025/ai-agent-observability/) (6 de marzo de 2025; es un post de blog que se queda viejo: contrasta siempre con la spec vigente de `semantic-conventions-genai`).
    - **Límite explícito del "todo en uno":** el propio README de `grafana/docker-otel-lgtm` avisa de que la imagen es para entornos de *desarrollo, demo y pruebas* y remite a Grafana Cloud para producción: sin réplicas, sin HA, sin retención dimensionada. Lo que aquí aprendes (configs, puertos, señales) se traslada; la topología no.
    - **Trade-off real:** el stack de observabilidad es *otra carga de producción* (CPU, RAM, disco, coste). Lo medimos aquí en miniatura; en el módulo 18 lo dimensionas con presupuesto.
    """)

    md(box("elite", "Entorno y arranque", """
    1. **«Listo» ≠ «arrancado».** Un contenedor `Up` no acepta escrituras hasta que su *readiness* pasa (Loki ≈ 17 s, Pyroscope ≈ 1 min aquí). Las pruebas de humo deben esperar a `/ready` con *timeout* explícito, no a `sleep 30`.
    2. **Un `200` del Collector solo prueba que *aceptó* el dato.** La verificación de verdad es **de extremo a extremo**: una traza *canario* que viaja app → Collector → Tempo y se busca por su `trace_id`. Es lo que hacen los equipos para detectar «pérdida silenciosa de telemetría».
    3. **Fija versiones y lee las notas de versión.** Este stack usa Tempo 3.x, que **eliminó** `ingester` y `compactor` de la configuración (ahora `live_store` y `backend_scheduler`); un `tempo.yaml` copiado de un tutorial de 2024 no arranca. En el Collector contrib 0.162 los exporters se llaman `otlp_grpc`/`otlp_http`. «Latest» en producción es una bomba de relojería.
    4. **`memory_limiter` va primero** en cada pipeline: si el Collector se queda sin memoria pierde *todo*; con el limitador, rechaza con elegancia y te avisa por métrica. Dos matices que su README documenta: (a) «rechazar» devuelve un error *no permanente* al emisor, que **debe reintentar**; si el componente anterior no reintenta, el dato se pierde para siempre (por eso los SDK de OTel reintentan OTLP); (b) los datos entrantes consumen memoria *antes* de que el limitador pueda rechazarlos, así que `limit_mib` debe dejar margen (`spike_limit_mib`) sobre el límite del contenedor. Fuente: README del `memorylimiterprocessor` y orden recomendado en `processor/README.md` (ver Referencias).
    5. **La app solo debe conocer al Collector.** Cualquier decisión de enrutado, redacción de datos o muestreo que puedas hacer allí es una decisión que no requiere redesplegar la aplicación.
    6. **Aprovisiona como código desde el día 1** (datasources y dashboards en ficheros). Un Grafana configurado a clics es irreproducible y se pierde al recrear el contenedor.
    7. **Observa tu pipeline**: las métricas internas del Collector (`:8888`) y de Tempo/Loki son lo primero que miras cuando «faltan trazas».
    """))

    md(box("warn", "Errores comunes (pitfalls)", """
    | Síntoma | Causa habitual | Cómo comprobarlo / arreglarlo |
    |---|---|---|
    | `port is already allocated` | Otro proceso usa 3000/3100/3200/4317/4318/9090 | `ss -ltnp \\| grep 3000` (Linux/macOS: `lsof -i :3000`); para el otro proceso o cambia el puerto de **host** (`"3001:3000"`) |
    | `docker compose` no arranca nada | Olvidaste `--profile` (sin perfil no hay servicios, a propósito) | `docker compose --profile core up -d` |
    | Datasource Loki/Tempo en rojo «connection refused» | Aún arrancando, o la URL usa `localhost` **dentro** de la red | Espera a `/ready`; en datasources usa el nombre del servicio (`http://loki:3100`) |
    | Grafana dice «dashboard … already in use» tras cambiar un `uid` | Volumen `grafana-data` antiguo con el dashboard anterior | `docker compose down -v` y vuelve a levantar |
    | `Killed` / contenedores que se reinician | Docker Desktop sin memoria suficiente | Aumenta la RAM de Docker Desktop (≥ 4 GB) |
    | El Collector devuelve 200 pero no aparece nada | Timestamps antiguos, exporter mal configurado o backend caído | `docker compose logs otel-collector`, y `otelcol_exporter_send_failed_*` en `:8888/metrics` |
    | `docker-compose: command not found` | Usas el binario v1 antiguo | Instala el plugin Compose v2: `docker compose` (con espacio) |
    | Ruido `no jobs found` en los logs de Tempo | Es el *backend worker* sondeando sin trabajo | Benigno en el laboratorio |
    | Datos «de 2026-09-01» que no aparecen en Tempo/Loki | Se envió tiempo **simulado** del pasado: los backends descartan o rechazan datos muy antiguos | Usa `generate_tickets(..., start_s="live")` para tráfico en vivo |
    """))

    # ------------------------------------------------------------------------------------------------ autoevaluación
    md("""
    ---
    # 6 · Autoevaluación

    Intenta responder **antes** de abrir cada respuesta. Hay preguntas de cálculo, diagnóstico y transferencia.
    """)
    qs = [
        ("1 · (Cálculo) Presupuesto de RAM",
         """Tu portátil tiene 16 GB, de los cuales el sistema y el navegador usan ≈ 7 GB. Con el factor de carga ×3 del gráfico 3.6, ¿cabe el perfil `all`? ¿Y con ×10?""",
         """El perfil `all` ocupa ≈ 0,43 GB en reposo (38+35+40+228+42+54 = 437 MiB). Con ×3 ≈ 1,3 GB → cabe de sobra en los 9 GB libres. Con ×10 ≈ 4,3 GB → **todavía cabe**, pero ya compites con el notebook y los modelos locales.
        Lo importante: el factor ×10 *no es una medición*; en carga real se mide con `docker stats` y se pone `mem_limit` por servicio para que uno no se coma al resto."""),
        ("2 · (Cálculo) Puertos",
         """Un compañero ya usa el puerto 3000. Cambias en Compose `"3000:3000"` por `"8080:3000"`. ¿En qué URL abres Grafana desde tu navegador? ¿Y con qué URL lo ve Tempo dentro de la red de Compose?""",
         """Navegador: `http://localhost:8080`. Dentro de la red de Compose los contenedores **siguen usando el puerto del contenedor**: `http://grafana:3000`. El mapeo `host:contenedor` solo afecta a la puerta que abres hacia fuera."""),
        ("3 · (Diagnóstico) Datasource en rojo",
         """Acabas de ejecutar `docker compose --profile core up -d`; `docker compose ps` muestra Loki `Up`, pero en Grafana el datasource Loki da «connection refused». Da dos hipótesis ordenadas y cómo descartarlas.""",
         """(1) **Aún no está listo** (≈ 17 s): `curl localhost:3100/ready` devolverá 503 con «Ingester not ready…» → espera y reintenta. (2) **URL equivocada** en el datasource (`http://localhost:3100` en vez de `http://loki:3100`): `curl` desde dentro de Grafana (`docker compose exec grafana curl -s http://loki:3100/ready`) distingue si es de red o de configuración."""),
        ("4 · (Diagnóstico) Se envió la traza pero no aparece",
         """El Collector devolvió 200 al `POST /v1/traces`, y 5 minutos después Tempo no la encuentra. Enumera tres comprobaciones, de la más barata a la más cara.""",
         """(1) Métricas internas del Collector: ¿`otelcol_receiver_accepted_spans` sube y `otelcol_exporter_sent_spans` también? Si el segundo no sube o `send_failed` sí → problema Collector→Tempo. (2) `docker compose logs otel-collector tempo`: errores de conexión o de rechazo (p. ej. *timestamps* demasiado antiguos). (3) Probar el camino corto: `GET :3200/api/traces/<id>` y una búsqueda TraceQL por `resource.service.name`; si el `traceId` no tiene 32 hex o es todo ceros, el dato se descarta."""),
        ("5 · (Cálculo) SLI clásico vs SLI de calidad",
         """En una ventana hay 800 peticiones: 19 terminan en error visible y 59 devuelven respuestas inventadas o con PII (de ellas 1 ya estaba entre los errores). ¿Qué disponibilidad «sin errores» y qué SLI de «correcto y seguro» calculas?""",
         """Sin errores: 1 − 19/800 = **97,6 %**. Correcto y seguro: peticiones malas = 19 (error) + 59 (calidad) − 1 (solape) = 77 → 1 − 77/800 = **90,4 %**. La diferencia de ≈ 7 puntos es la que no ve ningún dashboard de HTTP."""),
        ("6 · (Transferencia) Del ML al agente",
         """En un modelo de clasificación vigilas *drift* de datos y la accuracy contra etiquetas que llegan días después. ¿Qué equivalente tienes en un agente de soporte y qué se complica?""",
         """Equivalente: *drift* del comportamiento (cambia la mezcla de intenciones, el prompt o el modelo) y calidad **online** estimada con evaluadores, feedback del usuario o reglas. Se complica porque la «predicción» es una **cadena** de pasos con herramientas y coste, no una etiqueta; hay que atribuir el fallo al paso concreto (traza)."""),
        ("7 · (Transferencia) Un pipeline batch",
         """Tienes un pipeline nocturno de embeddings + RAG (sin interacción de usuario). ¿Cuáles de las cinco grietas siguen aplicando? ¿Qué cambia en cómo lo monitorizas?""",
         """Siguen: coste variable (tokens), calidad (documentos recuperados irrelevantes) y fallos parciales (un lote de documentos falla en silencio). Cambia que no hay latencia interactiva: priorizas **throughput, duración total, tasa de reintentos y coste por lote**, y alertas de «no ha terminado a la hora esperada» (*dead man's switch*)."""),
        ("8 · (Diagnóstico) Si Grafana se cae…",
         """Grafana se cae durante una hora (el contenedor está parado) pero la app y el resto del stack siguen. Mirando el diagrama del stack: ¿se pierden trazas, logs o métricas de esa hora? ¿Qué dejas de poder hacer? ¿Y si lo que se cae es el Collector?""",
         """Con Grafana caído **no se pierde telemetría**: las flechas de escritura van app → Collector → Tempo/Loki/Prometheus, y Grafana solo *lee* (flechas discontinuas). Pierdes la vista (dashboards, Explore, alertas de Grafana), no los datos; al volver verás la hora completa. Si cae el **Collector**, la app pierde su único punto de salida: los datos se acumulan en el buffer del SDK (módulo 03) hasta agotarlo y luego se descartan; por eso se vigila el Collector y se despliega con réplicas (módulo 05/19)."""),
        ("9 · (Recuerdo) ¿Por qué un Collector?",
         """Cita tres beneficios de enviar la telemetría al Collector en lugar de directamente al backend.""",
         """Reintentos y *buffering* si el backend cae; punto único de salida y de procesado (redacción de PII, etiquetas, muestreo) sin tocar aplicaciones; independencia del backend (cambiar Tempo/Loki/Prometheus por otro sin redesplegar)."""),
    ]
    for title, q, a in qs:
        md(f"**Pregunta {title}**\n\n{q}\n\n" + details("Ver respuesta", a))

    md("""
    ---
    # 7 · Referencias

    **Fuentes verificadas** (consultadas al construir el módulo; las de Honeycomb y OpenTelemetry confirmadas mediante búsqueda web, el resto en el repositorio oficial):

    - Docker Docs, *Using profiles with Compose* — <https://docs.docker.com/compose/how-tos/profiles/> y referencia del fichero Compose — <https://docs.docker.com/reference/compose-file/profiles/>.
    - OpenTelemetry, *Observability primer* — <https://opentelemetry.io/docs/concepts/observability-primer/>; *OTLP specification* — <https://opentelemetry.io/docs/specs/otlp/> (codificación JSON de ids hex y tiempos en nanosegundos).
    - OpenTelemetry, *Overview* de la especificación — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/overview.md>.
    - Grafana Labs, `grafana/docker-otel-lgtm` — <https://github.com/grafana/docker-otel-lgtm> (backend OpenTelemetry todo en uno: Collector, Prometheus, Tempo, Loki, Pyroscope, Grafana).
    - Grafana Tempo, *Release notes v3.0* (arquitectura sin ingester/compactor) — <https://grafana.com/docs/tempo/latest/release-notes/v3-0/>.
    - OpenTelemetry Collector, `memorylimiterprocessor` y «Recommended Processors» — <https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/memorylimiterprocessor/README.md> y <https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/README.md>.
    - Phillip Carter (Honeycomb), *All the Hard Stuff Nobody Talks About when Building Products with LLMs* (2023) — <https://www.honeycomb.io/blog/hard-stuff-nobody-talks-about-llm>.
    - Honeycomb, *So We Shipped an AI Product. Did it Work?* (2023) — <https://www.honeycomb.io/blog/we-shipped-ai-product>.
    - Guangya Liu (IBM) y Sujay Solomon (Google), *AI Agent Observability — Evolving Standards and Best Practices*, blog de OpenTelemetry (SIG GenAI Observability), 6-mar-2025 (autoría y fecha verificadas en el código fuente del sitio, `open-telemetry/opentelemetry.io`) — <https://opentelemetry.io/blog/2025/ai-agent-observability/>.
    - Beyer, Jones, Petoff, Murphy (eds.), *Site Reliability Engineering*, O'Reilly 2016, cap. 6 «Monitoring Distributed Systems» — <https://sre.google/sre-book/monitoring-distributed-systems/>.
    - Sculley et al., *Hidden Technical Debt in Machine Learning Systems*, NeurIPS 2015 — <https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html> (la analogía de «el modelo es una pequeña parte del sistema»).

    **Siguiente:** `01_agente_base` — abrimos SupportOps por dentro: bucle LLM + herramientas, proveedor agnóstico, tráfico y fallos inyectados.
    """)

    nb.save(out)


# =====================================================================================================================
# PROYECTO
# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "00_proyecto_entorno.ipynb", "Proyecto 00 · Levantar el stack y tu primer dashboard «hola mundo»")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 00 · Levanta el stack, verifica su salud y crea tu primer dashboard

    | | |
    |---|---|
    | **Nivel** | 🟢 Básico |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | `core` + `metrics` (≈ 0,5 GB de RAM). Sin ellos, el proyecto se evalúa en **modo degradado** (solo las comprobaciones sin red) |
    | **Prerrequisitos** | Lección `00_entorno` |
    | **Conexión** | Es la base de **SupportOps**: todos los proyectos posteriores reutilizan `check_stack()`, `backends` y el dashboard que crees aquí |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**, una tienda online de hardware que está a punto de poner un agente de soporte en producción.
    Antes de instrumentar nada, tu jefa de plataforma te pide un **entorno de observabilidad reproducible** para el equipo: que cualquiera pueda levantarlo con un comando,
    que un *script de verificación* confirme que de verdad funciona de extremo a extremo (no solo que los contenedores estén «Up») y que exista un **primer dashboard como código**.

    ## Datos

    No hay dataset: la telemetría de prueba la generas tú (una traza, un log y una métrica «hola mundo»). Cadena de resiliencia: **stack local → modo degradado** (las funciones puras
    se comprueban sin red con el *validador offline* incluido; las comprobaciones online se omiten y se marcan «no evaluable»).

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido por la solución de referencia | Umbral | Modo |
    |---|---|---|---|---|
    | R1 | Los 4 servicios `core` listos + Prometheus | `check_stack(["core","metrics"])` sin servicios requeridos faltantes | 5/5 | online |
    | R2 | Salud de datasources | `service_health_report()` devuelve OK para `tempo`, `loki`, `prometheus` | 3/3 (Pyroscope puede fallar) | online |
    | R3 | Payload de traza válido | El validador offline acepta tu traza: 3 spans, jerarquía raíz→hijos, ids hex correctos | 0 errores del validador | **offline** |
    | R4 | Telemetría de extremo a extremo | Tu `trace_id` se encuentra en Tempo (3 spans) y en Loki (1 log con `trace_id` como metadato) | 100 % de las 3 señales encontradas en ≤ 90 s | online |
    | R5 | Dashboard como código | JSON con ≥ 3 paneles de ≥ 2 tipos distintos y datasources `prometheus`+`loki` referenciados por uid | 0 errores del validador | **offline** |
    | R6 | Dashboard publicado | `GET /api/dashboards/uid/<tu uid>` existe y tiene los mismos paneles | igual nº de paneles | online |

    > 📏 **Calibración:** estos umbrales salen de lo que mide la solución de referencia (al final) en el stack real: 5/5 servicios, 3/3 datasources, traza de 3 spans visible en ≈ 15-30 s, log con `trace_id`, dashboard con 3 paneles.
    > No dependen de la velocidad de tu máquina (solo del plazo de 90 s).
    """)

    code(boot("viz"))
    code(IMPORTS + '''
import json, secrets, time, urllib.request, shutil, subprocess
STACK = check_stack(["core", "metrics"])
''')

    md("""
    ## Paso 0 · (fuera del notebook) Levanta el stack

    En una terminal, desde `agent-observability-course/stack/`:

    ```bash
    docker compose --profile core --profile metrics up -d
    ```

    Espera ≈ 20 s y vuelve a ejecutar la celda anterior hasta que `check_stack` diga *modo completo*. (Si no puedes usar Docker, sigue: los pasos 2, 4 y 6 se evalúan offline.)

    ## Paso 1 · Informe de salud de servicios

    **TODO 1.** Implementa `service_health_report()` que devuelva un `DataFrame` con una fila por servicio (`collector, tempo, loki, grafana, prometheus`), con columnas `servicio`, `estado` (`up`, `starting`, `down`) y `url`.
    Reutiliza lo que ya sabes: `supportops.stack.services()` te da las URLs de salud, y `check_stack(...).up` te dice cuáles responden.
    """)
    md(hint(1, "Cada servicio tiene una URL de salud en `supportops.stack.services()[nombre][\"url\"]`. `check_stack(require, verbose=False)` devuelve un objeto con `.up` (dict `nombre → bool`) y `.starting` (lista de nombres que responden pero aún arrancan)."))
    md(hint(2, "Construye una lista de diccionarios `{\"servicio\": n, \"estado\": ..., \"url\": ...}` iterando sobre `[\"collector\",\"tempo\",\"loki\",\"grafana\",\"prometheus\"]` y pásala a `pd.DataFrame`. Estado: `\"up\"` si `st.up[n]`, `\"starting\"` si `n in st.starting`, si no `\"down\"`."))
    code('''
from supportops.stack import services

def service_health_report() -> pd.DataFrame:
    # TODO 1: devuelve un DataFrame con columnas servicio, estado, url (una fila por servicio de core + prometheus)
    raise NotImplementedError("TODO 1")

try:
    display(service_health_report())
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 2 · Construye los payloads OTLP/JSON

    **TODO 2.** Completa `build_hello(service, n_requests)` para que devuelva `(trace_id, {"/v1/traces": ..., "/v1/logs": ..., "/v1/metrics": ...})` con:

    - **Traza** de **3 spans**: raíz `invoke_agent hola` (kind 1 = INTERNAL), hijo `chat mock-small` (kind 3 = CLIENT) y hermano `execute_tool get_order` (kind 1) — ambos hijos de la raíz, sin solaparse, dentro de la raíz.
    - **Log** `INFO` con cuerpo `"hola mundo"`, con el `traceId` y el `spanId` de la raíz y el atributo `ticket.id`.
    - **Métrica** *counter* acumulado (`sum`, `aggregationTemporality` 2, `isMonotonic` true) llamada `hello_requests` con valor `n_requests`.

    Reglas OTLP/JSON recordadas: ids en **hex** (32/16), tiempos en nanosegundos como **string**, atributos como `{"key","value":{"stringValue":...}}`.
    """)
    md(hint(1, "Parte de la función `hello_payloads()` de la lección: tenías 2 spans; añade un tercero con otro `spanId`, mismo `parentSpanId` (el de la raíz) y tiempos que no se solapen con el primer hijo, p. ej. `now-150ms → now-20ms`."))
    md(hint(2, "El `traceId` es **el mismo** en los 3 spans y en el log (`secrets.token_hex(16)`); cada `spanId` es distinto (`secrets.token_hex(8)`). El log usa `traceId` y `spanId` de la raíz. La métrica no lleva ids."))
    code('''
def attrs(**kv):
    def val(v):
        return {"intValue": str(v)} if isinstance(v, int) and not isinstance(v, bool) else {"boolValue": v} if isinstance(v, bool) else {"stringValue": str(v)}
    return [{"key": k, "value": val(v)} for k, v in kv.items()]

def build_hello(service: str = "proyecto-00", n_requests: int = 5):
    # TODO 2: construye trace_id y los 3 payloads (traza de 3 spans, log correlacionado, métrica counter)
    raise NotImplementedError("TODO 2")

try:
    TRACE_ID, PAYLOADS = build_hello()
    print("trace_id:", TRACE_ID)
except NotImplementedError as e:
    TRACE_ID, PAYLOADS = None, None
    print("Pendiente:", e)
''')

    md("""
    ## Paso 3 · Validador offline (te lo damos hecho)

    Para comprobar tus payloads **sin red**, usa este validador. Devuelve la lista de errores (vacía = correcto). Léelo: es una buena revisión del modelo de datos de OTLP.
    """)
    code('''
import re
HEX = lambda s, n: isinstance(s, str) and re.fullmatch(rf"[0-9a-f]{{{n}}}", s) is not None

def validate_trace_payload(p: dict) -> list[str]:
    errs = []
    try:
        spans = [s for rs in p["resourceSpans"] for ss in rs["scopeSpans"] for s in ss["spans"]]
    except (KeyError, TypeError):
        return ["estructura resourceSpans → scopeSpans → spans incorrecta"]
    if len(spans) != 3: errs.append(f"se esperaban 3 spans, hay {len(spans)}")
    tids = {s.get("traceId") for s in spans}
    if len(tids) != 1 or not all(HEX(t, 32) for t in tids): errs.append("traceId distinto entre spans o no es hex de 32")
    ids = [s.get("spanId") for s in spans]
    if not all(HEX(i, 16) for i in ids) or len(set(ids)) != len(ids): errs.append("spanId no es hex de 16 o está repetido")
    roots = [s for s in spans if not s.get("parentSpanId")]
    if len(roots) != 1: errs.append(f"debe haber exactamente 1 raíz, hay {len(roots)}")
    else:
        r = roots[0]; rs_, re_ = int(r["startTimeUnixNano"]), int(r["endTimeUnixNano"])
        for s in spans:
            if s is r: continue
            if s.get("parentSpanId") != r["spanId"]: errs.append(f"{s['name']}: el padre no es la raíz")
            a, b = int(s["startTimeUnixNano"]), int(s["endTimeUnixNano"])
            if not (rs_ <= a <= b <= re_): errs.append(f"{s['name']}: no está contenido en la raíz")
        kids = sorted((s for s in spans if s is not r), key=lambda s: int(s["startTimeUnixNano"]))
        if len(kids) == 2 and int(kids[0]["endTimeUnixNano"]) > int(kids[1]["startTimeUnixNano"]): errs.append("los dos hijos se solapan")
    names = {s["name"] for s in spans}
    for need in ("invoke_agent hola", "chat mock-small", "execute_tool get_order"):
        if need not in names: errs.append(f"falta el span «{need}»")
    for s in spans:
        if not isinstance(s.get("startTimeUnixNano"), str): errs.append("los tiempos deben ser strings")
    return errs

def validate_log_payload(p: dict, trace_id: str) -> list[str]:
    try:
        recs = [r for rl in p["resourceLogs"] for sl in rl["scopeLogs"] for r in sl["logRecords"]]
    except (KeyError, TypeError):
        return ["estructura resourceLogs → scopeLogs → logRecords incorrecta"]
    errs = []
    if len(recs) != 1: return [f"se esperaba 1 log, hay {len(recs)}"]
    r = recs[0]
    if r.get("severityNumber") != 9 or r.get("severityText") != "INFO": errs.append("severidad debe ser INFO (9)")
    if r.get("body", {}).get("stringValue") != "hola mundo": errs.append("cuerpo distinto de «hola mundo»")
    if r.get("traceId") != trace_id or not HEX(r.get("spanId"), 16): errs.append("el log no está correlacionado (traceId/spanId)")
    if "ticket.id" not in {a["key"] for a in r.get("attributes", [])}: errs.append("falta el atributo ticket.id")
    return errs

def validate_metric_payload(p: dict, n: int) -> list[str]:
    try:
        ms = [m for rm in p["resourceMetrics"] for sm in rm["scopeMetrics"] for m in sm["metrics"]]
    except (KeyError, TypeError):
        return ["estructura resourceMetrics → scopeMetrics → metrics incorrecta"]
    if len(ms) != 1 or ms[0]["name"] != "hello_requests": return ["debe haber una métrica llamada hello_requests"]
    s = ms[0].get("sum", {}); dp = (s.get("dataPoints") or [{}])[0]
    errs = []
    if s.get("aggregationTemporality") != 2 or s.get("isMonotonic") is not True: errs.append("debe ser sum acumulada (temporality 2) y monotónica")
    if dp.get("asInt") != str(n): errs.append(f"el valor debe ser {n} (asInt como string)")
    return errs

def validate_all(trace_id, payloads, n=5):
    if payloads is None: return {"traza": ["sin implementar"], "log": ["sin implementar"], "métrica": ["sin implementar"]}
    return {"traza": validate_trace_payload(payloads["/v1/traces"]), "log": validate_log_payload(payloads["/v1/logs"], trace_id),
            "métrica": validate_metric_payload(payloads["/v1/metrics"], n)}

print(validate_all(TRACE_ID, PAYLOADS))
''')

    md("""
    ## Paso 4 · Envía y verifica de extremo a extremo

    **TODO 3.** Implementa `send_and_verify(trace_id, payloads, timeout=90)`:

    1. `POST` de cada payload al Collector (`http://localhost:4318` + la ruta).
    2. *Polling* con plazo: busca la traza en Tempo (`backends.tempo_trace`) y comprueba que tiene **3 spans**; busca el log en Loki con LogQL `{service_name="proyecto-00"} | trace_id="<id>"` y la métrica en Prometheus (`hello_requests_total`).
    3. Devuelve un `dict` `{"traza": bool, "log": bool, "metrica": bool, "segundos": float}`.

    Si el Collector no está disponible, devuelve `None` (modo degradado).
    """)
    md(hint(1, "El `polling` de la lección (`wait_for`) ya hace casi todo. Cuenta los spans de Tempo con `sum(len(ss['spans']) for b in doc['batches'] for ss in b['scopeSpans'])`."))
    md(hint(2, "`backends.loki_query(logql, minutes=15)` devuelve una lista (vacía si no hay nada). `backends.prom_query('hello_requests_total')` devuelve una lista de series. Tempo tarda 15-30 s: usa un `timeout` de 90 s y una pausa de 2 s."))
    code('''
def wait_for(fn, timeout=90, every=2.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = fn()
            if r: return r
        except backends.BackendError:
            pass
        time.sleep(every)
    return None

def post(path, payload, base="http://localhost:4318"):
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status

def send_and_verify(trace_id, payloads, timeout=90):
    # TODO 3: enviar, esperar y verificar en Tempo, Loki y Prometheus
    raise NotImplementedError("TODO 3")

CHECK_STACK = check_stack(["core", "metrics"], verbose=False)
VERIFY = None
if PAYLOADS and CHECK_STACK.up.get("collector") and not any(validate_all(TRACE_ID, PAYLOADS).values()):
    try:
        VERIFY = send_and_verify(TRACE_ID, PAYLOADS)
        print(VERIFY)
    except NotImplementedError as e:
        print("Pendiente:", e)
else:
    print("Sin stack, sin payloads o con errores de validación: salto el envío.")
''')

    md("""
    ## Paso 5 · Tu primer dashboard, **como código**

    **TODO 4.** Completa `build_dashboard()` para devolver el JSON de un dashboard con **uid** `hola-mundo-NN` (elige tú el sufijo) y título «Hola mundo», con al menos 3 paneles de al menos 2 tipos:

    - un `stat` con la consulta PromQL `hello_requests_total` (datasource Prometheus, uid `prometheus`),
    - un `timeseries` con `sum(rate(otelcol_receiver_accepted_spans[1m]))` (Prometheus),
    - un panel de **logs** (`type: "logs"`) con la consulta LogQL `{service_name="proyecto-00"}` (datasource Loki, uid `loki`).

    Cada panel necesita `id` único, `title`, `type`, `gridPos` (`x,y,w,h`; el lienzo mide 24 de ancho), `datasource` (`{"type": ..., "uid": ...}`) y `targets` (con `refId` y `expr`).
    """)
    md(hint(1, "Mira `stack/grafana/dashboards/00-stack-overview.json`: es un dashboard real del repo con paneles `stat` y `timeseries`. Copia su estructura (`panels`, `gridPos`, `targets`)."))
    md(hint(2, "Estructura mínima de un panel: `{\"id\": 1, \"type\": \"stat\", \"title\": \"...\", \"datasource\": {\"type\": \"prometheus\", \"uid\": \"prometheus\"}, \"gridPos\": {\"x\": 0, \"y\": 0, \"w\": 8, \"h\": 6}, \"targets\": [{\"refId\": \"A\", \"expr\": \"...\"}]}`. Para Loki el `type` del datasource es `\"loki\"`. Dashboard: `{\"uid\": ..., \"title\": ..., \"schemaVersion\": 39, \"panels\": [...]}`."))
    code('''
DASH_UID = "hola-mundo-00"

def build_dashboard() -> dict:
    # TODO 4: devuelve el dict del dashboard (uid DASH_UID, título «Hola mundo», ≥ 3 paneles de ≥ 2 tipos)
    raise NotImplementedError("TODO 4")

def validate_dashboard(d: dict) -> list[str]:
    errs = []
    if d.get("uid") != DASH_UID: errs.append(f"uid debe ser {DASH_UID}")
    if not d.get("title"): errs.append("falta title")
    panels = d.get("panels", [])
    if len(panels) < 3: errs.append(f"se piden ≥ 3 paneles, hay {len(panels)}")
    if len({p.get('type') for p in panels}) < 2: errs.append("se piden ≥ 2 tipos de panel distintos")
    ids = [p.get("id") for p in panels]
    if len(set(ids)) != len(ids) or None in ids: errs.append("ids de panel repetidos o ausentes")
    uids = set()
    for p in panels:
        gp = p.get("gridPos", {})
        if not all(k in gp for k in "xywh") or gp.get("x", 0) + gp.get("w", 0) > 24: errs.append(f"gridPos incorrecto en «{p.get('title')}»")
        ds = p.get("datasource", {})
        uids.add(ds.get("uid"))
        if not p.get("targets") or not all("refId" in t and ("expr" in t) for t in p["targets"]): errs.append(f"targets incompletos en «{p.get('title')}»")
    if not {"prometheus", "loki"} <= uids: errs.append("deben usarse los datasources prometheus y loki (por uid)")
    if not any(p.get("type") == "logs" for p in panels): errs.append("falta un panel de tipo logs")
    return errs

try:
    DASH = build_dashboard()
    print("errores del validador:", validate_dashboard(DASH))
except NotImplementedError as e:
    DASH = None
    print("Pendiente:", e)
''')

    md("""
    ## Paso 6 · Publica el dashboard y compruébalo

    Dos formas de hacer un dashboard «como código»: (a) **provisionado** (copiar el JSON a `stack/grafana/dashboards/` y Grafana lo carga en ≤ 10 s) o (b) vía **API** de Grafana.
    Usaremos la API para poder verificarlo desde aquí.

    **TODO 5.** Implementa `publish_dashboard(d)`: `POST /api/dashboards/db` con `{"dashboard": d, "overwrite": True}` (usa `backends.grafana_post`) y después `GET /api/dashboards/uid/<uid>` (usa `backends.grafana_api`) para devolver el número de paneles guardado. Devuelve `None` si Grafana no está disponible.
    """)
    md(hint(1, "`backends.grafana_post(\"/api/dashboards/db\", {\"dashboard\": d, \"overwrite\": True})` devuelve un dict con `status: 'success'`. Para releerlo: `backends.grafana_api(f\"/api/dashboards/uid/{d['uid']}\")['dashboard']['panels']`."))
    code('''
def publish_dashboard(d: dict):
    # TODO 5: publicar vía API de Grafana y devolver len(paneles) releídos
    raise NotImplementedError("TODO 5")

PUBLISHED = None
if DASH and not validate_dashboard(DASH) and check_stack("grafana", verbose=False).up.get("grafana"):
    try:
        PUBLISHED = publish_dashboard(DASH)
        print("paneles guardados en Grafana:", PUBLISHED, "→ ábrelo en http://localhost:3000/d/" + DASH_UID)
    except NotImplementedError as e:
        print("Pendiente:", e)
else:
    print("Salto la publicación (sin Grafana, sin dashboard o con errores).")
''')

    md("""
    ## Paso 7 · Autoevaluación con la rúbrica

    Ejecuta la celda: calcula cada criterio. Lo que no se puede evaluar (porque no hay stack) aparece como **no evaluable**, no como fallo.
    """)
    code('''
def run_rubric() -> pd.DataFrame:
    rows = []
    st = check_stack(["core", "metrics"], verbose=False)
    def add(r, desc, ok, detail=""):
        rows.append({"criterio": r, "descripción": desc, "resultado": "—  no evaluable" if ok is None else ("✅ OK" if ok else "❌ FALLA"), "detalle": detail})
    # R1, R2 (online)
    try:
        rep = service_health_report()
        add("R1", "5/5 servicios listos", None if st.degraded and not st.up.get("collector") else bool((rep["estado"] == "up").all()), str(rep["estado"].value_counts().to_dict()))
    except NotImplementedError:
        add("R1", "5/5 servicios listos", False, "TODO 1 sin implementar")
    if st.up.get("grafana"):
        h = {u: backends.grafana_api(f"/api/datasources/uid/{u}/health").get("status") == "OK" for u in ["tempo", "loki", "prometheus"]}
        add("R2", "datasources tempo/loki/prometheus OK", all(h.values()), str(h))
    else:
        add("R2", "datasources tempo/loki/prometheus OK", None)
    # R3 (offline)
    errs = validate_all(TRACE_ID, PAYLOADS)
    add("R3", "payloads OTLP válidos (offline)", PAYLOADS is not None and not any(errs.values()), json.dumps(errs, ensure_ascii=False)[:160])
    # R4 (online)
    add("R4", "traza+log+métrica encontradas ≤ 90 s", None if VERIFY is None else all(VERIFY[k] for k in ("traza", "log", "metrica")) and VERIFY["segundos"] <= 90,
        str(VERIFY))
    # R5 (offline)
    derr = validate_dashboard(DASH) if DASH else ["sin implementar"]
    add("R5", "dashboard válido (offline)", not derr, "; ".join(derr)[:160])
    # R6 (online)
    add("R6", "dashboard publicado con sus paneles", None if PUBLISHED is None and not st.up.get("grafana") else (DASH is not None and PUBLISHED == len(DASH["panels"])), str(PUBLISHED))
    return pd.DataFrame(rows).set_index("criterio")

display(run_rubric())
''')

    md("""
    ---
    ## Retos extra (nivel experto)

    1. **Provisionado en lugar de API:** guarda tu dashboard en `stack/grafana/dashboards/01-hola-mundo.json`, espera ≤ 10 s y comprueba con `grafana_api` que aparece en la carpeta «Curso observabilidad de agentes». ¿Qué pasa si cambias el `uid` sin borrar el volumen? (pista: mira la tabla de pitfalls de la lección).
    2. **Canario permanente:** convierte `send_and_verify` en un script `canary.py` que un `cron`/GitHub Action pueda ejecutar y que termine con código de salida ≠ 0 si falta alguna señal. ¿Qué *timeout* eliges y por qué?
    3. **Perfil propio:** añade a `docker-compose.yml` (en una copia) un servicio opcional bajo el perfil `debug` con `otel/opentelemetry-collector-contrib` configurado con el exporter `debug`, y compara qué ve cada Collector.
    4. **Presupuesto de memoria:** añade `mem_limit` a cada servicio (calcula el valor a partir de `docker stats` bajo carga con `generate_tickets(500, start_s="live")` enviado a mano) y razona qué pasa cuando Tempo llega al límite.

    ## Reflexión (conecta con producción y con el hilo de SupportOps)

    - ¿Por qué verificar **de extremo a extremo** (traza canario) es mejor que mirar `docker compose ps`? ¿Qué fallos solo detecta el canario?
    - Tu equipo tendrá 5 agentes. ¿Un Collector por agente o uno compartido (*gateway*)? ¿Qué cambia en fallos, costes y seguridad? (lo retomamos en el módulo 05)
    - ¿Qué parte de este entorno pondrías bajo control de versiones y cuál *no* (datos, contraseñas)? ¿Qué harías con la contraseña `admin/admin` en un entorno compartido?
    - En el módulo 01 abrimos el agente SupportOps y empezamos a generar tráfico: ¿qué dos preguntas de negocio esperas poder contestar mirando Grafana al terminar el curso?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    Debajo está la **solución de referencia**, completa y ejecutable. Si te atascas, usa antes las pistas 🪜 de cada paso.
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
# TODO 1
def service_health_report() -> pd.DataFrame:
    names = ["collector", "tempo", "loki", "grafana", "prometheus"]
    st = check_stack(names, verbose=False)
    svc = services()
    return pd.DataFrame([{"servicio": n, "estado": "up" if st.up.get(n) else ("starting" if n in st.starting else "down"), "url": svc[n]["url"]}
                         for n in names])

# TODO 2
def build_hello(service: str = "proyecto-00", n_requests: int = 5):
    now = time.time_ns()
    trace_id, root, c1, c2 = secrets.token_hex(16), secrets.token_hex(8), secrets.token_hex(8), secrets.token_hex(8)
    resource, scope = {"attributes": attrs(**{"service.name": service})}, {"name": "proyecto.00", "version": "0"}
    span = lambda sid, name, kind, a, b, parent=None, **at: {**{"traceId": trace_id, "spanId": sid, "name": name, "kind": kind,
        "startTimeUnixNano": str(a), "endTimeUnixNano": str(b), "attributes": attrs(**at), "status": {"code": 1}},
        **({"parentSpanId": parent} if parent else {})}
    traces = {"resourceSpans": [{"resource": resource, "scopeSpans": [{"scope": scope, "spans": [
        span(root, "invoke_agent hola", 1, now - 400_000_000, now, **{"gen_ai.operation.name": "invoke_agent"}),
        span(c1, "chat mock-small", 3, now - 350_000_000, now - 150_000_000, root, **{"gen_ai.operation.name": "chat"}),
        span(c2, "execute_tool get_order", 1, now - 120_000_000, now - 30_000_000, root, **{"gen_ai.tool.name": "get_order"})]}]}]}
    logs = {"resourceLogs": [{"resource": resource, "scopeLogs": [{"scope": scope, "logRecords": [
        {"timeUnixNano": str(now), "severityNumber": 9, "severityText": "INFO", "body": {"stringValue": "hola mundo"},
         "traceId": trace_id, "spanId": root, "attributes": attrs(**{"ticket.id": "T-1"})}]}]}]}
    metrics = {"resourceMetrics": [{"resource": resource, "scopeMetrics": [{"scope": scope, "metrics": [
        {"name": "hello_requests", "unit": "{request}", "sum": {"aggregationTemporality": 2, "isMonotonic": True,
         "dataPoints": [{"startTimeUnixNano": str(now - 60_000_000_000), "timeUnixNano": str(now), "asInt": str(n_requests)}]}}]}]}]}
    return trace_id, {"/v1/traces": traces, "/v1/logs": logs, "/v1/metrics": metrics}

# TODO 3
def send_and_verify(trace_id, payloads, timeout=90):
    t0 = time.time()
    for path, payload in payloads.items():
        post(path, payload)
    n_spans = lambda doc: sum(len(ss["spans"]) for b in doc["batches"] for ss in b["scopeSpans"])
    tr = wait_for(lambda: (lambda d: d if n_spans(d) == 3 else None)(backends.tempo_trace(trace_id)), timeout)
    lg = wait_for(lambda: backends.loki_query(f'{{service_name="proyecto-00"}} | trace_id="{trace_id}"', minutes=15), timeout)
    mt = wait_for(lambda: backends.prom_query("hello_requests_total"), timeout) if check_stack("prometheus", verbose=False).up.get("prometheus") else None
    return {"traza": bool(tr), "log": bool(lg), "metrica": bool(mt), "segundos": round(time.time() - t0, 1)}

# TODO 4
def build_dashboard() -> dict:
    P, L = {"type": "prometheus", "uid": "prometheus"}, {"type": "loki", "uid": "loki"}
    return {"uid": DASH_UID, "title": "Hola mundo", "schemaVersion": 39, "editable": True, "time": {"from": "now-30m", "to": "now"}, "panels": [
        {"id": 1, "type": "stat", "title": "hello_requests", "datasource": P, "gridPos": {"x": 0, "y": 0, "w": 6, "h": 6},
         "targets": [{"refId": "A", "expr": "hello_requests_total", "instant": True}]},
        {"id": 2, "type": "timeseries", "title": "Spans aceptados por el Collector (por segundo)", "datasource": P, "gridPos": {"x": 6, "y": 0, "w": 18, "h": 6},
         "targets": [{"refId": "A", "expr": "sum(rate(otelcol_receiver_accepted_spans[1m]))"}]},
        {"id": 3, "type": "logs", "title": "Logs de proyecto-00", "datasource": L, "gridPos": {"x": 0, "y": 6, "w": 24, "h": 8},
         "targets": [{"refId": "A", "expr": '{service_name="proyecto-00"}'}]}]}

# TODO 5
def publish_dashboard(d: dict):
    r = backends.grafana_post("/api/dashboards/db", {"dashboard": d, "overwrite": True})
    assert r.get("status") == "success", r
    return len(backends.grafana_api(f"/api/dashboards/uid/{d['uid']}")["dashboard"]["panels"])

# --- ejecutar la solución de arriba a abajo ---
print(service_health_report())
TRACE_ID, PAYLOADS = build_hello()
print("validación offline:", validate_all(TRACE_ID, PAYLOADS))
CHECK_STACK = check_stack(["core", "metrics"], verbose=False)
if CHECK_STACK.up.get("collector"):
    VERIFY = send_and_verify(TRACE_ID, PAYLOADS); print("extremo a extremo:", VERIFY)
DASH = build_dashboard(); print("dashboard:", validate_dashboard(DASH))
if check_stack("grafana", verbose=False).up.get("grafana"):
    PUBLISHED = publish_dashboard(DASH); print("paneles publicados:", PUBLISHED)
display(run_rubric())
''')

    nb.save(out)


# =====================================================================================================================
README = """# Módulo 00 · Entorno: por qué los agentes rompen el monitoreo y cómo levantar el stack

🟢 Básico · ≈ 4 h · Servicios: perfil `core` (+ `metrics`) para la parte práctica; el resto funciona en modo degradado.

## Qué aprenderás
- Por qué un agente LLM rompe cuatro supuestos del monitoreo clásico (determinismo, longitud de la cadena, coste por petición, significado de «éxito»), **medido** con tráfico sintético de SupportOps.
- El mapa del stack: app (SDK OpenTelemetry) → Collector → Tempo / Loki / Prometheus → Grafana (+ Pyroscope).
- Docker y Compose desde cero: imagen, contenedor, volumen, red, puertos y **perfiles**; leer un `docker-compose.yml` línea a línea.
- Levantar el stack, comprobar que está **listo** (no solo «Up») y enviar a mano tu primera traza, log y métrica en OTLP/JSON.

## Archivos
| Archivo | Contenido |
|---|---|
| `00_entorno.ipynb` | Lección (teoría + código + 10 gráficos + autoevaluación) |
| `00_proyecto_entorno.ipynb` | Proyecto: levantar el stack, verificar su salud de extremo a extremo y crear tu primer dashboard como código |

## Servicios necesarios
```bash
cd agent-observability-course/stack
docker compose --profile core --profile metrics up -d     # ≈ 0,5 GB de RAM en reposo; ≈ 3,5 GB de imágenes la primera vez
```
Sin Docker: ambos notebooks funcionan en **modo degradado** (datos pregrabados; las comprobaciones online se marcan «no evaluable»).

## Lecturas
- Docker Docs, *Using profiles with Compose* — <https://docs.docker.com/compose/how-tos/profiles/>
- OpenTelemetry, *Observability primer* — <https://opentelemetry.io/docs/concepts/observability-primer/>
- Grafana Labs, `grafana/docker-otel-lgtm` — <https://github.com/grafana/docker-otel-lgtm>
- Honeycomb, *So We Shipped an AI Product. Did it Work?* — <https://www.honeycomb.io/blog/we-shipped-ai-product>

## Siguiente
`01_agente_base`: SupportOps por dentro (bucle LLM + herramientas, proveedor agnóstico, tráfico y fallos).
"""

if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    (COURSE / MOD / "README.md").write_text(README, encoding="utf-8")
    build_lesson()
    build_project()
