# Revisión de referencias y élite V2 · módulos 11-22 y extras

Revisor: rev-refs-elite-11-22 · Fecha: 16-oct-2026 · Método: lectura directa donde el sandbox lo permite (`anthropic.com`, `platform.claude.com`, `github.com`/`raw.githubusercontent.com`: README de `memorylimiterprocessor`, documentación de Prometheus y de Kubernetes, `danluu/post-mortems`) y búsqueda web con varias fuentes para lo bloqueado (`arxiv.org`, `sre.google`, `grafana.com`, `owasp.org`, `etsy.com`, `hamel.dev`, `eugeneyan.com`, `huggingface.co`).

Leyenda: **L** = leído en la fuente primaria · **B** = confirmado por búsqueda web / fuentes secundarias · **C** = conocimiento del libro/paper, no abierto.

## 1 · Referencias

| Referencia | Estado | Observaciones |
|---|---|---|
| Anthropic, *How we built our multi-agent research system* (4× / 15× tokens; 80 % de varianza; tracing sin leer contenido; rainbow deployments; ≈ 20 consultas; evaluación de estado final) | **L** ✅ | Citas exactas comprobadas |
| Anthropic, *Prompt caching* (1,25× / 2× escritura; 0,1× lectura, 0,05× y 0,025× en modelos recientes; mínimos 512-4 096; `input_tokens` excluye la caché; desglose `cache_creation`) | **L** ✅ | El texto de 13 («0,1× o menos», «512 a 4 096») coincide |
| Kim et al., arXiv:2512.08296 | **B** ✅ corregido | Hay **3 versiones**; v1: 180 configuraciones, 39-70 %; versiones posteriores: 260 configuraciones, peor caso −70 %; 17,2× / 4,4× estables. Texto de 11 reescrito; aviso de preprint |
| MCP SEP-414 | **B** ✅ | Final, autor Adrian Cole, creada 25-abr-2025, claves sin prefijo por diseño |
| OTel semconv MCP (`mcp.method.name`, `_meta`) | **B** ✅ | Estado Development |
| Invariant Labs, Tool Poisoning (1-abr-2025) | **B** ✅ | Añadido el detalle del PoC (clave SSH) |
| Elastic, trazado MCP | **B** corregido | Título real: «How to trace MCP server tool calls with OpenTelemetry and Elastic APM» (J. Rengifo); el *slug* de la URL difiere |
| FinOps Foundation, *Optimizing GenAI Usage* | **B** ✅ corregido | Existe (grupo de trabajo FinOps for AI, CC BY 4.0); enlace genérico → página del grupo; no se atribuyen cifras suyas |
| Zheng et al. 2023 (> 80 % de acuerdo = nivel humano), Panickssery et al. 2024 (NeurIPS 2024) | **B** ✅ | Añadido NeurIPS 2023 D&B |
| Johari et al., KDD '17 pp. 1517-1525 | **B** ✅ | Confirmado en DBLP; versión extendida «Always Valid Inference» (Oper. Res. 2022) solo por DBLP |
| SRE Workbook cap. 5 (14,4×/1 h/5 min/2 %; 6×/6 h/30 min/5 %; 1×/3 d/6 h/10 %) | **B** ✅ | Coincide con varias fuentes; el sandbox no abre `sre.google` |
| SRE Workbook cap. 16 *Canarying Releases* | **B** ✅ | Definición canario/control leída en el extracto de O'Reilly; «triángulo» de Davidovič (SREcon18) solo por New Relic: **fuente secundaria** |
| SRE Book cap. 11 (≤ 25 % guardia, ≥ 50 % ingeniería, ≤ 2 incidentes/turno ≈ 6 h por incidente) | **B** ✅ | La paráfrasis «2-3 incidentes» de blogs no es del original |
| SRE Book «70 % de las interrupciones por cambios» | **B** | Cifra confirmada por citas; capítulo (1, gestión de cambios) por **C** |
| SRE Book caps. 12-14, 28, 32; Workbook ap. «Example Error Budget Policy» | **C** | No confirmados por página; marcado en el texto |
| Allspaw 2012 | **B** ✅ | Existe; fecha 22-may-2012 vía enlace secundario |
| Grafana, blog multiventana (2025-02-28) | **B** ✅ | Autores A. Dedesko y A. Mariani |
| OTel Profiles alfa pública | **B** ✅ | Marzo 2026; Collector ≥ 0.148.0 solo por fuente secundaria |
| OTel `memorylimiterprocessor` README | **L** ✅ | Error no permanente, primero del pipeline, `spike_limit_mib` ≈ 20 % |
| Prometheus `sample_limit` («the entire scrape will be treated as failed») | **L** ✅ | |
| Kubernetes: «cpu limits are enforced by CPU throttling» | **L** ✅ | |
| OTel «Scaling the Collector» / Grafana «Scale Alloy tail sampling» | **B** ✅ | Afinidad por traceID y por servicio |
| Netflix *Edgar* (E. Carretto, sept-2020) | **B** ✅ corregido | Eliminada la afirmación «el tiempo ahorrado compensa el coste» (no verificada) |
| `danluu/post-mortems` | **L** ✅ corregido | **Eliminada** la afirmación «los mismos cinco patrones se repiten en todas las empresas»: el repositorio se organiza en categorías distintas |
| OWASP Top 10 LLM 2025 (LLM01, 02, 06, 07, 10) | **B** | Solo fuentes secundarias |
| Willison, *lethal trifecta* (16-jun-2025) | **B** ✅ | |
| RGPD cons. 26; WP29 Dictamen 05/2014 | **C** | Añadidos con aviso «no abierto / no es asesoramiento jurídico» |
| OTCA (15-nov-2024), ObservabilityCON 2026 (19-21 oct, Pier 27) | **B** ✅ | |
| Certificación de Grafana | **no confirmable** | Oficial: insignias de GROT Academy (Credly). El examen «Certified Grafana Associate» (60 preguntas, 90 min, 250 USD) solo lo citan terceros → **fuente secundaria / no verificada** |
| Afirmación del capstone «forma estándar» de contener el coste | **eliminada** | Reformulada como recomendación del curso |
| ENTREVISTAS: «política de ticket (≥ 3×)» | corregido | El Workbook usa 1× / 3 d / 6 h |

