"""Celdas compartidas por build_12.py, build_13.py y build_14.py (autor A5).

Cada notebook del curso es autocontenido: estas cadenas se incrustan en cada notebook
(NO se importan en Colab). Aquí viven los textos fuente de las celdas comunes:

- CODE_SETUP_*: instalación, semillas, device, FAST_DEV_RUN.
- CODE_CORPUS_SEED: PARAFRASIS = 29 conceptos técnicos x {EN, ES, código} escritos a mano (mini golden set).
- CODE_PARAFRASIS_LOADER: `corpus_parafrasis()`: mini golden set de paráfrasis/cruzado ES-EN-código (esquema del contrato).
- CODE_METRICS: nDCG/Recall/MRR (misma implementación canónica que el módulo 00).

Nota: carga_corpus() y las métricas canónicas vienen de poliglota_utils.py (módulo 00, autor A1); aquí solo viven
utilidades propias de A5 (setup, embedders de respaldo, mini golden set de paráfrasis, nDCG por query).
"""

CODE_SETUP_COMMON = r'''
import os, sys, time, math, random, json, warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore")

import numpy as np

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True      # True: tamaños diminutos (CPU en minutos). Pon False en Colab con GPU para la escala completa.
N_THREADS = int(os.environ.get("N_THREADS", "1" if FAST_DEV_RUN else "4"))
os.environ.setdefault("OMP_NUM_THREADS", str(N_THREADS))

try:
    import torch
    torch.manual_seed(SEED)
    torch.set_num_threads(N_THREADS)
    device = "cuda" if torch.cuda.is_available() else "cpu"
except ImportError:      # los fragmentos "desde cero" de NumPy funcionan sin torch
    torch, device = None, "cpu"
print(f"device={device} · FAST_DEV_RUN={FAST_DEV_RUN} · threads={N_THREADS}")
'''

