"""Celdas compartidas por los builders de A4 (módulos 09, 10 y 11).

Cada notebook del curso es autocontenido: estas cadenas se copian TAL CUAL dentro de los notebooks
(celdas de código). Aquí viven una sola vez para que los seis notebooks no diverjan.
Contrato común: carga_corpus(fast_dev) -> {"docs","queries","qrels","source"} y métricas ndcg/recall/mrr@k.
"""

# ── Métricas de retrieval (copia de la implementación canónica del módulo 00) ──────────────────────────────
METRICS_CELL = '''
# ── Métricas de retrieval (misma implementación que el módulo 00) ──
import math
import numpy as np


def _dedup(ranked_ids):
    seen, out = set(), []
    for d in ranked_ids:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def ndcg_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """nDCG@k con ganancia lineal (trec_eval). rels: doc_id -> relevancia (>0 relevante)."""
    ranked = _dedup(ranked_ids)[:k]
    dcg = sum(rels.get(d, 0) / math.log2(i + 2) for i, d in enumerate(ranked) if rels.get(d, 0) > 0)
    ideal = sorted((r for r in rels.values() if r > 0), reverse=True)[:k]
    idcg = sum(r / math.log2(i + 2) for i, r in enumerate(ideal))
    return 0.0 if idcg == 0 else dcg / idcg


def recall_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    relevant = {d for d, r in rels.items() if r > 0}
    return len(relevant & set(_dedup(ranked_ids)[:k])) / len(relevant) if relevant else 0.0


def mrr_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    for i, d in enumerate(_dedup(ranked_ids)[:k]):
        if rels.get(d, 0) > 0:
            return 1.0 / (i + 1)
    return 0.0


def rank_from_scores(scores, doc_ids, k=None):
    """Orden por score desc.; empates -> orden del corpus (determinista)."""
    scores = np.asarray(scores, dtype=float)
    order = np.lexsort((np.arange(len(scores)), -scores))
    return [doc_ids[i] for i in (order[:k] if k else order)]


def evaluate(run: dict, qrels: dict, k: int = 10) -> dict:
    """run: {qid: [doc_id ordenados]}; promedia solo sobre queries con algún relevante."""
    tot, n = {"ndcg": 0.0, "recall": 0.0, "mrr": 0.0}, 0
    for qid, rels in qrels.items():
        if not any(r > 0 for r in rels.values()):
            continue
        ranked = run.get(qid, [])
        tot["ndcg"] += ndcg_at_k(ranked, rels, k)
        tot["recall"] += recall_at_k(ranked, rels, k)
        tot["mrr"] += mrr_at_k(ranked, rels, k)
        n += 1
    out = {m: (v / n if n else 0.0) for m, v in tot.items()}
    out["n_queries"] = n
    return out
'''

# ── Corpus sintético (fallback) ───────────────────────────────────────────────────────────────────────────
LEXICON_CELL = '''
# ── Léxico del corpus SINTÉTICO (fallback): un "concepto" = (acción, objeto), con dos sinónimos por idioma ──
import random
import re
from collections import Counter

ACCIONES = {  # id: (sinónimos ES, sinónimos EN, verbo en código)
    "sort": (["ordenar", "clasificar"], ["sort", "order"], "sort"),
    "filter": (["filtrar", "depurar"], ["filter", "screen"], "filter"),
    "merge": (["combinar", "fusionar"], ["merge", "combine"], "merge"),
    "split": (["dividir", "separar"], ["split", "divide"], "split"),
    "delete": (["eliminar", "borrar"], ["delete", "remove"], "delete"),
    "copy": (["copiar", "duplicar"], ["copy", "duplicate"], "copy"),
    "encrypt": (["cifrar", "encriptar"], ["encrypt", "scramble"], "encrypt"),
    "compress": (["comprimir", "empaquetar"], ["compress", "pack"], "compress"),
    "validate": (["validar", "verificar"], ["validate", "verify"], "validate"),
    "parse": (["analizar", "interpretar"], ["parse", "interpret"], "parse"),
    "download": (["descargar", "bajar"], ["download", "fetch"], "download"),
    "upload": (["subir", "cargar"], ["upload", "push"], "upload"),
}
OBJETOS = {
    "list": (["lista", "arreglo"], ["list", "array"], "list"),
    "file": (["archivo", "fichero"], ["file", "document"], "file"),
    "string": (["cadena", "texto"], ["string", "text"], "string"),
    "table": (["tabla", "planilla"], ["table", "spreadsheet"], "table"),
    "image": (["imagen", "foto"], ["image", "picture"], "image"),
    "message": (["mensaje", "aviso"], ["message", "notification"], "message"),
    "user": (["usuario", "cuenta"], ["user", "account"], "user"),
    "log": (["registro", "bitácora"], ["log", "journal"], "log"),
    "password": (["contraseña", "clave"], ["password", "passphrase"], "password"),
    "link": (["enlace", "vínculo"], ["link", "address"], "link"),
    "matrix": (["matriz", "cuadrícula"], ["matrix", "grid"], "matrix"),
    "date": (["fecha", "calendario"], ["date", "calendar"], "date"),
}
RELLENO = {
    "es": ["Funciona en Linux y en macOS.", "Requiere Python 3.10 o superior.", "Revisa la configuración del servidor antes de continuar.",
           "El resultado se guarda en el directorio de trabajo.", "Consulta los registros si aparece un error.",
           "Esta operación es idempotente y segura en producción.", "Puedes automatizarlo con un script de shell.",
           "Se recomienda hacer una copia de seguridad previa.", "El tiempo de ejecución crece con el tamaño de los datos."],
    "en": ["It works on Linux and macOS.", "Requires Python 3.10 or later.", "Check the server configuration before continuing.",
           "The result is stored in the working directory.", "Look at the logs if an error shows up.",
           "This operation is idempotent and safe in production.", "You can automate it with a shell script.",
           "Making a backup first is recommended.", "Running time grows with the size of the data."],
}
PLANTILLAS = {
    "es": ["Cómo {a} {o} paso a paso.", "Guía rápida para {a} {o} correctamente.", "Tutorial: {a} {o} en tu proyecto."],
    "en": ["How to {a} a {o} step by step.", "Quick guide to {a} the {o} correctly.", "Tutorial: {a} the {o} in your project."],
}
'''

