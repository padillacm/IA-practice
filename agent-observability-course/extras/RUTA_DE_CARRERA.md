# Ruta de carrera: observabilidad de agentes de IA (AI platform · SRE de IA · observability engineering)

Documento extra del curso «Observabilidad de agentes de IA en producción (OpenTelemetry · Grafana · Loki · Tempo)». Conecta lo que has construido (módulos 00-22) con **roles**, **señales de nivel**, **certificaciones** y **comunidad**.

> **Honestidad sobre las fuentes (consultado el 16-oct-2026).** Cada certificación, enlace o evento lleva una marca de verificación:
> **✅ confirmado** = lo encontré en una búsqueda web con resultado de la propia organización o de un medio fiable; **🟡 existe, detalles por confirmar** = confirmado que existe pero precios, temario o fechas varían según la fuente (compruébalo en la página oficial); **❔ no confirmado desde el sandbox** = el sandbox del curso no pudo abrir el sitio ni verlo en búsquedas: es conocimiento general, verifícalo tú.
> Este documento **no** contiene datos de salarios ni de oferta de empleo: los mercados cambian y no tengo una fuente verificable. Las descripciones de los roles son **orientativas**: los títulos varían entre empresas.

---

## 1 · Los tres roles (y uno vecino)

| | **AI platform engineer** | **SRE de IA / de plataformas de ML** | **Observability engineer** | *(vecino)* **LLMOps / evaluation engineer** |
|---|---|---|---|---|
| **Misión** | Construir la plataforma sobre la que otros equipos despliegan agentes: gateway de modelos, herramientas, evaluación, límites, coste | Que los sistemas con agentes cumplan sus SLOs y se recuperen rápido: guardia, incidentes, capacidad, cambios | Construir y operar la telemetría: instrumentación, Collector, backends, SLOs, coste del propio stack | Medir y mejorar la calidad: datasets de oro, jueces, regresiones, canarios |
| **Trabajo típico** | Gateway LLM con presupuestos, enrutado y reintentos; servidores MCP seguros; plantillas de despliegue; multi-tenancy | Burn rate y alertas, runbooks, postmortems, game days, `LoopGuard` y disyuntores, planificación de capacidad | OTel SDK/Collector, convenciones GenAI, tail sampling, cardinalidad, retención, dashboards como código | Evaluación online, sesgos del juez, compuertas de despliegue, análisis de errores |
| **Módulos del curso** | 01, 11, 12, 13, 19, 22 | 09, 10, 13, 16, 18, 21, 22 | 02-10, 17, 18, 19, 20, 22 | 14, 15, 16, 21 |
| **Señal de dominio** | Diseña límites y presupuestos que evitan incidentes de coste | Reduce TTD/TTR con datos y reduce la fatiga de alertas | Una traza por ticket, sin PII, con coste previsible | Estimaciones con intervalo y compuertas que no dan falsos positivos |
| **Artefacto de portafolio** | Capstone (módulo 22) con revisión de arquitectura | Mesa de incidentes superada y postmortems (21, 16) | Gateway del Collector validado + contratos de telemetría (05, 20, 22) | Dataset de oro desde trazas + compuerta apareada (15) |

**Qué comparten:** pensar en **señales** (¿qué dato prueba esto?), **coste** (series, bytes, tokens), **privacidad** (qué NO capturar) y **método** (bucle de análisis, mitigar antes que resolver).

## 2 · Señales de nivel (de junior a staff)

| Nivel | Qué se espera | Cómo se demuestra con material de este curso |
|---|---|---|
| **Junior** | Instrumenta con el SDK, lee trazas/logs/métricas y arma un dashboard con ayuda | Módulos 03-10: instrumentar SupportOps y un dashboard provisionado como código |
| **Semi-senior** | Diagnostica incidentes sencillos solo con telemetría; define SLIs y alertas | Módulo 16 (SLO + burn rate) y 3 de 5 incidentes de la mesa |
| **Senior** | Diseña pipelines (Collector, muestreo, retención) con coste y privacidad; lidera incidentes | Módulos 18-20 y mesa de incidentes completa < 15 min por caso; diseño 1 de la guía de entrevistas |
| **Staff / principal** | Define la **estrategia**: contratos de telemetría, cultura, coste como SLO, revisión de arquitecturas de otros equipos; influye sin autoridad | Capstone (22) + checklist con lo manual resuelto + compendio de secretos aplicado a revisiones; diseño 3 (multi-tenant) |

