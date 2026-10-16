# Módulo 19 · Kubernetes + Helm para la plataforma de observabilidad

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
