"""Construye el módulo 15 (lección + proyecto + poliglota_eval.py). Ejecutar desde la raíz del repo:
    python tokenization-embeddings-course/_tools/builders/build_15.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))   # nbbuild
sys.path.insert(0, HERE)
from nbbuild import Notebook
from _a6_readmes import README_15
from _a6_src15 import METRICS_SRC, STATS_SRC, RETRIEVERS_SRC, EVAL_MODULE_HEADER
import _b15_lesson1, _b15_lesson2, _b15_lesson3

COURSE = "tokenization-embeddings-course"
MOD = f"{COURSE}/15_evaluacion_retrieval"


def build_lesson():
    path = f"{MOD}/15_evaluacion_retrieval.ipynb"
    nb = Notebook("Módulo 15 · Evaluación de embeddings y retrieval", colab_path=path)
    _b15_lesson1.part1(nb); _b15_lesson2.part2(nb); _b15_lesson3.part3(nb)
    nb.save(path)


def build_project():
    try:
        import _b15_project
    except ImportError:
        print("(proyecto 15 aún no escrito)"); return
    path = f"{MOD}/15_proyecto_evaluacion_retrieval.ipynb"
    nb = Notebook("Proyecto 15 · Banco de evaluación de Políglota", colab_path=path)
    _b15_project.build(nb)
    nb.save(path)


def write_support_files():
    os.makedirs(f"{MOD}/assets", exist_ok=True)
    open(f"{MOD}/assets/.gitkeep", "w").close()
    imports = "import re\nimport numpy as np\nfrom sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer\nfrom sklearn.decomposition import TruncatedSVD\n\n"
    with open(f"{MOD}/poliglota_eval.py", "w", encoding="utf-8") as f:
        f.write(EVAL_MODULE_HEADER + imports + METRICS_SRC + "\n\n" + STATS_SRC + "\n\n" + RETRIEVERS_SRC + "\n")
    open(f"{MOD}/README.md", "w", encoding="utf-8").write(README_15)
    print(f"OK {MOD}/poliglota_eval.py + README.md")


if __name__ == "__main__":
    os.makedirs(MOD, exist_ok=True)
    build_lesson(); build_project(); write_support_files()