Totales (aprox.): **≈ 38 referencias/cifras comprobadas** (9 leídas en fuente primaria, el resto por búsqueda), **9 correcciones**, **3 afirmaciones eliminadas/reformuladas**, **8 no confirmables o solo por conocimiento** (marcadas en el texto).

## 2 · Puntos de élite añadidos (todos con fuente o cálculo reproducible)

| Módulo | Nº | Temas |
|---|---|---|
| 11 | +3 | Reanudación y errores compuestos (Anthropic); versión + rainbow deployments; propagación de errores por topología (Kim et al.) |
| 12 | +2 | Claves sin prefijo en `_meta` (SEP-414); contrato frente a la spec de MCP; fuente del tool poisoning |
| 13 | +3 | Punto de equilibrio de caché por TTL (`n* = (w−r)/(1−r)`: 1,28 vs 2,11); desglose de escrituras 5 min/1 h; coste vs calidad (80 % de varianza) |
| 14 | +3 | Techo del 80 % juez-humano; poder con 20 casos (`min_detectable_drop`: 15/27/32 puntos); evaluación del estado final |
| 15 | +3 | A/A y SRM; inferencia siempre válida (mSPRT); canario con control concurrente y triángulo de Davidovič |
| 16 | +2 | Cultura de guardia con números (SRE Book); Wheel of Misfortune |
| 17 | +2 | El eje X del flamegraph no es tiempo; estado de OTel Profiles |
| 18 | +2 | `sample_limit` ⇒ apagón de métricas; Dapper 1/1024 en servicios de poco tráfico |
| 19 | +2 | Afinidad de `span_metrics`/service graph distinta de la de tail sampling; semántica del `memory_limiter` (+ fuente de CPU throttling) |
| 20 | +3 | Triple letal medible por traza; seudonimización ≠ anonimización (RGPD); LLM10/LLM06 de OWASP |
| 21 | +2 | A priori del 70 % por cambios; mitigar antes de diagnosticar (dos cronómetros) |
| 22 | +2 | ADR con consecuencias medibles; PRR con contrato de telemetría |
| Compendio | +11 filas (63 → 74) | Columna «Fuente» con referencias externas en 24 filas y leyenda L/B/medido |
| extras | 4 respuestas ampliadas | Guardia, A/A, juez, coste de agente vs telemetría |

## 3 · Qué NO se pudo verificar

- Contenido de `sre.google` (Book/Workbook), `arxiv.org` (abstract de v2 concreta; solo v1 y v3 por búsqueda), `grafana.com` (blog, certificación, docs), `owasp.org`, `etsy.com`, `hamel.dev`, `eugeneyan.com`: confirmación solo por búsqueda.
- Capítulos y títulos del SRE Book citados de memoria (1, 12-14, 28, 32) y el apéndice de política de presupuesto de error.
- Precio y temario de certificaciones; fechas de eventos distintos de ObservabilityCON San Francisco y OTCA.
- RGPD/WP29 (texto legal no consultado); Collector 0.148.0 como primera versión con perfiles.
- `INTERFACES.md` sigue diciendo «63 secretos» (archivo compartido que no se tocó): ahora son 74.
