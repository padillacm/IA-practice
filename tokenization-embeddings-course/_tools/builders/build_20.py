"""Genera el módulo 20 (lección + proyecto + README): Capstone · Políglota completo.

Ejecutar desde la raíz del repo:  python tokenization-embeddings-course/_tools/builders/build_20.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import _a7_l20  # noqa: E402

COURSE = "tokenization-embeddings-course"
MOD = f"{COURSE}/20_capstone"
LESSON = f"{MOD}/20_capstone.ipynb"
PROJECT = f"{MOD}/20_proyecto_capstone.ipynb"


def main():
    os.makedirs(f"{MOD}/assets", exist_ok=True)
    open(f"{MOD}/assets/.gitkeep", "a").close()
    nb = Notebook("Módulo 20 · Capstone: Políglota completo", colab_path=LESSON)
    _a7_l20.lesson(nb)
    nb.save(LESSON)
    try:
        import _a7_p20
    except ImportError:
        print("(proyecto 20 aún no escrito)")
        return
    nbp = Notebook("Proyecto 20 · Políglota completo", colab_path=PROJECT)
    _a7_p20.project(nbp)
    nbp.save(PROJECT)
    with open(f"{MOD}/README.md", "w", encoding="utf-8") as f:
        f.write(_a7_p20.README)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    main()
