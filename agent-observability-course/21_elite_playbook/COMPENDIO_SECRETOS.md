# Compendio de secretos de élite (módulos 00-21)

Recopila y amplía las secciones «🧠 Secretos de la élite» de todas las lecciones. Cada fila: **secreto**, *por qué importa o cifra medida* (laboratorio `mock`, semilla 42, salvo indicación) y **fuente** (módulo del curso y, entre paréntesis implícitos, las referencias que ese módulo cita).

> Las cifras proceden de simulaciones deterministas del propio curso; úsalas como órdenes de magnitud, no como constantes universales. Lo marcado *Development* (convenciones GenAI, MCP) cambia entre versiones. **Fuentes:** «leída/leído» = comprobado en la página o el repositorio primario el 16-oct-2026; «búsqueda» = confirmado solo por búsqueda web o fuentes secundarias (`sre.google`, `grafana.com`, `arxiv.org`, `owasp.org` no abren desde el sandbox del curso); «medido/cálculo del curso» = reproducible en los notebooks.


## Instrumentación

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 01 | **La unidad de coste y de fallo es el *paso*, no la petición** | Dos peticiones idénticas pueden costar 1× y 6×: pon `max_steps` **y** un tope de tokens/coste por petición. | Módulo 01 · módulo 13 |
| 01 | **Los reintentos enmascaran fallos** | Un `llm_error` transitorio acaba en `ok`; cuenta **intentos**, no solo resultados finales, o no verás degradarse al proveedor hasta que se agoten. | Módulo 01 · módulo 16 |
| 01/12 | **Las herramientas con efectos deben ser idempotentes** | Reintentar tras un timeout puede reembolsar dos veces (medido en el módulo 12: 2 reembolsos por 1 intención). Clave de idempotencia registrada en el span del servidor. | Módulo 12 §8 · MCP: anotaciones de herramientas (`idempotentHint`) — las declara el servidor, no son garantía |
| 01/15 | **«Más rápido y más barato» puede ser peor** | Una alucinación no llama herramientas: vigila `tool_calls` por petición como señal de salud (módulo 15: latencia −15 %, coste −12 %, groundedness 92,8 → 75,2 %). | Módulo 15 · Anthropic Engineering (2025): evaluación del estado final y trayectoria (leído en la fuente) |
| 02 | **El error de la raíz oculta los errores de los hijos** | Un agente que absorbe un fallo (reintento, disculpa) deja la petición en `ok`: alerta por errores **por tipo de span** (`execute_tool` por herramienta, `chat` por proveedor). | Módulo 02 |
| 02 | **`Status=Ok` es final; deja `Unset` salvo error** | Las librerías no deberían establecer `Ok`: suprime errores posteriores en las herramientas de análisis. | Módulo 02 · especificación de trazas de OpenTelemetry |
| 02 | **Nombres de span de baja cardinalidad** | `execute_tool get_order`, no `…ORD-00012`: el nombre agrupa service maps, span metrics y consultas; el detalle va en atributos. | Módulo 02 · módulo 07 · OTel Semantic Conventions (nombres de span de baja cardinalidad) |
| 03 | **`BatchSpanProcessor` descarta sin hacer ruido** | Cola de 2 048 y lotes de 512: un exportador lento convierte una ráfaga en pérdida de trazas enteras. Vigila `exported vs. dropped`. | Módulo 03 |
| 03 | **El sampler solo ve lo que le das al crear el span** | Un `set_attribute` posterior es invisible para él: los atributos que decidan el muestreo van en la creación. | Módulo 03 · especificación del SDK de trazas |
| 03 | **128 atributos y 128 eventos por span; el SDK descarta los más antiguos** | Un bucle de herramientas que añade `step_N_result` convierte un incidente en un span **truncado**: justo el dato que buscabas. | Módulo 03 |
| 03 | **`record_exception` guarda mensaje y *stacktrace*: ahí se cuela PII** | Una excepción con el correo del cliente en el mensaje acaba en el span y en Loki. | Módulo 03 · módulo 20 |
| 03 | **Las cabeceras HTTP no distinguen mayúsculas; los `dict` sí** | `extract` sobre `dict(headers)` con `Traceparent` crea una traza nueva **sin error alguno**: causa clásica de trazas partidas. | Módulo 03 · módulo 21 (caso E) |
| 04 | **Sumar todos los spans cuenta los tokens N veces** | Cuenta tokens y coste **solo en las hojas `chat`** (los `invoke_agent` repiten el total de sus hijos). Las convenciones GenAI siguen en *Development*: prueba de contrato. | Módulo 04 · módulo 11 |
| 06 | **Solo-auto = trazas huérfanas; los valores por defecto son decisiones de privacidad** | Medido: 66 trazas para 24 tickets y 0 % de tokens atribuibles; OpenLIT/OpenLLMetry capturan contenido por defecto. Una librería por proveedor (dos duplicaron los `chat`: 132 para 66 llamadas). | Módulo 06 |
| 06 | **El `0` falso es peor que el hueco; los reintentos del SDK son tráfico invisible** | En *streaming* sin `include_usage` se escribe `output_tokens=0`; con `max_retries=2` hubo 86 peticiones y 59 spans `chat`. Pon `max_retries=0` y reintenta tú, con un span por intento. | Módulo 06 |

