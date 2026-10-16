"""Módulo 19 · Kubernetes + Helm: renderizado y validación de charts, semántica de *values*, API server real de laboratorio, laboratorio de flujo de
telemetría con las configuraciones que producen los charts, HPA y el ejecutor de tráfico que corre dentro del pod.

Piezas (solo librería estándar + PyYAML; Docker/helm/kubectl solo para lo que los necesita):

* ``deep_merge`` / ``helm_values``: la semántica de fusión de *values* de Helm (mapas se fusionan, listas se REEMPLAZAN, ``null`` borra) escrita a mano.
* ``Tools`` / ``tools_available``: qué herramientas hay (helm, kubectl, kind, k3d, kubeconform, docker) y sus versiones.
* ``CHARTS`` / ``chart_path``: charts oficiales verificados (repositorio, versión, versión de la aplicación) y el resolvedor de rutas locales.
* ``render``, ``lint``, ``kubeconform``, ``kinds_count``, ``resource_requests``: ``helm template``/``helm lint``/validación de esquemas.
* ``ApiServerLab``: un API server REAL de Kubernetes (k3s en Docker) para ``helm install``/``kubectl apply --dry-run=server`` (los pods NO arrancan en este
  sandbox: ver ``ApiServerLab.can_run_pods``).
* ``FlowLab``: levanta Tempo, Loki, Prometheus, Grafana y el gateway del Collector en contenedores con los **ConfigMaps renderizados por los charts** y los
  nombres DNS de los Services de Kubernetes como alias de red, y verifica el flujo de telemetría de extremo a extremo.
* ``hpa_desired`` / ``hpa_simulate``: el algoritmo del HorizontalPodAutoscaler.
* ``python -m supportops.k8s run``: el bucle de tráfico del pod de SupportOps (variables de entorno).

Honestidad: en el sandbox donde se construyó el módulo ``runc`` no podía crear contenedores anidados dentro de un nodo de clúster (kind y k3s: «can't get
final child's PID from pipe: EOF»), así que **ningún pod llegó a ejecutarse en un clúster**. Lo que sí se probó está documentado en el README del módulo.
"""
from __future__ import annotations

import copy
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

COURSE = pathlib.Path(__file__).resolve().parents[1]
K8S_DIR = COURSE / "19_kubernetes_helm" / "k8s"
NAMESPACE = "observability"


# =====================================================================================================================
# 1. Semántica de values de Helm, a mano
# =====================================================================================================================
def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    """Fusión de *values* como Helm: los **mapas** se fusionan recursivamente, las **listas se reemplazan enteras** (no se concatenan) y ``None`` (``null`` en
    YAML) **borra** la clave heredada. Es la regla que más sorprende al personalizar ``config.service.pipelines`` o ``policies``."""
    out = copy.deepcopy(dict(base))
    for k, v in override.items():
        if v is None:
            out.pop(k, None)
        elif isinstance(v, Mapping) and isinstance(out.get(k), Mapping):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def helm_values(*layers: Mapping[str, Any]) -> dict[str, Any]:
    """Aplica capas de values de izquierda a derecha (equivale a ``helm -f a.yaml -f b.yaml``: la última gana)."""
    out: dict[str, Any] = {}
    for layer in layers:
        out = deep_merge(out, layer)
    return out


# =====================================================================================================================
# 2. Herramientas y charts
# =====================================================================================================================
def _which(name: str, env: str | None = None) -> str | None:
    if env and os.environ.get(env):
        return os.environ[env]
    p = shutil.which(name)
    if p:
        return p
    p = f"/root/bin/{name}"            # sandbox de construcción: binarios descargados aquí
    return p if os.path.exists(p) else None


def tool_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    cmds = {"helm": (["version", "--short"], "HELM"), "kubectl": (["version", "--client"], "KUBECTL"), "kind": (["version"], "KIND"), "k3d": (["version"], "K3D"),
            "kubeconform": (["-v"], "KUBECONFORM"), "docker": (["--version"], "DOCKER")}
    for name, (args, env) in cmds.items():
        exe = _which(name, env)
        if not exe:
            out[name] = "—"
            continue
        try:
            r = subprocess.run([exe, *args], capture_output=True, text=True, timeout=20)
            out[name] = (r.stdout + r.stderr).strip().splitlines()[0][:80] if (r.stdout + r.stderr).strip() else "?"
        except Exception:  # noqa: BLE001 - no ejecutable o sin permisos: se trata como no instalado
            out[name] = "—"
    return out


@dataclass(frozen=True)
class ChartRef:
    key: str
    chart: str            # nombre del chart en su repositorio
    repo_alias: str       # alias de `helm repo add`
    repo_url: str
    version: str          # versión del chart verificada (oct-2026)
    app_version: str
    clone: str = ""       # carpeta del clon local (repo de GitHub) bajo $COURSE_CHARTS_DIR
    subdir: str = "charts"
    own: bool = False


CHARTS: dict[str, ChartRef] = {
    "otel-collector": ChartRef("otel-collector", "opentelemetry-collector", "open-telemetry", "https://open-telemetry.github.io/opentelemetry-helm-charts", "0.176.0", "0.162.0", "opentelemetry-helm-charts"),
    "otel-operator": ChartRef("otel-operator", "opentelemetry-operator", "open-telemetry", "https://open-telemetry.github.io/opentelemetry-helm-charts", "0.126.0", "0.161.0", "opentelemetry-helm-charts"),
    "tempo": ChartRef("tempo", "tempo", "grafana-community", "https://grafana-community.github.io/helm-charts", "3.2.0", "3.1.0", "grafana-community"),
    "loki": ChartRef("loki", "loki", "grafana-community", "https://grafana-community.github.io/helm-charts", "18.16.0", "3.7.8", "grafana-community"),
    "grafana": ChartRef("grafana", "grafana", "grafana-community", "https://grafana-community.github.io/helm-charts", "14.0.0", "13.2.4", "grafana-community"),
    "supportops": ChartRef("supportops", "supportops", "", "", "0.1.0", "0.1.0-m19", own=True),
    "prom-lab": ChartRef("prom-lab", "prom-lab", "", "", "0.1.0", "v3.15.0", own=True),
}


