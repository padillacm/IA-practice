"""Celdas compartidas por los builders de A4 (módulos 09, 10 y 11).

El corpus Políglota y las métricas canónicas vienen de `poliglota_utils.py` (módulo 00). Aquí solo vive el
«mundo de juguete» del módulo 11 (laboratorio controlado de aprendizaje contrastivo) y un helper de evaluación.
"""

# ── Mundo de juguete (laboratorio controlado del módulo 11) ───────────────────────────────────────────────────────────────────────────
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


def genera_mundo_juguete(fast_dev: bool = True, seed: int = 42) -> dict:
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
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": "toy"}
'''

# ── Cargador REAL (se ejecuta en el proceso o en un subproceso con HF_ENDPOINT=espejo) ────────────────────────
# Evaluación de un embedder sobre el corpus: matriz de similitud -> run -> métricas
EVAL_CELL = '''
def evalua_scores(S, qs, doc_ids, qrels, k=10):
    """S: (n_queries, n_docs) similitudes -> {'ndcg','recall','mrr'}@k promediadas sobre qs."""
    run = {q["qid"]: rank_from_scores(S[i], doc_ids, 100) for i, q in enumerate(qs)}
    return evaluate(run, {q["qid"]: qrels[q["qid"]] for q in qs}, k)
'''