## Multi-agente y herramientas

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 11 | **`ParentBased` o trazas rotas** | Un sistema con 5 servicios muestreando al 10 % cada uno completa solo ≈ 0,001 % de las trazas (`0,1^5`). | Módulo 11 · especificación del SDK de OpenTelemetry (`ParentBased`) · OTel, *Sampling* (conceptos) |
| 11 | **Un timeout del llamador no cancela al llamado, y los reintentos multiplican** | Amplificación `A=(r+1)^d`; sin plazo propagado el subagente sigue gastando tokens (`zombie_s`) y el reintento paga de nuevo. | Módulo 11 §9 · módulo 21 (caso A) · Google SRE Book cap. 22 · Amazon Builders' Library (Brooker), *Timeouts, retries and backoff with jitter* |
| 11 | **La alucinación se «lava» al sintetizar** | El orquestador reescribe con tono seguro: guarda la calidad **por agente** y propaga `grounded` hacia arriba. | Módulo 11 · módulo 14 · Kim et al. (2025), arXiv:2512.08296 (preprint, 3 versiones; 17,2×/4,4× estables) |
| 12 | **Dos spans por salto y un tercero del agente; `isError` no es un error de protocolo** | Elige **uno** como «la herramienta» para latencia y errores; una alerta solo sobre spans CLIENT de MCP es ciega a `isError`. | Módulo 12 §7 |
| 12 | **`traceparent` en `_meta` es entrada no confiable; la descripción de una herramienta es un prompt** | Un cliente hostil puede forzar `sampled`; un servidor puede cambiar la descripción entre conexiones (*rug pull*): el cambio de huella es una señal barata y observable. | Módulo 12 · módulo 20 · MCP SEP-414 (Final) · Invariant Labs (1-abr-2025), *Tool Poisoning Attacks* |
| 11 | **Con agentes con estado, los errores se componen: registra puntos de reanudación y la versión del agente** | Anthropic reanuda agentes desde donde estaban al fallar y despliega con *rainbow deployments*; sin `checkpoint.id` y `gen_ai.agent.version` en el span no puedes ni reanudar ni atribuir un pico de errores a la versión. | Módulo 11 · Anthropic Engineering (2025), *How we built our multi-agent research system* |
| 12 | **Las claves `traceparent`/`tracestate`/`baggage` de `_meta` van sin prefijo a propósito** | SEP-414 documenta la excepción al prefijo DNS para no romper la correlación traza-log; prefijar la clave parte la traza sin error. | Módulo 12 · MCP SEP-414 (Final, 25-abr-2025) |

