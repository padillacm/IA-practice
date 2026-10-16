# Guía de entrevistas y system design de observabilidad de agentes de IA

Documento extra del curso «Observabilidad de agentes de IA en producción (OpenTelemetry · Grafana · Loki · Tempo)». Sirve para **practicar** entrevistas de AI platform, SRE de IA y observability engineering con lo aprendido en los módulos 00-22.

> **Cómo usarlo.** (1) Responde cada pregunta **en voz alta y sin mirar** (2 minutos), (2) compara con la respuesta modelo y con el módulo indicado, (3) en los diseños, dibuja primero y calcula después: **aclara requisitos → estima → diseña → discute riesgos y alternativas**.
> **Honestidad.** Las cifras de los ejemplos salen de las simulaciones del curso (`mock`, semilla 42) o de fórmulas con supuestos explícitos: úsalas como **órdenes de magnitud** y di siempre tus supuestos en una entrevista real. Esto no recoge preguntas reales de ninguna empresa: son preguntas *representativas* del tipo de problema.

---

## Parte A · 36 preguntas típicas (con qué evalúan y respuesta modelo)

### A1 · Fundamentos y modelo de datos

**1. ¿Por qué el monitoreo clásico (CPU, latencia media, 5xx) no basta para un agente LLM?** *(módulo 00-02)*
Evalúa: ¿entiendes qué cambia con los agentes? Respuesta modelo: la petición es una **cadena de pasos no determinista** (LLM + herramientas), el **coste** es un síntoma (bucles), la **calidad** puede degradarse sin errores (regresión silenciosa) y el contenido es **sensible**. Hacen falta trazas (forma de la ejecución), métricas (SLOs, coste), logs correlacionados y evaluación online.

**2. Explica trace, span, resource, scope y contexto. ¿Qué viaja entre servicios?** *(03)*
Respuesta modelo: un trace es un árbol de spans con un `trace_id`; el span tiene nombre, tiempos, atributos, eventos, estado y padre; el *resource* describe quién emite (`service.name`, `service.instance.id`); el *scope*, la librería instrumentada. Entre servicios viaja el **contexto** W3C (`traceparent` con `trace_id`, `span_id` del padre y flags `sampled`) y opcionalmente `baggage`.

**3. ¿Qué spans modelarías para un agente y qué atributos son críticos?** *(04)*
Respuesta modelo: `invoke_agent` (raíz), `chat` por llamada al modelo (CLIENT), `execute_tool` por herramienta. Atributos GenAI: `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.usage.input_tokens/output_tokens`, `gen_ai.response.finish_reasons`, `gen_ai.tool.name`, más dominio acotado (`supportops.*`) y **versión**. Cuenta tokens/coste **solo en las hojas `chat`**. Menciona que las convenciones GenAI son *Development*: contrato de pruebas.

**4. ¿Cuándo usar un evento de span y cuándo un log?** *(02)*
Evento: viaja y se muestrea con la traza (reintentos, excepciones); log independiente: auditoría y lo que ocurre fuera de un span. Siempre con `trace_id`.

**5. ¿Qué es la cardinalidad y por qué es el enemigo?** *(09, 18)*
Cada combinación de valores de etiquetas es una serie (≈ 1-3 KB de RAM por serie, medido en el curso). IDs (ticket, cliente, trace) van en trazas/logs; en métricas, etiquetas acotadas. Controla con Views del SDK y en el Collector; vigila `prometheus_tsdb_head_series`.

**6. ¿Por qué no se promedian percentiles?** *(09)*
El promedio de p95 de varias instancias no es el p95 global. Se agregan **buckets** (`sum by (le)`) y se calcula `histogram_quantile` después. Medido: ≈ 5 s frente a ≈ 9 s correcto.

### A2 · Stack (Collector, Tempo, Loki, Prometheus, Grafana)

**7. Pipeline típico del Collector y por qué ese orden.** *(05, 20, 22)*
`memory_limiter` primero (protege); redacción antes de cualquier exportador; `span_metrics` **antes** del muestreo; `tail_sampling`; `batch` al final. Cada inversión produce un incidente: OOM, PII en métricas, RED sesgada, colas sin sentido.

