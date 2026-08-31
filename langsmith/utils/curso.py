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

        # Estos atributos existen porque partes del SDK los leen del objeto sesión
        # antes de usarlo. `trust_env` en concreto lo consulta el cliente HTTP nuevo
        # (`client.threads`, del notebook 04): sin él, acceder a esa propiedad lanza
        # un `AttributeError` que parece decir que la funcionalidad no existe.
        self.headers: dict[str, str] = {}
        self.auth = None
        self.trust_env = False
        self.verify = True
        self.cert = None
        self.proxies: dict[str, str] = {}
        self.params: dict[str, str] = {}
        self.stream = False
        self.max_redirects = 0
        self.adapters: dict[str, Any] = {}
        self.hooks: dict[str, list] = {"response": []}
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
        self.cierres: list[dict] = []
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
        print(f"  runs que se cerraron    : {len(self.cierres)}")
        print(f"  peticiones rechazadas   : {len(self.rechazados)}")
        print(f"  errores de envío vistos : {len(self.errores)}")

    def run(self, indice: int = 0) -> dict:
        """El run tal y como llegó, con lo que trajo el cierre ya incorporado.

        Es lo que de verdad quedaría guardado, que es la pregunta del notebook 05:
        no «qué mandé» sino **qué acabó en el servidor**.
        """
        entero = dict(self.recibidos[indice])
        objetivo = str(entero.get("id"))
        for cierre in self.cierres:
            if str(cierre.get("id")) == objetivo:
                entero.update({k: v for k, v in cierre.items() if v is not None})
        return entero

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
        if not cuerpo:
            return True
        try:
            datos = json.loads(cuerpo)
        except (TypeError, ValueError):
            return True
        # El POST abre el run con sus entradas; el PATCH lo cierra con sus salidas.
        # Hay que quedarse con los dos para saber qué acabó guardado.
        destino = self.recibidos if str(method).upper() == "POST" else self.cierres
        for run in datos if isinstance(datos, list) else [datos]:
            if isinstance(run, dict):
                destino.append(run)
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
                      muestreo: float | None = None, **opciones_del_cliente: Any):
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
        **opciones_del_cliente: lo que sea que quieras pasarle al `Client`. Es lo que
            usa el notebook 05 para comprobar `anonymizer`, `hide_inputs` y
            `hide_outputs` mirando lo que llega de verdad, en vez de creerse la
            documentación.

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
        **opciones_del_cliente,
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


# --------------------------------------------------------------------------------------
# El agente del curso de LangGraph
# --------------------------------------------------------------------------------------


class ModeloGuionizado:
    """Un modelo de chat falso que **sí sabe pedir herramientas**.

    Los modelos falsos de LangChain que vienen de serie no implementan `bind_tools`, y
    sin eso un agente con `ToolNode` no llega a ejecutar ninguna herramienta: la traza
    sale plana y el proyecto P1 no tendría nada que enseñar.

    Se le da un guion —una respuesta por turno— y devuelve cada una en orden. Una
    entrada puede ser:

        "texto"                                  -> responde con ese texto
        ("contar_tickets", {"categoria": "x"})   -> pide esa herramienta

    Lleva `usage_metadata` con cifras fijas para que las cuentas de tokens y coste del
    módulo 4 tengan de dónde salir.
    """

    def __new__(cls, guion, **kwargs):
        from langchain_core.callbacks import CallbackManagerForLLMRun
        from langchain_core.language_models import BaseChatModel
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        class ModeloGuionizado(BaseChatModel):
            guion: list = []
            turno: int = 0
            llamadas: int = 0

            @property
            def _llm_type(self) -> str:
                return "guionizado-curso"

            def _generate(self, messages, stop=None,
                          run_manager: CallbackManagerForLLMRun | None = None, **kw):
                paso = self.guion[min(self.turno, len(self.guion) - 1)]
                object.__setattr__(self, "turno", self.turno + 1)
                object.__setattr__(self, "llamadas", self.llamadas + 1)

                uso = {"input_tokens": 100 + 20 * self.turno, "output_tokens": 25,
                       "total_tokens": 125 + 20 * self.turno}
                if isinstance(paso, tuple):
                    nombre, argumentos = paso
                    mensaje = AIMessage(
                        "",
                        tool_calls=[{"name": nombre, "args": argumentos,
                                     "id": f"llamada-{self.turno}", "type": "tool_call"}],
                        usage_metadata=uso,
                    )
                else:
                    mensaje = AIMessage(str(paso), usage_metadata=uso)
                return ChatResult(generations=[ChatGeneration(message=mensaje)])

            def bind_tools(self, tools, **kw):
                return self

        return ModeloGuionizado(guion=list(guion), **kwargs)