def chart_path(key: str, pull: bool = True) -> str | None:
    """Ruta LOCAL del chart, en este orden: (1) los propios del módulo (``k8s/charts/<chart>``); (2) un clon del repositorio oficial bajo ``$COURSE_CHARTS_DIR`` (sitios sin
    acceso a ``github.io``/OCI); (3) la caché de descargas; (4) ``helm pull --repo <url> <chart> --version <pinned> --untar`` (con red). ``None`` si ninguna funciona."""
    c = CHARTS[key]
    if c.own:
        p = K8S_DIR / "charts" / c.chart
        return str(p) if p.exists() else None
    base = os.environ.get("COURSE_CHARTS_DIR")
    if base:
        p = pathlib.Path(base) / c.clone / c.subdir / c.chart
        if p.exists():
            return str(_offline_copy(p) if key == "loki" else p)
    cache = pathlib.Path(os.environ.get("COURSE_CHART_CACHE", pathlib.Path.home() / ".cache" / "obs-course-charts")) / f"{c.chart}-{c.version}"
    if (cache / c.chart / "Chart.yaml").exists():
        return str(cache / c.chart)
    if pull and _which("helm", "HELM"):
        cache.mkdir(parents=True, exist_ok=True)
        r = helm("pull", c.chart, "--repo", c.repo_url, "--version", c.version, "--untar", "--untardir", str(cache), check=False, timeout=120)
        if r.returncode == 0 and (cache / c.chart / "Chart.yaml").exists():
            return str(cache / c.chart)
    return None


def _offline_copy(src: pathlib.Path) -> pathlib.Path:
    """El chart de Loki declara dependencias (minio, rollout-operator) que ``helm template`` exige ver en ``charts/`` aunque estén desactivadas. Sin acceso a sus
    repositorios se usa una copia sin ``dependencies`` (en SingleBinary con sistema de ficheros no se usan). Con acceso, ``helm dependency build`` basta."""
    dst = pathlib.Path(tempfile.gettempdir()) / f"chart-offline-{src.name}"
    if not dst.exists():
        shutil.copytree(src, dst)
        cy = (dst / "Chart.yaml").read_text()
        cy = re.sub(r"(?ms)^dependencies:.*?(?=^\w|\Z)", "", cy)
        (dst / "Chart.yaml").write_text(cy)
        (dst / "Chart.lock").unlink(missing_ok=True)
    return dst


def chart_ref(key: str) -> str:
    p = chart_path(key)
    if not p:
        c = CHARTS[key]
        raise RuntimeError(f"chart «{c.chart}» no disponible: añade el repositorio (`helm repo add {c.repo_alias} {c.repo_url}`) o define COURSE_CHARTS_DIR con un clon del repositorio")
    return p


def chart_versions() -> list[dict[str, str]]:
    """Tabla de charts: lo verificado aquí frente a lo que dice el ``Chart.yaml`` local (si existe)."""
    import yaml
    rows = []
    for k, c in CHARTS.items():
        row = {"chart": c.chart, "repo": c.repo_url or "(propio del curso)", "versión verificada": c.version, "appVersion": c.app_version, "Chart.yaml local": "—"}
        p = chart_path(k)
        if p:
            cy = yaml.safe_load((pathlib.Path(p) / "Chart.yaml").read_text())
            row["Chart.yaml local"] = f"{cy.get('version')} / app {cy.get('appVersion')}"
        rows.append(row)
    return rows


def helm_bin() -> str:
    exe = _which("helm", "HELM")
    if not exe:
        raise RuntimeError("helm no está instalado (https://helm.sh/docs/intro/install/)")
    return exe


def helm(*args: str, kubeconfig: str | None = None, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if os.path.exists("/root/.ccr/ca-bundle.crt"):
        env.setdefault("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")
    if kubeconfig:
        env["KUBECONFIG"] = kubeconfig
    r = subprocess.run([helm_bin(), *args], capture_output=True, text=True, env=env, timeout=timeout)
    if check and r.returncode:
        raise RuntimeError(f"helm {' '.join(args[:3])} falló:\n{(r.stderr or r.stdout)[-1500:]}")
    return r


def helm_no_wait() -> str:
    """Helm 4 sustituye ``--wait=false`` (obsoleto) por ``--wait=hookOnly``; Helm 3 no conoce ese valor."""
    try:
        out = subprocess.run([helm_bin(), "version", "--short"], capture_output=True, text=True, timeout=20).stdout
        return "--wait=hookOnly" if re.search(r"v?(\d+)\.", out) and int(re.search(r"v?(\d+)\.", out).group(1)) >= 4 else "--wait=false"
    except Exception:  # noqa: BLE001
        return "--wait=false"


def _values_args(values: Sequence[Mapping[str, Any] | str | pathlib.Path], tmp: pathlib.Path) -> list[str]:
    out = []
    for i, v in enumerate(values):
        if isinstance(v, (str, pathlib.Path)):
            out += ["-f", str(v)]
        else:
            p = tmp / f"values-{i}.yaml"
            p.write_text(_dump(v))
            out += ["-f", str(p)]
    return out


def _dump(obj: Any) -> str:
    import yaml
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)


