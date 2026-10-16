# Progreso: rev-refs-elite-00-10
Agente: Verificador de referencias + Élite V1 · Módulos: 00–10 · Informe: agent-observability-course/_tools/REVISION_REFERENCIAS_1.md
- [x] 00_entorno
- [x] 01_agente_base
- [x] 02_tres_pilares
- [x] 03_otel_sdk_python
- [x] 04_genai_semconv
- [ ] 05_collector
- [ ] 06_autoinstrumentacion
- [ ] 07_tempo_traceql
- [ ] 08_loki_logql
- [ ] 09_metricas
- [ ] 10_grafana
- [ ] check_course.py OK + informe final

## Notas para retomar
- (qué archivo/celda, decisiones tomadas)

- 00: refs OK (Honeycomb x2 y OTel blog confirmados por búsqueda; Tempo v3.0 notes y docker-otel-lgtm leídos en GitHub; Sculley OK). Élite +2 (memory_limiter matices, lgtm no-prod) +1 ref. Quitado «el sitio avisa de desfasado» (no verificable).
- Método: URLs github -> raw.githubusercontent / gh api (repos no habilitados dan 403 en gh api; usar raw README). Script commit: /tmp/claude-0/commit.sh NN msg
- 01: arXiv x3 y docs Anthropic confirmados por búsqueda; élite +2 (+celda coste cuadrático). Caché 0,1x/1,25x marcada secundaria.
- 02: Dapper (autores/año/TR) OK, RED OK, ISBN OK, spec Ok-final verificada en trace/api.md. Élite +1 (#10 muestreo, celda medible), +cita Prometheus, +Tempo3 multiplier.
- 03: Honeycomb distro archivada verificada (búsqueda); pre-fork/service.instance.id verificados en repo opentelemetry.io (raw); spec BSP defaults OK. Corregido: pre-fork afecta a métricas (PeriodicExportingMetricReader), no BSP. Élite +1 (#9 overhead medido).
- 04: Datadog blog (1-dic-2025, v1.37+) verificado por búsqueda; OTel blog autores Liu(IBM)/Solomon(Google) 2025-03-06 verificado en repo opentelemetry.io (corregido ref en 00); python-genai/contrib README leídos; élite +1 (#9 buckets, celda medida). Aviso openai-v2 reformulado.
