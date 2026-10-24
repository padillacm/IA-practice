# Spec Delta

## Purpose

Produce una evaluación independiente y accionable de cada etapa y simula el debrief del panel con la decisión del hiring manager, con un plan de estudio para cerrar las brechas detectadas.

## ADDED Requirements

### Requirement: Rúbrica por competencias
Cada etapa SHALL tener una rúbrica versionada con entre 3 y 6 competencias, una de ellas de señales de cultura. Cada competencia SHALL describir lo que se observa en cada punto de una escala de 4 niveles (Strong No, No, Yes, Strong Yes), calibrada por nivel L4–L6.

#### Scenario: Rúbrica completa
- **WHEN** se valida el catálogo de etapas
- **THEN** cada etapa tiene una rúbrica con 3–6 competencias, incluida una de cultura, con descriptores para los 4 puntos de la escala y los 3 niveles

### Requirement: Evaluación independiente del entrevistador
El scorecard de una etapa SHALL generarlo un agente evaluador distinto del entrevistador. Ese agente recibe solo la transcripción, la configuración de la sesión y la rúbrica, no el razonamiento interno del entrevistador.

#### Scenario: Evaluación tras cerrar una etapa
- **WHEN** se cierra una etapa
- **THEN** un agente evaluador en un contexto nuevo produce el scorecard a partir de la transcripción guardada

### Requirement: Contenido del scorecard
El scorecard SHALL incluir: por competencia, la puntuación y al menos una cita textual de la transcripción que la justifique; la recomendación del entrevistador (pass / no-pass), la calibración de nivel observada, fortalezas, brechas y entre 1 y 3 recomendaciones concretas. Todo en el idioma de la sesión.

#### Scenario: Justificación con evidencia
- **WHEN** el evaluador puntúa "Strong No" en una competencia
- **THEN** el scorecard cita el fragmento de la transcripción que lo justifica y explica cómo habría sido una respuesta de nivel "Yes"

#### Scenario: Evidencia insuficiente
- **WHEN** la transcripción no tiene evidencia para una competencia (p. ej. la etapa terminó antes)
- **THEN** esa competencia queda marcada como "no evidence" en lugar de recibir una puntuación

### Requirement: Feedback al terminar cada etapa
El sistema SHALL mostrar al candidato el scorecard de cada etapa al terminarla, antes de pasar a la siguiente, salvo que haya activado al configurar la sesión la opción de ver los scorecards solo al final.

#### Scenario: Feedback inmediato por defecto
- **WHEN** termina una etapa con la configuración por defecto
- **THEN** el candidato ve el scorecard antes de decidir si continúa

#### Scenario: Feedback diferido
- **WHEN** el candidato activó "scorecards only at the end"
- **THEN** los scorecards se guardan, pero solo se muestran junto a la decisión final

### Requirement: Debrief y decisión del hiring manager
Con dos o más etapas completadas, un agente de debrief SHALL simular el debrief del panel, en vez de un hiring committee. Presenta la recomendación pass / no-pass de cada entrevistador, busca un consenso alto y emite la decisión del hiring manager como "informed captain": Hire / No Hire, nivel recomendado, justificación, riesgos y, si aplica, las etapas sin evaluar.

#### Scenario: Strong no en una etapa
- **WHEN** un scorecard tiene una competencia central en "Strong No" y el resto es positivo
- **THEN** el debrief explica que con un consenso alto esa señal suele bloquear la oferta y qué evidencia la contrarrestaría

#### Scenario: Señales mixtas
- **WHEN** el candidato tiene "Strong Yes" en `ml-system-design` y "No" en `coding`
- **THEN** el debrief explica cómo pesó el hiring manager cada señal para el rol, el nivel y las necesidades del equipo

#### Scenario: Loop incompleto
- **WHEN** el debrief se convoca con etapas sin realizar
- **THEN** la decisión indica que es provisional y lista las etapas que faltan

### Requirement: Plan de estudio enlazado
La decisión final y cada scorecard SHALL incluir un plan de estudio priorizado según las brechas. Cuando una brecha corresponda a un tema de `recsys-course/`, SHALL enlazar la ruta relativa del módulo.

#### Scenario: Brecha en experimentación
- **WHEN** el scorecard de `experimentation` señala una brecha en reducción de varianza
- **THEN** el plan de estudio enlaza `recsys-course/15_online_experimentation/`
