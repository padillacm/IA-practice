# Progreso: rev-pedagogico-16-22
Agente: Revisor pedagógico P3 · Módulos: 16–22 + GUIA_DE_ESTUDIO.md · Informe: agent-observability-course/_tools/REVISION_PEDAGOGICA_3.md
- [x] 16_slos_alertas_incidentes
- [x] 17_profiling_pyroscope
- [x] 18_escala_muestreo_coste
- [x] 19_kubernetes_helm
- [ ] 20_privacidad_seguridad
- [ ] 21_elite_playbook
- [ ] 22_capstone
- [ ] GUIA_DE_ESTUDIO.md (ruta, tiempos, mapa mermaid, glosario ES/EN; tras leer los informes P1 y P2)
- [ ] check_course.py OK + informe final

## Notas para retomar
- Helpers en /tmp/claude-0/s (ph.py rep(n,old,new), commit.sh). Cambios 16: nivel 🟠, ejemplo resuelto §2, 🔁 +Módulo 09, pistas 1/2 en TODO 1,3,4a,5,6. Solo md cambiado (sin re-ejecutar).
- Hallazgos para informe: ver REVISION_PEDAGOGICA_3.md (se escribe al final; apuntar aquí cada hallazgo).
- 17: prereq +13, intuición ML (muestreo=accuracy en test), protobuf glosado, 🔁 +2 (13 y 16). Proyecto ya bien andamiado, sin cambios.
- 18: 🧭 header vs caja incoherentes -> unificado (núcleo §1-8,§12); ejemplo resuelto 1/π en §7; 🔁 +Q16; predicción previa en Paso 6 (TODO trivial, doc: wrapper de collector_config).
- 19: GRAN HALLAZGO: no se enseñaba Kubernetes (alumno parte de cero) -> añadida §0 'Kubernetes mínimo' (tabla Compose->K8s, manifiesto anotado, Helm~Jinja/Hydra); 🧭 header vs caja unificado; prereq 00 y sin 17; 🔁 +Q módulo 00.