**8. Head vs tail sampling. ¿Qué eliges para agentes?** *(18)*
Head: barato y sin estado, decide sin ver el resultado (pierde errores). Tail: decide con la traza completa (errores, lentas, caras) pero necesita memoria ≈ tráfico × `decision_wait` y afinidad por `traceID` con varias réplicas. Para agentes: tail por valor + base pequeña, métricas RED antes. Modo de fallo silencioso: `num_traces` insuficiente.

**9. ¿Por qué `trace_id` no debe ser etiqueta en Loki y qué es la structured metadata?** *(08)*
Etiqueta = índice y stream: 300 trazas → 300 streams (medido). Structured metadata guarda pares clave-valor por línea sin indexarlos como etiquetas; permite filtrar por `trace_id` y correlacionar.

**10. ¿Cómo consulta Tempo una traza lenta con error en una herramienta?** *(07)*
TraceQL: `{ name =~ "execute_tool.*" && status = error } | select(span.error.type)`; para trazas lentas, `trace:duration`. Recuerda: por id es inmediato, por búsqueda hay retraso de ≈ 15-20 s.

**11. ¿Cómo correlacionas métrica → traza → log?** *(09, 10)*
Exemplars en histogramas (con span *sampled* activo) saltan a la traza; la traza enlaza a logs por `trace_id`; los logs a la traza con un *derived field*. Condición: el `trace_id` debe llegar a los logs (módulo 08).

**12. Un dashboard queda vacío tras un despliegue sin cambios en el backend. ¿Qué miras?** *(10, 22)*
Atributos/etiquetas renombrados o eliminados (`allowed_keys`, un View), nombres de métrica con unidades, `noDataState`, datasource y `uid`. Un contrato de telemetría en CI lo habría detectado.

### A3 · Coste y escala

**13. ¿Cómo calculas el coste del propio stack de observabilidad?** *(18)*
Volumen = tickets/día × spans/ticket × bytes/span (trazas), líneas × bytes (logs), series × muestras (métricas); luego retención por clase y precio por GB-mes (+ ingesta en SaaS). Presenta **sensibilidad** (×2 tráfico, ×2 retención).

**14. Se duplica el tráfico. ¿Qué escala y qué no?** *(18, 19)*
Trazas y logs ~ linealmente; métricas **no** (dependen de series). Memoria del tail sampling sube con tráfico × `decision_wait`; ingesta de Loki/Tempo, límites por tenant; réplicas del gateway con `load_balancing` por `traceID`.

**15. ¿Cómo evitas que un incidente masivo dispare la factura?** *(18)*
Políticas por valor + límite de bytes/s (`rate_limiting`/`bytes_limiting`) como red de seguridad; límites por tenant; reducir la captura de contenido; muestreo adaptativo.

**16. ¿Qué coste añade capturar prompts y respuestas?** *(20)*
Multiplica por ≈ 2,5 los bytes por traza (1,8 → 4,7 KB/ticket en el laboratorio) y añade riesgo de PII. Política por niveles: apagado por defecto, redactado en muestra, completo con aprobación y caducidad.

### A4 · SLOs, alertas e incidentes

**17. Define SLIs/SLOs para un agente de soporte.** *(16)*
Disponibilidad (ok|escalated), latencia (percentil o fracción ≤ umbral, **medida sobre la línea base**), calidad (groundedness, muestra uniforme con IC), coste (USD por ticket resuelto). Presupuesto de error, política de congelación pactada de antemano.

**18. ¿Qué es el burn rate multiventana y por qué?** *(16)*
Burn = tasa de error / presupuesto. Ventana larga (¿es grave?) y corta (¿sigue?). 14,4× en 1 h/5 min = 2 % del presupuesto mensual en una hora. Una caída **parcial** rara vez llega a 14,4× (con el 20 % del tráfico afectado y un presupuesto del 5 % el máximo es 4×): política de ticket (≥ 3×).

