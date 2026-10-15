# Progreso: autor-03-05
Agente: Autor A2 · Módulos: 03–05
- [x] ENTREGABLE 0: supportops/telemetry.py + tests/test_telemetry.py + sección 4 de INTERFACES.md (probado con stack real) 
- [ ] 03_otel_sdk_python
- [ ] 04_genai_semconv
- [ ] 05_collector
- [ ] check_course.py OK + informe final

## Notas para retomar
- Spec GenAI clonada (efímero) en el scratchpad: `git clone --depth 1 https://github.com/open-telemetry/semantic-conventions-genai` (raw.githubusercontent y github.com funcionan; la API de GitHub no). Estado: TODO "Development"; metricas nuevas `gen_ai.client.inference.*` (antes `gen_ai.client.token.usage`); `gen_ai.provider.name` (no `gen_ai.system`); `gen_ai.usage.cache_write.input_tokens` (no cache_creation); invoke_agent INTERNAL no define provider.name; finish reason enum de output messages: stop|length|content_filter|tool_call|compaction|error. Contenido (`gen_ai.input.messages` etc.) Opt-In, JSON string en spans; env `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` solo citado como ejemplo.
- A4 (autor-09-10) crea supportops/otel_metrics.py; compone con OTelInstrumentor(emit_metrics=False). Ya se le respondió.
- pyproject.toml: extra `otel` subido a >=1.39 (Logger.emit con kwargs).
- Stack real probado con flock /tmp/obs-stack.lock y bajado con `down -v`.
