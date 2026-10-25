"""Genera el módulo 18 (lección + proyecto + README): Producción.

Ejecutar desde la raíz del repo:  python tokenization-embeddings-course/_tools/builders/build_18.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import _a7_l18  # noqa: E402

COURSE = "tokenization-embeddings-course"
MOD = f"{COURSE}/18_produccion"
LESSON = f"{MOD}/18_produccion.ipynb"
PROJECT = f"{MOD}/18_proyecto_produccion.ipynb"


def main():
    os.makedirs(f"{MOD}/assets", exist_ok=True)
    open(f"{MOD}/assets/.gitkeep", "a").close()
    nb = Notebook("Módulo 18 · Producción", colab_path=LESSON)
    _a7_l18.lesson(nb)
    nb.save(LESSON)
    try:
        import _a7_p18
    except ImportError:
        print("(proyecto 18 aún no escrito)")
        return
    nbp = Notebook("Proyecto 18 · Servicio Políglota", colab_path=PROJECT)
    _a7_p18.project(nbp)
    nbp.save(PROJECT)
    with open(f"{MOD}/README.md", "w", encoding="utf-8") as f:
        f.write(_a7_p18.README)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    main()
