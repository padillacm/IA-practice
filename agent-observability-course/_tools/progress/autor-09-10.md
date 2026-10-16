# Progreso: autor-09-10
Agente: Autor A4 · Módulos: 09–10
- [x] Investigación 09 (spec GenAI metrics en semantic-conventions-genai, Prometheus 3.15 docs, spec OTel Prometheus compat, Mimir docs) y experimentos con el stack real
- [x] supportops/otel_metrics.py (MetricsInstrumentor, PriceTable, run_live, prom_*), supportops/dashkit.py (dashboards como código)
- [x] 09_metricas: build_09.py -> README + lección (104 celdas: 68 md + 36 código) + proyecto (34 celdas: 19 md + 15 código); ejecutadas con nbclient en modo COMPLETO (stack real) y DEGRADADO: 0 errores; rúbrica OK; dashboard 09-genai-metrics.json con capturas
- [~] 10_grafana (ejecutado con stack real: lección 0 errores, alertas Pending->Firing verificadas, capturas en img/; falta solo re-ejecución final del proyecto en vivo si hay tiempo): build_10.py + README + lección (71 celdas) + proyecto (35) + dashboard 10-salud-del-agente.json + alertas provisionadas YA ESCRITOS y validados en modo degradado (commit WIP 9882e29). FALTA: ejecutar con stack real (candado ocupado por A3/módulo 07; hold.sh en cola), depurar celdas LIVE (ds/query, alertas, correlaciones), capturas Playwright a 10_grafana/img/ (10_salud_incidente.png, 10_explore_traza.png), ejecutar notebooks y commit final
- [ ] INTERFACES.md (mi sección), check_course.py OK + informe final

## Notas para retomar
- Hallazgos verificados en vivo (Prometheus v3.15.0, Collector 0.162, Grafana 13.2.4): ver notas en lección 09.
  * Collector prometheus exporter: histogramas exponenciales -> solo bucket +Inf (se pierde la distribución). Delta se acumula en el exporter; Prometheus OTLP receiver RECHAZA delta (HTTP 500 "invalid temporality and type combination").
  * Prometheus OTLP directo (:9090/api/v1/otlp/v1/metrics) guarda histogramas exponenciales como nativos sin flags.
  * Python SDK 1.45.1 NO tiene cardinality limit (spec: default 2000 + otel.metric.overflow).
  * Unidad USD -> sufijo _USD en el nombre; unidad "1" en gauge -> _ratio; {x} se descarta.
  * Exemplars solo si hay tráfico en el último intervalo de export; rate(x[15s]) con scrape 15s -> vacío.
  * A2: usar OTelInstrumentor(tel, emit_metrics=False) + MetricsInstrumentor(tel) en CompositeInstrumentor (el de A2 primero).
- Lock: patrón en scratchpad hold.sh (flock en background, /tmp/a4.hold). Stack bajado y lock liberado al terminar cada sesión de pruebas.

- Scripts de apoyo (scratchpad a4/): runnb.py (nbclient), shot.js/explore.js/linktest.js (Playwright node, chromium en /opt/pw-browsers), exp10.py (comprobaciones de la API de Grafana), hold.sh (candado). Para forzar degradado: STACK_HOST=nonexistent.invalid.
- A3 avisa: Tempo ignora spans antiguos; levantar con TEMPO_CONFIG=tempo-metrics.yaml si se quieren span metrics.
