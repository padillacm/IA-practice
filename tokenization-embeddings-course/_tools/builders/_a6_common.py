"""Fuentes de celdas compartidas por build_15/16/17 (autor A6).

Cada notebook es autocontenido: estas cadenas se copian TAL CUAL dentro de una celda de código.
Aquí NO se ejecuta nada; los builders hacen `from _a6_common import ...`.
"""

# ───────────────────────── Celda 1: datos de la versión sintética ─────────────────────────
SYNTH_DATA_SRC = r'''
# Corpus SINTÉTICO de Políglota (último recurso, mismo esquema que el real): 12 temas x 3 facetas.
# Por faceta: términos ES (5), EN (5), identificadores de código (3). Los 3 primeros términos son "centrales"
# (salen mucho en los documentos); los 2 últimos son sinónimos raros: las queries los usan -> hueco léxico.
TEMAS = {
 "cache": (["caché", "memoria", "datos"], ["cache", "memory", "data"], [
   ("ttl", "expiración|ttl|vencimiento|caducidad|refrescar", "expiration|ttl|timeout|lifetime|refresh", "set_ttl|expire_at|touch_key"),
   ("invalidacion", "invalidación|clave|purgar|obsoleto|desalojar", "invalidation|key|purge|stale|flush", "invalidate|purge_keys|delete_pattern"),
   ("evicion", "política|lru|desalojo|capacidad|recorte", "policy|lru|eviction|capacity|trim", "lru_evict|max_entries|pop_oldest")]),
 "basedatos": (["base", "datos", "consulta"], ["database", "data", "query"], [
   ("indices", "índice|b-tree|escaneo|selectividad|acelerar", "index|btree|scan|selectivity|speedup", "create_index|explain_plan|seq_scan"),
   ("transacciones", "transacción|commit|aislamiento|rollback|atomicidad", "transaction|commit|isolation|rollback|atomicity", "begin_tx|commit_tx|rollback_tx"),
   ("migraciones", "migración|esquema|columna|versionar|alterar", "migration|schema|column|versioning|alter", "run_migration|add_column|schema_version")]),
 "auth": (["usuario", "acceso", "seguridad"], ["user", "access", "security"], [
   ("tokens", "token|jwt|firma|sesión|testigo", "token|jwt|signature|session|bearer", "verify_jwt|sign_token|refresh_token"),
   ("oauth", "oauth|permiso|consentimiento|proveedor|delegar", "oauth|scope|consent|provider|delegate", "oauth_callback|request_scope|exchange_code"),
   ("hash", "contraseña|hash|sal|bcrypt|credencial", "password|hash|salt|bcrypt|credential", "hash_password|check_password|gen_salt")]),
 "contenedores": (["contenedor", "servicio", "despliegue"], ["container", "service", "deployment"], [
   ("imagenes", "imagen|capa|dockerfile|construir|empaquetar", "image|layer|dockerfile|build|package", "docker_build|pull_image|tag_image"),
   ("redes", "red|puerto|puente|exponer|conectar", "network|port|bridge|expose|connect", "create_network|publish_port|attach_bridge"),
   ("volumenes", "volumen|montaje|persistente|disco|compartir", "volume|mount|persistent|disk|share", "mount_volume|bind_path|prune_volumes")]),
 "testing": (["prueba", "código", "calidad"], ["test", "code", "quality"], [
   ("unitarias", "unitaria|aserción|fixture|función|verificar", "unit|assertion|fixture|function|verify", "assert_equal|run_unit|make_fixture"),
   ("mocks", "simulacro|mock|dependencia|sustituir|doble", "mock|stub|dependency|replace|double", "patch_call|make_mock|reset_mock"),
   ("cobertura", "cobertura|línea|rama|informe|medir", "coverage|line|branch|report|measure", "run_coverage|branch_report|min_cover")]),
 "concurrencia": (["hilo", "tarea", "ejecución"], ["thread", "task", "execution"], [
   ("hilos", "hilo|gil|paralelo|pool|lanzar", "thread|gil|parallel|pool|spawn", "start_thread|join_all|pool_map"),
   ("asincrono", "asíncrono|corrutina|await|bucle|esperar", "async|coroutine|await|loop|wait", "run_loop|gather_tasks|await_all"),
   ("bloqueos", "bloqueo|candado|interbloqueo|exclusión|sincronizar", "lock|mutex|deadlock|exclusion|synchronize", "acquire_lock|release_lock|try_lock")]),
 "api": (["api", "petición", "recurso"], ["api", "request", "resource"], [
   ("paginacion", "paginación|cursor|página|límite|desplazamiento", "pagination|cursor|page|limit|offset", "next_cursor|page_size|fetch_page"),
   ("versionado", "versión|compatibilidad|ruta|migrar|deprecar", "version|compatibility|route|migrate|deprecate", "api_version|route_v2|sunset_header"),
   ("limitacion", "cuota|tasa|límite|429|estrangular", "quota|rate|limit|429|throttle", "rate_limit|retry_after|token_bucket")]),
 "observabilidad": (["sistema", "registro", "evento"], ["system", "log", "event"], [
   ("logs", "log|nivel|formato|rotar|mensaje", "log|level|format|rotate|message", "get_logger|set_level|rotate_logs"),
   ("metricas", "métrica|contador|histograma|panel|alerta", "metric|counter|histogram|dashboard|alert", "inc_counter|observe_hist|export_metrics"),
   ("trazas", "traza|span|latencia|distribuido|correlación", "trace|span|latency|distributed|correlation", "start_span|inject_trace|trace_id")]),
 "git": (["repositorio", "cambio", "rama"], ["repository", "change", "branch"], [
   ("ramas", "rama|checkout|puntero|crear|cambiar", "branch|checkout|pointer|create|switch", "git_branch|git_checkout|list_branches"),
   ("merge", "fusión|merge|conflicto|resolver|integrar", "merge|conflict|resolve|integrate|combine", "git_merge|resolve_conflict|abort_merge"),
   ("rebase", "rebase|historial|reescribir|reaplicar|linealizar", "rebase|history|rewrite|replay|linearize", "git_rebase|squash_commits|pick_commit")]),
 "ml": (["modelo", "entrenamiento", "datos"], ["model", "training", "data"], [
   ("gradiente", "gradiente|descenso|pérdida|paso|optimizar", "gradient|descent|loss|step|optimize", "grad_step|zero_grad|clip_norm"),
   ("sobreajuste", "sobreajuste|regularización|generalizar|memorizar|dropout", "overfitting|regularization|generalize|memorize|dropout", "add_dropout|l2_penalty|early_stop"),
   ("validacion", "validación|pliegue|cruzada|partición|estimar", "validation|fold|cross|split|estimate", "kfold_split|val_score|holdout")]),
 "red": (["red", "paquete", "conexión"], ["network", "packet", "connection"], [
   ("tcp", "tcp|segmento|retransmisión|ventana|fiable", "tcp|segment|retransmission|window|reliable", "tcp_connect|set_window|resend_segment"),
   ("dns", "dns|dominio|resolución|registro|nombre", "dns|domain|resolution|record|name", "resolve_host|lookup_a|flush_dns"),
   ("tls", "tls|certificado|cifrado|apretón|confianza", "tls|certificate|encryption|handshake|trust", "tls_handshake|load_cert|verify_chain")]),
 "memoria": (["memoria", "proceso", "objeto"], ["memory", "process", "object"], [
   ("gc", "recolector|basura|referencia|ciclo|liberar", "collector|garbage|reference|cycle|free", "gc_collect|weak_ref|ref_count"),
   ("virtual", "virtual|página|dirección|paginación|fallo", "virtual|page|address|paging|fault", "map_page|page_fault|swap_out"),
   ("fugas", "fuga|crecimiento|perfilar|heap|retención", "leak|growth|profile|heap|retention", "heap_snapshot|track_alloc|find_leak")]),
}
'''.strip("\n")

