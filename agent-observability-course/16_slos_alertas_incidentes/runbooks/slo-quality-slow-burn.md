# Runbook · SLO de calidad: quema lenta (ticket)

**Alerta:** `SLO quality · slow-burn (×3)` · **Severidad:** ticket (no despierta a nadie) · **Servicio:** `supportops-agent` / `supportops-evaluator`

## Qué significa
La fracción de respuestas **fundamentadas** (groundedness) evaluadas por el juez baja del objetivo: el presupuesto de calidad se consume al menos 3× más rápido de lo sostenible.
Es el patrón de la **regresión silenciosa** (módulo 15): latencia y errores parecen normales.

## Primeros pasos (horas de trabajo, no minutos)
1. ¿Cambió algo? Compara calidad **por versión** (`gen_ai_agent_version`) en el dashboard `regresion-versiones` (uid): una versión por debajo de otra = regresión de despliegue.
2. ¿Está sano el **juez**? `supportops_eval_errors_total`, cobertura (`sampled/population`) y un cambio de versión del juez. Una caída de calidad sin cambios en el agente suele ser el juez.
3. Huella de comportamiento: herramientas por ticket y `no_tool_rate` (`gen_ai_invoke_agent_tool_calls_*`). Una caída señala que el agente deja de consultar.
4. Trazas culpables (TraceQL): `{ name =~ "invoke_agent.*" && span.supportops.tool_calls = 0 && span.supportops.intent =~ "order_status|refund" }`.

## Acciones
- Regresión de versión → revertir el prompt/modelo (o reducir el canario) y añadir los casos al dataset de oro.
- Drift de entrada (temas nuevos) → ampliar la base de conocimiento; no es un rollback.
- Juez roto → corregir y **recalibrar** antes de confiar en la serie.

## Escalado
Si el SLO de calidad lleva > 24 h por encima de 6× → promover la alerta a página y congelar los despliegues (política de presupuesto agotado).
