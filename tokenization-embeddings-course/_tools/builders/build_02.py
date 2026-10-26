"""Genera el módulo 02_bpe_desde_cero: README + lección + proyecto.   Ejecutar desde la raíz del repo:
    python tokenization-embeddings-course/_tools/builders/build_02.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_tools"))
sys.path.insert(0, str(ROOT / "_tools" / "builders"))
from a1_common import SRC_GPT2, SRC_PLOT_STYLE, caja, details, mapa_madurez, obs, pista, preguntas  # noqa: E402
from nbbuild import Notebook  # noqa: E402
from poliglota_utils import src_corpus_cells  # noqa: E402

MOD = ROOT / "02_bpe_desde_cero"
MOD.mkdir(exist_ok=True)
(MOD / "assets").mkdir(exist_ok=True)
(MOD / "assets" / ".gitkeep").touch()
REL = "tokenization-embeddings-course/02_bpe_desde_cero"

# ════════════════════════════════════════════════════════════════════════════
#  Código reutilizable (lección + solución del proyecto): patrones, entrenadores, tokenizer
# ════════════════════════════════════════════════════════════════════════════
SRC_PATTERNS = r'''
import regex

# Patrones de pre-tokenización copiados de tiktoken 0.14.0 (tiktoken_ext/openai_public.py; verificados el 25-oct-2026)
PAT_GPT2 = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}++| ?\p{N}++| ?[^\s\p{L}\p{N}]++|\s++$|\s+(?!\S)|\s"""
PAT_CL100K = r"""'(?i:[sdmt]|ll|ve|re)|[^\r\n\p{L}\p{N}]?+\p{L}++|\p{N}{1,3}+| ?[^\s\p{L}\p{N}]++[\r\n]*+|\s++$|\s*[\r\n]|\s+(?!\S)|\s"""
PAT_O200K = "|".join([
    r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]*[\p{Ll}\p{Lm}\p{Lo}\p{M}]+(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
    r"""[^\r\n\p{L}\p{N}]?[\p{Lu}\p{Lt}\p{Lm}\p{Lo}\p{M}]+[\p{Ll}\p{Lm}\p{Lo}\p{M}]*(?i:'s|'t|'re|'ve|'m|'ll|'d)?""",
    r"""\p{N}{1,3}""", r""" ?[^\s\p{L}\p{N}]+[\r\n/]*""", r"""\s*[\r\n]+""", r"""\s+(?!\S)""", r"""\s+"""])
PAT_ESPACIOS = r"""\s?\S+|\s+"""      # línea base SIN categorías: corta solo por espacios (puntuación pegada a la palabra)
PATRONES = {"gpt2": PAT_GPT2, "cl100k": PAT_CL100K, "o200k": PAT_O200K, "solo espacios": PAT_ESPACIOS}
'''.strip("\n")

SRC_TRAIN = r'''
import heapq
from collections import Counter, defaultdict


def contar_palabras(textos, pat_str=PAT_GPT2):
    """Corpus -> {palabra (tupla de bytes): frecuencia}. Entrenar sobre palabras únicas ponderadas es lo que hace Sennrich."""
    pat = regex.compile(pat_str)
    return Counter(tuple(w.encode("utf-8")) for t in textos for w in pat.findall(t))


def fusiona_palabra(w, par, nuevo):
    a, b = par; out, i = [], 0
    while i < len(w):
        if i < len(w) - 1 and w[i] == a and w[i + 1] == b:
            out.append(nuevo); i += 2
        else:
            out.append(w[i]); i += 1
    return out


def entrena_ingenuo(wc, n_merges, tie="lex"):
    """O(M · U): recuenta TODOS los pares en cada iteración. tie='lex' (menor par) o 'first' (primer visto, como tiktoken._educational)."""
    palabras, frec, merges = [list(w) for w in wc], list(wc.values()), []
    for k in range(n_merges):
        stats = Counter()
        for w, f in zip(palabras, frec):
            for p in zip(w, w[1:]):
                stats[p] += f
        if not stats:
            break
        par = min(stats, key=lambda p: (-stats[p], p)) if tie == "lex" else max(stats, key=stats.get)
        merges.append(par)
        palabras = [fusiona_palabra(w, par, 256 + k) for w in palabras]
    return merges
'''.strip("\n")

SRC_TRAIN_INC = r'''
def entrena_incremental(wc, n_merges):
    """Conteo INCREMENTAL: contadores de pares + índice invertido par -> palabras + heap con invalidación perezosa.
    Cada merge solo toca las palabras que contienen el par y ajusta los contadores de sus vecinos."""
    palabras, frec = [list(w) for w in wc], list(wc.values())
    stats, donde = Counter(), defaultdict(set)
    for i, (w, f) in enumerate(zip(palabras, frec)):
        for p in zip(w, w[1:]):
            stats[p] += f; donde[p].add(i)
    heap = [(-c, p) for p, c in stats.items()]; heapq.heapify(heap); merges = []
    while len(merges) < n_merges and heap:
        negc, par = heapq.heappop(heap)
        if stats.get(par, 0) != -negc:                       # entrada obsoleta: el contador cambió desde que se metió
            continue
        nuevo, (a, b), cambiados = 256 + len(merges), par, set(); merges.append(par)
        for i in list(donde[par]):
            w, f, out, j = palabras[i], frec[i], [], 0
            while j < len(w):
                if j < len(w) - 1 and w[j] == a and w[j + 1] == b:
                    if out:                                  # vecino izquierdo
                        stats[(out[-1], a)] -= f; stats[(out[-1], nuevo)] += f; donde[(out[-1], nuevo)].add(i)
                        cambiados |= {(out[-1], a), (out[-1], nuevo)}
                    if j + 2 < len(w):                       # vecino derecho
                        stats[(b, w[j + 2])] -= f; stats[(nuevo, w[j + 2])] += f; donde[(nuevo, w[j + 2])].add(i)
                        cambiados |= {(b, w[j + 2]), (nuevo, w[j + 2])}
                    stats[par] -= f; out.append(nuevo); j += 2
                else:
                    out.append(w[j]); j += 1
            palabras[i] = out
        del stats[par]; donde.pop(par, None)
        for p in cambiados - {par}:
            c = stats.get(p, 0)
            if c > 0:
                heapq.heappush(heap, (-c, p))
            else:
                stats.pop(p, None)
    return merges
'''.strip("\n")

SRC_TOKENIZER = r'''
class BPETokenizer:
    """Byte-level BPE. vocab: id -> bytes. merges: (id_a, id_b) -> id nuevo; el id nuevo ES la prioridad (menor = antes)."""

    def __init__(self, pat_str=PAT_GPT2, vocab=None, merges=None, special_tokens=None):
        self.pat_str, self.pat = pat_str, regex.compile(pat_str)
        self.vocab = vocab or {i: bytes([i]) for i in range(256)}
        self.merges = merges or {}
        self.special = special_tokens or {}
        self.byte2id = {b: i for i, b in self.vocab.items() if len(b) == 1}
        self._cache = {}

    @classmethod
    def train(cls, textos, vocab_size, pat_str=PAT_GPT2, tie="lex"):
        wc = contar_palabras(textos, pat_str)
        lista = entrena_incremental(wc, vocab_size - 256) if tie == "lex" else entrena_ingenuo(wc, vocab_size - 256, tie)
        vocab, merges = {i: bytes([i]) for i in range(256)}, {}
        for k, (a, b) in enumerate(lista):
            vocab[256 + k] = vocab[a] + vocab[b]; merges[(a, b)] = 256 + k
        return cls(pat_str, vocab, merges)

    def _encode_trozo(self, trozo: str, max_id=None):
        clave = (trozo, max_id)
        if clave not in self._cache:
            ids = [self.byte2id[bytes([b])] for b in trozo.encode("utf-8")]
            while len(ids) > 1:
                cand = [(self.merges.get(p, 1 << 60), p) for p in zip(ids, ids[1:])]
                rango, par = min(cand)                       # el par de MENOR id = el que se aprendió antes
                if rango == 1 << 60 or (max_id is not None and rango >= max_id):
                    break
                ids = fusiona_palabra(ids, par, rango)
            self._cache[clave] = ids
        return self._cache[clave]

    def encode(self, texto: str, allowed_special=(), max_id=None) -> list[int]:
        partes = [texto]
        if allowed_special:
            partes = regex.split("(" + "|".join(map(regex.escape, allowed_special)) + ")", texto)
        ids = []
        for p in partes:
            if p in self.special and p in allowed_special:
                ids.append(self.special[p])
            else:
                ids += [i for t in self.pat.findall(p) for i in self._encode_trozo(t, max_id)]
        return ids

    def decode_bytes(self, ids) -> bytes:
        inv = {v: k.encode() for k, v in self.special.items()}
        return b"".join(self.vocab[i] if i in self.vocab else inv[i] for i in ids)

    def decode(self, ids) -> str:
        return self.decode_bytes(ids).decode("utf-8", errors="replace")
'''.strip("\n")

SRC_TIKTOKEN_BRIDGE = r'''
import tiktoken


def a_tiktoken(tok, nombre="mi_bpe"):
    """Mi tokenizer como tiktoken.Encoding: mergeable_ranks = {bytes del token: id}. Los ids ya son las prioridades."""
    ranks = {tok.vocab[i]: i for i in sorted(tok.vocab)}
    assert len(ranks) == len(tok.vocab), "hay dos tokens con los mismos bytes: tiktoken no lo admite"
    return tiktoken.Encoding(nombre, pat_str=tok.pat_str, mergeable_ranks=ranks, special_tokens=dict(tok.special))


def bpe_bytes(ranks, pieza: bytes, max_rank=None):
    """Algoritmo de tiktoken sobre bytes: fusiona el par adyacente cuya unión tenga menor rango (< max_rank)."""
    partes = [bytes([b]) for b in pieza]
    while len(partes) > 1:
        mejor = min(((ranks.get(a + b), i) for i, (a, b) in enumerate(zip(partes, partes[1:])) if ranks.get(a + b) is not None), default=None)
        if mejor is None or (max_rank is not None and mejor[0] >= max_rank):
            break
        i = mejor[1]; partes[i:i + 2] = [partes[i] + partes[i + 1]]
    return partes


def desde_tiktoken(enc):
    """Recupera MIS estructuras (vocab, merges) desde un tiktoken.Encoding real (receta de minbpe: re-fusionar cada token con max_rank=su rango)."""
    ranks = enc._mergeable_ranks
    vocab = {r: b for b, r in ranks.items()}
    merges = {}
    for b, r in ranks.items():
        if len(b) > 1:
            a1, a2 = bpe_bytes(ranks, b, max_rank=r)
            merges[(ranks[a1], ranks[a2])] = r
    return BPETokenizer(enc._pat_str, vocab, merges, dict(enc._special_tokens))
'''.strip("\n")

# ════════════════════════════════════════════════════════════════════════════
#  LECCIÓN
# ════════════════════════════════════════════════════════════════════════════
LPATH = f"{REL}/02_bpe_desde_cero.ipynb"
nb = Notebook("Módulo 02 · BPE desde cero", colab_path=LPATH)

nb.md(nb.badge() + r"""

# Módulo 02 · BPE desde cero
**Tokenización y Embeddings: de BPE a los modelos modernos**

| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración** | ≈ 5 h (lección ≈ 3 h + proyecto ≈ 2 h) |
| **GPU / coste** | Ninguna: CPU (0 unidades de Colab Pro) |
| **Prerrequisitos** | Módulo 00 (corpus Políglota) y módulo 01 (bytes, UTF-8, normalización) |

> **Estado del arte de referencia: octubre de 2026.** Las cifras sujetas a cambio llevan fecha; las técnicas se etiquetan 🟢 / 🟡 / 🔴.
""")

nb.md(r"""
## Objetivos de aprendizaje
1. **Explicar** por qué los LLM usan sub-palabras y situar BPE entre la tokenización por palabras y por caracteres.
2. **Resolver a mano** el entrenamiento de BPE sobre un corpus de 4 palabras y **reproducirlo** en código.
3. **Implementar** byte-level BPE completo: pre-tokenización con regex, entrenamiento con conteo incremental, `encode` por orden de merges y `decode`.
4. **Comparar** los patrones de pre-tokenización de GPT-2, cl100k y o200k y **predecir** cómo trocean texto, números y código.
5. **Verificar** tu implementación contra `tiktoken` y Hugging Face `tokenizers` (y contra el vocabulario real de GPT-2), y **explicar** las diferencias de entrenamiento (desempates).
6. **Medir** compresión (bytes/token, bits/byte), efecto del tamaño de vocabulario, «impuesto» por idioma y complejidad temporal.
7. **Analizar** BPE como compresor (analogía con Huffman/LZ) y sus límites teóricos.
""")

nb.md(r"""
## 🔁 Conexión con módulos anteriores
""" + "\n" + preguntas([
    ("", "¿Cuántos bytes UTF-8 ocupa «ñ» y qué pasa si el vocabulario no tiene un token que la contenga?",
     "2 bytes (`C3 B1`). Un tokenizer byte-level la representa como dos tokens de un byte: nunca hay «desconocidos», pero cuesta más. Este módulo te enseña por qué."),
    ("", "¿Por qué `é` en NFC y en NFD producen tokens distintos en un tokenizer byte-level?",
     "Porque el tokenizer solo ve bytes: NFC → `C3 A9`; NFD → `65 CC 81`. Son secuencias distintas sobre las que se aprendieron (o no) fusiones distintas."),
    ("", "¿Qué convención de desempates usa `rank_from_scores` en el módulo 00 y por qué importa?",
     "Orden del corpus (determinista). Los empates arbitrarios cambian rankings entre ejecuciones; en BPE los desempates entre pares con el mismo conteo también cambian el vocabulario (lo verás hoy)."),
    ("", "¿Qué hace tu `normalizar` (módulo 01) y dónde encaja respecto al tokenizer?",
     "Deja el texto en una forma canónica (NFC, sin invisibles ni mojibake…) **antes** del tokenizer y del índice; hay que aplicar la misma función en entrenamiento e inferencia."),
]))

nb.md(caja("🧭 Ruta núcleo vs ampliación", r"""
La lección tiene ≈ 80 celdas. **Ruta núcleo (≈ 2 h 15 min):** secciones 1–6, 8 (verificación con tiktoken), 9.1 (tamaño de vocabulario) y 9.3 (impuesto por idioma). **Ampliación:** 7 (decodificación incremental y especiales), 9.2, 9.4–9.6 (regex, compresión, orden de merges) y 10 (complejidad). El proyecto asume la ruta núcleo.
"""))

nb.code(r'''
!pip install -q numpy pandas matplotlib regex tiktoken tokenizers
''')
nb.code(SRC_PLOT_STYLE + r'''

