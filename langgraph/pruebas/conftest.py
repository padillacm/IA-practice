"""Utilidades compartidas por las pruebas del curso.

La idea central: **un grafo se prueba sin llamar a ningún modelo**. Los modelos falsos de
este fichero son deterministas, así que las pruebas son rápidas, gratuitas y no fallan un
martes porque el proveedor tuviera un mal día.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda


class ModeloGuionizado(BaseChatModel):
    """Modelo falso que devuelve respuestas de un guion, en orden.

    Es la herramienta básica para probar un grafo: fijas exactamente qué contesta el modelo
    en cada turno y compruebas que el grafo hace lo que debe con esa respuesta.
    """

    respuestas: list[AIMessage] = []
    llamadas: list[list[BaseMessage]] = []

    @property
    def _llm_type(self) -> str:
        return "guionizado"

    def _generate(self, messages, stop=None, run_manager: CallbackManagerForLLMRun | None = None,
                  **kwargs) -> ChatResult:
        self.llamadas.append(list(messages))
        indice = min(len(self.llamadas) - 1, len(self.respuestas) - 1)
        mensaje = self.respuestas[indice]
        return ChatResult(generations=[ChatGeneration(message=mensaje)])

    def bind_tools(self, tools: Sequence, **kwargs) -> Runnable:
        return self

    def with_structured_output(self, schema, **kwargs) -> Runnable:
        respuestas = self.respuestas
        contador = {"n": 0}

        def elegir(_entrada):
            indice = min(contador["n"], len(respuestas) - 1)
            contador["n"] += 1
            valor = respuestas[indice]
            # En las pruebas guardamos el objeto estructurado en additional_kwargs.
            return valor.additional_kwargs.get("estructurado", valor)

        return RunnableLambda(elegir)


def guionizar(*respuestas) -> ModeloGuionizado:
    """Crea un modelo que devolverá estas respuestas, una por llamada.

    Acepta cadenas (se convierten en AIMessage), AIMessage ya construidos, u objetos
    Pydantic (para `with_structured_output`).
    """
    mensajes = []
    for r in respuestas:
        if isinstance(r, AIMessage):
            mensajes.append(r)
        elif isinstance(r, str):
            mensajes.append(AIMessage(r))
        else:
            mensajes.append(AIMessage("", additional_kwargs={"estructurado": r}))
    return ModeloGuionizado(respuestas=mensajes)


def con_herramientas(nombre: str, argumentos: dict, id_llamada: str = "call_1") -> AIMessage:
    """Un AIMessage que pide una herramienta, para guionizar el bucle de un agente."""
    return AIMessage("", tool_calls=[{"name": nombre, "args": argumentos, "id": id_llamada}])


@pytest.fixture
def hilo():
    """Una configuración de hilo nueva por prueba, para que no se contaminen entre sí."""
    import uuid
    return {"configurable": {"thread_id": f"prueba-{uuid.uuid4().hex[:8]}"}}
