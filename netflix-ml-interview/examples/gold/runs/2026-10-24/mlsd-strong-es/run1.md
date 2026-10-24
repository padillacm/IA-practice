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
    - {turn_id: 2, quote: "Guardarraíles: la diversidad de filas y la tasa de inicio de reproducción por perfil no deben empeorar"}
    - {turn_id: 2, quote: "¿Coincide este alcance con el tuyo, incluyendo varios perfiles por cuenta y la TV como dispositivo principal?"}
  architecture_data_flow:
    - {turn_id: 4, quote: "Nearline: un procesador de streams sobre el log de eventos de reproducción, Kafka más un motor tipo Flink"}
    - {turn_id: 4, quote: "Las features offline y online salen de las mismas definiciones, y el entrenamiento usa joins point-in-time para evitar fuga de datos."}
    - {turn_id: 4, quote: "Si el ranker excede 150 ms servimos la última página buena en caché de ese perfil, y si no existe, una página de popularidad regional."}
  modeling_choices:
    - {turn_id: 6, quote: "Un modelo transformer secuencial sobre las últimas 50 reproducciones captura el orden, pero cuesta unos 30 ms por lote en GPU y necesita más datos."}
    - {turn_id: 6, quote: "La pérdida es listwise con dos cabezas, inicio de reproducción y finalización"}
    - {turn_id: 6, quote: "Los datos de entrenamiento vienen de impresiones registradas, que están sesgadas por la exposición de la política anterior y por la posición"}
    - {turn_id: 6, quote: "Para elegir entre modelos offline uso NDCG@10 sobre un holdout temporal"}
  scale_reliability_security:
    - {turn_id: 8, quote: "Objetivo de disponibilidad: 99,95% para cargas de página, con p99 por debajo de 300 ms."}
    - {turn_id: 8, quote: "si el almacén de features online cae, el ranker corre con features por defecto calculadas en batch, con menor calidad pero con página"}
    - {turn_id: 8, quote: "Seguridad: las features del historial de visualización se etiquetan como restringidas, el acceso es por servicio y auditado"}
    - {turn_id: 8, quote: "El motor de costo es la inferencia en GPU del codificador secuencial"}
  online_validation_monitoring:
    - {turn_id: 10, quote: "Primero interleaving, que necesita mucho menos tráfico y detecta rápido la preferencia de ranking, pero es una medida relativa"}
    - {turn_id: 10, quote: "me dice qué ranker prefieren los miembros dentro de la misma lista y no dice nada sobre retención."}
    - {turn_id: 10, quote: "Las métricas offline y online pueden discrepar porque el replay offline está sesgado por la política de registro y por la posición"}
    - {turn_id: 10, quote: "mantengo activo el tráfico de exploración epsilon para que los datos sigan sin sesgo."}
    - {turn_id: 10, quote: "Disparador de rollback: un guardarraíl roto o una tasa de fallback superior al 5% durante diez minutos."}
  culture_signals:
    - {turn_id: 12, quote: "puntuar todo en tiempo real multiplica el costo de GPU y ensancha la latencia de cola, con lo que arriesga el objetivo de 300 ms."}
    - {turn_id: 12, quote: "Lo que me haría cambiar: una prueba donde el brazo en tiempo real mejore la retención o los inicios de reproducción por más de lo que justifica el costo."}
    - {turn_id: 12, quote: "Todavía no sé cuánta obsolescencia notan realmente los miembros, así que lo mediría con un A/B sobre la edad de la caché antes de pagar la infraestructura."}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation: pass. Observed level: L5.**

The candidate met the L5 Yes bar on all five core competencies and on culture_signals. No hints were given. The session closed normally: the final interviewer meta shows `phase: closed` and lists no uncovered points.