# ───────────────────────── Celda 2: generador sintético + carga real ─────────────────────────
CORPUS_SRC = r'''
import os, random, re

PLANT_ES = ["Esta guía explica cómo {a} influye en {b} cuando se trabaja con {c}.",
            "Para resolver el problema de {a}, revisa primero {b} y luego {c}.",
            "En producción conviene vigilar {a}, porque {b} cambia el comportamiento de {c}.",
            "Un error habitual es mezclar {a} con {b} sin entender {c}.",
            "La documentación recomienda medir {a} antes de tocar {b} o {c}.",
            "Ejemplo práctico: ajustar {a} reduce el coste de {b} en {c}."]
PLANT_EN = ["This guide explains how {a} affects {b} when working with {c}.",
            "To solve the problem with {a}, first check {b} and then {c}.",
            "In production you should watch {a}, because {b} changes the behavior of {c}.",
            "A common mistake is mixing {a} with {b} without understanding {c}.",
            "The documentation recommends measuring {a} before touching {b} or {c}.",
            "Practical example: tuning {a} lowers the cost of {b} in {c}."]
QS_ES = ["cómo gestionar {s}", "problemas con {s}", "guía de {s}", "qué hacer con {s}"]
QS_EN = ["how to handle {s}", "problems with {s}", "guide to {s}", "what to do about {s}"]

def _slot(rng, core, rare, shared, other):
    r = rng.random()
    return rng.choice(core) if r < .62 else rng.choice(shared) if r < .80 else rng.choice(rare) if r < .86 else rng.choice(other)

def genera_sintetico(n_temas: int = 8, docs_por_faceta: int = 4, seed: int = 42) -> dict:
    """Mismo esquema que el corpus real. Relevancia: docs de la misma faceta e idioma (code: faceta, queries 'code')."""
    rng = random.Random(seed)
    nombres = list(TEMAS)[:n_temas]
    docs, queries, qrels = [], [], {}
    for t in nombres:
        es_sh, en_sh, facetas = TEMAS[t]
        for fid, es, en, code in facetas:
            otros = [x for n in nombres if n != t for x in TEMAS[n][2][0][1].split("|")[:3]]
            otros_en = [x for n in nombres if n != t for x in TEMAS[n][2][0][2].split("|")[:3]]
            es, en, code = es.split("|"), en.split("|"), code.split("|")
            rel = {"es": {}, "en": {}, "code": {}}
            for lang, terms, shared, oth, plant in (("es", es, es_sh, otros, PLANT_ES), ("en", en, en_sh, otros_en, PLANT_EN)):
                for i in range(docs_por_faceta):
                    sents = [rng.choice(plant).format(a=_slot(rng, terms[:3], terms[3:], shared, oth),
                                                      b=_slot(rng, terms[:3], terms[3:], shared, oth),
                                                      c=_slot(rng, terms[:3], terms[3:], shared, oth)) for _ in range(3)]
                    did = f"{lang}-{t}.{fid}-{i}"
                    docs.append({"id": did, "lang": lang, "text": " ".join(sents)}); rel[lang][did] = 1
            for i in range(max(2, docs_por_faceta - 1)):
                fn = rng.choice(code); aux = rng.choice(code); w = rng.choice(en[:3])
                did = f"code-{t}.{fid}-{i}"
                docs.append({"id": did, "lang": "code", "text": f"def {fn}(x, n={rng.randint(2, 9)}):\n    \"\"\"{w} helper for {rng.choice(en_sh)}\"\"\"\n    return {aux}(x, {rng.choice(code)})"})
                rel["code"][did] = 1
            for lang, terms, qs in (("es", es, QS_ES), ("en", en, QS_EN), ("code", en, QS_EN)):
                s = " ".join(([rng.choice(terms[:3])] if rng.random() < .5 else []) + rng.sample(terms[3:], 2))   # 50%: 1 central + 2 raros
                qid = f"q-{lang}-{t}.{fid}"
                queries.append({"qid": qid, "lang": lang, "text": rng.choice(qs).format(s=s) + (" function" if lang == "code" else "")})
                qrels[qid] = dict(rel[lang])
    rng.shuffle(docs)
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": "synthetic"}
'''.strip("\n")

