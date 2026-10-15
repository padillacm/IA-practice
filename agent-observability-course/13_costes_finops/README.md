# Módulo 13 · Costes y FinOps de agentes de IA

🟠 **Avanzado** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ **Todos los precios del módulo son ILUSTRATIVOS** (tabla configurable, no de ningún proveedor ni fecha). Cárgalos de tu proveedor con
> `PriceTable.from_json(...)` o `SUPPORTOPS_PRICES_FILE`; cambian con frecuencia y por modelo (incluidos los multiplicadores de caché).

De tokens a dinero: una tabla de precios configurable, **atribución** por cliente/*feature*/modelo/agente sin disparar la cardinalidad, **caché de prompts**
(ahorro, punto de equilibrio y cómo se rompe), **presupuestos y topes** (por ticket, cliente y periodo, con degradación de modelo y *burn rate*),
**detección de bucles caros** y un **panel de FinOps con alerta de desvío**.

## Objetivos
1. Calcular el coste de una llamada/ticket con una tabla de precios (con lectura/escritura de caché) y reconciliarlo con el agente.
2. Normalizar el `usage` de una API a la semántica de la spec GenAI (la entrada **incluye** la caché).
3. Atribuir el gasto eligiendo la señal correcta (métricas, logs o trazas) y medir la unidad económica (coste por ticket **resuelto**).
4. Medir el ahorro de la caché, su punto de equilibrio y los modos en que se rompe.
5. Diseñar topes y presupuestos (burn rate, previsión) y degradación de modelo.
6. Detectar y cortar bucles de herramientas (post-hoc y en línea).
7. Publicar el coste como telemetría OpenTelemetry y construir panel + alerta de desvío.

## Contenido
| Archivo | Qué es |
|---|---|
| `13_costes_finops.ipynb` | Lección (9 secciones, 10+ gráficos, simulación de un mes, 🧠 de élite, autoevaluación) |
| `13_proyecto_costes_finops.ipynb` | Proyecto: `cost_breakdown`, atribución, tope por ticket, informe de bucles, alerta de desvío y panel como código (rúbrica calibrada, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/finops.py` | `PriceTable` (ilustrativa/configurable), `CacheSimulator`, `FinOpsInstrumentor`, `CostLedger`, `BudgetGuard`/`BudgetPool`, `DowngradeLLM`, `LoopGuard`, `cost_drift_alert`, regla de alerta de Grafana |
| `../stack/grafana/dashboards/13-finops.json` | Dashboard «13 · FinOps» (uid `finops`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 9 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`).

## Lecturas
- Anthropic, documentación de *prompt caching* (campos de uso, multiplicadores, TTL, mínimos, invalidación) · OpenTelemetry GenAI semconv (`cache_read`/`cache_write`).
- FinOps Foundation, *Optimizing GenAI Usage* · Google SRE Workbook, *Alerting on SLOs* (burn rate).

## Cómo se conecta
Antes: módulo 09 (cardinalidad, métricas), 11 (coste por agente, contar solo hojas), 12 (herramientas con coste propio). Después: el 14 combina coste y calidad (¿ahorrar sin empeorar?),
el 16 convierte el coste en un SLO con *burn rate* y el 18 mide el coste del propio stack de observabilidad.
