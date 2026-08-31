"""Utilidades transversales del curso de LangSmith.

Se importa desde cualquier notebook con el arranque estándar de tres líneas, el mismo
que el curso de LangGraph:

    import sys, pathlib
    sys.path.insert(0, str(next(p for p in [pathlib.Path.cwd(), *pathlib.Path.cwd().parents]
                                if (p / "utils" / "curso.py").exists())))
    from utils.curso import init, online, cliente

La pieza que distingue a este módulo del de LangGraph es `online`. Este curso habla de
un servicio en la nube, y se escribió en un entorno que no lo alcanza. En vez de fingir
lo contrario, cada notebook funciona en dos modos y `online` es la frontera entre ambos:
lo que está fuera se ejecuta siempre; lo que está dentro solo si hay clave.
"""

from __future__ import annotations

import contextlib
import os
import pathlib
import textwrap
import traceback
from importlib import metadata
from typing import Any, Callable

# --------------------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------------------

RAIZ = pathlib.Path(__file__).resolve().parent.parent

#: Los datos se comparten con el curso de LangGraph, y eso es intencionado: los mismos
#: 400 tickets etiquetados recorren los dos cursos, así que los experimentos de aquí se
#: pueden comparar con los evaluadores de allí. Se busca primero en local por si quieres
#: añadir los tuyos sin tocar el otro curso.
DIRECTORIOS_DE_DATOS = (RAIZ / "data", RAIZ.parent / "langgraph" / "data")

#: Versiones contra las que está escrito y verificado el curso.
VERSIONES_MINIMAS = {
    "langsmith": "0.11.0",
    "langchain": "1.3.0",
    "langchain-core": "1.6.0",
    "langgraph": "1.2.0",
}

#: Modelo por defecto, el mismo que el curso de LangGraph.
MODELO_POR_DEFECTO = os.environ.get("LANGSMITH_CURSO_MODELO", "gpt-4o-mini")

#: Proyecto de LangSmith donde caen las trazas del curso. Aparte del tuyo a propósito:
#: un curso que ensucia tu proyecto de trabajo se acaba haciendo con el trazado apagado.
PROYECTO_POR_DEFECTO = os.environ.get("LANGSMITH_PROJECT", "curso-langsmith")


def ruta_datos(nombre: str) -> pathlib.Path:
    """Devuelve la ruta a un fichero de datos, buscando en los dos cursos."""
    for directorio in DIRECTORIOS_DE_DATOS:
        candidato = directorio / nombre
        if candidato.exists():
            return candidato
    buscados = "\n".join(f"    {d / nombre}" for d in DIRECTORIOS_DE_DATOS)
    raise FileNotFoundError(
        f"No encuentro «{nombre}». Lo he buscado en:\n{buscados}\n"
        "Los datos vienen del curso de LangGraph; comprueba que `../langgraph/data/` existe."
    )


# --------------------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------------------


def _cargar_dotenv() -> pathlib.Path | None:
    """Carga `langsmith/.env` sin depender de python-dotenv si no está instalado."""
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


def hay_servicio() -> bool:
    """¿Hay clave de LangSmith en el entorno?

    Es la única pregunta que decide el modo del notebook. No comprueba que la clave
    sea válida ni que haya red: eso lo descubre la primera llamada, y `online` lo
    reporta sin tumbar el notebook.
    """
    return bool(os.environ.get("LANGSMITH_API_KEY") or os.environ.get("LANGCHAIN_API_KEY"))


