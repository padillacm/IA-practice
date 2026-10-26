# ── carga_corpus(): cadena oficial (HF) -> espejo (API de Wikipedia / stdlib) -> sintético ─────
import ast
import json
import os
import random
import urllib.parse
import urllib.request

SEED = 42


def _strip_docstring(func_src: str):
    """Devuelve (código sin docstring, primera frase del docstring) o None si no hay docstring útil."""
    try:
        fn = ast.parse(func_src).body[0]
        doc = ast.get_docstring(fn)
        first = fn.body[0]
    except Exception:
        return None
    if not doc or not (isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant)):
        return None
    lines = func_src.splitlines()
    code = "\n".join(lines[: first.lineno - 1] + lines[first.end_lineno :])
    frase = doc.strip().split("\n\n")[0].replace("\n", " ").strip()
    frase = frase.split(". ")[0].rstrip(".")
    return (code, frase) if len(frase.split()) >= 4 else None


def _code_stdlib(n_docs: int, n_queries: int, rng: random.Random):
    """Espejo OFFLINE con código real: funciones de la biblioteca estándar con su docstring como query."""
    import importlib, inspect, textwrap
    mods = ["argparse", "bisect", "calendar", "collections", "colorsys", "copy", "csv", "difflib", "fnmatch", "fractions",
            "functools", "getpass", "glob", "heapq", "html", "json", "operator", "os", "pathlib", "posixpath", "queue",
            "random", "re", "shlex", "shutil", "statistics", "string", "tempfile", "textwrap", "urllib.parse", "uuid", "zipfile"]
    cands = []
    for name in mods:
        try:
            src = inspect.getsource(importlib.import_module(name))
            tree = ast.parse(src)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno - node.lineno >= 4:
                seg = textwrap.dedent("\n".join(src.splitlines()[node.lineno - 1 : node.end_lineno]))
                r = _strip_docstring(seg)
                if r and 200 <= len(r[0]) <= 2500:
                    cands.append((f"{name}.{node.name}", r[0], r[1]))
    rng.shuffle(cands)
    return cands[:n_docs]


def _code_hf(n_docs: int, rng: random.Random):
    """Oficial: CodeSearchNet (Python) en streaming. Prueba varios repos por cambios de formato en `datasets`."""
    from datasets import load_dataset
    errs = []
    for repo, kw in [("code-search-net/code_search_net", {"name": "python"}), ("code_search_net", {"name": "python"}),
                     ("claudios/code_search_net", {"name": "python"}), ("Nan-Do/code-search-net-python", {})]:
        try:
            ds = load_dataset(repo, split="train", streaming=True, **kw).shuffle(seed=SEED, buffer_size=2000)
            out = []
            for ex in ds:
                src = ex.get("func_code_string") or ex.get("whole_func_string") or ex.get("code") or ""
                r = _strip_docstring(src) if '"""' in src or "'''" in src else None
                doc = (ex.get("func_documentation_string") or ex.get("docstring") or "").strip().split("\n\n")[0]
                doc = doc.replace("\n", " ").split(". ")[0].rstrip(".")
                code = r[0] if r else src
                if 200 <= len(code) <= 2500 and len(doc.split()) >= 4:
                    out.append((ex.get("func_name") or f"csn.{len(out)}", code, doc))
                if len(out) >= n_docs:
                    return out
        except Exception as e:  # noqa: BLE001
            errs.append(f"{repo}: {type(e).__name__}")
    raise RuntimeError("CodeSearchNet no disponible -> " + "; ".join(errs))


def _wiki_hf(lang: str, n_docs: int, cap: int):
    """Oficial: wikimedia/wikipedia (snapshot 20231101) en streaming con un buffer pequeño."""
    from datasets import load_dataset
    ds = load_dataset("wikimedia/wikipedia", f"20231101.{lang}", split="train", streaming=True)
    ds = ds.shuffle(seed=SEED, buffer_size=2000)
    out = []
    for ex in ds:
        if len(ex["text"]) >= 600 and len(ex["title"]) >= 3:
            out.append((f"{lang}-{ex['id']}", ex["title"], ex["text"][:cap]))
        if len(out) >= n_docs:
            break
    if len(out) < n_docs // 2:
        raise RuntimeError("pocos artículos")
    return out


