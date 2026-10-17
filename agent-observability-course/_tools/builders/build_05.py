"""Genera el módulo 05_collector: README, lección y proyecto.  Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_05.py

Usa la instantánea `05_collector/collector_components_0.162.0.json` (salida de
`docker run --rm otel/opentelemetry-collector-contrib:0.162.0 components`, componentes y estabilidad por señal) que
alimenta el linter offline de configuraciones. Si hay Docker, el build comprueba además que la solución del proyecto
pasa `otelcol validate` y los controles funcionales de la rúbrica.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "05_collector"
SNAP_PATH = COURSE / MOD / "collector_components_0.162.0.json"
IMAGE = "otel/opentelemetry-collector-contrib:0.162.0"

OTEL_IMPORTS = '''
import json, re, shutil, subprocess, tempfile, time, uuid, logging, collections, pathlib, os, urllib.request, urllib.error
import yaml
from opentelemetry.trace import SpanKind
from opentelemetry._logs import SeverityNumber
from supportops.telemetry import setup_telemetry
'''

# ---------------------------------------------------------------------------------------------------------------------
# Piezas compartidas por lección y proyecto
# ---------------------------------------------------------------------------------------------------------------------
LAB_SRC = '''
IMAGE = "otel/opentelemetry-collector-contrib:0.162.0"        # la misma imagen (y versión) que usa el stack del curso

def docker_ok() -> bool:
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False

INTERNAL_TELEMETRY = """  telemetry:
    metrics:
      level: normal
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888
"""

class LabCollector:
    """Collector de laboratorio en un contenedor efímero con puertos de host ALEATORIOS (no choca con el stack del curso).
    Monta `config` y un directorio /out (para el exportador `file`). `with LabCollector(cfg) as lab:` -> lab.otlp_http, lab.read(...), lab.internal_metrics()."""
    def __init__(self, config: str, network: str | None = None):
        self.config, self.network = config, network
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="otelcol-lab-")); (self.dir / "out").mkdir(); os.chmod(self.dir / "out", 0o777)
        (self.dir / "config.yaml").write_text(config); os.chmod(self.dir / "config.yaml", 0o644)
        self.name = f"otelcol-lab-{uuid.uuid4().hex[:8]}"
    def __enter__(self):
        cmd = ["docker", "run", "-d", "--name", self.name, "-p", "127.0.0.1::4318", "-p", "127.0.0.1::4317", "-p", "127.0.0.1::8888",
               "-v", f"{self.dir / 'config.yaml'}:/etc/otelcol-contrib/config.yaml:ro", "-v", f"{self.dir / 'out'}:/out"]
        if self.network: cmd += ["--network", self.network]
        r = subprocess.run(cmd + [IMAGE, "--config=/etc/otelcol-contrib/config.yaml"], capture_output=True, text=True)
        if r.returncode: raise RuntimeError(r.stderr[:500])
        self.port = {p: int(subprocess.run(["docker", "port", self.name, f"{p}/tcp"], capture_output=True, text=True).stdout.split(":")[-1]) for p in (4318, 4317, 8888)}
        for _ in range(80):
            if "Everything is ready" in self.logs() or self.exited(): break
            time.sleep(0.25)
        if self.exited():
            msg = self.logs()[-800:]; self.__exit__()                       # limpia el contenedor fallido antes de informar
            raise RuntimeError("el Collector no arrancó:\\n" + msg)
        return self
    def exited(self) -> bool:
        return subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", self.name], capture_output=True, text=True).stdout.strip() != "true"
    def logs(self) -> str:
        r = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True); return r.stdout + r.stderr
    @property
    def otlp_http(self) -> str: return f"http://127.0.0.1:{self.port[4318]}"
    def internal_metrics(self) -> dict:
        """Métricas internas del Collector (otelcol_*) sumadas por nombre. Requiere el bloque `service.telemetry` (INTERNAL_TELEMETRY)."""
        txt = urllib.request.build_opener(urllib.request.ProxyHandler({})).open(f"http://127.0.0.1:{self.port[8888]}/metrics", timeout=5).read().decode()
        out: dict = {}
        for ln in txt.splitlines():
            if ln.startswith("otelcol_"):
                name, val = ln.rsplit(" ", 1); name = re.sub(r"\\{.*\\}", "", name); out[name] = out.get(name, 0.0) + float(val)
        return out
    def read(self, fname: str) -> list:
        p = self.dir / "out" / fname
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []
    def __exit__(self, *a):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True); shutil.rmtree(self.dir, ignore_errors=True)

def _kv(attrs): return {a["key"]: next(iter(a["value"].values())) for a in attrs}
def flat_spans(lines):
    """Líneas OTLP/JSON del exportador `file` -> lista de spans con su resource aplanado."""
    return [{"name": s["name"], "attrs": _kv(s.get("attributes", [])), "resource": _kv(rs["resource"].get("attributes", []))}
            for l in lines for rs in l.get("resourceSpans", []) for ss in rs["scopeSpans"] for s in ss["spans"]]
def flat_logs(lines):
    return [{"body": next(iter(r["body"].values())) if r.get("body") else "", "attrs": _kv(r.get("attributes", [])), "resource": _kv(rs["resource"].get("attributes", []))}
            for l in lines for rs in l.get("resourceLogs", []) for sl in rs["scopeLogs"] for r in sl["logRecords"]]
def flat_metrics(lines):
    return [{"name": m["name"], "resource": _kv(rs["resource"].get("attributes", []))} for l in lines for rs in l.get("resourceMetrics", []) for sm in rs["scopeMetrics"] for m in sm["metrics"]]

def send_probe(endpoint: str, n_chat: int = 5, n_health: int = 3, n_logs: int = 2) -> dict:
    """Envía telemetría de PRUEBA con los defectos que un Collector bien configurado debe corregir: PII (customer.email), un atributo de depuración
    (debug.prompt), nombres antiguos (gen_ai.system, gen_ai.usage.prompt_tokens) y ruido (spans «GET /healthz»). Devuelve lo enviado."""
    tel = setup_telemetry("supportops-probe", endpoint=endpoint, mode="otlp", set_global=False, metric_interval_s=1, keep_local=False)
    tr, lg = tel.tracer(), tel.logger()
    for i in range(n_chat):
        with tr.start_as_current_span("chat mock-small", kind=SpanKind.CLIENT, attributes={"gen_ai.operation.name": "chat", "gen_ai.system": "mock",
                "gen_ai.usage.prompt_tokens": 100 + i, "customer.email": f"cliente{i}@example.com", "debug.prompt": "texto largo de depuración"}): pass
    for _ in range(n_health):
        with tr.start_as_current_span("GET /healthz"): pass
    for i in range(n_logs):
        lg.emit(body="ticket recibido", severity_number=SeverityNumber.INFO, severity_text="INFO", attributes={"customer.email": f"cliente{i}@example.com"})
    tel.meter().create_counter("supportops.probe.requests").add(7)
    tel.force_flush(10); time.sleep(1.5); tel.force_flush(10); time.sleep(1.0)
    tel.shutdown()
    return {"chat": n_chat, "health": n_health, "logs": n_logs}

def to_file_config(cfg_text: str) -> str:
    """Deriva una config de PRUEBA de otra: mismos receptores/procesadores/pipelines, pero los exportadores pasan a ser `file` (sin backends)."""
    cfg = yaml.safe_load(cfg_text)
    cfg["exporters"] = {f"file/{s}": {"path": f"/out/{s}.jsonl"} for s in ("traces", "metrics", "logs")}
    for name, p in cfg["service"]["pipelines"].items(): p["exporters"] = [f"file/{name.split('/')[0]}"]
    tele = cfg["service"].setdefault("telemetry", {}); tele.setdefault("metrics", {"level": "normal", "readers": [{"pull": {"exporter": {"prometheus": {"host": "0.0.0.0", "port": 8888}}}}]})
    return yaml.safe_dump(cfg, sort_keys=False)
'''

CFGLINT_SRC = '''
COMP = json.loads((ROOT / "05_collector" / "collector_components_0.162.0.json").read_text())      # componentes de la distribución contrib 0.162.0 y su estabilidad por señal
SECTIONS = ("receivers", "processors", "exporters", "connectors", "extensions")
ALIASES = {"otlphttp": "otlp_http", "prometheusremotewrite": "prometheus_remote_write", "spanmetrics": "span_metrics", "servicegraph": "service_graph", "k8sattributes": "k8s_attributes",
           "resourcedetection": "resource_detection", "filelog": "file_log", "hostmetrics": "host_metrics", "loadbalancing": "load_balancing", "metricstransform": "metrics_transform"}
EXPORTER_ALIAS = {"otlp": "otlp_grpc"}                                   # como EXPORTADOR, `otlp` es el nombre antiguo de otlp_grpc (como receptor sigue siendo `otlp`)
CFG_SEVERITY = {"PARSE": "error", "NOPIPE": "error", "UNKNOWN": "error", "UNDEF": "error", "SIGNAL": "error", "MLCFG": "error",
                "ALIAS": "warn", "UNUSED": "warn", "ORDER": "warn", "NOML": "warn", "EXPQ": "warn", "BIND": "warn", "SECRET": "warn", "NULL": "warn",
                "NOBATCH": "info", "HEALTH": "info"}
PHASE = {"memory_limiter": 1, "filter": 2, "probabilistic_sampler": 2, "tail_sampling": 2, "k8s_attributes": 3, "resource_detection": 3,
         "attributes": 4, "resource": 4, "transform": 4, "redaction": 4, "span": 4, "group_by_attrs": 4, "metrics_transform": 4, "batch": 5}
NETWORK_EXPORTERS = {"otlp_grpc", "otlp_http", "otlp", "otlphttp", "prometheus_remote_write", "prometheusremotewrite", "kafka", "load_balancing"}

def ctype(key: str) -> str: return key.split("/", 1)[0]

def cfglint(cfg_text: str) -> list:
    """Hallazgos [{rule, severity, where, msg}] de una configuración del Collector SIN ejecutar el Collector."""
    F = []
    def add(rule, where, msg): F.append({"rule": rule, "severity": CFG_SEVERITY[rule], "where": where, "msg": msg})
    try:
        cfg = yaml.safe_load(cfg_text); assert isinstance(cfg, dict)
    except Exception as e:
        add("PARSE", "yaml", f"no es un YAML de mapa válido: {str(e)[:80]}"); return F
    for sec in SECTIONS:                                                                   # 1) secciones nulas («processors:» vacío)
        if sec in cfg and cfg[sec] is None: add("NULL", sec, f"«{sec}:» vacío (null); usa {{}} o elimínalo")
    defined = {s: dict(cfg.get(s) or {}) for s in SECTIONS}
    for sec, items in defined.items():                                                     # 2) tipos de componente que existen en la distribución
        for key in items:
            t = ctype(key)
            if t in COMP[sec]: continue
            alias = ALIASES.get(t) or (EXPORTER_ALIAS.get(t) if sec == "exporters" else None)
            if alias and alias in COMP[sec]: add("ALIAS", f"{sec}.{key}", f"nombre antiguo: el canónico hoy es «{alias}» (puede aceptarse como alias; no cuentes con ello)")
            else: add("UNKNOWN", f"{sec}.{key}", f"«{t}» no existe en la distribución contrib {COMP['version']}")
    svc = cfg.get("service") or {}; pipes = svc.get("pipelines") or {}
    if not pipes: add("NOPIPE", "service.pipelines", "el servicio necesita al menos un pipeline")
    used = {s: set() for s in SECTIONS}
    for pname, p in pipes.items():                                                         # 3) referencias, señales y orden
        sig = ctype(pname); p = p or {}
        for sec in ("receivers", "processors", "exporters"):
            for key in p.get(sec) or []:
                used[sec].add(key)
                if key not in defined[sec]:
                    add("UNDEF", f"pipelines.{pname}.{sec}", f"referencia a «{key}», que no está configurado en «{sec}»"); continue
                t = ALIASES.get(ctype(key), EXPORTER_ALIAS.get(ctype(key), ctype(key)) if sec == "exporters" else ctype(key))
                st = COMP[sec].get(t)
                if st and sig in ("traces", "metrics", "logs") and sig not in st: add("SIGNAL", f"pipelines.{pname}.{sec}", f"«{key}» no soporta la señal {sig}")
        procs = [ctype(k) for k in p.get("processors") or []]
        if "memory_limiter" not in procs: add("NOML", f"pipelines.{pname}", "sin memory_limiter: el Collector no se protege de quedarse sin memoria")
        ph = [(PHASE[t], t) for t in procs if t in PHASE]
        for (a, ta), (b, tb) in zip(ph, ph[1:]):
            if a > b: add("ORDER", f"pipelines.{pname}.processors", f"«{tb}» debería ir antes que «{ta}» (memory_limiter → filtros/muestreo → contexto → enriquecimiento → batch)")
        has_q_batch = any(((defined["exporters"].get(k) or {}).get("sending_queue") or {}).get("batch") is not None for k in p.get("exporters") or [])
        if "batch" not in procs and not has_q_batch: add("NOBATCH", f"pipelines.{pname}", "sin batch (ni procesador ni sending_queue.batch): más peticiones y peor compresión")
    for sec in ("receivers", "processors", "exporters"):
        for key in defined[sec]:
            if key not in used[sec]: add("UNUSED", f"{sec}.{key}", "definido pero no usado en ningún pipeline: el Collector lo ignora en silencio")
    for key, c in defined["processors"].items():                                           # 4) configuración de componentes concretos
        if ctype(key) == "memory_limiter" and not ((c or {}).get("limit_mib") or (c or {}).get("limit_percentage")):
            add("MLCFG", f"processors.{key}", "memory_limiter sin limit_mib ni limit_percentage (el Collector lo rechaza)")
    for key, c in defined["exporters"].items():
        if ctype(key) in NETWORK_EXPORTERS and (((c or {}).get("sending_queue") or {}).get("enabled") is False):
            add("EXPQ", f"exporters.{key}", "sending_queue desactivada en un exportador de red: sin búfer ante caídas del backend")
    exts = svc.get("extensions") or []
    for e in exts:
        if e not in defined["extensions"]: add("UNDEF", "service.extensions", f"referencia a «{e}», que no está configurada")
    if not any(ctype(e) == "health_check" for e in exts): add("HEALTH", "service.extensions", "sin health_check: no hay endpoint de salud para sondas")
    for key, c in defined["extensions"].items():
        if ctype(key) in ("pprof", "zpages") and "0.0.0.0" in json.dumps(c or {}): add("BIND", f"extensions.{key}", "pprof/zpages escuchando en 0.0.0.0: expónlo solo en localhost")
    for m in re.finditer(r"(?im)^\\s*(authorization|api[_-]?key|password|token|secret)\\s*:\\s*(?!\\$\\{)(\\S{6,})", cfg_text):
        add("SECRET", m.group(1), "valor literal con aspecto de credencial: usa ${env:NOMBRE}")
    return F
'''

# La configuración del stack (A1) y la de la solución del proyecto
SOLUTION_CONFIG = '''# Collector del alumno · gateway del laboratorio SupportOps
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  memory_limiter:                 # 1.º: protege al Collector (límite duro 400 MiB, margen para picos 80 MiB = 20 %)
    check_interval: 1s
    limit_mib: 400
    spike_limit_mib: 80
  filter/health:                  # 2.º: descarta ruido ANTES de gastar CPU en el resto
    error_mode: ignore
    traces:
      span:
        - 'name == "GET /healthz"'
  attributes/pii:                 # PII: el correo se seudonimiza (hash) y el atributo de depuración se elimina
    actions:
      - key: customer.email
        action: hash
      - key: debug.prompt
        action: delete
  resource/lab:                   # etiqueta de entorno del laboratorio del alumno
    attributes:
      - key: deployment.environment.name
        value: lab-student
        action: upsert
  transform/semconv:              # migración a la spec GenAI actual (módulo 04): renombres en spans
    error_mode: ignore
    trace_statements:
      - set(span.attributes["gen_ai.provider.name"], span.attributes["gen_ai.system"]) where span.attributes["gen_ai.system"] != nil
      - delete_key(span.attributes, "gen_ai.system")
      - set(span.attributes["gen_ai.usage.input_tokens"], span.attributes["gen_ai.usage.prompt_tokens"]) where span.attributes["gen_ai.usage.prompt_tokens"] != nil
      - delete_key(span.attributes, "gen_ai.usage.prompt_tokens")
  batch:                          # último: agrupa lo que ya está filtrado y transformado
    timeout: 1s
    send_batch_size: 512

exporters:
  otlp_grpc/tempo:                # trazas -> Tempo (OTLP/gRPC dentro de la red de Compose)
    endpoint: tempo:4317
    tls:
      insecure: true
    sending_queue:
      enabled: true
      queue_size: 2000
    retry_on_failure:
      enabled: true
      max_elapsed_time: 120s
  otlp_http/loki:                 # logs -> Loki (endpoint OTLP nativo: el exportador añade /v1/logs)
    endpoint: http://loki:3100/otlp
    sending_queue:
      enabled: true
      queue_size: 2000
    retry_on_failure:
      enabled: true
      max_elapsed_time: 120s
  otlp_http/prometheus:           # métricas -> receptor OTLP de Prometheus (/api/v1/otlp/v1/metrics)
    endpoint: http://prometheus:9090/api/v1/otlp
    sending_queue:
      enabled: true
      queue_size: 2000
    retry_on_failure:
      enabled: true
      max_elapsed_time: 120s

extensions:
  health_check:
    endpoint: 0.0.0.0:13133

service:
  extensions: [health_check]
  telemetry:
    metrics:
      level: normal
      readers:
        - pull:
            exporter:
              prometheus:
                host: 0.0.0.0
                port: 8888
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, filter/health, attributes/pii, resource/lab, transform/semconv, batch]
      exporters: [otlp_grpc/tempo]
    logs:
      receivers: [otlp]
      processors: [memory_limiter, attributes/pii, resource/lab, batch]
      exporters: [otlp_http/loki]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, resource/lab, batch]
      exporters: [otlp_http/prometheus]
'''


# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "05_collector.ipynb", "Módulo 05 · El OpenTelemetry Collector")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 05 · El OpenTelemetry Collector: receivers, processors, exporters y pipelines

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Los experimentos usan **contenedores efímeros del Collector** (solo Docker, **no** necesitan el stack). Opcional `--profile core --profile metrics` para ver el stack real. **Sin Docker:** modo degradado con resultados pregrabados y el linter de configuraciones (offline) |
    | **RAM aproximada** | ≈ 0,1 GB por Collector de laboratorio; con el stack `core` + `metrics` ≈ 0,5 GB |
    | **Prerrequisitos** | Módulo 03 (OTLP, `BatchSpanProcessor`), módulo 04 (renombres y PII a corregir en el camino), módulo 00 (Docker/Compose) |
    | **Hilo conductor** | Hasta ahora SupportOps enviaba al Collector «del stack». Hoy abres la caja: entiendes cada línea de su configuración, la **validas**, la **rompes a propósito** y diseñas la tuya |

    > ⚠️ **Versión.** Todo está verificado con **`otel/opentelemetry-collector-contrib:0.162.0`** (la imagen del stack). El Collector sigue en versión `0.x`: los nombres de componente y de opciones **cambian** (de hecho, los nombres canónicos de varios exportadores ahora llevan guion bajo: `otlp_grpc`, `otlp_http`…). Fija siempre la versión y lee las notas de cada actualización.
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Explicar** por qué se pone un Collector entre las aplicaciones y los backends y **comparar** los patrones *sin Collector*, *agente* y *gateway*.
    2. **Describir** los componentes (receivers, processors, exporters, connectors, extensions), el `service` y cómo se componen los *pipelines* por señal, incluyendo la semántica de *fan-out* y de instancias por pipeline.
    3. **Ordenar** los procesadores según la práctica recomendada oficial y **demostrar** (con una versión «de juguete» hecha a mano) qué se pierde si se ordenan mal.
    4. **Configurar** `memory_limiter`, `batch`, `attributes`, `resource`, `filter` y `transform` y **verificar** su efecto sobre telemetría real de SupportOps (PII, nombres antiguos, ruido).
    5. **Validar** una configuración con `otelcol validate` y con un **linter offline** propio; **interpretar** los errores típicos.
    6. **Medir** el comportamiento ante sobrecarga y caídas (rechazo por memoria, cola de envío, reintentos) con las **métricas internas** del Collector (`otelcol_*`).
    7. **Dimensionar** colas y límites con cálculos y **decidir** cuándo escalar (y cuándo no).
    8. **Exportar** trazas, métricas y logs a Tempo, Loki y Prometheus y comprobar que no se pierde ningún dato (conservación de spans).
    """)

    md("""
    ## 🔁 Conexión con módulos anteriores
    """)
    md(details("1 · (Módulo 03, Cálculo) 100 réplicas del agente, cada una con un `BatchSpanProcessor` por defecto (lotes de hasta 512 spans, un envío cada 5 s), producen en total 1 280 spans/s. ¿Cuántas peticiones por segundo recibe el Collector? Si su `batch` agrupa de 512 en 512, ¿cuántas peticiones por segundo salen hacia el backend y qué ganas?",
               "Cada réplica envía ≈ 1 petición cada 5 s ⇒ 100/5 = **20 peticiones/s** de ≈ 64 spans (1280/20). El `batch` del Collector junta lotes de 512 ⇒ 1280/512 = **2,5 peticiones/s** hacia el backend: **8× menos** peticiones, más grandes, que comprimen mejor y cuestan menos al backend. Son dos niveles de agrupación: el del SDK dentro de cada proceso y el del Collector entre muchos procesos (lo medirás en 4.1)."))
    md(details("2 · (Módulo 03) ¿Qué ocurre en el SDK cuando el Collector rechaza datos con un 503?",
               "El exportador OTLP reintenta con *backoff*; si el rechazo persiste, el lote se descarta y el SDK lo registra en su log. Con el `BatchSpanProcessor`, además, la cola local se puede llenar y descartar los spans más antiguos. Hoy verás el **otro lado**: por qué el Collector devuelve ese 503."))
    md(details("3 · (Módulo 04) ¿Qué dos problemas de los spans «de otro equipo» (nombres antiguos y PII) conviene corregir en el Collector y no en cada aplicación?",
               "Los **renombres** de atributos (`gen_ai.system` → `gen_ai.provider.name`…) durante una migración, y la **redacción/seudonimización** de PII: ambos se aplican de forma centralizada y sin redesplegar a todos los equipos."))

    code(boot("viz,otel"))
    code(IMPORTS + OTEL_IMPORTS + '''
STACK = check_stack(["collector", "tempo", "loki", "prometheus"])
logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)
''' + LAB_SRC + '''
DOCKER = docker_ok()
print("Docker disponible:", DOCKER, "·", "experimentos en vivo con el Collector real" if DOCKER else "MODO DEGRADADO: resultados pregrabados (mismo formato)")
''')

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ---
    # 1 · Intuición: ¿por qué un Collector en medio?

    Con el SDK podrías enviar directamente al backend (Tempo, Loki…). Funciona… hasta que quieres cambiar de backend, filtrar datos sensibles, añadir metadatos comunes o proteger el backend de una avalancha.
    El **Collector** es un proceso (un binario) que **recibe**, **procesa** y **exporta** telemetría: un *middleware* de telemetría.

    | Si vienes de… | Analogía |
    |---|---|
    | **ML** | Un `sklearn.Pipeline`: cargadores → transformadores en orden → estimador final. El **orden** de los pasos cambia el resultado (igual que aquí). |
    | **Backend** | Un *API gateway* o *sidecar proxy* (Envoy): un punto único donde aplicas reglas (autenticación, reintentos, límites, *routing*) sin tocar las aplicaciones. |
    | **SRE / datos** | Un *log shipper* (Fluent Bit/Vector) o un ETL: *extract* (receivers) → *transform* (processors) → *load* (exporters). |
    """)
    code('''
fig, ax = viz.canvas(15, 6.2, xlim=(0, 150), ylim=(0, 62))
ax.add_patch(plt.Rectangle((38, 3), 76, 56, fill=False, ec=viz.PALETTE["metrics"], lw=2, ls="--")); ax.text(40, 56, "Collector (otelcol-contrib)", fontsize=10, fontweight="bold", color=viz.PALETTE["metrics"])
apps = [viz.box(ax, 2, 40 - i * 14, 26, 9, t, viz.PALETTE["neutral"], fontsize=8) for i, t in enumerate(["supportops-agent\\n(SDK OTLP)", "orquestador\\n(SDK OTLP)", "servidor MCP\\n(SDK OTLP)"])]
rec = viz.box(ax, 42, 26, 17, 14, "RECEIVER\\notlp\\n:4317 gRPC\\n:4318 HTTP", viz.PALETTE["metrics"], fontsize=8)
rows = {"traces": (44, viz.PALETTE["traces"]), "metrics": (30, viz.PALETTE["metrics"]), "logs": (16, viz.PALETTE["logs"])}
procs = {}
for sig, (y, c) in rows.items():
    procs[sig] = viz.box(ax, 66, y - 5, 28, 9, "memory_limiter → … → batch", c, fontsize=8)
    viz.arrow(ax, viz.right(rec), viz.left(procs[sig]), "", color=c)
tgt = {"traces": "Tempo", "metrics": "Prometheus", "logs": "Loki"}
for sig, (y, c) in rows.items():
    b = viz.box(ax, 120, y - 5, 27, 9, f"{tgt[sig]}\\n(exporter {sig})", c, fontsize=8)
    viz.arrow(ax, viz.right(procs[sig]), viz.left(b), sig, color=c)
for a in apps: viz.arrow(ax, viz.right(a), viz.left(rec), "", color=viz.PALETTE["neutral"])
ax.text(2, 4, "Un pipeline por señal · todos comparten el receptor OTLP · los procesadores forman una cadena ORDENADA", fontsize=9, style="italic", color=viz.PALETTE["neutral"])
plt.show()
''')
    md(observe("""
    - Las aplicaciones solo conocen **un endpoint OTLP** (`:4318`/`:4317`); no saben nada de Tempo, Loki ni Prometheus. Cambiar de backend es cambiar el `exporter` del Collector, **sin redesplegar** a nadie.
    - Hay **tres pipelines independientes** (trazas, métricas, logs) que comparten el receptor. Lo que le pase a uno (por ejemplo, un exportador lento) puede afectar a los demás **si comparten receptor**: lo verás en el experimento del *fan-out*.
    - El Collector es el sitio natural para **políticas transversales**: seudonimizar PII, descartar ruido, añadir `deployment.environment.name`, reintentar, poner en cola (módulos 18 y 20 lo explotan).
    """))

    md("""
    ### ¿Y si no uso Collector?

    La propia documentación del proyecto lo resume así ([*No Collector*](https://opentelemetry.io/docs/collector/deploy/other/no-collector/)): **ventaja**: sencillo, sin piezas extra (bueno en desarrollo y pruebas). **Inconvenientes**: cualquier cambio de recogida, procesamiento o ingestión exige **cambiar código**; **acoplamiento fuerte** entre aplicación y backend; y cada lenguaje soporta pocos exportadores. En producción casi todos acaban poniendo un Collector.

    ### Patrones de despliegue

    | Patrón | Qué es | Cuándo |
    |---|---|---|
    | **Agente** | Un Collector **junto a cada aplicación**: *sidecar* (un contenedor extra al lado de tu app) o *DaemonSet* (Kubernetes lanza un pod por máquina/nodo; lo verás en el módulo 19: piensa en «un proceso de monitoreo por servidor») | Baja latencia local, enriquecer con metadatos del host/pod, aislar fallos de red |
    | **Gateway** | Uno o más Collectors **centrales** con un único endpoint OTLP (por clúster/región), detrás de un balanceador | Políticas centrales (redacción, muestreo, enrutado), pocas conexiones salientes a los backends |
    | **Dos niveles** | Capa 1 con el exportador `load_balancing` (por `traceID`) → capa 2 con *tail sampling* | Cuando todos los spans de una traza deben llegar al **mismo** Collector (módulo 18) |

    En el laboratorio usamos **un gateway** (el del stack). En producción lo habitual es **agente + gateway**: el agente añade contexto local y reenvía por OTLP al gateway, que aplica las políticas.
    """)
    code('''
fig, ax = viz.canvas(15, 5.6, xlim=(0, 150), ylim=(0, 56))
def col(x, title, items, c):
    ax.text(x, 52, title, fontsize=10, fontweight="bold", color=c)
    return [viz.box(ax, x, 38 - i * 12, 22, 8, t, c, fontsize=8) for i, t in enumerate(items)]
apps = col(1, "Aplicaciones", ["agente A", "agente B", "orquestador"], viz.PALETTE["neutral"])
ag = col(34, "Capa agente (sidecar/nodo)", ["Collector\\nagente 1", "Collector\\nagente 2", "Collector\\nagente 3"], viz.PALETTE["logs"])
lb = viz.box(ax, 67, 26, 20, 10, "Collector\\nGATEWAY\\n(load_balancing)", viz.PALETTE["metrics"], fontsize=8)
t2 = col(95, "Capa 2 (réplicas)", ["gateway-1\\n(tail sampling)", "gateway-2\\n(tail sampling)"], viz.PALETTE["metrics"])
be = viz.box(ax, 125, 24, 23, 14, "Backends\\nTempo · Loki\\nPrometheus", viz.PALETTE["traces"], fontsize=8)
for a, g in zip(apps, ag): viz.arrow(ax, viz.right(a), viz.left(g), "OTLP", color=viz.PALETTE["neutral"])
for g in ag: viz.arrow(ax, viz.right(g), viz.left(lb), "", color=viz.PALETTE["logs"])
for t in t2: viz.arrow(ax, viz.right(lb), viz.left(t), "por traceID", color=viz.PALETTE["metrics"], fontsize=7)
for t in t2: viz.arrow(ax, viz.right(t), viz.left(be), "", color=viz.PALETTE["traces"])
ax.text(2, 4, "Nuestro laboratorio: aplicaciones → 1 gateway → backends (las capas agente y 2 son para producción, módulos 18 y 19)", fontsize=9, style="italic", color=viz.PALETTE["neutral"])
plt.show()
''')
    md(observe("""
    - En el patrón de **dos niveles** el balanceo es *por traza* (`routing_key: traceID`): así todos los spans de una traza acaban en la misma réplica, requisito del *tail sampling* (que decide mirando la traza completa).
    - Para el **resto** de casos basta un balanceador normal delante de réplicas idénticas (pero cuidado con componentes con estado, como los `scrapers` de Prometheus, que hay que repartir entre instancias).
    - Cada capa añade latencia, un punto de fallo y trabajo de operación. **No añadas capas «por si acaso».**
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ---
    # 2 · Teoría: componentes, pipelines y orden

    Un Collector se define en **un YAML** con cinco secciones de componentes y una sección `service` que los **activa**:

    | Sección | Qué es | Ejemplos (contrib 0.162) |
    |---|---|---|
    | `receivers` | Reciben o **obtienen** (scrapers) datos | `otlp`, `prometheus`, `file_log`, `host_metrics` |
    | `processors` | Transforman, filtran, enriquecen, agrupan (**en cadena**) | `memory_limiter`, `batch`, `attributes`, `resource`, `filter`, `transform`, `tail_sampling` |
    | `exporters` | Envían fuera del Collector | `otlp_grpc`, `otlp_http`, `prometheus`, `prometheus_remote_write`, `debug`, `file` |
    | `connectors` | Exportador de un pipeline **y** receptor de otro (convierten señales) | `span_metrics` (trazas → métricas RED), `forward`, `routing` |
    | `extensions` | Capacidades auxiliares (no tocan datos) | `health_check`, `file_storage`, `pprof`, `zpages` |
    | `service` | **Activa** componentes: `extensions`, `pipelines`, `telemetry` (métricas/logs internos) | |

    **Reglas que explican casi todos los errores de configuración:**

    1. **Definir no es activar.** Un componente solo funciona si aparece en un pipeline (o en `service.extensions`). Uno definido y no usado se **ignora en silencio** (lo comprobamos más abajo).
    2. **Un pipeline = una señal** (`traces`, `metrics`, `logs`; puedes tener varios con sufijo: `traces/otro`). Todo componente del pipeline debe **soportar** esa señal.
    3. Los nombres tienen forma **`tipo[/nombre]`**: `otlp_http/loki` y `otlp_http/prometheus` son dos exportadores del mismo tipo con distinta configuración.
    4. **Fan-out:** el mismo receptor en varios pipelines produce **una sola instancia** que reparte a cada pipeline; cada exportador recibe **una copia** de cada dato.
    5. **Instancias por pipeline:** el mismo procesador en dos pipelines son **dos instancias independientes** con su propio estado (dos `batch` distintos).
    6. **Orden:** los procesadores se ejecutan **en el orden de la lista**.

    ### El orden recomendado (documentación oficial del proyecto)

    1. `memory_limiter` — **el primero**: debe poder rechazar carga antes de que los siguientes acumulen datos que no pueden vaciar.
    2. Procesadores que **descartan** (filtros, muestreo): tira lo que no quieres cuanto antes.
    3. Procesadores que dependen del **contexto de origen** (p. ej. `k8s_attributes`): antes de `batch`, porque agrupar **borra el contexto de la petición**.
    4. Procesadores que **transforman o enriquecen** (`attributes`, `resource`, `transform`): solo sobre lo que se va a exportar.
    5. `batch` — **al final**: no agrupes lo que luego se va a descartar o modificar. (Y, cuando el exportador lo permita, es preferible usar su propio *batching*, ver 4.4.)
    """)
    code('''
fig, ax = viz.canvas(15, 4.4, xlim=(0, 150), ylim=(0, 44))
stages = [("1 · memory_limiter", "protege al Collector\\n(rechaza = backpressure)", viz.PALETTE["error"]), ("2 · filtros / muestreo", "filter, probabilistic_sampler\\n(tira lo que sobra)", viz.PALETTE["warn"]),
          ("3 · contexto de origen", "k8s_attributes, resource_detection\\n(antes de batch)", viz.PALETTE["logs"]), ("4 · enriquecer/transformar", "attributes, resource, transform,\\nredaction", viz.PALETTE["traces"]), ("5 · batch", "agrupa lo ya depurado\\n(mejor compresión)", viz.PALETTE["metrics"])]
bs = [viz.box(ax, 1 + i * 29.5, 14, 26, 16, f"{t}\\n\\n{d}", c, fontsize=8) for i, (t, d, c) in enumerate(stages)]
for a, b in zip(bs, bs[1:]): viz.arrow(ax, viz.right(a), viz.left(b), "", color=viz.PALETTE["neutral"])
ax.text(1, 36, "receiver → ", fontsize=10); ax.text(131, 36, "→ exporter(s)", fontsize=10)
ax.text(1, 6, "Orden recomendado en la documentación del proyecto (README de processors): el orden de la lista ES el orden de ejecución.", fontsize=9, style="italic", color=viz.PALETTE["neutral"])
plt.show()
''')
    md("""
    ### Configuración como código: sustitución de variables, varios ficheros, validación

    - **Variables de entorno:** `${env:NOMBRE}` y `${env:NOMBRE:-valor_por_defecto}`. **Nunca** pongas credenciales literales en el YAML.
    - **Varios ficheros:** `--config` puede repetirse y los mapas se **fusionan** (un fichero base + uno por entorno). Cuidado con las **secciones vacías**: un `processors:` sin contenido es `null` y, al fusionar, puede **borrar** lo anterior; usa `{}` o elimina la clave.
    - **Subcomandos útiles:** `otelcol validate --config=...` (sin arrancar), `otelcol components` (qué hay en *esta* distribución), `otelcol print-config` (config final; experimental, oculta secretos).
    - **Nombres canónicos 0.162:** los exportadores OTLP son `otlp_grpc` y `otlp_http`; `file_log`, `host_metrics`, `span_metrics`, `k8s_attributes`… También se aceptan alias antiguos (`otlphttp`, `otlp` como exportador, `prometheusremotewrite`; lo comprobamos con `validate`), pero `otelcol components` lista **solo** los nuevos: escribe los nuevos.

    ## 2.1 Un Collector «de juguete» hecho a mano

    Antes del Collector real, construimos uno mínimo en Python con las **mismas reglas** (cadena ordenada de procesadores, fan-out síncrono, exportadores). No pretende ser eficiente: sirve para ver **por qué** el orden y el fan-out importan.
    """)
    code('''
class MiniPipeline:
    """receptor -> [procesadores en orden] -> exportadores (fan-out: cada exportador recibe una copia). Llamadas SÍNCRONAS, como en el Collector."""
    def __init__(self, processors, exporters): self.processors, self.exporters = processors, exporters
    def push(self, spans):
        for p in self.processors:
            spans = p(spans)
            if not spans: return                                  # un procesador puede descartar todo
        for e in self.exporters: e([dict(s) for s in spans])      # copia por exportador

work = collections.Counter()                                      # «unidades de trabajo» por procesador (proxy de CPU)
def attributes_hash(spans):
    out = []
    for s in spans:
        work["attributes"] += 1; s = dict(s); s["email"] = "h:" + str(hash(s["email"]) % 10**8); out.append(s)
    return out
def filter_health(spans):
    work["filter"] += len(spans); return [s for s in spans if s["name"] != "GET /healthz"]
class Batch:
    def __init__(self, size): self.size, self.buf, self.sent = size, [], []
    def __call__(self, spans):
        self.buf += spans
        while len(self.buf) >= self.size: self.sent.append(self.buf[:self.size]); self.buf = self.buf[self.size:]
        return None                                               # el batch retiene (salida diferida)
rng = np.random.default_rng(SEED)
stream = [{"name": "GET /healthz" if rng.random() < 0.4 else "chat mock-small", "email": f"c{i}@example.com"} for i in range(2000)]
res = {}
for label, order in {"filter → attributes (recomendado)": [filter_health, attributes_hash], "attributes → filter (al revés)": [attributes_hash, filter_health]}.items():
    work.clear(); pipe = MiniPipeline(order, [lambda b: None])
    for i in range(0, len(stream), 50): pipe.push(stream[i:i + 50])
    res[label] = dict(work)
print(res)
fig, ax = plt.subplots(figsize=(8, 3.2)); labels = list(res); vals = [res[l]["attributes"] for l in labels]
bars = ax.bar(labels, vals, color=[viz.PALETTE["ok"], viz.PALETTE["error"]]); ax.bar_label(bars); ax.set_ylabel("spans procesados por `attributes`"); ax.set_title("Mismo resultado, distinto trabajo (40 % de spans de salud)"); plt.show()
''')
    md(observe("""
    - Si filtras **antes**, `attributes` procesa solo el 60 % de los spans; si filtras **después**, procesa el 100 % y luego tira el 40 %: **trabajo (CPU) tirado**. Con procesadores caros (`transform` con expresiones, `redaction`) la diferencia se nota en producción.
    - Lo mismo ocurre con `batch`: agrupar antes de filtrar mete en los lotes datos que luego se descartarán, y (según el README oficial) el *batching* además **borra el contexto de la petición**, así que cualquier procesador que lo necesite debe ir **antes**.
    """))
    code('''
# Fan-out SÍNCRONO: un exportador lento en un pipeline bloquea al receptor y, con él, a los demás pipelines que cuelgan del mismo receptor.
class MiniReceiver:
    def __init__(self, pipelines): self.pipelines = pipelines
    def push(self, spans):
        for p in self.pipelines: p.push(spans)                     # llamada síncrona: si una tarda, las demás esperan

def ingest_time(slow_ms, n=50):
    fast = MiniPipeline([], [lambda b: None]); slow = MiniPipeline([], [lambda b: time.sleep(slow_ms / 1000)])
    r = MiniReceiver([slow, fast]); batch = [{"name": "s"}] * 10
    t0 = time.perf_counter()
    for _ in range(n): r.push(batch)
    return (time.perf_counter() - t0) / n * 1000

delays = [0, 2, 5, 10, 20]; tt = [ingest_time(d) for d in delays]
fig, ax = plt.subplots(figsize=(7.5, 3.4)); ax.plot(delays, tt, marker="o", color=viz.PALETTE["error"], label="tiempo de ingesta por lote (medido)"); ax.plot(delays, delays, ls=":", color="k", label="retraso del exportador lento")
ax.set_xlabel("retraso del exportador lento (ms)"); ax.set_ylabel("ms por lote en el receptor"); ax.set_title("El pipeline lento frena al rápido (fan-out síncrono)"); ax.legend(); plt.show()
''')
    md(observe("""
    - El tiempo que tarda el **receptor** en aceptar un lote crece 1:1 con el retraso del exportador lento, aunque el otro pipeline sea instantáneo. Es exactamente la advertencia de la documentación oficial: *«si un procesador bloquea la llamada, los demás pipelines conectados a ese receptor quedan bloqueados y el receptor deja de procesar datos nuevos»*.
    - **Consecuencia práctica:** los exportadores de red deben tener **cola de envío** (`sending_queue`, activada por defecto) para desacoplar la entrega lenta de la recepción; y conviene aislar en Collectors/pipelines distintos las señales con comportamientos muy diferentes.
    """))

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ---
    # 3 · Con el Collector real: la configuración del stack, línea a línea

    Este es el `config.yaml` que usa el stack del curso (módulo 00). Léelo con las reglas de arriba:
    """)
    code('''
STACK_CFG_PATH = ROOT / "stack" / "otel-collector" / "config.yaml"
STACK_CFG = STACK_CFG_PATH.read_text()
print(STACK_CFG)
''')
    md("""
    | Fragmento | Qué hace y **por qué** |
    |---|---|
    | `receivers.otlp.protocols.{grpc,http}` en `0.0.0.0` | Escucha OTLP en las dos variantes. `0.0.0.0` es necesario **dentro del contenedor** para que el puerto publicado funcione (en un host expuesto, restringe la interfaz) |
    | `memory_limiter` (`limit_mib: 400`, `spike_limit_mib: 100`, `check_interval: 1s`) | Límite **duro** 400 MiB; el límite **blando** es `limit_mib − spike_limit_mib` = 300 MiB: por encima el Collector **rechaza** datos nuevos y fuerza GC |
    | `resource/lab` (`deployment.environment.name=lab`, `upsert`) | Etiqueta común de entorno. `upsert` = inserta o sobrescribe |
    | `batch` (`timeout: 1s`, `send_batch_size: 512`) | Envía cuando hay 512 elementos **o** pasa 1 s. (Por defecto serían 8192 y 200 ms.) |
    | `otlp_grpc/tempo` (`tempo:4317`, `tls.insecure`) | Trazas a Tempo por gRPC dentro de la red de Compose; sin TLS porque es laboratorio |
    | `otlp_http/loki` (`http://loki:3100/otlp`) | Logs al **endpoint OTLP nativo** de Loki; el exportador añade `/v1/logs` |
    | `prometheus` (`:8889`, `resource_to_telemetry_conversion`, `enable_open_metrics`) | Expone las métricas para que Prometheus las **raspe** (pull). `resource_to_telemetry_conversion` copia **todos** los atributos de resource a etiquetas (¡cardinalidad!); `enable_open_metrics` permite *exemplars* |
    | `debug` | Definido pero **no conectado** (se activa añadiéndolo a un pipeline) |
    | `health_check` (`:13133`) | Endpoint de salud para sondas |
    | `service.telemetry.metrics` (`:8888`) | **Métricas internas** del propio Collector (`otelcol_*`): tu «observabilidad de la observabilidad» |
    | `pipelines.{traces,logs,metrics}` | Tres cadenas `memory_limiter → resource/lab → batch` con su exportador |
    """)

    md("""
    ## 3.1 Validar: `otelcol validate` y un linter offline

    `otelcol validate` carga la configuración **sin arrancar** y detecta errores de sintaxis, claves inexistentes, referencias rotas y señales no soportadas. Lo ejecutamos en un contenedor desechable con la **misma imagen** del stack (no necesita puertos ni el stack).
    Primero, una colección de **configuraciones rotas a propósito** (cada una ilustra una regla de la sección 2) y lo que responde el Collector real:
    """)
    code('''
BASE_R = "receivers:\\n  otlp:\\n    protocols:\\n      http: {}\\n"
BAD = {
 "1 · componente definido y no usado": BASE_R + "exporters:\\n  debug: {}\\n  otlp_grpc/tempo:\\n    endpoint: tempo:4317\\nservice:\\n  pipelines:\\n    traces:\\n      receivers: [otlp]\\n      exporters: [debug]\\n",
 "2 · procesador referenciado y no definido": BASE_R + "exporters:\\n  debug: {}\\nservice:\\n  pipelines:\\n    traces:\\n      receivers: [otlp]\\n      processors: [batch]\\n      exporters: [debug]\\n",
 "3 · clave inexistente (limit_mb)": BASE_R + "processors:\\n  memory_limiter:\\n    check_interval: 1s\\n    limit_mb: 400\\nexporters:\\n  debug: {}\\nservice:\\n  pipelines:\\n    traces:\\n      receivers: [otlp]\\n      processors: [memory_limiter]\\n      exporters: [debug]\\n",
 "4 · memory_limiter sin límite": BASE_R + "processors:\\n  memory_limiter:\\n    check_interval: 1s\\nexporters:\\n  debug: {}\\nservice:\\n  pipelines:\\n    traces:\\n      receivers: [otlp]\\n      processors: [memory_limiter]\\n      exporters: [debug]\\n",
 "5 · exportador que no soporta la señal": BASE_R + "exporters:\\n  prometheus_remote_write:\\n    endpoint: http://prometheus:9090/api/v1/write\\nservice:\\n  pipelines:\\n    traces:\\n      receivers: [otlp]\\n      exporters: [prometheus_remote_write]\\n",
 "6 · ningún pipeline": BASE_R + "exporters:\\n  debug: {}\\nservice:\\n  pipelines: {}\\n",
 "7 · alias antiguo (otlphttp)": BASE_R + "exporters:\\n  otlphttp:\\n    endpoint: http://x:4318\\nservice:\\n  pipelines:\\n    traces:\\n      receivers: [otlp]\\n      exporters: [otlphttp]\\n",
}
RECORDED_VALIDATE = {   # salida real de `otelcol validate` (contrib 0.162.0) para las 7 configuraciones, por si no hay Docker
 "1 · componente definido y no usado": "OK (exit 0): el Collector lo acepta e ignora el exportador sin usar",
 "2 · procesador referenciado y no definido": 'Error: service::pipelines::traces: references processor "batch" which is not configured',
 "3 · clave inexistente (limit_mb)": "'processors' error reading configuration for \\"memory_limiter\\": ... 'memorylimiter.Config' has invalid keys: limit_mb",
 "4 · memory_limiter sin límite": "Error: processors::memory_limiter: 'limit_mib' or 'limit_percentage' must be greater than zero",
 "5 · exportador que no soporta la señal": 'Error: failed to build pipelines: failed to create "prometheus_remote_write" exporter for data type "traces": telemetry type is not supported',
 "6 · ningún pipeline": "Error: service::pipelines: service must have at least one pipeline",
 "7 · alias antiguo (otlphttp)": "OK (exit 0): el alias se acepta",
}
def otelcol_validate(cfg_text: str) -> str:
    d = pathlib.Path(tempfile.mkdtemp()); (d / "c.yaml").write_text(cfg_text); os.chmod(d / "c.yaml", 0o644)
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{d / 'c.yaml'}:/c.yaml:ro", IMAGE, "validate", "--config=/c.yaml"], capture_output=True, text=True)
    shutil.rmtree(d, ignore_errors=True)
    msg = " ".join((r.stdout + r.stderr).split())
    return ("OK (exit 0)" if r.returncode == 0 else msg[:230])
rows = [{"configuración": k, "otelcol validate": (otelcol_validate(v) if DOCKER else RECORDED_VALIDATE[k])} for k, v in BAD.items()]
pd.set_option("display.max_colwidth", 200); display(pd.DataFrame(rows).set_index("configuración"))
''')
    md("""
    Fíjate en dos casos **traicioneros**: el **1** (un componente definido y no usado) y el **7** (alias) **no dan error**. Que `validate` pase **no significa** que la configuración haga lo que quieres: el exportador sin usar nunca enviará nada.
    Para detectar ese tipo de cosas sin ejecutar el Collector construimos un **linter offline**, con la lista de componentes de la distribución (`collector_components_0.162.0.json`, salida de `otelcol components`) y las reglas de la sección 2. Es el análogo del linter de atributos del módulo 04:

    | Regla | Sev. | Detecta |
    |---|---|---|
    | `PARSE`, `NOPIPE` | error | YAML inválido; sin pipelines |
    | `UNKNOWN` | error | tipo de componente que no existe en la distribución |
    | `UNDEF` | error | pipeline que referencia un componente no configurado |
    | `SIGNAL` | error | componente que no soporta la señal del pipeline |
    | `MLCFG` | error | `memory_limiter` sin límite |
    | `ALIAS` | aviso | nombre antiguo (`otlphttp`…) |
    | `UNUSED` | aviso | definido y no usado |
    | `ORDER`, `NOML` | aviso | orden de procesadores contra la práctica recomendada; pipeline sin `memory_limiter` |
    | `EXPQ` | aviso | exportador de red con `sending_queue` desactivada |
    | `BIND`, `SECRET`, `NULL` | aviso | `pprof/zpages` en `0.0.0.0`; credenciales literales; secciones nulas |
    | `NOBATCH`, `HEALTH` | info | sin agrupación; sin `health_check` |
    """)
    code(CFGLINT_SRC)
    code('''
rows = []
for k, v in BAD.items():
    rows.append({"configuración": k, "reglas del linter": ", ".join(sorted({f["rule"] + f"({f['severity'][0]})" for f in cfglint(v) if f["rule"] not in ("NOML", "HEALTH", "NOBATCH")})) or "—"})
rows.append({"configuración": "★ la del stack (A1)", "reglas del linter": ", ".join(sorted({f["rule"] + f"({f['severity'][0]})" for f in cfglint(STACK_CFG)})) or "—"})
display(pd.DataFrame(rows).set_index("configuración"))
print([ (f["rule"], f["where"]) for f in cfglint(STACK_CFG) ])
''')
    md(observe("""
    - El linter **encuentra los casos que `validate` deja pasar** (`UNUSED` en el 1, `ALIAS` en el 7) y coincide con `validate` en los que sí son errores (`UNDEF`, `MLCFG`, `SIGNAL`, `NOPIPE`).
    - La configuración del stack solo tiene un aviso: el exportador `debug` **definido pero no conectado** (a propósito, para activarlo al depurar). Ningún error.
    - `validate` es el **juez final** (conoce las opciones exactas de cada componente); el linter es **rápido, sin Docker** y añade criterios de buena práctica. Úsalos juntos: linter en el editor/CI, `validate` antes de desplegar.
    """))

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ---
    # 4 · Experimentos con un Collector real (contenedores de laboratorio)

    Para cada experimento levantamos un **Collector desechable** (misma imagen que el stack) con **puertos de host aleatorios** —no choca con el stack— y, para ver exactamente qué sale, sustituimos los backends por el exportador **`file`** (escribe OTLP/JSON en un directorio montado).
    Enviamos telemetría con nuestro SDK y leemos el resultado. Si no tienes Docker, estas celdas usan los **resultados pregrabados** de una ejecución real (mismo formato) y los gráficos son idénticos.
    """)
    code('''
RECORD_FILE = ROOT / "05_collector" / "lab_results_recorded.json"
RECORDED = json.loads(RECORD_FILE.read_text()) if RECORD_FILE.exists() else {}
LAB_ACC: dict = {}
def lab(name, fn):
    """Ejecuta el experimento con Docker, o devuelve el resultado pregrabado si no hay Docker."""
    if DOCKER:
        LAB_ACC[name] = fn(); return LAB_ACC[name]
    return RECORDED[name]

def cfg_file(processors: str = "", chain=()) -> str:
    """Config de laboratorio: OTLP/HTTP -> [procesadores] -> exportador file (traces). `processors` es el bloque YAML `processors:`."""
    return ("receivers:\\n  otlp:\\n    protocols:\\n      http:\\n        endpoint: 0.0.0.0:4318\\n" + processors +
            "exporters:\\n  file/traces:\\n    path: /out/traces.jsonl\\nservice:\\n" + INTERNAL_TELEMETRY +
            f"  pipelines:\\n    traces:\\n      receivers: [otlp]\\n      processors: [{', '.join(chain)}]\\n      exporters: [file/traces]\\n")
''')

    md("""
    ## 4.1 `batch`: ¿cuántos datos viajan en cada petición?

    Simulamos **muchas aplicaciones pequeñas** (el SDK envía lotes de 20 spans cada ~20 ms) y miramos cuántos spans lleva cada «línea» (petición exportada) con tres configuraciones: sin `batch`, `batch` de 200 elementos/200 ms y `batch` de 400 elementos/1 s.
    """)
    code('''
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

def send_small_batches(endpoint, n=400, batch=20):
    p = TracerProvider(resource=Resource.create({"service.name": "probe"}))
    p.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint + "/v1/traces"), max_export_batch_size=batch, schedule_delay_millis=10))
    t = p.get_tracer("x")
    for i in range(n):
        with t.start_as_current_span("s"): pass
        if i % batch == 0: time.sleep(0.03)
    p.force_flush(10000); p.shutdown()

def exp_batch():
    out = {}
    variants = {"sin batch": cfg_file(), "batch 200 · 200 ms": cfg_file("processors:\\n  batch:\\n    timeout: 200ms\\n    send_batch_size: 200\\n", ["batch"]),
                "batch 400 · 1 s": cfg_file("processors:\\n  batch:\\n    timeout: 1s\\n    send_batch_size: 400\\n", ["batch"])}
    for label, cfg in variants.items():
        with LabCollector(cfg) as c:
            send_small_batches(c.otlp_http); time.sleep(2.5)
            out[label] = [sum(len(ss["spans"]) for rs in l["resourceSpans"] for ss in rs["scopeSpans"]) for l in c.read("traces.jsonl")]
    return out

B = lab("batch", exp_batch)
fig, axes = plt.subplots(1, 3, figsize=(14, 3.4), sharey=False)
for ax, (k, v) in zip(axes, B.items()):
    ax.hist(v, bins=range(0, 441, 20), color=viz.PALETTE["traces"], edgecolor="white"); ax.set_title(f"{k}\\n{len(v)} peticiones · media {np.mean(v):.0f} spans", fontsize=10); ax.set_xlabel("spans por petición exportada")
axes[0].set_ylabel("nº de peticiones")
plt.tight_layout(); plt.show()
print({k: (len(v), sum(v)) for k, v in B.items()}, "(peticiones, spans totales: no se pierde ninguno)")
''')
    md(observe("""
    - **Sin `batch`**, cada petición de cada SDK se exporta tal cual: muchas peticiones pequeñas (≈ 20 spans). **Con `batch`**, el Collector las junta: el número de peticiones al backend se divide por 5 o más (en esta prueba, de ≈ 20 a 4 y a 1) y cada una es mayor, así que **comprime mejor** y cuesta menos al backend.
    - Los **parámetros** son un compromiso: más `timeout` y más `send_batch_size` = menos peticiones y mejor compresión, pero más **latencia** (un dato espera hasta `timeout` antes de salir) y más memoria retenida. Los valores por defecto del procesador son `send_batch_size: 8192` y `timeout: 200ms`; el stack usa 512 y 1 s.
    - El total de spans es **idéntico** en las tres: el `batch` no pierde ni cambia datos, solo los reagrupa.
    """))

    md("""
    ## 4.2 Procesadores en acción: PII, ruido y entorno

    Enviamos telemetría con **defectos**: spans `GET /healthz` (ruido), `customer.email` (PII) y `debug.prompt` (atributo de depuración que no debe salir), y comprobamos qué sale tras una cadena en el orden recomendado:
    `memory_limiter → filter/health → attributes/pii → resource/lab → batch`.
    """)
    code('''
PROC_B = """processors:
  memory_limiter:
    check_interval: 1s
    limit_mib: 256
    spike_limit_mib: 50
  filter/health:                 # descarta spans que cumplen la condición OTTL
    error_mode: ignore
    traces:
      span:
        - 'name == "GET /healthz"'
  attributes/pii:                # insert | update | upsert | delete | hash | extract
    actions:
      - key: customer.email
        action: hash             # SHA-256: sigue sirviendo para correlacionar, no para identificar
      - key: debug.prompt
        action: delete
  resource/lab:
    attributes:
      - key: deployment.environment.name
        value: lab-student
        action: upsert
  batch:
    timeout: 300ms
"""
CHAIN_B = ["memory_limiter", "filter/health", "attributes/pii", "resource/lab", "batch"]
def exp_processors():
    with LabCollector(cfg_file(PROC_B, CHAIN_B)) as c:
        sent = send_probe(c.otlp_http, n_chat=5, n_health=3, n_logs=0)
        spans = flat_spans(c.read("traces.jsonl")); m = c.internal_metrics()
        return {"sent": sent, "spans_out": spans, "accepted": m.get("otelcol_receiver_accepted_spans"), "exported": m.get("otelcol_exporter_sent_spans")}

P = lab("processors", exp_processors)
print(f"enviados {P['sent']['chat'] + P['sent']['health']} spans (5 chat + 3 healthz) · aceptados por el receptor {P['accepted']:.0f} · exportados {P['exported']:.0f}")
ex = P["spans_out"][0]
print("\\natributos de un span que SALE:", {k: (v[:12] + "…" if isinstance(v, str) and len(v) > 12 else v) for k, v in ex["attrs"].items()})
print("resource que SALE            :", {k: v for k, v in ex["resource"].items() if k.startswith(("service.name", "deployment"))})
''')
    code('''
before = {"spans": 8, "con correo en claro": 5, "con debug.prompt": 5, "spans de salud": 3, "con entorno lab-student": 0}
after = {"spans": len(P["spans_out"]), "con correo en claro": sum("@" in str(s["attrs"].get("customer.email", "")) for s in P["spans_out"]), "con debug.prompt": sum("debug.prompt" in s["attrs"] for s in P["spans_out"]),
         "spans de salud": sum(s["name"] == "GET /healthz" for s in P["spans_out"]), "con entorno lab-student": sum(s["resource"].get("deployment.environment.name") == "lab-student" for s in P["spans_out"])}
fig, ax = plt.subplots(figsize=(10, 3.4)); x = np.arange(len(before)); w = 0.38
ax.bar(x - w / 2, list(before.values()), w, label="a la entrada del Collector", color=viz.PALETTE["neutral"]); b2 = ax.bar(x + w / 2, list(after.values()), w, label="a la salida", color=viz.PALETTE["ok"]); ax.bar_label(b2)
ax.set_xticks(x, list(before), fontsize=8); ax.set_ylabel("nº de spans"); ax.legend(); ax.set_title("Qué cambia el Collector en el camino (5 chat + 3 healthz)"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **El ruido desaparece** (0 spans de salud a la salida; el receptor aceptó 8 y el exportador envió 5) y **la PII también**: ningún correo en claro (el atributo sigue existiendo como *hash*, útil para contar clientes distintos sin conocerlos) y `debug.prompt` eliminado.
    - **El entorno se añade al 100 %** de los spans sin tocar las aplicaciones.
    - Todo ocurre **fuera de las aplicaciones**: ningún equipo cambió una línea. También es el motivo de su peligro: una regla mal escrita borra datos de **todos**.
    """))

    md("""
    ### Otros procesadores que usarás (y cómo se escriben)

    | Necesidad | Procesador | Ejemplo (verificado con `validate` o con la documentación) |
    |---|---|---|
    | Renombrar/copiar atributos con lógica | `transform` (lenguaje **OTTL**) | `set(span.attributes["gen_ai.provider.name"], span.attributes["gen_ai.system"]) where span.attributes["gen_ai.system"] != nil` y luego `delete_key(span.attributes, "gen_ai.system")` |
    | Cambiar el *status* de un span | `transform` | `set(span.status.code, STATUS_CODE_OK) where span.attributes["http.request.status_code"] == 400` (ejemplo de la documentación) |
    | Quedarse solo con ciertos servicios | `filter` | `resource.attributes["service.name"] != "app1" and ...` |
    | Insertar/borrar/hashear atributos de **datos** | `attributes` | `actions: [{key: ..., action: hash}]` |
    | Insertar/borrar atributos del **resource** | `resource` | `attributes: [{key: ..., value: ..., action: upsert}]` |
    | Enriquecer con metadatos del host/nube/pod | `resource_detection`, `k8s_attributes` | `detectors: [env, system]` |
    | Redacción de valores sensibles por patrones | `redaction` (alpha en logs y métricas, beta en trazas en 0.162) | módulo 20 |

    ⚠️ El procesador `attributes` actúa sobre los **atributos del dato** (span, log, punto), no sobre el **nombre del span** (eso es del procesador `span`) ni sobre el *resource* (procesador `resource`). Es una de las confusiones más comunes (lo recoge la guía oficial de problemas frecuentes).
    """)

    md("""
    ## 4.3 `memory_limiter`: el freno de emergencia y su efecto en las aplicaciones

    Ponemos un límite **absurdamente bajo** (10 MiB, menos que la memoria base del propio proceso) para forzar el modo «limitado» y ver qué recibe el SDK: la respuesta HTTP del Collector y las métricas internas.
    """)
    code('''
PROC_C = "processors:\\n  memory_limiter:\\n    check_interval: 100ms\\n    limit_mib: 10\\n    spike_limit_mib: 2\\n"
PAYLOAD = {"resourceSpans": [{"resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "probe"}}]}, "scopeSpans": [{"scope": {"name": "t"}, "spans": [
    {"traceId": "%032x" % (i + 1), "spanId": "%016x" % (i + 1), "name": "s", "kind": 1, "startTimeUnixNano": "1788253200000000000", "endTimeUnixNano": "1788253200100000000"} for i in range(10)]}]}]}
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
def post_traces(endpoint):
    try:
        r = OPENER.open(urllib.request.Request(endpoint + "/v1/traces", data=json.dumps(PAYLOAD).encode(), headers={"Content-Type": "application/json"}), timeout=5); return [r.status, ""]
    except urllib.error.HTTPError as e:
        return [e.code, e.read().decode()[:80]]

def exp_memory():
    with LabCollector(cfg_file(PROC_C, ["memory_limiter"])) as c:
        codes = [post_traces(c.otlp_http) for _ in range(5)]; time.sleep(0.5); m = c.internal_metrics()
        return {"responses": codes, "refused_spans": m.get("otelcol_receiver_refused_spans"), "accepted_spans": m.get("otelcol_receiver_accepted_spans"), "limiter_refused": m.get("otelcol_processor_memory_limiter_refused_spans")}

M = lab("memory", exp_memory)
print("respuestas del Collector a 5 peticiones de 10 spans:", M["responses"][:2], "…")
print({k: M[k] for k in ("accepted_spans", "refused_spans", "limiter_refused")})
fig, ax = plt.subplots(figsize=(6.5, 3)); bars = ax.bar(["aceptados", "rechazados"], [M["accepted_spans"], M["refused_spans"]], color=[viz.PALETTE["ok"], viz.PALETTE["error"]]); ax.bar_label(bars)
ax.set_ylabel("spans (50 enviados)"); ax.set_title("memory_limiter en modo limitado"); plt.show()
''')
    md(observe("""
    - El Collector responde **HTTP 503** con el mensaje *«data refused due to high memory usage»*: no pierde el dato por su cuenta, **lo devuelve** al cliente para que reintente (es un error *no permanente*). Las métricas internas lo cuentan en `otelcol_receiver_refused_spans` y `otelcol_processor_memory_limiter_refused_spans`.
    - **Quién se queda con el problema es el SDK** (módulo 03): reintenta con *backoff* y, si el rechazo dura, su cola local se llena y descarta. La documentación del procesador lo dice sin rodeos: *si el componente anterior no reintenta correctamente, los datos se pierden definitivamente.*
    - Un `memory_limiter` activo **no es normal**: es una alarma de que el Collector está mal dimensionado o el backend va lento. Se alerta con `otelcol_processor_refused_spans` (ver sección 5).
    """))

    md("""
    ## 4.4 La cola de envío: qué pasa cuando el backend se cae

    Cada exportador de red tiene una **`sending_queue`** (activada por defecto) y **`retry_on_failure`**. Lo medimos apuntando un exportador a un destino **inexistente** con una cola pequeña (10 peticiones) y un solo consumidor, mientras enviamos 30 peticiones, y vigilamos las métricas internas cada 0,2 s.

    > 🤔 **Predice antes de ejecutar.** El destino no responde nunca. (a) ¿Qué código HTTP recibirá el SDK en las primeras peticiones? (b) ¿Cambia algo cuando la cola llega a 10? (c) Si fueras el SDK, ¿qué tendrías que hacer con ese cambio? Apunta las tres respuestas y contrástalas con las dos fases de la gráfica.
    """)
    code('''
PROC_D = ("exporters:\\n  otlp_http/dead:\\n    endpoint: http://127.0.0.1:9\\n    retry_on_failure:\\n      enabled: true\\n      initial_interval: 1s\\n      max_interval: 2s\\n      max_elapsed_time: 60s\\n"
          "    sending_queue:\\n      enabled: true\\n      num_consumers: 1\\n      queue_size: 10\\n")
CFG_D = ("receivers:\\n  otlp:\\n    protocols:\\n      http:\\n        endpoint: 0.0.0.0:4318\\n" + PROC_D + "service:\\n" + INTERNAL_TELEMETRY +
         "  pipelines:\\n    traces:\\n      receivers: [otlp]\\n      exporters: [otlp_http/dead]\\n")
def exp_queue():
    with LabCollector(CFG_D) as c:
        t, q, cap, enq, ref, codes = [], [], None, [], [], []
        t0 = time.time()
        for i in range(30):
            codes.append(post_traces(c.otlp_http)[0]); m = c.internal_metrics()
            t.append(round(time.time() - t0, 2)); q.append(m.get("otelcol_exporter_queue_size", 0)); cap = m.get("otelcol_exporter_queue_capacity", cap)
            enq.append(m.get("otelcol_exporter_enqueue_failed_spans", 0)); ref.append(m.get("otelcol_receiver_refused_spans", 0)); time.sleep(0.2)
        return {"t": t, "queue": q, "capacity": cap, "enqueue_failed": enq, "refused": ref, "codes": codes}

Q = lab("queue", exp_queue)
fig, axes = plt.subplots(1, 2, figsize=(13, 3.4))
axes[0].plot(Q["t"], Q["queue"], color=viz.PALETTE["metrics"], lw=2, label="otelcol_exporter_queue_size"); axes[0].axhline(Q["capacity"], color="k", ls=":", label="otelcol_exporter_queue_capacity")
axes[0].set_xlabel("segundos"); axes[0].set_ylabel("peticiones en cola"); axes[0].set_title("La cola se llena y se queda llena"); axes[0].legend(fontsize=8)
axes[1].plot(Q["t"], Q["enqueue_failed"], color=viz.PALETTE["error"], lw=2, label="spans que no cupieron en la cola"); axes[1].plot(Q["t"], Q["refused"], color=viz.PALETTE["warn"], ls="--", label="spans rechazados al SDK (503)")
axes[1].set_xlabel("segundos"); axes[1].set_ylabel("spans (acumulado)"); axes[1].set_title("Desbordamiento = rechazo hacia atrás"); axes[1].legend(fontsize=8)
plt.tight_layout(); plt.show()
print("códigos HTTP vistos por el cliente:", dict(collections.Counter(Q["codes"])))
''')
    md(observe("""
    - **Fase 1 (cola subiendo):** el backend no responde, así que los lotes se acumulan en la cola mientras el consumidor reintenta con *backoff*. El Collector acepta datos (HTTP 200).
    - **Fase 2 (cola llena = capacidad):** `otelcol_exporter_queue_size` toca el techo; los datos nuevos **no caben** (`enqueue_failed_spans` sube) y el Collector **rechaza hacia atrás** (HTTP 503; `receiver_refused_spans` sube). La presión **viaja hasta el SDK**: cadena completa *backend caído → cola del exportador → receptor → SDK → cola del `BatchSpanProcessor`*.
    - Cada eslabón tiene su tamaño y su política. Los tamaños por defecto del exportador son `queue_size: 1000` (**peticiones**, no spans, salvo que cambies el `sizer`) y reintentos hasta `max_elapsed_time: 300s`; pasado ese plazo el dato más antiguo se **descarta**.
    - Para sobrevivir a **reinicios del Collector** existe la **cola persistente** (`sending_queue.storage` con la extensión `file_storage`): el lote se escribe en disco antes de enviarse. No equivale a una cola de mensajería: si el disco falla o se llena, también se pierde.
    """))

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ---
    # 5 · Observar al propio Collector: las métricas internas `otelcol_*`

    El Collector expone sus propias métricas (en el stack, `:8888`; Prometheus las raspa en el job `otel-collector-internal`). Estas son **las que importan**, todas verificadas en la documentación oficial de telemetría interna:

    | Métrica | Qué dice | Alerta sugerida |
    |---|---|---|
    | `otelcol_receiver_accepted_{spans,log_records,metric_points}` | Datos aceptados en el pipeline | Caída brusca = nadie envía |
    | `otelcol_receiver_refused_*` | **Rechazados** (memory_limiter, cola llena) | `rate(...) > 0` sostenido |
    | `otelcol_processor_incoming_items` / `outgoing_items` | Entrada y salida de un procesador | Diferencia = lo que descarta (filtros, muestreo) |
    | `otelcol_exporter_sent_*` / `send_failed_*` | Enviados / fallidos al destino | `send_failed > 0` sostenido |
    | `otelcol_exporter_queue_size` / `queue_capacity` | Ocupación de la cola de envío | **> 60-70 %** de la capacidad (guía de escalado) |
    | `otelcol_exporter_enqueue_failed_*` | No cupieron en la cola (**pérdida**) | `> 0` |
    | `otelcol_process_memory_rss`, `otelcol_process_cpu_seconds` | Consumo del proceso | Cerca del límite del contenedor |

    Nombres en Prometheus: con la configuración de telemetría interna del stack (`service.telemetry.metrics.readers.pull`, versión 0.162) los contadores se exponen **sin** sufijo `_total` (`otelcol_exporter_send_failed_spans`; verificado con `curl :8888/metrics`); otras versiones o ajustes del lector pueden añadirlo, así que comprueba el nombre exacto en tu `/metrics` antes de escribir una alerta. La **conservación** (`accepted − dropped_por_filtros = sent` cuando todo va bien) es el test más simple de que no pierdes datos.
    Verificamos esa conservación con el **Collector real del stack** (si está arriba): enviamos 60 spans y miramos el incremento de las métricas.
    """)
    code('''
def stack_collector_metrics():
    txt = OPENER.open("http://localhost:8888/metrics", timeout=5).read().decode(); out = {}
    for ln in txt.splitlines():
        if ln.startswith("otelcol_") and "spans" in ln:
            name, val = ln.rsplit(" ", 1); name = re.sub(r"\\{.*\\}", "", name); out[name] = out.get(name, 0.0) + float(val)
    return out
if STACK.degraded:
    print("Modo degradado: sin el stack no hay Collector central que medir. Levántalo con:\\n  ", STACK.command)
else:
    m0 = stack_collector_metrics()
    tel = setup_telemetry("supportops-conservation", metric_interval_s=2); tr = tel.tracer()
    for i in range(60):
        with tr.start_as_current_span("conservation-probe"): pass
    tel.force_flush(10); tel.shutdown(); time.sleep(3)
    m1 = stack_collector_metrics(); d = {k: m1.get(k, 0) - m0.get(k, 0) for k in m1}
    acc = d.get("otelcol_receiver_accepted_spans_total", d.get("otelcol_receiver_accepted_spans", 0)); sent = d.get("otelcol_exporter_sent_spans_total", d.get("otelcol_exporter_sent_spans", 0))
    print(f"enviados 60 · aceptados (Δ) = {acc:.0f} · exportados a Tempo (Δ) = {sent:.0f} · rechazados (Δ) = {d.get('otelcol_receiver_refused_spans_total', 0):.0f}")
    fig, ax = plt.subplots(figsize=(6.5, 3)); bars = ax.bar(["enviados\\n(SDK)", "aceptados\\n(receiver)", "exportados\\n(exporter)"], [60, acc, sent], color=[viz.PALETTE["neutral"], viz.PALETTE["traces"], viz.PALETTE["ok"]]); ax.bar_label(bars); ax.set_title("Conservación de spans en el Collector del stack"); plt.show()
''')
    md("""
    ---
    # 6 · De la config a los tres backends

    La configuración del stack (sección 3) ya exporta a Tempo (`otlp_grpc/tempo`), Loki (`otlp_http/loki`) y Prometheus (`prometheus` por *scrape*). En el **proyecto** escribirás tu propio gateway con **un exportador OTLP por backend**: para métricas, `otlp_http` hacia el **receptor OTLP de Prometheus** (activado en el stack con `--web.enable-otlp-receiver`, ruta `/api/v1/otlp`), una alternativa *push* al *pull* del stack.

    | Opción de métricas | Ventajas | Inconvenientes |
    |---|---|---|
    | `prometheus` exporter (pull, la del stack) | Simple; admite *exemplars* con OpenMetrics; Prometheus controla el ritmo | Estado de «frescura» y *staleness*; `resource_to_telemetry_conversion` convierte **todos** los atributos de resource en etiquetas (riesgo de cardinalidad) |
    | `otlp_http` → receptor OTLP de Prometheus (push) | Sin puerto de *scrape*; los atributos de resource van a la métrica `target_info` y **Prometheus no promociona ninguno a etiqueta** salvo los que configures (`promote_resource_attributes`); `service.name`/`service.instance.id` forman `job`/`instance` | Hay que activar el receptor (`--web.enable-otlp-receiver`) y decidir qué promocionar; revisa la traducción de nombres |
    | `prometheus_remote_write` | Clásico y muy extendido | Otra conversión de formato |
    """)

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ---
    # 7 · 🏭 En producción

    - **Distribuciones.** `otelcol-contrib` (la que usamos) incluye cientos de componentes; en producción se suele **construir una a medida** con el *OpenTelemetry Collector Builder* (solo los componentes que necesitas: menos superficie de ataque, imagen más pequeña) o usar una distribución de proveedor. Grafana Labs ofrece [Grafana Alloy](https://grafana.com/docs/alloy/latest/introduction/otel_alloy/), su distribución del Collector con *pipelines* de Prometheus integrados y soporte nativo de Loki y Pyroscope (su motor basado en el Collector de OpenTelemetry figura en la documentación de Alloy como *public preview*: sujeto a cambios incompatibles). [Lista de distribuciones oficiales](https://github.com/open-telemetry/opentelemetry-collector-releases).
    - **Agente + gateway.** El patrón habitual: Collector local (DaemonSet/sidecar) que añade metadatos del nodo/pod (`k8s_attributes`, `resource_detection`) y reenvía por OTLP a un gateway central que aplica políticas (redacción, muestreo, enrutado). Los Collectors con estado (*tail sampling*, `span_metrics`) exigen el balanceo por traza/servicio del exportador `load_balancing` (módulo 18).
    - **Escalado: qué mirar.** La guía oficial de escalado recomienda vigilar `otelcol_processor_refused_spans` (si el `memory_limiter` rechaza a menudo, escala) y la ocupación de la cola (`otelcol_exporter_queue_size` frente a `queue_capacity`): **escala al 60-70 %** de la capacidad y reduce si es baja de forma sostenida, manteniendo un mínimo de réplicas (p. ej. 3) por resiliencia. Y entiende cuándo **no** escalar: si la base de datos o la red están saturadas, más Collectors **empeoran** el problema.
    - **Resiliencia por capas** (documentación de resiliencia): cola en memoria + reintentos con *backoff* (por defecto hasta 5 min) → cola **persistente** (`file_storage`) para sobrevivir a reinicios del propio Collector → y aun así, datos perdidos si el destino está caído más allá de los límites. Elige los límites con **datos** (volumen × tiempo de caída tolerable), no con valores por defecto.
    - **Operación:** versión **fijada** (el Collector es `0.x`), `GOMEMLIMIT` al 80 % del límite duro junto con `memory_limiter` (recomendación del README del procesador), `health_check` para sondas, `zpages`/`pprof` solo en `localhost`, secretos por `${env:...}`, y **alertas sobre las métricas internas**.
    """)

    md("""
    ---
    # 8 · 🧠 Secretos de la élite

    1. **`memory_limiter` primero, y con `GOMEMLIMIT`.** Rechaza datos *antes* de que los demás procesadores los acumulen. La documentación recomienda fijar además `GOMEMLIMIT` al **80 %** del límite duro y un `spike_limit_mib` inicial de ~**20 %** del límite duro (el límite blando es `limit_mib − spike_limit_mib`). Aviso explícito del README: **un dato puede consumir memoria antes de que el limitador lo rechace**, sobre todo con receptores que no son OTLP; no sustituye a dimensionar bien.
    2. **Rechazar es devolver, no perder... si el cliente reintenta.** El 503 de `memory_limiter` (y el de cola llena, que viste en 4.4) es un error *no permanente*: los datos solo se pierden de verdad si el emisor **no reintenta** o agota su cola. Por eso el diseño completo es una **cadena de colas** (SDK → Collector → backend) y cada tamaño importa.
    3. **`batch` borra el contexto de la petición** (README oficial del directorio de procesadores). Un procesador que necesite metadatos del cliente (`k8s_attributes`, autenticación) debe ir **antes**. Alternativa vigente: el *batching* integrado en la cola del exportador (`sending_queue: {batch: {}}`, desactivado por defecto), que es el que muestran los ejemplos actuales de la documentación de configuración; el procesador `batch` sigue siendo *beta*.
    4. **El fan-out es síncrono.** Un procesador que se bloquea frena al receptor y a **todos** los pipelines que cuelgan de él (lo mediste en 2.1). Mantén los pipelines livianos y confía en `sending_queue` para desacoplar entregas lentas.
    5. **Definir ≠ activar, y `validate` no lo ve.** Un receptor o exportador sin pipeline se ignora sin error (lo vimos con `validate` en 3.1): es la causa más habitual de «mis logs no llegan». Un linter (o un test que envía telemetría de prueba y la lee) lo detecta.
    6. **La cola se mide en *peticiones* (`sizer: requests`), no en spans.** `queue_size: 1000` son 1000 peticiones; con lotes de 512 spans son hasta ~512 000 spans en memoria. Dimensiona con la memoria disponible; y recuerda que tras `max_elapsed_time` (300 s por defecto) el dato más antiguo **se descarta**. La cola persistente no conserva el contexto que añaden las extensiones de autenticación.
    7. **`resource_to_telemetry_conversion` es un cañón de cardinalidad.** El exportador `prometheus` del stack convierte **todos** los atributos de resource en etiquetas: añade `service.instance.id` por réplica y tendrás una serie por instancia. Con OTLP hacia Prometheus no se promociona nada por defecto (los atributos van a `target_info`): decides tú cuáles.
    8. **Los nombres de componente y de opciones cambian entre versiones `0.x`.** En 0.162 los canónicos son `otlp_grpc`, `otlp_http`, `file_log`, `span_metrics`, `k8s_attributes`… (los antiguos se aceptan como alias, pero `otelcol components` solo lista los nuevos); y también cambian los nombres exactos de las métricas internas (según la versión y el lector de telemetría aparecen con o sin `_total`). Fija la imagen, ejecuta `validate` en CI con **esa misma imagen** y lee el *changelog* antes de actualizar.
    9. **`error_mode: ignore` es *fail-open*.** En `transform`, un statement que falla (p. ej. `replace_pattern` sobre un atributo que no es cadena) se registra y **el dato pasa sin transformar**; con `propagate` el lote **se descarta**. Para redacción de PII, `ignore` significa que un fallo deja pasar el dato en claro: pon las reglas críticas en su propio grupo con `error_mode: propagate` (prefieres perder el lote que filtrarlo) y comprueba con un test que envía PII de prueba. Fuente: README de `transformprocessor` (valores `ignore` por defecto, `silent`, `propagate`).
    10. **Balancear por `traceID` rompe los *span metrics*.** Para el *tail sampling* hace falta que todos los spans de una traza lleguen a la misma réplica (`routing_key: traceID`, el valor por defecto en trazas), pero si esas mismas réplicas generan métricas con el conector `spanmetrics`, cada una ve el mismo par `servicio+operación` y aparecen **colisiones de etiquetas** en Prometheus. El README del `loadbalancingexporter` lo documenta y propone enrutar por `service` para ese caso: los span metrics van en un tier distinto al del tail sampling.
    """)

    md("""
    ---
    # 9 · ⚠️ Errores comunes

    | Error | Síntoma | Arreglo |
    |---|---|---|
    | Definir un exportador y no ponerlo en el pipeline | «No llegan los logs»; `validate` pasa | Linter `UNUSED`; test con telemetría de prueba |
    | `memory_limiter` no es el primero (o falta) | Reinicios por OOM | Primero de la lista, con `limit_mib` y `GOMEMLIMIT` |
    | `batch` antes de filtros/transformaciones | CPU malgastada; contexto perdido | `batch` al final |
    | `attributes` para renombrar el **span** o el **resource** | «No hace nada» | `span` / `resource` / `transform` |
    | `processors:` vacío (null) al fusionar ficheros | Se pierde la configuración base | `processors: {}` o quitar la clave |
    | Credenciales literales en el YAML | Fugas en el repositorio | `${env:TOKEN}` |
    | `pprof`/`zpages` en `0.0.0.0` | Información interna expuesta | `localhost` |
    | Sin alertas en `otelcol_*` | Pérdidas durante días sin enterarte | Alerta en `refused`, `send_failed`, cola > 70 % |
    | Escalar réplicas cuando el backend es el cuello | Empeora la saturación | Escalar/optimizar el backend; revisar límites |
    | Versión `latest` de la imagen | Cambios de nombres rompen el arranque | Fijar la versión |
    """)

    md("""
    ---
    # 10 · Autoevaluación
    """)
    md(details("1 · (Recuerdo) Ordena de primero a último: `batch`, `attributes`, `memory_limiter`, `filter`, `k8s_attributes`. ¿Por qué `batch` va al final?",
               "`memory_limiter` → `filter` (descarta) → `k8s_attributes` (necesita el contexto de origen) → `attributes` (enriquece/transforma) → `batch`. Va al final para no agrupar lo que luego se descarta o modifica y porque agrupar **borra el contexto de la petición**."))
    md(details("2 · (Cálculo) Cada réplica de un gateway recibe 5 000 spans/s, el `batch` envía lotes de 512 y el exportador tiene `queue_size: 1000` (en peticiones). El backend cae 120 s sin que el Collector lo sepa. ¿Cuánto tarda en llenarse la cola y cuántos spans pierde cada réplica? ¿Y con `queue_size: 5000`?",
               """
               Peticiones/s ≈ $5000/512 = 9{,}77$. Con $Q=1000$: la cola se llena en $1000/9{,}77 \\approx 102$ s. En los 18 s restantes llegan $\\approx 18\\times 9{,}77 \\approx 172$ peticiones que no caben ⇒ $172\\times512\\approx 88\\,000$ spans perdidos por réplica (suponiendo que no se vacía en ese tiempo).
               Con $Q=5000$ la cola aguanta $5000/9{,}77\\approx 512$ s > 120 s: **no se pierde nada**, pero retiene hasta $5000\\times512\\approx2{,}6$ M de spans en memoria (cientos de MiB): hay que dimensionar la memoria **y** el `memory_limiter` en consecuencia.
               """))
    md(details("3 · (Cálculo) Un Collector corre en un contenedor de 2 GiB. Propón `limit_mib`, `spike_limit_mib`, el límite blando y `GOMEMLIMIT` siguiendo las recomendaciones de la documentación.",
               "Por ejemplo `limit_mib: 1600` (margen para memoria fuera del Go heap), `spike_limit_mib: 320` (20 % del límite duro) ⇒ límite blando $1600-320=1280$ MiB; `GOMEMLIMIT` ≈ 80 % del límite duro $=1280$ MiB. Con la memoria por encima de 1280 MiB el Collector entra en modo limitado (rechaza y fuerza GC)."))
    md(details("4 · (Diagnóstico) Las trazas llegan a Tempo pero los logs no llegan a Loki. `otelcol validate` pasa sin errores. El YAML define `otlp_http/loki` y el pipeline `logs` tiene `exporters: [debug]`. ¿Qué pasa y cómo lo detectas antes de desplegar?",
               "El exportador `otlp_http/loki` está **definido pero no usado**: el pipeline de logs solo exporta a `debug`. `validate` no lo considera error. Se detecta con el linter (`UNUSED`) o con un test que envíe un log de prueba y lo busque en Loki. Arreglo: `exporters: [otlp_http/loki]` (y quitar `debug`)."))
    md(details("5 · (Diagnóstico) Configuras `attributes` con `action: upsert` sobre la clave `name` esperando cambiar el nombre de los spans, y no cambia nada. ¿Por qué?",
               "El procesador `attributes` actúa sobre los **atributos** del span, no sobre su nombre. Para el nombre se usa el procesador `span` o `transform` (OTTL, p. ej. `set(span.name, ...)`)."))
    md(details("6 · (Transferencia) Plataforma en Kubernetes con 200 servicios, PII en algunos atributos y la intención de hacer *tail sampling* (módulo 18). Diseña los Collectors: ¿qué capas, qué procesadores en cada una y qué exportador entre capas?",
               "Capa 1 (**agente** DaemonSet): `memory_limiter`, `k8s_attributes`/`resource_detection`, `batch`, exportador OTLP al gateway. Capa 2 (**gateway**): redacción de PII (`attributes`/`redaction`/`transform`) **antes** del muestreo si no quieres que la PII llegue a ningún almacén, y `load_balancing` con `routing_key: traceID` hacia la capa 3. Capa 3 (réplicas con **tail sampling**): `memory_limiter`, `tail_sampling`, `batch`, exportadores a los backends. Cada capa con `sending_queue` y alertas en `otelcol_*`."))
    md(details("7 · (Transferencia) `otelcol_exporter_queue_size` ronda el 90 % de la capacidad durante horas y `send_failed` crece levemente; la latencia del backend (Tempo) se ha duplicado. ¿Añades réplicas del Collector?",
               "Probablemente **no**: es el signo de que el destino es el cuello de botella; más Collectors le meten más presión. Primero diagnosticar y escalar/optimizar el backend (o limitar la ingesta con muestreo, módulo 18). Subir `queue_size` da margen a costa de memoria; añadir `num_consumers` solo ayuda si el destino tiene capacidad."))
    md(details("8 · (Diagnóstico) Tu gateway acepta 10 000 spans en 5 minutos (`otelcol_receiver_accepted_spans`), el `filter` descarta 1 200 (`incoming_items − outgoing_items` del filtro) y el exportador a Tempo informa `sent_spans = 8 500`. ¿Se pierde algo? ¿Dónde miras primero?",
               "Esperabas 10 000 − 1 200 = **8 800** enviados; faltan **300** spans. Mira por orden: `otelcol_exporter_send_failed_spans` (fallos de entrega tras reintentos), `otelcol_exporter_enqueue_failed_spans` (no cupieron en la cola ⇒ pérdida) y `otelcol_receiver_refused_spans` (rechazos por `memory_limiter`; esos no cuentan como aceptados, pero el emisor los reintenta). También puede ser que parte aún esté **en cola** (`queue_size`) o que Tempo haya rechazado datos inválidos. La conservación `aceptado − descartado por filtros = enviado` es el test más sencillo de «no pierdo datos»."))

    md("""
    ---
    # 11 · Referencias

    - OpenTelemetry. *Collector: Architecture*, *Configuration*, *Resiliency*, *Scaling*, *Transforming telemetry*, *Troubleshooting*, *Internal telemetry* — <https://opentelemetry.io/docs/collector/architecture/> · <https://opentelemetry.io/docs/collector/configuration/> · <https://opentelemetry.io/docs/collector/resiliency/> · <https://opentelemetry.io/docs/collector/scaling/> · <https://opentelemetry.io/docs/collector/transforming-telemetry/> · <https://opentelemetry.io/docs/collector/troubleshooting/> · <https://opentelemetry.io/docs/collector/internal-telemetry/>
    - OpenTelemetry. Patrones de despliegue: *Gateway*, *Agent*, *No Collector* — <https://opentelemetry.io/docs/collector/deploy/gateway/> · <https://opentelemetry.io/docs/collector/deploy/agent/> · <https://opentelemetry.io/docs/collector/deploy/other/no-collector/>
    - OpenTelemetry Collector (repositorio). *Processor README* (procesadores recomendados y orden), *memorylimiterprocessor*, *batchprocessor*, *exporterhelper* (cola de envío, reintentos, *batching*) — <https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/README.md> · <https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/memorylimiterprocessor/README.md> · <https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/batchprocessor/README.md> · <https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md>
    - OpenTelemetry Collector Contrib. *transformprocessor*, *filterprocessor*, *attributesprocessor*, *OTTL*, *loadbalancingexporter* — <https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/transformprocessor/README.md> · <https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/README.md> · <https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/exporter/loadbalancingexporter/README.md>
    - Contenido verificado en el código fuente de la documentación (`open-telemetry/opentelemetry.io`, `content/en/docs/collector/{scaling,resiliency,configuration}.md`): escalar al 60-70 % de la cola y mínimo de réplicas (p. ej. tres), reintentos 5 min por defecto, cola persistente. Alloy: *public preview* según `grafana/alloy` (`docs/sources/shared/stability/public_preview_otel.md`).
    - OpenTelemetry. *Collector releases* (distribuciones) — <https://github.com/open-telemetry/opentelemetry-collector-releases>
    - Prometheus. *Using Prometheus as your OpenTelemetry backend* (receptor OTLP, `target_info`, atributos promocionados) — <https://prometheus.io/docs/guides/opentelemetry/>
    - Grafana Labs. *OpenTelemetry in Alloy* — <https://grafana.com/docs/alloy/latest/introduction/otel_alloy/>

    ## Siguiente
    Proyecto: escribe y valida **tu propio gateway** (PII, ruido, entorno, renombres, colas) hacia Tempo, Loki y Prometheus. Después, módulo 06: instrumentación automática.

    **Limpieza:** los Collectors de laboratorio se borran al salir del bloque `with`; si algo se queda colgado: `docker ps -a --filter name=otelcol-lab` y `docker rm -f`.
    """)
    code('''
if DOCKER and os.environ.get("RECORD_LAB"):                       # (solo para regenerar los resultados pregrabados del modo degradado)
    RECORD_FILE.write_text(json.dumps(LAB_ACC, ensure_ascii=False)); print("pregrabado actualizado:", RECORD_FILE)
''')
    nb.save(out)


