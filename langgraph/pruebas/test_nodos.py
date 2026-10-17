"""Nivel 1: los nodos son funciones puras. Se prueban como cualquier otra función.

Es el nivel más barato y el que más errores caza. Si tus nodos no se pueden probar así,
probablemente tengan demasiadas responsabilidades.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest


class EstadoTriaje(TypedDict):
    mensaje: str
    plan: str
    prioridad: str
    razones: Annotated[list[str], operator.add]


ESCALA = ["baja", "media", "alta", "critica"]
PALABRAS_URGENTES = ("caído", "parado", "bloquea", "urgente", "no autorizado")
PESO_PLAN = {"free": -1, "pro": 0, "business": 1, "enterprise": 2}


def nodo_prioridad(estado: EstadoTriaje) -> dict:
    """El nodo bajo prueba: calcula prioridad a partir del texto y del plan."""
    texto = estado["mensaje"].lower()
    puntos = 1 + sum(p in texto for p in PALABRAS_URGENTES) + PESO_PLAN.get(estado["plan"], 0)
    indice = max(0, min(len(ESCALA) - 1, puntos))
    return {"prioridad": ESCALA[indice],
            "razones": [f"puntos={puntos}, plan={estado['plan']}"]}


def test_devuelve_solo_las_claves_que_cambia():
    """El error número uno del principiante: devolver el estado entero."""
    salida = nodo_prioridad({"mensaje": "hola", "plan": "pro", "prioridad": "", "razones": []})
    assert set(salida) == {"prioridad", "razones"}
    assert "mensaje" not in salida, "el nodo no debe reenviar las claves que no toca"


def test_no_muta_la_entrada():
    """Mutar el estado recibido afecta al llamante. Nunca debe pasar."""
    entrada = {"mensaje": "el servicio está caído", "plan": "pro", "prioridad": "", "razones": ["previa"]}
    copia = {**entrada, "razones": list(entrada["razones"])}
    nodo_prioridad(entrada)
    assert entrada == copia, "el nodo ha mutado el estado que recibió"


@pytest.mark.parametrize(("mensaje", "plan", "esperado"), [
    ("consulta general sobre el plan", "free", "baja"),
    ("consulta general sobre el plan", "pro", "media"),
    ("el servicio está caído", "pro", "alta"),
    ("el servicio está caído y estamos parados", "enterprise", "critica"),
    # Este caso documenta una decisión discutible: un cliente enterprise sin ninguna
    # señal de urgencia acaba en "critica" solo por su plan. La prueba NO dice que
    # esté bien; dice que hoy es así. Si mañana se decide bajarlo, esta prueba falla
    # y obliga a cambiarla a conciencia. Eso es exactamente lo que debe hacer.
    ("todo bien", "enterprise", "critica"),
])
def test_tabla_de_prioridades(mensaje, plan, esperado):
    """La lógica de negocio, caso por caso. Barata de escribir y de mantener."""
    salida = nodo_prioridad({"mensaje": mensaje, "plan": plan, "prioridad": "", "razones": []})
    assert salida["prioridad"] == esperado


def test_prioridad_siempre_en_la_escala():
    """Propiedad invariante: pase lo que pase, el resultado es un valor válido."""
    for plan in ("free", "pro", "business", "enterprise", "desconocido"):
        for mensaje in ("", "caído parado bloquea urgente no autorizado" * 3):
            salida = nodo_prioridad({"mensaje": mensaje, "plan": plan, "prioridad": "", "razones": []})
            assert salida["prioridad"] in ESCALA
