# Spec Delta

## Purpose

Define el catálogo de etapas del loop de ML de Netflix y el comportamiento observable de los entrevistadores simulados en cada una, para que la práctica se parezca a la entrevista real.

## ADDED Requirements

### Requirement: Catálogo de etapas
El sistema SHALL ofrecer estas etapas, en este orden canónico: `recruiter-screen`, `hiring-manager`, `coding`, `ml-fundamentals`, `ml-system-design`, `ml-depth`, `experimentation`, `project-deep-dive`, `culture`. Cada etapa SHALL declarar duración objetivo, roles aplicables, competencias evaluadas y la persona del entrevistador.

#### Scenario: Listar catálogo
- **WHEN** el candidato pide ver las etapas disponibles
- **THEN** el sistema lista las nueve etapas con su duración objetivo, roles aplicables y una descripción de una línea

### Requirement: Un entrevistador independiente por etapa
Cada etapa SHALL ser conducida por un agente entrevistador propio, con su propio contexto, que no conoce las transcripciones de otras etapas, salvo la información que el candidato aporta en `hiring-manager` y `project-deep-dive` sobre su experiencia.

#### Scenario: Aislamiento entre etapas
- **WHEN** el candidato pasa de `coding` a `ml-fundamentals`
- **THEN** el entrevistador de `ml-fundamentals` se presenta como una persona nueva y no hace referencia a lo ocurrido en `coding`

### Requirement: Realismo sin feedback en vivo
Durante una etapa, el entrevistador SHALL mantener su persona, hacer una pregunta o repregunta por turno y no SHALL revelar la rúbrica, puntuaciones, respuestas modelo ni juicios sobre si una respuesta es correcta.

#### Scenario: Candidato pide la respuesta
- **WHEN** el candidato pregunta "¿esto está bien?" en mitad de `ml-fundamentals`
- **THEN** el entrevistador responde como lo haría uno real (p. ej. pidiendo que razone o que siga) sin confirmar ni corregir

#### Scenario: Candidato atascado
- **WHEN** el candidato dice que está bloqueado en `coding`
- **THEN** el entrevistador da como máximo una pista neutral de las que un entrevistador real daría y esa pista queda anotada en la transcripción para la evaluación

### Requirement: Preguntas adaptadas a rol y nivel
El entrevistador SHALL elegir preguntas del banco de la etapa compatibles con el rol y el nivel de la sesión, y SHALL repreguntar en profundidad según las respuestas del candidato, en lugar de recorrer una lista fija.

#### Scenario: Nivel senior
- **WHEN** la sesión es L6 en `ml-system-design`
- **THEN** el entrevistador exige trade-offs a escala, estrategia de experimentación y riesgos de producción además del diseño base

#### Scenario: Repregunta
- **WHEN** el candidato menciona "usaría two-tower para retrieval"
- **THEN** el entrevistador repregunta sobre ese punto (p. ej. negative sampling, cold start o serving) antes de cambiar de tema

### Requirement: Presupuesto de tiempo
Cada etapa SHALL tener un presupuesto de tiempo medido con marcas de tiempo reales. El entrevistador SHALL avisar cuando quede aproximadamente el 20 % del tiempo y cerrar la etapa al agotarse, reservando un hueco para preguntas del candidato.

#### Scenario: Tiempo agotado
- **WHEN** se supera la duración objetivo de la etapa
- **THEN** el entrevistador cierra el tema en curso, ofrece al candidato hacer preguntas y termina la etapa

### Requirement: Etapa de coding ejecutable
En `coding`, el sistema SHALL aceptar la solución pegada en el chat o escrita en un archivo del espacio de la sesión y, cuando esté en un archivo, SHALL ejecutar los tests del problema y registrar el resultado en la transcripción.

#### Scenario: Solución en archivo
- **WHEN** el candidato escribe su solución en el archivo indicado y dice "listo"
- **THEN** el sistema ejecuta los tests del problema, el entrevistador pregunta por complejidad y casos borde, y el resultado de los tests queda en la transcripción

### Requirement: Etapa de cultura basada en el memo de Netflix
La etapa `culture` SHALL evaluar comportamientos alineados con el memo de cultura público de Netflix (juicio, candor, valentía, contexto y no control, keeper test) mediante preguntas conductuales con repreguntas sobre situaciones concretas.

#### Scenario: Respuesta genérica
- **WHEN** el candidato responde con generalidades sin un ejemplo concreto
- **THEN** el entrevistador pide un caso real específico: qué pasó, qué hizo el candidato y cuál fue el resultado

### Requirement: Idioma de la entrevista
El entrevistador SHALL conducir la etapa en el idioma elegido en la sesión, aunque el candidato cambie de idioma en alguna respuesta.

#### Scenario: Entrevista en inglés
- **WHEN** el idioma de la sesión es inglés y el candidato responde una vez en español
- **THEN** el entrevistador sigue en inglés y el cambio de idioma queda anotado para la evaluación de comunicación