# =====================================================================================================================
def _verify_solution() -> dict:
    """Comprueba (si hay Docker) que la solución del proyecto pasa linter, `otelcol validate` y los controles funcionales de la rúbrica."""
    sys.path.insert(0, str(COURSE))
    os.environ.setdefault("LLM_PROVIDER", "mock")
    ns: dict = {"ROOT": COURSE}
    for src in (OTEL_IMPORTS, LAB_SRC, CFGLINT_SRC):
        exec(src, ns)
    lint = ns["cfglint"](SOLUTION_CONFIG)
    bad = [f for f in lint if f["severity"] in ("error", "warn")]
    assert not bad, f"la solución del proyecto 05 no pasa el linter: {bad}"
    info = {"lint_info": sorted({f["rule"] for f in lint}), "docker": ns["docker_ok"]()}
    if info["docker"]:
        d = pathlib.Path(__import__("tempfile").mkdtemp()); (d / "c.yaml").write_text(SOLUTION_CONFIG); os.chmod(d / "c.yaml", 0o644)
        r = subprocess.run(["docker", "run", "--rm", "-v", f"{d / 'c.yaml'}:/c.yaml:ro", IMAGE, "validate", "--config=/c.yaml"], capture_output=True, text=True)
        assert r.returncode == 0, f"otelcol validate falla con la solución: {r.stdout}{r.stderr}"
        with ns["LabCollector"](ns["to_file_config"](SOLUTION_CONFIG)) as lab:
            ns["send_probe"](lab.otlp_http)
            sp, lg, mt = ns["flat_spans"](lab.read("traces.jsonl")), ns["flat_logs"](lab.read("logs.jsonl")), ns["flat_metrics"](lab.read("metrics.jsonl"))
        assert len(sp) == 5 and not any(s["name"] == "GET /healthz" for s in sp) and len(lg) == 2 and any(m["name"] == "supportops.probe.requests" for m in mt), (len(sp), len(lg), len(mt))
        assert all("@" not in str(s["attrs"].get("customer.email", "")) and "debug.prompt" not in s["attrs"] and "gen_ai.system" not in s["attrs"] for s in sp)
        info["functional"] = {"spans": len(sp), "logs": len(lg), "metrics": len(mt)}
    return info


