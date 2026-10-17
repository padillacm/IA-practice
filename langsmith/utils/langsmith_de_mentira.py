"""Un LangSmith simulado, con estado, que el SDK de verdad se cree.

**Por qué existe.** El curso se escribió sin poder alcanzar el servicio, así que las
celdas marcadas `@online` estaban escritas contra la firma verificada de cada función
pero **nunca se habían ejecutado**. Era la única parte del material que pedía fe.

Esto cierra esa deuda hasta donde se puede cerrar sin una clave: un servidor de mentira
que implementa las rutas HTTP que el SDK usa, guarda estado entre llamadas y devuelve
respuestas con la forma que el cliente sabe parsear. Las celdas `@online` se ejecutan
contra él en la CI, y si una tiene un nombre de argumento mal, consume una respuesta que
no existe o encadena dos llamadas que no encajan, **falla**.

**Qué demuestra y qué no.** Demuestra que el código de esas celdas corre: que los
argumentos son los que el SDK acepta, que las respuestas se consumen bien, que el
encadenado de llamadas se sostiene. **No** demuestra la semántica del servidor real —si
LangSmith versiona un dataset como aquí se supone, o si un filtro devuelve lo que crees.
Para eso hace falta una clave, y el `README` lo dice donde toca.

Se usa a través de `utils.curso`, no directamente:

    LANGSMITH_SIMULADO=1 uv run _tools/ejecutar_notebooks.py
"""

from __future__ import annotations

import datetime
import json
import re
import uuid
from typing import Any


def _ahora() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


#: Un tenant fijo: el curso lo imprime en algún sitio y conviene que no cambie por celda.
TENANT = "00000000-0000-4000-8000-000000000001"