import heapq, math, random, sys, time, unicodedata, zlib, bz2, lzma, re, collections
from collections import Counter, defaultdict
import numpy as np, pandas as pd

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True      # True: vocabularios de 1 000 y corpus pequeño (segundos). False: vocabularios de 4 000 y corpus mayor.
VOCAB = 1000 if FAST_DEV_RUN else 4000
print(f"python {sys.version.split()[0]} | FAST_DEV_RUN = {FAST_DEV_RUN} | VOCAB = {VOCAB}")
''')

nb.md(r"""
## 1. Intuición: tres formas de partir un texto

| Estrategia | Vocabulario | Palabras desconocidas | Longitud de la secuencia |
|---|---|---|---|
| **Palabras** | enorme (cientos de miles) y aun así incompleto | **sí** (OOV → `<unk>`) | corta |
| **Caracteres / bytes** | diminuto (≤ 256 bytes) | no | **muy larga** (1 token por byte) |
| **Sub-palabras (BPE)** | intermedio (32 000 – 262 000) | **no** (si es byte-level) | media |

BPE busca el punto medio **aprendiendo de los datos**: las secuencias frecuentes se convierten en tokens («ción», « the»), las raras se descomponen en piezas más pequeñas, y en el peor caso en bytes. Es un **compromiso entre tamaño de vocabulario y longitud de secuencia**: cada token extra en el vocabulario acorta los textos, pero cuesta una fila más en la matriz de embeddings (módulo 09) y una neurona más en la salida softmax.

> **Analogía con compresión.** BPE nació como un compresor (Gage, 1994): sustituye el par de bytes más frecuente por un símbolo nuevo y repite. Lo que en compresión se llama «diccionario» es aquí el vocabulario; «bits por byte» (sección 9.5) mide cuánto comprime.
""")

nb.md(r"""
Empezamos cargando el corpus Políglota y partiéndolo en entrenamiento (80 %) y prueba (20 %) por documento, para medir siempre con datos que el tokenizer no ha visto.
""")
_c = src_corpus_cells()
nb.code("# ── carga_corpus (1/3) ──\n" + _c[0])
nb.code("# ── carga_corpus (2/3) ──\n" + _c[1])
nb.code("# ── carga_corpus (3/3) ──\n" + _c[2])
nb.code(r'''
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs, source = corpus["docs"], corpus["source"]
train = {l: [d["text"] for i, d in enumerate([d for d in docs if d["lang"] == l]) if i % 5 != 0] for l in ("es", "en", "code")}
test = {l: [d["text"] for i, d in enumerate([d for d in docs if d["lang"] == l]) if i % 5 == 0] for l in ("es", "en", "code")}
nbytes = lambda ts: sum(len(t.encode("utf-8")) for t in ts)
print(f"source = {source!r}")
print(pd.DataFrame({"train (KB)": {l: nbytes(v) // 1000 for l, v in train.items()}, "test (KB)": {l: nbytes(v) // 1000 for l, v in test.items()}}))
''')

nb.code(r'''
# Cobertura: palabras (OOV) vs caracteres vs BPE. Un vocabulario de palabras de tamaño K cubre el texto de prueba… ¿en qué %?
tok_pal = lambda t: re.findall(r"\w+|[^\w\s]", t.lower())
filas = []
for l in ("es", "en", "code"):
    frec = Counter(w for t in train[l] for w in tok_pal(t))
    prueba = [w for t in test[l] for w in tok_pal(t)]
    for K in (100, 300, 1000, 3000):
        top = {w for w, _ in frec.most_common(K)}
        filas.append({"idioma": l, "K (palabras en el vocabulario)": K, "OOV %": 100 * np.mean([w not in top for w in prueba])})
df_oov = pd.DataFrame(filas)
fig, ax = plt.subplots(figsize=(7, 3.6))
for l, c in zip(("es", "en", "code"), (AZUL, NARANJA, VERDE)):
    d = df_oov[df_oov["idioma"] == l]; ax.plot(d["K (palabras en el vocabulario)"], d["OOV %"], "o-", color=c, label=l)
ax.set_xscale("log"); ax.set_xlabel("tamaño del vocabulario de palabras K"); ax.set_ylabel("% de palabras de prueba fuera del vocabulario")
ax.set_title(f"Un vocabulario de palabras siempre deja OOV (corpus {source})"); ax.legend(); plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""Las curvas bajan al crecer K pero **nunca llegan a 0** (con texto real, el «ruido» de nombres, números, errores y palabras raras es infinito): ahí un vocabulario de palabras necesita `<unk>`. BPE a nivel de bytes resuelve el problema de raíz: el vocabulario base son los 256 bytes y **cualquier** cadena es codificable. Con el corpus sintético las curvas caen más rápido que con Wikipedia real (generador repetitivo)."""))

nb.gemini(
    "imagen", "M02-IMG-01", "Pipeline de un tokenizer byte-level BPE",
    "El recorrido completo de un texto por un tokenizer estilo GPT-2: regex de pre-tokenización, bytes, aplicación de merges por rango, ids; y la dirección inversa (decode).",
    """Diagrama técnico limpio de un pipeline, fondo blanco, 16:9, flechas gruesas de izquierda a derecha. Paleta: azul #1F6FEB para texto y tokens, naranja #F28E2B para reglas y tablas de merges, verde #2CA02C para ids/resultado, gris #6B7280 para anotaciones. Tipografía sans-serif legible y monoespaciada para bytes, sin ilustraciones decorativas.
Composición: 5 cajas en fila con título arriba y contenido debajo. Textos EXACTOS:
1) «Texto»: «Hello, world!».
2) «Pre-tokenización (regex)»: cuatro cajitas azules «Hello», «,», « world», «!» con la nota «el espacio se queda pegado a la palabra siguiente».
3) «Bytes UTF-8»: bajo cada trozo sus bytes en hexadecimal: «48 65 6C 6C 6F», «2C», «20 77 6F 72 6C 64», «21».
4) «Merges por rango (menor rango primero)»: una pequeña tabla naranja con el título «tabla de merges (par → token nuevo)» y las filas «H e → He», «l l → ll», «He ll → Hell», «Hell o → Hello»; abajo, la leyenda «se aplica siempre el par aprendido antes» y la nota «ejemplo ilustrativo: no son los merges reales de GPT-2».
5) «Ids»: cuatro números verdes EXACTOS en este orden: «15496», «11», «995», «0» con la etiqueta «vocabulario GPT-2».
Debajo de las cajas, una flecha de derecha a izquierda de color gris etiquetada «decode: ids → bytes → texto (UTF-8)».
Título superior: «Byte-level BPE: de texto a ids».
Evita: números distintos de los indicados, tokens inventados, texto ilegible, flechas que se crucen, elementos decorativos.""",
    "Pipeline de byte-level BPE: texto, regex, bytes, merges por rango, ids y decodificación inversa",
    """"Hello, world!" → regex → [Hello][,][ world][!] → bytes 48 65 6C 6C 6F | 2C | 20 77 6F 72 6C 64 | 21
   → merges por rango: H e→He, l l→ll, He ll→Hell, Hell o→Hello
   → ids (GPT-2): 15496 | 11 | 995 | 0           ← decode: ids → bytes → UTF-8""",
)
nb.md(obs(r"""Sigue una cadena: el regex **parte primero**, los merges **solo se aplican dentro de cada trozo**. Los ids `15496, 11, 995, 0` son exactamente los que devuelve `tiktoken` con el vocabulario de GPT-2 (lo comprobarás en la sección 8). La flecha inversa (decode) es trivial: concatenar bytes."""))

nb.md(r"""
## 2. Historia y fuentes (qué es de quién)
| Año | Aporte | Fuente |
|---|---|---|
| 1994 | **Gage**: BPE como compresor de datos (sustituir el par de bytes más frecuente por un byte libre) | *A New Algorithm for Data Compression*, C Users Journal 12(2) |
| 2016 | **Sennrich, Haddow & Birch**: BPE para *segmentación en sub-palabras* en traducción neuronal; entrenan sobre un diccionario de palabras ponderado por frecuencia, sin cruzar fronteras de palabra, y fijan el nº de merges como único hiperparámetro | arXiv:1508.07909 |
| 2019 | **Wang, Cho & Gu**: BPE sobre **bytes** (BBPE): vocabulario base de 256, sin OOV | arXiv:1909.03341 |
| 2019 | **GPT-2** (Radford et al.): byte-level BPE + **regex de pre-tokenización** (no fusionar entre categorías de caracteres, salvo el espacio) y vocabulario de 50 257 | informe técnico de OpenAI |
| 2023 | `tiktoken` (OpenAI): implementación rápida; encodings `cl100k_base` y `o200k_base` | repositorio `openai/tiktoken` |
| 2024 | Llama 3 usa un vocabulario de 128 K: 100 K de `tiktoken` + 28 K tokens adicionales para idiomas no ingleses | Llama Team 2024, arXiv:2407.21783 |
""")

nb.md(r"""
## 3. Ejemplo resuelto a mano (el clásico de Sennrich)

Antes de la fórmula, ejecútalo a mano: la regla es *«cuenta los pares de símbolos adyacentes, fusiona el más frecuente, repite»*. Es el mismo espíritu que un compresor de diccionario (LZW): sustituir lo que se repite por un símbolo nuevo.

Corpus: «low» ×5, «lower» ×2, «newest» ×6, «widest» ×3. Cada palabra termina con un marcador `</w>` y empieza como secuencia de caracteres. (Es el diccionario del Algoritmo 1 de Sennrich et al., 2016.)

| Palabra | Frecuencia | Estado inicial |
|---|---|---|
| low | 5 | `l o w </w>` |
| lower | 2 | `l o w e r </w>` |
| newest | 6 | `n e w e s t </w>` |
| widest | 3 | `w i d e s t </w>` |

**Paso 1.** Pares y conteos: `e s` = 6 (newest) + 3 (widest) = **9**; `s t` = 9; `t </w>` = 9; `w e` = 2 + 6 = 8; `l o` = 5 + 2 = 7; `o w` = 7; … Hay un **empate a 9**. Convención del curso: **mayor conteo; ante empate, el par menor lexicográficamente** → fusionamos `e s` → `es`.
**Paso 2.** Ahora `es t` = 9 y `t </w>` = 9 → `es t` → `est`. **Paso 3.** `est </w>` = 9 → `est</w>`. **Paso 4.** `l o` = 7 = `o w` = 7 → `l o` → `lo`. **Paso 5.** `lo w` = 7 → `low`.

Tras 5 fusiones: `low </w>`×5, `low e r </w>`×2, `n e w est</w>`×6, `w i d est</w>`×3. Lo comprobamos con código.
""")

nb.code(r'''
def stats_pares(vocab):
    c = Counter()
    for w, f in vocab.items():
        for p in zip(w, w[1:]): c[p] += f
    return c

def fusiona_vocab(par, vocab):
    nuevo = {}
    for w, f in vocab.items():
        out, i = [], 0
        while i < len(w):
            if i < len(w) - 1 and (w[i], w[i + 1]) == par: out.append(w[i] + w[i + 1]); i += 2
            else: out.append(w[i]); i += 1
        nuevo[tuple(out)] = f
    return nuevo

vocab = {("l", "o", "w", "</w>"): 5, ("l", "o", "w", "e", "r", "</w>"): 2, ("n", "e", "w", "e", "s", "t", "</w>"): 6, ("w", "i", "d", "e", "s", "t", "</w>"): 3}
filas = []
for paso in range(1, 11):
    c = stats_pares(vocab)
    mejor = min(c.values(), key=lambda v: -v); empatados = sorted(p for p, v in c.items() if v == mejor)
    par = empatados[0]; vocab = fusiona_vocab(par, vocab)
    filas.append({"paso": paso, "par fusionado": " + ".join(par), "conteo": mejor, "empatados": len(empatados),
                  "estado": " | ".join(f"{' '.join(w)}×{f}" for w, f in vocab.items())})
pd.set_option("display.max_colwidth", 120)
display(pd.DataFrame(filas).set_index("paso"))
assert [f["par fusionado"] for f in filas[:5]] == ["e + s", "es + t", "est + </w>", "l + o", "lo + w"] and [f["conteo"] for f in filas[:5]] == [9, 9, 9, 7, 7]
''')

nb.gemini(
    "video", "M02-VID-01", "Animación: BPE fusiona el par más frecuente",
    "El proceso de merges del ejemplo clásico (low, lower, newest, widest), paso a paso, con la barra de conteos de pares y el vocabulario que crece. Es el proceso dinámico central del módulo.",
    """Video explicativo de 16:9, ritmo calmado, sin voz en off, con música ausente. Fondo blanco, estilo de diagrama técnico limpio, paleta: azul #1F6FEB para símbolos, naranja #F28E2B para el par que se fusiona, verde #2CA02C para el token nuevo, gris #6B7280 para anotaciones. Tipografía monoespaciada para los símbolos y sans-serif para los textos. Sin ilustraciones decorativas.
Guion por escenas (textos en pantalla EXACTOS):
0–4 s: Título «Byte Pair Encoding: fusionar el par más frecuente». Aparece una tabla de cuatro filas con la palabra, su frecuencia y su secuencia de símbolos: «low ×5 → l o w </w>», «lower ×2 → l o w e r </w>», «newest ×6 → n e w e s t </w>», «widest ×3 → w i d e s t </w>».
4–9 s: A la derecha aparece un gráfico de barras horizontales «Conteo de pares» con: «e s: 9», «s t: 9», «t </w>: 9», «w e: 8», «l o: 7», «o w: 7». Las tres barras de 9 parpadean en naranja con la nota «empate: se elige el menor lexicográficamente».
9–13 s: Paso 1. Las «e s» de las palabras newest y widest se resaltan en naranja y se funden en una sola caja verde «es». Texto: «Paso 1: e + s → es (9)».
13–16 s: Paso 2: «es + t → est (9)»; las cajas «es» y «t» se funden en «est».
16–19 s: Paso 3: «est + </w> → est</w> (9)».
19–22 s: Paso 4: «l + o → lo (7)».
22–25 s: Paso 5: «lo + w → low (7)».
25–30 s: Estado final en la tabla, EXACTO: «low </w> ×5», «low e r </w> ×2», «n e w est</w> ×6», «w i d est</w> ×3». Una lista lateral «Vocabulario aprendido» muestra en orden: «es», «est», «est</w>», «lo», «low». Texto final: «Cada fusión acorta el corpus y añade un token al vocabulario».
Evita: cambiar números o pares, texto ilegible, movimientos bruscos, elementos decorativos, mostrar pares distintos de los indicados.""",
    "Animación de 30 segundos con las cinco primeras fusiones de BPE sobre low, lower, newest y widest",
    """t=0   corpus:  low×5 | lower×2 | newest×6 | widest×3  (cada palabra = caracteres + </w>)
t=4   pares:   e s:9  s t:9  t </w>:9  w e:8  l o:7  o w:7     (empate a 9)
t=9   1) e+s→es   2) es+t→est   3) est+</w>→est</w>   4) l+o→lo   5) lo+w→low
t=25  final:   low </w>×5 | low e r </w>×2 | n e w est</w>×6 | w i d est</w>×3
       vocabulario aprendido: es, est, est</w>, lo, low""",
    duration="30 s",
)
nb.md(obs(r"""Fíjate en cómo cambian los conteos tras cada fusión: al fusionar `e s`, el par `s t` **desaparece** (ahora la `s` está dentro de `es`) y nace `es t` con el mismo conteo. Eso es lo que hace costoso el algoritmo ingenuo (recontar todo) y lo que explota el conteo incremental de la sección 6: solo cambian los pares **vecinos** de la fusión."""))

nb.md(r"""
## 4. El algoritmo, formalmente

