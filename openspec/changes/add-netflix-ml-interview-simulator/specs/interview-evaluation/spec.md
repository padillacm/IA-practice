# Spec Delta

## Purpose

Produce una evaluación independiente y accionable de cada etapa y un veredicto global de hiring committee, con un plan de estudio para cerrar las brechas detectadas.

## ADDED Requirements

### Requirement: Rúbrica por competencias
Cada etapa SHALL tener una rúbrica versionada con entre 3 y 6 competencias. Cada competencia SHALL describir lo que se observa en cada punto de una escala de 4 niveles (Strong No, No, Yes, Strong Yes), calibrada por nivel L4–L6.

#### Scenario: Rúbrica completa
- **WHEN** se valida el catálogo de etapas
- **THEN** cada etapa tiene una rúbrica con 3–6 competencias y descriptores para los 4 puntos de la escala y los 3 niveles

### Requirement: Evaluación independiente del entrevistador
El scorecard de una etapa SHALL generarlo un agente evaluador distinto del entrevistador. Ese agente recibe solo la transcripción, la configuración de la sesión y la rúbrica, no el razonamiento interno del entrevistador.

#### Scenario: Evaluación tras cerrar etapa
- **WHEN** se cierra una etapa
- **THEN** un agente evaluador en un contexto nuevo produce el scorecard a partir de la transcripción guardada

### Requirement: Contenido del scorecard
El scorecard SHALL incluir, por competencia, la puntuación y al menos una cita textual de la transcripción que la justifique. Además SHALL incluir una señal global de la etapa, la calibración de nivel observada, las fortalezas, las brechas y entre 1 y 3 recomendaciones concretas, todo en español.

#### Scenario: Justificación con evidencia
- **WHEN** el evaluador puntúa "Strong No" en una competencia
- **THEN** el scorecard cita el fragmento de la transcripción que lo justifica y explica qué habría sido una respuesta de nivel "Yes"

#### Scenario: Evidencia insuficiente
- **WHEN** la transcripción no tiene evidencia para una competencia (p. ej. la etapa terminó antes)
- **THEN** esa competencia queda marcada como "sin evidencia" en lugar de recibir una puntuación

### Requirement: Feedback al terminar cada etapa
El sistema SHALL mostrar al candidato el scorecard de cada etapa al terminarla y antes de pasar a la siguiente, salvo que haya activado al configurar la sesión la opción de ver los scorecards solo al final.

#### Scenario: Feedback inmediato por defecto
- **WHEN** termina una etapa con la configuración por defecto
- **THEN** el candidato ve el scorecard antes de decidir si continúa

#### Scenario: Feedback diferido
- **WHEN** el candidato activó "scorecards solo al final"
- **THEN** los scorecards se guardan, pero solo se muestran junto al veredicto final

### Requirement: Veredicto del hiring committee
Cuando la sesión incluye dos o más etapas completadas, un agente hiring committee SHALL consolidar los scorecards en un veredicto: Hire / No Hire, nivel recomendado, justificación que referencie los scorecards, riesgos y, si el loop está incompleto, la lista de etapas sin evaluar.

#### Scenario: Señales mixtas
- **WHEN** el candidato tiene "Strong Yes" en `ml-system-design` y "No" en `coding`
- **THEN** el veredicto explica cómo pesó cada señal para el rol y nivel y qué evidencia adicional cambiaría la decisión

### Requirement: Plan de estudio enlazado
El veredicto y cada scorecard SHALL incluir un plan de estudio priorizado según las brechas. Cuando una brecha corresponda a un tema cubierto en `recsys-course/`, SHALL enlazar la ruta relativa del módulo correspondiente.

#### Scenario: Brecha en experimentación
- **WHEN** el scorecard de `experimentation` señala una brecha en reducción de varianza
- **THEN** el plan de estudio enlaza `recsys-course/15_online_experimentation/`