**Anti-señales** que un entrevistador senior detecta rápido: listar herramientas sin criterio, dashboards sin pregunta ni acción asociada, capturar prompts «por si acaso», alertar por causas internas, no saber el coste de lo que operas, y no declarar lo que NO se ha verificado.

## 3 · Plan de 90 días (con el curso como base)

| Semanas | Objetivo | Entregable |
|---|---|---|
| 1-3 | Instrumentar y observar un agente real (el tuyo o uno de ejemplo) con OTel → Collector → Tempo/Loki/Prometheus | Repositorio con `docker compose`, dashboards como código y la traza de extremo a extremo |
| 4-6 | SLOs, alertas y runbooks; coste por ticket; redacción de PII | Documento de SLOs con presupuesto, 2 alertas multiventana y política de captura de contenido |
| 7-9 | Muestreo, cardinalidad, despliegue (Helm) y calidad online | Gateway validado + contratos de telemetría en CI + evaluación con intervalo |
| 10-12 | Mesa de incidentes, capstone y revisión de arquitectura | Revisión de arquitectura de 3-5 páginas, defendida ante un compañero |

## 4 · Certificaciones

> Las certificaciones **ayudan a pasar filtros y a ordenar el estudio**, pero ninguna demuestra el criterio de depurar un incidente: el portafolio (capstone + mesa) sí. Precios y temarios cambian: usa la página oficial.

| Certificación | Entidad | Para qué sirve en esta ruta | Verificación |
|---|---|---|---|
| **OpenTelemetry Certified Associate (OTCA)** | CNCF / Linux Foundation | Fundamentos de observabilidad, API/SDK, Collector e instrumentación: refuerza los módulos 02-06 | ✅ lanzada el 15-nov-2024 (anuncio de Linux Foundation); 🟡 pesos de dominios, nº de preguntas y precio varían entre fuentes (una cita 250 USD): confirma en la página oficial. El blog de OpenTelemetry (2025) describe su alcance |
| **Prometheus Certified Associate (PCA)** | CNCF / Linux Foundation | PromQL, alertas, instrumentación y exporters: módulos 09, 10, 16 | ✅ anunciada en mayo de 2022 por CNCF y Linux Foundation; 🟡 detalles del examen (duración, aprobado, vigencia) según fuentes de terceros |
| **Certified Kubernetes Administrator (CKA)** | CNCF / Linux Foundation | Base para operar el despliegue del módulo 19 (aparece como siguiente paso recomendado en la ficha de OTCA) | ✅ existe (la ficha de OTCA lo recomienda); ❔ temario no revisado aquí |
| **Professional Cloud DevOps Engineer** | Google Cloud | SRE, CI/CD, observabilidad y optimización de coste en GCP | ✅ página oficial accesible; 🟡 precio y recomendaciones de experiencia varían (la ficha habla de 2 horas y 50-60 preguntas; confirma) |
| **Datadog Fundamentals** (y APM/Log Management) | Datadog | Conocer una plataforma comercial de observabilidad para comparar con el stack abierto | ✅ página oficial de certificación accesible |
| **Certified Grafana Associate / Professional** | Grafana Labs | Dashboards, alertas y exploración en Grafana | ❔ **no confirmado**: las búsquedas solo devolvieron sitios de terceros (cursos de práctica) que se contradicen sobre el nombre, el precio y el temario; no pude verificar que exista una certificación oficial actual. Comprueba en grafana.com antes de planificar |
| Insignias/rutas gratuitas de Grafana (*learn.grafana.com*) | Grafana Labs | Aprender la plataforma con rutas guiadas | 🟡 mencionado por una guía de terceros; ❔ no abierto desde el sandbox |

## 5 · Comunidad y aprendizaje continuo

