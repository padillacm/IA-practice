# Revisión técnica R3 · módulos 15-22 y extras

Revisor: técnico R3 (módulos 15-22, `extras/`, `stack/` y `supportops/` compartidos solo con cambios mínimos y compatibles hacia atrás).
Fecha: 16-oct-2026. Método: lectura de lecciones, proyectos, builders, `supportops/` y configuraciones; **re-ejecución** de todos los notebooks 15-22 con `nbclient` (modo rápido, Docker real para los laboratorios efímeros) y, con el stack completo levantado bajo `flock`, de las lecciones 15, 16, 17, 20, 21 y 22; validación con binarios oficiales; lectura de los README de `contrib` v0.162.0 (tail sampling, redaction, spanmetrics, OTTL).

## 1 · Qué se verificó de forma independiente (sin tocar nada)

| Qué | Cómo | Resultado |
|---|---|---|
| Fórmulas de 15 | `required_n_per_arm`, `min_detectable_drop`, McNemar exacto, PSI/KS/JS, CUSUM, SPRT de Wald (umbrales `ln((1-β)/α)` y `ln(β/(1-α))`), simulación de *peeking* | Correctas. Peeking: 24,3 % de falsos positivos con 20 miradas (SPRT 3,3 %) |
| Burn rate multiventana de 16 | `GOOGLE_POLICIES`: 14,4×/1 h/5 min (2 %), 6×/6 h/30 min (5 %), 1×/3 d/6 h (10 %) | Coinciden con el SRE Workbook cap. 5 («Alerting on SLOs»); ventana corta = 1/12 de la larga |
| Reglas de Grafana de 16 | Provisionadas en Grafana 13.2.4 real: 11 reglas cargadas (3 de módulo 10 + 8 SLO) y 17 dashboards | OK |
| `pyroscope-io` 1.3.0 / `pyroscope-otel` 1.1.0 | `inspect.signature(pyroscope.configure)`, `pip index` | Firma y versiones tal como cita la lección |
| Configs de 18 | `otelcol-contrib validate` 0.162.0, `loki -verify-config`, `tempo -config.verify`, `promtool check config` | Todas válidas |
| Charts de 19 | `helm lint`/`template` (Helm 4.3.1) con los repositorios oficiales clonados (`grafana-community/helm-charts`, `open-telemetry/opentelemetry-helm-charts`), `kubeconform` 0.7.0, validación de cada ConfigMap con su binario, `helm install --dry-run=server` y CRs del Operator contra **k3s 1.31.5 real** | 43 manifiestos, 0 inválidos; todo OK. Versiones de chart coinciden con los repos (loki 18.16.2 y grafana 14.0.1 en HEAD frente a 18.16.0/14.0.0 fijadas: patch) |
| Redacción de 20 | 7 variantes de `redaction_collector_config` con `otelcol validate`; `hmac_key` < 32 B rechazada («must be at least 32 bytes») | OK; `IsValidLuhn` y `SHA256` existen en OTTL 0.162; la cita «una línea de defensa, no la única medida de cumplimiento» está en el README |
| Gateway de 22 | `otelcol validate` | OK |
| Rúbricas (proyectos 15-22) | Ejecución completa de la solución de referencia | Todas las comprobaciones en verde; las plantillas puntúan 0/0 con ⏭️ (no fallan) |
| Referencias | Wald 1945, Page 1954, McNemar 1947, Johari et al. 2017 (KDD '17, pp. 1517-1525), Kohavi et al. 2020, Zheng 2023 (arXiv:2306.05685), Greshake et al. 2023 (arXiv:2302.12173), Perez & Ribeiro 2022, Willison 2025, SRE Book caps. 4/11/15/32, Workbook caps. 5/16, Allspaw 2012, Hidalgo 2020, Ren et al. 2010, Gregg 2016, Dapper 2010, Horvitz–Thompson 1952, PCA (anunciada el 18-may-2022) | Existen y los datos bibliográficos son correctos. Blog de Grafana sobre alertas multiventana (feb-2025): confirmado por búsqueda. No se pudieron abrir desde el sandbox: arxiv.org, simonwillison.net, grafana.com, sre.google (las referencias se confirmaron por conocimiento o por búsqueda web) |

## 2 · Problemas encontrados y arreglados

### Módulo 15
- **Autoevaluación 1: cifra errónea.** «≈ 435 por grupo (97 → 92)» → el cálculo da **326** (`required_n_per_arm(0.97, 0.92)`); (90 → 85) = 686 era correcto.
- «Con 120 casos solo detectas caídas de ≥ 6–8 puntos» → `min_detectable_drop(120, p0)` = 6,2 puntos (base 97 %) y **12,9** (base 85 %). Texto corregido en lección y autoevaluación.
- Secreto 4 atribuía a Johari et al. (2017) «≈ 1 de cada 4 comparaciones». Esa cifra es de **nuestra** simulación (20 miradas, 24 %); Johari muestra que el efecto crece con el nº de miradas. Reescrito.

### Módulo 16
- Postmortem de ejemplo: «la alerta se resuelve (la ventana de 1 h deja de superar el umbral)» era falso en una política multiventana; la que apaga la alerta es la **ventana corta de 5 min**. Corregido.
- «Dónde hubo suerte»: «horas de bajo tráfico, con el pico del mediodía habrían sido ≈ el doble». Falso: la intensidad diurna del generador a las 10:00 ya es ≈ 95 % del pico (1,43 vs 1,5). Corregido en lección y en la solución del proyecto.

### Módulo 17
- **`tracesToProfiles` provisionado con una consulta que no funciona.** `stack/grafana/provisioning/datasources/datasources.yaml` usaba `customQuery` con `{service_name=…, span_id="${__span.spanId}"}`. Medido contra Pyroscope 2.1.2 real: `span_id` **no** es una etiqueta consultable (selector → 0 muestras; `SelectMergeSpanProfile` con `spanSelector` → las 30 muestras del span). Se elimina `customQuery`/`query` (Grafana arma `{service_name="…"}` y, al llevar el span `pyroscope.profile.id`, pide el perfil de ese span). Lección y datasource ajustados y se declara que **el salto del botón «Profiles for this span» de la interfaz no pudo probarse** (solo la mitad Pyroscope).
- Autoevaluación 1: «para estrechar a ±0,5 puntos necesitarías ≈ 4× más muestras» → de ±1,28 a ±0,5 hacen falta ≈ 6,6×; 4× da la mitad del margen (±0,64). Corregido.
- Afirmaciones demasiado optimistas: «el total de Pyroscope coincide a pocos %» (medido: +16 % frente a la CPU del SO) y «la CPU del span coincide con la del ticket» (20 ms frente a 67 ms: 2 muestras a 100 Hz). Reescritas como «mismo orden de magnitud».
- Factores de aceleración de la lección (×1,5-2 / ×5-6) → medidos ×2,1 / ×2,5 / ×4,8 / ×56 en esta máquina; textos y compendio (21) pasan a «≈ ×2» y «≈ ×4-6». La afirmación «hasta un orden de magnitud» de la variante `fast` se queda corta (≈ ×50): la cifra exacta depende de la máquina y de `N`.

### Módulo 18
- **El laboratorio en vivo de multi-tenant contradecía el texto**: `backends_experiment(CORPUS)` recibía el corpus de tiempos simulados (hace semanas) y Tempo devolvía **0** trazas visibles por tenant (la grabación usó `backends_experiment()` con su propio corpus «en vivo»). La celda llama ahora a `S.backends_experiment()` (verificado: 5 trazas por tenant a los ≈ 5 s).
- Comprobado: `numeric_attribute` + atributo *double* → SIGSEGV con 0.162.0 (también con `min_value: 0`; el texto lo decía solo para «decimal»), `FNV` en la política `probabilistic`, puerta `processor.tailsamplingprocessor.usetracestate`, `decision_cache`, `drop_pending_traces_on_shutdown`, métricas internas: todo coincide con el README v0.162.0.

### Módulo 19 (revisado con rigor; **los pods siguen sin ejecutarse**)
- **El agente OTLP no era alcanzable.** `supportops` enviaba a `http://otel-agent-opentelemetry-collector.observability.svc…:4318`: ese Service no existe (el release usa `fullnameOverride: otel-agent` y, en modo `daemonset`, el chart **no crea Service** salvo `service.enabled: true`). Arreglo: `otel-agent.yaml` activa `service.enabled` (el chart añade `internalTrafficPolicy: Local`) y los endpoints (chart `supportops`, values de laboratorio, CR `Instrumentation`) apuntan a `otel-agent.observability.svc.cluster.local:4318`. Re-renderizado y validado (6 manifiestos, `kubeconform` OK, dry-run=server OK). La captura pregrabada se actualizó en consecuencia (+1 Service).
- **El CR `Instrumentation` muestreaba al 25 % en el SDK** (`parentbased_traceidratio 0.25`) delante de un `tail_sampling`: contradice el aviso del módulo 18 (las probabilidades se multiplican y se pierden errores). Ahora `parentbased_always_on`.
- **El chart `supportops` no tenía sondas** aunque el objetivo del módulo prometía «sondas». Se añade `livenessProbe` `exec` por **latido** (el proceso no abre puertos): `supportops.k8s.run_traffic` toca `/tmp/heartbeat` en cada ciclo (cambio mínimo y compatible en un módulo compartido). Declarado como **no ejecutado en un pod**.
- El comentario del CR del Operator decía «equivale al gateway de Helm»: no (sin política `costly`, sin `span_metrics`). Reformulado.
- El texto de «honestidad» sobre el sandbox es correcto; se añaden a la lista de *no verificado* la `livenessProbe` por latido y el Service con `internalTrafficPolicy: Local`.

### Módulo 20
- Sin errores técnicos hallados (ver tabla). Redacción, HMAC mínimo de 32 bytes, OTTL, noisy-or, cálculos de fuerza bruta: todo verificado o recalculado.

### Módulo 21
- Compendio: fila del módulo 17 actualizada (factores de aceleración). La mesa de incidentes es diagnosticable sin pistas directas: las alertas son neutras y el catálogo ofrece **10 causas** y 8 mitigaciones (hay señuelos como `provider_outage`, `traffic_spike`, `raise_timeouts`); la solución de referencia saca 5/5 en los 5 casos y la rúbrica pasa completa.

### Módulo 22
- «Una caída parcial **nunca** quema a 14,4×… 4× un presupuesto del 5 %»: mezclaba el presupuesto de latencia (5 %) con el de disponibilidad (1 %; con el 20 % de tráfico malo serían 20×). La conclusión sigue siendo cierta porque el sistema degrada y escala (cuenta como disponible), pero el razonamiento estaba mal formulado. Corregido en lección y en la guía de entrevistas.
- «Grafana Labs documenta como arquitectura de referencia…» no tenía cita: suavizado y marcado como no verificado.
- **Sección 11 (en vivo) contaminada por otras lecciones**: con el stack compartido, las consultas `{ status = error }`, `{ trace:duration > 8s }` y `{service_name=~"supportops.*"}` mezclaban trazas/logs de módulos ejecutados minutos antes (salía «lentas guardadas: 36 de 18 enviadas», «282 trazas con error» y 6 correos en claro que eran los del servicio de demostración del módulo 20). Las consultas se acotan a los cinco servicios de la ejecución (`invoke_workflow` para las lentas).

### Extras
- `ENTREVISTAS_SYSTEM_DESIGN.md` P18: misma corrección del burn parcial. `RUTA_DE_CARRERA.md`: todas las certificaciones/eventos están marcados ✅/🟡/❔ de forma coherente; PCA (mayo 2022) y OTCA confirmadas; la certificación de Grafana sigue marcada «no confirmada».

## 3 · Recomendaciones (no aplicadas: cambios grandes o dependientes del entorno)

1. **Probar el módulo 19 en un clúster con pods** (kind/k3d en máquina del alumno): en especial el Service `otel-agent` con `internalTrafficPolicy: Local`, la `livenessProbe`, `hostPort` y el HPA. Hasta entonces el texto debe seguir diciendo que ningún pod se ejecutó.
2. **Probar el salto «Profiles for this span»** de Grafana con Tempo + Pyroscope reales (UI). Si Grafana exigiese `customQuery`, usar solo `{service_name="…"}` y nunca `span_id` dentro del selector.
3. **Fragilidad de los laboratorios en vivo** (módulos 18-19): el mismo notebook falló una vez por carrera de contenedores/puertos con otras sesiones y, otra vez, la tabla `num_traces` salió con `None` por un *scrape* de métricas internas tomado demasiado pronto. Convendría reintentar `SamplingLab.internal()` hasta 3 veces y subir el plazo de la búsqueda multi-tenant de Tempo (45 s → 90 s).
4. **Rúbricas con medidas de CPU (módulo 17)**: usan *ratios* y rangos amplios (≥ 5×, 0,4×–1,1× del tope de Amdahl) y pasaron aquí, pero dependen de la máquina; documentar que en equipos muy lentos o con mucha carga pueden oscilar.
5. **Módulo 20, R1**: el umbral de recall (≥ 0,86) está a 0,9 puntos de la solución (0,869), no «2-5 %» como dice la nota. Es determinista (semilla 42), pero cualquier cambio en el catálogo lo rompería; conviene recalibrar o redactar «margen del 1 %».
6. **Estados de las convenciones GenAI**: la fuente es `open-telemetry/semantic-conventions-genai` (confirmada por la instantánea del módulo 04); mantener el aviso *Development* en todos los módulos.
7. **Mesa de incidentes (21)**: el catálogo de causas sigue siendo una lista cerrada con un caso por causa principal; para un examen más duro, ofrecer causas plausibles pero incorrectas por caso y no imprimir las claves de evidencia por caso en el Paso 0.
8. **Chart `loki` y retención**: `values/loki.yaml` fija `retention_period: 168h` sin activar el compactor con `retention_enabled`; no tiene efecto. Documentar o activar con `delete_request_store`.
9. Versiones de chart fijadas (loki 18.16.0, grafana 14.0.0) ya tienen parches 18.16.2 / 14.0.1 en HEAD: revalidar al subir versiones.

## 4 · Qué NO se pudo verificar

- **Pods en clúster** (kind/k3d/k3s no arrancan pods en el sandbox): planificación, probes, `hostPort`, HPA con métricas, Operator en ejecución (webhook/inyección), tráfico agente→gateway real, `internalTrafficPolicy: Local`.
- El **botón «Profiles for this span»** de la UI de Grafana (solo se verificó la API de Pyroscope).
- Contenido de sitios bloqueados en el sandbox: `grafana.com` (documentación y blog), `arxiv.org`, `simonwillison.net`, `sre.google`, `genai.owasp.org`; las cifras de industria citadas (SRE Workbook, SRE Book) se contrastaron con el conocimiento del libro, no con la página en vivo. La disponibilidad/fechas de ObservabilityCON 2026 y precios de certificaciones no se comprobaron (están marcadas en el propio documento).
- Adaptadores de proveedores LLM reales y arm64/Windows (fuera de alcance, ya declarado en el README raíz).
