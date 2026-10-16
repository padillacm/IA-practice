"""Genera el módulo 02_tres_pilares: README, lección y proyecto.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_02.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "02_tres_pilares"


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "02_tres_pilares.ipynb", "Módulo 02 · Los tres pilares: traces, metrics y logs")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 02 · Los tres pilares: traces, metrics y logs (y el modelo de datos de OpenTelemetry)

    | | |
    |---|---|
    | **Nivel** | 🟢 Básico |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | **Ninguno** (usa tráfico simulado y los datos pregrabados del repo). Funciona igual en Colab |
    | **RAM aproximada** | < 400 MB (solo el kernel de Python) |
    | **Prerrequisitos** | Módulo 00 (mapa del stack, OTLP/JSON a mano) y módulo 01 (SupportOps v0, fallos inyectados, `RecordingInstrumentor`) |
    | **Hilo conductor** | Aprendes a *leer* telemetría de SupportOps antes de producirla con el SDK (módulo 03) |
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** qué pregunta responde cada señal (logs, métricas, trazas) y por qué un agente necesita las tres.
    2. **Construir a mano** un contador, un *gauge* y un histograma, y **estimar percentiles** a partir de sus *buckets* (con su error).
    3. **Describir** el modelo de datos de OpenTelemetry: *resource*, *instrumentation scope*, *span* (kind, status, atributos, eventos, enlaces), *log record* y tipos de métrica con su temporalidad.
    4. **Propagar contexto** con la cabecera W3C `traceparent` (implementarla a mano) y **demostrar** qué pasa cuando se rompe la propagación.
    5. **Correlacionar** señales: de una métrica anómala a una traza (exemplar) y de la traza a sus logs.
    6. **Aplicar** las *golden signals* (y RED/USE) a un agente: latencia, tráfico, errores y saturación **más** tokens/coste, pasos y calidad.
    7. **Calcular** por qué los percentiles no se promedian y cómo **explota la cardinalidad** de una métrica.
    8. **Decidir** qué señal detecta mejor cada tipo de fallo de un agente (preparación del proyecto).
    """)

    md("""
    ## 🔁 Conexión con módulos anteriores
    """)
    md(details("1 · (Módulo 00) ¿Qué trae el Collector en una petición OTLP/HTTP de trazas: dónde van `traceId` y los tiempos y en qué formato?",
               "En `POST :4318/v1/traces`, JSON jerárquico `resourceSpans → scopeSpans → spans`; `traceId` (32 hex) y `spanId` (16 hex) en **hexadecimal**, y `startTimeUnixNano`/`endTimeUnixNano` como **strings** de nanosegundos."))
    md(details("2 · (Módulo 01) ¿Por qué una alucinación es *más barata y rápida* que una respuesta correcta y qué implica para el monitoreo?",
               "Porque no llama herramientas (1 paso, ≈ 350 tokens frente a 5 pasos, ≈ 1300). Implica que una «mejora» de latencia/coste puede ser una regresión: hay que vigilar pasos/herramientas por petición y la calidad, no solo latencia y coste."))
    md(details("3 · (Módulo 01) ¿Qué punto de extensión del agente permite instrumentarlo y qué tres operaciones envuelve?",
               "El `Instrumentor` con context managers: `agent_run` (span raíz `invoke_agent`), `llm_call` (`chat`) y `tool_call` (`execute_tool`), más `log(...)`."))

    code(boot("viz"))
    code(IMPORTS + '''
_ = check_stack([])      # este módulo no necesita servicios
import json, re, secrets, bisect, math
''')

    # ------------------------------------------------------------------------------------------------ datos
    md("""
    ## Los datos de esta lección

    Trabajaremos con dos fuentes, ambas con el **mismo esquema** que producirá el SDK de OpenTelemetry:

    - **Pregrabados** (`sample_data`): 240 tickets de 60 min con fallos de fondo y **dos incidentes** (*proveedor LLM degradado* en los minutos 20-30 y *herramientas lentas* en 40-48): ejecuciones (`runs`), *spans* y *logs*.
    - **Generados al vuelo** con `RecordingInstrumentor`, para cuando necesitemos ver algo concreto.
    """)
    code('''
runs = pd.DataFrame(sample_data.load_runs())
spans = pd.DataFrame(sample_data.load_spans())
logs = pd.DataFrame(sample_data.load_logs())
meta = sample_data.load_meta()
spans["dur"] = (spans.end_unix_nano - spans.start_unix_nano) / 1e9
spans["minute"] = ((spans.start_unix_nano / 1e9 - SIM_EPOCH_S) // 60).astype(int)
runs["minute"] = ((runs.created_at - SIM_EPOCH_S) // 60).astype(int)
print(f"{len(runs)} ejecuciones · {len(spans)} spans · {len(logs)} logs · incidentes: {[ (i['name'], i['start_s']//60, i['end_s']//60) for i in meta['incidents']]}")
spans.head(3)[["trace_id", "span_id", "parent_span_id", "name", "kind", "status", "dur"]]
''')

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ---
    # 1 · Intuición: tres preguntas, tres señales

    Imagina que un cliente dice «el bot tardó una eternidad». Para investigarlo haces tres preguntas distintas:

    | Pregunta | Señal | Forma de los datos | Coste por dato | Para qué sirve |
    |---|---|---|---|---|
    | **¿Qué pasó exactamente?** | **Logs** | Eventos discretos con texto y campos | Alto (cada evento) | Detalle, auditoría, «qué dijo el error» |
    | **¿Cuánto y con qué frecuencia?** | **Métricas** | Series temporales numéricas agregadas | **Bajo y constante** | Alertas, tendencias, SLOs |
    | **¿Por dónde fue y dónde se fue el tiempo?** | **Trazas** | Árbol de *spans* de una petición | Alto (por petición, se muestrea) | Depurar un caso: causalidad y latencia |

    **Analogías:**

    | Si vienes de… | Logs | Métricas | Trazas |
    |---|---|---|---|
    | **ML** | Predicción *por muestra* (entrada, salida, error) | Métrica agregada (accuracy, AUC por lote) | *Debugging* de una predicción concreta: qué *features* y qué pasos del pipeline la produjeron |
    | **Microservicios** | `logger.error(...)` en cada servicio | Latencia p95, RPS, tasa de errores por endpoint | El *tracing distribuido* (Jaeger/Zipkin) de una petición a través de servicios |
    | **SRE** | La evidencia para el postmortem | Los SLIs que alimentan el SLO y la alerta | La herramienta del *on-call* para pasar de «algo va lento» a «esto va lento» |

    Veamos **las tres vistas de una misma petición lenta** de SupportOps, y cómo se *complementan*:
    """)
    code('''
demo_tk = generate_tickets(120, seed=SEED, fault_rates=DEFAULT_FAULT_RATES)
rec = RecordingInstrumentor()
demo_res = run_tickets(SupportAgent(instrumentor=rec), demo_tk)
roots = [s for s in rec.spans if s["parent_span_id"] is None]
warned = {l["trace_id"] for l in rec.logs if l["severity_number"] >= 13}                # trazas con algún log WARN o peor
slow = max([s for s in roots if s["trace_id"] in warned] or roots, key=lambda s: s["end_unix_nano"] - s["start_unix_nano"])
tid = slow["trace_id"]
mine = [s for s in rec.spans if s["trace_id"] == tid]
my_logs = [l for l in rec.logs if l["trace_id"] == tid]
D = pd.DataFrame(to_rows(demo_tk, demo_res)); D["minute"] = ((D.created_at - SIM_EPOCH_S) // 60).astype(int)
t0 = mine[0]["start_unix_nano"]; slow_minute = int((t0 / 1e9 - SIM_EPOCH_S) // 60)

fig = plt.figure(figsize=(15, 5.2)); gs = fig.add_gridspec(2, 2, width_ratios=[1.5, 1], left=0.19, right=0.98, wspace=0.12, hspace=0.45)
ax1 = fig.add_subplot(gs[:, 0]); viz.waterfall(mine, ax=ax1, title="TRAZAS · ¿por dónde fue y dónde se fue el tiempo? (1 petición)")
ax2 = fig.add_subplot(gs[0, 1]); ax2.axis("off"); ax2.set_title("LOGS · ¿qué pasó? (eventos de esa petición)", loc="left")
ax2.text(0, 0.9, "\\n".join(f"{(l['time_unix_nano'] - t0)/1e9:5.2f}s {l['severity_text']:5s} {l['body']}" for l in my_logs), va="top", family="monospace", fontsize=8.5)
ax3 = fig.add_subplot(gs[1, 1]); per_min = D.groupby("minute").latency_s.agg(["count", lambda x: np.quantile(x, .95)])
ax3.bar(per_min.index, per_min["count"], color=viz.PALETTE["metrics"], alpha=.5, label="peticiones/min"); ax3.set_ylabel("peticiones/min")
ax3b = ax3.twinx(); ax3b.plot(per_min.index, per_min.iloc[:, 1], color=viz.PALETTE["error"], marker="o", ms=3, label="p95 (s)"); ax3b.set_ylabel("p95 latencia (s)"); ax3b.grid(False)
ax3.axvline(slow_minute, color="k", ls=":"); ax3.set_title("MÉTRICAS · ¿cuánto? (todas las peticiones, agregadas)", loc="left"); ax3.set_xlabel("minuto")
plt.show()
print(f"trace_id de la petición lenta: {tid}  ({(slow['end_unix_nano']-slow['start_unix_nano'])/1e9:.1f} s)")
''')
    md(observe("""
    - **Métricas (abajo-derecha):** ven *que* hay un problema (el p95 sube en ese minuto) pero **no dicen cuál petición ni por qué**: la información se perdió al agregar.
    - **Trazas (izquierda):** muestran la **estructura** de esa petición concreta —cuántos pasos hubo, cuál fue lento, cuál falló (en rojo)— y por tanto **dónde** se fue el tiempo.
    - **Logs (arriba-derecha):** cuentan **qué ocurrió** con sus palabras (el mensaje de error), enlazados a la traza por el mismo identificador.
    - Se complementan: la métrica *avisa*, la traza *localiza*, el log *explica*. Ninguna sustituye a las otras; el resto del módulo es cómo se construyen y se unen.
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ---
    # 2 · Las tres señales «a mano»

    Antes del SDK, construimos cada señal con Python puro para entender qué datos contiene y qué *pierde*.

    ## 2.1 Logs: un evento con campos

    Un log es *(instante, severidad, mensaje, atributos)*. La diferencia clave es **texto libre vs estructurado**:
    """)
    code('''
l = logs[logs.body == "error de herramienta"].iloc[0]
print("NO estructurado (hay que parsear con regex):")
print("  ", f"{l.severity_text} {l.body} " + " ".join(f"{k}={v}" for k, v in l.attributes.items()))
print("\\nEstructurado (cada campo consultable):")
print(json.dumps({"time_unix_nano": int(l.time_unix_nano), "severity_text": l.severity_text, "severity_number": int(l.severity_number), "body": l.body,
                  "attributes": l.attributes, "trace_id": l.trace_id, "span_id": l.span_id}, ensure_ascii=False, indent=1)[:620])
# Pregunta analítica: ¿qué herramienta falla más? Con atributos es una línea; con texto sería un regex frágil.
w = logs[logs.body == "error de herramienta"]
print("\\nfallos por herramienta:", w.attributes.map(lambda a: a.get("tool")).value_counts().to_dict(), "·", "por error_type:", w.attributes.map(lambda a: a.get("error_type")).value_counts().to_dict())
''')
    md("""
    Dos propiedades hacen valiosos a los logs de producción: **estructura** (campos con nombre) y **correlación** (`trace_id` y `span_id` del span activo cuando se emitió el log). Severidad según OpenTelemetry:
    `1-4 TRACE`, `5-8 DEBUG`, `9-12 INFO`, `13-16 WARN`, `17-20 ERROR`, `21-24 FATAL`.

    ## 2.2 Métricas: contador, *gauge* e histograma

    Una métrica es una **serie temporal de números agregados**; no guarda peticiones individuales. Tres instrumentos esenciales (hay más: *UpDownCounter*, asíncronos…):

    | Instrumento | Qué es | Ejemplo en SupportOps | Operación válida |
    |---|---|---|---|
    | **Counter** | Solo sube (o se reinicia a 0 al reiniciar el proceso) | `agent_requests_total{status}` | `rate()`, `increase()` |
    | **Gauge** | Valor actual, sube y baja | ejecuciones en curso; uso de la ventana de contexto | media, máx., último |
    | **Histogram** | Distribución en *buckets* + suma + cuenta | `agent_request_duration_seconds` | percentiles aproximados, agregables entre instancias |

    Los implementamos **con su salida en el formato de texto de Prometheus** (lo que vería `GET /metrics`):
    """)
    code('''
class Counter:
    def __init__(self, name): self.name, self.v = name, {}
    def inc(self, n=1, **labels): k = tuple(sorted(labels.items())); self.v[k] = self.v.get(k, 0) + n

class Gauge:
    def __init__(self, name): self.name, self.v = name, {}
    def set(self, x, **labels): self.v[tuple(sorted(labels.items()))] = x

class Histogram:
    """Buckets con límites superiores (le = «menor o igual»); el último bucket implícito es +Inf."""
    def __init__(self, name, bounds): self.name, self.bounds = name, list(bounds); self.counts = [0] * (len(bounds) + 1); self.sum = 0.0; self.count = 0
    def record(self, x):
        self.counts[bisect.bisect_left(self.bounds, x)] += 1; self.sum += x; self.count += 1
    def quantile(self, q):
        """Estimación por interpolación lineal dentro del bucket (la misma idea que histogram_quantile de PromQL)."""
        target, cum = q * self.count, 0
        for i, c in enumerate(self.counts):
            if c and cum + c >= target:
                lo = 0.0 if i == 0 else self.bounds[i - 1]
                hi = self.bounds[i] if i < len(self.bounds) else self.bounds[-1] * 2        # el bucket +Inf no tiene techo: aproximamos
                return lo + (hi - lo) * (target - cum) / c
            cum += c
        return float("nan")

def exposition(*metrics):
    out = []
    for m in metrics:
        if isinstance(m, Histogram):
            out.append(f"# TYPE {m.name} histogram"); cum = 0
            for b, c in zip(m.bounds + [float("inf")], m.counts):
                cum += c; le = "+Inf" if b == float("inf") else b
                out.append(m.name + '_bucket{le="' + str(le) + '"} ' + str(cum))
            out += [f"{m.name}_sum {m.sum:.3f}", f"{m.name}_count {m.count}"]
        else:
            out.append(f"# TYPE {m.name} " + ("counter" if isinstance(m, Counter) else "gauge"))
            for k, v in m.v.items():
                lab = ",".join(a + '="' + str(b) + '"' for a, b in k)
                out.append(m.name + "{" + lab + "} " + str(v))
    return "\\n".join(out)

req_total = Counter("agent_requests_total"); dur = Histogram("agent_request_duration_seconds", [0.5, 1, 2, 3, 5, 8, 13]); ctx_gauge = Gauge("agent_context_tokens")
for r in runs.itertuples():
    req_total.inc(status=r.status); dur.record(r.latency_s); ctx_gauge.set(r.input_tokens, intent=r.intent_true)     # último valor por intención
print(exposition(req_total, dur, ctx_gauge))
''')
    md("""
    ### El histograma y el error de los percentiles

    Un histograma **descarta los valores individuales** y solo conserva *cuántos* cayeron en cada bucket. El percentil se estima **interpolando linealmente** dentro del bucket que contiene el rango $q\\cdot N$:

    $$ \\hat{x}_q \\;=\\; L_i \\;+\\; (U_i-L_i)\\,\\frac{q\\,N-C_{i-1}}{c_i} $$

    donde $[L_i,U_i]$ son los límites del bucket $i$ que contiene el percentil, $c_i$ su recuento y $C_{i-1}$ el recuento acumulado de los buckets anteriores. El **error** depende de cuán anchos son los buckets *justo donde está el percentil*.
    """)
    code('''
layouts = {"3 buckets gruesos [2, 10]": [2, 10], "exponencial [0.5…16]": [0.5, 1, 2, 4, 8, 16], "fino, paso 0.25 s": list(np.arange(0.25, 15, 0.25))}
exact = {q: np.quantile(runs.latency_s, q) for q in (0.5, 0.95)}
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8), sharey=False)
for ax, (name, b) in zip(axes, layouts.items()):
    h = Histogram("x", b); [h.record(v) for v in runs.latency_s]
    edges = [0] + h.bounds + [h.bounds[-1] * 1.6]; widths = np.diff(edges)
    ax.bar(edges[:-1], h.counts, width=widths, align="edge", color=viz.PALETTE["traces"], alpha=.7, edgecolor="white")
    for q, c in ((0.5, "ok"), (0.95, "error")):
        ax.axvline(h.quantile(q), color=viz.PALETTE[c], ls="--", lw=2); ax.axvline(exact[q], color="k", ls=":", lw=1.5)
    ax.set_title(f"{name}\\np95 estimado={h.quantile(.95):.2f}s · exacto={exact[0.95]:.2f}s (err {abs(h.quantile(.95)/exact[0.95]-1):.0%})", fontsize=10)
    ax.set_xlabel("latencia (s)"); ax.set_xlim(0, 16)
axes[0].set_ylabel("peticiones por bucket")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Las líneas **discontinuas de color** son la estimación desde los buckets (verde = mediana, roja = p95); las **punteadas negras**, el valor exacto calculado con todos los datos.
    - Con 3 buckets gruesos el p95 puede errar mucho (la estimación interpola dentro de un bucket enorme). Con buckets **exponenciales** el error baja bastante y con buckets finos casi desaparece… a cambio de **más series** (cada bucket es una serie en Prometheus).
    - Regla práctica de la élite: **pon límites de bucket alrededor de tus umbrales de SLO** (p. ej. justo en 3 s si tu SLO es «95 % < 3 s»), porque ahí es donde necesitas exactitud.
    """))

    md("""
    ## 2.3 Trazas: spans con padre, y «tiempo propio»

    Un **span** es una operación con inicio y fin; los spans de una petición forman un **árbol** (cada hijo apunta a su padre con `parent_span_id`). La traza es el conjunto de spans con el mismo `trace_id`.
    Una medida útil es el **tiempo propio** (*self time*): lo que tarda un span **sin contar a sus hijos**. Para un agente responde a «¿dónde se va el tiempo?».
    """)
    code('''
child_sum = spans[spans.parent_span_id.notna()].groupby("parent_span_id").dur.sum()
spans["self"] = spans.dur - spans.span_id.map(child_sum).fillna(0)
spans["tipo"] = spans.name.str.split().str[0].map({"invoke_agent": "agente (reintentos, esperas)", "chat": "LLM (chat)", "execute_tool": "herramientas"})
st = runs.set_index("ticket_id").status
tr2status = spans[spans.parent_span_id.isna()].assign(t=lambda d: d.attributes.map(lambda a: a["supportops.ticket.id"])).set_index("trace_id").t.map(st)
spans["estado"] = spans.trace_id.map(tr2status)
pivot = spans.pivot_table(index="estado", columns="tipo", values="self", aggfunc="sum").fillna(0)
share = pivot.div(pivot.sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(9, 3.8))
left = np.zeros(len(share))
for col, c in zip(["LLM (chat)", "herramientas", "agente (reintentos, esperas)"], [viz.PALETTE["traces"], viz.PALETTE["logs"], viz.PALETTE["warn"]]):
    ax.barh(share.index, share[col], left=left, color=c, label=col); left += share[col].values
ax.set_xlabel("% del tiempo (suma de tiempo propio de los spans)"); ax.set_title("¿Dónde se va el tiempo? Según cómo terminó la petición"); ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3, fontsize=8)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - En las peticiones `ok` **el LLM se lleva ≈ 90 % del tiempo**: optimizar una API interna casi no mueve la latencia de extremo a extremo.
    - En `degraded` (herramienta fallida o lenta) **las herramientas pasan de ≈ 10 % a ≈ 30 %** del tiempo (los timeouts de 5 s). En `error` aparece un ≈ 40 % de tiempo **del propio agente** (esperas de reintento con *backoff* mientras el proveedor falla).
    - Esta es una pregunta que **solo las trazas pueden contestar**: una métrica de latencia por separado no sabe qué parte de la petición pertenece a qué componente.
    """))

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ---
    # 3 · El modelo de datos de OpenTelemetry

    OpenTelemetry define un **modelo común** para las tres señales (y el protocolo OTLP que lo transporta). Todas comparten la misma envoltura: **quién** emite (*resource*) y **qué librería** lo midió (*scope*).

    - **Resource**: entidad que produce telemetría; un conjunto de atributos **inmutable**, p. ej. `service.name`, `service.version`, `deployment.environment.name`. Se comparte por todas las señales: es la clave de *join* gratuita.
    - **InstrumentationScope**: nombre (y versión) de la librería o módulo instrumentado (p. ej. `supportops.agent`). Permite saber *quién* instrumentó (y apagarlo).
    """)
    code('''
fig, ax = viz.canvas(13, 5.4, (0, 100), (0, 44))
viz.box(ax, 1, 1, 98, 41, "", viz.PALETTE["neutral"], fc="#00000004"); ax.text(2.5, 39.5, "ResourceSpans  (1 por resource)", fontsize=10, fontweight="bold", color=viz.PALETTE["neutral"])
viz.box(ax, 3, 24, 28, 12, "Resource\\nservice.name = supportops-agent\\nservice.version = 0.1.0\\ndeployment.environment.name = lab", viz.PALETTE["neutral"], fontsize=8)
viz.box(ax, 34, 3, 63, 34, "", viz.PALETTE["traces"], fc="#2a6fdb08"); ax.text(35.5, 34.5, "ScopeSpans  (1 por instrumentation scope)", fontsize=10, fontweight="bold", color=viz.PALETTE["traces"])
viz.box(ax, 36, 24, 24, 7, "Scope\\nname = supportops.agent", viz.PALETTE["traces"], fontsize=8)
viz.box(ax, 36, 5, 28, 17, "Span\\ntrace_id (16 B) · span_id (8 B)\\nparent_span_id\\nname · kind\\nstart/end (ns)\\nstatus (Unset|Ok|Error)", viz.PALETTE["traces"], fontsize=8, bold=False)
viz.box(ax, 67, 14, 28, 9, "attributes (clave→valor tipado)\\ngen_ai.*, supportops.*", viz.PALETTE["metrics"], fontsize=8)
viz.box(ax, 67, 4.5, 13, 7, "events\\n(exception…)", viz.PALETTE["logs"], fontsize=8); viz.box(ax, 82, 4.5, 13, 7, "links\\n(otras trazas)", viz.PALETTE["profiles"], fontsize=8)
viz.arrow(ax, (64.4, 15), (66.6, 17.5)); viz.arrow(ax, (64.4, 10), (66.6, 8))
ax.text(3, 15, "Mismo esquema para las otras señales:\\nLogs: ResourceLogs → ScopeLogs → LogRecord\\nMétricas: ResourceMetrics → ScopeMetrics → Metric", fontsize=8.5, style="italic", va="top")
plt.show()
''')
    md(observe("""
    - **Anidamiento**: `Resource ⊃ Scope ⊃ Span`. Lo que es común (quién emite, qué librería) se escribe **una vez** por lote, no por span; por eso OTLP es compacto.
    - Los atributos de **resource** describen *al emisor* y viajan con **todas** las señales (puedes filtrar logs, métricas y trazas por `service.name`); los atributos de **span** describen *esa operación*.
    - Logs y métricas tienen la misma estructura envolvente. Es lo que hizo posible nuestro «hola mundo» de 3 señales del módulo 00.
    """))

    md("""
    ## 3.1 El span, con precisión

    | Campo | Contenido | Notas |
    |---|---|---|
    | `trace_id` | 16 bytes (32 hex) | Al menos un byte distinto de cero. Común a toda la traza |
    | `span_id` | 8 bytes (16 hex) | Único dentro de la traza |
    | `parent_span_id` | `span_id` del padre | Vacío en el span **raíz** |
    | `name` | Texto de **baja cardinalidad** | `execute_tool get_order`, **no** `execute_tool ORD-00012` |
    | `kind` | `INTERNAL` (por defecto), `CLIENT`, `SERVER`, `PRODUCER`, `CONSUMER` | `CLIENT`: petición saliente que espera respuesta (p. ej. llamada al LLM); `SERVER`: la recibe; `PRODUCER/CONSUMER`: ejecución diferida (colas) |
    | `start/end` | ns desde la época Unix | Dos relojes: usa el monotónico para durar (ver 🧠) |
    | `status` | `Unset` (defecto), `Ok`, `Error` (+ mensaje) | Orden total `Ok > Error > Unset`; las librerías **no deberían** poner `Ok`; las aplicaciones sí pueden |
    | `attributes` | Pares clave→valor tipados | La carne del análisis: modelo, tokens, herramienta, ticket |
    | `events` | Marcas con tiempo dentro del span | Excepciones, «reintento»; baratos y viajan con la traza |
    | `links` | Referencias a otros spans/trazas | Relaciones no padre-hijo (p. ej. un lote que procesa muchos mensajes) |

    Veamos nuestros spans pregrabados **convertidos a OTLP/JSON a mano** (la misma forma que enviaste al Collector en el módulo 00):
    """)
    code('''
def to_otlp_json(span_records):
    """Spans (formato SPAN_SCHEMA del curso) → documento OTLP/JSON `resourceSpans`. Un resource, un scope."""
    def val(v):
        if isinstance(v, bool): return {"boolValue": v}
        if isinstance(v, int): return {"intValue": str(v)}
        if isinstance(v, float): return {"doubleValue": v}
        if isinstance(v, list): return {"arrayValue": {"values": [val(x) for x in v]}}
        return {"stringValue": str(v)}
    code_of = {"UNSET": 0, "OK": 1, "ERROR": 2}; kind_of = {"INTERNAL": 1, "SERVER": 2, "CLIENT": 3}
    res = span_records[0]["resource"]
    return {"resourceSpans": [{"resource": {"attributes": [{"key": k, "value": val(v)} for k, v in res.items()]},
        "scopeSpans": [{"scope": {"name": span_records[0]["scope"]}, "spans": [
            {"traceId": s["trace_id"], "spanId": s["span_id"], **({"parentSpanId": s["parent_span_id"]} if s["parent_span_id"] else {}),
             "name": s["name"], "kind": kind_of[s["kind"]], "startTimeUnixNano": str(s["start_unix_nano"]), "endTimeUnixNano": str(s["end_unix_nano"]),
             "attributes": [{"key": k, "value": val(v)} for k, v in s["attributes"].items()],
             "status": {"code": code_of[s["status"]], **({"message": s["status_message"]} if s["status_message"] else {})}} for s in span_records]}]}]}

one_trace = [s for s in sample_data.load_spans() if s["trace_id"] == sample_data.load_spans()[40]["trace_id"]]
doc = to_otlp_json(one_trace)
print(json.dumps(doc["resourceSpans"][0]["scopeSpans"][0]["spans"][1], indent=1, ensure_ascii=False)[:900])
print(f"\\n{len(one_trace)} spans → {len(json.dumps(doc))} bytes de JSON")
''')
    md("""
    > ⚠️ **No envíes estos datos tal cual a un Tempo vivo**: los timestamps simulados son de septiembre de 2026 y los backends descartan o rechazan datos muy antiguos. Para enviar tráfico en vivo, `generate_tickets(..., start_s="live")`.

    ## 3.2 Contexto y propagación (W3C Trace Context)

    ¿Cómo sabe un servicio B que su trabajo es *hijo* del span de A, si están en procesos distintos? **A le envía un identificador en una cabecera**. El estándar es la cabecera **`traceparent`** de W3C Trace Context:

    ```text
    traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
                 │  └──────── trace-id (32 hex) ───┘ └─ parent-id (16 hex) ┘ └ flags
                 └ versión
    ```

    El último byte son *flags*; el bit `01` = **sampled** («esta traza se está registrando»). El receptor extrae `trace_id` y `parent-id`, crea su propio span con ese **padre**, y sigue propagando. Si **nadie** propaga (o se pierde en un proxy/cola), la traza se **rompe** en dos.
    Implementémoslo a mano y simulemos un orquestador que llama a un servidor de herramientas (esto es lo que harán los módulos 11 y 12):
    """)
    code('''
def make_traceparent(trace_id: str, span_id: str, sampled: bool = True) -> str:
    return f"00-{trace_id}-{span_id}-{'01' if sampled else '00'}"

def parse_traceparent(h: str | None):
    """Devuelve dict o None si es inválida (formato incorrecto o ids todo ceros, que la spec declara inválidos)."""
    m = re.fullmatch(r"([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})", (h or "").strip())
    if not m or set(m.group(2)) == {"0"} or set(m.group(3)) == {"0"}: return None
    v, t, s, f = m.groups(); return {"version": v, "trace_id": t, "parent_id": s, "sampled": bool(int(f, 16) & 1)}

SIM = {"t": 0.0, "spans": []}                                       # reloj y almacén de spans del mini-experimento
def new_span(name, kind, trace_id=None, parent=None, dur=0.1, service="?"):
    s = {"trace_id": trace_id or secrets.token_hex(16), "span_id": secrets.token_hex(8), "parent_span_id": parent, "name": name, "kind": kind, "service": service,
         "status": "OK", "start_unix_nano": int(SIM["t"] * 1e9), "end_unix_nano": int((SIM["t"] + dur) * 1e9)}
    SIM["spans"].append(s); return s

def tool_server(headers: dict):                                     # «otro proceso»: solo ve las cabeceras que le llegan
    ctx = parse_traceparent(headers.get("traceparent"))
    SIM["t"] += 0.05
    return new_span("execute_tool get_order (servidor)", "SERVER", trace_id=ctx["trace_id"] if ctx else None, parent=ctx["parent_id"] if ctx else None, dur=0.12, service="orders-mcp")

def orchestrator(propagate: bool):
    SIM.update(t=0.0, spans=[])
    root = new_span("invoke_agent supportops", "INTERNAL", dur=0.6, service="supportops-agent")
    call = new_span("execute_tool get_order (cliente)", "CLIENT", trace_id=root["trace_id"], parent=root["span_id"], dur=0.25, service="supportops-agent")
    headers = {"traceparent": make_traceparent(call["trace_id"], call["span_id"])} if propagate else {}      # inyectar en la petición saliente
    tool_server(headers)
    return list(SIM["spans"])

ok, roto = orchestrator(True), orchestrator(False)
print("con propagación :", len({s["trace_id"] for s in ok}), "traza(s) ·", sum(s["parent_span_id"] is None for s in ok), "raíz")
print("sin propagación :", len({s["trace_id"] for s in roto}), "traza(s) ·", sum(s["parent_span_id"] is None for s in roto), "raíces (huérfano)")
print("round-trip traceparent:", parse_traceparent(make_traceparent("ab"*16, "cd"*8)), "| inválida →", parse_traceparent("00-000-xx"))
''')
    code('''
fig, axes = plt.subplots(2, 1, figsize=(10, 6)); fig.subplots_adjust(left=0.3, hspace=0.6)
for ax, data, title in [(axes[0], ok, "CON propagación: 1 traza, árbol completo"), (axes[1], roto, "SIN propagación: 2 trazas, el servidor queda huérfano")]:
    viz.waterfall(data, ax=ax, title=title)
plt.show()
''')
    md(observe("""
    - Con la cabecera `traceparent`, el span del servidor (`SERVER`) cuelga del span cliente (`CLIENT`): **un solo árbol**, con la causalidad correcta.
    - Sin ella, el servidor crea **otra traza** (otro `trace_id`) con su propio span raíz: en Tempo verías *dos* trazas inconexas y no podrías contestar «¿cuánto tardó el servidor de pedidos *dentro* de esta petición?».
    - En un agente multi-proceso (orquestador + subagentes + servidores MCP + colas) **cada salto** debe inyectar y extraer el contexto; un solo eslabón roto parte la traza. Es la causa nº 1 de «mis trazas salen cortadas».
    """))

    md("""
    ## 3.3 Métricas: temporalidad y tasas

    Un **contador** puede transmitirse como **acumulado** (*cumulative*: «desde el arranque llevo 4812 peticiones») o como **delta** («en los últimos 10 s hubo 37»). Prometheus usa acumulado y obtiene la **tasa** con `rate()` = incremento / tiempo.
    Si el proceso **se reinicia**, el contador vuelve a 0: una resta ingenua daría un valor *negativo*; `rate()` detecta la caída y la trata como reinicio.
    """)
    code('''
per_min = runs.groupby("minute").size().reindex(range(60), fill_value=0)
cum = per_min.cumsum().values.astype(float)
RESTART = 35                                                    # el proceso reinicia en el minuto 35: el contador vuelve a 0
obs = cum.copy(); obs[RESTART:] = cum[RESTART:] - cum[RESTART - 1]
naive = np.diff(obs, prepend=obs[0])                            # resta ingenua
def rate_reset_aware(c):
    d = np.diff(c, prepend=c[0]); return np.where(d < 0, c, d)  # si baja → reinicio: el incremento es el valor actual
smart = rate_reset_aware(obs)
fig, ax = plt.subplots(1, 2, figsize=(12, 3.6))
ax[0].plot(obs, color=viz.PALETTE["metrics"], lw=2); ax[0].axvline(RESTART, color="k", ls=":"); ax[0].text(RESTART + .5, obs.max() * .75, "reinicio del proceso", fontsize=9)
ax[0].set_title("Contador ACUMULADO agent_requests_total"); ax[0].set_xlabel("minuto"); ax[0].set_ylabel("valor del contador")
ax[1].bar(np.arange(60) - .2, naive, .4, color=viz.PALETTE["error"], label="resta ingenua (¡negativa!)"); ax[1].bar(np.arange(60) + .2, smart, .4, color=viz.PALETTE["ok"], label="tratando reinicios (rate)")
ax[1].set_title("Peticiones por minuto"); ax[1].set_xlabel("minuto"); ax[1].legend(fontsize=8)
plt.tight_layout(); plt.show()
print(f"incremento ingenuo en el minuto del reinicio: {naive[RESTART]:.0f}  ·  con tratamiento de reinicios: {smart[RESTART]:.0f}  ·  real: {per_min[RESTART]}")
''')
    md(observe("""
    - A la izquierda, el contador cae a casi 0 en el reinicio. A la derecha, la **resta ingenua** produce un pico negativo enorme (rojo); el tratamiento de reinicios (verde) recupera la tasa real.
    - Moraleja: **nunca restes contadores a mano**: usa `rate()`/`increase()`. Y recuerda que la tasa se calcula *por ventana*: ventanas cortas = ruidosas, largas = lentas en reaccionar.
    - Un contador **delta** (OTLP permite elegir) evita este problema pero obliga al backend a convertir a acumulado si lo necesita (Prometheus lo hace con `otlp-deltatocumulative`).
    """))

    md("""
    ## 3.4 Logs: el registro y su correlación

    | Campo del `LogRecord` | Significado |
    |---|---|
    | `Timestamp` / `ObservedTimestamp` | Cuándo ocurrió / cuándo lo observó el sistema de recogida |
    | `SeverityNumber` / `SeverityText` | Nivel (1-24) y su nombre |
    | `Body` | El mensaje (texto o estructura) |
    | `Attributes` | Campos estructurados |
    | **`TraceId`, `SpanId`, `TraceFlags`** | **Correlación con la traza activa** cuando se emitió el log |
    | `Resource`, `InstrumentationScope` | Quién y con qué librería |

    ## 3.5 Resumen: los cuatro «ejes» de cada señal

    | | Logs | Métricas | Trazas |
    |---|---|---|---|
    | Unidad | Evento | Punto agregado (serie × tiempo) | Span (operación) en un árbol |
    | Cardinalidad que soporta | Alta (cada evento es único) | **Baja** (cada combinación de labels = una serie) | Alta (cada petición es única) |
    | Coste | ∝ eventos | ∝ **series** (no eventos) | ∝ peticiones muestreadas |
    | Retiene detalle por petición | Sí | **No** | Sí |
    | Alerta | Posible pero cara | **La mejor opción** | Rara (se usa para investigar) |
    """)

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ---
    # 4 · Correlacionar: de la métrica a la traza y de la traza a los logs

    El valor máximo aparece cuando **las señales se enlazan**. Hay tres claves de unión:

    1. **Recurso común** (`service.name`, versión, entorno): une señales *del mismo servicio*.
    2. **`trace_id` / `span_id` en los logs**: une un log con *su* traza (y su span).
    3. **Exemplars**: un punto de una métrica (p. ej. el bucket más lento de un histograma) guarda el `trace_id` **de una petición concreta** que contribuyó a ese valor: el puente métrica → traza.

    Recorramos el camino completo con el incidente de los minutos 20-30 (proveedor LLM degradado):
    """)
    code('''
roots = spans[spans.parent_span_id.isna()].copy()
roots["ticket"] = roots.attributes.map(lambda a: a["supportops.ticket.id"])
roots = roots.merge(runs[["ticket_id", "latency_s", "status", "minute"]].rename(columns={"status": "run_status", "minute": "run_minute"}), left_on="ticket", right_on="ticket_id")
pm = roots.groupby("run_minute").agg(p95=("latency_s", lambda x: np.quantile(x, .95)), n=("latency_s", "size"), err=("run_status", lambda s: s.isin(["error", "max_steps"]).mean()))
# EXEMPLAR: por minuto, la traza más lenta (la que un histograma guardaría como exemplar del bucket más alto)
ex = roots.loc[roots.groupby("run_minute").latency_s.idxmax()].set_index("run_minute")
worst_min = pm.err.idxmax(); ex_tid = ex.loc[worst_min, "trace_id"]
fig = plt.figure(figsize=(11, 7.6)); gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.1], left=0.3, right=0.97, hspace=0.45)
ax1 = fig.add_subplot(gs[0]); ax1.plot(pm.index, pm.err * 100, color=viz.PALETTE["error"], marker="o", ms=3, label="% errores"); ax1.set_ylabel("% de peticiones con error", color=viz.PALETTE["error"]); ax1.set_xlabel("minuto")
ax1.axvspan(20, 30, color=viz.PALETTE["error"], alpha=.1); ax1.axvspan(40, 48, color=viz.PALETTE["warn"], alpha=.12)
ax1.scatter([worst_min], [pm.err[worst_min] * 100], s=120, facecolors="none", edgecolors="k", zorder=5); ax1.annotate("exemplar →", (worst_min, pm.err[worst_min] * 100), (worst_min - 14, pm.err[worst_min] * 100 + 3), arrowprops=dict(arrowstyle="->"))
ax1.set_title("MÉTRICA: tasa de error por minuto (franjas: incidentes)")
ax2 = fig.add_subplot(gs[1]); viz.waterfall(spans[spans.trace_id == ex_tid].to_dict("records"), ax=ax2, title=f"TRAZA del exemplar (minuto {worst_min})")
plt.show()
print("LOGS de esa traza (join por trace_id):")
for r in logs[logs.trace_id == ex_tid].itertuples(): print(f"  {r.severity_text:5s} {r.body}  {r.attributes}")
''')
    md(observe("""
    - La métrica señala un pico (**≈ minuto 26, dentro de la franja roja**): una tasa de error muy alta. Eso es «*que* algo pasa».
    - El **exemplar** nos lleva a *una* traza concreta de ese minuto: ahí vemos el span `chat` en rojo (el proveedor devolvió 5xx), los reintentos y el agente rindiéndose. Eso es «*dónde*».
    - Los **logs unidos por `trace_id`** dicen «error del proveedor LLM» con `status=503`. Eso es «*qué*».
    - Fíjate en la franja naranja (minutos 40-48): ahí **no hay errores** (la métrica de error no se mueve), pero algo pasa con la latencia: hay que mirar otras señales. Lo vemos en la sección 5.
    """))

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ---
    # 5 · Las *golden signals* aplicadas a agentes

    El libro de SRE de Google propone cuatro señales para monitorizar cualquier sistema orientado a usuarios: **latencia, tráfico, errores y saturación**. Dos recetas relacionadas:
    **RED** (*Rate, Errors, Duration*; Tom Wilkie, pensada para microservicios) y **USE** (*Utilization, Saturation, Errors*; Brendan Gregg, pensada para *recursos*).
    Para un agente hay que **extenderlas**:

    | Señal | En un servicio clásico | En un agente (SupportOps) | Dónde se mide |
    |---|---|---|---|
    | **Latencia** | Duración de la petición | Duración de `invoke_agent` **y** de cada `chat`/`execute_tool`; si hay *streaming*, tiempo al primer token. Separar éxito de error | Histograma + trazas |
    | **Tráfico** | Peticiones/s | Peticiones/s **y tokens/s** (el tráfico real del proveedor es en tokens) | Contador |
    | **Errores** | `5xx`, excepciones | Errores explícitos (**`error`**, `max_steps`) **+ implícitos**: respuesta inventada o con PII, herramienta caída con respuesta de cortesía (`degraded`) | Contador por `status`/`error.type` + evaluación online |
    | **Saturación** | CPU, colas, hilos | Límites de tasa del proveedor (429), peticiones concurrentes, **uso de la ventana de contexto**, cola de trabajos | Gauge / contadores de 429 |
    | **+ Coste** | (≈ constante) | USD por petición / por cliente / por función | Contador de tokens × precio |
    | **+ Pasos** | 1 | Llamadas LLM + herramientas por petición (¡bucles!) | Histograma |
    | **+ Calidad** | (implícita) | Fundamentación, utilidad, seguridad (módulo 14) | Evaluadores online |

    Construyamos el «dashboard de oro» de SupportOps con los datos pregrabados:
    """)
    code('''