class LangSmithDeMentira:
    """El servicio. Guarda el estado en diccionarios y responde a rutas."""

    def __init__(self) -> None:
        self.proyectos: dict[str, dict] = {}
        self.ejecuciones: dict[str, dict] = {}
        self.datasets: dict[str, dict] = {}
        self.ejemplos: dict[str, dict] = {}
        self.realimentacion: dict[str, dict] = {}
        self.configuraciones: dict[str, dict] = {}
        self.colas: dict[str, dict] = {}
        self.repos: dict[str, dict] = {}
        self.commits: dict[str, list[dict]] = {}
        self.compartidas: dict[str, str] = {}
        self.peticiones: list[tuple[str, str]] = []
        self._proyecto("default")

    # ---------------------------------------------------------------- utilidades

    def _proyecto(self, nombre: str) -> dict:
        for p in self.proyectos.values():
            if p["name"] == nombre:
                return p
        p = {"id": _id(), "name": nombre, "tenant_id": TENANT,
             "start_time": _ahora(), "reference_dataset_id": None, "extra": {}}
        self.proyectos[p["id"]] = p
        return p

    def _dataset_por_nombre(self, nombre: str) -> dict | None:
        return next((d for d in self.datasets.values() if d["name"] == nombre), None)

    # ------------------------------------------------------------------- el ruteo

    def responder(self, metodo: str, ruta: str, consulta: dict, cuerpo: Any):
        """Devuelve (codigo, objeto_json). `ruta` viene ya sin el dominio ni la query."""
        self.peticiones.append((metodo, ruta))
        for patron, manejador in self._rutas():
            if patron[0] != metodo:
                continue
            m = re.fullmatch(patron[1], ruta)
            if m:
                return manejador(self, m, consulta, cuerpo or {})
        # Lo que no está implementado devuelve vacío en vez de romper: el objetivo es
        # ejecutar las celdas del curso, no reimplementar LangSmith.
        return 200, {}

    @staticmethod
    def _rutas():
        R = LangSmithDeMentira
        return [
            (("GET", r"/info"), R._info),
            (("GET", r"/settings"), R._ajustes),
            (("GET", r"/sessions"), R._listar_proyectos),
            (("GET", r"/sessions/([0-9a-f-]+)"), R._leer_proyecto),
            (("POST", r"/sessions"), R._crear_proyecto),
            (("GET", r"/runs/([0-9a-f-]+)/share"), R._compartida),
            (("PUT", r"/runs/([0-9a-f-]+)/share"), R._compartir),
            (("GET", r"/runs/([0-9a-f-]+)"), R._leer_ejecucion),
            (("POST", r"/runs/query"), R._consultar_ejecuciones),
            (("POST", r"/runs/stats"), R._estadisticas),
            (("GET", r"/runs/stats"), R._estadisticas),
            (("POST", r"/runs/multipart"), R._ingerir),
            (("POST", r"/runs/batch"), R._ingerir),
            (("POST", r"/runs"), R._crear_ejecucion),
            (("PATCH", r"/runs/([0-9a-f-]+)"), R._actualizar_ejecucion),
            (("POST", r"/datasets/comparative"), R._experimento_comparativo),
            (("POST", r"/datasets"), R._crear_dataset),
            (("GET", r"/datasets"), R._listar_datasets),
            (("GET", r"/datasets/([0-9a-f-]+)"), R._leer_dataset),
            (("GET", r"/datasets/([0-9a-f-]+)/versions"), R._versiones),
            (("PUT", r"/datasets/([0-9a-f-]+)/tags"), R._etiquetar),
            (("GET", r"/datasets/([0-9a-f-]+)/splits"), R._listar_splits),
            (("PUT", r"/datasets/([0-9a-f-]+)/splits"), R._actualizar_splits),
            (("GET", r"/datasets/([0-9a-f-]+)/versions/diff"), R._diferencia),
            (("GET", r"/datasets/([0-9a-f-]+)/openai_ft"), R._finetuning),
            (("POST", r"/datasets/upload"), R._subir_csv),
            (("POST", r"/examples/bulk"), R._crear_ejemplos),
            (("POST", r"/examples"), R._crear_ejemplos),
            (("GET", r"/examples"), R._listar_ejemplos),
            (("GET", r"/examples/([0-9a-f-]+)"), R._leer_ejemplo),
            (("PATCH", r"/examples/([0-9a-f-]+)"), R._actualizar_ejemplo),
            (("PATCH", r"/examples"), R._actualizar_ejemplos),
            (("POST", r"/feedback"), R._crear_realimentacion),
            (("GET", r"/feedback"), R._listar_realimentacion),
            (("POST", r"/feedback/tokens"), R._token_de_realimentacion),
            (("POST", r"/feedback/tokens/([0-9a-f-]+)"), R._usar_token),
            (("POST", r"/feedback-configs"), R._crear_configuracion),
            (("GET", r"/feedback-configs"), R._listar_configuraciones),
            (("POST", r"/annotation-queues"), R._crear_cola),
            (("GET", r"/annotation-queues"), R._listar_colas),
            (("POST", r"/annotation-queues/([0-9a-f-]+)/runs"), R._encolar),
            (("GET", r"/repos/(.+)"), R._leer_repo),
            (("POST", r"/repos"), R._crear_repo),
            (("GET", r"/commits/([^/]+)/([^/]+)/(.+)"), R._leer_commit),
            (("GET", r"/commits/([^/]+)/([^/]+)"), R._listar_commits),
            (("POST", r"/commits/([^/]+)/([^/]+)"), R._crear_commit),
        ]

    # ------------------------------------------------------------------ manejadores

    def _info(self, m, q, b):
        return 200, {"version": "0.11.0", "instance_flags": {},
                     "batch_ingest_config": {"use_multipart_endpoint": True,
                                             "size_limit": 100, "size_limit_bytes": 20_000_000,
                                             "scale_up_qsize_trigger": 1000,
                                             "scale_up_nthreads_limit": 4,
                                             "scale_down_nempty_trigger": 4}}

    def _ajustes(self, m, q, b):
        return 200, {"id": TENANT, "tenant_handle": "curso", "display_name": "Curso",
                     "config": {}, "created_at": _ahora()}

    def _listar_proyectos(self, m, q, b):
        nombre = q.get("name")
        salida = [p for p in self.proyectos.values() if not nombre or p["name"] == nombre]
        if nombre and not salida:
            salida = [self._proyecto(nombre)]
        return 200, salida

    def _leer_proyecto(self, m, q, b):
        p = self.proyectos.get(m.group(1))
        if p is None:
            p = self._proyecto(f"proyecto-{m.group(1)[:8]}")
        if p.get("reference_dataset_id") is None:
            # Un experimento siempre corre sobre un dataset: sin esto,
            # `evaluate_comparative` se niega con «A reference dataset is required».
            id_dataset = next(iter(self.datasets), None)
            if id_dataset is None:
                _, d = self._crear_dataset(None, {}, {"name": "conjunto-del-experimento"})
                id_dataset = d["id"]
            p["reference_dataset_id"] = id_dataset
            self._semilla_de_ejemplos(id_dataset)
        # `TracerSessionResult` (lo que devuelve leer un experimento) trae además los
        # agregados que la interfaz enseña arriba del todo.
        return 200, {**p, "run_count": 32, "latency_p50": 0.8, "latency_p99": 2.9,
                     "total_tokens": 13_440, "prompt_tokens": 12_160,
                     "completion_tokens": 1_280, "total_cost": 0.0384,
                     "last_run_start_time": _ahora(), "error_rate": 0.0,
                     "feedback_stats": {"acierto": {"n": 32, "avg": 0.78}}}

    def _crear_proyecto(self, m, q, b):
        return 200, self._proyecto(b.get("name", "sin-nombre"))

    def _crear_ejecucion(self, m, q, b):
        b.setdefault("id", _id())
        self.ejecuciones[str(b["id"])] = b
        return 200, {}

    def _actualizar_ejecucion(self, m, q, b):
        self.ejecuciones.setdefault(m.group(1), {}).update(b)
        return 200, {}

    def _ingerir(self, m, q, b):
        return 200, {}

    def _plantilla_de_ejecucion(self, id_ejecucion: str) -> dict:
        guardada = self.ejecuciones.get(id_ejecucion, {})
        proyecto = next(iter(self.proyectos.values()))
        return {"id": id_ejecucion, "name": guardada.get("name", "atender_ticket"),
                "run_type": guardada.get("run_type", "chain"),
                "start_time": guardada.get("start_time", _ahora()),
                "end_time": guardada.get("end_time", _ahora()),
                "trace_id": guardada.get("trace_id", id_ejecucion),
                "session_id": proyecto["id"],
                "inputs": guardada.get("inputs", {"asunto": "Cobro duplicado",
                                                  "mensaje": "Me han cobrado dos veces."}),
                "outputs": guardada.get("outputs", {"categoria": "facturacion"}),
                "extra": guardada.get("extra", {"metadata": {"plan": "free"}}),
                "total_tokens": 420, "prompt_tokens": 380, "completion_tokens": 40,
                "total_cost": 0.0012, "prompt_cost": 0.0009, "completion_cost": 0.0003,
                "error": None, "tags": guardada.get("tags", [])}

    def _leer_ejecucion(self, m, q, b):
        return 200, self._plantilla_de_ejecucion(m.group(1))

    def _consultar_ejecuciones(self, m, q, b):
        cuantas = min(int(b.get("limit") or 5), 5)
        return 200, {"runs": [self._plantilla_de_ejecucion(_id()) for _ in range(cuantas)],
                     "cursors": {}}

    def _estadisticas(self, m, q, b):
        return 200, {"run_count": 128, "latency_p50": 0.9, "latency_p99": 3.4,
                     "total_tokens": 53_760, "prompt_tokens": 48_640,
                     "completion_tokens": 5_120, "total_cost": 0.1536,
                     "error_rate": 0.031, "median_tokens": 420,
                     "first_token_p50": 0.35, "first_token_p99": 1.2,
                     "feedback_stats": {"acierto": {"n": 128, "avg": 0.86}}}

    def _compartida(self, m, q, b):
        # El servicio real devuelve el token si la traza está compartida. Aquí se
        # comparte la primera vez que se pregunta, para que el notebook 16 pueda
        # enseñar las dos ramas sin montar estado a mano.
        token = self.compartidas.setdefault(m.group(1), _id())
        return 200, {"share_token": token}

    def _compartir(self, m, q, b):
        token = self.compartidas.setdefault(m.group(1), _id())
        return 200, {"share_token": token}

    # ------------------------------------------------------------------- datasets

    def _crear_dataset(self, m, q, b):
        d = {"id": _id(), "name": b.get("name", "sin-nombre"), "created_at": _ahora(),
             "modified_at": _ahora(), "description": b.get("description"),
             "data_type": b.get("data_type", "kv"), "example_count": 0,
             "session_count": 0, "tenant_id": TENANT}
        self.datasets[d["id"]] = d
        return 200, d

    def _leer_dataset(self, m, q, b):
        d = self.datasets.get(m.group(1))
        return (200, d) if d else self._crear_dataset(None, {}, {"name": "dataset"})

    def _experimento_comparativo(self, m, q, b):
        return 200, {"id": _id(), "name": b.get("name", "comparativa"),
                     "tenant_id": TENANT,
                     "created_at": _ahora(), "modified_at": _ahora(),
                     "reference_dataset_id": b.get("reference_dataset_id")
                     or next(iter(self.datasets), _id()),
                     "description": b.get("description"),
                     "experiments_info": [{"id": str(x), "name": f"experimento-{str(x)[:8]}"}
                                          for x in (b.get("experiment_ids") or [])],
                     "feedback_stats": {}, "extra": {}}

    def _listar_datasets(self, m, q, b):
        nombre = q.get("name")
        if nombre:
            d = self._dataset_por_nombre(nombre)
            if d is None:
                _, d = self._crear_dataset(None, {}, {"name": nombre})
            return 200, [d]
        return 200, list(self.datasets.values())

    def _crear_ejemplos(self, m, q, b):
        if isinstance(b, dict) and "examples" in b:
            entradas = b["examples"]
        elif isinstance(b, list):
            entradas = b
        elif isinstance(b, dict):
            entradas = [b]
        else:                       # el SDK manda multipart en algunas rutas
            entradas = []
        creados = []
        id_dataset = str(next(iter(self.datasets), _id()))
        for e in entradas:
            if not isinstance(e, dict):
                continue
            id_dataset = str(e.get("dataset_id") or id_dataset)
            ej = {"id": _id(), "dataset_id": id_dataset, "created_at": _ahora(),
                  "modified_at": _ahora(), "inputs": e.get("inputs", {}),
                  "outputs": e.get("outputs"), "metadata": e.get("metadata"),
                  "split": None}
            self.ejemplos[ej["id"]] = ej
            creados.append(ej)
        if id_dataset in self.datasets:
            self.datasets[id_dataset]["example_count"] = len(
                [e for e in self.ejemplos.values() if e["dataset_id"] == id_dataset])
        # Las dos rutas devuelven formas distintas, y el SDK cuenta con ello:
        # `/examples/bulk` devuelve LA LISTA de ejemplos creados (el cliente hace
        # `[d["id"] for d in respuesta]`), y `/examples` devuelve EL ejemplo.
        if m and m.group(0).endswith("/bulk"):
            return 200, creados
        return 200, creados[0] if creados else {}

    def _semilla_de_ejemplos(self, id_dataset: str, cuantos: int = 6) -> None:
        if any(e["dataset_id"] == id_dataset for e in self.ejemplos.values()):
            return
        categorias = ["facturacion", "integraciones", "acceso_cuenta", "bug_producto",
                      "rendimiento", "otros"]
        for i in range(cuantos):
            ej = {"id": _id(), "dataset_id": id_dataset, "created_at": _ahora(),
                  "modified_at": _ahora(),
                  "inputs": {"asunto": f"Ticket de ejemplo {i}", "mensaje": "Texto."},
                  "outputs": {"categoria": categorias[i % len(categorias)]},
                  "metadata": {"plan": "free"}, "split": None}
            self.ejemplos[ej["id"]] = ej

    def _listar_ejemplos(self, m, q, b):
        id_dataset = q.get("dataset")
        if not id_dataset and q.get("dataset_name"):
            d = self._dataset_por_nombre(q["dataset_name"])
            id_dataset = d and d["id"]
        if id_dataset:
            self._semilla_de_ejemplos(str(id_dataset))
        salida = [e for e in self.ejemplos.values()
                  if not id_dataset or e["dataset_id"] == str(id_dataset)]
        splits = q.get("splits")
        if splits:
            pedidos = splits if isinstance(splits, list) else [splits]
            salida = [e for e in salida if e.get("split") in pedidos]
        return 200, salida

    def _leer_ejemplo(self, m, q, b):
        return 200, self.ejemplos.get(m.group(1), {"id": m.group(1), "inputs": {},
                                                   "dataset_id": _id()})

    def _actualizar_ejemplo(self, m, q, b):
        self.ejemplos.setdefault(m.group(1), {"id": m.group(1)}).update(b)
        return 200, {"count": 1}

    def _actualizar_ejemplos(self, m, q, b):
        return 200, {"count": len(b if isinstance(b, list) else [b])}

    def _versiones(self, m, q, b):
        return 200, [{"as_of": _ahora(), "tags": ["latest", "v1"]}]

    def _etiquetar(self, m, q, b):
        return 200, {}

    def _listar_splits(self, m, q, b):
        return 200, sorted({e["split"] for e in self.ejemplos.values() if e.get("split")})

    def _actualizar_splits(self, m, q, b):
        for id_ejemplo in b.get("examples", []):
            if str(id_ejemplo) in self.ejemplos:
                self.ejemplos[str(id_ejemplo)]["split"] = (
                    None if b.get("remove") else b.get("split_name"))
        return 200, {}

    def _diferencia(self, m, q, b):
        return 200, {"examples_modified": [], "examples_added": [_id()],
                     "examples_removed": []}

    def _finetuning(self, m, q, b):
        return 200, {"messages": [{"role": "user", "content": "Ticket"},
                                  {"role": "assistant", "content": "facturacion"}]}

    def _subir_csv(self, m, q, b):
        _, d = self._crear_dataset(None, {}, {"name": "subido-desde-csv"})
        return 200, d

    # ------------------------------------------------------------- realimentación

    def _crear_realimentacion(self, m, q, b):
        b.setdefault("id", _id())
        b.setdefault("created_at", _ahora())
        b.setdefault("modified_at", _ahora())
        b.setdefault("trace_id", b.get("run_id"))
        self.realimentacion[str(b["id"])] = b
        return 200, b

    def _listar_realimentacion(self, m, q, b):
        if self.realimentacion:
            return 200, list(self.realimentacion.values())
        ejemplo = _id()
        return 200, [{"id": _id(), "created_at": _ahora(), "modified_at": _ahora(),
                      "run_id": ejemplo, "trace_id": ejemplo, "key": "acierto",
                      "score": 1.0, "comment": None}]

    def _token_de_realimentacion(self, m, q, b):
        # La URL termina en el UUID del token: el SDK la parsea para volver a llamar.
        token = _id()
        return 200, {"id": token, "expires_at": _ahora(),
                     "url": f"https://api.smith.langchain.com/{token}"}

    def _usar_token(self, m, q, b):
        return 200, {}

    def _crear_configuracion(self, m, q, b):
        c = {"feedback_key": b.get("feedback_key", "k"),
             "feedback_config": b.get("feedback_config", {"type": "continuous"}),
             "tenant_id": TENANT, "modified_at": _ahora(),
             "is_lower_score_better": b.get("is_lower_score_better", False)}
        self.configuraciones[c["feedback_key"]] = c
        return 200, c

    def _listar_configuraciones(self, m, q, b):
        return 200, list(self.configuraciones.values())

    # --------------------------------------------------------------------- colas

    def _crear_cola(self, m, q, b):
        c = {"id": _id(), "name": b.get("name", "cola"), "tenant_id": TENANT,
             "description": b.get("description"), "created_at": _ahora(),
             "updated_at": _ahora(), "num_reviewers_per_item": 1}
        self.colas[c["id"]] = c
        return 200, c

    def _listar_colas(self, m, q, b):
        return 200, list(self.colas.values())

    def _encolar(self, m, q, b):
        return 200, {}

    # -------------------------------------------------------------------- prompts

    def _plantilla_de_repo(self, handle: str) -> dict:
        return {"repo_handle": handle, "id": _id(), "tenant_id": TENANT,
                "created_at": _ahora(), "updated_at": _ahora(), "is_public": False,
                "is_archived": False, "tags": [], "owner": "-",
                "full_name": f"-/{handle}", "num_likes": 0, "num_downloads": 0,
                "num_views": 0, "num_commits": len(self.commits.get(handle, [])),
                "description": None, "readme": None, "last_commit_hash": (
                    self.commits.get(handle, [{}])[-1].get("commit_hash")
                    if self.commits.get(handle) else None)}

    def _leer_repo(self, m, q, b):
        handle = m.group(1).split("/")[-1]
        if handle not in self.repos:
            return 404, {"detail": "not found"}
        return 200, {"repo": self._plantilla_de_repo(handle)}

    def _crear_repo(self, m, q, b):
        handle = b.get("repo_handle", "prompt")
        self.repos[handle] = True
        return 200, {"repo": self._plantilla_de_repo(handle)}

    def _manifiesto(self) -> dict:
        return {"id": ["langchain", "prompts", "chat", "ChatPromptTemplate"],
                "lc": 1, "type": "constructor",
                "kwargs": {"input_variables": ["asunto", "mensaje"],
                           "messages": [{"id": ["langchain", "prompts", "chat",
                                                "HumanMessagePromptTemplate"],
                                         "lc": 1, "type": "constructor",
                                         "kwargs": {"prompt": {
                                             "id": ["langchain", "prompts", "prompt",
                                                    "PromptTemplate"],
                                             "lc": 1, "type": "constructor",
                                             "kwargs": {"template": "Asunto: {asunto}\nMensaje: {mensaje}",
                                                        "input_variables": ["asunto", "mensaje"],
                                                        "template_format": "f-string"}}}}]}}

    def _crear_commit(self, m, q, b):
        handle = m.group(2)
        self.repos[handle] = True
        commit = {"id": _id(), "commit_hash": uuid.uuid4().hex[:40],
                  "manifest": b.get("manifest", {}), "owner": "-", "repo": handle,
                  "examples": [], "created_at": _ahora(),
                  "tags": list(b.get("tags") or [])}
        self.commits.setdefault(handle, []).append(commit)
        return 200, {"commit": commit, "commit_hash": commit["commit_hash"]}

    def _listar_commits(self, m, q, b):
        handle = m.group(2)
        if handle not in self.commits:
            self._crear_commit(re.match(r"(-)/(.+)", f"-/{handle}"), {}, {})
        return 200, {"commits": [{**c, "manifest": None} for c in self.commits[handle]],
                     "total": len(self.commits[handle])}

    def _leer_commit(self, m, q, b):
        handle = m.group(2)
        commits = self.commits.get(handle)
        if not commits:
            self._crear_commit(None, {}, {"manifest": self._manifiesto()})
            commits = self.commits[handle]
        commit = dict(commits[-1])
        commit["manifest"] = commit.get("manifest") or self._manifiesto()
        return 200, commit