CODE_CORPUS_SEED = r'''
# Mini-corpus sintético "Políglota": 29 conceptos técnicos x {EN, ES, código}. Es el FALLBACK del cargador de datos;
# tiene el mismo esquema que el corpus real. Las queries están parafraseadas a propósito para que no compartan
# casi ninguna palabra con el documento (así BM25 no es trivial y los embeddings multilingües sí aportan).
PARAFRASIS = [
 ("hnsw",
  "HNSW builds a multi-layer proximity graph. A search enters at the top layer, walks greedily towards the target and descends layer by layer, returning approximate neighbors in logarithmic time.",
  "HNSW construye un grafo de proximidad con varias capas. La búsqueda entra por la capa superior, avanza de forma voraz hacia el objetivo y desciende capa a capa, devolviendo vecinos aproximados en tiempo logarítmico.",
  "def greedy_search(graph, vectors, q, entry):\n    best, improved = entry, True\n    while improved:\n        improved = False\n        for nb in graph[best]:\n            if dist(vectors[nb], q) < dist(vectors[best], q):\n                best, improved = nb, True\n    return best",
  "find similar vectors fast by hopping through a layered network", "buscar vectores parecidos rápido saltando por una red de niveles"),
 ("inverted_index",
  "An inverted index maps every term to the list of documents that contain it, so a keyword query only reads the posting lists of its terms instead of scanning the whole collection.",
  "Un índice invertido asocia cada término con la lista de documentos que lo contienen, de modo que una consulta solo lee las listas de sus términos en lugar de recorrer toda la colección.",
  "def build_index(docs):\n    index = {}\n    for doc_id, text in docs.items():\n        for term in set(text.lower().split()):\n            index.setdefault(term, []).append(doc_id)\n    return index",
  "data structure that avoids scanning every document for a word", "estructura que evita recorrer todos los textos al buscar una palabra"),
 ("bm25",
  "BM25 scores a document by summing, for each query term, its inverse document frequency times a saturating term frequency, normalized by document length with parameters k1 and b.",
  "BM25 puntúa un documento sumando, para cada término de la consulta, su frecuencia inversa de documento por una frecuencia de término saturada, normalizada por la longitud del documento con los parámetros k1 y b.",
  "def bm25_term(tf, idf, dl, avgdl, k1=1.2, b=0.75):\n    norm = k1 * (1 - b + b * dl / avgdl)\n    return idf * tf * (k1 + 1) / (tf + norm)",
  "classic keyword ranking formula with length normalization", "fórmula clásica de ranking por palabras clave que penaliza textos largos"),
 ("bpe",
  "Byte-pair encoding starts from single bytes and repeatedly merges the most frequent adjacent pair into a new token until the vocabulary reaches the desired size.",
  "La codificación por pares de bytes parte de bytes sueltos y fusiona repetidamente el par adyacente más frecuente en un nuevo token hasta alcanzar el tamaño de vocabulario deseado.",
  "def most_frequent_pair(ids):\n    counts = {}\n    for a, b in zip(ids, ids[1:]):\n        counts[(a, b)] = counts.get((a, b), 0) + 1\n    return max(counts, key=counts.get)",
  "how a language model splits text into subword pieces by merging common pairs", "cómo un modelo de lenguaje trocea el texto en piezas fusionando pares comunes"),
 ("cosine",
  "Cosine similarity measures the angle between two vectors: the dot product divided by the product of their norms. It ignores magnitude and ranges from -1 to 1.",
  "La similitud del coseno mide el ángulo entre dos vectores: el producto punto dividido por el producto de sus normas. Ignora la magnitud y va de -1 a 1.",
  "def cosine(a, b):\n    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))",
  "compare two vectors by direction rather than length", "comparar dos vectores por su dirección y no por su longitud"),
 ("kmeans",
  "K-means alternates two steps: assign every point to its nearest centroid, then move each centroid to the mean of its assigned points, until assignments stop changing.",
  "K-means alterna dos pasos: asignar cada punto a su centroide más cercano y mover cada centroide a la media de sus puntos, hasta que las asignaciones dejan de cambiar.",
  "def kmeans_step(X, C):\n    d = ((X[:, None] - C[None]) ** 2).sum(-1)\n    a = d.argmin(1)\n    return np.stack([X[a == k].mean(0) for k in range(len(C))]), a",
  "group unlabeled points into clusters around moving centers", "agrupar puntos sin etiquetas alrededor de centros que se desplazan"),
 ("pq",
  "Product quantization splits a vector into sub-vectors and replaces each by the index of its nearest codeword, compressing a float vector to a few bytes while allowing fast approximate distances.",
  "La cuantización de producto divide un vector en subvectores y sustituye cada uno por el índice de su palabra de código más cercana, comprimiendo un vector de floats a pocos bytes con distancias aproximadas rápidas.",
  "def pq_encode(x, codebooks):\n    subs = np.split(x, len(codebooks))\n    return [int(((cb - s) ** 2).sum(1).argmin()) for s, cb in zip(subs, codebooks)]",
  "shrink embeddings to a handful of bytes using small codebooks", "reducir embeddings a unos pocos bytes usando diccionarios pequeños"),
 ("reranker",
  "A cross-encoder reranker reads the query and a candidate document together in one transformer pass and outputs a relevance score; it is accurate but too slow for the whole corpus.",
  "Un reranker cross-encoder lee la consulta y un documento candidato juntos en una sola pasada del transformer y devuelve una puntuación de relevancia; es preciso pero demasiado lento para todo el corpus.",
  "def rerank(model, query, candidates, top_n=10):\n    scores = model.predict([(query, c) for c in candidates])\n    order = np.argsort(-scores)[:top_n]\n    return [candidates[i] for i in order]",
  "second-stage model that rescores a short list of candidates jointly with the question", "modelo de segunda etapa que reordena una lista corta mirando pregunta y texto a la vez"),
 ("matryoshka",
  "Matryoshka representation learning trains an embedding so that its first m dimensions already form a good smaller embedding, letting you truncate vectors and re-normalize them to save memory.",
  "El aprendizaje de representaciones Matryoshka entrena un embedding para que sus primeras m dimensiones ya formen un embedding más pequeño útil, permitiendo truncar los vectores y renormalizarlos para ahorrar memoria.",
  "def truncate(emb, m):\n    out = emb[:, :m]\n    return out / np.linalg.norm(out, axis=1, keepdims=True)",
  "cut a vector to fewer coordinates without retraining", "recortar un vector a menos coordenadas sin volver a entrenar"),
 ("contrastive",
  "Contrastive loss pulls the embeddings of matching pairs together and pushes apart the other examples in the batch, using a softmax over similarities scaled by a temperature.",
  "La pérdida contrastiva acerca los embeddings de los pares que coinciden y aleja el resto de ejemplos del lote, usando un softmax sobre similitudes escaladas por una temperatura.",
  "def info_nce(q, d, tau=0.05):\n    logits = (q @ d.T) / tau\n    labels = torch.arange(len(q))\n    return torch.nn.functional.cross_entropy(logits, labels)",
  "training objective that treats other items in the batch as wrong answers", "objetivo de entrenamiento que trata los demás ejemplos del lote como respuestas erróneas"),
 ("attention",
  "Self-attention lets every token build its representation as a weighted average of all value vectors, with weights given by the softmax of scaled query-key dot products.",
  "La autoatención permite que cada token construya su representación como un promedio ponderado de todos los vectores de valor, con pesos dados por el softmax de productos punto consulta-clave escalados.",
  "def attention(q, k, v):\n    w = torch.softmax(q @ k.T / q.shape[-1] ** 0.5, dim=-1)\n    return w @ v",
  "mechanism where each word looks at all the other words to update itself", "mecanismo en el que cada palabra mira a todas las demás para actualizarse"),
 ("cosine_decay",
  "A cosine learning-rate schedule starts at the peak value after warmup and decays smoothly towards zero following half a cosine wave, avoiding abrupt drops late in training.",
  "Un calendario de tasa de aprendizaje con coseno parte del valor máximo tras el calentamiento y decae suavemente hacia cero siguiendo media onda de coseno, evitando caídas bruscas al final del entrenamiento.",
  "def lr_at(step, total, peak=3e-4):\n    return 0.5 * peak * (1 + math.cos(math.pi * step / total))",
  "how to shrink the step size smoothly while a network trains", "cómo reducir poco a poco el tamaño del paso mientras una red entrena"),
 ("dropout",
  "Dropout randomly zeroes a fraction of activations during training and rescales the rest, which discourages co-adaptation of neurons and acts as a regularizer; it is disabled at inference.",
  "Dropout pone a cero al azar una fracción de las activaciones durante el entrenamiento y reescala el resto, lo que evita la coadaptación de neuronas y actúa como regularizador; se desactiva en inferencia.",
  "def dropout(x, p=0.1, training=True):\n    if not training:\n        return x\n    mask = (np.random.rand(*x.shape) > p) / (1 - p)\n    return x * mask",
  "randomly switching off neurons to reduce overfitting", "apagar neuronas al azar para reducir el sobreajuste"),
 ("layernorm",
  "Layer normalization standardizes each token's feature vector to zero mean and unit variance and then applies a learned scale and shift, stabilizing the training of deep transformers.",
  "La normalización por capas estandariza el vector de características de cada token a media cero y varianza uno y luego aplica una escala y un desplazamiento aprendidos, estabilizando el entrenamiento de transformers profundos.",
  "def layer_norm(x, g, b, eps=1e-5):\n    mu = x.mean(-1, keepdims=True)\n    var = x.var(-1, keepdims=True)\n    return g * (x - mu) / np.sqrt(var + eps) + b",
  "rescale each feature vector so deep networks train stably", "reescalar cada vector de características para que las redes profundas entrenen estables"),
 ("grad_clip",
  "Gradient clipping rescales the gradient whenever its global norm exceeds a threshold, which prevents rare huge updates from destabilizing training.",
  "El recorte de gradiente reescala el gradiente cada vez que su norma global supera un umbral, lo que evita que actualizaciones enormes y poco frecuentes desestabilicen el entrenamiento.",
  "def clip_grad(grads, max_norm=1.0):\n    total = math.sqrt(sum(float((g ** 2).sum()) for g in grads))\n    scale = min(1.0, max_norm / (total + 1e-6))\n    return [g * scale for g in grads]",
  "limit the size of parameter updates to avoid exploding values", "limitar el tamaño de las actualizaciones de parámetros para evitar valores que explotan"),
 ("lru_cache",
  "An LRU cache keeps the most recently used entries and evicts the least recently used one when it is full, giving constant-time lookups with a hash map plus a linked list.",
  "Una caché LRU conserva las entradas usadas más recientemente y expulsa la menos reciente cuando se llena, con búsquedas en tiempo constante mediante un mapa hash y una lista enlazada.",
  "from collections import OrderedDict\n\nclass LRU:\n    def __init__(self, cap):\n        self.cap, self.d = cap, OrderedDict()\n    def get(self, k):\n        self.d.move_to_end(k)\n        return self.d[k]",
  "memory that forgets whatever was touched longest ago", "memoria que olvida lo que se tocó hace más tiempo"),
 ("token_bucket",
  "A token bucket rate limiter adds tokens at a fixed rate up to a maximum capacity; each request consumes one token and is rejected when the bucket is empty, allowing short bursts.",
  "Un limitador de tasa de cubeta de tokens añade tokens a ritmo fijo hasta una capacidad máxima; cada petición consume un token y se rechaza si la cubeta está vacía, lo que permite ráfagas cortas.",
  "def allow(bucket, now, rate=5.0, cap=10.0):\n    bucket['tokens'] = min(cap, bucket['tokens'] + (now - bucket['t']) * rate)\n    bucket['t'] = now\n    if bucket['tokens'] >= 1:\n        bucket['tokens'] -= 1\n        return True\n    return False",
  "stop an API client from sending too many requests per second", "impedir que un cliente de una API envíe demasiadas peticiones por segundo"),
 ("binary_search",
  "Binary search finds a value in a sorted array by repeatedly comparing it with the middle element and discarding half of the remaining range, so it needs only logarithmic comparisons.",
  "La búsqueda binaria encuentra un valor en un arreglo ordenado comparándolo repetidamente con el elemento central y descartando la mitad del rango restante, por lo que solo necesita comparaciones logarítmicas.",
  "def binary_search(a, x):\n    lo, hi = 0, len(a) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if a[mid] == x:\n            return mid\n        lo, hi = (mid + 1, hi) if a[mid] < x else (lo, mid - 1)\n    return -1",
  "locate an item in an ordered list by halving the range each time", "localizar un elemento en una lista ordenada partiendo el rango a la mitad cada vez"),
 ("hash_collision",
  "A hash table maps keys to buckets with a hash function; when two keys land in the same bucket a collision occurs, resolved by chaining or open addressing.",
  "Una tabla hash asigna claves a cubetas mediante una función hash; cuando dos claves caen en la misma cubeta ocurre una colisión, que se resuelve con encadenamiento o direccionamiento abierto.",
  "def put(table, key, value):\n    bucket = table[hash(key) % len(table)]\n    for i, (k, _) in enumerate(bucket):\n        if k == key:\n            bucket[i] = (key, value)\n            return\n    bucket.append((key, value))",
  "what happens when two different keys map to the same slot", "qué pasa cuando dos claves distintas caen en la misma casilla"),
 ("deadlock",
  "A deadlock happens when two threads each hold a lock the other needs and wait forever; acquiring locks in a single global order prevents the circular wait.",
  "Un interbloqueo ocurre cuando dos hilos retienen cada uno un candado que el otro necesita y esperan para siempre; adquirir los candados en un único orden global evita la espera circular.",
  "def transfer(a, b, amount):\n    first, second = sorted([a, b], key=id)\n    with first.lock:\n        with second.lock:\n            a.balance -= amount\n            b.balance += amount",
  "two threads waiting on each other forever", "dos hilos esperándose mutuamente para siempre"),
 ("btree_index",
  "A B-tree index keeps keys sorted in a balanced tree with wide nodes, so a database can find a row or scan a range with only a few disk reads.",
  "Un índice B-tree mantiene las claves ordenadas en un árbol balanceado con nodos anchos, de modo que una base de datos puede encontrar una fila o recorrer un rango con pocas lecturas de disco.",
  "def create_index(cursor):\n    cursor.execute('CREATE INDEX idx_users_email ON users (email)')\n    cursor.execute('EXPLAIN SELECT * FROM users WHERE email = ?', ('a@b.c',))",
  "make database lookups on a column faster with a sorted tree", "acelerar las búsquedas de una columna en una base de datos con un árbol ordenado"),
 ("sharding",
  "Sharding splits a large dataset across several machines by a shard key, so each node stores and serves only part of the data and capacity grows horizontally.",
  "El sharding reparte un conjunto de datos grande entre varias máquinas según una clave de partición, de modo que cada nodo almacena y sirve solo una parte y la capacidad crece horizontalmente.",
  "def shard_for(key, n_shards):\n    h = int(hashlib.md5(key.encode()).hexdigest(), 16)\n    return h % n_shards",
  "distribute data over many servers so no single one holds everything", "distribuir los datos entre muchos servidores para que ninguno guarde todo"),
 ("backoff",
  "Exponential backoff retries a failed request after waiting 2^n times a base delay, usually with random jitter, so that many clients do not hammer a recovering service at once.",
  "El reintento con retroceso exponencial repite una petición fallida tras esperar 2^n veces un retardo base, normalmente con jitter aleatorio, para que muchos clientes no saturen a la vez un servicio que se recupera.",
  "def retry(fn, tries=5, base=0.5):\n    for n in range(tries):\n        try:\n            return fn()\n        except Exception:\n            time.sleep(base * 2 ** n * random.uniform(0.5, 1.5))\n    raise RuntimeError('agotados los reintentos')",
  "wait longer after each failed network call before trying again", "esperar más tras cada llamada de red fallida antes de volver a intentar"),
 ("mocking",
  "In unit tests a mock replaces a real dependency such as a network client, so the test is fast, deterministic and verifies how the code under test calls it.",
  "En las pruebas unitarias un mock sustituye una dependencia real, como un cliente de red, para que la prueba sea rápida, determinista y verifique cómo la llama el código bajo prueba.",
  "from unittest.mock import patch\n\ndef test_fetch():\n    with patch('app.http_get', return_value={'ok': True}) as m:\n        assert fetch('/x') == {'ok': True}\n        m.assert_called_once_with('/x')",
  "fake a service in a test so it runs without the internet", "simular un servicio en una prueba para que corra sin internet"),
 ("git_rebase",
  "Git rebase replays the commits of your branch on top of another base commit, producing a linear history instead of a merge commit, but it rewrites commit hashes.",
  "Git rebase reaplica los commits de tu rama encima de otro commit base, produciendo un historial lineal en lugar de un commit de fusión, pero reescribe los hashes de los commits.",
  "import subprocess\n\ndef rebase_onto_main():\n    subprocess.run(['git', 'fetch', 'origin'], check=True)\n    subprocess.run(['git', 'rebase', 'origin/main'], check=True)",
  "move my branch commits to the tip of main to keep a straight history", "mover los commits de mi rama a la punta de main para mantener un historial recto"),
 ("docker",
  "A Docker container packages an application with its dependencies and runs it as an isolated process that shares the host kernel, which makes deployments reproducible and lightweight.",
  "Un contenedor Docker empaqueta una aplicación con sus dependencias y la ejecuta como un proceso aislado que comparte el kernel del anfitrión, lo que hace los despliegues reproducibles y ligeros.",
  "import subprocess\n\ndef run_container(image, port=8000):\n    subprocess.run(['docker', 'run', '--rm', '-p', f'{port}:{port}', image], check=True)",
  "ship software with everything it needs so it runs the same everywhere", "entregar software con todo lo que necesita para que corra igual en cualquier sitio"),
 ("pagination",
  "Cursor-based pagination returns a page of results plus an opaque cursor pointing to the last item, which is more stable and efficient than offsets when the data changes between requests.",
  "La paginación por cursor devuelve una página de resultados junto con un cursor opaco que apunta al último elemento, algo más estable y eficiente que los desplazamientos cuando los datos cambian entre peticiones.",
  "def list_items(db, cursor=None, limit=20):\n    rows = db.query('SELECT * FROM items WHERE id > ? ORDER BY id LIMIT ?', cursor or 0, limit)\n    return rows, (rows[-1].id if rows else None)",
  "return long API results in chunks that stay consistent while data changes", "devolver resultados largos de una API en trozos que se mantienen coherentes mientras los datos cambian"),
 ("regex",
  "A regular expression describes a set of strings with literals, character classes and quantifiers; the engine scans the text and returns the matches, but nested quantifiers can cause catastrophic backtracking.",
  "Una expresión regular describe un conjunto de cadenas con literales, clases de caracteres y cuantificadores; el motor recorre el texto y devuelve las coincidencias, pero los cuantificadores anidados pueden causar retroceso catastrófico.",
  "import re\n\nEMAIL = re.compile(r'[\\w.+-]+@[\\w-]+\\.[\\w.]+')\n\ndef find_emails(text):\n    return EMAIL.findall(text)",
  "pattern language to extract pieces of text such as e-mail addresses", "lenguaje de patrones para extraer fragmentos de texto como direcciones de correo"),
 ("unicode_norm",
  "Unicode normalization converts equivalent character sequences to a canonical form: NFC composes accents into single code points, while NFD decomposes them into base letter plus combining mark.",
  "La normalización Unicode convierte secuencias de caracteres equivalentes a una forma canónica: NFC compone los acentos en un solo punto de código, mientras que NFD los descompone en letra base más marca combinante.",
  "import unicodedata\n\ndef strip_accents(s):\n    nfd = unicodedata.normalize('NFD', s)\n    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')",
  "make visually identical accented strings compare as equal", "lograr que cadenas con tildes visualmente idénticas se comparen como iguales"),
]
print(f"{len(PARAFRASIS)} conceptos x 3 documentos (en/es/código) en el mini golden set de paráfrasis")
'''

