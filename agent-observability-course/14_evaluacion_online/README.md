# Módulo 14 · Evaluación online de agentes de IA

🔴 **Experto** · ≈ 4 h 30 min (lección ≈ 2 h 45 min + proyecto ≈ 1 h 45 min)

> ⚠️ El agente y el «juez» son **simulados y deterministas** (`mock`, semilla 42): el juez es un conjunto de reglas con errores realistas
> (falsos negativos/positivos, sesgo de verbosidad y de posición) para poder **medirlos contra la verdad**. Las cifras cambian con un juez real; el método no.

Las señales clásicas (latencia, errores, coste) no ven la **calidad**: una respuesta inventada es `ok`, rápida y barata. Este módulo mide la calidad **en producción** y la convierte en telemetría:
un evaluador asíncrono sobre una **muestra**, el evento `gen_ai.evaluation.result` de la spec GenAI (estado *Development*) asociado al span evaluado, métricas de calidad y un panel en Grafana.

## Objetivos
1. Elegir el tipo de evaluador (reglas, juez LLM, humano, feedback) según coste, latencia y fiabilidad.
2. Implementar a mano un evaluador de *groundedness* y medir su sensibilidad y especificidad.
3. Emitir evaluaciones como telemetría OTel (evento ligado al span evaluado, span enlazado del juez, métricas `supportops.eval.*`).
4. Diseñar un muestreo estratificado y estimar la calidad poblacional sin sesgo (post-estratificación).
5. Medir y corregir los sesgos del juez (verbosidad, posición; corrección de Rogan–Gladen).
6. Interpretar el feedback de usuario (sesgo de respuesta) y calcular el coste de evaluar.

## Contenido
| Archivo | Qué es |
|---|---|
| `14_evaluacion_online.ipynb` | Lección (14 secciones, 10 gráficos, stack real opcional, 🧠 de élite, autoevaluación) |
| `14_proyecto_evaluacion_online.ipynb` | Proyecto: groundedness a mano, estimador post-estratificado, evento validado contra la spec, sondas de sesgo, calibración del juez, tasa de muestreo y panel como código (rúbrica calibrada, pistas 🪜, solución tras ⛔ SPOILER) |
| `../supportops/quality_eval.py` | `CaseCollector`, `RuleJudge`/`MockJudge`/`LLMJudge`, `RateSampler`/`StratifiedSampler`, `OnlineEvaluator`, estadística (Wilson, post-estratificación, Rogan–Gladen), `simulate_feedback` |
| `../supportops/tests/test_quality_eval.py` | Pruebas del módulo |
| `../stack/grafana/dashboards/14-calidad-online.json` | Dashboard «14 · Calidad online» (uid `calidad-online`) |

## Servicios necesarios
- **Sin Docker** (modo degradado): todo salvo la sección 8 de la lección y el paso final del proyecto. Funciona en Colab.
- **Con stack** (opcional): `cd stack && docker compose --profile core --profile metrics up -d`. Grafana: http://localhost:3000 (`admin`/`admin`).
- **Juez real** (opcional): `JUDGE_PROVIDER=anthropic|openai|ollama` + `JUDGE_MODEL` (claves solo por variables de entorno).

## Lecturas
- OpenTelemetry GenAI semantic conventions, evento `gen_ai.evaluation.result` (repo `open-telemetry/semantic-conventions-genai`).
- Zheng et al. (2023), *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* · Panickssery et al. (2024), *LLM Evaluators Recognize and Favor Their Own Generations* · Rogan y Gladen (1978).

## Cómo se conecta
Antes: módulos 04 (GenAI semconv), 09 (métricas), 13 (coste por ticket). Después: el 15 usa el evaluador para detectar regresiones de prompt y construir datasets desde trazas; el 16 convierte la calidad en un SLO con *burn rate*; el 18 decide cuánto evaluar con un presupuesto; el 20 revisa la privacidad de lo que se envía al juez.