SYNTH_CELL = '''
def _frase(rng, lang, a, o, estilo):
    idx = 0 if lang == "es" else 1
    return PLANTILLAS[lang][estilo % 3].format(a=rng.choice(ACCIONES[a][idx]), o=rng.choice(OBJETOS[o][idx]))


def _doc_codigo(rng, a, o):
    fa, fo = ACCIONES[a][2], OBJETOS[o][2]
    va, vo = rng.choice(ACCIONES[a][1]), rng.choice(OBJETOS[o][1])
    return (f"def {fa}_{fo}({fo}, strict=False):\\n    \\"\\"\\"{va.capitalize()} the {vo} and return the result.\\"\\"\\"\\n"
            f"    result = helper_{fa}({fo})\\n    return result")


def genera_sintetico(fast_dev: bool = True, seed: int = 42) -> dict:
    """Corpus sintético con el MISMO esquema que el real. Concepto = (acción, objeto); relevantes = TODOS los docs
    del concepto (ES, EN y código). Las queries usan sinónimos distintos: hay brecha léxica y cruce de idioma.
    Extras no contractuales: docs[i]['concept'], queries[i]['concept'] y queries[i]['split'] ('train'|'test', por concepto)."""
    rng = random.Random(seed)
    acts, objs = sorted(ACCIONES), sorted(OBJETOS)
    conceptos = [(a, o) for a in acts for o in objs]
    rng.shuffle(conceptos)
    conceptos = conceptos[:60] if fast_dev else conceptos
    docs, queries, qrels = [], [], {}
    for ci, (a, o) in enumerate(conceptos):
        cid, rel = f"c{ci:03d}", {}
        for lang, n in (("es", 3), ("en", 3), ("code", 2)):
            for k in range(n):
                did = f"{cid}-{lang}{k}"
                if lang == "code":
                    text = _doc_codigo(rng, a, o)
                else:
                    a2, o2 = rng.choice(acts), rng.choice(objs)
                    otra = _frase(rng, lang, a2, o2, k + 1) if (a2, o2) != (a, o) else ""
                    extra = (("No confundir con: " if lang == "es" else "Do not confuse with: ") + otra) if otra else ""
                    text = " ".join([_frase(rng, lang, a, o, k), rng.choice(RELLENO[lang]), rng.choice(RELLENO[lang]), extra]).strip()
                docs.append({"id": did, "lang": lang, "text": text, "concept": cid})
                rel[did] = 1
        for k, lang in enumerate(("es", "es", "en", "en")):
            qid = f"q{ci:03d}-{k}"
            idx = 0 if lang == "es" else 1
            text = f"{rng.choice(ACCIONES[a][idx])} {rng.choice(OBJETOS[o][idx])}"
            queries.append({"qid": qid, "lang": lang, "text": text, "concept": cid, "split": "test" if ci % 5 == 0 else "train"})
            qrels[qid] = dict(rel)
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": "synthetic"}
'''