Acabas de ver el algoritmo funcionar con 16 apariciones de 4 palabras; ahora lo escribimos en general.

Sea el corpus una secuencia (o un multiconjunto de «palabras» con frecuencia) sobre un alfabeto inicial $\Sigma_0$ (aquí, los 256 bytes). **Entrenamiento**, con $M$ fusiones:

$$\text{para } k=1,\dots,M:\quad (a_k,b_k)=\arg\max_{(a,b)}\ \text{count}(a,b);\qquad t_k := a_k b_k;\qquad \Sigma_k=\Sigma_{k-1}\cup\{t_k\}$$

y se reemplaza cada aparición adyacente de $(a_k,b_k)$ por $t_k$ en el corpus. Aquí $\text{count}(a,b)$ es el número de veces que $b$ sigue a $a$ en el corpus **actual**, ponderado por la frecuencia de cada palabra. El tamaño final del vocabulario es $|V|=256+M$ (más tokens especiales).

**Codificación** de un texto nuevo: se parte en trozos (pre-tokenización), cada trozo se convierte a bytes y se aplican las fusiones **en el orden en que se aprendieron**: en cada paso se fusiona el par adyacente cuyo token resultante tiene **menor rango** $k$, hasta que no queda ninguno. El **orden de los merges es parte del tokenizer**: dos listas con las mismas fusiones en distinto orden son tokenizers distintos.

**¿Qué optimiza?** Cada fusión de $(a,b)$ reduce la longitud del corpus en (≈) $\text{count}(a,b)$ tokens, así que BPE es un **algoritmo voraz de compresión**. Formalizar *qué* problema resuelve costó casi 30 años: Zouhar et al. (2023) lo plantean como un problema de optimización combinatoria y prueban que la versión voraz es una aproximación de factor $\tfrac{1}{\sigma}(1-e^{-\sigma})$ (≈ 0.37 como cota empírica) del óptimo; Kozma & Voderholzer (2024) demuestran que encontrar la secuencia óptima de $M$ fusiones es **APX-completo** y que BPE garantiza entre 0.333 y 0.625 del óptimo en el peor caso.

> ⚠️ **Más compresión ≠ mejor modelo.** Schmidt et al. (2024) no encuentran que menos tokens implique mejor rendimiento downstream; la pre-tokenización pesa más de lo que se pensaba. Y Bostrom & Durrett (2020) encuentran que Unigram LM (módulo 03) iguala o supera a BPE al preentrenar. BPE es *estándar*, no *óptimo*.
""")

nb.md(r"""
## 5. De caracteres a **bytes** y la pre-tokenización con regex

### 5.1 Byte-level
Si el alfabeto inicial son los **256 bytes**, no hay desconocidos: cualquier texto (cualquier idioma, emoji, bytes inválidos) es una secuencia de bytes. El módulo 01 mostró lo que cuesta cada idioma en bytes; BPE reduce ese costo para lo frecuente.

**El truco de GPT-2 (`bytes_to_unicode`).** El código original de GPT-2 trabaja con *cadenas*, así que mapea cada byte a un carácter Unicode «imprimible» (los bytes imprimibles se mapean a sí mismos y el resto a `U+0100…`). Por eso verás `Ġ` (espacio) y `Ċ` (salto de línea) en los vocabularios de Hugging Face; es solo una *representación* de los bytes. Lo necesitaremos para HF `tokenizers`.
""")
nb.code(r'''
def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs, n = bs[:], 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, map(chr, cs)))
B2U = bytes_to_unicode()
a_str = lambda b: "".join(B2U[x] for x in b)
print("espacio →", repr(B2U[0x20]), "| salto de línea →", repr(B2U[0x0A]), "| 'a' →", repr(B2U[0x61]), "| byte 0xC3 →", repr(B2U[0xC3]), "| distintos:", len(set(B2U.values())))
print("'¿qué?' como bytes de GPT-2:", a_str("¿qué?".encode()))
''')

nb.md(r"""
### 5.2 Por qué hace falta un regex
Si dejas a BPE operar sobre todo el texto, aprende fusiones **entre** palabra y puntuación («dog», «dog.», «dog!», «dog,»… como tokens distintos) y entre palabras, y desperdicia vocabulario. GPT-2 (Radford et al., 2019, sec. 2.2) evita fusionar entre **categorías de caracteres** (letras, números, puntuación), con una excepción para el **espacio**, que se mantiene pegado a la palabra siguiente porque eso comprime mucho mejor. Se implementa **partiendo antes** el texto con una expresión regular; las fusiones solo ocurren *dentro* de cada trozo. Además, entrenar sobre trozos únicos con frecuencia (como en Sennrich) acelera todo.

### 5.3 Tres generaciones de regex (copiados de `tiktoken` 0.14.0)
* **GPT-2 (`r50k`)**: contracciones (`'s`, `'t`…), ` ?\p{L}+` (palabra con espacio previo), ` ?\p{N}+` (**números de cualquier longitud**), ` ?[^\s\p{L}\p{N}]+` (símbolos), y reglas para espacios.
* **cl100k (GPT-3.5/4)**: contracciones **sin distinguir mayúsculas**; la letra puede ir precedida de **un carácter no alfanumérico** (`[^\r\n\p{L}\p{N}]?+\p{L}++`, de ahí `_var` o `¡Hola`); **números en grupos de 1 a 3 dígitos** (`\p{N}{1,3}`); los símbolos absorben saltos de línea finales.
* **o200k (GPT-4o y posteriores)**: palabras con **clases de mayúsculas/minúsculas** (`camelCase` se parte en `camel` + `Case`), contracciones pegadas a la palabra, dígitos 1–3, y símbolos con `[\r\n/]*`.
""")
nb.code(SRC_PATTERNS)
nb.code(r'''
import tiktoken, tiktoken_ext.openai_public as op
assert PAT_GPT2 == op.r50k_pat_str                      # el que trae tu versión de tiktoken
try:
    for nombre, pat in (("cl100k_base", PAT_CL100K), ("o200k_base", PAT_O200K)):
        assert tiktoken.get_encoding(nombre)._pat_str == pat, nombre
    print("✔ patrones cl100k y o200k idénticos a los de tiktoken instalado")
except Exception as e:
    print(f"(no pude descargar cl100k/o200k para contrastar: {type(e).__name__}; los patrones son los de tiktoken 0.14.0)")

ORIG = r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""   # GPT-2 original (sin cuantificadores posesivos)
texto = "\n".join(d["text"] for d in docs[:60]) + "  ¡Hola!  \n\n\tx=1  "
assert regex.findall(ORIG, texto) == regex.findall(PAT_GPT2, texto)
print("✔ el regex original de GPT-2 y r50k_pat_str trocean igual (tiktoken lo dice en un comentario: «equivalent, but faster»)")
''')
nb.code(r'''
muestras = ["Don't pay $1234567 for camelCase_var, OK?", "¡Hola, MundoGrande! Año 2026: 3.14159", "def f(x):\n    return x  \n\n\tif y:"]
filas = []
for m in muestras:
    for nombre in ("gpt2", "cl100k", "o200k"):
        filas.append({"texto": m.replace("\n", "⏎").replace("\t", "⇥")[:34], "regex": nombre, "trozos": " | ".join(t.replace("\n", "⏎").replace("\t", "⇥") for t in regex.findall(PATRONES[nombre], m))})
pd.set_option("display.max_colwidth", 200); display(pd.DataFrame(filas).set_index(["texto", "regex"]))
''')
nb.gemini(
    "imagen", "M02-IMG-02", "Cómo trocean GPT-2, cl100k y o200k la misma frase",
    "Una comparación visual de los trozos que producen los tres regex de pre-tokenización sobre dos frases, resaltando las diferencias clave: dígitos, camelCase, espacios y puntuación.",
    """Diagrama técnico limpio, fondo blanco, 16:9. Paleta: azul #1F6FEB, naranja #F28E2B, verde #2CA02C, gris #6B7280. Tipografía monoespaciada para los trozos, sans-serif para títulos. Sin ilustraciones decorativas.
Composición: una tabla con 3 filas (una por regex) y 2 bloques, uno por frase. Cada trozo es una cajita con borde fino; el carácter espacio se representa con el símbolo «␣» dentro de la cajita; el salto de línea con «⏎». Los textos son EXACTOS.
Frase A (título del bloque): «Don't pay $1234567 for camelCase_var».
Fila «GPT-2»: «Don» | «'t» | «␣pay» | «␣$» | «1234567» | «␣for» | «␣camelCase» | «_» | «var».
Fila «cl100k»: «Don» | «'t» | «␣pay» | «␣$» | «123» | «456» | «7» | «␣for» | «␣camelCase» | «_var».
Fila «o200k»: «Don't» | «␣pay» | «␣$» | «123» | «456» | «7» | «␣for» | «␣camel» | «Case» | «_var».
Frase B (título del bloque): «¡Hola, MundoGrande! Año 2026».
Fila «GPT-2»: «¡» | «Hola» | «,» | «␣MundoGrande» | «!» | «␣Año» | «␣2026».
Fila «cl100k»: «¡Hola» | «,» | «␣MundoGrande» | «!» | «␣Año» | «␣» | «202» | «6».
Fila «o200k»: «¡Hola» | «,» | «␣Mundo» | «Grande» | «!» | «␣Año» | «␣» | «202» | «6».
Resalta en naranja las cajitas que difieren entre filas de un mismo bloque. Título superior: «Mismo texto, tres pre-tokenizadores». Nota inferior en gris: «cl100k y o200k parten los números en grupos de hasta 3 dígitos; o200k parte camelCase».
Evita: cambiar los trozos, texto ilegible, más o menos cajitas de las indicadas, decoración.""",
    "Tabla de trozos de tres regex de pre-tokenización sobre dos frases con las diferencias resaltadas",
    """Don't pay $1234567 for camelCase_var
 GPT-2 : Don|'t|␣pay|␣$|1234567|␣for|␣camelCase|_|var
 cl100k: Don|'t|␣pay|␣$|123|456|7|␣for|␣camelCase|_var
 o200k : Don't|␣pay|␣$|123|456|7|␣for|␣camel|Case|_var
¡Hola, MundoGrande! Año 2026
 GPT-2 : ¡|Hola|,|␣MundoGrande|!|␣Año|␣2026
 cl100k: ¡Hola|,|␣MundoGrande|!|␣Año|␣|202|6
 o200k : ¡Hola|,|␣Mundo|Grande|!|␣Año|␣|202|6""",
)
nb.md(obs(r"""Tres diferencias con consecuencias reales: (1) los **números**: GPT-2 los deja enteros (`1234567` es un único trozo, a veces un único token) y cl100k/o200k los parten **de izquierda a derecha en grupos de 3**, de modo que la alineación de los dígitos depende de dónde empieza el número (Singh & Strouse, 2024, estudian el efecto en aritmética); (2) **camelCase** solo se parte en o200k; (3) el **espacio** de `␣2026` se separa del número en cl100k/o200k (`␣` + `202` + `6`)."""))

nb.md(r"""
## 6. Entrenamiento: del ingenuo al incremental

**Ingenuo** (Algoritmo 1 de Sennrich): en cada iteración recorre todo el corpus, recuenta todos los pares y fusiona. Coste $O(M\cdot U)$ con $U$ = nº de símbolos del corpus de palabras únicas. **Incremental** (lo que Sennrich et al. llaman «indexar todos los pares y actualizar las estructuras incrementalmente»): se mantienen **(1)** un contador de pares, **(2)** un **índice invertido** par → palabras donde aparece y **(3)** un **heap** con los conteos (con invalidación perezosa de entradas obsoletas). Fusionar un par solo toca las palabras de su lista, y por cada fusión actualiza los conteos de los pares **vecinos** (los que se destruyen y los que nacen).
""")
nb.gemini(
    "imagen", "M02-IMG-03", "Estructuras del entrenamiento incremental de BPE",
    "Las tres estructuras (palabras, contador de pares con heap, índice invertido) y qué se actualiza al fusionar el par «e s»; sirve para entender el código de `entrena_incremental` antes de leerlo.",
    """Diagrama técnico limpio, fondo blanco, 16:9. Paleta: azul #1F6FEB para palabras, naranja #F28E2B para el contador/heap, verde #2CA02C para el índice invertido, gris #6B7280 para anotaciones. Tipografía monoespaciada para los datos, sans-serif para títulos. Sin ilustraciones decorativas.
Composición: tres columnas con título arriba y una flecha etiquetada «fusionar (e, s)» que cruza de izquierda a derecha.
Columna 1, título «Palabras (únicas, con frecuencia)»: dos filas EXACTAS «n e w e s t </w> ×6» y «w i d e s t </w> ×3». Debajo, la misma columna después de fusionar: «n e w es t </w> ×6» y «w i d es t </w> ×3» con «es» resaltado en verde.
Columna 2, título «Contador de pares (+ heap)»: lista EXACTA antes: «(e,s): 9», «(s,t): 9», «(t,</w>): 9», «(w,e): 6», «(d,e): 3». Debajo, después de fusionar: «(e,s): 0 → se elimina», «(s,t): 0», «(es,t): 9 ← nuevo», «(w,es): 6 ← nuevo», «(d,es): 3 ← nuevo», «(w,e): 0», «(d,e): 0». Una nota: «solo cambian los pares vecinos del par fusionado».
Columna 3, título «Índice invertido (par → palabras)»: antes «(e,s) → {newest, widest}»; después «(es,t) → {newest, widest}», «(w,es) → {newest}», «(d,es) → {widest}».
Título superior: «Entrenamiento incremental de BPE». Nota inferior en gris: «cada merge toca solo las palabras de la lista del par».
Evita: cambiar los números, añadir estructuras no indicadas, texto ilegible, decoración.""",
    "Tres columnas: palabras, contador de pares con heap e índice invertido antes y después de fusionar e+s",
    """PALABRAS            CONTADOR DE PARES            ÍNDICE INVERTIDO
n e w e s t ×6      (e,s):9 (s,t):9 (t,</w>):9    (e,s)→{newest,widest}
w i d e s t ×3      (w,e):6 (d,e):3
   ── fusionar (e,s) ──────────────────────────────►
