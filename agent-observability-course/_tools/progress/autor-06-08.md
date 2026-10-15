# Progreso: autor-06-08
Agente: Autor A3 · Módulos: 06–08
- [x] 06_autoinstrumentacion (README + lección 72 celdas + proyecto 33 celdas; ejecutados con nbclient OK; rúbrica 6/6 con la solución)
- [x] 07_tempo_traceql (lección 76 celdas, proyecto 24, dashboard 07; en vivo + degradado OK, rúbrica 6/6; falta solo revisión final)
- [ ] 08_loki_logql
- [ ] check_course.py OK + informe final

## Hecho / decisiones (módulo 06)
- Investigación verificada (oct-2026): OpenLIT 1.45.0, traceloop-sdk/OpenLLMetry 0.62.4, instrumentación oficial OTel `opentelemetry-instrumentation-genai-openai` 1.2b0
  (repo `open-telemetry/opentelemetry-python-genai`; `-openai-v2` está deprecado). Semconv GenAI: repo `open-telemetry/semantic-conventions-genai`, estado Development.
  OpenLIT: captura contenido por defecto, instrumenta httpx (spans POST duplicados), descarga pricing.json de GitHub al init; `@openlit.trace` guarda function.args aunque desactives contenido.
  OpenLLMetry: `TRACELOOP_TRACE_CONTENT` (def. true). Oficial: `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` (def. no_content).
- Creados (sin builders aún): `supportops/openai_compat.py` (servidor falso OpenAI sobre MockLLM + `make_openai_llm`), `supportops/autoinstr_lab.py`
  (variantes en subproceso: manual/openlit/openllmetry/official/hybrid_*/decorated; `run_variant`, `bench_variant`, `build_dataset`),
  `06_autoinstrumentacion/recorded/lab_seed42.json.gz (la carpeta data/ está en .gitignore)` (27 ejecuciones n=24 seed=42; regenerar: `autoinstr_lab.build_dataset(path)` con venv que tenga openai+openlit+traceloop-sdk+genai-openai).
- Venv de pruebas: /tmp/claude-0/.../scratchpad/v06 (puede perderse). Medido: huella (paquetes/MB): base 29/67, openlit 63/141, traceloop 90/111, oficial 34/71.
  Overhead por llamada ≈ +1 ms sobre ~47 ms (servidor falso); init: base 1.0 s, openlit 3.5 s, openllmetry 3.2 s, oficial 1.5 s.
- Plan lección 06 (≥9 gráficos): arquitectura hooks vs patch; parche a mano; cadencia PyPI; estructura de trazas (huérfanas); heatmap de atributos; atribución de fallos;
  privacidad; trampas (doble instr., reintentos, streaming); huella; matriz de decisión + sensibilidad. Proyecto: trace_stats, attr_coverage, failure_attribution,
  pii_exposure, TicketContextProcessor (on_start), matriz+sensibilidad.
## Notas para retomar
- Tras 06: pull, 07 (Tempo; usar stack vivo con candado /tmp/obs-stack.lock), 08 (Loki). telemetry.py de A2 disponible (setup_telemetry/OTelInstrumentor).
- 06 TERMINADO (commit). Comandos: `python agent-observability-course/_tools/builders/build_06.py`; ejecución con kernel `v06` (venv con libs): lección 24 s, proyecto 5 s, 0 errores.
  Regenerar dataset si cambian versiones: `from supportops.autoinstr_lab import build_dataset; build_dataset("06_autoinstrumentacion/recorded/lab_seed42.json.gz")` (~4 min) y revisar cifras de texto (66 trazas, 132/66 spans, 86/59 peticiones, 5 spans con PII).
- Siguiente: 07_tempo_traceql. Plan: stack vivo con candado; Tempo 3.1 con `TEMPO_CONFIG=tempo-metrics.yaml`; lote con fallos inyectados con `generate_tickets(start_s="live")` + `setup_telemetry` + `OTelInstrumentor`.
- 07 TERMINADO (commit). Capturas: `SUPPORTOPS_CAPTURE=1` ejecutando la lección con stack limpio (down -v; up con TEMPO_CONFIG=tempo-metrics.yaml). Mini motor 18/18 vs Tempo 3.1. Hallazgo clave: `live_store.wal.ingestion_time_range_slack` (ver INTERFACES).
- Siguiente: 08_loki_logql. `supportops/loki_lab.py` ya escrito y probado con servidor falso; falta builder (build_08.py), ejecutar en vivo (pedir candado con `flock -n`, down -v al acabar), capturas `08_loki_logql/recorded/`, dashboard 08-*.json, proyecto. Loki docs clonadas en scratchpad (repos/loki/docs/sources) — re-clonar con `git clone --depth 1 --filter=blob:none --sparse https://github.com/grafana/loki.git` si se pierde.
