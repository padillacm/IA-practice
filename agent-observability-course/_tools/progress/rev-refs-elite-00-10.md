# Progreso: rev-refs-elite-00-10
Agente: Verificador de referencias + Élite V1 · Módulos: 00–10 · Informe: agent-observability-course/_tools/REVISION_REFERENCIAS_1.md
- [x] 00_entorno
- [x] 01_agente_base
- [x] 02_tres_pilares
- [x] 03_otel_sdk_python
- [x] 04_genai_semconv
- [x] 05_collector
- [x] 06_autoinstrumentacion
- [x] 07_tempo_traceql
- [x] 08_loki_logql
- [x] 09_metricas
- [x] 10_grafana
- [x] check_course.py OK + informe final

## Notas para retomar
- (qué archivo/celda, decisiones tomadas)

- 00: refs OK (Honeycomb x2 y OTel blog confirmados por búsqueda; Tempo v3.0 notes y docker-otel-lgtm leídos en GitHub; Sculley OK). Élite +2 (memory_limiter matices, lgtm no-prod) +1 ref. Quitado «el sitio avisa de desfasado» (no verificable).
- Método: URLs github -> raw.githubusercontent / gh api (repos no habilitados dan 403 en gh api; usar raw README). Script commit: /tmp/claude-0/commit.sh NN msg
- 01: arXiv x3 y docs Anthropic confirmados por búsqueda; élite +2 (+celda coste cuadrático). Caché 0,1x/1,25x marcada secundaria.
- 02: Dapper (autores/año/TR) OK, RED OK, ISBN OK, spec Ok-final verificada en trace/api.md. Élite +1 (#10 muestreo, celda medible), +cita Prometheus, +Tempo3 multiplier.
- 03: Honeycomb distro archivada verificada (búsqueda); pre-fork/service.instance.id verificados en repo opentelemetry.io (raw); spec BSP defaults OK. Corregido: pre-fork afecta a métricas (PeriodicExportingMetricReader), no BSP. Élite +1 (#9 overhead medido).
- 04: Datadog blog (1-dic-2025, v1.37+) verificado por búsqueda; OTel blog autores Liu(IBM)/Solomon(Google) 2025-03-06 verificado en repo opentelemetry.io (corregido ref en 00); python-genai/contrib README leídos; élite +1 (#9 buckets, celda medida). Aviso openai-v2 reformulado.
- 05: docs Collector (scaling/resiliency/config), READMEs de processor/memory_limiter/exporterhelper/transform/loadbalancing leídos vía raw. Corregido: Alloy 'experimental'->'public preview'; 'guía oficial prefiere sending_queue.batch' suavizado. Élite +2 (#9 error_mode fail-open, #10 LB vs spanmetrics).
- 06: Grafana AI Obs (5 vs 6 dashboards) matizado; openai DEFAULT_MAX_RETRIES=2, OpenLIT/OpenLLMetry defaults de contenido verificados en repos. Hallazgo: bandera OTEL_SEMCONV_STABILITY_OPT_IN eliminada en python-genai (corregido texto de 04 y 06). Élite +2.
- 07: Tempo 3.0 blog (1-jun-2026) por búsqueda; config/CHANGELOG/notas 3.1 verificados en grafana/tempo raw (slack 2m/30s, 168h/24h). Élite +2 (#10 extrapolate 3.1, #11 fail_on_high_lag). build_07 imprime ERR sin stack (normal).
- 08: todas las cifras de Loki (100k streams, 15 labels, 64KB/128, 1w, SSD->4.0, bloom 75TB, helm community) verificadas en grafana/loki raw. Élite +2 (#10 17 atributos OTLP incl. pod/instance.id, #11 multiplicación + streams limit).
- 09: spec cardinality 2000, Prometheus guide (30m OOO), CHANGELOG 3.8/3.9, Mimir flags, Grafana best practices (RED/symptoms) verificados vía raw. Sin correcciones. Élite +1 (#11 p99 clamp +Inf).
- 10: KubeCon/maturity/RED/grafanactl->gcx (archivado 1-jun-2026)/rate_interval/correlations verificados. Élite +2 (stale instances, ventana fija). Corrección URL OpenAI en 01. Informe REVISION_REFERENCIAS_1.md escrito. TODO COMPLETO.