def render(release: str, chart: str, values: Sequence[Mapping[str, Any] | str | pathlib.Path] = (), *, namespace: str = NAMESPACE, set_values: Mapping[str, str] | None = None,
           extra: Sequence[str] = (), kube_version: str = "1.31.0") -> list[dict[str, Any]]:
    """``helm template`` y análisis de los documentos YAML (lista de manifiestos). ``chart``: clave de ``CHARTS`` o ruta."""
    import yaml
    ref = chart_ref(chart) if chart in CHARTS else chart
    with tempfile.TemporaryDirectory() as d:
        args = ["template", release, ref, "-n", namespace, "--kube-version", kube_version, *_values_args(values, pathlib.Path(d)), *extra]
        for k, v in (set_values or {}).items():
            args += ["--set", f"{k}={v}"]
        r = helm(*args)
    return [m for m in yaml.safe_load_all(r.stdout) if m]


def lint(chart: str, values: Sequence[Mapping[str, Any] | str | pathlib.Path] = (), *, set_values: Mapping[str, str] | None = None) -> tuple[bool, str]:
    ref = chart_ref(chart) if chart in CHARTS else chart
    with tempfile.TemporaryDirectory() as d:
        args = ["lint", ref, *_values_args(values, pathlib.Path(d)), "--quiet"]
        for k, v in (set_values or {}).items():
            args += ["--set", f"{k}={v}"]
        r = helm(*args, check=False)
    return r.returncode == 0, (r.stdout + r.stderr).strip()[-800:]


def kubeconform(manifests: Sequence[Mapping[str, Any]], k8s_version: str = "1.31.0", ignore_missing_schemas: bool = True) -> dict[str, Any]:
    """Valida cada manifiesto contra los esquemas OpenAPI de Kubernetes (``kubeconform``). Devuelve ``{valid, invalid, skipped, errors}``."""
    exe = _which("kubeconform", "KUBECONFORM")
    if not exe:
        return {"valid": 0, "invalid": 0, "skipped": len(manifests), "errors": ["kubeconform no instalado"], "available": False}
    text = "\n---\n".join(_dump(m) for m in manifests)
    args = [exe, "-kubernetes-version", k8s_version, "-summary", "-output", "json"] + (["-ignore-missing-schemas"] if ignore_missing_schemas else [])
    r = subprocess.run(args, input=text, capture_output=True, text=True, timeout=180)
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"valid": 0, "invalid": 0, "skipped": 0, "errors": [(r.stdout + r.stderr)[-400:]], "available": True}
    s = d.get("summary", {})
    errs = [f"{x.get('filename', '')}: {x.get('msg', '')}" for x in d.get("resources", []) if x.get("status") in ("statusInvalid", "statusError")]
    return {"valid": s.get("valid", 0), "invalid": s.get("invalid", 0) + s.get("errors", 0), "skipped": s.get("skipped", 0), "errors": errs, "available": True}


def kinds_count(manifests: Iterable[Mapping[str, Any]]) -> Counter:
    return Counter(m.get("kind", "?") for m in manifests)


def _parse_quantity(q: str | int | float, kind: str) -> float:
    """CPU en milicores y memoria en MiB."""
    s = str(q)
    if kind == "cpu":
        return float(s[:-1]) if s.endswith("m") else float(s) * 1000
    units = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024, "k": 1000 / 1024 / 1024, "M": 1e6 / 2**20, "G": 1e9 / 2**20}
    for u, f in units.items():
        if s.endswith(u):
            return float(s[: -len(u)]) * f
    return float(s) / 2**20


