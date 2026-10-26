"""Construye el módulo 17 (lección + proyecto). Ejecutar desde la raíz del repo:
    python tokenization-embeddings-course/_tools/builders/build_17.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook
import _b17_lesson1, _b17_lesson2

COURSE = "tokenization-embeddings-course"
MOD = f"{COURSE}/17_interpretabilidad_geometria"


def build_lesson():
    path = f"{MOD}/17_interpretabilidad_geometria.ipynb"
    nb = Notebook("Módulo 17 · Interpretabilidad y geometría", colab_path=path, gpu=False)
    _b17_lesson1.part1(nb); _b17_lesson2.part2(nb)
    nb.save(path)


def build_project():
    try:
        import _b17_project
    except ImportError:
        print("(proyecto 17 aún no escrito)"); return
    path = f"{MOD}/17_proyecto_interpretabilidad_geometria.ipynb"
    nb = Notebook("Proyecto 17 · Interpretabilidad de Políglota (SAE)", colab_path=path, gpu=False)
    _b17_project.build(nb)
    nb.save(path)


def write_support_files():
    from _a6_readmes import README_17
    os.makedirs(f"{MOD}/assets", exist_ok=True)
    open(f"{MOD}/assets/.gitkeep", "w").close()
    open(f"{MOD}/README.md", "w", encoding="utf-8").write(README_17)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    os.makedirs(MOD, exist_ok=True)
    build_lesson(); build_project()
    try: write_support_files()
    except ImportError: print("(README_17 pendiente)")