def agente_de_soporte(guion: list | None = None):
    """Importa y compila el agente de soporte del curso de LangGraph, con modelo falso.

    Es la aplicación que instrumenta el proyecto P1: el mismo agente de `mi_agente/`,
    con sus herramientas sobre los 400 tickets etiquetados y su `ToolNode`.

    Hay un detalle de importación que hay que hacer bien y no es evidente. `grafo.py`
    escribe `from langchain.chat_models import init_chat_model` **en el momento de
    importarse**, así que el nombre queda enlazado a la función real. Parchear el módulo
    después no sirve de nada: hay que hacerlo **antes** del primer import, y por eso este
    ayudante existe en vez de tres líneas en el notebook.

    Devuelve `(grafo_compilado, modelo)`. El modelo es un `ModeloGuionizado`, así que
    puedes hacerle pedir herramientas y comprobar cuántas veces se le llamó.
    """
    import sys

    despliegue = RAIZ.parent / "langgraph" / "despliegue"
    if not despliegue.exists():
        raise FileNotFoundError(
            f"No encuentro el agente del curso de LangGraph en {despliegue}.\n"
            "El proyecto P1 lo necesita: es la aplicación que se instrumenta."
        )
    if str(despliegue) not in sys.path:
        sys.path.insert(0, str(despliegue))

    modelo = ModeloGuionizado(guion or [
        ("contar_tickets", {"categoria": "facturacion"}),
        "He mirado los datos: hay 87 tickets de facturación.",
    ])

    # El parche, ANTES de importar el grafo. `bind_tools` sobre el modelo falso devuelve
    # el propio modelo, que es lo que hace que el grafo se ejecute sin llamar a nadie.
    import langchain.chat_models as chat_models

    original = chat_models.init_chat_model
    chat_models.init_chat_model = lambda *a, **k: modelo
    try:
        for modulo in [m for m in sys.modules if m.startswith("mi_agente")]:
            del sys.modules[modulo]
        from mi_agente.grafo import construir

        return construir(), modelo
    finally:
        chat_models.init_chat_model = original


# --------------------------------------------------------------------------------------
# Datasets y experimentos en local (módulo 2)
# --------------------------------------------------------------------------------------
#
# Segundo hallazgo que amplía lo verificable, después del `enabled="local"` del módulo 1:
# `evaluate()` acepta `upload_results=False` y una **lista de `Example` construida en
# memoria** en vez del nombre de un dataset del servidor. Con las dos cosas, el motor de
# evaluación entero —el objetivo, los evaluadores, las repeticiones, los evaluadores de
# resumen, `to_pandas()`— corre en tu máquina sin cuenta, sin clave y sin gastar cuota.
#
# Lo que NO da el modo local, y conviene tenerlo claro para no venderlo de más:
# no hay historial entre experimentos, no hay comparación en la interfaz, no hay versiones
# del dataset y no hay nada que compartir con nadie. O sea, no sustituye al servicio:
# sirve para aprender la mecánica y para probar tus evaluadores antes de gastar trazas.


def ejemplos_locales(filas: list[dict], *, entradas: tuple[str, ...],
                     salidas: tuple[str, ...], id_dataset: Any = None) -> list[Any]:
    """Construye una lista de `Example` en memoria a partir de diccionarios.

        ejemplos = ejemplos_locales(
            [{"mensaje": "...", "categoria": "facturacion"}, ...],
            entradas=("mensaje",),
            salidas=("categoria",),
        )

    Es lo que se le pasa a `experimento_local()` como `datos`. Cada fila se parte en
    `inputs` y `outputs` según las claves que indiques; lo que no esté en ninguna de las
    dos listas se guarda en `metadata`, que es donde conviene dejar lo que sirve para
    filtrar (el plan del cliente, el canal, la dificultad) sin que el evaluador lo vea.
    """
    import datetime
    import uuid

    ahora = datetime.datetime.now(datetime.timezone.utc)
    id_dataset = id_dataset or uuid.uuid4()

    from langsmith.schemas import Example

    construidos = []
    for fila in filas:
        metadatos = {k: v for k, v in fila.items() if k not in entradas and k not in salidas}
        construidos.append(Example(
            id=uuid.uuid4(),
            dataset_id=id_dataset,
            created_at=ahora,
            inputs={k: fila[k] for k in entradas},
            outputs={k: fila[k] for k in salidas},
            metadata=metadatos or None,
        ))
    return construidos


