"""Piezas comunes de los builders del autor A3 (módulos 06, 07, 08).

Cada notebook sigue siendo autocontenido: aquí solo viven las cadenas de texto/código
que los builders copian dentro de las celdas, y pequeños helpers de markdown.
"""
from __future__ import annotations

import textwrap


def observe(text: str) -> str:
    """Caja «👀 Qué debes observar» (blockquote)."""
    body = textwrap.dedent(text).strip()
    lines = "\n".join(f"> {ln}" if ln.strip() else ">" for ln in body.splitlines())
    return f"> **👀 Qué debes observar**\n>\n{lines}"


def box(emoji_title: str, text: str) -> str:
    body = textwrap.dedent(text).strip()
    lines = "\n".join(f"> {ln}" if ln.strip() else ">" for ln in body.splitlines())
    return f"> **{emoji_title}**\n>\n{lines}"


def details(summary: str, body: str) -> str:
    return f"<details>\n<summary>{summary}</summary>\n\n{textwrap.dedent(body).strip()}\n\n</details>"


def hint(n: int, text: str) -> str:
    return details(f"🪜 Pista {n}", text)


SETUP_COMMON = '''
import os, sys, time, math, random, warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore")
import numpy as np
import torch

SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
FAST_DEV_RUN = True      # True: CPU, minutos. False: GPU (T4/L4), escala completa
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cpu":
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", min(4, os.cpu_count() or 1))))
print("device:", device, "| FAST_DEV_RUN:", FAST_DEV_RUN, "| torch", torch.__version__)
'''

CORPUS_SYNTH = '''
# --- Corpus Políglota (parte 1/2): generador SINTÉTICO de respaldo (mismo esquema que el real) ---
import inspect, textwrap as _tw

_TOOLS = ["Docker", "Redis", "PostgreSQL", "Nginx", "Kafka", "Kubernetes", "pytest", "Poetry", "FastAPI",
          "Prometheus", "Terraform", "Celery"]
_ASP = {"es": ["instalación", "autenticación", "registros", "rendimiento", "copias de seguridad",
               "migración", "errores comunes", "monitoreo"],
        "en": ["installation", "authentication", "logging", "performance", "backups",
               "migration", "common errors", "monitoring"]}
_S = {"es": ["el servidor", "la base de datos", "el cliente", "la API", "el worker", "la caché", "el planificador"],
      "en": ["the server", "the database", "the client", "the API", "the worker", "the cache", "the scheduler"]}
_V = {"es": ["procesa", "valida", "almacena", "registra", "reinicia", "consulta", "serializa", "expone"],
      "en": ["processes", "validates", "stores", "logs", "restarts", "queries", "serializes", "exposes"]}
_O = {"es": ["las peticiones entrantes", "los archivos de configuración", "los tokens de acceso",
             "los mensajes de error", "las variables de entorno", "los índices vectoriales"],
      "en": ["incoming requests", "configuration files", "access tokens", "error messages",
             "environment variables", "vector indexes"]}
_C = {"es": ["cuando el tiempo de espera supera el límite", "si falta la variable de entorno",
             "después de actualizar la dependencia", "antes de iniciar el servicio", "tras cada despliegue"],
      "en": ["when the timeout exceeds the limit", "if the environment variable is missing",
             "after upgrading the dependency", "before starting the service", "after every deployment"]}


def _doc_sintetico(rng, lang, tool, asp):
    head = f"# {tool}: {asp}\\n"
    sents = []
    for _ in range(rng.randint(4, 7)):
        s = f"{rng.choice(_S[lang]).capitalize()} {rng.choice(_V[lang])} {rng.choice(_O[lang])} {rng.choice(_C[lang])}."
        if rng.random() < 0.4:
            s += (f" Para {asp} de {tool}, ejecuta `{tool.lower()} --check` y revisa el registro." if lang == "es"
                  else f" For {asp} in {tool}, run `{tool.lower()} --check` and review the log.")
        sents.append(s)
    return head + " ".join(sents)


def _codigo_real(n):
    """Funciones reales de la biblioteca estándar de Python (siempre disponibles, sin red)."""
    out, seen = [], set()
    for modname in ["textwrap", "json.decoder", "argparse", "shutil", "string", "heapq", "bisect",
                    "fractions", "statistics", "csv", "pathlib", "difflib", "colorsys", "base64"]:
        try:
            mod = __import__(modname, fromlist=["x"])
        except Exception:
            continue
        for name, fn in inspect.getmembers(mod, inspect.isfunction):
            if fn.__module__ != mod.__name__ or fn in seen:
                continue
            seen.add(fn)
            try:
                src = inspect.getsource(fn)
            except Exception:
                continue
            doc = (inspect.getdoc(fn) or "").strip().split("\\n")[0]
            if 80 < len(src) < 2500 and doc:
                out.append((src, doc))
    random.Random(SEED).shuffle(out)
    return out[:n]
'''

