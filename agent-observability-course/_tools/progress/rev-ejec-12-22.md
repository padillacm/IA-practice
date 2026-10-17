# Progreso: rev-ejec-12-22
Agente: Revisor de ejecutabilidad E2 · Módulos: 12–22 · Informe: agent-observability-course/_tools/REVISION_EJECUTABILIDAD_2.md
- [ ] 12_mcp_tools
- [ ] 13_costes_finops
- [ ] 14_evaluacion_online
- [ ] 15_calidad_regresion
- [ ] 16_slos_alertas_incidentes
- [ ] 17_profiling_pyroscope
- [ ] 18_escala_muestreo_coste
- [ ] 19_kubernetes_helm
- [ ] 20_privacidad_seguridad
- [ ] 21_elite_playbook
- [ ] 22_capstone
- [ ] check_course.py OK + informe final

## Notas para retomar
- (qué archivo/celda, comandos largos lanzados y su resultado)
- venv limpio en scratchpad (`pip install -e ".[viz,otel,mcp,nb,dev]" ipykernel nbclient`), runner `run_nb.py` (nbclient, allow_errors, kernel del venv, cwd = carpeta del notebook). Sin stack (daemon Docker arriba, sin stack): 22 notebooks de 12-22 sin errores salvo 20/21 (`DataFrame.style` exigía jinja2 → añadido a extras `viz` y `nb` de pyproject) - repetido OK.
- 18 en vivo x3 (antes: 3/3 sin None ni fallo; RSS de la tormenta varía ±10 MB) + endurecido (`_host_port`, `_docker_run`, readiness OTLP real, reintentos) y x3 de nuevo OK; rúbrica 18 9/9 idéntica 6/6 veces. 20: umbral R1 recall 0.86→0.85.
- 19 en vivo x3 (COURSE_CHARTS_DIR=/tmp/claude-0/charts, helm 4.3.1, kubeconform, k3s API server): 3/3 sin errores, rúbrica 8/8; sin helm/Docker (HELM/DOCKER_HOST falsos) → degradado 4/4 con 4 omitidas y aviso. Corregido: R9 de 18 contaba "sin Docker" como ❌ (bool(None)); R7 de 19 ya no afirma API server real sin Docker. k8s.py usa los mismos helpers de puertos que sampling.py.
- Stack real (core+metrics, bajo flock) 12-16: lección+proyecto sin errores (45/36/65/85/184 s lecciones), rúbricas 6-7/6-7. Regenerados 12-22 con la celda de instalación nueva (_a1_common).
