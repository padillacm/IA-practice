"""Genera el módulo 19_kubernetes_helm: README, lección, proyecto, chart propio de SupportOps, values de Helm, CRs del Operator y dashboard 19.

Ejecutar desde la raíz del repo:
    python agent-observability-course/_tools/builders/build_19.py            # notebooks + README + k8s/ + dashboard
    python agent-observability-course/_tools/builders/build_19.py --record   # regenera recorded/capture_seed42.json.gz (necesita Docker, helm y los charts)
"""
from __future__ import annotations

import gzip
import json
import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "19_kubernetes_helm"
MODDIR = COURSE / MOD
K8S = MODDIR / "k8s"
RECORDED = MODDIR / "recorded" / "capture_seed42.json.gz"
NS = "observability"


def mdj(head: str, *items: str) -> str:
    return textwrap.dedent(head).strip("\n") + "\n\n" + "\n\n".join(items)


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.lstrip("\n"), encoding="utf-8")


# =====================================================================================================================
# 1. Chart propio: supportops (el agente de laboratorio que genera tráfico real contra el Collector)
# =====================================================================================================================
CHART_YAML = """apiVersion: v2
name: supportops
description: SupportOps - agente de soporte de laboratorio que emite trazas, logs y métricas OTLP (curso de observabilidad de agentes, módulo 19)
type: application
version: 0.1.0
appVersion: "0.1.0-m19"
keywords: [observabilidad, opentelemetry, agentes]
"""

CHART_VALUES = """# Valores por defecto del chart supportops. Cada clave está documentada y validada por values.schema.json.
replicaCount: 2

image:
  repository: supportops
  tag: lab                         # imagen de laboratorio (se construye con 19_kubernetes_helm/k8s/image/Dockerfile y se carga en el clúster)
  pullPolicy: IfNotPresent

serviceAccount:
  create: true
  name: ""

# Dónde envía OTLP el agente: el Service «otel-agent» del DaemonSet (values/otel-agent.yaml activa `service.enabled`; el chart lo crea con internalTrafficPolicy: Local, es decir, el tráfico va al agente de SU nodo).
otlp:
  endpoint: "http://otel-agent.observability.svc.cluster.local:4318"
  serviceName: supportops-agent

# Generador de tráfico sintético (el mismo de los módulos anteriores: semilla fija, fallos inyectados)
traffic:
  ratePerSecond: 4
  seed: 42
  faultProfile: default            # default | none

resources:
  requests: {cpu: 100m, memory: 128Mi}
  limits: {memory: 256Mi}

autoscaling:
  enabled: false
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70

podDisruptionBudget:
  enabled: true
  minAvailable: 1

podAnnotations: {}
nodeSelector: {}
tolerations: []
affinity: {}
"""

CHART_SCHEMA = json.dumps({
    "$schema": "https://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["image", "otlp", "traffic", "resources"],
    "properties": {
        "replicaCount": {"type": "integer", "minimum": 0},
        "image": {"type": "object", "required": ["repository", "tag"], "properties": {"repository": {"type": "string", "minLength": 1}, "tag": {"type": "string", "minLength": 1},
                                                                                 "pullPolicy": {"enum": ["Always", "IfNotPresent", "Never"]}}},
        "otlp": {"type": "object", "required": ["endpoint"], "properties": {"endpoint": {"type": "string", "pattern": "^https?://"}, "serviceName": {"type": "string"}}},
        "traffic": {"type": "object", "properties": {"ratePerSecond": {"type": "number", "minimum": 0, "maximum": 200}, "seed": {"type": "integer"}, "faultProfile": {"enum": ["default", "none"]}}},
        "resources": {"type": "object", "required": ["requests"], "properties": {"requests": {"type": "object", "required": ["cpu", "memory"]}}},
        "autoscaling": {"type": "object", "properties": {"enabled": {"type": "boolean"}, "minReplicas": {"type": "integer", "minimum": 1}, "maxReplicas": {"type": "integer", "minimum": 1},
                                                          "targetCPUUtilizationPercentage": {"type": "integer", "minimum": 1, "maximum": 100}}},
        "podDisruptionBudget": {"type": "object", "properties": {"enabled": {"type": "boolean"}}},
    },
}, indent=2, ensure_ascii=False) + "\n"

CHART_HELPERS = """{{- define "supportops.name" -}}{{ .Chart.Name }}{{- end -}}
{{- define "supportops.fullname" -}}{{ .Release.Name }}-{{ .Chart.Name }}{{- end -}}
{{- define "supportops.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "supportops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
{{- define "supportops.selectorLabels" -}}
app.kubernetes.io/name: {{ include "supportops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
{{- define "supportops.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}{{ default (include "supportops.fullname" .) .Values.serviceAccount.name }}{{- else -}}{{ default "default" .Values.serviceAccount.name }}{{- end -}}
{{- end -}}
"""

