# Módulo 12 · Trazas a través de servidores MCP y herramientas remotas

🟠 **Avanzado** · ≈ 5 h (lección ≈ 3 h 15 min + proyecto ≈ 1 h 45 min; ruta en dos sesiones)

Las herramientas de pedidos de SupportOps pasan de funciones locales a un **servidor MCP** (SDK oficial de Python, `mcp` 2.x) que corre
como **proceso aparte**. El reto: seguir una llamada a través de la frontera de proceso, entender qué emite ya el SDK, distinguir los
tres tipos de fallo, proteger los reintentos de herramientas destructivas y aplicar seguridad a la telemetría.

## Objetivos
1. Explicar MCP (clientes, servidores, herramientas, transportes) y por qué una herramienta remota rompe el tracing si no se propaga el contexto.
2. Construir un servidor MCP con el SDK y ejecutarlo como proceso hijo por stdio, con su propia telemetría.
3. Medir los spans del SDK en cliente y servidor y compararlos con las convenciones semánticas de MCP (estado **Development**).
4. Unir la traza del servidor con la del agente; detectar y corregir la pérdida de contexto en hilos.
5. Distinguir error de herramienta (`isError`), *timeout* y error de protocolo; medir el **trabajo zombi**.
6. Idempotencia y auditoría de herramientas destructivas.
7. Seguridad: lista blanca/redacción de argumentos, política de confianza del contexto remoto, huella de herramientas (*rug pull*).
8. Métrica `mcp.*.operation.duration`, dashboard y TraceQL de «traza partida».

## Contenido
| Archivo | Qué es |
|---|---|
| `12_mcp_tools.ipynb` | Lección (11 secciones, 8+ gráficos, medidas reales spec-vs-SDK, 🧠 de élite, autoevaluación) |
| `12_proyecto_mcp_tools.ipynb` | Proyecto: redacción de argumentos, middleware de política/auditoría, informe de unión de trazas, `safe_call` con idempotencia, huella de herramientas, contrato con la spec (rúbrica calibrada, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/mcp_orders.py` | Servidor MCP de pedidos, `McpServerProcess`, `McpToolBridge`, `WallClockInstrumentor`, middleware, política de contexto |
| `../stack/grafana/dashboards/12-mcp-tools.json` | Dashboard «12 · MCP y herramientas remotas» (uid `mcp-tools`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 11 y el paso final del proyecto. Lanza un proceso hijo por stdio (funciona en Colab).
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`).
- Dependencia extra: `pip install "mcp>=2,<3"` (la 1.x tiene otra API). El notebook lo instala.

## Lecturas
- MCP: especificación y **SEP-414** (contexto de traza en `_meta`) · OpenTelemetry: convenciones semánticas de MCP (Development) y spans de agentes (`execute_tool`).
- SDK de Python de MCP v2 · Invariant Labs, *Tool Poisoning Attacks* · W3C *Trace Context*.

## Cómo se conecta
Antes: módulo 11 (propagación W3C, trazas partidas, resiliencia). Después: el módulo 13 atribuye coste por agente/herramienta/modelo y el 20 trata la inyección
de instrucciones y la PII con más profundidad.