def resource_requests(manifests: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Suma de ``requests`` (milicores y MiB) de todas las réplicas declaradas: Deployments/StatefulSets (``replicas``), DaemonSets (1 por nodo = 1) y Pods."""
    cpu = mem = 0.0
    for m in manifests:
        spec = m.get("spec") or {}
        if m.get("kind") in ("Deployment", "StatefulSet", "DaemonSet"):
            reps = 1 if m["kind"] == "DaemonSet" else int(spec.get("replicas", 1) if spec.get("replicas") is not None else 1)
            tpl = spec.get("template", {}).get("spec", {})
        elif m.get("kind") == "Pod":
            reps, tpl = 1, spec
        else:
            continue
        for c in tpl.get("containers", []):
            req = (c.get("resources") or {}).get("requests") or {}
            cpu += reps * _parse_quantity(req.get("cpu", 0), "cpu")
            mem += reps * _parse_quantity(req.get("memory", 0), "mem")
    return {"cpu_m": cpu, "memory_mib": mem}


def configmap_text(manifests: Iterable[Mapping[str, Any]], name_contains: str, key: str | None = None) -> str:
    """Contenido de un ConfigMap renderizado (``key=None`` → el primer valor)."""
    for m in manifests:
        if m.get("kind") == "ConfigMap" and name_contains in m["metadata"]["name"]:
            data = m.get("data", {})
            if key is None:
                return next(iter(data.values()))
            if key in data:
                return data[key]
    raise KeyError(f"ConfigMap con «{name_contains}» no encontrado")


def configmap_files(manifests: Iterable[Mapping[str, Any]], name: str) -> dict[str, str]:
    """Todas las claves (= archivos al montarlo) del ConfigMap llamado exactamente ``name``."""
    name_contains = name
    out: dict[str, str] = {}
    for m in manifests:
        if m.get("kind") == "ConfigMap" and name_contains == m["metadata"]["name"]:
            out.update(m.get("data", {}))
    if not out:
        raise KeyError(f"ConfigMap con «{name_contains}» no encontrado")
    return out


# =====================================================================================================================
# 3. API server real (k3s en Docker)
# =====================================================================================================================
class ApiServerLab:
    """k3s (Kubernetes real, ``rancher/k3s``) en un contenedor privilegiado. ``kubeconfig`` apunta a ``127.0.0.1:<puerto>``.
    ⚠️ En el sandbox de construcción los pods no pudieron arrancar (``runc`` anidado); el API server, etcd/sqlite, controladores, admisión, CRDs y RBAC sí
    funcionan: sirve para ``helm install --wait=false``, ``kubectl apply --dry-run=server`` y validar CRs contra sus CRD reales."""

    IMAGE = os.environ.get("K3S_IMAGE", "rancher/k3s:v1.31.5-k3s1")

    def __init__(self, port: int = 0):
        self.name = f"k3s-lab-{uuid.uuid4().hex[:6]}"
        self.port = port
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="k3s-lab-"))
        self.kubeconfig = str(self.dir / "kubeconfig")

    def __enter__(self) -> "ApiServerLab":
        cmd = ["docker", "run", "-d", "--name", self.name, "--privileged", "--tmpfs", "/run", "--tmpfs", "/var/run", "-p", f"127.0.0.1:{self.port or ''}:6443", self.IMAGE,
               "server", "--disable=traefik", "--disable=metrics-server", "--disable=servicelb", "--disable=local-storage", "--tls-san=127.0.0.1"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr[:400])
        self.port = int(subprocess.run(["docker", "port", self.name, "6443/tcp"], capture_output=True, text=True).stdout.splitlines()[0].split(":")[-1])
        t0 = time.time()
        while time.time() - t0 < 120:
            r = subprocess.run(["docker", "exec", self.name, "cat", "/etc/rancher/k3s/k3s.yaml"], capture_output=True, text=True)
            if r.returncode == 0 and "server:" in r.stdout:
                (self.dir / "kubeconfig").write_text(r.stdout.replace("https://127.0.0.1:6443", f"https://127.0.0.1:{self.port}"))
                if self.kubectl("get", "ns", check=False).returncode == 0:
                    return self
            time.sleep(2)
        self.__exit__()
        raise RuntimeError("el API server de k3s no arrancó a tiempo")

    def kubectl(self, *args: str, input: str | None = None, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
        exe = _which("kubectl", "KUBECTL") or "kubectl"
        env = dict(os.environ, KUBECONFIG=self.kubeconfig)
        r = subprocess.run([exe, *args], input=input, capture_output=True, text=True, env=env, timeout=timeout)
        if check and r.returncode:
            raise RuntimeError(f"kubectl {' '.join(args[:4])}: {(r.stderr or r.stdout)[-800:]}")
        return r

    def apply(self, manifests: Sequence[Mapping[str, Any]] | str, *, dry_run: bool = False, namespace: str | None = None) -> subprocess.CompletedProcess:
        text = manifests if isinstance(manifests, str) else "\n---\n".join(_dump(m) for m in manifests)
        args = ["apply", "-f", "-"] + (["--dry-run=server"] if dry_run else []) + (["-n", namespace] if namespace else [])
        return self.kubectl(*args, input=text, check=False)

    def ensure_namespace(self, ns: str) -> None:
        self.kubectl("create", "namespace", ns, check=False)

    def helm_install(self, release: str, chart: str, values: Sequence[Mapping[str, Any] | str | pathlib.Path] = (), *, namespace: str = NAMESPACE,
                     set_values: Mapping[str, str] | None = None, dry_run_server: bool = False) -> subprocess.CompletedProcess:
        ref = chart_ref(chart) if chart in CHARTS else chart
        with tempfile.TemporaryDirectory() as d:
            args = ["upgrade", "--install", release, ref, "-n", namespace, "--create-namespace", helm_no_wait(), *_values_args(values, pathlib.Path(d))]
            if dry_run_server:
                args.append("--dry-run=server")
            for k, v in (set_values or {}).items():
                args += ["--set", f"{k}={v}"]
            return helm(*args, kubeconfig=self.kubeconfig, check=False)

    def objects(self, namespace: str = NAMESPACE) -> Counter:
        r = self.kubectl("get", "all,cm,hpa,pdb,sa", "-n", namespace, "-o", "json", check=False)
        try:
            return Counter(i["kind"] for i in json.loads(r.stdout)["items"])
        except Exception:  # noqa: BLE001
            return Counter()

    def can_run_pods(self, timeout_s: float = 60.0) -> tuple[bool, str]:
        """Intenta arrancar un pod de prueba con una imagen YA presente en el nodo; devuelve (ok, motivo). En el sandbox de construcción falla con el error de runc."""
        pod = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "probe", "namespace": "default"},
               "spec": {"restartPolicy": "Never", "containers": [{"name": "c", "image": "rancher/mirrored-pause:3.6", "imagePullPolicy": "Never"}]}}
        img = "rancher/mirrored-pause:3.6"            # los nodos del laboratorio no tienen red: se importan las imágenes que hagan falta desde el host
        subprocess.run(["docker", "pull", "-q", img], capture_output=True, timeout=180)
        save = subprocess.Popen(["docker", "save", img], stdout=subprocess.PIPE)
        subprocess.run(["docker", "exec", "-i", self.name, "ctr", "-n", "k8s.io", "images", "import", "-"], stdin=save.stdout, capture_output=True, timeout=180)
        self.apply([pod])
        t0 = time.time()
        while time.time() - t0 < timeout_s:
            r = self.kubectl("get", "pod", "probe", "-o", "jsonpath={.status.phase}", check=False)
            if r.stdout.strip() == "Running":
                return True, "Running"
            ev = self.kubectl("get", "events", "--field-selector", "involvedObject.name=probe", "-o", "jsonpath={.items[*].message}", check=False).stdout
            if "can't get final child's PID" in ev:
                return False, "runc: can't get final child's PID from pipe: EOF (contenedores anidados no soportados en este sandbox)"
            time.sleep(3)
        return False, "el pod no llegó a Running"

    def __exit__(self, *a: Any) -> None:
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        shutil.rmtree(self.dir, ignore_errors=True)


# =====================================================================================================================
# 4. Laboratorio de flujo: lo que renderizan los charts, ejecutado con los binarios reales
# =====================================================================================================================
class FlowLab:
    """Tempo, Loki, Prometheus y N réplicas del gateway del Collector en una red de Docker. Las **configuraciones salen de los ConfigMaps renderizados por los charts**
    (``configs``) y los contenedores llevan como alias el DNS de los Services de Kubernetes (``tempo.observability.svc.cluster.local``…): lo que el chart pone en
    ``endpoint:`` resuelve igual que en el clúster. No es Kubernetes (no hay kubelet, HPA ni scheduler), pero SÍ valida que esas configuraciones funcionan."""

    def __init__(self, tempo: Mapping[str, str], loki: Mapping[str, str], loki_runtime: Mapping[str, str], prometheus: Mapping[str, str], gateway: Mapping[str, str],
                 gateway_replicas: int = 1, namespace: str = NAMESPACE):
        """Cada argumento = ``{nombre_de_archivo: contenido}`` de los ConfigMaps renderizados (``configmap_files``): se montan donde los monta el chart."""
        self.files = {"tempo": dict(tempo), "loki": dict(loki), "loki-runtime": dict(loki_runtime), "prometheus": dict(prometheus), "gateway": dict(gateway)}
        self.replicas, self.ns = gateway_replicas, namespace
        self.id = uuid.uuid4().hex[:6]
        self.net = f"flowlab-{self.id}"
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="flowlab-"))
        self.names: list[str] = []
        self.ports: dict[str, int] = {}
        self._op = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _fqdn(self, svc: str) -> str:
        return f"{svc}.{self.ns}.svc.cluster.local"

    def _run(self, name: str, image: str, args: Sequence[str], aliases: Sequence[str], mounts: Sequence[tuple[pathlib.Path, str]], publish: Sequence[int] = (),
             env: Mapping[str, str] | None = None, user: str | None = None) -> str:
        cname = f"{name}-{self.id}"
        cmd = ["docker", "run", "-d", "--name", cname, "--network", self.net]
        for a in aliases:
            cmd += ["--network-alias", a]
        for src, dst in mounts:
            cmd += ["-v", f"{src}:{dst}:ro"]
        for p in publish:
            cmd += ["-p", f"127.0.0.1::{p}"]
        for k, v in (env or {}).items():
            cmd += ["-e", f"{k}={v}"]
        if user:
            cmd += ["--user", user]
        r = subprocess.run(cmd + [image, *args], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"{name}: {r.stderr[:400]}")
        self.names.append(cname)
        for p in publish:
            out = subprocess.run(["docker", "port", cname, f"{p}/tcp"], capture_output=True, text=True).stdout.splitlines()
            self.ports[f"{name}:{p}"] = int(out[0].split(":")[-1])
        return cname

    def _dir(self, key: str) -> pathlib.Path:
        d = self.dir / key
        d.mkdir(exist_ok=True)
        os.chmod(d, 0o755)
        for fname, text in self.files[key].items():
            f = d / fname
            f.write_text(text)
            os.chmod(f, 0o644)
        return d

    def __enter__(self) -> "FlowLab":
        subprocess.run(["docker", "network", "create", self.net], capture_output=True, check=True)
        gw_aliases = [self._fqdn("otel-gateway"), self._fqdn("otel-gateway-headless")]
        self._run("tempo", "grafana/tempo:3.1.0", ["-config.file=/conf/tempo.yaml"], [self._fqdn("tempo")], [(self._dir("tempo"), "/conf")], publish=[3200], user="root")
        self._run("loki", "grafana/loki:3.7.8", ["-config.file=/etc/loki/config/config.yaml"], [self._fqdn("loki")],
                  [(self._dir("loki"), "/etc/loki/config"), (self._dir("loki-runtime"), "/etc/loki/runtime-config")], publish=[3100], user="root")
        self._run("prometheus", "prom/prometheus:v3.15.0", ["--config.file=/conf/prometheus.yml", "--web.enable-otlp-receiver", "--storage.tsdb.path=/prometheus"],
                  [self._fqdn("prometheus")], [(self._dir("prometheus"), "/conf")], publish=[9090], user="root")
        gw_dir = self._dir("gateway")
        env = {"MY_POD_IP": "0.0.0.0", "OTEL_K8S_NAMESPACE": self.ns, "OTEL_K8S_NODE_NAME": "lab-node", "OTEL_K8S_NODE_IP": "10.0.0.1", "OTEL_K8S_POD_IP": "0.0.0.0", "GOMEMLIMIT": "400MiB"}
        for i in range(self.replicas):
            self._run(f"gw{i}", "otel/opentelemetry-collector-contrib:0.162.0", ["--config=/conf/relay"], gw_aliases, [(gw_dir, "/conf")], publish=[4318, 8888],
                      env={**env, "OTEL_K8S_POD_NAME": f"otel-gateway-{i}"})
        self.wait_ready()
        return self

    def wait_ready(self, timeout_s: float = 150.0) -> None:
        checks = {"tempo": f"http://127.0.0.1:{self.ports['tempo:3200']}/ready", "loki": f"http://127.0.0.1:{self.ports['loki:3100']}/ready",
                  "prometheus": f"http://127.0.0.1:{self.ports['prometheus:9090']}/-/ready"}
        t0 = time.time()
        pending = dict(checks)
        while pending and time.time() - t0 < timeout_s:
            for k, u in list(pending.items()):
                try:
                    if self._op.open(u, timeout=3).status == 200:
                        pending.pop(k)
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(2)
        if pending:
            raise RuntimeError(f"no están listos: {list(pending)}\n" + "\n".join(self.logs(n)[-300:] for n in self.names[:3]))
        for n in self.names:
            if n.startswith("gw") and self.exited(n):
                raise RuntimeError(f"{n} cayó:\n{self.logs(n)[-800:]}")

    def exited(self, name: str) -> bool:
        return subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", name], capture_output=True, text=True).stdout.strip() != "true"

    def logs(self, name: str) -> str:
        r = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
        return r.stdout + r.stderr

    @property
    def gateway_endpoints(self) -> list[str]:
        return [f"http://127.0.0.1:{self.ports[f'gw{i}:4318']}" for i in range(self.replicas)]

    def _get(self, url: str) -> Any:
        return json.loads(self._op.open(url, timeout=20).read())

    def tempo_trace_ids(self, q: str = '{ resource.service.name = "supportops-agent" }', limit: int = 1000) -> set[str]:
        d = self._get(f"http://127.0.0.1:{self.ports['tempo:3200']}/api/search?" + urllib.parse.urlencode({"q": q, "limit": limit}))
        return {t["traceID"] for t in d.get("traces", [])}

    def tempo_trace_span_count(self, trace_id: str) -> int:
        d = self._get(f"http://127.0.0.1:{self.ports['tempo:3200']}/api/traces/{trace_id}")
        n = 0
        for b in d.get("batches", d.get("resourceSpans", [])):
            for ss in b.get("scopeSpans", b.get("instrumentationLibrarySpans", [])):
                n += len(ss.get("spans", []))
        return n

    def loki_lines(self, logql: str = '{service_name="supportops-agent"}', minutes: int = 30) -> int:
        now = time.time_ns()
        q = urllib.parse.urlencode({"query": logql, "start": now - minutes * 60 * 10**9, "end": now + 10**9, "limit": 5000})
        d = self._get(f"http://127.0.0.1:{self.ports['loki:3100']}/loki/api/v1/query_range?" + q)
        return sum(len(r["values"]) for r in d["data"]["result"])

    def prom_query(self, expr: str) -> list[dict]:
        d = self._get(f"http://127.0.0.1:{self.ports['prometheus:9090']}/api/v1/query?" + urllib.parse.urlencode({"query": expr}))
        return d["data"]["result"]

    def wait_until(self, fn, timeout_s: float = 90.0, every_s: float = 3.0):
        t0, last = time.time(), None
        while time.time() - t0 < timeout_s:
            last = fn()
            if last:
                return last
            time.sleep(every_s)
        return last

    def __exit__(self, *a: Any) -> None:
        for n in self.names:
            subprocess.run(["docker", "rm", "-f", "-v", n], capture_output=True)
        subprocess.run(["docker", "network", "rm", self.net], capture_output=True)
        shutil.rmtree(self.dir, ignore_errors=True)


GATEWAY_FILE_CFG = """receivers:
  otlp:
    protocols:
      grpc: {endpoint: "0.0.0.0:4317"}
      http: {endpoint: "0.0.0.0:4318"}
processors:
  tail_sampling:
    decision_wait: 4s
    num_traces: 50000
    policies:
      - {name: errors, type: status_code, status_code: {status_codes: [ERROR]}}
      - {name: slow, type: latency, latency: {threshold_ms: 5000}}
      - {name: baseline, type: probabilistic, probabilistic: {sampling_percentage: 10}}
exporters:
  file: {path: /out/traces.jsonl}
service:
  pipelines:
    traces: {receivers: [otlp], processors: [tail_sampling], exporters: [file]}
"""

AGENT_LB_CFG = """receivers:
  otlp:
    protocols:
      http: {endpoint: "0.0.0.0:4318"}
exporters:
  load_balancing:
    routing_key: traceID
    protocol:
      otlp: {tls: {insecure: true}, timeout: 10s}
    resolver:
      static:
        hostnames: [%s]
service:
  pipelines:
    traces: {receivers: [otlp], exporters: [load_balancing]}
"""


class AffinityLab:
    """N gateways con ``tail_sampling`` (exportan a un archivo) y, opcionalmente, un agente con el exportador ``load_balancing`` por ``traceID`` delante.
    Reproduce el problema de escalar un procesador con estado: SIN afinidad (los lotes se reparten como haría un Service ClusterIP) cada réplica ve trozos de la traza
    y decide sobre información parcial; CON afinidad por traceID cada traza completa llega a una sola réplica."""

    def __init__(self, replicas: int = 2):
        self.n = replicas
        self.id = uuid.uuid4().hex[:6]
        self.net = f"affinity-{self.id}"
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="affinity-"))
        self.names: list[str] = []
        self.ports: dict[str, int] = {}
        self._op = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def _start(self, name: str, cfg: str, publish: Sequence[int] = (), out: pathlib.Path | None = None) -> None:
        d = self.dir / name
        d.mkdir()
        (d / "c.yaml").write_text(cfg)
        os.chmod(d / "c.yaml", 0o644)
        cmd = ["docker", "run", "-d", "--name", f"{name}-{self.id}", "--network", self.net, "--network-alias", name, "-v", f"{d / 'c.yaml'}:/c.yaml:ro"]
        if out is not None:
            out.mkdir()
            os.chmod(out, 0o777)
            cmd += ["-v", f"{out}:/out"]
        for p in publish:
            cmd += ["-p", f"127.0.0.1::{p}"]
        r = subprocess.run(cmd + ["otel/opentelemetry-collector-contrib:0.162.0", "--config=/c.yaml"], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr[:400])
        self.names.append(f"{name}-{self.id}")
        for p in publish:
            o = subprocess.run(["docker", "port", f"{name}-{self.id}", f"{p}/tcp"], capture_output=True, text=True).stdout.splitlines()
            self.ports[f"{name}:{p}"] = int(o[0].split(":")[-1])

    def __enter__(self) -> "AffinityLab":
        subprocess.run(["docker", "network", "create", self.net], capture_output=True, check=True)
        for i in range(self.n):
            self._start(f"gw{i}", GATEWAY_FILE_CFG, publish=[4318], out=self.dir / f"out{i}")
        self._start("agent", AGENT_LB_CFG % ", ".join(f"gw{i}:4317" for i in range(self.n)), publish=[4318])
        t0 = time.time()
        while time.time() - t0 < 60:
            if all("Everything is ready" in self.logs(n) for n in self.names):
                break
            time.sleep(1)
        return self

    def logs(self, name: str) -> str:
        r = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
        return r.stdout + r.stderr

    def _post(self, port: int, spans: Sequence[Mapping[str, Any]]) -> None:
        from .sampling import spans_to_otlp
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/traces", data=spans_to_otlp(spans).SerializeToString(), headers={"Content-Type": "application/x-protobuf"})
        self._op.open(req, timeout=20).read()

    def send(self, spans: Sequence[Mapping[str, Any]], affinity: bool, batch: int = 2) -> None:
        """Envía los spans en lotes pequeños (como lo harían servicios distintos). ``affinity=False``: reparto por turnos entre réplicas; ``True``: todo al agente con ``load_balancing``."""
        for i in range(0, len(spans), batch):
            chunk = spans[i:i + batch]
            port = self.ports["agent:4318"] if affinity else self.ports[f"gw{(i // batch) % self.n}:4318"]
            self._post(port, chunk)

    def kept_spans(self) -> dict[str, int]:
        """trace_id → nº de spans conservados (suma de todas las réplicas)."""
        out: Counter = Counter()
        for i in range(self.n):
            p = self.dir / f"out{i}" / "traces.jsonl"
            for line in (p.read_text().splitlines() if p.exists() else []):
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for rs in d.get("resourceSpans", []):
                    for ss in rs.get("scopeSpans", []):
                        for sp in ss.get("spans", []):
                            out[sp["traceId"]] += 1
        return dict(out)

    def settle(self, timeout_s: float = 40.0, quiet_s: float = 8.0) -> None:
        t0, last, change = time.time(), -1, time.time()
        while time.time() - t0 < timeout_s:
            n = sum(self.kept_spans().values())
            if n != last:
                last, change = n, time.time()
            elif time.time() - change >= quiet_s:
                return
            time.sleep(1)

    def __exit__(self, *a: Any) -> None:
        for n in self.names:
            subprocess.run(["docker", "rm", "-f", "-v", n], capture_output=True)
        subprocess.run(["docker", "network", "rm", self.net], capture_output=True)
        shutil.rmtree(self.dir, ignore_errors=True)


def affinity_experiment(traces: Sequence[Any], replicas: int = 2) -> dict[str, Any]:
    """Compara reparto sin afinidad vs ``load_balancing`` por traceID con el MISMO conjunto de trazas. Devuelve, por modo: trazas conservadas, % completas (todos sus
    spans), spans huérfanos y recall de las trazas con algún span en error o lentas."""
    spans = [s for t in traces for s in t.spans]
    expected = {t.trace_id: t.n_spans for t in traces}
    interesting = {t.trace_id for t in traces if t.interesting}
    out: dict[str, Any] = {}
    for mode, aff in (("sin afinidad (round-robin)", False), ("load_balancing por traceID", True)):
        with AffinityLab(replicas) as lab:
            lab.send(spans, affinity=aff)
            lab.settle()
            kept = lab.kept_spans()
        complete = sum(1 for tid, n in kept.items() if n == expected.get(tid))
        out[mode] = {"traces_kept": len(kept), "complete_pct": 100 * complete / max(1, len(kept)), "spans_kept": sum(kept.values()),
                     "interesting_recall_pct": 100 * len(interesting & set(kept)) / max(1, len(interesting)),
                     "interesting_complete_pct": 100 * sum(1 for tid in interesting if kept.get(tid) == expected[tid]) / max(1, len(interesting))}
    return out


def validate_with_binary(kind: str, config: str) -> tuple[bool, str]:
    """Valida una configuración renderizada con el binario oficial: ``collector`` (otelcol-contrib validate), ``tempo`` (-config.verify=true), ``loki`` (-verify-config),
    ``prometheus`` (promtool check config)."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="cfgval-"))
    try:
        f = d / "c.yaml"
        f.write_text(config)
        os.chmod(f, 0o644)
        base = ["docker", "run", "--rm", "--network", "none", "-v", f"{f}:/c.yaml:ro"]
        if kind == "collector":
            env = ["-e", "MY_POD_IP=0.0.0.0", "-e", "OTEL_K8S_NAMESPACE=x", "-e", "OTEL_K8S_NODE_NAME=x", "-e", "OTEL_K8S_NODE_IP=1.1.1.1", "-e", "OTEL_K8S_POD_IP=1.1.1.1", "-e", "OTEL_K8S_POD_NAME=x", "-e", "K8S_NODE_NAME=x"]
            cmd = base + env + ["otel/opentelemetry-collector-contrib:0.162.0", "validate", "--config=/c.yaml"]
        elif kind == "tempo":
            cmd = base + ["grafana/tempo:3.1.0", "-config.file=/c.yaml", "-config.verify=true"]
        elif kind == "loki":
            cmd = base + ["grafana/loki:3.7.8", "-config.file=/c.yaml", "-verify-config"]
        elif kind == "prometheus":
            cmd = base[:3] + ["--entrypoint", "promtool"] + base[3:] + ["prom/prometheus:v3.15.0", "check", "config", "/c.yaml"]
        else:
            raise ValueError(kind)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr)
        return r.returncode == 0 and "CONFIG ERROR" not in out and "level=error" not in out, out[-600:]
    finally:
        shutil.rmtree(d, ignore_errors=True)


