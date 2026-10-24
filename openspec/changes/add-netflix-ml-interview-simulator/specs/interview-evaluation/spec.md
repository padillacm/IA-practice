# Spec Delta

## Purpose

Produce una evaluación independiente, verificable y accionable de cada etapa, y simula el corte entre fases y el debrief con la decisión del hiring manager, incluyendo un plan de estudio para cerrar las brechas.

## ADDED Requirements

### Requirement: Rúbrica por competencias
Cada etapa SHALL tener una rúbrica versionada con 3 a 6 competencias, una de ellas de cultura vinculada a valores del memo. Cada competencia SHALL tener un id estable, una marca de si es central (core) y una barra "Yes" observable por nivel L4, L5 y L6. Strong No, No y Strong Yes se definen respecto a esa barra.

#### Scenario: Rúbrica válida
- **WHEN** se valida el contenido
- **THEN** cada rúbrica tiene versión; 3–6 competencias con ids únicos y al menos una central; la de cultura con sus valores del memo; y barras L4/L5/L6 distintas entre sí, sin adjetivos vacíos

#### Scenario: Cambio de versión
- **WHEN** una rúbrica cambia de versión
- **THEN** sus ids de competencia se mantienen, o se declaran renombrados

### Requirement: Evaluación independiente y basada en hechos
El scorecard de cada instancia SHALL generarlo un agente evaluador distinto del entrevistador. El evaluador SHALL recibir solo la transcripción sin las notas privadas del entrevistador, la configuración y la rúbrica. Con feedback inmediato se evalúa antes de continuar; con feedback diferido, en segundo plano.

#### Scenario: Notas privadas
- **WHEN** el entrevistador anotó juicios en su campo privado
- **THEN** la copia que recibe el evaluador no los contiene

### Requirement: Evidencia verificable
Cada puntuación SHALL estar respaldada por al menos una cita textual de un turno del candidato, identificado por su número de turno. El sistema SHALL verificar que cada cita aparece literalmente en ese turno antes de mostrar el scorecard.

#### Scenario: Cita inexistente
- **WHEN** una cita no aparece en el turno del candidato indicado
- **THEN** el sistema pide al evaluador que la corrija una vez y, si sigue sin aparecer, esa competencia pasa a "no evidence" con un aviso en el scorecard

### Requirement: Regla pedagógica de recomendación
La recomendación de cada etapa SHALL derivarse de las puntuaciones con una regla fija:
- **fail**: alguna competencia central en Strong No, o dos o más en No.
- **insufficient signal**: alguna central sin evidencia.
- **pass**: en los demás casos.

El nivel observado es el más alto cuya barra Yes cumplen todas las centrales. El scorecard SHALL indicar que esta regla es del simulador, no de Netflix.

#### Scenario: Dos centrales en No
- **WHEN** dos competencias centrales tienen No y el resto Yes
- **THEN** la recomendación es fail

#### Scenario: Sin evidencia
- **WHEN** una competencia central no tiene evidencia
- **THEN** la recomendación es insufficient signal, que no cuenta como pass ni como fail

### Requirement: Efecto de pistas y del fin de etapa
Una pista de tipo nudge SHALL limitar a Yes la competencia afectada, y una substantive, a No; ninguna afecta a otras competencias. Si la etapa termina por causa externa, las competencias sin cubrir quedan "no evidence". Si termina por causa del candidato (tiempo agotado o puntos sin cubrir pese a la redirección), SHALL puntuarse y listarse lo que faltó.

#### Scenario: Pista substantive
- **WHEN** el candidato necesitó una pista substantive para avanzar en una competencia
- **THEN** esa competencia no puede superar No y el scorecard lo explica en una sección de pistas

#### Scenario: Tiempo agotado por el candidato
- **WHEN** el candidato agotó el tiempo de `ml-system-design` sin cubrir monitorización
- **THEN** la competencia correspondiente se puntúa y el scorecard lista los puntos no cubiertos

### Requirement: Contenido del scorecard
El scorecard SHALL incluir, en el idioma de la sesión:
- la puntuación de cada competencia con su evidencia;
- para cada una por debajo de Yes, cómo sería una respuesta de nivel Yes;
- la recomendación, el nivel observado, las fortalezas y las brechas;
- un plan de estudio cuyos primeros 1–3 puntos son las recomendaciones.

Su cabecera estructurada SHALL usar enums en inglés y la versión de la rúbrica.

#### Scenario: Justificación con evidencia
- **WHEN** el evaluador puntúa No en una competencia
- **THEN** el scorecard cita el turno que lo justifica y explica qué habría sido una respuesta Yes

### Requirement: Feedback al terminar cada etapa
El sistema SHALL mostrar el scorecard de cada etapa al terminarla, salvo en modo diferido, en el que se guarda y se muestra junto a la decisión final. Antes del corte y del debrief, SHALL esperar a que existan todos los scorecards necesarios.

