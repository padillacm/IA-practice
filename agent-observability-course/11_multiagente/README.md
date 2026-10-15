# Módulo 11 · Observabilidad de sistemas multi-agente

🟠 **Avanzado** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

SupportOps pasa de **un agente** a un **orquestador + 4 especialistas** (`orders`, `billing`, `knowledge`, `escalation`).
Cada agente es un *servicio* con su propio `service.name` y `TelemetryHandle`; el reto es ver **una petición de extremo a
extremo**, atribuir coste sin contar dos veces y contener fallos en cascada.

## Objetivos
1. Modelar un sistema multi-agente como árbol de spans (`invoke_workflow` → `invoke_agent` → `chat`/`execute_tool`) y distinguir **delegación** de **handoff**.
2. Implementar **a mano** la propagación W3C `traceparent` (validación estricta, inyección, extracción) y compararla con el SDK; entender el **baggage**.
3. Demostrar la pérdida de contexto (hilos, colas, procesos) y detectar **trazas huérfanas**.
4. Propagar contexto por una cola entre **dos procesos reales** y elegir entre padre-hijo y *span link*.
5. Calcular el **camino crítico**, el ahorro del *fan-out* y el coste por agente (**solo hojas**, sin doble contabilidad).
6. Cuantificar la **amplificación de reintentos** y el **trabajo zombi**; comparar políticas (timeout, reintentos, disyuntor, *deadline*).
7. Diagnosticar la **causa raíz** recorriendo la cadena de errores.

## Contenido
| Archivo | Qué es |
|---|---|
| `11_multiagente.ipynb` | Lección (12 secciones, 12 gráficos, TraceQL/PromQL probados, 🧠 de élite, autoevaluación) |
| `11_proyecto_multiagente.ipynb` | Proyecto: propagar por una cola, detectar huérfanos, atribuir coste, causa raíz + zombi, elegir política (rúbrica calibrada, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/multiagent.py` | Código del módulo: `build_mesh`, `MultiAgentSupportOps`, `DelegationPolicy`, `RemoteAgentProcess`, W3C a mano, análisis de trazas |
| `../stack/grafana/dashboards/11-multiagente.json` | Dashboard «11 · Multi-agente» como código (uid `multiagent`) |

## Servicios necesarios
- **Sin Docker** (modo degradado, telemetría en memoria): todo salvo la sección 10 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d` (≈ 1,2 GB de RAM). Grafana: http://localhost:3000 (`admin`/`admin`).

## Lecturas
- W3C *Trace Context* y *Baggage* · OpenTelemetry *GenAI semantic conventions* (agentes, estado Development) y *messaging spans*.
- Anthropic Engineering, *How we built our multi-agent research system* · Kim et al., *Towards a Science of Scaling Agent Systems* (arXiv:2512.08296).
- Google SRE Book, cap. 22 *Addressing Cascading Failures* · Amazon Builders' Library, *Timeouts, retries and backoff with jitter*.

## Cómo se conecta
Antes: módulos 03 (SDK, `OTelInstrumentor`), 04 (GenAI semconv), 07-10 (TraceQL, LogQL, métricas, Grafana). Después: el módulo 12 sustituye herramientas locales
por **servidores MCP remotos** (nuevas fronteras de propagación y timeout) y el 13 usa el desglose por agente/modelo para el **FinOps**.