# =====================================================================================================================
# 5. HPA
# =====================================================================================================================
def hpa_desired(current: int, metric: float, target: float, min_replicas: int = 1, max_replicas: int = 10, tolerance: float = 0.1) -> int:
    """Algoritmo del HPA: ``desired = ceil(current × métrica / objetivo)``; si ``|métrica/objetivo − 1| ≤ tolerancia`` (0,1 por defecto) no se hace nada; se acota a [min, max]."""
    ratio = metric / target
    if abs(ratio - 1.0) <= tolerance:
        desired = current
    else:
        desired = math.ceil(current * ratio)
    return max(min_replicas, min(max_replicas, desired))


def hpa_simulate(load: Sequence[float], capacity_per_pod: float, target_util: float = 0.7, min_replicas: int = 2, max_replicas: int = 10, step_s: float = 15.0,
                 scale_down_window_s: float = 300.0, start: int | None = None) -> dict[str, list[float]]:
    """Simula un HPA sobre una carga (unidades de trabajo por segundo): utilización = carga / (réplicas × capacidad). Escalar hacia arriba es inmediato en cada paso;
    hacia abajo se usa el **máximo** de las recomendaciones de la ventana de estabilización (como ``behavior.scaleDown.stabilizationWindowSeconds``)."""
    cur = start or min_replicas
    reps, util, rec = [], [], []
    win = max(1, int(scale_down_window_s / step_s))
    for t, ld in enumerate(load):
        u = ld / (cur * capacity_per_pod)
        d = hpa_desired(cur, u, target_util, min_replicas, max_replicas)
        rec.append(d)
        if d > cur:
            cur = d
        elif d < cur:
            cur = min(cur, max(max(rec[-win:]), min_replicas))      # ventana de estabilización: la recomendación MÁS ALTA de la ventana
        reps.append(cur)
        util.append(u)
    return {"replicas": reps, "utilization": util, "recommended": rec}