n e w es t ×6       (es,t):9 nuevo (w,es):6 nuevo  (es,t)→{newest,widest}
w i d es t ×3       (d,es):3 nuevo; (e,s),(w,e),(d,e)→0   (w,es)→{newest} (d,es)→{widest}""",
)
nb.md(obs(r"""Mira la columna central: al fusionar `(e,s)` **no** hay que recontar el corpus; basta restar los pares viejos que rodeaban a la fusión y sumar los nuevos. Cuando el mismo par vecino aparece en muchas palabras, el índice invertido evita tocar las que no lo contienen."""))

nb.code(SRC_TRAIN)
nb.code(SRC_TRAIN_INC)

nb.md(r"""
**Convención de desempates.** Cuando dos pares tienen el mismo conteo hay que elegir uno, y **el vocabulario resultante cambia**. Aquí: mayor conteo y, ante empate, el **par menor** (`(id_a, id_b)` lexicográfico) → determinista y reproducible. `tiktoken._educational` y `minbpe` usan *«el primero que aparece»* (`max(stats, key=stats.get)`); HF `tokenizers` usa otra regla interna. Lo verificamos en la sección 8.

**Verificación 1: el incremental produce *exactamente* los mismos merges que el ingenuo** (misma regla de desempate), y es mucho más rápido.
""")
nb.code(r'''
wc = contar_palabras(train["es"] + train["en"] + train["code"])
print(f"palabras únicas: {len(wc):,} | símbolos totales (bytes): {sum(len(w) * f for w, f in wc.items()):,}")
tiempos = []
for M in ((50, 100, 200, 400) if FAST_DEV_RUN else (100, 300, 600, 1000)):
    t0 = time.time(); m1 = entrena_ingenuo(wc, M); t1 = time.time() - t0
    t0 = time.time(); m2 = entrena_incremental(wc, M); t2 = time.time() - t0
    assert m1 == m2, "el incremental debe coincidir con el ingenuo"
    tiempos.append((M, t1, t2))
df_t = pd.DataFrame(tiempos, columns=["merges", "ingenuo (s)", "incremental (s)"]).set_index("merges"); df_t["aceleración ×"] = df_t["ingenuo (s)"] / df_t["incremental (s)"]
display(df_t.round(3))
ax = df_t[["ingenuo (s)", "incremental (s)"]].plot(logy=True, marker="o", color=[NARANJA, AZUL], figsize=(6.5, 3.6))
ax.set_ylabel("segundos (escala log)"); ax.set_title("Tiempo de entrenamiento vs nº de merges"); plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""Las dos curvas **dan los mismos merges** (la aserción lo comprueba) pero el ingenuo crece con $M\times U$ y el incremental casi no se nota. Con corpus reales de GB, el ingenuo es inviable; por eso existen implementaciones en Rust (`tokenizers`, `tiktoken`) y trabajos que mejoran la complejidad de la **codificación** de $O(NM)$ a $O(N\log M)$ (Zouhar et al., 2023)."""))

nb.md(r"""
## 7. El tokenizer: `encode`, `decode`, especiales y orden de merges
`BPETokenizer` guarda `vocab` (id → bytes) y `merges` ((id_a, id_b) → id nuevo). El **id nuevo es la prioridad**: al codificar, en cada paso se fusiona el par adyacente de **menor** id resultante. Los ids 0–255 son los bytes; los tokens especiales (como `<|endoftext|>`) viven **fuera** del BPE y se insertan con `allowed_special`.
""")
nb.code(SRC_TOKENIZER)
nb.code(r'''
tok = BPETokenizer.train(train["es"] + train["en"] + train["code"], VOCAB)
tok.special = {"<|endoftext|>": len(tok.vocab)}
print(f"vocabulario: {len(tok.vocab)} tokens (+{len(tok.special)} especial) | merges: {len(tok.merges)}")
mostrar = lambda ids: [tok.vocab[i].decode("utf-8", "backslashreplace") if i in tok.vocab else "<ESP>" for i in ids]
print("primeros 12 merges :", [tok.vocab[i] for i in range(256, 268)])
print("últimos 8 merges   :", [tok.vocab[i] for i in range(len(tok.vocab) - 8, len(tok.vocab))])
for s in ["La caché del servidor", "The cache of the server", "def configurar_cache(x):", "Año 2026 😀"]:
    ids = tok.encode(s); print(f"{s!r:34} → {len(ids):2d} tokens {mostrar(ids)}")
    assert tok.decode(ids) == s
ids = tok.encode("hola<|endoftext|>mundo", allowed_special={"<|endoftext|>"}); print(ids[-4:], repr(tok.decode(ids)))
''')
nb.code(r'''
from IPython.display import HTML, display
def visualiza(texto, tk=None):
    tk = tk or tok; colores = ["#cfe2ff", "#ffe5c2", "#d4edda", "#e2d9f3"]; partes = []
    for k, i in enumerate(tk.encode(texto)):
        pieza = tk.vocab[i].decode("utf-8", "replace").replace(" ", "␣").replace("\n", "⏎")
        partes.append(f'<span style="background:{colores[k % 4]};padding:1px 2px;margin:1px;border-radius:3px;font-family:monospace">{pieza}</span>')
    display(HTML("".join(partes)))
for s in ("La configuración de la caché del servidor.", "The server cache configuration.", "def configure_cache(x): return x + 1", "Ñandú 😀"):
    visualiza(s)
''')
nb.md(obs(r"""Compara el **español** con el **inglés**: con un vocabulario pequeño aprendido sobre el corpus mixto, las palabras frecuentes de cada idioma son un solo token y las raras se parten. En «Ñandú 😀» verás **piezas de un byte** (`\xc3`, `\x91`…) que no son caracteres válidos por sí solas: un token puede ser *medio carácter* UTF-8."""))

nb.code(r'''
# Un token puede terminar a mitad de un carácter: decodificar token a token produce basura; hay que decodificar los BYTES acumulados
ids = tok.encode("Ñandú 😀")
por_token = [tok.vocab[i].decode("utf-8", "replace") for i in ids]
print("decodificar cada token por separado:", por_token)
print("decodificar todos los bytes juntos :", tok.decode(ids))
import codecs
dec = codecs.getincrementaldecoder("utf-8")(); print("decodificador incremental        :", [dec.decode(tok.vocab[i]) for i in ids])
''')

nb.md(r"""
## 8. Verificación contra las librerías de industria
Una implementación «que se ve bien» no vale: la **verificamos** contra lo que usa la industria. Cuatro comprobaciones:

1. **tiktoken**: construimos un `tiktoken.Encoding` con *mis* merges (`mergeable_ranks = {bytes: id}`) y comparamos los ids de `encode` en una muestra variada (español, inglés, código, emojis, espacios raros).
2. **Hugging Face `tokenizers`**: cargamos mis merges en un modelo `BPE` con pre-tokenizer `Split(regex) + ByteLevel` y comparamos.
3. **Entrenamiento**: mi entrenador con desempate «primer visto» debe igualar a `tiktoken._educational.bpe_train`; y el entrenador de HF diverge en un desempate que podemos identificar.
4. **Vocabulario real de GPT-2** (50 257 tokens): recuperamos sus merges desde `tiktoken` y comprobamos que **mi** `encode` reproduce exactamente a `tiktoken` sobre texto multilingüe.
""")
nb.code(SRC_TIKTOKEN_BRIDGE)
nb.code(r'''
muestra = [d["text"] for d in docs[::13]][:25] + ["Hola, ¿cómo estás? 😀 你好\n\n  x", "naïve café 123456 ", "   ", "a\tb\r\nc  ", "don't DON'T", "x=3.14159;y=-42", ""]
enc_mio = a_tiktoken(tok)
n_ok = sum(tok.encode(t) == enc_mio.encode(t) for t in muestra)
print(f"tiktoken(mis merges) vs mi encode: {n_ok}/{len(muestra)} textos idénticos | decode ida y vuelta:", all(enc_mio.decode(enc_mio.encode(t)) == t for t in muestra))
assert n_ok == len(muestra)

# HF tokenizers con mis merges (ByteLevel usa el alfabeto bytes_to_unicode)
from tokenizers import Tokenizer, models, pre_tokenizers, decoders, trainers, Regex
GPT2_ORIG = r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
def hf_desde_mio(tk, pat=GPT2_ORIG):
    vocab = {a_str(tk.vocab[i]): i for i in sorted(tk.vocab)}
    merges = [(a_str(tk.vocab[a]), a_str(tk.vocab[b])) for (a, b), _ in sorted(tk.merges.items(), key=lambda kv: kv[1])]
    hf = Tokenizer(models.BPE(vocab=vocab, merges=merges))
    hf.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(pat), behavior="isolated"), pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)])
    hf.decoder = decoders.ByteLevel(); return hf
hf = hf_desde_mio(tok)
n_ok = sum(tok.encode(t) == hf.encode(t).ids for t in muestra)
print(f"HF tokenizers(mis merges) vs mi encode: {n_ok}/{len(muestra)} idénticos | decode:", all(hf.decode(hf.encode(t).ids) == t for t in muestra))
assert n_ok == len(muestra)
''')
nb.code(r'''
# Entrenamiento: (a) tiktoken._educational  (b) HF BpeTrainer
texto_corto = "\n".join(train["es"] + train["en"] + train["code"])[:50_000]; V = 360
wc_c = contar_palabras([texto_corto])
mio_first = entrena_ingenuo(wc_c, V - 256, tie="first")
try:
    from tiktoken._educational import bpe_train
    ranks_edu = bpe_train(data=texto_corto, vocab_size=V, pat_str=PAT_GPT2, visualise=None)
    bytes_edu = [b for b, r in sorted(ranks_edu.items(), key=lambda kv: kv[1])][256:]
    vocab_b = {i: bytes([i]) for i in range(256)}
    for k, (a, b) in enumerate(mio_first): vocab_b[256 + k] = vocab_b[a] + vocab_b[b]
    print("mi entrenador (desempate «primer visto») == tiktoken._educational:", [vocab_b[256 + k] for k in range(len(mio_first))] == bytes_edu)
except Exception as e:
    print("tiktoken._educational no disponible:", type(e).__name__)

mio_lex = BPETokenizer.train([texto_corto], V)
hf_tr = Tokenizer(models.BPE()); hf_tr.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(GPT2_ORIG), behavior="isolated"), pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)])
hf_tr.train_from_iterator([texto_corto], trainers.BpeTrainer(vocab_size=V, initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), special_tokens=[], show_progress=False))
import json
m_hf = [tuple(m) if isinstance(m, list) else tuple(m.split(" ")) for m in json.loads(hf_tr.to_str())["model"]["merges"]]
m_mio = [(a_str(mio_lex.vocab[a]), a_str(mio_lex.vocab[b])) for (a, b), _ in sorted(mio_lex.merges.items(), key=lambda kv: kv[1])]
k = next((i for i, (x, y) in enumerate(zip(m_hf, m_mio)) if x != y), None)
print(f"HF BpeTrainer vs mi entrenador (desempate lexicográfico): coinciden los primeros {k} de {len(m_mio)} merges" if k is not None else "idénticos")
if k is not None:
    print("  HF  elige :", m_hf[k], "| yo elijo:", m_mio[k], "(¿mismo conteo? ver siguiente celda)")
''')
nb.code(r'''
# ¿Es un desempate? Cuenta los dos pares candidatos sobre el corpus tras aplicar los k merges comunes
if k is not None:
    U2B = {v: k_ for k_, v in B2U.items()}; a_bytes = lambda s: bytes(U2B[c] for c in s)
    tok_k = BPETokenizer(PAT_GPT2, mio_lex.vocab, mio_lex.merges)
    def cuenta(par_hf):
        ca, cb = a_bytes(par_hf[0]), a_bytes(par_hf[1]); n = 0
        for w, f in wc_c.items():
            ids = [tok_k.byte2id[bytes([b])] for b in w]
            while len(ids) > 1:
                cand = [(tok_k.merges.get(p, 1 << 60), p) for p in zip(ids, ids[1:])]; r, p = min(cand)
                if r == 1 << 60 or r >= 256 + k: break
                ids = fusiona_palabra(ids, p, r)
            n += f * sum(1 for x, y in zip(ids, ids[1:]) if tok_k.vocab[x] == ca and tok_k.vocab[y] == cb)
        return n
    print("conteo del par que elige HF:", cuenta(m_hf[k]), "| conteo del par que elijo yo:", cuenta(m_mio[k]))
''')
nb.md(obs(r"""1. Con **mis merges**, `tiktoken` y `tokenizers` producen **exactamente** los mismos ids que mi `encode`: la parte de *codificación* (regex + orden de merges + bytes) está bien implementada.
2. Mi entrenador, con el desempate «primer visto», **reproduce a `tiktoken._educational`** token a token.
3. El entrenador de HF **diverge** de mi desempate lexicográfico en un punto en el que los dos candidatos tienen **el mismo conteo** (la celda de arriba lo cuenta): no hay un «BPE correcto» único; **la regla de desempate forma parte de la definición del tokenizer**. Lo que importa en producción es que el tokenizer entrenado se guarda y se aplica siempre igual."""))

nb.md(r"""
### 8.4 Contra el vocabulario real de GPT-2
Obtenemos el encoding `gpt2` de `tiktoken` (o el espejo verificado por SHA-256 si el CDN está bloqueado), **recuperamos sus merges** con la receta de `minbpe` (volver a fusionar cada token con `max_rank` = su rango: el resultado son siempre exactamente dos piezas) y cargamos todo en **mi** `BPETokenizer`. Los ids deben coincidir con los de `tiktoken` (los ids de GPT-2 son sus rangos).
""")
nb.code(SRC_GPT2)
nb.code(r'''
gpt2 = get_gpt2_encoding()
if gpt2 is None:
    print("GPT-2 no disponible: se omite esta verificación")
else:
    t0 = time.time(); mio_gpt2 = desde_tiktoken(gpt2); print(f"merges de GPT-2 recuperados: {len(mio_gpt2.merges):,} en {time.time() - t0:.1f} s | n_vocab = {gpt2.n_vocab:,} (= 256 + {len(mio_gpt2.merges):,} merges + 1 especial)")
    textos = ["Hello, world!", "Tokenizers turn text into numbers.", "Los tokenizadores convierten texto en números.", "def añadir_ñu(x): return x+1", "Año 2026: 😀 你好 мир",
              "   espacios   y\n\nsaltos\t\ttabs  ", "supercalifragilisticexpialidocious", "1234567890 3.14159 -42"] + [d["text"][:400] for d in docs[::40]]
    ok = [mio_gpt2.encode(t) == gpt2.encode(t) for t in textos]
    print(f"mi encode vs tiktoken en GPT-2 real: {sum(ok)}/{len(ok)} textos idénticos")
    print("Hello, world! →", mio_gpt2.encode("Hello, world!"), "(el de la figura M02-IMG-01: [15496, 11, 995, 0])")
    assert all(ok) and mio_gpt2.encode("Hello, world!") == [15496, 11, 995, 0]
''')
nb.code(r'''
# Velocidad: mi Python vs HF tokenizers (Rust) vs tiktoken (Rust) sobre el mismo texto
grande = "\n".join(docs_t["text"] for docs_t in docs)[:300_000]
res_v = {}
for nombre, f in (("mi BPE (Python)", lambda: tok.encode(grande)), ("HF tokenizers", lambda: hf.encode(grande).ids), ("tiktoken", lambda: enc_mio.encode(grande))):
    t0 = time.time(); ids = f(); res_v[nombre] = len(grande.encode()) / (time.time() - t0) / 1e6
fig, ax = plt.subplots(figsize=(6.2, 3.3)); ax.barh(list(res_v), list(res_v.values()), color=[GRIS, NARANJA, AZUL]); ax.set_xscale("log")
ax.set_xlabel("MB/s de texto (escala log; una CPU compartida, un solo hilo)"); ax.set_title("Codificar con el mismo vocabulario"); plt.tight_layout(); plt.show()
print({k: f"{v:.2f} MB/s" for k, v in res_v.items()})
''')
nb.md(obs(r"""Mismo vocabulario, mismas salidas, **velocidades distintas**. En esta medición (CPU compartida, un hilo, texto sintético muy repetitivo) `tiktoken` es el más rápido con diferencia; mi Python puro se ayuda de su caché de trozos repetidos; y la llamada `encode` de HF `tokenizers` **no** es la más rápida porque construye objetos con offsets y máscaras (se usa `encode_batch`, en paralelo, en producción). No saques conclusiones finas de este número: depende de la máquina, del texto y de la API usada. El README de `tiktoken` afirma 3–6× frente a un tokenizer de código abierto comparable (GPT-2 de HF con `tokenizers==0.13.2`), medido sobre 1 GB de texto."""))