runs["steps"] = runs.n_llm_calls + runs.n_tool_calls
g = runs.groupby("minute")
M = pd.DataFrame({
    "tráfico (peticiones/min)": g.size().reindex(range(60), fill_value=0),
    "errores (%)": (g.status.apply(lambda x: x.isin(["error", "max_steps"]).mean()) * 100).reindex(range(60)),
    "latencia p50 (s)": pd.Series([runs[(runs.minute <= m) & (runs.minute > m - 5)].latency_s.median() for m in range(60)]),     # ventana móvil de 5 min
    "latencia p95 (s)": pd.Series([runs[(runs.minute <= m) & (runs.minute > m - 5)].latency_s.quantile(.95) for m in range(60)]),
    "tokens de entrada / min": g.input_tokens.sum().reindex(range(60), fill_value=0),
    "pasos por petición": g.steps.mean().reindex(range(60)),
})
fig, axes = plt.subplots(2, 3, figsize=(15, 6)); axes = axes.ravel()
cols = ["tráfico (peticiones/min)", "errores (%)", "latencia p50 (s)", "tokens de entrada / min", "pasos por petición"]
for ax, c in zip(axes, cols):
    ax.plot(M.index, M[c], color=viz.PALETTE["traces"], marker="o", ms=2.5, lw=1.4); ax.set_title(c)
