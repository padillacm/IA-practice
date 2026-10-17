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
    for variable in ("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY",
                     "LANGSMITH_PROJECT", "LANGCHAIN_PROJECT"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    # `langsmith.expect` (notebook 08) está pensado para el plugin de pytest y registra
    # cada comprobación en LangSmith. Fuera del plugin lo intenta igualmente y sale a la
    # red. `LANGSMITH_TEST_TRACKING=false` es justo la variable para eso —la misma que
    # documenta el notebook 02— y la que hace que la suite no toque el servicio.
    monkeypatch.setenv("LANGSMITH_TEST_TRACKING", "false")

    # `get_env_var` está decorada con `lru_cache`, así que el valor que leyó una prueba
    # se lo encuentra la siguiente. Es la misma trampa que enseña el notebook 02, y aquí
    # provoca pruebas que pasan solas y fallan en la suite —dependientes del orden—,
    # que son las peores de diagnosticar. Se vacía antes y después de cada una.
    from langsmith import utils as lu

    lu.get_env_var.cache_clear()
    yield
    lu.get_env_var.cache_clear()


@pytest.fixture
def con_servicio(monkeypatch):
    """Simula que hay clave, sin que exista ningún servicio detrás.

    Sirve para comprobar la *rama* en línea de `@online` —que ejecuta el cuerpo y que
    captura los errores— sin llamar a nadie.
    """
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2_pt_de_mentira")
    return "lsv2_pt_de_mentira"


@pytest.fixture(autouse=True, scope="session")
def _sin_salida_a_la_red():
    """Corta la salida al servicio durante TODA la suite, y anota los intentos.

    El curso afirma que sus pruebas no tocan LangSmith. Esto es lo que lo sostiene, y
    no es paranoia: `langsmith.expect` salía a la red desde una prueba que se llamaba
    literalmente «funciona sin red». Sin este corte, una dependencia puede empezar a
    gastar la cuota de quien ejecute la suite con su clave puesta y nadie se entera.
    """
    import socket

    intentos: list[str] = []
    original = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        nombre = host.decode() if isinstance(host, bytes) else str(host)
        if "smith.langchain.com" in nombre or "api.openai.com" in nombre:
            intentos.append(nombre)
            raise OSError(f"la suite intentó salir a {nombre}: eso no debe pasar")
        return original(host, port, *args, **kwargs)

    socket.getaddrinfo = getaddrinfo
    yield
    socket.getaddrinfo = original
    assert not intentos, f"la suite salió a la red: {sorted(set(intentos))}"