REAL_SRC = r'''
def _carga_real(n_docs: int, seed: int = 42):
    """Cadena OFICIAL: HF `wikimedia/wikipedia` (ES/EN, streaming) + CodeSearchNet Python. Lanza excepción si no hay red/HF.
    Espejo: define HF_ENDPOINT=https://hf-mirror.com ANTES de importar `datasets` (reinicia el runtime) y repite."""
    from datasets import load_dataset
    docs, queries, qrels = [], [], {}
    for lang, cfg in (("es", "20231101.es"), ("en", "20231101.en")):
        ds = load_dataset("wikimedia/wikipedia", cfg, split="train", streaming=True).shuffle(seed=seed, buffer_size=2000)
        got = 0
        for row in ds:
            body = re.sub(r"\s+", " ", row["text"].split("\n\n")[0]).strip()
            if len(body) < 200:
                continue
            did, qid = f"{lang}-{row['id']}", f"q-{lang}-{row['id']}"
            docs.append({"id": did, "lang": lang, "text": body[:700]})
            queries.append({"qid": qid, "lang": lang, "text": row["title"]}); qrels[qid] = {did: 1}
            got += 1
            if got >= n_docs: break
    cs = load_dataset("code-search-net/code_search_net", "python", split="test", streaming=True)
    got = 0
    for i, row in enumerate(cs):
        doc_str = (row.get("func_documentation_string") or "").strip().split("\n")[0]
        code = row.get("func_code_string") or row.get("whole_func_string") or ""
        if len(doc_str) < 25 or not code: continue
        did, qid = f"code-{i}", f"q-code-{i}"
        docs.append({"id": did, "lang": "code", "text": code[:700]})
        queries.append({"qid": qid, "lang": "code", "text": doc_str}); qrels[qid] = {did: 1}
        got += 1
        if got >= n_docs: break
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": "real"}

def carga_corpus(fast_dev: bool = True) -> dict:
    """Contrato Políglota: {"docs":[{id,lang,text}], "queries":[{qid,lang,text}], "qrels":{qid:{doc_id:1}}, "source":"real"|"synthetic"}.
    Cadena: oficial (HF) -> espejo (HF_ENDPOINT) -> sintético. NOTA: la versión real usa queries = título del artículo /
    docstring (golden set auto-supervisado, más fácil que uno humano); el sintético usa facetas con huecos léxicos."""
    if os.environ.get("POLIGLOTA_FORCE_SYNTHETIC") != "1":
        try:
            return _carga_real(n_docs=150 if fast_dev else 1500)
        except Exception as e:  # sin red, proxy, dataset movido...
            print(f"⚠️ Datos reales no disponibles ({type(e).__name__}: {str(e)[:80]}) -> corpus SINTÉTICO.")
    return genera_sintetico(n_temas=8 if fast_dev else 12)
'''.strip("\n")