# ── Cargador REAL (se ejecuta en el proceso o en un subproceso con HF_ENDPOINT=espejo) ────────────────────────
REAL_LOADER_CELL = r'''
# ── Cargador REAL de Políglota (Wikipedia ES/EN + CodeSearchNet Python) ──
# Cadena: (1) hub oficial -> (2) espejo (HF_ENDPOINT, en subproceso) -> (3) sintético (en carga_corpus).
import json
import os
import subprocess
import sys
import textwrap

LOADER_SRC = r"""
import ast, json, re, sys, zlib
from datasets import load_dataset

def split_de(qid):  # determinista: ~20 % test
    return "test" if zlib.crc32(qid.encode()) % 5 == 0 else "train"

def sin_docstring(code):
    try:
        tree = ast.parse(code)
        fn = tree.body[0]
        if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(getattr(fn.body[0], "value", None), ast.Constant):
            fn.body = fn.body[1:] or [ast.Pass()]
        return ast.unparse(tree)
    except Exception:
        return None

def wiki(lang, n):
    ds = load_dataset("wikimedia/wikipedia", "20231101." + lang, split="train", streaming=True)
    docs, queries, qrels = [], [], {}
    for ex in ds:
        sents = re.split(r"(?<=[.!?])\s+", ex["text"].strip())
        body = " ".join(" ".join(sents[1:]).split()[:120])  # sin la 1.ª frase (repite el título)
        if len(body.split()) < 50 or len(ex["title"]) < 3:
            continue
        i = len(docs)
        docs.append({"id": lang + format(i, "05d"), "lang": lang, "text": body})
        qid = "q-" + docs[-1]["id"]
        queries.append({"qid": qid, "lang": lang, "text": ex["title"], "split": split_de(qid)})
        qrels[qid] = {docs[-1]["id"]: 1}
        if len(docs) >= n:
            break
    return docs, queries, qrels

def codigo(n):
    ds = None
    for name in ("code-search-net/code_search_net", "claudios/code_search_net", "Nan-Do/code-search-net-python"):
        try:
            ds = load_dataset(name, split="train", streaming=True)
            break
        except Exception:
            ds = None
    if ds is None:
        raise RuntimeError("sin CodeSearchNet")
    docs, queries, qrels = [], [], {}
    for ex in ds:
        doc = ex.get("func_documentation_string") or ex.get("docstring") or ""
        code = ex.get("func_code_string") or ex.get("code") or ex.get("original_string") or ""
        first = doc.strip().split("\n")[0].strip()
        body = sin_docstring(code) if 60 < len(code) < 1500 else None
        if len(first.split()) < 4 or not body:
            continue
        i = len(docs)
        docs.append({"id": "code" + format(i, "05d"), "lang": "code", "text": body})
        qid = "q-" + docs[-1]["id"]
        queries.append({"qid": qid, "lang": "en", "text": first, "split": split_de(qid)})
        qrels[qid] = {docs[-1]["id"]: 1}
        if len(docs) >= n:
            break
    return docs, queries, qrels

if __name__ == "__main__":
    n_wiki, n_code, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    D, Q, R = [], [], {}
    for d, q, r in (wiki("es", n_wiki), wiki("en", n_wiki), codigo(n_code)):
        D += d; Q += q; R.update(r)
    json.dump({"docs": D, "queries": Q, "qrels": R, "source": "real"}, open(out, "w"))
"""


def _intenta_real(n_wiki: int, n_code: int, endpoint=None, timeout: int = 900):
    """Ejecuta el cargador en un subproceso (así HF_ENDPOINT se aplica limpio). Devuelve dict o None."""
    open("_poliglota_loader.py", "w").write(textwrap.dedent(LOADER_SRC))
    env = dict(os.environ, **({"HF_ENDPOINT": endpoint} if endpoint else {}))
    try:
        subprocess.run([sys.executable, "_poliglota_loader.py", str(n_wiki), str(n_code), "_poliglota_real.json"],
                       env=env, check=True, timeout=timeout, capture_output=True)
        return json.load(open("_poliglota_real.json"))
    except Exception as e:  # sin red, proxy, dataset renombrado, etc.
        print(f"   · carga real no disponible ({type(e).__name__}) desde {endpoint or 'hub oficial'}")
        return None
'''

CORPUS_CELL = '''
def carga_corpus(fast_dev: bool = True) -> dict:
    """Contrato común del curso. Devuelve {"docs": [{"id","lang","text"}], "queries": [{"qid","lang","text"}],
    "qrels": {qid: {doc_id: 1}}, "source": "real"|"synthetic"}.
    Cadena: hub oficial -> espejo hf-mirror.com -> sintético (mismo esquema, con aviso).
    Diferencias con la versión canónica del módulo 00: aquí las queries reales son 'título -> cuerpo del artículo sin su
    1.ª frase' (Wikipedia) y 'docstring -> función sin docstring' (CodeSearchNet); y se añaden las claves extra 'split'
    (train/test) y, en el sintético, 'concept'."""
    n_wiki, n_code = (150, 100) if fast_dev else (1500, 1000)
    for endpoint in (None, "https://hf-mirror.com"):
        corpus = _intenta_real(n_wiki, n_code, endpoint)
        if corpus:
            return corpus
    print("⚠️  Sin acceso a los datasets reales: uso el corpus SINTÉTICO (mismo esquema). Las cifras NO son comparables con las reales.")
    return genera_sintetico(fast_dev)
'''

# Evaluación de un embedder sobre el corpus: matriz de similitud -> run -> métricas
EVAL_CELL = '''
def evalua_scores(S, qs, doc_ids, qrels, k=10):
    """S: (n_queries, n_docs) similitudes -> {'ndcg','recall','mrr'}@k promediadas sobre qs."""
    run = {q["qid"]: rank_from_scores(S[i], doc_ids, 100) for i, q in enumerate(qs)}
    return evaluate(run, {q["qid"]: qrels[q["qid"]] for q in qs}, k)
'''

TEXT_BY_ID_NOTE = "Las claves extra (`concept`, `split`) no forman parte del contrato; los notebooks las usan solo para partir train/test."