#### Scenario: Feedback diferido
- **WHEN** el candidato activó el feedback diferido
- **THEN** en el corte ve solo la decisión, y los scorecards los ve al final

### Requirement: Pesos por rol
El catálogo SHALL asignar a cada etapa de cada loop un peso (high, normal o low) que use el debrief. Por ejemplo, para `mle` pesan más `ml-system-design`, `culture` y `ml-depth`, y menos `coding`. Para `ds` pesan más las de experimentación, `stats` y `culture`.

#### Scenario: Peso ausente
- **WHEN** una etapa de un loop por defecto no tiene peso
- **THEN** la validación del contenido falla

### Requirement: Debrief de corte tras la VO1
En los roles con corte activo, un agente de debrief SHALL decidir con la regla del debrief final, aplicada a los scorecards existentes, si se pasa a la VO2. Si no hay screens evaluados, lo indica.

#### Scenario: Pasa a VO2
- **WHEN** todas las etapas de peso alto de la VO1 tienen pass
- **THEN** el corte decide continuar y lo comunica en el tono de un recruiter

#### Scenario: Corte negativo
- **WHEN** una etapa de peso alto de la VO1 tiene fail
- **THEN** el corte decide no continuar, justificándolo con referencias a los scorecards

### Requirement: Debrief y decisión del hiring manager
Con dos o más instancias completadas, un agente de debrief SHALL calcular un resultado provisional con una regla fija. Después simulará la discusión del panel: pass o fail de cada entrevistador, "¿alguien cambiaría de opinión?" citando solo evidencia ya existente y búsqueda de consenso. Por último, el HM decide como informed captain y solo puede apartarse del resultado provisional justificándolo con citas de scorecards.

#### Scenario: Fail firme en una etapa de peso alto
- **WHEN** una etapa de peso alto tiene una competencia central en Strong No y el resto es positivo
- **THEN** el resultado provisional es No Hire y, si el HM lo cambia, la decisión lo marca como override con su justificación

#### Scenario: Señales mixtas
- **WHEN** un `mle` tiene Strong Yes en `ml-system-design` y fail en `coding`
- **THEN** el resultado sigue la mayoría ponderada por los pesos del rol y el debrief explica ese cálculo

#### Scenario: Buen candidato, otro equipo
- **WHEN** las etapas de peso alto de la VO1 son pass y la cultura es positiva, pero el encaje con el equipo es débil (fails solo en `ml-depth` o `hm-onsite`)
- **THEN** la decisión es "not a fit for this team, referred" y ofrece repetir la VO2 con otro dominio

#### Scenario: Hire por debajo del nivel objetivo
- **WHEN** el resultado es Hire pero el nivel observado en las etapas de peso alto es inferior al objetivo
- **THEN** la decisión es Hire al nivel observado, y el debrief explica que es un resultado pedagógico

#### Scenario: Loop incompleto o solo screens
- **WHEN** el debrief se convoca con etapas sin realizar, o solo con screens
- **THEN** la decisión se marca como provisional y lista lo que falta

#### Scenario: Práctica tras corte negativo
- **WHEN** la VO2 se hizo en modo práctica tras un corte negativo
- **THEN** la decisión final mantiene el No Hire del corte, y las etapas de práctica solo aportan feedback y plan de estudio

### Requirement: Cultura agregada por valor
El debrief SHALL agregar las señales de cultura de todas las etapas por valor del memo, en un único veredicto de cultura, sin sumar la misma debilidad una vez por etapa.

#### Scenario: Debilidad repetida
- **WHEN** tres etapas registran una señal débil del mismo valor
- **THEN** el veredicto de cultura lo trata como una única debilidad respaldada por tres evidencias

### Requirement: Plan de estudio enlazado
El plan de estudio SHALL priorizar las brechas y enlazar el módulo de `recsys-course/` asignado a cada competencia. Cuando el curso no cubra el tema, SHALL usar la alternativa del mapa: una etapa para practicar o un recurso como el memo de cultura.

#### Scenario: Brecha en experimentación
- **WHEN** el scorecard de `experimentation` señala una brecha en reducción de varianza
- **THEN** el plan enlaza `recsys-course/15_online_experimentation/`

#### Scenario: Brecha sin módulo
- **WHEN** la brecha es de coding o de SQL
- **THEN** el plan propone practicar la etapa correspondiente, en lugar de un módulo del curso

### Requirement: Calidad del evaluador verificable
El proyecto SHALL incluir un conjunto de transcripciones de referencia con resultados esperados, para comprobar a mano la consistencia del evaluador y del debrief.

#### Scenario: Consistencia
- **WHEN** se puntúa tres veces la misma transcripción de referencia
- **THEN** la recomendación coincide en las tres y ninguna competencia varía más de un punto
