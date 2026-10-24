---
instance_id: 01-ml-system-design@design
stage: ml-system-design
variant: design
level: L5
rubric_version: 1
recommendation: pass
level_observed: L5
scores:
  problem_framing_requirements: Y
  architecture_data_flow: Y
  modeling_choices: Y
  scale_reliability_security: Y
  online_validation_monitoring: Y
  culture_signals: Y
evidence:
  problem_framing_requirements:
    - {turn_id: 2, quote: "Separaría el objetivo de negocio, la satisfacción del miembro a largo plazo medida con retención, del proxy que puedo optimizar día a día"}
    - {turn_id: 2, quote: "un presupuesto p99 de 300 ms para la petición de la página"}
    - {turn_id: 2, quote: "Guardarraíles: la diversidad de filas y la tasa de inicio de reproducción por perfil no deben empeorar, y el costo por mil peticiones se mantiene plano."}
    - {turn_id: 2, quote: "¿Coincide este alcance con el tuyo, incluyendo varios perfiles por cuenta y la TV como dispositivo principal?"}
  architecture_data_flow:
    - {turn_id: 4, quote: "Usaría tres rutas."}
    - {turn_id: 4, quote: "Las features offline y online salen de las mismas definiciones, y el entrenamiento usa joins point-in-time para evitar fuga de datos."}
    - {turn_id: 4, quote: "el servicio de página lee filas de candidatos precalculadas de una caché clave-valor indexada por id de perfil"}
    - {turn_id: 4, quote: "Si el ranker excede 150 ms servimos la última página buena en caché de ese perfil, y si no existe, una página de popularidad regional."}
  modeling_choices:
    - {turn_id: 6, quote: "Un árbol con gradient boosting sobre features diseñadas es barato y maneja el arranque en frío mediante metadatos, pero es débil con el orden de visualización."}
    - {turn_id: 6, quote: "La pérdida es listwise con dos cabezas, inicio de reproducción y finalización, combinadas con pesos que ajusto contra retención en los tests."}
    - {turn_id: 6, quote: "Los datos de entrenamiento vienen de impresiones registradas, que están sesgadas por la exposición de la política anterior y por la posición"}
    - {turn_id: 6, quote: "Para elegir entre modelos offline uso NDCG@10 sobre un holdout temporal"}
  scale_reliability_security:
    - {turn_id: 8, quote: "Objetivo de disponibilidad: 99,95% para cargas de página, con p99 por debajo de 300 ms."}
    - {turn_id: 8, quote: "si el almacén de features online cae, el ranker corre con features por defecto calculadas en batch, con menor calidad pero con página"}
    - {turn_id: 8, quote: "las features del historial de visualización se etiquetan como restringidas, el acceso es por servicio y auditado"}
    - {turn_id: 8, quote: "El motor de costo es la inferencia en GPU del codificador secuencial"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "Primero interleaving, que necesita mucho menos tráfico y detecta rápido la preferencia de ranking, pero es una medida relativa"}
    - {turn_id: 10, quote: "me dice qué ranker prefieren los miembros dentro de la misma lista y no dice nada sobre retención."}
    - {turn_id: 10, quote: "Las métricas offline y online pueden discrepar porque el replay offline está sesgado por la política de registro y por la posición"}
    - {turn_id: 10, quote: "mantengo activo el tráfico de exploración epsilon para que los datos sigan sin sesgo."}
    - {turn_id: 10, quote: "Disparador de rollback: un guardarraíl roto o una tasa de fallback superior al 5% durante diez minutos."}
  culture_signals:
    - {turn_id: 12, quote: "Mantendría el enfoque híbrido pero cambiaría una cosa."}
    - {turn_id: 12, quote: "El socio tiene razón en que la obsolescencia duele en un caso"}
    - {turn_id: 12, quote: "Lo que me haría cambiar: una prueba donde el brazo en tiempo real mejore la retención o los inicios de reproducción por más de lo que justifica el costo."}
    - {turn_id: 12, quote: "Todavía no sé cuánta obsolescencia notan realmente los miembros, así que lo mediría con un A/B sobre la edad de la caché antes de pagar la infraestructura."}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary

**Recommendation: pass. Observed level: L5.**

The candidate designed the personalized homepage (rows, titles and their order) from start to finish and met the L5 Yes bar on all five core competencies and on culture signals, with no hints. The interview was conducted in Spanish, so all quotes below are verbatim Spanish. The final interviewer meta shows `phase: closed` and lists no uncovered points, so this was a normal close.

