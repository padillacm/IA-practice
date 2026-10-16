# Runbook · SLO de disponibilidad: quema rápida (página)

**Alerta:** `SLO availability · fast-burn (×14.4)` · **Severidad:** page · **Servicio:** `supportops-agent` · **Dashboard:** `16 · SLOs de SupportOps` (uid `slo-agente`)

## Qué significa
Más del 14,4 % de los tickets (con objetivo del 99 %) terminan en `error`, `degraded` o `max_steps` **ahora mismo** (ventana larga) **y** el problema sigue (ventana corta).
A este ritmo el presupuesto de error del periodo se agota en horas, no en semanas. Alguien está esperando una respuesta que no llega.

## Primeros 5 minutos (no diagnostiques, orienta)
1. Abre el dashboard `slo-agente`: ¿qué SLO arde? Si **solo** arde disponibilidad, mira la fila «Contexto».
2. ¿Hay un **despliegue** reciente? (`gen_ai.agent.version`, calendario de cambios). Si sí → **revierte primero, investiga después**.
3. Tipo de error dominante (PromQL): `sum by (error_type) (rate(gen_ai_client_inference_duration_seconds_count{service_name="supportops-agent",error_type!=""}[5m]))`.
4. Una traza con error (TraceQL): `{ resource.service.name = "supportops-agent" && status = error } | select(span.error.type, span.http.response.status_code)`.

## Árbol de diagnóstico
| Si ves… | Probable causa | Acción |
|---|---|---|
| `error.type=server_error`, `http.response.status_code=5xx` en los `chat` | Proveedor LLM degradado | Activar el modelo de reserva / `DowngradeLLM`; abrir caso con el proveedor; comunicar |
| `error.type=rate_limit` (429) | Cuota agotada o tráfico anómalo | Subir cuota, activar límites por cliente, revisar bucles (módulo 13) |
| `execute_tool` con `error.type=timeout`/`upstream_500` | Herramienta o API aguas abajo | Circuit breaker, modo degradado (escalar a humano), avisar al equipo propietario |
| Errores solo en una versión | Regresión de despliegue | Rollback del canario |
| Sin tráfico (`rate=0`) | Fallo aguas arriba o telemetría rota | Comprobar Collector (`otelcol_receiver_accepted_spans`) y balanceador |

## Mitigación
- Objetivo: **reducir el impacto**, no encontrar la causa raíz. Rollback, conmutación a modelo de reserva, escalado a humanos, reducción de carga.
- Anuncia en el canal de incidentes: impacto, hipótesis, siguiente actualización en 15 min.

## Escalado
Si no hay mitigación en **30 min**, escalar al responsable de guardia secundaria. SEV-1 si el impacto supera el 50 % de los tickets durante > 15 min.

## Después
Abrir postmortem sin culpa (`postmortem-template.md`) en 48 h. Revisar si la alerta saltó a tiempo (TTD) y si este runbook fue suficiente.
