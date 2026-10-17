# stack/ · laboratorio de observabilidad (Docker Compose)

```bash
cd agent-observability-course/stack
docker compose --profile core up -d                      # Collector + Tempo + Loki + Grafana
docker compose --profile core --profile metrics up -d    # + Prometheus
docker compose --profile profiling up -d                 # + Pyroscope
docker compose --profile all ps                          # estado
docker compose down                                      # parar (conserva datos); `down -v` borra volúmenes
```

Grafana: <http://localhost:3000> (usuario `admin`, contraseña `admin`; solo laboratorio).
Puertos, versiones, perfiles y convenciones: `../_tools/INTERFACES.md`.

| Carpeta | Contenido |
|---|---|
| `otel-collector/config.yaml` | pipelines OTLP → Tempo (trazas), Loki (logs), Prometheus (métricas) |
| `tempo/` | `tempo.yaml` (monolítico, Tempo 3.x) y `tempo-metrics.yaml` (+ metrics-generator, módulo 07) |
| `loki/loki.yaml` | Loki monolítico con OTLP nativo y structured metadata |
| `prometheus/prometheus.yml` | scrapes del Collector, Tempo y Loki |
| `grafana/provisioning/` | datasources (uids `tempo`, `loki`, `prometheus`, `pyroscope`) y proveedor de dashboards |
| `grafana/dashboards/` | dashboards como código (`00-stack-overview.json`) |
