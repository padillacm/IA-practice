"""Genera el módulo 04_genai_semconv: README, lección y proyecto.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_04.py

Si defines GENAI_SPEC_DIR=<clon de github.com/open-telemetry/semantic-conventions-genai>, regenera además la instantánea
`04_genai_semconv/genai_semconv_snapshot.json` (registro de atributos, spans y métricas) que usan lección y proyecto.
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "04_genai_semconv"
SNAPSHOT = COURSE / MOD / "genai_semconv_snapshot.json"


# ---------------------------------------------------------------------------------------------------------------------
# Instantánea de la spec (se regenera solo si se indica GENAI_SPEC_DIR)
# ---------------------------------------------------------------------------------------------------------------------
def _level(rl):
    if rl is None:
        return ("recommended", "")
    if isinstance(rl, str):
        return (rl, "")
    (k, v), = rl.items()
    return (k, v or "")


def make_snapshot(spec_dir: str) -> dict:
    import yaml
    spec = pathlib.Path(spec_dir)
    reg = yaml.safe_load((spec / "model/gen-ai/registry.yaml").read_text())
    attrs = {}
    for a in reg["attributes"]:
        t, enum = a.get("type"), None
        if isinstance(t, dict):
            enum, t = [m["value"] for m in t["members"]], "enum"
        attrs[a["key"]] = {"type": t, "stability": a.get("stability", "development"), "enum": enum,
                           "brief": " ".join((a.get("brief") or "").split())[:160]}
    sp = yaml.safe_load((spec / "model/gen-ai/spans.yaml").read_text())
    groups = {g["id"]: g for g in sp.get("attribute_groups", [])}

    def expand(items, out):
        for it in items:
            if "ref_group" in it:
                expand(groups[it["ref_group"]]["attributes"], out)
            else:
                lvl, cond = _level(it.get("requirement_level"))
                prev = out.get(it["ref"], {})
                out[it["ref"]] = {"level": lvl if "requirement_level" in it or not prev else prev["level"], "condition": cond or prev.get("condition", ""),
                                  "sampling_relevant": bool(it.get("sampling_relevant", prev.get("sampling_relevant", False)))}
    spans = {}
    for s in sp["spans"]:
        out: dict = {}
        expand(s.get("attributes", []), out)
        spans[s["type"]] = {"kind": s["kind"], "name_note": " ".join((s.get("name", {}).get("note") or "").split())[:200],
                            "stability": s.get("stability"), "attributes": out}
    mt = {}
    for f in ("metrics.yaml", "token-metrics.yaml"):
        for x in yaml.safe_load((spec / "model/gen-ai" / f).read_text())["metrics"]:
            mt[x["name"]] = {"instrument": x["instrument"], "unit": x["unit"], "stability": x.get("stability")}
    commit = subprocess.run(["git", "-C", str(spec), "log", "-1", "--format=%H %cs"], capture_output=True, text=True).stdout.split()
    fr = json.loads((spec / "model/gen-ai/gen-ai-output-messages.json").read_text())["$defs"]["FinishReason"]["enum"]
    return {"source": {"repo": "https://github.com/open-telemetry/semantic-conventions-genai", "commit": commit[0], "date": commit[1], "status": "development"},
            "attributes": attrs, "spans": spans, "metrics": mt, "finish_reason_enum": fr}


def ensure_snapshot() -> dict:
    if os.environ.get("GENAI_SPEC_DIR"):
        SNAPSHOT.parent.mkdir(exist_ok=True)
        SNAPSHOT.write_text(json.dumps(make_snapshot(os.environ["GENAI_SPEC_DIR"]), indent=1, ensure_ascii=False), encoding="utf-8")
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------------------------------------------------
# Código compartido por lección y proyecto (se inserta en celdas)
# ---------------------------------------------------------------------------------------------------------------------
OTEL_IMPORTS = '''
import copy, json, re, time, logging, collections, hashlib
from opentelemetry.sdk.trace import TracerProvider
from supportops.telemetry import setup_telemetry, OTelInstrumentor
'''

SPEC_LOADER = '''
SNAP = ROOT / "04_genai_semconv" / "genai_semconv_snapshot.json"          # instantánea de la spec oficial (ver README del módulo)
SPEC = json.loads(SNAP.read_text(encoding="utf-8"))
REG, SPANS = SPEC["attributes"], SPEC["spans"]
print("Spec:", SPEC["source"]["repo"].split("github.com/")[1], "· commit", SPEC["source"]["commit"][:8], "·", SPEC["source"]["date"], "· estado:", SPEC["source"]["status"])
print(f"{len(REG)} atributos gen_ai.* · {len(SPANS)} tipos de span · {len(SPEC['metrics'])} métricas · estabilidad de los atributos: {collections.Counter(a['stability'] for a in REG.values())}")
'''

# --- Constantes y utilidades del linter (compartidas) -----------------------------------------------------------------
LINT_CONSTANTS = '''
CONTENT_ATTRS = {"gen_ai.system_instructions", "gen_ai.input.messages", "gen_ai.output.messages", "gen_ai.tool.definitions", "gen_ai.tool.call.arguments",
                 "gen_ai.tool.call.result", "gen_ai.retrieval.documents", "gen_ai.retrieval.query.text", "gen_ai.memory.records", "gen_ai.memory.query.text"}
RENAMES = {"gen_ai.system": "gen_ai.provider.name", "gen_ai.usage.prompt_tokens": "gen_ai.usage.input_tokens", "gen_ai.usage.completion_tokens": "gen_ai.usage.output_tokens",
           "gen_ai.usage.cache_creation.input_tokens": "gen_ai.usage.cache_write.input_tokens", "gen_ai.prompt": "gen_ai.input.messages (aprox.)", "gen_ai.completion": "gen_ai.output.messages (aprox.)"}
SEVERITY = {"REQ": "error", "UNK": "error", "TYPE": "error", "TOK": "error", "ERR": "error",
            "SCOPE": "warn", "ENUM": "warn", "NAME": "warn", "KIND": "warn", "FINISH": "warn", "CARD": "warn", "CONV": "warn", "PRIV": "info"}
TYPES = {"string": str, "enum": str, "int": int, "double": (int, float), "boolean": bool}
OP_TO_SPAN = {"chat": "gen_ai.client.inference", "generate_content": "gen_ai.client.inference", "text_completion": "gen_ai.client.inference", "embeddings": "gen_ai.embeddings.client",
              "retrieval": "gen_ai.retrieval.client", "create_agent": "gen_ai.create_agent.client", "execute_tool": "gen_ai.execute_tool.internal",
              "invoke_workflow": "gen_ai.invoke_workflow.internal", "plan": "gen_ai.plan.internal"}
NAME_PART = {"chat": "gen_ai.request.model", "generate_content": "gen_ai.request.model", "text_completion": "gen_ai.request.model", "embeddings": "gen_ai.request.model",
             "execute_tool": "gen_ai.tool.name", "invoke_agent": "gen_ai.agent.name", "create_agent": "gen_ai.agent.name", "plan": "gen_ai.agent.name", "retrieval": "gen_ai.data_source.id"}
HIGH_CARD = re.compile(r"(ORD-\\d+|\\bT-\\d{3,}|\\bC-\\d{3,}|[0-9a-f]{8}-[0-9a-f]{4}-|\\b\\d{5,}\\b)")      # ids que no deben ir en un nombre de span

def span_type(rec, local_agent=True):
    """Tipo de span de la spec (clave de SPANS) a partir de gen_ai.operation.name (o, si falta, de la primera palabra del nombre)."""
    op = rec["attributes"].get("gen_ai.operation.name") or rec["name"].split(" ")[0]
    if op == "invoke_agent":
        return "gen_ai.invoke_agent.internal" if (local_agent or rec["kind"] != "CLIENT") else "gen_ai.invoke_agent.client"
    return OP_TO_SPAN.get(op)

def type_ok(v, t):
    if t in (None, "any") or t.startswith("template"): return True
    if t.endswith("[]"): return isinstance(v, (list, tuple)) and all(isinstance(x, str) for x in v)
    if t in ("int", "double") and isinstance(v, bool): return False
    return isinstance(v, TYPES[t])
'''

LEGACY_SRC = '''
def _h(rec, mod): return int(rec["span_id"][:8], 16) % mod            # «azar» determinista por span

def make_legacy(rec):
    """Simula la instrumentación «de la antigua usanza» de otro equipo. Devuelve (span_modificado, defectos_plantados: set de códigos de regla)."""
    r = copy.deepcopy(rec); a = r["attributes"]; planted = set(); op = a.get("gen_ai.operation.name")
    if op == "chat":
        if "gen_ai.provider.name" in a:
            a["gen_ai.system"] = a.pop("gen_ai.provider.name"); planted |= {"UNK", "REQ"}                 # nombre antiguo del proveedor
        if "gen_ai.usage.input_tokens" in a:
            a["gen_ai.usage.prompt_tokens"] = a.pop("gen_ai.usage.input_tokens"); a["gen_ai.usage.completion_tokens"] = a.pop("gen_ai.usage.output_tokens"); planted.add("UNK")
        if a.get("gen_ai.response.finish_reasons") == ["tool_call"]:
            a["gen_ai.response.finish_reasons"] = ["tool_calls"]; planted.add("FINISH")                  # valor «nativo» sin normalizar
        if _h(r, 6) == 0:
            a["gen_ai.input.messages"] = json.dumps([{"role": "user", "parts": [{"type": "text", "content": "Hola, soy un cliente"}]}]); planted.add("PRIV")
    elif op == "execute_tool":
        if _h(r, 3) == 0:
            a["tool"] = a.pop("gen_ai.tool.name"); planted.add("REQ")                                    # atributo propio en lugar del estándar
        elif _h(r, 5) == 0:
            r["name"] += " ORD-00017"; planted |= {"CARD", "NAME"}                                       # id dentro del nombre del span
    elif op == "invoke_agent":
        if _h(r, 2) == 0:
            r["kind"] = "CLIENT"; planted.add("KIND")                                                    # agente local marcado como remoto
        if _h(r, 4) == 0 and "gen_ai.usage.input_tokens" in a:
            a["gen_ai.usage.input_tokens"] = str(a["gen_ai.usage.input_tokens"]); planted.add("TYPE")    # número como cadena
        elif _h(r, 7) == 0 and "gen_ai.usage.input_tokens" in a:
            a["gen_ai.usage.cache_read.input_tokens"] = a["gen_ai.usage.input_tokens"] + 50; planted.add("TOK")   # subconjunto mayor que el total
        if _h(r, 3) == 0:
            a["gen_ai.conversation.id"] = r["trace_id"]; planted.add("CONV")                             # conversación inventada con el trace_id
    if r["status"] == "ERROR" and _h(r, 2) == 0 and "error.type" in a:
        a.pop("error.type"); planted.add("ERR")                                                          # error sin clasificar
    return r, planted
'''

# El linter completo de la lección (se muestra por partes y aquí queda como una sola cadena para el proyecto/solución)
LINT_FULL = '''
def lint_span(rec, local_agent=True):
    """Hallazgos [{rule, severity, attr, msg}] de un span (dict con el esquema SPAN_SCHEMA) frente a la spec."""
    F, a, st = [], rec["attributes"], span_type(rec, local_agent)
    def add(rule, attr, msg): F.append({"rule": rule, "severity": SEVERITY[rule], "attr": attr, "msg": msg})
    defined = SPANS[st]["attributes"] if st else {}
    for k, v in a.items():                                                               # 1) atributos: existencia, tipo, valores, ámbito
        if k.startswith("gen_ai.") and k not in REG and not k.startswith("gen_ai.prompt.variable."):
            add("UNK", k, "no existe en el registro actual" + (f"; usa {RENAMES[k]}" if k in RENAMES else ""))
        elif k in REG:
            if not type_ok(v, REG[k]["type"]): add("TYPE", k, f"esperaba {REG[k]['type']}, llegó {type(v).__name__}")
            elif REG[k]["enum"] and v not in REG[k]["enum"] and k != "gen_ai.provider.name": add("ENUM", k, f"valor fuera de los conocidos: {v!r}")
            if st and k not in defined: add("SCOPE", k, f"no está definido para {st}")
    if st:                                                                               # 2) requeridos
        for k, d in defined.items():
            if d["level"] == "required" and k not in a: add("REQ", k, f"requerido en {st}")
    if rec["status"] == "ERROR" and "error.type" not in a: add("ERR", "error.type", "span en ERROR sin error.type")
    op = a.get("gen_ai.operation.name")                                                  # 3) nombre y kind
    if st and op in NAME_PART:
        part = a.get(NAME_PART[op])
        if part is not None or op == "invoke_agent":
            expected = op + (f" {part}" if part else "")
            if rec["name"] != expected: add("NAME", "name", f"esperado «{expected}», hay «{rec['name']}»")
    if st:
        exp_kind = SPANS[st]["kind"].upper()
        if rec["kind"] != exp_kind and not (st == "gen_ai.client.inference" and rec["kind"] == "INTERNAL"):
            add("KIND", "kind", f"{st} debería ser {exp_kind}")
    if HIGH_CARD.search(rec["name"]): add("CARD", "name", "el nombre del span contiene un identificador")
    for x in (a.get("gen_ai.response.finish_reasons") if isinstance(a.get("gen_ai.response.finish_reasons"), (list, tuple)) else []):   # 4) valores
        if x not in SPEC["finish_reason_enum"]: add("FINISH", "gen_ai.response.finish_reasons", f"{x!r} no está en {SPEC['finish_reason_enum']}")
    i = a.get("gen_ai.usage.input_tokens")
    if isinstance(i, int) and not isinstance(i, bool):
        for sub in ("gen_ai.usage.cache_read.input_tokens", "gen_ai.usage.cache_write.input_tokens"):
            if isinstance(a.get(sub), int) and a[sub] > i: add("TOK", sub, f"{sub}={a[sub]} > input_tokens={i} (debe ser un subconjunto)")
    if a.get("gen_ai.conversation.id") == rec["trace_id"]: add("CONV", "gen_ai.conversation.id", "es el trace_id: la spec desaconseja (SHOULD NOT) inventar la conversación")
    for k in CONTENT_ATTRS & set(a): add("PRIV", k, f"contenido capturado ({len(str(a[k]))} car.)")
    return F

def lint(spans, **kw):
    rows = [{"span_id": s["span_id"], "name": s["name"], **f} for s in spans for f in lint_span(s, **kw)]
    return pd.DataFrame(rows, columns=["span_id", "name", "rule", "severity", "attr", "msg"])
'''


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "04_genai_semconv.ipynb", "Módulo 04 · GenAI semantic conventions")
    md, code = nb.md, nb.code
    snap_date = ensure_snapshot()["source"]["date"]

    md(f"""
    {nb.badge()}

    # Módulo 04 · GenAI semantic conventions: el vocabulario común de la telemetría de agentes

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | **Ninguno** (todo en memoria; funciona en Colab). Opcional: `--profile core` si quieres enviar al Collector |
    | **RAM aproximada** | < 0,5 GB (solo el kernel de Python) |
    | **Prerrequisitos** | Módulo 03 (spans, `SpanKind`, atributos «al crear», `setup_telemetry`/`OTelInstrumentor`) |
    | **Hilo conductor** | Los spans de SupportOps v1 existen, pero **tú inventaste sus nombres**. Aquí los alineamos con el estándar y construyes un **linter** que lo vigila |

    > ⚠️ **Estado de la especificación (verificado el {snap_date}).** Las GenAI semantic conventions siguen en estado **Development** (inestable): nombres, atributos y hasta el repositorio han cambiado en el último año.
    > Todo lo que aparece aquí se contrasta con la spec oficial (instantánea incluida en el módulo) y se marca lo que puede volver a cambiar. La lección te enseña **a detectar el cambio**, no solo los nombres de hoy.
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** por qué existen las semantic conventions y **localizar** la spec oficial vigente (repositorio, estado, qué es estable y qué es experimental).
    2. **Modelar** un agente con las operaciones `invoke_agent`, `chat`, `execute_tool` (y reconocer `create_agent`, `plan`, `invoke_workflow`…): *kind*, nombre y atributos exigidos por la spec.
    3. **Distinguir** los niveles de requisito (*Required*, *Conditionally Required*, *Recommended*, *Opt-In*) y **aplicarlos** a un span real.
    4. **Calcular** correctamente los atributos de tokens (entrada total, caché de lectura/escritura, razonamiento) para distintos proveedores y **evitar** el doble conteo.
    5. **Construir un linter** de atributos que compruebe existencia, tipos, requeridos, nombres, *kinds*, valores y privacidad, y **contrastarlo** con la implementación oficial.
    6. **Detectar y migrar** nombres deprecados (`gen_ai.system` → `gen_ai.provider.name`, `prompt_tokens` → `input_tokens`…).
    7. **Decidir** una política de captura de contenido (prompts/respuestas) y **medir** su coste de privacidad y de almacenamiento.
    8. **Gestionar** el riesgo de una spec inestable: versionado, mapa de renombres y doble emisión.
    """)

    md("""
    ## 🔁 Conexión con módulos anteriores
    """)
    md(details("1 · (Módulo 03) ¿Qué atributos deben pasarse **al crear** el span y por qué?",
               "Los que un *sampler* podría necesitar (operación, agente, modelo, herramienta…): el sampler solo ve lo que se da en `start_span(attributes=...)`; un `set_attribute` posterior es invisible para él. La spec GenAI marca varios atributos como *sampling relevant*."))
    md(details("2 · (Módulo 03) ¿`SpanKind` de la llamada al LLM y de una herramienta Python local?",
               "El LLM es una llamada a otro sistema que espera respuesta → `CLIENT`. Una función local es `INTERNAL`. El agente en el mismo proceso, `INTERNAL`."))
    md(details("3 · (Módulo 03) ¿Por qué el span `invoke_agent` lleva los tokens totales si cada `chat` ya lleva los suyos?",
               "Porque la raíz resume el trabajo del agente (útil para coste por petición sin recorrer el árbol). Pero ojo: **sumar tokens de todos los spans cuenta cada token dos veces** (lo calcularás en esta lección)."))

    code(boot("viz,otel") + '''
import subprocess, sys
try:                                                                  # implementación OFICIAL de referencia (para contrastar); opcional
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opentelemetry-util-genai"], check=True, capture_output=True)
except Exception as e:
    print("(opcional) no se pudo instalar opentelemetry-util-genai:", e)
''')
    code(IMPORTS + OTEL_IMPORTS + '''
STACK = check_stack([])                                         # este módulo no necesita servicios
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
''' + SPEC_LOADER)

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ---
    # 1 · Intuición: sin vocabulario común, cada equipo inventa el suyo

    Imagina tres equipos de SupportOps midiendo lo mismo: «tokens de entrada de una llamada al modelo». El equipo A escribe `llm.tokens.in`, el B `prompt_tokens`, el C `gen_ai.usage.input_tokens`.
    Cada dashboard, alerta y herramienta (Grafana, un *vendor*, tu propio cálculo de coste) tendría que **traducir** tres dialectos… y las consultas de uno no sirven a los otros.

    | Si vienes de… | Analogía |
    |---|---|
    | **ML** | Los nombres de columnas de un *feature store*: si cada equipo llama `edad`, `age` y `AGE_YRS` a la misma variable, ningún modelo ni validación se comparte. La *semantic convention* es el esquema de columnas común. |
    | **Backend** | Las convenciones HTTP de OTel (`http.request.method`, `http.response.status_code`): gracias a ellas un mismo panel sirve para cualquier framework web. |
    | **SRE** | La convención de etiquetas de Prometheus (`job`, `instance`): permite alertas genéricas reutilizables entre servicios. |
    """)
    code('''
fig, axes = plt.subplots(1, 2, figsize=(14, 4.2))
for ax, title in zip(axes, ("Sin convención: N dialectos × M herramientas", "Con convención: 1 vocabulario")):
    ax.axis("off"); ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.set_title(title, fontweight="bold")
teams = ["equipo A\\nllm.tokens.in", "equipo B\\nprompt_tokens", "equipo C\\nusage.in", "equipo D\\ntokens_entrada"]
tools = ["dashboard\\nGrafana", "cálculo de\\ncoste", "alertas", "vendor\\nSaaS"]
for i, t in enumerate(teams): viz.box(axes[0], 2, 46 - i * 14, 20, 9, t, viz.PALETTE["neutral"], fontsize=8)
for j, t in enumerate(tools): viz.box(axes[0], 78, 46 - j * 14, 20, 9, t, viz.PALETTE["traces"], fontsize=8)
for i in range(4):
    for j in range(4): viz.arrow(axes[0], (23, 50.5 - i * 14), (77, 50.5 - j * 14), color=viz.PALETTE["error"], lw=0.8, style="-")
axes[0].text(50, 1, "16 traducciones que mantener", ha="center", color=viz.PALETTE["error"], fontsize=10)
for i, t in enumerate(teams): viz.box(axes[1], 2, 46 - i * 14, 20, 9, t.split("\\n")[0], viz.PALETTE["neutral"], fontsize=8)
hub = viz.box(axes[1], 36, 22, 28, 16, "gen_ai.usage.input_tokens\\n(spec oficial)", viz.PALETTE["ok"], fontsize=9, bold=True)
for j, t in enumerate(tools): viz.box(axes[1], 78, 46 - j * 14, 20, 9, t, viz.PALETTE["traces"], fontsize=8)
for i in range(4):
    viz.arrow(axes[1], (23, 50.5 - i * 14), viz.left(hub), color=viz.PALETTE["ok"], lw=1.2)
    viz.arrow(axes[1], viz.right(hub), (77, 50.5 - i * 14), color=viz.PALETTE["ok"], lw=1.2)
axes[1].text(50, 1, "8 enlaces: añadir un equipo o herramienta cuesta 1", ha="center", color=viz.PALETTE["ok"], fontsize=10)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Con N productores y M consumidores, sin estándar hay **N × M** traducciones; con un vocabulario común, **N + M**. Es el argumento económico de las semantic conventions (y de OTLP).
    - El estándar no es gratis: obliga a **seguirlo cuando cambia**. En GenAI cambia con frecuencia, y por eso el resto de la lección trata de **medir la desviación** (linter) y de **migrar** con método.
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ---
    # 2 · Estado de la especificación: qué es estable, qué es experimental y cómo se mueve

    > 📚 **Dónde vive hoy.** Las convenciones GenAI se desarrollaron dentro de `open-telemetry/semantic-conventions` (carpeta `docs/gen-ai`). **Se han movido** a su propio repositorio, [`open-telemetry/semantic-conventions-genai`](https://github.com/open-telemetry/semantic-conventions-genai); la página antigua conserva solo un aviso de «Moved». Tutoriales anteriores a la mudanza apuntan a la ruta vieja.

    Lo que dice la spec **hoy** (instantánea del módulo, extraída de `model/gen-ai/registry.yaml` y `spans.yaml`):
    """)
    code('''
st = collections.Counter(a["stability"] for a in REG.values())
span_st = collections.Counter(s["stability"] for s in SPANS.values()); met_st = collections.Counter(m["stability"] for m in SPEC["metrics"].values())
print("atributos  :", dict(st)); print("tipos span :", dict(span_st)); print("métricas   :", dict(met_st))
print("\\nAtributos «compartidos» que usan los spans GenAI pero viven en las convenciones generales (estables):")
shared = sorted({k for s in SPANS.values() for k in s["attributes"] if k not in REG})
print("  ", shared)
''')
    md("""
    **Conclusiones verificables:**

    | Hecho | Qué implica |
    |---|---|
    | **Todos** los atributos, spans y métricas `gen_ai.*` están en estado `development` | No hay garantía de compatibilidad: un renombrado entre versiones es posible (ya ha ocurrido varias veces) |
    | `error.type`, `server.address`, `server.port` **sí** son estables (convenciones generales) | Puedes depender de ellos sin riesgo |
    | Cada documento de la spec lleva `Status: Development` | Desconfía de dashboards «universales» de terceros sin versión de spec |
    | Las librerías de instrumentación (`opentelemetry-util-genai`, `opentelemetry-instrumentation-genai-*`) están en versión **beta** (1.2b0 al escribir esto) | La implementación también se mueve |

    ### El mecanismo de transición: *opt-in* por variable de entorno

    Para no romper a quien ya consume los nombres antiguos, las librerías de instrumentación suelen emitir los nombres nuevos solo bajo una variable (`OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`, que documenta el README de `opentelemetry-util-genai`) y la captura de contenido bajo otra (`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`: `NO_CONTENT` por defecto, `SPAN_ONLY`, `EVENT_ONLY`, `SPAN_AND_EVENT`).
    Lección práctica: **trata los nombres de atributo como un contrato versionado**: fija la versión de spec que sigues, conserva un **mapa de renombres** y, si migras, emite ambos nombres durante un periodo (doble emisión).

    ## 2.1 La deriva, medida: el paquete de Python frente a la spec

    El paquete `opentelemetry-semantic-conventions` expone constantes Python (`gen_ai_attributes`). ¿Coinciden con la spec de hoy?
    """)
    code('''
import opentelemetry.semconv._incubating.attributes.gen_ai_attributes as pkg
from importlib.metadata import version
pkg_names = {getattr(pkg, n) for n in dir(pkg) if n.startswith("GEN_AI") and not n.endswith("VALUES") and isinstance(getattr(pkg, n), str)}
spec_names = set(REG)
only_pkg, only_spec, both = pkg_names - spec_names, spec_names - pkg_names, pkg_names & spec_names
print(f"opentelemetry-semantic-conventions {version('opentelemetry-semantic-conventions')}: {len(pkg_names)} nombres gen_ai.* · spec: {len(spec_names)}")
print("\\nSolo en el paquete (obsoletos o movidos en la spec actual):", sorted(only_pkg))
print("\\nSolo en la spec (aún sin constante en el paquete):", len(only_spec), "p. ej.", sorted(only_spec)[:6])
fig, ax = plt.subplots(figsize=(8, 2.6)); vals = [len(both), len(only_pkg), len(only_spec)]
bars = ax.barh(["coinciden", "solo paquete\\n(obsoletos/movidos)", "solo spec\\n(nuevos)"], vals, color=[viz.PALETTE["ok"], viz.PALETTE["error"], viz.PALETTE["warn"]]); ax.bar_label(bars)
ax.set_xlabel("nº de atributos gen_ai.*"); ax.set_title("Deriva entre el paquete Python y la spec oficial"); ax.invert_yaxis(); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Entre los «solo paquete» aparecen `gen_ai.system`, `gen_ai.usage.prompt_tokens`, `gen_ai.usage.completion_tokens`, `gen_ai.usage.cache_creation.input_tokens`, `gen_ai.prompt`, `gen_ai.completion` y `gen_ai.token.type`: **nombres que la spec actual ya no define** (la spec usa `gen_ai.provider.name`, `input_tokens`/`output_tokens`, `cache_write`…). Los `gen_ai.openai.*` se han movido a un espacio propio (`openai.*`).
    - En «solo spec» hay decenas de atributos nuevos (memoria, *skills*, modalidades, `gen_ai.token.modality`…) que el paquete aún no expone como constante.
    - **Consecuencia:** copiar constantes de la librería puede producir nombres ya obsoletos. Por eso SupportOps escribe los nombres como cadenas **verificadas contra el registro** y por eso el linter de esta lección toma la spec (no el paquete) como fuente de verdad. Tu versión instalada del paquete puede dar números distintos: la tabla se calcula en vivo.
    """))

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ---
    # 3 · Teoría: operaciones, tipos de span y niveles de requisito

    `gen_ai.operation.name` identifica **qué hace** el span. Valores conocidos hoy (de la spec; si ninguno aplica, se permite uno propio):
    """)
    code('''
ops = REG["gen_ai.operation.name"]["enum"]
print(len(ops), "operaciones:", ops)
mine = {"invoke_agent": "ticket completo (agente local)", "chat": "cada llamada al LLM", "execute_tool": "cada herramienta (get_order, issue_refund, search_kb, escalate_to_human)"}
print("\\nUsa SupportOps:", mine)
print("Aún sin usar: create_agent (agentes remotos gestionados), plan, invoke_workflow (módulo 11), retrieval/embeddings (RAG), memoria…")
''')
    md("""
    Cada operación corresponde a un **tipo de span** con su *kind*, plantilla de nombre y lista de atributos con **nivel de requisito**:

    | Nivel | Significado | Qué hacer |
    |---|---|---|
    | **Required** | Siempre | Si falta, la telemetría es no conforme |
    | **Conditionally Required** | Obligatorio *si* se cumple una condición («si está disponible», «si la operación terminó en error») | Cumple la condición |
    | **Recommended** | Conviene incluirlo | Inclúyelo salvo que cueste mucho |
    | **Opt-In** | Solo si el usuario lo activa (contenido, argumentos…) | **No por defecto**: privacidad y volumen |
    """)
    code('''
rows = []
for t, s in SPANS.items():
    lv = collections.Counter(a["level"] for a in s["attributes"].values())
    rows.append({"tipo de span": t, "kind": s["kind"], **{k: lv.get(k, 0) for k in ("required", "conditionally_required", "recommended", "opt_in")}})
T = pd.DataFrame(rows).set_index("tipo de span"); display(T)
core = T.loc[["gen_ai.invoke_agent.internal", "gen_ai.client.inference", "gen_ai.execute_tool.internal", "gen_ai.create_agent.client", "gen_ai.invoke_agent.client", "gen_ai.embeddings.client"], ["required", "conditionally_required", "recommended", "opt_in"]]
fig, ax = plt.subplots(figsize=(10, 3.8)); left = np.zeros(len(core)); cols = [viz.PALETTE["error"], viz.PALETTE["warn"], viz.PALETTE["traces"], viz.PALETTE["neutral"]]
for c, color in zip(core.columns, cols):
    ax.barh([i.replace("gen_ai.", "") for i in core.index], core[c], left=left, color=color, label=c.replace("_", " ")); left += core[c].values
ax.invert_yaxis(); ax.set_xlabel("nº de atributos"); ax.legend(ncol=4, loc="lower right", fontsize=8); ax.set_title("Qué exige cada tipo de span (spec actual)"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Muy pocos atributos son *Required* (**uno o dos** por tipo: `gen_ai.operation.name` siempre; además `gen_ai.provider.name` en `chat` y `gen_ai.tool.name` en `execute_tool`): la spec deja casi todo como *Recommended*/*Conditionally Required*.
    - Los atributos **Opt-In** (contenido: mensajes, instrucciones, definiciones y argumentos de herramientas) son una parte considerable de la superficie: la spec los trata como sensibles, no como «más datos».
    - `invoke_agent` en proceso (`internal`) y remoto (`client`) tienen requisitos distintos: p. ej. `gen_ai.provider.name` es obligatorio solo en el **remoto**.
    """))

    md("""
    ## 3.1 SupportOps modelado con la spec

    El árbol de una petición, con **qué tipo de span** es cada nodo y los atributos que lleva (los *Required* en rojo):
    """)
    code('''
fig, ax = viz.canvas(15, 5.4, xlim=(0, 150), ylim=(0, 54))
root = viz.box(ax, 32, 40, 86, 12, "invoke_agent supportops-agent   (INTERNAL)\\ngen_ai.operation.name=invoke_agent · gen_ai.agent.name · gen_ai.conversation.id=<ticket> · gen_ai.request.model\\ngen_ai.usage.input_tokens / output_tokens (total del ticket) · error.type si falla", viz.PALETTE["traces"], fontsize=8)
c1 = viz.box(ax, 1, 14, 47, 18, "chat mock-small   (CLIENT)\\ngen_ai.operation.name=chat\\ngen_ai.provider.name=mock   ← requeridos\\ngen_ai.request.model / max_tokens / temperature\\ngen_ai.response.model / id\\nfinish_reasons=[stop|tool_call]\\nusage.input_tokens / output_tokens", viz.PALETTE["traces"], fontsize=8)
t1 = viz.box(ax, 52, 14, 47, 18, "execute_tool get_order   (INTERNAL)\\ngen_ai.operation.name=execute_tool\\ngen_ai.tool.name   ← requeridos\\ngen_ai.tool.type=function\\ngen_ai.tool.call.id\\nerror.type=upstream_500 (si falla)", viz.PALETTE["logs"], fontsize=8)
c2 = viz.box(ax, 103, 14, 46, 18, "chat mock-small   (CLIENT)\\n2.ª llamada, con el resultado de la herramienta\\n(mismos atributos; los tokens de\\nentrada crecen: contexto acumulado)", viz.PALETTE["traces"], fontsize=8)
for b in (c1, t1, c2): viz.arrow(ax, viz.bottom(root), viz.top(b), rad=0.0)
ax.text(75, 5, "Opt-In (APAGADO por defecto): gen_ai.input.messages · gen_ai.output.messages · gen_ai.tool.call.arguments / .result", fontsize=9, color=viz.PALETTE["error"], style="italic", ha="center")
plt.show()
''')
    md("""
    Detalles que **no** son obvios y que la spec fija:

    - **`invoke_agent` en proceso es `INTERNAL`**; si el agente fuera un servicio remoto gestionado (Bedrock Agents, asistentes de OpenAI) sería `CLIENT` y exigiría también `gen_ai.provider.name`.
    - **Nombre del span** = `{gen_ai.operation.name} {objeto}`: `chat {modelo}`, `execute_tool {herramienta}`, `invoke_agent {agente}` (o solo `invoke_agent` si no hay nombre). **Nunca** un id de ticket o pedido.
    - **`gen_ai.conversation.id`**: úsalo solo si tienes un identificador **real** de conversación (para nosotros, el ticket). La spec **desaconseja** (SHOULD NOT) inventarlo con un UUID nuevo, el `trace_id` o un hash del contenido.
    - **`gen_ai.provider.name`**: lista de valores conocidos (`openai`, `anthropic`, `aws.bedrock`, `gcp.vertex_ai`…); se permite un valor propio (por eso `mock` es válido). `gen_ai.system` **ya no existe**.
    - **`gen_ai.request.model` en `invoke_agent`**: solo si el agente usa **un único** modelo; para agentes con varios, no se pone.

    ## 3.2 Tokens: la parte donde más se equivoca la gente

    📐 Reglas de la spec (con proveedores que cachean el prompt):

    - `gen_ai.usage.input_tokens` = **total** de entrada, **incluyendo** los tokens leídos y escritos en caché.
    - `gen_ai.usage.cache_read.input_tokens` y `cache_write.input_tokens` son **subconjuntos** de `input_tokens`.
    - `gen_ai.usage.output_tokens` incluye los de razonamiento (`gen_ai.usage.reasoning.output_tokens` es un subconjunto).
    - Si el proveedor informa tokens *facturables* y *consumidos*, se reportan los **facturables**.
    - Cada proveedor reporta a su manera. La spec de Anthropic lo dice explícitamente: su `input_tokens` **excluye** la caché, así que
    $$ \\texttt{gen\\_ai.usage.input\\_tokens} \\;=\\; \\texttt{input\\_tokens}+\\texttt{cache\\_read\\_input\\_tokens}+\\texttt{cache\\_write\\_input\\_tokens} $$
    """)
    code('''
# Ejemplo con la forma de uso de Anthropic: input_tokens EXCLUYE caché
prov = {"input_tokens": 50, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 20, "output_tokens": 30}
semconv = {"gen_ai.usage.input_tokens": prov["input_tokens"] + prov["cache_read_input_tokens"] + prov["cache_creation_input_tokens"],
           "gen_ai.usage.cache_read.input_tokens": prov["cache_read_input_tokens"], "gen_ai.usage.cache_write.input_tokens": prov["cache_creation_input_tokens"],
           "gen_ai.usage.output_tokens": prov["output_tokens"]}
print("proveedor :", prov); print("semconv   :", semconv)
# Coste ilustrativo: precio base 1,0 por unidad; lectura de caché 0,1×; escritura 1,25× (multiplicadores típicos de «prompt caching», ilustrativos)
base, rd, wr = 1.0, 0.1, 1.25
sin_cache = semconv["gen_ai.usage.input_tokens"] * base
con_cache = prov["input_tokens"] * base + prov["cache_read_input_tokens"] * base * rd + prov["cache_creation_input_tokens"] * base * wr
fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
axes[0].barh(["semconv\\ninput_tokens", "proveedor\\ninput_tokens"], [semconv["gen_ai.usage.input_tokens"], prov["input_tokens"]], color=[viz.PALETTE["ok"], viz.PALETTE["warn"]]); axes[0].set_title("¿Cuántos tokens de entrada hubo?")
axes[0].bar_label(axes[0].containers[0]); axes[0].set_xlim(0, 200)
axes[1].bar(["sin caché\\n(170 × 1,0)", "con caché\\n(50 + 100×0,1 + 20×1,25)"], [sin_cache, con_cache], color=[viz.PALETTE["error"], viz.PALETTE["ok"]]); axes[1].bar_label(axes[1].containers[0], fmt="%.0f"); axes[1].set_title("Coste de entrada (unidades ilustrativas)")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Si un dashboard suma `input_tokens` de un proveedor tipo Anthropic **sin** aplicar la regla, ve 50 en vez de 170: **subestima el volumen un 70 %** y no puede explicar por qué la factura no cuadra.
    - Con la spec, los tres números (total, lectura, escritura) permiten **recalcular el coste real**: la caché rebaja el coste de entrada (50 % menos en el ejemplo ilustrativo: 85 frente a 170 unidades) y lo ves en la telemetría.
    - SupportOps (mock) no usa caché de prompt, así que sus `cache_*` no aparecen; el proyecto te hará mapear tres formas de uso de proveedor.
    """))

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ---
    # 4 · A mano: un linter de atributos GenAI

    Para convertir la spec en algo **automatizable**, construimos un linter: una función que recibe un span (dict con el esquema `SPAN_SCHEMA`) y devuelve **hallazgos** con severidad. Es la herramienta que pondrías en CI y en el Collector (módulo 05/20) para vigilar que lo que emiten los servicios sigue la convención.

    | Regla | Severidad | Qué comprueba |
    |---|---|---|
    | `UNK` | error | atributo `gen_ai.*` que **no existe** en el registro (typo, deprecado → sugiere el reemplazo) |
    | `REQ` | error | falta un atributo **Required** del tipo de span |
    | `TYPE` | error | el valor no es del tipo del registro (p. ej. un número como cadena) |
    | `TOK` | error | `cache_read`/`cache_write` mayores que `input_tokens` (deben ser subconjuntos) |
    | `ERR` | error | span en `ERROR` sin `error.type` |
    | `SCOPE` | aviso | atributo válido pero **no definido para ese tipo** de span |
    | `ENUM` | aviso | valor fuera de los conocidos (si la spec permite uno propio, solo avisa) |
    | `NAME` | aviso | el nombre no sigue la plantilla `{operación} {objeto}` |
    | `KIND` | aviso | `SpanKind` distinto del esperado para el tipo |
    | `FINISH` | aviso | un `finish_reason` fuera del enum normalizado de la spec |
    | `CARD` | aviso | un identificador (pedido, ticket, UUID) dentro del **nombre** del span |
    | `CONV` | aviso | `gen_ai.conversation.id` igual al `trace_id` (la spec desaconseja inventar la conversación) |
    | `PRIV` | info | atributos de **contenido** (opt-in) presentes: revísalo con privacidad |

    Primero las constantes y utilidades (tablas de la spec y funciones pequeñas):
    """)
    code(LINT_CONSTANTS)
    md("""
    Ahora el linter. Cada bloque implementa una familia de reglas; fíjate en que **toda la «verdad» sale de `SPEC`** (la instantánea), no de constantes escritas a mano:
    """)
    code(LINT_FULL)
    md("""
    ### Probémoslo con cuatro fuentes de spans

    1. **Pregrabados** (`sample_data`): los que generó el `RecordingInstrumentor` del módulo 01 (escrito antes de esta lección).
    2. **Los nuestros**: `OTelInstrumentor` (módulo 03).
    3. **Oficiales**: la implementación de referencia `opentelemetry-util-genai`, conducida por el mismo agente (un adaptador de 20 líneas). Es nuestro «oráculo»: si el linter marca algo en ella, **dudamos del linter**.
    4. **Legados**: spans con nombres a la antigua y defectos plantados (`make_legacy`), para comprobar que el linter *detecta* lo que debe.
    """)
    code(LEGACY_SRC)
    code('''
from contextlib import contextmanager
from supportops import Instrumentor
SOURCES = {}
SOURCES["pregrabados"] = sample_data.load_spans()
tickets = generate_tickets(60, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, start_s=SIM_EPOCH_S)
tel = setup_telemetry("supportops-agent", mode="memory", set_global=False, deterministic_ids=True)
res = run_tickets(SupportAgent(instrumentor=OTelInstrumentor(tel)), tickets)
SOURCES["OTelInstrumentor"] = tel.span_records()

class OfficialInstrumentor(Instrumentor):
    """Adaptador sobre la implementación OFICIAL (opentelemetry-util-genai) para emitir spans GenAI desde el agente."""
    def __init__(self, tp):
        from opentelemetry.util.genai.handler import TelemetryHandler
        self.h = TelemetryHandler(tracer_provider=tp)
    @contextmanager
    def agent_run(self, ctx):
        with self.h.invoke_local_agent(agent_name=ctx.agent_name, request_model=ctx.model, conversation_id=ctx.ticket.ticket_id): yield
    @contextmanager
    def llm_call(self, ctx, info):
        with self.h.inference(info.provider, request_model=info.model, conversation_id=ctx.ticket.ticket_id) as inv:
            inv.max_tokens, inv.temperature = info.max_tokens, info.temperature
            yield
            r = info.response
            if r is not None:
                inv.input_tokens, inv.output_tokens, inv.response_id = r.usage.input_tokens, r.usage.output_tokens, r.response_id
                inv.response_model_name, inv.finish_reasons = r.model, [{"tool_calls": "tool_call"}.get(r.finish_reason, r.finish_reason)]
    @contextmanager
    def tool_call(self, ctx, info):
        with self.h.tool(info.call.name, tool_type="function", agent_name=ctx.agent_name) as inv:
            inv.tool_call_id = info.call.id
            yield

try:
    tel2 = setup_telemetry("oficial", mode="memory", set_global=False)
    run_tickets(SupportAgent(instrumentor=OfficialInstrumentor(tel2.tracer_provider)), tickets)
    SOURCES["oficial (util-genai)"] = tel2.span_records()
except Exception as e:                                           # sin el paquete oficial, seguimos con tres fuentes
    print("(sin implementación oficial:", repr(e)[:80], ")")
CLEAN = SOURCES["OTelInstrumentor"]
pairs = [make_legacy(s) for s in CLEAN]
SOURCES["legado (plantado)"] = [p[0] for p in pairs]; PLANTED = {s["span_id"]: p[1] for s, p in zip(CLEAN, pairs)}
print({k: len(v) for k, v in SOURCES.items()}, "spans")
''')
    code('''
L = {k: lint(v) for k, v in SOURCES.items()}
rules = list(SEVERITY)
H = pd.DataFrame({k: [int((df.rule == r).sum()) for r in rules] for k, df in L.items()}, index=rules)
pct_clean = {k: 100 * (1 - L[k][L[k].severity.isin(["error", "warn"])].span_id.nunique() / len(SOURCES[k])) for k in SOURCES}
fig, ax = plt.subplots(figsize=(9.5, 4.8)); im = ax.imshow(np.log1p(H.values), cmap="Reds", aspect="auto")
ax.set_xticks(range(H.shape[1]), [f"{c}\\n{pct_clean[c]:.0f} % sin aviso" for c in H.columns], fontsize=8); ax.set_yticks(range(len(rules)), [f"{r} ({SEVERITY[r]})" for r in rules], fontsize=8)
for i in range(H.shape[0]):
    for j in range(H.shape[1]): ax.text(j, i, H.iat[i, j], ha="center", va="center", fontsize=9, color="white" if H.iat[i, j] > 60 else "black")
ax.grid(False); ax.set_title("Hallazgos del linter por regla y por fuente de spans"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **`OTelInstrumentor` y la implementación oficial no tienen errores ni avisos** (columnas casi en blanco): nuestra instrumentación del módulo 03 coincide con el oráculo. Si el linter marcase algo aquí, el defecto estaría en el linter.
    - **Los pregrabados** (módulo 01) tienen dos desviaciones reales: `SCOPE` (`gen_ai.provider.name` en el span `invoke_agent` en proceso, que la spec no define para ese tipo) y `FINISH` (`tool_calls` en vez del valor normalizado `tool_call`). Nadie lo notó hasta tener un linter: es el valor de automatizar la comprobación.
    - **El legado** dispara casi todas las reglas: justo las que plantamos (`UNK`/`REQ` por nombres antiguos, `TYPE`, `TOK`, `CARD`, `KIND`…). Comprobamos más abajo que el linter **no deja escapar ninguna**.
    """))
    code('''
# ¿Detecta el linter TODO lo que plantamos? (recall por regla) y ejemplos de mensajes
found = L["legado (plantado)"].groupby("span_id").rule.apply(set).to_dict()
rec = {}
for r in sorted({c for p in PLANTED.values() for c in p}):
    exp = [sid for sid, p in PLANTED.items() if r in p]; rec[r] = (sum(r in found.get(sid, set()) for sid in exp), len(exp))
print("plantados detectados / plantados:", {r: f"{a}/{b}" for r, (a, b) in rec.items()})
ex = L["legado (plantado)"].drop_duplicates(["rule", "attr"]).sort_values("rule")[["rule", "severity", "name", "attr", "msg"]]
ex["name"] = ex.name.str.slice(0, 30)
print(ex.head(14).to_string(index=False))
''')

    md("""
    ## 4.1 Contrastar con la implementación oficial: ¿qué atributos emite cada una?

    El linter valida *conformidad*; esta comparación muestra *cobertura*: qué recomendados emite el oráculo y nosotros no (y al revés).
    """)
    code('''
def keysets(spans):
    d = collections.defaultdict(set)
    for s in spans: d[s["attributes"].get("gen_ai.operation.name")] |= {k for k in s["attributes"] if k.startswith("gen_ai.")}
    return d
if "oficial (util-genai)" in SOURCES:
    ours, off = keysets(SOURCES["OTelInstrumentor"]), keysets(SOURCES["oficial (util-genai)"])
    for op in ("invoke_agent", "chat", "execute_tool"):
        print(f"{op:13s} solo nosotros: {sorted(ours[op] - off[op])}\\n{'':13s} solo oficial : {sorted(off[op] - ours[op])}")
''')
    md("""
    En este experimento la implementación oficial emite un **subconjunto** de lo nuestro: la diferencia son los tokens agregados en la raíz `invoke_agent` y `gen_ai.conversation.id` en las herramientas (la spec los define para esos tipos de span). Ninguna diferencia es un **error**: son decisiones de cobertura, y ambas pasan el linter. (Las que dependen del proveedor —caché, `server.address`— no aparecen porque el mock no las tiene.)

    ## 4.2 Migrar nombres antiguos: el mapa de renombres

    El patrón de migración que usan los equipos serios tiene tres piezas (que construirás en el proyecto): (1) un **mapa de renombres** versionado (`RENAMES`, ya lo usa el linter para sugerir), (2) una **transformación** de spans antiguos a nuevos (por ejemplo en el Collector con el procesador `transform`, módulo 05), y (3) un periodo de **doble emisión** para que los consumidores antiguos migren sin romperse.
    """)
    code('''
legacy_chat = next(s for s in SOURCES["legado (plantado)"] if s["name"].startswith("chat") and "gen_ai.system" in s["attributes"])
print("antes  :", {k: v for k, v in legacy_chat["attributes"].items() if k.startswith("gen_ai.")})
migrated = copy.deepcopy(legacy_chat)
for old, new in RENAMES.items():
    if old in migrated["attributes"] and "(aprox.)" not in new: migrated["attributes"][new] = migrated["attributes"].pop(old)
print("después:", {k: v for k, v in migrated["attributes"].items() if k.startswith("gen_ai.")})
print("hallazgos antes:", [f["rule"] for f in lint_span(legacy_chat)], "→ después:", [f["rule"] for f in lint_span(migrated)])
''')

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ---
    # 5 · Contenido de prompts y respuestas: utilidad, coste de privacidad y coste de almacenamiento

    La spec marca los **mensajes de entrada/salida, las instrucciones de sistema, las definiciones y los argumentos/resultados de herramientas** como *Opt-In* y dice explícitamente que son «sensibles y a menudo grandes» y que las instrumentaciones **NO deben capturarlos por defecto**. Ofrece tres patrones:

    | Patrón | Qué es | Cuándo |
    |---|---|---|
    | **1. No registrar** (por defecto) | Solo metadatos (modelo, tokens, estado) | Producción por defecto |
    | **2. En atributos del span** | `gen_ai.input.messages` / `output.messages` como JSON | Pre-producción o cuando la normativa y el almacenamiento lo permiten |
    | **3. Almacenamiento externo + referencia** | El contenido va a un almacén con su control de acceso; el span solo guarda una referencia | Producción con necesidad de depurar con contenido |

    En spans el contenido va como **cadena JSON** (los atributos estructurados aún no están soportados en spans por el SDK de Python; en eventos/logs sí se pueden estructurar). Medimos qué cuesta cada patrón con **tráfico con PII sintética** (30 % de los tickets traen correo y teléfono):
    """)
    code('''
import re
EMAIL = re.compile(r"[\\w.+-]+@[\\w-]+\\.[\\w.-]+")
tk_pii = generate_tickets(60, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, pii_rate=0.3, start_s=SIM_EPOCH_S)
vault: dict = {}
def to_vault(s: str) -> str:                                      # patrón 3: contenido al almacén, el span guarda solo una referencia
    h = hashlib.sha256(s.encode()).hexdigest()[:16]; vault[h] = s; return json.dumps({"vault_ref": h})

def run_policy(**kw):
    t = setup_telemetry("policy", mode="memory", set_global=False)
    run_tickets(SupportAgent(instrumentor=OTelInstrumentor(t, **kw)), tk_pii); sp = t.span_records(); t.shutdown(); return sp

POL = {"1 · sin contenido": run_policy(), "2 · en atributos": run_policy(capture_content=True), "3 · almacén + ref.": run_policy(capture_content=True, redact=to_vault)}
def span_bytes(s): return len(json.dumps(s["attributes"], ensure_ascii=False).encode())
rows = []
for k, sp in POL.items():
    b = np.array([span_bytes(s) for s in sp]); pii = sum(bool(EMAIL.search(json.dumps(s["attributes"], ensure_ascii=False))) for s in sp)
    rows.append({"política": k, "spans": len(sp), "bytes/span (media)": int(b.mean()), "bytes/ticket": int(b.sum() / len(tk_pii)), "spans con correo en claro": pii})
R = pd.DataFrame(rows).set_index("política"); display(R)
''')
    code('''
fig, axes = plt.subplots(1, 3, figsize=(15, 3.6)); cols = [viz.PALETTE["ok"], viz.PALETTE["error"], viz.PALETTE["warn"]]
axes[0].boxplot([[span_bytes(s) for s in sp] for sp in POL.values()], tick_labels=[k.split(" · ")[0] for k in POL]); axes[0].set_yscale("log"); axes[0].set_ylabel("bytes de atributos por span (log)"); axes[0].set_title("Tamaño de un span")
b = axes[1].bar([k.split(" · ")[0] for k in POL], R["bytes/ticket"], color=cols); axes[1].bar_label(b); axes[1].set_title("Bytes de atributos por ticket")
b = axes[2].bar([k.split(" · ")[0] for k in POL], R["spans con correo en claro"], color=cols); axes[2].bar_label(b); axes[2].set_title("Spans con un correo en claro")
plt.tight_layout(); plt.show()
GB_DAY = R["bytes/ticket"] * 1_000_000 / 1e9           # suposición explícita: 1 M de tickets/día
print("Proyección a 1 M de tickets/día (solo atributos, sin comprimir ni índices):", {k: f"{v:.2f} GB/día" for k, v in GB_DAY.items()})
''')
    md(observe("""
    - **Patrón 2** multiplica el tamaño de los spans (más del doble aquí; y el contenido de **todos** los pasos se repite: cada `chat` lleva la conversación completa hasta ese momento, así que crece con la longitud de la conversación) y deja el **correo del cliente en claro** en decenas de spans: cualquiera con acceso a Tempo ve datos personales.
    - **Patrón 3** deja el tamaño cerca del patrón 1 (cada referencia ocupa unas decenas de bytes) y **elimina los datos personales de los spans** (están en el almacén, con su propio control de acceso y retención). No desaparece el riesgo: **lo mueves** a un sitio donde sí puedes gobernarlo (módulo 20).
    - La proyección (1 M de tickets/día es una suposición del ejercicio) es pequeña porque nuestros tickets tienen pocos pasos y mensajes cortos; con conversaciones reales (historiales largos, documentos RAG en el contexto) el factor del patrón 2 se dispara. El **coste de almacenamiento** es la segunda razón, tras la privacidad, para no capturar contenido por defecto.
    - La spec añade un matiz: el *hook* de subida a almacenamiento externo **debería invocarse aunque el span no se muestree**, para no perder el contenido de trazas descartadas.
    """))

    md("""
    ## 5.1 Las métricas GenAI de hoy (para el módulo 09)

    Los nombres de **métricas** también cambiaron. La spec actual define, entre otras (instantánea):
    """)
    code('''
M = pd.DataFrame(SPEC["metrics"]).T[["instrument", "unit", "stability"]]
mine = {"gen_ai.client.inference.duration", "gen_ai.client.inference.usage.input_tokens", "gen_ai.client.inference.usage.output_tokens"}
M["¿la emite OTelInstrumentor?"] = ["sí" if n in mine else "" for n in M.index]
display(M.loc[[n for n in M.index if n.startswith("gen_ai.client.inference") or n.startswith("gen_ai.invoke") or n.startswith("gen_ai.execute")]])
''')
    md("""
    Tres cambios de nombre que verás en tutoriales antiguos y que **ya no** coinciden con la spec: `gen_ai.client.token.usage` (histograma con `gen_ai.token.type`) → contadores `gen_ai.client.inference.usage.input_tokens`/`output_tokens` (+ histogramas `...operation.input_tokens/output_tokens`);
    `gen_ai.client.operation.duration` → **para inferencia** se usa `gen_ai.client.inference.duration` (la antigua queda para operaciones que no son inferencia); y aparecen métricas de agente (`gen_ai.invoke_agent.duration`, `gen_ai.invoke_agent.inference_calls`, `gen_ai.invoke_agent.tool_calls`) y de herramienta (`gen_ai.execute_tool.duration`).
    En Prometheus, `gen_ai.client.inference.usage.input_tokens` se convierte en `gen_ai_client_inference_usage_input_tokens_total` y la duración en `gen_ai_client_inference_duration_seconds_*` (lo medimos con el stack real en el módulo 03). El módulo 09 las implementa por completo.

    ## 5.2 Evaluaciones (adelanto del módulo 14)

    La spec ya define el evento `gen_ai.evaluation.result` (atributos `gen_ai.evaluation.name`, `.score.value`, `.score.label`, `.explanation`), que debe **colgar del span evaluado** (o llevar `gen_ai.response.id`). Es la forma estándar de adjuntar «la nota del juez» a una traza; el módulo 14 la usa.
    """)

    # ------------------------------------------------------------------------------------------------ 6
    md("""
    ---
    # 6 · 🏭 En producción

    - **Los *backends* ya consumen estas convenciones.** Datadog anunció soporte nativo de las GenAI semantic conventions (v1.37 en adelante) para recibir trazas OTel sin su SDK ([Datadog: *OTel GenAI semantic conventions*](https://www.datadoghq.com/blog/llm-otel-semantic-convention/)); las herramientas de código abierto de autoinstrumentación (OpenLIT, OpenLLMetry; módulo 06) también se alinean con estos nombres. Tu inversión en nombres estándar es portable entre ellos.
    - **Las librerías de instrumentación oficiales se reorganizan.** El repositorio [`opentelemetry-python-genai`](https://github.com/open-telemetry/opentelemetry-python-genai) agrupa `opentelemetry-util-genai` (la base común: spans, métricas, eventos y *hook* de subida de contenido) y paquetes `opentelemetry-instrumentation-genai-*` (OpenAI, Anthropic, Bedrock, LangChain, LlamaIndex…, en beta); las copias que siguen en `opentelemetry-python-contrib/instrumentation-genai` solo reciben parches de seguridad y se retirarán (aviso en su README), así que los paquetes antiguos como `opentelemetry-instrumentation-openai-v2` son un callejón sin salida. Fija versiones y lee el CHANGELOG antes de actualizar.
    - **Gobierno de nombres en una empresa:** un *schema registry* interno (YAML por servicio con los atributos que emite), un linter en CI (como el de esta lección) sobre los spans de los tests y otro en el pipeline de ingestión que cuenta los desvíos como métrica («% de spans con `UNK`»).
    - **Contenido de prompts:** la práctica habitual de producción es el patrón 3 (almacén externo con control de acceso y retención corta) o muestrear el contenido (guardarlo solo para un % de trazas y para los errores), nunca «todo en atributos».
    - **Cambio de versión sin romper tableros:** emitir ambos nombres un tiempo (doble emisión) o traducir en el Collector, y cambiar los dashboards después de comprobar con el linter que nadie emite ya el nombre antiguo.
    """)

    md("""
    ---
    # 7 · 🧠 Secretos de la élite

    Primero un par de comprobaciones numéricas con nuestros propios spans que sostienen dos de los puntos:
    """)
    code('''
sp = SOURCES["OTelInstrumentor"]
tok = lambda ss: sum(s["attributes"].get("gen_ai.usage.input_tokens", 0) for s in ss)
all_t, chat_t, agent_t = tok(sp), tok([s for s in sp if s["name"].startswith("chat ")]), tok([s for s in sp if s["name"].startswith("invoke_agent")])
print(f"tokens de entrada: todos los spans = {all_t} · solo chat = {chat_t} · solo invoke_agent = {agent_t}  → sumar todo cuenta {all_t / chat_t:.2f}× lo real")
samp = {t: sorted(k for k, v in SPANS[t]["attributes"].items() if v["sampling_relevant"]) for t in ("gen_ai.client.inference", "gen_ai.execute_tool.internal", "gen_ai.invoke_agent.internal")}
for t, v in samp.items(): print(f"atributos «sampling relevant» de {t}:", v)
''')
    md("""
    1. **Los nombres son un contrato versionado y la deriva es real.** En 2.1 contaste atributos del paquete Python que la spec ya no define (`gen_ai.system`, `prompt_tokens`…). *Contramedida:* fija la versión de spec que sigues (el commit de la instantánea del módulo), conserva un `RENAMES`, emite doble durante la transición y mide el desvío con un linter. Las librerías oficiales fijan además el **`schema_url`** de la versión de convenciones que emiten (`opentelemetry-util-genai` usa el de v1.37.0), que permite a un backend traducir nombres entre versiones.
    2. **Sumar tokens de todos los spans los cuenta ~2 veces.** `invoke_agent` repite el total de sus `chat` (lo acabas de medir: ≈ 2,0×). Los tableros de coste deben agregar **solo spans `chat`** (o solo la raíz), y la spec lo refuerza con métricas distintas (`gen_ai.client.inference.usage.*` por inferencia; `gen_ai.invoke_agent.*` por agente, donde incluso cuenta cada llamada solo en el agente que la hizo para no duplicar en árboles de subagentes).
    3. **«Tokens de entrada» depende del proveedor.** Para Anthropic `input_tokens` excluye la caché; para la spec incluye todo. Si sumas lo que dice el proveedor sin normalizar, tus costes divergen de la factura. Y **factura con el modelo real**: `gen_ai.response.model` (el que atendió), no `gen_ai.request.model` (que puede ser un alias).
    4. **Los `finish_reasons` son la señal más barata de calidad degradada.** `length` = respuesta truncada; `content_filter` = bloqueada; `error` = terminó mal (la spec pide **reportar `error`** si se esperaba un motivo y no llegó, en vez de omitirlo). Normalizar los valores nativos (`end_turn`, `max_tokens`, `tool_use`, `tool_calls`…) al enum de la spec es lo que permite un único panel multi-proveedor; en el módulo 16 será un SLI.
    5. **`gen_ai.conversation.id` no se inventa.** Un UUID nuevo por llamada o el `trace_id` rompen la semántica (agrupar mensajes de una conversación): la spec indica expresamente (SHOULD NOT) que no se usen como valor de reserva. En SupportOps el ticket **es** la conversación; en un chat multi-turno sería el id de sesión.
    6. **Los atributos «sampling relevant» deben existir al crear el span.** La spec marca `gen_ai.operation.name`, `gen_ai.agent.name`, `gen_ai.request.model`, `gen_ai.tool.name`, `gen_ai.tool.type`, `gen_ai.provider.name`… (lo viste impreso arriba) para que un muestreador de cabecera pueda decidir. Ponerlos tarde es un error silencioso que inutiliza reglas como «muestrea todo lo del modelo caro».
    7. **El contenido tiene su propio ciclo de vida.** En spans va como JSON string porque el SDK aún no soporta atributos estructurados en spans (sí en eventos/logs: OTEP 4485); los backends tienen límites por atributo/lote, y la propia spec avisa de que un prompt largo puede **superar los límites de atributo o de lote del backend**. El *hook* de subida a almacén externo se invoca aunque el span no se muestree: así el contenido sigue su política de retención, no la de las trazas.
    8. **`gen_ai.provider.name` identifica el «sabor» de telemetría, no necesariamente al proveedor real.** La spec lo dice: se fija según el mejor conocimiento de la instrumentación y puede diferir del upstream (un gateway compatible con OpenAI que enruta a otro modelo). Si facturas por proveedor, no uses este atributo como única fuente: añade el tuyo (`supportops.llm.upstream`).
    9. **Los *buckets* por defecto del SDK no sirven para latencias en segundos.** La spec del SDK de métricas fija por defecto `[0, 5, 10, 25, 50, 75, 100, 250, …, 10000]` (pensado para milisegundos); un histograma en **segundos** con esos límites mete casi todas las llamadas LLM en el bucket `(0, 5]` y el p95 estimado sale como una interpolación sin sentido. La spec GenAI pide (SHOULD) límites explícitos para `gen_ai.client.operation.duration` y similares: `[0.01, 0.02, 0.04, …, 81.92]` (doblando). La celda siguiente mide el error (con latencias de mediana 0,8 s, semilla 42: p95 real ≈ 2,2 s; estimado con los límites por defecto ≈ 4,8 s; con los de la spec GenAI ≈ 2,4 s). Comprueba que tu SDK aplica el *advisory* de la instrumentación (o fija una `View` con los límites).
    """)
    code('''
import numpy as np
rng = np.random.default_rng(42)
lat = rng.lognormal(mean=np.log(0.8), sigma=0.6, size=20_000)         # latencias sintéticas en segundos (mediana ≈ 0,8 s)
DEFAULT = [0, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000]   # defecto del SDK (spec de métricas)
GENAI = [0.01 * 2**i for i in range(14)]                                              # recomendado por la spec GenAI
def p_from_hist(x, bounds, q=0.95):
    counts, edges = np.histogram(x, bins=[-np.inf, *bounds, np.inf])
    cum, target = np.cumsum(counts), q * len(x)
    i = int(np.searchsorted(cum, target))
    lo = bounds[i - 1] if i > 0 else 0.0
    hi = bounds[i] if i < len(bounds) else bounds[-1]
    prev = cum[i - 1] if i > 0 else 0
    return lo + (hi - lo) * (target - prev) / max(counts[i], 1)                       # interpolación lineal (como histogram_quantile)
print(f"p95 exacto            : {np.quantile(lat, .95):6.2f} s")
print(f"p95 con buckets SDK   : {p_from_hist(lat, DEFAULT):6.2f} s")
print(f"p95 con buckets GenAI : {p_from_hist(lat, GENAI):6.2f} s")
''')

    md("""
    ---
    # 8 · ⚠️ Errores comunes

    | Error | Síntoma | Arreglo |
    |---|---|---|
    | Copiar nombres de un tutorial antiguo (`gen_ai.system`, `prompt_tokens`) | Dashboards a 0 tras actualizar; el linter marca `UNK` | Mapa de renombres + doble emisión + linter |
    | Marcar el LLM como `INTERNAL` o la raíz del agente local como `CLIENT` | Mapas de servicios y *span metrics* distorsionados | `chat` = `CLIENT`; `invoke_agent` en proceso = `INTERNAL` |
    | Nombres de span con ids (`execute_tool get_order ORD-17`) | Explosión de cardinalidad en Tempo | `execute_tool {herramienta}`; el id va como atributo |
    | Sumar tokens de todos los spans | Coste duplicado | Agregar solo `chat` (o la raíz) |
    | Ignorar la caché de prompt en `input_tokens` | Coste y volumen mal calculados | Aplicar la regla del proveedor → total de la spec |
    | Capturar contenido «para depurar» y dejarlo en producción | PII en Tempo, GB/día extra | Patrón 3 (almacén + referencia) y muestreo del contenido |
    | `finish_reasons` como cadena y no como lista | Rechazo de tipo (`TYPE`) en el backend o en el linter | Lista de cadenas, una por elección |
    | `conversation.id = trace_id` | Agrupaciones de «conversación» sin sentido | Id real de sesión/ticket o no ponerlo |
    | Confiar en las constantes de `opentelemetry-semantic-conventions` | Nombres obsoletos | Verificar contra el registro actual (instantánea/spec) |
    """)

    md("""
    ---
    # 9 · Autoevaluación
    """)
    md(details("1 · (Recuerdo) ¿Qué atributos son *Required* en un span `chat`? ¿Y en `execute_tool`? ¿Y por qué `gen_ai.provider.name` no lo es en `invoke_agent` en proceso?",
               "`chat`: `gen_ai.operation.name` y `gen_ai.provider.name`. `execute_tool`: `gen_ai.operation.name` y `gen_ai.tool.name`. En `invoke_agent` **interno** solo es obligatorio `gen_ai.operation.name`: el agente corre en tu proceso y no hay «proveedor» al que llamar; en el **remoto** (`invoke_agent` CLIENT) sí lo es."))
    md(details("2 · (Cálculo) Una respuesta de un proveedor tipo OpenAI informa `prompt_tokens=1200` (de los cuales `cached_tokens=900`) y `completion_tokens=150` (de los cuales 100 de razonamiento). ¿Qué valores pones en cada atributo `gen_ai.usage.*` y qué fracción de la entrada vino de caché?",
               """
               `gen_ai.usage.input_tokens = 1200` (ya incluye la caché), `gen_ai.usage.cache_read.input_tokens = 900`, `gen_ai.usage.output_tokens = 150` y `gen_ai.usage.reasoning.output_tokens = 100` (subconjunto de la salida).
               Fracción en caché: $900/1200 = 75\\,\\%$. Un linter debe comprobar $\\text{cache\\_read}\\le\\text{input}$ y $\\text{reasoning}\\le\\text{output}$.
               """))
    md(details("3 · (Cálculo) 10 000 tickets/día, 1 300 tokens de entrada acumulados por ticket repartidos en sus `chat`. Un panel suma `gen_ai.usage.input_tokens` de **todos** los spans. ¿Qué cifra muestra y cuál es la real?",
               "Real: $10\\,000\\times1\\,300 = 13$ M. El panel suma también la raíz `invoke_agent` (que repite el total del ticket): $2\\times 13 = 26$ M, un **100 % de sobreestimación** (como medimos, ≈ 2,0×). Arreglo: filtrar por `gen_ai.operation.name = chat`."))
    md(details("4 · (Diagnóstico) Tras actualizar la librería de instrumentación, el panel «tokens por modelo» cae a 0 pero las trazas siguen llegando y las ves en Tempo. ¿Qué miras primero y cómo lo arreglas sin perder histórico?",
               "Mirar los atributos del span nuevo: probablemente la librería emite `gen_ai.usage.input_tokens` y el panel consulta `gen_ai.usage.prompt_tokens` (nombre antiguo). Arreglo: cambiar el panel a **ambos** nombres durante la transición (`or`), o traducir en el Collector, y pasar el linter (`UNK` con sugerencia) por los spans de preproducción para ver qué más cambió."))
    md(details("5 · (Diagnóstico) Tu linter marca `KIND` en todos los spans `invoke_agent` de un servicio que **llama a un agente gestionado remoto** (p. ej. un asistente alojado). ¿Es un falso positivo? ¿Qué cambia en las reglas?",
               "Sí: para un agente **remoto** el tipo correcto es `invoke_agent` **CLIENT** (`gen_ai.invoke_agent.client`), con `gen_ai.provider.name` requerido. Hay que parametrizar el linter (`local_agent=False`) o decidir el tipo por una propiedad del servicio, no asumir siempre agente local."))
    md(details("6 · (Transferencia) Diseña la política de contenido de SupportOps en producción: ¿qué patrón, qué se redacta, quién puede leer, cuánto se retiene y qué haces con los tickets que fallan?",
               "Patrón 3: el span solo lleva metadatos y una referencia; el contenido (redactado: correos, teléfonos, tarjetas) va a un almacén con **acceso restringido por rol** y retención corta (p. ej. días), y se guarda solo para un porcentaje de tickets **más todos los que fallan o tienen baja calidad** (para depurar). Alertas si aparece PII en claro en spans (regla `PRIV` + detector). Auditoría de accesos al almacén. (Módulo 20.)"))
    md(details("7 · (Transferencia) Adoptas una librería de autoinstrumentación (módulo 06) que emite `gen_ai.*` con nombres de la versión 1.37, pero tu Collector y tus paneles esperan los nombres actuales. Plan en tres pasos.",
               "(1) Ejecutar el linter sobre sus spans y obtener la lista real de desvíos (`UNK`, `TYPE`, `SCOPE`). (2) Traducir en el **Collector** (procesador de transformación) o en un `SpanProcessor` propio con el mapa de renombres, con doble emisión si hay consumidores antiguos. (3) Fijar la versión de la librería, añadir el linter a CI y planificar la retirada del mapa cuando la librería actualice."))

    md("""
    ---
    # 10 · Referencias

    - OpenTelemetry. *GenAI semantic conventions* (repositorio actual, estado *Development*) — <https://github.com/open-telemetry/semantic-conventions-genai> · agentes: <https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md> · registro de atributos: <https://github.com/open-telemetry/semantic-conventions-genai/blob/main/model/gen-ai/registry.yaml> · ejemplos: <https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/non-normative/examples-llm-calls.md>
    - OpenTelemetry. *Attribute requirement levels* y *Recording errors* (convenciones generales) — <https://github.com/open-telemetry/semantic-conventions/blob/main/docs/general/attribute-requirement-level.md> · <https://github.com/open-telemetry/semantic-conventions/blob/main/docs/general/recording-errors.md>
    - OpenTelemetry. *OTEP 4485: Extending attributes to support complex values* — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/oteps/4485-extending-attributes-to-support-complex-values.md>
    - OpenTelemetry. `opentelemetry-python-genai` y `opentelemetry-util-genai` (README con variables de entorno) — <https://github.com/open-telemetry/opentelemetry-python-genai> · <https://github.com/open-telemetry/opentelemetry-python-genai/blob/main/util/opentelemetry-util-genai/README.rst>
    - Datadog. *OTel GenAI semantic conventions* (1-dic-2025; soporte nativo de las convenciones GenAI v1.37+; confirmado por búsqueda web, el dominio no es accesible desde el entorno de revisión) — <https://www.datadoghq.com/blog/llm-otel-semantic-convention/>
    - OpenTelemetry. *Metrics SDK* (límites por defecto del histograma explícito) — <https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/metrics/sdk.md> · *GenAI metrics* (límites recomendados) — <https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-metrics.md>.

    ## Siguiente
    `05_collector`: el Collector recibe estos spans, métricas y logs y los reparte a Tempo, Loki y Prometheus; allí podrás aplicar transformaciones (renombres, redacción) en el camino.
    """)
    nb.save(out)


# =====================================================================================================================
# Solución de referencia del proyecto (cadenas: se muestran en el notebook y se ejecutan en el build para calibrar la rúbrica)
# =====================================================================================================================
SOL_CHECKS = '''
# TODO 1 · atributos: UNK (con sugerencia), TYPE, SCOPE
def check_attributes(rec):
    F, a, st = [], rec["attributes"], span_type(rec)
    defined = SPANS[st]["attributes"] if st else {}
    for k, v in a.items():
        if k.startswith("gen_ai.") and k not in REG and not k.startswith("gen_ai.prompt.variable."):
            F.append(finding("UNK", k, "no existe en el registro actual" + (f"; usa {RENAMES[k]}" if k in RENAMES else "")))
        elif k in REG:
            if not type_ok(v, REG[k]["type"]): F.append(finding("TYPE", k, f"esperaba {REG[k]['type']}, llegó {type(v).__name__}"))
            if st and k not in defined: F.append(finding("SCOPE", k, f"no está definido para {st}"))
    return F

# TODO 2 · requeridos: REQ y ERR
def check_required(rec):
    F, a, st = [], rec["attributes"], span_type(rec)
    if st:
        F += [finding("REQ", k, f"requerido en {st}") for k, d in SPANS[st]["attributes"].items() if d["level"] == "required" and k not in a]
    if rec["status"] == "ERROR" and "error.type" not in a:
        F.append(finding("ERR", "error.type", "span en ERROR sin error.type"))
    return F

# TODO 3 · forma del span: NAME, KIND, CARD
def check_shape(rec):
    F, a, st = [], rec["attributes"], span_type(rec)
    op = a.get("gen_ai.operation.name")
    if st and op in NAME_PART:
        part = a.get(NAME_PART[op])
        if part is not None or op == "invoke_agent":
            expected = op + (f" {part}" if part else "")
            if rec["name"] != expected: F.append(finding("NAME", "name", f"esperado «{expected}», hay «{rec['name']}»"))
    if st:
        exp_kind = SPANS[st]["kind"].upper()
        if rec["kind"] != exp_kind and not (st == "gen_ai.client.inference" and rec["kind"] == "INTERNAL"):
            F.append(finding("KIND", "kind", f"{st} debería ser {exp_kind}"))
    if HIGH_CARD.search(rec["name"]): F.append(finding("CARD", "name", "el nombre del span contiene un identificador"))
    return F

# TODO 4 · valores: FINISH, TOK, CONV, PRIV
def check_values(rec):
    F, a = [], rec["attributes"]
    fr = a.get("gen_ai.response.finish_reasons")
    for x in (fr if isinstance(fr, (list, tuple)) else []):
        if x not in SPEC["finish_reason_enum"]: F.append(finding("FINISH", "gen_ai.response.finish_reasons", f"{x!r} no está en {SPEC['finish_reason_enum']}"))
    i = a.get("gen_ai.usage.input_tokens")
    if isinstance(i, int) and not isinstance(i, bool):
        for sub in ("gen_ai.usage.cache_read.input_tokens", "gen_ai.usage.cache_write.input_tokens"):
            if isinstance(a.get(sub), int) and a[sub] > i: F.append(finding("TOK", sub, f"{sub}={a[sub]} > input_tokens={i}"))
    if a.get("gen_ai.conversation.id") == rec["trace_id"]: F.append(finding("CONV", "gen_ai.conversation.id", "es el trace_id"))
    F += [finding("PRIV", k, f"contenido capturado ({len(str(a[k]))} car.)") for k in sorted(CONTENT_ATTRS & set(a))]
    return F
'''

SOL_MIGRATE = '''
# TODO 5 · migrar un span «legado» a la spec actual (devuelve una copia)
def migrate(rec):
    r = copy.deepcopy(rec); a = r["attributes"]
    for old, new in RENAMES.items():                                           # 1) renombres exactos
        if old in a and "(aprox.)" not in new: a[new] = a.pop(old)
    if "tool" in a and "gen_ai.tool.name" not in a: a["gen_ai.tool.name"] = a.pop("tool")      # 2) atributo propio -> estándar
    for k in list(a):                                                          # 3) tipos: números que llegaron como cadena
        if k in REG and REG[k]["type"] == "int" and isinstance(a[k], str) and a[k].isdigit(): a[k] = int(a[k])
    fr = a.get("gen_ai.response.finish_reasons")                               # 4) finish reasons al enum de la spec
    if isinstance(fr, list): a["gen_ai.response.finish_reasons"] = [normalize_finish("mock", x) for x in fr]
    for k in CONTENT_ATTRS & set(a): a.pop(k)                                  # 5) privacidad: la migración no arrastra contenido
    i = a.get("gen_ai.usage.input_tokens")                                     # 6) subconjuntos de tokens coherentes
    for sub in ("gen_ai.usage.cache_read.input_tokens", "gen_ai.usage.cache_write.input_tokens"):
        if isinstance(i, int) and isinstance(a.get(sub), int) and a[sub] > i: a.pop(sub)
    if a.get("gen_ai.conversation.id") == r["trace_id"]: a.pop("gen_ai.conversation.id")      # 7) conversación inventada
    if r["status"] == "ERROR" and "error.type" not in a: a["error.type"] = "_OTHER"          # 8) error sin clasificar
    op = a.get("gen_ai.operation.name")
    if op == "invoke_agent": r["kind"] = "INTERNAL"                            # 9) agente en proceso
    r["name"] = HIGH_CARD.sub("", r["name"]).strip()                           # 10) ids fuera del nombre
    return r
'''

SOL_USAGE = '''
# TODO 6a · uso de tokens de cada proveedor -> atributos de la spec
def usage_to_semconv(provider: str, usage: dict) -> dict:
    out = {}
    if provider == "anthropic":                                                # input_tokens EXCLUYE caché
        rd, wr = usage.get("cache_read_input_tokens", 0), usage.get("cache_creation_input_tokens", 0)
        out["gen_ai.usage.input_tokens"] = usage["input_tokens"] + rd + wr
        out["gen_ai.usage.output_tokens"] = usage["output_tokens"]
        if "cache_read_input_tokens" in usage: out["gen_ai.usage.cache_read.input_tokens"] = rd
        if "cache_creation_input_tokens" in usage: out["gen_ai.usage.cache_write.input_tokens"] = wr
    elif provider == "openai":                                                 # prompt_tokens YA incluye lo cacheado
        out["gen_ai.usage.input_tokens"], out["gen_ai.usage.output_tokens"] = usage["prompt_tokens"], usage["completion_tokens"]
        cached = usage.get("prompt_tokens_details", {}).get("cached_tokens")
        reasoning = usage.get("completion_tokens_details", {}).get("reasoning_tokens")
        if cached is not None: out["gen_ai.usage.cache_read.input_tokens"] = cached
        if reasoning is not None: out["gen_ai.usage.reasoning.output_tokens"] = reasoning
    elif provider == "ollama":
        out["gen_ai.usage.input_tokens"], out["gen_ai.usage.output_tokens"] = usage["prompt_eval_count"], usage["eval_count"]
    else:                                                                      # mock / SupportOps
        out["gen_ai.usage.input_tokens"], out["gen_ai.usage.output_tokens"] = usage["input_tokens"], usage["output_tokens"]
    return out

# TODO 6b · motivo de parada nativo -> enum de la spec (None -> "error"; lo desconocido se deja tal cual)
FINISH_MAP = {"openai": {"stop": "stop", "length": "length", "tool_calls": "tool_call", "function_call": "tool_call", "content_filter": "content_filter"},
              "anthropic": {"end_turn": "stop", "stop_sequence": "stop", "max_tokens": "length", "tool_use": "tool_call", "refusal": "content_filter"},
              "ollama": {"stop": "stop", "length": "length"}}
FINISH_MAP["mock"] = FINISH_MAP["openai"]

def normalize_finish(provider: str, reason):
    if not reason: return "error"
    return FINISH_MAP.get(provider, {}).get(reason, reason)
'''

SOL_POLICY = '''
# TODO 7 · política de contenido: redacción y almacén con referencia
EMAIL_RE = re.compile(r"[\\w.+-]+@[\\w-]+\\.[\\w.-]+")
CARD_RE = re.compile(r"\\b(?:\\d{4} ){3}\\d{4}\\b")
PHONE_RE = re.compile(r"\\+\\d{1,3}(?: \\d{2,4}){2,4}")

def redact_pii(text: str) -> str:
    text = CARD_RE.sub("[TARJETA]", text)                                      # primero tarjetas (también son dígitos con espacios)
    text = EMAIL_RE.sub("[EMAIL]", text)
    return PHONE_RE.sub("[TELEFONO]", text)

def to_vault(text: str, vault: dict) -> str:
    h = hashlib.sha256(text.encode()).hexdigest()[:16]; vault[h] = text       # el contenido (con su política de acceso) vive FUERA del span
    return json.dumps({"vault_ref": h})
'''

FINDING_SRC = '''
def finding(rule, attr, msg): return {"rule": rule, "severity": SEVERITY[rule], "attr": attr, "msg": msg}
'''


def _ns_for_reference() -> dict:
    """Espacio de nombres con la spec cargada y el linter/solución ejecutados: sirve para calibrar la rúbrica del proyecto."""
    import collections, copy, hashlib, re
    import pandas as pd
    spec = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    ns: dict = {"json": json, "re": re, "copy": copy, "hashlib": hashlib, "collections": collections, "pd": pd, "SPEC": spec, "REG": spec["attributes"], "SPANS": spec["spans"]}
    for src in (LINT_CONSTANTS, FINDING_SRC, LEGACY_SRC, LINT_FULL, SOL_USAGE, SOL_CHECKS, SOL_MIGRATE, SOL_POLICY):
        exec(src, ns)
    return ns


def _reference_04() -> dict:
    sys.path.insert(0, str(COURSE))
    os.environ.setdefault("LLM_PROVIDER", "mock")
    from supportops import DEFAULT_FAULT_RATES, SIM_EPOCH_S, SupportAgent, generate_tickets, run_tickets
    from supportops.telemetry import OTelInstrumentor, setup_telemetry
    ns = _ns_for_reference()
    tk = generate_tickets(60, seed=42, fault_rates=DEFAULT_FAULT_RATES, start_s=SIM_EPOCH_S)
    tel = setup_telemetry("ref", mode="memory", set_global=False, deterministic_ids=True)
    run_tickets(SupportAgent(instrumentor=OTelInstrumentor(tel)), tk)
    clean = tel.span_records()
    pairs = [ns["make_legacy"](s) for s in clean]
    legacy, planted = [p[0] for p in pairs], [p[1] for p in pairs]
    lint_span, migrate = ns["lint_span"], ns["migrate"]
    # consistencia: el linter monolítico de la lección == el linter por partes de la solución
    split = lambda r: sorted((f["rule"], f["attr"]) for f in ns["check_attributes"](r) + ns["check_required"](r) + ns["check_shape"](r) + ns["check_values"](r))   # noqa: E731
    mono = lambda r: sorted((f["rule"], f["attr"]) for f in lint_span(r))                                                                                       # noqa: E731
    assert all(split(r) == mono(r) for r in legacy + clean), "linter monolítico y por partes difieren"
    cnt = collections.Counter(c for p in planted for c in p)
    errs = ("REQ", "UNK", "TYPE", "TOK", "ERR"); warns = ("NAME", "KIND", "FINISH", "CARD", "CONV")
    mig_bad = sum(any(f["severity"] in ("error", "warn") for f in lint_span(migrate(r))) for r in legacy)
    clean_bad = sum(any(f["severity"] in ("error", "warn") for f in lint_span(r)) for r in clean)
    idem = sum(migrate(r) == r for r in clean)
    # política de contenido
    tk2 = generate_tickets(60, seed=42, fault_rates=DEFAULT_FAULT_RATES, pii_rate=0.3, start_s=SIM_EPOCH_S)
    def run(**kw):
        t = setup_telemetry("p", mode="memory", set_global=False)
        run_tickets(SupportAgent(instrumentor=OTelInstrumentor(t, **kw)), tk2); sp = t.span_records(); t.shutdown(); return sp
    raw, vault = run(capture_content=True), {}
    vlt = run(capture_content=True, redact=lambda s: ns["to_vault"](s, vault))
    size = lambda sp: sum(len(json.dumps(s["attributes"], ensure_ascii=False).encode()) for s in sp)           # noqa: E731
    pii = lambda sp: sum(bool(ns["EMAIL_RE"].search(json.dumps(s["attributes"], ensure_ascii=False))) for s in sp)   # noqa: E731
    red = run(capture_content=True, redact=ns["redact_pii"])
    cnt_red = sum(bool(ns["EMAIL_RE"].search(str(v)) or ns["PHONE_RE"].search(str(v)) or ns["CARD_RE"].search(str(v))) for s in red for k, v in s["attributes"].items() if k in ns["CONTENT_ATTRS"])
    assert cnt_red == 0 and all(json.loads(s["attributes"][k]) is not None for s in red for k in ns["CONTENT_ATTRS"] if k in s["attributes"]), "redact_pii de la solución falla"
    out = {"n_spans": len(clean), "n_legacy_defects": sum(len(p) for p in planted), "planted": dict(cnt),
           "planted_err": sum(cnt[c] for c in errs), "planted_warn": sum(cnt[c] for c in warns), "planted_priv": cnt["PRIV"],
           "n_planted_spans": sum(bool(p) for p in planted), "mig_bad": mig_bad, "clean_bad": clean_bad, "idem": idem,
           "size_raw": size(raw), "size_vault": size(vlt), "pii_raw": pii(raw), "pii_vault": pii(vlt), "n_tickets": len(tk2)}
    out["ratio"] = out["size_vault"] / out["size_raw"]
    assert mig_bad == 0 and clean_bad == 0 and idem == len(clean), (mig_bad, clean_bad, idem)
    tel.shutdown()
    return out


def build_project() -> None:
    ref = _reference_04()
    nb, out = nb_for(MOD, "04_proyecto_genai_semconv.ipynb", "Proyecto 04 · Modela SupportOps con las GenAI semconv y valídalo con un linter")
    md, code = nb.md, nb.code
    ratio_txt = f"{ref['ratio']:.0%}"
    rmax = max(25, int(ref["ratio"] * 100) + 10)

    md(f"""
    {nb.badge()}

    # Proyecto 04 · Modela cada paso del agente con las GenAI semantic conventions y valídalo con tu linter

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (todo en memoria; funciona en Colab) |
    | **RAM aproximada** | < 0,5 GB |
    | **Prerrequisitos** | Lección `04_genai_semconv` (spec, niveles de requisito, tokens, contenido) y módulo 03 (`OTelInstrumentor`) |
    | **Conexión** | Parte de **SupportOps v1** (módulo 03). Entrega un **linter reutilizable**, un **migrador** de nombres antiguos, la **normalización de uso de tokens** y la **política de contenido** que usarán los módulos 05 (Collector), 09 (métricas) y 20 (privacidad) |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Un segundo equipo (el de «Facturación IA») instrumentó su agente **a la antigua usanza**: `gen_ai.system`, `prompt_tokens`, motivos de parada nativos, ids en los nombres de span, contenido de los mensajes en los atributos…
    Los dashboards compartidos de coste y calidad **no funcionan con sus datos**. Tu trabajo: (1) **un linter** que mida cuánto se desvían de la spec oficial, (2) **un migrador** que los corrija en el camino, (3) la **normalización de uso y motivos de parada** para varios proveedores y (4) una **política de contenido** que no deje PII en los spans.

    ## Datos

    Spans generados por SupportOps con **semilla fija 42** ({ref['n_spans']} spans de 60 tickets): la versión *limpia* (`OTelInstrumentor`) y la versión *legada* (`make_legacy`, con **{ref['n_legacy_defects']} defectos plantados** en {ref['n_planted_spans']} spans). La spec es la instantánea oficial del módulo (`genai_semconv_snapshot.json`). Cadena de resiliencia: no necesita servicios, así que no hay modo degradado.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución, `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | Linter · reglas de **error** (`REQ`, `UNK`, `TYPE`, `TOK`, `ERR`) | Detecta los defectos plantados de esas reglas | {ref['planted_err']}/{ref['planted_err']} (100 % de *recall*) |
    | R2 | Linter · reglas de **aviso** (`NAME`, `KIND`, `FINISH`, `CARD`, `CONV`) | Detecta los defectos plantados | {ref['planted_warn']}/{ref['planted_warn']} (100 %) |
    | R3 | Linter · `PRIV` | Marca exactamente los spans con contenido capturado | {ref['planted_priv']} spans, sin falsos positivos |
    | R4 | Linter · precisión | Sobre los {ref['n_spans']} spans **limpios**: ningún error ni aviso | 0 spans marcados |
    | R5 | `migrate` | Tras migrar los spans legados, **0 errores y 0 avisos** | {ref['n_spans']}/{ref['n_spans']} spans limpios |
    | R6 | `migrate` es idempotente | Migrar un span ya correcto no lo cambia | {ref['idem']}/{ref['n_spans']} sin cambios |
    | R7 | `usage_to_semconv` | 4 formas de uso (OpenAI, Anthropic con caché, Ollama, mock) → atributos exactos | 4/4 |
    | R8 | `normalize_finish` | 12 motivos de parada (+ `None` → `error`) | 13/13 |
    | R9 | `redact_pii` | Sin correos, teléfonos ni tarjetas en el contenido capturado de {ref['n_tickets']} tickets con PII; el JSON sigue siendo válido | 0 PII, 100 % JSON válido |
    | R10 | `to_vault` | Spans con referencia: sin correos en claro, tamaño ≤ {rmax} % del de captura en atributos, y toda referencia existe en el almacén | cumple (solución: {ratio_txt}, de {ref['size_raw']:,} a {ref['size_vault']:,} bytes; {ref['pii_raw']} spans con correo → {ref['pii_vault']}) |

    > 📏 Los umbrales salen de lo que mide la solución de referencia con tiempo simulado y semilla fija; no dependen de tu máquina. Los defectos plantados son **deterministas** (dependen del `span_id` simulado).
    > **Honestidad sobre la validez:** las comprobaciones de R1–R6 miden *recall* sobre defectos que **nosotros** plantamos; un linter con 100 % aquí puede seguir dejando pasar defectos de otro tipo. Por eso R4 y la comparación con la implementación oficial (lección, sección 4) son parte del método.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + OTEL_IMPORTS + '''
STACK = check_stack([])                                         # este proyecto no necesita servicios
logging.getLogger("opentelemetry").setLevel(logging.ERROR)
''' + SPEC_LOADER)
    code(LINT_CONSTANTS + FINDING_SRC)
    md("""
    ## Los datos del proyecto

    `CLEAN` son spans conformes (los de `OTelInstrumentor`); `LEGACY` los deja «a la antigua usanza» y `PLANTED[span_id]` guarda **qué reglas debería detectar tu linter** en cada uno (la verdad de terreno de la rúbrica).
    """)
    code(LEGACY_SRC)
    code('''
tickets = generate_tickets(60, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, start_s=SIM_EPOCH_S)
tel = setup_telemetry("supportops-agent", mode="memory", set_global=False, deterministic_ids=True)      # ids deterministas: los defectos plantados son siempre los mismos
run_tickets(SupportAgent(instrumentor=OTelInstrumentor(tel)), tickets)
CLEAN = tel.span_records()
_pairs = [make_legacy(s) for s in CLEAN]
LEGACY, PLANTED = [p[0] for p in _pairs], {s["span_id"]: p[1] for s, p in zip(CLEAN, _pairs)}
print(len(CLEAN), "spans limpios ·", sum(bool(p) for p in PLANTED.values()), "legados con algún defecto ·", sum(len(p) for p in PLANTED.values()), "defectos plantados")
print("ejemplo de span legado:", {k: v for k, v in LEGACY[0]["attributes"].items() if k.startswith("gen_ai.")})
''')

    # ------------------------------------------------------------------------------------------------- linter
    md("""
    ## Paso 1 · El linter, por familias de reglas

    Tienes disponibles `SPEC`, `REG` (atributos), `SPANS` (tipos de span), `span_type(rec)`, `type_ok(valor, tipo)`, `RENAMES`, `NAME_PART`, `HIGH_CARD`, `CONTENT_ATTRS`, `SEVERITY` y `finding(regla, atributo, mensaje)`. Un *span* `rec` es un `dict` con `name`, `kind`, `status`, `trace_id`, `attributes`…
    Cada función devuelve una **lista de hallazgos** (`finding(...)`). La tabla de reglas está en la lección (sección 4).

    **TODO 1 · `check_attributes(rec)`:** `UNK` (atributo `gen_ai.*` que no existe en `REG`, sugiriendo `RENAMES[k]` si lo conoces), `TYPE` (valor que no cumple `type_ok`) y `SCOPE` (atributo del registro que no está definido para el tipo de span).
    """)
    md(hint(1, "Recorre `rec['attributes'].items()`. Un atributo es **desconocido** si empieza por `gen_ai.`, no está en `REG` y no empieza por `gen_ai.prompt.variable.` (es una plantilla). Si está en `REG`, comprueba el tipo con `type_ok(v, REG[k]['type'])`."))
    md(hint(2, "Para `SCOPE`: `st = span_type(rec)`; `defined = SPANS[st]['attributes'] if st else {}`; avisa si `k in REG` pero `k not in defined`."))
    code('''
def check_attributes(rec):
    # TODO 1
    raise NotImplementedError("TODO 1")
''')
    md("""
    **TODO 2 · `check_required(rec)`:** `REQ` por cada atributo con `level == "required"` en `SPANS[tipo]["attributes"]` que falte, y `ERR` si `rec["status"] == "ERROR"` y no hay `error.type`.
    """)
    md(hint(1, "`SPANS[st]['attributes']` es un dict `{atributo: {'level': 'required'|'conditionally_required'|'recommended'|'opt_in', ...}}`. Si `span_type(rec)` es `None` (operación desconocida) no hay requeridos que comprobar."))
    code('''
def check_required(rec):
    # TODO 2
    raise NotImplementedError("TODO 2")
''')
    md("""
    **TODO 3 · `check_shape(rec)`:** `NAME` (el nombre debe ser `{operación} {valor del atributo de NAME_PART[operación]}`; para `invoke_agent` sin nombre de agente basta `invoke_agent`; si falta el atributo del que depende el nombre, **no** avises), `KIND` (el *kind* del span debe ser `SPANS[tipo]["kind"].upper()`; para `gen_ai.client.inference` se admite también `INTERNAL`) y `CARD` (`HIGH_CARD.search(nombre)`).
    """)
    md(hint(1, "`op = a.get('gen_ai.operation.name')`; `part = a.get(NAME_PART[op])`; `expected = op + (' ' + part if part else '')`."))
    code('''
def check_shape(rec):
    # TODO 3
    raise NotImplementedError("TODO 3")
''')
    md("""
    **TODO 4 · `check_values(rec)`:** `FINISH` (cada valor de `gen_ai.response.finish_reasons` debe estar en `SPEC["finish_reason_enum"]`), `TOK` (`cache_read`/`cache_write` no pueden superar `gen_ai.usage.input_tokens`), `CONV` (`gen_ai.conversation.id` igual a `rec["trace_id"]`) y `PRIV` (un hallazgo por cada atributo de `CONTENT_ATTRS` presente).
    """)
    md(hint(1, "Comprueba antes de comparar que los valores son `int` (un `str` ya habrá dado `TYPE` en el TODO 1 y compararlo lanzaría una excepción). `CONTENT_ATTRS & set(a)` da los atributos de contenido presentes."))
    code('''
def check_values(rec):
    # TODO 4
    raise NotImplementedError("TODO 4")

def lint_span(rec):
    return check_attributes(rec) + check_required(rec) + check_shape(rec) + check_values(rec)

try:
    r0 = next(s for s in LEGACY if s["name"].startswith("chat"))
    print([ (f["rule"], f["attr"]) for f in lint_span(r0)])
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------------- migrate
    md("""
    ## Paso 2 · El migrador

    **TODO 5.** Implementa `migrate(rec) -> rec` (devuelve una **copia**; no mutes la entrada) que deje un span legado **sin errores ni avisos** del linter y que **no cambie** un span ya correcto (idempotente):

    1. aplica los **renombres exactos** de `RENAMES` (los que no son «aprox.»);
    2. `tool` → `gen_ai.tool.name`;
    3. números que llegaron como cadena → `int` (solo atributos que el registro declara `int`);
    4. `finish_reasons` al enum de la spec (usa `normalize_finish`, TODO 6b);
    5. **elimina** los atributos de contenido (una migración no debe arrastrar PII);
    6. quita `cache_read`/`cache_write` incoherentes (mayores que la entrada);
    7. quita `gen_ai.conversation.id` si es el `trace_id`;
    8. un span `ERROR` sin tipo recibe `error.type = "_OTHER"` (el valor de reserva de la spec);
    9. `invoke_agent` pasa a `INTERNAL` (nuestro agente es local);
    10. quita identificadores del nombre del span (`HIGH_CARD.sub("", nombre).strip()`).
    """)
    md(hint(1, "Empieza por `r = copy.deepcopy(rec)` y modifica `r['attributes']` en sitio. Itera sobre `list(a)` si vas a borrar claves mientras recorres."))
    md(hint(2, "Puedes escribir primero el TODO 6b (`normalize_finish`) y llamarlo desde aquí. Para la idempotencia, cada paso debe ser un no-op cuando el span ya cumple (p. ej. `if old in a`)."))
    code('''
def migrate(rec):
    # TODO 5
    raise NotImplementedError("TODO 5")
''')

    # ------------------------------------------------------------------------------------------------- usage
    md("""
    ## Paso 3 · Normalizar uso de tokens y motivos de parada

    **TODO 6a · `usage_to_semconv(provider, usage) -> dict`.** Dado el objeto de uso **tal como lo devuelve cada proveedor**, devuelve los atributos `gen_ai.usage.*` de la spec (solo los que el proveedor informa):

    | Proveedor | Forma del uso | Notas |
    |---|---|---|
    | `openai` | `prompt_tokens`, `completion_tokens`, `prompt_tokens_details.cached_tokens`, `completion_tokens_details.reasoning_tokens` | `prompt_tokens` **ya incluye** lo cacheado |
    | `anthropic` | `input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens` | `input_tokens` **excluye** caché → suma |
    | `ollama` | `prompt_eval_count`, `eval_count` | |
    | `mock` (SupportOps) | `input_tokens`, `output_tokens` | |

    **TODO 6b · `normalize_finish(provider, reason)`.** Traduce el motivo nativo al enum de la spec (`stop`, `length`, `tool_call`, `content_filter`, `error`): OpenAI/mock `stop`, `length`, `tool_calls`, `function_call`, `content_filter`; Anthropic `end_turn`, `stop_sequence`, `max_tokens`, `tool_use`, `refusal`; Ollama `stop`, `length`.
    `None` o vacío → `"error"` (la spec pide reportar `error` cuando se esperaba un motivo y no llegó); un valor desconocido se devuelve tal cual (así el linter lo señalará).
    """)
    md(hint(1, "Usa `usage.get('cache_read_input_tokens', 0)` para sumar sin fallar cuando el proveedor no informa caché, pero **solo escribe el atributo `cache_read`** si el proveedor lo informó."))
    md(hint(2, "Para los motivos, un diccionario por proveedor y `.get(reason, reason)`."))
    code('''
def usage_to_semconv(provider: str, usage: dict) -> dict:
    # TODO 6a
    raise NotImplementedError("TODO 6a")

def normalize_finish(provider: str, reason):
    # TODO 6b
    raise NotImplementedError("TODO 6b")

try:
    print(usage_to_semconv("anthropic", {"input_tokens": 50, "output_tokens": 30, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 20}))
    print(normalize_finish("anthropic", "tool_use"), normalize_finish("openai", None))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------------- policy
    md("""
    ## Paso 4 · Política de contenido

    Capturamos contenido (`capture_content=True`) de 60 tickets con **30 % de PII sintética** para probar la política.

    **TODO 7a · `redact_pii(text) -> str`:** sustituye **tarjetas** (`4000 0000 9705 5284`), **correos** y **teléfonos** (`+34 625 989 712`) por marcadores (`[TARJETA]`, `[EMAIL]`, `[TELEFONO]`). Cuidado con el **orden** (una tarjeta también «parece» un teléfono) y con los **falsos positivos**: un regex de teléfono demasiado general convierte en `[TELEFONO]` los números de seguimiento (`TRK…`) y las marcas de tiempo, y **rompe el JSON** del contenido (la rúbrica lo comprueba).
    **TODO 7b · `to_vault(text, vault) -> str`:** guarda `text` en el diccionario `vault` bajo un hash corto (p. ej. `sha256(...)[:16]`) y devuelve el JSON `{"vault_ref": "<hash>"}`, que es lo que irá al span (patrón 3 de la lección; la spec aún no define cómo referenciar contenido externo).
    """)
    md(hint(1, "Regex: correo `r\"[\\w.+-]+@[\\w-]+\\.[\\w.-]+\"`; tarjeta `r\"\\b(?:\\d{4} ){3}\\d{4}\\b\"`; teléfono internacional `r\"\\+\\d{1,3}(?: \\d{2,4}){2,4}\"` (exige el `+`: un patrón más general también cazaría números de seguimiento y marcas de tiempo y **rompería el JSON**). Aplica primero tarjeta."))
    code('''
import re, hashlib
tk_pii = generate_tickets(60, seed=SEED, fault_rates=DEFAULT_FAULT_RATES, pii_rate=0.3, start_s=SIM_EPOCH_S)

def redact_pii(text: str) -> str:
    # TODO 7a
    raise NotImplementedError("TODO 7a")

def to_vault(text: str, vault: dict) -> str:
    # TODO 7b
    raise NotImplementedError("TODO 7b")

EMAIL_RE = re.compile(r"[\\w.+-]+@[\\w-]+\\.[\\w.-]+"); PHONE_RE = re.compile(r"\\+\\d{1,3}(?: \\d{2,4}){2,4}"); CARD_RE = re.compile(r"\\b(?:\\d{4} ){3}\\d{4}\\b")   # (los usa la rúbrica para medir fugas)
def _pii_count(spans):                       # spans con PII en claro DENTRO de los atributos de contenido (los ids como resp_6ba07335… no son PII)
    txt = lambda x: " ".join(str(v) for k, v in x["attributes"].items() if k in CONTENT_ATTRS)
    return sum(bool(EMAIL_RE.search(txt(x)) or PHONE_RE.search(txt(x)) or CARD_RE.search(txt(x))) for x in spans)
try:
    print(redact_pii("Mi correo es ana@example.com y mi teléfono +34 625 989 712, tarjeta 4000 0000 9705 5284."))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    # ------------------------------------------------------------------------------------------------- rubric
    md("""
    ## Paso 5 · Rúbrica

    Ejecuta la celda para puntuar tu trabajo.
    """)
    code('''
def _spans_with_policy(**kw):
    t = setup_telemetry("policy", mode="memory", set_global=False)
    run_tickets(SupportAgent(instrumentor=OTelInstrumentor(t, **kw)), tk_pii); sp = t.span_records(); t.shutdown(); return sp

def run_rubric():
    rows = []
    def add(r, desc, ok, detail=""): rows.append({"criterio": r, "descripción": desc, "resultado": "✅ OK" if ok else "❌ FALLA", "detalle": detail})
    # ---- R1-R4: linter
    try:
        rules_of = lambda rec: {f["rule"] for f in lint_span(rec)}
        LF = {s["span_id"]: rules_of(s) for s in LEGACY}
        def rec_of(group):
            exp = [(sid, r) for sid, p in PLANTED.items() for r in p if r in group]; hit = sum(r in LF[sid] for sid, r in exp); return hit, len(exp)
        h, n = rec_of({"REQ", "UNK", "TYPE", "TOK", "ERR"}); add("R1", "reglas de error: defectos plantados detectados", h == n, f"{h}/{n}")
        h, n = rec_of({"NAME", "KIND", "FINISH", "CARD", "CONV"}); add("R2", "reglas de aviso: defectos plantados detectados", h == n, f"{h}/{n}")
        exp_priv = {sid for sid, p in PLANTED.items() if "PRIV" in p}; got_priv = {sid for sid, r in LF.items() if "PRIV" in r}
        add("R3", "PRIV exacto", exp_priv == got_priv, f"esperados {len(exp_priv)}, marcados {len(got_priv)}")
        bad = [s["name"] for s in CLEAN if any(f["severity"] in ("error", "warn") for f in lint_span(s))]
        add("R4", "spans limpios sin errores ni avisos", not bad, f"{len(bad)} marcados" + (f" (p. ej. {bad[0]})" if bad else ""))
    except Exception as e:
        for r in ("R1", "R2", "R3", "R4"): add(r, "linter", False, repr(e)[:80])
    # ---- R5-R6: migrador
    try:
        m = [migrate(s) for s in LEGACY]; bad = [s["name"] for s in m if any(f["severity"] in ("error", "warn") for f in lint_span(s))]
        add("R5", "tras migrar: 0 errores y 0 avisos", not bad, f"{len(m) - len(bad)}/{len(m)} limpios")
        same = sum(migrate(s) == s for s in CLEAN); add("R6", "migrate idempotente en spans correctos", same == len(CLEAN), f"{same}/{len(CLEAN)}")
    except Exception as e:
        for r in ("R5", "R6"): add(r, "migrate", False, repr(e)[:80])
    # ---- R7-R8: uso y motivos de parada
    try:
        cases = [("openai", {"prompt_tokens": 1200, "completion_tokens": 150, "prompt_tokens_details": {"cached_tokens": 900}, "completion_tokens_details": {"reasoning_tokens": 100}},
                  {"gen_ai.usage.input_tokens": 1200, "gen_ai.usage.output_tokens": 150, "gen_ai.usage.cache_read.input_tokens": 900, "gen_ai.usage.reasoning.output_tokens": 100}),
                 ("anthropic", {"input_tokens": 50, "output_tokens": 30, "cache_read_input_tokens": 100, "cache_creation_input_tokens": 20},
                  {"gen_ai.usage.input_tokens": 170, "gen_ai.usage.output_tokens": 30, "gen_ai.usage.cache_read.input_tokens": 100, "gen_ai.usage.cache_write.input_tokens": 20}),
                 ("ollama", {"prompt_eval_count": 90, "eval_count": 25}, {"gen_ai.usage.input_tokens": 90, "gen_ai.usage.output_tokens": 25}),
                 ("mock", {"input_tokens": 10, "output_tokens": 3}, {"gen_ai.usage.input_tokens": 10, "gen_ai.usage.output_tokens": 3})]
        ok = sum(usage_to_semconv(p, u) == e for p, u, e in cases); add("R7", "uso de tokens de 4 proveedores", ok == 4, f"{ok}/4")
        fin = [("openai", "stop", "stop"), ("openai", "length", "length"), ("openai", "tool_calls", "tool_call"), ("openai", "content_filter", "content_filter"), ("mock", "tool_calls", "tool_call"),
               ("anthropic", "end_turn", "stop"), ("anthropic", "max_tokens", "length"), ("anthropic", "tool_use", "tool_call"), ("anthropic", "refusal", "content_filter"),
               ("anthropic", "stop_sequence", "stop"), ("ollama", "stop", "stop"), ("ollama", "length", "length"), ("openai", None, "error")]
        ok = sum(normalize_finish(p, r) == e for p, r, e in fin); add("R8", "motivos de parada normalizados", ok == len(fin), f"{ok}/{len(fin)}")
    except Exception as e:
        for r in ("R7", "R8"): add(r, "uso/finish", False, repr(e)[:80])
    # ---- R9-R10: política de contenido
    try:
        raw = _spans_with_policy(capture_content=True)
        red = _spans_with_policy(capture_content=True, redact=redact_pii)
        def valid_json(sp): return all(json.loads(s["attributes"][k]) is not None for s in sp for k in CONTENT_ATTRS if k in s["attributes"])
        add("R9", "redact_pii: 0 PII y JSON válido", _pii_count(raw) > 0 and _pii_count(red) == 0 and valid_json(red), f"con PII en claro: {_pii_count(raw)} spans → tras redactar: {_pii_count(red)}")
        vault = {}; vlt = _spans_with_policy(capture_content=True, redact=lambda s: to_vault(s, vault))
        size = lambda sp: sum(len(json.dumps(s["attributes"], ensure_ascii=False).encode()) for s in sp)
        refs = [json.loads(s["attributes"][k])["vault_ref"] for s in vlt for k in CONTENT_ATTRS if k in s["attributes"]]
        ratio = size(vlt) / size(raw)
        add("R10", "almacén: sin correos en claro, tamaño reducido, referencias válidas", _pii_count(vlt) == 0 and ratio <= REF_RATIO_MAX and bool(refs) and all(r in vault for r in refs), f"tamaño = {ratio:.0%} del de captura en atributos")
    except Exception as e:
        for r in ("R9", "R10"): add(r, "política de contenido", False, repr(e)[:80])
    return pd.DataFrame(rows).set_index("criterio")

REF_RATIO_MAX = __RATIO_MAX__
display(run_rubric())
'''.replace("__RATIO_MAX__", f"{rmax / 100}"))

    md(f"""
    ---
    ## Retos extra (nivel experto)

    1. **Linter como `SpanProcessor` de aviso:** en lugar de analizar spans guardados, implementa un procesador que, al terminar cada span, ejecute `lint_span` y **cuente** los hallazgos con un `Counter` (y emita una métrica `supportops.semconv.findings{{rule}}`). ¿Qué coste añade por span? (mídelo como en el módulo 03).
    2. **Linter de métricas:** extiende el linter a nombres, unidades e instrumentos de métricas usando `SPEC["metrics"]` (p. ej. detectar `gen_ai.client.token.usage` como obsoleta).
    3. **Doble emisión:** modifica `OTelInstrumentor` (subclase) para emitir **también** `gen_ai.usage.prompt_tokens`/`completion_tokens` durante una transición, con una variable de entorno que lo active. Demuestra con el linter que los spans «dobles» generan `UNK` solo por los nombres antiguos.
    4. **Redacción más fina:** añade IBAN y DNI sintéticos a `redact_pii`, mide falsos positivos con números de pedido (`ORD-00017`) y razona la diferencia entre *redactar* (irreversible) y *seudonimizar* (hash con sal que permite correlacionar).
    5. **Contra el oráculo:** instala `opentelemetry-util-genai` y comprueba que su salida pasa tu linter para `invoke_agent`, `chat` y `execute_tool`; si alguna regla discrepa, decide quién tiene razón **leyendo la spec**.

    ## Reflexión (producción e hilo conductor)

    - Tu linter dio 100 % de *recall* sobre defectos que **plantamos nosotros**. ¿Qué tipos de defecto **no** puede detectar un linter basado en la spec (pista: valores correctos pero falsos, `gen_ai.request.model` equivocado, tokens mal contados por el proveedor)?
    - La spec está en `development`: ¿qué proceso pondrías para que una nueva versión de la spec no rompa tus dashboards (versión fijada, CI con el linter, doble emisión, fecha de retirada)?
    - El patrón 3 mueve la PII al almacén. ¿Quién debe poder leerlo, durante cuánto tiempo y cómo auditarías los accesos? (módulo 20)
    - En el módulo 05 pondrás un **Collector** entre los servicios y los backends: ¿qué parte de `migrate` y `redact_pii` preferirías ejecutar *en el Collector* y cuál *en el SDK*? ¿Por qué?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable, y la rúbrica con ella.
    """)
    code("# ===================== SOLUCIÓN DE REFERENCIA =====================\n" + SOL_USAGE.strip("\n") + "\n")
    code(SOL_CHECKS.strip("\n") + "\n\ndef lint_span(rec):\n    return check_attributes(rec) + check_required(rec) + check_shape(rec) + check_values(rec)\n")
    code(SOL_MIGRATE.strip("\n") + "\n")
    code(SOL_POLICY.strip("\n") + "\n")
    code('''
# Re-ejecuta la rúbrica con la solución
display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_readme() -> None:
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))["source"]
    (COURSE / MOD / "README.md").write_text(f"""# Módulo 04 · GenAI semantic conventions

🟡 Intermedio · ≈ 4 h 30 min · **No necesita servicios de Compose** (todo en memoria; funciona en Colab).

> ⚠️ **Estado de la spec:** las GenAI semantic conventions están en estado **Development** (inestables). Se contrastaron con la spec oficial el {snap['date']} (commit `{snap['commit'][:8]}` de [`open-telemetry/semantic-conventions-genai`]({snap['repo']})); el repositorio **se movió** desde `semantic-conventions/docs/gen-ai`.

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
""", encoding="utf-8")
    print("OK README 04")


if __name__ == "__main__":
    build_lesson()
    build_project()
    build_readme()