def init(
    *,
    trazas: bool = True,
    proyecto: str | None = None,
    silencioso: bool = False,
) -> dict[str, Any]:
    """Prepara el entorno del notebook y dice en qué modo estás.

    - Carga `langsmith/.env`.
    - Activa el trazado **solo si hay clave**. Sin ella deja `LANGSMITH_TRACING=false`
      explícitamente, en vez de dejarlo sin definir: así el SDK no intenta salir y no
      llenas la salida de avisos de conexión.
    - Comprueba versiones.
    """
    env = _cargar_dotenv()
    proyecto = proyecto or PROYECTO_POR_DEFECTO
    conectado = trazas and hay_servicio()

    if conectado:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ.setdefault("LANGSMITH_PROJECT", proyecto)
    else:
        os.environ["LANGSMITH_TRACING"] = "false"

    info: dict[str, Any] = {
        "raiz": RAIZ,
        "env": env,
        "modo": "en línea" if conectado else "local",
        "conectado": conectado,
        "proyecto": os.environ.get("LANGSMITH_PROJECT") if conectado else None,
        "endpoint": os.environ.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        "openai_api_key": bool(os.environ.get("OPENAI_API_KEY")),
        "modelo": MODELO_POR_DEFECTO,
        "versiones": {p: _version(p) for p in VERSIONES_MINIMAS},
    }

    if silencioso:
        return info

    print("Entorno del curso de LangSmith")
    print("-" * 70)
    print(f"  raíz del curso : {RAIZ}")
    print(f"  .env           : {env if env else 'no encontrado (copia .env.example a .env)'}")
    for paquete, minima in VERSIONES_MINIMAS.items():
        actual = info["versiones"][paquete]
        if actual is None:
            estado = "FALTA  -> uv sync"
        elif _tupla(actual) < _tupla(minima):
            estado = f"ANTIGUA (se requiere >= {minima})"
        else:
            estado = "ok"
        print(f"  {paquete:<16}: {actual or '-':<10} {estado}")
    print(f"  OPENAI_API_KEY : {'presente' if info['openai_api_key'] else 'ausente'}")
    print("-" * 70)
    if conectado:
        print(f"  MODO EN LÍNEA · trazas al proyecto «{info['proyecto']}»")
        print("  Las celdas marcadas con @online se ejecutan y consumen cuota.")
    else:
        print("  MODO LOCAL · sin clave de LangSmith")
        print("  Todo lo que no necesita servicio se ejecuta igual. Las celdas marcadas")
        print("  con @online se saltan y dicen qué habrían hecho.")
    print("-" * 70)
    return info


# --------------------------------------------------------------------------------------
# El mecanismo de los dos modos
# --------------------------------------------------------------------------------------

#: Trazas estimadas que se han consumido en esta sesión, según lo declarado por `online`.
#: No lo mide el servicio: lo declara cada celda. Sirve para no llevarse sorpresas.
_TRAZAS_CONSUMIDAS = 0


def trazas_consumidas() -> int:
    """Trazas estimadas consumidas por las celdas `@online` ejecutadas en esta sesión."""
    return _TRAZAS_CONSUMIDAS


def online(titulo: str, *, trazas: int = 1) -> Callable[[Callable[[], Any]], Any]:
    """Marca un bloque que **necesita el servicio de LangSmith**, y lo ejecuta o lo salta.

    Se usa como decorador sobre una función sin argumentos, que se ejecuta en el acto:

        @online("Crear el dataset de tickets", trazas=0)
        def _():
            ds = cliente().create_dataset(dataset_name="tickets-curso")
            print(ds.id)

    Sin clave, el bloque **no se ejecuta** y se imprime qué habría hecho. Con clave se
    ejecuta y se anota el consumo declarado en `trazas`.

    Los errores del bloque se capturan y se imprimen, pero **no se propagan**. Es una
    decisión deliberada y conviene entender por qué: el curso está escrito sin poder
    ejecutar la parte en línea, así que si una llamada tiene un fallo, lo mejor que
    puede pasar es que lo veas señalado y sigas con el resto del notebook, en vez de
    quedarte con el kernel a medias. Si te ocurre, es un error del material: anótalo.

    Devuelve lo que devuelva el bloque (o `None` si se saltó o falló), así que también
    sirve para capturar un valor:

        dataset = online("Crear el dataset")(lambda: cliente().create_dataset(...))
    """
    global _TRAZAS_CONSUMIDAS

    def decorador(funcion: Callable[[], Any]) -> Any:
        global _TRAZAS_CONSUMIDAS
        if not hay_servicio():
            print(f"[modo local] se salta: {titulo}")
            print("              necesita LANGSMITH_API_KEY en tu .env")
            if trazas:
                print(f"              consumiría ~{trazas} traza(s)")
            return None
        etiqueta = f" (~{trazas} traza(s))" if trazas else ""
        print(f"[en línea] {titulo}{etiqueta}")
        try:
            resultado = funcion()
        except Exception:
            print(f"[EN LÍNEA · FALLO] {titulo}")
            print(textwrap.indent(traceback.format_exc(limit=3), "    "))
            print("    El notebook sigue. Esto es un error del material: repórtalo.")
            return None
        _TRAZAS_CONSUMIDAS += trazas
        return resultado

    return decorador


