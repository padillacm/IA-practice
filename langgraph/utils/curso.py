"""Utilidades transversales del curso de LangGraph.

Se importa desde cualquier notebook con el arranque estándar de tres líneas:

    import sys, pathlib
    sys.path.insert(0, str(next(p for p in [pathlib.Path.cwd(), *pathlib.Path.cwd().parents]
                                if (p / "utils" / "curso.py").exists())))
    from utils.curso import init, llm, mostrar_grafo
"""

from __future__ import annotations

import os
import pathlib
import textwrap
from importlib import metadata
from typing import Any

# --------------------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------------------

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data"

#: Paquetes cuya versión se reporta en `init()`. El curso está escrito y verificado
#: contra estas versiones mínimas.
VERSIONES_MINIMAS = {
    "langgraph": "1.0.0",
    "langchain": "1.0.0",
    "langchain-core": "1.0.0",
    "langchain-openai": "1.0.0",
}

#: Modelo por defecto. Barato, rápido y con tool-calling fiable: suficiente para
#: todo el curso. Súbelo a un modelo mayor solo en los proyectos si quieres.
MODELO_POR_DEFECTO = os.environ.get("LANGGRAPH_CURSO_MODELO", "gpt-4o-mini")


def ruta_datos(nombre: str) -> pathlib.Path:
    """Devuelve la ruta a un fichero de `langgraph/data/`, validando que exista."""
    p = DATOS / nombre
    if not p.exists():
        raise FileNotFoundError(
            f"No encuentro {p}.\n"
            "Ejecuta desde la raíz del curso:  python utils/datos.py --descargar"
        )
    return p


# --------------------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------------------


def _cargar_dotenv() -> pathlib.Path | None:
    """Carga `langgraph/.env` sin depender de python-dotenv si no está instalado."""
    env = RAIZ / ".env"
    if not env.exists():
        return None
    try:
        from dotenv import load_dotenv

        load_dotenv(env, override=False)
    except ImportError:  # respaldo mínimo: KEY=VALOR por línea
        for linea in env.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, _, valor = linea.partition("=")
            os.environ.setdefault(clave.strip(), valor.strip().strip("'\""))
    return env


def _version(paquete: str) -> str | None:
    try:
        return metadata.version(paquete)
    except metadata.PackageNotFoundError:
        return None


def _tupla(v: str) -> tuple[int, ...]:
    partes: list[int] = []
    for trozo in v.split(".")[:3]:
        num = "".join(c for c in trozo if c.isdigit())
        partes.append(int(num) if num else 0)
    return tuple(partes)


def init(*, trazas: bool = True, proyecto: str = "curso-langgraph", silencioso: bool = False) -> dict[str, Any]:
    """Prepara el entorno del notebook y devuelve un diagnóstico.

    - Carga `langgraph/.env`.
    - Activa el trazado en LangSmith si hay `LANGSMITH_API_KEY` (opcional pero
      muy recomendable: sin trazas, depurar un grafo es adivinar).
    - Comprueba versiones y la presencia de `OPENAI_API_KEY`.
    """
    env = _cargar_dotenv()

    if trazas and os.environ.get("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGSMITH_PROJECT", proyecto)

    info: dict[str, Any] = {
        "raiz": RAIZ,
        "env": env,
        "openai_api_key": bool(os.environ.get("OPENAI_API_KEY")),
        "langsmith": os.environ.get("LANGSMITH_TRACING") == "true",
        "modelo": MODELO_POR_DEFECTO,
        "versiones": {p: _version(p) for p in VERSIONES_MINIMAS},
    }

    if silencioso:
        return info

    print("Entorno del curso de LangGraph")
    print("-" * 60)
    print(f"  raíz del curso : {RAIZ}")
    print(f"  .env           : {env if env else 'no encontrado (copia .env.example a .env)'}")
    for paquete, minima in VERSIONES_MINIMAS.items():
        actual = info["versiones"][paquete]
        if actual is None:
            estado = "FALTA  -> pip install -r requirements.txt"
        elif _tupla(actual) < _tupla(minima):
            estado = f"ANTIGUA (se requiere >= {minima})"
        else:
            estado = "ok"
        print(f"  {paquete:<16}: {actual or '-':<10} {estado}")
    print(f"  OPENAI_API_KEY : {'presente' if info['openai_api_key'] else 'AUSENTE -> los notebooks fallarán'}")
    print(f"  LangSmith      : {'trazando en ' + os.environ.get('LANGSMITH_PROJECT', '?') if info['langsmith'] else 'desactivado'}")
    print("-" * 60)
    return info