## Collector y despliegue

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 00 | **«Listo» no es «arrancado»; un `200` del Collector solo prueba que *aceptó*** | Loki ≈ 17 s, Pyroscope ≈ 1 min. La verificación real es una traza canario de extremo a extremo buscada por `trace_id`. | Módulo 00 |
| 05 | **`memory_limiter` primero, con `GOMEMLIMIT`; rechazar es devolver, no perder, si el cliente reintenta** | Un 503 del limitador es un error no permanente: los datos solo se pierden si el cliente no reintenta. | Módulo 05 · README oficial de `memorylimiterprocessor` (leído el 16-oct-2026: error no permanente, primero en el pipeline, `spike_limit_mib` ≈ 20 %) |
| 05 | **`batch` borra el contexto; el fan-out es síncrono; definir ≠ activar** | Un receptor/exportador sin pipeline se ignora sin error: la causa más habitual de «mis logs no llegan». | Módulo 05 |
| 05 | **La cola se mide en *peticiones*, no en spans** | `queue_size: 1000` con lotes de 512 spans son hasta ≈ 512 000 spans en memoria. | Módulo 05 |
| 05/09 | **`resource_to_telemetry_conversion` es un cañón de cardinalidad (y está obsoleto en 0.162)** | Copia todos los atributos de resource a cada serie: `service.instance.id` por réplica multiplica series. | Módulo 05 · módulo 09 |
| 19 | **`helm lint` no valida la aplicación; las listas se reemplazan, los mapas se fusionan** | Extrae el ConfigMap renderizado y valídalo con el binario; sin `load_balancing` por traceID el 42 % de las trazas interesantes quedaron rotas con 2 réplicas. | Módulo 19 · documentación de Kubernetes (CPU limits = throttling, leída en el repositorio) · OTel, *Scaling the Collector* |
| 19 | **No pongas límites de CPU a un Collector; fija versiones de chart e imagen** | El *throttling* de CFS produce latencia y pérdidas justo en las ráfagas. Helm 4: `--wait=false` está obsoleto. | Módulo 19 · documentación de Kubernetes (CPU limits = throttling, leída en el repositorio) · OTel, *Scaling the Collector* |

## Backends (Tempo, Loki)

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 07 | **El punto ciego de la «hora del span»** | Con la holgura por defecto (2 min) solo 12-14 de 30 trazas aparecían en búsquedas con rango; con 15 min, 30 de 30 a los 20-30 s (`live_store.wal.ingestion_time_range_slack`). | Módulo 07 · documentación de Tempo |
| 07 | **El generador de métricas descarta los spans tardíos** | `metrics_ingestion_time_range_slack` (30 s): se pueden buscar, pero nunca entran en span metrics ni en el service graph. | Módulo 07 |
| 07 | **La búsqueda devuelve «los primeros N»; por identificador es inmediato, por búsqueda con retraso** | Para contar usa TraceQL metrics, no el número de resultados. Medido: décimas de segundo frente a ≈ 15-20 s. | Módulo 07 |
| 07 | **`{A} && {B}` ≠ `{A && B}`; `duration` es la del span, no la de la traza** | Para trazas lentas usa `trace:duration`; el service graph necesita pares CLIENT/SERVER. | Módulo 07 |
| 08 | **`trace_id` como etiqueta es el error n.º 1 de Loki** | Medido: 300 trazas → 300 streams frente a 1 con metadato estructurado. | Módulo 08 · guía de etiquetas de Loki |
| 08 | **Un atributo grande hace que Loki rechace TODA la línea; la structured metadata rompe consultas de métricas** | 64 KB y 128 entradas por línea; `exception.stacktrace` suele pasarse. Agrega siempre con `by (...)`. | Módulo 08 |
| 08 | **No hagas del nivel una etiqueta dinámica; filtros de línea antes que parsers** | La etiqueta parte un stream en hasta 5; `|= "error"` antes de `| json` evita casi todo el coste. | Módulo 08 |

## Métricas y Grafana

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 09 | **El SDK de Python no limita la cardinalidad** | La spec pide 2 000 puntos por métrica con desbordamiento; el SDK de Python no lo implementa (medido): el límite es tu disciplina. | Módulo 09 · especificación de métricas de OpenTelemetry |
| 09 | **Los buckets por defecto mienten; nunca promedies percentiles** | p50 con +58 % de error con buckets de ms usados en segundos; `avg(histogram_quantile)` dio ≈ 5 s frente a ≈ 9 s del p95 correcto. | Módulo 09 |
| 09 | **La temporalidad se decide en el emisor; los histogramas exponenciales no llegan por el exporter `prometheus`** | *Delta* directo a Prometheus = HTTP 500; con 0.162 solo queda `+Inf`, `_sum` y `_count`. | Módulo 09 |
| 09 | **Los nombres de métrica son una API; `service.instance.id` único y estable** | `USD` acaba en el nombre; dos procesos con el mismo id escriben en la misma serie. | Módulo 09 |
| 10 | **El archivo manda… hasta que alguien guarda en la UI; el `uid` es una API** | Con `allowUiUpdates: true` el guardado diverge del repositorio; cambiar el `uid` rompe enlaces y alertas con `__dashboardUid__`. | Módulo 10 |
| 10 | **`noDataState` es una decisión de negocio; un YAML de alertas inválido tumba Grafana** | «Sin datos» puede ser valle de tráfico o telemetría caída. Con `interval: 15s` Grafana no arranca (múltiplo de 10 s). | Módulo 10 · módulo 16 |