nb.md(r"""
## 9. Experimentos
### 9.1 Tamaño del vocabulario: un entrenamiento, todos los vocabularios
Propiedad útil: el vocabulario de tamaño $V'<V$ de un BPE es **el prefijo** de sus merges. Entrenamos una vez y evaluamos `encode(max_id=…)` con los primeros $k$ merges. Métrica: **bytes por token** en el conjunto de prueba (más alto = mejor compresión; el inverso de la «fertilidad por byte»).
""")
nb.code(r'''
def trozos_prueba(textos, pat=PAT_GPT2):
    pat = regex.compile(pat); return Counter(t for x in textos for t in pat.findall(x))

def bytes_por_token(tk, trozos, max_id=None):
    nb_, nt = 0, 0
    for t, f in trozos.items():
        nb_ += f * len(t.encode("utf-8")); nt += f * len(tk._encode_trozo(t, max_id))
    return nb_ / nt

tp = {l: trozos_prueba(test[l]) for l in test}
Vs = sorted({256, 300, 400, 600, 800, VOCAB})
df_v = pd.DataFrame({l: [bytes_por_token(tok, tp[l], max_id=v) for v in Vs] for l in test}, index=Vs)
ax = df_v.plot(marker="o", color=[AZUL, NARANJA, VERDE], figsize=(7, 3.8)); ax.set_xlabel("tamaño del vocabulario"); ax.set_ylabel("bytes por token (prueba)")
ax.set_title(f"Compresión vs vocabulario (un solo entrenamiento, corpus {source})"); plt.tight_layout(); plt.show(); display(df_v.round(2))
''')
nb.md(obs(r"""La curva **sube rápido y se aplana**: las primeras fusiones (pares muy frecuentes) comprimen mucho; las últimas apenas. Con $V=256$ (solo bytes) el ratio es exactamente 1.0 bytes/token. Elegir el tamaño de vocabulario es leer dónde la curva deja de compensar el costo de más filas en la matriz de embeddings (módulo 04)."""))

nb.md("### 9.2 Distribución de los tokens (ley de Zipf)")
nb.code(r'''
usos = Counter(); idx_total = 0
for t, f in tp["es"].items():
    for i in tok._encode_trozo(t): usos[i] += f
for t, f in tp["en"].items():
    for i in tok._encode_trozo(t): usos[i] += f
frec = np.array(sorted(usos.values(), reverse=True)); n_vocab = len(tok.vocab)
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6))
axs[0].loglog(np.arange(1, len(frec) + 1), frec, color=AZUL); axs[0].set_xlabel("rango del token"); axs[0].set_ylabel("apariciones (ES+EN, prueba)"); axs[0].set_title("Frecuencia de tokens (log-log)")
acum = np.cumsum(frec) / frec.sum(); axs[1].plot(np.arange(1, len(frec) + 1), acum, color=NARANJA); axs[1].set_xlabel("nº de tokens más frecuentes"); axs[1].set_ylabel("fracción acumulada del texto"); axs[1].set_title("Cobertura acumulada")
plt.tight_layout(); plt.show()
print(f"tokens del vocabulario que NUNCA aparecen en la prueba ES+EN: {n_vocab - len(usos)} de {n_vocab} ({100 * (n_vocab - len(usos)) / n_vocab:.1f} %) | los 100 más frecuentes cubren {100 * acum[99]:.1f} % del texto")
''')
nb.md(obs(r"""La frecuencia sigue (aproximadamente) una **ley de potencias**: unos pocos tokens cubren casi todo el texto y una **cola larga** casi no se usa. Los tokens con muy pocas apariciones tienen embeddings mal entrenados; con vocabularios enormes y datos distintos del entrenamiento del tokenizer aparecen los *tokens sub-entrenados* que verás en el módulo 05."""))

nb.md(r"""
### 9.3 El «impuesto» de idioma: entrenar con un idioma y evaluar en otro
Entrenamos cuatro tokenizers con el **mismo** tamaño de vocabulario —solo inglés, solo español, solo código y la mezcla— y medimos los bytes por token en cada conjunto de prueba.
""")
nb.code(r'''
conjuntos = {"solo EN": train["en"], "solo ES": train["es"], "solo código": train["code"], "mezcla": train["es"] + train["en"] + train["code"]}
tks = {n: BPETokenizer.train(ts, VOCAB) for n, ts in conjuntos.items()}
M = pd.DataFrame({l: {n: bytes_por_token(tk_, tp[l]) for n, tk_ in tks.items()} for l in ("en", "es", "code")})
M.columns = ["prueba EN", "prueba ES", "prueba código"]
import seaborn as sns
fig, ax = plt.subplots(figsize=(6.4, 3.6)); sns.heatmap(M, annot=True, fmt=".2f", cmap="Blues", cbar_kws={"label": "bytes por token"}, ax=ax)
ax.set_title(f"Tokenizer entrenado en… (filas) y evaluado en… (columnas)"); ax.set_ylabel("")
plt.tight_layout(); plt.show()
print("coste relativo de usar el tokenizer solo-EN en español:", round(M.loc["solo ES", "prueba ES"] / M.loc["solo EN", "prueba ES"], 2), "× más tokens")
''')
nb.md(obs(r"""La **diagonal** es lo mejor de cada columna: cada tokenizer comprime bien *su* idioma. Fuera de la diagonal, el mismo texto cuesta **mucho más tokens** (la última línea lo cuantifica): ese es el «impuesto de tokens» que documentan Petrov et al. (2023) y Ahia et al. (2023) en tokenizers comerciales, y la razón de que Llama 3 añadiera 28 K tokens de idiomas no ingleses a los 100 K de `tiktoken`. La **mezcla** pierde algo en cada idioma respecto al especialista pero es el compromiso razonable. (Con el corpus sintético la diferencia se exagera porque cada idioma tiene un vocabulario muy limitado.)"""))