# --------------------------------------------------------------------------------------
# Modelos
# --------------------------------------------------------------------------------------


def llm(modelo: str | None = None, *, temperatura: float = 0.0, **kwargs: Any):
    """Devuelve un `ChatOpenAI` configurado con los valores del curso.

    `temperatura=0` por defecto: en un grafo con enrutado, el no-determinismo del
    modelo se propaga a las aristas y hace irreproducible el ejercicio.
    """
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "Falta OPENAI_API_KEY.\n"
            "  1) copia langgraph/.env.example a langgraph/.env\n"
            "  2) escribe tu clave de https://platform.openai.com/api-keys\n"
            "  3) reinicia el kernel y vuelve a ejecutar init()"
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=modelo or MODELO_POR_DEFECTO, temperature=temperatura, **kwargs)


# --------------------------------------------------------------------------------------
# Visualización de grafos
# --------------------------------------------------------------------------------------


def mostrar_grafo(grafo: Any, *, xray: bool | int = False, png: bool = True) -> Any:
    """Dibuja un grafo compilado en el notebook.

    Intenta PNG (usa el servicio mermaid.ink, requiere red). Si falla, cae a la
    fuente Mermaid en texto, que siempre funciona y es igual de informativa.
    `xray=True` expande los subgrafos.
    """
    try:
        dibujable = grafo.get_graph(xray=xray)
    except TypeError:  # objetos sin soporte de xray
        dibujable = grafo.get_graph()

    if png:
        try:
            from IPython.display import Image, display

            display(Image(dibujable.draw_mermaid_png()))
            return None
        except Exception as exc:  # red caída, mermaid.ink no disponible, sin IPython...
            print(f"[aviso] no se pudo renderizar el PNG ({type(exc).__name__}); muestro Mermaid en texto\n")

    fuente = dibujable.draw_mermaid()
    print(fuente)
    return fuente


# --------------------------------------------------------------------------------------
# Impresión legible
# --------------------------------------------------------------------------------------


def separador(titulo: str = "", ancho: int = 78, caracter: str = "=") -> None:
    if titulo:
        relleno = max(0, ancho - len(titulo) - 2)
        print(f"{caracter * 3} {titulo} {caracter * (relleno - 3)}")
    else:
        print(caracter * ancho)


def mostrar_mensajes(mensajes: Any, *, maximo: int | None = None, ancho: int = 100) -> None:
    """Imprime una lista de mensajes de LangChain de forma compacta y legible.

    `mensajes` puede ser la lista o el dict de estado completo (se busca la clave
    "messages"). Muestra las llamadas a herramientas, que es lo que de verdad
    quieres ver al depurar un agente.
    """
    if isinstance(mensajes, dict):
        mensajes = mensajes.get("messages", [])
    lista = list(mensajes)
    if maximo is not None:
        lista = lista[-maximo:]

    etiquetas = {"human": "USUARIO", "ai": "IA", "tool": "HERRAMIENTA", "system": "SISTEMA"}
    for m in lista:
        tipo = getattr(m, "type", "?")
        cabecera = etiquetas.get(tipo, tipo.upper())
        nombre = getattr(m, "name", None)
        if nombre:
            cabecera += f" ({nombre})"
        print(f"\n[{cabecera}]")

        contenido = getattr(m, "text", None)
        contenido = contenido() if callable(contenido) else contenido
        if contenido is None:
            contenido = getattr(m, "content", "")
        if isinstance(contenido, list):  # bloques de contenido estructurado
            contenido = " ".join(b.get("text", "") for b in contenido if isinstance(b, dict))
        if contenido:
            print(textwrap.indent(textwrap.fill(str(contenido), width=ancho), "  "))

        for tc in getattr(m, "tool_calls", None) or []:
            print(f"  -> llamada a herramienta: {tc['name']}({tc['args']})")


def resumen_estado(estado: Any, *, omitir: tuple[str, ...] = ("messages",)) -> None:
    """Imprime las claves de un estado (o snapshot) sin volcar el historial entero."""
    valores = getattr(estado, "values", estado)
    for clave, valor in valores.items():
        if clave in omitir:
            print(f"  {clave}: <{len(valor)} mensajes>" if hasattr(valor, "__len__") else f"  {clave}: ...")
            continue
        texto = repr(valor)
        print(f"  {clave}: {texto[:200]}{'...' if len(texto) > 200 else ''}")