- **Framing:** before designing anything, the candidate separated the business goal (long-term satisfaction measured by retention) from a daily proxy metric. They stated scale, latency and freshness numbers as assumptions, named guardrails and constraints, and confirmed scope.
- **Architecture:** batch, nearline and online paths, with offline/online feature consistency, and one request traced through a cache and fallback path.
- **Modeling:** a reasoned comparison of model options, a defined loss, and explicit handling of exposure and position bias.
- **Reliability and security:** an availability target, three degraded modes, access control for viewing history and unreleased titles, and a cost driver with a mitigation.
- **Validation:** a complete two-stage plan, with monitoring, explore/exploit and a rollback trigger.

The candidate did not consistently reach L6 bars. Missing L6 elements:
- framing in the wider product and organization, and what they would leave out of the first version;
- the first component to break at 10x traffic;
- regional failure, and owners per failure class;
- a program for many concurrent tests.

The transcript was in Spanish, so the quotes are kept verbatim in Spanish. The scorecard body is written in English, the session language given in the config.

## Scores and evidence

### problem_framing_requirements (core): Y
- T2: "Separaría el objetivo de negocio, la satisfacción del miembro a largo plazo medida con retención, del proxy que puedo optimizar día a día"
- T2: "un presupuesto p99 de 300 ms para la petición de la página"
- T2: "Guardarraíles: la diversidad de filas y la tasa de inicio de reproducción por perfil no deben empeorar"
- T2: "¿Coincide este alcance con el tuyo, incluyendo varios perfiles por cuenta y la TV como dispositivo principal?"

Every L5 element is present, unprompted:
- business goal separated from the proxy, with a reason (raw clicks reward misleading artwork);
- explicit numbers for scale, latency and freshness;
- two guardrails;
- privacy, licensing and cost constraints;
- scope confirmed with the interviewer.

It falls short of L6: there is no statement of what the first version would leave out, and no post-launch continue/stop rule.

### architecture_data_flow (core): Y
- T4: "Nearline: un procesador de streams sobre el log de eventos de reproducción, Kafka más un motor tipo Flink"
- T4: "Las features offline y online salen de las mismas definiciones, y el entrenamiento usa joins point-in-time para evitar fuga de datos."
- T4: "Si el ranker excede 150 ms servimos la última página buena en caché de ese perfil, y si no existe, una página de popularidad regional."

Covered:
- separate batch, nearline and online paths;
- feature consistency through shared definitions and point-in-time joins;
- a technology class for each hop: two-tower model with ANN index, feature store, streaming, key-value cache;
- a full request trace with timing budgets and a two-level fallback.

It falls short of L6: no end-to-end comparison of alternatives on cost and operational burden, no reusable component contracts, and no 10x breaking point.

### modeling_choices (core): Y
- T6: "Un modelo transformer secuencial sobre las últimas 50 reproducciones captura el orden, pero cuesta unos 30 ms por lote en GPU y necesita más datos."
- T6: "La pérdida es listwise con dos cabezas, inicio de reproducción y finalización"
- T6: "Los datos de entrenamiento vienen de impresiones registradas, que están sesgadas por la exposición de la política anterior y por la posición"
- T6: "Para elegir entre modelos offline uso NDCG@10 sobre un holdout temporal"

Covered:
- GBDT compared with a sequential transformer against latency, data volume and cold start;
- the heavy component moved to nearline to fit the 150 ms budget;
- a listwise loss with two heads;
- logged impressions with exposure and position bias handled through position features, propensity logging and an epsilon exploration slice;
- NDCG@10 plus IPS replay as the offline selection metric.

It falls short of L6: no shared-versus-per-task strategy across surfaces, and no experiment that would falsify the main modeling assumption.

### scale_reliability_security (core): Y
- T8: "Objetivo de disponibilidad: 99,95% para cargas de página, con p99 por debajo de 300 ms."
- T8: "si el almacén de features online cae, el ranker corre con features por defecto calculadas en batch, con menor calidad pero con página"
- T8: "Seguridad: las features del historial de visualización se etiquetan como restringidas, el acceso es por servicio y auditado"
- T8: "El motor de costo es la inferencia en GPU del codificador secuencial"