def experimento_local(objetivo, datos, *, evaluadores=None, evaluadores_de_resumen=None,
                      repeticiones: int = 1, prefijo: str = "local", **kwargs):
    """Ejecuta `evaluate()` **sin subir nada** y sin salir a la red.

        resultados = experimento_local(mi_clasificador, ejemplos, evaluadores=[acierto])
        resultados.to_pandas()

    Es el motor de evaluación de verdad —el mismo `evaluate()` del SDK— con dos
    diferencias: `upload_results=False` y un cliente que no habla con nadie.

    Un detalle que sorprende y conviene saber: en este modo **`experiment_prefix` se
    ignora** y `experiment_name` devuelve un nombre aleatorio. Sin subida no hay
    experimento que nombrar, así que no te fíes de ese nombre en local.
    """
    import warnings

    from langsmith import evaluate

    # `upload_results=False` está marcado como beta y el SDK avisa en cada llamada. El
    # aviso es cierto y el curso lo dice en el notebook 07, así que aquí se silencia
    # para que la salida del notebook se lea: repetirlo veinte veces no informa de nada.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*upload_results.*")
        return _lanzar(evaluate, objetivo, datos, evaluadores, evaluadores_de_resumen,
                       repeticiones, prefijo, kwargs)


def _lanzar(evaluate, objetivo, datos, evaluadores, evaluadores_de_resumen,
            repeticiones, prefijo, kwargs):
    return evaluate(
        objetivo,
        data=datos,
        evaluators=evaluadores,
        summary_evaluators=evaluadores_de_resumen,
        num_repetitions=repeticiones,
        experiment_prefix=prefijo,
        upload_results=False,
        client=_cliente_mudo(),
        **kwargs,
    )


def resumen_del_experimento(resultados) -> dict[str, float]:
    """Media de cada métrica de un experimento, más lo que dijeron los de resumen.

    `ExperimentResults` no expone las medias: hay que recorrer las filas. Y los
    resultados de los evaluadores de resumen viven en `_summary_results`, que es
    privado — en el servicio los ves en la interfaz, en local hay que ir a buscarlos.
    """
    import collections

    acumulado: dict[str, list[float]] = collections.defaultdict(list)
    for fila in resultados:
        for resultado in fila["evaluation_results"]["results"]:
            if resultado.score is not None:
                acumulado[resultado.key].append(float(resultado.score))

    medias = {clave: sum(v) / len(v) for clave, v in acumulado.items() if v}
    for resultado in (getattr(resultados, "_summary_results", None) or {}).get("results", []):
        if resultado.score is not None:
            medias[f"{resultado.key} (resumen)"] = float(resultado.score)
    return medias


