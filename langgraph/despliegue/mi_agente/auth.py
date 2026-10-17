"""Autenticación y control de acceso para la aplicación desplegada.

Se activa añadiendo esto a `langgraph.json` (ver `langgraph.produccion.json`):

    "auth": {
      "path": "./mi_agente/auth.py:auth",
      "disable_studio_auth": false
    }

Dos etapas, y conviene no confundirlas:

* **Autenticación** (`@auth.authenticate`): ¿quién eres? Corre como middleware en *todas*
  las peticiones. Devuelve el usuario o lanza un 401.
* **Autorización** (`@auth.on...`): ¿puedes hacer esto con este recurso? Devuelve un filtro
  de metadatos, o lanza un 403.

El servidor elige **un solo manejador** por petición: el más específico que encaje,
`(recurso, acción)` -> `(recurso, "*")` -> global. Si no hay ninguno, se permite.
"""

from __future__ import annotations

import os

from langgraph_sdk import Auth

auth = Auth()


# --------------------------------------------------------------------------------------
# Autenticación
# --------------------------------------------------------------------------------------
def _tokens_validos() -> dict[str, dict]:
    """Directorio de demostración.

    En producción esto es una llamada a tu proveedor de identidad (Auth0, Okta, Supabase,
    Cognito…) o la verificación de la firma de un JWT. Nunca una tabla en el código.
    """
    return {
        os.environ.get("TOKEN_DEMO_ANA", "token-ana"): {
            "identity": "u-ana",
            "display_name": "Ana",
            "permissions": ["threads:read", "threads:write"],
        },
        os.environ.get("TOKEN_DEMO_LUIS", "token-luis"): {
            "identity": "u-luis",
            "display_name": "Luis",
            "permissions": ["threads:read"],          # Luis solo lee
        },
    }


@auth.authenticate
async def autenticar(authorization: str | None) -> Auth.types.MinimalUserDict:
    """Valida la credencial y devuelve la identidad.

    El parámetro se pide **por nombre**: el servidor inyecta lo que declares. Están
    disponibles `request`, `path`, `method`, `path_params`, `query_params`, `headers`
    y `authorization`.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Falta el token")

    usuario = _tokens_validos().get(authorization.removeprefix("Bearer "))
    if usuario is None:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Token no válido")

    return {**usuario, "is_authenticated": True}


# --------------------------------------------------------------------------------------
# Autorización
# --------------------------------------------------------------------------------------
def _marcar_propietario(ctx: Auth.types.AuthContext, value: dict) -> dict:
    """Escribe el propietario en los metadatos y devuelve el filtro que lo exige.

    Las dos mitades son imprescindibles y se olvidan por separado:
      * sin escribir la metadata, el recurso nace sin dueño y el filtro no lo encuentra
        nunca (síntoma: "creo un hilo y luego no aparece en mi lista");
      * sin devolver el filtro, cualquiera lee los hilos de cualquiera.
    """
    metadatos = value.setdefault("metadata", {})
    metadatos["owner"] = ctx.user.identity
    return {"owner": ctx.user.identity}


@auth.on
async def denegar_lo_no_contemplado(ctx: Auth.types.AuthContext, value: dict):
    """Manejador global: todo lo que no tenga una regla específica se rechaza.

    Empezar por «denegar por defecto» y abrir lo necesario es lo contrario de lo que hace
    casi todo el mundo, y es lo correcto: cuando la plataforma añada un recurso nuevo,
    tu despliegue no lo expondrá por accidente.
    """
    raise Auth.exceptions.HTTPException(status_code=403, detail="Operación no permitida")


@auth.on.threads.create
async def crear_hilo(ctx: Auth.types.AuthContext, value: Auth.types.on.threads.create.value):
    if "threads:write" not in ctx.permissions:
        raise Auth.exceptions.HTTPException(status_code=403, detail="Sin permiso de escritura")
    return _marcar_propietario(ctx, value)


@auth.on.threads.create_run
async def crear_ejecucion(ctx: Auth.types.AuthContext, value):
    if "threads:write" not in ctx.permissions:
        raise Auth.exceptions.HTTPException(status_code=403, detail="Sin permiso de escritura")
    return _marcar_propietario(ctx, value)


@auth.on.threads.read
async def leer_hilo(ctx: Auth.types.AuthContext, value):
    # En lectura no hay metadata que escribir: basta con el filtro.
    return {"owner": ctx.user.identity}


@auth.on.threads.search
async def buscar_hilos(ctx: Auth.types.AuthContext, value):
    return {"owner": ctx.user.identity}


@auth.on.threads.delete
async def borrar_hilo(ctx: Auth.types.AuthContext, value):
    if "threads:write" not in ctx.permissions:
        raise Auth.exceptions.HTTPException(status_code=403, detail="Sin permiso de escritura")
    return {"owner": ctx.user.identity}


@auth.on.assistants.read
async def leer_assistants(ctx: Auth.types.AuthContext, value):
    """Los assistants son configuración compartida: todos los autenticados pueden leerlos."""
    return True


@auth.on.assistants.search
async def buscar_assistants(ctx: Auth.types.AuthContext, value):
    return True


# --------------------------------------------------------------------------------------
# Store: aquí NO se filtra por metadatos, se reescribe el namespace
# --------------------------------------------------------------------------------------
@auth.on.store
async def aislar_store(ctx: Auth.types.AuthContext, value: dict):
    """Fuerza que todo acceso al store cuelgue del namespace del usuario.

    El store es el único recurso que se protege de otra forma: en vez de devolver un
    filtro, se **reescribe el `namespace`** que venía en la petición. Así, dos usuarios
    que pidan la misma clave leen sitios distintos, sin que el código del agente tenga
    que saber nada.
    """
    namespace = value.get("namespace") or ()
    value["namespace"] = (ctx.user.identity, *namespace)
    return True