- **Framing:** the candidate fixed the objective, explicit assumptions, guardrails and constraints before building anything, then confirmed the scope with the interviewer.
- **Architecture:** batch, nearline and online paths with consistent offline and online features, plus one request traced through cache and fallback paths.
- **Modeling:** two ranker options compared against the latency budget, cold start and data volume. The loss was defined, exposure and position bias were handled, and the offline selection metric was named.
- **Reliability:** an availability target, three degraded modes, access control for sensitive data and a GPU cost mitigation.
- **Validation:** interleaving first, then an A/B test, with the limits of interleaving stated and monitoring split into three layers.

No competency reached the L6 bar with specific evidence, so the observed level stays at L5.

## Scores and evidence

### problem_framing_requirements (core): Y
- T2: "Separaría el objetivo de negocio, la satisfacción del miembro a largo plazo medida con retención, del proxy que puedo optimizar día a día"
- T2: "un presupuesto p99 de 300 ms para la petición de la página"
- T2: "Guardarraíles: la diversidad de filas y la tasa de inicio de reproducción por perfil no deben empeorar, y el costo por mil peticiones se mantiene plano."
- T2: "¿Coincide este alcance con el tuyo, incluyendo varios perfiles por cuenta y la TV como dispositivo principal?"

Every part of the L5 bar is present, without prompting:
- business goal (retention) kept separate from the proxy (qualified starts plus completion);
- scale, latency and freshness numbers stated as assumptions;
- guardrails (row diversity, play-start rate, cost);
- constraints (privacy of viewing history, regional licensing);
- scope confirmed with the interviewer.

It falls short of L6: the candidate did not say what they would leave out of v1, gave no continue/stop rule after launch, and did not place the work among adjacent surfaces or teams.

### architecture_data_flow (core): Y
- T4: "Usaría tres rutas."
- T4: "Las features offline y online salen de las mismas definiciones, y el entrenamiento usa joins point-in-time para evitar fuga de datos."
- T4: "el servicio de página lee filas de candidatos precalculadas de una caché clave-valor indexada por id de perfil"
- T4: "Si el ranker excede 150 ms servimos la última página buena en caché de ese perfil, y si no existe, una página de popularidad regional."

The design separates batch, nearline (Kafka plus a Flink-style engine) and online paths. It names the technology class for each hop (ANN index, feature store, key-value cache, low-latency store) and specifies feature consistency through shared definitions and point-in-time joins. One request is traced from the TV app to page assembly, including the fallback path.

It falls short of L6: there were no reusable versioned contracts, no comparison of two full designs, and no answer to which component breaks first at 10 times the traffic.

### modeling_choices (core): Y
- T6: "Un árbol con gradient boosting sobre features diseñadas es barato y maneja el arranque en frío mediante metadatos, pero es débil con el orden de visualización."
- T6: "La pérdida es listwise con dos cabezas, inicio de reproducción y finalización, combinadas con pesos que ajusto contra retención en los tests."
- T6: "Los datos de entrenamiento vienen de impresiones registradas, que están sesgadas por la exposición de la política anterior y por la posición"
- T6: "Para elegir entre modelos offline uso NDCG@10 sobre un holdout temporal"

The candidate compared GBDT against a sequential transformer on cost, cold start, sequence modeling and the 150 ms budget, and moved the heavy encoder to nearline. Bias handling was concrete:
- the loss is listwise with two heads;
- position and propensity are logged, and position is a feature neutralized at inference;
- an epsilon slice of random traffic gives unbiased data, with IPS replay on that slice;
- NDCG@10 on a temporal holdout is the selection metric.

It falls short of L6: there was no shared-versus-per-task strategy across surfaces, no estimate of gain against cost, and no experiment that would falsify the main modeling assumption.

### scale_reliability_security (core): Y
- T8: "Objetivo de disponibilidad: 99,95% para cargas de página, con p99 por debajo de 300 ms."
- T8: "si el almacén de features online cae, el ranker corre con features por defecto calculadas en batch, con menor calidad pero con página"
- T8: "las features del historial de visualización se etiquetan como restringidas, el acceso es por servicio y auditado"
- T8: "El motor de costo es la inferencia en GPU del codificador secuencial"

The candidate set an availability target and a latency target, and described degraded modes for three failures: ranker, feature store and cold cache. Viewing history is access-controlled, and unreleased titles are filtered in the page assembler. The cost driver is GPU encoding, mitigated by caching the encoding for profiles active in the last day.

It falls short of L6: classification, auditing and retention were covered only after the interviewer asked about security, and there was no regional failover, no owner per failure class, and no numeric comparison of deployment options.