def cliente(**kwargs: Any):
    """Devuelve un `langsmith.Client` con la configuración del curso.

    Solo tiene sentido dentro de un bloque `@online`: sin clave, construirlo funciona
    pero cualquier llamada falla.
    """
    from langsmith import Client

    return Client(**kwargs)


# --------------------------------------------------------------------------------------
# Presupuesto de trazas
# --------------------------------------------------------------------------------------

#: Cuota mensual del plan Developer sin método de pago, a fecha de escritura del curso.
CUOTA_MENSUAL_DEVELOPER = 5_000


def presupuesto_de_trazas(
    *,
    ejemplos: int,
    repeticiones: int = 1,
    evaluadores_llm: int = 0,
    tope: int | None = None,
    etiqueta: str = "experimento",
) -> int:
    """Estima cuántas trazas va a costar un experimento **antes** de lanzarlo.

    La cuenta es la que sorprende a todo el mundo la primera vez:

        trazas = ejemplos × repeticiones × (1 + evaluadores_llm)

    Cada ejecución del *target* es una traza. Y cada evaluador que sea un juez LLM es
    **otra llamada trazada** por ejemplo, no un extra gratuito de la primera. Un
    experimento de 50 ejemplos, 3 repeticiones y 2 jueces son 450 trazas: casi el 10 %
    de la cuota mensual del plan gratuito en una sola celda.

    Devuelve la estimación e imprime el desglose. Si `tope` está puesto y se supera,
    lanza `ValueError` en vez de dejarte lanzarlo.
    """
    por_ejemplo = 1 + evaluadores_llm
    total = ejemplos * repeticiones * por_ejemplo
    porcentaje = 100 * total / CUOTA_MENSUAL_DEVELOPER

    print(f"Presupuesto de «{etiqueta}»")
    print(f"  {ejemplos} ejemplos × {repeticiones} repetición(es) × {por_ejemplo} traza(s) por ejemplo")
    print(f"  = {total} trazas  ({porcentaje:.1f} % de las {CUOTA_MENSUAL_DEVELOPER:,} del plan Developer)")
    if evaluadores_llm:
        print(f"  ({evaluadores_llm} de esas trazas por ejemplo son los jueces LLM, que también cuentan)")

    if tope is not None and total > tope:
        raise ValueError(
            f"«{etiqueta}» costaría {total} trazas y tu tope es {tope}. "
            "Baja el número de ejemplos o de repeticiones, o sube el tope a conciencia."
        )
    return total


# --------------------------------------------------------------------------------------
# Modelos
# --------------------------------------------------------------------------------------


