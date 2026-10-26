"""Piezas comunes de los builders del autor A3 (módulos 06, 07, 08).

Cada notebook sigue siendo autocontenido: aquí solo viven las cadenas de texto/código
que los builders copian dentro de las celdas, y pequeños helpers de markdown.
"""
from __future__ import annotations

import textwrap


def observe(text: str) -> str:
    """Caja «👀 Qué debes observar» (blockquote)."""
    body = textwrap.dedent(text).strip()
    lines = "\n".join(f"> {ln}" if ln.strip() else ">" for ln in body.splitlines())
    return f"> **👀 Qué debes observar**\n>\n{lines}"


def box(emoji_title: str, text: str) -> str:
    body = textwrap.dedent(text).strip()
    lines = "\n".join(f"> {ln}" if ln.strip() else ">" for ln in body.splitlines())
    return f"> **{emoji_title}**\n>\n{lines}"


def details(summary: str, body: str) -> str:
    return f"<details>\n<summary>{summary}</summary>\n\n{textwrap.dedent(body).strip()}\n\n</details>"


def hint(n: int, text: str) -> str:
    return details(f"🪜 Pista {n}", text)


SETUP_COMMON = '''
import os, sys, time, math, random, warnings
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore")
import numpy as np
import torch

SEED = 42
random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
FAST_DEV_RUN = True      # True: CPU, minutos. False: GPU (T4/L4), escala completa
device = "cuda" if torch.cuda.is_available() else "cpu"
if device == "cpu":
    torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", min(4, os.cpu_count() or 1))))
print("device:", device, "| FAST_DEV_RUN:", FAST_DEV_RUN, "| torch", torch.__version__)
'''


def corpus_cells() -> list[str]:
    """Celdas canónicas de carga_corpus() (autor A1, poliglota_utils.py): datos, generador sintético, carga."""
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from poliglota_utils import src_corpus_cells
    return src_corpus_cells()
