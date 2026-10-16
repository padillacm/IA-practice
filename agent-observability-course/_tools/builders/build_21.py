"""Genera el módulo 21_elite_playbook: README, lección, proyecto («mesa de incidentes»), COMPENDIO_SECRETOS.md y dashboard 21.
Ejecutar desde la raíz del repo:  python agent-observability-course/_tools/builders/build_21.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _a1_common import COURSE, IMPORTS, box, boot, details, hint, nb_for, observe  # noqa: E402

MOD = "21_elite_playbook"
DASH_UID = "sala-de-guerra"

# =====================================================================================================================
# COMPENDIO de secretos de élite (módulos 00-21): (tema, módulo, secreto, por qué importa / cifra medida, fuente)
# Las cifras «medido» salen de las lecciones del curso (mock, semilla 42) y están referenciadas a su módulo; las fuentes externas son las que ese módulo cita.
# =====================================================================================================================
COMPENDIUM: list[tuple[str, str, str, str, str]] = [
    # ---------------------------------------------------------------- instrumentación y datos
    ("Instrumentación", "01", "La unidad de coste y de fallo es el *paso*, no la petición", "Dos peticiones idénticas pueden costar 1× y 6×: pon `max_steps` **y** un tope de tokens/coste por petición.", "Módulo 01 · módulo 13"),
    ("Instrumentación", "01", "Los reintentos enmascaran fallos", "Un `llm_error` transitorio acaba en `ok`; cuenta **intentos**, no solo resultados finales, o no verás degradarse al proveedor hasta que se agoten.", "Módulo 01 · módulo 16"),
    ("Instrumentación", "01/12", "Las herramientas con efectos deben ser idempotentes", "Reintentar tras un timeout puede reembolsar dos veces (medido en el módulo 12: 2 reembolsos por 1 intención). Clave de idempotencia registrada en el span del servidor.", "Módulo 12 §8"),
    ("Instrumentación", "01/15", "«Más rápido y más barato» puede ser peor", "Una alucinación no llama herramientas: vigila `tool_calls` por petición como señal de salud (módulo 15: latencia −15 %, coste −12 %, groundedness 92,8 → 75,2 %).", "Módulo 15"),
    ("Instrumentación", "02", "El error de la raíz oculta los errores de los hijos", "Un agente que absorbe un fallo (reintento, disculpa) deja la petición en `ok`: alerta por errores **por tipo de span** (`execute_tool` por herramienta, `chat` por proveedor).", "Módulo 02"),
    ("Instrumentación", "02", "`Status=Ok` es final; deja `Unset` salvo error", "Las librerías no deberían establecer `Ok`: suprime errores posteriores en las herramientas de análisis.", "Módulo 02 · especificación de trazas de OpenTelemetry"),
    ("Instrumentación", "02", "Nombres de span de baja cardinalidad", "`execute_tool get_order`, no `…ORD-00012`: el nombre agrupa service maps, span metrics y consultas; el detalle va en atributos.", "Módulo 02 · módulo 07"),
    ("Instrumentación", "03", "`BatchSpanProcessor` descarta sin hacer ruido", "Cola de 2 048 y lotes de 512: un exportador lento convierte una ráfaga en pérdida de trazas enteras. Vigila `exported vs. dropped`.", "Módulo 03"),
    ("Instrumentación", "03", "El sampler solo ve lo que le das al crear el span", "Un `set_attribute` posterior es invisible para él: los atributos que decidan el muestreo van en la creación.", "Módulo 03 · especificación del SDK de trazas"),
    ("Instrumentación", "03", "128 atributos y 128 eventos por span; el SDK descarta los más antiguos", "Un bucle de herramientas que añade `step_N_result` convierte un incidente en un span **truncado**: justo el dato que buscabas.", "Módulo 03"),
    ("Instrumentación", "03", "`record_exception` guarda mensaje y *stacktrace*: ahí se cuela PII", "Una excepción con el correo del cliente en el mensaje acaba en el span y en Loki.", "Módulo 03 · módulo 20"),
    ("Instrumentación", "03", "Las cabeceras HTTP no distinguen mayúsculas; los `dict` sí", "`extract` sobre `dict(headers)` con `Traceparent` crea una traza nueva **sin error alguno**: causa clásica de trazas partidas.", "Módulo 03 · módulo 21 (caso E)"),
    ("Instrumentación", "04", "Sumar todos los spans cuenta los tokens N veces", "Cuenta tokens y coste **solo en las hojas `chat`** (los `invoke_agent` repiten el total de sus hijos). Las convenciones GenAI siguen en *Development*: prueba de contrato.", "Módulo 04 · módulo 11"),
    ("Instrumentación", "06", "Solo-auto = trazas huérfanas; los valores por defecto son decisiones de privacidad", "Medido: 66 trazas para 24 tickets y 0 % de tokens atribuibles; OpenLIT/OpenLLMetry capturan contenido por defecto. Una librería por proveedor (dos duplicaron los `chat`: 132 para 66 llamadas).", "Módulo 06"),
    ("Instrumentación", "06", "El `0` falso es peor que el hueco; los reintentos del SDK son tráfico invisible", "En *streaming* sin `include_usage` se escribe `output_tokens=0`; con `max_retries=2` hubo 86 peticiones y 59 spans `chat`. Pon `max_retries=0` y reintenta tú, con un span por intento.", "Módulo 06"),
    ("Multi-agente y herramientas", "11", "`ParentBased` o trazas rotas", "Un sistema con 5 servicios muestreando al 10 % cada uno completa solo ≈ 0,001 % de las trazas (`0,1^5`).", "Módulo 11 · especificación del SDK (muestreadores)"),
    ("Multi-agente y herramientas", "11", "Un timeout del llamador no cancela al llamado, y los reintentos multiplican", "Amplificación `A=(r+1)^d`; sin plazo propagado el subagente sigue gastando tokens (`zombie_s`) y el reintento paga de nuevo.", "Módulo 11 §9 · módulo 21 (caso A)"),
    ("Multi-agente y herramientas", "11", "La alucinación se «lava» al sintetizar", "El orquestador reescribe con tono seguro: guarda la calidad **por agente** y propaga `grounded` hacia arriba.", "Módulo 11 · módulo 14"),
    ("Multi-agente y herramientas", "12", "Dos spans por salto y un tercero del agente; `isError` no es un error de protocolo", "Elige **uno** como «la herramienta» para latencia y errores; una alerta solo sobre spans CLIENT de MCP es ciega a `isError`.", "Módulo 12 §7"),
    ("Multi-agente y herramientas", "12", "`traceparent` en `_meta` es entrada no confiable; la descripción de una herramienta es un prompt", "Un cliente hostil puede forzar `sampled`; un servidor puede cambiar la descripción entre conexiones (*rug pull*): el cambio de huella es una señal barata y observable.", "Módulo 12 · módulo 20"),
    # ---------------------------------------------------------------- Collector y despliegue
    ("Collector y despliegue", "00", "«Listo» no es «arrancado»; un `200` del Collector solo prueba que *aceptó*", "Loki ≈ 17 s, Pyroscope ≈ 1 min. La verificación real es una traza canario de extremo a extremo buscada por `trace_id`.", "Módulo 00"),
    ("Collector y despliegue", "05", "`memory_limiter` primero, con `GOMEMLIMIT`; rechazar es devolver, no perder, si el cliente reintenta", "Un 503 del limitador es un error no permanente: los datos solo se pierden si el cliente no reintenta.", "Módulo 05 · documentación del Collector"),
    ("Collector y despliegue", "05", "`batch` borra el contexto; el fan-out es síncrono; definir ≠ activar", "Un receptor/exportador sin pipeline se ignora sin error: la causa más habitual de «mis logs no llegan».", "Módulo 05"),
    ("Collector y despliegue", "05", "La cola se mide en *peticiones*, no en spans", "`queue_size: 1000` con lotes de 512 spans son hasta ≈ 512 000 spans en memoria.", "Módulo 05"),
    ("Collector y despliegue", "05/09", "`resource_to_telemetry_conversion` es un cañón de cardinalidad (y está obsoleto en 0.162)", "Copia todos los atributos de resource a cada serie: `service.instance.id` por réplica multiplica series.", "Módulo 05 · módulo 09"),
    ("Collector y despliegue", "19", "`helm lint` no valida la aplicación; las listas se reemplazan, los mapas se fusionan", "Extrae el ConfigMap renderizado y valídalo con el binario; sin `load_balancing` por traceID el 42 % de las trazas interesantes quedaron rotas con 2 réplicas.", "Módulo 19"),
    ("Collector y despliegue", "19", "No pongas límites de CPU a un Collector; fija versiones de chart e imagen", "El *throttling* de CFS produce latencia y pérdidas justo en las ráfagas. Helm 4: `--wait=false` está obsoleto.", "Módulo 19"),
    # ---------------------------------------------------------------- backends
    ("Backends (Tempo, Loki)", "07", "El punto ciego de la «hora del span»", "Con la holgura por defecto (2 min) solo 12-14 de 30 trazas aparecían en búsquedas con rango; con 15 min, 30 de 30 a los 20-30 s (`live_store.wal.ingestion_time_range_slack`).", "Módulo 07 · documentación de Tempo"),
    ("Backends (Tempo, Loki)", "07", "El generador de métricas descarta los spans tardíos", "`metrics_ingestion_time_range_slack` (30 s): se pueden buscar, pero nunca entran en span metrics ni en el service graph.", "Módulo 07"),
    ("Backends (Tempo, Loki)", "07", "La búsqueda devuelve «los primeros N»; por identificador es inmediato, por búsqueda con retraso", "Para contar usa TraceQL metrics, no el número de resultados. Medido: décimas de segundo frente a ≈ 15-20 s.", "Módulo 07"),
    ("Backends (Tempo, Loki)", "07", "`{A} && {B}` ≠ `{A && B}`; `duration` es la del span, no la de la traza", "Para trazas lentas usa `trace:duration`; el service graph necesita pares CLIENT/SERVER.", "Módulo 07"),
    ("Backends (Tempo, Loki)", "08", "`trace_id` como etiqueta es el error n.º 1 de Loki", "Medido: 300 trazas → 300 streams frente a 1 con metadato estructurado.", "Módulo 08 · guía de etiquetas de Loki"),
    ("Backends (Tempo, Loki)", "08", "Un atributo grande hace que Loki rechace TODA la línea; la structured metadata rompe consultas de métricas", "64 KB y 128 entradas por línea; `exception.stacktrace` suele pasarse. Agrega siempre con `by (...)`.", "Módulo 08"),
    ("Backends (Tempo, Loki)", "08", "No hagas del nivel una etiqueta dinámica; filtros de línea antes que parsers", "La etiqueta parte un stream en hasta 5; `|= \"error\"` antes de `| json` evita casi todo el coste.", "Módulo 08"),
    # ---------------------------------------------------------------- métricas y Grafana
    ("Métricas y Grafana", "09", "El SDK de Python no limita la cardinalidad", "La spec pide 2 000 puntos por métrica con desbordamiento; el SDK de Python no lo implementa (medido): el límite es tu disciplina.", "Módulo 09 · especificación de métricas de OpenTelemetry"),
    ("Métricas y Grafana", "09", "Los buckets por defecto mienten; nunca promedies percentiles", "p50 con +58 % de error con buckets de ms usados en segundos; `avg(histogram_quantile)` dio ≈ 5 s frente a ≈ 9 s del p95 correcto.", "Módulo 09"),
    ("Métricas y Grafana", "09", "La temporalidad se decide en el emisor; los histogramas exponenciales no llegan por el exporter `prometheus`", "*Delta* directo a Prometheus = HTTP 500; con 0.162 solo queda `+Inf`, `_sum` y `_count`.", "Módulo 09"),
    ("Métricas y Grafana", "09", "Los nombres de métrica son una API; `service.instance.id` único y estable", "`USD` acaba en el nombre; dos procesos con el mismo id escriben en la misma serie.", "Módulo 09"),
    ("Métricas y Grafana", "10", "El archivo manda… hasta que alguien guarda en la UI; el `uid` es una API", "Con `allowUiUpdates: true` el guardado diverge del repositorio; cambiar el `uid` rompe enlaces y alertas con `__dashboardUid__`.", "Módulo 10"),
    ("Métricas y Grafana", "10", "`noDataState` es una decisión de negocio; un YAML de alertas inválido tumba Grafana", "«Sin datos» puede ser valle de tráfico o telemetría caída. Con `interval: 15s` Grafana no arranca (múltiplo de 10 s).", "Módulo 10 · módulo 16"),
    # ---------------------------------------------------------------- coste, calidad y SLOs
    ("Coste, calidad y SLOs", "13", "La entrada incluye la caché… según quién; los multiplicadores de caché no son constantes", "La spec define `input_tokens` con caché; Anthropic lo devuelve sin ella. Pon los multiplicadores en una tabla versionada y valida `cache_read + cache_write ≤ input`.", "Módulo 13 · documentación de *prompt caching*"),
    ("Coste, calidad y SLOs", "13", "La caché rota multiplica el coste; la unidad económica es el ticket resuelto", "Una marca de tiempo al principio del prompt: 3-4× el coste sano. Los tokens son la verdad; el coste, un derivado reprecificable.", "Módulo 13"),
    ("Coste, calidad y SLOs", "14", "La métrica de la muestra no es la de la población; corrige con sensibilidad y especificidad del juez", "Post-estratifica y aplica Rogan-Gladen (1978); con prevalencia baja un 2 % de falsos positivos puede ser la mayoría de las alarmas.", "Módulo 14"),
    ("Coste, calidad y SLOs", "14", "Código antes que LLM para lo verificable; el evaluador es otro servicio enlazado, no anidado; cuenta los fallos del juez", "PII, ids e importes se comprueban con regex a coste ≈ 0; el coste del juez no contamina el del agente; si el juez falla, la calidad «mejora» sola.", "Módulo 14"),
    ("Coste, calidad y SLOs", "15", "Evalúa la trayectoria y compara apareado y simultáneo; fija el tamaño de muestra antes de mirar", "Mirar 20 veces declara regresiones falsas en ≈ 24 % de las comparaciones (SPRT ≈ 3 %).", "Módulo 15"),
    ("Coste, calidad y SLOs", "15", "El dataset de oro envejece; etiqueta la versión en TODAS las señales", "Pesa por frecuencia real, retira lo obsoleto y añade cada incidente; versión ≈ decenas de valores, no un hash por despliegue.", "Módulo 15"),
    ("Coste, calidad y SLOs", "16", "Alerta sobre síntomas del usuario, diagnostica por causas", "Una página por «CPU alta» es ruido; una por «el presupuesto se agota en 2 h» es una decisión de negocio.", "Módulo 16 · SRE Workbook cap. 5"),
    ("Coste, calidad y SLOs", "16", "El burn rate es independiente del objetivo; la ventana corta es un interruptor de apagado", "14,4 sirve para 99 % y 99,99 %; la ventana corta (≈ 1/12 de la larga) evita páginas por incidentes ya resueltos.", "Módulo 16 · SRE Workbook cap. 5"),
    ("Coste, calidad y SLOs", "16", "SLI de muestra uniforme (muestra de caza aparte); una regresión de calidad es una quema lenta", "Medido: la política de ticket (no la de página) ve la regresión (≈ 4×). Bloqueo de despliegue, no página a las 3 a. m.", "Módulo 16"),
    ("Coste, calidad y SLOs", "16", "Mide la guardia, no solo el servicio; postmortem sin culpa ≠ sin responsabilidad; congelar solo funciona si se pactó antes", "Páginas por semana, % accionables, TTA; las acciones tienen dueño y plazo; la política de presupuesto se firma antes del incidente.", "Módulo 16 · Allspaw (2012)"),
    # ---------------------------------------------------------------- rendimiento y escala
    ("Rendimiento y escala", "17", "El profiler de Python escrito en Python miente un poco; mide antes de optimizar", "1 000 Hz pedidos dieron ≈ 300 Hz efectivos; el escaneo de PII era el 68 % de la CPU, no la serialización.", "Módulo 17"),
    ("Rendimiento y escala", "17", "Self ≠ total; elimina trabajo, no solo constantes", "Regex ≈ ×1,5-2; caché por línea ≈ ×5-6; el cuello de botella migra: planifica varias rondas con perfil diferencial.", "Módulo 17"),
    ("Rendimiento y escala", "18", "Métricas antes, trazas después", "Las métricas derivadas de spans ya muestreados están sesgadas (tasa de error 2,6 % → ≈ 12 %): RED en `traces/in`.", "Módulo 18"),
    ("Rendimiento y escala", "18", "El modo de fallo del tail sampling es silencioso; `numeric_attribute` es de enteros", "`num_traces` insuficiente: 1 300 de 1 500 trazas perdidas sin error; un atributo decimal con `numeric_attribute` hace caer el Collector 0.162.0 (SIGSEGV): usa `ottl_condition`.", "Módulo 18"),
    ("Rendimiento y escala", "18", "El coste de las métricas está en las series; los logs dependen de las trazas; sin presupuesto una política es una opinión", "≈ 1-3 KB de RAM por serie (medido). Un `trace_id` colgando por muestreo desigual rompe el salto de Grafana.", "Módulo 18"),
    # ---------------------------------------------------------------- privacidad y seguridad
    ("Privacidad y seguridad", "20", "Los logs fugan más que los spans y el hash sin clave no es anonimización", "Escenario medido: el antipatrón duplica la PII en logs; un seudónimo SHA-256 de un teléfono se recupera en menos de 1 s con el prefijo conocido. `hmac-sha256` + clave ≥ 32 bytes.", "Módulo 20 · README del procesador `redaction`"),
    ("Privacidad y seguridad", "20", "`allowed_keys` falla cerrado; redactar en el Collector no protege lo que no pasa por él", "Con una lista de 8 claves desaparecieron 23 de 31 atributos de span; logs enviados directos a Loki esquivan el procesador.", "Módulo 20"),
    ("Privacidad y seguridad", "20", "El detector de inyección es una alarma de humo; el monitor de comportamiento sobrevive a la ofuscación", "Paráfrasis y otros idiomas pasan (recall 0); «`issue_refund` sin `get_order` previo» marcó 15 de 16 secuestros con precisión 1,0 sin leer el prompt.", "Módulo 20 · Greshake et al. (2023)"),
    # ---------------------------------------------------------------- depuración de producción (este módulo)
    ("Depuración de producción", "21", "Una subida de coste sin errores es un bucle hasta que se demuestre lo contrario", "Mira la forma de la traza (nº de `execute_tool` idénticos seguidos) antes que el modelo: el bucle cuadruplica el coste de un ticket (caso B).", "Módulo 21"),
    ("Depuración de producción", "21", "Las buenas noticias también son síntomas", "Latencia y coste a la baja con valoraciones negativas al alza: algo dejó de hacerse (regresión silenciosa, caso C).", "Módulo 15 · módulo 21"),
    ("Depuración de producción", "21", "Un registro de cambios sin ruido no existe: correlación temporal ≠ causa", "En cada caso hay 3-4 cambios plausibles; el que sirve es el que **predice la forma** del síntoma (qué servicio, qué etiqueta, qué versión).", "Módulo 21"),
    ("Depuración de producción", "21", "Compara contra el denominador antes de culpar al tráfico", "Si las peticiones son planas y las series se multiplican por 6, no es carga: es una etiqueta (caso D).", "Módulo 21 · módulo 18"),
    ("Depuración de producción", "21", "`trazas por ticket ≠ 1` es una alarma barata de contexto perdido", "Un contrato de telemetría de una línea (`n_traces == n_tickets` en una prueba canario) evita semanas de trazas partidas (caso E).", "Módulo 21 · módulo 11"),
]


def build_compendium_md() -> None:
    by: dict[str, list] = {}
    for it in COMPENDIUM:
        by.setdefault(it[0], []).append(it)
    out = ["# Compendio de secretos de élite (módulos 00-21)\n",
           "Recopila y amplía las secciones «🧠 Secretos de la élite» de todas las lecciones. Cada fila: **secreto**, *por qué importa o cifra medida* (laboratorio `mock`, semilla 42, salvo indicación) y **fuente** (módulo del curso y, entre paréntesis implícitos, las referencias que ese módulo cita).\n",
           "> Las cifras proceden de simulaciones deterministas del propio curso; úsalas como órdenes de magnitud, no como constantes universales. Lo marcado *Development* (convenciones GenAI, MCP) cambia entre versiones.\n"]
    for theme, items in by.items():
        out.append(f"\n## {theme}\n\n| Módulo | Secreto | Por qué importa / medido | Fuente |\n|---|---|---|---|")
        for _, mod, sec, why, src in items:
            out.append(f"| {mod} | **{sec}** | {why} | {src} |")
    out.append(f"\n---\nTotal: {len(COMPENDIUM)} secretos. Generado por `_tools/builders/build_21.py`.\n")
    (COURSE / MOD / "COMPENDIO_SECRETOS.md").write_text("\n".join(out), encoding="utf-8")
    print("OK COMPENDIO_SECRETOS.md", len(COMPENDIUM), "secretos")


# =====================================================================================================================
# Dashboard 21 · sala de guerra
# =====================================================================================================================
def build_dashboard() -> None:
    sys.path.insert(0, str(COURSE))
    from supportops.dashkit import Dashboard, lint, logs, prom, stat, table, text, thresholds, timeseries, traces_table
    d = Dashboard(DASH_UID, "21 · Sala de guerra de SupportOps", tags=["curso", "incidentes", "playbook"], time_from="now-30m",
                  description="Las preguntas del bucle de análisis (¿qué cambió?, ¿a quién afecta?, ¿desde cuándo?, ¿qué señal discrepa?) como un único tablero para incidentes de agentes.")
    d.add(text("Cómo usar esta sala", "Lee de **izquierda a derecha y de arriba abajo**: (1) ¿hay síntoma de usuario (latencia, errores, coste)? (2) ¿qué **forma** tiene el síntoma: bucle (coste ↑, pasos por ticket ↑), cascada (intentos de delegación ↑), regresión silenciosa (pasos por ticket ↓ con latencia/coste ↓), "
               "cardinalidad (series activas ↑ con tráfico plano) o trazas partidas (trazas raíz de subagentes)? (3) salta a una traza con los enlaces de las tablas. Cada panel explica el patrón que vigila.", h=3))
    d.row("Señales de usuario (las cuatro doradas del agente)")
    d.add(stat("p95 de invoke_agent (5 min)", 'histogram_quantile(0.95, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket{service_name="supportops-agent"}[5m])))', unit="s", w=6, h=4,
               thr=thresholds((None, "green"), (5, "orange"), (10, "red")), description="Latencia de extremo a extremo del agente. Sube en cascadas y bucles."),
          stat("Tickets malos (5 min)", 'sum(rate(supportops_agent_requests_total{service_name="supportops-agent",supportops_status=~"error|degraded|max_steps"}[5m])) / sum(rate(supportops_agent_requests_total{service_name="supportops-agent"}[5m]))', unit="percentunit", w=6, h=4,
               thr=thresholds((None, "green"), (0.02, "orange"), (0.1, "red")), description="Fracción de tickets en error, degradado o max_steps."),
          stat("Coste por ticket (5 min)", 'sum(rate(supportops_agent_request_cost_USD_sum{service_name="supportops-agent"}[5m])) / sum(rate(supportops_agent_request_cost_USD_count{service_name="supportops-agent"}[5m]))', unit="currencyUSD", w=6, h=4, decimals=5,
               description="Coste medio por ticket (precios ilustrativos). Sube con bucles y reintentos; baja en regresiones silenciosas."),
          stat("Herramientas por ticket (p50)", 'histogram_quantile(0.5, sum by (le) (rate(gen_ai_invoke_agent_tool_calls_bucket{service_name="supportops-agent"}[5m])))', unit="none", w=6, h=4, decimals=1,
               description="Mediana de llamadas a herramientas por ticket: una caída brusca con latencia y coste a la baja es una regresión silenciosa."))
    d.row("Forma del síntoma · ¿bucle, cascada, regresión, cardinalidad o trazas partidas?")
    d.add(timeseries("Latencia p95 y coste por ticket", [prom('histogram_quantile(0.95, sum by (le) (rate(gen_ai_invoke_agent_duration_seconds_bucket{service_name="supportops-agent"}[2m])))', "p95 (s)"),
                                                          prom('1000 * sum(rate(supportops_agent_request_cost_USD_sum{service_name="supportops-agent"}[2m])) / sum(rate(supportops_agent_request_cost_USD_count{service_name="supportops-agent"}[2m]))', "coste por ticket (milésimas de USD)", ref="B")],
                     w=12, h=8, description="Ambos suben a la vez: bucle o reintentos. Solo la latencia: lentitud de una dependencia. Ambos bajan: ¿regresión silenciosa?"),
          timeseries("Pasos (herramientas) por ticket · p10, p50 y p90", [prom(f'histogram_quantile({q}, sum by (le) (rate(gen_ai_invoke_agent_tool_calls_bucket{{service_name="supportops-agent"}}[2m])))', f"p{int(q * 100)}", ref=r) for q, r in ((0.1, "A"), (0.5, "B"), (0.9, "C"))],
                     w=12, h=8, description="El p90 que se dispara = bucle de herramientas; el p10/p50 que cae a 0 = el agente deja de consultar (regresión silenciosa)."))
    d.add(timeseries("Delegaciones por resultado (multi-agente)", [prom('sum by (supportops_outcome) (rate(supportops_delegation_attempts_total[1m]))', "{{supportops_outcome}}")], w=8, h=7,
                     description="Cascada: los intentos `timeout`/`error` crecen y los `ok` no; la amplificación son los reintentos que se suman a la carga."),
          timeseries("Series activas de Prometheus (cardinalidad)", [prom('prometheus_tsdb_head_series', "series en la cabeza")], w=8, h=7,
                     description="Una tormenta de cardinalidad se ve aquí con el tráfico plano. Siguiente paso: `count by (__name__)` para localizar la métrica."),
          table("Métricas con más series (supportops_*)", [prom('topk(8, count by (__name__) ({__name__=~"supportops_.*"}))', "", instant=True, fmt="table")], w=8, h=7,
                description="Qué métrica concentra las series: el culpable de una explosión suele estar arriba."))
    d.row("Saltar a la evidencia (trazas y logs)")
    d.add(traces_table("Candidatos a bucle: ≥ 5 llamadas a herramientas en una traza (Tempo)", '{ name =~ "execute_tool.*" } | count() >= 5', w=12, h=8, description="Trazas con muchas llamadas a herramientas: sospechosas de bucle. Ábrelas y comprueba si repiten la misma."),
          traces_table("Trazas partidas: raíces de subagentes sin orquestador (Tempo)", '{ trace:rootName =~ "invoke_agent (orders|billing|knowledge|escalation)-agent" }', w=12, h=8, description="Si el padre se pierde (propagación rota) la raíz de la traza es un subagente: no debería ocurrir."))
    d.add(logs("Avisos y errores del agente (Loki)", '{service_name="supportops-agent"} | detected_level=~"warn|error"', w=24, h=8, description="Logs de aviso/error con trace_id: el salto de la alerta a la traza."))
    problems = lint(d.to_dict())
    assert not problems, problems
    path = d.save(COURSE / "stack" / "grafana" / "dashboards" / "21-sala-de-guerra.json")
    print("OK dashboard", path.name)


# =====================================================================================================================
# Piezas comunes
# =====================================================================================================================
IMPORTS_21 = """
import collections, dataclasses, json, math, re, statistics, time
import yaml
from IPython.display import Markdown
from supportops import incidents as I
from supportops.telemetry import setup_telemetry, OTelInstrumentor
STACK = check_stack("core+metrics")
LIVE = not STACK.degraded
"""

TOOLS_21 = '''
def find_window(x, min_len=5):
    """Ventana [a, b) cuya media difiere más del resto (estadístico t). Detecta saltos y ventanas aunque el ruido por minuto sea alto (n ≈ 4 tickets/min).
    Si la mejor ventana empieza en 0 se devuelve su complemento (el cambio es «desde b hasta el final»)."""
    x = np.asarray(x, float); n = len(x); sd = x.std() or 1.0
    c = np.concatenate([[0], np.cumsum(x)]); best, win = 0.0, (0, n)
    for a in range(0, n - min_len + 1):
        for b in range(a + min_len, n + 1):
            n_in, n_out = b - a, n - (b - a)
            if n_out < min_len: continue
            m_in, m_out = (c[b] - c[a]) / n_in, (c[n] - (c[b] - c[a])) / n_out
            t = (m_in - m_out) / (sd * np.sqrt(1 / n_in + 1 / n_out))
            if abs(t) > abs(best): best, win = t, (a, b)
    if win[0] == 0 and win[1] < n: win = (win[1], n)
    return win[0], win[1], float(best)

def span_frame(b):
    """Una fila por span con las columnas que más se usan al depurar."""
    rows = []
    for s in b.spans:
        a = s["attributes"]
        rows.append({"trace_id": s["trace_id"], "service": (s.get("resource") or {}).get("service.name"), "name": s["name"], "kind": s["kind"], "status": s["status"], "error_type": a.get("error.type"),
                     "minute": int((s["start_unix_nano"] / 1e9 - b.t0) // 60), "dur_s": (s["end_unix_nano"] - s["start_unix_nano"]) / 1e9, "version": a.get("gen_ai.agent.version"),
                     "intent": a.get("supportops.intent"), "tool": a.get("gen_ai.tool.name"), "tok_in": a.get("gen_ai.usage.input_tokens")})
    return pd.DataFrame(rows)

def bubble_up(df, bad, cols, min_n=5):
    """«Qué atributos están sobre-representados entre los malos»: para cada columna y valor, cuota entre malos / cuota entre buenos (lift)."""
    out = []
    for col in cols:
        pb = df[bad][col].value_counts(normalize=True); pg = df[~bad][col].value_counts(normalize=True)
        nb = df[bad][col].value_counts()
        for v, share in pb.items():
            if nb[v] >= min_n: out.append({"atributo": col, "valor": v, "cuota en malos": round(share, 3), "cuota en buenos": round(pg.get(v, 0.0), 3), "lift": round(share / (pg.get(v, 0.0) + 0.01), 1), "n malos": int(nb[v])})
    return pd.DataFrame(out).sort_values("lift", ascending=False).reset_index(drop=True)

def mark_window(ax, a, b, color="#d64545"):
    ax.axvspan(a, b, color=color, alpha=0.12); ax.axvline(a, color=color, ls="--", lw=1)
'''


# =====================================================================================================================
# LECCIÓN
# =====================================================================================================================
def build_lesson() -> None:
    nb, out = nb_for(MOD, "21_elite_playbook.ipynb", "Módulo 21 · Masterclass de élite: depuración de producción de agentes")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Módulo 21 · Masterclass de élite: depurar agentes en producción con telemetría

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min) |
    | **Servicios de Compose** | Opcional: `--profile core --profile metrics` (sección 9, ≈ 3 min en vivo). Docker para validar dos configuraciones del Collector (sección 5). Sin Docker, todo funciona en **modo degradado** |
    | **RAM aproximada** | < 600 MB sin stack · ≈ 1,2 GB con `core` + `metrics` |
    | **Prerrequisitos** | Todos los módulos anteriores (00-20). Es la síntesis: no hay herramientas nuevas, hay **criterio** |
    | **Hilo conductor** | SupportOps ya tiene instrumentación, backends, SLOs, calidad, coste, escala y privacidad. Hoy aprendes a **usarlos bajo presión**: cinco incidentes reales de la familia que más duele, un método y una cultura |

    > ⚠️ **Honestidad sobre el laboratorio.** Los incidentes salen de **simulaciones deterministas** del agente de SupportOps (`mock`, semilla fija): reproducen la *forma* de cada fallo (cascada de reintentos, bucle de herramientas, regresión silenciosa, tormenta de cardinalidad, trazas partidas)
    > con telemetría real del SDK de OpenTelemetry, pero **no son sistemas reales**: el número de tickets por minuto es bajo (≈ 4) y el ruido, por tanto, alto, y los valores de memoria/duración de *scrape* del caso D son un modelo simple. Los ejemplos resueltos de esta lección son **variantes
    > distintas** de los del proyecto (otro agente afectado, otras ventanas, otra etiqueta) para que la mesa de incidentes siga siendo un examen.
    """)

    md("""
    ## Objetivos de aprendizaje

    Al terminar esta lección podrás:

    1. **Aplicar** el bucle de análisis (síntoma → ámbito → cambio → hipótesis → falsación → mitigación → confirmación) a un incidente de un agente usando solo trazas, logs y métricas.
    2. **Detectar** cuándo empezó un incidente con una ventana estadística y **localizar** qué atributos están sobre-representados entre los casos malos (*bubble-up*).
    3. **Diagnosticar** una cascada de reintentos entre agentes midiendo su factor de amplificación y distinguirla de una caída del proveedor.
    4. **Reconocer** un bucle de herramientas por la forma de la traza, cuantificar su coste y **verificar** una mitigación re-ejecutando el incidente.
    5. **Descubrir** una regresión silenciosa a partir de «buenas noticias» (latencia y coste a la baja) y de señales de trayectoria.
    6. **Explicar** una tormenta de cardinalidad con el denominador (tráfico plano), el inventario de etiquetas y corregirla en el origen o en el Collector (configuración validada).
    7. **Probar** que las trazas están partidas (trazas por ticket ≠ 1, raíces huérfanas) y prevenirlo con un contrato de telemetría.
    8. **Elegir** patrones y evitar antipatrones de observabilidad, y **evaluar** la madurez de una organización con un cuestionario honesto.
    9. **Consultar** un compendio de secretos de élite de todo el curso, con fuentes.
    """)

    md("## 🔁 Conexión con módulos anteriores")
    md(details("1 · (Módulo 16) ¿Por qué se alerta sobre síntomas del usuario y se diagnostica por causas?",
               "Porque una alerta por una causa interna (CPU alta) es ruido, mientras que una por el síntoma (presupuesto de error agotándose) es una decisión de negocio. La causa se **busca** después, con trazas y logs: lo que hace esta lección."))
    md(details("2 · (Módulo 11) Si un llamador espera hasta 6 s, con 2 reintentos, a un subagente que falla, ¿cuántos intentos hace por petición y qué pasa si el subagente también reintenta a su vez?",
               "3 intentos (`r+1` con `r=2`) y, con profundidad `d`, `(r+1)^d`: con 2 niveles, 9. Eso es la amplificación de una cascada; los plazos deben decrecer con la profundidad."))
    md(details("3 · (Módulo 15) ¿Por qué una mejora simultánea de latencia y coste tras un cambio de prompt es sospechosa?",
               "Porque a menudo significa que el agente **dejó** de hacer algo caro: llamar a herramientas. Una alucinación no llama herramientas y es más rápida y barata."))
    md(details("4 · (Módulo 18) ¿Dónde está el coste de las métricas y qué etiqueta nunca debe aparecer?",
               "En el número de series (≈ 1-3 KB de RAM por serie, medido); nunca `ticket_id`, `customer_id` ni `trace_id` como etiqueta."))

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_21)
    code(TOOLS_21)

    # ------------------------------------------------------------------------------------------------------------- 1
    md("""
    ---
    # 1 · Intuición: depurar es un método, no una herramienta

    Lo que separa a quien resuelve un incidente en 20 minutos de quien tarda 3 horas **no** es conocer mejor Grafana: es un método que reduce el espacio de hipótesis rápido. Honeycomb lo llama el **bucle de análisis central** (*core analysis loop*, Majors, Fong-Jones y Miranker, 2022):
    parte de un síntoma, **compara poblaciones** (los casos malos frente a los buenos) para ver qué atributo los distingue, formula una hipótesis, la **falsa** con otra consulta y repite. Aplica a agentes con tres adaptaciones: el **coste** es un síntoma (no solo errores y latencia), la **forma de la traza** (nº de pasos, qué herramientas) es evidencia
    de primera clase, y las «buenas noticias» (más rápido, más barato) también pueden ser el incidente.

    | Si vienes de… | Esto es como… | Lo que cambia |
    |---|---|---|
    | **ML** | Análisis de errores de un modelo: ¿en qué *segmentos* falla? | Los segmentos son atributos de span (versión, herramienta, servicio, intención) y el «modelo» cambió de versión hace minutos |
    | **Backend** | Debuggear una latencia: dependencia lenta, cola, reintentos, release reciente | Los reintentos del agente y de los subagentes **multiplican** la carga y el coste |
    | **SRE** | Incident command: mitigar primero, entender después, comunicar | La mitigación tiene opciones propias (modelo de reserva, `LoopGuard`, rollback de prompt) |
    """)
    code('''
fig, ax = viz.canvas(13, 5.0, (0, 130), (0, 50))
P_ = viz.PALETTE
steps = [("1 · Síntoma\\n(alerta de\\nusuario)", P_["error"]), ("2 · Ámbito\\n¿a quién y\\ndesde cuándo?", P_["metrics"]), ("3 · ¿Qué cambió?\\n(despliegues,\\nflags, tráfico)", P_["warn"]),
         ("4 · Comparar\\npoblaciones\\n(bubble-up)", P_["traces"]), ("5 · Hipótesis", P_["profiles"]), ("6 · Falsar\\notra consulta,\\notra señal", P_["logs"]), ("7 · Mitigar y\\nconfirmar\\ncon datos", P_["ok"])]
bs = []
for i, (t, c) in enumerate(steps):
    x = 1 + i * 18.4
    bs.append(viz.box(ax, x, 24, 16.0, 11, t, c, fontsize=7.4))
for a, b in zip(bs, bs[1:]): viz.arrow(ax, viz.right(a), viz.left(b), "", P_["neutral"])
viz.arrow(ax, viz.bottom(bs[5]), viz.bottom(bs[3]), "", P_["error"], rad=-0.45, dashed=True)
ax.text(86, 12.5, "¿no se sostiene? vuelve al paso 4", ha="center", fontsize=8, color=P_["error"])
viz.arrow(ax, viz.top(bs[6]), viz.top(bs[0]), "", P_["ok"], rad=0.12, dashed=True)
ax.text(65, 48.5, "El bucle de análisis: cada vuelta descarta hipótesis, no recoge más datos al azar", ha="center", fontsize=11, fontweight="bold")
for x, t in [(9, "¿Qué señal discrepa?"), (46, "El cambio más cercano\\nNO es siempre la causa"), (65, "Compara contra el\\ndenominador (tráfico)"), (120, "Confirma: ¿vuelve la señal\\na la línea base?")]:
    ax.text(x, 17.5, t, fontsize=8, color=P_["neutral"], ha="center")
plt.show()
''')
    md(observe("""
    - El bucle tiene **dos retroalimentaciones**: si la hipótesis no se sostiene vuelves al paso 4 (otra comparación), y tras mitigar **cierras** comprobando que la señal del síntoma vuelve a la línea base (si no vuelve, la causa era otra).
    - El paso 4 (comparar poblaciones) es el que más tiempo ahorra: en vez de adivinar, le preguntas a los datos «¿qué es distinto en los tickets malos?».
    - Mitigar (paso 7) puede ir **antes** de entender (rollback, disyuntor): la causa raíz es para el postmortem.
    """))

    md("""
    ## 1.1 · Las dos herramientas que usarás en todos los casos

    1. **`find_window(x)`**: con ~4 tickets por minuto, cada minuto es ruidoso. En vez de buscar un salto con umbrales, busca la **ventana** cuya media más se distingue del resto (estadístico t). Detecta saltos («desde el minuto 35») y ventanas («del 25 al 40»).
    2. **`bubble_up(df, malos, columnas)`**: para cada atributo y valor calcula su cuota entre los casos malos y entre los buenos; el cociente (*lift*) apunta a lo que distingue a unos de otros. Es la idea de «BubbleUp» de Honeycomb, a mano.
    """)

    # ------------------------------------------------------------------------------------------------------------- 2
    md("""
    ---
    # 2 · Caso 1 · Cascada de reintentos entre agentes

    **Alerta (neutral, como llega a la guardia):** «p95 de `invoke_workflow` > 8 s durante 5 min y subida de escalados a humano. Los errores 5xx del proveedor LLM no han cambiado.»

    Datos: SupportOps multi-agente (módulo 11) con telemetría real de OpenTelemetry en memoria: orquestador + cuatro especialistas. Variante de la lección (semilla 7): el especialista afectado y la ventana **no** son los del proyecto.
    """)
    code('''
bA = I.build_incident("INC-A", 7, variant="lesson")
print(bA.summary())
display(pd.DataFrame(bA.changes)[["minute", "kind", "service", "desc"]].set_index("minute"))
''')
    code('''
M = pd.DataFrame(bA.metrics)
cols = [("p95_s", "p95 de la petición (s)"), ("error_rate", "tickets malos (error/degradado)"), ("attempts_per_ticket", "intentos de delegación por ticket"), ("escalated_share", "fracción escalada a humano")]
a0, b0, t = find_window(M["p95_s"])
fig, axes = plt.subplots(2, 2, figsize=(13, 6))
for ax, (c, ttl) in zip(axes.ravel(), cols):
    ax.plot(M["minute"], M[c], color=viz.PALETTE["traces"]); mark_window(ax, a0, b0); ax.set_title(ttl); ax.set_xlabel("minuto")
plt.suptitle(f"Caso 1 · ventana detectada con find_window (p95): minutos {a0}-{b0} (|t| = {abs(t):.1f})", fontweight="bold"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El **p95** y los **escalados** suben en una ventana nítida; la tasa de errores **no** (los agentes terminan en `ok` o `escalated`: el sistema «degrada bien» y por eso no hay alerta de errores). Una alerta que solo mire errores no habría saltado.
    - «Intentos por ticket» sube de ≈ 1,2 a ≈ 2: **hay reintentos**. Los reintentos son la firma de una cascada.
    - La ventana la da la estadística (`find_window`), no el ojo; el registro de cambios tiene un despliegue cerca del inicio y otros cuatro irrelevantes: **no te fíes de la cercanía**.
    """))
    code('''
sf = span_frame(bA)
w0, w1 = a0, b0
leaf = sf[sf["name"].str.startswith("execute_tool") | sf["name"].str.startswith("chat")].copy()
leaf["malo"] = (leaf["status"] == "ERROR")
display(bubble_up(leaf, leaf["malo"], ["service", "name", "error_type"]).head(6))
orders_err = sf[(sf["status"] == "ERROR") & (sf["name"] == "execute_tool get_order")]
print("Spans execute_tool get_order en ERROR por servicio y tipo:", orders_err.groupby(["service", "error_type"]).size().to_dict())
''')
    md("""
    El *bubble-up* sobre los spans en error señala **un servicio** (`supportops-orders-agent`) y **un tipo de error** (`timeout`) en una herramienta (`execute_tool get_order`): el problema no está en el LLM ni en el orquestador, sino en la **dependencia** que usa el especialista de pedidos.
    Falta cuantificar cómo un fallo local se convierte en una cascada: los **intentos de delegación** (spans CLIENT `invoke_agent orders-agent`) por traza.
    """)
    code('''
def attempts(b, agent, lo, hi):
    tt = {r["trace_id"]: r["start_min"] for r in I.trace_table(b.spans, b.t0)}
    c = collections.Counter(s["trace_id"] for s in b.spans if s["name"] == f"invoke_agent {agent}" and s["kind"] == "CLIENT")
    return [v for t, v in c.items() if lo <= tt[t] < hi]
prm = bA.extra["params"]
before, during = attempts(bA, prm["agent"], 0, prm["start"]), attempts(bA, prm["agent"], prm["start"], prm["end"])
fig, ax = plt.subplots(figsize=(8, 3.6))
bins = np.arange(0.5, 5.5, 1)
ax.hist(before, bins=bins, alpha=0.7, label=f"antes (media {np.mean(before):.2f})", color=viz.PALETTE["ok"], density=True)
ax.hist(during, bins=bins, alpha=0.7, label=f"durante (media {np.mean(during):.2f})", color=viz.PALETTE["error"], density=True)
ax.set_xlabel("intentos de delegación por ticket"); ax.set_ylabel("fracción de tickets"); ax.legend(); ax.set_title("Amplificación: intentos por petición")
plt.tight_layout(); plt.show()
print(f"Amplificación medida = {np.mean(during) / np.mean(before):.2f}×  ·  máximo teórico con r=2 reintentos y profundidad 1: (r+1)^d = {(2 + 1) ** 1}×")
''')
    md(observe("""
    - Antes del incidente casi todos los tickets necesitan **un** intento; durante, la moda pasa a **tres** (el máximo `r+1`). La amplificación medida (≈ 2×) queda por debajo del máximo teórico 3× porque no todos los tickets tocan al especialista afectado ni todos agotan los reintentos.
    - Cada intento extra es **carga adicional sobre la dependencia que ya sufre**: eso es una cascada. Con profundidad 2 (un subagente que a su vez delega) sería hasta 9×.
    - La mitigación no es subir los timeouts (alarga la agonía): es **disyuntor + degradación + plazos propagados** (módulo 11). Y la confirmación: tras la mitigación el *intentos por ticket* vuelve a ≈ 1.
    """))
    code('''
bad_tid = next(t for t in {s["trace_id"] for s in bA.spans} if (lambda tt: tt.get(t, 99) >= prm["start"])({r["trace_id"]: r["start_min"] for r in I.trace_table(bA.spans, bA.t0)})
               and sum(1 for s in bA.spans if s["trace_id"] == t and s["name"] == f"invoke_agent {prm['agent']}" and s["kind"] == "CLIENT") >= 3)
from supportops.multiagent import waterfall_services
fig, ax = plt.subplots(figsize=(12, 4.8))
waterfall_services([s for s in bA.spans if s["trace_id"] == bad_tid], ax=ax, title=f"Traza con 3 intentos de delegación ({bad_tid[:8]}…)", hide_chat=True)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Verás **tres** spans CLIENT `invoke_agent orders-agent` en escalera, cada uno con su `execute_tool get_order` en rojo (timeout), separados por el *backoff*; al final el orquestador escala a humano. La traza **cuenta la historia** que las métricas solo insinúan.
    - Esta es la única fuente que distingue «el proveedor LLM está caído» (los `chat` en rojo) de «una herramienta aguas abajo agota plazos» (los `execute_tool` en rojo).
    """))

    # ------------------------------------------------------------------------------------------------------------- 3
    md("""
    ---
    # 3 · Caso 2 · Bucle de herramientas

    **Alerta:** «coste por ticket ≥ 2× la línea base durante 10 min y la tasa de tickets sin resolver crece. La latencia del proveedor LLM es normal.»
    """)
    code('''
bB = I.build_incident("INC-B", 7, variant="lesson")
print(bB.summary()); display(pd.DataFrame(bB.changes)[["minute", "kind", "service", "desc"]].set_index("minute"))
MB = pd.DataFrame(bB.metrics); aB, bB_, tB = find_window(MB["cost_per_ticket"])
tt = pd.DataFrame(I.trace_table(bB.spans, bB.t0))
fig, axes = plt.subplots(1, 3, figsize=(14, 3.8))
axes[0].plot(MB["minute"], MB["cost_per_ticket"] * 1000, color=viz.PALETTE["metrics"]); mark_window(axes[0], aB, bB_); axes[0].set_title("Coste por ticket (milésimas de USD)"); axes[0].set_xlabel("minuto")
inw = tt[(tt["start_min"] >= aB) & (tt["start_min"] < bB_)]; out_ = tt[tt["start_min"] < aB]
bins = np.arange(-0.5, 8.5, 1)
axes[1].hist(out_["n_tools"], bins=bins, alpha=0.7, density=True, label="antes", color=viz.PALETTE["ok"]); axes[1].hist(inw["n_tools"], bins=bins, alpha=0.7, density=True, label="durante", color=viz.PALETTE["error"])
axes[1].set_title("Herramientas por traza"); axes[1].set_xlabel("nº de execute_tool"); axes[1].legend()
loop = tt[(tt["n_tools"] >= 5) & (tt["tools"].apply(lambda t: len(set(t)) == 1))]
axes[2].bar(*zip(*collections.Counter(r[0] for r in loop["tools"]).items()), color=viz.PALETTE["error"]); axes[2].set_title(f"Trazas con ≥ 5 llamadas idénticas: {len(loop)}"); axes[2].set_xlabel("herramienta repetida")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El coste por ticket sube en una ventana sin que cambie la latencia del proveedor: **no es el modelo**, es el *número de pasos*. El histograma de herramientas por traza crece una **cola** en 5-6 (el tope `max_steps`).
    - Las trazas «de bucle» comparten una firma: **≥ 5 `execute_tool` y una sola herramienta distinta**. Esa regla —sin leer el contenido— las identifica; la herramienta repetida señala dónde mirar (aquí, la primera que el modelo pidió).
    - Un despliegue «de reindexación» justo antes coincide con el inicio: es una **hipótesis plausible**, pero la prueba es que el bucle exista en la traza. (En producción, el bucle suele nacer de una herramienta que devuelve vacío o un error ambiguo que el modelo reintenta.)
    """))
    code('''
loop_ids = list(loop.sort_values("n_tools", ascending=False)["trace_id"])[:1]
chats = sorted([s for s in bB.spans if s["trace_id"] == loop_ids[0] and s["name"].startswith("chat")], key=lambda s: s["start_unix_nano"])
toks = [s["attributes"].get("gen_ai.usage.input_tokens", 0) for s in chats]
fig, ax = plt.subplots(figsize=(7.5, 3.6))
ax.plot(range(1, len(toks) + 1), toks, "o-", color=viz.PALETTE["error"]); ax.set_xlabel("llamada al LLM dentro del ticket"); ax.set_ylabel("tokens de entrada")
ax.set_title("El contexto crece en cada vuelta del bucle (el coste crece más que linealmente)")
plt.tight_layout(); plt.show()
print("tokens de entrada por llamada:", toks, "· suma:", sum(toks))
''')
    md(observe("""
    - Cada vuelta del bucle **añade el resultado de la herramienta al contexto**: la entrada de la llamada *k* incluye todo lo anterior. La suma de tokens crece como una progresión aritmética y el coste del ticket se multiplica (aquí ≈ 2,5-3× el de un ticket sano).
    - Por eso un bucle es un problema de **coste** antes que de errores: cada ticket «funciona» (hasta `max_steps`).
    """))
    md("**Confirmar la mitigación re-ejecutando el incidente.** Un `LoopGuard` (módulo 13) rechaza la tercera llamada idéntica y aborta el siguiente `chat`. Re-ejecutamos exactamente los mismos tickets con y sin guarda y medimos el coste de los tickets afectados:")
    code('''
from supportops.finops import LoopGuard
ts = I.loop_tickets(7, 240, "lesson")
sin = [SupportAgent().run(t) for t in ts]
lg = LoopGuard(2); con = [SupportAgent(instrumentor=lg).run(t) for t in ts]
aff = [i for i, t in enumerate(ts) if t.incident]
res = pd.DataFrame({"sin guarda": {"coste/ticket afectado (USD)": np.mean([sin[i].cost_usd for i in aff]), "pasos del LLM/ticket": np.mean([sin[i].n_llm_calls for i in aff]), "max_steps": sum(r.status == "max_steps" for r in sin)},
                    "con LoopGuard(2)": {"coste/ticket afectado (USD)": np.mean([con[i].cost_usd for i in aff]), "pasos del LLM/ticket": np.mean([con[i].n_llm_calls for i in aff]), "max_steps": sum(r.status == "max_steps" for r in con)}})
display(res.style.format("{:.5f}", subset=pd.IndexSlice["coste/ticket afectado (USD)", :]).format("{:.2f}", subset=pd.IndexSlice["pasos del LLM/ticket", :]))
print(f"Ahorro en tickets afectados: {1 - res.iloc[0, 1] / res.iloc[0, 0]:.0%} · tickets que acabaron en loop_detected: {len(set(lg.tripped))}")
''')
    md(observe("""
    - La guarda recorta el coste de los tickets afectados en más de la mitad y elimina los `max_steps`: **la mitigación se demuestra con datos**, no con confianza.
    - Contrapartida: los tickets «cortados» acaban degradados/escalados (el bucle no se «arregla», se **acota**). La causa raíz (¿por qué la herramienta devuelve algo que hace reintentar?) sigue pendiente: va al postmortem.
    """))

    # ------------------------------------------------------------------------------------------------------------- 4
    md("""
    ---
    # 4 · Caso 3 · Regresión silenciosa

    **Aviso (ticket, no página):** «las valoraciones negativas (👎) de los clientes suben ≈ 60 % frente a ayer. No hay alertas de errores ni de latencia.»
    """)
    code('''
bC = I.build_incident("INC-C", 7, variant="lesson")
print(bC.summary()); display(pd.DataFrame(bC.changes)[["minute", "kind", "service", "desc"]].set_index("minute"))
MC = pd.DataFrame(bC.metrics)
panels = [("p95_s", "p95 (s)"), ("cost_per_ticket", "coste por ticket (USD)"), ("error_rate", "tickets malos"), ("tool_calls_per_ticket", "herramientas por ticket"), ("thumbs_down_rate", "valoración negativa por ticket")]
fig, axes = plt.subplots(1, 5, figsize=(16, 3.2))
for ax, (c, ttl) in zip(axes, panels):
    y = MC[c].rolling(5, min_periods=1).mean(); ax.plot(MC["minute"], y, color=viz.PALETTE["traces"]); ax.axvline(bC.extra["params"]["rollout_start"], color="#d64545", ls="--"); ax.set_title(ttl, fontsize=9); ax.set_xlabel("minuto")
plt.suptitle("Caso 3 · medias móviles de 5 min (línea roja = despliegue de «v2»): latencia y coste ↓, errores sin cambio, valoración negativa ↑", fontweight="bold"); plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Ninguna** señal «mala» salta: la latencia y el coste **bajan**, los errores no cambian. Solo el 👎 sube (y cae el número de herramientas por ticket). Esta es la firma de la **regresión silenciosa** (módulo 15): el agente hace *menos* y lo hace más rápido y más barato.
    - Si tu alerta de coste solo avisa de subidas, **aplaude** este incidente. Las bajas bruscas de coste/latencia sin explicación también merecen una alerta (de «cambio inesperado»).
    """))
    code('''
sfC = span_frame(bC)
ia = sfC[sfC["name"].str.startswith("invoke_agent")].copy()
tools_per = sfC[sfC["name"].str.startswith("execute_tool")].groupby("trace_id").size()
ia["n_tools"] = ia["trace_id"].map(tools_per).fillna(0).astype(int)
ia["sin_tools"] = ia["n_tools"] == 0
ia = ia[ia["intent"].isin(["order_status", "refund"])]
g = ia.groupby(["version", "intent"])["sin_tools"].agg(["mean", "size"]).reset_index()
display(g.rename(columns={"mean": "fracción SIN llamar a herramientas", "size": "tickets"}))
fig, ax = plt.subplots(figsize=(7, 3.6))
pv = g.pivot(index="intent", columns="version", values="mean"); pv.plot.bar(ax=ax, color=[viz.PALETTE["ok"], viz.PALETTE["error"]]); ax.set_ylabel("fracción sin herramientas"); ax.set_title("Tickets de pedido/reembolso que no consultan nada, por versión"); ax.set_xticklabels(pv.index, rotation=0)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - Estos tickets **deberían** consultar una herramienta (consultar el pedido, reembolsar). Con `v1` los tickets de estado de pedido **siempre** consultan; con `v2`, una de cada **tres** respuestas se «inventa» sin consultar: esa es la regresión y el origen de la valoración negativa.
    - Lo decisivo fue **etiquetar la versión en los spans** (`gen_ai.agent.version`, módulo 15): sin esa dimensión, el *bubble-up* no habría tenido de dónde tirar. La mitigación: **rollback del prompt** y, después, añadir estos casos al dataset de oro.
    """))

    # ------------------------------------------------------------------------------------------------------------- 5
    md("""
    ---
    # 5 · Caso 4 · Tormenta de cardinalidad

    **Alerta:** «memoria de Prometheus al 85 %, duración del *scrape* > 10 s y series activas ×6 en 30 minutos. El tráfico es normal.»
    """)
    code('''
bD = I.build_incident("INC-D", 7, variant="lesson"); prmD = bD.extra["params"]
print(bD.summary()); display(pd.DataFrame(bD.changes)[["minute", "kind", "service", "desc"]].set_index("minute"))
MD = pd.DataFrame(bD.metrics); SD = pd.DataFrame(bD.extra["series_by_metric"])
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
axes[0].plot(MD["minute"], MD["requests"].rolling(5, min_periods=1).mean(), color=viz.PALETTE["traces"]); axes[0].set_title("Peticiones por minuto (media móvil): plano"); axes[0].set_xlabel("minuto")
piv = SD.pivot(index="minute", columns="metric", values="active_series"); axes[1].stackplot(piv.index, piv.T.values, labels=[c.replace("supportops_", "") for c in piv.columns]); axes[1].legend(fontsize=7, loc="upper left"); axes[1].set_title("Series activas por métrica"); axes[1].set_xlabel("minuto")
axes[2].plot(MD["minute"], MD["scrape_duration_s"], color=viz.PALETTE["error"]); axes[2].axhline(10, color="k", ls=":"); axes[2].set_title("Duración del scrape (s) · modelo simple"); axes[2].set_xlabel("minuto")
for ax in axes: ax.axvline(prmD["change"], color="#d64545", ls="--", lw=1)
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - El **denominador** manda: las peticiones por minuto son planas; las series se multiplican por ≈ 6 **en un solo escalón** (no gradualmente, como haría la carga). Eso descarta «tráfico» y apunta a un **cambio de etiquetas**.
    - El apilado por métrica localiza **cuáles** crecen: un histograma (1 serie × 14 por combinación) y un contador. La métrica de coste por modelo no se mueve.
    - El escalón coincide con el despliegue de instrumentación del registro de cambios; pero **la prueba** es el inventario de etiquetas del siguiente paso.
    """))
    code('''
lv = bD.extra["label_values"]; early, late = sorted(lv)
rows = []
for metric in lv[late]:
    for label, n in lv[late][metric].items():
        rows.append({"métrica": metric.replace("supportops_", ""), "etiqueta": label, f"valores distintos (min {early})": lv[early][metric].get(label, "-"), f"valores distintos (min {late})": n})
display(pd.DataFrame(rows))
''')
    md("""
    La tabla lo dice claro: `conversation_id` pasó de **no existir** a decenas de valores distintos (uno por conversación) en dos métricas; el resto de etiquetas (estado, intención, tier) están acotadas. El crecimiento es **lineal en el nº de conversaciones** y no tiene techo.
    Dos formas de arreglarlo (la segunda es la red de seguridad): **en el origen**, con una *View* del SDK que conserve solo las claves permitidas (`attribute_keys`), y **en el Collector**, agregando la etiqueta fuera con `metricstransform`. Probamos la primera y validamos la segunda con `otelcol validate`.
    """)
    code('''
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.metrics.view import View
def series_count(with_view: bool, n_conv: int = 300) -> int:
    reader = InMemoryMetricReader()
    views = [View(instrument_name="supportops.agent.requests", attribute_keys={"supportops.status", "supportops.intent"})] if with_view else []
    mp = MeterProvider(metric_readers=[reader], views=views)
    c = mp.get_meter("demo").create_counter("supportops.agent.requests")
    for i in range(n_conv):
        c.add(1, {"supportops.status": "ok" if i % 7 else "error", "supportops.intent": ["order_status", "refund", "kb_question", "escalation"][i % 4], "supportops.conversation_id": f"T-{i:05d}"})
    pts = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics[0].data.data_points
    mp.shutdown(); return len(pts)
print("series SIN View:", series_count(False), "· series CON View(attribute_keys): ", series_count(True))
CFG_D = yaml.safe_dump({"receivers": {"otlp": {"protocols": {"http": {"endpoint": "0.0.0.0:4318"}}}},
    "processors": {"metricstransform/drop_label": {"transforms": [{"include": "supportops.agent.requests", "match_type": "strict", "action": "update",
                                                                    "operations": [{"action": "aggregate_labels", "label_set": ["supportops.status", "supportops.intent", "supportops.customer.tier"], "aggregation_type": "sum"}]}]}},
    "exporters": {"debug": {"verbosity": "basic"}}, "service": {"pipelines": {"metrics": {"receivers": ["otlp"], "processors": ["metricstransform/drop_label"], "exporters": ["debug"]}}}}, sort_keys=False)
print(CFG_D)
from supportops import privacy as P
ok, msg = P.validate_collector_config(CFG_D) if P.docker_available() else (None, "sin Docker")
print("otelcol validate →", {True: "OK", False: msg, None: "(no ejecutado: sin Docker)"}[ok])
''')
    md(observe("""
    - La *View* convierte **300 series en 8** (2 estados × 4 intenciones): el arreglo **en el origen** es el barato y el definitivo, porque ni siquiera se crea la serie.
    - El procesador `metricstransform` con `aggregate_labels` **suma** los puntos tras eliminar la etiqueta: es la red de seguridad cuando no puedes redesplegar la app. (Borrar la etiqueta con `transform`/`delete_key` sin re-agregar produce **duplicados** de la misma serie en el mismo instante: no lo uses para métricas acumulativas.)
    - Las series antiguas siguen ocupando memoria hasta que caduquen (~5 min de *staleness*) y hasta que el bloque se compacte: la **confirmación** es ver `prometheus_tsdb_head_series` volver a la línea base.
    """))

    # ------------------------------------------------------------------------------------------------------------- 6
    md("""
    ---
    # 6 · Caso 5 · Trazas partidas

    **Aviso:** «las aristas del grafo de servicios (orquestador → agentes) desaparecen y *coste por traza* cae ≈ 60 %. No hay errores ni cambios de latencia.»
    """)
    code('''
bE = I.build_incident("INC-E", 7, variant="lesson"); brk = bE.extra["params"]["break"]
print(bE.summary()); display(pd.DataFrame(bE.changes)[["minute", "kind", "service", "desc"]].set_index("minute"))
ME = pd.DataFrame(bE.metrics); TT = pd.DataFrame(I.trace_table(bE.spans, bE.t0))
TT["periodo"] = np.where(TT["start_min"] < brk, "antes", "después"); TT["raíz"] = TT["root"].str.replace(r" .*", "", regex=True)
sf = span_frame(bE).set_index("trace_id")
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
axes[0].plot(ME["minute"], ME["traces_per_ticket"].rolling(3, min_periods=1).mean(), color=viz.PALETTE["error"]); axes[0].axhline(1, color="k", ls=":"); axes[0].set_title("Trazas por ticket (debería ser 1)"); axes[0].set_xlabel("minuto")
axes[1].plot(ME["minute"], ME["cost_per_trace_tokens"].rolling(3, min_periods=1).mean(), color=viz.PALETTE["metrics"]); axes[1].set_title("Tokens por traza (la «caída de coste»)"); axes[1].set_xlabel("minuto")
ct = pd.crosstab(TT["periodo"], TT["root"].str.split(" ").str[0] + " " + TT["root"].str.split(" ").str[1].str.replace("supportops-", ""))
ct.plot.bar(stacked=True, ax=axes[2], colormap="tab20"); axes[2].set_title("Nombre de la raíz de cada traza"); axes[2].legend(fontsize=6); axes[2].set_xticklabels(ct.index, rotation=0)
for ax in axes[:2]: ax.axvline(brk, color="#d64545", ls="--")
plt.tight_layout(); plt.show()
''')
    md(observe("""
    - **Trazas por ticket** salta de 1 a ≈ 2-3 en un escalón: cada ticket produce **varias trazas**. Los tokens por traza caen simplemente porque cada traza contiene **menos** (una parte del árbol): el «ahorro» es una ilusión de agrupación, no menos gasto real.
    - La tabla de raíces confirma el mecanismo: tras el corte aparecen trazas cuya **raíz es un subagente** (`invoke_agent orders-agent`…) en lugar de `invoke_workflow`: el span hijo perdió a su padre.
    - Sin errores ni latencia, **ninguna alerta clásica salta**. Es un incidente de *observabilidad* sobre tu observabilidad.
    """))
    code('''
def service_edges(df_spans):
    """Aristas servicio→servicio reales: un span cuyo padre pertenece a OTRO servicio (lo que dibuja el service graph)."""
    by_id = {(s["trace_id"], s["span_id"]): (s.get("resource") or {}).get("service.name") for s in bE.spans}
    c = collections.Counter()
    for s in bE.spans:
        p = by_id.get((s["trace_id"], s["parent_span_id"]))
        me = (s.get("resource") or {}).get("service.name")
        if p and p != me: c[(int((s["start_unix_nano"] / 1e9 - bE.t0) // 60) >= brk, p.replace("supportops-", ""), me.replace("supportops-", ""))] += 1
    return c
E = service_edges(None)
rows = [{"periodo": "después" if k[0] else "antes", "arista": f"{k[1]} → {k[2]}", "spans": v} for k, v in E.items()]
display(pd.DataFrame(rows).pivot_table(index="arista", columns="periodo", values="spans", fill_value=0))
''')
    md(observe("""
    - Antes del corte existen aristas **orquestador → cada especialista**; después, esas aristas **casi desaparecen** (quedan solo las del tramo previo a `BREAK` o las de dentro de un mismo servicio). Es exactamente lo que ve el service graph de Tempo: nodos sin conexión.
    - Causas típicas: una librería de transporte nueva que no inyecta `traceparent`, un *gateway* que elimina cabeceras desconocidas, un `dict(headers)` que cambia las mayúsculas (módulo 03), o un servicio con muestreo independiente en lugar de `ParentBased` (módulo 11).
    """))
    code('''
# Contrato de telemetría preventivo: «una traza por ticket». Prueba canario de 6 tickets con dos configuraciones de propagación.
from supportops.multiagent import MultiAgentSupportOps, build_mesh
def traces_per_ticket(propagation: str, n: int = 6) -> float:
    mesh = build_mesh(mode="memory"); system = MultiAgentSupportOps(mesh, mode="delegate", propagation=propagation)
    ts = generate_tickets(n, SEED, duration_s=60, pii_rate=0.0)
    for t in ts: system.run(t)
    mesh.force_flush(); n_tr = len({s["trace_id"] for s in mesh.span_records()}); mesh.shutdown(); return n_tr / n
for p_ in ("sdk", "none"):
    v = traces_per_ticket(p_); print(f"propagation={p_:5} → trazas por ticket = {v:.2f}", "✅ contrato cumplido" if v == 1.0 else "❌ CONTRATO ROTO: trazas partidas")
''')

    # ------------------------------------------------------------------------------------------------------------- 7
    md("""
    ---
    # 7 · Patrones y antipatrones

    ## 7.1 · La tabla de síntomas → primera sospecha → consulta

    | Síntoma | Primera sospecha | La consulta que la confirma | Mitigación habitual |
    |---|---|---|---|
    | Latencia ↑, errores sin cambio, escalados ↑ | Cascada de reintentos / dependencia lenta | Spans `execute_tool` en ERROR por servicio; intentos CLIENT por traza (`≥ 2`) | Disyuntor + degradación + plazo propagado |
    | Coste ↑ sin errores | Bucle de herramientas | Trazas con ≥ 5 `execute_tool` de una sola herramienta; tokens de entrada creciendo | `LoopGuard`, `max_steps`, tope de coste por ticket |
    | Latencia ↓, coste ↓, 👎 ↑ | Regresión silenciosa | Fracción de tickets de pedido/reembolso **sin** herramientas por versión | Rollback, dataset de oro, compuerta (módulo 15) |
    | Series activas ×N con tráfico plano | Etiqueta de cardinalidad nueva | Valores distintos por etiqueta y métrica; `count by (__name__)` | View del SDK / agregación en el Collector |
    | Trazas por ticket > 1, raíces de subagentes | Contexto perdido | Raíz de las trazas; aristas del service graph | Restaurar propagación; contrato `n_traces == n_tickets` |
    | Errores solo en `chat`, 5xx/429 | Proveedor LLM | `status=ERROR` por `gen_ai.provider.name`, `http.response.status_code` | Modelo de reserva, backoff, límites |
    | PII en la salida / orden extraña ejecutada | Fuga o inyección | Detector + monitor de comportamiento (módulo 20) | Redacción, mínimo privilegio, aprobación humana |
    """)
    code('''
fig, ax = viz.canvas(13, 5.2, (0, 130), (0, 52))
P_ = viz.PALETTE
root = viz.box(ax, 50, 42, 30, 7, "¿Qué señal de usuario discrepa?", P_["error"], bold=True, fontsize=9)
q = {"lat": viz.box(ax, 2, 28, 24, 8, "Latencia ↑\\nerrores sin cambio", P_["traces"], fontsize=8), "cost": viz.box(ax, 28, 28, 24, 8, "Coste ↑\\nsin errores", P_["metrics"], fontsize=8),
     "good": viz.box(ax, 54, 28, 24, 8, "Latencia/coste ↓\\n👎 ↑", P_["profiles"], fontsize=8), "series": viz.box(ax, 80, 28, 22, 8, "Series ↑\\ntráfico plano", P_["warn"], fontsize=8), "split": viz.box(ax, 104, 28, 24, 8, "Trazas por ticket > 1", P_["logs"], fontsize=8)}
for b in q.values(): viz.arrow(ax, viz.bottom(root), viz.top(b), "", P_["neutral"])
ans = [("Cascada de\\nreintentos", q["lat"], P_["traces"]), ("Bucle de\\nherramientas", q["cost"], P_["metrics"]), ("Regresión\\nsilenciosa", q["good"], P_["profiles"]), ("Tormenta de\\ncardinalidad", q["series"], P_["warn"]), ("Contexto\\nperdido", q["split"], P_["logs"])]
for t, b, c in ans:
    r = viz.box(ax, b[0], 10, b[2], 9, t, c, fc="#f3f4f6", fontsize=8, bold=True); viz.arrow(ax, viz.bottom(b), viz.top(r), "", c)
for b, t in zip(q.values(), ["intentos CLIENT\\npor traza", "n_tools idénticas\\nseguidas", "sin herramientas\\npor versión", "valores distintos\\npor etiqueta", "raíces de\\nsubagentes"]):
    ax.text(b[0] + b[2] / 2, 23.5, t, ha="center", fontsize=7, color=P_["neutral"])
ax.text(65, 3, "Primer movimiento: mira la FORMA del síntoma, no el nombre de la alerta", ha="center", fontsize=9.5, fontweight="bold")
plt.show()
''')
    md(observe("""
    - Cada síntoma de usuario apunta a **una** familia de causas; la señal distintiva (intentos por traza, herramientas idénticas seguidas, herramientas por versión, valores distintos por etiqueta, raíces de subagentes) es lo que **separa** familias que, vistas desde el dashboard de golden signals, parecerían iguales.
    - Memorízalo como un árbol de triaje, no como una lista de causas: el objetivo es hacer **una** consulta que descarte las otras cuatro familias.
    """))
    md("""
    ## 7.2 · Antipatrones (y su alternativa)

    | Antipatrón | Por qué falla | Alternativa |
    |---|---|---|
    | Alertas por causas internas (CPU, longitud de cola) | Páginas que no se corresponden con dolor del usuario → fatiga de alertas | Alertas por SLO y burn rate; diagnóstico por causas (módulo 16) |
    | Dashboards sin dueño ni fecha de caducidad | Se pudren; en el incidente nadie sabe qué panel es fiable | `description` en cada panel, `uid` estable, dueño en etiquetas, revisión trimestral (módulo 10) |
    | Solo medias (latencia media, coste medio) | La cola larga (bucles, reintentos) se esconde | Percentiles y concentración (módulo 13); nunca promediar percentiles (módulo 09) |
    | «Registrarlo todo por si acaso» | Coste, PII y ruido; el dato útil se pierde en el volumen | Muestreo por valor (módulo 18), captura de contenido por niveles (módulo 20) |
    | Etiquetas con IDs en métricas | Cardinalidad ilimitada (caso D) | IDs en trazas/logs; métricas acotadas; View del SDK |
    | Calcular métricas después de muestrear | Sesgo (2,6 % → 12 % en el módulo 18) | RED antes del muestreo (`span_metrics` en `traces/in`) |
    | Comparar «esta semana vs la pasada» | Mezcla regresión con deriva | Comparar apareado y simultáneo (canario, módulo 15) |
    | Postmortems con nombres propios | Se esconde información; se repite el fallo | Sin culpa, con acciones con dueño y plazo (módulo 16) |
    | «Observabilidad teatro»: muchos paneles, ninguna decisión | Nadie actúa con ellos | Cada panel responde una pregunta que acaba en una acción documentada en un runbook |
    """)

    # ------------------------------------------------------------------------------------------------------------- 8
    md("""
    ---
    # 8 · Cultura de observabilidad

    La tecnología es la parte fácil. Las organizaciones que depuran bien comparten prácticas que no salen en ningún chart de Helm:

    1. **La observabilidad es parte de «hecho»** (*definition of done*): una funcionalidad nueva no se fusiona sin su telemetría, su panel o consulta de verificación y su fila en el runbook. Una **lista de revisión de telemetría en los PR** (¿atributos acotados? ¿PII? ¿versión etiquetada? ¿nombres de span estables?) cuesta 5 minutos y evita la mitad de los incidentes de esta lección.
    2. **Contratos de telemetría con pruebas**: «una traza por ticket», «`cache_read + cache_write ≤ input`», «ningún span con PII», «todos los atributos que usa un dashboard existen». Si el panel depende de un atributo, la prueba de CI también.
    3. **Todos se curan con los mismos datos**: el equipo de producto mira las mismas trazas que la guardia. Así las preguntas «¿cuánto cuesta un ticket?» o «¿qué fracción usa herramientas?» tienen una sola respuesta.
    4. **Game days** (simulacros) con incidentes como los de esta lección: se aprende más una vez que se rompe a propósito que cien dashboards bonitos. La mesa de incidentes del proyecto es un game day en cuaderno.
    5. **Presupuesto de error como lenguaje común** con producto (módulo 16) y **salud de la guardia** como métrica (páginas por semana, % accionables).
    6. **Postmortems sin culpa que cierran el bucle**: cada acción de «detectar» se convierte en una alerta o un contrato; cada acción de «prevenir», en una prueba. Un postmortem sin acciones comprobables es literatura.
    7. **Coste de observabilidad visible**: el equipo ve cuánto cuestan sus propias series, logs y trazas (módulo 18) y tiene incentivo para podarlos.
    """)
    code('''
PRACT = ["Trazas de extremo a extremo", "Logs con trace_id", "Métricas RED + GenAI", "SLOs y burn rate", "Runbooks y postmortems", "Calidad online", "Control de coste", "Privacidad y seguridad", "Muestreo y retención", "Todo como código",
         "Game days / simulacros", "Contratos de telemetría en CI"]
# Autoevaluación ILUSTRATIVA de SupportOps tal y como la dejan los módulos 00-22 (0 = nada · 3 = automatizado y probado). Rellénala con TU organización.
SCORE = {"Trazas de extremo a extremo": 3, "Logs con trace_id": 3, "Métricas RED + GenAI": 3, "SLOs y burn rate": 3, "Runbooks y postmortems": 2, "Calidad online": 3, "Control de coste": 3, "Privacidad y seguridad": 2,
         "Muestreo y retención": 3, "Todo como código": 3, "Game days / simulacros": 1, "Contratos de telemetría en CI": 1}
ang = np.linspace(0, 2 * np.pi, len(PRACT), endpoint=False); vals = [SCORE[p] for p in PRACT]
fig = plt.figure(figsize=(7.2, 6)); ax = fig.add_subplot(111, polar=True)
ax.plot(np.append(ang, ang[0]), np.append(vals, vals[0]), color=viz.PALETTE["traces"], lw=2); ax.fill(ang, vals, color=viz.PALETTE["traces"], alpha=0.2)
ax.plot(np.append(ang, ang[0]), [3] * (len(ang) + 1), color=viz.PALETTE["ok"], ls="--", lw=1)
ax.set_xticks(ang); ax.set_xticklabels([p.replace(" y ", "\\ny ").replace(" de ", "\\nde ", 1) for p in PRACT], fontsize=7.5); ax.set_yticks([1, 2, 3]); ax.set_ylim(0, 3)
ax.set_title("Madurez de observabilidad de SupportOps (autoevaluación ilustrativa)", pad=22, fontsize=10, fontweight="bold")
plt.tight_layout(); plt.show()
print("Brechas (≤ 1):", [p for p in PRACT if SCORE[p] <= 1])
''')
    md(observe("""
    - La plataforma que construyes en el curso es fuerte en **instrumentación y datos**; las brechas honestas están en lo **cultural**: simulacros y contratos de telemetría automatizados (≤ 1). Esos dos puntos son lo que convierte un buen stack en una buena práctica.
    - El valor de este cuestionario no es el gráfico sino el **plan**: cada brecha debe acabar en una acción con dueño y plazo (como en un postmortem).
    """))

    # ------------------------------------------------------------------------------------------------------------- 9
    md("""
    ---
    # 9 · Míralo en Grafana (con el stack): la sala de guerra

    Reproducimos el **bucle de herramientas** de la lección en vivo —con los tiempos comprimidos a los últimos 5 minutos— a través del Collector real, con `OTelInstrumentor` + `MetricsInstrumentor` (módulo 09), y comprobamos que las **tres** pantallas de la sala de guerra
    (dashboard `21 · Sala de guerra de SupportOps`, uid `sala-de-guerra`) ven el patrón: coste por ticket y herramientas por ticket (Prometheus), trazas con ≥ 5 herramientas (Tempo).
    """)
    code('''
LIVE_OK = False
if LIVE:
    from supportops.otel_metrics import MetricsInstrumentor
    ts = I.loop_tickets(7, 240, "lesson"); now = time.time(); t0 = ts[0].created_at; span = ts[-1].created_at - t0
    live = [dataclasses.replace(t, created_at=now - 300 + (t.created_at - t0) / span * 285) for t in ts]
    tel = setup_telemetry("supportops-agent", metric_interval_s=2, service_version="0.1.0-m21")
    agent = SupportAgent(max_steps=6, instrumentor=CompositeInstrumentor(OTelInstrumentor(tel, emit_metrics=False), MetricsInstrumentor(tel)))
    run_tickets(agent, live); tel.force_flush(); tel.shutdown(); LIVE_OK = True
    print("Enviado: 240 tickets, 5 min de ventana, bucle en la ventana relativa 53-83 %. Espera ~20 s…")
else:
    print("Sin stack: omitido (modo degradado). Comando:", STACK.command)
''')
    code('''
if LIVE and LIVE_OK:
    def poll(fn, ok, tries=40, wait=2.0):
        v = None
        for _ in range(tries):
            try: v = fn()
            except Exception: v = None
            if v is not None and ok(v): return v
            time.sleep(wait)
        return v
    # contadores acumulados desde que arrancó el stack (con una sola muestra de scrape `increase`/`rate` darían NaN)
    p90 = poll(lambda: backends.prom_query('histogram_quantile(0.9, sum by (le) (gen_ai_invoke_agent_tool_calls_bucket{service_name="supportops-agent"}))'), lambda r: len(r) > 0 and r[0]["value"][1] != "NaN")
    p50 = backends.prom_query('histogram_quantile(0.5, sum by (le) (gen_ai_invoke_agent_tool_calls_bucket{service_name="supportops-agent"}))')
    cost = backends.prom_query('sum(supportops_agent_request_cost_USD_sum{service_name="supportops-agent"}) / sum(supportops_agent_request_cost_USD_count{service_name="supportops-agent"})')
    print("Prometheus · herramientas por ticket p50 / p90:", [m["value"][1] for m in p50], [m["value"][1] for m in p90 or []], "· coste medio por ticket:", [m["value"][1] for m in cost])
    tr = poll(lambda: backends.tempo_search('{ name =~ "execute_tool.*" } | count() >= 5', 10, 100).get("traces", []), lambda r: len(r) >= 10, tries=40)
    print("Tempo · trazas con ≥ 5 llamadas a herramientas:", len(tr or []), "· (esperadas ≈ 35-45)")
''')
    md("Abre el dashboard **21 · Sala de guerra de SupportOps**: el p90 de herramientas por ticket se dispara, el coste por ticket sube y la tabla de Tempo lista las trazas candidatas a bucle; desde cada una saltas a la traza y, con el `trace_id`, a los logs del ticket.")

    # ------------------------------------------------------------------------------------------------------------- 10
    md("""
    ---
    # 10 · Compendio de secretos de élite (módulos 00-21)

    A continuación, el **compendio**: los secretos de las secciones 🧠 de todas las lecciones, recopilados por tema y con su fuente (y ampliados con los de este módulo). También está en `COMPENDIO_SECRETOS.md`.
    Úsalo como **lista de comprobación** al revisar una plataforma de observabilidad de agentes: cada fila es algo que alguien ha medido o sufrido.
    """)
    code("COMPENDIUM = " + repr(COMPENDIUM) + '''
CP = pd.DataFrame(COMPENDIUM, columns=["tema", "módulo", "secreto", "por qué importa / medido", "fuente"])
print(f"{len(CP)} secretos · {CP['tema'].nunique()} temas")
fig, ax = plt.subplots(figsize=(8.5, 3.6))
cnt = CP["tema"].value_counts().sort_values(); ax.barh(cnt.index, cnt.values, color=viz.PALETTE["traces"]); ax.set_xlabel("nº de secretos"); ax.set_title("Compendio por tema")
for i, v in enumerate(cnt.values): ax.text(v + 0.1, i, str(v), va="center")
plt.tight_layout(); plt.show()
''')
    code('''
def compendio(consulta: str = "", tema: str | None = None, n: int = 8):
    """Busca en el compendio por texto libre (en secreto + por qué) y/o tema; imprime una tabla Markdown."""
    d = CP if tema is None else CP[CP["tema"] == tema]
    if consulta:
        m = d["secreto"].str.contains(consulta, case=False) | d["por qué importa / medido"].str.contains(consulta, case=False)
        d = d[m]
    lines = ["| Módulo | Secreto | Por qué importa / medido | Fuente |", "|---|---|---|---|"] + [f"| {r['módulo']} | **{r['secreto']}** | {r['por qué importa / medido']} | {r['fuente']} |" for _, r in d.head(n).iterrows()]
    return Markdown("\\n".join(lines))
compendio("cardinalidad")
''')
    code('''
compendio(tema="Collector y despliegue", n=4)
''')
    md(observe("""
    - Los secretos se agrupan en **diez temas** y casi la mitad son **trampas silenciosas**: pérdida sin error (cola del `BatchSpanProcessor`, tail sampling con `num_traces` corto), números que mienten (buckets, ceros falsos, promedios de percentiles) y valores por defecto que son decisiones (privacidad, retención, ventanas).
    - Prueba `compendio("muestreo")`, `compendio("PII")`, `compendio(tema="Backends (Tempo, Loki)")`. La mejor forma de usarlo es **antes de un despliegue**, no durante un incidente.
    """))

    # ------------------------------------------------------------------------------------------------------------- 11
    md("""
    ---
    # 11 · 🏭 En producción: cómo lo hacen otros

    - **Honeycomb** formalizó el **bucle de análisis central** y la comparación de poblaciones (BubbleUp) como el modo de depurar sistemas con alta cardinalidad: se parte de un síntoma y se pregunta por qué los eventos malos se distinguen de los buenos (*Observability Engineering*, Majors, Fong-Jones y Miranker, 2022).
    - **Netflix** construyó **Edgar**, una herramienta de resolución de problemas sobre *distributed tracing* que une trazas, logs, metadatos y análisis en una sola vista para no saltar entre herramientas; el artículo de Netflix Tech Blog (Elizabeth Carretto, 2020) subraya que el tiempo ahorrado en incidentes y depuración diaria compensa el coste de construirla.
    - **Google** (Dapper, 2010) argumentó que el rastreo útil es **de bajo coste, transparente para la aplicación y desplegado en todas partes**, y que el muestreo es parte del diseño; de ahí vienen `trace_id`, spans y la propagación de contexto que usa OpenTelemetry.
    - **SRE de Google**: el postmortem **sin culpa** y la acción con dueño y plazo (*Site Reliability Engineering*, cap. 15). Recopilaciones públicas de postmortems de la industria (el repositorio `danluu/post-mortems`) muestran que **los mismos cinco patrones** (reintentos que amplifican, cambios de configuración, dependencias, cardinalidad, límites de capacidad) se repiten en todas las empresas.
    - **Grafana Labs** documenta las alertas por **burn rate multiventana** y el uso de *exemplars* para saltar de una métrica a la traza: la columna vertebral del bucle de análisis cuando empiezas en un dashboard.
    """)

    md("""
    ---
    # 12 · 🧠 Secretos de la élite de este módulo

    1. **Una subida de coste sin errores es un bucle hasta que se demuestre lo contrario.** La forma de la traza (≥ 5 `execute_tool` idénticos seguidos) lo confirma sin leer contenido; el coste de un ticket con bucle fue ≈ 2,5-3× el sano en el laboratorio.
    2. **Las buenas noticias también son síntomas.** Latencia y coste a la baja con 👎 al alza: algo dejó de hacerse. Alerta también sobre **bajadas inesperadas**.
    3. **El cambio más cercano no es la causa.** En los cinco casos el registro de cambios tenía 3-4 candidatos; sirve el que **predice la forma** del síntoma (qué servicio, qué etiqueta, qué versión).
    4. **El denominador manda.** Series ×6 con tráfico plano, coste ×2 con tickets planos: antes de culpar a la carga, divide por la carga.
    5. **«Trazas por ticket ≠ 1» es el contrato de telemetría más barato** del mundo (una división). Quien lo tiene no sufre semanas de trazas partidas.
    6. **La mitigación se demuestra re-ejecutando el incidente** (mismos tickets, con y sin guarda): es la mejor forma de convencer a un revisor… y al *yo* de las 3 a. m.
    7. **Mitiga antes de entender; entiende antes de cerrar.** El rollback no sustituye al postmortem: sin causa raíz el incidente vuelve.
    8. **La versión es la dimensión más rentable de la telemetría de un agente.** Sin `gen_ai.agent.version` en spans, el caso 3 no habría tenido bubble-up. Cuesta una línea y ahorra días.
    """)

    md("""
    ---
    # 13 · ⚠️ Errores comunes al depurar

    - Empezar por la causa (CPU, GC) en vez de por el síntoma de usuario y su forma.
    - Dar por buena la correlación temporal con un despliegue sin verificar el mecanismo (¿qué servicio/etiqueta/versión predice el síntoma?).
    - Mirar medias; los incidentes de agentes viven en la **cola** y en la **forma** (pasos, herramientas, intentos).
    - Subir *timeouts* para «arreglar» una cascada: alarga la agonía y multiplica el coste.
    - Borrar la etiqueta problemática solo en el Collector sin re-agregar (duplicados) o solo en la app sin reiniciar las series.
    - No cerrar el bucle: dar el incidente por terminado sin ver volver la señal a la línea base.
    - No dejar rastro: sin postmortem con acciones comprobables el patrón reaparecerá.
    """)

    md("""
    ---
    # 14 · Autoevaluación
    """)
    md(details("1 · (Cálculo) Un orquestador reintenta 2 veces a un subagente (`r = 2`) y el subagente reintenta 2 veces a una herramienta. ¿Cuántas llamadas a la herramienta puede generar un solo ticket en el peor caso? ¿Y si el plazo del orquestador no decrece?",
               "`(r+1)^d = 3² = 9` llamadas a la herramienta en el peor caso (3 intentos del orquestador × 3 del subagente). Si el plazo del orquestador es menor que el tiempo total de los reintentos del subagente, el orquestador abandona antes y los 9 se convierten en trabajo zombi (módulo 11). Los plazos deben decrecer con la profundidad."))
    md(details("2 · (Diagnóstico) Tras un despliegue, la latencia media baja un 15 %, el coste un 12 % y no hay errores, pero las valoraciones negativas suben. ¿Qué tres consultas ejecutas para confirmar una regresión silenciosa?",
               "(1) Fracción de tickets de pedido/reembolso **sin** `execute_tool` por versión (`gen_ai.agent.version`). (2) Herramientas por ticket (p10/p50) antes/después del despliegue. (3) Una muestra de respuestas de la versión nueva comparadas con las de la antigua por un juez o por la trayectoria de herramientas (módulos 14-15). Mitigación: rollback y añadir los casos al dataset de oro."))
    md(details("3 · (Transferencia) Prometheus va al 85 % de memoria y el tráfico es plano. Describe tres comprobaciones y dos arreglos, uno en el origen y otro en la red de seguridad.",
               "Comprobaciones: (a) `prometheus_tsdb_head_series` frente a peticiones (escalón vs rampa); (b) `topk(10, count by (__name__) ({__name__=~\".+\"}))` para localizar la métrica; (c) valores distintos por etiqueta de esa métrica (`count(count by (label) (metric))`). Arreglos: **origen**: View del SDK con `attribute_keys` o quitar el atributo del instrumento; **red de seguridad**: `metricstransform` con `aggregate_labels` en el Collector (no `delete_key` sin re-agregar). Confirmar con el descenso de series (≈ 5 min de staleness)."))
    md(details("4 · (Cálculo) Tres servicios de la cadena muestrean cada uno de forma independiente al 20 %. ¿Qué fracción de trazas queda completa? ¿Qué cambias?",
               "`0,2³ = 0,8 %` de las trazas completas. Con `ParentBased` (decide la raíz y los demás respetan el bit `sampled`) quedaría el 20 % completo. Es el mismo error del módulo 11 (`0,1^5`)."))
    md(details("5 · (Diagnóstico) El registro de cambios muestra un despliegue exactamente en el minuto en que empieza un incidente. ¿Cómo sabes si es la causa?",
               "Buscas el **mecanismo**: ¿el síntoma está en el servicio, la versión o la etiqueta que ese despliegue tocó? (bubble-up por servicio/versión). Si el síntoma aparece también en los tickets que no pasan por lo desplegado, no es la causa. La prueba definitiva es el **contrafactual**: revertir (o desactivar) y ver si la señal vuelve a la línea base."))
    md(details("6 · (Transferencia) Diseña un contrato de telemetría de una frase y su prueba para cada uno de los cinco casos de la lección.",
               "A: «ningún `invoke_agent` CLIENT se repite más de `r+1` veces por traza» (prueba de trazas). B: «ninguna traza supera `max_steps` herramientas idénticas» (alerta de forma). C: «las versiones nuevas no bajan `tool_calls` p50 más de X % sin aprobación» (compuerta del módulo 15). D: «cada métrica tiene un conjunto de etiquetas permitido y ≤ N valores distintos» (lint de series). E: «`n_traces == n_tickets` en la prueba canario» (la de la sección 6)."))
    md(details("7 · ¿Por qué se dice que mitigar es distinto de resolver y por qué se hace primero?",
               "Mitigar reduce el impacto en minutos (rollback, disyuntor, degradación); resolver encuentra y elimina la causa raíz (puede llevar días). Se mitiga primero porque cada minuto cuenta contra el presupuesto de error; se resuelve después con calma y se documenta en el postmortem sin culpa."))

    md("""
    ---
    # 15 · Referencias

    - C. Majors, L. Fong-Jones, G. Miranker (2022), *Observability Engineering*, O'Reilly: bucle de análisis central, alta cardinalidad y comparación de poblaciones.
    - E. Carretto, *Edgar: Solving Mysteries Faster with Observability*, Netflix Technology Blog (2020): <https://netflixtechblog.com/edgar-solving-mysteries-faster-with-observability-e1a76302c71f>.
    - B. H. Sigelman et al. (2010), *Dapper, a Large-Scale Distributed Systems Tracing Infrastructure*, Google Technical Report: <https://research.google/pubs/pub36356/>.
    - B. Beyer, C. Jones, J. Petoff, N. R. Murphy (2016), *Site Reliability Engineering*, O'Reilly, cap. 15 «Postmortem Culture: Learning from Failure»; B. Beyer et al. (2018), *The Site Reliability Workbook*, cap. 5 «Alerting on SLOs».
    - J. Allspaw (2012), *Blameless PostMortems and a Just Culture*, Etsy Code as Craft.
    - D. Luu, *post-mortems* (recopilación de postmortems públicos): <https://github.com/danluu/post-mortems>.
    - C. Sridharan (2018), *Distributed Systems Observability*, O'Reilly.
    - Documentación del procesador `metricstransform` del Collector contrib (acción `aggregate_labels`, versión 0.162.0) y de las *Views* del SDK de métricas de OpenTelemetry (`attribute_keys`): validadas en este módulo con `otelcol validate` y con el SDK de Python.
    - Cada secreto del compendio cita el módulo del curso y, a través de él, sus fuentes (especificaciones de OpenTelemetry, documentación de Tempo/Loki/Prometheus/Grafana, SRE Workbook, Rogan y Gladen 1978…).
    """)
    nb.save(out)