# ------------------------------------------------------------------- la sesión HTTP


class _Respuesta:
    def __init__(self, codigo: int, objeto: Any) -> None:
        self.status_code = codigo
        self._objeto = objeto
        self.headers = {"Content-Type": "application/json"}
        self.text = json.dumps(objeto, default=str)
        self.content = self.text.encode()
        self.url = ""
        self.reason = "OK" if codigo < 400 else "Error"
        self.ok = codigo < 400

    def json(self):
        return self._objeto

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"{self.status_code}", response=self)

    def iter_lines(self, *a, **k):
        yield self.content

    def iter_content(self, *a, **k):
        yield self.content

    def close(self):
        pass


class SesionDeMentira:
    """Una sesión de `requests` que habla con `LangSmithDeMentira` en vez de con la red."""

    def __init__(self, servicio: LangSmithDeMentira) -> None:
        self.servicio = servicio
        self.trust_env = False
        self.verify = True
        self.cert = None
        self.proxies: dict = {}
        self.params: dict = {}
        self.stream = False
        self.max_redirects = 30
        self.adapters: dict = {}
        self.hooks: dict = {"response": []}
        self.headers: dict = {}
        from requests.cookies import RequestsCookieJar

        self.cookies = RequestsCookieJar()
        self.auth = None

    # -- la API que usa el SDK --------------------------------------------------

    def request(self, method, url, *args, **kwargs):
        cuerpo = kwargs.get("json")
        if cuerpo is None:
            crudo = kwargs.get("data")
            if isinstance(crudo, (bytes, str)):
                try:
                    cuerpo = json.loads(crudo)
                except Exception:
                    cuerpo = None
        return self._responder(method, url, kwargs.get("params") or {}, cuerpo)

    def send(self, peticion, **kwargs):
        cuerpo = None
        if getattr(peticion, "body", None):
            try:
                cuerpo = json.loads(peticion.body)
            except Exception:
                cuerpo = None
        return self._responder(peticion.method, peticion.url, {}, cuerpo)

    def get(self, url, **k):
        return self.request("GET", url, **k)

    def post(self, url, **k):
        return self.request("POST", url, **k)

    def patch(self, url, **k):
        return self.request("PATCH", url, **k)

    def put(self, url, **k):
        return self.request("PUT", url, **k)

    def delete(self, url, **k):
        return self.request("DELETE", url, **k)

    def mount(self, *a, **k):
        pass

    def close(self):
        pass

    # -- el puente --------------------------------------------------------------

    def _responder(self, metodo, url, consulta, cuerpo):
        from urllib.parse import parse_qs, urlparse

        partes = urlparse(str(url))
        consulta = {**{k: (v[0] if len(v) == 1 else v)
                       for k, v in parse_qs(partes.query).items()}, **(consulta or {})}
        codigo, objeto = self.servicio.responder(metodo, partes.path, consulta, cuerpo)
        return _Respuesta(codigo, objeto)


