# Spec Delta

## Purpose

Permite al candidato configurar y conducir una sesión de entrevista simulada de Netflix para roles de ML, eligiendo rol, nivel, idioma y qué etapas practicar, y orquesta el paso entre etapas.

## ADDED Requirements

### Requirement: Inicio de sesión con configuración explícita
El sistema SHALL iniciar cada sesión pidiendo o aceptando como argumento: rol (ML Engineer, Research Scientist, Applied/Data Scientist), nivel objetivo (L4, L5, L6), idioma de la entrevista (inglés o español) y etapas a simular. No SHALL comenzar ninguna etapa hasta que los cuatro valores estén definidos y confirmados por el candidato.

#### Scenario: Configuración interactiva
- **WHEN** el candidato invoca `/netflix-ml-interview` sin argumentos
- **THEN** el sistema pregunta rol, nivel, idioma y etapas, muestra un resumen de la configuración y espera confirmación antes de empezar

#### Scenario: Configuración por argumentos
- **WHEN** el candidato invoca `/netflix-ml-interview rol=mle nivel=L5 etapas=ml-system-design`
- **THEN** el sistema completa solo los valores que faltan (idioma) y muestra el resumen para confirmar

#### Scenario: Valor inválido
- **WHEN** el candidato indica una etapa, rol o nivel que no existe en el catálogo
- **THEN** el sistema rechaza el valor, lista las opciones válidas y no inicia la sesión

### Requirement: Selección de etapas a simular
El sistema SHALL permitir simular el loop completo, una única etapa o cualquier subconjunto de etapas del catálogo. Cuando se seleccionan varias, SHALL ejecutarlas en el orden canónico del catálogo, salvo que el candidato pida otro orden de forma explícita.

#### Scenario: Loop completo
- **WHEN** el candidato elige "loop completo"
- **THEN** el sistema ejecuta todas las etapas del catálogo aplicables al rol elegido, en orden canónico, y al final convoca al hiring committee

#### Scenario: Una sola etapa
- **WHEN** el candidato elige solo `experimentation`
- **THEN** el sistema ejecuta únicamente esa etapa, emite su scorecard y no convoca al hiring committee

#### Scenario: Subconjunto en orden propio
- **WHEN** el candidato elige `culture` y `coding` y pide hacer `culture` primero
- **THEN** el sistema ejecuta `culture` y luego `coding`

### Requirement: Etapas aplicables por rol
El sistema SHALL ajustar el loop completo al rol elegido usando la aplicabilidad declarada en el catálogo de etapas, e informar qué etapas se incluyen antes de empezar.

#### Scenario: Research Scientist
- **WHEN** el rol es Research Scientist y se pide el loop completo
- **THEN** el resumen de configuración lista las etapas aplicables a ese rol según el catálogo, incluido `project-deep-dive`

### Requirement: Transición entre etapas
Al terminar una etapa, el sistema SHALL anunciar el cierre, guardar su transcripción, lanzar su evaluación y preguntar al candidato si continúa con la siguiente etapa, pausa o termina la sesión.

#### Scenario: Continuar
- **WHEN** termina `coding` y quedan etapas pendientes
- **THEN** el sistema guarda la transcripción, ofrece continuar, pausar o terminar, y al elegir continuar presenta al entrevistador de la siguiente etapa

#### Scenario: Terminar antes de tiempo
- **WHEN** el candidato decide terminar con etapas pendientes
- **THEN** el sistema marca esas etapas como no realizadas, emite los scorecards de las completadas y, si hay más de una, convoca al hiring committee indicando que el loop está incompleto

### Requirement: Pausa y reanudación
El sistema SHALL permitir pausar una sesión y reanudarla más tarde desde la siguiente etapa pendiente, aunque sea en otra conversación.

#### Scenario: Reanudar sesión
- **WHEN** el candidato invoca `/netflix-ml-interview reanudar` y existe una sesión con etapas pendientes
- **THEN** el sistema muestra la configuración y las etapas completadas y continúa desde la primera etapa pendiente

#### Scenario: Nada que reanudar
- **WHEN** el candidato pide reanudar y no hay sesiones con etapas pendientes
- **THEN** el sistema lo indica y ofrece iniciar una sesión nueva

### Requirement: Comandos del candidato durante la sesión
Durante una etapa, el sistema SHALL reconocer los comandos `/pausa`, `/terminar-etapa` y `/tiempo` como instrucciones al orquestador y no como respuestas al entrevistador.

#### Scenario: Consultar tiempo
- **WHEN** el candidato escribe `/tiempo` en mitad de una etapa
- **THEN** el sistema muestra el tiempo transcurrido y el presupuesto de la etapa sin que el entrevistador lo trate como respuesta

#### Scenario: Terminar etapa
- **WHEN** el candidato escribe `/terminar-etapa`
- **THEN** el entrevistador cierra la etapa y el sistema pasa a la transición como en un cierre normal