**19. Latencia ↓, coste ↓, 👎 ↑ tras un despliegue. ¿Qué pasó y cómo lo demuestras?** *(15, 21)*
Regresión silenciosa: el agente dejó de llamar herramientas. Demuestra con herramientas por ticket por versión, fracción sin herramientas, juez/trayectoria; mitiga con rollback.

**20. Coste por ticket ×3 sin errores. Triage.** *(13, 21)*
Mira la forma de la traza: ≥ 5 `execute_tool` idénticos seguidos = bucle; tokens de entrada creciendo; mitiga con `LoopGuard`/`max_steps` y **verifica re-ejecutando** el incidente.

**21. Orquestador con 2 reintentos a un subagente que a su vez reintenta 2 veces a una herramienta. ¿Peor caso de llamadas?** *(11)*
`(r+1)^d = 3² = 9`. Plazos decrecientes, disyuntor, deadline propagado, idempotencia.

**22. Prometheus al 85 % de memoria con tráfico plano.** *(21)*
Cardinalidad: escalón en `active_series`, localizar métrica (`topk(count by (__name__))`) y etiqueta (valores distintos), arreglar en origen (View) y red de seguridad (`aggregate_labels`), confirmar el descenso.

**23. «Tenemos 3 trazas por petición.» ¿Por qué?** *(11, 21)*
Contexto perdido: librería de transporte, gateway que elimina `traceparent`, cabeceras sensibles a mayúsculas, muestreo sin `ParentBased`. Contrato: `n_traces == n_tickets`.

**24. ¿Qué hay en un buen runbook y un postmortem sin culpa?** *(16)*
Runbook: qué significa la alerta, primeros 5 minutos, árbol de diagnóstico, mitigación, escalado. Postmortem: impacto con cifras, cronología, causa y factores contribuyentes, acciones con dueño, plazo y tipo (prevenir/detectar/mitigar).

### A5 · Calidad y evaluación

**25. ¿Cómo mides calidad online sin evaluarlo todo?** *(14)*
Muestreo (estratificado para cazar, uniforme para el SLO), juez LLM con sesgos conocidos, corrección Rogan-Gladen con sensibilidad/especificidad del juez, IC de Wilson; coste del juez ≈ 9× el de atender.

**26. ¿Cómo detectas una regresión de prompt antes de producción?** *(15)*
Dataset de oro desde trazas, replay con compuerta apareada (McNemar), trayectoria de herramientas, canario con SPRT; evita «mirar 20 veces» (≈ 24 % de falsos positivos).

**27. ¿Por qué un LLM-juez puede mentirte?** *(14)*
Sesgos de verbosidad, posición y autopreferencia; ruido; fallos silenciosos (`parse_error`). Sondas de sesgo por cambio de juez, código antes que LLM para lo verificable, métricas de fallos del juez.

### A6 · Privacidad y seguridad

**28. ¿Qué haces con la PII en prompts y logs?** *(20)*
Minimiza (captura apagada), redacta en la app y en el Collector (`redaction`/`transform`), HMAC (no SHA sin clave) para seudónimos, retención por clase, acceso y auditoría. Defensa en profundidad: cada capa tiene residuo.

**29. ¿Cómo se detecta prompt injection con telemetría?** *(20)*
Contenido (reglas/normalización, puntuación) y **comportamiento** (herramienta destructiva sin verificación previa, fuera de intención). Señales estructurales sobreviven a la ofuscación. Detectar ≠ impedir: arquitectura (mínimo privilegio, aprobación humana).

**30. Derecho de supresión con trazas en Tempo.** *(20)*
Planificar antes: no escribir PII, contenido en almacén aparte con retención corta, seudónimo por sujeto (borrado criptográfico), índice sujeto→trace_ids. No hay un `DELETE` cómodo por traza.

### A7 · Cultura y criterio

**31. ¿Qué mides para saber si tu guardia está sana?** *(16, 21)* Páginas por semana, % accionables, tiempo de reconocimiento, repetición de incidentes.