Covered:
- availability and latency targets;
- degraded modes for three failures (ranker, feature store, cold cache);
- access control and auditing for viewing history, with hashed IDs and retention limits;
- unreleased titles filtered in the page assembler;
- GPU cost mitigated by computing embeddings only for active profiles and caching them.

It falls short of L6: the interviewer asked for the security model rather than the candidate raising it, and there is no regional failure design or owner per failure class.

### online_validation_monitoring (core): Y
- T10: "Primero interleaving, que necesita mucho menos tráfico y detecta rápido la preferencia de ranking, pero es una medida relativa"
- T10: "me dice qué ranker prefieren los miembros dentro de la misma lista y no dice nada sobre retención."
- T10: "Las métricas offline y online pueden discrepar porque el replay offline está sesgado por la política de registro y por la posición"
- T10: "mantengo activo el tráfico de exploración epsilon para que los datos sigan sin sesgo."
- T10: "Disparador de rollback: un guardarraíl roto o una tasa de fallback superior al 5% durante diez minutos."

Every L5 element is present:
- interleaving first, then an A/B test;
- interleaving explicitly limited as relative and blind to retention;
- reasons why offline and online metrics disagree, with an ordered diagnosis;
- epsilon exploration;
- monitors in three layers (model, data, system) with a rollback action.

The thresholded rollback criterion touches L6, but the L6 program for many concurrent variants and long-term holdouts was not described.

### culture_signals (non-core): Y
- T12: "puntuar todo en tiempo real multiplica el costo de GPU y ensancha la latencia de cola, con lo que arriesga el objetivo de 300 ms."
- T12: "Lo que me haría cambiar: una prueba donde el brazo en tiempo real mejore la retención o los inicios de reproducción por más de lo que justifica el costo."
- T12: "Todavía no sé cuánta obsolescencia notan realmente los miembros, así que lo mediría con un A/B sobre la edad de la caché antes de pagar la infraestructura."

The interviewer's culture probe at T11 pointed at judgment. The candidate:
- disagreed directly and politely with the product partner, backing the position with cost and latency evidence (judgment, candor);
- conceded the valid case and changed the design with a targeted re-rank;
- named what evidence would change their mind;
- said they did not know how much staleness members notice, and proposed an experiment to find out (candor).

It falls short of L6: no farming for dissent and no named people to inform.

## Hints
None.

## Uncovered signal points
None. The session closed normally (`phase: closed`) with no uncovered points recorded.

## Strengths and gaps

**Strengths:**
- Rigorous, quantified framing before any design.
- Strong awareness of bias in training data and in offline evaluation (position, exposure, propensity, IPS).
- Concrete degraded modes and fallbacks.
- A well-reasoned validation plan with a clear diagnosis for "offline up, A/B flat".
- A calibrated stance with the stakeholder: holds the position and concedes the valid point.

**Gaps toward L6:**
- No view of the wider product or organization, and no statement of what the first version leaves out.
- No end-to-end comparison of architecture alternatives, and no 10x bottleneck.
- No regional failure design or incident ownership.
- No validation program for concurrent variants or long-term holdouts.
- No falsifying experiment for the main modeling assumption.

## Study plan
1. **architecture_data_flow (toward L6).** Practice comparing two end-to-end designs on cost, latency and operational burden, and naming the first component that breaks at 10x traffic. Course: `recsys-course/16_production_serving/`, `recsys-course/08_deep_retrieval_ann/`. Practice stage: `ml-system-design`.
2. **scale_reliability_security (toward L6).** Add regional failover, owners per failure class, and a deployment cost/reliability trade-off with numbers. Course: `recsys-course/16_production_serving/`, `recsys-course/17_mlops_monitoring/`. Practice stage: `ml-system-design`.
3. **online_validation_monitoring and problem_framing_requirements (toward L6).** Design a program for many concurrent tests (pruning, allocation, interference, long-term holdouts). Practice framing with a first-version scope cut and a post-launch decision rule. Course: `recsys-course/15_online_experimentation/`, `recsys-course/14_bandits_rl_ope/`, `recsys-course/19_elite_playbook/`. Practice stage: `ml-system-design`.
