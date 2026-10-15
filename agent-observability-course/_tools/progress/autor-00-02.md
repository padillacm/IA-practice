# Progreso: autor-00-02
Agente: Autor A1 · Módulos: 00–02
- [x] Infraestructura compartida: stack/ (Compose + configs verificados con Docker real), supportops/ (agente, mock, tools, tráfico, fallos, check_stack, backends, viz, datos pregrabados, 20 tests), pyproject.toml, _tools/INTERFACES.md
- [ ] 00_entorno (build_00.py → README + lección + proyecto)
- [ ] 01_agente_base
- [ ] 02_tres_pilares
- [ ] check_course.py OK + informe final

## Notas para retomar
- Docker: `dockerd` no corre por defecto en el sandbox; se arranca con `nohup dockerd &` (funciona, pulls OK; Docker Hub puede dar 429: reintentar).
- Verificado: versiones (Tempo 3.1.0, Loki 3.7.8, Grafana 13.2.4, Prometheus v3.15.0, Pyroscope 2.1.2, Collector contrib 0.162.0); Collector usa exporters `otlp_grpc`/`otlp_http`; Grafana 13 solo admite anónimo Viewer (se usa admin/admin).
- GenAI semconv se movió a open-telemetry/semantic-conventions-genai (docs/gen-ai/*.md en ese repo; raw.githubusercontent.com SÍ es accesible, grafana.com NO desde el sandbox).
- Notebooks: ejecutar builders desde la raíz del repo: `python agent-observability-course/_tools/builders/build_00.py`.
