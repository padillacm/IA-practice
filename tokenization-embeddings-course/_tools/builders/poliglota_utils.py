"""Fuente ÚNICA de las utilidades canónicas de Políglota (definidas en el módulo 00).

Los builders de otros módulos pueden pegarlas en sus notebooks sin reescribirlas:

    import sys; sys.path.insert(0, "tokenization-embeddings-course/_tools/builders")
    from poliglota_utils import src_corpus_cells, SRC_METRICS, SRC_BM25
    for cell_src in src_corpus_cells(): nb.code(cell_src)      # 3 celdas: datos, sintético, carga_corpus
    nb.code(SRC_METRICS)                                       # ndcg_at_k, recall_at_k, mrr_at_k, evaluate
    nb.code(SRC_BM25)                                          # tokenize_simple + BM25

Cada notebook sigue siendo autocontenido (el código se copia dentro de las celdas).
"""
import pathlib

_D = pathlib.Path(__file__).parent / "poliglota_src"


def _read(name: str) -> str:
    return (_D / name).read_text(encoding="utf-8").rstrip() + "\n"


SRC_METRICS = _read("metrics.py")
SRC_BM25 = _read("bm25.py")
SRC_CORPUS_DATA = _read("corpus_data.py")
SRC_CORPUS_SYNTH = _read("corpus_synth.py")
SRC_CORPUS_LOADER = _read("corpus_loader.py")


def src_corpus_cells() -> list[str]:
    """Las 3 celdas de código que definen carga_corpus() (en este orden)."""
    return [SRC_CORPUS_DATA, SRC_CORPUS_SYNTH, SRC_CORPUS_LOADER]
