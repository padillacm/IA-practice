# Progreso: autor-06-08
Agente: Autor A3 · Módulos: 06–08
- [ ] 06_autoinstrumentacion  (infra lista; falta build_06.py -> README + lección + proyecto)
- [ ] 07_tempo_traceql
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
