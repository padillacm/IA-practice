# Progreso: autor-17-19
Agente: Autor A7 · Módulos: 17–19
- [x] 17_profiling_pyroscope (lección 44md+23code, proyecto 14md+13code; ejecutados con nbclient y Pyroscope real: OK; rúbrica 9/9)
- [x] 18_escala_muestreo_coste (lección 37md+21code, proyecto 15md+14code; ejecutados con nbclient + Docker real: OK; rúbrica 9/9)
- [ ] 19_kubernetes_helm
- [ ] check_course.py OK + informe final

## Notas para retomar
- (qué archivo/celda, decisiones tomadas, comandos largos lanzados y su resultado)

- 17: probado con Pyroscope 2.1.2 real, SDK pyroscope-io 1.3.0, pyroscope-otel 1.1.0, Tempo/Collector reales. Kernel de pruebas: /root/venv17 (system-site-packages + pyroscope-io). Runner: /tmp/claude-0/runnb.py. Candado del stack lo mantiene /root/lockhold.sh (borrar /root/lock.release lo libera al crear el archivo; luego `docker compose --profile all down -v`).
- Herramientas K8s descargadas en /root/bin (helm 4.3.1 vía imagen alpine/helm, kind 0.30.0, k3d 5.8.3, kubectl 1.34, kubeconform 0.7.0). Charts fuente en /root/src (github.io y blobs OCI de ghcr están bloqueados; usar git clone). Versiones: otel collector chart 0.176.0 (app 0.162.0), operator chart 0.126.0 (app 0.161.0), grafana-community: grafana 14.0.0 (13.2.4), loki 18.16.0 (3.7.8), tempo 3.2.0 (3.1.0); pyroscope chart en grafana/pyroscope operations/pyroscope/helm (2.4.0).
- 18: probado con Collector contrib 0.162.0, Loki 3.7.8, Tempo 3.1.0 y Prometheus v3.15 reales (contenedores efímeros). Hallazgos en INTERFACES. tail_sampling claves reales en /root/src/tsp_README.md.
