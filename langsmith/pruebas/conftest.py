"""Utilidades compartidas por las pruebas del curso de LangSmith.

La regla es la misma que en el curso de LangGraph: **las pruebas no llaman a ningún
servicio ni a ningún modelo**. Aquí eso importa el doble, porque el servicio del que
habla el curso cuesta cuota. Una CI que gasta cuota se acaba desactivando.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))


@pytest.fixture(autouse=True)
def sin_servicio(monkeypatch):
    """Deja el entorno en modo local para TODAS las pruebas.

    Es `autouse` a propósito: si alguien ejecuta la suite con su clave en el entorno,
    no queremos que una prueba mande trazas de verdad. Las pruebas que quieran simular
    el modo en línea ponen la variable ellas, con `monkeypatch`.
    """
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")


@pytest.fixture
def con_servicio(monkeypatch):
    """Simula que hay clave, sin que exista ningún servicio detrás.

    Sirve para comprobar la *rama* en línea de `@online` —que ejecuta el cuerpo y que
    captura los errores— sin llamar a nadie.
    """
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_pt_de_mentira")
    return "lsv2_pt_de_mentira"