# =====================================================================================================================
# 6. Ejecutor de tráfico que corre DENTRO del pod (imagen de laboratorio)
# =====================================================================================================================
def run_traffic(rate: float | None = None, seconds: float | None = None, seed: int | None = None) -> dict[str, Any]:
    """Bucle de SupportOps para un pod: cada segundo genera ``rate`` tickets «en vivo» y los atiende con la telemetría OTLP configurada por variables de entorno
    (``OTEL_EXPORTER_OTLP_ENDPOINT``, ``OTEL_SERVICE_NAME``, ``OTEL_RESOURCE_ATTRIBUTES``). ``seconds=None``/0 → hasta ser terminado (SIGTERM)."""
    import signal

    from . import DEFAULT_FAULT_RATES, SupportAgent, generate_tickets
    from .telemetry import OTelInstrumentor, setup_telemetry
    rate = float(os.environ.get("SUPPORTOPS_RATE", "4")) if rate is None else rate
    seed = int(os.environ.get("SUPPORTOPS_SEED", "42")) if seed is None else seed
    faults = None if os.environ.get("SUPPORTOPS_FAULT_PROFILE", "default") == "none" else DEFAULT_FAULT_RATES
    attrs = dict(kv.split("=", 1) for kv in os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").split(",") if "=" in kv)
    tel = setup_telemetry(os.environ.get("OTEL_SERVICE_NAME", "supportops-agent"), mode="otlp", resource_attrs=attrs, metric_interval_s=5)
    agent = SupportAgent(instrumentor=OTelInstrumentor(tel))
    stop = {"flag": False}
    signal.signal(signal.SIGTERM, lambda *_: stop.update(flag=True))
    t0, n, tick = time.time(), 0, 0
    while not stop["flag"] and (not seconds or time.time() - t0 < seconds):
        batch = max(1, int(round(rate)))
        for t in generate_tickets(batch, seed=seed + tick, duration_s=1.0, fault_rates=faults, start_s="live"):
            agent.run(t)
            n += 1
        tick += 1
        time.sleep(max(0.0, 1.0 - ((time.time() - t0) % 1.0)))
    tel.force_flush(10)
    tel.shutdown()
    return {"tickets": n, "seconds": round(time.time() - t0, 1)}


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["run"]:
        secs = float(argv[argv.index("--seconds") + 1]) if "--seconds" in argv else None
        print(json.dumps(run_traffic(seconds=secs)))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
