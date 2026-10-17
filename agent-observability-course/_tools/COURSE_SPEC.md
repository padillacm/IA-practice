# COURSE_SPEC · Observabilidad de agentes de IA en producción (OpenTelemetry · Grafana · Loki · Tempo)

## Criterios de éxito (palabras literales del usuario)
- "Crear un curso de monitoreo de agentes en producción con el stack opentelemetry, grafana, loki, tempo".
- Nivel final: "Experto de empresa top".
- Para qué: "Trabajo actual" y "Emprender / producto propio".
- Enfoque: "Equilibrado, hands-on" (30 % conceptos · 50 % implementación con el stack real · 20 % operación y casos de fallo).
- Élite: "Sección por módulo y módulo propio".
- Estado del arte: "Hasta lo publicado este año" (marcando qué es experimental/inestable).
- Formato: "Notebooks Colab + stack docker-compose" · cómputo: "Mi máquina con Docker" · duración "~100 h, 16+ módulos".
- LLM de los labs: "Agnóstico de proveedor".
- Profundizar: "Calidad y evaluación online (13)", "Multi-agente y MCP (11)" y "el que creas que puede aportarme más profesionalmente" (→ escala, muestreo y coste del propio stack).
- Añadir: "Profiling continuo (Pyroscope)" y "Kubernetes + Helm".
- Stack: "Solo lo pedido + opcionales" (OTel, Grafana, Loki, Tempo como núcleo; Prometheus/Mimir y OpenLIT/OpenLLMetry como apoyo).
- Proyectos: "Hilo: «SupportOps» — soporte con agentes", "Generador de tráfico sintético propio", "Plantilla con TODOs + pistas graduadas + solución oculta".
- Extras: "Capstone final", "Guía de entrevistas / system design", "Ruta de carrera / certificaciones".
- Revisores: "Técnico, Ejecutabilidad, Pedagógico, Verificador de referencias + Élite", "Por bloque", "Pueden reestructurar secciones".

## Alumno
- Domina: Python sólido.
- Del tema sabe: nada del stack (OTel, Grafana, Loki, Tempo); tampoco ha usado agentes LLM, Docker/Compose ni observabilidad. Todo se explica desde cero y se introduce lo justo de Docker y de agentes.
- Analogías a usar: ciencia de datos/ML (evaluación de modelos, drift, offline vs online), backend/microservicios (latencia, errores, tracing distribuido, SLOs) y DevOps/SRE (alertas, on-call, incident response, runbooks).
- Idioma: español con términos técnicos en inglés (span, trace, tool call, tail sampling…).

## Objetivo
- Nivel final: experto de empresa top (referentes: Grafana Labs, Honeycomb, Datadog, Netflix, Uber; usar solo fuentes verificables).
- Para qué: trabajo actual (agentes en producción que monitorear) y producto propio (observabilidad barata y seria).
- Peso: conceptos 30 % · implementación con el stack real 50 % · operación y casos de fallo 20 %.

## Formato y recursos
- Formato: notebooks (lección + proyecto por módulo) Jupyter-first, ejecutados con el kernel local junto al stack `docker-compose` del curso. Badges de Colab solo útiles para las partes conceptuales o con LLM simulado y sin Docker (cada notebook lo indica).
- Cómputo: máquina local con Docker (8 GB de RAM libres recomendados); sin GPU. Kubernetes (módulo 19) con kind/k3d local.
- Duración: ~100 h · ritmo libre · nº de módulos: 23 (00–22) + documentos extra.
- Gráficos: ≥ 6 por lección (diagramas dibujados en código, capturas de paneles descritas o generadas, gráficos de trazas/latencias/costes).

## Contenido
- Alcance: observabilidad de agentes LLM con OTel (GenAI semantic conventions), Collector, Tempo/TraceQL, Loki/LogQL, métricas (Prometheus/Mimir), Grafana, evaluación online, SLOs, coste, escala, K8s, profiling, privacidad. Estado del arte hasta 2026, marcando lo experimental.
- Fuera de alcance: entrenar o evaluar modelos offline en profundidad; frameworks de agentes más allá de lo necesario para ilustrar la instrumentación; plataformas SaaS de observabilidad (solo comparaciones breves).
- Stack obligatorio: OpenTelemetry (SDK Python + Collector), Grafana, Loki, Tempo. Apoyo: Prometheus/Mimir, Pyroscope, OpenLIT/OpenLLMetry, Helm/kind.
- Ciclo de vida/producción: sí (SLOs, alertas, incidentes, costes, escala, calidad online, privacidad).
- Contenido de élite: sección 🧠 por módulo + módulo propio (21) + compendio.

## Proyectos y evaluación
- Hilo conductor: «SupportOps» — empresa ficticia de soporte con agentes; el agente crece módulo a módulo y el alumno añade observabilidad en cada uno.
- Datasets: ninguno externo; **generador de tráfico sintético propio** con inyección de fallos (latencia, errores, alucinaciones, bucles de herramientas), semillas fijas y esquema documentado. Sin descargas ni licencias.
- LLM de los labs: capa agnóstica (`LLM_PROVIDER=mock|anthropic|openai|ollama`); el modo `mock` determinista es el valor por defecto y el que usan las rúbricas.
- Capstone: plataforma de observabilidad completa para SupportOps multi-agente + checklist de producción · Guía de entrevistas/system design: sí · Ruta de carrera/certificaciones: sí.

## Agentes
- Autores: A1 (00–02, oleada 0) · A2 (03–05), A3 (06–08), A4 (09–10), A5 (11–13) en paralelo (oleada 1) · A6 (14–16), A7 (17–19), A8 (20–22 + extras) (oleada 2).
- Revisores: Técnico, Ejecutabilidad, Pedagógico, Verificador de referencias + Élite; por bloque; pueden reestructurar secciones (los cambios grandes se documentan en `_tools/`).

## Repositorio
- Ruta del curso: `agent-observability-course/` · Rama: `claude/agent-observability-course` · Repo para badges: `padillacm/IA-practice` (rama por defecto `master`).