nb.md("### 9.4 El regex importa: ablación de la pre-tokenización")
nb.code(r'''
def clase(c): return "L" if c.isalpha() else "N" if c.isdigit() else "P"
def mezcla(b):                       # ¿el token mezcla letras, números y/o símbolos (ignorando un espacio inicial)?
    s = b.decode("utf-8", "ignore").lstrip(" "); return len({clase(c) for c in s if not c.isspace()}) > 1

todo = train["es"] + train["en"] + train["code"]; filas = []
for nombre, pat in PATRONES.items():
    tk_ = BPETokenizer.train(todo, VOCAB, pat_str=pat); tpp = {l: trozos_prueba(test[l], pat) for l in test}
    filas.append({"pre-tokenizador": nombre, "bytes/token (ES)": bytes_por_token(tk_, tpp["es"]), "bytes/token (EN)": bytes_por_token(tk_, tpp["en"]),
                  "bytes/token (código)": bytes_por_token(tk_, tpp["code"]), "% tokens que mezclan letra/número/símbolo": 100 * np.mean([mezcla(b) for i, b in tk_.vocab.items() if i >= 256])})
df_r = pd.DataFrame(filas).set_index("pre-tokenizador"); display(df_r.round(2))
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6))
df_r[["bytes/token (ES)", "bytes/token (EN)", "bytes/token (código)"]].plot.bar(ax=axs[0], color=[AZUL, NARANJA, VERDE], rot=0); axs[0].set_title("Compresión según el pre-tokenizador"); axs[0].set_ylabel("bytes por token")
df_r["% tokens que mezclan letra/número/símbolo"].plot.bar(ax=axs[1], color=GRIS, rot=0); axs[1].set_title("Tokens que cruzan categorías"); axs[1].set_ylabel("% del vocabulario aprendido")
plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""1. La línea base «**solo espacios**» deja la puntuación pegada a las palabras y aprende **bastante más tokens que mezclan letras y símbolos** (gráfica derecha): vocabulario gastado en variantes como `cache.`, `cache,`. Los regex de GPT-2/cl100k/o200k evitan casi toda esa mezcla (cl100k/o200k conservan los tokens con un símbolo inicial como `_var`).
2. En **compresión pura** (gráfica izquierda) «solo espacios» *no pierde*, incluso gana algo aquí: el regex **no** se introdujo para comprimir más, sino para que el vocabulario sea más limpio y generalice (GPT-2 solo hace una excepción con el espacio porque eso sí comprime). Lo mismo vale para los dígitos y el camelCase: son decisiones de **calidad del modelo**, no de compresión. Con Wikipedia real las diferencias entre generaciones de regex son más visibles en números y mayúsculas."""))

nb.md(r"""
### 9.5 BPE como compresor: bits por byte
Si cada token se almacena con un código de **longitud fija** de $\lceil\log_2 |V|\rceil$ bits, el texto ocupa $n_{\text{tokens}}\cdot\log_2|V|$ bits. Un código de **Huffman** sobre la frecuencia de los tokens baja hacia la **entropía** $H_{\text{tok}}$ (cota inferior para un código de prefijo por símbolo): $n_{\text{tokens}}\cdot H_{\text{tok}}$ bits. Comparamos con compresores generales (`zlib` = LZ77 + Huffman, `bz2`, `lzma`) sobre los mismos bytes. *No incluimos el costo de almacenar el vocabulario/diccionario* (tampoco el de `zlib`, que no lo necesita).
""")
nb.code(r'''
def bits_por_byte(texto_lista, tk, max_id=None):
    nb_ = nbytes(texto_lista); ids = [i for t in texto_lista for i in tk.encode(t, max_id=max_id)]
    cnt = Counter(ids); n = len(ids); H = -sum(v / n * math.log2(v / n) for v in cnt.values())
    return {"BPE longitud fija": n * math.ceil(math.log2(len(tk.vocab) if max_id is None else max_id)) / nb_, "BPE + Huffman (cota entropía)": n * H / nb_}

filas = []
for l in ("es", "en", "code"):
    crudo = "\n".join(test[l]).encode("utf-8"); n_ = len(crudo)
    fila = {"corpus": l, "sin comprimir": 8.0, **bits_por_byte(test[l], tok),
            "zlib": len(zlib.compress(crudo, 9)) * 8 / n_, "bz2": len(bz2.compress(crudo)) * 8 / n_, "lzma": len(lzma.compress(crudo)) * 8 / n_}
    filas.append(fila)
df_b = pd.DataFrame(filas).set_index("corpus"); display(df_b.round(2))
ax = df_b.plot.bar(figsize=(9, 3.8), color=[ROJO, AZUL, NARANJA, GRIS, "#8c564b", VERDE], rot=0, width=0.85); ax.set_ylabel("bits por byte de texto"); ax.set_title(f"BPE como compresor (vocab {VOCAB}) vs compresores generales")
ax.legend(fontsize=7, ncol=3); plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""1. Un BPE con código de longitud fija **ya baja de 8 bits/byte**, y con codificación entrópica (Huffman) baja más: es compresión *orden 0 sobre tokens* (Shannon, 1948: no se puede bajar de la entropía por símbolo con un código de prefijo por símbolo).
2. Los compresores con **contexto** (LZ77 en `zlib`, BWT en `bz2`, `lzma`) ganan con claridad: BPE solo captura dependencias *locales* dentro de cada trozo. Esa dependencia a larga distancia es justo la que aprende el modelo de lenguaje: la métrica independiente del tokenizer con la que se comparan LLMs con vocabularios distintos es **bits por byte** del modelo (menos es mejor).
3. En el corpus sintético los compresores se disparan por la repetitividad del generador; con texto real su ventaja es menor, pero el orden relativo se mantiene."""))

nb.md("### 9.6 El orden de los merges importa")
nb.code(r'''
import random as _r
def seg_rango(tk, t): return tk._encode_trozo(t)
def seg_inverso(tk, t):                      # aplica el par de MAYOR id disponible (orden de merges invertido)
    ids = [tk.byte2id[bytes([b])] for b in t.encode()]
    while len(ids) > 1:
        c = [(tk.merges[p], p) for p in zip(ids, ids[1:]) if p in tk.merges]
        if not c: break
        r, p = max(c); ids = fusiona_palabra(ids, p, r)
    return ids
def seg_codicioso(tk, t):                    # prefijo más largo presente en el vocabulario (sin rangos), estilo MaxMatch
    b = t.encode(); inv = {v: k for k, v in tk.vocab.items()}; out, i = [], 0
    while i < len(b):
        L = next(L for L in range(min(len(b) - i, 16), 0, -1) if b[i:i + L] in inv); out.append(inv[b[i:i + L]]); i += L
    return out
def seg_azar(tk, t, rng=_r.Random(SEED)):
    ids = [tk.byte2id[bytes([b])] for b in t.encode()]
    while len(ids) > 1:
        c = [(tk.merges[p], p) for p in zip(ids, ids[1:]) if p in tk.merges]
        if not c: break
        r, p = rng.choice(c); ids = fusiona_palabra(ids, p, r)
    return ids
filas = []
for nombre, f in (("por rango (BPE)", seg_rango), ("rango invertido", seg_inverso), ("prefijo más largo", seg_codicioso), ("par al azar", seg_azar)):
    igual = tot = n_tok = n_byt = 0
    for t, fr in tp["es"].items():
        s = f(tok, t); igual += fr * (s == seg_rango(tok, t)); tot += fr; n_tok += fr * len(s); n_byt += fr * len(t.encode())
    filas.append({"orden de aplicación": nombre, "% trozos idénticos al de BPE": 100 * igual / tot, "bytes/token (ES)": n_byt / n_tok})
df_o = pd.DataFrame(filas).set_index("orden de aplicación"); display(df_o.round(2))
ax = df_o["% trozos idénticos al de BPE"].plot.bar(color=[AZUL, NARANJA, VERDE, GRIS], figsize=(6.5, 3.3), rot=0); ax.set_ylabel("% de trozos con la misma segmentación"); ax.set_title("Mismos merges, distinto orden de aplicación")
plt.tight_layout(); plt.show()
''')
nb.md(obs(r"""Con **el mismo conjunto de merges**, aplicarlos en otro orden (o con otra estrategia, como el prefijo más largo de WordPiece, módulo 03) cambia la segmentación de una fracción de los trozos y la compresión. Un modelo preentrenado con la segmentación por rango **no sabe leer** la otra: el *algoritmo de codificación* es parte del contrato del tokenizer, igual que el vocabulario."""))

nb.md(r"""
## 10. Complejidad
| Operación | Ingenuo | Eficiente | Notas |
|---|---|---|---|
| **Entrenar** ($M$ merges, $U$ símbolos en palabras únicas) | $O(M\cdot U)$ | ≈ $O(U + \sum_k \text{occ}_k\log P)$ con heap ($P$ = nº de pares): cada merge toca solo las ocurrencias del par | Lo medimos en la sección 6 |
| **Codificar** un trozo de $n$ bytes | $O(n\cdot m)$ ($m$ = merges aplicables) | $O(n\log n)$ con cola de prioridad y lista enlazada | Zouhar et al. (2023): de $O(NM)$ a $O(N\log M)$ |
| **Decodificar** | $O(n)$ | $O(n)$ | concatenar bytes |
| **Memoria** | $O(\lvert V\rvert)$ | igual | + caché de trozos frecuentes |

La **caché de trozos** (`_cache`) acelera la codificación de texto natural, porque las palabras se repiten (Zipf). `tiktoken` además fusiona **un par por vez** (el de menor rango, el más a la izquierda en empates) y `HF tokenizers` mantiene una caché por palabra: el resultado es el mismo que el de aplicar todos los pares de una pasada, como verificamos.
""")

nb.md(r"""
## 11. Mapa de madurez
Estado a **octubre de 2026**.
""" + "\n\n" + mapa_madurez([
    ("Byte-level BPE + regex de pre-tokenización (familia GPT)", "🟢", "Encodings `gpt2`, `cl100k_base`, `o200k_base` de `tiktoken`; los modelos de OpenAI se asocian a ellos en `tiktoken/model.py` (p. ej. `gpt-4`→cl100k, `gpt-4o`→o200k, `gpt-5`→o200k en tiktoken 0.14.0)", "Radford et al. 2019; repositorio `openai/tiktoken`"),
    ("Vocabulario ampliado sobre un BPE existente", "🟢", "Llama 3: 100 K de `tiktoken` + 28 K tokens adicionales (128 K en total)", "Llama Team 2024 (arXiv:2407.21783)"),
    ("BPE (Sennrich) con fronteras de palabra", "🟢", "Traducción automática neuronal; base de muchos tokenizers", "Sennrich et al. 2016 (arXiv:1508.07909)"),
    ("Regularización: BPE-dropout", "🟡", "Resultados en traducción; adopción parcial", "Provilkov et al. 2019 (arXiv:1910.13267)"),
    ("Tokenizers que cruzan fronteras de palabra (SuperBPE)", "🟡", "Preentrenamientos de 8B parámetros reportados en el artículo (2025)", "Liu et al. 2025 (arXiv:2503.13423)"),
    ("Modelos sin tokenizer (BLT)", "🔴", "Investigación de Meta FAIR (módulo 06)", "Pagnoni et al. 2024 (arXiv:2412.09871)"),
]) + "\n")

nb.md(r"""
## 12. 🏭 En producción
* **Casi todo LLM generalista de la familia GPT usa byte-level BPE.** En `tiktoken` 0.14.0, `gpt-4`/`gpt-3.5-turbo` → `cl100k_base`; `gpt-4o`, `gpt-4.1`, `o1`, `o3` y `gpt-5` → `o200k_base`; `gpt-oss` → `o200k_harmony` (tamaños de vocabulario: 100 277 y 200 019 contando especiales, según las constantes del código). Llama 3 parte de ese mismo tokenizer y lo amplía a 128 K.
* **Costo = tokens.** Cada token se factura y ocupa contexto: medir *tokens por carácter* de **tu** tráfico por idioma es una tarea de ingeniería habitual (módulo 04).
* **Se entrena una vez y se congela.** El tokenizer se entrena con una muestra representativa de **los datos del modelo** (no del dominio de la tarea), se serializa (vocabulario + merges + regex) y se usa idéntico en entrenamiento e inferencia; cambiarlo invalida el modelo (hay técnicas de *tokenizer transfer*, módulo 07).
* **Implementación rápida.** `tiktoken` y `tokenizers` están en Rust; Python puro sirve para entender, no para servir.
* **Tokens especiales y plantillas de chat** quedan fuera del BPE y se tratan aparte (`allowed_special`): módulo 04.
""")

nb.md(r"""
## 13. 🧠 Secretos de la élite
1. **El orden de los merges y los desempates son parte del tokenizer** (sección 9.6 y 8): dos BPE con las mismas fusiones en otro orden son incompatibles; HF y `tiktoken` desempatan distinto y por eso un vocabulario entrenado con uno no se «reproduce» con el otro aunque el algoritmo sea el mismo.
2. **Los dígitos de cl100k/o200k se parten de izquierda a derecha en grupos de 3**: `1234567` → `123|456|7`. Singh & Strouse (2024) muestran que forzar la partición de derecha a izquierda (separando con comas) **mejora la aritmética** de GPT-3.5/4. Un detalle de regex que condiciona una capacidad.
3. **El regex es más importante de lo que parece**: Schmidt et al. (2024) concluyen que la pre-tokenización pesa mucho en la calidad del tokenizer y que inicializar el vocabulario con BPE ayuda; comprimir más no implica un modelo mejor.
4. **Se entrena sobre palabras únicas ponderadas, no sobre el texto bruto** (Sennrich 2016): por eso el coste depende de la *diversidad* del corpus y no de su tamaño. En esta lección: ≈ 3 000 palabras únicas para ≈ 300 KB.
5. **Un token puede ser medio carácter UTF-8**: en *streaming* hay que decodificar bytes acumulados (sección 7). El `�` en salidas parciales de un LLM suele ser esto.
6. **Un tokenizer entrenado sobre datos distintos a los del modelo crea tokens que el modelo nunca vio** (tokens sub-entrenados): Land & Bartolo (2024) los detectan automáticamente; lo desarrollas en el módulo 05.
7. **La compresión del tokenizer no es comparable entre vocabularios** salvo normalizando por bytes: usa *bytes por token* o *bits por byte*, no «perplejidad por token».
8. **Verifica siempre contra una implementación de referencia** con *tus* merges cargados en ella (sección 8): es la forma barata de encontrar errores sutiles de regex, de orden o de bytes.
""")

nb.md(r"""
## 14. ⚠️ Errores comunes
* **Entrenar el tokenizer sobre texto sin normalizar** (o normalizar distinto en inferencia): módulo 01.
* **Aplicar los merges en un orden distinto** (p. ej. por frecuencia del par en el texto a codificar) y creer que «es lo mismo».
* **Olvidar el espacio inicial**: en GPT-2 `hello` y ` hello` son tokens distintos. Concatenar prompts sin cuidar los espacios cambia la tokenización (módulo 05: *token healing*).
* **Medir compresión sobre el mismo texto con el que entrenaste**: usa un conjunto de prueba.
* **Comparar vocabularios de distinto tamaño con «tokens por palabra»** sin fijar el corpus de evaluación.
* **Decodificar token a token y pegar cadenas**: parte caracteres multibyte.
* **Suponer que `tokenizers` y `tiktoken` entrenan igual**: coinciden al *codificar*, no al *entrenar* (desempates).
""")

nb.md(r"""
## 15. Autoevaluación
""" + "\n" + preguntas([
    ("(Cálculo)", "Corpus: «aab»×3, «ab»×2 (sobre el alfabeto `a`, `b`, sin marcador de fin). Entrena BPE un paso con la regla «mayor conteo; empate → par menor». ¿Qué par se fusiona y cómo queda el corpus?",
     "Pares: `(a,a)` aparece 1 vez en «aab» → 3 veces en total; `(a,b)`: 1 vez en «aab» (×3 = 3) + 1 en «ab» (×2 = 2) = 5. Gana `(a,b)` con 5 → token `ab`. Corpus: «a ab»×3 y «ab»×2 (es decir, `a`,`ab` y `ab`)."),
    ("(Cálculo)", "Con un vocabulario de 50 000 merges + 256 bytes + 1 token especial, ¿cuál es `n_vocab` y cuántos bits necesitas con código de longitud fija por token?",
     "`n_vocab` = 50 257 (es el de GPT-2). $\\lceil\\log_2 50257\\rceil = 16$ bits por token."),
    ("(Diagnóstico)", "Entrenaste tu BPE con `tiktoken._educational` y lo cargas en HF `tokenizers` con el mismo regex, pero algunos textos tokenizan distinto. Da tres causas posibles.",
     "(1) El regex difiere (posesivos `++` o clases Unicode entre motores); (2) falta el mapeo `bytes_to_unicode` o el pre-tokenizer `ByteLevel(use_regex=False)`; (3) hay tokens duplicados con los mismos bytes o un orden de merges distinto; (4) especiales. Se detecta comparando sobre una muestra con ids de ambos lados."),
    ("(Diagnóstico)", "Tu tokenizer comprime 4.2 bytes/token en español de Wikipedia pero 2.1 en tickets de soporte (jerga, números, mayúsculas). ¿Qué haces?",
     "El vocabulario se entrenó con datos distintos del dominio: mide con una muestra del dominio, considera reentrenar o **ampliar** el vocabulario (como Llama 3 con 28 K tokens) y revisa el regex (números, mayúsculas). Ojo: cambiar el tokenizer de un modelo ya entrenado requiere adaptación (módulo 07)."),
    ("(Transferencia)", "Quieres que un LLM sume números de 7 dígitos con fiabilidad. ¿Qué propiedades del pre-tokenizador y del vocabulario te importan?",
     "Que los dígitos se partan de forma consistente (p. ej. un dígito por token o grupos alineados a la derecha), no en grupos de 3 desde la izquierda dependientes de la longitud; Singh & Strouse (2024) muestran que el sentido de la partición cambia la exactitud."),
    ("", "¿Por qué el vocabulario de $V'$ tokens de un BPE es un prefijo del de $V>V'$?",
     "Porque cada merge se elige con el corpus resultante de aplicar los anteriores: el entrenamiento a $V'$ es exactamente las primeras $V'-256$ iteraciones del entrenamiento a $V$."),
    ("", "¿Qué garantiza la complejidad $O(N\\log M)$ de la codificación y qué estructura la logra?",
     "Una cola de prioridad con los pares adyacentes por rango y una lista doblemente enlazada de los tokens: cada fusión actualiza O(1) vecinos y cuesta $O(\\log n)$ en el heap (Zouhar et al., 2023)."),
]) + "\n")

nb.md(caja("➡️ Siguiente módulo", r"""
**03 · WordPiece, Unigram, SentencePiece, tiktoken y HF tokenizers.** Ya sabes construir y verificar un BPE. En el módulo 03 ves otros dos algoritmos (WordPiece y Unigram LM), la regularización por sub-palabras (BPE-dropout), el pipeline de `tokenizers` (normalizer → pre-tokenizer → model → post-processor → decoder) y comparas los tres sobre Políglota.
"""))

nb.md(r"""
## 16. Referencias
Referencias de arXiv comprobadas (título y autores) el 25-oct-2026 y, con venue, el 26-oct-2026; los datos de `tiktoken` provienen de la versión 0.14.0 instalada.

* Gage, P. (1994). *A New Algorithm for Data Compression.* The C Users Journal 12(2): 23–38.
* Sennrich, R., Haddow, B., Birch, A. (2016). *Neural Machine Translation of Rare Words with Subword Units.* ACL 2016. arXiv:1508.07909. https://arxiv.org/abs/1508.07909
* Wang, C., Cho, K., Gu, J. (2019). *Neural Machine Translation with Byte-Level Subwords.* arXiv:1909.03341. https://arxiv.org/abs/1909.03341
* Radford, A., Wu, J., Child, R., Luan, D., Amodei, D., Sutskever, I. (2019). *Language Models are Unsupervised Multitask Learners* (GPT-2). OpenAI.
* Zouhar, V. et al. (2023). *A Formal Perspective on Byte-Pair Encoding.* Findings of ACL 2023. arXiv:2306.16837. https://arxiv.org/abs/2306.16837
* Kozma, L., Voderholzer, J. (2024). *Theoretical Analysis of Byte-Pair Encoding.* arXiv:2411.08671. https://arxiv.org/abs/2411.08671
* Schmidt, C. W. et al. (2024). *Tokenization Is More Than Compression.* EMNLP 2024. arXiv:2402.18376. https://arxiv.org/abs/2402.18376
* Bostrom, K., Durrett, G. (2020). *Byte Pair Encoding is Suboptimal for Language Model Pretraining.* Findings of EMNLP 2020. arXiv:2004.03720. https://arxiv.org/abs/2004.03720
* Singh, A. K., Strouse, D. J. (2024). *Tokenization counts: the impact of tokenization on arithmetic in frontier LLMs.* arXiv:2402.14903. https://arxiv.org/abs/2402.14903
* Petrov, A. et al. (2023). *Language Model Tokenizers Introduce Unfairness Between Languages.* NeurIPS 2023. arXiv:2305.15425. https://arxiv.org/abs/2305.15425
* Ahia, O. et al. (2023). *Do All Languages Cost the Same? Tokenization in the Era of Commercial Language Models.* EMNLP 2023. arXiv:2305.13707. https://arxiv.org/abs/2305.13707
* Land, S., Bartolo, M. (2024). *Fishing for Magikarp: Automatically Detecting Under-trained Tokens in Large Language Models.* EMNLP 2024. arXiv:2405.05417. https://arxiv.org/abs/2405.05417
* Llama Team, AI @ Meta (2024). *The Llama 3 Herd of Models.* arXiv:2407.21783. https://arxiv.org/abs/2407.21783
* Provilkov, I., Emelianenko, D., Voita, E. (2019). *BPE-Dropout: Simple and Effective Subword Regularization.* ACL 2020. arXiv:1910.13267. https://arxiv.org/abs/1910.13267
* Liu, A. et al. (2025). *SuperBPE: Space Travel for Language Models.* COLM 2025. arXiv:2503.13423. https://arxiv.org/abs/2503.13423
* Pagnoni, A. et al. (2024). *Byte Latent Transformer: Patches Scale Better Than Tokens.* arXiv:2412.09871. https://arxiv.org/abs/2412.09871
* Shannon, C. E. (1948). *A Mathematical Theory of Communication.* Bell System Technical Journal.
* Código: `tiktoken` (https://github.com/openai/tiktoken, incl. `tiktoken/_educational.py`); Karpathy, `minbpe` (https://github.com/karpathy/minbpe); Hugging Face `tokenizers` (https://github.com/huggingface/tokenizers); `rsennrich/subword-nmt` (https://github.com/rsennrich/subword-nmt).
""")

nb.save(str(ROOT.parent / LPATH))

# ════════════════════════════════════════════════════════════════════════════
#  PROYECTO · BPE propio entrenado en Políglota
# ════════════════════════════════════════════════════════════════════════════
PPATH = f"{REL}/02_proyecto_bpe_desde_cero.ipynb"
pb = Notebook("Módulo 02 · Proyecto: BPE propio para Políglota", colab_path=PPATH)

# ---- medidas de la solución (corpus sintético, FAST_DEV, VOCAB=1000, seed 42) ----
MED = dict(es=3.29, en=3.33, code=2.19, tax=2.10)
UMB = dict(es=3.0, en=3.0, code=1.9, tax=1.5)

pb.md(pb.badge() + r"""

# Proyecto · Tu BPE para Políglota
**Módulo 02 · BPE desde cero**

| | |
|---|---|
| **Nivel** | 🟡 Intermedio |
| **Duración** | ≈ 2 h |
| **GPU** | Ninguna (CPU) |
| **Entregable** | tu `BPETokenizer` verificado contra `tiktoken` y HF `tokenizers`, y `poliglota_bpe.json` (merges) |
""")
pb.md(r"""
## Contexto de negocio
Políglota Labs va a indexar documentación en español, inglés y código. El CTO quiere **un tokenizer propio** (para controlar costos y para poder inspeccionarlo) y exige **evidencia de que está bien hecho**: que reproduce exactamente a `tiktoken` y a Hugging Face cuando se cargan sus merges, que comprime razonablemente cada idioma y que se sabe cuánto cuesta entrenar con un idioma y usarlo en otro.

**Conexión.** *Anterior (módulo 01):* tu texto llega normalizado a NFC (usa `unicodedata.normalize('NFC', t)`, o tu `normalizar` del módulo 01). *Siguiente (módulo 03):* compararás este BPE con WordPiece y Unigram sobre el mismo corpus, y el módulo 04 lo evaluará en fertilidad y paridad.
""")
pb.md(r"""
## Dataset
Corpus Políglota (`carga_corpus`, módulo 00): Wikipedia ES/EN + código Python; cadena **oficial → espejo → sintético** (la celda de carga imprime la fuente). Partición por documento: 80 % entrenamiento, 20 % prueba.
""")
pb.md(r"""
## Entregables y criterios de evaluación (rúbrica)

| # | Criterio | Umbral |
|---|---|---|
| R1 | `contar_palabras` pasa sus tests (regex GPT-2, bytes, frecuencias) | tests ✅ |
| R2 | `entrena_ingenuo` coincide con el incremental dado (60 merges sobre el corpus) y con el caso de mano | tests ✅ |
| R3 | `_encode_trozo`/`decode_bytes`: ida y vuelta sin pérdida en **todos** los documentos de prueba; con `max_id=256` el texto queda en bytes | 100 % |
| R4 | `a_tiktoken`: `tiktoken` con **tus** merges produce los mismos ids que tu `encode` | 100 % de ≥ 40 textos |
| R5 | HF `tokenizers` con **tus** merges produce los mismos ids | 100 % de ≥ 40 textos |
| R6 | Compresión en **prueba** (tokenizer entrenado en la mezcla ES+EN+código, vocabulario 1 000): bytes por token | ES ≥ **%(es).1f**, EN ≥ **%(en).1f**, código ≥ **%(code).1f** (corpus sintético) |
| R7 | **Impuesto de idioma**: bytes/token en prueba ES del tokenizer entrenado solo en ES ÷ el entrenado solo en EN | ≥ **%(tax).1f**× (corpus sintético) |
| R8 | Barrido de vocabulario: bytes/token **no decrece** al crecer el vocabulario (ES, EN, código) | monótono |
| R9 | `poliglota_bpe.json` guardado (merges, vocabulario, regex y métricas) | ✅ |

Umbrales calibrados con **lo que mide la solución de referencia** (corpus **sintético**, `FAST_DEV_RUN=True`, vocabulario 1 000, semilla 42): ES = %(mes).2f, EN = %(men).2f, código = %(mcode).2f bytes/token; impuesto ES = %(mtax).2f×. Los umbrales tienen un margen de ≈ 0.3 (0.6 en el impuesto). **No pudimos medir la solución con Wikipedia real** en el entorno de autoría (Hugging Face bloqueado): con datos reales R6 y R7 **no están calibrados**; las comprobaciones estructurales (R1–R5, R8, R9) valen igual y la solución imprime sus valores para que compares.
""".replace("%(es).1f", f"{UMB['es']:.1f}").replace("%(en).1f", f"{UMB['en']:.1f}").replace("%(code).1f", f"{UMB['code']:.1f}").replace("%(tax).1f", f"{UMB['tax']:.1f}")
   .replace("%(mes).2f", f"{MED['es']:.2f}").replace("%(men).2f", f"{MED['en']:.2f}").replace("%(mcode).2f", f"{MED['code']:.2f}").replace("%(mtax).2f", f"{MED['tax']:.2f}"))

pb.md("## 0. Preparación (celdas dadas)")
pb.code("!pip install -q numpy pandas matplotlib regex tiktoken tokenizers")
pb.code(r'''
import heapq, json, math, pathlib, random, re, sys, time, unicodedata, collections
from collections import Counter, defaultdict
import numpy as np, pandas as pd, regex
import matplotlib.pyplot as plt

SEED = 42
random.seed(SEED); np.random.seed(SEED)
FAST_DEV_RUN = True
VOCAB = 1000 if FAST_DEV_RUN else 4000
CHECKS: dict = {}

def chequea(nombre, fn):
    """Ejecuta fn() y registra ✅/❌/⏳ sin romper «Ejecutar todo»."""
    try:
        fn(); CHECKS[nombre] = True; print("✅", nombre)
    except NotImplementedError as e:
        CHECKS[nombre] = None; print("⏳ pendiente:", nombre, "→", e)
    except AssertionError as e:
        CHECKS[nombre] = False; print("❌", nombre, "→", e)
    except Exception as e:  # noqa: BLE001
        CHECKS[nombre] = False; print("💥", nombre, "→", type(e).__name__, e)
''')
_c = src_corpus_cells()
pb.code("# ── carga_corpus (1/3) ──\n" + _c[0])
pb.code("# ── carga_corpus (2/3) ──\n" + _c[1])
pb.code("# ── carga_corpus (3/3) ──\n" + _c[2])
pb.code(SRC_PATTERNS)
_fus = SRC_TRAIN[SRC_TRAIN.index("def fusiona_palabra"):SRC_TRAIN.index("def entrena_ingenuo")].rstrip()
pb.code("# ── Dado: fusión de un par en una palabra y entrenador INCREMENTAL de la lección ──\n" + _fus + "\n\n\n" + SRC_TRAIN_INC)
pb.code(r'''
corpus = carga_corpus(fast_dev=FAST_DEV_RUN)
docs, source = corpus["docs"], corpus["source"]
nf = lambda t: unicodedata.normalize("NFC", t)
train = {l: [nf(d["text"]) for i, d in enumerate([d for d in docs if d["lang"] == l]) if i % 5 != 0] for l in ("es", "en", "code")}
test = {l: [nf(d["text"]) for i, d in enumerate([d for d in docs if d["lang"] == l]) if i % 5 == 0] for l in ("es", "en", "code")}
print(f"source = {source!r} | train: {sum(map(len, train.values()))} docs | test: {sum(map(len, test.values()))} docs")
''')

pb.md(r"""
## TODO 1 · Contar palabras
Implementa `contar_palabras(textos, pat_str=PAT_GPT2)`: parte cada texto con el regex, convierte cada trozo a **tupla de bytes UTF-8** y devuelve un `Counter` `{tupla: frecuencia}`. (Entrenar sobre palabras únicas ponderadas es lo que hace Sennrich y lo que hace tractable el entrenamiento.)

""" + pista(1, "`regex.compile(pat_str).findall(texto)` devuelve los trozos; cada trozo `w` se convierte con `tuple(w.encode('utf-8'))`.") + "\n\n" + pista(2, "`Counter(tuple(w.encode('utf-8')) for t in textos for w in pat.findall(t))`."))
pb.code(r'''
def contar_palabras(textos, pat_str=PAT_GPT2):
    # TODO
    raise NotImplementedError("TODO 1: implementa contar_palabras")

def test_contar():
    wc = contar_palabras(["a b a", "ab"])
    assert wc == Counter({(97,): 1, (32, 98): 1, (32, 97): 1, (97, 98): 1}), f"obtuve {wc}"
    assert contar_palabras(["¿qué?"])[tuple("é".encode())] == 0 and tuple("qué".encode()) in contar_palabras(["¿qué?"])
chequea("R1 contar_palabras", test_contar)
''')

pb.md(r"""
## TODO 2 · Entrenador ingenuo
Implementa `entrena_ingenuo(wc, n_merges)`: en cada iteración **recuenta todos los pares** (ponderados por la frecuencia de la palabra), elige el de **mayor conteo y, ante empate, el menor** `(a, b)`, lo añade a `merges` y lo fusiona en todas las palabras con id nuevo `256 + k` (usa `fusiona_palabra`). Devuelve la lista de pares. Debe coincidir **exactamente** con `entrena_incremental`.

""" + pista(1, "Mantén `palabras = [list(w) for w in wc]` y `frec = list(wc.values())`. Cada iteración: un `Counter` de pares con `zip(w, w[1:])`.") + "\n\n" + pista(2, "Elección: `min(stats, key=lambda p: (-stats[p], p))`. Después `palabras = [fusiona_palabra(w, par, 256 + k) for w in palabras]`. Detente si `stats` está vacío."))
pb.code(r'''
def entrena_ingenuo(wc, n_merges):
    # TODO
    raise NotImplementedError("TODO 2: implementa entrena_ingenuo")

def test_ingenuo():
    assert entrena_ingenuo(Counter({(97, 98): 3, (97, 97, 98): 1}), 1) == [(97, 98)], "(a,b) aparece 4 veces; (a,a), 1"
    wc = contar_palabras(train["es"][:40] + train["code"][:20])
    assert entrena_ingenuo(wc, 60) == entrena_incremental(wc, 60), "el ingenuo y el incremental deben dar los mismos merges"
chequea("R2 entrena_ingenuo", test_ingenuo)
''')

pb.md(r"""
## TODO 3 · Codificar y decodificar
Completa dos métodos de `BPETokenizer` (el resto está dado): `_encode_trozo(trozo, max_id=None)` y `decode_bytes(ids)`.
* `_encode_trozo`: convierte el trozo a ids de byte (`self.byte2id`), y **mientras haya algún par en `self.merges`**, fusiona el de **menor id resultante** (`merges[par]`) en todas sus apariciones (con `fusiona_palabra`). Si `max_id` no es `None`, no apliques merges con id `>= max_id`. Guarda el resultado en `self._cache`.
* `decode_bytes`: concatena `self.vocab[i]` (o los bytes del token especial) → `bytes`.

""" + pista(1, "Bucle `while len(ids) > 1:`; candidatos `[(self.merges.get(p, 1 << 60), p) for p in zip(ids, ids[1:])]`; `rango, par = min(candidatos)`; si `rango == 1 << 60` (o `>= max_id`) sal del bucle.") + "\n\n" + pista(2, "`ids = fusiona_palabra(ids, par, rango)`. Para decodificar: `b''.join(self.vocab[i] if i in self.vocab else inv_especiales[i] for i in ids)` con `inv_especiales = {v: k.encode() for k, v in self.special.items()}`."))
pb.code(r'''
class BPETokenizer:
    def __init__(self, pat_str=PAT_GPT2, vocab=None, merges=None, special_tokens=None):
        self.pat_str, self.pat = pat_str, regex.compile(pat_str)
        self.vocab = vocab or {i: bytes([i]) for i in range(256)}
        self.merges = merges or {}                    # (id_a, id_b) -> id nuevo (el id nuevo ES la prioridad)
        self.special = special_tokens or {}
        self.byte2id = {b: i for i, b in self.vocab.items() if len(b) == 1}
        self._cache = {}

    @classmethod
    def train(cls, textos, vocab_size, pat_str=PAT_GPT2):
        lista = entrena_incremental(contar_palabras(textos, pat_str), vocab_size - 256)
        vocab, merges = {i: bytes([i]) for i in range(256)}, {}
        for k, (a, b) in enumerate(lista):
            vocab[256 + k] = vocab[a] + vocab[b]; merges[(a, b)] = 256 + k
        return cls(pat_str, vocab, merges)

    def _encode_trozo(self, trozo, max_id=None):
        # TODO: aplica los merges por rango (menor id primero)
        raise NotImplementedError("TODO 3a: implementa _encode_trozo")

    def encode(self, texto, allowed_special=(), max_id=None):
        partes = regex.split("(" + "|".join(map(regex.escape, allowed_special)) + ")", texto) if allowed_special else [texto]
        ids = []
        for p in partes:
            if p in self.special and p in allowed_special: ids.append(self.special[p])
            else: ids += [i for t in self.pat.findall(p) for i in self._encode_trozo(t, max_id)]
        return ids

    def decode_bytes(self, ids):
        # TODO
        raise NotImplementedError("TODO 3b: implementa decode_bytes")

    def decode(self, ids): return self.decode_bytes(ids).decode("utf-8", errors="replace")

tok = None
try:
    tok = BPETokenizer.train(train["es"] + train["en"] + train["code"], VOCAB)
    tok.special = {"<|endoftext|>": len(tok.vocab)}
    print(f"vocabulario: {len(tok.vocab)} tokens | merges: {len(tok.merges)} | primeros tokens aprendidos:", [tok.vocab[i] for i in range(256, 264)])
except NotImplementedError as e:
    print("⏳ pendiente:", e)

def test_roundtrip():
    if tok is None: raise NotImplementedError('completa antes los TODO 1-3')
    todos = [t for l in test for t in test[l]]
    assert all(tok.decode(tok.encode(t)) == t for t in todos), "ida y vuelta fallida"
    assert all(len(tok.encode(t, max_id=256)) == len(t.encode()) for t in todos[:30]), "con max_id=256 debe haber 1 token por byte"
    assert tok.decode(tok.encode("a<|endoftext|>b", allowed_special={"<|endoftext|>"})) == "a<|endoftext|>b"
chequea("R3 encode/decode", test_roundtrip)
''')

pb.md(r"""
## TODO 4 · Verifica contra `tiktoken`
Implementa `a_tiktoken(tok)`: un `tiktoken.Encoding` con `pat_str=tok.pat_str`, `mergeable_ranks = {bytes del token: id}` y `special_tokens=dict(tok.special)`. Luego compara los ids de `tok.encode(t)` y `enc.encode(t, allowed_special="all")` sobre ≥ 40 textos variados (los dados + los tuyos).

""" + pista(1, "`tiktoken.Encoding(name, pat_str=..., mergeable_ranks=..., special_tokens=...)`. Las claves de `mergeable_ranks` son `bytes`; el valor es el rango (aquí, el id).") + "\n\n" + pista(2, "`ranks = {tok.vocab[i]: i for i in tok.vocab}`. Si `len(ranks) != len(tok.vocab)` hay dos tokens con los mismos bytes y tiktoken no lo admite."))
pb.code(r'''
import tiktoken
from tokenizers import Tokenizer, models, pre_tokenizers, decoders, Regex

def a_tiktoken(tok, nombre="mi_bpe"):
    # TODO
    raise NotImplementedError("TODO 4: implementa a_tiktoken")

PRUEBAS = [t[:300] for l in test for t in test[l][:12]] + ["Hola, ¿cómo estás? 😀 你好\n\n  x", "naïve café 123456 ", "   ", "a\tb\r\nc  ", "don't DON'T", "x=3.14159;y=-42", "", "Año 2026"]

def test_tiktoken():
    if tok is None: raise NotImplementedError('completa antes los TODO 1-3')
    assert len(PRUEBAS) >= 40
    enc = a_tiktoken(tok)
    malos = [t for t in PRUEBAS if tok.encode(t) != enc.encode(t)]
    assert not malos, f"{len(malos)}/{len(PRUEBAS)} textos difieren, p. ej. {malos[0][:50]!r}"
chequea("R4 == tiktoken", test_tiktoken)
''')

pb.md(r"""
## TODO 5 · Verifica contra Hugging Face `tokenizers` (dado) y analiza
La función `hf_desde_mio` está dada (usa `bytes_to_unicode` de GPT-2 y un pre-tokenizer `Split(regex) + ByteLevel`). Solo tienes que ejecutar la comparación y **explicar** (en la celda de texto) por qué el *entrenador* de HF, a diferencia de su *codificador*, no reproduce tus merges.
""")
pb.code(r'''
def bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs, n = bs[:], 0
    for b in range(256):
        if b not in bs: bs.append(b); cs.append(256 + n); n += 1
    return dict(zip(bs, map(chr, cs)))
B2U = bytes_to_unicode(); a_str = lambda b: "".join(B2U[x] for x in b)
GPT2_ORIG = r"""'s|'t|'re|'ve|'m|'ll|'d| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""

def hf_desde_mio(tk, pat=GPT2_ORIG):
    vocab = {a_str(tk.vocab[i]): i for i in sorted(tk.vocab)}
    merges = [(a_str(tk.vocab[a]), a_str(tk.vocab[b])) for (a, b), _ in sorted(tk.merges.items(), key=lambda kv: kv[1])]
    hf = Tokenizer(models.BPE(vocab=vocab, merges=merges))
    hf.pre_tokenizer = pre_tokenizers.Sequence([pre_tokenizers.Split(Regex(pat), behavior="isolated"), pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=False)])
    hf.decoder = decoders.ByteLevel(); return hf

def test_hf():
    if tok is None: raise NotImplementedError('completa antes los TODO 1-3')
    hf = hf_desde_mio(tok)
    malos = [t for t in PRUEBAS if tok.encode(t) != hf.encode(t).ids]
    assert not malos, f"{len(malos)}/{len(PRUEBAS)} textos difieren, p. ej. {malos[0][:50]!r}"
chequea("R5 == HF tokenizers", test_hf)
''')
pb.md(r"""
**✍️ Explica (2–4 líneas):** ¿por qué HF `BpeTrainer` y tu `entrena_incremental` pueden producir listas de merges distintas aunque el *codificador* coincida? ¿Qué parte del contrato del tokenizer decide? *(Pista: desempates.)*

> …
""")

pb.md(r"""
## TODO 6 · Evalúa: compresión, impuesto de idioma y barrido de vocabulario
Implementa `bytes_por_token(tk, textos, max_id=None)` (bytes UTF-8 totales ÷ tokens totales sobre `textos`). Después rellena `RES` con:
* `comp`: bytes/token de `tok` en prueba por idioma (`es`, `en`, `code`);
* `tax`: bytes/token en prueba ES del tokenizer entrenado **solo en ES** ÷ el entrenado **solo en EN** (mismo `VOCAB`);
* `barrido`: para `Vs = [256, 400, 600, 800, VOCAB]` y cada idioma, `bytes_por_token(tok, test[l], max_id=V)`.

""" + pista(1, "Para la compresión, suma `len(t.encode())` y `len(tk.encode(t, max_id=max_id))` sobre los textos. El barrido no reentrena: usa `max_id` (el vocabulario de tamaño V es el prefijo de los merges).") + "\n\n" + pista(2, "`tax = bpt(tk_es, test['es']) / bpt(tk_en, test['es'])`, con `tk_es = BPETokenizer.train(train['es'], VOCAB)` y análogo para EN."))
pb.code(r'''
def bytes_por_token(tk, textos, max_id=None):
    # TODO
    raise NotImplementedError("TODO 6a: implementa bytes_por_token")

RES = {}
try:
    Vs = [256, 400, 600, 800, VOCAB]
    tk_es, tk_en = BPETokenizer.train(train["es"], VOCAB), BPETokenizer.train(train["en"], VOCAB)
    RES = {"comp": {l: bytes_por_token(tok, test[l]) for l in test},
           "tax": bytes_por_token(tk_es, test["es"]) / bytes_por_token(tk_en, test["es"]),
           "barrido": {l: [bytes_por_token(tok, test[l], max_id=v) for v in Vs] for l in test}, "Vs": Vs}
    print({k: (round(v, 2) if isinstance(v, float) else {a: (round(b, 2) if isinstance(b, float) else [round(x, 2) for x in b]) for a, b in v.items()}) for k, v in RES.items() if k != "Vs"})
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for l, c in zip(test, ("#1F6FEB", "#F28E2B", "#2CA02C")): ax.plot(Vs, RES["barrido"][l], "o-", color=c, label=l)
    ax.set_xlabel("tamaño del vocabulario"); ax.set_ylabel("bytes por token (prueba)"); ax.set_title(f"Compresión vs vocabulario (corpus {source})"); ax.legend(); plt.tight_layout(); plt.show()
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''')
pb.md("> 👀 **Qué debes observar.** En $V=256$ (solo bytes) las tres curvas valen exactamente 1 byte/token; después suben rápido y se aplanan (rendimientos decrecientes, como en la lección §9.1). El **código** queda por debajo de ES/EN (más símbolos y combinaciones raras). Y el impuesto `tax` > 1 significa que, para el mismo texto en español, el tokenizer entrenado solo en español comprime más que el entrenado en inglés: la referencia mide ≈ 2.1× con corpus sintético.")

pb.md(r"""
## TODO 7 · Guardar tu tokenizer
Implementa `guardar_bpe(tok, path='poliglota_bpe.json')`: guarda un JSON con `pat_str`, `merges` (lista de pares `[id_a, id_b]` **en orden**), `vocab_size`, `special_tokens`, `source` y `metricas` (`RES['comp']`, `RES['tax']`). Debe poder reconstruirse: añade `cargar_bpe(path)` que devuelva un `BPETokenizer` con el mismo `encode`.

""" + pista(1, "Con la lista ordenada de merges puedes reconstruir `vocab` (`vocab[256+k] = vocab[a] + vocab[b]`) y `merges`.") + "\n\n" + pista(2, "`sorted(tok.merges.items(), key=lambda kv: kv[1])` te da los pares en orden de creación."))
pb.code(r'''
def guardar_bpe(tok, path="poliglota_bpe.json"):
    # TODO
    raise NotImplementedError("TODO 7a: implementa guardar_bpe")

def cargar_bpe(path="poliglota_bpe.json"):
    # TODO
    raise NotImplementedError("TODO 7b: implementa cargar_bpe")

def test_json():
    guardar_bpe(tok); tok2 = cargar_bpe()
    assert all(tok.encode(t) == tok2.encode(t) for t in PRUEBAS) and len(tok2.vocab) == len(tok.vocab)
    assert {"pat_str", "merges", "vocab_size", "special_tokens", "source", "metricas"} <= set(json.loads(pathlib.Path("poliglota_bpe.json").read_text()))
chequea("R9 poliglota_bpe.json", test_json)
''')

pb.md("## Rúbrica: comprobación automática")
pb.code(r'''
UMBRALES = ''' + repr(UMB) + r'''   # medidos con la solución (ver la tabla; solo corpus SINTÉTICO)

def rubrica():
    for n, e in CHECKS.items(): print({True: "✅", False: "❌", None: "⏳"}[e], n)
    if RES:
        mono = all(all(b >= a - 1e-9 for a, b in zip(v, v[1:])) for v in RES["barrido"].values())
        print("✅" if mono else "❌", "R8 barrido monótono:", {l: [round(x, 2) for x in v] for l, v in RES["barrido"].items()})
        if source == "synthetic":
            u = UMBRALES
            for nombre, v, t in (("R6 ES", RES["comp"]["es"], u["es"]), ("R6 EN", RES["comp"]["en"], u["en"]), ("R6 código", RES["comp"]["code"], u["code"]), ("R7 impuesto", RES["tax"], u["tax"])):
                print("✅" if v >= t else "❌", f"{nombre} = {v:.2f} (≥ {t})")
        else:
            print("ℹ️ corpus REAL: R6 y R7 no están calibrados; reporta tus valores:", {k: round(v, 2) for k, v in RES["comp"].items()}, "impuesto", round(RES["tax"], 2))
rubrica()
''')

pb.md(r"""
## Retos extra (nivel experto)
1. **Mejora la codificación a $O(n\log n)$** con una lista doblemente enlazada y un heap de pares adyacentes; mide la aceleración con trozos largos (URLs, líneas de código sin espacios) frente a tu `_encode_trozo`.
2. **Carga `cl100k_base`/`o200k_base`** (si `tiktoken` puede descargarlos) con la receta de `desde_tiktoken` de la lección y verifica tu `encode` con ellos sobre Políglota; compara tokens/carácter por idioma.
3. **Regex propio para Políglota**: parte de `PAT_O200K`, añade una regla que no parta `snake_case` en el código y mide bytes/token en código antes y después.
4. **BPE-dropout** (Provilkov et al., 2019): en `_encode_trozo`, ignora cada merge con probabilidad $p$ y observa cuánto varía la segmentación de una misma palabra entre llamadas.
5. **Tokens sub-entrenados:** cuenta cuántos tokens de tu vocabulario no aparecen nunca en el conjunto de prueba y cuántos aparecen < 3 veces en entrenamiento; relaciónalo con el módulo 05.
""")
pb.md(r"""
## Reflexión
* Tu tokenizer, entrenado en la mezcla, rinde peor en cada idioma que el especialista. ¿Qué proporción de datos por idioma elegirías para Políglota y cómo lo decidirías (costo en tokens vs calidad del retrieval)?
* ¿Qué ocurre si en producción el indexador usa tu tokenizer con NFC y el cliente envía texto NFD? ¿Dónde lo arreglas?
* El módulo 03 compara BPE con Unigram y WordPiece: ¿qué métricas, además de bytes/token, usarías para decidir?
""")

pb.md(r"""
---
# ⛔ SPOILER — intenta resolverlo primero
Debajo está la solución de referencia, completa y ejecutable. Si «Ejecutar todo» llega hasta aquí, estas celdas **sobrescriben** tus funciones con las de referencia.
""")
pb.code("# ── SOLUCIÓN · TODO 1 y 2 ──\n" + SRC_TRAIN)
pb.code("# ── SOLUCIÓN · TODO 3 ──\n" + SRC_TOKENIZER + r'''

tok = BPETokenizer.train(train["es"] + train["en"] + train["code"], VOCAB)
tok.special = {"<|endoftext|>": len(tok.vocab)}
print(f"vocabulario: {len(tok.vocab)} tokens | merges: {len(tok.merges)} | primeros tokens:", [tok.vocab[i] for i in range(256, 264)])
''')
pb.code(r'''
# ── SOLUCIÓN · TODO 4 ──
def a_tiktoken(tok, nombre="mi_bpe"):
    ranks = {tok.vocab[i]: i for i in sorted(tok.vocab)}
    assert len(ranks) == len(tok.vocab), "hay dos tokens con los mismos bytes: tiktoken no lo admite"
    return tiktoken.Encoding(nombre, pat_str=tok.pat_str, mergeable_ranks=ranks, special_tokens=dict(tok.special))
''')
pb.code(r'''
# ── SOLUCIÓN · TODO 6 y 7 ──
def bytes_por_token(tk, textos, max_id=None):
    nb_ = sum(len(t.encode("utf-8")) for t in textos); nt = sum(len(tk.encode(t, max_id=max_id)) for t in textos)
    return nb_ / nt

Vs = [256, 400, 600, 800, VOCAB]
tk_es, tk_en = BPETokenizer.train(train["es"], VOCAB), BPETokenizer.train(train["en"], VOCAB)
RES = {"comp": {l: bytes_por_token(tok, test[l]) for l in test}, "tax": bytes_por_token(tk_es, test["es"]) / bytes_por_token(tk_en, test["es"]),
       "barrido": {l: [bytes_por_token(tok, test[l], max_id=v) for v in Vs] for l in test}, "Vs": Vs}
print({l: round(v, 2) for l, v in RES["comp"].items()}, "| impuesto ES:", round(RES["tax"], 2))

def guardar_bpe(tok, path="poliglota_bpe.json"):
    merges = [list(p) for p, _ in sorted(tok.merges.items(), key=lambda kv: kv[1])]
    d = {"pat_str": tok.pat_str, "merges": merges, "vocab_size": len(tok.vocab), "special_tokens": tok.special, "source": source,
         "metricas": {"comp": RES["comp"], "tax": RES["tax"]}}
    pathlib.Path(path).write_text(json.dumps(d, ensure_ascii=False)); return d

def cargar_bpe(path="poliglota_bpe.json"):
    d = json.loads(pathlib.Path(path).read_text()); vocab, merges = {i: bytes([i]) for i in range(256)}, {}
    for k, (a, b) in enumerate(d["merges"]):
        vocab[256 + k] = vocab[a] + vocab[b]; merges[(a, b)] = 256 + k
    return BPETokenizer(d["pat_str"], vocab, merges, d["special_tokens"])

for nombre, fn in [("R1 contar_palabras", test_contar), ("R2 entrena_ingenuo", test_ingenuo), ("R3 encode/decode", test_roundtrip),
                   ("R4 == tiktoken", test_tiktoken), ("R5 == HF tokenizers", test_hf), ("R9 poliglota_bpe.json", test_json)]:
    chequea(nombre, fn)
rubrica()
''')
pb.md(caja("📌 Valores de referencia de la solución", r"""
Corpus **sintético**, `FAST_DEV_RUN=True`, vocabulario 1 000, semilla 42: bytes/token en prueba ES 3.29, EN 3.33, código 2.19; impuesto de idioma (ES-ES ÷ EN-ES) 2.10×; `tiktoken` y HF con tus merges: 100 % de coincidencia. Con datos **reales** tus números serán distintos (no pudimos medirlos en el entorno de autoría). Guarda `poliglota_bpe.json`: los módulos 03 y 04 lo usan como punto de comparación.
"""))
pb.save(str(ROOT.parent / PPATH))
