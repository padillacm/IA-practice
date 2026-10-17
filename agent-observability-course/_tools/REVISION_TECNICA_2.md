# Revisión técnica 2 (R2)

Cada revisor añade su sección. Esta es la de **módulos 08-14** (`rev-tecnico-08-14`).

## Módulos 08-14 · método
Lectura de los builders y de `supportops/` + ejecución de las lecciones y proyectos con nbclient (modo degradado) + validación con binarios oficiales en
puertos aleatorios (sin tocar el stack compartido): Loki 3.7.8 (`-verify-config` y consultas LogQL reales), Collector contrib 0.162.0 (`validate` y arranque),
Prometheus v3.15.0 (`promtool check config` y PromQL real), Tempo 3.1.0 (TraceQL real) y un Grafana 13.2.4 efímero en Docker (provisioning de dashboards y
alertas, `dashkit.query_check` sobre los dashboards 08-14 y estado de las reglas de alerta). Atributos GenAI/MCP contrastados con `semantic-conventions-genai`.

## Arreglado
| Módulo | Problema | Arreglo |
|---|---|---|
| stack/loki | `limits_config.retention_period: 168h` **no borraba nada**: sin `compactor.retention_enabled: true` (+ `delete_request_store`) Loki no aplica retención. El módulo 08 lo describía como efectiva | Añadido el bloque `compactor` (validado con `loki -verify-config`) y aclarada la fila de la tabla del 08 |
| 08 | Texto de «En producción» hablaba del exportador `otlphttp` (en 0.162 es `otlp_http`, como dice la sección de conexión y el `config.yaml`) | Corregido |
| 11 | `supportops.multiagent.critical_path` solo seguía al hijo que termina el último en cada nivel: devolvía `workflow → orquestador → chat(síntesis)`, no la cadena `enrutar → pre-chequeo más lento → facturación → sintetizar` que la sección 5 explica y que sostiene la latencia | Reescrito (recorrido hacia atrás por la ventana de cada span; las ramas paralelas más cortas quedan fuera). La celda ahora imprime la cadena y comprueba que su suma ≈ latencia real; test nuevo en `test_multiagent.py` |
| 11 | Cifras de arXiv:2512.08296 (39-70 %, 17×/4×) son de la **v1**; la v2 revisó el estudio | Se indica la versión y se rebaja a «señal, no ley» |
| 13 | «Caché rota: se pierde casi todo el ahorro»: lo medido es 0,67× del coste sin caché (se pierde más de la mitad del ahorro, no casi todo); «200×» de cardinalidad no coincidía con los 69 clientes del lote; la FinOps Foundation no define «visibilidad/asignación/optimización» como tres pasos | Textos y títulos de gráfico ajustados |
| 14 | Texto de la sonda de verbosidad decía 0,5 → 0,65, y con `FAST_DEV_RUN` (14 casos) se mide 0,62 → 0,83; «mi primera versión…» en primera persona | Texto coherente con lo medido y explicado el efecto del tamaño de muestra |
| 09, 10, 12 | Sin errores técnicos encontrados: fórmulas (`rate` con extrapolación, `histogram_quantile`, burn rate, break-even de caché, Wilson, Rogan-Gladen, post-estratificación), nombres de métricas tras la traducción a Prometheus, alertas provisionadas (reglas en `ok`), dashboards (todas las consultas ejecutan; las que salen vacías lo hacen por falta de datos de ese escenario) y atributos `mcp.*`/`gen_ai.evaluation.*` coinciden con la spec | Solo progreso |

## Recomendaciones (no aplicadas)
1. **Dashboard 14, «Calidad estimada»**: la consulta post-estratificada deja fuera del numerador los estratos sin evaluaciones en la ventana pero los mantiene en el denominador
   (`sum(rate(population))`); con ventanas cortas o estratos raros (p. ej. `error`) subestima la calidad. Mejor normalizar con `sum(population de estratos evaluados)`.
2. **Dashboard 13, panel «Desvío» (actual / hace 1 h)** no muestra nada en la primera hora de datos (esperable) y la alerta provisionada con `finops_alert_rule_json` se crea por API
   desde la lección, no por provisioning: moverla a `stack/grafana/provisioning/alerting/` daría un comportamiento reproducible.
3. **Acoplamiento a puertos fijos**: `supportops.stack.services()` solo se puede redirigir con `STACK_HOST` (no por puerto). Varias validaciones paralelas (CI, otros revisores)
   chocan en el mismo daemon; permitir `SUPPORTOPS_PORT_OFFSET` o variables por servicio facilitaría pruebas con puertos aleatorios.
4. **Referencias no verificables desde el entorno de construcción** (dominios no GitHub bloqueados por el proxy): las URL de grafana.com, opentelemetry.io, sre.google, w3.org,
   arxiv.org, invariantlabs.ai y elastic.co se comprobaron solo con búsqueda web (SEP-414, Elastic, arXiv 2512.08296, FinOps Foundation: existen); el resto de URL de GitHub
   (raw) responden 200.
5. El `loki.yaml` del laboratorio sigue sin `limits_config.otlp_config` explícito; si el curso quiere enseñar el mapeo de atributos de resource a etiquetas (módulo 08, sección 3) convendría
   fijarlo en la config en lugar de depender del valor por defecto de la versión.

## No verificado
- Stack completo con Docker Compose (los puertos fijos estaban ocupados por otros revisores): se usaron binarios nativos y un Grafana efímero con datasources apuntando a ellos.
- Comportamiento de proveedores LLM reales (todo es `mock`); precios y multiplicadores de caché son ilustrativos (los multiplicadores de Anthropic citados coinciden con su documentación, pero cambian).
- Capturas `img/*.png` (no re-generadas).
