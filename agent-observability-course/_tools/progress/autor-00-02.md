# Progreso: autor-00-02
Agente: Autor A1 · Módulos: 00–02
- [x] Infraestructura compartida: stack/ (Compose + configs verificados con Docker real), supportops/ (agente, mock, tools, tráfico, fallos, check_stack, backends, viz, datos pregrabados, 20 tests), pyproject.toml, _tools/INTERFACES.md
- [x] 00_entorno (build_00.py → README + lección 44md+22code, 10 gráficos; proyecto 19md+10code; ejecutado con nbclient online y degradado: 0 errores)
- [x] 01_agente_base (lección 48md+27code, 12 gráficos; proyecto 19md+10code; ejecutados con nbclient 0 errores; solución calibrada: R3 8/8, R4 150/150, R5 3/3, R6 prec/recall 1.00)
- [x] 02_tres_pilares (lección 46md+18code, 11 gráficos; proyecto 18md+13code: 10 incidentes, rúbrica con verdad en base64, estable en 6 semillas)
- [x] check_course.py OK (Todo OK) · pendiente solo: informe final (SubagentHandback)

## Notas para retomar
- Docker: `dockerd` no corre por defecto en el sandbox; se arranca con `nohup dockerd &` (funciona, pulls OK; Docker Hub puede dar 429: reintentar).
- Verificado: versiones (Tempo 3.1.0, Loki 3.7.8, Grafana 13.2.4, Prometheus v3.15.0, Pyroscope 2.1.2, Collector contrib 0.162.0); Collector usa exporters `otlp_grpc`/`otlp_http`; Grafana 13 solo admite anónimo Viewer (se usa admin/admin).
- GenAI semconv se movió a open-telemetry/semantic-conventions-genai (docs/gen-ai/*.md en ese repo; raw.githubusercontent.com SÍ es accesible, grafana.com NO desde el sandbox).
- Notebooks: ejecutar builders desde la raíz del repo: `python agent-observability-course/_tools/builders/build_00.py`.
