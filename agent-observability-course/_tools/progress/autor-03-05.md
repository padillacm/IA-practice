# Progreso: autor-03-05
Agente: Autor A2 · Módulos: 03–05
- [x] ENTREGABLE 0: supportops/telemetry.py + tests/test_telemetry.py + sección 4 de INTERFACES.md (probado con stack real) 
- [x] 03_otel_sdk_python (lección 25 cód./47 md, proyecto 11/20; nbclient OK en modo degradado; pendiente comprobación con stack vivo: `flock /tmp/obs-stack.lock bash <scratchpad>/a2/live_nb.sh 03_otel_sdk_python <nbs>`)
- [x] 04_genai_semconv (lección 21 cód./40 md, proyecto 18/22; snapshot JSON de la spec; nbclient OK, no necesita stack)
- [x] 05_collector (lección 19 cód./43 md, proyecto 11/14; Docker real + modo sin Docker OK; solución del proyecto verificada con validate + funcional + extremo a extremo)
- [ ] check_course.py OK + informe final

## Notas para retomar
- Spec GenAI clonada (efímero) en el scratchpad: `git clone --depth 1 https://github.com/open-telemetry/semantic-conventions-genai` (raw.githubusercontent y github.com funcionan; la API de GitHub no). Estado: TODO "Development"; metricas nuevas `gen_ai.client.inference.*` (antes `gen_ai.client.token.usage`); `gen_ai.provider.name` (no `gen_ai.system`); `gen_ai.usage.cache_write.input_tokens` (no cache_creation); invoke_agent INTERNAL no define provider.name; finish reason enum de output messages: stop|length|content_filter|tool_call|compaction|error. Contenido (`gen_ai.input.messages` etc.) Opt-In, JSON string en spans; env `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` solo citado como ejemplo.
- A4 (autor-09-10) crea supportops/otel_metrics.py; compone con OTelInstrumentor(emit_metrics=False). Ya se le respondió.
- pyproject.toml: extra `otel` subido a >=1.39 (Logger.emit con kwargs).
- Stack real probado con flock /tmp/obs-stack.lock y bajado con `down -v`.
- Scripts de trabajo en el scratchpad (`.../scratchpad/a2/`: runnb.py, dumpnb.py, live_nb.sh, snap.py): el scratchpad es COMPARTIDO con otros agentes, usa siempre la subcarpeta a2/.
- Hallazgos clave 04: W3C Trace Context Level 2 (flag 0x02 random-trace-id → traceparent '-03' en el SDK reciente); paquete semconv de Python va atrasado (12 nombres obsoletos y 31 nuevos frente a la spec); repo oficial de instrumentaciones: github.com/open-telemetry/opentelemetry-python-genai (util-genai 1.2b0, openai-v2 de contrib obsoleto); Datadog soporta GenAI semconv v1.37+.
- Docker: tras el reinicio hubo que arrancar `dockerd` (nohup dockerd &). Las imágenes seguían descargadas.
- Siguiente: 05_collector (build_05.py; validar config con `otelcol validate` usando la imagen otel/opentelemetry-collector-contrib:0.162.0).
- 03: ejecución con stack vivo pendiente de repetir cuando el candado esté libre (el stack lo tenía otro autor; los resultados de 03 en modo degradado y los de 05 con stack real (lectura) fueron OK).
- 05: Collectors de laboratorio con puertos aleatorios (no necesitan el candado); `lab_results_recorded.json` se regenera con RECORD_LAB=1.
