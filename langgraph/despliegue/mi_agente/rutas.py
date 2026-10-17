"""Rutas HTTP propias montadas dentro del Agent Server.

El servidor de LangGraph trae `/threads`, `/runs`, `/assistants`, `/store`… pero casi
ninguna aplicación real vive solo de eso: hace falta una sonda de salud con tu semántica,
un endpoint de métricas, un webhook entrante, un `/version` para saber qué está desplegado.

En vez de levantar un segundo servicio al lado, se monta una app de Starlette (o FastAPI,
que es Starlette por dentro) dentro del mismo proceso:

    "http": { "app": "./mi_agente/rutas.py:app" }

Dos avisos que ahorran una tarde:

* Tus rutas **no pasan por la autenticación** del servidor salvo que pongas
  `"enable_custom_route_auth": true`. Por defecto quedan abiertas.
* El orden entre tu middleware y el de auth lo decide `"middleware_order"`. Por defecto es
  `middleware_first`: tu middleware corre **antes** de que se sepa quién es el usuario.
"""

from __future__ import annotations

import os
import time

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

ARRANQUE = time.time()


async def version(peticion):
    """Qué está desplegado exactamente. Lo primero que se pregunta en un incidente."""
    return JSONResponse({
        "servicio": "mi-agente",
        "version": os.environ.get("VERSION_DESPLIEGUE", "desarrollo"),
        "commit": os.environ.get("COMMIT_SHA", "desconocido"),
        "en_pie_desde_segundos": round(time.time() - ARRANQUE, 1),
    })


async def salud_profunda(peticion):
    """Sonda de salud CON semántica: comprueba que las dependencias reales responden.

    `/ok` del servidor dice "el proceso está vivo". Esto dice "el servicio puede trabajar",
    que es lo que le importa a un balanceador. Son cosas distintas y conviene tener las dos.
    """
    comprobaciones: dict[str, bool] = {}

    try:
        from mi_agente.herramientas import CATEGORIAS
        comprobaciones["datos_cargados"] = len(CATEGORIAS) > 0
    except Exception:
        comprobaciones["datos_cargados"] = False

    comprobaciones["clave_modelo_presente"] = bool(os.environ.get("OPENAI_API_KEY"))

    todo_bien = all(comprobaciones.values())
    return JSONResponse({"listo": todo_bien, "comprobaciones": comprobaciones},
                        status_code=200 if todo_bien else 503)


async def metricas(peticion):
    """Un stub en formato Prometheus, para enseñar dónde encaja."""
    lineas = [
        "# HELP mi_agente_en_pie_segundos Tiempo desde el arranque del proceso.",
        "# TYPE mi_agente_en_pie_segundos gauge",
        f"mi_agente_en_pie_segundos {time.time() - ARRANQUE:.1f}",
    ]
    return PlainTextResponse("\n".join(lineas) + "\n", media_type="text/plain; version=0.0.4")


app = Starlette(routes=[
    Route("/version", version, methods=["GET"]),
    Route("/salud", salud_profunda, methods=["GET"]),
    Route("/metricas", metricas, methods=["GET"]),
])
