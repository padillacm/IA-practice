# ── Tokenización simple + BM25 propio (módulo 00) ─────────────────────────────
import math
import re
import unicodedata
from collections import Counter, defaultdict

import numpy as np

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def fold_accents(text: str) -> str:
    """'canción' -> 'cancion' (NFD y descartar marcas combinantes Mn)."""
    nfd = unicodedata.normalize("NFD", text)
    return unicodedata.normalize("NFC", "".join(c for c in nfd if unicodedata.category(c) != "Mn"))


def tokenize_simple(text: str, accents: str = "keep") -> list[str]:
    """Minúsculas + palabras \\w+. accents='fold' quita tildes. (Esto NO es el 'token' de un LLM: es un token léxico.)"""
    text = unicodedata.normalize("NFC", text).lower()
    if accents == "fold":
        text = fold_accents(text)
    return _WORD_RE.findall(text)


class BM25:
    """BM25 con índice invertido. idf='lucene': ln(1+(N-n+.5)/(n+.5)) (siempre >= 0).
    idf='okapi': ln((N-n+.5)/(n+.5)) con suelo epsilon*idf_medio (como rank_bm25.BM25Okapi)."""

    def __init__(self, k1: float = 1.2, b: float = 0.75, idf: str = "lucene", epsilon: float = 0.25):
        self.k1, self.b, self.idf_kind, self.epsilon = k1, b, idf, epsilon

    def fit(self, docs_tokens: list[list[str]], doc_ids: list[str]) -> "BM25":
        self.doc_ids = list(doc_ids)
        self.N = len(docs_tokens)
        self.dl = np.array([len(t) for t in docs_tokens], dtype=float)
        self.avgdl = float(self.dl.mean()) if self.N else 0.0
        self.postings = defaultdict(list)  # término -> [(índice_doc, tf)]
        for i, toks in enumerate(docs_tokens):
            for term, tf in Counter(toks).items():
                self.postings[term].append((i, tf))
        raw = {t: len(p) for t, p in self.postings.items()}
        if self.idf_kind == "lucene":
            self.idf = {t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in raw.items()}
        else:
            self.idf = {t: math.log(self.N - n + 0.5) - math.log(n + 0.5) for t, n in raw.items()}
            floor = self.epsilon * sum(self.idf.values()) / len(self.idf)
            self.idf = {t: (v if v >= 0 else floor) for t, v in self.idf.items()}
        return self

    def scores(self, q_tokens: list[str]) -> np.ndarray:
        s = np.zeros(self.N)
        for term in q_tokens:  # los términos repetidos de la query suman varias veces (igual que rank_bm25)
            for i, tf in self.postings.get(term, ()):
                norm = self.k1 * (1 - self.b + self.b * self.dl[i] / self.avgdl)
                s[i] += self.idf[term] * tf * (self.k1 + 1) / (tf + norm)
        return s

    def search(self, q_tokens: list[str], k: int = 10) -> list[str]:
        s = self.scores(q_tokens)
        order = np.lexsort((np.arange(self.N), -s))[:k]  # empates -> orden del corpus
        return [self.doc_ids[i] for i in order]