def build_project() -> None:
    ver = _verify_solution()
    print("verificación de la solución 05:", ver)
    nb, out = nb_for(MOD, "05_proyecto_collector.ipynb", "Proyecto 05 · Tu propio gateway OpenTelemetry")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 05 · Configura un Collector que reciba OTLP y exporte trazas, métricas y logs a los tres backends

    | | |
    |---|---|
    | **Nivel** | 🟡 Intermedio |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Opcional `docker compose --profile core --profile metrics up -d` para el último control (R11). **Sin el stack** funcionan R1–R10 (con Docker) y R1–R8 sin Docker (solo linter y análisis del YAML) |
    | **RAM aproximada** | ≈ 0,1 GB por Collector de laboratorio; con el stack ≈ 0,5 GB |
    | **Prerrequisitos** | Lección `05_collector` (componentes, orden, `validate`, linter, métricas internas) y módulos 03-04 |
    | **Conexión** | Sustituyes el Collector del stack por **el tuyo**: aplica las políticas que se diseñaron en 03 (SDK), 04 (spec GenAI y PII) y el siguiente paso natural para los módulos 18 (muestreo) y 20 (privacidad) |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Seguridad y Plataforma exigen un **gateway** único de telemetría con estas políticas, aplicadas **sin tocar las aplicaciones**:

    | # | Requisito | Detalle |
    |---|---|---|
    | A | Recibir OTLP | gRPC `0.0.0.0:4317` y HTTP `0.0.0.0:4318` |
    | B | Tres destinos | **trazas → Tempo** (`otlp_grpc`, `tempo:4317`, sin TLS) · **logs → Loki** (`otlp_http`, `http://loki:3100/otlp`) · **métricas → Prometheus** (`otlp_http`, `http://prometheus:9090/api/v1/otlp`) |
    | C | Protección | `memory_limiter` primero, con límite duro > 0 y margen de picos ≤ 25 % del límite |
    | D | Ruido | descartar los spans llamados **`GET /healthz`** |
    | E | PII | `customer.email` **seudonimizado (hash)** y `debug.prompt` **eliminado**, en **trazas y logs** |
    | F | Entorno | `deployment.environment.name = lab-student` en **las tres señales** |
    | G | Migración (módulo 04) | en spans: `gen_ai.system` → `gen_ai.provider.name` y `gen_ai.usage.prompt_tokens` → `gen_ai.usage.input_tokens` (copiar y borrar el antiguo) |
    | H | Resiliencia | cada exportador de red con `sending_queue` (`queue_size ≥ 1000`) y `retry_on_failure` (`max_elapsed_time ≥ 60s`) |
    | I | Operación | `health_check` activo y métricas internas del Collector en `:8888`; `batch` en todos los pipelines |

    ## Datos

    La **telemetría de prueba** la genera `send_probe(endpoint)`: 5 spans `chat mock-small` (con `customer.email`, `debug.prompt`, `gen_ai.system`, `gen_ai.usage.prompt_tokens`), 3 spans `GET /healthz`, 2 logs con `customer.email` y un contador `supportops.probe.requests`. Es **determinista** (cantidades fijas): no depende de tu máquina.
    Cadena de resiliencia: stack local → contenedor de laboratorio con exportador `file` (**sin** backends) → análisis estático del YAML (linter) si no hay Docker.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución, Collector contrib 0.162.0) |
    |---|---|---|---|
    | R1 | YAML válido | `cfglint` sin **errores** | 0 errores |
    | R2 | Buenas prácticas | `cfglint` sin **avisos** (nada definido y sin usar, orden correcto, `memory_limiter`…) | 0 avisos (la solución tampoco tiene informativos{(': ' + ', '.join(ver['lint_info'])) if ver['lint_info'] else ''}) |
    | R3 | Receptor | `otlp` con gRPC `0.0.0.0:4317` y HTTP `0.0.0.0:4318` | cumple |
    | R4 | Tres pipelines y destinos | traces→`otlp_grpc` a `tempo:4317`; logs→`otlp_http` a `loki:3100/otlp`; metrics→`otlp_http` a `prometheus:9090` | 3/3 |
    | R5 | Orden | en los 3 pipelines `memory_limiter` primero y `batch` último; en trazas el filtro va antes de los procesadores de atributos | cumple |
    | R6 | `memory_limiter` | `limit_mib > 0` y `spike_limit_mib ≤ 25 %` de `limit_mib` | cumple (solución: 400 / 80 = 20 %) |
    | R7 | Resiliencia | cada exportador usado: `queue_size ≥ 1000` y `max_elapsed_time ≥ 60 s` | 3/3 exportadores |
    | R8 | Operación | `health_check` en `service.extensions` y lector `pull` de métricas internas en el puerto 8888 | cumple |
    | R9 | `otelcol validate` | La configuración pasa `validate` con la imagen 0.162.0 (**requiere Docker**) | exit 0 |
    | R10 | Comportamiento | Con `send_probe` y exportadores `file`: 5 spans a la salida (0 de salud), 0 correos en claro y 0 `debug.prompt` en spans y logs, renombres aplicados, entorno en trazas, logs y métricas (**requiere Docker**) | todos los controles |
    | R11 | Extremo a extremo | Tu config, conectada al stack, hace llegar los datos de prueba a **Tempo, Loki y Prometheus** (**requiere el stack**) | 3/3 |

    > 📏 R1–R8 son análisis del YAML; R9–R11 ejecutan el Collector real. Los umbrales son lo que mide la solución de referencia. R10 es **funcional**: da igual *cómo* lo escribas, importa que la telemetría que sale sea la correcta.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + OTEL_IMPORTS + '''
STACK = check_stack(["tempo", "loki", "prometheus"])
logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)
''' + LAB_SRC + '''
DOCKER = docker_ok()
print("Docker disponible:", DOCKER)
''')
    md("""
    ## Herramientas que ya tienes (de la lección)

    - `cfglint(texto_yaml)` — linter offline (reglas `UNKNOWN`, `UNDEF`, `SIGNAL`, `ORDER`, `UNUSED`…).
    - `otelcol_validate(texto_yaml)` — `otelcol validate` en un contenedor (definido abajo).
    - `LabCollector(config)` — Collector de laboratorio; `send_probe(endpoint)` — telemetría de prueba; `to_file_config(cfg)` — la misma config con exportadores `file`.
    """)
    code(CFGLINT_SRC + '''
def otelcol_validate(cfg_text: str) -> tuple[bool, str]:
    d = pathlib.Path(tempfile.mkdtemp()); (d / "c.yaml").write_text(cfg_text); os.chmod(d / "c.yaml", 0o644)
    r = subprocess.run(["docker", "run", "--rm", "-v", f"{d / 'c.yaml'}:/c.yaml:ro", IMAGE, "validate", "--config=/c.yaml"], capture_output=True, text=True)
    shutil.rmtree(d, ignore_errors=True)
    return r.returncode == 0, " ".join((r.stdout + r.stderr).split())[:300]
''')

    # ----------------------------------------------------------------------------------------- paso 1
    md("""
    ## Paso 1 · Escribe la configuración

    **TODO 1.** Completa `CONFIG` (un YAML en una cadena) para cumplir los requisitos A-I. El esqueleto trae el receptor y la extensión; **faltan** los procesadores, los exportadores y los pipelines (y el bloque `service`).
    Aplica lo aprendido: el **orden** de la lección (sección 2), los nombres canónicos 0.162 (`otlp_grpc`, `otlp_http`), y las sintaxis de `filter` (condición OTTL sobre el nombre), `attributes` (acciones `hash`/`delete`), `resource` (`upsert`) y `transform` (OTTL con `set(...)` y `delete_key(...)`).

    > 🧩 **Trabaja en tres iteraciones y ejecuta el linter (paso 2) entre ellas:** (1a) define los procesadores y comprueba que el linter solo se queja de que están sin usar; (1b) define los exportadores; (1c) escribe los tres pipelines. Un error por iteración es mucho más fácil de localizar que diez a la vez, y el linter te dice cuál es.
    """)
    md(hint(1, "Procesadores que necesitas (en este orden en los tres pipelines cuando apliquen): `memory_limiter` → `filter/health` (solo trazas) → `attributes/pii` (trazas y logs) → `resource/lab` (las tres) → `transform/semconv` (solo trazas) → `batch`. Cada uno se **define** en `processors:` y se **activa** en el pipeline."))
    md(hint(2, """Sintaxis (compruébala con `cfglint` y `otelcol_validate`):
```yaml
filter/health:
  error_mode: ignore
  traces:
    span:
      - 'name == "GET /healthz"'
attributes/pii:
  actions:
    - {key: customer.email, action: hash}
    - {key: debug.prompt, action: delete}
resource/lab:
  attributes:
    - {key: deployment.environment.name, value: lab-student, action: upsert}
```"""))
    md(hint(3, """Renombrar en spans con OTTL (copiar y borrar):
```yaml
transform/semconv:
  error_mode: ignore
  trace_statements:
    - set(span.attributes["gen_ai.provider.name"], span.attributes["gen_ai.system"]) where span.attributes["gen_ai.system"] != nil
    - delete_key(span.attributes, "gen_ai.system")
```
Y lo mismo con `gen_ai.usage.prompt_tokens` → `gen_ai.usage.input_tokens`."""))
    md(hint(4, """Exportadores (uno por backend, con cola y reintentos explícitos):
```yaml
otlp_grpc/tempo:
  endpoint: tempo:4317
  tls: {insecure: true}
  sending_queue: {enabled: true, queue_size: 2000}
  retry_on_failure: {enabled: true, max_elapsed_time: 120s}
otlp_http/loki:        {endpoint: "http://loki:3100/otlp", ...}
otlp_http/prometheus:  {endpoint: "http://prometheus:9090/api/v1/otlp", ...}
```
Métricas internas: `service.telemetry.metrics.readers: [{pull: {exporter: {prometheus: {host: 0.0.0.0, port: 8888}}}}]`."""))
    code('''
CONFIG = """# Collector del alumno · gateway del laboratorio SupportOps
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors: {}        # TODO 1a: memory_limiter, filter/health, attributes/pii, resource/lab, transform/semconv, batch

exporters: {}         # TODO 1b: otlp_grpc/tempo, otlp_http/loki, otlp_http/prometheus (con sending_queue y retry_on_failure)

extensions:
  health_check:
    endpoint: 0.0.0.0:13133

service:
  extensions: [health_check]
  pipelines: {}       # TODO 1c: traces, logs y metrics (receivers, processors EN ORDEN, exporters) y service.telemetry para las métricas internas en :8888
"""
print(len(CONFIG.splitlines()), "líneas")
''')

    md("""
    ## Paso 2 · Comprueba sin ejecutar nada: el linter

    Itera hasta que no queden **errores** ni **avisos** (los de nivel *info* son opcionales).
    """)
    code('''
def show_lint(cfg):
    F = cfglint(cfg)
    df = pd.DataFrame(F, columns=["rule", "severity", "where", "msg"]) if F else pd.DataFrame(columns=["rule", "severity", "where", "msg"])
    print(f"{(df.severity == 'error').sum()} errores · {(df.severity == 'warn').sum()} avisos · {(df.severity == 'info').sum()} informativos")
    return df
show_lint(CONFIG)
''')

    md("""
    ## Paso 3 · `otelcol validate` (requiere Docker)
    """)
    code('''
if DOCKER:
    ok, msg = otelcol_validate(CONFIG); print("otelcol validate:", "✅ OK" if ok else "❌ " + msg)
else:
    print("Sin Docker: salta este paso (el linter del paso 2 es tu red de seguridad).")
''')

    md("""
    ## Paso 4 · Comprueba el comportamiento sobre telemetría real (requiere Docker)

    Ejecutamos **tu configuración** con los exportadores sustituidos por `file` (`to_file_config`: mismos receptores, procesadores y pipelines), enviamos la telemetría de prueba y leemos lo que **sale**:
    """)
    code('''
def functional_test(cfg: str) -> dict:
    with LabCollector(to_file_config(cfg)) as lab:
        send_probe(lab.otlp_http, n_chat=5, n_health=3, n_logs=2)
        return {"spans": flat_spans(lab.read("traces.jsonl")), "logs": flat_logs(lab.read("logs.jsonl")), "metrics": flat_metrics(lab.read("metrics.jsonl"))}

if DOCKER:
    try:
        FT = functional_test(CONFIG)
        print(f"salen {len(FT['spans'])} spans, {len(FT['logs'])} logs, {len(FT['metrics'])} métricas")
        if FT["spans"]: print("ejemplo de span:", FT["spans"][0]["name"], {k: (v[:10] + '…' if isinstance(v, str) and len(v) > 10 else v) for k, v in FT["spans"][0]["attrs"].items()})
    except Exception as e:
        FT = None; print("No se pudo ejecutar (¿falta completar la configuración?):", str(e)[:300])
else:
    FT = None; print("Sin Docker: salta este paso.")
''')

    md("""
    ## Paso 5 · Extremo a extremo con el stack (opcional)

    Con el stack arriba (`docker compose --profile core --profile metrics up -d`), **tu** Collector se conecta a la red de Compose (`agentobs_default`: ahí se resuelven `tempo`, `loki` y `prometheus`), recibe la telemetría de prueba y la entrega. Comprobamos que **llega a los tres backends**.
    Es **lectura**: no tocamos el stack, y tu Collector usa puertos aleatorios de tu máquina (el del stack sigue intacto).
    """)
    code('''
def end_to_end(cfg: str, wait_s: int = 60) -> dict:
    res = {"tempo": 0, "loki": 0, "prometheus": 0.0}
    with LabCollector(cfg, network="agentobs_default") as lab:
        send_probe(lab.otlp_http, n_chat=5, n_health=3, n_logs=2)
        t0 = time.time()
        while time.time() - t0 < wait_s and not (res["tempo"] >= 5 and res["loki"] >= 2 and res["prometheus"] >= 7):
            try:
                res["tempo"] = len(backends.tempo_search('{ resource.service.name = "supportops-probe" && span.gen_ai.provider.name = "mock" }', minutes=15, limit=50).get("traces", []))
                res["loki"] = len(backends.loki_query('{service_name="supportops-probe"} |= "ticket recibido"', minutes=15, limit=50))
                pr = backends.prom_query('sum(supportops_probe_requests_total{job="supportops-probe"})'); res["prometheus"] = float(pr[0]["value"][1]) if pr else 0.0
            except backends.BackendError:
                pass
            time.sleep(3)
    return res

if STACK.degraded or not DOCKER:
    E2E = None; print("Modo degradado: levanta el stack (", STACK.command, ") y vuelve a ejecutar.")
else:
    try:
        E2E = end_to_end(CONFIG); print("llegado a los backends:", E2E)
    except Exception as e:
        E2E = None; print("No se pudo ejecutar:", str(e)[:300])
''')

    # ----------------------------------------------------------------------------------------- rúbrica
    md("""
    ## Paso 6 · Rúbrica
    """)
    code('''
def _dur_s(v) -> float:
    m = re.fullmatch(r"(\\d+(?:\\.\\d+)?)(ms|s|m|h)", str(v).strip()); return float(m[1]) * {"ms": 1e-3, "s": 1, "m": 60, "h": 3600}[m[2]] if m else 0.0

def run_rubric():
    rows = []
    def add(r, desc, ok, detail=""): rows.append({"criterio": r, "descripción": desc, "resultado": ("✅ OK" if ok else "❌ FALLA") if ok is not None else "⏭ no evaluable", "detalle": detail})
    F = cfglint(CONFIG); errs = [f for f in F if f["severity"] == "error"]; warns = [f for f in F if f["severity"] == "warn"]
    add("R1", "cfglint sin errores", not errs, "; ".join(f"{f['rule']}@{f['where']}" for f in errs[:3]))
    add("R2", "cfglint sin avisos", not warns and not errs, "; ".join(f"{f['rule']}@{f['where']}" for f in warns[:3]))
    try: cfg = yaml.safe_load(CONFIG) or {}
    except Exception: cfg = {}
    ex, pr, pipes = cfg.get("exporters") or {}, cfg.get("processors") or {}, (cfg.get("service") or {}).get("pipelines") or {}
    proto = (((cfg.get("receivers") or {}).get("otlp") or {}).get("protocols") or {})
    add("R3", "receptor otlp gRPC 4317 + HTTP 4318 en 0.0.0.0", (proto.get("grpc") or {}).get("endpoint") == "0.0.0.0:4317" and (proto.get("http") or {}).get("endpoint") == "0.0.0.0:4318")
    def pipe(sig): return next((p for n, p in pipes.items() if ctype(n) == sig), None) or {}
    def exps(sig): return [(ctype(k), str((ex.get(k) or {}).get("endpoint", ""))) for k in pipe(sig).get("exporters") or [] if k in ex]
    ok4 = {"traces": any(t == "otlp_grpc" and "tempo:4317" in e for t, e in exps("traces")),
           "logs": any(t == "otlp_http" and "loki:3100/otlp" in e for t, e in exps("logs")),
           "metrics": any(t in ("otlp_http", "prometheus_remote_write") and "prometheus:9090" in e for t, e in exps("metrics"))}
    add("R4", "traces→Tempo, logs→Loki, metrics→Prometheus", all(ok4.values()), str(ok4))
    def chain(sig): return [ctype(k) for k in pipe(sig).get("processors") or []]
    order_ok = all(chain(s)[:1] == ["memory_limiter"] and chain(s)[-1:] == ["batch"] for s in ("traces", "logs", "metrics"))
    ct = chain("traces"); order_ok = order_ok and "filter" in ct and all(ct.index("filter") < ct.index(x) for x in ("attributes", "resource", "transform") if x in ct)
    add("R5", "memory_limiter primero, batch último, filtro antes de enriquecer", order_ok, " | ".join(f"{s}: {chain(s)}" for s in ("traces", "logs", "metrics")))
    ml = next((c for k, c in pr.items() if ctype(k) == "memory_limiter"), None) or {}
    add("R6", "memory_limiter: limit_mib > 0 y spike ≤ 25 %", bool(ml.get("limit_mib")) and ml.get("spike_limit_mib", 0) <= 0.25 * ml.get("limit_mib", 0), f"limit={ml.get('limit_mib')} spike={ml.get('spike_limit_mib')}")
    used_ex = {k for s in ("traces", "logs", "metrics") for k in pipe(s).get("exporters") or [] if k in ex}
    good = [k for k in used_ex if ((ex[k] or {}).get("sending_queue") or {}).get("queue_size", 0) >= 1000 and _dur_s(((ex[k] or {}).get("retry_on_failure") or {}).get("max_elapsed_time")) >= 60]
    add("R7", "cada exportador: queue_size ≥ 1000 y max_elapsed_time ≥ 60 s", bool(used_ex) and len(good) == len(used_ex) and len(used_ex) >= 3, f"{len(good)}/{len(used_ex)} exportadores")
    readers = ((((cfg.get("service") or {}).get("telemetry") or {}).get("metrics") or {}).get("readers")) or []
    ok_int = any(((r.get("pull") or {}).get("exporter") or {}).get("prometheus", {}).get("port") == 8888 for r in readers if isinstance(r, dict))
    add("R8", "health_check + métricas internas en :8888", any(ctype(e) == "health_check" for e in (cfg.get("service") or {}).get("extensions") or []) and ok_int)
    if DOCKER:
        ok, msg = otelcol_validate(CONFIG); add("R9", "otelcol validate", ok, "" if ok else msg[:120])
        try:
            T = functional_test(CONFIG); sp, lg, mt = T["spans"], T["logs"], T["metrics"]
            checks = {"5 spans (0 healthz)": len(sp) == 5 and not any(s["name"] == "GET /healthz" for s in sp),
                      "sin correo en claro (spans y logs)": all("@" not in str(x["attrs"].get("customer.email", "")) for x in sp + lg) and bool(sp) and bool(lg),
                      "sin debug.prompt": not any("debug.prompt" in x["attrs"] for x in sp + lg),
                      "renombres": bool(sp) and all("gen_ai.system" not in s["attrs"] and s["attrs"].get("gen_ai.provider.name") == "mock" and "gen_ai.usage.prompt_tokens" not in s["attrs"] and "gen_ai.usage.input_tokens" in s["attrs"] for s in sp),
                      "entorno en trazas, logs y métricas": bool(sp) and bool(lg) and bool(mt) and all(x["resource"].get("deployment.environment.name") == "lab-student" for x in sp + lg + mt)}
            add("R10", "comportamiento sobre telemetría real", all(checks.values()), ", ".join(k for k, v in checks.items() if not v) or "todos los controles")
        except Exception as e:
            add("R10", "comportamiento sobre telemetría real", False, str(e)[:120])
    else:
        add("R9", "otelcol validate", None, "sin Docker"); add("R10", "comportamiento", None, "sin Docker")
    if DOCKER and not STACK.degraded:
        try:
            e = end_to_end(CONFIG, wait_s=45); add("R11", "llega a Tempo, Loki y Prometheus", e["tempo"] >= 5 and e["loki"] >= 2 and e["prometheus"] >= 7, str(e))
        except Exception as e:
            add("R11", "llega a los tres backends", False, str(e)[:120])
    else:
        add("R11", "llega a los tres backends", None, "sin stack/Docker")
    return pd.DataFrame(rows).set_index("criterio")

display(run_rubric())
''')

    md("""
    ---
    ## Retos extra (nivel experto)

    1. **Métricas RED desde las trazas:** añade el **conector** `span_metrics` (sale de un pipeline de trazas y entra en uno de métricas) y comprueba en Prometheus las métricas de llamadas y duración por servicio. ¿Qué pasa con su cardinalidad si pones `customer.email` como dimensión?
    2. **Cola persistente:** añade la extensión `file_storage` y úsala en `sending_queue.storage` del exportador de Tempo; reinicia el Collector con datos en cola y demuestra que no se pierden.
    3. **Agente → gateway:** escribe una segunda configuración de **agente** (receptor OTLP, `resource_detection`, exportador `otlp_grpc` hacia tu gateway) y encadénalos con `LabCollector`. ¿Qué procesadores pondrías en cada capa y por qué?
    4. **Variables de entorno:** parametriza endpoints y límites con `${env:TEMPO_ENDPOINT:-tempo:4317}` y `${env:LIMIT_MIB:-400}`; ¿cómo las inyectarías en Compose y en Kubernetes?
    5. **Alerta:** escribe la expresión PromQL de una alerta sobre las métricas internas que avise cuando la cola de un exportador supere el 70 % durante 5 minutos (`otelcol_exporter_queue_size / otelcol_exporter_queue_capacity`).

    ## Reflexión (producción e hilo conductor)

    - Tu `attributes/pii` aplica `hash` al correo. ¿Qué garantía da realmente un hash SHA-256 **sin sal** sobre un espacio de correos acotado? ¿Qué alternativa (sal secreta, tokenización, eliminar) elegirías y qué perdería la correlación?
    - Has puesto la **política de PII en el gateway**. ¿Qué ocurre con los datos *antes* de llegar a él (agente, red, logs del propio Collector con el exportador `debug`)?
    - El `filter/health` descarta spans por nombre exacto. ¿Qué pasaría si un equipo cambia el nombre a `GET /health`? ¿Cómo detectarías **datos que desaparecen** por un filtro (pista: `otelcol_processor_incoming_items` frente a `outgoing_items`)?
    - En el módulo 18 sustituirás la «cola y reintentos» por **muestreo**; en el 19 desplegarás este gateway con Helm. ¿Qué parámetros de tu configuración deberían venir de variables de entorno o de *values*?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa (la verificada con el linter, `otelcol validate` y los controles funcionales) y la rúbrica con ella.
    """)
    code('CONFIG = """' + SOLUTION_CONFIG + '"""\n')
    code('''
# Re-ejecuta la rúbrica con la solución
display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_readme() -> None:
    (COURSE / MOD / "README.md").write_text("""# Módulo 05 · El OpenTelemetry Collector

🟡 Intermedio · ≈ 4 h 30 min · **Docker** para los experimentos con el Collector real (contenedores efímeros con puertos aleatorios, **no** necesitan el stack). Sin Docker: modo degradado (resultados pregrabados y linter offline). Opcional `--profile core --profile metrics` para ver el stack real y el control extremo a extremo del proyecto.

> ⚠️ Verificado con `otel/opentelemetry-collector-contrib:0.162.0` (la imagen del stack). El Collector es `0.x`: nombres de componente y de opciones cambian; fija la versión.

## Qué aprenderás
- **Por qué** un Collector (patrones *sin Collector*, *agente*, *gateway*, *dos niveles*) y la anatomía de un *pipeline*: receivers, processors, exporters, connectors, extensions; fan-out síncrono e instancias por pipeline.
- El **orden recomendado de procesadores** (documentación oficial) demostrado con un Collector «de juguete» hecho a mano, y el efecto del fan-out bloqueante.
- La **configuración del stack, línea a línea**; `otelcol validate` frente a un **linter offline propio** (16 reglas) y siete configuraciones rotas a propósito.
- Experimentos con el **Collector real**: efecto de `batch`, PII/ruido/entorno con `attributes`/`filter`/`resource`, **`memory_limiter` (503 al SDK)** y **cola de envío** (llenado y rechazo hacia atrás), con las **métricas internas `otelcol_*`** y la conservación de spans.
- Resiliencia y escalado: colas, reintentos, cola persistente, `GOMEMLIMIT`, cuándo escalar (60-70 % de la cola) y cuándo no.

## Archivos
| Archivo | Contenido |
|---|---|
| `05_collector.ipynb` | Lección (teoría + código + 10 gráficos + autoevaluación) |
| `05_proyecto_collector.ipynb` | Proyecto: escribe tu gateway (PII, ruido, entorno, renombres GenAI, colas) hacia Tempo, Loki y Prometheus; rúbrica de 11 criterios (análisis estático, `validate`, comportamiento real y extremo a extremo) |
| `collector_components_0.162.0.json` | Componentes de la distribución contrib 0.162.0 y su estabilidad por señal (salida de `docker run --rm otel/opentelemetry-collector-contrib:0.162.0 components`); lo usa el linter |
| `lab_results_recorded.json` | Resultados pregrabados de los experimentos (modo degradado sin Docker). Se regeneran con `RECORD_LAB=1` al ejecutar la lección con Docker |

## Servicios necesarios
Docker (imagen del Collector ≈ 0,5 GB en disco). Stack `core` + `metrics` solo para el control R11 del proyecto y la conservación de spans de la lección.

## Lecturas
- OpenTelemetry, *Collector* (arquitectura, configuración, resiliencia, escalado, telemetría interna) — <https://opentelemetry.io/docs/collector/>
- OpenTelemetry Collector, *Processor README* (procesadores recomendados y orden) — <https://github.com/open-telemetry/opentelemetry-collector/blob/main/processor/README.md>
- OpenTelemetry Collector, *exporterhelper* (cola de envío, reintentos, batching) — <https://github.com/open-telemetry/opentelemetry-collector/blob/main/exporter/exporterhelper/README.md>
- Prometheus, *Using Prometheus as your OpenTelemetry backend* — <https://prometheus.io/docs/guides/opentelemetry/>

## Siguiente
`06_autoinstrumentacion`: OpenLIT y OpenLLMetry frente a la instrumentación manual de los módulos 03-04.
""", encoding="utf-8")
    print("OK README 05")


if __name__ == "__main__":
    build_lesson()
    build_project()
    build_readme()
