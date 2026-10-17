# Módulo 15 · Calidad y regresión de agentes

🟠 **Avanzado** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ Las versiones de prompt (`v1`, `v2` «regresión silenciosa», `v2.1` hotfix) son **simuladas** sobre el `mock` (`PromptVariantLLM`): reproducen el patrón de una regresión real con el *ground truth* en los datos.
> Las cifras cambian con modelos reales; el método no.

Un prompt «más conciso» baja la latencia y el coste… y hace que el agente se invente datos. Ningún panel clásico lo ve. Este módulo construye la red de seguridad: **dataset de oro desde trazas**, **replay y compuerta de release** con estadística apareada,
**poder estadístico**, **drift** de entrada/comportamiento/calidad (PSI, JS, CUSUM), **canarios con SPRT** y la detección **usando solo telemetría**.

## Objetivos
1. Explicar por qué una regresión de prompt/modelo es silenciosa y qué señales la delatan.
2. Construir un dataset de regresión desde trazas (fallos, feedback negativo, escalados y muestra de buenos), sin duplicados ni PII.
3. Decidir con una compuerta de release (McNemar apareado) y calcular su poder estadístico y el problema del *peeking*.
4. Medir drift de entrada y de comportamiento y detectar caídas de calidad con CUSUM.
5. Diseñar un canario con decisión secuencial (SPRT) y enrutamiento determinista.
6. Localizar una regresión solo con spans y eventos de evaluación (TraceQL/PromQL/LogQL).

## Contenido
| Archivo | Qué es |
|---|---|
| `15_calidad_regresion.ipynb` | Lección (14 secciones, 11 gráficos, canario en vivo con el stack real, 🧠 de élite, autoevaluación) |
| `15_proyecto_calidad_regresion.ipynb` | Proyecto: dataset de oro, compuerta apareada, huella de comportamiento, detección solo con telemetría, canario SPRT y panel como código (rúbrica, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/regression.py` | `PromptVariantLLM`, `select_golden`/`replay`/`ReleaseGate`, estadística (McNemar, potencia, bootstrap), drift (`psi`, `js_divergence`, `ks_2samp`, `Cusum`), canarios (`canary_route`, `sprt_bernoulli`), `trace_shapes`/`version_report`, `LivePipeline` |
| `../supportops/tests/test_regression.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/15-regresion-versiones.json` | Dashboard «15 · Regresión por versión» (uid `regresion-versiones`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 9 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`).

## Lecturas
- OpenTelemetry GenAI semantic conventions: `gen_ai.agent.version`, `gen_ai.prompt.name`/`gen_ai.prompt.version`, evento `gen_ai.evaluation.result`.
- Wald (1945), SPRT · Johari et al. (2017), *Peeking at A/B Tests* · Page (1954), CUSUM · Kohavi et al. (2020), *Trustworthy Online Controlled Experiments* · SRE Workbook, cap. «Canarying Releases».

## Cómo se conecta
Antes: módulo 14 (juez, muestreo, sesgos, eventos de evaluación), 09 (métricas), 07 (TraceQL). Después: el 16 convierte la calidad en un SLO con *burn rate* y alertas; el 18 decide cuánto muestrear y evaluar con un presupuesto; el 21 reutiliza la regresión silenciosa en la «mesa de incidentes».
