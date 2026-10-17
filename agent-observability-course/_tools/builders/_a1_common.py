"""Utilidades compartidas por build_00/01/02 (autor A1): rutas, bootstrap de notebooks y cajas de estilo."""
from __future__ import annotations

import pathlib
import sys
import textwrap

COURSE = pathlib.Path(__file__).resolve().parents[2]          # .../agent-observability-course
sys.path.insert(0, str(COURSE / "_tools"))
from nbbuild import Notebook  # noqa: E402

REL = "agent-observability-course"                             # prefijo relativo a la raíz del repo (para el badge)


def nb_for(slug_dir: str, fname: str, title: str) -> tuple[Notebook, str]:
    path = f"{REL}/{slug_dir}/{fname}"
    return Notebook(title, colab_path=path), str(COURSE / slug_dir / fname)


def box(kind: str, title: str, body: str) -> str:
    icons = {"idea": "💡 Intuición", "math": "📐 Matemáticas", "prod": "🏭 En producción", "elite": "🧠 Secretos de la élite",
             "warn": "⚠️ Cuidado", "exp": "🧪 Experimento", "more": "📚 Para profundizar", "route": "🧭 Ruta"}
    head = f"**{icons.get(kind, kind)} · {title}**" if title else f"**{icons.get(kind, kind)}**"
    lines = textwrap.dedent(body).strip("\n").splitlines()
    return "> " + head + "\n>\n" + "\n".join("> " + ln if ln.strip() else ">" for ln in lines)


def observe(text: str) -> str:
    lines = textwrap.dedent(text).strip("\n").splitlines()
    return "> 👀 **Qué debes observar**\n>\n" + "\n".join("> " + ln if ln.strip() else ">" for ln in lines)


def details(summary: str, body: str) -> str:
    first, _, rest = body.strip().partition("\n")
    body = first + ("\n" + textwrap.dedent(rest) if rest else "")
    return f"<details>\n<summary>{summary}</summary>\n\n{body}\n\n</details>"


def hint(n: int, body: str) -> str:
    return details(f"🪜 Pista {n}", body)


BOOT = '''
# Instala el paquete del curso (editable) con extras de gráficos. Sirve en local y en Colab (clona el repo si hace falta).
import pathlib, subprocess, sys

def _find_root():
    for p in [pathlib.Path.cwd(), *pathlib.Path.cwd().parents]:
        if (p / "pyproject.toml").exists() and (p / "supportops").is_dir():
            return p
    return None

ROOT = _find_root()
if ROOT is None:  # p. ej. Google Colab: el notebook se abre sin el repo
    subprocess.run(["git", "clone", "-q", "--depth", "1", "https://github.com/padillacm/IA-practice", "/content/IA-practice"], check=True)
    ROOT = pathlib.Path("/content/IA-practice/agent-observability-course")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", f"{ROOT}[EXTRAS]"], check=True)
if str(ROOT) not in sys.path:   # un editable recién instalado no es visible hasta reiniciar el kernel: lo añadimos a mano
    sys.path.insert(0, str(ROOT))
import importlib; importlib.invalidate_caches()
print("Curso en:", ROOT)
'''


def boot(extras: str = "viz") -> str:
    return BOOT.replace("EXTRAS", extras)


IMPORTS = '''
import os
os.environ.setdefault("LLM_PROVIDER", "mock")          # mock = determinista, sin coste, sin API keys
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from supportops import *                                 # SupportAgent, generate_tickets, check_stack, ...
from supportops import viz, sample_data, schema, backends
viz.apply_style()
pd.set_option("display.width", 140); pd.set_option("display.max_colwidth", 80)
SEED = 42
FAST_DEV_RUN = True   # True: pocos tickets (iteración rápida). False: tamaños «completos» del texto
'''