CODE_PARAFRASIS_LOADER = r'''
def corpus_parafrasis() -> dict:
    """Mini golden set de PARÁFRASIS y búsqueda CRUZADA ES<->EN<->código (29 conceptos x 3 documentos, 58 queries).
    Mismo esquema que carga_corpus(). Las queries casi no comparten palabras con sus documentos: BM25 sufre y los
    modelos semánticos/multilingües deberían ganar. Es un conjunto pequeño y escrito a mano: úsalo para diagnosticar,
    no para reportar cifras de producción."""
    docs, queries, qrels = [], [], {}
    for key, en, es, code, q_en, q_es in PARAFRASIS:
        ids = {"en": f"{key}-en", "es": f"{key}-es", "code": f"{key}-code"}
        docs += [{"id": ids["en"], "lang": "en", "text": en}, {"id": ids["es"], "lang": "es", "text": es},
                 {"id": ids["code"], "lang": "code", "text": code}]
        for lang, q in (("en", q_en), ("es", q_es)):
            qid = f"par-{key}-{lang}"
            queries.append({"qid": qid, "lang": lang, "text": q})
            qrels[qid] = {d: 1 for d in ids.values()}
    return {"docs": docs, "queries": queries, "qrels": qrels, "source": "paraphrase-golden"}
'''