CORPUS_LOAD = '''
# --- Corpus Políglota (parte 2/2): carga_corpus() con la cadena oficial -> espejo -> sintético ---
def _try_real(fast_dev):
    """Wikipedia ES/EN (HF wikimedia/wikipedia, streaming) + CodeSearchNet Python. Devuelve None si falla."""
    from datasets import load_dataset
    n_wiki, n_code = (150, 100) if fast_dev else (3000, 2000)
    docs, queries, qrels = [], [], {}
    for lang in ["es", "en"]:
        ds = None
        for repo, cfg in [("wikimedia/wikipedia", f"20231101.{lang}"), ("wikimedia/wikipedia", f"20231101.{lang}")]:
            try:   # (oficial; añade aquí un espejo propio si tu red bloquea el oficial)
                ds = load_dataset(repo, cfg, split="train", streaming=True); break
            except Exception:
                ds = None
        if ds is None:
            return None
        for i, ex in enumerate(ds):
            if i >= n_wiki:
                break
            did = f"{lang}-{i}"
            docs.append({"id": did, "lang": lang, "text": ex["text"][:3000]})
            queries.append({"qid": f"q-{did}", "lang": lang, "text": ex["title"]})
            qrels[f"q-{did}"] = {did: 1}
    for repo in ["code-search-net/code_search_net", "code_search_net"]:
        try:
            ds = load_dataset(repo, "python", split="train", streaming=True); break
        except Exception:
            ds = None
    if ds is None:
        return None
    for i, ex in enumerate(ds):
        if i >= n_code:
            break
        did = f"code-{i}"
        docs.append({"id": did, "lang": "code", "text": ex["func_code_string"][:3000]})
        q = (ex["func_documentation_string"] or "").strip().split("\\n")[0]
        if q:
            queries.append({"qid": f"q-{did}", "lang": "code", "text": q}); qrels[f"q-{did}"] = {did: 1}
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": "real"}


def _sintetico(fast_dev):
    rng = random.Random(SEED)
    per_cell = 1 if fast_dev else 5
    docs, queries, qrels = [], [], {}
    for lang in ["es", "en"]:
        for ti, tool in enumerate(_TOOLS):
            for ai, asp in enumerate(_ASP[lang]):
                qid = f"q-{lang}-{ti}-{ai}"
                qrels[qid] = {}
                for k in range(per_cell):
                    did = f"{lang}-{ti}-{ai}-{k}"
                    docs.append({"id": did, "lang": lang, "text": _doc_sintetico(rng, lang, tool, asp)})
                    qrels[qid][did] = 1
                queries.append({"qid": qid, "lang": lang,
                                "text": f"{asp} de {tool}" if lang == "es" else f"{tool} {asp}"})
    for i, (src, doc) in enumerate(_codigo_real(60 if fast_dev else 400)):
        did = f"code-{i}"
        docs.append({"id": did, "lang": "code", "text": src})
        queries.append({"qid": f"q-{did}", "lang": "code", "text": doc}); qrels[f"q-{did}"] = {did: 1}
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": "synthetic"}


def carga_corpus(fast_dev: bool = True) -> dict:
    """{"docs": [{"id","lang","text"}], "queries": [{"qid","lang","text"}], "qrels": {qid: {doc_id: 1}},
    "source": "real"|"synthetic"}. Cadena: oficial (HF) -> sintético (con aviso). Semilla 42."""
    try:
        corpus = _try_real(fast_dev)
        if corpus:
            return corpus
    except Exception as e:
        print("[aviso] datos reales no disponibles:", type(e).__name__, str(e)[:80])
    print("[aviso] usando corpus SINTÉTICO (mismo esquema). Resultados cualitativos, no comparables con real.")
    return _sintetico(fast_dev)
'''
