"""Modelo de chat falso, pero `BaseChatModel` de verdad.

Soporta `bind_tools`, `with_structured_output` y `usage_metadata`, que es lo que hace
falta para que los grafos del curso se ejecuten de principio a fin sin gastar cuota ni
necesitar clave. No sirve para evaluar calidad —siempre responde lo mismo— pero sí para
comprobar que **la estructura funciona**: que los nodos encajan, que los reducers acumulan
y que ningún notebook se ha roto al actualizar una dependencia.

Es la pieza que usa `_tools/ejecutar_notebooks.py`, y la que permite tener los notebooks
en la integración continua sin una clave de API.
"""
from __future__ import annotations

import typing
from collections.abc import Sequence
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import Runnable, RunnableLambda


def _instancia(modelo):
    return modelo(**{n: _valor_falso(c) for n, c in modelo.model_fields.items()})


def _de_tipo(ann):
    if ann is bool: return True
    if ann is float: return 0.85
    if ann is int: return 1
    if ann is str: return "texto de prueba"
    if hasattr(ann, "model_fields"): return _instancia(ann)
    if getattr(ann, "__origin__", None) is list:
        args = typing.get_args(ann)
        return [_de_tipo(args[0])] if args else ["elemento de prueba"]
    args = typing.get_args(ann)
    if args: return _de_tipo(args[0]) if not isinstance(args[0], str) else args[0]
    return "prueba"


def _valor_falso(campo):
    return _de_tipo(campo.annotation)


class FakeChat(BaseChatModel):
    """Responde siempre con texto; nunca pide herramientas (el bucle termina en un turno)."""

    respuesta: str = "respuesta de prueba del modelo falso"

    @property
    def _llm_type(self) -> str:
        return "fake-curso"

    def _generate(self, messages: list[BaseMessage], stop=None,
                  run_manager: CallbackManagerForLLMRun | None = None, **kwargs) -> ChatResult:
        m = AIMessage(
            self.respuesta,
            usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        )
        return ChatResult(generations=[ChatGeneration(message=m)])

    def bind_tools(self, tools: Sequence, **kwargs) -> Runnable:
        return self

    def with_structured_output(self, schema, **kwargs) -> Runnable:
        def construir(_):
            if hasattr(schema, "model_fields"):
                return schema(**{n: _valor_falso(c) for n, c in schema.model_fields.items()})
            return {}
        return RunnableLambda(construir)


def instalar():
    instalar_embeddings()
    import utils.curso as curso
    curso.llm = lambda *a, **k: FakeChat()
    import langchain.chat_models as cm
    cm.init_chat_model = lambda *a, **k: FakeChat()


class FakeEmbeddings(Embeddings):
    """Embeddings deterministas por hash: no valen para buscar, valen para probar estructura."""
    dims = 1536

    def _v(self, texto: str) -> list[float]:
        import hashlib, math
        h = hashlib.sha256(texto.lower().encode()).digest()
        base = [b / 255 for b in h] * (self.dims // len(h) + 1)
        v = base[: self.dims]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed_documents(self, textos): return [self._v(t) for t in textos]
    def embed_query(self, texto): return self._v(texto)
    async def aembed_documents(self, textos): return self.embed_documents(textos)
    async def aembed_query(self, texto): return self.embed_query(texto)


def instalar_embeddings():
    import langchain.embeddings as le
    le.init_embeddings = lambda *a, **k: FakeEmbeddings()


# --------------------------------------------------------------------------------------
# Aislamiento del servicio de LangSmith
# --------------------------------------------------------------------------------------
#
# Esta parte no existe en el curso de LangGraph, y aquí es el centro de la verificación.
# Los notebooks de este curso están escritos en dos modos: sin clave se ejecutan enteros
# en local, con clave se conectan al servicio. Afirmar que el modo local es de verdad
# local no se puede hacer leyendo el código — hay que quitar la red y ver qué pasa.

#: Anfitriones que este curso no debe tocar durante la verificación. Cada intento se
#: anota en `INTENTOS_DE_RED` y se rechaza.
ANFITRIONES_VETADOS = ("smith.langchain.com", "api.openai.com", "api.anthropic.com")

#: Lista de `(anfitrión, puerto)` que alguna celda intentó resolver. La consulta
#: `intentos_de_red()`, y el ejecutor la vuelca al final de cada notebook.
INTENTOS_DE_RED: list[tuple[str, object]] = []


class SalidaDeRedBloqueada(OSError):
    """Se intentó salir a un servicio externo durante la verificación offline."""


def aislar_langsmith() -> None:
    """Deja el proceso en el estado «sin clave y sin red», que es el modo verificable.

    Hace dos cosas, y las dos importan:

    1. **Vacía las variables de la clave** y pone `LANGSMITH_TRACING=false`, para que
       `utils.curso.init()` tome la rama local. Sin esto, una clave que estuviera en el
       entorno de quien ejecuta la CI mandaría trazas de verdad y gastaría cuota.
    2. **Corta la resolución de nombres** de los anfitriones vetados. Es más fuerte que
       lo anterior: aunque un notebook construyera un `Client()` a mano, no saldría.

    Advertencia honesta sobre el punto 2: el SDK de LangSmith **se traga los errores de
    red a propósito** —el envío va en un hilo de fondo y nunca debe tumbar tu aplicación,
    que es justo lo que cuenta el notebook 03—. Así que bloquear la red no basta para que
    un notebook falle si intenta salir: por eso también se anotan los intentos, y el
    ejecutor los reporta. El bloqueo evita el gasto; la anotación es la que informa.
    """
    import os
    import socket

    for variable in ("LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"):
        os.environ.pop(variable, None)
    os.environ["LANGSMITH_TRACING"] = "false"
    os.environ["LANGCHAIN_TRACING_V2"] = "false"

    if getattr(socket, "_curso_langsmith_aislado", False):
        return

    original = socket.getaddrinfo

    def getaddrinfo(host, port, *args, **kwargs):
        nombre = host.decode() if isinstance(host, bytes) else str(host)
        if any(v in nombre for v in ANFITRIONES_VETADOS):
            INTENTOS_DE_RED.append((nombre, port))
            raise SalidaDeRedBloqueada(
                f"verificación offline: conexión a {nombre}:{port} bloqueada a propósito"
            )
        return original(host, port, *args, **kwargs)

    socket.getaddrinfo = getaddrinfo
    socket._curso_langsmith_aislado = True


def intentos_de_red() -> list[tuple[str, object]]:
    """Los intentos de salida bloqueados desde que se llamó a `aislar_langsmith()`."""
    return list(INTENTOS_DE_RED)
