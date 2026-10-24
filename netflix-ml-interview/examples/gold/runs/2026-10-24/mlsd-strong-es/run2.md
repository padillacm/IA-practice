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
    - {turn_id: 4, quote: "el servicio de página lee filas de candidatos precalculadas de una caché clave-valor indexada por id de perfil"}
    - {turn_id: 4, quote: "Las features offline y online salen de las mismas definiciones, y el entrenamiento usa joins point-in-time para evitar fuga de datos."}
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
    - {turn_id: 10, quote: "me dice qué ranker prefieren los miembros dentro de la misma lista y no dice nada sobre retención"}
    - {turn_id: 10, quote: "Las métricas offline y online pueden discrepar porque el replay offline está sesgado por la política de registro y por la posición"}
    - {turn_id: 10, quote: "mantengo activo el tráfico de exploración epsilon para que los datos sigan sin sesgo"}
    - {turn_id: 10, quote: "Disparador de rollback: un guardarraíl roto o una tasa de fallback superior al 5% durante diez minutos."}
  culture_signals:
    - {turn_id: 12, quote: "puntuar todo en tiempo real multiplica el costo de GPU y ensancha la latencia de cola, con lo que arriesga el objetivo de 300 ms"}
    - {turn_id: 12, quote: "Lo que me haría cambiar: una prueba donde el brazo en tiempo real mejore la retención o los inicios de reproducción por más de lo que justifica el costo."}
    - {turn_id: 12, quote: "Todavía no sé cuánta obsolescencia notan realmente los miembros, así que lo mediría con un A/B sobre la edad de la caché antes de pagar la infraestructura."}
hints: []
---

# Scorecard: 01-ml-system-design@design

> Recommendation derived by the simulator's pedagogical rule; Netflix does not use a common scale.
> Recomendación derivada por la regla pedagógica del simulador; Netflix no usa una escala común.

## Summary
**Recommendation:** pass. **Observed level:** L5.

The candidate met the L5 Yes bar on all five core competencies and on culture_signals, with no hints. The framing was complete and confirmed with the interviewer before any design work. The architecture had separate batch, nearline and online paths, consistent features and a traced request with fallbacks. The modeling section compared two options against the constraints and covered exposure and position bias. Reliability had explicit targets, three degraded modes, access control and a cost mitigation. Validation was a two-stage interleaving-then-A/B plan with exploration and layered monitors. Several answers touched L6 elements, such as data classification with auditing and retention, and a rollback threshold. None of the five core competencies fully reached the L6 bar, so no score is SY. The session was a normal close: the final interviewer meta shows `phase: closed` and lists no uncovered points. The session config language is English, but the candidate answered in Spanish throughout. This was not penalized; the quotes are kept verbatim in Spanish.

## Scores and evidence

### problem_framing_requirements: Y
- T2: "Separaría el objetivo de negocio, la satisfacción del miembro a largo plazo medida con retención, del proxy que puedo optimizar día a día"
- T2: "un presupuesto p99 de 300 ms para la petición de la página"
- T2: "Guardarraíles: la diversidad de filas y la tasa de inicio de reproducción por perfil no deben empeorar, y el costo por mil peticiones se mantiene plano."
- T2: "¿Coincide este alcance con el tuyo, incluyendo varios perfiles por cuenta y la TV como dispositivo principal?"

The candidate separated the business goal (retention) from the proxy (qualified play starts plus completion). They stated scale, latency and freshness numbers as explicit assumptions, named guardrails, named privacy and licensing constraints, and confirmed scope. Everything the L5 bar asks for is present. It is not SY because the L6 elements are missing: placing the page in the wider product and among other teams' metrics, saying what v1 would leave out, and a continue/stop rule after launch.

### architecture_data_flow: Y
- T4: "el servicio de página lee filas de candidatos precalculadas de una caché clave-valor indexada por id de perfil"
- T4: "Las features offline y online salen de las mismas definiciones, y el entrenamiento usa joins point-in-time para evitar fuga de datos."
- T4: "Si el ranker excede 150 ms servimos la última página buena en caché de ese perfil, y si no existe, una página de popularidad regional."

The design had separate batch, nearline and online paths. It named a technology class for each hop: ANN index, feature store, Kafka/Flink stream, key-value cache and low-latency store. It kept offline and online features consistent with shared definitions and point-in-time joins, and it traced one TV request with latency figures through two levels of fallback. It is not SY: there were no reusable versioned contracts, no comparison of two end-to-end alternatives, and no answer on what breaks first at 10x traffic.

### modeling_choices: Y
- T6: "Un árbol con gradient boosting sobre features diseñadas es barato y maneja el arranque en frío mediante metadatos, pero es débil con el orden de visualización."
- T6: "La pérdida es listwise con dos cabezas, inicio de reproducción y finalización, combinadas con pesos que ajusto contra retención en los tests."
- T6: "Los datos de entrenamiento vienen de impresiones registradas, que están sesgadas por la exposición de la política anterior y por la posición"
- T6: "Para elegir entre modelos offline uso NDCG@10 sobre un holdout temporal"

