# Revisión pedagógica 2 · módulos 08-15

Revisor: P2 (08-15). Criterios: carga cognitiva, andamiaje (ejemplo resuelto → práctica guiada → independiente), recuperación espaciada, alineamiento constructivo, Bloom. Solo se editaron **builders** (texto y cajas); ninguna celda ejecutable ni rúbrica cambió, así que no hizo falta reejecutar. `check_course.py`: Todo OK.

## Resumen
Los módulos ya tenían buena base: intuición con tabla de analogías ML / backend / SRE, ≥ 6 gráficos con «👀 Qué debes observar», autoevaluación con Cálculo / Diagnóstico / Transferencia y proyectos con rúbrica. Los huecos reales eran de **andamiaje y de alineamiento**:

1. **Rutas «núcleo vs ampliación» que contradecían el proyecto** (09 y 10 declaraban «ampliación» secciones que el proyecto exige: exemplars y nombres Prometheus en 09; variables y alertas en 10). Reescritas como dos sesiones A/B; añadidas en 11 y 12 (90 y 75 celdas); duraciones de 11 y 12 corregidas (≈ 5 h).
2. **TODOs difíciles sin pistas graduadas**: faltaban en 08 (T3, T4), 09 (T6), 10 (T4, T6), 12 (T6), 14 (T3-T6, el módulo con menos andamiaje) y 15 (T2, T3, T5, T6). Añadidas 🪜 Pista 1 (idea) y 2 (casi la API), sin dar la solución.
3. **🔁 solo de recuerdo**: cada lección tiene ahora una 4.ª pregunta de aplicación, diagnóstico o cálculo que enlaza con un módulo no inmediato (08→03; 09→08; 10→07; 11→08; 12→11; 13→10; 14→13; 15→08/09).
4. **Ejemplo resuelto antes de la fórmula** en 13 (sección 1.1: ticket de 3 llamadas a mano + predicción del bucle), porque la fórmula con caché llegaba sin ejemplo numérico previo.
5. «👀 Qué debes observar» tras el gráfico final de los proyectos 08, 09 y 10 (11-15 no tienen gráficos).
6. Consistencia: «verdad de terreno (*ground truth*)» unificado (08 decía «verdad de campo»); cabeceras de caja duplicadas («Secretos de la élite · Secretos de la élite») corregidas en 11-13.

## Detalle por módulo
- **08 Loki/LogQL:** pistas T3 (cuatro consultas) y T4a/b; 🔁 Q4 (obtener `trace_id` en hex, necesario para el TODO 1); 👀 en proyecto (picos de 5xx en los minutos 2-4).
- **09 Métricas:** la lección tiene 104 celdas → Sesión A (1, 2.2, 3, 5) y B (4, 6, 7, 8), ampliación (2.1, 3.4, 9, 10); pistas T6 (forma fija de PromQL y reglas de traducción de nombres, incl. `USD`); 🔁 Q4 (por qué alertar con métrica y no con LogQL); 👀 en proyecto.
- **10 Grafana:** ruta corregida; pistas T4 (trampa de llaves en f-strings) y T6; 🔁 Q4 TraceQL; 👀 en proyecto.
- **11 Multiagente:** ruta A (1-4, 7) / B (8, 9) / ampliación (5, 6, 10-12); duración ≈ 5 h; 🔁 Q4 (LogQL por `trace_id` y qué ocurre con propagación rota).
- **12 MCP:** ruta A (1-5) / B (6-10) / opcional (11); pista T6; 🔁 Q4 (hilos y `contextvars`).
- **13 FinOps:** sección 1.1 con cálculo a mano (0,01155 USD vs 0,0009625 USD; bucle ×3,3) y 🔁 Q4 (`rate()` sobre contador de coste).
- **14 Evaluación online:** 8 pistas nuevas (T3-T6); 🔁 Q4 de cálculo (sobrecoste de evaluar = tasa × coste_juez/coste_agente).
- **15 Calidad/regresión:** 8 pistas nuevas (pareado/McNemar, huella y deriva, SPRT, panel); 🔁 Q4 (`gen_ai.agent.version`: etiqueta en métrica, metadato en Loki).

## Pendientes (no abordados; cambios grandes)
- 09 (≈ 100 celdas) y 11 (≈ 90) siguen siendo largos; lo sano sería partirlos en dos cuadernos (A/B). Se dejó la ruta como mitigación.
- Los proyectos 11-15 no tienen gráficos propios: podrían añadir una visualización del resultado (p. ej. curva de Λ del SPRT en 15, árbol de agentes en 11).
- El hilo SupportOps es coherente (mismo agente, semilla 42, lote de 120 tickets, nombres `supportops_*`), pero cada proyecto reconstruye el entorno en su Paso 0; no hay objeto «SupportOps v-N» acumulativo entre proyectos.
- El proyecto 14 concentra 7 TODOs en 1 h 45 min: es el más apretado.

## No evaluado
No se ejecutó ningún notebook (solo cambió texto); el tiempo real por módulo es estimación razonada por nº de celdas y densidad, no medición con alumnos.

## Tabla para la guía de estudio (horas reales estimadas, lección + proyecto)
| Módulo | Horas reales | Nivel | Prerrequisitos | Conceptos clave |
|---|---|---|---|---|
| 08 Loki y LogQL | 5 h | 🟡 | 02, 05, 07 | stream, etiqueta vs *structured metadata* vs línea, cardinalidad de streams, LogQL (selector, filtros, `json`/`logfmt`, `unwrap`), logging estructurado, correlación `trace_id`, coste de consulta |
| 09 Métricas | 5,5 h (4,5 h núcleo) | 🟡 | 02, 03, 04, 05 | serie, contador/histograma/gauge, `rate()`, `histogram_quantile()`, *buckets*, temporalidad cumulative/delta, traducción de nombres OTel→Prometheus, RED + GenAI, exemplars, presupuesto de series, histogramas nativos, Mimir |
| 10 Grafana | 5 h | 🟡 | 07, 08, 09 | dashboard como código, *provisioning*, variables, `$__rate_interval`, data links / correlaciones, Explore, alertas aprovisionadas |
| 11 Multi-agente | 5,5 h | 🟠 | 02, 03, 04, 07-10 | orquestador/subagentes, delegación vs *handoff*, `traceparent`, trazas huérfanas, padre-hijo vs *span link*, camino crítico, cascada, trabajo zombi, *baggage*, contar tokens en hojas |
| 12 MCP y herramientas | 5,5 h | 🟠 | 03, 04, 11 | MCP, JSON-RPC, convenciones semánticas MCP (Development), middleware de servidor, contexto en `_meta`, `contextvars` e hilos, idempotencia, auditoría, huella y deriva de herramientas, PII en telemetría |
| 13 Costes y FinOps | 4,5 h | 🟠 | 03, 04, 09, 10, 11 | tokens→USD, caché de prompts y punto de equilibrio, atribución, unidad económica, topes y presupuestos, bucles caros, alerta de desvío |
| 14 Evaluación online | 5 h | 🟠 | 04, 08, 09, 10, 13 | evaluadores (reglas, LLM-as-judge), sensibilidad/especificidad, Rogan–Gladen, sesgos del juez, muestreo estratificado y post-estratificación, evento `gen_ai.evaluation.result`, feedback, coste de evaluar |
| 15 Calidad y regresión | 5 h | 🟠 | 07, 09, 13, 14 | regresión silenciosa, dataset de oro desde trazas, *replay*, McNemar apareado, poder estadístico y *peeking*, drift (entrada, comportamiento, calidad/CUSUM), huella de comportamiento, canario con SPRT |
