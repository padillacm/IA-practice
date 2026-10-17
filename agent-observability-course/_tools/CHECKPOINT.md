# CHECKPOINT · estado final del curso

Rama `claude/agent-observability-course` · curso en `agent-observability-course/` · stack: Collector 0.162.0, Tempo 3.1.0,
Loki 3.7.8, Prometheus 3.15.0, Grafana 13.2.4, Pyroscope 2.1.2.

## Estado
- **23 módulos (00–22)**, cada uno con README, lección y proyecto (46 notebooks), más `GUIA_DE_ESTUDIO.md`,
  `extras/ENTREVISTAS_SYSTEM_DESIGN.md`, `extras/RUTA_DE_CARRERA.md` y `21_elite_playbook/COMPENDIO_SECRETOS.md` (74 secretos).
- `python agent-observability-course/_tools/check_course.py` → **Todo OK**.
- `pytest agent-observability-course/supportops/tests` → 173 pasan, 3 se saltan (helm/charts/Pyroscope no disponibles); el
  test de charts de Tempo se salta si no hay repositorio Helm.
- Revisiones hechas, con informe en `_tools/`: técnica (×3), referencias + élite (×2), ejecutabilidad (×2), pedagógica (×3).
- Horas reales estimadas: ≈ 118 h (ruta núcleo ≈ 60 h) frente a ≈ 100 h anunciadas; ver la guía de estudio.

## Pendiente de validar (no se pudo probar en el entorno de construcción)
- **Kubernetes (módulo 19):** ningún pod se ejecutó en un clúster (kind y k3s fallan con `runc` en el sandbox). Verificados:
  `helm lint/template`, kubeconform, `helm install` y `--dry-run=server` contra un API server k3s. Sin verificar: planificación,
  sondas, `hostPort`, HPA con métricas, OpenTelemetry Operator en marcha, inyección de auto-instrumentación, tráfico agente→gateway real.
- **Proveedores LLM reales** (Anthropic, OpenAI, Ollama): solo con clientes falsos; todo el curso usa el `mock` determinista. Los
  precios son ilustrativos y configurables.
- **Grafana en navegador:** el nodeGraph del dashboard 07, el botón «Profiles for this span» (17), el clic sobre `traceID`
  y el renderizado visual de los dashboards 14–22.
- **Colab, Windows, macOS, arm64** y equipos con menos de 8 GB de RAM; `FAST_DEV_RUN=False`.
- **Referencias no confirmables** (marcadas en el texto): examen «Certified Grafana Associate», OWASP, triángulo de Davidovič,
  RGPD/WP29, capítulos del SRE Book citados de memoria, multiplicadores de caché de Anthropic y que `temperature=0` no sea
  determinista (fuentes secundarias), versión del Collector con soporte de perfiles. Dominios bloqueados en el sandbox:
  grafana.com, opentelemetry.io, sre.google, arxiv.org (se verificó por repos de GitHub y búsqueda).
- **Mimir:** solo documentado; no hay imagen en el stack.
- **Horas:** estimaciones por nº de celdas, no mediciones con alumnos.

## Recomendaciones abiertas (ver informes)
- Partir en dos cuadernos los módulos más largos: 03 (`contextvars`), 09 (~104 celdas), 11 (~90), 20 y 21.
- El TODO 1 del proyecto 05 (todo el YAML del Collector) y los 7 TODOs del proyecto 14 en 1 h 45 min son densos.
- Provisionar la alerta de desvío de FinOps (13) en lugar de crearla por API; revisar la consulta de calidad post-estratificada del dashboard 14.
- `values/loki.yaml` del módulo 19 fija `retention_period` sin activar la retención del compactor.
- Regenerar los datos pregrabados `sample_data` si se quiere un ejemplo limpio de GenAI semconv (el módulo 04 los usa como ejemplo «sucio»).
- La instantánea de la spec GenAI (módulo 04) caduca rápido (estado *Development*): revisar al actualizar versiones.

## Notas para quien continúe
- Los `.ipynb` se generan siempre desde `_tools/builders/build_NN.py`; nunca se editan a mano. Utilidades comunes en `builders/_a1_common.py`.
- Un solo daemon de Docker y puertos fijos: usa `flock /tmp/obs-stack.lock` para las ejecuciones con stack y bájalo con `down -v`.
- Los badges de Colab apuntan a `master` y funcionarán tras el merge; solo sirven para partes sin Docker.