**32. ¿Qué es un contrato de telemetría? Dame tres.** *(21, 22)* Afirmaciones comprobables en CI: una traza por ticket, tokens de hojas = árbol, ningún span con PII, atributos que usan los dashboards existen.

**33. ¿Cuándo NO usarías tail sampling / captura de contenido / un juez LLM?** *(18, 20, 14)* Tráfico bajo y barato (guárdalo todo), datos sensibles sin base de tratamiento, calidad verificable con reglas.

**34. Elige entre instrumentación manual y automática (OpenLIT/OpenLLMetry).** *(06)* Auto: rápido, cubre clientes; riesgos: trazas huérfanas, contenido por defecto, doble instrumentación, ceros falsos en *streaming*. Híbrido: spans de agente/herramienta manuales + auto en el cliente, `max_retries=0`.

**35. Un ejecutivo pregunta «¿cuánto cuesta la observabilidad y qué obtenemos?»** *(18, 22)* Cifras con supuestos, sensibilidad, y beneficios medibles: TTD/TTR de la mesa de incidentes, incidentes evitados por contratos, ahorro por bucles cortados.

**36. ¿Cómo aceptarías una plataforma de observabilidad nueva?** *(21, 22)* Con un examen de incidentes (mesa) + scorecard automático + checklist con lo manual declarado, no con una demo de dashboards.

---

## Parte B · Tres diseños de referencia

> Formato: **1) Aclaraciones → 2) Requisitos → 3) Estimaciones → 4) Arquitectura → 5) Decisiones y alternativas → 6) Modos de fallo y detección → 7) Seguimiento**. Los números son *ilustrativos*: lo que se evalúa es el razonamiento y los supuestos explícitos.

### Diseño 1 · Plataforma de observabilidad para un agente de soporte multi-agente (1 M tickets/día)

**Aclaraciones a preguntar:** ¿latencia aceptable?, ¿datos personales (qué región y qué base legal)?, ¿un solo proveedor LLM o varios?, ¿cuántos equipos consultan?, ¿SaaS o autoalojado?, ¿presupuesto?

**Requisitos (medibles):** disponibilidad ≥ 99 %, latencia p95 ≤ 10 s (línea base multi-agente), calidad ≥ 95 % (muestra uniforme), coste por ticket vigilado, 0 PII en backends, depurar en < 15 min con solo telemetría.

**Estimaciones (fórmulas):**
- Tickets/s medios = 10⁶ / 86 400 ≈ **11,6**; pico ×3 ≈ **35/s**.
- Spans por ticket multi-agente ≈ **11** (medido en el curso: 2 686 spans / 240 tickets); bytes/span ≈ 600 → trazas ≈ 10⁶ × 11 × 600 B ≈ **6,6 GB/día** sin muestrear.
- Tail sampling: guarda errores, lentas, caras y 10 % de base → en el laboratorio ≈ 29 % de las trazas (con un incidente) y bastante menos en régimen normal: **≈ 1,9 GB/día** almacenados antes de compresión.
- `num_traces` ≥ tráfico pico × `decision_wait` = 35 × 10 = **350** trazas simultáneas; con margen 3× → **≈ 1 000**. (Si tu gateway recibe más, escala en réplicas con `load_balancing` por `traceID`.)
- Series de métricas: 5 000 series × (86 400/15) muestras × 1,5 B ≈ 43 MB/día; **el riesgo es la cardinalidad**, no el volumen.

**Arquitectura:**
```
agentes ──OTLP──► gateway Collector ──► Tempo (trazas, tail sampling)
 (SDK OTel)        memory_limiter       Loki (logs redactados, trace_id)
 contenido OFF     redaction            Prometheus/Mimir (RED + GenAI + coste)
 por defecto       span_metrics (100 %)        │
                   tail_sampling               ▼
                   batch                  Grafana · alertas burn rate · runbooks
evaluador online (otro servicio, traza enlazada) ──► eventos de evaluación
```