### online_validation_monitoring (core): Y
- T10: "Primero interleaving, que necesita mucho menos tráfico y detecta rápido la preferencia de ranking, pero es una medida relativa"
- T10: "me dice qué ranker prefieren los miembros dentro de la misma lista y no dice nada sobre retención."
- T10: "Las métricas offline y online pueden discrepar porque el replay offline está sesgado por la política de registro y por la posición"
- T10: "mantengo activo el tráfico de exploración epsilon para que los datos sigan sin sesgo."
- T10: "Disparador de rollback: un guardarraíl roto o una tasa de fallback superior al 5% durante diez minutos."

All elements of the L5 bar are present:
- interleaving first, then an A/B test, with interleaving stated to be relative and blind to retention;
- reasons why offline and online metrics can disagree, and a diagnostic order (training/serving skew, holdout exposure, segment concentration);
- epsilon exploration kept on;
- monitoring in three layers (model quality, data, system), with a rollback trigger.

There is some L6 signal in the rollback thresholds, but no program for many concurrent variants or long-term holdouts, so this stays at Y.

### culture_signals (non-core): Y
- T12: "Mantendría el enfoque híbrido pero cambiaría una cosa."
- T12: "El socio tiene razón en que la obsolescencia duele en un caso"
- T12: "Lo que me haría cambiar: una prueba donde el brazo en tiempo real mejore la retención o los inicios de reproducción por más de lo que justifica el costo."
- T12: "Todavía no sé cuánta obsolescencia notan realmente los miembros, así que lo mediría con un A/B sobre la edad de la caché antes de pagar la infraestructura."

These lines show the memo values judgment, candor and courage. The candidate disagreed directly and politely with the product partner, defended the hybrid design on cost and tail latency, and conceded the valid case with a targeted re-rank. They also named the evidence that would change their mind and said "I do not know" (todavía no sé) with a concrete plan to find out.

It falls short of L6: there was no explicit accepted risk with a named person to inform, and no plan to seek out dissent before committing.

## Hints

None.

## Uncovered signal points

None. The stage closed normally (`phase: closed`) with no uncovered points recorded.

## Strengths and gaps

**Strengths**
- Disciplined framing: the candidate quantified assumptions and set guardrails before any design.
- A coherent three-path architecture with explicit consistency and fallback behavior.
- Mature handling of exposure and position bias: propensity logging, epsilon exploration and IPS replay.
- Clear limits of interleaving, and a structured diagnosis when offline and online results disagree.
- Balanced pushback with a stakeholder, including a partial concession and a falsifiable condition for changing course.

**Gaps (toward L6)**
- No explicit v1 scope cuts and no continue/stop decision rule after launch.
- No "what breaks first at 10x" analysis, and no comparison of two end-to-end alternatives.
- The security and privacy model came only after prompting, and there was no regional-failure or incident-ownership design.
- No validation program for many concurrent variants (pruning, interference, long-term holdouts).
- No quantified gain-versus-cost estimate for the modeling choice, and no falsification experiment.

## Study plan

1. **Framing at L6 scope (problem_framing_requirements, core):** practice stating what you leave out of v1, a continue/stop rule after launch, and the metrics of adjacent surfaces and teams. Modules: `recsys-course/19_elite_playbook/`, `recsys-course/18_capstone/`, `recsys-course/00_intro/`. Practice stage: `ml-system-design`.
2. **Architecture and reliability at scale (architecture_data_flow, scale_reliability_security, core):** practice naming the first component to break at 10 times the traffic, comparing two full designs on cost, latency and operational load, and designing regional failover with owners per failure class. Modules: `recsys-course/16_production_serving/`, `recsys-course/17_mlops_monitoring/`, `recsys-course/08_deep_retrieval_ann/`. Practice stage: `ml-system-design`.
3. **Validation programs (online_validation_monitoring, core):** practice running many concurrent variants with pruning rules, traffic allocation, test interference and long-term holdouts, and auditing offline/online metric alignment over time. Modules: `recsys-course/15_online_experimentation/`, `recsys-course/14_bandits_rl_ope/`, `recsys-course/17_mlops_monitoring/`. Practice stage: `ml-system-design`.

Additional: for modeling_choices, practice deciding between a shared representation and per-task models, and quantifying the expected gain (`recsys-course/07_learning_to_rank_multitask/`, `recsys-course/09_sequential/`). For culture_signals, practice naming the risk you accept, who you would inform, and how you would seek dissent before committing (practice stage `culture`; Netflix culture memo: jobs.netflix.com/culture).
