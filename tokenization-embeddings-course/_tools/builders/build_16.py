"""Construye el módulo 16 (lección + proyecto). Ejecutar desde la raíz del repo:
    python tokenization-embeddings-course/_tools/builders/build_16.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook
import _b16_lesson1, _b16_lesson2

COURSE = "tokenization-embeddings-course"
MOD = f"{COURSE}/16_embeddings_multimodales"


def build_lesson():
    path = f"{MOD}/16_embeddings_multimodales.ipynb"
    nb = Notebook("Módulo 16 · Embeddings multimodales", colab_path=path, gpu=True)
    _b16_lesson1.part1(nb); _b16_lesson2.part2(nb)
    nb.save(path)


def build_project():
    try:
        import _b16_project
    except ImportError:
        print("(proyecto 16 aún no escrito)"); return
    path = f"{MOD}/16_proyecto_embeddings_multimodales.ipynb"
    nb = Notebook("Proyecto 16 · Políglota Visual", colab_path=path, gpu=True)
    _b16_project.build(nb)
    nb.save(path)


def write_support_files():
    from _a6_readmes import README_16
    os.makedirs(f"{MOD}/assets", exist_ok=True)
    open(f"{MOD}/assets/.gitkeep", "w").close()
    open(f"{MOD}/README.md", "w", encoding="utf-8").write(README_16)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    os.makedirs(MOD, exist_ok=True)
    build_lesson(); build_project()
    try: write_support_files()
    except ImportError: print("(README_16 pendiente)")