def tickets(n: int | None = None, *, semilla: int = 7, **filtros) -> list[dict]:
    """Devuelve tickets del conjunto compartido con el curso de LangGraph, como dicts.

        tickets(30, categoria="facturacion")
        tickets(50)                            # muestra estratificada por categoría

    Sin filtros y con `n`, la muestra es **estratificada por categoría**: coge
    aproximadamente la misma cantidad de cada una. Un conjunto de evaluación construido
    con las primeras 50 filas de un CSV mide lo que hubo en enero, no lo que hace tu
    sistema — y esa es una de las lecciones del módulo 2.
    """
    import pandas as pd

    marco = pd.read_csv(ruta_datos("tickets_soporte.csv"))
    for columna, valor in filtros.items():
        marco = marco[marco[columna] == valor]
    if n is None:
        return marco.to_dict("records")

    if filtros:
        return marco.sample(min(n, len(marco)), random_state=semilla).to_dict("records")

    # Muestreo estratificado a mano: `groupby().apply()` cambió de contrato en pandas 3
    # (`include_groups` ya no se admite) y esto funciona igual en las dos versiones.
    categorias = sorted(marco["categoria"].unique())
    por_grupo = max(1, n // len(categorias))
    trozos = []
    for categoria in categorias:
        grupo = marco[marco["categoria"] == categoria]
        trozos.append(grupo.sample(min(por_grupo, len(grupo)), random_state=semilla))
    muestra = pd.concat(trozos)

    # Si `n` no es múltiplo del número de categorías, la estratificación se queda corta.
    # Se completa con lo que sobra, al azar, para devolver exactamente `n`: un conjunto
    # que dice tener 30 casos y trae 24 estropea cualquier cuenta que hagas encima.
    if len(muestra) < n:
        resto = marco.drop(index=muestra.index)
        faltan = min(n - len(muestra), len(resto))
        if faltan:
            muestra = pd.concat([muestra, resto.sample(faltan, random_state=semilla)])

    return muestra.sample(frac=1.0, random_state=semilla).head(n).to_dict("records")


# --------------------------------------------------------------------------------------
# Un juez LLM que se puede ejecutar sin clave (módulo 2 y 3)
# --------------------------------------------------------------------------------------


def juez_local(decidir):
    """Un modelo de chat falso que sirve como juez de `openevals`, sin clave ni red.

        juez = juez_local(lambda texto: (1.0, "la respuesta menciona la política"))
        evaluador = create_llm_as_judge(prompt=CORRECTNESS_PROMPT, judge=juez,
                                        feedback_key="correccion")

    `decidir` recibe el **prompt ya montado** —todo el texto que se le mandaría al juez
    de verdad, con las entradas, la salida y la referencia dentro— y devuelve
    `(puntuacion, razonamiento)`.

    Para qué sirve: para trabajar la parte del juez que **no** es el modelo. La rúbrica,
    la clave de feedback, el rango de la puntuación, cómo se integra en `evaluate()`, y
    sobre todo el desacuerdo con los humanos del módulo 3. Todo eso se puede estudiar
    con un juez determinista, y estudiarlo con uno de verdad cuesta una traza por caso.

    Para qué NO sirve: para saber si tu rúbrica está bien escrita. Eso solo lo dice un
    modelo de verdad, y el módulo 3 va de medir exactamente eso.

    Descansa en un detalle de `openevals`: al juez le llama
    `judge.with_structured_output(esquema).invoke(mensajes)`. Basta implementar esos
    dos métodos.
    """
    from langchain_core.callbacks import CallbackManagerForLLMRun
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_core.runnables import RunnableLambda

    class _Juez(BaseChatModel):
        @property
        def _llm_type(self) -> str:
            return "juez-local-del-curso"

        def _generate(self, messages, stop=None,
                      run_manager: CallbackManagerForLLMRun | None = None, **kwargs):
            puntuacion, razon = decidir(_texto_de(messages))
            return ChatResult(generations=[ChatGeneration(
                message=AIMessage(f"{puntuacion} — {razon}"))])

        def with_structured_output(self, schema, **kwargs):
            claves = set(_claves_del_esquema(schema))

            def responder(mensajes):
                puntuacion, razon = decidir(_texto_de(mensajes))
                salida: dict[str, Any] = {}
                if "score" in claves:
                    salida["score"] = puntuacion
                if "reasoning" in claves:
                    salida["reasoning"] = razon
                return salida or {"score": puntuacion, "reasoning": razon}

            return RunnableLambda(responder)

    return _Juez()


def _texto_de(mensajes) -> str:
    """Aplana a texto lo que `openevals` le pasa al juez (dicts o mensajes)."""
    trozos = []
    for mensaje in mensajes if isinstance(mensajes, list) else [mensajes]:
        if isinstance(mensaje, dict):
            trozos.append(str(mensaje.get("content", "")))
        else:
            trozos.append(str(getattr(mensaje, "content", mensaje)))
    return "\n".join(trozos)


def _claves_del_esquema(schema) -> list[str]:
    if isinstance(schema, dict):
        return list((schema.get("properties") or {}))
    return list(getattr(schema, "model_fields", {}) or {})