# ------------------------------------------------------ el cliente moderno (httpx)
#
# Los accesores nuevos —`client.evaluators`, `client.threads`, `client.runs.share`…—
# no usan `requests`: van por un cliente generado que habla `httpx`. Así que hay que
# interceptar también ahí, y por eso esto no es una sesión más.


def _httpx():
    """El `httpx` que usa el SDK, que **no es el que instalas tú**.

    El cliente generado vendoriza `httpx2`. Construir el transporte con el `httpx` de
    siempre da un `TypeError` maravilloso: «Expected an instance of httpx.AsyncClient
    but got httpx.AsyncClient».
    """
    from langsmith._openapi_client import _base_client

    return _base_client.httpx


def _manejador_httpx(servicio: LangSmithDeMentira):
    httpx = _httpx()

    def manejar(peticion):
        cuerpo = None
        if peticion.content:
            try:
                cuerpo = json.loads(peticion.content)
            except Exception:
                cuerpo = None
        ruta = peticion.url.path
        # El cliente generado habla con /api/v1 y /api/v2; el ruteo de arriba no.
        ruta = re.sub(r"^/api/v[12]", "", ruta)
        consulta = dict(peticion.url.params)
        codigo, objeto = servicio.responder(peticion.method, ruta, consulta, cuerpo)
        return httpx.Response(codigo, json=objeto if objeto != {} else _vacio(ruta))

    return manejar


def _vacio(ruta: str) -> Any:
    """Una respuesta con la forma que espera un listado paginado, si no hay nada."""
    return {"data": [], "has_more": False}


def atar_cliente_moderno(client, servicio: LangSmithDeMentira) -> None:
    """Hace que los accesores `client.evaluators` y compañía hablen con el simulador.

    Toca atributos privados a propósito: es un banco de pruebas, no código de
    producción, y el SDK no expone otra forma de inyectar un transporte.
    """
    from langsmith._openapi_client import AsyncLangsmith

    httpx = _httpx()
    transporte = httpx.MockTransport(_manejador_httpx(servicio))
    client._langsmith_api = AsyncLangsmith(
        api_key="simulado",
        base_url="https://api.smith.langchain.com",
        http_client=httpx.AsyncClient(transport=transporte),
    )
    try:
        from langsmith._openapi_client import Langsmith

        client._langsmith_api_sync = Langsmith(
            api_key="simulado",
            base_url="https://api.smith.langchain.com",
            http_client=httpx.Client(
                transport=httpx.MockTransport(_manejador_httpx(servicio))),
        )
    except Exception:                     # el cliente síncrono puede no estar
        pass