CODE_METRICS = r'''
# ── Métricas de retrieval (misma implementación canónica que el módulo 00) ──────────────────
def _dedup(ranked_ids):
    seen, out = set(), []
    for d in ranked_ids:
        if d not in seen:
            seen.add(d); out.append(d)
    return out

def ndcg_at_k(ranked_ids, rels: dict, k: int = 10) -> float:
    """nDCG@k con ganancia lineal (trec_eval/BEIR/MTEB). rels: doc_id -> relevancia (>0 relevante)."""
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
    order = order[:k] if k else order
    return [doc_ids[i] for i in order]

def evaluate(run: dict, qrels: dict, k: int = 10, per_query: bool = False):
    """run: {qid: [doc_id ordenados]}. Devuelve medias de nDCG@k, Recall@k, MRR@k (y la lista por query si se pide)."""
    rows = []
    for qid, rels in qrels.items():
        if not any(r > 0 for r in rels.values()):
            continue
        ranked = run.get(qid, [])
        rows.append((ndcg_at_k(ranked, rels, k), recall_at_k(ranked, rels, k), mrr_at_k(ranked, rels, k)))
    arr = np.array(rows) if rows else np.zeros((0, 3))
    out = {"ndcg": arr[:, 0].mean(), "recall": arr[:, 1].mean(), "mrr": arr[:, 2].mean(), "n_queries": len(arr)}
    return (out, arr[:, 0]) if per_query else out
'''


