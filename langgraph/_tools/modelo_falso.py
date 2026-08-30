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