CHART_DEPLOYMENT = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "supportops.fullname" . }}
  labels:
    {{- include "supportops.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "supportops.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
        {{- with .Values.podAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      labels:
        {{- include "supportops.selectorLabels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "supportops.serviceAccountName" . }}
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: agent
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          args: ["python", "-m", "supportops.k8s", "run"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          env:
            - name: LLM_PROVIDER
              value: mock
            - name: K8S_POD_NAME
              valueFrom: {fieldRef: {fieldPath: metadata.name}}
            - name: K8S_NAMESPACE
              valueFrom: {fieldRef: {fieldPath: metadata.namespace}}
            - name: K8S_NODE_NAME
              valueFrom: {fieldRef: {fieldPath: spec.nodeName}}
            - name: OTEL_SERVICE_NAME
              value: {{ .Values.otlp.serviceName | quote }}
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: {{ .Values.otlp.endpoint | quote }}
            - name: OTEL_RESOURCE_ATTRIBUTES
              value: "k8s.pod.name=$(K8S_POD_NAME),k8s.namespace.name=$(K8S_NAMESPACE),k8s.node.name=$(K8S_NODE_NAME),service.version={{ .Chart.AppVersion }}"
          envFrom:
            - configMapRef:
                name: {{ include "supportops.fullname" . }}
          # El proceso no abre ningún puerto: la vivacidad se comprueba con un «latido» (fichero tocado en cada ciclo del bucle de tráfico).
          livenessProbe:
            exec:
              command: ["python", "-c", "import os,sys,time; sys.exit(0 if time.time() - os.path.getmtime('/tmp/heartbeat') < 90 else 1)"]
            initialDelaySeconds: 45
            periodSeconds: 30
            timeoutSeconds: 10
            failureThreshold: 3
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
      {{- with .Values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.tolerations }}
      tolerations:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      {{- with .Values.affinity }}
      affinity:
        {{- toYaml . | nindent 8 }}
      {{- end }}
"""

CHART_CONFIGMAP = """apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "supportops.fullname" . }}
  labels:
    {{- include "supportops.labels" . | nindent 4 }}
data:
  SUPPORTOPS_RATE: {{ .Values.traffic.ratePerSecond | quote }}
  SUPPORTOPS_SEED: {{ .Values.traffic.seed | quote }}
  SUPPORTOPS_FAULT_PROFILE: {{ .Values.traffic.faultProfile | quote }}
"""

CHART_HPA = """{{- if .Values.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "supportops.fullname" . }}
  labels:
    {{- include "supportops.labels" . | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "supportops.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
"""

CHART_PDB = """{{- if .Values.podDisruptionBudget.enabled }}
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: {{ include "supportops.fullname" . }}
  labels:
    {{- include "supportops.labels" . | nindent 4 }}
spec:
  minAvailable: {{ .Values.podDisruptionBudget.minAvailable }}
  selector:
    matchLabels:
      {{- include "supportops.selectorLabels" . | nindent 6 }}
{{- end }}
"""

CHART_SA = """{{- if .Values.serviceAccount.create }}
apiVersion: v1
kind: ServiceAccount
metadata:
  name: {{ include "supportops.serviceAccountName" . }}
  labels:
    {{- include "supportops.labels" . | nindent 4 }}
automountServiceAccountToken: false
{{- end }}
"""

CHART_NOTES = """SupportOps desplegado: {{ include "supportops.fullname" . }} ({{ .Values.replicaCount }} réplicas).
Envía OTLP a {{ .Values.otlp.endpoint }} con service.name={{ .Values.otlp.serviceName }}.
Comprueba: kubectl -n {{ .Release.Namespace }} logs deploy/{{ include "supportops.fullname" . }} --tail=5
"""

# =====================================================================================================================
# 2. Chart propio: prom-lab (Prometheus mínimo con receptor OTLP; evita el chart oficial, que arrastra kube-state-metrics, alertmanager...)
# =====================================================================================================================
PROM_CHART_YAML = """apiVersion: v2
name: prom-lab
description: Prometheus mínimo de laboratorio con receptor OTLP (curso de observabilidad de agentes, módulo 19)
type: application
version: 0.1.0
appVersion: "v3.15.0"
"""
PROM_VALUES = """image:
  repository: prom/prometheus
  tag: v3.15.0
resources:
  requests: {cpu: 50m, memory: 128Mi}
  limits: {memory: 512Mi}
retention: 2d
# Se raspa la telemetría interna de las réplicas del gateway por DNS (Service headless: una A por pod)
scrapeGatewayHost: otel-gateway-headless.observability.svc.cluster.local
scrapeGatewayPort: 8888
"""
PROM_DEPLOY = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
  labels: {app.kubernetes.io/name: prom-lab, app.kubernetes.io/instance: {{ .Release.Name }}}
spec:
  replicas: 1
  strategy: {type: Recreate}
  selector:
    matchLabels: {app.kubernetes.io/name: prom-lab, app.kubernetes.io/instance: {{ .Release.Name }}}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
      labels: {app.kubernetes.io/name: prom-lab, app.kubernetes.io/instance: {{ .Release.Name }}}
    spec:
      securityContext: {runAsNonRoot: true, runAsUser: 65534, fsGroup: 65534, seccompProfile: {type: RuntimeDefault}}
      containers:
        - name: prometheus
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          args:
            - --config.file=/etc/prometheus/prometheus.yml
            - --storage.tsdb.path=/prometheus
            - --storage.tsdb.retention.time={{ .Values.retention }}
            - --web.enable-otlp-receiver
          ports: [{name: http, containerPort: 9090}]
          readinessProbe: {httpGet: {path: /-/ready, port: http}}
          livenessProbe: {httpGet: {path: /-/healthy, port: http}}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
          securityContext: {allowPrivilegeEscalation: false, capabilities: {drop: [ALL]}}
          volumeMounts:
            - {name: config, mountPath: /etc/prometheus}
            - {name: data, mountPath: /prometheus}
      volumes:
        - name: config
          configMap: {name: {{ .Release.Name }}}
        - name: data
          emptyDir: {}
"""
PROM_SVC = """apiVersion: v1
kind: Service
metadata:
  name: {{ .Release.Name }}
  labels: {app.kubernetes.io/name: prom-lab, app.kubernetes.io/instance: {{ .Release.Name }}}
spec:
  selector: {app.kubernetes.io/name: prom-lab, app.kubernetes.io/instance: {{ .Release.Name }}}
  ports: [{name: http, port: 9090, targetPort: http}]
"""
PROM_CM = """apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
      - job_name: otel-gateway
        dns_sd_configs:
          - names: ["{{ .Values.scrapeGatewayHost }}"]
            type: A
            port: {{ .Values.scrapeGatewayPort }}
"""

# =====================================================================================================================
# 3. Values de los charts oficiales (configuración como código)
# =====================================================================================================================
DOMAIN = "svc.cluster.local"


def gateway_values(policies_yaml: str | None = None, replicas: int = 2, autoscaling: bool = True, decision_wait: str = "10s", num_traces: int = 20000) -> dict:
    """values del chart opentelemetry-collector para el GATEWAY (Deployment): span_metrics ANTES del muestreo + tail_sampling + exportación a Tempo/Loki/Prometheus."""
    policies = policies_yaml or [
        {"name": "errors", "type": "status_code", "status_code": {"status_codes": ["ERROR"]}},
        {"name": "slow", "type": "latency", "latency": {"threshold_ms": 5000}},
        {"name": "costly", "type": "ottl_condition", "ottl_condition": {"error_mode": "ignore", "span": ['attributes["supportops.cost_usd"] > 0.0005']}},
        {"name": "baseline", "type": "probabilistic", "probabilistic": {"sampling_percentage": 10}},
    ]
    v: dict = {
        "fullnameOverride": "otel-gateway",
        "mode": "deployment",
        "replicaCount": replicas,
        "image": {"repository": "otel/opentelemetry-collector-contrib", "tag": "0.162.0"},
        "command": {"name": "otelcol-contrib"},
        "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}, "limits": {"memory": "512Mi"}},
        "podDisruptionBudget": {"enabled": True, "minAvailable": 1},
        "autoscaling": {"enabled": autoscaling, "minReplicas": replicas, "maxReplicas": 6, "targetCPUUtilizationPercentage": 70,
                        "behavior": {"scaleDown": {"stabilizationWindowSeconds": 600, "policies": [{"type": "Pods", "value": 1, "periodSeconds": 120}]}}},
        "ports": {"jaeger-compact": {"enabled": False}, "jaeger-thrift": {"enabled": False}, "jaeger-grpc": {"enabled": False}, "zipkin": {"enabled": False}},
        "extraManifests": [{"apiVersion": "v1", "kind": "Service", "metadata": {"name": "otel-gateway-headless"},
                            "spec": {"clusterIP": "None", "selector": {"app.kubernetes.io/name": "opentelemetry-collector", "app.kubernetes.io/instance": "otel-gateway"},
                                     "ports": [{"name": "otlp-grpc", "port": 4317, "targetPort": 4317}, {"name": "metrics", "port": 8888, "targetPort": 8888}]}}],
        "config": {
            "receivers": {"jaeger": None, "zipkin": None, "prometheus": None},
            "connectors": {"forward": {}, "span_metrics": {"histogram": {"explicit": {"buckets": ["100ms", "500ms", "1s", "2s", "5s", "10s"]}}, "metrics_flush_interval": "15s"}},
            "processors": {"tail_sampling": {"decision_wait": decision_wait, "num_traces": num_traces, "expected_new_traces_per_sec": 50, "policies": policies}},
            "exporters": {"debug": None,
                          "otlp_grpc/tempo": {"endpoint": f"tempo.{NS}.{DOMAIN}:4317", "tls": {"insecure": True}},
                          "otlp_http/loki": {"endpoint": f"http://loki.{NS}.{DOMAIN}:3100/otlp"},
                          "otlp_http/prometheus": {"endpoint": f"http://prometheus.{NS}.{DOMAIN}:9090/api/v1/otlp"}},
            "service": {"pipelines": {
                "traces": None,
                "traces/in": {"receivers": ["otlp"], "processors": ["memory_limiter"], "exporters": ["forward", "span_metrics"]},
                "traces/sampled": {"receivers": ["forward"], "processors": ["memory_limiter", "tail_sampling", "batch"], "exporters": ["otlp_grpc/tempo"]},
                "metrics": {"receivers": ["otlp", "span_metrics"], "processors": ["memory_limiter", "batch"], "exporters": ["otlp_http/prometheus"]},
                "logs": {"receivers": ["otlp"], "processors": ["memory_limiter", "batch"], "exporters": ["otlp_http/loki"]}}},
        },
    }
    return v


def agent_values() -> dict:
    """values del chart opentelemetry-collector para el AGENTE (DaemonSet): metadatos de K8s + balanceo por traceID hacia el gateway (afinidad para tail sampling)."""
    return {
        "fullnameOverride": "otel-agent",
        "mode": "daemonset",
        "image": {"repository": "otel/opentelemetry-collector-contrib", "tag": "0.162.0"},
        "command": {"name": "otelcol-contrib"},
        "presets": {"kubernetesAttributes": {"enabled": True}},
        "service": {"enabled": True},            # en modo daemonset el chart NO crea Service por defecto: lo necesitan los pods (otel-agent.observability:4318)
        "resources": {"requests": {"cpu": "50m", "memory": "128Mi"}, "limits": {"memory": "256Mi"}},
        "ports": {"jaeger-compact": {"enabled": False}, "jaeger-thrift": {"enabled": False}, "jaeger-grpc": {"enabled": False}, "zipkin": {"enabled": False},
                  "otlp": {"enabled": True, "hostPort": 4317}, "otlp-http": {"enabled": True, "hostPort": 4318}},
        "config": {
            "receivers": {"jaeger": None, "zipkin": None, "prometheus": None},
            "exporters": {"debug": None,
                          "load_balancing": {"routing_key": "traceID", "protocol": {"otlp": {"tls": {"insecure": True}, "timeout": "10s"}},
                                             "resolver": {"dns": {"hostname": f"otel-gateway-headless.{NS}.{DOMAIN}", "port": "4317", "interval": "15s"}}},
                          "otlp_grpc/gateway": {"endpoint": f"otel-gateway.{NS}.{DOMAIN}:4317", "tls": {"insecure": True}}},
            "service": {"pipelines": {
                "traces": {"receivers": ["otlp"], "processors": ["k8s_attributes", "memory_limiter", "batch"], "exporters": ["load_balancing"]},
                "metrics": {"receivers": ["otlp"], "processors": ["k8s_attributes", "memory_limiter", "batch"], "exporters": ["otlp_grpc/gateway"]},
                "logs": {"receivers": ["otlp"], "processors": ["k8s_attributes", "memory_limiter", "batch"], "exporters": ["otlp_grpc/gateway"]}}},
        },
    }


def tempo_values() -> dict:
    return {"tempo": {"registry": "docker.io", "repository": "grafana/tempo", "tag": "3.1.0", "reportingEnabled": False, "streamOverHttpEnabled": True,
                      "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}, "limits": {"memory": "768Mi"}},
                      "liveStore": {"max_block_duration": "5m", "wal": {"ingestion_time_range_slack": "15m"}}},
            "persistence": {"enabled": False}}


def loki_values() -> dict:
    return {"deploymentMode": "SingleBinary",
            "loki": {"auth_enabled": False, "commonConfig": {"replication_factor": 1}, "storage": {"type": "filesystem"},
                     "schemaConfig": {"configs": [{"from": "2024-04-01", "store": "tsdb", "object_store": "filesystem", "schema": "v13", "index": {"prefix": "index_", "period": "24h"}}]},
                     "limits_config": {"allow_structured_metadata": True, "retention_period": "168h"},
                     "image": {"registry": "docker.io", "repository": "grafana/loki", "tag": "3.7.8"}, "useTestSchema": False},
            "singleBinary": {"replicas": 1, "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}, "limits": {"memory": "768Mi"}}, "persistence": {"enabled": False}},
            "backend": {"replicas": 0}, "read": {"replicas": 0}, "write": {"replicas": 0},
            "chunksCache": {"enabled": False}, "resultsCache": {"enabled": False}, "gateway": {"enabled": False}, "lokiCanary": {"enabled": False}, "test": {"enabled": False},
            "sidecar": {"rules": {"enabled": False}}, "minio": {"enabled": False}}


def grafana_values() -> dict:
    ds = {"apiVersion": 1, "datasources": [
        {"name": "Tempo", "uid": "tempo", "type": "tempo", "access": "proxy", "url": f"http://tempo.{NS}.{DOMAIN}:3200", "jsonData": {
            "tracesToLogsV2": {"datasourceUid": "loki", "filterByTraceID": True, "customQuery": True, "query": '{service_name="${__span.tags["service.name"]}"} | trace_id="${__trace.traceId}"'}}},
        {"name": "Loki", "uid": "loki", "type": "loki", "access": "proxy", "url": f"http://loki.{NS}.{DOMAIN}:3100",
         "jsonData": {"derivedFields": [{"name": "trace_id", "matcherType": "label", "matcherRegex": "trace_id", "url": "${__value.raw}", "datasourceUid": "tempo"}]}},
        {"name": "Prometheus", "uid": "prometheus", "type": "prometheus", "access": "proxy", "url": f"http://prometheus.{NS}.{DOMAIN}:9090", "isDefault": True}]}
    return {"image": {"registry": "docker.io", "repository": "grafana/grafana", "tag": "13.2.4"}, "adminUser": "admin", "adminPassword": "admin",   # SOLO laboratorio
            "persistence": {"enabled": False}, "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}, "limits": {"memory": "512Mi"}},
            "sidecar": {"dashboards": {"enabled": False}, "datasources": {"enabled": False}},
            "datasources": {"datasources.yaml": ds}, "initChownData": {"enabled": False}, "testFramework": {"enabled": False}, "env": {"GF_ANALYTICS_REPORTING_ENABLED": "false"}}


def to_yaml(obj) -> str:
    sys.path.insert(0, str(COURSE))
    from supportops.sampling import to_yaml as _y
    return _y(obj)


# =====================================================================================================================
# 4. Archivos del módulo (k8s/): chart propio, values, Operator, kind, imagen
# =====================================================================================================================
KIND_CONFIG = """# Clúster local con kind (https://kind.sigs.k8s.io). Úsalo en TU máquina: kind create cluster --name obs19 --config kind-config.yaml --image kindest/node:v1.34.0
# (En el sandbox de construcción de este curso kind NO pudo arrancar pods: runc anidado fallaba; ver el README del módulo.)
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
    kubeadmConfigPatches:
      - |
        kind: InitConfiguration
        nodeRegistration:
          kubeletExtraArgs:
            node-labels: "ingress-ready=true"
    extraPortMappings:
      - {containerPort: 30300, hostPort: 3000, protocol: TCP}      # Grafana (NodePort 30300)
"""

DOCKERFILE = """# Imagen de laboratorio de SupportOps (módulo 19). Construcción SIN red de pip si primero descargas las ruedas:
#   pip download -d wheels "opentelemetry-sdk>=1.39" "opentelemetry-exporter-otlp-proto-http>=1.39"
#   docker build -f 19_kubernetes_helm/k8s/image/Dockerfile -t supportops:lab .      (contexto = agent-observability-course/)
#   kind load docker-image supportops:lab --name obs19
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY pyproject.toml ./pyproject.toml
COPY supportops ./supportops
RUN pip install --no-cache-dir ".[otel]"
USER 10001
ENTRYPOINT []
CMD ["python", "-m", "supportops.k8s", "run"]
"""

OPERATOR_VALUES = """# opentelemetry-operator (chart 0.126.0, operator 0.161.0). Requiere Helm 4+ (README del chart).
# Los CRDs van PLANTILLADOS en el chart (no se pueden saltar con --skip-crds): crds.create=false si ya los gestionas aparte.
manager:
  collectorImage:
    repository: otel/opentelemetry-collector-contrib      # el chart exige elegir la distribución del Collector que lanzará el operador
admissionWebhooks:
  certManager:
    enabled: false                  # sin cert-manager: el propio chart genera un certificado autofirmado
  autoGenerateCert:
    enabled: true
replicaCount: 1
"""

COLLECTOR_CR = """# OpenTelemetryCollector (CRD v1beta1): el operador crea el Deployment, Service, ConfigMap, HPA y PDB. Versión SIMPLIFICADA del gateway de los values de Helm (sin la política «costly», sin span_metrics y solo con el exportador de trazas): sirve para validar el CRD, no como sustituto completo.
apiVersion: opentelemetry.io/v1beta1
kind: OpenTelemetryCollector
metadata:
  name: gateway
  namespace: observability
spec:
  mode: deployment
  image: otel/opentelemetry-collector-contrib:0.162.0
  replicas: 2
  resources:
    requests: {cpu: 100m, memory: 256Mi}
    limits: {memory: 512Mi}
  autoscaler:
    minReplicas: 2
    maxReplicas: 6
    targetCPUUtilization: 70
  podDisruptionBudget:
    minAvailable: 1
  config:                               # en v1beta1 la configuración es YAML estructurado (no una cadena)
    receivers:
      otlp:
        protocols:
          grpc: {endpoint: 0.0.0.0:4317}
          http: {endpoint: 0.0.0.0:4318}
    processors:
      memory_limiter: {check_interval: 5s, limit_percentage: 80, spike_limit_percentage: 25}
      batch: {}
      tail_sampling:
        decision_wait: 10s
        num_traces: 20000
        policies:
          - {name: errors, type: status_code, status_code: {status_codes: [ERROR]}}
          - {name: slow, type: latency, latency: {threshold_ms: 5000}}
          - {name: baseline, type: probabilistic, probabilistic: {sampling_percentage: 10}}
    exporters:
      otlp_grpc/tempo: {endpoint: "tempo.observability.svc.cluster.local:4317", tls: {insecure: true}}
    service:
      pipelines:
        traces:
          receivers: [otlp]
          processors: [memory_limiter, tail_sampling, batch]
          exporters: [otlp_grpc/tempo]
"""

INSTRUMENTATION_CR = """# Instrumentation (CRD v1alpha1): auto-instrumentación por inyección de un init container con el SDK de Python al anotar un Deployment:
#   metadata.annotations: instrumentation.opentelemetry.io/inject-python: "true"     (o «<namespace>/<nombre>» para otra Instrumentation)
apiVersion: opentelemetry.io/v1alpha1
kind: Instrumentation
metadata:
  name: supportops-python
  namespace: supportops
spec:
  exporter:
    endpoint: http://otel-agent.observability.svc.cluster.local:4318
  propagators: [tracecontext, baggage]
  sampler:
    type: parentbased_always_on          # NO muestrear en el SDK: el tail_sampling del gateway decide (módulo 18: las probabilidades se multiplican y se pierden errores)
  python:
    env:
      - {name: OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED, value: "true"}
"""

SUPPORTOPS_VALUES_LAB = """# Valores de laboratorio del chart supportops.
replicaCount: 2
otlp:
  endpoint: http://otel-agent.observability.svc.cluster.local:4318
traffic:
  ratePerSecond: 4
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 6
  targetCPUUtilizationPercentage: 70
"""


def build_k8s_files() -> None:
    c = K8S / "charts" / "supportops"
    write(c / "Chart.yaml", CHART_YAML)
    write(c / "values.yaml", CHART_VALUES)
    write(c / "values.schema.json", CHART_SCHEMA)
    write(c / ".helmignore", "*.swp\n.git\n")
    for name, text in (("_helpers.tpl", CHART_HELPERS), ("deployment.yaml", CHART_DEPLOYMENT), ("configmap.yaml", CHART_CONFIGMAP), ("hpa.yaml", CHART_HPA), ("pdb.yaml", CHART_PDB),
                       ("serviceaccount.yaml", CHART_SA), ("NOTES.txt", CHART_NOTES)):
        write(c / "templates" / name, text)
    p = K8S / "charts" / "prom-lab"
    write(p / "Chart.yaml", PROM_CHART_YAML)
    write(p / "values.yaml", PROM_VALUES)
    for name, text in (("deployment.yaml", PROM_DEPLOY), ("service.yaml", PROM_SVC), ("configmap.yaml", PROM_CM)):
        write(p / "templates" / name, text)
    v = K8S / "values"
    hdr = lambda t: f"# {t}\n# Generado por _tools/builders/build_19.py (config como código en Python → YAML). Los `null` borran claves heredadas del chart (semántica de Helm).\n"
    write(v / "otel-gateway.yaml", hdr("Gateway del Collector (Deployment): span_metrics ANTES del muestreo, tail_sampling, exporta a Tempo/Loki/Prometheus. chart opentelemetry-collector 0.176.0 (app 0.162.0)") + to_yaml(gateway_values()))
    write(v / "otel-agent.yaml", hdr("Agente del Collector (DaemonSet): k8s_attributes + load_balancing por traceID hacia el gateway (afinidad para tail sampling)") + to_yaml(agent_values()))
    write(v / "tempo.yaml", hdr("Tempo 3.1.0 monolítico (chart grafana-community/tempo 3.2.0)") + to_yaml(tempo_values()))
    write(v / "loki.yaml", hdr("Loki 3.7.8 SingleBinary con sistema de ficheros (chart grafana-community/loki 18.16.0)") + to_yaml(loki_values()))
    write(v / "grafana.yaml", hdr("Grafana 13.2.4 con datasources por código (chart grafana-community/grafana 14.0.0). adminPassword SOLO para laboratorio") + to_yaml(grafana_values()))
    write(v / "supportops-lab.yaml", SUPPORTOPS_VALUES_LAB)
    o = K8S / "operator"
    write(o / "values-operator.yaml", OPERATOR_VALUES)
    write(o / "collector-gateway.yaml", COLLECTOR_CR)
    write(o / "instrumentation.yaml", INSTRUMENTATION_CR)
    write(K8S / "kind-config.yaml", KIND_CONFIG)
    write(K8S / "image" / "Dockerfile", DOCKERFILE)
    print("OK k8s/:", sorted(str(p.relative_to(K8S)) for p in K8S.rglob("*") if p.is_file()))

# =====================================================================================================================
# 5. Dashboard 19 (métricas del gateway: lo que el Prometheus del chart prom-lab recoge de las réplicas)
# =====================================================================================================================
DASH_UID = "k8s-gateway"
DASH_EXPRS = {
    "replicas": 'count(up{job="otel-gateway"} == 1)',
    "accepted": 'sum(rate(otelcol_receiver_accepted_spans{job="otel-gateway"}[$__rate_interval]))',
    "sent": 'sum(rate(otelcol_exporter_sent_spans{job="otel-gateway"}[$__rate_interval]))',
    "on_memory": 'sum by (instance) (otelcol_processor_tail_sampling_sampling_traces_on_memory{job="otel-gateway"})',
    "dropped_early": 'sum(rate(otelcol_processor_tail_sampling_sampling_trace_dropped_too_early{job="otel-gateway"}[$__rate_interval]))',
    "decisions": 'sum by (policy) (rate(otelcol_processor_tail_sampling_count_traces_sampled{sampled="true",job="otel-gateway"}[$__rate_interval]))',
    "rss": 'sum by (instance) (otelcol_process_memory_rss{job="otel-gateway"})',
    "queue": 'sum by (exporter) (otelcol_exporter_queue_size{job="otel-gateway"})',
}


def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, lint, prom, stat, text, thresholds, timeseries
    d = Dashboard(DASH_UID, "19 · Gateway del Collector en Kubernetes", tags=["curso", "kubernetes", "helm", "collector"], time_from="now-30m",
                  description="Salud del gateway (Deployment con tail sampling) desplegado con Helm: réplicas, flujo de spans, trazas en memoria, descartes tempranos y memoria. Fuente: el Prometheus del chart prom-lab (job otel-gateway).")
    d.add(text("Cómo leer este dashboard", "Las métricas son la **telemetría interna** de cada réplica del gateway (`:8888`), raspada por DNS del Service headless `otel-gateway-headless`. "
               "Se espera: **réplicas** estables (y que el HPA las cambie despacio), **aceptados ≫ enviados** (el resto es lo muestreado), **trazas en memoria** ≈ tráfico × `decision_wait` y **descartes tempranos = 0**.", h=3))
    d.row("Réplicas y flujo")
    d.add(stat("Réplicas del gateway listas", DASH_EXPRS["replicas"], w=6, h=5, thr=thresholds((None, "red"), (2, "green")), description="Número de réplicas con up=1 (objetivo ≥ 2 para el PDB minAvailable: 1)."),
          timeseries("Spans aceptados vs enviados (por segundo)", [prom(DASH_EXPRS["accepted"], "aceptados"), prom(DASH_EXPRS["sent"], "enviados a Tempo", ref="B")], unit="ops", w=18, h=5,
                     description="La diferencia es lo que el tail sampling descartó (con la política del curso se conserva ≈ 20-25 % de los spans)."))
    d.row("Tail sampling")
    d.add(timeseries("Trazas en memoria por réplica", [prom(DASH_EXPRS["on_memory"], "{{instance}}")], w=8, h=7, description="Debe seguir ≈ tráfico × decision_wait; si se acerca a num_traces habrá descartes tempranos."),
          timeseries("Descartadas antes de decidir", [prom(DASH_EXPRS["dropped_early"], "dropped_too_early")], unit="ops", w=8, h=7, description="Debe ser 0 (num_traces insuficiente si crece)."),
          timeseries("Decisiones por política (conservar)", [prom(DASH_EXPRS["decisions"], "{{policy}}")], unit="ops", w=8, h=7, description="Trazas/s que cada política votó conservar."))
    d.row("Recursos")
    d.add(timeseries("Memoria RSS por réplica", [prom(DASH_EXPRS["rss"], "{{instance}}")], unit="bytes", w=12, h=7, description="Debe quedar por debajo del límite del pod (512 Mi en los values); el memory_limiter rechaza antes de que el kernel mate el pod."),
          timeseries("Cola de exportación", [prom(DASH_EXPRS["queue"], "{{exporter}}")], w=12, h=7, description="Una cola que crece indica un backend lento o con límites (ver módulo 18)."))
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "19-kubernetes.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
# 6. Datos pregrabados (modo sin helm/Docker): medidos con helm 4.3.1, k3s 1.31.5 y los binarios oficiales
# =====================================================================================================================
RELEASES = [("otel-gateway", "otel-collector", ["otel-gateway.yaml"], NS), ("otel-agent", "otel-collector", ["otel-agent.yaml"], NS), ("tempo", "tempo", ["tempo.yaml"], NS),
            ("loki", "loki", ["loki.yaml"], NS), ("grafana", "grafana", ["grafana.yaml"], NS), ("prometheus", "prom-lab", [], NS), ("supportops", "supportops", ["supportops-lab.yaml"], "supportops")]


def record() -> None:
    import os
    import time
    sys.path.insert(0, str(COURSE))
    from supportops import k8s as Kk
    from supportops import sampling as S
    if not os.environ.get("COURSE_CHARTS_DIR"):
        print("aviso: COURSE_CHARTS_DIR no definido; se usarán los repositorios de Helm (necesitan acceso a github.io)")
    V = Kk.K8S_DIR / "values"
    out: dict = {"meta": {"tools": Kk.tool_versions(), "charts": Kk.chart_versions(), "seed": 42}}
    rel_rows, rendered = [], {}
    for rel, ch, vals, ns in RELEASES:
        files = [V / v for v in vals]
        ms = Kk.render(rel, ch, files, namespace=ns)
        rendered[rel] = ms
        ok, _ = Kk.lint(ch, files)
        kc = Kk.kubeconform(ms)
        req = Kk.resource_requests(ms)
        rel_rows.append({"release": rel, "chart": ch, "manifests": len(ms), "kinds": dict(Kk.kinds_count(ms)), "lint": ok, "kubeconform_valid": kc["valid"], "kubeconform_invalid": kc["invalid"],
                         "cpu_m": req["cpu_m"], "memory_mib": req["memory_mib"]})
    out["render"] = rel_rows
    import math
    ns_: dict = {"K": Kk, "math": math}
    exec(SOLUTION_19, ns_)                                   # la referencia calcula los hallazgos de seguridad esperados (R3)
    out["expected_findings"] = {k: len(ns_["security_findings"](v)) for k, v in rendered.items()}
    cfgs = {"otel-gateway": ("collector", Kk.configmap_text(rendered["otel-gateway"], "otel-gateway", "relay")), "otel-agent": ("collector", Kk.configmap_text(rendered["otel-agent"], "otel-agent", "relay")),
            "tempo": ("tempo", Kk.configmap_text(rendered["tempo"], "tempo", "tempo.yaml")), "loki": ("loki", Kk.configmap_text(rendered["loki"], "loki", "config.yaml")),
            "prometheus": ("prometheus", Kk.configmap_text(rendered["prometheus"], "prometheus", "prometheus.yml"))}
    out["binary_validation"] = {k: Kk.validate_with_binary(kind, txt)[0] for k, (kind, txt) in cfgs.items()}
    # el agente con el puerto como entero: el fallo real que encontramos
    bad = Kk.configmap_text(rendered["otel-agent"], "otel-agent", "relay").replace('port: "4317"', "port: 4317")
    out["agent_port_int"] = Kk.validate_with_binary("collector", bad)[1][-300:]
    # API server real
    with Kk.ApiServerLab() as lab:
        for ns in (NS, "supportops"):
            lab.ensure_namespace(ns)
        ops = lab.helm_install("otel-operator", "otel-operator", [K8S / "operator" / "values-operator.yaml"], namespace="opentelemetry-operator-system",
                               set_values={"admissionWebhooks.create": "false"})
        out["api"] = {"operator_install_rc": ops.returncode, "crds": sorted(x.split("/")[-1] for x in lab.kubectl("get", "crd", "-o", "name").stdout.split() if "opentelemetry" in x)}
        installs = {}
        for rel, ch, vals, ns in RELEASES:
            dry = lab.helm_install(rel, ch, [V / v for v in vals], namespace=ns, dry_run_server=True)
            real = lab.helm_install(rel, ch, [V / v for v in vals], namespace=ns)
            installs[rel] = {"dry_run_server_rc": dry.returncode, "install_rc": real.returncode}
        out["api"]["installs"] = installs
        out["api"]["objects"] = dict(lab.objects(NS))
        out["api"]["cr_collector"] = lab.apply((K8S / "operator" / "collector-gateway.yaml").read_text(), dry_run=True).stdout.strip()
        out["api"]["cr_instrumentation"] = lab.apply((K8S / "operator" / "instrumentation.yaml").read_text(), dry_run=True).stdout.strip()
        bad_cr = (K8S / "operator" / "collector-gateway.yaml").read_text().replace("replicas: 2", 'replicas: "dos"')
        out["api"]["cr_invalid"] = lab.apply(bad_cr, dry_run=True).stderr.strip()[:300]
        out["api"]["hpa"] = lab.kubectl("get", "hpa", "-n", NS, "-o", "wide").stdout
        ok, why = lab.can_run_pods(timeout_s=45)
        out["api"]["can_run_pods"] = {"ok": ok, "reason": why}
        out["api"]["server_version"] = lab.kubectl("version", "-o", "json").stdout and json.loads(lab.kubectl("version", "-o", "json").stdout).get("serverVersion", {}).get("gitVersion")
    # Flujo de telemetría con las configuraciones renderizadas
    from supportops import DEFAULT_FAULT_RATES, SupportAgent, generate_tickets, run_tickets
    from supportops.telemetry import OTelInstrumentor, setup_telemetry
    with Kk.FlowLab(Kk.configmap_files(rendered["tempo"], "tempo"), Kk.configmap_files(rendered["loki"], "loki"), Kk.configmap_files(rendered["loki"], "loki-runtime"),
                    Kk.configmap_files(rendered["prometheus"], "prometheus"), Kk.configmap_files(rendered["otel-gateway"], "otel-gateway"), gateway_replicas=1) as lab:
        tel = setup_telemetry("supportops-agent", endpoint=lab.gateway_endpoints[0], mode="otlp", resource_attrs={"deployment.environment.name": "lab", "k8s.pod.name": "sim"}, metric_interval_s=3)
        agent = SupportAgent(instrumentor=OTelInstrumentor(tel))
        tk = generate_tickets(300, seed=42, duration_s=60, start_s="live", fault_rates=DEFAULT_FAULT_RATES)
        res = run_tickets(agent, tk)
        tel.force_flush(10)
        time.sleep(4)
        tel.force_flush(10)
        traces = lab.wait_until(lambda: len(lab.tempo_trace_ids()) >= 20 and lab.tempo_trace_ids(), 90) or set()
        time.sleep(5)
        traces = lab.tempo_trace_ids()
        lines = lab.wait_until(lambda: lab.loki_lines() > 100 and lab.loki_lines(), 60) or 0
        gen = lab.wait_until(lambda: lab.prom_query("gen_ai_client_inference_duration_seconds_count"), 60) or []
        sm = lab.wait_until(lambda: [r for r in lab.prom_query("traces_span_metrics_calls_total") if float(r["value"][1]) > 0], 90) or []
        up = lab.wait_until(lambda: lab.prom_query('up{job="otel-gateway"}'), 45) or []
        time.sleep(40)                                       # el Prometheus del lab raspa cada 15 s: hacen falta ≥ 2 muestras para increase()
        dash = {}
        for k, e in DASH_EXPRS.items():
            try:
                dash[k] = len(lab.prom_query(e.replace("rate(", "increase(").replace("$__rate_interval", "10m")))     # increase(): el tráfico ya terminó, rate() daría vacío
            except Exception as ex:  # noqa: BLE001
                dash[k] = f"ERROR {ex}"
        out["flow"] = {"tickets": len(tk), "traces_in_tempo": len(traces), "loki_lines": lines, "prom_genai_series": len(gen), "span_metrics_series": len(sm),
                       "span_metrics_calls": sum(float(r["value"][1]) for r in sm), "gateway_up": [r["value"][1] for r in up], "dashboard_queries_series": dash}
        tel.shutdown()
    out["affinity"] = Kk.affinity_experiment(S.build_corpus(600).traces)
    RECORDED.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(RECORDED, "wt", encoding="utf-8") as f:
        json.dump(out, f)
    print("OK", RECORDED, RECORDED.stat().st_size, "bytes")


# =====================================================================================================================
# 7. Celdas comunes y lección
# =====================================================================================================================
IMPORTS_19 = '''
import collections, copy, gzip, json, math, os, pathlib, subprocess, time
import yaml
from IPython.display import Markdown, display
from supportops import k8s as K
from supportops import sampling as S
K8S = ROOT / "19_kubernetes_helm" / "k8s"
VALUES = K8S / "values"
REC = json.load(gzip.open(ROOT / "19_kubernetes_helm" / "recorded" / "capture_seed42.json.gz", "rt", encoding="utf-8"))   # medido con helm, k3s y los binarios reales (modo degradado)
TOOLS = K.tool_versions()
HELM = TOOLS["helm"] != "—"
DOCKER = S.docker_ok()
CHARTS_OK = HELM and all(K.chart_path(k, pull=True) for k in K.CHARTS)       # los 5 charts oficiales + los 2 propios, en local
LIVE_RENDER = HELM and CHARTS_OK
print(f"helm: {TOOLS['helm']} · docker: {DOCKER} · charts disponibles en local: {CHARTS_OK}")
if not LIVE_RENDER:
    print("→ modo degradado: lo que necesita helm o los charts usa los resultados pregrabados (mismo código, medido al construir el módulo).")
'''

PLAN_CELL = '''
PLAN = [("otel-gateway", "otel-collector", ["otel-gateway.yaml"], "observability"), ("otel-agent", "otel-collector", ["otel-agent.yaml"], "observability"),
        ("tempo", "tempo", ["tempo.yaml"], "observability"), ("loki", "loki", ["loki.yaml"], "observability"), ("grafana", "grafana", ["grafana.yaml"], "observability"),
        ("prometheus", "prom-lab", [], "observability"), ("supportops", "supportops", ["supportops-lab.yaml"], "supportops")]
'''


def build_lesson() -> None:
    nb, out = nb_for(MOD, "19_kubernetes_helm.ipynb", "Módulo 19 · Kubernetes y Helm para la plataforma de observabilidad")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 19 · Kubernetes + Helm: la plataforma de observabilidad como código

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 5 h (ruta núcleo ≈ 3 h 30: §1-4, §6, §8-9 y §12) |
    | **Servicios de Compose** | Ninguno del stack. Necesita `helm` (4.x) y, para los experimentos con contenedores, **Docker**. Un clúster con kind/k3d es lo ideal en TU máquina (ver «Honestidad» en §3) |
    | **RAM aproximada** | ≈ 1-2 GB mientras corre un experimento (API server de k3s + Tempo/Loki/Prometheus/Collector en contenedores efímeros) |
    | **Modo sin helm/Docker** | Se ejecuta con los resultados pregrabados (medidos al construir el módulo); la parte conceptual, `deep_merge` y el HPA corren en cualquier sitio |
    | **Prerrequisitos** | Módulos 05 (Collector), 17-18 (profiling, muestreo: aquí se despliega el Collector de dos capas del 18) y 16 (SLOs) |

    > 🧭 **Ruta núcleo vs ampliación.** Núcleo: topología y Helm (§1-2), render y validación (§4-6), flujo real de telemetría (§8) y afinidad (§9). Ampliación: API server real (§7), autoscaling (§10), Operator (§11), GitOps (§12).
    """)

    md("""
    ## Objetivos de aprendizaje

    1. **Diseñar** la topología de observabilidad en Kubernetes (agente DaemonSet → gateway Deployment con tail sampling → Tempo/Loki/Prometheus → Grafana) y **justificar** cada capa.
    2. **Explicar y reproducir** la semántica de *values* de Helm (mapas se fusionan, listas se reemplazan, `null` borra) y escribir un chart propio con esquema, sondas, seguridad y HPA.
    3. **Renderizar y validar** con `helm lint`, `helm template`, `kubeconform` y los binarios oficiales (otelcol, Tempo, Loki, promtool) las configuraciones que producen los charts.
    4. **Verificar** con un API server real de Kubernetes que los manifiestos y los CRs del OpenTelemetry Operator son válidos, y **distinguir** lo que se probó de lo que no.
    5. **Comprobar** de extremo a extremo que la telemetría fluye con las configuraciones renderizadas y **medir** por qué el tail sampling exige afinidad por `traceID` al escalar.
    6. **Dimensionar** el autoscaling (HPA) de un componente con estado y **elegir** entre Helm y Operator con criterio.
    7. **Aplicar** configuración como código (capas de values, versiones fijadas, CI de validación, despliegues reproducibles).
    """)

    md(mdj("""
    ## 🔁 Conexión con módulos anteriores
    """,
           details("1. (Módulo 05/18) ¿Por qué el `tail_sampling` obliga a que todos los spans de una traza lleguen a la misma réplica?",
                   "Porque decide sobre la traza **completa** que guarda en memoria; si una réplica solo ve trozos decide con información parcial (p. ej. no ve el span en error o la duración total). En el módulo 18 lo vimos en el simulador; aquí lo **medimos** con dos réplicas reales."),
           details("2. (Módulo 00/10) ¿Qué ventaja tiene que los dashboards y datasources sean archivos en el repositorio?",
                   "Son reproducibles, revisables y versionados (diff en un PR). Helm lleva la misma idea al despliegue: `values.yaml` es la fuente de verdad y `helm template` es determinista."),
           details("3. (Módulo 16) ¿Qué es el presupuesto de error y por qué importa al actualizar un Collector?",
                   "Cada actualización puede perder telemetría o romper trazas; el despliegue gradual (PDB, `maxUnavailable`, ventana de estabilización del HPA) es cómo se protege el SLO de la propia plataforma.")))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_19 + PLAN_CELL)

    # ------------------------------------------------------------------------------------------------ 1
    md("""
    ## 1 · Intuición: dónde vive cada pieza

    En `docker compose` todo corre en una máquina. En producción, la plataforma de observabilidad es **un conjunto de cargas de trabajo** con necesidades distintas:

    | Pieza | Forma en K8s | Por qué |
    |---|---|---|
    | **Agente** del Collector | **DaemonSet** (un pod por nodo) | recibe OTLP de los pods del nodo, añade metadatos de K8s (`k8s_attributes`) y reenvía; barato y sin estado |
    | **Gateway** del Collector | **Deployment** + HPA + PDB | aquí vive el `tail_sampling` (estado en memoria) y las métricas RED (`span_metrics`); se escala con cuidado |
    | **Tempo / Loki** | **StatefulSet** | estado en disco (o almacenamiento de objetos) |
    | **Prometheus** | Deployment/StatefulSet | TSDB local; raspa por DNS/descubrimiento |
    | **Grafana** | Deployment | sin estado (datasources y dashboards como código) |
    | **SupportOps** | Deployment + HPA | la carga que se observa |

    > 💡 **Intuición (SRE).** Es el patrón «agente + gateway» de cualquier pipeline de telemetría: el borde es tonto y cercano a la aplicación; el centro es inteligente, centralizado y pequeño. Y como Helm describe todo **declarativamente**, el despliegue de la plataforma es reproducible y revisable igual que el código del agente.
    """)

    code('''
fig, ax = viz.canvas(12.5, 5.6, xlim=(0, 125), ylim=(0, 56))
ax.text(62, 53, "Topología de observabilidad en Kubernetes (namespaces observability y supportops)", ha="center", fontsize=12, fontweight="bold")
pods = [viz.box(ax, 3, 30 + 7 * i, 17, 5.5, f"SupportOps pod {i+1}", viz.PALETTE["traces"], fontsize=8) for i in range(3)]
agent = viz.box(ax, 28, 31, 19, 14, "otel-agent\\nDaemonSet\\nk8s_attributes\\nload_balancing(traceID)", viz.PALETTE["profiles"], fontsize=8)
gw = viz.box(ax, 56, 31, 21, 14, "otel-gateway ×N\\nDeployment+HPA+PDB\\nspan_metrics → tail_sampling", viz.PALETTE["metrics"], fontsize=8)
tempo = viz.box(ax, 90, 42, 16, 6, "Tempo (StatefulSet)", viz.PALETTE["traces"], fontsize=8)
loki = viz.box(ax, 90, 33, 16, 6, "Loki (StatefulSet)", viz.PALETTE["logs"], fontsize=8)
prom = viz.box(ax, 90, 24, 16, 6, "Prometheus", viz.PALETTE["metrics"], fontsize=8)
graf = viz.box(ax, 110, 33, 13, 6, "Grafana", viz.PALETTE["neutral"], fontsize=8)
for p in pods: viz.arrow(ax, viz.right(p), (27.5, 38), "", viz.PALETTE["traces"], rad=0.05)
viz.arrow(ax, viz.right(agent), viz.left(gw), "OTLP + hash(traceID)", viz.PALETTE["profiles"])
viz.arrow(ax, viz.right(gw), viz.left(tempo), "trazas muestreadas", viz.PALETTE["traces"], rad=-0.2)
viz.arrow(ax, viz.right(gw), viz.left(loki), "logs", viz.PALETTE["logs"])
viz.arrow(ax, viz.right(gw), viz.left(prom), "métricas RED", viz.PALETTE["metrics"], rad=0.2)
for b in (tempo, loki, prom): viz.arrow(ax, viz.right(b), viz.left(graf), "", viz.PALETTE["neutral"], rad=0.0)
op = viz.box(ax, 28, 8, 49, 9, "OpenTelemetry Operator (opcional): CRDs OpenTelemetryCollector / Instrumentation", viz.PALETTE["neutral"], fontsize=8)
viz.arrow(ax, viz.top(op), (66, 30.5), "gestiona", viz.PALETTE["neutral"], dashed=True)
hpa = viz.box(ax, 90, 8, 33, 9, "Helm: values.yaml por componente\\n(configuración como código, versionada)", viz.PALETTE["ok"], fontsize=8)
plt.show()
''')
    md(observe("""
    - Dos capas con **responsabilidades distintas**: el agente es local y sin estado; el gateway concentra el estado (tail sampling) y por eso el agente reparte **por `traceID`** hacia sus réplicas (§9).
    - Las métricas RED se calculan en el gateway **antes** del muestreo (módulo 18); lo que llega a Tempo es solo lo conservado.
    - El Operator es una alternativa a Helm para gestionar el Collector (§11); no sustituye a Tempo/Loki/Grafana.
    """))

    # ------------------------------------------------------------------------------------------------ 2
    md("""
    ## 2 · Helm por dentro: chart, values y la regla de fusión

    Un **chart** es una carpeta: `Chart.yaml` (metadatos), `values.yaml` (parámetros por defecto), `values.schema.json` (validación, opcional) y `templates/` (YAML con plantillas Go). `helm template <release> <chart> -f values.yaml` produce los manifiestos;
    `helm install` los envía al API server y guarda la **release** (revisión, valores usados) en un Secret del clúster. Veamos el chart propio del curso:
    """)
    code('''
chart = K8S / "charts" / "supportops"
for p in sorted(chart.rglob("*")):
    if p.is_file():
        print(f"{str(p.relative_to(chart)):38} {len(p.read_text().splitlines()):3} líneas")
print()
print((chart / "values.yaml").read_text()[:900])
''')
    md("""
    ### 2.1 · La regla de fusión de *values*, a mano

    Cuando pasas `-f base.yaml -f prod.yaml --set x=y`, Helm **fusiona** las capas: los **mapas** se combinan recursivamente, las **listas se reemplazan enteras** y `null` **borra** la clave heredada. Es la fuente de errores nº 1 al personalizar `config.service.pipelines`
    o `policies`. La implementamos en 12 líneas (`K.deep_merge`) y comprobamos contra `helm template` real.
    """)
    code('''
import inspect
print(inspect.getsource(K.deep_merge))
base = {"config": {"processors": {"batch": {}, "memory_limiter": {"check_interval": "5s"}}, "service": {"pipelines": {"logs": {"receivers": ["otlp"], "exporters": ["debug"]}}}}}
over = {"config": {"processors": {"memory_limiter": {"check_interval": "1s"}, "tail_sampling": {"decision_wait": "10s"}}, "service": {"pipelines": {"logs": {"exporters": ["otlp_http/loki"]}, "traces": None}}}}
merged = K.deep_merge(base, over)
print(json.dumps(merged, indent=1))
''')
    code('''
if LIVE_RENDER:
    over = {"config": {"service": {"pipelines": {"logs": {"exporters": ["debug", "otlp_http/loki"]}}}}}
    ms = K.render("demo", "otel-collector", [over, {"mode": "deployment", "image": {"repository": "otel/opentelemetry-collector-contrib"}}])
    helm_cfg = yaml.safe_load(K.configmap_text(ms, "demo", "relay"))
    defaults = yaml.safe_load(open(K.chart_path("otel-collector") + "/values.yaml"))
    mine = K.deep_merge(defaults, over)
    print("Chart: pipeline de logs según helm →", helm_cfg["service"]["pipelines"]["logs"])
    print("Mi deep_merge                      →", mine["config"]["service"]["pipelines"]["logs"])
    print("¿Iguales?", helm_cfg["service"]["pipelines"]["logs"] == mine["config"]["service"]["pipelines"]["logs"],
          "· la lista exporters NO se concatenó con [debug] por defecto: se reemplazó")
else:
    print("(sin helm/charts) pregrabado: helm y deep_merge coinciden; las listas se reemplazan")
''')
    md(observe("""
    - `memory_limiter` se **fusionó** (conserva `check_interval` nuevo y los demás campos del chart), `traces: null` **borró** el pipeline de trazas heredado y la lista `exporters` de `logs` fue **reemplazada** (no `["debug", "otlp_http/loki"]` concatenada con la anterior).
    - `helm template` real da exactamente el mismo resultado que nuestra función: ahora sabes qué hace Helm con tus capas de values. Consecuencia práctica: al sobrescribir una lista, **repite todos sus elementos**; al quitar un componente por defecto del chart usa `null`.
    """))

    # ------------------------------------------------------------------------------------------------ 3
    md("""
    ## 3 · El entorno, con honestidad

    Qué hay en esta máquina y qué se verificó al construir el módulo. Los charts oficiales **no se copian** al curso: se fijan por versión y se descargan de su repositorio (o de un clon de GitHub, como aquí).
    """)
    code('''
display(pd.Series(TOOLS, name="versión").to_frame())
rows = K.chart_versions() if CHARTS_OK else REC["meta"]["charts"]
display(pd.DataFrame(rows))
''')
    md("""
    > ⚠️ **Qué corrió en un clúster real y qué NO.** En el sandbox donde se construyó el módulo `docker` ejecuta contenedores, pero **ni `kind` (v1.31 y v1.34) ni `k3s` pudieron arrancar pods**: `runc` anidado falla con
    > `can't get final child's PID from pipe: EOF`. Por tanto **ningún pod llegó a ejecutarse en un clúster**. Lo que SÍ se verificó con binarios reales:
    >
    > | Verificado | Cómo |
    > |---|---|
    > | Manifiestos y values de los 7 *releases* | `helm lint`, `helm template`, `kubeconform` (esquemas de K8s 1.31) |
    > | Las **configuraciones que renderizan los charts** | `otelcol-contrib validate`, `tempo -config.verify`, `loki -verify-config`, `promtool check config` |
    > | Objetos y CRs contra un **API server real** (k3s 1.31) | `helm install`, `kubectl apply --dry-run=server`, rechazo de CRs inválidos por el esquema del CRD |
    > | **Flujo de telemetría de extremo a extremo** | Tempo, Loki, Prometheus y el gateway en contenedores con **esas mismas configuraciones** y los DNS de los Services como alias de red |
    > | **Afinidad por `traceID`** con 2 réplicas del gateway | Collectors reales (`load_balancing`) y comparación de trazas completas |
    >
    > **No** verificado: planificación y ciclo de vida de pods, sondas (también la `livenessProbe` por latido del chart `supportops`), el Service `otel-agent` con `internalTrafficPolicy: Local`, `hostPort`, HPA con métricas reales (no hay metrics-server), el Operator en ejecución (sus imágenes están en `ghcr.io`/`quay.io`, inaccesibles aquí), el webhook de admisión y la inyección de auto-instrumentación.
    > En tu máquina con kind o k3d todo eso se ejecuta con los mismos archivos (`k8s/kind-config.yaml`, `k8s/values/`).
    """)

    # ------------------------------------------------------------------------------------------------ 4
    md("""
    ## 4 · Renderizar y validar: `helm template` + `helm lint` + `kubeconform`

    Para cada *release* (6 en `observability`, 1 en `supportops`) renderizamos los manifiestos con los values del módulo, pasamos `helm lint` y validamos cada documento contra el esquema OpenAPI de Kubernetes con `kubeconform`.
    """)
    code('''
if LIVE_RENDER:
    REN, rows = {}, []
    for rel, ch, vals, ns in PLAN:
        files = [VALUES / v for v in vals]
        ms = K.render(rel, ch, files, namespace=ns)
        REN[rel] = ms
        ok, _ = K.lint(ch, files)
        kc = K.kubeconform(ms)
        req = K.resource_requests(ms)
        rows.append({"release": rel, "chart": ch, "manifests": len(ms), "kinds": dict(K.kinds_count(ms)), "lint": ok, "kubeconform_valid": kc["valid"], "kubeconform_invalid": kc["invalid"], "cpu_m": req["cpu_m"], "memory_mib": req["memory_mib"]})
else:
    REN, rows = {}, REC["render"]
R = pd.DataFrame(rows)
display(R[["release", "chart", "manifests", "lint", "kubeconform_valid", "kubeconform_invalid", "cpu_m", "memory_mib"]])
print("total de manifiestos:", int(R["manifests"].sum()), "· inválidos para el esquema de K8s:", int(R["kubeconform_invalid"].sum()))
''')
    code('''
kinds = collections.Counter()
per_rel = {r["release"]: r["kinds"] for r in rows}
all_kinds = sorted({k for d in per_rel.values() for k in d}, key=lambda k: -sum(d.get(k, 0) for d in per_rel.values()))
fig, axs = plt.subplots(1, 2, figsize=(13, 4.2))
bottom = np.zeros(len(per_rel))
cmap = plt.cm.tab20(np.linspace(0, 1, len(all_kinds)))
for k, c in zip(all_kinds, cmap):
    vals = np.array([per_rel[r].get(k, 0) for r in per_rel])
    axs[0].bar(list(per_rel), vals, bottom=bottom, color=c, label=k); bottom += vals
axs[0].set_ylim(0, bottom.max() + 4); axs[0].set_title("Objetos de Kubernetes por release"); axs[0].set_ylabel("nº de manifiestos"); axs[0].legend(fontsize=7, ncol=3, loc="upper right"); axs[0].tick_params(axis="x", labelrotation=30, labelsize=8)
NODE_CPU, NODE_MEM = 4000, 8 * 1024
cpu = R["cpu_m"].values; mem = R["memory_mib"].values
xr = np.arange(len(R))
axs[1].bar(xr - 0.2, cpu / NODE_CPU * 100, 0.4, color=viz.PALETTE["metrics"], label="CPU requests (% de 4 vCPU)")
axs[1].bar(xr + 0.2, mem / NODE_MEM * 100, 0.4, color=viz.PALETTE["traces"], label="memoria requests (% de 8 GiB)")
axs[1].set_xticks(xr); axs[1].set_xticklabels(R["release"])
axs[1].set_title(f"Requests por release — total {cpu.sum():.0f} m · {mem.sum():.0f} MiB"); axs[1].set_ylabel("% de un nodo de laboratorio"); axs[1].legend(fontsize=8); axs[1].tick_params(axis="x", labelrotation=30, labelsize=8)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Todos** los manifiestos de los 7 releases pasan `helm lint` y el esquema de Kubernetes (`kubeconform`: 0 inválidos). Loki y el gateway concentran más objetos (cuentas de servicio, RBAC, Services).
    - Las **requests** suman ≈ 0,6 vCPU y ≈ 1,4 GiB: caben holgadas en un nodo kind de laboratorio; en producción se dimensionan con medidas (el módulo 18 te dio el cálculo de memoria del tail sampling).
    - Los **límites** de memoria están fijados y los de CPU **no** (a propósito: un límite de CPU provoca *throttling* en un Collector bajo ráfagas; ver 🧠).
    """))

    # ------------------------------------------------------------------------------------------------ 5
    md("""
    ## 5 · Configuración como código: los values del gateway

    El archivo `k8s/values/otel-gateway.yaml` está **generado desde Python** (el módulo lo construye con `build_19.py`) y es la pieza central: reutiliza la política del módulo 18 (errors, slow, costly, baseline), calcula RED antes del muestreo y exporta a los tres backends por los **nombres DNS de los Services**.
    Se muestra tal cual, con los puntos clave:
    """)
    code('''
txt = (VALUES / "otel-gateway.yaml").read_text()
print(txt[:3400])
''')
    md("""
    Puntos clave del archivo (compáralo con el módulo 18):

    - `config.receivers.jaeger/zipkin/prometheus: null` → **borra** receptores que el chart trae por defecto (regla de fusión de §2).
    - `connectors.span_metrics` + `forward`: las métricas RED salen de `traces/in` **antes** de `tail_sampling` (`traces/sampled`).
    - `extraManifests`: el Service **headless** `otel-gateway-headless` que el agente usa para repartir por `traceID`.
    - `autoscaling.behavior.scaleDown`: ventana de estabilización de 10 min y bajada de 1 pod cada 2 min: escalar **hacia abajo** un componente con estado es lo delicado (§10).
    - `resources.limits`: solo memoria; `podDisruptionBudget.minAvailable: 1`.
    """)

    # ------------------------------------------------------------------------------------------------ 6
    md("""
    ## 6 · Validar lo que renderizan los charts con los binarios oficiales

    Un chart puede ser YAML perfecto y producir una **configuración de aplicación** inválida (el Collector, Tempo, Loki y Prometheus tienen su propio esquema). Extraemos los ConfigMaps renderizados y los validamos con el binario de cada uno (en contenedores efímeros, sin red).
    """)
    code('''
if LIVE_RENDER and DOCKER:
    cfgs = {"otel-gateway": ("collector", K.configmap_text(REN["otel-gateway"], "otel-gateway", "relay")), "otel-agent": ("collector", K.configmap_text(REN["otel-agent"], "otel-agent", "relay")),
            "tempo": ("tempo", K.configmap_text(REN["tempo"], "tempo", "tempo.yaml")), "loki": ("loki", K.configmap_text(REN["loki"], "loki", "config.yaml")),
            "prometheus": ("prometheus", K.configmap_text(REN["prometheus"], "prometheus", "prometheus.yml"))}
    BIN = {k: K.validate_with_binary(kind, txt)[0] for k, (kind, txt) in cfgs.items()}
else:
    BIN = REC["binary_validation"]
display(pd.Series({k: ("✅ válida" if v else "❌") for k, v in BIN.items()}, name="validación con el binario oficial").to_frame())
''')
    md("""
    Dos errores **reales** que aparecieron al construir los values, tal como los reportó el binario:

    1. `load_balancing.resolver.dns.port` debe ser una **cadena** (`"4317"`), no un entero. Con `port: 4317` el Collector 0.162.0 responde: `'port' expected type 'string', got unconvertible type 'int'`.
    2. El preset `kubernetesAttributes` usa `node_from_env_var: K8S_NODE_NAME`: la configuración **depende de variables de entorno que inyecta el pod** (el chart las pone con *downward API*). Validar fuera del pod exige definirlas.
    """)
    code('''
if LIVE_RENDER and DOCKER:
    bad = K.configmap_text(REN["otel-agent"], "otel-agent", "relay").replace('port: "4317"', "port: 4317")
    print(K.validate_with_binary("collector", bad)[1][-330:])
else:
    print(REC["agent_port_int"])
''')
    md(observe("""
    - Las 5 configuraciones renderizadas son válidas **según el binario**, no solo según el esquema de YAML. Es el control que falta en la mayoría de pipelines de CI de Helm: `helm lint` no sabe qué es un `tail_sampling`.
    - Los dos fallos de arriba se detectaron **antes** de desplegar. En un clúster habrían sido un `CrashLoopBackOff` con el error en los logs del pod.
    """))

    # ------------------------------------------------------------------------------------------------ 7
    md("""
    ## 7 · Un API server real: `helm install` y CRs del Operator

    Con `k3s` (Kubernetes real) en un contenedor tenemos API server, controladores, admisión, CRDs y RBAC. Instalamos los 7 releases con `helm upgrade --install` (sin esperar a los pods: no pueden arrancar aquí), verificamos primero con `--dry-run=server`
    (el API server **valida** de verdad) y aplicamos los CRs del Operator contra los CRDs reales instalados por su chart.
    """)
    code('''
if LIVE_RENDER and DOCKER:
    with K.ApiServerLab() as lab:
        for ns in ("observability", "supportops"):
            lab.ensure_namespace(ns)
        ops = lab.helm_install("otel-operator", "otel-operator", [K8S / "operator" / "values-operator.yaml"], namespace="opentelemetry-operator-system", set_values={"admissionWebhooks.create": "false"})
        API = {"operator_install_rc": ops.returncode, "crds": sorted(x.split("/")[-1] for x in lab.kubectl("get", "crd", "-o", "name").stdout.split() if "opentelemetry" in x), "installs": {}}
        for rel, ch, vals, ns in PLAN:
            dry = lab.helm_install(rel, ch, [VALUES / v for v in vals], namespace=ns, dry_run_server=True)
            real = lab.helm_install(rel, ch, [VALUES / v for v in vals], namespace=ns)
            API["installs"][rel] = {"dry_run_server_rc": dry.returncode, "install_rc": real.returncode}
        API["objects"] = dict(lab.objects("observability"))
        API["cr_collector"] = lab.apply((K8S / "operator" / "collector-gateway.yaml").read_text(), dry_run=True).stdout.strip()
        API["cr_instrumentation"] = lab.apply((K8S / "operator" / "instrumentation.yaml").read_text(), dry_run=True).stdout.strip()
        API["cr_invalid"] = lab.apply((K8S / "operator" / "collector-gateway.yaml").read_text().replace("replicas: 2", 'replicas: "dos"'), dry_run=True).stderr.strip()[:300]
        API["hpa"] = lab.kubectl("get", "hpa", "-n", "observability", "-o", "wide").stdout
        ok, why = lab.can_run_pods(timeout_s=45)
        API["can_run_pods"] = {"ok": ok, "reason": why}
else:
    API = REC["api"]
display(pd.DataFrame(API["installs"]).T.rename(columns={"dry_run_server_rc": "dry-run=server (rc)", "install_rc": "install (rc)"}))
print("CRDs del Operator instalados por su chart:", API["crds"])
print("CR OpenTelemetryCollector →", API["cr_collector"]); print("CR Instrumentation        →", API["cr_instrumentation"])
print("CR inválido (replicas: \\"dos\\") →", API["cr_invalid"].splitlines()[0] if API["cr_invalid"] else "")
print("HPA creado (sin metrics-server → TARGETS <unknown>):\\n" + API["hpa"])
print("¿Pueden arrancar pods en este sandbox?", API["can_run_pods"])
''')
    code('''
objs = pd.Series(API["objects"]).sort_values()
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.barh(objs.index, objs.values, color=viz.PALETTE["traces"]); ax.set_title("Objetos creados en el namespace observability (API server real)"); ax.set_xlabel("nº de objetos")
for i, v in enumerate(objs.values): ax.text(v, i, f" {v}", va="center", fontsize=8)
plt.tight_layout(); plt.show()
''')
    code('''
cols = ["helm lint", "kubeconform", "config con\\nsu binario", "dry-run=server", "helm install", "pods\\nRunning"]
rel_names = [r["release"] for r in rows]
M = np.full((len(rel_names), len(cols)), np.nan)
for i, r in enumerate(rows):
    M[i, 0] = float(r["lint"]); M[i, 1] = float(r["kubeconform_invalid"] == 0)
    if r["release"] in BIN: M[i, 2] = float(BIN[r["release"]])
    ins = API["installs"].get(r["release"], {})
    M[i, 3] = float(ins.get("dry_run_server_rc", 1) == 0); M[i, 4] = float(ins.get("install_rc", 1) == 0)
    M[i, 5] = float(API["can_run_pods"]["ok"])
from matplotlib.colors import ListedColormap
fig, ax = plt.subplots(figsize=(9, 3.9))
ax.imshow(np.ma.masked_invalid(M), cmap=ListedColormap([viz.PALETTE["error"], viz.PALETTE["ok"]]), vmin=0, vmax=1, aspect="auto")
ax.set_facecolor("#d9dde3"); ax.grid(False)
ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, fontsize=8); ax.set_yticks(range(len(rel_names))); ax.set_yticklabels(rel_names, fontsize=8)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, "n/a" if np.isnan(M[i, j]) else ("✔" if M[i, j] else "✘"), ha="center", va="center", color=("#1f2937" if np.isnan(M[i, j]) else "white"), fontsize=11, fontweight="bold")
ax.set_title("Matriz de verificación por release (gris = no aplica; rojo = NO se pudo en este sandbox)")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Todo se instala** (`rc = 0`, también con `--dry-run=server`): el API server aceptó los 7 releases y los 2 CRs del Operator, e instaló los CRDs que su chart trae **plantillados** (`crds.create`).
    - Un CR con `replicas: "dos"` es **rechazado por el esquema del CRD** con un mensaje claro: validación gratuita antes del despliegue.
    - El HPA se crea pero marca `<unknown>/70%`: sin `metrics-server` y sin pods ejecutándose no hay métrica. Y la última línea es la verdad incómoda del sandbox: **los pods no arrancan** (runc anidado), por eso §8-9 usan contenedores directos.
    """))

    # ------------------------------------------------------------------------------------------------ 8
    md("""
    ## 8 · El flujo de telemetría de extremo a extremo con las configuraciones renderizadas

    Como no hay pods, levantamos Tempo, Loki, Prometheus y el gateway en **contenedores con las configuraciones que acaban de renderizar los charts** (`configmap_files`) y con los DNS de los Services de Kubernetes como alias de red
    (`tempo.observability.svc.cluster.local`…): lo que el chart pone en `endpoint:` resuelve igual que en el clúster. Enviamos tráfico real de SupportOps (trazas, logs y métricas por OTLP) y consultamos cada backend.
    """)
    code('''
if LIVE_RENDER and DOCKER:
    from supportops import DEFAULT_FAULT_RATES, SupportAgent, generate_tickets, run_tickets
    from supportops.telemetry import OTelInstrumentor, setup_telemetry
    lab_cm = dict(tempo=K.configmap_files(REN["tempo"], "tempo"), loki=K.configmap_files(REN["loki"], "loki"), loki_runtime=K.configmap_files(REN["loki"], "loki-runtime"),
                  prometheus=K.configmap_files(REN["prometheus"], "prometheus"), gateway=K.configmap_files(REN["otel-gateway"], "otel-gateway"))
    with K.FlowLab(lab_cm["tempo"], lab_cm["loki"], lab_cm["loki_runtime"], lab_cm["prometheus"], lab_cm["gateway"], gateway_replicas=1) as lab:
        tel = setup_telemetry("supportops-agent", endpoint=lab.gateway_endpoints[0], mode="otlp", resource_attrs={"deployment.environment.name": "lab", "k8s.pod.name": "sim"}, metric_interval_s=3)
        agent = SupportAgent(instrumentor=OTelInstrumentor(tel))
        tk = generate_tickets(300, seed=SEED, duration_s=60, start_s="live", fault_rates=DEFAULT_FAULT_RATES)
        res = run_tickets(agent, tk); tel.force_flush(10); time.sleep(4); tel.force_flush(10)
        lab.wait_until(lambda: len(lab.tempo_trace_ids()) >= 20, 90); time.sleep(5)
        FLOW = {"tickets": len(tk), "traces_in_tempo": len(lab.tempo_trace_ids()), "loki_lines": lab.wait_until(lambda: lab.loki_lines() > 100 and lab.loki_lines(), 60) or 0,
                "prom_genai_series": len(lab.wait_until(lambda: lab.prom_query("gen_ai_client_inference_duration_seconds_count"), 60) or []),
                "span_metrics_series": 0, "span_metrics_calls": 0.0, "gateway_up": [r["value"][1] for r in (lab.wait_until(lambda: lab.prom_query('up{job="otel-gateway"}'), 45) or [])]}
        sm = lab.wait_until(lambda: [r for r in lab.prom_query("traces_span_metrics_calls_total") if float(r["value"][1]) > 0], 90) or []
        FLOW["span_metrics_series"], FLOW["span_metrics_calls"] = len(sm), sum(float(r["value"][1]) for r in sm)
        FLOW["dashboard_queries_series"] = {}
        for k, e in {"replicas": 'count(up{job="otel-gateway"} == 1)', "accepted": 'sum(increase(otelcol_receiver_accepted_spans{job="otel-gateway"}[10m]))',
                     "on_memory": 'sum by (instance) (otelcol_processor_tail_sampling_sampling_traces_on_memory{job="otel-gateway"})'}.items():
            FLOW["dashboard_queries_series"][k] = len(lab.prom_query(e))
        tel.shutdown()
else:
    FLOW = REC["flow"]
display(pd.Series({k: v for k, v in FLOW.items() if k != "dashboard_queries_series"}, name="resultado").to_frame())
print("consultas del dashboard 19 contra el Prometheus del lab (nº de series):", FLOW["dashboard_queries_series"])
''')
    code('''
fig, axs = plt.subplots(1, 2, figsize=(12.5, 3.8))
funnel = {"tickets atendidos": FLOW["tickets"], "trazas en Tempo\\n(tail sampling)": FLOW["traces_in_tempo"], "líneas de log en Loki": FLOW["loki_lines"]}
axs[0].bar(list(funnel), list(funnel.values()), color=[viz.PALETTE["neutral"], viz.PALETTE["traces"], viz.PALETTE["logs"]])
for i, v in enumerate(funnel.values()): axs[0].text(i, v, f"{v}", ha="center", va="bottom")
axs[0].set_title("Lo que sale de SupportOps y lo que llega a cada backend"); axs[0].set_ylabel("nº")
sm = {"series gen_ai.* (Prometheus)": FLOW["prom_genai_series"], "series span_metrics": FLOW["span_metrics_series"], "réplicas del gateway con up=1": len(FLOW["gateway_up"])}
axs[1].barh(list(sm), list(sm.values()), color=viz.PALETTE["metrics"]); axs[1].set_title("Métricas: del SDK y generadas por el gateway")
plt.tight_layout(); plt.show()
print(f"Fracción de trazas conservadas: {FLOW['traces_in_tempo'] / FLOW['tickets']:.0%} (la política del módulo 18 conserva lo interesante + un 10 % base)")
''')
    md(observe("""
    - Con la configuración **tal como la renderizan los charts**, la telemetría fluye de extremo a extremo: ≈ 1/5 de las trazas llega a Tempo (tail sampling), los **logs** completos a Loki (con `trace_id` como structured metadata) y las **métricas** del SDK y las RED del gateway a Prometheus.
    - `up{job="otel-gateway"} = 1`: el Prometheus de `prom-lab` descubre las réplicas **por DNS** del Service headless, igual que lo haría en el clúster.
    - Las consultas del dashboard `19-kubernetes.json` devuelven series con datos reales (se validan en esta misma celda).
    """))

    # ------------------------------------------------------------------------------------------------ 9
    md("""
    ## 9 · Afinidad por `traceID`: por qué el gateway no se puede escalar «a ciegas»

    Con **2 réplicas** del gateway detrás de un Service normal (reparto por turnos), cada réplica recibe *trozos* de cada traza (los spans de servicios distintos llegan en lotes distintos) y decide con información parcial. La solución (§1): el agente usa el exportador **`load_balancing`** con `routing_key: traceID`
    y un resolvedor DNS sobre el Service **headless**. Lo medimos con dos Collectors reales (`tail_sampling` → archivo) y las mismas 600 trazas en ambos modos.
    """)
    code('''
if DOCKER:
    corpus = S.build_corpus(600)
    AFF = K.affinity_experiment(corpus.traces, replicas=2)
else:
    AFF = REC["affinity"]
df = pd.DataFrame(AFF).T[["traces_kept", "complete_pct", "interesting_recall_pct", "interesting_complete_pct", "spans_kept"]].round(1)
display(df)
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = np.arange(2); w = 0.35
ax.bar(x - w / 2, df["complete_pct"], w, color=viz.PALETTE["warn"], label="% de trazas conservadas COMPLETAS")
ax.bar(x + w / 2, df["interesting_complete_pct"], w, color=viz.PALETTE["error"], label="% de las trazas interesantes conservadas COMPLETAS")
ax.set_xticks(x); ax.set_xticklabels(df.index, fontsize=9); ax.set_ylim(0, 110); ax.set_ylabel("%"); ax.set_title("Sin afinidad, el tail sampling guarda trazas rotas"); ax.legend(fontsize=8)
for i, (a, b) in enumerate(zip(df["complete_pct"], df["interesting_complete_pct"])): ax.text(i - w / 2, a + 1, f"{a:.0f}", ha="center"); ax.text(i + w / 2, b + 1, f"{b:.0f}", ha="center")
plt.show()
''')
    md(observe("""
    - **Sin afinidad**, solo ≈ 2/3 de las trazas conservadas están completas y, lo peor, **solo ≈ 42 % de las interesantes** (errores, lentas): una réplica guarda el span en error y la otra no, o decide «no lenta» al ver media traza. **Con `load_balancing` por `traceID`**: el **100 %**.
    - El número de trazas conservadas es el mismo (127): lo que cambia es su **calidad**. Un panel de «trazas con error» cuenta bien, pero al abrir la traza faltan spans: el síntoma más desconcertante del tail sampling mal desplegado.
    - En el clúster el resolvedor `dns` sobre `otel-gateway-headless` (una A por pod) mantiene el anillo al día cada `interval`; el chart del agente lo configura así (`k8s/values/otel-agent.yaml`). El resolvedor `k8s` (endpoints) requiere RBAC adicional.
    """))

    # ------------------------------------------------------------------------------------------------ 10
    md("""
    ## 10 · Autoscaling del gateway

    El HPA calcula $\\text{réplicas}_{\\text{deseadas}}=\\left\\lceil \\text{réplicas}_{\\text{actuales}}\\cdot\\dfrac{\\text{métrica actual}}{\\text{objetivo}}\\right\\rceil$ (con una tolerancia del 10 %: si la razón está entre 0,9 y 1,1 no hace nada), acotado a `[min, max]`.
    Subir réplicas es sencillo; **bajarlas** en un componente con estado es delicado: cada cambio de réplicas **reasigna** parte de las trazas en curso (el anillo del `load_balancing` cambia) y las trazas partidas se rompen. De ahí `behavior.scaleDown` con una ventana de estabilización larga.
    """)
    code('''
rng = np.random.default_rng(SEED)
t = np.arange(0, 120)                      # 120 pasos de 15 s = 30 min
load = 150 + 30 * np.sin(t / 10) + rng.normal(0, 8, t.size)
load[40:70] += 420                          # un incidente: tráfico ×4 durante 7,5 min
CAP = 100                                   # unidades de trabajo por réplica a 100 % de CPU
fast = K.hpa_simulate(load, CAP, 0.7, min_replicas=2, max_replicas=10, step_s=15, scale_down_window_s=15)
slow = K.hpa_simulate(load, CAP, 0.7, min_replicas=2, max_replicas=10, step_s=15, scale_down_window_s=600)
fig, axs = plt.subplots(2, 1, figsize=(10, 5.4), sharex=True)
axs[0].plot(t * 15 / 60, load, color=viz.PALETTE["neutral"], lw=1.5); axs[0].set_ylabel("carga (trabajo/s)"); axs[0].set_title("Un pico de tráfico y la respuesta del HPA")
axs[1].step(t * 15 / 60, fast["replicas"], where="post", color=viz.PALETTE["error"], lw=2, label="ventana de bajada 15 s (sin estabilización)")
axs[1].step(t * 15 / 60, slow["replicas"], where="post", color=viz.PALETTE["ok"], lw=2, label="ventana de bajada 10 min (como los values)")
axs[1].set_xlabel("minutos"); axs[1].set_ylabel("réplicas"); axs[1].legend(fontsize=8)
plt.tight_layout(); plt.show()
changes = lambda r: int(np.sum(np.diff(r["replicas"]) != 0))
print(f"cambios de réplicas: sin estabilización {changes(fast)} · con ventana de 10 min {changes(slow)} · pico {max(slow['replicas'])} réplicas · réplica-minutos {sum(slow['replicas']) * 15 / 60:.0f} vs {sum(fast['replicas']) * 15 / 60:.0f}")
''')
    md(observe("""
    - Ambas curvas **suben igual de rápido** al llegar el pico (el HPA reacciona en un paso); la diferencia está en la **bajada**: sin estabilización oscila siguiendo el ruido de la carga (cada cambio = trazas reasignadas); con la ventana de 10 min mantiene las réplicas y baja de forma ordenada. Cuesta algunas réplica-minutos extra, y las paga el **recall** de trazas íntegras.
    - La métrica de CPU es una aproximación: la presión real del gateway es **memoria** (`sampling_traces_on_memory`). En producción se escala por métricas personalizadas (KEDA / Prometheus Adapter) sobre esa serie; es un reto del proyecto.
    - En este sandbox el HPA **no se ejecutó** (sin metrics-server ni pods): la simulación es el algoritmo documentado, no una medida del clúster.
    """))

    # ------------------------------------------------------------------------------------------------ 11
    md("""
    ## 11 · OpenTelemetry Operator: CRDs en lugar de values

    El **Operator** (chart 0.126.0, operador 0.161.0) añade CRDs y un controlador: `OpenTelemetryCollector` (v1beta1) crea el Deployment/DaemonSet/StatefulSet, Service, ConfigMap, **HPA y PDB** a partir de un solo CR; `Instrumentation` (v1alpha1) permite
    **auto-instrumentar** pods con una anotación (`instrumentation.opentelemetry.io/inject-python: "true"`: un webhook inyecta un *init container* con el SDK). Requiere un certificado para su webhook: cert-manager o, como aquí, `autoGenerateCert`.
    """)
    code('''
print((K8S / "operator" / "collector-gateway.yaml").read_text()[:1600])
print("...")
print((K8S / "operator" / "values-operator.yaml").read_text())
''')
    md("""
    | | **Helm** (chart del Collector) | **Operator** (CRs) |
    |---|---|---|
    | Qué gestionas | values → manifiestos (tú ves y versionas el YAML resultante) | un CR → el controlador crea y **reconcilia** los recursos |
    | Auto-instrumentación | no | **sí** (`Instrumentation` + anotación) |
    | Reconciliación continua | no (Helm aplica y se va) | sí (corrige derivas) |
    | Dependencias | ninguna | webhook + certificado (cert-manager) |
    | Operar/depurar | `helm template` explica todo | un nivel más de indirección |
    | Cuándo | plataformas con GitOps y equipos que quieren ver el YAML | muchos Collectors, TargetAllocator para Prometheus, inyección masiva |

    Existe además el chart **`opentelemetry-kube-stack`** (0.24.6, app 0.159.0 en el repositorio verificado), que instala el Operator y colectores preconfigurados «de una tacada». El CR de este módulo **se validó contra el API server real** (§7); su ejecución (imágenes en `ghcr.io`) **no** se pudo probar aquí.
    """)

    # ------------------------------------------------------------------------------------------------ 12
    md("""
    ## 12 · Configuración como código y GitOps

    1. **Capas de values**: `-f base.yaml -f env/prod.yaml`: la última gana (regla de §2). Mantén `base` mínimo y diferencias por entorno pequeñas.
    2. **Versiones fijadas**: chart (`--version`), imagen (`tag` y, mejor, `digest`) y apps. Aquí todas las versiones coinciden con el stack de Compose (Collector 0.162.0, Tempo 3.1.0, Loki 3.7.8, Grafana 13.2.4, Prometheus v3.15.0).
    3. **Reinicios por cambio de configuración**: el chart del Collector pone un *checksum* de la ConfigMap en las anotaciones del pod (`enableConfigChecksumAnnotation`): cambiar la configuración cambia el hash y fuerza el *rollout*. Lo comprobamos:
    """)
    code('''
if LIVE_RENDER:
    def ck(over):
        ms = K.render("otel-gateway", "otel-collector", [VALUES / "otel-gateway.yaml", over])
        dep = next(m for m in ms if m["kind"] == "Deployment")
        return dep["spec"]["template"]["metadata"]["annotations"]
    a0 = ck({})
    a1 = ck({"config": {"processors": {"tail_sampling": {"decision_wait": "20s"}}}})
    a2 = ck({"replicaCount": 3})
    print("checksum base      :", a0)
    print("decision_wait 20 s :", a1, "→ cambia:", a0 != a1)
    print("replicaCount 3     :", a2, "→ no cambia:", a0 == a2)
else:
    print("(sin helm) pregrabado: cambiar la configuración cambia el checksum del pod; cambiar solo las réplicas no")
''')
    md("""
    4. **Pipeline de CI** (cada PR): `helm lint` → `helm template | kubeconform` → validación de las configuraciones renderizadas con los binarios (§6) → `helm install --dry-run=server` contra un clúster efímero (§7) → pruebas de flujo. Todo está en este módulo salvo el último paso en un clúster con pods.
    5. **Secretos**: nada de contraseñas en values (aquí `adminPassword: admin` es **solo laboratorio**): `existingSecret`, External Secrets o Sealed Secrets.
    6. **GitOps** (Argo CD/Flux): el repositorio es el estado deseado; el controlador aplica y corrige derivas. Los charts de este módulo son compatibles tal cual (`helm template` determinista).
    """)

    md("""
    ## 13 · 🏭 En producción

    - **Grafana Labs** publica charts para Tempo (`tempo-distributed` 3.13.0 verificado) y Loki; en 2026 los charts de la comunidad (Tempo monolítico, Loki, Grafana) se mantienen en `grafana-community/helm-charts` y el repositorio `grafana/helm-charts` quedó para los productos Enterprise: **verifica el repositorio de cada chart** antes de fijarlo.
    - El **Collector** se despliega casi siempre en **dos niveles** (agente DaemonSet + gateway Deployment) y el gateway con tail sampling detrás de `load_balancing` (documentado en el README del procesador y usado por Honeycomb Refinery y los despliegues de OpenTelemetry Demo).
    - Los charts de **kube-prometheus-stack**, **opentelemetry-kube-stack** y **k8s-monitoring** empaquetan «un stack completo»: útiles para empezar; aprende primero a leer los values de cada pieza (este módulo) para poder depurarlos.
    - Las plataformas de ingeniería maduras no despliegan nunca desde una laptop: **GitOps + revisión + validación en CI** (kubeconform, conftest/Kyverno para políticas de seguridad: `runAsNonRoot`, `readOnlyRootFilesystem`, límites de memoria).
    """)
    md("""
    ## 14 · 🧠 Secretos de la élite

    1. **`helm lint` no valida la aplicación.** Pasa con un Collector de configuración inválida. Extrae el ConfigMap renderizado y valídalo con el binario (medido: `port` de `load_balancing` entero ⇒ error de tipo; §6).
    2. **Las listas se reemplazan, los mapas se fusionan.** Al sobrescribir `service.pipelines.logs.exporters` repite toda la lista; para quitar un receptor por defecto usa `null` (§2). Es la causa de «he añadido un exportador y han desaparecido los otros».
    3. **Un componente con estado no se escala como uno sin estado.** Sin `load_balancing` por `traceID` el 42 % de las trazas interesantes quedaron rotas con solo 2 réplicas (§9); y cada cambio de réplicas reasigna trazas en curso: estabiliza la bajada (§10) y usa PDB.
    4. **No pongas límites de CPU a un Collector** (sí de memoria y `memory_limiter` por debajo): el *throttling* de CFS produce latencia y pérdidas justo en las ráfagas. Pide CPU (`requests`) para que el scheduler lo reserve.
    5. **El agente y el gateway tienen presupuestos distintos.** El agente va por nodo: barato (50 m/128 Mi aquí); el gateway concentra memoria (≈ tráfico × `decision_wait`, módulo 18). Dimensiónalos por separado.
    6. **La configuración depende del entorno del pod.** `${env:MY_POD_IP}`, `K8S_NODE_NAME`… provienen del *downward API*: una validación fuera del pod necesita las mismas variables (§6).
    7. **`--wait` de Helm 4.** `--wait=false` está obsoleto (se sustituye por `--wait=hookOnly`): scripts de CI escritos para Helm 3 emiten avisos o esperan por defecto. Fija la versión de Helm en CI.
    8. **Nada de `latest`, nada sin versión.** Un chart sin `--version` y una imagen sin `tag` convierten tu plataforma en una lotería; las 7 versiones de este módulo están verificadas y fijadas.
    """)
    md("""
    ## 15 · ⚠️ Errores comunes

    - Confiar en `helm lint` como validación de las configuraciones del Collector/Tempo/Loki.
    - Escalar el gateway con tail sampling con un Service normal (sin `load_balancing`).
    - Un HPA sin `requests` de CPU (la utilización se calcula sobre requests) o sin metrics-server.
    - Olvidar `automountServiceAccountToken: false`, `runAsNonRoot` y `readOnlyRootFilesystem` en cargas propias (el chart `supportops` los fija).
    - Usar `kind load docker-image` con la etiqueta `latest` (el kubelet intenta *pull*): usa una etiqueta explícita y `imagePullPolicy: IfNotPresent`.
    - Poner la contraseña de Grafana en un values del repositorio.
    - Mezclar charts de `grafana/helm-charts` y `grafana-community/helm-charts` sin comprobar cuál mantiene cada componente.
    """)
    md(mdj("""
    ## 16 · Autoevaluación
    """,
           details("1. (Cálculo) Un HPA con objetivo 70 % de CPU tiene 3 réplicas al 98 % de utilización. ¿Cuántas réplicas pide? ¿Y si estuvieran al 74 %?",
                   "$\\lceil 3\\cdot 98/70\\rceil=\\lceil 4,2\\rceil=5$. Con 74 %: la razón $74/70=1,057$ está dentro de la tolerancia del 10 % ⇒ **no cambia** (3)."),
           details("2. (Cálculo) El gateway recibe 150 trazas nuevas/s, `decision_wait` 10 s y cada traza ocupa ≈ 30 KB en memoria. ¿Qué `requests`/`limits` de memoria pones por réplica con 3 réplicas y qué `num_traces`?",
                   "Por réplica: 50 trazas/s × 10 s = 500 trazas × 30 KB ≈ 15 MB de datos; con las estructuras del procesador y GOMEMLIMIT, `requests` 256 Mi y `limits` 512 Mi son holgados. `num_traces` ≥ 500 × 1,5 ≈ 750 por réplica (y mucho más si el tráfico crece: usa 20 000 como en los values y alerta sobre `dropped_too_early`)."),
           details("3. (Diagnóstico) Tras escalar el gateway de 2 a 4 réplicas aparecen trazas de error «incompletas» en Tempo y el recall de errores baja. El agente usa `load_balancing`. ¿Qué miras?",
                   "(a) La resolución DNS del Service headless (`interval` del resolvedor: hasta que se actualice, parte del tráfico va al anillo viejo); (b) que las réplicas nuevas estén `Ready` antes de entrar en el DNS; (c) que `decision_wait` cubra el retraso; (d) la ventana de estabilización del HPA: cada cambio reasigna trazas en curso. `sampling_trace_dropped_too_early` y `sampling_traces_on_memory` por réplica."),
           details("4. (Diagnóstico) `helm install` termina bien pero el pod del Collector está en `CrashLoopBackOff` con `'port' expected type 'string', got unconvertible type 'int'`. ¿Cómo evitas que vuelva a pasar?",
                   "Validar en CI la configuración renderizada con `otelcol-contrib validate` (con las variables de entorno que inyecta el pod) además de `helm lint`/`kubeconform`; y comprobar el tipo en los values (`port: \"4317\"`)."),
           details("5. (Transferencia) Tu empresa usa Datadog en producción y quiere un laboratorio OTel/Grafana en Kubernetes para pruebas. ¿Qué parte de este módulo reutilizas y qué cambiarías?",
                   "Reutilizas el patrón agente DaemonSet + gateway Deployment, los values del Collector (cambiando solo el exportador al backend que corresponda) y el CI de validación. Cambiarías los exportadores (`datadog` en contrib) y los datasources; la afinidad por `traceID`, el dimensionado y la validación de configuración se mantienen."),
           details("6. (Transferencia) ¿Cuándo elegirías el Operator frente al chart del Collector?",
                   "Cuando necesitas auto-instrumentación por anotación, reconciliación continua o el TargetAllocator para raspar Prometheus a escala con muchos Collectors; si quieres ver y versionar el YAML final y evitar webhooks/cert-manager, el chart con GitOps es más simple de depurar.")))

    md("""
    ## 17 · Referencias

    - Helm: documentación (`helm template`, `helm lint`, esquemas de values, `--wait`): https://helm.sh/docs/ · notas de Helm 4: https://helm.sh/docs/overview/
    - OpenTelemetry Helm charts (repositorio verificado en oct-2026: `opentelemetry-collector` 0.176.0 / app 0.162.0; `opentelemetry-operator` 0.126.0 / app 0.161.0; `opentelemetry-kube-stack` 0.24.6): https://github.com/open-telemetry/opentelemetry-helm-charts
    - Grafana community charts (Tempo 3.2.0, Loki 18.16.0, Grafana 14.0.0): https://github.com/grafana-community/helm-charts · charts del Pyroscope: https://github.com/grafana/pyroscope/tree/main/operations/pyroscope/helm/pyroscope
    - OpenTelemetry Operator: https://github.com/open-telemetry/opentelemetry-operator (CRDs `OpenTelemetryCollector` v1beta1, `Instrumentation` v1alpha1; requisitos de TLS del webhook en el README del chart).
    - OpenTelemetry Collector contrib: `loadbalancingexporter` (`load_balancing`) y `tailsamplingprocessor` (README v0.162.0): https://github.com/open-telemetry/opentelemetry-collector-contrib
    - Kubernetes: HorizontalPodAutoscaler (algoritmo y `behavior`): https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
    - kubeconform: https://github.com/yannh/kubeconform · kind: https://kind.sigs.k8s.io · k3s: https://k3s.io
    """)
    nb.save(out)


# =====================================================================================================================
# 8. Proyecto
# =====================================================================================================================
SOLUTION_19 = '''
def gateway_overrides(decision_wait, num_traces, baseline_pct, replicas):
    return {"autoscaling": {"minReplicas": replicas},
            "config": {"processors": {"tail_sampling": {"decision_wait": decision_wait, "num_traces": num_traces,
                                                          "policies": [{"name": "errors", "type": "status_code", "status_code": {"status_codes": ["ERROR"]}},
                                                                       {"name": "slow", "type": "latency", "latency": {"threshold_ms": 5000}},
                                                                       {"name": "costly", "type": "ottl_condition", "ottl_condition": {"error_mode": "ignore", "span": ['attributes["supportops.cost_usd"] > 0.0005']}},
                                                                       {"name": "baseline", "type": "probabilistic", "probabilistic": {"sampling_percentage": baseline_pct}}]}}}}

def memory_budget(manifests, node_mem_mib, headroom=0.5):
    total = K.resource_requests(manifests)["memory_mib"]
    return total <= node_mem_mib * headroom, total

def security_findings(manifests):
    out = []
    for m in manifests:
        if m.get("kind") not in ("Deployment", "StatefulSet", "DaemonSet"):
            continue
        pod = m["spec"]["template"]["spec"]
        pod_nonroot = (pod.get("securityContext") or {}).get("runAsNonRoot") is True
        for c in pod.get("containers", []):
            sc = c.get("securityContext") or {}
            who = f"{m['kind']}/{m['metadata']['name']}/{c['name']}"
            if "memory" not in ((c.get("resources") or {}).get("limits") or {}):
                out.append(f"{who}: sin limits.memory")
            if not (pod_nonroot or sc.get("runAsNonRoot") is True):
                out.append(f"{who}: runAsNonRoot no está a true")
            if sc.get("readOnlyRootFilesystem") is not True:
                out.append(f"{who}: readOnlyRootFilesystem no está a true")
    return out

def validate_rendered(rendered):
    cfg = {"otel-gateway": ("collector", K.configmap_text(rendered["otel-gateway"], "otel-gateway", "relay")),
           "otel-agent": ("collector", K.configmap_text(rendered["otel-agent"], "otel-agent", "relay")),
           "tempo": ("tempo", K.configmap_text(rendered["tempo"], "tempo", "tempo.yaml")),
           "loki": ("loki", K.configmap_text(rendered["loki"], "loki", "config.yaml"))}
    return {k: K.validate_with_binary(kind, txt)[0] for k, (kind, txt) in cfg.items()}

AFFINITY_TYPES = {"latency", "status_code", "span_count", "numeric_attribute", "string_attribute", "boolean_attribute", "ottl_condition", "trace_state", "and", "composite"}
def needs_affinity(policies):
    return any(p["type"] in AFFINITY_TYPES for p in policies)

def desired_replicas(current, metric, target, min_r, max_r, tol=0.1):
    ratio = metric / target
    d = current if abs(ratio - 1) <= tol else math.ceil(current * ratio)
    return max(min_r, min(max_r, d))

def operator_cr(values, name="gateway", namespace="observability"):
    cfg = {k: v for k, v in values["config"].items() if k in ("receivers", "processors", "exporters", "connectors", "service")}
    cr = {"apiVersion": "opentelemetry.io/v1beta1", "kind": "OpenTelemetryCollector", "metadata": {"name": name, "namespace": namespace},
          "spec": {"mode": values["mode"], "image": f"{values['image']['repository']}:{values['image']['tag']}", "replicas": values["replicaCount"],
                   "resources": values["resources"], "config": cfg}}
    a = values.get("autoscaling") or {}
    if a.get("enabled"):
        cr["spec"]["autoscaler"] = {"minReplicas": a["minReplicas"], "maxReplicas": a["maxReplicas"], "targetCPUUtilization": a["targetCPUUtilizationPercentage"]}
    if (values.get("podDisruptionBudget") or {}).get("enabled"):
        cr["spec"]["podDisruptionBudget"] = {"minAvailable": values["podDisruptionBudget"]["minAvailable"]}
    return cr

def verify_flow(flow):
    frac = flow["traces_in_tempo"] / flow["tickets"]
    return {"trazas conservadas entre 10 % y 40 %": 0.10 <= frac <= 0.40, "hay logs en Loki": flow["loki_lines"] > 0, "hay métricas gen_ai en Prometheus": flow["prom_genai_series"] > 0,
            "hay span_metrics con llamadas": flow["span_metrics_calls"] > 0, "el gateway está up": len(flow["gateway_up"]) >= 1 and all(float(x) == 1.0 for x in flow["gateway_up"])}
'''

RUBRIC_19 = '''
def run_rubric(live=LIVE_RENDER, docker=DOCKER):
    R = {}
    def chk(name, fn, needs=True):
        if not needs:
            R[name] = None; return
        try:
            R[name] = bool(fn())
        except NotImplementedError:
            R[name] = None
        except Exception as e:
            R[name] = False; print(f"  {name}: {type(e).__name__}: {str(e)[:300]}")
    def r1():
        ov = gateway_overrides("20s", 30000, 5, 3)
        ms = K.render("otel-gateway", "otel-collector", [VALUES / "otel-gateway.yaml", ov])
        cfg = yaml.safe_load(K.configmap_text(ms, "otel-gateway", "relay"))
        ts = cfg["processors"]["tail_sampling"]
        hpa = next(m for m in ms if m["kind"] == "HorizontalPodAutoscaler")
        pols = {p["name"]: p for p in ts["policies"]}
        return (ts["decision_wait"] == "20s" and ts["num_traces"] == 30000 and pols["baseline"]["probabilistic"]["sampling_percentage"] == 5 and list(pols) == ["errors", "slow", "costly", "baseline"]
                and hpa["spec"]["minReplicas"] == 3 and K.kubeconform(ms)["invalid"] == 0 and (not docker or K.validate_with_binary("collector", K.configmap_text(ms, "otel-gateway", "relay"))[0]))
    chk("R1 gateway_overrides: values por capas → decision_wait, num_traces, baseline y réplicas correctos; kubeconform y otelcol validate OK", r1, live)
    def r2():
        tot = {k: K.resource_requests(v)["memory_mib"] for k, v in REND.items()}
        ok, total = memory_budget(sum(REND.values(), []), 8192, 0.5)
        ok2, _ = memory_budget(REND["tempo"], 200, 1.0)
        return ok and abs(total - sum(tot.values())) < 1e-6 and ok2 is False
    chk("R2 memory_budget: suma de requests de todos los releases (≈ 1,4 GiB) cabe en el 50 % de 8 GiB y Tempo solo NO cabe en 200 MiB", r2, live)
    def r3():
        counts = {k: len(security_findings(v)) for k, v in REND.items()}
        return counts == EXPECTED_FINDINGS and counts["supportops"] == 0
    chk("R3 security_findings: 0 hallazgos en el chart propio y los mismos que la referencia en el resto de releases", r3, live)
    chk("R4 validate_rendered: gateway, agente, Tempo y Loki válidos según SUS binarios (Docker)", lambda: all(validate_rendered(REND).values()), live and docker)
    chk("R5 needs_affinity: errors/latency exigen afinidad por traceID; solo probabilistic, no", lambda: needs_affinity([{"type": "status_code"}, {"type": "probabilistic"}]) and needs_affinity([{"type": "latency"}])
        and not needs_affinity([{"type": "probabilistic"}]))
    chk("R6 desired_replicas: coincide con K.hpa_desired en 8 casos (tolerancia del 10 %, mínimos y máximos)", lambda: all(desired_replicas(*a) == K.hpa_desired(*a) for a in
        [(3, 98, 70, 2, 10), (3, 74, 70, 2, 10), (4, 20, 70, 2, 10), (6, 700, 70, 2, 8), (2, 70, 70, 1, 5), (5, 40, 70, 3, 9), (1, 1000, 70, 1, 4), (10, 66, 70, 2, 12)]))
    def r7():
        vals = yaml.safe_load((VALUES / "otel-gateway.yaml").read_text())
        cr = operator_cr(vals)
        ok = (cr["apiVersion"] == "opentelemetry.io/v1beta1" and cr["kind"] == "OpenTelemetryCollector" and cr["spec"]["autoscaler"]["maxReplicas"] == 6 and cr["spec"]["podDisruptionBudget"]["minAvailable"] == 1
              and "tail_sampling" in cr["spec"]["config"]["processors"] and isinstance(cr["spec"]["config"], dict))
        if not (live and docker):
            return ok
        cr["spec"]["config"]["service"]["pipelines"]["traces/in"]  # existe
        r = API_LAB.apply([cr], dry_run=True)
        return ok and r.returncode == 0
    chk("R7 operator_cr: CR v1beta1 con autoscaler y PDB derivados de los values; el API server real lo acepta (--dry-run=server)", r7)
    chk("R8 verify_flow: aprueba el flujo medido y suspende un flujo roto", lambda: all(verify_flow(REC["flow"]).values()) and not all(verify_flow({**REC["flow"], "loki_lines": 0, "traces_in_tempo": 290}).values()))
    ok = sum(v is True for v in R.values()); tot = sum(v is not None for v in R.values())
    for k, v in R.items():
        print(("✅" if v else ("⏭️ " if v is None else "❌")), k)
    print(f"\\nPuntuación: {ok}/{tot} comprobaciones superadas" + ("" if (live and docker) else " (algunas se omiten sin helm/charts/Docker)"))
    return R
'''


def build_project() -> None:
    nb, out = nb_for(MOD, "19_proyecto_kubernetes_helm.ipynb", "Proyecto 19 · Desplegar el stack y SupportOps en Kubernetes con Helm")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 19 · Despliega el stack y SupportOps en Kubernetes (con Helm) y verifica el flujo de telemetría

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 2 h 30 min |
    | **Servicios de Compose** | Ninguno. Necesita `helm` y, para R1/R4/R7, Docker (contenedores efímeros y un API server k3s). Sin ellos, esas comprobaciones se omiten y el resto puntúa |
    | **RAM aproximada** | ≈ 1-2 GB durante la rúbrica |
    | **Prerrequisitos** | Lección `19_kubernetes_helm`; proyecto 18 (la política de muestreo) y módulo 05 |
    | **Conexión** | Despliega como código la plataforma completa de los módulos 05-18 (Collector de dos capas con la política de muestreo, Tempo, Loki, Prometheus, Grafana) y el agente SupportOps; es el «Despliegue» del capstone |

    ## Contexto de negocio

    Eres ingeniero/a de plataforma en **SupportOps**. Producción pasa de `docker compose` a Kubernetes y el equipo de seguridad exige: **requests/limits, usuario no-root, sistema de ficheros de solo lectura**, validación automática en CI de todo lo que se despliegue,
    autoscaling del gateway **sin romper el tail sampling**, y la opción de gestionar el Collector con el Operator. Tú escribes las piezas de código que lo comprueban y generan; la rúbrica las ejecuta contra los charts, los binarios y un API server reales.

    ## Datos

    Los charts y values del módulo (`k8s/`), 7 releases ya renderizados en `REND` y el flujo medido en `REC["flow"]`. Sin datos externos.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución) |
    |---|---|---|---|
    | R1 | `gateway_overrides` | `helm template` con tus capas: `decision_wait`, `num_traces`, baseline, nº de réplicas; `kubeconform` y `otelcol validate` | exacto; 0 inválidos |
    | R2 | `memory_budget` | suma de requests de memoria de todos los releases frente a un nodo | ≈ 1,4 GiB total ≤ 50 % de 8 GiB; Tempo solo no cabe en 200 MiB |
    | R3 | `security_findings` | hallazgos por release (sin `limits.memory`, sin `runAsNonRoot`, sin `readOnlyRootFilesystem`) | 0 en `supportops`; mismos que la referencia en el resto |
    | R4 | `validate_rendered` | las configuraciones renderizadas pasan por **su** binario | 4/4 (con Docker) |
    | R5 | `needs_affinity` | qué políticas de tail sampling exigen que la traza llegue entera a una réplica | exacto |
    | R6 | `desired_replicas` | algoritmo del HPA | 8/8 casos idénticos al de Kubernetes |
    | R7 | `operator_cr` | CR `OpenTelemetryCollector` v1beta1 derivado de tus values; el API server real lo valida | estructura + `--dry-run=server` OK |
    | R8 | `verify_flow` | criterios de aceptación del flujo extremo a extremo | aprueba el medido y suspende uno roto |

    > 📏 Los umbrales salen de la solución con los charts verificados (Collector 0.176.0, Tempo 3.2.0, Loki 18.16.0, Grafana 14.0.0). Si usas otras versiones de chart, las cifras de R2/R3 pueden cambiar.
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_19 + PLAN_CELL)

    md("""
    ## Paso 0 · Los releases renderizados (te lo damos hecho)

    `REND` contiene los manifiestos de los 7 releases (o, sin helm, los datos pregrabados reducidos). `API_LAB` es un API server k3s real si hay Docker (se usa en R7; se destruye al final de la rúbrica).
    """)
    code('''
if LIVE_RENDER:
    REND = {rel: K.render(rel, ch, [VALUES / v for v in vals], namespace=ns) for rel, ch, vals, ns in PLAN}
    print({k: len(v) for k, v in REND.items()}, "manifiestos")
else:
    REND = {}
    print("sin helm/charts: R1-R4 se omiten; el resto de pasos sigue funcionando")
API_LAB = None
''')

    def todo(n, title, desc, stub, hints=()):
        md(f"## Paso {n} · {title}\n\n{desc}" + ("\n\n" + "\n\n".join(hint(i + 1, h) for i, h in enumerate(hints)) if hints else ""))
        code(stub)

    todo(1, "El gateway por capas de values (TODO)",
         "Escribe `gateway_overrides(decision_wait, num_traces, baseline_pct, replicas)` → un dict de **values** (solo lo que cambia) que, aplicado sobre `k8s/values/otel-gateway.yaml`, fija `decision_wait`, `num_traces`, el `sampling_percentage` de la política `baseline` y `autoscaling.minReplicas`. "
         "⚠️ Recuerda la regla de fusión de la lección §2: **las listas se reemplazan enteras** (`policies` incluida: repite las cuatro, con los mismos nombres y en el mismo orden: `errors`, `slow`, `costly`, `baseline`).",
         '''
def gateway_overrides(decision_wait, num_traces, baseline_pct, replicas):
    # TODO: {"autoscaling": {"minReplicas": ...}, "config": {"processors": {"tail_sampling": {...}}}}
    raise NotImplementedError("TODO 1")

try:
    if LIVE_RENDER:
        ms = K.render("otel-gateway", "otel-collector", [VALUES / "otel-gateway.yaml", gateway_overrides("20s", 30000, 5, 3)])
        print(yaml.safe_load(K.configmap_text(ms, "otel-gateway", "relay"))["processors"]["tail_sampling"]["policies"][-1])
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Las capas de values se aplican de izquierda a derecha; la tuya gana. Solo necesitas escribir las claves que cambian, pero `policies` es una lista: se reemplaza completa.",
      "`{\"autoscaling\": {\"minReplicas\": replicas}, \"config\": {\"processors\": {\"tail_sampling\": {\"decision_wait\": ..., \"num_traces\": ..., \"policies\": [ {...errors}, {...slow}, {...costly OTTL}, {...baseline} ]}}}}`; copia las políticas del módulo 18 (el coste con `ottl_condition`, no `numeric_attribute`)."])

    todo(2, "El presupuesto de memoria (TODO)",
         "Escribe `memory_budget(manifests, node_mem_mib, headroom=0.5)` → `(cabe, total_mib)`: suma las `requests` de memoria de los manifiestos (usa `K.resource_requests`) y comprueba que no superan `headroom` × la memoria del nodo (dejamos la mitad libre para el sistema y los picos).",
         '''
def memory_budget(manifests, node_mem_mib, headroom=0.5):
    # TODO
    raise NotImplementedError("TODO 2")

try:
    if LIVE_RENDER:
        print(memory_budget(sum(REND.values(), []), 8192, 0.5), memory_budget(REND["tempo"], 200, 1.0))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["`K.resource_requests(manifiestos)` ya devuelve `{\"cpu_m\", \"memory_mib\"}` con las réplicas contadas.", "`total = K.resource_requests(manifests)[\"memory_mib\"]; return total <= node_mem_mib * headroom, total`."])

    todo(3, "Seguridad (TODO)",
         "Escribe `security_findings(manifests)` → lista de textos (uno por hallazgo) para cada contenedor de Deployment/StatefulSet/DaemonSet que **(a)** no tenga `resources.limits.memory`, **(b)** no tenga `runAsNonRoot: true` (a nivel de pod **o** de contenedor) o **(c)** no tenga `securityContext.readOnlyRootFilesystem: true`. "
         "Formato: `\"Deployment/nombre/contenedor: motivo\"`.",
         '''
def security_findings(manifests):
    # TODO: recorre manifests; pod = m["spec"]["template"]["spec"]; contenedores en pod["containers"]
    raise NotImplementedError("TODO 3")

try:
    if LIVE_RENDER:
        for k, v in REND.items():
            print(k, len(security_findings(v)))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Los manifiestos son dicts de Python (salida de `yaml.safe_load`): `m[\"kind\"]`, `m[\"metadata\"][\"name\"]`, `m[\"spec\"][\"template\"][\"spec\"][\"containers\"]`.", "Usa `(c.get(\"securityContext\") or {})` y `(pod.get(\"securityContext\") or {})` para evitar `KeyError` cuando falta el bloque."])

    todo(4, "Valida lo renderizado con los binarios (TODO)",
         "Escribe `validate_rendered(rendered)` → `{\"otel-gateway\": bool, \"otel-agent\": bool, \"tempo\": bool, \"loki\": bool}`: extrae cada ConfigMap con `K.configmap_text` (claves `relay`, `relay`, `tempo.yaml`, `config.yaml`) y valida con `K.validate_with_binary(kind, texto)[0]` (`kind` ∈ `collector|tempo|loki`).",
         '''
def validate_rendered(rendered):
    # TODO
    raise NotImplementedError("TODO 4")

try:
    if LIVE_RENDER and DOCKER:
        print(validate_rendered(REND))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["`K.configmap_text(manifiestos, nombre_del_configmap, clave)`; el ConfigMap del gateway se llama `otel-gateway` y su clave es `relay`.", "`{\"otel-gateway\": K.validate_with_binary(\"collector\", K.configmap_text(rendered[\"otel-gateway\"], \"otel-gateway\", \"relay\"))[0], ...}`."])

    todo(5, "¿Cuándo hace falta afinidad? (TODO)",
         "Escribe `needs_affinity(policies)` → `True` si **alguna** política de la lista (dicts con `type`) depende de ver la traza **entera**. Piensa en la lección §9: `probabilistic` decide solo con el `traceID` (todas las réplicas deciden igual), mientras que las que miran spans, estado, duración o número de spans necesitan toda la traza en una réplica.",
         '''
def needs_affinity(policies):
    # TODO: tipos que necesitan la traza completa: latency, status_code, span_count, numeric_attribute, string_attribute, boolean_attribute, ottl_condition, trace_state, and, composite
    raise NotImplementedError("TODO 5")

try:
    print(needs_affinity([{"type": "probabilistic"}]), needs_affinity([{"type": "status_code"}, {"type": "probabilistic"}]))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Una política «por traceID» da el mismo veredicto en cualquier réplica; una política «por contenido» solo es correcta si la réplica tiene todos los spans.", "`any(p[\"type\"] != \"probabilistic\" for p in policies)` sirve como primera aproximación; la referencia usa la lista explícita de tipos."])

    todo(6, "El HPA (TODO)",
         "Escribe `desired_replicas(current, metric, target, min_r, max_r, tol=0.1)` con el algoritmo del HorizontalPodAutoscaler: `ceil(current × métrica/objetivo)`, sin cambios si `|métrica/objetivo − 1| ≤ tol`, acotado a `[min_r, max_r]`.",
         '''
def desired_replicas(current, metric, target, min_r, max_r, tol=0.1):
    # TODO
    raise NotImplementedError("TODO 6")

try:
    print([desired_replicas(3, 98, 70, 2, 10), desired_replicas(3, 74, 70, 2, 10), desired_replicas(6, 700, 70, 2, 8)])
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["La razón métrica/objetivo decide todo: dentro de la tolerancia no hay cambio.", "`ratio = metric/target; d = current if abs(ratio-1) <= tol else math.ceil(current*ratio); return max(min_r, min(max_r, d))`."])

    todo(7, "Del chart al Operator (TODO)",
         "Escribe `operator_cr(values, name=\"gateway\", namespace=\"observability\")` → el dict de un CR `OpenTelemetryCollector` (`opentelemetry.io/v1beta1`) derivado de los **values** del gateway: `mode`, `image` (`repositorio:tag`), `replicas`, `resources`, `config` (receivers/processors/exporters/connectors/service; en v1beta1 es un **mapa**), "
         "`autoscaler` (`minReplicas`, `maxReplicas`, `targetCPUUtilization`) si `autoscaling.enabled`, y `podDisruptionBudget` si está habilitado.",
         '''
def operator_cr(values, name="gateway", namespace="observability"):
    # TODO: ver k8s/operator/collector-gateway.yaml como modelo
    raise NotImplementedError("TODO 7")

try:
    vals = yaml.safe_load((VALUES / "otel-gateway.yaml").read_text())
    print(list(operator_cr(vals)["spec"]))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["El modelo es `k8s/operator/collector-gateway.yaml`. Los nombres de los campos del CR no son los de los values (`targetCPUUtilizationPercentage` → `targetCPUUtilization`).", "`spec = {\"mode\": ..., \"image\": f\"{repo}:{tag}\", \"replicas\": values[\"replicaCount\"], \"resources\": ..., \"config\": {k: values[\"config\"][k] for k in (...)}}`; la config de los values contiene claves con `None` (borrados de Helm): ¡fíltralas por las cinco claves de la lista!"])

    todo(8, "Criterios de aceptación del flujo (TODO)",
         "Escribe `verify_flow(flow)` → dict `{criterio: bool}` con cinco comprobaciones sobre el resultado del flujo (`REC[\"flow\"]`: `tickets`, `traces_in_tempo`, `loki_lines`, `prom_genai_series`, `span_metrics_calls`, `gateway_up`): "
         "trazas conservadas entre el 10 % y el 40 % de los tickets, hay logs, hay métricas `gen_ai`, hay `span_metrics` con llamadas y todas las réplicas del gateway están `up` (=1).",
         '''
def verify_flow(flow):
    # TODO
    raise NotImplementedError("TODO 8")

try:
    print(verify_flow(REC["flow"]))
except NotImplementedError as e:
    print("⏳ pendiente:", e)
''', ["Un criterio de aceptación es una proposición booleana sobre las métricas medidas; el 10-40 % sale de la política (≈ 10 % base + lo interesante).", "`frac = flow[\"traces_in_tempo\"]/flow[\"tickets\"]`; `{\"trazas...\": 0.10 <= frac <= 0.40, \"hay logs...\": flow[\"loki_lines\"] > 0, ...}`."])

    md("## Rúbrica · ejecútala cuando quieras")
    code('''
EXPECTED_FINDINGS = REC["expected_findings"]
'''.strip() + RUBRIC_19 + '''
try:
    if LIVE_RENDER and DOCKER and API_LAB is None:
        API_LAB = K.ApiServerLab().__enter__()
        API_LAB.ensure_namespace("observability")
        op = API_LAB.helm_install("otel-operator", "otel-operator", [K8S / "operator" / "values-operator.yaml"], namespace="opentelemetry-operator-system", set_values={"admissionWebhooks.create": "false"})
    run_rubric()
except NameError as e:
    print("Define las funciones de los pasos primero:", e)
finally:
    if API_LAB is not None:
        API_LAB.__exit__(); API_LAB = None
''')

    md("""
    ## Retos extra (nivel experto)

    1. **Despliegue real**: con kind/k3d en tu máquina, construye la imagen (`k8s/image/Dockerfile`), cárgala con `kind load docker-image`, instala los 7 releases en orden (Tempo/Loki/Prometheus → gateway → agente → Grafana → SupportOps) y **ejecuta `verify_flow` contra los backends del clúster** (`kubectl port-forward`).
    2. **HPA por memoria de tail sampling**: escribe el `HorizontalPodAutoscaler` (v2, métrica `Pods`) sobre `otelcol_processor_tail_sampling_sampling_traces_on_memory` (con Prometheus Adapter o KEDA) y simula con `K.hpa_simulate` si cambia el comportamiento frente a CPU.
    3. **Política de seguridad como código**: convierte `security_findings` en una regla de Kyverno o conftest y pruébala con `kubeconform`.
    4. **Tres capas**: añade un Collector intermedio solo para `span_metrics`/`k8s_attributes` y mide con `K.affinity_experiment` qué cambia en la completitud de trazas.
    5. **Upgrade sin pérdida**: simula un `helm upgrade` del gateway (mismo `decision_wait`) con 3 réplicas y calcula cuántas trazas en curso se reasignan (anillo de `load_balancing`).
    """)
    md("""
    ## Reflexión

    - ¿Qué pasaría con tu política de muestreo si el HPA duplicara las réplicas en pleno incidente (justo cuando más errores hay)? ¿Qué protege tu SLO de observabilidad?
    - ¿Qué parte de este despliegue pondrías bajo GitOps y cuál mantendrías manual? ¿Por qué?
    - ¿Qué validaciones de este proyecto **no** habrían detectado un `CrashLoopBackOff` por falta de memoria o una sonda mal puesta? ¿Cómo las cubrirías en un clúster real?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable: redefine las funciones y vuelve a lanzar la rúbrica.
    """)
    code('# ===================== SOLUCIÓN DE REFERENCIA =====================' + SOLUTION_19 + '''
if LIVE_RENDER and DOCKER:
    API_LAB = K.ApiServerLab().__enter__()
    API_LAB.ensure_namespace("observability")
    API_LAB.helm_install("otel-operator", "otel-operator", [K8S / "operator" / "values-operator.yaml"], namespace="opentelemetry-operator-system", set_values={"admissionWebhooks.create": "false"})
try:
    if LIVE_RENDER:
        print({k: len(security_findings(v)) for k, v in REND.items()}, "· memoria total (MiB):", round(memory_budget(sum(REND.values(), []), 8192)[1]))
    print(verify_flow(REC["flow"]))
    R = run_rubric()
finally:
    if API_LAB is not None:
        API_LAB.__exit__(); API_LAB = None
''')
    nb.save(out)


README_19 = """# Módulo 19 · Kubernetes + Helm para la plataforma de observabilidad

**Nivel:** 🔴 Experto · **Duración:** ≈ 5 h (lección) + ≈ 2 h 30 (proyecto) · **Necesita:** `helm` 4.x (y Docker para los experimentos con contenedores). Un clúster kind/k3d en tu máquina es lo ideal (ver «Honestidad»).

Desplegar el Collector (agente DaemonSet + gateway con tail sampling), Tempo, Loki, Prometheus, Grafana y el agente SupportOps con **Helm**, con configuración como código: la regla de fusión de *values*, un chart propio con esquema y seguridad, validación (`helm lint`, `kubeconform`, binarios oficiales), afinidad por `traceID`, autoscaling y el **OpenTelemetry Operator**.

## Contenido

| Archivo | Qué es |
|---|---|
| `19_kubernetes_helm.ipynb` | Lección (17 secciones, 7 gráficos, experimentos con un API server real y con los binarios, 🧠 de élite, autoevaluación) |
| `19_proyecto_kubernetes_helm.ipynb` | Proyecto: values por capas, presupuesto de memoria, seguridad, validación, afinidad, HPA, CR del Operator y criterios de aceptación (rúbrica R1-R8, pistas 🪜, solución tras ⛔ SPOILER) |
| `k8s/charts/supportops/` | Chart propio del agente: `values.schema.json`, Deployment seguro (`runAsNonRoot`, `readOnlyRootFilesystem`, checksum de config), HPA, PDB |
| `k8s/charts/prom-lab/` | Prometheus mínimo con receptor OTLP (scrape por DNS del Service headless del gateway) |
| `k8s/values/` | values de los charts oficiales: `otel-gateway`, `otel-agent`, `tempo`, `loki`, `grafana` (generados por `build_19.py`) y `supportops-lab` |
| `k8s/operator/` | `values-operator.yaml`, `collector-gateway.yaml` (CR v1beta1), `instrumentation.yaml` (CR v1alpha1) |
| `k8s/kind-config.yaml`, `k8s/image/Dockerfile` | Clúster kind e imagen de laboratorio de SupportOps |
| `recorded/capture_seed42.json.gz` | Resultados pregrabados de todos los experimentos (modo sin helm/Docker) |
| `../supportops/k8s.py` | `deep_merge`, charts (`CHARTS`, `chart_path`), `render`/`lint`/`kubeconform`, `ApiServerLab` (k3s), `FlowLab`, `AffinityLab`, HPA, `python -m supportops.k8s run` |
| `../supportops/tests/test_k8s.py` | Pruebas (las de helm se saltan si no está) |
| `../stack/grafana/dashboards/19-kubernetes.json` | Dashboard «19 · Gateway del Collector en Kubernetes» (uid `k8s-gateway`) |

## Versiones verificadas (oct-2026, en los repositorios oficiales)

| Chart | Repositorio | Versión | App |
|---|---|---|---|
| `opentelemetry-collector` | open-telemetry/opentelemetry-helm-charts | 0.176.0 | 0.162.0 |
| `opentelemetry-operator` | ídem | 0.126.0 | 0.161.0 (requiere Helm 4+) |
| `tempo` (monolítico) | grafana-community/helm-charts | 3.2.0 | 3.1.0 |
| `loki` | ídem | 18.16.0 | 3.7.8 |
| `grafana` | ídem | 14.0.0 | 13.2.4 |

(El chart de Pyroscope vive en `grafana/pyroscope` → `operations/pyroscope/helm/pyroscope`, 2.4.0. Desde marzo de 2026 el chart de Loki OSS está en `grafana-community`; `grafana/helm-charts` queda para Enterprise.)

## Honestidad: qué corrió en un clúster real y qué NO

En el sandbox donde se construyó este módulo **kind (K8s 1.31 y 1.34) y k3s no pudieron arrancar pods** (`runc` anidado: «can't get final child's PID from pipe: EOF»); además `github.io`, `ghcr.io`, `quay.io` y `registry.k8s.io` estaban bloqueados (los charts se tomaron de clones de GitHub; el Operator y cert-manager no se pudieron descargar). **Ningún pod se ejecutó en un clúster.**

**Sí se verificó con binarios reales:** `helm lint`/`template` de los 7 releases (Helm 4.3.1), `kubeconform` (K8s 1.31), validación de las configuraciones **renderizadas** con `otelcol-contrib 0.162.0`, Tempo 3.1.0, Loki 3.7.8 y promtool; `helm install` y `--dry-run=server` de todo, y los CRs del Operator, contra un **API server real (k3s 1.31.5)**; el **flujo de telemetría de extremo a extremo** (Tempo + Loki + Prometheus + gateway en contenedores con los ConfigMaps renderizados y los DNS de los Services como alias); y la **afinidad por `traceID`** con 2 Collectors reales.

**No verificado:** planificación y sondas de pods (la `livenessProbe` por latido del chart `supportops` y el Service `otel-agent` con `internalTrafficPolicy: Local` solo pasaron el esquema y el API server), `hostPort`, HPA con métricas reales (sin metrics-server), el Operator en ejecución (webhook, cert, inyección), kind/k3d con pods y la imagen `supportops:lab` ejecutándose en un pod (`python -m supportops.k8s run` sí se usó localmente).

## Lecturas

Documentación de Helm · README de los charts de OpenTelemetry (Collector y Operator) · README del `tailsamplingprocessor` y del `loadbalancingexporter` · documentación del HPA de Kubernetes · kubeconform.
"""


def build_readme() -> None:
    (MODDIR / "README.md").write_text(README_19, encoding="utf-8")
    print("OK README 19")


if __name__ == "__main__":
    if "--record" in sys.argv:
        record()
    else:
        build_k8s_files()
        build_dashboard()
        build_readme()
        build_lesson()
        build_project()
