"""Genera el módulo 19 (lección + proyecto + README): Playbook de élite.

Ejecutar desde la raíz del repo:  python tokenization-embeddings-course/_tools/builders/build_19.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from nbbuild import Notebook  # noqa: E402
import _a7_l19  # noqa: E402

COURSE = "tokenization-embeddings-course"
MOD = f"{COURSE}/19_playbook_elite"
LESSON = f"{MOD}/19_playbook_elite.ipynb"
PROJECT = f"{MOD}/19_proyecto_playbook_elite.ipynb"


def main():
    os.makedirs(f"{MOD}/assets", exist_ok=True)
    open(f"{MOD}/assets/.gitkeep", "a").close()
    nb = Notebook("Módulo 19 · Playbook de élite", colab_path=LESSON)
    _a7_l19.lesson(nb)
    nb.save(LESSON)
    try:
        import _a7_p19
    except ImportError:
        print("(proyecto 19 aún no escrito)")
        return
    nbp = Notebook("Proyecto 19 · Tres casos de system design", colab_path=PROJECT)
    _a7_p19.project(nbp)
    nbp.save(PROJECT)
    with open(f"{MOD}/README.md", "w", encoding="utf-8") as f:
        f.write(_a7_p19.README)
    print(f"OK {MOD}/README.md")


if __name__ == "__main__":
    main()