### 5.1 · Dónde se decide el estado del arte
| Recurso | Qué ofrece | Verificación |
|---|---|---|
| **Convenciones semánticas GenAI de OpenTelemetry** — repositorio `open-telemetry/semantic-conventions-genai` | La spec que usa este curso (atributos `gen_ai.*`, agentes, MCP). Estado **Development** a la fecha de la instantánea del módulo 04 (14-oct-2026) | ✅ confirmado (las convenciones de GenAI, proveedores y MCP se movieron a este repositorio dedicado en junio de 2026); 🟡 hay artículos que afirman que se han estabilizado y otros que siguen en *Development*: **la fuente es el repositorio y opentelemetry.io**, no un blog |
| SIG de GenAI de OpenTelemetry | Grupo de trabajo que define esas convenciones | 🟡 confirmado por fuentes de terceros (activo desde 2024); su calendario de reuniones no lo localicé: busca «SIG» en el repositorio de la comunidad de OpenTelemetry |
| Reuniones del grupo técnico de IA de CNCF (sesiones sobre convenciones GenAI) | Charlas puntuales con mantenedores | ✅ existe una sesión listada en `community.cncf.io` (año no indicado en el listado) |
| Slack de CNCF (canales de OpenTelemetry) | Preguntas a mantenedores, anuncios | ❔ no abierto desde el sandbox; la invitación está en la web de CNCF |
| `community.grafana.com` | Foro de Grafana, Loki, Tempo | ❔ no abierto desde el sandbox |
| Repositorios de `grafana/*`, `open-telemetry/*`, `prometheus/*` en GitHub | Issues, *changelogs*, *design docs*: la mejor fuente de «qué cambió» | ✅ patrón usado a lo largo del curso (lectura de READMEs y *changelogs*) |

### 5.2 · Conferencias
| Evento | Dato | Verificación |
|---|---|---|
| **ObservabilityCON 2026** (Grafana Labs) | San Francisco, 19-21 oct 2026 (el día 19 es de talleres con entrada aparte); versiones de un día en São Paulo, Londres, Madrid y Bengaluru en otoño | ✅ según las páginas de grafana.com encontradas (revisa fechas y precios) |
| **KubeCon + CloudNativeCon** (CNCF) | Incluye contenido de observabilidad y OpenTelemetry | ❔ existe (conocimiento general); fechas 2026 no verificadas |
| **SREcon** (USENIX) | Fiabilidad, incidentes, guardia | ❔ existe (conocimiento general); fechas 2026 no verificadas |
| **Monitorama** | Monitorización y observabilidad | ❔ existe (conocimiento general); fechas 2026 no verificadas |

### 5.3 · Libros y lecturas (citados por título)
- C. Majors, L. Fong-Jones, G. Miranker (2022), *Observability Engineering*, O'Reilly.
- T. Young, A. Parker (2024), *Learning OpenTelemetry*, O'Reilly — ✅ confirmado en el catálogo de O'Reilly (marzo de 2024).
- B. Beyer, C. Jones, J. Petoff, N. R. Murphy (2016), *Site Reliability Engineering*; B. Beyer et al. (2018), *The Site Reliability Workbook*, O'Reilly (ambos gratuitos en línea en el sitio de SRE de Google; ❔ no abierto desde el sandbox).
- A. Parker, D. Spoonhower, J. Mace, B. Sigelman, R. Isaacs (2020), *Distributed Tracing in Practice*, O'Reilly.
- B. H. Sigelman et al. (2010), *Dapper* (Google Technical Report) — ✅ confirmado en `research.google`.
- Netflix Technology Blog (2020), *Edgar: Solving Mysteries Faster with Observability* — ✅ confirmado (copia sindicada; la URL original es la del blog de Netflix).
- D. Luu, `post-mortems` (recopilación pública de postmortems), GitHub — ❔ repositorio conocido; no verificado desde el sandbox.
- OWASP, *Top 10 for LLM Applications 2025* — ✅ confirmado por búsqueda (LLM01 Prompt Injection, LLM02 Sensitive Information Disclosure) en fuentes secundarias; consulta el sitio de OWASP.

## 6 · Cómo presentar este curso en una candidatura

1. **Un repositorio**: tu capstone con el `docker compose`, el gateway del Collector validado, los contratos de telemetría y la revisión de arquitectura. Un revisor técnico debe poder ejecutarlo en 10 minutos.
2. **Una historia de incidente**: elige un caso de la mesa y cuenta el bucle de análisis (síntoma → ámbito → cambio → hipótesis → falsación → mitigación → confirmación), con cifras.
3. **Una decisión de coste y una de privacidad**, con sensibilidad y alternativas descartadas.
4. **Declara los límites**: qué probaste con el stack real y qué no (por ejemplo, sin clúster de Kubernetes real): la honestidad técnica se valora.

## 7 · Cómo mantener este documento
Las certificaciones, precios, fechas y estados de especificaciones **caducan**. Antes de usarlo: (1) abre las páginas oficiales de cada certificación, (2) comprueba el estado de las convenciones GenAI en el repositorio de OpenTelemetry, (3) revisa fechas de eventos. Si encuentras algo desactualizado, corrígelo y anota la fecha de verificación al principio.