axes[2].plot(M.index, M["latencia p95 (s)"], color=viz.PALETTE["error"], lw=1.4, label="p95"); axes[2].plot(M.index, M["latencia p50 (s)"], color=viz.PALETTE["traces"], label="p50"); axes[2].legend(); axes[2].set_title("latencia p50 / p95 (s, ventana móvil de 5 min)")
ax = axes[5]; ax.plot(M.index, runs.groupby("minute").cost_usd.sum().reindex(range(60), fill_value=0) * 1000, color=viz.PALETTE["metrics"]); ax.set_title("coste (milésimas de USD / min)")
for ax in axes:
    ax.axvspan(20, 30, color=viz.PALETTE["error"], alpha=.1); ax.axvspan(40, 48, color=viz.PALETTE["warn"], alpha=.12); ax.set_xlabel("minuto")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Franja roja (min 20-30, proveedor LLM degradado):** sube la tasa de **errores**; fíjate que los **tokens de entrada** *bajan* (las llamadas fallidas no consumen tokens) y los **pasos** también: un fallo total *reduce* el coste.
    - **Franja naranja (min 40-48, herramientas lentas):** **no hay errores**, el tráfico y los tokens no cambian… pero la **latencia p95 se duplica o más** mientras la mediana sube mucho menos. Si solo vigilaras errores, no verías este incidente. Hace falta **latencia con percentiles altos** (y ventanas con suficientes peticiones: con pocos datos por minuto el p95 es ruidoso).
    - Ninguno de los seis paneles cuenta si las respuestas fueron **correctas**. Esa es la *quinta* señal que un agente necesita (módulo 14).
    """))

    # ------------------------------------------------------------------------------------------------ 6
    md("""
    ---
    # 6 · 📐 Percentiles: por qué no se promedian

    El percentil **no es lineal**: el p95 de la unión de dos conjuntos **no** es la media de sus p95. Un tablero que «promedia p95 de varias instancias» o «el p95 medio por minuto» da números sin significado estadístico.
    Lo correcto es **agregar los histogramas** (sumar los recuentos por bucket) y calcular el percentil sobre el histograma combinado.

    $$ p_{95}\\big(A\\cup B\\big)\\;\\neq\\;\\tfrac{1}{2}\\big(p_{95}(A)+p_{95}(B)\\big)\\qquad\\text{pero}\\qquad \\text{hist}(A\\cup B)=\\text{hist}(A)+\\text{hist}(B) $$

    Tres instancias del agente con tráfico muy desigual (la tercera es lenta pero casi no recibe peticiones):
    """)
    code('''
rng = np.random.default_rng(SEED)
pods = {"pod-a (90 %)": rng.lognormal(np.log(1.4), 0.30, 9000), "pod-b (9 %)": rng.lognormal(np.log(1.6), 0.35, 900), "pod-c (1 %, lento)": rng.lognormal(np.log(6.0), 0.40, 100)}
allv = np.concatenate(list(pods.values()))
bounds = [0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 20]
H = {}
for k, v in pods.items():
    h = Histogram(k, bounds); [h.record(x) for x in v]; H[k] = h
merged = Histogram("merged", bounds); merged.counts = [sum(h.counts[i] for h in H.values()) for i in range(len(bounds) + 1)]; merged.count = sum(h.count for h in H.values())
vals = {"promedio de los p95\\nde cada pod (MAL)": np.mean([np.quantile(v, .95) for v in pods.values()]), "p95 exacto\\nde todas las peticiones": np.quantile(allv, .95),
        "p95 del histograma\\nagregado (BIEN)": merged.quantile(.95)}
fig, ax = plt.subplots(figsize=(9, 3.6))
ax.bar(list(vals), list(vals.values()), color=[viz.PALETTE["error"], "k", viz.PALETTE["ok"]], alpha=.85)
for i, v in enumerate(vals.values()): ax.text(i, v + 0.05, f"{v:.2f}s", ha="center")
ax.set_ylabel("latencia p95 (s)"); ax.set_title("El p95 «global»: tres formas de calcularlo"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El **promedio de p95** (rojo) está inflado por el pod lento (que solo recibe el 1 % del tráfico pero pesa un tercio en el promedio simple): **sobreestima** mucho el p95 real.
    - El **histograma agregado** (verde) queda cerca del valor exacto (negro); la diferencia es el error de interpolar dentro del bucket (aquí el de 2-3 s).
    - Es la razón por la que Prometheus/OTel prefieren **histogramas** a «p95 precalculado en la aplicación»: los primeros se pueden sumar entre instancias, ventanas y servicios; los segundos, no.
    """))

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ---
    # 7 · 🧠 Cardinalidad: lo que rompe un sistema de métricas

    En métricas cada **combinación de valores de etiquetas** (*labels*) es una **serie temporal distinta**, y el coste de almacenamiento y consulta crece con el número de series, no con el de eventos. Para un histograma:

    $$ \\#\\text{series} \\;=\\; \\Big(\\prod_{l\\in\\text{labels}} |V_l|\\Big)\\times(\\#\\text{buckets}+2) $$

    (cada *bucket*, más `_sum` y `_count`, es una serie). Veamos qué ocurre al añadir etiquetas «razonables» a `agent_request_duration_seconds` (10 buckets):
    """)
    code('''
BUCKETS = 10
labels = [("intent (4)", 4), ("+ status (5)", 5), ("+ modelo (2)", 2), ("+ tier (2)", 2), ("+ canal (3)", 3), ("+ customer_id (200)", 200), ("+ ticket_id (1 por petición: 1000)", 1000)]
series, prod, names = [], 1, []
for n, c in labels:
    prod *= c; series.append(prod * (BUCKETS + 2)); names.append(n)
fig, ax = plt.subplots(figsize=(10, 4))
colors = [viz.PALETTE["ok"] if s < 5_000 else viz.PALETTE["warn"] if s < 100_000 else viz.PALETTE["error"] for s in series]
ax.bar(range(len(series)), series, color=colors); ax.set_yscale("log"); ax.set_xticks(range(len(series))); ax.set_xticklabels(names, rotation=30, ha="right", fontsize=8)
for i, s in enumerate(series): ax.text(i, s * 1.15, f"{s:,}".replace(",", "."), ha="center", fontsize=8)
ax.set_ylabel("series temporales (escala log)"); ax.set_title("Cada etiqueta multiplica las series (histograma de 10 buckets)"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con `intent` + `status` (+ modelo, tier, canal) estás en **cientos o pocos miles** de series: razonable.
    - `customer_id` multiplica **por 200** (varios cientos de miles de series): ya es un problema, y en producción real serán miles de clientes.
    - `ticket_id` (valor único por petición) crea una serie *nueva por petición*: cardinalidad **ilimitada**. Es el error clásico que tumba un Prometheus.
    - **Regla:** los identificadores de alta cardinalidad (ticket, cliente, trace_id) van en **trazas y logs** (donde cada evento ya es único), **no** en etiquetas de métricas. Si necesitas «métricas por cliente», usa pocos grupos (p. ej. `tier`) o atribución a través de trazas/span metrics (módulo 18).
    """))

    # ------------------------------------------------------------------------------------------------ 8
    md("""
    ---
    # 8 · ¿Qué señal detecta qué fallo? (hipótesis para el proyecto)

    Con lo visto en el módulo 01 (huellas de cada fallo) y en esta lección (qué ve cada señal), podemos formular una **hipótesis** de detectabilidad. En el **proyecto** la *medirás* con 10 incidentes simulados; aquí solo la razonamos.
    Escala: 2 = la señal lo detecta con claridad · 1 = lo deja ver pero ambiguo/indirecto · 0 = ciega.
    """)
    code('''
H = pd.DataFrame({
    "métricas (RED + tokens)":  [2, 2, 0, 2, 0, 2, 1, 0],
    "logs":                     [2, 0, 2, 2, 2, 1, 0, 0],
    "trazas":                   [2, 2, 2, 2, 2, 2, 0, 0],
    "contenido / evaluación":   [0, 0, 0, 0, 0, 0, 2, 2],
}, index=["llm_error persistente", "latencia del LLM ×6", "tool_error (degraded)", "tool_timeout", "reintentos 429 (transitorio)", "tool_loop", "alucinación", "fuga de PII"])
fig, ax = plt.subplots(figsize=(8.5, 4.4))
im = ax.imshow(H.values, cmap="RdYlGn", vmin=0, vmax=2, aspect="auto")
ax.set_xticks(range(H.shape[1])); ax.set_xticklabels(H.columns, rotation=20, ha="right"); ax.set_yticks(range(H.shape[0])); ax.set_yticklabels(H.index)
for i in range(H.shape[0]):
    for j in range(H.shape[1]): ax.text(j, i, ["ciega", "indirecta", "clara"][H.values[i, j]], ha="center", va="center", fontsize=8)
ax.set_title("HIPÓTESIS de detectabilidad (la mediremos en el proyecto)"); ax.grid(False); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Cada fila tiene al menos una señal clara **salvo** alucinaciones y fugas de PII: **ninguno de los tres pilares las ve de forma directa**. Hace falta mirar el **contenido** (evaluación online, filtros de PII): un cuarto «pilar» propio de los agentes.
    - Algunas filas son **ciegas para las métricas** (`tool_error` y los reintentos, porque el agente absorbe el fallo y la petición raíz sale «ok»): ahí mandan logs y trazas. Lección: alertar *solo* sobre la tasa de error de la petición raíz es insuficiente.
    - Esto es una **hipótesis razonada**, no un dato. En el proyecto la contrastarás con mediciones y verás si aguanta.
    """))

    # ------------------------------------------------------------------------------------------------ prod / elite
    md("""
    ---
    # 9 · 🏭 En producción

    - **Google (Dapper, 2010):** el artículo describe la infraestructura de *tracing* distribuido de Google y atribuye parte de su éxito al **muestreo** y a limitar la instrumentación a un pequeño conjunto de librerías comunes. Es el origen conceptual de Zipkin, Jaeger y OpenTelemetry (según resúmenes posteriores) y justifica por qué en producción **no se guarda el 100 % de las trazas** (módulo 18).
    - **Honeycomb** (Majors, Fong-Jones y Miranda, *Observability Engineering*, 2022) defiende guardar **eventos estructurados de alta dimensionalidad** y explorar de forma abierta, en lugar de depender solo de métricas pre-agregadas: es la razón de que las trazas con muchos atributos (modelo, tokens, cliente, herramienta) sean tan valiosas en agentes.
    - **Grafana Labs** formalizó **RED** (Tom Wilkie, 2015-2018) para servicios y recomienda, junto con la **USE** de Brendan Gregg para recursos, un conjunto **mínimo y consistente** de métricas por servicio: es lo que replicamos para `invoke_agent`, `chat` y `execute_tool`.
    - **Google SRE (cap. 6):** las cuatro *golden signals* y la recomendación de **alertar sobre síntomas** (lo que siente el usuario) más que sobre causas internas.
    - **OpenTelemetry:** especifica el modelo de datos de las tres señales y de **correlación** entre ellas (trace_id en logs, exemplars en métricas). Los atributos específicos de GenAI (`gen_ai.*`) están en estado *Development*: úsalos con versión fijada (módulo 04).
    """)
    md(box("elite", "Secretos de la élite · los tres pilares", """
    1. **Cardinalidad = coste (y caídas).** Cada combinación de etiquetas es una serie. Los IDs (cliente, ticket, `trace_id`) pertenecen a trazas y logs; en métricas, pocas dimensiones acotadas (modelo, intención, estado, tier). Controla la cardinalidad con *views* del SDK o el Collector (módulos 05 y 18).
    2. **Los percentiles no se agregan; los histogramas sí.** Elige los *buckets* alrededor de tus umbrales de SLO. Los histogramas **exponenciales** de OpenTelemetry (si tu backend los soporta) dan buena precisión con pocos parámetros — compruébalo en tu backend antes de adoptarlos.
    3. **El muestreo sesga las métricas.** Si calculas «tasa de error» solo con las trazas que sobreviven al *tail sampling* (que conserva errores y lentas), tu tasa sale inflada. Las métricas RED deben calcularse **antes** de muestrear (span metrics del Collector, o instrumentos de métricas en la app).
    4. **El error de la raíz oculta errores de los hijos.** Un agente que absorbe un fallo (reintento, disculpa) deja la petición en `ok`. Alerta sobre **errores por tipo de span** (`execute_tool` por herramienta, `chat` por proveedor), no solo sobre la raíz.
    5. **Relojes:** las duraciones deben medirse con reloj **monotónico**; las marcas de tiempo de pared (NTP) pueden retroceder y producir spans con duración negativa o hijos «antes» que su padre entre máquinas. Las trazas multi-host siempre tienen algo de *skew*.
    6. **Eventos de span vs. logs:** un evento dentro del span viaja y se muestrea con la traza (barato, contextual); un log independiente se retiene por separado (útil para auditoría y para lo que ocurre *fuera* de un span). Para un agente: reintentos y excepciones → eventos; auditoría de acciones → logs.
    7. **Status:** deja `Unset` salvo error; `Ok` (que las librerías *no* deberían establecer) es **final** y suprime errores posteriores en las herramientas de análisis. Ponerlo «por si acaso» esconde fallos.
    8. **Nombres de span de baja cardinalidad** (`execute_tool get_order`, no `…ORD-00012`): el nombre agrupa en *service maps*, *span metrics* y consultas; el detalle va en atributos.
    9. **Contenido de prompts y completions = datos sensibles y voluminosos.** No es una métrica ni un log por defecto: se captura de forma opcional, redactada y con retención corta (módulo 20).
    """))
    md(box("warn", "Errores comunes (pitfalls)", """
    - Promediar percentiles o «p95 medio por instancia».
    - Restar contadores a mano (valores negativos tras un reinicio).
    - Poner `user_id` / `trace_id` como etiqueta de métrica.
    - Alertar solo sobre errores de la petición raíz (los fallos parciales no aparecen).
    - Logs en texto libre sin `trace_id`: no se pueden correlacionar ni consultar por campos.
    - Perder el contexto en colas, hilos o clientes HTTP sin instrumentar: trazas partidas.
    - Medir «tiempo de respuesta» sin separar éxito de error (un error rápido mejora la media).
    - Confundir *métrica de recurso* (CPU del pod) con *saturación del agente* (límite de tasa del proveedor, ventana de contexto).
    """))

    # ------------------------------------------------------------------------------------------------ autoevaluación
    md("""
    ---
    # 10 · Autoevaluación
    """)
    qs = [
        ("1 · (Cálculo) Percentil desde un histograma",
         """Un histograma con límites `[1, 2, 5]` s tiene recuentos por bucket `(≤1: 50, 1-2: 30, 2-5: 15, >5: 5)`. Estima el p90 por interpolación lineal.""",
         """N = 100; objetivo = 0,9·100 = 90. Acumulados: 50, 80, 95. El bucket que contiene el rango 90 es (2, 5] con recuento 15 y acumulado previo 80. p90 ≈ 2 + (5−2)·(90−80)/15 = 2 + 3·10/15 = **4,0 s**. Si dijeras «el p90 está entre 2 y 5 s» también sería correcto, pero la interpolación asume reparto uniforme dentro del bucket."""),
        ("2 · (Cálculo) Tasa con reinicio",
         """Un contador lee, en cuatro lecturas separadas 60 s: 100, 160, 20, 80. ¿Cuántas peticiones por segundo hubo en total en esa ventana (tratando el reinicio)?""",
         """Incrementos: 100→160 = +60; 160→20 es una **caída** (reinicio): el incremento es el valor actual = 20; 20→80 = +60. Total = 140 en 180 s ⇒ **≈ 0,78 req/s**. La resta ingenua (80−100 = −20) sería absurda."""),
        ("3 · (Cálculo) Cardinalidad",
         """Quieres un histograma de 12 buckets con etiquetas `intent` (4), `status` (5) y `model` (3). ¿Cuántas series? Si añades `tier` (2) y `customer_id` (300), ¿y ahora?""",
         """(4·5·3)·(12+2) = 60·14 = **840** series. Con `tier` y `customer_id`: 60·2·300 = 36 000 combinaciones · 14 = **504 000** series (600× más). `customer_id` es el culpable: va a trazas/logs."""),
        ("4 · (Diagnóstico) Trazas partidas",
         """Tras desplegar un servidor de herramientas, en Tempo ves dos trazas por petición: una con el agente y otra con solo el servidor. ¿Qué ha pasado y cómo lo compruebas?""",
         """El contexto **no se propaga** entre el agente y el servidor: falta inyectar `traceparent` en la llamada saliente (cliente) o extraerlo en la entrante (servidor), o un proxy/cola descarta la cabecera. Comprobación: capturar la petición saliente y buscar la cabecera `traceparent`; en el servidor, comprobar que el span `SERVER` tiene `parent_span_id` distinto de vacío. Las trazas del servidor tienen un único span raíz con *kind* `SERVER` y sin padre."""),
        ("5 · (Diagnóstico) La alerta que no salta",
         """Los clientes se quejan de lentitud durante 10 minutos pero tu alerta («tasa de error > 5 %») no se dispara y la latencia *mediana* apenas se mueve. ¿Qué cambias?""",
         """La latencia degradada afecta a una **fracción** de peticiones (cola): la mediana la oculta y no son errores. Alertar sobre **p95/p99 de latencia** (histograma, ventana adecuada) y, para el mismo síntoma, sobre el **burn rate** de un SLO de latencia (módulo 16). Usa trazas del p99 para localizar el span responsable."""),
        ("6 · (Diagnóstico) «Más barato y rápido»",
         """El dashboard muestra, tras un cambio de prompt, −40 % de coste y −35 % de latencia sin errores. ¿Qué señal añades para decidir si es bueno?""",
         """**Pasos/herramientas por petición** (una caída fuerte es sospechosa) y una **señal de calidad** (fundamentación/evaluación online), más una muestra de trazas antes y después. Sin ellas no puedes distinguir eficiencia de regresión silenciosa."""),
        ("7 · (Transferencia) Del ML a los agentes",
         """En un modelo de recomendación monitorizas CTR (agregado) y revisas casos individuales cuando cae. ¿A qué señal corresponde cada cosa en un agente de soporte?""",
         """El CTR agregado ≈ **métricas** (tasa de resolución, p95, coste); revisar casos individuales ≈ **trazas** (el recorrido del agente) con **logs** correlacionados y, para la calidad de la respuesta, **evaluación online** (equivalente a las etiquetas tardías)."""),
        ("8 · (Transferencia) Una API de pagos",
         """Aplica *golden signals* a una API de pagos con LLM antifraude. ¿Qué cambia respecto a SupportOps?""",
         """Latencia (con SLO estricto), tráfico, errores y saturación siguen valiendo; **sube la importancia** de: errores *silenciosos* (falsos negativos del modelo antifraude), de la **auditoría** (logs inmutables con retención y PII redactada) y de la **calidad** medida con etiquetas tardías (contracargos). Cardinalidad: `merchant_id` en trazas, no en métricas."""),
    ]
    for title, q, a in qs:
        md(f"**Pregunta {title}**\n\n{q}\n\n" + details("Ver respuesta", a))

    md("""
    ---
    # 11 · Referencias

    - OpenTelemetry, *Specification overview* — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/overview.md>; *Trace API* (SpanContext, SpanKind, Status) — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/api.md>;
      *Logs Data Model* (campos, `SeverityNumber` 1-24) — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/logs/data-model.md>; *Metrics Data Model* (temporalidad, exemplars) — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/data-model.md>.
    - W3C, *Trace Context* (cabecera `traceparent`) — <https://www.w3.org/TR/trace-context/> (la especificación de OpenTelemetry ya referencia también el nivel 2, con el flag *random*).
    - Sigelman, Barroso, Burrows et al., *Dapper, a Large-Scale Distributed Systems Tracing Infrastructure*, Google Technical Report dapper-2010-1, 2010 — <https://research.google/pubs/pub36356/>.
    - Beyer, Jones, Petoff, Murphy (eds.), *Site Reliability Engineering*, O'Reilly 2016, cap. 6 *Monitoring Distributed Systems* (las cuatro golden signals) — <https://sre.google/sre-book/monitoring-distributed-systems/>.
    - Tom Wilkie, *The RED Method: How to Instrument Your Services*, Grafana Labs, 2018 — <https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/>.
    - Brendan Gregg, *The USE Method* — <https://www.brendangregg.com/usemethod.html>.
    - Charity Majors, Liz Fong-Jones, George Miranda, *Observability Engineering*, O'Reilly, 2022 (ISBN 978-1-492-07644-5).
    - Prometheus, *Histograms and summaries* y `histogram_quantile` (documentación oficial) — <https://prometheus.io/docs/practices/histograms/>.
    - OpenTelemetry, *GenAI semantic conventions* (estado Development) — <https://github.com/open-telemetry/semantic-conventions-genai>.

    **Siguiente:** haz el **proyecto** (`02_proyecto_tres_pilares.ipynb`): clasificar 10 incidentes de SupportOps según qué señal los detecta. Después, módulo 03: producirás estas señales con el SDK de OpenTelemetry.
    """)
    nb.save(out)


# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "02_proyecto_tres_pilares.ipynb", "Proyecto 02 · Diagnóstico de 10 incidentes: ¿qué señal los detecta?")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 02 · Diez incidentes de SupportOps: ¿qué señal los detecta y por qué?

    | | |
    |---|---|
    | **Nivel** | 🟢 Básico |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (todo simulado; funciona en Colab) |
    | **RAM aproximada** | < 400 MB |
    | **Prerrequisitos** | Lección `02_tres_pilares` y proyecto 01 (fallos inyectados) |
    | **Conexión** | Convierte las «huellas» del proyecto 01 en una **política de alertas**: qué señal vigilar para qué fallo. Es la hoja de ruta de los módulos 03-10 |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Tras tres meses en producción, el equipo de on-call os pide un **mapa de detección**: para cada tipo de incidente que habéis sufrido, ¿qué señal salta primero, cuál sirve para localizar y cuáles son ciegas?
    Tienes **telemetría de 10 incidentes simulados** (cada uno: 30 min de línea base «normal» + 30 min con el incidente) en el formato de OpenTelemetry (ejecuciones, *spans* y *logs*). Tu trabajo: **medir** y **clasificar**.

    ## Datos

    `simulate(nombre)` genera la telemetría de un incidente con semilla fija (determinista). Los incidentes: `llm_outage`, `llm_slow`, `tool_errors`, `tool_timeout`, `retry_storm`, `tool_loop`, `hallucination`, `pii_leak`, `cost_drift`, `traffic_spike`.
    No hay datasets externos; **no se necesitan servicios** (no hay modo degradado porque nada depende del stack).

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución, `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `per_minute_metrics` | Para `llm_outage`: 60 filas; `requests` suma 200; la tasa de error media por minuto de la fase B ≈ la tasa global medida por la solución | tolerancia ±0,05 |
    | R2 | `culprit_name` | Sobre `llm_slow`, `tool_timeout` y `retry_storm` devuelve el mismo span responsable que la solución en ≥ 90 % de las trazas anómalas | ≥ 90 % |
    | R3 | `phase_features` | Las 9 características coinciden con la solución (tolerancia relativa 2 %) en 3 incidentes de prueba | 3/3 |
    | R4 | `fires` (qué señales saltan) | El conjunto de señales (`M`étricas, `L`ogs, `T`razas) coincide con la verdad en ≥ 9 de 10 incidentes | ≥ 9/10 |
    | R5 | `diagnose` | Etiqueta correcta (incluye `sin_senal`) en ≥ 8 de 10 incidentes | ≥ 8/10 |
    | R6 | Puntos ciegos | Identificas **exactamente** los incidentes donde *ninguna* señal salta y los que **no ve la métrica** pero sí logs/trazas | coincidencia exacta |

    > 📏 Los umbrales salen de la solución de referencia, comprobada con 5 semillas distintas (42, 7, 99, 123, 2024): las clasificaciones son estables. No dependen de tu máquina (el tiempo es simulado).
    """)

    code(boot("viz"))
    code(IMPORTS + '''
import json, re, collections
_ = check_stack([])      # este proyecto no necesita servicios
''')

    md("""
    ## Paso 0 · El simulador de incidentes (te lo damos hecho)

    Cada incidente tiene **dos fases de 30 min**: **A = línea base** (sin fallos) y **B = incidente**. Se registra con `RecordingInstrumentor`, así que tienes `runs` (una fila por ticket), `spans` y `logs` con el esquema del curso.
    `cost_drift` simula que alguien cambió el modelo por uno 12× más caro en la fase B; `traffic_spike` triplica el tráfico en B.
    """)
    code('''
A_START, B_START = SIM_EPOCH_S, SIM_EPOCH_S + 1800
SCENARIOS = {   # nombre: (tipo de fallo en la fase B, probabilidad por ticket, parámetros)
    "llm_outage":    ("llm_error", 0.6, {"status": 503, "persistent": True}),
    "llm_slow":      ("latency_spike", 0.8, {"factor": 6.0, "target": "llm"}),
    "tool_errors":   ("tool_error", 0.5, {}),
    "tool_timeout":  ("tool_timeout", 0.4, {"timeout_s": 5.0}),
    "retry_storm":   ("llm_error", 0.6, {"status": 429, "persistent": False}),
    "tool_loop":     ("tool_loop", 0.4, {}),
    "hallucination": ("hallucination", 0.5, {}),
    "pii_leak":      ("pii_leak", 0.3, {}),
    "cost_drift":    (None, 0, {}),
    "traffic_spike": (None, 0, {}),
}

def simulate(name: str, seed: int = SEED, n_base: int = 100) -> dict:
    kind, prob, params = SCENARIOS[name]
    n_b = n_base * (3 if name == "traffic_spike" else 1)
    ta = generate_tickets(n_base, seed, duration_s=1800, start_s=A_START)
    inc = [Incident(name, kind, 0, 1800, prob, params)] if kind else []
    tb = generate_tickets(n_b, seed + 1, duration_s=1800, start_s=B_START, incidents=inc)
    rec = RecordingInstrumentor()
    small = SupportAgent(llm=MockLLM("mock-small", seed=seed), instrumentor=rec)
    big = SupportAgent(llm=MockLLM("mock-large" if name == "cost_drift" else "mock-small", seed=seed), instrumentor=rec)
    rows = to_rows(ta, run_tickets(small, ta)) + to_rows(tb, run_tickets(big, tb))
    runs = pd.DataFrame(rows)
    runs["phase"] = np.where(runs.created_at < B_START, "A", "B"); runs["minute"] = ((runs.created_at - A_START) // 60).astype(int)
    runs["steps"] = runs.n_llm_calls + runs.n_tool_calls
    spans = pd.DataFrame(rec.spans); spans["dur"] = (spans.end_unix_nano - spans.start_unix_nano) / 1e9
    logs = pd.DataFrame(rec.logs)
    return {"name": name, "runs": runs, "spans": spans, "logs": logs}

INC = {n: simulate(n) for n in SCENARIOS}
print({n: (len(d["runs"]), len(d["spans"]), len(d["logs"])) for n, d in INC.items()})
INC["llm_outage"]["runs"].head(3)[["ticket_id", "phase", "minute", "status", "latency_s", "steps", "input_tokens", "cost_usd"]]
''')

    md("""
    ## Paso 1 · La señal de **métricas**: tabla por minuto

    Las métricas son agregados. **TODO 1.** Implementa `per_minute_metrics(runs)` que devuelva un `DataFrame` con **60 filas** (índice `minute` de 0 a 59, rellena con 0/NaN los minutos vacíos) y columnas:
    `phase` (A/B), `requests`, `error_rate` (fracción de `status` en {`error`,`max_steps`}), `p95_latency_s`, `tokens_in_per_req`, `cost_per_req`, `steps_per_req`.
    """)
    md(hint(1, "`runs.groupby('minute')` con `.agg(...)`, y después `.reindex(range(60))`. Para `error_rate` usa `status.isin([...]).mean()`; para el p95 `quantile(0.95)`. La fase de un minuto es `'A'` si `minute < 30`, `'B'` si no."))
    md(hint(2, "Estructura: `g = runs.groupby('minute'); out = pd.DataFrame({'requests': g.size(), 'error_rate': g.status.apply(lambda s: s.isin(['error','max_steps']).mean()), 'p95_latency_s': g.latency_s.quantile(.95), 'tokens_in_per_req': g.input_tokens.mean(), 'cost_per_req': g.cost_usd.mean(), 'steps_per_req': g.steps.mean()}).reindex(range(60))` y rellena `requests` con 0 y `phase` con la regla de los 30 min."))
    code('''
def per_minute_metrics(runs: pd.DataFrame) -> pd.DataFrame:
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    PM = per_minute_metrics(INC["llm_outage"]["runs"]); display(PM.iloc[[0, 1, 29, 30, 45, 59]].round(3))
except NotImplementedError as e:
    PM = None; print("Pendiente:", e)
''')

    md("""
    ## Paso 2 · Características por fase (métricas + logs + trazas)

    Para decidir si una señal «salta», compara la fase **B** (incidente) con la **A** (base). Calcularás 9 características. Las de métricas y logs son agregaciones; la de trazas requiere **mirar dentro de los árboles de spans**.

    | Característica | Señal | Definición (B frente a A) |
    |---|---|---|
    | `err_delta` | métricas | `error_rate`(B) − `error_rate`(A) sobre `runs` (error = `error` o `max_steps`) |
    | `p95_ratio` | métricas | p95 de `latency_s`(B) / p95(A) |
    | `tokens_ratio` | métricas | media de `input_tokens`(B) / media(A) |
    | `cost_ratio` | métricas | media de `cost_usd`(B) / media(A) |
    | `steps_ratio` | métricas | media de `steps`(B) / media(A) |
    | `traffic_ratio` | métricas | nº de tickets(B) / nº de tickets(A) |
    | `warn_per_req_delta` | logs | (logs con `severity_number` ≥ 13 por ticket)(B) − (A). Para atribuir un log a una fase, une `logs.trace_id` con la traza del ticket |
    | `child_err_delta` | trazas | fracción de trazas con **algún span hijo en ERROR**(B) − (A) |
    | `repeat_share_delta` | trazas | fracción de trazas con **≥ 3 spans `execute_tool` con el mismo nombre**(B) − (A) |

    Además necesitas `slow_share` (fracción de trazas de B «anómalas»: con un hijo en ERROR **o** duración de la raíz > 2 × p95 de A) y `purity` (de las anómalas, fracción cuyo `culprit_name` es el más frecuente).

    **TODO 2.** `culprit_name(trace_spans)`: dado el `DataFrame` de los spans de **una** traza, devuelve el `name` del span **hijo** responsable: el hijo en ERROR de **mayor duración** si hay alguno; si no, el hijo de mayor duración. (Si no hay hijos, `None`.)
    """)
    md(hint(1, "Filtra los hijos con `trace_spans[trace_spans.parent_span_id.notna()]`. Si hay `status == 'ERROR'`, quédate con esos; ordena por `dur` y toma el último (`.iloc[-1]['name']`)."))
    code('''
def culprit_name(trace_spans: pd.DataFrame):
    # TODO 2
    raise NotImplementedError("TODO 2")

try:
    d = INC["tool_timeout"]; tr = d["spans"][d["spans"].trace_id == d["spans"][d["spans"].status == "ERROR"].trace_id.iloc[0]]
    print(culprit_name(tr))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    **TODO 3.** `phase_features(inc)` devuelve un `dict` con las 9 características + `slow_share`, `purity` y `culprit` (el nombre más frecuente, o `None`). Te damos como ayuda el mapa `trace → fase` y los tiempos de A.
    """)
    md(hint(1, "Mapas útiles: `t2p` (trace_id → fase) se obtiene uniendo los spans raíz con `runs` por el atributo `supportops.ticket.id`. Para logs: `logs['phase'] = logs.trace_id.map(t2p)`."))
    md(hint(2, "Por traza: `has_err_child = ((g.status == 'ERROR') & g.parent_span_id.notna()).any()`; `repeat = (g[g.name.str.startswith('execute_tool')].name.value_counts() >= 3).any()`; duración de la raíz = `g[g.parent_span_id.isna()].dur.iloc[0]`. Agrupa con `spans.groupby('trace_id')`."))
    code('''
def phase_features(inc: dict) -> dict:
    # TODO 3
    raise NotImplementedError("TODO 3")

try:
    FEATS = {n: phase_features(d) for n, d in INC.items()}
    display(pd.DataFrame(FEATS).T.round(2))
except NotImplementedError as e:
    FEATS = None; print("Pendiente:", e)
''')

    md("""
    ## Paso 3 · ¿Qué señal salta?

    **TODO 4.** `fires(f)` devuelve el conjunto de señales que **saltan**: `"M"` (métricas), `"L"` (logs), `"T"` (trazas). Reglas del equipo (las mismas en la solución):

    - **M** si: `err_delta ≥ 0,10` **o** `p95_ratio ≥ 2` **o** `steps_ratio ≥ 1,4` **o** `steps_ratio ≤ 0,75` **o** `cost_ratio ≥ 2` **o** `traffic_ratio ≥ 2` **o** `tokens_ratio ≥ 1,5` **o** `tokens_ratio ≤ 0,6`.
    - **L** si `warn_per_req_delta ≥ 0,15`.
    - **T** si `child_err_delta ≥ 0,10` **o** `repeat_share_delta ≥ 0,10` **o** (`slow_share ≥ 0,25` **y** `purity ≥ 0,7`).

    *(Reflexiona: ¿por qué las reglas de M incluyen umbrales «≤»? ¿Qué incidente los necesita?)*
    """)
    code('''
def fires(f: dict) -> set:
    # TODO 4
    raise NotImplementedError("TODO 4")

try:
    FIRED = {n: fires(f) for n, f in FEATS.items()}
    display(pd.DataFrame({n: {"M": "M" in s, "L": "L" in s, "T": "T" in s} for n, s in FIRED.items()}).T.replace({True: "✔", False: "·"}))
except (NotImplementedError, TypeError, AttributeError) as e:
    FIRED = None; print("Pendiente:", type(e).__name__)
''')

    md("""
    ## Paso 4 · Diagnóstico

    **TODO 5.** `diagnose(f, fired)` devuelve **una** etiqueta de entre
    `llm_outage, llm_slow, tool_errors, tool_timeout, retry_storm, tool_loop, hallucination, cost_drift, traffic_spike, sin_senal`.
    Usa las características (y `f["culprit"]`, que dice si el responsable es un span `chat…` o `execute_tool…`). `sin_senal` significa «ninguna señal salta: no hay nada que diagnosticar con los tres pilares».
    Piensa el **orden** de las reglas: de lo más específico (tráfico, coste) a lo más general.
    """)
    md(hint(1, "Un posible árbol: (1) `traffic_ratio ≥ 2` → `traffic_spike`; (2) `cost_ratio ≥ 2` y `tokens_ratio < 1.5` y `steps_ratio` cercano a 1 → `cost_drift`; (3) nada salta (`fired` vacío) → `sin_senal`; (4) `repeat_share_delta ≥ 0.1` (o pasos y tokens muy altos) → `tool_loop`; (5) errores en el span `chat` con `err_delta ≥ 0.1` → `llm_outage`…"))
    md(hint(2, "Continuación: (6) hijos en ERROR y `err_delta < 0.1` (la raíz sale «ok»): si el culpable empieza por `chat` → `retry_storm`; si por `execute_tool` → `tool_errors`, salvo que además `p95_ratio ≥ 2` → `tool_timeout`; (7) `p95_ratio ≥ 2` con culpable `chat` → `llm_slow`; (8) solo M por `steps_ratio ≤ 0.75` → `hallucination`."))
    code('''
LABELS = ["llm_outage", "llm_slow", "tool_errors", "tool_timeout", "retry_storm", "tool_loop", "hallucination", "cost_drift", "traffic_spike", "sin_senal"]

def diagnose(f: dict, fired: set) -> str:
    # TODO 5
    raise NotImplementedError("TODO 5")

try:
    DIAG = {n: diagnose(FEATS[n], FIRED[n]) for n in INC}
    display(pd.DataFrame({"diagnóstico": DIAG, "esperado": {n: n if n != "pii_leak" else "sin_senal" for n in INC}}))
except (NotImplementedError, TypeError) as e:
    DIAG = None; print("Pendiente:", type(e).__name__)
''')

    md("""
    ## Paso 5 · Informe final y puntos ciegos

    **TODO 6.** Rellena `REPORT`: para cada incidente, un `dict` con `fired` (el conjunto), `blind` (las señales de {M, L, T} que **no** saltan), `first_alert` (la señal con la que **alertarías** primero: prioriza M si salta —las métricas son baratas y rápidas—, si no L, si no T, si no `None`) y `evidence` (una frase con **al menos un número** de tus características que respalde el diagnóstico).
    Después contesta en `BLIND_SPOTS` dos listas: los incidentes donde **ninguna** señal salta y los incidentes que **la métrica no ve** pero sí logs o trazas.
    """)
    code('''
REPORT = {}
BLIND_SPOTS = {"ninguna_senal": [], "invisibles_para_metricas": []}

def build_report():
    # TODO 6: rellena REPORT[nombre] = {"fired": set, "blind": set, "first_alert": "M"|"L"|"T"|None, "evidence": str} y BLIND_SPOTS
    raise NotImplementedError("TODO 6")

try:
    build_report()
    display(pd.DataFrame(REPORT).T[["fired", "blind", "first_alert"]]); print(BLIND_SPOTS)
except (NotImplementedError, TypeError, KeyError) as e:
    print("Pendiente:", type(e).__name__)
''')

    md("""
    ## Paso 6 · Rúbrica
    """)
    code('''
# Valores de verdad (calibrados con la solución de referencia sobre varias semillas). Van codificados en base64 SOLO para no
# estropearte el ejercicio: no los decodifiques antes de intentarlo (la rúbrica los usa por ti).
import base64
_T = json.loads(base64.b64decode("eyJmaXJlZCI6eyJsbG1fb3V0YWdlIjoiTUxUIiwibGxtX3Nsb3ciOiJNVCIsInRvb2xfZXJyb3JzIjoiTFQiLCJ0b29sX3RpbWVvdXQiOiJNTFQiLCJyZXRyeV9zdG9ybSI6IkxUIiwidG9vbF9sb29wIjoiTUxUIiwiaGFsbHVjaW5hdGlvbiI6Ik0iLCJwaWlfbGVhayI6IiIsImNvc3RfZHJpZnQiOiJNIiwidHJhZmZpY19zcGlrZSI6Ik0ifSwiYmxpbmQiOnsibmluZ3VuYV9zZW5hbCI6WyJwaWlfbGVhayJdLCJpbnZpc2libGVzX3BhcmFfbWV0cmljYXMiOlsicmV0cnlfc3Rvcm0iLCJ0b29sX2Vycm9ycyJdfSwicmVmIjp7ImxsbV9vdXRhZ2UiOnsiZXJyX2RlbHRhIjowLjU2LCJwOTVfcmF0aW8iOjAuOTEzOCwidG9rZW5zX3JhdGlvIjowLjQ0NjQsImNvc3RfcmF0aW8iOjAuNDUxOSwic3RlcHNfcmF0aW8iOjAuODAyNSwidHJhZmZpY19yYXRpbyI6MS4wLCJ3YXJuX3Blcl9yZXFfZGVsdGEiOjEuNjgsImNoaWxkX2Vycl9kZWx0YSI6MC41NiwicmVwZWF0X3NoYXJlX2RlbHRhIjowLjB9LCJ0b29sX2Vycm9ycyI6eyJlcnJfZGVsdGEiOjAuMCwicDk1X3JhdGlvIjowLjg0NTIsInRva2Vuc19yYXRpbyI6MC45MDAxLCJjb3N0X3JhdGlvIjowLjg4OSwic3RlcHNfcmF0aW8iOjAuOTQyNywidHJhZmZpY19yYXRpbyI6MS4wLCJ3YXJuX3Blcl9yZXFfZGVsdGEiOjAuOTIsImNoaWxkX2Vycl9kZWx0YSI6MC40OCwicmVwZWF0X3NoYXJlX2RlbHRhIjowLjB9LCJ0b29sX2xvb3AiOnsiZXJyX2RlbHRhIjowLjQxLCJwOTVfcmF0aW8iOjIuNzQzNSwidG9rZW5zX3JhdGlvIjoyLjQ1MDMsImNvc3RfcmF0aW8iOjIuMzAzLCJzdGVwc19yYXRpbyI6Mi4xMTc4LCJ0cmFmZmljX3JhdGlvIjoxLjAsIndhcm5fcGVyX3JlcV9kZWx0YSI6MC40MSwiY2hpbGRfZXJyX2RlbHRhIjowLjAsInJlcGVhdF9zaGFyZV9kZWx0YSI6MC40MX19fQ=="))
TRUTH_FIRED, REF_FEATS = _T["fired"], _T["ref"]
TRUTH_DIAG = {n: n for n in INC} | {"pii_leak": "sin_senal"}

def run_rubric():
    rows = []
    def add(r, d, ok, det=""): rows.append({"criterio": r, "descripción": d, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": det})
    # R1
    try:
        pm = per_minute_metrics(INC["llm_outage"]["runs"]); b = pm[pm.phase == "B"]
        ref = INC["llm_outage"]["runs"].query("phase == 'B'").status.isin(["error", "max_steps"]).mean()
        ok = len(pm) == 60 and int(pm.requests.sum()) == 200 and abs(b.error_rate.mean() - ref) < 0.05
        add("R1", "per_minute_metrics (60 filas, 200 peticiones, tasa de error coherente)", ok, f"filas={len(pm)} peticiones={int(pm.requests.sum())} err(B)≈{b.error_rate.mean():.2f} vs {ref:.2f}")
    except Exception as e: add("R1", "per_minute_metrics", False, type(e).__name__)
    # R2
    try:
        hits = tot = 0
        for n in ("llm_slow", "tool_timeout", "retry_storm"):
            sp = INC[n]["spans"]; B = set(INC[n]["runs"].query("phase == 'B'").ticket_id)
            roots = sp[sp.parent_span_id.isna()]; tb = set(roots[roots.attributes.map(lambda a: a["supportops.ticket.id"]).isin(B)].trace_id)
            for t, g in sp[sp.trace_id.isin(tb)].groupby("trace_id"):
                ch = g[g.parent_span_id.notna()]; ref_ch = ch[ch.status == "ERROR"] if (ch.status == "ERROR").any() else ch
                if len(ch) == 0: continue
                tot += 1; hits += culprit_name(g) == ref_ch.sort_values("dur").iloc[-1]["name"]
        add("R2", "culprit_name coincide con la referencia (≥ 90 %)", tot > 0 and hits / tot >= 0.9, f"{hits}/{tot}")
    except Exception as e: add("R2", "culprit_name", False, type(e).__name__)
    # R3
    try:
        ref_cols = ["err_delta", "p95_ratio", "tokens_ratio", "cost_ratio", "steps_ratio", "traffic_ratio", "warn_per_req_delta", "child_err_delta", "repeat_share_delta"]
        good = 0
        for n in ("llm_outage", "tool_errors", "tool_loop"):
            f, g = phase_features(INC[n]), REF_FEATS[n]
            good += all(abs(f[c] - g[c]) <= 0.02 * max(abs(g[c]), 1e-9) + 1e-6 for c in ref_cols)
        add("R3", "phase_features coincide con la referencia (3 incidentes)", good == 3, f"{good}/3")
    except Exception as e: add("R3", "phase_features", False, type(e).__name__)
    # R4
    try:
        n_ok = sum(set(TRUTH_FIRED[n]) == fires(FEATS[n]) for n in INC)
        add("R4", "fires: señales correctas en ≥ 9/10", n_ok >= 9, f"{n_ok}/10")
    except Exception as e: add("R4", "fires", False, type(e).__name__)
    # R5
    try:
        n_ok = sum(diagnose(FEATS[n], fires(FEATS[n])) == TRUTH_DIAG[n] for n in INC)
        add("R5", "diagnose: etiqueta correcta en ≥ 8/10", n_ok >= 8, f"{n_ok}/10")
    except Exception as e: add("R5", "diagnose", False, type(e).__name__)
    # R6
    try:
        exp = _T["blind"]
        got = {k: sorted(v) for k, v in BLIND_SPOTS.items()}
        ev_ok = all(isinstance(REPORT[n]["evidence"], str) and re.search(r"\\d", REPORT[n]["evidence"]) for n in INC)
        add("R6", "puntos ciegos exactos + evidencias con números", got == {k: sorted(v) for k, v in exp.items()} and ev_ok, f"{got}")
    except Exception as e: add("R6", "puntos ciegos", False, type(e).__name__)
    return pd.DataFrame(rows).set_index("criterio")

''')
    code('''
# Ejecuta esta celda cuando hayas terminado los TODO
display(run_rubric())
''')

    md("""
    ---
    ## Retos extra (nivel experto)

    1. **Robustez:** repite el análisis con las semillas 7, 99 y 123 (`simulate(n, seed=...)`). ¿Qué reglas de `fires` están más cerca de sus umbrales? ¿Qué incidente es más frágil y por qué (pista: `cost_drift` en trazas)?
    2. **Tiempo hasta la detección:** en vez de comparar fases enteras, calcula con ventana deslizante de 3 min el **primer minuto** en que cada regla de M salta tras el inicio del incidente. ¿Qué incidentes detectan las métricas en < 3 min y cuáles tardan más? ¿Cómo cambia con 3× menos tráfico?
    3. **El «cuarto pilar»:** añade a `diagnose` una señal de **contenido** (por ejemplo, el regex de PII del proyecto 01 sobre `runs.answer`). ¿Cuántos incidentes pasan de `sin_senal` a diagnosticados? ¿A qué coste (falsos positivos, privacidad)?
    4. **Cardinalidad:** calcula cuántas series generaría un histograma por `customer_id` en estos incidentes (`runs.customer_id.nunique()`) y diseña una alternativa con trazas para atribuir latencia por cliente.
    5. **Alerta multi-señal:** propón una regla de alerta que combine `error_rate` y `p95` y estima su tasa de falsos positivos en las fases A de los 10 incidentes.

    ## Reflexión (producción e hilo conductor)

    - `tool_errors` y `retry_storm` son **invisibles para las métricas de la raíz**. ¿Qué métrica *adicional* (con qué etiquetas acotadas) las haría visibles sin disparar la cardinalidad?
    - `hallucination` solo se veía por una **caída** de pasos/tokens. ¿Qué pasaría si el agente alucinara *y además* hiciera llamadas innecesarias a herramientas (pasos iguales)? ¿Qué señal sobreviviría?
    - Tu `first_alert` favorece a M por ser barata. ¿En qué incidente esa preferencia te llevaría a una alerta **ruidosa o tardía** y qué señal mejoraría el *tiempo de diagnóstico*?
    - En el módulo 03 instrumentarás SupportOps con el SDK: ¿qué atributos pondrías para que `culprit_name` (y el análisis por herramienta/modelo) funcionase sin tocar el código de análisis?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable.
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
ERR = ["error", "max_steps"]

# TODO 1
def per_minute_metrics(runs: pd.DataFrame) -> pd.DataFrame:
    g = runs.groupby("minute")
    out = pd.DataFrame({"requests": g.size(), "error_rate": g.status.apply(lambda s: s.isin(ERR).mean()), "p95_latency_s": g.latency_s.quantile(.95),
                        "tokens_in_per_req": g.input_tokens.mean(), "cost_per_req": g.cost_usd.mean(), "steps_per_req": g.steps.mean()}).reindex(range(60))
    out["requests"] = out.requests.fillna(0).astype(int)
    out.insert(0, "phase", ["A" if m < 30 else "B" for m in range(60)])
    out.index.name = "minute"
    return out

# TODO 2
def culprit_name(trace_spans: pd.DataFrame):
    ch = trace_spans[trace_spans.parent_span_id.notna()]
    if len(ch) == 0: return None
    err = ch[ch.status == "ERROR"]
    return (err if len(err) else ch).sort_values("dur").iloc[-1]["name"]

# TODO 3
def phase_features(inc: dict) -> dict:
    runs, spans, logs = inc["runs"], inc["spans"], inc["logs"]
    A, B = runs[runs.phase == "A"], runs[runs.phase == "B"]
    f = {}
    err = lambda d: d.status.isin(ERR).mean()
    f["err_delta"] = err(B) - err(A)
    f["p95_ratio"] = B.latency_s.quantile(.95) / A.latency_s.quantile(.95)
    f["tokens_ratio"] = B.input_tokens.mean() / A.input_tokens.mean()
    f["cost_ratio"] = B.cost_usd.mean() / A.cost_usd.mean()
    f["steps_ratio"] = B.steps.mean() / A.steps.mean()
    f["traffic_ratio"] = len(B) / len(A)
    roots = spans[spans.parent_span_id.isna()].copy()
    roots["ticket"] = roots.attributes.map(lambda a: a["supportops.ticket.id"])
    t2p = dict(zip(roots.trace_id, roots.ticket.map(dict(zip(runs.ticket_id, runs.phase)))))
    w = logs[logs.severity_number >= 13].copy(); w["phase"] = w.trace_id.map(t2p)
    f["warn_per_req_delta"] = (w.phase == "B").sum() / len(B) - (w.phase == "A").sum() / len(A)
    by = {t: g for t, g in spans.groupby("trace_id")}
    has_err = lambda g: bool(((g.status == "ERROR") & g.parent_span_id.notna()).any())
    repeat = lambda g: bool((g[g.name.str.startswith("execute_tool")].name.value_counts() >= 3).any())
    ids = {p: [t for t, q in t2p.items() if q == p] for p in "AB"}
    share = lambda fn, p: float(np.mean([fn(by[t]) for t in ids[p]]))
    f["child_err_delta"] = share(has_err, "B") - share(has_err, "A")
    f["repeat_share_delta"] = share(repeat, "B") - share(repeat, "A")
    p95a = A.latency_s.quantile(.95)
    anom = [t for t in ids["B"] if has_err(by[t]) or by[t][by[t].parent_span_id.isna()].dur.iloc[0] > 2 * p95a]
    f["slow_share"] = len(anom) / max(1, len(ids["B"]))
    c = collections.Counter(culprit_name(by[t]) for t in anom)
    f["purity"] = c.most_common(1)[0][1] / len(anom) if anom else 0.0
    f["culprit"] = c.most_common(1)[0][0] if anom else None
    return f

# TODO 4
def fires(f: dict) -> set:
    s = set()
    if (f["err_delta"] >= .10 or f["p95_ratio"] >= 2 or f["steps_ratio"] >= 1.4 or f["steps_ratio"] <= .75 or f["cost_ratio"] >= 2
            or f["traffic_ratio"] >= 2 or f["tokens_ratio"] >= 1.5 or f["tokens_ratio"] <= .6): s.add("M")
    if f["warn_per_req_delta"] >= .15: s.add("L")
    if f["child_err_delta"] >= .10 or f["repeat_share_delta"] >= .10 or (f["slow_share"] >= .25 and f["purity"] >= .7): s.add("T")
    return s

# TODO 5
def diagnose(f: dict, fired: set) -> str:
    cul = (f.get("culprit") or "")
    if f["traffic_ratio"] >= 2: return "traffic_spike"
    if f["cost_ratio"] >= 2 and f["tokens_ratio"] < 1.5 and .8 <= f["steps_ratio"] <= 1.25: return "cost_drift"
    if not fired: return "sin_senal"
    if f["repeat_share_delta"] >= .10 or (f["steps_ratio"] >= 1.4 and f["tokens_ratio"] >= 1.5): return "tool_loop"
    if f["err_delta"] >= .10 and cul.startswith("chat"): return "llm_outage"
    if f["child_err_delta"] >= .10:                                  # la raíz sale «ok»: el fallo vive dentro
        if cul.startswith("chat"): return "retry_storm"
        return "tool_timeout" if f["p95_ratio"] >= 2 else "tool_errors"
    if f["p95_ratio"] >= 2 and cul.startswith("chat"): return "llm_slow"
    if f["steps_ratio"] <= .75: return "hallucination"
    return "sin_senal"

# TODO 6
def build_report():
    for n in INC:
        f, s = FEATS[n], FIRED[n]
        REPORT[n] = {"fired": s, "blind": set("MLT") - s, "first_alert": next((x for x in "MLT" if x in s), None),
                     "evidence": f"err_delta={f['err_delta']:.2f}, p95×{f['p95_ratio']:.1f}, pasos×{f['steps_ratio']:.2f}, tokens×{f['tokens_ratio']:.2f}, coste×{f['cost_ratio']:.1f}, tráfico×{f['traffic_ratio']:.1f}"}
    BLIND_SPOTS["ninguna_senal"] = [n for n in INC if not FIRED[n]]
    BLIND_SPOTS["invisibles_para_metricas"] = [n for n in INC if "M" not in FIRED[n] and FIRED[n]]

FEATS = {n: phase_features(d) for n, d in INC.items()}
FIRED = {n: fires(f) for n, f in FEATS.items()}
DIAG = {n: diagnose(FEATS[n], FIRED[n]) for n in INC}
build_report()
display(pd.DataFrame(FEATS).T.round(2))
display(pd.DataFrame({"fired": {n: "".join(sorted(s, key="MLT".index)) or "—" for n, s in FIRED.items()}, "diagnóstico": DIAG, "primera alerta": {n: REPORT[n]["first_alert"] for n in INC}}))
print(BLIND_SPOTS)
display(run_rubric())
''')

    code('''
# Visualización de la solución: ¿qué señal salta en cada incidente? (matriz) + series por minuto de tres incidentes representativos
fig, axes = plt.subplots(1, 2, figsize=(15, 4.2), gridspec_kw={"width_ratios": [1, 1.5]})
mat = np.array([[("M" in FIRED[n]), ("L" in FIRED[n]), ("T" in FIRED[n])] for n in INC], dtype=int)
axes[0].imshow(mat, cmap="Greens", vmin=0, vmax=1.4, aspect="auto"); axes[0].set_xticks(range(3)); axes[0].set_xticklabels(["métricas", "logs", "trazas"]); axes[0].set_yticks(range(len(INC))); axes[0].set_yticklabels(list(INC))
for i in range(mat.shape[0]):
    for j in range(3): axes[0].text(j, i, "✔" if mat[i, j] else "·", ha="center", va="center", fontsize=12)
axes[0].set_title("¿Qué señal salta? (medido)"); axes[0].grid(False)
for n, c in [("tool_errors", viz.PALETTE["warn"]), ("llm_slow", viz.PALETTE["error"]), ("traffic_spike", viz.PALETTE["traces"])]:
    pm = per_minute_metrics(INC[n]["runs"]); axes[1].plot(pm.index, pm.requests.rolling(3, min_periods=1).mean() / pm.requests[:30].mean(), color=c, ls=":", lw=1.2)
    axes[1].plot(pm.index, (pm.p95_latency_s / pm.p95_latency_s[:30].mean()).rolling(3, min_periods=1).mean(), color=c, lw=2, label=f"{n}: p95 relativo (—) / tráfico (···)")
axes[1].axvline(30, color="k", ls="--"); axes[1].set_xlabel("minuto"); axes[1].set_ylabel("relativo a la media de la fase A"); axes[1].legend(fontsize=8); axes[1].set_title("Lo que ve un dashboard de RED en tres incidentes (inicio del incidente: línea discontinua)")
plt.tight_layout(); plt.show()
''')
    nb.save(out)


README = """# Módulo 02 · Los tres pilares: traces, metrics y logs

🟢 Básico · ≈ 4 h 30 min · **No necesita servicios de Compose** (datos simulados y pregrabados; funciona en Colab).

## Qué aprenderás
- Qué pregunta responde cada señal (logs: *qué pasó*, métricas: *cuánto*, trazas: *dónde y por qué*) y por qué un agente necesita las tres; analogías con ML, microservicios y SRE.
- Contador, *gauge* e **histograma construidos a mano** (con salida en formato Prometheus) y el error al estimar percentiles desde *buckets*.
- El **modelo de datos de OpenTelemetry**: resource, instrumentation scope, span (kind, status, atributos, eventos, links), log record, temporalidad de métricas; **propagación de contexto** con W3C `traceparent` (implementada a mano) y qué pasa cuando se rompe.
- **Correlación**: métrica → exemplar → traza → logs.
- *Golden signals* (y RED/USE) aplicadas a agentes: latencia, tráfico, errores, saturación **más** tokens/coste, pasos y calidad.
- Percentiles que no se promedian, **cardinalidad** de métricas y la hipótesis de «qué señal detecta qué fallo».

## Archivos
| Archivo | Contenido |
|---|---|
| `02_tres_pilares.ipynb` | Lección (teoría + código + 11 gráficos + autoevaluación) |
| `02_proyecto_tres_pilares.ipynb` | Proyecto: mide y clasifica **10 incidentes** de SupportOps (qué señal salta, qué señal es ciega, diagnóstico) |

## Servicios necesarios
Ninguno.

## Lecturas
- OpenTelemetry, especificación (modelos de datos de trazas, métricas y logs) — <https://github.com/open-telemetry/opentelemetry-specification>
- W3C, *Trace Context* — <https://www.w3.org/TR/trace-context/>
- Google SRE book, cap. 6 *Monitoring Distributed Systems* — <https://sre.google/sre-book/monitoring-distributed-systems/>
- Sigelman et al., *Dapper* (2010) — <https://research.google/pubs/pub36356/>

## Siguiente
`03_otel_sdk_python`: producirás estas señales con el SDK de OpenTelemetry (TracerProvider, spans, contexto y exportador OTLP).
"""

if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    (COURSE / MOD / "README.md").write_text(README, encoding="utf-8")
    build_lesson()
    build_project()