**Decisiones y alternativas:** tail sampling por valor (frente a head: pierde errores; frente a guardarlo todo: coste); RED antes del muestreo (frente a derivar de trazas muestreadas: sesgo ≈ ×4); redacción en app **y** Collector; SLO de latencia sobre la línea base del multi-agente; política de ticket para caídas parciales.

**Modos de fallo y detección:** pérdida silenciosa (`dropped_too_early`, exportadores fallidos, canario e2e), cardinalidad (series activas con tráfico plano), trazas partidas (`trazas/ticket ≠ 1`), PII (contador de salida + LogQL de control), regresión silenciosa (herramientas por versión), cascada (intentos por ticket).

**Seguimiento típico:** «¿qué cambia con 3 niveles de agentes?» (`(r+1)^d`, más spans, plazos decrecientes) · «¿y con 10× el tráfico?» (réplicas del gateway, límites por tenant, coste) · «¿cómo pruebas que funciona?» (mesa de incidentes, contratos en CI).

### Diseño 2 · Evaluación continua de calidad y control de regresiones de prompts/modelos

**Aclaraciones:** ¿qué es «calidad» para el negocio (resolución, groundedness, tono)?, ¿hay feedback de usuario?, ¿con qué frecuencia cambian prompts/modelos?, ¿presupuesto de evaluación?

**Requisitos:** detectar caídas de calidad de ≥ 5 puntos en < 24 h, bloquear despliegues regresivos, coste de evaluación acotado.

**Estimaciones:** juez ≈ 9× el coste de atender un ticket (módulo 14) → evaluar el 100 % es inviable; muestra uniforme del 25 % para el SLO (n ≈ 100 por hora a 400 tickets/h → IC de Wilson ≈ ±5 pts); muestra estratificada (errores 100 %, escalados 50 %, premium 25 %, base 10 %) para cazar. Tamaño mínimo por brazo con `required_n_per_arm`.

**Arquitectura:** `CaseCollector` en el agente → cola → `OnlineEvaluator` (otro servicio; traza propia con *link*; eventos `gen_ai.evaluation.result`) → métricas por versión → dashboard + SLO de calidad (quema lenta). Pre-producción: dataset de oro desde trazas + replay + `ReleaseGate` (McNemar apareado, trayectoria, guardarraíles) → canario con SPRT.

**Decisiones:** muestreo determinista por hash; corrección Rogan-Gladen; sondas de sesgo del juez al cambiar de juez; código antes que LLM para lo verificable; trayectoria de herramientas como señal barata.

**Fallos:** juez roto («calidad mejora» el día que falla: cuenta `parse_error`), dataset envejecido, mirar demasiadas veces (falsos positivos ≈ 24 %), versión sin etiquetar.

**Seguimiento:** «¿cómo evitas que el juez favorezca al modelo que lo escribió?» · «¿qué haces con 5 versiones simultáneas (A/B)?» · «¿cuándo haces rollback automático?» (solo con datos suficientes: SPRT).

### Diseño 3 · Plataforma multi-tenant de agentes: aislamiento, coste y privacidad

**Aclaraciones:** ¿tenants = empresas clientes (aislamiento duro) o equipos internos?, ¿facturación por uso?, ¿residencia de datos?, ¿cuántos tenants (10, 1 000, 100 000)?

**Requisitos:** que un tenant ruidoso no afecte a otros; atribución de coste por tenant/feature/modelo; datos de un tenant nunca visibles a otro; retención y supresión por tenant.

**Estimaciones:** límites por tenant en ingesta (ej. bytes/s) = radio de explosión; atribución: tokens por tenant (en **logs/atributos de span**, no como etiqueta de métrica si hay 10⁵ tenants → series ilimitadas; usa agregados por *tier* en métricas y detalle por tenant en logs/trazas); coste por serie ≈ 1-3 KB × tenants × combinaciones.

