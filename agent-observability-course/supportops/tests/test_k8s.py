"""Pruebas del módulo 19 (Kubernetes + Helm). Las que necesitan helm/Docker se saltan si no están."""
from __future__ import annotations

import pytest

from supportops import k8s as K


def test_deep_merge_helm_semantics():
    base = {"a": {"x": 1, "y": [1, 2]}, "b": 2, "c": {"d": 1}}
    over = {"a": {"y": [9]}, "b": None, "c": {"e": 2}}
    assert K.deep_merge(base, over) == {"a": {"x": 1, "y": [9]}, "c": {"d": 1, "e": 2}}
    assert base["a"]["y"] == [1, 2]                                   # no muta la entrada
    assert K.helm_values({"a": 1}, {"a": 2}, {"b": 3}) == {"a": 2, "b": 3}


def test_hpa_desired_and_tolerance():
    assert K.hpa_desired(2, 140, 70) == 4
    assert K.hpa_desired(4, 74, 70) == 4                              # dentro de la tolerancia del 10 %
    assert K.hpa_desired(4, 20, 70, min_replicas=2) == 2
    assert K.hpa_desired(3, 1000, 70, max_replicas=6) == 6


def test_hpa_simulation_scales_up_fast_and_down_slowly():
    load = [100] * 10 + [400] * 20 + [100] * 60
    r = K.hpa_simulate(load, capacity_per_pod=100, target_util=0.7, min_replicas=2, max_replicas=8, step_s=15, scale_down_window_s=300)
    reps = r["replicas"]
    assert max(reps) >= 5 and reps[0] == 2
    up = next(i for i, x in enumerate(reps) if x >= 5)
    assert up <= 11                                                   # sube en cuanto llega la carga
    first_down = next(i for i in range(30, len(reps)) if reps[i] < max(reps))
    assert first_down - 30 >= 15                                      # la ventana de estabilización retrasa la bajada (≥ 15 pasos de 15 s)


def test_quantities_and_requests():
    assert K._parse_quantity("250m", "cpu") == 250 and K._parse_quantity("2", "cpu") == 2000
    assert K._parse_quantity("1Gi", "mem") == 1024 and K._parse_quantity("512Mi", "mem") == 512
    ms = [{"kind": "Deployment", "spec": {"replicas": 3, "template": {"spec": {"containers": [{"resources": {"requests": {"cpu": "100m", "memory": "128Mi"}}}]}}}},
          {"kind": "DaemonSet", "spec": {"template": {"spec": {"containers": [{"resources": {"requests": {"cpu": "50m", "memory": "64Mi"}}}]}}}},
          {"kind": "ConfigMap"}]
    assert K.resource_requests(ms) == {"cpu_m": 350.0, "memory_mib": 448.0}


def test_chart_refs_and_versions():
    assert K.CHARTS["otel-collector"].app_version == "0.162.0" and K.CHARTS["tempo"].app_version == "3.1.0" and K.CHARTS["loki"].app_version == "3.7.8"
    assert K.chart_ref("supportops").endswith("charts/supportops") and K.chart_ref("tempo") in ("grafana-community/tempo",) or "tempo" in K.chart_ref("tempo")


needs_helm = pytest.mark.skipif(K._which("helm", "HELM") is None, reason="helm no instalado")


@needs_helm
def test_own_charts_render_lint_and_schema():
    ms = K.render("sup", "supportops", [K.K8S_DIR / "values" / "supportops-lab.yaml"], namespace="supportops")
    kinds = K.kinds_count(ms)
    assert kinds["Deployment"] == 1 and kinds["HorizontalPodAutoscaler"] == 1 and kinds["PodDisruptionBudget"] == 1
    dep = next(m for m in ms if m["kind"] == "Deployment")
    assert "replicas" not in dep["spec"]                              # con HPA el chart no fija replicas
    ctr = dep["spec"]["template"]["spec"]["containers"][0]
    assert ctr["securityContext"]["readOnlyRootFilesystem"] is True and dep["spec"]["template"]["spec"]["securityContext"]["runAsNonRoot"] is True
    assert "checksum/config" in dep["spec"]["template"]["metadata"]["annotations"]
    ok, _ = K.lint("supportops", [K.K8S_DIR / "values" / "supportops-lab.yaml"])
    assert ok
    with pytest.raises(RuntimeError):                                  # values.schema.json rechaza un valor fuera de rango
        K.render("sup", "supportops", [{"traffic": {"ratePerSecond": 9999}}])
    prom = K.render("prometheus", "prom-lab")
    assert K.kinds_count(prom)["Deployment"] == 1


def test_deep_merge_matches_helm_on_pipelines():
    """Las listas se REEMPLAZAN: el mismo resultado que ``helm template`` (se comprueba contra el chart si está disponible)."""
    if K._which("helm", "HELM") is None or K.chart_path("otel-collector") is None:
        pytest.skip("helm o el chart del Collector no disponibles")
    import yaml
    base_defaults = yaml.safe_load(open(K.chart_path("otel-collector") + "/values.yaml"))
    over = {"config": {"service": {"pipelines": {"logs": {"exporters": ["debug", "otlp_http/loki"]}}}}}
    merged = K.deep_merge(base_defaults, over)
    assert merged["config"]["service"]["pipelines"]["logs"]["exporters"] == ["debug", "otlp_http/loki"]
    assert merged["config"]["service"]["pipelines"]["logs"]["receivers"] == ["otlp"]
    ms = K.render("g", "otel-collector", [over, {"mode": "deployment", "image": {"repository": "otel/opentelemetry-collector-contrib"}}])
    cfg = yaml.safe_load(K.configmap_text(ms, "g", "relay"))
    assert cfg["service"]["pipelines"]["logs"]["exporters"] == ["debug", "otlp_http/loki"]


@needs_helm
def test_gateway_values_render_with_tail_sampling():
    import sys, pathlib
    sys.path.insert(0, str(K.COURSE / "_tools" / "builders"))
    ms = K.render("otel-gateway", "otel-collector", [K.K8S_DIR / "values" / "otel-gateway.yaml"]) if K.chart_path("otel-collector") else None
    if ms is None:
        pytest.skip("chart del Collector no disponible")
    import yaml
    cfg = yaml.safe_load(K.configmap_text(ms, "otel-gateway", "relay"))
    assert [p["name"] for p in cfg["processors"]["tail_sampling"]["policies"]] == ["errors", "slow", "costly", "baseline"]
    pipes = cfg["service"]["pipelines"]
    assert pipes["traces/in"]["exporters"] == ["forward", "span_metrics"] and "traces" not in pipes
    assert K.kinds_count(ms)["HorizontalPodAutoscaler"] == 1 and K.kinds_count(ms)["PodDisruptionBudget"] == 1
    kc = K.kubeconform(ms)
    assert kc["invalid"] == 0
