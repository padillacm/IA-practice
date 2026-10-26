# ── Generador del corpus sintético (mismo esquema que el real) ────────────────
import random


def _es_fix(s: str) -> str:
    """Contracciones del español: 'a el' -> 'al', 'de el' -> 'del'."""
    return s.replace(" a el ", " al ").replace(" de el ", " del ").replace("De el ", "Del ").replace("A el ", "Al ")


def _sintetico_wiki(lang: str, n_docs: int, n_queries: int, seed: int = 42):
    """Docs técnicos sintéticos ES/EN: concepto x aspecto x herramienta. Devuelve (docs, queries, qrels)."""
    rng = random.Random(seed + (0 if lang == "es" else 1))
    li = 0 if lang == "es" else 1
    combos = [(c, a, t) for c in range(len(CONCEPTOS)) for a in ASPECTOS for t in range(len(HERRAMIENTAS))]
    rng.shuffle(combos)
    docs, titles = [], []
    for k, (ci, asp, ti) in enumerate(combos[:n_docs]):
        concepto, definicion = CONCEPTOS[ci][li], CONCEPTOS[ci][2 + li]
        tool = HERRAMIENTAS[ti]
        tit_t, plantillas = ASPECTOS[asp][li], ASPECTOS[asp][4 + li]
        nombre = concepto.split(" ", 1)[1] if concepto.split(" ", 1)[0] in ("el", "la", "los", "las", "the") else concepto
        slots = lambda: dict(c=concepto, t=tool, p=rng.choice(PARAMETROS), x=rng.choice([8, 16, 30, 64, 100, 256, 1024]))
        frases = [("{C} " + ("es " if li == 0 else "is ") + definicion + ".").format(C=concepto)]
        frases += [pl.format(**slots()) for pl in rng.sample(plantillas, len(plantillas))]
        frases.append(rng.choice(ASPECTOS["intro"][4 + li]).format(**slots()))
        for _ in range(2):  # ruido: frases de otro concepto (hace el retrieval no trivial)
            otro = rng.randrange(len(CONCEPTOS))
            otra = rng.choice(list(ASPECTOS.values()))[4 + li]
            s = slots(); s["c"] = CONCEPTOS[otro][li]
            frases.append(rng.choice(otra).format(**s))
        s = slots()
        frases.append(("Ejemplo: `{p} = {x}`." if li == 0 else "Example: `{p} = {x}`.").format(**s))
        text = " ".join(f[0].upper() + f[1:] for f in frases)
        docs.append({"id": f"{lang}-syn-{k:04d}", "lang": lang, "text": _es_fix(text) if lang == "es" else text})
        titles.append((nombre, ASPECTOS[asp][2 + li], tool, tit_t.format(n=nombre) + f" ({tool})"))
    queries, qrels = [], {}
    for j, k in enumerate(rng.sample(range(len(docs)), min(n_queries, len(docs)))):
        nombre, kw, tool, titulo = titles[k]
        q = titulo.replace(":", "").replace("(", "").replace(")", "") if j % 2 == 0 else f"{nombre} {kw} {tool}"
        qid = f"{lang}-q{j:04d}"
        queries.append({"qid": qid, "lang": lang, "text": q})
        qrels[qid] = {docs[k]["id"]: 1}
    return docs, queries, qrels
