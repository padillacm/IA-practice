"""Esquemas de estado y de contexto del agente."""

from __future__ import annotations

import operator
from dataclasses import dataclass
from typing import Annotated

from langgraph.graph import MessagesState


class EstadoSoporte(MessagesState):
    """Estado del agente. `messages` viene de MessagesState."""

    #: Traza de decisiones, para auditoría. Reducer acumulador porque varios nodos escriben.
    bitacora: Annotated[list[str], operator.add]
    #: Número de consultas a herramientas, para vigilar el coste.
    consultas: Annotated[int, operator.add]


@dataclass
class ContextoPeticion:
    """Datos de la petición: los fija quien llama y el grafo no los modifica.

    Van aquí y no en el estado porque no se persisten en cada checkpoint y porque
    ningún nodo debería poder cambiarlos.
    """

    id_usuario: str = "anonimo"
    plan: str = "free"
    idioma: str = "es"