CODE_EVAL_PQ = r'''
def ndcgs_por_query(run: dict, qrels: dict, k: int = 10):
    """nDCG@k de cada query (mismo filtro que evaluate(): solo queries con algún relevante). Sirve para bootstrap."""
    return np.array([ndcg_at_k(run.get(q, []), r, k) for q, r in qrels.items() if any(v > 0 for v in r.values())])
'''


CODE_EMBEDDER_TOOLS = r'''
# Catálogo de embedders multilingües "pequeños" (caben en CPU/T4). Prefijos copiados de las tarjetas de modelo:
# VERIFÍCALOS en la tarjeta antes de usar un modelo en producción (cambian entre versiones).
MODELOS = {
    "multilingual-e5-small": dict(hf="intfloat/multilingual-e5-small", q="query: ", d="passage: "),
    "multilingual-e5-base": dict(hf="intfloat/multilingual-e5-base", q="query: ", d="passage: "),
    "paraphrase-multilingual-MiniLM-L12-v2": dict(hf="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", q="", d=""),
    "gte-multilingual-base": dict(hf="Alibaba-NLP/gte-multilingual-base", q="", d="", trust=True),
    "bge-m3": dict(hf="BAAI/bge-m3", q="", d=""),
    "nomic-embed-text-v2-moe": dict(hf="nomic-ai/nomic-embed-text-v2-moe", q="search_query: ", d="search_document: ", trust=True),
    "Qwen3-Embedding-0.6B": dict(hf="Qwen/Qwen3-Embedding-0.6B", d="",
                                 q="Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:"),
    "embeddinggemma-300m": dict(hf="google/embeddinggemma-300m", q="task: search result | query: ", d="title: none | text: ", gated=True),
}

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD

class HashSVDEmbedder:
    """Fallback SIN descargas: TF-IDF de n-gramas de caracteres + SVD. NO es multilingüe ni semántico:
    sirve para ejercitar el pipeline (truncado, cuantización, métricas) cuando HF no es accesible."""
    def __init__(self, dim: int = 64, ngram=(3, 5), analyzer: str = "char_wb"):
        self.dim = dim
        self.tfidf = TfidfVectorizer(analyzer=analyzer, ngram_range=ngram, sublinear_tf=True, min_df=1)
        self.svd = TruncatedSVD(n_components=dim, random_state=SEED)
    def fit(self, textos):
        X = self.tfidf.fit_transform(textos)
        self.svd.n_components = min(self.dim, X.shape[1] - 1, X.shape[0] - 1)
        self.svd.fit(X)
        return self
    def encode(self, textos):
        Z = self.svd.transform(self.tfidf.transform(textos))
        return (Z / np.maximum(np.linalg.norm(Z, axis=1, keepdims=True), 1e-9)).astype(np.float32)

class Embedder:
    """Interfaz común: encode_queries / encode_docs (aplican el prefijo de cada modelo) -> float32 normalizado."""
    def __init__(self, clave, cfg, model=None, fallback=None):
        self.clave, self.cfg, self.model, self.fallback = clave, cfg, model, fallback
        self.is_real = model is not None
    def _enc(self, textos, prefijo, bs=16):
        if self.model is not None:
            E = self.model.encode([prefijo + t for t in textos], batch_size=bs, normalize_embeddings=True,
                                  convert_to_numpy=True, show_progress_bar=False)
            return E.astype(np.float32)
        return self.fallback.encode([prefijo + t for t in textos])
    def encode_queries(self, textos): return self._enc(textos, self.cfg.get("q", ""))
    def encode_docs(self, textos): return self._enc(textos, self.cfg.get("d", ""))
    @property
    def n_params(self):
        return sum(p.numel() for p in self.model.parameters()) if self.model is not None else 0

def cargar_embedder(clave, textos_ajuste=None, max_len=256):
    """Carga con sentence-transformers; si no se puede (sin red, modelo con licencia, falta de RAM) cae al fallback."""
    cfg = MODELOS[clave]
    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(cfg["hf"], device=device, trust_remote_code=cfg.get("trust", False))
        m.max_seq_length = min(m.max_seq_length or max_len, max_len)
        return Embedder(clave, cfg, model=m)
    except Exception as e:
        print(f"[embedder] {clave}: no se pudo cargar ({type(e).__name__}: {str(e)[:70]})")
        if textos_ajuste is None:
            return None
        print(f"[embedder] {clave}: usando fallback TF-IDF+SVD (NO representa al modelo real)")
        return Embedder(clave + " (fallback)", cfg, fallback=HashSVDEmbedder().fit(textos_ajuste))
'''