The candidate compared GBDT and a sequential transformer on latency, data volume and cold start. They defined a listwise two-head loss, described the logged-impression data and its exposure and position bias along with mitigations (position feature, propensity logging, epsilon exploration), and chose models by NDCG@10 plus IPS replay. It is not SY: there was no shared-versus-per-task strategy across surfaces, no quantified gain against cost, and no experiment that would falsify the main modeling assumption.

### scale_reliability_security: Y
- T8: "Objetivo de disponibilidad: 99,95% para cargas de página, con p99 por debajo de 300 ms."
- T8: "si el almacén de features online cae, el ranker corre con features por defecto calculadas en batch, con menor calidad pero con página"
- T8: "las features del historial de visualización se etiquetan como restringidas, el acceso es por servicio y auditado"
- T8: "El motor de costo es la inferencia en GPU del codificador secuencial"

The candidate set availability and latency targets and described degraded modes for three failures: ranker, feature store and cold cache. They covered access control for viewing history and unreleased titles, and named the main cost driver (GPU inference for the sequence encoder) with a mitigation. Data classification, auditing and retention are L6 elements, but regional failure, owners per failure class and a costed comparison of deployment options were absent, so the score stays Y.

### online_validation_monitoring: Y
- T10: "Primero interleaving, que necesita mucho menos tráfico y detecta rápido la preferencia de ranking, pero es una medida relativa"
- T10: "me dice qué ranker prefieren los miembros dentro de la misma lista y no dice nada sobre retención"
- T10: "Las métricas offline y online pueden discrepar porque el replay offline está sesgado por la política de registro y por la posición"
- T10: "mantengo activo el tráfico de exploración epsilon para que los datos sigan sin sesgo"
- T10: "Disparador de rollback: un guardarraíl roto o una tasa de fallback superior al 5% durante diez minutos."

Every L5 element is present. The candidate proposed interleaving followed by an A/B test, stated that interleaving is relative and says nothing about retention, explained why offline and online metrics can disagree, gave an ordered diagnosis for the flat-A/B case, kept epsilon exploration running, and listed model, data and system monitors with a rollback action. It is not SY because the L6 program for many concurrent variants (pruning, interference, long-term holdouts) and an ongoing audit of offline/online alignment were not discussed.

### culture_signals: Y
- T12: "puntuar todo en tiempo real multiplica el costo de GPU y ensancha la latencia de cola, con lo que arriesga el objetivo de 300 ms"
- T12: "Lo que me haría cambiar: una prueba donde el brazo en tiempo real mejore la retención o los inicios de reproducción por más de lo que justifica el costo."
- T12: "Todavía no sé cuánta obsolescencia notan realmente los miembros, así que lo mediría con un A/B sobre la edad de la caché antes de pagar la infraestructura."

In the judgment probe (T11), the candidate showed judgment, candor and courage, the three memo values for this stage. They disagreed directly and politely with the product partner and backed it with cost and latency reasoning. They conceded the one case where the partner is right and added a targeted re-rank for it. They named the evidence that would change their mind, and said they did not yet know how much staleness members notice, with a plan to measure it. It is not SY: they did not name who they would inform about the accepted risk, did not propose a way to farm for dissent, and did not commit with an explicit trigger to reopen the decision.

## Hints
None.

## Uncovered signal points
None. The stage closed normally (`phase: closed`) with no uncovered points recorded.

## Strengths and gaps
**Strengths:**
- Rigorous framing, with the business goal and proxy kept apart and explicit numeric assumptions.
- Clean separation of batch, nearline and online paths, with feature consistency and layered fallbacks.
- Strong treatment of exposure and position bias across modeling, offline evaluation and online exploration.
- A concrete validation plan with a diagnosis order and a quantified rollback trigger.
- Good handling of stakeholder pushback, including openly saying what was not yet known.

**Gaps (all toward L6):**
- No organizational or cross-surface framing, no explicit v1 non-goals, and no post-launch stop rule.
- No 10x bottleneck analysis and no comparison of two end-to-end architectures on cost, latency and operational burden.
- No regional-failure design, no incident owners, and no costed comparison of deployment options.
- No program for many concurrent experiments, and no long-term holdouts.
- On culture: no explicit dissent-farming step and no named reopen trigger.

## Study plan
1. **Architecture trade-offs at scale (architecture_data_flow, scale_reliability_security):** practice naming the first component to break at 10x traffic, comparing two end-to-end designs with numbers, and designing for regional failover. Study map: `recsys-course/16_production_serving/`, `recsys-course/17_mlops_monitoring/`, `recsys-course/08_deep_retrieval_ann/`; then the `ml-system-design` practice stage again.
2. **Validation program at L6 (online_validation_monitoring):** concurrent variants, pruning rules, interference between tests, long-term holdouts, and auditing offline/online metric alignment over time. Study map: `recsys-course/15_online_experimentation/`, `recsys-course/14_bandits_rl_ope/`, `recsys-course/17_mlops_monitoring/`.
3. **Product-level framing (problem_framing_requirements):** state v1 non-goals, adjacent surfaces and other teams' metrics, and a continue/stop decision rule after launch. Study map: `recsys-course/00_intro/`, `recsys-course/18_capstone/`, `recsys-course/19_elite_playbook/`.

Additional: for culture_signals, use the `culture` practice stage and the Netflix culture memo (jobs.netflix.com/culture) to work on farming for dissent and committing with a reopen trigger.
