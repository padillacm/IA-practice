"""RAG minimalista: recuperación TF-IDF + coseno sobre ~14 documentos. Sin dependencias externas."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

from .catalog import KB_DOCS, KBDoc

STOPWORDS = set(
    "a al algo como con de del el ella en es esta este la las lo los me mi mis no o para por que se si su sus un una "
    "y ya puedo puede quiero tengo hay cuanto cuando donde cual".split()
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def tokenize(text: str) -> list[str]:
    toks = re.findall(r"[a-z0-9]+", _norm(text))
    return [t for t in toks if t not in STOPWORDS and len(t) > 1]


class KnowledgeBase:
    def __init__(self, docs: list[KBDoc] | None = None):
        self.docs = docs or KB_DOCS
        self._tf = [Counter(tokenize(d.title + " " + d.text)) for d in self.docs]
        n = len(self.docs)
        df: Counter[str] = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        self._idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        self._vecs = [self._vec(tf) for tf in self._tf]

    def _vec(self, tf: Counter) -> dict[str, float]:
        v = {t: c * self._idf.get(t, 0.0) for t, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def search(self, query: str, k: int = 3) -> list[dict]:
        q = self._vec(Counter(tokenize(query)))
        scored = []
        for doc, vec in zip(self.docs, self._vecs):
            score = sum(w * vec.get(t, 0.0) for t, w in q.items())
            scored.append((score, doc))
        scored.sort(key=lambda x: (-x[0], x[1].doc_id))
        return [
            {"doc_id": d.doc_id, "title": d.title, "text": d.text, "score": round(s, 4)}
            for s, d in scored[:k] if s > 0
        ]