# =====================================================================================================================
# PROYECTO · Mesa de incidentes
# =====================================================================================================================
def build_project() -> None:
    nb, out = nb_for(MOD, "21_proyecto_mesa_de_incidentes.ipynb", "Proyecto 21 · Mesa de incidentes de SupportOps")
    md, code = nb.md, nb.code

    md(f"""
    {nb.badge()}

    # Proyecto 21 · Mesa de incidentes: diagnostica 5 incidentes solo con telemetría

    | | |
    |---|---|
    | **Nivel** | 🔴 Experto |
    | **Duración estimada** | ≈ 1 h 45 min |
    | **Servicios de Compose** | Ninguno (todo en memoria) |
    | **RAM aproximada** | < 600 MB |
    | **Prerrequisitos** | Lección `21_elite_playbook` y los módulos 11, 13, 15, 16, 18 y 20 |
    | **Conexión** | Es el examen del curso: los cinco incidentes son las familias de fallo que viste en cada bloque. La telemetría de cada caso es real (SDK de OpenTelemetry, agente SupportOps); la **verdad** está en el módulo `supportops.incidents` (no la leas antes de terminar) |

    ## Contexto de negocio

    Hoy estás de guardia en **SupportOps**. Llegan cinco alertas a lo largo de la semana. De cada una recibes **solo telemetría** —spans, logs, métricas por minuto y un registro de cambios con ruido—, **sin pistas directas**: el texto de la alerta describe un síntoma, no una causa.
    Tu trabajo: para cada incidente, entregar un **diagnóstico** con la causa raíz, cuándo empezó, qué elemento es el culpable, **una cifra de evidencia** y la mitigación.

    ## Datos

    `I.build_incident("INC-A")` … `"INC-E"` devuelven un `IncidentBundle` con `.alert`, `.spans` (esquema `SPAN_SCHEMA`), `.logs`, `.metrics` (una fila por minuto; columnas según el caso), `.changes` y `.extra`. Determinista (semilla 42, `mock`). Todas las cifras y ventanas son de la simulación.
    Los *ground truth* están en el paquete; la corrección usa `I.grade(caso, diagnóstico)`, que comprueba **5 cosas**: causa raíz, inicio (±4 min), culpable, evidencia numérica (tolerancia 25-35 %) y mitigación.

    ## Entregables y criterios de evaluación (rúbrica)

    | # | Entregable | Criterio medido | Umbral (calibrado con la solución; `mock`, semilla 42) |
    |---|---|---|---|
    | R1 | `find_window` | 4 vectores: salto, ventana, sin cambio y complemento | 4/4 |
    | R2 | `bubble_up` | El valor sobre-representado está en primera posición con *lift* ≥ 5 | 3/3 |
    | R3-R7 | `diagnose_a` … `diagnose_e` | `I.grade` de cada incidente | **≥ 4/5** cada uno (la solución obtiene **5/5** en los cinco) |
    | R8 | Informe | Los cinco diagnósticos usan causas y mitigaciones distintas y consistentes con el catálogo | 3/3 |

    > 📏 Umbrales calibrados con la solución de referencia (semilla 42). Nota: cada incidente tiene **5 comprobaciones**; con 4/5 apruebas (un fallo de precisión numérica o de ventana es tolerable), con 5/5 «has resuelto la mesa».
    """)

    code(boot("viz,otel"))
    code(IMPORTS + IMPORTS_21.replace('STACK = check_stack("core+metrics")', 'STACK = check_stack([])').replace("LIVE = not STACK.degraded", "LIVE = False"))

    md("## Paso 0 · Los datos y el catálogo de causas")
    code('''
BUNDLES = {c: I.build_incident(c) for c in I.CASE_IDS}
for c, b in BUNDLES.items(): print(b.summary(), "\\n")
print("Causas posibles:"); [print(f"  {k:34} {v}") for k, v in I.CAUSES.items()]
print("\\nMitigaciones:"); [print(f"  {k:26} {v}") for k, v in I.MITIGATIONS.items()]
print("\\nCampos de evidencia por caso:", {c: I.evidence_keys(c) for c in I.CASE_IDS})
''')

    md("""
    ## Paso 1 · Herramienta: dónde empieza el incidente

    **TODO 1.** `find_window(x, min_len=5)` devuelve `(a, b, t)`: la ventana `[a, b)` (de al menos `min_len` minutos, con al menos `min_len` fuera) que maximiza el valor absoluto del estadístico
    `t = (media_dentro − media_fuera) / (σ·√(1/n_dentro + 1/n_fuera))`, con `σ = x.std()` de toda la serie. Si la mejor ventana empieza en 0 y no cubre toda la serie, devuelve su **complemento** `(b, n)`.
    """)
    md(hint(1, "Doble bucle sobre `a` y `b`; con sumas acumuladas (`np.cumsum`) cada media sale en O(1). Guarda la mejor `|t|`."))
    md(hint(2, "`c = np.concatenate([[0], np.cumsum(x)])`; media dentro = `(c[b]-c[a])/(b-a)`; media fuera = `(c[n]-(c[b]-c[a]))/(n-(b-a))`."))
    code('''
def find_window(x, min_len=5):
    # TODO 1
    raise NotImplementedError("TODO 1")

try:
    print(find_window([1.0] * 20 + [5.0] * 10 + [1.0] * 10))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Paso 2 · Herramienta: qué distingue a los malos

    **TODO 2.** `bubble_up(df, bad, cols, min_n=5)` recibe un `DataFrame`, una máscara booleana `bad` y una lista de columnas; devuelve un `DataFrame` con una fila por (columna, valor) que aparece **al menos `min_n` veces** entre los malos, con las columnas `atributo`, `valor`, `lift` y `n malos`,
    donde `lift = cuota entre malos / (cuota entre buenos + 0,01)` y las cuotas son `value_counts(normalize=True)`. Ordénalo por `lift` descendente.
    """)
    code('''
def bubble_up(df, bad, cols, min_n=5):
    # TODO 2
    raise NotImplementedError("TODO 2")

try:
    _df = pd.DataFrame({"svc": ["a"] * 30 + ["b"] * 30 + ["c"] * 30, "bad": [True] * 20 + [False] * 10 + [False] * 30 + [False] * 28 + [True] * 2})
    print(bubble_up(_df, _df["bad"], ["svc"]).head(2))
except NotImplementedError as e:
    print("Pendiente:", e)
''')

    md("""
    ## Pasos 3-7 · Los cinco incidentes

    Para cada caso escribe `diagnose_x(bundle) -> dict` con las claves `cause`, `start_min`, `end_min`, `culprit`, `evidence` (dict con las claves que lista `I.evidence_keys(caso)`) y `mitigation`.
    **Las pistas son graduadas y plegadas: ábrelas solo si te atascas.** Ninguna da la causa; orientan el método.
    Material útil ya hecho: `I.trace_table(spans, t0)` (una fila por traza), `I.minute_table`, `span_frame(b)` (celda siguiente), `find_window` y `bubble_up`.
    """)
    code('''
def span_frame(b):
    rows = []
    for s in b.spans:
        a = s["attributes"]
        rows.append({"trace_id": s["trace_id"], "service": (s.get("resource") or {}).get("service.name"), "name": s["name"], "kind": s["kind"], "status": s["status"], "error_type": a.get("error.type"),
                     "minute": int((s["start_unix_nano"] / 1e9 - b.t0) // 60), "dur_s": (s["end_unix_nano"] - s["start_unix_nano"]) / 1e9, "version": a.get("gen_ai.agent.version"),
                     "intent": a.get("supportops.intent"), "tool": a.get("gen_ai.tool.name")})
    return pd.DataFrame(rows)

def run(case, fn):
    """Ejecuta tu diagnóstico, lo corrige y lo muestra."""
    try:
        d = fn(BUNDLES[case]); g = I.grade(case, d, BUNDLES[case])
        print(case, f"{g['score']}/{g['of']}", {k: ("✅" if v else "❌") for k, v in g["checks"].items()}, "· evidencia:", g["evidence_detail"])
        return d
    except NotImplementedError as e:
        print(case, "pendiente:", e)
''')

    md("""
    ### INC-A

    Lee la alerta (`BUNDLES["INC-A"].alert`) y la tabla de métricas. **TODO 3** · `diagnose_a(b)`.
    """)
    md(hint(1, "Compara las métricas con y sin errores: ¿qué señal discrepa? Después mira los spans en `ERROR` agrupados por `service` y `name`: ¿dónde se concentran? Para cuantificar un fenómeno de «repeticiones» cuenta spans de un mismo `name` por `trace_id`."))
    md(hint(2, "Candidatos a causa: `provider_outage` (¿hay `chat` en error?) frente a una dependencia concreta. La amplificación es (media de intentos por traza dentro de la ventana) / (media fuera), contando spans CLIENT `invoke_agent <agente>` del culpable. El culpable se escribe como el `service.name` (p. ej. `supportops-…-agent`)."))
    code('''
def diagnose_a(b):
    # TODO 3: causa (clave de I.CAUSES), ventana, culpable, evidencia {"retry_amplification": ...} y mitigación (clave de I.MITIGATIONS)
    raise NotImplementedError("TODO 3")

d_a = run("INC-A", diagnose_a)
''')

    md("### INC-B\n\n**TODO 4** · `diagnose_b(b)`.")
    md(hint(1, "Es una alerta de coste. Mira el coste por ticket por minuto con `find_window` y después **la forma de las trazas**: `I.trace_table` te da `n_tools` y las herramientas de cada traza."))
    md(hint(2, "Define «bucle» como una traza con ≥ 5 `execute_tool` y una sola herramienta distinta. La evidencia pide `loop_traces` (cuántas) y `cost_ratio` (coste por ticket dentro de la ventana / fuera: usa `b.extra[\"tickets\"]`, con `created_at` en segundos). El culpable es la herramienta que más se repite."))
    code('''
def diagnose_b(b):
    # TODO 4: evidencia {"loop_traces": ..., "cost_ratio": ...}
    raise NotImplementedError("TODO 4")

d_b = run("INC-B", diagnose_b)
''')

    md("### INC-C\n\n**TODO 5** · `diagnose_c(b)`.")
    md(hint(1, "No hay alertas de errores ni de latencia. Mira todas las columnas de `b.metrics`: ¿qué se movió **a mejor**? Luego busca una dimensión por la que partir los spans `invoke_agent`."))
    md(hint(2, "Los spans `invoke_agent` llevan `gen_ai.agent.version`. Para cada traza cuenta sus `execute_tool` y calcula, para las intenciones `order_status`/`refund`, la fracción **sin** herramientas por versión. La evidencia `no_tool_share_after` es esa fracción a partir del minuto en que la versión nueva tiene todo el tráfico (el registro de cambios y los spans te dicen cuándo). El inicio es el primer minuto con la versión nueva."))
    code('''
def diagnose_c(b):
    # TODO 5: evidencia {"no_tool_share_after": ...}
    raise NotImplementedError("TODO 5")

d_c = run("INC-C", diagnose_c)
''')

    md("### INC-D\n\n**TODO 6** · `diagnose_d(b)`. Aquí no hay spans: trabajas con `b.metrics`, `b.extra[\"series_by_metric\"]` y `b.extra[\"label_values\"]`.")
    md(hint(1, "Compara `requests` con `active_series`: ¿es el tráfico? Luego, ¿qué **métrica** concentra el crecimiento y qué **etiqueta** tiene muchos más valores distintos después que antes?"))
    md(hint(2, "`label_values[minuto][métrica][etiqueta] = nº de valores distintos`. La etiqueta culpable es la que aparece en el minuto tardío y no en el temprano con muchos valores. `series_growth` = media de las series activas de los últimos 5 minutos / media de los 9 minutos previos al cambio."))
    code('''
def diagnose_d(b):
    # TODO 6: evidencia {"series_growth": ...}
    raise NotImplementedError("TODO 6")

d_d = run("INC-D", diagnose_d)
''')

    md("### INC-E\n\n**TODO 7** · `diagnose_e(b)`.")
    md(hint(1, "La alerta habla de aristas del grafo y de «coste por traza»; mira `traces_per_ticket` en `b.metrics`. ¿Qué nombre tiene la **raíz** de las trazas antes y después?"))
    md(hint(2, "`I.trace_table` da `root` (nombre del span raíz) y `start_min`. La evidencia `orphan_share_after` es la fracción de trazas posteriores al corte (a partir de 2 minutos después) cuya raíz **no** empieza por `invoke_workflow`. El culpable no tiene un valor único: pon `None`."))
    code('''
def diagnose_e(b):
    # TODO 7: evidencia {"orphan_share_after": ...}
    raise NotImplementedError("TODO 7")

d_e = run("INC-E", diagnose_e)
''')

    md("""
    ---
    ## Rúbrica automática

    Ejecuta esta celda cuando hayas terminado los TODO.
    """)
    code('''
def run_rubric():
    rows = []
    def add(rid, name, ok, detail=""):
        rows.append({"id": rid, "criterio": name, "resultado": "✅" if ok else "❌", "detalle": detail})
    try:
        a1 = find_window([1.0] * 20 + [5.0] * 10 + [1.0] * 10)
        a2 = find_window([1.0] * 30 + [4.0] * 20)
        a3 = find_window(list(np.random.default_rng(0).normal(0, 1, 40)))
        a4 = find_window([5.0] * 12 + [1.0] * 28)
        checks = {"ventana 20-30": a1[:2] == (20, 30), "salto 30-50": a2[:2] == (30, 50), "sin cambio: |t| bajo": abs(a3[2]) < 3.5, "complemento (12, 40)": a4[:2] == (12, 40)}
        add("R1", "find_window: 4 vectores", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R1", "find_window", False, f"{type(e).__name__}: {e}")
    try:
        df = pd.DataFrame({"svc": ["a"] * 30 + ["b"] * 30 + ["c"] * 30, "bad": [True] * 20 + [False] * 10 + [False] * 30 + [False] * 28 + [True] * 2})
        out = bubble_up(df, df["bad"], ["svc"])
        checks = {"primero = a": out.iloc[0]["valor"] == "a", "lift >= 5": out.iloc[0]["lift"] >= 5, "columnas": {"atributo", "valor", "lift", "n malos"} <= set(out.columns)}
        add("R2", "bubble_up: 3 comprobaciones", all(checks.values()), str({k: v for k, v in checks.items() if not v} or f"lift={out.iloc[0]['lift']}"))
    except Exception as e: add("R2", "bubble_up", False, f"{type(e).__name__}: {e}")
    diag = {}
    for rid, case, fn in [("R3", "INC-A", diagnose_a), ("R4", "INC-B", diagnose_b), ("R5", "INC-C", diagnose_c), ("R6", "INC-D", diagnose_d), ("R7", "INC-E", diagnose_e)]:
        try:
            d = fn(BUNDLES[case]); g = I.grade(case, d, BUNDLES[case]); diag[case] = d
            add(rid, f"{case}: diagnóstico", g["score"] >= 4, f"{g['score']}/{g['of']} · fallos: {[k for k, v in g['checks'].items() if not v] or 'ninguno'}")
        except Exception as e: add(rid, f"{case}: diagnóstico", False, f"{type(e).__name__}: {e}")
    try:
        causes = [d["cause"] for d in diag.values()]; mits = [d["mitigation"] for d in diag.values()]
        checks = {"5 causas distintas": len(set(causes)) == 5, "causas y mitigaciones del catálogo": all(c in I.CAUSES for c in causes) and all(m in I.MITIGATIONS for m in mits), "ninguna mitigación «raise_timeouts»": "raise_timeouts" not in mits}
        add("R8", "informe de los cinco diagnósticos", all(checks.values()), str({k: v for k, v in checks.items() if not v} or "todas OK"))
    except Exception as e: add("R8", "informe", False, f"{type(e).__name__}: {e}")
    return pd.DataFrame(rows).set_index("id")
''')
    code('''
display(run_rubric())
''')

    md("""
    ---
    ## Retos extra (nivel experto)

    1. **Sin el registro de cambios**: repite los cinco diagnósticos sin mirar `b.changes`. ¿Cuántos puedes resolver? ¿Qué te falta para los que no?
    2. **Tiempo hasta diagnóstico (TTD)**: cronometra cada diagnóstico y razona qué dato **de más** habrías necesitado (p. ej. `gen_ai.agent.version` en métricas) para acortarlo.
    3. **Contratos**: escribe, para cada incidente, la prueba o alerta que lo habría detectado **antes** de llegar al usuario (por ejemplo, «trazas por ticket == 1» para INC-E) y ejecútala contra los datos.
    4. **Postmortem**: con `supportops.slo.render_postmortem` (módulo 16) escribe uno completo de INC-A con las cifras de tu diagnóstico.
    5. **Crea tu incidente**: define un nuevo fallo en `supportops.incidents` (p. ej. una caída del proveedor con *backoff* mal configurado) y pásaselo a un compañero.

    ## Reflexión (producción e hilo conductor)

    - ¿Qué señal habría **acortado más** tus diagnósticos si hubiera existido desde el principio? ¿Cuánto cuesta añadirla?
    - ¿Qué incidente es más peligroso para un negocio real: el que da errores (INC-A) o el que no da ninguna alerta (INC-C, INC-E)? ¿Cómo lo detectarías en tu empresa?
    - En el capstone (módulo 22) esta mesa se convierte en el **plan de pruebas** de tu plataforma: ¿qué incidente de la mesa debe poder diagnosticar tu arquitectura en menos de 15 minutos?
    """)

    md("""
    ---
    # ⛔ SPOILER — intenta resolverlo primero

    A continuación, la **solución de referencia** completa y ejecutable (redefine las funciones y vuelve a lanzar la rúbrica).
    """)
    code('''
# ===================== SOLUCIÓN DE REFERENCIA =====================
def find_window(x, min_len=5):
    x = np.asarray(x, float); n = len(x); sd = x.std() or 1.0
    c = np.concatenate([[0], np.cumsum(x)]); best, win = 0.0, (0, n)
    for a in range(0, n - min_len + 1):
        for b in range(a + min_len, n + 1):
            n_in, n_out = b - a, n - (b - a)
            if n_out < min_len: continue
            m_in, m_out = (c[b] - c[a]) / n_in, (c[n] - (c[b] - c[a])) / n_out
            t = (m_in - m_out) / (sd * np.sqrt(1 / n_in + 1 / n_out))
            if abs(t) > abs(best): best, win = t, (a, b)
    if win[0] == 0 and win[1] < n: win = (win[1], n)
    return win[0], win[1], float(best)

def bubble_up(df, bad, cols, min_n=5):
    out = []
    for col in cols:
        pb = df[bad][col].value_counts(normalize=True); pg = df[~bad][col].value_counts(normalize=True); nb = df[bad][col].value_counts()
        for v, share in pb.items():
            if nb[v] >= min_n: out.append({"atributo": col, "valor": v, "cuota en malos": round(share, 3), "cuota en buenos": round(pg.get(v, 0.0), 3), "lift": round(share / (pg.get(v, 0.0) + 0.01), 1), "n malos": int(nb[v])})
    return pd.DataFrame(out).sort_values("lift", ascending=False).reset_index(drop=True)

def diagnose_a(b):
    M = pd.DataFrame(b.metrics); a, e, _ = find_window(M["p95_s"])
    sf = span_frame(b); err = sf[(sf["status"] == "ERROR") & sf["name"].str.startswith("execute_tool")]
    culprit = err.groupby("service").size().idxmax()                                      # el servicio con más herramientas en error
    agent = culprit.replace("supportops-", "")
    tt = {r["trace_id"]: r["start_min"] for r in I.trace_table(b.spans, b.t0)}
    c = collections.Counter(s["trace_id"] for s in b.spans if s["name"] == f"invoke_agent {agent}" and s["kind"] == "CLIENT")
    inw = [v for t, v in c.items() if a <= tt[t] < e]; out = [v for t, v in c.items() if tt[t] < a]
    return {"cause": "dependency_timeout_retry_storm", "start_min": a, "end_min": e, "culprit": culprit, "evidence": {"retry_amplification": np.mean(inw) / np.mean(out)}, "mitigation": "circuit_breaker_fallback"}

def diagnose_b(b):
    M = pd.DataFrame(b.metrics); a, e, _ = find_window(M["cost_per_ticket"])
    tt = pd.DataFrame(I.trace_table(b.spans, b.t0))
    loops = tt[(tt["n_tools"] >= 5) & tt["tools"].apply(lambda t: len(set(t)) == 1)]
    tool = collections.Counter(t[0] for t in loops["tools"]).most_common(1)[0][0]
    tk = pd.DataFrame(b.extra["tickets"]); tk["m"] = (tk["created_at"] - b.t0) / 60
    ratio = tk[(tk["m"] >= a) & (tk["m"] < e)]["cost_usd"].mean() / tk[tk["m"] < a]["cost_usd"].mean()
    return {"cause": "tool_loop", "start_min": a, "end_min": e, "culprit": tool, "evidence": {"loop_traces": len(loops), "cost_ratio": ratio}, "mitigation": "loop_guard"}

def diagnose_c(b):
    sf = span_frame(b); ia = sf[sf["name"].str.startswith("invoke_agent")].copy()
    tools = sf[sf["name"].str.startswith("execute_tool")].groupby("trace_id").size()
    ia["n_tools"] = ia["trace_id"].map(tools).fillna(0); ia = ia[ia["intent"].isin(["order_status", "refund"])]
    new = sorted(v for v in ia["version"].dropna().unique())[-1]                       # la versión «más nueva» presente (v2)
    start = int(ia[ia["version"] == new]["minute"].min())
    full = ia[ia["version"] == new].groupby("minute").size().index.min()
    share_by_v = ia.groupby("version")["n_tools"].apply(lambda s: (s == 0).mean())
    late = ia[ia["minute"] >= max(30, start)]                                             # cuando la versión nueva lleva todo el tráfico
    after = (late["n_tools"] == 0).mean()
    return {"cause": "silent_prompt_regression", "start_min": start, "end_min": 59, "culprit": new, "evidence": {"no_tool_share_after": after}, "mitigation": "rollback_release"}

def diagnose_d(b):
    M = pd.DataFrame(b.metrics); a, e, _ = find_window(M["active_series"])
    lv = b.extra["label_values"]; early, late = sorted(lv)
    cand = {(m, l): n for m in lv[late] for l, n in lv[late][m].items() if l not in lv[early].get(m, {})}
    culprit = max(cand.items(), key=lambda kv: kv[1])[0][1]
    growth = M["active_series"].iloc[-5:].mean() / M["active_series"].iloc[a - 10:a - 1].mean()
    return {"cause": "metric_label_cardinality", "start_min": a, "end_min": e, "culprit": culprit, "evidence": {"series_growth": growth}, "mitigation": "drop_label_collector"}

def diagnose_e(b):
    M = pd.DataFrame(b.metrics); a, e, _ = find_window(M["traces_per_ticket"])
    tt = pd.DataFrame(I.trace_table(b.spans, b.t0)); after = tt[tt["start_min"] >= a + 2]
    share = (~after["root"].str.startswith("invoke_workflow")).mean()
    return {"cause": "context_propagation_broken", "start_min": a, "end_min": e, "culprit": None, "evidence": {"orphan_share_after": share}, "mitigation": "restore_propagation"}

D = {c: run(c, f) for c, f in [("INC-A", diagnose_a), ("INC-B", diagnose_b), ("INC-C", diagnose_c), ("INC-D", diagnose_d), ("INC-E", diagnose_e)]}
display(run_rubric())
''')
    nb.save(out)


# =====================================================================================================================
def build_readme() -> None:
    readme = """# Módulo 21 · Masterclass de élite: depuración de producción de agentes

🔴 **Experto** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ Los incidentes son **simulaciones deterministas** del agente de SupportOps (`mock`, semilla fija) con telemetría real del SDK de OpenTelemetry: reproducen la **forma** de cada fallo, no son sistemas reales (≈ 4 tickets/min, valores de memoria del caso D de un modelo simple).
> Los ejemplos de la lección son **variantes** de los de la mesa del proyecto.

No hay herramientas nuevas: hay **criterio**. Un método (bucle de análisis, *bubble-up*, `find_window`), cinco casos de la familia que más duele —**cascada de reintentos, bucle de herramientas, regresión silenciosa, tormenta de cardinalidad y trazas partidas**— con su mitigación **verificada re-ejecutando el incidente**, patrones y antipatrones,
cultura de observabilidad (con una autoevaluación de madurez) y un **compendio de secretos de élite** de los módulos 00-21, con fuentes.

## Objetivos
1. Aplicar el bucle de análisis a un incidente de un agente usando solo telemetría.
2. Detectar cuándo empezó un incidente y qué atributos distinguen a los casos malos.
3. Diagnosticar cascada, bucle, regresión silenciosa, tormenta de cardinalidad y trazas partidas.
4. Verificar una mitigación con datos y prevenir con contratos de telemetría.
5. Elegir patrones, evitar antipatrones y evaluar la madurez de una organización.

## Contenido
| Archivo | Qué es |
|---|---|
| `21_elite_playbook.ipynb` | Lección (15 secciones, 13 gráficos, cinco casos resueltos, 🧠 de élite, compendio consultable, autoevaluación) |
| `21_proyecto_mesa_de_incidentes.ipynb` | Proyecto «mesa de incidentes»: diagnostica 5 incidentes **sin pistas directas** (rúbrica R1-R8, pistas 🪜 solo de método, solución tras ⛔ SPOILER) |
| `COMPENDIO_SECRETOS.md` | Compendio de secretos de élite 00-21 por tema, con módulo y fuente (generado por `build_21.py`) |
| `../supportops/incidents.py` | `build_incident`, `grade`, `trace_table`, `minute_table`, `loop_tickets`, catálogos de causas y mitigaciones (¡la verdad está dentro: no la leas antes de diagnosticar!) |
| `../supportops/tests/test_incidents.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/21-sala-de-guerra.json` | Dashboard «21 · Sala de guerra de SupportOps» (uid `sala-de-guerra`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 9 de la lección y la validación del Collector de la sección 5. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. La sección 9 tarda ≈ 3 min.

## Lecturas
- Majors, Fong-Jones, Miranker (2022), *Observability Engineering* · Carretto (2020), *Edgar* (Netflix Tech Blog) · Sigelman et al. (2010), *Dapper* · Beyer et al., *SRE* cap. 15 y *SRE Workbook* cap. 5 · `danluu/post-mortems`.

## Cómo se conecta
Antes: todo el curso (00-20). Después: el 22 convierte la mesa en el **plan de pruebas** del capstone y reutiliza el compendio como lista de comprobación de la revisión de arquitectura.
"""
    (COURSE / MOD / "README.md").write_text(readme, encoding="utf-8")
    print("OK README", MOD)


if __name__ == "__main__":
    (COURSE / MOD).mkdir(exist_ok=True)
    build_compendium_md()
    build_dashboard()
    build_lesson()
    build_project()
    build_readme()
