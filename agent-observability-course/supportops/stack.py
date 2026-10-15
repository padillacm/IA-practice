"""``check_stack()``: ¿qué servicios del stack están arriba? Si faltan, imprime el comando EXACTO de Compose y avisa del
modo degradado (datos pregrabados con el mismo esquema) para que el notebook nunca se quede bloqueado.

Uso::

    from supportops import check_stack
    st = check_stack("core")                    # o ["collector", "tempo"], o "core+metrics"
    if st.degraded: ...                         # usa supportops.sample_data
"""
from __future__ import annotations

import os
import pathlib
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field

# nombre de servicio -> (perfil de Compose, URL de salud en el host, descripción)
def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def services() -> dict[str, dict[str, str]]:
    host = _env("STACK_HOST", "localhost")
    return {
        "collector": {"profile": "core", "url": f"http://{host}:13133/", "ui": f"http://{host}:13133/", "otlp_http": f"http://{host}:4318", "otlp_grpc": f"{host}:4317"},
        "tempo": {"profile": "core", "url": f"http://{host}:3200/ready", "ui": f"http://{host}:3200"},
        "loki": {"profile": "core", "url": f"http://{host}:3100/ready", "ui": f"http://{host}:3100"},
        "grafana": {"profile": "core", "url": f"http://{host}:3000/api/health", "ui": f"http://{host}:3000"},
        "prometheus": {"profile": "metrics", "url": f"http://{host}:9090/-/ready", "ui": f"http://{host}:9090"},
        "pyroscope": {"profile": "profiling", "url": f"http://{host}:4040/ready", "ui": f"http://{host}:4040"},
    }


PROFILES = {"core": ["collector", "tempo", "loki", "grafana"], "metrics": ["prometheus"], "profiling": ["pyroscope"]}


def stack_dir() -> pathlib.Path:
    """Carpeta ``stack/`` del curso (junto al paquete, o ``SUPPORTOPS_STACK_DIR``)."""
    if os.environ.get("SUPPORTOPS_STACK_DIR"):
        return pathlib.Path(os.environ["SUPPORTOPS_STACK_DIR"])
    return pathlib.Path(__file__).resolve().parents[1] / "stack"


@dataclass
class StackStatus:
    up: dict[str, bool] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    profiles: list[str] = field(default_factory=list)
    command: str = ""
    starting: list[str] = field(default_factory=list)

    @property
    def degraded(self) -> bool:
        """True si falta algún servicio requerido: trabaja con datos pregrabados (``supportops.sample_data``)."""
        return not all(self.up.get(s, False) for s in self.required)

    @property
    def missing(self) -> list[str]:
        return [s for s in self.required if not self.up.get(s, False)]

    def __bool__(self) -> bool:
        return not self.degraded


def _probe(url: str, timeout: float) -> str:
    """'up' (2xx) | 'starting' (responde pero 503: p. ej. Loki/Pyroscope en sus primeros ~15-30 s) | 'down'."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # sin proxy: es localhost
        with opener.open(url, timeout=timeout) as r:
            return "up" if 200 <= r.status < 300 else "starting"
    except urllib.error.HTTPError:
        return "starting"          # el puerto responde: el servicio existe pero aún no está listo
    except Exception:
        return "down"


def _resolve(spec: str | list[str] | tuple[str, ...]) -> tuple[list[str], list[str]]:
    """Admite 'core', 'core+metrics', ['core','metrics'] o nombres de servicio. Devuelve (servicios, perfiles)."""
    items = spec.replace("+", ",").split(",") if isinstance(spec, str) else list(spec)
    svcs: list[str] = []
    profs: list[str] = []
    all_svcs = services()
    for it in (i.strip() for i in items if i.strip()):
        if it in PROFILES:
            svcs += PROFILES[it]
            profs.append(it)
        elif it in all_svcs:
            svcs.append(it)
            profs.append(all_svcs[it]["profile"])
        else:
            raise ValueError(f"servicio/perfil desconocido: {it!r}; opciones: {list(PROFILES) + list(all_svcs)}")
    return list(dict.fromkeys(svcs)), list(dict.fromkeys(profs))


def compose_command(profiles: list[str]) -> str:
    flags = " ".join(f"--profile {p}" for p in profiles)
    return f"docker compose -f {stack_dir() / 'docker-compose.yml'} {flags} up -d"


def check_stack(require: str | list[str] | tuple[str, ...] = "core", timeout: float = 1.5, verbose: bool = True) -> StackStatus:
    """Comprueba los servicios pedidos (y informa también del resto). No lanza excepciones: devuelve ``StackStatus``."""
    required, profiles = _resolve(require)
    svc = services()
    probes = {name: _probe(info["url"], timeout) for name, info in svc.items()}
    up = {n: p == "up" for n, p in probes.items()}
    st = StackStatus(up=up, required=required, profiles=profiles, command=compose_command(profiles),
                     starting=[n for n, p in probes.items() if p == "starting"])
    if verbose:
        print("Estado del stack:")
        for name, info in svc.items():
            mark = "OK  " if up[name] else ("...." if probes[name] == "starting" else "----")
            need = " (requerido)" if name in required else ""
            print(f"  [{mark}] {name:<10} {info['ui']}{need}")
        if st.degraded:
            print(f"\nFaltan servicios requeridos: {', '.join(st.missing)}")
            if st.starting:
                print(f"  (....) = arrancando: {', '.join(st.starting)}. Loki tarda ~20 s y Pyroscope ~30 s en estar listos: reintenta.")
            if shutil.which("docker") is None:
                print("No encuentro `docker` en el PATH: instálalo (ver módulo 00) o trabaja en MODO DEGRADADO.")
            print("Para levantarlos (aprox. 1,2 GB de RAM el perfil core):\n  " + st.command)
            print("\nMODO DEGRADADO: el notebook sigue funcionando con datos pregrabados "
                  "(supportops.sample_data, mismo esquema), pero NO verás nada en Grafana.")
        else:
            print("\nTodo lo requerido está arriba: modo completo.")
    return st
