# Módulo 16 · SLOs, alertas e incidentes de agentes de IA

🔴 **Experto** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ Tráfico e incidentes **simulados y deterministas** (`mock`, semilla 42): el agente real procesa 24 h de tickets con un fallo del proveedor LLM y una regresión de prompt inyectados, así que conocemos la verdad de cada alerta.
> Las ventanas del laboratorio en vivo están **comprimidas** (minutos); las de producción (1 h/5 min, 6 h/30 min, 3 d/6 h) se tratan con simulación y aritmética.

De «creo que va mal» a «el presupuesto se agota en 2 horas»: **SLIs específicos de agentes** (disponibilidad, latencia, calidad, coste), **presupuesto de error** y **burn rate multiventana**, comparado con umbrales fijos en un Monte Carlo de 40 meses;
**alertas de Grafana provisionadas como código** (intervalo múltiplo de 10 s, enlace alerta→panel en `annotations`) probadas con un incidente real en el stack; **runbooks**, guardia sostenible y **postmortem sin culpa** con cifras de la telemetría.

## Objetivos
1. Definir SLIs como «eventos buenos / válidos» y fijar SLOs con la línea base medida.
2. Calcular presupuesto, burn rate y tiempo hasta agotarlo; derivar el 14,4 de la SRE Workbook.
3. Implementar y comparar alertas por burn rate (umbral fijo, una ventana, multiventana).
4. Dimensionar ventanas para SLIs de poco volumen (calidad) y entender las quemas lentas.
5. Provisionar reglas de alerta como código y probarlas en vivo.
6. Redactar runbook y postmortem sin culpa.

## Contenido
| Archivo | Qué es |
|---|---|
| `16_slos_alertas_incidentes.ipynb` | Lección (14 secciones, 9 gráficos, incidente en vivo con alertas reales, 🧠 de élite, autoevaluación) |
| `16_proyecto_slos_alertas_incidentes.ipynb` | Proyecto: SLIs, presupuesto, alerta multiventana, regla de Grafana como código, informe del incidente y postmortem (rúbrica, pistas 🪜, solución tras ⛔ SPOILER) |
| `runbooks/` | Runbooks de las alertas (`slo-availability-fast-burn`, `slo-quality-slow-burn`) y plantilla de postmortem |
| `../supportops/slo.py` | `SLO`, burn rate y políticas (`GOOGLE_POLICIES`, `LAB_POLICIES`), `fire_series`, `alert_quality`, `simulate_day`/`simulate_month`, PromQL, `grafana_burn_rule`, `rules_yaml`, `render_postmortem` |
| `../supportops/tests/test_slo.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/16-slos.json` | Dashboard «16 · SLOs de SupportOps» (uid `slo-agente`) |
| `../stack/grafana/provisioning/alerting/16-slo-alerts.yaml` | 8 reglas de alerta de SLO (grupo `supportops-slo`, intervalo 30 s) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 7.1 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`). La sección 7.1 tarda ≈ 3 min.

## Lecturas
- Google, *The Site Reliability Workbook*, cap. 5 «Alerting on SLOs» · *Site Reliability Engineering*, caps. 4, 11 y 15.
- Grafana Labs, alertas multiventana multi-burn-rate · Allspaw (2012), *Blameless PostMortems and a Just Culture*.

## Cómo se conecta
Antes: módulos 09 (métricas), 10 (alertas básicas), 13 (coste), 14 (calidad online), 15 (regresión). Después: el 18 usa el presupuesto para decidir muestreo y retención; el 21 reutiliza los incidentes en la «mesa de incidentes»; el 22 integra SLOs y runbooks en el capstone.
