"""Piezas de recuperación construidas en el notebook 14, empaquetadas para reutilizarlas.

No hay nada aquí que no se explique paso a paso en `05_rag/14_rag_agentico.ipynb`. Vive en
un módulo para que el proyecto P5 no tenga que repetir cien líneas de fontanería y pueda
centrarse en el grafo y en la evaluación.

Todo lo de este fichero es **determinista y sin coste**: trocear, tokenizar, BM25 y la fusión
de rangos no llaman a ningún modelo. Los embeddings (que sí cuestan) se construyen en los
notebooks, a la vista.
"""

from __future__ import annotations

import math
import pathlib
import re
from collections import defaultdict
from typing import Any, Iterable

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CORPUS = RAIZ / "data" / "kb"

#: Fragmentos por debajo de este tamaño son ruido (una cabecera suelta, una línea en blanco).
MINIMO_CARACTERES = 120


def _documento():
    from langchain_core.documents import Document
    return Document


def cargar_fragmentos(
    *,
    tamano: int = 1200,
    solape: int = 150,
    minimo: int = MINIMO_CARACTERES,
    carpeta: pathlib.Path | None = None,
) -> list[Any]:
    """Trocea el corpus de `data/kb/` en fragmentos con metadatos de procedencia.

    Estrategia en dos pasos: primero se corta por cabeceras de Markdown (para que cada
    fragmento pertenezca a una sección y podamos citarla), y después se subdivide lo que
    siga siendo demasiado largo, respetando los límites de bloque de código.
    """
    from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

    Document = _documento()
    carpeta = carpeta or CORPUS
    ficheros = sorted(carpeta.glob("*.md"))
    if not ficheros:
        raise FileNotFoundError(f"El corpus {carpeta} está vacío. Ejecuta _tools/preparar_kb.py")

    por_cabecera = MarkdownHeaderTextSplitter(
        [("#", "titulo"), ("##", "seccion"), ("###", "subseccion")], strip_headers=False
    )
    por_tamano = RecursiveCharacterTextSplitter(
        chunk_size=tamano,
        chunk_overlap=solape,
        # El orden importa: partimos antes por secciones que por líneas, y evitamos
        # cortar un bloque de código por la mitad siempre que se pueda.
        separators=["\n## ", "\n### ", "\n```", "\n\n", "\n", " "],
    )

    fragmentos: list[Any] = []
    for fichero in ficheros:
        texto = re.sub(r"^<!--.*?-->\n", "", fichero.read_text(encoding="utf-8"), flags=re.S)
        for seccion in por_cabecera.split_text(texto):
            for trozo in por_tamano.split_text(seccion.page_content):
                if len(trozo.strip()) < minimo:
                    continue
                fragmentos.append(Document(
                    page_content=trozo,
                    metadata={
                        "fuente": fichero.stem,
                        "id": f"{fichero.stem}#{len(fragmentos)}",
                        **seccion.metadata,
                    },
                ))
    return fragmentos


def tokenizar(texto: str) -> list[str]:
    """Tokenizador léxico simple, válido para español e inglés."""
    return re.findall(r"[a-z0-9áéíóúüñ_]+", texto.lower())


class RecuperadorLexico:
    """BM25 sobre los fragmentos. Encuentra coincidencias exactas de términos raros.

    Es el complemento natural del recuperador vectorial: uno entiende el significado y el
    otro encuentra `InvalidUpdateError` cuando escribes `InvalidUpdateError`.
    """

    def __init__(self, fragmentos: list[Any]) -> None:
        from rank_bm25 import BM25Okapi

        self.fragmentos = fragmentos
        self._bm25 = BM25Okapi([tokenizar(d.page_content) for d in fragmentos])

    def buscar(self, consulta: str, k: int = 5) -> list[tuple[Any, float]]:
        puntuaciones = self._bm25.get_scores(tokenizar(consulta))
        mejores = sorted(range(len(puntuaciones)), key=lambda i: puntuaciones[i], reverse=True)[:k]
        return [(self.fragmentos[i], float(puntuaciones[i])) for i in mejores
                if puntuaciones[i] > 0]


def fusion_rrf(listas: Iterable[list[Any]], k: int = 60, limite: int = 6) -> list[Any]:
    """Reciprocal Rank Fusion: combina varios rankings usando solo las POSICIONES.

    La gracia es que no hay que normalizar puntuaciones entre sistemas que no son
    comparables (una similitud coseno de 0,82 y un BM25 de 13,3 no viven en la misma escala).
    Cada documento suma `1 / (k + posición)` por cada lista donde aparece, así que estar
    razonablemente arriba en dos rankings vale más que ser el primero en uno solo.

    `k=60` es el valor del artículo original (Cormack et al., 2009) y funciona bien;
    subirlo aplana las diferencias entre posiciones, bajarlo las exagera.
    """
    puntos: dict[str, float] = defaultdict(float)
    documentos: dict[str, Any] = {}

    for lista in listas:
        for posicion, doc in enumerate(lista, start=1):
            clave = doc.metadata.get("id") or doc.page_content[:120]
            puntos[clave] += 1.0 / (k + posicion)
            documentos.setdefault(clave, doc)

    ordenados = sorted(puntos.items(), key=lambda kv: kv[1], reverse=True)
    return [documentos[clave] for clave, _ in ordenados[:limite]]


def formatear_contexto(documentos: list[Any], *, maximo_caracteres: int = 6000) -> str:
    """Convierte fragmentos en un bloque de contexto citable y acotado.

    Cada fragmento va numerado para que el modelo pueda citar `[1]`, `[2]`... y para que
    después podamos comprobar que las citas existen.
    """
    partes, total = [], 0
    for i, doc in enumerate(documentos, start=1):
        cabecera = f"[{i}] fuente: {doc.metadata.get('fuente', '?')}"
        if doc.metadata.get("seccion"):
            cabecera += f" — sección: {doc.metadata['seccion']}"
        bloque = f"{cabecera}\n{doc.page_content.strip()}"
        if total + len(bloque) > maximo_caracteres:
            partes.append(f"[...] {len(documentos) - i + 1} fragmentos más, omitidos por espacio")
            break
        partes.append(bloque)
        total += len(bloque)
    return "\n\n---\n\n".join(partes)


def cobertura_lexica(respuesta: str, contexto: str) -> float:
    """Fracción de los términos poco comunes de la respuesta que aparecen en el contexto.

    Es un detector de alucinaciones barato y determinista: no perfecto, pero sin coste y sin
    opinión. Una respuesta con cobertura baja está diciendo cosas que no estaban en las
    fuentes recuperadas.
    """
    vocabulario_contexto = set(tokenizar(contexto))
    terminos = [t for t in set(tokenizar(respuesta)) if len(t) > 5]
    if not terminos:
        return 1.0
    return sum(t in vocabulario_contexto for t in terminos) / len(terminos)