def llm(modelo: str | None = None, *, temperatura: float = 0.0, **kwargs: Any):
    """Devuelve un `ChatOpenAI` configurado con los valores del curso."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "Falta OPENAI_API_KEY.\n"
            "  1) copia langsmith/.env.example a langsmith/.env\n"
            "  2) escribe tu clave de https://platform.openai.com/api-keys\n"
            "  3) reinicia el kernel y vuelve a ejecutar init()"
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=modelo or MODELO_POR_DEFECTO, temperature=temperatura, **kwargs)


# --------------------------------------------------------------------------------------
# Impresión legible
# --------------------------------------------------------------------------------------


def separador(titulo: str = "", ancho: int = 78, caracter: str = "=") -> None:
    if titulo:
        relleno = max(0, ancho - len(titulo) - 2)
        print(f"{caracter * 3} {titulo} {caracter * (relleno - 3)}")
    else:
        print(caracter * ancho)


def arbol_de_runs(raiz: Any, *, sangria: int = 0) -> None:
    """Dibuja la jerarquía de un `RunTree` (o de un `Run` con `child_runs`).

    Sirve para ver a mano lo que la interfaz de LangSmith dibuja por ti, que es la
    forma de entender que una traza es un árbol y no una lista.
    """
    nombre = getattr(raiz, "name", "?")
    tipo = getattr(raiz, "run_type", "?")
    print(f"{' ' * sangria}├─ {nombre}  [{tipo}]")
    for hijo in getattr(raiz, "child_runs", None) or []:
        arbol_de_runs(hijo, sangria=sangria + 3)


# --------------------------------------------------------------------------------------
# Trazas en local, de verdad
# --------------------------------------------------------------------------------------
#
# Este es el hallazgo que hace posible el modo local del curso, y no está en los
# tutoriales: `tracing_context` acepta `enabled="local"` además de `True`/`False`.
# Con `"local"` el SDK **construye el árbol de la traza entero en memoria** —jerarquía,
# tipos de run, entradas, salidas, etiquetas, metadatos, `dotted_order`— y **no lo
# envía**. Es exactamente lo que hace falta para estudiar la anatomía de una traza sin
# clave, sin red y sin gastar cuota.
#
# Queda un detalle: `Client` sondea `GET /info` la primera vez que se usa, para saber
# de qué es capaz el servidor. Ese sondeo sí sale a la red, falla y escribe un aviso.
# Se evita presembrando `client._info`, que es justo lo que la propiedad comprueba
# antes de llamar. No es una API pública, así que `traza_local` lo aísla aquí: si
# cambia, se arregla en un sitio.


class _Traza:
    """Lo que devuelve `traza_local()`: el árbol de la traza, una vez terminada.

    `raiz` es un `RunTree` envoltorio que se crea para tener de dónde colgar todo; lo
    que a ti te interesa suele estar en `t.principales`, las funciones decoradas que
    llamaste desde el bloque.
    """

    def __init__(self, raiz: Any) -> None:
        self.raiz = raiz

    @property
    def principales(self) -> list[Any]:
        """Los runs de primer nivel: las funciones que llamaste desde el bloque."""
        return list(self.raiz.child_runs or [])

    def __repr__(self) -> str:
        nombres = [r.name for r in self.principales]
        return f"<Traza con {len(nombres)} run(s) de primer nivel: {nombres}>"

    def recorrer(self, *, incluir_envoltorio: bool = False):
        """Recorre el árbol en profundidad y produce `(profundidad, run)`."""
        def _bajar(nodo, profundidad=0):
            yield profundidad, nodo
            for hijo in getattr(nodo, "child_runs", None) or []:
                yield from _bajar(hijo, profundidad + 1)

        if incluir_envoltorio:
            yield from _bajar(self.raiz)
        else:
            for run in self.principales:
                yield from _bajar(run)

    def dibujar(self, *, detalle: bool = False) -> None:
        """Imprime el árbol como lo dibujaría la interfaz de LangSmith."""
        for profundidad, run in self.recorrer():
            linea = f"{'   ' * profundidad}├─ {run.name}  [{run.run_type}]"
            if detalle:
                linea += f"  in={_corto(run.inputs)}  out={_corto(run.outputs)}"
            print(linea)

    def __len__(self) -> int:
        return sum(1 for _ in self.recorrer())


def _corto(valor: Any, ancho: int = 44) -> str:
    texto = repr(valor)
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


class _SesionMuda:
    """Una sesión de `requests` que responde 200 a todo sin tocar la red.

    Es el corte definitivo, y hace falta por una razón que conviene conocer porque
    también te afecta a ti: **`tracing_context(enabled="local")` solo gobierna el
    camino de `@traceable`.** El tracer de callbacks de LangChain —el que instrumenta
    solo tus grafos de LangGraph y tus cadenas— es otro camino, y ese intenta enviar
    igual. Sin esto, ejecutar un grafo dentro de `traza_local()` llena la salida de
    errores de conexión.

    Cortando en el transporte da igual qué camino lo intente: no sale nada.
    """

    def __init__(self) -> None:
        import requests

        self.headers: dict[str, str] = {}
        self.auth = None
        self.cookies = requests.cookies.RequestsCookieJar()
        self.peticiones: list[tuple[str, str]] = []

    def request(self, method, url, *args, **kwargs):
        return self._respuesta(method, url)

    def send(self, request, **kwargs):
        return self._respuesta(getattr(request, "method", "?"), getattr(request, "url", "?"))

    def _respuesta(self, method, url):
        import requests

        self.peticiones.append((str(method), str(url)))
        r = requests.Response()
        r.status_code = 200
        r._content = b"{}"
        r.headers["Content-Type"] = "application/json"
        r.request = None
        return r

    def mount(self, *args, **kwargs):
        return None

    def close(self):
        return None


def _cliente_mudo():
    """Un `Client` que no sale a la red por ningún camino.

    Dos cortes, y los dos hacen falta:

    1. **`_info` presembrado.** `Client.info` sondea `GET /info` la primera vez que se
       usa, para saber de qué es capaz el servidor. Ese sondeo sale a la red, falla y
       escribe un aviso en mitad de la salida. Presembrarlo es lo primero que comprueba
       la propiedad. No es API pública, así que vive aquí y solo aquí.
    2. **Una sesión muda.** Ver `_SesionMuda`: el tracer de callbacks de LangChain no
       respeta `enabled="local"` e intenta enviar de todas formas.
    """
    from langsmith import Client
    from langsmith.schemas import LangSmithInfo

    c = Client(api_key="local-sin-servicio", auto_batch_tracing=False, session=_SesionMuda())
    c._info = LangSmithInfo()
    return c


@contextlib.contextmanager
def traza_local(nombre: str = "bloque"):
    """Construye la traza en memoria y **no la envía** a ninguna parte.

        with traza_local() as t:
            responder("¿por qué me han cobrado dos veces?")

        t.dibujar()
        print(t.principales[0].dotted_order)

    Funciona sin clave, sin red y sin gastar cuota, y el árbol que produce es el mismo
    que subiría el modo en línea. Es la herramienta del módulo 1: mirar por dentro lo
    que la interfaz de LangSmith te dibuja por fuera.

    Descansa sobre un detalle del SDK que no está en los tutoriales: `tracing_context`
    acepta `enabled="local"` además de `True` y `False`. Con `"local"` se construye el
    árbol entero —jerarquía, tipos de run, entradas, salidas, etiquetas, metadatos,
    `dotted_order`— y no se sube nada.

    Lo que **no** hace: comprobar nada del servidor. Si lo que quieres es verificar que
    tus trazas llegan de verdad, esto no lo prueba; para eso hace falta el modo en línea.
    """
    import warnings

    from langsmith import RunTree
    from langsmith.run_helpers import tracing_context

    mudo = _cliente_mudo()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raiz = RunTree(name=nombre, run_type="chain", inputs={}, client=mudo)
        with tracing_context(enabled="local", parent=raiz, client=mudo):
            yield _Traza(raiz)


# --------------------------------------------------------------------------------------
# Un servicio de LangSmith simulado, para el notebook 03
# --------------------------------------------------------------------------------------
#
# El notebook 03 va de trazas que se pierden. Enseñarlo sin poder perder ninguna sería
# ridículo, así que en vez de describir el problema se monta un servicio de mentira que
# se puede tirar a voluntad y contar qué llegó y qué no.
#
# Es un servicio de verdad en lo único que importa aquí: el SDK habla con él por su
# camino normal —`Client`, cola de envío, reintentos, callbacks de error— sin saber que
# al otro lado no hay nadie. Lo que no hace es nada de lo que LangSmith hace de verdad:
# no guarda, no indexa, no calcula coste. Solo acusa recibo o falla.


class _ServicioSimulado:
    """Lo que devuelve `servicio_simulado()`. Ver ahí la documentación."""

    def __init__(self, *, falla: bool, cae_tras: int | None) -> None:
        self.falla = falla
        self.cae_tras = cae_tras
        self.peticiones: list[tuple[str, str]] = []
        self.recibidos: list[dict] = []
        self.rechazados: list[tuple[str, str]] = []
        self.errores: list[Exception] = []
        self.cliente: Any = None

    # -- lo que ve el usuario del notebook ---------------------------------------------

    @property
    def nombres_recibidos(self) -> list[str]:
        """Los nombres de los runs que llegaron al servicio."""
        return [r.get("name", "?") for r in self.recibidos]

    def resumen(self) -> None:
        print(f"  peticiones que salieron : {len(self.peticiones)}")
        print(f"  runs que llegaron       : {len(self.recibidos)} {self.nombres_recibidos}")
        print(f"  peticiones rechazadas   : {len(self.rechazados)}")
        print(f"  errores de envío vistos : {len(self.errores)}")

    # -- las tripas --------------------------------------------------------------------

    def _debe_fallar(self) -> bool:
        if self.cae_tras is not None:
            return len(self.peticiones) > self.cae_tras
        return self.falla

    def _anotar(self, method: str, url: str, cuerpo: Any) -> bool:
        import json

        self.peticiones.append((str(method), str(url)))
        if self._debe_fallar():
            self.rechazados.append((str(method), str(url)))
            return False
        if str(method).upper() == "POST" and cuerpo:
            try:
                datos = json.loads(cuerpo)
            except (TypeError, ValueError):
                return True
            for run in datos if isinstance(datos, list) else [datos]:
                if isinstance(run, dict) and "name" in run:
                    self.recibidos.append(run)
        return True


class _SesionDeServicio(_SesionMuda):
    """La sesión que habla con el `_ServicioSimulado` en vez de con la red."""

    def __init__(self, servicio: _ServicioSimulado) -> None:
        super().__init__()
        self._servicio = servicio

    def request(self, method, url, *args, **kwargs):
        aceptado = self._servicio._anotar(method, url, kwargs.get("data"))
        return self._respuesta(method, url, aceptado)

    def send(self, request, **kwargs):
        aceptado = self._servicio._anotar(
            getattr(request, "method", "?"), getattr(request, "url", "?"),
            getattr(request, "body", None))
        return self._respuesta(getattr(request, "method", "?"),
                               getattr(request, "url", "?"), aceptado)

    def _respuesta(self, method, url, aceptado=True):  # type: ignore[override]
        import requests

        r = requests.Response()
        r.status_code = 200 if aceptado else 503
        r._content = b"{}" if aceptado else b'{"detail":"servicio no disponible"}'
        r.headers["Content-Type"] = "application/json"
        r.url = str(url)
        r.request = None
        return r


@contextlib.contextmanager
def servicio_simulado(*, falla: bool = False, cae_tras: int | None = None,
                      muestreo: float | None = None):
    """Un LangSmith de mentira con el que el SDK habla de verdad.

    Sirve para enseñar en local lo que solo se ve cuando el servicio falla:

        with servicio_simulado(falla=True) as servicio:
            with servicio.trazando():
                responder("un ticket")
            servicio.cliente.flush()

        servicio.resumen()

    Parámetros:
        falla: si es `True`, el servicio responde 503 a todo desde el principio.
        cae_tras: acepta las primeras N peticiones y falla a partir de ahí. Sirve para
            el caso realista —el servicio se cae a mitad— en vez del binario.
        muestreo: la tasa de `tracing_sampling_rate` del `Client`, entre 0 y 1.

    Lo que se puede mirar después: `peticiones`, `recibidos`, `nombres_recibidos`,
    `rechazados` y `errores` —estos últimos son los que el SDK pasó a
    `tracing_error_callback`, que es la única forma de enterarse de que se pierden
    trazas—.

    Sin reintentos, para que las cuentas del notebook salgan claras: `retry_config`
    va a cero. En producción sí hay reintentos, y eso es parte de por qué el problema
    es escurridizo.
    """
    from langsmith import Client
    from langsmith.run_helpers import tracing_context
    from langsmith.schemas import LangSmithInfo
    from urllib3.util import Retry

    servicio = _ServicioSimulado(falla=falla, cae_tras=cae_tras)
    cliente = Client(
        api_key="servicio-simulado",
        auto_batch_tracing=False,
        session=_SesionDeServicio(servicio),
        retry_config=Retry(total=0),
        tracing_sampling_rate=muestreo,
        tracing_error_callback=servicio.errores.append,
    )
    cliente._info = LangSmithInfo()
    servicio.cliente = cliente

    def trazando(**kwargs):
        return tracing_context(enabled=True, client=cliente, **kwargs)

    servicio.trazando = trazando  # type: ignore[attr-defined]
    yield servicio


@contextlib.contextmanager
def registro_del_sdk(nivel: int = 30):
    """Captura lo que el SDK de LangSmith escribe en el log, en vez de imprimirlo.

        with registro_del_sdk() as lineas:
            ...

        for linea in lineas:
            print(linea)

    Existe porque **esa línea de log es lo único que tu aplicación produce cuando pierde
    una traza**. Verla como dato, y no como ruido que pasa por la consola, es la mitad
    de la lección del notebook 03.
    """
    import logging

    lineas: list[str] = []

    class _Recolector(logging.Handler):
        def emit(self, registro: logging.LogRecord) -> None:
            lineas.append(f"[{registro.levelname}] {registro.getMessage()}")

    recolector = _Recolector(level=nivel)
    afectados = [logging.getLogger("langsmith"),
                 logging.getLogger("langsmith.client"),
                 logging.getLogger("langchain_core.tracers.core")]
    estado = [(lg, lg.handlers[:], lg.propagate) for lg in afectados]
    try:
        for lg in afectados:
            lg.handlers = [recolector]
            lg.propagate = False
        yield lineas
    finally:
        for lg, handlers, propaga in estado:
            lg.handlers = handlers
            lg.propagate = propaga
