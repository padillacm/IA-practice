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