def _wiki_api(lang: str, n_docs: int):
    """Espejo: API pública de Wikipedia (artículos aleatorios, solo la sección introductoria; ~20 por petición)."""
    out, seen, tries = [], set(), 0
    while len(out) < n_docs and tries < 80:
        tries += 1
        qs = urllib.parse.urlencode({"action": "query", "format": "json", "generator": "random", "grnnamespace": 0,
                                     "grnlimit": 20, "prop": "extracts", "exintro": 1, "explaintext": 1, "exlimit": 20})
        req = urllib.request.Request(f"https://{lang}.wikipedia.org/w/api.php?{qs}",
                                     headers={"User-Agent": "poliglota-course/1.0 (curso educativo)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            pages = json.load(r).get("query", {}).get("pages", {})
        for p in pages.values():
            if p["pageid"] not in seen and len(p.get("extract", "")) >= 300:
                seen.add(p["pageid"])
                out.append((f"{lang}-{p['pageid']}", p["title"], p["extract"]))
    if len(out) < n_docs // 2:
        raise RuntimeError("pocos artículos")
    return out[:n_docs]


def carga_corpus(fast_dev: bool = True) -> dict:
    """Corpus Políglota -> {"docs": [{id, lang, text}], "queries": [{qid, lang, text}], "qrels": {qid: {doc_id: 1}},
    "source": "real" | "synthetic"}. Cadena: oficial (HF) -> espejo (API Wikipedia; código de la stdlib) -> sintético."""
    rng = random.Random(SEED)
    n_wiki, n_code, q_wiki, q_code, cap = (150, 100, 40, 30, 1500) if fast_dev else (3000, 1500, 200, 150, 6000)
    docs, queries, qrels, source = [], [], {}, "real"
    wiki = {}
    for lang in ("es", "en"):
        for nombre, fn in (("HF wikimedia/wikipedia", lambda: _wiki_hf(lang, n_wiki, cap)),
                           ("API de Wikipedia (espejo)", lambda: _wiki_api(lang, min(n_wiki, 400)))):
            try:
                wiki[lang] = fn()
                print(f"[carga_corpus] Wikipedia {lang}: {len(wiki[lang])} artículos desde {nombre}")
                break
            except Exception as e:  # noqa: BLE001
                print(f"[carga_corpus] {nombre} ({lang}) falló: {type(e).__name__}: {str(e)[:80]}")
    if len(wiki) == 2:
        for lang, arts in wiki.items():
            docs += [{"id": i, "lang": lang, "text": t} for i, _, t in arts]
            for j, k in enumerate(rng.sample(range(len(arts)), min(q_wiki, len(arts)))):
                qid = f"{lang}-q{j:04d}"
                queries.append({"qid": qid, "lang": lang, "text": arts[k][1]})
                qrels[qid] = {arts[k][0]: 1}
    else:
        source = "synthetic"
        print("⚠️  [carga_corpus] SIN acceso a Wikipedia: uso texto ES/EN SINTÉTICO (mismo esquema). Los números NO son comparables con datos reales.")
        for lang in ("es", "en"):
            d, q, r = _sintetico_wiki(lang, n_wiki, q_wiki, SEED)
            docs += d; queries += q; qrels.update(r)
    try:
        code = _code_hf(n_code, rng)
        print(f"[carga_corpus] código: {len(code)} funciones desde CodeSearchNet (HF)")
    except Exception as e:  # noqa: BLE001
        print(f"[carga_corpus] CodeSearchNet falló ({str(e)[:90]}); uso funciones REALES de la stdlib de Python (espejo offline)")
        code = _code_stdlib(n_code, q_code, rng)
    for k, (name, src, doc) in enumerate(code):
        docs.append({"id": f"code-{k:04d}", "lang": "code", "text": src})
    for j, k in enumerate(rng.sample(range(len(code)), min(q_code, len(code)))):
        qid = f"code-q{j:04d}"
        queries.append({"qid": qid, "lang": "code", "text": code[k][2]})
        qrels[qid] = {f"code-{k:04d}": 1}
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": source}