## Coste, calidad y SLOs

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 13 | **La entrada incluye la caché… según quién; los multiplicadores de caché no son constantes** | La spec define `input_tokens` con caché; Anthropic lo devuelve sin ella. Pon los multiplicadores en una tabla versionada y valida `cache_read + cache_write ≤ input`. | Módulo 13 · Anthropic, *Prompt caching* (platform.claude.com, leída el 16-oct-2026: 1,25×/2× escritura, 0,1× o menos lectura, mínimos 512-4 096) |
| 13 | **La caché rota multiplica el coste; la unidad económica es el ticket resuelto** | Una marca de tiempo al principio del prompt: 3-4× el coste sano. Los tokens son la verdad; el coste, un derivado reprecificable. | Módulo 13 |
| 14 | **La métrica de la muestra no es la de la población; corrige con sensibilidad y especificidad del juez** | Post-estratifica y aplica Rogan-Gladen (1978); con prevalencia baja un 2 % de falsos positivos puede ser la mayoría de las alarmas. | Módulo 14 · Rogan y Gladen (1978) · Zheng et al. (2023), arXiv:2306.05685 · Panickssery et al. (2024), arXiv:2404.13076 |
| 14 | **Código antes que LLM para lo verificable; el evaluador es otro servicio enlazado, no anidado; cuenta los fallos del juez** | PII, ids e importes se comprueban con regex a coste ≈ 0; el coste del juez no contamina el del agente; si el juez falla, la calidad «mejora» sola. | Módulo 14 · Rogan y Gladen (1978) · Zheng et al. (2023), arXiv:2306.05685 · Panickssery et al. (2024), arXiv:2404.13076 |
| 15 | **Evalúa la trayectoria y compara apareado y simultáneo; fija el tamaño de muestra antes de mirar** | Mirar 20 veces declara regresiones falsas en ≈ 24 % de las comparaciones (SPRT ≈ 3 %). | Módulo 15 · Anthropic Engineering (2025): evaluación del estado final y trayectoria (leído en la fuente) |
| 15 | **El dataset de oro envejece; etiqueta la versión en TODAS las señales** | Pesa por frecuencia real, retira lo obsoleto y añade cada incidente; versión ≈ decenas de valores, no un hash por despliegue. | Módulo 15 · Anthropic Engineering (2025): evaluación del estado final y trayectoria (leído en la fuente) |
| 16 | **Alerta sobre síntomas del usuario, diagnostica por causas** | Una página por «CPU alta» es ruido; una por «el presupuesto se agota en 2 h» es una decisión de negocio. | Módulo 16 · SRE Workbook cap. 5 |
| 16 | **El burn rate es independiente del objetivo; la ventana corta es un interruptor de apagado** | 14,4 sirve para 99 % y 99,99 %; la ventana corta (≈ 1/12 de la larga) evita páginas por incidentes ya resueltos. | Módulo 16 · SRE Workbook cap. 5 |
| 16 | **SLI de muestra uniforme (muestra de caza aparte); una regresión de calidad es una quema lenta** | Medido: la política de ticket (no la de página) ve la regresión (≈ 4×). Bloqueo de despliegue, no página a las 3 a. m. | Módulo 16 · SRE Workbook cap. 5 (14,4×/6×/1×) · SRE Book cap. 4 |
| 16 | **Mide la guardia, no solo el servicio; postmortem sin culpa ≠ sin responsabilidad; congelar solo funciona si se pactó antes** | Páginas por semana, % accionables, TTA; las acciones tienen dueño y plazo; la política de presupuesto se firma antes del incidente. | Módulo 16 · Allspaw (2012) |
| 13 | **El punto de equilibrio de la caché depende del TTL: `n* = (w−r)/(1−r)`** | Con 5 min (w=1,25, r=0,1) basta 1 reutilización (n*≈1,28); con 1 h (w=2) hacen falta ≥ 3 usos (n*≈2,11; con 2 usos pagas ≈ 5 % más). | Módulo 13 · Anthropic, *Prompt caching* (multiplicadores; cálculo del curso) |
| 14 | **Con ~20 casos solo ves efectos de ≥ 15-30 puntos** | `min_detectable_drop(20, p0)`: ≈ 15 (base 97 %), 27 (90 %), 32 (85 %); con 120 casos, 6-13; con 500, 3-6. Una muestra de arranque no es una compuerta de regresión. | Módulo 14 · módulo 15 (medido) · Anthropic Engineering (2025) |
| 15 | **Haz un A/A antes del A/B y usa inferencia válida si vas a mirar siempre** | Un A/A que dispara > 5 % de falsos positivos invalida juez, reparto o etiquetado; los p-valores siempre válidos (mSPRT) controlan el error con mirada continua a cambio de potencia. | Módulo 15 · Kohavi, Tang y Xu (2020) · Johari et al. (KDD '17) |
| 16 | **Cultura de guardia con números: ≥ 50 % ingeniería, ≤ 25 % guardia, ≤ 2 incidentes por turno** | Cada incidente completo consume del orden de 6 h (diagnóstico, mitigación, postmortem, arreglos): por encima de 2 por turno no hay tiempo de aprender. | Módulo 16 · Google SRE Book cap. 11 (cifras confirmadas por búsqueda) |

## Rendimiento y escala

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 17 | **El profiler de Python escrito en Python miente un poco; mide antes de optimizar** | 1 000 Hz pedidos dieron ≈ 300 Hz efectivos; el escaneo de PII era el 68 % de la CPU, no la serialización. | Módulo 17 · Ren et al. (2010), *Google-Wide Profiling* · Gregg (2016), *The Flame Graph* |
| 17 | **Self ≠ total; elimina trabajo, no solo constantes** | Regex ≈ ×2; caché por línea ≈ ×4-6; el cuello de botella migra: planifica varias rondas con perfil diferencial. | Módulo 17 · Ren et al. (2010), *Google-Wide Profiling* · Gregg (2016), *The Flame Graph* |
| 18 | **Métricas antes, trazas después** | Las métricas derivadas de spans ya muestreados están sesgadas (tasa de error 2,6 % → ≈ 12 %): RED en `traces/in`. | Módulo 18 · README de `tailsamplingprocessor` v0.162.0 · Sigelman et al. (2010), *Dapper* · Horvitz y Thompson (1952) |
| 18 | **El modo de fallo del tail sampling es silencioso; `numeric_attribute` es de enteros** | `num_traces` insuficiente: 1 300 de 1 500 trazas perdidas sin error; un atributo decimal con `numeric_attribute` hace caer el Collector 0.162.0 (SIGSEGV): usa `ottl_condition`. | Módulo 18 · README de `tailsamplingprocessor` v0.162.0 · Sigelman et al. (2010), *Dapper* · Horvitz y Thompson (1952) |
| 18 | **El coste de las métricas está en las series; los logs dependen de las trazas; sin presupuesto una política es una opinión** | ≈ 1-3 KB de RAM por serie (medido). Un `trace_id` colgando por muestreo desigual rompe el salto de Grafana. | Módulo 18 · README de `tailsamplingprocessor` v0.162.0 · Sigelman et al. (2010), *Dapper* · Horvitz y Thompson (1952) |
| 17 | **El eje X de un flamegraph no es el tiempo** | La anchura es la proporción de muestras y el orden alfabético solo sirve para fusionar; para el orden temporal usa trazas o FlameScope. | Módulo 17 · Gregg (2016), CACM 59(6) |
| 18 | **`sample_limit` convierte una explosión de cardinalidad en un apagón de métricas** | Si un objetivo supera el límite tras el relabeling, **todo el scrape** se trata como fallido: ni métricas ni alertas de ese objetivo. Vigila `scrape_sample_limit` frente a lo scrapeado. | Módulo 18 · documentación de configuración de Prometheus (leída en el repositorio) |
| 19 | **El tail sampling reparte por `traceID`; `span_metrics` y el service graph tienen otra afinidad** | Calcular RED después de repartir por traza deja a cada réplica con fragmentos de serie o con la mitad de los pares cliente/servidor. | Módulo 19 · OTel, *Scaling the Collector* · Grafana, *Scale Alloy tail sampling* (búsqueda) |

## Privacidad y seguridad

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 20 | **Los logs fugan más que los spans y el hash sin clave no es anonimización** | Escenario medido: el antipatrón duplica la PII en logs; un seudónimo SHA-256 de un teléfono se recupera en menos de 1 s con el prefijo conocido. `hmac-sha256` + clave ≥ 32 bytes. | Módulo 20 · README del procesador `redaction` |
| 20 | **`allowed_keys` falla cerrado; redactar en el Collector no protege lo que no pasa por él** | Con una lista de 8 claves desaparecieron 23 de 31 atributos de span; logs enviados directos a Loki esquivan el procesador. | Módulo 20 · README de `redactionprocessor` v0.162.0 · Greshake et al. (2023) · Willison (2025) |
| 20 | **El detector de inyección es una alarma de humo; el monitor de comportamiento sobrevive a la ofuscación** | Paráfrasis y otros idiomas pasan (recall 0); «`issue_refund` sin `get_order` previo» marcó 15 de 16 secuestros con precisión 1,0 sin leer el prompt. | Módulo 20 · Greshake et al. (2023) |
| 20 | **Mide la «triple letal» por traza y recuerda que seudonimizar no saca el dato de la normativa** | Datos privados + contenido no fiable + salida externa en la misma traza es una deuda de seguridad medible sin leer contenido; el considerando 26 del RGPD mantiene los seudónimos como datos personales. | Módulo 20 · Willison (2025) · RGPD cons. 26 / WP29 05/2014 (no abiertos desde el sandbox) |

## Depuración de producción

| Módulo | Secreto | Por qué importa / medido | Fuente |
|---|---|---|---|
| 21 | **Una subida de coste sin errores es un bucle hasta que se demuestre lo contrario** | Mira la forma de la traza (nº de `execute_tool` idénticos seguidos) antes que el modelo: el bucle cuadruplica el coste de un ticket (caso B). | Módulo 21 · Majors, Fong-Jones y Miranker (2022), *Observability Engineering* · SRE Book caps. 12-15 |
| 21 | **Las buenas noticias también son síntomas** | Latencia y coste a la baja con valoraciones negativas al alza: algo dejó de hacerse (regresión silenciosa, caso C). | Módulo 15 · módulo 21 |
| 21 | **Un registro de cambios sin ruido no existe: correlación temporal ≠ causa** | En cada caso hay 3-4 cambios plausibles; el que sirve es el que **predice la forma** del síntoma (qué servicio, qué etiqueta, qué versión). | Módulo 21 · Majors, Fong-Jones y Miranker (2022), *Observability Engineering* · SRE Book caps. 12-15 |
| 21 | **Compara contra el denominador antes de culpar al tráfico** | Si las peticiones son planas y las series se multiplican por 6, no es carga: es una etiqueta (caso D). | Módulo 21 · módulo 18 |
| 21 | **`trazas por ticket ≠ 1` es una alarma barata de contexto perdido** | Un contrato de telemetría de una línea (`n_traces == n_tickets` en una prueba canario) evita semanas de trazas partidas (caso E). | Módulo 21 · módulo 11 |
| 21 | **Mitiga primero y mide por separado el tiempo hasta mitigar y hasta causa** | Optimizar solo el segundo premia cerrar tarde. Los cambios son un buen a priori (≈ 70 % de las interrupciones según el libro de SRE), no un veredicto. | Módulo 21 · Google SRE Book caps. 1 y 12-14 (cifra confirmada por citas; capítulos por conocimiento) |

---
Total: 74 secretos. Generado por `_tools/builders/build_21.py`.