**Arquitectura:** `X-Scope-OrgID` (Loki/Tempo multitenancy) por tenant o por *tier*; Collector gateway que inyecta el tenant desde la autenticación (no de la carga útil); redacción obligatoria; límites en Loki (`ingestion_rate_mb`, streams activos) y Tempo (`max_bytes_per_trace`); retención por tenant (`retention_stream`/overrides); auditoría de accesos a contenido; paneles por tenant con variables y RBAC en Grafana.

**Decisiones:** aislamiento por tenant (más seguro, más coste) vs lógico (etiqueta + RBAC); `customer_id` jamás como etiqueta de métrica; contenido en almacén aparte con retención corta y borrado por tenant; presupuestos (`BudgetGuard`) por tenant.

**Fallos:** tenant que dispara cardinalidad/ingesta (429 y métrica propia), fuga entre tenants por una consulta sin filtro (pruebas de aislamiento), cabecera de tenant falsificada (confía solo en la autenticación), supresión incompleta.

**Seguimiento:** «¿cómo facturas con exactitud si hay muestreo?» (pesos de inclusión o métricas previas al muestreo) · «¿qué pasa con un tenant que quiere sus propios dashboards?» (provisión como código por tenant).

---

## Parte C · Ejercicios de pizarra rápidos (con solución)

| # | Ejercicio | Solución |
|---|---|---|
| 1 | SLO 99,9 % a 30 días. ¿Minutos de caída total permitidos? | 0,1 % × 43 200 min = **43,2 min** |
| 2 | Burn 14,4× con SLO 99 %: ¿cuánto tarda en agotar el presupuesto mensual? | 720 h / 14,4 = **50 h** |
| 3 | 150 trazas nuevas/s, `decision_wait` 10 s. `num_traces` mínimo | 150 × 10 = **1 500** (con margen 2-3×) |
| 4 | 3 servicios muestrean al 20 % de forma independiente. Fracción de trazas completas | 0,2³ = **0,8 %** (con `ParentBased`: 20 %) |
| 5 | `r = 2` reintentos, profundidad 2. Llamadas máximas a la herramienta | (2+1)² = **9** |
| 6 | Un `customer_id` con 200 valores en una métrica con 3 etiquetas (3 × 4 × 2 = 24 series). ¿Series nuevas? | 24 × 200 = **4 800** (×200) |
| 7 | Muestreo: errores 100 %, base 10 %. Peso de una traza base en la corrección | 1/0,10 = **10** |
| 8 | Tokens de entrada: contexto 350 tokens y +100 por vuelta de un bucle de 6 pasos. Total aproximado | 350+450+550+650+750+850 = **3 600** (medido en el curso: 3 576) |
| 9 | SHA-256 sin clave de un móvil (2·10⁸ candidatos) a 10⁶ hash/s | 2·10⁸/10⁶ = **200 s**; con 10⁹/s: 0,2 s |
| 10 | Noisy-or de dos señales (0,75 y 0,55) | 1 − 0,25·0,45 = **0,8875** |

---

## Rúbrica de autoevaluación de un diseño

| Criterio | 0 | 1 | 2 |
|---|---|---|---|
| Requisitos | no hay | cualitativos | **medibles** (SLI, umbral) |
| Estimaciones | no hay | cifras sueltas | fórmulas con **supuestos** y sensibilidad |
| Arquitectura | lista de herramientas | diagrama | diagrama **con orden y por qué** |
| Alternativas | ninguna | menciona | compara con coste/riesgo |
| Modos de fallo | ninguno | lista | cada uno con **señal** y mitigación |
| Privacidad y coste | ausentes | mencionados | integrados en las decisiones |
| Pruebas | «probar» | pruebas unitarias | contratos + mesa de incidentes |

Objetivo: ≥ 11/14 en los tres diseños antes de una entrevista de nivel senior/staff.

## Lecturas
- Majors, Fong-Jones, Miranker (2022), *Observability Engineering*, O'Reilly · Beyer et al., *Site Reliability Engineering* (cap. 4, 6, 15) y *The Site Reliability Workbook* (cap. 5) · el compendio del curso (`21_elite_playbook/COMPENDIO_SECRETOS.md`) como lista de comprobación para las respuestas.
